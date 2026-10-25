#!/usr/bin/env python3
"""Chapter 012: declarative KafkaTopic lifecycle and metadata reconciliation."""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha", "ch012-topic-admin"
OUT = Path("kafka/qa/evidence/chapter-012-runtime.json")

def kubectl(*args, data=None, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1200:]}")
    return p.stdout

def topic_manifest(partitions, retention):
    return json.dumps({
        "apiVersion": "kafka.strimzi.io/v1beta2",
        "kind": "KafkaTopic",
        "metadata": {"name": TOPIC, "labels": {"strimzi.io/cluster": CLUSTER}},
        "spec": {"partitions": partitions, "replicas": 3,
                 "config": {"min.insync.replicas": 2, "retention.ms": retention}}
    })

def wait_topic():
    kubectl("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}",
            "--timeout=240s", timeout=260)

def describe():
    pods = json.loads(kubectl("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}",
                              "-o", "json"))["items"]
    names = sorted(p["metadata"]["name"] for p in pods
                   if "dual-role" in p["metadata"]["name"] and p["status"].get("phase") == "Running")
    if len(names) != 3:
        raise RuntimeError("Expected three running Kafka Pods")
    return kubectl("exec", names[0], "-c", "kafka", "--",
                   "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server",
                   f"{CLUSTER}-kafka-bootstrap:9092", "--describe", "--topic", TOPIC)

def check_partitions(description, count):
    rows = re.findall(r"Partition:\s*(\d+).*?Replicas:\s*([\d,]+).*?Isr:\s*([\d,]+)", description)
    if len(rows) != count or {int(p) for p, _, _ in rows} != set(range(count)):
        raise RuntimeError(f"Expected {count} partitions: {description[-1200:]}")
    if any(len(set(reps.split(","))) != 3 or len(set(isr.split(","))) != 3
           for _, reps, isr in rows):
        raise RuntimeError(f"RF3/ISR3 mismatch: {description[-1200:]}")

def main():
    report = {"chapter": "012", "timestamp": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Isolated disposable topic; no production retention changes.",
                              "Partition expansion is irreversible in-place; only QA topic used.",
                              "No ACL, legal retention, or consumer-key migration certification."]}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"], check=True,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        kubectl("wait", "--for=condition=Ready", f"kafka/{CLUSTER}",
                "--timeout=600s", timeout=630)
        kubectl("apply", "--dry-run=server", "-f", "-", data=topic_manifest(2, 600000))
        report["checks"]["topic_manifest_server_dry_run"] = "PASS"
        kubectl("apply", "-f", "-", data=topic_manifest(2, 600000))
        wait_topic()
        check_partitions(describe(), 2)
        report["checks"]["two_partition_rf3_isr3"] = "PASS"
        kubectl("apply", "-f", "-", data=topic_manifest(3, 600000))
        wait_topic()
        check_partitions(describe(), 3)
        report["checks"]["declarative_partition_expansion"] = "PASS"
        kubectl("apply", "-f", "-", data=topic_manifest(3, 900000))
        wait_topic()
        actual = json.loads(kubectl("get", "kafkatopic", TOPIC, "-o", "json"))
        if actual["spec"]["config"].get("retention.ms") != 900000:
            raise RuntimeError("Retention desired state mismatch")
        report["checks"]["retention_cr_readback"] = "PASS"
        check_partitions(describe(), 3)
        report["checks"]["post_reconciliation_metadata"] = "PASS"
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        report["error"] = str(exc)[:1500]
        print(f"Chapter 012 failure: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 012: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
