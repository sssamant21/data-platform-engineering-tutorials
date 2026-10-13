# Chapter 065 — PostgreSQL Backup Retention, Automation and Restore Testing

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Operate backups as a continuously tested recovery service. Define retention by recovery objectives and legal requirements, automate protected backup creation, monitor archive and backup health, safely expire backups and WAL only after dependency analysis, and prove recoverability through timed isolated restore drills. Builds on [Chapter 061](061-postgresql-backup-strategy-rpo-and-rto-fundamentals.md), [Chapter 063](063-postgresql-physical-backups-with-pg-basebackup-and-backup-verification.md), and [Chapter 064](064-postgresql-wal-archiving-and-point-in-time-recovery.md).

## 2. Backup inventory and dependency model

```text
Backup B1 ---- required WAL chain ---- PITR window ---- Backup B2 ---- WAL ---- now
    |                                 |
    +-- verified manifest             +-- newer recovery base
    +-- storage/key metadata              +-- independent verification
```

A retained physical base backup is usable only when its files, required WAL, timeline history, encryption keys and restore tooling remain accessible. A recovery window is the set of **actually recoverable points**, not merely the oldest backup timestamp. WAL archive cleanup must preserve the chain needed for the oldest retained usable backup and all supported PITR targets.

Inventory fields: backup_id, cluster/system identifier, timeline, backup type, start/end UTC, WAL start/end, storage URI, checksum/manifest, verification result, encryption key reference, immutable-until date, retention class, expiry date, last restore drill, measured RPO/RTO and owner. Do not put credentials or key material in inventory.

## 3. Retention policy

| Class | Example policy (illustrative) | Control |
|---|---|---|
| Operational recovery | Daily base backups for 7 days | WAL coverage across all retained recovery bases |
| Weekly recovery | Weekly verified backup for 4 weeks | Preserve dependency chain and offsite copy |
| Monthly compliance | Monthly immutable copy for 12 months | Legal holds, access review and key recovery |
| Logical selective restore | Encrypted weekly pg_dump | Independently test object/role restore |
| Cross-region DR | Replicated protected copies | Verify replication completeness and regional credentials |

These are **examples, not defaults**. Set retention based on RPO/RTO, audit, storage growth and regulations. An object-store lifecycle rule that deletes WAL independently of backup retention can silently destroy PITR. Never apply time-based deletion to WAL without proving the oldest required segment for all supported backups and timelines.

## 4. Automation design

```text
Scheduler -> acquire singleton lease -> preflight -> backup -> verify -> upload
                                  |                   |
                                  +-- logs/metrics <--+
                                         |
                              inventory + immutable copy
                                         |
                         independent restore drill / alerts
```

Use a scheduler appropriate to the environment (systemd timer, Kubernetes CronJob, cloud scheduler, or backup product). Enforce a singleton lock, bounded runtime, retries with jitter, storage capacity checks, failure notifications, least-privilege backup role, protected secrets, TLS, checksum verification, and an immutable/offsite copy. A scheduler success status is insufficient: distinguish **backup created**, **artifact verified**, **offsite copy confirmed**, and **restore drill passed**.

On Kubernetes, use concurrencyPolicy: Forbid, a bounded activeDeadlineSeconds, history limits, secure service account and secrets, and persistent/object storage. Consider CronJob scheduling gaps, node eviction, container restart and duplicate execution. Protect against incomplete artifacts being marked as completed.

## 5. Example PowerShell automation (disposable logical backup)

```powershell
$ErrorActionPreference = 'Stop'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$dir = Join-Path (Get-Location) 'backups\ch065'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$out = Join-Path $dir ('ch065_' + $stamp + '.dump')
pg_dump -h localhost -U backup_user -d ch065_lab -Fc -f $out
if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed' }
pg_restore -l $out | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'archive inspection failed' }
Get-FileHash $out -Algorithm SHA256
```

This produces a **logical** backup demonstration only; it does not test PITR or replace physical backups. Run against an isolated test database, protect credentials, check for nonempty output and restore to a fresh database before acceptance. Do not schedule this as-is for production.

## 6. Physical backup and WAL lifecycle

Recommended production process: create physical base backup with pg_basebackup or a tested backup manager; verify with pg_verifybackup where applicable; confirm archive continuity and offsite storage; execute a restore drill; then calculate candidate expiry with a dependency graph. Backup managers such as pgBackRest or Barman may manage retention and WAL dependencies; understand their retention semantics and test actual restores.

**Deletion safety gates:** (1) inventory current, (2) valid newer recoverable base available if policy requires it, (3) no legal hold, (4) all dependent WAL/timelines preserved, (5) offsite/immutable requirements satisfied, (6) dry-run deletion report reviewed, (7) two-person approval for production deletion, (8) post-cleanup restore verification. Do not manually delete files from live pg_wal.

## 7. Observability and alerts

| Signal | Warning condition | Critical condition |
|---|---|---|
| Last valid backup age | Exceeds planned cadence + grace | RPO protection cannot be met |
| Last successful archive / archive failures | Sustained failures or unexpected lag | WAL accumulating / recoverability threatened |
| Verified offsite copy age | Copy delayed | No independent recoverable copy |
| Backup duration | Growing vs baseline | Cannot finish within window |
| Restore drill age | Missed scheduled drill | Recovery assurance out of policy |
| Recovery RTO | Drill nearing target | Timed drill exceeds RTO |
| Storage / immutable retention | Growth or expiry risk | Full disk or unrecoverable key/copy |

Use alert windows that account for low WAL generation, archive_timeout and backup cadence. pg_stat_archiver is useful but does not prove archived files are intact or readable. Alert on exporter/telemetry loss separately.

## 8. Restore drill schedule and evidence

Perform regular isolated drills using random retained backups, including oldest supported recovery point and newest point. Test full cluster startup, required extensions/tablespaces, application queries, roles, encryption keys, timeline changes and WAL availability. Include one controlled PITR test before and after a known transaction. Record restore start/end, transfer time, replay time, validation time, achieved recovery timestamp, and RPO/RTO. A drill should not touch production routing or data.

## 9. Failure cases

| Failure | Impact | Response |
|---|---|---|
| Backup job green but archive missing | PITR gap | Fail recovery acceptance; repair archiving |
| Object lifecycle deletes WAL too early | Unrecoverable targets | Freeze cleanup, evaluate surviving chains |
| Backup and WAL in same compromised account | Shared blast radius | Separate identity, immutable/offsite copy |
| Encryption key retired | Backups unreadable | Key retention and tested key recovery |
| Job overlaps | Resource pressure, inconsistent inventory | Singleton lease / concurrency control |
| Restore exceeds RTO | SLA breach | Optimize transfer, provisioning and replay |
| Oldest backup untested | Hidden dependency break | Sample oldest retained point in drill rotation |

## 10. Hands-on lab

See [Chapter 065 lab](../labs/065-postgresql-backup-retention-automation-and-restore-testing-lab.md), [backup inspection SQL](../labs/sql/065-backup-inspect.sql) and [retention decision worksheet](../labs/retention/065-retention-decision-template.csv). The lab exercises a bounded logical backup and isolated restore, builds a dependency inventory and rehearses a **dry-run-only** expiry decision. Actual physical/WAL expiry is deliberately not automated.

## 11. Acceptance

Require a versioned backup policy, inventory, tested artifact, verified offsite copy, WAL dependency analysis, protected keys, timed isolated restore within RTO, achieved RPO, a non-destructive retention dry run and an on-call alert response. **Runtime pending; no recovery acceptance claimed.**

## Official references

- https://www.postgresql.org/docs/18/backup.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/app-pgbasebackup.html
- https://www.postgresql.org/docs/18/app-pgverifybackup.html

**Next:** Chapter 066 — PostgreSQL Backup and Disaster Recovery Acceptance Lab.