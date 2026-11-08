# Chapter 007 — SELECT Fundamentals: Retrieve Rows and Columns

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 006](006-anatomy-of-sql-statement-and-logical-query-processing.md) · Next: 008 — Aliases, expressions, literals, and calculated columns (planned)  
> **Audience:** Beginner analysts, data engineers, application engineers, DBREs/SREs · **Duration:** 60 minutes · **Lab target:** PostgreSQL 18  
> **Status:** Published content; independent editorial review and PostgreSQL 18 runtime execution pending.

## Outcomes and lesson plan

By the end, you can retrieve named columns and all columns, explain how `SELECT` relates to `FROM`, use `WHERE` to select records, choose a deterministic display order, and recognize when a query may be unsafe or costly in production.

| Minutes | Activity | Result |
|---:|---|---|
| 0–5 | Context, prerequisites, safety | Identify the isolated lab |
| 5–15 | SELECT syntax and result shape | Understand projection and selection |
| 15–30 | Five worked examples | Predict columns, rows and order |
| 30–50 | Hands-on lab and assertions | Run and check read-only queries |
| 50–55 | Troubleshooting and DBRE/SRE notes | Recognize common mistakes |
| 55–60 | Knowledge check | Explain outcomes independently |

**Prerequisites:** [Chapter 003 — PostgreSQL 18 Docker lab](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [Chapter 004 — tables and columns](004-databases-schemas-tables-rows-columns.md), and [Chapter 006 — query anatomy](006-anatomy-of-sql-statement-and-logical-query-processing.md). The examples use a fictional in-query dataset; no permanent table creation or real customer records are needed.

## 1. What SELECT does (10 minutes)

`SELECT` returns a result set. The expressions following `SELECT` define **which columns** appear (relational *projection*). `FROM` supplies the rows, often from a table or a common table expression (CTE). `WHERE` optionally chooses **which rows** remain (relational *selection*). `ORDER BY` controls result order.

```sql
SELECT order_id, customer_name
FROM orders
WHERE status = 'paid'
ORDER BY order_id;
```

This is illustrative syntax for a hypothetical `orders` table. **Do not run it unchanged** unless your lab has that table. The runnable examples below use `WITH ... VALUES` to provide a safe in-query `orders` relation.

A query result is a table-shaped collection, but **SQL does not guarantee row order without `ORDER BY`**, even if repeated runs appear stable.

### Syntax essentials

| Clause | Question answered | Example |
|---|---|---|
| `SELECT` | Which output expressions? | `order_id, customer_name` |
| `FROM` | Which input relation? | `orders` |
| `WHERE` | Which rows qualify? | `status = 'paid'` |
| `ORDER BY` | How should rows be displayed? | `order_id` |
| `*` | Which columns? | All columns in the input relation |

The SQL keywords are case-insensitive in PostgreSQL; conventionally uppercase keywords improve readability. SQL string literals use single quotes. Avoid `SELECT *` for long-lived application contracts: schema changes can unexpectedly alter the result shape and transfer unnecessary data.

## 2. Our fictional orders dataset (5 minutes)

The same six rows are used in every example.

| order_id | customer_name | amount_usd | status |
|---:|---|---:|---|
| 7001 | Ava | 120.00 | paid |
| 7002 | Noah | 75.00 | pending |
| 7003 | Mia | 40.00 | paid |
| 7004 | Ava | 60.00 | paid |
| 7005 | Leo | 15.00 | cancelled |
| 7006 | Mia | 90.00 | pending |

The examples use `WITH orders (...) AS (VALUES ...)`. This CTE exists only for its query and is **not** a stored table. PostgreSQL's `::numeric(10,2)` is a PostgreSQL-specific cast; `CAST(... AS DECIMAL(10,2))` is the more portable syntax. CTEs and `VALUES` are widely supported, but dialect details vary.

## 3. Worked SELECT examples (15 minutes)

### A — Select a literal without FROM

```sql
SELECT 'hello, SQL' AS message, 7 * 6 AS answer;
```

**Expected:** one row with `hello, SQL` and `42`. PostgreSQL allows `SELECT` without `FROM`; Oracle traditionally uses `FROM DUAL` for similar expressions.

### B — Return all columns

```sql
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES
    (7001, 'Ava', 120.00::numeric(10,2), 'paid'),
    (7002, 'Noah', 75.00::numeric(10,2), 'pending'),
    (7003, 'Mia', 40.00::numeric(10,2), 'paid'),
    (7004, 'Ava', 60.00::numeric(10,2), 'paid'),
    (7005, 'Leo', 15.00::numeric(10,2), 'cancelled'),
    (7006, 'Mia', 90.00::numeric(10,2), 'pending')
)
SELECT *
FROM orders
ORDER BY order_id;
```

**Expected:** 6 rows, 4 columns, IDs 7001–7006 in order. `SELECT *` is useful for small exploration, but name only required columns in production-facing queries.

### C — Return named columns

```sql
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES
    (7001, 'Ava', 120.00::numeric(10,2), 'paid'),
    (7002, 'Noah', 75.00::numeric(10,2), 'pending'),
    (7003, 'Mia', 40.00::numeric(10,2), 'paid'),
    (7004, 'Ava', 60.00::numeric(10,2), 'paid'),
    (7005, 'Leo', 15.00::numeric(10,2), 'cancelled'),
    (7006, 'Mia', 90.00::numeric(10,2), 'pending')
)
SELECT order_id, customer_name
FROM orders
ORDER BY order_id;
```

**Expected:** 6 rows, exactly 2 columns. Explicit projection reduces result width and makes the output contract clear.

### D — Return paid rows only

```sql
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES
    (7001, 'Ava', 120.00::numeric(10,2), 'paid'),
    (7002, 'Noah', 75.00::numeric(10,2), 'pending'),
    (7003, 'Mia', 40.00::numeric(10,2), 'paid'),
    (7004, 'Ava', 60.00::numeric(10,2), 'paid'),
    (7005, 'Leo', 15.00::numeric(10,2), 'cancelled'),
    (7006, 'Mia', 90.00::numeric(10,2), 'pending')
)
SELECT order_id, customer_name, amount_usd
FROM orders
WHERE status = 'paid'
ORDER BY order_id;
```

**Expected:** IDs **7001, 7003, 7004**, with amounts 120.00, 40.00, 60.00. Filtering is introduced here; Chapter 011 covers predicate logic in depth.

### E — Ask a simple reporting question

```sql
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES
    (7001, 'Ava', 120.00::numeric(10,2), 'paid'),
    (7002, 'Noah', 75.00::numeric(10,2), 'pending'),
    (7003, 'Mia', 40.00::numeric(10,2), 'paid'),
    (7004, 'Ava', 60.00::numeric(10,2), 'paid'),
    (7005, 'Leo', 15.00::numeric(10,2), 'cancelled'),
    (7006, 'Mia', 90.00::numeric(10,2), 'pending')
)
SELECT COUNT(*) AS paid_order_count, SUM(amount_usd) AS paid_revenue_usd
FROM orders
WHERE status = 'paid';
```

**Expected:** `3 | 220.00`. Aggregates summarize rows instead of returning each row individually. Aggregation gets its own detailed treatment in Part 06.

## 4. Hands-on lab (20 minutes)

**Script:** [labs/007-select-fundamentals.sql](../labs/007-select-fundamentals.sql).

**Safety:** Use only the disposable `sql_tutorials` database from Chapter 003, not a shared, staging, or production database. The script checks PostgreSQL major version 18 and database name, begins a read-only transaction, uses only synthetic CTE data, and ends with `ROLLBACK`.

From the repository's `sql-tutorials/` directory, with an authenticated `psql` session pointed at the isolated lab:

```powershell
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f labs/007-select-fundamentals.sql
```

If using Docker, follow the connection commands in Chapter 003 instead of assuming a local `psql` installation. **Expected:** environment check succeeds; exercises A–E show the results above; the final assertion returns `pass` and no SQL errors.

**Exercises:**

1. Run the script and identify the number of columns returned by B versus C.
2. Change Example D's `WHERE status = 'paid'` to `WHERE status = 'pending'` in your own scratch copy. Predict **7002 and 7006** before executing it.
3. In a scratch copy of Example C, remove `ORDER BY`. Notice that any displayed order is *not* a guaranteed contract.
4. Change the column list in C to `SELECT customer_name, order_id`. Observe that column order in the output follows the `SELECT` list.
5. Check that Example E's total excludes pending and cancelled orders.

**Acceptance:** B has 6 rows and 4 columns; C has 6 rows and 2 columns; D has 3 rows; E reports 3 and 220.00; changing the predicate to pending returns two rows. The provided lab has machine-checkable assertions for those invariants.

## 5. Troubleshooting, production safety and portability (5 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| `relation "orders" does not exist` | You ran the illustrative query without its CTE | Run the complete runnable example |
| `column ... does not exist` | Misspelled or omitted column name | Compare against the four CTE column names |
| Unexpected row order | Missing `ORDER BY` | Specify deterministic sort keys |
| Too many result columns | `SELECT *` used | Enumerate only required columns |
| Connection or environment assertion fails | Wrong database/server or missing lab | Follow Chapter 003; never bypass the guard to run against production |
| Script stops at assertion | Expected output differs | Inspect earlier result rows; do not change assertion merely to silence it |

**DBRE/SRE perspective:** A read-only `SELECT` is not necessarily cheap. On large production tables it can scan many pages, consume CPU, create temporary files, and increase load. Limit data exposure, use least-privilege roles, and review execution plans before high-impact queries. A `LIMIT` can reduce returned rows, but does not universally guarantee cheap execution; learn `EXPLAIN` in Chapter 091.

**Dialect notes:** `SELECT`, named columns, `FROM`, and `WHERE` are widely portable. PostgreSQL-specific `::numeric` can be replaced with standard `CAST`; `ORDER BY` is needed for deterministic results across engines. A no-`FROM` expression differs among platforms.

## 6. Knowledge check (5 minutes)

1. What is the difference between choosing columns and choosing rows?
2. Why might `SELECT *` be risky in a long-lived application query?
3. Is the result order guaranteed without `ORDER BY`?
4. Which IDs appear in the paid-orders query?
5. Can a read-only query still impact database performance?

**Answer key:** (1) `SELECT` chooses output expressions; `WHERE` filters rows. (2) Unexpected columns, more data transferred, fragile contracts. (3) No. (4) 7001, 7003, 7004. (5) Yes, because scans and computation consume resources.

**Next:** Chapter 008 — Aliases, Expressions, Literals, and Calculated Columns.

## Authoritative references

- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Querying a Table](https://www.postgresql.org/docs/18/tutorial-select.html)
- [PostgreSQL 18 — VALUES](https://www.postgresql.org/docs/18/sql-values.html)

**Validation record:** Expected results and read-only safeguards reviewed statically. **PostgreSQL 18 runtime execution and independent editorial review remain pending.**
