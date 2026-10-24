#!/usr/bin/env python3
"""Chapter 001 recovery exercise in a disposable, single-node kind Strimzi cluster."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS = "kind-kafka-qa", "kafka-qa"
OUT = Path("kafka/qa/evidence/chapter-001-recovery-result.json")
BROKER_LABEL = "strimzi.io/cluster=qa-kafka"

def kubectl(*args, data=None, timeout=120):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-1000:]}")
    return p.stdout

def broker():
    pods = json.loads(kubectl("get", "pods", "-l", BROKER_LABEL, "-o", "json"))
    matches = [p for p in pods["items"] if "dual-role" in p["metadata"]["name"]]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one dual-role broker; found {len(matches)}")
    return matches[0]

def send_and_receive(message):
    pod = broker()["metadata"]["name"]
    base = ("exec", "-i", pod, "-c", "kafka", "--")
    cli = "/opt/kafka/bin/"
    kubectl(*base, cli+"kafka-console-producer.sh", "--bootstrap-server",
            "qa-kafka-kafka-bootstrap:9092", "--topic", "qa-smoke",
            data=message+"\n", timeout=75)
    output = kubectl(*base, cli+"kafka-console-consumer.sh", "--bootstrap-server",
                     "qa-kafka-kafka-bootstrap:9092", "--topic", "qa-smoke",
                     "--from-beginning", "--max-messages", "1",
                     "--timeout-ms", "45000", timeout=75)
    if output.strip() != message:
        raise RuntimeError(f"Message mismatch: {output.strip()!r} != {message!r}")

def main():
    report = {"chapter": "001", "lab": "single-broker-recovery", "status": "FAIL",
              "checks": {}, "started_utc": datetime.now(timezone.utc).isoformat(),
              "limitations": "Single-node ephemeral-storage restart: validates service recovery, not HA, retained records or durability."}
    try:
        context = subprocess.run(["kubectl", "config", "current-context"], text=True,
                                 capture_output=True, check=True, timeout=10).stdout.strip()
        if context != CTX:
            raise RuntimeError(f"Refusing unsafe context {context!r}")
        kubectl("wait", "kafka/qa-kafka", "--for=condition=Ready", "--timeout=420s", timeout=450)
        kubectl("wait", "kafkatopic/qa-smoke", "--for=condition=Ready", "--timeout=180s", timeout=200)
        report["checks"]["baseline_ready"] = "PASS"
        send_and_receive("chapter-001-before-restart")
        report["checks"]["baseline_messaging"] = "PASS"
        before = broker()
        name = before["metadata"]["name"]
        uid = before["metadata"]["uid"]
        started = time.monotonic()
        kubectl("delete", "pod", name, "--wait=false", timeout=45)
        report["checks"]["pod_restarted"] = "PASS"
        deadline = time.monotonic() + 360
        while time.monotonic() < deadline:
            try:
                after = broker()
                if (after["metadata"]["uid"] != uid and
                    after["status"].get("phase") == "Running" and
                    all(c.get("ready") for c in after["status"].get("containerStatuses", []))):
                    break
            except RuntimeError:
                pass
            time.sleep(5)
        else:
            raise RuntimeError("Replacement broker pod not ready within 360 seconds")
        kubectl("wait", "kafka/qa-kafka", "--for=condition=Ready", "--timeout=240s", timeout=260)
        report["checks"]["reconciliation"] = "PASS"
        # Ephemeral storage is intentionally used: topic may be recreated by Strimzi.
        kubectl("wait", "kafkatopic/qa-smoke", "--for=condition=Ready", "--timeout=180s", timeout=200)
        # Consumer --from-beginning may see baseline record if ephemeral storage survives.
        # Use a unique topic for post-recovery validation to avoid ambiguous old offsets.
        new_topic = "qa-recovery"
        pod = broker()["metadata"]["name"]
        base = ("exec", "-i", pod, "-c", "kafka", "--")
        cli = "/opt/kafka/bin/"
        kubectl(*base, cli+"kafka-topics.sh", "--bootstrap-server",
                "qa-kafka-kafka-bootstrap:9092", "--create", "--if-not-exists",
                "--topic", new_topic, "--partitions", "1", "--replication-factor", "1")
        message = "chapter-001-after-restart"
        kubectl(*base, cli+"kafka-console-producer.sh", "--bootstrap-server",
                "qa-kafka-kafka-bootstrap:9092", "--topic", new_topic,
                data=message+"\n", timeout=75)
        output = kubectl(*base, cli+"kafka-console-consumer.sh", "--bootstrap-server",
                         "qa-kafka-kafka-bootstrap:9092", "--topic", new_topic,
                         "--from-beginning", "--max-messages", "1", "--timeout-ms", "45000", timeout=75)
        if output.strip() != message:
            raise RuntimeError(f"Post-recovery message mismatch: {output.strip()!r}")
        report["checks"]["post_recovery_messaging"] = "PASS"
        report["recovery_seconds"] = round(time.monotonic()-started, 1)
        report["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        report["error"] = str(exc)[:1400]
        print(f"Chapter 001 recovery failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        print(f"Chapter 001 recovery: {report['status']} | {OUT}")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
