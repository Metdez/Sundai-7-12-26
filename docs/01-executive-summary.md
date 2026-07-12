<!-- Source: agent_debugger_prd.md (lines 8-14). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 1. Executive Summary

Agent Debugger is a benchmark authoring, execution, and analysis platform for evaluating how AI coding agents investigate, diagnose, repair, and verify software failures. It is designed for agent developers, model teams, research groups, and engineering organizations that need repeatable evidence about an agent's behavior before granting it access to real repositories and execution environments.

A test run places a coding agent inside a fictional but stateful software project. The agent may inspect files, search code, execute commands, edit files, run tests, inspect logs, and use version-control operations through a normalized tool protocol. Agent Debugger applies each action to an authoritative scenario state engine, then uses a simulation provider - initially Qwen-AgentWorld - to produce realistic environment observations consistent with that state. The platform records the full trajectory and scores not only task completion, but also investigation quality, hypothesis discipline, verification, recovery, efficiency, and safety.

The key differentiator is a **hybrid truth-and-simulation architecture**. A deterministic scenario model owns hidden root causes, state transitions, allowed actions, success conditions, and scoring facts. A language world model renders realistic outputs and controlled ambiguity, but does not decide whether the task is solved. This preserves reproducibility and auditability while retaining the flexibility and lower cost of model-based environment simulation.
