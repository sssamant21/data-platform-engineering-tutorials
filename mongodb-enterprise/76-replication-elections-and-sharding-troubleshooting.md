# 76 — Replication Elections and Sharding Troubleshooting

Part 10 — Troubleshooting and Production Projects

**Audience:** DBREs, SREs, Platform Engineers and on-call engineers.  
**Goal:** Diagnose replication/election and routing failures, distinguish service availability from recoverability, and reconcile acknowledged data before declaring recovery.  
**Baseline:** Accepted retained MongoDB 8.0 / FCV 8.0 three-member TLS/SCRAM replica set. Sharding observations require the separately accepted Chapter 35–40 cluster. Record exact server, mongosh and client versions. Core lab is Community-compatible.  
**Status:** Written; syntax and offline topology/recovery checks complete; live handoff, member reconciliation and sharded diagnostics pending.  
**Prerequisites:** Chapters 25–40, 49–56, 63–64 and 69–75; topology inventory, application concern contract and maintenance/recovery ownership.  
**Estimated time:** 60–90 minutes for replica-set acceptance; sharded observation has its own deployment scope.

## 1. Incident contract and first response

Record the affected application, deployment, UTC window, selected read/write concerns, observed errors, primary/router identities and recent maintenance/network/resource changes. Preserve election/replication logs and FTDC through Chapter 69's restricted evidence workflow.

The lab creates an owned data fixture, records a majority-acknowledged barrier, optionally rehearses one planned non-forced handoff under the existing accepted maintenance procedure, and reconciles the fixture on every member. Sharding diagnostics are read-only on the retained accepted sharded lab. The chapter does not force reconfiguration, delete member data, induce network partitions or reshard business data.

Acceptance means correct acknowledged data and application behavior, healthy declared redundancy, sufficient retained history and verified routing. A new primary or reachable mongos alone is insufficient.

## 2. Separate failure boundaries

| Boundary | Evidence | Investigation direction |
|---|---|---|
| Client cannot select server | Nested driver error, advertised hosts, TLS and set name | Chapter 74 connection/topology discovery |
| Primary unavailable | Member states, votes/eligibility, election logs and majority reachability | Quorum/network/eligibility |
| Secondary lagging | Optimes, sync source, write demand, I/O and retained history | Catch-up capacity and recovery horizon |
| Repeated elections | Term/primary timeline, heartbeats and service impact | Network instability, resource stalls or configuration |
| Router reachable, query fails | mongos discovery, config server and shard replica health | Routing/dependency boundary |
| Sharded query slow | Exact predicate, explain per-shard work and placement | Fan-out, skew, local index or hot shard |
| Data differs after recovery | Stable identities, acknowledgement ledger and recovery boundary | Rollback/replay/restore reconciliation |

Avoid diagnosing a server-selection timeout as a quorum failure before checking TLS and discovery. Conversely, a reachable member can still be unable to participate in a usable majority.

## 3. Replica-set evidence

Connect through the accepted observer. For member-local observations use each recorded direct endpoint with verified TLS; for application verification use the normal replica-set-aware URI.

```javascript
var admin = db.getSiblingDB("admin");
printjson({ observedAt: new Date(), version: db.version(), hello: db.hello() });
var status = admin.runCommand({ replSetGetStatus: 1 });
if (status.ok !== 1) throw new Error("Replica observation failed");
printjson({ set: status.set, term: status.term, date: status.date, myState: status.myState,
  members: status.members.map(m => ({ name: m.name, self: m.self, health: m.health,
    stateStr: m.stateStr, optime: m.optime, optimeDate: m.optimeDate,
    syncSourceHost: m.syncSourceHost, lastHeartbeatMessage: m.lastHeartbeatMessage })) });
```

Replica status reflects the responding member's view.[1] Compare views and clock/time bounds before interpreting contradictory observations. Record member configuration/votes/priorities through the authorized configuration observer, not by guessing from state labels.

A primary needs the applicable voting majority and an electable member under the configured topology.[2] Member count alone does not define quorum when arbiters, nonvoters or special configurations exist. The fixture assumes the previously accepted three data-bearing voting members, with eligible secondaries; it does not authorize topology changes.

Use Chapter 29's lag/history method. Timestamp differences are diagnostic estimates, not an exact document reconciliation. Healthy heartbeats and equal displayed dates do not prove every acknowledged business operation is present.

## 4. Replication lag and recoverability

Compare source arrival rate, secondary apply progress, network and storage performance. A secondary that applies at the arrival rate does not drain an existing backlog. A secondary whose required history has expired may need supported initial sync/member replacement from Chapter 30.

Distinguish replication lag from CDC materialization lag. They can have different checkpoints and recovery owners. Before restart/rejoin, record the source history window and required outage/catch-up budget.

Do not force a lagged member into primary role to make a service green. Do not remove oplog or dbPath files to accelerate catch-up. A rollback or restore needs acknowledged-write reconciliation and the recovery packet from Chapters 31 and 49–56.

## 5. Election triage and stop conditions

Build a primary/term timeline and correlate it with heartbeat failures, resource stalls, client errors and changes. Expected planned handoffs differ from repeated unexplained elections.

| Finding | Action boundary |
|---|---|
| Another member degraded | Stop further disruptive maintenance; restore declared redundancy |
| No eligible caught-up secondary | Investigate eligibility/lag; do not add force to bypass refusal |
| Client still addresses old primary directly | Repair application discovery/routing contract |
| Quorum lost | Restore original member/network availability through accepted recovery plan |
| Divergent histories suspected | Preserve data/logs and reconcile acknowledged writes before publishing |
| Evidence stale/missing | Restore observation coverage; keep diagnosis unresolved |

A forced reconfiguration can alter safety/recovery semantics. It is not a generic “no primary” command. Use the already documented disaster-recovery decision and supported version-specific procedure if restoration of the original topology is impossible.

## 6. Lab A — acknowledged data barrier

Use the lifecycle identity through Chapter 42's verified TLS/SCRAM connection to the retained replica-set primary. Create once, with no concurrent fixture writers.

```javascript
var labName = "mongodb_enterprise_ch76_topology";
var lab = db.getSiblingDB(labName);
function check(condition, message) { if (!condition) throw new Error(message); }
check(lab.getCollectionInfos().length === 0, "Namespace already exists");
var beforeHello = db.hello();
check(beforeHello.isWritablePrimary === true, "Expected primary");
var beforeStatus = db.getSiblingDB("admin").runCommand({ replSetGetStatus: 1 });
check(beforeStatus.ok === 1 && beforeStatus.members.length === 3, "Expected accepted three-member lab");
check(beforeStatus.members.every(m => m.health === 1 &&
  ["PRIMARY", "SECONDARY"].includes(m.stateStr)), "Members not accepted");
check(beforeStatus.members.filter(m => m.stateStr === "PRIMARY").length === 1,
      "Expected one primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch76", createdAt: new Date() });
var rows = [];
for (var i = 0; i < 100; i++) rows.push({ _id: i, seq: i, value: i * 4 });
lab.items.insertMany(rows, { writeConcern: { w: "majority", wtimeout: 10000 } });
lab.barrier.insertOne({ _id: "before-handoff", expectedRows: 100, expectedSum: 19800 }, {
  writeConcern: { w: "majority", wtimeout: 10000 }
});
check(lab.items.countDocuments({}) === 100, "Fixture count mismatch");
printjson({ originalPrimary: beforeHello.me, acknowledgedRows: 100,
            expectedSum: 19800, observedAt: new Date() });
```

Expected: 100 majority-acknowledged items and an acknowledged barrier. The fixed identities allow exact reconciliation; a simple count is not enough. Preserve original primary name and UTC start before any optional handoff.

## 7. Lab B — optional planned non-forced handoff

Execute only on the already accepted isolated retained lab under Chapter 71's maintenance gates. Stop if service/recovery/resource evidence is not accepted or another change is active. This is a planned handoff, not an unplanned crash or partition test.

Through the authorized maintenance identity connected to the current primary:

```javascript
printjson(db.getSiblingDB("admin").runCommand({
  replSetStepDown: 60, secondaryCatchUpPeriodSecs: 10, force: false
}));
```

The command can refuse when no suitable caught-up electable secondary exists; diagnose that refusal rather than switching to force.[3] Capture the actual response or disconnect/error and verify resulting member state. A client error is neither proof that stepdown failed nor proof that it succeeded.

Open a fresh normal replica-set-aware application session using the original TLS/authentication contract. Poll hello at the approved bounded interval for up to the lab's 120-second observation budget. Record selection/election delay and errors, then stop on timeout for diagnosis. Do not issue repeated stepdowns while waiting.

```javascript
var elected = db.hello();
check(elected.isWritablePrimary === true, "Fresh session has not selected a writable primary");
printjson({ currentPrimary: elected.me, set: elected.setName, observedAt: new Date() });
```

Compare current primary with the recorded original during its stepdown exclusion period and record actual roles/term. Reconnecting late can miss that interval; in that case use the event timeline rather than claiming the live name proves the handoff. Do not force the original primary back simply to restore its old name. A healthy accepted role distribution is the recovery criterion.

If the optional drill is skipped, record it not run and continue member reconciliation of the unchanged fixture. No live handoff acceptance is claimed from offline work.

## 8. Lab C — post-transition write and exact reconciliation

In the fresh normal application session, reestablish the `check` helper if needed. Require the original acknowledged fixture, then perform one stable desired-state write.

```javascript
function check(condition, message) { if (!condition) throw new Error(message); }
var lab = db.getSiblingDB("mongodb_enterprise_ch76_topology");
check(lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch76" }) !== null,
      "Ownership missing");
check(lab.barrier.findOne({ _id: "before-handoff" }) !== null, "Acknowledged barrier absent");
lab.after.updateOne({ _id: "post-transition" }, { $set: { value: "accepted" } }, {
  upsert: true, writeConcern: { w: "majority", wtimeout: 10000 }
});
var result = lab.items.find({}, { _id: 1, seq: 1, value: 1 }).sort({ _id: 1 }).toArray();
check(result.length === 100, "Missing acknowledged items");
for (var i = 0; i < 100; i++) {
  check(result[i]._id === i && result[i].seq === i && result[i].value === i * 4,
        "Acknowledged item mismatch at " + i);
}
check(result.reduce((sum, row) => sum + row.value, 0) === 19800, "Value total mismatch");
print("PASS: application write and acknowledged fixture reconciled");
```

For each recorded member, open a separate verified direct observer session with secondary reads intentionally enabled, such as URI `readPreference=secondaryPreferred&directConnection=true`. Run the exact item/barrier/post-transition checks after allowing bounded catch-up. A lagged read must not be reported as permanent loss from a single observation.

Record member identity, role, evidence time and convergence delay. Require the declared one-primary/two-secondary healthy baseline and Chapter 29's replication/history acceptance before closing. Majority acknowledgement does not imply every secondary was instantly current; direct-member reconciliation establishes the lab's final convergence.

On an ambiguous post-transition write, inspect the stable `_id` desired state and acknowledgements before deciding to retry. The lab's idempotent update is not a general exactly-once business-write guarantee.

## 9. Sharding diagnostics on the accepted retained cluster

Connect to recorded mongos endpoints, not directly to a shard for application verification. Use the authorized observer on the accepted Chapter 35–40 lab; do not execute these observations on the replica-set-only lab and label them sharding acceptance.

```javascript
printjson({ observedAt: new Date(), hello: db.hello() });
var shards = db.getSiblingDB("admin").runCommand({ listShards: 1 });
if (shards.ok !== 1) throw new Error("Shard inventory failed");
printjson(shards);
sh.status();
```

Require mongos identity (`msg: "isdbgrid"`), expected shard inventory and supported metadata summary.[4] Capture config-server and each shard replica-set health through their authorized member observers. Router reachability cannot substitute for those dependencies.

For the exact owned collection/query retained from Chapter 37, compare a shard-key-targeted predicate and a deliberately broader query using that chapter's bounded fixtures. Preserve projection/sort/result semantics and inspect explain per-shard work. Do not invent a production namespace or shard key from a generic example.

| Observation | Interpretation boundary |
|---|---|
| Targeted query visits expected shard(s) | Routing evidence for that exact predicate/placement |
| Broad query fans out | Scatter/gather evidence; not proof that every fan-out is a defect |
| One shard has high local work | Local indexing/selectivity or placement/load may dominate |
| Uneven data distribution | Does not automatically imply uneven request demand |
| Movement/balancing active | Correlate resource/lag with intended policy and exact-version behavior |

Do not flush router caches, move ranges, change balancer policy or reshard merely because one query is slow. Identify ownership, placement metadata, actual routing and local resource/query evidence first. Sharded restore/metadata recovery follows Chapters 39 and 55–56.

## 10. Offline recovery-gate lab

Save as `ch76_recovery_gate.py`. The gate represents reviewed evidence for the declared replica-set lab plus optional router/shard acceptance; it does not compute actual quorum from raw member count.

```python
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Recovery:
    evidence_fresh: bool
    expected_members_healthy: bool
    configured_quorum_verified: bool
    writable_primary_verified: bool
    acknowledged_data_reconciled: bool
    application_contract_verified: bool
    retained_history_accepted: bool
    sharded_scope: bool = False
    routing_dependencies_verified: bool = False


def gate(packet):
    for name, value in vars(packet).items():
        if not isinstance(value, bool):
            raise ValueError("Explicit reviewed boolean evidence required: " + name)
    required = ["evidence_fresh", "expected_members_healthy", "configured_quorum_verified",
                "writable_primary_verified", "acknowledged_data_reconciled",
                "application_contract_verified", "retained_history_accepted"]
    if packet.sharded_scope:
        required.append("routing_dependencies_verified")
    missing = [name for name in required if not getattr(packet, name)]
    return {"decision": "accepted" if not missing else "stop_and_investigate",
            "missing": missing}


baseline = Recovery(True, True, True, True, True, True, True)
assert gate(baseline)["decision"] == "accepted"
for name in ["evidence_fresh", "expected_members_healthy", "configured_quorum_verified",
             "writable_primary_verified", "acknowledged_data_reconciled",
             "application_contract_verified", "retained_history_accepted"]:
    result = gate(replace(baseline, **{name: False}))
    assert result["decision"] == "stop_and_investigate" and name in result["missing"]
    print(name, result)
sharded = replace(baseline, sharded_scope=True)
assert gate(sharded)["decision"] == "stop_and_investigate"
assert gate(replace(sharded, routing_dependencies_verified=True))["decision"] == "accepted"
print("PASS: replica/sharded acceptance requires complete reviewed evidence")
```

Run `python ch76_recovery_gate.py`. Expected: complete replica evidence accepted, every missing requirement blocked, sharded scope blocked until routing dependencies pass. A restored primary with unreconciled acknowledged data remains unaccepted.

## 11. Recovery and escalation branches

| Finding | Accepted recovery direction | Verification |
|---|---|---|
| Discovery/TLS issue | Restore correct endpoint/trust through authoritative owner | Fresh normal application connection and intended role selection |
| Lag with retained history | Restore apply capacity/network and bound competing work | Backlog drains; member/data/history acceptance |
| Required history expired | Planned initial sync/member replacement | Correct source, retained topology and full data reconciliation |
| Quorum outage | Recover original members/routes under accepted plan | Configured majority and healthy declared redundancy |
| Rollback/divergence | Preserve evidence and reconcile acknowledged outcomes | Supported recovery boundary and application correctness |
| Router failure | Restore accepted router/service discovery | Normal routed application operations |
| Shard/config-server issue | Recover the specific dependency through its owner | Cluster metadata/routing plus affected data acceptance |

Escalate when source history, quorum safety, corruption or metadata integrity cannot be established. Include exact versions, topology/term timeline, acknowledgements, logs/FTDC and attempted actions. Do not erase member data or make forced topology changes to shorten the diagnostic phase.

## 12. Troubleshooting matrix

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| No primary seen by one app | Nested client errors and member views | Discovery/trust versus actual quorum loss | Resolve boundary; verify fresh app routing |
| Stepdown refused | Eligible secondary/config and lag | No suitable caught-up candidate | Stop drill; restore accepted secondary state |
| New primary exists but writes fail | Client URI/roles/concerns and nested error | Old direct route or client policy | Restore normal discovery and verify actual write outcome |
| One secondary grows lag | Apply/source rate and disk/network | Insufficient catch-up capacity | Remediate resource/workload and verify retained history |
| Elections repeat | Term/heartbeat/log/resource timeline | Network or process stalls | Correct supported cause; observe stable service window |
| Counts match but data differs | Exact IDs/values and acknowledgement ledger | Partial/divergent state | Block closure; reconcile supported recovery boundary |
| mongos responds but query fails | Config/shard replica health and routing | Dependency outage | Recover affected dependency; verify routed query/data |
| Fan-out query slow | Exact predicate and per-shard explain | Missing target key or local work | Review targeting/index/placement contract |
| One shard hot despite balanced bytes | Request demand, query routing and resource metrics | Workload skew | Address workload/placement through accepted design |
| Cleanup attempted before convergence | Member data/state/history packet | Service-only recovery assumed complete | Finish convergence acceptance before fixture removal |

## 13. Acceptance evidence and cleanup

| Check | Required evidence |
|---|---|
| Identity/config | Exact versions, set/member roles, votes/eligibility and UTC timeline |
| Fixture | 100 acknowledged rows, exact values and sum 19800, pre-transition barrier |
| Optional handoff | Actual non-forced command outcome, term/role timeline and fresh client recovery |
| Post-transition | Stable majority desired-state write and correct acknowledged fixture |
| Member convergence | Exact checks on all recorded members; healthy declared baseline/history |
| Sharded scope | Actual mongos/config/shard inventory and retained owned routing-query evidence |
| Gate | Actual offline missing-evidence/sharded cases passed |

Mark optional handoff and sharded diagnostics not run when their accepted deployment/procedure is unavailable. No offline test converts those items into live acceptance.

After saving nonsecret evidence and confirming convergence, clean only the owned replica-set fixture through the lifecycle identity:

```javascript
function check(condition, message) { if (!condition) throw new Error(message); }
var labName = "mongodb_enterprise_ch76_topology";
var lab = db.getSiblingDB(labName);
if (labName !== "mongodb_enterprise_ch76_topology" || lab.getName() !== labName) {
  throw new Error("Refusing cleanup outside Chapter 76 database");
}
check(lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch76" }) !== null,
      "Ownership missing");
check(lab.items.countDocuments({}) === 100, "Fixture needs reconciliation");
check(lab.after.findOne({ _id: "post-transition", value: "accepted" }) !== null,
      "Post-transition acceptance missing");
check(lab.dropDatabase().ok === 1, "Owned cleanup failed");
check(db.getSiblingDB(labName).getCollectionInfos().length === 0, "Collections remain");
print("PASS: chapter-owned topology fixture removed");
```

The handoff does not change member configuration and does not require forcing the original primary back. Retain all original members, volumes, routers/config servers, logging/FTDC, credentials and prior chapter resources under their existing ownership. Sharding observations changed no policy or data.

Review questions:

1. Why does member count alone not establish voting quorum?
2. Why does majority acknowledgement not imply instant visibility on every secondary?
3. Why should a non-forced stepdown refusal remain a stop condition?
4. How can a client timeout hide a connection failure rather than an election failure?
5. What changes when a secondary's needed history is no longer retained?
6. Why does router availability not prove shard/config-server recovery?
7. How can balanced bytes coexist with a hot shard?
8. What evidence closes recovery beyond a new primary?

## 14. DBRE/SRE extension — quorum safety, data reconciliation and sharded recovery

This extension is an incident command checklist, not permission to force an election, reconfigure votes, remove members or alter shard metadata.

### 14.1 Protect quorum and acknowledged writes

Identify voting members, election eligibility, actual reachable majority, current term/primary, member optimes and network partitions **before** any topology action. A three-data-bearing-member lab is not a universal model for arbiters, hidden/delayed members or custom votes.

- **No writable primary:** verify quorum, reachability, member logs, clock/host health and client topology discovery. Do not assume a forced reconfiguration will preserve acknowledged data.
- **Repeated elections:** correlate term changes with network, CPU/IO stalls, storage and heartbeat failures. Avoid repeated manual stepdowns that worsen availability.
- **Lagging secondary:** check oplog window, sync source, IO/CPU capacity and history needed for catch-up. If history is insufficient, use an explicitly approved initial-sync/restore plan, not an unreviewed deletion of data files.
- **Ambiguous client write:** reconcile using the application's idempotency key, transaction/session metadata where available and majority-acknowledged state. Do not blindly retry non-idempotent writes.
- **Divergent member state:** preserve forensic evidence and the last accepted backup/recovery point; escalate before any destructive resync.

A majority-acknowledged write does not imply that every secondary has applied it at the same instant. The acceptance test must reflect the application's actual read concern, read preference, write concern and causality contract.

### 14.2 Read-only incident triage

Use the authorized TLS/SCRAM observer identity. The commands below are intended for the accepted replica-set lab and must be scoped to the verified deployment.

```javascript
var a = db.getSiblingDB("admin");
var hello = a.runCommand({ hello: 1 });
var rs = a.runCommand({ replSetGetStatus: 1 });
if (hello.ok !== 1 || rs.ok !== 1) throw new Error("Topology observation failed");
printjson({
  observedAt: new Date(),
  set: rs.set,
  primaryHint: hello.primary,
  writablePrimary: hello.isWritablePrimary,
  members: rs.members.map(m => ({
    name: m.name, health: m.health, state: m.stateStr,
    optimeDate: m.optimeDate, lastHeartbeatMessage: m.lastHeartbeatMessage
  }))
});
```

This output reflects the responding member's view. Correlate with member-local logs and independent monitoring; do not treat a single `hello` as proof of cluster-wide consensus or absence of split-brain symptoms.

### 14.3 Sharded outage boundaries

| Symptom | Required evidence | Recovery guardrail |
|---|---|---|
| mongos reachable but writes fail | Router logs, target shard state, config-server health, routing metadata | Verify affected shard and metadata; do not assume router health equals data availability |
| Hot shard / uneven load | Targeting, chunk placement, per-shard IO/CPU and query distribution | Distinguish workload skew from raw byte imbalance before migration |
| Balancer/migration issues | Balancer state, migration errors, donor/recipient health and free space | Avoid ad hoc balancing changes during resource or replication incidents |
| Stale routing symptoms | Client/router errors, config server availability and metadata propagation | Follow supported metadata recovery; never edit config collections directly |
| Cross-shard consistency concern | Application transaction/read concern, operation history and per-shard health | Preserve acknowledged outcome and reconcile through supported application contracts |

For a sharded incident, collect separate evidence for **mongos, config-server replica set and each affected shard replica set**. Do not run the replica-set fixture as a certification of sharded recovery.

### 14.4 Controlled recovery and closure

1. Declare incident commander, severity, affected service/tenants, UTC window, change freeze and escalation contacts.
2. Preserve telemetry, election logs, term/optime timeline, backup/recovery evidence and sanitized client error samples.
3. Stabilize the underlying network, host, storage or resource issue before considering topology intervention.
4. If a planned handoff is required, use the chapter's **non-forced** maintenance procedure with explicit preflight and refusal-as-stop behavior.
5. Verify one accepted primary, healthy required voting/data-bearing members, stable replication, adequate history reserve and no ongoing elections.
6. Reconcile majority-acknowledged fixture/application writes under the declared consistency contract and verify correct client read/write behavior.
7. For sharded deployments, separately verify router targeting, config-server availability, affected shard health and application correctness.
8. Close only after SLO recovery, post-incident observation, recovery owner sign-off and unresolved risks are assigned.

### 14.5 Fail-closed recovery manifest

Save as `ch76-recovery.json`:

```json
{
  "chapter": 76,
  "incident_id": "NOT_ASSIGNED",
  "incident_commander": "NOT_ASSIGNED",
  "dbre_reviewer": "NOT_ASSIGNED",
  "service_owner": "NOT_ASSIGNED",
  "quorum_and_votes_recorded": false,
  "primary_and_term_stable": false,
  "required_members_healthy": false,
  "replication_and_oplog_reserve_accepted": false,
  "acknowledged_writes_reconciled": false,
  "application_read_write_accepted": false,
  "backup_and_recovery_evidence_accepted": false,
  "shard_router_config_health_accepted_or_na": false,
  "monitoring_and_slo_recovered": false,
  "evidence_references": []
}
```

The sharded field may be true for a replica-set-only incident **only with documented reviewer approval of not-applicable scope**.

Save as `ch76_recovery_gate.py`:

```python
import json
from pathlib import Path

p = json.loads(Path("ch76-recovery.json").read_text(encoding="utf-8"))
checks = (
    "quorum_and_votes_recorded", "primary_and_term_stable",
    "required_members_healthy", "replication_and_oplog_reserve_accepted",
    "acknowledged_writes_reconciled", "application_read_write_accepted",
    "backup_and_recovery_evidence_accepted",
    "shard_router_config_health_accepted_or_na", "monitoring_and_slo_recovered",
)
missing = [key for key in checks if p.get(key) is not True]
for key in ("incident_id", "incident_commander", "dbre_reviewer", "service_owner"):
    if not isinstance(p.get(key), str) or not p[key].strip() or p[key].startswith("NOT_"):
        missing.append(key)
if not isinstance(p.get("evidence_references"), list) or not p["evidence_references"]:
    missing.append("evidence_references")
if missing:
    raise SystemExit("NOT ACCEPTED: " + ", ".join(missing))
print("PASS: recovery declarations complete; independently validate evidence")
```

Run `python ch76_recovery_gate.py`; the untouched template must fail. This offline gate checks declarations, not actual quorum, data safety or recovery. Live handoff and sharded recovery drills remain separately pending.

---

## 15. Official references and validation status

1. [MongoDB 8.0 — replSetGetStatus](https://www.mongodb.com/docs/v8.0/reference/command/replSetGetStatus/).
2. [MongoDB 8.0 — Replica Set Elections](https://www.mongodb.com/docs/v8.0/core/replica-set-elections/).
3. [MongoDB 8.0 — replSetStepDown](https://www.mongodb.com/docs/v8.0/reference/command/replSetStepDown/).
4. [MongoDB 8.0 — sh.status](https://www.mongodb.com/docs/v8.0/reference/method/sh.status/).

Documentation reviewed on 2026-10-12. Fixture, observation budgets and reviewed-evidence gate are teaching designs. Python/JavaScript syntax, fixture arithmetic and actual offline recovery-gate cases were checked, including invalid evidence inputs. These checks do not validate live elections, concerns, member convergence, routing metadata or recovery. No live member or sharded configuration change was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline recovery-gate acceptance complete. Runtime validation remains pending until the authorized replica-set/member/sharded evidence and owned cleanup are recorded.

Previous: [Chapter 75 — Disk Pressure Cache Pressure and Resource Incidents](75-disk-pressure-cache-pressure-and-resource-incidents.md).  
Next: Chapter 77 — Production Data Modeling and Query Tuning Project.
