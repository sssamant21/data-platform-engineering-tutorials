# Chapter 038 — Table Partitioning Fundamentals and Operational Tradeoffs

**Audience:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Draft; runtime verification pending

## 1. Learning outcomes

Choose between range, list and hash declarative partitioning; explain partition pruning, local indexes, partition keys, constraints, retention and operational tradeoffs; validate pruning with EXPLAIN; design safe partition creation and retirement.

## 2. Architecture

A partitioned parent defines the logical table. Child partitions hold actual rows; routing uses partition bounds. The parent does not store ordinary heap rows. PostgreSQL supports RANGE (time windows), LIST (categories/regions), and HASH (balanced distribution by key). A DEFAULT partition catches unmatched values when defined but can complicate future partition attachment.

```text
events (partitioned parent, RANGE(event_time))
   ├── events_2026_01  [2026-01-01, 2026-02-01)
   ├── events_2026_02  [2026-02-01, 2026-03-01)
   └── events_2026_03  [2026-03-01, 2026-04-01)
```

Bounds are lower-inclusive and upper-exclusive. A missing partition causes inserts outside available bounds to fail unless a suitable DEFAULT partition exists.

## 3. Choosing a strategy

| Strategy | Good fit | Operational caution |
|---|---|---|
| RANGE | Event timestamps, time-series retention | Pre-create future partitions; handle late data and timezone boundaries |
| LIST | Bounded categories or tenant groups | Skew and category growth |
| HASH | Evenly distribute rows by stable key | Retention by date is difficult; modulus changes are expensive |

Partitioning is not a universal performance improvement. Benefits depend on pruning, retention, per-partition maintenance and workload shape. Too many tiny partitions increase planning, catalog, autovacuum and operational overhead. Partitioning does not distribute load across servers by itself.

## 4. Range partition DDL

```sql
CREATE TABLE telemetry.events (
  event_id bigint NOT NULL,
  event_time timestamptz NOT NULL,
  tenant_id integer NOT NULL,
  payload text NOT NULL,
  PRIMARY KEY (event_id, event_time)
) PARTITION BY RANGE (event_time);

CREATE TABLE telemetry.events_2026_01 PARTITION OF telemetry.events
  FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');
```

The primary key includes the partition key. PostgreSQL partitioned-table UNIQUE/PRIMARY KEY constraints must include all partition-key columns and have additional restrictions; there is no general global unique index across partitions. Foreign keys, triggers, indexes, generated columns and defaults need version-specific review. Partitioned indexes are virtual at the parent with physical indexes on child partitions.

## 5. Pruning and query plans

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM telemetry.events
WHERE event_time >= timestamptz '2026-02-01 00:00:00+00'
  AND event_time < timestamptz '2026-03-01 00:00:00+00';
```

Look for partitions absent from the plan or `Subplans Removed` for execution-time pruning. Compare with a query lacking a partition-key predicate. Pruning is based on partition bounds, not necessarily indexes. Expressions, implicit casts, generic prepared plans and join patterns may affect when pruning occurs. Verify on the actual query, parameter types and workload; never claim pruning merely because the table is partitioned.

## 6. Indexes, statistics and autovacuum

Each leaf partition has separate physical storage, indexes and vacuum activity. Query `pg_stat_user_tables` and `pg_stat_user_indexes` at leaf level. Autovacuum does not automatically ANALYZE the partitioned parent based solely on child changes in the same way as ordinary tables; schedule parent ANALYZE when needed for representative statistics. Review local index sizes and per-partition autovacuum settings; excessive partition counts can increase maintenance overhead.

```sql
SELECT inhparent::regclass AS parent, inhrelid::regclass AS child
FROM pg_inherits WHERE inhparent='telemetry.events'::regclass;

SELECT relid::regclass, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE relid IN (SELECT inhrelid FROM pg_inherits
                WHERE inhparent='telemetry.events'::regclass);
```

## 7. Partition lifecycle and retention

Pre-create future partitions before ingest; detect missing partitions and unexpected DEFAULT growth. Prefer partition detach/drop for whole-period retention rather than enormous DELETE batches, after verifying legal retention, backups, replication, downstream consumers and foreign-key dependencies.

`ALTER TABLE ... DETACH PARTITION ... CONCURRENTLY` has restrictions and cannot run inside a transaction block. A detached partition remains a regular table until explicitly archived or removed. `DROP TABLE` is destructive and must have a separate approval, verified backup and ownership check. Partition attachment may scan existing rows and acquire locks; use validated CHECK constraints where appropriate and plan the lock window.

## 8. Production change runbook

1. Baseline table sizes, workload filters, query plans, WAL, replicas and retention obligations.
2. Choose partition key and granularity from query patterns, ingestion rate and retention.
3. Verify unique/foreign-key semantics, update behavior when partition key changes, DEFAULT handling and late-arriving data.
4. Create partitions ahead of time with idempotent automation and alert on future-bound coverage.
5. Roll out queries and ingestion; inspect EXPLAIN pruning, planning time, locks, latency and worker utilization.
6. Retire partitions only after retention, archive, dependencies and replica checks.
7. Document rollback: detach/attach or route adjustments may require locks; dropped data requires restore.

## 9. Lab and acceptance

[Chapter 038 hands-on lab](../labs/038-table-partitioning-fundamentals-and-operational-tradeoffs-lab.md) builds three monthly partitions, inserts synthetic rows, checks partition routing, compares plans and performs a non-destructive detach/reattach exercise in an isolated schema.

**Acceptance:** explain bounds, missing-partition behavior, constraint restrictions, pruning evidence, per-leaf maintenance and safe retention decisions. **Validation:** static review only; PostgreSQL 18 execution pending.

## Official references

- [Table partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html)
- [CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
- [ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
- [EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Next:** Chapter 039 — Partition Pruning, Indexes and Query Performance.
