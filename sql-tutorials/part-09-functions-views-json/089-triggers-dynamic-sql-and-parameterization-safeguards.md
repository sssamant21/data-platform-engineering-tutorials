# 089 — Triggers, Dynamic SQL, and Parameterization Safeguards

**Part 09 — SQL Objects, Functions & Semi-Structured Data** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, application engineers, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only SQL lab](../labs/089-triggers-dynamic-sql-parameterization.sql) · [Previous: 088](088-stored-functions-and-procedures-dialect-specific-syntax.md) · **Next: 090 — Lab 09: Build reusable reporting objects** (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

By the end you can explain trigger timing and row/statement scope; distinguish trigger functions from ordinary routines; identify recursive, expensive and surprising trigger behavior; use bound values rather than string-concatenated SQL; safely distinguish identifiers from values in dynamic SQL; and validate a synthetic audit/change-event transformation. Prerequisites: [038 — Transactions](../part-04-data-modification/038-begin-commit-rollback-and-savepoint.md), [085 — Views](085-views-and-secure-abstraction.md), and [088 — Stored functions and procedures](088-stored-functions-and-procedures-dialect-specific-syntax.md).

**Operational motivation:** triggers execute implicitly as part of writes. They can increase transaction latency, amplify locks, cause failures and hide business logic. Dynamic SQL built by concatenating untrusted input can change the meaning of a query. A parameterized application query protects values, but does not automatically protect interpolated table or column names.

## 2. Concepts and portability (5–15 minutes)

A trigger responds to a specified event on a table (and in PostgreSQL, certain events on views). Common timing is `BEFORE`, `AFTER`, or `INSTEAD OF`; scope is `FOR EACH ROW` or `FOR EACH STATEMENT`. PostgreSQL row triggers can inspect `OLD` and `NEW` records; an UPDATE trigger sees both. An AFTER trigger runs as part of the same transaction, **not** as a durable asynchronous queue. An exception can abort the statement/transaction.

| Concern | PostgreSQL 18 | Portability note |
|---|---|---|
| Definition | `CREATE TRIGGER ... EXECUTE FUNCTION ...` | SQL Server uses inserted/deleted pseudo-tables; MySQL and Oracle have different syntax |
| Timing | BEFORE / AFTER; INSTEAD OF for views | Availability and restrictions differ |
| Granularity | FOR EACH ROW / FOR EACH STATEMENT | SQL Server DML triggers are statement-level |
| Function body | `RETURNS trigger` in PL/pgSQL | Not portable verbatim |
| Dynamic statements | PL/pgSQL `EXECUTE ... USING` | Other systems use `sp_executesql`, `EXECUTE IMMEDIATE`, etc. |
| Bound values | `$1`, `$2` in PostgreSQL prepared statements | Driver placeholder styles differ |

PostgreSQL trigger ordering: when multiple triggers of the same kind fire for the same event, their names determine alphabetical execution order. Do not depend on unspecified order across vendors. PostgreSQL also supports transition relations for some AFTER triggers; use them when set-based processing is more appropriate than per-row work.

**Choose a trigger only when appropriate:** constraints and declarative defaults are preferable for simple invariants; explicit application/service logic may be easier to observe; CDC/outbox designs require careful transactional guarantees. Avoid triggers that perform network calls, scan large tables for each row, or silently update unrelated business entities.

## 3. Worked example: changes and audit intent (15–30 minutes)

Suppose a synthetic order changes from `pending` to `paid`. An audit event should contain the order ID, previous status and new status. The following **portable-style, read-only** CTE models what a trigger would see; no trigger or table is created:

```sql
WITH changes(order_id, old_status, new_status) AS (
  VALUES (101, 'pending', 'paid'),
         (102, 'pending', 'pending'),
         (103, 'paid', 'refunded'),
         (104, 'pending', 'cancelled')
)
SELECT order_id, old_status, new_status
FROM changes
WHERE old_status <> new_status
ORDER BY order_id;
```

**Expected:** orders 101, 103 and 104; order 102 is unchanged. In real tables, account for NULL transitions with PostgreSQL `IS DISTINCT FROM` (also available in some other dialects); `<>` does not detect a change from NULL to non-NULL.

**Illustrative PostgreSQL trigger DDL — DO NOT execute on shared/production databases:**

```sql
-- Conceptual example ONLY. Requires a disposable schema with suitable tables.
CREATE FUNCTION demo_order_audit_fn() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO demo_order_audit(order_id, old_status, new_status)
    VALUES (NEW.order_id, OLD.status, NEW.status);
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER demo_order_audit_after_update
AFTER UPDATE OF status ON demo_orders
FOR EACH ROW EXECUTE FUNCTION demo_order_audit_fn();
```

This snippet is deliberately **not self-contained or runnable**: the `demo_orders` and `demo_order_audit` tables must first be created in an approved disposable environment. The canonical lab below is completely read-only. In PostgreSQL, `UPDATE OF status` means the column is targeted by the UPDATE statement; it does **not** prove the value changed, hence the `IS DISTINCT FROM` check. For an AFTER row trigger, the returned value is ignored; `RETURN NEW` is conventional.

### Parameterization: values are not identifiers

**Unsafe pseudocode (never execute):**

```python
sql = "SELECT * FROM orders WHERE customer_code = '" + user_input + "'"
```

A malicious input could alter the SQL structure. Use the database driver's bound parameters instead:

```python
# psycopg 3 example; use a nonproduction connection with least privilege.
cur.execute(
    "SELECT order_id FROM demo_orders WHERE customer_code = %s",
    (customer_code,)
)
```

**Do not** put a user-controlled identifier in a value placeholder. For dynamic table/column names, use a strict allowlist and driver identifier-composition APIs. In PostgreSQL PL/pgSQL:

```sql
-- Illustrative fragment inside a reviewed PL/pgSQL function:
-- target_table must come from a trusted allowlist, not arbitrary input.
EXECUTE format('SELECT count(*) FROM %I', target_table) INTO row_count;
-- For values: EXECUTE 'SELECT ... WHERE customer_code = $1'
--             USING supplied_code;
```

`format('%I', ...)` quotes an identifier; `%L` quotes a literal, but `USING` is preferable for bindable values. `EXECUTE ... USING` parameter binding applies to optimizable SQL commands; some utility statements require safely constructed text. Do not confuse PL/pgSQL `EXECUTE` with SQL-level `EXECUTE` of a prepared statement.

### Trigger and DBRE/SRE risk checklist

Before deploying: document owner, purpose, affected tables and row counts; measure write overhead in staging; inspect privileges and `search_path` of security-definer code; assess recursion, cascading writes, deadlocks, replication and bulk-load impact; test rollback and migrations; set statement/lock timeouts; and define alerting for trigger exceptions. Never use trigger logic as a substitute for a verified backup/recovery strategy.

## 4. Hands-on lab (30–50 minutes)

Use only an isolated PostgreSQL 18 database named `sql_tutorials` with nonproduction credentials:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/089-triggers-dynamic-sql-parameterization.sql
```

The [canonical SQL lab](../labs/089-triggers-dynamic-sql-parameterization.sql) starts a read-only transaction, checks database/version, sets local timeouts, models changes with synthetic `VALUES`, tests NULL-safe transition detection, demonstrates a parameter-like CTE input instead of interpolating a string, checks exact rows using bidirectional `EXCEPT ALL`, and rolls back. It does **not** create triggers, routines, tables, grants, or other objects.

Expected changed orders: **101, 103, 104, 105** (105 changes from NULL to pending); unchanged: **102**. Expected paid transitions: **101 only**. Expected filtered result for the synthetic status parameter `paid`: order **101** only. The assertions fail closed if actual results diverge.

**Exercises:** (1) Change the filter parameter to `refunded`; predict order 103. (2) Replace `IS DISTINCT FROM` with `<>`; explain why order 105 disappears. (3) Explain why an AFTER trigger is not an asynchronous job. (4) Describe how a row trigger on a million-row UPDATE can become a performance incident. (5) Write a change-review checklist for introducing a trigger on an orders table.

## 5. Troubleshooting, validation and safety (50–55 minutes)

- **Trigger did not fire:** inspect event type, column-specific trigger definition, enable state, WHEN condition, row versus statement scope and partition behavior.
- **Unexpected extra rows:** inspect recursive trigger calls, cascading DML and multiple triggers; use deterministic reconciliation.
- **Slow writes or lock waits:** investigate trigger execution, indexes, transaction duration, query plans and wait events in staging before changing production.
- **Dynamic SQL errors:** confirm identifier quoting, schema qualification, data types and correct `USING` placement; never “fix” by concatenating user input.
- **Security-definer concerns:** restrict ownership, schema resolution and EXECUTE privileges; audit nested calls.
- **Validation boundary:** passing assertions in a read-only CTE lab demonstrates modeled transformations, **not** actual trigger firing, trigger DDL acceptance, or SQL-injection resistance of a real application driver.
- **Evidence:** capture server version, isolated database identity, exact SQL revision, command, exit code, output, assertions and cleanup before claiming PostgreSQL 18 runtime validation.

## 6. Review questions and answers (55–60 minutes)

1. **When does an AFTER trigger run?** As part of the originating statement/transaction, not asynchronously.
2. **What distinguishes row and statement triggers?** One invocation per affected row versus one per triggering statement.
3. **How do you detect NULL-to-value changes in PostgreSQL?** `OLD.col IS DISTINCT FROM NEW.col`.
4. **Can bound parameters represent table names?** No; allowlist and safely quote identifiers separately.
5. **What protects values in PL/pgSQL dynamic SQL?** `EXECUTE ... USING` for supported statements.
6. **What is the main operational risk of a per-row trigger?** Unbounded write amplification, latency and contention.
7. **What has this lab actually validated?** Nothing at runtime until executed on isolated PostgreSQL 18 with retained evidence; it models transition logic without creating a trigger.

## References

- [PostgreSQL 18 — CREATE TRIGGER](https://www.postgresql.org/docs/18/sql-createtrigger.html)
- [PostgreSQL 18 — Trigger functions](https://www.postgresql.org/docs/18/plpgsql-trigger.html)
- [PostgreSQL 18 — PL/pgSQL executing dynamic commands](https://www.postgresql.org/docs/18/plpgsql-statements.html#PLPGSQL-STATEMENTS-EXECUTING-DYN)
- [PostgreSQL 18 — Comparison predicates / IS DISTINCT FROM](https://www.postgresql.org/docs/18/functions-comparison.html)
- [psycopg 3 — Passing parameters to SQL queries](https://www.psycopg.org/psycopg3/docs/basic/params.html)

**Validation state:** authored and targeted static/manual reasoning; independent editorial review, comprehensive parser-based SQL syntax/link QA and actual isolated PostgreSQL 18 execution remain pending.
