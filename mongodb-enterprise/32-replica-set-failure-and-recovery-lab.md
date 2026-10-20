# 32 — Replica Set Failure and Recovery Lab

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Run bounded client traffic during primary failure, reconcile acknowledged/uncertain requests, deliberately demonstrate quorum loss and restore the original topology and application state.  
**Audience:** DBREs, SREs, Developers and Platform Engineers  
**Time:** 150–180 minutes  
**Baseline:** MongoDB 8.0, mongosh and Docker Compose v2; record exact versions/image digest.  
**Deployment:** Owned disposable Chapter 26 `rs26`, three voting data members on one host. Community-compatible; no Enterprise-only validation.  
**Prerequisites:** Chapters 25–31, original volumes/network aliases restored, no active overrides or partitions, adequate resources, no other workload/automation.

## 1. Integrated acceptance, not another topology build

Earlier chapters separately covered maintenance, lag, initial sync and partitions. This chapter combines application evidence with two process-failure scenarios. It does not rebuild the replica set or change its membership.

| Scenario | Trigger | Required recovery evidence |
|---|---|---|
| A: primary crash | SIGKILL of the current primary only | Different primary, client request ledger, surviving acknowledged writes, restarted-member convergence |
| B: quorum loss | Stop both current secondaries sequentially in the owned lab | Survivor loses writable-primary role, write is not acknowledged, original members restored in order |
| Final acceptance | All processes running again | Full roles, exact fixture state, concern-aware reconciliation, unchanged config/storage/network |

Scenario B deliberately violates the one-member-at-a-time maintenance rule to demonstrate an outage. It is an explicit disposable failure experiment, never a production maintenance technique. Complete Scenario A's full recovery before starting B.

**Use case:** An SRE rehearses how process availability, driver selection, acknowledgement and data convergence interact. The evidence should support a recovery decision and identify which application tests remain unproven.

## 2. Recovery contracts and limits

Three voting data members need a majority of two for election. Losing one can leave a writable pair; losing two removes the intended quorum. A process being alive does not prove primary availability, and a new primary does not prove every secondary is current.

This lab uses explicit majority+journal acknowledgement for durable fixture operations. It checks that every acknowledged traffic identity survives. Uncertain requests are reconciled against committed current history before cleanup; they are not automatically retried.

No automatic retries are used in the teaching writer. That isolates single-attempt outcomes; it does not validate production retryable writes, transaction retries or external side effects. A one-second loop provides sampled request observations, not continuous availability measurement.

The set shares one host, so this experiment does not validate independent host/zone failure domains. SIGKILL is an abrupt process exit, not a simulated disk failure, kernel failure or power loss. Backups/PITR and whole-set disaster recovery are separate exercises.

## 3. Preflight, versions and independent sessions

Use the exact Chapter 26 `compose.yaml` and project. Retain original volumes. Remove a prior Chapter 30 override only after its successful restoration; heal any Chapter 31 endpoint before beginning.

```bash
docker version
docker compose version
docker compose -p mongodb-ch26 -f compose.yaml config
docker compose -p mongodb-ch26 -f compose.yaml ps
docker network inspect mongodb-ch26_replica
docker volume ls --filter label=com.docker.compose.project=mongodb-ch26
docker stats --no-stream
docker run --rm -it --network mongodb-ch26_replica mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=5000&socketTimeoutMS=10000&retryWrites=false"
```

Use the approved image digest, not an unreviewed patch change. The independent operator client remains alive when a member is killed or stopped. Keep another host terminal for process commands and a third for bounded traffic.

Record each member's original mounts, image ID and network aliases; confirm no additional process shares a data volume. Verify disk and CPU/memory margins. No host ports are published. Docker control and MongoDB status/config inspection plus scoped database access are required. The isolated Chapter 26 topology is unauthenticated; production needs approved TLS/authentication and access controls.

## 4. Guard the topology and retain configuration

In the independent operator mongosh client:

```javascript
const hosts32 = ["a:27017", "b:27017", "c:27017"];
const name32 = "mongodb_enterprise_tutorial_ch32";
const lab32 = db.getSiblingDB(name32);
const wc32 = { w: "majority", j: true, wtimeout: 5000 };
function check32(condition, message) {
  if (!condition) throw new Error(message);
}
function direct32(host) {
  check32(hosts32.includes(host), "Host outside owned lab");
  const c = new Mongo("mongodb://" + host +
    "/?directConnection=true&serverSelectionTimeoutMS=3000&socketTimeoutMS=10000&retryWrites=false");
  c.setReadPref("secondaryPreferred");
  return c;
}
function status32() { return db.adminCommand({ replSetGetStatus: 1 }); }
function healthy32(s) {
  return s && s.ok === 1 && s.set === "rs26" && s.members.length === 3 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "PRIMARY").length === 1 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "SECONDARY").length === 2;
}
function waitHealthy32(timeoutMs = 180000) {
  const end = Date.now() + timeoutMs;
  let last;
  while (Date.now() < end) {
    try { last = status32(); if (healthy32(last)) return last; }
    catch (error) { print(error.message); }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Full readiness not observed within lab budget");
}
function ack32(r) {
  return r && r.ok === 1 && Number(r.n) === 1 &&
    (!r.writeErrors || r.writeErrors.length === 0) && !r.writeConcernError;
}
const cfg32 = db.adminCommand({ replSetGetConfig: 1 }).config;
check32(cfg32._id === "rs26" && cfg32.members.length === 3 &&
  cfg32.members.every(m => hosts32.includes(m.host) && !m.hidden && !m.arbiterOnly &&
    Number(m.votes === undefined ? 1 : m.votes) === 1 &&
    Number(m.priority === undefined ? 1 : m.priority) > 0 &&
    Number(m.secondaryDelaySecs || 0) === 0), "Unexpected replica configuration");
const originalConfig32 = EJSON.stringify(cfg32);
check32(lab32.getCollectionNames().length === 0,
        "Chapter database already exists; inspect before rerunning");
waitHealthy32();
printjson({ version: db.version(), config: cfg32 });
```

Observation budgets are stop-and-diagnose limits, not MongoDB recovery guarantees. No election/heartbeat settings are changed to shorten the experiment.

## 5. Deterministic fixture and data contract

The collection is created before traffic; failure-time inserts do not depend on implicit collection creation. Stable identities allow exact reconciliation rather than comparing counts alone.

```javascript
check32(lab32.createCollection("events").ok === 1, "Collection creation failed");
const events32 = lab32.events;
check32(events32.insertOne({ _id: "baseline", revision: 1, source: "operator" },
  { writeConcern: wc32 }).acknowledged, "Baseline acknowledgement failed");
const fixedIds32 = ["baseline"];
const trafficIds32 = Array.from({ length: 30 }, (_, i) =>
  "traffic-" + String(i).padStart(3, "0"));
function rows32(host) {
  return direct32(host).getDB(name32).events.find().sort({ _id: 1 }).toArray();
}
function canonical32(rows) {
  return JSON.stringify(rows.map(r => ({ id: r._id, revision: Number(r.revision),
    source: r.source, seq: r.seq === undefined ? null : Number(r.seq) })));
}
function contract32(rows) {
  const ids = rows.map(r => r._id);
  return fixedIds32.every(id => ids.includes(id)) && rows.every(r => {
    if (Number(r.revision) !== 1) return false;
    if (fixedIds32.includes(r._id))
      return r.source === "operator" && r.seq === undefined;
    const pos = trafficIds32.indexOf(r._id);
    return pos >= 0 && r.source === "traffic" && Number(r.seq) === pos;
  });
}
function converge32(timeoutMs = 90000) {
  const reference = events32.find().sort({ _id: 1 }).toArray();
  check32(contract32(reference), "Primary fixture contract differs");
  const expected = canonical32(reference);
  for (const host of hosts32) {
    const end = Date.now() + timeoutMs;
    let got;
    do { got = rows32(host); if (canonical32(got) === expected) break; sleep(500); }
    while (Date.now() < end);
    check32(canonical32(got) === expected, "Fixture not converged: " + host);
  }
  return reference;
}
check32(converge32().length === 1, "Baseline differs");
```

Do not add new identities to `fixedIds32` until their acknowledgement is confirmed or their uncertain outcome is reconciled and the intended payload is verified.

## 6. Save the bounded client workload

Save the following complete JavaScript as `traffic32.js` beside `compose.yaml`. It runs in a separate mongosh process, makes 30 single-attempt requests and prints one JSON record per request plus a final summary. It never reuses a failed identity for a new request.

```javascript
const trafficDb32 = db.getSiblingDB("mongodb_enterprise_tutorial_ch32");
const ledger32 = [];
for (let i = 0; i < 30; i++) {
  const id = "traffic-" + String(i).padStart(3, "0");
  const started = Date.now();
  let response = null;
  let error = null;
  try {
    response = trafficDb32.runCommand({ insert: "events", ordered: true,
      documents: [{ _id: id, seq: i, revision: 1, source: "traffic" }],
      maxTimeMS: 3000, writeConcern: { w: "majority", j: true, wtimeout: 2000 },
      comment: "mongodb-ch32-" + id });
  } catch (e) {
    error = { code: e.code, message: e.message };
  }
  const acknowledged = response !== null && response.ok === 1 &&
    Number(response.n) === 1 &&
    (!response.writeErrors || response.writeErrors.length === 0) &&
    !response.writeConcernError;
  const item = { kind: "request", id, startedAt: new Date(started).toISOString(),
    endedAt: new Date().toISOString(), elapsedMs: Date.now() - started,
    outcome: acknowledged ? "acknowledged" : "unresolved",
    response, error };
  ledger32.push(item);
  print(JSON.stringify(item));
  sleep(1000);
}
print(JSON.stringify({ kind: "summary", attempts: ledger32.length,
  acknowledgedIds: ledger32.filter(r => r.outcome === "acknowledged").map(r => r.id),
  unresolvedIds: ledger32.filter(r => r.outcome !== "acknowledged").map(r => r.id) }));
```

From a third host terminal, start the writer and capture its output:

```bash
docker run --rm --network mongodb-ch26_replica --mount "type=bind,source=${PWD}/traffic32.js,target=/lab/traffic32.js,readonly" mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=2000&socketTimeoutMS=6000&retryWrites=false" --quiet --file /lab/traffic32.js > ch32-traffic.jsonl
```

Run this in Bash or PowerShell from the folder containing the saved file, with the approved image digest substituted. Do not run it from Windows `cmd.exe` with this path syntax. The command mounts only the script. Retain the output file; encoding may differ by shell, so read it with the matching encoding when processing it.

Initial client connection can fail before the script runs. Require a final 30-attempt summary, not only process exit. The loop's duration can exceed 30 seconds because request latency and sleeps accumulate. Selection, server operation, acknowledgement and socket limits cover different stages and are not interchangeable.

Use the process-control host terminal to inspect the output while the writer runs. In Bash use `tail -n 5 ch32-traffic.jsonl`; in PowerShell use `Get-Content ch32-traffic.jsonl -Tail 5`. Preserve the actual crash time in your event notes so request timestamps can establish overlap.

## 7. Scenario A: kill the current primary

After the traffic output contains at least two acknowledged requests, generate the crash/recovery pair from the operator client:

```javascript
const preCrash32 = waitHealthy32();
const crashedHost32 = preCrash32.members.find(m => m.stateStr === "PRIMARY").name;
const crashedService32 = crashedHost32.split(":")[0];
const crashSurvivors32 = hosts32.filter(h => h !== crashedHost32);
check32(direct32(crashedHost32).getDB("admin").runCommand({ hello: 1 }).isWritablePrimary,
        "Target no longer primary; reassess before crash");
const crashObservationStart32 = Date.now();
print("CRASH: docker compose -p mongodb-ch26 -f compose.yaml kill -s SIGKILL " + crashedService32);
print("RECOVER: docker compose -p mongodb-ch26 -f compose.yaml start " + crashedService32);
```

Run only the generated CRASH command now. SIGKILL deliberately skips graceful shutdown; inspect Docker state and preserve logs. It should affect exactly one current primary service. Do not kill a survivor or remove any container/volume.

The traffic writer keeps running on the surviving network. Do not rerun it. If the writer had already finished before the crash, recover topology and mark concurrent-traffic coverage as not exercised; do not claim the requests overlapped the event.

## 8. Observe failover and restore the crashed member

```javascript
function waitPair32(pair, timeoutMs = 90000) {
  const end = Date.now() + timeoutMs;
  let last;
  while (Date.now() < end) {
    try {
      last = status32();
      const selected = last.members.filter(m => pair.includes(m.name));
      if (last.ok === 1 && selected.length === 2 &&
          selected.every(m => m.health === 1) &&
          selected.filter(m => m.stateStr === "PRIMARY").length === 1 &&
          selected.filter(m => m.stateStr === "SECONDARY").length === 1)
        return last;
    } catch (error) { print(error.message); }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Writable pair not observed; restore saved stopped member(s)");
}
const elected32 = waitPair32(crashSurvivors32);
const crashNewPrimary32 = elected32.members.find(m => m.stateStr === "PRIMARY").name;
check32(crashNewPrimary32 !== crashedHost32, "Different primary not observed");
printjson({ crashed: crashedHost32, primary: crashNewPrimary32,
  observationElapsedMs: Date.now() - crashObservationStart32 });
print("START NOW: docker compose -p mongodb-ch26 -f compose.yaml start " + crashedService32);
```

Run the generated START command. Wait for the full topology, then let the traffic process finish and preserve its complete 30-attempt summary before continuing:

```javascript
waitHealthy32();
```

Do not call fixture convergence while the writer is still changing the dataset. If restart fails, leave both survivors running, inspect the target's startup/storage logs and recover that service with original volumes. Chapter 30 applies if supported resync is actually required; a failed restart does not justify deleting its data.

## 9. Reconcile the traffic ledger against committed history

Paste the exact arrays from the writer's final summary into these variables in the operator client. The null values deliberately block acceptance until real evidence is supplied:

```javascript
let acknowledgedIds32 = null;
let unresolvedIds32 = null;
// Assign the exact summary arrays before executing the following checks.
```

Validate the completed ledger and advance a majority-acknowledged barrier after the writer has exited:

```javascript
check32(Array.isArray(acknowledgedIds32) && Array.isArray(unresolvedIds32),
        "Paste actual completed writer summary arrays first");
const accountedIds32 = [...acknowledgedIds32, ...unresolvedIds32];
check32(accountedIds32.length === 30 && new Set(accountedIds32).size === 30 &&
  accountedIds32.every(id => trafficIds32.includes(id)), "Ledger incomplete or duplicated");
// A client timeout can outlive the caller; verify tagged server operations are finished.
const drainDeadline32 = Date.now() + 30000;
let activeTraffic32 = [];
do {
  activeTraffic32 = hosts32.flatMap(host => direct32(host).getDB("admin").aggregate([
    { $currentOp: { allUsers: true } },
    { $match: { active: true, "command.comment": /^mongodb-ch32-traffic-/ } },
    { $project: { _id: 0, opid: 1, ns: 1, command: 1 } }
  ]).toArray().map(op => ({ host, op })));
  if (activeTraffic32.length === 0) break;
  sleep(500);
} while (Date.now() < drainDeadline32);
printjson({ activeTaggedOperations: activeTraffic32 });
check32(activeTraffic32.length === 0,
        "Requests still active on server; wait/diagnose before reconciliation");
const afterCrashWrite32 = events32.insertOne({
  _id: "after-primary-loss", revision: 1, source: "operator"
}, { writeConcern: wc32 });
check32(afterCrashWrite32.acknowledged, "Barrier outcome uncertain; reconcile identity");
fixedIds32.push("after-primary-loss");
function committedRows32() {
  const result = lab32.runCommand({ find: "events", filter: {}, sort: { _id: 1 },
    limit: 100, singleBatch: true, readConcern: { level: "majority" }, maxTimeMS: 5000 });
  check32(result.ok === 1, "Committed snapshot failed");
  return result.cursor.firstBatch;
}
const committedAfterCrash32 = committedRows32();
check32(contract32(committedAfterCrash32), "Committed fixture payload mismatch");
const committedIds32 = new Set(committedAfterCrash32.map(r => r._id));
check32(acknowledgedIds32.length >= 2, "Required acknowledged baseline traffic missing");
check32(acknowledgedIds32.every(id => committedIds32.has(id)),
        "Acknowledged traffic missing after failover; stop acceptance");
const reconciledRequests32 = trafficIds32.map(id => ({ id,
  originalOutcome: acknowledgedIds32.includes(id) ? "acknowledged" : "unresolved",
  recoveredOutcome: committedIds32.has(id) ? "present-matching" : "absent-after-recovery" }));
printjson(reconciledRequests32);
const convergedAfterCrash32 = converge32();
check32(canonical32(convergedAfterCrash32) === canonical32(committedAfterCrash32),
        "Local and committed recovered history differ");
```

This absence classification requires writer termination, completed topology recovery and committed-history reconciliation. It is a final state observation for this synthetic single-attempt insert, not proof that the operation never applied earlier. Preserve raw uncertain responses; data rolled back or rejected during the transition can both be absent now.

The tagged-operation inspection also requires permission to view other users' current operations on authenticated deployments. A permissions error blocks this gate; it must not be interpreted as an empty operation list. The isolated unauthenticated lab avoids that access difference.

Do not replay unresolved IDs in this lab. Production replay also needs an idempotency/business contract and external side-effect reconciliation. Duplicate identity with a mismatching payload is an incident, not automatic success.

## 10. Scenario B: deliberately remove quorum

Only begin after the writer has finished and Scenario A fully converged. Capture the current primary and two current secondaries. Prepare both recovery commands before stopping either:

```javascript
const quorumStart32 = waitHealthy32();
converge32();
const quorumPrimary32 = quorumStart32.members.find(m => m.stateStr === "PRIMARY").name;
const quorumSecondaries32 = quorumStart32.members.filter(m => m.stateStr === "SECONDARY")
  .map(m => m.name);
const firstStopped32 = quorumSecondaries32[0].split(":")[0];
const secondStopped32 = quorumSecondaries32[1].split(":")[0];
printjson({ survivor: quorumPrimary32, stopOrder: quorumSecondaries32 });
print("STOP FIRST: docker compose -p mongodb-ch26 -f compose.yaml stop --timeout 60 " + firstStopped32);
print("RECOVER FIRST: docker compose -p mongodb-ch26 -f compose.yaml start " + firstStopped32);
print("RECOVER SECOND: docker compose -p mongodb-ch26 -f compose.yaml start " + secondStopped32);
```

Run STOP FIRST. Check that the remaining primary and the other secondary still form a healthy pair before generating the second stop:

```javascript
const reduced32 = waitPair32([quorumPrimary32, quorumSecondaries32[1]]);
check32(reduced32.members.find(m => m.name === quorumPrimary32).stateStr === "PRIMARY",
        "Survivor primary changed; restore first stopped member and reassess");
check32(direct32(quorumSecondaries32[1]).getDB("admin")
  .runCommand({ hello: 1 }).secondary === true,
  "Second stop target is not a secondary; restore first and reassess");
print("DELIBERATE QUORUM LOSS: docker compose -p mongodb-ch26 -f compose.yaml stop --timeout 60 " + secondStopped32);
```

Run the generated second stop only for this explicit outage exercise. Preserve graceful shutdown outcomes. The former primary remains the only running member; do not modify votes to make it writable. Keep this outage short and proceed to observation and recovery immediately.

## 11. Confirm unavailable write service and retain probe outcome

Use a direct connection to the survivor because the primary-aware client may now fail selection:

```javascript
const loneConn32 = direct32(quorumPrimary32);
const loneAdmin32 = loneConn32.getDB("admin");
const noQuorumDeadline32 = Date.now() + 90000;
let loneStatus32 = null;
while (Date.now() < noQuorumDeadline32) {
  loneStatus32 = loneAdmin32.runCommand({ replSetGetStatus: 1 });
  if (loneStatus32.ok === 1 && loneStatus32.myState === 2 &&
      loneStatus32.members.filter(m => m.health === 1).length === 1) break;
  sleep(1000);
}
check32(loneStatus32 && loneStatus32.myState === 2 &&
  loneStatus32.members.filter(m => m.health === 1).length === 1,
  "No-quorum state not observed; START BOTH STOPPED SERVICES NOW");
printjson({ survivorState: loneStatus32.myState, members: loneStatus32.members });
let quorumProbeResponse32 = null;
let quorumProbeError32 = null;
try {
  quorumProbeResponse32 = loneConn32.getDB(name32).runCommand({ insert: "events",
    documents: [{ _id: "quorum-probe", revision: 1, source: "operator" }],
    ordered: true, maxTimeMS: 2000,
    writeConcern: { w: "majority", j: true, wtimeout: 1000 } });
} catch (error) {
  quorumProbeError32 = { code: error.code, message: error.message };
}
check32(!ack32(quorumProbeResponse32), "Unexpected acknowledgement without quorum; recover and investigate");
printjson({ response: quorumProbeResponse32, error: quorumProbeError32 });
```

Expected: the lone member steps down, and the insert is not acknowledged. It may return a not-primary error or a client/server error; preserve the actual response. This probe runs after stepdown, so do not label it an observed write-concern timeout merely because its requested concern cannot be satisfied.

The direct status observation proves this member's local view. Docker state confirms both stopped processes. It does not establish global state in an arbitrary production partition. No in-flight workload runs during the quorum-loss phase.

## 12. Restore a majority, then full redundancy

Run RECOVER FIRST from the saved command pair. It restarts one original secondary, restoring two voting data processes. Wait for their writable pair before inserting the recovery marker:

```javascript
const restoredPair32 = waitPair32([quorumPrimary32, quorumSecondaries32[0]]);
printjson(restoredPair32.members.map(m => ({ host: m.name, role: m.stateStr, health: m.health })));
const afterQuorumWrite32 = events32.insertOne({
  _id: "after-quorum-restoration", revision: 1, source: "operator"
}, { writeConcern: wc32 });
check32(afterQuorumWrite32.acknowledged, "Recovery marker outcome uncertain; reconcile before proceeding");
fixedIds32.push("after-quorum-restoration");
print("RESTORE FULL REDUNDANCY NOW: docker compose -p mongodb-ch26 -f compose.yaml start " + secondStopped32);
```

Run the generated start for the second stopped service, then:

```javascript
waitHealthy32();
const finalRows32 = converge32();
const finalCommitted32 = committedRows32();
check32(canonical32(finalRows32) === canonical32(finalCommitted32),
        "Final local/committed history mismatch");
check32(events32.findOne({ _id: "quorum-probe" }) === null,
        "Unexpected quorum probe state; reconcile raw response before acceptance");
check32(acknowledgedIds32.every(id => finalRows32.some(r => r._id === id)),
        "Acknowledged traffic missing after quorum recovery");
check32(EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalConfig32, "Configuration changed during failure recovery");
printjson({ finalCount: finalRows32.length, fixedIds: fixedIds32,
  acknowledgedTraffic: acknowledgedIds32.length,
  uncertainTraffic: unresolvedIds32.length, finalRows: finalRows32 });
```

If the second service fails to start, retain the working pair and recover that target. If the first service cannot restore quorum, start the other saved stopped service rather than waiting with one member forever. Reconcile any ambiguous marker before replay. A successful election alone does not complete recovery.

## 13. Failure diagnosis, evidence and production differences

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| No traffic summary | Container output and mount/path | Writer never connected or terminated early | Recover topology; classify workload coverage incomplete |
| No errors during crash traffic | Request timestamps versus event | Sampling missed selection gap | Do not invent outage; retain observed result |
| New primary but writes fail | Pair health, concern errors and latency | Slow/unavailable acknowledger or resource pressure | Restore failed member and diagnose |
| Acknowledged identity missing | Raw ledger, concern and committed payloads | Durability/history contract violation | Stop acceptance and investigate |
| Unresolved request present | Stable identity and expected payload | Applied despite lost acknowledgement | Reconcile as present, no duplicate replay |
| Unresolved request absent after recovery | Terminated writer, committed current history | Rejection or rolled-back/unapplied outcome | Preserve timeline; apply business policy separately |
| Lone process cannot accept writes | Direct role/status, stopped members | No election/acknowledgement majority | Restore original members, never force a routine fix |
| Restart stays recovering | Startup/replication logs, disk and history | Catch-up, storage failure or missing overlap | Diagnose; use supported resync only if needed |
| Count matches but payload differs | Exact ID/revision/source/seq | Duplicate/conflicting application state | Treat as mismatch; do not accept counts alone |

Collect bounded logs and Docker state:

```bash
docker compose -p mongodb-ch26 -f compose.yaml ps -a
docker compose -p mongodb-ch26 -f compose.yaml logs --tail 200 a b c
docker network inspect mongodb-ch26_replica
```

A production drill additionally needs approved blast radius, independent failure domains, workload realism, backups, business SLOs, client retries/pools/deadlines and a tested rollback/recovery plan. This exercise contains no version upgrade, forced reconfiguration, initial-sync erase, storage replacement or network mutation.

Inspect the ledger for start/end/error intervals and request latency. Separate server selection, operation execution and acknowledgement stages where trace data supports it. Do not call polling elapsed time an RTO, or infer RPO from a temporary lag metric. The synthetic durability assertion is limited to explicitly acknowledged fixture identities.

## 14. Cleanup and restoration

If an assertion fails with services stopped, start those exact saved services first. Restore all processes before adapting fixture logic or cleanup. Keep original mounts/image/network and inspect the final configuration. Preserve unresolved request evidence; deleting its collection is not reconciliation.

Retain `ch32-traffic.jsonl`, the exact workload script and version/event evidence with your lab notes. Delete only the chapter database after all acceptance data checks pass:

```javascript
waitHealthy32();
const cleanupRows32 = converge32();
check32(acknowledgedIds32.every(id => cleanupRows32.some(r => r._id === id)),
        "Cleanup blocked by missing acknowledged request");
check32(canonical32(cleanupRows32) === canonical32(committedRows32()),
        "Cleanup blocked by unresolved history mismatch");
check32(EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalConfig32, "Cleanup blocked by configuration change");
check32(lab32.getName() === "mongodb_enterprise_tutorial_ch32",
        "Refusing cleanup outside the Chapter 32 training database");
check32(lab32.dropDatabase().ok === 1, "Chapter database cleanup failed");
for (const host of hosts32) {
  const d = direct32(host).getDB(name32);
  const end = Date.now() + 30000;
  while (Date.now() < end && d.getCollectionNames().length !== 0) sleep(500);
  check32(d.getCollectionNames().length === 0, "Cleanup not applied: " + host);
}
waitHealthy32();
```

Leave the original replica set healthy if retaining it for future practice. To dismantle the entire owned project instead, exit clients and follow Chapter 26's explicit volume cleanup after evidence preservation. Do not use pruning, unrelated service stops or broad volume removal here.

No process-wide settings changed. Crashed/restarted member leadership may differ from the original; do not force restoration of the old primary for cosmetic consistency.

## 15. Acceptance and evidence

- [ ] Recorded versions/image, original mounts/network, configuration and full readiness.
- [ ] Created and reconciled the baseline everywhere before failures.
- [ ] Preserved a complete 30-attempt ledger with at least two initial acknowledged requests.
- [ ] Killed only the verified current primary and observed a different survivor primary.
- [ ] Recorded whether traffic actually overlapped the failure and what errors occurred.
- [ ] Restarted the crashed member and verified full convergence after writer termination.
- [ ] Verified every acknowledged identity and reconciled uncertain identities against committed history.
- [ ] Deliberately stopped both validated secondaries only in the quorum-loss exercise.
- [ ] Observed the survivor's stepdown and a non-acknowledged probe without relabeling its error.
- [ ] Restored a writable pair, verified a majority recovery marker, then restored all members.
- [ ] Verified exact final rows, unchanged configuration and original resource contracts.
- [ ] Preserved evidence and completed scoped cleanup.

**Evidence:** topology/versions, generated crash/stop/start commands, event timestamps, Docker/log outcomes, traffic ledger/raw errors, acknowledged/uncertain identity reconciliation, committed/local snapshots, quorum-loss response and cleanup. Runtime validation remains pending until executed. Concurrent traffic coverage must be recorded separately from topology recovery. A complete written Part 4 does not make any runtime lab canonical.

## 16. Review questions

1. Why must traffic stop before exact final fixture reconciliation?
2. Why can a timed-out request be present after recovery?
3. What separates a new primary from a fully recovered replica set?
4. Why can a running lone member not provide the intended write service?
5. Why is the two-secondary stop acceptable only as a deliberate disposable failure test?
6. How do exact payload checks improve on document-count checks?
7. What does a sampled request ledger fail to prove about continuous availability?
8. Which tests remain necessary for production retries, external effects and disaster recovery?

## 17. Official references

- [MongoDB 8.0: replica-set elections](https://www.mongodb.com/docs/v8.0/core/replica-set-elections/)
- [MongoDB 8.0: write concern](https://www.mongodb.com/docs/v8.0/reference/write-concern/)
- [MongoDB 8.0: insert command and response fields](https://www.mongodb.com/docs/v8.0/reference/command/insert/)
- [MongoDB 8.0: $currentOp and access requirements](https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/currentOp/)
- [MongoDB 8.0: majority read concern](https://www.mongodb.com/docs/v8.0/reference/read-concern-majority/)
- [MongoDB 8.0: rollbacks during failover](https://www.mongodb.com/docs/v8.0/core/replica-set-rollbacks/)
- [MongoDB 8.0: resync a member](https://www.mongodb.com/docs/v8.0/tutorial/resync-replica-set-member/)
- [Docker Compose: kill](https://docs.docker.com/reference/cli/docker/compose/kill/)
- [Docker Compose: start](https://docs.docker.com/reference/cli/docker/compose/start/)

---

Previous: [Chapter 31 — Network Partitions Rollback and Consistency](31-network-partitions-rollback-and-consistency.md)  
Next: [Chapter 33 — Sharded Cluster Architecture](33-sharded-cluster-architecture.md).
