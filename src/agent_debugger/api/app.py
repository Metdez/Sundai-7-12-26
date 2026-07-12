"""REST API and event streaming (PRD §10.2, FR-025 data source).

Route handlers contain no evaluation logic — they call application services
and repositories only. The web review app is served as static files.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_debugger import __version__
from agent_debugger.application import services
from agent_debugger.application.openrouter import OpenRouterGateway
from agent_debugger.domain.errors import AgentDebuggerError
from agent_debugger.orchestration.replay import replay_run
from agent_debugger.persistence.events import utc_now
from agent_debugger.persistence.workspace import Workspace
from agent_debugger.reports.compare import compare_run_sets, evaluate_regression
from agent_debugger.reports.exporters import run_report_html, run_report_markdown
from agent_debugger.reports.run_report import build_run_report
from agent_debugger.scoring.engine import scoring_rubric

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"


class RunSubmission(BaseModel):
    scenario: str
    agent: str
    seed: int = 0
    renderer: str | None = None
    trajectory: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class KeySubmission(BaseModel):
    # Plain str on purpose: Field(pattern=...) would echo the submitted key
    # back in FastAPI's 422 body. Format is checked in the gateway.
    key: str


class BenchmarkSubmission(BaseModel):
    models: list[str] = Field(min_length=1, max_length=8)
    seed: int = 0
    scenarios: list[str] | None = None


def create_app(workspace: Workspace) -> FastAPI:
    app = FastAPI(title="Agent Debugger API", version=__version__)
    active_runs: dict[str, Any] = {}
    gateway = OpenRouterGateway()
    app.state.openrouter_gateway = gateway  # test hook
    exec_cfg = (workspace.config().get("execution") or {})
    run_semaphore = asyncio.Semaphore(int(exec_cfg.get("max_concurrent_runs", 4)))
    # batch_id -> {"created_at": ..., "runs": [{run_id, scenario_id, model}]}
    benchmarks: dict[str, dict[str, Any]] = {}

    def _spawn_run(
        package: Any,
        revision: Any,
        *,
        seed: int,
        renderer: str | None = None,
        trajectory: str | None = None,
        labels: dict[str, str] | None = None,
        suite_id: str | None = None,
    ) -> str:
        """Create a background run task, gated by the concurrency semaphore."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        async def _execute() -> None:
            try:
                async with run_semaphore:
                    await services.execute_run(
                        workspace,
                        package,
                        revision,
                        seed=seed,
                        renderer_override=renderer,
                        trajectory=trajectory,
                        labels=labels or {},
                        suite_id=suite_id,
                        run_id=run_id,
                    )
            except Exception:  # noqa: BLE001 - recorded via run status/events
                pass
            finally:
                active_runs.pop(run_id, None)

        task = asyncio.create_task(_execute())
        active_runs[run_id] = task
        return run_id

    def _err(exc: AgentDebuggerError) -> HTTPException:
        status = {"configuration": 400, "scenario_defect": 400, "authorization": 403}.get(
            exc.category.value, 500
        )
        return HTTPException(status_code=status, detail=exc.to_payload())

    # -- metadata ---------------------------------------------------------
    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "workspace": str(workspace.root)}

    @app.get("/api/v1/scenarios")
    def scenarios(tag: str | None = None, difficulty: str | None = None):
        return services.enrich_scenario_rows(
            workspace.db().list_scenarios(tag=tag, difficulty=difficulty)
        )

    @app.get("/api/v1/scenarios/{scenario_id}")
    def scenario_detail(scenario_id: str):
        # Exposes hidden_facts (the planted bug) — operator review surface
        # only; never point an agent adapter at this API.
        detail = services.scenario_detail(workspace, scenario_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="scenario not found")
        return detail

    @app.get("/api/v1/agents")
    def agents():
        return workspace.db().list_agents()

    @app.get("/api/v1/scoring/rubric")
    def scoring_rubric_endpoint():
        return scoring_rubric()

    # -- runs ----------------------------------------------------------------
    @app.get("/api/v1/runs")
    def list_runs(
        scenario_id: str | None = None,
        agent: str | None = None,
        suite_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ):
        return workspace.db().list_runs(
            scenario_id=scenario_id,
            agent_revision_id=agent,
            suite_id=suite_id,
            status=status,
            limit=limit,
        )

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str):
        run = workspace.db().get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        return run

    @app.get("/api/v1/runs/{run_id}/events")
    def get_events(run_id: str):
        path = workspace.run_dir(run_id) / "events.jsonl"
        if not path.exists():
            raise HTTPException(404, "run events not found")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    @app.get("/api/v1/runs/{run_id}/report")
    def get_report(run_id: str):
        run = workspace.db().get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        return build_run_report(workspace.run_dir(run_id), run)

    @app.get("/api/v1/runs/{run_id}/report.md", response_class=PlainTextResponse)
    def get_report_md(run_id: str):
        run = workspace.db().get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        return run_report_markdown(build_run_report(workspace.run_dir(run_id), run))

    @app.get("/api/v1/runs/{run_id}/report.html", response_class=HTMLResponse)
    def get_report_html(run_id: str):
        run = workspace.db().get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        return run_report_html(build_run_report(workspace.run_dir(run_id), run))

    @app.post("/api/v1/runs/{run_id}/replay")
    def post_replay(run_id: str):
        run = workspace.db().get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        try:
            package = services.resolve_package(workspace, run["scenario_id"])
            return replay_run(workspace.run_dir(run_id), package)
        except AgentDebuggerError as exc:
            raise _err(exc) from exc

    @app.post("/api/v1/runs", status_code=202)
    async def submit_run(submission: RunSubmission):
        try:
            package = services.resolve_package(workspace, submission.scenario)
            revision = services.get_agent(workspace, submission.agent)
        except AgentDebuggerError as exc:
            raise _err(exc) from exc
        run_id = _spawn_run(
            package,
            revision,
            seed=submission.seed,
            renderer=submission.renderer,
            trajectory=submission.trajectory,
            labels=submission.labels,
        )
        return {"run_id": run_id, "status": "queued"}

    # -- providers + benchmark ---------------------------------------------
    @app.get("/api/v1/providers/openrouter/status")
    def openrouter_status():
        return app.state.openrouter_gateway.status()

    @app.post("/api/v1/providers/openrouter/key")
    async def openrouter_set_key(submission: KeySubmission):
        try:
            return await app.state.openrouter_gateway.set_key(submission.key)
        except AgentDebuggerError as exc:
            raise _err(exc) from exc

    @app.delete("/api/v1/providers/openrouter/key")
    def openrouter_clear_key():
        return app.state.openrouter_gateway.clear_key()

    @app.get("/api/v1/providers/openrouter/models")
    async def openrouter_models(refresh: bool = False):
        try:
            return await app.state.openrouter_gateway.list_models(refresh=refresh)
        except AgentDebuggerError as exc:
            raise HTTPException(status_code=502, detail=exc.user_message) from exc

    @app.post("/api/v1/benchmark", status_code=202)
    async def submit_benchmark(submission: BenchmarkSubmission):
        if not app.state.openrouter_gateway.status()["configured"]:
            raise HTTPException(400, "No OpenRouter key configured — add one first")
        scenario_ids = submission.scenarios or [
            row["scenario_id"] for row in workspace.db().list_scenarios()
        ]
        if not scenario_ids:
            raise HTTPException(400, "No scenarios registered in this workspace")
        try:
            packages = {
                sid: services.resolve_package(workspace, sid) for sid in scenario_ids
            }
            revisions = services.register_benchmark_agents(workspace, submission.models)
        except AgentDebuggerError as exc:
            raise _err(exc) from exc
        batch_id = f"bench-{uuid.uuid4().hex[:10]}"
        submitted: list[dict[str, str]] = []
        for slug in submission.models:
            for sid in scenario_ids:
                run_id = _spawn_run(
                    packages[sid],
                    revisions[slug],
                    seed=submission.seed,
                    labels={"batch": batch_id},
                    suite_id=batch_id,
                )
                submitted.append(
                    {"run_id": run_id, "scenario_id": sid, "model": slug}
                )
        benchmarks[batch_id] = {
            "created_at": utc_now(),
            "seed": submission.seed,
            "runs": submitted,
        }
        return {"batch_id": batch_id, "submitted": submitted}

    @app.get("/api/v1/benchmark/{batch_id}")
    def benchmark_status(batch_id: str):
        batch = benchmarks.get(batch_id)
        if batch is None:
            raise HTTPException(404, "unknown benchmark batch (server restarted?)")
        runs = []
        for entry in batch["runs"]:
            row = workspace.db().get_run(entry["run_id"])
            if row is None:
                runs.append({**entry, "status": "pending", "terminal_reason": None, "score": None})
            else:
                scorecard = row.get("scorecard") or {}
                runs.append(
                    {
                        **entry,
                        "status": row["status"],
                        "terminal_reason": row["terminal_reason"],
                        "score": scorecard.get("overall_score"),
                    }
                )
        return {
            "batch_id": batch_id,
            "created_at": batch["created_at"],
            "seed": batch["seed"],
            "runs": runs,
        }

    @app.post("/api/v1/runs/{run_id}/cancel")
    def cancel_run(run_id: str):
        task = active_runs.get(run_id)
        if task is None:
            raise HTTPException(409, "run is not active")
        task.cancel()
        return {"run_id": run_id, "cancel_requested": True}

    @app.get("/api/v1/runs/{run_id}/stream")
    async def stream_events(run_id: str):
        """Server-sent events: tail the run's event log until terminal."""
        path = workspace.run_dir(run_id) / "events.jsonl"

        async def generator():
            offset = 0
            terminal_seen = False
            for _ in range(1800):  # up to ~15 minutes at 0.5s
                if path.exists():
                    text = path.read_text(encoding="utf-8")
                    lines = [l for l in text.splitlines() if l]
                    while offset < len(lines):
                        event = lines[offset]
                        offset += 1
                        yield f"data: {event}\n\n"
                        if '"run.terminal"' in event or '"score.completed"' in event:
                            terminal_seen = '"score.completed"' in event or terminal_seen
                    if terminal_seen and run_id not in active_runs:
                        yield "event: done\ndata: {}\n\n"
                        return
                await asyncio.sleep(0.5)
            yield "event: timeout\ndata: {}\n\n"

        return StreamingResponse(generator(), media_type="text/event-stream")

    # -- comparison ------------------------------------------------------------
    @app.get("/api/v1/compare")
    def compare(baseline: str, candidate: str, gate: bool = False):
        db = workspace.db()
        base = db.list_runs(suite_id=baseline) or db.list_runs(agent_revision_id=baseline)
        cand = db.list_runs(suite_id=candidate) or db.list_runs(agent_revision_id=candidate)
        if not base or not cand:
            raise HTTPException(400, "baseline or candidate run set is empty")
        comparison = compare_run_sets(base, cand, baseline, candidate)
        if gate:
            thresholds = (workspace.config().get("ci", {}) or {}).get("fail_on")
            return evaluate_regression(comparison, thresholds)
        return comparison

    # -- web review app -----------------------------------------------------------
    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST), name="assets")

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def index():
            return FileResponse(WEB_DIST / "index.html")

    return app
