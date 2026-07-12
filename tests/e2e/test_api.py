"""API end-to-end against the ASGI app (no network)."""
import asyncio

import httpx
import pytest

from agent_debugger.api.app import create_app
from agent_debugger.application import services
from agent_debugger.domain.model import RunLimits
from agent_debugger.scenario.package import load_package


@pytest.fixture()
async def api(workspace, repo_root):
    package = load_package(repo_root / "scenarios" / "login-env-var")
    services.register_scenario(workspace, package)
    revision = services.register_agent(workspace, {
        "name": "scripted", "adapter_id": "scripted", "model_identifier": "none",
        "behavior": {"trajectory": package.load_trajectory("known_good")},
        "limits": {"max_actions": 25},
    })
    app = create_app(workspace)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, workspace, package, revision


class TestApi:
    async def test_health_and_catalog(self, api):
        client, workspace, package, revision = api
        health = (await client.get("/api/v1/health")).json()
        assert health["status"] == "ok"
        scenarios = (await client.get("/api/v1/scenarios")).json()
        assert scenarios[0]["scenario_id"] == "webapp.login-env-var"
        agents = (await client.get("/api/v1/agents")).json()
        assert agents[0]["name"] == "scripted"

    async def test_submit_run_then_inspect(self, api):
        client, workspace, package, revision = api
        submitted = await client.post("/api/v1/runs", json={
            "scenario": "webapp.login-env-var", "agent": "scripted",
        })
        assert submitted.status_code == 202
        run_id = submitted.json()["run_id"]

        for _ in range(100):
            run = (await client.get(f"/api/v1/runs/{run_id}")).json() if (
                (await client.get(f"/api/v1/runs/{run_id}")).status_code == 200
            ) else None
            if run and run["status"] in ("completed", "failed", "canceled"):
                break
            await asyncio.sleep(0.05)
        assert run is not None and run["status"] == "completed"
        assert run["terminal_reason"] == "success"

        events = (await client.get(f"/api/v1/runs/{run_id}/events")).json()
        assert events[0]["event_type"] == "run.created"
        assert any(e["event_type"] == "score.completed" for e in events)

        report = (await client.get(f"/api/v1/runs/{run_id}/report")).json()
        assert report["outcome"]["terminal_reason"] == "success"

        html = await client.get(f"/api/v1/runs/{run_id}/report.html")
        assert html.status_code == 200 and "<table>" in html.text

        replay = (await client.post(f"/api/v1/runs/{run_id}/replay")).json()
        assert replay["match"] and replay["chain_verified"]

    async def test_missing_run_404(self, api):
        client, *_ = api
        assert (await client.get("/api/v1/runs/run-missing")).status_code == 404
        assert (await client.get("/api/v1/runs/run-missing/events")).status_code == 404

    async def test_bad_submission_400(self, api):
        client, *_ = api
        response = await client.post("/api/v1/runs", json={
            "scenario": "no.such", "agent": "scripted",
        })
        assert response.status_code == 400

    async def test_compare_empty_400(self, api):
        client, *_ = api
        response = await client.get("/api/v1/compare?baseline=a&candidate=b")
        assert response.status_code == 400
