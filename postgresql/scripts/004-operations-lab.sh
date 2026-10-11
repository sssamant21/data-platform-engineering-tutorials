#!/usr/bin/env bash
# PostgreSQL 18 disposable loopback-only three-instance lab.
set -Eeuo pipefail
umask 077
action="${1:-help}"
if [[ "$action" == help ]]; then
  printf '%s\n' "Usage: bash 004-operations-lab.sh setup|verify|start|stop|destroy" \
    "setup prints PG_LAB_ROOT; export it before later commands." \
    "destroy requires PG_LAB_CONFIRM_DESTROY=yes."
  exit 0
fi
case "$action" in setup|verify|start|stop|destroy) ;; *) echo "Unknown action" >&2; exit 2;; esac
[[ "$(id -u)" != 0 ]] || { echo "Run as an unprivileged lab OS user, not root." >&2; exit 2; }
for cmd in initdb pg_ctl psql pg_basebackup python3; do
  command -v "$cmd" >/dev/null || { echo "Missing tool: $cmd" >&2; exit 2; }
done
for cmd in initdb pg_ctl psql pg_basebackup; do
  [[ "$("$cmd" --version)" =~ PostgreSQL\)\ 18\. ]] ||
    { echo "Use PostgreSQL 18 binaries consistently: $cmd" >&2; exit 2; }
done
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS PGCHANNELBINDING
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGAPPNAME=chapter004-control
sql() {
  local port="$1"; shift
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p "$port" -U lab_admin -d ops_lab "$@"
}
guard() {
  : "${PG_LAB_ROOT:?Export PG_LAB_ROOT printed by setup}"
  [[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] ||
    { echo "Refusing unexpected lab path." >&2; exit 2; }
  [[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] ||
    { echo "Lab root must be an owned real directory." >&2; exit 2; }
  [[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == "postgresql18-dbre-sre-disposable" ]] ||
    { echo "Lab marker missing or mismatched." >&2; exit 2; }
  export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
}
start_node() {
  local node="$1"
  if ! pg_ctl -D "$PG_LAB_ROOT/$node" status >/dev/null 2>&1; then
    pg_ctl -D "$PG_LAB_ROOT/$node" -l "$PG_LAB_ROOT/logs/$node.log" -w -t 30 start
  fi
}
stop_nodes() {
  local node
  for node in standby2 standby1 primary; do
    if [[ -f "$PG_LAB_ROOT/$node/PG_VERSION" ]]; then
      if pg_ctl -D "$PG_LAB_ROOT/$node" status >/dev/null 2>&1; then
        pg_ctl -D "$PG_LAB_ROOT/$node" -m fast -w -t 30 stop
      elif [[ -f "$PG_LAB_ROOT/$node/postmaster.pid" ]]; then
        echo "Unresolved PID file at $node; investigate before deleting anything." >&2
        return 1
      fi
    fi
  done
}
verify() {
  [[ "$(sql 55432 -Atc 'SELECT pg_is_in_recovery()')" == f ]] ||
    { echo "Expected primary at 55432." >&2; return 1; }
  for port in 55433 55434; do
    [[ "$(sql "$port" -Atc 'SELECT pg_is_in_recovery()')" == t ]] ||
      { echo "Expected standby at $port." >&2; return 1; }
  done
  local token count attempt ready
  token="$(date +%s)-$$"
  sql 55432 -v probe_token="$token" <<'SQL'
SET statement_timeout = '5s';
SET lock_timeout = '1s';
INSERT INTO public.lab_probe(id, payload) VALUES (1, :'probe_token')
ON CONFLICT(id) DO UPDATE SET payload = EXCLUDED.payload;
SQL
  ready=0
  for attempt in {1..30}; do
    count="$(sql 55432 -Atc "SELECT count(*) FROM pg_stat_replication
      WHERE state='streaming' AND application_name IN ('standby1','standby2')")"
    if [[ "$count" == 2 ]]; then
      ready=1
      for port in 55433 55434; do
        count="$(sql "$port" -Atc "SELECT count(*) FROM public.lab_probe
          WHERE id=1 AND payload='$token'")"
        [[ "$count" == 1 ]] || ready=0
      done
      [[ "$ready" == 1 ]] && break
    fi
    sleep 1
  done
  [[ "$ready" == 1 ]] || { echo "Replication verification exceeded 30 polling attempts." >&2; return 1; }
  sql 55432 -c "SELECT application_name, state, sync_state FROM pg_stat_replication ORDER BY application_name;"
  printf '%s\n' "PASS: primary, two recovering standbys, two streaming senders and replicated probe."
}
if [[ "$action" == setup ]]; then
  [[ -z "${PG_LAB_ROOT:-}" ]] ||
    { echo "Unset PG_LAB_ROOT to create a fresh lab. Existing labs are not overwritten." >&2; exit 2; }
  python3 - <<'PY'
import socket
for port in (55432, 55433, 55434):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise SystemExit(f"Port {port} unavailable: {exc}")
PY
  PG_LAB_ROOT="$(mktemp -d /tmp/postgresql-dbre-lab.XXXXXXXX)"
  export PG_LAB_ROOT
  printf '%s\n' "postgresql18-dbre-sre-disposable" > "$PG_LAB_ROOT/LAB_MARKER"
  mkdir "$PG_LAB_ROOT/logs" "$PG_LAB_ROOT/socket"
  printf 'export PG_LAB_ROOT=%s\n' "$PG_LAB_ROOT"
  trap 'printf "Setup incomplete. Keep logs; export PG_LAB_ROOT=%s before stop/destroy.\n" "$PG_LAB_ROOT" >&2' ERR
  python3 - "$PG_LAB_ROOT" <<'PY'
from pathlib import Path
import secrets, sys
root = Path(sys.argv[1])
passwords = {role: secrets.token_hex(24) for role in
             ("lab_admin", "lab_repl", "lab_observer", "lab_app")}
(root/"initdb-password").write_text(passwords["lab_admin"]+"\n")
entries = []
for port in (55432,55433,55434):
    for role in ("lab_admin","lab_observer","lab_app"):
        entries.append(f"127.0.0.1:{port}:*:{role}:{passwords[role]}")
entries.append(f"127.0.0.1:55432:replication:lab_repl:{passwords['lab_repl']}")
(root/"credentials.pgpass").write_text("\n".join(entries)+"\n")
sql = [
 "SET password_encryption = 'scram-sha-256';",
 f"CREATE ROLE lab_repl LOGIN REPLICATION PASSWORD '{passwords['lab_repl']}';",
 f"CREATE ROLE lab_observer LOGIN PASSWORD '{passwords['lab_observer']}';",
 "GRANT pg_monitor TO lab_observer;",
 f"CREATE ROLE lab_app LOGIN PASSWORD '{passwords['lab_app']}';",
 "CREATE DATABASE ops_lab OWNER lab_app;",
 "\\connect ops_lab",
 "CREATE TABLE public.lab_probe(id integer PRIMARY KEY, payload text NOT NULL);",
 "GRANT SELECT, INSERT, UPDATE ON public.lab_probe TO lab_app;",
]
(root/"bootstrap.sql").write_text("\n".join(sql)+"\n")
for name in ("initdb-password","credentials.pgpass","bootstrap.sql"):
    (root/name).chmod(0o600)
PY
  initdb -D "$PG_LAB_ROOT/primary" -U lab_admin \
    --pwfile="$PG_LAB_ROOT/initdb-password" \
    --auth-local=scram-sha-256 --auth-host=scram-sha-256 \
    --encoding=UTF8 --locale=C --data-checksums
  cat >> "$PG_LAB_ROOT/primary/postgresql.conf" <<CFG
listen_addresses = '127.0.0.1'
port = 55432
unix_socket_directories = '$PG_LAB_ROOT/socket'
shared_buffers = '64MB'
max_connections = 30
wal_level = replica
max_wal_senders = 6
max_replication_slots = 0
wal_keep_size = '128MB'
hot_standby = on
fsync = on
full_page_writes = on
synchronous_commit = on
synchronous_standby_names = ''
log_line_prefix = '%m [%p] %a %u@%d '
CFG
  cat > "$PG_LAB_ROOT/primary/pg_hba.conf" <<'HBA'
local all all scram-sha-256
host all all 127.0.0.1/32 scram-sha-256
host replication lab_repl 127.0.0.1/32 scram-sha-256
HBA
  export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
  start_node primary
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
    -f "$PG_LAB_ROOT/bootstrap.sql"
  rm -- "$PG_LAB_ROOT/initdb-password" "$PG_LAB_ROOT/bootstrap.sql"
  for spec in standby1:55433 standby2:55434; do
    node="${spec%:*}"
    port="${spec#*:}"
    pg_basebackup -d "host=127.0.0.1 port=55432 user=lab_repl passfile=$PGPASSFILE application_name=$node sslmode=disable" \
      -D "$PG_LAB_ROOT/$node" -R -X stream --no-slot -w
    printf '\nport = %s\n' "$port" >> "$PG_LAB_ROOT/$node/postgresql.conf"
    start_node "$node"
  done
  printf 'export PG_LAB_ROOT=%s\n' "$PG_LAB_ROOT"
  verify
  trap - ERR
  exit 0
fi
guard
case "$action" in
  verify) verify ;;
  start) for node in primary standby1 standby2; do start_node "$node"; done; verify ;;
  stop) stop_nodes ;;
  destroy)
    [[ "${PG_LAB_CONFIRM_DESTROY:-}" == yes ]] ||
      { echo "Set PG_LAB_CONFIRM_DESTROY=yes to delete this disposable lab." >&2; exit 2; }
    stop_nodes
    python3 - "$PG_LAB_ROOT" <<'PY'
import sys
from pathlib import Path
root = sys.argv[1]
for line in Path("/proc/self/mountinfo").read_text().splitlines():
    mountpoint = line.split()[4]
    if mountpoint == root or mountpoint.startswith(root+"/"):
        raise SystemExit("Refusing to remove a lab containing a mount point.")
PY
    rm -rf -- "$PG_LAB_ROOT"
    echo "Disposable lab removed."
    ;;
esac
