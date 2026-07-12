<!-- Source: agent_debugger_prd.md (lines 1117-1160). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 18. Distribution and Installation

### Distribution channels

- PyPI package for CLI/server/SDK.
- Signed standalone releases for Windows, macOS, and Linux after MVP stabilization.
- OCI images for server, worker, and real validator.
- First-party GitHub Action wrapping the CLI.
- Source installation for contributors.

### Installation flow

```bash
pipx install agent-debugger
agent-debugger init
agent-debugger doctor
agent-debugger serve
```

Windows users may alternatively install a signed bundle that includes the core runtime and launches a local browser UI. The bundle should not include large model weights.

### Initial setup

The setup wizard detects WSL2, Docker/Podman, reachable world-model endpoints, and OS credential-store support. It runs a deterministic smoke test before model configuration.

### Upgrade flow

- Semantic versioned packages.
- `upgrade --check` compatibility preview.
- Automatic database backup.
- Forward-only migrations with documented rollback using backups.
- Scenario and protocol compatibility warnings before breaking upgrades.

### Uninstallation

Uninstalling the application does not remove workspaces by default. A separate `workspace purge` command requires confirmation and supports export first.

### CI installation

Pin the CLI version and scenario lockfile. Cache only non-secret packages and immutable scenario artifacts. Upload reports regardless of pass/fail.

### Air-gapped environments

Support wheelhouse installation, offline deterministic rendering, local model endpoints, preloaded container images, and local scenario registries. All network attempts must be disableable and auditable.
