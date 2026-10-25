#!/usr/bin/env python3
"""Phase 7.3: targeted partition leader restart with bounded recovery."""
import json,re,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
CTX,NS="kind-kafka-qa","kafka-qa"
OUT=Path("kafka/qa/evidence/chapter-003-leader-failover.json")
def run(args,timeout=120,input=None):
    p=subprocess.run(args,input=input,text=True,capture_output=True,timeout=timeout)
    if p.returncode:raise RuntimeError("Command failed: "+" ".join(args[:7])+" "+p.stderr[-1300:])
    return p.stdout
def k(*args,timeout=120,input=None):return run(["kubectl","--context",CTX,"-n",NS,*args],timeout,input)
def brokers():
    items=json.loads(k("get","pods","-l","strimzi.io/cluster=qa-six","-o","json"))["items"]
    return {int(p["metadata"]["labels"]["strimzi.io/pool-name"]=="brokers")*int(re.search(r"-(\d+)$",p["metadata"]["name"]).group(1)):p for p in items
            if "-brokers-" in p["metadata"]["name"] and re.search(r"-(\d+)$",p["metadata"]["name"])}
def broker_pods():
    return [p for p in json.loads(k("get","pods","-l","strimzi.io/cluster=qa-six","-o","json"))["items"]
            if "-brokers-" in p["metadata"]["name"]]
def describe(pod):
    return k("exec",pod,"-c","kafka","--","bin/kafka-topics.sh",
             "--bootstrap-server","qa-six-kafka-bootstrap:9092","--describe",
             "--topic","qa-ch003-delivery",timeout=90)
def leader_id(description):
    m=re.search(r"Partition:\s*0\s+Leader:\s*(\d+)",description)
    if not m:raise RuntimeError("Could not identify partition 0 leader: "+description[-1200:])
    return int(m.group(1))
def main():
    report={"chapter":"003","lab":"targeted-leader-failover","status":"FAIL",
            "checks":{},"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "retry_observed":False,
            "limitations":"A producer retry count of zero is not proof of a retry; leader failover and delivery are separately verified."}
    try:
        if run(["kubectl","config","current-context"],10).strip()!=CTX:raise RuntimeError("Unsafe Kubernetes context")
        k("wait","kafka/qa-six","--for=condition=Ready","--timeout=900s",timeout=930)
        k("wait","kafkatopic/qa-ch003-delivery","--for=condition=Ready","--timeout=240s",timeout=260)
        pods=broker_pods()
        if len(pods)!=3:raise RuntimeError("Expected three broker Pods")
        byid={}
        for p in pods:
            name=p["metadata"]["name"]
            nodeid=int(re.search(r"-(\d+)$",name).group(1))
            byid[nodeid]=p
        initial=leader_id(describe(pods[0]["metadata"]["name"]))
        if initial not in byid:raise RuntimeError("Partition leader not in broker node pool")
        victim=byid[initial]
        victim_name=victim["metadata"]["name"]
        old_uid=victim["metadata"]["uid"]
        survivor=sorted(p["metadata"]["name"] for p in pods if p["metadata"]["name"]!=victim_name)[0]
        report["old_leader_id"]=initial
        report["checks"]["leader_identified"]="PASS"
        source=Path("kafka/qa/runtime/Chapter003LeaderFailover.java").read_text().replace("__RUN__",uuid.uuid4().hex[:12])
        k("exec","-i",survivor,"-c","kafka","--","sh","-c",
          "cat > /tmp/Chapter003LeaderFailover.java",input=source,timeout=30)
        # Start Java asynchronously. The marker ensures producer traffic precedes deletion.
        k("exec",survivor,"-c","kafka","--","sh","-c",
          "nohup sh -c \"java -cp '/opt/kafka/libs/*' /tmp/Chapter003LeaderFailover.java > /tmp/ch003-leader.log 2>&1; echo $? > /tmp/ch003-leader.exit\" </dev/null >/dev/null 2>&1 &",timeout=30)
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            log=k("exec",survivor,"-c","kafka","--","sh","-c","cat /tmp/ch003-leader.log 2>/dev/null || true",timeout=15)
            if "PRODUCER_PROGRESS_10" in log:break
            if "Exception" in log or "Error" in log:raise RuntimeError("Java failed before injection: "+log[-1200:])
            time.sleep(2)
        else:raise RuntimeError("Producer progress marker not observed")
        report["checks"]["producer_active_before_failure"]="PASS"
        k("delete","pod",victim_name,"--wait=false",timeout=30)
        report["checks"]["leader_broker_deletion_requested"]="PASS"
        deadline=time.monotonic()+240
        newleader=None
        while time.monotonic()<deadline:
            try:
                current=leader_id(describe(survivor))
                if current!=initial:
                    newleader=current
                    break
            except RuntimeError:pass
            time.sleep(3)
        if newleader is None:raise RuntimeError("New partition leader not observed")
        report["new_leader_id"]=newleader
        report["checks"]["new_partition_leader_elected"]="PASS"
        deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            status=k("exec",survivor,"-c","kafka","--","sh","-c",
                     "cat /tmp/ch003-leader.exit 2>/dev/null || true",timeout=15).strip()
            if status:
                if status!="0":raise RuntimeError("Java exited "+status+": "+k("exec",survivor,"-c","kafka","--","cat","/tmp/ch003-leader.log")[-1800:])
                break
            time.sleep(4)
        else:raise RuntimeError("Java producer acceptance timed out")
        log=k("exec",survivor,"-c","kafka","--","cat","/tmp/ch003-leader.log",timeout=20)
        for name in ("acknowledged_100_records","ordered_exactly_100_observed"):
            if f"CHECK:{name}:PASS" not in log:raise RuntimeError("Missing "+name+": "+log[-1200:])
            report["checks"][name]="PASS"
        m=re.search(r"PRODUCER_RETRY_TOTAL:([0-9.]+)",log)
        if not m:raise RuntimeError("Missing retry metric")
        report["producer_retry_total"]=float(m.group(1))
        report["retry_observed"]=report["producer_retry_total"]>0
        report["checks"]["producer_retry_metric_recorded"]="PASS"
        deadline=time.monotonic()+420
        while time.monotonic()<deadline:
            replacement=next((p for p in broker_pods() if p["metadata"]["name"]==victim_name),None)
            if replacement and replacement["metadata"]["uid"]!=old_uid and any(
                c.get("name")=="kafka" and c.get("ready") for c in replacement["status"].get("containerStatuses",[])):
                break
            time.sleep(5)
        else:raise RuntimeError("Replacement broker Pod not Ready with new UID")
        report["checks"]["replacement_broker_ready"]="PASS"
        k("wait","kafka/qa-six","--for=condition=Ready","--timeout=420s",timeout=450)
        report["checks"]["kafka_recovered"]="PASS"
        report["status"]="PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,KeyError,ValueError) as exc:
        report["error"]=str(exc)[:1600]
        print("Chapter 003 leader failover failed: "+str(exc),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2)+"\n")
        print("Chapter 003 leader failover: "+report["status"])
    return 0 if report["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
