# Chapter 089 — Cloud Cost Governance, Rightsizing and FinOps Acceptance Lab

**PostgreSQL 18 · Read-only production telemetry permitted with approval · Runtime pending**

## 1. Preconditions

Use a disposable PostgreSQL 18 lab for performance tests and approved read-only telemetry for existing production capacity. Obtain a redacted cloud billing export with region, currency, discounts and usage period. Do not modify production compute, storage, replicas, backups or retention during this exercise.

## 2. Baseline inventory

Run [089 capacity preflight SQL](../labs/sql/089-finops-capacity-preflight.sql) and capture timestamp, statistics reset and cluster role. Collect 30–90 days of host CPU, memory, disk latency/IOPS, peak TPS, application p95/p99, replication lag, backup and WAL metrics where available. Mark missing external data NOT VERIFIED.

## 3. Model three candidates

Populate [089 scenario model](../labs/finops/089-rightsizing-scenario-model.csv) for baseline, smaller compute, storage tier change and retention/index optimization. Use real prices when authorized; otherwise clearly label values as hypothetical. Include HA standby, snapshots, archive/WAL, monitoring, network and one-time migration costs.

## 4. Workload validation

Use the Chapter 087 controlled `pgbench` lab or a validated application replay in disposable staging. Compare candidate and baseline at the same dataset and load. Capture latency, throughput, errors, CPU, memory, I/O and replication. Do not infer production readiness from synthetic-only tests.

## 5. Storage and recovery checks

Apply Chapter 088 growth forecasting. Model 3/6/12-month used storage, WAL growth during consumer outage, maintenance scratch, archive retention and restore costs. Require explicit recovery approval before proposing any backup/replica change.

## 6. Decision memo

Complete [089 decision memo](../labs/acceptance/089-finops-decision-memo.md): economics, uncertainty, peak headroom, HA/DR, security, change window, rollback and decision. Reject scenarios that fail mandatory reliability gates regardless of cost savings.

## 7. Post-change verification tabletop

Define an observation window and one complete billing-cycle reconciliation. Document how to compare actual invoiced savings against modeled savings and how to rollback if p99, error budget, replication or RPO/RTO regresses.

## 8. Acceptance

Complete [089 scorecard](../labs/acceptance/089-finops-acceptance-scorecard.csv). Do not mark actual savings PASS until measured billing evidence exists. Record NOT VERIFIED for unexecuted production change or resilience tests.

**Runtime:** pending.
