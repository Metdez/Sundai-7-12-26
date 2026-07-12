<!-- Source: agent_debugger_prd.md (lines 137-148). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

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
