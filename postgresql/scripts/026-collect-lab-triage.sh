#!/usr/bin/env bash
# Read-only database collection for the disposable Chapter 004 PRIMARY only.
set -euo pipefail
if [[ "$#" == 1 ]]; then
  if [[ "$1" == "--help" ]]; then
    echo "Usage: bash 026-collect-lab-triage.sh LABEL"
    echo "Non-root Chapter 004 owner, PG_LAB_ROOT and PG18 tools required."
    echo "Creates a private bundle with explicit capture/validation status."
    exit 0
  fi
fi
[[ "$#" == 1 ]] || { echo "Use --help or a simple label" >&2; exit 2; }
label="$1"
[[ "$label" =~ ^[A-Za-z0-9_-]{1,32}$ ]] || exit 2
[[ "$(id -u)" != 0 ]] || { echo "Use the non-root lab owner" >&2; exit 2; }
for command in psql timeout python3 mktemp stat; do
  command -v "$command" >/dev/null || { echo "Missing dependency: $command" >&2; exit 2; }
done
test -n "$PG_LAB_ROOT"
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ ! -L "$PG_LAB_ROOT/LAB_MARKER" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
passfile="$PG_LAB_ROOT/credentials.pgpass"
[[ -f "$passfile" && ! -L "$passfile" && -O "$passfile" ]] || exit 2
[[ "$(stat -c %a "$passfile")" == 600 ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$passfile" PGCONNECT_TIMEOUT=3 PGSSLMODE=disable PGGSSENCMODE=disable
export PGAPPNAME=c026_collector
export PGOPTIONS='-c statement_timeout=3s -c lock_timeout=500ms'
identity="$(timeout --kill-after=2s 8s psql -X -w -qAt -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab \
  -c "SELECT current_setting('data_directory'),pg_is_in_recovery(),current_setting('server_version_num')::int BETWEEN 180000 AND 189999;")"
[[ "$identity" == "$PG_LAB_ROOT/primary|f|t" ]] || { echo "Wrong disposable primary identity" >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
sql_file="$script_dir/026-triage-snapshot.sql"
[[ -f "$sql_file" ]] || { echo "Missing snapshot SQL" >&2; exit 2; }
umask 077
parent="$PG_LAB_ROOT/c026-evidence"
[[ ! -L "$parent" ]] || exit 2
mkdir -p -m 700 "$parent"
[[ -d "$parent" && -O "$parent" && "$(stat -c %a "$parent")" == 700 ]] || exit 2
bundle="$(mktemp -d "$parent/$label.XXXXXXXX")"
rc=0
timeout --kill-after=2s 8s psql -X -w -qAt -v ON_ERROR_STOP=1 \
  -v source_id=chapter004-primary-55432 -h 127.0.0.1 -p 55432 \
  -U lab_observer -d ops_lab -f "$sql_file" \
  > "$bundle/database.json" 2> "$bundle/database.stderr" || rc=$?
printf '%s\n' "$rc" > "$bundle/database.exit"
if [[ "$rc" == 0 ]]; then
  python3 - "$bundle/database.json" <<'PY' || rc=$?
import json, sys
from pathlib import Path
sample=json.loads(Path(sys.argv[1]).read_text())
assert sample["schema_version"]==1 and isinstance(sample["sessions"],list)
assert sample["server_port"]==55432 and sample["in_recovery"] is False
PY
fi
printf '%s\n' "$rc" > "$bundle/database.validation_exit"
capture_optional() {
  local name="$1"
  shift
  local status=0
  if command -v "$1" >/dev/null; then
    timeout --kill-after=2s 5s "$@" > "$bundle/$name.txt" 2> "$bundle/$name.stderr" || status=$?
  else
    status=127
    echo "UNAVAILABLE: optional command" > "$bundle/$name.stderr"
    : > "$bundle/$name.txt"
  fi
  printf '%s\n' "$status" > "$bundle/$name.exit"
}
capture_optional filesystem df -P "$PG_LAB_ROOT"
capture_optional vmstat vmstat 1 3
capture_optional processes ps -C postgres -o pid,ppid,comm,pcpu,pmem,etime
python3 - "$bundle" "$label" "$rc" <<'PY'
from datetime import datetime, timezone
from pathlib import Path
import json, sys
root=Path(sys.argv[1])
status={p.stem:int(p.read_text()) for p in root.glob("*.exit")}
record={"schema_version":1,"label":sys.argv[2],"completed_at":datetime.now(timezone.utc).isoformat(),
        "source_id":"chapter004-primary-55432","database_validation_exit":int(sys.argv[3]),
        "captures":status,
        "limitations":"Optional host commands describe this host/namespace; database collection is metadata only."}
(root/"manifest.json").write_text(json.dumps(record,indent=2)+"\n")
PY
echo "$bundle"
if [[ "$rc" != 0 ]]; then
  echo "Database evidence incomplete; retain bundle and inspect statuses privately" >&2
  exit 1
fi
