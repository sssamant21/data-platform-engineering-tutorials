# 034 — DELETE with Safe Predicates and Referential Implications

**Part 04 — Data Modification & Transaction Fundamentals** · **60 minutes** · **PostgreSQL 18 isolated lab**

[Master TOC](../MASTER-TOC.md) · [Previous: 033](033-update-with-safe-predicates-and-preview-queries.md) · [SQL lab](../labs/034-delete-safe-predicates-referential-implications.sql) · [Status](../STATUS-TRACKER.md)

> **Safety:** DELETE removes rows. Run the companion lab **only** against a separately verified, disposable PostgreSQL 18 instance with nonproduction credentials. The lab creates temporary tables, guards the database/version, uses a transaction, and rolls back. A database name alone does not establish safety. Never run these examples on production.

## 0–5 minutes — Learning outcomes and prerequisites

You will be able to: (1) distinguish DELETE from SELECT and UPDATE, (2) preview exact target rows with a stable key and expected state, (3) explain foreign-key RESTRICT/NO ACTION, CASCADE, and SET NULL effects, (4) reconcile affected rows and surviving child rows, (5) identify concurrency and rollback limitations, and (6) prepare a DBRE/SRE deletion change plan.

Prerequisites: [WHERE](../part-02-filtering/011-where-and-comparison-operators.md), [foreign keys](../part-03-modeling/025-foreign-keys-and-referential-integrity.md), and [UPDATE safeguards](033-update-with-safe-predicates-and-preview-queries.md).

## 5–15 minutes — Concepts and portable SQL

The widely portable form is:

```sql
DELETE FROM order_events
WHERE event_id = 'EV-104'
  AND processing_status = 'cancelled';
```

**Omitting WHERE can delete all rows.** A DELETE that affects zero rows is not necessarily an error. Use a unique key and an expected-state condition, and validate the target set **before** deletion:

```sql
SELECT event_id, processing_status
FROM order_events
WHERE event_id = 'EV-104'
  AND processing_status = 'cancelled'
ORDER BY event_id;
```

A SELECT preview is not a concurrency guarantee: other transactions can change the matching set. A transaction and appropriate locks/expected-state predicates may be needed for approved operational changes. Rows deleted inside an uncommitted transaction can normally be restored with ROLLBACK; after COMMIT, recovery generally requires an explicitly designed restore or compensating workflow. Do not assume backups or PITR have been tested.

### Referential actions

| Parent deletion with child rows | Result | Operational consideration |
|---|---|---|
| `ON DELETE NO ACTION` (default) | Rejects a violating delete when checked (potentially deferred if the constraint is deferrable) | Keeps parent/child integrity |
| `ON DELETE RESTRICT` | Rejects referenced parent deletion immediately | Cannot defer the referential check |
| `ON DELETE CASCADE` | Automatically deletes referencing children | Can expand blast radius dramatically |
| `ON DELETE SET NULL` | Clears referencing FK columns | Requires nullable columns and appropriate application semantics |

**Important:** Referential actions are defined on the *child foreign key*. Deleting a child row does not normally delete its parent. In systems with soft-delete policies, a status flag may be more appropriate than physical deletion, but retention, legal hold, and audit requirements must be reviewed by owners.

**Dialect notes:** Standard DELETE/WHERE and foreign keys are broadly portable, but feature support and behavior vary. PostgreSQL supports `DELETE ... RETURNING` and `DELETE ... USING`; SQL Server offers `OUTPUT`; MySQL has vendor-specific multi-table DELETE forms. Do not assume syntax or cascades behave identically across platforms.

## 15–30 minutes — Worked synthetic example

Assume customers C-01 and C-02, with orders O-101 (C-01), O-102 (C-01), and O-103 (C-02). Requirement: remove **only cancelled order O-102**; preserve both customers and all other orders.

```sql
SELECT order_id, customer_id, order_status
FROM orders
WHERE order_id = 'O-102'
  AND order_status = 'cancelled';
-- Expected: O-102 | C-01 | cancelled
```

After confirming the preview, PostgreSQL can capture exactly which row was deleted:

```sql
DELETE FROM orders
WHERE order_id = 'O-102'
  AND order_status = 'cancelled'
RETURNING order_id, customer_id;
-- Expected: O-102 | C-01
```

Expected post-change counts: **2 customers, 2 orders**, surviving order IDs **O-101, O-103**, and **zero orphan orders**. The accompanying lab uses an explicit foreign key with `ON DELETE RESTRICT` and verifies that attempting to delete C-01 while O-101 references it raises SQLSTATE `23503` without changing any rows. The expected error is caught inside PL/pgSQL so the exercise continues safely.

## 30–50 minutes — Hands-on PostgreSQL 18 lab

1. Prepare the isolated PostgreSQL 18 environment from [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Verify host, port, container, database, role and environment independently.
2. Inspect the entire [SQL lab](../labs/034-delete-safe-predicates-referential-implications.sql), including its environment guard, temporary tables, assertions, negative test, and ROLLBACK.
3. From the repository root, run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/034-delete-safe-predicates-referential-implications.sql
```

4. Confirm preview returns O-102; captured DELETE output returns O-102; rejected parent deletion has SQLSTATE 23503; final acceptance displays `PASS`, 2 customers, 2 orders, 0 orphans.
5. **Exercise A:** In a local copy, change the delete predicate to a nonexistent order ID. Predict zero affected rows and the fail-closed assertion.
6. **Exercise B:** Explain why deleting C-01 before O-101 is rejected, and why a CASCADE relationship would require a separate blast-radius review.
7. **Exercise C:** Draft a safe retention-deletion proposal for a synthetic 90-day staging table: define ownership, retention policy, preview query, count/ID checks, batch boundaries, backups, audit records, monitoring, and abort conditions. Do not execute on shared systems.
8. **Exercise D:** Explain why a successful ROLLBACK lab does not establish that a committed deletion is recoverable.

## 50–55 minutes — Troubleshooting and safety review

| Symptom | Likely cause | Safe response |
|---|---|---|
| 0 rows deleted | Predicate mismatch, already removed, concurrent change | Inspect key and expected state; do not widen blindly |
| Unexpectedly many rows | Broad or missing WHERE | Stop before COMMIT; reconcile IDs and rollback |
| `23503` foreign-key violation | Parent still referenced | Preserve integrity; review child relationships and policy |
| `55P03` / lock timeout | Blocking transaction | Abort and investigate blockers |
| `40P01` deadlock | Conflicting lock acquisition | Roll back and review transaction ordering |
| `25P02` transaction aborted | Earlier statement failed | Roll back and investigate original failure |

**DBRE/SRE checklist:** obtain owner approval; verify exact target; inspect FK dependencies and cascades; confirm retention/legal-hold policy; count preview rows; record identifiers and pre-delete state securely; set conservative lock/statement timeouts; measure deleted rows via RETURNING or equivalent; check orphan counts and application invariants; monitor WAL, locks, replicas, and latency; retain evidence; define stop, rollback, and tested recovery conditions. Large deletes can create MVCC dead tuples and vacuum pressure in PostgreSQL; plan batching and maintenance capacity. Never use this training script for real deletion campaigns.

## 55–60 minutes — Review questions and answers

1. **What if DELETE has no WHERE?** All rows can be eligible.
2. **Does zero affected rows mean an error?** No; validate expected counts yourself.
3. **Why preview before DELETE?** To inspect candidate keys and business eligibility.
4. **Does preview guarantee the same DELETE set?** No, concurrency can change it.
5. **Where is ON DELETE CASCADE configured?** On the referencing child's foreign-key constraint.
6. **What happens when RESTRICT protects a referenced parent?** The deletion is rejected.
7. **Can ROLLBACK undo a committed DELETE?** No; recovery needs a separately planned mechanism.
8. **What does PostgreSQL RETURNING provide?** Data from rows affected by the DELETE.
9. **Why inspect downstream effects?** Cascades, triggers and application dependencies can enlarge impact.
10. **Does a database-name check prove isolation?** No; verify the endpoint independently.

## References

- [PostgreSQL 18 DELETE](https://www.postgresql.org/docs/18/sql-delete.html)
- [PostgreSQL 18 foreign-key constraints](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [PostgreSQL 18 RETURNING](https://www.postgresql.org/docs/18/dml-returning.html)
- [PostgreSQL 18 transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 routine vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)

**Next:** Chapter 035 — DELETE versus TRUNCATE versus DROP.

**Validation status:** Authored content; targeted static inspection only. Independent editorial review, full SQL syntax verification, and isolated PostgreSQL 18 runtime acceptance remain pending.
