<!-- Source: agent_debugger_prd.md (lines 79-89). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 5. Non-Goals

- **General-purpose coding-agent framework:** Agent Debugger evaluates agents; it does not replace their planners, memory systems, or model clients.
- **Proof of software correctness from simulation:** Simulated success is behavioral evidence, not proof that a patch works in a real repository.
- **Unrestricted autonomous remediation of production systems:** Production access and deployment are outside initial scope.
- **Full IDE replacement:** The dashboard reviews runs; it is not a primary code editor.
- **Training infrastructure in the MVP:** Reinforcement-learning data export may be supported later, but model training orchestration is excluded.
- **Automatic generation of trustworthy scenarios without review:** Scenario generation may be assisted later, but v1 requires authored and validated scenario packages.
- **Arbitrary shell compatibility:** The MVP supports a normalized subset of Linux-like file, test, package, and Git actions relevant to benchmark tasks.
- **A broad plugin marketplace:** Extension interfaces will remain narrow until repeated integration needs justify a formal plugin ecosystem.
- **Cloud multi-tenancy in the first vertical slice:** The MVP is local-first and single-workspace; hosted team features follow after core validity is established.
