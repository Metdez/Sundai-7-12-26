"""Core domain enums and entities (PRD §15).

This module must not import FastAPI, database clients, or provider SDKs
(NFR-009). Pydantic is the sanctioned schema library (PRD §17).
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSIONS = {
    "action_protocol": "0.1.0",
    "event": "0.1.0",
    "scenario": "1.0.0",
    "run_manifest": "0.1.0",
    "report": "0.1.0",
}


def canonical_json(data: Any) -> str:
    """Deterministic JSON serialization used for all hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str | bytes) -> str:
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def digest_of(data: Any) -> str:
    return sha256_hex(canonical_json(data))


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED_FOR_APPROVAL = "paused_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"


#: FR-015 — only these lifecycle transitions are accepted.
VALID_STATUS_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELED, RunStatus.EXPIRED}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.PAUSED_FOR_APPROVAL,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELED,
            RunStatus.EXPIRED,
        }
    ),
    RunStatus.PAUSED_FOR_APPROVAL: frozenset(
        {RunStatus.RUNNING, RunStatus.CANCELED, RunStatus.EXPIRED, RunStatus.FAILED}
    ),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELED: frozenset(),
    RunStatus.EXPIRED: frozenset(),
}


class TerminalReason(str, Enum):
    SUCCESS = "success"
    FAILURE_PREDICATE = "failure_predicate"
    SUBMITTED_UNSOLVED = "submitted_unsolved"
    GAVE_UP = "gave_up"
    ACTION_LIMIT = "action_limit"
    TIME_LIMIT = "time_limit"
    TOKEN_LIMIT = "token_limit"
    COST_LIMIT = "cost_limit"
    INVALID_ACTION_LIMIT = "invalid_action_limit"
    REPEATED_ACTION_LIMIT = "repeated_action_limit"
    CANCELED = "canceled"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


class ActionClass(str, Enum):
    """PRD §20 action classes."""

    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"
    PRIVILEGED = "privileged"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


class EventType(str, Enum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    AGENT_ACTION = "agent.action"
    POLICY_DECISION = "policy.decision"
    STATE_TRANSITION = "state.transition"
    OBSERVATION_RENDERED = "observation.rendered"
    RENDERER_FALLBACK = "renderer.fallback"
    PERTURBATION_APPLIED = "perturbation.applied"
    LIMIT_EXCEEDED = "run.limit"
    RUN_TERMINAL = "run.terminal"
    RUN_ERROR = "run.error"
    SCORE_COMPLETED = "score.completed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"
    ANNOTATION_ADDED = "annotation.added"
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    SNAPSHOT_TAKEN = "state.snapshot"


class RunLimits(BaseModel):
    """FR-016 — bounded, comparable runs."""

    max_actions: int = 80
    max_wall_clock_seconds: float = 1200.0
    max_tokens: int = 1_000_000
    max_cost_usd: float = 10.0
    max_invalid_actions: int = 5
    max_repeated_actions: int = 6


class RunManifest(BaseModel):
    """FR: complete reproducibility envelope (PRD §15.4). Immutable after freeze."""

    run_id: str
    scenario_id: str
    scenario_version: str
    scenario_digest: str
    agent_revision_id: str
    agent_config_digest: str
    renderer: str
    renderer_revision: str
    scorer_revision: str
    scoring_profile: str
    seed: int
    limits: RunLimits
    created_at: str
    product_version: str
    action_protocol_version: str = SCHEMA_VERSIONS["action_protocol"]
    event_schema_version: str = SCHEMA_VERSIONS["event"]
    manifest_schema_version: str = SCHEMA_VERSIONS["run_manifest"]
    baseline_id: str | None = None
    operator: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    ci_metadata: dict[str, Any] = Field(default_factory=dict)

    def digest(self) -> str:
        return digest_of(self.model_dump(mode="json"))


class EvidenceRef(BaseModel):
    """Artifact and evidence reference format (shared contract #6)."""

    kind: str  # "event" | "state_fact" | "artifact" | "judge"
    ref: str  # event id, fact key, artifact digest, or judge output digest
    note: str | None = None


class Finding(BaseModel):
    """FR-020 — every score component references evidence."""

    code: str
    summary: str
    delta: float
    evidence: list[EvidenceRef] = Field(default_factory=list)


class DimensionScore(BaseModel):
    dimension: str
    score: float
    maximum: float
    confidence: float = 1.0
    not_applicable: bool = False
    na_reason: str | None = None
    findings: list[Finding] = Field(default_factory=list)


class Scorecard(BaseModel):
    run_id: str
    scorer_version: str
    scoring_profile: str
    dimensions: list[DimensionScore]
    overall_score: float
    overall_maximum: float
    judge_used: bool = False
    judge_output_digest: str | None = None

    def dimension(self, name: str) -> DimensionScore | None:
        for d in self.dimensions:
            if d.dimension == name:
                return d
        return None


class ArtifactMeta(BaseModel):
    """PRD §15.7 — content-addressed artifact metadata."""

    artifact_id: str
    media_type: str
    digest: str
    size: int
    logical_role: str
    creation_event: str | None = None
    external_location: str | None = None


class AgentRevision(BaseModel):
    """PRD §15.3 — immutable executable configuration; secrets by reference only."""

    revision_id: str
    name: str
    adapter_id: str
    adapter_version: str
    model_identifier: str
    prompt_digest: str
    tool_contract_version: str = SCHEMA_VERSIONS["action_protocol"]
    limits: RunLimits = Field(default_factory=RunLimits)
    generation_settings: dict[str, Any] = Field(default_factory=dict)
    behavior: dict[str, Any] = Field(default_factory=dict)
    endpoint: str | None = None
    api_key_ref: str | None = None  # reference such as env:NAME — never a value
    tags: list[str] = Field(default_factory=list)

    @staticmethod
    def compute_revision_id(config: dict[str, Any]) -> str:
        material = {
            k: config.get(k)
            for k in (
                "name",
                "adapter_id",
                "adapter_version",
                "model_identifier",
                "prompt",
                "limits",
                "generation_settings",
                "behavior",
                "endpoint",
            )
        }
        return "agent-" + digest_of(material)[:16]
