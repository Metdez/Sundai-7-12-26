<!-- Source: agent_debugger_prd.md (lines 1162-1217). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 19. Integration Architecture

### 19.1 Qwen-AgentWorld

**Purpose:** Render realistic Terminal and SWE observations from actions and state context.  
**Data flow:** Agent Debugger sends system prompt, bounded history, action, protected state facts, and rendering constraints; provider returns an observation.  
**Authentication:** Optional bearer/API key depending on deployment; none for trusted local endpoints.  
**Permissions:** No direct filesystem or database access; text request/response only.  
**Failure behavior:** Retry bounded transient failures; validate output; use deterministic fallback when allowed.  
**Limits:** Provider token, context, concurrency, and GPU memory limits.  
**Versioning:** Pin model identifier, endpoint implementation, prompt template digest, and decoding settings.  
**Required:** Optional for deterministic mode, required for model-rendered runs.

### 19.2 Coding Agent or Model Provider

**Purpose:** Supply the system under evaluation.  
**Data flow:** Task and observations outbound; canonical actions inbound through adapter.  
**Authentication:** Provider-specific secret reference.  
**Permissions:** Only the tool schema exposed by the run.  
**Failure behavior:** Timeouts and malformed actions are recorded as agent/provider events according to classification.  
**Limits:** Token, cost, rate, concurrency, and tool-call limits.  
**Versioning:** Agent revision captures model and adapter identity.  
**Required:** Yes.

### 19.3 Container Runtime

**Purpose:** Execute promoted patches in an isolated real environment.  
**Data flow:** Scenario fixture and patch into ephemeral container; logs, exit codes, and diff out.  
**Authentication:** Local daemon permission or remote runner credential.  
**Permissions:** Minimal runtime socket access; validator service should mediate direct daemon usage in shared deployments.  
**Failure behavior:** Mark infrastructure failure; do not convert to agent failure.  
**Limits:** CPU, memory, disk, process count, wall time, and network.  
**Versioning:** Image digests and validator protocol.  
**Required:** Optional.

### 19.4 GitHub Actions

**Purpose:** Automated regression execution and result publication.  
**Data flow:** Repository configuration to CLI; summary and artifacts back to workflow.  
**Authentication:** GitHub token only when annotations or artifact APIs require it.  
**Permissions:** Read repository by default; write checks only when configured.  
**Failure behavior:** Distinct exit codes and always-upload report step.  
**Limits:** Runner time, storage, and hosted network policy.  
**Versioning:** Pin action by immutable release or commit.  
**Required:** Optional.

### 19.5 Object Storage and PostgreSQL

**Purpose:** Shared team deployment and large artifact retention.  
**Data flow:** Metadata to PostgreSQL; immutable artifacts to object storage.  
**Authentication:** Service identity or scoped credentials.  
**Permissions:** Prefix/bucket and schema scoped.  
**Failure behavior:** Run enters artifact-pending or infrastructure-failed state; local spool may retry.  
**Limits:** Storage quotas and request rates.  
**Versioning:** Database migrations and artifact manifest schema.  
**Required:** Optional after MVP.
