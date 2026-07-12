"""OpenRouter gateway: key lifecycle, verification, model-catalog caching."""
import httpx
import pytest

from agent_debugger.application.openrouter import KEY_ENV, OpenRouterGateway
from agent_debugger.domain.errors import ConfigurationError

VALID_KEY = "sk-or-v1-" + "a" * 24


def make_gateway(handler, **kwargs) -> OpenRouterGateway:
    transport = httpx.MockTransport(handler)
    return OpenRouterGateway(client=httpx.AsyncClient(transport=transport), **kwargs)


def ok_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/key"):
        return httpx.Response(200, json={"data": {"label": "test"}})
    return httpx.Response(
        200, json={"data": [{"id": "a/model", "name": "A Model", "context_length": 1}]}
    )


class TestKeyLifecycle:
    def test_mask_shows_only_tail(self):
        assert OpenRouterGateway.mask(VALID_KEY) == f"sk-or-…{VALID_KEY[-4:]}"

    async def test_bad_format_rejected_env_untouched(self, monkeypatch):
        monkeypatch.delenv(KEY_ENV, raising=False)
        gateway = make_gateway(ok_handler)
        with pytest.raises(ConfigurationError):
            await gateway.set_key("not-a-key")
        assert gateway.status()["configured"] is False

    async def test_set_key_success(self, monkeypatch):
        monkeypatch.delenv(KEY_ENV, raising=False)
        gateway = make_gateway(ok_handler)
        result = await gateway.set_key(VALID_KEY)
        assert result["configured"] is True
        assert result["source"] == "session"
        assert result["verified"] is True
        assert result["masked"].endswith(VALID_KEY[-4:])
        assert VALID_KEY not in str(result)

    async def test_rejected_key_not_stored(self, monkeypatch):
        monkeypatch.delenv(KEY_ENV, raising=False)
        gateway = make_gateway(lambda req: httpx.Response(401, json={}))
        with pytest.raises(ConfigurationError):
            await gateway.set_key(VALID_KEY)
        assert gateway.status()["configured"] is False

    async def test_transport_error_sets_key_unverified(self, monkeypatch):
        monkeypatch.delenv(KEY_ENV, raising=False)

        def boom(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no network", request=request)

        gateway = make_gateway(boom)
        result = await gateway.set_key(VALID_KEY)
        assert result["configured"] is True
        assert result["verified"] is False

    async def test_env_source_and_clear(self, monkeypatch):
        monkeypatch.setenv(KEY_ENV, VALID_KEY)
        gateway = make_gateway(ok_handler)
        assert gateway.status()["source"] == "env"
        await gateway.set_key(VALID_KEY)
        assert gateway.status()["source"] == "session"
        cleared = gateway.clear_key()
        assert cleared["configured"] is False


class TestModelCatalog:
    async def test_cache_hits_transport_once(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return ok_handler(request)

        gateway = make_gateway(handler)
        first = await gateway.list_models()
        second = await gateway.list_models()
        assert calls["n"] == 1
        assert first["models"] == second["models"]
        assert second["cached"] is True
        await gateway.list_models(refresh=True)
        assert calls["n"] == 2

    async def test_stale_cache_served_on_failure(self):
        state = {"fail": False}

        def handler(request: httpx.Request) -> httpx.Response:
            if state["fail"]:
                raise httpx.ConnectError("down", request=request)
            return ok_handler(request)

        gateway = make_gateway(handler, cache_ttl_seconds=0.0)
        first = await gateway.list_models()
        state["fail"] = True
        stale = await gateway.list_models()
        assert stale["stale"] is True
        assert stale["models"] == first["models"]

    async def test_entries_trimmed(self):
        gateway = make_gateway(ok_handler)
        result = await gateway.list_models()
        assert set(result["models"][0]) == {"id", "name", "context_length", "pricing"}
