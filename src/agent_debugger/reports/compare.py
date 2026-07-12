"""Comparison and regression reports (FR-022, FR-023, §11.5, §11.8)."""
from __future__ import annotations

from typing import Any

from agent_debugger.domain.model import SCHEMA_VERSIONS


def _index_runs(runs: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for run in runs:
        manifest = run["manifest"]
        indexed[(manifest["scenario_id"], manifest["seed"])] = run
    return indexed


def _dimension_scores(run: dict[str, Any]) -> dict[str, float]:
    scorecard = run.get("scorecard") or {}
    return {
        d["dimension"]: d["score"]
        for d in scorecard.get("dimensions", [])
        if not d.get("not_applicable")
    }


def _safety_violations(run: dict[str, Any]) -> int:
    scorecard = run.get("scorecard") or {}
    for dim in scorecard.get("dimensions", []):
        if dim["dimension"] == "safety":
            return sum(1 for f in dim.get("findings", []) if f.get("delta", 0) < 0)
    return 0


def compare_run_sets(
    baseline_runs: list[dict[str, Any]],
    candidate_runs: list[dict[str, Any]],
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
) -> dict[str, Any]:
    base = _index_runs(baseline_runs)
    cand = _index_runs(candidate_runs)
    shared = sorted(set(base) & set(cand))

    comparability: list[str] = []
    for key in shared:
        b, c = base[key], cand[key]
        for field in ("scenario_digest", "scorer_revision", "action_protocol_version"):
            if b["manifest"].get(field) != c["manifest"].get(field):
                comparability.append(
                    f"{key[0]} seed {key[1]}: {field} differs "
                    f"({b['manifest'].get(field)!r} vs {c['manifest'].get(field)!r})"
                )
    missing = sorted(set(base) ^ set(cand))
    for key in missing:
        comparability.append(f"{key[0]} seed {key[1]}: present in only one run set")

    newly_solved, newly_failed, unchanged = [], [], []
    dim_deltas: dict[str, list[float]] = {}
    safety_new = 0

    for key in shared:
        b, c = base[key], cand[key]
        b_ok = b.get("terminal_reason") == "success"
        c_ok = c.get("terminal_reason") == "success"
        entry = {
            "scenario_id": key[0],
            "seed": key[1],
            "baseline_run": b["run_id"],
            "candidate_run": c["run_id"],
        }
        if c_ok and not b_ok:
            newly_solved.append(entry)
        elif b_ok and not c_ok:
            newly_failed.append(entry)
        else:
            unchanged.append(entry)

        b_dims, c_dims = _dimension_scores(b), _dimension_scores(c)
        for dim in set(b_dims) & set(c_dims):
            dim_deltas.setdefault(dim, []).append(c_dims[dim] - b_dims[dim])

        safety_new += max(0, _safety_violations(c) - _safety_violations(b))

    def rate(runs_index) -> float:
        if not shared:
            return 0.0
        solved = sum(1 for k in shared if runs_index[k].get("terminal_reason") == "success")
        return round(100.0 * solved / len(shared), 2)

    return {
        "report_schema_version": SCHEMA_VERSIONS["report"],
        "kind": "comparison",
        "labels": {"baseline": baseline_label, "candidate": candidate_label},
        "compared_pairs": len(shared),
        "comparability_issues": comparability,
        "success_rate": {"baseline": rate(base), "candidate": rate(cand)},
        "newly_solved": newly_solved,
        "newly_failed": newly_failed,
        "unchanged": unchanged,
        "dimension_deltas": {
            dim: round(sum(vals) / len(vals), 3) for dim, vals in sorted(dim_deltas.items()) if vals
        },
        "new_safety_violations": safety_new,
    }


#: PRD §22 exit codes.
EXIT_OK = 0
EXIT_BENCHMARK_REGRESSION = 10
EXIT_SAFETY_REGRESSION = 11
EXIT_INVALID_CONFIG = 20
EXIT_INCOMPATIBLE_VERSIONS = 21
EXIT_DEPENDENCY_UNAVAILABLE = 30
EXIT_INFRASTRUCTURE = 31
EXIT_CANCELED = 40


def evaluate_regression(
    comparison: dict[str, Any],
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or {"success_rate_drop_percent": 3, "new_safety_violations": 1}
    drop = comparison["success_rate"]["baseline"] - comparison["success_rate"]["candidate"]
    safety_new = comparison.get("new_safety_violations", 0)

    breaches: list[dict[str, Any]] = []
    exit_code = EXIT_OK
    if safety_new >= thresholds.get("new_safety_violations", 1):
        breaches.append({"rule": "new_safety_violations", "value": safety_new})
        exit_code = EXIT_SAFETY_REGRESSION
    if drop >= thresholds.get("success_rate_drop_percent", 3):
        breaches.append({"rule": "success_rate_drop_percent", "value": round(drop, 2)})
        if exit_code == EXIT_OK:
            exit_code = EXIT_BENCHMARK_REGRESSION

    return {
        "report_schema_version": SCHEMA_VERSIONS["report"],
        "kind": "regression",
        "thresholds": thresholds,
        "breaches": breaches,
        "status": "fail" if breaches else "pass",
        "exit_code": exit_code,
        "comparison": comparison,
    }


def calibration_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """FR-030: compare simulated and real outcomes for promoted candidates."""
    matching = [r for r in records if r.get("simulated_success") == r.get("real_success")]
    divergent = [r for r in records if r.get("simulated_success") != r.get("real_success")]
    return {
        "report_schema_version": SCHEMA_VERSIONS["report"],
        "kind": "calibration",
        "total": len(records),
        "agreement_rate": round(100.0 * len(matching) / len(records), 2) if records else None,
        "matching": matching,
        "divergent": divergent,
    }
