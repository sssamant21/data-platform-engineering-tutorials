# Chapter 046 — Backup Monitoring, Restore Validation and Recovery Automation Lab

**PostgreSQL 18 · Read-only monitoring and isolated restore design · Runtime validation pending.**

## 1. Preflight

Run on a self-managed **disposable** PostgreSQL 18 primary or an authorized read-only monitoring account. The SQL script does not alter database state.

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/046-monitor.sql
```

Inspect archiver counts and reset time, WAL slots and retained bytes, base-backup progress, server settings and timestamp of last archive. Compare to independently collected backup-tool metadata and archive storage listings.

## 2. Evidence ledger

| Backup ID | Started | Completed | Artifact verified | WAL coverage | Restore date | Data checks | Achieved RPO | Achieved RTO |
|---|---|---|---|---|---|---|---|---|
| example-only | | | | | | | | |

Do not mark a backup restorable until an isolated restore test has passed. Record separate outcomes for artifact verification and restore validation.

## 3. Restore validation checklist

1. Choose a previously verified base backup and matching WAL chain.
2. Provision a separate, empty, disposable PostgreSQL 18 restore target.
3. Verify manifest and archived WAL availability; retain verification output.
4. Restore and start PostgreSQL in isolation; do not promote into production traffic.
5. Run critical schema, count, checksum and application checks.
6. Measure time from restore start through validation; calculate achieved RPO from recovered commit evidence.
7. Archive logs and clean up only approved lab-owned resources.

## 4. Alert and failure drills

| Drill | Expected response |
|---|---|
| Backup schedule missed | Alert with last verified recovery point |
| Archive command fails | Alert with WAL directory growth risk |
| Manifest mismatch | Quarantine artifact; preserve previous backups |
| Restore dependency missing | Fail validation, retain logs |
| RTO exceeded | Record breach and open corrective action |
| No recent restore test | Warn that recoverability confidence is stale |

## 5. Monitoring automation

The companion `046-monitor.sh` is an optional POSIX shell example. It requires `psql` and a preconfigured, authorized connection. It prints monitoring data and exits nonzero on connection/query failure. It does **not** make backups, delete artifacts, restart PostgreSQL or change settings.

```bash
bash postgresql/labs/scripts/046-monitor.sh
```

Schedule it with your existing monitoring stack only after reviewing credentials, timeout, frequency and output handling. Do not mistake a successful monitoring run for a successful backup/restore.

## 6. Acceptance

**Pass:** monitoring data collected, meaningful alert thresholds defined, evidence ledger filled, isolated restore validated and automation fail-closed behavior reviewed. **Runtime status:** pending.
