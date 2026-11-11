# 063 — EXISTS versus IN and NULL-sensitive Behavior

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** beginners, data engineers, DBRE/SREs.

**Prerequisites:** [062 — IN, ANY, ALL](062-in-any-all-and-multi-row-subqueries.md), [048 — Semi-joins and anti-joins](../part-05-joins/048-semi-joins-and-anti-joins-using-exists-and-not-exists.md). **Next:** 064 — Correlated subqueries and performance tradeoffs.

> **Safety:** Use only fictional data. The [read-only PostgreSQL 18 lab](../labs/063-exists-versus-in-null-sensitive.sql) uses inline `VALUES`, an explicitly read-only transaction, local timeouts, version/database checks, and `ROLLBACK`. Verify the endpoint is disposable independently: a database name or version check cannot prove isolation.

## 1. Objectives and agenda — 5 minutes

By the end, explain existence predicates, compare `EXISTS` and `IN`, implement NULL-safe anti-membership, handle NULL join keys and duplicates, and validate operational reconciliation.

| Activity | Minutes |
|---|---:|
| Objectives and safety | 5 |
| Concepts and portability | 10 |
| Guided SQL examples | 15 |
| Hands-on practice | 20 |
| Troubleshooting and validation | 5 |
| Review and answers | 5 |

**Scenario:** An ingestion service has six fictional batches. A separate alert table records zero or more alerts per batch; one alert has an unknown batch ID.

| batch_id | source | processed |
|---:|---|---:|
| 1 | api | 100 |
| 2 | file | 50 |
| 3 | api | 70 |
| 4 | file | 20 |
| 5 | api | NULL |
| 6 | file | 40 |

Alerts: `(101,1,'error'), (102,1,'warning'), (103,3,'error'), (104,NULL,'orphan'), (105,6,'warning')`.

Expected: **6 batches**, **5 alerts**, **4 distinct non-NULL alert batch IDs? No: 3** (1, 3, 6), **3 batches with alerts**, **3 without** (2, 4, 5), and **280 known processed records**. The orphan alert is a deliberate data-quality exception.

## 2. Concepts and portability — 10 minutes

- `EXISTS (SELECT ...)` is TRUE if its subquery produces at least one row. The selected expression is not the test: `SELECT 1` communicates intent. `EXISTS (SELECT NULL)` is TRUE because it returns one row.
- `IN (SELECT key ...)` compares a value with a set. With non-NULL, matching keys, it commonly gives the same selected outer rows as a correlated `EXISTS` query. SQL three-valued logic means their Boolean results can differ when NULLs appear.
- `NOT EXISTS` is the preferred anti-membership pattern when nullable lookup keys are possible. `NOT IN` can yield UNKNOWN for every nonmatching key if the lookup contains NULL.
- Duplicates in the inner table do **not** duplicate outer rows with `EXISTS` or `IN`; an ordinary `JOIN` can multiply rows.
- `NULL = NULL` is UNKNOWN, so a conventional correlated equality does not match two NULL keys. Use an explicit business rule if unknown keys should match; PostgreSQL's `IS NOT DISTINCT FROM` is a NULL-safe comparison, but this changes semantics.
- `EXISTS` can be used in `WHERE`, `CASE`, and other Boolean contexts. Do not assume that it always runs faster than `IN`; optimizers can transform both into semi-joins. Inspect real plans and cardinalities before optimizing.

**Portable SQL:** `EXISTS`, `NOT EXISTS`, `IN`, `NOT IN`, correlated subqueries, and `CASE` are standard SQL patterns. **PostgreSQL-specific lab elements:** `VALUES`-derived fixture syntax, `BEGIN READ ONLY`, `SET LOCAL`, `current_setting`, and array-based assertions. SQL Server, MySQL, Snowflake, and BigQuery may require different fixture or transaction syntax.

## 3. Guided examples — 15 minutes

These examples are independent, read-only SQL queries.

### A. EXISTS — batches with at least one alert

```sql
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(alert_id,batch_id) AS (
  VALUES (101,1),(102,1),(103,3),(104,NULL::integer),(105,6)
)
SELECT b.batch_id
FROM batches AS b
WHERE EXISTS (
  SELECT 1 FROM alerts AS a WHERE a.batch_id = b.batch_id
)
ORDER BY b.batch_id;
```

**Expected IDs:** 1, 3, 6. The two alerts for batch 1 do not create two output rows. The `NULL::integer` cast is PostgreSQL syntax; a typed fixture is the portable alternative.

### B. IN — same membership result for known matching IDs

```sql
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT batch_id FROM batches
WHERE batch_id IN (SELECT batch_id FROM alerts)
ORDER BY batch_id;
```

**Expected IDs:** 1, 3, 6. For batch 2, the Boolean `IN` expression is UNKNOWN because there is no match and the lookup contains NULL; `WHERE` discards UNKNOWN. The `EXISTS` expression for batch 2 is FALSE. Their **filtered rows match**, but their raw Boolean values differ.

### C. NOT EXISTS — NULL-safe absence test

```sql
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT b.batch_id FROM batches AS b
WHERE NOT EXISTS (
  SELECT 1 FROM alerts AS a WHERE a.batch_id = b.batch_id
)
ORDER BY b.batch_id;
```

**Expected IDs:** 2, 4, 5. Replacing the predicate with `batch_id NOT IN (SELECT batch_id FROM alerts)` yields **zero rows** because the lookup contains NULL. Filtering NULLs out of the lookup makes `NOT IN` return 2, 4, 5 for these non-NULL outer keys; if the outer key can be NULL, decide its meaning separately.

### D. NULL-safe equality is a different business rule

```sql
SELECT NULL::integer = NULL::integer AS ordinary_equality,
       NULL::integer IS NOT DISTINCT FROM NULL::integer AS null_safe_equality;
```

**Expected:** `ordinary_equality = NULL` (UNKNOWN), `null_safe_equality = TRUE`. Do not turn unknown identifiers into matches without a documented policy.

### E. Reconciling an operational report

```sql
WITH batches(batch_id,processed) AS (
 VALUES (1,100),(2,50),(3,70),(4,20),(5,NULL::integer),(6,40)
), alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT COUNT(*) AS total_batches,
       COUNT(*) FILTER (WHERE EXISTS (
         SELECT 1 FROM alerts AS a WHERE a.batch_id=b.batch_id
       )) AS alerted_batches,
       COUNT(*) FILTER (WHERE NOT EXISTS (
         SELECT 1 FROM alerts AS a WHERE a.batch_id=b.batch_id
       )) AS clean_batches,
       SUM(processed) AS known_processed
FROM batches AS b;
```

**Expected:** 6, 3, 3, 280. `FILTER` is supported by PostgreSQL but not universal; use `SUM(CASE WHEN EXISTS (...) THEN 1 ELSE 0 END)` for a more portable alternative.

## 4. Hands-on lab — 20 minutes

1. Verify an **isolated** PostgreSQL 18 container, database `sql_tutorials`, and non-production credentials. Confirm host, port, and database identity out of band.
2. Inspect [lab 063](../labs/063-exists-versus-in-null-sensitive.sql) before executing.
3. From repository root, substitute your independently verified disposable connection:

   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/063-exists-versus-in-null-sensitive.sql
   ```

4. Check membership IDs **1,3,6** and anti-membership IDs **2,4,5**; the `NOT IN` example returns zero rows. Check **one orphan alert**, **one NULL measurement**, **280 known processed**, and all Boolean checks `t`.
5. Practice on a **local copy**: (A) remove alert 105 — predicted alerted IDs **1,3**, clean **2,4,5,6**; (B) add another alert for batch 1 — `EXISTS` remains **1,3,6**; (C) filter NULL lookup IDs before `NOT IN` — predicted **2,4,5**; (D) explain why `EXISTS (SELECT NULL)` is TRUE; (E) explain why joining alerts and summing batch processed counts double-counts batch 1.

**Acceptance evidence required for a future runtime pass:** SQL commit SHA, isolated container identity, PostgreSQL version, redacted invocation, complete `psql` output, exit status, assertion output, and rollback. An authored assertion is **not** execution evidence.

## 5. Troubleshooting and safeguards — 5 minutes

| Symptom | Likely cause | Safe response |
|---|---|---|
| `NOT IN` returns nothing | NULL in lookup | Inspect `COUNT(*) FILTER (WHERE key IS NULL)`; prefer `NOT EXISTS` |
| More rows after rewriting to JOIN | One-to-many fan-out | Compare grain, count distinct keys, inspect duplicates |
| Unknown batch incorrectly matched | NULL-safe comparison applied indiscriminately | Document key policy; avoid matching unknowns by default |
| Query is slow | Large correlated lookup, skew, or missing index | Benchmark on a replica/sandbox with `EXPLAIN`; review plans, not folklore |
| Totals differ from source | Duplicates or missing measurements | Reconcile distinct batches, orphan alerts, and NULL measurements |

Even SELECT queries can consume substantial I/O and memory. Never run an unbounded lab query against production. This lab has local timeouts and a rollback, but **read-only does not imply zero operational impact**.

## 6. Review questions with answers — 5 minutes

1. **What does EXISTS test?** Whether the subquery returns any row, regardless of projected value.
2. **Why doesn't duplicate alert 102 duplicate batch 1?** EXISTS is a Boolean semi-join-style predicate.
3. **Which batches have alerts?** 1, 3, 6.
4. **Which batches lack alerts?** 2, 4, 5 using NOT EXISTS.
5. **Why does NOT IN return no rows?** The NULL lookup key makes nonmatches UNKNOWN.
6. **Are IN and EXISTS always identical Boolean expressions?** No. With NULL lookup values, a nonmatch can be UNKNOWN for IN but FALSE for EXISTS.
7. **Does NULL = NULL match?** No; it evaluates UNKNOWN.
8. **What evidence supports a runtime-validation claim?** Actual isolated PostgreSQL 18 execution, complete results, and reproducible provenance.

## References and status

- [PostgreSQL 18 — Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html)
- [PostgreSQL 18 — Comparison Functions](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Validation:** Authored; expected outputs manually reasoned and targeted structural inspection performed. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime validation **pending**.
