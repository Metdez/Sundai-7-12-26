<!-- Source: agent_debugger_prd.md (lines 649-857). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 13. Functional Requirements

### 13.1 Scenario Management

**FR-001 - Versioned scenario packages**  
**Requirement:** The system shall load scenarios from versioned packages containing manifest, fixtures, transitions, policies, scoring, and optional rendering assets.  
**Rationale:** Portable, immutable scenarios are required for reproducibility.  
**Priority:** Must.  
**Acceptance criteria:** A package digest is recorded on every run; modifying any package file changes the digest.

**FR-002 - Scenario schema validation**  
**Requirement:** The system shall validate structure, references, IDs, versions, and required fields before execution.  
**Rationale:** Invalid scenarios must fail before consuming model resources.  
**Priority:** Must.  
**Acceptance criteria:** Invalid references produce file-and-field-specific errors and a nonzero exit code.

**FR-003 - Deterministic state transitions**  
**Requirement:** Scenario handlers shall produce authoritative state transitions independent of the observation renderer.  
**Rationale:** Truth and scoring cannot depend on probabilistic text generation.  
**Priority:** Must.  
**Acceptance criteria:** Replaying the same canonical actions from the same initial state yields the same state hashes.

**FR-004 - Multiple valid solutions**  
**Requirement:** Scenarios shall support multiple success predicates and equivalent valid patch paths.  
**Rationale:** Debugging tasks often have more than one correct repair.  
**Priority:** Should.  
**Acceptance criteria:** At least two fixture paths can satisfy one sample scenario without hard-coding a single transcript.

**FR-005 - Difficulty and tags**  
**Requirement:** Scenarios shall declare difficulty, language, framework, failure type, and capability tags.  
**Rationale:** Suites need meaningful composition and reporting.  
**Priority:** Should.  
**Acceptance criteria:** CLI and API can filter scenarios by declared metadata.

### 13.2 Agent and Tool Integration

**FR-006 - Canonical action protocol**  
**Requirement:** The system shall define versioned canonical actions for file inspection, search, command execution, tests, edits, logs, configuration, and Git operations.  
**Rationale:** Cross-framework comparison requires normalized semantics.  
**Priority:** Must.  
**Acceptance criteria:** All bundled adapters emit valid protocol objects that pass JSON schema validation.

**FR-007 - Adapter conformance suite**  
**Requirement:** The SDK shall provide fixtures for action serialization, observation handling, timeout, cancellation, and invalid calls.  
**Rationale:** Adapter defects must be distinguished from agent behavior.  
**Priority:** Must.  
**Acceptance criteria:** Registration reports pass/fail by conformance case.

**FR-008 - Agent revision immutability**  
**Requirement:** Each executable agent configuration shall be stored as an immutable revision excluding secret values.  
**Rationale:** Comparisons require exact configuration provenance.  
**Priority:** Must.  
**Acceptance criteria:** Changing prompt, model, tools, limits, or adapter version creates a new revision ID.

**FR-009 - Model-provider neutrality**  
**Requirement:** Agent adapters shall support local and hosted model endpoints without core changes.  
**Rationale:** The target users compare many model types.  
**Priority:** Must.  
**Acceptance criteria:** Two reference adapters using different endpoint styles complete the same smoke scenario.

### 13.3 Simulation and State

**FR-010 - Pluggable observation renderers**  
**Requirement:** The core shall support deterministic template, Qwen-AgentWorld, and hybrid renderers behind one interface.  
**Rationale:** Deterministic tests and realistic production simulation have different needs.  
**Priority:** Must.  
**Acceptance criteria:** A scenario can switch renderer configuration without changing its authoritative handlers.

**FR-011 - Stateful multi-turn context**  
**Requirement:** The renderer shall receive bounded relevant history and current authoritative state projection.  
**Rationale:** Later observations must reflect earlier actions.  
**Priority:** Must.  
**Acceptance criteria:** File edits and test-state changes are reflected in subsequent rendered observations.

**FR-012 - Simulation conformance checks**  
**Requirement:** The system shall detect observation outputs that violate required format or contradict protected state facts.  
**Rationale:** Model simulation can drift.  
**Priority:** Must.  
**Acceptance criteria:** Contradictory outputs are rejected, retried, repaired, or replaced by deterministic fallback and logged.

**FR-013 - Seeded perturbations**  
**Requirement:** Scenarios may introduce controlled ambiguity, tool failures, or misleading evidence using recorded seeds.  
**Rationale:** Recovery evaluation requires repeatable adversity.  
**Priority:** Should.  
**Acceptance criteria:** The same seed produces the same perturbation schedule.

**FR-014 - Provider fallback**  
**Requirement:** A run policy may fall back from a model renderer to a deterministic renderer for infrastructure failure.  
**Rationale:** Provider outages should not always invalidate a suite.  
**Priority:** Should.  
**Acceptance criteria:** The final report discloses every fallback event and affected turns.

### 13.4 Run Orchestration

**FR-015 - Run lifecycle**  
**Requirement:** The system shall support queued, running, paused-for-approval, completed, failed, canceled, and expired states.  
**Rationale:** Long agent sessions and safety approvals need explicit lifecycle semantics.  
**Priority:** Must.  
**Acceptance criteria:** Only valid lifecycle transitions are accepted.

**FR-016 - Limits and budgets**  
**Requirement:** Runs shall enforce action, wall-clock, token, cost, invalid-action, and repeated-action limits.  
**Rationale:** Evaluation must be bounded and comparable.  
**Priority:** Must.  
**Acceptance criteria:** Exceeding each limit produces a distinct terminal reason and recorded metrics.

**FR-017 - Cancellation**  
**Requirement:** Users and CI shall be able to cancel active runs.  
**Rationale:** Models or providers may hang or become costly.  
**Priority:** Must.  
**Acceptance criteria:** Cancellation stops further agent calls and preserves a partial auditable record.

**FR-018 - Parallel suite execution**  
**Requirement:** The runner shall execute independent scenarios concurrently within resource limits.  
**Rationale:** Comparative evaluation requires throughput.  
**Priority:** Should.  
**Acceptance criteria:** Configured concurrency is respected and individual failures do not terminate unrelated runs.

### 13.5 Scoring and Analysis

**FR-019 - Multidimensional scoring**  
**Requirement:** The system shall score completion, investigation, reasoning discipline, testing, recovery, efficiency, and safety.  
**Rationale:** Final success alone is insufficient.  
**Priority:** Must.  
**Acceptance criteria:** Every completed run produces all required dimensions or marks a dimension not applicable with reason.

**FR-020 - Evidence-linked findings**  
**Requirement:** Every score component shall reference events, state facts, or explicit rubric-judge evidence.  
**Rationale:** Scores must be explainable.  
**Priority:** Must.  
**Acceptance criteria:** The API rejects score findings without evidence references.

**FR-021 - Rule and rubric composition**  
**Requirement:** Scoring profiles shall combine deterministic metrics with constrained qualitative rubrics.  
**Rationale:** Some behaviors are measurable directly; others require bounded interpretation.  
**Priority:** Must.  
**Acceptance criteria:** Completion and prohibited-action penalties work with judge models disabled.

**FR-022 - Comparison reports**  
**Requirement:** The system shall compare compatible run sets and report solved/failed transitions and metric deltas.  
**Rationale:** The main product value includes configuration comparison.  
**Priority:** Must.  
**Acceptance criteria:** A report can compare two agent revisions across the same suite and seeds.

**FR-023 - Regression gates**  
**Requirement:** CI shall support threshold rules for success, safety, efficiency, and selected scenarios.  
**Rationale:** Agent releases require enforceable quality gates.  
**Priority:** Should.  
**Acceptance criteria:** Threshold breach produces a dedicated nonzero exit code and machine-readable report.

**FR-024 - Failure clustering**  
**Requirement:** The system should group runs by repeated-action, premature-edit, missing-verification, unsafe-action, and other signatures.  
**Rationale:** Teams need patterns, not only individual transcripts.  
**Priority:** Could.  
**Acceptance criteria:** Bundled signatures classify known fixture trajectories.

### 13.6 Review, Replay, and Reporting

**FR-025 - Full timeline**  
**Requirement:** The review UI shall display actions, policy decisions, observations, state changes, test evidence, and findings in order.  
**Rationale:** Behavioral diagnosis depends on chronology.  
**Priority:** Must.  
**Acceptance criteria:** Every stored event type is renderable and filterable.

**FR-026 - Patch and scope view**  
**Requirement:** The system shall show final and incremental file changes with related-file classification.  
**Rationale:** Broad or unrelated edits are key quality signals.  
**Priority:** Must.  
**Acceptance criteria:** Reviewers can identify files changed and the turn responsible.

**FR-027 - Replay**  
**Requirement:** The system shall replay authoritative transitions and verify final state checksums.  
**Rationale:** Auditability and defect isolation require deterministic reconstruction.  
**Priority:** Must.  
**Acceptance criteria:** A replay command reports match or exact divergence event.

**FR-028 - Export formats**  
**Requirement:** Reports shall export to JSON, JSONL, Markdown, and HTML.  
**Rationale:** Research, CI, and human review have different consumption needs.  
**Priority:** Should.  
**Acceptance criteria:** Exports include manifest, summary, scores, evidence references, and provenance.

### 13.7 Real Validation

**FR-029 - Isolated container validation**  
**Requirement:** Approved candidate patches shall be executable in an ephemeral, resource-limited, network-restricted container.  
**Rationale:** Simulation cannot prove correctness.  
**Priority:** Should.  
**Acceptance criteria:** The runner records image digest, commands, exit codes, logs, diff, and cleanup status.

**FR-030 - Simulation calibration records**  
**Requirement:** The system shall compare simulated and real outcomes for promoted candidates.  
**Rationale:** Simulator trust must be measured.  
**Priority:** Should.  
**Acceptance criteria:** Calibration reports identify matching and divergent observations and outcomes.

### 13.8 Administration and Workspace

**FR-031 - Local workspace management**  
**Requirement:** The product shall create, validate, back up, and migrate a local workspace.  
**Rationale:** The MVP is local-first.  
**Priority:** Must.  
**Acceptance criteria:** Initialization creates a documented layout and migrations preserve recoverable backups.

**FR-032 - Secret references**  
**Requirement:** Configuration shall reference secrets from environment variables, OS credential stores, or external secret providers rather than storing values.  
**Rationale:** Model and service credentials are sensitive.  
**Priority:** Must.  
**Acceptance criteria:** Secret scanning fixtures confirm no plaintext secret enters database, logs, or exports.
