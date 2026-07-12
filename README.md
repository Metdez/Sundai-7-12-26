# Agent Debugger

Benchmark authoring, execution, and analysis platform for evaluating how AI
coding agents **investigate, diagnose, repair, and verify** software failures.

The core idea is a **hybrid truth-and-simulation architecture**: a
deterministic scenario state engine owns hidden root causes, state
transitions, allowed actions, success conditions, and scoring facts. A
language world model (Qwen-AgentWorld or any OpenAI-compatible endpoint) may
render realistic observations — but it never decides whether the task is
solved. See [agent_debugger_prd.md](agent_debugger_prd.md) for the full PRD
and [CLAUDE.md](CLAUDE.md) for the documentation router.

## Quick start

```bash
pip install -e ".[dev]"

agent-debugger init ./agent-evals
cd ./agent-evals
agent-debugger doctor

# register a benchmark scenario and two agent configurations
agent-debugger scenario add ../scenarios/login-env-var
agent-debugger agent add ../configs/agents/careful-reference.yaml
agent-debugger agent add ../configs/agents/hasty-reference.yaml

# run, inspect, replay
agent-debugger run webapp.login-env-var --agent careful-reference
agent-debugger run webapp.login-env-var --agent hasty-reference
agent-debugger compare --baseline <careful-rev> --candidate <hasty-rev> --gate

# review dashboard (timeline, scorecard, patch view, replay verification)
agent-debugger serve   # http://127.0.0.1:8321
```

Everything above runs fully offline with the deterministic renderer
(NFR-012). To enable model-rendered observations, point
`AGENTWORLD_BASE_URL` at any OpenAI-compatible endpoint serving
Qwen-AgentWorld and use `--renderer hybrid`; contradictions of protected
state facts are detected and fall back to deterministic rendering with full
disclosure in the run log (FR-012/FR-014).

## What exists

| Surface | Location | Notes |
|---|---|---|
| CLI | `src/agent_debugger/cli/` | init, doctor, scenario new/validate/test/add/list, agent add/list, run, suite, replay, report, compare, promote, serve — PRD §22 exit codes |
| REST API + SSE | `src/agent_debugger/api/` | runs, events, reports (json/md/html), replay, submit/cancel, compare, event stream |
| Web review app | `web/` | TypeScript, framework-free; run list, evidence-linked scorecard, filterable timeline, patch view, replay button |
| Scenario packages | `scenarios/` | 5 scenarios across 5 fictional repos, each with known-good/known-bad trajectories and deterministic fixtures |
| Adapter SDK | `src/agent_debugger/sdk/` | conformance suite (FR-007); adapters: scripted, reference-heuristic, openai-compat |
| Real validation | `src/agent_debugger/validation/` | ephemeral rootless container, `--network none`, argv-only commands, evidence bundle, calibration record |
| CI | `.github/workflows/ci.yml`, `action.yml` | test matrix + a dogfooding regression gate that must exit 10 |
| Traceability | `docs/requirements-matrix.yaml` | FR-001…FR-032 → modules → tests → phases |

## Architecture

Modules follow PRD §25 with strict dependency direction — `domain`,
`protocol`, and `scenario` import no web, database, or provider SDKs:

```
cli / api / web        (presentation)
  └─ application       (services shared by all surfaces)
       └─ orchestration → policy → scenario (truth engine) → domain
       └─ renderers (deterministic | qwen | hybrid+conformance)
       └─ adapters  (scripted | reference | openai-compat)
       └─ scoring   (deterministic facts → 7 dimensions, evidence-linked)
       └─ persistence (hash-chained JSONL events, SQLite metadata,
                       content-addressed artifacts)
       └─ reports / validation
```

Every run writes an append-only, hash-chained event log. `agent-debugger
replay <run-id>` reapplies authoritative transitions from the initial state
and verifies per-transition and final state hashes (FR-027; verified 10/10
consecutive runs in the integration suite).

## Development

```bash
pytest                      # 169 tests: unit, contract, integration, e2e, security
cd web && npx tsc --noEmit && npm run build
```

New scenarios: `agent-debugger scenario new <id> <dir>`, edit the manifest,
then `scenario validate` and `scenario test` (runs fixture trajectories and a
determinism check). See `docs/implementation-notes.md` for conventions the
PRD does not cover.
