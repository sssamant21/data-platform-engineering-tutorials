#!/usr/bin/env python3
"""Chapter 003 isolated producer, consumer group, offset and replay acceptance."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka", "ch003-delivery"
OUT = Path("kafka/qa/evidence/chapter-003-runtime.json")
EVENTS = ["payment-003-001", "payment-003-002"]
GROUP1, GROUP2 = "qa-ch003-primary", "qa-ch003-replay"

def k(*args, data=None, timeout=100):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1400:]}")
    return p.stdout

def main():
    report = {"chapter": "003", "lab_ids": ["KAFKA-003-A", "KAFKA-003-B", "KAFKA-003-D"],
              "time_utc": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Single-broker RF=1: acks=all cannot prove multi-replica durability.",
                              "Idempotent producer retry behavior not fault-injected.",
                              "Explicit manual commits with Python client (Lab C) not exercised.",
                              "Kafka transactions and downstream exactly-once semantics not certified."]}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"], capture_output=True,
                             text=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=420s", timeout=445)
        topic = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                 "metadata": {"name": TOPIC, "labels": {"strimzi.io/cluster": CLUSTER}},
                 "spec": {"partitions": 1, "replicas": 1, "config": {"retention.ms": 600000}}}
        k("apply", "-f", "-", data=json.dumps(topic))
        k("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}", "--timeout=180s", timeout=200)
        report["checks"]["topic_ready"] = "PASS"
        pods = json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))
        brokers = [p["metadata"]["name"] for p in pods["items"]
                   if "dual-role" in p["metadata"]["name"] and p["status"].get("phase") == "Running"]
        if len(brokers) != 1:
            raise RuntimeError(f"Expected one QA broker, got {brokers!r}")
        base = ["exec", "-i", brokers[0], "-c", "kafka", "--"]
        bs = f"{CLUSTER}-kafka-bootstrap:9092"
        # Console producer supports acks=all; idempotent retries need a dedicated client.
        k(*base, "/opt/kafka/bin/kafka-console-producer.sh",
          "--bootstrap-server", bs, "--topic", TOPIC,
          "--producer-property", "acks=all",
          data="\n".join(EVENTS) + "\n", timeout=90)
        report["checks"]["producer_acks_all"] = "PASS"
        consumer = "/opt/kafka/bin/kafka-console-consumer.sh"
        def consume(group):
            output = k(*base, consumer, "--bootstrap-server", bs, "--topic", TOPIC,
                       "--group", group, "--from-beginning", "--max-messages", "2",
                       "--timeout-ms", "45000", timeout=90)
            records = [s.strip() for s in output.splitlines() if s.strip()]
            if records != EVENTS:
                raise RuntimeError(f"Group {group}: expected {EVENTS!r}, got {records!r}")
            return records
        consume(GROUP1)
        report["checks"]["primary_consumer_group"] = "PASS"
        groups = k(*base, "/opt/kafka/bin/kafka-consumer-groups.sh",
                   "--bootstrap-server", bs, "--describe", "--group", GROUP1, timeout=60)
        # CLI commits are asynchronous during consumer shutdown. A missing offset is a failure.
        lines = [s for s in groups.splitlines() if TOPIC in s and GROUP1 in s]
        if not lines:
            raise RuntimeError(f"Primary group committed offsets not visible: {groups[-1000:]!r}")
        report["checks"]["primary_group_offsets_visible"] = "PASS"
        consume(GROUP2)
        report["checks"]["independent_group_replay"] = "PASS"
        report["verified_event_count"] = 2
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        report["error"] = str(exc)[:1800]
        print(f"Chapter 003 failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 003: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
