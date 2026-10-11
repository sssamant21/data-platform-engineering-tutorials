# Chapter 017 — Isolation Levels and Application Failure Patterns

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18.
**Duration:** 90–120 minutes with concurrent lab sessions.
**Prerequisites:** Chapters 004, 005 and 016.
**Status:** Authored and statically reviewed; PostgreSQL concurrency execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](016-mvcc-snapshots-and-tuple-visibility.md) · [Hands-on lab](../labs/017-isolation-levels-and-failure-patterns-lab.md) · [Provisioning](../scripts/017-provision-isolation-lab.sql) · [Reset](../scripts/017-reset-isolation-lab.sql) · [Inspection](../scripts/017-isolation-inspection.sql) · [Retry helper](../scripts/017-transaction-retry-pattern.py)

## 1. Operational problem and objectives

Two requests both report success, yet a counter loses one adjustment. Two transactions update different rows and violate a shared business rule without blocking each other. After an isolation change, applications begin receiving serialization errors and either drop work or retry an unsafe cached decision.

DBRE/SRE operators must separate database availability from transaction correctness. This chapter teaches failure signatures, invariant-based acceptance, whole-transaction retries and the operational consequences of changing isolation. The lab reproduces stale-value overwrite, Repeatable Read concurrent-update failure, write skew and Serializable conflict handling.

## 2. Choose isolation against an invariant

An invariant is a rule that committed state must satisfy: capacity cannot be oversold, a balance adjustment must not be lost, or at least one on-call worker must remain active.

| PostgreSQL isolation | Ordinary-read contract | Reliability limit |
|---|---|---|
| Read Uncommitted | Behaves as Read Committed | Does not permit dirty reads in PostgreSQL |
| Read Committed | Statement snapshots | Separate reads/decisions can become stale |
| Repeatable Read | Stable transaction snapshot | Cross-row serialization anomalies remain possible |
| Serializable | Successful participating transactions behave like serial execution | Conflicting work can abort and must be retried |

Repeatable Read in PostgreSQL also prevents phantom reads within its transaction snapshot. A stable snapshot is still insufficient for every multi-row invariant.

Serializable does not understand an unstated business rule or correct buggy transaction logic. Participating transactions must actually enforce the invariant. Writers using a weaker/incorrect protocol can undermine a system-wide guarantee. Include every writer path, batch job and administrative workflow in the review.

## 3. Stale-value overwrite at Read Committed

Suppose two transactions read a capacity counter of 100. One computes 90 and another computes 80. Writing those absolute cached values can leave 80 after both commit, losing the first decrement. PostgreSQL can accept this schedule without an error.

This is an application read/compute/write pattern, not a dirty read or failed server. A new Read Committed statement could observe the latest committed value, but the application may never reread it.

For a suitable single-row invariant, express the change atomically:

~~~sql
UPDATE c017_iso.counter
SET units=units-20
WHERE id=1 AND units>=20
RETURNING units;
~~~

The predicate and affected-row count form part of the business outcome. Zero rows can mean insufficient capacity; it is not automatically a retryable database error. A CHECK constraint is useful defense, but does not by itself prevent lost absolute-value updates.

Explicit locks and optimistic version checks are other designs. They require all affected writers to follow the protocol; inspect behavior under concurrency rather than choosing a technique by name alone.

## 4. Repeatable Read detects some conflicts

A Repeatable Read transaction that tries to update a row changed by another committed transaction after its snapshot can receive SQLSTATE 40001. Its stable snapshot cannot simply adopt the newer row and continue that decision.

Rollback and start the transaction again, rereading the input and recomputing the change. Replaying only the UPDATE with an old calculated value is not a correct retry.

However, transactions can read a shared condition and then update different rows. They need not conflict on the same tuple. Repeatable Read can allow both commits even though their combined result violates an invariant.

## 5. Write skew and Serializable

The lab begins with two on-call rows. Each transaction sees two active workers and decides its own worker may go off call. At Repeatable Read, both can update separate rows and commit, leaving none.

Serializable Snapshot Isolation tracks dependencies between reads and writes. Predicate-read metadata can appear as SIReadLock in pg_locks. These are not ordinary blocking row locks; pg_blocking_pids can be empty while a serialization conflict is developing.

A dangerous dependency structure can cause one transaction to abort with 40001, sometimes during a statement and sometimes at COMMIT. Do not depend on which participant is rejected or on exact human-readable error wording.

After the other transaction finishes, retry the rejected business operation from a fresh snapshot. It now sees only one active worker and should decline to remove that last worker. A correct retry may produce a different business result than the first attempt.

False-positive/conservative conflict detection can also produce retries. Measure retry rate and transaction shape rather than treating every serialization abort as corruption or an outage.

## 6. Classify errors before deciding to retry

| SQLSTATE | Meaning | Handling boundary |
|---|---|---|
| 40001 | Serialization failure | Retry complete transaction with fresh decision data |
| 40P01 | Deadlock detected | Complete-transaction retry may be appropriate; investigate lock order |
| 55P03 | Lock not available / lock timeout | Apply workload-specific contention policy |
| 57014 | Query canceled, including statement timeout | Inspect cancellation cause and deadline |
| 25P02 | Current transaction is aborted | Rollback; find the earlier cause |
| 23505 | Unique violation | Usually business/conflict handling; not a blanket retry |
| Class 08 / connection loss | Connection exception | Outcome can be uncertain, especially around COMMIT |

PostgreSQL documents cases where an application may determine that a constraint error represents a retryable concurrency race. Make that decision from the operation's semantics; never retry every integrity error.

Parse driver SQLSTATE, not localized message text. Once an explicit transaction is aborted by a statement error, ordinary commands fail until rollback. A failure at COMMIT can leave different connection state; inspect the driver rather than assuming every error leaves the same open block.

Connection loss around COMMIT is different from a known transaction abort. The work may have committed. Reconcile using an idempotency key or application outcome record before resubmitting externally meaningful work.

## 7. A safe retry boundary

The supplied dependency-free teaching helper expects a fresh Psycopg 3-compatible non-autocommit connection per attempt. It sets Serializable before decision reads, performs only the callback's database work, commits, and returns success only after COMMIT.

It retries only 40001/40P01, rolls back failures, closes before backoff and bounds total attempts with jitter. The callback must reread/recompute every attempt. It must not commit itself or send email, charge a payment, write a file or call an external API.

The helper does not install a driver, discover credentials or execute the lab automatically. Its statement/lock budgets are illustrative; total business-operation deadlines and production pool policies need separate design. A series of individually bounded statements can still exceed an end-to-end deadline.

External effects need an appropriate idempotency or outbox/reconciliation design. Publishing success before commit or sending an external effect inside a retry callback can duplicate work.

Return a clean connection to a pool after failures. Do not hand the next borrower a 25P02 transaction. Also avoid hiding retries from metrics: retain total attempts, SQLSTATE, elapsed time, final outcome and exhaustion.

## 8. Production change and diagnosis

Precheck current per-login/per-database defaults, explicit BEGIN/SET TRANSACTION use, driver transaction management, pool behavior, invariant owners, all writers and retry implementation. A default-isolation change affects new transactions according to session settings; it is not proof that every service follows it.

| Symptom | Evidence | Next action |
|---|---|---|
| Two successes, lost adjustment | Original reads and absolute writes | Repair transaction design |
| Different-row updates break rule | Read predicate, invariant and schedule | Use reviewed Serializable/locking design |
| 40001 at COMMIT | Full transaction and driver state | Retry whole decision, not just COMMIT |
| Repeated 25P02 | First error and pool lifecycle | Rollback/reset and repair failure handling |
| Retry storm | Conflict rate, overlap and backoff | Bound work; reduce hot contention |
| Duplicate external operation | Commit uncertainty and idempotency records | Reconcile before resubmission |
| No blocking PID, serialization abort | Predicate/read-write dependencies | Do not confuse SSI with lock waits |

Canary a reviewed change with representative contention, invariant checks, retry metrics and latency. Measure success after commit, business declines and retry exhaustion separately.

Stop for missing full-transaction retry, unknown external effects, unreviewed writer paths, unexpected invariant violations or excessive latency/retry pressure. Do not lower isolation during an incident without understanding which correctness guarantee would change.

Rollback of a transaction removes its uncommitted work, not another transaction's commit. Rollback of an isolation rollout must restore application/session behavior and pool state consistently. It does not repair data already corrupted by an earlier pattern; plan reconciliation separately.

## 9. Monitoring and acceptance

Track 40001/40P01 rates, attempts per completed operation, retry exhaustion, commit latency, aborted-pool reuse and invariant violations. Report final business outcome separately from transient errors.

The lab passes when Read Committed cached overwrite is reproduced, the atomic counter pattern preserves both decrements, Repeatable Read raises 40001 for the same-row conflict, its write skew is observed, and Serializable rejects an incompatible outcome while a fresh retry preserves the roster invariant.

Helper fixture tests validate orchestration, not PostgreSQL SSI. Real concurrency execution remains pending until the lab runs.

## 10. Primary references

- [PostgreSQL 18 transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [Serialization failure handling](https://www.postgresql.org/docs/18/mvcc-serialization-failure-handling.html)
- [SQLSTATE reference](https://www.postgresql.org/docs/18/errcodes-appendix.html)
- [Psycopg transaction management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [Psycopg SQLSTATE exceptions](https://www.psycopg.org/psycopg3/docs/api/errors.html)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Next:** Chapter 018 — Locks, Blocking Chains and Deadlocks.
