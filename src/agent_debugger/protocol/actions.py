"""Canonical action and observation protocol v0.1.0 (FR-006).

Every agent framework is translated into this vocabulary by an adapter.
Actions are validated with parameter schemas per action type; malformed
actions raise ProtocolError (adapter defect) while well-formed but
disallowed actions flow to the policy engine (agent behavior).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from agent_debugger.domain.errors import ProtocolError
from agent_debugger.domain.model import SCHEMA_VERSIONS, digest_of

PROTOCOL_VERSION = SCHEMA_VERSIONS["action_protocol"]

MAX_PARAM_BYTES = 256_000  # input size limit (PRD §20 input validation)


class _FsList(BaseModel):
    path: str = "."


class _FsRead(BaseModel):
    path: str
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)


class _FsSearch(BaseModel):
    query: str = Field(min_length=1)
    glob: str | None = None
    regex: bool = False


class _PatchEdit(BaseModel):
    old_text: str
    new_text: str


class _FsPatch(BaseModel):
    path: str
    mode: str = Field(default="edit", pattern="^(edit|create|overwrite)$")
    edits: list[_PatchEdit] = Field(default_factory=list)
    content: str | None = None


class _FsDelete(BaseModel):
    path: str


class _ShellRun(BaseModel):
    command: str = Field(min_length=1)


class _TestRun(BaseModel):
    suite: str | None = None


class _LogRead(BaseModel):
    name: str


class _GitDiff(BaseModel):
    path: str | None = None


class _GitStatus(BaseModel):
    pass


class _EnvGet(BaseModel):
    name: str
    scope: str = "test"


class _EnvSet(BaseModel):
    name: str
    value: str
    scope: str = "test"


class _NetRequest(BaseModel):
    url: str
    method: str = "GET"


class _Submit(BaseModel):
    summary: str = ""


class _GiveUp(BaseModel):
    reason: str = ""


class _Hypothesis(BaseModel):
    statement: str = Field(min_length=1)


ACTION_PARAM_MODELS: dict[str, type[BaseModel]] = {
    "fs.list": _FsList,
    "fs.read": _FsRead,
    "fs.search": _FsSearch,
    "fs.patch": _FsPatch,
    "fs.delete": _FsDelete,
    "shell.run": _ShellRun,
    "test.run": _TestRun,
    "log.read": _LogRead,
    "git.diff": _GitDiff,
    "git.status": _GitStatus,
    "env.get": _EnvGet,
    "env.set": _EnvSet,
    "net.request": _NetRequest,
    "agent.submit": _Submit,
    "agent.give_up": _GiveUp,
    "agent.hypothesis": _Hypothesis,
}

ACTION_TYPES = sorted(ACTION_PARAM_MODELS)


class CanonicalAction(BaseModel):
    """A single normalized agent action."""

    action_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    thought: str | None = None  # optional stated reasoning intended for the tool loop
    protocol_version: str = PROTOCOL_VERSION

    def signature(self) -> str:
        """Stable identity for repeated-action detection."""
        return digest_of({"t": self.action_type, "p": self.params})


class Observation(BaseModel):
    """The normalized environment response returned to the agent."""

    turn: int
    action_type: str
    status: str = "ok"  # ok | error | blocked
    source: str = "deterministic"  # deterministic | model | fallback
    body: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    protocol_version: str = PROTOCOL_VERSION


def normalize_action(raw: dict[str, Any] | CanonicalAction) -> CanonicalAction:
    """Validate and normalize a proposed action.

    Raises ProtocolError (adapter defect) for structurally invalid input.
    Unknown action types are structurally valid — they become policy/state
    errors attributed to the agent, so cross-framework quirks are measurable.
    """
    if isinstance(raw, CanonicalAction):
        action = raw
    else:
        try:
            action = CanonicalAction.model_validate(raw)
        except ValidationError as exc:
            raise ProtocolError(
                "Action does not match canonical envelope",
                details={"errors": exc.errors(include_url=False)},
            ) from exc

    if len(str(action.params)) > MAX_PARAM_BYTES:
        raise ProtocolError(
            "Action parameters exceed size limit",
            details={"limit": MAX_PARAM_BYTES},
        )

    model = ACTION_PARAM_MODELS.get(action.action_type)
    if model is not None:
        try:
            validated = model.model_validate(action.params)
        except ValidationError as exc:
            raise ProtocolError(
                f"Invalid parameters for {action.action_type}",
                details={"errors": exc.errors(include_url=False)},
            ) from exc
        action = action.model_copy(update={"params": validated.model_dump(exclude_none=True)})
    return action


def tool_contract() -> list[dict[str, Any]]:
    """JSON-schema style tool contract sent to agents (FR-006 acceptance)."""
    tools = []
    for name, model in sorted(ACTION_PARAM_MODELS.items()):
        tools.append(
            {
                "name": name,
                "parameters": model.model_json_schema(),
                "protocol_version": PROTOCOL_VERSION,
            }
        )
    return tools
