# Chapter 098 — Reliability Automation and Continuous Validation Lab

**PostgreSQL 18 · Windows PowerShell + psql · Runtime pending**

## 1. Preflight

Use an approved disposable PostgreSQL 18 instance or a read-only monitoring target. Confirm `psql --version`, connectivity, least-privilege monitoring identity and output directory access. Never put passwords in scripts or GitHub.

## 2. Collect baseline

Run [098 SQL](../labs/sql/098-reliability-validation.sql) manually first. Capture server version, role, UTC time, database counters, replication, WAL archive, slots, autovacuum and settings. Supplement with host and application metrics.

## 3. Run PowerShell collector

```powershell
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
$env:PGDATABASE = "postgres"
$env:PGUSER = "monitor"
.\postgresql\labs\scripts\098-run-reliability-validation.ps1 -SqlPath ".\postgresql\labs\sql\098-reliability-validation.sql" -OutputDirectory ".\evidence\pg098"
```

Credentials must be supplied through approved secret handling. Review output and exit status; this script collects evidence and does not change PostgreSQL state.

## 4. Failure injection

In a disposable environment only, test missing `psql`, invalid SQL path, unreachable host and expired/invalid monitoring credentials. Each must return nonzero and must not be treated as a healthy result.

## 5. Scheduling and governance

Populate [098 schedule](../labs/automation/098-reliability-validation-schedule.csv) with control owner, frequency, runbook, alert and evidence retention. Keep destructive restore/failover exercises in separately approved workflows.

## 6. Acceptance

Complete [098 scorecard](../labs/acceptance/098-reliability-automation-scorecard.csv). A successful SQL collector run does not certify backup recoverability, HA or production readiness.

**Runtime:** pending.
