# 061 — Scalar Subqueries and Derived Tables

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** beginner SQL learners, data engineers, DBRE/SRE.

**Prerequisites:** [051 — aggregate functions](../part-06-aggregation/051-count-sum-avg-min-and-max.md), [052 — aggregation grain](../part-06-aggregation/052-group-by-and-aggregation-grain.md), [060 — monthly KPI lab](../part-06-aggregation/060-lab-06-build-a-monthly-kpi-report.md). **Next:** Chapter 062 — IN, ANY, ALL, and multi-row subqueries (planned).

> **Safety:** All examples use fictional ingestion batches. The [companion read-only PostgreSQL 18 lab](../labs/061-scalar-subqueries-derived-tables.sql) uses inline `VALUES` data and `BEGIN READ ONLY`; do not run against production. Independently confirm the endpoint is a disposable PostgreSQL 18 database before executing. Database names/version checks do not prove isolation.

## 1. Learning outcomes and agenda (5 minutes)

By the end, you can: (1) distinguish scalar subqueries from multi-row subqueries; (2) use a scalar aggregate result in a filter; (3) summarize an inline derived table with an explicit alias; (4) handle empty-set scalar results and NULLs; (5) reason about aggregation grain and duplicate rows; and (6) review subquery performance safely.

| Activity | Time |
|---|---:|
| Outcomes, prerequisites, safety | 5 min |
| Concepts, shapes, portability | 10 min |
| Worked examples and expected results | 15 min |
| Read-only hands-on lab and exercises | 20 min |
| Troubleshooting and operational checks | 5 min |
| Review questions with answers | 5 min |

**Scenario:** Six fictional ingestion batches arrive from three regions. The DBRE/SRE team needs to find batches above the overall batch-size average and regions whose total volume exceeds that average. The input grain is **one batch**; the region summary grain is **one region**.

## 2. Key concepts and SQL portability (10 minutes)

A **subquery** is a `SELECT` nested inside another SQL statement. A **scalar subquery** must return **at most one row and one column**. A single returned value can be used as an expression, including inside a comparison or a `SELECT` list. **Zero rows** produce SQL `NULL`; **more than one row** cause an error in PostgreSQL when used as a scalar expression. A scalar aggregate without `GROUP BY`, such as `SELECT AVG(...)`, returns one row even when the input is empty; the aggregate value is then `NULL` (except `COUNT`, which returns zero).

A **derived table** is a subquery in the `FROM` clause, representing a relation with rows and columns. Give it an explicit alias such as `regional`, and alias its output columns. It can return any number of rows, including zero. A derived table is not necessarily materialized; the optimizer can inline or transform it.

**Portable core:** `SELECT`, `FROM (SELECT ...) AS alias`, `AVG`, `SUM`, `WHERE`, `GROUP BY`, and scalar subquery comparisons are broadly standardized SQL. `WITH` is also widely supported, but belongs to Chapter 065. **PostgreSQL 18-specific lab details:** `BEGIN READ ONLY`, `SET LOCAL`, `current_setting('server_version_num')`, and the `VALUES` fixture cast syntax. SQL Server requires care with subquery aliases and scalar-subquery errors; vendor optimizers and explain-plan formats differ. Avoid relying on implicit casts or unspecified row order.

### Six synthetic ingestion batches

| batch_id | region | processed |
|---:|---|---:|
| 1 | East | 100 |
| 2 | East | 50 |
| 3 | West | 40 |
| 4 | West | 60 |
| 5 | North | 20 |
| 6 | North | 30 |

The total is **300** and the mean batch size is **50.00**.

## 3. Guided examples (15 minutes)

### A. Scalar subquery: compare every batch with one aggregate

```sql
SELECT b.batch_id, b.region, b.processed
FROM (VALUES (1,'East',100),(2,'East',50),(3,'West',40),
             (4,'West',60),(5,'North',20),(6,'North',30))
     AS b(batch_id, region, processed)
WHERE b.processed > (
    SELECT AVG(x.processed)
    FROM (VALUES (100),(50),(40),(60),(20),(30)) AS x(processed)
)
ORDER BY b.batch_id;
```

**Expected rows:** `(1, East, 100)` and `(4, West, 60)`. The threshold is 50, and `>` excludes the batch exactly equal to 50. The repeated literal fixture makes this example self-contained; real queries would normally reference the same source table or a reusable CTE rather than duplicate data definitions.

### B. Derived table: aggregate first, filter second

```sql
SELECT regional.region, regional.total_processed
FROM (
    SELECT b.region, SUM(b.processed) AS total_processed
    FROM (VALUES (1,'East',100),(2,'East',50),(3,'West',40),
                 (4,'West',60),(5,'North',20),(6,'North',30))
         AS b(batch_id, region, processed)
    GROUP BY b.region
) AS regional
WHERE regional.total_processed > 50
ORDER BY regional.total_processed DESC, regional.region;
```

**Expected:** East = 150, West = 100. North = 50 is excluded. The inner query establishes **one row per region**, and the outer query filters these region-level totals. Do not confuse the per-batch threshold with the per-region total.

### C. Scalar subquery in a SELECT list

```sql
SELECT b.batch_id, b.processed,
       (SELECT AVG(x.processed)
        FROM (VALUES (100),(50),(40),(60),(20),(30)) AS x(processed))
         AS overall_avg
FROM (VALUES (1,100),(2,50)) AS b(batch_id, processed)
ORDER BY b.batch_id;
```

**Expected:** two rows with `overall_avg = 50.0000...` (display scale varies by engine). A non-correlated scalar subquery can be evaluated efficiently by the optimizer; never assume its physical execution frequency without examining the plan.

### D. NULL and cardinality traps

```sql
SELECT (SELECT v.n FROM (VALUES (1)) AS v(n) WHERE v.n = 99) AS no_match;
-- One row, no_match = NULL.
```

A scalar subquery returning two rows is **not** an alternative to `IN`; PostgreSQL reports `more than one row returned by a subquery used as an expression`. Do not hide a cardinality bug with arbitrary `LIMIT 1` unless a deterministic business rule and `ORDER BY` justify the selection.

## 4. Hands-on lab (20 minutes)

1. Confirm an independently controlled, disposable PostgreSQL 18 server, database, login, and host/port. Never trust a familiar database name alone.
2. Inspect [061 SQL lab](../labs/061-scalar-subqueries-derived-tables.sql). It is read-only, uses only synthetic `VALUES`, and includes deterministic assertions.
3. Execute from the repository root (substitute **your verified isolated endpoint**):
   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/061-scalar-subqueries-derived-tables.sql
   ```
   Port 5432 is only an example, not proof of isolation. Never place passwords in commands.
4. Confirm the batch filter returns IDs **1 and 4**; the region summary returns **East 150** and **West 100**; the scalar average is **50**; the empty scalar subquery yields **NULL**; and the assertion query reports all checks `true`.
5. Exercises: (A) change `>` to `>=` and predict the batch IDs (**1, 2, 4**); (B) change the regional cutoff to `>= 50` and predict the regions (**East, West, North**); (C) explain why using `AVG` of regional totals would change the metric (**different grain**); (D) explain why a scalar query with multiple matching rows fails (**scalar cardinality violation**); (E) describe how a one-to-many join to error details could inflate processed totals (**fan-out; preaggregate or preserve batch grain**).

**Lab acceptance:** The script must exit with status 0, all Boolean assertions must be true, and the final transaction must roll back. Expected values in source code are **not runtime evidence**. Retain the actual output, exit code, PostgreSQL version, endpoint/container identity, and the exact commit SHA for later runtime certification.

## 5. Troubleshooting and DBRE/SRE guardrails (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| More than one row returned by scalar subquery | Inner query is multi-row | Confirm intended cardinality; aggregate or use an appropriate multi-row predicate |
| No rows when filtering with a scalar result | Empty scalar yields NULL; comparisons are UNKNOWN | Inspect inner query and NULL policy |
| Wrong regional totals | Comparing batch-level and region-level grains | State grain before joining or aggregating |
| Duplicate or inflated totals | Join fan-out | Reconcile source count/sum and preaggregate details |
| Slow subquery | Correlation, large scans, poor estimates | Use `EXPLAIN` in an isolated environment; inspect plans and indexes without changing production |
| Wrong database or server version | Endpoint mismatch | Stop and verify container identity and connection |

**Operational discipline:** Use synthetic inputs; never use real credentials or patient records. Read-only SQL can still consume resources, so set a short statement timeout and test only on a disposable lab. Avoid `EXPLAIN ANALYZE` on production-sized or mutating statements. Distinguish **logical SQL semantics** from physical optimizer behavior.

## 6. Review questions and answers (5 minutes)

1. **What is the maximum number of rows a scalar subquery can return?** At most one; zero returns NULL, multiple rows error in PostgreSQL.
2. **How is a derived table different?** It appears in `FROM` and can contain multiple rows and columns.
3. **Why is `AVG(processed)` a valid scalar query?** An aggregate without grouping returns a single row.
4. **Why did batch 2 not pass the filter?** Its 50 equals the mean; `50 > 50` is false.
5. **Why does North not appear in the region report?** Its total is 50, not greater than 50.
6. **Does a derived table always create a temporary table?** No; optimizer transformations are engine-specific.
7. **What must be retained to claim PostgreSQL 18 validation?** Real execution output, exit status, version, isolation identity, and reproducible code revision.

## References and status

- [PostgreSQL 18 — Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html)
- [PostgreSQL 18 — Table Expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Publication state:** authored; targeted static reasoning only. Independent editorial review, comprehensive automated syntax/link QA, and actual isolated PostgreSQL 18 execution remain **pending** until recorded evidence exists.
