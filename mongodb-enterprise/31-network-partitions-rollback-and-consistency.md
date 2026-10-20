# 31 — Network Partitions Rollback and Consistency

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Isolate the current primary, verify the surviving majority's election and durable writes, heal connectivity, reconcile operation identities and distinguish observed rollback from a rejected write.  
**Audience:** DBREs, SREs, Developers and Platform Engineers  
**Time:** 120–150 minutes  
**Baseline:** MongoDB 8.0, mongosh and Docker Compose v2; record exact versions and image digest.  
**Deployment:** Owned disposable Chapter 26 `rs26`, three voting data members on one host. Community-compatible; no Enterprise-only feature validation.  
**Prerequisites:** Chapters 25–30; original storage restored, override removed, full topology and fixtures reconciled, no concurrent automation.

## 1. A partition creates different local views

A network partition breaks communication even when processes remain running. A three-member set can split into a reachable pair and an isolated member. The pair can form an election majority; the isolated former primary eventually relinquishes leadership after detecting lost majority connectivity.

These transitions are not instantaneous. An isolated member can briefly report itself primary while the majority is electing another. Observe each member's view and operation outcomes; a single stale role sample does not establish sustained writable split brain.

This lab disconnects only the current primary's Docker network endpoint. The majority-side client remains connected to both survivors. An operator uses `docker compose exec` and loopback to inspect the isolated process. No votes, priorities, election settings, storage, FCV or images change.

**Use case:** Applications see server-selection delays and uncertain writes after a network event. The operator needs to restore connectivity and reconcile affected operations without blindly replaying business actions.

## 2. Durability, visibility and application meaning

| Contract or observation | What it establishes | What still needs checking |
|---|---|---|
| `w:1` acknowledgement | Primary accepted the operation | Replication/commit survival after leadership change |
| `w:1, j:true` | Local journal acknowledgement | Majority replication; local durability is insufficient |
| `w:"majority", j:true` success | Requested majority journal acknowledgement satisfied | Business meaning, request identity and external side effects |
| Write-concern timeout or transport error | Requested outcome was not confirmed | Whether the operation applied and later committed |
| Local read sees a document | State visible in that member's local view | It may be uncommitted or subsequently rolled back |
| Majority read sees a document | Document visible in committed history | It does not imply the newest possible application state |

Write concern describes acknowledgement; read concern describes visibility. Neither substitutes for request identity, idempotency or reconciliation with external systems. Replica-set rollback resolves divergent replication history; it is not an application undo feature.

## 3. Lab scope and recovery contract

The partition exercise is required. The rollback observation is conditional: one bounded `w:1` write is attempted immediately after disconnect. If stepdown already occurred, the write is rejected and no divergent fixture exists. Record that result honestly; do not alter election timing, enable failpoints or repeat rapidly until an attractive result appears.

If the write applies only to the isolated member and a different branch advances on the majority, recovery can roll it back. Require document-history evidence and member rollback evidence before claiming this happened.

Stop conditions: wrong project/network, unexpected member/mounts, another unhealthy member, survivor resource pressure, failed majority write, missing recovery command or unexplained fixture mismatch. Heal the original network endpoint immediately when a dependent step fails. Never disconnect a second member or force reconfiguration.

This fixture changes availability and may generate rollback artifacts in the owned disposable project. Other retained lab databases should have no active writers. Do not run this procedure against production/shared services.

## 4. Inventory and independent client

From the original Chapter 26 Compose folder:

```bash
docker compose -p mongodb-ch26 -f compose.yaml config
docker compose -p mongodb-ch26 -f compose.yaml ps
docker network inspect mongodb-ch26_replica
docker run --rm -it --network mongodb-ch26_replica mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=5000&retryWrites=false"
```

Use the approved image digest. The client publishes no ports and remains on the internal project network. Keep a host terminal open for network commands and a local probe. `retryWrites=false` makes this single-attempt teaching experiment easier to attribute; production driver policies require their own testing.

Confirm the network's project/name labels, all three containers' network membership, aliases and original volumes. Preserve each target endpoint's alias list and IP before disconnect. This lab assumes default Chapter 26 service/container names; inspect actual names before using generated commands.

Docker control handles the partition. MongoDB permissions cover status/config/serverStatus inspection and scoped fixture operations. Production requires approved authentication/TLS; the isolated Chapter 26 topology has neither. No credentials or role changes are included.

## 5. Readiness, helpers and current primary

In the independent mongosh client:

```javascript
const hosts31 = ["a:27017", "b:27017", "c:27017"];
const name31 = "mongodb_enterprise_tutorial_ch31";
const lab31 = db.getSiblingDB(name31);
const wc31 = { w: "majority", j: true, wtimeout: 10000 };
function check31(condition, message) {
  if (!condition) throw new Error(message);
}
function direct31(host) {
  check31(hosts31.includes(host), "Host outside owned lab");
  const c = new Mongo("mongodb://" + host +
    "/?directConnection=true&serverSelectionTimeoutMS=5000&retryWrites=false");
  c.setReadPref("secondaryPreferred");
  return c;
}
function status31() { return db.adminCommand({ replSetGetStatus: 1 }); }
function healthy31(s) {
  return s && s.ok === 1 && s.set === "rs26" && s.members.length === 3 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "PRIMARY").length === 1 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "SECONDARY").length === 2;
}
function waitHealthy31(timeoutMs = 180000) {
  const end = Date.now() + timeoutMs;
  let last;
  while (Date.now() < end) {
    try { last = status31(); if (healthy31(last)) return last; }
    catch (error) { print(error.message); }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Full topology not observed within budget");
}
const cfg31 = db.adminCommand({ replSetGetConfig: 1 }).config;
check31(cfg31._id === "rs26" && cfg31.members.length === 3 &&
  cfg31.members.every(m => hosts31.includes(m.host) && !m.arbiterOnly && !m.hidden &&
    Number(m.votes === undefined ? 1 : m.votes) === 1 &&
    Number(m.priority === undefined ? 1 : m.priority) > 0 &&
    Number(m.secondaryDelaySecs || 0) === 0), "Unexpected topology");
const originalConfig31 = EJSON.stringify(cfg31);
check31(lab31.getCollectionNames().length === 0,
        "Chapter database exists; inspect before rerunning");
const initial31 = waitHealthy31();
const oldPrimary31 = initial31.members.find(m => m.stateStr === "PRIMARY").name;
const oldService31 = oldPrimary31.split(":")[0];
const oldContainer31 = "mongodb-ch26-" + oldService31 + "-1";
const survivors31 = hosts31.filter(h => h !== oldPrimary31);
function rollbackId31(host) {
  const s = direct31(host).getDB("admin").runCommand({ serverStatus: 1, repl: 1 });
  check31(s.ok === 1 && s.repl && s.repl.rbid !== undefined,
          "Rollback identifier unavailable on " + host);
  return Number(s.repl.rbid);
}
const beforeRbid31 = rollbackId31(oldPrimary31);
printjson({ version: db.version(), isolatedTarget: oldPrimary31,
            survivors: survivors31, rollbackId: beforeRbid31 });
```

Record exact server/mongosh/Docker/Compose versions, image digest, initial roles and configuration. No member is stopped. Timeout values are lab observation budgets, not failover SLAs.

## 6. Majority baseline and operation identities

```javascript
check31(lab31.createCollection("events").ok === 1, "Collection creation failed");
const events31 = lab31.events;
check31(events31.insertOne({ _id: "baseline", revision: 1, branch: "committed" },
  { writeConcern: wc31 }).acknowledged, "Baseline acknowledgement failed");
function readRows31(host) {
  return direct31(host).getDB(name31).events.find().sort({ _id: 1 }).toArray();
}
function baselineValid31(rows) {
  return rows.length === 1 && rows[0]._id === "baseline" &&
    Number(rows[0].revision) === 1 && rows[0].branch === "committed";
}
for (const host of hosts31) {
  const end = Date.now() + 30000;
  let rows;
  do { rows = readRows31(host); if (baselineValid31(rows)) break; sleep(500); }
  while (Date.now() < end);
  check31(baselineValid31(rows), "Baseline not converged: " + host);
}
const fixtureInfo31 = lab31.getCollectionInfos({ name: "events" })[0];
printjson({ namespace: name31 + ".events", uuid: fixtureInfo31.info.uuid,
  identities: ["baseline", "minority-candidate", "majority-after"] });
```

Baseline state must match every member before the partition. The candidate identity belongs only to the local probe; do not replay it through the majority client. The post-election identity belongs to a separate majority-acknowledged write.

## 7. Prepare all host commands before disconnect

Generate commands in the independent client. Inspect the target's actual network attachments and container name first:

```javascript
print("INSPECT TARGET: docker inspect " + oldContainer31);
print("DISCONNECT: docker network disconnect mongodb-ch26_replica " + oldContainer31);
print("HEAL: docker network connect --alias " + oldService31 +
  " --alias " + oldContainer31 + " mongodb-ch26_replica " + oldContainer31);
```

The HEAL command restores Chapter 26's normal service and container aliases. If inspection shows additional aliases, preserve them with additional `--alias` flags. For nonstandard static addressing, review and preserve the original IP using Docker's supported options. Do not guess an endpoint configuration.

Prepare this local probe by generating its full command:

```javascript
const probeCode31 = [
  'const d = db.getSiblingDB("mongodb_enterprise_tutorial_ch31");',
  'const h = db.adminCommand({hello:1});',
  'let response = null; let error = null;',
  'if (h.isWritablePrimary === true) {',
  '  try { response = d.runCommand({insert:"events",',
  '    documents:[{_id:"minority-candidate",revision:1,branch:"isolated"}],',
  '    ordered:true,maxTimeMS:1500,writeConcern:{w:1,j:true}}); }',
  '  catch(e) { error = {code:e.code,message:e.message}; }',
  '}',
  'db.getMongo().setReadPref("secondaryPreferred");',
  'let local = null; let readError = null;',
  'try { const r = d.runCommand({find:"events",filter:{_id:"minority-candidate"},',
  '  limit:1,singleBatch:true,readConcern:{level:"local"},maxTimeMS:1500});',
  '  if(r.ok===1) local = r.cursor.firstBatch;',
  '  else readError = {code:r.code,message:r.errmsg}; }',
  'catch(e) { readError = {code:e.code,message:e.message}; }',
  'printjson({at:new Date(),hello:h,response,error,local,readError});'
].join(" ");
check31(!probeCode31.includes("'"), "Probe requires shell quoting review");
print("LOCAL PROBE: docker compose -p mongodb-ch26 -f compose.yaml exec -T " +
  oldService31 + ' mongosh "mongodb://localhost:27017/?directConnection=true&serverSelectionTimeoutMS=2000&socketTimeoutMS=5000&retryWrites=false" --quiet --eval ' +
  "'" + probeCode31 + "'");
```

The generated command uses shell single quoting for the JavaScript; run it in Bash or PowerShell, not Windows `cmd.exe`. Keep the literal quotes. It targets loopback inside the isolated member and performs at most one raw insert, with no automatic retry. Capture its complete output separately from other commands.

The hello check can become stale before the insert. Record the actual response, write errors and local read, not only hello. `maxTimeMS`, selection and socket timeouts bound different stages; an interrupted request may still have applied.

## 8. Trigger the partition and run one local probe

Immediately before disconnect, recheck current primary and full readiness:

```javascript
const gate31 = waitHealthy31();
check31(gate31.members.find(m => m.name === oldPrimary31)?.stateStr === "PRIMARY",
        "Primary changed; reassess and regenerate target commands");
check31(direct31(oldPrimary31).getDB("admin").runCommand({ hello: 1 }).isWritablePrimary,
        "Direct role check failed");
check31(EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalConfig31, "Configuration changed");
const partitionObservedStart31 = Date.now();
```

In the host terminal, run the generated DISCONNECT command, then the prepared LOCAL PROBE immediately. If disconnect fails, do not run the probe as though isolation succeeded. Inspect the target to verify that the project network endpoint is absent; other networks would invalidate the isolation contract.

Expected outcomes are conditional:

| Probe result | Interpretation |
|---|---|
| Insert `ok=1`, `n=1`, no write/write-concern errors, local candidate present | Locally acknowledged divergent candidate; still not majority committed |
| Hello is already non-primary and candidate absent | Probe skipped after stepdown; rollback fixture not created |
| Not-primary response and candidate absent | Role changed before insert; candidate rejected |
| Transport/timeout/other error or local read unavailable | Outcome unresolved; preserve evidence and reconcile |

Do not repeat the probe. Do not extend the partition merely to make a write land. If any unexpected process/resource failure occurs, use the saved HEAL command immediately and continue recovery before cleanup.

## 9. Observe the majority's election and durable write

Back in the independent seeded client:

```javascript
function waitMajorityPrimary31(timeoutMs = 90000) {
  const end = Date.now() + timeoutMs;
  let last;
  while (Date.now() < end) {
    try {
      last = status31();
      const p = last.members.find(m => m.health === 1 && m.stateStr === "PRIMARY");
      const survivorStates = last.members.filter(m => survivors31.includes(m.name));
      if (p && survivors31.includes(p.name) && survivorStates.length === 2 &&
          survivorStates.every(m => m.health === 1 &&
            ["PRIMARY", "SECONDARY"].includes(m.stateStr))) return { status: last, primary: p.name };
    } catch (error) { print(error.message); }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Majority primary not observed; HEAL NETWORK NOW");
}
const majoritySide31 = waitMajorityPrimary31();
const newPrimary31 = majoritySide31.primary;
check31(newPrimary31 !== oldPrimary31, "Different primary not observed");
const committedWrite31 = events31.insertOne({
  _id: "majority-after", revision: 1, branch: "committed"
}, { writeConcern: wc31 });
check31(committedWrite31.acknowledged, "Majority-side write not acknowledged; HEAL NOW");
const committedRead31 = lab31.runCommand({ find: "events",
  filter: { _id: { $in: ["baseline", "majority-after"] } },
  sort: { _id: 1 }, limit: 10, singleBatch: true,
  readConcern: { level: "majority" }, maxTimeMS: 5000 });
check31(committedRead31.ok === 1 && committedRead31.cursor.firstBatch.length === 2,
        "Committed fixture not visible; HEAL NOW");
check31(events31.findOne({ _id: "minority-candidate" }) === null,
        "Candidate unexpectedly present on majority; inspect isolation and HEAL NOW");
printjson({ oldPrimary: oldPrimary31, majorityPrimary: newPrimary31,
  observationElapsedMs: Date.now() - partitionObservedStart31,
  committed: committedRead31.cursor.firstBatch });
```

Expected: the two survivors have a different primary and can acknowledge the new committed fixture. Preserve raw errors if any write is uncertain; the error does not prove absence. Reconcile `majority-after` instead of issuing a second insert blindly.

Elapsed observation includes polling, client selection and operator delay. No representative continuous application traffic is running, so this is not measured application outage or an election-duration SLA.

## 10. Heal first, then verify history and state

Run the saved HEAL command now. Use `docker network inspect mongodb-ch26_replica` and target inspection to verify restored membership and service aliases. If Docker reports already connected, inspect the existing endpoint instead of forcing a second attachment.

```javascript
const healed31 = waitHealthy31();
function finalValid31(rows) {
  return rows.length === 2 && rows[0]._id === "baseline" &&
    rows[1]._id === "majority-after" &&
    rows.every(r => Number(r.revision) === 1 && r.branch === "committed");
}
for (const host of hosts31) {
  const end = Date.now() + 90000;
  let rows;
  do { rows = readRows31(host); if (finalValid31(rows)) break; sleep(500); }
  while (Date.now() < end);
  check31(finalValid31(rows), "Final history did not converge on " + host);
  printjson({ host, rows });
}
const afterRbid31 = rollbackId31(oldPrimary31);
printjson({ oldPrimary: oldPrimary31, rollbackIdBefore: beforeRbid31,
  rollbackIdAfter: afterRbid31, identifierChanged: afterRbid31 !== beforeRbid31,
  finalMembers: healed31.members.map(m => ({ host: m.name, role: m.stateStr })) });
check31(EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalConfig31, "Configuration was not preserved");
```

Both committed identities must survive on all members; candidate absence alone does not prove rollback if it never applied. A member's rollback identifier change helps detect rollback but does not identify the business operation without the document/log timeline. Original-primary restoration is not a goal; leave a healthy topology rather than forcing a cosmetic election.

## 11. Classify rollback evidence and inspect artifacts

| Evidence | Lab classification |
|---|---|
| Candidate acknowledged and locally observed in isolation; absent on majority before heal; absent everywhere after heal; target rollback evidence changed | Rollback observed for the divergent fixture |
| Candidate skipped/rejected and never observed locally; no target rollback evidence | Partition/election observed; fixture rollback not exercised |
| Candidate outcome uncertain; logs/identifier insufficient | Inconclusive write/rollback observation; reconcile before acceptance |
| Candidate survives or committed fixture differs | Contract mismatch; investigate topology/history before cleanup |

Generate bounded target log/artifact commands:

```javascript
print("LOGS: docker compose -p mongodb-ch26 -f compose.yaml logs --tail 300 " + oldService31);
print("ARTIFACTS: docker compose -p mongodb-ch26 -f compose.yaml exec " +
  oldService31 + " find /data/db/rollback -type f -name '*.bson'");
```

The Linux `find` command runs inside the owned container. If the directory does not exist, record that output; do not treat it as proof no rollback occurred. Rollback file generation can depend on settings and operation type. Retain logs showing the rollback timeline and associate artifacts with the fixture's collection UUID captured in Section 6.

If a fixture rollback file exists, use the exact returned path with an installed compatible Database Tools `bsondump`. For example, replace the placeholder before executing:

```bash
docker compose -p mongodb-ch26 -f compose.yaml exec TARGET_SERVICE bsondump /data/db/rollback/EXACT_COLLECTION_UUID/EXACT_FILE.bson
```

The image may not include that tool; record its version or inspect a copied artifact with approved tooling. Do not invent a path or assume filenames. Rollback artifacts are forensic material, not a complete backup, and must not be blindly restored into current history. Keep patient/production data out of this synthetic exercise.

## 12. Failure exercise: uncertain outcome is not absence

Classify synthetic responses without creating another outage:

```javascript
function outcome31(e) {
  if (e.committedDocumentMatches === true) return "reconciled-present";
  if (e.terminalRejection === true && e.authoritativeAbsent === true)
    return "reconciled-rejected";
  return "unresolved";
}
check31(outcome31({ transportError: true }) === "unresolved",
        "Transport error incorrectly treated as absence");
check31(outcome31({ writeConcernTimeout: true }) === "unresolved",
        "Concern timeout incorrectly treated as absence");
check31(outcome31({ committedDocumentMatches: true, transportError: true }) ===
        "reconciled-present", "Present operation not reconciled");
check31(outcome31({ terminalRejection: true, authoritativeAbsent: true }) ===
        "reconciled-rejected", "Rejected operation classification failed");
printjson({ classifier: "passed", realProbe: "classify from captured evidence" });
```

Trigger: a timeout is interpreted as permission to replay an operation. Diagnosis: acknowledgement failed but application state is unresolved. Correction: reconcile stable identity and expected payload against committed current history, check in-flight/session outcomes and apply the business retry policy. One absent snapshot during a transition is insufficient to declare terminal absence.

This classifier validates decision logic only. It does not test driver retryable writes, transaction commit retry or external side-effect compensation.

## 13. Production investigation and troubleshooting

Capture affected time window, per-member local role/term/progress, network/DNS/TLS changes, application errors, write/read concerns, retries and operation identities. Align timestamps before inferring the sequence. Distinguish client-to-member reachability from member-to-member reachability.

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Old member briefly reports primary | Local hello timestamp and majority status | Failure detection still in progress | Observe actual writes/terms; do not force config |
| No survivor becomes primary | Health, DNS/network, votes and logs | Majority path or eligibility broken | Heal original network; diagnose survivors |
| Candidate rejected | Raw response and local state | Stepdown preceded probe | Record branch as not exercised |
| Candidate acknowledgement uncertain | Response/error and committed identity | Transport interruption or state transition | Reconcile without blind replay |
| Candidate never appears on majority | Isolation timeline and target local read | Divergent uncommitted history or rejected insert | Use complete rollback evidence |
| Healed member stays unreachable | Endpoint aliases/IP and DNS inside project | Incorrect network restoration | Restore recorded endpoint contract |
| ROLLBACK missed by polling | Identifier and target logs | State transition completed between samples | Use logs; do not invent observed states |
| Committed rows differ after heal | Exact IDs/payloads, concerns and topology | Wrong contract/history or unexpected mutations | Stop cleanup and investigate |
| Rollback file absent | File settings, operation type and logs | Artifacts not generated or unavailable | Preserve other evidence; no false negative |

Majority concerns protect the stated durability contract during ordinary failover; they are not a substitute for backups. Forced reconfiguration, quorum changes and correlated failures have separate risks and are not performed here. Do not adjust election timeout, priorities or flow control merely to make this teaching experiment faster.

## 14. Recovery and scoped cleanup

If any dependent assertion fails while disconnected, restore the saved endpoint first. Keep every container and original volume intact. If network healing fails, inspect Docker state/aliases and recover that single endpoint; do not restart or remove the whole project.

Before cleanup, preserve probe output, timing, rollback classification, logs, UUID and artifacts if present. Keep rollback files in their original member volume for later analysis; this chapter does not recursively delete `/data/db/rollback`.

```javascript
waitHealthy31();
for (const host of hosts31) check31(finalValid31(readRows31(host)),
                                   "Cleanup blocked by fixture mismatch: " + host);
check31(EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalConfig31, "Cleanup blocked by configuration change");
check31(lab31.getName() === "mongodb_enterprise_tutorial_ch31",
        "Refusing cleanup outside the Chapter 31 training database");
check31(lab31.dropDatabase().ok === 1, "Chapter database cleanup failed");
for (const host of hosts31) {
  const d = direct31(host).getDB(name31);
  const end = Date.now() + 30000;
  while (Date.now() < end && d.getCollectionNames().length !== 0) sleep(500);
  check31(d.getCollectionNames().length === 0, "Cleanup not converged: " + host);
}
waitHealthy31();
```

On the host, confirm original network membership and aliases once more:

```bash
docker network inspect mongodb-ch26_replica
docker compose -p mongodb-ch26 -f compose.yaml ps
```

Leave all three members running on original storage for Chapter 32. Do not use `down --volumes`, broad network removal, pruning or forced reconfiguration. No process-wide settings were changed. An inconclusive write needs reconciliation before final acceptance; dropping its database is not reconciliation.

## 15. Acceptance and evidence

- [ ] Recorded versions/image, project/network/volume ownership and original aliases.
- [ ] Verified full initial topology, configuration and majority baseline everywhere.
- [ ] Prepared the exact recovery command before disconnecting one current primary.
- [ ] Captured one bounded local probe with response/errors and local-read evidence.
- [ ] Observed a different primary on the surviving majority.
- [ ] Verified the committed post-election fixture with explicit majority concern.
- [ ] Healed the original endpoint and verified data convergence/configuration everywhere.
- [ ] Classified rollback as observed, not exercised or inconclusive using real evidence.
- [ ] Preserved member identifier/log/UUID/artifact evidence where available.
- [ ] Tested uncertain-outcome classification and completed scoped cleanup.

**Evidence:** endpoint inventory, generated commands, initial/full/majority status, local probe output, write/read concerns, exact document snapshots, rollback identifiers/logs, collection UUID/artifacts and restoration/cleanup. Runtime validation remains pending until executed. A rejected candidate validates the partition/election branch but does not validate fixture rollback. Static parsing does not establish runtime behavior or uninterrupted production service.

## 16. Review questions

1. Why can partitioned members briefly report conflicting role views?
2. Why is a locally journaled `w:1` write still exposed to rollback?
3. Why does candidate absence after healing not prove it was rolled back?
4. What makes a concern timeout different from a confirmed terminal rejection?
5. Why should recovery commands and aliases be captured before disconnect?
6. How do rollback identifiers and document identities complement each other?
7. Why should rollback files be reviewed rather than blindly replayed?
8. Which additional tests would establish application retry and availability behavior?

## 17. Official references

- [MongoDB 8.0: replica-set elections](https://www.mongodb.com/docs/v8.0/core/replica-set-elections/)
- [MongoDB 8.0: rollbacks during failover](https://www.mongodb.com/docs/v8.0/core/replica-set-rollbacks/)
- [MongoDB 8.0: write concern](https://www.mongodb.com/docs/v8.0/reference/write-concern/)
- [MongoDB 8.0: majority read concern](https://www.mongodb.com/docs/v8.0/reference/read-concern-majority/)
- [MongoDB 8.0: insert command](https://www.mongodb.com/docs/v8.0/reference/command/insert/)
- [MongoDB 8.0: serverStatus, including repl.rbid](https://www.mongodb.com/docs/v8.0/reference/command/serverStatus/)
- [Docker: network disconnect](https://docs.docker.com/reference/cli/docker/network/disconnect/)
- [Docker: network connect and aliases](https://docs.docker.com/reference/cli/docker/network/connect/)

---

Previous: [Chapter 30 — Initial Sync Resync and Member Replacement](30-initial-sync-resync-and-member-replacement.md)  
Next: [Chapter 32 — Replica Set Failure and Recovery Lab](32-replica-set-failure-and-recovery-lab.md).
