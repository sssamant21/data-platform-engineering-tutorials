# 78 — HA Failover and Application Resilience Project

Part 10 — Troubleshooting and Production Projects

**Audience:** DBREs, SREs, Developers and Platform Engineers.  
**Goal:** Measure application behavior across a controlled primary handoff, reconcile acknowledged and ambiguous outcomes, verify stable-identity replay, and accept restored redundancy.  
**Baseline:** Accepted retained MongoDB 8.0 / FCV 8.0 three-member TLS/SCRAM replica set; exact recorded mongosh and reviewed pinned synchronous PyMongo 4.x on Python 3.11+. Core lab is Community-compatible.  
**Status:** Written; syntax and offline ledger/reconciliation checks complete; live failover and application acceptance pending.  
**Prerequisites:** Chapters 27–32, 41–42, 63, 69–71 and 76–77; healthy topology, resource/history reserve and independent maintenance/recovery identity.  
**Estimated time:** 90–120 minutes including evidence review and member convergence.

## 1. Project contract

High availability includes the database election, client discovery, application deadlines, acknowledgement semantics and final data correctness. A primary election without usable application recovery is incomplete HA acceptance.

This project runs 60 bounded logical writes under one long-lived application client. Each write has a stable identity and immutable desired content. A local fsynced ledger records intent before submission and observed acknowledgement/error afterward. One separately operated non-forced handoff occurs during the workload under the retained lab's maintenance procedure. Reconciliation precedes optional application replay.

The project does not induce quorum loss, network partitions, multi-member crashes or production changes. Planned handoff evidence must not be reported as acceptance of every unplanned outage scenario.

Acceptance requires:

- A healthy declared three-member baseline and fresh monitoring.
- Durable local intent/outcome records and correct immutable payloads.
- Actual handoff/election and client recovery timeline.
- No missing acknowledged writes after accepted recovery.
- Explicit ambiguous outcomes; no assumption that an error means no write.
- Repeated stable-identity writes leave one correct document per logical operation.
- All original members converge with accepted resource/history headroom.

## 2. Concern, timeout and retry design

Use the normal replica-set-aware URI, verified TLS and majority write concern. Use majority reads on the primary for post-run reconciliation. The write contract is one immutable acceptance document per logical operation; it does not include an external side effect.

Retryable writes apply to supported operations/topologies and do not make arbitrary application replays or external side effects exactly once.[1] This project uses `updateOne` with `$setOnInsert`, stable `_id` and immutable content. Replaying the same identity should not increment a counter or duplicate business work.

Client deadlines, server selection and write-concern timeout describe different boundaries. The script uses a five-second PyMongo operation deadline for each logical write and does not add an unlimited application retry loop.[2] Review behavior against the exact pinned driver. Timeout/error outcomes can be ambiguous; reconcile state before deciding to replay.

The local ledger is durable against ordinary process interruption when the local filesystem honors fsync. It is not a replicated production ledger and does not survive arbitrary disk/host loss. Production intent/outcome durability needs its own accepted architecture.

## 3. Scope, permissions and stop gates

The lifecycle identity creates and cleans the owned database. The application identity needs scoped find/update/insert on its operation collection and read access to the marker. The observer needs replication/process evidence; the maintenance identity needs the already accepted handoff privilege. Do not grant those privileges to the application client.

Require one primary, two healthy eligible secondaries, accepted lag/history and storage/memory reserve, working verified connections and no conflicting change. Stop if the gate fails. Do not add `force:true` to overcome a refused handoff.

Record exact versions, set/member endpoints, original primary/term, UTC run boundary, service deadline, write/read concern, driver options and evidence directory owner. Keep secrets outside URIs and logs.

## 4. Owned setup

Through Chapter 42's lifecycle connection to the accepted primary:

```javascript
var labName = "mongodb_enterprise_ch78_resilience";
var lab = db.getSiblingDB(labName);
function check(condition, message) { if (!condition) throw new Error(message); }
check(lab.getCollectionInfos().length === 0, "Namespace already exists");
check(db.hello().isWritablePrimary === true, "Expected primary");
var status = db.getSiblingDB("admin").runCommand({ replSetGetStatus: 1 });
check(status.ok === 1 && status.members.length === 3, "Expected accepted three-member lab");
check(status.members.every(m => m.health === 1 &&
  ["PRIMARY", "SECONDARY"].includes(m.stateStr)), "Topology not maintenance-ready");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch78", createdAt: new Date() });
lab.createCollection("operations");
printjson({ originalPrimary: db.hello().me, term: status.term, observedAt: new Date() });
```

Use a fresh local evidence directory. Set `CH78_URI` to the normal credential-free replica-set URI, `CH78_USER` to the scoped application identity, `CH78_CA_FILE` to the verified CA and `CH78_EVIDENCE_DIR` to an absolute new directory. Install the exact approved PyMongo release in an isolated environment.

## 5. Complete application runner and verifier

Save Sections 5–7 consecutively as `ch78_resilience.py`. Modes are `run`, `verify` and `replay`. Run creates a new directory and submits 60 operations. Verify is read-only and must be executed before replay. Replay is an explicit data action limited to the retained owned intent set.

```python
import getpass
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pymongo
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

DB = "mongodb_enterprise_ch78_resilience"
OWNER = "mongodb-enterprise-tutorial-ch78"
RUN_ID = "ch78-owned-run"
COUNT = 60
root = Path(os.environ["CH78_EVIDENCE_DIR"])
mode = sys.argv[1] if len(sys.argv) == 2 else "verify"
if mode not in {"run", "verify", "replay"}:
    raise ValueError("Choose run, verify or replay")
if mode == "run":
    root.mkdir(parents=True, exist_ok=False)
elif not root.is_dir():
    raise RuntimeError("Recorded evidence directory unavailable")


def record(event):
    entry = dict(event, utc=datetime.now(timezone.utc).isoformat())
    with (root / "ledger.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps(entry, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())


def payload(seq):
    return {"_id": RUN_ID + ":" + str(seq), "run_id": RUN_ID,
            "seq": seq, "value": seq * 7}


def ledger_contract(entries):
    intents = {}
    acknowledged = set()
    for entry in entries:
        if entry["kind"] == "intent":
            doc = entry["document"]
            if doc["_id"] in intents and intents[doc["_id"]] != doc:
                raise RuntimeError("Conflicting durable intent")
            intents[doc["_id"]] = doc
        if entry["kind"] == "ack":
            acknowledged.add(entry["id"])
    if not acknowledged.issubset(intents):
        raise RuntimeError("Acknowledgement without intent")
    return intents, acknowledged


def reconcile(intents, acknowledged, actual):
    ids = set(intents)
    missing = sorted(ids - set(actual))
    unexpected = sorted(set(actual) - ids)
    changed = sorted(key for key in ids & set(actual) if intents[key] != actual[key])
    return {"intended": len(intents), "acknowledged": len(acknowledged),
            "missing_acknowledged": sorted(acknowledged - set(actual)),
            "unacknowledged_present": sorted((ids - acknowledged) & set(actual)),
            "unacknowledged_absent": sorted((ids - acknowledged) - set(actual)),
            "missing_all": missing, "unexpected": unexpected, "changed": changed}


client = MongoClient(
    os.environ["CH78_URI"], username=os.environ["CH78_USER"],
    password=getpass.getpass("MongoDB application password: "), authSource="admin",
    tls=True, tlsCAFile=os.environ["CH78_CA_FILE"], retryWrites=True,
    serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, maxPoolSize=4,
)
lab = client.get_database(DB, write_concern=WriteConcern(w="majority", wtimeout=4000),
                          read_concern=ReadConcern("majority"))
```

## 6. Workload with intent-before-submit and outcome-after-return

```python
try:
    with pymongo.timeout(5):
        if lab.ownership.find_one({"_id": OWNER}) is None:
            raise RuntimeError("Owned marker absent")
        client.admin.command("ping")
    if mode == "run":
        with pymongo.timeout(5):
            if lab.operations.count_documents({}) != 0:
                raise RuntimeError("Expected empty owned operation collection")
        record({"kind": "start", "run_id": RUN_ID, "driver": pymongo.version,
                "count": COUNT, "deadline_seconds": 5})
        print("RUNNING: begin the separately authorized handoff after several writes", flush=True)
        for seq in range(COUNT):
            doc = payload(seq)
            record({"kind": "intent", "document": doc})
            started = time.monotonic()
            try:
                with pymongo.timeout(5):
                    result = lab.operations.update_one(
                        {"_id": doc["_id"]}, {"$setOnInsert": {k: v for k, v in doc.items() if k != "_id"}},
                        upsert=True,
                    )
                    if not result.acknowledged:
                        raise RuntimeError("Acknowledged-write contract violated")
                record({"kind": "ack", "id": doc["_id"],
                        "elapsed_ms": (time.monotonic()-started)*1000})
            except PyMongoError as error:
                record({"kind": "uncertain", "id": doc["_id"],
                        "error_class": type(error).__name__, "code": getattr(error, "code", None),
                        "elapsed_ms": (time.monotonic()-started)*1000})
                if getattr(error, "code", None) in {13, 18}:
                    raise  # Authorization/authentication is not transient election recovery.
            time.sleep(0.5)
        record({"kind": "run_complete", "count": COUNT})
        print("RUN COMPLETE: perform topology acceptance and read-only verify before replay")
```

The workload runs at most 60 submitted logical operations with bounded per-operation driver budgets and short pacing. It can take longer than 30 seconds when operations hit deadlines. No exception message/URI/password is printed; retain sanitized underlying cause through the approved diagnostic channel if required.

A caught PyMongoError is recorded as uncertain rather than classified as definitely absent. Review its code/labels and context. Driver-internal retries are distinct from the explicit application replay mode.

## 7. Reconcile first, then deliberately replay

```python
    else:
        entries = [json.loads(line) for line in (root / "ledger.jsonl").read_text().splitlines()]
        intents, acknowledged = ledger_contract(entries)
        if mode == "replay":
            # Review the prior read-only report and accepted topology before this owned write stage.
            for key in sorted(intents):
                doc = intents[key]
                with pymongo.timeout(5):
                    lab.operations.update_one({"_id": key}, {
                        "$setOnInsert": {k: v for k, v in doc.items() if k != "_id"}
                    }, upsert=True)
            record({"kind": "replay_complete", "intents": len(intents)})
        with pymongo.timeout(5):
            actual_rows = list(lab.operations.find({}, {"_id": 1, "run_id": 1, "seq": 1, "value": 1}))
        actual = {row["_id"]: row for row in actual_rows}
        report = reconcile(intents, acknowledged, actual)
        report["mode"] = mode
        report["complete_intent_set"] = set(intents) == {payload(i)["_id"] for i in range(COUNT)}
        phase = "verify" if mode == "verify" else "replay"
        name = phase + "-" + str(time.time_ns()) + ".json"
        (root / name).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(report)
        if report["missing_acknowledged"] or report["unexpected"] or report["changed"]:
            raise RuntimeError("Integrity acceptance failed: stop and investigate")
        if not report["complete_intent_set"]:
            raise RuntimeError("Run interrupted: reconcile partial intent set; not full project acceptance")
        if report["missing_all"]:
            raise RuntimeError("Owned intents absent: record result and review bounded replay")
        print("PASS: complete intended immutable state reconciled")
finally:
    client.close()
```

Run `python ch78_resilience.py run` in one terminal. Keep monitoring and the maintenance session separate. After topology recovery, run `python ch78_resilience.py verify` and preserve its report even if it fails. Missing acknowledged documents, conflicting content or unexpected IDs block acceptance and need investigation, not replay that hides evidence.

If only unacknowledged intents are absent and topology/recovery is accepted, review that result and run `python ch78_resilience.py replay`. Then repeat replay once and require unchanged identities/content/count. An unacknowledged-present outcome demonstrates why timeout is not proof of no write.

A crashed runner may leave fewer than 60 intents. Preserve that boundary; do not restart `run` in the same directory or namespace and call it the original uninterrupted experiment. Reconcile the partial run and create a fresh owned experiment after cleanup.

## 8. Controlled primary handoff during the workload

Use Chapter 71's already accepted lab gates and an independent maintenance identity. Confirm the current primary and caught-up eligible secondaries before issuing one command while the runner is active:

```javascript
printjson(db.getSiblingDB("admin").runCommand({
  replSetStepDown: 60, secondaryCatchUpPeriodSecs: 10, force: false
}));
```

A non-forced handoff can refuse if no suitable secondary is ready.[3] Stop and investigate; do not force or repeat it to make the exercise pass. Capture the response/error, UTC event time, original/new primary, term and actual selection delay through the observer.

The application client remains alive and uses normal discovery. A successful driver retry may hide transient errors from this workload, so zero caught exceptions does not prove that no election occurred. Require the actual election timeline. Conversely, caught errors alone do not prove a topology cause; correlate with client/TLS/network evidence.

No additional member changes occur until full recovery. Do not force the original member back to primary; accepted role distribution matters more than preserving its original role.

## 9. Member and application recovery acceptance

Observe one primary and two healthy secondaries from the authorized member perspectives. Require the accepted lag/history/resource budgets and exact operation reconciliation on every retained member after bounded catch-up. Use verified direct diagnostic sessions with intentional secondary reads only for member-local checks; application traffic remains replica-set-aware.

```javascript
var admin = db.getSiblingDB("admin");
var status = admin.runCommand({ replSetGetStatus: 1 });
if (status.ok !== 1) throw new Error("Recovery observation failed");
printjson({ observedAt: new Date(), term: status.term,
  members: status.members.map(m => ({ name: m.name, health: m.health,
    stateStr: m.stateStr, optimeDate: m.optimeDate })) });
```

Measure the observed application's latency/errors and gap between acknowledged successes. The ledger's elapsed times cover the logical driver operation, not a real business HTTP endpoint. Add actual service trace/SLO evidence before production acceptance.

Reconcile all 60 immutable records after any approved replay. Require `_id`, run_id, seq and value equality, not merely count 60 or total value. Record pre-replay missing/ambiguous outcomes separately from final convergence.

## 10. Additional scenarios and scope limits

| Scenario | Required accepted procedure | Evidence beyond this handoff |
|---|---|---|
| Single primary process failure | Chapter 32 isolated failure/recovery lab | Actual process loss, restored original member and application/data contract |
| Secondary maintenance | Chapter 28/71 sequential maintenance | Continued service, recovered secondary and history headroom |
| Network partition | Chapter 31 isolated partition lab | Exact boundary, quorum behavior and rollback reconciliation |
| Longer quorum outage | Accepted isolated outage/recovery plan | Deadline behavior, bounded retries and restored majority |
| Sharded service | Chapter 35–40/76 accepted cluster | Router/config/shard dependencies and routed application outcome |
| Application restart | Durable intent/checkpoint design | Restart with original identities and no skipped/doubled effects |

Mark each unexecuted scenario not run. A planned handoff is a useful minimum exercise, not complete production HA certification. Do not run all failure scenarios concurrently or reuse a degraded deployment as a fresh baseline.

## 11. Offline ledger/reconciliation failure drill

Save as `ch78_ledger_check.py` with the `ledger_contract` and `reconcile` helper definitions from Section 5 above the following block. These tests execute the same helpers without opening a database connection.

```python
intents = {"op1": {"_id": "op1", "value": 7}, "op2": {"_id": "op2", "value": 14}}
acked = {"op1"}
actual = dict(intents)
report = reconcile(intents, acked, actual)
assert report["missing_acknowledged"] == [] and report["unacknowledged_present"] == ["op2"]
missing = reconcile(intents, acked, {"op2": intents["op2"]})
assert missing["missing_acknowledged"] == ["op1"]
conflict = reconcile(intents, acked, {"op1": {"_id": "op1", "value": 999}, "op2": intents["op2"]})
assert conflict["changed"] == ["op1"]
entries = [{"kind": "intent", "document": intents["op1"]}, {"kind": "ack", "id": "op1"}]
parsed_intents, parsed_acks = ledger_contract(entries)
assert parsed_intents == {"op1": intents["op1"]} and parsed_acks == {"op1"}
try:
    ledger_contract([{"kind": "ack", "id": "unknown"}])
except RuntimeError:
    pass
else:
    raise AssertionError("Acknowledgement without intent accepted")
print("PASS: acknowledged loss, ambiguous-present, payload conflict and ledger boundary checks")
```

A ledger where outcome recording fails after a database acknowledgement can represent the operation as unacknowledged-present. Reconciliation handles that boundary; it does not invent a client acknowledgement that was not recorded.

## 12. Troubleshooting and stop decisions

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Handoff refused | Eligible secondary/lag and command error | Baseline not ready | Stop; restore healthy eligible redundancy |
| No client errors during election | Election timeline and per-operation timing | Driver recovered within deadline | Record actual transition and correctness rather than inventing errors |
| Selection errors persist | Nested cause, advertised names and roles | Discovery/TLS or ongoing quorum failure | Use Chapter 74/76; verify normal routing |
| Timed-out write present | Intent/outcome and actual payload | Lost acknowledgement | Preserve ambiguity; stable identity prevents duplicate state |
| Acknowledged document missing | Concern, boundary, topology and actual state | Integrity/recovery failure | Block closure; preserve evidence before repair/replay |
| Same identity different payload | Intent/server content and writer ownership | Identity reuse or concurrent writer | Stop; reject conflict rather than overwrite silently |
| Run ends with partial intent set | Ledger and runner interruption | Process/local storage failure | Reconcile partial run; repeat a fresh accepted experiment |
| Replay restores absent intents but hides initial failure | Pre/post reports | Acceptance conflated with remediation | Preserve pre-replay outcome and revise resilience design |
| Application recovered, secondary behind | Member data/history/resources | Catch-up backlog | Wait/diagnose before another maintenance step |
| Retries overload recovered primary | Demand, client attempts and resource metrics | Unbounded retry policy | Bound retry budget/concurrency and revalidate service |

## 13. Acceptance packet and owned cleanup

| Check | Evidence |
|---|---|
| Baseline | Versions, TLS/URI/concerns, healthy declared topology and reserve/history |
| Workload | 60 durable intents, acknowledgement/error records and immutable payloads |
| Handoff | Actual non-forced transition outcome, primary/term timeline and duration |
| Pre-replay | Missing-acknowledged, uncertain-present/absent, conflict/unexpected report |
| Replay | Reviewed stable-identity replay, repeated replay unchanged |
| Recovery | Correct all-member state, application evidence and restored redundancy |
| Scope | Additional failure scenarios explicitly passed/failed/not run |

Save restricted ledger/reports and nonsecret summaries. Require accepted convergence before cleanup. Through the lifecycle connection:

```javascript
var labName = "mongodb_enterprise_ch78_resilience";
var lab = db.getSiblingDB(labName);
if (labName !== "mongodb_enterprise_ch78_resilience" || lab.getName() !== labName) {
  throw new Error("Refusing cleanup outside Chapter 78 database");
}
if (lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch78" }) === null) {
  throw new Error("Ownership missing");
}
if (lab.operations.countDocuments({}) !== 60) throw new Error("Reconcile full intended state first");
for (var i = 0; i < 60; i++) {
  var row = lab.operations.findOne({ _id: "ch78-owned-run:" + i });
  if (!row || row.run_id !== "ch78-owned-run" || row.seq !== i || row.value !== i * 7) {
    throw new Error("Operation state mismatch: " + i);
  }
}
if (lab.dropDatabase().ok !== 1) throw new Error("Owned cleanup failed");
if (db.getSiblingDB(labName).getCollectionInfos().length !== 0) throw new Error("Collections remain");
print("PASS: chapter-owned application-resilience fixture removed");
```

For an interrupted partial run, preserve the report and use a separately recorded lifecycle cleanup decision after reconciling its exact intent set; do not bypass the full-project guard and mark acceptance passed. Retain original members/volumes, credentials, logs/FTDC and other chapter resources. Local evidence follows its recorded retention policy.

Review questions:

1. Why is a timed-out write not equivalent to a definitely absent write?
2. How does stable immutable identity differ from incrementing on replay?
3. What can driver retries hide from application error counts?
4. Why must pre-replay evidence be preserved?
5. Which failures can the local fsynced ledger not survive?
6. Why does new-primary availability not close all-member recovery?
7. What additional evidence is needed for unplanned failure acceptance?
8. How does a transaction/external side effect change the replay contract?

## 14. DBRE/SRE extension — failover game day and reliability acceptance

This extension defines an **approved game-day contract** for the chapter's existing non-forced primary handoff. It does not authorize a production outage, forced stepdown, network partition, replica-set reconfiguration or multi-member disruption.

### 14.1 Preconditions and explicit abort gates

Obtain service-owner, DBRE and change-manager approval; name the game-day commander, observer, rollback authority and communication channel. Confirm all required voting/data-bearing members healthy, a writable primary, current backups and accepted restore drill, adequate oplog/history reserve, no competing maintenance, and fresh application/replica telemetry.

Record baseline P50/P95/P99, error rate, request throughput, connection-pool/server-selection latency, majority write acknowledgements, client retry counts, election term, primary identity and replica lag. Set **service-specific** RTO/RPO and error-budget limits before starting.

**Abort** for existing customer impact, unhealthy quorum, stale monitoring, insufficient recovery evidence, lag/history deficit, resource reserve breach, or a failed preflight application probe. A non-forced stepdown refusal is a stop, not permission to retry with `force`.

### 14.2 Failure timeline and application correctness

| Stage | Evidence | Acceptance condition |
|---|---|---|
| Before handoff | UTC timestamps, healthy members, write/read baseline and durable intent ledger | No missing baseline or pre-existing ambiguous outcomes |
| Handoff request | Exact approved operator, command/result, old primary/term and election timeline | Non-forced action only, no concurrent disruptive change |
| Election interval | Driver topology/selection, retries, timeouts, service SLI and write outcomes | Errors bounded by declared service objective; unknown writes retained for reconciliation |
| New primary | New primary/term, majority write and application read/write success | Application contract works, not merely `hello` success |
| Reconciliation | Every stable operation ID and immutable payload checked against majority-readable state | No lost acknowledged write; unknown outcomes resolved without duplicate effects |
| Member convergence | All expected members healthy, lag/history reserve, resource recovery | Redundancy restored before closure |
| Observation | SLO recovery over declared window, alert delivery and incident handoff | Reviewed evidence and explicit outstanding risks |

A local fsynced ledger is **not** automatically durable across loss of its host or filesystem. Production exactly-once business outcomes may require a durable server-side idempotency store and separate handling of external side effects.

### 14.3 Additional chaos scenarios (design-only until approved)

- **Primary pod/process termination:** validate actual application recovery, not just a planned handoff. Requires isolated environment and separate failure-injection approval.
- **One secondary unavailable:** confirm quorum and failure-mode capacity; never take a second member offline during the drill.
- **DNS/TLS or secret rollout issue:** distinguish client topology discovery from server election and use Chapter 74's fresh-session recovery tests.
- **Disk/CPU pressure during election:** correlate Chapter 75 resource signals and replication catch-up; do not intentionally exhaust a production node.
- **Cross-zone impairment:** review election/voting topology, network partitions and placement without asserting split-brain immunity from a single drill.

Do not report a planned handoff as proof of unplanned node, zone, region or disaster recovery readiness. Those are distinct acceptance scopes.

### 14.4 Fail-closed HA evidence manifest

Save as `ch78-ha-acceptance.json`:

```json
{
  "chapter": 78,
  "change_id": "NOT_ASSIGNED",
  "game_day_commander": "NOT_ASSIGNED",
  "service_owner": "NOT_ASSIGNED",
  "dbre_reviewer": "NOT_ASSIGNED",
  "quorum_and_recovery_preflight_passed": false,
  "service_slo_and_rto_rpo_defined": false,
  "intent_ledger_complete": false,
  "nonforced_handoff_observed": false,
  "client_recovery_timeline_recorded": false,
  "acknowledged_writes_reconciled": false,
  "ambiguous_writes_reconciled": false,
  "idempotent_replay_verified": false,
  "all_members_converged": false,
  "post_failover_slo_accepted": false,
  "evidence_references": []
}
```

Save as `ch78_ha_gate.py`:

```python
import json
from pathlib import Path

p = json.loads(Path("ch78-ha-acceptance.json").read_text(encoding="utf-8"))
checks = (
    "quorum_and_recovery_preflight_passed", "service_slo_and_rto_rpo_defined",
    "intent_ledger_complete", "nonforced_handoff_observed",
    "client_recovery_timeline_recorded", "acknowledged_writes_reconciled",
    "ambiguous_writes_reconciled", "idempotent_replay_verified",
    "all_members_converged", "post_failover_slo_accepted",
)
missing = [key for key in checks if p.get(key) is not True]
for key in ("change_id", "game_day_commander", "service_owner", "dbre_reviewer"):
    if not isinstance(p.get(key), str) or not p[key].strip() or p[key].startswith("NOT_"):
        missing.append(key)
if not isinstance(p.get("evidence_references"), list) or not p["evidence_references"]:
    missing.append("evidence_references")
if missing:
    raise SystemExit("NOT ACCEPTED: " + ", ".join(missing))
print("PASS: declared HA evidence complete; independent verification required")
```

Run `python ch78_ha_gate.py`. The untouched template must fail. A passing manifest does not validate a real election, SLO or data integrity without independent review of actual logs, ledger and application metrics.

### 14.5 Recovery decision and sign-off

If the application cannot select the new primary, reconcile driver DNS/TLS/topology before changing database votes. If writes are ambiguous, inspect their stable IDs before replay. If any acknowledged write is missing, **do not declare success**; preserve evidence and invoke the data-integrity incident process. If a member remains lagged or needs initial sync, keep the game day open and apply an approved recovery plan.

Close only with verified application service recovery, complete acknowledged/ambiguous write reconciliation, healthy required redundancy, recovery reserves and named owner sign-off. Mark unexecuted scenarios **NOT RUN**.

---

## 15. Official references and validation status

1. [MongoDB 8.0 — Retryable Writes](https://www.mongodb.com/docs/v8.0/core/retryable-writes/).
2. [PyMongo — Client-Side Operation Timeout](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/csot/): verify exact pinned driver semantics.
3. [MongoDB 8.0 — replSetStepDown](https://www.mongodb.com/docs/v8.0/reference/command/replSetStepDown/).

Documentation reviewed on 2026-10-12. The immutable operation contract, local ledger, operation count/deadlines and acceptance gates are teaching designs. Python/JavaScript syntax and actual offline ledger/reconciliation helpers were checked. These checks do not validate live elections, PyMongo retries/deadlines, acknowledgement durability, member convergence or service failover. No live failover or process fault was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline ledger acceptance complete. Runtime validation remains pending until the authorized workload, handoff, pre/post reconciliation, replay and member recovery evidence are recorded.

Previous: [Chapter 77 — Production Data Modeling and Query Tuning Project](77-production-data-modeling-and-query-tuning-project.md).  
Next: Chapter 79 — Backup Restore and Disaster Recovery Project.
