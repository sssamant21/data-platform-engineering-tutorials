#!/usr/bin/env python3
"""Bounded three-node Strimzi HA exercise, disposable kind context only."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS = "kind-kafka-qa", "kafka-qa"
OUT = Path("kafka/qa/evidence/chapter-001-ha-result.json")
CLI = "/opt/kafka/bin/"
BOOTSTRAP = "qa-ha-kafka-bootstrap:9092"
TOPIC = "qa-ha-events"

def run(*args, data=None, timeout=120, check=True):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, text=True, capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f"kubectl {args[0]}: {p.stderr[-900:]}")
    return p

def brokers():
    items = json.loads(run("get", "pods", "-l", "strimzi.io/cluster=qa-ha", "-o", "json").stdout)["items"]
    return sorted([p for p in items if "ha-dual" in p["metadata"]["name"]],
                  key=lambda p: p["metadata"]["name"])

def client_pod():
    ready = [p for p in brokers() if p["status"].get("phase") == "Running" and
             any(c.get("name") == "kafka" and c.get("ready") for c in p["status"].get("containerStatuses", []))]
    if not ready:
        raise RuntimeError("No ready Kafka client Pod")
    return ready[0]["metadata"]["name"]

def cli(pod, command, *args, data=None, timeout=90):
    return run("exec", "-i", pod, "-c", "kafka", "--", CLI+command,
               "--bootstrap-server", BOOTSTRAP, *args, data=data, timeout=timeout).stdout

def main():
    result = {"chapter": "001", "lab": "three-dual-role-node-ha",
              "status": "FAIL", "checks": {},
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "3 combined broker/controller pods; not 6 dedicated-role pods or zone-level HA."}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"], check=True,
                             text=True, capture_output=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Unsafe Kubernetes context: {ctx!r}")
        run("wait", "kafka/qa-ha", "--for=condition=Ready", "--timeout=600s", timeout=625)
        run("wait", "kafkatopic/qa-ha-events", "--for=condition=Ready", "--timeout=240s", timeout=260)
        pods = brokers()
        if len(pods) != 3 or any(p["status"].get("phase") != "Running" for p in pods):
            raise RuntimeError(f"Expected 3 running Kafka pods; found {len(pods)}")
        result["checks"]["three_nodes_ready"] = "PASS"
        metadata = cli(client_pod(), "kafka-topics.sh", "--describe", "--topic", TOPIC)
        if "ReplicationFactor: 3" not in metadata or "PartitionCount: 1" not in metadata:
            raise RuntimeError(f"Unexpected topic metadata: {metadata[-700:]}")
        result["checks"]["replication_factor_three"] = "PASS"
        baseline = "chapter-001-ha-before-failure"
        cli(client_pod(), "kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all", data=baseline+"\n")
        result["checks"]["baseline_produced"] = "PASS"
        victim = pods[0]["metadata"]["name"]
        old_uid = pods[0]["metadata"]["uid"]
        start = time.monotonic()
        run("delete", "pod", victim, "--wait=false", timeout=50)
        result["checks"]["one_broker_failure_injected"] = "PASS"
        # Verify continued write availability while a broker is absent or recovering.
        # Repeated bounded attempts allow leader election, without claiming zero downtime.
        during = "chapter-001-ha-during-recovery"
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            try:
                cli(client_pod(), "kafka-console-producer.sh", "--topic", TOPIC,
                    "--producer-property", "acks=all", data=during+"\n", timeout=35)
                break
            except (RuntimeError, subprocess.SubprocessError):
                time.sleep(5)
        else:
            raise RuntimeError("Failed to produce with acks=all after one Pod failure")
        result["checks"]["produce_after_failure"] = "PASS"
        # Kafka Ready can be observed before the replacement Pod is fully recreated.
        # Require a new UID and a ready Kafka container before testing recovery.
        replacement_deadline = time.monotonic() + 420
        replacement_seen = False
        while time.monotonic() < replacement_deadline:
            current = {p["metadata"]["name"]: p for p in brokers()}
            candidate = current.get(victim)
            if (candidate and candidate["metadata"]["uid"] != old_uid and
                candidate["status"].get("phase") == "Running" and
                any(c.get("name") == "kafka" and c.get("ready")
                    for c in candidate["status"].get("containerStatuses", []))):
                replacement_seen = True
                break
            time.sleep(5)
        if not replacement_seen:
            raise RuntimeError("Replacement Pod UID and ready Kafka container not observed within 420 seconds")
        result["checks"]["replacement_pod_ready"] = "PASS"
        run("wait", "kafka/qa-ha", "--for=condition=Ready", "--timeout=420s", timeout=445)
        result["checks"]["operator_recovered"] = "PASS"
        # Unique consumer group ensures the full topic is read from the beginning.
        output = cli(client_pod(), "kafka-console-consumer.sh", "--topic", TOPIC,
                     "--from-beginning", "--max-messages", "2",
                     "--timeout-ms", "60000", timeout=85)
        messages = [x.strip() for x in output.splitlines() if x.strip()]
        if sorted(messages) != sorted([baseline, during]):
            raise RuntimeError(f"Unexpected consumed records: {messages!r}")
        result["checks"]["messages_retained_and_consumed"] = "PASS"
        result["recovery_seconds"] = round(time.monotonic()-start, 1)
        result["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        result["error"] = str(exc)[:1200]
        print(f"HA lab failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print(f"Chapter 001 HA: {result['status']} | {OUT}")
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
