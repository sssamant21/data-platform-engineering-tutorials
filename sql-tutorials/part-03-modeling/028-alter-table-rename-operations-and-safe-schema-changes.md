# Chapter 028 — ALTER TABLE, Rename Operations, and Safe Schema Changes

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 027](027-identity-columns-sequences-and-generated-values.md) · [Next: 029](../MASTER-TOC.md)
>
> **Part 03 · 60 minutes · PostgreSQL 18 isolated lab**
>
> **Status:** Authored; targeted static inspection only. Independent editorial review, comprehensive syntax checks, and actual PostgreSQL 18 runtime validation pending.

## Learning objectives and agenda (0–5 minutes)

Explain how ALTER TABLE evolves an existing schema; distinguish add, rename, type change, default and constraint operations; identify locking, compatibility, and rollback risks; and design an expand–migrate–contract release. Prerequisites: [022 — DDL](022-create-database-create-schema-and-create-table.md), [025 — foreign keys](025-foreign-keys-and-referential-integrity.md), and [026 — constraints](026-not-null-check-default-and-constraint-validation.md).

| Time | Activity |
|---|---|
| 0–5 min | Objectives, isolation and prerequisite check |
| 5–15 min | Syntax, semantics, and portability |
| 15–30 min | Walkthrough and expected results |
| 30–50 min | Synthetic PostgreSQL 18 lab and practice |
| 50–55 min | Troubleshooting and deployment safeguards |
| 55–60 min | Questions, answers and references |

## Concepts and syntax (5–15 minutes)

**DDL** changes structure rather than merely updating row values. An ALTER can change a table's columns, defaults, constraints, and names. Even a metadata-only change can require a strong lock; never equate "fast SQL" with "zero impact." The following patterns are broadly recognizable SQL, but details and locking differ across engines:

```sql
ALTER TABLE orders ADD COLUMN source_system VARCHAR(30);
ALTER TABLE orders ALTER COLUMN source_system SET DEFAULT 'batch';
ALTER TABLE orders RENAME COLUMN source_system TO ingestion_source;
ALTER TABLE orders ADD CONSTRAINT positive_total CHECK (order_total >= 0);
```

PostgreSQL supports the shown syntax; SQL Server uses `sp_rename` for some renames, MySQL uses its own `CHANGE COLUMN` / `RENAME COLUMN` variations, and Oracle and cloud warehouses differ on online DDL and constraints. **Verify syntax and operational semantics on the actual vendor/version.**

In PostgreSQL, `ALTER TABLE ... ADD COLUMN` without a default is commonly a catalog-only operation, but still takes a lock. A non-volatile constant default can avoid rewriting existing rows on supported versions. A volatile default or a type conversion can force a rewrite; adding or validating a constraint may scan data. `ALTER COLUMN ... TYPE ... USING` is PostgreSQL-specific for explicit conversion:

```sql
ALTER TABLE sample ALTER COLUMN amount TYPE NUMERIC(12,2)
  USING amount::NUMERIC(12,2);
```

A narrower type may fail or lose precision. A column rename changes the database identifier, **not** application SQL, ORM mappings, ETL code, dashboards, or external contracts automatically. PostgreSQL dependencies may be tracked internally, but client queries still need coordinated releases.

### Expand–migrate–contract

1. **Expand:** Add a nullable replacement column; deploy readers that tolerate both old and new schemas.
2. **Migrate:** Backfill in bounded batches with checks, observe locks/WAL/replication lag, and switch writers/readers deliberately.
3. **Contract:** After verification and a rollback window, enforce constraints and remove obsolete fields in a separately approved release.

For large tables, adding a validated `NOT NULL` or changing a type deserves a separate staging rehearsal and measured lock budget. PostgreSQL-specific `CHECK (...) NOT VALID` followed by `VALIDATE CONSTRAINT` can separate creation from validation; `NOT VALID` does **not** mean future writes bypass the constraint. A CHECK evaluates UNKNOWN as accepted, so combine it with `NOT NULL` when required.

## Walkthrough: synthetic ingestion events (15–30 minutes)

We begin with two records:

| event_id | event_code | amount |
|---:|---|---:|
| 1 | SYN-A | 12.50 |
| 2 | SYN-B | 7.25 |

After adding `source_system TEXT`, the existing two rows have **NULL** in that column. Setting `DEFAULT 'batch'` affects later inserts, **not** existing NULLs. Renaming the column to `ingestion_source` preserves its values. A new record `SYN-C` inserted without the column receives `batch`.

Expected final output, sorted by event_id:

| event_id | event_code | amount | ingestion_source |
|---:|---|---:|---|
| 1 | SYN-A | 12.50 | legacy |
| 2 | SYN-B | 7.25 | legacy |
| 3 | SYN-C | 5.00 | batch |

Expected count **3**, total **24.75**, and no NULL ingestion sources after an explicit backfill. The lab adds a positive-amount CHECK and proves a negative value is rejected with SQLSTATE **23514**. It also verifies a deliberate duplicate event code is rejected with SQLSTATE **23505**.

## Hands-on lab (30–50 minutes)

Open [028 SQL lab](../labs/028-alter-table-safe-schema-changes.sql). Use **only** a disposable PostgreSQL 18 database named `sql_tutorials`; confirm the server and credentials are isolated. Do not point this file at a shared, staging, or production database.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/028-alter-table-safe-schema-changes.sql
```

The SQL file begins a transaction, checks PostgreSQL major version/database/primary status, sets timeouts, creates a temporary table, performs the changes, asserts expected results, and finishes with `ROLLBACK`. A database name check is **not proof of isolation**; verify host/container identity before connecting. The lab does not modify persistent tables.

**Practice A (5 min):** Before running, predict the two old rows' `source_system` values immediately after `ADD COLUMN` and `SET DEFAULT`. Answer: both remain NULL until updated.

**Practice B (5 min):** Explain why renaming `source_system` to `ingestion_source` can break an ETL pipeline. Answer: the pipeline may still query the old identifier; deploy compatibility logic before renaming.

**Practice C (5 min):** Modify a **copy** of the lab to insert an event with amount 0.00. The CHECK `amount >= 0` permits zero. Change it to `amount > 0` and predict a CHECK violation. Keep the entire exercise inside the temporary rollback transaction.

**Practice D (5 min):** Write a migration checklist for a hypothetical 500-million-row table: dependencies, size, lock/statement timeout, rewrite risk, disk/WAL headroom, replicas, backups, rollout/rollback, validation queries, and stakeholder approval. Do not run the migration.

## Troubleshooting and production safeguards (50–55 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| `column does not exist` | Application still uses renamed column | Check deployed SQL/contracts; restore compatibility before cutover |
| `lock timeout` / blocked sessions | Concurrent activity and DDL lock contention | Abort and inspect blockers in a safe read-only session; schedule/replan |
| CHECK violation | Historical or incoming values break the rule | Profile bad rows; correct through approved pipeline before validating |
| Type conversion fails | Non-castable values or narrowing | Inspect samples and `USING` expression in disposable staging |
| High WAL / replication lag | Rewrite or bulk backfill | Stop rollout; reduce batches and review capacity/replica health |

**Production change gates:** Confirm owner approval and change window; inventory readers/writers and dependencies; snapshot/restore readiness; capture pre-change schema and counts; use a short `lock_timeout` and bounded `statement_timeout`; monitor lock waits, CPU, disk, WAL and replication; record rollback decision points. A transactional rollback is not a substitute for an application-compatible reversal after deployment. Avoid `DROP COLUMN` or destructive type conversions until the contract phase is approved.

## Review questions with answers (55–60 minutes)

1. **Does SET DEFAULT backfill old NULLs?** No. It applies to future inserts that omit the column (or use DEFAULT).
2. **Does a rename update every application query?** No. External clients must be updated or made compatible.
3. **Can ALTER TABLE be low-cost yet block writers?** Yes. Metadata-only operations may still require strong locks.
4. **Why split constraint creation and validation?** To control when existing rows are scanned; future writes must still obey a NOT VALID CHECK in PostgreSQL.
5. **Why is a type change risky?** It may rewrite a large table, take locks, fail casts, or alter precision.
6. **What is the safest learning environment?** An independently verified disposable PostgreSQL 18 instance with synthetic data and rollback.

## References and next chapter

- [PostgreSQL 18 — ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
- [PostgreSQL 18 — DDL](https://www.postgresql.org/docs/18/ddl.html)
- [PostgreSQL 18 — Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)

**Next:** Chapter 029 — Normalization (1NF–3NF) and intentional denormalization. Follow the [Master TOC](../MASTER-TOC.md) until published.
