# Chapter 041 — PostgreSQL Backup Architecture and Recovery Objectives

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Draft; lab validation pending

## 1. Mission and learning outcomes

Design a recoverable PostgreSQL service that meets measurable **recovery point objective (RPO)** and **recovery time objective (RTO)** requirements. Distinguish physical and logical backups, WAL archiving and point-in-time recovery (PITR); document dependencies and retention; verify backups by restoring them; and prepare an incident runbook.

**Principle:** A backup job reporting success is not proof that recovery works. Recovery confidence comes from independent restore tests, integrity checks and measured restore times.

## 2. RPO, RTO and recovery scenarios

- **RPO:** maximum acceptable data loss measured in time. Example: 15-minute RPO means recovery must not lose more than 15 minutes of committed data under the defined failure scenario.
- **RTO:** maximum acceptable elapsed time to restore service. Example: a 60-minute RTO includes detection, decision, provisioning, restoring, replaying WAL, validating and reopening traffic.
- **Backup retention:** how long usable recovery points are preserved. This is not the same as the number of daily backup files.
- **Recovery granularity:** full cluster, database, selected objects, or a particular timestamp/LSN.

| Incident | Likely recovery path | Key limitation |
|---|---|---|
| Accidental DELETE of one table | Restore logical backup to isolated database; reconcile data | Backup freshness and row-level reconciliation |
| Whole-node loss | Physical base backup + WAL, or promoted healthy replica | Replica lag, WAL continuity, infrastructure recovery |
| Bad deployment discovered later | PITR to isolated instance; compare and reconcile | PITR restores an entire cluster state, not one table in place |
| Corrupt/missing backup | Alternate independent copy and tested restore | Backups are not guaranteed valid without tests |
| Regional outage | Cross-region backups/replication with independent credentials | Network, regional isolation and failover RPO/RTO |

A streaming replica is not a substitute for independent backups: logical corruption and accidental changes can replicate.

## 3. Backup architecture

```text
PostgreSQL primary
  |-- physical base backup (pg_basebackup or managed backup tooling)
  |-- continuous WAL archive -> durable independent storage
  |-- logical exports (pg_dump/pg_dumpall) for object-level portability
  |-- streaming replicas for availability, not independent recovery history
                       |
                  restore rehearsal
                       |
                isolated restore target
                       |
             integrity + application validation
```

**Physical:** captures a cluster-level data directory, requires compatible PostgreSQL binaries/environment and the WAL needed for consistency and requested PITR. `pg_basebackup` provides a base backup; the archive chain must cover the required recovery window.

**Logical:** `pg_dump` exports a database or selected objects; `pg_dumpall --globals-only` can capture cluster roles/tablespaces, which a single-database dump does not include. Logical dumps do not provide arbitrary PITR, and a selective table dump may omit external dependencies. Logical restore time depends on indexes, constraints, data volume and parallelism.

**Managed PostgreSQL:** provider snapshots/PITR can change procedures, retention and permissions. Verify the actual service's restore semantics, rather than assuming self-managed commands apply unchanged.

## 4. WAL archiving and PITR

PostgreSQL records changes in WAL. Physical PITR requires a valid base backup and an uninterrupted sequence of WAL files through the recovery target. In self-managed deployments, review `wal_level`, `archive_mode`, `archive_command` or `archive_library`, archiver health and storage durability.

```sql
SELECT name,setting,unit,source
FROM pg_settings
WHERE name IN ('wal_level','archive_mode','archive_command',
               'archive_timeout','max_wal_senders','wal_keep_size')
ORDER BY name;

SELECT archived_count,last_archived_wal,last_archived_time,
       failed_count,last_failed_wal,last_failed_time
FROM pg_stat_archiver;
```

Archive success counters alone cannot prove every required WAL segment is present. Validate storage manifests, archive continuity and restoration from the actual archive location. A failing archive may eventually fill local WAL storage; watch disk headroom and slot retention.

PITR is performed on an isolated restored physical cluster using the appropriate `restore_command`, recovery target and recovery signal mechanism. Do not attempt PITR directly on a running production primary or assume an exact wall-clock target corresponds to a known committed transaction without verification.

## 5. Recovery design worksheet

| Service | Target RPO | Target RTO | Recovery source | Verification | Owner |
|---|---|---|---|---|---|
| Example critical database | 15 min | 60 min | Base backup + WAL archive | Monthly isolated PITR drill | DBRE |
| Example noncritical dataset | 24 h | 4 h | Daily logical export | Scheduled restore test | Data team |

These targets are **illustrative**, not promises. Calculate observed recovery time as detection + authorization + provision + restore + WAL replay + integrity/application validation + traffic cutover. Test worst-case database size and cross-region transfer speed. Capture achieved recovery timestamp/LSN to measure actual RPO.

## 6. Retention, security and resilience

- Keep backup storage in a separate failure domain with least-privilege credentials and encryption in transit/at rest.
- Consider immutable/object-locked copies and an independent account to reduce ransomware and operator-error exposure.
- Protect secrets and backup contents as production data; test access without exposing credentials in shell history.
- Define retention by business, compliance and recovery requirements; include full backups and required WAL continuity.
- Verify checksums, backup manifests, object completeness, role/extension dependencies and restore logs.
- Alert on missed schedules, archive failures, age of last successful restore test, restore duration, unexpected backup size and storage consumption.

## 7. Incident runbook

1. **Declare and scope:** classify accidental modification, infrastructure loss, corruption, ransomware or regional failure. Preserve evidence and stop additional damaging writes where safe.
2. **Choose recovery point:** record requested timestamp/LSN, available backup chain, expected data loss and business approval.
3. **Protect source:** preserve backup/archival artifacts and current logs; do not overwrite a healthy source or destroy forensic evidence.
4. **Restore isolated:** provision clean target, restore backup, replay WAL if needed, and keep traffic isolated.
5. **Validate:** compare critical tables, row counts, checksums where meaningful, roles/extensions, query plans and application invariants.
6. **Cut over:** coordinate application connection changes and write fencing to prevent split brain; monitor latency, errors, replicas and ingestion.
7. **Close:** measure achieved RPO/RTO, document gaps and schedule preventive actions.

For a single-table accidental deletion, restoring a separate copy and selectively reconciling rows is often safer than rolling back the entire production cluster.

## 8. Hands-on lab

[Chapter 041 lab](../labs/041-postgresql-backup-architecture-and-recovery-objectives-lab.md) creates an isolated fixture, takes a custom-format logical dump, restores into a second schema/database context, validates rows and records measured restore duration. Physical backup and PITR are designed as a separate exercise requiring a disposable cluster with WAL archiving configured.

**Acceptance:** explain recovery method by failure type; calculate RPO/RTO; identify WAL archive continuity risks; demonstrate an independent logical restore and verify counts; document access controls and retention.

**Runtime validation:** pending. No claim of an executed backup/restore test.

## Official references

- [Backup and restore](https://www.postgresql.org/docs/18/backup.html)
- [Continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)

**Next:** Chapter 042 — Logical Backups with pg_dump, pg_restore and pg_dumpall.
