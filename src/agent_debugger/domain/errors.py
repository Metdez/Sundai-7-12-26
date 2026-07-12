"""Typed error model (PRD §25, §22).

Errors carry category, retryability, actor attribution, user message, technical
details, and evidence references. Infrastructure errors never silently become
agent deductions: orchestration checks `category` before scoring.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    AGENT_BEHAVIOR = "agent_behavior"
    ADAPTER_DEFECT = "adapter_defect"
    SCENARIO_DEFECT = "scenario_defect"
    SIMULATOR_DEFECT = "simulator_defect"
    SCORER_DEFECT = "scorer_defect"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    INFRASTRUCTURE = "infrastructure"
    AUTHORIZATION = "authorization"
    UNKNOWN = "unknown"


#: Categories that must never be attributed to the agent when scoring.
NON_AGENT_CATEGORIES = frozenset(
    {
        ErrorCategory.ADAPTER_DEFECT,
        ErrorCategory.SCENARIO_DEFECT,
        ErrorCategory.SIMULATOR_DEFECT,
        ErrorCategory.SCORER_DEFECT,
        ErrorCategory.CONFIGURATION,
        ErrorCategory.DEPENDENCY,
        ErrorCategory.INFRASTRUCTURE,
        ErrorCategory.AUTHORIZATION,
    }
)


class AgentDebuggerError(Exception):
    """Base typed error for the whole product."""

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        retryable: bool = False,
        actor: str = "system",
        user_message: str | None = None,
        details: dict[str, Any] | None = None,
        evidence: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.retryable = retryable
        self.actor = actor
        self.user_message = user_message or message
        self.details = details or {}
        self.evidence = evidence or []

    def to_payload(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "actor": self.actor,
            "user_message": self.user_message,
            "details": self.details,
            "evidence": self.evidence,
        }


class ConfigurationError(AgentDebuggerError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.CONFIGURATION)
        super().__init__(message, **kw)


class ScenarioError(AgentDebuggerError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.SCENARIO_DEFECT)
        super().__init__(message, **kw)


class ProtocolError(AgentDebuggerError):
    """Malformed canonical actions or observations (attributed to adapter)."""

    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.ADAPTER_DEFECT)
        kw.setdefault("actor", "adapter")
        super().__init__(message, **kw)


class PolicyViolation(AgentDebuggerError):
    """The agent proposed an action the policy blocks. Attributed to the agent."""

    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.AGENT_BEHAVIOR)
        kw.setdefault("actor", "agent")
        super().__init__(message, **kw)


class SimulatorError(AgentDebuggerError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.SIMULATOR_DEFECT)
        kw.setdefault("actor", "simulator")
        super().__init__(message, **kw)


class DependencyError(AgentDebuggerError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.DEPENDENCY)
        kw.setdefault("retryable", True)
        super().__init__(message, **kw)


class InfrastructureError(AgentDebuggerError):
    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.INFRASTRUCTURE)
        super().__init__(message, **kw)


class IntegrityError(AgentDebuggerError):
    """Hash chain or artifact digest mismatch."""

    def __init__(self, message: str, **kw: Any) -> None:
        kw.setdefault("category", ErrorCategory.INFRASTRUCTURE)
        super().__init__(message, **kw)
