#!/usr/bin/env python3
"""Chapter 001 dedicated controller/broker acceptance, disposable kind only."""
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

CTX, NS = "kind-kafka-qa", "kafka-qa"
OUT = Path("kafka/qa/evidence/chapter-001-six-pod-result.json")
BOOT = "qa-six-kafka-bootstrap:9092"
TOPIC = "qa-six-events"
BIN = "/opt/kafka/bin/"

def k(*args, data=None, timeout=120):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-900:]}")
    return p.stdout

def pods():
    return json.loads(k("get", "pods", "-l", "strimzi.io/cluster=qa-six", "-o", "json"))["items"]

def ready(p):
    return p["status"].get("phase") == "Running" and any(
        x.get("name") == "kafka" and x.get("ready")
        for x in p["status"].get("containerStatuses", []))

def broker():
    names = [p["metadata"]["name"] for p in pods()
             if "-brokers-" in p["metadata"]["name"] and ready(p)]
    if not names:
        raise RuntimeError("No ready broker Pod")
    return sorted(names)[0]

def cli(pod, command, *args, data=None, timeout=100):
    return k("exec", "-i", pod, "-c", "kafka", "--",
             BIN+command, "--bootstrap-server", BOOT,
             *args, data=data, timeout=timeout)

def main():
    report = {"chapter": "001", "lab": "dedicated-six-pod-architecture",
              "status": "FAIL", "checks": {},
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "limitations": "Single kind host and ephemeral storage; not zone resilience or persistent-data disaster recovery."}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        k("wait", "kafka/qa-six", "--for=condition=Ready", "--timeout=900s", timeout=930)
        k("wait", "kafkatopic/qa-six-events", "--for=condition=Ready", "--timeout=240s", timeout=260)
        ps = pods()
        controllers = [p for p in ps if "-controllers-" in p["metadata"]["name"]]
        brokers = [p for p in ps if "-brokers-" in p["metadata"]["name"]]
        if len(controllers) != 3 or len(brokers) != 3 or not all(map(ready, controllers+brokers)):
            raise RuntimeError(f"Expected 3 ready controllers and 3 ready brokers; got {len(controllers)}, {len(brokers)}")
        report["checks"]["six_role_separated_pods"] = "PASS"
        desc = cli(broker(), "kafka-topics.sh", "--describe", "--topic", TOPIC)
        if "ReplicationFactor: 3" not in desc or "PartitionCount: 1" not in desc:
            raise RuntimeError(f"Topic metadata unexpected: {desc[-600:]}")
        report["checks"]["replicated_topic"] = "PASS"
        before = "chapter-001-six-before"
        cli(broker(), "kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all", data=before+"\n")
        report["checks"]["baseline_publish"] = "PASS"
        victim = sorted(brokers, key=lambda p:p["metadata"]["name"])[0]
        name, uid = victim["metadata"]["name"], victim["metadata"]["uid"]
        start = time.monotonic()
        k("delete", "pod", name, "--wait=false", timeout=45)
        report["checks"]["broker_failure_injected"] = "PASS"
        after = "chapter-001-six-after"
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            try:
                cli(broker(), "kafka-console-producer.sh", "--topic", TOPIC,
                    "--producer-property", "acks=all", data=after+"\n", timeout=35)
                break
            except (RuntimeError, subprocess.SubprocessError):
                time.sleep(5)
        else:
            raise RuntimeError("Could not publish with acks=all after broker failure")
        report["checks"]["publish_after_failure"] = "PASS"
        # Kafka Ready may briefly remain true while Pod deletion/recreation is in flight.
        # Observe the replacement UID and container readiness before asserting recovery.
        replacement_deadline = time.monotonic() + 420
        replacement_seen = False
        while time.monotonic() < replacement_deadline:
            replacements = {p["metadata"]["name"]: p for p in pods()}
            candidate = replacements.get(name)
            if candidate and candidate["metadata"]["uid"] != uid and ready(candidate):
                replacement_seen = True
                break
            time.sleep(5)
        if not replacement_seen:
            raise RuntimeError("Replacement broker Pod with new UID and Ready container not observed within 420 seconds")
        report["checks"]["replacement_pod_ready"] = "PASS"
        k("wait", "kafka/qa-six", "--for=condition=Ready", "--timeout=420s", timeout=450)
        report["checks"]["operator_recovery"] = "PASS"
        output = cli(broker(), "kafka-console-consumer.sh", "--topic", TOPIC,
                     "--from-beginning", "--max-messages", "2",
                     "--timeout-ms", "60000", timeout=90)
        if sorted(output.splitlines()) != sorted([before, after]):
            raise RuntimeError(f"Expected both messages; got {output!r}")
        report["checks"]["message_retention"] = "PASS"
        report["recovery_seconds"] = round(time.monotonic()-start, 1)
        report["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        report["error"] = str(e)[:1400]
        print(f"Six-pod acceptance failed: {e}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        print(f"Six-pod acceptance: {report['status']} | {OUT}")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
