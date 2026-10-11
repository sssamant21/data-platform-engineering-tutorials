# Lab 010 — Configuration Drift and Baseline Acceptance

**Audience:** DBRE/SRE. **Environment:** guarded Chapter 004 PG18 Linux lab.
**Duration:** 90–120 minutes. **Execution evidence:** pending.

[Chapter](../chapters/010-configuration-drift-and-baseline-acceptance.md) · [Lab setup](004-reproducible-postgresql-operations-lab.md) · [Capture SQL](../scripts/010-capture-baseline.sql) · [Comparator](../scripts/010-compare-baseline.py) · [Diagnostic SQL](../scripts/010-drift-inspection.sql)

This exercise modifies the disposable primary's logging setting, proposes a memory change, and deliberately breaks one startup. Keep the two standbys running, never promote them, and run from the repository's postgresql directory as the Chapter 004 lab OS user.

## 1. Guard and prepare

Export the existing PG_LAB_ROOT from Chapter 004. Recreate that lab if its transient directory disappeared. Do not substitute a production directory.

~~~bash
: "${PG_LAB_ROOT:?Export the disposable Chapter 004 lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ -d "$PG_LAB_ROOT/primary" && ! -L "$PG_LAB_ROOT/primary" \
   && -O "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/primary/PG_VERSION")" == 18 ]] || exit 2
for cmd in pg_ctl psql; do
  [[ "$("$cmd" --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
done
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGAPPNAME=chapter010-lab
umask 077
EVIDENCE_010="$PG_LAB_ROOT/evidence-010"
[[ ! -e "$EVIDENCE_010" ]] || { echo 'Preserve previous evidence; choose a fresh lab for a rerun.'; exit 2; }
mkdir "$EVIDENCE_010"
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U lab_admin -d ops_lab "$@"
}
capture_010() {
  local role="$1" output="$2"
  psql -X -q -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U "$role" -d ops_lab -f scripts/010-capture-baseline.sql > "$output"
}
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
~~~

The helper targets PG18 only. All changes below use the lab_admin role; captures use fresh lab_observer or lab_app sessions.

## 2. Reconcile the baseline before approving it

This lab requires the original Chapter 004 settings and complete cleanup from Chapters 008–009. Check:

~~~bash
lab_sql <<'SQL'
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT name,setting,unit,source,sourcefile,pending_restart
FROM pg_settings
WHERE name IN ('shared_buffers','fsync','full_page_writes','work_mem',
               'log_min_duration_statement')
ORDER BY name;
SELECT sourcefile,name,setting,error FROM pg_file_settings
WHERE error IS NOT NULL
   OR (sourcefile LIKE '%/postgresql.auto.conf'
       AND name IN ('shared_buffers','log_min_duration_statement'));
SELECT d.datname,r.rolname,s.setconfig
FROM pg_db_role_setting s
LEFT JOIN pg_database d ON d.oid=s.setdatabase
LEFT JOIN pg_roles r ON r.oid=s.setrole;
SELECT name FROM pg_settings WHERE pending_restart;
COMMIT;
SQL
~~~

Required starting state: shared_buffers = 8192 with unit 8kB (64MB), fsync and full_page_writes on, work_mem = 4096 with unit kB (4MB), log_min_duration_statement = -1, no pending-restart settings, no file errors and no auto-conf entries for the two parameters that this lab will modify. No applicable role/database work_mem override may exist for lab_observer or lab_app.

If these checks fail, stop and reconcile the previous exercise. Do not erase unexplained overrides. These preconditions make the later RESET operations restore the original configuration rather than overwrite an earlier exception.

Capture build/version, role and topology in a private report. Capture both session profiles:

~~~bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$EVIDENCE_010/collection-time.txt"
lab_sql -c 'SELECT version(),pg_postmaster_start_time(),pg_is_in_recovery();' \
  > "$EVIDENCE_010/identity.txt"
capture_010 lab_observer "$EVIDENCE_010/candidate-observer.csv" || exit 2
capture_010 lab_app "$EVIDENCE_010/candidate-app.csv" || exit 2
~~~

Read each candidate and compare it with the Chapter 004 contract and current source files. Verify all 12 rows, source attribution and recovery role. Observer/app sourcefile visibility can differ; do not interchange their baselines. Record your review and approval in the report.

Only after that review, create the exercise's approved copies:

~~~bash
cp "$EVIDENCE_010/candidate-observer.csv" "$EVIDENCE_010/approved-observer.csv"
cp "$EVIDENCE_010/candidate-app.csv" "$EVIDENCE_010/approved-app.csv"
capture_010 lab_observer "$EVIDENCE_010/before.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-observer.csv" "$EVIDENCE_010/before.csv"
~~~

Expected exit 0. A self-comparison only verifies the file shape; your explicit contract review is what establishes approval.

## 3. Reloadable drift and provenance

Introduce a logging override:

~~~bash
lab_sql -c 'ALTER SYSTEM SET log_min_duration_statement = 1000;'
lab_sql -c 'SELECT pg_reload_conf();'
~~~

Observe in fresh sessions for up to ten attempts:

~~~bash
for attempt in {1..10}; do
  [[ "$(lab_sql -Atc 'SHOW log_min_duration_statement')" == 1s ]] && break
  sleep 1
done
lab_sql -c "SELECT name,setting,unit,source,sourcefile,pending_restart
FROM pg_settings WHERE name='log_min_duration_statement';"
capture_010 lab_observer "$EVIDENCE_010/logging-drift.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-observer.csv" "$EVIDENCE_010/logging-drift.csv"
~~~

SHOW rendering can vary; the decisive evidence is pg_settings showing setting 1000, unit ms, source configuration file and the auto-conf path. If the loop does not observe the value, inspect the displayed normalized value and logs; do not treat the loop's completion as proof.

Expected comparison exit 1 with the changed value and provenance. Record the difference. Restore the original owning layer:

~~~bash
lab_sql -c 'ALTER SYSTEM RESET log_min_duration_statement;'
lab_sql -c 'SELECT pg_reload_conf();'
~~~

Collect fresh snapshots until the original setting/source returns, within ten seconds. Then:

~~~bash
capture_010 lab_observer "$EVIDENCE_010/logging-restored.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-observer.csv" "$EVIDENCE_010/logging-restored.csv"
~~~

Expected exit 0. If it fails, inspect precedence before continuing.

## 4. Session drift despite an unchanged server file

Inject a client startup option only into one new application connection:

~~~bash
PGOPTIONS='-c work_mem=8MB' capture_010 lab_app "$EVIDENCE_010/session-drift.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-app.csv" "$EVIDENCE_010/session-drift.csv"
capture_010 lab_observer "$EVIDENCE_010/observer-unchanged.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-observer.csv" "$EVIDENCE_010/observer-unchanged.csv"
~~~

Expected: application comparison exit 1, work_mem 8192 kB with client provenance; observer comparison exit 0. No server file or role catalog was changed.

The temporary variable assignment applies only to that function invocation. Confirm the normal application profile in a new session:

~~~bash
capture_010 lab_app "$EVIDENCE_010/session-restored.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-app.csv" "$EVIDENCE_010/session-restored.csv"
~~~

Expected exit 0. This illustrates why an observer connection cannot certify every workload session.

## 5. Pending restart without active-value drift

~~~bash
lab_sql -c "ALTER SYSTEM SET shared_buffers = '96MB';"
lab_sql -c 'SELECT pg_reload_conf();'
~~~

Inspect fresh sessions until pending_restart becomes true, within ten seconds:

~~~bash
lab_sql -c "SELECT name,setting,unit,pending_restart
FROM pg_settings WHERE name='shared_buffers';"
lab_sql -c "SELECT sourcefile,name,setting,applied,error
FROM pg_file_settings WHERE name='shared_buffers' ORDER BY seqno;"
capture_010 lab_observer "$EVIDENCE_010/pending-restart.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-observer.csv" "$EVIDENCE_010/pending-restart.csv"
~~~

Expected: active shared_buffers still 8192 8kB; pending_restart true; persisted proposal 96MB; comparison exit 1. Do not activate the proposal.

Restore it:

~~~bash
lab_sql -c 'ALTER SYSTEM RESET shared_buffers;'
lab_sql -c 'SELECT pg_reload_conf();'
~~~

Wait for fresh-session evidence that pending_restart is false, then capture and compare again. Expected exit 0 without a restart. If the flag persists, inspect file entries and logs rather than assuming RESET completed acceptance.

## 6. Module acceptance: failed start and safe restoration

Before this step, all drift comparisons must match. No other operator or configuration writer may modify the lab. Verify the configuration file is the guarded primary's regular, owned file:

~~~bash
CONF_010="$PG_LAB_ROOT/primary/postgresql.conf"
[[ -f "$CONF_010" && ! -L "$CONF_010" && -O "$CONF_010" ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW config_file')" == "$CONF_010" ]] || exit 2
cp "$CONF_010" "$EVIDENCE_010/pre-failed-start.conf"
pg_ctl -D "$PG_LAB_ROOT/primary" -m fast -w -t 30 stop
~~~

Confirm status reports no server running. If shutdown timed out, follow Chapter 009; do not proceed. Append one intentionally invalid value only while the primary is stopped:

~~~bash
printf "\n# Chapter 010 disposable failed-start trigger\nshared_buffers = 'not-memory'\n" >> "$CONF_010"
if pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 start; then
  echo 'Unexpected startup success: stop the experiment and inspect the instance.'
else
  echo 'Start returned nonzero; verify the log shows the intended invalid-value failure.'
fi
pg_ctl -D "$PG_LAB_ROOT/primary" status
tail -n 60 "$PG_LAB_ROOT/logs/primary.log"
~~~

Expected: start failure, no running primary and a log error identifying the invalid shared_buffers value. If a process is running or the failure has another cause, stop and investigate. Preserve the failure log; never delete a PID file to bypass the check.

With the primary confirmed stopped, restore the saved exact file and start through its existing owner:

~~~bash
cp "$EVIDENCE_010/pre-failed-start.conf" "$CONF_010"
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 start
bash scripts/004-operations-lab.sh verify
~~~

If startup wait expires, inspect recovery and process state before taking another action. Expected: normal primary readiness and both standbys streaming. No durability setting was disabled, and no standby was promoted.

## 7. Final acceptance and cleanup

~~~bash
capture_010 lab_observer "$EVIDENCE_010/final-observer.csv" || exit 2
capture_010 lab_app "$EVIDENCE_010/final-app.csv" || exit 2
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-observer.csv" "$EVIDENCE_010/final-observer.csv"
python3 scripts/010-compare-baseline.py \
  "$EVIDENCE_010/approved-app.csv" "$EVIDENCE_010/final-app.csv"
lab_sql -f scripts/010-drift-inspection.sql > "$EVIDENCE_010/final-diagnostics.txt"
bash scripts/004-operations-lab.sh verify
~~~

Pass requires both comparisons exit 0, no pending restart anywhere, no configuration/HBA parse errors, no test auto-conf entries, the original configuration file restored, correct primary/standby roles and the replication probe visible on both standbys.

Retain observed outputs and times for each injected failure and restoration. Complete the chapter's Module 02 acceptance table using actual evidence from Chapters 006–010; mark unexecuted gates pending. A manual-lab pass does not certify systemd behavior on a production host.

Evidence files may contain private paths and configuration. Keep them protected and sanitize copies before publication. Keep the lab for Chapter 011 or stop/destroy it through Chapter 004. If interrupted mid-exercise, restore only the two overrides introduced here after checking their current ownership, and restore the saved configuration if the failed-start trigger remains. Do not use RESET ALL or overwrite another operator's change.
