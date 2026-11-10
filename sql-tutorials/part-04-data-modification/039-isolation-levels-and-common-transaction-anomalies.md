# 039 — Isolation Levels and Common Transaction Anomalies

**Part 04 — Data Modification & Transaction Fundamentals · 60 minutes · PostgreSQL 18**

**Prerequisites:** [Chapter 038 — Transactions and savepoints](038-begin-commit-rollback-and-savepoint.md), [Chapter 033 — Safe UPDATE](033-update-with-safe-predicates-and-preview-queries.md), and [isolated PostgreSQL setup](../labs/docker/README.md).

**Safety and scope:** All examples use fictional retail inventory. The [read-only PostgreSQL 18 lab](../labs/039-isolation-levels-transaction-anomalies.sql) performs no persistent writes. Use only a separately verified disposable PostgreSQL 18 primary named `sql_tutorials`. A version/database guard is **not** proof that a host is non-production. No production credentials, concurrent load, or blocking demonstrations are needed.

## 0–5 minutes — Learning objectives and operational scenario

By the end, you can (1) distinguish atomicity from isolation; (2) explain dirty reads, nonrepeatable reads, phantoms, lost updates, write skew, and serialization failures; (3) choose between PostgreSQL Read Committed, Repeatable Read, and Serializable; (4) identify when a retry is necessary; and (5) design a bounded, idempotent transaction for an inventory reservation. For data engineers, this matters when ingesting batches while reports run. For DBRE/SREs, it matters when diagnosing unexpected totals, contention, and retry storms.

## 5–15 minutes — Isolation fundamentals

**Atomicity** answers whether a transaction's writes succeed together. **Isolation** governs what concurrent transactions can observe and how their results interact. A consistent single-statement SELECT does not imply a multi-statement workflow is immune to concurrent changes.

| Phenomenon | Meaning | Fictional inventory example |
|---|---|---|
| Dirty read | Read another transaction's uncommitted changes | See a quantity that is later rolled back |
| Nonrepeatable read | Re-read the same row and see a changed value | Quantity changes from 10 to 7 |
| Phantom | Re-run a predicate and see a different matching row set | Another order appears among pending orders |
| Lost update | One writer overwrites another's work | Two read-modify-write clients each save an outdated quantity |
| Write skew | Two transactions read shared conditions and modify different rows, jointly violating an invariant | Two on-call operators each mark themselves off duty |
| Serialization failure | Database cannot safely order concurrent operations as if they ran serially | PostgreSQL raises SQLSTATE `40001` |

SQL-standard anomaly terminology and vendor guarantees are not identical. In PostgreSQL 18:

| Requested isolation | PostgreSQL effective behavior | Important caveat |
|---|---|---|
| Read Uncommitted | Behaves as **Read Committed** | PostgreSQL does **not** permit dirty reads |
| Read Committed (default) | New snapshot at the start of each command | Two SELECT statements can see different committed data |
| Repeatable Read | Stable transaction snapshot | PostgreSQL prevents phantoms here, stronger than SQL minimum; serialization anomalies remain possible |
| Serializable | Detects serialization anomalies, including dangerous write skew | Transactions can fail with SQLSTATE `40001`; retry **entire** transaction |

In PostgreSQL, Read Committed UPDATE may wait on a concurrently modified row and re-evaluate its WHERE clause after the other transaction commits. Repeatable Read/Serializable may instead abort with a concurrent-update or serialization error. **Do not assume all databases implement these levels identically.** SQL Server uses locking/snapshot configuration, MySQL InnoDB has different repeatable-read locking behavior, and cloud warehouses vary.

## 15–30 minutes — Worked examples

### Example A: two snapshots under Read Committed

Session A starts `BEGIN ISOLATION LEVEL READ COMMITTED;`, reads an order's status, then waits. Session B commits a status change. A's second SELECT may see the new committed status. This is a **nonrepeatable read**, not a dirty read. The example describes behavior only; do not use live tables to reproduce it.

### Example B: transaction snapshot under Repeatable Read

Session A starts `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;` and reads a predicate. If another session commits a new matching row after A's snapshot is established, A continues to see the original snapshot until it ends its transaction. A new transaction can see the new row. This is why a transaction snapshot matters for multi-query reconciliation.

### Example C: lost-update prevention

Unsafe application pattern:

```sql
-- Conceptual anti-pattern; DO NOT execute on shared tables:
SELECT quantity FROM inventory WHERE sku = 'SKU-A'; -- returns 10
-- Client computes 10 - 2 = 8, while another client may also write.
UPDATE inventory SET quantity = 8 WHERE sku = 'SKU-A';
```

Safer, atomic conditional mutation (portable SQL shape):

```sql
UPDATE inventory
SET quantity = quantity - 2
WHERE sku = 'SKU-A' AND quantity >= 2;
-- Verify exactly one affected row, then commit only if invariants hold.
```

This prevents negative quantity for the row under concurrent writers but does **not** automatically protect multi-row or cross-table business invariants. Use explicit locking or Serializable where appropriate, with a carefully designed retry policy.

### Example D: write skew and retries

Two transactions both observe two available on-call engineers. Each independently changes a **different** engineer to unavailable. At snapshot isolation / PostgreSQL Repeatable Read, both may commit and leave nobody on call. Serializable can detect this dangerous structure and abort one transaction. A serialization failure is **not** evidence of corruption; it is a safety mechanism. Retry the **whole** transaction, re-read its inputs, apply capped exponential backoff with jitter, and ensure external side effects are idempotent (e.g., an outbox).

## 30–50 minutes — Hands-on PostgreSQL 18 lab

1. Independently confirm the target host, port, role, and disposable database; use a least-privilege lab account.
2. Run the linked read-only lab, which checks PostgreSQL 18 and `sql_tutorials`, verifies the default level, demonstrates explicit transaction settings, and computes deterministic synthetic inventory checks.
3. Compare Read Committed and Repeatable Read transaction settings. **These single-session queries do not reproduce concurrent anomalies.** Concurrency behavior in the examples above is explained conceptually, not falsely certified.
4. Explain why the conditional inventory update must check its affected-row count.
5. Explain how a serialization retry differs from blindly repeating only the failed UPDATE.

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_user, inet_server_addr(), inet_server_port(), version();"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/039-isolation-levels-transaction-anomalies.sql
```

**Expected lab output:** `PASS read committed`, `PASS repeatable read`, `PASS synthetic inventory`, `PASS serializable`, and a final `ROLLBACK`. The synthetic data are inline `VALUES` rows; the inventory total is 15 and 2 units can be reserved from SKU-A's 10 units, leaving 8. These are **expected** results, not recorded PostgreSQL runtime evidence.

**Practice (explain without executing writes):** Which level gives a stable multi-statement snapshot? Why can Serializable abort a valid-looking transaction? What does SQLSTATE `40001` mean? Why might `SELECT FOR UPDATE` be helpful for a targeted row but not sufficient for a predicate-based invariant? How would you monitor retry rates and transaction duration?

## 50–55 minutes — Troubleshooting and safety

| Symptom | Interpretation | DBRE/SRE action |
|---|---|---|
| Repeated SELECT values change | Possible Read Committed snapshot difference | Check transaction boundaries and concurrent writes |
| `could not serialize access` / SQLSTATE `40001` | Serializable or Repeatable Read conflict | Retry the **whole** transaction with a cap and jitter; investigate persistent hotspots |
| SQLSTATE `40P01` | Deadlock detected | Retry whole transaction after checking lock ordering |
| Long idle-in-transaction sessions | Snapshots/locks retained | Set bounded timeouts; terminate only through approved incident procedure |
| Large retry spikes | Contention, high conflict rate, or long transactions | Reduce transaction scope, inspect lock waits, verify invariants |
| Reporting totals disagree | Snapshot timing, duplicates, or incorrect aggregation grain | Use a consistent snapshot and reconciliation queries; do not assume isolation is the only cause |

**Guardrails:** No changes to production isolation defaults. Never use a teaching script against production. Keep transactions short; check row counts, predicates, and invariants; protect external effects with idempotency. `SERIALIZABLE` is not a substitute for sound schema constraints or error handling. For PostgreSQL, transaction isolation is set before the first query or data-modifying statement in the transaction.

## 55–60 minutes — Review questions and answers

1. **Does PostgreSQL Read Uncommitted allow dirty reads?** No; it behaves as Read Committed.
2. **Why can two SELECTs in Read Committed disagree?** Each command can use a fresh committed snapshot.
3. **Does PostgreSQL Repeatable Read prevent phantoms?** Yes, in PostgreSQL; other engines may differ.
4. **What can Serializable do that Repeatable Read cannot?** Detect and abort transactions whose combined results cannot be serialized.
5. **What is the safe response to SQLSTATE 40001?** Retry the complete transaction with fresh reads and bounded backoff.
6. **Does a single-session lab prove concurrency safety?** No; concurrent execution with reproducible evidence is required for that claim.

## References and navigation

- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 — SET TRANSACTION](https://www.postgresql.org/docs/18/sql-set-transaction.html)
- [PostgreSQL 18 — Serializable Isolation](https://www.postgresql.org/docs/18/applevel-consistency.html)
- [PostgreSQL 18 — Error Codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)
- [Chapter 038](038-begin-commit-rollback-and-savepoint.md) · [Master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Next:** Chapter 040 — Lab 04: Complete a Safe, Auditable Transaction Workflow (listed in the Master TOC; not yet linked as a published file).

**Validation at authorship:** Targeted static reasoning only. Independent editorial review, comprehensive syntax checking, and actual PostgreSQL 18 execution remain pending.
