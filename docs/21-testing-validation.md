<!-- Source: agent_debugger_prd.md (lines 1288-1336). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 21. Testing and Validation Strategy

### Unit tests

State transitions, path normalization, scoring rules, limit enforcement, configuration precedence, hashing, and redaction.

### Integration tests

Core with SQLite/PostgreSQL, artifact store, deterministic renderer, Qwen-compatible mock endpoint, agent adapters, and container validator.

### Contract tests

Versioned JSON schemas for actions, observations, adapter SDK, worker protocol, API, scenario packages, and reports.

### End-to-end tests

Bundled scenarios covering successful solve, wrong hypothesis recovery, invalid command, repeated action, unsafe deletion attempt, renderer outage, cancellation, and real validation.

### Security tests

Path traversal, shell injection, prompt injection, secret leakage, oversized payloads, malicious archives, unsafe container configuration, authorization boundaries, and dependency scanning.

### Compatibility tests

Windows native core, WSL2 provider, Linux server, macOS CLI, supported Python versions, SQLite/PostgreSQL, Docker/Podman, and multiple provider adapters.

### Fixture-based tests

Every released scenario contains at least one known-good trajectory, one known-bad trajectory, expected state hashes, and score expectations.

### Failure-injection tests

Model timeouts, partial responses, malformed JSON, provider rate limits, database interruption, disk-full condition, artifact upload failure, worker crash, and flaky real tests.

### Upgrade tests

Open workspaces from supported prior versions, migrate, replay historical runs, and verify old exports remain readable.

### Dogfooding

- Use Agent Debugger to evaluate a simple reference coding agent against the product's own intentionally broken fixtures.
- Encode bugs from Agent Debugger's repository as scenarios once the state engine supports them.
- Use the reporting pipeline to compare the reference agent before and after changes to its prompt and tool policy.
- Promote selected simulated fixes into the product's own test container.
- Require each phase to add at least one scenario that tests a capability introduced in that phase.

### Required evidence

Validation results include structured action/observation logs, state hashes, patches, command outputs, test results, exit codes, scorer findings, provider metadata, and source references. Screenshots are optional UI evidence, never the sole proof of correctness.
