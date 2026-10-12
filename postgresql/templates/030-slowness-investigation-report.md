# Chapter 030 — Slowness Investigation Report

**Status:** Draft; runtime-dependent fields pending.  
**Environment:** Lab / staging / production (select one).  
**Incident owner / reviewer:**  
**UTC start / end / evidence location:**  
**PostgreSQL version / instance identity / application deployment:**  

## Impact and measurement

- Affected operation and request/transaction boundary:
- Customer or synthetic impact; traffic volume and concurrency:
- Healthy comparison window:
- Latency/error objective and telemetry coverage:
- Pool/admission, execution, commit and delivery timing coverage:
- Retries, deadline behavior and correctness risks:
- Data sensitivity and evidence retention:

## Timeline

| UTC | Observation or action | Evidence file / metric | Owner |
|---|---|---|---|
| Pending | Baseline | Pending | Pending |
| Pending | Incident starts | Pending | Pending |
| Pending | Mechanism observed | Pending | Pending |
| Pending | Containment | Pending | Pending |
| Pending | Recovery validated | Pending | Pending |
| Pending | Separate durable experiment | Pending | Pending |

## Diagnosis

| Hypothesis | Supporting facts | Contrary evidence / visibility gap | Confidence | Next bounded check |
|---|---|---|---|---|
| Blocking | Pending | Pending | Pending | Pending |
| CPU / quota | Pending | Pending | Pending | Pending |
| Memory / spills | Pending | Pending | Pending | Pending |
| Storage / WAL | Pending | Pending | Pending | Pending |
| Estimates / plan | Pending | Pending | Pending | Pending |
| Pool / network / consumer | Pending | Pending | Pending | Pending |

**Observed facts:**  
**Confirmed mechanism:**  
**Inference and unresolved questions:**  
**Trigger and contributing conditions:**  

## Evidence quality

- PID + backend_start and relevant session scope:
- Snapshot timestamps, reset epochs and publication lag:
- Enabled timing and statement-statistics coverage:
- Plan mode, role, parameters, settings and dataset identity:
- Host/device/cgroup mapping or managed-service visibility gap:
- Sampling gaps and failed/incomplete captures:
- Successful result validation:
- Lab proxy limitations; no tail/SLO claims from eight serial requests:

## Containment and recovery

**Action / owner / exact scope:**  
**Expected result and abort threshold:**  
**Rollback:**  
**Actual effect and evidence:**  
**Recovery before durable change:**  
**Queues, retries, replication and unrelated workload checks:**  

| Window | Attempts / successful correct results / failures | Observed duration range | Wait/resource evidence | Acceptance / gap |
|---|---|---|---|---|
| Baseline | Pending | Pending | Pending | Pending |
| Incident | Pending | Pending | Pending | Pending |
| Recovered before statistics change | Pending | Pending | Pending | Pending |
| After durable experiment | Pending | Pending | Pending | Pending |

## Durable correction

**Hypothesis / object / maintenance budget / owner:**  
**Before and after estimates, actual rows, plan shape, execution time and buffers:**  
**Common/rare/NULL/incompatible parameter coverage:**  
**Observed latency gain or absence of gain:**  
**Change rollback and rollback evidence:**  
**Why this is separate from incident containment:**  

## Prevention and acceptance

| Action | Owner | Due date | Completion test | Rollback / risk |
|---|---|---|---|---|
| Maintenance transaction and lock budget | Pending | Pending | Pending | Pending |
| Distribution-change / plan regression coverage | Pending | Pending | Pending | Pending |
| Missing telemetry | Pending | Pending | Pending | Pending |

**Production recovery duration / representative traffic / thresholds / monitor owner:**  
**Scoped fixture cleanup and local-setting restoration evidence:**  
**Remaining risks and handoff:**  

[Return to chapter](../chapters/030-production-slowness-investigation-project.md)
