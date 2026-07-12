<!-- Source: agent_debugger_prd.md (lines 66-77). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 4. Goals

1. Measure coding-agent debugging behavior across multi-step, stateful tasks rather than final answers alone.
2. Produce reproducible runs whose authoritative state and scoring can be replayed from recorded inputs.
3. Reduce the cost and risk of early-stage agent evaluation compared with running every trial in a real environment.
4. Compare models, prompts, tools, planning policies, memory strategies, and agent versions on identical scenarios.
5. Detect behavioral regressions in investigation, recovery, verification, efficiency, and safety.
6. Provide complete evidence for each score and final outcome.
7. Support progressive validation from simulation to isolated real execution.
8. Make benchmark scenarios inspectable, versioned, testable, and portable.
9. Operate on Windows through a browser or desktop-friendly local service while allowing model infrastructure to run in WSL2, containers, Linux hosts, or managed GPU services.
10. Permit incremental adoption through a framework-neutral action protocol and thin adapters.
