#!/usr/bin/env python3
"""Chapter 015 bounded reliability capstone; read-only checks plus one disposable Pod recovery."""
import json,re,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

CTX,NS,CLUSTER,TOPIC="kind-kafka-qa","kafka-qa","qa-kafka-ha","ch004-replication"
OUT=Path("kafka/qa/evidence/chapter-015-runtime.json")
def k(*args,timeout=90):
    p=subprocess.run(["kubectl","--context",CTX,"-n",NS,*args],text=True,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(p.stderr[-1200:])
    return p.stdout
def members():
    return sorted([p for p in json.loads(k("get","pods","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
                   if "-dual-role-" in p["metadata"]["name"]],key=lambda p:p["metadata"]["name"])
def describe(pod):
    return k("exec",pod,"-c","kafka","--","/opt/kafka/bin/kafka-topics.sh",
             "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092","--describe","--topic",TOPIC,timeout=50)
def metadata(desc):
    m=re.search(r"Partition:\s*0\s+Leader:\s*(\d+).*?Replicas:\s*([\d,]+).*?Isr:\s*([\d,]+)",desc)
    if not m:raise RuntimeError("Partition metadata not found: "+desc[-900:])
    return {"leader":m.group(1),"replicas":set(m.group(2).split(",")),"isr":set(m.group(3).split(","))}
def wait_for(fn,seconds):
    end=time.monotonic()+seconds
    last=None
    while time.monotonic()<end:
        try:
            value=fn()
            if value:return value
        except (RuntimeError,subprocess.SubprocessError) as e:last=str(e)
        time.sleep(4)
    raise RuntimeError("Recovery timeout: "+str(last))
def main():
    r={"chapter":"015","status":"FAIL","certification":"NOT_CERTIFIED",
       "timestamp":datetime.now(timezone.utc).isoformat(),"checks":{},
       "score":{"earned":0,"possible":60},
       "limitations":["60-point runtime subset of 100-point enterprise capstone.",
                      "Combined-role ephemeral single-node kind; no PVC/multi-zone certification.",
                      "No producer/consumer reconciliation, TLS, metrics alerts or signed change approval."]}
    try:
        ctx=subprocess.run(["kubectl","config","current-context"],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        if ctx!=CTX:raise RuntimeError("Refusing unsafe Kubernetes context")
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=600s",timeout=630)
        k("wait","--for=condition=Ready",f"kafkatopic/{TOPIC}","--timeout=240s",timeout=260)
        pool=json.loads(k("get","kafkanodepool","dual-role","-o","json"))
        if pool["spec"]["replicas"]!=3:raise RuntimeError("Broker pool does not have three replicas")
        r["checks"]["nodepool_capacity"]="PASS";r["score"]["earned"]+=10
        ps=members()
        if len(ps)!=3 or any(p["status"].get("phase")!="Running" for p in ps):
            raise RuntimeError("Expected three running brokers")
        r["inventory"]=[{"pod":p["metadata"]["name"],"node":p["spec"].get("nodeName"),
                          "uid":p["metadata"]["uid"]} for p in ps]
        r["checks"]["kubernetes_inventory"]="PASS";r["score"]["earned"]+=10
        topic=json.loads(k("get","kafkatopic",TOPIC,"-o","json"))
        if topic["spec"]["replicas"]!=3 or topic["spec"]["config"].get("min.insync.replicas")!=2:
            raise RuntimeError("Topic RF/minISR mismatch")
        r["checks"]["topic_policy"]="PASS";r["score"]["earned"]+=10
        before=metadata(describe(ps[0]["metadata"]["name"]))
        if len(before["isr"])!=3 or before["isr"]!=before["replicas"]:
            raise RuntimeError("Unhealthy baseline ISR")
        r["checks"]["healthy_replica_placement"]="PASS";r["score"]["earned"]+=10
        victim=next((p for p in ps if p["metadata"]["name"].split("-")[-1]!=before["leader"]),None)
        if not victim:raise RuntimeError("No safe non-leader Pod")
        victim_name=victim["metadata"]["name"];old_uid=victim["metadata"]["uid"]
        survivor=next(p["metadata"]["name"] for p in ps if p["metadata"]["name"]!=victim_name)
        k("delete","pod",victim_name,"--wait=false",timeout=35)
        def replacement():
            for p in members():
                if p["metadata"]["name"]==victim_name and p["metadata"]["uid"]!=old_uid:
                    if any(c.get("name")=="kafka" and c.get("ready") for c in p["status"].get("containerStatuses",[])):return p
            return None
        new=wait_for(replacement,420)
        r["recreated_pod_uid"]=new["metadata"]["uid"]
        r["checks"]["single_pod_recovered"]="PASS";r["score"]["earned"]+=10
        after=wait_for(lambda: (lambda x:x if x["isr"]==x["replicas"] and len(x["isr"])==3 else None)(metadata(describe(survivor))),300)
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=300s",timeout=330)
        r["checks"]["isr_and_cluster_recovered"]="PASS";r["score"]["earned"]+=10
        r["status"],r["certification"]="PASS","PARTIAL_RUNTIME_PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as e:
        r["error"]=str(e)[:1600]
        print("Chapter 015 failed: "+str(e),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(r,indent=2)+"\n")
    return 0 if r["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
