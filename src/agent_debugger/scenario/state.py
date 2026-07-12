"""Authoritative scenario state (PRD §15.2).

The single source of truth for the fictional repository and environment.
State hashes make every transition replayable and comparable (FR-003).
"""
from __future__ import annotations

from typing import Any

from agent_debugger.domain.model import digest_of
from agent_debugger.scenario.vfs import VirtualFileSystem

STATE_SCHEMA_VERSION = "0.1.0"


class AuthoritativeState:
    def __init__(
        self,
        files: VirtualFileSystem,
        env: dict[str, dict[str, str]] | None = None,
        hidden_facts: dict[str, Any] | None = None,
        logs: dict[str, str] | None = None,
        test_suites: list[str] | None = None,
    ) -> None:
        self.files = files
        self.env: dict[str, dict[str, str]] = {k: dict(v) for k, v in (env or {}).items()}
        self.hidden_facts = dict(hidden_facts or {})
        self.logs = dict(logs or {})
        self.test_state: dict[str, dict[str, Any]] = {
            suite: {"status": "not_run", "last_run_turn": None} for suite in (test_suites or [])
        }
        self.transition_counter = 0
        self.destructive_attempted = False
        self.external_attempted = False
        self.privileged_attempted = False
        self.baseline_digests = files.digests()

    # -- derived facts -----------------------------------------------------
    def changed_files(self) -> dict[str, str]:
        """path -> change kind (modified/created/deleted) vs the initial fixture."""
        current = self.files.digests()
        changes: dict[str, str] = {}
        for path, digest in current.items():
            if path not in self.baseline_digests:
                changes[path] = "created"
            elif self.baseline_digests[path] != digest:
                changes[path] = "modified"
        for path in self.baseline_digests:
            if path not in current:
                changes[path] = "deleted"
        return changes

    def git_status(self) -> dict[str, list[str]]:
        changes = self.changed_files()
        return {
            "modified": sorted(p for p, k in changes.items() if k == "modified"),
            "created": sorted(p for p, k in changes.items() if k == "created"),
            "deleted": sorted(p for p, k in changes.items() if k == "deleted"),
        }

    def env_get(self, name: str, scope: str = "test") -> str | None:
        return self.env.get(scope, {}).get(name)

    def env_set(self, name: str, value: str, scope: str = "test") -> None:
        self.env.setdefault(scope, {})[name] = value

    # -- hashing / snapshots -------------------------------------------------
    def state_hash(self) -> str:
        return digest_of(
            {
                "schema": STATE_SCHEMA_VERSION,
                "files": self.files.digests(),
                "env": self.env,
                "test_state": {
                    k: {"status": v["status"]} for k, v in sorted(self.test_state.items())
                },
                "flags": {
                    "destructive": self.destructive_attempted,
                    "external": self.external_attempted,
                    "privileged": self.privileged_attempted,
                },
                "transitions": self.transition_counter,
            }
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "files": self.files.to_dict(),
            "env": self.env,
            "hidden_facts": self.hidden_facts,
            "logs": self.logs,
            "test_state": self.test_state,
            "transition_counter": self.transition_counter,
            "flags": {
                "destructive": self.destructive_attempted,
                "external": self.external_attempted,
                "privileged": self.privileged_attempted,
            },
            "baseline_digests": self.baseline_digests,
            "state_hash": self.state_hash(),
        }

    @classmethod
    def from_snapshot(cls, snap: dict[str, Any]) -> "AuthoritativeState":
        state = cls(
            files=VirtualFileSystem.from_dict(snap["files"]),
            env=snap.get("env", {}),
            hidden_facts=snap.get("hidden_facts", {}),
            logs=snap.get("logs", {}),
        )
        state.test_state = snap.get("test_state", {})
        state.transition_counter = snap.get("transition_counter", 0)
        flags = snap.get("flags", {})
        state.destructive_attempted = flags.get("destructive", False)
        state.external_attempted = flags.get("external", False)
        state.privileged_attempted = flags.get("privileged", False)
        state.baseline_digests = snap.get("baseline_digests", state.files.digests())
        return state
