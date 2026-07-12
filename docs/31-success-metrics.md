<!-- Source: agent_debugger_prd.md (lines 1797-1821). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 31. Success Metrics

### Launch metrics

- Median first successful deterministic run within 15 minutes of installation.
- At least 90% of pilot users complete setup without developer intervention.
- At least 10 validated scenarios across 5 fictional repositories.
- At least 2 agent configurations compared end to end.
- 100% of score findings in released scenarios have evidence references.
- Replay success above 99.99% on fixture runs.
- Zero host-command execution from simulated actions.
- Less than 2% unclassified platform failures in pilot suites.

### Long-term metrics

**Adoption:** Active workspaces, weekly suite runs, integrated CI repositories, and authored scenarios.  
**Time saved:** Reduction in human review time and avoided real-container runs. Target assumption: 50% reduction in early evaluation cost after calibration.  
**Reliability:** Run completion rate excluding external provider outages; replay divergence; artifact integrity failures.  
**Coverage:** Percentage of agent capabilities, failure classes, and action classes represented by suites.  
**Accuracy:** Human agreement with score findings; simulation-real outcome agreement by scenario class.  
**User trust:** Percentage of reviewers rating score explanations as sufficient and reproducible.  
**Setup time:** Median time from install to first model-rendered run.  
**Failure rate:** Provider, scenario, adapter, platform, and unknown failure rates tracked separately.  
**Output usefulness:** Percentage of failed runs that lead to an identified prompt, tool, model, or policy improvement.  
**Maintenance cost:** Scenario authoring hours per validated task and breakage rate per product release.
