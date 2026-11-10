# 037 — RETURNING, OUTPUT, and Write Verification

**Part 04 — Data Modification & Transaction Fundamentals · 60 minutes · PostgreSQL 18 lab**

**Prerequisites:** [Chapter 033 — Safe UPDATE](033-update-with-safe-predicates-and-preview-queries.md), [Chapter 034 — Safe DELETE](034-delete-with-safe-predicates-and-referential-implications.md), and [Chapter 036 — UPSERT/MERGE](036-upsert-and-merge-patterns-across-sql-dialects.md).

**Safety:** Use a disposable PostgreSQL 18 database named `sql_tutorials` and synthetic data only. Never run this lab against production. The lab uses temporary tables and an explicit transaction that ends in `ROLLBACK`. The guard checks PostgreSQL major version, database name, and recovery state; it cannot prove an endpoint is safe, so independently verify host, port, role, and environment before connecting.

## 0–5 minutes — Learning objectives

By the end you can (1) distinguish affected-row counts from returned row images; (2) use PostgreSQL `RETURNING` with INSERT, UPDATE and DELETE; (3) explain SQL Server `OUTPUT` and the limits of portability; (4) reconcile intended versus actual writes; (5) recognize concurrency, trigger, and retry hazards; and (6) produce audit evidence without exposing sensitive data.

**Use case:** A synthetic retail order-processing pipeline changes a payment status. The DBRE/SRE wants proof of *which* row changed, *what* values were written, and whether the expected count matched, before committing.

## 5–15 minutes — Concepts and syntax

Portable SQL DML includes `INSERT`, `UPDATE`, `DELETE`, and a `WHERE` predicate. **`RETURNING` is PostgreSQL-specific syntax** (also present in some other engines with differences); it is not universally portable. SQL Server supports `OUTPUT inserted.column, deleted.column` instead. Oracle and SQLite have their own capabilities and restrictions. Check your exact engine/version before porting.

| Technique | What it proves | What it does not prove |
|---|---|---|
| `SELECT` preview | Rows matching a predicate at read time | That the same rows will still match at write time |
| Command row count | Number of rows affected by a statement | Business correctness or a durable commit |
| `RETURNING` | Values emitted by the write statement | That the transaction committed, or downstream delivery succeeded |
| Post-write `SELECT` | State visible in your transaction | State after rollback or later concurrent updates |
| Commit + independent reconciliation | Durable state observed in a separate transaction | Exactly-once external side effects without an outbox/idempotency design |

PostgreSQL examples:

```sql
INSERT INTO payments (payment_id, amount, status)
VALUES (104, 20.00, 'pending')
RETURNING payment_id, amount, status;

UPDATE payments
SET status = 'reviewed'
WHERE payment_id = 104 AND status = 'pending'
RETURNING payment_id, status;

DELETE FROM payments
WHERE payment_id = 104 AND status = 'reviewed'
RETURNING payment_id, amount, status;
```

These statements are illustrative: first create the isolated `payments` table in the lab. Never omit a deliberate `WHERE` for operational UPDATE/DELETE. A returned row is not evidence of commit until the transaction succeeds.

**SQL Server comparison (illustrative T-SQL; not executable in PostgreSQL):**

```sql
UPDATE dbo.payments
SET status = 'reviewed'
OUTPUT deleted.status AS old_status,
       inserted.status AS new_status,
       inserted.payment_id
WHERE payment_id = 104 AND status = 'pending';
```

SQL Server `OUTPUT` supports `inserted` and `deleted` row images, but has trigger and destination restrictions. PostgreSQL 18 also supports `OLD` and `NEW` row images in DML `RETURNING` with appropriate syntax; the lab uses simple post-write values for readability.

## 15–30 minutes — Worked example: fail closed

Synthetic starting data:

| payment_id | amount | status |
|---:|---:|---|
| 101 | 12.50 | pending |
| 102 | 18.00 | pending |
| 103 | 9.25 | settled |

Goal: review **only payment 101**, preserve its amount, and verify one change.

```sql
-- Preview, not a concurrency guarantee:
SELECT payment_id, amount, status
FROM payments
WHERE payment_id = 101 AND status = 'pending';

-- PostgreSQL 18:
UPDATE payments
SET status = 'reviewed'
WHERE payment_id = 101 AND status = 'pending'
RETURNING payment_id, amount, status;
-- Expected: 101 | 12.50 | reviewed
```

If the returned set is empty, the record was missing, already reviewed, or changed concurrently. **Do not silently treat zero affected rows as success** unless the business contract explicitly defines an idempotent no-op. The accompanying lab uses a CTE to count returned rows and raises an exception when the count is not exactly one. A conditional predicate helps avoid lost-intent updates, but a preview alone does not lock the target.

For a write pipeline, capture a stable business key, operation type, batch ID, expected count, actual count, and safe non-sensitive values. Avoid logging customer details or full raw payloads. If a statement succeeds but the transaction later rolls back, its returned values describe an *attempt*, not a durable write.

## 30–50 minutes — Hands-on PostgreSQL 18 lab

1. Follow the isolated setup in [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Verify the target host, role, database, and PostgreSQL 18 server version out of band.
2. Inspect [Lab 037 SQL](../labs/037-returning-output-write-verification.sql). Confirm the `DO` safety guard, temporary table, transaction boundary, timeouts, and final `ROLLBACK`.
3. From the repository root, run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/037-returning-output-write-verification.sql
```

4. Verify output includes the deterministic checks: **one UPDATE returned**, **one INSERT returned**, **one DELETE returned**, **three rows remain**, and **total amount 41.75**. The lab intentionally rolls back, so no permanent table or data should remain.
5. **Exercise A:** Change the UPDATE predicate to `payment_id = 999` in a disposable copy. Predict the assertion failure and transaction rollback.
6. **Exercise B:** Change the status predicate from `pending` to `settled`. Explain why the expected-row check blocks an incorrect update.
7. **Exercise C:** Sketch an audit design with batch ID, key, operation, expected/actual counts, transaction outcome, and reconciliation query. Separate attempt logs from committed evidence.
8. **Exercise D:** Explain why retrying a write after a network timeout requires an idempotency key or version check, not merely inspecting the previous `RETURNING` output.

## 50–55 minutes — Troubleshooting and operational safeguards

| Symptom | Likely cause | Safe response |
|---|---|---|
| `RETURNING` returns zero rows | Predicate did not match; stale state | Re-read key/version, investigate; do not broaden predicate blindly |
| Too many returned rows | Predicate is too broad | Abort/rollback, narrow by stable key, review expected cardinality |
| `23505` unique violation | Duplicate key | Investigate replay or key collision; do not disable uniqueness |
| `55P03` lock unavailable | Concurrent writer or DDL | Inspect blockers, back off, keep transactions short |
| `40P01` deadlock or `40001` serialization failure | Concurrency conflict | Roll back whole transaction and retry boundedly |
| Rows returned but not persisted | Transaction rolled back | Check commit outcome in a separate transaction |
| SQL Server syntax rejected by PostgreSQL | `OUTPUT` is T-SQL | Use `RETURNING` in PostgreSQL |

**DBRE/SRE guardrails:** least-privilege lab role; isolated endpoint; exact predicates; expected row-count assertions; transaction and lock timeouts; no production credentials; synthetic data; redacted audit logs; no external side effects before commit; reconciliation after commit; monitor locks, WAL, and replication lag for real deployments. For large write batches, validate bounded chunks and measure operational impact. `RETURNING` is not a substitute for backup/restore readiness.

## 55–60 minutes — Review questions with answers

1. **What does `RETURNING` do?** Emits values from rows processed by PostgreSQL DML.
2. **Is it portable SQL?** No; vendors have different syntax and restrictions.
3. **What is SQL Server's counterpart?** `OUTPUT` with `inserted`/`deleted` images.
4. **Does a returned row prove commit?** No; the transaction can still roll back.
5. **Why check exact affected-row counts?** To fail closed on missing or unexpectedly broad matches.
6. **Does a preview guarantee the later write matches?** No; concurrent changes may intervene.
7. **Why include the old status in the UPDATE predicate?** To enforce the expected state transition.
8. **What should be logged?** Business key, batch ID, intended/actual counts, outcome, and safe audit metadata.
9. **How do you verify persistence?** Commit, then reconcile from a separate transaction.
10. **What is the lab's expected final in-transaction amount?** 41.75 across three rows.

## References

- [PostgreSQL 18 — RETURNING data from modified rows](https://www.postgresql.org/docs/18/dml-returning.html)
- [PostgreSQL 18 — UPDATE](https://www.postgresql.org/docs/18/sql-update.html)
- [PostgreSQL 18 — INSERT](https://www.postgresql.org/docs/18/sql-insert.html)
- [PostgreSQL 18 — DELETE](https://www.postgresql.org/docs/18/sql-delete.html)
- [SQL Server — OUTPUT clause](https://learn.microsoft.com/en-us/sql/t-sql/queries/output-clause-transact-sql)
- [PostgreSQL 18 — Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)

**Next:** [Chapter 038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT](../MASTER-TOC.md).

**Validation state:** Authored; targeted static review of the examples and links only. Independent editorial review, comprehensive syntax checking, and **actual isolated PostgreSQL 18 runtime validation** remain pending.
