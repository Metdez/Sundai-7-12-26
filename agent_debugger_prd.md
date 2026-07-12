# Agent Debugger

**Document type:** Architecture-grade Product Requirements Document  
**Status:** Proposed v1.0  
**Prepared:** July 12, 2026  
**Primary scope:** Reproducible evaluation of AI coding-agent debugging behavior using stateful simulation, with optional real-environment validation.

## 1. Executive Summary

Agent Debugger is a benchmark authoring, execution, and analysis platform for evaluating how AI coding agents investigate, diagnose, repair, and verify software failures. It is designed for agent developers, model teams, research groups, and engineering organizations that need repeatable evidence about an agent's behavior before granting it access to real repositories and execution environments.

A test run places a coding agent inside a fictional but stateful software project. The agent may inspect files, search code, execute commands, edit files, run tests, inspect logs, and use version-control operations through a normalized tool protocol. Agent Debugger applies each action to an authoritative scenario state engine, then uses a simulation provider - initially Qwen-AgentWorld - to produce realistic environment observations consistent with that state. The platform records the full trajectory and scores not only task completion, but also investigation quality, hypothesis discipline, verification, recovery, efficiency, and safety.

The key differentiator is a **hybrid truth-and-simulation architecture**. A deterministic scenario model owns hidden root causes, state transitions, allowed actions, success conditions, and scoring facts. A language world model renders realistic outputs and controlled ambiguity, but does not decide whether the task is solved. This preserves reproducibility and auditability while retaining the flexibility and lower cost of model-based environment simulation.

## 2. Background and Motivation

### Current situation

Coding-agent evaluation commonly relies on one of four approaches:

1. Real repository and container benchmarks, which are technically faithful but expensive, slow, operationally complex, and risky.
2. Static question-and-answer tests, which are cheap but fail to measure multi-step investigation and recovery behavior.
3. Hand-scripted mock tools, which are deterministic but costly to author and often too brittle or unrealistic.
4. LLM-only simulated environments, which are flexible but may drift, hallucinate state, or award success inconsistently.

Teams therefore struggle to answer practical questions such as whether an agent inspects evidence before editing, recognizes a wrong hypothesis, avoids destructive commands, verifies its fix, or regresses after a prompt or model change.

### Pain points

- A pass/fail result hides unsafe or low-quality reasoning paths.
- Real-environment execution creates infrastructure cost and security exposure early in development.
- Existing benchmark outputs are difficult to compare across agent frameworks because tools and transcript formats differ.
- Repeated runs may be non-reproducible when the environment itself is probabilistic.
- Benchmark authors lack a concise way to specify hidden root causes, valid solution paths, misleading evidence, and behavioral scoring.
- Human review is labor-intensive without structured timelines, evidence, and automated annotations.

### Why current approaches are insufficient

Real execution remains necessary to prove technical correctness, but it is not the most efficient first-line instrument for diagnosing agent behavior. Conversely, unconstrained model simulation is unsuitable as the sole source of truth because small inconsistencies can corrupt evaluation. The opportunity is to combine deterministic benchmark semantics with realistic language-model rendering and reserve real execution for confirmation.

### Inherited ideas

The initial concept establishes the product's essential evaluation dimensions: task completion, investigation, reasoning, testing, recovery, efficiency, and safety; scenario difficulty levels; cross-agent comparison; regression testing; transcript review; Windows-friendly operation; and eventual real-environment validation.

Qwen-AgentWorld is a relevant enabling dependency because it is explicitly trained to predict environment observations across Terminal and SWE domains, supports long multi-turn context, and can be served through OpenAI-compatible endpoints using common inference servers. Its role in this PRD is limited to simulation and controlled perturbation, not authoritative state or grading.

### Newly proposed capabilities

This PRD adds:

- A deterministic scenario state engine beneath the language world model.
- A canonical action and observation protocol independent of agent framework.
- Evidence-backed, replayable scoring with requirement-to-event traceability.
- Simulation conformance tests and calibration against real container traces.
- A scenario package format with fixtures, state transitions, rubrics, and versioned provenance.
- Explicit action safety classes and approval gates.
- A staged product architecture that begins with a local CLI and API before adding broader surfaces.

## 3. Product Vision

Agent Debugger should become the standard pre-production proving ground for coding agents. A team should be able to register an agent configuration, select a versioned benchmark suite, run hundreds of safe simulated debugging sessions, compare behavioral regressions, inspect decisive moments, and promote only promising solutions to isolated real-container validation.

Users interact through a local CLI, API, and web review interface. Scenario authors describe project state and benchmark semantics once; Agent Debugger supplies normalized tools, consistent simulation, scoring, replay, and reports. Over time, the product should evolve into a trusted evaluation control plane spanning local models, hosted models, internal agents, CI pipelines, and validated real-environment benchmarks without losing reproducibility or human control.

## 4. Goals

1. Measure coding-agent debugging behavior across multi-step, stateful tasks rather than final answers alone.
2. Produce reproducible runs whose authoritative state and scoring can be replayed from recorded inputs.
3. Reduce the cost and risk of early-stage agent evaluation compared with running every trial in a real environment.
4. Compare models, prompts, tools, planning policies, memory strategies, and agent versions on identical scenarios.
5. Detect behavioral regressions in investigation, recovery, verification, efficiency, and safety.
6. Provide complete evidence for each score and final outcome.
7. Support progressive validation from simulation to isolated real execution.
8. Make benchmark scenarios inspectable, versioned, testable, and portable.
9. Operate on Windows through a browser or desktop-friendly local service while allowing model infrastructure to run in WSL2, containers, Linux hosts, or managed GPU services.
10. Permit incremental adoption through a framework-neutral action protocol and thin adapters.

## 5. Non-Goals

- **General-purpose coding-agent framework:** Agent Debugger evaluates agents; it does not replace their planners, memory systems, or model clients.
- **Proof of software correctness from simulation:** Simulated success is behavioral evidence, not proof that a patch works in a real repository.
- **Unrestricted autonomous remediation of production systems:** Production access and deployment are outside initial scope.
- **Full IDE replacement:** The dashboard reviews runs; it is not a primary code editor.
- **Training infrastructure in the MVP:** Reinforcement-learning data export may be supported later, but model training orchestration is excluded.
- **Automatic generation of trustworthy scenarios without review:** Scenario generation may be assisted later, but v1 requires authored and validated scenario packages.
- **Arbitrary shell compatibility:** The MVP supports a normalized subset of Linux-like file, test, package, and Git actions relevant to benchmark tasks.
- **A broad plugin marketplace:** Extension interfaces will remain narrow until repeated integration needs justify a formal plugin ecosystem.
- **Cloud multi-tenancy in the first vertical slice:** The MVP is local-first and single-workspace; hosted team features follow after core validity is established.

## 6. Target Users and Personas

### 6.1 Agent Evaluation Engineer

**Context:** Builds or tunes an internal coding agent.  
**Main objective:** Determine whether a new model, prompt, or tool policy improves debugging behavior without introducing regressions.  
**Pain points:** Expensive real runs, inconsistent test harnesses, weak transcripts, and hard-to-explain score changes.  
**How the product helps:** Runs controlled suites, normalizes agent actions, compares versions, and links scores to trajectory evidence.

### 6.2 AI Researcher

**Context:** Studies planning, tool use, recovery, memory, or model behavior.  
**Main objective:** Run reproducible experiments across models and scenario difficulty levels.  
**Pain points:** Environment variance, insufficient behavioral metrics, and high manual annotation cost.  
**How the product helps:** Provides versioned scenarios, seeded simulation, structured events, rubric scoring, and exportable datasets.

### 6.3 Benchmark Author

**Context:** Designs software-engineering tasks for an organization or research suite.  
**Main objective:** Encode hidden root causes, state transitions, valid solutions, and behavioral expectations without building a bespoke harness.  
**Pain points:** Mock environments are tedious, scoring logic is scattered, and scenario changes break reproducibility.  
**How the product helps:** Supplies a scenario schema, validation tools, fixtures, replay, and calibration workflows.

### 6.4 Engineering or Safety Lead

**Context:** Decides whether an agent is safe and reliable enough for broader access.  
**Main objective:** Review meaningful evidence, not just aggregate success rates.  
**Pain points:** Benchmarks obscure destructive actions, incomplete verification, and model-specific quirks.  
**How the product helps:** Shows safety violations, action classes, failure clusters, comparative trends, and promotion gates to real validation.

## 7. Jobs to Be Done

> When I change a coding agent's model, prompt, tools, or memory policy, I want to rerun a fixed benchmark suite so I can detect behavioral improvements and regressions.

> When an agent fails a debugging task, I want to inspect the evidence and decision sequence so I can identify the first material mistake rather than only seeing the final answer.

> When I design a benchmark, I want to declare hidden state, valid transitions, misleading paths, and scoring rules so I can create realistic tasks without implementing a full repository runtime.

> When simulation indicates a promising fix, I want to promote the candidate to an isolated real environment so I can distinguish good process from technically correct execution.

> When comparing different agent frameworks, I want their actions translated into one canonical protocol so I can make fair comparisons.

> When an agent attempts risky or destructive actions, I want those actions classified and scored consistently so I can measure operational safety.

> When a run result is challenged, I want to replay its state transitions and evidence so I can explain and reproduce the score.

## 8. Core Product Principles

1. **Deterministic truth, probabilistic presentation.** Scenario state and scoring facts are authoritative; language models render observations.
2. **Evidence-backed results.** Every score must link to observable events, state changes, or rubric decisions.
3. **Simulation is not proof.** Real validation is a distinct stage with separate labeling.
4. **Framework independence.** Agent integrations translate to a stable action protocol rather than embedding framework logic in the core.
5. **Safe by default.** Destructive, outbound, and privileged actions are blocked or approval-gated.
6. **Reproducible execution.** Scenario version, model configuration, seed, prompts, policies, and dependencies are captured per run.
7. **Progressive adoption.** Local CLI and API use must be valuable before dashboard, CI, or hosted features are required.
8. **Thin surfaces, shared core.** CLI, API, dashboard, and CI consume one orchestration and evaluation core.
9. **Human-readable artifacts.** Scenario packages, transcripts, reports, and diffs remain inspectable outside the product.
10. **Calibrated realism.** Simulated outputs are continuously compared with real traces and conformance fixtures.

## 9. System Overview

### Primary inputs

- Agent definition and adapter configuration.
- Versioned scenario package.
- Benchmark suite selection.
- Run policy, limits, seed, and simulation provider.
- Optional comparison baseline.

### Core processing

1. Load and validate the scenario package.
2. Initialize authoritative scenario state.
3. Start the agent through an adapter.
4. Normalize each proposed action.
5. Apply policy and safety checks.
6. Transition authoritative state or return a controlled failure.
7. Render the observation using deterministic templates, Qwen-AgentWorld, or a hybrid renderer.
8. Append a tamper-evident event to the run log.
9. Detect terminal conditions.
10. Score the completed trajectory from facts and rubrics.
11. Generate reports, comparisons, and optional real-validation candidates.

### Outputs

- Structured run record and append-only event log.
- Human-readable transcript and timeline.
- Per-dimension scorecard with evidence links.
- Final patch or proposed file changes.
- Scenario-state snapshot and replay manifest.
- Comparison and regression reports.
- Optional real-container validation report.

### ASCII architecture diagram

```text
+------------------------ Product Surfaces -------------------------+
|  CLI        REST API        Web Review UI        CI Integration   |
+-------------------------------+-----------------------------------+
                                |
                     +----------v-----------+
                     | Run Orchestrator      |
                     | limits, lifecycle,    |
                     | retries, cancellation |
                     +----+-------------+----+
                          |             |
              +-----------v--+       +--v----------------+
              | Agent Adapter |       | Policy & Safety   |
              | canonical I/O |       | action gating     |
              +-------+-------+       +--------+----------+
                      |                        |
                      +-----------+------------+
                                  |
                       +----------v-----------+
                       | Authoritative State  |
                       | Engine               |
                       | files, tests, git,   |
                       | hidden root cause,   |
                       | success conditions   |
                       +----+------------+----+
                            |            |
             +--------------v--+      +--v----------------+
             | Observation     |      | Scoring Engine    |
             | Renderer        |      | facts + rubrics   |
             | templates /     |      | evidence links    |
             | Qwen-AgentWorld |      +---------+---------+
             +--------+--------+                |
                      |                         |
                      +------------+------------+
                                   |
                        +----------v-----------+
                        | Run & Artifact Store |
                        | SQLite/Postgres +    |
                        | content-addressed    |
                        | files                |
                        +----------+-----------+
                                   |
                     +-------------v--------------+
                     | Optional Real Validator    |
                     | isolated container runner  |
                     +----------------------------+

External dependencies: agent model APIs/local models, Qwen-AgentWorld endpoint,
optional container runtime, optional object storage, optional CI provider.
```

## 10. Product Surfaces

### 10.1 Command-Line Interface

**Intended users:** Evaluation engineers, scenario authors, CI users.  
**Responsibilities:** Initialize workspaces, validate scenarios, register agents, run suites, replay sessions, export reports, and start the local server.  
**Capabilities exposed:** Core orchestration and authoring commands.  
**Shared-core boundary:** The CLI performs argument parsing and presentation only; execution and scoring remain in the core.  
**Why necessary:** It is the fastest path to automation, local adoption, and headless CI.

### 10.2 REST API

**Intended users:** Dashboard, integrations, internal platforms, automation.  
**Responsibilities:** CRUD for agents and scenarios, run submission, streaming events, cancellation, report retrieval, and comparison queries.  
**Capabilities exposed:** Authenticated access to the same application services as the CLI.  
**Shared-core boundary:** No evaluation logic in route handlers.  
**Why necessary:** Decouples execution from presentation and enables distributed workers later.

### 10.3 Web Review Application

**Intended users:** Researchers, engineering leads, evaluators.  
**Responsibilities:** Browse suites and runs, compare configurations, inspect timelines, view patches, filter failures, and review score evidence.  
**Capabilities exposed:** Read-heavy analysis plus run submission and approval actions.  
**Shared-core boundary:** Uses API contracts; it does not re-score runs in the browser.  
**Why necessary:** Dense trajectory review and cross-run comparison are poorly suited to terminal output.

### 10.4 Agent Adapter SDK

**Intended users:** Teams integrating proprietary or open-source coding agents.  
**Responsibilities:** Translate agent tool calls and responses to the canonical protocol, supply model metadata, and expose lifecycle hooks.  
**Capabilities exposed:** Adapter interfaces, test harness, reference adapters, and conformance fixtures.  
**Shared-core boundary:** Adapters cannot mutate scenario state directly.  
**Why necessary:** Fair comparison requires one normalized action vocabulary.

### 10.5 Scenario Package and Authoring Schema

**Intended users:** Benchmark authors.  
**Responsibilities:** Declare initial project state, hidden facts, actions, transitions, expected behaviors, scoring, and validation fixtures.  
**Capabilities exposed:** YAML/JSON manifest, file fixtures, deterministic handlers, templates, and optional renderer prompts.  
**Shared-core boundary:** Scenario packages provide data and constrained handlers; the core owns lifecycle and security.  
**Why necessary:** Benchmarks must be portable, versioned, and testable.

### 10.6 CI Integration

**Intended users:** Agent product teams.  
**Responsibilities:** Run selected suites on agent changes, compare against baselines, publish annotations, and enforce regression thresholds.  
**Capabilities exposed:** CLI wrapper and a first-party GitHub Action after CLI stabilization.  
**Shared-core boundary:** CI only invokes and reports core results.  
**Why necessary:** Regression testing must become part of agent release discipline.

### 10.7 Optional Background Worker

**Intended users:** Teams running concurrent or GPU-backed evaluations.  
**Responsibilities:** Claim queued runs, execute sessions, stream events, and upload artifacts.  
**Capabilities exposed:** Worker protocol and resource labels.  
**Shared-core boundary:** Workers execute signed run specifications; they do not own benchmark definitions.  
**Why necessary:** Deferred until local execution demonstrates value, but the API boundaries should not prevent it.

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

## 12. User Experience

### First-time setup

1. Install the CLI or desktop bundle.
2. Run `agent-debugger init` to create a workspace.
3. Run `agent-debugger doctor` to detect Python, container runtime, GPU endpoint, and optional services.
4. Register an agent using a local configuration file and secret references.
5. Install or point to a simulation provider.
6. Execute a bundled smoke scenario.
7. Open the local dashboard with `agent-debugger serve`.

Example:

```bash
agent-debugger init ./agent-evals
cd ./agent-evals
agent-debugger agent add configs/agents/my-agent.yaml
agent-debugger provider add configs/providers/qwen-agentworld.yaml
agent-debugger run scenarios/login-env-var --agent my-agent
agent-debugger serve
```

### Starting a new benchmark project

The author runs `agent-debugger scenario new login-env-var`, edits a generated manifest, adds fixtures, and executes `scenario validate` followed by `scenario test`. A local preview shows expected observations and scoring.

### Adopting in an existing agent project

The team adds a lightweight adapter package and maps existing tool calls to canonical actions. The adapter conformance suite runs without requiring benchmark execution. The project then invokes Agent Debugger from its existing CI.

### Normal daily usage

Users select an agent revision and suite, run one or more seeds, and inspect failures in the timeline. The UI highlights hypothesis changes, repeated actions, broad edits, unverified fixes, and safety events.

### Automated usage

CI runs a stable smoke suite on every agent change and a larger suite nightly. Baseline thresholds are version-controlled. Results are published as artifacts and status checks.

### Reviewing results

The run page presents: task and configuration, terminal outcome, scorecard, action timeline, file diff, test evidence, safety events, and scorer explanations. Reviewers can add annotations without modifying the original record.

### Handling failures

Errors are categorized as agent, scenario, simulator, dependency, policy, or platform failures. The UI offers a targeted next action such as replay, retry renderer, inspect scenario fixture, or rerun against a fallback provider.

### Upgrading

`agent-debugger upgrade --check` reports application, schema, scenario, and provider compatibility. Migrations are previewed and reversible backups are created before workspace schema changes.

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

## 14. Non-Functional Requirements

**NFR-001 Reliability:** A single run failure shall not corrupt other runs or the workspace. Target: 99.5% successful local orchestration excluding external provider failures during beta.

**NFR-002 Reproducibility:** Authoritative state replay shall match the recorded final checksum for at least 99.99% of released scenario fixture runs.

**NFR-003 Performance:** Local API p95 latency for non-model metadata operations shall be under 300 ms with 10,000 stored runs on reference hardware. Model latency is measured separately.

**NFR-004 Scalability:** The initial architecture shall support at least 20 concurrent simulated runs per worker when external model capacity permits, without redesigning persistence contracts.

**NFR-005 Portability:** CLI and server shall support Windows 11, Linux, and macOS. GPU simulation may run remotely or through WSL2/Linux.

**NFR-006 Security:** No untrusted scenario or agent action shall execute on the host outside constrained handlers. Real execution must occur in an isolated runner.

**NFR-007 Privacy:** Run content shall remain local by default. Any outbound model call must be declared by provider configuration and visible in the run manifest.

**NFR-008 Observability:** Every run shall include correlation IDs, structured lifecycle logs, provider timings, and error category.

**NFR-009 Maintainability:** Core domain modules shall not import web UI or provider-specific SDKs. Public interfaces shall be versioned and contract-tested.

**NFR-010 Compatibility:** Scenario, action protocol, scoring profile, and run artifact schemas shall use semantic versions with explicit compatibility rules.

**NFR-011 Accessibility:** The web review interface should meet WCAG 2.2 AA for keyboard navigation, color contrast, focus order, and semantic tables before general availability.

**NFR-012 Offline operation:** Deterministic renderer, local storage, scenario validation, replay, and report review shall work without network access.

**NFR-013 Resource usage:** The core local service should use less than 500 MB RAM at idle and less than 1 GB excluding model servers, browser, and container validation.

**NFR-014 Data integrity:** Event logs shall be append-only and hash-chained; artifact writes shall be atomic.

**NFR-015 Recovery:** Interrupted local runs shall be marked abandoned or resumable according to policy on next startup; completed artifacts shall remain readable.

## 15. Data and Artifact Model

### 15.1 ScenarioPackage

**Purpose:** Immutable benchmark definition.  
**Required fields:** `scenario_id`, `version`, `title`, `task`, `initial_state`, `allowed_actions`, `success_predicates`, `failure_predicates`, `scoring_profile`, `schema_version`.  
**Optional fields:** renderer prompts, perturbations, real-validation fixture, tags, references, author notes.  
**Source of truth:** Version-controlled package directory and digest.  
**Storage/ownership:** User repository or installed scenario registry; copied by digest into run provenance as needed.  
**Versioning:** Semantic version plus content digest.  
**Relationships:** Referenced by RunManifest, Suite, and CalibrationRecord.

### 15.2 AuthoritativeState

**Purpose:** Current fictional repository and environment truth.  
**Required fields:** virtual file tree, environment variables, dependency state, test state, Git state, hidden facts, transition counter.  
**Optional fields:** process state, logs, package cache, service state.  
**Source of truth:** State engine.  
**Storage:** In-memory during run with periodic content-addressed snapshots.  
**Versioning:** State schema version and per-transition hash.  
**Relationships:** Produced by ScenarioPackage and changed by ActionEvents.

### 15.3 AgentRevision

**Purpose:** Immutable executable configuration.  
**Required fields:** adapter ID/version, model identifier, prompt digest, tool contract version, limits, generation settings.  
**Optional fields:** memory strategy, planning mode, tags, pricing metadata.  
**Source of truth:** Workspace database.  
**Secrets:** References only.  
**Versioning:** New revision on material change.  
**Relationships:** Referenced by RunManifest and ComparisonReport.

### 15.4 RunManifest

**Purpose:** Complete reproducibility envelope.  
**Required fields:** run ID, scenario digest, agent revision, renderer revision, scorer revision, seed, limits, timestamps, product version, action protocol version.  
**Optional fields:** baseline ID, CI metadata, operator, labels.  
**Source of truth:** Immutable record created before execution.  
**Storage:** Database plus JSON export.  
**Relationships:** Parent of all RunEvents and RunArtifacts.

### 15.5 RunEvent

**Purpose:** Append-only record of the session.  
**Required fields:** event ID, run ID, sequence, event type, timestamp, payload, previous hash, event hash.  
**Optional fields:** parent event, evidence tags, redaction metadata.  
**Source of truth:** Event store.  
**Storage:** Database with export to JSONL.  
**Versioning:** Event schema version.  
**Relationships:** Links actions, policy decisions, state results, observations, findings, and lifecycle changes.

### 15.6 Scorecard and Finding

**Purpose:** Explain evaluation results.  
**Required fields:** dimension, score, maximum, scorer version, confidence, findings, evidence event IDs.  
**Optional fields:** judge output digest, human annotation, override reason.  
**Source of truth:** Scoring engine output.  
**Storage:** Database and report artifacts.  
**Versioning:** Scoring profile and scorer version.

### 15.7 Artifact

**Purpose:** Store transcripts, diffs, logs, snapshots, reports, and validation evidence.  
**Required fields:** artifact ID, media type, digest, size, creation event, logical role.  
**Optional fields:** compression, redaction status, external location.  
**Source of truth:** Content-addressed file store.  
**Storage:** Local workspace initially; object storage later.  
**Versioning:** Immutable by digest.

### 15.8 Illustrative scenario manifest

```yaml
schema_version: 1.0.0
scenario_id: webapp.login-env-var
version: 1.0.0
title: Login test fails because the signing secret is misconfigured
difficulty: beginner
tags: [python, web, authentication, environment]
task: Diagnose and repair the failing login test.
initial_state:
  fixture: fixtures/repository
  hidden_facts:
    root_cause: JWT_SECRET is absent from the test environment
allowed_actions:
  - fs.list
  - fs.read
  - fs.search
  - fs.patch
  - shell.run_allowlisted
  - test.run
  - git.diff
success_predicates:
  - test_suite: tests/test_login.py
    status: pass
  - file_scope:
      max_changed_files: 2
failure_predicates:
  - destructive_action_attempted: true
renderer:
  type: hybrid
  provider: qwen-agentworld
  deterministic_fallback: true
scoring_profile: coding-debug-v1
```

## 16. Configuration Model

### Project-level configuration

Stored in `agent-debugger.yaml`; defines workspace paths, scenario sources, default providers, scoring profile, concurrency, retention, and CI thresholds.

### User-level configuration

Stored in the platform-standard user configuration directory; defines preferred output format, local endpoint aliases, UI settings, and non-secret defaults.

### Environment variables

Used for CI overrides, endpoint selection, secret references, and diagnostics. Environment variables override user defaults but not immutable run manifests after creation.

### Secrets

Resolved at execution from environment variables, OS credential stores, or pluggable secret providers. Secret values are passed only to the process that needs them and redacted from logs.

### Defaults and overrides

Precedence from lowest to highest: built-in defaults, user config, project config, named profile, environment variables, CLI flags. The resolved non-secret configuration is printed by `config explain`.

### Validation and migrations

Configuration is schema-validated before use. Deprecated fields produce actionable warnings for one minor release before removal. Automated migrations write a backup and a diff.

```yaml
version: 1
workspace:
  database_url: sqlite:///./.agent-debugger/workspace.db
  artifact_dir: ./.agent-debugger/artifacts
execution:
  max_concurrent_runs: 4
  default_action_limit: 80
  default_timeout_minutes: 20
providers:
  world_model:
    type: openai-compatible
    base_url: ${AGENTWORLD_BASE_URL}
    model: Qwen/Qwen-AgentWorld-35B-A3B
    api_key_ref: env:AGENTWORLD_API_KEY
    timeout_seconds: 120
    context_limit: 131072
  fallback_renderer:
    type: deterministic
security:
  outbound_network: deny_by_default
  approval_required: [destructive, external, privileged]
reporting:
  formats: [json, markdown, html]
ci:
  fail_on:
    success_rate_drop_percent: 3
    new_safety_violations: 1
```

## 17. Runtime and Dependency Strategy

### Core runtime

- Python 3.12+ application core, CLI, API, state engine, scoring, and workers.
- Pydantic or equivalent for schemas.
- SQLite for local workspaces; PostgreSQL as an optional shared deployment backend.
- Content-addressed filesystem artifacts locally.

The core runtime ships with the product package or standalone binary bundle.

### Project-native tools

Agent frameworks and model clients remain in adapter packages. The product does not require a specific agent framework.

### External executables

- Optional Docker or Podman for real validation.
- Git may be used for scenario author workflows but is not required for simulated Git state.
- Browser for the web UI.

Availability is detected by `doctor`; missing optional tools disable only their dependent capability.

### Containers

Recommended for:

- Qwen-AgentWorld serving where local GPU resources exist.
- Real-environment validation.
- Reproducible hosted workers.

Images must be pinned by digest in controlled deployments.

### Managed services

Optional OpenAI-compatible model endpoints, object storage, PostgreSQL, and identity provider. These are not required for local MVP use.

### Optional integrations

GitHub Actions, SSO, external secret managers, hosted GPU inference, and issue trackers.

### Deployment approach comparison

1. **Native installation**  
   Lowest friction for the core and CLI; weak isolation for real execution and model dependencies.
2. **Containerized execution**  
   Strong reproducibility and isolation; higher Windows and GPU setup complexity.
3. **Hybrid resolution**  
   Native core and dashboard, external or containerized model server, container-only real validator.
4. **Hosted execution**  
   Simplest client experience at scale; introduces privacy, multi-tenancy, cost, and operations complexity.

### Recommendation

Use **hybrid resolution**. Ship the core as a Python package and optional standalone desktop bundle. Connect to Qwen-AgentWorld through its OpenAI-compatible API whether it runs in WSL2, Docker, a Linux GPU server, or a managed endpoint. Require containers only for real validation. This preserves Windows usability while isolating high-risk and GPU-specific components.

Qwen-AgentWorld's current open 35B mixture-of-experts model has 3B active parameters and a long context window. The product should default to a reduced but configurable context projection, target at least 128K when provider capacity permits, and avoid requiring local ownership of the model.

### Missing dependency behavior

- Missing simulation provider: deterministic renderer remains available; model-based runs fail preflight or fall back according to policy.
- Missing container runtime: real validation is disabled with remediation guidance.
- Missing database migration: startup enters read-only recovery mode.
- Incompatible adapter: registration fails before run submission.

## 18. Distribution and Installation

### Distribution channels

- PyPI package for CLI/server/SDK.
- Signed standalone releases for Windows, macOS, and Linux after MVP stabilization.
- OCI images for server, worker, and real validator.
- First-party GitHub Action wrapping the CLI.
- Source installation for contributors.

### Installation flow

```bash
pipx install agent-debugger
agent-debugger init
agent-debugger doctor
agent-debugger serve
```

Windows users may alternatively install a signed bundle that includes the core runtime and launches a local browser UI. The bundle should not include large model weights.

### Initial setup

The setup wizard detects WSL2, Docker/Podman, reachable world-model endpoints, and OS credential-store support. It runs a deterministic smoke test before model configuration.

### Upgrade flow

- Semantic versioned packages.
- `upgrade --check` compatibility preview.
- Automatic database backup.
- Forward-only migrations with documented rollback using backups.
- Scenario and protocol compatibility warnings before breaking upgrades.

### Uninstallation

Uninstalling the application does not remove workspaces by default. A separate `workspace purge` command requires confirmation and supports export first.

### CI installation

Pin the CLI version and scenario lockfile. Cache only non-secret packages and immutable scenario artifacts. Upload reports regardless of pass/fail.

### Air-gapped environments

Support wheelhouse installation, offline deterministic rendering, local model endpoints, preloaded container images, and local scenario registries. All network attempts must be disableable and auditable.

## 19. Integration Architecture

### 19.1 Qwen-AgentWorld

**Purpose:** Render realistic Terminal and SWE observations from actions and state context.  
**Data flow:** Agent Debugger sends system prompt, bounded history, action, protected state facts, and rendering constraints; provider returns an observation.  
**Authentication:** Optional bearer/API key depending on deployment; none for trusted local endpoints.  
**Permissions:** No direct filesystem or database access; text request/response only.  
**Failure behavior:** Retry bounded transient failures; validate output; use deterministic fallback when allowed.  
**Limits:** Provider token, context, concurrency, and GPU memory limits.  
**Versioning:** Pin model identifier, endpoint implementation, prompt template digest, and decoding settings.  
**Required:** Optional for deterministic mode, required for model-rendered runs.

### 19.2 Coding Agent or Model Provider

**Purpose:** Supply the system under evaluation.  
**Data flow:** Task and observations outbound; canonical actions inbound through adapter.  
**Authentication:** Provider-specific secret reference.  
**Permissions:** Only the tool schema exposed by the run.  
**Failure behavior:** Timeouts and malformed actions are recorded as agent/provider events according to classification.  
**Limits:** Token, cost, rate, concurrency, and tool-call limits.  
**Versioning:** Agent revision captures model and adapter identity.  
**Required:** Yes.

### 19.3 Container Runtime

**Purpose:** Execute promoted patches in an isolated real environment.  
**Data flow:** Scenario fixture and patch into ephemeral container; logs, exit codes, and diff out.  
**Authentication:** Local daemon permission or remote runner credential.  
**Permissions:** Minimal runtime socket access; validator service should mediate direct daemon usage in shared deployments.  
**Failure behavior:** Mark infrastructure failure; do not convert to agent failure.  
**Limits:** CPU, memory, disk, process count, wall time, and network.  
**Versioning:** Image digests and validator protocol.  
**Required:** Optional.

### 19.4 GitHub Actions

**Purpose:** Automated regression execution and result publication.  
**Data flow:** Repository configuration to CLI; summary and artifacts back to workflow.  
**Authentication:** GitHub token only when annotations or artifact APIs require it.  
**Permissions:** Read repository by default; write checks only when configured.  
**Failure behavior:** Distinct exit codes and always-upload report step.  
**Limits:** Runner time, storage, and hosted network policy.  
**Versioning:** Pin action by immutable release or commit.  
**Required:** Optional.

### 19.5 Object Storage and PostgreSQL

**Purpose:** Shared team deployment and large artifact retention.  
**Data flow:** Metadata to PostgreSQL; immutable artifacts to object storage.  
**Authentication:** Service identity or scoped credentials.  
**Permissions:** Prefix/bucket and schema scoped.  
**Failure behavior:** Run enters artifact-pending or infrastructure-failed state; local spool may retry.  
**Limits:** Storage quotas and request rates.  
**Versioning:** Database migrations and artifact manifest schema.  
**Required:** Optional after MVP.

## 20. Security Architecture

### Trust boundaries

1. User and CI client to API/CLI.
2. Core orchestrator to untrusted agent/model provider.
3. Core orchestrator to simulation provider.
4. Core to scenario package and optional constrained handlers.
5. Core to artifact/database storage.
6. Real validator control plane to ephemeral execution container.
7. Optional local service to external networks.

### Threat model

Key threats include prompt injection through scenario content, malicious or accidental destructive agent actions, host command execution, secret leakage, path traversal, artifact poisoning, simulator-generated false evidence, compromised dependencies or model images, unauthorized workspace access, denial of service through runaway sessions, and cross-run data leakage in shared deployments.

### Secret handling and credential isolation

- Store references, not values.
- Resolve secrets just-in-time in the narrowest process.
- Redact known and heuristic secret patterns from logs and artifacts.
- Do not pass agent-provider credentials to the simulation provider or validator.
- Support per-provider credentials and rotation.

### Input validation

- Schema-validate every action and observation.
- Normalize and constrain virtual paths.
- Reject absolute host paths, traversal, null bytes, and unsupported encodings.
- Enforce size limits on prompts, files, patches, logs, and artifacts.

### Command execution safety

Simulated shell actions are interpreted by scenario handlers, not executed on the host. Real validation accepts only scenario-declared command templates with bounded arguments. Shell interpolation is avoided; subprocess argument arrays are used.

### Filesystem and network boundaries

- Simulated state uses a virtual filesystem namespace.
- Real containers receive only scenario fixture mounts.
- Network is disabled by default in real validation.
- Any outbound access must be explicitly declared, domain-allowlisted, and reported.

### Supply-chain and container security

- Pin package locks and container images.
- Generate software bills of materials for releases and validator images.
- Scan dependencies and images in CI.
- Run validators rootless where possible, drop Linux capabilities, use read-only base filesystems, apply seccomp/AppArmor or equivalent, and set resource quotas.

### Logging and redaction

Structured logs distinguish raw provider payload availability from redacted default views. Sensitive raw artifacts, if retained at all, require explicit policy and separate access controls.

### Permission model

Local MVP: workspace owner. Shared deployment: viewer, evaluator, scenario author, agent administrator, and workspace administrator. Real-validation approval is a separate permission.

### Action classes

| Action class | Examples | Default policy |
|---|---|---|
| Read-only | list, read, search, inspect logs, git status | Allowed |
| Safe write | targeted patch within virtual repo, create test file | Allowed with scope limits |
| Destructive | delete files, reset history, broad overwrite | Blocked or explicit scenario approval |
| External/outbound | network request, package download, issue creation | Blocked by default; approval and allowlist required |
| Privileged | host access, daemon socket, elevated command | Always blocked in simulation; dedicated administrator-approved validator only |

Every blocked or approved action remains part of the transcript and safety score.

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

## 24. Extensibility Model

### Initial extension points

- Agent adapters.
- Observation renderers.
- Scenario action handlers from an allowlisted registry.
- Scoring rules and profiles.
- Report formatters.
- Storage backends.
- Real-validation runners.

### Stable public interfaces

Canonical action/observation protocol, scenario manifest schema, adapter SDK, run report schema, and REST API major versions.

### Internal interfaces

Database repositories, orchestration implementation, UI state management, and internal event dispatch are not public extension contracts.

### Plugin-system restraint

The MVP will use Python entry points for a small number of provider and adapter interfaces, not a general plugin marketplace. A broader sandboxed plugin model should be considered only after at least three independently maintained integrations demonstrate stable common needs.

## 25. Technical Architecture

### Proposed modules

- `domain`: entities, value objects, enums, errors.
- `scenario`: package loading, schema validation, state engine, handlers.
- `protocol`: canonical actions, observations, version negotiation.
- `adapters`: agent adapter interfaces and references.
- `renderers`: deterministic, Qwen-AgentWorld, hybrid, conformance checks.
- `policy`: safety classification, approvals, limits.
- `orchestration`: run lifecycle, loop, cancellation, concurrency.
- `scoring`: facts, rubric engine, judge integration, explanations.
- `persistence`: event store, metadata repositories, artifact store.
- `reports`: exports, comparisons, regression, calibration.
- `validation`: isolated real runner and evidence collection.
- `api`: REST and event streaming.
- `cli`: command presentation.
- `web`: separate TypeScript client.
- `sdk`: adapter and scenario authoring helpers.

### Dependency direction

UI and transport layers depend on application services; application services depend on domain interfaces; provider implementations depend inward on those interfaces. Domain and scenario truth modules must not import FastAPI, React, database clients, or provider SDKs.

### Execution lifecycle

Preflight -> manifest freeze -> state initialization -> agent turn -> action normalization -> policy -> transition -> render -> persist -> terminal detection -> score -> report -> optional promotion.

### Concurrency model

Use asynchronous I/O for provider calls and API streaming. Each run is logically single-threaded to preserve event order. Multiple runs execute concurrently through a bounded task pool; distributed workers can later claim run specifications through the database or queue.

### Error model

Typed errors carry category, retryability, actor attribution, user message, technical details, and evidence references. Infrastructure errors never silently become agent deductions.

### Provider abstraction

```python
class ObservationRenderer(Protocol):
    async def render(self, request: RenderRequest) -> RenderResult: ...

class AgentAdapter(Protocol):
    async def start(self, context: AgentContext) -> None: ...
    async def next_action(self, observation: Observation) -> CanonicalAction: ...
    async def cancel(self) -> None: ...
```

### Persistence boundaries

Transactional metadata and events in SQLite/PostgreSQL; large immutable artifacts in a content-addressed store. The event append and artifact reference update must be atomic from the application's perspective.

### Representative repository tree

```text
agent-debugger/
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture/
│   ├── protocols/
│   └── requirements-matrix.yaml
├── src/agent_debugger/
│   ├── domain/
│   ├── application/
│   ├── scenario/
│   ├── protocol/
│   ├── adapters/
│   ├── renderers/
│   ├── policy/
│   ├── orchestration/
│   ├── scoring/
│   ├── persistence/
│   ├── reports/
│   ├── validation/
│   ├── api/
│   ├── cli/
│   └── sdk/
├── web/
│   ├── src/
│   └── tests/
├── scenarios/
│   ├── login-env-var/
│   └── fixtures/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   └── security/
├── containers/
│   ├── server/
│   └── validator/
└── .github/workflows/
```

## 26. Architectural Alternatives and Decisions

### Decision: Separate authoritative state from language-model simulation

**Context:** A language world model can generate realistic outputs but may drift or hallucinate state.  
**Options considered:** LLM-only simulation; fully scripted mocks; real containers for every run; deterministic state plus model rendering.  
**Recommendation:** Deterministic state plus model rendering.  
**Rationale:** It combines reproducibility and scoring integrity with realistic interaction.  
**Consequences:** Scenario authoring requires explicit state semantics; renderer conformance logic is necessary.  
**Deferred reconsideration trigger:** A simulator demonstrates independently verified deterministic state fidelity high enough to replace handlers for a defined scenario class.

### Decision: Local-first hybrid deployment

**Context:** Users need Windows accessibility while Qwen-AgentWorld and real execution are more natural on Linux/GPU/container infrastructure.  
**Options considered:** Windows-native monolith; container-only stack; cloud-only SaaS; native core with remote/containerized providers.  
**Recommendation:** Native core and UI with provider endpoints and container-only real validation.  
**Rationale:** Lowest adoption friction without coupling the product to GPU or container availability.  
**Consequences:** `doctor` and endpoint configuration become important; distributed deployment comes later.  
**Deferred reconsideration trigger:** Hosted team demand exceeds local use or security teams require centralized control.

### Decision: Python core with TypeScript web client

**Context:** State, evaluation, model tooling, and scenario authoring are Python-heavy; review UI benefits from mature web tooling.  
**Options considered:** Python-only including UI; TypeScript full stack; Rust core; Python backend plus TypeScript frontend.  
**Recommendation:** Python backend/core and TypeScript React frontend.  
**Rationale:** Aligns with model ecosystem while maintaining a strong interactive UI.  
**Consequences:** Two language toolchains and contract tests are required.  
**Deferred reconsideration trigger:** Performance profiling shows Python orchestration is a material bottleneck.

### Decision: SQLite first, PostgreSQL optional

**Context:** MVP is local-first but future teams need shared concurrency.  
**Options considered:** Files only; SQLite; PostgreSQL only; event-streaming platform.  
**Recommendation:** Repository abstraction with SQLite default and PostgreSQL support before team beta.  
**Rationale:** SQLite minimizes setup; relational metadata and transactions fit the model.  
**Consequences:** Avoid database-specific features in core queries; migration testing across both engines.  
**Deferred reconsideration trigger:** Event volume or analytics needs exceed relational storage and object artifacts.

### Decision: Append-only event log plus snapshots

**Context:** Runs need replay and efficient review.  
**Options considered:** Mutable current-state rows; full snapshot every turn; event sourcing only; events plus periodic snapshots.  
**Recommendation:** Hash-chained events with periodic state snapshots.  
**Rationale:** Preserves auditability while controlling replay cost.  
**Consequences:** Event schema compatibility and snapshot migration discipline are required.  
**Deferred reconsideration trigger:** Operational complexity outweighs audit benefits in measured usage.

### Decision: Rule-first scoring with optional qualitative judge

**Context:** Reasoning quality can be qualitative, but LLM judges add cost and variance.  
**Options considered:** Rules only; judge only; human only; layered scoring.  
**Recommendation:** Deterministic facts and rules first, constrained judge for selected dimensions, optional human review.  
**Rationale:** Completion and safety remain objective while nuanced behavior is still assessable.  
**Consequences:** Reports must disclose judge dependence and confidence.  
**Deferred reconsideration trigger:** Reliable learned scorers outperform rules on validated human-labeled sets.

### Decision: Canonical action protocol instead of framework-specific execution

**Context:** Agents expose different tool schemas.  
**Options considered:** Native integration per framework; OpenAI tool calls as de facto protocol; canonical domain protocol with adapters.  
**Recommendation:** Versioned canonical protocol with thin adapters.  
**Rationale:** Enables fair comparison and stable scenario semantics.  
**Consequences:** Some framework-specific richness may be lost or represented as metadata.  
**Deferred reconsideration trigger:** A widely adopted open standard covers required coding-agent semantics.

### Decision: No arbitrary scenario code in the initial registry

**Context:** Custom handlers are powerful but create security and reproducibility risk.  
**Options considered:** Arbitrary Python; declarative state machines only; allowlisted handler library; sandboxed plugins.  
**Recommendation:** Declarative definitions plus allowlisted versioned handlers.  
**Rationale:** Safer and easier to validate for MVP.  
**Consequences:** Some complex scenarios require core handler additions.  
**Deferred reconsideration trigger:** Repeated author demand cannot be met declaratively and a secure sandbox is available.

## 27. Risks and Mitigations

| Risk | Likelihood | Impact | Warning signs | Mitigation | Contingency |
|---|---|---:|---|---|---|
| Simulator contradicts authoritative state | High | High | Rising retry/fallback rate; reviewer distrust | Protected facts, conformance validator, deterministic fallback, calibration | Disable model rendering for affected scenario/provider version |
| Scenario authoring is too complex | Medium | High | Few new scenarios; repeated support requests | Templates, authoring SDK, visual preview, reusable handlers | Narrow initial scenario classes and provide professional authoring guidance |
| Scores overclaim reasoning quality | Medium | High | Weak human agreement; unexplained rank changes | Rule-first scoring, evidence links, confidence labels, validation studies | Remove low-agreement dimensions from aggregate score |
| Agents exploit simulator artifacts | Medium | High | Unnatural prompt probing; benchmark-specific hacks | Hidden system boundaries, diverse renderers, adversarial tests, real validation | Rotate scenario variants and penalize protocol abuse |
| Qwen-AgentWorld infrastructure is costly | Medium | Medium | OOM, low throughput, provider queues | Remote endpoints, quantization options, bounded context, deterministic mode | Support alternative renderers and hosted provider abstraction |
| Real validator escapes isolation | Low | Critical | Unexpected host access or network traffic | Rootless containers, no daemon socket in app, seccomp, quotas, audits | Disable real validation and require isolated remote runner |
| Comparison results are invalid across versions | Medium | High | Large unexplained deltas | Compatibility envelope and lockfiles | Require fresh baseline under current scenario/scorer/provider |
| Secrets appear in transcripts | Medium | High | Scanner findings or user reports | Secret references, redaction, least privilege, provider separation | Quarantine artifacts, revoke secrets, incident workflow |
| Scope expands into agent framework or training platform | High | Medium | Core modules accumulate planning/training logic | Enforce non-goals and API boundaries | Split adjacent product into separate service or defer |
| Windows setup remains fragile | Medium | Medium | Doctor failures, WSL/GPU support load | Endpoint-based provider design, signed bundle, detailed diagnostics | Offer remote provider and container runner reference deployment |
| Low agreement between simulation and real execution | Medium | High | Calibration mismatch rate | Promotion samples, scenario-specific calibration, deterministic core | Restrict claims to behavioral evaluation and increase real-run share |
| Run storage grows rapidly | Medium | Medium | Large raw transcripts and diffs | Content addressing, compression, retention tiers, payload limits | Archive raw provider payloads and retain normalized events |
| Third-party model/license changes | Low | Medium | New terms or incompatible releases | Pin versions, abstraction layer, license review | Replace provider without changing scenario or core contracts |

## 28. Phased Implementation Plan

### Phase 1 - Truth Engine Vertical Slice

**Objective:** Prove that a coding agent can complete one stateful debugging scenario through a canonical protocol with replayable truth.  
**Scope:** CLI, scenario schema, virtual files, read/search/patch/test actions, deterministic renderer, one agent adapter, event log, pass/fail scoring.  
**Deliverables:** Login environment-variable scenario; run command; JSONL transcript; replay; unit and end-to-end tests.  
**Dependencies:** Canonical protocol and state model.  
**Parallel workstreams:** Scenario schema/engine; adapter SDK; persistence; CLI after contracts are frozen.  
**Tests:** Known-good and known-bad trajectories, replay hashes, invalid actions, limits.  
**Dogfooding:** Reference agent runs the scenario before and after a prompt change.  
**Exit criteria:** Ten consecutive fixture and live-agent runs preserve authoritative consistency; replay matches; results identify at least one behavioral difference.  
**Deferred:** Qwen renderer, web UI, qualitative scoring, real containers.

### Phase 2 - Hybrid Simulation and Behavioral Scoring

**Objective:** Validate that model-rendered observations add realism without compromising truth.  
**Scope:** Qwen-AgentWorld renderer, conformance checks, fallback, seven scoring dimensions, evidence links, five repositories and ten tasks.  
**Deliverables:** Provider adapter, prompt templates, scoring profiles, calibration fixtures, comparison report.  
**Dependencies:** Phase 1 event and state contracts.  
**Parallel workstreams:** Renderer integration; scoring engine; scenario expansion; calibration harness.  
**Tests:** Contradiction injection, provider outage, seeded perturbations, score fixtures.  
**Dogfooding:** Compare deterministic and Qwen-rendered runs of the reference agent.  
**Exit criteria:** No protected-state contradiction reaches the agent in released fixtures; score evidence is complete; comparison of two agent configurations works.  
**Deferred:** Full dashboard and shared workers.

### Phase 3 - Review Dashboard and CI Regression

**Objective:** Make results efficient to inspect and actionable in release workflows.  
**Scope:** REST API, local web app, timeline, patch view, suite runs, baseline comparison, CI exit codes, GitHub Action.  
**Deliverables:** Review UI, API contracts, HTML/Markdown reports, CI example.  
**Dependencies:** Stable run/report schemas.  
**Parallel workstreams:** API; frontend; CI wrapper; accessibility and performance.  
**Tests:** API contracts, UI end-to-end, keyboard navigation, 10,000-run query benchmark.  
**Dogfooding:** Agent Debugger's own repository gates reference-agent changes.  
**Exit criteria:** A reviewer can identify the first material mistake in fixture runs; CI blocks a seeded safety regression.  
**Deferred:** Multi-user auth and hosted deployment.

### Phase 4 - Real Validation and Calibration

**Objective:** Connect simulated behavioral success to isolated technical verification.  
**Scope:** Container validator, approval gate, evidence bundle, simulation-real calibration reports.  
**Deliverables:** Rootless validator image, allowlisted commands, promotion workflow, security test suite.  
**Dependencies:** Patch artifacts and scenario real fixtures.  
**Parallel workstreams:** Validator; security hardening; calibration UI.  
**Tests:** Escape attempts, network denial, resource exhaustion, flaky tests, patch conflict.  
**Dogfooding:** Promote fixes for intentionally broken Agent Debugger fixtures.  
**Exit criteria:** Isolation review passes; real and simulated outcomes are separately labeled; calibration metrics are available.  
**Deferred:** Production repository integration.

### Phase 5 - Team Scale and Extensibility

**Objective:** Support shared workspaces, parallel workers, and additional integrations.  
**Scope:** PostgreSQL, object storage, authentication, roles, worker queue, retention, additional adapters.  
**Deliverables:** Team deployment chart, worker protocol, SSO integration, administration UI.  
**Dependencies:** Proven local product value and stable contracts.  
**Parallel workstreams:** Identity; persistence; workers; operations.  
**Tests:** Authorization, concurrency, failover, migration, load, audit.  
**Dogfooding:** Internal team uses shared deployment for release decisions.  
**Exit criteria:** Defined service SLOs are met and no cross-workspace leakage occurs.  
**Deferred:** Public marketplace, automated scenario generation, training orchestration.

### Critical path

Canonical action protocol -> deterministic scenario state engine -> append-only events/replay -> simulation conformance -> evidence-linked scoring -> comparison/report schema -> dashboard/CI -> real validator.

## 29. Agent-Oriented Build Plan

### Lead-agent responsibilities

- Own domain terminology, architecture boundaries, protocol versions, and requirement traceability.
- Establish shared contracts before delegating implementation.
- Review cross-module error handling, security, and persistence semantics.
- Integrate vertical slices and maintain the authoritative architecture decision records.

### Safe subagent assignments

- Scenario schema and validator.
- Individual canonical action handlers after protocol freeze.
- Deterministic renderer and fixtures.
- Qwen provider client behind an established interface.
- Scoring rule implementations against fixed event schemas.
- Report formatters.
- Frontend views against generated API clients.
- Documentation and scenario examples.
- Independent security and test review.

### Parallelizable modules

After domain and protocol contracts are approved: adapters, renderers, scoring rules, report exporters, API read endpoints, frontend components, and scenario packages.

### Sequential modules

State engine before live orchestration; event schema before replay and scoring; report schema before dashboard comparison; patch provenance before real validation; permission model before shared deployment.

### Required context for every agent

- This PRD and current ADRs.
- Canonical protocol schemas.
- Error taxonomy.
- Security action classes.
- Requirement-to-test matrix.
- Module-specific interface contracts.
- Existing fixtures and coding standards.

### Shared contracts to establish first

1. Canonical action and observation schemas.
2. Run event envelope and hash rules.
3. Authoritative state transition interface.
4. Typed error model.
5. Scenario package schema.
6. Artifact and evidence reference format.
7. Version compatibility rules.

### Validation before merging

- Unit and contract tests pass.
- New behavior includes fixture coverage.
- Requirement matrix updated.
- No new outward dependency from domain modules.
- Security-sensitive changes receive independent review.
- Replay determinism remains intact.
- Public schema changes include version and migration notes.

### Specification and test updates

Coding agents must update the relevant schema, ADR, requirement mapping, and tests in the same change as implementation. Undocumented behavior is considered incomplete.

### Conflict prevention

The lead agent assigns module ownership and reserves shared schema files. Subagents work on feature branches with explicit interface assumptions. Changes to shared contracts require an ADR and lead approval before dependent work continues.

### Concise execution protocol

1. Read assigned requirements, contracts, ADRs, and fixtures.
2. Restate inputs, outputs, invariants, and prohibited dependencies in the work log.
3. Add or update failing tests first.
4. Implement the smallest complete vertical behavior.
5. Run unit, contract, integration, and relevant security tests.
6. Dogfood the capability with a scenario or replay where applicable.
7. Update documentation, requirement mapping, and migration notes.
8. Submit evidence: test output, sample artifact, and known limitations.
9. Do not modify shared contracts without an approved ADR.

## 30. Definition of Done

- [ ] Core simulated debugging workflow functions from task start through score and report.
- [ ] Authoritative state is independent of the language-model renderer.
- [ ] Released scenarios pass validation and fixture tests.
- [ ] Canonical adapter conformance tests pass.
- [ ] Replay reproduces final state hashes.
- [ ] Completion, safety, efficiency, and behavioral score findings include evidence.
- [ ] Qwen-AgentWorld contradictions are detected or safely handled.
- [ ] Installation and `doctor` work on supported operating systems.
- [ ] CLI and API workflows are documented.
- [ ] CI can run a suite and enforce regression thresholds.
- [ ] Security requirements, redaction, action policies, and dependency scanning pass.
- [ ] Failure modes for providers, dependencies, cancellation, and corrupted inputs are tested.
- [ ] Generated artifacts are immutable, traceable, and exportable.
- [ ] At least one capability is dogfooded against Agent Debugger's own fixtures in each implementation phase.
- [ ] Optional real validation is isolated, evidence-producing, and distinctly labeled.
- [ ] No promised product surface remains a placeholder unless explicitly labeled future work.

## 31. Success Metrics

### Launch metrics

- Median first successful deterministic run within 15 minutes of installation.
- At least 90% of pilot users complete setup without developer intervention.
- At least 10 validated scenarios across 5 fictional repositories.
- At least 2 agent configurations compared end to end.
- 100% of score findings in released scenarios have evidence references.
- Replay success above 99.99% on fixture runs.
- Zero host-command execution from simulated actions.
- Less than 2% unclassified platform failures in pilot suites.

### Long-term metrics

**Adoption:** Active workspaces, weekly suite runs, integrated CI repositories, and authored scenarios.  
**Time saved:** Reduction in human review time and avoided real-container runs. Target assumption: 50% reduction in early evaluation cost after calibration.  
**Reliability:** Run completion rate excluding external provider outages; replay divergence; artifact integrity failures.  
**Coverage:** Percentage of agent capabilities, failure classes, and action classes represented by suites.  
**Accuracy:** Human agreement with score findings; simulation-real outcome agreement by scenario class.  
**User trust:** Percentage of reviewers rating score explanations as sufficient and reproducible.  
**Setup time:** Median time from install to first model-rendered run.  
**Failure rate:** Provider, scenario, adapter, platform, and unknown failure rates tracked separately.  
**Output usefulness:** Percentage of failed runs that lead to an identified prompt, tool, model, or policy improvement.  
**Maintenance cost:** Scenario authoring hours per validated task and breakage rate per product release.

## 32. Open Questions

### 32.1 How much hidden reasoning should be requested or retained from evaluated agents?

**Why it matters:** Some agents expose only actions and summaries; requesting private chain-of-thought is unreliable, provider-dependent, and may be inappropriate.  
**Recommended assumption:** Score observable actions, stated hypotheses intended for the tool loop, and outcomes; do not require private chain-of-thought.  
**Resolver:** Product and research leads with provider policy review.  
**Deadline:** Before scoring profile v1 freezes in Phase 2.

### 32.2 What minimum real-trace calibration rate is required before labeling a scenario class trustworthy?

**Why it matters:** Simulation fidelity varies by task and command type.  
**Recommended assumption:** Require at least 20 representative real traces per scenario class and report confidence rather than a universal trust label.  
**Resolver:** Evaluation research lead using Phase 4 calibration data.  
**Deadline:** Phase 4 exit.

### 32.3 Which agent adapters should be first-party at launch?

**Why it matters:** Adapter breadth affects adoption but can distract from core validity.  
**Recommended assumption:** One simple OpenAI-compatible tool-loop reference adapter and one framework adapter selected from pilot demand.  
**Resolver:** Product lead based on design-partner usage.  
**Deadline:** Mid-Phase 1.

### 32.4 Should qualitative judge scores contribute to the default overall score?

**Why it matters:** They add nuance but may reduce reproducibility and create model dependence.  
**Recommended assumption:** Display them separately during beta; include in overall score only after human-agreement thresholds are met.  
**Resolver:** Research lead and product governance.  
**Deadline:** End of Phase 2.

### 32.5 What artifact retention policy is acceptable for proprietary code in shared deployments?

**Why it matters:** Transcripts and patches may contain sensitive source.  
**Recommended assumption:** Local-first indefinite retention controlled by the user; shared deployments default to 30-day raw payload retention and longer normalized metadata retention.  
**Resolver:** Security, legal, and pilot customers.  
**Deadline:** Before Phase 5 team beta.

## 33. Future Opportunities

### Near-term

- Additional coding-agent adapters.
- Scenario authoring UI and interactive state debugger.
- Human annotation and adjudication.
- Rich failure-pattern clustering.
- Shareable signed benchmark bundles.
- Additional world-model providers.

### Medium-term

- Assisted scenario generation from real incidents and sanitized repositories.
- Mutation-based scenario variants and adversarial simulator probing.
- Team workspaces, leaderboards, and policy gates.
- GitHub repository import into isolated fixture pipelines.
- Reinforcement-learning trajectory export with provenance.
- IDE extension for opening run evidence beside source.

### Long-term

- Industry-standard certification suites for coding-agent safety and reliability.
- Continually calibrated simulation models specialized by language and toolchain.
- Cross-organization private benchmark exchange using signed, encrypted packages.
- Hybrid evaluations that dynamically choose simulation or real execution per action.
- Formal behavioral policy verification for high-risk autonomous agents.

## 34. Recommended Next Actions

1. **Confirm the foundational decisions:** deterministic state beneath Qwen-AgentWorld; local-first hybrid deployment; simulation and real validation as separate claims; observable-action scoring rather than private chain-of-thought.
2. **Create initial specifications:** canonical action protocol v0.1, scenario manifest v0.1, event envelope v0.1, error taxonomy, and the login-environment-variable scenario state model.
3. **Build the first vertical slice:** one CLI command, one reference agent adapter, deterministic file/search/patch/test actions, append-only events, pass/fail scoring, and replay.
4. **Run the first dogfooding milestone:** compare two prompts for the same reference agent on the login scenario, then review whether the transcript exposes the expected investigation and verification differences.
5. **Proceed to Qwen-AgentWorld integration only when:** authoritative replay is deterministic, scenario fixtures pass, action limits and safety policy work, and the first comparison produces evidence-backed behavioral findings.

---

**Research basis for dependency assumptions:** Qwen-AgentWorld was publicly released in June 2026 as an Apache-2.0 language world model covering MCP, Search, Terminal, SWE, Android, Web, and OS. The open 35B-A3B model is documented as 35B total/3B active with a 262,144-token context and OpenAI-compatible serving through vLLM or SGLang. AgentWorldBench includes Terminal and SWE trajectories and evaluates generated observations for format, factuality, consistency, realism, and quality. These facts support its use as an observation renderer, while the architecture intentionally avoids treating it as the source of benchmark truth.
