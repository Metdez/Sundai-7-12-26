<!-- Source: agent_debugger_prd.md (lines 859-889). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 14. Non-Functional Requirements

**NFR-001 Reliability:** A single run failure shall not corrupt other runs or the workspace. Target: 99.5% successful local orchestration excluding external provider failures during beta.

**NFR-002 Reproducibility:** Authoritative state replay shall match the recorded final checksum for at least 99.99% of released scenario fixture runs.

**NFR-003 Performance:** Local API p95 latency for non-model metadata operations shall be under 300 ms with 10,000 stored runs on reference hardware. Model latency is measured separately.

**NFR-004 Scalability:** The initial architecture shall support at least 20 concurrent simulated runs per worker when external model capacity permits, without redesigning persistence contracts.

**NFR-005 Portability:** CLI and server shall support Windows 11, Linux, and macOS. GPU simulation may run remotely or through WSL2/Linux.

**NFR-006 Security:** No untrusted scenario or agent action shall execute on the host outside constrained handlers. Real execution must occur in an isolated runner.

**NFR-007 Privacy:** Run content shall remain local by default. Any outbound model call must be declared by provider configuration and visible in the run manifest.

**NFR-008 Observability:** Every run shall include correlation IDs, structured lifecycle logs, provider timings, and error category.

**NFR-009 Maintainability:** Core domain modules shall not import web UI or provider-specific SDKs. Public interfaces shall be versioned and contract-tested.

**NFR-010 Compatibility:** Scenario, action protocol, scoring profile, and run artifact schemas shall use semantic versions with explicit compatibility rules.

**NFR-011 Accessibility:** The web review interface should meet WCAG 2.2 AA for keyboard navigation, color contrast, focus order, and semantic tables before general availability.

**NFR-012 Offline operation:** Deterministic renderer, local storage, scenario validation, replay, and report review shall work without network access.

**NFR-013 Resource usage:** The core local service should use less than 500 MB RAM at idle and less than 1 GB excluding model servers, browser, and container validation.

**NFR-014 Data integrity:** Event logs shall be append-only and hash-chained; artifact writes shall be atomic.

**NFR-015 Recovery:** Interrupted local runs shall be marked abandoned or resumable according to policy on next startup; completed artifacts shall remain readable.
