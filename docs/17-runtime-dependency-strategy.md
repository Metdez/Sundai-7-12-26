<!-- Source: agent_debugger_prd.md (lines 1052-1116). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 17. Runtime and Dependency Strategy

### Core runtime

- Python 3.12+ application core, CLI, API, state engine, scoring, and workers.
- Pydantic or equivalent for schemas.
- SQLite for local workspaces; PostgreSQL as an optional shared deployment backend.
- Content-addressed filesystem artifacts locally.

The core runtime ships with the product package or standalone binary bundle.

### Project-native tools

Agent frameworks and model clients remain in adapter packages. The product does not require a specific agent framework.

### External executables

- Optional Docker or Podman for real validation.
- Git may be used for scenario author workflows but is not required for simulated Git state.
- Browser for the web UI.

Availability is detected by `doctor`; missing optional tools disable only their dependent capability.

### Containers

Recommended for:

- Qwen-AgentWorld serving where local GPU resources exist.
- Real-environment validation.
- Reproducible hosted workers.

Images must be pinned by digest in controlled deployments.

### Managed services

Optional OpenAI-compatible model endpoints, object storage, PostgreSQL, and identity provider. These are not required for local MVP use.

### Optional integrations

GitHub Actions, SSO, external secret managers, hosted GPU inference, and issue trackers.

### Deployment approach comparison

1. **Native installation**  
   Lowest friction for the core and CLI; weak isolation for real execution and model dependencies.
2. **Containerized execution**  
   Strong reproducibility and isolation; higher Windows and GPU setup complexity.
3. **Hybrid resolution**  
   Native core and dashboard, external or containerized model server, container-only real validator.
4. **Hosted execution**  
   Simplest client experience at scale; introduces privacy, multi-tenancy, cost, and operations complexity.

### Recommendation

Use **hybrid resolution**. Ship the core as a Python package and optional standalone desktop bundle. Connect to Qwen-AgentWorld through its OpenAI-compatible API whether it runs in WSL2, Docker, a Linux GPU server, or a managed endpoint. Require containers only for real validation. This preserves Windows usability while isolating high-risk and GPU-specific components.

Qwen-AgentWorld's current open 35B mixture-of-experts model has 3B active parameters and a long context window. The product should default to a reduced but configurable context projection, target at least 128K when provider capacity permits, and avoid requiring local ownership of the model.

### Missing dependency behavior

- Missing simulation provider: deterministic renderer remains available; model-based runs fail preflight or fall back according to policy.
- Missing container runtime: real validation is disabled with remediation guidance.
- Missing database migration: startup enters read-only recovery mode.
- Incompatible adapter: registration fails before run submission.

