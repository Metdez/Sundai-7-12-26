"""Append-only JSONL event store with hash chaining (NFR-014).

The JSONL file is the authoritative record and stays human-readable
(core principle 9). SQLite holds queryable metadata, not truth.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_debugger.domain.model import EventType
from agent_debugger.protocol.events import GENESIS_HASH, RunEvent, make_event, verify_chain


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventStore:
    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / "events.jsonl"
        self.run_id = run_id
        self._seq = 0
        self._prev_hash = GENESIS_HASH
        if self.path.exists():
            events = self.read_all()
            if events:
                self._seq = events[-1].seq + 1
                self._prev_hash = events[-1].event_hash

    def append(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        evidence_tags: list[str] | None = None,
    ) -> RunEvent:
        event = make_event(
            run_id=self.run_id,
            seq=self._seq,
            event_type=event_type,
            payload=payload,
            prev_hash=self._prev_hash,
            timestamp=utc_now(),
            evidence_tags=evidence_tags,
        )
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
        self._seq += 1
        self._prev_hash = event.event_hash
        return event

    def read_all(self) -> list[RunEvent]:
        if not self.path.exists():
            return []
        events = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(RunEvent.model_validate(json.loads(line)))
        return events

    def verify(self) -> list[RunEvent]:
        events = self.read_all()
        verify_chain(events)
        return events

    @staticmethod
    def load_events(path: Path) -> list[RunEvent]:
        events = []
        with Path(path).open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(RunEvent.model_validate(json.loads(line)))
        return events
