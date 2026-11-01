#!/usr/bin/env bash
# Disposable PG18 physical backup + isolated PITR; no production/staging access.
set -Eeuo pipefail
export LC_ALL=C
[[ "$GITHUB_ACTIONS" == true && -n "$GITHUB_RUN_ID" ]] || {
  echo "REFUSED: GitHub Actions-only ephemeral lab" >&2; exit 3;
}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SQL="$ROOT/postgresql/labs/sql"
EVIDENCE="$ROOT/postgresql/validation/evidence-v03-ch061066-pitr.json"
WORK="$(mktemp -d)"
NAME="pg18-pitr-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
DATA=/tmp/postgresql-dbre-lab.v03pitr/primary
BACKUP=/tmp/v03base/base001
RESTORE=/tmp/v03-restored
ARCHIVE=/tmp/v03-walarchive
SOURCE_PORT=55442
RESTORE_PORT=55443
RUNS=0; PASSED=0; FAILED=0
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT
docker pull postgres:18 >/dev/null
docker run -d --name "$NAME" --network none --tmpfs /tmp:rw,size=1024m,mode=1777 \
  --memory 1536m --cpus 2 --pids-limit 256 \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=lab_admin \
  -e POSTGRES_DB=postgres -e PGDATA="$DATA" \
  postgres:18 -c listen_addresses=127.0.0.1 -c port="$SOURCE_PORT" \
  -c timezone=UTC -c wal_level=replica -c archive_mode=on \
  -c max_wal_senders=5 -c max_replication_slots=6 > "$WORK/container-id"
[[ "$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$NAME")" == none ]] || {
  echo "REFUSED: Docker networking not isolated" >&2; exit 3;
}
[[ -z "$(docker port "$NAME")" ]] || { echo "REFUSED: published host port" >&2; exit 3; }
for i in $(seq 1 80); do
  if docker exec "$NAME" pg_isready -h 127.0.0.1 -p "$SOURCE_PORT" -U lab_admin -d postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$NAME" pg_isready -h 127.0.0.1 -p "$SOURCE_PORT" -U lab_admin -d postgres
query() {
  local db="$1" statement="$2" port="$SOURCE_PORT"
  if [[ "$#" -gt 2 ]]; then port="$3"; fi
  docker exec "$NAME" psql -X -v ON_ERROR_STOP=1 -A -t \
    -h 127.0.0.1 -p "$port" -U lab_admin -d "$db" -c "$statement"
}
assert_eq() {
  local label="$1" observed="$2" expected="$3"
  RUNS=$((RUNS+1))
  if [[ "$observed" == "$expected" ]]; then
    PASSED=$((PASSED+1)); echo "PASS $label"
  else
    FAILED=$((FAILED+1)); echo "FAIL $label expected=$expected got=$observed" >&2
  fi
}
SID="$(query postgres 'SELECT system_identifier::text FROM pg_control_system()')"
OBSERVED="$(query postgres 'SHOW data_directory')"
VERSION="$(query postgres 'SHOW server_version_num')"
assert_eq pg18_version "$((VERSION/10000))" 18
assert_eq isolated_primary_pgdata "$OBSERVED" "$DATA"
assert_eq archive_mode_enabled "$(query postgres 'SHOW archive_mode')" on
[[ "$SID" =~ ^[0-9]+$ ]] || { echo "REFUSED: missing cluster identifier" >&2; exit 3; }
docker exec -u postgres "$NAME" mkdir -p "$ARCHIVE" /tmp/v03base
query postgres "ALTER SYSTEM SET archive_command = 'test ! -f $ARCHIVE/%f && cp %p $ARCHIVE/%f || cmp -s %p $ARCHIVE/%f'" >/dev/null
assert_eq archive_config_reloaded "$(query postgres 'SELECT pg_reload_conf()')" t
assert_eq archive_command_active "$(query postgres "SELECT current_setting('archive_command') LIKE '%$ARCHIVE%'")" t
for db in ch064_lab ch066_lab; do query postgres "CREATE DATABASE $db" >/dev/null; done
for triple in \
    'ch064_lab|064-fixture.sql|064-ONE-TIME-FIXTURE' \
    'ch066_lab|066-dr-fixture.sql|066-ONE-TIME-FIXTURE'; do
  IFS='|' read -r db file token <<< "$triple"
  docker exec -i "$NAME" psql -X -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p "$SOURCE_PORT" -U lab_admin -d "$db" \
    -v "expected_system_id=$SID" \
    -v "expected_lab_data_directory=$OBSERVED" \
    -v expected_lab_role=lab_admin -v "confirm_stage=$token" -f - \
    < "$SQL/$file" > "$WORK/fixture-$db.log"
done
assert_eq ch064_initial_empty "$(query ch064_lab 'SELECT count(*) FROM ch064.events')" 0
assert_eq ch066_reference_row "$(query ch066_lab 'SELECT count(*) FROM ch066.reference_data')" 1
# Base backup is FINISHED before generating any incident marker.
docker exec -u postgres "$NAME" pg_basebackup -h 127.0.0.1 -p "$SOURCE_PORT" \
  -U lab_admin -D "$BACKUP" -Fp -X stream --manifest-checksums=SHA256 > "$WORK/backup.log" 2>&1
docker exec -u postgres "$NAME" pg_verifybackup "$BACKUP" > "$WORK/verify.log" 2>&1
RUNS=$((RUNS+1)); PASSED=$((PASSED+1)); echo "PASS pg_basebackup_pg_verifybackup"
# Corrupt COPY, not authoritative backup; verified manifest must reject.
docker exec -u postgres "$NAME" cp -a "$BACKUP" /tmp/v03-corrupt
docker exec -u postgres "$NAME" sh -c 'printf X >> /tmp/v03-corrupt/PG_VERSION'
RUNS=$((RUNS+1))
if docker exec -u postgres "$NAME" pg_verifybackup /tmp/v03-corrupt > "$WORK/corrupt.log" 2>&1; then
  FAILED=$((FAILED+1)); echo "FAIL corrupt backup copy accepted" >&2
else
  PASSED=$((PASSED+1)); echo "PASS corrupt_backup_copy_refused"
fi
query ch064_lab "INSERT INTO ch064.events(event_key,phase) VALUES ('before-target','keep')" >/dev/null
query ch066_lab "INSERT INTO ch066.events(event_key,description) VALUES ('before-target','keep')" >/dev/null
TARGET="$(query postgres 'SELECT clock_timestamp()::text')"
[[ "$TARGET" == *+00 ]] || { echo "REFUSED: timestamp lacks UTC offset" >&2; exit 3; }
sleep 2
query ch064_lab "INSERT INTO ch064.events(event_key,phase) VALUES ('after-target','exclude')" >/dev/null
query ch066_lab "INSERT INTO ch066.events(event_key,description) VALUES ('after-target','exclude')" >/dev/null
query ch066_lab "DELETE FROM ch066.reference_data WHERE id=1" >/dev/null
query postgres 'SELECT pg_switch_wal()' >/dev/null
ARCHIVED=0
for i in $(seq 1 45); do
  ARCHIVED="$(query postgres 'SELECT archived_count FROM pg_stat_archiver')"
  if [[ "$ARCHIVED" =~ ^[0-9]+$ && "$ARCHIVED" -ge 1 ]]; then break; fi
  sleep 1
done
[[ "$ARCHIVED" -ge 1 ]] || { echo "FAIL no archived WAL observed" >&2; exit 1; }
assert_eq wal_archiver_success "$(query postgres 'SELECT last_archived_wal IS NOT NULL FROM pg_stat_archiver')" t
# Separate restored PGDATA and TCP port, still within network-none container.
docker exec -u postgres "$NAME" cp -a "$BACKUP" "$RESTORE"
docker exec -u postgres "$NAME" touch "$RESTORE/recovery.signal"
docker exec -i -u postgres "$NAME" sh -c "cat >> $RESTORE/postgresql.auto.conf" <<EOF
restore_command = 'cp $ARCHIVE/%f %p'
recovery_target_time = '$TARGET'
recovery_target_inclusive = off
recovery_target_action = 'pause'
recovery_target_timeline = 'current'
EOF
docker exec -u postgres "$NAME" pg_ctl -D "$RESTORE" -l /tmp/v03-restore.log \
  -o "-c port=$RESTORE_PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=/tmp" \
  -w -t 50 start > "$WORK/restore.log" 2>&1 || {
    docker exec "$NAME" sh -c 'tail -70 /tmp/v03-restore.log' >&2 || true
    echo "FAIL failed to start isolated PITR" >&2; exit 1;
  }
PAUSED=f
for i in $(seq 1 40); do
  if PAUSED="$(query postgres 'SELECT pg_is_wal_replay_paused()' "$RESTORE_PORT" 2>/dev/null)" && [[ "$PAUSED" == t ]]; then break; fi
  sleep 1
done
assert_eq recovery_paused_at_target "$PAUSED" t
assert_eq recovery_read_only "$(query postgres 'SELECT pg_is_in_recovery()' "$RESTORE_PORT")" t
assert_eq restored_distinct_pgdata "$(query postgres 'SHOW data_directory' "$RESTORE_PORT")" "$RESTORE"
assert_eq ch064_before_present "$(query ch064_lab "SELECT count(*) FROM ch064.events WHERE event_key='before-target' AND phase='keep'" "$RESTORE_PORT")" 1
assert_eq ch064_after_absent "$(query ch064_lab "SELECT count(*) FROM ch064.events WHERE event_key='after-target'" "$RESTORE_PORT")" 0
assert_eq ch066_before_present "$(query ch066_lab "SELECT count(*) FROM ch066.events WHERE event_key='before-target'" "$RESTORE_PORT")" 1
assert_eq ch066_after_absent "$(query ch066_lab "SELECT count(*) FROM ch066.events WHERE event_key='after-target'" "$RESTORE_PORT")" 0
assert_eq ch066_deleted_reference_restored "$(query ch066_lab "SELECT count(*) FROM ch066.reference_data WHERE id=1 AND payload='recover-me'" "$RESTORE_PORT")" 1
assert_eq original_primary_after_present "$(query ch064_lab "SELECT count(*) FROM ch064.events WHERE event_key='after-target'")" 1
assert_eq original_primary_delete_preserved "$(query ch066_lab "SELECT count(*) FROM ch066.reference_data WHERE id=1")" 0
docker exec -u postgres "$NAME" pg_ctl -D "$RESTORE" -m fast -w stop >/dev/null
RUNS=$((RUNS+1)); PASSED=$((PASSED+1)); echo "PASS isolated_restored_instance_stopped"
export EVIDENCE RUNS PASSED FAILED VERSION ARCHIVED
python3 - <<'PY'
import datetime,json,os
from pathlib import Path
report={
 "schema":"pg-v03-ch061066-disposable-physical-backup-pitr-1",
 "scope":"single network-none PG18 Docker container; separate original/restored PGDATA",
 "real_pg18_sql_executed":True,"postgres_version_num":os.environ["VERSION"],
 "archived_wal_count":int(os.environ["ARCHIVED"]),
 "checks":int(os.environ["RUNS"]),"passed":int(os.environ["PASSED"]),
 "failed":int(os.environ["FAILED"]),
 "staging_or_production_changed":False,"business_rpo_rto_verified":False,
 "external_fencing_verified":False,"enterprise_certification":"NOT_CERTIFIED",
 "checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()
}
Path(os.environ["EVIDENCE"]).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print("DISPOSABLE PHYSICAL BACKUP AND PITR:",report["passed"],"/",report["checks"])
if report["failed"] or report["checks"]!=report["passed"]:raise SystemExit(1)
PY
