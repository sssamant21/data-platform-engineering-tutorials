# 28 — Elections Stepdown and Planned Maintenance

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Rehearse one-member-at-a-time restarts, perform a non-forced primary stepdown, and verify topology and application state after each maintenance action.  
**Audience:** DBREs, SREs and Platform Engineers  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; Docker/Compose project from Chapter 26. Record exact versions and image digest.  
**Deployment:** Disposable three-voting-data-member rs26 on one host. This lab deliberately changes availability only within that owned project.

## 1. Planned handoff is not an unplanned crash

An election chooses an eligible primary when conditions require it. A planned stepdown lets a primary relinquish its role while an eligible secondary catches up. Client operations can encounter interruptions or selection delays during the transition.

Do not promise zero application impact merely because a replica set has three members. Driver discovery, request deadlines, retries, concerns and pool behavior determine what callers experience. This lab validates bounded observations and post-transition writes; it does not measure uninterrupted service under representative traffic.

The maintenance sequence is:

1. Verify all three members are healthy and application state is correct.
2. Restart each current secondary individually, waiting for full recovery before the next action.
3. Step down the primary without force.
4. Verify a different primary and a healthy old-primary secondary.
5. Restart the former primary only while it is still secondary.
6. Verify the full set and application state.

No versions, FCV, votes, priorities or replica-set configuration change. This is a restart rehearsal, not an upgrade procedure.

## 2. Quorum and capacity before maintenance

With three voting data-bearing members, two voting members constitute an election majority. Removing one healthy secondary leaves two members. Removing another before recovery leaves only one and breaks the intended quorum.

Quorum arithmetic alone is insufficient: the survivors must be reachable, eligible and able to support application work/acknowledgements. A lagging or resource-constrained survivor can make a seemingly valid maintenance plan unsafe.

| Precondition | Evidence | Stop if |
|---|---|---|
| Correct owned topology | Set name, config, project resources | Shared/production set or unexpected member |
| One primary/two secondaries | replSetGetStatus | Any member is unhealthy/transitional |
| Fixture convergence | Direct member reads | State differs or read fails |
| Surviving capacity | CPU/memory/storage/lag evidence | Known pressure or backlog |
| Client discovery | Seeded URI and reachable hosts | Client tied to stopped member |
| Recovery path | Same image, volumes, startup config | Data/config ownership unclear |

Do not use force:true to bypass failed catch-up checks. Stop and diagnose readiness. Partition/rollback exercises follow in Chapters 31–32.

## 3. Prerequisites and independent client

Retain or rebuild the Chapter 26 project. Ensure no chapter automation is modifying it. Use only the owned mongodb-ch26 project and preserve its volumes.

The operator needs replica-set status/config inspection, replSetStepDown authorization and database-scoped lab access. Docker access controls the disposable services. No role grants are included.

Run the client in its own temporary container, so stopping member a does not stop the operator shell:

```bash
docker compose -p mongodb-ch26 ps
docker run --rm -it --network mongodb-ch26_replica mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=5000"
```

The default Compose network name assumes the exact Chapter 26 project definition. Inspect the actual project network if it differs. Use the same approved image digest as the members for repeatability.

The client publishes no ports and uses the existing internal network. Keep another host terminal open for Compose stop/start commands. Do not run the maintenance control shell inside a member you may stop.

## 4. Initial checks and reusable readiness helpers

In the independent mongosh client:

```javascript
const labName28 = "mongodb_enterprise_tutorial_ch28";
const lab28 = db.getSiblingDB(labName28);
const allowedHosts28 = ["a:27017", "b:27017", "c:27017"];
function check28(condition, message) {
  if (!condition) throw new Error(message);
}
const config28 = db.adminCommand({ replSetGetConfig: 1 }).config;
check28(config28._id === "rs26" && config28.members.length === 3,
        "Only the owned Chapter 26 rs26 topology is permitted");
check28(config28.members.every(m =>
  allowedHosts28.includes(m.host) && m.arbiterOnly !== true &&
  m.hidden !== true && (m.votes === undefined || Number(m.votes) === 1) &&
  Number(m.priority === undefined ? 1 : m.priority) > 0 &&
  Number(m.secondaryDelaySecs || 0) === 0),
  "Unexpected member configuration; stop before maintenance");
check28(lab28.getCollectionNames().length === 0,
        "Chapter database exists; review before rerunning");
function healthy28(status) {
  return status && status.ok === 1 && status.members.length === 3 &&
    status.members.filter(m => m.health === 1 && m.stateStr === "PRIMARY").length === 1 &&
    status.members.filter(m => m.health === 1 && m.stateStr === "SECONDARY").length === 2;
}
function waitHealthy28(timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() < deadline) {
    try {
      last = db.adminCommand({ replSetGetStatus: 1 });
      if (healthy28(last)) return last;
    } catch (error) {
      print("Readiness observation: " + error.message);
    }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Full topology did not recover within lab observation budget");
}
function primaryName28(status) {
  const found = status.members.find(m => m.stateStr === "PRIMARY" && m.health === 1);
  check28(found, "No healthy primary observed");
  return found.name;
}
const initialStatus28 = waitHealthy28();
printjson({ version: db.version(), primary: primaryName28(initialStatus28),
            members: initialStatus28.members.map(m =>
              ({ name: m.name, state: m.stateStr, health: m.health })) });
```

Record mongosh/Docker/Compose versions and image digest separately. The 90-second limit is an observation budget, not an election/recovery SLA.

## 5. Seed deterministic application state

```javascript
lab28.createCollection("events");
const events28 = lab28.events;
const concern28 = { w: "majority", j: true, wtimeout: 10000 };
events28.insertMany([
  { _id: "baseline-0", revision: 1 },
  { _id: "baseline-1", revision: 1 }
], { writeConcern: concern28 });
const expectedIds28 = ["baseline-0", "baseline-1"];
function verifyPrimary28() {
  const rows = events28.find().sort({ _id: 1 }).toArray();
  check28(JSON.stringify(rows.map(r => r._id)) ===
          JSON.stringify([...expectedIds28].sort()), "Fixture identity mismatch");
  check28(rows.every(r => Number(r.revision) === 1), "Fixture revision mismatch");
}
function verifyMembers28() {
  for (const host of allowedHosts28) {
    const connection = new Mongo(
      "mongodb://" + host + "/?directConnection=true&serverSelectionTimeoutMS=5000"
    );
    connection.setReadPref("secondaryPreferred");
    const collection = connection.getDB(labName28).events;
    const deadline = Date.now() + 30000;
    let rows = [];
    while (Date.now() < deadline) {
      rows = collection.find().sort({ _id: 1 }).toArray();
      if (JSON.stringify(rows.map(r => r._id)) ===
          JSON.stringify([...expectedIds28].sort()) &&
          rows.every(r => Number(r.revision) === 1)) break;
      sleep(500);
    }
    check28(JSON.stringify(rows.map(r => r._id)) ===
            JSON.stringify([...expectedIds28].sort()) &&
            rows.every(r => Number(r.revision) === 1),
            "Member fixture did not converge: " + host);
  }
}
verifyPrimary28();
verifyMembers28();
```

Stable identities let you reconcile uncertain outcomes. If any write errors, stop and inspect state; do not add its identity to the expected list without confirming the business operation.

## 6. Restart secondaries one at a time

Capture the two original secondaries and the original primary:

```javascript
const maintenanceStart28 = waitHealthy28();
const originalPrimary28 = primaryName28(maintenanceStart28);
const secondaryQueue28 = maintenanceStart28.members
  .filter(m => m.stateStr === "SECONDARY").map(m => m.name);
printjson({ originalPrimary: originalPrimary28, secondaryQueue: secondaryQueue28 });
function prepareSecondaryRestart28(host) {
  check28(allowedHosts28.includes(host), "Target is outside owned lab");
  const current = waitHealthy28();
  const member = current.members.find(m => m.name === host);
  check28(member && member.stateStr === "SECONDARY" && member.health === 1,
          "Target is not a healthy secondary; do not stop it");
  verifyMembers28();
  const service = host.split(":")[0];
  print("NEXT HOST COMMAND: docker compose -p mongodb-ch26 stop --timeout 60 " + service);
  print("RECOVERY COMMAND: docker compose -p mongodb-ch26 start " + service);
  return service;
}
let targetHost28 = secondaryQueue28[0];
prepareSecondaryRestart28(targetHost28);
```

Copy only the generated stop command into the host terminal. It targets one validated service. Immediately before stopping, rerun the role check if time has elapsed; roles can change.

After the stop returns, start that same service using the generated recovery command. Do not remove its container or volumes, change its image or stop a second member.

Back in the client:

```javascript
const firstRestartRecovered28 = waitHealthy28();
verifyPrimary28();
verifyMembers28();
printjson(firstRestartRecovered28.members.map(m =>
  ({ name: m.name, state: m.stateStr, health: m.health })));
targetHost28 = secondaryQueue28[1];
prepareSecondaryRestart28(targetHost28);
```

Repeat the generated stop/start pair for the second target. Then:

```javascript
const secondRestartRecovered28 = waitHealthy28();
verifyPrimary28();
verifyMembers28();
printjson(secondRestartRecovered28.members.map(m =>
  ({ name: m.name, state: m.stateStr, health: m.health })));
```

If a target has become primary, the guard stops. Do not bypass it; reconcile the current topology and select a current secondary deliberately.

Docker stop sends a graceful signal and waits up to the stated timeout before escalation. If shutdown does not complete cleanly, inspect logs; do not silently label a forced termination as successful planned shutdown.

## 7. Record the primary and perform a non-forced stepdown

Recollect the current primary after secondary maintenance:

```javascript
const preStepdown28 = waitHealthy28();
verifyMembers28();
const steppedHost28 = primaryName28(preStepdown28);
const stepConnection28 = new Mongo(
  "mongodb://" + steppedHost28 + "/?directConnection=true&serverSelectionTimeoutMS=5000"
);
const stepAdmin28 = stepConnection28.getDB("admin");
check28(stepAdmin28.runCommand({ hello: 1 }).isWritablePrimary,
        "Selected target is no longer primary");
const stepStarted28 = Date.now();
let stepResponse28 = null;
let stepError28 = null;
try {
  stepResponse28 = stepAdmin28.runCommand({
    replSetStepDown: 120,
    secondaryCatchUpPeriodSecs: 15
  });
  printjson(stepResponse28);
} catch (error) {
  stepError28 = { code: error.code, message: error.message };
  printjson(stepError28);
}
```

The 120-second value temporarily prevents this member from standing for election after successful stepdown. The catch-up allowance is 15 seconds. No force flag is used.

A returned error or connection interruption is evidence to interpret, not automatic proof that stepdown succeeded. Confirm the actual topology next. Do not universally expect all clients to disconnect; behavior is version-specific.

## 8. Verify handoff, not merely command output

```javascript
const postStepdown28 = waitHealthy28();
const newPrimary28 = primaryName28(postStepdown28);
check28(newPrimary28 !== steppedHost28,
        "Different primary not observed; investigate stepdown outcome");
check28(postStepdown28.members.find(m =>
  m.name === steppedHost28).stateStr === "SECONDARY",
  "Former primary did not become secondary");
printjson({
  oldPrimary: steppedHost28, newPrimary: newPrimary28,
  observationElapsedMs: Date.now() - stepStarted28,
  response: stepResponse28, error: stepError28
});
const handoffWrite28 = events28.insertOne({
  _id: "after-handoff", revision: 1
}, { writeConcern: concern28 });
check28(handoffWrite28.acknowledged, "Post-handoff write not acknowledged");
expectedIds28.push("after-handoff");
verifyPrimary28();
verifyMembers28();
```

Elapsed time includes command/catch-up and observation work. It is not measured application outage or election-only duration. No continuous traffic ran during this handoff.

A direct connection to the old primary remains bound to that member. A seeded connection can select the new primary. That difference is an application design requirement, not a reason to change replica configuration.

## 9. Restart the former primary only as a secondary

```javascript
prepareSecondaryRestart28(steppedHost28);
```

Use the generated stop/start commands, one service only, then return to the client:

```javascript
const finalStatus28 = waitHealthy28();
verifyPrimary28();
verifyMembers28();
printjson({
  finalPrimary: primaryName28(finalStatus28),
  members: finalStatus28.members.map(m =>
    ({ name: m.name, state: m.stateStr, health: m.health }))
});
```

If the stepdown period elapsed and the target became primary again, the guard rejects it. Reassess the maintenance sequence. Do not stop it merely because it was previously named “old primary.”

The final primary need not remain the same forever. Do not force an election to restore the original leader as a cosmetic rollback. Preserve a healthy eligible topology and correct application state.

## 10. Failure exercise: maintenance gate rejects unsafe topology

Use synthetic status documents rather than stopping a second live member:

```javascript
const unsafeStatus28 = {
  ok: 1,
  members: [
    { name: "a:27017", stateStr: "PRIMARY", health: 1 },
    { name: "b:27017", stateStr: "SECONDARY", health: 1 },
    { name: "c:27017", stateStr: "UNKNOWN", health: 0 }
  ]
};
check28(!healthy28(unsafeStatus28), "Unsafe maintenance gate incorrectly passed");
const recoveredStatus28 = {
  ok: 1,
  members: [
    { name: "a:27017", stateStr: "PRIMARY", health: 1 },
    { name: "b:27017", stateStr: "SECONDARY", health: 1 },
    { name: "c:27017", stateStr: "SECONDARY", health: 1 }
  ]
};
check28(healthy28(recoveredStatus28), "Recovered maintenance gate rejected");
printjson({ unsafeGate: healthy28(unsafeStatus28),
            recoveredGate: healthy28(recoveredStatus28) });
```

Diagnosis: the set already has a missing/unhealthy member, so another planned restart should not begin. Correction is recovering the existing problem and verifying full readiness, not bypassing the gate.

This pure classification does not test an actual quorum-loss outage. The lab intentionally preserves the one-member-at-a-time rule.

## 11. Recovery when an action fails

If a stopped service fails to start, keep the other two members running. Inspect only the owned target's logs/state and recover that target with the same volumes and configuration.

```bash
docker compose -p mongodb-ch26 ps
docker compose -p mongodb-ch26 logs --tail 100 a b c
```

Use the exact previously generated start command for the affected service. Do not execute another stop command until the full readiness and fixture checks pass.

If stepdown reports catch-up/eligibility failure, inspect lag, health, priorities, voting and resource pressure. Preserve the response. Do not retry repeatedly with force or shorten election settings to make the chapter pass.

If an application write returned an uncertain error, query its stable identity and reconcile before replay. Ordinary reconnect success does not resolve the business operation by itself.

## 12. Production maintenance planning

A production window needs an inventory of versions/configuration, tested backups, rollback/recovery steps, client readiness, resource margins, monitoring and explicit stop conditions. This lab's Docker restart is not a version-upgrade runbook.

Observe foreground latency/errors, driver server-selection delays, replication lag, CPU/memory/storage and elections. Review surviving-member capacity during each restart. Stop when data convergence, latency/error budgets or topology readiness fail.

Communicate that planned leadership changes can interrupt operations; validate application retry/idempotency and deadline behavior under representative traffic. Do not promise zero downtime based only on post-action success.

Do not conflate planned restarts with running a replica member as a standalone for special maintenance. Such procedures have separate isolation, port and supported-operation requirements and are not performed here.

## 13. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Gate rejects restart | Full status and target role | Existing unhealthy member or target became primary | Recover/reassess before stopping |
| Stepdown refuses | Command response, lag and eligibility | No suitable caught-up secondary | Fix readiness; no forced fallback |
| New primary not observed | Seeded client, status, network | Selection/election/connectivity issue | Preserve error and diagnose topology |
| Old connection rejects writes | directConnection and hello | It remains bound to a secondary | Use replica-set-aware application routing |
| Restarted member stays recovering | Logs, storage, optimes | Startup/replication backlog | Recover one member before continuing |
| Same fixture differs after restart | Direct member reads | Lag or real state mismatch | Stop, reconcile identity and history |
| Shell says command interrupted | Response and post-action status | Transition affected command path | Verify outcome, never assume success |
| “Outage time” based on polling | Measurement interval and traffic | Observation latency mistaken for request availability | Use representative application traces |

## 14. Cleanup and restoration

Ensure all services are running and all members are healthy before cleanup. Leave configuration, votes, priorities and image unchanged. Temporary stepdown ineligibility expires naturally; no preferred-primary restoration is required.

```javascript
waitHealthy28();
verifyMembers28();
check28(events28.countDocuments({}) === 3, "Final fixture count mismatch");
if (lab28.getName() !== "mongodb_enterprise_tutorial_ch28") {
  throw new Error("Refusing cleanup outside the Chapter 28 training database");
}
const dropResult28 = lab28.dropDatabase();
if (dropResult28.ok !== 1) throw new Error("Chapter 28 database cleanup failed");
check28(lab28.getCollectionNames().length === 0, "Cleanup incomplete");
```

Retain the Chapter 26 project for the next labs. If dismantling the owned disposable project instead, exit the independent client and follow Chapter 26's down --volumes procedure deliberately.

No process-wide settings changed. A failed member restart requires restoring that service first; dropping the chapter database is not topology recovery.

## 15. Acceptance and evidence

- [ ] Recorded versions, project ownership, member configuration and initial readiness.
- [ ] Used an independent client with replica-set-aware discovery.
- [ ] Reconciled baseline data on every member.
- [ ] Restarted each secondary individually with full recovery between actions.
- [ ] Performed non-forced stepdown with bounded catch-up.
- [ ] Observed a different primary and former-primary secondary.
- [ ] Verified a majority-acknowledged post-handoff write on all members.
- [ ] Restarted the former primary only while it was secondary.
- [ ] Validated unsafe/recovered maintenance-gate logic.
- [ ] Recorded observation limits and restored healthy topology before cleanup.

**Evidence:** configuration/status, generated target commands, shutdown/startup logs, direct member assertions, stepdown response/error, old/new primary identities, observation timings, application state and cleanup. Runtime validation remains pending until executed. Post-transition success is not proof of uninterrupted production traffic.

## 16. Review questions

1. Why must every restarted member recover before the next stop?
2. Why is a separate client container useful for this lab?
3. What does a non-forced stepdown check before relinquishing primary?
4. Why is a command error insufficient to determine the final topology?
5. Why should an old-primary target be rechecked immediately before stopping?
6. Why should the original primary not be forcibly restored for cosmetic consistency?
7. What separates observation elapsed time from application outage?
8. Which acceptance criteria are needed for a real upgrade beyond this restart rehearsal?

## 17. Official references

- [MongoDB 8.0: rs.stepDown](https://www.mongodb.com/docs/v8.0/reference/method/rs.stepDown/)
- [MongoDB 8.0: replica-set elections](https://www.mongodb.com/docs/v8.0/core/replica-set-elections/)
- [MongoDB 8.0: maintenance on replica-set members](https://www.mongodb.com/docs/v8.0/tutorial/perform-maintenance-on-replica-set-members/)
- [MongoDB 8.0: process shutdown behavior](https://www.mongodb.com/docs/v8.0/tutorial/manage-mongodb-processes/)
- [MongoDB 8.0: replica-set rollback boundaries](https://www.mongodb.com/docs/v8.0/core/replica-set-rollbacks/)

---

Previous: [Chapter 27 — Read Preference Read Concern and Write Concern](27-read-preference-read-concern-and-write-concern.md)  
Next: [Chapter 29 — Replication Lag and Oplog Sizing](29-replication-lag-and-oplog-sizing.md).
