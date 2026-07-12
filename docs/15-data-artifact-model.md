<!-- Source: agent_debugger_prd.md (lines 891-994). Content below is verbatim from the PRD — do not edit here; edit the PRD and re-split. -->

## 15. Data and Artifact Model

### 15.1 ScenarioPackage

**Purpose:** Immutable benchmark definition.  
**Required fields:** `scenario_id`, `version`, `title`, `task`, `initial_state`, `allowed_actions`, `success_predicates`, `failure_predicates`, `scoring_profile`, `schema_version`.  
**Optional fields:** renderer prompts, perturbations, real-validation fixture, tags, references, author notes.  
**Source of truth:** Version-controlled package directory and digest.  
**Storage/ownership:** User repository or installed scenario registry; copied by digest into run provenance as needed.  
**Versioning:** Semantic version plus content digest.  
**Relationships:** Referenced by RunManifest, Suite, and CalibrationRecord.

### 15.2 AuthoritativeState

**Purpose:** Current fictional repository and environment truth.  
**Required fields:** virtual file tree, environment variables, dependency state, test state, Git state, hidden facts, transition counter.  
**Optional fields:** process state, logs, package cache, service state.  
**Source of truth:** State engine.  
**Storage:** In-memory during run with periodic content-addressed snapshots.  
**Versioning:** State schema version and per-transition hash.  
**Relationships:** Produced by ScenarioPackage and changed by ActionEvents.

### 15.3 AgentRevision

**Purpose:** Immutable executable configuration.  
**Required fields:** adapter ID/version, model identifier, prompt digest, tool contract version, limits, generation settings.  
**Optional fields:** memory strategy, planning mode, tags, pricing metadata.  
**Source of truth:** Workspace database.  
**Secrets:** References only.  
**Versioning:** New revision on material change.  
**Relationships:** Referenced by RunManifest and ComparisonReport.

### 15.4 RunManifest

**Purpose:** Complete reproducibility envelope.  
**Required fields:** run ID, scenario digest, agent revision, renderer revision, scorer revision, seed, limits, timestamps, product version, action protocol version.  
**Optional fields:** baseline ID, CI metadata, operator, labels.  
**Source of truth:** Immutable record created before execution.  
**Storage:** Database plus JSON export.  
**Relationships:** Parent of all RunEvents and RunArtifacts.

### 15.5 RunEvent

**Purpose:** Append-only record of the session.  
**Required fields:** event ID, run ID, sequence, event type, timestamp, payload, previous hash, event hash.  
**Optional fields:** parent event, evidence tags, redaction metadata.  
**Source of truth:** Event store.  
**Storage:** Database with export to JSONL.  
**Versioning:** Event schema version.  
**Relationships:** Links actions, policy decisions, state results, observations, findings, and lifecycle changes.

### 15.6 Scorecard and Finding

**Purpose:** Explain evaluation results.  
**Required fields:** dimension, score, maximum, scorer version, confidence, findings, evidence event IDs.  
**Optional fields:** judge output digest, human annotation, override reason.  
**Source of truth:** Scoring engine output.  
**Storage:** Database and report artifacts.  
**Versioning:** Scoring profile and scorer version.

### 15.7 Artifact

**Purpose:** Store transcripts, diffs, logs, snapshots, reports, and validation evidence.  
**Required fields:** artifact ID, media type, digest, size, creation event, logical role.  
**Optional fields:** compression, redaction status, external location.  
**Source of truth:** Content-addressed file store.  
**Storage:** Local workspace initially; object storage later.  
**Versioning:** Immutable by digest.

### 15.8 Illustrative scenario manifest

```yaml
schema_version: 1.0.0
scenario_id: webapp.login-env-var
version: 1.0.0
title: Login test fails because the signing secret is misconfigured
difficulty: beginner
tags: [python, web, authentication, environment]
task: Diagnose and repair the failing login test.
initial_state:
  fixture: fixtures/repository
  hidden_facts:
    root_cause: JWT_SECRET is absent from the test environment
allowed_actions:
  - fs.list
  - fs.read
  - fs.search
  - fs.patch
  - shell.run_allowlisted
  - test.run
  - git.diff
success_predicates:
  - test_suite: tests/test_login.py
    status: pass
  - file_scope:
      max_changed_files: 2
failure_predicates:
  - destructive_action_attempted: true
renderer:
  type: hybrid
  provider: qwen-agentworld
  deterministic_fallback: true
scoring_profile: coding-debug-v1
```
