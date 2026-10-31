#!/usr/bin/env python3
"""Actual pg_rewind against ONLY the stopped old primary of a new Chapter 004 PG18 lab.

Not an operational failover tool. Source and target are hard-coded to an owned,
fresh, three-node, loopback-only topology inside the network-disabled CI image.
No caller-supplied target path, source host, SQL or pg_rewind arguments.
The original stopped primary is backed up before pg_rewind. On any failure,
do not start the target: preserve it for inspection / rebuild instead.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

import v03_negative_path as shared

TOKEN = "REWIND-OWNED-FRESH-CH004-ONLY"
ROOT = None
steps = []


def stop(message: str):
    raise RuntimeError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def record(name: str, detail: str):
    steps.append({"utc": utc(), "gate": name, "result": detail})
    print(f"PASS {name}: {detail}", flush=True)


def command(argv, *, timeout=90, expect=True, env=None):
    result = subprocess.run([str(v) for v in argv], capture_output=True,
                            text=True, env=env or os.environ.copy(),
                            check=False, timeout=timeout)
    if expect and result.returncode != 0:
        stop(f"{Path(str(argv[0])).name} failed with code {result.returncode}: "
             + (result.stderr + result.stdout)[-700:])
    return result


def query(port: int, sql: str):
    got = shared.psql(port=port, statement=sql)
    if got.returncode:
        stop(f"Read-only probe failed at port {port}: {got.stderr[-400:]}")
    return got.stdout.strip()


def ctl(datadir: Path, mode: str):
    cmd = ["pg_ctl", "-D", str(datadir)]
    if mode == "stop":
        cmd += ["-m", "fast", "-w", "-t", "30", "stop"]
    elif mode == "promote":
        cmd += ["-w", "-t", "30", "promote"]
    elif mode == "start":
        cmd += ["-l", str(ROOT / "logs" / "rewound-primary.log"),
                "-w", "-t", "30", "start"]
    else:
        stop("Refused unsupported pg_ctl action")
    return command(cmd, timeout=65)


def stopped(datadir: Path):
    return command(["pg_ctl", "-D", str(datadir), "status"],
                   expect=False).returncode != 0


def closed(port: int):
    import socket
    with socket.socket() as s:
        s.settimeout(.8)
        return s.connect_ex(("127.0.0.1", port)) != 0


def check_owned_clean_dir(datadir: Path):
    assert ROOT is not None
    if not datadir.is_dir() or datadir.is_symlink():
        stop("Stopped target must be an existing ordinary PGDATA directory")
    if datadir.parent != ROOT or datadir.name != "primary":
        stop("Refused target PGDATA outside exact Chapter 004 primary")
    if datadir.stat().st_uid != os.geteuid():
        stop("PGDATA ownership mismatch")
    if (datadir / "PG_VERSION").read_text().strip() != "18":
        stop("Only PostgreSQL 18 targets accepted")
    if not stopped(datadir) or not closed(55432):
        stop("Old writer is still running or accepting connections: do not rewind")
    for p in datadir.rglob("*"):
        if p.is_symlink():
            stop("Refused unexpected PGDATA symlink or tablespace mapping")
    # pg_rewind must never trigger automatic single-user crash recovery on a
    # target that was not cleanly shut down.
    info = command(["pg_controldata", "-D", str(datadir)]).stdout
    if not re.search(r"Database cluster state:\s+shut down\s*$", info, re.M):
        stop("Target control state is not clean shutdown")
    if not re.search(r"Data page checksum version:\s+[1-9]\d*\s*$", info, re.M):
        stop("Checksums not enabled on the exact target")
    record("old_primary_fence", "clean shutdown, no TCP writer, exact PG18 PGDATA and checksums")


def wait_for_marker(port: int, marker: str, *, attempts=35):
    for _ in range(attempts):
        try:
            observed = query(port, "SELECT payload FROM public.lab_probe WHERE id=491")
        except RuntimeError:
            observed = ""
        if observed == marker:
            return
        time.sleep(1)
    stop(f"Replayed fixture is not visible on {port}")


def passfile_for_new_primary() -> Path:
    path = ROOT / "credentials.pgpass"
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        stop("Missing or unsafe isolated lab credential file")
    rows = path.read_text(encoding="utf-8").splitlines()
    matches = [r for r in rows if r.startswith("127.0.0.1:55432:replication:lab_repl:")]
    if len(matches) != 1:
        stop("Exactly one known lab replication credential required")
    target = ROOT / "actual-rewind.pgpass"
    if target.exists() or target.is_symlink():
        stop("Preexisting passfile: expected a fresh lab")
    target.write_text("\n".join(rows +
                    [matches[0].replace(":55432:", ":55433:", 1)]) + "\n",
                      encoding="utf-8")
    target.chmod(0o600)
    return target


def main():
    global ROOT
    if os.geteuid() == 0:
        stop("Refuse root execution")
    if os.environ.get("PG_V03_REWIND_CONFIRM") != TOKEN:
        stop("Explicit actual-rewind-in-disposable-lab token absent")
    if os.environ.get("PG_V03_CONFIRM_ISOLATED") != shared.CONFIRM:
        stop("Chapter 004 isolation token absent")
    if os.environ.get("PG_V03_HA_CONFIRM") != "FENCE-AND-PROMOTE-NEW-LAB":
        stop("Controlled switchover token absent")
    system_id = shared.preflight()
    ROOT = shared.lab_root
    target = ROOT / "primary"
    candidate = ROOT / "standby1"
    unused = ROOT / "standby2"
    backup = ROOT / "original-before-actual-rewind"
    if backup.exists() or backup.is_symlink():
        stop("Refused existing old-primary safety backup")
    if (ROOT / "actual-rewind.pgpass").exists():
        stop("Refused existing rewind credential file")
    if any(x.is_symlink() for x in (target,candidate,unused)):
        stop("Refused symlinked lab instance")
    if query(55432, "SELECT count(*) FROM public.lab_probe WHERE id=491") != "0":
        stop("Test marker already exists")
    for port in (55432,55433,55434):
        expected = "f" if port == 55432 else "t"
        if query(port,"SELECT pg_is_in_recovery()") != expected:
            stop("Unexpected roles before initiating isolated test")
        if query(port,"SELECT system_identifier::text FROM pg_control_system()") != system_id:
            stop("Mismatched system IDs before test")
    record("preflight", "fresh 3-node PG18 cluster; matching identity, ports, roles and markers")

    token = "rewind-" + secrets.token_hex(8)
    insert=shared.psql(statement=f"INSERT INTO public.lab_probe(id,payload) VALUES (491,'{token}')")
    if insert.returncode:
        stop("Pre-fence acknowledged marker insert failed")
    wait_for_marker(55433,token)
    wait_for_marker(55434,token)
    original_timeline = query(55432, "SELECT left(pg_walfile_name(pg_current_wal_lsn()),8)")
    record("candidate_freshness","marker acknowledged and replayed on both standbys")

    # Only the freshly created CI lab is stopped; old PGDATA is never deleted.
    ctl(target,"stop")
    ctl(unused,"stop")
    check_owned_clean_dir(target)
    if not stopped(unused):
        stop("Unused standby not stopped")
    ctl(candidate,"promote")
    if query(55433, "SELECT pg_is_in_recovery()") != "f":
        stop("Candidate did not become the writable primary")
    new_timeline = query(55433,"SELECT left(pg_walfile_name(pg_current_wal_lsn()),8)")
    if original_timeline == new_timeline:
        stop("No timeline change after promotion")
    wait_for_marker(55433, token)
    if not stopped(target) or not closed(55432):
        stop("Old primary reachable after promotion: split-writer refusal")
    record("promotion", f"old node fenced; new primary=55433; timeline {original_timeline}->{new_timeline}")

    # Create a new write on the promoted timeline to prove data alignment
    # after rewinding, without generating user-like data.
    after = token + "-after-promotion"
    promoted = shared.psql(port=55433,statement=
        f"UPDATE public.lab_probe SET payload='{after}' WHERE id=491")
    if promoted.returncode or query(55433,
                                    "SELECT payload FROM public.lab_probe WHERE id=491") != after:
        stop("Promoted timeline synthetic update failed")
    record("divergence", "new primary acknowledged new-timeline marker, old target remains down")

    # Backup BEFORE the first mutating pg_rewind call, preserving original state.
    check_owned_clean_dir(target)
    shutil.copytree(target, backup, symlinks=False)
    if not (backup/"PG_VERSION").is_file() or not (backup/"global"/"pg_control").is_file():
        stop("Preserved pre-rewind PGDATA is incomplete")
    record("target_backup", "owned old PGDATA copied to separate backup directory")

    # Dry-run and REAL rewind target are fixed to exactly the verified OLD PGDATA;
    # '--no-ensure-shutdown' prevents automatic single-user crash recovery.
    conn="host=127.0.0.1 port=55433 user=lab_admin dbname=postgres sslmode=disable"
    args=["pg_rewind", "--target-pgdata", str(target),
          "--source-server", conn, "--no-ensure-shutdown"]
    command(args+["--dry-run"],timeout=70)
    record("rewind_preflight", "pg_rewind --dry-run passed on exact clean old primary")
    check_owned_clean_dir(target)
    command(args+["--progress"],timeout=120)
    record("actual_rewind", "pg_rewind changed only old stopped disposable PGDATA; backup retained")

    # Never start the rewound target as a writable server. Source config can be
    # copied by pg_rewind, so explicitly create standby.signal and OVERRIDE
    # any old primary_conninfo and port. Do not store passwords in PGDATA.
    passfile=passfile_for_new_primary()
    (target/"standby.signal").touch(exist_ok=True,mode=0o600)
    with (target/"postgresql.conf").open("a",encoding="utf-8") as f:
        f.write("\n# Rewound former primary must start only as a standby\n"
                "port = 55432\nlisten_addresses = '127.0.0.1'\n")
    with (target/"postgresql.auto.conf").open("a",encoding="utf-8") as f:
        f.write("\n# V03 force correct source/role after rewind\n"
                "primary_conninfo = 'host=127.0.0.1 port=55433 user=lab_repl "
                f"passfile={passfile} application_name=rewound_old_primary sslmode=disable'\n")
    if not (target/"standby.signal").is_file():
        stop("Rewound target missing standby.signal: start forbidden")
    cfg=(target/"postgresql.auto.conf").read_text(encoding="utf-8")
    if "port=55433 user=lab_repl" not in cfg or str(passfile) not in cfg:
        stop("Rewound target missing validated standby source")
    if not stopped(target) or not closed(55432):
        stop("Rewound PGDATA not fenced immediately before startup")

    ctl(target,"start")
    if query(55432,"SELECT pg_is_in_recovery()") != "t":
        stop("Safety violation: rewound target started as a writer")
    wait_for_marker(55432, after)
    if query(55433,"SELECT pg_is_in_recovery()")!="f":
        stop("Promotion source lost writable role")
    if query(55432,"SELECT system_identifier::text FROM pg_control_system()") != system_id:
        stop("Rewound replica cluster identifier mismatch")
    if query(55432,"SELECT payload FROM public.lab_probe WHERE id=491") != after:
        stop("Rewound follower did not replay promoted timeline marker")
    record("actual_rejoin",
           "former-primary PGDATA rewound in place; started in recovery and replayed new-timeline marker")
    record("single_writer", "55433 writable; rewound 55432 is a streaming read-only standby")
    print(json.dumps({"status":"PASS_ISOLATED_ACTUAL_REWIND",
                      "original_timeline":original_timeline,
                      "promoted_timeline":new_timeline,
                      "former_primary_reused":True,
                      "old_pgdata_backup_retained":True,
                      "production_fencing":"NOT_PROVEN",
                      "application_cutover":"NOT_EXECUTED",
                      "business_rpo_rto":"NOT_CERTIFIED",
                      "gates":steps},indent=2),flush=True)


if __name__=="__main__":
    try:
        main()
    except (RuntimeError,OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print(f"V03 ACTUAL REWIND FAIL: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)
    finally:
        # Stop fixed lab nodes if they are running; do NOT remove or overwrite
        # old PGDATA or preserved pre-rewind backup.
        folder=globals().get("ROOT")
        if isinstance(folder,Path) and folder.is_dir():
            for name in ("primary","standby1","standby2"):
                node=folder/name
                if node.is_dir():
                    try:
                        if not stopped(node):
                            ctl(node,"stop")
                    except Exception as e:
                        print(f"Manual stop review for {name}: {e}",file=sys.stderr,flush=True)
