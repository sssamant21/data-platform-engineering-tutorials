#!/usr/bin/env python3
"""PostgreSQL 18 Chapter 045 PITR on an isolated ephemeral loopback cluster.

Reuses the chapter's guarded fixture/good-marker/incident/verify SQL.
Restores into a SEPARATE new PGDATA via the archive and named restore point.
No routing, promotion, production access, or filesystem deletion.
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

REPO = Path(__file__).resolve().parents[1]
SQL = REPO / "labs" / "sql"
CONFIRM = "NEW-ISOLATED-CH045-PITR"
root: Path
events: list[dict[str, object]] = []


def stamp():
    return datetime.now(timezone.utc).isoformat()


def evidence(gate: str, value: str):
    events.append({"utc": stamp(), "gate": gate, "observed": value})
    print(f"PASS {gate}: {value}", flush=True)


def reject(reason: str):
    raise RuntimeError(reason)


def command(args, *, env=None, timeout=90, good=True):
    result = subprocess.run([str(v) for v in args], env=env or os.environ.copy(),
                            text=True, capture_output=True, timeout=timeout, check=False)
    if good and result.returncode != 0:
        reject(f"{args[0]} exit={result.returncode}: " + (result.stderr+result.stdout)[-700:])
    return result


def sql(port, *, statement=None, script=None, variables=None, env=None, good=True):
    args = ["psql", "-X", "-w", "-A", "-t", "-v", "ON_ERROR_STOP=1",
            "-h", "127.0.0.1", "-p", str(port), "-U", "lab_admin", "-d", "postgres"]
    for key, value in (variables or {}).items():
        args += ["-v", f"{key}={value}"]
    if statement:
        args += ["-c", statement]
    elif script:
        args += ["-f", str(SQL / script)]
    else:
        reject("Missing SQL operation")
    return command(args, env=env, timeout=30, good=good)


def read(port, statement, env=None):
    return sql(port, statement=statement, env=env).stdout.strip()


def pg_ctl(data: Path, mode, *, env=None):
    if mode=="start":
        args=["pg_ctl","-D",str(data),"-l",str(root/"logs"/(data.name+".log")),
              "-w","-t","60","start"]
    else:
        args=["pg_ctl","-D",str(data),"-m","fast","-w","-t","30","stop"]
    return command(args, env=env, timeout=70)


def pids_stopped(data: Path):
    return command(["pg_ctl","-D",str(data),"status"],good=False).returncode != 0


def main():
    global root
    if os.geteuid()==0 or os.environ.get("PG_V03_PITR_CONFIRM")!=CONFIRM:
        reject("Requires non-root and explicit isolated Chapter 045 PITR approval")
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="postgresql-v03-pitr.",dir="/tmp"))
    if not re.fullmatch(r"/tmp/postgresql-v03-pitr\.[A-Za-z0-9_-]+",str(root)):
        reject("Unexpected PITR root")
    root.chmod(0o700)
    for name in ("logs","archive","sock"):
        (root/name).mkdir(mode=0o700)
    source = root/"source"
    backup = root/"basebackup"
    recovered = root/"recovered"
    passwd = secrets.token_hex(24)
    pwfile = root/"initdb-password"
    pwfile.write_text(passwd+"\n")
    pwfile.chmod(0o600)
    passfile = root/"lab.pgpass"
    passfile.write_text(f"127.0.0.1:55445:*:lab_admin:{passwd}\n"
                        f"127.0.0.1:55445:replication:lab_admin:{passwd}\n"
                        f"127.0.0.1:55446:*:lab_admin:{passwd}\n")
    passfile.chmod(0o600)
    env={**os.environ,"PGPASSFILE":str(passfile),"PGSSLMODE":"disable",
         "PGCONNECT_TIMEOUT":"5"}
    command(["initdb","-D",source,"-U","lab_admin","--pwfile",pwfile,
             "--auth-local=scram-sha-256","--auth-host=scram-sha-256",
             "--encoding=UTF8","--locale=C","--data-checksums"],env=env)
    pwfile.unlink()
    with (source/"postgresql.conf").open("a",encoding="utf-8") as f:
        f.write(f"\nlisten_addresses = '127.0.0.1'\nport = 55445\n"
                f"unix_socket_directories = '{root / 'sock'}'\n"
                "max_wal_senders = 4\nwal_level = replica\narchive_mode = on\n"
                "archive_timeout = '2s'\n"
                f"archive_command = 'test ! -f {root}/archive/%f && cp %p {root}/archive/%f'\n")
    with (source/"pg_hba.conf").open("a",encoding="utf-8") as f:
        f.write("\nhost replication lab_admin 127.0.0.1/32 scram-sha-256\n")
    pg_ctl(source,"start",env=env)
    identity=read(55445,"SELECT current_database()||'|'||current_user||'|'||"
                  "current_setting('data_directory')||'|'||"
                  "pg_is_in_recovery()::text||'|'||current_setting('server_version_num')",env)
    fields=identity.split("|")
    if len(fields)!=5 or fields[:4]!=["postgres","lab_admin",str(source),"false"] or not (
        180000 <= int(fields[4]) < 190000):
        reject("Wrong source identity; fixture and bad update refused")
    system_id=read(55445,"SELECT system_identifier::text FROM pg_control_system()",env)
    evidence("source_preflight","owned isolated PG18 primary, exact PGDATA and system ID")

    basevars={"expected_data_directory":str(source),"expected_operator":"lab_admin",
              "expected_system_id":system_id}
    sql(55445,script="045-fixture.sql",
        variables={**basevars,"confirm_stage":"045-CREATE-FIXTURE"},env=env)
    if read(55445,"SELECT count(*) FROM ch045.orders",env)!="1000":
        reject("Source fixture mismatch")

    command(["pg_basebackup","-h","127.0.0.1","-p","55445","-U","lab_admin",
             "-D",backup,"-Fp","-Xs","-w"],env=env,timeout=100)
    command(["pg_verifybackup",backup],env=env,timeout=90)
    if not (backup/"backup_manifest").is_file():
        reject("Verified backup missing manifest")
    evidence("physical_backup","pg_basebackup and pg_verifybackup completed")

    sql(55445,script="045-good-marker.sql",
        variables={**basevars,"confirm_stage":"045-GOOD-MARKER"},env=env)
    good_lsn=read(55445,"SELECT pg_current_wal_lsn()",env)
    # Named restore point is logged AFTER the committed marker, BEFORE the incident.
    sql(55445,statement="SELECT pg_create_restore_point('v03-045-good')",env=env)
    pitr_target="v03-045-good"
    incident_started=time.monotonic()
    sql(55445,script="045-incident.sql",
        variables={"expected_db":"postgres","expected_system_id":system_id,
                   "expected_source_data_directory":str(source),
                   "expected_operator":"lab_admin","confirm_incident":"045-INCIDENT"},env=env)
    if read(55445,"SELECT count(*) FROM ch045.orders WHERE status='corrupted'",env)!="100":
        reject("Deliberate source incident did not affect expected lab rows")
    wal_to_archive=read(55445,"SELECT pg_walfile_name(pg_switch_wal())",env)
    evidence("source_incident","100 synthetic bad rows on isolated source, good marker previously committed")

    # The switch closes the WAL segment containing the good marker + incident;
    # the archived segment must be present before recovery starts.
    archived=False
    for _ in range(40):
        if (root/"archive"/wal_to_archive).is_file():
            archived=True
            break
        time.sleep(1)
    if not archived:
        reject(f"Required archive segment did not arrive: {wal_to_archive}")
    evidence("wal_archive","closed WAL segment archived after bad update; source remains isolated")

    # Copy the physical backup only to a NEW recovery directory. Never modify source.
    if recovered.exists():
        reject("Recovery directory unexpectedly exists")
    shutil.copytree(backup,recovered)
    (recovered/"recovery.signal").touch(mode=0o600,exist_ok=False)
    with (recovered/"postgresql.conf").open("a",encoding="utf-8") as f:
        f.write(f"\nport = 55446\n"
                f"restore_command = 'cp {root}/archive/%f %p'\n"
                f"recovery_target_name = '{pitr_target}'\n"
                "recovery_target_action = 'pause'\n"
                "recovery_target_inclusive = on\n")
    pg_ctl(recovered,"start",env=env)
    paused=False
    for _ in range(35):
        try:
            paused=read(55446,"SELECT pg_is_wal_replay_paused()",env)=="t"
        except RuntimeError:
            paused=False
        if paused:
            break
        time.sleep(1)
    if not paused:
        reject("Recovered instance did not pause at named WAL restore point")
    if read(55446,"SELECT pg_is_in_recovery()",env)!="t":
        reject("Recovered instance is not safely in recovery")
    if read(55446,"SELECT system_identifier::text FROM pg_control_system()",env)!=system_id:
        reject("Recovered cluster identity mismatch")
    verdict=sql(55446,script="045-verify.sql",
                variables={"expected_recovery_data_directory":str(recovered),
                           "expected_system_id":system_id,
                           "confirm_recovery":"045-VERIFY-RECOVERY"},env=env)
    if "PASS: isolated PITR fixture marker/rows validated" not in verdict.stdout:
        reject("Chapter 045 recovery acceptance marker missing")
    wrong=sql(55446,script="045-verify.sql",
              variables={"expected_recovery_data_directory":str(source),
                         "expected_system_id":system_id,
                         "confirm_recovery":"045-VERIFY-RECOVERY"},env=env,good=False)
    if wrong.returncode==0:
        reject("Wrong PITR target path exited zero: safety regression")
    ready_seconds=time.monotonic()-incident_started
    evidence("isolated_pitr","named restore point paused; 1000 valid rows, known-good marker, zero bad rows")
    evidence("wrong_recovery_target","wrong PGDATA verification refused with nonzero psql exit")
    evidence("pitr_recovery_duration",f"{ready_seconds:.3f} s incident through verification; lab metric only")
    evidence("pitr_marker_boundary",f"named restore point={pitr_target} after good marker at sampled LSN {good_lsn}")
    print(json.dumps({"status":"PASS_ISOLATED_PITR","chapter":"045",
                      "source_port":55445,"restore_port":55446,
                      "manifest_verified":True,"archive_segment_verified":True,
                      "good_marker_and_rows_verified":True,
                      "bad_rows_excluded":True,
                      "actual_application_cutover":"NOT_EXECUTED",
                      "business_rpo_rto":"NOT_CERTIFIED",
                      "events":events},indent=2),flush=True)


if __name__=="__main__":
    try:
        main()
    except (RuntimeError,OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print(f"V03 PITR FAIL: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)
    finally:
        # Preserve all PGDATA for inspection; no rm -rf or destructive cleanup.
        rr=globals().get("root")
        if isinstance(rr,Path) and rr.is_dir():
            for name in ("recovered","source"):
                datadir=rr/name
                if datadir.is_dir():
                    try:
                        if not pids_stopped(datadir):
                            pg_ctl(datadir,"stop")
                    except Exception as ex:
                        print(f"STOP REVIEW REQUIRED for {name}: {ex}",file=sys.stderr)
