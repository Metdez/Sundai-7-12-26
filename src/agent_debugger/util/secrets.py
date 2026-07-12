"""Secret reference resolution and redaction (FR-032, PRD §20).

Configuration stores references such as ``env:MY_KEY``; values are resolved
just-in-time and never persisted. `redact` strips known secret shapes from
any text before it reaches logs, events, or artifacts.
"""
from __future__ import annotations

import os
import re

from agent_debugger.domain.errors import ConfigurationError

_SECRET_VALUE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}\b"),
    re.compile(r"(?i)\b(api[_-]?key|password|secret|token)\s*[=:]\s*['\"]?[^\s'\"]{8,}"),
]

REDACTED = "[REDACTED]"


def resolve_secret_ref(ref: str | None) -> str | None:
    """Resolve ``env:NAME`` (or plain ``NAME`` as env fallback) to a value."""
    if not ref:
        return None
    if ref.startswith("env:"):
        name = ref.split(":", 1)[1]
        value = os.environ.get(name)
        if value is None:
            raise ConfigurationError(
                f"Secret reference {ref!r} is not set in the environment",
                details={"ref": ref},
            )
        return value
    if ref.startswith("literal:"):
        # Only for tests; never write literals into stored configuration.
        return ref.split(":", 1)[1]
    raise ConfigurationError(f"Unsupported secret reference scheme: {ref!r}")


def redact(text: str, extra_values: list[str] | None = None) -> str:
    for value in extra_values or []:
        if value:
            text = text.replace(value, REDACTED)
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text
