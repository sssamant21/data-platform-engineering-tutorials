# Chapter 099 — Enterprise Reliability Engineering and Operational Acceptance Lab

**PostgreSQL 18 · Read-only preflight and controlled test environment · Runtime pending**

## 1. Scope and roles

Identify service, environment, application, PostgreSQL version, topology, SLO, RPO/RTO, owners, reviewers and approved test window. Use a disposable cluster for fault injection. Never perform destructive recovery exercises against production without a separate approved change.

## 2. Baseline

Run [099 preflight SQL](../labs/sql/099-enterprise-reliability-preflight.sql). Capture application p95/p99, error rate, throughput, cloud/host CPU and disk IOPS, pooler connections, WAL, backup age and restore-test evidence.

## 3. Execute approved tests

Populate [099 scenario matrix](../labs/acceptance/099-reliability-test-matrix.csv). Run representative load, HA fencing/failover, isolated PITR restore, alert routing, incident response and Chapter 098 read-only collector negative tests. Tabletop-only scenarios must be marked as such.

## 4. Validate safety

Verify one authoritative writer, durable transaction markers, application recovery, no duplicate/missing business transactions, backup continuity and data access controls. Do not claim RPO/RTO if not measured.

## 5. Score and remediate

Complete [099 scorecard](../labs/acceptance/099-enterprise-reliability-scorecard.csv) with evidence and reviewer. Enter each failed or unknown control in [099 remediation register](../labs/acceptance/099-reliability-remediation-register.csv).

## 6. Decide and hand off

Complete [099 decision memo](../labs/acceptance/099-operational-acceptance-decision.md). GO requires all mandatory gates PASS; conditional approval is restricted to noncritical gaps. Schedule ongoing reliability checks and independent re-review.

**Runtime:** pending.
