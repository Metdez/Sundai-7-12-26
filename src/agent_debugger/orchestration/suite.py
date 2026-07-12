"""Concurrent suite execution (FR-018).

Independent scenarios run in a bounded task pool; one run's failure never
terminates unrelated runs.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable

from agent_debugger.adapters.registry import build_adapter
from agent_debugger.domain.model import AgentRevision, RunLimits
from agent_debugger.orchestration.runner import RunOrchestrator, RunResult
from agent_debugger.persistence.workspace import Workspace
from agent_debugger.renderers.base import ObservationRenderer
from agent_debugger.scenario.package import ScenarioPackage


async def run_suite(
    workspace: Workspace,
    packages: list[ScenarioPackage],
    agent_revision: AgentRevision,
    renderer_factory: Callable[[ScenarioPackage], ObservationRenderer],
    seeds: list[int] | None = None,
    limits: RunLimits | None = None,
    max_concurrency: int = 4,
    operator: str | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    suite_id = f"suite-{uuid.uuid4().hex[:10]}"
    seeds = seeds or [0]
    semaphore = asyncio.Semaphore(max_concurrency)
    results: list[RunResult | dict[str, Any]] = []

    async def one(package: ScenarioPackage, seed: int):
        async with semaphore:
            try:
                adapter = build_adapter(agent_revision)
                orchestrator = RunOrchestrator(
                    workspace=workspace,
                    package=package,
                    agent_revision=agent_revision,
                    adapter=adapter,
                    renderer=renderer_factory(package),
                    seed=seed,
                    limits=limits or agent_revision.limits,
                    operator=operator,
                    suite_id=suite_id,
                    labels=labels or {},
                )
                return await orchestrator.execute()
            except Exception as exc:  # noqa: BLE001 - isolate per-run failures
                return {
                    "scenario_id": package.scenario_id,
                    "seed": seed,
                    "error": str(exc),
                }

    tasks = [one(pkg, seed) for pkg in packages for seed in seeds]
    for coro in asyncio.as_completed(tasks):
        results.append(await coro)

    summary = {
        "suite_id": suite_id,
        "total": len(tasks),
        "succeeded": sum(
            1
            for r in results
            if isinstance(r, RunResult) and r.terminal_reason is not None
            and r.terminal_reason.value == "success"
        ),
        "infrastructure_failures": sum(
            1
            for r in results
            if (isinstance(r, dict) and "error" in r)
            or (isinstance(r, RunResult) and r.status.value == "failed")
        ),
        "runs": [
            r.run_id if isinstance(r, RunResult) else r for r in results
        ],
    }
    return {"summary": summary, "results": results}
