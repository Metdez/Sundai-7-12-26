<!-- Source: agent_debugger_prd.md (lines 598-647). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

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
