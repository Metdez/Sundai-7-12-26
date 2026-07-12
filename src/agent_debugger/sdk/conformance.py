"""Adapter conformance suite (FR-007).

Exercises an adapter against fixed cases without running a benchmark, so
adapter defects can be separated from agent behavior before registration.
"""
from __future__ import annotations

from typing import Any

from agent_debugger.adapters.base import AgentAdapter, AgentContext
from agent_debugger.domain.errors import ProtocolError
from agent_debugger.domain.model import RunLimits
from agent_debugger.protocol.actions import Observation, normalize_action, tool_contract

CONFORMANCE_CONTEXT = AgentContext(
    task="Conformance dry run: inspect the repository and submit.",
    scenario_id="conformance.dry-run",
    tool_contract=tool_contract(),
    limits=RunLimits(max_actions=10),
)


async def run_conformance(adapter: AgentAdapter, max_steps: int = 10) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def record(case: str, passed: bool, detail: str = "") -> None:
        cases.append({"case": case, "passed": passed, "detail": detail})

    # Case 1: lifecycle start
    try:
        await adapter.start(CONFORMANCE_CONTEXT)
        record("start", True)
    except Exception as exc:  # noqa: BLE001
        record("start", False, str(exc))
        return {"passed": False, "cases": cases}

    # Case 2: first action is protocol-valid
    try:
        first = await adapter.next_action(None)
        normalize_action(first)
        record("first_action_valid", True)
    except ProtocolError as exc:
        record("first_action_valid", False, exc.message)
        first = None
    except Exception as exc:  # noqa: BLE001
        record("first_action_valid", False, f"adapter raised: {exc}")
        first = None

    # Case 3: handles a normal observation
    try:
        obs = Observation(turn=1, action_type="fs.list", status="ok", body="Contents of .: (empty)")
        action = await adapter.next_action(obs)
        normalize_action(action)
        record("observation_handling", True)
    except Exception as exc:  # noqa: BLE001
        record("observation_handling", False, str(exc))

    # Case 4: survives an error observation without crashing
    try:
        obs = Observation(
            turn=2, action_type="fs.read", status="error", body="ERROR [not_found]: no such file"
        )
        action = await adapter.next_action(obs)
        normalize_action(action)
        record("error_observation_handling", True)
    except Exception as exc:  # noqa: BLE001
        record("error_observation_handling", False, str(exc))

    # Case 5: terminates within bounded steps
    try:
        terminated = False
        obs = Observation(turn=3, action_type="test.run", status="ok", body="tests: PASS")
        for _ in range(max_steps):
            action = normalize_action(await adapter.next_action(obs))
            if action.action_type in ("agent.submit", "agent.give_up"):
                terminated = True
                break
        record("bounded_termination", terminated, "" if terminated else "no terminal action emitted")
    except Exception as exc:  # noqa: BLE001
        record("bounded_termination", False, str(exc))

    # Case 6: cancellation support
    try:
        await adapter.cancel()
        action = normalize_action(await adapter.next_action(None))
        record("cancellation", action.action_type in ("agent.give_up", "agent.submit"),
               f"post-cancel action: {action.action_type}")
    except Exception as exc:  # noqa: BLE001
        record("cancellation", False, str(exc))

    # Case 7: usage accounting shape
    try:
        usage = adapter.usage()
        record("usage_accounting", {"tokens", "cost_usd"} <= set(usage), str(usage))
    except Exception as exc:  # noqa: BLE001
        record("usage_accounting", False, str(exc))

    return {"passed": all(c["passed"] for c in cases), "cases": cases}
