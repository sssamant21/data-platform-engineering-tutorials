# 042 — INNER JOIN: Matched Records

**Part 05 — Joins & Relational Query Patterns** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE

**Prerequisite:** [041 — Join fundamentals and relationship cardinality](041-join-fundamentals-and-relationship-cardinality.md). **Lab:** [042 — INNER JOIN matched records](../labs/042-inner-join-matched-records.sql). **Next:** 043 — LEFT OUTER JOIN (planned; see [Master TOC](../MASTER-TOC.md)).

## 1. Learning objectives and timing (5 minutes)

By the end, you can write an explicit INNER JOIN, explain which rows disappear, qualify ambiguous columns, distinguish key matches from business filters, detect unexpected multiplicity, and reconcile matched and unmatched records. Schedule: objectives 5m; concepts 10m; walkthroughs 15m; lab 20m; troubleshooting 5m; review 5m.

## 2. Key concept: matched pairs (10 minutes)

An **INNER JOIN** returns a row for **each pair** of input rows satisfying the `ON` condition. If no pair matches, the input row does not appear. If a customer has two orders, that customer can appear twice. This is *not* a deduplication operation.

Portable syntax:

```sql
SELECT o.order_id, c.customer_name, o.amount
FROM orders AS o
INNER JOIN customers AS c
  ON c.customer_id = o.customer_id
ORDER BY o.order_id;
```

Here `o` and `c` are aliases; `o.customer_id` and `c.customer_id` are qualified to prevent ambiguity. A primary key on `customers.customer_id` ensures at most one customer per order; an enforced foreign key ensures a valid customer for each non-null order customer_id. Without constraints, an inner join may silently omit orphan orders or multiply rows when the customer key is not unique.

`JOIN` alone is usually shorthand for `INNER JOIN`; spelling it out improves beginner readability. Never omit `ON` accidentally. Use explicit join predicates, not comma-separated tables.

## 3. Worked example: synthetic retail data (15 minutes)

Customers: (1, Ada), (2, Ben), (3, Cy). Orders: (101, 1, 20.00), (102, 1, 30.00), (103, 2, 15.00). A separate **unconstrained staging** row (104, 99, 9.00) intentionally has no matching customer. This represents an ingestion-quality exception, not a valid production foreign key.

```sql
SELECT o.order_id, c.customer_name, o.amount
FROM staging_orders AS o
INNER JOIN customers AS c
  ON o.customer_id = c.customer_id
ORDER BY o.order_id;
```

| order_id | customer_name | amount |
|---:|---|---:|
| 101 | Ada | 20.00 |
| 102 | Ada | 30.00 |
| 103 | Ben | 15.00 |

**Expected:** 3 matched order rows; 2 distinct matched customers; matched amount **65.00**. Cy has no order; staged order 104 has no customer. Neither appears in the inner join. The **raw staging total is 74.00**; reporting only the matched total without documenting the rejected 9.00 would hide a data-quality issue.

An extra business filter belongs in `WHERE`:

```sql
SELECT o.order_id, c.customer_name
FROM staging_orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
WHERE o.amount >= 25.00
ORDER BY o.order_id;
```

Expected: only (102, Ada). The `ON` condition relates records; `WHERE` filters the resulting matched pairs. For inner joins, some predicates can be moved between `ON` and `WHERE` without changing results, but this is **not generally true for outer joins** (Chapter 043).

**Preflight reconciliation** — always compare the input grain and the output grain:

```sql
SELECT COUNT(*) AS source_orders, SUM(amount) AS source_amount
FROM staging_orders;
-- 4, 74.00

SELECT COUNT(*) AS matched_orders, SUM(o.amount) AS matched_amount
FROM staging_orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id;
-- 3, 65.00
```

Avoid `SUM(o.amount)` if you add a one-to-many `order_items` join; the same order amount can be repeated. Aggregate at the correct grain first.

## 4. Hands-on lab: isolated PostgreSQL 18 (20 minutes)

Execute [the complete lab SQL](../labs/042-inner-join-matched-records.sql) only in a disposable `sql_tutorials` database on PostgreSQL 18. It checks the database name, version, and writable primary; uses transaction-local timeouts and temporary synthetic tables; raises an exception on failed assertions; and finishes with `ROLLBACK`.

From the repository root, using isolated lab credentials:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/042-inner-join-matched-records.sql
```

Steps: (1) inspect three customers and four staged orders; (2) run the explicit inner join and verify three rows; (3) run the amount filter and verify one row; (4) identify the unmatched staging order using `NOT EXISTS`; (5) compare source and matched counts and amounts; (6) inspect the deterministic assertion notice and final rollback.

Expected: source **4 / 74.00**, matched **3 / 65.00**, unmatched **1 / 9.00**, two distinct matched customers, filtered **1**, and zero persistent objects. An inner join cannot itself show which source rows were lost: use a separately audited anti-join or `NOT EXISTS` query.

**Practice:** Change the filter in the *SELECT example* to `amount >= 15.00` (expected three matched rows). Then explain why `COUNT(DISTINCT customer_id)` equals 2, not 3. Do not modify the assertion script to conceal a failure.

## 5. Troubleshooting and DBRE/SRE safeguards (5 minutes)

| Symptom | Likely cause | Safe diagnostic |
|---|---|---|
| Missing orders | Unmatched customer key | `NOT EXISTS` anti-join on staged orders |
| Too many rows | Duplicate right-side keys or incorrect join predicate | `GROUP BY customer_id HAVING COUNT(*) > 1` |
| Inflated amount | One-to-many fan-out | Aggregate at order grain before joining children |
| Ambiguous column error | Both tables contain the same column | Qualify columns with aliases |
| Slow join | Large scans, stale statistics, missing useful access path | Review read-only `EXPLAIN` and actual plan only in approved environment |

For production incidents, start with read-only count/uniqueness checks, avoid unbounded exports of sensitive data, and capture reconciliation evidence. Do not add `DISTINCT` merely to mask an unexpected fan-out. Index selection and query plans are covered in Part 10.

## 6. Portability and safety

`INNER JOIN ... ON`, `WHERE`, `ORDER BY`, `COUNT`, `SUM`, and `NOT EXISTS` are widely portable SQL. The lab uses **PostgreSQL-specific** `DO $$`, PL/pgSQL `RAISE EXCEPTION`, `current_setting`, `pg_is_in_recovery()`, and `CREATE TEMP TABLE ... ON COMMIT DROP`. Behavior and syntax for temporary tables and transaction controls vary by vendor. Never run the lab against production or with production credentials.

## 7. Review questions with answers (5 minutes)

1. **Why is Cy missing?** No order matches customer 3.
2. **Why does Ada appear twice?** Two orders match Ada's customer key.
3. **Why is staged order 104 absent?** Customer 99 is not in the customer table.
4. **What is the matched revenue?** 65.00; source revenue is 74.00, leaving 9.00 unmatched.
5. **Does INNER JOIN guarantee unique output?** No; multiple matching pairs can produce multiple rows.
6. **How do you investigate dropped source records?** Compare source and matched counts and run an anti-join / `NOT EXISTS`.
7. **Can DISTINCT fix a faulty join?** It can hide the symptom, not repair incorrect keys or grain.

## 8. References and navigation

- [PostgreSQL 18 — Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-JOIN)
- [PostgreSQL 18 — Constraints and foreign keys](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md) · [Previous chapter](041-join-fundamentals-and-relationship-cardinality.md)

**Validation disclosure:** Authorship and publication do not constitute independent editorial review or PostgreSQL 18 runtime validation. Those require separate recorded evidence.
