"""Declarative condition DSL for test suites and predicates.

Per ADR "No arbitrary scenario code": scenarios declare conditions from this
allowlisted vocabulary; the core evaluates them deterministically against
authoritative state. Adding a condition type is a core change with tests.
"""
from __future__ import annotations

import re
from typing import Any

from agent_debugger.domain.errors import ScenarioError
from agent_debugger.scenario.state import AuthoritativeState


def evaluate_condition(cond: dict[str, Any], state: AuthoritativeState) -> bool:
    if not isinstance(cond, dict) or len(cond) != 1:
        raise ScenarioError(f"Condition must be a single-key mapping: {cond!r}")
    kind, spec = next(iter(cond.items()))

    if kind == "all_of":
        return all(evaluate_condition(c, state) for c in spec)
    if kind == "any_of":
        return any(evaluate_condition(c, state) for c in spec)
    if kind == "not":
        return not evaluate_condition(spec, state)

    if kind == "env_var_set":
        return bool(state.env_get(spec["name"], spec.get("scope", "test")))
    if kind == "env_var_equals":
        return state.env_get(spec["name"], spec.get("scope", "test")) == spec["value"]
    if kind == "file_exists":
        return state.files.exists(spec["path"])
    if kind == "file_contains":
        try:
            return spec["text"] in state.files.read(spec["path"])
        except FileNotFoundError:
            return False
    if kind == "file_regex":
        try:
            return re.search(spec["pattern"], state.files.read(spec["path"])) is not None
        except FileNotFoundError:
            return False
    if kind == "file_absent":
        return not state.files.exists(spec["path"])
    if kind == "max_changed_files":
        return len(state.changed_files()) <= int(spec)
    if kind == "test_suite_status":
        entry = state.test_state.get(spec["suite"])
        return entry is not None and entry["status"] == spec["status"]
    if kind == "destructive_action_attempted":
        return state.destructive_attempted is bool(spec)
    if kind == "external_action_attempted":
        return state.external_attempted is bool(spec)

    raise ScenarioError(f"Unknown condition type: {kind}")


def condition_references(cond: dict[str, Any]) -> list[tuple[str, str]]:
    """(kind, reference) pairs used by scenario validation."""
    kind, spec = next(iter(cond.items()))
    if kind in ("all_of", "any_of"):
        refs: list[tuple[str, str]] = []
        for child in spec:
            refs.extend(condition_references(child))
        return refs
    if kind == "not":
        return condition_references(spec)
    if kind in ("file_exists", "file_contains", "file_regex", "file_absent"):
        return [("file", spec["path"])]
    if kind in ("env_var_set", "env_var_equals"):
        return [("env", spec["name"])]
    if kind == "test_suite_status":
        return [("suite", spec["suite"])]
    return []
