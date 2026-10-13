# Chapter 086 — Capacity Forecasting, Cost Optimization and FinOps Lab

**PostgreSQL 18 · Read-only capacity inspection · Runtime pending**

## 1. Scope and safety

Use a disposable PostgreSQL 18 instance or read-only approved production telemetry. This lab does not change production capacity, replication, backups, retention or cloud billing settings. Collect cloud/OS metrics and provider prices through authorized monitoring/billing sources; SQL cannot supply them.

## 2. Capture time-series evidence

Run [086 capacity SQL](../labs/sql/086-capacity-inspect.sql) at two or more known UTC timestamps. Record stats reset times and distinguish cumulative counters from rates. Collect 30–90 days of peak CPU, memory, disk, IOPS, latency, WAL, connections, replication and backup metrics if available. If historical data is unavailable, mark trend gates NOT VERIFIED.

## 3. Storage forecast

Use the starting used TiB, monthly growth and usable capacity to compute linear and compound forecasts for 3/6/12 months. Include 15–30% **scenario** headroom as an assumption, not a universal target. Test high-growth cases for new tenants, bulk imports and index rebuild scratch space.

## 4. WAL and recovery headroom

Measure WAL generation over a known interval using counter deltas or LSN differences, accounting for stats resets and role changes. Estimate slot retention during 1h/4h/24h consumer outages. Check archive/replica health and identify the disk-exhaustion threshold.

## 5. Compute and memory

Compare peak vs sustained CPU, memory, active sessions, pooler queue, temporary file activity and disk read latency. Do not recommend a downsize solely from average CPU utilization.

## 6. FinOps scenarios

Populate [086 cost model](../labs/finops/086-capacity-cost-model.csv) with **real** provider prices and usage, or clearly label illustrative estimates. Compare baseline, compute rightsizing, storage tier change and retention optimization. Include HA replicas, backup/WAL storage, cross-region traffic and one-time migration cost.

## 7. Decision and acceptance

For each option record monthly savings, implementation effort, confidence, risk, application SLO, RPO/RTO, rollback and owner. Complete [086 scorecard](../labs/acceptance/086-capacity-finops-scorecard.csv). Reject any scenario that compromises recovery or cannot demonstrate sufficient peak headroom.

**Runtime:** pending; no live cost or performance claims are validated.
