# Chapter 005 — Records, Relationships, Keys, and Relational Terminology

> [Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Previous: Chapter 004](004-databases-schemas-tables-rows-columns.md)  
> **Audience:** Beginners, data engineers, application engineers, DBRE/SRE · **Duration:** 60 minutes · **Baseline:** PostgreSQL 18  
> **Status:** Authored/published; independent editorial review and actual PostgreSQL 18 runtime validation pending.

## Outcomes and agenda

| Time | Activity | Goal |
|---:|---|---|
| 0–5 min | Safety and prerequisites | Confirm the isolated PostgreSQL 18 lab |
| 5–15 min | Records and relations | Identify tuples, attributes, domains and cardinality |
| 15–25 min | Keys and relationships | Explain PK, FK, candidate, natural and surrogate keys |
| 25–40 min | Guided examples | Trace 1:N and M:N joins without accidental duplication |
| 40–55 min | Hands-on SQL lab | Run read-only assertions and inspect unmatched references |
| 55–60 min | Troubleshooting and quiz | Check conceptual understanding |

**Prerequisite:** [Chapter 003 PostgreSQL 18 Docker setup](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). All SQL in this chapter is read-only, uses fictional in-query records and creates no tables. The runnable file is [labs/005-records-relationships-keys.sql](../labs/005-records-relationships-keys.sql). Do **not** use production connections or real patient/customer data.

## 1. Relational vocabulary (10 minutes)

A **relation** is the relational model's mathematical concept underlying a table; SQL tables can contain duplicate rows unless constraints or query operations prevent them, and SQL permits NULL, so a SQL table is not identical to a pure mathematical relation.

| Term | Beginner explanation | Example |
|---|---|---|
| Entity | Thing about which we store data | Customer, order, product |
| Table / relation | Collection of similarly shaped records | `customers` |
| Row / tuple / record | One occurrence of an entity or fact | Customer 101 |
| Column / attribute | Named property of each row | `customer_id` |
| Data type / domain | Allowed representation and values | Integer ID, text name |
| Cardinality (table) | Number of rows | 3 customers |
| Degree | Number of columns | 2 customer columns |
| Relationship cardinality | Number of matching records across entities | One customer to many orders |
| NULL | Missing/unknown or inapplicable SQL value, not zero or empty string | Optional email |

**Logical model vs. physical implementation:** The logical model specifies entities and relationships. PostgreSQL stores and indexes them using physical structures; keys and constraints define correctness, while indexes support access patterns. An index is not a substitute for a uniqueness constraint.

### Fictional retail model

```text
customers (customer_id PK, customer_name)
    1 ──────────< many
orders (order_id PK, customer_id FK, order_total)
    1 ──────────< many
order_items (order_id FK, product_id FK, quantity)
    many >─────── 1
products (product_id PK, product_name)
```

`order_items` is a **junction/associative entity** representing the many-to-many relationship between orders and products. The pair `(order_id, product_id)` can be its composite primary key **if** each product occurs at most once per order; otherwise a line identifier is needed.

## 2. Identifiers and integrity (10 minutes)

- **Superkey:** Any set of columns that uniquely identifies rows, potentially including unnecessary columns.
- **Candidate key:** Minimal set of columns that uniquely identifies rows.
- **Primary key (PK):** Selected candidate key; unique and non-NULL. A table has at most one PK constraint, which can contain multiple columns.
- **Alternate key:** Candidate key not selected as the primary key, often enforced with `UNIQUE`.
- **Natural key:** Meaningful business identifier, e.g., a stable external order number; evaluate mutability and reuse.
- **Surrogate key:** Artificial identifier such as an identity number or UUID; useful when business identifiers can change.
- **Foreign key (FK):** Column(s) constrained to match a referenced candidate/unique key in another or the same table, subject to NULL and match rules. FKs protect referential integrity when actually declared and enforced.
- **Composite key:** Identifier consisting of more than one column.
- **Unique constraint:** Prevents duplicate key values, with database-specific NULL behavior. PostgreSQL defaults to allowing multiple NULLs in a UNIQUE column unless `NULLS NOT DISTINCT` is specified.

**Important:** Merely naming a column `customer_id` does **not** declare a foreign key. This chapter's `WITH ... VALUES` datasets have **no persisted constraints**; they demonstrate intended relationships and detect orphans with queries. Chapters 024–026 will create and enforce real constraints in an isolated database.

### Relationship types

| Type | Example | Common modeling choice |
|---|---|---|
| 1:1 | Customer ↔ optional preferences row | Unique FK on dependent side |
| 1:N | Customer → orders | FK on the many side |
| M:N | Orders ↔ products | Junction table with two FKs |
| Recursive | Employee → manager | Self-referencing FK |

A join may produce **more rows** than either source when there are multiple matches. Never interpret a join's row count as the number of distinct customers without checking the output grain.

## 3. Guided SQL examples (15 minutes)

These examples use SQL common-table expressions (CTEs) and `VALUES` to avoid persistent objects. PostgreSQL supports the syntax shown; `::integer` casts are PostgreSQL-specific and `CAST(... AS INTEGER)` is more portable. Explicit `ORDER BY` ensures stable displayed order.

### Example A — One customer, many orders

```sql
WITH customers(customer_id, customer_name) AS (
  VALUES (101, 'Ava'), (102, 'Noah'), (103, 'Mia')
), orders(order_id, customer_id, amount_usd) AS (
  VALUES (5001, 101, 30.00::numeric(10,2)),
         (5002, 101, 45.00::numeric(10,2)),
         (5003, 102, 20.00::numeric(10,2))
)
SELECT c.customer_id, c.customer_name, o.order_id, o.amount_usd
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
ORDER BY c.customer_id, o.order_id;
```

Expected **4 rows**: Ava/5001/30.00, Ava/5002/45.00, Noah/5003/20.00, Mia/NULL/NULL. Mia is preserved by `LEFT JOIN` even though she has no orders. An `INNER JOIN` would return **3** rows and omit Mia.

### Example B — Measure the correct grain

```sql
WITH customers(customer_id, customer_name) AS (
  VALUES (101, 'Ava'), (102, 'Noah'), (103, 'Mia')
), orders(order_id, customer_id, amount_usd) AS (
  VALUES (5001, 101, 30.00::numeric(10,2)),
         (5002, 101, 45.00::numeric(10,2)),
         (5003, 102, 20.00::numeric(10,2))
)
SELECT c.customer_id, c.customer_name,
       COUNT(o.order_id) AS order_count,
       COALESCE(SUM(o.amount_usd), 0::numeric) AS total_usd
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;
```

Expected:

| customer_id | customer_name | order_count | total_usd |
|---:|---|---:|---:|
| 101 | Ava | 2 | 75.00 |
| 102 | Noah | 1 | 20.00 |
| 103 | Mia | 0 | 0 |

`COUNT(o.order_id)` counts matching orders, unlike `COUNT(*)` which counts the outer-join placeholder row for Mia. `COALESCE` replaces NULL aggregate results with zero.

### Example C — Find orphaned references before an ingestion job

```sql
WITH customers(customer_id) AS (VALUES (101), (102), (103)),
     staged_orders(order_id, customer_id) AS (
       VALUES (5001,101), (5002,101), (5003,102), (5004,999)
     )
SELECT s.order_id, s.customer_id
FROM staged_orders AS s
LEFT JOIN customers AS c ON c.customer_id = s.customer_id
WHERE c.customer_id IS NULL
ORDER BY s.order_id;
```

Expected: **one orphan**, order 5004 referencing customer 999. A real FK on an enforced target table would reject an invalid non-NULL reference. Staging files may not have such constraints; validate before loading.

### Example D — Composite key and many-to-many modeling

```sql
WITH order_items(order_id, product_id, quantity) AS (
  VALUES (5001, 201, 2), (5001, 202, 1), (5002, 201, 1)
)
SELECT order_id, product_id, COUNT(*) AS occurrences
FROM order_items
GROUP BY order_id, product_id
ORDER BY order_id, product_id;
```

Expected: 3 distinct pairs, each with `occurrences = 1`. For a true composite-key validation, assert **no group has COUNT(*) > 1**. A business model allowing repeated product lines should use a separate line key instead.

## 4. Hands-on lab (15 minutes)

Use the [committed SQL file](../labs/005-records-relationships-keys.sql), which checks the lab identity and PostgreSQL 18 major version before running fictional data tests. It runs inside `BEGIN READ ONLY` and ends with `ROLLBACK`; it has no persistent effects.

From `sql-tutorials/labs/docker` on **Windows PowerShell**:

```powershell
Get-Content ../005-records-relationships-keys.sql -Raw |
  docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f -
if ($LASTEXITCODE -ne 0) { throw "Chapter 005 lab failed: $LASTEXITCODE" }
```

On **Bash**:

```bash
docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f - < ../005-records-relationships-keys.sql
```

**Expected assertions:**

| Check | Expected |
|---|---|
| PostgreSQL major | 18 |
| Connected database | sql_tutorials |
| Customers | 3 |
| Valid orders | 3 |
| Left join rows | 4 |
| Customers with no orders | 1 |
| Total valid order amount | 95.00 |
| Orphaned staged orders | 1 |
| Duplicate (order_id, product_id) pairs | 0 |
| Final lab result | PASS |

**Exercises:** Predict the results before executing. (1) Why does Ava appear twice in Example A? (2) Change the join to `INNER JOIN` in a scratch copy: how many rows remain? (3) Explain why `COUNT(*)` can overcount orders after a left join. (4) Which columns should form a composite key for `order_items`? (5) How would you prevent order 5004 from being inserted into a constrained production orders table?

**Evidence requirements:** For future runtime acceptance, record the actual PostgreSQL version, container image identifier, command, exit code, redacted query output, and timestamp. Do not claim a pass merely because the SQL file was committed.

## 5. Operational troubleshooting and safety

| Symptom | Diagnostic | Safe next step |
|---|---|---|
| Unexpected duplicate records after join | 1:N fan-out or duplicate source keys | Check relationship grain and group by the intended business key |
| Missing rows | INNER JOIN excludes unmatched records | Compare row counts using LEFT JOIN and anti-join |
| Orphaned references | Missing/late-arriving parent records | Quarantine staged rows; reconcile before constrained load |
| Primary-key violation | Duplicate identifier or incorrect key design | Inspect duplicates; do not disable constraints |
| Foreign-key violation | Missing referenced row | Check ingest order and source-of-truth integrity |
| Unexpected NULL in key | Incomplete source data or join placeholder | Separate actual source NULLs from outer-join NULLs |
| Slow relationship query | Missing index, poor estimates, or excessive join fan-out | Capture EXPLAIN in a safe lab; index tuning is covered later |

**DBRE/SRE note:** A foreign key is a correctness mechanism, not a blanket performance guarantee. In PostgreSQL, the referenced side must be backed by a suitable unique/primary key, but indexes on referencing FK columns are **not automatically created**. Evaluate them based on joins, deletes, updates and workload. Never drop constraints or run mass repairs as a first response to an incident.

## 6. Knowledge check (5 minutes)

1. Is a SQL table exactly the same as a mathematical relation?
2. Can a primary key contain two columns?
3. Does a column named `customer_id` automatically enforce referential integrity?
4. Why might `COUNT(*)` return 1 for a customer with no orders in a LEFT JOIN?
5. What is a junction table used for?
6. How many orders and how much revenue belong to Ava in the example?

**Answers:** (1) No; SQL permits duplicates and NULL. (2) Yes, a composite PK. (3) No, an FK constraint must be declared. (4) It counts the NULL-extended placeholder row. (5) Modeling M:N relationships. (6) Two orders, 75.00.

## Portability and references

The relational concepts are cross-platform; details of NULL uniqueness, identity generation, FK enforcement, constraint deferral and SQL casts vary across products. PostgreSQL-specific syntax in the lab includes `::numeric`, `current_setting`, and `BEGIN READ ONLY`. Use the equivalent constructs only after checking the target database version.

- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Table Expressions and Joins](https://www.postgresql.org/docs/18/queries-table-expressions.html)
- [PostgreSQL 18 — WITH Queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — VALUES](https://www.postgresql.org/docs/18/sql-values.html)

**Next:** Chapter 006 — Anatomy of a SQL Statement and Logical Query Processing (planned).

> **Validation:** Authored and static-reviewed for SQL shape, safety and expected outputs. Independent editorial review and **actual PostgreSQL 18 runtime execution are pending**.
