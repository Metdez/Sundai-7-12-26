<!-- Source: agent_debugger_prd.md (lines 1338-1385). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 22. Observability and Reporting

### Logs

JSON structured logs with timestamp, severity, component, run ID, turn, provider, latency, error category, and redaction status.

### Progress reporting

CLI progress shows run state, current turn, budgets, and completed suite counts. API supports server-sent events or WebSocket streaming. The UI displays paused approvals and retry status.

### Metrics

- Runs started/completed/canceled/failed.
- Turn and token distributions.
- Provider latency and error rate.
- Renderer fallback and contradiction rate.
- Scenario success rate.
- Safety violation rate.
- Replay divergence rate.
- Real-versus-simulated outcome agreement.
- Queue time and worker utilization.

### Traces

OpenTelemetry-compatible tracing is recommended for shared deployments, with spans for run orchestration, agent call, policy check, transition, render, score, persistence, and validation.

### Structured reports

Run, suite, comparison, regression, scenario validation, replay, and calibration reports share a common provenance envelope.

### Exit codes

- `0`: success or thresholds met.
- `10`: agent benchmark threshold failure.
- `11`: safety threshold failure.
- `20`: invalid configuration or scenario.
- `21`: incompatible versions.
- `30`: dependency/provider unavailable.
- `31`: platform/infrastructure failure.
- `40`: user cancellation.

### Error categories

Agent behavior, adapter defect, scenario defect, simulator defect, scorer defect, configuration, dependency, infrastructure, authorization, and unknown. Reports shall avoid collapsing these categories into a generic failed status.

### Historical records

Aggregate metrics retain links to immutable runs. Retention policies may compact raw provider payloads while preserving normalized events, evidence, and hashes.
