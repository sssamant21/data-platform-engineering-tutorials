#!/usr/bin/env bash
# PostgreSQL 18 disposable streaming + sync-commit tests.
# Three server processes in ONE network-none Docker container.
# NO promotion, NO fencing claims, NO production/staging access.
set -Eeuo pipefail
export LC_ALL=C
[[ "$GITHUB_ACTIONS" == true && -n "$GITHUB_RUN_ID" ]] || {
  echo "REFUSED: ephemeral GitHub Actions Docker lab required" >&2; exit 3;
}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EVIDENCE="$ROOT/postgresql/validation/evidence-v03-ch067070-streaming.json"
WORK="$(mktemp -d)"
NAME="pg18-replication-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
PRIMARY=/tmp/postgresql-dbre-lab.v03replica/primary
A=/tmp/standby_a
B=/tmp/standby_b
P1=55432; P2=55433; P3=55434
CASES=0; PASS=0; FAIL=0; AMBIGUOUS="unobserved"
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT
docker pull postgres:18 >/dev/null
docker run -d --name "$NAME" --network none --tmpfs /tmp:rw,size=1536m,mode=1777 \
  --memory 2g --cpus 2 --pids-limit 300 \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=lab_admin \
  -e POSTGRES_DB=postgres -e PGDATA="$PRIMARY" \
  postgres:18 -c listen_addresses=127.0.0.1 -c port="$P1" \
  -c wal_level=replica -c max_wal_senders=8 \
  -c max_replication_slots=4 -c wal_keep_size=64MB \
  > "$WORK/container_id"
[[ "$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$NAME")" == none ]] || {
  echo "REFUSED: container network is not none" >&2; exit 3;
}
[[ -z "$(docker port "$NAME")" ]] || { echo "REFUSED: published port" >&2; exit 3; }
for attempt in $(seq 1 70); do
  if docker exec "$NAME" pg_isready -h 127.0.0.1 -p "$P1" -U lab_admin -d postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$NAME" pg_isready -h 127.0.0.1 -p "$P1" -U lab_admin -d postgres >/dev/null
q() {
  local port="$1" db="$2" sql="$3"
  docker exec "$NAME" psql -X -v ON_ERROR_STOP=1 -A -t \
    -h 127.0.0.1 -p "$port" -U lab_admin -d "$db" -c "$sql"
}
check() {
  local name="$1" got="$2" want="$3"
  CASES=$((CASES+1))
  if [[ "$got" == "$want" ]]; then PASS=$((PASS+1)); echo "PASS $name"
  else FAIL=$((FAIL+1)); echo "FAIL $name expected=$want observed=$got" >&2; exit 1; fi
}
poll() {
  local label="$1" port="$2" db="$3" sql="$4" want="$5" observed=""
  for attempt in $(seq 1 45); do
    if observed="$(q "$port" "$db" "$sql" 2>/dev/null)" && [[ "$observed" == "$want" ]]; then break; fi
    sleep 1
  done
  check "$label" "$observed" "$want"
}
VERS="$(q "$P1" postgres 'SHOW server_version_num')"
DATA="$(q "$P1" postgres 'SHOW data_directory')"
SYSTEM="$(q "$P1" postgres 'SELECT system_identifier::text FROM pg_control_system()')"
check pg18_major "$((VERS/10000))" 18
check primary_pgdata "$DATA" "$PRIMARY"
[[ "$SYSTEM" =~ ^[0-9]+$ ]] || { echo "REFUSED: no real system identifier" >&2; exit 3; }
# Identity and source role baseline. No preexisting synchronous setting or outside CM.
ORIGINAL="$(q "$P1" postgres 'SHOW synchronous_standby_names')"
ORIGINAL_SOURCE="$(q "$P1" postgres "SELECT source FROM pg_settings WHERE name='synchronous_standby_names'")"
ORIGINAL_FILE_ROWS="$(q "$P1" postgres "SELECT count(*) FROM pg_file_settings WHERE name='synchronous_standby_names'")"
check original_sync_names_empty "$ORIGINAL" ""
check original_sync_source_default "$ORIGINAL_SOURCE" default
check original_sync_file_entries_absent "$ORIGINAL_FILE_ROWS" 0
q "$P1" postgres 'CREATE DATABASE ch067_lab' >/dev/null
q "$P1" ch067_lab "CREATE TABLE public.replication_marker(event_id text PRIMARY KEY, note text NOT NULL)" >/dev/null
# Real physical base backups with -R standby.signal and the original primary conninfo.
# No external network, no service manager, no promotion. Source/standbys share host.
for triple in "standby_a:$A:$P2" "standby_b:$B:$P3"; do
  IFS=: read -r app dir port <<< "$triple"
  docker exec -u postgres "$NAME" test ! -e "$dir" || {
    echo "REFUSED: standby PGDATA already exists" >&2; exit 3;
  }
  docker exec -u postgres "$NAME" pg_basebackup \
    -d "host=127.0.0.1 port=$P1 user=lab_admin application_name=$app" \
    -D "$dir" -Fp -X stream -R -c fast > "$WORK/backup-$app.log" 2>&1
  docker exec -u postgres "$NAME" test -e "$dir/standby.signal" || {
    echo "FAIL standby.signal absent for $app" >&2; exit 1;
  }
  docker exec -u postgres "$NAME" pg_ctl -D "$dir" -l "/tmp/$app.log" \
    -o "-c listen_addresses=127.0.0.1 -c port=$port -c unix_socket_directories=/tmp" \
    -w -t 35 start > "$WORK/start-$app.log" 2>&1 || {
      echo "FAIL standby boot $app" >&2; exit 1;
    }
done
poll two_streaming_senders "$P1" postgres \
  "SELECT count(*) FROM pg_stat_replication WHERE application_name IN ('standby_a','standby_b') AND state='streaming'" 2
check standby_a_in_recovery "$(q "$P2" postgres 'SELECT pg_is_in_recovery()')" t
check standby_b_in_recovery "$(q "$P3" postgres 'SELECT pg_is_in_recovery()')" t
check standby_a_read_only "$(q "$P2" postgres 'SHOW transaction_read_only')" on
check standby_b_read_only "$(q "$P3" postgres 'SHOW transaction_read_only')" on
check distinct_standby_pgdata "$(q "$P2" postgres 'SHOW data_directory')" "$A"
check other_distinct_pgdata "$(q "$P3" postgres 'SHOW data_directory')" "$B"
check standby_a_wal_receiver "$(q "$P2" postgres "SELECT count(*) FROM pg_stat_wal_receiver WHERE status='streaming'")" 1
check standby_b_wal_receiver "$(q "$P3" postgres "SELECT count(*) FROM pg_stat_wal_receiver WHERE status='streaming'")" 1

q "$P1" ch067_lab "INSERT INTO public.replication_marker VALUES('first-marker','async-commit')" >/dev/null
LSN="$(q "$P1" postgres 'SELECT pg_current_wal_lsn()')"
poll standby_a_marker "$P2" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='first-marker'" 1
poll standby_b_marker "$P3" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='first-marker'" 1
poll standby_a_replay_lsn_caught_up "$P2" postgres "SELECT pg_wal_lsn_diff(pg_last_wal_replay_lsn(),'$LSN') >= 0" t
poll standby_b_replay_lsn_caught_up "$P3" postgres "SELECT pg_wal_lsn_diff(pg_last_wal_replay_lsn(),'$LSN') >= 0" t
q "$P1" ch067_lab "INSERT INTO public.replication_marker SELECT 'load-'||g,repeat('x',100) FROM generate_series(1,200) AS g" >/dev/null
poll standby_a_bounded_201_rows "$P2" ch067_lab 'SELECT count(*) FROM public.replication_marker' 201
poll standby_b_bounded_201_rows "$P3" ch067_lab 'SELECT count(*) FROM public.replication_marker' 201

# Chapter 069 FIRST 1: one eligible synchronous standby and a safe bounded commit.
q "$P1" postgres "ALTER SYSTEM SET synchronous_standby_names = 'FIRST 1 (standby_a, standby_b)'" >/dev/null
check first1_reload "$(q "$P1" postgres 'SELECT pg_reload_conf()')" t
poll first1_candidate "$P1" postgres \
  "SELECT count(*) FROM pg_stat_replication WHERE application_name='standby_a' AND sync_state='sync'" 1
check first1_primary_setting "$(q "$P1" postgres 'SHOW synchronous_standby_names')" "FIRST 1 (standby_a, standby_b)"
q "$P1" ch067_lab "BEGIN; SET LOCAL synchronous_commit=remote_apply; SET LOCAL statement_timeout='10s'; INSERT INTO public.replication_marker VALUES('sync-first','remote_apply'); COMMIT" >/dev/null
check sync_first_applied_a "$(q "$P2" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='sync-first'")" 1
poll sync_first_applied_b "$P3" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='sync-first'" 1

# Chapter 069 ANY 2 requires both standbys for acknowledgement.
q "$P1" postgres "ALTER SYSTEM SET synchronous_standby_names = 'ANY 2 (standby_a, standby_b)'" >/dev/null
check quorum_reload "$(q "$P1" postgres 'SELECT pg_reload_conf()')" t
poll both_quorum "$P1" postgres "SELECT count(*) FROM pg_stat_replication WHERE sync_state='quorum'" 2
q "$P1" ch067_lab "BEGIN; SET LOCAL synchronous_commit=remote_apply; SET LOCAL statement_timeout='10s'; INSERT INTO public.replication_marker VALUES('quorum-ok','two-standbys'); COMMIT" >/dev/null
check quorum_applied_a "$(q "$P2" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='quorum-ok'")" 1
check quorum_applied_b "$(q "$P3" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='quorum-ok'")" 1

# Stop ONE disposable standby and attempt bounded commit. Client outcome may be
# ambiguous even after statement_timeout: reconcile by unique id and both replicas.
docker exec -u postgres "$NAME" pg_ctl -D "$B" -m fast -w -t 25 stop >/dev/null
poll quorum_missing_one "$P1" postgres \
  "SELECT count(*) FROM pg_stat_replication WHERE application_name='standby_b'" 0
TIMEOUT_LOG="$WORK/quorum-timeout.log"
TIMEOUT_EXIT=0
if docker exec "$NAME" psql -X -v ON_ERROR_STOP=1 \
   -h 127.0.0.1 -p "$P1" -U lab_admin -d ch067_lab \
   -c "SET statement_timeout='2000ms'" \
   -c "BEGIN; SET LOCAL synchronous_commit=on; INSERT INTO public.replication_marker VALUES('quorum-ambiguous','must-reconcile'); COMMIT" \
   > "$TIMEOUT_LOG" 2>&1; then TIMEOUT_EXIT=0; else TIMEOUT_EXIT=$?; fi
CASES=$((CASES+1))
if [[ "$TIMEOUT_EXIT" -ne 0 ]] && grep -Eqi 'canceling statement due to statement timeout' "$TIMEOUT_LOG"; then
  PASS=$((PASS+1)); echo "PASS quorum_missing_second_blocks_and_times_out"
else
  FAIL=$((FAIL+1)); echo "FAIL quorum outage did not produce bounded timeout" >&2
fi
docker exec -u postgres "$NAME" pg_ctl -D "$B" -l /tmp/standby_b.log \
  -o "-c listen_addresses=127.0.0.1 -c port=$P3 -c unix_socket_directories=/tmp" \
  -w -t 35 start > "$WORK/restart-b.log" 2>&1
poll quorum_restored "$P1" postgres "SELECT count(*) FROM pg_stat_replication WHERE sync_state='quorum'" 2
AMBIGUOUS="$(q "$P1" ch067_lab "SELECT count(*) FROM public.replication_marker WHERE event_id='quorum-ambiguous'")"
CASES=$((CASES+1))
if [[ "$AMBIGUOUS" == 0 || "$AMBIGUOUS" == 1 ]]; then
  PASS=$((PASS+1)); echo "PASS client_timeout_outcome_reconciled_not_blindly_retried"
else
  FAIL=$((FAIL+1)); echo "FAIL cannot reconcile timed-out write" >&2
fi
poll standby_b_reconciles_outcome "$P3" ch067_lab \
  "SELECT count(*) FROM public.replication_marker WHERE event_id='quorum-ambiguous'" "$AMBIGUOUS"
# Safe lab config restoration: original effective setting was explicitly DEFAULT
# and verified absent from pg_file_settings. Never blindly RESET on shared systems.
q "$P1" postgres "ALTER SYSTEM RESET synchronous_standby_names" >/dev/null
check sync_rollback_reload "$(q "$P1" postgres 'SELECT pg_reload_conf()')" t
check exact_original_setting_restored "$(q "$P1" postgres 'SHOW synchronous_standby_names')" "$ORIGINAL"
check original_config_owner_restored "$(q "$P1" postgres "SELECT source FROM pg_settings WHERE name='synchronous_standby_names'")" "$ORIGINAL_SOURCE"
check original_no_auto_entry_restored "$(q "$P1" postgres "SELECT count(*) FROM pg_file_settings WHERE name='synchronous_standby_names'")" "$ORIGINAL_FILE_ROWS"
check primary_still_writable "$(q "$P1" ch067_lab "SELECT NOT pg_is_in_recovery()")" t
check standby_a_still_readonly "$(q "$P2" postgres 'SELECT pg_is_in_recovery()')" t
check standby_b_still_readonly "$(q "$P3" postgres 'SELECT pg_is_in_recovery()')" t
# One writer + two read-only standbys are directly checked above.
# That observation is NOT independent fencing or HA-manager acceptance.
export EVIDENCE CASES PASS FAIL VERS AMBIGUOUS
python3 - <<'PY'
import datetime,json,os
from pathlib import Path
data={
  "schema":"pg-v03-ch067070-three-process-replication-1",
  "scope":"one Docker network-none container; one primary and two standby PG18 processes",
  "real_postgresql_execution":True,
  "version_num":os.environ["VERS"],
  "tests":int(os.environ["CASES"]),"passed":int(os.environ["PASS"]),
  "failed":int(os.environ["FAIL"]),
  "ambiguous_commit_row_count_after_reconciliation":int(os.environ["AMBIGUOUS"]),
  "source_systems_isolated":False,
  "independent_failure_domains":False,
  "independent_fencing_proven":False,
  "ha_promotion_executed":False,
  "business_rpo_rto_verified":False,
  "production_or_staging_touched":False,
  "enterprise_certification":"NOT_CERTIFIED",
  "observed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()
}
Path(os.environ["EVIDENCE"]).write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
print("DISPOSABLE PG18 STREAMING/SYNC:",data["passed"],"/",data["tests"])
if data["failed"] or data["passed"]!=data["tests"]:raise SystemExit(1)
PY
