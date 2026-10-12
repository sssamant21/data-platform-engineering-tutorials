# Lab 026 — Performance Triage Evidence

Audience: DBRE/SRE. PostgreSQL 18. Runtime execution pending.
[Chapter](../chapters/026-performance-triage-and-evidence-collection.md) · [Collector](../scripts/026-collect-lab-triage.sh) · [Snapshot SQL](../scripts/026-triage-snapshot.sql)

## Scenario and boundaries

Use Chapter 004's primary, existing credentials and roles. You will distinguish an idle transaction, a lock-waiting request, a slow active sleep and a strong relation lock. Collect baseline/incident/recovery bundles and write one evidence-based hypothesis.

No server restart, statistics reset, configuration change, broad session termination or arbitrary EXPLAIN ANALYZE is required. Every fixture mutation is rolled back; the collector itself uses metadata-only reads.

Use O as operator and A/B as actors. Keep each phase below the actor timeout guards. If a wait expires while you are reading, recover the actors and repeat the phase with fresh transactions/identities.

## 1. Guard and provision

Run from repository root as the Chapter 004 non-root owner. In O:

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
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable
admin() {
  PGAPPNAME=c026_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
actor() {
  PGAPPNAME="$1" PGOPTIONS='-c statement_timeout=40s -c lock_timeout=30s -c transaction_timeout=90s -c idle_in_transaction_session_timeout=60s' \
    psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
~~~

Provision once:

~~~bash
admin <<'SQL'
BEGIN;
CREATE SCHEMA c026_triage AUTHORIZATION lab_admin;
CREATE TABLE c026_triage.probe (id integer PRIMARY KEY, value integer NOT NULL);
INSERT INTO c026_triage.probe VALUES (1,100);
GRANT USAGE ON SCHEMA c026_triage TO lab_app,lab_observer;
GRANT SELECT,UPDATE ON c026_triage.probe TO lab_app;
GRANT SELECT ON c026_triage.probe TO lab_observer;
COMMIT;
SQL
bash postgresql/scripts/026-collect-lab-triage.sh --help
baseline_bundle="$(bash postgresql/scripts/026-collect-lab-triage.sh baseline)"
python3 -m json.tool "$baseline_bundle/manifest.json"
python3 -m json.tool "$baseline_bundle/database.json"
~~~

Existing schema is a precondition failure. Investigate previous ownership; do not drop it automatically. The collector independently guards its primary endpoint and private passfile.

Evidence directories are unique per invocation and private. A manifest records SQL execution/validation and optional host-command statuses. Optional process observations can be empty or unavailable; that is not zero database load.

## 2. Observe an idle transaction

In A and B, run only the guard/export/function block from step 1. Open A with actor c026_A and B with actor c026_B. In each:

~~~sql
\set VERBOSITY verbose
\set ON_ERROR_STOP off
\set ON_ERROR_ROLLBACK off
\pset pager off
SELECT pg_backend_pid(),backend_start
FROM pg_stat_activity WHERE pid=pg_backend_pid();
~~~

Record both original PID/start pairs. In A:

~~~sql
BEGIN;
UPDATE c026_triage.probe SET value=101 WHERE id=1;
~~~

Leave A at its prompt. In O:

~~~bash
held_bundle="$(bash postgresql/scripts/026-collect-lab-triage.sh held-transaction)"
python3 -m json.tool "$held_bundle/database.json"
~~~

Expected: A idle in transaction, with nonzero transaction/idle age and no active_age. The fixture's uncommitted value does not establish a consumer-visible update. Do not label the last-query age as active execution.

## 3. Observe a blocked request and recover it

In B:

~~~sql
BEGIN;
UPDATE c026_triage.probe SET value=102 WHERE id=1;
~~~

While B is waiting, O collects promptly:

~~~bash
blocked_bundle="$(bash postgresql/scripts/026-collect-lab-triage.sh blocked-request)"
python3 -m json.tool "$blocked_bundle/database.json"
~~~

Required: B active with Lock wait and blocker_pids including A; A remains idle in transaction with its recorded identity. Look at cohort/blocker clipping fields before claiming the graph is complete.

Write the initial hypothesis: request B is delayed acquiring a lock held by A's open transaction. Evidence supports this wait mechanism. It does not explain why the application left A open; that needs an application transaction/trace review.

Have A ROLLBACK. B's UPDATE should complete, then B ROLLBACK. In O:

~~~bash
recovered_bundle="$(bash postgresql/scripts/026-collect-lab-triage.sh recovered)"
admin -c 'SELECT value FROM c026_triage.probe WHERE id=1;'
~~~

Expect no B lock wait and value 100. The recovery action was owner rollback; no administrative cancellation/termination was used. If B got 55P03/57014 first, explicitly roll it back, retain the real error and repeat with a new phase.

## 4. Observe active work without claiming CPU saturation

In A, outside any transaction block:

~~~sql
SELECT pg_sleep(20);
~~~

During the sleep, O collects:

~~~bash
sleep_bundle="$(bash postgresql/scripts/026-collect-lab-triage.sh active-sleep)"
python3 -m json.tool "$sleep_bundle/database.json"
~~~

Expect active state and a sleep-related wait, commonly Timeout/PgSleep. The active age is meaningful for the current statement. A slow active statement is not necessarily an expensive CPU computation.

Review processes.txt and vmstat.txt with their exit statuses. ps percentages can be lifetime averages; vmstat's first line is a different baseline from later interval lines. They describe the collector's host/namespace, not an automatically identified cloud storage device or cgroup.

Let the sleep finish. Do not artificially consume CPU, fill disk or cause OOM to reproduce resource pressure. State which additional interval CPU/storage/memory signals a real resource hypothesis would need.

## 5. Prove collection does not read the locked fixture

Quit A's lab_app connection. Open a new bounded admin actor in A's shell:

~~~bash
PGAPPNAME=c026_strong_lock \
PGOPTIONS='-c statement_timeout=40s -c lock_timeout=2s -c transaction_timeout=90s -c idle_in_transaction_session_timeout=60s' \
  psql -X -w -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab
~~~

In this disposable admin actor:

~~~sql
SELECT pg_backend_pid(),backend_start
FROM pg_stat_activity WHERE pid=pg_backend_pid();
BEGIN;
LOCK TABLE c026_triage.probe IN ACCESS EXCLUSIVE MODE;
~~~

O now runs:

~~~bash
strong_bundle="$(bash postgresql/scripts/026-collect-lab-triage.sh strong-lock)"
python3 -m json.tool "$strong_bundle/manifest.json"
~~~

Required: metadata collection succeeds without waiting on c026_triage.probe. The initial collector never reads fixture rows, estimates table size or executes application SQL. Do not add a fixture SELECT as a “health check” during this held lock.

Roll back the admin actor and quit it. This phase exercises collector availability under a relation lock, not a production permission policy.

## 6. Interpret evidence limits and partial capture

Review the bundle structure:

| Artifact | Meaning |
|---|---|
| database.json | One bounded metadata snapshot with source/time/context |
| database.exit | psql/process execution status |
| database.validation_exit | Basic JSON/identity validation status |
| filesystem/vmstat/processes text | Optional local host observations |
| Per-command exit/stderr files | Explicit unavailable/error evidence |
| manifest.json | Phase label, completion time, source and statuses |

A SQL failure can leave an empty/partial database.json. The wrapper returns a nonzero exit and still retains the bundle after a guarded identity check. Do not use that file as a successful zero-activity sample.

The session list is capped at 50; blocker lists are bounded. Query text and parameters are absent. The collector can still include application_name and role names, so keep bundles private and review sharing.

For optional window analysis, use Chapter 022's collector/delta helper before and after an approved observation. Do not subtract nested fields from this snapshot across an unchecked restart/reset. If pg_stat_statements is unavailable after Chapter 023's restoration, record that fact; do not preload/restart it just to make this evidence pack look complete.

Use a labeled synthetic failed-capture manifest to discuss unknown evidence, or run offline orchestration fixtures. Do not remove real permissions, corrupt credentials or disable tracking merely to force a partial result.

## 7. Write the triage decision and clean up

Produce a short record: affected operation, observation window, verified source, stable A/B identities, lock evidence, owner rollback, recovered request/data state and remaining uncertainty. Separate facts from hypotheses.

Explicitly reject these unsupported conclusions: “active means CPU saturated,” “buffer misses equal physical reads,” “filesystem utilization proves IOPS saturation,” and “one recovered SQL statement proves the service SLO recovered.”

Close B and any other lab actors with ROLLBACK and \q. O checks:

~~~bash
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='ops_lab' AND application_name IN ('c026_A','c026_B','c026_strong_lock');"
admin <<'SQL'
BEGIN;
DROP TABLE c026_triage.probe;
DROP SCHEMA c026_triage;
COMMIT;
SELECT to_regnamespace('c026_triage') IS NULL AS fixture_removed;
SQL
~~~

Required: no actors, fixture_removed true. Resolve owners before retrying bounded cleanup. No server/role defaults or statistics need restoration.

Acceptance requires real baseline/held/blocked/sleep/strong-lock/recovery evidence, explicit collection status, final value 100, scoped cleanup and a defensible triage narrative. Static checks and mocked orchestration do not verify PostgreSQL wait/publication behavior.
