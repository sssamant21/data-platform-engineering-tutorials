# 110 — Lab 11: Operational SQL Incident and Recovery Exercise

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **Duration: 60 minutes** · **Audience:** data engineers, application engineers, DBRE/SRE beginners

**Scope:** Synthetic, read-only incident triage and recovery *decision* exercise. **This is not a real database restore, failover, deadlock, or production incident.** PostgreSQL 18 is the lab target. SQL `WITH`, `VALUES`, `JOIN`, `CASE`, and `GROUP BY` are broadly portable; `FILTER`, `DO`, `current_setting`, `SET LOCAL`, and `EXCEPT ALL` are PostgreSQL-specific or vary by dialect.

## 1. Outcomes and prerequisites (0–5 min)

After this lab, learners can (1) distinguish symptoms from causes, (2) prioritize incidents using evidence, (3) evaluate a proposed recovery against RPO/RTO and sign-off gates, (4) reconcile before/after business records, (5) recommend safe mitigations and escalation, and (6) document evidence and closure criteria.

Review [105 — Locks, blocking, and deadlocks](105-locks-blocking-deadlocks-and-troubleshooting.md), [107 — Data quality and reconciliation](107-data-quality-assertions-and-reconciliation-queries.md), [108 — Backup and recovery](108-backup-recovery-and-restore-validation-concepts.md), and [109 — Slow-query runbooks](109-slow-query-investigation-monitoring-and-incident-runbooks.md).

Use a disposable PostgreSQL **18** database named `sql_tutorials` with a nonproduction account. Lab file: [110-lab-11-operational-sql-incident-recovery.sql](../labs/110-lab-11-operational-sql-incident-recovery.sql).

## 2. Scenario and decision model (5–15 min)

A fictional order-ingestion service reports delayed requests and a planned recovery drill. Evidence includes four synthetic query observations, three synthetic recovery candidates, and source/target order snapshots. An incident commander needs an evidence-based recommendation—not an automatic termination, failover, or restore.

**Signal versus cause:** a high query duration may reflect locking, CPU/I/O contention, bad cardinality estimates, network delay, or workload changes. A lock wait does not prove a deadlock. A backup existing does not prove restorability. **RPO** is maximum acceptable data loss measured against a recovery point; **RTO** is maximum acceptable elapsed restoration time. Both must be approved for the service.

Decision gates for a candidate recovery: `data_loss_min <= rpo_limit_min`, `restore_min <= rto_limit_min`, `checksum_ok`, `app_signoff`, and `reconciled`. A missing approval blocks promotion even when timings pass. The SQL models this logic; it does **not** measure a restore.

## 3. Walkthrough: classify query evidence (15–25 min)

Synthetic query samples:

| Query | Duration ms | Blocked? | Plan concern? | Classification |
|---|---:|---|---|---|
| q01 | 90 | no | no | NORMAL |
| q02 | 820 | yes | no | BLOCKING |
| q03 | 950 | no | yes | PLAN_REVIEW |
| q04 | 710 | yes | yes | BLOCKING |

A simple rule prioritizes blocking over plan review; it is a **triage heuristic**, not a diagnosis. The lab should report **4 samples, 3 slow (>=500 ms), 2 blocked, 1 plan-review**. Do not extrapolate p95 or SLO compliance from four fictional observations.

**Portable pattern:**
```sql
WITH observations(query_id, duration_ms, blocked, plan_concern) AS (
  VALUES ('q01', 90, FALSE, FALSE),
         ('q02', 820, TRUE, FALSE),
         ('q03', 950, FALSE, TRUE),
         ('q04', 710, TRUE, TRUE)
)
SELECT query_id,
       CASE WHEN blocked THEN 'BLOCKING'
            WHEN duration_ms >= 500 AND plan_concern THEN 'PLAN_REVIEW'
            ELSE 'NORMAL' END AS triage
FROM observations
ORDER BY query_id;
```

In a *separately approved* real investigation, PostgreSQL's `pg_stat_activity`, `pg_locks`, `pg_blocking_pids()`, and `EXPLAIN` can provide additional evidence. Those live queries are intentionally **not** executed by this lab.

## 4. Walkthrough: recovery acceptance gates (25–35 min)

| Candidate | Data loss / RPO (min) | Restore / RTO (min) | Checksum | App sign-off | Reconciled | Decision |
|---|---|---|---|---|---|---|
| drill_a | 3 / 5 | 18 / 30 | yes | yes | yes | ACCEPT |
| drill_b | 8 / 5 | 20 / 30 | yes | yes | yes | BLOCK |
| drill_c | 2 / 5 | 24 / 30 | yes | no | yes | BLOCK |

Exactly **one** candidate passes. No candidate is executed. A failed gate requires an owner and remediation, not an override by the SQL exercise.

## 5. Hands-on lab (35–50 min)

1. Confirm you are on a disposable PostgreSQL 18 database `sql_tutorials`; use a nonproduction connection and read the entire SQL file before running it.
2. Execute the [lab SQL](../labs/110-lab-11-operational-sql-incident-recovery.sql) with `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/110-lab-11-operational-sql-incident-recovery.sql` from the repository root, with your already configured *isolated* connection. Never substitute a production DSN.
3. Record the four classifications, recovery decisions, and snapshot reconciliation results. Expected: 4 query samples, 3 slow, 2 blocked, 1 plan review; 1 accepted recovery, 2 blocked; source/target snapshots have 3 rows each and totals 90.00 each, but **one source-only and one target-only row**.
4. Explain why equal totals do **not** prove equal datasets. The modeled incident closure must remain **BLOCKED** because record-level reconciliation fails.
5. Verify the SQL ends with `ROLLBACK`; it uses `BEGIN READ ONLY`, local timeouts, version/database guards, and in-memory `VALUES` only. Assertions raise an exception on unexpected results.

**Expected notices:** `Chapter 110 synthetic assertions passed`. No tables, roles, settings, production data, backups, or real incidents are changed.

**Practice extension:** Explain how an incident decision changes if `drill_a` lacks app sign-off, or if the source-only discrepancy is resolved. Do not alter real recovery configuration. Optional: copy the `VALUES` query into a scratch file and change a fictional flag; distinguish the resulting simulated decision from an observed system outcome.

## 6. Incident runbook, troubleshooting, and validation (50–55 min)

**Observe → contain → diagnose → authorize → execute → verify → document.** Capture UTC timestamps, service impact, error rate, latency distributions, workload mix, connection saturation, lock waits, replication state, backup/restore evidence, and approvals. Prefer safe traffic management and reversible mitigations. Never automatically run `pg_terminate_backend`, change roles, drop objects, force failover, or perform restore from this tutorial.

If the lab rejects the database name or major version, **stop** and create the intended disposable PostgreSQL 18 lab environment; do not bypass guards. If permissions fail, check your nonproduction connection rather than escalating privileges. If an assertion fails, compare source and target `EXCEPT ALL` results and check NULL/duplicate semantics. If `psql` exits after an error, the transaction is aborted and no persistent writes occurred.

**Evidence required for actual runtime validation:** PostgreSQL server version, isolated database identity, exact commit SHA of the SQL, command used, stdout/stderr, exit code, assertion notices, execution date, and reviewer. Publication and calculated expectations alone are not runtime proof. A real restore requires separate staging infrastructure, recorded restore logs, measured RPO/RTO, reconciliation, and independent approvals.

## 7. Review questions with answers (55–60 min)

**Q1. Does a lock wait prove a deadlock?** No; a deadlock requires a cycle of dependencies.

**Q2. Does matching total revenue prove recovery correctness?** No; different records can have equal sums. Compare keys and values with multiset-aware reconciliation.

**Q3. Can an RPO-compliant restore be accepted without application sign-off?** Not under this exercise's acceptance policy.

**Q4. What does this lab validate?** Synthetic decision logic if actually executed; it does not validate a real backup, restore, production incident, or service RTO.

**Q5. Who authorizes an operational recovery?** The service's designated incident/change owners according to the approved runbook; not an automated training query.

## References and next step

- [PostgreSQL 18 — Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 — Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [PostgreSQL 18 — Backup and Restore](https://www.postgresql.org/docs/18/backup.html)
- [PostgreSQL 18 — Continuous Archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)

Next: **111 — OLTP versus OLAP query design**, Part 12. **Validation state:** authored for publication; independent editorial review, comprehensive static SQL/link QA, and isolated PostgreSQL 18 runtime evidence remain pending.
