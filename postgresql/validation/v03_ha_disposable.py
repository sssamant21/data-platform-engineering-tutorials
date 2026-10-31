#!/usr/bin/env python3
"""Isolated PostgreSQL 18 controlled-switchover acceptance, never production HA.

Requires a fresh Chapter 004 cluster, two independent environment tokens,
loopback-only endpoints and a network-disabled CI container.
This demonstrates a local planned shutdown fence, NOT independently proven
production fencing or an application failover orchestration system.
Former primary PGDATA is retained; pg_rewind is DRY RUN ONLY.
Rejoin is a new separate pg_basebackup, never in-place deletion/replacement.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

# Existing exact-cluster gates verify role, PG18 version, PGDATA, credentials,
# three loopback nodes, zero pre-existing Chapter 047/048 objects and system ID.
import v03_negative_path as shared

CONFIRM = "FENCE-AND-PROMOTE-NEW-LAB"
events = []
root: Path
rejoin: Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def event(name: str, detail: str) -> None:
    events.append({"at_utc": now(), "gate": name, "observed": detail})
    print(f"PASS {name}: {detail}", flush=True)


def fail(message: str) -> None:
    raise RuntimeError(message)


def run(cmd, *, timeout=75, env=None, expect=True):
    result = subprocess.run([str(v) for v in cmd], text=True, capture_output=True,
                            timeout=timeout, check=False, env=env or os.environ.copy())
    if expect and result.returncode != 0:
        fail(f"{Path(str(cmd[0])).name} exit {result.returncode}: "
             f"{(result.stderr + result.stdout)[-800:]}")
    return result


def sql(command: str, port: int) -> str:
    done = shared.psql(port=port, statement=command)
    if done.returncode != 0:
        fail(f"PostgreSQL port {port} rejected validation: {done.stderr[-350:]}")
    return done.stdout.strip()


def pg_ctl(node: Path, action: str, *, mode=None, timeout=40):
    cmd = ["pg_ctl", "-D", str(node)]
    if action == "stop":
        cmd += ["-m", mode or "fast", "-w", "-t", "30", "stop"]
    elif action == "promote":
        cmd += ["-w", "-t", "30", "promote"]
    elif action == "start":
        cmd += ["-l", str(root / "logs" / "rejoined.log"),
                "-w", "-t", "30", "start"]
    else:
        fail("Unexpected pg_ctl operation")
    return run(cmd, timeout=timeout)


def stopped(node: Path) -> bool:
    return run(["pg_ctl", "-D", str(node), "status"], expect=False).returncode != 0


def socket_closed(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1.0)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def wait_marker(port: int, marker: str, seconds=30):
    for _ in range(seconds):
        if sql("SELECT payload FROM public.lab_probe WHERE id=490", port) == marker:
            return
        time.sleep(1)
    fail(f"Marker not visible at port {port}")


def create_repl_passfile() -> Path:
    source = root / "credentials.pgpass"
    rows = source.read_text(encoding="utf-8").splitlines()
    source_row = [r for r in rows if r.startswith("127.0.0.1:55432:replication:lab_repl:")]
    if len(source_row) != 1:
        fail("Expected exactly one Chapter 004 replication credential")
    # No credentials are printed or included in artifacts.
    target = root / "ha-rejoin.pgpass"
    if target.exists() or target.is_symlink():
        fail("Unexpected existing HA credential file")
    replacement = source_row[0].replace(":55432:", ":55433:", 1)
    target.write_text("\n".join(rows + [replacement]) + "\n", encoding="utf-8")
    target.chmod(0o600)
    return target


def main():
    global root, rejoin
    if os.environ.get("PG_V03_HA_CONFIRM") != CONFIRM:
        fail("Explicit fresh disposable switchover confirmation required")
    if os.environ.get("PG_V03_CONFIRM_ISOLATED") != shared.CONFIRM:
        fail("Chapter 004 isolation token missing")
    system_id = shared.preflight()
    root = shared.lab_root
    rejoin = root / "rejoined-standby"
    if rejoin.exists() or rejoin.is_symlink():
        fail("Rejoin target must not exist before the test")
    for node in ("primary", "standby1", "standby2"):
        if (root / node).is_symlink():
            fail("Unexpected symlink in Chapter 004 node")
    if sql("SELECT count(*) FROM public.lab_probe WHERE id=490", 55432) != "0":
        fail("HA fixture already exists")
    for port in (55432, 55433, 55434):
        role = sql("SELECT pg_is_in_recovery()", port)
        if role != ("f" if port == 55432 else "t"):
            fail(f"Unexpected initial role on {port}")
    observed_id = sql("SELECT system_identifier::text FROM pg_control_system()", 55432)
    if observed_id != system_id:
        fail("Primary cluster ID changed after isolated preflight")
    event("preflight", "fresh Chapter 004 primary+2 standbys, exact owner and identity")

    token = "ha-" + secrets.token_hex(12)
    start_timeline = sql("SELECT left(pg_walfile_name(pg_current_wal_lsn()),8)", 55432)
    write = shared.psql(port=55432, statement=f"INSERT INTO public.lab_probe(id,payload) VALUES (490,'{token}')")
    if write.returncode != 0:
        fail("Synthetic marker insert failed; no promotion")
    acknowledged_at = now()
    wait_marker(55433, token)
    wait_marker(55434, token)
    event("candidate_freshness", "committed marker 490 visible on BOTH standbys before shutdown")

    # Demonstrated local planned shutdown fence only, NOT independent HA-manager fencing.
    fence_t0 = time.monotonic()
    event("simulation_detected", "approved planned stop of isolated A; no unexpected failure induced")
    pg_ctl(root / "primary", "stop")
    pg_ctl(root / "standby2", "stop")  # Exclude unused candidate from the writer set.
    if not (stopped(root / "primary") and stopped(root / "standby2") and socket_closed(55432)):
        fail("Fencing not demonstrated: STOP, no promotion")
    event("lab_fence", "old primary and unused candidate are stopped; old writer port refused TCP")

    # Promotion is permitted only after the above positive local fence evidence.
    pg_ctl(root / "standby1", "promote")
    if sql("SELECT pg_is_in_recovery()", 55433) != "f":
        fail("Candidate is not a writable primary after promotion")
    new_timeline = sql("SELECT left(pg_walfile_name(pg_current_wal_lsn()),8)", 55433)
    if start_timeline == new_timeline:
        fail("Expected a new WAL timeline after promotion")
    if not (stopped(root / "primary") and socket_closed(55432) and stopped(root / "standby2")):
        fail("Old primary became reachable: split-writer stop condition")
    wait_marker(55433, token)
    recovery_t0 = time.monotonic()
    # Simulated application smoke test: only B accepts new writes.
    response = shared.psql(port=55433, statement="SELECT count(*) FROM public.lab_probe WHERE id=490")
    if response.returncode != 0 or response.stdout.strip() != "1":
        fail("Candidate application-read smoke test failed")
    event("promoted_single_writer",
          f"new writer=55433; old=stopped; timeline={start_timeline}->{new_timeline}")
    event("observed_marker_rpo", "zero acknowledged-marker loss in this controlled async switchover")
    event("lab_service_rto", f"{recovery_t0 - fence_t0:.3f} s, local fencing through SQL smoke test")
    print(f"MARKER_ACK_UTC={acknowledged_at}", flush=True)

    # Rewind assess only; never run actual pg_rewind on preserved old PGDATA.
    if not stopped(root / "primary"):
        fail("Cannot inspect rewind while original primary is running")
    rewind = run(["pg_rewind", "--dry-run",
                  "--target-pgdata", str(root / "primary"),
                  "--source-server",
                  "host=127.0.0.1 port=55433 user=lab_admin dbname=postgres sslmode=disable"],
                 timeout=75, expect=False)
    if rewind.returncode != 0:
        fail("Rewind dry-run failed; preserved target unchanged: " + rewind.stderr[-600:])
    event("rewind_dry_run", "pg_rewind --dry-run successful, OLD PGDATA preserved, no actual rewind")

    # Demonstrate safer non-destructive rejoin: separate empty directory, NOT an overwrite
    # of the former primary. This is a rebuild, not a pg_rewind execution.
    passfile = create_repl_passfile()
    env = {**os.environ, "PGPASSFILE": str(passfile)}
    run(["pg_basebackup", "-d",
         f"host=127.0.0.1 port=55433 user=lab_repl passfile={passfile} sslmode=disable",
         "-D", str(rejoin), "-R", "-X", "stream", "--no-slot", "-w"],
        timeout=95, env=env)
    if not (rejoin / "standby.signal").is_file():
        fail("Fresh rebuild missing standby.signal: refuse startup")
    auto = (rejoin / "postgresql.auto.conf").read_text(encoding="utf-8")
    if "primary_conninfo" not in auto or "port=55433" not in auto:
        fail("Fresh rebuild missing explicit promoted-primary connection info")
    with (rejoin / "postgresql.conf").open("a", encoding="utf-8") as f:
        f.write("\n# V03 disposable standby rebuild, not original old primary\nport = 55432\n")
    if not (stopped(root / "primary") and socket_closed(55432)):
        fail("Former-primary process must stay fenced before rebuilt standby start")
    pg_ctl(rejoin, "start")
    if sql("SELECT pg_is_in_recovery()", 55432) != "t":
        fail("Rebuild unexpectedly started as a writer")
    wait_marker(55432, token)
    if sql("SELECT pg_is_in_recovery()", 55433) != "f":
        fail("New primary lost writer role")
    if sql("SELECT system_identifier::text FROM pg_control_system()", 55432) != system_id:
        fail("Rebuilt standby cluster identity mismatch")
    if not stopped(root / "primary"):
        fail("Original primary must remain shut down and preserved")
    event("non_destructive_rebuild",
          "new directory rebuilt as standby on 55432, streaming marker present; old PGDATA preserved")
    event("scope", "NOT certified: independent production fence, actual rewind, PITR and business RPO/RTO")
    print(json.dumps({"status": "PASS_DISPOSABLE_SWITCHOVER",
                      "pg_version": "18", "system_id_verified": True,
                      "events": events, "pitr": "NOT_EXECUTED",
                      "rewind_actual": "NOT_EXECUTED",
                      "production_fencing": "NOT_CERTIFIED"}, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"V03 HA FAIL: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        # Do not leave the added standby active: Chapter 004 destroy knows only its
        # original three node names. CI container is also ephemeral/networkless.
        try:
            rr = globals().get("rejoin")
            if isinstance(rr, Path) and rr.is_dir() and not stopped(rr):
                pg_ctl(rr, "stop")
        except Exception as exc:
            print(f"V03 HA cleanup requires manual review: {exc}", file=sys.stderr)
