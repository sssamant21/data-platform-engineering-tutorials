#!/usr/bin/env python3
"""V05 offline physical-storage growth reference calculator.

Accepts curated provider/OS physical disk daily snapshots only. No DB, cloud,
network, subprocess, mutations, billing, PHI or credentials involved.

CSV columns:
sample_date_utc,cluster_id,instance_id,used_bytes,free_bytes,reserve_bytes,quality

All byte columns are non-negative integers; quality must be COMPLETE.
At least 14 consecutive UTC daily samples per instance are required.
Run: python V05-capacity-forecast.py --input physical-daily.csv
Run: python V05-capacity-forecast.py --self-test

Forecast assumes no storage auto-growth. For actual decisions review peak
workload, provider auto-scaling, disk/WAL volumes, failover/restore headroom.
"""
import argparse
import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
import sys

GIB = 1024 ** 3
FIELDS = (
    "sample_date_utc", "cluster_id", "instance_id",
    "used_bytes", "free_bytes", "reserve_bytes", "quality",
)

def read_rows(filename):
    with open(filename, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != set(FIELDS):
            raise ValueError("CSV header must contain exactly: " + ",".join(FIELDS))
        groups = {}
        for line_number, row in enumerate(reader, 2):
            if not row["cluster_id"] or not row["instance_id"]:
                raise ValueError(f"line {line_number}: missing cluster or instance identity")
            if row["quality"] != "COMPLETE":
                raise ValueError(f"line {line_number}: non-COMPLETE sample")
            try:
                day = date.fromisoformat(row["sample_date_utc"])
                values = tuple(int(row[k]) for k in ("used_bytes","free_bytes","reserve_bytes"))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"line {line_number}: bad UTC date or integer bytes") from exc
            if any(value < 0 for value in values):
                raise ValueError(f"line {line_number}: negative byte measurement")
            key = (row["cluster_id"], row["instance_id"])
            groups.setdefault(key, []).append((day, *values))
    if not groups:
        raise ValueError("No samples")
    return groups

def percentile_nearest_rank(values, quantile):
    if not values:
        raise ValueError("No growth deltas")
    ordered = sorted(values)
    from math import ceil
    return ordered[max(0, ceil(len(ordered) * quantile) - 1)]

def forecast_one(key, samples):
    samples = sorted(samples)
    if len(samples) < 14:
        raise ValueError(f"{key}: need at least 14 UTC daily samples")
    if len({x[0] for x in samples}) != len(samples):
        raise ValueError(f"{key}: duplicate sample dates")
    if any((b[0] - a[0]) != timedelta(days=1)
           for a,b in zip(samples, samples[1:])):
        raise ValueError(f"{key}: missing a UTC daily sample")
    if len({x[3] for x in samples}) > 1:
        raise ValueError(f"{key}: reserve policy changed within sample series")
    rates = [b[1]-a[1] for a,b in zip(samples, samples[1:])]
    baseline_rate = max(0, median(rates))
    peak_rate = max(baseline_rate, 0, percentile_nearest_rank(rates, 0.9))
    day, used, free, reserve = samples[-1]
    headroom = max(0, free-reserve)

    def runway(rate):
        if headroom == 0:
            return "0.0"
        if rate <= 0:
            return "UNKNOWN"
        return f"{headroom/rate:.1f}"

    return {
        "cluster_id": key[0], "instance_id": key[1],
        "latest_utc_date": day.isoformat(), "daily_samples": len(samples),
        "latest_used_gib": f"{used/GIB:.2f}",
        "latest_free_gib": f"{free/GIB:.2f}",
        "reserve_gib": f"{reserve/GIB:.2f}",
        "baseline_gib_day": f"{baseline_rate/GIB:.2f}",
        "high_gib_day": f"{peak_rate/GIB:.2f}",
        "baseline_runway_days": runway(baseline_rate),
        "high_runway_days": runway(peak_rate),
        **{
            f"baseline_free_{days}d_gib": f"{(free-baseline_rate*days)/GIB:.2f}"
            for days in (30,60,90)
        },
        **{
            f"high_free_{days}d_gib": f"{(free-peak_rate*days)/GIB:.2f}"
            for days in (30,60,90)
        },
    }

def self_test():
    samples = [
        (date(2026,10,1)+timedelta(days=i), 1000*GIB+i*20*GIB,
         1200*GIB-i*20*GIB, 100*GIB)
        for i in range(14)
    ]
    value = forecast_one(("testcluster","primary"), samples)
    assert value["baseline_gib_day"] == "20.00"
    assert value["high_gib_day"] == "20.00"
    assert value["baseline_free_30d_gib"] == "340.00"
    assert value["baseline_runway_days"] == "42.0"
    for invalid in (samples[:13], samples[0:6]+samples[7:],
                    samples+samples[-1:]):
        try:
            forecast_one(("testcluster","primary"), invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid sample series was accepted")
    flat = [(d, 100*GIB, 100*GIB, 20*GIB) for d, *_ in samples]
    flat_out = forecast_one(("testcluster","primary"), flat)
    assert flat_out["baseline_runway_days"] == "UNKNOWN"
    print("PASS: offline V05 forecast deterministic self-tests (synthetic data)")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="CSV of DAILY PHYSICAL disk readings")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.input is None:
        parser.error("--input is required unless using --self-test")
    groups = read_rows(args.input)
    results = [forecast_one(key, rows) for key, rows in sorted(groups.items())]
    writer = csv.DictWriter(sys.stdout, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(f"V05 input validation FAILED: {exc}")
