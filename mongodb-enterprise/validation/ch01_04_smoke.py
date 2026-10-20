#!/usr/bin/env python3
"""Chapters 01–04 isolated integration smoke checks.

Mutates only four dedicated empty tutorial databases. Requires a fresh disposable
localhost MongoDB, explicit opt-in and an empty namespace gate. No database drops.
This is a supplemental smoke test, not complete chapter runtime certification.
"""
import argparse
import json
import os
import sys
import uuid

from lab_preflight import validate_inputs

NAMES = {n: f"mongodb_enterprise_tutorial_ch{n:02d}" for n in range(1, 5)}

def run(client, run_id):
    from bson import ObjectId
    from pymongo.errors import DuplicateKeyError, WriteError
    output = []
    for n, name in NAMES.items():
        database = client[name]
        if name in client.list_database_names() or database.list_collection_names():
            raise RuntimeError(f"Refusing nonempty or preexisting namespace: {name}")
    # Each chapter owns a separate, newly created collection with a unique run marker.
    for n, name in NAMES.items():
        database = client[name]
        coll = database[f"phase4_{run_id}"]
        if coll.count_documents({}) != 0:
            raise RuntimeError("Unexpected existing fixture")
        try:
            if n == 1:
                coll.insert_one({"_id": "fixture", "run_id": run_id, "status": "open"})
                try:
                    coll.insert_one({"_id": "fixture", "run_id": run_id})
                except DuplicateKeyError:
                    pass
                else:
                    raise AssertionError("Duplicate-key negative test failed")
                assert coll.update_one({"_id": "fixture", "run_id": run_id}, {"$set": {"status": "closed"}}).modified_count == 1
                assert coll.find_one({"_id": "fixture"})["status"] == "closed"
                output.append({"chapter": n, "checks": ["insert", "duplicate_key", "update", "read"]})
            elif n == 2:
                oid = ObjectId()
                coll.insert_one({"_id": oid, "run_id": run_id, "amount": 3, "enabled": True})
                assert coll.count_documents({"_id": str(oid)}) == 0
                assert coll.count_documents({"_id": oid, "enabled": True}) == 1
                output.append({"chapter": n, "checks": ["bson_objectid", "string_mismatch", "boolean"]})
            elif n == 3:
                build = client.admin.command("buildInfo")
                assert build.get("version")
                coll.insert_one({"_id": "sentinel", "run_id": run_id})
                assert coll.count_documents({"_id": "sentinel", "run_id": run_id}) == 1
                output.append({"chapter": n, "checks": ["build_info", "bounded_sentinel"],
                               "wiredtiger_metrics": "not_run"})
            else:
                build = client.admin.command("buildInfo")
                assert build.get("version")
                coll.insert_one({"_id": "edition", "run_id": run_id})
                assert coll.count_documents({"run_id": run_id}) == 1
                output.append({"chapter": n, "checks": ["build_info", "fixture_read"],
                               "edition_certified": False})
        finally:
            # Only the precisely named collection created for this run is removed.
            # A failure to verify ownership preserves state for manual review.
            marker_count = coll.count_documents({"run_id": run_id})
            total = coll.count_documents({})
            if marker_count == total and total > 0 and coll.name == f"phase4_{run_id}":
                coll.drop()
            else:
                raise RuntimeError(f"Cleanup blocked for chapter {n}: unexpected ownership")
    return output

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--allowed-host", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    uri = os.getenv("MONGODB_LAB_URI", "")
    if os.getenv("MONGODB_LAB_APPROVED") != "YES" or os.getenv("MONGODB_LAB_MUTATION_APPROVED") != "YES":
        p.error("Both explicit lab and mutation approvals are required")
    for n in NAMES:
        try:
            validate_inputs(uri, args.allowed_host, n, args.run_id)
        except ValueError as exc:
            p.error(str(exc))
    try:
        from pymongo import MongoClient
    except ImportError:
        p.error("Install pymongo only in the approved disposable lab")
    evidence = {"mode": "isolated_smoke", "run_id": args.run_id,
                "runtime_certified": False, "status": "blocked"}
    try:
        with MongoClient(uri, serverSelectionTimeoutMS=4000, directConnection=True) as client:
            hello = client.admin.command("hello")
            if hello.get("msg") == "isdbgrid" or hello.get("setName"):
                raise RuntimeError("Pilot only allows disposable standalone mongod")
            if not hello.get("isWritablePrimary"):
                raise RuntimeError("Lab standalone is not writable")
            evidence["checks"] = run(client, args.run_id)
            evidence["status"] = "smoke_passed"
    except Exception as exc:
        evidence["error_type"] = type(exc).__name__
        evidence["error"] = str(exc)[:300]
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(evidence, file, indent=2)
        file.write("\n")
    print(json.dumps({"status": evidence["status"], "runtime_certified": False}))
    return 0 if evidence["status"] == "smoke_passed" else 1

if __name__ == "__main__":
    sys.exit(main())
