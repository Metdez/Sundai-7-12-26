<!-- Source: agent_debugger_prd.md (lines 1699-1776). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 29. Agent-Oriented Build Plan

### Lead-agent responsibilities

- Own domain terminology, architecture boundaries, protocol versions, and requirement traceability.
- Establish shared contracts before delegating implementation.
- Review cross-module error handling, security, and persistence semantics.
- Integrate vertical slices and maintain the authoritative architecture decision records.

### Safe subagent assignments

- Scenario schema and validator.
- Individual canonical action handlers after protocol freeze.
- Deterministic renderer and fixtures.
- Qwen provider client behind an established interface.
- Scoring rule implementations against fixed event schemas.
- Report formatters.
- Frontend views against generated API clients.
- Documentation and scenario examples.
- Independent security and test review.

### Parallelizable modules

After domain and protocol contracts are approved: adapters, renderers, scoring rules, report exporters, API read endpoints, frontend components, and scenario packages.

### Sequential modules

State engine before live orchestration; event schema before replay and scoring; report schema before dashboard comparison; patch provenance before real validation; permission model before shared deployment.

### Required context for every agent

- This PRD and current ADRs.
- Canonical protocol schemas.
- Error taxonomy.
- Security action classes.
- Requirement-to-test matrix.
- Module-specific interface contracts.
- Existing fixtures and coding standards.

### Shared contracts to establish first

1. Canonical action and observation schemas.
2. Run event envelope and hash rules.
3. Authoritative state transition interface.
4. Typed error model.
5. Scenario package schema.
6. Artifact and evidence reference format.
7. Version compatibility rules.

### Validation before merging

- Unit and contract tests pass.
- New behavior includes fixture coverage.
- Requirement matrix updated.
- No new outward dependency from domain modules.
- Security-sensitive changes receive independent review.
- Replay determinism remains intact.
- Public schema changes include version and migration notes.

### Specification and test updates

Coding agents must update the relevant schema, ADR, requirement mapping, and tests in the same change as implementation. Undocumented behavior is considered incomplete.

### Conflict prevention

The lead agent assigns module ownership and reserves shared schema files. Subagents work on feature branches with explicit interface assumptions. Changes to shared contracts require an ADR and lead approval before dependent work continues.

### Concise execution protocol

1. Read assigned requirements, contracts, ADRs, and fixtures.
2. Restate inputs, outputs, invariants, and prohibited dependencies in the work log.
3. Add or update failing tests first.
4. Implement the smallest complete vertical behavior.
5. Run unit, contract, integration, and relevant security tests.
6. Dogfood the capability with a scenario or replay where applicable.
7. Update documentation, requirement mapping, and migration notes.
8. Submit evidence: test output, sample artifact, and known limitations.
9. Do not modify shared contracts without an approved ADR.
