<!-- Source: agent_debugger_prd.md (lines 1541-1613). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 26. Architectural Alternatives and Decisions

### Decision: Separate authoritative state from language-model simulation

**Context:** A language world model can generate realistic outputs but may drift or hallucinate state.  
**Options considered:** LLM-only simulation; fully scripted mocks; real containers for every run; deterministic state plus model rendering.  
**Recommendation:** Deterministic state plus model rendering.  
**Rationale:** It combines reproducibility and scoring integrity with realistic interaction.  
**Consequences:** Scenario authoring requires explicit state semantics; renderer conformance logic is necessary.  
**Deferred reconsideration trigger:** A simulator demonstrates independently verified deterministic state fidelity high enough to replace handlers for a defined scenario class.

### Decision: Local-first hybrid deployment

**Context:** Users need Windows accessibility while Qwen-AgentWorld and real execution are more natural on Linux/GPU/container infrastructure.  
**Options considered:** Windows-native monolith; container-only stack; cloud-only SaaS; native core with remote/containerized providers.  
**Recommendation:** Native core and UI with provider endpoints and container-only real validation.  
**Rationale:** Lowest adoption friction without coupling the product to GPU or container availability.  
**Consequences:** `doctor` and endpoint configuration become important; distributed deployment comes later.  
**Deferred reconsideration trigger:** Hosted team demand exceeds local use or security teams require centralized control.

### Decision: Python core with TypeScript web client

**Context:** State, evaluation, model tooling, and scenario authoring are Python-heavy; review UI benefits from mature web tooling.  
**Options considered:** Python-only including UI; TypeScript full stack; Rust core; Python backend plus TypeScript frontend.  
**Recommendation:** Python backend/core and TypeScript React frontend.  
**Rationale:** Aligns with model ecosystem while maintaining a strong interactive UI.  
**Consequences:** Two language toolchains and contract tests are required.  
**Deferred reconsideration trigger:** Performance profiling shows Python orchestration is a material bottleneck.

### Decision: SQLite first, PostgreSQL optional

**Context:** MVP is local-first but future teams need shared concurrency.  
**Options considered:** Files only; SQLite; PostgreSQL only; event-streaming platform.  
**Recommendation:** Repository abstraction with SQLite default and PostgreSQL support before team beta.  
**Rationale:** SQLite minimizes setup; relational metadata and transactions fit the model.  
**Consequences:** Avoid database-specific features in core queries; migration testing across both engines.  
**Deferred reconsideration trigger:** Event volume or analytics needs exceed relational storage and object artifacts.

### Decision: Append-only event log plus snapshots

**Context:** Runs need replay and efficient review.  
**Options considered:** Mutable current-state rows; full snapshot every turn; event sourcing only; events plus periodic snapshots.  
**Recommendation:** Hash-chained events with periodic state snapshots.  
**Rationale:** Preserves auditability while controlling replay cost.  
**Consequences:** Event schema compatibility and snapshot migration discipline are required.  
**Deferred reconsideration trigger:** Operational complexity outweighs audit benefits in measured usage.

### Decision: Rule-first scoring with optional qualitative judge

**Context:** Reasoning quality can be qualitative, but LLM judges add cost and variance.  
**Options considered:** Rules only; judge only; human only; layered scoring.  
**Recommendation:** Deterministic facts and rules first, constrained judge for selected dimensions, optional human review.  
**Rationale:** Completion and safety remain objective while nuanced behavior is still assessable.  
**Consequences:** Reports must disclose judge dependence and confidence.  
**Deferred reconsideration trigger:** Reliable learned scorers outperform rules on validated human-labeled sets.

### Decision: Canonical action protocol instead of framework-specific execution

**Context:** Agents expose different tool schemas.  
**Options considered:** Native integration per framework; OpenAI tool calls as de facto protocol; canonical domain protocol with adapters.  
**Recommendation:** Versioned canonical protocol with thin adapters.  
**Rationale:** Enables fair comparison and stable scenario semantics.  
**Consequences:** Some framework-specific richness may be lost or represented as metadata.  
**Deferred reconsideration trigger:** A widely adopted open standard covers required coding-agent semantics.

### Decision: No arbitrary scenario code in the initial registry

**Context:** Custom handlers are powerful but create security and reproducibility risk.  
**Options considered:** Arbitrary Python; declarative state machines only; allowlisted handler library; sandboxed plugins.  
**Recommendation:** Declarative definitions plus allowlisted versioned handlers.  
**Rationale:** Safer and easier to validate for MVP.  
**Consequences:** Some complex scenarios require core handler additions.  
**Deferred reconsideration trigger:** Repeated author demand cannot be met declaratively and a secure sandbox is available.
