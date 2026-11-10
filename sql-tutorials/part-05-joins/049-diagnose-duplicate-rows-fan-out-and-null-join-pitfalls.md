# 049 — Diagnose Duplicate Rows, Fan-out, and NULL Join Pitfalls

**Part 05 — Joins & Relational Query Patterns** · **60 minutes** · **Audience:** data engineers, analysts, DBRE/SRE · **Primary lab:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 048](048-semi-joins-and-anti-joins-using-exists-and-not-exists.md) · [Lab 049](../labs/049-duplicate-rows-fanout-null-join-pitfalls.sql) · [Next: 050](../MASTER-TOC.md)

## 1. Objectives and prerequisites (5 minutes)

After this lesson you can distinguish source duplicates from legitimate one-to-many rows; calculate join cardinality and fan-out; explain NULL join behavior; find missing and duplicated keys; prevent inflated sums; and produce an auditable reconciliation. Prerequisites: Chapters 041–048, SELECT, GROUP BY basics, and SQL NULL logic.

**Agenda:** objectives 5 min; concepts 10; worked examples 15; lab 20; troubleshooting 5; review 5.

## 2. The business problem (5 minutes)

A fictional retailer stores **three orders** with order amounts **40.00, 30.00, and 20.00** (total **90.00**). There are **four item rows**: order 101 has two items, order 102 one, and order 103 one. There are **four payment rows**: order 101 has two payments, order 102 one, and order 103 one. An additional imported item has a NULL order_id and cannot match an order using ordinary equality. All data are synthetic.

The expected order-to-item join has **4 rows**. The expected order-to-payment join has **4 rows**. Joining all three at the detail grain yields **6 rows**: order 101 contributes 2 × 2 = 4, and the other orders contribute one each. Summing the order amount over those six rows yields **210.00**, not 90.00. That number is wrong for an order-level revenue report even though every join predicate is syntactically valid.

## 3. Core concepts: grain and cardinality (5 minutes)

**Grain** is what one row represents: an order, an order item, or a payment. A **one-to-many** relationship legitimately repeats a parent key in joined output. **Fan-out** is the increase in rows when joining to multiple matches. **Duplicate source keys** are a different defect: a supposed unique business key appears more than once in its own dataset. A many-to-many join between two detail tables can multiply measures from both sides.

Before writing a query, write down its intended grain and the uniqueness guarantee for each join key. A LEFT JOIN preserves all left rows, but it does **not** promise one output row per left row. A WHERE predicate on a right-side column can silently remove NULL-extended rows and change effective outer-join behavior.

## 4. Worked example: locate fan-out (7 minutes)

The following portable SQL assumes tables `orders(order_id, amount)` and `order_items(item_id, order_id, item_amount)`:

```sql
SELECT o.order_id, COUNT(i.item_id) AS item_rows
FROM orders AS o
LEFT JOIN order_items AS i ON i.order_id = o.order_id
GROUP BY o.order_id
ORDER BY o.order_id;
```

Expected rows: **101 → 2**, **102 → 1**, **103 → 1**. To find nonunique keys in a staging feed:

```sql
SELECT external_order_id, COUNT(*) AS occurrences
FROM staging_orders
GROUP BY external_order_id
HAVING COUNT(*) > 1;
```

An empty result means no duplicate non-NULL values in this specific check; investigate NULL keys separately. `COUNT(*)` counts rows, `COUNT(column)` ignores NULLs, and `COUNT(DISTINCT column)` counts distinct non-NULL values. Never assume `DISTINCT` repairs a wrong join.

## 5. Worked example: why the total inflates (8 minutes)

```sql
-- Incorrect for order-level revenue: each order amount repeats per detail pair.
SELECT SUM(o.amount) AS incorrect_order_total
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
JOIN payments AS p ON p.order_id = o.order_id;
-- Expected: 210.00, whereas the authoritative order total is 90.00.
```

A safe approach is to **aggregate each child to one row per order before joining**:

```sql
WITH item_totals AS (
  SELECT order_id, SUM(item_amount) AS item_total
  FROM order_items
  GROUP BY order_id
), payment_totals AS (
  SELECT order_id, SUM(payment_amount) AS paid_total
  FROM payments
  GROUP BY order_id
)
SELECT o.order_id, o.amount,
       COALESCE(i.item_total, 0) AS item_total,
       COALESCE(p.paid_total, 0) AS paid_total
FROM orders AS o
LEFT JOIN item_totals AS i ON i.order_id = o.order_id
LEFT JOIN payment_totals AS p ON p.order_id = o.order_id
ORDER BY o.order_id;
```

Expected **3 rows**, one per order. With synthetic items totaling 40, 30, 20 and payments totaling 40, 30, 20, each per-order child total equals its order amount. The authoritative order total remains **90.00**. Use an explicit business rule for partial, refunded, or overpaid orders in real pipelines.

## 6. NULL pitfalls and anti-join checks (5 minutes)

Ordinary `NULL = NULL` is UNKNOWN, so a NULL child key does not match a NULL parent key under `=`. Use `IS NULL` to identify missing keys, not `= NULL`. For unmatched imported items:

```sql
SELECT i.item_id, i.order_id
FROM order_items AS i
LEFT JOIN orders AS o ON o.order_id = i.order_id
WHERE o.order_id IS NULL;
```

This returns orphaned and NULL-key item rows. `NOT EXISTS` is an alternative when you need an anti-join. PostgreSQL's `IS NOT DISTINCT FROM` is a NULL-safe equality operator; **do not** apply NULL-safe matching to business keys without explicit data-model approval. A NULL often means unknown, not a shared entity.

## 7. Hands-on PostgreSQL 18 lab (20 minutes)

Use an isolated, disposable PostgreSQL 18 database named `sql_tutorials`; never use production endpoints or credentials.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/049-duplicate-rows-fanout-null-join-pitfalls.sql
```

[Lab 049](../labs/049-duplicate-rows-fanout-null-join-pitfalls.sql) creates **temporary** tables in a transaction, checks PostgreSQL 18 and the database name, enforces transaction-local timeouts, tests counts and amounts with fail-closed assertions, and finishes with `ROLLBACK`. The lab is *not* read-only because it creates temporary fixtures; it makes no persistent schema/data changes.

**Expected, not observed:** orders 3; order amount 90.00; valid item rows 4; imported NULL-key item rows 1; payments 4; three-way join rows 6; incorrect order sum 210.00; safe preaggregated rows 3; item/payment sums 90.00 each; unmatched items 1; staging duplicate business keys 1. Record database version, command, output, exit status, and rollback confirmation if executing in a real isolated environment.

Practice: (A) explain why order 101 generates four detail pairs; (B) change a temporary payment's amount and identify which reconciliation assertion fails; (C) add a duplicate staging key and predict duplicate-key group counts; (D) explain why `SUM(DISTINCT o.amount)` is unsafe when two orders have the same amount.

## 8. Production engineering and DBRE/SRE safeguards (2 minutes)

Require a documented output grain, pre/post join row counts, source uniqueness checks, orphan-key counts, and amount reconciliation before a pipeline is accepted. For healthcare-like synthetic encounters/claims, the same rule applies: do not sum encounter-level costs after joining multiple claim lines and observations. Use least-privilege read access to investigate actual systems; never delete duplicate records based solely on a row-count anomaly.

## 9. Troubleshooting (3 minutes)

- **Unexpectedly high totals:** inspect join keys and child multiplicities; preaggregate by parent key.
- **Missing outer rows:** check right-side filters in `WHERE` versus `ON`.
- **NULL mismatch:** use `IS NULL` for diagnostics; do not invent NULL-equality semantics.
- **Still duplicated after preaggregation:** check whether the parent source has duplicate keys or the child grouping uses the wrong grain.
- **Slow query:** inspect plan and row estimates; indexing and statistics matter, but correctness comes first.
- **Lab guard failure:** verify the disposable database and PostgreSQL 18; never bypass the guard.

## 10. Review questions and answers (5 minutes)

1. **What is fan-out?** More joined rows caused by multiple matches on a join key.
2. **Why is 210.00 incorrect?** Order 101's 40.00 is repeated four times, while orders 102 and 103 contribute once.
3. **What does preaggregation fix?** It reduces each child to the intended parent grain before the multi-table join.
4. **Does DISTINCT always fix revenue?** No; two different orders can have equal amounts.
5. **How does NULL join?** Under ordinary equality, NULL matches neither a non-NULL value nor another NULL.
6. **What makes an operational reconciliation safe?** Independent source counts/totals, uniqueness checks, unmatched-key checks, and fail-closed assertions.

## 11. Validation and safety status

**Authored/published:** subject to GitHub publication checkpoint. **Targeted static reasoning:** expected cardinalities and arithmetic checked against synthetic fixture. **Independent editorial review:** pending. **Comprehensive syntax/link QA:** pending. **Actual isolated PostgreSQL 18 runtime validation:** pending until executed with reproducible evidence. No production credentials or patient data are used.

## 12. References and next chapter

- [PostgreSQL 18 — Table Expressions and Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Comparison Predicates](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [Master TOC](../MASTER-TOC.md): **050 — Lab 05: consolidate customers, orders, and payments**.
