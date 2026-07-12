"""Reference heuristic agent (PRD §21 dogfooding, open question 32.3).

A deterministic, offline agent whose *behavioral policy* is configurable:
how much it investigates, whether it states hypotheses, and whether it
verifies its fix. The repair recipe comes from configuration, so the same
recipe under different policies produces measurably different trajectories —
exactly what the Phase 1 dogfooding milestone needs to detect.
"""
from __future__ import annotations

from typing import Any

from agent_debugger.adapters.base import AgentContext
from agent_debugger.protocol.actions import Observation

DEFAULT_INVESTIGATION: list[dict[str, Any]] = [
    {"action_type": "test.run", "params": {}},
    {"action_type": "git.status", "params": {}},
]


class ReferenceHeuristicAgent:
    adapter_id = "reference-heuristic"
    adapter_version = "0.1.0"

    def __init__(self, behavior: dict[str, Any] | None = None) -> None:
        behavior = behavior or {}
        self.investigate: list[dict[str, Any]] = behavior.get(
            "investigate", DEFAULT_INVESTIGATION
        )
        self.hypothesis: str | None = behavior.get("hypothesis")
        self.fix: list[dict[str, Any]] = behavior.get("fix", [])
        self.verify_fix: bool = behavior.get("verify_fix", True)
        self.give_up_on_error: bool = behavior.get("give_up_on_error", False)
        self._plan: list[dict[str, Any]] = []
        self._canceled = False
        self._last_error = False

    async def start(self, context: AgentContext) -> None:
        plan: list[dict[str, Any]] = []
        plan.extend(self.investigate)
        if self.hypothesis:
            plan.append(
                {"action_type": "agent.hypothesis", "params": {"statement": self.hypothesis}}
            )
        plan.extend(self.fix)
        if self.verify_fix:
            plan.append({"action_type": "test.run", "params": {}})
        plan.append({"action_type": "agent.submit", "params": {"summary": "fix applied"}})
        self._plan = plan

    async def next_action(self, observation: Observation | None) -> dict[str, Any]:
        if self._canceled:
            return {"action_type": "agent.give_up", "params": {"reason": "canceled"}}
        if observation is not None and observation.status in ("error", "blocked"):
            self._last_error = True
            if self.give_up_on_error:
                return {
                    "action_type": "agent.give_up",
                    "params": {"reason": f"blocked by {observation.status}"},
                }
        if not self._plan:
            return {"action_type": "agent.submit", "params": {"summary": "plan exhausted"}}
        return self._plan.pop(0)

    async def cancel(self) -> None:
        self._canceled = True

    def usage(self) -> dict[str, float]:
        return {"tokens": 0, "cost_usd": 0.0}
