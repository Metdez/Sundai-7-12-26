"""E2E: OpenRouter provider endpoints + UI benchmark launch (ASGI, no network)."""
import asyncio

import httpx
import pytest

from agent_debugger.adapters.scripted import ScriptedAgent
from agent_debugger.api.app import create_app
from agent_debugger.application import services
from agent_debugger.application.openrouter import KEY_ENV
from agent_debugger.scenario.package import load_package

FAKE_KEY = "sk-or-v1-" + "f" * 24


@pytest.fixture()
async def bench_api(workspace, repo_root, monkeypatch):
    package = load_package(repo_root / "scenarios" / "login-env-var")
    services.register_scenario(workspace, package)
    monkeypatch.delenv(KEY_ENV, raising=False)
    app = create_app(workspace)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, workspace, package, app


def scripted_factory(package):
    def factory(revision, trajectory=None):
        return ScriptedAgent(package.load_trajectory("known_good"))

    return factory


async def wait_for_terminal(client, suite_id: str, expected: int, tries: int = 200):
    for _ in range(tries):
        rows = (await client.get(f"/api/v1/runs?suite_id={suite_id}")).json()
        done = [r for r in rows if r["status"] in ("completed", "failed", "canceled")]
        if len(done) == expected:
            return rows
        await asyncio.sleep(0.05)
    raise AssertionError(f"benchmark runs did not finish (suite {suite_id})")


class TestProviderEndpoints:
    async def test_key_lifecycle(self, bench_api, monkeypatch):
        client, workspace, package, app = bench_api
        status = (await client.get("/api/v1/providers/openrouter/status")).json()
        assert status == {"configured": False, "source": None, "masked": None}

        async def accept(key: str) -> bool:
            return True

        monkeypatch.setattr(app.state.openrouter_gateway, "verify_key", accept)
        response = await client.post(
            "/api/v1/providers/openrouter/key", json={"key": FAKE_KEY}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["configured"] is True and body["source"] == "session"
        assert body["masked"].endswith(FAKE_KEY[-4:])
        assert FAKE_KEY not in response.text  # never echo the full key

        bad = await client.post(
            "/api/v1/providers/openrouter/key", json={"key": "sk-wrong"}
        )
        assert bad.status_code == 400
        assert "sk-wrong" not in bad.text

        cleared = (await client.delete("/api/v1/providers/openrouter/key")).json()
        assert cleared["configured"] is False

    async def test_models_proxy_shape(self, bench_api, monkeypatch):
        client, workspace, package, app = bench_api

        async def canned(refresh: bool = False):
            return {"cached": False, "models": [{"id": "x/y", "name": "XY",
                                                 "context_length": 8, "pricing": {}}]}

        monkeypatch.setattr(app.state.openrouter_gateway, "list_models", canned)
        result = (await client.get("/api/v1/providers/openrouter/models")).json()
        assert result["models"][0]["id"] == "x/y"


class TestBenchmark:
    async def test_requires_key(self, bench_api):
        client, *_ = bench_api
        response = await client.post(
            "/api/v1/benchmark", json={"models": ["a/b"], "seed": 1}
        )
        assert response.status_code == 400

    async def test_model_count_validated(self, bench_api, monkeypatch):
        client, *_ = bench_api
        monkeypatch.setenv(KEY_ENV, FAKE_KEY)
        too_many = await client.post(
            "/api/v1/benchmark", json={"models": [f"m/{i}" for i in range(9)]}
        )
        assert too_many.status_code == 422
        empty = await client.post("/api/v1/benchmark", json={"models": []})
        assert empty.status_code == 422

    async def test_happy_path_and_idempotent_agents(self, bench_api, monkeypatch):
        client, workspace, package, app = bench_api
        monkeypatch.setenv(KEY_ENV, FAKE_KEY)
        monkeypatch.setattr(services, "build_adapter", scripted_factory(package))

        submitted = await client.post(
            "/api/v1/benchmark",
            json={"models": ["fake/model-a", "fake/model-b"], "seed": 1},
        )
        assert submitted.status_code == 202
        body = submitted.json()
        batch_id = body["batch_id"]
        assert len(body["submitted"]) == 2  # 2 models × 1 registered scenario
        assert {e["model"] for e in body["submitted"]} == {"fake/model-a", "fake/model-b"}

        rows = await wait_for_terminal(client, batch_id, expected=2)
        assert all(r["status"] == "completed" for r in rows)
        assert all(r["terminal_reason"] == "success" for r in rows)

        agents = (await client.get("/api/v1/agents")).json()
        names = [a["name"] for a in agents]
        assert "fake-model-a" in names and "fake-model-b" in names

        # Re-submitting the same models must not create new agent revisions.
        again = await client.post(
            "/api/v1/benchmark",
            json={"models": ["fake/model-a", "fake/model-b"], "seed": 1},
        )
        assert again.status_code == 202
        await wait_for_terminal(client, again.json()["batch_id"], expected=2)
        assert len((await client.get("/api/v1/agents")).json()) == len(agents)

        batch = (await client.get(f"/api/v1/benchmark/{batch_id}")).json()
        assert batch["batch_id"] == batch_id
        assert len(batch["runs"]) == 2
        assert all(r["status"] == "completed" for r in batch["runs"])
        assert all(isinstance(r["score"], (int, float)) for r in batch["runs"])

        missing = await client.get("/api/v1/benchmark/bench-does-not-exist")
        assert missing.status_code == 404

    async def test_semaphore_serializes_runs(self, workspace, repo_root, monkeypatch):
        package = load_package(repo_root / "scenarios" / "login-env-var")
        services.register_scenario(workspace, package)
        monkeypatch.setenv(KEY_ENV, FAKE_KEY)
        workspace.config()["execution"]["max_concurrent_runs"] = 1  # cached dict
        monkeypatch.setattr(services, "build_adapter", scripted_factory(package))

        # Wrap execute_run with a concurrency gauge. The API's semaphore wraps
        # this call, so with max_concurrent_runs=1 the observed peak MUST be 1;
        # without the gate all three tasks enter immediately (peak 3).
        real_execute = services.execute_run
        gauge = {"active": 0, "peak": 0, "calls": 0}

        async def gauged_execute(*args, **kwargs):
            gauge["active"] += 1
            gauge["calls"] += 1
            gauge["peak"] = max(gauge["peak"], gauge["active"])
            try:
                await asyncio.sleep(0.01)  # widen the overlap window
                return await real_execute(*args, **kwargs)
            finally:
                gauge["active"] -= 1

        monkeypatch.setattr(services, "execute_run", gauged_execute)
        app = create_app(workspace)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/benchmark", json={"models": ["m/one", "m/two", "m/three"]}
            )
            assert response.status_code == 202
            await wait_for_terminal(client, response.json()["batch_id"], expected=3)

        assert gauge["calls"] == 3
        assert gauge["peak"] == 1, f"semaphore not enforced (peak {gauge['peak']})"
