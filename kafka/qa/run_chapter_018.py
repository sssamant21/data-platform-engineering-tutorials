#!/usr/bin/env python3
"""Chapter 018: disposable Kubernetes Deployment group scaling acceptance."""
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kafka/qa/evidence/chapter-018-runtime.json"
BOOT = CLUSTER + "-kafka-bootstrap:9092"


def k(*args, data=None, timeout=90):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-3000:]} {p.stdout[-3000:]}")
    return p.stdout


def deployment(name, topic, group, image):
    return {"apiVersion": "apps/v1", "kind": "Deployment",
            "metadata": {"name": name}, "spec": {
                "replicas": 1, "selector": {"matchLabels": {"app": name}},
                "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxSurge": 1, "maxUnavailable": 0}},
                "template": {"metadata": {"labels": {"app": name}}, "spec": {
                    "automountServiceAccountToken": False,
                    "terminationGracePeriodSeconds": 60,
                    "containers": [{"name": "consumer", "image": image,
                        "command": ["/opt/kafka/bin/kafka-console-consumer.sh"],
                        "args": ["--bootstrap-server", BOOT, "--topic", topic,
                                 "--group", group, "--from-beginning",
                                 "--consumer-property", "group.protocol=classic",
                                 "--consumer-property", "partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor",
                                 "--consumer-property", "auto.commit.interval.ms=1000"],
                        "env": [{"name": "KAFKA_HEAP_OPTS", "value": "-Xms64m -Xmx128m"}],
                        "resources": {"requests": {"cpu": "100m", "memory": "192Mi"},
                                      "limits": {"cpu": "1", "memory": "384Mi"}}}]}}}}


def main():
    run = uuid.uuid4().hex[:12]
    name, topic, group = (f"ch018-{kind}-{run}" for kind in ("consumer", "events", "group"))
    r = {"chapter": "018", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
         "commit": os.environ.get("GITHUB_SHA"), "run_id": os.environ.get("GITHUB_RUN_ID"),
         "status": "FAIL", "certification": "NOT_CERTIFIED", "checks": {},
         "resources": {"deployment": name, "topic": topic, "group": group},
         "versions": {"kafka": "4.0.0", "strimzi": "0.47.0", "protocol": "classic/cooperative"},
         "limitations": ["Console consumers demonstrate assignment and committed lag, not application side-effect correctness or a reviewed SIGTERM handler.",
                         "No HPA/KEDA, newer consumer protocol, static membership or rebalance latency SLO validation.",
                         "Plaintext disposable lab; TLS/ACL and independent security review remain pending.",
                         "Ephemeral kind on one host is not multi-zone or enterprise certification."],
         "observations": []}
    safe = False
    try:
        context = subprocess.run(["kubectl", "config", "current-context"], check=True,
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        if context != CTX:
            raise RuntimeError("Unsafe Kubernetes context")
        # A context name alone is insufficient: require the kind control-plane container.
        node = json.loads(k("get", "node", "kafka-qa-control-plane", "-o", "json"))
        if node["metadata"].get("labels", {}).get("kubernetes.io/hostname") != "kafka-qa-control-plane":
            raise RuntimeError("Expected disposable kind node")
        safe = True
        k("wait", "--for=condition=Ready", f"kafka/{CLUSTER}", "--timeout=600s", timeout=630)
        cluster = json.loads(k("get", "kafka", CLUSTER, "-o", "json"))
        config = cluster["spec"]["kafka"]
        if config["version"] != "4.0.0" or config["config"]["min.insync.replicas"] != 2:
            raise RuntimeError("Unexpected Kafka version or durability configuration")
        pods = json.loads(k("get", "pods", "-l", f"strimzi.io/cluster={CLUSTER}", "-o", "json"))["items"]
        brokers = [p for p in pods if "-dual-role-" in p["metadata"]["name"]
                   and any(c.get("name") == "kafka" and c.get("ready") for c in p["status"].get("containerStatuses", []))]
        if len(brokers) != 3:
            raise RuntimeError("Expected three ready brokers")
        pod = brokers[0]["metadata"]["name"]
        image = next(c["image"] for c in brokers[0]["spec"]["containers"] if c["name"] == "kafka")
        r["client_image"] = image
        def cli(tool, *args, data=None):
            return k("exec", "-i", pod, "-c", "kafka", "--", f"/opt/kafka/bin/kafka-{tool}.sh",
                     "--bootstrap-server", BOOT, *args, data=data, timeout=90)
        manifest = {"apiVersion": "kafka.strimzi.io/v1beta2", "kind": "KafkaTopic",
                    "metadata": {"name": topic, "labels": {"strimzi.io/cluster": CLUSTER}},
                    "spec": {"partitions": 3, "replicas": 3,
                             "config": {"min.insync.replicas": 2, "retention.ms": 600000}}}
        k("apply", "-f", "-", data=json.dumps(manifest))
        k("wait", "--for=condition=Ready", f"kafkatopic/{topic}", "--timeout=240s", timeout=260)
        source = (ROOT / "kafka/qa/runtime/Chapter018.java").read_text(encoding="utf-8-sig")
        k("exec", "-i", pod, "-c", "kafka", "--", "sh", "-c", "cat > /tmp/Chapter018.java", data=source)
        expected = [f"{run}-event-{i}" for i in range(6)]
        cli("console-producer", "--topic", topic, "--producer-property", "acks=all",
            "--producer-property", "enable.idempotence=true", data="\n".join(expected) + "\n")
        actual = cli("console-consumer", "--topic", topic, "--group", group + "-audit",
                     "--from-beginning", "--max-messages", "6", "--timeout-ms", "45000").splitlines()
        if sorted(actual) != sorted(expected):
            raise RuntimeError(f"Event reconciliation failed: {actual!r}")
        r["checks"]["six_unique_events_reconciled"] = "PASS"
        k("apply", "-f", "-", data=json.dumps(deployment(name, topic, group, image)))
        for count in (1, 2, 4, 1):
            k("scale", f"deployment/{name}", f"--replicas={count}")
            k("rollout", "status", f"deployment/{name}", "--timeout=180s", timeout=200)
            deadline, stable, last = time.monotonic() + 120, 0, ""
            while time.monotonic() < deadline:
                try:
                    last = k("exec", pod, "-c", "kafka", "--", "java", "-Xmx128m", "-cp",
                             "/opt/kafka/libs/*", "/tmp/Chapter018.java", topic, group, str(count), timeout=65)
                    if "ASSIGNMENT_OK" not in last:
                        raise RuntimeError("Missing assignment assertion")
                    stable += 1
                    if stable == 2:
                        break
                except (RuntimeError, subprocess.TimeoutExpired) as exc:
                    last, stable = str(exc), 0
                time.sleep(2)
            if stable != 2:
                raise RuntimeError(f"Group did not converge to {count} members: {last}")
            r["observations"].append({"replicas": count, "assignment": last})
            r["checks"][f"stage_{len(r['observations'])}_{count}_members_exclusive_ownership"] = "PASS"
        deadline = time.monotonic() + 45
        while True:
            offsets = cli("consumer-groups", "--describe", "--group", group)
            rows = [line.split() for line in offsets.splitlines() if topic in line]
            if (len(rows) == 3 and all(len(row) >= 6 and row[5] == "0" and row[3].isdigit() and row[4].isdigit() for row in rows)
                    and sum(int(row[3]) for row in rows) == 6 and sum(int(row[4]) for row in rows) == 6):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Committed lag did not reach zero: " + offsets)
            time.sleep(2)
        r["offsets"] = offsets
        r["checks"]["zero_committed_lag_after_scale_down"] = "PASS"
        r["status"] = "PASS"
        r["runtime_scope"] = "SUPPORTED_ACCEPTANCE_PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        r["error"] = str(exc)
        print(str(exc), file=sys.stderr)
    finally:
        if safe:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            for label, args in (("consumer-logs", ("logs", "-l", f"app={name}", "--all-containers", "--prefix", "--tail=200", "--max-log-requests=5")),
                                ("deployment", ("get", "deployment", name, "-o", "yaml")),
                                ("pods", ("get", "pods", "-o", "wide"))):
                try:
                    (OUT.parent / f"chapter-018-{label}.txt").write_text(k(*args, timeout=20), encoding="utf-8")
                except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                    r.setdefault("diagnostic_errors", []).append(str(exc))
            for kind, resource in (("deployment", name), ("kafkatopic", topic)):
                try:
                    k("delete", kind, resource, "--ignore-not-found", "--wait=false", timeout=20)
                except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                    r.setdefault("cleanup_errors", []).append(str(exc))
                    r["status"] = "FAIL"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    return 0 if r["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
