#!/usr/bin/env python3
"""Chapter 001 bounded acceptance test on disposable kind-kafka-qa only."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("kafka/qa/evidence/chapter-001-result.json")
CTX = "kind-kafka-qa"
NS = "kafka-qa"
MESSAGES = ["chapter-001-event-001", "chapter-001-event-002"]

def cmd(*args, input_text=None, timeout=120):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=input_text, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-800:]}")
    return p.stdout

def main():
    result = {"chapter": "001", "lab": "kubernetes-basic-messaging",
              "status": "FAIL", "checks": {}, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Basic Kubernetes architecture and two-message flow only; HA/recovery not certified."}
    try:
        context = subprocess.run(["kubectl", "config", "current-context"],
                                 capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if context != CTX:
            raise RuntimeError(f"Unsafe context {context!r}; expected {CTX!r}")
        cmd("wait", "kafka/qa-kafka", "--for=condition=Ready", "--timeout=420s", timeout=450)
        result["checks"]["kafka_ready"] = "PASS"
        cmd("wait", "kafkatopic/qa-smoke", "--for=condition=Ready", "--timeout=180s", timeout=200)
        result["checks"]["topic_ready"] = "PASS"
        pods = json.loads(cmd("get", "pods", "-l", "strimzi.io/cluster=qa-kafka", "-o", "json"))
        matches = [p["metadata"]["name"] for p in pods["items"]
                   if "dual-role" in p["metadata"]["name"] and p["status"].get("phase") == "Running"]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one Kafka broker pod, found {matches}")
        base = ["exec", "-i", matches[0], "-c", "kafka", "--"]
        cmd(*base, "/opt/kafka/bin/kafka-console-producer.sh",
            "--bootstrap-server", "qa-kafka-kafka-bootstrap:9092", "--topic", "qa-smoke",
            input_text="\n".join(MESSAGES) + "\n", timeout=75)
        result["checks"]["produce"] = "PASS"
        output = cmd(*base, "/opt/kafka/bin/kafka-console-consumer.sh",
                     "--bootstrap-server", "qa-kafka-kafka-bootstrap:9092", "--topic", "qa-smoke",
                     "--from-beginning", "--max-messages", "2", "--timeout-ms", "45000", timeout=75)
        actual = [line.strip() for line in output.splitlines() if line.strip()]
        if actual != MESSAGES:
            raise RuntimeError(f"Messages did not match: {actual!r}")
        result["checks"]["consume_verify"] = "PASS"
        result["verified_messages"] = len(actual)
        result["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        result["error"] = str(exc)[:1200]
        print(f"Chapter 001 lab FAILED: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 001 lab: {result['status']} | evidence: {OUT}")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
