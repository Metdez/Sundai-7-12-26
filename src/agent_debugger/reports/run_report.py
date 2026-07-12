"""Structured run report with a common provenance envelope (FR-028, PRD §22)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debugger.domain.model import EventType, RunManifest, SCHEMA_VERSIONS
from agent_debugger.persistence.events import EventStore

REPORT_SCHEMA_VERSION = SCHEMA_VERSIONS["report"]


def build_run_report(run_dir: str | Path, db_run: dict[str, Any] | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir)
    manifest = RunManifest.model_validate_json(
        (run_dir / "manifest.json").read_text(encoding="utf-8")
    )
    events = EventStore.load_events(run_dir / "events.jsonl")

    terminal: dict[str, Any] = {}
    fallbacks: list[dict[str, Any]] = []
    safety_events: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    score_payload: dict[str, Any] | None = None

    for event in events:
        entry = {
            "seq": event.seq,
            "event_id": event.event_id,
            "type": event.event_type.value,
            "timestamp": event.timestamp,
            "payload": event.payload,
        }
        timeline.append(entry)
        if event.event_type is EventType.RUN_TERMINAL:
            terminal = event.payload
        elif event.event_type is EventType.RENDERER_FALLBACK:
            fallbacks.append(entry)
        elif event.event_type is EventType.POLICY_DECISION and event.payload.get("decision") != "allow":
            safety_events.append(entry)
        elif event.event_type is EventType.SCORE_COMPLETED:
            score_payload = event.payload

    scorecard = db_run.get("scorecard") if db_run else None

    return {
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "kind": "run",
        "provenance": {
            "run_id": manifest.run_id,
            "manifest": manifest.model_dump(mode="json"),
            "manifest_digest": manifest.digest(),
            "event_count": len(events),
        },
        "outcome": {
            "terminal_reason": terminal.get("reason"),
            "final_state_hash": terminal.get("final_state_hash"),
            "changed_files": terminal.get("changed_files", {}),
            "metrics": terminal.get("metrics", {}),
            "final_patch_artifact": terminal.get("final_patch"),
        },
        "scorecard": scorecard,
        "score_summary": score_payload,
        "renderer_fallbacks": fallbacks,
        "safety_events": safety_events,
        "timeline": timeline,
    }


def export_events_jsonl(run_dir: str | Path) -> str:
    return (Path(run_dir) / "events.jsonl").read_text(encoding="utf-8")


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)
