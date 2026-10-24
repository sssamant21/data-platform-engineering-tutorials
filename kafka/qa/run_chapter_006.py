#!/usr/bin/env python3
"""Chapter 006 bootstrap acceptance, isolated kind context only."""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

CTX, NS, CLUSTER = "kind-kafka-qa", "kafka-qa", "qa-kafka"
OUT = Path("kafka/qa/evidence/chapter-006-runtime.json")

def run(*args, data=None, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1100:]}")
    return p.stdout

def main():
    report = {"chapter": "006", "status": "FAIL", "certification": "NOT_CERTIFIED",
              "timestamp": datetime.now(timezone.utc).isoformat(), "checks": {},
              "limitations": ["Single-node ephemeral bootstrap only; persistent volumes and operator-managed restart untested.",
                              "Controller quorum resilience and multi-node failure recovery untested."]}
    try:
        current = subprocess.run(["kubectl", "config", "current-context"], check=True,
                                 text=True, capture_output=True, timeout=10).stdout.strip()
        if current != CTX:
            raise RuntimeError(f"Refusing context {current!r}")
        crds = run("get", "crd", "kafkas.kafka.strimzi.io", "kafkanodepools.kafka.strimzi.io", "-o", "json")
        if len(json.loads(crds)["items"]) != 2:
            raise RuntimeError("Missing Kafka or KafkaNodePool CRD")
        report["checks"]["strimzi_crds_installed"] = "PASS"
        deployments = json.loads(run("get", "deployment", "-o", "json"))["items"]
        if not any("strimzi-cluster-operator" in d["metadata"]["name"]
                   and d["status"].get("availableReplicas", 0) >= 1 for d in deployments):
            raise RuntimeError("Strimzi operator not available")
        report["checks"]["operator_available"] = "PASS"
        run("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=420s", timeout=445)
        kafka = json.loads(run("get", "kafka", CLUSTER, "-o", "json"))
        report["checks"]["kraft_kafka_ready"] = "PASS"
        pools = json.loads(run("get", "kafkanodepool", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
        if not pools or not any({"controller", "broker"}.issubset(set(p["spec"]["roles"])) for p in pools):
            raise RuntimeError("KRaft combined controller/broker pool missing")
        report["checks"]["kraft_node_pool_roles"] = "PASS"
        ps = json.loads(run("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
        brokers = [p["metadata"]["name"] for p in ps if "dual-role" in p["metadata"]["name"]
                   and p["status"].get("phase") == "Running"]
        if len(brokers) != 1:
            raise RuntimeError(f"Expected one bootstrap broker, found {brokers}")
        report["checks"]["broker_pod_running"] = "PASS"
        svc = json.loads(run("get", "service", f"{CLUSTER}-kafka-bootstrap", "-o", "json"))
        if not svc["spec"].get("ports"):
            raise RuntimeError("Bootstrap service missing ports")
        report["checks"]["bootstrap_service"] = "PASS"
        manifest = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                    "metadata": {"name": "ch006-bootstrap", "labels": {"strimzi.io/cluster": CLUSTER}},
                    "spec": {"partitions": 1, "replicas": 1}}
        run("apply", "--dry-run=server", "-f", "-", data=json.dumps(manifest))
        report["checks"]["topic_server_side_dry_run"] = "PASS"
        run("apply", "-f", "-", data=json.dumps(manifest))
        run("wait", "--for=condition=Ready", "kafkatopic/ch006-bootstrap",
            "--timeout=180s", timeout=200)
        report["checks"]["topic_reconciled"] = "PASS"
        base = ["exec", "-i", brokers[0], "-c", "kafka", "--"]
        bootstrap = f"{CLUSTER}-kafka-bootstrap:9092"
        run(*base, "/opt/kafka/bin/kafka-console-producer.sh", "--bootstrap-server",
            bootstrap, "--topic", "ch006-bootstrap", data="ch006-bootstrap-ok\n")
        output = run(*base, "/opt/kafka/bin/kafka-console-consumer.sh", "--bootstrap-server",
                     bootstrap, "--topic", "ch006-bootstrap", "--from-beginning",
                     "--max-messages", "1", "--timeout-ms", "45000", timeout=80)
        if [s.strip() for s in output.splitlines() if s.strip()] != ["ch006-bootstrap-ok"]:
            raise RuntimeError("Bootstrap event verification failed")
        report["checks"]["bootstrap_produce_consume"] = "PASS"
        report["status"], report["certification"] = "PASS", "PARTIAL_RUNTIME_PASS"
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as exc:
        report["error"] = str(exc)[:1400]
        print(f"Chapter 006 failed: {exc}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Chapter 006: {report['status']} ({report['certification']})")
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
