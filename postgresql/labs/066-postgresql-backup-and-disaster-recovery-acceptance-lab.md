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
psql -X -v ON_ERROR_STOP=1 -h VERIFIED_LAB_HOST -U VERIFIED_LAB_ROLE -d ch066_lab \
  -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID \
  -v expected_lab_data_directory=REPLACE_WITH_OBSERVED_LAB_PGDATA \
  -v expected_lab_role=REPLACE_WITH_OBSERVED_LAB_ROLE \
  -v confirm_stage=066-ONE-TIME-FIXTURE \
  -f postgresql/labs/sql/066-dr-fixture.sql
```

The fixture refuses execution outside ch066_lab **and** demands an exact independently observed PostgreSQL 18 system identifier, PGDATA location, role, primary state, unused schema and one-time operator stage token. Do not substitute guessed values. It deliberately refuses reuse of any existing schema or data. A partial failure requires review and an independently verified new fixture. Keep the reference row unchanged until after backup.

## 4. Backup and integrity

```bash
set -euo pipefail
mkdir -p /backups/ch066
test ! -e /backups/ch066/base001 || { echo 'REFUSED: base001 exists' >&2; exit 3; }
pg_basebackup -h 127.0.0.1 -U backup_repl -D /backups/ch066/base001 -Fp -X stream -P --manifest-checksums=SHA256
pg_verifybackup /backups/ch066/base001
```

base001 must be unused. Preserve exit codes, duration, manifest, backup size and source identity. Confirm WAL archiving is configured and durable, as practiced in Chapter 064.

## 5. Incident timeline

On the disposable source, issue separate autocommit statements:

```sql
INSERT INTO ch066.events(event_key,description) VALUES ('before-target','must survive');
SELECT clock_timestamp() AS after_first_commit_with_utc_offset;
```

Wait several seconds and record a UTC target after the first commit. Then:

```sql
INSERT INTO ch066.events(event_key,description) VALUES ('after-target','must be absent');
DELETE FROM ch066.reference_data WHERE id=1;
SELECT pg_switch_wal();
```

Preserve the full timestamp **including UTC offset** and confirm the target lies after the first acknowledged commit and before the second transaction begins. Validate the ordering using transaction and WAL evidence, not the timestamp's label alone. Wait for archiver to durably store all required WAL; a successful `pg_switch_wal()` call does not mean the archive is complete. Do not delete data outside ch066_lab.

## 6. Isolated PITR

On a separate disposable host/container, copy the verified base backup to a **new** PGDATA. Validate copied configs, filesystem ownership, tablespace paths, TLS, replication settings and unique port. Configure restore_command against a read-only lab archive, recovery_target_time with explicit UTC offset, recovery_target_action='pause', recovery_target_inclusive=false and recovery.signal. Ensure the base backup ended **before** the requested target, and require explicit evidence that recovery actually reached it. Start only on a localhost-only lab port and monitor logs until the target is reached.

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
