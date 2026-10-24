#!/usr/bin/env python3
"""Chapter 011 topology and replica-placement inspection; no destructive mutations."""
import json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

CTX, NS, CLUSTER = "kind-kafka-qa", "kafka-qa", "qa-kafka-ha"
OUT = Path("kafka/qa/evidence/chapter-011-runtime.json")

def k(*args, timeout=90):
    cmd = ["kubectl", "--context", CTX, "-n", NS, *args]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{' '.join(cmd[:8])}: {p.stderr[-1200:]}")
    return p.stdout

def main():
    r = {"chapter":"011","timestamp":datetime.now(timezone.utc).isoformat(),
         "status":"FAIL","certification":"NOT_CERTIFIED","checks":{},
         "limitations":["Ephemeral 3-Pod combined-role fixture; PVC continuity is not tested.",
                        "Single-worker kind cannot validate multi-zone scheduling.",
                        "Read-only topology inspection; no broker scaling or reassignment."]}
    try:
        context = subprocess.run(["kubectl","config","current-context"],capture_output=True,
                                 text=True,check=True,timeout=10).stdout.strip()
        if context != CTX:
            raise RuntimeError(f"Unexpected context {context}")
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=600s",timeout=630)
        pools=json.loads(k("get","kafkanodepool","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
        if not any(p["spec"]["replicas"]==3 and "broker" in p["spec"]["roles"] for p in pools):
            raise RuntimeError("Expected three-broker NodePool")
        r["checks"]["nodepool_broker_capacity"]="PASS"
        pods=json.loads(k("get","pods","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
        brokers=[p for p in pods if "dual-role" in p["metadata"]["name"]]
        if len(brokers)!=3 or any(not p["spec"].get("nodeName") or p["status"].get("phase")!="Running" for p in brokers):
            raise RuntimeError("Expected three scheduled running broker Pods")
        r["pod_placement"]={p["metadata"]["name"]:p["spec"]["nodeName"] for p in brokers}
        r["checks"]["pod_scheduling_visible"]="PASS"
        topic="ch004-replication"
        pod=sorted(p["metadata"]["name"] for p in brokers)[0]
        desc=k("exec",pod,"-c","kafka","--","/opt/kafka/bin/kafka-topics.sh",
               "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092",
               "--describe","--topic",topic)
        rows=re.findall(r"Partition:\s*(\d+).*?Leader:\s*(\d+).*?Replicas:\s*([\d,]+).*?Isr:\s*([\d,]+)",desc)
        if not rows or any(len(set(rep.split(",")))!=3 or len(set(isr.split(",")))!=3 for _,_,rep,isr in rows):
            raise RuntimeError(f"Replica placement/ISR unexpected: {desc[-1000:]}")
        r["topic_replica_placement"]=desc[-1800:]
        r["checks"]["partition_leader_replica_isr_inspection"]="PASS"
        r["status"],r["certification"]="PASS","PARTIAL_RUNTIME_PASS"
    except (OSError,subprocess.SubprocessError,RuntimeError,KeyError,ValueError) as exc:
        r["error"]=str(exc)[:1500]
        print(f"Chapter 011 failure: {exc}",file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    return 0 if r["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
