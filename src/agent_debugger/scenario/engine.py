"""Authoritative state transition engine (FR-003, shared contract #3).

Every canonical action is applied here — never by the renderer, never on the
host. Results are structured data; renderers turn them into text. Replaying
the same actions from the same initial state yields the same state hashes.
"""
from __future__ import annotations

import difflib
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from agent_debugger.protocol.actions import CanonicalAction
from agent_debugger.scenario.conditions import evaluate_condition
from agent_debugger.scenario.package import ScenarioManifest
from agent_debugger.scenario.state import AuthoritativeState
from agent_debugger.scenario.templating import render_template
from agent_debugger.scenario.vfs import PathViolation

MAX_PERTURBED_TURNS = 500


@dataclass
class TransitionResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None
    changed_paths: list[str] = field(default_factory=list)
    state_hash: str = ""
    perturbed: bool = False
    terminal_hint: str | None = None  # "submit" | "give_up"


class StateEngine:
    def __init__(self, manifest: ScenarioManifest, state: AuthoritativeState, seed: int = 0) -> None:
        self.manifest = manifest
        self.state = state
        self.seed = seed
        self.baseline_files = state.files.to_dict()
        self._perturbation_draws = self._compute_perturbation_schedule(seed)
        self._handlers: dict[str, Callable[[CanonicalAction, int], TransitionResult]] = {
            "fs.list": self._fs_list,
            "fs.read": self._fs_read,
            "fs.search": self._fs_search,
            "fs.patch": self._fs_patch,
            "fs.delete": self._fs_delete,
            "shell.run": self._shell_run,
            "test.run": self._test_run,
            "log.read": self._log_read,
            "git.diff": self._git_diff,
            "git.status": self._git_status,
            "env.get": self._env_get,
            "env.set": self._env_set,
            "net.request": self._net_request,
            "agent.submit": self._agent_submit,
            "agent.give_up": self._agent_give_up,
            "agent.hypothesis": self._agent_hypothesis,
        }

    # ------------------------------------------------------------------
    def _compute_perturbation_schedule(self, seed: int) -> list[list[float]]:
        """FR-013: the same seed produces the same perturbation schedule."""
        rng = random.Random(f"perturb:{seed}")
        return [
            [rng.random() for _ in self.manifest.perturbations]
            for _ in range(MAX_PERTURBED_TURNS)
        ]

    def _perturbation_for(self, action_type: str, turn: int):
        if turn >= MAX_PERTURBED_TURNS:
            return None
        for idx, rule in enumerate(self.manifest.perturbations):
            if rule.action_types and action_type not in rule.action_types:
                continue
            if self._perturbation_draws[turn][idx] < rule.probability:
                return rule
        return None

    # ------------------------------------------------------------------
    def apply(self, action: CanonicalAction, turn: int) -> TransitionResult:
        handler = self._handlers.get(action.action_type)
        if handler is None:
            result = TransitionResult(
                ok=False,
                error={"code": "unknown_action", "message": f"Unknown action {action.action_type}"},
            )
        else:
            rule = self._perturbation_for(action.action_type, turn)
            if rule is not None and rule.kind == "tool_failure":
                result = TransitionResult(
                    ok=False,
                    perturbed=True,
                    error={"code": "tool_failure", "message": rule.message},
                )
            else:
                try:
                    result = handler(action, turn)
                except PathViolation as exc:
                    result = TransitionResult(
                        ok=False,
                        error={"code": "path_violation", "message": exc.message},
                    )
                except FileNotFoundError as exc:
                    result = TransitionResult(
                        ok=False,
                        error={"code": "not_found", "message": f"No such file: {exc}"},
                    )
        self.state.transition_counter += 1
        result.state_hash = self.state.state_hash()
        return result

    # -- read-only handlers ---------------------------------------------
    def _fs_list(self, action: CanonicalAction, turn: int) -> TransitionResult:
        entries = self.state.files.list_dir(action.params.get("path", "."))
        return TransitionResult(ok=True, data={"entries": entries, "path": action.params.get("path", ".")})

    def _fs_read(self, action: CanonicalAction, turn: int) -> TransitionResult:
        content = self.state.files.read(action.params["path"])
        lines = content.splitlines()
        start = action.params.get("start_line") or 1
        end = action.params.get("end_line") or len(lines)
        window = lines[start - 1 : end]
        return TransitionResult(
            ok=True,
            data={
                "path": action.params["path"],
                "content": "\n".join(window),
                "total_lines": len(lines),
                "start_line": start,
            },
        )

    def _fs_search(self, action: CanonicalAction, turn: int) -> TransitionResult:
        try:
            matches = self.state.files.search(
                action.params["query"],
                glob=action.params.get("glob"),
                regex=action.params.get("regex", False),
            )
        except re.error as exc:
            return TransitionResult(
                ok=False, error={"code": "bad_regex", "message": f"Invalid regex: {exc}"}
            )
        return TransitionResult(ok=True, data={"query": action.params["query"], "matches": matches})

    def _log_read(self, action: CanonicalAction, turn: int) -> TransitionResult:
        name = action.params["name"]
        if name not in self.state.logs:
            return TransitionResult(
                ok=False,
                error={"code": "not_found", "message": f"No such log: {name}"},
            )
        return TransitionResult(
            ok=True,
            data={"name": name, "content": render_template(self.state.logs[name], self.state)},
        )

    def _git_status(self, action: CanonicalAction, turn: int) -> TransitionResult:
        return TransitionResult(ok=True, data={"status": self.state.git_status()})

    def _git_diff(self, action: CanonicalAction, turn: int) -> TransitionResult:
        only = action.params.get("path")
        diffs: list[str] = []
        changes = self.state.changed_files()
        for path in sorted(changes):
            if only and path != only:
                continue
            before = self.baseline_files.get(path, "")
            after = self.state.files.read(path) if self.state.files.exists(path) else ""
            diff = difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
            diffs.append("".join(diff))
        return TransitionResult(ok=True, data={"diff": "".join(diffs), "changed": changes})

    def _env_get(self, action: CanonicalAction, turn: int) -> TransitionResult:
        name = action.params["name"]
        scope = action.params.get("scope", "test")
        value = self.state.env_get(name, scope)
        return TransitionResult(
            ok=True, data={"name": name, "scope": scope, "value": value, "set": value is not None}
        )

    # -- write handlers ---------------------------------------------------
    def _fs_patch(self, action: CanonicalAction, turn: int) -> TransitionResult:
        path = action.params["path"]
        mode = action.params.get("mode", "edit")
        edits = action.params.get("edits", [])
        content = action.params.get("content")

        if mode in ("create", "overwrite"):
            if content is None:
                return TransitionResult(
                    ok=False,
                    error={"code": "missing_content", "message": f"mode={mode} requires content"},
                )
            if mode == "create" and self.state.files.exists(path):
                return TransitionResult(
                    ok=False,
                    error={"code": "already_exists", "message": f"{path} already exists"},
                )
            norm = self.state.files.write(path, content)
            return TransitionResult(ok=True, data={"path": norm, "mode": mode}, changed_paths=[norm])

        if not edits:
            return TransitionResult(
                ok=False, error={"code": "empty_patch", "message": "edit mode requires edits"}
            )
        current = self.state.files.read(path)
        applied = current
        for edit in edits:
            old = edit["old_text"]
            if old not in applied:
                return TransitionResult(
                    ok=False,
                    error={
                        "code": "patch_mismatch",
                        "message": f"old_text not found in {path}",
                    },
                )
            applied = applied.replace(old, edit["new_text"], 1)
        norm = self.state.files.write(path, applied)
        return TransitionResult(
            ok=True, data={"path": norm, "mode": "edit", "edits": len(edits)}, changed_paths=[norm]
        )

    def _fs_delete(self, action: CanonicalAction, turn: int) -> TransitionResult:
        # Reaching the engine means policy explicitly allowed it for this scenario.
        norm = self.state.files.delete(action.params["path"])
        return TransitionResult(ok=True, data={"path": norm, "deleted": True}, changed_paths=[norm])

    def _env_set(self, action: CanonicalAction, turn: int) -> TransitionResult:
        name = action.params["name"]
        scope = action.params.get("scope", "test")
        self.state.env_set(name, action.params["value"], scope)
        return TransitionResult(ok=True, data={"name": name, "scope": scope, "set": True})

    # -- simulated execution ----------------------------------------------
    def _shell_run(self, action: CanonicalAction, turn: int) -> TransitionResult:
        command = action.params["command"].strip()
        for rule in self.manifest.shell_allowlist:
            if re.fullmatch(rule.pattern, command):
                stdout = render_template(rule.output, self.state)
                return TransitionResult(
                    ok=True,
                    data={"command": command, "stdout": stdout, "exit_code": rule.exit_code},
                )
        return TransitionResult(
            ok=False,
            error={
                "code": "command_not_allowlisted",
                "message": f"Command not available in this scenario: {command}",
            },
        )

    def _test_run(self, action: CanonicalAction, turn: int) -> TransitionResult:
        requested = action.params.get("suite")
        suites = [requested] if requested else sorted(self.manifest.test_suites)
        if requested and requested not in self.manifest.test_suites:
            return TransitionResult(
                ok=False,
                error={"code": "unknown_suite", "message": f"Unknown test suite: {requested}"},
            )
        results = {}
        outputs = []
        for name in suites:
            spec = self.manifest.test_suites[name]
            passed = all(evaluate_condition(c, self.state) for c in spec.pass_when)
            status = "pass" if passed else "fail"
            self.state.test_state[name] = {"status": status, "last_run_turn": turn}
            output = render_template(spec.pass_output if passed else spec.fail_output, self.state)
            results[name] = status
            outputs.append(f"$ pytest {name}\n{output}")
        return TransitionResult(
            ok=True,
            data={"results": results, "output": "\n\n".join(outputs)},
        )

    # -- gated / terminal --------------------------------------------------
    def _net_request(self, action: CanonicalAction, turn: int) -> TransitionResult:
        # Policy blocks external actions by default; if a scenario allows them,
        # they still never leave the simulation.
        return TransitionResult(
            ok=False,
            error={"code": "network_unavailable", "message": "Outbound network is disabled"},
        )

    def _agent_submit(self, action: CanonicalAction, turn: int) -> TransitionResult:
        return TransitionResult(
            ok=True, data={"summary": action.params.get("summary", "")}, terminal_hint="submit"
        )

    def _agent_give_up(self, action: CanonicalAction, turn: int) -> TransitionResult:
        return TransitionResult(
            ok=True, data={"reason": action.params.get("reason", "")}, terminal_hint="give_up"
        )

    def _agent_hypothesis(self, action: CanonicalAction, turn: int) -> TransitionResult:
        return TransitionResult(ok=True, data={"statement": action.params.get("statement", "")})

    # -- terminal predicates -------------------------------------------------
    def success_satisfied(self) -> bool:
        for item in self.manifest.success_predicates:
            if "test_suite" in item:
                entry = self.state.test_state.get(item["test_suite"])
                if entry is None or entry["status"] != item["status"]:
                    return False
            elif "file_scope" in item:
                limit = int(item["file_scope"]["max_changed_files"])
                if len(self.state.changed_files()) > limit:
                    return False
            elif "condition" in item:
                if not evaluate_condition(item["condition"], self.state):
                    return False
        return True

    def failure_satisfied(self) -> bool:
        for item in self.manifest.failure_predicates:
            if "destructive_action_attempted" in item:
                if self.state.destructive_attempted is bool(item["destructive_action_attempted"]):
                    return True
            elif "external_action_attempted" in item:
                if self.state.external_attempted is bool(item["external_action_attempted"]):
                    return True
            elif "condition" in item:
                if evaluate_condition(item["condition"], self.state):
                    return True
        return False
