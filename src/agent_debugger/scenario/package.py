"""Scenario package schema, loading, digest, and validation (FR-001, FR-002, §11.1)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from agent_debugger.domain.errors import ScenarioError
from agent_debugger.domain.model import SCHEMA_VERSIONS, digest_of, sha256_hex
from agent_debugger.protocol.actions import ACTION_TYPES
from agent_debugger.scenario.conditions import condition_references
from agent_debugger.scenario.state import AuthoritativeState
from agent_debugger.scenario.vfs import VirtualFileSystem

SCENARIO_SCHEMA_VERSION = SCHEMA_VERSIONS["scenario"]


class ShellRule(BaseModel):
    pattern: str
    output: str = ""
    exit_code: int = 0


class TestSuiteSpec(BaseModel):
    pass_when: list[dict[str, Any]]
    pass_output: str = "All tests passed."
    fail_output: str = "Tests failed."


class RendererSpec(BaseModel):
    type: str = Field(default="deterministic", pattern="^(deterministic|qwen-agentworld|hybrid)$")
    provider: str | None = None
    deterministic_fallback: bool = True
    protected_facts: list[str] = Field(default_factory=list)


class PerturbationSpec(BaseModel):
    kind: str = Field(pattern="^(tool_failure|noisy_output)$")
    action_types: list[str] = Field(default_factory=list)
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str = "transient tool failure"


class RealValidationSpec(BaseModel):
    image: str
    setup_commands: list[list[str]] = Field(default_factory=list)
    test_commands: list[list[str]]
    network: str = "none"
    timeout_seconds: int = 600


class InitialStateSpec(BaseModel):
    fixture: str = "fixtures/repository"
    env: dict[str, dict[str, str]] = Field(default_factory=dict)
    hidden_facts: dict[str, Any] = Field(default_factory=dict)
    logs: dict[str, str] = Field(default_factory=dict)


class ScenarioManifest(BaseModel):
    schema_version: str
    scenario_id: str
    version: str
    title: str
    task: str
    difficulty: str = "beginner"
    language: str | None = None
    framework: str | None = None
    failure_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    initial_state: InitialStateSpec
    allowed_actions: list[str]
    shell_allowlist: list[ShellRule] = Field(default_factory=list)
    test_suites: dict[str, TestSuiteSpec] = Field(default_factory=dict)
    success_predicates: list[dict[str, Any]]
    failure_predicates: list[dict[str, Any]] = Field(default_factory=list)
    renderer: RendererSpec = Field(default_factory=RendererSpec)
    scoring_profile: str = "coding-debug-v1"
    perturbations: list[PerturbationSpec] = Field(default_factory=list)
    trajectories: dict[str, str] = Field(default_factory=dict)
    real_validation: RealValidationSpec | None = None
    action_policy_overrides: dict[str, str] = Field(default_factory=dict)
    par_actions: int = 12
    author_notes: str | None = None


#: Actions that are always available to the agent even if not listed.
IMPLICIT_ACTIONS = {"agent.submit", "agent.give_up", "agent.hypothesis"}

_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
]
_HOST_PATH_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]:\\\\|/home/[a-z]|/etc/|/Users/)")


class ScenarioPackage:
    def __init__(self, root: Path, manifest: ScenarioManifest, digest: str) -> None:
        self.root = root
        self.manifest = manifest
        self.digest = digest

    @property
    def scenario_id(self) -> str:
        return self.manifest.scenario_id

    @property
    def version(self) -> str:
        return self.manifest.version

    def fixture_files(self) -> dict[str, str]:
        fixture_dir = self.root / self.manifest.initial_state.fixture
        if not fixture_dir.is_dir():
            raise ScenarioError(
                f"Fixture directory not found: {self.manifest.initial_state.fixture}",
                details={"scenario": self.scenario_id},
            )
        files: dict[str, str] = {}
        for path in sorted(fixture_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(fixture_dir).as_posix()
                files[rel] = path.read_text(encoding="utf-8")
        return files

    def build_initial_state(self) -> AuthoritativeState:
        return AuthoritativeState(
            files=VirtualFileSystem(self.fixture_files()),
            env=self.manifest.initial_state.env,
            hidden_facts=self.manifest.initial_state.hidden_facts,
            logs=self.manifest.initial_state.logs,
            test_suites=sorted(self.manifest.test_suites),
        )

    def load_trajectory(self, name: str) -> list[dict[str, Any]]:
        rel = self.manifest.trajectories.get(name)
        if rel is None:
            raise ScenarioError(f"Trajectory {name!r} not declared in manifest")
        path = self.root / rel
        if not path.is_file():
            raise ScenarioError(f"Trajectory file missing: {rel}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ScenarioError(f"Trajectory {name!r} must be a list of actions")
        return data


def compute_package_digest(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": sha256_hex(path.read_bytes()),
                }
            )
    return digest_of(entries)


def load_package(root: str | Path) -> ScenarioPackage:
    root = Path(root)
    manifest_path = root / "manifest.yaml"
    if not manifest_path.is_file():
        raise ScenarioError(f"manifest.yaml not found in {root}")
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"manifest.yaml is not valid YAML: {exc}") from exc
    try:
        manifest = ScenarioManifest.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError(
            "Scenario manifest failed schema validation",
            details={"errors": exc.errors(include_url=False)},
        ) from exc
    return ScenarioPackage(root=root, manifest=manifest, digest=compute_package_digest(root))


def _iter_predicate_conditions(predicates: list[dict[str, Any]]):
    for item in predicates:
        if "condition" in item:
            yield item["condition"]


def validate_package(pkg: ScenarioPackage) -> dict[str, list[str]]:
    """Structural validation (§11.1 steps 1-3, 6). Returns {errors, warnings}."""
    errors: list[str] = []
    warnings: list[str] = []
    m = pkg.manifest

    if m.schema_version != SCENARIO_SCHEMA_VERSION:
        warnings.append(
            f"schema_version {m.schema_version} != supported {SCENARIO_SCHEMA_VERSION}"
        )

    known = set(ACTION_TYPES)
    for action in m.allowed_actions:
        if action not in known:
            errors.append(f"allowed_actions: unknown action type {action!r}")

    # fixture presence and file references
    try:
        files = pkg.fixture_files()
    except ScenarioError as exc:
        errors.append(str(exc.message))
        files = {}

    suite_names = set(m.test_suites)
    all_conditions: list[dict[str, Any]] = []
    for suite in m.test_suites.values():
        all_conditions.extend(suite.pass_when)
    all_conditions.extend(_iter_predicate_conditions(m.success_predicates))
    all_conditions.extend(_iter_predicate_conditions(m.failure_predicates))

    for cond in all_conditions:
        try:
            for kind, ref in condition_references(cond):
                if kind == "suite" and ref not in suite_names:
                    errors.append(f"condition references unknown test suite {ref!r}")
        except Exception as exc:  # noqa: BLE001 - collect as validation error
            errors.append(f"invalid condition {cond!r}: {exc}")

    for item in m.success_predicates:
        if "test_suite" in item:
            if item["test_suite"] not in suite_names:
                errors.append(f"success predicate references unknown suite {item['test_suite']!r}")
            if item.get("status") not in ("pass", "fail"):
                errors.append(f"success predicate for {item.get('test_suite')} needs status pass|fail")
        elif "file_scope" in item:
            if "max_changed_files" not in item["file_scope"]:
                errors.append("file_scope predicate requires max_changed_files")
        elif "condition" not in item:
            errors.append(f"unrecognized success predicate shape: {sorted(item)}")

    for item in m.failure_predicates:
        if not ({"destructive_action_attempted", "external_action_attempted", "condition"} & set(item)):
            errors.append(f"unrecognized failure predicate shape: {sorted(item)}")

    if not m.success_predicates:
        errors.append("scenario declares no success predicates")
    if "test.run" not in m.allowed_actions and any("test_suite" in p for p in m.success_predicates):
        warnings.append("success depends on tests but test.run is not an allowed action")

    for rule in m.shell_allowlist:
        try:
            re.compile(rule.pattern)
        except re.error as exc:
            errors.append(f"shell_allowlist pattern {rule.pattern!r} invalid: {exc}")

    for name, rel in m.trajectories.items():
        if not (pkg.root / rel).is_file():
            errors.append(f"trajectory {name!r} file missing: {rel}")

    # safety lint (§11.1 step 6)
    lint_targets: dict[str, str] = {"manifest.yaml": (pkg.root / "manifest.yaml").read_text(encoding="utf-8")}
    lint_targets.update({f"fixture:{p}": c for p, c in files.items()})
    for label, content in lint_targets.items():
        for pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(f"safety lint: credential-like material in {label}")
        if _HOST_PATH_PATTERN.search(content):
            warnings.append(f"safety lint: host-like path reference in {label}")

    return {"errors": errors, "warnings": warnings}


NEW_SCENARIO_TEMPLATE = """schema_version: {schema_version}
scenario_id: {scenario_id}
version: 0.1.0
title: TODO one-line failure summary
difficulty: beginner
tags: []
task: TODO describe the debugging task given to the agent.
initial_state:
  fixture: fixtures/repository
  env:
    test: {{}}
  hidden_facts:
    root_cause: TODO
allowed_actions:
  - fs.list
  - fs.read
  - fs.search
  - fs.patch
  - shell.run
  - test.run
  - git.diff
  - git.status
test_suites:
  tests/test_example.py:
    pass_when:
      - file_contains:
          path: src/example.py
          text: TODO
    pass_output: "1 passed"
    fail_output: "1 failed: TODO error message the agent sees"
success_predicates:
  - test_suite: tests/test_example.py
    status: pass
  - file_scope:
      max_changed_files: 2
failure_predicates:
  - destructive_action_attempted: true
renderer:
  type: deterministic
scoring_profile: coding-debug-v1
"""


def scaffold_scenario(directory: Path, scenario_id: str) -> Path:
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "fixtures" / "repository").mkdir(parents=True)
    manifest = NEW_SCENARIO_TEMPLATE.format(
        schema_version=SCENARIO_SCHEMA_VERSION, scenario_id=scenario_id
    )
    (directory / "manifest.yaml").write_text(manifest, encoding="utf-8")
    (directory / "fixtures" / "repository" / "README.md").write_text(
        f"# {scenario_id}\n\nFictional repository fixture.\n", encoding="utf-8"
    )
    return directory
