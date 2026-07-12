<!-- Source: agent_debugger_prd.md (lines 1823-1858). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 32. Open Questions

### 32.1 How much hidden reasoning should be requested or retained from evaluated agents?

**Why it matters:** Some agents expose only actions and summaries; requesting private chain-of-thought is unreliable, provider-dependent, and may be inappropriate.  
**Recommended assumption:** Score observable actions, stated hypotheses intended for the tool loop, and outcomes; do not require private chain-of-thought.  
**Resolver:** Product and research leads with provider policy review.  
**Deadline:** Before scoring profile v1 freezes in Phase 2.

### 32.2 What minimum real-trace calibration rate is required before labeling a scenario class trustworthy?

**Why it matters:** Simulation fidelity varies by task and command type.  
**Recommended assumption:** Require at least 20 representative real traces per scenario class and report confidence rather than a universal trust label.  
**Resolver:** Evaluation research lead using Phase 4 calibration data.  
**Deadline:** Phase 4 exit.

### 32.3 Which agent adapters should be first-party at launch?

**Why it matters:** Adapter breadth affects adoption but can distract from core validity.  
**Recommended assumption:** One simple OpenAI-compatible tool-loop reference adapter and one framework adapter selected from pilot demand.  
**Resolver:** Product lead based on design-partner usage.  
**Deadline:** Mid-Phase 1.

### 32.4 Should qualitative judge scores contribute to the default overall score?

**Why it matters:** They add nuance but may reduce reproducibility and create model dependence.  
**Recommended assumption:** Display them separately during beta; include in overall score only after human-agreement thresholds are met.  
**Resolver:** Research lead and product governance.  
**Deadline:** End of Phase 2.

### 32.5 What artifact retention policy is acceptable for proprietary code in shared deployments?

**Why it matters:** Transcripts and patches may contain sensitive source.  
**Recommended assumption:** Local-first indefinite retention controlled by the user; shared deployments default to 30-day raw payload retention and longer normalized metadata retention.  
**Resolver:** Security, legal, and pilot customers.  
**Deadline:** Before Phase 5 team beta.
