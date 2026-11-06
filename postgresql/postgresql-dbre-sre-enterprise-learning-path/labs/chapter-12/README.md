# Chapter 12 Lab — PostgreSQL Monitoring and Observability

**Runtime:** PostgreSQL 17, Docker Desktop (Linux containers), Windows PowerShell.  
**Time:** 25 minutes core + 15 minutes optional exporter/Prometheus.  
**Status:** Authored; not executed or independently reviewed.

[Chapter 12](../../chapters/12-monitoring-alerting-and-observability.md) · [Learning path](../../README.md)

## Prerequisites and guardrails (5 minutes)

Use a disposable local Docker environment, not production. This lab creates a dedicated container and network; it does not alter the existing `pg-fleet-lab` or prior chapters. No cloud resources are needed. Verify that ports 55434, 9188 and 9099 are unused.

```powershell
docker version
docker context show
docker info --format '{{.OSType}}'
docker ps -a --filter "name=pg-monitor-ch12"
docker ps -a --filter "name=pg-exporter-ch12"
docker ps -a --filter "name=prometheus-ch12"
docker network ls --filter "name=pg-monitor-ch12-net"
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 55434,9188,9099 }
```

Expected on first use: Linux Docker daemon, no existing Chapter 12 resources. **If any name collides, stop and inspect; do not overwrite or delete it.** Passwords shown below are disposable demo values only; never reuse them in production.

## 1. Start PostgreSQL (3 minutes)

```powershell
$labContext = docker context show
$labNetworkId = docker network create --label training.owner=postgresql-dbre-sre-enterprise-learning-path --label training.chapter=12 pg-monitor-ch12-net
if ($LASTEXITCODE -ne 0 -or -not $labNetworkId) { throw 'Network creation failed; stop lab.' }
$labNetworkId = $labNetworkId.Trim()
$pgContainerId = docker run -d --name pg-monitor-ch12 --label training.owner=postgresql-dbre-sre-enterprise-learning-path --label training.chapter=12 --network pg-monitor-ch12-net -p 127.0.0.1:55434:5432 -e POSTGRES_PASSWORD=TrainingOnly_Ch12_ChangeMe postgres:17
if ($LASTEXITCODE -ne 0 -or -not $pgContainerId) { throw 'PostgreSQL creation failed; stop lab.' }
$pgContainerId = $pgContainerId.Trim()
Write-Host "Retain privately for cleanup: context=$labContext network ID=$labNetworkId PostgreSQL ID=$pgContainerId"
docker exec pg-monitor-ch12 pg_isready -U postgres -d postgres
docker exec pg-monitor-ch12 psql -U postgres -d postgres -c "SELECT version(), current_database(), pg_is_in_recovery();"
```

Expected: PostgreSQL 17, database `postgres`, recovery = false. Retry readiness after a brief initialization delay if needed.

## 2. Baseline monitoring queries (5 minutes)

Open a psql session:

```powershell
docker exec -it pg-monitor-ch12 psql -U postgres -d postgres
```

Execute the following SQL in psql, one statement at a time:

```sql
SELECT current_database(), current_user, pg_is_in_recovery();
SHOW max_connections;

SELECT COALESCE(state,'<unknown>') AS state, count(*) AS sessions
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY 1 ORDER BY 1;

SELECT datname, numbackends, xact_commit, xact_rollback,
       deadlocks, temp_bytes, stats_reset
FROM pg_stat_database WHERE datname = current_database();

SELECT wal_records, wal_bytes, stats_reset FROM pg_stat_wal;

SELECT num_timed, num_requested, write_time, sync_time
FROM pg_stat_checkpointer;

SELECT application_name, state, sync_state, sent_lsn, replay_lsn
FROM pg_stat_replication;
```

Expected: one or more active sessions, numeric cumulative counters, and **zero replication rows** because this is a standalone PostgreSQL server. Record the values and the `stats_reset` timestamps. Never interpret a cumulative counter as a per-second rate.

## 3. Generate synthetic workload (5 minutes)

```sql
CREATE TABLE public.monitor_ch12_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.monitor_ch12_events(event_type)
SELECT 'inserted' FROM generate_series(1,5000);

UPDATE public.monitor_ch12_events
SET event_type = 'updated'
WHERE event_id <= 1000;

SELECT count(*) AS total_rows,
       count(*) FILTER (WHERE event_type='updated') AS updated_rows
FROM public.monitor_ch12_events;
```

Expected: 5,000 total rows and 1,000 updated rows.

```sql
SELECT pg_sleep(1);
SELECT pg_stat_clear_snapshot();

SELECT xact_commit, xact_rollback, blks_hit, blks_read, stats_reset
FROM pg_stat_database WHERE datname=current_database();

SELECT wal_records, wal_bytes, stats_reset FROM pg_stat_wal;

SELECT relname, n_tup_ins, n_tup_upd, n_dead_tup
FROM pg_stat_user_tables
WHERE schemaname='public' AND relname='monitor_ch12_events';

SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
```

Expected: some counters rise compared with baseline. Exact numbers are not fixed because statistics update asynchronously and background activity continues. If `stats_reset` changed, do not compute a delta across the reset.

## 4. Inspect live sessions safely (2 minutes)

```sql
SELECT pid, usename, state, wait_event_type, wait_event,
       now() - xact_start AS transaction_age
FROM pg_stat_activity
WHERE datname = current_database()
ORDER BY xact_start NULLS LAST;
```

Avoid exporting query text because it can contain secrets or user data in real environments. Exit with `\q`; do not leave a transaction open.

## 5. Optional local postgres_exporter (5 minutes)

This section demonstrates a least-privilege monitoring user. It uses a visible demo password in a local Docker environment variable; **production requires proper secrets, TLS, access controls and private endpoints**. The exporter version `v0.20.1` was released in July 2026.

```powershell
docker exec pg-monitor-ch12 psql -U postgres -d postgres -c "CREATE ROLE monitor_ch12 LOGIN PASSWORD 'TrainingOnly_Monitor_Ch12';"
docker exec pg-monitor-ch12 psql -U postgres -d postgres -c "GRANT pg_monitor TO monitor_ch12;"
docker exec pg-monitor-ch12 psql -U postgres -d postgres -c "GRANT CONNECT ON DATABASE postgres TO monitor_ch12;"

$exporterContainerId = docker run -d --name pg-exporter-ch12 --label training.owner=postgresql-dbre-sre-enterprise-learning-path --label training.chapter=12 --network pg-monitor-ch12-net -p 127.0.0.1:9188:9187 -e DATA_SOURCE_USER=monitor_ch12 -e DATA_SOURCE_PASS=TrainingOnly_Monitor_Ch12 quay.io/prometheuscommunity/postgres-exporter:v0.20.1 --datasource.uri="pg-monitor-ch12:5432/postgres?sslmode=disable"
if ($LASTEXITCODE -ne 0 -or -not $exporterContainerId) { throw 'Exporter creation failed; stop lab.' }
$exporterContainerId = $exporterContainerId.Trim()
Write-Host "Retain privately for cleanup: exporter ID=$exporterContainerId"

docker logs --tail 25 pg-exporter-ch12
```

Visit `http://127.0.0.1:9188/metrics`. Look for `pg_up 1` and database statistics metrics. If `pg_up 0`, investigate connection, role and network rather than granting superuser. Exporter metric names may change by version; inspect actual series before writing PromQL.

## 6. Optional Prometheus scrape (5 minutes)

In PowerShell, create `prometheus-ch12.yml` in a disposable working directory:

```powershell
@'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: postgres-ch12
    static_configs:
      - targets: ['pg-exporter-ch12:9187']
'@ | Set-Content -Path .\prometheus-ch12.yml -Encoding ascii
```

Start Prometheus:

```powershell
$promContainerId = docker run -d --name prometheus-ch12 --label training.owner=postgresql-dbre-sre-enterprise-learning-path --label training.chapter=12 --network pg-monitor-ch12-net -p 127.0.0.1:9099:9090 -v "$($PWD.Path)\prometheus-ch12.yml:/etc/prometheus/prometheus.yml:ro" prom/prometheus:v3.7.3
if ($LASTEXITCODE -ne 0 -or -not $promContainerId) { throw 'Prometheus creation failed; stop lab.' }
$promContainerId = $promContainerId.Trim()
Write-Host "Retain privately for cleanup: Prometheus ID=$promContainerId"
docker logs --tail 25 prometheus-ch12
```

Visit `http://127.0.0.1:9099/targets`; after a scrape, job `postgres-ch12` should show UP. Evaluate these expressions in the Prometheus query UI:

```promql
up{job="postgres-ch12"}
pg_up{job="postgres-ch12"}
pg_stat_database_numbackends{job="postgres-ch12",datname="postgres"}
```

Expected: `up = 1`, `pg_up = 1`, and a nonnegative connection count if the collector emits that series. `up` means exporter scrape success; `pg_up` means database scrape success. Neither alone proves application availability. Grafana is **not** installed in this lab.

## 7. Design review and acceptance (5 minutes)

Create a dashboard sketch with application p95 latency/error rate, connection utilization, transaction rate, WAL bytes/sec, replication health, dead tuples, and host storage usage. Explain which signals are not available from PostgreSQL alone.

Design two warning alerts with a 2-minute evaluation window: exporter unreachable (`up == 0`) and exporter reachable but database scrape failed (`pg_up == 0`). Include owner, severity, runbook and missing-series handling. Do not connect alerts to real paging systems.

Acceptance checklist:
- [ ] Verified PostgreSQL version, database identity and standalone topology.
- [ ] Recorded session, transaction, WAL and checkpoint statistics.
- [ ] Created 5,000 synthetic rows and updated 1,000.
- [ ] Compared counters and explained reset/delay behavior.
- [ ] Queried live session state without leaking SQL text.
- [ ] Optional: monitoring role is not superuser; exporter responds.
- [ ] Optional: Prometheus target UP and expressions evaluated.
- [ ] Drafted dashboard and two owned, actionable alerts.
- [ ] Closed psql sessions and sanitized all evidence.
- [ ] Kept runtime validation **pending** until actual execution and review.

## 8. Troubleshooting

| Symptom | Check | Safe next step |
|---|---|---|
| Port already in use | Docker and host port inventory | Stop and choose unused port |
| Docker daemon unavailable | `docker info` | Start Docker Desktop |
| PostgreSQL not ready | `docker logs pg-monitor-ch12` | Wait for initialization |
| Monitoring role already exists | Prior lab run | Inspect identity; do not overwrite blindly |
| `pg_up = 0` | Exporter logs, credentials, network | Repair lab connection; don't grant superuser |
| Prometheus target DOWN | `/targets`, Prometheus logs, YAML | Correct local config |
| No replication rows | Single-node topology | Expected |
| Unexpectedly low counters | Stats delay or reset | Inspect `stats_reset`; retry read |

## 9. Optional cleanup (destructive to disposable lab only)

Before cleanup, retain the **full** container IDs and network ID printed during creation, plus the original Docker context. If those values are lost, **stop** rather than guessing by name. Confirm no other containers or users depend on this network or any mounted volume. Never use these commands on shared or production resources.

Run the following in the **same PowerShell session** that created the resources (or restore the recorded IDs and context explicitly). Optional container IDs may be absent when those steps were skipped. Inspect each mount and network attachment before removal; a bind mount must point only to the disposable configuration file, and unexpected volumes or connections are a stop condition.

```powershell
if (-not $labContext -or -not $labNetworkId -or -not $pgContainerId) { throw 'Missing creation evidence; do not clean up.' }
if ((docker context show) -ne $labContext) { throw 'Docker context changed; stop.' }
$expected = @(
    @{ Name='pg-monitor-ch12'; Id=$pgContainerId },
    @{ Name='pg-exporter-ch12'; Id=$exporterContainerId },
    @{ Name='prometheus-ch12'; Id=$promContainerId }
)
foreach ($item in $expected) {
    if (-not $item.Id) { continue } # Optional service was not created
    $actual = docker inspect --format '{{.Id}}' $item.Name
    if ($LASTEXITCODE -ne 0 -or $actual.Trim() -cne $item.Id) { throw "Container ID mismatch: $($item.Name)" }
    $owner = docker inspect --format '{{index .Config.Labels "training.owner"}}' $item.Name
    $chapter = docker inspect --format '{{index .Config.Labels "training.chapter"}}' $item.Name
    if ($owner -cne 'postgresql-dbre-sre-enterprise-learning-path' -or $chapter -cne '12') { throw "Ownership mismatch: $($item.Name)" }
    docker inspect --format '{{json .Mounts}}' $item.Name
    docker inspect --format '{{json .NetworkSettings.Networks}}' $item.Name
}
$actualNetwork = docker network inspect --format '{{.Id}}' pg-monitor-ch12-net
if ($LASTEXITCODE -ne 0 -or $actualNetwork.Trim() -cne $labNetworkId) { throw 'Network ID mismatch; stop.' }
docker network inspect --format '{{json .Containers}}' pg-monitor-ch12-net
```

**Manual approval gate:** Inspect the displayed mounts and network members. Confirm every connected container is one of the captured lab IDs, the Prometheus bind source is the intended disposable file, and PostgreSQL's anonymous data volume belongs only to this lab. Do not proceed on any mismatch. The commands below intentionally omit `docker rm -v`; anonymous volumes may remain and require a separate identity-checked disposal procedure. Never prune volumes globally.

```powershell
foreach ($item in $expected) {
    if (-not $item.Id) { continue }
    docker stop $item.Id
    if ($LASTEXITCODE -ne 0) { throw "Stop failed: $($item.Name)" }
    docker rm $item.Id
    if ($LASTEXITCODE -ne 0) { throw "Remove failed: $($item.Name)" }
    docker inspect $item.Id 2>$null
    if ($LASTEXITCODE -eq 0) { throw "Container still exists: $($item.Name)" }
}
docker network rm $labNetworkId
if ($LASTEXITCODE -ne 0) { throw 'Network removal failed; inspect remaining connections.' }
docker network inspect $labNetworkId 2>$null
if ($LASTEXITCODE -eq 0) { throw 'Network still exists.' }
# Optional: remove the local YAML only after verifying its absolute path and contents.
```

Record sanitized evidence of the context, IDs, ownership labels, mount review, network membership, cleanup result and absence checks. Do not publish `docker inspect` environment variables or credentials. If any command fails, stop and investigate rather than force-removing resources.

## Official references

- [PostgreSQL 18 statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL predefined roles](https://www.postgresql.org/docs/18/predefined-roles.html)
- [Prometheus postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
- [Prometheus Docker installation](https://prometheus.io/docs/prometheus/latest/installation/)
- [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
