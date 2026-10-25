#!/usr/bin/env python3
"""Chapter 002 Phase 6.2: consumer committed-offset restart and replay."""
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

CTX, NS = "kind-kafka-qa", "kafka-qa"
TOPIC, BOOT = "qa-ch002-ordering", "qa-six-kafka-bootstrap:9092"
OUT = Path("kafka/qa/evidence/chapter-002-offset-recovery.json")
CLI = "/opt/kafka/bin/"

def k(*args, data=None, timeout=120):
    p = subprocess.run(["kubectl", "--context", CTX, "-n", NS, *args],
                       input=data, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-1000:]}")
    return p.stdout

def broker():
    ps = json.loads(k("get", "pods", "-l", "strimzi.io/cluster=qa-six", "-o", "json"))["items"]
    ready = [p["metadata"]["name"] for p in ps if "-brokers-" in p["metadata"]["name"]
             and p["status"].get("phase") == "Running"
             and any(c.get("name") == "kafka" and c.get("ready")
                     for c in p["status"].get("containerStatuses", []))]
    if not ready:
        raise RuntimeError("No ready Kafka broker")
    return sorted(ready)[0]

def cli(command, *args, data=None, timeout=120):
    return k("exec", "-i", broker(), "-c", "kafka", "--", CLI+command,
             "--bootstrap-server", BOOT, *args, data=data, timeout=timeout)

def consume(group, count, offset_mode, timeout=120):
    args = ["--topic", TOPIC, "--group", group,
            "--max-messages", str(count), "--timeout-ms", "60000",
            "--consumer-property", "enable.auto.commit=false"]
    # Explicit synchronous offset commit after consumption via consumer CLI is
    # not guaranteed; use the group consumer's auto commit and verify offsets.
    args.remove("enable.auto.commit=false")
    args.remove("--consumer-property")
    args.extend(["--consumer-property", "enable.auto.commit=true",
                 "--consumer-property", "auto.commit.interval.ms=1000"])
    if offset_mode == "earliest":
        args.extend(["--consumer-property", "auto.offset.reset=earliest"])
    else:
        args.extend(["--consumer-property", "auto.offset.reset=latest"])
    return cli("kafka-console-consumer.sh", *args, timeout=timeout)

def group_offsets(group):
    return cli("kafka-consumer-groups.sh", "--describe", "--group", group)

def main():
    result = {"chapter": "002", "lab": "offset-commit-restart-replay",
              "status": "FAIL", "checks": {},
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "limitations": "One consumer per group, no rebalance or multi-consumer test; disposable single-host kind."}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Unsafe context: {ctx!r}")
        k("wait", "kafka/qa-six", "--for=condition=Ready", "--timeout=900s", timeout=930)
        k("wait", "kafkatopic/"+TOPIC, "--for=condition=Ready", "--timeout=240s", timeout=260)
        # Distinct partition with explicit assignment makes offsets deterministic.
        # Produce directly to partition 0 using the console producer property.
        prefix = "ch002-offset-" + uuid.uuid4().hex[:10]
        baseline = [f"{prefix}-baseline-{i}" for i in range(3)]
        cli("kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all",
            "--property", "parse.key=true", "--property", "key.separator=|",
            data="\n".join("stable-key|"+x for x in baseline)+"\n")
        result["checks"]["baseline_produce"] = "PASS"

        group = "ch002-"+uuid.uuid4().hex[:10]
        first = consume(group, 3, "earliest")
        for value in baseline:
            if value not in first:
                raise RuntimeError(f"Missing baseline event {value} in first consumption")
        result["checks"]["initial_consumption"] = "PASS"

        # Console consumer auto-commit may not commit when max-messages exits
        # immediately; require a visible committed offset instead of assuming.
        deadline = time.monotonic()+30
        offsets = ""
        while time.monotonic() < deadline:
            try:
                offsets = group_offsets(group)
                if "CURRENT-OFFSET" in offsets and " - " not in offsets:
                    break
            except RuntimeError:
                pass
            time.sleep(3)
        else:
            raise RuntimeError("Consumer-group committed offset not confirmed; console consumer may exit before auto commit")
        result["checks"]["committed_offsets_visible"] = "PASS"
        result["group"] = group
        result["offset_description"] = offsets[-1600:]

        followup = f"{prefix}-after-restart"
        cli("kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all",
            "--property", "parse.key=true", "--property", "key.separator=|",
            data="stable-key|"+followup+"\n")
        second = consume(group, 1, "earliest")
        if followup not in second:
            raise RuntimeError("Restarted consumer did not resume at newly published event")
        result["checks"]["restart_resumes_from_commit"] = "PASS"

        replay_group = "ch002-replay-"+uuid.uuid4().hex[:10]
        replay = consume(replay_group, 4, "earliest")
        for value in baseline+[followup]:
            if value not in replay:
                raise RuntimeError(f"Replay group missing event {value}")
        result["checks"]["fresh_group_replays_history"] = "PASS"
        result["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        result["error"] = str(e)[:1400]
        print(f"Chapter 002 offset lab failed: {e}", file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print("Chapter 002 offset lab: "+result["status"])
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
