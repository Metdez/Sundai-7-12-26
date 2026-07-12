<!-- Source: agent_debugger_prd.md (lines 150-235). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

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
