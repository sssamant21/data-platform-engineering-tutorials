#!/usr/bin/env python3
"""Chapter 014 bounded single-Pod failure recovery; disposable kind cluster only."""
import json,re,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

CTX,NS,CLUSTER,TOPIC="kind-kafka-qa","kafka-qa","qa-kafka-ha","ch004-replication"
OUT=Path("kafka/qa/evidence/chapter-014-runtime.json")
def k(*args,timeout=90):
    cmd=["kubectl","--context",CTX,"-n",NS,*args]
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError(" ".join(cmd[:8])+": "+p.stderr[-1100:])
    return p.stdout
def pods():
    items=json.loads(k("get","pods","-l",f"strimzi.io/cluster={CLUSTER}","-o","json"))["items"]
    return sorted((p for p in items if "-dual-role-" in p["metadata"]["name"]),
                  key=lambda p:p["metadata"]["name"])
def describe(pod):
    return k("exec",pod,"-c","kafka","--","/opt/kafka/bin/kafka-topics.sh",
             "--bootstrap-server",f"{CLUSTER}-kafka-bootstrap:9092","--describe",
             "--topic",TOPIC,timeout=45)
def state(desc):
    m=re.search(r"Partition:\s*0\s+Leader:\s*(\d+).*?Replicas:\s*([\d,]+).*?Isr:\s*([\d,]+)",desc)
    if not m:raise RuntimeError("Partition metadata unavailable: "+desc[-800:])
    return {"leader":int(m.group(1)),"replicas":set(m.group(2).split(",")),
            "isr":set(m.group(3).split(","))}
def until(fn,seconds,interval=4):
    end=time.monotonic()+seconds
    last=None
    while time.monotonic()<end:
        try:
            result=fn()
            if result:return result
        except (RuntimeError,subprocess.SubprocessError) as exc:last=str(exc)
        time.sleep(interval)
    raise RuntimeError("Timed out waiting for recovery; last error: "+str(last))
def main():
    report={"chapter":"014","timestamp":datetime.now(timezone.utc).isoformat(),
            "status":"FAIL","certification":"NOT_CERTIFIED","checks":{},
            "limitations":["Single-worker kind with three combined controller/broker Pods; not a multi-zone HA test.",
                           "Ephemeral storage; no durable PVC continuity or client record audit.",
                           "Only one Pod is deleted, with bounded recovery and no unclean election changes."]}
    try:
        ctx=subprocess.run(["kubectl","config","current-context"],capture_output=True,
                           text=True,check=True,timeout=10).stdout.strip()
        if ctx!=CTX:raise RuntimeError("Refusing unsafe context: "+ctx)
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=600s",timeout=630)
        k("wait","--for=condition=Ready",f"kafkatopic/{TOPIC}","--timeout=240s",timeout=260)
        members=pods()
        if len(members)!=3:raise RuntimeError("Expected three combined-role Pods")
        before=state(describe(members[0]["metadata"]["name"]))
        if len(before["replicas"])!=3 or len(before["isr"])!=3:
            raise RuntimeError("Baseline RF3/ISR3 not healthy")
        report["checks"]["baseline_rf3_isr3"]="PASS"
        # Delete a non-leader replica so KRaft controller quorum is not intentionally reduced by leadership loss.
        leader=str(before["leader"])
        candidates=[p for p in members if p["metadata"]["name"].split("-")[-1]!=leader]
        if not candidates:raise RuntimeError("No non-leader broker candidate")
        victim=candidates[0]
        name=victim["metadata"]["name"]
        old_uid=victim["metadata"]["uid"]
        survivor=next(p["metadata"]["name"] for p in members if p["metadata"]["name"]!=name)
        report["fault_injection"]={"pod":name,"old_uid":old_uid}
        k("delete","pod",name,"--wait=false",timeout=35)
        report["checks"]["single_pod_recreation_requested"]="PASS"
        def replacement():
            for p in pods():
                if p["metadata"]["name"]==name and p["metadata"]["uid"]!=old_uid:
                    if any(c.get("name")=="kafka" and c.get("ready") for c in p["status"].get("containerStatuses",[])):
                        return p
            return None
        restored=until(replacement,420)
        report["fault_injection"]["new_uid"]=restored["metadata"]["uid"]
        report["checks"]["replacement_pod_ready"]="PASS"
        def converged():
            s=state(describe(survivor))
            return s if len(s["isr"])==3 and s["isr"]==s["replicas"] else None
        after=until(converged,300)
        report["checks"]["isr_recovered_to_three"]="PASS"
        k("wait","--for=condition=Ready",f"kafka/{CLUSTER}","--timeout=300s",timeout=330)
        report["checks"]["strimzi_kafka_ready"]="PASS"
        report["before"]={"leader":before["leader"],"isr":sorted(before["isr"])}
        report["after"]={"leader":after["leader"],"isr":sorted(after["isr"])}
        report["status"],report["certification"]="PASS","PARTIAL_RUNTIME_PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError,StopIteration) as exc:
        report["error"]=str(exc)[:1600]
        print("Chapter 014 failure: "+str(exc),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return 0 if report["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
