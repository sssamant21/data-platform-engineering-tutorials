# 096 — Optimizer Statistics and PostgreSQL Maintenance Basics

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, analysts, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only SQL lab](../labs/096-optimizer-statistics-maintenance.sql) · [Previous: 095](095-partial-expression-and-covering-indexes.md) · Next: 097 — Make predicates index-friendly and rewrite expensive SQL (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

After this lesson you should be able to (1) explain how cardinality estimates affect plan selection, (2) interpret PostgreSQL table and column statistics, (3) distinguish VACUUM, ANALYZE, and autovacuum, (4) diagnose stale or misleading estimates without guessing, and (5) propose an approved maintenance response with rollback and monitoring. Prerequisites: [091 — EXPLAIN](091-read-execution-plans-with-explain.md), [092 — selectivity](092-table-scans-index-scans-row-estimates-and-selectivity.md), and [095 — specialized indexes](095-partial-expression-and-covering-indexes.md).

**Scenario:** A fictional ingestion pipeline loads a large batch of orders. The application reports a suddenly slower dashboard. DBRE must distinguish changed data distribution, missing statistics, expensive physical I/O, and a genuinely unsuitable index before taking action.

## 2. Concepts: estimates are not measurements (5–15 minutes)

The PostgreSQL planner estimates input rows, filter selectivity, join cardinality, and operation costs. It may choose sequential scans, index access, hash joins, nested loops, or sorting based on those estimates. A large error can propagate into expensive join choices. **Estimated plan costs are not milliseconds.** Even a correct estimate does not guarantee a fast query: cache state, I/O, locks, concurrency, and row width matter.

PostgreSQL's `ANALYZE` collects sampled statistics for planner use. `pg_stats` exposes accessible column statistics such as `null_frac`, `n_distinct`, `most_common_vals`, `most_common_freqs`, `histogram_bounds`, and `correlation`; some fields are NULL when not applicable. A negative `n_distinct` is a fraction of table row count (for example, -1 suggests nearly unique values), not a negative count. Samples and histograms are approximate. `pg_class.reltuples` and `relpages` are estimates, not exact live counts.

**Portable SQL:** `COUNT(*)`, `GROUP BY`, `WHERE`, and `EXPLAIN` as a general concept (syntax varies). **PostgreSQL-specific:** `pg_stats`, `pg_stat_all_tables`, `pg_class`, `ANALYZE` syntax, autovacuum thresholds, visibility map, extended statistics, `EXPLAIN (ANALYZE, BUFFERS)`. Never assume that PostgreSQL maintenance commands transfer unchanged to Snowflake, SQL Server, MySQL, or BigQuery.

### Why one-column statistics may be insufficient

Consider synthetic orders where `tenant_id=10` and `status='paid'` are correlated. Multiplying independent selectivities may be wrong. PostgreSQL extended statistics (`CREATE STATISTICS ... (dependencies, ndistinct, mcv)`) can help estimate certain correlated filters and group cardinalities, but do not fix every join-estimation problem. Their creation and collection require approval; no statistics objects are created in this lab.

### VACUUM versus ANALYZE

| Operation | Main purpose | Operational considerations |
|---|---|---|
| `ANALYZE` | Refresh sampled planner statistics | Consumes CPU/I/O; changes future plan choices; is not read-only |
| `VACUUM` | Reclaim dead tuple space for reuse, maintain visibility/freeze state | Ordinary VACUUM usually does not return table space to OS; consumes resources |
| Autovacuum | Background VACUUM and ANALYZE based on activity/thresholds, plus anti-wraparound safeguards | Can lag under heavy writes; monitor workers, dead tuples, age, and configuration |
| `VACUUM FULL` | Rewrite table to compact it | Requires an ACCESS EXCLUSIVE lock and extra disk; never an incident default |

PostgreSQL autovacuum generally triggers vacuum when changed/dead-tuple counts exceed a base threshold plus a scale-factor term, with additional insert-related and freeze rules. Automatic analyze uses modification counts and its own threshold/scale factor. Effective settings can be per-table; exact behavior depends on version and configuration. **Never disable anti-wraparound vacuum to quiet an alert.** A routine `VACUUM` is not equivalent to `VACUUM FULL`.

## 3. Guided examples (15–30 minutes)

### A. Synthetic selectivity and correlation

```sql
WITH orders(order_id, tenant_id, status) AS (
 VALUES (1,10,'paid'),(2,10,'paid'),(3,10,'paid'),
        (4,10,'pending'),(5,20,'pending'),(6,20,'pending'),
        (7,20,'pending'),(8,20,'paid')
)
SELECT COUNT(*) AS total_rows,
       COUNT(*) FILTER (WHERE tenant_id = 10) AS tenant_10,
       COUNT(*) FILTER (WHERE status = 'paid') AS paid,
       COUNT(*) FILTER (WHERE tenant_id = 10 AND status = 'paid') AS tenant_10_paid
FROM orders;
```

**Expected (reasoned):** 8 total, 4 tenant 10, 4 paid, 3 tenant-10 paid. Independent-selectivity arithmetic predicts `8 * (4/8) * (4/8) = 2`, while the actual synthetic intersection is **3**. This is a teaching example, not evidence of PostgreSQL's actual plan estimate.

### B. Inspect existing statistics safely (catalog read only)

```sql
-- PostgreSQL-specific; run only in an authorized isolated database.
SELECT schemaname, tablename, attname, null_frac, n_distinct
FROM pg_catalog.pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname
LIMIT 20;

SELECT schemaname, relname, n_live_tup, n_dead_tup,
       last_analyze, last_autoanalyze, last_autovacuum
FROM pg_catalog.pg_stat_all_tables
WHERE schemaname = 'public'
ORDER BY relname
LIMIT 20;
```

The catalog queries may return **zero rows** in a fresh lab database. Statistics counters are estimates and may lag; a NULL timestamp is not by itself proof that maintenance has never occurred. Permissions affect visibility.

### C. Interpret plan and maintenance evidence

```sql
EXPLAIN (COSTS ON)
SELECT order_id
FROM (VALUES (1,10,'paid'),(2,10,'paid'),(3,20,'pending'))
 AS o(order_id,tenant_id,status)
WHERE tenant_id = 10 AND status = 'paid';
```

This displays **estimated** operations on inline rows. It cannot demonstrate the impact of refreshing table statistics: the inline `VALUES` relation has no physical table statistics. For a real diagnosis compare before/after row estimates against actual row counts and timings **only in an approved disposable benchmark**. `EXPLAIN ANALYZE` executes its statement, including writes if supplied a DML statement; never run it blindly in production.

**Documentation-only, not part of the executable lab:**

```sql
-- Requires change approval and isolated representative tables:
-- ANALYZE public.orders;
-- VACUUM (ANALYZE) public.orders;
-- CREATE STATISTICS orders_tenant_status_stats (mcv, dependencies)
--   ON tenant_id, status FROM public.orders;
-- ANALYZE public.orders;
```

Collect baseline and post-change `EXPLAIN (ANALYZE, BUFFERS)` results only on an isolated, representative **SELECT** workload with bounded resources. Record PostgreSQL version, row counts, data skew, indexes, settings, concurrent workload, cache state, planning/execution time, buffers, and estimate-versus-actual ratios. Avoid claiming improvement from a single timing sample.

## 4. Hands-on lab (30–50 minutes)

Follow [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Connect to a disposable PostgreSQL **18** database named `sql_tutorials`, never production:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/096-optimizer-statistics-maintenance.sql
```

The [read-only lab](../labs/096-optimizer-statistics-maintenance.sql) guards database name and major version, uses transaction-local timeouts, computes actual synthetic selectivity, demonstrates a plain estimated `EXPLAIN`, reads existing catalog counters, checks exact results with bidirectional `EXCEPT ALL`, and ends with `ROLLBACK`. It does **not** create tables, update statistics, run VACUUM, or modify data.

1. Predict the marginal and joint counts for tenant 10 and paid orders.
2. Run the SQL file; compare its output with the expected values below.
3. Explain why multiplying marginal probabilities yields 2, not the observed 3.
4. Inspect `pg_stats` and `pg_stat_all_tables` output. Zero rows are acceptable in an empty lab.
5. Write an **unexecuted** incident plan: identify affected query IDs, check estimated versus actual rows in an approved replica/benchmark, review `last_autoanalyze`, data changes and statistics target, compare index choices, and request change approval before targeted ANALYZE or statistics changes.

| Check | Expected (static calculation, not runtime evidence) |
|---|---|
| Total synthetic orders | 8 |
| Tenant 10 | 4 (50%) |
| Paid | 4 (50%) |
| Tenant 10 and paid | 3 (37.5%) |
| Independent estimate for intersection | 2 |
| Absolute difference | 1 |
| Rows for tenant 20 and pending | 3 |
| Catalog output | Environment-dependent; may be empty |

## 5. Troubleshooting and safety (50–55 minutes)

| Symptom | Investigation before remediation |
|---|---|
| Estimated rows far below actual | Stale statistics, skew, correlated columns, expressions, parameter-specific plans |
| Statistics look current but plan is poor | Histogram sampling, `default_statistics_target`, extended statistics, join shape, cost settings |
| Autovacuum not keeping up | Worker limits, long transactions, table-specific thresholds, write volume, lock conflicts, I/O pressure |
| Table remains large after ordinary VACUUM | Space reusable internally; distinguish bloat from OS-level reclamation |
| `last_autoanalyze` NULL | New/unused table, reset stats, visibility/permissions; corroborate with other evidence |
| Maintenance creates latency | Monitor I/O, CPU, locks, WAL, replicas, and scheduling; avoid aggressive parallel jobs |

**Guardrails:** No production credentials or real customer data. Never issue `VACUUM FULL`, `REINDEX`, `ANALYZE`, or `ALTER TABLE ... SET STATISTICS` as an unapproved reaction to a slow query. Establish owner, maintenance window, disk/WAL headroom, replication impact, abort criteria, monitoring, and a rollback/forward-fix plan. Statistics changes can alter plans; there is no universal instant rollback for a changed plan. Use a representative isolated environment for experiments and record evidence. Do not disable autovacuum or freeze protections.

## 6. Review questions with answers (55–60 minutes)

1. **Does `ANALYZE` execute the application query?** No. It samples table data to refresh planner statistics; the planner uses those estimates when planning subsequent queries.
2. **Are `reltuples` and `n_live_tup` exact counts?** No, they are estimates.
3. **Why can correlated columns mislead the planner?** Independent selectivity assumptions can under- or overestimate the intersection.
4. **Does ordinary VACUUM usually shrink the table file?** No; it primarily makes dead space reusable and maintains visibility/freeze state.
5. **Is `VACUUM FULL` safe during an incident by default?** No; it rewrites the table, needs extra space and a strong lock.
6. **What proves a statistics fix helped?** Reproducible before/after representative workload evidence: row estimates versus actuals, plans, buffers, latency distribution, and resource overhead.

**Next:** Chapter 097 — Make Predicates Index-Friendly and Rewrite Expensive SQL.

## References

- [PostgreSQL 18 — Planner Statistics](https://www.postgresql.org/docs/18/planner-stats.html)
- [PostgreSQL 18 — Statistics Used by the Planner](https://www.postgresql.org/docs/18/planner-stats-details.html)
- [PostgreSQL 18 — Routine Vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [PostgreSQL 18 — ANALYZE](https://www.postgresql.org/docs/18/sql-analyze.html)
- [PostgreSQL 18 — Monitoring Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Validation state:** Authored for publication; expected results reasoned manually and targeted static safety checks intended. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime execution remain pending until independently demonstrated.
