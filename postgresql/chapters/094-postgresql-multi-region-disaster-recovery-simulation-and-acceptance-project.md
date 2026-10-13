# Chapter 094 — PostgreSQL Multi-Region Disaster Recovery Simulation and Acceptance Project

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Capstone mission

Combine [Chapter 090 — Multi-Region DR Architecture](090-postgresql-multi-region-architecture-geo-replication-and-disaster-recovery-design.md), [Chapter 091 — Fencing and Split-Brain Prevention](091-postgresql-cross-region-failover-fencing-and-split-brain-prevention.md), [Chapter 092 — Cross-Region Backup/Restore](092-postgresql-cross-region-backup-restore-and-disaster-recovery-automation.md), and [Chapter 093 — Observability and DR Drills](093-postgresql-multi-region-observability-dr-drills-and-reliability-testing.md) into one evidence-based recovery acceptance project.

**Success is application recovery with one authoritative writer, measured RPO/RTO, recoverable backups and a safe return to protected steady state.**

## 2. Scenario and scope

Design a regional failure exercise using two independent failure domains. A two-container single-host lab is useful for learning but does **not** demonstrate true regional resilience.

```text
Region A (normal active)                   Region B (standby / DR)
App -> pooler -> primary --WAL stream----> warm standby
           |                                   |
      backup + WAL archive ----cross-copy--> remote backup store
           |                                   |
      writer fencing authority  <---->  promotion authority
                         |
             independent monitoring + incident command
```

Scope application read/write correctness, routing, replication, WAL archiving, backup restore, security, IAM/KMS, DNS, on-call and change control.

## 3. Acceptance contract

Define and approve before the exercise:

| Objective | Definition | Evidence |
|---|---|---|
| RPO | Maximum tolerated loss of committed business transactions | Durable transaction markers and recovered state |
| RTO | Incident start to successful application acceptance | UTC timeline and application smoke test |
| Writer safety | At most one authoritative writer at every point | Independent fencing and routing proof |
| Application SLO | p95/p99, throughput and errors under DR load | Application and pooler telemetry |
| Data correctness | Expected business records and constraints intact | SQL reconciliation and app assertions |
| Recoverability | Isolated PITR restore available | Restore logs and recovered marker |
| Failback | Old primary safely rebuilt/rejoined as standby | Timeline and replication evidence |

Targets must be supplied by service owners. Do not invent universal RPO/RTO limits or report an unexecuted drill as PASS.

## 4. Preconditions and readiness

- Incident commander, database operator, SRE, application owner and independent verifier assigned.
- Production-like dataset and load profile; test environment separated from production.
- Current backup generation, WAL archive and isolated restore verified.
- DR region has capacity for peak load and dependencies.
- Fencing mechanism tested, including direct and privileged writer routes.
- Change ticket, blast radius, abort triggers and rollback documented.
- Observability accessible outside simulated failed region.
- Time synchronization and durable transaction markers available.

## 5. Exercise phases

### Phase A — Baseline

Capture PostgreSQL version, role, timeline, send/receive/replay LSN, slots, archive state, backup status, application p95/p99 and error rate. Insert unique business transaction markers via a test application and record UTC commit evidence.

### Phase B — Fault injection

Inject one approved fault at a time in an isolated topology: clean primary shutdown, WAN partition, standby lag, failed WAL archive, or regional control-plane dependency. Record the exact fault and its detection time. Do not equate failed health checks with proven primary fencing.

### Phase C — Declare and decide

Incident commander compares failover versus backup/PITR. Quantify last recoverable transaction and possible loss. If writer fencing is uncertain, **STOP**; do not promote.

### Phase D — Fence and recover

Independently verify the original primary cannot accept writes through any direct or pooled path. Promote eligible standby through the supported HA/controller mechanism, or restore a quarantined PostgreSQL instance from independent backup/WAL using Chapter 092.

### Phase E — Application acceptance

Confirm `pg_is_in_recovery() = false` on the new writer, verify exactly one writer, route test application, check unique transaction markers, constraints, extensions, credentials, throughput, p95/p99 and error rate.

### Phase F — Restore protection

Reestablish replicas, WAL archive, backups, alerts and capacity headroom. Quarantine old primary; inspect timeline divergence and rebuild or rewind only under supported prerequisites.

### Phase G — Failback and closure

Rejoin former primary **as a standby**, prove catch-up, then optionally perform a separately approved planned switchover. Close with independent acceptance and corrective actions.

## 6. Incident timeline and measurements

```text
Detection time = alert UTC - fault UTC
Fencing time = independently verified fence UTC - declaration UTC
Observed RTO = application accepted UTC - incident start UTC
Observed RPO = age of newest committed transaction missing after recovery
               relative to the incident boundary
```

If durable source-side commit evidence is unavailable, report RPO **UNKNOWN**. WAL byte distance is not a time-based RPO. Account for clock skew and async commit semantics.

## 7. Failure injection matrix

| Fault | Expected safe behavior | Pass evidence |
|---|---|---|
| Clean primary failure | Fence then promote eligible standby | Single writer, app recovery |
| Network partition | No promotion without fencing | STOP decision and alert |
| Replica lag | RPO gate before promotion | Transaction-marker comparison |
| Archive gap | Fail PITR closed | Missing WAL detected and escalated |
| DR IAM/KMS failure | Block inaccessible restore | Alert and alternate plan |
| Stale DNS/pooler | Prevent old-writer traffic | Direct and pooled route tests |
| Old primary reappears | Quarantine, never dual-write | Rejoin only as standby |
| DR capacity shortage | Fail SLO acceptance | Measured load and scale decision |

## 8. Observability and evidence

Preserve: redacted topology, exact commands/controller actions, timestamps, SQL inspection snapshots, fencing proof, WAL/timeline positions, backup/restore logs, application traces, dashboard screenshots, business transaction markers, alerts, approvals and deviations. Store evidence outside the failed region and avoid sensitive data in public repositories.

## 9. STOP and rollback rules

Stop the drill immediately if:
- Original writer cannot be conclusively fenced.
- Multiple active writer claims appear.
- Data loss exceeds approved RPO or cannot be assessed.
- Backup or WAL recovery chain is broken.
- DR application error budget or critical security controls fail.
- The test impacts unapproved production resources.

Rollback is **not** restarting the old primary as a writer. Use supported HA failback, restore/reseed and approved routing with a single authoritative timeline.

## 10. Operational acceptance and signoff

Use [Chapter 094 capstone lab](../labs/094-postgresql-multi-region-disaster-recovery-simulation-and-acceptance-project-lab.md), [read-only DR preflight SQL](../labs/sql/094-dr-capstone-preflight.sql), [exercise matrix](../labs/dr/094-dr-acceptance-exercise-matrix.csv), [incident evidence template](../labs/dr/094-dr-capstone-evidence-template.md), and [acceptance scorecard](../labs/acceptance/094-dr-capstone-scorecard.csv).

**PASS:** all mandatory safety and recovery gates met with real evidence and independent signoff. **CONDITIONAL:** noncritical gaps have approved owners and dates but no false PASS. **FAIL:** fencing, single-writer, data integrity, RPO/RTO or recoverability gates missed. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/high-availability.html
- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/app-pgrewind.html

**Next:** Chapter 095 — PostgreSQL Enterprise Reliability and Operational Readiness Review.
