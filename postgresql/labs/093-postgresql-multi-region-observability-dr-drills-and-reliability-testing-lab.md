# Chapter 093 — Multi-Region Observability, DR Drills and Reliability Testing Lab

**PostgreSQL 18 · Isolated disposable simulation or tabletop · Runtime pending**

## 1. Scope and safety

Use isolated PostgreSQL 18 primary/standby test instances, test application transactions and independent monitoring where available. Never run destructive network isolation or promotion against production without a formal approved DR exercise. A local two-container setup is not proof of multi-region fault isolation.

## 2. Baseline telemetry

Run [093 inspection SQL](../labs/sql/093-multi-region-observability-inspect.sql) on each node. Record node role, UTC sample time, replication sender/receiver state, WAL archive, slots, database activity, disk headroom and backup restore age. Supplement with host, cloud, pooler, application and control-plane metrics.

## 3. Build a DR dashboard

Include: writer authority, application p95/p99/errors, replica receive/replay backlog, WAL archive freshness, retained WAL, backup copy and restore test age, KMS access probe, regional dependencies, and incident timeline. Each signal needs owner and actionable runbook.

## 4. Design drills

Populate [093 drill matrix](../labs/dr/093-dr-drill-matrix.csv). Rehearse tabletop, backup restore, WAN partition, lag, failed archive, lost DR credentials, stale routing, failover and failback in increasing risk order. State which drills are simulation only.

## 5. Execute a controlled drill

Choose one approved isolated scenario. Collect transaction markers and baseline telemetry, inject a bounded fault, follow Chapter 091 fencing and Chapter 092 recovery gates, and record recovery timestamps. **STOP** if fencing cannot be proven.

## 6. Measure and validate

Verify one authoritative writer, application read/write recovery, backup/archive continuity, replica state, recovered transaction markers and measured RPO/RTO. Mark RPO UNKNOWN if source transaction evidence is insufficient.

## 7. Evidence and acceptance

Complete [093 evidence template](../labs/dr/093-dr-drill-evidence-template.md) and [093 scorecard](../labs/acceptance/093-multi-region-reliability-scorecard.csv). Assign owners and due dates to failed gates; retest before signoff.

**Runtime:** pending.
