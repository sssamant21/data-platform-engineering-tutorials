#!/usr/bin/env python3
"""Chapter 008: safe operator-owned broker config reconciliation and rollback."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER = "kind-kafka-qa", "kafka-qa", "qa-kafka"
OUT = Path("kafka/qa/evidence/chapter-008-runtime.json")
SETTING = "log.cleaner.threads"

def k(*args, data=None, timeout=100):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1100:]}")
    return p.stdout

def main():
    report = {"chapter": "008", "timestamp": datetime.now(timezone.utc).isoformat(),
              "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
              "limitations": ["Single-broker disposable lab, not a multi-node rolling-change test.",
                              "Does not mutate broker dynamic overrides directly; Strimzi remains source of truth."]}
    baseline = None
    changed = False
    try:
        current = subprocess.run(["kubectl", "config", "current-context"], capture_output=True,
                                 text=True, check=True, timeout=10).stdout.strip()
        if current != CTX:
            raise RuntimeError(f"Refusing context {current!r}")
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=420s", timeout=445)
        cr = json.loads(k("get", "kafka", CLUSTER, "-o", "json"))
        cfg = cr["spec"]["kafka"].get("config", {})
        baseline = cfg.get(SETTING)
        report["original_setting"] = baseline
        report["checks"]["baseline_cr_read"] = "PASS"
        # Reconcile one safe, supported non-storage setting using Strimzi's CR.
        target = 2 if baseline != 2 else 1
        patch = {"spec": {"kafka": {"config": {SETTING: target}}}}
        k("patch", "kafka", CLUSTER, "--type=merge", "-p", json.dumps(patch),
          "--dry-run=server", "-o", "json")
        report["checks"]["server_dry_run"] = "PASS"
        k("patch", "kafka", CLUSTER, "--type=merge", "-p", json.dumps(patch))
        changed = True
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=420s", timeout=445)
        effective = json.loads(k("get", "kafka", CLUSTER, "-o", "json"))
        if effective["spec"]["kafka"]["config"].get(SETTING) != target:
            raise RuntimeError("Desired Kafka CR setting not reconciled")
        report["checks"]["desired_state_readback"] = "PASS"
        pods = json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
        brokers = [p["metadata"]["name"] for p in pods if "dual-role" in p["metadata"]["name"]
                   and p["status"].get("phase") == "Running"]
        if len(brokers) != 1:
            raise RuntimeError("Expected one running QA broker")
        output = k("exec", brokers[0], "-c", "kafka", "--",
                   "/opt/kafka/bin/kafka-configs.sh", "--bootstrap-server",
                   f"{CLUSTER}-kafka-bootstrap:9092", "--entity-type", "brokers",
                   "--entity-default", "--describe", "--all", timeout=90)
        report["broker_config_excerpt"] = output[:1800]
        report["checks"]["broker_config_cli_readable"] = "PASS"
        report["status"] = "PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError, KeyError) as exc:
        report["error"] = str(exc)[:1600]
        print(f"Chapter 008 failure: {exc}", file=sys.stderr)
    finally:
        if changed:
            try:
                # JSON patch remove restores an originally absent setting, avoiding null config.
                if baseline is None:
                    k("patch", "kafka", CLUSTER, "--type=json", "-p",
                      json.dumps([{"op": "remove", "path": "/spec/kafka/config/log.cleaner.threads"}]))
                else:
                    k("patch", "kafka", CLUSTER, "--type=merge", "-p",
                      json.dumps({"spec": {"kafka": {"config": {SETTING: baseline}}}}))
                k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=420s", timeout=445)
                restored = json.loads(k("get", "kafka", CLUSTER, "-o", "json"))
                if restored["spec"]["kafka"].get("config", {}).get(SETTING) != baseline:
                    raise RuntimeError("Rollback readback mismatch")
                report["checks"]["desired_state_rollback"] = "PASS"
            except (OSError, subprocess.SubprocessError, RuntimeError, KeyError) as exc:
                report["checks"]["desired_state_rollback"] = "FAIL"
                report["rollback_error"] = str(exc)[:1200]
                report["status"] = "FAIL"
        if report["status"] == "PASS":
            report["certification"] = "PARTIAL_RUNTIME_PASS"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 008: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
