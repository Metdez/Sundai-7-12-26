"""Deterministic template rendering for scenario-authored outputs.

Supported placeholders (all resolve from authoritative state only):
  {{env:SCOPE:NAME}}            -> value or empty string
  {{env:SCOPE:NAME|default}}    -> value or default
  {{env_dump:SCOPE}}            -> sorted KEY=VALUE lines
  {{file:PATH}}                 -> file content or <missing:PATH>
  {{hidden:KEY}}                -> hidden fact (for authored logs/hints)
"""
from __future__ import annotations

import re

from agent_debugger.scenario.state import AuthoritativeState

_PLACEHOLDER = re.compile(r"\{\{([a-z_]+):([^}|]*)(?:\|([^}]*))?\}\}")


def render_template(text: str, state: AuthoritativeState) -> str:
    def _sub(match: re.Match[str]) -> str:
        kind, arg, default = match.group(1), match.group(2), match.group(3) or ""
        if kind == "env":
            scope, _, name = arg.partition(":")
            value = state.env_get(name, scope)
            return value if value is not None else default
        if kind == "env_dump":
            scope_vars = state.env.get(arg, {})
            return "\n".join(f"{k}={v}" for k, v in sorted(scope_vars.items()))
        if kind == "file":
            try:
                return state.files.read(arg)
            except (FileNotFoundError, Exception):
                return f"<missing:{arg}>"
        if kind == "hidden":
            return str(state.hidden_facts.get(arg, default))
        return match.group(0)

    return _PLACEHOLDER.sub(_sub, text)
