# Chapter 041 — Backup Architecture and Recovery Objectives Lab

**PostgreSQL 18 · Disposable local database only · Runtime verification pending.** Use a non-production PostgreSQL instance with `pg_dump`, `pg_restore`, `createdb` and `psql` available. Never restore into a database containing valuable data.

## 1. Preflight

```bash
psql -X -d postgres -c "SELECT current_database(), current_user, current_setting('server_version');"
pg_dump --version
pg_restore --version
```

Choose two **new** lab-only database names, `ch041_source` and `ch041_restore`, and verify neither exists before proceeding. Create both with `createdb`. Do not overwrite existing databases.

## 2. Create fixture

```bash
psql -X -v ON_ERROR_STOP=1 -d ch041_source -f postgresql/labs/sql/041-fixture.sql
```

## 3. Take a logical backup

```bash
pg_dump -Fc -d ch041_source -f ch041-source.dump
pg_restore --list ch041-source.dump
```

Store the dump in a restricted lab directory. Capture file size and a cryptographic hash using an OS-native command. A successful archive listing is **not** a verified restore.

## 4. Restore independently

```bash
pg_restore --exit-on-error --no-owner --no-privileges -d ch041_restore ch041-source.dump
psql -X -v ON_ERROR_STOP=1 -d ch041_restore -f postgresql/labs/sql/041-verify.sql
psql -X -v ON_ERROR_STOP=1 -d ch041_source -f postgresql/labs/sql/041-verify.sql
```

Compare counts and aggregate checks from both databases. Record backup start/end, restore start/end and validation completion to estimate achievable RTO. The dump provides a snapshot, not arbitrary PITR.

## 5. RPO/RTO tabletop

| Scenario | RPO target | RTO target | Proposed recovery | Missing dependencies |
|---|---|---|---|---|
| Accidental DELETE | | | | |
| Primary storage loss | | | | |
| WAL archive gap | | | | |
| Region outage | | | | |

Discuss role/extension restoration, WAL continuity, storage isolation, backup encryption, alerting and retention. Do not run physical PITR on a production cluster as part of this lab.

## 6. Cleanup and evidence

Keep dump and restore logs until validation is reviewed. Only after confirming both databases are exclusively lab-owned, remove them using your approved local lab cleanup process. Never use a forced database drop on shared systems.

**Pass:** independent restore succeeds, row count and checksum agree, measured restore time is documented, and the recovery plan distinguishes logical backup from physical PITR. **Runtime:** pending.
