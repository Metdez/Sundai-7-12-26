<!-- Source: agent_debugger_prd.md (lines 1615-1631). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 27. Risks and Mitigations

| Risk | Likelihood | Impact | Warning signs | Mitigation | Contingency |
|---|---|---:|---|---|---|
| Simulator contradicts authoritative state | High | High | Rising retry/fallback rate; reviewer distrust | Protected facts, conformance validator, deterministic fallback, calibration | Disable model rendering for affected scenario/provider version |
| Scenario authoring is too complex | Medium | High | Few new scenarios; repeated support requests | Templates, authoring SDK, visual preview, reusable handlers | Narrow initial scenario classes and provide professional authoring guidance |
| Scores overclaim reasoning quality | Medium | High | Weak human agreement; unexplained rank changes | Rule-first scoring, evidence links, confidence labels, validation studies | Remove low-agreement dimensions from aggregate score |
| Agents exploit simulator artifacts | Medium | High | Unnatural prompt probing; benchmark-specific hacks | Hidden system boundaries, diverse renderers, adversarial tests, real validation | Rotate scenario variants and penalize protocol abuse |
| Qwen-AgentWorld infrastructure is costly | Medium | Medium | OOM, low throughput, provider queues | Remote endpoints, quantization options, bounded context, deterministic mode | Support alternative renderers and hosted provider abstraction |
| Real validator escapes isolation | Low | Critical | Unexpected host access or network traffic | Rootless containers, no daemon socket in app, seccomp, quotas, audits | Disable real validation and require isolated remote runner |
| Comparison results are invalid across versions | Medium | High | Large unexplained deltas | Compatibility envelope and lockfiles | Require fresh baseline under current scenario/scorer/provider |
| Secrets appear in transcripts | Medium | High | Scanner findings or user reports | Secret references, redaction, least privilege, provider separation | Quarantine artifacts, revoke secrets, incident workflow |
| Scope expands into agent framework or training platform | High | Medium | Core modules accumulate planning/training logic | Enforce non-goals and API boundaries | Split adjacent product into separate service or defer |
| Windows setup remains fragile | Medium | Medium | Doctor failures, WSL/GPU support load | Endpoint-based provider design, signed bundle, detailed diagnostics | Offer remote provider and container runner reference deployment |
| Low agreement between simulation and real execution | Medium | High | Calibration mismatch rate | Promotion samples, scenario-specific calibration, deterministic core | Restrict claims to behavioral evaluation and increase real-run share |
| Run storage grows rapidly | Medium | Medium | Large raw transcripts and diffs | Content addressing, compression, retention tiers, payload limits | Archive raw provider payloads and retain normalized events |
| Third-party model/license changes | Low | Medium | New terms or incompatible releases | Pin versions, abstraction layer, license review | Replace provider without changing scenario or core contracts |
