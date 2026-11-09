# 033 — UPDATE with Safe Predicates and Preview Queries

**Part 04 — Data Modification & Transaction Fundamentals** · **60 minutes** · **PostgreSQL 18 isolated lab**

[Master TOC](../MASTER-TOC.md) · [Previous: 032](032-insert-select-and-bulk-loading-fundamentals.md) · [SQL lab](../labs/033-update-safe-predicates-preview.sql) · [Status](../STATUS-TRACKER.md)

> **Safety:** Execute mutations only in an independently verified, disposable PostgreSQL 18 instance using synthetic data and nonproduction credentials. The lab requires the dedicated `sql_tutorials` database, creates temporary tables, and rolls back. Database/version checks are *additional* guards, not proof that an endpoint is nonproduction. Never run these examples against production.

## 0–5 minutes — Objectives and prerequisites

After this chapter, you can: explain UPDATE semantics; write narrowly scoped WHERE predicates; preview exactly which rows would change; detect unintended row counts; use PostgreSQL RETURNING to inspect changes; reason about NULL and concurrent writes; and build a safe DBRE/SRE change checklist.

Prerequisites: [WHERE](../part-02-filtering/011-where-and-comparison-operators.md), [keys](../part-03-modeling/024-primary-keys-natural-keys-surrogate-keys-and-unique.md), [INSERT](031-insert-single-row-and-multi-row-records.md). Later chapters cover transaction isolation and advanced concurrency.

## 5–15 minutes — UPDATE fundamentals

Portable SQL commonly uses:

```sql
UPDATE order_events
SET processing_status = 'reviewed'
WHERE event_id = 'EV-102'
  AND processing_status = 'pending';
```

`SET` specifies new values. `WHERE` selects candidate rows; omitting it can update **every row**. A predicate that matches zero rows is not a SQL error. Use a stable unique key whenever possible, and add the expected current state for an optimistic guard. SQL does not promise an UPDATE processing order.

A safe **preview** uses the same WHERE predicate:

```sql
SELECT event_id, processing_status
FROM order_events
WHERE event_id = 'EV-102'
  AND processing_status = 'pending'
ORDER BY event_id;
```

The preview must run on the same trusted connection and ideally in the same transaction as the change. Even then, under PostgreSQL's default READ COMMITTED isolation, concurrent transactions can alter eligible rows between statements. For sensitive changes, plan row locking, expected-state predicates, reconciliation, and an approved concurrency strategy; preview alone is not a concurrency guarantee.

### NULL and expressions

`status = NULL` is not true; use `status IS NULL`. `SET amount = amount + 1` calculates from the row's existing value. Use exact `NUMERIC` for money. An UPDATE can violate CHECK, UNIQUE, NOT NULL or foreign-key constraints and fail.

**Portability:** Basic UPDATE/SET/WHERE is broadly portable. PostgreSQL `RETURNING` and `UPDATE ... FROM`, SQL Server `OUTPUT`, MySQL multi-table UPDATE and vendor-specific row-limit syntax are **not** interchangeable. SQL Server and other engines have different locking/isolation details.

## 15–30 minutes — Worked example: correct one event

Synthetic staging data:

| Event | Status | Amount |
|---|---|---:|
| EV-101 | pending | 12.50 |
| EV-102 | pending | 20.00 |
| EV-103 | reviewed | 7.25 |
| EV-104 | pending | 5.00 |

Requirement: mark **only EV-102** reviewed, provided it is still pending. The preview should return one row, EV-102. Then run:

```sql
UPDATE order_events
SET processing_status = 'reviewed'
WHERE event_id = 'EV-102'
  AND processing_status = 'pending'
RETURNING event_id, processing_status;
```

`RETURNING` is PostgreSQL syntax. Expected output is one row: `EV-102 | reviewed`. Afterwards, exactly **2 pending** and **2 reviewed** rows remain, with the original total amount **44.75** unchanged. The lab asserts both the row identities and totals, and ends in ROLLBACK.

**Important:** A zero-row result could mean the event is absent, already processed, or concurrently modified. Investigate rather than forcing a broader UPDATE.

## 30–50 minutes — Hands-on lab

1. Use the isolated PostgreSQL 18 lab setup in [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Independently verify host, port, database, role, and container before connecting.
2. Inspect the entire [Chapter 033 SQL lab](../labs/033-update-safe-predicates-preview.sql), including the transaction, temporary objects, environment checks, and final ROLLBACK.
3. From the repository root run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/033-update-safe-predicates-preview.sql
```

4. Confirm preview ID EV-102; the UPDATE returns exactly EV-102; the acceptance row reads `PASS`; the totals remain 44.75.
5. **Exercise A:** Change the target to EV-101 in a *local copy*, updating the expected ID and state assertions. Predict the two reviewed rows.
6. **Exercise B:** Replace the status predicate with `processing_status = 'reviewed'`. Explain why the target now matches zero rows and why the fail-closed assertion is useful.
7. **Exercise C:** Add a synthetic event with NULL status in a local copy (adjust table definition if needed); demonstrate `IS NULL` versus `= NULL`.
8. **Exercise D:** Design an operational change plan for a hypothetical 50,000-row correction: preview IDs, verify business ownership, batch carefully, capture before/after counts, monitor locks/WAL/replication, and define stop and recovery conditions. Do not run this on shared systems.

## 50–55 minutes — Troubleshooting and guardrails

| Symptom | Possible cause | Safe response |
|---|---|---|
| 0 rows updated | Predicate mismatch, already processed, or concurrent change | Recheck key and expected state; do not widen blindly |
| Too many rows eligible | Missing or broad WHERE clause | Abort before write; inspect exact candidate IDs |
| `23514` or `23502` | CHECK or NOT NULL violation | ROLLBACK; correct mapping/input |
| `55P03` or timeout | Lock contention | Stop and investigate blockers; avoid raising timeouts blindly |
| `40P01` | Deadlock | Roll back and review transaction order/retry policy |
| `25P02` | Earlier transaction error | ROLLBACK and diagnose original error |
| Different result after preview | Concurrent changes or isolation behavior | Use approved locking/expected-state strategy |

**DBRE/SRE change checklist:** verify nonproduction or approved production target independently; identify unique keys; preview count and IDs; record pre-change values; require a reviewed WHERE clause; choose transaction size; set lock/statement timeouts; verify affected rows and unchanged invariants; monitor lock waits, WAL, replica lag and application error rates; plan rollback and restore. A transaction rollback is not a substitute for tested backup/recovery.

## 55–60 minutes — Review questions and answers

1. **What happens without WHERE?** Every row may be eligible for update.
2. **Does a SELECT preview guarantee identical UPDATE rows?** No; concurrency can change the match set.
3. **Why include the current status in WHERE?** It rejects unexpected state and helps detect stale assumptions.
4. **How do you test for NULL?** `IS NULL`, not `= NULL`.
5. **What is RETURNING?** PostgreSQL's way to return rows affected by a write.
6. **Does an UPDATE of zero rows raise an error?** Normally no; enforce expected counts explicitly.
7. **What must be checked after the write?** Exact affected IDs, row count, new values and unchanged invariants.
8. **Is a database-name guard sufficient for production safety?** No; independently verify the endpoint and isolation.

## References

- [PostgreSQL 18 UPDATE](https://www.postgresql.org/docs/18/sql-update.html)
- [PostgreSQL 18 RETURNING](https://www.postgresql.org/docs/18/dml-returning.html)
- [PostgreSQL 18 transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html)

**Next:** Chapter 034 — DELETE with safe predicates and referential implications.

**Validation:** Authored material requires separate independent editorial review, comprehensive static/syntax checks, and evidence-backed execution on an isolated PostgreSQL 18 instance. No runtime acceptance is implied by publication.
