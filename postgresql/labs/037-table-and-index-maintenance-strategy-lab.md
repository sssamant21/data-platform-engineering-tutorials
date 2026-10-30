# Lab 037 — Table and Index Maintenance Strategy

**Baseline:** PostgreSQL 18, the **disposable Chapter 004** primary only (127.0.0.1:55432, ops_lab, lab_admin). **Status:** Authored and statically reviewed; no PostgreSQL 18 runtime proof yet. This exercise performs real INSERT/UPDATE/DELETE and VACUUM on 100,000 synthetic rows. Never use production or shared staging.

[Chapter](../chapters/037-table-and-index-maintenance-strategy.md) · [Chapter 004 lab](004-reproducible-postgresql-operations-lab.md) · [Setup](sql/037-setup.sql) · [Investigate](sql/037-investigate.sql) · [Cleanup](sql/037-cleanup.sql)

## 1. Identify the target before mutation

Run from the repository root as the **non-root lab OS owner**. Complete Chapter 004 first; this lab no longer assumes the machine's default `postgres` database is disposable.

~~~bash
set -euo pipefail
: "${PG_LAB_ROOT:?Export the disposable Chapter 004 directory}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=3 PGSSLMODE=disable PGGSSENCMODE=disable
admin037() {
  PGAPPNAME=c037_control PGOPTIONS='-c statement_timeout=30s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
[[ "$(admin037 -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin037 -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin037 -Atc "SELECT current_setting('server_version_num')::integer BETWEEN 180000 AND 189999")" == t ]] || exit 2
admin037 -c 'SELECT current_database(), current_user, inet_server_port(), system_identifier FROM pg_control_system();'
~~~

Verify that the output is the **same disposable** instance and record its identifier before typing it below. An identifier is not proof of authorization if the target was chosen incorrectly.

~~~bash
PG_LAB_SYSTEM_ID_037=REPLACE_WITH_INDEPENDENTLY_OBSERVED_LAB_SYSTEM_ID
[[ "$PG_LAB_SYSTEM_ID_037" =~ ^[0-9]+$ ]] || exit 2
~~~

## 2. Create one fixed fixture

~~~bash
admin037 -v expected_system_id="$PG_LAB_SYSTEM_ID_037" \
  -v confirm_setup=037-CREATE -f postgresql/labs/sql/037-setup.sql
admin037 -Atc 'SELECT count(*) FROM ch037.orders;'
~~~

**Expected:** exactly 100,000 rows; a new schema `ch037` owned by `lab_admin`, a synthetic `orders` table, one primary-key index, and one `(customer_id, created_at DESC)` index. Setup **refuses** an existing schema, wrong connection, wrong system ID or missing approval. It never adopts or appends to somebody else's data. If creation/ANALYZE fails midway, inspect before proceeding; do not retry blindly.

## 3. Generate bounded churn and compare maintenance

~~~bash
admin037 -v expected_system_id="$PG_LAB_SYSTEM_ID_037" \
  -v confirm_churn=037-CHURN -f postgresql/labs/sql/037-investigate.sql
admin037 -Atc 'SELECT count(*) AS surviving_rows FROM ch037.orders;'
~~~

The investigation script refuses a second run or altered fixture: it requires the original 100,000 rows, no preexisting `updated` status values, and exactly 20,000/10,000 target rows for update/delete. It samples table and index bytes, `n_live_tup`, `n_dead_tup`, a bounded `EXPLAIN (ANALYZE, BUFFERS)`, then updates 20,000 and deletes 10,000 fixture rows. It runs `ANALYZE`, then `VACUUM (ANALYZE)` **outside a transaction block**, and observes estimates and timestamp changes.

**Expected:** 90,000 surviving rows; statistics estimates may lag or fluctuate due to concurrent autovacuum. Do not infer physical bloat from index/table size alone, or that ordinary VACUUM returns disk space to the OS. If a statement fails, preserve the actual error and make an explicit state-reconciliation plan rather than force a subsequent phase.

## 4. Operational decision worksheet

| Choice | Evidence | Lock / availability risk | Storage, WAL and replica cost | Recovery and approval |
|---|---|---|---|---|
| ANALYZE | Stale planner estimates / plan drift | | | |
| VACUUM (ANALYZE) | Dead tuples and freeze/visibility requirements | | | |
| REINDEX INDEX CONCURRENTLY | Proven index damage/bloat and validated alternative | | | |
| VACUUM FULL / CLUSTER | Proven table rewrite need | | | |

Also capture oldest transaction, table/database freeze age, prepared transactions, replication-slot xmin and replica lag using the earlier **read-only** labs. Do not reset global stats, disable autovacuum, force index rebuilds or run VACUUM FULL for this exercise.

## 5. Verified cleanup and acceptance

Only after saving the fixture evidence and confirming the correct owner, rows, schema dependencies and **90,000 surviving rows**, close exercise sessions and execute:

~~~bash
admin037 -v expected_system_id="$PG_LAB_SYSTEM_ID_037" \
  -v confirm_cleanup=037-DROP -f postgresql/labs/sql/037-cleanup.sql
admin037 -Atc "SELECT to_regnamespace('ch037') IS NULL AS schema_removed;"
bash postgresql/scripts/004-operations-lab.sh verify
~~~

**Expected:** schema_removed=true and healthy original disposable topology. The cleanup script checks the cluster, database, role, port, PostgreSQL version, primary, data directory, system ID, schema owner, surviving row count and absence of other tables, then executes `DROP TABLE ch037.orders` and `DROP SCHEMA ch037` in one transaction. It does **not** use `CASCADE`. It refuses missing/partial/modified fixtures; these require a separately reviewed recovery plan, not a broad delete.

**Acceptance:** preflight, intended synthetic changes, bounded maintenance, credible before/after evidence, written decision, no unapproved action, guarded cleanup and verification all recorded. **Live runtime validation and independent sign-off remain pending.**
