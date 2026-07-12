<!-- Source: agent_debugger_prd.md (lines 1633-1697). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

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
