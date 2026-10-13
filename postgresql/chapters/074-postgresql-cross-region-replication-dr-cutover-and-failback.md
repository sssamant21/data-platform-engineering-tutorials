# Chapter 074 — PostgreSQL Cross-Region Replication, DR Cutover and Failback

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design, rehearse and operate cross-region PostgreSQL disaster recovery with measurable RPO/RTO, independently recoverable backups, safe cutover, transaction reconciliation and controlled failback. This chapter extends [Chapter 073 — Multi-Zone HA and DR Design](073-postgresql-multi-zone-high-availability-and-disaster-recovery-design.md) and [Chapter 066 — Backup and DR Acceptance](066-postgresql-backup-and-disaster-recovery-acceptance-lab.md).

## 2. Reference topology

```text
          Region A (active)                           Region B (DR)
   +-----------------------------+          +-----------------------------+
   | Primary + in-region HA      | --WAL--> | Async physical standby      |
   | Regional DCS / writer route |          | Separate recovery controls  |
   | WAL archive + backups       | --copy-> | Independent backup archive  |
   +-----------------------------+          +-----------------------------+
                    |                                      |
             Application writer endpoint / controlled DNS or proxy
                    |                                      |
             Monitoring, IAM, certificates, IaC, runbooks, incident command
```

Cross-region asynchronous replication usually avoids WAN commit latency, but recent acknowledged writes may be absent from Region B after a sudden loss of Region A. Streaming replication is not a substitute for immutable/offsite backups or PITR. Do not stretch a single quorum across distant regions without a reviewed failure-domain and latency model.

## 3. Recovery objectives and failure modes

| Scenario | Preferred response | Data-loss concern |
|---|---|---|
| Single instance failure | In-region HA failover | Depends on local replication |
| Single AZ failure | In-region HA if quorum survives | Depends on eligible standby |
| Regional outage | Invoke DR cutover | Async WAL not yet durable in DR |
| Regional network partition | **Do not assume original region is dead** | Split-brain if both accept writes |
| Corruption / accidental delete | Isolated PITR or backup restore | Replication propagates bad writes |
| Archive or DR standby lag | Repair replication/archive | DR RPO may be out of policy |
| Original region returns | Controlled rejoin/failback | Divergent WAL timelines |

Specify **RPO** (maximum acceptable lost committed data) and **RTO** (time to restore usable application service) for regional DR separately from local HA.

## 4. Cross-region replication setup

A physical standby can be initialized with a verified `pg_basebackup -R` and a dedicated replication role. Use protected credentials, TLS, tightly scoped `pg_hba.conf`, independent storage and a unique standby `application_name`. The standby needs sufficient CPU, disk, IOPS, WAN throughput and WAL retention for catch-up.

Illustrative settings, **not production sizing defaults**:

```conf
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
wal_keep_size = '256MB'
```

A physical replication slot can protect required WAL but may exhaust the source disk when DR is unreachable. `max_slot_wal_keep_size` bounds retention at checkpoints but can invalidate a lagging slot, forcing reseeding. Archive completed WAL independently and verify restore continuity.

## 5. Inspect RPO exposure

On Region A primary:

```sql
SELECT application_name,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(),flush_lsn) AS remote_flush_gap_bytes
FROM pg_stat_replication;
```

On Region B standby:

```sql
SELECT pg_is_in_recovery(),pg_last_wal_receive_lsn(),
       pg_last_wal_replay_lsn(),pg_last_xact_replay_timestamp();
```

Compare LSNs only for the same WAL history/timeline and understand each node's role. Byte lag is **not** a direct number of lost transactions or seconds of RPO. `pg_last_xact_replay_timestamp()` can look stale when idle. Track commit markers, generation rate, WAN delay, archive freshness and last durable/replayed WAL. See [074 inspection SQL](../labs/sql/074-cross-region-dr-inspect.sql).

## 6. DR cutover decision and authorization

1. Declare regional incident, identify incident commander and freeze conflicting automation.
2. Verify whether Region A is actually unavailable or merely unreachable from Region B.
3. **Prove Region A writer is fenced** through independent control-plane evidence; if not provable, fail closed and escalate.
4. Check DR candidate health, last received/flushed/replayed LSN, timeline, slot status, backups and actual RPO estimate.
5. Obtain approval for potential data loss, RTO and application cutover.
6. Promote **exactly one** DR candidate through the supported orchestrator; record timeline and promotion time.
7. Change writer endpoint and invalidate stale pools/sessions. Verify old routing cannot send writes to Region A.
8. Reconcile ambiguous COMMIT outcomes using idempotency keys; validate critical tables and application transactions.
9. Restore DR-region redundancy, archive continuity, backups and monitoring. Measure achieved RPO/RTO.

**Never promote Region B merely because a health check cannot reach Region A.** Network partitions can leave Region A writable.

## 7. Data reconciliation

A client timeout during COMMIT does not prove rollback. Maintain stable request/transaction identifiers, query the authoritative new primary for outcomes, and reconcile source events against downstream queues/CDC consumers. Capture an application-specific consistency report before re-enabling write-heavy jobs. Do not replay all failed requests blindly.

## 8. Controlled failback to Region A

Failback is **not** a reverse DNS change. Once Region B accepts writes, its timeline is authoritative. Before moving back:

1. Restore Region A infrastructure while keeping former primary stopped/fenced.
2. Decide whether `pg_rewind` is safe (required WAL, checksums or wal_log_hints, full_page_writes, compatible system ID/timeline) or rebuild Region A from a new base backup from Region B.
3. Start Region A as a **standby of Region B**, not as an independent primary.
4. Verify WAL receive/replay catch-up, backup/archive configuration, replication slots and capacity.
5. Plan a maintenance switchover with a write drain, verified LSN convergence, old-leader fencing and authoritative promotion.
6. Update routing and credentials; reconcile transactions and verify application health.
7. Restore standby redundancy and backups in both regions, and capture final evidence.

If rewind prerequisites or source WAL are missing, rebuild from a verified new backup rather than forcing divergence.

## 9. Observability and alerts

Monitor regional leader/fencing status, WAN connectivity, receive/flush/replay LSNs, WAL bytes/sec, slots and `safe_wal_size`, archive failures, backup freshness, proxy backend, DNS/client reconnection, application synthetic writes, regional capacity, IAM/key availability and achieved RPO/RTO. Alert on **time to disk exhaustion** and DR replication falling outside approved data-loss policy.

## 10. Failure modes and safe actions

| Symptom | Risk | Response |
|---|---|---|
| DR standby disconnected | Increasing potential data loss | Restore WAN/receiver, check WAL availability |
| Replication slot retains excessive WAL | Source disk exhaustion | Repair consumer, add headroom; do not blindly drop slot |
| Slot `wal_status=lost` | DR cannot resume from required WAL | Reinitialize standby from verified source |
| Region A status uncertain | Dual-writer risk | No DR promotion until fencing is proven |
| DR promoted but app fails | RTO not achieved | Inspect routing, secrets, pools, dependencies |
| Region A returns as old primary | Timeline divergence | Keep fenced; rewind or rebuild |
| Backups unavailable in DR | No independent recoverability | Repair archive/backup chain before declaring readiness |

## 11. Hands-on lab and acceptance

Use [Chapter 074 lab](../labs/074-postgresql-cross-region-replication-dr-cutover-and-failback-lab.md), [inspection SQL](../labs/sql/074-cross-region-dr-inspect.sql) and [DR cutover scorecard](../labs/acceptance/074-cross-region-dr-scorecard.csv).

**PASS requires:** independent fencing evidence, one writable region, verified DR candidate, measured RPO/RTO, application routing and transaction reconciliation, regional backup/PITR continuity, safe rejoin/failback and no unexplained data divergence. If the lab uses simulated regions or lacks fencing, mark physical regional resilience and fencing **NOT VERIFIED**.

**Runtime validation pending.**

## References

- https://www.postgresql.org/docs/18/warm-standby.html
- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/app-pgrewind.html
- https://patroni.readthedocs.io/

**Next:** Chapter 075 — PostgreSQL High Availability and Disaster Recovery Acceptance Project.
