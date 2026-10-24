#!/usr/bin/env python3
"""Readiness and message verification in disposable kind-kafka-qa context only."""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CTX = "kind-kafka-qa"
NS = "kafka-qa"
OUT = Path("kafka/qa/evidence/strimzi-runtime-smoke.json")
MESSAGES = ["strimzi-qa-001", "strimzi-qa-002", "strimzi-qa-003"]

def run(*args, data=None, timeout=120):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:6])}: {p.stderr[-1000:]}")
    return p.stdout

def main():
    report = {"time_utc": datetime.now(timezone.utc).isoformat(),
              "context": CTX, "namespace": NS, "checks": {},
              "scope": "One disposable kind + Strimzi KRaft integration scenario, not 120-lab certification.",
              "status": "ERROR"}
    try:
        actual = subprocess.run(["kubectl", "config", "current-context"], text=True,
                                capture_output=True, check=True, timeout=10).stdout.strip()
        if actual != CTX:
            raise RuntimeError(f"Refusing context {actual!r}; expected {CTX!r}")
        run("wait", "--for=condition=Ready", "kafka/qa-kafka", "--timeout=420s", timeout=445)
        report["checks"]["kafka_reconciled"] = "PASS"
        run("wait", "--for=condition=Ready", "kafkatopic/qa-smoke", "--timeout=180s", timeout=200)
        report["checks"]["topic_reconciled"] = "PASS"
        pods = json.loads(run("get", "pods", "-l", "strimzi.io/cluster=qa-kafka", "-o", "json"))
        brokers = [p["metadata"]["name"] for p in pods["items"]
                   if "dual-role" in p["metadata"]["name"] and
                   p["status"].get("phase") == "Running"]
        if len(brokers) != 1:
            raise RuntimeError(f"Expected one running dual-role Kafka pod, found {brokers!r}")
        pod = brokers[0]
        base = ["exec", "-i", pod, "-c", "kafka", "--"]
        producer = "/opt/kafka/bin/kafka-console-producer.sh"
        consumer = "/opt/kafka/bin/kafka-console-consumer.sh"
        run(*base, producer, "--bootstrap-server", "qa-kafka-kafka-bootstrap:9092",
            "--topic", "qa-smoke", data="\n".join(MESSAGES) + "\n", timeout=75)
        report["checks"]["produce"] = "PASS"
        output = run(*base, consumer, "--bootstrap-server", "qa-kafka-kafka-bootstrap:9092",
                     "--topic", "qa-smoke", "--from-beginning",
                     "--max-messages", "3", "--timeout-ms", "45000", timeout=75)
        received = [s.strip() for s in output.splitlines() if s.strip()]
        if received != MESSAGES:
            raise RuntimeError(f"Message mismatch: {received!r}")
        report["checks"]["consume_verify"] = "PASS"
        report["verified_messages"] = len(received)
        report["status"] = "PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError) as exc:
        report["error"] = str(exc)[:1500]
        print(f"Strimzi smoke failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Strimzi runtime: {report['status']} | {OUT}")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
