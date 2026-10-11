# 004 — Build a Reproducible PostgreSQL Operations Lab

[Master plan](../MASTER-PLAN.md) · [Previous chapter](003-linux-networking-and-storage-prerequisites.md) · [Hands-on lab](../labs/004-reproducible-postgresql-operations-lab.md) · [Setup/control script](../scripts/004-operations-lab.sh)

## 1. Operational problem

A useful operations lab must let another engineer reproduce the same topology, identify every instance, verify data movement and remove only its own resources. Three databases created inside one instance do not simulate a primary and two standbys.

This chapter creates **three PostgreSQL 18 instances** on a single disposable Linux host: a primary and two asynchronous streaming standbys. Each has a separate data directory, port and log.

**Audience:** DBRE/SRE only.  
**Prerequisites:** Chapters 001–003, PostgreSQL 18 server binaries and Python 3 installed, Bash and a non-root lab OS account.  
**Estimated effort:** 60–90 minutes.  
**Scope:** local development and failure exercises, not a production deployment template.

## 2. Learning objectives

- Build separate server instances from one documented procedure.
- Bootstrap physical standbys from a running primary.
- Verify writable/recovery roles and streaming replication.
- Demonstrate that a primary write becomes visible on both readers.
- Use administrative, replication, monitoring and application roles appropriately.
- Stop/restart the lab without confusing processes or deleting live data.
- Record exact versions and limitations before later experiments.

## 3. Topology and resource budget

| Instance | Address | Data directory | Intended role |
|---|---|---|---|
| Primary | 127.0.0.1:55432 | PG_LAB_ROOT/primary | Writable primary |
| Standby 1 | 127.0.0.1:55433 | PG_LAB_ROOT/standby1 | Read-only physical standby |
| Standby 2 | 127.0.0.1:55434 | PG_LAB_ROOT/standby2 | Read-only physical standby |

All three share one host and storage failure domain. Losing that host can lose the entire lab. This is a teaching topology, not HA qualification or a backup strategy.

Start with a small workload. A disposable VM with approximately 2 CPU cores, 4 GiB RAM and 10 GiB free disk is a reasonable starting point for these exercises, not a production sizing rule. Actual demand depends on the workload and retained WAL. Monitor free space.

The script uses 64 MiB shared_buffers and 30 connections per instance to limit the initial footprint. Aggregate resource use includes all three servers, their private allocations and OS overhead.

## 4. Prerequisites and installation boundary

Use an approved PostgreSQL 18 package or build for your Linux distribution. This chapter does not alter distribution package repositories, auto-created system services or existing installations.

If tools live in a version-specific directory, add that verified directory to PATH. Example on some Debian-family installations:

~~~bash
export PATH="/usr/lib/postgresql/18/bin:$PATH"
~~~

Verify the tools:

~~~bash
initdb --version
pg_ctl --version
psql --version
pg_basebackup --version
python3 --version
~~~

All PostgreSQL tools must report major version 18. Record exact minor versions and package provenance. Do not use PostgreSQL 17 initdb with an 18 server or reuse an older data directory.

On Windows, run these instructions inside a Linux VM or WSL with PostgreSQL 18 binaries installed **inside that environment**. Use its Linux filesystem for the lab. Native Windows service management and platform-specific paths require a separate adapted procedure.

Do not run initdb as root. Use a dedicated unprivileged OS account on an isolated development host. Only the package-installation stage, if needed, belongs to an administrator.

## 5. What setup performs

The script:

1. Verifies the required major version and rejects root execution.
2. Checks loopback ports 55432–55434 before creating anything.
3. Creates a unique private directory under /tmp and a lab marker.
4. Generates random local passwords with restrictive file permissions.
5. Initializes the primary with checksums, UTF-8 and explicit SCRAM authentication.
6. Starts the primary and creates the ops_lab database and lab roles.
7. Takes two sequential streamed base backups and writes standby configuration.
8. Overrides each copied standby's port and starts it.
9. Verifies server roles and a replicated probe row.

Setup refuses to overwrite an existing PG_LAB_ROOT. Do not delete another lab or data directory to work around that guard.

The directory is deliberately transient: /tmp can be cleaned by the OS or reboot policy. Retain reusable source code and nonsecret evidence in the repository; recreate the lab when its temporary files are gone.

## 6. Authentication and role separation

| Role | Purpose | Privilege boundary |
|---|---|---|
| lab_admin | Initialization and controlled lab administration | Lab-only superuser |
| lab_repl | Physical base backup and replication | LOGIN + REPLICATION; not superuser |
| lab_observer | Diagnostic metadata | LOGIN + pg_monitor |
| lab_app | Later application exercises | Owns ops_lab; specific privileges on the probe |

The lab's owning OS account can read all its generated credentials. This is appropriate for a single-operator disposable exercise, not a production secrets architecture.

credentials.pgpass has mode 0600. Replication uses the physical-replication password-file match and a passfile reference in the standby connection configuration. Passwords are not printed or placed in process arguments.

The script restricts TCP listeners to loopback. It explicitly disables TLS for this local lab; do not expose the ports remotely or copy that choice into production. Production TLS, access controls and rotation are covered in later chapters.

If setup fails during bootstrap, protected temporary password/SQL files can remain for diagnosis and must be removed when the lab is destroyed. Never commit the lab root, credential file or raw sensitive logs.

## 7. Replication design and its limits

pg_basebackup takes a physical copy over the replication protocol. The lab uses -X stream so required WAL is included, and -R to create standby.signal and connection configuration.

Streaming the backup needs more than one WAL sender connection. The configured sender capacity supports the small sequential bootstrap plus connected standbys.

The lab uses asynchronous replication. Local synchronous_commit=on does not by itself require remote acknowledgement because no synchronous standby policy is set.

No persistent replication slots are created. wal_keep_size offers limited retention for brief interruptions; it is not a guarantee that a stopped standby can always catch up. If required WAL has been recycled, rebuild that standby using the later documented procedure or recreate this entire disposable lab.

Long-term backup, archiving, PITR, synchronous replication, promotion, fencing and rejoin are separate chapters. Do not promote either standby as part of this setup.

## 8. Verification: readiness versus correctness

The verification command checks:

- Primary recovery state is false.
- Both standby recovery states are true.
- Two named senders are streaming.
- A new token written to the designated probe table is visible on both standbys.

It polls up to 30 attempts rather than assuming immediate visibility. Connection timeouts are bounded separately, so total failure duration can exceed 30 seconds.

A successful check proves replication of that probe under the observed conditions. It does not prove an RPO/RTO objective, no data loss during failover or protection from host/storage failure.

Verification **writes one probe row on the primary**. It is not a read-only production health script. Later read-only monitoring must distinguish inspection from synthetic writes.

## 9. Start, stop and recovery boundaries

Use the script's start/stop actions only for this marked lab. Stops use fast shutdown: existing transactions can be rolled back and clients disconnected, followed by a clean server shutdown.

Start is idempotent for already running lab instances and reruns verification. It does not automatically repair a broken standby, undo promotion or migrate incompatible binaries.

If setup fails, retain the printed lab root and logs. Stop any started instances using that root. Investigate before attempting another fresh setup.

Destroy requires an explicit environment flag, validates the owned directory and marker, stops instances and refuses nested mounts before deleting the lab root. Destruction is irreversible for these disposable data files; recreate them from source rather than expecting recovery.

## 10. Monitoring and troubleshooting

| Symptom | Likely category | Next step |
|---|---|---|
| Tool missing or wrong version | Installation/PATH | Verify installed PostgreSQL 18 binary directory |
| Refused root execution | OS identity | Use the intended non-root lab account |
| Port unavailable | Existing listener | Identify the listener; do not kill unrelated processes |
| initdb/start failure | Permissions, resources, config | Inspect the specific lab log and Chapter 003 evidence |
| Authentication failure | Password match/HBA | Check file permissions, host/port/role and replication entry |
| Copied standby port conflicts | Configuration | Verify final port setting in that standby's config |
| No streaming sender | Receiver/network/authentication | Inspect standby log and primary replication view |
| Required WAL removed | Retention gap | Plan a rebuild; do not delete pg_wal or fake progress |
| Probe never appears | Replay/receiver/topology | Confirm endpoints, logs and replay state |
| Old /tmp directory disappears | Transient storage | Recreate the lab; retain source/evidence separately |

Monitor lab disk/WAL growth, database processes and logs before later fault injection. Stop the exercise if it affects other services or approaches resource exhaustion.

## 11. Acceptance and next chapter

Complete the linked lab and retain versions, topology, two replication rows, probe results and successful stop/start evidence.

Authorship and static validation do not constitute executed acceptance. Mark lab verified only with actual runtime evidence.

**Next:** Chapter 005 — psql, System Catalogs and Safe Administrative SQL.

## 12. Official references

- [initdb](https://www.postgresql.org/docs/18/app-initdb.html)
- [pg_ctl](https://www.postgresql.org/docs/18/app-pg-ctl.html)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [Streaming standbys](https://www.postgresql.org/docs/18/warm-standby.html)
- [Replication settings](https://www.postgresql.org/docs/18/runtime-config-replication.html)
- [Password files](https://www.postgresql.org/docs/18/libpq-pgpass.html)
- [Authentication rules](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)
