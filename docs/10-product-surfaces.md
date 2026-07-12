<!-- Source: agent_debugger_prd.md (lines 237-293). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

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
