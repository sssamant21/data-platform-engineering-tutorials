# Chapter 098 — PostgreSQL Reliability Automation, Continuous Validation and Operational Excellence

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Build a safe, repeatable PostgreSQL reliability validation system that collects evidence, evaluates acceptance gates, detects drift and triggers human-reviewed remediation. Integrate [Chapter 095 ORR](095-postgresql-enterprise-reliability-and-operational-readiness-review.md), [Chapter 096 incident command](096-postgresql-enterprise-incident-response-escalation-and-operational-command.md) and [Chapter 097 RCA/COA](097-postgresql-production-incident-simulation-root-cause-analysis-and-corrective-actions.md).

**Rule:** automated validation is not automated authority to terminate sessions, fail over, delete backups or change production configuration.

## 2. Reliability control loop

```text
Service inventory -> scheduled evidence collection -> evaluate gates
        ^                                         |
        |                                    PASS / WARN / FAIL / UNKNOWN
        |                                         |
        +---- independent review <- corrective actions <- alert/owner
```

Each control needs an owner, collection frequency, target, evidence location, last verified time and escalation. Treat missing metrics as UNKNOWN rather than PASS.

## 3. Continuous validation domains

| Domain | Automated evidence | Human acceptance |
|---|---|---|
| Availability | Role, replication sender/receiver, connection checks | Actual failover and fencing drill |
| Recoverability | Backup age, archive status, restore-job evidence | Verified isolated restore and PITR |
| Performance | p95/p99, pool wait, deadlocks, temp files, I/O | Workload and SLO review |
| Capacity | Storage growth, WAL retention, connections, CPU, IOPS | Forecast and headroom decision |
| Configuration | Approved baseline versus observed settings | Change approval and drift resolution |
| Security | TLS, role/privilege inventory, patch version | Access review, secret rotation, compliance |
| Data integrity | Reconciliation and anomaly tests | Business owner validation |
| Operations | Alert paging, runbook links, incident COAs | Drill and independent signoff |

## 4. Automation design principles

- **Read-only by default:** SQL uses catalog/statistics views and no mutation.
- **Least privilege:** monitoring identity has only necessary permissions; use approved `pg_monitor` where required.
- **Timeouts:** `PGOPTIONS` sets statement and lock timeouts before connecting; automation has bounded execution.
- **Idempotency:** reruns create new timestamped evidence, not conflicting database changes.
- **Separation:** evidence collector cannot approve or execute production failover.
- **Failure transparency:** nonzero exit, missing output, stale evidence and authentication errors are FAIL/UNKNOWN, never silent success.
- **Data minimization:** do not store query literals, secrets, connection strings or PII in published artifacts.
- **Environment allowlist:** explicitly specify target database; production runs require existing authorization.
- **Retention:** store evidence securely with audit controls and expiry policy.

## 5. Read-only SQL controls

Run [098 reliability validation SQL](../labs/sql/098-reliability-validation.sql) against PostgreSQL 18. It samples database health, activity, autovacuum, replication, slots and archive. Interpret counters using `stats_reset` and multiple time samples; a single snapshot cannot establish rates or SLO compliance.

Not all metrics are available from SQL. Integrate application telemetry, cloud host metrics, backup/restore tool logs, IAM/KMS probes and independent regional monitoring.

## 6. PowerShell evidence runner

Use [098 PowerShell runner](../labs/scripts/098-run-reliability-validation.ps1) on Windows/PowerShell with `psql` on PATH. It requires explicit target connection, validates prerequisites, applies connection/statement timeouts, executes read-only SQL and writes timestamped evidence with exit code. Credentials should come from approved environment/secret manager or `pgpass`; never embed passwords in scripts.

Example:

```powershell
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
$env:PGDATABASE = "postgres"
$env:PGUSER = "monitor"
# Provide credentials through approved secret handling.
.\postgresql\labs\scripts\098-run-reliability-validation.ps1 -SqlPath ".\postgresql\labs\sql\098-reliability-validation.sql" -OutputDirectory ".\evidence\pg098"
```

The runner does not evaluate all enterprise readiness gates; it is an evidence collection component, not a certification engine.

## 7. CI/CD and scheduling

Schedule read-only checks at an appropriate frequency with concurrency limits and secrets injected at runtime. Add policy-as-code checks for required evidence files, stale timestamps and reviewer approvals. Keep destructive recovery drills in a separate explicitly approved workflow.

Do not run production restore tests on production databases. Schedule isolated restores, replay tests, application smoke tests and DR drills on independent infrastructure.

## 8. Alerting and reliability reviews

Alert on failed collector runs, archive errors, unhealthy replication, excessive WAL retention, backup age, failed isolated restore and missed acceptance gates. Link each alert to runbook, owner and escalation. Use weekly reviews for trend and drift, monthly reviews for risk closure, and periodic disaster recovery exercises based on policy.

## 9. Continuous improvement

Feed incident and RCA corrective actions into automated checks. For each action capture a regression test, expected outcome, evidence, owner and independent verifier. An action is not closed until the failure mode has been retested and the improvement measured.

## 10. Failure and safety scenarios

- Collector credentials expire: exit nonzero, alert, no false PASS.
- Monitoring server unreachable: evidence marked UNKNOWN, preserve last known timestamp.
- Replication receiver absent: investigate role and topology before escalation.
- Archive failure rises: inspect archive durability and disk headroom; do not delete WAL.
- Backup catalog healthy but restore fails: mark recoverability FAIL.
- Configuration drift appears: open change review; do not auto-restart PostgreSQL.
- Regional partition: no automatic promotion without fencing proof.

## 11. Lab and acceptance

Use [Chapter 098 lab](../labs/098-postgresql-reliability-automation-continuous-validation-and-operational-excellence-lab.md), [SQL checks](../labs/sql/098-reliability-validation.sql), [PowerShell runner](../labs/scripts/098-run-reliability-validation.ps1), [validation schedule](../labs/automation/098-reliability-validation-schedule.csv) and [acceptance scorecard](../labs/acceptance/098-reliability-automation-scorecard.csv).

**PASS:** collector runs safely with evidence, errors fail closed, owners and alerts are defined, restore/DR validation is independently verified, and corrective actions are regression-tested. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/runtime-config-client.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/high-availability.html

**Next:** Chapter 099 — PostgreSQL Enterprise Reliability Engineering and Operational Acceptance Project.
