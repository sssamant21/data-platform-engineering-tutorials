# Chapter 016 — DISTINCT and Duplicate Handling

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 015](015-like-wildcard-matching-and-dialect-specific-ilike.md) · [Next: 017 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **PostgreSQL 18 lab target**
>
> **Status:** Authored/published; targeted static checks only. Independent editorial review, comprehensive syntax verification and isolated PostgreSQL 18 runtime acceptance pending.

## Objectives and agenda (0–5 minutes)

After this chapter, distinguish duplicate rows from duplicate business entities; use `SELECT DISTINCT` for unique projections; count distinct non-NULL values; explain how NULL, ordering and joins affect results; and recognize when deduplication requires an explicit business rule rather than `DISTINCT`.

| Time | Activity |
|---|---|
| 0–5 min | Objectives, prerequisites and safety |
| 5–15 min | DISTINCT, NULL, COUNT and query semantics |
| 15–30 min | Worked synthetic examples |
| 30–50 min | Read-only PostgreSQL lab and practice |
| 50–55 min | Troubleshooting, performance and operational safeguards |
| 55–60 min | Review questions and answers |

**Prerequisites:** [007 SELECT fundamentals](../part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md), [009 data types and NULL](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), [013 three-valued logic](013-null-handling-and-sql-three-valued-logic.md), and [003 isolated lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

## Key concepts (5–15 minutes)

**Portable SQL:** `SELECT DISTINCT region FROM customers` emits one row per distinct projected `region`. With `SELECT DISTINCT region, status`, uniqueness applies to the **combination**, not each column independently. `SELECT` without `DISTINCT` normally retains duplicate projected rows (bag semantics). `DISTINCT` treats multiple NULLs as one distinct projected value for this purpose, even though `NULL = NULL` is UNKNOWN. `COUNT(DISTINCT region)` counts distinct **non-NULL** values; `COUNT(*)` counts rows. `COUNT(DISTINCT region, status)` is **not portable syntax**; use a subquery with `SELECT DISTINCT region, status` then `COUNT(*)`.

SQL result order is unspecified without `ORDER BY`. For portable queries using `SELECT DISTINCT`, order by projected columns rather than hidden columns. PostgreSQL requires `ORDER BY` expressions in the `SELECT DISTINCT` list. `DISTINCT ON (...)` is a **PostgreSQL-specific** extension that selects a row per group using an explicit compatible `ORDER BY`; it is not equivalent to standard `DISTINCT`. Later chapters cover `ROW_NUMBER()` for controlled deduplication.

**Important:** `DISTINCT` removes identical *projected* rows, not duplicate customer IDs or duplicate source records. It cannot repair data-quality defects or decide which of two conflicting events is authoritative. A one-to-many join can legitimately repeat customer attributes; fix join cardinality or aggregation rather than automatically masking the result with `DISTINCT`.

## Worked examples (15–30 minutes)

All six rows below are fictional. The two rows for customer 101 are separate order events, not accidental duplicate orders.

| order_id | customer_id | region | status | amount |
|---:|---:|---|---|---:|
| 1 | 101 | East | paid | 100.00 |
| 2 | 102 | West | paid | 80.00 |
| 3 | 101 | East | paid | 25.00 |
| 4 | 103 | East | pending | 40.00 |
| 5 | 104 | NULL | paid | 60.00 |
| 6 | 105 | West | paid | 90.00 |

### A. Projected duplicates versus distinct rows

```sql
WITH orders(order_id,customer_id,region,status,amount) AS (
 VALUES (1,101,'East'::text,'paid'::text,100.00),
        (2,102,'West','paid',80.00),
        (3,101,'East','paid',25.00),
        (4,103,'East','pending',40.00),
        (5,104,NULL::text,'paid',60.00),
        (6,105,'West','paid',90.00)
)
SELECT DISTINCT region FROM orders ORDER BY region NULLS LAST;
-- PostgreSQL: East, West, NULL (3 rows).
-- NULLS LAST is PostgreSQL-supported syntax; explicit NULL ordering varies by engine.
```

Without `DISTINCT`, the region projection has **6 rows**. `SELECT DISTINCT region, status` returns **4 combinations**: (East, paid), (East, pending), (West, paid), (NULL, paid). Use `ORDER BY region NULLS LAST, status` to make the display deterministic.

### B. COUNT differences

```sql
WITH orders(region) AS (
 VALUES ('East'::text),('West'),('East'),('East'),(NULL::text),('West')
)
SELECT COUNT(*) AS all_rows,
       COUNT(region) AS non_null_regions,
       COUNT(DISTINCT region) AS unique_non_null_regions
FROM orders;
-- 6 | 5 | 2
```

To include NULL as its own projected category, count the rows of `SELECT DISTINCT region`:

```sql
WITH orders(region) AS (
 VALUES ('East'::text),('West'),('East'),('East'),(NULL::text),('West')
)
SELECT COUNT(*) AS distinct_categories
FROM (SELECT DISTINCT region FROM orders) AS categories;
-- 3
```

### C. Business-key duplicates are a different question

```sql
WITH orders(customer_id) AS (
 VALUES (101),(102),(101),(103),(104),(105)
)
SELECT customer_id, COUNT(*) AS order_count
FROM orders
GROUP BY customer_id
HAVING COUNT(*) > 1;
-- customer_id 101 | order_count 2
```

This query finds customers with multiple orders, **not** invalid duplicate order records. A true data-quality check must define the expected unique key (for example, `order_id`) and the intended grain.

### D. A deterministic latest-event example (preview only)

When a downstream feed needs the most recent event per customer, simply writing `DISTINCT customer_id, event_time, status` will not choose a winner. PostgreSQL `DISTINCT ON (customer_id)` can do so with `ORDER BY customer_id, event_time DESC, event_id DESC`, where `event_id` breaks timestamp ties. This is vendor-specific and requires a business-approved tie-breaker; the portable window-function alternative is covered later. Never delete source records based on a deduplicated report.

## Hands-on practice (30–50 minutes)

Use the [Chapter 016 read-only SQL lab](../labs/016-distinct-duplicate-handling.sql). First independently confirm your PostgreSQL 18 server is a disposable training environment; a matching database name/version does **not** establish isolation.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/016-distinct-duplicate-handling.sql
```

The script uses `BEGIN READ ONLY`, a 10-second statement timeout, a database/version assertion, synthetic `VALUES` rows, deterministic example outputs, fail-closed acceptance assertions, and `ROLLBACK`. Expected: `environment_assertion = 1`, `acceptance_assertion = 1`, and exit status 0. These are **expected**, not observed runtime results.

Exercises (try before inspecting the answer key):

1. List unique regions including the NULL category. **Answer:** East, West, NULL (3 rows).
2. List unique (region, status) combinations. **Answer:** 4 combinations.
3. Count rows, non-NULL regions, and unique non-NULL regions. **Answer:** 6, 5, 2.
4. Count unique customers. **Answer:** 5.
5. Identify customers with more than one order. **Answer:** 101 has 2 orders; this is not evidence of an error.
6. Confirm unique order IDs. **Answer:** 6 distinct IDs out of 6 rows.
7. Count distinct regions including NULL by wrapping `SELECT DISTINCT` in a subquery. **Answer:** 3.
8. Compare `DISTINCT region` with `DISTINCT region,status`. **Answer:** 3 versus 4 rows; uniqueness applies to the whole projection.

## Troubleshooting and operational safety (50–55 minutes)

| Symptom | Explanation | Safe action |
|---|---|---|
| COUNT(DISTINCT) smaller than DISTINCT subquery count | Aggregate excludes NULL | State whether NULL is a category |
| Unexpected duplicates after JOIN | One-to-many relationship | Inspect join keys and expected grain |
| Different rows chosen on repeat runs | No deterministic tie-breaker | Define explicit ordering and unique tie key |
| Query expensive on large table | DISTINCT may sort or hash many rows | Review EXPLAIN and memory/spill metrics in sandbox |
| Counts disagree across systems | Collation, types, NULL or source grain differ | Reconcile source filters and normalization |
| Duplicate rows remain | Selected columns differ | Compare exact projected columns and business keys |

**DBRE/SRE guardrails:** Avoid `SELECT DISTINCT *` on large tables as an automatic fix for incorrect joins; it can increase CPU, memory and temporary disk usage. On a real system, investigate `EXPLAIN` plans, row estimates and sort/hash spill behavior under an approved workload budget. Do not run destructive `DELETE` deduplication or change unique constraints based solely on this chapter. Read-only `SELECT` may still be expensive; apply bounded test datasets and statement timeouts. Use no production credentials, production endpoints or real patient/customer data.

## Review questions and answers (55–60 minutes)

1. Does DISTINCT apply to a single column if two columns are projected? **No, to the entire projected tuple.**
2. Are two NULL values collapsed by SELECT DISTINCT? **Yes, for distinct-row elimination.**
3. Does COUNT(DISTINCT region) include NULL? **No.**
4. Is output ordered by DISTINCT alone? **No.**
5. Does DISTINCT repair an incorrect JOIN? **No; inspect cardinality and keys.**
6. Does a customer with two orders imply duplicate orders? **No.**
7. Why is DISTINCT ON not portable? **It is a PostgreSQL extension.**
8. What makes latest-record selection deterministic? **A business-approved sort with a unique tie-breaker.**
9. How can you count distinct tuples portably? **SELECT COUNT(*) FROM (SELECT DISTINCT a,b FROM ...) AS x.**
10. What proves PostgreSQL 18 runtime acceptance? **Executed SQL on an isolated PostgreSQL 18 instance with retained reproducible evidence.**

## References

- [PostgreSQL 18 SELECT and DISTINCT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18 transactions](https://www.postgresql.org/docs/18/sql-begin.html)
- [Next chapter 017 in Master TOC](../MASTER-TOC.md)
