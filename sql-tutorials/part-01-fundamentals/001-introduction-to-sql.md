# Chapter 001 — Introduction to SQL: Purpose, Use Cases, and Stakeholder Roles

> **Learning path:** [SQL Tutorials](../README.md) · [Master TOC](../MASTER-TOC.md) · **Part 01: Fundamentals**  
> **Audience:** Beginners, analysts, application developers, data engineers, DBREs, and SREs  
> **Duration:** 60 minutes · **Reference database:** PostgreSQL 18  
> **Status:** Authored and published; independent review and PostgreSQL 18 runtime execution pending  
> **Prerequisites:** None for the concepts. A working PostgreSQL SQL editor or `psql` session is needed for the optional live lab. Chapter 003 covers setup.

## 1. Learning outcomes (5 minutes)

After this chapter, you should be able to:

1. Explain what SQL is and what a relational database does.
2. Describe the difference between tables, rows, and columns using an everyday example.
3. Identify common SQL workloads: querying, changing data, schema definition, permissions, and transactions.
4. Match SQL responsibilities to analysts, developers, data engineers, DBREs, and SREs.
5. Run four **read-only** PostgreSQL examples and check their results.

## 2. What is SQL? (10 minutes)

**Structured Query Language (SQL)** is a declarative language used to work with relational data. You describe the result or change you want; the database engine decides how to execute it.

- A **database** organizes stored data.
- A **database management system (DBMS)** such as PostgreSQL manages storage, querying, transactions, access control, and recovery.
- A **table** stores related records in **rows** and attributes in **columns**.
- A **query** asks the DBMS for a result.
- **SQL is not itself a database product:** PostgreSQL, SQL Server, MySQL, Oracle, and Snowflake each implement SQL with vendor-specific differences.

Example business question: *Which paid orders should appear in today's report?*

A conceptual retail table might look like this:

| order_id | customer_name | total_usd | status |
|---:|---|---:|---|
| 1001 | Ava | 120.00 | paid |
| 1002 | Noah | 75.00 | pending |
| 1003 | Ava | 40.00 | paid |
| 1004 | Mia | 60.00 | paid |

Here, `order_id` is a column, while `1001 / Ava / 120.00 / paid` is one row. In a real design, customers would normally live in a separate table and be linked by keys; data modeling is covered in Chapters 021–030.

### SQL command families

| Family | Purpose | Typical commands | Production caution |
|---|---|---|---|
| Data query | Read data | `SELECT` | Queries can still consume substantial resources or expose sensitive data |
| Data manipulation (DML) | Change rows | `INSERT`, `UPDATE`, `DELETE`, `MERGE` | Validate predicates, affected rows, and transactions |
| Data definition (DDL) | Define or change structures | `CREATE`, `ALTER`, `DROP` | Schema changes may lock objects or be destructive |
| Access control (DCL) | Control privileges | `GRANT`, `REVOKE` | Apply least privilege |
| Transaction control (TCL) | Manage transaction outcomes | `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT` | Understand implicit commits and dialect differences |

These are educational categories; exact commands and transaction behavior vary by vendor.

## 3. Where SQL is used (10 minutes)

| Use case | Example question | Primary benefit |
|---|---|---|
| Application operations | Find a customer's recent orders | Correct transactional reads and writes |
| Business intelligence | Report monthly paid revenue | Reproducible metrics |
| Data engineering | Transform and validate imported rows | Reliable pipelines |
| Synthetic healthcare reporting | Aggregate fictional encounter counts | Analytics without exposing real patient data |
| DBRE/SRE incident response | Find slow statements or blocking transactions | Faster, evidence-based diagnosis |
| Data quality | Find missing references or unexpected duplicates | Protect correctness |

**OLTP vs. OLAP:** Transactional systems typically prioritize short, reliable row-oriented operations. Analytical systems typically prioritize larger scans and aggregates. SQL serves both, but designs and performance considerations differ.

### Who owns what?

| Role | Common SQL responsibilities | Typical boundary |
|---|---|---|
| Analyst / BI engineer | Read-only reports, validated metrics | Do not directly modify production transactional data |
| Application engineer | Parameterized application queries, transaction logic, schema-change proposals | Coordinate high-impact migrations |
| Data engineer | ELT transforms, reconciliation, data quality | Observe source-of-truth ownership and retention |
| DBRE | Database performance, indexing advice, resilience, access and change safeguards | Collaborate with owning application/data teams |
| SRE / infrastructure | Monitoring, incident response, capacity, availability | Coordinate with DBRE and service owners |
| Security / governance | Access policy, sensitive data and audit controls | Review privileged access and masking |

Actual ownership is organization-specific; establish a RACI instead of assuming a universal split.

## 4. First SQL examples (15 minutes)

All examples below are **read-only** and require no table creation. A `WITH ... VALUES` expression creates an in-query sample dataset, not a persistent table. PostgreSQL-style numeric casts are shown explicitly.

### Example A — A first statement

```sql
SELECT 'SQL is working' AS message, 2 + 3 AS answer;
```

Expected result:

| message | answer |
|---|---:|
| SQL is working | 5 |

**Read it:** `SELECT` produces result columns; `AS` assigns human-readable output names; the semicolon ends the statement.

### Example B — Select rows from sample data

```sql
WITH orders (order_id, customer_name, total_usd, status) AS (
    VALUES
        (1001, 'Ava',  120.00::numeric(10,2), 'paid'),
        (1002, 'Noah',  75.00::numeric(10,2), 'pending'),
        (1003, 'Ava',   40.00::numeric(10,2), 'paid'),
        (1004, 'Mia',   60.00::numeric(10,2), 'paid')
)
SELECT order_id, customer_name, total_usd
FROM orders
ORDER BY order_id;
```

Expected rows: `1001 Ava 120.00`, `1002 Noah 75.00`, `1003 Ava 40.00`, `1004 Mia 60.00`.

`WITH` labels a reusable query result; `VALUES` provides rows; `FROM` identifies the source; `ORDER BY` provides a predictable display order. CTEs are revisited in Chapter 065.

### Example C — Filter to paid orders

```sql
WITH orders (order_id, customer_name, total_usd, status) AS (
    VALUES
        (1001, 'Ava',  120.00::numeric(10,2), 'paid'),
        (1002, 'Noah',  75.00::numeric(10,2), 'pending'),
        (1003, 'Ava',   40.00::numeric(10,2), 'paid'),
        (1004, 'Mia',   60.00::numeric(10,2), 'paid')
)
SELECT order_id, customer_name, total_usd
FROM orders
WHERE status = 'paid'
ORDER BY order_id;
```

Expected rows: **1001, 1003, 1004** (3 paid orders). `WHERE` removes rows that do not match the condition.

### Example D — Count and total paid orders

```sql
WITH orders (order_id, customer_name, total_usd, status) AS (
    VALUES
        (1001, 'Ava',  120.00::numeric(10,2), 'paid'),
        (1002, 'Noah',  75.00::numeric(10,2), 'pending'),
        (1003, 'Ava',   40.00::numeric(10,2), 'paid'),
        (1004, 'Mia',   60.00::numeric(10,2), 'paid')
)
SELECT
    COUNT(*) AS paid_order_count,
    SUM(total_usd) AS paid_revenue_usd
FROM orders
WHERE status = 'paid';
```

Expected result:

| paid_order_count | paid_revenue_usd |
|---:|---:|
| 3 | 220.00 |

**Why 220.00?** The paid amounts are 120.00 + 40.00 + 60.00; pending order 1002 is excluded.

## 5. Hands-on Lab 001 — Read-only SQL discovery (20 minutes)

**Goal:** Execute the examples, verify exact results, and explain what each query does.

**Environment:** Use a **non-production** PostgreSQL 18 database and an SQL editor or `psql`. If no SQL environment exists, read through the examples now and return after Chapter 003 (lab setup). All four queries are also available in [the standalone lab SQL file](../labs/001-first-queries.sql).

1. Confirm your lab session is connected (optional PostgreSQL-specific checks):

   ```sql
   SELECT current_database() AS database_name,
          current_user AS connected_role,
          current_setting('server_version') AS postgres_version;
   ```

   **Expected:** One row. The actual database/user/version strings depend on your environment; verify that the server version begins with `18` for the course baseline.

2. Run Examples A–D in order using your SQL editor or `psql`.
3. Confirm Example A returns `5`; Example B returns **4** rows; Example C returns **3**; Example D returns **3** and **220.00**.
4. Edit Example C in your *own SQL editor* to change `'paid'` to `'pending'`. Predict the result before you run it. **Expected:** only order 1002.
5. Restore the original query after the exercise. No cleanup or rollback is needed because nothing was persisted.

### Lab acceptance checklist

- [ ] I can describe a row and a column.
- [ ] Example A returns `SQL is working / 5`.
- [ ] Example B returns 4 rows in ascending order ID.
- [ ] Example C returns 3 rows (1001, 1003, 1004).
- [ ] Example D returns `3 / 220.00`.
- [ ] Changing the filter to `pending` returns exactly order 1002.
- [ ] I can explain why I should not run ad-hoc writes on production.

### Troubleshooting

| Symptom | Likely cause | Safe next action |
|---|---|---|
| SQL editor says connection refused | PostgreSQL is not running or inaccessible | Follow Chapter 003; check hostname, port and client settings |
| `syntax error` | Missing comma, quote, parenthesis, or semicolon | Paste one complete example at a time |
| Results arrive in a different order | Query omitted `ORDER BY` | Add `ORDER BY order_id` |
| `permission denied` on a real table | Access role lacks privileges | Use the read-only in-query dataset; request appropriate approved access |
| Wrong count or total | Sample row or status altered | Restore the exact four sample rows |

## 6. DBRE/SRE safety notes and SQL portability (5 minutes)

- Prefer **read-only queries** for your first exercises, and always confirm the environment before querying sensitive systems.
- SQL syntax is not identical across platforms. For instance, `::numeric(10,2)` is a **PostgreSQL-style cast**; a more portable explicit form is `CAST(120.00 AS DECIMAL(10,2))`.
- On busy production databases, even a `SELECT` may be expensive. Later chapters cover indexes, execution plans, timeouts, locks, and workload-safe query patterns.
- Do not use real patient, customer, or employee records in shared tutorial artifacts.

## 7. Knowledge check and next chapter (5 minutes)

1. What is SQL, and how is it different from PostgreSQL?
2. Which SQL command typically retrieves records?
3. How many rows do we expect after filtering the sample to paid orders?
4. Which team usually owns an application query, and who should help with database-side performance?
5. Why should a DBRE verify the database environment before running a change?

<details>
<summary>Answer key</summary>

1. SQL is a language; PostgreSQL is a DBMS implementing SQL.
2. `SELECT`.
3. Three.
4. Usually the application team owns its query; DBRE collaborates on query plans, indexes, and capacity.
5. To avoid impacting the wrong system or sensitive data.

</details>

**Next:** [Chapter 002 — Relational Databases and DBMS Architecture](002-relational-databases-and-dbms-architecture.md) (published; independent editorial review and runtime validation pending).

## References

- [PostgreSQL 18 — SQL language introduction](https://www.postgresql.org/docs/18/tutorial-sql.html)
- [PostgreSQL 18 — SELECT reference](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — VALUES reference](https://www.postgresql.org/docs/18/sql-values.html)

> **Validation record:** Logical expected outputs have been manually reviewed against the fictional data. This document has **not yet been executed against a PostgreSQL 18 runtime**. Do not label it runtime-validated until actual execution evidence is recorded.
