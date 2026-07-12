"""Markdown and HTML report exporters (FR-028)."""
from __future__ import annotations

import html
from typing import Any


def _score_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    scorecard = report.get("scorecard") or {}
    return scorecard.get("dimensions", [])


def run_report_markdown(report: dict[str, Any]) -> str:
    prov = report["provenance"]
    outcome = report["outcome"]
    manifest = prov["manifest"]
    lines = [
        f"# Run Report — {prov['run_id']}",
        "",
        f"- **Scenario:** {manifest['scenario_id']} v{manifest['scenario_version']}",
        f"- **Agent revision:** {manifest['agent_revision_id']}",
        f"- **Renderer:** {manifest['renderer']} (rev {manifest['renderer_revision']})",
        f"- **Seed:** {manifest['seed']}  |  **Scorer:** {manifest['scorer_revision']}",
        f"- **Scenario digest:** `{manifest['scenario_digest'][:16]}…`",
        f"- **Terminal reason:** **{outcome.get('terminal_reason')}**",
        "",
        "## Metrics",
        "",
    ]
    for key, value in (outcome.get("metrics") or {}).items():
        lines.append(f"- {key}: {value}")
    scorecard = report.get("scorecard")
    if scorecard:
        lines += ["", "## Scorecard", "",
                  f"**Overall: {scorecard['overall_score']} / {scorecard['overall_maximum']}**", "",
                  "| Dimension | Score | Max | Notes |", "|---|---:|---:|---|"]
        for dim in scorecard["dimensions"]:
            if dim.get("not_applicable"):
                note = f"N/A — {dim.get('na_reason')}"
                lines.append(f"| {dim['dimension']} | – | {dim['maximum']} | {note} |")
            else:
                notes = "; ".join(f["summary"] for f in dim.get("findings", []))
                lines.append(
                    f"| {dim['dimension']} | {dim['score']} | {dim['maximum']} | {notes} |"
                )
    changed = outcome.get("changed_files") or {}
    if changed:
        lines += ["", "## Changed files", ""]
        for path, kind in sorted(changed.items()):
            lines.append(f"- `{path}` ({kind})")
    fallbacks = report.get("renderer_fallbacks") or []
    lines += ["", "## Renderer fallbacks", "",
              f"{len(fallbacks)} fallback event(s)." if fallbacks else "None."]
    safety = report.get("safety_events") or []
    if safety:
        lines += ["", "## Safety events", ""]
        for entry in safety:
            payload = entry["payload"]
            lines.append(
                f"- seq {entry['seq']}: {payload.get('action_class')} — {payload.get('reason')}"
            )
    return "\n".join(lines) + "\n"


_HTML_STYLE = """
body{font-family:system-ui,Segoe UI,sans-serif;margin:2rem auto;max-width:70rem;padding:0 1rem;color:#1a1a2e}
table{border-collapse:collapse;width:100%;margin:1rem 0}
th,td{border:1px solid #d0d0e0;padding:.4rem .6rem;text-align:left}
th{background:#f0f0f8}
code{background:#f5f5fa;padding:.1rem .3rem;border-radius:3px}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:9999px;font-weight:600}
.badge.success{background:#d9f2e2;color:#146c43}.badge.fail{background:#fbe3e4;color:#a12622}
h1,h2{color:#0f3460}
"""


def run_report_html(report: dict[str, Any]) -> str:
    prov = report["provenance"]
    outcome = report["outcome"]
    manifest = prov["manifest"]
    reason = outcome.get("terminal_reason") or "unknown"
    badge_class = "success" if reason == "success" else "fail"
    rows = ""
    scorecard = report.get("scorecard")
    if scorecard:
        for dim in scorecard["dimensions"]:
            if dim.get("not_applicable"):
                rows += (
                    f"<tr><td>{html.escape(dim['dimension'])}</td><td>–</td>"
                    f"<td>{dim['maximum']}</td><td>N/A — {html.escape(str(dim.get('na_reason')))}</td></tr>"
                )
            else:
                notes = "; ".join(html.escape(f["summary"]) for f in dim.get("findings", []))
                rows += (
                    f"<tr><td>{html.escape(dim['dimension'])}</td><td>{dim['score']}</td>"
                    f"<td>{dim['maximum']}</td><td>{notes}</td></tr>"
                )
    changed = "".join(
        f"<li><code>{html.escape(p)}</code> ({html.escape(k)})</li>"
        for p, k in sorted((outcome.get("changed_files") or {}).items())
    )
    metrics = "".join(
        f"<li>{html.escape(str(k))}: {html.escape(str(v))}</li>"
        for k, v in (outcome.get("metrics") or {}).items()
    )
    overall = (
        f"<p><strong>Overall score: {scorecard['overall_score']} / {scorecard['overall_maximum']}"
        "</strong></p>"
        if scorecard
        else "<p>No scorecard (run not scored).</p>"
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Run {html.escape(prov['run_id'])}</title><style>{_HTML_STYLE}</style></head><body>
<h1>Run Report — {html.escape(prov['run_id'])}</h1>
<p><span class="badge {badge_class}">{html.escape(reason)}</span></p>
<ul>
<li>Scenario: <code>{html.escape(manifest['scenario_id'])}</code> v{html.escape(manifest['scenario_version'])}</li>
<li>Agent revision: <code>{html.escape(manifest['agent_revision_id'])}</code></li>
<li>Renderer: {html.escape(manifest['renderer'])}</li>
<li>Seed: {manifest['seed']}</li>
<li>Scenario digest: <code>{html.escape(manifest['scenario_digest'][:20])}…</code></li>
</ul>
<h2>Scorecard</h2>{overall}
<table><tr><th>Dimension</th><th>Score</th><th>Max</th><th>Findings</th></tr>{rows}</table>
<h2>Metrics</h2><ul>{metrics}</ul>
<h2>Changed files</h2><ul>{changed or '<li>none</li>'}</ul>
</body></html>"""
