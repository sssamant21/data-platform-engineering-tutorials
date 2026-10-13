# Chapter 050 — High Availability and Disaster Recovery Acceptance Project

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime acceptance pending

## 1. Mission

Prove—not merely document—that a PostgreSQL HA/DR design can withstand a primary outage, recover from accidental data changes, rejoin a former primary, and meet business-approved RPO/RTO targets. This is the capstone for [Chapters 041–049](049-replication-failover-rejoin-and-timeline-recovery.md).

## 2. Acceptance architecture

```text
                   PostgreSQL 18 primary (A)
                       |            |
                 WAL archive     streaming WAL
                       |            |
                 base backup     standby (B)
                       |            |
                       +------ isolated PITR target (C)

During failover: A is fenced -> B promoted -> A rewound/rebuilt as standby
During data-loss drill: C restored from verified base backup + WAL to approved target
```

All destructive, promotion, rewind and routing exercises must occur in an **isolated disposable environment**. Do not run this capstone on production or shared staging. Production use requires a separate change-approved runbook and qualified operator.

## 3. Scenario and acceptance objectives

A critical service requires HA for infrastructure failures and PITR for operator mistakes. The test simulates (a) a primary outage and controlled promotion, (b) an unwanted data change followed by isolated PITR, and (c) rejoin of the former primary. The exercise must prove there is only one writable primary at any time.

| Requirement | Illustrative target | Pass evidence |
|---|---|---|
| Availability | Single writable leader | Fencing proof, topology and routing checks |
| HA RPO | <= 5 minutes | Last business commit on old primary versus recovered primary |
| HA RTO | <= 15 minutes | Failure detection to validated application service |
| PITR RPO | <= 5 minutes | Chosen restore point and verified recovered records |
| PITR RTO | <= 60 minutes | Detection to isolated restore validation and service readiness |
| Backup integrity | 100% of selected artifacts verified | Manifest/hash and tool exit status |
| Recovery correctness | Critical invariants pass | SQL and application checks |
| Rejoin | No dual-writer condition | Timeline/rewind or rebuild evidence |

Targets are **examples**, not defaults. Record actual business SLOs, data-loss policy and test measurements. A failover RPO claim cannot be inferred from LSN bytes alone; use committed business transaction evidence.

## 4. Phase A — Preflight and risk controls

1. Inventory cluster IDs, major versions, timeline, primary/standby endpoints, slots, synchronous replication policy and connection routing.
2. Verify backup schedule, last successful physical backup, manifest, archive continuity and restore credentials.
3. Validate monitoring of `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_stat_archiver`, `pg_replication_slots`, WAL disk headroom and standby conflicts.
4. Confirm **independent fencing** method, business owner approval, abort conditions and a fresh isolated restore target.
5. Confirm backup and recovery artifacts are protected, access-controlled and retained throughout the exercise.

Run the [read-only preflight SQL](../labs/sql/050-primary-preflight.sql) on the primary and [standby preflight SQL](../labs/sql/050-standby-preflight.sql) on the standby.

## 5. Phase B — Backup and PITR acceptance

- Create a physical backup to a new destination and verify it using `pg_verifybackup`.
- Confirm WAL archive continuity from backup through the chosen recovery point; record timeline history and recovery target.
- Use the lab-owned fixture and markers from [Chapter 045](../labs/045-point-in-time-recovery-and-disaster-recovery-lab.md). Simulate the unwanted change **only** in the disposable lab.
- Restore to isolated target C, replay to a verified pre-incident point, and validate that good rows exist and unwanted changes do not.
- Record actual achieved PITR RPO/RTO, missing legitimate transactions, validation output and reconciliation requirements.

**Gate:** PITR cannot pass if the backup verifies but the restore or business invariants fail.

## 6. Phase C — HA failover acceptance

1. Capture the latest committed test marker and primary/standby WAL positions.
2. Simulate primary A failure within the isolated lab.
3. **Prove fencing** prevents A from accepting writes before B is promoted or application writes are redirected.
4. Assess B's replay position, durability, health and expected data loss.
5. Promote B under manual approval; verify `pg_is_in_recovery() = false`, single-writer topology, application reads/writes and monitoring.
6. Measure elapsed HA RTO and actual recovered business marker for HA RPO.
7. If fencing, recovery position or application checks fail, **abort** and preserve evidence; do not promote another node.

**Gate:** no confirmed fencing means failover acceptance fails, even if promotion technically succeeds.

## 7. Phase D — Former-primary rejoin and timelines

Preserve A's original data directory and logs. Verify cluster ancestry, divergent timelines, `wal_log_hints` or checksums, `full_page_writes`, required WAL and compatibility. Assess `pg_rewind --dry-run` on a stopped, fenced target; if unsuitable, rebuild A from a verified base backup. Configure A as a standby of B and verify streaming catch-up. Never resume A as an independent writable primary.

## 8. Phase E — Failure injection and recovery decisions

| Injected failure | Expected detection | Required response |
|---|---|---|
| Primary unreachable | Health and client errors | Fence, evaluate B, controlled promotion |
| Standby behind | LSN gaps and business marker | Quantify loss, approve or reject |
| WAL archive missing segment | Recovery logs | Reject PITR, select valid chain |
| Replication slot abandoned | restart_lsn and disk trend | Owner review, safe remediation |
| Standby conflicts | Conflict counters and canceled queries | Adjust workload/replay policy |
| Rewind prerequisites absent | pg_rewind dry-run failure | Rebuild from base backup |
| Dual-writer risk | Routing/fencing evidence | Immediate stop; preserve data |

## 9. Operational acceptance rubric

| Gate | Weight | Must pass? |
|---|---:|---|
| Backup integrity and WAL continuity | 15 | Yes |
| Independent PITR restore and row validation | 20 | Yes |
| Primary fencing and single-writer proof | 20 | Yes |
| Controlled failover and business validation | 15 | Yes |
| Timeline-safe rejoin or approved rebuild | 10 | Yes |
| Measured HA/PITR RPO and RTO | 10 | Yes |
| Alerting, runbooks and audit evidence | 10 | Yes |

**Scoring:** 100 points total. A missing mandatory gate is a **FAIL regardless of total score**. All gates must pass, and the achieved objectives must meet the approved service tier to claim production readiness. A lab pass does not automatically authorize a production cutover.

## 10. Deliverables

Produce a signed evidence pack with: topology diagram; backup manifest verification; WAL inventory; primary/standby telemetry; recovery target; failover approval; fencing evidence; promotion timeline; application validation; old-primary rejoin method; actual RPO/RTO; incidents and corrective actions; rollback and ownership matrix.

[Chapter 050 acceptance lab](../labs/050-high-availability-and-disaster-recovery-acceptance-project-lab.md) contains the operator checklist and SQL probes.

## 11. Troubleshooting and stop conditions

Stop if cluster identity is ambiguous, the old primary cannot be fenced, the backup/WAL chain is incomplete, the restore target is not isolated, replica loss exceeds the approved RPO, a rewind target is still running, or the application cannot prove a single writer. Preserve logs and escalate rather than improvising.

## Official references

- [Continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [Failover](https://www.postgresql.org/docs/18/warm-standby-failover.html)
- [pg_rewind](https://www.postgresql.org/docs/18/app-pgrewind.html)
- [Monitoring](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Next:** Chapter 051 — PostgreSQL Security Architecture, Roles and Privilege Boundaries.
