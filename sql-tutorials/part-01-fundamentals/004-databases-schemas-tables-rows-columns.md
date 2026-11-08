# Chapter 004 — Databases, Schemas, Tables, Rows, and Columns

> [Master TOC](../MASTER-TOC.md) · [SQL Tutorials](../README.md) · [Chapter 003 setup](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md)  
> **60 minutes** · PostgreSQL 18 reference · Beginner / Data Engineer / DBRE/SRE  
> **Status:** Published; independent review and PostgreSQL 18 runtime execution pending.

## Objectives and schedule

| Time | Topic | Outcome |
|---:|---|---|
| 5 min | Prerequisites and safety | Verify an isolated lab |
| 10 min | Hierarchy | Explain server, database, schema and table |
| 10 min | Rows, columns, types | Recognize relational records |
| 15 min | SQL walkthrough | Query synthetic records and metadata |
| 15 min | Hands-on lab | Run assertions and interpret results |
| 5 min | Troubleshooting / quiz | Diagnose common mistakes |

**Prerequisite:** Chapter 003's local Docker PostgreSQL 18 instance. This chapter's [SQL lab](../labs/004-databases-schemas-tables-rows-columns.sql) is entirely read-only. Do not use production connections or real customer/patient data.

## 1. Relational object hierarchy

```text
PostgreSQL server (cluster)
  ├─ database: postgres
  └─ database: sql_tutorials  [our connected database]
       ├─ schema: pg_catalog          [system catalogs]
       ├─ schema: information_schema  [metadata views]
       └─ schema: public              [default-style namespace]
            ├─ table: orders          [conceptual only; not created]
            └─ table: customers       [conceptual only; not created]
```

A **database** contains schemas and their objects. In PostgreSQL, a connection chooses one database; normal SQL does not directly join across databases without special integration. A **schema** is a namespace *within* a database. Two schemas may each contain an `orders` table. A **table** stores related rows; each **column** defines an attribute with a declared type. A **row** is one record. A **constraint** enforces rules such as uniqueness or non-null values; Chapters 024–026 explore constraints in detail.

| order_id (integer) | customer_name (text) | amount_usd (numeric) | status (text) |
|---:|---|---:|---|
| 2001 | Ava | 45.50 | paid |
| 2002 | Noah | 80.00 | pending |
| 2003 | Mia | 24.50 | paid |
| 2004 | Ava | 10.00 | paid |

This fictional relation has **4 columns** and **4 rows**. A production design would normally separate customer details and order details into related tables; Chapter 005 explains keys and relationships. SQL does **not** guarantee row order without `ORDER BY`.

**Names and qualification:** Within the connected `sql_tutorials` database, a table can be addressed as `public.orders`. The conceptual `sql_tutorials.public.orders` hierarchy does *not* provide general cross-database access in PostgreSQL. Prefer explicit `schema.table` names in critical scripts.

## 2. Database and schema metadata

PostgreSQL provides system catalogs in `pg_catalog` and standards-oriented metadata views in `information_schema`. Run these safe, read-only queries:

```sql
SELECT current_database() AS database_name,
       current_user AS role_name,
       current_schema() AS default_schema;
SHOW search_path;
SELECT current_schemas(true) AS effective_schemas;
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;
```

The first query returns one row. The database should be `sql_tutorials` in the course lab; role should be `sql_lab`. Other output varies with configuration and permissions. `search_path` determines where PostgreSQL looks for **unqualified** object names. Never assume `public` is first or writable.

Inspect ordinary and partitioned tables without creating anything:

```sql
SELECT n.nspname AS schema_name,
       c.relname AS table_name,
       CASE c.relkind WHEN 'r' THEN 'ordinary'
                      WHEN 'p' THEN 'partitioned' END AS table_kind
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r','p')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname, c.relname;
```

An empty result is normal in a fresh lab. Catalog visibility does not prove the current role has permission to query every listed table.

## 3. Guided SQL examples

A `WITH ... VALUES` expression supplies rows for **one statement**; it creates no permanent table. This lets beginners explore relational concepts safely.

```sql
WITH orders (order_id, customer_name, amount_usd, status) AS (
 VALUES
 (2001, 'Ava', 45.50::numeric(10,2), 'paid'),
 (2002, 'Noah', 80.00::numeric(10,2), 'pending'),
 (2003, 'Mia', 24.50::numeric(10,2), 'paid'),
 (2004, 'Ava', 10.00::numeric(10,2), 'paid')
)
SELECT order_id, customer_name, amount_usd, status
FROM orders
ORDER BY order_id;
```

Expected: four rows in ID order. `::numeric(10,2)` is PostgreSQL casting syntax; `CAST(45.50 AS DECIMAL(10,2))` is a more portable alternative.

```sql
WITH orders (order_id, customer_name, amount_usd, status) AS (
 VALUES
 (2001, 'Ava', 45.50::numeric(10,2), 'paid'),
 (2002, 'Noah', 80.00::numeric(10,2), 'pending'),
 (2003, 'Mia', 24.50::numeric(10,2), 'paid'),
 (2004, 'Ava', 10.00::numeric(10,2), 'paid')
)
SELECT COUNT(*) AS all_rows,
       COUNT(*) FILTER (WHERE status = 'paid') AS paid_rows,
       SUM(amount_usd) FILTER (WHERE status = 'paid') AS paid_total
FROM orders;
```

Expected: **all_rows=4**, **paid_rows=3**, **paid_total=80.00**. `FILTER` is supported by PostgreSQL; portability varies by SQL dialect. For conditional counts, a common alternative is `SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END)`.

**Concept only, do not execute:** A future table could be defined using `CREATE TABLE training.orders (order_id integer PRIMARY KEY, customer_name text NOT NULL, amount_usd numeric(10,2) NOT NULL, status text NOT NULL);`. Schema and table creation belong to Chapter 022, not this read-only chapter.

## 4. Hands-on lab (15 minutes)

The [committed SQL lab](../labs/004-databases-schemas-tables-rows-columns.sql) checks PostgreSQL 18, verifies the intended database, inspects schemas and catalogs, and validates synthetic row totals. It uses a read-only transaction with assertions that raise an error if expected results are wrong.

From `sql-tutorials/labs/docker`, on **Windows PowerShell**:

```powershell
Get-Content ../004-databases-schemas-tables-rows-columns.sql -Raw |
  docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f -
if ($LASTEXITCODE -ne 0) { throw "Chapter 004 lab failed: $LASTEXITCODE" }
```

On **Bash**:

```bash
docker compose exec -T postgres psql -U sql_lab -d sql_tutorials -X -v ON_ERROR_STOP=1 -f - < ../004-databases-schemas-tables-rows-columns.sql
```

| Validation | Expected |
|---|---|
| PostgreSQL major version | 18 |
| Database name | sql_tutorials |
| Schema `public` | exists |
| Synthetic order rows | 4 |
| Paid order rows | 3 |
| Paid order total | 80.00 |
| Distinct customers | 3 |
| Final lab assertion | PASS |

**Exercises:** (1) Name the connected database, role, and default schema. (2) List available schemas and explain `information_schema`. (3) Name the four synthetic columns and their data types. (4) Change the predicate in your own query to `status='pending'`; predict one row totaling **80.00**. (5) Remove `ORDER BY` and explain why the apparent order must not be relied upon. (6) Explain why two sessions with different search paths might resolve the same unqualified table name differently.

**Acceptance:** The lab exits with code 0 and prints PASS. Capture the actual PostgreSQL version, command, exit status, and redacted output when runtime testing is performed. The lab creates no persistent objects, so no cleanup is required.

## 5. Troubleshooting and DBRE/SRE safeguards

| Symptom | Likely reason and safe response |
|---|---|
| `relation does not exist` | Check connected database, schema qualification and `search_path`; do not create a replacement table impulsively |
| `permission denied for schema` | Role lacks access; request least-privilege authorization |
| No user tables listed | New lab has none; metadata visibility varies by role |
| Unexpected row order | Add `ORDER BY` |
| Unexpected columns | Check the correct schema/table and approved definition before changing SQL |
| `current_schema()` is null | No suitable schema found in the current search path; inspect `current_schemas(true)` |

For production investigations, verify database identity and role, scope catalog queries, use schema-qualified names, and never equate metadata visibility with authorization. Do not use this training lab as a production access or schema-change procedure.

## 6. Knowledge check (5 minutes)

1. Can two schemas in the same database each contain a table called `orders`?
2. Is `public.orders` schema-qualified?
3. Does a `WITH` CTE persist after its statement?
4. Is row order guaranteed without `ORDER BY`?
5. What controls resolution of unqualified table names?
6. Is `information_schema` specific only to PostgreSQL?

**Answers:** 1 Yes; 2 Yes; 3 No; 4 No; 5 the active search path (and current database); 6 No, it is SQL-standard-oriented, though implementation details differ.

**Next:** Chapter 005 — Records, Relationships, Keys, and Relational Terminology.

## Authoritative references

- [PostgreSQL 18 — Data Definition](https://www.postgresql.org/docs/18/ddl.html)
- [PostgreSQL 18 — Schemas](https://www.postgresql.org/docs/18/ddl-schemas.html)
- [PostgreSQL 18 — Information Schema](https://www.postgresql.org/docs/18/information-schema.html)
- [PostgreSQL 18 — System Catalogs](https://www.postgresql.org/docs/18/catalogs.html)
- [PostgreSQL 18 — WITH](https://www.postgresql.org/docs/18/queries-with.html)

> **Validation record:** Syntax and expected arithmetic have been reviewed in the authored text. This is **not** independent editorial review or runtime certification. PostgreSQL 18 execution evidence is pending.
