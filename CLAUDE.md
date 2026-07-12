# Agent Debugger — Codebase Router

This file is the entry point for any AI agent working in this repo. It routes you to the right code and the right doc instead of forcing you to read everything. Identify what you're trying to do, open only what's listed for it.

**What this is:** a benchmark platform that runs AI coding agents against fictional repositories with planted bugs, scores their debugging behavior deterministically across 7 dimensions, and renders the results in a web dashboard. A deterministic state engine owns all truth; LLMs only ever produce observation text, never verdicts.

## Repo map

| Path | What it is |
|---|---|
| [src/agent_debugger/](src/agent_debugger/) | The Python package (engine, scoring, API, CLI) — see module router below |
| [web/](web/) | Framework-free TypeScript dashboard (esbuild → committed [web/dist/](web/dist/)) |
| [scenarios/](scenarios/) | The 5 scenario packages (manifest + fixture repo + reference trajectories) |
| [scenarios/_guides/](scenarios/_guides/) | Human-facing guide YAML per scenario, rendered by the dashboard — deliberately OUTSIDE package roots (digest safety, see invariants) |
| [configs/agents/](configs/agents/) | Registered agent configs: 3 OpenRouter models, careful/hasty reference agents, scripted known-good |
| [tests/](tests/) | pytest suite (~180 tests): unit / contract / integration / e2e / security |
| [docs/](docs/) | PRD split into per-section files + post-PRD implementation knowledge (index below) |
| [agent_debugger_prd.md](agent_debugger_prd.md) | The complete original PRD — frozen source of truth |
| [containers/](containers/) | Dockerfiles: `server` (dashboard), `validator` (real-validation sandbox) |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | CI: pytest matrix, web build, scenario validation loop, regression-gate demo |
| [action.yml](action.yml) | GitHub Action wrapper (run benchmark in CI) |
| `demo-workspace/` (gitignored) | Live workspace the local server points at; runs live in `.agent-debugger/runs/<run_id>/` |
| `.env` (gitignored, NEVER commit) | `OPENROUTER_API_KEY` for live-model runs |

## Source module router (`src/agent_debugger/`)

Dependency direction: `domain` and `protocol` are the bottom; `application/services.py` is the shared core; `cli` and `api` are thin surfaces that call services only.

| Module | Owns | Touch it when… |
|---|---|---|
| [domain/model.py](src/agent_debugger/domain/model.py) | Core dataclasses (RunManifest, AgentRevision, RunLimits), hashing helpers (`sha256_hex`, `digest_of`), schema versions | Adding fields to manifests/revisions |
| [domain/errors.py](src/agent_debugger/domain/errors.py) | Error taxonomy (`ScenarioError`, `ConfigurationError`, … with categories → exit codes/HTTP) | New error kinds |
| [protocol/actions.py](src/agent_debugger/protocol/actions.py) | Canonical action protocol v0.1.0 (16 action types), normalization, `tool_contract()` (regenerates [docs/protocols/](docs/protocols/action-protocol-0.1.0.json)) | Adding/changing agent actions |
| [protocol/events.py](src/agent_debugger/protocol/events.py) | Event type definitions for the run log | New event kinds |
| [scenario/package.py](src/agent_debugger/scenario/package.py) | Manifest schema (`ScenarioManifest`), `load_package`, `compute_package_digest` (hashes EVERY file under a package root), `validate_package`, scaffolding | Scenario schema changes — read the digest invariant first |
| [scenario/engine.py](src/agent_debugger/scenario/engine.py) | `StateEngine` — applies actions to authoritative state, perturbation schedule, state hashing | Action semantics, perturbations |
| [scenario/state.py](src/agent_debugger/scenario/state.py) / [scenario/vfs.py](src/agent_debugger/scenario/vfs.py) | `AuthoritativeState` (files/env/logs/suites/flags) and the virtual filesystem | State shape, file ops |
| [scenario/conditions.py](src/agent_debugger/scenario/conditions.py) | Predicate DSL (`file_regex`, `env_var_set`, `any_of`, …) used by `pass_when`/success predicates | New predicate kinds |
| [scenario/guide.py](src/agent_debugger/scenario/guide.py) | `ScenarioGuide` model + best-effort loader for `scenarios/_guides/<id>.yaml` (never raises) | Guide schema changes |
| [policy/engine.py](src/agent_debugger/policy/engine.py) | Action classes (read_only/safe_write/destructive/external/privileged), allow/block decisions, `PolicyTracker.metrics()` (actions/tokens/cost/elapsed) | Safety gating, metrics keys |
| [adapters/](src/agent_debugger/adapters/) | Agent adapters: [openai_compat.py](src/agent_debugger/adapters/openai_compat.py) (live models via tool loop — handles parallel tool_calls; falls back `tool_choice` required→auto for providers that reject it), [reference.py](src/agent_debugger/adapters/reference.py) (heuristic careful/hasty), [scripted.py](src/agent_debugger/adapters/scripted.py) (trajectory playback), [registry.py](src/agent_debugger/adapters/registry.py) | New model providers or adapter behavior |
| [renderers/](src/agent_debugger/renderers/) | Observation rendering: [deterministic.py](src/agent_debugger/renderers/deterministic.py) (default), [qwen.py](src/agent_debugger/renderers/qwen.py) + [hybrid.py](src/agent_debugger/renderers/hybrid.py) (LLM-rendered text with fallback) | Observation formatting; NEVER let a renderer decide success |
| [orchestration/runner.py](src/agent_debugger/orchestration/runner.py) | `RunOrchestrator` — the run loop: adapter ↔ policy ↔ engine ↔ renderer, event emission, terminal predicates, scoring hand-off | Run lifecycle |
| [orchestration/replay.py](src/agent_debugger/orchestration/replay.py) | Deterministic replay + hash-chain verification (FR-027) | Replay divergence handling |
| [orchestration/suite.py](src/agent_debugger/orchestration/suite.py) | Multi-run suite execution | Batch runs |
| [scoring/engine.py](src/agent_debugger/scoring/engine.py) | `score_run()` — all point values as module constants, `DIMENSION_WEIGHTS` (35/10/10/15/5/10/15), `scoring_rubric()` (serves the dashboard rubric page from the SAME constants) | Any scoring change — keep rubric generated, not hand-written |
| [scoring/facts.py](src/agent_debugger/scoring/facts.py) | Extracts behavioral facts from the event log (investigated? hypothesized? verified?) | What counts as investigation/verification |
| [scoring/judge.py](src/agent_debugger/scoring/judge.py) | Optional LLM judge annotations (advisory only, never the score) | Judge integration |
| [persistence/workspace.py](src/agent_debugger/persistence/workspace.py) | Workspace layout (`.agent-debugger/` state dir, `run_dir()`), config; `Workspace.close()` matters on Windows | Workspace/state layout |
| [persistence/db.py](src/agent_debugger/persistence/db.py) | SQLite metadata index (runs/agents/scenarios), thread-local connections, `_row_to_run` (the API row shape incl. `agent_name`/`agent_model`) | Query/index changes — events stay authoritative in JSONL, not here |
| [persistence/events.py](src/agent_debugger/persistence/events.py) | Hash-chained append-only `events.jsonl` writer/reader (NFR-014), `utc_now` | Event log format |
| [persistence/artifacts.py](src/agent_debugger/persistence/artifacts.py) | Content-addressed artifact store | Artifact storage |
| [application/services.py](src/agent_debugger/application/services.py) | Shared core: `resolve_package` (hard-fails on digest mismatch), `register_scenario/agent`, `scenario_detail`/`enrich_scenario_rows` (dashboard payloads), `openrouter_agent_config`/`register_benchmark_agents` (UI benchmark agents), `execute_run`, renderer wiring | Any behavior shared by CLI + API — put logic HERE, not in route handlers |
| [application/openrouter.py](src/agent_debugger/application/openrouter.py) | `OpenRouterGateway`: session API key (memory-only, `os.environ`, masked in responses) + cached model-catalog proxy | Provider key/catalog handling — the key must never reach configs, events, or responses |
| [api/app.py](src/agent_debugger/api/app.py) | FastAPI routes (all `/api/v1/*` incl. providers/benchmark), semaphore-gated `_spawn_run` (enforces `max_concurrent_runs`), benchmark batch registry, SSE stream, static dashboard mount. Handlers contain NO logic — services calls only | New endpoints (thin!) |
| [cli/main.py](src/agent_debugger/cli/main.py) | `agent-debugger` CLI: init/scenario/agent/run/replay/compare/promote/serve, PRD §22 exit codes (0/10/11/20/21/30/31/40) | New commands |
| [reports/](src/agent_debugger/reports/) | Run reports (JSON/MD/HTML), [compare.py](src/agent_debugger/reports/compare.py) (baseline-vs-candidate + regression gate exit 10) | Report content |
| [validation/real.py](src/agent_debugger/validation/real.py) | Container-based real validation (`promote`); daemon-down → DependencyError exit 30, never a verdict | Real-validation flow |
| [sdk/conformance.py](src/agent_debugger/sdk/conformance.py) | Adapter conformance harness (7 checks) | Adapter certification |
| [util/secrets.py](src/agent_debugger/util/secrets.py) | Secret redaction (regex requires an opaque literal — must not mangle code like `os.environ.get("JWT_SECRET")`) | Redaction rules (security tests guard this) |

## Web dashboard (`web/`)

- Single-file client: [web/src/app.ts](web/src/app.ts) — hash router (`#/` overview, `#/models` (key + picker + benchmark launcher + comparison), `#/scenarios`, `#/scenario/<id>`, `#/runs?scenario=&model=&outcome=`, `#/run/<id>`, `#/compare/<a>/<b>`, `#/rubric`), strict TS, no framework.
- Conventions that must survive edits: every view re-checks `parseHash()` after its fetches (stale-fetch race guard); the 5s poll only repaints overview/runs and pauses while a `<select>`/`<input>` is focused; leaderboard/matrix group by `agentLabel()` (display label), NOT model id.
- Shell/styles: [web/static/index.html](web/static/index.html), [web/static/styles.css](web/static/styles.css). Build: `cd web && npx tsc --noEmit && npm run build`. **`web/dist/` is committed** — rebuild and include it in the same commit.

## Common tasks → where to go

- **Add a scenario** → scaffold with `agent-debugger scenario new`, follow an existing package (e.g. [scenarios/login-env-var/](scenarios/login-env-var/)); add a matching guide in [scenarios/_guides/](scenarios/_guides/) (a unit test enforces one per package); validate with `scenario test`. Schema/docs: [docs/15-data-artifact-model.md](docs/15-data-artifact-model.md), [docs/11-workflows-pipelines.md](docs/11-workflows-pipelines.md) §11.1.
- **Add a model/agent** → new YAML in [configs/agents/](configs/agents/) (`api_key_ref: env:NAME`, never literals), `agent add`, then run. Never guess OpenRouter slugs — query the live `/models` endpoint.
- **Change scoring** → [scoring/engine.py](src/agent_debugger/scoring/engine.py) constants + [scoring/facts.py](src/agent_debugger/scoring/facts.py); the rubric page updates itself. Update [tests/unit/test_scoring.py](tests/unit/test_scoring.py).
- **Add an API endpoint** → logic in [application/services.py](src/agent_debugger/application/services.py), thin route in [api/app.py](src/agent_debugger/api/app.py), test in [tests/e2e/test_api.py](tests/e2e/test_api.py).
- **Change the dashboard** → [web/src/app.ts](web/src/app.ts) + styles; rebuild dist; verify in a browser (navigate via `about:blank` first — same-URL navigation keeps the old bundle).
- **Touch security-sensitive code** (policy, shell allowlist, secrets, containers) → read [docs/20-security-architecture.md](docs/20-security-architecture.md) first, always; tests in [tests/security/](tests/security/).
- **Scope question** ("is X in scope?") → [docs/04-goals.md](docs/04-goals.md) / [docs/05-non-goals.md](docs/05-non-goals.md); architecture choice → check [docs/26-architectural-decisions.md](docs/26-architectural-decisions.md) first, it may already be decided.

## Commands

```bash
# from repo root; venv interpreter is .venv/Scripts/python.exe (Windows)
.venv/Scripts/python.exe -m pytest -q            # full suite, must be green
cd web && npx tsc --noEmit && npm run build      # dashboard typecheck + bundle
cd demo-workspace && ../.venv/Scripts/python.exe -m agent_debugger.cli.main serve --port 8321
# live-model runs need: set -a && source .env && set +a   (OPENROUTER_API_KEY)
```

## Invariants — do not break these

1. **Package digest safety.** `compute_package_digest` hashes every file under a scenario root. Never add/edit files inside `scenarios/<package>/` unless you intend to invalidate registrations and replay of existing runs; docs/content go in `scenarios/_guides/` or `docs/`. CI's scenario loop skips dirs without `manifest.yaml`.
2. **Deterministic truth.** Renderers and judges never decide success; predicates over authoritative state do. "Verification is part of solved": an unverified correct fix terminates `submitted_unsolved`.
3. **Events are authoritative in JSONL** (hash-chained); SQLite is only an index. Replay must reproduce state hashes exactly.
4. **Thin surfaces.** CLI and API handlers call services; no evaluation logic in routes/commands.
5. **Secrets are references** (`env:NAME`), never literals in configs; redaction must not mangle source code (dogfooding regression).
6. **Generated explanations.** The rubric page and action-protocol JSON are generated from code constants — regenerate, don't hand-edit.
7. **Nested git repo.** This repo lives inside a HOME directory that is itself a git repo — always run git from the repo root, never from parent dirs.

---

## PRD documentation index

**Source of truth:** [agent_debugger_prd.md](agent_debugger_prd.md) is the complete, original PRD — unmodified. Everything in `docs/01…34` is that document split into topic files (verbatim excerpts, one PRD section per file). If a doc file and the PRD ever disagree, the PRD wins — re-split rather than hand-editing a doc file.

| Doc | PRD § | Use when you need to know... |
|---|---|---|
| [01-executive-summary.md](docs/01-executive-summary.md) | 1 | What Agent Debugger is, in one paragraph |
| [02-background-motivation.md](docs/02-background-motivation.md) | 2 | Why this exists, prior approaches, pain points |
| [03-product-vision.md](docs/03-product-vision.md) | 3 | Long-term product direction |
| [04-goals.md](docs/04-goals.md) | 4 | What success looks like |
| [05-non-goals.md](docs/05-non-goals.md) | 5 | What is explicitly out of scope |
| [06-personas.md](docs/06-personas.md) | 6 | Who the users are and what they need |
| [07-jobs-to-be-done.md](docs/07-jobs-to-be-done.md) | 7 | The concrete jobs users hire this product for |
| [08-core-principles.md](docs/08-core-principles.md) | 8 | The non-negotiable design principles |
| [09-system-overview.md](docs/09-system-overview.md) | 9 | High-level architecture, inputs/outputs, ASCII diagram |
| [10-product-surfaces.md](docs/10-product-surfaces.md) | 10 | CLI, API, web UI, adapter SDK, CI integration boundaries |
| [11-workflows-pipelines.md](docs/11-workflows-pipelines.md) | 11 | Step-by-step core workflows (scenario auth, run, score, replay, promote, drift) |
| [12-user-experience.md](docs/12-user-experience.md) | 12 | Setup flow, daily usage, upgrade flow |
| [13-functional-requirements.md](docs/13-functional-requirements.md) | 13 | FR-001…FR-032, the numbered requirements |
| [14-non-functional-requirements.md](docs/14-non-functional-requirements.md) | 14 | NFR-001…NFR-015, reliability/perf/security targets |
| [15-data-artifact-model.md](docs/15-data-artifact-model.md) | 15 | Core entities: ScenarioPackage, RunManifest, RunEvent, etc. + example manifest |
| [16-configuration-model.md](docs/16-configuration-model.md) | 16 | Config precedence, secrets, example YAML |
| [17-runtime-dependency-strategy.md](docs/17-runtime-dependency-strategy.md) | 17 | Language/runtime choices, containers, managed services |
| [18-distribution-installation.md](docs/18-distribution-installation.md) | 18 | Install channels, upgrade/uninstall, air-gapped use |
| [19-integration-architecture.md](docs/19-integration-architecture.md) | 19 | External integrations (Qwen-AgentWorld, containers, GitHub Actions, storage) |
| [20-security-architecture.md](docs/20-security-architecture.md) | 20 | Trust boundaries, threat model, action classes table |
| [21-testing-validation.md](docs/21-testing-validation.md) | 21 | Test strategy across unit/integration/e2e/security/dogfooding |
| [22-observability-reporting.md](docs/22-observability-reporting.md) | 22 | Logs, metrics, exit codes, error categories |
| [23-state-memory-traceability.md](docs/23-state-memory-traceability.md) | 23 | Persisted state, requirement traceability, drift/recovery |
| [24-extensibility-model.md](docs/24-extensibility-model.md) | 24 | Extension points and plugin-system restraint |
| [25-technical-architecture.md](docs/25-technical-architecture.md) | 25 | Module layout, dependency direction, provider interfaces, repo tree |
| [26-architectural-decisions.md](docs/26-architectural-decisions.md) | 26 | ADR-style decisions with alternatives considered and reconsideration triggers |
| [27-risks-mitigations.md](docs/27-risks-mitigations.md) | 27 | Risk register with mitigations and contingencies |
| [28-phased-implementation-plan.md](docs/28-phased-implementation-plan.md) | 28 | Phase 1–5 scope, deliverables, exit criteria |
| [29-agent-oriented-build-plan.md](docs/29-agent-oriented-build-plan.md) | 29 | How lead/subagents should split and sequence implementation work |
| [30-definition-of-done.md](docs/30-definition-of-done.md) | 30 | The checklist for "done" |
| [31-success-metrics.md](docs/31-success-metrics.md) | 31 | Launch and long-term success metrics |
| [32-open-questions.md](docs/32-open-questions.md) | 32 | Unresolved decisions, owners, deadlines |
| [33-future-opportunities.md](docs/33-future-opportunities.md) | 33 | Near/medium/long-term ideas outside current scope |
| [34-next-actions.md](docs/34-next-actions.md) | 34 | Immediate next steps + Qwen-AgentWorld research basis |

### Quick PRD routing by task type

- **"I'm implementing Phase N"** → [28-phased-implementation-plan.md](docs/28-phased-implementation-plan.md) for scope/exit criteria, then [29-agent-oriented-build-plan.md](docs/29-agent-oriented-build-plan.md), then the specific FR/NFR docs (13, 14).
- **"I'm writing a scenario package"** → [15-data-artifact-model.md](docs/15-data-artifact-model.md) and [11-workflows-pipelines.md](docs/11-workflows-pipelines.md) §11.1.
- **"I'm building an agent adapter"** → [10-product-surfaces.md](docs/10-product-surfaces.md) §10.4, [11-workflows-pipelines.md](docs/11-workflows-pipelines.md) §11.2, [25-technical-architecture.md](docs/25-technical-architecture.md).
- **"I need the full picture"** → read [agent_debugger_prd.md](agent_debugger_prd.md) directly.

## Rules for this environment

- The PRD content itself is frozen: do not add to or remove from what the document says. If requirements change, that's a PRD edit followed by a re-split, not a docs/ edit.
- Doc files `docs/01…34` are verbatim slices, not summaries or rewrites — safe to trust their wording as identical to the PRD.
- When you learn something during implementation that isn't in the PRD (a decision, a gotcha, a convention), add it to the implementation-knowledge files below and link it here rather than editing a PRD slice.

## Implementation knowledge (post-PRD, added during the build)

- [implementation-notes.md](docs/implementation-notes.md) — decisions the PRD left open (verification-is-part-of-solved, JSONL-authoritative events, approval auto-deny, reference-agent design, dashboard IA, guides-outside-digest), gotchas (SQLite threading, fullmatch allowlists, pass_when literalism), and the content backlog.
- [requirements-matrix.yaml](docs/requirements-matrix.yaml) — machine-readable FR/NFR → module → test → phase traceability (PRD §23).
- [protocols/action-protocol-0.1.0.json](docs/protocols/action-protocol-0.1.0.json) — generated canonical action JSON schemas (regenerate from `agent_debugger.protocol.actions.tool_contract()` after protocol changes).
