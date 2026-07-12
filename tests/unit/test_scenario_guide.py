"""Scenario guide loading (dashboard docs) — presentational, never raises."""
from pathlib import Path

import yaml

from agent_debugger.scenario.guide import ScenarioGuide, load_guide

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "scenarios"


def _make_layout(tmp_path, content):
    package_root = tmp_path / "scenarios" / "demo"
    package_root.mkdir(parents=True)
    guides = tmp_path / "scenarios" / "_guides"
    guides.mkdir()
    if content is not None:
        (guides / "demo.id.yaml").write_text(content, encoding="utf-8")
    return package_root


def test_load_guide_valid(tmp_path):
    package_root = _make_layout(
        tmp_path, "scenario_id: demo.id\nsummary: hi\nwhat_it_tests: [a, b]\n"
    )
    guide = load_guide(package_root, "demo.id")
    assert isinstance(guide, ScenarioGuide)
    assert guide.summary == "hi"
    assert guide.what_it_tests == ["a", "b"]
    assert guide.the_trap is None


def test_load_guide_missing_returns_none(tmp_path):
    package_root = _make_layout(tmp_path, None)
    assert load_guide(package_root, "demo.id") is None


def test_load_guide_non_mapping_returns_none(tmp_path):
    package_root = _make_layout(tmp_path, "- just\n- a list\n")
    assert load_guide(package_root, "demo.id") is None


def test_load_guide_schema_violation_returns_none(tmp_path):
    package_root = _make_layout(
        tmp_path, "scenario_id: demo.id\nwhat_it_tests: not-a-list\n"
    )
    assert load_guide(package_root, "demo.id") is None


def test_every_package_has_matching_guide():
    """Docs drift guard: every scenario package ships a guide whose
    scenario_id matches its manifest."""
    package_dirs = [p for p in SCENARIOS.iterdir() if (p / "manifest.yaml").is_file()]
    assert package_dirs, "no scenario packages found"
    for package_root in package_dirs:
        manifest = yaml.safe_load(
            (package_root / "manifest.yaml").read_text(encoding="utf-8")
        )
        scenario_id = manifest["scenario_id"]
        guide = load_guide(package_root, scenario_id)
        assert guide is not None, f"missing or invalid guide for {scenario_id}"
        assert guide.scenario_id == scenario_id
