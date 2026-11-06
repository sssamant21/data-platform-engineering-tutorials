# Chapter 11 — Backup, Restore, PITR and Disaster Recovery

**Audience:** PostgreSQL DBRE/SRE and platform engineers  
**Level:** Intermediate · **Session:** 60 minutes · **Reference runtime:** PostgreSQL 17  
**Status:** Authored; no runtime execution, independent approval, or production certification

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 11 lab](../labs/chapter-11/README.md) · [Progress tracker](../STATUS-TRACKER.md)

## 1. Learning outcomes and agenda

By the end, engineers should be able to:

1. Distinguish logical backups, physical base backups, WAL archiving, PITR and replication.
2. Explain how a base backup plus a continuous WAL chain enables point-in-time recovery.
3. Inspect backup/archive health and interpret the limitations of a successful backup command.
4. Perform an **isolated** physical restore to a named recovery point with PostgreSQL 17.
5. Define RPO/RTO, measure a bounded lab restore interval, and distinguish it from enterprise disaster-recovery acceptance.
6. Describe recovery ownership and guardrails across self-managed PostgreSQL, AWS RDS and Kubernetes operators.

| Minutes | Topic | Output |
|---|---|---|
| 0–10 | Backup types, business objectives and failure scenarios | Recovery requirements |
| 10–20 | WAL archive architecture, base backups and timelines | Recovery sequence |
| 20–30 | Restore verification, RPO/RTO and operational safety | Acceptance criteria |
| 30–53 | [Isolated Chapter 11 lab](../labs/chapter-11/README.md) | Backup, named PITR, evidence |
| 53–60 | Incident decision table and design review | Recovery runbook notes |

**Prerequisites:** Chapters 03–04 (transactions and WAL), Chapter 10 (replication), local Docker Engine/Desktop with Linux containers, and enough local disk for several PostgreSQL 17 volumes. The lab is a teaching exercise on a **single host**, not an enterprise DR rehearsal.

## 2. Start with business requirements, not a backup tool

- **RPO (Recovery Point Objective):** maximum acceptable data loss expressed as a time interval. Example requirement: at most 15 minutes of acknowledged business writes may be lost after a qualifying disaster.
- **RTO (Recovery Time Objective):** maximum acceptable time until the business service is restored after a qualifying incident. It includes detection, declaration, authorization, recovery, application reconnect and verification—not just PostgreSQL startup.
- **Recovery retention:** how far back a valid recovery point must be available.
- **Recovery scope:** a table, a database, a whole PostgreSQL cluster, a zone or a region.
- **Recovery integrity:** whether recovered data passes referential, application, and reconciliation checks.

Define these with application owners, business continuity, security and compliance. A database administrator should not silently choose acceptable data loss.

### Common scenarios

| Incident | Candidate recovery approach | Caution |
|---|---|---|
| Accidentally deleted a few rows | Restore separate copy to before the error; reconcile/export approved rows | Do not rewind the production cluster without approval |
| Entire instance/storage lost | Physical base backup plus archived WAL, or managed restore | Requires off-host durable copies and validated restore |
| Logical corruption propagated to replicas | PITR to a point before corruption | Replicas may have replayed the same bad change |
| Region outage | Cross-region backups/restore or independently designed DR | Same-host/same-region copies are not regional DR |
| One service needs selected tables | Logical dump/restore or isolated PITR plus selective extraction | Physical PITR restores a whole cluster, not a single table in place |

## 3. Three distinct backup and recovery mechanisms

### Logical backup: pg_dump / pg_restore

A logical backup exports schema/data from a selected database. It is useful for selected-database restore, migration and portability within supported compatibility boundaries. It is **not** a physical base backup and cannot be replayed with archived WAL for PITR.

~~~powershell
# Illustrative command for a known disposable PostgreSQL container:
docker exec pg-fleet-lab pg_dump -U postgres -d appdb -Fc -f /tmp/appdb.dump
~~~

A successful dump file is not proof of a usable restore; validate it on a different, isolated database and compare expected objects and data.

### Physical base backup: pg_basebackup

A physical backup copies the PostgreSQL **cluster** files. PostgreSQL can recover a base backup by replaying the necessary WAL. A backup manifest and the matching-version `pg_verifybackup` tool can check file integrity and required backup WAL, but even a passing verification cannot replace an actual restore test.

### Continuous WAL archive: PITR

WAL archives contain changes between base backups. A consistent **base backup + uninterrupted required WAL** can be recovered to a named restore point, timestamp, LSN or transaction ID (with relevant limitations).

~~~text
                 PostgreSQL PRIMARY
                 transactions + WAL
                       |
             +---------+---------+
             |                   |
       pg_basebackup       archive_command
             |                   |
       physical base         completed WAL
             |                   |
             +---------+---------+
                       |
                protected backups
                       |
           isolated recovery environment
                       |
             restore base files
             create recovery.signal
             configure restore_command
             choose recovery target
                       |
                 WAL replay
                       |
             verify restored data
                       |
          approved routing / cutover
~~~

The WAL archive must be independent of the primary's failure domain in real systems. The chapter lab intentionally shares a Docker host, so it proves only recovery mechanics.

## 4. Recovery prerequisites and failure modes

A recoverable physical archive chain requires:

- A valid physical base backup for the correct PostgreSQL major version and system identifier.
- The WAL records needed from the backup's start through the chosen recovery point, including timeline history when relevant.
- Access to encryption keys, backup credentials, required extensions, tablespace mounts and configuration.
- A destination that does not overwrite the running source, with matching supported binaries and adequate disk.
- Recovery target semantics chosen deliberately; restoring beyond a destructive statement recreates the damage.
- Documented ownership of backups, retention, immutable storage, access controls and restore evidence.

**Important:** PostgreSQL WAL archiving does not automatically preserve external configuration edits, secrets, TLS material, infrastructure definitions or application-side data. Back them up through approved separate processes.

### Archive command safety

A production archive command must report success **only when a WAL segment has been durably preserved**. Do not overwrite a different existing segment with the same name. Monitor archive failures and lag; when archiving cannot keep up, WAL accumulation can exhaust disk.

~~~sql
-- Read-only diagnostics (run as an appropriately privileged operator)
SHOW archive_mode;
SHOW archive_command;
SELECT archived_count, last_archived_wal, last_archived_time,
       failed_count, last_failed_wal, last_failed_time
FROM pg_stat_archiver;
SELECT pg_current_wal_lsn() AS primary_lsn;
~~~

These metrics are indicators, not an end-to-end guarantee. `pg_stat_archiver` counters may be reset; an idle server may legitimately have no recent archive event. Avoid treating archive count alone as a passing DR test.

## 5. Recovery target and timeline fundamentals

In PostgreSQL 17, a physical PITR recovery uses a `recovery.signal` file, a `restore_command`, and a recovery target such as `recovery_target_name` or `recovery_target_time`. A named restore point can be written with `pg_create_restore_point`, which requires suitable privileges and WAL settings.

When a recovery completes and a new primary is created, it follows a **new timeline**. This does not make the original primary and recovered copy safe to write simultaneously: a controlled production cutover needs independently verified fencing, routing controls and a plan for the old primary.

**Safe teaching pattern:** stop the source lab primary before starting the restored writable container. The lab never points an application at both copies.

## 6. RPO/RTO evidence: what counts?

A **successful backup** is not a recovery result. A **passing pg_verifybackup** is not a booted server. A **booted server** is not a validated business service.

### A recovery test should retain

1. Incident or drill ID, source system ID, PostgreSQL version, environment and approvers.
2. Business-approved RPO and RTO targets and scope of failure scenario.
3. Backup identifier, base backup timestamp, WAL coverage, checksums/manifest status and restore tool versions.
4. Recovery target selection, archive continuity and timeline evidence.
5. Actual start/end timestamps for detection, authorization, restore, PostgreSQL availability, application validation and routing.
6. Last business-acknowledged transaction before failure and last recovered transaction, to calculate observed loss against RPO.
7. Integrity checks: counts, checksums where appropriate, schema/constraints, reconciliation and application functional tests.
8. Owner sign-off and documented exceptions.

**Measurement caution:** the Chapter 11 lab records a bounded **restore-start-to-verified-query** elapsed interval and demonstrates which rows are included/excluded at a named point. It does **not** establish a real incident RTO or a measured disaster RPO: there is no real failure, independent backup site, application routing, or approved loss boundary.

## 7. Cross-platform responsibility matrix

| Control | Bare metal / VM | Amazon RDS PostgreSQL | Kubernetes PostgreSQL operator |
|---|---|---|---|
| Backup orchestration | DBRE/platform-owned | RDS automated backups/snapshots under customer policy | Operator/backup tooling under DBRE/platform policy |
| WAL archiving | DBRE configures and monitors | Managed mechanism and service-specific PITR limits | Operator/object-store integration; verify configuration |
| Restore environment | Separate VM/storage and matching binaries | Restore into a **new** RDS instance/cluster as supported | Isolated operator-managed cluster/PVC and object storage |
| Security | Off-host encryption, key custody, least privilege | IAM/KMS/network and data access ownership | Secrets, object-store identity, RBAC, storage access |
| Recovery certification | Joint DBRE, app, change and business review | Customer still owns app validation and objectives | Joint DBRE, operator and application review |

RDS and operator PITR features differ by deployment mode, version, backup configuration and retention. Do not copy self-managed `pg_basebackup` procedures directly into managed services without consulting their supported recovery workflows. AWS restoration may incur charges; no AWS resources are created in this lab.

## 8. Incident and troubleshooting guide

| Symptom | Investigate | Safe next step |
|---|---|---|
| `archive_mode = off` | Configuration, startup settings and backup policy | Plan reviewed configuration change in non-production |
| `failed_count` increasing | Archive permissions, target storage, errors and capacity | Protect WAL and fix archival path; don't delete WAL files manually |
| Backup exists but `pg_verifybackup` fails | Missing files, manifest, WAL, version mismatch | Quarantine backup and use a verified alternative |
| Recovery cannot find a WAL file | Archive gaps, wrong timeline, retention expiry | Stop and investigate continuity; don't fabricate a WAL file |
| Recovery target not reached | Wrong target or incomplete WAL | Inspect startup logs and target name/time, do not promote blindly |
| Restored instance starts but app fails | Roles, extensions, secrets, endpoint, schema, external dependencies | Validate on isolated endpoint with app owner |
| Restore exceeds RTO | Backup location, bandwidth, replay volume, process latency | Record actual bottleneck and revise architecture/targets |

Never issue `pg_resetwal`, remove archived WAL, delete replication slots, promote an uncontrolled replica, or overwrite production PGDATA as an incident shortcut.

## 9. Hands-on exercise and acceptance

Follow the [Chapter 11 lab](../labs/chapter-11/README.md). It creates dedicated `pg-ch11-*` resources and does not reuse Chapter 10's replication topology.

- [ ] Explain why `pg_dump` alone cannot provide WAL-based PITR.
- [ ] Capture PostgreSQL version, archive configuration and archive health.
- [ ] Create and verify a physical base backup with `pg_basebackup` / `pg_verifybackup`.
- [ ] Insert a row **after** the base backup, mark a safe restore point, then apply a synthetic bad change.
- [ ] Verify the relevant WAL segment reached the archive.
- [ ] Stop the source before starting a restored writable instance.
- [ ] Recover to the named point, showing the safe row is present and the later bad change is absent.
- [ ] Record bounded restore elapsed time and explain why it is not an enterprise RTO.
- [ ] Record actual runtime evidence only if executed; retain review and approval status separately.

**Publication status:** lesson and lab are authored; runtime execution, independent review and production certification are not complete.

## 10. Official references

- [PostgreSQL 18 — Backup and Restore](https://www.postgresql.org/docs/18/backup.html)
- [PostgreSQL 18 — Continuous Archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18 — pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [PostgreSQL 18 — pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [PostgreSQL 18 — Recovery Target Settings](https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET)
- [Amazon RDS for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [CloudNativePG backup and recovery documentation](https://cloudnative-pg.io/docs/)
