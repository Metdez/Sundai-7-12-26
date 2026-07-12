<!-- Source: agent_debugger_prd.md (lines 121-135). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 7. Jobs to Be Done

> When I change a coding agent's model, prompt, tools, or memory policy, I want to rerun a fixed benchmark suite so I can detect behavioral improvements and regressions.

> When an agent fails a debugging task, I want to inspect the evidence and decision sequence so I can identify the first material mistake rather than only seeing the final answer.

> When I design a benchmark, I want to declare hidden state, valid transitions, misleading paths, and scoring rules so I can create realistic tasks without implementing a full repository runtime.

> When simulation indicates a promising fix, I want to promote the candidate to an isolated real environment so I can distinguish good process from technically correct execution.

> When comparing different agent frameworks, I want their actions translated into one canonical protocol so I can make fair comparisons.

> When an agent attempts risky or destructive actions, I want those actions classified and scored consistently so I can measure operational safety.

> When a run result is challenged, I want to replay its state transitions and evidence so I can explain and reproduce the score.
