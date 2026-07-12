"""Adapter construction from immutable agent revisions."""
from __future__ import annotations

from typing import Any

from agent_debugger.adapters.openai_compat import OpenAICompatAdapter
from agent_debugger.adapters.reference import ReferenceHeuristicAgent
from agent_debugger.adapters.scripted import ScriptedAgent
from agent_debugger.domain.errors import ConfigurationError
from agent_debugger.domain.model import AgentRevision

ADAPTER_IDS = ("scripted", "reference-heuristic", "openai-compat")


def build_adapter(revision: AgentRevision, trajectory: list[dict[str, Any]] | None = None):
    if revision.adapter_id == "scripted":
        return ScriptedAgent(trajectory or revision.behavior.get("trajectory", []))
    if revision.adapter_id == "reference-heuristic":
        return ReferenceHeuristicAgent(revision.behavior)
    if revision.adapter_id == "openai-compat":
        if not revision.endpoint:
            raise ConfigurationError("openai-compat adapter requires an endpoint")
        return OpenAICompatAdapter(
            endpoint=revision.endpoint,
            model=revision.model_identifier,
            system_prompt=revision.behavior.get("system_prompt", "You are a debugging agent."),
            api_key_ref=revision.api_key_ref,
            **revision.generation_settings,
        )
    raise ConfigurationError(
        f"Unknown adapter_id {revision.adapter_id!r}; supported: {ADAPTER_IDS}"
    )
