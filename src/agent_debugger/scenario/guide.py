"""Human-facing scenario guides for the review dashboard.

Guides live at scenarios/_guides/<scenario_id>.yaml — deliberately OUTSIDE
each scenario package root, because compute_package_digest hashes every file
under the root; documentation edits must never invalidate registrations or
the replay of existing runs.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError


class ScenarioGuide(BaseModel):
    schema_version: int = 1
    scenario_id: str
    summary: str = ""
    what_it_tests: list[str] = Field(default_factory=list)
    the_trap: str | None = None
    planted_bug: str | None = None
    ideal_path: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    scoring_notes: list[str] = Field(default_factory=list)
    common_failure_modes: list[str] = Field(default_factory=list)


def guide_path(package_root: Path, scenario_id: str) -> Path:
    return Path(package_root).parent / "_guides" / f"{scenario_id}.yaml"


def load_guide(package_root: Path, scenario_id: str) -> ScenarioGuide | None:
    """Best-effort read of the sibling _guides/<scenario_id>.yaml.

    Guides are presentational; any problem (missing file, invalid YAML,
    schema violation) yields None rather than an error.
    """
    path = guide_path(package_root, scenario_id)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        return ScenarioGuide.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError):
        return None
