#!/usr/bin/env python3
"""Correlate restricted PG18 JSON logs with Chapter 024 client records."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re

DURATION = re.compile(r"^duration:\s+([0-9]+(?:\.[0-9]+)?)\s+ms\b")


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp string required")
    if value.endswith(" UTC"):
        value = value[:-4] + "+00:00"
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid timestamp format") from None
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.astimezone(timezone.utc)


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("object required")
            except ValueError as exc:
                # Do not echo the raw line or its data in error output.
                raise ValueError(f"invalid JSON record at line {number}") from exc
            rows.append(row)
    return rows


def correlate(logs, traces, source_id, skew_ms=500):
    if not source_id or type(skew_ms) is not int or not 0 <= skew_ms <= 5000:
        raise ValueError("source identity and bounded skew required")
    apps, results = {}, []
    for trace in traces:
        trace_id = trace.get("trace_id", "")
        if not isinstance(trace_id, str) or not re.fullmatch(r"[0-9a-f]{32}", trace_id):
            raise ValueError("invalid trace identifier")
        if trace.get("source_id") != source_id or trace.get("database") != "c024_logs":
            raise ValueError("trace outside source/database contract")
        app = trace.get("application_name")
        if app != "c024_" + trace_id or app in apps:
            raise ValueError("invalid/duplicate correlation application")
        span = trace.get("span_id", "")
        if not isinstance(span, str) or not re.fullmatch(r"[0-9a-f]{16}", span):
            raise ValueError("invalid span identifier")
        if timestamp(trace["end"]) < timestamp(trace["start"]):
            raise ValueError("reversed trace interval")
        duration = trace.get("duration_ms")
        if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
            raise ValueError("invalid client duration")
        if trace.get("pid") is not None and (type(trace["pid"]) is not int or trace["pid"] <= 0):
            raise ValueError("invalid trace PID")
        if trace.get("session_id") is not None and not re.fullmatch(r"[0-9a-f]+\.[0-9a-f]+", str(trace["session_id"])):
            raise ValueError("invalid trace session")
        if trace.get("outcome") not in ("success", "error", "client_timeout"):
            raise ValueError("invalid trace outcome")
        row = {k: trace[k] for k in ("trace_id", "span_id", "application_name", "pid",
                                     "session_id", "start", "end", "duration_ms", "outcome")}
        row["server_events"] = []
        row["match_status"] = "NO_MATCH_NOT_PROOF_OF_HEALTH"
        apps[app] = (trace, row)
        results.append(row)
    seen, duplicate_count = {}, 0
    tolerance = timedelta(milliseconds=skew_ms)
    for log in logs:
        app = log.get("application_name")
        if log.get("dbname") != "c024_logs" or app not in apps:
            continue
        trace, row = apps[app]
        if (trace.get("pid") is None or trace.get("session_id") is None
                or log.get("pid") != trace["pid"] or log.get("session_id") != trace["session_id"]):
            continue
        moment = timestamp(log.get("timestamp"))
        if not timestamp(trace["start"]) - tolerance <= moment <= timestamp(trace["end"]) + tolerance:
            continue
        line = log.get("line_num")
        if type(line) is not int or line <= 0:
            raise ValueError("invalid server line number")
        key = (log["session_id"], log["pid"], line)
        if key in seen:
            if log != seen[key]:
                raise ValueError("conflicting duplicate server identity")
            duplicate_count += 1
            continue
        seen[key] = log
        severity = log.get("error_severity")
        message = log.get("message", "")
        duration = DURATION.match(message) if isinstance(message, str) else None
        state = log.get("state_code")
        if state is not None and (not isinstance(state, str) or not re.fullmatch(r"[0-9A-Z]{5}", state)):
            raise ValueError("invalid SQLSTATE")
        query_id = log.get("query_id")
        if query_id is not None and (type(query_id) is not int or not -(2**63) <= query_id < 2**63):
            raise ValueError("invalid query identifier")
        if severity in ("ERROR", "FATAL", "PANIC"):
            duration_ms, kind = None, "server_error"
        elif duration is not None and severity == "LOG":
            duration_ms = float(duration[1])
            if not math.isfinite(duration_ms):
                raise ValueError("nonfinite server duration")
            kind = "completed_duration"
        else:
            continue
        event = dict(timestamp=moment.isoformat(), session_line=line, kind=kind,
                     state_code=state, duration_ms=duration_ms,
                     query_id=str(query_id) if query_id is not None else None)
        row["server_events"].append(event)
        row["match_status"] = "MATCHED_SESSION_EVENTS_NOT_ONE_TO_ONE_SPANS"
    return dict(source_id=source_id, skew_tolerance_ms=skew_ms,
                duplicate_records_skipped=duplicate_count, traces=results,
                limitation="No SQL/message/detail/context exported; raw logs remain sensitive.")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("logs")
    cli.add_argument("traces")
    cli.add_argument("--source-id", required=True)
    cli.add_argument("--skew-ms", type=int, default=500)
    args = cli.parse_args()
    try:
        result = correlate(read_jsonl(args.logs), read_jsonl(args.traces),
                           args.source_id, args.skew_ms)
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as exc:
        print(json.dumps({"valid": False, "reason": str(exc)}))
        raise SystemExit(2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
