# Chapter 031 Lab — B-tree and Other Index Types: Operational Tradeoffs

**Target:** Chapter 004 disposable PostgreSQL 18 primary, ops_lab, port 55432. Run from the repository root as the non-root lab owner. Prerequisites: psql 18, Python 3, Chapters 027–030.

**Scope:** 50,000 synthetic rows in one guarded schema. No extensions, production targets, global settings, resets or cache dropping. Regular index builds are appropriate only for this isolated fixture; production deployment needs a separate lock/load plan.

## 1. Guard the lab and create the fixture

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
  PGAPPNAME=c031_control PGOPTIONS='-c statement_timeout=20s -c lock_timeout=1s -c maintenance_work_mem=8MB -c max_parallel_maintenance_workers=0' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
app() {
  PGAPPNAME=c031_plan PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms -c transaction_timeout=5s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc "SELECT to_regnamespace('c031_indexes') IS NULL")" == t ]] || {
  echo 'Existing fixture: investigate; do not overwrite'; exit 2;
}
umask 077
evidence="$(mktemp -d "$PG_LAB_ROOT/c031-evidence.XXXXXXXX")"
admin -f postgresql/scripts/031-index-types-setup.sql > "$evidence/setup.txt" 2>&1
~~~

The id primary key creates a B-tree from the start. It does not cover the tested predicates. event_key repeats 10,000 values; ordered_at follows insertion order; scattered_at permutes the same time domain. tags contains a rare component, span contains ten integers, and location is an integer point grid.

Setup DDL/data commits atomically, followed by ANALYZE. On failure, inspect the fixture and errors before resuming. Do not silently recreate it.

## 2. Establish truth and baseline plans

~~~bash
admin -At > "$evidence/truth.txt" <<'SQL'
SELECT count(*),
 count(*) FILTER(WHERE event_key=42),
 count(*) FILTER(WHERE event_key>=42 AND event_key<92),
 count(*) FILTER(WHERE tags @> ARRAY['rare']::text[]),
 count(*) FILTER(WHERE span @> 4242),
 count(*) FILTER(WHERE location <@ box(point(10,10),point(12,12))),
 count(*) FILTER(WHERE ordered_at>=timestamp '2026-01-01 01:00:00'
                    AND ordered_at<timestamp '2026-01-01 01:01:40'),
 count(*) FILTER(WHERE scattered_at>=timestamp '2026-01-01 01:00:00'
                    AND scattered_at<timestamp '2026-01-01 01:01:40')
FROM c031_indexes.events;
SQL
[[ "$(cat "$evidence/truth.txt")" == '50000|5|250|50|10|9|100|100' ]] || exit 2
capture() {
  [[ "$#" == 2 || "$#" == 3 ]] || return 2
  [[ "$1" =~ ^[a-z][a-z0-9_-]*$ ]] || return 2
  (
    set -o noclobber
    app -qAt -v shape="$2" -v diagnostic="${3:-off}" \
      -f postgresql/scripts/031-index-types-plan.sql \
      > "$evidence/$1.json" 2> "$evidence/$1.stderr"
    python3 postgresql/scripts/027-plan-summary.py "$evidence/$1.json" \
      > "$evidence/$1-summary.json"
  )
}
for shape in eq range tags span points ordered scattered; do
  capture "baseline-$shape" "$shape"
done
admin -f postgresql/scripts/031-index-types-inventory.sql > "$evidence/baseline-inventory.txt"
~~~

The plan script accepts only these fixed synthetic queries and diagnostic=off/on. Plans execute in READ ONLY transactions with local time/lock/memory budgets and parallel scans disabled. Default planning is the acceptance baseline.

A failed capture leaves incomplete evidence; correct the cause and use a new label. Do not overwrite it or treat an empty plan as success. Look at actual rows per scan and compare with truth.txt.

## 3. B-tree versus Hash on the same key

~~~bash
admin > "$evidence/btree-build.txt" 2>&1 <<'SQL'
\timing on
CREATE INDEX event_key_btree ON c031_indexes.events USING btree(event_key);
SQL
capture btree-eq eq
capture btree-range range
admin -f postgresql/scripts/031-index-types-inventory.sql > "$evidence/btree-inventory.txt"
admin -c 'DROP INDEX c031_indexes.event_key_btree;' > "$evidence/btree-drop.txt"

admin > "$evidence/hash-build.txt" 2>&1 <<'SQL'
\timing on
CREATE INDEX event_key_hash ON c031_indexes.events USING hash(event_key);
SQL
capture hash-eq eq
capture hash-range range
admin -f postgresql/scripts/031-index-types-inventory.sql > "$evidence/hash-inventory.txt"
admin -c 'DROP INDEX c031_indexes.event_key_hash;' > "$evidence/hash-drop.txt"
~~~

Only one candidate on event_key exists at a time. Compare equality plans, size and heap work. The range predicate can use the B-tree but is not supported by Hash. A planner choice of sequential scan is an observation, not a failed installation.

No UNIQUE constraint is attempted with Hash. The primary key remains intact. Do not infer write or recovery superiority from a small cached read.

## 4. GIN, GiST and SP-GiST with native operators

~~~bash
admin > "$evidence/specialized-builds.txt" 2>&1 <<'SQL'
\timing on
CREATE INDEX tags_gin ON c031_indexes.events USING gin(tags);
CREATE INDEX span_gist ON c031_indexes.events USING gist(span);
CREATE INDEX location_spgist ON c031_indexes.events USING spgist(location);
SQL
capture gin-tags tags
capture gist-span span
capture spgist-points points
admin -f postgresql/scripts/031-index-types-inventory.sql > "$evidence/specialized-inventory.txt"
~~~

Expect the planner to consider GIN for array containment, GiST for range containment and SP-GiST for point-in-box. Inspect actual index names/operator classes, actual rows and any rechecks. These predicates have different meanings; their timings do not form a universal method ranking.

For GIN, define a follow-up write test covering component counts, insert/update concurrency and pending-list cleanup. For GiST/SP-GiST, define representative distributions and overlap/duplicate cases. This lab does not perform a production write benchmark.

## 5. BRIN on ordered versus scattered time

~~~bash
admin > "$evidence/brin-builds.txt" 2>&1 <<'SQL'
\timing on
CREATE INDEX ordered_brin ON c031_indexes.events USING brin(ordered_at)
 WITH (pages_per_range=16);
CREATE INDEX scattered_brin ON c031_indexes.events USING brin(scattered_at)
 WITH (pages_per_range=16);
SQL
capture brin-ordered ordered
capture brin-scattered scattered
admin -f postgresql/scripts/031-index-types-inventory.sql > "$evidence/brin-inventory.txt"
~~~

Both predicates return 100 rows. Compare their column/physical correlation, chosen scan, heap blocks and rows removed by index recheck. The index build summarizes existing ranges. Subsequent ingestion would need a summarization policy; this fixture does not test unsummarized future ranges.

If the default planner avoids scattered_brin, retain that default plan. You may then run this separately labeled diagnostic:

~~~bash
capture brin-scattered-diagnostic scattered on
~~~

This sets enable_seqscan=off locally and only discourages sequential scans. Confirm the actual chosen plan before interpreting BRIN rechecks. It is not a production tuning setting and is not counted as evidence that the index is faster. Local settings end at ROLLBACK.

## 6. Compare results and operational acceptance

Fill the table with observed results, not expected node names:

| Candidate | Predicate | Actual rows | Method/class and size | Default scan / heap work | Decision and limitation |
|---|---|---|---|---|---|
| B-tree | Equality / range | 5 / 250 expected | Pending | Pending | Pending |
| Hash | Equality / range | 5 / 250 expected | Pending | Pending | Pending |
| GIN | Array containment | 50 expected | Pending | Pending | Pending |
| GiST | Range contains integer | 10 expected | Pending | Pending | Pending |
| SP-GiST | Point in box | 9 expected | Pending | Pending | Pending |
| BRIN ordered | Time window | 100 expected | Pending | Pending | Pending |
| BRIN scattered | Time window | 100 expected | Pending | Pending | Pending |

All retained plans must parse with the Chapter 027 helper; validate raw plans for specialized fields it omits. Inspect validity/readiness and primary/unique flags in each inventory. Record build completion/errors and size in bytes.

Use measured default plans to explain which candidate reduces work for its operation. Compare identical predicates where available. Account for cache warming, estimated/actual rows, heap visits and inclusive buffer counts. Do not sum parent/child buffers or invent a device-I/O result from shared reads.

Write an acceptance plan for:
- Representative read and write concurrency, key/component distribution and correctness.
- WAL/replica lag, disk growth, cache pressure and maintenance latency.
- Production build lock/load limits, progress and failed-build cleanup.
- Rare jobs and constraint dependencies before index removal.
- Restore/upgrade validation and extension compatibility if extensions are proposed.
- Rollback owner, exact object scope and service acceptance window.

The small fixture cannot establish stable tail latency, bloat growth or crash/recovery performance. Record these as unverified, not passed.

## 7. Scoped rollback and cleanup

Hash and the candidate B-tree were already removed. The remaining five candidate indexes are removed explicitly; the primary-key index is removed only with its disposable table.

~~~bash
admin > "$evidence/cleanup.txt" 2>&1 <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DROP INDEX c031_indexes.tags_gin;
DROP INDEX c031_indexes.span_gist;
DROP INDEX c031_indexes.location_spgist;
DROP INDEX c031_indexes.ordered_brin;
DROP INDEX c031_indexes.scattered_brin;
DROP TABLE c031_indexes.events;
DROP SCHEMA c031_indexes;
COMMIT;
SQL
[[ "$(admin -Atc "SELECT to_regnamespace('c031_indexes') IS NULL")" == t ]] || exit 2
admin -Atc "SELECT clock_timestamp(),to_regnamespace('c031_indexes') IS NULL" \
  > "$evidence/cleanup-verification.txt"
printf 'Evidence: %s\n' "$evidence"
~~~

If a previous step failed, inspect which known objects this run created and adjust the exact drop list accordingly. Do not run the final block blindly when a listed index is absent; its transaction will roll back. Never use CASCADE or remove an unrelated/constraint-backed production index.

**Completion:** truth verified; baseline/default indexed plans retained; B-tree/Hash isolated; specialized operators explained; BRIN physical-layout effect observed or its visibility gap recorded; lifecycle acceptance plan complete; namespace absent.

**Runtime status:** execution pending in the authoring environment.

[Return to chapter](../chapters/031-b-tree-and-other-index-types-operational-tradeoffs.md)
