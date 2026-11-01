# Page 03 — PostgreSQL Monitoring, Alerting & Service-Level Objectives

**Document ID:** PG-DBRE-OPS-003 | **Owner:** DBRE + APP | **Status:** DRAFT — metric mappings and alerts unvalidated  
**Tools:** postgres_exporter, Prometheus, Grafana, application tracing/APM and managed-service cloud monitoring

## 1. Monitoring architecture

PostgreSQL statistics/catalogs + OS/host/cloud metrics + pooler metrics + application telemetry → approved exporters/collectors → Prometheus/Grafana/alerting → DBRE on-call, APP, DATA and PLT. Managed providers supply platform telemetry that may not be visible from SQL.

**Measure user SLOs at the application boundary**. pg_stat_statements total_exec_time/calls is SQL execution average, not request p95/p99. Replication interval columns are not guaranteed per-request data-lag SLOs.

### Exporter compatibility and privacy

Metrics below are illustrative. Current Prometheus Community postgres_exporter source confirms the database transactions, deadlocks, size and activity metric names used below; deployed collector flags, exporter release, labels and monitoring privileges still require actual /metrics verification. Restrict collector impact and metric cardinality. The stat_activity collector may expose username and application name labels: prevent PHI, patient identifiers, credentials and full confidential SQL from appearing in scraped metrics or broadly accessible dashboards.

## 2. Required dashboard suite

| ID | Dashboard | Required panels |
|---|---|---|
| PG-01 | Service & HA overview | Synthetic reachability, role/primary/standby, SLO, on-call incidents |
| PG-02 | Connection and lock health | Sessions by state, pool saturation, xact age, blockers/deadlocks |
| PG-03 | Query performance | APP p95/p99, SQL calls/mean exec, high CPU/IO, top query IDs |
| PG-04 | Replication & WAL | Primary/replica LSN lag, slot retention, archiver, timeline and lag risk |
| PG-05 | Storage & growth | Per database, table, index bytes, disk free, WAL footprint, forecast |
| PG-06 | Vacuum / bloat / wraparound | Dead tuples, last vacuum/analyze, frozen XID and MXID ages |
| PG-07 | Host/IO and cache | CPU, memory, disk IOPS/latency, checkpointer, block reads/cache |
| PG-08 | Backup/PITR & DR | Last successful backup and restore drill, archive gaps, RPO/RTO |
| PG-09 | Security & operations | Auth errors, roles, certificate expiry, maintenance/patch risk |
| PG-10 | Cloud, FinOps & alerts | Instance/IOPS/storage cost, alert quality, node/pooler utilization |

## 3. Example PromQL (verify actual metric names first)

**Distinguish exporter reachability from PostgreSQL reachability.**

Prometheus could not scrape the exporter:

~~~~promql
up{job="postgres-exporter"} == 0
~~~~

Exporter can be reached but reports that its DB connection/scrape failed (verify semantics with deployed version and simulated failure):

~~~~promql
pg_up{job="postgres-exporter"} == 0
~~~~

Exporter target scrapes successfully but the expected database-health metric is missing:

~~~~promql
(up{job="postgres-exporter"} == 1)
unless on (job,instance) pg_up{job="postgres-exporter"}
~~~~

No exporter job targets have been observed for 10 minutes:

~~~~promql
absent_over_time(up{job="postgres-exporter"}[10m])
~~~~

**Limit:** The job-wide absence alert does not detect ONE instance disappearing while others remain. Maintain an independent expected-target inventory/operational service-discovery check. The exporter can also report misleading pg_up values in failure edge cases; require a separate database or application synthetic probe and explicit failure-injection validation.

Database transactions/s (counter reset safe; check labels and scrape consistency):

~~~~promql
sum by (instance,datname) (
  rate(pg_stat_database_xact_commit[5m])
  + rate(pg_stat_database_xact_rollback[5m])
)
~~~~

Deadlocks increase (requires database metric):

~~~~promql
sum by (instance,datname) (increase(pg_stat_database_deadlocks[5m])) > 0
~~~~

Database size — provided by the current default database collector, provided it is enabled and permitted:

~~~~promql
sum by (instance,datname) (pg_database_size_bytes)
~~~~

Active connections (verify column/labels in exporter version):

~~~~promql
sum by (instance,datname) (pg_stat_activity_count{state="active",backend_type="client backend"})
~~~~

The current exporter also defines pg_exporter_last_scrape_error, an independent exporter-side error indicator (confirm behavior in the installed version). Combine it with up, pg_up and application probes rather than using a single metric as proof of availability.

**Replication/slot metrics** vary widely. Prefer validated, version-specific exporter queries or custom SQL with stable identity labels and a corresponding lag/wal-retention SLI; never invent a hard-coded exporter metric name.

**Disk usage** must come from OS/node exporter or cloud monitoring. pg_database_size does not include WAL, free-space headroom or filesystem overhead.

## 4. SLI and SLO framework

| SLI | Definition | Measurement and owner |
|---|---|---|
| Business availability | Eligible successful app operations / eligible attempts | APP instrumentation |
| End-to-end latency | Percent completed within approved time, or p95/p99 | APP APM/histograms |
| DB response | SQL calls, durations, wait, errors, pool wait time | DBRE |
| Data freshness | Source commit/event visible to consuming app in interval | DATA + APP |
| Replication recovery | Confirmed secondary replay watermark / source commit | DBRE + APP |
| Backup RPO | Latest **recoverable** point, not merely backup start | DBRE + DATA |
| DR RTO | Incident start to APP business validation | APP + DBRE |
| Capacity and expense | Forecasted headroom, billed instance/storage/IO costs | DBRE + FIN |

**Candidate targets ONLY:** 99.9% eligible application operation success per rolling 30 days; 95% of interactive reads under 500 ms; business-defined freshness; approved RPO/RTO. These are **not** automatically suitable for every transactional workload.

### Example instrumented application p95

~~~~promql
histogram_quantile(
  0.95,
  sum by (le,service) (
    rate(app_db_operation_duration_seconds_bucket{service="orders-api"}[5m])
  )
)
~~~~

Application histogram is hypothetical; instrument and verify bucket conventions. SQL pg_stat_statements averages must not be substituted for P95.

### Error budget

At 99.9% request success, the allowed unsuccessful proportion is 0.1% of eligible requests over the SLO window. Agree cancellations, retries, transaction aborts and planned maintenance rules. Use fast and slow burn alerting, not only a static service-state page.

## 5. Recommended alert categories

| Signal | Candidate warning | Critical gate | Owner |
|---|---|---|---|
| Primary unresponsive | One confirmed failed synthetic check | Sustained outage / app requests failing | DBRE/PLT |
| Unplanned failover/role change | Unexpected timeline or primary role change | Potential dual writer/unknown leader | DBRE/incident |
| Replica replay lag | Near approved freshness or RPO window | Actual breached objective | DBRE |
| WAL slot retention | Rising retained WAL/low disk runway | Disk full or slot lost risk | DBRE/DATA |
| WAL archive failure | Repeated failed archiving | PITR gap/backups at risk | DBRE/PLT |
| Session connections | Sustained >70–80% of configured safe pool | Pool exhaustion/client errors | DBRE/APP |
| Locks/transaction age | Persistent abnormal blocker | Business critical work blocked | DBRE/APP |
| Deadlock rate | New sustained increases | Widespread transaction failure | DBRE/APP |
| Autovacuum/freeze | Age/dead tuples trending above baseline | Measured wraparound emergency risk | DBRE |
| Storage | Low projected runway | WAL/disk exhaustion risk | DBRE/PLT |
| Query latency | Near approved APP SLO | SLO breach/high burn | APP/DBRE |
| Backup | Missed complete backup or restore test | Proven RPO coverage absent | DBRE |
| Telemetry | Exporter stale or data gaps | Cannot observe production issue | DBRE/PLT |

**No universal XID-age threshold:** assess age(relfrozenxid), multixact age, autovacuum_freeze_max_age, xid consumption, per-table risk and vacuum blockers. A static 200M alert cannot replace expert assessment. Likewise, high connection counts are meaningful only relative to pool behavior and reserved maintenance capacity.

## 6. Additional read-only SQL for data sources

~~~~sql
SELECT pid, datname, usename, state, wait_event_type, wait_event,
       now()-xact_start AS xact_age
FROM pg_stat_activity
WHERE backend_type = 'client backend'
ORDER BY xact_start NULLS LAST LIMIT 100;

SELECT datname, deadlocks, blks_hit, blks_read, stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL;

SELECT slot_name, slot_type, active, restart_lsn
FROM pg_replication_slots;

SELECT archived_count, last_archived_time, failed_count,
       last_failed_time, stats_reset
FROM pg_stat_archiver;

SELECT schemaname, relname, n_dead_tup, last_autovacuum,
       last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 25;
~~~~

Use a dedicated least-privilege exporter identity, not SUPERUSER. The built-in pg_monitor role is broader than pg_read_all_stats because it includes read-all-settings and stat-scan-table monitoring powers. Test pg_read_all_stats first and grant only the additional role privileges truly required for enabled collectors. Do not grant pg_signal_backend, broad write/DDL, file access or replication management to metrics identities. Protect TLS, credentials, Prometheus exporter port 9187, network access and endpoint authorization.

Read-only authorized staging role check:

~~~~sql
SELECT current_user AS monitoring_role, current_database() AS db,
       pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER') AS stats_member,
       pg_has_role(current_user, 'pg_monitor', 'MEMBER') AS monitor_member,
       pg_has_role(current_user, 'pg_signal_backend', 'MEMBER') AS signal_member;
~~~~

A membership check alone is not full privilege certification. Current-query text may be sensitive. pg_stat_io exists in PostgreSQL 16+ and pg_stat_checkpointer in PostgreSQL 17+; gate panels accordingly. Provider-managed services may restrict stats and WAL functions.

## 7. Sample alert rules and staging test plan

A non-deployed YAML alert template is in [V03 example alerts](qa/V03-prometheus-alerts.example.yml). It covers exporter scrape failure, database scrape failure, missing pg_up, job-wide absence, and last-scrape errors. All alerts are warnings pending workload/service-impact assessment, and must be validated with promtool, real exporter labels, synthetic probes and routing before any production use. There is deliberately no automatic failover, write termination or database configuration action.

| Test | Required failure-injection or inspection | Acceptance |
|---|---|---|
| V03-T01 | Exporter unreachable | Prometheus up=0 and routed warning |
| V03-T02 | Database unreachable while exporter up | pg_up/collector behavior and independent probe |
| V03-T03 | pg_up absent but up=1 | Missing-series warning |
| V03-T04 | All exporter targets removed | Whole-job absence warning |
| V03-T05 | One expected target removed, others remain | Independent inventory-based missing-target alarm |
| V03-T06 | Metric collector disabled or privilege denied | Coverage/error alert, diagnosis |
| V03-T07 | Stats counter reset/restart | Sensible rates and alert noise |
| V03-T08 | Sensitive username/app label/SQL | No PHI/secrets distributed; SEC signs off |
| V03-T09 | TLS/credential rotation failure | No secret disclosure; correct alert routing |
| V03-T10 | APP client and backup/replication SLO checks | Independent service evidence, not just exporter health |

## 8. Alert and monitoring validation

- [ ] Prometheus targets include all primaries, replicas and poolers, with topology labels.
- [ ] Exporter health and missing-target detection tested.
- [ ] Deployed metric names, labels, collector flags, HELP/TYPE, counter resets and up versus pg_up behavior verified.
- [ ] App p95/p99 measured from actual client requests.
- [ ] Lag/WAL/backup alerts tied to approved business objectives.
- [ ] Version-specific stats views and cloud metrics tested.
- [ ] Alert routing and runbook links validated in staging.
- [ ] Role grants, metric endpoint access, secret rotation, user/app labels and PHI-safe query capture approved by Security.
- [ ] Run V03-T01–T10 in staging, validate sample alerts with promtool and confirm individual target disappearance detection.
- [ ] On-call ownership and noise/suppression rules approved.

## References
- [PostgreSQL monitoring views](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [pg_stat_statements](https://www.postgresql.org/docs/current/pgstatstatements.html)
- [Prometheus postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
- [Exporter collector source](https://github.com/prometheus-community/postgres_exporter/tree/master/collector)
- [Exporter role guidance](https://github.com/prometheus-community/postgres_exporter/blob/master/docs/database-permissions.md)
- [PostgreSQL predefined roles](https://www.postgresql.org/docs/current/predefined-roles.html)
- [Prometheus alert rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Grafana No Data behavior](https://grafana.com/docs/grafana/latest/alerting/guides/missing-data/)
- [PostgreSQL WAL/replication configuration](https://www.postgresql.org/docs/current/runtime-config-replication.html)
