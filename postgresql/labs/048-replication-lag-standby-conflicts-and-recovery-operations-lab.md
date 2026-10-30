# Chapter 048 — Replication Lag, Standby Conflicts and Recovery Operations Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `048-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18 · Dedicated primary/standby test topology · Runtime validation pending.**

## 1. Read-only baseline

Run primary and standby scripts against the correct node. Do not run primary-only functions on a standby.

```bash
psql -X -v ON_ERROR_STOP=1 -h PRIMARY_HOST -d postgres -f postgresql/labs/sql/048-primary.sql
psql -X -v ON_ERROR_STOP=1 -h STANDBY_HOST -d postgres -f postgresql/labs/sql/048-standby.sql
```

Replace host placeholders with your lab endpoints and configure credentials securely. Capture two or more samples at known intervals.

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
psql -X -v ON_ERROR_STOP=1 -h PRIMARY_HOST -d postgres -f postgresql/labs/sql/048-workload.sql
```

Observe changes in lag stages and conflict counters. This bounded workload may not produce meaningful lag on fast systems; **do not** increase load indiscriminately just to force an incident.

## 4. Conflict investigation

On standby, inspect `pg_stat_database_conflicts`, `pg_stat_activity` wait events and PostgreSQL logs. Discuss whether query cancellations are preferable to delayed replay. Evaluate `max_standby_streaming_delay` and `hot_standby_feedback` tradeoffs without changing production settings.

## 5. Cleanup and acceptance

After verifying the schema is exclusively lab-owned:

```bash
psql -X -v ON_ERROR_STOP=1 -h PRIMARY_HOST -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=048-DROP -f postgresql/labs/sql/048-cleanup.sql
```

Cleanup only removes the lab schema. Confirm replica replay has caught up after cleanup.

**Pass:** lag stage diagnosed, conflict counts interpreted, safe recovery path documented, and primary/standby status validated. **Runtime:** pending.
