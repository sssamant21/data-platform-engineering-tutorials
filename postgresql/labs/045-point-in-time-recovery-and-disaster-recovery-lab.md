# Chapter 045 — PITR and Disaster Recovery Hands-on Lab

**PostgreSQL 18 · Dedicated disposable cluster only · Runtime validation pending.**

## Safety requirements

This drill deliberately changes test rows. Never run the fixture or incident SQL on production, a shared database, or a system containing valuable data. Use a separately provisioned recovery instance and an empty restore data directory. Do not overwrite a live PGDATA.

## Phase 1 — Preflight

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/045-preflight.sql
```

Confirm physical backup permissions, working WAL archive, restore storage, compatible PostgreSQL 18 binaries, and an independent recovery host.

## Phase 2 — Fixture and verified base backup

```bash
psql -X -w -v ON_ERROR_STOP=1 -d postgres \
  -v expected_system_id=REPLACE_WITH_OBSERVED_DISPOSABLE_SOURCE_SYSTEM_ID \
  -v expected_data_directory=/absolute/path/to/disposable/source/PGDATA \
  -v expected_operator=AUTHORIZED_SOURCE_ROLE \
  -v confirm_stage=045-CREATE-FIXTURE -f postgresql/labs/sql/045-fixture.sql
pg_basebackup -h 127.0.0.1 -p 5432 -U backup_user -D /secure/lab/ch045-base -Fp -Xs -P
pg_verifybackup /secure/lab/ch045-base
```

Independently inspect `current_database()`, `current_user`, `SHOW data_directory` and `pg_control_system().system_identifier` on the dedicated test source before filling **all** placeholders. The fixture script requires explicit source identity, `045-CREATE-FIXTURE` and an unused `ch045` schema; creation is atomic and fails closed. The backup destination must be new and empty. Preserve command exit codes, timestamps and the manifest.

## Phase 3 — Good marker and incident

```bash
psql -X -w -v ON_ERROR_STOP=1 -d postgres \
  -v expected_system_id=REPLACE_WITH_OBSERVED_DISPOSABLE_SOURCE_SYSTEM_ID \
  -v expected_data_directory=/absolute/path/to/disposable/source/PGDATA \
  -v expected_operator=AUTHORIZED_SOURCE_ROLE \
  -v confirm_stage=045-GOOD-MARKER -f postgresql/labs/sql/045-good-marker.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v expected_source_data_directory=/absolute/path/to/disposable/source/PGDATA -v expected_operator=LAB_SOURCE_ADMIN_ROLE -v confirm_incident=045-INCIDENT -f postgresql/labs/sql/045-incident.sql
```

Before executing the incident script on the disposable source, record its identity using `SELECT current_database(), system_identifier FROM pg_control_system();`. Verify the target is a dedicated test cluster and manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID`, the expected source data-directory path, and `LAB_SOURCE_ADMIN_ROLE` (the exact authorized invoking role) in the command. The incident script rejects mismatched source paths and roles in addition to cluster identifier, database, major version and token. The `045-INCIDENT` token authorizes only this intentional corruption simulation. A cluster system identifier by itself cannot establish that data is safe to modify. Run these **only** after the base backup and archive prerequisites pass. The source good-marker script also refuses the wrong role, path, system ID, token, incomplete fixture or repeated marker. The good marker is committed before the simulated bad update. Record UTC times and available WAL evidence; a sampled timestamp is not a guaranteed exact commit boundary.

## Phase 4 — Isolated PITR

Restore the verified physical backup into an isolated PostgreSQL 18 instance. Configure a tested `restore_command`, create `recovery.signal` and choose a verified target after the good marker and before the incident. Monitor replay and pause at the target. Do not promote or accept writes until validation passes.

```bash
# Use the isolated recovery endpoint, NOT the source endpoint.
# Independently verify its data-directory path and original source system ID.
psql -X -w -v ON_ERROR_STOP=1 -h RECOVERY_HOST -p RECOVERY_PORT -U lab_admin \
  -d postgres \
  -v expected_recovery_data_directory=/absolute/path/to/isolated/recovered/PGDATA \
  -v expected_system_id=REPLACE_WITH_OBSERVED_SOURCE_LAB_SYSTEM_ID \
  -v confirm_recovery=045-VERIFY-RECOVERY \
  -f postgresql/labs/sql/045-verify.sql
```

Run verification against the **recovered instance**, not the source. Replace the endpoint, independently observed absolute PGDATA path and source-cluster system identifier. Verify that the restored instance is isolated from all application writers. The script now exits **nonzero** for wrong target or unacceptable row/marker state; a printed result alone is not a success gate. If any test fails, reject the target and repeat from a clean restored backup. The data_directory value can require a privileged verification role, not an application account.

## CI-only Chapter 045 PITR exercise

For reproducible safety testing on an isolated, network-disabled PostgreSQL 18 container, see [v03_pitr_disposable.py](../validation/v03_pitr_disposable.py) and [the dedicated workflow](../../.github/workflows/postgresql-v03-pitr-disposable.yml). Unlike the manual scenario, this harness creates its own new source, archive and recovered data directories and requires an explicit isolation token. It intentionally never overwrites source PGDATA, promotes the restore target, or routes application traffic. It checks the actual `045-verify.sql` exit status and a failed wrong-PGDATA test, not merely printed PASS/FAIL labels.

Treat even a successful CI test as *lab-only* evidence. Real off-host archive durability, replay and restore failure cases, full-business RPO/RTO, production authorization and independent acceptance are still required.

## Evidence worksheet

| Gate | Evidence | Result |
|---|---|---|
| Base backup complete | pg_basebackup exit code | |
| Manifest valid | pg_verifybackup output | |
| WAL chain continuous | Archive inventory and recovery logs | |
| Good marker present | Verification SQL | |
| Corrupt rows absent | Verification SQL | |
| Recovered row count | Expected versus actual | |
| Recovery target correct | Timestamp/LSN/timeline | |
| Achieved RPO | Last committed good data recovered | |
| Achieved RTO | Detection to validated service readiness | |
| Cutover readiness | Fencing, approvals, rollback | |

## Failure injection discussion

Review archive gaps, restore command failures, timezone mistakes, target before base backup, wrong timeline, missing tablespaces and insufficient recovery disk. No destructive filesystem commands are provided.

**Acceptance:** demonstrated independent PITR and documented data integrity, RPO/RTO and rollback. **Runtime status:** pending.
