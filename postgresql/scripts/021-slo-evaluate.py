#!/usr/bin/env python3
"""Offline event SLI arithmetic. Does not infer telemetry coverage or issue alerts."""
import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

FIELDS = ["event_id", "finished_at", "eligible", "success", "duration_ms"]


def timestamp(value):
    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return value.astimezone(timezone.utc)


def number(value):
    value = Decimal(value)
    if not value.is_finite():
        raise ValueError("nonfinite number")
    return value


def load_events(path):
    rows, ids = [], set()
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV header must be: " + ",".join(FIELDS))
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"invalid column count at line {line}")
            event_id = row["event_id"]
            if not event_id.strip() or event_id in ids:
                raise ValueError(f"empty/duplicate event_id at line {line}")
            ids.add(event_id)
            if row["eligible"] not in ("0", "1") or row["success"] not in ("0", "1"):
                raise ValueError(f"flags must be 0 or 1 at line {line}")
            duration = number(row["duration_ms"])
            if duration < 0:
                raise ValueError(f"negative duration at line {line}")
            rows.append((timestamp(row["finished_at"]), row["eligible"] == "1",
                         row["success"] == "1", duration))
    return rows


def metric(total, good, target):
    if not Decimal(0) < target < Decimal(1):
        raise ValueError("targets must be strictly between 0 and 1")
    if total == 0:
        return dict(total=0, good=0, bad=0, sli=None, allowed_bad=None,
                    budget_consumed=None, remaining_bad=None, burn_rate=None)
    bad = total - good
    allowance = Decimal(total) * (1 - target)
    consumed = Decimal(bad) / allowance
    return dict(total=total, good=good, bad=bad,
                sli=str(Decimal(good) / total), allowed_bad=str(allowance),
                budget_consumed=str(consumed),
                remaining_bad=str(allowance - bad), burn_rate=str(consumed))


def evaluate(rows, end, window_seconds, threshold, availability_target,
             latency_target, min_events):
    if window_seconds <= 0 or min_events <= 0 or threshold < 0:
        raise ValueError("window/min-events must be positive; latency must be nonnegative")
    # Validate even empty windows.
    metric(0, 0, availability_target)
    metric(0, 0, latency_target)
    start = end - timedelta(seconds=window_seconds)
    selected = [r for r in rows if start <= r[0] < end]
    events = [r for r in selected if r[1]]
    total = len(events)
    return dict(window_start=start.isoformat(), window_end=end.isoformat(),
                interval="[start,end)", quality=("NO_EVENTS" if not total else
                "LOW_VOLUME" if total < min_events else "OBSERVED"),
                coverage="not inferred; verify independently",
                excluded=len(selected) - total,
                outside_window=len(rows) - len(selected),
                latency_threshold_ms=str(threshold),
                availability_target=str(availability_target),
                timely_success_target=str(latency_target),
                availability=metric(total, sum(r[2] for r in events), availability_target),
                timely_success=metric(total, sum(r[2] and r[3] <= threshold
                                                for r in events), latency_target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--end", required=True, help="timezone-aware reporting end")
    parser.add_argument("--window-seconds", type=int, default=2592000)
    parser.add_argument("--latency-ms", default="250")
    parser.add_argument("--availability-target", default="0.999")
    parser.add_argument("--latency-target", default="0.99")
    parser.add_argument("--min-events", type=int, default=100)
    args = parser.parse_args()
    try:
        result = evaluate(load_events(args.csv), timestamp(args.end), args.window_seconds,
                          number(args.latency_ms), number(args.availability_target),
                          number(args.latency_target), args.min_events)
    except (ValueError, InvalidOperation, OSError, OverflowError) as exc:
        parser.exit(2, f"Invalid input: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
