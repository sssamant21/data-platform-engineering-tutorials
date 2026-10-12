# Chapter 028 Lab — Planner Estimates, Statistics and Extended Statistics

**Scope:** Chapter 004 disposable PostgreSQL 18 primary, database ops_lab. Run as its non-root OS owner from the repository root. No production targets. No server restart, global settings, activity-statistics resets or application-table changes.

**Prerequisites:** Chapters 004, 026 and 027; psql 18, Python 3 and a running primary. Use a fresh shell. All fixture DDL and maintenance uses lab_admin; fixed bounded plans use lab_app. Runtime verification is pending in the authoring environment.

## 1. Verify target and create a private evidence directory

~~~bash
set -euo pipefail
test -n "$PG_LAB_ROOT"
[[ "$(id -u)" != 0 ]] || { echo 'Run as the lab OS owner'; exit 2; }
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=3 PGSSLMODE=disable PGGSSENCMODE=disable
admin() {
  PGAPPNAME=c028_control PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
app() {
  PGAPPNAME=c028_app PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms -c transaction_timeout=5s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc "SELECT to_regnamespace('c028_stats') IS NULL")" == t ]] || {
  echo 'Existing fixture: investigate ownership and prior run; do not overwrite it'; exit 2;
}
umask 077
evidence="$(mktemp -d "$PG_LAB_ROOT/c028-evidence.XXXXXXXX")"
admin -Atc "SELECT clock_timestamp(),current_setting('server_version'),current_database(),current_user,current_setting('default_statistics_target')" \
  > "$evidence/environment.txt"
admin -f postgresql/scripts/028-statistics-setup.sql > "$evidence/setup.txt" 2>&1
~~~

Setup creates 20,000 rows, with a=b and exactly 100 distinct pairs. The primary key only indexes id. No predicate index is introduced, so this exercise tests estimates rather than index design. CREATE SCHEMA fails if the namespace already exists; setup DDL/data commits atomically, followed by explicit ANALYZE. If that maintenance fails, stop and inspect the fixture before resuming.

## 2. Prove fixture truth and collect baseline plans

~~~bash
admin -Atc "SELECT count(*),count(DISTINCT (a,b)),count(*) FILTER (WHERE a=7 AND b=7),count(*) FILTER (WHERE a=7 AND b=8) FROM c028_stats.correlated" \
  > "$evidence/truth.txt"
[[ "$(cat "$evidence/truth.txt")" == '20000|100|200|0' ]] || exit 2

capture() {
  [[ "$#" == 2 ]] || return 2
  [[ "$1" =~ ^[a-z][a-z0-9_-]*$ ]] || return 2
  [[ "$2" == compatible || "$2" == incompatible || "$2" == groups ]] || return 2
  (
    set -o noclobber
    app -qAt -v shape="$2" -f postgresql/scripts/028-statistics-plan.sql \
      > "$evidence/$1.json" 2> "$evidence/$1.stderr"
    python3 postgresql/scripts/027-plan-summary.py "$evidence/$1.json" \
      > "$evidence/$1.summary.json"
  )
}
capture baseline-compatible compatible
capture baseline-incompatible incompatible
capture baseline-groups groups
admin -f postgresql/scripts/028-statistics-inventory.sql > "$evidence/baseline-inventory.txt"
~~~

If capture fails, treat its files as incomplete evidence. Use a new label after correcting the cause; never relabel a partial JSON file as success. The plan script permits only three fixed synthetic SELECT shapes and executes them in a read-only transaction with local budgets. It uses literal parameters and disables parallel plans locally to simplify per-loop comparison.

For compatible predicates, independence suggests roughly 2 estimated rows against 200 actual. The incompatible case has 0 actual rows. For grouping, look at the aggregate's estimated groups versus 100 actual groups, not merely its input scan. Plan node types and precise estimates are observations, not hard-coded pass conditions.

## 3. Raise only single-column targets

~~~bash
admin > "$evidence/higher-target-maintenance.txt" 2>&1 <<'SQL'
ALTER TABLE c028_stats.correlated ALTER COLUMN a SET STATISTICS 250;
ALTER TABLE c028_stats.correlated ALTER COLUMN b SET STATISTICS 250;
ANALYZE c028_stats.correlated;
SQL
capture higher-target-compatible compatible
admin -f postgresql/scripts/028-statistics-inventory.sql > "$evidence/higher-target-inventory.txt"
admin > "$evidence/restore-target-maintenance.txt" 2>&1 <<'SQL'
ALTER TABLE c028_stats.correlated ALTER COLUMN a SET STATISTICS -1;
ALTER TABLE c028_stats.correlated ALTER COLUMN b SET STATISTICS -1;
ANALYZE c028_stats.correlated;
SQL
~~~

The new fixture's original targets were -1 (inherit default). Confirm this in baseline inventory. Raising a and b targets can improve individual distributions but does not describe their relationship. Explain why a compatibility estimate can remain wrong despite fresh, detailed individual statistics. Restore targets before testing extended kinds.

## 4. Dependencies: compatible predicates and a counterexample

~~~bash
admin > "$evidence/dependencies-maintenance.txt" 2>&1 <<'SQL'
CREATE STATISTICS c028_stats.ab_dependencies (dependencies)
ON a,b FROM c028_stats.correlated;
ANALYZE c028_stats.correlated;
SQL
capture dependencies-compatible compatible
capture dependencies-incompatible incompatible
admin -f postgresql/scripts/028-statistics-inventory.sql > "$evidence/dependencies-inventory.txt"
admin -c 'DROP STATISTICS c028_stats.ab_dependencies;' > "$evidence/dependencies-drop.txt"
~~~

Expect the compatible estimate to move toward 200. The incompatible estimate may also remain positive: dependencies recognize redundancy but do not enforce a=b or evaluate every allowed pair. The inventory shows the dependency summary; no raw MCV values are exported. Explain why this object alone is insufficient for a workload dominated by contradictory combinations.

## 5. MCV: joint combinations

~~~bash
admin > "$evidence/mcv-maintenance.txt" 2>&1 <<'SQL'
CREATE STATISTICS c028_stats.ab_mcv (mcv)
ON a,b FROM c028_stats.correlated;
ALTER STATISTICS c028_stats.ab_mcv SET STATISTICS 100;
ANALYZE c028_stats.correlated;
SQL
capture mcv-compatible compatible
capture mcv-incompatible incompatible
admin -f postgresql/scripts/028-statistics-inventory.sql > "$evidence/mcv-inventory.txt"
admin -c 'DROP STATISTICS c028_stats.ab_mcv;' > "$evidence/mcv-drop.txt"
~~~

The 100 frequent pairs can be represented by the MCV list. Compare compatible and incompatible estimates with baseline and dependencies. A positive estimate of one for an impossible pair can reflect row-estimate clamping; actual zero remains the truth. Record mcv_entries and sample behavior rather than assuming every real-world combination will be captured.

## 6. Multi-column distinct counts

~~~bash
admin > "$evidence/ndistinct-maintenance.txt" 2>&1 <<'SQL'
CREATE STATISTICS c028_stats.ab_ndistinct (ndistinct)
ON a,b FROM c028_stats.correlated;
ANALYZE c028_stats.correlated;
SQL
capture ndistinct-groups groups
capture ndistinct-compatible compatible
admin -f postgresql/scripts/028-statistics-inventory.sql > "$evidence/ndistinct-inventory.txt"
~~~

Expect the group estimate to move toward 100. Compare the compatible WHERE estimate too: ndistinct is not a replacement for dependency or MCV predicate estimates. Each preceding object was dropped so improvements can be attributed to one kind at a time.

## 7. Acceptance report

Fill this table from actual evidence; leave runtime-dependent cells pending until executed.

| Phase | Compatible estimated / actual rows | Incompatible estimated / actual rows | Estimated / actual groups | Explanation |
|---|---|---|---|---|
| Baseline | Pending / 200 expected | Pending / 0 expected | Pending / 100 expected | Independent summaries |
| Higher column targets | Pending / 200 expected | Not captured | Not captured | More detail, same relationship gap |
| Dependencies | Pending / 200 expected | Pending / 0 expected | Not captured | Redundancy; contradiction limitation |
| MCV | Pending / 200 expected | Pending / 0 expected | Not captured | Joint frequencies |
| ndistinct | Pending / 200 expected | Not captured | Pending / 100 expected | Group counts |

Add per-node q-error where both values are positive; report zero-actual cases separately. Record maintenance success/warnings, actual targets, statistics kinds, plan shape, execution time and buffers. Do not claim tiny fixture timings predict production gains. Explain why extended statistics will not directly solve a cross-table join-selectivity error in PostgreSQL 18.

## 8. Cleanup and verify

Only after confirming this session created the guarded fixture:

~~~bash
admin > "$evidence/cleanup.txt" 2>&1 <<'SQL'
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='5s';
DROP STATISTICS c028_stats.ab_ndistinct;
DROP TABLE c028_stats.correlated;
DROP SCHEMA c028_stats;
COMMIT;
SQL
[[ "$(admin -Atc "SELECT to_regnamespace('c028_stats') IS NULL")" == t ]] || exit 2
admin -Atc "SELECT clock_timestamp(),to_regnamespace('c028_stats') IS NULL" \
  > "$evidence/cleanup-verification.txt"
printf 'Evidence: %s\n' "$evidence"
~~~

A failed cleanup transaction rolls back its drops. For an interrupted earlier phase, inspect the schema and statistics ownership with admin before removing exactly the known object(s) that remain. Do not apply the final block blindly when ab_ndistinct was never created, and do not use CASCADE. Retain private evidence according to team policy.

**Completion:** all fixture truth and plan captures succeeded, the table is filled with observed estimates, limitations are explained, targets restored before extended-statistics tests, and the namespace is absent after cleanup.

[Return to chapter](../chapters/028-planner-estimates-statistics-and-extended-statistics.md)
