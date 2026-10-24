#!/usr/bin/env python3
"""Chapter 004: safe three-broker ISR and controlled broker Pod recovery."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha", "ch004-replication"
OUT = Path("kafka/qa/evidence/chapter-004-runtime.json")
EVENTS = ["ch004-before-failure", "ch004-after-recovery"]

def k(*args, data=None, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1200:]}")
    return p.stdout

def pods():
    items = json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
    return [p for p in items if "dual-role" in p["metadata"]["name"]]

def topic_metadata(pod):
    return k("exec", pod, "-c", "kafka", "--", "/opt/kafka/bin/kafka-topics.sh",
             "--bootstrap-server", f"{CLUSTER}-kafka-bootstrap:9092",
             "--describe", "--topic", TOPIC)

def parse_isr(desc):
    match = re.search(r"\bIsr:\s*([0-9,]+)", desc)
    if not match:
        raise RuntimeError(f"No ISR found: {desc[-700:]}")
    return set(match.group(1).split(","))

def main():
    report = {"chapter": "004", "lab_ids": ["KAFKA-004-A", "KAFKA-004-B", "KAFKA-004-C"],
              "time_utc": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Ephemeral broker storage; does not certify PVC durability.",
                              "Tests one controlled broker-Pod restart, not controller quorum loss or regional failure."]}
    try:
        current = subprocess.run(["kubectl", "config", "current-context"], text=True,
                                 capture_output=True, check=True, timeout=10).stdout.strip()
        if current != CTX:
            raise RuntimeError(f"Refusing context {current!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=600s", timeout=630)
        k("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}", "--timeout=180s", timeout=200)
        ps = pods()
        if len(ps) != 3 or any(p["status"].get("phase") != "Running" for p in ps):
            raise RuntimeError("Expected exactly three running QA broker/controller Pods")
        names = sorted(p["metadata"]["name"] for p in ps)
        report["checks"]["three_brokers_running"] = "PASS"
        desc = topic_metadata(names[0])
        if not re.search(r"ReplicationFactor:\s*3\b", desc) or not re.search(r"PartitionCount:\s*1\b", desc):
            raise RuntimeError(f"Unexpected RF or partitions: {desc[-800:]}")
        before = parse_isr(desc)
        if len(before) != 3:
            raise RuntimeError(f"Unsafe to inject fault: ISR not healthy ({before})")
        report["checks"]["rf3_full_isr_baseline"] = "PASS"
        report["before_metadata"] = desc[-1500:]
        base = ["exec", "-i", names[0], "-c", "kafka", "--"]
        bs = f"{CLUSTER}-kafka-bootstrap:9092"
        k(*base, "/opt/kafka/bin/kafka-console-producer.sh",
          "--bootstrap-server", bs, "--topic", TOPIC,
          "--producer-property", "acks=all", data=EVENTS[0] + "\n", timeout=90)
        report["checks"]["baseline_acknowledged_write"] = "PASS"
        # Never target any Pod outside this ephemeral kind cluster and QA namespace.
        target = names[-1]
        report["fault_target"] = target
        k("delete", "pod", target, "--wait=false", timeout=40)
        report["checks"]["qa_broker_pod_failure_injected"] = "PASS"
        # Wait for Kubernetes to recreate the broker and ISR to fully converge.
        deadline = time.monotonic() + 420
        recovered = False
        while time.monotonic() < deadline:
            time.sleep(10)
            try:
                current_pods = pods()
                ready = len(current_pods) == 3 and all(
                    p["status"].get("phase") == "Running"
                    and all(c.get("ready") for c in p["status"].get("containerStatuses", []))
                    and p["status"].get("containerStatuses")
                    for p in current_pods)
                if not ready:
                    continue
                desc_after = topic_metadata(sorted(p["metadata"]["name"] for p in current_pods)[0])
                if len(parse_isr(desc_after)) == 3:
                    recovered = True
                    report["after_metadata"] = desc_after[-1500:]
                    break
            except (RuntimeError, ValueError, KeyError):
                continue
        if not recovered:
            raise RuntimeError("Three-broker ISR did not converge before timeout")
        report["checks"]["broker_recreated_and_full_isr_restored"] = "PASS"
        active = sorted(p["metadata"]["name"] for p in pods())[0]
        base = ["exec", "-i", active, "-c", "kafka", "--"]
        k(*base, "/opt/kafka/bin/kafka-console-producer.sh",
          "--bootstrap-server", bs, "--topic", TOPIC,
          "--producer-property", "acks=all", data=EVENTS[1] + "\n", timeout=90)
        output = k(*base, "/opt/kafka/bin/kafka-console-consumer.sh",
                   "--bootstrap-server", bs, "--topic", TOPIC,
                   "--from-beginning", "--max-messages", "2",
                   "--timeout-ms", "45000", timeout=90)
        actual = [s.strip() for s in output.splitlines() if s.strip()]
        if actual != EVENTS:
            raise RuntimeError(f"Event reconciliation failed: {actual!r}")
        report["checks"]["pre_post_event_reconciliation"] = "PASS"
        report["verified_events"] = actual
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        report["error"] = str(exc)[:1500]
        print(f"Chapter 004 failure: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 004: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
