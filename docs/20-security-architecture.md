<!-- Source: agent_debugger_prd.md (lines 1219-1286). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 20. Security Architecture

### Trust boundaries

1. User and CI client to API/CLI.
2. Core orchestrator to untrusted agent/model provider.
3. Core orchestrator to simulation provider.
4. Core to scenario package and optional constrained handlers.
5. Core to artifact/database storage.
6. Real validator control plane to ephemeral execution container.
7. Optional local service to external networks.

### Threat model

Key threats include prompt injection through scenario content, malicious or accidental destructive agent actions, host command execution, secret leakage, path traversal, artifact poisoning, simulator-generated false evidence, compromised dependencies or model images, unauthorized workspace access, denial of service through runaway sessions, and cross-run data leakage in shared deployments.

### Secret handling and credential isolation

- Store references, not values.
- Resolve secrets just-in-time in the narrowest process.
- Redact known and heuristic secret patterns from logs and artifacts.
- Do not pass agent-provider credentials to the simulation provider or validator.
- Support per-provider credentials and rotation.

### Input validation

- Schema-validate every action and observation.
- Normalize and constrain virtual paths.
- Reject absolute host paths, traversal, null bytes, and unsupported encodings.
- Enforce size limits on prompts, files, patches, logs, and artifacts.

### Command execution safety

Simulated shell actions are interpreted by scenario handlers, not executed on the host. Real validation accepts only scenario-declared command templates with bounded arguments. Shell interpolation is avoided; subprocess argument arrays are used.

### Filesystem and network boundaries

- Simulated state uses a virtual filesystem namespace.
- Real containers receive only scenario fixture mounts.
- Network is disabled by default in real validation.
- Any outbound access must be explicitly declared, domain-allowlisted, and reported.

### Supply-chain and container security

- Pin package locks and container images.
- Generate software bills of materials for releases and validator images.
- Scan dependencies and images in CI.
- Run validators rootless where possible, drop Linux capabilities, use read-only base filesystems, apply seccomp/AppArmor or equivalent, and set resource quotas.

### Logging and redaction

Structured logs distinguish raw provider payload availability from redacted default views. Sensitive raw artifacts, if retained at all, require explicit policy and separate access controls.

### Permission model

Local MVP: workspace owner. Shared deployment: viewer, evaluator, scenario author, agent administrator, and workspace administrator. Real-validation approval is a separate permission.

### Action classes

| Action class | Examples | Default policy |
|---|---|---|
| Read-only | list, read, search, inspect logs, git status | Allowed |
| Safe write | targeted patch within virtual repo, create test file | Allowed with scope limits |
| Destructive | delete files, reset history, broad overwrite | Blocked or explicit scenario approval |
| External/outbound | network request, package download, issue creation | Blocked by default; approval and allowlist required |
| Privileged | host access, daemon socket, elevated command | Always blocked in simulation; dedicated administrator-approved validator only |

Every blocked or approved action remains part of the transcript and safety score.
