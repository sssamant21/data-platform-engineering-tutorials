#!/usr/bin/env python3
"""Chapter 003 producer/consumer delivery semantics smoke acceptance."""
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
CTX,NS="kind-kafka-qa","kafka-qa"
OUT=Path("kafka/qa/evidence/chapter-003-delivery.json")
SRC=Path("kafka/qa/runtime/Chapter003Delivery.java")
def k(*args,data=None,timeout=120):
    p=subprocess.run(["kubectl","--context",CTX,"-n",NS,*args],
                     input=data,text=True,capture_output=True,timeout=timeout)
    if p.returncode: raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-1500:]}")
    return p.stdout
def broker():
    ps=json.loads(k("get","pods","-l","strimzi.io/cluster=qa-six","-o","json"))["items"]
    names=[p["metadata"]["name"] for p in ps
           if "-brokers-" in p["metadata"]["name"]
           and p["status"].get("phase")=="Running"
           and any(c.get("name")=="kafka" and c.get("ready")
                   for c in p["status"].get("containerStatuses",[]))]
    if not names: raise RuntimeError("No ready Kafka broker")
    return sorted(names)[0]
def main():
    report={"chapter":"003","lab":"producer-consumer-delivery","status":"FAIL",
            "checks":{},"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "limitations":"Tests successful acknowledgements and explicit commits; does not simulate ambiguous acknowledgements, retries, transactions or exactly-once end-to-end processing."}
    try:
        current=subprocess.run(["kubectl","config","current-context"],check=True,
                               capture_output=True,text=True,timeout=10).stdout.strip()
        if current!=CTX: raise RuntimeError("Unsafe context: "+current)
        k("wait","kafka/qa-six","--for=condition=Ready","--timeout=900s",timeout=930)
        k("wait","kafkatopic/qa-ch003-delivery","--for=condition=Ready","--timeout=240s",timeout=260)
        pod=broker()
        source=SRC.read_text(encoding="utf-8").replace("__RUN__",uuid.uuid4().hex[:12])
        k("exec","-i",pod,"-c","kafka","--","sh","-c",
          "cat > /tmp/Chapter003Delivery.java",data=source,timeout=30)
        output=k("exec",pod,"-c","kafka","--","sh","-c",
                 "java -cp '/opt/kafka/libs/*' /tmp/Chapter003Delivery.java",timeout=240)
        for name in ["acks_all_idempotent_producer","delivery_and_partition_order",
                     "explicit_commit_sync","restart_reads_committed_offset"]:
            if f"CHECK:{name}:PASS" not in output: raise RuntimeError("Missing check "+name)
            report["checks"][name]="PASS"
        if "CH003_DELIVERY_OK" not in output: raise RuntimeError("Missing final success marker")
        report["status"]="PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,ValueError,KeyError) as e:
        report["error"]=str(e)[:1600]
        print("Chapter 003 delivery failed: "+str(e),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print("Chapter 003 delivery: "+report["status"])
    return 0 if report["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
