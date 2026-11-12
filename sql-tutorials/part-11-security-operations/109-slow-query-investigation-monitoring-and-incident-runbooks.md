# 109 — Slow-Query Investigation, Monitoring, and Incident Runbooks

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · PostgreSQL 18 baseline · Beginner-friendly

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Lab 109 SQL](../labs/109-slow-query-monitoring-incident-runbook.sql) · [Previous: 108](108-backup-recovery-and-restore-validation-concepts.md) · Next: 110 — Lab 11: operational SQL incident and recovery exercise (planned)

## 1. Learning outcomes and incident scenario (0–5 minutes)

After this lesson you can distinguish query latency from system saturation, capture evidence safely, interpret PostgreSQL monitoring views, classify blocking versus expensive plans, create an incident timeline, and propose reversible remediation with verification. Prerequisites: [EXPLAIN (091)](../part-10-performance/091-read-execution-plans-with-explain.md), [locks and blocking (105)](105-locks-blocking-deadlocks-and-troubleshooting.md), [recovery concepts (108)](108-backup-recovery-and-restore-validation-concepts.md).

**Scenario:** A fictional order-search API's p95 latency increases from 150 ms to 900 ms. Three query samples exceed 500 ms. Is the cause necessarily a missing index? No: blocking, resource pressure, plan changes, increased data volume, client/network time, or connection-pool waits may explain the symptom.

## 2. Concepts, telemetry, and safe boundaries (5–15 minutes)

- **Latency:** elapsed time observed at a specific boundary. Application end-to-end latency includes more than database execution.
- **Throughput:** completed requests per second; compare with concurrency and queueing.
- **p50/p95/p99:** percentiles of a *defined population and interval*, not individual-query averages. Track sample count and workload mix.
- **Wait events:** where a PostgreSQL backend is waiting; `wait_event_type='Lock'` suggests a lock wait, but a non-null wait event does not alone prove an incident.
- **Query plan:** estimated access strategy; `EXPLAIN` without `ANALYZE` does not execute the statement. `EXPLAIN ANALYZE` executes it, including writes for DML, so use only with approved isolated data.
- **Statistics:** `pg_stat_activity` shows current activity; `pg_stat_statements` requires an enabled extension and appropriate permissions. Its aggregated statistics are not per-execution traces, and may reset.
- **DBRE/SRE triage:** prioritize safety, impact, evidence, hypothesis, controlled mitigation, and post-change validation.

**Portable SQL:** `SELECT`, `WHERE`, `GROUP BY`, `CASE`, and `ORDER BY` support portable synthetic incident classification. **PostgreSQL-specific:** `pg_stat_activity`, `pg_blocking_pids()`, `pg_locks`, `pg_stat_statements`, `EXPLAIN (FORMAT JSON)`, and `SET LOCAL`. Other engines use different monitoring views and plan facilities.

## 3. Investigation walkthrough (15–30 minutes)

### A. Establish the impact and timeline

Record incident ID, start time (UTC), affected service, error rate, p50/p95/p99, request rate, DB connections, CPU, storage latency, lock waits, deployment/change events, and business impact. Compare a **matching workload window** before and during the incident; never compare dissimilar query mixes as if they were identical.

### B. Inspect current activity (PostgreSQL 18, approved read-only account)

```sql
SELECT pid, state, wait_event_type, wait_event,
       now() - query_start AS query_age,
       pg_blocking_pids(pid) AS blocker_pids
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
ORDER BY query_age DESC NULLS LAST
LIMIT 20;
```

Access to other sessions' details depends on privileges. Query age is not execution duration when the backend is idle; interpret `state` and `query_start` together. Never expose raw SQL text containing personal data or secrets in incident tickets.

### C. Investigate candidate plans safely

```sql
-- Estimated plan only; do not use ANALYZE on an unapproved production statement.
EXPLAIN (FORMAT TEXT)
SELECT order_id, total_amount
FROM (VALUES (1, 20.00::numeric), (2, 45.00::numeric))
     AS sample_orders(order_id, total_amount)
WHERE total_amount >= 30;
```

The plan node types and costs are **environment-dependent**, not a fixed expected result. For real slow queries, compare query fingerprints, bind-value selectivity, row estimates versus actual rows (only in an approved isolated benchmark), indexes, statistics freshness, sort/hash spill, and disk I/O. A missing-index hypothesis is not proof that an index will improve latency.

### D. Classify synthetic samples

| Sample | Duration (ms) | Blocking observed | Index hypothesis | Triage |
|---|---:|---|---|---|
| q01 | 120 | no | no | normal |
| q02 | 780 | yes | no | investigate blocking |
| q03 | 910 | no | yes | review plan/index |
| q04 | 80 | no | no | normal |
| q05 | 650 | yes | no | investigate blocking |
| q06 | 240 | no | no | normal |

**Calculated:** six samples, three at or above 500 ms, two with blocking indicators, one with an index hypothesis. These are fictional values, not measurements. The [SQL lab](../labs/109-slow-query-monitoring-incident-runbook.sql) asserts the exact classifications.

## 4. Hands-on exercise (30–50 minutes)

**Safety prerequisites:** isolated disposable PostgreSQL **18** database named `sql_tutorials`, nonproduction read-only credentials, and `psql`. Never paste production query literals or credentials into a lab.

1. Inspect the [SQL lab](../labs/109-slow-query-monitoring-incident-runbook.sql). Verify `BEGIN READ ONLY`, PostgreSQL 18/database guards, transaction-local timeouts, and `ROLLBACK`.
2. Execute with `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/109-slow-query-monitoring-incident-runbook.sql` from the repository root, using only the isolated lab connection. The guard refuses a different database or major version.
3. Record the six classifications, the count of slow samples, and the blocking/index-hypothesis counts.
4. Explain why a blocking signal should be investigated before proposing an index for q02/q05.
5. Draft a hypothetical incident note: impact, timeline, evidence, root-cause hypothesis (not confirmed), proposed mitigation, approval owner, rollback, and post-change checks.

**Expected output (calculated, not runtime observed):** q01 NORMAL; q02 BLOCKING; q03 PLAN_REVIEW; q04 NORMAL; q05 BLOCKING; q06 NORMAL. Totals: six samples, three slow, two blocking, one plan-review, zero assertion mismatches. The SQL lab models decisions; it does not reproduce an actual slow query, capture production monitoring, or certify a mitigation.

## 5. Incident runbook, troubleshooting, and guardrails (50–55 minutes)

1. **Declare and scope:** identify impacted endpoints, SLO/error-budget impact, incident commander, and UTC timeline.
2. **Preserve evidence:** capture aggregate latency, traffic, saturation, wait categories, deployment markers, and sanitized plan identifiers before any intervention.
3. **Separate hypotheses:** lock waits → identify blockers and transaction age; I/O → inspect disk latency and buffer reads; plan regression → inspect statistics, cardinality, and index options; connection exhaustion → inspect pools and session states.
4. **Approve mitigation:** application retry/backoff or traffic shaping may be safer than immediate database changes. Canceling queries, terminating sessions, changing indexes/configuration, or failover requires named authorization and impact assessment.
5. **Verify:** compare equivalent pre/post workload windows, error rates, p95/p99, throughput, wait time, and resource pressure; monitor for recurrence.
6. **Close:** retain sanitized evidence, corrective actions, owners, rollback decision, and follow-up date.

**Common pitfalls:** `pg_stat_activity` is a point-in-time snapshot; `pg_stat_statements` is optional and cumulative; p95 from six rows is not a reliable production SLO estimate; lock waits are not necessarily deadlocks; an estimated plan is not measured execution; an index can increase write and maintenance cost. Avoid unbounded monitoring queries, raw sensitive SQL logging, and any automatic backend termination.

## 6. Review questions with answers and references (55–60 minutes)

**Q1. Does a slow query always need an index?** No; investigate blocking, resource pressure, query shape, and plan evidence first.

**Q2. Can `EXPLAIN ANALYZE UPDATE ...` modify rows?** Yes; `ANALYZE` executes the statement. Use only in a controlled isolated environment with an explicit transaction/rollback strategy.

**Q3. What does `pg_blocking_pids()` provide?** PostgreSQL backend PIDs blocking a specified process, subject to current lock state.

**Q4. Why record workload and time window with p95?** Percentiles depend on the request population, traffic mix, and observation interval.

**Q5. When can an incident be marked resolved?** After service-level symptoms and relevant DB indicators recover, agreed validation passes, and responsible owners confirm.

**References (PostgreSQL 18 official):**
- [Monitoring database activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Explicit locking and deadlocks](https://www.postgresql.org/docs/18/explicit-locking.html)
- [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)
- [Runtime configuration: client connection defaults](https://www.postgresql.org/docs/18/runtime-config-client.html)

**Publication/validation note:** Authored as a training chapter. Independent editorial review, comprehensive static SQL/link QA, and isolated PostgreSQL 18 runtime execution require separate evidence; do not infer these from publication.
