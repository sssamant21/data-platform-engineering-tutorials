# 048 — Semi-joins and Anti-joins Using EXISTS and NOT EXISTS

**Part 05 — Joins & Relational Query Patterns** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Baseline:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Chapter 047](047-one-to-many-and-many-to-many-relationships.md) · [Lab 048](../labs/048-exists-not-exists-semi-anti-joins.sql)

## 1. Learning objectives and prerequisites (5 minutes)

After this lesson, you can explain semi-joins (return qualifying left-side rows) and anti-joins (return nonqualifying left-side rows); write correlated `EXISTS` and `NOT EXISTS` predicates; predict results with duplicate matches and NULLs; reconcile counts; and avoid accidental production writes. Prerequisites: SELECT, WHERE, primary/foreign keys, INNER and LEFT JOIN (Chapters 011, 041–047).

**Schedule:** objectives 5; concepts 10; walkthrough 15; isolated lab 20; troubleshooting 5; review 5.

## 2. Scenario and mental model (10 minutes)

A fictional retailer has four customers and four orders. Ana (1) has two orders, Ben (2) has one, Cleo (3) has none, and Dev (4) has one. One order has a NULL customer_id to model a malformed imported feed; the source order table intentionally does not enforce a foreign key in this *training fixture*. Valid customer IDs are 1, 2, 3, 4; order customer IDs are 1, 1, 2, NULL, 4.

A **semi-join** answers *which customers have at least one order?* It returns each qualifying customer once, regardless of how many matching orders exist. An **anti-join** answers *which customers have no orders?* It returns customers for whom no match exists.

SQL expresses these patterns portably with `WHERE EXISTS (subquery)` and `WHERE NOT EXISTS (subquery)`. These are existence tests, not aggregation; SQL does not require `SELECT 1` specifically, but it communicates that the subquery's selected values do not matter.

## 3. Walkthrough: positive existence (7 minutes)

```sql
SELECT c.customer_id, c.customer_name
FROM customers AS c
WHERE EXISTS (
  SELECT 1
  FROM orders AS o
  WHERE o.customer_id = c.customer_id
)
ORDER BY c.customer_id;
```

**Expected rows:** (1, Ana), (2, Ben), (4, Dev). Ana appears once even though two orders match. The subquery is *correlated*: `c.customer_id` comes from the outer query. A regular `INNER JOIN` without deduplication would return Ana twice.

A customer count can be computed with `COUNT(*)` over the filtered customer table; the expected answer is **3**, not 4.

## 4. Walkthrough: negative existence (8 minutes)

```sql
SELECT c.customer_id, c.customer_name
FROM customers AS c
WHERE NOT EXISTS (
  SELECT 1
  FROM orders AS o
  WHERE o.customer_id = c.customer_id
)
ORDER BY c.customer_id;
```

**Expected:** (3, Cleo), exactly **1** customer. This is useful for detecting missing ingestion, unmatched master records, or accounts without activity. A correctly correlated `NOT EXISTS` ignores unrelated NULL order keys.

A common alternative uses `LEFT JOIN orders ... WHERE o.order_id IS NULL`. This can be correct when `order_id` is guaranteed NOT NULL and the join condition is correct. Prefer `NOT EXISTS` when the intent is simply absence: it avoids depending on the nullable status of a selected right-side column.

## 5. NULL trap: NOT IN is not equivalent (5 minutes)

```sql
-- Deliberately problematic if the subquery includes NULL:
SELECT customer_id
FROM customers
WHERE customer_id NOT IN (SELECT customer_id FROM orders);
```

Because the subquery includes NULL, comparisons for unmatched customer IDs evaluate to UNKNOWN under SQL three-valued logic. The predicate does **not** return Cleo; expected output is **zero rows** in this fixture. `NOT EXISTS` correctly returns Cleo. A carefully filtered `NOT IN (SELECT customer_id FROM orders WHERE customer_id IS NOT NULL)` can be equivalent here, but always verify nullable inputs and SQL dialect behavior.

## 6. Data engineering and DBRE/SRE patterns (5 minutes)

- **Incremental reconciliation:** find staging customer IDs without a matching curated customer record using `NOT EXISTS`, before any write.
- **Coverage checks:** find customers with at least one paid order using `EXISTS` with `AND o.status = 'paid'` *inside* the subquery.
- **Safety:** on large datasets, inspect query plans and indexing of the matching key (`orders.customer_id`); don't assume a correlated subquery is always slower or faster than a JOIN. PostgreSQL may implement existence predicates with semi/anti join plan nodes.
- **Correct grain:** `EXISTS` retains one row per source customer, even with many matching orders; it does not resolve duplicate rows already present in the left source.
- **Read-only first:** use count checks and investigate NULL/unmatched keys before applying any cleanup or ETL mutation.

## 7. Hands-on PostgreSQL 18 lab (20 minutes)

Use a **disposable** PostgreSQL 18 database named `sql_tutorials`, never a production cluster. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/048-exists-not-exists-semi-anti-joins.sql
```

[Lab 048 SQL](../labs/048-exists-not-exists-semi-anti-joins.sql) checks database name, PostgreSQL version, and read-write server state before creating temporary tables. It uses synthetic rows, transaction-local timeouts, exact assertions, and `ROLLBACK`. **Predicted checks:** 4 customers, 5 orders, 3 customers with orders, 1 without, 4 matched order rows, 1 NULL-key order, 0 rows from the unsafe `NOT IN` expression, and 1 from `NOT EXISTS`. These are *expected*, not observed runtime results.

Practice: (A) add a second order for Dev inside the disposable transaction; does the semi-join output count change? (B) add a paid-status condition and predict who qualifies. (C) remove the NULL-key order in a temporary fixture and compare `NOT IN` with `NOT EXISTS`. (D) describe why `SELECT DISTINCT` on a broken JOIN is not a substitute for fixing cardinality.

## 8. Portability notes (2 minutes)

`EXISTS`, `NOT EXISTS`, correlated subqueries, and `IS NULL` are broadly portable SQL. PostgreSQL-specific *lab harness* features include `DO $$ ... $$`, `RAISE EXCEPTION`, `SET LOCAL`, `pg_is_in_recovery()`, and temporary tables with `ON COMMIT DROP`. Optimizer choices and NULL-related edge cases should be verified on each target platform. `EXPLAIN` formats vary across PostgreSQL, MySQL, SQL Server, Oracle, Snowflake, and BigQuery.

## 9. Troubleshooting and acceptance (3 minutes)

**All rows qualify unexpectedly:** verify the correlation references the outer customer ID; an uncorrelated EXISTS can be true for every customer. **Missing rows from NOT IN:** inspect NULLs in the subquery. **Duplicate output:** check whether the left source itself contains duplicates or whether a JOIN was used instead of EXISTS. **Slow query:** inspect key types, statistics, and indexes before changing SQL. **Guard failure:** check isolated database name, version, and permissions; never bypass a guard against a live database.

Acceptance requires predicted results to match observed output, no permanent objects, successful rollback, and retained command/version/exit-code evidence for any future PostgreSQL 18 runtime certification.

## 10. Review questions and answers (5 minutes)

1. **What does EXISTS test?** Whether the correlated subquery returns at least one row.
2. **Why does Ana appear once?** The outer customer row is filtered by a Boolean existence condition, not multiplied by matching orders.
3. **What does NOT EXISTS return here?** Cleo, the sole customer with no matching order.
4. **Why is NOT IN dangerous with NULLs?** UNKNOWN comparisons can exclude every otherwise unmatched candidate.
5. **How do you detect customers with a paid order?** Add `o.status = 'paid'` to the correlated EXISTS subquery.
6. **Is publication proof of successful PostgreSQL 18 execution?** No. Preserve actual isolated runtime evidence separately.

## 11. Safety and validation status

Only synthetic data. Never use production credentials, endpoints, or tables. The lab uses temporary tables in a rollback-only transaction and fails closed on unexpected database/version/standby state. **Authored and published:** this chapter. **Targeted static reasoning:** expected counts and NULL behavior inspected. **Independent editorial review:** pending. **Comprehensive automated syntax/link QA:** pending. **Actual isolated PostgreSQL 18 runtime validation:** pending, no evidence claimed.

## 12. References and next milestone

- [PostgreSQL 18 — Subquery Expressions (EXISTS, IN, NOT IN)](https://www.postgresql.org/docs/18/functions-subquery.html)
- [PostgreSQL 18 — Table Expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [Master TOC](../MASTER-TOC.md): next **049 — Diagnose duplicate rows, fan-out, and NULL join pitfalls**.
