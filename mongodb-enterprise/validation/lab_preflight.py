#!/usr/bin/env python3
"""Fail-closed preflight for a disposable MongoDB Chapter 01–04 integration lab.

Requires pymongo, an explicitly allowed URI and a separately approved lab. No writes.
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit

EXPECTED_PREFIX = "mongodb_enterprise_tutorial_ch"
ALLOWED_CHAPTERS = (1, 2, 3, 4)

def validate_inputs(uri, allowed_host, chapter, run_id):
    if chapter not in ALLOWED_CHAPTERS:
        raise ValueError("Only Chapters 01–04 are permitted in the pilot")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", run_id):
        raise ValueError("Run ID must be 8–64 safe characters")
    parts = urlsplit(uri)
    if parts.scheme != "mongodb" or not parts.hostname:
        raise ValueError("Pilot requires a mongodb:// URI with a single explicit host")
    if parts.hostname != allowed_host or "," in parts.netloc:
        raise ValueError("MongoDB endpoint is not the exact allowlisted host")
    if parts.hostname in {"localhost", "127.0.0.1"} and allowed_host not in {"localhost", "127.0.0.1"}:
        raise ValueError("Endpoint mismatch")
    if parts.username or parts.password:
        raise ValueError("Do not put credentials in the pilot URI; use a separately configured auth mechanism")
    if parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Pilot URI must not contain query options, fragment or database path")
    if parts.hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("Remote pilot connections are disabled until TLS/auth and cluster-ID verification are implemented")
    return f"{EXPECTED_PREFIX}{chapter:02d}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--allowed-host", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    uri = os.environ.get("MONGODB_LAB_URI", "")
    if os.environ.get("MONGODB_LAB_APPROVED") != "YES":
        parser.error("Set MONGODB_LAB_APPROVED=YES only after isolated-lab authorization")
    try:
        database = validate_inputs(uri, args.allowed_host, args.chapter, args.run_id)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        from pymongo import MongoClient
    except ImportError:
        parser.error("Install pymongo in the isolated lab environment")
    evidence = {"chapter": args.chapter, "run_id": args.run_id, "database": database,
                "mode": "read_only_preflight", "runtime_certified": False}
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=4000, connectTimeoutMS=4000)
        hello = client.admin.command("hello")
        info = client.admin.command("buildInfo")
        evidence["server_version"] = info.get("version")
        evidence["is_writable_primary"] = bool(hello.get("isWritablePrimary"))
        evidence["topology"] = ("mongos" if hello.get("msg") == "isdbgrid" else
                                "replica_set" if hello.get("setName") else "standalone")
        evidence["lab_db_exists"] = database in client.list_database_names()
        evidence["status"] = "preflight_observed"
    except Exception as exc:
        evidence["status"] = "blocked"
        evidence["error_type"] = type(exc).__name__
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in evidence.items() if k != "run_id"}, indent=2))
    return 0 if evidence["status"] == "preflight_observed" else 1

if __name__ == "__main__":
    sys.exit(main())
