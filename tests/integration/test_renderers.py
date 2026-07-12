"""Renderer integration: hybrid conformance, fallback, and provider outage (FR-012, FR-014)."""
import pytest

from agent_debugger.domain.errors import DependencyError, SimulatorError
from agent_debugger.protocol.actions import CanonicalAction
from agent_debugger.renderers.base import RenderRequest, RenderResult, derive_protected_facts
from agent_debugger.renderers.deterministic import DeterministicRenderer
from agent_debugger.renderers.hybrid import HybridRenderer


def request_for_test_run(results=None):
    request = RenderRequest(
        action=CanonicalAction(action_type="test.run", params={}),
        turn=1,
        ok=True,
        result_data={"results": results or {"tests/t.py": "fail"}, "output": "1 failed"},
        error=None,
        state_projection={},
    )
    request.protected_facts = derive_protected_facts(request)
    return request


class FakeModelRenderer:
    name = "fake-model"
    revision = "f1"

    def __init__(self, bodies=None, error=None):
        self.bodies = list(bodies or [])
        self.error = error
        self.calls = 0

    async def render(self, request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return RenderResult(body=self.bodies.pop(0), source="model")


class TestProtectedFacts:
    def test_test_run_facts(self):
        facts = request_for_test_run().protected_facts
        assert {"must_contain": "tests/t.py: FAIL"} in facts
        assert {"must_not_contain": "tests/t.py: PASS"} in facts

    def test_error_facts(self):
        request = RenderRequest(
            action=CanonicalAction(action_type="fs.read", params={"path": "x"}),
            turn=1, ok=False, result_data={}, error={"code": "not_found", "message": "no"},
            state_projection={},
        )
        assert {"must_contain": "not_found"} in derive_protected_facts(request)


class TestHybridRenderer:
    async def test_conforming_output_passes_through(self):
        model = FakeModelRenderer(bodies=["running pytest…\ntests/t.py: FAIL\n1 failed"])
        hybrid = HybridRenderer(model)
        result = await hybrid.render(request_for_test_run())
        assert result.source == "model" and model.calls == 1

    async def test_contradiction_retries_then_falls_back(self):
        # Model claims tests pass while authoritative state says they fail.
        model = FakeModelRenderer(
            bodies=["all good! tests/t.py: PASS", "still fine, everything passed"]
        )
        hybrid = HybridRenderer(model, deterministic_fallback=True)
        result = await hybrid.render(request_for_test_run())
        assert model.calls == 2
        assert result.source == "fallback"
        assert result.fallback_reason == "conformance_violation"
        assert result.conformance_violations
        assert "tests/t.py: FAIL" in result.body  # deterministic truth reaches the agent

    async def test_provider_outage_falls_back(self):
        model = FakeModelRenderer(error=DependencyError("endpoint down"))
        hybrid = HybridRenderer(model, deterministic_fallback=True)
        result = await hybrid.render(request_for_test_run())
        assert result.source == "fallback" and "provider_error" in result.fallback_reason

    async def test_no_fallback_raises_simulator_error(self):
        model = FakeModelRenderer(error=DependencyError("endpoint down"))
        hybrid = HybridRenderer(model, deterministic_fallback=False)
        with pytest.raises(SimulatorError):
            await hybrid.render(request_for_test_run())


class TestDeterministicRenderer:
    async def test_identical_input_identical_output(self):
        renderer = DeterministicRenderer()
        a = await renderer.render(request_for_test_run())
        b = await renderer.render(request_for_test_run())
        assert a.body == b.body and a.source == "deterministic"
