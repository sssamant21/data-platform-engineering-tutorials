# Chapter 016 — MVCC, Snapshots and Tuple Visibility

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18.
**Duration:** 75–100 minutes with three lab terminals.
**Prerequisites:** Chapters 002, 004, 005 and 011.
**Status:** Authored and statically reviewed; PostgreSQL execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](015-audit-logging-network-isolation-and-security-acceptance.md) · [Hands-on lab](../labs/016-mvcc-snapshots-and-tuple-visibility-lab.md) · [Provisioning SQL](../scripts/016-provision-mvcc-lab.sql) · [Inspection SQL](../scripts/016-mvcc-inspection.sql)

## 1. Operational problem and objectives

An ordinary query reads an earlier row value while another transaction has updated it. A long report continues to see rows that a newer session no longer sees. VACUUM runs successfully, but old versions cannot yet be reclaimed because another session may need them.

These are reliability problems when they affect maintenance, storage, connection capacity or user expectations. DBRE/SRE operators need to explain which snapshot is being used, which tuple version is visible and which retention horizon is relevant before choosing a mitigation.

This chapter introduces MVCC and snapshot lifetime. The lab compares Read Committed and Repeatable Read, demonstrates rollback, and observes retained versions across ordinary VACUUM. Detailed isolation anomalies, lock chains and vacuum tuning follow in later chapters.

## 2. One logical row can have multiple physical versions

An UPDATE creates a new row version rather than overwriting the only representation in place. Older versions may remain physically present while visible to older snapshots. DELETE similarly changes visibility before its physical storage can be reclaimed.

| State | Ordinary reader's interpretation |
|---|---|
| Insert/update in another uncommitted transaction | New version is not visible |
| Committed update before the reader's snapshot | Updated version can be visible |
| Committed update after an older snapshot | Older snapshot can retain earlier version |
| Own earlier change in the same transaction | The transaction can read its own work |
| Rolled-back change | Its new version does not become committed visible data |
| Deleted row needed by an older snapshot | Older reader can still see it until that snapshot ends |

Visibility depends on transaction status, snapshot membership and command-level details. The newest physical version is not necessarily the version a reader may see.

A snapshot is not a durable backup or a general historical query facility. Normal SQL returns versions visible to its snapshot; it does not expose every dead tuple as a time-travel API.

Sequences have special behavior: advancing a sequence is not rolled back like an ordinary table update. Do not use sequence gaps to infer committed rows.

## 3. Snapshot lifetime is an operational decision

| Context | Snapshot behavior relevant to ordinary SELECT |
|---|---|
| Autocommit Read Committed | Each statement starts with its own snapshot |
| Explicit Read Committed transaction | Later statements can see new commits despite the same open transaction |
| Repeatable Read | A transaction retains a data snapshot once established |
| Serializable | Adds protection against serialization anomalies; retries may be required |
| Read Uncommitted in PostgreSQL | Behaves as Read Committed |

BEGIN alone does not imply that a data snapshot has been pinned. Repeatable Read establishes its snapshot when a statement needs one, commonly the first SELECT. It can still see its own subsequent writes.

An older snapshot is not replication lag. If one primary session sees a new value and another sees the old value, check transaction isolation and snapshot age before attributing the difference to replicas or caches.

Read Committed's rule for plain SELECT is not the full behavior of every statement. Concurrent UPDATE/DELETE, row-locking reads and conflict-handling inserts have additional rules. Chapter 017 develops their reliability consequences.

## 4. MVCC reduces read/write blocking; locks remain

Ordinary snapshot SELECT generally does not wait for a concurrent row update merely to read the previously visible version. This does not mean PostgreSQL has no locks.

Two writers targeting the same row can wait. SELECT FOR UPDATE/SHARE asks for row locks and is not an ordinary snapshot read. DDL requiring stronger table locks can block or be blocked by readers. Even a read-only transaction can hold relation locks and a snapshot with maintenance impact.

The lab deliberately uses plain SELECT for visibility checks. Do not add FOR UPDATE to “make the test more realistic”; that changes the concurrency behavior being measured.

When investigating a wait, use wait events and blocking evidence. When investigating retained old versions, use transaction/snapshot horizon evidence. A session can retain a vacuum-relevant horizon without appearing in a lock wait chain.

## 5. Read tuple metadata carefully

Useful visible-row fields:

| Field | Meaning | Limit |
|---|---|---|
| xmin | Transaction ID that inserted this row version | Not a globally ordered commit timestamp |
| xmax | Deletion/update or locking metadata | Nonzero does not prove the visible row is deleted |
| ctid | Physical location of this row version | Changes with updates/rewrites; not a business key |

Keep an application key such as id when comparing versions. Record actual metadata rather than assuming fixed tuple locations or IDs. An UPDATE can change ctid even when it qualifies for HOT; HOT eligibility and observed counters are not visibility guarantees.

Tuple XIDs are 32-bit transaction identifiers. Modern snapshot functions use epoch-aware 64-bit identifiers. Do not compare them through naive casts or sort tuple xmin numerically to reconstruct chronology across wraparound.

pg_current_snapshot exposes xmin:xmax:in-progress IDs. This snapshot xmax is an upper transaction-ID boundary; it is different from a tuple's xmax. Transaction IDs within its bounds still need status/membership interpretation.

The helper uses pg_current_xact_id_if_assigned so observation does not deliberately allocate an XID. Read-only sessions can have a visibility horizon even without an assigned writer XID.

## 6. Old snapshots and VACUUM

VACUUM can remove obsolete versions only when they are no longer needed under the applicable visibility rules. A retained Repeatable Read snapshot can preserve an older updated row or deleted row.

A vacuum that leaves such versions has not necessarily failed. Raising worker counts or running VACUUM repeatedly does not remove the underlying horizon. Distinguish obsolete-but-not-yet-removable versions from reusable storage and free disk space.

Ordinary VACUUM usually makes space available for reuse; it does not normally return all freed space to the OS. VACUUM FULL rewrites data and requires stronger locks; it is not an automatic response to a long snapshot.

n_dead_tup and n_live_tup are estimates. Statistics publication, pruning and background maintenance affect what is observed. Use visible-data results and VACUUM output together, and do not require a tiny fixture to produce one universal counter value.

Long transactions are not the only relevant horizon. Review prepared transactions, replication-slot xmin/catalog_xmin and standby feedback where appropriate. A null backend_xmin at one observation does not prove the session is harmless: it may still hold locks or contain an uncommitted write.

## 7. Production diagnosis and mitigation

Collect endpoint/role, isolation, transaction age, state, backend_xid/backend_xmin, wait events and representative table/vacuum evidence. Protect application query contents; the helper omits query text and limits the exercise's session scope.

| Symptom | Evidence | Action |
|---|---|---|
| Same primary, different visible value | Isolation and first snapshot timing | Explain snapshot scope; end/retry only when contract permits |
| Reader runs while writer is open | Plain SELECT and transaction state | Expected MVCC behavior; do not treat it as a dirty read |
| Second writer waits | Row conflict and blocking PID | Follow bounded concurrency diagnosis |
| Vacuum preserves versions | Old horizon and verbose output | Coordinate transaction completion |
| Large dead-tuple estimate | Churn, horizons, vacuum progress and storage | Establish cause before tuning/rewrite |
| Idle transaction grows old | Owner, transaction scope and timeout policy | Repair pool/application transaction handling |
| Read-only session pins horizon | Retained snapshot and report duration | Bound reporting transactions or use an approved reporting design |

Prefer asking the owner to finish or roll back the identified transaction. Canceling an idle session's query is not transaction cleanup. Inspect resulting state and arrange explicit rollback or narrowly authorized termination when required.

Termination can abort work and trigger application retries. Record blast radius, client behavior and reconciliation needs. Do not terminate all old transactions from a generic age threshold without an agreed runbook.

Timeout policy should distinguish statement duration from idle-in-transaction time and match the workload. Do not silently shorten a legitimate reporting transaction without testing its correctness/retry contract.

## 8. Prechecks, stop conditions and recovery boundaries

Before an exercise or remediation, identify the instance, transaction owner, isolation contract and data scope. Establish bounded statement/lock waits, preserve baseline results and observe from a separate session.

Stop if the instance role changes unexpectedly, writes target another relation, a transaction's owner/purpose is unknown, storage pressure threatens service, or a requested stronger lock/rewrite exceeds the authorized scope.

Rollback of an uncommitted transaction removes its logical changes; physical cleanup can occur later. Ending a read transaction releases its snapshot but does not revert changes another transaction already committed. These are different recovery boundaries.

For the disposable lab, close all experiment transactions and drop only its isolated schema/table. Production data does not have that cleanup boundary.

## 9. Acceptance and official references

Pass requires an uncommitted writer version hidden from another session, own-write visibility, a Read Committed statement seeing a new commit, rollback leaving the prior value, Repeatable Read retaining old updated/deleted rows through VACUUM, and fresh visibility after the retained snapshot ends.

Preserve timestamps, row values, tuple metadata, observed backend horizon and VACUUM output. Do not present static review or estimated counters as executed MVCC evidence.

- [MVCC introduction](https://www.postgresql.org/docs/18/mvcc-intro.html)
- [Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [System columns](https://www.postgresql.org/docs/18/ddl-system-columns.html)
- [Snapshot functions](https://www.postgresql.org/docs/18/functions-info.html)
- [Statistics views](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Routine vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [VACUUM](https://www.postgresql.org/docs/18/sql-vacuum.html)
- [Replication-slot horizons](https://www.postgresql.org/docs/18/view-pg-replication-slots.html)

**Next:** Chapter 017 — Isolation Levels and Application Failure Patterns.
