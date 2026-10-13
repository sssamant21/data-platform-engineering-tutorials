# Chapter 070 — PostgreSQL Planned Switchover, Failover and Split-Brain Prevention

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Operate PostgreSQL high availability without dual writers or silent data loss. Execute a planned switchover with verified catch-up, rehearse an unplanned failover with explicit fencing, validate application routing and transaction outcomes, and safely rejoin the former primary. Integrates [Chapter 067](067-postgresql-streaming-replication-and-high-availability-architecture.md), [068](068-postgresql-replication-slots-wal-retention-and-lag-management.md) and [069](069-postgresql-synchronous-replication-and-commit-durability.md).

## 2. Architecture and ownership

```text
                  Application write endpoint / connection pool
                                  |
                         HA leader routing
                                  |
                 +----------------+----------------+
                 |                                 |
           Primary A                          Standby B
        WAL source + writes               WAL receive/replay
                 |                                 |
                 +---------- HA manager -----------+
                               |
                     DCS/quorum + fencing
                               |
                    backup/PITR + observability
```

PostgreSQL streaming replication does **not** supply automatic fencing, distributed leader election or writer endpoint updates. Use a supported HA manager and its documented failover API, or a managed service that supplies these controls. A load balancer health check alone cannot prove single-writer safety.

## 3. Planned switchover versus unplanned failover

| Aspect | Planned switchover | Unplanned failover |
|---|---|---|
| Primary state | Healthy and reachable | Failed or uncertain |
| Writes | Drain/freeze in controlled window | Must fence old primary before promotion |
| Standby selection | Verify fully caught up | Choose best eligible candidate within data-loss policy |
| Data-loss objective | Aim for zero acknowledged transaction loss | Depends on replication and last durable WAL |
| Cutover | Controlled routing and connection drain | Fenced promotion, route update, reconciliation |
| Rejoin | Former primary demoted/rebuilt | Must prove old leader fenced and timelines reconciled |

A standby with low replay lag is not automatically eligible. Check timeline, replication health, synchronous acknowledgment policy, hardware/zone placement, replay position, promotion permissions and application readiness.

## 4. Non-negotiable split-brain controls

1. **Single authoritative leader:** quorum-backed DCS or equivalent control plane with an explicit lease/term.
2. **Fencing:** prove old primary cannot accept writes (STONITH, cloud isolation, storage/network fencing or trusted HA mechanism) before another node is writable.
3. **Fail-closed routing:** writer endpoint must route only to verified leader; stale connections must be drained.
4. **Promotion discipline:** exactly one approved promotion, tracked by incident commander and automation logs.
5. **Timeline verification:** new primary creates a new WAL timeline; capture timeline history.
6. **Old-primary reintegration:** never restart the old primary as a writable node. Rewind or rebuild it after verifying compatibility and fencing.

**Never promote a standby solely because the primary is unreachable from one observer.** Network partition can make both nodes believe they are leader.

## 5. Preflight inspection

Use [Chapter 070 inspection SQL](../labs/sql/070-ha-preflight.sql). On primary:

```sql
SELECT pg_is_in_recovery() AS is_standby,
       pg_current_wal_lsn() AS current_lsn;
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn,wal_status
FROM pg_replication_slots;
```

On standby:

```sql
SELECT pg_is_in_recovery() AS is_standby,
       pg_last_wal_receive_lsn() AS receive_lsn,
       pg_last_wal_replay_lsn() AS replay_lsn;
```

Compare LSNs only within a compatible timeline and with the correct role context. Check synchronous policy, pending WAL, archive health, replication slots, disk headroom, client sessions and backups. Document source and destination system identifiers, timeline and endpoint ownership.

## 6. Planned switchover runbook

1. Announce maintenance and establish an explicit write freeze/drain. Stop scheduled writes, migrations and background jobs; verify no active write transactions.
2. Confirm primary/standby healthy, standby eligible, and replication catch-up to a recorded primary flush LSN.
3. Have the HA orchestrator perform a **controlled demotion and promotion** with fencing/single-leader guarantees. Avoid hand-executing pg_promote while old primary accepts writes.
4. Verify former primary is stopped or read-only and fenced before replacement accepts writes.
5. Verify new primary `pg_is_in_recovery()=false`, expected timeline, transaction marker and application write test.
6. Switch writer endpoint and connection pool; drain stale connections and validate read routing.
7. Reconfigure former primary as standby using the HA manager; use pg_rewind or fresh base backup only after validating prerequisites and timelines.
8. Re-enable workloads, inspect replication, capture RTO, data-loss evidence and rollback decision.

## 7. Unplanned failover runbook

1. Declare incident and assess primary health from independent vantage points.
2. Stop unsafe automatic/manual promotion while fencing status is uncertain.
3. Establish quorum/leader authority; **fence the old primary** and capture evidence.
4. Select a standby using durable WAL/replay position and policy-defined RPO.
5. Promote through the HA manager; capture promotion timestamp and timeline.
6. Update routing and revoke stale writer access. Verify exactly one writable primary.
7. Reconcile application transactions: clients that timed out at COMMIT may have ambiguous outcomes; check idempotency keys before retrying.
8. Restore redundancy, backup/WAL archive continuity and monitoring; measure achieved RPO/RTO.

If fencing cannot be proven, **stop** and escalate rather than accepting split-brain risk.

## 8. pg_rewind and rejoin

`pg_rewind` may allow the former primary to rejoin by reconciling divergent data files, but only when the tool's prerequisites hold (data checksums or wal_log_hints, full_page_writes, required WAL, correct system ID and compatible versions). The old primary must be **stopped** and its data protected. Validate divergence, timeline history, archive availability and rollback. If prerequisites fail or confidence is low, rebuild the standby from a verified new base backup. Rewind is not a substitute for fencing.

## 9. Observability and acceptance

| Signal | Why it matters |
|---|---|
| HA leader term and DCS quorum | Prevent conflicting leadership |
| Fencing result and old-primary write probe | Verify single-writer invariant |
| Standby receive/replay/flush LSN | Assess candidate currency |
| Writer endpoint target and pool connections | Detect stale routing |
| WAL timeline and replication slot health | Detect divergence and retention risks |
| Application idempotency reconciliation | Resolve ambiguous commits |
| Failover duration and achieved RPO | Validate SLO |
| Backup/archive health after cutover | Ensure historical recoverability |

The [Chapter 070 lab](../labs/070-postgresql-planned-switchover-failover-and-split-brain-prevention-lab.md) rehearses planned and unplanned paths using **isolated** nodes and explicit safety gates. Use [070 HA preflight SQL](../labs/sql/070-ha-preflight.sql) and [070 acceptance scorecard](../labs/acceptance/070-ha-failover-scorecard.csv).

## 10. Common failures

| Symptom | Likely cause | Safe response |
|---|---|---|
| Two writable nodes | Fencing/leadership failure | Halt writes, isolate nodes, incident escalation |
| Promotion blocked | Standby not eligible or HA lease active | Inspect HA manager and quorum |
| Stale application writes | Connection pool or DNS cache | Drain/terminate stale sessions and verify endpoint |
| Data absent after failover | Async WAL not durable on promoted standby | Quantify loss, reconcile and restore if needed |
| Old primary cannot rejoin | Divergent timeline or rewind prerequisites missing | Rebuild safely from verified backup |
| Failover succeeds but WAL grows | Broken slots or archiver | Restore archive/slot health promptly |

## 11. Acceptance criteria

**PASS** requires: old primary fenced before new writes, exactly one writable primary, documented promotion authority, verified endpoint switch, test transaction correctness, no unexplained WAL/timeline divergence, measured RPO/RTO, restored redundancy and successful rollback/rejoin rehearsal. If the lab lacks a real fencing/DCS implementation, mark automated failover and fencing **NOT VERIFIED**, not PASS.

**Runtime validation pending.**

## References

- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/app-pg-ctl.html
- https://www.postgresql.org/docs/18/app-pgrewind.html
- https://www.postgresql.org/docs/18/monitoring-stats.html

**Next:** Chapter 071 — PostgreSQL HA Automation, Leader Election and Failover Orchestration.
