#!/usr/bin/env bash
# Only a self-contained, Docker network-none PostgreSQL 18 CI lab.
set -Eeuo pipefail
export LC_ALL=C
[[ "$GITHUB_ACTIONS" == true && -n "$GITHUB_RUN_ID" ]] || {
  echo "REFUSED: GitHub Actions-only disposable fixture harness" >&2; exit 3;
}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SQL="$ROOT/postgresql/labs/sql"
NAME="pg18-ch061070-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
PGDATA="/tmp/postgresql-dbre-lab.v03guard/primary"
EVIDENCE="$ROOT/postgresql/validation/evidence-v03-ch061070.json"
WORK="$(mktemp -d)"
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT
docker pull postgres:18 >/dev/null
docker run -d --name "$NAME" --network none --tmpfs /tmp:rw,size=512m,mode=1777 \
  --memory 1g --cpus 2 --pids-limit 256 \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=lab_admin \
  -e POSTGRES_DB=postgres -e PGDATA="$PGDATA" \
  postgres:18 -c listen_addresses=127.0.0.1 -c port=55432 \
  -c max_replication_slots=5 -c max_slot_wal_keep_size=64MB > "$WORK/id"
NET="$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$NAME")"
[[ "$NET" == none ]] || { echo "REFUSED: unsafe Docker network" >&2; exit 3; }
[[ -z "$(docker port "$NAME")" ]] || {
  echo "REFUSED: published host port mapping" >&2; exit 3;
}
for i in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -h 127.0.0.1 -p 55432 -U lab_admin -d postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$NAME" pg_isready -h 127.0.0.1 -p 55432 -U lab_admin -d postgres
query() {
  docker exec "$NAME" psql -X -v ON_ERROR_STOP=1 -A -t \
    -h 127.0.0.1 -p 55432 -U lab_admin -d "$1" -c "$2"
}
SID="$(query postgres 'SELECT system_identifier::text FROM pg_control_system()')"
DATA="$(query postgres 'SHOW data_directory')"
VER="$(query postgres 'SHOW server_version_num')"
[[ "$SID" =~ ^[0-9]+$ && "$DATA" == "$PGDATA" && "$VER" -ge 180000 && "$VER" -lt 190000 ]] || {
  echo "REFUSED: unexpected cluster version or PGDATA" >&2; exit 3;
}
for db in ch064_lab ch066_lab ch068_lab ch070_lab; do
  query postgres "CREATE DATABASE $db" >/dev/null
done
query postgres "CREATE ROLE lab_readonly LOGIN" >/dev/null
printf 'case\tresult\texit_code\n' > "$WORK/cases.tsv"
CASES=0; PASSES=0; FAILURES=0
run_case() {
  local label="$1" expectation="$2" file="$3" database="$4" stage="$5" mode="$6"
  local sid="$SID" data="$DATA" role="lab_admin" user="lab_admin" port=55432 code=0
  case "$mode" in
    normal) ;;
    bad_sid) sid=0 ;;
    bad_data) data=/tmp/wrong-PGDATA ;;
    bad_role) role=unapproved_role ;;
    bad_db) database=postgres ;;
    bad_stage) stage=INVALID-STAGE ;;
    bad_port) port=55433 ;;
    bad_user) user=lab_readonly ;;
    missing_sid) sid="" ;;
    missing_stage) stage="" ;;
    *) echo "Unknown mode $mode" >&2; exit 3 ;;
  esac
  local -a opts=(-X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$port" -U "$user" -d "$database")
  if [[ -n "$sid" ]]; then opts+=(-v "expected_system_id=$sid"); fi
  opts+=(-v "expected_lab_data_directory=$data" -v "expected_lab_role=$role")
  if [[ -n "$stage" ]]; then opts+=(-v "confirm_stage=$stage"); fi
  if docker exec -i "$NAME" psql "${opts[@]}" -f - < "$SQL/$file" > "$WORK/$label.log" 2>&1; then code=0; else code=$?; fi
  CASES=$((CASES+1))
  if [[ "$expectation" == yes && "$code" == 0 ]] || [[ "$expectation" == no && "$code" != 0 ]]; then
    PASSES=$((PASSES+1)); printf '%s\tPASS\t%s\n' "$label" "$code" >> "$WORK/cases.tsv"
    echo "PASS $label (expected $expectation, exit $code)"
  else
    FAILURES=$((FAILURES+1)); printf '%s\tFAIL\t%s\n' "$label" "$code" >> "$WORK/cases.tsv"
    echo "FAIL $label (expected $expectation, exit $code)" >&2
    tail -16 "$WORK/$label.log" >&2
  fi
}
assert_query() {
  local label="$1" db="$2" statement="$3" expected="$4" got=""
  if got="$(query "$db" "$statement")" && [[ "$got" == "$expected" ]]; then
    PASSES=$((PASSES+1)); printf '%s\tPASS\t0\n' "$label" >> "$WORK/cases.tsv"
  else
    FAILURES=$((FAILURES+1)); printf '%s\tFAIL\t3\n' "$label" >> "$WORK/cases.tsv"
    echo "FAIL state invariant: $label" >&2
  fi
  CASES=$((CASES+1))
}
for pair in 064:064-fixture.sql:064-ONE-TIME-FIXTURE \
            066:066-dr-fixture.sql:066-ONE-TIME-FIXTURE \
            070:070-one-time-marker-fixture.sql:070-ONE-TIME-MARKER; do
  IFS=: read -r num file stage <<< "$pair"
  db="ch$num""_lab"
  for mode in missing_sid bad_sid bad_data bad_role bad_db bad_stage; do
    run_case "$num-$mode" no "$file" "$db" "$stage" "$mode"
  done
  assert_query "$num-refusals-no-schema" "$db" "SELECT to_regnamespace('ch$num') IS NULL" t
  run_case "$num-create-once" yes "$file" "$db" "$stage" normal
  run_case "$num-rerun-refused" no "$file" "$db" "$stage" normal
done
assert_query "064-empty-events" ch064_lab "SELECT count(*) FROM ch064.events" 0
assert_query "066-one-reference-row" ch066_lab "SELECT count(*) FROM ch066.reference_data WHERE id=1 AND payload='recover-me'" 1
assert_query "070-one-marker" ch070_lab "SELECT count(*) FROM ch070.markers WHERE id='before-switchover'" 1
for mode in missing_sid bad_sid bad_db bad_stage bad_port bad_user; do
  run_case "068-setup-$mode" no 068-safe-slot-setup.sql ch068_lab 068-CREATE-SLOT "$mode"
done
assert_query "068-no-slot-after-refusals" postgres "SELECT count(*) FROM pg_replication_slots WHERE slot_name='ch068_lab_slot'" 0
run_case "068-setup" yes 068-safe-slot-setup.sql ch068_lab 068-CREATE-SLOT normal
run_case "068-setup-rerun" no 068-safe-slot-setup.sql ch068_lab 068-CREATE-SLOT normal
assert_query "068-inactive-slot" postgres "SELECT count(*) FROM pg_replication_slots WHERE slot_name='ch068_lab_slot' AND slot_type='physical' AND NOT active" 1
run_case "068-workload-bad-stage" no 068-safe-wal-workload.sql ch068_lab 068-GENERATE-WAL bad_stage
run_case "068-workload" yes 068-safe-wal-workload.sql ch068_lab 068-GENERATE-WAL normal
assert_query "068-1000-rows" ch068_lab "SELECT count(*) FROM ch068.wal_probe" 1000
run_case "068-workload-rerun" no 068-safe-wal-workload.sql ch068_lab 068-GENERATE-WAL normal
assert_query "068-no-duplicate-rows" ch068_lab "SELECT count(*) FROM ch068.wal_probe" 1000
run_case "068-cleanup-bad-stage" no 068-safe-slot-cleanup.sql ch068_lab 068-DROP-LAB-SLOT bad_stage
assert_query "068-slot-still-present" postgres "SELECT count(*) FROM pg_replication_slots WHERE slot_name='ch068_lab_slot'" 1
run_case "068-cleanup" yes 068-safe-slot-cleanup.sql ch068_lab 068-DROP-LAB-SLOT normal
assert_query "068-slot-gone" postgres "SELECT count(*) FROM pg_replication_slots WHERE slot_name='ch068_lab_slot'" 0
assert_query "068-schema-gone" ch068_lab "SELECT to_regnamespace('ch068') IS NULL" t
run_case "068-cleanup-rerun" no 068-safe-slot-cleanup.sql ch068_lab 068-DROP-LAB-SLOT normal
export EVIDENCE WORK VER NET CASES PASSES FAILURES
python3 - <<'PY'
import csv, datetime, json, os
from pathlib import Path
with (Path(os.environ["WORK"])/"cases.tsv").open(encoding="utf-8") as handle:
    rows=list(csv.DictReader(handle,delimiter="\t"))
document={
    "schema":"pg-v03-ch061070-disposable-1",
    "scope":"PostgreSQL 18 disposable Docker; actual psql positive/negative execution",
    "network_mode":os.environ["NET"],
    "postgres_version_num":os.environ["VER"],
    "test_count":int(os.environ["CASES"]),
    "passed":int(os.environ["PASSES"]),
    "failed":int(os.environ["FAILURES"]),
    "source_records":"synthetic disposable only",
    "enterprise_certification":"NOT_CERTIFIED",
    "staging_rehearsal_executed":False,
    "cases":rows,
    "observed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
Path(os.environ["EVIDENCE"]).write_text(json.dumps(document,indent=2)+"\n",encoding="utf-8")
print("Disposable PG18 runtime:",document["passed"],"/",document["test_count"])
if document["failed"] or document["passed"]!=document["test_count"]:
    raise SystemExit(1)
PY
