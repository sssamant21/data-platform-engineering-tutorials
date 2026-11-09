# 031 — INSERT Single-Row and Multi-Row Records

**Part 04 — Data Modification & Transaction Fundamentals** · **60 minutes** · **Audience:** data engineers, DBREs, SREs · **Lab:** isolated PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Previous: Lab 03](../part-03-modeling/030-lab-03-design-and-build-a-normalized-operational-schema.md) · [SQL lab](../labs/031-insert-single-row-and-multi-row-records.sql) · [Status tracker](../STATUS-TRACKER.md)

> **Safety:** INSERT changes data. Run the lab **only** against a verified disposable PostgreSQL 18 instance and dedicated `sql_tutorials` database, with synthetic rows and no production credentials. The database-name guard is not proof of isolation. The lab creates temporary objects and explicitly rolls back; inspect host, port, database, user and container *before* running it.

## 0–5 min — Learning objectives and prerequisites

After this chapter, you can (1) insert one row and several rows, (2) name target columns and understand defaults, (3) distinguish omitted columns from explicit NULL, (4) recognize constraint failures and transaction atomicity, (5) verify inserted rows and reconcile counts, and (6) plan safe, idempotent ingestion. Prerequisites: [tables and columns](../part-01-fundamentals/004-databases-schemas-tables-rows-columns.md), [data types](../part-03-modeling/023-choosing-numeric-character-boolean-and-temporal-types.md), [keys](../part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md), and [constraints](../part-03-modeling/026-not-null-check-default-and-constraint-validation.md).

## 5–15 min — INSERT fundamentals

An `INSERT` adds rows to a table. The common, portable pattern is:

```sql
INSERT INTO customers (customer_id, customer_name, region)
VALUES (1, 'Sample Ada', 'EAST');
```

Always **name the destination columns**. Omitting the column list couples values to physical table order and breaks when schema evolves. A multi-row insert uses one `VALUES` list per row:

```sql
INSERT INTO customers (customer_id, customer_name, region)
VALUES
  (2, 'Sample Ben', 'WEST'),
  (3, 'Sample Cy', 'EAST');
```

The examples assume a disposable table with compatible column definitions; the runnable lab creates it. Strings use single quotes; `NULL` is a keyword, not the text `'NULL'`. Use typed parameters in applications rather than interpolating untrusted strings into SQL. **Portable concept:** explicit-column `INSERT ... VALUES`. **Dialect differences:** auto-generated identifiers, returning generated rows, error-handling syntax and batch limits vary; `RETURNING` is PostgreSQL-specific in this tutorial (covered in Chapter 037).

A column omitted from the target list receives its defined default, or NULL if nullable and no default exists. Explicit `NULL` **does not invoke the default**. `NOT NULL`, `UNIQUE`, `CHECK`, and foreign keys are checked during writes. Multi-row INSERT is one statement: if a row violates a nondeferrable constraint, the statement does not partially succeed. A failed statement inside a PostgreSQL transaction leaves the transaction in an error state until rollback or savepoint recovery.

## 15–30 min — Worked synthetic retail example

Imagine a small ingestion staging table with a unique `source_event_id` for deduplication, a nonnegative amount, and a default status. The [lab](../labs/031-insert-single-row-and-multi-row-records.sql) builds a temporary `ingest_events` table, then executes:

```sql
INSERT INTO ingest_events (source_event_id, customer_code, amount)
VALUES ('EVT-001', 'C-001', 12.50);

INSERT INTO ingest_events (source_event_id, customer_code, amount, status)
VALUES
  ('EVT-002', 'C-002', 20.00, 'READY'),
  ('EVT-003', 'C-001', 7.25, 'HELD');
```

Expected rows, ordered by event ID:

| Event | Customer | Amount | Status |
|---|---|---:|---|
| EVT-001 | C-001 | 12.50 | NEW (default) |
| EVT-002 | C-002 | 20.00 | READY |
| EVT-003 | C-001 | 7.25 | HELD |

Expected `COUNT(*) = 3`, `SUM(amount) = 39.75`, and `NEW = 1`, `READY = 1`, `HELD = 1`. A fourth row with an existing `source_event_id` fails with SQLSTATE `23505`. A negative amount fails `23514`. Explicit NULL for `status` fails `23502`. The lab tests these failures inside PL/pgSQL exception subtransactions so the outer transaction can continue; it verifies the row count stays at three.

**Data engineering:** source IDs are business-level idempotency keys. A retry of an already ingested event should not silently create duplicates. Do not treat `ON CONFLICT DO NOTHING` as a universal fix: it can hide upstream errors; design explicit retry and reconciliation policy (Chapter 036). **DBRE/SRE:** bulk inserts generate WAL, consume storage, may contend on unique indexes and foreign keys, and can increase replication lag. Batch size and transaction duration must be measured under staging load, not guessed.

## 30–50 min — Hands-on PostgreSQL 18 lab

1. Start the isolated disposable lab from [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Independently verify host, port, database and credentials; use only `sql_tutorials`.
2. Read the complete [031 SQL lab](../labs/031-insert-single-row-and-multi-row-records.sql) before running it. It guards PostgreSQL major version, database name and standby status, sets short timeouts, creates a temporary table, inserts three fictional events, asserts results, tests three expected errors, and rolls back.
3. From repository root run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/031-insert-single-row-and-multi-row-records.sql
```

4. Confirm the final `lab_acceptance = PASS`, `expected_rows = 3`, `expected_amount = 39.75`. With `ON_ERROR_STOP=1`, an unexpected error should produce a nonzero exit.
5. **Practice A:** In a local copy, add `EVT-004` amount `10.00` with no status; predict four rows, sum `49.75`, and two `NEW` rows. Update assertions before executing.
6. **Practice B:** Replace an omitted status with explicit `NULL`; predict SQLSTATE `23502`, not the default `NEW`.
7. **Practice C:** Explain why an unguarded retry using the same source event ID must fail, and propose a reviewed deduplication policy.
8. **Practice D:** Explain why a batch with one invalid row cannot be counted as partially loaded.

The lab intentionally does not persist any data; a successful rollback does not excuse running it against an unverified endpoint.

## 50–55 min — Validation, troubleshooting and safeguards

| Symptom | Meaning | Safe response |
|---|---|---|
| `23505` | Duplicate unique event ID | Inspect source IDs, replay semantics and deduplication policy |
| `23514` | CHECK constraint rejected amount/status | Quarantine malformed source row; never disable constraint casually |
| `23502` | Required column received NULL | Supply valid value or omit column when a default is intended |
| `25P02` | Earlier error aborted PostgreSQL transaction | Roll back; rerun cleanly after diagnosis |
| Unexpected count/sum | Missing, duplicated or altered rows | Reconcile source and destination IDs and amounts |
| Wrong database/version guard | Unsafe or unsupported target | Stop and inspect connection configuration |

**Production guardrails:** require explicit change approval, workload sizing, unique-key policy, staging dry runs, WAL/replication monitoring, lock and statement timeouts, per-batch audit records, failure quarantine, retry strategy, and recovery plan. Prefer parameterized application inserts. Never disable integrity constraints or use production credentials in this lab. For very large imports, compare `INSERT` with PostgreSQL `COPY` (Chapter 032), noting that COPY has its own validation and transaction considerations.

## 55–60 min — Review questions with answers

1. **Why specify columns?** To avoid positional coupling and make schema changes safer.
2. **What is the difference between omitting a column and supplying NULL?** Omission uses a default if defined; explicit NULL does not.
3. **Can a three-row INSERT commit only two rows when the third violates a regular CHECK?** No; that INSERT statement fails atomically.
4. **What prevents duplicate source event IDs?** A UNIQUE constraint, combined with an explicit retry policy.
5. **Why use NUMERIC for money?** It provides exact decimal arithmetic for these values.
6. **What proves the lab was runtime validated?** Retained output, exit status, PostgreSQL 18 version and isolated instance evidence—not publication alone.

## References and next chapter

- [PostgreSQL 18 INSERT](https://www.postgresql.org/docs/18/sql-insert.html)
- [PostgreSQL 18 Default Values](https://www.postgresql.org/docs/18/ddl-default.html)
- [PostgreSQL 18 Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)
- [PostgreSQL 18 Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [Master TOC](../MASTER-TOC.md)

**Next:** Chapter 032 — INSERT ... SELECT and bulk-loading fundamentals.

**Validation distinction:** Authored/published does not imply independent editorial review, comprehensive syntax verification or actual isolated PostgreSQL 18 execution.
