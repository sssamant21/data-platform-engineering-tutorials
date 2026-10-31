#!/usr/bin/env python3
"""Run fail-closed PostgreSQL 18 stage/cleanup tests on a NEW Chapter 004 lab.

This script deliberately creates and deletes synthetic Chapter 047/048 fixtures.
It never runs without both an exact Chapter 004 identity preflight and
PG_V03_CONFIRM_ISOLATED=047-048-DISPOSABLE-ONLY.
There is no production/shared-host override.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "labs" / "sql"
MARKER = "postgresql18-dbre-sre-disposable"
CONFIRM = "047-048-DISPOSABLE-ONLY"
results: list[dict[str, object]] = []
lab_root: Path


def stop(message: str) -> None:
    raise RuntimeError(message)


def psql(port=55432, user="lab_admin", db="ops_lab", statement=None, script=None, vars=None):
    args = ["psql", "-X", "-q", "-A", "-t", "-w", "-v", "ON_ERROR_STOP=1",
            "-h", "127.0.0.1", "-p", str(port), "-U", user, "-d", db]
    for key, value in (vars or {}).items():
        args.extend(["-v", f"{key}={value}"])
    if statement is not None:
        args.extend(["-c", statement])
    else:
        args.extend(["-f", str(SQL / script)])
    return subprocess.run(args, capture_output=True, text=True, timeout=40,
                          env=os.environ.copy(), check=False)


def query(statement: str, port=55432):
    result = psql(port=port, statement=statement)
    if result.returncode != 0:
        stop(f"Read-only query failed at port {port}: {result.stderr[-500:]}")
    return result.stdout.strip()


def fingerprint():
    """Capture exact lab fixture identities and row data, not just error text."""
    slot = query("""SELECT coalesce(string_agg(slot_name||':'||slot_type||':'||active::text, ','
                  ORDER BY slot_name),'none') FROM pg_replication_slots
                  WHERE slot_name='ch047_lab_physical'""")
    schemas = query("""SELECT coalesce(string_agg(nspname,',' ORDER BY nspname),'none')
                       FROM pg_namespace WHERE nspname IN ('ch047','ch048')""")
    rows = {}
    for schema, table in (("ch047", "wal_fixture"), ("ch048", "events")):
        present = query(f"SELECT to_regclass('{schema}.{table}') IS NOT NULL")
        if present == "t":
            rows[schema] = query(
                f"SELECT count(*)||':'||md5(coalesce(string_agg("
                f"id::text||':'||payload, ',' ORDER BY id),'')) "
                f"FROM {schema}.{table}"
            )
        else:
            rows[schema] = "absent"
    return {"slot": slot, "schemas": schemas, "rows": rows}


def run_case(label, script, vars, *, success=False, port=55432,
             user="lab_admin", db="ops_lab", refusal_marker=True):
    before = fingerprint()
    done = psql(port=port, user=user, db=db, script=script, vars=vars)
    combined = done.stdout + "\n" + done.stderr
    if success:
        if done.returncode != 0:
            stop(f"{label}: positive case failed (exit {done.returncode}): {combined[-700:]}")
    else:
        if done.returncode == 0:
            stop(f"{label}: unsafe success, expected refusal")
        if refusal_marker and "REFUSED:" not in combined:
            stop(f"{label}: failure did not emit explicit refusal: {combined[-700:]}")
        after = fingerprint()
        if after != before:
            stop(f"{label}: a rejected operation changed fixture state: {before} => {after}")
    results.append({"case": label, "outcome": "positive-pass" if success else "refused-unchanged",
                    "exit_code": done.returncode})
    print(f"PASS {label}: {'approved disposable fixture' if success else 'rejected without fixture changes'}", flush=True)


def preflight():
    global lab_root
    if os.environ.get("PG_V03_CONFIRM_ISOLATED") != CONFIRM:
        stop("Explicit PG_V03_CONFIRM_ISOLATED confirmation is required")
    if os.geteuid() == 0:
        stop("Never run this lab as root")
    value = os.environ.get("PG_LAB_ROOT", "")
    if not re.fullmatch(r"/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+", value):
        stop("PG_LAB_ROOT does not match a Chapter 004 disposable root")
    lab_root = Path(value)
    if lab_root.is_symlink() or not lab_root.is_dir() or lab_root.stat().st_uid != os.geteuid():
        stop("Lab root must be a real owned directory")
    if (lab_root / "LAB_MARKER").read_text().strip() != MARKER:
        stop("Lab marker mismatch")
    passfile = lab_root / "credentials.pgpass"
    if os.environ.get("PGPASSFILE") != str(passfile) or passfile.is_symlink():
        stop("Expected isolated Chapter 004 PGPASSFILE")
    if passfile.stat().st_mode & 0o077:
        stop("Credential file permissions are too broad")
    expected = str(lab_root / "primary")
    identity = query("""SELECT current_database()||'|'||current_user||'|'||
                        current_setting('data_directory')||'|'||
                        host(inet_server_addr())||'|'||inet_server_port()::text||'|'||
                        pg_is_in_recovery()::text||'|'||
                        current_setting('server_version_num')""").split("|")
    if identity != ["ops_lab", "lab_admin", expected, "127.0.0.1",
                    "55432", "false", "180000"]:
        # PostgreSQL 18 minor versions encode 180001 etc.; check major separately.
        if len(identity) != 7 or identity[:6] != ["ops_lab", "lab_admin", expected,
                                                   "127.0.0.1", "55432", "false"] or not (
                180000 <= int(identity[6]) < 190000):
            stop(f"Incorrect primary role, PGDATA, port or PostgreSQL major: {identity}")
    for port, recovering in ((55432, "f"), (55433, "t"), (55434, "t")):
        role = query("SELECT pg_is_in_recovery()", port=port)
        slots = query("SHOW max_replication_slots", port=port)
        size = query("SELECT setting FROM pg_settings WHERE name='max_slot_wal_keep_size' AND unit='MB'",
                     port=port)
        if (role, slots, size) != (recovering, "4", "256"):
            stop(f"Unexpected topology/config at {port}: {(role, slots, size)}")
    if fingerprint() != {"slot": "none", "schemas": "none",
                         "rows": {"ch047": "absent", "ch048": "absent"}}:
        stop("Existing Chapter 047/048 objects: refusing to mutate or clean up")
    system_id = query("SELECT system_identifier::text FROM pg_control_system()")
    if not re.fullmatch(r"\d{8,25}", system_id):
        stop("Could not verify exact PostgreSQL cluster system identifier")
    print("PASS preflight: fresh, isolated, owned PostgreSQL 18 Chapter 004 topology", flush=True)
    return system_id


def main():
    system_id = preflight()
    correct = {"expected_system_id": system_id}
    wrong = {"expected_system_id": "0"}
    # All negative tests must fail before the first valid fixture is created.
    run_case("047 missing token", "047-create-lab-slot.sql", correct)
    run_case("047 wrong system ID", "047-create-lab-slot.sql",
             {**wrong, "confirm_stage": "047-CREATE-SLOT"})
    run_case("047 wrong stage token", "047-create-lab-slot.sql",
             {**correct, "confirm_stage": "048-WORKLOAD"})
    run_case("047 wrong target database", "047-create-lab-slot.sql",
             {**correct, "confirm_stage": "047-CREATE-SLOT"}, db="postgres")
    run_case("047 standby target", "047-create-lab-slot.sql",
             {**correct, "confirm_stage": "047-CREATE-SLOT"}, port=55433)
    run_case("047 wrong role", "047-create-lab-slot.sql",
             {**correct, "confirm_stage": "047-CREATE-SLOT"},
             user="lab_observer", refusal_marker=False)
    run_case("048 wrong system ID", "048-workload.sql",
             {**wrong, "confirm_stage": "048-WORKLOAD"})
    run_case("048 wrong token", "048-workload.sql",
             {**correct, "confirm_stage": "047-GENERATE-WAL"})
    run_case("048 standby target", "048-workload.sql",
             {**correct, "confirm_stage": "048-WORKLOAD"}, port=55433)

    # Only the preflighted disposable lab is ever modified.
    run_case("047 slot creation", "047-create-lab-slot.sql",
             {**correct, "confirm_stage": "047-CREATE-SLOT"}, success=True)
    run_case("047 duplicate slot", "047-create-lab-slot.sql",
             {**correct, "confirm_stage": "047-CREATE-SLOT"})
    run_case("047 WAL wrong token", "047-generate-wal.sql",
             {**correct, "confirm_stage": "047-CREATE-SLOT"})
    run_case("047 WAL fixture", "047-generate-wal.sql",
             {**correct, "confirm_stage": "047-GENERATE-WAL"}, success=True)
    run_case("047 repeated fixture", "047-generate-wal.sql",
             {**correct, "confirm_stage": "047-GENERATE-WAL"})
    for label, args in (
        ("047 cleanup wrong ID", {"expected_db": "ops_lab", **wrong,
                                  "confirm_cleanup": "047-DROP"}),
        ("047 cleanup wrong token", {"expected_db": "ops_lab", **correct,
                                     "confirm_cleanup": "048-DROP"}),
        ("047 cleanup wrong DB", {"expected_db": "postgres", **correct,
                                  "confirm_cleanup": "047-DROP"}),
    ):
        run_case(label, "047-cleanup.sql", args)
    run_case("047 approved cleanup", "047-cleanup.sql",
             {"expected_db": "ops_lab", **correct, "confirm_cleanup": "047-DROP"}, success=True)

    run_case("048 bounded workload", "048-workload.sql",
             {**correct, "confirm_stage": "048-WORKLOAD"}, success=True)
    run_case("048 repeated workload", "048-workload.sql",
             {**correct, "confirm_stage": "048-WORKLOAD"})
    run_case("048 cleanup wrong ID", "048-cleanup.sql",
             {"expected_db": "ops_lab", **wrong, "confirm_cleanup": "048-DROP"})
    run_case("048 cleanup wrong token", "048-cleanup.sql",
             {"expected_db": "ops_lab", **correct, "confirm_cleanup": "047-DROP"})
    run_case("048 approved cleanup", "048-cleanup.sql",
             {"expected_db": "ops_lab", **correct, "confirm_cleanup": "048-DROP"}, success=True)
    if fingerprint() != {"slot": "none", "schemas": "none",
                         "rows": {"ch047": "absent", "ch048": "absent"}}:
        stop("Post-cleanup fixture state differs from clean baseline")
    print(json.dumps({"status": "PASS", "environment": "isolated Chapter 004 PG18",
                      "tests": results, "live_pitr_fencing_rewind": "NOT_EXECUTED"},
                     indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"V03 NEGATIVE-PATH FAIL: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
