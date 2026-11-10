# 038 — BEGIN, COMMIT, ROLLBACK, and SAVEPOINT

**Part 04 — Data Modification & Transaction Fundamentals · 60 minutes · PostgreSQL 18**

**Prerequisites:** [Chapter 033 — Safe UPDATE](033-update-with-safe-predicates-and-preview-queries.md), [Chapter 037 — Write verification](037-returning-output-and-write-verification.md), and the [isolated lab setup](../labs/docker/README.md).

**Safety:** Execute only on a disposable, independently verified PostgreSQL 18 instance and a database named `sql_tutorials`, using synthetic data. The [lab SQL](../labs/038-begin-commit-rollback-savepoint.sql) creates temporary tables and finishes with `ROLLBACK`. A database-name/version guard is not proof that the endpoint is non-production. Verify host, port, role, and environment **before** running the file.

## 0–5 minutes — Outcomes and scenario

After this lesson, you can explain atomicity, begin and finish transactions, distinguish `COMMIT` from `ROLLBACK`, recover from a statement error with `SAVEPOINT`, and verify that an operation did not accidentally persist. Data engineering use case: transfer a synthetic allocation between two budget buckets without changing the combined total. DBRE/SRE use case: keep a short, auditable unit of work and recover safely from expected validation errors.

## 5–15 minutes — Core concepts

A **transaction** groups statements into one logical unit. **Atomicity** means that either the whole committed unit takes effect or none of its changes do. A transaction does not automatically prevent all concurrent anomalies; isolation is covered in Chapter 039 (planned in the Master TOC).

| Statement | Purpose | Operational note |
|---|---|---|
| `BEGIN` | Start explicit transaction | Some platforms say `START TRANSACTION` |
| `COMMIT` | Make successful transaction changes permanent | Do not commit until invariants pass |
| `ROLLBACK` | Abandon all changes since transaction began | Does not undo effects outside the database |
| `SAVEPOINT checkpoint` | Mark a point within a transaction | Not a separate durable transaction |
| `ROLLBACK TO SAVEPOINT checkpoint` | Undo work after checkpoint | Transaction stays open |
| `RELEASE SAVEPOINT checkpoint` | Remove checkpoint | Does **not** commit |

In PostgreSQL, a statement error normally marks the current transaction as aborted; use `ROLLBACK TO SAVEPOINT` after an error (if a savepoint exists), or `ROLLBACK` the whole transaction. `COMMIT` on an already-aborted PostgreSQL transaction does not rescue its writes. Never assume a failed statement means prior writes have committed.

**Portability:** Standard-style transaction control exists across major relational engines, but syntax and semantics differ. PostgreSQL supports `BEGIN`, `START TRANSACTION`, `SAVEPOINT`, and `ROLLBACK TO SAVEPOINT`. SQL Server uses `BEGIN TRANSACTION` and `SAVE TRANSACTION`; Oracle uses implicit transaction starts and DDL can commit implicitly; MySQL transactional behavior depends on storage engine and DDL can implicitly commit; Snowflake and BigQuery have distinct scripting/DDL transaction rules. Check vendor documentation before porting a runbook.

## 15–30 minutes — Worked examples

For illustration, assume an isolated table `budgets(bucket_id, balance)` contains bucket 1 = 100.00 and bucket 2 = 50.00. This example is PostgreSQL-compatible SQL; create the table with the lab first.

```sql
BEGIN;
UPDATE budgets SET balance = balance - 20.00 WHERE bucket_id = 1;
UPDATE budgets SET balance = balance + 20.00 WHERE bucket_id = 2;
SELECT bucket_id, balance FROM budgets ORDER BY bucket_id;
-- Expected: 1 | 80.00 ; 2 | 70.00
ROLLBACK;
-- Original balances are restored: 100.00 and 50.00
```

To persist a verified business transaction, replace `ROLLBACK` with `COMMIT` **only in an approved isolated exercise** after checking affected-row counts, constraints, and the sum (150.00). `COMMIT` is deliberately not used in the runnable lab.

A savepoint permits recovery from a failed sub-operation without losing earlier successful work:

```sql
BEGIN;
SAVEPOINT before_optional_change;
-- A failed statement here may abort the transaction in PostgreSQL.
ROLLBACK TO SAVEPOINT before_optional_change;
-- Continue with validated work, then COMMIT or ROLLBACK.
ROLLBACK;
```

A savepoint is **not** a nested independent commit: releasing it does not persist data, and a later outer rollback still undoes everything. In PostgreSQL, the default psql autocommit behavior executes each standalone statement in its own transaction unless you explicitly begin one. Do not use an interactive client that silently commits while following a rollback-only lab.

## 30–50 minutes — Hands-on PostgreSQL 18 lab

Use a disposable PostgreSQL 18 primary, with a dedicated low-privilege lab role and database `sql_tutorials`. Independently confirm the connection target before running:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_user, inet_server_addr(), inet_server_port(), version();"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/038-begin-commit-rollback-savepoint.sql
```

The [complete lab](../labs/038-begin-commit-rollback-savepoint.sql) executes these steps:

1. Start a transaction, apply short statement/lock/idle timeouts, and check PostgreSQL major version and database name.
2. Create temporary synthetic budgets and assert initial balances (100.00, 50.00).
3. Transfer 20.00 using two targeted UPDATEs; assert both balances and conserved total 150.00.
4. Create a savepoint, make an optional 5.00 transfer, and assert the interim values (75.00, 75.00).
5. Roll back to the savepoint, assert restored post-transfer values (80.00, 70.00), and release the savepoint.
6. Assert the two expected rows and total 150.00, then roll back the outer transaction.

**Expected evidence:** `NOTICE: PASS initial...`, `NOTICE: PASS transfer...`, `NOTICE: PASS optional...`, `NOTICE: PASS savepoint rollback...`, and `NOTICE: PASS final...`, followed by `ROLLBACK`. The lab does **not** demonstrate a durable commit; the commit example above is conceptual. Capture actual PostgreSQL 18 version, exit code, and console output in a future isolated acceptance run. Expected notices are predictions, not execution evidence.

**Practice:** Explain why an outer `ROLLBACK` undoes even the transfer made before the savepoint. Identify how you would detect a missing second UPDATE (affected-row checks plus invariant checks). Describe why a database transaction cannot undo an email or message already sent externally.

## 50–55 minutes — Troubleshooting and operational guardrails

| Symptom | Likely cause | Safe response |
|---|---|---|
| `current transaction is aborted` | Prior SQL error in PostgreSQL | `ROLLBACK TO SAVEPOINT` if available, otherwise `ROLLBACK` |
| Update affects zero rows | Predicate/key mismatch or concurrent change | Abort and investigate; never silently commit |
| Lock timeout | Another transaction holds conflicting lock | Roll back; inspect blocking safely before retrying |
| Session idle in transaction | Transaction left open | Roll back; avoid long-lived locks and vacuum interference |
| Totals do not reconcile | Missing/duplicate update or arithmetic error | Fail closed; roll back and preserve sanitized evidence |

**Production safety:** Obtain change approval for real writes; preview exact keys and counts, use bounded transactions, set appropriate timeouts, confirm recovery/backup posture, and avoid retrying non-idempotent external side effects. Savepoints do not protect against host failures after commit or external side effects. For high-volume data engineering jobs, batch and reconcile rather than holding a transaction open indefinitely.

## 55–60 minutes — Review questions with answers

1. **What does COMMIT do?** Makes a successful transaction's changes durable under the database's durability guarantees.
2. **What does ROLLBACK TO SAVEPOINT do?** Undoes changes after the named checkpoint but leaves the outer transaction active.
3. **Does RELEASE SAVEPOINT persist data?** No; only the outer transaction can commit.
4. **What should follow a failed PostgreSQL statement inside an explicit transaction?** Roll back to a valid earlier savepoint or roll back the transaction.
5. **Why verify both affected rows and a conserved total?** A correct sum alone could conceal an incorrect target, and row counts alone do not establish business correctness.
6. **Can ROLLBACK unsend an external message?** No; use an outbox/idempotency design for external effects.

## References and next chapter

- [PostgreSQL 18 — Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL 18 — BEGIN](https://www.postgresql.org/docs/18/sql-begin.html), [COMMIT](https://www.postgresql.org/docs/18/sql-commit.html), [ROLLBACK](https://www.postgresql.org/docs/18/sql-rollback.html)
- [PostgreSQL 18 — SAVEPOINT](https://www.postgresql.org/docs/18/sql-savepoint.html), [ROLLBACK TO SAVEPOINT](https://www.postgresql.org/docs/18/sql-rollback-to.html)
- [SQL Server — Transactions](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/transactions-transact-sql)
- [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Next:** Chapter 039 — Isolation Levels and Common Transaction Anomalies (see [Master TOC](../MASTER-TOC.md)); publication and runtime status must be tracked independently.

**Validation status at authorship:** Targeted static reasoning only; independent editorial review, comprehensive SQL syntax validation, and isolated PostgreSQL 18 runtime execution pending.
