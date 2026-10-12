#!/usr/bin/env python3
"""Bounded synthetic probe for the disposable Chapter 004 primary ONLY."""
import argparse
import csv
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import uuid
from datetime import datetime, timezone


def run_sql(role, sql, env):
    return subprocess.run(
        ["psql", "-X", "-w", "-qAt", "-v", "ON_ERROR_STOP=1",
         "-h", "127.0.0.1", "-p", "55432", "-U", role, "-d", "ops_lab", "-c", sql],
        env=env, capture_output=True, text=True, timeout=8)


def guard():
    raw = os.environ.get("PG_LAB_ROOT", "")
    if os.getuid() == 0 or not re.fullmatch(r"/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+", raw):
        raise ValueError("requires non-root Chapter 004 lab owner and PG_LAB_ROOT")
    root = Path(raw)
    if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("lab root must be a real directory owned by this user")
    marker = root / "LAB_MARKER"
    if marker.is_symlink() or marker.read_text().strip() != "postgresql18-dbre-sre-disposable":
        raise ValueError("invalid disposable marker")
    passfile = root / "credentials.pgpass"
    mode = passfile.stat().st_mode
    if (passfile.is_symlink() or not stat.S_ISREG(mode)
            or passfile.stat().st_uid != os.getuid() or stat.S_IMODE(mode) != 0o600):
        raise ValueError("private owner-only regular passfile required")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(PGPASSFILE=str(passfile), PGCONNECT_TIMEOUT="3", PGSSLMODE="disable",
               PGGSSENCMODE="disable", PGAPPNAME="c021_probe",
               PGOPTIONS="-c statement_timeout=1s -c lock_timeout=500ms "
                         "-c transaction_timeout=2s -c idle_in_transaction_session_timeout=2s "
                         "-c idle_session_timeout=0 -c timezone=UTC")
    version = subprocess.run(["psql", "--version"], env=env, capture_output=True,
                             text=True, timeout=5)
    if version.returncode or not re.search(r"PostgreSQL\) 18\.", version.stdout):
        raise ValueError("PostgreSQL 18 psql required")
    check = run_sql("lab_admin",
                    "SELECT current_setting('data_directory'), pg_is_in_recovery(), "
                    "current_setting('server_version_num');", env)
    fields = check.stdout.strip().split("|")
    if (check.returncode or len(fields) != 3 or fields[0] != str(root / "primary")
            or fields[1] != "f" or not 180000 <= int(fields[2]) <= 189999):
        raise ValueError("server must be the PostgreSQL 18 disposable primary")
    return root, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new CSV basename in lab evidence directory")
    parser.add_argument("--mode", choices=["fast", "slow"], default="fast")
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.count <= 20 or not re.fullmatch(r"[A-Za-z0-9_-]+\.csv", args.output):
        parser.error("count must be 1..20 and output a simple .csv basename")
    os.umask(0o077)
    try:
        root, env = guard()
        directory = root / "c021-evidence"
        directory.mkdir(mode=0o700, exist_ok=True)
        if (directory.is_symlink() or directory.stat().st_uid != os.getuid()
                or stat.S_IMODE(directory.stat().st_mode) != 0o700):
            raise ValueError("evidence directory must be real, owned and mode 0700")
        sql = "BEGIN; "
        if args.mode == "slow":
            sql += "SELECT pg_sleep(0.4); "
        sql += "SELECT value FROM c021_slo.probe WHERE id=1 FOR UPDATE; ROLLBACK;"
        output = directory / args.output
        # Exclusive creation prevents overwriting previous evidence or following a file symlink.
        with output.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["event_id", "finished_at", "eligible", "success", "duration_ms"])
            for _ in range(args.count):
                start = time.monotonic()
                success = False
                try:
                    result = run_sql("lab_app", sql, env)
                    success = result.returncode == 0 and result.stdout.strip() == "100"
                except subprocess.TimeoutExpired:
                    pass
                duration = (time.monotonic() - start) * 1000
                writer.writerow([str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(),
                                 1, int(success), f"{duration:.3f}"])
                handle.flush()
        print(output)
        print("Synthetic samples recorded; completeness and production coverage are not inferred.")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Probe refused/failed: {exc}\n")


if __name__ == "__main__":
    main()
