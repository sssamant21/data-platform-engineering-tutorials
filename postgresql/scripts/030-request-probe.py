#!/usr/bin/env python3
"""Eight serial synthetic reads in the guarded Chapter 004 PostgreSQL 18 lab."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

def fail(message):
    raise SystemExit(message)

if sys.argv[1:] == ["--help"]:
    print("Usage: python3 postgresql/scripts/030-request-probe.py PHASE")
    print("Eight bounded lab requests; JSON lines on stdout; no automatic retries.")
    raise SystemExit(0)
if len(sys.argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9_-]{0,23}", sys.argv[1]):
    fail("One valid phase label is required")
if os.geteuid() == 0:
    fail("Run as the lab OS owner")
root_text = os.environ.get("PG_LAB_ROOT", "")
if not re.fullmatch(r"/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+", root_text):
    fail("Invalid PG_LAB_ROOT")
root = Path(root_text)
if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.geteuid():
    fail("Lab directory ownership/type mismatch")
if (root/"LAB_MARKER").read_text().strip() != "postgresql18-dbre-sre-disposable":
    fail("Lab marker mismatch")
password_file = root/"credentials.pgpass"
info = password_file.lstat()
if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
    fail("Credential-file ownership/type/mode mismatch")
env = dict(os.environ)
for key in ("PGOPTIONS", "PGSERVICE", "PGSERVICEFILE", "PGPASSWORD", "PGHOSTADDR",
            "PGDATABASE", "PGTARGETSESSIONATTRS"):
    env.pop(key, None)
env.update(PGPASSFILE=str(password_file), PGCONNECT_TIMEOUT="3", PGSSLMODE="disable",
           PGGSSENCMODE="disable", PGAPPNAME="c030_probe",
           PGOPTIONS="-c statement_timeout=2s -c lock_timeout=700ms -c transaction_timeout=3s")
base = ["psql", "-X", "-w", "-qAt", "-v", "ON_ERROR_STOP=1",
        "-v", "VERBOSITY=sqlstate", "-h", "127.0.0.1", "-p", "55432", "-d", "ops_lab"]
guard = subprocess.run(base + ["-U", "lab_observer", "-c",
    "SELECT current_setting('data_directory'),pg_is_in_recovery(),"
    "current_setting('server_version_num')::int BETWEEN 180000 AND 189999"],
    env=env, capture_output=True, text=True, timeout=6)
if guard.returncode != 0 or guard.stdout.strip() != root_text+"/primary|f|t":
    fail("Primary target/version verification failed")
# Fixed fixture only. No user-supplied SQL or connection parameters.
sql = ("BEGIN READ ONLY; "
       "SELECT count(*) FROM c030_incident.requests WHERE a=7 AND b=7; "
       "ROLLBACK;")
failed = 0
for attempt in range(1, 9):
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    tick = time.monotonic()
    try:
        result = subprocess.run(base + ["-U", "lab_app", "-c", sql], env=env,
                                capture_output=True, text=True, timeout=6)
        match = re.search(r"ERROR:\s+([0-9A-Z]{5})(?:\s|$)", result.stderr)
        sqlstate = match.group(1) if match else None
        ok = result.returncode == 0 and result.stdout.strip() == "200"
        outcome = "success" if ok else ("database_error" if result.returncode else "wrong_result")
        code = result.returncode
    except subprocess.TimeoutExpired:
        ok, outcome, sqlstate, code = False, "client_process_timeout", None, None
    elapsed = (time.monotonic()-tick)*1000
    failed += not ok
    print(json.dumps({"phase": sys.argv[1], "attempt": attempt,
        "started_at": started, "duration_ms": round(elapsed,3),
        "outcome": outcome, "sqlstate": sqlstate, "exit_code": code,
        "correct_result": ok}), flush=True)
    if attempt != 8:
        time.sleep(0.2)
# Preserve all observations; a failing phase returns a nonzero status after collection.
raise SystemExit(1 if failed else 0)
