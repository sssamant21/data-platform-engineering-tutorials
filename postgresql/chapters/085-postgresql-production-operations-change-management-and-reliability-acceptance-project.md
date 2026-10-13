# Chapter 085 — PostgreSQL Production Operations, Change Management and Reliability Acceptance Project

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime acceptance pending

## 1. Mission and scope

Execute an evidence-driven PostgreSQL production operations capstone integrating [Chapter 081 — Extension Lifecycle](081-postgresql-extensions-compatibility-and-operational-lifecycle.md), [Chapter 082 — Version Upgrades](082-postgresql-version-upgrades-compatibility-testing-and-rollback-planning.md), [Chapter 083 — Configuration and IaC](083-postgresql-configuration-management-infrastructure-as-code-and-drift-detection.md) and [Chapter 084 — Maintenance Automation](084-postgresql-maintenance-automation-scheduling-and-operational-runbooks.md).

A successful SQL command is **not** sufficient for acceptance. Prove the change was authorized, reversible or recoverable, observable, and safe for the application and its recovery objectives.

## 2. Operational change lifecycle

```text
Change request and risk classification
                |
Inventory -> baseline -> compatibility -> backup/restore preflight
                |
   Approval + maintenance window + communications
                |
     Dry run / staged rollout / execution
                |
  Database + application + HA/DR verification
                |
        PASS / ROLLBACK / RECOVER
                |
     Evidence, ownership and post-review
```

Define a change commander, executor, independent verifier, application owner, security reviewer (if relevant), and rollback decision-maker. Separate duties when required by policy.

## 3. Change classification and risk

| Change | Main risk | Minimum preflight | Rollback boundary |
|---|---|---|---|
| Extension install/update | Binary/SQL incompatibility, permissions, restart | Compatibility matrix, replica inventory, restore | Extension downgrade may be unsupported |
| PostgreSQL minor upgrade | Restart, package mismatch, driver compatibility | Supported versions, HA plan, app smoke tests | Restore/redeploy supported binaries as appropriate |
| PostgreSQL major upgrade | Data format, replication, extension incompatibility | pg_upgrade --check or logical-migration rehearsal | Target writes make old source stale |
| Configuration/IaC change | Pending restart, wrong precedence, drift | Desired/effective baseline, controller owner | Revert declaration and reload/restart |
| Maintenance job | Locks, I/O/WAL saturation, data retention | SLO, disk, backup, job concurrency and target checks | Some actions irreversible; restore may be needed |

Risk increases with blast radius, write impact, expected outage, irreversible changes, lack of verified backup, incomplete telemetry or unclear ownership.

## 4. Readiness gates

All critical gates must be assessed before execution:

1. **Change identity:** ticket, scope, approver, owner, start/end UTC, communication and abort criteria.
2. **Baseline:** source/target PostgreSQL versions, installed extensions, config, workload and HA/DR topology.
3. **Compatibility:** binaries, extension scripts, drivers, schema, SQL, collation, replication and managed-service constraints.
4. **Recoverability:** recent backup, archive continuity, encryption key access and tested isolated restore.
5. **Capacity:** disk headroom, WAL retention, memory, CPU and expected temporary space.
6. **Availability:** primary/standby state, lag, fencing/leader ownership, connection routing and error budget.
7. **Observability:** dashboards, logs, alerts, application synthetic tests and incident channel.
8. **Rollback:** last safe decision point, authoritative writer and forward-recovery procedure.

**STOP** if a mandatory gate is missing or NOT VERIFIED; do not convert a tabletop review into a PASS.

## 5. Change execution strategy

### 5.1 Prepare

Capture [085 operational inspection SQL](../labs/sql/085-production-change-preflight.sql) output in every relevant database and node. Review the IaC diff, extension compatibility and planned maintenance SQL. Verify independent backup recovery and stakeholder availability.

### 5.2 Dry run

Rehearse the exact change on a disposable environment with representative data and the same version/extension packages. Record elapsed time, lock waits, resource impact, replica behavior, application errors and postchecks. Simulate a failure and validate the rollback decision.

### 5.3 Execute

Use a bounded maintenance window and one approved executor. For each step: record UTC timestamp, expected effect, observed result, next gate and abort condition. Avoid simultaneous unrelated configuration, schema and extension changes unless the change plan explicitly handles their dependencies.

### 5.4 Verify

Verify both PostgreSQL and application: read/write operations, latency, error rate, pooler connections, replication, backups, security posture, logs and monitoring. Compare to baseline over an agreed observation window. An empty `pending_restart` alone does not prove service health.

## 6. Failure and rollback decision matrix

| Failure point | Decision | Required validation |
|---|---|---|
| Preflight gate fails | Abort before changes | Original application healthy |
| Reloadable setting regression | Revert via authoritative controller; reload | Effective setting, workload and logs |
| Restart-required setting regression | Approved HA-aware restart/rollback | Primary routing, replication, app health |
| Extension update regression | Consult supported downgrade path; otherwise restore/recover | SQL compatibility and data integrity |
| Maintenance lock timeout | Stop and investigate blockers | No partial destructive operation |
| Upgrade target has accepted writes | Treat old source as stale; plan reconciliation/reverse migration | Transaction consistency and RPO |
| Backup restore fails | Escalate; stop irreversible steps | Independent recovery path established |

Do not promise zero-data-loss rollback after target writes without a tested reverse data path. For destructive partition retention, deletion or schema changes, restoration may be the only recovery.

## 7. Observability and SLO acceptance

Record change duration, database and application availability, p95/p99 latency, error rate, connection failures, lock wait time, deadlocks, disk/WAL growth, replication lag, backup health and alert delivery. Compare against **predeclared** thresholds; never invent a universal latency or RTO target.

An alert should fire on failed postchecks or missing evidence, not merely on process exit status. Require a separate verifier to confirm the final application result.

## 8. Operational runbooks

**Abort:** stop further changes, preserve evidence, notify owners, verify original state, and record reason.

**Rollback:** confirm authoritative writer and data consistency, use the approved reverse change or recovery plan, validate database and application health, and capture remaining risks.

**Escalation:** if recovery exceeds RTO, replication/fencing is uncertain, backup keys are unavailable or data loss is possible, activate incident command and DR runbooks.

**Post-change:** document deviations, corrective actions, owner, due date, change history, runbook improvements and independent signoff.

## 9. Compliance and audit evidence

Retain approved ticket, Git/IaC revision, version matrix, backup restore proof, pre/post SQL, job logs, UTC timeline, incident approvals, app SLO evidence and final scorecard. Redact secrets, tokens, connection strings and customer data. Technical acceptance does not by itself establish regulatory certification.

## 10. Hands-on capstone

Use [085 execution lab](../labs/085-postgresql-production-operations-change-management-and-reliability-acceptance-project-lab.md), [preflight SQL](../labs/sql/085-production-change-preflight.sql), [acceptance scorecard](../labs/acceptance/085-production-operations-scorecard.csv), and [change evidence template](../labs/acceptance/085-change-evidence-template.md).

The lab combines an approved **reloadable** setting change, targeted maintenance, application smoke tests, drift reconciliation and a simulated rollback decision. PostgreSQL major upgrades and extension binary updates remain separate gated rehearsals rather than unapproved production-like mutations.

**PASS requires** completed readiness gates, tested change, independent verification, measured application/DB health, recovery evidence and signoff. **NOT VERIFIED** means not executed, missing external evidence or tabletop-only. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/pgupgrade.html
- https://www.postgresql.org/docs/18/sql-alterextension.html
- https://www.postgresql.org/docs/18/config-setting.html
- https://www.postgresql.org/docs/18/routine-vacuuming.html
- https://www.postgresql.org/docs/18/monitoring-stats.html

**Next:** Chapter 086 — PostgreSQL Capacity Forecasting, Cost Optimization and FinOps.
