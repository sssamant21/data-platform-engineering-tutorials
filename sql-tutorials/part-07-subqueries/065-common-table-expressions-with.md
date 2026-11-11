# 065 — Common Table Expressions (WITH)

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBREs and SREs.

**Prerequisite:** [064 — Correlated subqueries](064-correlated-subqueries-and-performance-tradeoffs.md). **Next:** 066 — Recursive CTEs and hierarchical queries.

> **Safety:** All examples use fictional ingestion batches embedded in SQL. Run the [read-only PostgreSQL 18 lab](../labs/065-common-table-expressions-with.sql) only after independently confirming a disposable PostgreSQL 18 instance. Database-name/version guards do not prove isolation. Never use production credentials.

## 1. Outcomes and schedule (5 minutes)

After this chapter you can explain a nonrecursive CTE, write multiple named CTEs, separate filtering from aggregation, detect accidental fan-out, compare a CTE with a derived table, and identify PostgreSQL-specific materialization controls.

| Activity | Minutes |
|---|---:|
| Objectives, fixture and safety | 5 |
| Concepts, scope and portability | 10 |
| Guided examples | 15 |
| Hands-on exercises | 20 |
| Troubleshooting and acceptance | 5 |
| Review questions and answers | 5 |

**Scenario:** Six synthetic ingestion batches. Each has accepted and rejected counts; two source systems report to a daily operational dashboard.

| batch_id | source | accepted | rejected |
|---:|---|---:|---:|
| 1 | api | 80 | 20 |
| 2 | api | 40 | 10 |
| 3 | file | 60 | 0 |
| 4 | file | 30 | 10 |
| 5 | api | 20 | 0 |
| 6 | file | 10 | 20 |

Expected: **240 accepted**, **60 rejected**, **300 processed**, **80.00% weighted acceptance**. API processed 170; file processed 130.

## 2. Concepts and portability (10 minutes)

A **common table expression (CTE)** is a named query result declared with `WITH` and referenced within one SQL statement. It is not a permanent table or reusable view. CTEs can make multi-stage SQL easier to review: define a fixture, calculate batch totals, then aggregate by source. A nonrecursive CTE may reference earlier CTEs in the same `WITH` list; do not assume later CTEs are visible to earlier ones. Use descriptive names and explicit column aliases.

**Portable core:** `WITH name AS (SELECT ...)`, multiple CTEs separated by commas, `JOIN`, `GROUP BY`, `CASE`, `SUM`, and `NULLIF` are standard patterns supported by major engines. Exact support for data-changing CTEs, recursive syntax, materialization, and optimizer transformations varies. This chapter uses **read-only, nonrecursive** CTEs. PostgreSQL 18 supports `MATERIALIZED` and `NOT MATERIALIZED` as optimizer controls; these are **PostgreSQL-specific**, not universal SQL. PostgreSQL can inline eligible side-effect-free CTEs, often when referenced once; a CTE is not necessarily an optimization fence. A multiply referenced CTE may be materialized by default. Avoid assuming either syntax forces a faster plan.

A CTE does not automatically prevent duplicate rows or make a query efficient. Every stage must have a documented **grain** (one row per batch, one per source, etc.). `NULLIF(denominator,0)` protects division by zero; choose whether a missing ratio should be NULL or a documented default.

## 3. Guided examples (15 minutes)

### A. Single CTE: calculate processed records

```sql
WITH batches(batch_id, source, accepted, rejected) AS (
  VALUES (1,'api',80,20),(2,'api',40,10),(3,'file',60,0),
         (4,'file',30,10),(5,'api',20,0),(6,'file',10,20)
)
SELECT batch_id, source, accepted + rejected AS processed
FROM batches ORDER BY batch_id;
```

**Expected processed by batch:** 100, 50, 60, 40, 20, 30.

### B. Multiple CTEs: separate stages and reconcile

```sql
WITH batches(batch_id, source, accepted, rejected) AS (
  VALUES (1,'api',80,20),(2,'api',40,10),(3,'file',60,0),
         (4,'file',30,10),(5,'api',20,0),(6,'file',10,20)
), per_batch AS (
  SELECT batch_id, source, accepted, rejected,
         accepted + rejected AS processed
  FROM batches
), per_source AS (
  SELECT source, COUNT(*) AS batch_count,
         SUM(accepted) AS accepted,
         SUM(rejected) AS rejected,
         SUM(processed) AS processed
  FROM per_batch GROUP BY source
)
SELECT source, batch_count, accepted, rejected, processed,
       ROUND(100.0 * accepted / NULLIF(processed,0), 2) AS acceptance_pct
FROM per_source ORDER BY source;
```

| source | batch_count | accepted | rejected | processed | acceptance_pct |
|---|---:|---:|---:|---:|---:|
| api | 3 | 140 | 30 | 170 | 82.35 |
| file | 3 | 100 | 30 | 130 | 76.92 |

The weighted overall acceptance is `240 / 300 = 80%`. Averaging the two displayed percentages instead gives about 79.64%, which is **not** the weighted rate.

### C. CTE versus derived table

```sql
SELECT source, SUM(processed) AS processed
FROM (
  SELECT source, accepted + rejected AS processed
  FROM (VALUES ('api',80,20),('file',60,0))
       AS b(source,accepted,rejected)
) AS per_batch
GROUP BY source ORDER BY source;
```

**Expected:** api 100; file 60. A derived table can express the same logical transformation. Choose CTEs for clarity, not presumed speed.

### D. PostgreSQL-specific optimizer discussion

```sql
-- PostgreSQL 18 only; inspect EXPLAIN, do not assume a speedup.
WITH per_batch AS NOT MATERIALIZED (
  SELECT 1 AS batch_id, 80 AS accepted
)
SELECT SUM(accepted) FROM per_batch;
```

**Expected:** 80. On tiny constant fixtures, plan differences are not representative. `EXPLAIN` estimates a plan; `EXPLAIN ANALYZE` actually executes the query and belongs only in an approved isolated benchmark.

## 4. Hands-on exercises (20 minutes)

1. Independently verify the PostgreSQL 18 host, port, disposable database `sql_tutorials`, and least-privilege lab account. Inspect [lab 065](../labs/065-common-table-expressions-with.sql) before execution.
2. From the repository root, run on the independently verified isolated endpoint:

   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/065-common-table-expressions-with.sql
   ```

3. Confirm the six processed counts, the two source summary rows, total processed **300**, and all Boolean checks `t`. The lab fails closed if essential checks differ and ends with `ROLLBACK`.
4. **On a local copy of the fixture only**, change batch 6 rejected from 20 to 0. Predict new totals: accepted 240, rejected 40, processed 280, file processed 110, overall acceptance **85.71%**. Restore the original before accepting the supplied assertions.
5. Add a CTE that filters batches with processed >= 50. Expected IDs: **1, 2, 3**. Compare filtering before versus after aggregation: these answer different questions.
6. Rewrite the source summary as a derived table and compare exact result sets, not just row counts. Optionally inspect `EXPLAIN` for the two forms on the isolated fixture; no performance conclusion is warranted from six rows.

**Evidence required for actual runtime acceptance:** immutable lab commit SHA, disposable container identity, `SELECT version()`, redacted connection details, complete `psql` output, assertion results, exit status, and proof of rollback. Authorship or static reasoning is **not** runtime validation.

## 5. Troubleshooting and safety (5 minutes)

| Symptom | Likely cause | Safe correction |
|---|---|---|
| `relation ... does not exist` | CTE referenced outside its statement | Keep reference within the same statement |
| Ambiguous column | Repeated column names across stages | Qualify columns and give explicit aliases |
| Unexpected duplicate totals | Join multiplies one-to-many rows | Verify grain before joining; pre-aggregate |
| Division by zero | No processed records | Use `NULLIF`; document NULL policy |
| Slower plan after refactor | Changed optimizer choices or repeated work | Compare plans and results on representative isolated data |
| Lab guard failure | Wrong version/database/endpoint | Stop; do not bypass the guard or redirect to production |

A CTE is a readability tool, **not** a security boundary. Read-only queries can still consume CPU, memory and I/O. Never use real customer or patient records for these exercises.

## 6. Review questions with answers (5 minutes)

1. **What does WITH define?** Named query expressions scoped to one SQL statement.
2. **Is a CTE a permanent table?** No.
3. **Can one CTE reference an earlier CTE?** Yes, in a nonrecursive `WITH` list.
4. **How many processed records are in the fixture?** 300.
5. **What is the correct overall acceptance percentage?** 80.00%, weighted by processed count.
6. **Why is averaging source percentages misleading?** Sources have different denominators.
7. **Does a CTE always materialize in PostgreSQL 18?** No; planner behavior depends on query and references.
8. **What must be checked after refactoring?** Result equivalence, grain, NULL behavior, plans, and resource cost.

## References and validation state

- [PostgreSQL 18 — WITH Queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**State:** Authored; expected results manually calculated and targeted static inspection performed. Independent editorial review, comprehensive SQL syntax/link QA, and **actual isolated PostgreSQL 18 runtime execution** remain pending.
