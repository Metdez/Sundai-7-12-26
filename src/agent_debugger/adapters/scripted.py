"""Scripted agent adapter: replays a fixed trajectory (fixtures, known-good/bad paths)."""
from __future__ import annotations

from typing import Any

from agent_debugger.adapters.base import AgentContext
from agent_debugger.protocol.actions import Observation


class ScriptedAgent:
    adapter_id = "scripted"
    adapter_version = "0.1.0"

    def __init__(self, trajectory: list[dict[str, Any]]) -> None:
        self._trajectory = list(trajectory)
        self._index = 0
        self._canceled = False

    async def start(self, context: AgentContext) -> None:
        self._index = 0

    async def next_action(self, observation: Observation | None) -> dict[str, Any]:
        if self._canceled:
            return {"action_type": "agent.give_up", "params": {"reason": "canceled"}}
        if self._index >= len(self._trajectory):
            return {"action_type": "agent.submit", "params": {"summary": "trajectory complete"}}
        action = self._trajectory[self._index]
        self._index += 1
        return action

    async def cancel(self) -> None:
        self._canceled = True

    def usage(self) -> dict[str, float]:
        return {"tokens": 0, "cost_usd": 0.0}
