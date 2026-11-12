# 106 — Backward-Compatible Migrations and Deployment Controls

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · PostgreSQL 18 focus · Beginner-friendly

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Synthetic read-only lab](../labs/106-backward-compatible-migrations-deployment-controls.sql) · [Previous: 105](105-locks-blocking-deadlocks-and-troubleshooting.md) · Next: 107 — Data quality assertions and reconciliation queries (planned)

## 1. Learning objectives and scenario (0–5 minutes)

After this lesson, explain expand–migrate–contract, identify incompatible schema changes, plan application/database rollout ordering, use migration preflight and postflight SQL, distinguish transactional DDL from nontransactional operations, and write a safe rollback/forward-recovery plan. Prerequisites: [constraints (026)](../part-03-modeling/026-not-null-check-default-and-constraint-validation.md), [transactions (038)](../part-04-data-modification/038-begin-commit-rollback-and-savepoint.md), and [locks (105)](105-locks-blocking-deadlocks-and-troubleshooting.md).

**Scenario:** A synthetic order-ingestion application currently stores `customer_name` in `orders`. A new application release needs `customer_display_name`. Old and new application versions may run concurrently during deployment. Renaming or dropping the original column immediately would break old instances.

## 2. Core concepts and deployment sequence (5–15 minutes)

A migration is a controlled change to database structure, data, or both. **Backward compatible** means the database supports the *currently deployed* clients and the intended transition clients; it does not imply indefinite compatibility.

| Phase | Database and application work | Gate |
|---|---|---|
| Expand | Add nullable new column; keep old column and existing reads/writes | Old app still works |
| Bridge | Deploy application version that can read old or new; coordinate writes to both or use a carefully reviewed database-side synchronization mechanism | Mixed-version reads/writes verified |
| Backfill | Copy historical values in bounded, restartable batches; record high-water mark | Missing/invalid count trends to zero |
| Cut over | Prefer new column only after every writer and reader supports it | Canary, error rates, reconciliation |
| Contract | Drop obsolete column only after old binaries, jobs, consumers, rollback paths and retention dependencies are retired | Approved change window and recovery plan |

**Important:** A one-time backfill does not keep values synchronized while old writers remain active. A `COALESCE(new_column, old_column)` read bridge helps readers, but it is **not** a write synchronization mechanism. Choose and test dual-write, application compatibility, or trigger-based synchronization according to system ownership. Define conflict resolution for divergent values.

**Portable SQL concepts:** `ALTER TABLE ... ADD COLUMN`, `UPDATE`, `CASE`, `COALESCE`, `COUNT`, and transactions are widely supported, but exact DDL locking, defaults, online operations, rollback behavior, and syntax differ by database. PostgreSQL-specific notes below are not universal guarantees.

## 3. Worked examples and operational decisions (15–30 minutes)

### Step A — Preflight and approval

Record change ticket, owning data/application/DBRE teams, schema version, compatible application versions, dependencies (views, ETL, CDC, reports, prepared statements), estimated row count, disk/WAL budget, replication lag, backups/restore proof, maintenance approval, success thresholds, and stop/rollback criteria. Verify deployment order with application owners. Inspect `pg_stat_activity`, relevant locks, and table size with authorized read-only access; avoid broad production catalog scans during incidents.

### Step B — Expand (illustrative DDL; **do not execute against production**)

```sql
-- PostgreSQL example only: run after approved review in an isolated environment.
ALTER TABLE training.orders
  ADD COLUMN customer_display_name text;
```

PostgreSQL `ALTER TABLE` commonly takes an `ACCESS EXCLUSIVE` lock unless the specific subform documents otherwise. Even a metadata-only operation can wait behind long transactions and block later requests. Set short `lock_timeout` and bounded `statement_timeout` for approved operations; test on realistic data.

### Step C — Compatible reads and controlled backfill

```sql
-- Portable read bridge while both columns exist.
SELECT order_id, COALESCE(customer_display_name, customer_name) AS display_name
FROM training.orders;
```

A production backfill must use stable keyset batches and commit boundaries chosen for load, replication, and rollback impact; the following is an **illustration, not an approved production job**:

```sql
-- Isolated training only; single small batch with an explicit key boundary.
UPDATE training.orders
SET customer_display_name = customer_name
WHERE order_id >= 100 AND order_id < 200
  AND customer_display_name IS NULL;
```

Do not assume a single large `UPDATE` is safe: it generates WAL, dead tuples, row locks, replica lag, and possible bloat. Throttle, measure, checkpoint progress, and ensure concurrent writers are covered. PostgreSQL supports `CREATE INDEX CONCURRENTLY` for some online indexing workflows, but it **cannot run inside a transaction block**; its failure/retry/invalid-index behavior needs a separate runbook.

### Step D — Reconcile before cutover

```sql
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE customer_display_name IS NULL) AS missing_new,
       COUNT(*) FILTER (WHERE customer_display_name IS DISTINCT FROM customer_name) AS divergent
FROM training.orders;
```

`FILTER` and `IS DISTINCT FROM` are supported in PostgreSQL 18; use `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` for broader conditional-aggregation portability. A zero divergence result is a **point-in-time** check, not proof that every concurrent writer is safe. Repeat checks across canary traffic and include downstream CDC consumers.

### Step E — Contract only after an explicit gate

Removing a column is a separate, potentially irreversible deployment. Confirm no old application instance, scheduled job, CDC consumer, or rollback image requires it. Retain restore evidence and independent approval. Never rely on `ROLLBACK` to undo a committed drop or an external side effect. PostgreSQL transactional DDL can be rolled back *before commit*, but not every database behaves this way.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Run only against a disposable PostgreSQL 18 database named `sql_tutorials`, using an unprivileged training account:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/106-backward-compatible-migrations-deployment-controls.sql
```

[Lab 106](../labs/106-backward-compatible-migrations-deployment-controls.sql) uses in-query synthetic data, a read-only transaction, version/database guards, timeouts, and multiset assertions. It models the old/new application overlap without creating tables, changing schemas, or writing rows. **It does not test DDL locking, concurrent writers, real deployment behavior, or recovery.**

Dataset: five synthetic orders; three already backfilled; two still require backfill. A compatible `COALESCE` reader returns five non-NULL names. Two legacy-only records would be invisible to a premature new-column-only reader. One proposed contraction is blocked because old readers and unsynchronized writers still exist. The SQL lab asserts these calculated expectations and ends with `ROLLBACK`.

Exercises: (1) explain why adding a nullable column precedes cutover; (2) identify which orders still need backfill; (3) describe a writer-synchronization design; (4) define an acceptance gate for contraction; (5) explain what changes if a replica falls behind; (6) draft a forward-fix plan for a failed canary.

## 5. Troubleshooting, safety and acceptance (50–55 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| `lock_timeout` during DDL | Existing transactions hold incompatible locks | Stop; inspect blockers and retry only with approval |
| New-column NULLs persist | Backfill incomplete or old writer still active | Pause cutover; inspect writer versions and sync path |
| CDC consumer errors | Schema contract changed unexpectedly | Restore compatible producer/consumer path; verify offsets |
| Replica lag / WAL growth | Backfill too large or too fast | Throttle/stop batches; monitor replication and disk |
| Mismatch count rises | Conflicting dual writes or stale data | Stop cutover, isolate owner, reconcile with audit evidence |
| Old application errors after contract | Premature removal of old schema | Execute preapproved recovery/forward-fix, not ad hoc DDL |

**Safety guardrails:** No production credentials or patient data; never perform destructive DDL in this lab. Approval must cover owner, exact SQL, application compatibility matrix, bounded timeouts, rollback/forward-fix, backup/restore evidence, canary metrics, and stop criteria. The migration can affect replication, long transactions, and connection pools even when DDL appears small. Read-only SQL is not a substitute for an isolated end-to-end deployment rehearsal.

**Validation status:** Authored and targeted statically reasoned. Independent editorial review, comprehensive SQL parser/link QA, and actual PostgreSQL 18 execution with retained evidence remain pending. All expected outputs are calculated, not observed.

## 6. Review questions and answers (55–60 minutes)

1. **Why expand first?** Old and new application versions can coexist during rollout.
2. **Does backfill alone protect new writes?** No; ongoing old writers need synchronization or coordinated retirement.
3. **Why prefer a nullable addition initially?** It avoids immediately requiring every existing row and old writer to supply a new value.
4. **What is the contraction gate?** Verified compatible readers/writers, zero required dependencies, reconciliation, restore plan, and approval.
5. **Is `CREATE INDEX CONCURRENTLY` transactional in PostgreSQL?** It cannot run inside an explicit transaction block.
6. **Can `COALESCE` guarantee consistent writes?** No; it only chooses a read value.
7. **What should DBRE monitor?** Lock waits, WAL/disk, replication lag, query errors, latency, and data reconciliation.
8. **What follows?** Chapter 107 — Data quality assertions and reconciliation queries.

## References

- [PostgreSQL 18 — ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
- [PostgreSQL 18 — Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [PostgreSQL 18 — CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)
- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 — Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
