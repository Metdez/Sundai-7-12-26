<!-- Source: agent_debugger_prd.md (lines 16-58). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 2. Background and Motivation

### Current situation

Coding-agent evaluation commonly relies on one of four approaches:

1. Real repository and container benchmarks, which are technically faithful but expensive, slow, operationally complex, and risky.
2. Static question-and-answer tests, which are cheap but fail to measure multi-step investigation and recovery behavior.
3. Hand-scripted mock tools, which are deterministic but costly to author and often too brittle or unrealistic.
4. LLM-only simulated environments, which are flexible but may drift, hallucinate state, or award success inconsistently.

Teams therefore struggle to answer practical questions such as whether an agent inspects evidence before editing, recognizes a wrong hypothesis, avoids destructive commands, verifies its fix, or regresses after a prompt or model change.

### Pain points

- A pass/fail result hides unsafe or low-quality reasoning paths.
- Real-environment execution creates infrastructure cost and security exposure early in development.
- Existing benchmark outputs are difficult to compare across agent frameworks because tools and transcript formats differ.
- Repeated runs may be non-reproducible when the environment itself is probabilistic.
- Benchmark authors lack a concise way to specify hidden root causes, valid solution paths, misleading evidence, and behavioral scoring.
- Human review is labor-intensive without structured timelines, evidence, and automated annotations.

### Why current approaches are insufficient

Real execution remains necessary to prove technical correctness, but it is not the most efficient first-line instrument for diagnosing agent behavior. Conversely, unconstrained model simulation is unsuitable as the sole source of truth because small inconsistencies can corrupt evaluation. The opportunity is to combine deterministic benchmark semantics with realistic language-model rendering and reserve real execution for confirmation.

### Inherited ideas

The initial concept establishes the product's essential evaluation dimensions: task completion, investigation, reasoning, testing, recovery, efficiency, and safety; scenario difficulty levels; cross-agent comparison; regression testing; transcript review; Windows-friendly operation; and eventual real-environment validation.

Qwen-AgentWorld is a relevant enabling dependency because it is explicitly trained to predict environment observations across Terminal and SWE domains, supports long multi-turn context, and can be served through OpenAI-compatible endpoints using common inference servers. Its role in this PRD is limited to simulation and controlled perturbation, not authoritative state or grading.

### Newly proposed capabilities

This PRD adds:

- A deterministic scenario state engine beneath the language world model.
- A canonical action and observation protocol independent of agent framework.
- Evidence-backed, replayable scoring with requirement-to-event traceability.
- Simulation conformance tests and calibration against real container traces.
- A scenario package format with fixtures, state transitions, rubrics, and versioned provenance.
- Explicit action safety classes and approval gates.
- A staged product architecture that begins with a local CLI and API before adding broader surfaces.
