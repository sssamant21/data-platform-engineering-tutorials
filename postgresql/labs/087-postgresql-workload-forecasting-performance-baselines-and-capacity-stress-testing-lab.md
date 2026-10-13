# Chapter 087 — Workload Forecasting, Performance Baselines and Capacity Stress Testing Lab

**PostgreSQL 18 · Disposable database only · Runtime pending**

## 1. Safety

Use a dedicated disposable PostgreSQL 18 instance. Install matching `pgbench` client tools and secure test credentials. Record CPU, memory, disk, IOPS, network, PostgreSQL version, connection pooler, test host and storage limits. Never run the example stress profile against production.

## 2. Initialize the workload

```powershell
createdb -h localhost -U postgres ch087_lab
pgbench -h localhost -U postgres -i -s 10 ch087_lab
```

Use a test identity with the required permissions. Record dataset size and table/index statistics.

## 3. Capture baseline

Run [087 inspection SQL](../labs/sql/087-workload-baseline-inspect.sql) before and after each phase. Save UTC sample timestamps and `stats_reset`. Collect host CPU, memory, disk I/O and application/pgbench latency externally.

## 4. Execute controlled phases

Complete [087 load test plan](../labs/performance/087-load-test-plan.csv). Example:

```powershell
pgbench -h localhost -U postgres -c 4 -j 2 -T 120 -P 10 -r ch087_lab
pgbench -h localhost -U postgres -c 8 -j 2 -T 120 -P 10 -r ch087_lab
pgbench -h localhost -U postgres -c 16 -j 4 -T 120 -P 10 -r ch087_lab
```

Add 32 clients only when prior phases pass and headroom remains. Run a warmup and recovery phase. Stop immediately if the approved disk, latency, error, memory or replication thresholds are breached.

## 5. Analyze saturation

Compare TPS, average/p95/p99 latency where supported by your measurement tooling, error rate, active backends, waits, WAL generation, temp bytes, host I/O and CPU. `pgbench` summary does not automatically provide every percentile; capture per-transaction latency logs or use a validated load-test telemetry pipeline. Identify the highest phase that passed **all** gates.

## 6. Recovery and HA tabletop

Stop load; verify that connection counts, latency, WAL archive and replication lag return to baseline. Document how backups, autovacuum and failover would change headroom. Do not claim HA acceptance from a single-node lab.

## 7. Acceptance

Complete [087 scorecard](../labs/acceptance/087-workload-capacity-scorecard.csv). Include command line, client host, UTC timestamps, data size, repetitions, results, failures and capacity recommendation. Mark missing real-world traffic representativeness and external metrics NOT VERIFIED.

**Runtime:** pending.
