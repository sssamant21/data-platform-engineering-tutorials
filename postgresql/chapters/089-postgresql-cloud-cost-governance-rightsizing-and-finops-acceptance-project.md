# Chapter 089 — PostgreSQL Cloud Cost Governance, Rightsizing and FinOps Acceptance Project

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Deliver an auditable PostgreSQL FinOps decision integrating [Chapter 086 — Capacity and Cost Forecasting](086-postgresql-capacity-forecasting-cost-optimization-and-finops.md), [Chapter 087 — Performance Baselines and Stress Testing](087-postgresql-workload-forecasting-performance-baselines-and-capacity-stress-testing.md) and [Chapter 088 — Storage Retention](088-postgresql-storage-growth-retention-and-lifecycle-optimization.md).

**Acceptance rule:** a cheaper option is rejected if it violates approved application SLOs, HA capacity, RPO/RTO, security, or recoverability.

## 2. Operating model and ownership

FinOps governance requires shared accountability among DBRE, SRE, application engineering, platform/cloud engineering, finance, security and data governance.

| Role | Responsibility | Evidence |
|---|---|---|
| DBRE | Query workload, database capacity, replication, storage | SQL baseline, sizing assessment |
| SRE | SLOs, error budget, incident risk, change and rollback | Dashboard, acceptance record |
| Cloud/platform | Instance/storage tiers, provider limits, IaC | Terraform plan, pricing inputs |
| Finance/FinOps | Cost allocation, savings validation, unit economics | Billing export, allocation |
| Application owner | Demand forecast, smoke tests, traffic growth | Load test and approval |
| Data governance | Retention, holds, recovery obligations | Policy and retention signoff |

Assign an owner for each cost driver and ensure tags/labels map resources to environment, service, owner, business unit and cost center. Never publish sensitive account identifiers in public Git repositories.

## 3. Cost inventory and allocation

Capture current billing by resource and month:

- Primary and standby compute hours, instance class, pricing model, reserved/committed utilization.
- Provisioned storage GiB-month, IOPS/throughput charges, burst credits and autoscaling limits.
- Snapshots, backups, archived WAL, cross-region copies and restore/test storage.
- Network egress, cross-AZ/region replication, monitoring, logs, support and licensing.
- Idle nonproduction resources, orphaned snapshots and unused provisioned capacity.

Cloud prices vary by provider, region, billing model, tier and contract. **Do not invent prices**; record actual provider billing source, date, currency, effective discounts and tax treatment.

## 4. Baseline and workload capacity

Measure 30–90 days of usage when available, including peaks and seasonal events. Correlate business throughput with CPU, memory, cache, connection pools, p95/p99 latency, disk IOPS/latency, WAL bytes, replication lag, backup time and disk headroom.

Use `pg_stat_database`, `pg_stat_wal`, `pg_stat_user_tables` and `pg_stat_replication` as database inputs; obtain host metrics and billing externally. Use timestamped deltas and account for statistics resets.

```text
Cost per 1M successful transactions =
 (fully allocated monthly PostgreSQL operating cost /
  successful monthly business transactions) × 1,000,000
```

Use consistent scope and time windows; exclude failed/retried transactions from the successful transaction denominator and document attribution limitations.

## 5. Rightsizing candidates

| Candidate | Potential benefit | Mandatory validation |
|---|---|---|
| Smaller compute class | Lower compute charge | Peak CPU, memory, query p99, pool queue |
| Different storage tier | Lower storage/IOPS bill | Latency, throughput, WAL/checkpoint bursts |
| Index/retention optimization | Less storage and write amplification | Query plans, legal hold, backup restore |
| Pooling / workload scheduling | Higher useful concurrency | Pool wait, transaction semantics, batch SLO |
| Reserved/committed spend | Better effective unit price | Utilization forecast, contract lock-in |
| Nonprod scheduling | Lower idle compute | Startup readiness, dependencies, exceptions |
| Replica topology change | Potential cost reduction | HA/RPO/RTO; usually higher risk |

Do not propose deleting production replicas, weakening backup retention, disabling audit/security controls or dropping replication slots purely for cost savings without a separately approved risk decision.

## 6. Scenario economics

For each candidate calculate:

```text
Baseline monthly TCO = compute + storage + IOPS/throughput
                     + backups/WAL + network + monitoring/support
Candidate monthly TCO = same cost categories under candidate
Gross monthly savings = baseline TCO - candidate TCO
Net first-year benefit = 12 × gross monthly savings
                       - migration cost - incremental operating cost
Simple payback months = one-time migration cost / gross monthly savings
                        (only when gross monthly savings > 0)
```

Treat discounts, reservations, amortization, one-time engineering cost and uncertainty explicitly. A storage tier change can shift spend between GiB and provisioned IOPS; compare the **full bill**.

## 7. Reliability gates

**Gate A — Performance:** representative peak and burst load passes p95/p99, throughput, error and timeout thresholds.

**Gate B — HA/DR:** surviving nodes can absorb load; replication lag, archive, backup and tested restore meet RPO/RTO.

**Gate C — Storage:** growth and maintenance scratch space fit within disk headroom and scaling lead time; WAL/slots cannot exhaust disk under credible outage scenarios.

**Gate D — Operations:** monitoring, alerting, on-call runbook, rollback and IaC state are complete.

**Gate E — Governance:** cost allocation, security, retention, approvals and finance assumptions are recorded.

A single-node `pgbench` pass is insufficient for production HA acceptance.

## 8. Rollout and rollback

1. Collect baseline metrics, invoices, IaC state and business forecast.
2. Model low/base/high scenarios and compare options at identical workload.
3. Test on staging with representative data, peak load and maintenance overlap.
4. Review change window, failover/fencing, backup and rollback.
5. Deploy one change at a time through approved IaC/provider controls.
6. Verify application SLOs, replica catch-up, WAL/backup health and actual bill.
7. If a gate fails, revert through the authoritative controller or invoke documented recovery.
8. Reconcile forecast versus actual cost after a complete billing cycle.

Some cloud volume downgrades or instance migrations require replacement/copy, not in-place rollback. Document the actual provider limitation and data synchronization boundary.

## 9. Anti-patterns and incident risks

- Downsizing from average CPU alone: ignores burst and memory/cache pressure.
- Counting logical VACUUM free space as a reduction in cloud provisioned storage: charges may not change.
- Ignoring WAL archive/slots: disk fills during CDC or standby outage.
- Removing indexes based only on low scan counts: statistics reset and seasonal queries can mislead.
- Reducing backups or replicas without recovery testing: hidden RPO/RTO failure.
- Comparing costs across different SLO or workload conditions: invalid savings estimate.
- Treating a cost spreadsheet as evidence of achieved savings: actual invoices must confirm.

## 10. Lab and acceptance

Use [089 FinOps capstone lab](../labs/089-postgresql-cloud-cost-governance-rightsizing-and-finops-acceptance-project-lab.md), [read-only SQL](../labs/sql/089-finops-capacity-preflight.sql), [scenario model](../labs/finops/089-rightsizing-scenario-model.csv), [acceptance scorecard](../labs/acceptance/089-finops-acceptance-scorecard.csv), and [decision memo template](../labs/acceptance/089-finops-decision-memo.md).

**PASS requires:** documented billing inputs, reproducible scenario calculations, peak-load validation, HA/DR acceptance, storage/WAL headroom, approved change/rollback, independent signoff and post-billing savings verification. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/pgbench.html
- https://www.postgresql.org/docs/18/diskusage.html
- https://www.postgresql.org/docs/18/warm-standby.html
- https://www.postgresql.org/docs/18/routine-vacuuming.html

**Next:** Chapter 090 — PostgreSQL Multi-Region Architecture, Geo-Replication and Disaster Recovery Design.
