#!/usr/bin/env python3
"""Isolated Docker Kafka smoke test. Requires Docker; no Kubernetes/cloud access."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

IMAGE = "apache/kafka:3.9.1"
BIN = "/opt/kafka/bin"
MESSAGES = ["kafka-qa-message-001", "kafka-qa-message-002", "kafka-qa-message-003"]

def call(args, *, input_text=None, timeout=45, check=True):
    result = subprocess.run(args, input=input_text, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args[0]} {args[1:4]}\n{result.stderr[-1500:]}")
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/kafka-runtime-smoke.json"))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", "local"))
    args = parser.parse_args()
    suffix = "".join(c for c in args.run_id if c.isalnum())[:24] or "local"
    name = f"kafka-qa-{suffix}"
    topic = f"qa-smoke-{suffix}".lower()
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "image": IMAGE, "container": name, "topic": topic,
        "scope": "Disposable single-broker Kafka runtime smoke test; not certification of 120 chapter labs.",
        "checks": {}, "status": "ERROR"
    }
    created = False
    started = time.monotonic()
    try:
        call(["docker", "info"], timeout=20)
        existing = call(["docker", "container", "inspect", name], check=False)
        if existing.returncode == 0:
            raise RuntimeError(f"Refusing to reuse or delete existing container: {name}")
        call(["docker", "run", "-d", "--name", name, "--label", "kafka-qa-owned=true",
              "--memory", "3g", "--cpus", "2", IMAGE], timeout=150)
        created = True
        deadline = time.monotonic() + 150
        last = ""
        while time.monotonic() < deadline:
            ready = call(["docker", "exec", name, f"{BIN}/kafka-broker-api-versions.sh",
                          "--bootstrap-server", "localhost:9092"], timeout=15, check=False)
            if ready.returncode == 0:
                report["checks"]["broker_ready"] = "PASS"
                break
            last = ready.stderr[-400:]
            time.sleep(5)
        else:
            raise RuntimeError(f"Kafka broker did not become ready: {last}")
        call(["docker", "exec", name, f"{BIN}/kafka-topics.sh",
              "--bootstrap-server", "localhost:9092", "--create", "--topic", topic,
              "--partitions", "1", "--replication-factor", "1"], timeout=35)
        describe = call(["docker", "exec", name, f"{BIN}/kafka-topics.sh",
                         "--bootstrap-server", "localhost:9092", "--describe",
                         "--topic", topic])
        if topic not in describe.stdout:
            raise RuntimeError("Created topic not found in topic description")
        report["checks"]["topic_create"] = "PASS"
        payload = "\n".join(MESSAGES) + "\n"
        call(["docker", "exec", "-i", name, f"{BIN}/kafka-console-producer.sh",
              "--bootstrap-server", "localhost:9092", "--topic", topic], input_text=payload, timeout=45)
        report["checks"]["produce"] = "PASS"
        consumer = call(["docker", "exec", name, f"{BIN}/kafka-console-consumer.sh",
                         "--bootstrap-server", "localhost:9092", "--topic", topic,
                         "--from-beginning", "--max-messages", str(len(MESSAGES)),
                         "--timeout-ms", "25000"], timeout=40)
        received = [line.strip() for line in consumer.stdout.splitlines() if line.strip()]
        if received != MESSAGES:
            raise RuntimeError(f"Message verification failed: expected {MESSAGES!r}; got {received!r}")
        report["checks"]["consume_and_verify"] = "PASS"
        report["messages_produced"] = len(MESSAGES)
        report["messages_verified"] = len(received)
        report["status"] = "PASS"
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        report["error"] = str(exc)[:2000]
        print(f"Kafka runtime smoke: ERROR: {exc}", file=sys.stderr)
    finally:
        if created:
            cleanup = call(["docker", "rm", "-f", name], timeout=30, check=False)
            report["cleanup"] = "PASS" if cleanup.returncode == 0 else "FAIL"
            if cleanup.returncode != 0:
                report["status"] = "ERROR"
                report["cleanup_error"] = cleanup.stderr[-500:]
        else:
            report["cleanup"] = "NOT_NEEDED"
        report["duration_seconds"] = round(time.monotonic() - started, 1)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Kafka runtime smoke: {report['status']} | evidence: {args.output}", flush=True)
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
