# 046 — Multi-table Joins and Join Condition Design

**Part 05 — Joins & Relational Query Patterns** · **Duration:** 60 minutes · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Baseline:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Chapter 045](045-cross-join-and-self-join.md) · [Lab SQL](../labs/046-multi-table-joins-condition-design.sql)

## 1. Learning objectives (5 minutes)

By the end you can: (1) join three or more tables using explicit keys; (2) choose INNER versus LEFT JOIN based on reporting requirements; (3) predict output grain and cardinality; (4) avoid accidental fan-out and incorrect totals; (5) reconcile missing relationships before promoting an ETL query; and (6) distinguish portable SQL from PostgreSQL-specific lab controls.

## 2. Business scenario and data grain (5 minutes)

A synthetic retailer stores **customers** (one row/customer), **orders** (one row/order), **order_items** (one row/item), and **payments** (one row/payment). A data engineer needs a customer/order report; an SRE needs evidence that joins do not inflate monetary totals. These tables intentionally have different grains. Joining orders to items AND payments can multiply rows: an order with two items and two payments produces four joined rows.

Synthetic fixtures: customers 1=Ana, 2=Ben, 3=Cleo; orders 101(customer 1), 102(customer 1), 103(customer 2), 104(customer 99, deliberately unmatched); items: (101,30), (101,20), (102,15), (103,25), (104,10); payments: (101,40), (101,10), (102,15), (103,25). Currency amounts use NUMERIC(12,2). Orders are 4; items 5, total 100.00; payments 4, total 90.00; order 104 has no customer or payment.

## 3. Join keys and relationship map (5 minutes)

- `orders.customer_id = customers.customer_id`: many orders to one customer; use `LEFT JOIN` when orphan detection matters.
- `order_items.order_id = orders.order_id`: many items to one order.
- `payments.order_id = orders.order_id`: many payments to one order.
- **Never** join `order_items` directly to `payments` using only `order_id` and then sum both monetary columns: both child sets expand independently.

The example deliberately omits a foreign key on `orders.customer_id` so a missing reference can be detected. In real systems, enforce referential integrity where feasible; staging feeds may temporarily contain unmatched records.

## 4. First multi-table join (5 minutes)

Portable SQL:

```sql
SELECT o.order_id, c.customer_name, i.item_amount
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
JOIN order_items AS i ON i.order_id = o.order_id
ORDER BY o.order_id, i.item_id;
```

Expected **5 rows**: order 101 appears twice, orders 102/103/104 once each; order 104 has a NULL customer name. This is **item grain**, not order grain. A `WHERE c.customer_name IS NOT NULL` would silently discard the unmatched order; decide whether that is acceptable before filtering.

## 5. Avoid multiplying child rows (10 minutes)

Aggregate each child table to the desired **order grain** first, then join:

```sql
WITH item_totals AS (
  SELECT order_id, SUM(item_amount) AS item_total
  FROM order_items GROUP BY order_id
), payment_totals AS (
  SELECT order_id, SUM(payment_amount) AS paid_total
  FROM payments GROUP BY order_id
)
SELECT o.order_id, c.customer_name,
       COALESCE(i.item_total, 0) AS item_total,
       COALESCE(p.paid_total, 0) AS paid_total
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
LEFT JOIN item_totals AS i ON i.order_id = o.order_id
LEFT JOIN payment_totals AS p ON p.order_id = o.order_id
ORDER BY o.order_id;
```

Expected **4 rows** with item/paid totals: 101 = 50/50; 102 = 15/15; 103 = 25/25; 104 = 10/0. Grand item total = **100.00**, paid total = **90.00**. The naive four-table join creates **6 rows** (four for order 101, one each for 102 and 103, and one for 104 with LEFT joins = **7 rows**); its sums are wrong: item amounts for order 101 repeat per payment, and payments repeat per item. Do not repair with `SUM(DISTINCT amount)`: two legitimately equal amounts would be lost.

## 6. ON versus WHERE (5 minutes)

A predicate on a nullable right-side column in `WHERE` can turn a LEFT JOIN into an effective inner join:

```sql
-- Keeps all orders, with qualifying payment matches when present:
SELECT o.order_id, p.payment_amount
FROM orders o LEFT JOIN payments p
  ON p.order_id = o.order_id AND p.payment_amount >= 20;
```

Moving `p.payment_amount >= 20` to `WHERE` removes orders with no qualifying payment. `ON` defines which rows match; `WHERE` filters the resulting rows. Parenthesize complex predicates and use qualified column names.

## 7. Hands-on PostgreSQL 18 lab (15 minutes)

Use [046-multi-table-joins-condition-design.sql](../labs/046-multi-table-joins-condition-design.sql). Run **only** on a disposable PostgreSQL 18+ instance with database `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/046-multi-table-joins-condition-design.sql
```

The lab checks server version, database name and recovery mode; creates only transaction-local temporary tables; sets statement and lock timeouts; verifies exact row counts and sums; and ends in `ROLLBACK`. Expected PASS notice: `orders=4, item_rows=5, joined_item_rows=5, report_rows=4, item_total=100.00, paid_total=90.00, orphan_orders=1`. This is an **expected** result, not a claim of observed execution.

Exercises: A. Change the customer join to INNER JOIN and predict which order disappears (104). B. Explain why a direct items-to-payments join multiplies order 101 (2 × 2 = 4). C. Add a per-order balance `item_total - paid_total`; expected balance is 10.00 for order 104, zero otherwise. D. Describe how to handle late-arriving payments without dropping unpaid orders.

## 8. Troubleshooting (4 minutes)

| Symptom | Likely cause | Safe diagnosis |
|---|---|---|
| Unexpected duplicate orders | Child-table fan-out | Count rows per order after each join |
| Inflated revenue | Two independent one-to-many joins | Aggregate each child before joining |
| Missing orders | INNER JOIN or right-table WHERE filter | Compare source IDs using LEFT JOIN and NULL checks |
| NULL amounts | No matching child rows | Preserve NULL until business meaning is clear; use COALESCE for reporting only |
| Slow query | Missing key indexes, poor cardinality estimates | In isolated/staging environment inspect `EXPLAIN`; do not assume indexes alone fix fan-out |

## 9. Operational safeguards and portability (3 minutes)

SQL `JOIN`, `ON`, `GROUP BY`, `SUM`, `COALESCE` and CTEs are broadly portable; optimizer choices, temporary-table lifecycle, `SET LOCAL`, `DO` blocks and `pg_is_in_recovery()` are PostgreSQL-specific. Never run tutorial DDL/DML against production or use production credentials. In ETL, compare input/output row counts and totals, track orphan keys, set cost/time limits, and investigate unexpected cardinality changes before publication. Avoid `EXPLAIN ANALYZE` on expensive production queries without approval.

## 10. Review questions with answers (5 minutes)

1. **What is the grain of an order-item join?** One row per matching item, not necessarily one per order.
2. **Why can joining items and payments inflate totals?** Each matching item pairs with each matching payment for the same order.
3. **How do you obtain one row per order?** Aggregate items and payments separately by order ID, then join each aggregate to orders.
4. **Why use LEFT JOIN for reconciliation?** It retains parent rows with no matching child or dimension.
5. **Why not use SUM(DISTINCT amount)?** Equal monetary values may represent separate valid transactions.
6. **What is a safe first diagnostic?** Compare source and joined row counts by key, then check unmatched keys.

## 11. References (2 minutes)

- [PostgreSQL 18 — Table Expressions](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — WITH Queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

## 12. Completion checklist (1 minute)

- [ ] Explain order grain versus item/payment grain.
- [ ] Predict all four order-level report rows and totals.
- [ ] Run lab on isolated PostgreSQL 18 and retain evidence if available.
- [ ] Verify that no persistent objects remain.
- [ ] Continue with Chapter 047 — One-to-many and many-to-many relationships.

**Publication state:** Authored. **Independent editorial review:** Pending. **Targeted static inspection:** Authored SQL reviewed, runtime not executed. **Comprehensive static QA:** Pending. **Actual PostgreSQL 18 runtime validation:** Pending.
