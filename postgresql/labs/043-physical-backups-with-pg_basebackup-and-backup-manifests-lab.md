# Chapter 043 — Physical Backup and Manifest Verification Lab

**PostgreSQL 18 · Isolated lab cluster only · Runtime validation pending.** This lab is designed for a self-managed PostgreSQL instance with replication access. Managed services may require provider-native backup APIs.

## 1. Preflight

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/043-preflight.sql
pg_basebackup --version
pg_verifybackup --version
```

Verify a dedicated replication-enabled backup role, approved host-based authentication, free disk, WAL sender capacity and a **new empty backup directory**. Do not commit credentials or backup files.

## 2. Create a physical backup

Replace example host, role and path with isolated lab values. The target must be empty and outside all running PostgreSQL data directories.

```bash
pg_basebackup -h 127.0.0.1 -p 5432 -U backup_user \
  -D /secure/lab-backups/ch043-base-001 -Fp -Xs -P -v
```

Do not add `-R` unless intentionally configuring a standby. Record start/end time, backup size and relevant WAL details.

## 3. Verify integrity

```bash
pg_verifybackup /secure/lab-backups/ch043-base-001
```

Inspect the `backup_manifest`, file and WAL verification output. Capture exit codes and logs. A manifest pass is **not** a successful recovery test.

## 4. Isolated recovery rehearsal

On a **separate disposable PostgreSQL 18 instance**, provision a clean and exclusively owned data directory, restore files/tablespaces and required WAL using the official procedure, then start the server in isolation. Validate version, readiness, application tables and a bounded representative query. Measure recovery duration. Do not replace or modify a running production PGDATA.

## 5. Failure drills

- Backup role cannot authenticate: inspect privileges and `pg_hba.conf`.
- Backup cannot stream WAL: check sender availability and connectivity.
- Backup files or WAL missing: treat the backup as unusable until corrected.
- Restore fails to start: inspect permissions, tablespace mapping, PostgreSQL major version and WAL continuity.
- Recovery misses RPO/RTO: record actual result and revise design.

## 6. Acceptance evidence

| Check | Evidence |
|---|---|
| Dedicated backup access | Role and authentication reviewed |
| Backup completes | Command exit code, start/end time |
| Manifest verifies | pg_verifybackup success |
| WAL available | Required WAL coverage documented |
| Isolated restore starts | Startup/recovery logs |
| Data validates | Critical query and invariant results |
| RPO/RTO measured | Achieved recovery point and duration |

**Pass:** manifest verification **and** independent recovery validation. **Runtime status:** pending.
