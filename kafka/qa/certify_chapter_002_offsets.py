#!/usr/bin/env python3
"""Chapter 002 offset/replay acceptance using Kafka's Java consumer with commitSync."""
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

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

def consume_java(group, count, reset, expected, timeout=150):
    # Source and classes are placed only in disposable Kafka Pods.
    pod = broker()
    source = JAVA.replace("__GROUP__", group).replace("__COUNT__", str(count)).replace("__RESET__", reset)
    k("exec", "-i", pod, "-c", "kafka", "--", "sh", "-c",
      "cat > /tmp/Chapter002Commit.java", data=source, timeout=30)
    # Strimzi Kafka images include the Kafka runtime jars. Java source-file mode
    # uses the runtime classpath, avoiding a separate build tool.
    output = k("exec", pod, "-c", "kafka", "--", "sh", "-c",
               "java -cp '/opt/kafka/libs/*' /tmp/Chapter002Commit.java",
               timeout=timeout)
    events = [line[6:] for line in output.splitlines() if line.startswith("EVENT:")]
    if events != expected:
        raise RuntimeError(f"Consumer returned {events!r}, expected {expected!r}")
    if "COMMIT_OK" not in output:
        raise RuntimeError("commitSync acknowledgement not observed")
    return output

JAVA = r'''
import java.time.Duration;
import java.util.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.serialization.StringDeserializer;
public class Chapter002Commit {
  public static void main(String[] args) throws Exception {
    Properties p = new Properties();
    p.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "qa-six-kafka-bootstrap:9092");
    p.put(ConsumerConfig.GROUP_ID_CONFIG, "__GROUP__");
    p.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
    p.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
    p.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
    p.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "__RESET__");
    try (KafkaConsumer<String,String> consumer = new KafkaConsumer<>(p)) {
      consumer.subscribe(Collections.singletonList("qa-ch002-ordering"));
      List<String> received = new ArrayList<>();
      long deadline = System.nanoTime() + Duration.ofSeconds(90).toNanos();
      while (received.size() < __COUNT__ && System.nanoTime() < deadline) {
        ConsumerRecords<String,String> batch = consumer.poll(Duration.ofSeconds(2));
        for (ConsumerRecord<String,String> record : batch) {
          received.add(record.value());
        }
      }
      if (received.size() != __COUNT__) {
        throw new IllegalStateException("Expected __COUNT__ records, got " + received.size());
      }
      consumer.commitSync(Duration.ofSeconds(20));
      for (String item : received) System.out.println("EVENT:" + item);
      System.out.println("COMMIT_OK");
    }
  }
}
'''

def main():
    result = {"chapter": "002", "lab": "explicit-commit-offset-recovery",
              "status": "FAIL", "checks": {},
              "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    try:
        ctx = subprocess.run(["kubectl", "config", "current-context"],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if ctx != CTX:
            raise RuntimeError(f"Unsafe context: {ctx!r}")
        k("wait", "kafka/qa-six", "--for=condition=Ready", "--timeout=900s", timeout=930)
        k("wait", "kafkatopic/"+TOPIC, "--for=condition=Ready", "--timeout=240s", timeout=260)
        # Fresh isolated topic per workflow; unique consumer groups per execution.
        prefix = "ch002-"+uuid.uuid4().hex[:10]
        initial = [prefix+"-baseline-"+str(i) for i in range(3)]
        cli("kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all", "--property", "parse.key=true", "--property", "key.separator=|",
            data="\n".join("stable-key|"+v for v in initial)+"\n")
        result["checks"]["baseline_produced"] = "PASS"
        group = "ch002-"+uuid.uuid4().hex[:10]
        consume_java(group, 3, "earliest", initial)
        result["checks"]["explicit_commit_sync"] = "PASS"
        offsets = cli("kafka-consumer-groups.sh", "--describe", "--group", group)
        if "CURRENT-OFFSET" not in offsets or not any(
            line.strip().startswith(group) and line.split()[3].isdigit()
            for line in offsets.splitlines()):
            raise RuntimeError("Committed offset not visible in consumer-group description: "+offsets[-900:])
        result["checks"]["committed_offsets_visible"] = "PASS"
        followup = prefix+"-after-restart"
        cli("kafka-console-producer.sh", "--topic", TOPIC,
            "--producer-property", "acks=all", "--property", "parse.key=true", "--property", "key.separator=|",
            data="stable-key|"+followup+"\n")
        consume_java(group, 1, "earliest", [followup])
        result["checks"]["resume_after_restart"] = "PASS"
        consume_java("ch002-replay-"+uuid.uuid4().hex[:10], 4, "earliest", initial+[followup])
        result["checks"]["fresh_group_replay"] = "PASS"
        result["group"] = group
        result["status"] = "PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        result["error"] = str(e)[:1400]
        print("Chapter 002 offset lab failed: "+str(e), file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print("Chapter 002 offset lab: "+result["status"])
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
