# Lab 023 — Query Families and Interval Rankings

PostgreSQL 18; DBRE/SRE only. Runtime verification pending.
[Chapter](../chapters/023-query-statistics-with-pg-stat-statements.md) · [Collector](../scripts/023-query-statistics-snapshot.sql) · [Ranking helper](../scripts/023-query-window-rank.py)

## Scope

Use the Chapter 004 disposable cluster, not a supervised production server. This lab briefly stops all three lab nodes, starts only the primary with temporary preload options, creates database c023_queries, then restores normal startup. Close earlier actors first.

No configuration file is edited. pg_ctl restart can reuse previous command-line options, so restoration uses an explicit stop followed by normal Chapter 004 start, not an unqualified restart.

## 1. Preflight and guard

From repository root, as the non-root Chapter 004 owner:

~~~bash
set -euo pipefail
test -n "$PG_LAB_ROOT"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
[[ "$(pg_ctl --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable
admin() {
  PGAPPNAME=c023_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
admin23() {
  PGAPPNAME=c023_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d c023_queries "$@"
}
app23() {
  PGAPPNAME=c023_workload PGOPTIONS='-c statement_timeout=3s -c lock_timeout=1s -c transaction_timeout=10s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d c023_queries "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc 'SHOW shared_preload_libraries')" == "" ]] || exit 2
[[ "$(admin -Atc 'SHOW compute_query_id')" == auto ]] || exit 2
[[ "$(admin -Atc "SELECT count(*) FROM pg_available_extensions WHERE name='pg_stat_statements'")" == 1 ]] || exit 2
~~~

The empty preload/auto-query-ID baseline is a deliberate precondition. If it fails, investigate rather than overwrite settings. Install the matching PostgreSQL 18 extension package on the lab host if the extension is unavailable; package names depend on its distribution.

Do not expose the passfile. Adjust repository script paths only if your working directory differs.

## 2. Start with temporary preload options

Close all interactive clients. Then:

~~~bash
bash postgresql/scripts/004-operations-lab.sh stop
pg_ctl -D "$PG_LAB_ROOT/primary" -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 \
  -o "-c shared_preload_libraries=pg_stat_statements -c compute_query_id=on -c pg_stat_statements.track=top -c pg_stat_statements.track_utility=off -c pg_stat_statements.track_planning=off" start
admin -c 'SHOW shared_preload_libraries;'
admin -c 'SHOW compute_query_id;'
~~~

Expected: pg_stat_statements and on. Standbys stay stopped during measurements; they catch up after restoration.

If startup fails or times out, inspect pg_ctl status and the primary log. A timeout does not prove the server is stopped. If it is running, stop it cleanly, then use normal Chapter 004 start without these options. Fix the missing/incompatible library before attempting the lab again. Do not leave the lab cluster unavailable.

## 3. Install the interface and seed query families

In the running primary:

~~~bash
admin -c 'CREATE DATABASE c023_queries OWNER lab_admin;'
admin23 <<'SQL'
CREATE EXTENSION pg_stat_statements WITH SCHEMA public;
BEGIN;
CREATE SCHEMA c023_queries AUTHORIZATION lab_admin;
CREATE TABLE c023_queries.items (id integer PRIMARY KEY, grp integer, payload text);
INSERT INTO c023_queries.items
SELECT i, i%100, repeat('x',512) FROM generate_series(1,5000) AS g(i);
GRANT USAGE ON SCHEMA c023_queries TO lab_app, lab_observer;
GRANT SELECT ON c023_queries.items TO lab_app;
COMMIT;
ANALYZE c023_queries.items;
SELECT extversion FROM pg_extension WHERE extname='pg_stat_statements';
SELECT * FROM public.pg_stat_statements_info;
SQL
app23 <<'SQL'
SHOW compute_query_id;
SHOW pg_stat_statements.track;
SHOW pg_stat_statements.track_planning;
SELECT payload FROM c023_queries.items WHERE id=1;
SELECT sum(length(payload)) FROM c023_queries.items WHERE grp=0;
SELECT pg_sleep(0.05);
SQL
~~~

Expect on/top/off. Existing database or extension is a precondition failure; investigate prior work.

These three completed statements seed entries before the baseline. The payload lookup, group scan and sleep have different structures. Constants in later variants should normalize into their existing families. No nested DO-loop workload is used because track=top would record the outer command rather than every nested statement.

## 4. Capture text-free samples and generate work

Define in the same guarded shell:

~~~bash
umask 077
evidence="$PG_LAB_ROOT/c023-evidence"
[[ ! -L "$evidence" ]] || exit 2
mkdir -p -m 700 "$evidence"
[[ -d "$evidence" && -O "$evidence" ]] || exit 2
capture23() {
  local name="$1"
  [[ "$name" =~ ^[A-Za-z0-9_-]+\.json$ ]] || return 2
  (
    set -o noclobber
    PGAPPNAME=c023_collector PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
      psql -X -w -qAt -v ON_ERROR_STOP=1 -v source_id=chapter004-primary-55432 \
      -h 127.0.0.1 -p 55432 -U lab_observer -d c023_queries \
      -f postgresql/scripts/023-query-statistics-snapshot.sql > "$evidence/$name"
  )
}
capture23 before.json
python3 -m json.tool "$evidence/before.json"
~~~

Expected: queryid strings and no query text; metadata includes global_reset, dealloc, per-entry stats_since and effective collector policy. Existing filenames are refused; failed samples may be partial and must not be interpreted as zero work.

Generate bounded SQL locally and execute it as ordinary top-level client statements:

~~~bash
python3 - "$evidence/workload.sql" <<'PY'
from pathlib import Path
import sys
lines = [f"SELECT payload FROM c023_queries.items WHERE id={i};" for i in range(1,41)]
lines += [f"SELECT sum(length(payload)) FROM c023_queries.items WHERE grp={i};" for i in range(10)]
lines += ["SELECT pg_sleep(0.05);" for _ in range(3)]
with Path(sys.argv[1]).open("x", encoding="utf-8") as output:
    output.write("\n".join(lines) + "\n")
PY
app23 -f "$evidence/workload.sql" > "$evidence/workload-results.txt"
capture23 after.json
python3 postgresql/scripts/023-query-window-rank.py "$evidence/before.json" "$evidence/after.json"
~~~

Expected family call deltas: 40 lookups, 10 scans and three sleeps. No entry should need a new baseline for these already seeded families. Other statements may exist; identify the three fixture queryids through controlled client query IDs or a restricted text inspection in this fully synthetic lab.

For this lab only, admin23 may query representative text filtered to c023_queries/lab_app to map its synthetic families. Keep text out of production exports; do not assume normalization always removes sensitive values.

The helper ranks by execution-time delta. Sleep often dominates elapsed time, while lookups dominate call count; actual ordering depends on host conditions. Compare aggregate contribution with interval mean and buffer deltas. Never subtract cumulative means or claim a p99 from this output.

## 5. Show that execution failures are not successful calls

Capture a new baseline and run a deliberate statement timeout:

~~~bash
capture23 before-error.json
if app23 <<'SQL'
SET statement_timeout='100ms';
SELECT pg_sleep(2);
SQL
then
  echo "Unexpected completion"; exit 2
else
  echo "Expected timeout; retain the original client error"
fi
capture23 after-error.json
python3 postgresql/scripts/023-query-window-rank.py \
  "$evidence/before-error.json" "$evidence/after-error.json"
~~~

The sleep family should not gain one completed execution call from its failed execution. The client received a failure despite a zero successful-call delta. Planning statistics were disabled; enabling them would introduce separate successful-planning accounting.

This is why pg_stat_statements cannot supply application availability denominators. Check effective settings and normalized identity if observed counts differ. No connection pool behavior or end-to-end deadline is measured here.

## 6. Demonstrate a scoped reset boundary

Keep the previous evidence. Reset only this disposable database and the lab_app cohort with all selectors explicit:

~~~bash
capture23 pre-reset.json
admin23 <<'SQL'
SELECT public.pg_stat_statements_reset(
  userid => r.oid, dbid => d.oid, queryid => 0, minmax_only => false)
FROM pg_roles r CROSS JOIN pg_database d
WHERE r.rolname='lab_app' AND d.datname='c023_queries'
  AND d.oid <> 0 AND r.oid <> 0
  AND current_database()='c023_queries';
SQL
capture23 post-reset.json
python3 postgresql/scripts/023-query-window-rank.py \
  "$evidence/pre-reset.json" "$evidence/post-reset.json"
~~~

This resets all query IDs only for the specified role/database. Omitted/zero role and database selectors would broaden scope; do not run an unqualified reset.

Expected: changed entry epochs are excluded, or removed entries are reported disappeared. The global full-reset marker need not change for this selective reset. A valid envelope with excluded/disappeared entries does not mean those entry intervals were valid.

Seed the three statements again, capture a fresh baseline, execute a small fresh workload and compare it. Do not bridge the selective reset by clamping negative deltas. minmax_only is not exercised: its extrema epoch differs from the cumulative-counter epoch.

## 7. Offline cases and operational interpretation

Use labeled synthetic copies outside the live evidence set. Verify rejection when source, server restart, extension version, policy, global_reset or dealloc changes. Set truncated true and verify refusal. Add a new query entry and verify it is excluded pending a baseline. Remove an entry and verify disappeared reporting.

Change stats_since while increasing counters: the entry must be excluded. Keep its epoch but decrease a counter: also excluded. A zero-call interval must have null interval_mean_exec_ms. Duplicate entry keys, invalid bigint query IDs, malformed counters and stale/gapped timestamps must fail.

Choose one measured candidate and write a short incident note: identity, interval, call growth, aggregate/mean execution time, resource evidence, next diagnostic action and missing application evidence. State why the statistics do not prove CPU saturation, committed row outcomes or latency percentiles.

## 8. Cleanup and restore all three nodes

Close every client connected to c023_queries. From ops_lab:

~~~bash
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='c023_queries';"
admin -c 'DROP DATABASE c023_queries;'
~~~

Require zero sessions before DROP; no FORCE option is used. Resolve owners if cleanup fails. Database-local extension interfaces are removed with the database; the preloaded module remains active until the next stop.

Restore startup without temporary command-line settings:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" -m fast -w -t 30 stop
bash postgresql/scripts/004-operations-lab.sh start
[[ "$(admin -Atc 'SHOW shared_preload_libraries')" == "" ]] || exit 2
[[ "$(admin -Atc 'SHOW compute_query_id')" == auto ]] || exit 2
admin -c "SELECT NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='c023_queries') AS fixture_database_removed;"
~~~

Chapter 004 start verifies the original primary/two-standby topology and its own probe. Normal startup rewrites postmaster.opts; future restarts must not reuse this lab's temporary settings. No manual deletion of internal extension statistics files is needed.

Acceptance: full activation evidence; normalized family deltas; text-free snapshots; timeout/client failure with no completed-call increment; scoped-reset exclusion; new-baseline recovery; fixture removed; original preload/query-ID settings and replication topology restored. Static/offline checks alone do not verify these PostgreSQL behaviors.
