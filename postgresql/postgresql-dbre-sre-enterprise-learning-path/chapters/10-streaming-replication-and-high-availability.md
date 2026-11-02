# Chapter 10 — Streaming Replication and High Availability

**Audience:** PostgreSQL DBRE/SRE, database and platform engineers  
**Level:** Intermediate · **Session:** 60 minutes · **Reference:** PostgreSQL 17  
**Status:** Authored; runtime exercise and independent review **not yet executed**

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 10 lab](../labs/chapter-10/README.md) · [Progress tracker](../STATUS-TRACKER.md)

## 1. Learning objectives and agenda

By the end of this lesson, engineers should be able to:
1. Distinguish physical streaming replication from logical replication and from backups.
2. Explain WAL sender/receiver, base backup, recovery, replication slots, timelines, and read-only hot standby.
3. Interpret primary and standby health/lag signals without equating a single metric to RPO.
4. Design for **single-writer safety** and explain why promotion without fencing risks split-brain.
5. Demonstrate an isolated primary/standby topology with **no failover or promotion**.
6. Describe RPO/RTO test requirements, application reconnection, and independent acceptance evidence.

| Minutes | Activity | Output |
|---|---|---|
| 0–10 | Availability requirements and failure domains | SLO/RPO/RTO assumptions |
| 10–20 | WAL-based replication architecture | Primary/standby data flow |
| 20–30 | Asynchronous vs synchronous, slots, lag, failover safety | Design questions |
| 30–53 | [Chapter 10 hands-on lab](../labs/chapter-10/README.md) | Read-only replication observations |
| 53–60 | Incident runbook and acceptance review | Evidence checklist |

## 2. What HA does and does not solve

**High availability** aims to restore or maintain service when a component fails. A replica can reduce recovery time, but it does not independently provide correct application failover, backups, data corruption protection, or cross-region disaster recovery.

- **RPO (Recovery Point Objective):** maximum acceptable data loss measured in time, defined by the business.
- **RTO (Recovery Time Objective):** maximum acceptable service restoration time, defined by the business.
- **SLO:** measurable reliability target, such as availability or successful query latency.
- **Failure domain:** host, storage, availability zone, region, network or control-plane boundary.

A primary and standby on one Docker host share the same host failure domain; the chapter lab teaches mechanics, **not enterprise HA**.

## 3. Architecture and write lifecycle

~~~text
                      application / connection router
                                     |
                          writes only to primary
                                     |
                              PRIMARY (RW)
                          transaction -> WAL
                                     |
                                WAL sender
                                     |
                           physical WAL stream
                                     |
                                WAL receiver
                                     |
                             STANDBY (RO)
                          WAL replay -> data pages
                                     |
                          optional read-only queries
~~~

**Primary:** the designated writer that generates WAL.  
**Standby:** a server in recovery that replays WAL; `pg_is_in_recovery()` returns true.  
**WAL sender:** primary-side process serving WAL.  
**WAL receiver:** standby-side process receiving WAL.  
**Base backup:** initial copy of an entire PostgreSQL cluster, used to seed the standby.  
**`standby.signal`:** instructs PostgreSQL 12+ to start in standby mode.  
**`primary_conninfo`:** libpq settings telling the standby where/how to connect.  
**Replication slot:** records the WAL retention requirement of a consumer; an inactive slot can retain large amounts of WAL.  
**Timeline:** identifies a branch of WAL history, important after promotion and recovery.

Physical streaming replication copies WAL for the **whole PostgreSQL cluster**, not selected tables. Logical replication publishes selected changes and has different schema, sequence, DDL and failover considerations.

## 4. Replication mode tradeoffs

| Mode | What commit waits for | Benefit | Risk / cost |
|---|---|---|---|
| Asynchronous (default) | Local commit, not standby acknowledgement | Lower write latency, more tolerant of replica outage | Recent committed transactions may be absent on standby after primary failure |
| Synchronous, `remote_write` | Standby has written WAL to OS | Stronger acknowledgement | Not equivalent to durable flush |
| Synchronous, `on` (remote flush) | Required standby has flushed WAL | Stronger durability boundary | Commit latency and availability depend on standby/quorum |
| Synchronous, `remote_apply` | Required standby has replayed commit | Read-after-write visibility on that standby | Higher latency and availability tradeoff |

The meaning of `synchronous_commit` depends on `synchronous_standby_names` and which standbys qualify. Never promise zero data loss for every failure scenario merely because a setting says "synchronous." Check failure domains, storage durability, client acknowledgement and fencing.

**Lab scope:** asynchronous physical replication only. No synchronous setting changes, automated failover, or deliberate outage simulation.

## 5. Safe single-writer architecture

An uncoordinated promotion can produce **two independent writable primaries** when the old primary remains accessible. That is split-brain, and PostgreSQL does not automatically reconcile divergent histories.

Production promotion must be gated by:
1. **Independent fencing:** prove the old primary cannot accept writes, using controls outside the failing database itself (e.g., power/host fencing, cloud API fencing, verified storage or network isolation with an independent authority).
2. **Leader election and quorum:** prevent competing orchestrators from choosing different writers.
3. **Candidate eligibility:** assess replay state, timeline, replication lag and data-loss approval.
4. **Routing control:** direct writes only to the new primary and remove the old writer from all write endpoints.
5. **Application validation:** verify transaction success, connection-pool behavior and idempotent retries.
6. **Old-primary reintegration:** use a reviewed rewind/rebuild procedure after confirming histories; never simply start an old primary as another writer.

**Do not run `pg_promote()`, `pg_ctl promote`, force-failover, or partition/kill exercises in this chapter's lab.** A complete HA rehearsal needs independent staging, approvals, rollback and evidence (covered in later chapters).

## 6. Replication health and lag

### Primary-side read-only queries

~~~sql
SELECT application_name, client_addr, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication
ORDER BY application_name;

SELECT slot_name, slot_type, active, restart_lsn, wal_status,
       pg_size_pretty(
         GREATEST(0, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn))::bigint
       ) AS approximate_retained_bytes
FROM pg_replication_slots
WHERE restart_lsn IS NOT NULL;
~~~

The slot calculation approximates the WAL position gap, **not exact on-disk WAL size**. A slot's `wal_status` can indicate retention danger. Slot retention is not unlimited safe capacity; alert on slot inactivity, retained bytes and disk headroom.

### Standby-side read-only queries

~~~sql
SELECT pg_is_in_recovery() AS standby,
       pg_last_wal_receive_lsn() AS received_lsn,
       pg_last_wal_replay_lsn() AS replayed_lsn,
       pg_last_xact_replay_timestamp() AS last_replayed_commit;

SELECT status, receive_start_lsn, written_lsn, flushed_lsn,
       latest_end_lsn, last_msg_receipt_time
FROM pg_stat_wal_receiver;
~~~

**Important interpretation:** `now() - pg_last_xact_replay_timestamp()` can increase on an *idle, healthy* cluster with no transactions to replay. It is not a standalone replication-lag or RPO metric. Likewise, `write_lag`, `flush_lag` and `replay_lag` can be NULL on a caught-up idle standby; NULL is not necessarily an outage.

Track together: replication connectivity/state, byte-position gaps, recent write/replay confirmation, slot retention, WAL disk usage, client error rate and application recovery objectives. RPO is established from a **measured failure/recovery exercise**, not a dashboard screenshot.

## 7. Cross-platform ownership

| Concern | Self-managed VM/bare metal | AWS RDS for PostgreSQL | Kubernetes operator |
|---|---|---|---|
| Replica deployment | DB/platform team | RDS-managed deployment features | Operator/controller plus platform team |
| Promotion/fencing | Explicit HA manager, quorum and independent fencing | Managed failover behavior depends on selected RDS architecture | Operator/cluster and infrastructure fencing controls |
| WAL retention | DBRE owns slot/archive/disk monitoring | RDS exposes supported parameters and service metrics | DBRE/operator own retention plus PVC/storage |
| Endpoint switch | Proxy/DNS/service discovery with application validation | Managed endpoints and client reconnect testing | Services/operator routing and client reconnect testing |
| Recovery validation | DBRE-led staging evidence | Customer still validates restore and application RPO/RTO | DBRE/platform team validates backup, storage and recovery |

Do not assume RDS Multi-AZ instance, RDS Multi-AZ DB cluster, read replicas, or a Kubernetes standby have identical read routing and failover guarantees. Review the specific managed architecture.

## 8. Troubleshooting decision table

| Signal | Likely causes to investigate | Safe first action |
|---|---|---|
| No row in `pg_stat_replication` | Standby disconnected, auth/DNS/network, failed receiver | Read standby logs, `pg_stat_wal_receiver`, primary `pg_hba.conf` and slot status |
| Receiver connected, replay behind | I/O saturation, replay conflicts, long read queries | Inspect standby activity, WAL receive/replay positions, storage latency |
| WAL disk growing | Inactive replication slot, archiving backlog, high write rate | Read slot status, archive status, disk utilization and growth rate |
| Replica query canceled | Recovery conflicts with long-running reads | Inspect standby conflicts; adjust workload rather than disable replay |
| Client write failures during failover | Routing stale, connection pool not refreshed, retries unsafe | Verify one writer and application recovery workflow before changing endpoints |
| `requested WAL segment has already been removed` | Required WAL no longer available | Rebuild standby from approved fresh base backup/archive; do not bypass consistency checks |

## 9. Hands-on exercise and review

Complete the [isolated Chapter 10 lab](../labs/chapter-10/README.md), which creates a **new** primary and physical standby with a dedicated Docker network and named volumes. Verify:
- primary is writable and standby reports recovery mode;
- synthetic data inserted on primary becomes visible on standby;
- `pg_stat_replication`, `pg_stat_wal_receiver` and `pg_replication_slots` show expected topology;
- standby rejects a write attempt;
- no promotion, failover or destruction is performed.

### Architecture review prompt

A healthcare application requires 99.95% availability and a business-approved RPO of 30 seconds, with patient record updates. Evaluate whether a single AZ, asynchronous cross-AZ standby, or managed Multi-AZ design meets requirements. Identify the additional testing needed: independent fencing, application reconnection, audit correctness, measured data loss, PITR, and failback. Do not claim compliance based on topology alone.

## 10. Acceptance and evidence

- [ ] Explain physical vs logical replication and why a standby is not a backup.
- [ ] Identify WAL sender, receiver, slot, `standby.signal` and recovery state.
- [ ] Demonstrate primary write / standby read-only behavior.
- [ ] Record replication connectivity, slot health and LSN observations.
- [ ] Explain limitations of time-based lag indicators and idle systems.
- [ ] Describe fencing, quorum, endpoint control and split-brain risk.
- [ ] Explain RPO/RTO measurement and independent approval requirements.
- [ ] Retain sanitized outputs and reviewer sign-off **after** real lab execution.

**Publication status:** Content authored; static formatting review only. No live lab execution, measured RPO/RTO, failover validation, independent approval or production certification is claimed.

## 11. Official references (PostgreSQL 17)

- [Warm standby and streaming replication](https://www.postgresql.org/docs/17/warm-standby.html)
- [pg_basebackup](https://www.postgresql.org/docs/17/app-pgbasebackup.html)
- [Replication configuration](https://www.postgresql.org/docs/17/runtime-config-replication.html)
- [Monitoring statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [Replication slots view](https://www.postgresql.org/docs/17/view-pg-replication-slots.html)
- [High availability, load balancing and replication](https://www.postgresql.org/docs/17/high-availability.html)
