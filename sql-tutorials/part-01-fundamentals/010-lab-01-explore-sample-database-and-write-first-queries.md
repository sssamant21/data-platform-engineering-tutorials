# Chapter 010 — Lab 01: Explore the Sample Database and Write First Queries

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 009](009-data-types-null-and-explicit-type-conversion.md) · Next: Chapter 011 (planned)  
> **Duration:** 60 minutes · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Platform:** isolated PostgreSQL 18  
> **Publication status:** Authored; independent editorial review and actual PostgreSQL 18 execution pending.

## Outcomes and prerequisites (0–5 minutes)

By the end you can identify your connected database and version, read a synthetic retail dataset, select explicit columns, calculate order values, filter NULLs, summarize counts, and explain why SQL results need explicit ordering. Review [Chapters 003](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md), [007](007-select-fundamentals-retrieve-rows-and-columns.md), and [009](009-data-types-null-and-explicit-type-conversion.md). This capstone integrates Part 01 rather than duplicating its lessons.

| Minutes | Activity | Evidence |
|---|---|---|
| 0–5 | Confirm isolated lab | Database/version assertion |
| 5–15 | Relational model and portable SQL | Explain grain and keys |
| 15–30 | Worked examples | Predict result rows |
| 30–50 | Guided hands-on lab | Five queries and acceptance checks |
| 50–55 | Troubleshoot and safety | Identify failure modes |
| 55–60 | Review | Answer key |

## 1. Model and safety (5–15 minutes)

Our **synthetic retail** model has three customers (customer_id, customer_name, email), four orders (order_id, customer_id, order_date, status), and five order lines (order_id, product_name, quantity, unit_price). Each customer has a unique ID; each order references one customer; order lines may repeat order IDs. The **grain** of customers is one row per customer, orders one row per order, and order_lines one row per product line. Joining orders to lines can increase row count: this is normal one-to-many fan-out, not automatically duplicate data.

The lab defines these datasets inside SQL using `WITH ... VALUES`; **no permanent sample database objects are created**. The lab is read-only and must run only in the disposable `sql_tutorials` database on PostgreSQL 18. The environment guard checks both the name and major version, but a matching name/version alone does **not** prove the host is non-production: verify your Docker endpoint and connection identity yourself. Never use production credentials.

**Portable concepts:** SELECT, FROM, WHERE, JOIN, GROUP BY, ORDER BY, CAST, COUNT and SUM. **PostgreSQL-specific lab mechanics:** `current_database()`, `current_setting()`, `::` casts, `BEGIN READ ONLY`, and the division-by-zero guard. SQL implementations differ in CTE/VALUES typing, date literal syntax and display formatting.

## 2. Walkthroughs and expected results (15–30 minutes)

### A. List customers in stable order

```sql
WITH customers(customer_id, customer_name, email) AS (
 VALUES (1, 'Ava', 'ava@example.invalid'),
        (2, 'Ben', NULL),
        (3, 'Chen', 'chen@example.invalid')
)
SELECT customer_id, customer_name, email
FROM customers ORDER BY customer_id;
```

Expected rows: `1 | Ava | ava@example.invalid`, `2 | Ben | NULL`, `3 | Chen | chen@example.invalid`. Without ORDER BY, presentation order is not guaranteed.

### B. Filter for missing email

```sql
WITH customers(customer_id, customer_name, email) AS (
 VALUES (1, 'Ava', 'ava@example.invalid'), (2, 'Ben', NULL),
        (3, 'Chen', 'chen@example.invalid')
)
SELECT customer_id FROM customers WHERE email IS NULL;
```

Expected: one row, customer 2. `email = NULL` is incorrect because it evaluates to UNKNOWN.

### C. Calculate an order-line amount

```sql
SELECT CAST(2 AS NUMERIC(10,2)) * CAST(12.50 AS NUMERIC(10,2))
       AS line_total;
```

Expected `25.00`. Exact NUMERIC arithmetic is preferred for this introductory monetary example; actual payment systems need currency and rounding policies.

### D. Order totals and cardinality

The lab joins orders to order_lines on `order_id`, then groups by `order_id`. Synthetic lines are:

| Order | Product | Quantity | Unit price | Extended |
|---|---|---:|---:|---:|
| 101 | Notebook | 2 | 12.50 | 25.00 |
| 101 | Pen | 3 | 2.00 | 6.00 |
| 102 | Bag | 1 | 30.00 | 30.00 |
| 103 | Notebook | 1 | 12.50 | 12.50 |
| 104 | Pen | 2 | 2.00 | 4.00 |

Expected order totals: 101 = 31.00, 102 = 30.00, 103 = 12.50, 104 = 4.00; **grand total = 77.50**. There are four orders but five order lines. Always name the grain of an aggregate before interpreting its count.

## 3. Guided lab (30–50 minutes)

Run [010-lab-01-explore-sample-database.sql](../labs/010-lab-01-explore-sample-database.sql) from the repository root, using the isolated PostgreSQL 18 setup from Chapter 003:

```powershell
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/010-lab-01-explore-sample-database.sql
```

Before running, inspect `psql` connection parameters (`\conninfo` interactively) and confirm the local disposable Docker endpoint. The script checks database name and major version, opens a read-only transaction, uses only in-query synthetic data, and rolls back. Run these tasks and compare with the expected results:

1. **Environment:** verify PostgreSQL major 18 and database `sql_tutorials`; expected guard `1`.
2. **Projection:** list three customers in ID order; expected IDs 1, 2, 3.
3. **NULL:** identify the one missing email; expected customer 2.
4. **Calculated columns:** list five line totals; expected 25.00, 6.00, 30.00, 12.50, 4.00 in line-ID order.
5. **Joins and aggregation:** calculate four order totals; expected 31.00, 30.00, 12.50, 4.00.
6. **Acceptance:** compare counts, missingness and total; expected `acceptance_assertion = 1`. With `ON_ERROR_STOP=1`, any failed assertion stops execution.

**Stretch exercise:** find customer names with at least one order. Expected Ava and Ben; Chen has no orders. Compare INNER JOIN with LEFT JOIN, noting that LEFT JOIN preserves Chen.

**Evidence for runtime acceptance:** save command, timestamp, exact file commit, PostgreSQL server version, isolated endpoint/database identity, stdout/stderr, exit code, and any corrections under a future validation artifact. The printed expected outputs are not evidence of execution.

## 4. Troubleshooting and operational guardrails (50–55 minutes)

| Symptom | Explanation | Safe action |
|---|---|---|
| Database/version assertion fails | Wrong target or PostgreSQL major | Stop; verify disposable connection, do not bypass guard |
| `psql` connection refused | Container stopped, port mismatch | Inspect local Docker state and Chapter 003 instructions |
| More than four rows after join | One-to-many order lines | Aggregate at order grain before interpreting totals |
| NULL email not returned | Used `= NULL` | Use `IS NULL` |
| Totals differ | Wrong join or integer/float arithmetic | Inspect individual lines; use exact NUMERIC |
| Different row order | ORDER BY omitted | Sort by stable unique key |
| Permission denied | Wrong account or database | Use lab-only account; do not elevate production access |

**Data engineering:** use explicit schema contracts and reconciliation counts to catch missing or duplicated records. **DBRE/SRE:** avoid running tutorial queries against production, especially ad-hoc joins or unbounded scans. The example dataset is tiny; do not extrapolate performance to real workloads. No DELETE, UPDATE, CREATE or DROP is required.

## 5. Review questions and answers (55–60 minutes)

1. What is the grain of `order_lines`? **One row per order line.**
2. Why can a join return more rows than the orders table? **Each order can match multiple lines.**
3. Why explicitly sort? **SQL does not guarantee result order without ORDER BY.**
4. Which predicate finds missing emails? **`IS NULL`.**
5. How many orders and lines are in this dataset? **Four orders and five lines.**
6. What is the grand total? **77.50.**
7. Does `BEGIN READ ONLY` prove the connection is non-production? **No; verify the endpoint independently.**
8. What counts as runtime validation? **Actual isolated PostgreSQL 18 execution with retained, reproducible evidence.**

## References and next chapter

- [PostgreSQL 18 SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 WITH Queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 Table Expressions and Joins](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL 18 psql](https://www.postgresql.org/docs/18/app-psql.html)

**Part 01 complete (authorship only). Next: Chapter 011 — WHERE and Comparison Operators**, beginning Part 02. Independent editorial and isolated PostgreSQL 18 runtime validation remain pending.
