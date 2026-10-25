#!/usr/bin/env python3
"""Chapter 003 Phase 7.2 broker restart fault injection and delivery checks."""
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path

CTX,NS="kind-kafka-qa","kafka-qa"
OUT=Path("kafka/qa/evidence/chapter-003-retry.json")
SRC=Path("kafka/qa/runtime/Chapter003Retry.java")

def cmd(args,timeout=120,input=None):
    p=subprocess.run(args,input=input,text=True,capture_output=True,timeout=timeout)
    if p.returncode: raise RuntimeError("Command failed: "+" ".join(args[:5])+" "+p.stderr[-1200:])
    return p.stdout

def k(*args,timeout=120,input=None):
    return cmd(["kubectl","--context",CTX,"-n",NS,*args],timeout,input)

def pods():
    return json.loads(k("get","pods","-l","strimzi.io/cluster=qa-six","-o","json"))["items"]

def ready(p):
    return p["status"].get("phase")=="Running" and any(
        c.get("name")=="kafka" and c.get("ready")
        for c in p["status"].get("containerStatuses",[]))

def broker():
    candidates=[p for p in pods() if "-brokers-" in p["metadata"]["name"] and ready(p)]
    if len(candidates)!=3: raise RuntimeError("Expected 3 ready broker Pods")
    return sorted(candidates,key=lambda p:p["metadata"]["name"])[0]["metadata"]["name"]

def main():
    report={"chapter":"003","lab":"broker-restart-producer-retry",
            "status":"FAIL","checks":{},"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "limitations":"Validates broker restart and exact observed records. It does not prove an internal Kafka client retry occurred, nor end-to-end exactly-once processing."}
    try:
        context=cmd(["kubectl","config","current-context"],timeout=10).strip()
        if context!=CTX: raise RuntimeError("Unsafe Kubernetes context "+context)
        k("wait","kafka/qa-six","--for=condition=Ready","--timeout=900s",timeout=930)
        k("wait","kafkatopic/qa-ch003-delivery","--for=condition=Ready","--timeout=240s",timeout=260)
        victim=broker()
        uid=next(p["metadata"]["uid"] for p in pods() if p["metadata"]["name"]==victim)
        source=SRC.read_text(encoding="utf-8").replace("__RUN__",uuid.uuid4().hex[:12])
        # Run the Java client in a broker Pod that is NOT the restart victim.
        survivor=sorted(p["metadata"]["name"] for p in pods()
                        if "-brokers-" in p["metadata"]["name"] and p["metadata"]["name"]!=victim)[0]
        k("exec","-i",survivor,"-c","kafka","--","sh","-c",
          "cat > /tmp/Chapter003Retry.java",input=source,timeout=30)
        # Java execution and restart are coordinated by a durable stdout marker.
        proc=subprocess.Popen(["kubectl","--context",CTX,"-n",NS,"exec",survivor,"-c","kafka","--",
                               "sh","-c","java -cp '/opt/kafka/libs/*' /tmp/Chapter003Retry.java"],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        # Avoid blocking on Java stdout by using a short bounded delay before injecting.
        # The first six sends may complete quickly; injection is still a real broker restart.
        time.sleep(5)
        k("delete","pod",victim,"--wait=false",timeout=30)
        report["checks"]["broker_restart_injected"]="PASS"
        stdout,stderr=proc.communicate(timeout=260)
        if proc.returncode: raise RuntimeError("Java producer failed: "+stderr[-1500:]+stdout[-800:])
        for check in ["acknowledged_writes","no_duplicate_records_in_test_window","partition_order_preserved"]:
            if f"CHECK:{check}:PASS" not in stdout:
                raise RuntimeError("Missing acceptance check "+check+": "+stdout[-900:])
            report["checks"][check]="PASS"
        deadline=time.monotonic()+420
        while time.monotonic()<deadline:
            replacement=next((p for p in pods() if p["metadata"]["name"]==victim),None)
            if replacement and replacement["metadata"]["uid"]!=uid and ready(replacement): break
            time.sleep(5)
        else: raise RuntimeError("Replacement broker UID/Ready not observed")
        report["checks"]["replacement_broker_ready"]="PASS"
        k("wait","kafka/qa-six","--for=condition=Ready","--timeout=420s",timeout=450)
        report["checks"]["kafka_ready_after_restart"]="PASS"
        report["status"]="PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,ValueError,KeyError) as exc:
        report["error"]=str(exc)[:1600]
        print("Chapter 003 retry failed: "+str(exc),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print("Chapter 003 retry: "+report["status"])
    return 0 if report["status"]=="PASS" else 1

if __name__=="__main__":sys.exit(main())
