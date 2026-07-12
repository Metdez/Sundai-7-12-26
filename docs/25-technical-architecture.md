<!-- Source: agent_debugger_prd.md (lines 1445-1539). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

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
