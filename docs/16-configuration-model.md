<!-- Source: agent_debugger_prd.md (lines 996-1050). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 16. Configuration Model

### Project-level configuration

Stored in `agent-debugger.yaml`; defines workspace paths, scenario sources, default providers, scoring profile, concurrency, retention, and CI thresholds.

### User-level configuration

Stored in the platform-standard user configuration directory; defines preferred output format, local endpoint aliases, UI settings, and non-secret defaults.

### Environment variables

Used for CI overrides, endpoint selection, secret references, and diagnostics. Environment variables override user defaults but not immutable run manifests after creation.

### Secrets

Resolved at execution from environment variables, OS credential stores, or pluggable secret providers. Secret values are passed only to the process that needs them and redacted from logs.

### Defaults and overrides

Precedence from lowest to highest: built-in defaults, user config, project config, named profile, environment variables, CLI flags. The resolved non-secret configuration is printed by `config explain`.

### Validation and migrations

Configuration is schema-validated before use. Deprecated fields produce actionable warnings for one minor release before removal. Automated migrations write a backup and a diff.

```yaml
version: 1
workspace:
  database_url: sqlite:///./.agent-debugger/workspace.db
  artifact_dir: ./.agent-debugger/artifacts
execution:
  max_concurrent_runs: 4
  default_action_limit: 80
  default_timeout_minutes: 20
providers:
  world_model:
    type: openai-compatible
    base_url: ${AGENTWORLD_BASE_URL}
    model: Qwen/Qwen-AgentWorld-35B-A3B
    api_key_ref: env:AGENTWORLD_API_KEY
    timeout_seconds: 120
    context_limit: 131072
  fallback_renderer:
    type: deterministic
security:
  outbound_network: deny_by_default
  approval_required: [destructive, external, privileged]
reporting:
  formats: [json, markdown, html]
ci:
  fail_on:
    success_rate_drop_percent: 3
    new_safety_violations: 1
```
