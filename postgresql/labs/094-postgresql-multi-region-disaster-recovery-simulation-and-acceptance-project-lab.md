# Chapter 094 — Multi-Region Disaster Recovery Simulation and Acceptance Lab

**PostgreSQL 18 · Disposable simulation or approved DR exercise · Runtime pending**

## 1. Safety and environment

Use two isolated PostgreSQL 18 clusters with primary/standby replication, a test application, separate backup storage and an independent observer. A single-host setup proves workflow only, not regional isolation. Never inject faults or promote production systems without explicit change approval and demonstrated fencing.

## 2. Preflight

Run [094 read-only SQL](../labs/sql/094-dr-capstone-preflight.sql) on both nodes. Record roles, UTC time, WAL send/receive/replay, slots, archive, database size, transaction markers, backup generation, DR capacity and application baseline.

## 3. Define acceptance

Agree on RPO, RTO, p95/p99 latency, error rate, peak workload, writer uniqueness, recovery-chain integrity, alerting and signoff owners. Populate [094 exercise matrix](../labs/dr/094-dr-acceptance-exercise-matrix.csv) before any fault injection.

## 4. Simulate failure

Select one bounded scenario: clean primary stop, inter-region partition, lagged standby, WAL archive gap, DR credential outage, stale app routing or old-primary return. Record exact fault and UTC time. For ambiguous fencing, demonstrate the required **STOP** behavior.

## 5. Recovery

Use Chapter 091 fencing runbook. After independent fencing, promote the eligible standby through the supported controller; if unavailable, perform a Chapter 092 isolated backup/PITR restore. Do not connect a recovered candidate to authoritative writes without approval.

## 6. Validate application

Test unique committed markers, business invariants, reads, writes, connection pool routing, p95/p99, error rate, replica/WAL/archive, backup and security. Record measured RPO and RTO or UNKNOWN when not provable.

## 7. Failback and cleanup

Quarantine former primary. Evaluate timeline divergence and supported rewind/reseed; rejoin as standby only. Rebuild backup and monitoring protection. Restore test network state, remove only disposable resources and preserve evidence.

## 8. Acceptance

Complete [094 evidence template](../labs/dr/094-dr-capstone-evidence-template.md) and [094 scorecard](../labs/acceptance/094-dr-capstone-scorecard.csv). Fail any exercise that lacks fencing proof, single-writer validation or actual restore evidence. Mark unexecuted tests NOT VERIFIED.

**Runtime:** pending.
