#!/usr/bin/env python3
"""Chapter 002 Phase 6.3: verify consumer-group partition reassignment."""
import json
import subprocess
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

CTX, NS = "kind-kafka-qa", "kafka-qa"
TOPIC, BOOT = "qa-ch002-ordering", "qa-six-kafka-bootstrap:9092"
OUT = Path("kafka/qa/evidence/chapter-002-rebalance-result.json")
JAVA = Path("kafka/qa/runtime/Chapter002Rebalance.java")

def k(*args, data=None, timeout=120):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-1400:]}")
    return p.stdout

def broker():
    items = json.loads(k("get", "pods", "-l", "strimzi.io/cluster=qa-six", "-o", "json"))["items"]
    matches = [p["metadata"]["name"] for p in items
               if "-brokers-" in p["metadata"]["name"]
               and p["status"].get("phase") == "Running"
               and any(c.get("name") == "kafka" and c.get("ready")
                       for c in p["status"].get("containerStatuses", []))]
    if not matches:
        raise RuntimeError("No ready Kafka broker Pod")
    return sorted(matches)[0]

def main():
    result = {"chapter": "002", "lab": "consumer-group-restart-reassignment",
              "status": "FAIL", "checks": {},
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Consumer-group partition assignment; NOT Kafka broker partition replica reassignment."}
    try:
        context = subprocess.run(["kubectl", "config", "current-context"],
                                 check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        if context != CTX:
            raise RuntimeError(f"Unsafe Kubernetes context: {context}")
        k("wait", "kafka/qa-six", "--for=condition=Ready", "--timeout=900s", timeout=930)
        k("wait", "kafkatopic/"+TOPIC, "--for=condition=Ready", "--timeout=240s", timeout=260)
        pod = broker()
        meta = k("exec", pod, "-c", "kafka", "--", "/opt/kafka/bin/kafka-topics.sh",
                 "--bootstrap-server", BOOT, "--describe", "--topic", TOPIC)
        if "PartitionCount: 3" not in meta:
            raise RuntimeError("Expected a three-partition topic: "+meta[-700:])
        result["checks"]["three_partition_topic"] = "PASS"
        run = uuid.uuid4().hex[:12]
        source = JAVA.read_text(encoding="utf-8").replace("__RUN__", run)
        k("exec", "-i", pod, "-c", "kafka", "--", "sh", "-c",
          "cat > /tmp/Chapter002Rebalance.java", data=source, timeout=30)
        output = k("exec", pod, "-c", "kafka", "--", "sh", "-c",
                   "java -cp '/opt/kafka/libs/*' /tmp/Chapter002Rebalance.java",
                   timeout=300)
        required = ["single_consumer_three_partitions", "balanced_group_assignment",
                    "survivor_reassigned_three_partitions", "replacement_consumer_rebalance"]
        for check in required:
            if "CHECK:"+check+":PASS" not in output:
                raise RuntimeError("Missing assertion "+check+" in Java output: "+output[-1200:])
            result["checks"][check] = "PASS"
        if "REBALANCE_OK" not in output:
            raise RuntimeError("Java test did not complete")
        result["group"] = "ch002-rebalance-"+run
        result["assignment_evidence"] = [line for line in output.splitlines()
                                          if line.startswith("ASSIGNMENTS:")]
        result["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        result["error"] = str(e)[:1600]
        print("Chapter 002 rebalance failed: "+str(e), file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print("Chapter 002 rebalance: "+result["status"])
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
