# Chapter 074 — Cross-Region Replication, DR Cutover and Failback Lab

**PostgreSQL 18 · Isolated regional simulation · Runtime pending**

## 1. Environment and safety

Use two **disposable** PostgreSQL 18 environments labeled Region A and Region B, each with independent storage, credentials and routing. Region A starts as writer; Region B is a physical standby or a verified backup/PITR recovery target. Have an independently controlled fencing mechanism and a lab-only application writer endpoint. Two containers on one laptop are a logical simulation, **not proof of regional fault tolerance**.

Never promote a DR standby if Region A may still accept writes. Do not run this lab against production.

## 2. Baseline and inventory

Run [074-cross-region-dr-inspect.sql](../labs/sql/074-cross-region-dr-inspect.sql) against both nodes, capturing node identity and UTC time. Record current leader, WAN path, replication slot owner, WAL receive/flush/replay LSN, backup age, archive health, writer endpoint and RPO/RTO targets.

## 3. Seed a DR marker

Create a disposable database/table on Region A, insert uniquely identified rows and commit. Wait until Region B has replayed the corresponding WAL; verify marker visibility on Region B. Measure delay with application timestamps and LSN evidence, not only last replay timestamp.

## 4. Bounded network degradation

In the isolated lab, interrupt only the replication path briefly. Observe Region B receive/replay progress, Region A retained WAL, slot status, archive continuity and time-to-exhaustion. Restore connectivity before disk pressure. Confirm catch-up.

## 5. DR cutover rehearsal

1. Freeze application writes and record final Region A commit marker and flush LSN.
2. Independently **fence Region A** so it cannot accept writes. If fencing cannot be proven, stop the exercise and mark NOT VERIFIED.
3. Confirm Region B has received/replayed the agreed recovery point; document any gap and obtain test approval.
4. Promote Region B through the HA manager's supported procedure, record timeline and role.
5. Route the lab writer endpoint to Region B, drain stale connections and verify a unique post-cutover transaction.
6. Confirm Region A remains fenced and that only Region B accepts writes.

## 6. Failback rehearsal

Keep Region A stopped/fenced. Verify pg_rewind prerequisites or rebuild it from a verified Region B backup. Start Region A as a standby of Region B and confirm WAL catch-up. Schedule a separate planned switchover: drain writes, verify LSN convergence, fence Region B as old leader, promote Region A through the HA manager, switch routing and validate transaction IDs. Reestablish standby and backup/archiving protection.

## 7. Regional DR recoverability

Restore a **copy** of a Region B backup in an isolated target. Verify backup manifest/restore, archived WAL continuity, application marker and key/credential access. Do not confuse streaming catch-up with backup recoverability.

## 8. Acceptance

Complete [074 DR scorecard](../labs/acceptance/074-cross-region-dr-scorecard.csv). Record incident start, fencing, promotion, routing, first successful app write, redundancy restoration and achieved RPO/RTO. Mark simulated or unexecuted gates NOT VERIFIED rather than PASS.

**Runtime:** pending.
