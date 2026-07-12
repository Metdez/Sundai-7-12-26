import pytest
import yaml

from agent_debugger.domain.errors import ScenarioError
from agent_debugger.domain.model import SCHEMA_VERSIONS
from agent_debugger.reports.compare import (
    EXIT_BENCHMARK_REGRESSION,
    EXIT_OK,
    EXIT_SAFETY_REGRESSION,
    compare_run_sets,
    evaluate_regression,
)
from agent_debugger.scenario.package import ScenarioManifest, load_package, validate_package

MINIMAL = {
    "schema_version": "1.0.0",
    "scenario_id": "x.min",
    "version": "0.1.0",
    "title": "t",
    "task": "do it",
    "initial_state": {"fixture": "fixtures/repository"},
    "allowed_actions": ["fs.read", "test.run"],
    "test_suites": {
        "tests/t.py": {"pass_when": [{"file_exists": {"path": "ok"}}]}
    },
    "success_predicates": [{"test_suite": "tests/t.py", "status": "pass"}],
}


class TestManifestSchema:
    def test_minimal_valid(self):
        manifest = ScenarioManifest.model_validate(MINIMAL)
        assert manifest.renderer.type == "deterministic"
        assert manifest.scoring_profile == "coding-debug-v1"

    @pytest.mark.parametrize("missing", ["scenario_id", "version", "task", "success_predicates"])
    def test_required_fields(self, missing):
        data = {k: v for k, v in MINIMAL.items() if k != missing}
        with pytest.raises(Exception):
            ScenarioManifest.model_validate(data)

    def test_prd_sample_manifest_loads(self, login_package):
        m = login_package.manifest
        assert m.scenario_id == "webapp.login-env-var"
        assert m.schema_version == SCHEMA_VERSIONS["scenario"]
        assert {"fs.list", "fs.read", "fs.search", "fs.patch", "test.run"} <= set(m.allowed_actions)

    def test_digest_changes_when_package_changes(self, tmp_path, login_package):
        import shutil

        clone = tmp_path / "clone"
        shutil.copytree(login_package.root, clone)
        original = load_package(clone).digest
        (clone / "fixtures" / "repository" / "README.md").write_text("tampered", encoding="utf-8")
        assert load_package(clone).digest != original  # FR-001

    def test_validation_catches_bad_references(self, tmp_path):
        root = tmp_path / "bad"
        (root / "fixtures" / "repository").mkdir(parents=True)
        bad = dict(MINIMAL)
        bad["allowed_actions"] = ["fs.read", "fs.warp"]
        bad["success_predicates"] = [{"test_suite": "tests/other.py", "status": "pass"}]
        (root / "manifest.yaml").write_text(yaml.safe_dump(bad), encoding="utf-8")
        report = validate_package(load_package(root))
        assert any("fs.warp" in e for e in report["errors"])
        assert any("unknown suite" in e for e in report["errors"])

    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(ScenarioError):
            load_package(tmp_path)


def _run(run_id, scenario, reason, safety_findings=0, digest="d1"):
    findings = [
        {"code": "destructive_attempt", "summary": "s", "delta": -5.0,
         "evidence": [{"kind": "event", "ref": "e"}]}
    ] * safety_findings
    return {
        "run_id": run_id,
        "terminal_reason": reason,
        "manifest": {
            "scenario_id": scenario, "seed": 0, "scenario_digest": digest,
            "scorer_revision": "0.1.0", "action_protocol_version": "0.1.0",
        },
        "scorecard": {
            "dimensions": [
                {"dimension": "safety", "score": 10 - 5 * safety_findings, "maximum": 10,
                 "findings": findings},
                {"dimension": "completion", "score": 10 if reason == "success" else 0,
                 "maximum": 10, "findings": []},
            ]
        },
    }


class TestComparisonContract:
    def test_newly_failed_and_gate(self):
        base = [_run("b1", "s.a", "success"), _run("b2", "s.b", "success")]
        cand = [_run("c1", "s.a", "success"), _run("c2", "s.b", "gave_up")]
        comparison = compare_run_sets(base, cand)
        assert comparison["newly_failed"][0]["scenario_id"] == "s.b"
        assert comparison["success_rate"] == {"baseline": 100.0, "candidate": 50.0}
        regression = evaluate_regression(comparison)
        assert regression["exit_code"] == EXIT_BENCHMARK_REGRESSION

    def test_safety_gate_takes_priority(self):
        base = [_run("b1", "s.a", "success")]
        cand = [_run("c1", "s.a", "success", safety_findings=1)]
        regression = evaluate_regression(compare_run_sets(base, cand))
        assert regression["exit_code"] == EXIT_SAFETY_REGRESSION

    def test_clean_pass(self):
        base = [_run("b1", "s.a", "success")]
        cand = [_run("c1", "s.a", "success")]
        regression = evaluate_regression(compare_run_sets(base, cand))
        assert regression["status"] == "pass" and regression["exit_code"] == EXIT_OK

    def test_comparability_disclosure(self):
        base = [_run("b1", "s.a", "success", digest="d1")]
        cand = [_run("c1", "s.a", "success", digest="d2")]
        comparison = compare_run_sets(base, cand)
        assert any("scenario_digest" in issue for issue in comparison["comparability_issues"])
