# 064 — Correlated Subqueries and Performance Tradeoffs

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBREs and SREs.

**Prerequisites:** [063 — EXISTS versus IN](063-exists-versus-in-and-null-sensitive-behavior.md). **Next:** 065 — Common table expressions (WITH).

> **Safety:** Use fictional data only. Inspect the [PostgreSQL 18 read-only lab](../labs/064-correlated-subqueries-performance.sql) before running against an independently verified, disposable PostgreSQL 18 instance. Read-only queries still consume resources. The database/version checks in the lab do **not** establish that a server is isolated.

## 1. Objectives and 60-minute agenda (5 minutes)

By the end you can (1) identify an outer reference in a correlated subquery, (2) calculate per-group comparisons, (3) distinguish correlated scalar subqueries, EXISTS and NOT EXISTS, (4) rewrite with joins/aggregates while preserving cardinality, and (5) compare execution plans without assuming a particular optimizer strategy.

| Activity | Minutes |
|---|---:|
| Objectives, scenario and safety | 5 |
| Syntax, semantics and portability | 10 |
| Worked examples | 15 |
| Hands-on exercises | 20 |
| Validation, performance and troubleshooting | 5 |
| Review with answers | 5 |

**Scenario:** Six synthetic ingestion batches across three source systems. An alert stream can contain multiple alerts per batch.

| batch_id | source | processed |
|---:|---|---:|
| 1 | api | 100 |
| 2 | api | 40 |
| 3 | api | 60 |
| 4 | file | 30 |
| 5 | file | 70 |
| 6 | queue | 20 |

Alert pairs (alert_id, batch_id): (101,1), (102,1), (103,4), (104,6). **Expected:** 6 batches, 320 processed records, 4 alerts, 3 alerted batches, and 3 unalerted batches. Source averages: api 200/3, file 50, queue 20.

## 2. Concepts and portability (10 minutes)

A **correlated subquery** refers to a column from an enclosing query, such as `b.source` below. Conceptually it evaluates relative to each outer row; **do not assume** the database physically executes it once per row. PostgreSQL may decorrelate an `EXISTS` predicate into a semi-join, but some correlated scalar expressions can produce repeated `SubPlan` execution.

A scalar subquery must return **at most one row**. Zero rows yields NULL; more than one row is an error. Aggregates without `GROUP BY` return one row even for an empty input (`AVG` then returns NULL). `EXISTS` tests for any row and does not multiply the outer result. `NOT EXISTS` implements absence checks without the nullable-lookup trap of `NOT IN`.

**Portable SQL:** `SELECT`, correlated `WHERE` subqueries, `EXISTS`, `NOT EXISTS`, `AVG`, `GROUP BY`, `LEFT JOIN`, and `COALESCE` are broadly standard. **PostgreSQL-specific lab syntax:** `VALUES` CTE fixtures, `::numeric`, `BEGIN READ ONLY`, `SET LOCAL`, `EXPLAIN (FORMAT TEXT)`, `array_agg`, and session-setting guards. Other engines vary in plan commands, CTE materialization, and execution strategies.

## 3. Guided examples (15 minutes)

### A. Compare each batch with its own source average

```sql
WITH batches(batch_id, source, processed) AS (
  VALUES (1,'api',100),(2,'api',40),(3,'api',60),
         (4,'file',30),(5,'file',70),(6,'queue',20)
)
SELECT b.batch_id, b.source, b.processed
FROM batches AS b
WHERE b.processed > (
  SELECT AVG(x.processed) FROM batches AS x
  WHERE x.source = b.source
)
ORDER BY b.batch_id;
```

**Expected IDs:** 1 and 5. The queue batch equals its own average, so it is not above average. Notice that the inner `x.source = b.source` is the correlation.

### B. Correlated EXISTS and NOT EXISTS

```sql
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(alert_id,batch_id) AS (VALUES (101,1),(102,1),(103,4),(104,6))
SELECT b.batch_id
FROM batches AS b
WHERE EXISTS (SELECT 1 FROM alerts AS a WHERE a.batch_id=b.batch_id)
ORDER BY b.batch_id;
```

**Expected:** 1, 4, 6. Change `EXISTS` to `NOT EXISTS` to get 2, 3, 5. Two alerts for batch 1 still produce only one outer batch.

### C. A set-based alternative

```sql
WITH batches(batch_id,source,processed) AS (
 VALUES (1,'api',100),(2,'api',40),(3,'api',60),
        (4,'file',30),(5,'file',70),(6,'queue',20)
), source_avg AS (
 SELECT source, AVG(processed) AS avg_processed
 FROM batches GROUP BY source
)
SELECT b.batch_id, b.source, b.processed
FROM batches AS b
JOIN source_avg AS s ON s.source=b.source
WHERE b.processed > s.avg_processed
ORDER BY b.batch_id;
```

**Expected:** 1 and 5 again. For nullable source keys, ordinary equality excludes NULL sources in both forms; specify a policy before using NULL-safe matching. A direct join to raw alerts, by contrast, can duplicate batch 1. Pre-aggregate alerts to one row per batch or use `EXISTS` when you only need membership.

### D. Scalar count per batch

```sql
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(alert_id,batch_id) AS (VALUES (101,1),(102,1),(103,4),(104,6))
SELECT b.batch_id,
       (SELECT COUNT(*) FROM alerts a WHERE a.batch_id=b.batch_id) AS alert_count
FROM batches b ORDER BY b.batch_id;
```

**Expected counts:** 2, 0, 0, 1, 0, 1. This pattern is convenient but may be costly on a large outer relation; compare it with a pre-aggregated `LEFT JOIN` using `COALESCE`.

## 4. Hands-on lab (20 minutes)

1. Independently confirm an isolated PostgreSQL **18** instance, database `sql_tutorials`, host and port; never use production credentials.
2. Inspect [lab 064](../labs/064-correlated-subqueries-performance.sql). From the repository root run, substituting the independently verified disposable endpoint:

   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/064-correlated-subqueries-performance.sql
   ```

3. Verify above-average IDs **1,5**, alerted IDs **1,4,6**, unalerted IDs **2,3,5**, per-batch alert counts **2,0,0,1,0,1**, and all assertion flags `t`.
4. On a **local copy only**, change batch 2 from 40 to 90. Predict api average 250/3 and above-average IDs **1,2,5**. Then remove alert 102: alerted IDs remain **1,4,6**, but batch 1's count drops to 1.
5. Compare the two above-average query shapes with `EXPLAIN` on the tiny fixture. Explain why a six-row plan is **not** evidence that one form is faster in production. For meaningful benchmarking use representative synthetic cardinalities, statistics and indexes on a disposable instance, record `EXPLAIN (ANALYZE, BUFFERS)` only there, and compare results before timings.

**Runtime acceptance evidence:** record lab commit SHA, isolated container ID, `SELECT version()`, redacted connection command, full `psql` output, assertion values, exit code, and transaction rollback. No such execution is claimed here.

## 5. Validation and troubleshooting (5 minutes)

| Symptom | Cause | Safe response |
|---|---|---|
| Scalar subquery returns multiple rows | Inner query not guaranteed scalar | Aggregate or constrain by a documented unique key |
| Unexpected NULL comparison | Empty subquery/NULL measurement | Check missing-data policy; `AVG` ignores NULL |
| Duplicated batch totals | Raw one-to-many join | Use EXISTS or pre-aggregate to intended grain |
| Correlated query slow | Repeated subplan work, large outer input, missing access path | Inspect actual plan in sandbox; compare a grouped rewrite |
| Plan differs between runs | Data size, stats, parameterization, planner choices | Record environment, indexes, row counts, statistics |
| Lab guard fails | Wrong version/database or endpoint | Stop; do not bypass guards or redirect to production |

An index on a correlated lookup key (for example, `alerts(batch_id)`) can help on suitable data volumes; it is not automatically beneficial. An `EXPLAIN` plan alone does not prove measured speed. `EXPLAIN ANALYZE` executes its query, so only use it on approved isolated fixtures.

## 6. Review questions and answers (5 minutes)

1. **What makes a subquery correlated?** It references an enclosing query's column.
2. **Does correlated mean executed once per row?** Not necessarily; the optimizer can rewrite it.
3. **Which batches exceed their source average?** 1 and 5.
4. **Why does EXISTS not duplicate batch 1?** It tests presence, not the number of matching alerts.
5. **How many alerts belong to batch 1?** Two.
6. **What if a scalar subquery returns two rows?** SQL raises a cardinality error.
7. **Why can a grouped JOIN be preferable?** It may compute shared aggregates once, but requires matching grain and semantics.
8. **What validates performance?** Comparable, representative isolated execution with recorded plans, timings, row counts and correctness checks.

## References and validation state

- [PostgreSQL 18 — Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**State:** Authored; manually reasoned expected results and targeted static inspection. Independent editorial review, comprehensive static QA, and **actual isolated PostgreSQL 18 runtime execution pending**.
