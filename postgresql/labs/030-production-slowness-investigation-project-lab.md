# Chapter 030 Lab — Production Slowness Investigation Project

**Environment:** Chapter 004 disposable PostgreSQL 18 primary, ops_lab, port 55432. Run from the repository root as the non-root lab OS owner. This simulates production investigation; no fault injection targets production.

**Prerequisites:** Chapters 018, 020 and 026–029, psql 18 and Python 3. The environment must have a working lab_observer (pg_monitor), lab_app and lab_admin with the Chapter 004 private pgpass file.

**Resource budget:** 20,000 synthetic rows, one serial probe, one timed lock holder and bounded observers. No global changes, resets, broad signals, cache dropping or server restarts. Runtime verification remains pending.

## 1. Prepare and guard the target

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
  PGAPPNAME=c030_control PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
app() {
  PGAPPNAME=c030_plan PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms -c transaction_timeout=5s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
observe() {
  PGAPPNAME=c030_observer PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc "SELECT to_regnamespace('c030_incident') IS NULL")" == t ]] || exit 2
[[ "$(admin -Atc "SELECT count(*) FROM pg_stat_activity WHERE datname='ops_lab' AND application_name IN ('c030_blocker','c030_probe')")" == 0 ]] || exit 2
umask 077
evidence="$(mktemp -d "$PG_LAB_ROOT/c030-project.XXXXXXXX")"
admin -f postgresql/scripts/030-project-setup.sql > "$evidence/setup.txt" 2>&1
admin -Atc "SELECT clock_timestamp(),count(*),count(DISTINCT (a,b)),count(*) FILTER(WHERE a=7 AND b=7) FROM c030_incident.requests" \
  > "$evidence/truth.txt"
[[ "$(admin -Atc 'SELECT count(*) FROM c030_incident.requests WHERE a=7 AND b=7')" == 200 ]] || exit 2
cp postgresql/templates/030-slowness-investigation-report.md "$evidence/report.md"
~~~

Pre-existing namespaces or matching sessions are stop conditions: investigate, do not overwrite or signal them. Setup's DDL/data transaction is atomic; ANALYZE follows it. A failed setup/ANALYZE is not a completed fixture.

Review truth.txt: 20,000 rows, 100 distinct pairs, 200 matching rows. The probe's correct result is exactly 200. No predicate index is added.

## 2. Healthy baseline

~~~bash
bash postgresql/scripts/029-resource-window.sh c030-baseline > "$evidence/baseline-window.txt" 2>&1 &
window_job=$!
python3 postgresql/scripts/030-request-probe.py baseline > "$evidence/baseline.jsonl"
wait "$window_job"
app -qAt -f postgresql/scripts/030-project-plan.sql > "$evidence/before-plan.json" 2> "$evidence/before-plan.stderr"
python3 postgresql/scripts/027-plan-summary.py "$evidence/before-plan.json" > "$evidence/before-plan-summary.json"
~~~

The probe makes eight independent, serial connections, executes one fixed read-only count with a 700ms lock timeout and two-second statement limit, validates the result, and records duration including client/connection overhead. It does not retry requests. Guard/connection prerequisites fail before collection; a phase with request failures exits nonzero after retaining all eight observations.

Baseline must have eight successful correct results before continuing. Review the raw plan's input scan: count(*)'s aggregate returns one row and is not the relevant estimate comparison.

## 3. Simulate a maintenance lock and observe live impact

~~~bash
PGAPPNAME=c030_blocker PGOPTIONS='-c statement_timeout=20s -c lock_timeout=1s -c transaction_timeout=25s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  > "$evidence/blocker.txt" 2>&1 <<'SQL' &
BEGIN;
LOCK TABLE c030_incident.requests IN ACCESS EXCLUSIVE MODE;
SELECT pg_sleep(18);
ROLLBACK;
SQL
blocker_job=$!
ready=f
for attempt in $(seq 1 20); do
  ready="$(admin -Atc "SELECT EXISTS (
    SELECT 1 FROM pg_stat_activity
    WHERE datname='ops_lab' AND application_name='c030_blocker'
      AND state='active' AND wait_event='PgSleep'
      AND backend_start>clock_timestamp()-interval '30 seconds')")"
  [[ "$ready" == t ]] && break
  sleep 0.1
done
[[ "$ready" == t ]] || { wait "$blocker_job"; echo 'Blocker not ready: stop phase'; exit 2; }

bash postgresql/scripts/029-resource-window.sh c030-incident > "$evidence/incident-window.txt" 2>&1 &
window_job=$!
python3 postgresql/scripts/030-request-probe.py incident > "$evidence/incident.jsonl" 2> "$evidence/incident-probe.stderr" &
probe_job=$!
for sample in $(seq 1 8); do
  observe -f postgresql/scripts/030-project-observer.sql \
    > "$evidence/lock-$sample.txt" 2> "$evidence/lock-$sample.stderr"
  sleep 0.5
done
if wait "$probe_job"; then
  echo 'No request failures; inspect timing and whether the incident overlapped' > "$evidence/incident-status.txt"
else
  echo 'Probe returned failure; classify retained observations before claiming lock impact' > "$evidence/incident-status.txt"
fi
wait "$blocker_job"
wait "$window_job"
~~~

The holder deliberately waits while retaining an ACCESS EXCLUSIVE relation lock. The requests need conflicting read locks and can fail with SQLSTATE 55P03 (lock timeout). Distinguish this from 57014 (statement cancellation), authentication/connect errors, process timeout and wrong result.

Capture at least one live c030_probe Lock/relation observation and a blocking edge to the holder's PID plus backend_start. The metadata observer does not read the locked fixture. Repeated samples can still miss short waits; missing evidence is not a successful causal diagnosis.

The holder should be active in PgSleep while the request is blocked. Normal host CPU does not disprove the impact. Compare the Chapter 029 collector's activity with its optional host metrics; do not assume CPU, memory or storage conclusions from absent metrics.

Do not run EXPLAIN ANALYZE on the blocked fixture during this phase. The lock has a known lifetime, and statements have budgets. If a phase fails unexpectedly, preserve errors and wait for the known jobs before cleanup.

## 4. Containment and recovery before any planner change

~~~bash
observe -f postgresql/scripts/030-project-observer.sql > "$evidence/after-blocker.txt"
bash postgresql/scripts/029-resource-window.sh c030-recovered > "$evidence/recovered-window.txt" 2>&1 &
window_job=$!
python3 postgresql/scripts/030-request-probe.py recovered > "$evidence/recovered.jsonl"
wait "$window_job"
app -qAt -f postgresql/scripts/030-project-plan.sql > "$evidence/recovered-plan.json" 2> "$evidence/recovered-plan.stderr"
~~~

The timed holder rolls back in its own session and exits. Confirm that no holder or waiter remains, the eight recovered requests return 200, and observed failures/waits disappear.

For the report, record the end of the controlled lock as containment. A production responder would coordinate the transaction's end with its owner or justify a tightly scoped Chapter 020 action. This lab does not exercise an emergency signal.

State clearly: request recovery occurred without creating extended statistics. The continuing estimate error is a separate weakness, not proof that it caused this lock incident.

## 5. Test a durable statistics hypothesis

~~~bash
admin > "$evidence/statistics-maintenance.txt" 2>&1 <<'SQL'
CREATE STATISTICS c030_incident.request_ab_dependencies (dependencies)
ON a,b FROM c030_incident.requests;
ANALYZE c030_incident.requests;
SQL
app -qAt -f postgresql/scripts/030-project-plan.sql > "$evidence/after-plan.json" 2> "$evidence/after-plan.stderr"
python3 postgresql/scripts/027-plan-summary.py "$evidence/after-plan.json" > "$evidence/after-plan-summary.json"
python3 postgresql/scripts/030-request-probe.py after_stats > "$evidence/after-stats.jsonl"
admin -c "SELECT statistics_name,attnames,kinds,dependencies FROM pg_stats_ext WHERE schemaname='c030_incident' AND tablename='requests'" \
  > "$evidence/statistics-inventory.txt"
~~~

Compare scan estimated rows and actual rows using the same query, role, local settings and data. Independence suggests about two estimated rows against 200 actual; dependencies should improve the compatible equality estimate after ANALYZE. Exact estimates and timings remain observations.

Do not claim latency gains if the same sequential scan remains and measured durations differ only by noise. Include the incompatible-predicate limitation from Chapter 028 in the report. For production acceptance, define broader parameter coverage than this fixture.

## 6. Demonstrate rollback of the separate change

~~~bash
admin -c 'DROP STATISTICS c030_incident.request_ab_dependencies;' > "$evidence/statistics-rollback.txt"
app -qAt -f postgresql/scripts/030-project-plan.sql > "$evidence/rollback-plan.json" 2> "$evidence/rollback-plan.stderr"
python3 postgresql/scripts/030-request-probe.py after_rollback > "$evidence/after-rollback.jsonl"
~~~

Dropping the introduced object reverses its influence on subsequent planning. Individual-column statistics remain refreshed. This rollback does not recreate the lock incident; requests should still succeed. Record the estimate behavior and correct-result acceptance again.

## 7. Summarize evidence and complete the report

~~~bash
export PROJECT_EVIDENCE="$evidence"
python3 - <<'PY'
import json, os
from pathlib import Path
root=Path(os.environ['PROJECT_EVIDENCE'])
for name in ['baseline','incident','recovered','after-stats','after-rollback']:
    records=[json.loads(x) for x in (root/(name+'.jsonl')).read_text().splitlines()]
    if len(records)!=8 or [x['attempt'] for x in records]!=list(range(1,9)):
        raise SystemExit('Incomplete phase: '+name)
    good=sum(x['correct_result'] and x['outcome']=='success' for x in records)
    durations=[x['duration_ms'] for x in records]
    failures=[x.get('sqlstate') or x['outcome'] for x in records if not x['correct_result']]
    print(name,'correct=',good,'failed=',8-good,'duration_ms_range=',
          (min(durations),max(durations)),'failure_classes=',failures)
    if name!='incident' and good!=8:
        raise SystemExit('Acceptance failed: '+name)
PY
~~~

The summary deliberately reports counts and ranges, not unstable p95/p99 from eight attempts. Check timestamps and collection-status.txt for every collector window; apply Chapter 029 JSON/reset-boundary validation before any cumulative deltas. Missing or disabled metrics stay unknown.

Complete report.md with the timeline, impact, lock identities, hypothesis ranking, recovery-before-statistics evidence, before/after estimates, rollback, visibility gaps and production acceptance plan. Require at least one classified lock timeout and a live edge for the incident exercise to pass. If the host is too slow or sampling misses the edge, repeat the bounded phase with new evidence filenames after confirming the original holder exited; do not stretch the fault duration without reviewing its budget.

The exercise does not supply application pool/trace telemetry, stable tail latency, sustained production traffic or live provider metrics. Describe what those measurements must establish before accepting an actual production fix.

## 8. Cleanup and verify

Ensure every known background job completed and no c030_blocker/c030_probe remains. This removes only objects created by this guarded run.

~~~bash
[[ "$(admin -Atc "SELECT count(*) FROM pg_stat_activity WHERE datname='ops_lab' AND application_name IN ('c030_blocker','c030_probe')")" == 0 ]] || exit 2
admin > "$evidence/cleanup.txt" 2>&1 <<'SQL'
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='5s';
DROP TABLE c030_incident.requests;
DROP SCHEMA c030_incident;
COMMIT;
SQL
[[ "$(admin -Atc "SELECT to_regnamespace('c030_incident') IS NULL")" == t ]] || exit 2
admin -Atc "SELECT clock_timestamp(),to_regnamespace('c030_incident') IS NULL" \
  > "$evidence/cleanup-verification.txt"
printf 'Project evidence and report: %s\n' "$evidence"
~~~

If interrupted before the statistics rollback, first inspect and drop exactly c030_incident.request_ab_dependencies if this run created it. Do not use CASCADE or remove unrelated objects. Failed cleanup rolls back its transaction; inspect scoped conflicts before retrying.

**Completion:** baseline and recovered probes passed; classified lock impact plus identity edge observed; separate statistics experiment and rollback documented; no unsupported performance claims; report reviewed; fixture namespace absent.

[Return to chapter](../chapters/030-production-slowness-investigation-project.md)
