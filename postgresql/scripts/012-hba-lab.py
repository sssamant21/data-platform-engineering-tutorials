#!/usr/bin/env python3
"""Guarded Chapter 004 HBA staging only; never reloads or restarts PostgreSQL."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tempfile

BASELINE = (
    "local all all scram-sha-256\n"
    "host all all 127.0.0.1/32 scram-sha-256\n"
    "host replication lab_repl 127.0.0.1/32 scram-sha-256\n"
).encode()
STATES = {
    "original": BASELINE,
    "reject": b"# Chapter 012: narrow deliberate rejection\n"
              b"hostnossl ops_lab lab_app 127.0.0.1/32 reject\n" + BASELINE,
    "malformed": b"# Chapter 012: deliberately invalid lab-only method\n"
                 b"hostnossl ops_lab lab_app 127.0.0.1/32 not_an_auth_method\n" + BASELINE,
}


def owned(path, directory=False):
    st = path.lstat()
    valid = stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode)
    if not valid or st.st_uid != os.geteuid():
        raise ValueError(f"Expected owned real {'directory' if directory else 'file'}: {path}")
    return st


def current_state(content):
    for name, data in STATES.items():
        if content == data:
            return name
    raise ValueError("HBA differs from known exercise states; refuse to overwrite concurrent edits")


def replace_known(path, content):
    before = path.read_bytes()
    current_state(before)
    st = owned(path)
    fd, temporary = tempfile.mkstemp(prefix=".chapter012-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), stat.S_IMODE(st.st_mode))
            os.fchown(handle.fileno(), -1, st.st_gid)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # Detect an intervening edit before replacing; an exclusive operator is still required.
        owned(path)
        if path.read_bytes() != before:
            raise ValueError("HBA changed during staging")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def private_write(path, content):
    with path.open("xb") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(content)


def guard(root):
    if os.geteuid() == 0:
        raise ValueError("Use the non-root Chapter 004 lab OS account")
    if not re.fullmatch(r"/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+", str(root)):
        raise ValueError("Unexpected disposable lab path")
    owned(root, directory=True)
    owned(root / "LAB_MARKER")
    if (root / "LAB_MARKER").read_text().strip() != "postgresql18-dbre-sre-disposable":
        raise ValueError("Missing or incorrect disposable lab marker")
    primary = root / "primary"
    owned(primary, directory=True)
    owned(primary / "PG_VERSION")
    if (primary / "PG_VERSION").read_text().strip() != "18":
        raise ValueError("Expected PostgreSQL 18 lab data directory")
    hba = primary / "pg_hba.conf"
    owned(hba)
    return hba, root / "evidence-012"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "reject", "malformed", "restore", "status", "clean-secrets"])
    args = parser.parse_args()
    try:
        root = Path(os.environ.get("PG_LAB_ROOT", ""))
        hba, evidence = guard(root)
        state = current_state(hba.read_bytes())
        if args.action == "prepare":
            if state != "original":
                raise ValueError("Prepare requires the exact Chapter 004 HBA baseline")
            credentials = root / "credentials.pgpass"
            st = owned(credentials)
            if stat.S_IMODE(st.st_mode) & 0o077:
                raise ValueError("Lab credential file must be private")
            matches = []
            for line in credentials.read_text().splitlines():
                fields = line.split(":")
                if fields[:4] == ["127.0.0.1", "55432", "*", "lab_app"] and len(fields) == 5:
                    matches.append(fields[4])
            if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{48}", matches[0]):
                raise ValueError("Unexpected Chapter 004 app credential structure")
            evidence.mkdir(mode=0o700)  # refuse an occupied evidence path
            private_write(evidence / "original-pg_hba.conf", BASELINE)
            private_write(evidence / "empty.pgpass", b"")
            private_write(evidence / "wrong.pgpass",
                          f"127.0.0.1:55432:ops_lab:lab_app:{secrets.token_hex(24)}\n".encode())
            private_write(evidence / "socket.pgpass",
                          f"{root / 'socket'}:55432:ops_lab:lab_app:{matches[0]}\n".encode())
            print("Prepared private backup and lab-only credential probes; no HBA change")
            return 0
        owned(evidence, directory=True)
        backup = evidence / "original-pg_hba.conf"
        owned(backup)
        if backup.read_bytes() != BASELINE:
            raise ValueError("Original backup differs from the known baseline")
        if args.action == "status":
            print(f"Disk state={state}; SHA256={hashlib.sha256(hba.read_bytes()).hexdigest()}")
        elif args.action == "clean-secrets":
            if state != "original":
                raise ValueError("Restore the HBA before removing probe credential files")
            for name in ("empty.pgpass", "wrong.pgpass", "socket.pgpass"):
                path = evidence / name
                if path.exists() or path.is_symlink():
                    owned(path)
                    path.unlink()
            print("Probe credential files removed; configuration evidence retained")
        else:
            desired = "original" if args.action == "restore" else args.action
            if desired != "original" and state != "original":
                raise ValueError("Restore between failure experiments")
            replace_known(hba, STATES[desired])
            print(f"Staged disk state={desired}; inspect before reload; no reload performed")
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
