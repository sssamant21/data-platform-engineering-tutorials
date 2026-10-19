# 71 — Daily Administration and Maintenance Runbook

Part 9 — Specialized Data and Observability

**Audience:** DBREs, SREs, Platform Engineers and on-call operators.  
**Goal:** Run an evidence-based daily review, execute one reversible owned maintenance change, and verify service, data and recovery readiness before closing the change.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 three-member replica set; exact recorded mongosh, Python 3.11+ and pinned reviewed PyMongo 4.x. Core exercises are Community-compatible. Enterprise/operator observations require their already accepted deployments.  
**Status:** Written; script syntax and offline maintenance-gate checks complete; live daily review and maintenance acceptance pending.  
**Prerequisites:** Chapters 17–24, 25–32, 41–48, 49–62 and 69–70; current inventory, ownership, monitoring and recovery records.  
**Estimated time:** 60–90 minutes for the lab; daily production duration depends on scope and exceptions.

## 1. Operational contract

Daily administration is a review of service health and operational risk. It is not a schedule of unconditional restarts, collection scans or storage reclamation. Each finding becomes either evidence of acceptable state or an owned action with severity and due time.

The lab performs a bounded read-only observation, verifies a synthetic application's read/write contract, rehearses index hiding/unhiding on an owned collection, and tests stop decisions with offline evidence. It does not restart members, resize storage, rotate production logs or change global profiling.

Acceptance requires:

- Recorded deployment/member identity and fresh service evidence.
- Healthy declared replica-set baseline, resource headroom and recovery evidence.
- Explicit missing-data and stop decisions.
- A correct 200-row fixture and deterministic query results.
- Owned reversible index change with metadata and query verification.
- Failure detection when the index is hidden and restoration before cleanup.
- A closed maintenance record with post-checks and unresolved risks.

## 2. Daily review order

Start with user impact and telemetry freshness. A missing collector is an evidence gap, not a healthy database. Use Chapter 70's actual service objectives and action thresholds instead of substituting universal numbers.

| Review | Evidence | Decision/owner |
|---|---|---|
| Service | Request success, latency, timeouts, correctness and active incidents | Service owner with DBRE |
| Monitoring | Expected members/series, scrape success, clock and log coverage | Monitoring owner |
| Topology | Primary, member states, health, elections, replication/history headroom | DBRE |
| Resources | Per-volume free space/growth, I/O latency, CPU, memory/cache and throttling | DBRE/platform |
| Workload | Demand, slow query patterns, client pools, ingestion and TTL activity | Application/data owner |
| Recovery | Backup status/recovery point, restore-test evidence, key/credential dependencies | Recovery owner |
| Lifecycle | Certificate expiry, rotations, automation drift, scheduled changes | Security/platform/DBRE |
| Follow-up | Open capacity/reliability actions and previous maintenance exceptions | Named action owner |

Record UTC review window, exact environment, source dashboards/logs and owner. A three-member replica set with one member down can still serve traffic, but it is outside this lab's maintenance-ready baseline. Diagnose the degraded state before starting another disruptive action.

## 3. Read-only database observation

Connect using Chapter 42's TLS/SCRAM procedure with an authorized observer. Use the replica-set-aware application URI for service checks; use a recorded direct member endpoint only when collecting member-local evidence. Do not mix counters from members or processes.

```javascript
var admin = db.getSiblingDB("admin");
printjson({ observedAt: new Date(), version: db.version(), hello: db.hello() });
var status = admin.runCommand({ replSetGetStatus: 1 });
if (status.ok !== 1) throw new Error("Replication observation failed");
printjson({ set: status.set, date: status.date, myState: status.myState,
  members: status.members.map(m => ({
    name: m.name, self: m.self, health: m.health, stateStr: m.stateStr,
    optimeDate: m.optimeDate, lastHeartbeatMessage: m.lastHeartbeatMessage
  })) });
var process = admin.runCommand({ serverStatus: 1 });
if (process.ok !== 1) throw new Error("Process observation failed");
printjson({ host: process.host, pid: process.pid, uptime: process.uptime,
  connections: process.connections, opcounters: process.opcounters,
  opLatencies: process.opLatencies });
```

Expected: actual observed identity, one primary and two healthy secondaries for the declared baseline. Replica status describes the responding member's perspective; correlate member-local observations and monitoring when diagnosing disagreements.[1] A successful ping alone does not prove replication, application access or backup recoverability.

Do not assert zero replication lag from equal displayed timestamps alone. Use the accepted Chapter 29 lag/history method, timestamps/roles and application concern contract. Global counters require valid deltas from Chapter 69; a lifetime total is not the current workload rate.

Inspect collection options/indexes only for the relevant scope. Avoid automatic daily enumeration and expensive statistics across every namespace. Retrieve full current operations or query payloads only through scoped, authorized incident procedures.

## 4. Host, Kubernetes and automation review

Map each member to its actual service/pod, host, PVC/volume and cloud disk. Review restarts, OOM events, CPU throttling, filesystem free space, I/O limits, latency and queueing. Container limits and host totals are different units of capacity.

On native deployments, compare the active service configuration with the approved baseline and verify log/FTDC destinations and rotation. On operator-managed deployments, inspect desired status, agent/controller health and pending reconciliation. Do not hand-edit generated resources as a routine repair; identify the authoritative configuration owner first.

The presence of a Running pod is not readiness acceptance. Verify the database role, replication and service query contract. Persistent volumes must retain the intended identity and data lifecycle before pod maintenance is considered.

For sharded deployments add router/config-server/shard health, balancing/placement and targeted query evidence from Chapters 33–40. The three-member replica-set lab does not certify sharded maintenance readiness.

## 5. Recovery and lifecycle evidence

Review whether backups are recent, complete and usable for the required recovery scope. Capture the recoverable boundary, last successful restore drill, RPO/RTO result and missing dependencies. A completed backup job does not establish restore correctness.

Check credential/certificate lifecycle against the agreed renewal lead time. Verify service accounts are owned and least-privilege grants match current workloads. Record expiry and rotation readiness without copying private keys or secrets into the daily report.

Review source oplog/CDC history and downstream materialization freshness separately. A healthy source with an expired consumer token or an old warehouse checkpoint needs an owned pipeline recovery action. Do not clear that finding because replica-set health is green.

Daily review should not initiate `repair`, `compact`, full `validate`, index rebuilds, bulk deletes or rolling restarts automatically. Validation can have substantial locking/I/O effects; foreground validation can also reconcile count/size statistics.[2] Choose scope, exact-version options, role/replication implications and a maintenance window before executing it.

## 6. Maintenance packet and stop gates

Before a change, record:

- Exact target deployment/member/namespace and ownership.
- Trigger, expected behavior and measurable acceptance criteria.
- Current service/topology/resource/recovery evidence and its age.
- Authoritative configuration and maintenance owner.
- Execution order, maximum duration and explicit stop conditions.
- Reversal/recovery steps and limitations once data changes.
- Post-checks, observation window and handoff record.

For this lab, all three members must be healthy, telemetry fresh and declared reserve/recovery checks accepted. Production exceptions require a specific risk decision within the organization's existing change process. Do not weaken the evidence gate silently.

A reversible configuration step is not necessarily harmless. A hidden index can change planner choices and foreground performance. A data deletion cannot be reversed by restoring a setting. After a failed step, pause dependent work and verify state before deciding to retry or reverse it.

## 7. Lab A — owned application fixture

Use the existing authorized lifecycle identity through mongosh. Create a fresh namespace and collection. No background writer is needed.

```javascript
var labName = "mongodb_enterprise_ch71_maintenance";
var lab = db.getSiblingDB(labName);
if (lab.getCollectionInfos().length !== 0) throw new Error("Namespace already exists");
if (!db.hello().isWritablePrimary) throw new Error("Expected writable primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch71", createdAt: new Date() });
lab.items.createIndex({ tenant: 1, seq: 1 }, { name: "tenant_seq" });
var rows = [];
for (var i = 0; i < 200; i++) {
  rows.push({ _id: i, tenant: "training", seq: i, value: i * 2 });
}
lab.items.insertMany(rows, { writeConcern: { w: "majority", wtimeout: 10000 } });
if (lab.items.countDocuments({}) !== 200) throw new Error("Expected 200 fixture rows");
var result = lab.items.find({ tenant: "training", seq: { $gte: 190 } })
  .sort({ seq: 1 }).toArray();
if (result.length !== 10 || result[0].value !== 380 || result[9].value !== 398) {
  throw new Error("Fixture read contract failed");
}
printjson(lab.items.getIndexes());
```

Expected: 200 rows and ten terminal-range rows with values 380–398. Keep fixture writes stopped during index-change acceptance. This small dataset demonstrates state and query correctness; it cannot predict production performance.

## 8. Lab B — application identity read/write probe

Save as `ch71_probe.py`. Use a distinct scoped application identity with the credential-free replica-set URI and verified CA from the accepted lab. Set `CH71_URI`, `CH71_CA_FILE` and `CH71_USER` using the approved environment mechanism. Install the exact reviewed PyMongo release in an isolated environment.

The probe uses a single transaction-free compare-and-set update on one owned document and restores it. It is not an unrestricted health-check writer for production collections.

```python
import getpass
import os
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

client = MongoClient(
    os.environ["CH71_URI"], username=os.environ["CH71_USER"],
    password=getpass.getpass("MongoDB application probe password: "),
    authSource="admin", tls=True, tlsCAFile=os.environ["CH71_CA_FILE"],
    serverSelectionTimeoutMS=10000, socketTimeoutMS=10000,
)
try:
    lab = client.get_database("mongodb_enterprise_ch71_maintenance",
                             write_concern=WriteConcern(w="majority", wtimeout=10000))
    if lab.ownership.find_one({"_id": "mongodb-enterprise-tutorial-ch71"}) is None:
        raise RuntimeError("Ownership missing")
    rows = list(lab.items.find({"tenant": "training", "seq": {"$gte": 190}}).sort("seq", 1))
    if len(rows) != 10 or rows[0]["value"] != 380 or rows[-1]["value"] != 398:
        raise RuntimeError("Application read acceptance failed")
    changed = lab.items.update_one({"_id": 0, "value": 0}, {"$set": {"value": 1}})
    if changed.modified_count != 1:
        raise RuntimeError("Probe compare-and-set failed; reconcile document 0")
    observed = lab.items.find_one({"_id": 0})
    if observed is None or observed["value"] != 1:
        raise RuntimeError("Probe write visibility failed; reconcile document 0")
    restored = lab.items.update_one({"_id": 0, "value": 1}, {"$set": {"value": 0}})
    if restored.modified_count != 1 or lab.items.find_one({"_id": 0})["value"] != 0:
        raise RuntimeError("Probe restoration failed; reconcile document 0")
    print("PASS: scoped application read/write and restoration verified")
finally:
    client.close()
```

Run `python ch71_probe.py` before maintenance and after index restoration. If the connection fails after an acknowledged/ambiguous write, inspect document 0 through the lifecycle identity. Restore only its expected owned state after confirming no concurrent writer. Do not rerun the script blindly when value 0 is no longer present.

## 9. Lab C — hide the owned index and detect planner-contract failure

Capture the initial state before changing it. This lab starts with the owned index visible and restores that state. Existing production index states require their own recorded reversal value.

```javascript
var lab = db.getSiblingDB("mongodb_enterprise_ch71_maintenance");
var originalIndex = lab.items.getIndexes().find(x => x.name === "tenant_seq");
if (!originalIndex || originalIndex.hidden === true) throw new Error("Expected visible owned index");
var beforeCount = lab.items.countDocuments({});
var beforeRows = lab.items.find({ tenant: "training", seq: { $gte: 190 } })
  .sort({ seq: 1 }).toArray();
var beforePlan = lab.items.find({ tenant: "training", seq: { $gte: 190 } })
  .sort({ seq: 1 }).hint("tenant_seq").explain("executionStats");
printjson(beforePlan);
var hideResult = lab.runCommand({ collMod: "items", index: { name: "tenant_seq", hidden: true } });
if (hideResult.ok !== 1) throw new Error("Index hide failed");
var hiddenIndex = lab.items.getIndexes().find(x => x.name === "tenant_seq");
if (!hiddenIndex || hiddenIndex.hidden !== true) throw new Error("Index hide metadata failed");
var hintRejected = false;
try {
  lab.items.find({ tenant: "training", seq: { $gte: 190 } })
    .hint("tenant_seq").toArray();
} catch (error) {
  hintRejected = true;
  printjson({ expectedHintFailure: true, code: error.code, message: error.message });
}
if (!hintRejected) throw new Error("Hidden-index hint unexpectedly succeeded");
var duringRows = lab.items.find({ tenant: "training", seq: { $gte: 190 } })
  .sort({ seq: 1 }).toArray();
if (duringRows.length !== 10 || duringRows[0].value !== 380 || duringRows[9].value !== 398 ||
    lab.items.countDocuments({}) !== beforeCount) {
  throw new Error("Correctness changed during index maintenance; pause and restore");
}
printjson(lab.items.find({ tenant: "training", seq: { $gte: 190 } })
  .sort({ seq: 1 }).explain("executionStats"));
```

Expected: hidden metadata is true, explicit hint is rejected, and the unhinted query still returns correct data. Verify the recorded error is the expected hidden-index hint failure; an authorization/network error is not a passed negative test. Index hiding makes an index unavailable to the query planner while keeping it maintained.[3]

This is a controlled planner-contract failure, not a database outage. A correct unhinted result does not prove equivalent performance. Compare plans, examined work and real query latency under the production query distribution before considering permanent changes.

## 10. Lab D — reverse and verify

Run this restoration block even after an interrupted hide drill once ownership and current index state are confirmed. It is safe only for this fixture's known originally visible index.

```javascript
var lab = db.getSiblingDB("mongodb_enterprise_ch71_maintenance");
if (lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch71" }) === null) {
  throw new Error("Ownership missing");
}
var restoreResult = lab.runCommand({
  collMod: "items", index: { name: "tenant_seq", hidden: false }
});
if (restoreResult.ok !== 1) throw new Error("Index visibility restoration failed");
var restoredIndex = lab.items.getIndexes().find(x => x.name === "tenant_seq");
if (!restoredIndex || restoredIndex.hidden === true) throw new Error("Index remains hidden");
var restoredRows = lab.items.find({ tenant: "training", seq: { $gte: 190 } })
  .sort({ seq: 1 }).hint("tenant_seq").toArray();
if (restoredRows.length !== 10 || restoredRows[0].value !== 380 || restoredRows[9].value !== 398 ||
    lab.items.countDocuments({}) !== 200) {
  throw new Error("Post-maintenance data/query acceptance failed");
}
printjson(lab.items.getIndexes());
print("PASS: owned index visible, hint works, data contract retained");
```

Rerun the application probe. Recollect topology/service evidence and inspect monitoring freshness. Close the change only after the observation window and acceptance results are recorded, not merely because `collMod` returned success.

If the client loses the hide/unhide acknowledgement, inspect the index metadata rather than assuming the request failed. A retry must use the verified current state and intended original value.

## 11. Lab E — maintenance-readiness gate

Save this standalone offline script as `ch71_gate.py`. Its inputs represent already reviewed evidence, not automatically inferred production health. The freshness, replication and reserve limits are illustrative and must be replaced by the actual approved contract.

```python
from dataclasses import dataclass, replace
from math import isfinite


@dataclass(frozen=True)
class Readiness:
    evidence_age_minutes: float
    expected_members: int
    healthy_members: int
    primaries: int
    service_accepted: bool
    recovery_accepted: bool
    resource_reserve_accepted: bool
    another_disruptive_change: bool


def gate(packet, maximum_age_minutes=5):
    if not isfinite(packet.evidence_age_minutes) or packet.evidence_age_minutes < 0:
        raise ValueError("Invalid evidence age")
    if not isfinite(maximum_age_minutes) or maximum_age_minutes < 0:
        raise ValueError("Invalid freshness budget")
    for value in (packet.expected_members, packet.healthy_members, packet.primaries):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("Invalid member count")
    if packet.expected_members < 1 or packet.healthy_members > packet.expected_members:
        raise ValueError("Invalid topology contract")
    reasons = []
    if packet.evidence_age_minutes > maximum_age_minutes:
        reasons.append("stale_evidence")
    if packet.healthy_members != packet.expected_members or packet.primaries != 1:
        reasons.append("topology_not_accepted")
    if not packet.service_accepted:
        reasons.append("service_not_accepted")
    if not packet.recovery_accepted:
        reasons.append("recovery_not_accepted")
    if not packet.resource_reserve_accepted:
        reasons.append("resource_reserve_not_accepted")
    if packet.another_disruptive_change:
        reasons.append("conflicting_change")
    return {"decision": "proceed" if not reasons else "stop", "reasons": reasons}


baseline = Readiness(1, 3, 3, 1, True, True, True, False)
assert gate(baseline)["decision"] == "proceed"
cases = {
    "stale": replace(baseline, evidence_age_minutes=10),
    "secondary_down": replace(baseline, healthy_members=2),
    "no_primary": replace(baseline, primaries=0),
    "service_failure": replace(baseline, service_accepted=False),
    "backup_gap": replace(baseline, recovery_accepted=False),
    "reserve_gap": replace(baseline, resource_reserve_accepted=False),
    "concurrent_maintenance": replace(baseline, another_disruptive_change=True),
}
for name, packet in cases.items():
    result = gate(packet)
    assert result["decision"] == "stop" and result["reasons"]
    print(name, result)
print("PASS: baseline proceeds and all exception fixtures stop")
```

Run `python ch71_gate.py`. Expected: accepted baseline proceeds; each exception stops with a named reason. A backup-gap stop does not prove backup data was lost; it says recovery evidence is insufficient for the declared maintenance gate. Restore evidence and reevaluate rather than editing the boolean to bypass review.

## 12. Maintenance task boundaries

| Task | Before execution | Reversal/recovery and post-check |
|---|---|---|
| Log rotation | Recorded destination and rename/reopen policy; shipper coordination | Verify new writes and retained incident files; restore policy if misconfigured |
| Scoped profiling | Original namespace/profile settings, payload controls and duration | Restore exact original settings; verify profiler state and sensitive-data lifecycle |
| Index visibility | Original index name/options, query contract and latency budget | Restore hidden state; verify hinted/unhinted queries and resource impact |
| TTL change | Policy inventory, eligible-data preview and retention owner | Setting restoration cannot restore deleted data; use accepted recovery source |
| Rolling member maintenance | Quorum, healthy redundancy, source history and application resilience | One member at a time through accepted Chapter 28/62 procedure; wait for recovery |
| Storage/placement change | Capacity/IOPS contract, authoritative operator/IaC and backup | Verify persistent identity, replication and application performance |
| Collection validation | Exact-version options, expected locking/I/O and selected member | Preserve findings; investigate corruption through supported recovery, not blind repair |

Log rotation behavior depends on the configured MongoDB logging method and external rotation strategy.[4] Inspect the active native/operator configuration before issuing `logRotate`; do not apply a file-log procedure to stdout/syslog or truncate a live file to reclaim space.

A maintenance window does not justify quorum loss, a second disruptive change on another member or unreviewed FCV changes. Upgrades and rollback constraints stay under Chapter 62's version-specific plan. Each recovered member must be accepted before the next step.

## 13. Daily record and handoff

Use a compact evidence record rather than a checklist of unverified “OK” labels:

| Field | Required content |
|---|---|
| Identity/window | Environment, deployment, member scope, UTC review time and reviewer |
| Service | SLI status, known incident and representative application result |
| Topology | Role/member state, replication and history headroom |
| Resources | Constrained volume/member, reserve/forecast and I/O pressure |
| Recovery | Actual backup boundary, latest accepted restore and dependencies |
| Security/lifecycle | Expiry/rotation/drift findings and owners |
| Change | Before/after state, performed step, reversal and observation result |
| Exceptions | Severity, evidence link, action owner, due time and handoff |

Do not mark an entire cluster healthy from a single sample. Missing scope is recorded as pending/unavailable. Distinguish current service impact from future capacity/recovery risk so both receive the right response.

## 14. Troubleshooting and stop decisions

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Ping passes but service fails | Actual app identity/query and TLS/pool errors | Wrong privileges, routing or timeout contract | Restore app access; verify correct read/write outcome |
| Member Running but lagged | Replica status, optime/history and host I/O | Catch-up/resource constraint | Stop further maintenance; accept recovered state before continuing |
| Hidden-index hint failure persists | Index metadata and current target | Restoration failed or wrong namespace | Restore recorded visibility; rerun exact query contract |
| `collMod` response lost | Current index metadata and command evidence | Ambiguous acknowledgement | Reconcile state before retry; verify intended original setting |
| Probe left value 1 | Owned document and acknowledged/error boundary | Interruption before reversal | Confirm writer isolation; restore fixture state and reverify |
| Backup job green but restore old | Backup/restore acceptance packet | Job status substituted for recovery evidence | Assign recovery drill; gate disruptive work accordingly |
| Log volume fills | Rotation/destination, open files and shipper backlog | Retention/rotation mismatch | Follow reviewed logging procedure; verify active writes and space |
| Validation affects service | Command options, member role and latency | Unexpected lock/I/O impact | Stop dependent work; monitor operation and use supported incident procedure |
| Operator undoes manual change | Desired resource/config and reconciliation events | Wrong configuration owner | Change authoritative source; verify durable accepted runtime state |
| Maintenance collides with ingestion | Schedule, workload/lock/I/O evidence | Conflicting changes | Pause dependent change; coordinate explicit reschedule/acceptance |

## 15. Acceptance, cleanup and review

| Check | Required result |
|---|---|
| Daily observation | Recorded fresh identity, service/topology/resources/recovery scope |
| Fixture | 200 documents; ten range rows; values 380–398 |
| Application probe | Scoped read/write accepted; document 0 restored to value 0 |
| Hidden-index drill | Hidden metadata, expected hint failure, unhinted correctness |
| Reversal | Visible metadata, successful hinted query, unchanged fixture |
| Gate lab | Baseline proceeds; stale/degraded/missing/conflicting cases stop |
| Handoff | Before/after evidence and unresolved actions owned |
| Cleanup | Marker checked and only chapter-owned database removed |

Save nonsecret evidence, verify the index is restored and document 0 is back to its original value, then run through the lifecycle identity:

```javascript
var labName = "mongodb_enterprise_ch71_maintenance";
var lab = db.getSiblingDB(labName);
if (lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch71" }) === null) {
  throw new Error("Ownership missing: investigate before cleanup");
}
var index = lab.items.getIndexes().find(x => x.name === "tenant_seq");
var probe = lab.items.findOne({ _id: 0 });
if (!index || index.hidden === true || !probe || probe.value !== 0) {
  throw new Error("Restore owned maintenance state before cleanup");
}
if (lab.dropDatabase().ok !== 1) throw new Error("Owned cleanup failed");
if (db.getSiblingDB(labName).getCollectionInfos().length !== 0) {
  throw new Error("Cleanup left collections");
}
print("PASS: owned maintenance fixture removed");
```

Retain the cluster, backups, monitoring, FTDC/logs, operator resources and other chapter data under their existing owners. Local gate/probe scripts and evidence may remain until their lab retention policy expires.

Review questions:

1. Why can service availability and maintenance readiness have different outcomes?
2. What evidence is missing from a successful ping or Running pod?
3. How should an ambiguous index-change acknowledgement be reconciled?
4. Why does restoring a TTL setting not recover removed documents?
5. Which maintenance tasks need a separate exact-version impact review?
6. What closes a change beyond a successful database command?
7. How should daily review record unavailable evidence and action ownership?

## 16. DBRE/SRE extension — owner-approved index maintenance and auditability

This extension applies the daily runbook to real operational tickets. **The chapter's synthetic index-hide lab remains isolated**; the production workflow below requires an independent change approval and does not authorize dropping an index or deleting data.

### 16.1 Index-owner review before DBRE action

An index candidate may be unused, duplicated, redundant, empty or expensive to maintain. None of those labels alone proves it is safe to remove. A query that has not appeared in a bounded observation period may be seasonal, failover-only, reporting-only or owned by a dormant service.

Record an owner response for every proposed index:

| Question to owner | Required evidence or decision |
|---|---|
| Which application, job, tenant or team owns this collection and its query paths? | Named accountable owner and approved ticket |
| Does any workload use the index for filtering, sorting, uniqueness or a query hint? | Query examples, plans and explicit correctness constraints |
| Are there scheduled, monthly, incident-only, migration or DR workloads that need it? | Coverage period and exceptions |
| Is the index unique, TTL, partial, sparse, collation-specific, multikey or otherwise policy-bearing? | Exact `getIndexes()` definition and dependent contracts |
| Is the candidate truly redundant given field order, sort, collation and query predicates? | Comparison to surviving indexes and representative `explain` results |
| Can the application owner remove or correct the dependency first? | Owner action, rollout evidence and completion date |
| What is the expected write/storage/query benefit and potential regression? | Baseline, hypothesis and measurable acceptance limits |
| Who approves, monitors and reverses the proposed change? | Owner, DBRE/Infra reviewer, change window, rollback authority |

A collection with no documents can still carry critical uniqueness, TTL or future application contracts. **Empty does not mean disposable.** TTL indexes govern deletion; changing TTL retention can permanently delete data. Do not combine index housekeeping with data-deletion authorization.

### 16.2 Safe index lifecycle — propose, hide, observe, decide

1. **Inventory read-only:** capture namespace, exact index specification, index size if safely obtainable, deployment/FCV, query shapes, ownership and monitoring freshness. Scope collection scans and statistics to an approved target.
2. **Classify:** distinguish a query-performance index from unique/TTL or other functional controls. Exclude special-purpose indexes from automatic retirement.
3. **Approve:** obtain application/data-owner review, DBRE change approval, service SLO budget, current backup/recovery evidence and a named rollback operator.
4. **Rehearse:** on a representative isolated workload, compare plans, examined/returned counts, P95/P99 application latency, error ratio and write cost. Hidden-index behavior and support must be checked against the exact server version.
5. **Canary in production only if approved:** for an eligible index, record original hidden state, hide under a bounded change, and monitor a full representative workload cycle. Index hiding can affect query plans; it does not remove index maintenance overhead.
6. **Restore on regression:** unhide using the recorded original state, verify plans and application outcomes, and reconcile ambiguous command acknowledgements before retrying.
7. **Retire only by a separate approved change:** dropping an index is not a reversible configuration toggle. Rebuilding can take substantial time and resources; preserve the exact definition and evaluate operational risk.
8. **Close:** retain evidence, owner sign-off, post-change observation and exceptions. Keep the audit ticket even when the correct decision is **no change**.

**Stop immediately** for missing owner approval, unexpected query-hint errors, elevated application latency/errors, uncertain index identity, degraded replica set, exhausted error budget, missing backups or insufficient rollback capacity. Do not hide or drop the mandatory `_id` index.

### 16.3 Change record schema and offline approval gate

Save the following template as `ch71-change.json`. It represents an **approval record**, not an automated production change executor.

```json
{
  "chapter": 71,
  "change_id": "NOT_ASSIGNED",
  "environment": "isolated-test",
  "namespace": "mongodb_enterprise_ch71_maintenance.items",
  "index_name": "tenant_seq",
  "operation": "hide",
  "index_owner": "NOT_ASSIGNED",
  "dbre_approver": "NOT_ASSIGNED",
  "maintenance_window_utc": "NOT_ASSIGNED",
  "original_index_spec_recorded": false,
  "service_slo_baseline_recorded": false,
  "monitoring_fresh": false,
  "replica_health_accepted": false,
  "recovery_evidence_accepted": false,
  "rollback_procedure_reviewed": false,
  "owner_query_impact_reviewed": false,
  "another_disruptive_change": false,
  "expected_query_acceptance": "NOT_RECORDED",
  "evidence_references": []
}
```

Save this dependency-free offline check as `ch71_change_gate.py`:

```python
import json
from pathlib import Path

p = json.loads(Path("ch71-change.json").read_text(encoding="utf-8"))
required_true = (
    "original_index_spec_recorded", "service_slo_baseline_recorded",
    "monitoring_fresh", "replica_health_accepted",
    "recovery_evidence_accepted", "rollback_procedure_reviewed",
    "owner_query_impact_reviewed",
)
required_identity = (
    "change_id", "namespace", "index_name", "index_owner",
    "dbre_approver", "maintenance_window_utc", "expected_query_acceptance",
)
failures = [k for k in required_true if p.get(k) is not True]
failures += [k for k in required_identity
             if not isinstance(p.get(k), str) or not p[k].strip()
             or p[k].startswith("NOT_")]
if p.get("another_disruptive_change") is not False:
    failures.append("another_disruptive_change")
if p.get("operation") != "hide":
    failures.append("operation_not_authorized_by_this_gate")
if p.get("index_name") == "_id_":
    failures.append("mandatory_id_index")
if not isinstance(p.get("evidence_references"), list) or not p["evidence_references"]:
    failures.append("evidence_references")
if failures:
    raise SystemExit("STOP: " + ", ".join(failures))
print("PASS: change record fields declared; independently verify evidence and approval")
```

Run `python ch71_change_gate.py`. The untouched template **must stop**. The gate is intentionally restricted to `hide`; it does **not** authorize an index drop, TTL change, or any production action. Passing means declarations are present, not that approvals are genuine.

### 16.4 Post-change acceptance and escalation

| Check | PASS evidence | STOP / rollback condition |
|---|---|---|
| Application impact | Representative good/eligible requests and P95/P99 remain inside the approved baseline/SLO | Increased errors, timeouts or material query regression |
| Query correctness | Representative predicates, sort, hints and uniqueness/retention expectations verified | Wrong results, hint failures or changed functional behavior |
| Replica health | All required members healthy, lag/history within recovery budget | Election, sustained lag, degraded quorum or insufficient history |
| Monitoring | Expected member and application series fresh; change annotated | Missing metrics or stale green panels |
| Index state | Exact target and hidden state match the approved phase | Ambiguous state, wrong namespace or unexpected metadata |
| Handoff | Owner acknowledgement, before/after evidence, rollback result and observation interval | Unowned exception or incomplete evidence |

The operator must verify state after any lost command acknowledgement. A successful `collMod` alone does not close a production maintenance ticket. Record whether the outcome is **approved/no change**, **reversed**, **accepted canary**, or **separately approved retirement**. Maintain an audit trail of who made the decision and why.

---

## 17. Official references and validation status

1. [MongoDB 8.0 — replSetGetStatus](https://www.mongodb.com/docs/v8.0/reference/command/replSetGetStatus/).
2. [MongoDB 8.0 — validate](https://www.mongodb.com/docs/v8.0/reference/command/validate/).
3. [MongoDB 8.0 — Hidden Indexes](https://www.mongodb.com/docs/v8.0/core/index-hidden/).
4. [MongoDB 8.0 — Rotate Log Files](https://www.mongodb.com/docs/v8.0/tutorial/rotate-log-files/).

Documentation reviewed on 2026-10-12. Daily review ordering, fixture/probe contracts and maintenance gates are operational teaching designs. Python/JavaScript syntax and actual offline gate cases were checked, including invalid evidence/count inputs. These checks do not validate live MongoDB permissions, member health, index behavior, application recovery, operator reconciliation or log rotation. No live maintenance was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline gate acceptance complete. Runtime validation remains pending until the authorized observation, application probe, index drill/restoration and cleanup are executed and recorded.

Previous: [Chapter 70 — Alert Thresholds SLOs and Capacity Forecasting](70-alert-thresholds-slos-and-capacity-forecasting.md).  
Next: Chapter 72 — Cost Optimization and Enterprise License Planning.
