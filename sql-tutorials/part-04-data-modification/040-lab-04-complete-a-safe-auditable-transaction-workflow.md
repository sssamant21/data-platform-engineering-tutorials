# 040 — Lab 04: Complete a Safe, Auditable Transaction Workflow

> **Part 04 capstone · 60 minutes · PostgreSQL 18 isolated lab · Content status: authored; runtime acceptance pending.**
>
> **Safety:** Use a disposable PostgreSQL 18 instance and the dedicated `sql_tutorials` database. All records are synthetic. The companion lab uses temporary tables and ends with `ROLLBACK`. Never run against production or with production credentials.

## 0–5 minutes — Outcomes and prerequisites

By the end, you can (1) preview and bound a write, (2) enforce a business invariant, (3) record an audit event in the same transaction, (4) use a savepoint to undo an unsafe intermediate change, (5) reconcile before completion, and (6) explain why application retries must be idempotent.

Prerequisites: [Chapter 033 — safe UPDATE](033-update-with-safe-predicates-and-preview-queries.md), [Chapter 034 — safe DELETE](034-delete-with-safe-predicates-and-referential-implications.md), [Chapter 037 — write verification](037-returning-output-and-write-verification.md), [Chapter 038 — transaction controls](038-begin-commit-rollback-and-savepoint.md), and [Chapter 039 — isolation](039-isolation-levels-and-common-transaction-anomalies.md). Have `psql` available and independently verify that the server is disposable.

**Scenario:** A synthetic retail order `1001` is paid. The workflow must change exactly one order from `pending` to `paid`, insert exactly one payment, and append one audit event. A simulated erroneous status change must be undone using a savepoint. All three changes are part of one transaction.

## 5–15 minutes — Transaction and audit design

| Object | Key columns | Invariant |
|---|---|---|
| `lab040_orders` | `order_id`, `amount`, `status` | Amount positive; status `pending` or `paid` |
| `lab040_payments` | `payment_id`, `order_id`, `amount` | One payment per order; amount positive |
| `lab040_audit` | `event_id`, `order_id`, `old_status`, `new_status` | Audit row matches the intended transition |

**Portable SQL concepts:** `BEGIN`/`COMMIT`/`ROLLBACK` concepts, `UPDATE ... WHERE`, `INSERT`, primary and foreign keys, `CHECK`, and `SAVEPOINT` are broadly supported, but syntax and transactional DDL differ across engines. **PostgreSQL-specific lab syntax:** `DO`, `RAISE EXCEPTION`, `RETURNING`, `SET LOCAL`, temporary tables with `ON COMMIT DROP`, `current_setting`, and `FILTER`.

**Atomicity versus auditing:** The order, payment, and audit rows are updated together. A rolled-back transaction leaves no committed audit record; if an organization needs an immutable record of *attempts*, it must capture those separately through an approved external audit system. A SQL audit table is not tamper-proof.

**Concurrency:** The guarded update requires `status = 'pending'`; the unique payment key helps reject duplicate processing. In real services, retry the *entire* transaction after SQLSTATE `40001` or `40P01` using bounded backoff. External notifications must use an idempotent outbox/consumer design rather than assuming a DB rollback can undo an email or API call.

## 15–30 minutes — Walkthrough

The lab starts a transaction, sets bounded timeouts, and checks `current_database() = 'sql_tutorials'`, PostgreSQL major version 18, and that the server is not in recovery. **These checks are defense in depth, not proof of isolation:** confirm host, account, and environment yourself before running.

The three starting orders are:

| order_id | amount | status |
|---:|---:|---|
| 1001 | 40.00 | pending |
| 1002 | 35.00 | pending |
| 1003 | 25.00 | pending |

The preview is `SELECT ... WHERE order_id = 1001 AND status = 'pending'`. Expected: **exactly one row, amount 40.00**.

An intentionally incorrect intermediate update marks order `1002` paid, but `ROLLBACK TO SAVEPOINT` restores it. The real guarded update changes order `1001` to paid and verifies `ROW_COUNT = 1`. A payment for 40.00 and a matching audit record are then inserted.

**Important:** `RETURNING` can show modified rows, but does not itself prove the entire workflow committed. This lab deliberately rolls everything back. A real change would require approved change control, commit authorization, post-commit reconciliation, and durable evidence.

## 30–50 minutes — Hands-on lab

From the repository root, after separately verifying the isolated PostgreSQL 18 target:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/040-lab-04-safe-auditable-transaction.sql
```

Use a dedicated nonproduction account and explicit connection parameters as appropriate. Never substitute a production database. Inspect the SQL file before execution.

**Expected (not yet runtime-verified) results:**

| Assertion | Expected |
|---|---|
| Initial orders / total | 3 / 100.00 |
| Preview matching pending order | 1 |
| Erroneous change after savepoint rollback | Order 1002 still pending |
| Real guarded update | Exactly 1 row |
| Payments / amount | 1 / 40.00 |
| Audit events | 1, pending → paid |
| Final paid / pending | 1 / 2 |
| Final orders total | 100.00 |
| Final transaction action | `ROLLBACK`; no persistent lab objects |

The script raises an exception if an invariant fails; `ON_ERROR_STOP=1` makes `psql` stop. A failure before final `ROLLBACK` may leave the session's transaction aborted until the connection ends; inspect the state and close the disposable session. Do not convert the lab's final rollback into a commit.

**Practice tasks:** Change the preview predicate to order 1003 *in a copy of the isolated lab*, then predict the new amount and audit entry before running. Explain why re-running the transaction after a commit would be rejected by a unique payment key or status predicate. Design a read-only post-commit reconciliation query for a real deployment.

## 50–55 minutes — Troubleshooting and guardrails

| Symptom | Cause / safe response |
|---|---|
| Guard rejects target | Wrong database, version, or standby; stop and verify the connection |
| Preview count not 1 | Missing/duplicate/already-processed order; fail closed |
| `23505` unique violation | Duplicate payment or replay; investigate idempotency key, do not bypass constraint |
| `23503` foreign-key violation | Missing parent order; correct source reconciliation |
| `40001` / `40P01` | Serialization failure / deadlock; retry whole transaction with bounded backoff |
| Lock timeout | Contention; investigate blocking safely, do not disable timeouts blindly |
| Audit mismatch | Abort; audit and business mutation must reconcile before commit |

DBRE/SRE review: record the database identity, change ticket, expected row count, lock and statement timeouts, rollback procedure, invariant results, and approved execution window. Never log credentials or real customer data. For production, require peer review and a tested recovery plan.

## 55–60 minutes — Review questions and answers

1. **Why preview before an UPDATE?** To verify the predicate and expected affected rows before a write.
2. **What does a savepoint accomplish?** It allows undoing a portion of an open transaction without discarding all earlier work.
3. **Does `RETURNING` guarantee durability?** No. The transaction may still roll back.
4. **Why put the audit insert in the same transaction?** To avoid a committed business change without its matching transactional audit row.
5. **Can a rollback undo an external payment API call?** No. Use an approved idempotency and compensation design.
6. **What is the final durable state of this lab?** No lab changes are committed; it ends with `ROLLBACK`.
7. **Does one successful run certify concurrency safety?** No; isolated multi-session tests and recorded evidence are required.

## References and navigation

- [PostgreSQL 18 — Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [PostgreSQL 18 — SAVEPOINT](https://www.postgresql.org/docs/18/sql-savepoint.html)
- [PostgreSQL 18 — UPDATE](https://www.postgresql.org/docs/18/sql-update.html)
- [PostgreSQL 18 — INSERT](https://www.postgresql.org/docs/18/sql-insert.html)
- [PostgreSQL 18 — Error Codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)
- [Companion SQL lab](../labs/040-lab-04-safe-auditable-transaction.sql)
- [Chapter 039](039-isolation-levels-and-common-transaction-anomalies.md) · [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Next:** Chapter 041 — Join Fundamentals and Relationship Cardinality (Part 05; see Master TOC).

**Validation declaration:** Authored for PostgreSQL 18; targeted static reasoning performed. Independent editorial review, full static QA, and actual isolated PostgreSQL 18 runtime validation remain **pending**.
