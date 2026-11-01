#!/usr/bin/env python3
"""V08 identity-gated READ-ONLY PostgreSQL staging diagnostic launcher.

Requires psql in PATH, approved non-production target, explicit version/role
identity, protected password file, allowlist and private local evidence folder.
No DB writes, restore/failover, cloud API, network telemetry upload or approval.
Does NOT certify runtime recovery or HA. Python 3.10+ standard library.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone

def fail(message):
    raise RuntimeError("V08 BLOCKED: " + message)

def required(name):
    value = os.environ.get(name, "")
    if not value:
        fail("missing required environment variable " + name)
    return value

def restricted_file(path_string, max_mode=0o600):
    file_path = Path(path_string)
    if file_path.is_symlink() or not file_path.is_file():
        fail("required private regular file missing")
    perms = stat.S_IMODE(file_path.stat().st_mode)
    if perms & 0o077:
        fail("private file is accessible to group/others (chmod 600)")
    return file_path

def main():
    if os.environ.get("V08_EXECUTION_APPROVED") != "YES":
        fail("explicit V08_EXECUTION_APPROVED=YES required after change approval")
    ticket = required("V08_CHANGE_TICKET")
    if not ticket.startswith("https://"):
        fail("HTTPS change approval link required")
    allowlist = restricted_file(required("V08_ALLOWLIST_FILE"))
    expected_db = required("V08_EXPECT_DATABASE")
    expected_role = required("V08_EXPECT_ROLE")
    expected_version = required("V08_EXPECT_SERVER_VERSION_NUM")
    expected_standby = required("V08_EXPECT_IS_STANDBY")
    if not re.fullmatch(r"[0-9]{5,6}", expected_version):
        fail("exact server_version_num integer required")
    if expected_standby not in ("t", "f"):
        fail("expected recovery state must be t or f")
    host = required("PGHOST")
    port = required("PGPORT")
    db = required("PGDATABASE")
    user = required("PGUSER")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        fail("invalid PostgreSQL port")
    if db != expected_db or user != expected_role:
        fail("requested database or role does not match reviewed expectations")
    if (host + "|" + port + "|" + db) not in allowlist.read_text(encoding="utf-8").splitlines():
        fail("target tuple not in approved allowlist")
    mode = required("PGSSLMODE")
    local_lab = (host == "127.0.0.1" and db == "ops_lab"
                 and port in ("55432", "55433", "55434")
                 and os.environ.get("V08_LOCAL_CH004_LAB_ONLY") == "YES"
                 and mode == "disable")
    if not local_lab and mode != "verify-full":
        fail("TLS verify-full is mandatory except explicit Chapter 004 loopback lab")
    if mode == "verify-full":
        if not Path(required("PGSSLROOTCERT")).is_file():
            fail("trusted CA certificate not found")
    if "PGPASSWORD" in os.environ:
        fail("do not use environment variable PGPASSWORD; use protected PGPASSFILE")
    restricted_file(required("PGPASSFILE"))
    evidence_dir = Path(required("V08_EVIDENCE_DIR"))
    if evidence_dir.is_symlink() or not evidence_dir.is_dir():
        fail("private evidence directory must exist and not be symlink")
    if stat.S_IMODE(evidence_dir.stat().st_mode) & 0o077:
        fail("evidence directory too accessible (chmod 700)")
    psql = shutil.which("psql")
    if not psql:
        fail("psql is not installed")
    environment = dict(os.environ)
    environment["PGCONNECT_TIMEOUT"] = "5"
    environment["PGOPTIONS"] = "-c default_transaction_read_only=on -c statement_timeout=5000"
    identity_cmd = [psql, "-X", "-A", "-t", "-F", "|",
                    "-v", "ON_ERROR_STOP=1",
                    "-c", "SELECT current_database(),current_user,"
                          "current_setting('server_version_num'),pg_is_in_recovery();"]
    try:
        identity = subprocess.run(identity_cmd, capture_output=True, text=True,
                                  env=environment, timeout=20, check=True)
    except (subprocess.SubprocessError, OSError):
        fail("identity query failed; sensitive connection details suppressed")
    fields = identity.stdout.strip().split("|")
    if fields != [expected_db, expected_role, expected_version, expected_standby]:
        fail("actual PostgreSQL identity/role/version/standby does not match approved target")
    sql_file = Path(__file__).with_name("V08-readonly-staging-preflight.sql")
    if not sql_file.is_file():
        fail("matching SQL preflight missing")
    command = [psql, "-X", "-v", "ON_ERROR_STOP=1", "-f", str(sql_file)]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                env=environment, timeout=90, check=True)
    except (subprocess.SubprocessError, OSError):
        fail("read-only preflight failed; inspect authorized PostgreSQL monitoring securely")
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = evidence_dir / ("V08-readonly-" + now + "-" + str(os.getpid()) + ".txt")
    with out.open("x", encoding="utf-8") as stream:
        stream.write(result.stdout)
    out.chmod(0o600)
    print("Read-only PostgreSQL staging preflight executed; private evidence:", out)
    print("SHA-256:", hashlib.sha256(out.read_bytes()).hexdigest())
    print("This is NOT a PITR result, HA fencing proof, RPO/RTO acceptance or certification.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
