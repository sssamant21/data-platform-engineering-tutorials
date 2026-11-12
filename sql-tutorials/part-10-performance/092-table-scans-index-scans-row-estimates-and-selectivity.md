# 092 — Table Scans, Index Scans, Row Estimates, and Selectivity

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, DBRE/SRE, analysts

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Read-only SQL lab](../labs/092-scans-estimates-selectivity.sql) · [Previous: 091](091-read-execution-plans-with-explain.md) · Next: 093 — B-tree indexes and common index access patterns (planned)

## 1. Objectives and prerequisites (0–5 minutes)

After this lesson, distinguish sequential, index, index-only, and bitmap heap scans; estimate predicate selectivity; interpret estimated versus actual rows; explain when indexes may lose to sequential scans; and design a safe performance investigation. Complete [091](091-read-execution-plans-with-explain.md) first.

**Scenario:** a synthetic order-events dataset has different status frequencies. An operations report filters by event status. A selective predicate *might* benefit from an index on a large persisted table; a broad predicate may not. We intentionally do **not** create indexes or extrapolate from tiny VALUES rows.

## 2. Concepts and SQL portability (5–15 minutes)

**Selectivity** is the fraction of input rows matching a predicate: matching rows / input rows. If 2 of 10 records match, selectivity is 0.20 (20%). A highly selective filter matches few rows. **Cardinality** means the number of rows (or distinct values, depending on context). An index does not guarantee an index scan.

| PostgreSQL plan operator | What it does | Typical considerations |
|---|---|---|
| Seq Scan | Visits table pages sequentially, applying filters | Often best for small tables or many matching rows |
| Index Scan | Uses an index to locate tuples, typically visits heap | May involve scattered heap I/O; visibility and cache matter |
| Index Only Scan | Can return columns from index | Heap visibility checks may still be required; not always heap-free |
| Bitmap Index Scan + Bitmap Heap Scan | Collects matching tuple locations, then visits heap pages | Useful for moderate selectivity; lossy bitmaps can require rechecks |
| Parallel Seq Scan | Splits table scan among workers | Parallel overhead; depends on settings and workload |

PostgreSQL estimated `rows` reflects planner statistics and assumptions, not observed counts. In `EXPLAIN (ANALYZE, BUFFERS)`, actual rows are measured, but values may be **per loop**. A ratio of estimated to actual rows is useful for diagnosis; it is not proof that stale statistics are the only cause. Correlated columns, skew, expressions, parameter values and missing extended statistics can all affect estimates.

**Portable SQL:** `SELECT`, `WHERE`, `COUNT(*)`, `GROUP BY`. **PostgreSQL-specific:** plan operator names, `EXPLAIN (FORMAT TEXT)`, `SET LOCAL`, `pg_stats`, `CREATE STATISTICS`. MySQL, SQL Server, Snowflake and BigQuery have different plan/profile mechanisms and statistics models.

## 3. Guided examples (15–30 minutes)

### Compute selectivity before discussing access paths

```sql
WITH events(event_id, status) AS (
  VALUES (1,'paid'),(2,'paid'),(3,'paid'),(4,'paid'),
         (5,'paid'),(6,'paid'),(7,'paid'),(8,'pending'),
         (9,'failed'),(10,'failed')
)
SELECT status, COUNT(*) AS matching_rows,
       COUNT(*)::numeric / (SELECT COUNT(*) FROM events) AS selectivity
FROM events
GROUP BY status
ORDER BY status;
```

**Expected (calculated, not executed):** failed = 2/10 = 0.20; paid = 7/10 = 0.70; pending = 1/10 = 0.10. The cast to numeric prevents integer division in PostgreSQL.

### Inspect a plan safely

```sql
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT *
FROM (VALUES (1,'paid'),(2,'pending'),(3,'paid')) AS e(event_id,status)
WHERE status = 'pending';
```

Expect a plan over inline values, **not** a real table's index access. Exact operator choices, costs, and row estimates are planner-dependent. To observe actual index-vs-sequential decisions, a separate **approved isolated** benchmark needs realistic persisted tables, representative statistics, known index definitions, comparable settings, and repeated measurements. Never force `enable_seqscan=off` to justify a production index decision; it is only a diagnostic experiment under controlled conditions.

### Interpreting estimate errors

If a plan predicts 100 rows but an approved measured execution returns 10,000, the estimate is 100× too low. Investigate `pg_stats` distributions, skew, correlation, predicates, and statistics freshness. Do not issue `ANALYZE` or change planner parameters in production without an approved change.

## 4. Hands-on lab (30–50 minutes)

**Prerequisites:** isolated PostgreSQL 18 database named `sql_tutorials`; use disposable credentials and [Chapter 003 setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/092-scans-estimates-selectivity.sql
```

The [lab](../labs/092-scans-estimates-selectivity.sql) begins a read-only transaction, checks database/version, sets local timeouts, uses ten synthetic inline rows, prints an estimated plan, checks expected status counts and selectivities with bidirectional `EXCEPT ALL`, and rolls back. It creates **no** tables or indexes.

1. Predict counts and selectivity for `paid`, `pending`, and `failed`.
2. Inspect the `EXPLAIN` output. Why is an index scan not demonstrated?
3. Change the **practice SELECT only** to `WHERE status = 'pending'` and predict one row; do not modify assertion blocks.
4. Explain why 10 synthetic rows cannot establish an index recommendation for 10 million rows.
5. Sketch a controlled benchmark: same SQL and parameters, representative distribution, warmed and cold-cache considerations, concurrency, p50/p95 latency, `BUFFERS`, and a rollback plan.

**Expected results (reasoned, not runtime-observed):**

| Status | Matching rows | Selectivity |
|---|---:|---:|
| failed | 2 | 0.20 |
| paid | 7 | 0.70 |
| pending | 1 | 0.10 |

Total = 10, sum of selectivities = 1.00. The exact `EXPLAIN` text is intentionally not asserted.

## 5. Troubleshooting and safety (50–55 minutes)

| Symptom | Investigation |
|---|---|
| Sequential scan despite an index | Check table size, predicate selectivity, available index keys, cost assumptions, visibility and statistics |
| Estimated and actual rows differ | Confirm comparison accounts for loops; inspect skew, correlations and statistics age |
| Index-only scan still accesses heap | Visibility map may require heap checks; examine Heap Fetches in approved `EXPLAIN ANALYZE` |
| Bitmap plan has rechecks | Lossy bitmap pages or predicate semantics can require recheck |
| Performance differs across runs | Check cache state, concurrency, parameterization, I/O, and plan changes |
| Lab guard fails | Confirm isolated database name and PostgreSQL major version; do not weaken safeguards |

**Production guardrails:** `EXPLAIN ANALYZE` executes statements, potentially generating expensive load or modifying data. This lab uses plain `EXPLAIN` only. Avoid `CREATE INDEX`, `ANALYZE`, session-wide planner changes, and destructive operations on production. Indexes have storage and write-amplification costs. Obtain change approval, baseline metrics, representative load, and rollback before tuning. Mask sensitive SQL literals and schema identifiers in shared plans.

## 6. Review questions and answers (55–60 minutes)

1. **What is selectivity?** Fraction of rows matching a predicate.
2. **Is a sequential scan necessarily slow?** No; for small tables or broad predicates it may be optimal.
3. **Does an index-only scan guarantee zero heap reads?** No; visibility checks can fetch heap pages.
4. **Does `EXPLAIN` report measured row counts?** No; plain EXPLAIN reports estimates.
5. **What can cause estimate errors besides stale statistics?** Skew, correlated columns, expressions, parameterization and model assumptions.
6. **Why not benchmark on ten VALUES rows?** They lack persisted table storage, indexes, representative distributions and scale.

## References and next step

- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Planner statistics](https://www.postgresql.org/docs/18/planner-stats.html)
- [PostgreSQL 18 — Index-only scans](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Next:** Chapter 093 — B-tree indexes and common index access patterns.

**Validation:** Authored with targeted manual/static reasoning. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime validation with retained evidence are pending.
