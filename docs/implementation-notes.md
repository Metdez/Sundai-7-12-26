# Implementation Notes (new project knowledge — not a PRD slice)

Decisions, gotchas, and conventions discovered while building v0.1.0 that the
PRD does not specify. The PRD remains the source of truth for requirements;
this file records how the implementation resolved its open edges.

## Decisions

- **Verification is part of "solved."** Success predicates that reference a
  test suite require the suite's *authoritative status* to be `pass`, and the
  status only changes when the agent runs `test.run`. An agent that applies a
  correct fix but never re-runs tests terminates as `submitted_unsolved`.
  This is deliberate: it operationalizes "simulation is not proof" at the
  agent level and is what makes the careful-vs-hasty dogfooding comparison
  produce a completion delta, not just behavioral deltas.
- **Events are authoritative in JSONL, metadata in SQLite.** PRD §15.5 allows
  "database with export to JSONL"; local-first v0.1 inverts that: the
  hash-chained `events.jsonl` per run is the record of truth (human-readable,
  core principle 9), SQLite only indexes runs/agents/scenarios for queries.
- **Approval gates auto-deny in non-interactive runs.** `require_approval`
  emits `approval.requested` + `approval.resolved(approved=false, reason:
  non-interactive run)` and the attempt stays in the transcript and safety
  score. The `paused_for_approval` lifecycle state exists in the FSM for the
  future interactive path.
- **Unknown action types are envelope-valid.** A structurally valid action
  with an unknown type is not an adapter defect; it flows to the state engine
  and fails as agent behavior (`unknown_action`). Malformed envelopes and
  parameter-schema violations are `ProtocolError` (adapter defect).
- **Reference agent = configurable behavioral policy, not an LLM.** For
  offline determinism the dogfooding agent takes an investigation list, an
  optional hypothesis, a fix recipe, and a `verify_fix` flag from its config.
  Live-model evaluation uses the `openai-compat` adapter instead.
- **Blocked attempts mutate state flags.** `destructive/external/privileged`
  attempts set flags on authoritative state (so failure predicates and the
  state hash reflect them), and replay reapplies the same flags from recorded
  policy decisions.
- **Web client is TypeScript without a framework.** The PRD says "TypeScript
  React"; v0.1 ships strict-mode TypeScript compiled with esbuild but no
  React, keeping the dashboard a single 8 kB module. Revisit if the UI grows
  interactive state beyond list/detail.
- **Daemon failures never become validation verdicts.** `promote` raises a
  dependency error (exit 30) when the container runtime daemon is
  unreachable or the image is missing, instead of recording
  `real_success=false` — found by dogfooding promote on a machine where
  Docker Desktop was installed but not running.

## Gotchas

- `sqlite3` connections cannot cross threads; FastAPI sync endpoints run in a
  threadpool. `MetadataDB` opens one connection per thread. Close workspaces
  in tests (`Workspace.close()`) or Windows temp-dir cleanup fails.
- Shell allowlist patterns are matched with `re.fullmatch`, which is what
  makes `cat .env.example; rm -rf /` fail closed (see security tests).
- Scenario `pass_when` conditions must match what the *fixed file actually
  contains*, not the conceptual fix — e.g. code using
  `f"{CONFIG_ROOT}/development.yaml"` never contains the literal
  `config/development.yaml`.
- Perturbation schedules are precomputed per run from `seed` for turns
  0..499, so a perturbation draw never depends on how many rules matched
  earlier turns (replay-stable).

- **Dashboard is hash-routed with pages, not a single view.** `#/` (run
  grid with new-tab links + pick-2-to-compare), `#/run/<id>`, `#/compare/<a>/<b>`,
  `#/rubric`. Hash routing keeps `web/dist` fully static-servable with zero
  server-side route additions. Views re-check the hash after their fetches
  resolve so a stale in-flight render (e.g. the 5s home poll) can never paint
  over the current route.
- **The scoring rubric page is generated, not written.** `GET
  /api/v1/scoring/rubric` serializes the same module constants
  `score_run()` executes (weights, per-rule deltas, efficiency formula), so
  the UI's explanation of the math cannot drift from the scorer.
- **Dashboard IA is task-first: Overview / Scenarios / Runs / Rubric.** The
  default view answers "who's winning" (agent leaderboard + a scenario×agent
  matrix of latest scores) instead of listing raw runs; the run list moved to
  `#/runs` as a filterable table (`?scenario=&model=&outcome=` deep links).
  Leaderboard/matrix aggregation is client-side over the existing runs list;
  the grouping key is the display label (`name (model)`), NOT the model id —
  reference agents all share `model_identifier: "none"` and would wrongly
  merge under model-first grouping.
- **Scenario guides live in `scenarios/_guides/<scenario_id>.yaml`, outside
  package roots.** `compute_package_digest` hashes every file under a
  package root, so docs inside `scenarios/<dir>/` would invalidate
  registrations and replay. `GET /api/v1/scenarios/{id}` loads the manifest
  live via `load_package` (never `resolve_package`, which hard-fails on
  digest mismatch) and reports `digest_ok` as data for a UI warning banner;
  the guide is merged in best-effort (missing/malformed → `guide: null`,
  never a 500). The CI scenario-validation loop skips directories without a
  `manifest.yaml` so `_guides/` doesn't break `scenario test`.

- **Models hub: the OpenRouter key is a session secret, never persisted.**
  `POST /api/v1/providers/openrouter/key` verifies the key against OpenRouter
  and stores it ONLY in the server process's `os.environ` — adapters resolve
  `env:OPENROUTER_API_KEY` live per request, so it takes effect instantly and
  vanishes on restart. Responses carry a masked tail only; the security suite
  scans workspace files and API responses for the literal. Single-process
  assumption (serve runs one uvicorn worker). The API remains a no-auth local
  operator tool bound to 127.0.0.1 — do not expose it.
- **`execution.max_concurrent_runs` is now actually enforced** on the API
  path: all run spawning (POST /runs and POST /benchmark) goes through one
  semaphore-gated `_spawn_run` helper in `create_app`. Benchmark batches keep
  an in-memory registry so semaphore-queued runs (no DB row yet) surface as
  `"pending"` via `GET /api/v1/benchmark/{batch_id}`; the registry does not
  survive restarts (clients get 404 and fall back to `/runs?suite_id=`).
- **UI benchmark agents are generated configs.** One agent per model slug
  (`services.openrouter_agent_config`), same debugging prompt/limits as
  `configs/agents/openrouter-*.yaml`; registration is idempotent because
  `save_agent` is INSERT OR IGNORE on the config-hash revision_id.
- **Providers may reject `tool_choice: "required"`** — found by dogfooding
  the UI benchmark: Alibaba's qwen3.7-plus 400s with "does not support being
  set to required or object in thinking mode", which showed up as 5
  infrastructure-failed runs. The openai-compat adapter now retries once with
  `tool_choice: "auto"` (sticky per run) and surfaces a response-body excerpt
  in DependencyError details for all other HTTP failures.

## Backlog (content and features, not requirements changes)

- 5 more scenario tasks to reach the Phase 2 target of ten (current: five
  across five fictional repos).
- Failure-signature clustering (FR-024, "could") beyond newly-solved /
  newly-failed grouping.
- Interactive approval flow using the existing `paused_for_approval` state.
- SSE-driven live timeline in the dashboard (endpoint exists; UI polls).
