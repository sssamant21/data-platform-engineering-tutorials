# Chapter 06 — PostgreSQL on Bare Metal

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Audience:** DBRE/SRE beginners progressing to host-level PostgreSQL ownership  
**Duration:** 60 minutes · **Reference version:** PostgreSQL 17 · **State:** Authored; runtime and independent review pending

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 06 lab](../labs/chapter-06/README.md) · [Tracker](../STATUS-TRACKER.md)

## 1. Learning outcomes and scope

After this chapter, learners can:

1. Describe the operational responsibilities of a self-managed PostgreSQL server on physical hardware or a Linux VM.
2. Explain the relationships among CPU, RAM, operating system, filesystem, PostgreSQL data directory, WAL, networking and service supervision.
3. Identify the PostgreSQL runtime, configuration and authentication file locations using SQL rather than guessing filesystem paths.
4. Perform safe readiness, capacity, service and observability checks.
5. Distinguish a configuration **reload** from a **restart**, including which changes require downtime.
6. Propose a basic host design and an operational acceptance checklist without treating a container demonstration as bare-metal certification.

**Training boundary:** The hands-on lab uses an isolated PostgreSQL 17 Docker container on Windows or Linux. It emulates several host-level responsibilities but **does not** validate bare-metal disk durability, NUMA, systemd, kernel tuning, networking, or HA. An optional read-only Linux-host checklist is provided for an approved staging VM.

## 2. 60-minute lesson plan

| Time | Topic | Output |
|---|---|---|
| 0–10 min | Self-managed PostgreSQL responsibility model | Owner/RACI sketch |
| 10–20 min | Hardware, storage and Linux architecture | Host deployment diagram |
| 20–30 min | PostgreSQL files, services, networking, configuration and security | Change-control checklist |
| 30–52 min | [Local hands-on lab](../labs/chapter-06/README.md) | Identity, health, config, storage and restart evidence |
| 52–60 min | Troubleshooting, design review and acceptance | Operational go/no-go notes |

## 3. What "bare metal" changes

For PostgreSQL on a dedicated Linux server, the enterprise DBRE/SRE and platform teams must explicitly allocate ownership for the entire host stack.

| Layer | Typical responsible group | Acceptance questions |
|---|---|---|
| Hardware / virtualization | Infrastructure | What are CPU, RAM, failure domains, vendor support and replacement SLAs? |
| OS / kernel / patching | Linux/platform | Who manages kernel security updates, limits, time sync and reboots? |
| Storage | Storage/platform + DBRE | What are IOPS, throughput, latency, durability, filesystem, free-space and failure controls? |
| PostgreSQL packages | DBRE | Which major/minor version, signed packages, repository, rollback and upgrade plan? |
| Data/WAL | DBRE + storage | What are PGDATA and WAL placement, monitoring and capacity thresholds? |
| Authentication / network | DBRE + security + network | Who controls roles, TLS, firewall, pg_hba.conf and secret distribution? |
| HA/DR | DBRE + SRE | What is the topology, independent fencing, recovery process and measured RPO/RTO? |
| Application SQL | Application + DBRE | Who owns schema changes, queries, pooling and transaction retries? |

The physical platform is not inherently more reliable than managed hosting. Reliability depends on **measured recovery**, independent failure domains, storage guarantees, disciplined operations and workload-aware sizing.

## 4. Reference architecture

~~~text
Application / connection pool
        |
        | TLS + authenticated TCP 5432 (restricted network)
        v
Linux host / VM
  ├── systemd service + PostgreSQL server process
  ├── CPU, RAM, OS page cache, filesystem, network
  ├── PostgreSQL shared_buffers and background processes
  ├── PGDATA: base/, global/, pg_wal/, configuration*
  ├── logging, metrics, alerts and audit controls
  └── backups + WAL archive to independent durable storage
          |
          +--> restore testing on separate isolated target
~~~

*Configuration files are often in PGDATA, but packaged Linux installations can keep them elsewhere. Use \`SHOW config_file;\`, \`SHOW hba_file;\`, \`SHOW data_directory;\` and \`SHOW ident_file;\` to discover actual paths.*

**Do not** assume the filesystem containing WAL is independent simply because it is mounted at another path. Verify physical devices, controllers, storage failure domains and persistence guarantees. A separate WAL volume can help certain workloads but is not a universal requirement.

## 5. Host sizing fundamentals

**CPU:** consider active query concurrency, joins/sorts, parallel workers, background maintenance, replication and CPU saturation. More vCPUs do not automatically improve a single-query plan.

**RAM:** consider OS page cache, \`shared_buffers\`, backend/private memory, \`work_mem\` per operation, maintenance tasks and connection count. Never estimate memory as \`work_mem × max_connections\` alone; actual memory usage depends on simultaneous plan nodes and workers. Budget peak behavior with workload evidence.

**Storage:** monitor used/free bytes, data and index growth, WAL generation/retention, temporary files, backup staging, filesystem inodes, latency and write durability. Avoid storage configurations whose write-cache durability semantics are unknown. Maintain headroom for spikes and recovery.

**Network:** use restricted ingress, TLS, DNS and time synchronization. Document connection pooling and expected failover behavior.

**Operating system:** document Linux distribution, filesystem, service unit, package source, kernel/OS limits, cgroups, patch windows and access controls. Change huge pages, transparent huge pages, scheduler or other kernel settings only after platform-specific testing; do not copy generic tuning recipes blindly.

## 6. PostgreSQL files and lifecycle

| Object | Meaning | Safe inspection |
|---|---|---|
| \`data_directory\` / PGDATA | Persistent cluster data | \`SHOW data_directory;\` |
| \`postgresql.conf\` | Server settings | \`SHOW config_file;\` |
| \`pg_hba.conf\` | Client authentication rules | \`SHOW hba_file;\`; inspect \`pg_hba_file_rules\` |
| \`pg_ident.conf\` | User-name mappings | \`SHOW ident_file;\` |
| \`pg_wal/\` | WAL segment files | Inspect path and WAL metrics; never delete WAL files manually |
| \`postmaster.pid\` | Server process lock/state file | Read-only inspection; do not remove to "fix" startup |

PostgreSQL's \`pg_settings\` exposes current values, source and \`pending_restart\`. A change with \`context = 'postmaster'\` requires restart to take effect. Many other settings can be reloaded, but **not all** changes take effect via reload; review parameter context and documented behavior.

~~~sql
SELECT name, setting, unit, source, context, pending_restart
FROM pg_settings
WHERE name IN ('shared_buffers','max_connections','work_mem',
               'logging_collector','wal_level','fsync')
ORDER BY name;
~~~

For a Linux host installed via OS packages, prefer the package-provided **systemd service**. Unit names vary (for example, \`postgresql\` or \`postgresql-17\`); discover them before operating on a service. PostgreSQL must run as an unprivileged database OS account, not root. Never improvise \`kill -9\` or delete \`postmaster.pid\` as routine incident mitigation.

## 7. Networking, authentication and secrets

- Prefer TLS with a verified server identity for remote clients and documented certificate rotation.
- Restrict host firewall and network ACLs; do not expose PostgreSQL directly to the internet.
- Use least-privilege database roles for applications; reserve superuser access for controlled administration.
- Treat \`pg_hba.conf\` as an **ordered** authentication policy; rule ordering matters.
- Review \`pg_hba_file_rules\` for parse errors after planned changes; avoid locking out administration.
- Use approved secrets management and avoid passwords in command histories, shell scripts or logs.
- A loopback-only Docker lab password is **not** a production pattern; Docker environment variables can be inspected by administrators.

## 8. Production change and restart safeguards

**Before a change:** verify cluster identity, primary/standby role, replication state, application owner, change ticket, backup/recovery status, maintenance window, storage headroom and rollback method.

**During:** follow the approved deployment method; use one change at a time; retain timestamps, configuration diffs, service logs and health evidence. For HA, coordinate with the topology manager and independent fencing plan.

**After:** verify readiness, authentication, application connections, latency/error rates, WAL/archive status, replica lag, backups, disk utilization and SLOs.

**Rollback is not always "restart with old config":** schema or data-format changes, major upgrades, extension changes and failed storage operations may require recovery or a separate plan. Treat this chapter's local stop/start demonstration as an exercise in process lifecycle only, not HA or DR validation.

## 9. Hands-on lab

Complete [Chapter 06 — Host Operations Lab](../labs/chapter-06/README.md). It creates a dedicated local container named \`pg-baremetal-ch06\`, with its own Docker volume and host loopback port. It does **not** reuse or mutate earlier chapter databases.

Learners will:

1. Confirm Docker and a safe, unused local lab identity.
2. Start PostgreSQL 17 with persistent storage.
3. Read service readiness, runtime configuration and authentication metadata.
4. Inspect container OS/storage and Docker resource metrics.
5. Create a tiny synthetic health marker and record its count.
6. Perform an optional controlled **local-only** stop/start and verify the marker persisted.
7. Capture sanitized evidence and compare the container lifecycle with native Linux systemd responsibilities.

## 10. Incident scenarios

| Symptom | Investigate first | Avoid |
|---|---|---|
| Database connection refused | Service state, listening port, bind address, firewall, logs | Broadly opening \`5432\` |
| Authentication failed | Username, database, ordered HBA rules, TLS, secret rotation | Setting \`trust\` globally |
| Startup failure | Service logs, permissions, PGDATA identity, disk, configuration | Deleting PID/WAL files blindly |
| High write latency | Storage latency, checkpoints, WAL fsync, host saturation | Disabling \`fsync\` for performance |
| Storage pressure | Data/index growth, WAL retention, archive health, temp files | Manual deletion inside \`pg_wal\` |
| CPU / memory pressure | Query plans, concurrency, background jobs, host metrics | Increasing every setting without workload evidence |

## 11. Acceptance checklist

- [ ] Identify which team owns host, PostgreSQL, backups, HA, security and application schema.
- [ ] Explain PostgreSQL's host process, PGDATA, WAL, configuration and logging paths.
- [ ] Demonstrate safe readiness and read-only configuration inspection.
- [ ] Explain \`pending_restart\` and why a reload is not always sufficient.
- [ ] Record host/container storage and resource observations with their limitations.
- [ ] Verify the local synthetic marker remains after an optional controlled restart.
- [ ] Distinguish local persistence from validated backup, PITR, failover or durability.
- [ ] Provide an operational readiness and rollback checklist for a **hypothetical** staging server.
- [ ] Retain real execution evidence before marking the lab verified.

**Publication state:** chapter and lab instructions are authored. No live execution, independent review, or production certification is asserted.

## 12. Official references

- [PostgreSQL 17: Server Setup and Operation](https://www.postgresql.org/docs/17/runtime.html)
- [PostgreSQL 17: Starting the Database Server](https://www.postgresql.org/docs/17/server-start.html)
- [PostgreSQL 17: File Locations](https://www.postgresql.org/docs/17/runtime-config-file-locations.html)
- [PostgreSQL 17: Database File Layout](https://www.postgresql.org/docs/17/storage-file-layout.html)
- [PostgreSQL 17: pg_hba.conf](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html)
- [PostgreSQL 17: pg_ctl](https://www.postgresql.org/docs/17/app-pg-ctl.html)
- [PostgreSQL 17: pg_settings](https://www.postgresql.org/docs/17/view-pg-settings.html)
- [PostgreSQL 17: Monitoring Statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
