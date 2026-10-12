# Lab 027 — Estimated Plans, Execution and Side Effects

Audience: DBRE/SRE. PostgreSQL 18; Chapter 004 disposable primary only.
Status: authored/static reviewed; runtime plan execution pending.

[Chapter](../chapters/027-explain-and-explain-analyze-safely.md) · [Fixed read plan](../scripts/027-read-plan.sql) · [Known write/rollback](../scripts/027-write-plan-rollback.sql) · [Offline summary](../scripts/027-plan-summary.py)

## Scope

Create a small fixture with 20,000 synthetic rows and a separate sequence-backed mutation probe. Capture one fixed correlated read in estimated/executed modes, inspect loops, demonstrate planning lock waits and observe rollback's sequence limitation.

No arbitrary application query, external function, foreign table, production write, global planner setting or cache flush is part of this lab. No server restart or statistics reset is required.

## 1. Guard and provision

In repository root, as the non-root Chapter 004 owner:

~~~bash
set -euo pipefail
test -n "$PG_LAB_ROOT"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=3 PGSSLMODE=disable PGGSSENCMODE=disable
admin() {
  PGAPPNAME=c027_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
app() {
  PGAPPNAME=c027_app PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms -c transaction_timeout=5s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
~~~

Provision once:

~~~bash
admin <<'SQL'
BEGIN;
CREATE SCHEMA c027_plans AUTHORIZATION lab_admin;
CREATE TABLE c027_plans.items (id integer PRIMARY KEY, grp integer, payload text);
INSERT INTO c027_plans.items
SELECT i,i%100,repeat('x',128) FROM generate_series(1,20000) AS g(i);
CREATE INDEX items_grp_idx ON c027_plans.items(grp);
CREATE SEQUENCE c027_plans.probe_seq START 1 CACHE 1;
CREATE TABLE c027_plans.mutation_probe (
  id bigint PRIMARY KEY DEFAULT nextval('c027_plans.probe_seq'),
  payload text
);
ALTER SEQUENCE c027_plans.probe_seq OWNED BY c027_plans.mutation_probe.id;
GRANT USAGE ON SCHEMA c027_plans TO lab_app;
GRANT SELECT ON c027_plans.items TO lab_app;
GRANT SELECT,INSERT ON c027_plans.mutation_probe TO lab_app;
GRANT USAGE,SELECT ON SEQUENCE c027_plans.probe_seq TO lab_app;
COMMIT;
ANALYZE c027_plans.items;
SQL
~~~

Existing schema is a precondition failure; investigate instead of overwriting it. Fixtures have no user triggers, foreign tables or custom functions. nextval is the deliberately reviewed nontransactional effect. Never print credentials.

## 2. Capture estimated and executed read plans

Use private files and exclusive creation:

~~~bash
umask 077
evidence="$PG_LAB_ROOT/c027-evidence"
[[ ! -L "$evidence" ]] || exit 2
mkdir -p -m 700 "$evidence"
[[ -d "$evidence" && -O "$evidence" ]] || exit 2
capture_read() {
  local mode="$1" name="$2"
  [[ "$mode" == estimated || "$mode" == executed ]] || return 2
  [[ "$name" =~ ^[A-Za-z0-9_-]{1,32}$ ]] || return 2
  (
    set -o noclobber
    PGAPPNAME=c027_read PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms -c transaction_timeout=5s' \
      timeout --kill-after=2s 8s psql -X -w -qAt -v ON_ERROR_STOP=1 -v mode="$mode" \
      -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab \
      -f postgresql/scripts/027-read-plan.sql > "$evidence/$name.json"
  )
}
capture_read estimated estimated
capture_read executed executed
python3 postgresql/scripts/027-plan-summary.py "$evidence/estimated.json" > "$evidence/estimated-summary.json"
python3 postgresql/scripts/027-plan-summary.py "$evidence/executed.json" > "$evidence/executed-summary.json"
~~~

The script uses one fixed correlated SELECT in an explicit read-only transaction with local statement/lock budgets. Estimated output should have no actual row/loop observations. Executed output should have actual observations, buffer fields and an Execution Time summary despite TIMING OFF.

The query returns three outer IDs, each counting a three-ID inner range. Locate its correlated subplan: repeated inner work should have loops reflecting those outer invocations. Node choice can differ by platform/version/settings; do not assert a particular scan algorithm.

Check actual rows per loop against Plan Rows before multiplying by loops. A repeated inner scan averaging three rows over three loops represents about nine output rows across invocations. Do not add that to the outer result as nine additional business rows.

Raw JSON includes expressions and object names. The summary omits those strings, but it does not make the original file safe to share unrestricted.

## 3. Repeat with honest measurement boundaries

~~~bash
capture_read executed executed-repeat
python3 postgresql/scripts/027-plan-summary.py "$evidence/executed-repeat.json" > "$evidence/repeat-summary.json"
~~~

Compare estimates, rows, loops and buffer observations. Timing may change with cache state and scheduling. Do not flush OS/PostgreSQL caches or restart the server for this exercise.

TIMING OFF removes per-node timing fields, not execution or all instrumentation overhead. Parent buffer observations can include children; do not total every node. The summary keeps them per node and does not manufacture an exclusive-work ranking.

A root LIMIT changes query semantics and may stop producers early. Explain why adding LIMIT 1 to an aggregate/sort is not a general resource cap. Keep the supplied query unchanged so the before/after contract remains comparable.

## 4. Plain EXPLAIN can wait for locks

In a second guarded terminal, open a disposable admin holder:

~~~bash
PGAPPNAME=c027_holder \
PGOPTIONS='-c statement_timeout=30s -c lock_timeout=1s -c transaction_timeout=90s -c idle_in_transaction_session_timeout=60s' \
  psql -X -w -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab
~~~

In that terminal:

~~~sql
BEGIN;
LOCK TABLE c027_plans.items IN ACCESS EXCLUSIVE MODE;
~~~

In O, capture the expected failure without claiming the partial file is a plan:

~~~bash
if capture_read estimated locked-estimate; then
  echo "Unexpected success while incompatible lock is held"; exit 2
else
  echo "Expected bounded lock failure; preserve the client error and partial file"
fi
~~~

Expect 55P03 after the read-plan script's 500 ms lock budget. Plain EXPLAIN must access/lock the relation for planning even though it does not execute its scan.

In the holder ROLLBACK and \q. Capture a new estimated plan under a new filename and verify successful parsing. If the holder timed out first, diagnose ordering and repeat; do not force the expected result by editing evidence.

## 5. A rolled-back analyzed insert still consumes a sequence value

First verify the isolated mutation probe is untouched:

~~~bash
app -c 'SELECT count(*) FROM c027_plans.mutation_probe;'
app -c 'SELECT last_value,is_called FROM c027_plans.probe_seq;'
app <<'SQL'
BEGIN;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
EXPLAIN (ANALYZE FALSE)
INSERT INTO c027_plans.mutation_probe(payload) VALUES ('synthetic-estimate');
ROLLBACK;
SELECT last_value,is_called FROM c027_plans.probe_seq;
SQL
~~~

Expected: table count 0; sequence last_value 1/is_called false before and after this plain estimated INSERT. nextval is volatile and is not the constant-folding function used by this statement. This observation does not establish that every unreviewed expression is harmless during planning.

Now execute only the known insert/rollback script:

~~~bash
(
  set -o noclobber
  app -qAt -f postgresql/scripts/027-write-plan-rollback.sql > "$evidence/write-rollback.json"
)
python3 postgresql/scripts/027-plan-summary.py "$evidence/write-rollback.json" > "$evidence/write-summary.json"
app -c 'SELECT count(*) FROM c027_plans.mutation_probe;'
app -c 'SELECT last_value,is_called FROM c027_plans.probe_seq;'
~~~

Expected: count remains 0 after rollback, but sequence last_value 1/is_called true. The analyzed INSERT actually used the first sequence value. Do not call nextval again before recording evidence: that would advance it further.

Inspect WAL/buffer observations in the restricted raw plan. Rollback did not undo generation of work. No exact WAL-byte count or elapsed time is prescribed.

This is a fixture-only demonstration, not permission to analyze a production INSERT with unknown triggers/defaults. Deferred commit-time effects and external calls are not necessarily modeled or reversed by this transaction.

## 6. Read-only failure and generic-plan boundaries

In a fresh interactive app connection with verbose errors, try:

~~~sql
\set VERBOSITY verbose
\set ON_ERROR_STOP off
\set ON_ERROR_ROLLBACK off
BEGIN READ ONLY;
EXPLAIN (ANALYZE TRUE) SELECT nextval('c027_plans.probe_seq');
ROLLBACK;
~~~

Expected: read-only sequence-write error, commonly SQLSTATE 25006. Recover the explicit transaction with rollback. This guard is useful for reviewed local statements; it is not a universal external-side-effect sandbox.

For estimated generic planning, run:

~~~sql
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
EXPLAIN (GENERIC_PLAN TRUE)
SELECT id FROM c027_plans.items WHERE grp=$1;
ROLLBACK;
~~~

The parameter type is inferred from grp. GENERIC_PLAN cannot be combined with ANALYZE. Optionally PREPARE a typed fixture lookup and inspect EXPLAIN EXECUTE in the same connection; deallocate it before quitting. A literal test does not automatically reproduce a production driver's generic/custom-plan choice.

## 7. Offline summary cases and cleanup

Use clearly labeled synthetic JSON outside live evidence. Verify missing actual fields remain not_measured, zero loops become not_executed and positive actual output with zero estimated rows is explicit rather than a divided-by-zero ratio.

Test a repeated node, nested buffer counts, unknown additional fields and a literal marker in Filter/Output/Relation Name. The marker must be absent from summary output. Malformed/nonfinite numbers, incomplete actual row/loop pairs, multiple documents and excessive plan depth must fail. This tests parsing, not database statement safety.

Close holders and app sessions. In O:

~~~bash
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='ops_lab' AND application_name IN ('c027_holder','c027_read','c027_app');"
admin <<'SQL'
BEGIN;
DROP TABLE c027_plans.mutation_probe;
DROP TABLE c027_plans.items;
DROP SCHEMA c027_plans;
COMMIT;
SELECT to_regnamespace('c027_plans') IS NULL AS fixture_removed;
SQL
~~~

Require no fixture actors and fixture_removed true. The owned sequence is removed with mutation_probe. Resolve remaining locks through their owners before retrying bounded cleanup. No planner/server/role settings need restoration.

Acceptance requires estimated/executed/repeated capture, loop interpretation, bounded planning-lock failure and recovery, empty table with advanced sequence, read-only error recovery and scoped cleanup. Static/helper tests do not verify actual PostgreSQL plans, performance or side-effect behavior.
