# Chapter 069 — PostgreSQL Synchronous Replication and Commit Durability

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design, configure, measure and troubleshoot PostgreSQL synchronous replication without accidentally sacrificing write availability or acknowledging a weaker durability level than the business expects. This chapter builds on [Chapter 067 — Streaming Replication](067-postgresql-streaming-replication-and-high-availability-architecture.md) and [Chapter 068 — Replication Slots and WAL Retention](068-postgresql-replication-slots-wal-retention-and-lag-management.md).

## 2. Commit acknowledgment architecture

```text
Application COMMIT
      |
      v
Primary WAL generation + local WAL handling
      |
      +--> asynchronous: client may receive success without standby acknowledgment
      |
      +--> synchronous_standby_names selects required standby acknowledgments
                       |
           remote_write: standby writes WAL to OS
           on:           standby flushes WAL durably
           remote_apply: standby replays WAL and makes it query-visible
                       |
                 COMMIT acknowledged
```

**Important:** Acknowledgment semantics depend on both `synchronous_commit` and `synchronous_standby_names`. Without a configured eligible synchronous standby, remote acknowledgment modes do not establish remote durability. Local `synchronous_commit=off` can acknowledge before local WAL is durably flushed, risking recent transactions on crash. Synchronous replication is not a replacement for backups, PITR, fencing or safe HA election.

## 3. synchronous_commit levels

| Setting | Commit waits for | Tradeoff |
|---|---|---|
| `off` | No synchronous local WAL flush requirement before success | Lowest latency; recent acknowledged transactions can be lost on crash |
| `local` | Local WAL flush | Local durability without waiting for standby |
| `remote_write` | Local flush plus standby WAL written to operating system, when synchronous standby configured | Lower remote wait; standby OS crash may lose not-yet-flushed WAL |
| `on` | Local flush plus required standby WAL flush, when configured | Stronger remote durability; network/standby availability affects commits |
| `remote_apply` | Required standby WAL replay, when configured | Supports immediate standby read visibility; potentially greater latency |

A standby acknowledgment does not mean independent protection against operator error, corruption, or split-brain. Durability guarantees are conditional on configured replication topology and failure assumptions.

## 4. Selecting synchronous standbys

```conf
# Priority-based: first eligible standby from ordered list
synchronous_standby_names = 'FIRST 1 (standby_a, standby_b)'

# Quorum-based: any two eligible standbys
synchronous_standby_names = 'ANY 2 (standby_a, standby_b)'
```

`application_name` in each standby's `primary_conninfo` identifies the standby. A priority-based policy selects the highest-priority connected eligible standby; quorum mode waits for the configured number of acknowledgments. Design for zone failure and network partition. `ANY 2` with only one available standby will block transactions using remote synchronous commit modes.

## 5. Read-only inspection

On the primary:

```sql
SHOW synchronous_commit;
SHOW synchronous_standby_names;

SELECT application_name, state, sync_priority, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

On the standby:

```sql
SELECT pg_is_in_recovery() AS is_standby,
       pg_last_wal_receive_lsn() AS receive_lsn,
       pg_last_wal_replay_lsn() AS replay_lsn;
SELECT status, written_lsn, flushed_lsn, latest_end_lsn
FROM pg_stat_wal_receiver;
```

Use [069 diagnostic SQL](../labs/sql/069-synchronous-replication-inspect.sql) for an extended inspection. `write_lag`, `flush_lag` and `replay_lag` are not continuous wall-clock backlog measures; they may be NULL on idle systems. Correlate them with WAL LSN progression, application commit latency and wait events.

## 6. Establish a safe baseline

1. Deploy a disposable PostgreSQL 18 primary and at least two standbys, with distinct PGDATA and endpoints.
2. Verify `pg_stat_replication.state='streaming'` and standby `application_name` values.
3. Record local and cross-zone network latency, WAL write/flush/replay latency, and application p50/p95/p99 commit latency.
4. Begin with asynchronous or `synchronous_commit=local` to establish a baseline.
5. Set `synchronous_standby_names='FIRST 1 (standby_a, standby_b)'` **only in the lab** and test `on`, `remote_write` and `remote_apply` in separate sessions.
6. Simulate standby unavailability and observe `SyncRep` waits and blocked commits; use a separate administrative session to restore the standby.
7. Return the lab to the baseline and verify application writes recover.

**Do not run a synchronous-commit outage test against production.** A COMMIT may block after its WAL record is locally committed but before remote acknowledgment. If a client times out or is canceled, transaction outcome can be ambiguous: query authoritative state using an idempotency key before retrying.

## 7. Monitoring and failure diagnosis

| Symptom | Evidence | Safe response |
|---|---|---|
| COMMIT latency rises | `SyncRep` wait events, standby flush lag | Inspect network, disk, WAL sender/receiver and synchronous policy |
| COMMIT blocks indefinitely | No eligible synchronous standby | Restore eligible standby or invoke approved availability/durability change |
| `sync_state='async'` unexpectedly | Application name mismatch, priority/quorum selection | Verify standby names and `synchronous_standby_names` |
| Standby flush advances but apply stalls | Replay conflicts, I/O, long reads | Inspect replay and `remote_apply` cost |
| Standby lost after acknowledgment | Failure domain and flush mode | Review durability assumption and restore/reseed plan |
| Application retries duplicate writes | Ambiguous commit outcome | Use idempotent transaction keys and reconcile state |

Monitor `pg_stat_activity.wait_event='SyncRep'`, synchronous candidate count, per-standby state, WAL bytes behind, commit latency percentiles, transaction timeouts, replication slot WAL retention, network failures, and primary/standby disk. Alert on absence of required standbys before write unavailability occurs.

## 8. Availability versus durability decision

| Requirement | Example policy | Caution |
|---|---|---|
| Maximize write availability | Async or local commit | Standby may lack acknowledged writes |
| Require remote durable acknowledgment | `synchronous_commit=on` + eligible synchronous standby | Writes can block if no required standby |
| Immediate reads from synchronous standby | `remote_apply` | Higher latency and replay-dependent availability |
| Zone failure tolerance | Multiple standbys with appropriate FIRST/ANY policy | Quorum placement and fencing still required |

Never automatically weaken durability to unblock writes without an approved incident policy. A DCS/HA manager, fencing, client routing and backups are separate controls.

## 9. Lab and acceptance

Complete [Chapter 069 lab](../labs/069-postgresql-synchronous-replication-and-commit-durability-lab.md), inspect with [069 SQL](../labs/sql/069-synchronous-replication-inspect.sql), and record latency/availability outcomes in the [069 scorecard](../labs/monitoring/069-commit-durability-scorecard.csv).

**Acceptance gates:** correct standby selection, verified acknowledgment modes, measured commit latency, observed blocked-commit behavior, documented ambiguous-outcome handling, safe rollback, no production changes, and explicit business signoff on durability/availability policy.

**Runtime validation pending.**

## References

- https://www.postgresql.org/docs/18/warm-standby.html#SYNCHRONOUS-REPLICATION
- https://www.postgresql.org/docs/18/runtime-config-wal.html
- https://www.postgresql.org/docs/18/runtime-config-replication.html
- https://www.postgresql.org/docs/18/monitoring-stats.html

**Next:** Chapter 070 — PostgreSQL Planned Switchover, Failover and Split-Brain Prevention.
