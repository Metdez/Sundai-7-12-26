"""Agent adapter interface (PRD §10.4, §25 provider abstraction).

Adapters translate an agent's native tool calls into canonical actions.
They can never mutate scenario state directly — the orchestrator owns the loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_debugger.domain.model import RunLimits
from agent_debugger.protocol.actions import CanonicalAction, Observation


@dataclass
class AgentContext:
    task: str
    scenario_id: str
    tool_contract: list[dict[str, Any]]
    limits: RunLimits
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentAdapter(Protocol):
    adapter_id: str
    adapter_version: str

    async def start(self, context: AgentContext) -> None: ...

    async def next_action(self, observation: Observation | None) -> CanonicalAction | dict[str, Any]:
        """Return the next proposed action.

        `observation` is None on the first turn (the task is in the context).
        The return value may be a raw dict; the orchestrator normalizes and
        validates it, so adapter defects surface as protocol errors.
        """
        ...

    async def cancel(self) -> None: ...

    def usage(self) -> dict[str, float]:
        """Cumulative {tokens, cost_usd} for budget enforcement."""
        ...
