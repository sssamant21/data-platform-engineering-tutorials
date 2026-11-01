#!/usr/bin/env bash
# PostgreSQL 18 actual logical dump/restore; isolated disposable CI only.
set -Eeuo pipefail
export LC_ALL=C
[[ "$GITHUB_ACTIONS" == true && -n "$GITHUB_RUN_ID" ]] || {
  echo "REFUSED: GitHub Actions disposable lab only" >&2; exit 3;
}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SQL="$ROOT/postgresql/labs/sql"
OUT="$ROOT/postgresql/validation/evidence-v03-ch061062065-logical.json"
WORK="$(mktemp -d)"
NAME="pg18-logical-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
PGDATA=/tmp/postgresql-dbre-lab.v03logical/primary
PORT=55432
DUMPS=/tmp/v03-logical
CASES=0; PASS=0; FAIL=0
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT
docker pull postgres:18 >/dev/null
docker run -d --name "$NAME" --network none --tmpfs /tmp:rw,size=768m,mode=1777 \
  --memory 1536m --cpus 2 --pids-limit 256 \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=lab_admin \
  -e POSTGRES_DB=postgres -e PGDATA="$PGDATA" \
  postgres:18 -c listen_addresses=127.0.0.1 -c port="$PORT" > "$WORK/container-id"
[[ "$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$NAME")" == none ]] || {
  echo "REFUSED: external container network" >&2; exit 3;
}
[[ -z "$(docker port "$NAME")" ]] || { echo "REFUSED: published host ports" >&2; exit 3; }
for i in $(seq 1 75); do
  if docker exec "$NAME" pg_isready -h 127.0.0.1 -p "$PORT" -U lab_admin -d postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$NAME" pg_isready -h 127.0.0.1 -p "$PORT" -U lab_admin -d postgres >/dev/null
psqlc() {
  docker exec "$NAME" psql -X -v ON_ERROR_STOP=1 -A -t \
    -h 127.0.0.1 -p "$PORT" -U lab_admin -d "$1" -c "$2"
}
pgcmd() {
  docker exec -u postgres "$NAME" "$@" -h 127.0.0.1 -p "$PORT" -U lab_admin
}
check() {
  local label="$1" actual="$2" expected="$3"
  CASES=$((CASES+1))
  if [[ "$actual" == "$expected" ]]; then
    PASS=$((PASS+1)); echo "PASS $label"
  else
    FAIL=$((FAIL+1)); echo "FAIL $label expected=$expected observed=$actual" >&2
  fi
}
expected_failure() {
  local label="$1"; shift
  CASES=$((CASES+1))
  if "$@" > "$WORK/$label.log" 2>&1; then
    FAIL=$((FAIL+1)); echo "FAIL $label unexpectedly succeeded" >&2
  else
    PASS=$((PASS+1)); echo "PASS $label refused"
  fi
}
VERSION="$(psqlc postgres 'SHOW server_version_num')"
OBSERVED="$(psqlc postgres 'SHOW data_directory')"
SID="$(psqlc postgres 'SELECT system_identifier::text FROM pg_control_system()')"
check pg18_major "$((VERSION/10000))" 18
check lab_primary_pgdata "$OBSERVED" "$PGDATA"
[[ "$SID" =~ ^[0-9]+$ ]] || { echo "REFUSED: no cluster identifier" >&2; exit 3; }
docker exec -u postgres "$NAME" mkdir -p "$DUMPS"
for db in ch061_source ch062_source ch065_lab ch061_restored ch062_restored ch062_directory_restore ch065_restore; do
  psqlc postgres "CREATE DATABASE $db" >/dev/null
done
# Chapters 061 and 065: the tutorial's two-row data set.
for db in ch061_source ch065_lab; do
  psqlc "$db" "CREATE TABLE public.backup_probe(id integer PRIMARY KEY,marker text NOT NULL)" >/dev/null
done
psqlc ch061_source "INSERT INTO public.backup_probe VALUES (1,'restore-verified'),(2,'rpo-test')" >/dev/null
psqlc ch065_lab "INSERT INTO public.backup_probe VALUES (1,'retention-test'),(2,'restore-test')" >/dev/null
# Chapter 062: use the actual tutorial fixture and verify its original values.
docker exec -i "$NAME" psql -X -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p "$PORT" -U lab_admin -d ch062_source -f - \
  < "$SQL/062-fixture.sql" > "$WORK/ch062-fixture.log"
check ch062_source_count "$(psqlc ch062_source 'SELECT count(*) FROM ch062.orders')" 3
check ch062_source_sum "$(psqlc ch062_source 'SELECT sum(amount)::text FROM ch062.orders')" 61.50

# Refuse existing output files/dirs rather than silently overwriting them.
dump_custom() {
  local db="$1" target="$2"
  [[ ! -e "$DUMPS/$target" ]] || { echo "REFUSED: archive already exists" >&2; return 3; }
  pgcmd pg_dump -d "$db" -Fc -f "$DUMPS/$target"
}
dump_directory() {
  local db="$1" target="$2"
  [[ ! -e "$DUMPS/$target" ]] || { echo "REFUSED: directory archive exists" >&2; return 3; }
  pgcmd pg_dump -d "$db" -Fd -j 2 -f "$DUMPS/$target"
}
# Note: pgcmd appends connection flags; -j and -f are supported with -Fd.
dump_custom ch061_source ch061.dump
dump_custom ch062_source ch062.dump
dump_directory ch062_source ch062.dir
dump_custom ch065_lab ch065.dump
expected_failure overwrite_ch061_archive dump_custom ch061_source ch061.dump
expected_failure overwrite_ch062_archive dump_custom ch062_source ch062.dump
expected_failure overwrite_ch062_directory dump_directory ch062_source ch062.dir
expected_failure overwrite_ch065_archive dump_custom ch065_lab ch065.dump
check four_archives_present "$(docker exec "$NAME" sh -c "test -f $DUMPS/ch061.dump && test -f $DUMPS/ch062.dump && test -d $DUMPS/ch062.dir && test -f $DUMPS/ch065.dump && echo yes")" yes

for archive in ch061.dump ch062.dump ch062.dir ch065.dump; do
  pgcmd pg_restore -l "$DUMPS/$archive" > "$WORK/toc-$archive.txt"
  check "toc_$archive" "$(test -s "$WORK/toc-$archive.txt" && echo readable)" readable
done
docker exec -u postgres "$NAME" sha256sum "$DUMPS/ch061.dump" "$DUMPS/ch062.dump" "$DUMPS/ch065.dump" > "$WORK/dump-hashes.txt"
check file_hashes_recorded "$(wc -l < "$WORK/dump-hashes.txt" | tr -d ' ')" 3

# Restore into separate fresh databases (never --clean or overwrite).
pgcmd pg_restore --exit-on-error -d ch061_restored "$DUMPS/ch061.dump" > "$WORK/restore-061.log"
pgcmd pg_restore --exit-on-error -d ch062_restored "$DUMPS/ch062.dump" > "$WORK/restore-062.log"
pgcmd pg_restore --exit-on-error -d ch062_directory_restore -j 2 "$DUMPS/ch062.dir" > "$WORK/restore-062dir.log"
pgcmd pg_restore --exit-on-error -d ch065_restore "$DUMPS/ch065.dump" > "$WORK/restore-065.log"
check ch061_restored_count "$(psqlc ch061_restored 'SELECT count(*) FROM public.backup_probe')" 2
check ch061_restored_markers "$(psqlc ch061_restored "SELECT string_agg(marker,',' ORDER BY id) FROM public.backup_probe")" "restore-verified,rpo-test"
check ch065_restored_count "$(psqlc ch065_restore 'SELECT count(*) FROM public.backup_probe')" 2
check ch065_restored_markers "$(psqlc ch065_restore "SELECT string_agg(marker,',' ORDER BY id) FROM public.backup_probe")" "retention-test,restore-test"

# Real Chapter 062 acceptance SQL (includes count, sum, PK, identity seq).
docker exec -i "$NAME" psql -X -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p "$PORT" -U lab_admin -d ch062_restored -f - \
  < "$SQL/062-verify.sql" > "$WORK/ch062-verified.log" 2>&1
check ch062_restored_count "$(psqlc ch062_restored 'SELECT count(*) FROM ch062.orders')" 3
check ch062_restored_total "$(psqlc ch062_restored 'SELECT sum(amount)::text FROM ch062.orders')" 61.50
check ch062_directory_count "$(psqlc ch062_directory_restore 'SELECT count(*) FROM ch062.orders')" 3
check ch062_directory_total "$(psqlc ch062_directory_restore 'SELECT sum(amount)::text FROM ch062.orders')" 61.50
check ch062_pk_exists "$(psqlc ch062_restored "SELECT count(*) FROM pg_constraint WHERE conrelid='ch062.orders'::regclass AND contype='p'")" 1
check ch062_unique_constraint_exists "$(psqlc ch062_restored "SELECT count(*) FROM pg_constraint WHERE conrelid='ch062.orders'::regclass AND contype='u'")" 1
check ch062_identity_next_id "$(psqlc ch062_restored "INSERT INTO ch062.orders(order_ref,amount) VALUES('ORD-004',40.00) RETURNING order_id")" 4
expected_failure ch062_duplicate_unique psqlc ch062_restored "INSERT INTO ch062.orders(order_ref,amount) VALUES('ORD-004',99.00)"
check ch062_duplicate_no_mutation "$(psqlc ch062_restored 'SELECT count(*) FROM ch062.orders')" 4
# Globals are inventory only. Never execute global role/tablespace SQL.
pgcmd pg_dumpall --globals-only -f "$DUMPS/globals.sql"
check globals_inventory_exists "$(docker exec "$NAME" sh -c "test -s $DUMPS/globals.sql && echo recorded")" recorded
check globals_admin_role_present "$(docker exec "$NAME" grep -c '^CREATE ROLE lab_admin;' "$DUMPS/globals.sql")" 1
# The public retention worksheet is handled by a separate Python offline screen.
# This shell script does not delete, expire, prune or recycle any data.
export OUT CASES PASS FAIL VERSION
python3 - <<'PY'
import datetime, json, os
from pathlib import Path
data = {
  "schema":"pg-v03-ch061062065-disposable-logical-1",
  "scope":"one PostgreSQL 18 Docker network-none container with isolated logical restores",
  "runtime":"actual pg_dump/pg_restore/pg_dumpall and psql",
  "postgres_version_num":os.environ["VERSION"],
  "checks":int(os.environ["CASES"]),
  "passed":int(os.environ["PASS"]),
  "failed":int(os.environ["FAIL"]),
  "backup_deletion_executed":False,
  "retention_dry_run_only":True,
  "staging_or_production_changed":False,
  "enterprise_certification":"NOT_CERTIFIED",
  "completed_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()
}
Path(os.environ["OUT"]).write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
print("DISPOSABLE PG18 LOGICAL BACKUP/RESTORE:",data["passed"],"/",data["checks"])
if data["failed"] or data["checks"]!=data["passed"]:
    raise SystemExit(1)
PY
