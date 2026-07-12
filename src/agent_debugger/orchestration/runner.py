"""Run orchestrator (FR-015..FR-018, PRD §25 execution lifecycle).

Preflight -> manifest freeze -> state init -> loop(agent turn -> normalize ->
policy -> transition -> render -> persist -> terminal detection) -> score.

Each run is logically single-threaded so event order is total. Infrastructure
failures terminate the run distinctly and are never scored as agent failures.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from agent_debugger import __version__
from agent_debugger.adapters.base import AgentAdapter, AgentContext
from agent_debugger.domain.errors import AgentDebuggerError, DependencyError, ProtocolError
from agent_debugger.domain.model import (
    EventType,
    PolicyDecision,
    RunLimits,
    RunManifest,
    RunStatus,
    Scorecard,
    TerminalReason,
    digest_of,
)
from agent_debugger.persistence.events import EventStore, utc_now
from agent_debugger.persistence.workspace import Workspace
from agent_debugger.policy.engine import LimitTracker, PolicyEngine, record_attempt_flags
from agent_debugger.protocol.actions import (
    CanonicalAction,
    Observation,
    normalize_action,
    tool_contract,
)
from agent_debugger.renderers.base import ObservationRenderer, RenderRequest, derive_protected_facts
from agent_debugger.scenario.engine import StateEngine
from agent_debugger.scenario.package import ScenarioPackage
from agent_debugger.scoring.engine import SCORER_VERSION, score_run
from agent_debugger.util.secrets import redact

AGENT_CALL_TIMEOUT_SECONDS = 180.0
SNAPSHOT_INTERVAL = 10


@dataclass
class RunResult:
    run_id: str
    status: RunStatus
    terminal_reason: TerminalReason | None
    manifest: RunManifest
    metrics: dict[str, Any] = field(default_factory=dict)
    scorecard: Scorecard | None = None
    final_state_hash: str | None = None
    error: dict[str, Any] | None = None


class RunOrchestrator:
    def __init__(
        self,
        workspace: Workspace,
        package: ScenarioPackage,
        agent_revision,
        adapter: AgentAdapter,
        renderer: ObservationRenderer,
        seed: int = 0,
        limits: RunLimits | None = None,
        operator: str | None = None,
        baseline_id: str | None = None,
        suite_id: str | None = None,
        labels: dict[str, str] | None = None,
        event_listener=None,
    ) -> None:
        self.workspace = workspace
        self.package = package
        self.agent_revision = agent_revision
        self.adapter = adapter
        self.renderer = renderer
        self.seed = seed
        self.limits = limits or RunLimits(max_actions=package.manifest.par_actions * 6)
        self.operator = operator
        self.baseline_id = baseline_id
        self.suite_id = suite_id
        self.labels = labels or {}
        self._cancel_requested = False
        self._event_listener = event_listener

    def cancel(self) -> None:
        self._cancel_requested = True

    # ------------------------------------------------------------------
    def _freeze_manifest(self, run_id: str) -> RunManifest:
        return RunManifest(
            run_id=run_id,
            scenario_id=self.package.scenario_id,
            scenario_version=self.package.version,
            scenario_digest=self.package.digest,
            agent_revision_id=self.agent_revision.revision_id,
            agent_config_digest=digest_of(self.agent_revision.model_dump(mode="json")),
            renderer=getattr(self.renderer, "name", "deterministic"),
            renderer_revision=getattr(self.renderer, "revision", "0"),
            scorer_revision=SCORER_VERSION,
            scoring_profile=self.package.manifest.scoring_profile,
            seed=self.seed,
            limits=self.limits,
            created_at=utc_now(),
            product_version=__version__,
            baseline_id=self.baseline_id,
            operator=self.operator,
            labels=self.labels,
        )

    def _emit(self, store: EventStore, event_type: EventType, payload: dict[str, Any], tags=None):
        event = store.append(event_type, payload, evidence_tags=tags)
        if self._event_listener is not None:
            try:
                self._event_listener(event)
            except Exception:  # noqa: BLE001 - listeners must not break runs
                pass
        return event

    # ------------------------------------------------------------------
    async def execute(self) -> RunResult:
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        manifest = self._freeze_manifest(run_id)
        run_dir = self.workspace.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        db = self.workspace.db()
        artifacts = self.workspace.artifacts()
        db.create_run(manifest, suite_id=self.suite_id)
        store = EventStore(run_dir, run_id)
        self._emit(store, EventType.RUN_CREATED, {"manifest_digest": manifest.digest()})

        state = self.package.build_initial_state()
        engine = StateEngine(self.package.manifest, state, seed=self.seed)
        policy = PolicyEngine(self.package.manifest)
        tracker = LimitTracker(limits=self.limits)

        db.set_run_status(run_id, RunStatus.RUNNING, utc_now())
        self._emit(
            store,
            EventType.RUN_STARTED,
            {"initial_state_hash": state.state_hash(), "seed": self.seed},
        )

        context = AgentContext(
            task=self.package.manifest.task,
            scenario_id=self.package.scenario_id,
            tool_contract=[
                t for t in tool_contract()
                if t["name"] in set(self.package.manifest.allowed_actions)
                | {"agent.submit", "agent.give_up", "agent.hypothesis"}
            ],
            limits=self.limits,
            metadata={"difficulty": self.package.manifest.difficulty},
        )

        terminal: TerminalReason | None = None
        status = RunStatus.COMPLETED
        error_payload: dict[str, Any] | None = None
        observation: Observation | None = None
        history: list[dict[str, str]] = []
        turn = 0

        try:
            await self.adapter.start(context)
            while terminal is None:
                if self._cancel_requested:
                    terminal = TerminalReason.CANCELED
                    status = RunStatus.CANCELED
                    await self.adapter.cancel()
                    break

                turn += 1
                # ---- agent turn -------------------------------------------------
                try:
                    raw = await asyncio.wait_for(
                        self.adapter.next_action(observation), timeout=AGENT_CALL_TIMEOUT_SECONDS
                    )
                except asyncio.TimeoutError:
                    raise DependencyError(
                        "Agent adapter timed out", details={"turn": turn}
                    ) from None

                usage = self.adapter.usage()
                tracker.tokens_used = int(usage.get("tokens", 0))
                tracker.cost_usd = float(usage.get("cost_usd", 0.0))

                try:
                    action = normalize_action(raw)
                except ProtocolError as exc:
                    tracker.record_invalid()
                    self._emit(store, EventType.RUN_ERROR, {"error": exc.to_payload(), "turn": turn})
                    observation = Observation(
                        turn=turn,
                        action_type="invalid",
                        status="error",
                        body=f"ERROR [protocol]: {exc.user_message}",
                    )
                    breach = tracker.breach()
                    if breach is not None:
                        self._emit(store, EventType.LIMIT_EXCEEDED, {"limit": breach.value})
                        terminal = breach
                    continue

                tracker.record_action(action.signature())
                action_event = self._emit(
                    store,
                    EventType.AGENT_ACTION,
                    {
                        "turn": turn,
                        "action": action.model_dump(mode="json"),
                        "signature": action.signature(),
                    },
                )

                # ---- policy ------------------------------------------------------
                decision = policy.evaluate(action)
                self._emit(
                    store,
                    EventType.POLICY_DECISION,
                    {"turn": turn, "action_event": action_event.event_id, **decision.to_payload()},
                )

                if decision.decision is not PolicyDecision.ALLOW:
                    record_attempt_flags(state, decision.action_class)
                    if decision.decision is PolicyDecision.REQUIRE_APPROVAL:
                        # Non-interactive runs auto-deny; the attempt stays auditable.
                        self._emit(
                            store,
                            EventType.APPROVAL_REQUESTED,
                            {"turn": turn, "action_class": decision.action_class.value},
                        )
                        self._emit(
                            store,
                            EventType.APPROVAL_RESOLVED,
                            {"turn": turn, "approved": False, "reason": "non-interactive run"},
                        )
                    body = f"BLOCKED [{decision.action_class.value}]: {decision.reason}"
                    observation = Observation(
                        turn=turn, action_type=action.action_type, status="blocked", body=body
                    )
                    self._emit(
                        store,
                        EventType.OBSERVATION_RENDERED,
                        {
                            "turn": turn,
                            "status": "blocked",
                            "source": "deterministic",
                            "body": body,
                        },
                    )
                    history.append({"action": action.action_type, "observation": body})
                    if engine.failure_satisfied():
                        terminal = TerminalReason.FAILURE_PREDICATE
                        break
                    breach = tracker.breach()
                    if breach is not None:
                        self._emit(store, EventType.LIMIT_EXCEEDED, {"limit": breach.value})
                        terminal = breach
                    continue

                # ---- transition ---------------------------------------------------
                result = engine.apply(action, turn)
                if not result.ok:
                    tracker.record_invalid()
                if result.perturbed:
                    self._emit(
                        store,
                        EventType.PERTURBATION_APPLIED,
                        {"turn": turn, "action_type": action.action_type},
                    )
                self._emit(
                    store,
                    EventType.STATE_TRANSITION,
                    {
                        "turn": turn,
                        "action_event": action_event.event_id,
                        "ok": result.ok,
                        "error": result.error,
                        "changed_paths": result.changed_paths,
                        "state_hash": result.state_hash,
                        "perturbed": result.perturbed,
                    },
                )

                # ---- render --------------------------------------------------------
                request = RenderRequest(
                    action=action,
                    turn=turn,
                    ok=result.ok,
                    result_data=result.data,
                    error=result.error,
                    state_projection={
                        "changed_files": len(state.changed_files()),
                        "test_state": {k: v["status"] for k, v in state.test_state.items()},
                    },
                    history=history,
                    seed=self.seed,
                )
                request.protected_facts = derive_protected_facts(request)
                try:
                    rendered = await self.renderer.render(request)
                except AgentDebuggerError as exc:
                    error_payload = exc.to_payload()
                    self._emit(store, EventType.RUN_ERROR, {"error": error_payload, "turn": turn})
                    terminal = TerminalReason.INFRASTRUCTURE_FAILURE
                    status = RunStatus.FAILED
                    break

                if rendered.source == "fallback":
                    self._emit(
                        store,
                        EventType.RENDERER_FALLBACK,
                        {
                            "turn": turn,
                            "reason": rendered.fallback_reason,
                            "violations": rendered.conformance_violations,
                        },
                    )

                body = redact(rendered.body)
                obs_status = "ok" if result.ok else "error"
                observation = Observation(
                    turn=turn,
                    action_type=action.action_type,
                    status=obs_status,
                    source=rendered.source,
                    body=body,
                    data={"error": result.error} if result.error else {},
                )
                self._emit(
                    store,
                    EventType.OBSERVATION_RENDERED,
                    {
                        "turn": turn,
                        "status": obs_status,
                        "source": rendered.source,
                        "body": body,
                        "provider_meta": rendered.provider_meta,
                    },
                )
                history.append({"action": f"{action.action_type} {json.dumps(action.params)}",
                                "observation": body[:2000]})

                if turn % SNAPSHOT_INTERVAL == 0:
                    snap = artifacts.put(
                        json.dumps(state.snapshot(), sort_keys=True),
                        "application/json",
                        "state_snapshot",
                    )
                    self._emit(
                        store,
                        EventType.SNAPSHOT_TAKEN,
                        {"turn": turn, "artifact": snap.artifact_id, "state_hash": result.state_hash},
                    )

                # ---- terminal detection ---------------------------------------------
                if result.terminal_hint == "give_up":
                    terminal = TerminalReason.GAVE_UP
                elif engine.failure_satisfied():
                    terminal = TerminalReason.FAILURE_PREDICATE
                elif engine.success_satisfied():
                    terminal = TerminalReason.SUCCESS
                elif result.terminal_hint == "submit":
                    terminal = TerminalReason.SUBMITTED_UNSOLVED
                else:
                    breach = tracker.breach()
                    if breach is not None:
                        self._emit(store, EventType.LIMIT_EXCEEDED, {"limit": breach.value})
                        terminal = breach

        except AgentDebuggerError as exc:
            error_payload = exc.to_payload()
            self._emit(store, EventType.RUN_ERROR, {"error": error_payload, "turn": turn})
            terminal = TerminalReason.INFRASTRUCTURE_FAILURE
            status = RunStatus.FAILED

        # ---- freeze final state ------------------------------------------------
        final_hash = state.state_hash()
        final_snapshot = artifacts.put(
            json.dumps(state.snapshot(), sort_keys=True), "application/json", "final_state"
        )
        diff_result = engine._git_diff(  # authoritative final patch artifact
            CanonicalAction(action_type="git.diff", params={}), turn
        )
        patch_artifact = artifacts.put(
            diff_result.data.get("diff", ""), "text/x-diff", "final_patch"
        )
        metrics = tracker.metrics()
        self._emit(
            store,
            EventType.RUN_TERMINAL,
            {
                "reason": (terminal or TerminalReason.INFRASTRUCTURE_FAILURE).value,
                "final_state_hash": final_hash,
                "final_snapshot": final_snapshot.artifact_id,
                "final_patch": patch_artifact.artifact_id,
                "changed_files": state.changed_files(),
                "metrics": metrics,
            },
        )

        # ---- score (never for infrastructure failures) ---------------------------
        scorecard: Scorecard | None = None
        if status is not RunStatus.FAILED and terminal is not TerminalReason.INFRASTRUCTURE_FAILURE:
            events = store.read_all()
            scorecard = score_run(
                events,
                scoring_profile=self.package.manifest.scoring_profile,
                par_actions=self.package.manifest.par_actions,
                run_id=run_id,
            )
            self._emit(
                store,
                EventType.SCORE_COMPLETED,
                {
                    "overall": scorecard.overall_score,
                    "scorer_version": scorecard.scorer_version,
                    "dimensions": {d.dimension: d.score for d in scorecard.dimensions},
                },
            )
            db.save_scorecard(run_id, scorecard.model_dump_json(), utc_now())

        db.set_run_status(
            run_id,
            status,
            utc_now(),
            terminal_reason=terminal.value if terminal else None,
            metrics=metrics,
            error=error_payload,
        )

        return RunResult(
            run_id=run_id,
            status=status,
            terminal_reason=terminal,
            manifest=manifest,
            metrics=metrics,
            scorecard=scorecard,
            final_state_hash=final_hash,
            error=error_payload,
        )
