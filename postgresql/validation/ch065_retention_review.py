#!/usr/bin/env python3
"""Offline Chapter 065 retention decision screen. NO DELETION CAPABILITY.

The submitted CSV is self-reported metadata. An eligible row merely requests
independent review; it NEVER establishes actual WAL dependency coverage or
authorizes deletion. No database, filesystem deletion, cloud or API calls.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

REQUIRED = {
    "backup_id", "backup_type", "start_utc", "end_utc", "timeline",
    "wal_start", "wal_end", "manifest_verified", "offsite_copy_verified",
    "immutable_until_utc", "legal_hold", "retention_class",
    "expiry_candidate_utc", "dependency_chain_verified", "restore_tested",
    "decision", "reviewer", "notes"
}
TYPES = {"physical", "logical"}
TRUE = "yes"
FALSE = "no"


def parse_utc(value: str):
    if not value:
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset() != timezone.utc.utcoffset(t):
            return None
        return t.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def evaluate(row: dict, now: datetime):
    errors = []
    def req(name):
        return isinstance(row.get(name), str) and bool(row[name].strip())
    for field in ("backup_id","start_utc","end_utc","timeline",
                  "wal_start","wal_end","retention_class","expiry_candidate_utc",
                  "reviewer"):
        if not req(field):
            errors.append("missing_" + field)
    if row.get("backup_type") not in TYPES:
        errors.append("unsupported_backup_type")
    for field in ("manifest_verified","offsite_copy_verified",
                  "dependency_chain_verified","restore_tested"):
        if row.get(field) != TRUE:
            errors.append(field + "_not_verified")
    if row.get("legal_hold") != FALSE:
        errors.append("legal_hold_active_or_unknown")
    if row.get("decision") not in ("DO_NOT_DELETE","PENDING_REVIEW"):
        errors.append("unsafe_existing_decision")
    start = parse_utc(row.get("start_utc", ""))
    end = parse_utc(row.get("end_utc", ""))
    expiry = parse_utc(row.get("expiry_candidate_utc", ""))
    immutable_str = row.get("immutable_until_utc", "")
    immutable = parse_utc(immutable_str)
    if start is None or end is None or not start < end <= now:
        errors.append("invalid_backup_window")
    if expiry is None or expiry > now or (end and expiry < end):
        errors.append("retention_not_expired_or_invalid")
    if immutable_str:
        if immutable is None or immutable > now:
            errors.append("immutable_until_active_or_invalid")
    return sorted(set(errors))


def screen(rows: list[dict], now: datetime, header: list[str]):
    faults = []
    if not REQUIRED.issubset(set(header)):
        faults.append("missing_required_csv_columns")
    ids = set()
    outcomes = []
    for row in rows:
        reasons = evaluate(row, now)
        key = row.get("backup_id")
        if not isinstance(key, str) or not key.strip() or key in ids:
            reasons.append("missing_or_duplicate_backup_id")
        else:
            ids.add(key)
        if faults:
            reasons += faults
        outcomes.append({
            "status": "HOLD" if reasons else "ELIGIBLE_FOR_INDEPENDENT_REVIEW_ONLY",
            "reasons": sorted(set(reasons))
        })
    if not rows:
        faults.append("no_backup_rows")
    return {
        "schema": "pg-ch065-retention-review-v1",
        "decision": "NO_GO" if faults or any(x["status"]=="HOLD" for x in outcomes) else "METADATA_REVIEW_POSSIBLE_UNAUTHENTICATED",
        "rows": len(rows),
        "held": sum(x["status"]=="HOLD" for x in outcomes),
        "eligible_for_review": sum(x["status"]=="ELIGIBLE_FOR_INDEPENDENT_REVIEW_ONLY" for x in outcomes),
        "row_results": outcomes,
        "packet_reasons": sorted(set(faults)),
        "deletion_authorized": False,
        "deletion_performed": False,
        "source_provenance_authenticated": False,
        "certification": "NOT_CERTIFIED",
        "note": "A YES flag does not prove real WAL coverage, restore viability or offsite durability. Only an authorized independent human can decide disposition."
    }


def main():
    ap=argparse.ArgumentParser(description="Offline metadata-only retention safety review; never deletes")
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--now-utc", required=True)
    ap.add_argument("--json-out",type=Path)
    args=ap.parse_args()
    now=parse_utc(args.now_utc)
    if now is None:
        print("NO_GO: --now-utc must contain an explicit UTC offset",file=sys.stderr)
        return 2
    try:
        with args.csv.open(encoding="utf-8-sig", newline="") as f:
            reader=csv.DictReader(f)
            header=reader.fieldnames or []
            rows=list(reader)
        output=screen(rows,now,header)
    except (OSError, UnicodeError, csv.Error):
        output=screen([],now,[])
        output["packet_reasons"].append("csv_unavailable_or_invalid")
        output["decision"]="NO_GO"
    encoded=json.dumps(output,indent=2)+"\n"
    if args.json_out:
        args.json_out.write_text(encoded, encoding="utf-8")
    print(encoded)
    # Eligible simply permits metadata review; no operating authorization.
    return 0 if output["decision"]=="METADATA_REVIEW_POSSIBLE_UNAUTHENTICATED" else 2


if __name__=="__main__":
    raise SystemExit(main())
