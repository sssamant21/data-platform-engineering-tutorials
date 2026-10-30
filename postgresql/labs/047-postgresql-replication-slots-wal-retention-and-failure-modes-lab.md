# Chapter 047 — Replication Slots, WAL Retention and Failure Modes Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `047-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18 · Disposable self-managed primary · Runtime validation pending.**

## 1. Read-only baseline

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/047-investigate.sql
```

Record all slots, types, active states, `restart_lsn`, logical `confirmed_flush_lsn`, `wal_status`, `safe_wal_size`, `inactive_since`, retained-WAL estimates and archiver state. Capture `pg_wal` filesystem usage separately; LSN distance is not physical disk usage.

## 2. Optional disposable physical-slot demonstration

**Only on a dedicated lab primary** with enough free disk and a clearly documented rollback. Do not run on shared staging/production. The SQL creates one named physical slot; verify no slot of that name exists before running.

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/047-create-lab-slot.sql
```

Generate a bounded amount of WAL with lab-owned rows:

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/047-generate-wal.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/047-investigate.sql
```

The example creates a slot without reserving WAL immediately. Its `restart_lsn` may remain NULL until the slot is used; therefore the exercise demonstrates slot metadata and bounded WAL generation, **not guaranteed slot-driven retention**. To study sustained retention, connect a disposable physical replication consumer using the slot and observe its confirmed usage before stopping it. That extended exercise is manual and must be capacity-limited.

## 3. Cleanup

Review the slot identity and ensure it is inactive and exclusively lab-owned before running:

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=047-DROP -f postgresql/labs/sql/047-cleanup.sql
```

Cleanup removes only the lab slot and lab schema. Never use this script against a shared cluster. Verify `pg_replication_slots` and `pg_wal` afterward; space reclamation may require later checkpoints and is not guaranteed immediately.

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
