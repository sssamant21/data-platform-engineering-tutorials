# Chapter 084 — PostgreSQL Maintenance Automation, Scheduling and Operational Runbooks

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design repeatable, safe PostgreSQL maintenance workflows that include scheduling, preflight checks, execution limits, observability, incident response and evidence. Build on [Chapter 083 — Configuration Management](083-postgresql-configuration-management-infrastructure-as-code-and-drift-detection.md), backup/DR and performance chapters.

**Operational invariant:** a scheduled job must be bounded, observable, safe to retry and prevented from running when critical preconditions fail.

## 2. Maintenance catalog and ownership

| Workload | Typical mechanism | Scheduling consideration | Failure concern |
|---|---|---|---|
| Vacuum/analyze | Autovacuum; targeted VACUUM/ANALYZE | Prefer autovacuum; tune from evidence | Bloat, wraparound, IO saturation |
| Index maintenance | REINDEX CONCURRENTLY when supported | Coordinate write load and capacity | Long duration, invalid index, extra disk |
| Partition lifecycle | Create/detach/drop via reviewed scripts | Ahead of ingest, retention approval | Missing future partitions, data loss |
| Backup/restore validation | Backup scheduler and isolated restore | Independent schedule, retention | False-positive backup success |
| Statistics | Autoanalyze; targeted ANALYZE | After bulk loads or distribution changes | Poor query plans |
| Replication/WAL | Slot, lag and archive checks | Continuous checks and escalation | Disk exhaustion, RPO violation |
| Integrity checks | Checksums, logical consistency, application probes | Off-peak/clone where appropriate | Heavy scans and false confidence |
| Configuration/security review | IaC drift, role and certificate inventory | Periodic + change-triggered | Silent drift and expired credentials |

**Do not replace autovacuum with blanket nightly VACUUM jobs.** Autovacuum also protects transaction ID age. Routine `VACUUM FULL` rewrites tables, takes an ACCESS EXCLUSIVE lock and requires substantial disk; do not automate it indiscriminately.

## 3. Scheduling architectures

- **Systemd timer/cron:** simple self-managed hosts; define OS identity, working directory, log delivery and host-failure handling.
- **Kubernetes CronJob:** specify `concurrencyPolicy: Forbid`, `startingDeadlineSeconds`, deadlines, job history, scoped ServiceAccount, resources and secret injection. Forbid is a scheduler policy, not a distributed database-wide mutex.
- **pg_cron:** optional extension, subject to version/provider availability and extension security review. Confirm worker/database configuration and restart requirements.
- **Airflow/Argo/enterprise scheduler:** dependency DAGs, approval gates, retry policy and central observability.
- **Managed PostgreSQL:** prefer provider-supported maintenance/backup operations and respect control-plane constraints.

Avoid placing credentials directly in crontab or command arguments. Use a secrets manager, scoped workload identity or securely permissioned passfile.

## 4. Safe automation contract

Each job must declare:

1. **Identity and scope:** database, cluster, environment, target objects, authorized service role.
2. **Preflight:** cluster role, replica health, disk headroom, lock contention, backups, application SLO, active incidents and maintenance approval.
3. **Idempotency:** a rerun must not duplicate destructive work; use checkpoint/state for multi-step workflows.
4. **Concurrency:** distributed lock or scheduler coordination, plus database-level checks.
5. **Limits:** statement and lock timeouts, job deadline, retry budget, WAL/IO/disk safeguards.
6. **Execution:** dry-run when possible, explicit target lists, no unbounded table loops.
7. **Verification:** before/after metrics and SQL checks, job outcome, data/application correctness.
8. **Escalation:** page owner on critical failure, with rollback or safe stop instructions.

A PostgreSQL advisory lock is **session-scoped** when acquired with `pg_try_advisory_lock`. It is released when the session ends. For external scripts, do not acquire a lock in one short-lived `psql` process and expect it to protect another process. Keep the lock-owning session alive for the protected operation or use a properly designed external distributed lock.

## 5. Safe preflight SQL

Use [084 read-only inspection SQL](../labs/sql/084-maintenance-preflight.sql) to inspect database identity, recovery state, transaction age, autovacuum activity, dead tuples, replication slots, WAL archiving and progress views.

```sql
SELECT pg_is_in_recovery() AS is_standby;
SELECT datname,age(datfrozenxid) AS xid_age
FROM pg_database ORDER BY xid_age DESC;
SELECT schemaname,relname,n_live_tup,n_dead_tup,
 last_autovacuum,last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
```

Statistics are estimates and may lag. Always correlate with disk, I/O, lock waits and the active workload. XID wraparound emergencies take priority over normal maintenance windows.

## 6. Vacuum and statistics runbook

**Default:** rely on autovacuum with monitored thresholds. For a targeted maintenance action:

```sql
-- Example: approved lab table only
VACUUM (ANALYZE, VERBOSE) public.ch084_events;
```

`VACUUM` cannot run inside a transaction block. It can consume IO and generate WAL. For wraparound, inspect `age(datfrozenxid)`, `age(relfrozenxid)`, long transactions and autovacuum blockers; do not simply disable autovacuum or raise freeze thresholds.

## 7. Index maintenance runbook

Check index size, usage, validity and bloat evidence before acting. `REINDEX INDEX CONCURRENTLY` reduces blocking compared with nonconcurrent reindex but can take much longer, require additional disk and wait on transactions; it cannot run in a transaction block. Review version and object restrictions, and handle failed/invalid index artifacts with a tested procedure.

Never schedule blanket reindex without evidence. Plan a pause/abort criterion if disk free space or query latency deteriorates.

## 8. Partition retention and data safety

Create future partitions before the application needs them. Retention jobs must confirm data age, regulatory hold, export/archive completion, partition bounds and downstream consumer state. A `DROP TABLE` or detached partition removal is destructive; require an explicit approved retention policy and separate backup verification.

Use a two-stage workflow: discover and report candidate partitions, then execute only approved changes with a deterministic manifest and checkpoint.

## 9. Failure handling and retries

| Failure | Action | Retry rule |
|---|---|---|
| Lock timeout | Record blockers and exit safely | Retry with jitter in approved window |
| Standby or role change | Stop write maintenance | Re-evaluate primary ownership and fencing |
| Disk pressure | Abort optional heavy work | Do not retry until capacity restored |
| Backup/restore verification failed | Escalate; protect recovery path | Do not delete old backups |
| Job deadline exceeded | Stop or cancel safely; inspect state | Resume only after idempotency check |
| Partial partition operation | Reconcile catalog/state | No blind rerun |
| Monitoring gap | Mark result NOT VERIFIED | Do not mark job successful |

## 10. Observability and SLOs

Capture job ID, cluster, database, target, start/end UTC, owner, Git revision, approval ID, SQLSTATE, retry count, duration, locks, WAL/IO impact and postcheck results. Use structured logs without secrets or sensitive query parameters.

Monitor maintenance duration, success rate, missed schedules, overlapping executions, autovacuum lag, XID age, index validity, WAL generation, disk headroom, backup age and application latency. Alert on **failed verification**, not only nonzero exit status.

## 11. Production rollout

1. Define and version the maintenance policy.
2. Rehearse on disposable representative data.
3. Confirm backup, HA health, change window, escalation and owner.
4. Run read-only preflight and fail closed on unmet gates.
5. Acquire effective job-wide concurrency protection.
6. Execute bounded maintenance with timeouts and checkpoints.
7. Perform independent postchecks and application smoke tests.
8. Record evidence, update dashboard and release lock.
9. If partial failure occurs, stop, preserve state and follow the recovery runbook.

## 12. Lab and acceptance

Use [Chapter 084 lab](../labs/084-postgresql-maintenance-automation-scheduling-and-operational-runbooks-lab.md), [preflight SQL](../labs/sql/084-maintenance-preflight.sql), [maintenance job template](../labs/scripts/084-maintenance-job.ps1), and [acceptance scorecard](../labs/acceptance/084-maintenance-automation-scorecard.csv).

**PASS requires:** verified preflight, bounded execution, real concurrency protection, targeted maintenance, captured postchecks, safe retry/stop behavior, alert evidence and rollback/escalation documentation. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/routine-vacuuming.html
- https://www.postgresql.org/docs/18/sql-vacuum.html
- https://www.postgresql.org/docs/18/sql-reindex.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/explicit-locking.html

**Next:** Chapter 085 — PostgreSQL Production Operations, Change Management and Reliability Acceptance Project.
