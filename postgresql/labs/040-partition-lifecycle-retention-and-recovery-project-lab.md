# Chapter 040 — Partition Lifecycle, Retention and Recovery Lab
**V02-D safety gates:** The creation, lifecycle and cleanup scripts all require explicit stage tokens and an independently verified Chapter 004 cluster identifier. The system ID alone is not production authorization; ownership, partition dependencies and archive/recovery evidence must also be reviewed.


**PostgreSQL 18 · Chapter 004 disposable instance only · Runtime execution pending.** Scripts use schema `ch040`, with no production/shared-staging execution.

## Run from repository root

This capstone is restricted to the **Chapter 004 disposable PostgreSQL 18** primary at 127.0.0.1:55432 in `ops_lab` as `lab_admin`. Create/start that lab first. Do not use an unverified local `postgres` database or shared staging. Run as the non-root lab OS account.

~~~bash
set -euo pipefail
: "${PG_LAB_ROOT:?Export the Chapter 004 disposable lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=3 PGSSLMODE=disable PGGSSENCMODE=disable
admin040() {
  PGAPPNAME=c040_control PGOPTIONS='-c statement_timeout=25s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
[[ "$(admin040 -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin040 -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
admin040 -c 'SELECT current_database(), current_user, inet_server_port(), system_identifier FROM pg_control_system();'
~~~

Independently verify the cluster identifier, private lab marker and target. **Manually enter** the observed system ID; do not blindly retrieve it from whatever endpoint happens to be configured. Missing/mismatched identifiers cause refusal.

~~~bash
PG_LAB_SYSTEM_ID_040=REPLACE_WITH_OBSERVED_DISPOSABLE_SYSTEM_ID
[[ "$PG_LAB_SYSTEM_ID_040" =~ ^[0-9]+$ ]] || exit 2
admin040 -v expected_system_id="$PG_LAB_SYSTEM_ID_040" \
  -v confirm_stage=040-CREATE -f postgresql/labs/sql/040-setup.sql
admin040 -v expected_system_id="$PG_LAB_SYSTEM_ID_040" \
  -v confirm_stage=040-LIFECYCLE -f postgresql/labs/sql/040-investigate.sql
~~~

Setup refuses an occupied schema and creates 12,000 synthetic events atomically, then ANALYZE runs separately. Investigation refuses partial or previously altered fixtures; it creates the April partition, inserts an April event and late January event, detaches the January partition and reattaches it. Capture all outputs and counts. If a detach/attach or count check fails, **stop** and inspect the detached standalone table. Do not run cleanup until the partition is reattached and all expected data is verified.

After the independent archive/restore acceptance described below, and only when the parent has **all four** expected attached partitions and 12,002 rows, remove the lab objects:

~~~bash
admin040 -v expected_db=ops_lab \
  -v expected_system_id="$PG_LAB_SYSTEM_ID_040" \
  -v confirm_cleanup=040-DROP -f postgresql/labs/sql/040-cleanup.sql
bash postgresql/scripts/004-operations-lab.sh verify
~~~

The cleanup refuses an unexpected target, missing partition, changed ownership or incorrect row count. It uses `DROP TABLE ch040.events` and `DROP SCHEMA ch040` **without CASCADE** within one transaction, so an unexpected standalone child or other dependency blocks cleanup rather than silently erasing it. Never use this lab as an automated retention-deletion procedure.

## Exercises

1. Inspect partition bounds, row counts and local indexes.
2. Provision April 2026 ahead of ingestion and insert an event into the new partition.
3. Insert a late-arriving January event and verify routing.
4. Compare EXPLAIN for a February-only query against an unbounded query.
5. Record January row count; detach January and verify that its standalone table still holds all rows.
6. Reattach January using the original bounds and compare total counts and routing.
7. Independently verify an archive by restoring into a separate disposable database before marking archival acceptance. This archive test is an operator-controlled extension, not automated by the SQL scripts.
8. Complete cleanup after verifying the lab schema is exclusively owned by the exercise.

## Acceptance

| Check | Expected |
|---|---|
| Future partition | April exists and accepts events |
| Late arrival | January row routed correctly |
| Pruning | February filter excludes unrelated partitions |
| Detach | January data preserved in standalone table |
| Recovery | Reattach restores parent visibility and counts |
| Archive | Independent restore test documented |
| Cleanup | Lab objects removed |

**Stop conditions:** unexpected locks, mismatched row counts, missing backups, unapproved deletion or replica risk. **Runtime validation:** pending.
