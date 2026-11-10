# 047 — One-to-many and Many-to-many Relationships

**Part 05 — Joins & Relational Query Patterns** · **Duration:** 60 minutes · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Baseline:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Chapter 046](046-multi-table-joins-and-join-condition-design.md) · [Lab 047](../labs/047-one-to-many-many-to-many.sql)

## 1. Objectives and timing (5 minutes)

Explain one-to-many (1:N) and many-to-many (M:N) relationships; identify primary, foreign and composite keys; predict join output grain; avoid duplicated metrics; verify orphan and duplicate associations; and apply safe PostgreSQL 18 lab practices.

**60-minute plan:** objectives 5; relationship models 10; queries 15; reconciliation 10; lab 15; review 5.

## 2. Scenario: customers, orders, and product tags (5 minutes)

A synthetic retailer has customers (one row per customer), orders (many per customer), products (one row per product), tags (one row per tag), and product_tags (one row per product/tag pair). Customer-to-order is **1:N**. Product-to-tag is **M:N**, implemented using a junction/bridge table. A product may have several tags; a tag may describe several products.

**Grain** means what a single output row represents. A customer-order join returns one row per matched order, not one row per customer. A product-tag join returns one row per association, not one row per product. Always document grain before counting or summing.

## 3. Keys and constraints (5 minutes)

Portable relational design:

```sql
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, customer_name VARCHAR(80) NOT NULL);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id), amount DECIMAL(12,2) NOT NULL);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, product_name VARCHAR(80) NOT NULL);
CREATE TABLE tags (tag_id INTEGER PRIMARY KEY, tag_name VARCHAR(80) NOT NULL UNIQUE);
CREATE TABLE product_tags (
  product_id INTEGER NOT NULL REFERENCES products(product_id),
  tag_id INTEGER NOT NULL REFERENCES tags(tag_id),
  PRIMARY KEY (product_id, tag_id)
);
```

The junction table's composite primary key prevents duplicate pairs. Foreign keys reject nonexistent product/tag references; in some systems constraints are optional or unenforced, so ingestion reconciliation still matters. The DDL above is conceptual: execute it only in an isolated disposable database. The accompanying lab uses temporary tables and rollback.

## 4. One-to-many joins (5 minutes)

```sql
SELECT c.customer_id, c.customer_name, o.order_id, o.amount
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
ORDER BY c.customer_id, o.order_id;
```

With Ana's two orders, Ben's one, and Cleo's none, the LEFT JOIN returns **four rows**: Ana twice, Ben once, Cleo once with NULL order fields. An INNER JOIN would return **three rows**, omitting Cleo. The LEFT JOIN's unmatched row is a placeholder, not an actual order.

## 5. Many-to-many joins (10 minutes)

```sql
SELECT p.product_id, p.product_name, t.tag_name
FROM products AS p
JOIN product_tags AS pt ON pt.product_id = p.product_id
JOIN tags AS t ON t.tag_id = pt.tag_id
ORDER BY p.product_id, t.tag_name;
```

Synthetic associations: Keyboard → Office, Tech; Mouse → Tech; Notebook → Office. The join returns **four rows** across **three products**. Counting rows counts *associations*. For products per tag, group by tag ID; for tags per product, group by product ID. Use `COUNT(DISTINCT p.product_id)` when a report truly needs unique products, but do not use DISTINCT to conceal bad join conditions.

```sql
SELECT t.tag_name, COUNT(pt.product_id) AS product_count
FROM tags AS t
LEFT JOIN product_tags AS pt ON pt.tag_id = t.tag_id
GROUP BY t.tag_id, t.tag_name
ORDER BY t.tag_name;
```

Expected: Office=2, Tech=2. A tag with no associations would still appear with count zero. `COUNT(pt.product_id)` excludes the unmatched NULL; `COUNT(*)` would incorrectly count the placeholder as one.

## 6. Reconciliation and avoiding fan-out (10 minutes)

For a customer-level order report, aggregate orders *before* joining another child table:

```sql
WITH order_totals AS (
  SELECT customer_id, COUNT(*) AS order_count, SUM(amount) AS total_amount
  FROM orders GROUP BY customer_id
)
SELECT c.customer_id, COALESCE(ot.order_count,0) AS order_count,
       COALESCE(ot.total_amount,0) AS total_amount
FROM customers AS c
LEFT JOIN order_totals AS ot ON ot.customer_id = c.customer_id
ORDER BY c.customer_id;
```

For orders 101=30.00 and 102=20.00 (Ana), 103=15.00 (Ben), expected customer totals are Ana 2/50.00, Ben 1/15.00, Cleo 0/0.00; grand total 65.00. Joining order rows to an unrelated many-to-many association before summing can multiply monetary values. Compare source totals with output totals and test unique keys at the intended grain. For a bridge table, check `COUNT(*)` versus `COUNT(DISTINCT (product_id,tag_id))` in PostgreSQL; portable alternatives group by both keys.

## 7. Hands-on isolated PostgreSQL 18 lab (15 minutes)

Run [047-one-to-many-many-to-many.sql](../labs/047-one-to-many-many-to-many.sql) on a **disposable** PostgreSQL 18+ instance with database `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/047-one-to-many-many-to-many.sql
```

The script guards version/database/standby status, uses transaction-local timeouts, creates only temporary tables, asserts exact counts/totals and ends with `ROLLBACK`. Expected PASS: customers=3, orders=3, left_join_rows=4, order_total=65.00, products=3, tags=2, associations=4, duplicates=0. These are **predicted** results, not observed runtime evidence.

**Practice:** (A) Change the customer LEFT JOIN to INNER JOIN and explain the missing row. (B) Count products per tag; verify Office=2 and Tech=2. (C) Remove a junction association in the disposable transaction and predict the new count; restore the original fixture by rerunning the lab. (D) Explain why joining a monetary fact to product tags can inflate totals.

## 8. Portability and operations (3 minutes)

`JOIN`, `LEFT JOIN`, `GROUP BY`, `COUNT`, and composite keys are broadly portable SQL concepts. PostgreSQL-specific lab features include `DO` blocks, `RAISE EXCEPTION`, `SET LOCAL`, `CREATE TEMP TABLE ... ON COMMIT DROP`, `pg_is_in_recovery()`, and version settings. SQL Server, Snowflake, BigQuery, SQLite and MySQL have differing temporary-table, procedural assertion, transaction and constraint semantics. Validate each target dialect rather than copying the PostgreSQL harness.

DBRE/SRE safeguards: check query plans on large bridge tables, consider indexes on foreign-key columns, track join fan-out, enforce uniqueness where supported, and investigate missing references. Do not disable constraints or run training DDL against production.

## 9. Troubleshooting (2 minutes)

**Unexpected duplicates:** verify the join keys and bridge uniqueness; confirm whether multiple associations are legitimate. **Missing customers:** INNER JOIN excludes parents without children; use LEFT JOIN if preserving parents is required. **Wrong totals:** aggregate at the correct grain before joining to another 1:N relation. **Foreign-key errors:** insert parents before children and check IDs. **Lab guard fails:** confirm isolated database name and PostgreSQL 18+; never bypass the guard in production.

## 10. Review questions and answers (5 minutes)

1. **Why is customer→orders 1:N?** One customer can own multiple orders; each order references one customer.
2. **How is M:N represented relationally?** With a bridge table holding foreign keys to both entities.
3. **What prevents duplicate product/tag pairs?** A composite primary key on `(product_id,tag_id)`.
4. **Why can `COUNT(*)` miscount after LEFT JOIN?** It counts the NULL-extended unmatched row.
5. **Why preaggregate before joining multiple child tables?** To prevent child-row multiplication from inflating totals.
6. **Does a published SQL file prove PostgreSQL 18 correctness?** No; isolated execution and retained evidence are required.

## 11. Safety and acceptance

Only synthetic records; no credentials or production endpoints. The lab is rollback-only and deliberately fails closed outside its expected PostgreSQL 18 database. Check expected counts, totals, association uniqueness and rollback; capture server version, command, exit code and SQL output for any later runtime acceptance. **Status at publication: authored, targeted static reasoning; independent editorial review, comprehensive syntax/link QA, and PostgreSQL 18 runtime validation pending.**

## 12. References and next step

- [PostgreSQL 18 — Table Expressions / Joined Tables](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- Next in the [Master TOC](../MASTER-TOC.md): **048 — Semi-joins and anti-joins using EXISTS and NOT EXISTS**.
