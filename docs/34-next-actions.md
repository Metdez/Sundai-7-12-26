<!-- Source: agent_debugger_prd.md (lines 1888-1899). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 34. Recommended Next Actions

1. **Confirm the foundational decisions:** deterministic state beneath Qwen-AgentWorld; local-first hybrid deployment; simulation and real validation as separate claims; observable-action scoring rather than private chain-of-thought.
2. **Create initial specifications:** canonical action protocol v0.1, scenario manifest v0.1, event envelope v0.1, error taxonomy, and the login-environment-variable scenario state model.
3. **Build the first vertical slice:** one CLI command, one reference agent adapter, deterministic file/search/patch/test actions, append-only events, pass/fail scoring, and replay.
4. **Run the first dogfooding milestone:** compare two prompts for the same reference agent on the login scenario, then review whether the transcript exposes the expected investigation and verification differences.
5. **Proceed to Qwen-AgentWorld integration only when:** authoritative replay is deterministic, scenario fixtures pass, action limits and safety policy work, and the first comparison produces evidence-backed behavioral findings.

---

**Research basis for dependency assumptions:** Qwen-AgentWorld was publicly released in June 2026 as an Apache-2.0 language world model covering MCP, Search, Terminal, SWE, Android, Web, and OS. The open 35B-A3B model is documented as 35B total/3B active with a 262,144-token context and OpenAI-compatible serving through vLLM or SGLang. AgentWorldBench includes Terminal and SWE trajectories and evaluates generated observations for format, factuality, consistency, realism, and quality. These facts support its use as an observation renderer, while the architecture intentionally avoids treating it as the source of benchmark truth.
