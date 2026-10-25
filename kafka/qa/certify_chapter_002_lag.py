#!/usr/bin/env python3
"""Chapter 002 Phase 6.4 lag and controlled replay certification."""
import json
import subprocess
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

CTX, NS = "kind-kafka-qa", "kafka-qa"
OUT = Path("kafka/qa/evidence/chapter-002-lag-result.json")
JAVA = Path("kafka/qa/runtime/Chapter002Lag.java")

def k(*args, data=None, timeout=120):
    p=subprocess.run(["kubectl","--context",CTX,"-n",NS,*args],
                     input=data,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"kubectl {args[0]} failed: {p.stderr[-1500:]}")
    return p.stdout

def broker():
    ps=json.loads(k("get","pods","-l","strimzi.io/cluster=qa-six","-o","json"))["items"]
    matches=[p["metadata"]["name"] for p in ps
             if "-brokers-" in p["metadata"]["name"]
             and p["status"].get("phase")=="Running"
             and any(c.get("name")=="kafka" and c.get("ready")
                     for c in p["status"].get("containerStatuses",[]))]
    if not matches: raise RuntimeError("No ready broker")
    return sorted(matches)[0]

def main():
    result={"chapter":"002","lab":"consumer-lag-offset-replay","status":"FAIL",
            "checks":{},"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"Disposable kind, test-only consumer group, explicit partition assignment; not production offset reset."}
    try:
        context=subprocess.run(["kubectl","config","current-context"],
                               capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        if context!=CTX: raise RuntimeError("Unsafe context "+context)
        k("wait","kafka/qa-six","--for=condition=Ready","--timeout=900s",timeout=930)
        k("wait","kafkatopic/qa-ch002-ordering","--for=condition=Ready","--timeout=240s",timeout=260)
        pod=broker()
        source=JAVA.read_text(encoding="utf-8").replace("__RUN__",uuid.uuid4().hex[:12])
        k("exec","-i",pod,"-c","kafka","--","sh","-c",
          "cat > /tmp/Chapter002Lag.java",data=source,timeout=30)
        output=k("exec",pod,"-c","kafka","--","sh","-c",
                 "java -cp '/opt/kafka/libs/*' /tmp/Chapter002Lag.java",timeout=240)
        checks=["five_new_records","initial_offset_commit","lag_before_consumption",
                "commit_after_consumption","lag_zero_after_commit",
                "restart_at_committed_end","explicit_seek_replay",
                "replay_does_not_change_commit"]
        for check in checks:
            if f"CHECK:{check}:PASS" not in output:
                raise RuntimeError("Missing "+check+": "+output[-1200:])
            result["checks"][check]="PASS"
        if "LAG_BEFORE:5" not in output or "LAG_AFTER:0" not in output or "LAG_ACCEPTANCE_OK" not in output:
            raise RuntimeError("Expected lag transition 5 -> 0 not observed")
        result["lag_before"]=5
        result["lag_after"]=0
        result["status"]="PASS"
    except (RuntimeError,OSError,subprocess.SubprocessError,ValueError,KeyError) as e:
        result["error"]=str(e)[:1600]
        print("Chapter 002 lag failed: "+str(e),file=sys.stderr)
    finally:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        print("Chapter 002 lag: "+result["status"])
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":
    sys.exit(main())
