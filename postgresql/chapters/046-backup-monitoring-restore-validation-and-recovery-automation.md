# Chapter 046 — Backup Monitoring, Restore Validation and Recovery Automation

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Move from ad hoc backup jobs to an evidence-backed backup reliability program: continuously monitor backup and WAL archive freshness, validate backup artifacts, rehearse isolated restores, measure achieved RPO/RTO, and automate escalation without automatically deleting recovery data or changing production roles. This chapter builds on [Chapters 041–045](045-point-in-time-recovery-and-disaster-recovery-lab.md).

## 2. Reliability model

```text
backup schedule -> backup artifact -> integrity verification
                                          |
archive/WAL telemetry -> continuity check |
                                          v
                                   isolated restore test
                                          |
                              data checks + application smoke
                                          |
                                measured RPO/RTO + evidence
                                          |
                                  alert + incident workflow
```

**Three distinct gates:** (1) backup job completed, (2) artifact and WAL integrity verified, (3) isolated restore and application validation passed. A successful scheduled job is not proof of recoverability.

## 3. SLIs, SLOs and alerting

| Signal | Example objective | Alert example | Evidence source |
|---|---|---|---|
| Latest successful backup age | Under 24 hours | No verified backup within 24 h | Backup tool metadata |
| WAL archive delay | Within agreed RPO budget | Delivery lag approaching RPO | Archive storage inventory + PG metrics |
| Archive failures | No persistent errors | Repeated failure and WAL growth | pg_stat_archiver, disk |
| Backup integrity | Every new backup verified | Manifest/hash mismatch | pg_verifybackup or tool equivalent |
| Restore test freshness | Within 30 days | No successful drill in 30 d | Restore-test ledger |
| Restore duration | Within RTO | Drill exceeds time budget | Run timestamps |
| Restore correctness | Critical invariants pass | Missing records or wrong recovery point | SQL + app checks |

All values are **illustrative**. Tune to service tier, workload, business-approved RPO/RTO, backup frequency and actual recovery duration. Avoid treating the `pg_stat_archiver` counter as a complete archive inventory: statistics can reset, and files can disappear after reporting success.

## 4. Monitoring SQL

```sql
SELECT name,setting,source,pending_restart FROM pg_settings
WHERE name IN ('archive_mode','archive_command','archive_library',
               'archive_timeout','wal_level','max_wal_senders')
ORDER BY name;

SELECT archived_count,last_archived_wal,last_archived_time,
       failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;

SELECT slot_name,slot_type,active,restart_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn) AS retained_bytes
FROM pg_replication_slots
WHERE restart_lsn IS NOT NULL;

SELECT pid,phase,backup_total,backup_streamed
FROM pg_stat_progress_basebackup;
```

These queries are for a primary where `pg_current_wal_lsn()` is supported. Use role-appropriate permissions; query replicas separately with replica-safe functions. Archive lag cannot be inferred reliably from `last_archived_time` alone when WAL traffic is quiet. Correlate generated segments, object-store arrival, archival success and configured `archive_timeout`.

## 5. Automation stages

**Stage A — scheduled backup:** orchestration creates a unique destination, records tool version, command parameters (excluding secrets), source identity, timeline, start/end, exit code and artifact inventory. A failed run must not overwrite the last verified backup.

**Stage B — integrity check:** run `pg_verifybackup` for compatible physical backup layouts, or `pg_restore --list` plus artifact integrity checks for logical archives. Archive listing is not an actual restore.

**Stage C — isolated restore:** provision an ephemeral, access-controlled target; restore using verified files and required WAL; start PostgreSQL; execute schema/data checks and application smoke tests; record achieved recovery point and elapsed time.

**Stage D — report and alert:** publish success/failure with immutable evidence, classify causes, open incidents when RPO/RTO is at risk and notify owners. Keep the last known-good recovery chain intact.

**Stage E — retention:** delete artifacts only through an independently approved, dependency-aware retention process. Verify that removing a base backup or WAL segment cannot invalidate the required recovery window. Do not let the same unattended workflow both declare backups valid and erase all alternatives.

## 6. Backup/restore evidence ledger

Record backup ID, cluster/system identifier, PostgreSQL major version, base-backup start/stop LSN, timeline, WAL coverage, manifest/hash status, destination, encryption state, retention expiry, restore-test date, achieved recovery point, validation results, elapsed RTO, operator and ticket. Protect evidence from unauthorized edits and exclude passwords.

A backup's age is not the same as achievable RPO. For PITR, the last continuously available WAL and the verified target determine recovery capability.

## 7. Failure response runbook

1. **Backup missed:** inspect scheduler, access, disk, network and backup-tool exit status; confirm last verified recovery point.
2. **Archiver failing:** inspect `pg_stat_archiver`, archive destination and `pg_wal` free space; avoid manual WAL deletion.
3. **Manifest mismatch:** quarantine failed artifact, retain alternate copies and run fresh verification; never mark usable.
4. **Restore failed:** preserve logs, isolate missing roles/extensions/tablespaces/WAL and retry on a fresh disposable target.
5. **RPO/RTO breach:** declare incident, estimate recoverable point and elapsed recovery time, engage application/business owners and prioritize a verified restore path.
6. **Repeated false alerts:** improve signal design and quiet-period handling, not by disabling recovery-critical monitoring.

## 8. Safe automation design

Use least-privilege backup/restore identities, secret injection, immutable backup IDs, per-run timeouts, idempotent scheduling, concurrency controls, resource quotas, isolated network access and auditable approval gates. A recovery job must not point at production PGDATA, promote a restored node into live traffic, or remove old backups without explicit authorization. Implement dry-run, rollback and failure injection tests.

**Pseudocode:**

```text
if source_preflight_failed: alert; stop
backup = create_new_artifact()
if backup_failed: preserve_previous; alert; stop
if integrity_verification_failed: quarantine; alert; stop
restore = create_isolated_target()
if restore_or_validation_failed: preserve_logs; alert; stop
record_measured_RPO_RTO_and_evidence()
mark_backup_chain_verified()
# Retention is a separate approved workflow
```

## 9. Hands-on lab and acceptance

[Chapter 046 lab](../labs/046-backup-monitoring-restore-validation-and-recovery-automation-lab.md) provides read-only monitoring SQL, a sample evidence ledger, a safe local monitoring script and a restore-validation checklist. The monitoring script reports findings; it does not modify PostgreSQL or delete backups.

**Acceptance:** distinguish freshness, integrity and restore success; define actionable SLOs; detect archive risk; produce auditable restore evidence; demonstrate that automation fails closed. **Runtime:** not executed.

## Official references

- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [Continuous archiving](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)

**Next:** Chapter 047 — PostgreSQL Replication Slots, WAL Retention and Failure Modes.
