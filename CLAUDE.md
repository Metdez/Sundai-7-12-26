# Agent Debugger — Context Router

This file is the entry point for any AI agent working in this repo. It routes you to the right doc instead of forcing you to read the full PRD.

**Source of truth:** [agent_debugger_prd.md](agent_debugger_prd.md) is the complete, original PRD — unmodified, kept in place. Everything in `docs/` is that same document split into topic files (verbatim excerpts, one PRD section per file) so an agent can pull only the section it needs instead of loading all ~1,900 lines. If a doc file and the PRD ever disagree, the PRD wins — re-split rather than hand-editing a doc file.

## How to use this router

1. Identify what you're trying to do (design, implement, review, plan) from the table below.
2. Open only the doc(s) listed — don't read the whole PRD unless you need cross-section context.
3. Each doc file has a header comment pointing back to its exact line range in the PRD.

## Doc index

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

## Quick routing by task type

- **"I'm implementing Phase N"** → [28-phased-implementation-plan.md](docs/28-phased-implementation-plan.md) for scope/exit criteria, then [29-agent-oriented-build-plan.md](docs/29-agent-oriented-build-plan.md) for how to sequence the work, then the specific FR/NFR docs (13, 14) for the requirements that phase touches.
- **"I'm writing a scenario package"** → [15-data-artifact-model.md](docs/15-data-artifact-model.md) (schema + example manifest) and [11-workflows-pipelines.md](docs/11-workflows-pipelines.md) §11.1.
- **"I'm building an agent adapter"** → [10-product-surfaces.md](docs/10-product-surfaces.md) §10.4, [11-workflows-pipelines.md](docs/11-workflows-pipelines.md) §11.2, [25-technical-architecture.md](docs/25-technical-architecture.md) (Provider abstraction).
- **"I'm touching security-sensitive code"** → [20-security-architecture.md](docs/20-security-architecture.md) first, always.
- **"I need to know if something is in scope"** → [04-goals.md](docs/04-goals.md) and [05-non-goals.md](docs/05-non-goals.md).
- **"I'm deciding between two architectural approaches"** → check [26-architectural-decisions.md](docs/26-architectural-decisions.md) first — it may already be decided, with a documented reconsideration trigger.
- **"I need the full picture"** → read [agent_debugger_prd.md](agent_debugger_prd.md) directly.

## Rules for this environment

- The PRD content itself is frozen: do not add to or remove from what the document says. If requirements change, that's a PRD edit followed by a re-split, not a docs/ edit.
- Doc files under `docs/` are verbatim slices, not summaries or rewrites — safe to trust their wording as identical to the PRD.
- When you learn something during implementation that isn't in the PRD (a decision, a gotcha, a convention), that's new project knowledge — add it as its own file rather than editing a PRD slice, and link it from this router.
