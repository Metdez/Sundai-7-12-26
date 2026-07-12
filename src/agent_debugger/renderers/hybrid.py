"""Hybrid renderer: model realism with deterministic truth (FR-012, FR-014).

Order of operations per observation:
1. Ask the model renderer.
2. Check conformance against protected facts.
3. On violation, retry once; on second violation or provider failure,
   fall back to the deterministic renderer when the scenario allows it.
Every fallback and violation is reported so the run log can disclose it.
"""
from __future__ import annotations

from agent_debugger.domain.errors import AgentDebuggerError, SimulatorError
from agent_debugger.renderers.base import (
    ObservationRenderer,
    RenderRequest,
    RenderResult,
    check_conformance,
)
from agent_debugger.renderers.deterministic import DeterministicRenderer


class HybridRenderer:
    name = "hybrid"

    def __init__(
        self,
        model_renderer: ObservationRenderer,
        deterministic_fallback: bool = True,
    ) -> None:
        self.model_renderer = model_renderer
        self.fallback_renderer = DeterministicRenderer()
        self.deterministic_fallback = deterministic_fallback
        self.revision = f"hybrid+{model_renderer.revision}"

    async def _fallback(self, request: RenderRequest, reason: str, violations: list[str]) -> RenderResult:
        if not self.deterministic_fallback:
            raise SimulatorError(
                f"Model renderer failed without permitted fallback: {reason}",
                details={"violations": violations},
            )
        result = await self.fallback_renderer.render(request)
        result.source = "fallback"
        result.fallback_reason = reason
        result.conformance_violations = violations
        return result

    async def render(self, request: RenderRequest) -> RenderResult:
        violations: list[str] = []
        for attempt in range(2):
            try:
                result = await self.model_renderer.render(request)
            except AgentDebuggerError as exc:
                return await self._fallback(request, f"provider_error: {exc.message}", violations)
            violations = check_conformance(result.body, request.protected_facts)
            if not violations:
                return result
        return await self._fallback(request, "conformance_violation", violations)
