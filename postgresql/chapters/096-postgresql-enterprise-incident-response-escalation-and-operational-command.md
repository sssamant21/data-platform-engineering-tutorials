# Chapter 096 — PostgreSQL Enterprise Incident Response, Escalation and Operational Command

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Establish a reproducible enterprise incident response framework for PostgreSQL availability, latency, integrity, backup and replication incidents. Connect [Chapter 095 — Operational Readiness Review](095-postgresql-enterprise-reliability-and-operational-readiness-review.md) with production incident command, technical diagnosis, stakeholder communications, safe mitigations and post-incident learning.

**Rule:** restore customer service safely while protecting data integrity, preserving evidence and maintaining one incident commander and a single authoritative change log.

## 2. Incident severity and triggers

| Severity | Example impact | Response expectation |
|---|---|---|
| SEV1 | Broad outage, confirmed data loss, split-brain risk | Immediate incident command, executive/business escalation |
| SEV2 | Material latency, partial outage, replication/backup degradation | On-call response and coordinated mitigation |
| SEV3 | Limited impact, warning threshold or recoverable maintenance issue | Tracked response within team policy |

Severity thresholds, paging SLAs and communication cadence must be defined by the organization. Do not infer customer impact from one PostgreSQL metric alone.

## 3. Command roles and decision rights

- **Incident commander (IC):** sets severity, priorities, decisions, communication cadence and recovery declaration.
- **DBRE technical lead:** owns PostgreSQL diagnosis, data safety and database recovery plan.
- **SRE operations lead:** owns application SLO, telemetry, infrastructure, traffic and automation.
- **Communications lead:** sends factual, timestamped updates and manages stakeholder channels.
- **Scribe:** maintains UTC timeline, action owner, hypothesis, evidence and decision record.
- **Security/data owner:** approves sensitive data, access or integrity decisions where needed.
- **Business/application owner:** confirms user impact, transaction correctness and restoration.

A single person may fill multiple roles during a small incident, but role ownership must remain explicit.

## 4. First 15 minutes: safe triage

1. Acknowledge alert, identify affected application, environment and customer impact.
2. Open incident channel, ticket and UTC timeline; assign IC and technical lead.
3. Confirm database role and cluster topology before any write or failover operation.
4. Compare application p95/p99, errors, throughput and pool waits with database sessions, waits, locks, WAL, disk and host metrics.
5. Check recent deploys, config changes, ingestion/batch jobs and infrastructure events.
6. State working hypothesis, uncertainty, next check and mitigation owner.
7. Preserve pre-mitigation snapshots and avoid simultaneous uncontrolled changes.

Use [096 read-only SQL](../labs/sql/096-incident-command-triage.sql) for safe inspection; it does not replace host/cloud and application telemetry.

## 5. Diagnosis by symptom

| Symptom | Investigate | Avoid |
|---|---|---|
| Query latency | Wait events, `pg_stat_statements`, plans, I/O, locks | Killing sessions without impact review |
| Connection exhaustion | Pooler, `pg_stat_activity`, max connections, client retries | Raising limits without memory model |
| Lock pileup | Blocking chain, long transactions, idle-in-transaction | Terminating unknown business transactions |
| WAL/disk growth | Slots, archiving, replication, checkpoints, storage | Deleting `pg_wal` files manually |
| Replica lag | Receive/replay positions, WAN, CPU/I/O, large transactions | Assuming lag bytes equal RPO seconds |
| Primary unavailable | Control plane, quorum, fencing, backup/DR | Promoting without single-writer proof |
| Data deletion/corruption | Scope, audit, backups/PITR, application reconciliation | Overwriting live data with unverified restore |

## 6. Mitigation safety hierarchy

Prefer reversible, scoped changes: rate limiting, reducing batch concurrency, pausing approved ingestion, fixing pooler retry storms, or cancelling a **known** runaway statement after ownership review. Escalate to session termination, config restart, storage changes or failover only with explicit risk assessment, approval and rollback.

`pg_cancel_backend` requests cancellation of the active query; `pg_terminate_backend` ends a session and may roll back its transaction. Neither should be applied broadly without confirming business impact. For replication/failover, enforce Chapter 091 fencing.

## 7. Incident command cycle

```text
Detect -> declare -> assign roles -> quantify impact
       -> collect evidence -> hypothesis -> approve mitigation
       -> execute one change -> observe -> accept or rollback
       -> validate application -> communicate -> close -> PIR
```

For every change record owner, reason, expected result, abort threshold, exact UTC time, rollback and observed result. Freeze unrelated risky changes during SEV1/SEV2 unless required for recovery.

## 8. Communications and escalation

Provide a consistent update: current impact, start time, verified facts, mitigation in progress, uncertainty, next update and responsible team. Do not speculate on root cause or blame individuals. Escalate when RTO/SLO breach approaches, data integrity is uncertain, restore/failover is required, or the current team lacks permissions/authority.

## 9. Recovery acceptance

Service is not recovered merely because PostgreSQL accepts connections. Verify application success transactions, p95/p99, error rate, pool routing, business record correctness, replica health, WAL archiving, backup protection, monitoring and on-call ownership. Continue heightened monitoring after recovery and declare closure with the IC.

## 10. Evidence and post-incident review

Capture timestamped dashboards, SQL outputs, logs, cloud events, changes, alerts, stakeholder updates and data recovery decisions. Redact secrets and customer data. PIR should include impact, timeline, contributing conditions, detection/response gaps, what helped, what delayed recovery, corrective actions, owners, due dates and verification plan. Avoid unsupported causal claims.

## 11. Practice scenarios

- Long-running transaction blocks critical writes.
- Connection pool retry storm saturates PostgreSQL.
- WAL archiver failure causes disk pressure.
- Replica lag during planned maintenance.
- Region failure with ambiguous fencing; expected decision **STOP**.
- Accidental deletion requiring isolated PITR and controlled data reconciliation.

Run only bounded failure injection in disposable environments.

## 12. Lab and acceptance

Use [Chapter 096 lab](../labs/096-postgresql-enterprise-incident-response-escalation-and-operational-command-lab.md), [read-only triage SQL](../labs/sql/096-incident-command-triage.sql), [incident timeline template](../labs/incident/096-incident-command-timeline.csv), [incident communications template](../labs/incident/096-incident-communications-template.md), and [acceptance scorecard](../labs/acceptance/096-incident-command-scorecard.csv).

**PASS requires:** clear IC, measured impact, evidence-based triage, approved reversible mitigation, customer/application recovery, communications, preserved timeline and assigned corrective actions. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/functions-admin.html
- https://www.postgresql.org/docs/18/explicit-locking.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/high-availability.html

**Next:** Chapter 097 — PostgreSQL Production Incident Simulation, Root Cause Analysis and Corrective Actions.
