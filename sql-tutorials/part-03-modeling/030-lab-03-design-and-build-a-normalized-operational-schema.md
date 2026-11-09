# 030 — Lab 03: Design and Build a Normalized Operational Schema

**Part 03 — Data Modeling, DDL & Constraints** · **Duration:** 60 minutes · **Audience:** beginner data engineers, DBREs, SREs · **Target:** isolated PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Previous: 029 — Normalization](029-normalization-1nf-3nf-and-intentional-denormalization.md) · [SQL lab](../labs/030-lab-03-normalized-operational-schema.sql) · [Status](../STATUS-TRACKER.md)

> **Safety:** The SQL lab uses only synthetic retail data and temporary tables inside a rollback-only transaction. Run it **only** on a disposable PostgreSQL 18 instance in database `sql_tutorials`. The database name guard is not proof of isolation; verify host, container, user, and connection target before executing. Never use production credentials.

## Learning objectives and prerequisites (0–5 minutes)

By the end, you can identify entity grain, draw one-to-many relationships, choose primary/foreign/business keys, enforce `NOT NULL`, `UNIQUE` and `CHECK`, load parent-before-child rows, reconcile order totals without join fan-out, and explain operational migration risks.

Prerequisites: [021 relationships](021-entity-relationships-and-conceptual-data-modeling.md), [024 keys](024-primary-keys-natural-keys-surrogate-keys-and-unique.md), [025 foreign keys](025-foreign-keys-and-referential-integrity.md), [026 constraints](026-not-null-check-default-and-constraint-validation.md), and [029 normalization](029-normalization-1nf-3nf-and-intentional-denormalization.md). Familiarity with SELECT and JOIN is useful; queries are explained below.

## Model the business requirements (5–15 minutes)

A fictional retailer accepts orders from customers. Each order has one or more line items; a product may appear on many order lines. We need to preserve the **historical unit price at purchase time**, even if the current catalog price changes.

| Entity | Grain (one row represents) | Key | Business rule |
|---|---|---|---|
| Customer | One customer | `customer_id` | `customer_code` is unique |
| Product | One catalog product | `product_id` | `sku` is unique; price nonnegative |
| Order | One order header | `order_id` | `order_code` unique; customer required |
| Order item | One product line in an order | (`order_id`, `line_no`) | Product required; quantity positive; snapshot unit price nonnegative |

**Relationships:** Customer 1 → many Orders; Order 1 → many Order Items; Product 1 → many Order Items. The composite key makes `line_no` unique *within* an order, not across all orders. Order items implement the many-to-many relationship between orders and products. Foreign keys prevent orphan order items, but **do not enforce that every order has at least one line**; that cross-row business rule needs a controlled workflow or additional design.

This is a practical 3NF-oriented model: customer names are stored once, product descriptions are stored once, and order lines reference those entities. `unit_price_at_order` is intentionally a historical fact, not an accidental duplicate of `products.list_price`. A change to catalog price must not rewrite historical revenue.

## SQL design and portability (15–25 minutes)

The executable [PostgreSQL 18 lab](../labs/030-lab-03-normalized-operational-schema.sql) creates four temporary tables in dependency order and adds explicit constraints. Representative portable SQL:

```sql
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  customer_code VARCHAR(20) NOT NULL UNIQUE,
  customer_name VARCHAR(100) NOT NULL
);
```

The actual lab uses `CREATE TEMP TABLE` and PostgreSQL-specific transaction/guard mechanisms; the model's basic `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `UNIQUE`, and `CHECK` ideas are widely supported. Identity/autoincrement syntax, temporary-table lifetime, constraint naming, error codes, and transactional DDL behavior vary across PostgreSQL, MySQL, SQL Server, Oracle, Snowflake, and BigQuery. Do **not** copy this script into a different engine without adaptation.

**Why use explicit integer IDs?** Predictable synthetic IDs make results and acceptance checks reproducible. In a real system, surrogate-key generation and collision avoidance require separate design. **Why no `ON DELETE CASCADE`?** Order history should not disappear when a customer is removed; restrictive referential behavior is safer for this example. Privacy deletion requirements need an approved retention/anonymization design, not an ad hoc cascade.

## Walkthrough and expected outputs (25–35 minutes)

Load two customers, two products, two orders and three lines. The second order belongs to the first customer; the second customer has no orders. The line facts are:

| Order | Line | Product | Qty | Historical unit price | Extended amount |
|---|---:|---|---:|---:|---:|
| ORD-001 | 1 | SKU-A | 2 | 12.50 | 25.00 |
| ORD-001 | 2 | SKU-B | 1 | 30.00 | 30.00 |
| ORD-002 | 1 | SKU-A | 3 | 10.00 | 30.00 |

Expected: **2 customers, 2 products, 2 orders, 3 order lines**. Order totals: `ORD-001 = 55.00`, `ORD-002 = 30.00`. **Grand total = 85.00**. Customer C-001 owns both orders and 85.00 revenue; C-002 owns none.

```sql
SELECT o.order_code, SUM(i.quantity * i.unit_price_at_order) AS order_total
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
GROUP BY o.order_id, o.order_code
ORDER BY o.order_code;
```

The SQL above assumes the four tables exist in the current session's temporary schema. Aggregate at **order grain** before joining additional one-to-many entities (such as payments) or you may multiply revenue through fan-out. `SUM` of `NUMERIC` preserves decimal arithmetic; floating-point types are inappropriate for exact currency amounts. Currency conversion, tax, discounts and refunds are deliberately out of scope.

## Hands-on lab (35–50 minutes)

1. Start a **disposable** PostgreSQL 18 instance, using the isolated setup from [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Confirm its identity independently and use the dedicated `sql_tutorials` database.
2. Read the complete [lab SQL](../labs/030-lab-03-normalized-operational-schema.sql). It checks database/version/primary status, sets timeouts, creates temporary tables, inserts only fictional data, checks row counts and totals, and rolls back.
3. Run from repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/030-lab-03-normalized-operational-schema.sql
```

4. Inspect the displayed order totals and final `lab_acceptance` row: expected `PASS`. A failure should terminate with a nonzero exit when `ON_ERROR_STOP=1`.
5. **Practice A:** Predict the result if `ORD-001` line 2 had quantity 2: its total becomes **85.00**, grand total **115.00**. Change only a local copy, then adjust assertions.
6. **Practice B:** Explain why a duplicate (`order_id`, `line_no`) must fail: it violates the composite primary key.
7. **Practice C:** Describe a safe data migration from a flat CSV into this model: profile keys and nulls, deduplicate reference entities, load customers/products, load orders, then items; reconcile counts and monetary totals; quarantine invalid records.
8. **Practice D:** Explain how a new product list price should affect historical order lines: it must **not** change `unit_price_at_order`.

The lab uses PostgreSQL `DO` assertions and ends with `ROLLBACK`; no persistent tables are created. Transaction rollback is not a substitute for verifying you are connected to an isolated instance.

## Validation, troubleshooting, and DBRE/SRE guardrails (50–55 minutes)

| Symptom | Cause | Safe response |
|---|---|---|
| `23503` foreign-key error | Child references missing parent | Inspect ingestion order and source keys; quarantine bad rows |
| `23505` duplicate key | Duplicate business ID or line number | Investigate deduplication/idempotency; do not drop uniqueness |
| `23514` CHECK violation | Negative price or nonpositive quantity | Profile source records; fix upstream or quarantine |
| `42P01` relation missing | Temporary tables exist only in this session | Run full lab in one `psql` session |
| Wrong revenue | Join fan-out or current catalog price substituted | Aggregate order lines at correct grain and use historical price |
| Version/database assertion fails | Wrong instance/target | Stop; verify Docker endpoint and dedicated database |

**Operational controls:** Real schema deployment requires review of lock levels, long-running transactions, replication lag, storage/WAL headroom, backup/restore readiness, grants, data quality, application compatibility, change approval and rollback. Indexing foreign-key columns may improve operational performance; PostgreSQL does not automatically index every referencing column. For production, plan constraints and backfills with measured staging evidence rather than using this teaching script.

**Validation labels:** Published = GitHub file exists; targeted static inspection = manual review of syntax/links/expected arithmetic; independently editorially reviewed = separate reviewer sign-off; runtime validated = actually executed against isolated PostgreSQL 18 with retained reproducible logs. These are distinct.

## Review questions and answers (55–60 minutes)

1. **What is the order-items primary key?** (`order_id`, `line_no`).
2. **Why keep a historical unit price?** To preserve what was charged at transaction time even after catalog changes.
3. **Can a foreign key alone require every order to have at least one item?** No; it ensures child references are valid, not that a parent has children.
4. **Why not sum order headers after joining payments and lines?** Two one-to-many joins can multiply rows and inflate totals.
5. **Which order has total 55.00?** `ORD-001`.
6. **How do we know the lab was actually runtime validated?** Only from a recorded PostgreSQL 18 execution with version, command, output, exit status and environment evidence—not from publication or manual reasoning.

## References and next chapter

- [PostgreSQL 18 — Table Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18 — Numeric Types](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [PostgreSQL 18 — Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [Master TOC](../MASTER-TOC.md)

**Next:** Chapter 031 — INSERT single-row and multi-row records (Part 04).
