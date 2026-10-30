#!/usr/bin/env python3
"""Compare the bounded Chapter 010 PG18 CSV snapshots. Never changes a server."""
import argparse
import csv
from pathlib import Path
import sys

FIELDS = ["name", "setting", "unit", "source", "context", "sourcefile",
          "pending_restart", "server_major", "is_in_recovery"]
NAMES = {
    "server_version", "port", "listen_addresses", "shared_buffers",
    "max_connections", "work_mem", "fsync", "full_page_writes",
    "synchronous_commit", "wal_level", "synchronous_standby_names",
    "log_min_duration_statement",
}


def read_snapshot(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"{path}: unexpected CSV header")
        rows = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}: malformed row")
            name = row["name"]
            if name not in NAMES or name in rows:
                raise ValueError(f"{path}: unknown or duplicate name {name!r}")
            if row["server_major"] != "18":
                raise ValueError(f"{path}: requires PostgreSQL major 18")
            if row["pending_restart"] not in {"t", "f"}:
                raise ValueError(f"{path}: invalid pending_restart flag")
            if row["is_in_recovery"] not in {"t", "f"}:
                raise ValueError(f"{path}: invalid recovery flag")
            if not row["source"] or not row["context"]:
                raise ValueError(f"{path}: missing source or context")
            rows[name] = row
        if set(rows) != NAMES:
            raise ValueError(f"{path}: missing settings {sorted(NAMES - set(rows))}")
        if len({r["is_in_recovery"] for r in rows.values()}) != 1:
            raise ValueError(f"{path}: inconsistent instance role")
        if not rows["server_version"]["setting"] or not rows["port"]["setting"] or not rows["listen_addresses"]["setting"]:
            raise ValueError(f"{path}: missing version/listener identity")
        return rows


def compare(approved, observed):
    if any(row["pending_restart"] == "t" for row in approved.values()):
        raise ValueError("approved baseline contains a pending restart")
    differences = []
    for name in sorted(NAMES):
        for field in FIELDS[1:]:
            before, after = approved[name][field], observed[name][field]
            if before != after:
                differences.append(
                    f"DRIFT {name}.{field}: approved={before!r} observed={after!r}")
        if observed[name]["pending_restart"] == "t":
            differences.append(f"PENDING RESTART {name}")
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approved", type=Path)
    parser.add_argument("observed", type=Path)
    args = parser.parse_args()
    try:
        differences = compare(read_snapshot(args.approved),
                              read_snapshot(args.observed))
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    if differences:
        print("\n".join(differences))
        return 1
    print("PASS: selected PG18 settings, provenance and instance role match; "
          "no selected pending restart. Other acceptance gates remain required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
