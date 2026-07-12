"""Adapter conformance + Qwen renderer against a mocked OpenAI-compatible endpoint."""
import json

import httpx
import pytest

from agent_debugger.adapters.openai_compat import OpenAICompatAdapter
from agent_debugger.adapters.reference import ReferenceHeuristicAgent
from agent_debugger.adapters.scripted import ScriptedAgent
from agent_debugger.protocol.actions import CanonicalAction
from agent_debugger.renderers.base import RenderRequest, derive_protected_facts
from agent_debugger.renderers.qwen import QwenAgentWorldRenderer
from agent_debugger.sdk.conformance import run_conformance


class TestConformance:
    async def test_scripted_agent_passes(self):
        adapter = ScriptedAgent([
            {"action_type": "fs.list", "params": {}},
            {"action_type": "test.run", "params": {}},
        ])
        report = await run_conformance(adapter)
        assert report["passed"], report["cases"]

    async def test_reference_agent_passes(self):
        report = await run_conformance(ReferenceHeuristicAgent({"fix": []}))
        assert report["passed"], report["cases"]

    async def test_defective_adapter_fails_cleanly(self):
        class Broken:
            adapter_id = "broken"
            adapter_version = "0"

            async def start(self, context):
                pass

            async def next_action(self, observation):
                return {"action_type": "fs.read", "params": {"path": 42}}  # bad param type

            async def cancel(self):
                pass

            def usage(self):
                return {"tokens": 0, "cost_usd": 0.0}

        report = await run_conformance(Broken())
        assert not report["passed"]
        failed = {c["case"] for c in report["cases"] if not c["passed"]}
        assert "first_action_valid" in failed


def openai_mock(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5)


class TestOpenAICompatAdapter:
    async def test_tool_call_translation(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["tools"], "tool contract must be forwarded"
            return httpx.Response(200, json={
                "choices": [{"message": {
                    "role": "assistant", "content": "checking files",
                    "tool_calls": [{"id": "c1", "type": "function", "function": {
                        "name": "fs__read", "arguments": json.dumps({"path": "src/app.py"}),
                    }}],
                }}],
                "usage": {"total_tokens": 123},
            })

        from agent_debugger.sdk.conformance import CONFORMANCE_CONTEXT

        adapter = OpenAICompatAdapter(
            endpoint="http://mock/v1", model="m", system_prompt="s",
            client=openai_mock(handler),
        )
        await adapter.start(CONFORMANCE_CONTEXT)
        raw = await adapter.next_action(None)
        assert raw["action_type"] == "fs.read"
        assert raw["params"] == {"path": "src/app.py"}
        assert adapter.usage()["tokens"] == 123

    async def test_plain_text_becomes_submission(self):
        def handler(request):
            return httpx.Response(200, json={
                "choices": [{"message": {"role": "assistant", "content": "All fixed."}}],
                "usage": {},
            })

        from agent_debugger.sdk.conformance import CONFORMANCE_CONTEXT

        adapter = OpenAICompatAdapter(
            endpoint="http://mock/v1", model="m", system_prompt="s", client=openai_mock(handler)
        )
        await adapter.start(CONFORMANCE_CONTEXT)
        raw = await adapter.next_action(None)
        assert raw["action_type"] == "agent.submit"


def render_request():
    request = RenderRequest(
        action=CanonicalAction(action_type="shell.run", params={"command": "ls"}),
        turn=3, ok=True,
        result_data={"command": "ls", "stdout": "src tests", "exit_code": 0},
        error=None, state_projection={"changed_files": 0}, seed=11,
    )
    request.protected_facts = derive_protected_facts(request)
    return request


class TestQwenRenderer:
    async def test_request_shape_and_response(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "src tests\n(exit code 0)"}}],
                "usage": {"total_tokens": 55},
            })

        renderer = QwenAgentWorldRenderer(
            base_url="http://mock/v1", client=openai_mock(handler)
        )
        result = await renderer.render(render_request())
        assert result.source == "model"
        assert result.provider_meta["usage"]["total_tokens"] == 55
        assert captured["seed"] == 11
        user_message = captured["messages"][-1]["content"]
        assert "exit code 0" in user_message  # protected fact forwarded
        assert "AUTHORITATIVE" in user_message

    async def test_retry_then_dependency_error(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(503)

        renderer = QwenAgentWorldRenderer(base_url="http://mock/v1", client=openai_mock(handler))
        from agent_debugger.domain.errors import DependencyError

        with pytest.raises(DependencyError):
            await renderer.render(render_request())
        assert calls["n"] == 2  # bounded retry

    async def test_malformed_response_is_simulator_error(self):
        def handler(request):
            return httpx.Response(200, json={"unexpected": True})

        from agent_debugger.domain.errors import SimulatorError

        renderer = QwenAgentWorldRenderer(base_url="http://mock/v1", client=openai_mock(handler))
        with pytest.raises(SimulatorError):
            await renderer.render(render_request())
