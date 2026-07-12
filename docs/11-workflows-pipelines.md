<!-- Source: agent_debugger_prd.md (lines 295-596). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 11. Core Workflows and Pipelines

### 11.1 Create and Validate a Scenario

#### Purpose

Produce a versioned, executable benchmark scenario with deterministic truth, realistic observations, and testable scoring.

#### Trigger

Manual CLI or authoring API action.

#### Inputs

Required: scenario manifest, initial file tree, hidden root cause, action policy, success/failure conditions, scoring rules. Optional: observation templates, Qwen-AgentWorld prompts, misleading paths, real-container reference fixture.

#### Processing Steps

1. Parse schema and resolve referenced files.
2. Validate IDs, versions, and checksums.
3. Verify every state transition is reachable or explicitly terminal.
4. Run scenario unit fixtures against deterministic handlers.
5. Render sample observations and check protocol format.
6. Run safety lint for secrets, host paths, unrestricted commands, and ambiguous destructive actions.
7. Produce a signed package digest and validation report.

#### Outputs

Scenario package, package digest, validation report, sample transcript, and warnings.

#### Failure Modes

Invalid schema, unreachable success state, contradictory scoring rules, missing fixture, nondeterministic handler, unsafe path reference, or renderer protocol mismatch.

#### Acceptance Criteria

- Validation exits successfully with zero errors.
- A known-good action sequence reaches success.
- At least one known-bad path produces the expected failure or penalty.
- Repeated fixture runs produce identical authoritative events.
- Every scoring rule references a defined event or state fact.

### 11.2 Register and Verify an Agent Adapter

#### Purpose

Make an agent configuration executable through the canonical action protocol.

#### Trigger

Manual CLI/API registration or CI setup.

#### Inputs

Adapter type, model endpoint, credentials reference, system prompt, tool schema, limits, and metadata.

#### Processing Steps

1. Validate configuration and secret references.
2. Test model connectivity.
3. Run adapter conformance fixtures.
4. Verify action serialization, cancellation, timeout handling, and token accounting.
5. Store immutable configuration revision with secrets excluded.

#### Outputs

Agent revision ID, capability matrix, conformance report.

#### Failure Modes

Authentication error, unsupported tool call, malformed action, model timeout, missing cancellation support, or unsafe adapter capability.

#### Acceptance Criteria

- Adapter passes required conformance cases.
- A dry run emits only valid canonical actions.
- Secrets never appear in stored configuration or logs.

### 11.3 Execute a Simulated Debugging Session

#### Purpose

Evaluate an agent's debugging process in a safe, stateful scenario.

#### Trigger

CLI, API, dashboard, scheduled suite, or CI.

#### Inputs

Agent revision, scenario revision, seed, run limits, simulation provider, scoring profile, and optional baseline.

#### Processing Steps

1. Create immutable run manifest.
2. Initialize authoritative state and event chain.
3. Send task and tool contract to the agent.
4. Receive and normalize an action.
5. Classify the action and enforce policy.
6. Apply the action to state.
7. Render a consistent observation.
8. Return observation to the agent and persist evidence.
9. Repeat until success, failure, give-up, timeout, or budget limit.
10. Freeze final state and invoke scoring.

#### Outputs

Run state, transcript, event log, final patch, token/time/action counts, and terminal reason.

#### Failure Modes

Agent timeout, invalid tool call, renderer timeout, simulation inconsistency, policy violation, state-handler defect, budget exhaustion, or infrastructure failure.

#### Acceptance Criteria

- Every agent action has one corresponding policy decision, state result, and observation.
- The run can be replayed without invoking the agent.
- Terminal reason is unambiguous.
- Infrastructure failures are not scored as agent failures.

### 11.4 Score and Explain a Run

#### Purpose

Produce defensible multidimensional scores with traceable evidence.

#### Trigger

Automatically after terminal state; manually for re-scoring with a compatible scoring profile.

#### Inputs

Frozen run events, final state, scenario rubric, scoring profile, optional judge model.

#### Processing Steps

1. Compute deterministic facts such as completion, tests run, repeated actions, file scope, failed actions, and prohibited attempts.
2. Evaluate rule-based rubric components.
3. Optionally invoke a rubric judge for qualitative dimensions using a constrained evidence packet.
4. Apply weighting and confidence rules.
5. Generate evidence links and score explanation.
6. Mark low-confidence or judge-dependent results.

#### Outputs

Dimension scores, overall score, confidence, findings, evidence references, and scorer version.

#### Failure Modes

Missing evidence, incompatible scoring version, judge failure, rubric ambiguity, or unbounded qualitative prompt.

#### Acceptance Criteria

- Completion and safety scores are derivable without a judge model.
- Every deduction or award cites at least one event or state fact.
- Re-scoring with the same scorer version and inputs produces identical deterministic components.

### 11.5 Compare Agent Configurations

#### Purpose

Identify meaningful differences across models, prompts, tools, or versions.

#### Trigger

CLI/API/dashboard comparison request or CI baseline check.

#### Inputs

Two or more run sets sharing compatible suite and scoring versions.

#### Processing Steps

1. Validate comparability.
2. Aggregate per-scenario and per-dimension metrics.
3. Separate solved/unsolved transitions from efficiency and safety changes.
4. Compute confidence intervals when sample count permits.
5. Cluster repeated failure signatures.
6. Generate a regression summary and evidence links.

#### Outputs

Comparison report, changed outcomes, metric deltas, failure clusters, and recommended review runs.

#### Failure Modes

Mismatched scenario versions, too few samples, changed scoring profile, missing runs, or incomparable budgets.

#### Acceptance Criteria

- Report discloses all comparability differences.
- Newly solved and newly failed scenarios are listed explicitly.
- Aggregate deltas link to individual runs.

### 11.6 Replay and Audit a Run

#### Purpose

Reconstruct the session for debugging, trust, and dispute resolution.

#### Trigger

Manual review, incident investigation, or automated consistency check.

#### Inputs

Run manifest, event log, scenario package, and artifact hashes.

#### Processing Steps

1. Verify event-chain and artifact hashes.
2. Reapply authoritative transitions from the initial state.
3. Compare reconstructed state with recorded snapshots.
4. Reuse recorded observations or optionally re-render for diagnostic comparison.
5. Report divergence.

#### Outputs

Replay transcript, state checksum result, divergence report.

#### Failure Modes

Missing package revision, corrupted artifact, incompatible handler version, or nondeterministic custom code.

#### Acceptance Criteria

- Authoritative replay reaches the recorded final state checksum.
- Recorded observations remain accessible even when the simulation provider is unavailable.

### 11.7 Promote a Candidate to Real-Environment Validation

#### Purpose

Confirm that a promising simulated fix works in an isolated executable environment.

#### Trigger

Manual approval, policy-based promotion, or CI rule.

#### Inputs

Scenario real-validation fixture, candidate patch, container image digest, resource policy, and test commands.

#### Processing Steps

1. Verify scenario and patch provenance.
2. Create an ephemeral network-restricted container.
3. Mount repository fixture read-write and secrets none by default.
4. Apply patch.
5. Run allowlisted validation commands.
6. Collect exit codes, logs, diffs, and resource usage.
7. Destroy the container and compare simulation outcome with real outcome.

#### Outputs

Real-validation report, evidence bundle, simulation calibration record.

#### Failure Modes

Container startup failure, unavailable image, dependency download blocked, flaky test, resource limit, or patch apply conflict.

#### Acceptance Criteria

- Validation is labeled separately from simulation.
- Container image and command digests are recorded.
- No host filesystem or credential access occurs.
- Result includes patch, logs, exit codes, and final diff.

### 11.8 Detect Drift and Regression

#### Purpose

Identify changes in agent behavior, simulator fidelity, or scenario semantics over time.

#### Trigger

CI, scheduled suite, scenario update, simulation-provider update, or scorer update.

#### Inputs

Current runs, baseline runs, compatibility rules, and thresholds.

#### Processing Steps

1. Validate version compatibility.
2. Compare outcome and behavior metrics.
3. Separate agent regression from simulator/scorer change.
4. Flag statistically or operationally meaningful changes.
5. Generate a triage list.

#### Outputs

Drift report, regression status, blocking decision, and linked evidence.

#### Failure Modes

Insufficient sample size, changed seeds, missing baseline, or broad version changes that invalidate comparison.

#### Acceptance Criteria

- The report attributes each delta to agent, scenario, simulator, scorer, or unknown category.
- CI returns a distinct exit code for threshold regression versus infrastructure failure.
