"""Run event envelope and hash-chain rules (shared contract #2, NFR-014).

Events are append-only. Each event hash covers the previous hash, so any
mutation of history is detectable. `verify_chain` recomputes every link.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_debugger.domain.errors import IntegrityError
from agent_debugger.domain.model import SCHEMA_VERSIONS, EventType, digest_of

EVENT_SCHEMA_VERSION = SCHEMA_VERSIONS["event"]

GENESIS_HASH = "0" * 64


class RunEvent(BaseModel):
    event_id: str
    run_id: str
    seq: int
    event_type: EventType
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    event_hash: str = ""
    schema_version: str = EVENT_SCHEMA_VERSION
    evidence_tags: list[str] = Field(default_factory=list)

    def hash_material(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "seq": self.seq,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "schema_version": self.schema_version,
        }

    def compute_hash(self) -> str:
        return digest_of(self.hash_material())

    def sealed(self) -> "RunEvent":
        return self.model_copy(update={"event_hash": self.compute_hash()})


def make_event(
    run_id: str,
    seq: int,
    event_type: EventType,
    payload: dict[str, Any],
    prev_hash: str,
    timestamp: str,
    evidence_tags: list[str] | None = None,
) -> RunEvent:
    event = RunEvent(
        event_id=f"{run_id}-e{seq:05d}",
        run_id=run_id,
        seq=seq,
        event_type=event_type,
        timestamp=timestamp,
        payload=payload,
        prev_hash=prev_hash,
        evidence_tags=evidence_tags or [],
    )
    return event.sealed()


def verify_chain(events: list[RunEvent]) -> None:
    """Raise IntegrityError at the first broken link."""
    prev = GENESIS_HASH
    for i, event in enumerate(events):
        if event.seq != i:
            raise IntegrityError(
                f"Event sequence gap at index {i}: seq={event.seq}",
                details={"index": i, "seq": event.seq},
            )
        if event.prev_hash != prev:
            raise IntegrityError(
                f"Broken hash chain at seq {event.seq}: prev_hash mismatch",
                details={"seq": event.seq},
            )
        expected = event.compute_hash()
        if event.event_hash != expected:
            raise IntegrityError(
                f"Event hash mismatch at seq {event.seq}",
                details={"seq": event.seq, "expected": expected, "stored": event.event_hash},
            )
        prev = event.event_hash
