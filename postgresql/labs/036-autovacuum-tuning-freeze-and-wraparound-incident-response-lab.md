# Chapter 036 — Hands-on Autovacuum Tuning and Freeze Safety Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `036-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18 · Disposable database only.** Setup refuses an existing schema; separately confirmed cleanup destroys the `ch036` schema. Never test wraparound by exhausting XIDs or disabling autovacuum.

## Run from repository root

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/036-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/036-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=036-DROP -f postgresql/labs/sql/036-cleanup.sql
```

Use a local disposable PostgreSQL 18 database, not shared staging. `VACUUM` must run outside an explicit transaction block. Capture outputs for the incident worksheet.

## Investigation stages

1. **Baseline:** verify server version, database identity, XID/multixact ages, table statistics and effective autovacuum settings.
2. **Trigger estimate:** compute the illustrative dead-tuple trigger for 100,000 rows with threshold 50 and scale factor 0.2; then compare a proposed lab-only threshold 100 and scale factor 0.02.
3. **Controlled churn:** update and delete bounded row ranges; observe `n_dead_tup` estimates and size.
4. **Maintenance:** run `VACUUM (ANALYZE)` and compare estimates, freeze age and timestamps. Note that autovacuum may run independently.
5. **Blocker triage:** inspect active transaction ages and replication slots read-only; do not cancel or modify anything.
6. **Rollback:** reset lab table overrides and verify `reloptions`; drop only the lab schema.

## Incident decision exercise

| Evidence | Value | Interpretation | Escalation/Action |
|---|---|---|---|
| Database XID age | | | |
| Database multixact age | | | |
| Table age | | | |
| Autovacuum worker activity | | | |
| Oldest snapshot / slot xmin | | | |
| Disk and WAL headroom | | | |
| Dead tuple trend | | | |

**Pass:** evidence supports a safe change and rollback, no unsafe session/slot intervention, and cleanup verified. **Runtime status:** pending.
