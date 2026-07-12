<!-- Source: agent_debugger_prd.md (lines 1387-1419). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 23. State, Memory, and Traceability

### Persisted state

- Run manifests and lifecycle.
- Append-only events.
- Periodic authoritative state snapshots.
- Scenario and agent revision metadata.
- Scorecards and findings.
- Artifact provenance.
- Comparison baselines.
- Calibration history.
- Human annotations separate from original records.

### Requirement and test mapping

The repository shall maintain a machine-readable matrix mapping PRD requirement IDs to modules, automated tests, and implementation phases. CI shall flag Must requirements without test references after their scheduled phase.

### Drift detection

State is stale when scenario digest, renderer prompt digest, scoring profile, product major version, or adapter contract differs from the compatibility envelope. Comparisons disclose rather than hide these differences.

### Caching

Safe caches include downloaded immutable scenarios, provider model metadata, rendered deterministic observations, and content-addressed artifacts. Model-generated observations are cached only by complete request digest and must retain provider metadata.

### Recovery

The event log is authoritative. On restart, the orchestrator identifies incomplete runs, verifies the last event hash and snapshot, and marks the run abandoned or resumes only when adapter and provider semantics explicitly support it.

### Reset and regeneration

Users may delete derived reports and regenerate them from immutable events. Deleting source runs or artifacts requires explicit confirmation and respects retention locks.
