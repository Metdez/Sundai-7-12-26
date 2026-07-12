"""Isolated real-environment validation (FR-029, §11.7, PRD §20).

Applies a candidate patch to the scenario's real fixture inside an
ephemeral, network-disabled, resource-limited container and runs only the
scenario-declared command arrays (no shell interpolation). Results are
labeled `real`, never merged with simulated outcomes.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agent_debugger.domain.errors import ConfigurationError, DependencyError
from agent_debugger.persistence.events import utc_now
from agent_debugger.scenario.package import ScenarioPackage


def detect_container_runtime() -> str | None:
    for runtime in ("docker", "podman"):
        if shutil.which(runtime):
            return runtime
    return None


#: stderr signatures meaning the runtime daemon itself failed — an
#: infrastructure condition, never a validation verdict (PRD §19.3).
_DAEMON_FAILURE_SIGNS = (
    "failed to connect to the docker api",
    "cannot connect to the docker daemon",
    "error during connect",
    "docker daemon is not running",
    "no such image",
    "unable to find image",
)


def _daemon_failure(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(sign in lowered for sign in _DAEMON_FAILURE_SIGNS)


def _apply_patch_to_fixture(fixture_dir: Path, changed_files: dict[str, str], final_files: dict[str, str]) -> None:
    for path, kind in changed_files.items():
        target = fixture_dir / path
        if kind == "deleted":
            if target.exists():
                target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(final_files[path], encoding="utf-8")


def run_real_validation(
    package: ScenarioPackage,
    changed_files: dict[str, str],
    final_files: dict[str, str],
    simulated_success: bool,
    runtime: str | None = None,
    memory_limit: str = "512m",
    cpu_limit: str = "1",
) -> dict[str, Any]:
    spec = package.manifest.real_validation
    if spec is None:
        raise ConfigurationError(
            f"Scenario {package.scenario_id} declares no real_validation fixture"
        )
    runtime = runtime or detect_container_runtime()
    if runtime is None:
        raise DependencyError(
            "No container runtime found (docker or podman); real validation is disabled"
        )

    started_at = utc_now()
    with tempfile.TemporaryDirectory(prefix="adbg-real-") as tmp:
        workdir = Path(tmp) / "repo"
        fixture_src = package.root / package.manifest.initial_state.fixture
        shutil.copytree(fixture_src, workdir)
        _apply_patch_to_fixture(workdir, changed_files, final_files)

        evidence: list[dict[str, Any]] = []
        overall_ok = True
        for command in [*spec.setup_commands, *spec.test_commands]:
            if not isinstance(command, list) or not all(isinstance(c, str) for c in command):
                raise ConfigurationError(f"Real-validation command must be an argv array: {command!r}")
            argv = [
                runtime, "run", "--rm",
                "--network", spec.network or "none",
                "--memory", memory_limit,
                "--cpus", cpu_limit,
                "--pids-limit", "256",
                "--read-only",
                "--tmpfs", "/tmp",
                "--security-opt", "no-new-privileges",
                "-v", f"{workdir.as_posix()}:/workspace:rw",
                "-w", "/workspace",
                spec.image,
                *command,
            ]
            try:
                proc = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=spec.timeout_seconds,
                    check=False,
                )
                exit_code = proc.returncode
                stdout, stderr = proc.stdout[-20000:], proc.stderr[-20000:]
            except subprocess.TimeoutExpired:
                exit_code, stdout, stderr = -1, "", "timeout"
            if exit_code != 0 and _daemon_failure(stderr):
                raise DependencyError(
                    "Container runtime daemon unavailable or image missing; "
                    "real validation not attempted",
                    details={"stderr": stderr[-2000:], "runtime": runtime},
                )
            evidence.append(
                {
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
            if command in spec.test_commands and exit_code != 0:
                overall_ok = False

        return {
            "kind": "real_validation",
            "label": "real",  # never merged with simulated outcome labels
            "scenario_id": package.scenario_id,
            "scenario_digest": package.digest,
            "image": spec.image,
            "runtime": runtime,
            "network": spec.network or "none",
            "started_at": started_at,
            "finished_at": utc_now(),
            "commands": evidence,
            "real_success": overall_ok,
            "simulated_success": simulated_success,
            "outcome_agreement": overall_ok == simulated_success,
            "cleanup": "container removed (--rm); workdir deleted",
        }
