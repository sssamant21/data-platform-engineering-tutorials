#!/usr/bin/env python3
"""Chapter 002: partition metadata, keyed routing and per-partition offsets."""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka", "ch002-ordering"
OUT = Path("kafka/qa/evidence/chapter-002-runtime.json")
RECORDS = ["customer-1:created", "customer-1:paid", "customer-2:created"]

def k(*args, data=None, timeout=100):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1200:]}")
    return p.stdout

def main():
    report = {"chapter": "002", "lab_ids": ["KAFKA-002-A", "KAFKA-002-B"],
              "time_utc": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Uses a disposable single-broker Kafka cluster with RF=1; chapter RF=3/minISR=2 lab remains untested.",
                              "Does not certify offset commits, lag monitoring, or partition reassignment."]}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        k("wait", "--for=condition=Ready", "kafka/qa-kafka", "--timeout=420s", timeout=445)
        manifest = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                    "metadata": {"name": TOPIC, "labels": {"strimzi.io/cluster": CLUSTER}},
                    "spec": {"partitions": 3, "replicas": 1,
                             "config": {"retention.ms": 600000}}}
        k("apply", "-f", "-", data=json.dumps(manifest))
        k("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}",
          "--timeout=180s", timeout=200)
        report["checks"]["three_partition_topic_ready"] = "PASS"
        pods = json.loads(k("get", "pods", "-l", "strimzi.io/cluster=qa-kafka", "-o", "json"))
        candidates = [p["metadata"]["name"] for p in pods["items"]
                      if "dual-role" in p["metadata"]["name"]
                      and p["status"].get("phase") == "Running"]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one running QA Kafka broker, got {candidates}")
        pod = candidates[0]
        base = ["exec", "-i", pod, "-c", "kafka", "--"]
        bs = "qa-kafka-kafka-bootstrap:9092"
        desc = k(*base, "/opt/kafka/bin/kafka-topics.sh",
                 "--bootstrap-server", bs, "--describe", "--topic", TOPIC)
        if not re.search(r"PartitionCount:\s*3\b", desc) or not re.search(r"ReplicationFactor:\s*1\b", desc):
            raise RuntimeError(f"Unexpected topic metadata: {desc[:900]}")
        report["checks"]["partition_count_metadata"] = "PASS"
        k(*base, "/opt/kafka/bin/kafka-console-producer.sh",
          "--bootstrap-server", bs, "--topic", TOPIC,
          "--property", "parse.key=true", "--property", "key.separator=:",
          data="\n".join(RECORDS) + "\n", timeout=90)
        report["checks"]["keyed_production"] = "PASS"
        output = k(*base, "/opt/kafka/bin/kafka-console-consumer.sh",
                   "--bootstrap-server", bs, "--topic", TOPIC,
                   "--from-beginning", "--max-messages", "3", "--timeout-ms", "45000",
                   "--property", "print.key=true",
                   "--property", "print.partition=true",
                   "--property", "print.offset=true",
                   "--property", "key.separator=:",
                   timeout=80)
        parsed = []
        for line in output.splitlines():
            # Kafka CLI emits Partition:0	Offset:0	customer-1:created.
            m = re.search(r"Partition:(\d+)\s+Offset:(\d+)\s+(.+)$", line)
            if not m:
                continue
            partition, offset, payload = int(m.group(1)), int(m.group(2)), m.group(3)
            if ":" not in payload:
                raise RuntimeError(f"Missing keyed payload: {payload!r}")
            key, value = payload.split(":", 1)
            parsed.append({"partition": partition, "offset": offset, "key": key, "value": value})
        expected = {(x.split(":", 1)[0], x.split(":", 1)[1]) for x in RECORDS}
        actual = {(x["key"], x["value"]) for x in parsed}
        if len(parsed) != 3 or actual != expected:
            raise RuntimeError(f"Missing or unexpected keyed records: {parsed!r}; output={output[:700]!r}")
        report["checks"]["all_keyed_records_received"] = "PASS"
        customer1 = [r for r in parsed if r["key"] == "customer-1"]
        if len(customer1) != 2 or len({r["partition"] for r in customer1}) != 1:
            raise RuntimeError(f"Key routing inconsistent: {customer1!r}")
        if [r["value"] for r in customer1] != ["created", "paid"]:
            raise RuntimeError(f"Same-key order violated: {customer1!r}")
        if customer1[1]["offset"] <= customer1[0]["offset"]:
            raise RuntimeError(f"Offsets not increasing: {customer1!r}")
        report["checks"]["same_key_partition_and_order"] = "PASS"
        report["checks"]["monotonic_partition_offsets"] = "PASS"
        report["verified_records"] = parsed
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError) as exc:
        report["error"] = str(exc)[:1800]
        print(f"Chapter 002 failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 002: {report['status']} | {report['certification']}")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
