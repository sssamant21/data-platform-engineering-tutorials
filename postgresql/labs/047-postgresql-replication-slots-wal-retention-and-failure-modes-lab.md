# Chapter 047 — Replication Slots, WAL Retention and Failure Modes Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `047-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18 · Chapter 004 isolated primary at 127.0.0.1:55432, database ops_lab, lab_admin · Runtime validation pending.**

Before all commands, provision/verify the Chapter 004 lab as a non-root OS user, set `PG_LAB_ROOT` and export `PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"`. Independently inspect `SHOW data_directory`, `pg_is_in_recovery()`, server version, system identifier and sufficient WAL/disk headroom. Replace each `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` manually with the verified Chapter 004 cluster identifier. A system ID alone is not authorization. **Stage commands now refuse** a wrong/missing identity, incorrect role, existing slot or schema, or a repeated WAL fixture. Do not execute them on a generic postgres server or shared environment.



## 1. Read-only baseline

```bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -f postgresql/labs/sql/047-investigate.sql
```

Record all slots, types, active states, `restart_lsn`, logical `confirmed_flush_lsn`, `wal_status`, `safe_wal_size`, `inactive_since`, retained-WAL estimates and archiver state. Capture `pg_wal` filesystem usage separately; LSN distance is not physical disk usage.

## 2. Optional disposable physical-slot demonstration

**Only on a dedicated lab primary** with enough free disk and a clearly documented rollback. Do not run on shared staging/production. The SQL creates one named physical slot; verify no slot of that name exists before running.

```bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_stage=047-CREATE-SLOT -f postgresql/labs/sql/047-create-lab-slot.sql
```

Generate a bounded amount of WAL with lab-owned rows:

```bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_stage=047-GENERATE-WAL -f postgresql/labs/sql/047-generate-wal.sql
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -f postgresql/labs/sql/047-investigate.sql
```

The one-time, explicitly approved example creates a slot without reserving WAL immediately. Its `restart_lsn` may remain NULL until the slot is used; therefore the exercise demonstrates slot metadata and bounded WAL generation, **not guaranteed slot-driven retention**. To study sustained retention, connect a disposable physical replication consumer using the slot and observe its confirmed usage before stopping it. That extended exercise is manual and must be capacity-limited.

## 3. Cleanup

Review the slot identity and ensure it is inactive and exclusively lab-owned before running:

```bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -v expected_db=ops_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=047-DROP -f postgresql/labs/sql/047-cleanup.sql
```

Cleanup requires the exact lab cluster and both expected objects, no active consumer, no unexpected tables, and 2,000 fixture rows. It removes the fixture table/schema without CASCADE before dropping the inactive slot. **These are not one atomic operation**: if the second step fails, inspect partial state and obtain a reviewed recovery plan before retrying. A missing fixture or slot is an intentional refusal, not permission to broaden cleanup. Never use this script against a shared cluster. Verify `pg_replication_slots` and `pg_wal` afterward; space reclamation may require later checkpoints and is not guaranteed immediately.

## 4. Failure drills (tabletop)

| Failure | Expected response |
|---|---|
| Consumer disconnected | Identify owner, lag, restart_lsn and safe_wal_size |
| WAL nearing disk capacity | Fix archive/consumer, expand storage with approval |
| Slot becomes unreserved | Warn of imminent required-WAL loss |
| Slot becomes lost | Plan consumer reinitialization |
| Logical CDC stalled | Inspect confirmed_flush_lsn and catalog_xmin |
| Orphaned slot | Obtain approval before removal |

**Pass:** evidence-based slot assessment and safe cleanup, with no production slot modifications. **Runtime:** pending.
