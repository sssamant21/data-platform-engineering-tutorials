# Chapter 059 — Connection Pool Monitoring, Capacity and Alerting Lab

**PostgreSQL 18 · Versioned PgBouncer · Runtime validation pending**

## 1. Preconditions

Use a disposable PostgreSQL 18 instance, a PgBouncer lab instance, and a Prometheus/Grafana sandbox with compatible exporters. Record exporter metric names, PostgreSQL and PgBouncer versions. Do not expose administrative or metrics endpoints publicly.

## 2. PostgreSQL baseline

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/059-monitoring.sql
```

Record server connection budget, backend counts by application, long transactions and wait events. Use a monitoring role with appropriate least-privilege stats access.

## 3. PgBouncer snapshot

```powershell
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW VERSION;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW POOLS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW STATS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW DATABASES;"
```

Record `cl_waiting`, `sv_active`, `sv_idle`, pool limits and queue timing fields if present.

## 4. Dashboard build

Create panels for application acquisition latency, PgBouncer waiting clients and waiting age, server utilization, PostgreSQL backend count, long transactions, errors and exporter health. Verify every panel's labels, units and denominator. Avoid using a series that is missing as evidence of zero errors.

## 5. Alert rule examples

Use [sample alert rules](../labs/monitoring/059-alerts.example.yml) as a **template**. Metric names and labels are exporter-specific; do not deploy without verifying live series, thresholds, runbook URLs and notification routing.

## 6. Controlled alert acceptance

Generate a small, bounded burst of short transactions in a disposable test database. Observe client wait, PostgreSQL backends and application latency. Test a transient spike (should not page), sustained pressure (should alert) and exporter unavailability (should alert separately). Stop if timeouts or CPU/IO pressure persist.

## 7. Evidence worksheet

| Gate | Evidence | Pass/Fail |
|---|---|---|
| PostgreSQL connection denominator | | |
| PgBouncer pool mapping | | |
| Application acquisition latency | | |
| Transient spike suppressed | | |
| Sustained queue detected | | |
| Missing exporter detected | | |
| Alert routed to on-call | | |
| Recovery metrics return to baseline | | |

**Runtime:** pending.
