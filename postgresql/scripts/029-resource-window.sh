#!/usr/bin/env bash
# Disposable Chapter 004 lab only. Read-only PostgreSQL observation.
set -euo pipefail
if [[ "$#" == 1 && "$1" == --help ]]; then
  echo 'Usage: bash postgresql/scripts/029-resource-window.sh LABEL'
  echo 'Collect 10 bounded snapshots and optional vmstat/iostat host evidence.'
  exit 0
fi
[[ "$#" == 1 ]] || { echo 'One phase label is required' >&2; exit 2; }
[[ "$1" =~ ^[a-z][a-z0-9_-]{0,23}$ ]] || { echo 'Invalid phase label' >&2; exit 2; }
[[ "$(id -u)" != 0 ]] || { echo 'Run as the lab OS owner' >&2; exit 2; }
test -n "$PG_LAB_ROOT"
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ -f "$PG_LAB_ROOT/credentials.pgpass" && ! -L "$PG_LAB_ROOT/credentials.pgpass" && -O "$PG_LAB_ROOT/credentials.pgpass" ]] || exit 2
[[ "$(stat -c %a "$PG_LAB_ROOT/credentials.pgpass")" == 600 ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=3 PGSSLMODE=disable PGGSSENCMODE=disable
export PGAPPNAME=c029_observer
export PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms -c transaction_timeout=5s'
observer() {
  psql -X -w -qAt -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab "$@"
}
[[ "$(observer -c 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(observer -c 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(observer -c "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
umask 077
out="$(mktemp -d "$PG_LAB_ROOT/c029-$1.XXXXXXXX")"
# Print immediately so incomplete windows remain discoverable.
printf 'Evidence: %s\n' "$out"
date -u +%FT%TZ > "$out/start-utc.txt"
uname -sr > "$out/kernel.txt"
getconf _NPROCESSORS_ONLN > "$out/online-cpus.txt"
if [[ -r /proc/meminfo ]]; then
  cat /proc/meminfo > "$out/meminfo-before.txt"
fi
for resource in cpu memory io; do
  if [[ -r "/proc/pressure/$resource" ]]; then
    cat "/proc/pressure/$resource" > "$out/psi-$resource-before.txt"
  else
    echo unavailable > "$out/psi-$resource-before.txt"
  fi
done
host_jobs=()
if command -v timeout >/dev/null && command -v vmstat >/dev/null; then
  (timeout 15s vmstat 1 11 > "$out/vmstat.txt" 2> "$out/vmstat.stderr" || echo 'Host command failed' > "$out/vmstat.failed") &
  host_jobs+=("$!")
else
  echo unavailable > "$out/vmstat.txt"
fi
if command -v timeout >/dev/null && command -v iostat >/dev/null; then
  (timeout 15s iostat -x -y 1 10 > "$out/iostat.txt" 2> "$out/iostat.stderr" || echo 'Host command failed' > "$out/iostat.failed") &
  host_jobs+=("$!")
else
  echo unavailable > "$out/iostat.txt"
fi
for sample in $(seq 1 10); do
  file="$(printf '%s/sample-%02d.json' "$out" "$sample")"
  observer -f "$script_dir/029-resource-snapshot.sql" > "$file" 2> "$file.stderr"
  [[ "$sample" == 10 ]] || sleep 1
done
for job in "${host_jobs[@]}"; do
  wait "$job"
done
if [[ -r /proc/meminfo ]]; then
  cat /proc/meminfo > "$out/meminfo-after.txt"
fi
for resource in cpu memory io; do
  if [[ -r "/proc/pressure/$resource" ]]; then
    cat "/proc/pressure/$resource" > "$out/psi-$resource-after.txt"
  fi
done
date -u +%FT%TZ > "$out/end-utc.txt"
echo 'Collection completed; validate JSON and epochs before interpreting deltas.' > "$out/collection-status.txt"
