# 088 — Stored Functions and Procedures: Dialect-Specific Syntax

**Part 09 — SQL Objects, Functions & Semi-Structured Data** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** analysts, data engineers, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only lab](../labs/088-stored-functions-and-procedures.sql) · [Previous: 087](087-temporary-tables-and-intermediate-result-sets.md) · **Next: 089 — Triggers, dynamic SQL, and parameterization safeguards** (planned)

## 1. Learning outcomes and prerequisites (0–5 minutes)

By the end, distinguish a function from a procedure; recognize SQL-language and PL/pgSQL routines; call routines with correct syntax; identify volatility, privileges, transaction boundaries and side effects; and implement a safe, testable reporting transformation. Prerequisites: SELECT, expressions, aggregation, transaction basics ([038](../part-04-transactions/038-begin-commit-rollback-and-savepoint.md)) and [087](087-temporary-tables-and-intermediate-result-sets.md).

**Why DBRE/SRE care:** routines can hide expensive SQL, elevated privileges, long transactions, or writes. Data engineers need stable, documented interfaces and reproducible results. A function's name does not guarantee read-only behavior.

## 2. Concepts, portable ideas and dialect boundaries (5–15 minutes)

A **function** returns a value or set of rows and is commonly used in expressions or FROM. A **procedure** is invoked for an operation; PostgreSQL uses `CALL` and procedures do not have a function-style return value (OUT/INOUT parameters can return a result row). SQL/PSM-style routine concepts are standardized, but routine definitions and procedural languages are **not portable verbatim**.

| Topic | PostgreSQL 18 | Other dialects |
|---|---|---|
| Define a function | `CREATE FUNCTION ... RETURNS ... LANGUAGE sql` or `plpgsql` | SQL Server `CREATE FUNCTION`; Oracle PL/SQL; Snowflake SQL/JavaScript |
| Invoke a scalar function | `SELECT function_name(args)` | Common concept, syntax/semantics vary |
| Define a procedure | `CREATE PROCEDURE ... LANGUAGE plpgsql` | SQL Server `CREATE PROCEDURE`; MySQL stored routines |
| Invoke a procedure | `CALL procedure_name(args)` | SQL Server `EXEC`; other dialects vary |
| Return rows | `RETURNS TABLE (...)` / set-returning function | Table-valued functions or cursor/result-set conventions vary |

**PostgreSQL-specific:** `IMMUTABLE`, `STABLE`, `VOLATILE` are planner promises, not security labels. Never mark a routine `IMMUTABLE` if it reads changing tables or depends on time, locale, or session settings. `STRICT` (or `RETURNS NULL ON NULL INPUT`) skips a function body for NULL arguments. `SECURITY INVOKER` is the default; `SECURITY DEFINER` executes with owner privileges and requires rigorous `search_path` and privilege review. `PARALLEL SAFE` is a separate, carefully justified property.

A PostgreSQL procedure may control transactions only in eligible top-level `CALL` contexts; a `CALL` inside an explicit transaction block cannot commit/rollback. Additional restrictions apply to security-definer procedures and procedures with SET clauses. Do not assume a stored procedure is automatically atomic or safe to retry. Functions cannot issue transaction-control commands.

## 3. Walkthrough — reusable fee calculation (15–30 minutes)

**Portable, no-routine expression** (good first choice when reuse is limited):

```sql
WITH invoices(invoice_id, subtotal, fee_rate) AS (
 VALUES (1, 100.00::numeric, 0.05::numeric),
        (2,  40.00::numeric, 0.10::numeric),
        (3,  20.00::numeric, 0.00::numeric)
)
SELECT invoice_id, subtotal,
       ROUND(subtotal * fee_rate, 2) AS fee,
       subtotal + ROUND(subtotal * fee_rate, 2) AS total
FROM invoices ORDER BY invoice_id;
```

The `VALUES` clause is widely supported; the `::numeric` cast is PostgreSQL-specific (use `CAST(... AS DECIMAL(...))` when porting). Expected rows: (1,100.00,5.00,105.00), (2,40.00,4.00,44.00), (3,20.00,0.00,20.00). Fees sum to 9.00 and totals to 169.00.

**PostgreSQL 18 isolated DDL demonstration — optional, never run on production:**

```sql
-- Run only in an approved, disposable sql_tutorials database.
BEGIN;
CREATE FUNCTION pg_temp.fee_088(amount numeric, rate numeric)
RETURNS numeric
LANGUAGE sql IMMUTABLE STRICT
RETURN round(amount * rate, 2);
SELECT pg_temp.fee_088(100.00::numeric, 0.05::numeric); -- 5.00
ROLLBACK;
```

PostgreSQL 18 supports SQL-standard function bodies with `RETURN` for SQL-language functions. `pg_temp` keeps this demonstration session-local; rolling back the creation removes it. This optional example executes DDL and is **not** part of the canonical read-only lab. For a multi-statement procedure, PostgreSQL's PL/pgSQL form is:

```sql
-- Illustrative syntax ONLY: do not execute outside a disposable environment.
CREATE PROCEDURE demo_log_088(IN p_message text)
LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE 'Synthetic message: %', p_message;
END;
$$;
CALL demo_log_088('test');
-- No transaction control or persistent write in this example.
```

A function can be called within SELECT; a procedure uses CALL. Avoid wrapping a routine that performs writes inside a supposedly read-only reporting pipeline. For production routine deployment, use reviewed migrations, versioning, explicit grants, schema-qualified names and rollback procedures.

## 4. Hands-on read-only lab (30–50 minutes)

Run from the repository root, with an isolated PostgreSQL **18** database called `sql_tutorials` and nonproduction credentials:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/088-stored-functions-and-procedures.sql
```

The [canonical SQL lab](../labs/088-stored-functions-and-procedures.sql) uses a read-only transaction, synthetic invoice rows, a CTE modeling a reusable calculation, an inspection of PostgreSQL built-in routine metadata, exact bidirectional `EXCEPT ALL` comparison, source-count and totals checks, and `ROLLBACK`. It does not create functions, procedures, tables, roles, or grants.

**Practice:** (1) Change invoice 2 rate to 0.15; predict fee 6.00 and new total 46.00. (2) Explain why `IMMUTABLE` is appropriate for a pure numeric calculation but not for a table lookup. (3) Identify whether `SELECT` or `CALL` invokes a PostgreSQL procedure. (4) Explain why `SECURITY DEFINER` plus an untrusted `search_path` is dangerous. (5) Compare row-by-row fee rounding against rounding only the sum; state the financial rounding policy explicitly.

**Stretch, isolated only:** run the rollback-only temporary function demonstration in a separate disposable session, verify the returned 5.00, then confirm the function is absent after rollback. Never substitute production credentials.

## 5. Validation, troubleshooting and operational safety (50–55 minutes)

- **Routine does not exist:** verify schema, argument types and overload resolution; explicitly cast ambiguous literals.
- **Permission denied:** inspect `EXECUTE` grants and schema `USAGE`; never grant blanket privileges as a shortcut.
- **Unexpected side effects:** review the routine body and nested calls; `VOLATILE` is not a guarantee of writes, and `STABLE` is not a security guarantee.
- **Performance regression:** profile actual statements, function calls and query plans in isolation; set `statement_timeout`, monitor execution counts, and avoid per-row SQL lookups.
- **Transaction error:** top-level CALL transaction control differs from an explicit BEGIN/CALL context; review procedure attributes.
- **Security:** favor invoker rights, restrict EXECUTE, schema-qualify objects, validate input, avoid unsafe dynamic SQL, and avoid altering production functions or procedures.
- **Evidence requirement:** record PostgreSQL version, database identity, SQL file revision, command, exit status, complete output, assertions and cleanup before declaring runtime validation.

## 6. Review questions and answers (55–60 minutes)

1. **How do you call a PostgreSQL scalar function?** `SELECT schema.function_name(args)`.
2. **How do you invoke a procedure?** `CALL schema.procedure_name(args)`.
3. **Does `IMMUTABLE` mean a routine is safe?** No; it is a planner volatility promise, not an access-control guarantee.
4. **When is `SECURITY DEFINER` risky?** When privileges, `search_path`, ownership, or input handling are not tightly controlled.
5. **Can a procedure always COMMIT?** No; transaction-control eligibility depends on call context and procedure attributes.
6. **What does two-way `EXCEPT ALL` verify?** Both missing and unexpected rows, including duplicates.
7. **What is required for runtime certification?** Actual isolated PostgreSQL 18 execution with reproducible evidence.

## References

- [PostgreSQL 18 — CREATE FUNCTION](https://www.postgresql.org/docs/18/sql-createfunction.html)
- [PostgreSQL 18 — CREATE PROCEDURE](https://www.postgresql.org/docs/18/sql-createprocedure.html)
- [PostgreSQL 18 — CALL](https://www.postgresql.org/docs/18/sql-call.html)
- [PostgreSQL 18 — PL/pgSQL transaction management](https://www.postgresql.org/docs/18/plpgsql-transactions.html)
- [PostgreSQL 18 — Writing SECURITY DEFINER functions safely](https://www.postgresql.org/docs/18/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY)

**Validation:** authored and targeted static/manual reasoning; independent editorial review, comprehensive automated SQL syntax/link QA and actual PostgreSQL 18 runtime validation pending.
