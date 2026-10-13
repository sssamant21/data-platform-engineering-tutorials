# Chapter 090 — PostgreSQL Multi-Region Architecture, Geo-Replication and Disaster Recovery Design

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design a PostgreSQL architecture that survives a regional failure with explicitly agreed RPO/RTO, an authoritative writer, verified replication, recoverable backups, and an executable failover/failback runbook. This chapter extends earlier streaming replication, HA, backup/PITR and operational acceptance chapters.

**Safety invariant:** never promote a remote standby unless the original primary is fenced or conclusively unavailable as a writer. A network partition is not proof that the old primary has stopped accepting writes.

## 2. Reference architecture

```text
Region A (active)                            Region B (DR)
┌──────────────────────────────┐            ┌──────────────────────────────┐
│ Application + connection pool│            │ Standby app / read services  │
│          |                   │            │          |                   │
│  PostgreSQL primary          │── WAL ────>│ PostgreSQL warm standby      │
│     |                        │   async    │    |                         │
│  Local HA standby            │            │ Optional local DR standby   │
│     |                        │            │    |                         │
│  Backups + WAL archive       │──copy─────>│ Independent backup/archive  │
└──────────────────────────────┘            └──────────────────────────────┘
                \\____________________  _____________________/
                        Control plane, fencing, DNS/routing,
                          monitoring, credentials, runbooks
```

Separate regional compute, storage, networking, IAM, secrets, monitoring and backup failure domains where practical. A second AZ is not a second region.

## 3. Define RPO and RTO before choosing replication

- **RPO:** maximum acceptable data loss measured from the last durable/recoverable transaction in the surviving region.
- **RTO:** maximum acceptable time from declared incident to restored application service.
- **MTTR and detection:** monitoring, human approval, fencing, promotion, application routing and validation all consume RTO.
- **Recovery consistency:** require an explicit policy for transactions committed in the old region but absent from the promoted standby.

Asynchronous physical replication usually permits some data loss at region failure. Synchronous cross-region replication can reduce the commit-loss window but increases write latency and may reduce availability when the remote region is unreachable. PostgreSQL synchronous settings and application commit behavior must be validated for the chosen durability guarantee.

## 4. Replication choices

| Design | Advantages | Tradeoffs |
|---|---|---|
| Physical streaming replication | Whole-cluster WAL-based standby; efficient DR | Same major PostgreSQL version; standby read-only; failover coordination |
| Logical replication | Selected tables, schema flexibility, migration use cases | DDL/sequences/roles not automatically fully covered; conflict/consistency planning |
| WAL archive + base backups | PITR and independent recovery | Restore and replay can exceed tight RTO |
| Managed cross-region replica | Provider-integrated deployment | Service-specific lag, promotion and pricing behavior |
| Application-level multi-writer | Potential locality | Not native PostgreSQL physical DR; requires conflict resolution |

A cross-region replica is **not** a substitute for independently tested backups. Logical replication is not a transparent full-cluster DR replacement.

## 5. PostgreSQL physical DR prerequisites

Confirm `wal_level=replica` or higher, `max_wal_senders`, `max_replication_slots`, network/TLS, `pg_hba.conf`, replication identity and correct standby bootstrap using `pg_basebackup` or a supported provider/operator method. Configure `primary_conninfo`, `primary_slot_name` where applicable, `standby.signal`, and a robust WAL archive/restore path.

Replication slots can prevent required WAL removal but may fill disk if the consumer stalls. Use capacity alarms and a recovery procedure; `max_slot_wal_keep_size` can cap retention at the cost of standby catch-up failure.

## 6. Network and latency budget

Estimate round-trip latency, throughput and failure behavior between regions. Account for TLS, DNS, routing, bandwidth, WAL bursts, large transactions, archive delivery, and storage write throughput in the DR region. For synchronous replication, evaluate commit latency at p95/p99 and the effect of remote disconnection on availability.

```text
Required sustained replication bandwidth
  > peak WAL generation rate × safety factor
WAL retention exposure
  ≈ WAL generation rate × maximum expected disconnect duration
```

Validate burst and backfill scenarios, not only steady averages.

## 7. Observability and lag interpretation

Inspect `pg_stat_replication` on the primary, `pg_stat_wal_receiver` on the standby, `pg_last_wal_receive_lsn()`, `pg_last_wal_replay_lsn()`, `pg_last_xact_replay_timestamp()`, WAL archive status and slots.

`pg_wal_lsn_diff` measures byte differences; timestamp-based replay delay can be misleading on an idle primary. Differentiate send, write, flush and replay positions, and distinguish byte backlog from recovery time. A missing row can mean disconnection or monitoring visibility limitations.

## 8. Fencing and single-writer promotion

Promotion workflow must enforce:

1. Incident commander declares regional failover with evidence.
2. Fence old primary at infrastructure/control-plane level, revoke writer routing, or use an HA system with proven quorum/lease semantics.
3. Confirm no remaining authoritative writes can reach the old primary.
4. Estimate last durable WAL and potential RPO loss; record decision.
5. Promote eligible DR standby through supported HA/operator/provider process or `pg_ctl promote` on a self-managed standalone standby.
6. Verify recovery state changed, writable transactions work, required extensions/roles/config are present, and app traffic routes only to new primary.
7. Rebuild replication/backup protection in the new active region and monitor.

**Do not automatically promote on an isolated cross-region network timeout.** If fencing cannot be established, stop and escalate instead of risking split-brain.

## 9. Failback is a separate migration

The old primary must **not** simply restart as a writer. Determine divergence, preserve forensic backups, rebuild/reseed it as a standby of the new primary, or use a validated `pg_rewind` path when prerequisites are met. Confirm timeline history, replication slots, WAL availability, data reconciliation, extension parity, and routing. Plan a new controlled switchover only after catch-up and acceptance.

## 10. Backups and regional independence

Keep independent, encrypted, access-controlled backups and WAL archives in another failure domain; verify retention, immutability where required, key availability and periodic isolated restores. Confirm that control-plane credentials, DNS, KMS, object storage and monitoring remain usable during a source-region outage.

## 11. Failure-mode matrix

| Failure | Risk | Safe response |
|---|---|---|
| Region A unavailable | Writes lost or delayed; uncertain writer | Fence and verify before promotion |
| Inter-region partition | Both sides may appear alive | Quorum/fencing; no automatic dual promotion |
| Standby replay lag | RPO breach | Quantify backlog; compare alternate recovery |
| WAL slot growth | Primary disk full | Add headroom, repair consumer; no blind slot deletion |
| Archive outage | PITR gap | Repair archive; stop risky changes |
| DNS/control-plane failure | App routes to stale primary | Test TTL, routing, credentials and manual bypass |
| DR region capacity shortfall | RTO/latency failure | Provision and load-test DR capacity |
| Failback divergence | Conflicting transaction histories | Rebuild/reconcile, never rejoin as dual writer |

## 12. Lab and acceptance

Use [Chapter 090 DR design lab](../labs/090-postgresql-multi-region-architecture-geo-replication-and-disaster-recovery-design-lab.md), [read-only DR inspection SQL](../labs/sql/090-geo-replication-inspect.sql), [architecture decision matrix](../labs/dr/090-multi-region-architecture-matrix.csv), [failover runbook](../labs/dr/090-regional-failover-runbook.md), and [acceptance scorecard](../labs/acceptance/090-multi-region-dr-scorecard.csv).

**PASS requires:** approved RPO/RTO, replication and archive verification, independent backup restore, tested fencing, single-writer proof, timed promotion, application acceptance and safe failback. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/warm-standby.html
- https://www.postgresql.org/docs/18/high-availability.html
- https://www.postgresql.org/docs/18/logical-replication.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/app-pgbasebackup.html
- https://www.postgresql.org/docs/18/app-pgrewind.html

**Next:** Chapter 091 — PostgreSQL Cross-Region Failover, Fencing and Split-Brain Prevention.
