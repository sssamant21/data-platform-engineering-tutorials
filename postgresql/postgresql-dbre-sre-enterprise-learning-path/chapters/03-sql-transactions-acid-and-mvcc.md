# Chapter 03 — SQL Transactions, ACID and MVCC

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Level:** Beginner → Intermediate · **Duration:** 60 minutes · **Reference:** PostgreSQL 17  
**State:** Authored; runtime testing and independent review pending

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 03 lab](../labs/chapter-03/README.md) · [Progress](../STATUS-TRACKER.md)

## 1. Why a DBRE/SRE needs transaction literacy

A database can be available while an application is still losing correctness through partial writes, stale decisions, deadlocks, and improperly handled transaction retries. Understanding PostgreSQL transactions is essential for architecture reviews and production incidents.

This chapter uses a **synthetic two-account ledger** to examine atomic multi-statement updates and concurrent transactions. It is a training example, not a design for a real payment or bank ledger.

### Learning outcomes

By the end, learners should be able to:

1. Explain `BEGIN`, `COMMIT`, `ROLLBACK` and `SAVEPOINT`.
2. Explain ACID and when application logic must enforce business invariants.
3. Describe PostgreSQL MVCC and row versions at a conceptual level.
4. Distinguish `READ COMMITTED`, `REPEATABLE READ` and `SERIALIZABLE`.
5. Observe changes to visibility between two separate `psql` sessions.
6. Diagnose long-running or idle transactions safely using `pg_stat_activity`.
7. Describe why serialization/deadlock errors require careful **whole-transaction retry** in applications.

## 2. 60-minute outline

| Time | Section | Practice |
|---|---|---|
| 0–10 min | Transaction boundaries and ACID | Interpret an atomic transfer |
| 10–20 min | MVCC and row visibility | Explain snapshots |
| 20–30 min | Isolation levels, anomaly risks and retries | Application-design questions |
| 30–53 min | Hands-on [two-session lab](../labs/chapter-03/README.md) | Commit, rollback, READ COMMITTED vs REPEATABLE READ |
| 53–60 min | Operational checks and acceptance | Identify and clean up open transactions |

## 3. Transaction lifecycle and ACID

```text
Application begins transaction
             |
             v
          BEGIN
             |
   +---------+---------+
   | statement(s) SQL |
   +---------+---------+
             |
    +--------+--------+
    |                 |
   COMMIT           ROLLBACK
    |                 |
Changes made       Uncommitted
visible as         changes discarded
committed
```

PostgreSQL normally operates in autocommit mode: each standalone SQL statement is its own transaction unless an explicit block is started.

- **Atomicity:** all changes inside a transaction commit together or none do.
- **Consistency:** database constraints and correctly designed application transactions preserve intended invariants. The DBMS does not automatically know all domain rules.
- **Isolation:** concurrent transactions interact according to the chosen isolation level.
- **Durability:** PostgreSQL's WAL and storage system support persistence of committed changes under documented settings and failure assumptions. Non-default asynchronous-commit configurations can change crash-loss expectations.

### Atomic transfer illustration

```sql
BEGIN;
UPDATE accounts SET balance = balance - 25.00 WHERE account_id = 1;
UPDATE accounts SET balance = balance + 25.00 WHERE account_id = 2;
COMMIT;
```

Without one transaction, a failure between the two statements could leave the application with only one side of the transfer. In a production financial system, additional controls such as immutable journal entries, idempotency keys, reconciliation, authorization, and audit are required.

A `CHECK (balance >= 0)` constraint in our lab demonstrates one database invariant; it does not prevent every possible business error.

### Savepoints

`SAVEPOINT` marks a location to which a transaction can roll back without discarding earlier work. Some SQL errors put the current transaction into an aborted state; use `ROLLBACK TO SAVEPOINT` or roll back the entire transaction before further work.

## 4. How MVCC works

Multi-Version Concurrency Control (MVCC) lets readers see versions appropriate to their snapshots instead of requiring every read to block ordinary writes.

```text
Time →
Session A: SELECT balance = 100   |    SELECT balance = ?
Session B:          UPDATE 100→80 | COMMIT
                                  |
Isolation level decides which committed version A sees.
```

Conceptually, PostgreSQL associates row versions with transaction visibility metadata. Old versions remain temporarily available for suitable snapshots and later become candidates for vacuum cleanup when no longer needed.

**Critical DBRE implication:** an old transaction snapshot may delay removal of dead tuples; replication slots and long transactions can also contribute to WAL/storage pressure through separate mechanisms. Investigate each case using evidence rather than assuming every long transaction is the root cause.

## 5. Isolation levels and observed behavior

| SQL isolation setting | PostgreSQL behavior | Practical implication |
|---|---|---|
| `READ UNCOMMITTED` | Treated as `READ COMMITTED` in PostgreSQL | Dirty reads not supported |
| `READ COMMITTED` | Each statement sees a new committed-data snapshot | Repeated statements may see changed results |
| `REPEATABLE READ` | Snapshot is stable from the first applicable query/statement; PostgreSQL's implementation also prevents phantom reads under its snapshot model | Transactions can still encounter serialization failures for concurrent updates |
| `SERIALIZABLE` | Strongest isolation via Serializable Snapshot Isolation (SSI) | Conflicting schedules may abort with `SQLSTATE 40001`; application retries are essential |

In PostgreSQL, **READ COMMITTED is the default**. It prevents dirty reads, but does not ensure that a sequence of reads within one transaction observes an unchanged committed world.

PostgreSQL `REPEATABLE READ` is stronger than the minimum SQL standard requirements in its phantom-read behavior; do not rely on generic DBMS summaries that imply identical semantics in every product.

For `SERIALIZABLE`, application retries must rerun the **entire logical transaction**, including dependent reads and decisions, not only the failed SQL statement. Deadlock errors (`SQLSTATE 40P01`) may also require controlled retries after understanding the cause.

## 6. Operational diagnostics and SRE guardrails

### Read-only observability

```sql
SELECT
    pid,
    usename,
    datname,
    state,
    wait_event_type,
    wait_event,
    now() - xact_start AS transaction_age,
    left(query, 100) AS query_prefix
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY xact_start NULLS LAST;
```

This query can reveal sessions in `idle in transaction` state, running queries, and blocked activity. Query text can contain sensitive information: follow logging/redaction policy. Avoid capturing complete statements indiscriminately.

### Why long-lived transactions matter

- May hold locks or snapshots longer than intended.
- Can delay cleanup of obsolete row versions and contribute to bloat.
- May increase latency for schema changes or concurrent writers.
- Can cause application connection pool exhaustion under load.
- Can make incident mitigation more complex, especially if a transaction spans multiple services.

### Safe incident sequence

1. Confirm application symptoms and cluster identity.
2. Identify transaction owners, transaction age, SQL operation, locks and pool state.
3. Engage application owner before a disruptive action.
4. Prefer reducing new workload or addressing the source of stalled transactions.
5. Use an approved, scoped mitigation with stop conditions and rollback plan.
6. Verify the affected application and retain sanitized evidence.

Never terminate sessions solely because a query has run for an arbitrary number of seconds; investigate business context, lock ownership and transaction criticality. This chapter does not teach or automate destructive session termination.

## 7. Hands-on lab

The [Chapter 03 lab](../labs/chapter-03/README.md) provides:

- independent `training_ch03` database and a two-account synthetic table;
- atomic transfer using `BEGIN`/`COMMIT`;
- `ROLLBACK` and `SAVEPOINT` examples;
- a constraint rejection test;
- two simultaneous `psql` sessions showing READ COMMITTED vs REPEATABLE READ snapshot behavior;
- a safe diagnostic query and explicit session cleanup.

**Important:** Session A and Session B instructions must be executed manually in the indicated order; do not combine them into one SQL batch.

## 8. Application-design review

A service moves resource quotas from one account to another while thousands of operations run concurrently.

Ask:
- Is the invariant simply "no balance below zero," or must the sum be conserved?
- How are concurrent operations serialized on the same account?
- Does the application retry whole transactions after `40001` and `40P01`?
- Is a request idempotent when clients retry after timeout?
- Can locks and transactions remain open while waiting on network calls?
- What are the latency and connection pool budgets?
- What schema constraints are required, and what monitoring signals expose violations or saturation?

No isolation setting can make a poor transaction design safe by itself.

## 9. Acceptance checklist

- [ ] Explain all four ACID properties without claiming the database understands all application invariants.
- [ ] Demonstrate atomic commit and rollback.
- [ ] Demonstrate a savepoint and a safe `CHECK` rejection.
- [ ] Describe why Session A sees a new value on a second READ COMMITTED query.
- [ ] Demonstrate stable snapshot reads in REPEATABLE READ.
- [ ] Explain how SERIALIZABLE differs and when retries may be required.
- [ ] Inspect session state and cleanly close both sessions.
- [ ] Record sanitized, real execution evidence **only after** running the lab.

**Authored is not validated:** written examples and expected outcomes have not been run in this publication step.

## 10. References and deeper reading

- [PostgreSQL 18: Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18: MVCC](https://www.postgresql.org/docs/18/mvcc.html)
- [PostgreSQL 18: Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [PostgreSQL 18: Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18: ROLLBACK TO SAVEPOINT](https://www.postgresql.org/docs/18/sql-rollback-to.html)
- [Existing advanced PostgreSQL MVCC tutorial](../../chapters/016-mvcc-snapshots-and-tuple-visibility.md)
