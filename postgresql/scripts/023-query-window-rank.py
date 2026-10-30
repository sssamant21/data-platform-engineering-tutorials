#!/usr/bin/env python3
"""Rank compatible, seeded PG18 statement entries. Query text is never required."""
import argparse
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

IDENTITY = ("source_id", "server_addr", "server_port", "server_version_num",
            "postmaster_start", "in_recovery", "database_oid", "role_oid",
            "extension_version", "policy", "global_reset", "dealloc")
COUNTERS = ("calls", "total_exec_time", "rows", "shared_blks_hit",
            "shared_blks_read", "temp_blks_written")


def time(value):
    if not isinstance(value, str):
        raise ValueError("missing/nonstring timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.astimezone(timezone.utc)


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("numeric counter required")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("counter must be finite and nonnegative")
    return result


def index(sample):
    if not isinstance(sample, dict) or type(sample.get("schema_version")) is not int or sample["schema_version"] != 1:
        raise ValueError("unsupported schema")
    for key in IDENTITY + ("sampled_at", "entries", "truncated"):
        if key not in sample:
            raise ValueError("missing " + key)
    if not isinstance(sample["source_id"], str) or not sample["source_id"].strip():
        raise ValueError("source identity required")
    if type(sample["server_version_num"]) is not int or not 180000 <= sample["server_version_num"] < 190000:
        raise ValueError("PG18 required")
    for key in ("database_oid", "role_oid", "server_port"):
        if type(sample[key]) is not int or sample[key] <= 0:
            raise ValueError("positive integer " + key + " required")
    if type(sample["in_recovery"]) is not bool or type(sample["dealloc"]) is not int or sample["dealloc"] < 0:
        raise ValueError("invalid recovery/deallocation metadata")
    if sample["truncated"] is not False:
        raise ValueError("truncated/unknown cohort")
    if not isinstance(sample["policy"], dict) or set(sample["policy"]) != {
            "compute_query_id", "track", "track_utility", "track_planning"}:
        raise ValueError("invalid collection policy")
    if sample["policy"]["compute_query_id"] not in ("auto", "on") or sample["policy"]["track"] not in ("top", "all"):
        raise ValueError("inactive/unsupported query collection")
    for key in ("track_utility", "track_planning"):
        if sample["policy"][key] not in ("on", "off"):
            raise ValueError("invalid policy flag")
    if not isinstance(sample["extension_version"], str) or not sample["extension_version"]:
        raise ValueError("extension version required")
    observed = time(sample["sampled_at"])
    if observed < time(sample["postmaster_start"]):
        raise ValueError("sample before server start")
    if sample["global_reset"] is not None and time(sample["global_reset"]) > observed:
        raise ValueError("future reset marker")
    if not isinstance(sample["entries"], list) or len(sample["entries"]) > 200:
        raise ValueError("invalid/bounded entry set required")
    entries = {}
    for entry in sample["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("entry object required")
        for key in ("userid", "dbid", "queryid", "toplevel", "stats_since") + COUNTERS:
            if key not in entry:
                raise ValueError("missing entry field " + key)
        if (type(entry["userid"]) is not int or type(entry["dbid"]) is not int
                or entry["userid"] != sample["role_oid"] or entry["dbid"] != sample["database_oid"]):
            raise ValueError("entry outside cohort")
        queryid = entry["queryid"]
        if not isinstance(queryid, str) or not re.fullmatch(r"-?[0-9]+", queryid) or not -(2**63) <= int(queryid) < 2**63:
            raise ValueError("queryid must be signed bigint text")
        if type(entry["toplevel"]) is not bool:
            raise ValueError("invalid toplevel")
        key = (entry["userid"], entry["dbid"], queryid, entry["toplevel"])
        if key in entries or time(entry["stats_since"]) > observed:
            raise ValueError("duplicate/future entry")
        for field in COUNTERS:
            numeric(entry[field])
            if field != "total_exec_time" and type(entry[field]) is not int:
                raise ValueError("integer counter required: " + field)
        entries[key] = entry
    return entries


def compare(before, after, max_gap=300):
    if type(max_gap) is not int or max_gap <= 0:
        raise ValueError("positive maximum gap required")
    a, b = index(before), index(after)
    for field in IDENTITY:
        left, right = before[field], after[field]
        if field in ("postmaster_start", "global_reset") and left is not None and right is not None:
            left, right = time(left), time(right)
        if left != right:
            raise ValueError("incompatible window: " + field + " changed")
    elapsed = time(after["sampled_at"]) - time(before["sampled_at"])
    seconds = Decimal(elapsed.days * 86400 + elapsed.seconds) + Decimal(elapsed.microseconds) / 1000000
    if seconds <= 0 or seconds > max_gap:
        raise ValueError("nonpositive interval/excessive gap")
    ranked, excluded = [], []
    for key, latest in b.items():
        prior = a.get(key)
        if prior is None:
            excluded.append({"queryid": key[2], "toplevel": key[3], "reason": "new entry: baseline required"})
            continue
        if time(prior["stats_since"]) != time(latest["stats_since"]):
            excluded.append({"queryid": key[2], "toplevel": key[3], "reason": "entry epoch changed"})
            continue
        delta = {field: numeric(latest[field]) - numeric(prior[field]) for field in COUNTERS}
        if any(value < 0 for value in delta.values()):
            excluded.append({"queryid": key[2], "toplevel": key[3], "reason": "counter decreased"})
            continue
        calls = delta["calls"]
        ranked.append({"queryid": key[2], "toplevel": key[3],
                       "delta": {k: str(v) for k, v in delta.items()},
                       "calls_per_second": str(calls / seconds),
                       "interval_mean_exec_ms": str(delta["total_exec_time"] / calls) if calls else None})
    ranked.sort(key=lambda row: Decimal(row["delta"]["total_exec_time"]), reverse=True)
    return {"valid": True, "elapsed_seconds": str(seconds), "ranked": ranked,
            "excluded": excluded,
            "disappeared": [{"queryid": k[2], "toplevel": k[3]} for k in a.keys() - b.keys()],
            "scope": "Compatible retained entries in the exported role/database cohort only."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--max-gap-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        samples = [json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.before, args.after)]
        if any(not isinstance(s, dict) for s in samples):
            raise ValueError("sample object required")
        output = compare(*samples, args.max_gap_seconds)
    except (ValueError, OSError, OverflowError, TypeError) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}))
        raise SystemExit(2)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
