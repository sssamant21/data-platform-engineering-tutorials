# 041 — Join Fundamentals and Relationship Cardinality

**Part 05: Joins & Relational Query Patterns** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE

**Prerequisites:** [Chapter 005 — keys and relationships](../part-01-fundamentals/005-records-relationships-keys-and-relational-terminology.md), [Chapter 025 — foreign keys](../part-03-modeling/025-foreign-keys-and-referential-integrity.md), and [Chapter 040 — transaction capstone](../part-04-data-modification/040-lab-04-complete-a-safe-auditable-transaction-workflow.md).

**Lab:** [041 — join cardinality and fan-out (SQL)](../labs/041-join-fundamentals-cardinality.sql). **Next:** Chapter 042 — INNER JOIN (planned; consult [Master TOC](../MASTER-TOC.md)).

## 1. Learning objectives (5 minutes)

After this lesson, you can explain relational joins, identify one-to-one and one-to-many relationships, predict joined row counts, choose a correct join key, spot unintended fan-out, and reconcile query results before using them in reporting or production troubleshooting.

## 2. The business question (5 minutes)

A synthetic retailer stores customers separately from orders. The application asks: *Which customer placed each order?* A join combines related rows without copying customer details into every order. In operational reporting, incorrect joins can double-count revenue or obscure missing parent records.

**Grain** means what one row represents. A customer table has one row per customer; an order table has one row per order. Joining a customer to multiple orders produces multiple rows for that customer; that is expected, not automatically a duplicate-data defect.

## 3. Join syntax and keys (10 minutes)

Portable SQL:

```sql
SELECT o.order_id, c.customer_name, o.amount
FROM orders AS o
INNER JOIN customers AS c
  ON o.customer_id = c.customer_id
ORDER BY o.order_id;
```

`INNER JOIN` returns matching pairs. `ON` specifies the relationship. The query is portable across PostgreSQL, MySQL, SQL Server, Oracle, Snowflake, and BigQuery, although identifier and type rules can vary. Use explicit `JOIN ... ON` rather than comma joins; a missing predicate can create a Cartesian product.

A primary key uniquely identifies a parent row. A foreign key expresses the child-to-parent relationship and, when enforced, prevents orphan references. A foreign key does **not** make the child key unique. Thus one customer can have many orders.

## 4. Walkthrough: synthetic retail data (10 minutes)

Use these conceptual tables:

| customers.customer_id | customer_name |
|---:|---|
| 1 | Ada |
| 2 | Ben |
| 3 | Cy |

| orders.order_id | customer_id | amount |
|---:|---:|---:|
| 101 | 1 | 20.00 |
| 102 | 1 | 30.00 |
| 103 | 2 | 15.00 |

The inner join returns **3 rows**: orders 101 and 102 belong to Ada, and order 103 belongs to Ben. Cy is absent because Cy has no orders. The sum of joined order amounts is **65.00**. There are **2 distinct purchasing customers**.

**Cardinality vocabulary:** one-to-one (each side at most one related row), one-to-many (one parent, several children), many-to-many (typically represented with a junction table). Join cardinality is a data property; the SQL engine does not infer your intended business grain from the query.

## 5. Understand fan-out before aggregating (5 minutes)

Suppose order 101 has two line items. Joining customers → orders → order_items repeats order 101 twice. Summing `orders.amount` over that three-table join overstates order revenue. First aggregate line items to one row per order, or compute order-level metrics from the orders table before joining.

**Do not use `DISTINCT` to hide an unexplained fan-out.** It may remove legitimate records and conceal a broken join predicate.

A useful preflight:

```sql
SELECT customer_id, COUNT(*) AS order_count
FROM orders
GROUP BY customer_id
ORDER BY customer_id;
```

Expected: customer 1 has 2 orders, customer 2 has 1. A join should preserve the **order grain** when each order joins to exactly one customer.

## 6. Hands-on lab (20 minutes)

Run [the accompanying SQL lab](../labs/041-join-fundamentals-cardinality.sql) only in a disposable **PostgreSQL 18** tutorial database (for example, `sql_tutorials`). It creates **temporary** tables within a transaction and rolls back. The lab verifies server version, database name, and non-recovery status before any DDL.

1. Inspect the three customer rows and three order rows.
2. Run the inner join; inspect the three matched order/customer pairs.
3. Run the left join; observe Cy's unmatched row and NULL order fields.
4. Verify order-grain reconciliation: three joined orders, 65.00 total, two purchasing customers.
5. Examine an order-line join that produces four rows, including fan-out for order 101.
6. Run the fail-closed assertions and confirm the final `ROLLBACK`.

Expected summary: **3 customers, 3 orders, 3 inner-join rows, 4 left-join rows, 4 order-line joined rows, 65.00 order revenue**. The left join has four rows because Ada has two orders, Ben one, and Cy one NULL-extended row.

**Lab command (psql):**

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/041-join-fundamentals-cardinality.sql
```

Run from the repository root and use only isolated lab credentials. Never point this command at a production database.

## 7. Troubleshooting and DBRE/SRE guardrails (5 minutes)

| Symptom | Likely cause | Check |
|---|---|---|
| Too many rows | Many-to-many fan-out or incomplete `ON` | Count keys on both sides; check uniqueness |
| Too few rows | `INNER JOIN` drops unmatched parents | Compare with `LEFT JOIN` and inspect NULL matches |
| Revenue inflated | Parent amount summed after child join | Aggregate at correct grain before joining |
| Unexpected NULL | Unmatched left row | Check foreign keys, filters, and join direction |
| Query slow | Large inputs or poor join-key access | Inspect `EXPLAIN` safely; later performance chapters cover tuning |

Use read-only previews for operational investigations. Avoid joining real patient or customer data into uncontrolled exports. Validate row counts, key uniqueness, and financial totals before approving an analytical result. `LEFT JOIN` followed by a right-table filter in `WHERE` can unintentionally behave like an inner join; understand predicate placement.

## 8. SQL portability

`INNER JOIN`, `LEFT OUTER JOIN`, `ON`, `COUNT`, `SUM`, and `GROUP BY` are broadly portable. The lab's `DO $$ ... $$`, `current_setting`, `pg_is_in_recovery()`, `CREATE TEMP TABLE ... ON COMMIT DROP`, and PL/pgSQL `RAISE EXCEPTION` are **PostgreSQL-specific**. The lab's rollback and guards are not a promise of identical behavior on other vendors.

## 9. Review questions and answers (5 minutes)

1. **Why does Ada appear twice?** Because Ada has two orders; output is one row per matched order.
2. **Does a foreign key make child values unique?** No; multiple orders can reference one customer.
3. **What happens to Cy in an inner join?** Cy has no matching order and is omitted.
4. **How can a join inflate revenue?** Joining order lines repeats the parent order amount.
5. **Should you add DISTINCT to fix any unexpected duplicate?** No; first identify the intended grain and incorrect cardinality.
6. **What should an SRE verify before trusting a report?** Join keys, cardinality, row counts, NULL handling, and aggregate reconciliation.

## 10. References and further learning

- [PostgreSQL 18 — Table Expressions / Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Foreign Keys](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Publication is not runtime certification.** Independent editorial review, comprehensive static checks, and actual PostgreSQL 18 execution with retained evidence are tracked separately.
