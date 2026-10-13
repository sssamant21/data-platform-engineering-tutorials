# Chapter 066 — Backup and Disaster Recovery Acceptance Lab

**PostgreSQL 18 · Disposable isolated cluster · Runtime pending**

## 1. Roles, scope and stop conditions

Assign incident commander, backup operator, recovery operator, application verifier and observer. Confirm lab-only PostgreSQL source, dedicated archive, backup location and isolated restore environment. Stop immediately if any command targets a production host, an active PGDATA, shared WAL archive or production traffic endpoint.

## 2. Preflight evidence

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/066-dr-inspect.sql
```

Record RPO/RTO targets, PostgreSQL version, system identity, UTC clock, backup inventory, replication access, archive health, offsite copy and encryption-key access. Verify the restore host has sufficient space and a unique listener.

## 3. Prepare fixture BEFORE base backup

```bash
createdb -U postgres ch066_lab
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch066_lab -f postgresql/labs/sql/066-dr-fixture.sql
```

The fixture refuses execution outside ch066_lab. Keep the reference row unchanged until after backup.

## 4. Backup and integrity

```bash
mkdir -p /backups/ch066
pg_basebackup -h 127.0.0.1 -U backup_repl -D /backups/ch066/base001 -Fp -X stream -P --manifest-checksums=SHA256
pg_verifybackup /backups/ch066/base001
```

base001 must be unused. Preserve exit codes, duration, manifest, backup size and source identity. Confirm WAL archiving is configured and durable, as practiced in Chapter 064.

## 5. Incident timeline

On the disposable source, issue separate autocommit statements:

```sql
INSERT INTO ch066.events(event_key,description) VALUES ('before-target','must survive');
SELECT clock_timestamp() AS after_first_commit;
```

Wait several seconds and record a UTC target after the first commit. Then:

```sql
INSERT INTO ch066.events(event_key,description) VALUES ('after-target','must be absent');
DELETE FROM ch066.reference_data WHERE id=1;
SELECT pg_switch_wal();
```

Confirm the target lies before the second commit and deletion. Wait for archiver to store all required WAL. Do not delete data outside ch066_lab.

## 6. Isolated PITR

On a separate disposable host/container, copy the verified base backup to a **new** PGDATA. Validate copied configs, filesystem ownership, tablespace paths, TLS, replication settings and unique port. Configure restore_command against a read-only lab archive, recovery_target_time with explicit UTC offset, recovery_target_action='pause', recovery_target_inclusive=false and recovery.signal. Start only on a localhost-only lab port and monitor logs until the target is reached.

## 7. Acceptance SQL

While recovery is paused, use a read-only query on the restored ch066_lab database:

```sql
SELECT event_key FROM ch066.events ORDER BY event_key;
SELECT id,payload FROM ch066.reference_data ORDER BY id;
```

Expected: before-target present, after-target absent, reference_data id=1 present. Record recovery target, WAL timeline and recovery log. If any check fails, mark DR03 FAIL; do not promote or route application traffic.

## 8. Failure rehearsals

Use **copies only**: verify that a modified backup copy fails pg_verifybackup, and that hiding a required segment in a cloned archive prevents a falsely successful PITR. Restore all test-only artifacts after capturing evidence. Never damage the authoritative backup or archive.

## 9. RPO/RTO and signoff

Populate [scorecard](../labs/acceptance/066-dr-acceptance-scorecard.csv). Record detection, decision, provisioning, transfer, replay, validation and lab cutover times. Verify latest recoverable point against RPO separately from the historical PITR exercise. Mark conditional out-of-scope tests explicitly; do not award PASS for unexecuted mandatory tests.

## 10. Cleanup

Shut down isolated restore instance; return only lab routing to baseline; preserve artifacts, hashes, logs and signoffs. Delete only resources positively confirmed as lab-owned.

**Runtime:** pending.
