# 087 — Temporary Tables and Intermediate Result Sets

**Part 09 — SQL Objects, Functions & Semi-Structured Data** · **Duration: 60 minutes** · **Audience:** beginners, data engineers, DBRE/SRE · **Baseline:** PostgreSQL 18

[Curriculum](../MASTER-TOC.md) · [Part 09 navigation](../README.md) · [Lab SQL](../labs/087-temporary-tables-intermediate-results.sql) · [Previous: 086](086-materialized-views-and-refresh-strategies.md) · **Next: 088 — Stored functions and procedures** (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

After this lesson you can (1) choose between a CTE, derived table and temporary table; (2) explain session scope and transaction cleanup; (3) distinguish PostgreSQL temporary-table behavior from portable SQL; (4) build a safe intermediate aggregation; (5) check for duplicate keys and reconcile totals. Prerequisites: SELECT, GROUP BY, joins, transactions, and [Chapter 065](../part-07-subqueries/065-common-table-expressions-with.md).

**Production motivation:** a data engineer may stage an expensive transformation before a downstream join; a DBRE/SRE must understand the resulting temp-file I/O, temp-table lifecycle, session pooling risks and resource consumption. Intermediate materialization is a deliberate design decision, not automatically a performance improvement.

## 2. Concepts and syntax (5–15 minutes)

A **derived table** is a subquery in FROM; a **CTE** is a named query expression scoped to a statement. Neither creates a persistent database table. PostgreSQL may inline or materialize a nonrecursive, side-effect-free CTE depending on its use and optimizer decisions; `MATERIALIZED` and `NOT MATERIALIZED` are PostgreSQL-specific controls. A **temporary table** is a real relation in a session-specific temporary schema, visible only to that session; it may have indexes and statistics and can be queried across statements in the same session.

| Technique | Lifetime | Writes catalog/relations? | Typical use |
|---|---|---|---|
| Derived table | One statement | No user table | Simple single-use transformation |
| CTE (`WITH`) | One statement | No user table | Readable multi-stage SQL |
| `CREATE TEMP TABLE` | Session, or shorter with `ON COMMIT` | Yes, temporary relation | Reuse across statements, inspect intermediate data |
| Permanent staging table | Until explicitly removed | Yes, persistent relation | Shared pipeline state; requires operational change control |

**Portable pattern:** `WITH paid AS (SELECT ...)` is broadly supported. **PostgreSQL-specific:** `CREATE TEMP TABLE ... ON COMMIT DROP`, `ON COMMIT DELETE ROWS`, `pg_temp`, and `ANALYZE` of a temp table. Some vendors support different temp-table naming, visibility, commit behavior, and DDL transaction semantics. SQL Server commonly uses `#temp`; Snowflake uses `CREATE TEMPORARY TABLE`. Do not assume equivalent behavior without testing.

PostgreSQL `ON COMMIT PRESERVE ROWS` (default) keeps rows until session end; `DELETE ROWS` clears rows at commit; `DROP` drops the table at commit. A temp table can shadow a permanent table of the same unqualified name; qualify permanent references and avoid reused names. Session pools can retain temp objects, whereas transaction pools may not preserve session affinity. Temporary table data are not replicated like permanent application data; they still consume memory and disk, and temp relations can generate local I/O.

## 3. Walkthrough: aggregate synthetic payments (15–30 minutes)

Suppose six synthetic orders exist: three paid for customer 101 (10.00, 15.00, 5.00), one pending for customer 101 (99.00), one paid for customer 102 (20.00), and one failed for customer 103 (50.00). Our reporting grain is **one row per customer with paid orders**.

**Portable, statement-scoped CTE:**

```sql
WITH orders(order_id, customer_id, status, amount) AS (
  VALUES (1,101,'paid',10.00), (2,101,'paid',15.00),
         (3,101,'pending',99.00), (4,102,'paid',20.00),
         (5,103,'failed',50.00), (6,101,'paid',5.00)
), paid AS (
  SELECT customer_id, COUNT(*) AS paid_count, SUM(amount) AS paid_total
  FROM orders WHERE status = 'paid'
  GROUP BY customer_id
)
SELECT customer_id, paid_count, paid_total
FROM paid ORDER BY customer_id;
```

Expected:

| customer_id | paid_count | paid_total |
|---:|---:|---:|
| 101 | 3 | 30.00 |
| 102 | 1 | 20.00 |

**PostgreSQL-specific isolated example (not the canonical read-only lab):** Execute only in a disposable PostgreSQL 18 database with a dedicated session and explicit approval for temporary DDL.

```sql
BEGIN;
CREATE TEMP TABLE tmp_087_paid ON COMMIT DROP AS
SELECT customer_id, COUNT(*) AS paid_count, SUM(amount) AS paid_total
FROM (VALUES (101,'paid',10.00::numeric), (101,'paid',15.00),
             (101,'paid',5.00), (102,'paid',20.00),
             (101,'pending',99.00)) AS o(customer_id,status,amount)
WHERE status = 'paid' GROUP BY customer_id;
SELECT * FROM pg_temp.tmp_087_paid ORDER BY customer_id;
ROLLBACK;
```

`ROLLBACK` removes this transaction-created temp table; `ON COMMIT DROP` would remove it on successful commit. This example deliberately avoids a persistent schema change. For repeated joins over a large temp table, consider `ANALYZE pg_temp.tmp_087_paid` in an isolated environment, then measure with `EXPLAIN (ANALYZE, BUFFERS)` only when authorized; that option executes the query.

**Performance trade-off:** a temp table may avoid recomputation and allow indexing/statistics, but incurs creation, population, cleanup, and I/O overhead. A CTE may be faster for a small one-use result. Compare plans and measured workloads rather than asserting a universal winner.

## 4. Hands-on lab (30–50 minutes)

Use only a disposable PostgreSQL 18 database named `sql_tutorials`, never production credentials. The [canonical read-only SQL lab](../labs/087-temporary-tables-intermediate-results.sql) models the intermediate result using CTEs and synthetic `VALUES`, so it does **not** create a temp table or any persistent object.

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/087-temporary-tables-intermediate-results.sql
```

Run from the repository root. The lab checks PostgreSQL major version 18 and database identity, uses a read-only transaction with local statement and lock timeouts, compares the complete two-row result using two-way `EXCEPT ALL`, checks input row counts and paid totals, and ends with `ROLLBACK`. Expected: six source rows; four paid rows; two customer groups; 50.00 total paid; customer 101 has three paid orders totaling 30.00 and customer 102 has one totaling 20.00.

**Exercises:** (1) Change the grouping to include `status`; predict how many groups appear. (2) Explain why a CTE is safer than a session temp table for a read-only reporting role. (3) In a *separate disposable session*, run the temp-table example and confirm it disappears after rollback. (4) Identify why summing all orders would overstate revenue by 149.00. (5) Explain the risks of using temp tables behind transaction-pooling middleware.

## 5. Validation, troubleshooting and guardrails (50–55 minutes)

- **Relation not found:** verify the same backend session and whether `ON COMMIT DROP` or a rollback removed the temp relation. A CTE is not visible to a second statement.
- **Unexpected totals:** filter paid status before aggregation; compare source count and `SUM` against intermediate totals. Check join fan-out and NULL amounts.
- **Performance regression:** inspect row counts, temp file creation, disk capacity, `temp_bytes` statistics and plans; avoid assuming temp tables always improve speed.
- **Connection pool issues:** session-scoped objects are unsafe to assume with transaction pooling; prefer statement-scoped CTEs unless session affinity is guaranteed.
- **Safety:** canonical lab is read-only; temporary DDL example is optional and must remain in an isolated disposable database. Do not create permanent staging tables, alter production roles, or run `EXPLAIN ANALYZE` on production without approval.
- **Evidence:** for runtime acceptance retain PostgreSQL version, database identity, lab SHA, command, exit code, full output, assertions, and cleanup evidence. Authorship and static reasoning are **not** PostgreSQL 18 runtime certification.

## 6. Review questions with answers (55–60 minutes)

1. **What is the lifetime of a CTE?** One SQL statement.
2. **What does `ON COMMIT DROP` do in PostgreSQL?** Drops the temporary table at transaction commit.
3. **Why choose a temp table?** Reuse intermediate rows across statements, optionally with indexes/statistics, when measured benefits outweigh overhead.
4. **Why can a temp table fail with transaction pooling?** Later statements may run on different server sessions.
5. **Why is a two-way `EXCEPT ALL` useful?** It detects both missing and unexpected rows, including multiplicity differences.
6. **What must be recorded before claiming runtime validation?** An actual isolated PostgreSQL 18 execution and reproducible evidence.

## References

- [PostgreSQL 18 — CREATE TABLE (temporary tables and ON COMMIT)](https://www.postgresql.org/docs/18/sql-createtable.html)
- [PostgreSQL 18 — WITH queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — ANALYZE](https://www.postgresql.org/docs/18/sql-analyze.html)
- [PostgreSQL 18 — Database activity statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Validation status:** authored; targeted static/manual reasoning only. Independent editorial review, comprehensive automated SQL syntax/link QA, and actual isolated PostgreSQL 18 execution remain pending.
