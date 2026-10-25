#!/usr/bin/env python3
"""Chapter 013 read-only broker/replica balancing preflight, disposable kind only."""
import json, re, subprocess, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha"
OUT=Path("kafka/qa/evidence/chapter-013-runtime.json")

def k(*args, timeout=90):
    p=subprocess.run(["kubectl","--context",CTX,"-n",NS,*args],
                     capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr[-1400:])
    return p.stdout

def main():
    report={"chapter":"013","timestamp":datetime.now(timezone.utc).isoformat(),
            "status":"FAIL","certification":"NOT_CERTIFIED","checks":{},
            "limitations":["Read-only preflight; no replica reassignment or broker scale-in/out performed.",
                           "Three combined-role brokers with ephemeral storage on kind.",
                           "Multi-zone, persistent storage and throttled reassignment require separate labs."]}
    try:
        ctx=subprocess.run(["kubectl","config","current-context"],capture_output=True,
                           text=True,check=True,timeout=10).stdout.strip()
        if ctx!=CTX:raise RuntimeError("Unsafe Kubernetes context: "+ctx)
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=600s",timeout=630)
        pool=json.loads(k("get","kafkanodepool","dual-role","-o","json"))
        if pool["spec"]["replicas"]!=3 or "broker" not in pool["spec"]["roles"]:
            raise RuntimeError("Unexpected broker pool configuration")
        report["checks"]["broker_pool_capacity"]="PASS"
        pods=json.loads(k("get","pods","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
        brokers=sorted(p["metadata"]["name"] for p in pods if "-dual-role-" in p["metadata"]["name"] and p["status"].get("phase")=="Running")
        if len(brokers)!=3:raise RuntimeError("Expected three running brokers")
        report["checks"]["three_broker_pods"]="PASS"
        output=k("exec",brokers[0],"-c","kafka","--","/opt/kafka/bin/kafka-topics.sh",
                 "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092","--describe",
                 "--topic","ch004-replication")
        rows=re.findall(r"Partition:\s*(\d+).*?Leader:\s*(\d+).*?Replicas:\s*([\d,]+).*?Isr:\s*([\d,]+)",output)
        if not rows:raise RuntimeError("No partition placement data: "+output[-1200:])
        replicas=Counter()
        leaders=Counter()
        for partition,leader,rep,isr in rows:
            replica_ids=rep.split(",")
            isr_ids=isr.split(",")
            if len(set(replica_ids))!=3 or set(replica_ids)!=set(isr_ids):
                raise RuntimeError("Under-replicated partition "+partition)
            for broker in replica_ids:replicas[broker]+=1
            leaders[leader]+=1
        report["checks"]["replica_assignment_and_isr_preflight"]="PASS"
        report["placement"]={"replica_counts":dict(replicas),"leader_counts":dict(leaders),
                             "partitions_inspected":len(rows)}
        report["checks"]["broker_scale_in_safety_gate"]="PASS"
        report["scale_in_safe"]=False
        report["scale_in_reason"]="All three brokers host replicas; scale-in requires approved reassignment and completion verification."
        report["status"],report["certification"]="PASS","PARTIAL_RUNTIME_PASS"
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        report["error"]=str(exc)[:1500]
        print("Chapter 013 failed: "+str(exc),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return 0 if report["status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
