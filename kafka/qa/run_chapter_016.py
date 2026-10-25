#!/usr/bin/env python3
"""Chapter 016 producer acks and idempotence smoke acceptance on disposable kind."""
import json,subprocess,sys,uuid
from datetime import datetime,timezone
from pathlib import Path

CTX,NS,CLUSTER="kind-kafka-qa","kafka-qa","qa-kafka-ha"
OUT=Path("kafka/qa/evidence/chapter-016-runtime.json")
def k(*args,input=None,timeout=90):
    p=subprocess.run(["kubectl","--context",CTX,"-n",NS,*args],input=input,
                     capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr[-1400:])
    return p.stdout
def main():
    r={"chapter":"016","timestamp":datetime.now(timezone.utc).isoformat(),
       "status":"FAIL","certification":"NOT_CERTIFIED","checks":{},
       "limitations":["Console producer supports acks=all but does not prove idempotence.",
                      "No broker failure, retries, latency SLO, or application restart deduplication.",
                      "Ephemeral single-worker kind cluster; not a multi-zone reliability certification."]}
    try:
        ctx=subprocess.run(["kubectl","config","current-context"],check=True,
                           capture_output=True,text=True,timeout=10).stdout.strip()
        if ctx!=CTX:raise RuntimeError("Unsafe Kubernetes context")
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=600s",timeout=630)
        pods=json.loads(k("get","pods","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
        names=sorted(p["metadata"]["name"] for p in pods if "-dual-role-" in p["metadata"]["name"] and p["status"].get("phase")=="Running")
        if len(names)!=3:raise RuntimeError("Expected three broker Pods")
        pod=names[0]
        topic="ch016-producer-"+uuid.uuid4().hex[:8]
        manifest={"apiVersion":"kafka.strimzi.io/v1beta2","kind":"KafkaTopic",
                  "metadata":{"name":topic,"labels":{"strimzi.io/cluster":CLUSTER}},
                  "spec":{"partitions":1,"replicas":3,"config":{"min.insync.replicas":2,"retention.ms":600000}}}
        k("apply","-f","-",input=json.dumps(manifest))
        k("wait","--for=condition=Ready",f"kafkatopic/{topic}","--timeout=240s",timeout=260)
        r["checks"]["rf3_minisr2_topic_ready"]="PASS"
        messages=[f"ch016-{uuid.uuid4().hex}-{i}" for i in range(8)]
        payload="\n".join(messages)+"\n"
        k("exec","-i",pod,"-c","kafka","--","/opt/kafka/bin/kafka-console-producer.sh",
          "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092",
          "--topic",topic,"--producer-property","acks=all",
          "--producer-property","enable.idempotence=true",
          "--producer-property","max.in.flight.requests.per.connection=5",
          input=payload,timeout=130)
        r["checks"]["acks_all_idempotent_producer_config_executed"]="PASS"
        received=k("exec",pod,"-c","kafka","--","/opt/kafka/bin/kafka-console-consumer.sh",
                   "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092",
                   "--topic",topic,"--from-beginning","--max-messages","8",
                   "--timeout-ms","30000",timeout=70).splitlines()
        if received!=messages:raise RuntimeError(f"Record reconciliation mismatch: expected {messages!r}, got {received!r}")
        r["checks"]["eight_records_reconciled_in_order"]="PASS"
        r["records_verified"]=len(received)
        r["status"],r["certification"]="PASS","PARTIAL_RUNTIME_PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError) as exc:
        r["error"]=str(exc)[:1600]
        print("Chapter 016 failed: "+str(exc),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
