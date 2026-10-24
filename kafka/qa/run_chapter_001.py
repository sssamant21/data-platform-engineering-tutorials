#!/usr/bin/env python3
"""Chapter 001 scoped Kubernetes/Strimzi lab acceptance. No external clusters."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTEXT = "kind-kafka-qa"
NAMESPACE = "kafka-qa"
CLUSTER = "qa-kafka"
TOPIC = "ch001-events"
EVENTS = ["ch001-architecture-event-001", "ch001-architecture-event-002"]
OUT = Path("kafka/qa/evidence/chapter-001-runtime.json")

def kubectl(*args, input_text=None, timeout=90):
    cmd = ["kubectl", "--context", CONTEXT, "-n", NAMESPACE, *args]
    p = subprocess.run(cmd, input=input_text, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1200:]}")
    return p.stdout

def main():
    result = {"chapter": "001", "lab_ids": ["KAFKA-001-A", "KAFKA-001-B"],
              "time_utc": datetime.now(timezone.utc).isoformat(),
              "environment": {"context": CONTEXT, "namespace": NAMESPACE, "cluster": CLUSTER},
              "checks": {}, "status": "FAIL", "certification": "NOT_CERTIFIED",
              "limitations": ["Single dual-role broker; six-Pod HA architecture variant not tested.",
                              "Only chapter-scoped architecture and topic/message acceptance tested."]}
    try:
        current = subprocess.run(["kubectl", "config", "current-context"], capture_output=True,
                                 text=True, check=True, timeout=10).stdout.strip()
        if current != CONTEXT:
            raise RuntimeError(f"Refusing Kubernetes context {current!r}")
        kafka = json.loads(kubectl("get", "kafka", CLUSTER, "-o", "json"))
        if not any(c.get("type") == "Ready" and c.get("status") == "True"
                   for c in kafka.get("status", {}).get("conditions", [])):
            raise RuntimeError("Kafka custom resource not Ready")
        result["checks"]["kafka_ready"] = "PASS"
        pools = json.loads(kubectl("get", "kafkanodepool", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))
        if not any({"controller", "broker"}.issubset(set(p["spec"]["roles"]))
                   for p in pools.get("items", [])):
            raise RuntimeError("No dual-role KafkaNodePool found")
        result["checks"]["node_pool_roles"] = "PASS"
        pods = json.loads(kubectl("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))
        broker_pods = [p for p in pods.get("items", []) if "dual-role" in p["metadata"]["name"]
                       and p.get("status", {}).get("phase") == "Running"]
        if len(broker_pods) != 1:
            raise RuntimeError("Expected one running QA dual-role broker pod")
        pod = broker_pods[0]["metadata"]["name"]
        result["checks"]["broker_pod_running"] = "PASS"
        services = json.loads(kubectl("get", "service", f"{CLUSTER}-kafka-bootstrap", "-o", "json"))
        if not services["spec"].get("ports"):
            raise RuntimeError("Bootstrap Service has no ports")
        result["checks"]["bootstrap_service"] = "PASS"
        manifest = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                    "metadata": {"name": TOPIC, "labels": {"strimzi.io/cluster": CLUSTER}},
                    "spec": {"partitions": 1, "replicas": 1,
                             "config": {"retention.ms": 600000}}}
        kubectl("apply", "-f", "-", input_text=json.dumps(manifest))
        kubectl("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}",
                "--timeout=180s", timeout=200)
        result["checks"]["chapter_topic_ready"] = "PASS"
        prefix = ["exec", "-i", pod, "-c", "kafka", "--"]
        bootstrap = f"{CLUSTER}-kafka-bootstrap:9092"
        kubectl(*prefix, "/opt/kafka/bin/kafka-console-producer.sh",
                "--bootstrap-server", bootstrap, "--topic", TOPIC,
                input_text="\n".join(EVENTS) + "\n")
        result["checks"]["chapter_producer"] = "PASS"
        output = kubectl(*prefix, "/opt/kafka/bin/kafka-console-consumer.sh",
                         "--bootstrap-server", bootstrap, "--topic", TOPIC,
                         "--from-beginning", "--max-messages", "2",
                         "--timeout-ms", "45000", timeout=75)
        if [line.strip() for line in output.splitlines() if line.strip()] != EVENTS:
            raise RuntimeError("Chapter 001 message reconciliation mismatch")
        result["checks"]["chapter_consumer_reconciliation"] = "PASS"
        result["verified_event_count"] = 2
        result["status"] = "PASS"
        result["certification"] = "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        result["error"] = str(exc)[:1500]
        print(f"Chapter 001 runtime acceptance failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 001: {result['status']} ({result['certification']})")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
