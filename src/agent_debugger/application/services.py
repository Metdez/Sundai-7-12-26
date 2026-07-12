"""Application services shared by CLI and API (thin surfaces, shared core)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from agent_debugger.adapters.registry import build_adapter
from agent_debugger.domain.errors import ConfigurationError, ScenarioError
from agent_debugger.domain.model import AgentRevision, RunLimits, digest_of, sha256_hex
from agent_debugger.orchestration.runner import RunOrchestrator, RunResult
from agent_debugger.persistence.events import utc_now
from agent_debugger.persistence.workspace import Workspace
from agent_debugger.renderers.base import ObservationRenderer
from agent_debugger.renderers.deterministic import DeterministicRenderer
from agent_debugger.renderers.hybrid import HybridRenderer
from agent_debugger.renderers.qwen import QwenAgentWorldRenderer
from agent_debugger.scenario.guide import load_guide
from agent_debugger.scenario.package import ScenarioPackage, load_package


# -- scenarios -------------------------------------------------------------
def resolve_package(workspace: Workspace, ref: str) -> ScenarioPackage:
    """Resolve a scenario by directory path or registered scenario_id."""
    path = Path(ref)
    if not path.is_absolute():
        for base in (Path.cwd(), workspace.root):
            candidate = base / ref
            if (candidate / "manifest.yaml").is_file():
                return load_package(candidate)
    if (path / "manifest.yaml").is_file():
        return load_package(path)
    row = workspace.db().get_scenario(ref)
    if row is None:
        raise ScenarioError(f"Scenario not found by path or id: {ref}")
    package = load_package(row["root_path"])
    if package.digest != row["digest"]:
        raise ScenarioError(
            f"Scenario {ref} changed since registration (digest mismatch); re-register it",
            details={"registered": row["digest"], "current": package.digest},
        )
    return package


def register_scenario(workspace: Workspace, package: ScenarioPackage) -> None:
    workspace.db().register_scenario(
        scenario_id=package.scenario_id,
        version=package.version,
        digest=package.digest,
        root_path=str(package.root.resolve()),
        title=package.manifest.title,
        difficulty=package.manifest.difficulty,
        tags=package.manifest.tags,
        registered_at=utc_now(),
    )


def scenario_detail(workspace: Workspace, scenario_id: str) -> dict[str, Any] | None:
    """Full scenario payload for the review dashboard.

    Deliberately exposes hidden_facts (the planted bug) — this is the
    operator review surface; never point an agent adapter at this API.
    Loads the package directly rather than via resolve_package so a digest
    mismatch is reported as data (digest_ok=False), not raised as an error.
    """
    row = workspace.db().get_scenario(scenario_id)
    if row is None:
        return None
    payload: dict[str, Any] = {
        **row,
        "task": None,
        "failure_type": None,
        "language": None,
        "framework": None,
        "par_actions": None,
        "package_available": False,
        "digest_ok": None,
        "guide": None,
    }
    try:
        package = load_package(row["root_path"])
        manifest = package.manifest
        payload.update(
            title=manifest.title,
            task=manifest.task,
            difficulty=manifest.difficulty,
            language=manifest.language,
            framework=manifest.framework,
            failure_type=manifest.failure_type,
            tags=manifest.tags,
            par_actions=manifest.par_actions,
            scoring_profile=manifest.scoring_profile,
            allowed_actions=manifest.allowed_actions,
            success_predicates=manifest.success_predicates,
            failure_predicates=manifest.failure_predicates,
            perturbations=[p.model_dump() for p in manifest.perturbations],
            hidden_facts=manifest.initial_state.hidden_facts,
            log_channels=sorted(manifest.initial_state.logs),
            test_suites=sorted(manifest.test_suites),
            package_available=True,
            digest_ok=package.digest == row["digest"],
        )
    except (ScenarioError, OSError):
        pass  # degraded payload from the DB row only
    guide = load_guide(Path(row["root_path"]), scenario_id)
    if guide is not None:
        payload["guide"] = guide.model_dump()
    return payload


def enrich_scenario_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best-effort manifest enrichment for the scenario list (never raises)."""
    enriched: list[dict[str, Any]] = []
    for row in rows:
        extra: dict[str, Any] = {
            "task": None,
            "par_actions": None,
            "failure_type": None,
            "language": None,
            "framework": None,
        }
        try:
            manifest = load_package(row["root_path"]).manifest
            extra.update(
                task=manifest.task,
                par_actions=manifest.par_actions,
                failure_type=manifest.failure_type,
                language=manifest.language,
                framework=manifest.framework,
            )
        except (ScenarioError, OSError):
            pass
        enriched.append({**row, **extra})
    return enriched


# -- agents ----------------------------------------------------------------
def register_agent(workspace: Workspace, config: dict[str, Any]) -> AgentRevision:
    if "name" not in config or "adapter_id" not in config:
        raise ConfigurationError("Agent config requires at least: name, adapter_id")
    prompt = config.get("prompt") or config.get("behavior", {}).get("system_prompt", "")
    revision = AgentRevision(
        revision_id=AgentRevision.compute_revision_id(config),
        name=config["name"],
        adapter_id=config["adapter_id"],
        adapter_version=config.get("adapter_version", "0.1.0"),
        model_identifier=config.get("model_identifier", "none"),
        prompt_digest=sha256_hex(prompt),
        limits=RunLimits.model_validate(config.get("limits", {})),
        generation_settings=config.get("generation_settings", {}),
        behavior=config.get("behavior", {}),
        endpoint=config.get("endpoint"),
        api_key_ref=config.get("api_key_ref"),
        tags=config.get("tags", []),
    )
    if config.get("api_key") or config.get("secret"):
        raise ConfigurationError(
            "Agent config must reference secrets (api_key_ref: env:NAME), never store values"
        )
    workspace.db().save_agent(revision, utc_now())
    return revision


def load_agent_config(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigurationError(f"Agent config must be a mapping: {path}")
    return data


def get_agent(workspace: Workspace, ref: str) -> AgentRevision:
    revision = workspace.db().get_agent(ref)
    if revision is None:
        raise ConfigurationError(f"Agent not found: {ref} (register with `agent add`)")
    return revision


# -- renderers ---------------------------------------------------------------
def build_renderer(
    workspace: Workspace, package: ScenarioPackage, override: str | None = None
) -> ObservationRenderer:
    kind = override or package.manifest.renderer.type
    if kind == "deterministic":
        return DeterministicRenderer()

    provider_cfg = (workspace.config().get("providers") or {}).get("world_model") or {}
    base_url = os.environ.get("AGENTWORLD_BASE_URL") or provider_cfg.get("base_url", "")
    if base_url.startswith("${"):
        base_url = ""
    if not base_url:
        raise ConfigurationError(
            "Model renderer requested but AGENTWORLD_BASE_URL is not configured; "
            "use --renderer deterministic or configure providers.world_model"
        )
    qwen = QwenAgentWorldRenderer(
        base_url=base_url,
        model=provider_cfg.get("model", "Qwen/Qwen-AgentWorld-35B-A3B"),
        api_key_ref=provider_cfg.get("api_key_ref")
        if os.environ.get(str(provider_cfg.get("api_key_ref", "")).removeprefix("env:"))
        else None,
        timeout_seconds=float(provider_cfg.get("timeout_seconds", 120)),
    )
    if kind == "qwen-agentworld":
        return HybridRenderer(qwen, deterministic_fallback=False)
    return HybridRenderer(
        qwen, deterministic_fallback=package.manifest.renderer.deterministic_fallback
    )


# -- runs ------------------------------------------------------------------
async def execute_run(
    workspace: Workspace,
    package: ScenarioPackage,
    revision: AgentRevision,
    seed: int = 0,
    renderer_override: str | None = None,
    trajectory: str | None = None,
    limits: RunLimits | None = None,
    operator: str | None = None,
    labels: dict[str, str] | None = None,
    suite_id: str | None = None,
    run_id: str | None = None,
    event_listener=None,
) -> RunResult:
    trajectory_data = package.load_trajectory(trajectory) if trajectory else None
    adapter = build_adapter(revision, trajectory=trajectory_data)
    orchestrator = RunOrchestrator(
        workspace=workspace,
        package=package,
        agent_revision=revision,
        adapter=adapter,
        renderer=build_renderer(workspace, package, renderer_override),
        seed=seed,
        limits=limits or revision.limits,
        operator=operator,
        labels=labels or {},
        suite_id=suite_id,
        run_id=run_id,
        event_listener=event_listener,
    )
    return await orchestrator.execute()


def scenario_determinism_check(package: ScenarioPackage, trajectory: str, repeats: int = 2) -> bool:
    """Repeated fixture runs must produce identical state hash sequences (§11.1)."""
    from agent_debugger.protocol.actions import normalize_action
    from agent_debugger.scenario.engine import StateEngine

    sequences = []
    for _ in range(repeats):
        state = package.build_initial_state()
        engine = StateEngine(package.manifest, state, seed=0)
        hashes = []
        for turn, raw in enumerate(package.load_trajectory(trajectory), start=1):
            action = normalize_action(raw)
            result = engine.apply(action, turn)
            hashes.append(result.state_hash)
        sequences.append(hashes)
    return all(seq == sequences[0] for seq in sequences)
