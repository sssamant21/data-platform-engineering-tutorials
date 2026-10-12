# Lab 024 — Slow Logs and Client Trace Correlation

Audience: DBRE/SRE. PostgreSQL 18. Runtime verification pending.
[Chapter](../chapters/024-logs-slow-statements-and-correlation-with-application-traces.md) · [Client workload](../scripts/024-lab-trace-workload.py) · [Correlation helper](../scripts/024-correlate-json-logs.py)

## Scope and measurement limits

Use the Chapter 004 disposable cluster. Close prior actors. This lab temporarily stops all three nodes, starts only the primary with JSON logging, creates c024_logs, then restores normal startup. No configuration file is edited.

Three dedicated psql sessions generate synthetic client records. Each has a unique c024_ application tag tied to a trace-shaped identifier. This is an educational join, not an OpenTelemetry SDK export or a production pooled-connection design. Client duration includes process launch, connection setup, a metadata query and the operation.

Raw logs can contain SQL and diagnostics. Keep them private, even though these operations are synthetic. Parameter-value suppression does not sanitize literals or messages.

## 1. Guard and capture the baseline

In repository root, use the non-root Chapter 004 owner and exported PG_LAB_ROOT:

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
  PGAPPNAME=c024_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc 'SHOW logging_collector')" == off ]] || exit 2
[[ "$(admin -Atc 'SHOW log_destination')" == stderr ]] || exit 2
[[ "$(admin -Atc 'SHOW compute_query_id')" == auto ]] || exit 2
umask 077
evidence="$PG_LAB_ROOT/c024-evidence"
[[ ! -L "$evidence" ]] || exit 2
mkdir -p -m 700 "$evidence"
[[ -d "$evidence" && -O "$evidence" ]] || exit 2
settings_sql="SELECT name,setting FROM pg_settings WHERE name IN ('logging_collector','log_destination','log_directory','log_filename','log_rotation_age','log_rotation_size','log_file_mode','log_min_duration_statement','log_min_duration_sample','log_transaction_sample_rate','log_statement','log_duration','log_parameter_max_length','log_parameter_max_length_on_error','log_min_error_statement','compute_query_id','log_timezone') ORDER BY name;"
(
  set -o noclobber
  admin -qAt -c "$settings_sql" > "$evidence/baseline-settings.txt"
)
~~~

Existing evidence filenames are refused. If the baseline preconditions fail, investigate; do not overwrite an existing logging arrangement. Do not print the passfile.

## 2. Start a temporary JSON destination

Close every interactive client before stopping the lab. Then:

~~~bash
bash postgresql/scripts/004-operations-lab.sh stop
pg_ctl -D "$PG_LAB_ROOT/primary" -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 \
  -o "-c logging_collector=on -c log_destination=jsonlog -c log_directory=c024-logs -c log_filename=c024-%Y%m%d-%H%M%S.log -c log_rotation_age=0 -c log_rotation_size=0 -c log_file_mode=0600 -c log_min_duration_statement=100ms -c log_min_duration_sample=-1 -c log_transaction_sample_rate=0 -c log_statement=none -c log_duration=off -c log_parameter_max_length=0 -c log_parameter_max_length_on_error=0 -c log_min_error_statement=error -c compute_query_id=on -c log_timezone=UTC" start
admin -c "$settings_sql"
admin -c "SELECT pg_current_logfile('jsonlog');"
admin -c 'CREATE DATABASE c024_logs OWNER lab_admin;'
~~~

These are temporary lab settings. Rotation is disabled only for this short bounded run; do not copy that choice into a production logging policy. Standbys remain stopped until cleanup.

If startup fails or times out, inspect pg_ctl status and the primary log. A timeout can leave startup continuing. Stop a running primary cleanly and restore normal Chapter 004 start without these options before troubleshooting further. Preserve baseline evidence.

## 3. Generate fast, slow and timeout records

In the guarded shell:

~~~bash
python3 postgresql/scripts/024-lab-trace-workload.py --output traces.jsonl
python3 -m json.tool --json-lines "$evidence/traces.jsonl"
~~~

Use a Python version that supports json.tool --json-lines, or inspect each JSON object with the standard json module.

Expected records:

| Operation | Client observation | Expected server evidence |
|---|---|---|
| fast | Successful SELECT 1 | Usually no duration record at 100 ms threshold |
| slow | Successful 250 ms sleep | Completed duration at/above threshold |
| timeout | Error, typically 57014 | Server error/cancellation record |

The runner independently checks the disposable marker, private passfile, server identity and JSON settings. It creates exclusive evidence files and performs only three operations. Its psql process deadline and server transaction/statement budgets are bounded.

Each session records the PID and session ID from the very connection running the operation. Unique application tags fit PostgreSQL's normal identifier length. Raw SQL and client error text are not exported into the trace file.

A fast operation can exceed the threshold under load; accept the observed evidence rather than forcing an expected absence. A connection/setup failure can leave no backend identity and no matched server event.

## 4. Freeze the raw log after clean shutdown

After the runner exits, record the current destination while the server is still running:

~~~bash
log_relative="$(admin -Atc "SELECT pg_current_logfile('jsonlog')")"
[[ "$log_relative" =~ ^c024-logs/c024-[0-9]{8}-[0-9]{6}\.json$ ]] || exit 2
raw_log="$PG_LAB_ROOT/primary/$log_relative"
[[ -f "$raw_log" && ! -L "$raw_log" && -O "$raw_log" ]] || exit 2
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='c024_logs';"
admin -c 'DROP DATABASE c024_logs;'
pg_ctl -D "$PG_LAB_ROOT/primary" -m fast -w -t 30 stop
~~~

Require zero c024_logs clients before DROP. Resolve remaining owners through their clients, not a broad termination command. DROP runs from ops_lab without FORCE. Clean shutdown flushes/closes collector output, avoiding a partially written final record during analysis.

Copy one stable raw file into restricted evidence and immediately restore availability:

~~~bash
if ! python3 - "$raw_log" "$evidence/raw.jsonl" <<'PY'
from pathlib import Path
import sys
with Path(sys.argv[2]).open("xb") as output:
    output.write(Path(sys.argv[1]).read_bytes())
PY
then
  bash postgresql/scripts/004-operations-lab.sh start
  echo "Log copy failed; normal lab startup restored; preserve the source file" >&2
  exit 2
fi
bash postgresql/scripts/004-operations-lab.sh start
admin -qAt -c "$settings_sql" > "$evidence/restored-settings.txt"
cmp "$evidence/baseline-settings.txt" "$evidence/restored-settings.txt"
admin -c "SELECT NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='c024_logs') AS fixture_database_removed;"
~~~

The copied file can include startup/control/shutdown messages in addition to the three test sessions. Its directory is private. Do not ship it to an unrestricted ticket or repository.

Chapter 004 start verifies primary/two-standby topology. Stop followed by normal start discards temporary command-line settings; an unqualified pg_ctl restart can reuse them. No internal log files or configuration files need manual deletion.

If log copy fails, restore normal startup first and preserve the source for later review. If cmp fails, inspect settings and source precedence; do not declare cleanup complete.

## 5. Correlate and inspect the summary

~~~bash
python3 postgresql/scripts/024-correlate-json-logs.py \
  "$evidence/raw.jsonl" "$evidence/traces.jsonl" \
  --source-id chapter004-primary-55432 --skew-ms 500 > "$evidence/summary.json"
python3 -m json.tool "$evidence/summary.json"
~~~

The helper joins the declared physical source, database, exact application tag, PID, session ID and a bounded time interval. A source label is a verified inventory assertion, not authenticated evidence by itself.

Expected: slow has a completed_duration event; timeout has a server_error with 57014; fast may be unmatched. A missing match is explicitly not proof of health. Server events are associated with a session interval, not asserted to be one-to-one database spans. The metadata query can generate another event if it becomes slow.

The helper ignores unknown JSON fields and exports only allowlisted metadata, extracted duration and SQLSTATE. It does not emit message, statement, detail, context, remote address or user data. Python preserves bigint query IDs and exports them as strings. A zero/missing query ID is not a failed correlation when the session match is valid.

Compare client and server duration boundaries. Explain why their difference cannot be labeled pure network latency. The client record includes more than just the timed SELECT; it does not represent pool checkout or a real application retry chain.

## 6. Exercise parser and correlation limits offline

Create labeled synthetic copies outside live evidence. Keep raw originals unchanged.

- Change PID or session ID: no match should be manufactured from application_name alone.
- Move an event outside the tolerance window: it must not match.
- Use another source label or invalid trace identity: refuse the contract.
- Repeat an identical session/line record: deduplicate and report the skip.
- Use the same session/line with conflicting contents: fail rather than choose silently.
- Add unknown fields and escaped newlines in SQL/message text: parsing should remain structured and output should omit that text.
- Supply malformed/partial JSON, a naive timestamp or an invalid line/query identifier: report failure.
- Omit all eligible server records: retain explicit unmatched traces.

Put a distinctive synthetic marker in statement/detail/context and verify it never appears in summary output. This tests output selection; it does not remove that marker from the raw file.

The lab uses simple protocol. Test production drivers' Parse/Bind/Execute evidence and prepared-statement behavior separately. Pool tagging/reset and transaction-pool backend mapping also require real integration tests.

## 7. Record acceptance and operational follow-up

Retain server version, baseline/restored settings, trace records, restricted raw logs, summary and cleanup evidence. Write one incident narrative linking slow success and timeout to their server session records. Distinguish observed correlation from inferred cause.

Propose a production collection policy with thresholds, sampling, retention, access, clock/ingestion health, source identity, parameter/text controls and an expiry for temporary changes. Describe how actual application traces will carry context and avoid leaking tags across pool requests.

Acceptance requires matched slow/error evidence, explicit unmatched interpretation, no SQL/diagnostic text in the summary, preserved raw evidence boundaries, fixture removal and restored settings/replication topology. Offline tests do not verify PostgreSQL log delivery or production OpenTelemetry/pool behavior.
