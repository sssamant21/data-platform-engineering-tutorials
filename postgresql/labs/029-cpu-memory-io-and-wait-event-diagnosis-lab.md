# Chapter 029 Lab — CPU, Memory, I/O and Wait Event Diagnosis

**Target:** Chapter 004 disposable PostgreSQL 18 primary, port 55432, ops_lab. Run from the repository root as its non-root OS owner. Prerequisites: psql 18, Python 3 and the earlier operations lab.

**Limits:** one synthetic workload at a time, one observer, bounded query time, local parallelism disabled, at most 32MB temporary files per workload backend. This exercise does not generate an OOM, exhaust storage, clear caches, reset statistics, restart the server or alter cluster settings. Actual PostgreSQL execution remains pending in the authoring environment.

## 1. Guard the target and reserve the fixture

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
  PGAPPNAME=c029_control PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc "SELECT to_regnamespace('c029_resources') IS NULL")" == t ]] || {
  echo 'Existing namespace: investigate previous run; do not overwrite'; exit 2;
}
umask 077
evidence="$(mktemp -d "$PG_LAB_ROOT/c029-results.XXXXXXXX")"
admin > "$evidence/setup.txt" 2>&1 <<'SQL'
BEGIN;
CREATE SCHEMA c029_resources AUTHORIZATION lab_admin;
CREATE TABLE c029_resources.lock_probe(id integer PRIMARY KEY);
INSERT INTO c029_resources.lock_probe VALUES (1);
COMMIT;
SQL
~~~

The namespace reserves the fixture for this run. A pre-existing namespace is a stop condition. The synthetic plan workload uses generate_series rather than a large stored relation. lab_admin runs fixed workloads because setting the local temp_file_limit requires suitable privilege; lab_observer collects statistics through pg_monitor.

## 2. Start the baseline window

~~~bash
bash postgresql/scripts/029-resource-window.sh baseline | tee "$evidence/baseline-collector.txt"
~~~

The collector prints a new private evidence path immediately. It collects ten fresh-session JSON snapshots approximately one second apart, optional vmstat/iostat output, memory information and available host PSI. It checks the lab marker, ownership, credential-file mode, PostgreSQL version and exact primary directory.

Each JSON is produced by [the read-only snapshot SQL](../scripts/029-resource-snapshot.sql). Its activity scope is ops_lab; I/O/checkpointer/WAL scope is the entire cluster. Background traffic, including the Chapter 004 standbys, can contribute. No statement text is included.

Copy each printed window path into your acceptance report. If a collector fails, preserve the partial directory and label that window incomplete. collection-status.txt appears only at successful completion. Host *.failed markers mean those command outputs are not reliable. Optional metrics marked unavailable remain unknown.

## 3. Intentional sleep: a wait is not CPU demand

~~~bash
bash postgresql/scripts/029-resource-window.sh sleep > "$evidence/sleep-collector.txt" 2>&1 &
collector_job=$!
PGAPPNAME=c029_sleep PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -qAt -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -v mode=sleep -f postgresql/scripts/029-resource-workload.sql > "$evidence/sleep.txt" 2>&1
wait "$collector_job"
~~~

Find c029_sleep in repeated activity samples. Expect active with Timeout/PgSleep during its four-second delay. Compare with low backend CPU if you can sample the actual server PID. Do not classify it as an expensive compute query from elapsed duration alone.

## 4. CPU work and the sampling boundary

~~~bash
bash postgresql/scripts/029-resource-window.sh cpu > "$evidence/cpu-collector.txt" 2>&1 &
collector_job=$!
if PGAPPNAME=c029_cpu PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -qAt -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -v mode=cpu -f postgresql/scripts/029-resource-workload.sql > "$evidence/cpu.txt" 2>&1; then
  echo completed > "$evidence/cpu-status.txt"
else
  echo 'Failed or timed out: inspect cpu.txt; do not assume completion' > "$evidence/cpu-status.txt"
fi
wait "$collector_job"
~~~

The fixed query calculates MD5 lengths for two million integers, with one backend and an eight-second statement limit. Successful output should be 64000000. A timeout on a slower host is a bounded failure; other errors need diagnosis.

An observed active backend with NULL wait is only a CPU hypothesis. Confirm with pidstat for that current server PID while a new controlled run executes, if needed. This collector does not collect per-PID CPU. Host vmstat can dilute one busy core across many CPUs. A query finishing between samples may be absent; report that observation gap rather than inventing occupancy or scaling the workload without a budget.

## 5. Controlled heavyweight lock wait

First start the blocker, then prove its identity and state before starting a waiter. The fixture lock is held for six seconds and released by COMMIT. All backends have time budgets.

~~~bash
PGAPPNAME=c029_blocker PGOPTIONS='-c statement_timeout=8s -c lock_timeout=1s -c transaction_timeout=10s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  > "$evidence/blocker.txt" 2>&1 <<'SQL' &
BEGIN;
LOCK TABLE c029_resources.lock_probe IN ACCESS EXCLUSIVE MODE;
SELECT pg_sleep(6);
COMMIT;
SQL
blocker_job=$!
ready=f
for attempt in $(seq 1 20); do
  ready="$(admin -Atc "SELECT EXISTS (
    SELECT 1 FROM pg_stat_activity
    WHERE datname='ops_lab' AND application_name='c029_blocker'
      AND state='active' AND wait_event='PgSleep'
      AND backend_start > clock_timestamp()-interval '30 seconds')")"
  [[ "$ready" == t ]] && break
  sleep 0.1
done
[[ "$ready" == t ]] || { wait "$blocker_job"; echo 'Blocker not observed: stop phase'; exit 2; }

bash postgresql/scripts/029-resource-window.sh lock > "$evidence/lock-collector.txt" 2>&1 &
collector_job=$!
PGAPPNAME=c029_waiter PGOPTIONS='-c statement_timeout=8s -c lock_timeout=7s -c transaction_timeout=10s' \
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  > "$evidence/waiter.txt" 2>&1 <<'SQL' &
BEGIN READ ONLY;
SELECT id FROM c029_resources.lock_probe;
COMMIT;
SQL
waiter_job=$!
admin -Atc "SELECT clock_timestamp(),pid,backend_start,wait_event_type,wait_event,pg_blocking_pids(pid)
FROM pg_stat_activity WHERE datname='ops_lab' AND application_name='c029_waiter'" \
  > "$evidence/blocking-edge.txt"
wait "$blocker_job"
wait "$waiter_job"
wait "$collector_job"
~~~

Expect repeated Lock/relation observations for c029_waiter with little CPU demand. The one-shot blocking-edge sample can race the waiter; an empty file does not prove there was no blocker. If needed, collect that same bounded metadata query again during a fresh run and retain its timestamp. Use Chapter 018 identity safeguards before acting on any production blocker.

No cancellation or termination is needed: these sessions complete normally or hit their own time limits. On failure, wait for the known background jobs to finish before cleanup; do not signal unrelated sessions.

## 6. Operation memory and executor temporary files

~~~bash
bash postgresql/scripts/029-resource-window.sh spill-low > "$evidence/spill-low-collector.txt" 2>&1 &
collector_job=$!
PGAPPNAME=c029_spill_low PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -qAt -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -v mode=spill_low -f postgresql/scripts/029-resource-workload.sql \
  > "$evidence/spill-low.json" 2> "$evidence/spill-low.stderr"
wait "$collector_job"

bash postgresql/scripts/029-resource-window.sh spill-high > "$evidence/spill-high-collector.txt" 2>&1 &
collector_job=$!
PGAPPNAME=c029_spill_high PGOPTIONS='-c statement_timeout=10s -c lock_timeout=1s' \
  psql -X -w -qAt -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -v mode=spill_high -f postgresql/scripts/029-resource-workload.sql \
  > "$evidence/spill-high.json" 2> "$evidence/spill-high.stderr"
wait "$collector_job"

python3 postgresql/scripts/027-plan-summary.py "$evidence/spill-low.json" > "$evidence/spill-low-summary.json"
python3 postgresql/scripts/027-plan-summary.py "$evidence/spill-high.json" > "$evidence/spill-high-summary.json"
~~~

Both cases sort the same 30,000 synthetic rows with roughly 256-byte payloads. The script uses READ ONLY, disabled parallel workers, temp_file_limit=32MB and local work_mem of 64kB versus 32MB. All local settings disappear at transaction end.

Inspect the restricted raw JSON for Sort Method, Sort Space Type/Used, actual rows and temporary blocks; Chapter 027's summary intentionally does not expose every plan field. Expect the low budget to spill and the higher budget to reduce/eliminate spilling, but record actual behavior. FunctionScan/materialization can also contribute temporary work; attribute evidence to the actual nodes.

Compare database temp_bytes/temp_files deltas from matching reset epochs and stable database identity after each workload finishes and its backend exits. Do not attribute cluster-wide pg_stat_io deltas entirely to this query. Sort/hash work files are not fully described by temp relation counters. Fast cached writes/reads can produce a spill with no sampled IO wait.

If temporary-file or statement limits stop execution, mark that phase failed; retain errors and plan no production change from partial evidence. Never drop caches or fill the disk to make an IO wait visible.

## 7. Validate retained JSON and build a diagnosis report

Set WINDOW_DIR to one printed collector evidence path; repeat for every window.

~~~bash
export WINDOW_DIR=/tmp/postgresql-dbre-lab.REPLACE/c029-baseline.REPLACE
python3 - <<'PY'
import json, os
from pathlib import Path
p=Path(os.environ['WINDOW_DIR'])
files=sorted(p.glob('sample-*.json'))
if len(files)!=10 or not (p/'collection-status.txt').exists():
    raise SystemExit('Incomplete window')
for f in files:
    item=json.loads(f.read_text())
    if item.get('schema_version')!=1 or not 180000<=item['server_version_num']<190000:
        raise SystemExit(f'Unexpected version: {f.name}')
    print(f.name,item['captured_at'],len(item['activity']),len(item['io']))
PY
~~~

Parsing validates evidence format, not PostgreSQL behavior. Compare actual timestamps, postmaster_start, database_oid and stats_reset before deltas. Use fresh rows keyed by backend_type/object/context for I/O. Record which timing flags are enabled and whether workload-side timing policy is known. If timings are disabled, analyze operation/byte counts and host latency without claiming an instrumented average.

| Phase | Observed activity/wait | Host or PID evidence | Counter/plan evidence | Diagnosis and limitation |
|---|---|---|---|---|
| Baseline | Pending | Pending | Pending | Normal reference window |
| Sleep | Pending | Pending | Pending | Timed wait, not compute |
| CPU | Pending | Pending | Pending | Compute hypothesis needs PID CPU confirmation |
| Lock | Pending | Pending | Pending | Relation lock and scoped blocker |
| Low-memory sort | Pending | Pending | Pending | Operation spill versus host pressure |
| Higher-memory sort | Pending | Pending | Pending | Same workload, local budget comparison |

Add one production response and rollback for each observed bottleneck. Explain why a NULL wait, a zero timing value, a high cache-hit ratio or a low host CPU average alone cannot settle the diagnosis.

## 8. Cleanup and acceptance

Ensure all known workload/collector jobs have completed before cleanup. In an interrupted shell, verify the c029 application names and backend_start values read-only and let bounded sessions finish; do not terminate broad matches.

~~~bash
admin > "$evidence/cleanup.txt" 2>&1 <<'SQL'
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='5s';
DROP TABLE c029_resources.lock_probe;
DROP SCHEMA c029_resources;
COMMIT;
SQL
[[ "$(admin -Atc "SELECT to_regnamespace('c029_resources') IS NULL")" == t ]] || exit 2
admin -Atc "SELECT clock_timestamp(),to_regnamespace('c029_resources') IS NULL" \
  > "$evidence/cleanup-verification.txt"
printf 'Results: %s\n' "$evidence"
~~~

Cleanup uses no CASCADE; if it fails, investigate the scoped fixture and retry after conflicting sessions finish. Keep evidence private under the team retention policy.

**Acceptance:** complete parsed windows; sleep/lock correctly distinguished; CPU hypothesis corroborated or explicitly unconfirmed; low/high sort plans compared; valid counter boundaries; host visibility gaps recorded; no global setting changes; namespace absent after cleanup.

[Return to chapter](../chapters/029-cpu-memory-io-and-wait-event-diagnosis.md)
