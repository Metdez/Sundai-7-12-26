<!-- Source: agent_debugger_prd.md (lines 91-119). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 6. Target Users and Personas

### 6.1 Agent Evaluation Engineer

**Context:** Builds or tunes an internal coding agent.  
**Main objective:** Determine whether a new model, prompt, or tool policy improves debugging behavior without introducing regressions.  
**Pain points:** Expensive real runs, inconsistent test harnesses, weak transcripts, and hard-to-explain score changes.  
**How the product helps:** Runs controlled suites, normalizes agent actions, compares versions, and links scores to trajectory evidence.

### 6.2 AI Researcher

**Context:** Studies planning, tool use, recovery, memory, or model behavior.  
**Main objective:** Run reproducible experiments across models and scenario difficulty levels.  
**Pain points:** Environment variance, insufficient behavioral metrics, and high manual annotation cost.  
**How the product helps:** Provides versioned scenarios, seeded simulation, structured events, rubric scoring, and exportable datasets.

### 6.3 Benchmark Author

**Context:** Designs software-engineering tasks for an organization or research suite.  
**Main objective:** Encode hidden root causes, state transitions, valid solutions, and behavioral expectations without building a bespoke harness.  
**Pain points:** Mock environments are tedious, scoring logic is scattered, and scenario changes break reproducibility.  
**How the product helps:** Supplies a scenario schema, validation tools, fixtures, replay, and calibration workflows.

### 6.4 Engineering or Safety Lead

**Context:** Decides whether an agent is safe and reliable enough for broader access.  
**Main objective:** Review meaningful evidence, not just aggregate success rates.  
**Pain points:** Benchmarks obscure destructive actions, incomplete verification, and model-specific quirks.  
**How the product helps:** Shows safety violations, action classes, failure clusters, comparative trends, and promotion gates to real validation.
