# 30 — Initial Sync Resync and Member Replacement

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Replace one secondary's storage with empty owned volumes, observe logical initial sync, reconcile application state and restore the original member storage.  
**Audience:** DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes  
**Baseline:** MongoDB 8.0, mongosh and Docker Compose v2; retain Chapter 26's exact Compose definition and record versions/image digest.  
**Deployment:** Disposable three-voting-data-member `rs26`, on one host. Community-compatible logical initial sync; Enterprise file-copy initial sync is not exercised.  
**Prerequisites:** Chapters 25–29, healthy topology, known volume ownership, adequate disk/CPU/memory and no concurrent lab automation.

## 1. Catch-up, initial sync and restore

An ordinary restart reuses existing data and can catch up through retained replication history. Initial sync builds a member's dataset anew. A resync rebuilds a member that cannot safely resume with its existing state. Backup restore recovers from a separately preserved recovery source; replication alone is not that source.

| Situation | Path to assess | Evidence before action |
|---|---|---|
| Short outage, usable history retained | Restart and incremental catch-up | Source overlap, target logs and applied progress |
| Required history unavailable | Supported resync | Confirm missing-history diagnosis and healthy current source |
| Failed secondary storage | Replacement storage and initial sync | Current survivors, identity, storage ownership and capacity |
| Hostname changes | Controlled member host reconfiguration | DNS/TLS/reachability and full current configuration |
| Accidental application deletion | Backup/PITR recovery | Recovery point and independently tested backup |

This lab practices empty-storage replacement at the same hostname and member ID. The healthy original volume is retained for restoration. It does not manufacture a stale member, perform a host rename or validate production backup recovery.

**Use case:** A secondary disk fails while two healthy members remain. An operator provisions replacement storage and verifies the replacement before considering the maintenance complete.

## 2. Sync phases and operational budget

Logical initial sync clones the dataset, builds indexes and reconciles changes from the source's history. Source reads, destination writes and index work compete with foreground traffic. A ping-ready process is not necessarily a readable secondary.

Plan for the full dataset, indexes, destination oplog/temporary work, repair time and catch-up. Source history must support sync continuity. Chapter 29's rate/window measurements inform that budget; a tiny fixture's completion time does not forecast a multi-terabyte rebuild.

File-copy initial sync is an Enterprise-specific alternative with its own version and operational restrictions. Do not assume a Community image tests that path. Neither logical sync nor file-copy sync authorizes copying a running data directory with ordinary filesystem tools.

Only one member is replaced at a time. Two remaining voting data members provide limited redundancy: another failure can affect majority writes and election availability. Stop if either survivor becomes unhealthy or resource/application budgets fail.

## 3. Independent client and resource inventory

Use the original Chapter 26 working folder containing `compose.yaml`. Do not use a different project or an edited Compose definition without reviewing every mount and startup option.

```bash
docker compose -p mongodb-ch26 -f compose.yaml config
docker compose -p mongodb-ch26 -f compose.yaml ps
docker volume ls --filter label=com.docker.compose.project=mongodb-ch26
docker run --rm -it --network mongodb-ch26_replica mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=5000"
```

Use the same approved image digest as all members. The independent client remains available when the selected service is recreated. No ports are published. Keep a host terminal open.

The operator needs Docker control and status/configuration inspection plus scoped database access. Authenticated deployments require approved TLS and member/client authentication; this isolated Chapter 26 lab has neither. No credentials or role grants are included.

Initial sync copies other retained lab databases too. Inventory their sizes before creating replacement storage and reserve capacity for both original and replacement copies, indexes and temporary replication work. Record host memory/CPU pressure and filesystem free space; stop if the budget cannot support the extra copy.

```bash
docker compose -p mongodb-ch26 -f compose.yaml exec a df -h /data/db
docker compose -p mongodb-ch26 -f compose.yaml exec b df -h /data/db
docker compose -p mongodb-ch26 -f compose.yaml exec c df -h /data/db
docker stats --no-stream
```

Use `db.adminCommand({listDatabases: 1})` in the primary-aware client for the size inventory. In this one-host lab the disk checks share a filesystem; do not count free capacity three times. Pin the recorded member image digest in the base definition before recreation if it still uses a movable tag, and verify the resolved Compose image matches the running image.

## 4. Readiness and identity guards

In the independent mongosh client:

```javascript
const hosts30 = ["a:27017", "b:27017", "c:27017"];
const name30 = "mongodb_enterprise_tutorial_ch30";
const lab30 = db.getSiblingDB(name30);
const wc30 = { w: "majority", j: true, wtimeout: 10000 };
function check30(condition, message) {
  if (!condition) throw new Error(message);
}
function direct30(host) {
  check30(hosts30.includes(host), "Host outside owned lab");
  const conn = new Mongo("mongodb://" + host +
    "/?directConnection=true&serverSelectionTimeoutMS=5000");
  conn.setReadPref("secondaryPreferred");
  return conn;
}
function status30() { return db.adminCommand({ replSetGetStatus: 1 }); }
function healthy30(s) {
  return s && s.ok === 1 && s.set === "rs26" && s.members.length === 3 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "PRIMARY").length === 1 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "SECONDARY").length === 2;
}
function waitHealthy30(timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try { last = status30(); if (healthy30(last)) return last; }
    catch (error) { print(error.message); }
    sleep(1000);
  }
  printjson(last);
  throw new Error("Full readiness not observed within lab budget");
}
function configContract30(cfg) {
  return JSON.stringify({ set: cfg._id, members: cfg.members.map(m => ({
    id: Number(m._id), host: m.host,
    votes: Number(m.votes === undefined ? 1 : m.votes),
    priority: Number(m.priority === undefined ? 1 : m.priority),
    hidden: m.hidden === true, arbiter: m.arbiterOnly === true,
    delay: Number(m.secondaryDelaySecs || 0)
  })).sort((a, b) => a.id - b.id) });
}
const cfg30 = db.adminCommand({ replSetGetConfig: 1 }).config;
check30(cfg30._id === "rs26" && cfg30.members.length === 3 &&
  cfg30.members.every(m => hosts30.includes(m.host) && !m.hidden && !m.arbiterOnly &&
    Number(m.votes === undefined ? 1 : m.votes) === 1 &&
    Number(m.priority === undefined ? 1 : m.priority) > 0 &&
    Number(m.secondaryDelaySecs || 0) === 0), "Unexpected topology");
check30(lab30.getCollectionNames().length === 0,
        "Chapter database exists; review before rerunning");
const originalContract30 = configContract30(cfg30);
const start30 = waitHealthy30();
const target30 = start30.members.find(m => m.stateStr === "SECONDARY").name;
const service30 = target30.split(":")[0];
const targetId30 = cfg30.members.find(m => m.host === target30)._id;
printjson({ version: db.version(), target: target30, memberId: targetId30,
            initialMembers: start30.members.map(m => ({ host: m.name, role: m.stateStr })) });
```

Record exact tool versions, image digest, config and volume names. The target is selected by current role; do not assume `b` is secondary. Recheck immediately before every stop.

## 5. Synthetic fixture, index and validator

The bounded dataset is approximately 5 MiB of payload plus BSON/index overhead. It is large enough to check clone correctness without trying to prolong initial sync through artificial delays.

```javascript
const validator30 = { $jsonSchema: {
  bsonType: "object", required: ["_id", "seq", "revision", "payload"],
  properties: { _id: { bsonType: "string" }, seq: { bsonType: "int" },
    revision: { bsonType: "int" }, payload: { bsonType: "string" } }
} };
check30(lab30.createCollection("events", { validator: validator30,
  validationLevel: "strict", validationAction: "error" }).ok === 1,
  "Collection creation failed");
const events30 = lab30.events;
events30.createIndex({ seq: 1 }, { name: "seq_unique", unique: true });
for (let batch = 0; batch < 50; batch++) {
  const docs = Array.from({ length: 100 }, (_, j) => {
    const n = batch * 100 + j;
    return { _id: "row-" + String(n).padStart(5, "0"),
      seq: Int32(n), revision: Int32(0), payload: "x".repeat(1024) };
  });
  check30(events30.insertMany(docs, { writeConcern: wc30 }).acknowledged,
          "Fixture batch not acknowledged");
}
let updated30 = false;
function validRows30(rows) {
  if (rows.length !== 5000) return false;
  return rows.every((r, i) => r._id === "row-" + String(i).padStart(5, "0") &&
    Number(r.seq) === i && Number(r.revision) === (updated30 && i < 100 ? 1 : 0) &&
    r.payload === "x".repeat(1024));
}
function verifyHost30(host, timeoutMs = 90000) {
  const conn = direct30(host);
  const d = conn.getDB(name30);
  const deadline = Date.now() + timeoutMs;
  let rows = [];
  while (Date.now() < deadline) {
    rows = d.events.find().sort({ seq: 1 }).toArray();
    if (validRows30(rows)) break;
    sleep(500);
  }
  check30(validRows30(rows), "Fixture differs on " + host);
  const ix = d.events.getIndexes().find(i => i.name === "seq_unique");
  check30(ix && ix.unique === true && Number(ix.key.seq) === 1,
          "Unique index missing on " + host);
  const info = d.getCollectionInfos({ name: "events" })[0];
  check30(info && info.options.validationLevel === "strict" &&
    info.options.validationAction === "error" &&
    JSON.stringify(info.options.validator) === JSON.stringify(validator30),
    "Validator differs on " + host);
  return { host, count: rows.length, index: ix.name, validator: "matched" };
}
function verifyAll30() { printjson(hosts30.map(h => verifyHost30(h))); }
verifyAll30();
```

Expected: 5000 exact IDs, payloads, sequences and revision=0 on each member; unique index and validator match. Int32 values satisfy the BSON schema explicitly. If a batch errors, reconcile IDs and recover before proceeding; do not blindly repeat inserts.

## 6. Prepare a separate storage override

This avoids deleting or emptying the original data directory. The replacement process uses fresh, separately named volumes at the same `/data/db` and `/data/configdb` mount targets.

Generate the complete override text in mongosh:

```javascript
const replacementData30 = "mongodb-ch26-ch30-" + service30 + "-data";
const replacementConfig30 = "mongodb-ch26-ch30-" + service30 + "-config";
print([
  "services:", "  " + service30 + ":", "    volumes:",
  "      - ch30-data:/data/db", "      - ch30-config:/data/configdb",
  "volumes:", "  ch30-data:", "    name: " + replacementData30,
  "  ch30-config:", "    name: " + replacementConfig30
].join("\n"));
print("CHECK: docker volume inspect " + replacementData30 + " " + replacementConfig30);
print("INSPECT ORIGINAL: docker inspect mongodb-ch26-" + service30 + "-1");
```

Save only the generated YAML as `compose.ch30.yaml` beside `compose.yaml`. The volume inspection must report that **both replacement volumes do not exist**. Existing names mean a previous attempt or unexpected ownership: stop and investigate; do not reuse them as an empty-sync demonstration.

Container names assume Chapter 26's default Compose naming. Use `docker compose ps -a` to obtain the actual target name if it differs. Inspect its mounts and record the original two volume names and image ID before recreation.

```bash
docker compose -p mongodb-ch26 -f compose.yaml -f compose.ch30.yaml config
```

Inspect the rendered configuration: only the target's two mount sources differ; mount destinations, command, image, network and other services remain correct. Compose merges volumes by container target path. If the rendered result differs from this contract, stop before mutation.

## 7. Stop one secondary and start its replacement

```javascript
function restartGate30() {
  const s = waitHealthy30();
  const m = s.members.find(x => x.name === target30);
  check30(m && m.health === 1 && m.stateStr === "SECONDARY",
          "Target is not a healthy secondary");
  check30(direct30(target30).getDB("admin").runCommand({ hello: 1 }).secondary === true,
          "Direct role check failed");
  check30(configContract30(db.adminCommand({ replSetGetConfig: 1 }).config) ===
          originalContract30, "Member configuration changed");
  verifyAll30();
}
restartGate30();
print("STOP: docker compose -p mongodb-ch26 -f compose.yaml stop --timeout 60 " + service30);
print("REPLACE: docker compose -p mongodb-ch26 -f compose.yaml -f compose.ch30.yaml up -d --no-deps --force-recreate " + service30);
```

Run the generated STOP then REPLACE commands in the host terminal. Inspect clean shutdown logs; forced timeout termination is a separate outcome. Do not run `down`, `down --volumes`, `rs.initiate`, `rs.remove`, or `rs.add` for this same-identity exercise.

The selected service gets a new container and new empty storage. The old named volumes remain detached. Confirm the replacement's two mounts and unchanged image ID with `docker inspect` using the same target container name. Do not start a second container attached to the original target volumes.

## 8. Observe initial sync and maintain bounded writes

Immediately after replacement, capture direct target status. Status may initially return an initialization error; record it without treating it as proof of permanent failure.

```javascript
const syncObservedStart30 = Date.now();
function observeTarget30() {
  try {
    const s = direct30(target30).getDB("admin").runCommand({
      replSetGetStatus: 1, initialSync: 1
    });
    printjson({ ok: s.ok, code: s.code, message: s.errmsg,
      state: s.myState, syncSource: s.syncSourceHost,
      initialSyncStatus: s.initialSyncStatus,
      applied: s.optimes?.appliedOpTime });
    return s;
  } catch (error) { printjson({ observationError: error.message }); return null; }
}
observeTarget30();
const mutation30 = events30.updateMany({ seq: { $lt: Int32(100) }, revision: Int32(0) },
  { $set: { revision: Int32(1) } }, { writeConcern: wc30 });
check30(mutation30.matchedCount === 100 && mutation30.modifiedCount === 100,
        "Mutation outcome differs; reconcile before continuing");
updated30 = true;
observeTarget30();
```

These writes occur after replacement launch. A small dataset may finish initial sync before them; do not claim concurrent clone/apply coverage unless timestamps/logs prove overlap. No artificial failpoints or large uncontrolled workload are used to slow synchronization.

Get bounded target logs using the generated command:

```javascript
print("LOGS: docker compose -p mongodb-ch26 -f compose.yaml -f compose.ch30.yaml logs --tail 200 " + service30);
```

Look for initial sync attempts/source selection, clone/index activity, completion or failure. A fast sync can finish between status polls; logs and empty mount provenance are needed to support the initial-sync claim. Do not require `initialSyncStatus` fields to remain present after completion.

## 9. Verify readiness, application state and metadata

```javascript
const afterSync30 = waitHealthy30(180000);
verifyAll30();
const targetStatus30 = direct30(target30).getDB("admin")
  .runCommand({ replSetGetStatus: 1 });
check30(targetStatus30.ok === 1 && targetStatus30.myState === 2,
        "Replacement is not a secondary; reassess before further maintenance");
check30(configContract30(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalContract30, "Replica-set membership contract changed");
check30(afterSync30.members.find(m => m.name === target30)._id === targetId30,
        "Target member ID changed");
printjson({ observationElapsedMs: Date.now() - syncObservedStart30,
  target: target30, state: targetStatus30.myState,
  syncSource: targetStatus30.syncSourceHost, count: 5000, revisedRows: 100 });
```

Expected: full readiness, target secondary, all rows match, first 100 rows revision=1, remaining 4900 revision=0, cloned index/validator intact and same membership contract. A config/role mismatch stops acceptance even if counts match.

This checks the exact synthetic collection and its selected metadata. It does not reconcile every database, user, index option or production object. Observation elapsed includes operator delays and fixture verification; it is not measured clone duration or application outage.

## 10. Failure exercise: reject premature completion

Use synthetic observations to exercise the acceptance decision without disrupting a second member:

```javascript
function replacementAccepted30(e) {
  return e.healthyTopology === true && e.targetState === "SECONDARY" &&
    e.fixtureMatches === true && e.indexMatches === true &&
    e.validatorMatches === true && e.mountsVerified === true;
}
const goodEvidence30 = { healthyTopology: true, targetState: "SECONDARY",
  fixtureMatches: true, indexMatches: true, validatorMatches: true, mountsVerified: true };
check30(!replacementAccepted30({ ...goodEvidence30, targetState: "STARTUP2" }),
        "Syncing member incorrectly accepted");
check30(!replacementAccepted30({ ...goodEvidence30, fixtureMatches: false }),
        "Partial dataset incorrectly accepted");
check30(!replacementAccepted30({ ...goodEvidence30, indexMatches: false }),
        "Missing index incorrectly accepted");
check30(replacementAccepted30(goodEvidence30), "Complete evidence rejected");
printjson({ classifier: "passed", runtimeEvidence: "record separately" });
```

Trigger: process/partial data is mistaken for completion. Diagnosis: one or more acceptance requirements are missing. Correction: wait for readiness, reconcile exact state/metadata and verify mounts before proceeding. This tests decision logic, not a real failed initial-sync attempt.

## 11. Recovery if replacement fails

Keep both survivors running. Capture replacement logs, source health/history and target mounts/resources. Do not repeatedly erase replacement storage or restart all three members. An observation timeout is a reason to inspect progress, not a requirement to terminate ongoing useful work.

For a failed replacement, recover through the preserved original storage when its history is still usable. First inspect survivor status and confirm a writable primary and a healthy surviving secondary. If survivors are unhealthy or no primary exists, stop this routine recovery sequence and assess the incident; do not force reconfiguration.

The restoration commands are generated in Section 14. Before stopping a running target, ensure it is not primary. If it became primary, perform Chapter 28's non-forced stepdown and recheck its secondary role. If it is unreachable, inspect Docker state and confirm which process/storage will be stopped.

The original volume is a retained member copy, not an independent backup. It missed the revision updates and must catch up. If history no longer overlaps, restoring it can still require initial sync; preserve it for investigation and plan a supported recovery rather than promising instant rollback.

If normal Section 14 readiness cannot pass because the replacement failed, run this command generator only after the survivor and target-role checks described above. It does not bypass those operational checks:

```javascript
print("RECOVERY STOP: docker compose -p mongodb-ch26 -f compose.yaml -f compose.ch30.yaml stop --timeout 60 " + service30);
print("RECOVERY RESTORE: docker compose -p mongodb-ch26 -f compose.yaml up -d --no-deps --force-recreate " + service30);
```

After those commands, verify original mounts, full topology and reconciled fixture state. If a mutation returned an uncertain error, query all deterministic IDs and revisions before adjusting `updated30`; retain partial results rather than blindly repeating the update. Do not run ordinary cleanup until that uncertainty is resolved.

## 12. Production member replacement planning

A real change includes current-source validation, tested backups, exact build/FCV compatibility, routable advertised DNS, TLS names, member authentication, storage ownership, disk/memory/CPU budgets, source load, replication history and application stop conditions.

Same-address empty-storage replacement preserves the member identity. A changed hostname requires a reviewed configuration update on the current primary. Locate the member by `_id`, update its `host` in freshly fetched configuration and follow supported non-forced reconfiguration rules. Never infer array position from member ID. Observe the actual topology after any ambiguous command result.

An add-new/remove-old migration has different voting and capacity implications. Do not add a voter casually, change several voting members at once or apply `force:true` to routine replacement. Automation-managed sets require changes through the owning operator/Ops Manager workflow so reconciliation does not undo manual edits.

Restore from snapshots or seed data only through a supported consistency procedure. Copying live files or treating a logical dump as a storage-engine directory is not the lab's recovery path. Whole-set loss and application-level recovery are covered later in the backup/DR chapters.

## 13. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Process pings but stays STARTUP2 | Direct status and initial-sync logs | Clone/apply work still active | Observe progress and source/target resources |
| No initial-sync metrics captured | Poll timings, target logs, mount provenance | Small sync completed between polls | Record log evidence; do not invent phases |
| Replacement shows old data immediately | Docker mount sources and volume history | Wrong/reused volume | Stop acceptance and inspect provenance |
| Source selection repeatedly fails | DNS, authentication, source status/logs | Source unreachable or unsuitable | Correct access/source readiness |
| Initial sync retries or fails | Attempt logs, window and resources | History gaps, network/disk failure | Resolve cause before restarting the procedure |
| Majority writes fail during sync | Survivor health and concern errors | Surviving acknowledgement path failed | Stop workload and recover quorum safely |
| Rows match but query performance differs | Index definitions and source metadata | Missing/different indexes | Reconcile metadata before completion |
| Validator differs after sync | Collection options and server build | Wrong source/namespace or incompatible procedure | Diagnose contract mismatch |
| Target becomes primary | Direct hello/status | Election occurred during exercise | Reassess; step down non-forced before planned stop |
| Restored original cannot catch up | Last-known optime, current source history/logs | Retained copy is too old | Assess supported resync; preserve evidence |

## 14. Restore original storage and clean up

The normal completion path restores the original two volumes while keeping the chapter fixture available for catch-up verification. Do this promptly within the retained-history budget. Use Section 11 if the replacement never became healthy.

```javascript
restartGate30();
print("STOP REPLACEMENT: docker compose -p mongodb-ch26 -f compose.yaml -f compose.ch30.yaml stop --timeout 60 " + service30);
print("RESTORE ORIGINAL: docker compose -p mongodb-ch26 -f compose.yaml up -d --no-deps --force-recreate " + service30);
```

Run the two generated commands in that order. The restore command intentionally uses **only the base file**. Inspect the target's mounts and match the original two volume names recorded in Section 6. Verify the image ID is still the approved one.

```javascript
waitHealthy30(180000);
verifyAll30();
check30(configContract30(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalContract30, "Final member contract differs");
check30(lab30.getName() === "mongodb_enterprise_tutorial_ch30",
        "Refusing cleanup outside the Chapter 30 training database");
check30(lab30.dropDatabase().ok === 1, "Chapter database cleanup failed");
for (const host of hosts30) {
  const d = direct30(host).getDB(name30);
  const end = Date.now() + 30000;
  while (Date.now() < end && d.getCollectionNames().length !== 0) sleep(500);
  check30(d.getCollectionNames().length === 0, "Cleanup not applied on " + host);
}
waitHealthy30();
print("INSPECT UNUSED: docker volume inspect " + replacementData30 + " " + replacementConfig30);
print("CHECK ATTACHMENTS: docker ps -a --filter volume=" + replacementData30);
print("CHECK ATTACHMENTS: docker ps -a --filter volume=" + replacementConfig30);
print("DELETE ONLY DETACHED REPLACEMENT: docker volume rm " + replacementData30 + " " + replacementConfig30);
```

Inspect volume names/ownership and ensure neither is attached to any container before running the generated deletion. These two volumes contain a cloned copy of other retained lab databases as well as this chapter's fixture; delete them only after original-storage restoration and convergence are verified. Never remove `mongodb-ch26_a-data`, `b-data`, `c-data` or their original config volumes here.

Remove `compose.ch30.yaml` only after successful restoration and detached-volume cleanup. Keep `compose.yaml` and the original six volumes for Chapter 31. If normal recovery failed, preserve the override, volumes and logs until resolved.

## 15. Acceptance and evidence

- [ ] Recorded versions, image ID/digest, project ownership and original mounts.
- [ ] Verified full readiness, exact member ID/host and fresh chapter namespace.
- [ ] Reconciled 5000 baseline documents plus index and validator on all members.
- [ ] Rendered a one-service override and proved both replacement volumes were absent.
- [ ] Rechecked the secondary role immediately before stopping only that service.
- [ ] Verified fresh replacement mounts and captured initial-sync log/status evidence.
- [ ] Reconciled the bounded 100-row revision update on every member.
- [ ] Verified complete topology, unchanged identity, document payloads and metadata.
- [ ] Tested premature-completion rejection without a second-member outage.
- [ ] Restored original mounts, verified catch-up and cleaned only named owned resources.

**Evidence:** config, mount provenance, versions/image, fixture assertions, generated commands, shutdown/sync logs, source/target observations, mutation results, metadata verification and restoration/cleanup. Runtime validation remains pending until executed. Static JavaScript parsing does not test MongoDB behavior. One-host success does not establish production HA or an initial-sync SLA.

## 16. Review questions

1. What distinguishes initial sync from ordinary retained-history catch-up?
2. Why does a process healthcheck not prove a member is ready?
3. Why retain the original volumes separately during this rehearsal?
4. Which evidence demonstrates initial sync if STARTUP2 was missed between polls?
5. Why must a replacement verify indexes and validators as well as counts?
6. Why can restoring the original volume require another initial sync?
7. What changes when the replacement hostname differs from the original?
8. Why is a replica-set member copy insufficient for accidental-delete recovery?

## 17. Official references

- [MongoDB 8.0: resync a member](https://www.mongodb.com/docs/v8.0/tutorial/resync-replica-set-member/)
- [MongoDB 8.0: replica-set data synchronization](https://www.mongodb.com/docs/v8.0/core/replica-set-sync/)
- [MongoDB 8.0: replace a replica-set member](https://www.mongodb.com/docs/v8.0/tutorial/replace-replica-set-member/)
- [MongoDB 8.0: replSetGetStatus](https://www.mongodb.com/docs/v8.0/reference/command/replSetGetStatus/)
- [MongoDB 8.0: rs.reconfig](https://www.mongodb.com/docs/v8.0/reference/method/rs.reconfig/)
- [Docker Compose: merge Compose files](https://docs.docker.com/reference/compose-file/merge/)
- [Docker Compose: up](https://docs.docker.com/reference/cli/docker/compose/up/)

---

Previous: [Chapter 29 — Replication Lag and Oplog Sizing](29-replication-lag-and-oplog-sizing.md)  
Next: [Chapter 31 — Network Partitions Rollback and Consistency](31-network-partitions-rollback-and-consistency.md).
