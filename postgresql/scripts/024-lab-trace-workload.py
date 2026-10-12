#!/usr/bin/env python3
"""Three bounded lab operations with trace-shaped records; not an OTel exporter."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import uuid


def connect(role, sql, env):
    return subprocess.run(
        ["psql", "-X", "-w", "-qAt", "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose",
         "-h", "127.0.0.1", "-p", "55432", "-U", role, "-d", "c024_logs"],
        input=sql, env=env, capture_output=True, text=True, timeout=8)


def guard():
    raw = os.environ.get("PG_LAB_ROOT", "")
    if os.getuid() == 0 or not re.fullmatch(r"/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+", raw):
        raise ValueError("non-root Chapter 004 owner and PG_LAB_ROOT required")
    root = Path(raw)
    if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("real owned lab directory required")
    marker = root / "LAB_MARKER"
    if marker.is_symlink() or marker.read_text().strip() != "postgresql18-dbre-sre-disposable":
        raise ValueError("invalid lab marker")
    passfile = root / "credentials.pgpass"
    mode = passfile.stat().st_mode
    if (passfile.is_symlink() or not stat.S_ISREG(mode)
            or passfile.stat().st_uid != os.getuid() or stat.S_IMODE(mode) != 0o600):
        raise ValueError("private owned passfile required")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(PGPASSFILE=str(passfile), PGCONNECT_TIMEOUT="3", PGSSLMODE="disable",
               PGGSSENCMODE="disable", PGAPPNAME="c024_control",
               PGOPTIONS="-c statement_timeout=2s -c lock_timeout=500ms "
                         "-c transaction_timeout=5s -c idle_in_transaction_session_timeout=5s")
    client = subprocess.run(["psql", "--version"], env=env, capture_output=True, text=True, timeout=5)
    if client.returncode or not re.search(r"PostgreSQL\) 18\.", client.stdout):
        raise ValueError("PostgreSQL 18 client required")
    check = connect("lab_admin", "SELECT current_setting('data_directory'), pg_is_in_recovery(), "
                    "current_setting('server_version_num'), current_setting('logging_collector'), "
                    "current_setting('log_destination'), current_setting('compute_query_id');\n", env)
    fields = check.stdout.strip().split("|")
    if (check.returncode or len(fields) != 6 or fields[0] != str(root / "primary")
            or fields[1] != "f" or not 180000 <= int(fields[2]) < 190000
            or fields[3:] != ["on", "jsonlog", "on"]):
        raise ValueError("expected PG18 lab primary and temporary JSON logging settings")
    return root, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="traces.jsonl", help="new private evidence basename")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.jsonl", args.output):
        parser.error("simple .jsonl basename required")
    os.umask(0o077)
    try:
        root, base_env = guard()
        directory = root / "c024-evidence"
        directory.mkdir(mode=0o700, exist_ok=True)
        if directory.is_symlink() or directory.stat().st_uid != os.getuid() or stat.S_IMODE(directory.stat().st_mode) != 0o700:
            raise ValueError("real owned private evidence directory required")
        header = ("SELECT pg_backend_pid(), "
                  "to_hex(trunc(extract(epoch FROM backend_start))::integer)||'.'||to_hex(pid) "
                  "FROM pg_stat_activity WHERE pid=pg_backend_pid();\n")
        operations = [("fast", "SELECT 1;\n"),
                      ("slow", "SELECT pg_sleep(0.25);\n"),
                      ("timeout", "SET statement_timeout='100ms';\nSELECT pg_sleep(2);\n")]
        path = directory / args.output
        with path.open("x", encoding="utf-8") as output:
            for name, sql in operations:
                trace_id = uuid.uuid4().hex
                app = "c024_" + trace_id
                env = dict(base_env, PGAPPNAME=app)
                started = datetime.now(timezone.utc)
                tick = time.monotonic()
                pid = session = state_code = None
                outcome = "client_timeout"
                try:
                    result = connect("lab_app", header + sql, env)
                    outcome = "success" if result.returncode == 0 else "error"
                    first = result.stdout.splitlines()[0] if result.stdout.splitlines() else ""
                    match = re.fullmatch(r"([0-9]+)\|([0-9a-f]+\.[0-9a-f]+)", first)
                    if match:
                        pid, session = int(match[1]), match[2]
                    error = re.search(r"(?:ERROR|FATAL):\s+([0-9A-Z]{5}):", result.stderr)
                    if error:
                        state_code = error[1]
                except subprocess.TimeoutExpired:
                    pass
                duration = (time.monotonic() - tick) * 1000
                record = dict(source_id="chapter004-primary-55432", trace_id=trace_id,
                              span_id=uuid.uuid4().hex[:16], operation=name,
                              application_name=app, database="c024_logs", pid=pid,
                              session_id=session, start=started.isoformat(),
                              end=datetime.now(timezone.utc).isoformat(),
                              duration_ms=round(duration, 3), outcome=outcome,
                              state_code=state_code)
                output.write(json.dumps(record) + "\n")
                output.flush()
        print(path)
        print("Educational client records only; no SQL or raw error text exported.")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Lab runner refused/failed: {exc}\n")


if __name__ == "__main__":
    main()
