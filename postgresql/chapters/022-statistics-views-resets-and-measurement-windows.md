# 022 — Statistics Views, Resets and Measurement Windows

Audience: DBRE and SRE only. Baseline: PostgreSQL 18.
Status: authored/static reviewed; live PostgreSQL verification pending.

[Previous: SLIs and Error Budgets](021-database-slis-slos-and-error-budgets.md) · [Measurement lab](../labs/022-statistics-views-resets-and-measurement-windows-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Select a statistics view for an incident question, distinguish current state from accumulated work, and calculate rates only across compatible samples. Explain why a counter can appear frozen, why zero is not always evidence of no activity, and why resets create new measurement epochs.

PostgreSQL statistics describe database behavior. They do not directly count successful application requests. Chapter 021's consumer SLIs still require their own instrumentation.

## Choose the view and scope

| Question | Starting view | Scope and interpretation |
|---|---|---|
| Which backend is waiting now? | pg_stat_activity | Backend state and waits; visibility depends on role |
| Who blocks a lock request? | pg_locks with pg_blocking_pids | Lock-manager state, not a cumulative counter |
| How much work occurred in this database? | pg_stat_database | Database cumulative counters plus current gauges |
| Which table accumulated writes or scans? | pg_stat_user_tables | Relations in the connected database |
| Which indexes were used? | pg_stat_user_indexes | Index access counters, not proof of optimal design |
| Which relation blocks were served from PostgreSQL buffers? | pg_statio_user_tables / indexes | Buffer-access accounting, not physical disk telemetry |
| Which backend categories performed I/O? | pg_stat_io | Cluster-wide rows keyed by backend type/object/context |
| What WAL activity accumulated? | pg_stat_wal | Cluster-wide WAL statistics |
| What did checkpoints and background writing do? | pg_stat_checkpointer / pg_stat_bgwriter | Separate responsibilities and reset domains |
| Where is a maintenance operation now? | pg_stat_progress_* | Active-operation progress; rows can disappear on completion |

Read the PostgreSQL 18 schema, not a copied dashboard from another major release. pg_stat_io arrived in PostgreSQL 16 and the separate checkpointer view in 17; PostgreSQL 18 adds fields and categories that older collectors may not understand. Explicit columns and versioned collector output make changes reviewable.

Table/index views are local to the connected database. Cluster counters cannot be attributed entirely to one database. Replication views describe specific server relationships; do not assume a primary view includes every cascading standby.

## Classify the value before calculating

A counter accumulates events or work: xact_commit, temp_bytes or wal_records. Use a compatible before/after difference, then divide by elapsed seconds for a rate.

A gauge describes a current quantity: numbackends, session count or an estimated live/dead tuple population. Report point values or trends. Do not turn a decrease in an estimated population into a negative event rate.

A timestamp describes an event or measurement boundary: stats_reset, last_autovacuum or backend_start. A duration can be cumulative time or the age of a current operation; determine which before using it.

n_live_tup and n_dead_tup are estimates. Their changes reflect workload and maintenance; they are not exact physical counts. A high lifetime scan count does not identify what happened during the incident window.

## Account for publication lag and observer caching

Backend cumulative statistics are published to shared memory at intervals, typically when the backend goes idle, and are not an instantaneous account of running work. Current activity information and cumulative counters follow different collection paths.

The observer also has a transaction-level consistency policy:

- cache, the default, reuses accessed cumulative statistics until that observer transaction ends.
- snapshot caches a broader statistics snapshot for consistent cumulative-statistics access within that transaction.
- none avoids cumulative-statistics caching and can reduce overhead for a single access, while allowing skew across multiple reads.

Current activity information can also be retained within an observer transaction. Even a fresh cumulative snapshot is not an atomic photograph of every lock, activity row and server counter.

pg_stat_clear_snapshot discards the observer's cached statistics. It does not reset server counters. The next access fetches statistics again, but cannot force another backend's unpublished work to appear.

Short independent collection transactions are usually easier to reason about than a monitoring connection left in BEGIN. Record sampling timestamps, terminate the collection transaction promptly, and use current-transaction views such as pg_stat_xact_user_tables when examining a backend's own uncommitted work.

## Define the measurement envelope

Each stored sample should identify collector schema, physical source or verified inventory identity, endpoint, server version, postmaster start time, recovery role, database OID/name, relevant reset marker, timestamp, tracking policy and the selected fields.

Do not use a load-balanced service name as the only physical source identity. A reader endpoint can move between replicas. A shared system identifier identifies a physical replication lineage, not necessarily one running node.

The [database collector](../scripts/022-database-statistics-snapshot.sql) uses a caller-supplied source_id plus observed endpoint/start/database fields. The lab guard establishes that source is the disposable primary. Production source_id must come from verified inventory; an arbitrary string is not authenticated identity.

It deliberately captures one database's counters in a short read-only statistics snapshot, without application data or query text. It includes both collection time and statistics-snapshot time. Neither timestamp says that every backend had just flushed its statistics.

## Calculate compatible deltas

~~~text
delta(counter) = after(counter) - before(counter)
rate = delta(counter) / elapsed snapshot seconds
interval buffer hit ratio =
  delta(blks_hit) / (delta(blks_hit) + delta(blks_read))
~~~

Use actual elapsed time, not a hard-coded assumed scrape interval. If no block-access events occurred, the ratio is undefined, not 100%. blks_read is a PostgreSQL buffer miss; the operating system may satisfy it from its cache, so it is not equivalent to a physical disk read.

The [offline delta helper](../scripts/022-statistics-window-delta.py) refuses source, endpoint, database, version, recovery-role, restart, tracking-policy and reset mismatches. It also refuses nonpositive/stale intervals, excessive gaps, missing fields and counter decreases. It reports a numbackends point-value pair rather than a gauge rate.

This deliberately conservative helper starts a new baseline after any restart, even when a clean restart preserved cumulative values. It is a teaching tool for database counters, not a complete time-series ingestion system.

A long gap can hide a short burst. A valid interval rate is only an average. Choose a maximum gap appropriate to the analysis; changing the allowed gap does not reconstruct missing samples.

## Recognize reset domains

| Reset or boundary | Operational effect |
|---|---|
| pg_stat_clear_snapshot | Clears observer cache only |
| pg_stat_reset | Resets statistics for the connected database |
| pg_stat_reset_single_table_counters | Resets one relation's counters |
| pg_stat_reset_shared | Resets selected cluster statistics; omitted/NULL target affects all supported shared targets |
| Extension-specific reset | Separate semantics, ownership and reset marker |
| Clean shutdown and restart | Cumulative statistics can survive; node start time changes |
| Crash, immediate shutdown, restore/base-backup start or PITR | Cumulative counters are reset |

A reset boundary invalidates a subtraction even if the later value is numerically larger. Traffic can refill a counter after reset. A decreasing counter is evidence of incompatibility, but the absence of a decrease does not prove continuity.

Not every view exposes a per-object reset timestamp. Database stats_reset does not prove an individual table was never reset. Record administrative reset events and invalidate affected series; track relation OIDs and object lifecycle too. A drop/recreate or extension-entry eviction can break continuity without a simple database-wide marker change.

Statistics resets are privileged administrative actions, not prerequisites for an incident investigation. They erase diagnostic history and can affect maintenance scheduling: database-wide reset also clears counters used for autovacuum/analyze decisions. The official documentation recommends database-wide ANALYZE afterward. Do not reset production counters merely to obtain a convenient zero baseline.

The lab resets only its newly created disposable database and analyzes its fixture afterward. No shared or existing ops_lab counters are deliberately reset.

## Interpret configuration and missing values

Verify track_counts, track_activities and relevant timing policies at the source. With I/O timing disabled, a zero timing counter does not establish negligible latency. Enabling track_io_timing can add overhead and requires an appropriate privilege; assess it rather than casually changing it during collection.

NULL activity fields may reflect visibility restrictions. Missing progress rows may mean completion, inactivity or timing of observation. An empty or broken scrape must not become a fabricated zero. Preserve unknown states and emit collection-health evidence.

Collector queries themselves generate database activity and can affect commit/read statistics. Do not promise exact workload transaction counts from a database-wide delta. Background work and other sessions contribute too.

## Incident measurement procedure

1. State the question, source, database, metric class and observation window.
2. Capture baseline identity, reset markers, tracking policies and a bounded sample.
3. Observe or apply an authorized change; retain independent application and host evidence.
4. Capture another fresh sample and validate continuity before calculating.
5. If invalid, retain both samples and the reason, then establish a fresh baseline.
6. Correlate rates with latency, waits, host I/O and consumer outcomes. Record limitations and cleanup.

Do not bridge a reset with zero-clamping, silently merge replicas, or average incompatible percentages. Keep raw samples so another engineer can reproduce the calculation.

## Acceptance and official references

Complete the lab's cached-observer demonstration, compatible deltas, scoped reset, rejected cross-reset interval and new-baseline recovery. Prove that clearing observer cache and resetting database counters are different operations.

- [PostgreSQL 18 cumulative statistics and functions](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Statistics configuration and timing](https://www.postgresql.org/docs/18/runtime-config-statistics.html)
- [Monitoring activity](https://www.postgresql.org/docs/18/monitoring.html)
- [PostgreSQL 16 release notes](https://www.postgresql.org/docs/16/release-16.html)
- [PostgreSQL 17 release notes](https://www.postgresql.org/docs/17/release-17.html)

Next: Chapter 023 — Query Statistics with pg_stat_statements.
