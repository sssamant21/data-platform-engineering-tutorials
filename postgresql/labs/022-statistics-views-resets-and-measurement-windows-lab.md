# Lab 022 — Statistics Caching, Resets and Valid Windows

Audience: DBRE/SRE. PostgreSQL 18. Live execution pending.
[Chapter](../chapters/022-statistics-views-resets-and-measurement-windows.md) · [JSON collector](../scripts/022-database-statistics-snapshot.sql) · [Delta helper](../scripts/022-statistics-window-delta.py)

## Scope and safety

Create a separate database c022_stats on the Chapter 004 disposable primary. Only this new database's statistics are deliberately reset. Do not reset ops_lab, shared counters or a production database.

Use operator O and observer M. Run from repository root or adjust script paths. Keep observations below the five-minute comparison gap. Do not restart or crash the cluster to learn reset arithmetic: offline fixtures cover those invalid boundaries.

## 1. Guard the cluster and create an isolated database

In O, use the non-root Chapter 004 owner and exported PG_LAB_ROOT:

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
  PGAPPNAME=c022_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
admin22() {
  PGAPPNAME=c022_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d c022_stats "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc 'SHOW track_counts')" == on ]] || exit 2
~~~

Provision once in O:

~~~bash
admin -c 'CREATE DATABASE c022_stats OWNER lab_admin;'
admin22 <<'SQL'
BEGIN;
CREATE SCHEMA c022_metrics AUTHORIZATION lab_admin;
CREATE TABLE c022_metrics.probe (id integer PRIMARY KEY, value integer NOT NULL);
INSERT INTO c022_metrics.probe SELECT i, 0 FROM generate_series(1,100) AS g(i);
GRANT USAGE ON SCHEMA c022_metrics TO lab_app, lab_observer;
GRANT SELECT, UPDATE ON c022_metrics.probe TO lab_app;
GRANT SELECT ON c022_metrics.probe TO lab_observer;
COMMIT;
ANALYZE c022_metrics.probe;
SQL
~~~

An existing database/schema is a precondition failure. Investigate ownership and a prior attempt rather than automatically dropping it. The Chapter 004 passfile has wildcard database entries, so no new password file is required. Do not print credentials.

## 2. Capture a bounded baseline

In O define:

~~~bash
umask 077
evidence="$PG_LAB_ROOT/c022-evidence"
[[ ! -L "$evidence" ]] || exit 2
mkdir -p -m 700 "$evidence"
[[ -d "$evidence" && -O "$evidence" ]] || exit 2
capture22() {
  local name="$1"
  [[ "$name" =~ ^[A-Za-z0-9_-]+\.json$ ]] || return 2
  (
    set -o noclobber
    PGAPPNAME=c022_collector PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
      psql -X -w -qAt -v ON_ERROR_STOP=1 -v source_id=chapter004-primary-55432 \
      -h 127.0.0.1 -p 55432 -U lab_observer -d c022_stats \
      -f postgresql/scripts/022-database-statistics-snapshot.sql > "$evidence/$name"
  )
}
capture22 before.json
python3 -m json.tool "$evidence/before.json"
~~~

The collector returns one JSON document; quiet/unaligned/tuples-only psql output is required. Existing filenames are refused. A failed collection can leave a partial file; retain it as failed evidence and use another basename rather than treating it as a zero sample.

Identify database name/OID, endpoint, source_id, postmaster start, stats_reset, snapshot_at, sampled_at and track_counts. numbackends is a point gauge. The collector reads no fixture rows and does not reset statistics.

## 3. Demonstrate a cached observer

In M repeat only the guard/export/function block, not provisioning. Open an interactive monitoring connection:

~~~bash
PGAPPNAME=c022_cached_observer \
PGOPTIONS='-c statement_timeout=5s -c transaction_timeout=120s -c idle_in_transaction_session_timeout=120s' \
  psql -X -w -h 127.0.0.1 -p 55432 -U lab_observer -d c022_stats
~~~

In M:

~~~sql
\pset pager off
BEGIN READ ONLY;
SET LOCAL stats_fetch_consistency = 'cache';
SELECT relid, n_tup_upd
FROM pg_stat_user_tables
WHERE schemaname='c022_metrics' AND relname='probe';
~~~

Record the first value. In O run a fresh application connection:

~~~bash
PGAPPNAME=c022_workload PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s -c transaction_timeout=15s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d c022_stats <<'SQL'
SHOW track_counts;
BEGIN;
UPDATE c022_metrics.probe SET value=value+1;
COMMIT;
SQL
~~~

Expect track_counts on and UPDATE 100. Wait briefly for publication. In M, without ending its observer transaction, repeat the same SELECT: it should return the cached value. Then:

~~~sql
SELECT pg_stat_clear_snapshot();
SELECT relid, n_tup_upd
FROM pg_stat_user_tables
WHERE schemaname='c022_metrics' AND relname='probe';
COMMIT;
\q
~~~

The fresh access should show the published updates. If it does not, use a new short transaction and a bounded recheck; do not repeatedly reset counters to force the expected result. Stay within M's two-minute guards.

Clearing the snapshot changed the observer's cache, not the database's accumulated history. No reset function was used in this step.

## 4. Calculate an ordinary interval

In O:

~~~bash
capture22 after.json
python3 postgresql/scripts/022-statistics-window-delta.py \
  "$evidence/before.json" "$evidence/after.json"
~~~

Expect valid true, a positive elapsed interval and nonnegative counter deltas. Transactions from collectors, control connections and background work contribute: do not assert exactly one new xact_commit for the UPDATE transaction.

Inspect numbackends_points. A change there is not a counter reset and should not be divided into a transaction rate. If block-access deltas are both zero, interval_buffer_hit_ratio is null. PostgreSQL buffer hits/misses do not prove disk latency or application SLO compliance.

If the observation took more than 300 seconds, the helper refuses the gap. Start a fresh pair for the intended short window, or explicitly choose a larger maximum with an explanation of the lost temporal resolution.

## 5. Compare current-transaction statistics

Open a new lab_app connection to c022_stats with the same bounded workload options. Inside it:

~~~sql
BEGIN;
UPDATE c022_metrics.probe SET value=value+1 WHERE id<=5;
SELECT relid, n_tup_upd
FROM pg_stat_xact_user_tables
WHERE schemaname='c022_metrics' AND relname='probe';
ROLLBACK;
~~~

The transaction-local view should show its own five updates before transaction completion. The rollback undoes the row values; operational statistics are not a count of surviving business changes. Quit this connection.

Do not use tuple statistics as a substitute for application correctness. Verify actual values with an authorized fixture query only when needed, outside the metadata collector.

## 6. Reset only the newly created database

In O, first capture and verify the exact target:

~~~bash
capture22 pre-reset.json
[[ "$(admin22 -Atc 'SELECT current_database()')" == c022_stats ]] || exit 2
admin22 -c "SELECT pg_stat_reset() WHERE current_database()='c022_stats' AND NOT pg_is_in_recovery();"
admin22 -c 'ANALYZE c022_metrics.probe;'
capture22 post-reset.json
~~~

This is an explicit lab administrative mutation. The reset cannot restore old counters by ROLLBACK. ANALYZE addresses the reset's maintenance-counter implications for this fixture; the database will be dropped at cleanup.

Compare across the reset and capture the expected refusal without letting shell errexit hide the result:

~~~bash
if python3 postgresql/scripts/022-statistics-window-delta.py \
  "$evidence/pre-reset.json" "$evidence/post-reset.json"; then
  echo "Unexpected continuity across reset"; exit 2
else
  echo "Expected rejected window; inspect the JSON reason"
fi
~~~

Required: valid false with changed stats_reset. Counter decreases can also invalidate a window; they are not a replacement for the reset marker. Even if work has refilled the counters above their old values, this reset boundary remains invalid.

Do not call pg_stat_reset_shared or reset ops_lab to reproduce the example.

## 7. Start a new epoch and test offline boundaries

Treat post-reset.json as the new baseline. In O:

~~~bash
admin22 -c 'SELECT sum(value) FROM c022_metrics.probe;'
capture22 new-epoch.json
python3 postgresql/scripts/022-statistics-window-delta.py \
  "$evidence/post-reset.json" "$evidence/new-epoch.json"
~~~

Expect a valid same-epoch interval. If timestamps do not advance sufficiently, collect a fresh sample instead of editing them.

For offline exercises, copy samples to a separate temporary directory and clearly label them synthetic. Change source_id, recovery role, database OID or postmaster_start in one copy and verify refusal. Keep counters increasing but alter stats_reset to prove reset detection does not depend on a decrease. Decrease one counter without changing markers and verify refusal.

Also try repeated snapshot timestamps, reversed sample times, an excessive gap, missing counters and a zero-access valid interval. Never modify the live evidence files to force a passing result. The helper cannot discover an unrecorded table-only reset from the database reset marker; explain how an administrative reset log or a new object baseline would cover that limitation.

## 8. Cleanup and acceptance

Close M and all lab_app connections; stop no servers. In O:

~~~bash
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='c022_stats';"
~~~

Required: zero sessions. Resolve remaining clients through their own terminals. Then:

~~~bash
admin -c 'DROP DATABASE c022_stats;'
admin -c "SELECT NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='c022_stats') AS fixture_database_removed;"
~~~

DROP DATABASE runs from ops_lab, outside an explicit transaction, and has no FORCE option. If connections or locks remain, resolve their ownership before retrying. Preserve evidence files; source-server counters outside the isolated database were not deliberately reset. Session-only consistency settings end with the connections.

| Required evidence | Acceptance |
|---|---|
| Cached observer | Same value before cache clear; updated value after fresh access |
| Ordinary interval | Compatible identity/markers; valid nonnegative deltas |
| Transaction-local view | Five own updates visible before rollback |
| Scoped reset | New c022_stats reset marker; cross-reset interval refused |
| New epoch | Valid comparison from the post-reset baseline |
| Offline incompatibilities | Reset, restart/source/role/time/schema problems refused |
| Cleanup | No c022_stats sessions; fixture_database_removed true |

Retain exact server version, raw JSON, comparison outputs and reasons for rejected windows. Offline arithmetic and syntax review do not verify PostgreSQL publication/cache/reset behavior.
