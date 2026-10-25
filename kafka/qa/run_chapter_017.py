#!/usr/bin/env python3
"""Chapter 017: isolated consumer-group offset and replay acceptance."""
import json,subprocess,sys,uuid
from datetime import datetime,timezone
from pathlib import Path

CTX,NS,CLUSTER="kind-kafka-qa","kafka-qa","qa-kafka-ha"
OUT=Path("kafka/qa/evidence/chapter-017-runtime.json")
def k(*args,input=None,timeout=90):
    p=subprocess.run(["kubectl","--context",CTX,"-n",NS,*args],input=input,
                     capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr[-1400:])
    return p.stdout
def main():
    r={"chapter":"017","timestamp":datetime.now(timezone.utc).isoformat(),
       "status":"FAIL","certification":"NOT_CERTIFIED","checks":{},
       "limitations":["Console consumer commits are client-dependent; this lab uses group CLI to verify committed offsets.",
                      "Replay uses a distinct disposable group; no active-group offset reset.",
                      "No Kubernetes consumer Job restart or application side-effect deduplication."]}
    try:
        ctx=subprocess.run(["kubectl","config","current-context"],capture_output=True,
                           text=True,check=True,timeout=10).stdout.strip()
        if ctx!=CTX:raise RuntimeError("Unsafe Kubernetes context")
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=600s",timeout=630)
        pods=json.loads(k("get","pods","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
        brokers=sorted(p["metadata"]["name"] for p in pods if "-dual-role-" in p["metadata"]["name"] and p["status"].get("phase")=="Running")
        if len(brokers)!=3:raise RuntimeError("Expected three brokers")
        pod=brokers[0]
        tag=uuid.uuid4().hex[:8]
        topic="ch017-consumer-"+tag
        group="ch017-committed-"+tag
        replay="ch017-replay-"+tag
        manifest={"apiVersion":"kafka.strimzi.io/v1beta2","kind":"KafkaTopic",
                  "metadata":{"name":topic,"labels":{"strimzi.io/cluster":CLUSTER}},
                  "spec":{"partitions":1,"replicas":3,"config":{"min.insync.replicas":2,"retention.ms":600000}}}
        k("apply","-f","-",input=json.dumps(manifest))
        k("wait","--for=condition=Ready",f"kafkatopic/{topic}","--timeout=240s",timeout=260)
        r["checks"]["disposable_rf3_topic_ready"]="PASS"
        values=[f"ch017-{tag}-{i}" for i in range(6)]
        k("exec","-i",pod,"-c","kafka","--","/opt/kafka/bin/kafka-console-producer.sh",
          "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092","--topic",topic,
          "--producer-property","acks=all",input="\n".join(values)+"\n",timeout=120)
        r["checks"]["six_records_produced"]="PASS"
        def consume(g):
            return k("exec",pod,"-c","kafka","--","/opt/kafka/bin/kafka-console-consumer.sh",
                     "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092","--topic",topic,
                     "--group",g,"--from-beginning","--max-messages","6",
                     "--timeout-ms","45000",timeout=80).splitlines()
        if consume(group)!=values:raise RuntimeError("Primary consumer did not receive exact records")
        r["checks"]["group_consumption_order"]="PASS"
        if consume(replay)!=values:raise RuntimeError("Independent group replay mismatch")
        r["checks"]["independent_group_replay"]="PASS"
        # Read-only group metadata; avoid assuming auto-commit timing or active membership.
        info=k("exec",pod,"-c","kafka","--","/opt/kafka/bin/kafka-consumer-groups.sh",
               "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092","--describe",
               "--group",group,timeout=65)
        if topic not in info:raise RuntimeError("Consumer group topic metadata missing: "+info[-900:])
        r["checks"]["consumer_group_offset_metadata_visible"]="PASS"
        r["group_metadata"]=info[-1500:]
        r["status"],r["certification"]="PASS","PARTIAL_RUNTIME_PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError) as exc:
        r["error"]=str(exc)[:1600]
        print("Chapter 017 failed: "+str(exc),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
