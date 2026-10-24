#!/usr/bin/env python3
"""Chapter 010 bounded capstone on disposable three-node combined-role Strimzi."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha", "ch010-capstone"
OUT = Path("kafka/qa/evidence/chapter-010-runtime.json")
EVENTS = [f"capstone-{i:03d}" for i in range(1, 7)]

def k(*args, data=None, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1100:]}")
    return p.stdout

def pods():
    return [p for p in json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
            if "dual-role" in p["metadata"]["name"]]

def cli(pod, command, *args, data=None, timeout=90):
    return k("exec", "-i", pod, "-c", "kafka", "--",
             f"/opt/kafka/bin/kafka-{command}.sh", "--bootstrap-server",
             f"{CLUSTER}-kafka-bootstrap:9092", *args, data=data, timeout=timeout)

def isr_metadata(pod):
    desc = cli(pod, "topics", "--describe", "--topic", TOPIC)
    rows = re.findall(r"\bPartition:\s*(\d+).*?\bReplicas:\s*([\d,]+).*?\bIsr:\s*([\d,]+)", desc)
    if len(rows) != 3 or any(len(set(rep.split(","))) != 3 for _, rep, _ in rows):
        raise RuntimeError(f"Topic not RF3 across three partitions: {desc[-1000:]}")
    return desc, all(len(set(isr.split(","))) == 3 for _, _, isr in rows)

def main():
    report = {"chapter": "010", "timestamp": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Three combined-role ephemeral nodes, not six dedicated controller/broker Pods.",
                              "No PVC durability or multi-worker failure-domain validation.",
                              "Security, observability, and production upgrade acceptance remain pending."]}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"], check=True,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=600s", timeout=630)
        ps = pods()
        if len(ps) != 3 or any(p["status"].get("phase") != "Running" for p in ps):
            raise RuntimeError("Requires exactly three healthy combined-role Pods")
        names = sorted(p["metadata"]["name"] for p in ps)
        report["checks"]["cluster_topology_ready"] = "PASS"
        quorum = cli(names[0], "metadata-quorum", "describe", "--status")
        if not re.search(r"(?m)^LeaderId:\s*\d+", quorum):
            raise RuntimeError("Metadata quorum leader missing")
        report["checks"]["kraft_metadata_leader"] = "PASS"
        report["quorum_before"] = quorum[-1800:]
        manifest = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                    "metadata": {"name": TOPIC, "labels": {"strimzi.io/cluster": CLUSTER}},
                    "spec": {"partitions": 3, "replicas": 3,
                             "config": {"min.insync.replicas": 2, "retention.ms": 600000}}}
        k("apply", "--dry-run=server", "-f", "-", data=json.dumps(manifest))
        k("apply", "-f", "-", data=json.dumps(manifest))
        k("wait", "--for=condition=Ready", f"kafkatopic/{TOPIC}", "--timeout=180s", timeout=200)
        desc, full = isr_metadata(names[0])
        if not full:
            raise RuntimeError("ISR3 prerequisite failed; refusing broker fault")
        report["checks"]["topic_rf3_minisr2_isr3"] = "PASS"
        report["topic_before"] = desc[-2000:]
        cli(names[0], "console-producer", "--topic", TOPIC,
            "--producer-property", "acks=all", data="\n".join(EVENTS) + "\n")
        report["checks"]["acks_all_six_events"] = "PASS"
        def consume(pod, group):
            out = cli(pod, "console-consumer", "--topic", TOPIC,
                      "--group", group, "--from-beginning", "--max-messages", "6",
                      "--timeout-ms", "45000", timeout=85)
            records = [line.strip() for line in out.splitlines() if line.strip()]
            if len(records) != 6 or set(records) != set(EVENTS):
                raise RuntimeError(f"Business event reconciliation failed: {records!r}")
        consume(names[0], "qa-ch010-primary")
        report["checks"]["primary_event_reconciliation"] = "PASS"
        target = names[-1]
        report["fault_target"] = target
        k("delete", "pod", target, "--wait=false", timeout=45)
        report["checks"]["single_broker_failure"] = "PASS"
        recovered = False
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline:
            time.sleep(10)
            try:
                ps2 = pods()
                if len(ps2) != 3 or not all(p["status"].get("phase") == "Running"
                        and p["status"].get("containerStatuses")
                        and all(c.get("ready") for c in p["status"]["containerStatuses"]) for p in ps2):
                    continue
                desc, full = isr_metadata(sorted(p["metadata"]["name"] for p in ps2)[0])
                if full:
                    report["topic_after"] = desc[-2000:]
                    recovered = True
                    break
            except (RuntimeError, KeyError, ValueError):
                continue
        if not recovered:
            raise RuntimeError("Full ISR failed to recover")
        report["checks"]["full_isr_restored"] = "PASS"
        active = sorted(p["metadata"]["name"] for p in pods())[0]
        consume(active, "qa-ch010-replay")
        report["checks"]["new_group_replay_reconciled"] = "PASS"
        report["verified_events"] = EVENTS
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        report["error"] = str(exc)[:1500]
        print(f"Chapter 010 failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 010: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
