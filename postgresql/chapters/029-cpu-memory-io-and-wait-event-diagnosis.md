# Chapter 029 — CPU, Memory, I/O and Wait Event Diagnosis

**Audience:** DBRE and SRE. **Baseline:** PostgreSQL 18 on Linux; adapt host evidence to the deployment platform. **Outcome:** form a resource hypothesis from a shared measurement window, test it with bounded evidence, and choose an operational response.

## 1. Diagnose the service symptom first

Start with request latency, error rate, throughput and affected workload from Chapter 021. Define the incident window and compare with a similar healthy interval. Separate connection admission, execution, commit and result delivery where application traces allow it.

Reuse [Chapter 026](026-performance-triage-and-evidence-collection.md) for general incident evidence, [Chapter 027](027-explain-and-explain-analyze-safely.md) for safe execution plans and [Chapter 028](028-planner-estimates-statistics-and-extended-statistics.md) for estimate problems. This chapter correlates resource evidence; it does not prescribe a universal tuning percentage.

## 2. Build a common measurement window

Collect UTC timestamps, database/version identity, role, reset epochs, host identity, CPU allocation and workload phase. Take two cumulative snapshots plus repeated activity observations between them. Keep each observer transaction short; a long transaction can preserve cached activity/statistics. Publication of cumulative counters can lag an active query.

Do not subtract counters across a reset, restart, missing row or changed identity. Compute elapsed time from observed timestamps, not the number of loop iterations. Treat NULL fields and disabled timing as unavailable. A fresh observer session's settings describe that observer, not necessarily every workload backend's settings.

Keep the snapshot and activity output private. Application names and query identifiers can expose operational information even when query text is omitted. The supplied collector omits statement text, client addresses, user names, database names for unrelated sessions and object definitions.

## 3. Read state and wait events together

| Observation | Interpretation | Evidence needed next |
|---|---|---|
| active, no reported wait | Executing or between instrumented waits | Per-process CPU and scheduler evidence; this alone does not prove CPU saturation |
| active, Lock | Waiting for a heavyweight lock | Blocking PID/identity and transaction scope; Chapter 018 |
| active, LWLock | Waiting on an internal shared-memory lock | Exact event, concurrency and subsystem; ordinary blocking chains may be empty |
| IO | An instrumented I/O operation is pending | Event, bytes/operations, device latency and throughput |
| ClientRead | Waiting for client input | State matters: idle can be normal, idle-in-transaction can retain locks/snapshots |
| ClientWrite | Waiting to send data to the client | Result size, driver consumption, network and downstream backpressure |
| IPC | Interaction with another PostgreSQL process | Parallel/replication context and the exact event |
| Timeout / PgSleep | Deliberate timed delay | Do not classify sleep as CPU or storage distress |
| Activity | Background process awaiting work | Usually normal; relate to its backend type |
| BufferPin | Buffer access blocked by a pin | Cursor/transaction behavior; not simply a SQL row-lock problem |

One sample is a point observation. Repeated one-second samples estimate occupancy at that cadence, not exact time spent waiting. Short waits can be missed. State and wait fields are sampled with possible transient inconsistencies. Retain backend_start with PID to protect against PID reuse; leader_pid connects parallel workers to their leader.

## 4. CPU: utilization, demand and entitlement

A PostgreSQL query generally runs in a backend process, with optional parallel workers. One serial backend can use one CPU heavily while the host average remains low. Examine the workload PID and workers in the server's PID namespace.

Correlate backend CPU with host user/system utilization, runnable queue, effective CPU allocation and application concurrency. On virtual machines inspect steal time. In containers inspect cgroup CPU quota and throttling deltas; a quiet host can contain a throttled database container. Load average also includes uninterruptible tasks and is not equivalent to CPU utilization.

A resource hypothesis should distinguish expensive SQL from excessive concurrency, quota constraints or work done by maintenance. Confirm the plan and query statistics before adding CPUs. Response choices include reducing admitted concurrency, fixing query work, rescheduling competing maintenance or changing allocation after capacity review. Never disable maintenance blindly.

For cgroup v2, correlate cpu.max with deltas of cpu.stat (including throttling), plus cpuset.cpus.effective where available. Locate the actual database cgroup from its server-side /proc/PID/cgroup and mount namespace; reading the observer shell's cgroup can describe the wrong service.

## 5. Memory: budget concurrent operations, not connections alone

Account for shared buffers, process-private memory, active operations, maintenance, OS cache and deployment overhead. work_mem is an operation budget: several sorts/hashes can coexist in one query and many sessions can execute them concurrently. Parallel execution and hash_mem_multiplier further affect the envelope. It is not a guaranteed per-connection allocation or a total query cap.

Use EXPLAIN to identify sort methods, reported memory/disk use, hash batches and temporary blocks. PostgreSQL 18 EXPLAIN MEMORY describes planner memory, not total execution memory. pg_backend_memory_contexts describes the inspecting backend; it cannot establish the entire cluster's memory consumption.

At the host, consider MemAvailable, swap-in/out rates, memory pressure and OOM evidence. Low free memory alone can reflect useful cache. Summing backend RSS can double-count shared mappings; use appropriate PSS/shared-private accounting if needed. For cgroup v2 inspect memory.current, memory.max and memory.events deltas; counters require an interval and an allocation context.

Memory pressure and a query spill are different findings. A spill can happen because one operation's budget is low even when the host has headroom. Increasing work_mem globally to remove it can make concurrency unsafe. Prefer a tested session/local change for the relevant workload and validate the aggregate envelope.

## 6. I/O: separate PostgreSQL operations from storage requests

| Source | Scope | Limitation |
|---|---|---|
| pg_stat_database | Current database aggregate counters, temp bytes/files and timing | Does not identify the responsible query |
| pg_stat_io | Cluster-wide backend type/object/context counters | Not a per-database or per-query device trace |
| EXPLAIN BUFFERS | Statement/node buffer activity and temporary blocks | Shared read does not prove physical device access; OS cache may serve it |
| pg_stat_checkpointer / pg_stat_wal | Checkpoint and WAL activity | Keep reset/window boundaries; concurrent subsystems contribute |
| Linux device metrics / cloud volume telemetry | Latency, queues, throughput, IOPS and allocation | Map the correct mount/device/volume and include platform throttling |

PostgreSQL 18 pg_stat_io has read_bytes and write_bytes and includes WAL object rows. Use the schema for the pinned version; older scripts relying on op_bytes need review. Preserve backend_type, object, context and stats_reset as the comparison key. Unsupported combinations can have NULLs or no row.

Its temp relation rows describe temporary relations, not all executor sort/hash work files. Use database temp_bytes/temp_files, EXPLAIN temporary blocks and controlled temporary-file logging when investigating spills. PostgreSQL statistics cannot determine whether a read went to media or was satisfied by the operating-system cache.

For matching rows and a valid interval, byte rate is delta(read_bytes)/elapsed_seconds; operation rate is delta(reads)/elapsed_seconds. Mean instrumented read time is delta(read_time)/delta(reads) in milliseconds only when timing was enabled throughout and reads increased. This is not a device percentile. track_io_timing and track_wal_io_timing are separate controls; a zero time with collection disabled is not zero latency. Benchmark overhead before changing timing policy.

Map PGDATA, WAL, tablespaces and temporary storage separately when applicable. Compare device latency, queue growth and achieved throughput/IOPS to the volume's actual limits. A busy-device percentage alone does not prove saturation for every storage topology. CPU iowait is not a per-query wait-duration metric.

## 7. Linux commands and interpretation

Run these on the database host/namespace with an authorized account; optional tools may be absent. They collect evidence and do not change the host.

~~~bash
date -u +%FT%TZ
vmstat 1 6
iostat -x -y 1 5
pidstat -u -r -d -p 12345 1 5
free -m
df -h
df -i
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
~~~

Replace 12345 only with a current PostgreSQL PID verified against backend_start and the host namespace. vmstat's first report normally reflects averages since boot; subsequent reports cover intervals. iostat -y omits the first since-boot report. Filesystem fullness/inode exhaustion is a capacity finding; it does not measure latency.

Pressure Stall Information reports time tasks are stalled for CPU, memory or I/O. Correlate its window with service behavior and allocation. The supplied lab intentionally avoids generating host memory exhaustion or storage saturation. On managed PostgreSQL, use provider metrics for OS/cgroup evidence unavailable to SQL and record the visibility gap.

## 8. Response matrix

| Combined evidence | Working hypothesis | Controlled next action |
|---|---|---|
| Backend CPU high, runnable pressure, no dominant reported wait | CPU demand or CPU entitlement constraint | Inspect plan/concurrency/quota; test reduced admission or query change |
| Lock samples, blockers, low CPU | Concurrency blocking | Diagnose oldest relevant transaction; scoped Chapter 020 response |
| External sort/hash batches, temp growth, host memory healthy | Operation spilling | Test local budget/query change; validate concurrent memory headroom |
| Memory pressure/swap/OOM evidence with many active operations | Aggregate memory pressure | Reduce concurrency; review per-operation and maintenance budgets |
| IO waits plus growing device latency/queues and volume-limit telemetry | Storage bottleneck | Identify reads/WAL/checkpoints/spills; reduce source work or revise volume allocation |
| ClientWrite plus slow consumer | Delivery backpressure | Examine result size, application reader, network and downstream |
| No clear correlation or missing permissions/metrics | Incomplete evidence | State uncertainty, improve coverage and repeat a bounded window |

Several causes can coexist. Choose an action that addresses observed pressure, define the expected metric change and rollback, and compare the same workload after recovery. Do not terminate sessions, reset counters, drop caches, disable fsync or change global memory settings as a diagnostic shortcut.

## 9. Lab and operational acceptance

Run the [hands-on lab](../labs/029-cpu-memory-io-and-wait-event-diagnosis-lab.md). It observes intentional sleep, CPU work, a controlled lock wait, and a low/high local-memory sort. It collects repeated PostgreSQL snapshots and optional bounded host evidence.

Acceptance requires a phase-by-phase diagnosis, correlated timestamps, valid reset boundaries, explicit missing observations, resource-budget reasoning, successful cleanup and an actionable response with rollback. Runtime results remain pending until the lab is executed.

## References

- [PostgreSQL 18 monitoring](https://www.postgresql.org/docs/18/monitoring.html)
- [Cumulative statistics and wait events](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Resource consumption settings](https://www.postgresql.org/docs/18/runtime-config-resource.html)
- [EXPLAIN interpretation](https://www.postgresql.org/docs/18/using-explain.html)
- [Kernel cgroup v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [Kernel pressure stall information](https://www.kernel.org/doc/html/latest/accounting/psi.html)
- [sysstat upstream](https://github.com/sysstat/sysstat)

**Next:** Chapter 030 — Production Slowness Investigation Project.
