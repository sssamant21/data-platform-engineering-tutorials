# Chapter 059 — PostgreSQL Connection Pool Monitoring, Capacity and Alerting

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 and versioned PgBouncer · **Status:** Authored; runtime validation pending

## 1. Mission

Build actionable, low-noise observability for PostgreSQL connections, PgBouncer queues, and application connection acquisition. Translate the incident patterns in [Chapter 058 — Pool Saturation and Recovery](058-postgresql-connection-pool-saturation-timeouts-and-recovery.md) into dashboards, capacity forecasts, alerts, and response runbooks.

## 2. Observe all three layers

```text
Application pool            PgBouncer                     PostgreSQL
active / idle / pending --> cl_active / cl_waiting ----> backends / max_connections
acquisition p95/p99          sv_active / sv_idle           long transactions / waits
timeouts / retries           queue wait / errors          connection failures / CPU / I/O
```

A database can have free connection slots while requests wait at an undersized application pool or a PgBouncer per-user pool. Conversely, a pooler can show low queue depth while direct clients exhaust PostgreSQL slots. Collect correlated timestamps and endpoint labels.

## 3. SLIs and operational signals

| Signal | Definition | Why it matters |
|---|---|---|
| PostgreSQL backend utilization | Client backends / approved application backend budget | Detect headroom loss |
| PgBouncer waiting clients | `cl_waiting` by pool | Immediate queue pressure |
| PgBouncer queue age | Longest waiting client, where exported | User-visible latency risk |
| PgBouncer server utilization | Active server connections / allowed pool capacity | Distinguish idle vs saturated |
| Application acquisition latency | p50/p95/p99 time to acquire connection | Detect upstream pool bottleneck |
| Connection errors | Failed logins, connection limits, TCP/TLS errors | Availability and security |
| Long transaction count | Transactions older than workload threshold | Backends held unnecessarily |
| Connection churn | New connections/sec and disconnects/sec | Reconnect storms and overhead |
| Pooler scrape health | Exporter success / last successful scrape | Detect telemetry gaps |

**Avoid naive utilization denominators.** PostgreSQL's `max_connections` includes reserved capacity and is not the usable application budget. PgBouncer has multiple pools per database/user and potentially multiple instances. Capture the effective limits used for each calculation.

## 4. Read-only PostgreSQL inspection

```sql
SELECT current_setting('max_connections')::int AS max_connections,
       current_setting('superuser_reserved_connections')::int AS superuser_reserved,
       current_setting('reserved_connections')::int AS reserved;

SELECT datname,usename,application_name,state,count(*) AS sessions
FROM pg_stat_activity GROUP BY 1,2,3,4 ORDER BY sessions DESC;

SELECT pid,datname,usename,application_name,state,wait_event_type,wait_event,
       now()-xact_start AS xact_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 20;
```

Use [Chapter 059 SQL](../labs/sql/059-monitoring.sql) for a repeatable baseline. Some details of other users' sessions require monitoring privileges such as `pg_read_all_stats`; do not grant SUPERUSER to exporters.

## 5. PgBouncer administrative signals

Connect to PgBouncer's `pgbouncer` administrative database:

```sql
SHOW VERSION;
SHOW POOLS;
SHOW STATS;
SHOW DATABASES;
SHOW CLIENTS;
SHOW SERVERS;
```

Capture `cl_active`, `cl_waiting`, `sv_active`, `sv_idle`, `sv_used`, per-pool limits, request counts and average timing fields. Exact columns and reset semantics vary by PgBouncer release and exporter. Validate your version before writing production alert expressions.

## 6. Prometheus and Grafana design

Use a PostgreSQL exporter and a compatible PgBouncer exporter with read-only credentials. Collect labels for cluster, environment, database, pooler instance and pool; avoid unbounded per-PID/client labels in time-series metrics.

Recommended dashboard rows:
1. **Customer impact:** connection-acquisition p95/p99, request latency, timeouts, errors.
2. **PgBouncer pressure:** waiting clients, longest wait, active/idle server connections, pool limits.
3. **PostgreSQL headroom:** backend count, application budget, reserved slots, direct connections.
4. **Root causes:** long transactions, lock waits, CPU, I/O, connection churn.
5. **Telemetry health:** exporter up, scrape age, missing metrics and pooler instance count.

**Illustrative PromQL only** (verify metric names in the installed exporter):

```promql
# Example exporter-specific series; rename to match your deployment.
sum by (cluster, database) (pgbouncer_pools_cl_waiting)

# Avoid alerting on an instantaneous spike; use a sustained range.
max_over_time(pgbouncer_pools_cl_waiting[5m]) > 0
```

A five-minute maximum still fires for a single spike. For sustained pressure, prefer `min_over_time(...[5m]) > 0` or an alert `for: 5m` with suitable sampling and missing-data handling. Choose alert logic based on whether *continuous* waiting or *repeated* waiting is the concern.

## 7. Alert policy (starting hypotheses, not universal thresholds)

| Severity | Example trigger | Required action |
|---|---|---|
| Warning | Backend utilization >75% of application budget for 10 min | Check pool growth, direct clients and forecasts |
| Critical | Backend utilization >90% for 5 min plus errors/queue | Triage active incident; preserve admin access |
| Warning | PgBouncer waiting clients persist for 5 min | Inspect long transactions and pool caps |
| Critical | Waiting age exceeds application SLO or acquisition timeouts rise | Apply recovery runbook |
| Warning | Long transactions exceed workload-specific threshold | Identify owners and blockers |
| Critical | Exporter/collector missing during incident | Restore observability; do not treat missing as healthy |

Tune thresholds using at least several normal peak periods, deployment spikes, maintenance and expected batch jobs. Pair queue alerts with request impact to reduce noise.

## 8. Capacity forecasting

Record daily peak backends, PgBouncer pool counts, replicas, peak active/waiting clients, request concurrency, transaction duration and connection churn. Model growth:

```text
potential_server_backends =
  sum over PgBouncer replicas and active pools of
    (default_pool_size + reserve_pool_size)
  + direct clients + operational clients
```

Account for per-database/user caps and configuration overrides. Compare the potential ceiling against PostgreSQL's approved application budget. Forecast with p95 peak utilization and realistic scaling events; do not extrapolate from averages alone.

## 9. Incident response mapping

- **Waiting rises, PostgreSQL CPU low:** inspect locks, long transactions, pool-specific caps and server connection errors.
- **Waiting rises, PostgreSQL CPU high:** reduce concurrency, pause noncritical jobs, optimize slow queries; increasing pool size may worsen overload.
- **App acquisition timeouts, PgBouncer idle:** inspect app connection leaks, thread starvation and local pool limits.
- **Backend slots near limit, PgBouncer not full:** identify direct clients, additional poolers, deployment replicas and stale sessions.
- **Missing metrics:** verify exporter auth, target discovery, scrape errors and label changes before interpreting dashboards.

Use targeted cancellation/termination only after confirming process ownership and transaction impact. Document before/after metrics and rollback.

## 10. Hands-on acceptance lab

The [Chapter 059 lab](../labs/059-postgresql-connection-pool-monitoring-capacity-and-alerting-lab.md) includes SQL baseline collection, PgBouncer administrative snapshots, dashboard design, sample alert rules, synthetic short-lived queue tests and an alert acceptance worksheet.

**Acceptance:** all three layers observable, capacity denominators correct, alerts distinguish sustained from transient pressure, on-call runbooks actionable and missing telemetry detected. **Runtime:** pending.

## References

- [PostgreSQL monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL connection settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [PgBouncer usage](https://www.pgbouncer.org/usage.html)
- [PgBouncer configuration](https://www.pgbouncer.org/config.html)
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)

**Next:** Chapter 060 — PostgreSQL Connection Pooling and Availability Acceptance Project.
