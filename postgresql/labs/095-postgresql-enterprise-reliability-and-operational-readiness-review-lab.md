# Chapter 095 — Enterprise Reliability and Operational Readiness Review Lab

**PostgreSQL 18 · Read-only diagnostics; independent acceptance · Runtime pending**

## 1. Scope

Select an approved disposable PostgreSQL 18 cluster or an existing environment for read-only inspection. Record cluster, environment, owners, application, SLO, RPO/RTO and review window. No production configuration changes or fault injection are authorized by this lab.

## 2. Collect evidence

Run [095 preflight SQL](../labs/sql/095-enterprise-readiness-preflight.sql). Supplement with cloud/host CPU, memory, disk, IOPS, connection pool metrics, app p95/p99, backup inventory, isolated restore results, IAM/TLS controls, incident history and IaC configuration.

## 3. Review readiness

Populate [095 readiness scorecard](../labs/acceptance/095-enterprise-readiness-scorecard.csv). Every mandatory gate needs evidence, an owner and a reviewer. Mark untested HA, restore or security controls NOT VERIFIED rather than PASS.

## 4. Simulate the ORR meeting

Review capacity pressure, failed backup, replica lag, unbounded WAL slot, certificate expiration, connection exhaustion and regional failure as tabletop scenarios. Identify paging owner, rollback, recovery and customer communication.

## 5. Register risks

For each gap complete [095 risk register](../labs/acceptance/095-enterprise-risk-register.csv), including severity, impact, remediation, deadline, compensating controls and retest.

## 6. Decide

Complete [095 decision record](../labs/acceptance/095-enterprise-readiness-decision-record.md). NO-GO when a mandatory gate fails or lacks evidence. CONDITIONAL GO is only for explicitly approved noncritical risks.

## 7. Acceptance

Obtain independent DBRE, SRE, application and security review. Do not claim production readiness solely from a disposable lab or checklist.

**Runtime:** pending.
