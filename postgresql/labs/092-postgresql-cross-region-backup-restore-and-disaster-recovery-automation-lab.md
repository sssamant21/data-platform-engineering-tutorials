# Chapter 092 — Cross-Region Backup, Restore and DR Automation Lab

**PostgreSQL 18 · Disposable isolated restore only · Runtime pending**

## 1. Safety

Use a disposable PostgreSQL 18 cluster and isolated restore target. Never restore into a live primary data directory or expose a recovered candidate to production write routing. Cross-region access must be verified independently; copying between folders on one host is only a local simulation.

## 2. Preflight

Run [092 recovery preflight SQL](../labs/sql/092-cross-region-recovery-preflight.sql). Record version, system identity through approved administration tooling, WAL/archive settings, slots, archiver status, backup policy, UTC time, recovery objectives and owner approvals.

## 3. Base backup and archive

In an isolated self-managed test, configure a durable test WAL archive and use a supported backup manager or `pg_basebackup` with required replication permissions. Verify backup completion, manifest and WAL segment inventory. Record backup generation and recovery chain in [092 manifest](../labs/dr/092-backup-recovery-chain-manifest.csv).

## 4. Cross-region copy simulation

Copy backup and WAL to a separate test storage account/bucket or failure domain. Verify checksum/inventory parity, encryption and independent restore credentials. If using a single-host simulation, mark regional-independence acceptance NOT VERIFIED.

## 5. Recovery point rehearsal

Write unique transaction markers, record UTC timestamps and select a point before a disposable test change. Restore into a **new** PostgreSQL 18 instance using the documented backup manager or PostgreSQL recovery configuration with `restore_command` and `recovery.signal`. Never overwrite original data.

## 6. Verification

Run `pg_verifybackup` when a compatible manifest is available, then start the restored server and verify data/roles/extensions, selected transaction markers and application smoke tests. Measure restore elapsed time and recoverable transaction gap. Manifest validation alone is not sufficient.

## 7. Failure injection

On disposable copies only, simulate a missing WAL segment, denied KMS/decryption permission or incomplete archive copy. Verify that the automation fails closed, alerts, and preserves evidence; do not mark the backup usable.

## 8. Runbook and acceptance

Complete [092 restore runbook](../labs/dr/092-isolated-restore-automation-runbook.md) and [092 scorecard](../labs/acceptance/092-cross-region-recovery-scorecard.csv). Promotion and application cutover are tabletop-only unless independent fencing is tested in an approved isolated topology.

**Runtime:** pending.
