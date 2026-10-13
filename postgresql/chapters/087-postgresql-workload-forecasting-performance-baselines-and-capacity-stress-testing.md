# Chapter 087 — PostgreSQL Workload Forecasting, Performance Baselines and Capacity Stress Testing

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Convert [Chapter 086 — Capacity Forecasting and FinOps](086-postgresql-capacity-forecasting-cost-optimization-and-finops.md) into evidence-backed workload limits and scale decisions. Establish a repeatable performance baseline, test realistic peak scenarios, find the saturation knee, and define safe operating headroom.

**The usable capacity ceiling is the highest workload that still satisfies application SLOs and recovery constraints**, not the highest transactions per second a benchmark can produce.

## 2. Characterize the workload

Inventory workload by business operation, not only SQL statement:

| Dimension | Examples | Why it matters |
|---|---|---|
| Transaction mix | Read-only, read-write, bulk ingest, reporting | CPU, lock and WAL demand |
| Arrival pattern | Steady, diurnal, burst, batch overlap | Queueing and peak saturation |
| Concurrency | Clients, pool size, active backends | Contention and memory |
| Data shape | Hot set, table/index size, skew, retention | Cache and query-plan behavior |
| Latency | p50, p95, p99 by operation | User experience and tail risk |
| Throughput | Committed transactions/s, rows/s | Business demand |
| Reliability | Timeouts, errors, deadlocks, failover | True sustainable capacity |
| Recovery | Replication lag, WAL/archive, backup windows | RPO/RTO guardrails |

Use application traces, pooler metrics, `pg_stat_statements` where approved, `pg_stat_database`, host/cloud monitoring and business demand forecasts. PostgreSQL statistics are cumulative and require timestamped deltas; note `stats_reset`.

## 3. Forecast demand

```text
Expected peak TPS = current measured peak TPS × demand growth factor
Scenario peak TPS = expected peak TPS × event/burst factor
Required capacity = scenario peak TPS + explicitly approved headroom
```

Model low/base/high demand, new tenants, data backfills, scheduled jobs and simultaneous failures. Avoid extrapolating throughput linearly with vCPU count: locks, I/O, shared cache, connection overhead and serial bottlenecks can dominate.

## 4. Define the test contract

Before load generation, document:

- Environment, PostgreSQL version, CPU/RAM, storage tier, IOPS, topology and pooler.
- Dataset size, indexes, cardinality, skew and hot/cold cache state.
- Workload mix and query/transaction scripts with parameter distributions.
- Ramp, steady-state, burst, recovery and cool-down durations.
- Concurrency and arrival rate; distinguish **closed-loop clients** from **open-loop arrivals**.
- SLO thresholds for p95/p99, throughput, error rate, CPU, I/O, replica lag and disk/WAL.
- Abort limits for latency, disk headroom, memory, replication and production-like neighbors.
- Ownership, approval, observation window, rollback and evidence location.

A benchmark without representative data and arrival patterns is a microbenchmark, not a production capacity guarantee.

## 5. Baseline and pgbench

`pgbench` is bundled with PostgreSQL client tools and can run its standard transaction mix or a custom script. Run only against a **disposable** database:

```bash
createdb ch087_lab
pgbench -i -s 10 ch087_lab
pgbench -c 4 -j 2 -T 120 -P 10 -r ch087_lab
```

Use an approved test role, explicit host/port and secure authentication in real environments. `-s 10` initializes a moderate synthetic dataset; it is **not** representative of production by itself. For custom workload scripts, use `-f` and verify that the transaction mix and data distributions match the application. Report `pgbench` TPS alongside errors, latency and host metrics.

## 6. Controlled ramp and saturation

Recommended disposable-lab progression:

| Phase | Concurrency | Duration | Goal |
|---|---:|---:|---|
| Warmup | 2 | 60 s | Stabilize cache and connections |
| Baseline | 4 | 120 s | Establish reference TPS and latency |
| Moderate | 8 | 120 s | Check scaling efficiency |
| High | 16 | 120 s | Find contention/queueing |
| Stress | 32 | 120 s | Identify saturation; abort if limits hit |
| Recovery | 4 | 120 s | Confirm performance returns |

These numbers are **illustrative**, not universal production limits. Keep dataset and workload constant while changing one variable. Repeat runs, include variance and capture confidence/measurement uncertainty.

## 7. Interpreting results

- **CPU saturation:** high runnable load and query CPU, throughput plateau; inspect query plans and CPU quotas.
- **Disk bottleneck:** latency/queue depth rises, read/write IOPS reaches tier limit; inspect cache hit, checkpoints and WAL.
- **Lock contention:** sessions wait on locks; investigate transaction scope, hot rows and deadlocks.
- **Connection pressure:** active backends and pool queue rise; use pooling rather than unlimited connections.
- **Memory pressure:** temp spill, swap/OOM, reduced page cache; inspect sort/hash and concurrency.
- **WAL/replication:** high WAL bytes/s, archive failures, lag and slot retention; capacity may be limited by recovery objectives before primary TPS saturates.

A throughput plateau with rising p99 latency signals the saturation knee. Report the **last passing phase** as sustainable tested capacity, subject to workload representativeness.

## 8. Queueing and latency

Little's Law provides an approximate relationship for stable systems:

```text
Average in-flight work L = arrival rate λ × average response time W
```

It does not replace tail-latency measurement or prove stability during bursts. Closed-loop load generators may self-throttle as latency rises and understate overload risk; consider controlled arrival-rate tests for production-like traffic.

## 9. HA and resilience under load

Repeat approved scenarios during replica catch-up, backup windows, autovacuum, maintenance and failover rehearsal. Verify read/write routing, replication lag, WAL retention, archive, application retries and error budget. A primary that meets TPS while its standby falls irrecoverably behind is not an acceptable production capacity result.

## 10. Test safety and cleanup

Never run unbounded stress tests against production without a formal load-test change and protective controls. Use dedicated test environments, explicit duration, hard resource ceilings, abort conditions and monitoring. Stop the load generator first on overload; then verify database and replica recovery. Remove disposable fixtures only after preserving evidence.

## 11. Capacity decision and cost tradeoff

Compare baseline and candidate configurations at the **same workload**, dataset and SLOs. Calculate cost per successful transaction only within an accepted reliability envelope; include HA replicas, storage I/O, backup and operational effort. A cheaper configuration that violates p99 or RPO is rejected, regardless of lower cost/TPS.

## 12. Lab and acceptance

Use [Chapter 087 lab](../labs/087-postgresql-workload-forecasting-performance-baselines-and-capacity-stress-testing-lab.md), [metrics inspection SQL](../labs/sql/087-workload-baseline-inspect.sql), [load test plan](../labs/performance/087-load-test-plan.csv), and [acceptance scorecard](../labs/acceptance/087-workload-capacity-scorecard.csv).

**PASS requires:** representative workload and dataset, repeatable runs, timestamped database/host metrics, measured latency/error/throughput, documented saturation point, safe abort/recovery and approved capacity headroom. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/pgbench.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/using-explain.html
- https://www.postgresql.org/docs/18/runtime-config-resource.html
- https://www.postgresql.org/docs/18/warm-standby.html

**Next:** Chapter 088 — PostgreSQL Storage Growth, Retention and Lifecycle Optimization.
