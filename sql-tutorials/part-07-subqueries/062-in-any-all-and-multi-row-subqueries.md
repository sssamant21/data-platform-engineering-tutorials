# 062 — IN, ANY, ALL, and Multi-row Subqueries

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBREs and SREs.

**Prerequisites:** [061 — Scalar subqueries and derived tables](061-scalar-subqueries-and-derived-tables.md), [013 — NULL and three-valued logic](../part-02-filtering/013-null-handling-and-sql-three-valued-logic.md), [014 — IN and range predicates](../part-02-filtering/014-in-between-and-range-predicates.md). **Next:** 063 — EXISTS versus IN and NULL-sensitive behavior.

> **Safety:** Synthetic data only. The [PostgreSQL 18 companion lab](../labs/062-in-any-all-multi-row-subqueries.sql) uses inline VALUES in a read-only transaction. Independently verify an isolated, disposable endpoint before running; version and database-name guards do not establish isolation.

## 1. Learning outcomes and 60-minute agenda (5 minutes)

You will distinguish a scalar from a multi-row subquery; use `IN`, `= ANY`, `> ANY`, `> ALL`, and `NOT IN`; predict empty-set and NULL outcomes; choose an appropriate comparison for a business rule; and reconcile operational reporting results.

| Activity | Minutes |
|---|---:|
| Objectives, prerequisites, safety | 5 |
| Concepts and portability | 10 |
| Worked examples | 15 |
| Hands-on lab and practice | 20 |
| Troubleshooting and guardrails | 5 |
| Review with answers | 5 |

**Scenario:** A fictional ingestion platform records six batches. A separate synthetic threshold list represents alert levels. The grain is one batch; never mistake a batch count for a count of alert thresholds.

| batch_id | region | processed |
|---:|---|---:|
| 1 | East | 120 |
| 2 | East | 80 |
| 3 | West | 50 |
| 4 | West | 30 |
| 5 | North | 10 |
| 6 | North | NULL |

Known processed total = **290**; one missing measurement. Alert thresholds are **40, 90**.

## 2. Concepts and portable syntax (10 minutes)

A **multi-row subquery** returns zero or more values. Use it with predicates designed for a set of values, not with scalar `=`. In this chapter the subquery selects **one column**.

- `x IN (subquery)` is equivalent in result truth value to `x = ANY (subquery)` in PostgreSQL; both test whether **at least one** equality comparison is true.
- `x > ANY (subquery)` asks whether **at least one** threshold is lower than x. With thresholds 40 and 90, 50 qualifies.
- `x > ALL (subquery)` asks whether x exceeds **every** threshold. With thresholds 40 and 90, only 120 qualifies.
- `x NOT IN (subquery)` is not a reliable anti-join when the subquery can contain NULL. A non-matching value compared against a set containing NULL generally evaluates to UNKNOWN, so `WHERE` discards it.
- For an **empty subquery**, `ANY` (and `IN`) evaluates FALSE and `ALL` evaluates TRUE, even when the left operand is NULL. For a nonempty set, NULL comparisons can yield UNKNOWN.
- SQL `WHERE` retains only TRUE, not FALSE or UNKNOWN. `NOT (UNKNOWN)` is still UNKNOWN.

**Portability:** `IN`, `ANY`/`SOME`, `ALL`, `NOT IN`, and subqueries are standardized SQL constructs, but actual dialect support and edge cases should be tested. PostgreSQL supports these operators; SQL Server supports comparison with ANY/ALL, while other engines differ. `VALUES` inside `FROM`, `BEGIN READ ONLY`, `SET LOCAL`, and PostgreSQL configuration checks in the companion lab are PostgreSQL-oriented. Never assume SQL array syntax and subquery syntax are interchangeable across vendors.

## 3. Guided examples (15 minutes)

All examples are read-only and self-contained. The sample fixture is repeated to make each example executable independently.

### A. IN — membership in a region selection

```sql
SELECT b.batch_id, b.region
FROM (VALUES (1,'East'),(2,'East'),(3,'West'),
             (4,'West'),(5,'North'),(6,'North')) AS b(batch_id,region)
WHERE b.region IN (
  SELECT r.region
  FROM (VALUES ('East'),('North')) AS r(region)
)
ORDER BY b.batch_id;
```

**Expected IDs:** 1, 2, 5, 6. The subquery returns two rows and one column. Duplicates in the lookup set do not duplicate outer rows.

### B. ANY versus ALL — different threshold policies

```sql
SELECT b.batch_id, b.processed
FROM (VALUES (1,120),(2,80),(3,50),(4,30),(5,10),(6,NULL::integer))
     AS b(batch_id,processed)
WHERE b.processed > ANY (
  SELECT t.limit_value FROM (VALUES (40),(90)) AS t(limit_value)
)
ORDER BY b.batch_id;
```

**Expected IDs:** 1, 2, 3. Change `ANY` to `ALL`: **only ID 1**. In both cases batch 6's NULL does not pass the nonempty threshold comparison.

### C. NOT IN and the NULL trap

```sql
SELECT b.batch_id
FROM (VALUES (1),(2),(3)) AS b(batch_id)
WHERE b.batch_id NOT IN (
  SELECT x.id FROM (VALUES (2),(NULL::integer)) AS x(id)
)
ORDER BY b.batch_id;
```

**Expected:** **zero rows**, not IDs 1 and 3. To safely exclude known IDs when NULL means “unknown,” filter NULL from the subquery:

```sql
SELECT b.batch_id
FROM (VALUES (1),(2),(3)) AS b(batch_id)
WHERE b.batch_id NOT IN (
  SELECT x.id FROM (VALUES (2),(NULL::integer)) AS x(id)
  WHERE x.id IS NOT NULL
)
ORDER BY b.batch_id;
```

**Expected:** IDs **1, 3**. When expressing absence of a matching row, `NOT EXISTS` (Chapter 063) is often clearer, especially with nullable keys.

### D. Empty sets and logical truth

```sql
SELECT
  50 > ANY (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS any_empty,
  50 > ALL (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS all_empty,
  50 IN (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS in_empty;
```

**Expected:** FALSE, TRUE, FALSE. Vacuous truth for `ALL` is intentional SQL semantics; check for empty policy tables if that is not acceptable for your alerting rule.

## 4. Hands-on lab and exercises (20 minutes)

1. Independently confirm the PostgreSQL 18 container/server identity and disposable database `sql_tutorials`. Use no production credentials.
2. Inspect [lab 062](../labs/062-in-any-all-multi-row-subqueries.sql) before execution. It contains no persistent DML or DDL and rolls back.
3. From the repository root, substitute your verified isolated connection:

   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/062-in-any-all-multi-row-subqueries.sql
   ```

4. Check the returned ID lists: `IN` = **1,2,5,6**; `> ANY` = **1,2,3**; `> ALL` = **1**; NULL-bearing `NOT IN` = **none**; NULL-filtered `NOT IN` = **1,3**. All acceptance columns should read `t`.
5. Practice and predict before editing a local copy: (A) replace `> ANY` with `>= ANY` — **IDs 1,2,3**, unchanged because no batch equals 40 or 90; (B) change threshold 90 to 80 and use `> ALL` — **ID 1**; (C) use `>= ALL` with thresholds 40 and 80 — **IDs 1,2**; (D) explain why an empty threshold list makes `> ALL` TRUE for every batch, including the NULL batch; (E) explain why NULLs in an exclusion list can silently suppress rows.

**Acceptance evidence to retain during a future actual run:** SQL commit SHA, psql command with secrets omitted, container identity, server version, exit status, complete output, assertion values, and rollback. Source-code assertions alone are not proof of execution.

## 5. Troubleshooting and operational safeguards (5 minutes)

| Symptom | Cause | Safe investigation |
|---|---|---|
| Scalar subquery error | `=` used against multiple rows | Use `IN` or a justified aggregate; never arbitrary `LIMIT 1` |
| No rows with `NOT IN` | NULL in lookup set | Inspect NULL counts; filter intentionally or use `NOT EXISTS` |
| Unexpected ALL matches | Empty threshold table | Validate threshold-set non-emptiness as a separate data-quality check |
| Wrong alert volume | Confused `ANY` and `ALL` | Translate the policy into “at least one” or “every” before coding |
| Missing batch | NULL measurement | Track unknowns separately; do not silently convert NULL to zero |
| Slow predicate | Large subquery or skew | Check query plan and statistics in isolated testing; avoid unbounded scans in production |

Read-only queries can still create CPU, memory, and I/O pressure. Use local timeouts and explicit endpoint verification. Reconcile counts and known-value sums before treating results as operational alerts.

## 6. Review questions and answers (5 minutes)

1. **Can a multi-row subquery be compared with scalar `=`?** Not safely if it returns multiple rows; use a set predicate.
2. **What does `> ANY` mean?** Greater than at least one value in the subquery.
3. **What does `> ALL` mean?** Greater than every value in the subquery.
4. **How does `IN` compare with `= ANY`?** Equivalent truth-value semantics for a single-column subquery in PostgreSQL.
5. **Why can `NOT IN` return no rows unexpectedly?** NULL in the right-hand set can make nonmatches UNKNOWN.
6. **What happens with an empty set?** ANY/IN FALSE; ALL TRUE.
7. **Why count NULL measurements separately?** A missing value is not zero, and SQL comparisons with it are UNKNOWN for nonempty sets.
8. **What proves runtime validation?** Actual isolated PostgreSQL 18 execution with reproducible logs and identity, not merely authored expected results.

## References and validation status

- [PostgreSQL 18 — Subquery Expressions](https://www.postgresql.org/docs/18/functions-subquery.html)
- [PostgreSQL 18 — Comparison Functions and Operators](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Status:** authored; targeted static reasoning of fixtures and expected results. Independent editorial review, comprehensive automated SQL syntax/link QA, and **actual isolated PostgreSQL 18 runtime validation** remain pending.
