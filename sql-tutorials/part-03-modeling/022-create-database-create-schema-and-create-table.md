# Chapter 022 — CREATE DATABASE, CREATE SCHEMA, and CREATE TABLE

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 021](021-entity-relationships-and-conceptual-data-modeling.md) · [Next: 023](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 isolated lab**
>
> **Validation:** Authored; targeted static inspection only. Independent editorial review, comprehensive SQL syntax verification, and actual PostgreSQL 18 execution pending.

## Learning outcomes and prerequisites (0–5 minutes)

By the end you can explain database versus schema versus table, read basic DDL, create a constrained table safely in a disposable PostgreSQL database, inspect metadata, and distinguish reversible transactional DDL from database provisioning. Read [Chapter 021](021-entity-relationships-and-conceptual-data-modeling.md) first. **Never run the examples against production or with production credentials.**

| Time | Activity |
|---|---|
| 0–5 | Outcomes, isolation and safety |
| 5–15 | Database, schema, table, DDL and dialects |
| 15–30 | Worked design and expected outputs |
| 30–50 | Isolated PostgreSQL 18 lab |
| 50–55 | Troubleshooting and validation |
| 55–60 | Review with answers |

## Key concepts and syntax (5–15 minutes)

**DDL (data definition language)** defines database objects. In PostgreSQL a **database** is a separate catalog and connection target; a **schema** is a namespace *inside* a database; a **table** holds typed rows within a schema. One PostgreSQL connection addresses one database, and SQL queries cannot directly join ordinary tables across different databases without additional integration mechanisms. PostgreSQL's default schema is commonly `public`, but explicit schema qualification reduces search-path surprises.

**Conceptual hierarchy:**

```text
PostgreSQL cluster (server)
  └── database: sql_tutorials
       └── schema: sql_ch022_demo
            ├── customers
            └── orders
```

The SQL-standard family supports `CREATE TABLE` and `CREATE SCHEMA`, but database creation and object privileges differ by vendor. PostgreSQL's `CREATE DATABASE` is a server-level administrative command; it **cannot run inside a transaction block**. Consequently, this chapter **shows** its syntax but deliberately does **not** execute it in the lab. PostgreSQL `CREATE SCHEMA` and `CREATE TABLE` are transactional and can be rolled back in a controlled exercise.

```sql
-- Illustration ONLY: provision a database through an approved
-- isolated administrative workflow, never as part of this lab.
CREATE DATABASE sql_tutorials;

-- PostgreSQL 18: executable only inside the isolated lab transaction.
CREATE SCHEMA sql_ch022_demo;
CREATE TABLE sql_ch022_demo.customers (
  customer_id integer PRIMARY KEY,
  customer_code varchar(16) NOT NULL UNIQUE,
  display_name varchar(80) NOT NULL
);
```

A table definition specifies column names, types, and constraints. A primary key prevents duplicate or NULL identifiers; `NOT NULL` requires a value; `UNIQUE` rejects duplicate non-NULL values (NULL handling varies by implementation). `REFERENCES` creates a foreign key, which enforces matching parent rows. Constraints are covered in depth in Chapters 024–026.

**Vendor distinctions:** PostgreSQL uses `CREATE DATABASE` outside transactions and supports transactional DDL. SQL Server uses `CREATE DATABASE` and typically `dbo` as a schema; MySQL commonly treats `CREATE SCHEMA` as a synonym for `CREATE DATABASE`; Snowflake and BigQuery have different account/project/dataset naming and authorization models. Do not assume PostgreSQL's transaction/rollback behavior holds for MySQL, Oracle, or cloud warehouses.

## Worked example (15–30 minutes)

The fictional retail system has customers and orders. One order belongs to exactly one customer. Our table grain is **one customer per customers row** and **one order per orders row**.

```sql
CREATE TABLE sql_ch022_demo.orders (
  order_id integer PRIMARY KEY,
  customer_id integer NOT NULL
    REFERENCES sql_ch022_demo.customers(customer_id),
  order_status varchar(12) NOT NULL,
  total_amount numeric(12,2) NOT NULL CHECK (total_amount >= 0)
);
```

The explicit `numeric(12,2)` type avoids floating-point rounding for currency-like totals. The foreign key must reference a table that already exists. This is a **simplified training design**, not a complete payment, tax, or accounting schema.

Insert the following **synthetic** rows *only inside the disposable lab transaction*:

```sql
INSERT INTO sql_ch022_demo.customers
  (customer_id, customer_code, display_name)
VALUES (1, 'C001', 'Example Customer A'),
       (2, 'C002', 'Example Customer B');

INSERT INTO sql_ch022_demo.orders
  (order_id, customer_id, order_status, total_amount)
VALUES (1001, 1, 'PAID', 32.00),
       (1002, 1, 'PENDING', 15.50);
```

Expected customer count: **2**. Expected order count: **2**. Expected order total: **47.50**. Customer 2 has no orders, consistent with optional participation on the customer side. These are reasoned expected results, **not measured PostgreSQL 18 output**.

`CREATE TABLE IF NOT EXISTS` is not a migration safety guarantee: an existing table may have the wrong columns or constraints. In production, schema migrations need review, deployment sequencing, lock analysis, backup/restore readiness, and an explicit rollback strategy. PostgreSQL DDL can acquire strong locks; transactional rollback does not make a production migration risk-free.

## Hands-on lab (30–50 minutes)

**Prerequisite:** a separately verified disposable PostgreSQL **18.x** instance with a pre-created `sql_tutorials` database and restricted lab credentials. The database name/version guard is **not** proof of isolation. Do not create the lab database with production access. If the isolated environment is unavailable, read the SQL without executing it and mark runtime acceptance pending.

Run from the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/022-create-schema-and-tables-isolated.sql
```

The [companion lab](../labs/022-create-schema-and-tables-isolated.sql) verifies PostgreSQL 18 and database identity, sets timeouts, starts a transaction, creates a uniquely named training schema and two tables, inserts synthetic rows, checks metadata and deterministic counts/totals, then **ROLLBACKs**. It does not issue `CREATE DATABASE`, `DROP DATABASE`, or `COMMIT`. Because all DDL and DML occur within the transaction, the schema and data should not persist after a successful rollback. Use the lab only in an independently confirmed disposable environment.

Practice: (1) identify the database/schema/table boundary; (2) locate the primary key and foreign key; (3) predict the result of attempting an order with a missing customer (FK violation); (4) calculate the two-order total; (5) explain why the second customer is absent from an inner join with orders. Do **not** deliberately trigger constraint failures in the shared acceptance transaction; they would abort it. Use a separate disposable savepoint exercise if exploring errors.

Expected query outputs:

| Check | Expected |
|---|---|
| Customer rows | 2 |
| Order rows | 2 |
| Sum of order totals | 47.50 |
| Foreign-key constraints on orders | 1 |
| Schema exists after rollback | false |

The final existence check is outside the transaction. A pre-existing `sql_ch022_demo` schema is treated as a **blocker**; the lab refuses to overwrite it. Run it only once at a time in the disposable database.

## Validation, troubleshooting, and DBRE/SRE safeguards (50–55 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Version/database guard rejects run | Wrong target | Stop; verify independently, never bypass |
| Permission denied for schema | Missing CREATE privilege | Use approved restricted lab role; do not escalate in production |
| Schema already exists | Prior object or concurrent run | Stop; inspect; never auto-drop |
| Foreign key violation | Parent row missing | Validate load order and source integrity |
| Relation does not exist | Wrong schema or creation order | Use schema-qualified names |
| DDL appears to vanish | Intentional ROLLBACK | Expected; this is a reversible lab |
| CREATE DATABASE fails inside transaction | PostgreSQL restriction | Provision only via separately approved isolated admin workflow |

**Operational guardrails:** Use an isolated cluster, a dedicated non-production role, a statement timeout and lock timeout, no real customer or patient data, no persistent credentials in scripts, and no unreviewed DDL against live systems. Validate migration dependencies and assess lock duration, replication, disk growth, and recovery plans before production change control. PostgreSQL `ROLLBACK` protects this lab's changes, not every possible side effect in arbitrary production workflows.

## Review questions and answers (55–60 minutes)

1. **Database vs schema?** A database is a separate connection/catalog boundary; a schema organizes objects within one database.
2. **What does CREATE TABLE define?** Columns, types, and optional constraints.
3. **Can PostgreSQL CREATE DATABASE run inside BEGIN/ROLLBACK?** No.
4. **Why schema-qualify table names?** To avoid ambiguous `search_path` resolution.
5. **What does a foreign key protect?** Referential integrity to a qualifying parent key.
6. **Does IF NOT EXISTS verify schema compatibility?** No; it only suppresses a duplicate-object error.
7. **Why use ROLLBACK in this lab?** To leave no persistent training schema or rows.
8. **Is passing the database-name guard enough to prove safety?** No; isolation must be verified independently.

## References and next chapter

- [PostgreSQL 18 — CREATE DATABASE](https://www.postgresql.org/docs/18/sql-createdatabase.html)
- [PostgreSQL 18 — CREATE SCHEMA](https://www.postgresql.org/docs/18/sql-createschema.html)
- [PostgreSQL 18 — CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18 — DDL](https://www.postgresql.org/docs/18/ddl.html)
- [PostgreSQL 18 — Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 — Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)

Next: **023 — Choosing numeric, character, Boolean, and temporal types** ([Master TOC](../MASTER-TOC.md)).
