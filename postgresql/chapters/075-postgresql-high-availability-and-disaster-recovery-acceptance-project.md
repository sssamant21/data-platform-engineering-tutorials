# Chapter 075 — PostgreSQL High Availability and Disaster Recovery Acceptance Project

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; acceptance execution pending

## 1. Capstone mission

Prove, with reproducible evidence, that a PostgreSQL service can survive node and availability-zone failures, recover from a regional disaster, safely fail back and restore application service within approved RPO/RTO. Integrate [Chapter 067](067-postgresql-streaming-replication-and-high-availability-architecture.md) through [Chapter 074](074-postgresql-cross-region-replication-dr-cutover-and-failback.md) plus the [backup/DR capstone in Chapter 066](066-postgresql-backup-and-disaster-recovery-acceptance-lab.md).

**A successful promotion is not an acceptance PASS** without single-writer safety, transaction reconciliation, client routing, recovered redundancy, and independently verified backup/WAL continuity.

## 2. Reference system under test

```text
          Region A — active                     Region B — DR
    AZ A          AZ B          AZ C           independent recovery
  PG primary    PG standby   PG standby      PG standby / PITR restore
  DCS voter     DCS voter    DCS voter       independent backup + WAL
       +-------------+------------+                 |
                 HA manager                          |
                 fencing                             |
                 writer endpoint <--- authorized cutover/failback
                       |
              synthetic application
                       |
       metrics + logs + transaction ledger + incident evidence
```

Use PostgreSQL 18, a supported HA orchestrator (Patroni-style), quorum-backed DCS, independent fencing, a test writer endpoint, verified backups and a restore target. A single-host simulation **cannot** validate physical AZ or region independence. Record which claims are simulated versus physically exercised.

## 3. Scope and ownership

| Role | Responsibility |
|---|---|
| Incident commander | Approve start, stop, DR cutover and failback |
| DBRE lead | Replication, WAL, promotion, rewind/rebuild and consistency |
| Platform/SRE lead | DCS, fencing, infrastructure and routing |
| Application owner | Write freeze, idempotency and client recovery |
| Backup owner | WAL archive, backup validation and PITR |
| Observer / recorder | UTC timeline, evidence and scorecard |
| Change approver | RPO/RTO and durability/availability tradeoffs |

Require explicit approvals for any change to synchronous commit policy, fencing, routing, promotion or regional cutover. Lab-only commands do not authorize production changes.

## 4. Acceptance prerequisites

1. Written service-level objectives: write availability, RPO, RTO, acceptable replication lag and backup retention.
2. Topology and shared-dependency inventory: nodes, AZs, regions, DCS voters, network, disks, DNS, IAM and secrets.
3. Verified single-leader control: leader lease/quorum, independent fencing and fail-closed routing.
4. WAL retention capacity model: replication slots, archive and time-to-disk-exhaustion.
5. Verified backup and PITR restore in an isolated environment.
6. Application probe with unique transaction IDs, timestamped commit acknowledgments and read-back verification.
7. Monitoring/alerts for DCS quorum, leader state, WAL lag, blocked synchronous commits, archive failures, endpoint routing and app errors.
8. Dedicated test infrastructure, rollback and emergency STOP plan.

If a prerequisite is absent, mark the dependent acceptance gates **BLOCKED / NOT VERIFIED**, never PASS.

## 5. Execution phases

### Phase A — Baseline and observability

Record PostgreSQL role and WAL LSNs on every node, DCS quorum and leader, fencing status, proxy backend, replication mode, slot status, WAL archive and backup freshness. Establish application write success rate and latency percentiles. Run [075 read-only SQL](../labs/sql/075-ha-dr-acceptance-inspect.sql) on each PostgreSQL node.

### Phase B — Durability and standby failure

Test `synchronous_commit` policy and standby eligibility. Simulate a standby failure in the disposable lab. Observe write latency, `SyncRep` waits, fallback policy, WAL retained and recovery time. Verify that no durability policy silently changes.

### Phase C — Planned switchover

Freeze writes; verify standby catch-up to the recorded recovery point; perform an orchestrator-controlled switchover. Prove the former primary is fenced/demoted before new writes. Verify new timeline, one writable leader, writer routing, application marker and safe rejoin.

### Phase D — Unplanned primary failure

Induce an isolated primary failure. Capture detection, DCS quorum, fencing, candidate eligibility, promotion, routing, first successful application write and restoration of standby redundancy. Quantify achieved RPO/RTO and reconcile uncertain COMMITs.

### Phase E — AZ and coordination failures

Simulate loss of a standby AZ, primary AZ and one DCS voter. Verify surviving quorum, correct promotion policy and no dual writer. Separately simulate DCS quorum loss and a partition **only if independently verifiable fencing is available**. Safe behavior may be write unavailability.

### Phase F — Regional DR cutover

Demonstrate that Region A cannot accept writes before Region B promotion. Record last durable/replayed WAL and accepted potential data loss. Promote exactly one DR writer, change endpoint, reconcile transactions, verify application SLOs, backup/archive continuity and regional recovery time.

### Phase G — Controlled failback

Keep former Region A primary fenced. Rebuild/rewind it from the Region B leader only after validating timeline and `pg_rewind` prerequisites. Catch up Region A as standby; perform a separate approved switchover with write drain and fencing. Restore original routing, replica redundancy and backup/WAL protection.

### Phase H — Independent PITR and closure

Restore a **copy** of a verified backup with WAL into an isolated target. Validate transaction markers and recovery timestamp, inspect archive continuity, and document backup age. Confirm no active lab failure injection remains.

## 6. RPO/RTO and evidence method

- **RTO:** measure from agreed incident start until the application can reliably complete a verified write/read through the authorized endpoint. Record promotion time and endpoint update time separately.
- **RPO:** compare last acknowledged application transaction ID/time before failure with the last transaction verified after recovery. Account for asynchronous replication, unknown commit outcomes and reconciliation.
- **Data correctness:** reconcile missing, duplicate and uncertain transaction IDs using an immutable lab transaction ledger; do not equate WAL byte lag with lost transactions.
- **Durability:** record which acknowledgments were local, remote_write, remote flush or remote apply.
- **Safety:** capture independent fencing evidence, DCS leader/term, role and proxy backend at every transition.

Use [075 scorecard](../labs/acceptance/075-ha-dr-acceptance-scorecard.csv) and [075 evidence template](../labs/acceptance/075-ha-dr-evidence-template.md). A passing RTO without single-writer safety is a **FAIL**.

## 7. Incident stop conditions

Immediately halt promotion/cutover when: old-primary fencing is unproven; two nodes appear writable; DCS leader identity conflicts; standby candidate exceeds approved RPO; required WAL/backup chain is unavailable; or application reconciliation indicates unexplained data divergence. Preserve evidence, isolate writes and escalate.

## 8. Acceptance decision

| Gate | Required result |
|---|---|
| Single writer | Exactly one authoritative writable primary in all tested phases |
| Quorum and fencing | Independent proof of safe leader election and old-writer isolation |
| HA switchover/failover | Orchestrated cutover with correct application routing |
| Zone resilience | Survives one AZ failure where topology claims tolerance |
| Regional DR | Cutover meets approved RPO/RTO, including app verification |
| Failback | Rejoined former region as standby before controlled switch |
| Transaction correctness | All acknowledged and uncertain transactions reconciled |
| Backup/PITR | Independent restore with WAL continuity verified |
| Observability | Critical alerts fired, routed and cleared |
| Operational recovery | Replica redundancy, slots, archive and backups healthy |

**PASS** only when all mandatory gates have measured evidence and responsible owner signoff. **FAIL** for any safety violation. **NOT VERIFIED** for unexecuted, simulated-only or unsupported controls. This chapter is **authored and published, not runtime accepted**.

## 9. Deliverables

- [Complete Chapter 075 execution lab](../labs/075-postgresql-high-availability-and-disaster-recovery-acceptance-project-lab.md)
- [Read-only HA/DR inspection SQL](../labs/sql/075-ha-dr-acceptance-inspect.sql)
- [Acceptance scorecard CSV](../labs/acceptance/075-ha-dr-acceptance-scorecard.csv)
- [Evidence and signoff template](../labs/acceptance/075-ha-dr-evidence-template.md)

## References

- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/app-pgrewind.html
- https://patroni.readthedocs.io/
- https://etcd.io/docs/

**Next:** Chapter 076 — PostgreSQL Security Architecture, Roles and Privileges.
