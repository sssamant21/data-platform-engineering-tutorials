#!/usr/bin/env python3
"""Chapter 005 capstone: guarded three-broker RF3/minISR2 failure and replay."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha", "sre-capstone-orders"
OUT = Path("kafka/qa/evidence/chapter-005-runtime.json")
EVENTS = [f"order-{i:03d}:created-{i:03d}" for i in range(1, 7)]
VALUES = [event.split(":", 1)[1] for event in EVENTS]

def k(*args, data=None, timeout=100):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1100:]}")
    return p.stdout

def broker_pods():
    return [p for p in json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}",
                                  "-o", "json"))["items"] if "dual-role" in p["metadata"]["name"]]

def cli(pod, tool, *args, data=None, timeout=100):
    return k("exec", "-i", pod, "-c", "kafka", "--",
             f"/opt/kafka/bin/kafka-{tool}.sh", "--bootstrap-server",
             f"{CLUSTER}-kafka-bootstrap:9092", *args, data=data, timeout=timeout)

def describe(pod):
    return cli(pod, "topics", "--describe", "--topic", TOPIC)

def partitions(desc):
    rows = {}
    for line in desc.splitlines():
        m = re.search(r"\bPartition:\s*(\d+).*?\bLeader:\s*(\d+).*?\bReplicas:\s*([\d,]+).*?\bIsr:\s*([\d,]+)", line)
        if m:
            rows[int(m.group(1))] = {"leader": m.group(2), "replicas": set(m.group(3).split(",")),
                                     "isr": set(m.group(4).split(","))}
    if len(rows) != 3:
        raise RuntimeError(f"Expected 3 partition metadata rows, got {desc[-1000:]}")
    return rows

def consume(pod, group):
    output = cli(pod, "console-consumer", "--topic", TOPIC, "--group", group,
                 "--from-beginning", "--max-messages", "6", "--timeout-ms", "45000", timeout=85)
    records = [s.strip() for s in output.splitlines() if s.strip()]
    if len(records) != len(VALUES) or set(records) != set(VALUES):
        raise RuntimeError(f"Business event ID mismatch for {group}: {records!r}")
    return records

def main():
    report = {"chapter": "005", "lab_ids": ["KAFKA-005-A", "KAFKA-005-B", "KAFKA-005-C"],
              "time_utc": datetime.now(timezone.utc).isoformat(), "checks": {},
              "status": "FAIL", "certification": "NOT_CERTIFIED",
              "limitations": ["Ephemeral broker storage; PVC persistence gate is NOT TESTED.",
                              "No production-grade availability, independent controller quorum, or durable sink test.",
                              "Keyed events are verified by event ID, not a per-key ordering assertion."]}
    try:
        current = subprocess.run(["kubectl", "config", "current-context"], check=True,
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        if current != CTX:
            raise RuntimeError(f"Refusing context {current!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=600s", timeout=630)
        topic = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                 "metadata": {"name": TOPIC, "labels": {"strimzi.io/cluster": CLUSTER}},
                 "spec": {"partitions": 3, "replicas": 3,
                          "config": {"min.insync.replicas": 2, "retention.ms": 600000}}}
        k("apply", "-f", "-", data=json.dumps(topic))
        k("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}", "--timeout=180s", timeout=200)
        ps = broker_pods()
        if len(ps) != 3 or any(p["status"].get("phase") != "Running" for p in ps):
            raise RuntimeError("Three healthy broker/controller Pods required before fault")
        report["checks"]["three_brokers_ready"] = "PASS"
        names = sorted(p["metadata"]["name"] for p in ps)
        initial = describe(names[0])
        rows = partitions(initial)
        if not all(len(row["isr"]) == 3 and len(row["replicas"]) == 3 for row in rows.values()):
            raise RuntimeError("Unsafe to inject fault: RF3/ISR3 not satisfied")
        report["checks"]["three_partitions_rf3_isr3"] = "PASS"
        report["metadata_before"] = initial[-2500:]
        cli(names[0], "console-producer", "--topic", TOPIC,
            "--producer-property", "acks=all", "--property", "parse.key=true",
            "--property", "key.separator=:",
            data="\n".join(EVENTS) + "\n", timeout=90)
        report["checks"]["six_keyed_events_acks_all"] = "PASS"
        consume(names[0], "qa-ch005-primary")
        report["checks"]["primary_group_business_reconciliation"] = "PASS"
        # Select a broker hosting a replica; a single Pod deletion cannot break 2-of-3 quorum.
        target = names[-1]
        report["fault_target"] = target
        k("delete", "pod", target, "--wait=false", timeout=40)
        report["checks"]["one_qa_broker_failure_injected"] = "PASS"
        # Observe degradation opportunistically; recovery may happen before polling catches it.
        degraded = False
        deadline = time.monotonic() + 420
        recovered = False
        while time.monotonic() < deadline:
            time.sleep(8)
            try:
                current_ps = broker_pods()
                active = [p["metadata"]["name"] for p in current_ps
                          if p["status"].get("phase") == "Running"]
                if not active:
                    continue
                metadata = describe(active[0])
                snapshot = partitions(metadata)
                if any(len(v["isr"]) < 3 for v in snapshot.values()):
                    degraded = True
                    report["metadata_during"] = metadata[-2500:]
                healthy = (len(current_ps) == 3
                           and all(p["status"].get("phase") == "Running"
                                   and p["status"].get("containerStatuses")
                                   and all(c.get("ready") for c in p["status"]["containerStatuses"])
                                   for p in current_ps))
                if healthy and all(len(v["isr"]) == 3 for v in snapshot.values()):
                    recovered = True
                    report["metadata_after"] = metadata[-2500:]
                    break
            except (RuntimeError, ValueError, KeyError):
                continue
        report["degraded_isr_observed"] = degraded
        if not recovered:
            raise RuntimeError("ISR3 and all broker Pods did not recover")
        report["checks"]["full_isr_restored"] = "PASS"
        active = sorted(p["metadata"]["name"] for p in broker_pods())[0]
        consume(active, "qa-ch005-replay")
        report["checks"]["independent_group_replay_no_offset_reset"] = "PASS"
        report["verified_event_ids"] = EVENTS
        report["verified_consumer_values"] = VALUES
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError) as exc:
        report["error"] = str(exc)[:1600]
        print(f"Chapter 005 acceptance failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 005: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
