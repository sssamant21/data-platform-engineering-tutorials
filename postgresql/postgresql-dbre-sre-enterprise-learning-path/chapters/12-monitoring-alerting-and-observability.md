# Chapter 12 — Monitoring, Alerting and Observability

**PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path**  
**Audience:** DBRE/SRE beginners progressing to enterprise operations  
**Target:** PostgreSQL 17, local Docker (primary lab); AWS RDS and Kubernetes comparisons are conceptual/read-only  
**Duration:** 60 minutes | **Status:** Authored; runtime lab and independent review pending

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 12 lab](../labs/chapter-12/README.md) · [Progress](../STATUS-TRACKER.md)

## 1. Outcomes and 60-minute agenda

Learners will distinguish availability from application health, explain core PostgreSQL statistics, collect safe metrics, identify actionable alerts, and design a minimal PostgreSQL dashboard.

| Minutes | Topic | Deliverable |
|---|---|---|
| 00–08 | Signals, SLI/SLO, telemetry pipeline | Signal inventory |
| 08–18 | PostgreSQL built-in statistics | Explain counters and gauges |
| 18–28 | Connections, locks, transactions, WAL, I/O, replication | Triage mapping |
| 28–48 | [Chapter 12 lab](../labs/chapter-12/README.md) | SQL evidence and optional local exporter scrape |
| 48–55 | Prometheus, Grafana and alert design | Dashboard + sample alert rules |
| 55–60 | Review and acceptance | Explain safe escalation |

**Prerequisites:** Chapters 01–11 concepts; Docker Desktop with Linux containers for the lab; PowerShell or an equivalent shell. Do not point this lab at any production instance.

## 2. Architecture: observe the user experience, not just PostgreSQL

```text
Application requests / SLOs
  ├── latency (p50/p95/p99), errors, saturation, request rate
  └── application traces and pool metrics
               |
         PostgreSQL primary / replicas
  ├── pg_stat_activity, pg_stat_database, pg_stat_wal
  ├── pg_stat_io, pg_stat_checkpointer, pg_stat_replication
  └── pg_stat_user_tables, pg_stat_progress_vacuum
               |
        postgres_exporter (read-only monitoring role)
               |
        Prometheus scrapes / stores time series
               |
       Grafana dashboards / alert rules
               |
       Alertmanager or equivalent routing
               |
       On-call DBRE/SRE + app owner + incident record
```

An available database can still deliver unacceptable application latency. Conversely, a single database counter can rise without affecting customer SLOs. Combine application, infrastructure and database evidence before declaring an incident.

### Four signal families

| Signal | Examples | Primary question |
|---|---|---|
| Latency | Application p95/p99, query duration, lock wait | Are customers slow? |
| Traffic | Transactions/sec, queries/sec, connections, throughput | How much work? |
| Errors | Failed requests, rollbacks, deadlocks, failed scrapes | Is work failing? |
| Saturation | Connection utilization, CPU, storage, I/O, WAL retention | Are resources near a limit? |

**SLI** is a measured indicator (for example, successful requests within 300 ms). **SLO** is a target over a period. **Error budget** is the permitted deviation from the SLO. These are application-facing commitments, not a generic 90%-CPU alarm.

## 3. PostgreSQL statistics: counters versus gauges

PostgreSQL 17 has cumulative statistics views and live process views. Many values are counters since the last statistics reset, not "events per second."

- **`pg_stat_activity`:** live sessions, states, wait events, transaction age.
- **`pg_stat_database`:** connection count (`numbackends`), committed/rolled-back transactions, block hits/reads, deadlocks, temporary-file bytes.
- **`pg_stat_wal`:** generated WAL records and bytes; observe **rate of change** to infer workload-driven WAL generation.
- **`pg_stat_io`:** I/O broken down by backend type, object and context; interpret according to version and collection settings.
- **`pg_stat_checkpointer`:** checkpoint count and time, separate from background writer in PostgreSQL 17.
- **`pg_stat_user_tables`:** approximate live/dead tuple counts, scan activity, vacuum/analyze timestamps.
- **`pg_stat_replication`:** connected standbys on a primary, LSNs, state, sync state and lag estimates. Empty on a standalone server is normal.
- **`pg_stat_progress_vacuum`:** live progress only while a vacuum is running.

### SQL examples (read-only)

```sql
-- 1. Verify target identity before interpreting metrics
SELECT current_database(), current_user, pg_is_in_recovery();
SELECT setting::int AS max_connections
FROM pg_settings WHERE name = 'max_connections';

-- 2. Current sessions by state
SELECT COALESCE(state, '<unknown>') AS state, count(*) AS sessions
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY 1 ORDER BY 1;

-- 3. Transaction counters, deadlocks and temporary bytes
SELECT datname, numbackends, xact_commit, xact_rollback,
       deadlocks, temp_bytes, stats_reset
FROM pg_stat_database
WHERE datname = current_database();

-- 4. WAL generation counter (cluster-wide)
SELECT wal_records, wal_bytes, stats_reset FROM pg_stat_wal;

-- 5. Approximate table health
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       last_autovacuum, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 10;
```

Do not subtract counters across a reset without detecting the changed `stats_reset` timestamp. PostgreSQL statistics can be delayed, approximate or cached within a transaction; for fresh snapshots, use short autocommit queries. For WAL, use a rate such as `rate(metric[5m])` only after confirming the actual exporter metric name and semantics.

## 4. Practical incident signal mapping

| Symptom | First DB signals | Cross-check | Escalation |
|---|---|---|---|
| Application p99 spikes | `pg_stat_activity` waits, `pg_locks`, query plans | App traces, CPU, storage latency | App + DBRE |
| Connections exhausted | `numbackends` / `max_connections`, idle transactions | Pool size, retry storm, admission | App + DBRE |
| Disk pressure | Database/table size, WAL/replication slots, host filesystem | Storage/volume monitoring | Infra + DBRE |
| Write latency | WAL bytes/sec, checkpoint activity, I/O wait | Disk IOPS/latency, commit timing | Infra + DBRE |
| Replica stale | `pg_stat_replication` and standby replay LSN | App replica-read staleness | DBRE + app |
| Vacuum lag | Dead tuple trends, autovacuum timestamps, oldest XID age | Long transactions, bloat, disk | DBRE |
| Query errors | App error rate, database logs, deadlock count | Release changes, retry behavior | App + DBRE |

A null or zero replication lag field does **not** by itself prove the replica is current. Validate LSN movement and replay plus application freshness requirements. `pg_stat_replication` only shows directly connected standbys.

## 5. Minimal Grafana dashboard design

Create dashboard variables for `environment`, `cluster`, `instance` and `database`. Use labels that uniquely identify a real cluster and distinguish primary from standby; do not mix similarly named databases from multiple clusters.

| Panel | Recommended visualization | Source |
|---|---|---|
| App request success and p95 latency | Time series + SLO threshold | Application telemetry |
| DB exporter/target health | Status and history | Prometheus `up` and exporter `pg_up` |
| Connections and headroom | Gauge/time series | `pg_stat_database_numbackends` / configuration |
| Transaction rate and rollback rate | Time series | `pg_stat_database` counter rates |
| Long transactions and wait states | Table/time series | Restricted monitoring queries |
| WAL generation and retention | Time series | `pg_stat_wal` + host disk + slots |
| Replication health | Per-replica table | Primary/standby LSN evidence |
| Storage growth by database/table | Time series | DB sizes + host/storage monitoring |
| Autovacuum and dead tuples | Table/trend | `pg_stat_user_tables` |
| CPU, memory and disk I/O | Time series | Node/host/cloud telemetry |

**Example PromQL** (verify series exist in the installed exporter version):

```promql
# Prometheus cannot scrape the exporter
up{job="postgres-ch12"} == 0

# Exporter scraped, but cannot connect to PostgreSQL
pg_up{job="postgres-ch12"} == 0

# DB connections for this lab
pg_stat_database_numbackends{datname="postgres",job="postgres-ch12"}
```

`pg_up` is a database scrape-success signal, not an application-availability SLO. Prometheus `up` is a scrape-success signal, not proof of database write readiness.

## 6. Alerts: actionable, owned, and testable

Alert on **impact and risk**, not every metric fluctuation. A useful alert has a clear owner, severity, runbook, noise policy, evaluation window and recovery condition.

Illustrative Prometheus rules:

```yaml
groups:
  - name: postgres-ch12-demo
    rules:
      - alert: PostgreSQLExporterDown
        expr: up{job="postgres-ch12"} == 0
        for: 2m
        labels:
          severity: warning
          owner: dbre
        annotations:
          summary: "PostgreSQL metrics exporter is unreachable"
          description: "Check exporter and Prometheus scrape configuration before assuming database outage."
      - alert: PostgreSQLDatabaseScrapeFailed
        expr: pg_up{job="postgres-ch12"} == 0
        for: 2m
        labels:
          severity: warning
          owner: dbre
        annotations:
          summary: "Exporter cannot read PostgreSQL metrics"
          description: "Check target identity, credentials, network, and database health."
```

These alerts are examples, not production-ready thresholds. Configure **missing-series** detection as appropriate: an absent `pg_up` is not the same as zero. For production, correlate application error-budget burn with database symptoms, and use multi-window alerts to avoid paging for transient spikes. Thresholds for connections, disk, lag and dead tuples must be workload-specific and validated with staging data.

## 7. Least-privilege telemetry and sensitive data

A monitoring user typically needs `LOGIN`, database `CONNECT` and the built-in `pg_monitor` role (or a more narrowly scoped alternative). Do **not** use a superuser for an exporter. Review `pg_monitor` visibility: monitoring views may expose query text or operational details; restrict access to metrics endpoints and dashboards. Exporter endpoints should not be publicly reachable. Use TLS, secret management, network policy and authenticated access in production.

High-cardinality labels (query text, customer ID, request ID, arbitrary tenant ID) can make Prometheus expensive and leak sensitive data. Prefer stable labels such as cluster, database, role and environment. Retain logs/metrics according to governance.

## 8. Deployment differences

| Area | Self-managed/bare metal | AWS RDS PostgreSQL | Kubernetes PostgreSQL |
|---|---|---|---|
| Host metrics | Node exporter/OS tools | CloudWatch and RDS monitoring features | Node/cAdvisor/CSI metrics |
| Database metrics | PostgreSQL views + exporter | Supported PostgreSQL views, CloudWatch Database Insights | Operator metrics + PostgreSQL exporter |
| HA telemetry | Replication/orchestrator + fencing | RDS topology-specific events and status | Operator reconciliation, pod/PVC/replication |
| Access | DBRE-managed roles and network | IAM/network controls plus DB roles | Secrets, RBAC, NetworkPolicy and DB roles |
| Escalation | DBRE + infrastructure | DBRE + cloud platform | DBRE + Kubernetes platform |

The exact metrics, managed-service privileges and HA mechanisms differ by product and version. AWS RDS does not expose the same host or superuser capabilities as self-managed PostgreSQL.

## 9. Lab and acceptance

Run [Chapter 12 lab](../labs/chapter-12/README.md). Its mandatory section uses isolated local PostgreSQL and read-only monitoring queries, then generates synthetic writes to observe counter changes. The optional section starts a local exporter and Prometheus without touching cloud resources.

- [ ] Explain the difference between app SLOs and database metrics.
- [ ] Capture PostgreSQL version, database identity, session state and transaction counters.
- [ ] Show that transaction and WAL counters can change after a small synthetic workload.
- [ ] Explain why a cumulative counter is not a rate.
- [ ] Distinguish exporter-down from database-scrape-failed conditions.
- [ ] Propose at least four dashboard panels and two owned, actionable alerts.
- [ ] Close sessions, confirm no idle-in-transaction connection remains, and sanitize evidence.
- [ ] Mark runtime verified **only** after real execution and review.

**Current validation:** authored only; no Docker, PostgreSQL, Prometheus, Grafana or cloud runtime was executed during this publication.

## 10. Troubleshooting and safe rollback

| Observation | Likely cause | Safe response |
|---|---|---|
| Exporter metrics absent | Wrong port, network or exporter process | Check `docker ps`, scrape target and logs |
| `up=1` but `pg_up=0` | Exporter reachable but DB login/queries failed | Check read-only credentials and connection |
| Metrics reset or drop | Server/statistics reset | Inspect `stats_reset` and deployment history |
| No replication rows | Standalone primary or no connected standby | Verify topology; not automatically an error |
| Unusual dead tuples | Write churn, autovacuum, long snapshots | Investigate before changing vacuum settings |
| Dashboard shows unexpected spikes | Counter resets or high-cardinality aggregation | Review query, labels and reset handling |

Rollback is limited to stopping the **optional, disposable** monitoring containers and restoring the original lab state. Never delete an existing database, shared Docker volume, exporter, or production dashboard as part of the exercise.

## 11. Official references

- [PostgreSQL 17 — Monitoring Database Activity](https://www.postgresql.org/docs/17/monitoring.html)
- [PostgreSQL 17 — Statistics Views](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17 — Monitoring Disk Usage](https://www.postgresql.org/docs/17/diskusage.html)
- [PostgreSQL 17 — Monitoring Roles](https://www.postgresql.org/docs/17/predefined-roles.html)
- [Prometheus Community PostgreSQL Exporter](https://github.com/prometheus-community/postgres_exporter)
- [Prometheus — Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Grafana — PostgreSQL Monitoring](https://grafana.com/docs/grafana/latest/datasources/postgres/)
