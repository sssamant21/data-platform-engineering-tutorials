# 043 — LEFT OUTER JOIN: Preserve Unmatched Left Rows

**Part 05 — Joins & Relational Query Patterns** · **60 minutes** · **Audience:** beginners, data engineers, DBRE/SRE.

**Prerequisite:** [042 — INNER JOIN](042-inner-join-matched-records.md). **Hands-on:** [Chapter 043 PostgreSQL 18 lab](../labs/043-left-outer-join-unmatched-rows.sql). **Next:** 044 — RIGHT and FULL OUTER JOIN (planned; see [Master TOC](../MASTER-TOC.md)).

## 1. Outcomes and agenda (5 minutes)

By the end, explain left-table preservation, identify NULL-extended rows, distinguish filters in `ON` from `WHERE`, report unmatched records, and reconcile counts without multiplying amounts. Timing: objectives 5m; concepts 10m; walkthrough 15m; lab 20m; troubleshooting 5m; review 5m.

## 2. Concept and portable syntax (10 minutes)

`LEFT [OUTER] JOIN` returns every row from the **left** input at least once. For each matching right row it produces a pair; if no right row matches, the right-side columns are NULL. Multiple matches still produce multiple output rows: a left join **does not guarantee one output row per left row**.

```sql
SELECT o.order_id, o.customer_id, c.customer_name
FROM staging_orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
ORDER BY o.order_id;
```

The left table is `staging_orders`; orders without known customers remain visible. A NULL in `c.customer_name` alone is not proof of a missing match because a real matched customer name might be nullable. Test a non-nullable key from the right table, such as `c.customer_id IS NULL`. For nullable join keys, `NULL = NULL` is UNKNOWN, not TRUE.

## 3. Worked retail example (15 minutes)

Synthetic customers: (1, Ada), (2, Ben), (3, Cy). Staging orders: (101,1,20.00), (102,1,30.00), (103,2,15.00), (104,99,9.00). Order 104 intentionally references an absent customer in an **unconstrained staging table**, not a production table with an enforced foreign key.

```sql
SELECT o.order_id, c.customer_name, o.amount
FROM staging_orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
ORDER BY o.order_id;
```

| order_id | customer_name | amount |
|---:|---|---:|
| 101 | Ada | 20.00 |
| 102 | Ada | 30.00 |
| 103 | Ben | 15.00 |
| 104 | NULL | 9.00 |

Four rows and 74.00 total are preserved because the right-side key is unique. Compare `INNER JOIN`: only three rows and 65.00. Cy has no orders; she does not appear because **orders**, not customers, are on the left.

**Find missing customers (portable anti-join pattern):**

```sql
SELECT o.order_id, o.customer_id, o.amount
FROM staging_orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL
ORDER BY o.order_id;
```

Expected: (104,99,9.00). `NOT EXISTS` is an alternative, often clearer when testing absence.

**ON versus WHERE — crucial distinction:**

```sql
-- Keep every order, attach only matching Ada rows:
SELECT o.order_id, c.customer_name
FROM staging_orders o
LEFT JOIN customers c
  ON c.customer_id = o.customer_id AND c.customer_name = 'Ada'
ORDER BY o.order_id;
-- 4 rows; names Ada, Ada, NULL, NULL.

-- Filter the result *after* the join:
SELECT o.order_id, c.customer_name
FROM staging_orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_name = 'Ada'
ORDER BY o.order_id;
-- 2 rows: orders 101 and 102 only.
```

The latter WHERE condition removes unmatched rows (and Ben), effectively behaving like an inner join for this predicate. When a business filter must preserve unmatched left rows, put the right-side predicate in `ON`, or explicitly account for NULL in `WHERE` after considering semantics.

**One-to-many fan-out:** Joining customers on the left to orders on the right yields Ada twice, Ben once, and Cy once with NULL order fields. Summing customer-level balances after that join would double-count Ada's balance. Pre-aggregate orders by customer, or use a separately validated grain.

## 4. Hands-on lab (20 minutes)

Run only on an **isolated disposable PostgreSQL 18** database named `sql_tutorials`. Do not use production credentials. The lab creates temporary tables inside a transaction, sets local timeouts, checks version/database/standby, verifies exact results and totals, and ends with `ROLLBACK`.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/043-left-outer-join-unmatched-rows.sql
```

Exercises: (1) predict all four left-join rows; (2) identify order 104; (3) compare `ON` versus `WHERE` filtering; (4) swap left and right tables and identify customer Cy; (5) reconcile source amount = matched + unmatched. Expected source 4/74.00, matched 3/65.00, unmatched 1/9.00; customer-left result 4 rows with one no-order customer. The SQL script raises an exception if any invariant fails.

## 5. Troubleshooting, safety, and portability (5 minutes)

| Symptom | Likely cause | Safe check |
|---|---|---|
| Missing left rows | Right-side filter in `WHERE` | Compare predicates in `ON` versus `WHERE` |
| Unexpected duplicate rows | Right join key is not unique | `GROUP BY key HAVING COUNT(*) > 1` on synthetic staging |
| Wrong totals | One-to-many fan-out | Aggregate at original grain before joining |
| Missing match not detected | Checking nullable payload instead of key | Check right-side non-nullable primary key |
| NULL keys fail to match | Standard three-valued logic | Inspect NULL keys explicitly; do not assume equality |

`LEFT OUTER JOIN` and `LEFT JOIN` are portable SQL across PostgreSQL, MySQL/MariaDB, SQL Server, Oracle, Snowflake, BigQuery and SQLite; optimizer choices, collation and implicit conversions vary. PostgreSQL-specific lab features: `DO` blocks, `SET LOCAL`, `CREATE TEMP TABLE ... ON COMMIT DROP`, `IS DISTINCT FROM` row assertions, and `pg_is_in_recovery()`. Never apply this training lab to live systems. Read-only production reconciliation queries still require access approvals, bounded workloads, and appropriate data-handling controls.

## 6. Review questions with answers (5 minutes)

1. **Does a left join always produce the same number of rows as the left input?** No; multiple right matches multiply rows.
2. **Why is order 104 retained?** It is a left input row with no matching customer; right columns are NULL.
3. **Which right column is safest to test for a missing match?** A guaranteed non-nullable right-side key.
4. **Why does `WHERE c.customer_name = 'Ada'` remove unmatched orders?** NULL does not satisfy that predicate.
5. **What protects financial totals from join fan-out?** Validate join cardinality and aggregate at the correct grain.

## References and navigation

- [PostgreSQL 18 — Table Expressions / Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md) · [Lab SQL](../labs/043-left-outer-join-unmatched-rows.sql)

**Publication is not runtime certification.** Independent editorial review, comprehensive static QA, and actual PostgreSQL 18 execution require separate evidence.
