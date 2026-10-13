# Chapter 061 — PostgreSQL Backup Strategy, RPO and RTO Fundamentals

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Design PostgreSQL backups from business recovery objectives rather than from a cron schedule. Select logical, physical, WAL-based and managed-service protection appropriately; calculate recovery coverage, prove recoverability in isolation, and document an actionable restoration decision tree.

This chapter begins the backup and disaster recovery track after [Chapter 060 — Connection Pooling Acceptance](060-postgresql-connection-pooling-and-availability-acceptance-project.md).

## 2. Define RPO and RTO precisely

- **RPO (Recovery Point Objective):** maximum acceptable data loss, measured as time between the most recent recoverable consistent point and the incident.
- **RTO (Recovery Time Objective):** maximum acceptable elapsed time to restore the required service, including detection, decision, provisioning, data recovery, validation and application cutover.
- **Actual recovery point:** latest recoverable timestamp/LSN supported by a valid base backup plus an unbroken WAL chain or by a verified backup artifact.
- **Actual recovery duration:** measured in a timed drill, not inferred from backup job runtime.

Example: RPO = 15 minutes and RTO = 2 hours. A nightly logical dump does **not** meet a 15-minute RPO on its own. A physical base backup plus continuous WAL archiving *may* meet it if archive lag, retention and restore validation satisfy the target. A backup completing successfully does not prove restore correctness.

## 3. Protection methods and tradeoffs

| Method | Best use | Recovery granularity | Important limits |
|---|---|---|---|
| `pg_dump` / `pg_restore` | Portable database/object restore, migration | Database/object | Does not provide continuous PITR; excludes cluster-global roles |
| `pg_dumpall --globals-only` | Roles and global objects | Cluster globals | Secure handling of role definitions; restore ordering |
| `pg_basebackup` | Physical cluster backup | Cluster-wide base | Needs WAL for consistency and later PITR |
| Base backup + WAL archive | PITR and full cluster recovery | Time/LSN target | Continuous WAL chain and matching timeline required |
| Storage snapshots | Fast volume recovery when consistent | Snapshot point | Multi-volume consistency and WAL integration essential |
| Managed-service backups | Platform-native retention/PITR | Provider-dependent | Check RPO/RTO, region, encryption, export and restore behavior |
| Replica | High availability / read scaling | Current replicated state | **Not a backup**: deletes/corruption can replicate |

A backup strategy typically combines physical backup/PITR for cluster disaster recovery, logical backups for selective recovery and independently protected copies for ransomware or operator error.

## 4. PostgreSQL WAL and PITR fundamentals

PostgreSQL WAL records changes required for crash recovery and continuous archive recovery. A valid physical base backup plus **all required WAL segments** enables replay to a target timestamp, transaction ID, restore point or LSN (depending on supported recovery settings). Missing WAL breaks the recovery chain.

Key settings and evidence:

```sql
SELECT name,setting,unit,context,pending_restart
FROM pg_settings
WHERE name IN (
 'wal_level','archive_mode','archive_command','archive_library',
 'archive_timeout','full_page_writes','max_wal_senders',
 'max_replication_slots','wal_keep_size'
)
ORDER BY name;

SELECT archived_count,last_archived_wal,last_archived_time,
       failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;
```

`archive_mode=on` without a functional `archive_command` or `archive_library` does not prove recoverability. Archive success counters are operational indicators, **not** end-to-end restore validation. `pg_stat_archiver` counters may reset; compare rates within known measurement windows.

## 5. Recovery coverage model

```text
Recoverable interval:
    valid base backup
       + every WAL segment needed for consistency and target replay
       + timeline history where required
       + accessible encryption keys and credentials
       + verified restoration tooling
```

Do not delete a base backup or archived WAL solely because it is older than a fixed number of days. Retention must preserve every WAL segment needed by the oldest retained recovery base and any active recovery requirements. Validate backup dependency chains, timeline switches and immutable/offsite copies.

## 6. Backup design checklist

1. **Inventory:** database size, growth, write rate, WAL generation, peak load, object storage and replication topology.
2. **Objectives:** RPO/RTO per service tier, business hours, compliance retention and regional disaster scenarios.
3. **Methods:** physical base backup frequency, continuous WAL archiving, logical exports where required, snapshot consistency.
4. **Security:** encrypted transit/storage, KMS/key recovery, least-privilege backup identities, access logs and separation of duties.
5. **Resilience:** offsite/cross-region copies, immutable or write-protected copies, independent credentials and restore infrastructure.
6. **Performance:** backup I/O throttling, compression, concurrency, network throughput and recovery parallelism.
7. **Observability:** age of latest valid backup, archive failures/lag, backup duration, storage growth, restore drill age and failed verification.
8. **Lifecycle:** version compatibility, extension availability, global objects, ownership, tablespaces and decommissioning.

## 7. Estimate restore time

```text
RTO ≈ detection + authorization + provisioning
    + data transfer + restore/replay + validation + cutover
```

Illustration: 10 min detection + 10 min decision + 15 min provisioning + 40 min restore + 15 min WAL replay + 10 min verification/cutover = 100 min. This meets a 120-minute objective **only if actual drill measurements confirm each step**. Large indexes, slow object storage, WAL replay, schema validation and application reconnection can dominate.

## 8. Common failure modes

| Failure | Why backups fail | Preventive control |
|---|---|---|
| Missing WAL segment | Broken PITR chain | Archive-lag monitoring and restore drills |
| Backup completed but unreadable | Corruption/incomplete copy | Checksums/manifests and isolated restore |
| Lost KMS key | Encrypted copy inaccessible | Key lifecycle and recovery rehearsal |
| Logical dump misses roles | Cluster globals separate | `pg_dumpall --globals-only` and restore plan |
| Snapshot inconsistent across volumes | No coordinated consistency point | Provider-supported coordinated snapshot method |
| Backup stored in same blast radius | Ransomware/operator error | Offsite/immutable copy and separate credentials |
| Restore exceeds RTO | Transfer/replay/provisioning too slow | Timed drills and capacity modeling |
| Replica assumed to be backup | Deletes propagate | Independent historical backups |

## 9. Production incident recovery decision tree

- **Single table accidentally deleted:** evaluate logical object restore into a separate database, then controlled data reconciliation. Avoid overwriting the live cluster.
- **Database corruption or lost primary:** use a verified physical base backup plus WAL and restore to isolated infrastructure; validate consistency before routing writes.
- **Region loss:** invoke cross-region backups and separately recoverable encryption keys; verify DNS, network and client configuration.
- **Ransomware:** isolate compromised identities, preserve evidence and restore from independently protected, known-clean backups.

Never execute a destructive restore over the original production data directory without a separately approved, validated recovery plan.

## 10. Lab and acceptance

The [Chapter 061 lab](../labs/061-postgresql-backup-strategy-rpo-and-rto-fundamentals-lab.md) includes read-only configuration inspection, a disposable `pg_dump`/`pg_restore` exercise, and an RPO/RTO acceptance worksheet. The [inspection SQL](../labs/sql/061-backup-inspect.sql) does not modify server configuration.

**Acceptance:** objectives documented, backup scope complete, recovery artifact integrity checked, isolated restore verified, WAL/archive dependencies assessed and actual RPO/RTO measured. **Runtime:** pending.

## Official references

- [PostgreSQL backup and restore](https://www.postgresql.org/docs/18/backup.html)
- [SQL dump](https://www.postgresql.org/docs/18/backup-dump.html)
- [Continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)

**Next:** Chapter 062 — PostgreSQL Logical Backups with pg_dump, pg_restore and pg_dumpall.
