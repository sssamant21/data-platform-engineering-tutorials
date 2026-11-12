# 105 — Locks, Blocking, Deadlocks, and Troubleshooting

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · **PostgreSQL 18** · Beginner-friendly

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Read-only synthetic lab](../labs/105-locks-blocking-deadlocks-troubleshooting.sql) · [Previous: 104](104-sensitive-data-protection-masking-and-audit-requirements.md) · Next: 106 — Backward-compatible migrations and deployment controls (planned)

## 1. Learning objectives and scenario (0–5 min)

By the end, distinguish ordinary locking from blocking and deadlock; identify waiting versus holding sessions; interpret `pg_stat_activity`, `pg_locks`, and `pg_blocking_pids`; choose safe investigation and escalation steps; and explain why cancellation, termination, and DDL are not first-line fixes. Prerequisites: transactions (Chapter 038), isolation (039), safe modifications (033–035), and security (101–104).

**Scenario:** A fictional order-ingestion service has slow updates while a reporting session holds an open transaction. A DBRE needs evidence before taking action. All records and session identifiers in this lesson are invented.

## 2. Concepts and SQL portability (5–15 min)

A **lock** coordinates concurrent access. A **wait** is a session unable to proceed until a resource becomes available. **Blocking** means a session is waiting for another transaction or resource holder. A **deadlock** is a cycle of dependencies in which no participant can proceed; PostgreSQL detects it and aborts one participant's transaction. A slow query is *not* necessarily blocked: CPU, I/O, network, client backpressure, and poor plans can also cause latency.

PostgreSQL uses MVCC: normal `SELECT` generally does not block ordinary `UPDATE`, but DDL, explicit locking clauses, conflicting writes, and other lock modes can create waits. Row-lock waits may appear in `pg_locks` as waits on transaction IDs rather than an obvious tuple entry. A session with `state = 'idle in transaction'` may retain locks after its last SQL statement. `wait_event_type = 'Lock'` identifies a lock wait; `state = 'active'` alone does not prove CPU execution.

| Concept | Portable principle | PostgreSQL 18 implementation |
|---|---|---|
| Transactions | Short transactions reduce lock-hold time | `BEGIN`, `COMMIT`, `ROLLBACK` |
| Isolation and row locks | Concurrent writes may conflict | `SELECT ... FOR UPDATE` and MVCC semantics |
| Lock inventory | Vendor-specific system views | `pg_locks`, `pg_stat_activity` |
| Identify blockers | Inspect dependency graph | `pg_blocking_pids(pid)` |
| Deadlock handling | Retry the *whole* failed transaction when safe | SQLSTATE `40P01`; `deadlock_timeout` |
| Lock timeout | Bound waiting, not total query duration | `lock_timeout`; `statement_timeout` |

Other platforms have different monitoring views and locking models; do not copy PostgreSQL catalog queries to SQL Server, MySQL, Oracle, or Snowflake unchanged.

## 3. Investigation walkthrough (15–30 min)

### A. Identify waiting sessions (PostgreSQL-specific; observational)

```sql
SELECT pid, usename, application_name, state,
       wait_event_type, wait_event,
       now() - query_start AS query_age,
       now() - xact_start AS transaction_age,
       pg_blocking_pids(pid) AS blocker_pids
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid()
  AND wait_event_type = 'Lock'
ORDER BY query_start NULLS LAST, pid;
```

**Expected shape:** zero or more rows; **not a deterministic expected row count**. Monitoring permissions can restrict details. This is a snapshot; blockers can disappear between samples. `pg_blocking_pids` may return multiple PIDs or special cases involving prepared transactions. Do not mistake a PID for a durable session identity; record timestamp and backend start.

### B. Inspect lock inventory (PostgreSQL-specific; observational)

```sql
SELECT pid, locktype, mode, granted, relation::regclass AS relation_name
FROM pg_locks
WHERE pid = pg_backend_pid()
ORDER BY locktype, mode;
```

**Expected:** environment-dependent catalog/transaction locks. The query itself acquires locks; do not assert an exact count. `relation::regclass` is PostgreSQL-specific. An ungranted lock is a wait request; granted locks do not automatically indicate a harmful blocker.

### C. Understand a deadlock without creating one

Imagine transaction A updates order 501 then attempts 502, while B updates 502 then attempts 501. Each waits for the other's row lock, forming a cycle. PostgreSQL raises `40P01` in one transaction; the application should roll back and retry the *entire* idempotent business operation with bounded retries and jitter. Prevent this pattern by acquiring locks in a consistent key order, keeping transactions short, and indexing predicates to avoid unnecessary scans.

### D. Evidence-first operational runbook

1. Confirm the affected service, time window, error rate, and whether it is actually a lock wait. Capture UTC time, database, backend PID, backend start, application name, transaction age, wait type, blockers, and query fingerprint **without copying sensitive literals**.
2. Compare several snapshots and inspect the blocking transaction owner, service deployment, connection pool, and `idle in transaction` state. A blocker may be doing necessary work; check business criticality.
3. Coordinate with the application owner. Prefer normal transaction completion, safe application rollback, or workload throttling. Review transaction boundaries and consistent lock ordering.
4. **Only with authorization and an incident change record**, consider `pg_cancel_backend` (cancel current statement) before `pg_terminate_backend` (disconnect and roll back the session's open transaction). Neither is guaranteed to be safe for the business workflow; both may disrupt clients and require retries.
5. Validate recovery with lock-wait counts, p95/p99 latency, throughput, transaction failures, replication health, and application-level correctness. Record root cause and prevention.

**Never run termination commands or lock-heavy DDL in this tutorial.** Do not automatically kill the oldest transaction. Never assume the blocking PID is the root cause or that a deadlock means database corruption.

## 4. Hands-on lab (30–50 min)

Use a disposable **PostgreSQL 18** database named `sql_tutorials` and an unprivileged training account. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/105-locks-blocking-deadlocks-troubleshooting.sql
```

[Lab 105](../labs/105-locks-blocking-deadlocks-troubleshooting.sql) runs inside `BEGIN READ ONLY`, sets transaction-local timeouts, verifies database and major version, examines only the current session's lock inventory, and analyzes a **fictional** wait-for graph with inline `VALUES`. It creates no lock contention, does not call `pg_cancel_backend` or `pg_terminate_backend`, and ends with `ROLLBACK`.

**Exercises:** (A) classify each synthetic session as waiting, blocking, or neither; (B) find the A↔B cycle; (C) explain why C→D is not a deadlock; (D) decide what additional evidence to capture before intervention; (E) explain the difference between `lock_timeout` and `statement_timeout`.

**Calculated expected results:** five fictional edges: 101→102, 102→101, 103→104, 105→104, 106→107; two cycle participants (101 and 102); three distinct noncycle waiters (103, 105, 106); one additional terminal blocker (107); zero multiset assertion mismatches. Actual current-session `pg_locks` row counts vary by environment. The lab assertion checks the cycle and graph summary using bidirectional `EXCEPT ALL`; these values are reasoned, **not observed runtime output**.

## 5. Troubleshooting, safety, and validation (50–55 min)

| Symptom | Likely interpretation | Safe next check |
|---|---|---|
| `wait_event_type = 'Lock'` | Waiting on a lock | `pg_blocking_pids` and repeated snapshots |
| `idle in transaction` for minutes | Open transaction may retain locks | Application ownership, transaction age, pool logs |
| SQLSTATE `40P01` | Deadlock victim | Full transaction retry design and lock ordering |
| SQLSTATE `55P03` | Lock not available / timeout | Timeout settings and blocker context |
| No lock waits but slow requests | Other bottleneck possible | Plans, I/O, CPU, client and pool telemetry |
| Permission-denied monitoring fields | Limited visibility | Request approved monitoring role; no privilege escalation |

`lock_timeout` applies while acquiring each lock; `statement_timeout` limits a statement. `idle_in_transaction_session_timeout` can close idle transactions, but production values require application coordination. `deadlock_timeout` affects detection timing; do not change server settings in the lab. **A read-only transaction can still acquire ordinary read locks; it is not a universal no-impact guarantee.** The lab's short timeouts and local-only inspection reduce risk, but isolated execution is mandatory.

**Validation status:** Authored example and expected values have been reasoned statically. Independent editorial review, full parser-based syntax/link QA, and actual isolated PostgreSQL 18 execution with retained logs are separate pending gates. Do not interpret expected values as runtime evidence.

## 6. Review questions and answers (55–60 min)

1. **Is every lock a problem?** No. Locks are essential for correctness; investigate harmful waits and duration.
2. **Does a slow query prove blocking?** No. Confirm wait events and blockers.
3. **What happens in a deadlock?** PostgreSQL detects a cycle and aborts one transaction; the application may retry the whole operation safely.
4. **Why can idle sessions block writes?** An open transaction can retain locks until commit/rollback.
5. **Why not terminate every blocker?** It may be doing legitimate work; termination can roll back business operations and trigger failures.
6. **How do you prevent common row-lock deadlocks?** Consistent lock ordering, short transactions, narrow predicates, bounded retries.
7. **What is the next lesson?** [106 — Backward-compatible migrations and deployment controls](../MASTER-TOC.md) (planned).

## References

- [PostgreSQL 18 — Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [PostgreSQL 18 — Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 — System Information Functions (`pg_blocking_pids`)](https://www.postgresql.org/docs/18/functions-info.html)
- [PostgreSQL 18 — Runtime Configuration: Client Connection Defaults](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [PostgreSQL 18 — Error Codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)
