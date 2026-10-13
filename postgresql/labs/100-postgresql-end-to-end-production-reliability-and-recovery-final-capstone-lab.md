# Chapter 100 — End-to-End Production Reliability and Recovery Final Capstone Lab

**PostgreSQL 18 · Approved isolated environment · Runtime pending**

## 1. Safety and scope

Build a disposable PostgreSQL 18 primary/standby topology, test application, backup/WAL destination and monitoring. A single-host topology is a simulation, not real regional resilience. Obtain change approval before any production-facing exercise. Establish incident commander, DBRE, SRE, application owner and independent observer.

## 2. Define acceptance

Record service SLO, p95/p99, throughput, RPO/RTO, critical transaction markers, backup policy, HA/fencing authority, failure injection scope, abort limits and rollback. Populate [100 exercise matrix](../labs/acceptance/100-final-capstone-exercise-matrix.csv).

## 3. Baseline

Run [100 preflight SQL](../labs/sql/100-final-capstone-preflight.sql) on each database node. Collect application latency/errors, CPU, RAM, storage, IOPS, WAL generation, replication state, slots, archiving, backup status, connection pools and security configuration.

## 4. Recovery proof

Perform an approved isolated backup/PITR restore and verify durable transaction markers. Record exact UTC start/end, restore point, recovered transaction and application smoke test. Reject missing WAL or inaccessible encryption keys.

## 5. Fault and incident command

Inject one bounded fault in the disposable environment: blocking transaction, clean primary stop or replication interruption. Record alert, incident declaration, severity, impact, command roles and diagnostic evidence. If promotion is needed, STOP without independently verified old-writer fencing.

## 6. Mitigation and service acceptance

Execute only the approved scoped recovery. Validate exactly one authoritative writer, business transaction correctness, application read/write, p95/p99 and error rate. Measure RPO/RTO; record UNKNOWN if commit evidence is inadequate.

## 7. Protection and failback

Reestablish replicas, archiving, backups, alerts and operational ownership. Quarantine old writer and rejoin as standby only. Preserve evidence and do not attempt uncontrolled failback.

## 8. RCA and automation

Write a blameless RCA and assign corrective actions. Run Chapter 098 collector and negative tests. Verify fixes by repeat tests in disposable environment.

## 9. Independent review

Complete [100 evidence report](../labs/acceptance/100-final-capstone-evidence-report.md), [100 scorecard](../labs/acceptance/100-final-capstone-scorecard.csv) and [100 graduation decision](../labs/acceptance/100-final-capstone-graduation-decision.md). GO requires all mandatory gates PASS. Missing evidence means NO-GO, not assumed success.

## 10. Cleanup and handoff

Stop synthetic traffic, restore disposable test resources, verify backup/replication protection, archive evidence in approved storage and schedule ongoing reliability drills.

**Runtime:** pending. Content publication does not constitute executed certification.
