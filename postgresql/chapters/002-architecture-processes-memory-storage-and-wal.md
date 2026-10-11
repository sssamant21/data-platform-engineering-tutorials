# 002 — Architecture: Processes, Memory, Storage and WAL

[Master plan](../MASTER-PLAN.md) · [Previous chapter](001-postgresql-responsibilities-for-dbre-and-sre.md) · [Hands-on lab](../labs/002-postgresql-architecture-inspection-lab.md)

## 1. Operational problem and objectives

A latency incident can originate in query execution, contention, memory pressure, WAL flushes or data-file I/O. Changing one setting without knowing which component is constrained can move the problem elsewhere.

This chapter builds an operational map of PostgreSQL. By the end you should identify the processes behind connections, distinguish memory budgets, locate logical storage, explain WAL and checkpoints, and collect evidence without changing production configuration.

**Audience:** DBRE/SRE only. **Reference major:** PostgreSQL 18. Pin the exact minor and tool versions when running the lab. **Prerequisite:** Chapter 001 and an existing disposable instance. Allow approximately 60–90 minutes including the lab.

## 2. Operational architecture

~~~mermaid
flowchart TD
    A["Application or pool"] --> B["Client backend"]
    B --> C["Shared buffers"]
    B --> D["WAL buffers"]
    D --> E["WAL storage"]
    C --> F["Data storage"]
    G["Checkpointer and background writer"] --> F
    E --> H["Recovery and replication"]
~~~

This is a component map, not a strict timeline: normal backends can also write dirty buffers. The operating system and storage stack sit below both WAL and data storage.

A PostgreSQL **database cluster** is the databases managed by one server instance using a data directory. It does not inherently mean multiple hosts or HA. Within an instance, databases share resources and roles. A session normally operates in one database.

The frontend may be a driver, psql or pool. Each direct client connection has a server backend process. A pool can serve many application clients through fewer server connections; transaction pooling changes which backend handles successive transactions.

**Operational consequence:** connection count, pool queue depth and active queries are different quantities. A connection storm can consume resources before useful throughput increases.

## 3. Processes and their operational meaning

Use pg_stat_activity.backend_type to identify processes visible through PostgreSQL. Presence depends on configuration and current work.

| Process or worker | Purpose | DBRE/SRE investigation |
|---|---|---|
| Supervisor/postmaster | Coordinates server startup and client admission | Startup errors, restart timeline and service status |
| Client backend | Executes work for a direct connection | State, waits, transaction age and connection ownership |
| Checkpointer | Performs checkpoints or restartpoints as appropriate | Checkpoint frequency, write/fsync time and storage contention |
| Background writer | Writes selected dirty shared buffers | Buffer reuse and write activity |
| WAL writer | Writes WAL as configured | WAL activity and flush-related waits |
| Autovacuum launcher/workers | Schedule and perform vacuum/analyze | Maintenance progress, blockers and growing churn |
| WAL sender/receiver | Send or receive physical replication WAL | Transport and replay evidence, not just process presence |
| Parallel/background workers | Support parallel queries and other work | Worker pressure, query plans and extensions |
| Archiver | Invokes configured WAL archival | Failures, archive freshness and WAL retention |
| Startup process | Performs recovery on a recovering instance | Recovery progress and replay waits |

The supervisor is not a normal client activity row. On a self-managed host, authorized OS inspection complements SQL. In containers, PIDs may be from another namespace; managed services may not expose host processes.

An active backend can be waiting. Inspect state together with wait_event_type and wait_event. An idle connection is not necessarily harmless: large counts still require an admission and resource budget.

## 4. Memory: shared and concurrent private demand

| Area or setting | Operational interpretation |
|---|---|
| shared_buffers | Shared database page cache |
| WAL buffers | Shared buffering for WAL records |
| work_mem | Budget for certain executor operations; not a total per-session cap |
| hash_mem_multiplier | Can increase the budget for hash operations relative to work_mem |
| maintenance_work_mem | Budget for selected maintenance operations |
| autovacuum_work_mem | Worker maintenance budget; -1 uses maintenance_work_mem |
| OS cache and other memory | Additional memory outside the shared buffer setting |

A query can contain several memory-consuming operations. Many concurrent queries and workers can create aggregate demand. Settings generally permit allocations when needed; multiplying work_mem by max_connections is neither a guaranteed allocation nor a complete worst-case bound.

Build a budget from representative plans, concurrency, maintenance, process overhead, OS cache and container/host limits. Inspect spill and memory pressure before raising work_mem. Summing process RSS can double-count shared pages.

A container OOM event, host swap activity and SQL temporary-file growth require separate evidence. A large cache alone does not establish healthy memory headroom.

## 5. Storage map

| Location or object | Meaning | Operational note |
|---|---|---|
| base | Default per-database storage | Database OIDs identify directories |
| global | Shared catalogs | Instance-wide metadata |
| pg_wal | WAL segments | Retention can drive disk pressure independently of table growth |
| pg_tblspc | Links to user tablespaces | Include actual target volumes in recovery planning |
| pg_xact / pg_multixact | Transaction-related status | Required internal state; never treat as disposable files |
| Relation heap/index/TOAST | Table contents, indexes and large values | Total relation footprint differs from heap-only size |
| Temporary files | Executor spills | May consume storage beyond durable relation growth |

Use pg_relation_filepath() rather than assuming an OID equals a physical filename. Relations can use multiple files. Configuration and data paths may be separate.

SQL-reported database size is not filesystem capacity. Space planning must include WAL, temporary files, logs, tablespace targets and storage growth. Do not remove files from data directories to reclaim space.

## 6. WAL, commit and checkpoints

WAL records changes needed for recovery. Relevant WAL must be durable before the changed data page is persisted. Crash recovery uses the durable database state and required WAL to reconstruct a consistent state.

Commit acknowledgement depends on configuration:

| Setting or design | Operational implication |
|---|---|
| fsync | Required for PostgreSQL's normal crash-durability guarantees |
| synchronous_commit | Controls commit waiting behavior |
| synchronous_standby_names | Defines candidate synchronous standbys; behavior depends on commit mode |
| Checkpoint policy | Balances write work, WAL/recovery considerations and resource pressure |
| Archiving/slots/standbys | Can require retaining WAL beyond normal recycling needs |

With synchronous_commit=on and no synchronous standby requirement, commit waits for local WAL flush. It does not wait for all changed table pages to reach storage. Asynchronous commit can acknowledge work before its WAL is flushed, allowing recent acknowledged transactions to be lost after a crash.

A checkpoint establishes a recovery position and schedules required dirty-page persistence. It is not a backup, a replica freshness guarantee or a flush of application business workflows.

max_wal_size is a soft limit, not a storage reservation or hard disk ceiling. Retention requirements and other conditions can exceed it. Do not lower it as an emergency substitute for identifying WAL retention.

## 7. A practical diagnosis map

| Symptom | Candidate architectural path | Evidence before action |
|---|---|---|
| Pool queueing | Client admission and backend demand | Pool queues, backend counts and resource headroom |
| High CPU | Executor, planning or workers | Plans, workload and host CPU |
| Slow commits | WAL flush or synchronous replication | Waits, WAL device latency and standby policy |
| Slow reads | Plans, cache misses or storage | Query plans, I/O counters and device metrics |
| Temporary-file growth | Executor spill | Query/workload, temp deltas and memory policy |
| Frequent checkpoints | WAL generation and checkpoint policy | Checkpoint counters, time interval and workload |
| WAL volume growth | Generation or retention | Archival, slots, standby state and disk trend |
| Vacuum backlog | Churn, workers or old transactions | Vacuum progress, transaction age and maintenance settings |

These are hypotheses. A wait sampled once does not prove causality. Avoid resetting statistics during evidence collection.

## 8. Commands and bounded collection

Run [the architecture snapshot](../scripts/002-architecture-snapshot.sql):

~~~bash
psql -X -v ON_ERROR_STOP=1   -f postgresql/scripts/002-architecture-snapshot.sql
~~~

Use an approved observer with CONNECT and suitable monitoring privileges; pg_monitor is broad monitoring access, not a blanket application-data read grant. Restricted settings can produce an error: record it and have an authorized administrator collect the missing portion.

Expected output includes instance identity, backend groups, settings with units, current-database counters, WAL counters and checkpoint counters.

WAL and checkpoint statistics are cumulative. Read them with stats_reset and elapsed time. A high lifetime count is not automatically an incident. Live statistics can lag updates, and observations inside a long transaction can reuse snapshots. Use fresh autocommit queries.

PostgreSQL 18 exposes pg_stat_checkpointer separately; older major versions can have different view layouts. Managed services may restrict settings, host access or available extensions. Use the deployed version's documentation when applying this model to production.

## 9. Production procedure and acceptance

Before collecting, confirm target, environment, role and service impact. Use bounded queries, connection timeout and statement timeout. Keep query text and secrets out of the evidence pack.

Stop on an unexpected target, missing authorization, timeout or unexpected cost. Do not grant yourself privileges, force a checkpoint, reset counters or change fsync as part of this inspection.

Verify that collection ends and leaves no open transaction. Correlate findings with application metrics and storage/host evidence before mitigation.

Pass the linked lab by identifying backend behavior, memory settings and logical storage, demonstrating a small logged write on a disposable primary, and explaining why its WAL delta cannot be attributed exclusively to that session.

**Next:** Chapter 003 — Linux, Networking and Storage Prerequisites.

## 10. Official references

- [Architecture](https://www.postgresql.org/docs/18/tutorial-arch.html)
- [Resource consumption](https://www.postgresql.org/docs/18/runtime-config-resource.html)
- [Database file layout](https://www.postgresql.org/docs/18/storage-file-layout.html)
- [WAL introduction](https://www.postgresql.org/docs/18/wal-intro.html)
- [WAL configuration](https://www.postgresql.org/docs/18/wal-configuration.html)
- [WAL settings and commit policy](https://www.postgresql.org/docs/18/runtime-config-wal.html)
- [Monitoring and statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
