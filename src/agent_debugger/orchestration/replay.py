"""Deterministic replay and audit (FR-027, §11.6).

Verifies the event hash chain, reapplies authoritative transitions from the
initial state, and compares state hashes turn by turn — without invoking the
agent or any renderer. Recorded observations remain readable offline.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_debugger.domain.model import EventType, PolicyDecision, RunManifest
from agent_debugger.persistence.events import EventStore
from agent_debugger.policy.engine import record_attempt_flags
from agent_debugger.protocol.actions import CanonicalAction
from agent_debugger.protocol.events import RunEvent, verify_chain
from agent_debugger.scenario.engine import StateEngine
from agent_debugger.scenario.package import ScenarioPackage


def replay_run(run_dir: str | Path, package: ScenarioPackage) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest = RunManifest.model_validate_json(
        (run_dir / "manifest.json").read_text(encoding="utf-8")
    )
    events = EventStore.load_events(run_dir / "events.jsonl")

    report: dict[str, Any] = {
        "run_id": manifest.run_id,
        "scenario_id": manifest.scenario_id,
        "chain_verified": False,
        "scenario_digest_match": None,
        "match": False,
        "divergence": None,
        "transitions_replayed": 0,
    }

    verify_chain(events)
    report["chain_verified"] = True
    report["scenario_digest_match"] = package.digest == manifest.scenario_digest

    state = package.build_initial_state()
    engine = StateEngine(package.manifest, state, seed=manifest.seed)

    pending_action: CanonicalAction | None = None
    pending_turn: int = 0
    pending_decision: str | None = None
    pending_class: str | None = None
    recorded_final: str | None = None

    def diverge(seq: int, expected: str, actual: str) -> dict[str, Any]:
        return {"seq": seq, "expected": expected, "actual": actual}

    for event in events:
        if event.event_type is EventType.RUN_STARTED:
            recorded = event.payload.get("initial_state_hash")
            actual = state.state_hash()
            if recorded != actual:
                report["divergence"] = diverge(event.seq, recorded, actual)
                return report
        elif event.event_type is EventType.AGENT_ACTION:
            pending_action = CanonicalAction.model_validate(event.payload["action"])
            pending_turn = event.payload.get("turn", 0)
            pending_decision = None
        elif event.event_type is EventType.POLICY_DECISION:
            pending_decision = event.payload.get("decision")
            pending_class = event.payload.get("action_class")
            if pending_decision != PolicyDecision.ALLOW.value and pending_action is not None:
                from agent_debugger.domain.model import ActionClass

                record_attempt_flags(state, ActionClass(pending_class))
                pending_action = None
        elif event.event_type is EventType.STATE_TRANSITION:
            if pending_action is None:
                continue
            result = engine.apply(pending_action, pending_turn)
            report["transitions_replayed"] += 1
            recorded_hash = event.payload.get("state_hash")
            if result.state_hash != recorded_hash:
                report["divergence"] = diverge(event.seq, recorded_hash, result.state_hash)
                return report
            pending_action = None
        elif event.event_type is EventType.RUN_TERMINAL:
            recorded_final = event.payload.get("final_state_hash")

    actual_final = state.state_hash()
    if recorded_final is not None and recorded_final != actual_final:
        report["divergence"] = diverge(-1, recorded_final, actual_final)
        return report

    report["match"] = True
    report["final_state_hash"] = actual_final
    return report
