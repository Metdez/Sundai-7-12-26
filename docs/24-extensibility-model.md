<!-- Source: agent_debugger_prd.md (lines 1421-1443). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 24. Extensibility Model

### Initial extension points

- Agent adapters.
- Observation renderers.
- Scenario action handlers from an allowlisted registry.
- Scoring rules and profiles.
- Report formatters.
- Storage backends.
- Real-validation runners.

### Stable public interfaces

Canonical action/observation protocol, scenario manifest schema, adapter SDK, run report schema, and REST API major versions.

### Internal interfaces

Database repositories, orchestration implementation, UI state management, and internal event dispatch are not public extension contracts.

### Plugin-system restraint

The MVP will use Python entry points for a small number of provider and adapter interfaces, not a general plugin marketplace. A broader sandboxed plugin model should be considered only after at least three independently maintained integrations demonstrate stable common needs.
