# Chapter 018 — Locks, Blocking Chains and Deadlocks

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18.
**Duration:** 90–120 minutes; four lab terminals.
**Prerequisites:** Chapters 004, 005, 016 and 017.
**Status:** Authored and statically reviewed; PostgreSQL lock/deadlock execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](017-isolation-levels-and-application-failure-patterns.md) · [Hands-on lab](../labs/018-locks-blocking-chains-and-deadlocks-lab.md) · [Provisioning](../scripts/018-provision-lock-lab.sql) · [Reset](../scripts/018-reset-lock-lab.sql) · [Inspection](../scripts/018-lock-chain-inspection.sql)

## 1. Operational problem and objectives

A blocked application session is blamed for latency, but it is waiting behind another session that itself waits for an idle transaction. A migration asks for a strong table lock and starts a queue that also delays later readers. Two workers acquire rows in opposite order and one receives a deadlock error.

The operational task is to identify the dependency chain, the resource, the owner and the least disruptive resolution. This chapter teaches lock evidence, hard/soft blockers, root candidates, timeout classification and deadlock prevention. The lab reproduces all three schedules without changing production settings or terminating unrelated sessions.

## 2. Locks have different purposes and scopes

| Mechanism | Operational role | Common diagnostic mistake |
|---|---|---|
| Relation/table lock | Protect concurrent access and definition changes | Treating a mode containing “row” as a tuple lock |
| Tuple/row locking | Coordinate writes and locking reads | Expecting every held row lock to appear as a tuple row in pg_locks |
| Transaction/virtual-XID lock | Wait for another transaction to finish | Assuming it is unrelated to a row conflict |
| Advisory lock | Application-defined coordination | Forgetting session-scoped locks can survive rollback |
| SIReadLock | Serializable dependency tracking | Treating predicate-read metadata as an ordinary blocking lock |
| LWLock/buffer synchronization | Internal shared-memory coordination | Using a heavyweight blocker graph to explain every wait |

A wait_event_type of Lock is different from LWLock or I/O waits. Identify the class before applying the lock-chain procedure. Locks do not by themselves establish CPU saturation, storage latency or a visibility-horizon problem.

Normal table/row locks generally last through the transaction; locks acquired after a savepoint can be released by rollback to that savepoint. Advisory locks have their own lifetime: session-level advisory locks require explicit release or session end; transaction-level ones end with their transaction.

## 3. Table modes and row modes are separate

| Operation | Typical relation mode | Practical implication |
|---|---|---|
| Ordinary SELECT | AccessShareLock | Can coexist with ordinary DML; conflicts with AccessExclusiveLock |
| UPDATE/INSERT/DELETE | RowExclusiveLock plus applicable row locks | Two table-mode holders can coexist while same-row writes wait |
| Ordinary VACUUM/ANALYZE | ShareUpdateExclusiveLock | Compatible with ordinary reads/writes; conflicts with some maintenance/DDL |
| Many strong DDL operations | AccessExclusiveLock | Can block ordinary readers and writers |

DDL lock requirements vary by command/subcommand. Inspect the exact operation and current lock request rather than assuming all migrations behave alike.

Row modes include FOR UPDATE, FOR NO KEY UPDATE, FOR SHARE and FOR KEY SHARE. The weaker key-share/no-key-update relationship matters for foreign keys and non-key updates. A plain snapshot SELECT is different from SELECT FOR UPDATE.

pg_locks reports held/awaited lock objects and modes, but row ownership is largely recorded in tuple metadata. A writer waiting for a row may show an ungranted transaction-ID ShareLock. Do not search only for locktype tuple and conclude there is no row conflict.

## 4. Trace dependencies, not only the largest wait

Use pg_blocking_pids for blocking edges. It includes holders of conflicting locks and conflicting requests earlier in the wait queue. A queued strong request can therefore be a soft blocker even before it owns the lock.

The lab's first chain is C waits for B, while B waits for A. A is the root candidate. Releasing A lets B continue, but C remains blocked until B ends its own transaction. Releasing one edge is not proof every affected client recovered.

The second chain uses a queued AccessExclusive request. A already holds a reader lock; B waits for the strong lock; a later reader C queues behind B. This can create a convoy even though A and C would otherwise hold compatible read locks.

The provided SQL samples three named actors, deduplicates immediate blocker PIDs, follows paths to depth eight and marks cycles, prepared PID zero and out-of-scope endpoints. It omits query text, does not read the locked fixture, and performs no actuation. A root candidate is limited to the sampled graph; an external node requires further investigation.

Parallel queries can produce duplicate client-visible PIDs. Prepared transactions can be represented by PID zero, which is not a backend you can cancel. Inspect prepared-transaction ownership through its approved recovery procedure.

## 5. Read live evidence with limits

Collect PID, backend start, login/database, application label, state, transaction age, wait event, blocker PIDs, lock mode/object and wait start. A PID can be reused; revalidate identity before any intervention. application_name is client-supplied metadata, not an authorization boundary.

The helper's current_or_last_statement_age measures age since query_start. For an idle session this describes the last statement's start, not an actively running query. An idle-in-transaction root can hold locks even though it consumes little CPU.

Timeout settings returned by the inspector belong to its own session; retain the actor's explicit SET/SHOW evidence for its budgets.

Lock views change while you inspect them. A read-only transaction does not freeze the lock manager. The graph and raw views are complementary observations, not an atomic reconstruction of all activity.

Relation OIDs are database-scoped. Do not resolve another database's relation lock through the current database's pg_class without checking scope. Prepared, parallel and advisory cases also need their appropriate metadata.

Avoid tight unbounded polling of pg_blocking_pids/pg_locks; collection itself has overhead. Sample at a rate appropriate to the incident and retain observation timestamps.

## 6. Waiting policies and deadlock detection

| Control/outcome | Meaning | Operator response |
|---|---|---|
| lock_timeout / 55P03 | Lock acquisition budget exhausted | Diagnose contention and workload retry policy |
| NOWAIT / 55P03 | Immediate failure if required lock unavailable | Treat as deliberate admission behavior |
| statement_timeout / 57014 | Statement execution budget/cancellation | Inspect total operation and cause |
| deadlock detection / 40P01 | A dependency cycle was broken | Retry complete transaction when safe; repair ordering |
| 25P02 | Transaction already aborted | Rollback and locate the first error |

deadlock_timeout controls when PostgreSQL checks a wait for a deadlock; it is not a general lock-wait deadline. It also matters to log_lock_waits reporting. Do not tune it as a substitute for fixing transaction order.

max_locks_per_transaction sizes the shared lock-table budget; it is not a limit on the number of row locks and does not remove contention.

SKIP LOCKED can be useful for a reviewed work-queue pattern, but returns an incomplete view. Do not use it to silently make a correctness-sensitive report “stop blocking.” NOWAIT and SKIP LOCKED also do not eliminate every table-level lock requirement.

## 7. Deadlocks and ordered acquisition

A holds row 1 and needs row 2; B holds row 2 and needs row 1. Neither can complete without intervention. PostgreSQL detects the cycle and aborts a participant; do not assume which participant loses.

A deadlock can resolve before an observer captures a live cycle. The client SQLSTATE and protected server detail are important evidence. The database's cumulative deadlock counter is supporting evidence, not proof that one specific operation caused its delta.

After 40P01, discard the failed transaction's decisions and retry the whole operation according to Chapter 017. An error during a statement can leave the connection in an aborted block until rollback. Do not repeatedly retry the last UPDATE inside it.

A consistent resource order prevents the lab's opposite-row cycle. Real designs must consider every resource: tables, rows, foreign keys, triggers, advisory keys and lock upgrades. Shorten transaction scope, avoid waiting for external services while holding locks and use the appropriate strongest needed lock deliberately rather than accidental upgrades.

## 8. Production mitigation and stop conditions

1. Confirm the instance/client impact and distinguish heavyweight locks from other waits.
2. Capture dependency edges and candidate ownership, including backend start and transaction state.
3. Identify the resource and expected transaction/migration lifetime.
4. Ask the owner to finish or roll back when feasible.
5. If approved, cancel a waiting operation or terminate an identified session according to its retry/rollback contract.
6. Verify both lock release and application recovery, including new attempts.

Canceling a waiting migration can remove a queue convoy without ending a legitimate reader. Canceling an idle holder's current query does not by itself end its transaction. Termination can abort work, create retries and affect correctness; Chapter 020 develops actuation procedures.

Stop if root ownership is uncertain, the graph exits the scope, a prepared transaction is involved, an active critical transaction's rollback cost is unknown or a proposed intervention broadens to unrelated clients. Preserve evidence and escalate.

Do not reboot PostgreSQL or disable transaction safeguards as a first response to a lock queue. Restore the intended transaction protocol and verify data outcomes after an intervention.

## 9. Monitoring and diagnosis

| Symptom | Evidence | Next action |
|---|---|---|
| Many waiters, idle root | Transaction age/ownership and chain | Repair transaction completion |
| Readers wait after migration starts | Queued strong request and soft edges | Review/cancel/reschedule the migration safely |
| No tuple locks visible | Transaction-ID waits and blockers | Interpret row conflict correctly |
| 40P01 but graph already empty | Error detail, actor schedule and final state | Review lock order and retries |
| Retry storm after release | Connection/workload admission and retry metrics | Bound reconnection/retry pressure |
| PID zero blocker | Prepared transaction inventory | Resolve through the owning coordinator |
| Empty blocker list with SSI abort | Isolation/dependency evidence | Follow serialization diagnosis |

Monitor blocked-session count, duration, root transaction age, lock timeout/deadlock rates and user-facing latency. Set workload-specific thresholds and distinguish background maintenance from application critical paths.

## 10. Acceptance and references

Pass requires C→B→A observed, root release followed by intermediate release, queued strong-lock convoy, deliberate NOWAIT/SKIP LOCKED behavior, a 40P01 deadlock victim with one valid survivor, and successful consistent-order execution. Actual PostgreSQL execution remains pending.

- [Explicit locking and deadlocks](https://www.postgresql.org/docs/18/explicit-locking.html)
- [pg_locks](https://www.postgresql.org/docs/18/view-pg-locks.html)
- [Blocking-PID functions](https://www.postgresql.org/docs/18/functions-info.html)
- [Lock-management settings](https://www.postgresql.org/docs/18/runtime-config-locks.html)
- [Client timeout settings](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [LOCK permissions and semantics](https://www.postgresql.org/docs/18/sql-lock.html)
- [NOWAIT/SKIP LOCKED](https://www.postgresql.org/docs/18/sql-select.html)

**Next:** Chapter 019 — Long Transactions, Idle Sessions and Transaction Timeouts.
