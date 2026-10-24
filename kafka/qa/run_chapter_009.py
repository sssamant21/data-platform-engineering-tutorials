#!/usr/bin/env python3
"""Chapter 009 guarded Strimzi rolling maintenance and single broker recovery."""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER, TOPIC = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha", "ch004-replication"
OUT = Path("kafka/qa/evidence/chapter-009-runtime.json")

def k(*args, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1100:]}")
    return p.stdout

def pods():
    return [p for p in json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
            if "dual-role" in p["metadata"]["name"]]

def describe(pod):
    return k("exec", pod, "-c", "kafka", "--", "/opt/kafka/bin/kafka-topics.sh",
             "--bootstrap-server", f"{CLUSTER}-kafka-bootstrap:9092",
             "--describe", "--topic", TOPIC)

def isr(desc):
    m = re.search(r"\bIsr:\s*([\d,]+)", desc)
    if not m:
        raise RuntimeError("Topic ISR missing")
    return set(m.group(1).split(","))

def healthy():
    ps = pods()
    if len(ps) != 3 or not all(p["status"].get("phase") == "Running"
                                and p["status"].get("containerStatuses")
                                and all(c.get("ready") for c in p["status"]["containerStatuses"])
                                for p in ps):
        return False
    return len(isr(describe(sorted(p["metadata"]["name"] for p in ps)[0]))) == 3

def wait_healthy(timeout=420):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if healthy():
                return
        except (RuntimeError, KeyError, ValueError):
            pass
        time.sleep(10)
    raise RuntimeError("Three brokers and full ISR did not recover before timeout")

def main():
    report = {"chapter": "009", "timestamp": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Uses ephemeral volumes; persistent-storage maintenance not tested.",
                              "No Kafka/Strimzi version upgrade or metadata feature-level change performed.",
                              "Operator rolling restart annotation behavior must be confirmed by execution."]}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"], text=True,
                             capture_output=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Refusing context {ctx!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=600s", timeout=630)
        wait_healthy(180)
        report["checks"]["pre_maintenance_rf3_isr3"] = "PASS"
        ps = pods()
        target = sorted(ps, key=lambda p: p["metadata"]["name"])[-1]
        name = target["metadata"]["name"]
        uid_before = target["metadata"]["uid"]
        report["maintenance_target"] = name
        # Strimzi 0.47 supported manual rolling update annotation on an individual Pod.
        k("annotate", "pod", name, "strimzi.io/manual-rolling-update=true", "--overwrite")
        deadline = time.monotonic() + 420
        restarted = False
        while time.monotonic() < deadline:
            time.sleep(10)
            try:
                ps2 = pods()
                match = [p for p in ps2 if p["metadata"]["name"] == name]
                if match and match[0]["metadata"]["uid"] != uid_before:
                    restarted = True
                    break
            except (RuntimeError, KeyError):
                continue
        if not restarted:
            raise RuntimeError("Operator-managed rolling restart did not recreate target Pod")
        report["checks"]["strimzi_managed_rolling_restart"] = "PASS"
        wait_healthy()
        report["checks"]["post_rolling_restart_isr3"] = "PASS"
        # Abrupt Pod loss only after full ISR and all three brokers are healthy.
        k("delete", "pod", name, "--wait=false", timeout=45)
        report["checks"]["single_pod_failure_injected"] = "PASS"
        wait_healthy()
        report["checks"]["post_failure_isr3_restored"] = "PASS"
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        report["error"] = str(exc)[:1700]
        print(f"Chapter 009 failure: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 009: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
