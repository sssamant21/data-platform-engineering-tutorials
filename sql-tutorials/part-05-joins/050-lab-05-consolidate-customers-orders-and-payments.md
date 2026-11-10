# 050 — Lab 05: Consolidate Customers, Orders, and Payments

**Part 05 — Joins & Relational Query Patterns** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Lab target:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 049](049-diagnose-duplicate-rows-fan-out-and-null-join-pitfalls.md) · [SQL lab 050](../labs/050-lab-05-consolidate-customers-orders-payments.sql) · [Next: 051](../MASTER-TOC.md)

## 1. Outcomes and prerequisites (5 minutes)

By the end, you can (1) define the output grain before joining, (2) retain unmatched orders with LEFT JOIN, (3) distinguish zero payments from missing customers, (4) preaggregate one-to-many payments without fan-out, (5) reconcile source and output totals, and (6) document safe DBRE/SRE acceptance evidence.

Prerequisites: Chapters 041–049, SELECT, JOIN, GROUP BY, COALESCE, CASE, and NULL basics. **Agenda:** objectives 5 min; modeling and SQL concepts 10; worked examples 15; lab 20; validation/troubleshooting 5; review 5.

## 2. Business scenario and grain (5 minutes)

A fictional retailer receives customer, order, and payment feeds. The data engineer needs **one report row per order**, including orders whose customer reference is missing and orders with no payments. The DBRE/SRE team must prove that no source order or amount disappears during consolidation. All identifiers, names, and amounts are synthetic.

| Source | Expected rows | Notes |
|---|---:|---|
| Customers | 3 | IDs 1, 2, 3 |
| Orders | 5 | IDs 101–105; order 105 references nonexistent customer 99 |
| Payments | 5 | Order 101 has two payments; 102, 103, 105 have one each; 104 has none |
| Report | 5 | One row **per order**, including orphaned customer and unpaid order |

Order amounts: 101=40.00, 102=30.00, 103=20.00, 104=10.00, 105=15.00; total **115.00**. Payments: 101=10.00+30.00, 102=30.00, 103=15.00, 105=15.00; total **100.00**. Unpaid balance **15.00**: order 103 has 5.00 outstanding, order 104 has 10.00 outstanding. There are **4 orders with payments**, **1 with none**, **1 unmatched customer**, and **1 partially paid order**.

## 3. Relational design and safety principles (5 minutes)

The customer-to-order relationship is one-to-many, and the order-to-payment relationship is one-to-many. An INNER JOIN to customers would drop order 105. An INNER JOIN to payments would drop order 104. A direct LEFT JOIN to payments repeats order 101, so summing order amounts on the raw join produces **155.00**, an incorrect total.

Define the output grain first: `order_id` must be unique in the final report. Aggregate payments to one row per order before joining. Prefer source-of-truth order amounts to sums of amounts repeated by payment detail. Treat a NULL customer as a data-quality issue, not as a reason to discard an order. `COALESCE` may display 0.00 for missing payments, but distinguish "no payment rows" from an actual zero-value payment by also carrying `payment_count`.

## 4. Portable SQL walkthrough (10 minutes)

Assume tables `customers(customer_id, customer_name)`, `orders(order_id, customer_id, order_amount)`, and `payments(payment_id, order_id, payment_amount)`. This pattern uses broadly portable SQL; `WITH`, `LEFT JOIN`, `CASE`, `COALESCE`, and `GROUP BY` are widely supported. Exact data types and transaction guards in the executable lab are PostgreSQL-specific.

```sql
WITH payment_summary AS (
  SELECT order_id,
         COUNT(*) AS payment_count,
         SUM(payment_amount) AS paid_amount
  FROM payments
  GROUP BY order_id
)
SELECT o.order_id,
       o.customer_id,
       c.customer_name,
       o.order_amount,
       COALESCE(p.payment_count, 0) AS payment_count,
       COALESCE(p.paid_amount, 0) AS paid_amount,
       o.order_amount - COALESCE(p.paid_amount, 0) AS balance_due,
       CASE WHEN c.customer_id IS NULL THEN 'MISSING_CUSTOMER'
            ELSE 'MATCHED_CUSTOMER' END AS customer_status
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
LEFT JOIN payment_summary AS p ON p.order_id = o.order_id
ORDER BY o.order_id;
```

Expected report:

| Order | Customer | Order amount | Payments | Paid | Due | Customer status |
|---|---|---:|---:|---:|---:|---|
| 101 | 1 | 40.00 | 2 | 40.00 | 0.00 | MATCHED_CUSTOMER |
| 102 | 1 | 30.00 | 1 | 30.00 | 0.00 | MATCHED_CUSTOMER |
| 103 | 2 | 20.00 | 1 | 15.00 | 5.00 | MATCHED_CUSTOMER |
| 104 | 3 | 10.00 | 0 | 0.00 | 10.00 | MATCHED_CUSTOMER |
| 105 | 99 | 15.00 | 1 | 15.00 | 0.00 | MISSING_CUSTOMER |

The customer name for order 105 is NULL, not a real customer. This report is a snapshot of the synthetic fixture; real payment statuses require business-approved refund, chargeback, currency, and cutoff-time rules.

## 5. Reconciliation and anti-join diagnostics (5 minutes)

```sql
-- Orders with invalid customer references (portable anti-join):
SELECT o.order_id, o.customer_id
FROM orders AS o
WHERE NOT EXISTS (
  SELECT 1 FROM customers AS c WHERE c.customer_id = o.customer_id
);
-- Expected: order 105, customer_id 99.

-- Payments not linked to an order:
SELECT p.payment_id
FROM payments AS p
WHERE NOT EXISTS (
  SELECT 1 FROM orders AS o WHERE o.order_id = p.order_id
);
-- Expected: zero rows.
```

Compare source and report row counts and `SUM(order_amount)` before acceptance. Check `COUNT(DISTINCT order_id)` equals report row count and no `order_id` appears twice. Avoid `SUM(DISTINCT order_amount)`: different orders can share the same amount.

## 6. Executable hands-on lab (20 minutes)

**Isolation requirement:** Run only in a disposable PostgreSQL **18** database named `sql_tutorials` with nonproduction credentials. The SQL file performs a database/version check, sets transaction-local timeouts, creates temporary tables, inserts fictional fixtures, executes the consolidated report, checks deterministic assertions, and ends with `ROLLBACK`. It does **not** change permanent application tables. Database-name checks are defense in depth, not proof that a server is nonproduction; verify endpoint and credentials yourself.

From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/050-lab-05-consolidate-customers-orders-payments.sql
```

Run the complete script unchanged first. The script's `DO` assertion raises an exception if counts, sums, customer coverage, payment coverage, output uniqueness, or balances differ from the expected values. The success notice is **expected output only until a real PostgreSQL 18 run is recorded**.

Exercises: (A) predict the result of replacing the customer LEFT JOIN with INNER JOIN; (B) predict the raw order/payment join's incorrect order sum; (C) explain why payment preaggregation preserves order grain; (D) add a sixth *temporary* order and adjust acceptance assertions only in a disposable copy; (E) design a read-only reconciliation query for the source/report totals.

## 7. Expected acceptance metrics (5 minutes)

| Metric | Expected |
|---|---:|
| Customers / orders / payments | 3 / 5 / 5 |
| Source order total / source payment total | 115.00 / 100.00 |
| Raw LEFT JOIN order-payment rows | 6 |
| Incorrect raw-join order sum | 155.00 |
| Final report rows / distinct order IDs | 5 / 5 |
| Report order total / paid total / due total | 115.00 / 100.00 / 15.00 |
| Orders with no payment / partial payment | 1 / 1 |
| Orders with missing customer / orphan payments | 1 / 0 |
| Customer-matched orders / orders with payments | 4 / 4 |

These are **predictions**, not observed PostgreSQL 18 runtime results. Record server version, execution command, stdout/stderr, process exit code, and rollback confirmation for actual runtime certification.

## 8. Troubleshooting and DBRE/SRE guardrails (5 minutes)

- **Report has six rows:** payments were joined before aggregation; check `GROUP BY order_id` in the payment summary.
- **Order 104 or 105 disappears:** check for an INNER JOIN or right-table filter in `WHERE`; preserve orders as the left source.
- **Totals exceed 115.00:** look for duplicated order amounts from payment fan-out; reconcile at order grain.
- **Payment totals mismatch:** check missing payment records, duplicate payment IDs, refund semantics, and payment cutoff rules before interpreting discrepancies.
- **Version/database guard fails:** stop; do not bypass it or run against a shared/production endpoint.
- **Timeout or assertion failure:** investigate in a disposable database, do not disable safety controls to force a pass.

Operational acceptance requires a source-to-report reconciliation, row-grain uniqueness, orphan counts, a named reviewer, and retained runtime evidence. Avoid production credentials, sensitive customer data, and persistent schema changes.

## 9. Review questions and answers (5 minutes)

1. **Why LEFT JOIN from orders?** To retain unpaid orders and orders with missing customer records.
2. **Why preaggregate payments?** Multiple payments per order otherwise duplicate order amounts.
3. **What is the correct report grain?** Exactly one row per `order_id`.
4. **How many source orders have no payment?** One: order 104.
5. **What is the correct total outstanding balance?** 15.00.
6. **What does a NULL customer name on order 105 indicate?** A missing referenced customer, not a zero-valued customer.
7. **Why is `SUM(DISTINCT order_amount)` not a reliable fix?** Two distinct orders can have identical amounts.
8. **Does a successful static review prove PostgreSQL 18 compatibility?** No. Actual isolated execution with evidence is required.

## 10. Dialect portability notes

The SELECT/CTE pattern is portable across modern PostgreSQL, SQL Server, Oracle, Snowflake, BigQuery, and MySQL 8+. PostgreSQL-specific lab features include `DO $$ ... $$`, `RAISE EXCEPTION`, `CREATE TEMP TABLE ... ON COMMIT DROP`, `SET LOCAL`, `current_setting`, and psql's `\\set`. SQL Server uses different procedural error syntax; MySQL temporary-table lifecycle and timeout controls differ; Snowflake/BigQuery use their own scripting and temporary-object rules. Do not copy the executable PostgreSQL harness into another engine unchanged.

## 11. References

- [PostgreSQL 18 — Table expressions and joins](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — WITH queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL 18 — psql](https://www.postgresql.org/docs/18/app-psql.html)

## 12. Completion and next milestone

Part 05 closes with an order-grain report, synthetic fixtures, expected assertions, and a rollback-only PostgreSQL 18 lab. **Authored/published is not equivalent to independently reviewed or runtime-validated.** Continue with [Chapter 051 — COUNT, SUM, AVG, MIN, and MAX](../MASTER-TOC.md) in Part 06.
