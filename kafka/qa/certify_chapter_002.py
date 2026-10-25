#!/usr/bin/env python3
"""Chapter 002: validate topic partitions, keyed ordering and partition offsets."""
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

CTX = "kind-kafka-qa"
NS = "kafka-qa"
TOPIC = "qa-ch002-ordering"
BOOT = "qa-six-kafka-bootstrap:9092"
OUT = Path("kafka/qa/evidence/chapter-002-certification.json")
CLI = "/opt/kafka/bin/"

def kubectl(*args, data=None, timeout=120):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-1000:]}")
    return p.stdout

def broker():
    ps = json.loads(kubectl("get", "pods", "-l", "strimzi.io/cluster=qa-six", "-o", "json"))["items"]
    ready = [p["metadata"]["name"] for p in ps
             if "-brokers-" in p["metadata"]["name"]
             and p["status"].get("phase") == "Running"
             and any(c.get("name") == "kafka" and c.get("ready")
                     for c in p["status"].get("containerStatuses", []))]
    if not ready:
        raise RuntimeError("No ready broker")
    return sorted(ready)[0]

def cli(script, *args, data=None, timeout=120):
    return kubectl("exec", "-i", broker(), "-c", "kafka", "--",
                   CLI+script, "--bootstrap-server", BOOT, *args,
                   data=data, timeout=timeout)

def main():
    report = {"chapter": "002", "status": "FAIL", "checks": {},
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Single-host kind, ephemeral Kafka storage; tests partition-local ordering, not cross-partition ordering."}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Unsafe context: {ctx!r}")
        kubectl("wait", "kafka/qa-six", "--for=condition=Ready", "--timeout=900s", timeout=930)
        kubectl("wait", "kafkatopic/"+TOPIC, "--for=condition=Ready", "--timeout=240s", timeout=260)
        metadata = cli("kafka-topics.sh", "--describe", "--topic", TOPIC)
        if "PartitionCount: 3" not in metadata or "ReplicationFactor: 3" not in metadata:
            raise RuntimeError(f"Topic metadata mismatch: {metadata[-700:]}")
        report["checks"]["three_partitions_three_replicas"] = "PASS"

        # One key maps consistently to one partition in a single producer session.
        # Unique run prefix makes evidence unambiguous even if the topic is reused.
        prefix = "ch002-" + uuid.uuid4().hex[:12]
        lines = [f"{prefix}-patient|{prefix}-event-{i}" for i in range(1, 6)]
        cli("kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all",
            "--property", "parse.key=true",
            "--property", "key.separator=|",
            data="\n".join(lines)+"\n", timeout=120)
        report["checks"]["keyed_produce_acks_all"] = "PASS"

        # A single partition's offsets increase monotonically for these five records.
        # Read a bounded count from the beginning of a fresh test topic.
        raw = cli("kafka-console-consumer.sh", "--topic", TOPIC,
                  "--from-beginning", "--max-messages", "5",
                  "--timeout-ms", "90000",
                  "--property", "print.key=true",
                  "--property", "print.partition=true",
                  "--property", "print.offset=true",
                  "--property", "key.separator=|", timeout=120)
        parsed = []
        for line in raw.splitlines():
            if prefix not in line:
                continue
            partition = re.search(r"Partition:(\d+)", line)
            offset = re.search(r"Offset:(\d+)", line)
            value = re.search(re.escape(prefix)+r"-event-(\d+)", line)
            if not (partition and offset and value):
                raise RuntimeError(f"Cannot parse consumer metadata: {line!r}")
            parsed.append((int(partition.group(1)), int(offset.group(1)), int(value.group(1))))
        if len(parsed) != 5:
            raise RuntimeError(f"Expected 5 keyed records; got {len(parsed)}: {raw[-900:]}")
        if len({p for p, _, _ in parsed}) != 1:
            raise RuntimeError(f"Same key appeared on multiple partitions: {parsed}")
        report["checks"]["same_key_same_partition"] = "PASS"
        if [seq for _, _, seq in parsed] != [1, 2, 3, 4, 5]:
            raise RuntimeError(f"Per-partition order not preserved: {parsed}")
        offsets = [off for _, off, _ in parsed]
        if offsets != sorted(offsets) or len(set(offsets)) != 5:
            raise RuntimeError(f"Offsets not strictly increasing: {offsets}")
        report["checks"]["partition_order_and_offsets"] = "PASS"
        report["partition"] = parsed[0][0]
        report["offsets"] = offsets
        report["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        report["error"] = str(e)[:1400]
        print(f"Chapter 002 failed: {e}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        print("Chapter 002: "+report["status"])
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
