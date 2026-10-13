# Chapter 093 — PostgreSQL Multi-Region Observability, DR Drills and Reliability Testing

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Establish a measurable, repeatable multi-region PostgreSQL reliability program that verifies detection, recovery, data correctness and operational readiness. Build on [Chapter 090 — Multi-Region DR Architecture](090-postgresql-multi-region-architecture-geo-replication-and-disaster-recovery-design.md), [Chapter 091 — Fencing and Split-Brain Prevention](091-postgresql-cross-region-failover-fencing-and-split-brain-prevention.md), and [Chapter 092 — Cross-Region Backup and Restore](092-postgresql-cross-region-backup-restore-and-disaster-recovery-automation.md).

**Principle:** a green replication dashboard does not prove that a region can recover, an application can reconnect, or the old writer is safely fenced.

## 2. DR observability model

Collect evidence from **both regions** and an independent observer:

| Layer | Metrics / evidence | Failure detected |
|---|---|---|
| PostgreSQL primary | WAL generation, commits, active connections, errors, locks | Writer degradation |
| Standby | WAL receive/write/flush/replay positions, receiver status | Transport/replay backlog |
| Replication slots | Active state, retained WAL, safe WAL size | Disk exhaustion risk |
| Archiving | Success/failure counters, last archived WAL/time | PITR gaps |
| Backups | Backup age, checksum/manifest, cross-region copy status | Unrecoverable backups |
| Restore tests | Last success, recovered transaction marker, elapsed time | Actual recovery failure |
| Control plane | Quorum, leases, fencing state, promotion authority | Split-brain exposure |
| Application | p95/p99, errors, retries, pool wait, routing target | Customer impact |
| Infrastructure | CPU, memory, IOPS, disk, network, DNS, IAM/KMS | Regional dependency failure |

Keep alerting outside the failed region where possible; ensure metrics storage, paging, credentials and dashboards remain accessible during source-region loss.

## 3. SQL observability

Use [093 read-only SQL](../labs/sql/093-multi-region-observability-inspect.sql) on each PostgreSQL 18 node. Distinguish `pg_stat_replication` (primary-side sender view) from `pg_stat_wal_receiver` (standby-side receiver view). Capture UTC sample time, node identity and role.

`pg_wal_lsn_diff` reports WAL byte distance, not elapsed RPO. Replay timestamp age may be misleading when the primary is idle. Interpret lag together with last observed transaction marker, send/receive/replay LSNs and application commit semantics.

## 4. DR SLIs, SLOs and error budgets

Recommended DR service-level indicators:
- **Recovery time:** incident declaration to successful application service restoration.
- **Recovery point:** newest verified committed transaction recovered relative to the incident boundary.
- **Restore success rate:** completed verified isolated restores / scheduled restores.
- **Backup recoverability age:** elapsed time since last *verified* recoverable backup chain.
- **Replication freshness:** transport and replay backlog with workload context.
- **Fencing proof:** time from incident declaration to independent verification old writer cannot write.
- **DR coverage:** critical services with approved RPO/RTO, tested runbooks and owners.

Targets must be agreed with business owners; do not invent universal RPO/RTO thresholds. Maintain an error budget and escalation for missed restore exercises or untested dependencies.

## 5. Alert design

| Alert | Example signal | Operator action |
|---|---|---|
| Replication disconnected | Receiver absent beyond approved window | Check network/credentials, slot/WAL |
| WAL backlog growing | Byte backlog or slot retained bytes increase | Check receiver, I/O and disk headroom |
| Archive failures | Failure counter rises or latest archive stale during WAL activity | Repair archive and verify PITR chain |
| Restore exercise overdue | Last verified restore older than policy | Schedule immediate controlled restore |
| DR credentials invalid | Backup/KMS access probe fails | Escalate identity and key access |
| Writer authority conflict | Multiple active writer claims | Block routing, page incident command |
| DR capacity insufficient | Projected failover load exceeds headroom | Scale and retest before accepting DR |

Alerts must have owner, severity, threshold rationale, runbook, suppressions and test evidence. Never let a missing heartbeat automatically authorize standby promotion.

## 6. Drill program

Use a progressive cadence based on risk and policy:

1. **Tabletop:** roles, escalation, RPO/RTO, regional dependency mapping.
2. **Backup restore:** isolated full/PITR recovery and application validation.
3. **Replication degradation:** throttled WAN, lag, WAL retention, archive outage.
4. **Controlled regional failover:** fence old writer, promote candidate, route application.
5. **Regional dependency failure:** DNS, IAM/KMS, object storage, monitoring, control plane.
6. **Failback:** quarantine old primary, reconcile timelines, rebuild standby, controlled switchover.

Do not run destructive failure injection against production without explicit change approval and blast-radius controls. A single-host lab cannot validate true regional independence.

## 7. DR drill execution protocol

**Preflight:** approve scope and rollback, baseline application traffic, verify backups, designate incident commander and independent observer, prepare abort limits.

**Inject:** execute only the approved isolated fault, record exact UTC timestamps, capture monitoring and application traces.

**Recover:** follow Chapter 091 fencing gates, select standby promotion or Chapter 092 restore, record all decisions and unknown data-loss exposure.

**Validate:** exactly one writer, application transactions, backup/archive, standby health, credentials, RPO/RTO and business data consistency.

**Close:** restore protection, preserve logs, document deviations, assign corrective actions and retest.

## 8. RPO and RTO measurement

```text
Observed RTO = application acceptance UTC - incident start UTC
Observed RPO = newest committed transaction absent after recovery
               expressed as its age relative to incident boundary
```

Use unique transaction markers with durable timestamps and independent application-side evidence. Clock skew, async commit behavior and visibility gaps can affect conclusions. If the last committed transaction cannot be proven, mark RPO **UNKNOWN**, not zero.

## 9. Failure modes and reliability findings

- Green standby connection with high replay backlog: failover may violate RPO.
- Backup job success but no verified restore: recoverability unproven.
- Monitoring hosted only in failed region: blind DR operation.
- Stale DNS/poolers after promotion: application downtime continues after database recovery.
- Unverified fencing: dual-writer hazard even if the new region serves traffic.
- Broken KMS access: remote backups are unusable despite intact objects.
- DR region undersized: recovery completes but application SLOs fail.
- Failure injection succeeds but no evidence or rollback: exercise cannot be accepted.

## 10. SRE operational governance

Maintain versioned runbooks, on-call ownership, an incident commander, evidence retention, audit trails, exercise calendar, issue tracker and action closure. Trend recovery times and exercise defects. Promote DR readiness only after **independent reviewer signoff**, not based on a self-reported success.

## 11. Acceptance and next steps

Use [Chapter 093 lab](../labs/093-postgresql-multi-region-observability-dr-drills-and-reliability-testing-lab.md), [read-only inspection SQL](../labs/sql/093-multi-region-observability-inspect.sql), [DR drill matrix](../labs/dr/093-dr-drill-matrix.csv), [DR evidence template](../labs/dr/093-dr-drill-evidence-template.md), and [acceptance scorecard](../labs/acceptance/093-multi-region-reliability-scorecard.csv).

**PASS requires:** independently accessible telemetry, alert/runbook coverage, successful isolated restore, verified fencing and one writer, measured RPO/RTO, application recovery, failback readiness and action closure. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/warm-standby.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/high-availability.html

**Next:** Chapter 094 — PostgreSQL Multi-Region Disaster Recovery Simulation and Acceptance Project.
