# Chapter 091 — Cross-Region Failover, Fencing and Split-Brain Prevention Lab

**PostgreSQL 18 · Isolated disposable environment · Runtime pending**

## 1. Lab topology and safety

Prepare two isolated PostgreSQL 18 instances with physical streaming replication, a test application and a separate controller/fencing simulation. Use a disposable environment only. Two containers on one host can rehearse logic but **cannot** prove regional failure isolation. Never issue promotion or fencing commands against production for this exercise.

## 2. Baseline

Run [091 preflight SQL](../labs/sql/091-failover-fencing-preflight.sql) on each node. Capture role, server identity, replication positions, slots, archive health, configuration and UTC time. Record test transaction IDs on the current writer and verify their visibility on the standby.

## 3. Failure scenarios

Complete [091 failure matrix](../labs/dr/091-failover-failure-matrix.csv). At minimum rehearse:
- Clean primary stop: controlled fencing verified; eligible standby may be promoted.
- Network partition: original writer status uncertain; **STOP**.
- Stalled standby: assess WAL backlog and RPO; reject if beyond approval.
- Fencing failure: **STOP**, even if primary is unreachable.
- Stale application pool: route remains blocked until verified.
- Old primary returns: quarantine, no writes, rebuild/rejoin as standby.

## 4. Controlled failover tabletop

Follow [091 runbook](../labs/dr/091-single-writer-failover-runbook.md). Only in an approved isolated setup, execute the provider/HA promotion after proving the old writer is fenced. Measure detection, fencing, promotion, routing and application recovery durations.

## 5. Validate the safety invariant

Confirm only the promoted instance can accept writes. Test application and direct connection paths, privileged bypass routes and pooler caches. Record a new unique transaction on the promoted writer; verify the former primary cannot independently accept an authoritative write.

## 6. Rejoin and failback

Preserve the old primary, inspect timeline divergence and choose a supported rewind or fresh base backup. Rejoin as a standby; do not enable old-primary writes. Plan a separate approved switchover only after replication catches up.

## 7. Acceptance

Complete [091 scorecard](../labs/acceptance/091-failover-fencing-scorecard.csv). A tabletop alone is NOT VERIFIED for actual fencing and single-writer enforcement.

**Runtime:** pending.
