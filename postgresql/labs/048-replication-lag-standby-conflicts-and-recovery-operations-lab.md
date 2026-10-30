# Chapter 048 — Replication Lag, Standby Conflicts and Recovery Operations Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `048-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18 · Chapter 004 disposable primary (127.0.0.1:55432), standby 1 (127.0.0.1:55433) · Runtime validation pending.**

Provision and verify the non-root Chapter 004 isolated topology first. Export `PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"`. Confirm primary/standby roles and the primary system identifier independently. Substitute `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` with the verified identifier **only for the disposable cluster**. Do not run the workload or cleanup on an arbitrary PRIMARY_HOST or shared server. The workload now refuses existing `ch048` objects and can be run only once.


## 1. Read-only baseline

Run primary and standby scripts against the correct node. Do not run primary-only functions on a standby.

```bash
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab -f postgresql/labs/sql/048-primary.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55433 -U lab_observer -d ops_lab -f postgresql/labs/sql/048-standby.sql
```

For the Chapter 004 topology, endpoints are fixed loopback ports 55432/55433. Do not substitute production hosts. Capture two or more samples at known intervals.

## 2. Classify lag

| Metric | Evidence | Interpretation |
|---|---|---|
| Current primary LSN - sent LSN | Primary SQL | Unsent WAL |
| Sent LSN - write LSN | Primary SQL | Transport/receiver write gap |
| Write LSN - flush LSN | Primary SQL | WAL not yet flushed |
| Flush LSN - replay LSN | Primary SQL | Replay backlog |
| Receive LSN - replay LSN | Standby SQL | Received but not applied |
| Conflict counters | Standby SQL | Cancellations from recovery conflicts |

LSN gaps are byte differences, not elapsed time. A stale last replay timestamp during primary idle time does not alone prove lag.

## 3. Controlled workload observation

On a dedicated disposable primary, run the bounded workload script and repeat primary/standby samples. It creates a lab-owned schema and inserts a limited number of rows. Do not run it on production.

```bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_stage=048-WORKLOAD -f postgresql/labs/sql/048-workload.sql
```

Observe changes in lag stages and conflict counters. This bounded workload may not produce meaningful lag on fast systems; **do not** increase load indiscriminately just to force an incident.

## 4. Conflict investigation

On standby, inspect `pg_stat_database_conflicts`, `pg_stat_activity` wait events and PostgreSQL logs. Discuss whether query cancellations are preferable to delayed replay. Evaluate `max_standby_streaming_delay` and `hot_standby_feedback` tradeoffs without changing production settings.

## 5. Cleanup and acceptance

After verifying the schema is exclusively lab-owned:

```bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab -v expected_db=ops_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=048-DROP -f postgresql/labs/sql/048-cleanup.sql
```

Cleanup checks the exact lab identifier, ownership, 5,000 synthetic rows and absence of unexpected independent objects, then atomically drops the known table and schema without CASCADE. Partial/altered fixtures are stop conditions requiring manual review. No production data or shared slots are touched. Confirm replica replay has caught up after cleanup.

**Pass:** lag stage diagnosed, conflict counts interpreted, safe recovery path documented, and primary/standby status validated. **Runtime:** pending.
