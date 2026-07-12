"""End-to-end CLI workflows via main(argv) (PRD §12, §22 exit codes)."""
import json

import pytest

from agent_debugger.cli.main import main
from agent_debugger.reports.compare import (
    EXIT_INVALID_CONFIG,
    EXIT_OK,
)


@pytest.fixture()
def cli_workspace(tmp_path, repo_root, capsys):
    ws_dir = tmp_path / "ws"
    assert main(["init", str(ws_dir)]) == EXIT_OK
    assert main([
        "--workspace", str(ws_dir), "scenario", "add",
        str(repo_root / "scenarios" / "login-env-var"),
    ]) == EXIT_OK
    for config in ("careful-reference.yaml", "hasty-reference.yaml", "scripted-known-good.yaml"):
        assert main([
            "--workspace", str(ws_dir), "agent", "add",
            str(repo_root / "configs" / "agents" / config),
        ]) == EXIT_OK
    capsys.readouterr()
    return ws_dir


def run_json(capsys, argv):
    code = main(argv)
    output = capsys.readouterr().out
    return code, json.loads(output)


class TestCliWorkflow:
    def test_scenario_validate_and_test(self, repo_root, capsys):
        scenario = str(repo_root / "scenarios" / "login-env-var")
        assert main(["scenario", "validate", scenario]) == EXIT_OK
        assert main(["scenario", "test", scenario]) == EXIT_OK

    def test_scenario_validate_rejects_broken(self, tmp_path):
        bad = tmp_path / "broken"
        (bad / "fixtures" / "repository").mkdir(parents=True)
        (bad / "manifest.yaml").write_text("schema_version: 1.0.0\n", encoding="utf-8")
        assert main(["scenario", "validate", str(bad)]) == EXIT_INVALID_CONFIG

    def test_scenario_new_scaffolds(self, tmp_path):
        target = tmp_path / "fresh"
        assert main(["scenario", "new", "x.fresh", str(target)]) == EXIT_OK
        assert (target / "manifest.yaml").exists()

    def test_run_replay_report_compare(self, cli_workspace, capsys):
        ws = str(cli_workspace)

        code, careful = run_json(capsys, [
            "--workspace", ws, "--json", "run", "webapp.login-env-var",
            "--agent", "careful-reference", "--seed", "3",
        ])
        assert code == EXIT_OK and careful["terminal_reason"] == "success"

        code, hasty = run_json(capsys, [
            "--workspace", ws, "--json", "run", "webapp.login-env-var",
            "--agent", "hasty-reference", "--seed", "3",
        ])
        assert code == EXIT_OK and hasty["terminal_reason"] == "submitted_unsolved"

        code, replay = run_json(capsys, ["--workspace", ws, "--json", "replay", careful["run_id"]])
        assert code == EXIT_OK and replay["match"]

        assert main(["--workspace", ws, "report", careful["run_id"], "--format", "markdown"]) == EXIT_OK
        md = capsys.readouterr().out
        assert "# Run Report" in md and "success" in md

        assert main(["--workspace", ws, "report", careful["run_id"], "--format", "html"]) == EXIT_OK
        html = capsys.readouterr().out
        assert "<table>" in html

        careful_rev = None
        assert main(["--workspace", ws, "agent", "list"]) == EXIT_OK
        for row in json.loads(capsys.readouterr().out):
            if row["name"] == "careful-reference":
                careful_rev = row["revision_id"]
            if row["name"] == "hasty-reference":
                hasty_rev = row["revision_id"]

        code, regression = run_json(capsys, [
            "--workspace", ws, "--json", "compare",
            "--baseline", careful_rev, "--candidate", hasty_rev, "--gate",
        ])
        assert regression["status"] == "fail"
        assert code == regression["exit_code"] == 10  # benchmark regression

    def test_scripted_run_via_trajectory_flag(self, cli_workspace, capsys):
        code, result = run_json(capsys, [
            "--workspace", str(cli_workspace), "--json", "run", "webapp.login-env-var",
            "--agent", "scripted-known-good", "--trajectory", "known_good",
        ])
        assert code == EXIT_OK and result["terminal_reason"] == "success"
        assert result["overall_score"] == 100.0

    def test_suite_command(self, cli_workspace, repo_root, capsys):
        code, summary = run_json(capsys, [
            "--workspace", str(cli_workspace), "--json", "suite",
            str(repo_root / "scenarios" / "login-env-var"),
            str(repo_root / "scenarios" / "pagination-off-by-one"),
            "--agent", "careful-reference", "--seeds", "0,1",
        ])
        assert code == EXIT_OK
        assert summary["total"] == 4
        assert summary["infrastructure_failures"] == 0

    def test_unknown_run_errors_cleanly(self, cli_workspace):
        assert main(["--workspace", str(cli_workspace), "replay", "run-nope"]) == EXIT_INVALID_CONFIG
