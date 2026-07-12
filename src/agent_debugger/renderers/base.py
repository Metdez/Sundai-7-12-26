"""Observation renderer interface (FR-010) and protected-fact derivation (FR-012)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_debugger.protocol.actions import CanonicalAction


@dataclass
class RenderRequest:
    action: CanonicalAction
    turn: int
    ok: bool
    result_data: dict[str, Any]
    error: dict[str, str] | None
    state_projection: dict[str, Any]
    history: list[dict[str, str]] = field(default_factory=list)
    seed: int = 0
    protected_facts: list[dict[str, str]] = field(default_factory=list)


@dataclass
class RenderResult:
    body: str
    source: str  # deterministic | model | fallback
    provider_meta: dict[str, Any] = field(default_factory=dict)
    fallback_reason: str | None = None
    conformance_violations: list[str] = field(default_factory=list)


class ObservationRenderer(Protocol):
    name: str
    revision: str

    async def render(self, request: RenderRequest) -> RenderResult: ...


def derive_protected_facts(request: RenderRequest) -> list[dict[str, str]]:
    """Authoritative facts that a model renderer must not contradict.

    Each fact is {"must_contain": s} or {"must_not_contain": s}. These are the
    conformance contract for FR-012: contradiction of protected state facts is
    detected mechanically, not by judgment.
    """
    facts: list[dict[str, str]] = []
    data = request.result_data
    if request.action.action_type == "test.run" and request.ok:
        for suite, status in sorted(data.get("results", {}).items()):
            facts.append({"must_contain": f"{suite}: {status.upper()}"})
            opposite = "PASS" if status == "fail" else "FAIL"
            facts.append({"must_not_contain": f"{suite}: {opposite}"})
    if request.action.action_type == "shell.run" and request.ok:
        facts.append({"must_contain": f"exit code {data.get('exit_code', 0)}"})
    if not request.ok and request.error is not None:
        facts.append({"must_contain": request.error.get("code", "error")})
    return facts


def check_conformance(body: str, facts: list[dict[str, str]]) -> list[str]:
    violations = []
    for fact in facts:
        if "must_contain" in fact and fact["must_contain"] not in body:
            violations.append(f"missing required fact: {fact['must_contain']!r}")
        if "must_not_contain" in fact and fact["must_not_contain"] in body:
            violations.append(f"contradicts protected fact: {fact['must_not_contain']!r}")
    return violations
