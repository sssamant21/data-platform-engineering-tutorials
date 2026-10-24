#!/usr/bin/env python3
"""Chapter 007 KRaft quorum status, voter mapping, one-Pod fault and recovery."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha"
OUT = Path("kafka/qa/evidence/chapter-007-runtime.json")

def k(*args, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1300:]}")
    return p.stdout

def pods():
    return [p for p in json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}",
                                  "-o", "json"))["items"] if "dual-role" in p["metadata"]["name"]]

def quorum(pod, mode="status"):
    return k("exec", pod, "-c", "kafka", "--",
             "/opt/kafka/bin/kafka-metadata-quorum.sh",
             "--bootstrap-server", f"{CLUSTER}-kafka-bootstrap:9092",
             "describe", f"--{mode}", timeout=90)

def fields(raw):
    return dict(re.findall(r"(?m)^([A-Za-z][A-Za-z0-9]*):\s*(.+?)\s*$", raw))

def main():
    report = {"chapter": "007", "status": "FAIL", "certification": "NOT_CERTIFIED",
              "timestamp": datetime.now(timezone.utc).isoformat(), "checks": {},
              "limitations": ["Disposable combined controller/broker Pods; no dedicated-controller topology.",
                              "Ephemeral storage; metadata durability after disk loss not tested.",
                              "Single controller-Pod failure only; no quorum-loss injection."]}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"], check=True,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=600s", timeout=630)
        ps = pods()
        if len(ps) != 3 or any(p["status"].get("phase") != "Running" for p in ps):
            raise RuntimeError("Requires exactly three running controller/broker Pods")
        names = sorted(p["metadata"]["name"] for p in ps)
        pools = json.loads(k("get", "kafkanodepool", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
        if not any({"controller", "broker"}.issubset(set(p["spec"]["roles"])) and p["spec"]["replicas"] == 3 for p in pools):
            raise RuntimeError("Three-controller KafkaNodePool not present")
        report["checks"]["three_controller_roles"] = "PASS"
        baseline = quorum(names[0])
        status = fields(baseline)
        voters = re.findall(r"\b\d+\b", status.get("CurrentVoters", ""))
        if len(voters) != 3 or len(set(voters)) != 3:
            raise RuntimeError(f"Expected three distinct quorum voters: {baseline[-1200:]}")
        if not status.get("LeaderId") or not status.get("HighWatermark"):
            raise RuntimeError(f"Missing leader or high watermark: {baseline[-1200:]}")
        report["checks"]["three_voters_leader_high_watermark"] = "PASS"
        report["quorum_before"] = baseline[-2500:]
        replication = quorum(names[0], "replication")
        if "Lag" not in replication or "NodeId" not in replication:
            raise RuntimeError(f"Quorum replication columns missing: {replication[-1000:]}")
        report["checks"]["metadata_replication_visible"] = "PASS"
        report["replication_before"] = replication[-2500:]
        # Stop one controller/broker only in the explicitly scoped disposable kind context.
        target = names[-1]
        report["fault_target"] = target
        k("delete", "pod", target, "--wait=false", timeout=45)
        report["checks"]["single_controller_pod_fault"] = "PASS"
        deadline = time.monotonic() + 420
        recovered = False
        while time.monotonic() < deadline:
            time.sleep(10)
            try:
                ps2 = pods()
                healthy = (len(ps2) == 3 and all(
                    p["status"].get("phase") == "Running"
                    and p["status"].get("containerStatuses")
                    and all(c.get("ready") for c in p["status"]["containerStatuses"])
                    for p in ps2))
                if not healthy:
                    continue
                after = quorum(sorted(p["metadata"]["name"] for p in ps2)[0])
                fs = fields(after)
                voter_ids = re.findall(r"\b\d+\b", fs.get("CurrentVoters", ""))
                if len(set(voter_ids)) == 3 and fs.get("LeaderId") and fs.get("HighWatermark"):
                    report["quorum_after"] = after[-2500:]
                    report["replication_after"] = quorum(sorted(p["metadata"]["name"] for p in ps2)[0], "replication")[-2500:]
                    recovered = True
                    break
            except (RuntimeError, KeyError, ValueError):
                continue
        if not recovered:
            raise RuntimeError("Controller quorum failed to return to healthy three-voter status")
        report["checks"]["quorum_restored"] = "PASS"
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError) as exc:
        report["error"] = str(exc)[:1700]
        print(f"Chapter 007 acceptance failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 007: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
