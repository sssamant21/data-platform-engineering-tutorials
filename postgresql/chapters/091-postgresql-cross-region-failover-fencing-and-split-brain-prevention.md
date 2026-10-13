# Chapter 091 — PostgreSQL Cross-Region Failover, Fencing and Split-Brain Prevention

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Turn [Chapter 090 multi-region DR design](090-postgresql-multi-region-architecture-geo-replication-and-disaster-recovery-design.md) into a safe operational failover protocol. Prevent dual-writer divergence during partial outages, distinguish loss of visibility from loss of the primary, and demonstrate recovery within agreed RPO/RTO.

**Safety invariant:** the old primary must be conclusively fenced from writes before promoting a remote standby. DNS changes, failed pings, expired connections and a region timeout do not by themselves prove fencing.

## 2. Failure states and decisions

```text
Regional alarm / primary unreachable
             |
  Confirm monitoring + control-plane view
             |
   Is original writer conclusively fenced?
        /                    \
       NO                    YES
       |                      |
 STOP / escalate       Check candidate WAL
       |                      |
 Maintain no-promotion   RPO/RTO approval
                              |
                      Controlled promotion
                              |
                     Writer uniqueness test
                              |
                      Route app / validate
                              |
                      Rebuild HA and backup
```

## 3. Split-brain failure modes

- Network partition isolates DR observer while the old primary continues accepting writes.
- Automated HA controllers in different regions independently elect leaders without shared quorum.
- Connection pools or DNS caches continue routing to the former primary.
- An old primary restarts automatically after promotion and resumes writing.
- Stale cloud API responses or expired fencing credentials lead to false success.
- Logical replication conflicts or multi-writer application patterns create divergent histories.

Physical PostgreSQL streaming replication is **not** a distributed consensus protocol. Promotion alone cannot guarantee global single-writer authority.

## 4. Fencing mechanisms and trust

| Control | Strength | Limitation |
|---|---|---|
| Infrastructure power-off / instance isolation | Strong when independently verified | Cloud control-plane failure may block action |
| Storage/network isolation | Can block old writer from clients or durable storage | Must cover all write paths and bypass routes |
| Quorum-based HA with DCS lease | Coordinates leadership and failover | Requires correctly designed quorum and fencing behavior |
| Database read-only setting | Weak as sole fencing | Superusers/control plane can reverse it |
| DNS or load balancer switch | Routing mitigation only | Stale clients and direct connections remain |
| Application write-disable | Useful supplementary control | Cannot guarantee database-level fencing alone |

Use a trusted authority that cannot issue simultaneous valid writer grants to both regions. Validate lease expiration, fencing ordering, control-plane reachability, clock assumptions and operational override permissions. Never rely on a single health-check result.

## 5. Replication eligibility and data-loss decision

On the original primary, `pg_stat_replication` exposes sent, write, flush and replay LSNs for connected standbys. On a standby, `pg_stat_wal_receiver` and receive/replay LSNs show its progress. A standby may have received WAL that is not yet replayed; promotion replays available WAL before becoming writable.

Capture candidate timeline, receive/replay positions, WAL archive continuity and latest verified application transaction marker. If the primary is unavailable, the true latest committed LSN may be unknown. State uncertainty rather than claiming zero data loss.

```text
Estimated bytes behind (when both LSNs are known)
 = pg_wal_lsn_diff(primary_current_lsn, standby_replay_lsn)

RPO estimate = observed missing committed transactions / timestamps
               subject to source visibility and commit semantics
```

LSN bytes alone are not an RPO in seconds. Compare business-critical transaction markers and the approved loss threshold.

## 6. Automatic versus manual failover

Automated failover is acceptable only with tested quorum, fencing, bounded promotion eligibility, routing integration and failure-mode coverage. Cross-region DR often uses a human-approved promotion because partition ambiguity and potential data loss require business decisions. Test simultaneous controller failure and partial network partitions, not only clean instance shutdown.

## 7. Pre-promotion STOP gates

1. Incident commander and failover authority identified.
2. Old primary fencing completed and independently verified.
3. Direct, pooled and privileged write paths to old primary blocked.
4. Candidate standby is healthy, consistent and has required WAL.
5. RPO exposure quantified or explicitly marked unknown and approved.
6. DR region capacity, secrets, extensions, networking and monitoring ready.
7. Backup/archive recovery alternative available.
8. Application routing plan and abort/escalation path approved.

If any critical gate fails, **do not promote**; escalate through the incident command process.

## 8. Controlled promotion sequence

For an approved disposable self-managed standby only, a promotion may be initiated through `pg_ctl promote` or the supported HA operator. In production use the HA/controller/provider interface to preserve authority and state.

After promotion:
- Confirm `pg_is_in_recovery() = false`.
- Record new timeline and relevant WAL positions.
- Execute a uniquely identified test transaction through the authorized application route.
- Prove all old-primary routes reject writes.
- Validate pooler/DNS routing, error rates, p95/p99 latency, replication, backups and archiving.
- Preserve evidence and notify incident stakeholders.

Do not run independent promotion commands concurrently from multiple automation systems.

## 9. Old-primary return and failback

Treat the old primary as **quarantined**. Never restart it as a second writer. Preserve forensic snapshots and timeline history. Evaluate `pg_rewind` prerequisites (including WAL availability and required checksums or `wal_log_hints`) or rebuild from a fresh base backup. Rejoin as a standby only after validation. A later planned switchover requires a separate approval, write-drain, synchronization and routing procedure.

## 10. Observability and alerting

Alert on competing writer claims, failed fencing, lost quorum, stale leases, replication disconnect, growing lag, WAL slot retention, archive failure, stale routing, and DR capacity. Distinguish informational replica disconnect alerts from permission to promote.

Measure:
- Detection time and incident declaration time.
- Fencing completion and independent verification time.
- Promotion duration and application routing recovery.
- Application errors, throughput and tail latency.
- Missing business transaction markers, RPO and RTO.
- Time to restore HA, backups and replica protection.

## 11. Failure injection and recovery

Use a disposable topology to simulate: clean primary stop, network partition, delayed standby replay, fencing API failure, stale pooler route, and former-primary reappearance. For each scenario document expected **STOP / PROMOTE / RECOVER** decision and prove no dual-writer condition. Never test fencing by disconnecting production infrastructure.

## 12. Lab and acceptance

Use [Chapter 091 lab](../labs/091-postgresql-cross-region-failover-fencing-and-split-brain-prevention-lab.md), [read-only failover preflight SQL](../labs/sql/091-failover-fencing-preflight.sql), [failure injection matrix](../labs/dr/091-failover-failure-matrix.csv), [single-writer runbook](../labs/dr/091-single-writer-failover-runbook.md), and [acceptance scorecard](../labs/acceptance/091-failover-fencing-scorecard.csv).

**PASS requires:** independently verified fencing, one authoritative writer, bounded and approved data-loss exposure, application read/write recovery, tested routing and safe old-primary quarantine. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/app-pg-ctl.html
- https://www.postgresql.org/docs/18/app-pgrewind.html
- https://www.postgresql.org/docs/18/high-availability.html

**Next:** Chapter 092 — PostgreSQL Cross-Region Backup, Restore and Disaster Recovery Automation.
