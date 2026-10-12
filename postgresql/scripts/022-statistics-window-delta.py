#!/usr/bin/env python3
"""Compare PostgreSQL 18 database counter samples without bridging known epochs."""
import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

COUNTERS = ("xact_commit", "xact_rollback", "blks_read", "blks_hit",
            "temp_files", "temp_bytes", "deadlocks")
IDENTITY = ("source_id", "server_addr", "server_port", "server_version_num",
            "postmaster_start", "in_recovery", "database_oid", "database_name",
            "track_counts", "stats_reset")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.astimezone(timezone.utc)


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def validate(sample):
    if not isinstance(sample, dict) or type(sample.get("schema_version")) is not int or sample["schema_version"] != 1:
        raise ValueError("unsupported sample schema")
    for key in IDENTITY + ("sampled_at", "snapshot_at", "counters", "gauges"):
        if key not in sample:
            raise ValueError(f"missing field: {key}")
    for key in ("source_id", "database_name"):
        if not isinstance(sample[key], str) or not sample[key].strip():
            raise ValueError(f"nonempty {key} required")
    if sample["server_addr"] is not None and not isinstance(sample["server_addr"], str):
        raise ValueError("invalid server_addr")
    if sample["server_port"] is not None:
        integer(sample["server_port"], "server_port", 1)
    integer(sample["database_oid"], "database_oid", 1)
    integer(sample["server_version_num"], "server_version_num", 180000)
    if sample["server_version_num"] >= 190000:
        raise ValueError("PostgreSQL 18 samples required")
    if type(sample["in_recovery"]) is not bool:
        raise ValueError("in_recovery must be boolean")
    if sample["track_counts"] != "on":
        raise ValueError("track_counts must be on")
    observed, captured = timestamp(sample["snapshot_at"]), timestamp(sample["sampled_at"])
    if captured < observed or observed < timestamp(sample["postmaster_start"]):
        raise ValueError("inconsistent sample timestamps")
    if sample["stats_reset"] is not None and timestamp(sample["stats_reset"]) > captured:
        raise ValueError("reset marker is after collection")
    counters = sample["counters"]
    if not isinstance(counters, dict) or set(counters) != set(COUNTERS):
        raise ValueError("counter field set mismatch")
    for key, value in counters.items():
        integer(value, key)
    gauges = sample["gauges"]
    if not isinstance(gauges, dict) or "numbackends" not in gauges:
        raise ValueError("missing numbackends gauge")
    integer(gauges["numbackends"], "numbackends")


def compare(before, after, max_gap_seconds=300):
    validate(before)
    validate(after)
    integer(max_gap_seconds, "max_gap_seconds", 1)
    for field in IDENTITY:
        # Normalize timestamp representation before comparison.
        a, b = before[field], after[field]
        if field in ("postmaster_start", "stats_reset") and a is not None and b is not None:
            a, b = timestamp(a), timestamp(b)
        if a != b:
            raise ValueError(f"incompatible window: {field} changed")
    elapsed = timestamp(after["snapshot_at"]) - timestamp(before["snapshot_at"])
    seconds = Decimal(elapsed.days * 86400 + elapsed.seconds) + Decimal(elapsed.microseconds) / 1000000
    if seconds <= 0 or seconds > max_gap_seconds:
        raise ValueError("nonpositive/stale interval or excessive gap")
    if timestamp(after["sampled_at"]) <= timestamp(before["sampled_at"]):
        raise ValueError("collection time did not advance")
    delta = {}
    for key in COUNTERS:
        value = after["counters"][key] - before["counters"][key]
        if value < 0:
            raise ValueError(f"incompatible window: {key} decreased")
        delta[key] = value
    accesses = delta["blks_read"] + delta["blks_hit"]
    return dict(valid=True, source_id=after["source_id"], database=after["database_name"],
                snapshot_elapsed_seconds=str(seconds), deltas=delta,
                rates_per_second={key: str(Decimal(value) / seconds) for key, value in delta.items()},
                interval_buffer_hit_ratio=(str(Decimal(delta["blks_hit"]) / accesses)
                                           if accesses else None),
                numbackends_points={"before": before["gauges"]["numbackends"],
                                    "after": after["gauges"]["numbackends"]},
                limitation="Published database counters; not logical request SLIs or physical disk I/O.")


def reject_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def read_sample(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--max-gap-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        result = compare(read_sample(args.before), read_sample(args.after), args.max_gap_seconds)
    except (ValueError, OSError, OverflowError) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}))
        raise SystemExit(2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
