# Chapter 090 — Multi-Region Architecture, Geo-Replication and DR Design Lab

**PostgreSQL 18 · Disposable two-cluster simulation or tabletop · Runtime pending**

## 1. Safety

Do not promote, fence or reconfigure a production PostgreSQL instance for this lab. Use isolated disposable primary/standby clusters, or complete a documented tabletop if infrastructure is unavailable. Avoid presenting two containers on one host as a genuine regional fault-isolation test.

## 2. Define recovery objectives

Specify target RPO, RTO, acceptable write downtime, source-region outage assumptions, application routing method, approval roles, backup retention and disaster declaration criteria. Identify source and DR failure domains and independent dependencies.

## 3. Architecture review

Complete [090 architecture matrix](../labs/dr/090-multi-region-architecture-matrix.csv) for physical async, physical sync, logical replication and backup/PITR options. Include latency, data loss, recovery time, cost, operational complexity and provider support.

## 4. Build or inspect disposable replication

For self-managed test instances, initialize a standby from a consistent base backup, configure replication TLS and access, and verify streaming. Run [090 inspection SQL](../labs/sql/090-geo-replication-inspect.sql) on each node; standby-only and primary-only queries are separated by role. Capture primary/standby LSNs, WAL slots, archiving, lag and UTC time.

## 5. Model regional disconnection

Use a controlled test-network isolation only in the disposable lab. Observe WAL backlog, slot growth, archive behavior and recovery after reconnection. Quantify backlog bytes and estimate RPO. Never assume replay timestamp difference on an idle primary equals true replication delay.

## 6. Promotion and fencing tabletop

Follow [090 regional failover runbook](../labs/dr/090-regional-failover-runbook.md). Before promotion, require independent evidence that the original primary cannot accept writes. If fencing is not demonstrable, **STOP** and mark the failover gate NOT VERIFIED. A tabletop cannot prove fencing effectiveness.

## 7. Failback planning

Document how to preserve the old primary for investigation, identify timeline divergence, reseed/rewind only when supported, reestablish a standby and perform a controlled switchover. Verify backup protection in the new active region.

## 8. Acceptance

Complete [090 scorecard](../labs/acceptance/090-multi-region-dr-scorecard.csv). Record measured promotion time, RPO evidence, application smoke tests, single-writer proof, routing and backup restore evidence. Mark regional isolation and live fencing NOT VERIFIED if not exercised.

**Runtime:** pending.
