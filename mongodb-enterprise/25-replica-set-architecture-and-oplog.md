# 25 — Replica Set Architecture and Oplog

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Inventory replica-set roles and configuration, trace ordinary writes into the oplog, measure a member's retained history window and distinguish replication evidence from HA acceptance.  
**Audience:** DBREs, SREs, Developers and Platform Engineers  
**Time:** 75–105 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Self-managed Community or Enterprise training replica set. A one-member replica set supports the core inspection lab but does not demonstrate redundancy.

## 1. A replica set has several different majorities

A replica set is a group of mongod members with shared replication configuration. The primary accepts ordinary application writes. Data-bearing secondaries copy and apply replicated operations. Eligible members can participate in elections when primary availability changes.

Keep these questions separate:

- Which members vote in an election?
- Which members are eligible to become primary?
- Which members store and acknowledge replicated data?
- Which members can serve the application's chosen reads?

A vote is not a copy of data. An arbiter can vote but does not store application data. A priority-zero member cannot become primary; it may still store data and may vote according to its configuration.

A common starting topology has three data-bearing members distributed across appropriate failure domains. Three processes on one host help teach protocol behavior but share that host's failure risk.

## 2. Roles and configuration flags

| Role/property | Data copy | Election implications | Operational boundary |
|---|---|---|---|
| Primary | Yes | Current elected write leader | Applications need discovery after role changes |
| Secondary | Yes | Eligible if its configuration/state permits | Reads may lag according to policy |
| Arbiter | No | Votes, cannot become primary | Does not provide a third data copy |
| priority: 0 | Yes for data-bearing member | Ineligible for primary | Does not automatically mean non-voting |
| hidden: true | Yes | Hidden members require priority zero | Ordinary client discovery does not expose it as a normal read target |
| votes: 0 | Depends on member role | Does not contribute an election vote | Not part of the voting majority calculation |
| Delayed secondary | Yes, intentionally delayed application | Must be designed carefully for voting/visibility | Not a replacement for backup/recovery |

This chapter reads these settings; it does not add, remove, hide or delay members. Topology setup follows in Chapter 26. Elections and maintenance follow in Chapter 28.

Do not use an arbiter merely to reduce cost without analyzing data acknowledgement and failure behavior. A primary-secondary-arbiter topology has different write availability constraints than three data-bearing members.

## 3. Oplog: a bounded replication history

A data-bearing replica-set member has a local.oplog.rs collection containing replication operations. Members use operation history to catch up, potentially from eligible sync sources according to topology and configuration.

The local database contains member-local state. Reading one member's oplog is not reading a replicated collection with identical retention on every member.

Oplog entries are not an immutable application audit log. History is finite, payloads are replication-oriented, and entry formats can evolve. Transactions and some commands can use applyOps or other command-shaped representations. One business request is not universally one simple oplog record.

The oplog can exceed its configured size to protect the majority commit point. A configured capacity is therefore not an absolute filesystem usage ceiling. Minimum-retention settings and write volume also affect actual storage/time coverage.

An application needing CDC should use supported change-stream/connector contracts and resume-token handling, not a custom parser coupled to raw oplog update formats. Change streams follow in Chapter 64.

## 4. Majority acknowledgement is not every member being current

A majority write concern asks for acknowledgement from the required majority of voting data-bearing members under the deployment's durability settings. It is different from “all secondaries applied this write.”

The majority commit point records committed replication progress. Member applied/durable positions and the commit point describe different boundaries. A status snapshot can lag a just-completed operation and is not an application read contract.

This lab specifies majority write concern explicitly. On a single-member set, majority is one data-bearing voter. That teaches command/oplog behavior but does not validate redundancy or failover.

Timeouts can leave an uncertain acknowledgement outcome. Do not blindly repeat business writes because a write-concern timeout appeared. Preserve operation identity and reconcile state; Chapter 16 explains that distinction.

## 5. Prerequisites and connection context

Complete Chapters 06, 16 and 24. Use an existing authorized disposable replica set, including the Chapter 16 one-member lab if retained. Do not run rs.initiate or reconfigure a shared deployment for this chapter.

Connect using an approved replica-set URI with discoverable member addresses and credentials. Record the replicaSet name and read preference. The main write lab uses the primary.

The operator needs:

- Read/write, collection creation and cleanup access on the named chapter database.
- Authorized replica-set status/configuration inspection.
- Read-only access to local.oplog.rs on the connected data-bearing member and its collection statistics.

Monitoring roles may supply status/configuration privileges without raw oplog read access. Verify the actual custom role. Raw oplog access can expose other namespaces' data; restrict the queries and operator scope. This chapter does not grant privileges.

Atlas and managed deployments can restrict direct member/local access. If raw inspection is unsupported, record that branch as unavailable and use the service's supported monitoring; do not claim the core oplog assertions ran.

In mongosh:

```javascript
const labName25 = "mongodb_enterprise_tutorial_ch25";
const lab25 = db.getSiblingDB(labName25);
const hello25 = db.adminCommand({ hello: 1 });
if (!hello25.setName || hello25.msg === "isdbgrid") {
  throw new Error("Connect to a data-bearing replica-set mongod");
}
if (!hello25.isWritablePrimary) {
  throw new Error("Core mutation lab requires the primary");
}
if (lab25.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
function check25(condition, message) {
  if (!condition) throw new Error(message);
}
printjson({
  serverVersion: db.version(),
  setName: hello25.setName,
  me: hello25.me,
  primary: hello25.primary,
  hosts: hello25.hosts,
  writablePrimary: hello25.isWritablePrimary
});
```

Record mongosh --version separately. Hello's discovery host list is not a complete substitute for configuration inspection; hidden and special members can have different visibility.

## 6. Inspect topology without changing it

```javascript
const configResult25 = db.adminCommand({ replSetGetConfig: 1 });
check25(configResult25.ok === 1, "Configuration inspection failed");
const config25 = configResult25.config;
const statusResult25 = db.adminCommand({ replSetGetStatus: 1 });
check25(statusResult25.ok === 1, "Status inspection failed");
check25(config25._id === hello25.setName &&
        statusResult25.set === hello25.setName, "Replica-set identity mismatch");
printjson({
  configurationVersion: config25.version,
  members: config25.members.map(member => ({
    id: member._id,
    host: member.host,
    votes: member.votes === undefined ? 1 : member.votes,
    priority: member.priority === undefined ? 1 : member.priority,
    hidden: member.hidden === true,
    arbiterOnly: member.arbiterOnly === true,
    secondaryDelaySecs: member.secondaryDelaySecs || 0
  }))
});
printjson({
  members: statusResult25.members.map(member => ({
    id: member._id, name: member.name, health: member.health,
    state: member.stateStr, self: member.self === true,
    optime: member.optime, optimeDate: member.optimeDate,
    syncSourceHost: member.syncSourceHost || null
  })),
  optimes: statusResult25.optimes
});
```

Do not treat configuration as current health. A configured member can be unreachable or in a transition state. Similarly, one primary's status view is not identical to all members' observations.

Classify configured voters:

```javascript
function voteInventory25(members) {
  const voters = members.filter(m =>
    (m.votes === undefined ? 1 : Number(m.votes)) === 1);
  const dataVoters = voters.filter(m => m.arbiterOnly !== true);
  return {
    configuredMembers: members.length,
    votingMembers: voters.length,
    votingDataMembers: dataVoters.length,
    electionMajority: Math.floor(voters.length / 2) + 1
  };
}
const voteSummary25 = voteInventory25(config25.members);
printjson(voteSummary25);
if (voteSummary25.votingDataMembers < 3) {
  print("Teaching observation: this topology is not three voting data copies.");
}
```

This inventory is a static configuration calculation. It does not calculate effective write availability for every failure combination, tag-based concern or transition state.

## 7. Measure retained history on this member

```javascript
const local25 = db.getSiblingDB("local");
const oplog25 = local25.getCollection("oplog.rs");
const oldest25 = oplog25.find({}, { ts: 1, wall: 1 })
  .sort({ $natural: 1 }).limit(1).toArray()[0];
const newest25 = oplog25.find({}, { ts: 1, wall: 1 })
  .sort({ $natural: -1 }).limit(1).toArray()[0];
check25(oldest25 && newest25, "Oplog has no inspectable history");
function timestampSeconds25(ts) {
  check25(ts && typeof ts.getHighBits === "function",
          "Expected BSON Timestamp; inspect shell/BSON compatibility");
  return ts.getHighBits() >>> 0;
}
const retainedSeconds25 =
  timestampSeconds25(newest25.ts) - timestampSeconds25(oldest25.ts);
check25(retainedSeconds25 >= 0, "Negative history window; inspect samples");
const oplogStats25 = local25.runCommand({ collStats: "oplog.rs", scale: 1 });
check25(oplogStats25.ok === 1, "Oplog statistics unavailable");
printjson({
  oldestTimestamp: oldest25.ts, oldestWall: oldest25.wall || null,
  newestTimestamp: newest25.ts, newestWall: newest25.wall || null,
  retainedWindowSeconds: retainedSeconds25,
  logicalBytes: oplogStats25.size,
  allocatedDocumentBytes: oplogStats25.storageSize,
  configuredCappedBytes: oplogStats25.maxSize,
  count: oplogStats25.count
});
```

BSON Timestamp contains seconds and an increment; it is not interchangeable with a BSON Date. This approximate window uses seconds only. Wall timestamps can aid human correlation but do not replace operation ordering.

The samples are taken sequentially, not atomically. Busy history rollover or topology changes require careful interpretation. A new or quiet replica set can have a very short history window despite a large configured oplog.

The measured window is past retained coverage under actual writes. It is not a guarantee of future coverage. Chapter 29 develops lag and oplog sizing under peak write volume.

## 8. Create fixture and anchor the observation

Create the collection before capturing an oplog anchor, so collection creation is not part of the ordinary insert/update/delete assertions.

```javascript
lab25.createCollection("events");
const events25 = lab25.events;
const runId25 = "ch25-" + new ObjectId().toHexString();
const ids25 = [runId25 + "-0", runId25 + "-1", runId25 + "-2"];
const namespace25 = labName25 + ".events";
const anchorEntry25 = oplog25.find({}, { ts: 1 })
  .sort({ $natural: -1 }).limit(1).toArray()[0];
check25(anchorEntry25, "Could not capture oplog anchor");
const anchorTimestamp25 = anchorEntry25.ts;
printjson({ runId: runId25, namespace: namespace25,
            anchorTimestamp: anchorTimestamp25 });
```

Use a stable run ID to correlate application state and replication evidence. Do not include sensitive user identifiers in diagnostic markers. The anchor bounds this exercise; it is not a resume token for a production CDC consumer.

## 9. Trace ordinary mutations

Use three separate single-document inserts, one update and one delete. These operations intentionally exclude transactions and bulk command interpretation.

```javascript
const writeConcern25 = { w: "majority", j: true, wtimeout: 10000 };
for (let i = 0; i < ids25.length; i++) {
  const inserted = events25.insertOne({
    _id: ids25[i], runId: runId25, seq: i, revision: 0,
    payload: "Synthetic replication event"
  }, { writeConcern: writeConcern25 });
  check25(inserted.acknowledged, "Insert not acknowledged");
}
const changed25 = events25.updateOne(
  { _id: ids25[0], revision: 0 },
  { $set: { revision: 1 } },
  { writeConcern: writeConcern25 }
);
check25(changed25.modifiedCount === 1, "Update did not modify expected fixture");
const deleted25 = events25.deleteOne(
  { _id: ids25[2] }, { writeConcern: writeConcern25 }
);
check25(deleted25.deletedCount === 1, "Delete did not remove expected fixture");
const state25 = events25.find({ runId: runId25 }).sort({ seq: 1 }).toArray();
check25(state25.length === 2, "Wrong final document count");
check25(state25[0]._id === ids25[0] && Number(state25[0].revision) === 1,
        "Updated state mismatch");
check25(state25[1]._id === ids25[1] && Number(state25[1].revision) === 0,
        "Untouched state mismatch");
printjson(state25);
```

The acknowledgement options are deliberate teaching settings. A concern error or timeout should stop the exercise and trigger reconciliation; it does not prove the write was absent. Do not rerun the insert loop blindly after an uncertain result.

## 10. Read bounded oplog evidence and verify identity

```javascript
const entries25 = oplog25.find({
  ns: namespace25, ts: { $gt: anchorTimestamp25 }
}).sort({ $natural: 1 }).limit(100).toArray();
printjson(entries25.map(entry => ({
  ts: entry.ts, wall: entry.wall, operation: entry.op,
  namespace: entry.ns, object: entry.o, selector: entry.o2
})));
for (const id of ids25) {
  check25(entries25.some(e => e.op === "i" && e.o && e.o._id === id),
          "Missing insert oplog evidence for " + id);
}
check25(entries25.some(e => e.op === "u" && e.o2 && e.o2._id === ids25[0]),
        "Missing update oplog selector");
check25(entries25.some(e => e.op === "d" && e.o && e.o._id === ids25[2]),
        "Missing delete oplog selector");
```

For these ordinary nontransactional fixture writes, expect insert, update and delete entries. The update object can be a versioned diff rather than the original $set command. Verify operation and identity without assuming a fixed update payload schema.

The limit protects this diagnostic read. If evidence is missing, inspect version, operation form, member, namespace, anchor and rollover before drawing a conclusion. Transactional applyOps entries can use a command namespace and require different interpretation; they are outside these assertions.

Do not write, delete, resize or repair local.oplog.rs manually. Raw oplog inspection is read-only here.

## 11. Failure exercise: namespace typo hides evidence

```javascript
const wrongNamespace25 = labName25 + ".event_typo";
const wrongEvidence25 = oplog25.find({
  ns: wrongNamespace25, ts: { $gt: anchorTimestamp25 }
}).limit(1).toArray();
check25(wrongEvidence25.length === 0, "Unexpected typo-namespace evidence");
const correctEvidence25 = oplog25.find({
  ns: namespace25, ts: { $gt: anchorTimestamp25 }, op: "i",
  "o._id": ids25[0]
}).limit(1).toArray();
check25(correctEvidence25.length === 1,
        "Corrected namespace still lacks known insert evidence");
```

Diagnosis: the query searched a namespace that was never written. An empty result is not proof of replication failure. Correct the correlation and verify the known operation.

For real missing history, consider member/local scope, recent rollover, BSON timestamp bounds, transaction representation and authorization. Do not replace an evidence gap with a manual oplog mutation.

## 12. Optional secondary application-state check

On an existing authorized multi-member training set, open a separate mongosh connection to a known data-bearing secondary using its reachable address, TLS/auth options and directConnection=true. Do not guess host addresses or expose credentials.

Use a separate connection so changing its read preference cannot affect the primary lab shell. Substitute the printed run ID and IDs:

```javascript
// Optional: execute in a NEW shell connected directly to the approved secondary.
const secondaryHello25 = db.adminCommand({ hello: 1 });
if (!secondaryHello25.secondary || !secondaryHello25.setName) {
  throw new Error("Optional branch requires a data-bearing secondary");
}
db.getMongo().setReadPref("secondary");
const secondaryLab25 = db.getSiblingDB("mongodb_enterprise_tutorial_ch25");
const expectedRun25 = "<paste-the-primary-runId>";
if (expectedRun25.startsWith("<")) throw new Error("Set the actual lab run ID");
const secondaryDeadline25 = Date.now() + 30000;
let secondaryRows25 = [];
while (Date.now() < secondaryDeadline25) {
  secondaryRows25 = secondaryLab25.events.find({
    runId: expectedRun25
  }).sort({ seq: 1 }).toArray();
  if (secondaryRows25.length === 2 &&
      Number(secondaryRows25[0].seq) === 0 &&
      Number(secondaryRows25[0].revision) === 1 &&
      Number(secondaryRows25[1].seq) === 1 &&
      Number(secondaryRows25[1].revision) === 0) break;
  sleep(500);
}
if (secondaryRows25.length !== 2 ||
    Number(secondaryRows25[0].seq) !== 0 ||
    Number(secondaryRows25[0].revision) !== 1 ||
    Number(secondaryRows25[1].seq) !== 1 ||
    Number(secondaryRows25[1].revision) !== 0) {
  throw new Error("Secondary fixture did not converge within observation budget");
}
printjson(secondaryRows25);
```

This demonstrates eventual fixture convergence on that secondary. It does not prove a complete lag distribution, read-your-writes policy or failover acceptance. The 30-second budget is a lab observation, not a replication SLA.

If using a one-member set, record the optional branch as not applicable. Do not label it passed. Close the secondary shell afterward.

## 13. Interpret commit and member progress

Back on the primary shell:

```javascript
const afterStatus25 = db.adminCommand({ replSetGetStatus: 1 });
check25(afterStatus25.ok === 1, "Post-write status unavailable");
printjson({
  optimes: afterStatus25.optimes,
  members: afterStatus25.members.map(member => ({
    name: member.name, state: member.stateStr,
    optime: member.optime, optimeDate: member.optimeDate,
    health: member.health
  }))
});
```

Inspect lastCommittedOpTime and available applied/durable fields. Do not compare timestamps by string sorting or assume every member's sampled position equals the newest primary entry.

A member's state SECONDARY and health 1 are not proof that it is current enough for every application. Read preference and read/write concerns define additional behavior; Chapter 27 develops those contracts.

## 14. Synthetic vote exercise: three voters are not three copies

```javascript
const threeData25 = voteInventory25([
  { _id: 0, votes: 1 }, { _id: 1, votes: 1 }, { _id: 2, votes: 1 }
]);
const psa25 = voteInventory25([
  { _id: 0, votes: 1 }, { _id: 1, votes: 1 },
  { _id: 2, votes: 1, arbiterOnly: true }
]);
check25(threeData25.electionMajority === 2 &&
        psa25.electionMajority === 2, "Wrong election-majority arithmetic");
check25(threeData25.votingDataMembers === 3 &&
        psa25.votingDataMembers === 2, "Data-copy distinction lost");
printjson({ threeDataMembers: threeData25, primarySecondaryArbiter: psa25 });
```

Both examples have the same voting majority arithmetic. Their data-bearing redundancy differs. This is configuration reasoning, not a simulated election or a measured write-availability test.

## 15. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| No setName or oplog | hello, deployment mode | Standalone/router/wrong target | Use approved data-bearing replica-set member |
| Status/config succeeds but oplog read denied | Exact privilege/error | Monitoring access does not include raw local reads | Record unavailable branch or use authorized operator |
| Empty evidence query | Namespace, timestamp type, run IDs | Correlation typo, rollover or operation representation | Correct scope; preserve missing-evidence limitation |
| Update payload differs from command | op, o, o2, version | Replication diff format | Verify identity/state, avoid fixed parser assumptions |
| Secondary state but stale result | Member optimes and application read | Lag or read contract | Investigate progress and concern settings |
| Majority acknowledgement timeout | Error, identity, actual data | Insufficient acknowledgement or delayed response | Reconcile; do not blindly replay |
| Large oplog but short window | Oldest/newest timestamps, write volume | High operation generation | Size for measured peak rates and recovery duration |
| Oplog allocation exceeds configured size | Commit progress and retention settings | Protection/retention semantics | Investigate capacity, do not truncate manually |

## 16. Production design boundaries

Inventory failure domains as well as member count. Host, availability-zone, network and storage dependencies can defeat apparent redundancy. Driver discovery must reach advertised members; one reachable seed is insufficient if discovered addresses are inaccessible.

Size each member for steady traffic, election/recovery overlap and oplog retention. A lagging member can fall outside available history and require resynchronization. A large oplog is not a backup and does not prevent accidental application deletes from replicating.

Use periodic backups with tested restoration and application reconciliation. Hidden/delayed members can support particular operational designs, but do not replace that recovery discipline.

This chapter does not step down a primary, kill a node, change votes/priorities, simulate partitions or validate rollback. Those are separate scoped HA labs. Do not promote inspection results into a production HA completion claim.

## 17. Cleanup

Finish any optional secondary read before dropping the primary fixture. Capture configuration/status, window and bounded oplog evidence first:

```javascript
check25(events25.countDocuments({ runId: runId25 }) === 2,
        "Fixture state changed");
if (lab25.getName() !== "mongodb_enterprise_tutorial_ch25") {
  throw new Error("Refusing cleanup outside the Chapter 25 training database");
}
const dropResult25 = lab25.dropDatabase();
if (dropResult25.ok !== 1) throw new Error("Chapter 25 database cleanup failed");
check25(lab25.getCollectionNames().length === 0, "Cleanup incomplete");
```

Dropping the chapter database does not erase its historical oplog entries immediately. They remain according to normal retention. Do not delete local history to hide the lab.

No replica configuration, oplog size or concern defaults changed. No topology rollback is required. If you reused a container from Chapter 16, manage its lifecycle using that chapter's scoped cleanup only when no longer needed.

## 18. Acceptance and evidence

- [ ] Recorded exact server/shell versions and primary/member/set identity.
- [ ] Inspected configuration and current member status separately.
- [ ] Distinguished voters, electable members and data-bearing members.
- [ ] Measured this member's retained timestamp window and allocation.
- [ ] Captured a BSON timestamp anchor and stable synthetic run ID.
- [ ] Verified three inserts, one update, one delete and final two-document state.
- [ ] Matched ordinary oplog operations by namespace and document identity.
- [ ] Diagnosed a namespace typo without modifying oplog history.
- [ ] Recorded optional secondary convergence as passed, failed or not applicable.
- [ ] Explained commit-point/acknowledgement limits and completed cleanup.

**Evidence:** versions/member identity, configuration/status snapshots, vote inventory, oldest/newest oplog bounds and sizes, anchor/run ID, application assertions, bounded operation records, optional branch result and cleanup. Runtime validation remains pending until executed on the stated deployment.

## 19. Review questions

1. Why is an election vote different from a replicated data copy?
2. Why does priority zero not automatically mean non-voting?
3. What does a majority acknowledgement fail to prove about every secondary?
4. Why is the raw oplog unsuitable as an immutable business audit log?
5. Why can configured oplog bytes differ from actual allocation?
6. Why is a measured history window not guaranteed future coverage?
7. Which observations would require a different parser for transaction operations?
8. What HA/recovery behavior remains untested by this inspection lab?

## 20. Official references

- [MongoDB 8.0: replica-set members](https://www.mongodb.com/docs/v8.0/core/replica-set-members/)
- [MongoDB 8.0: replica-set oplog](https://www.mongodb.com/docs/v8.0/core/replica-set-oplog/)
- [MongoDB 8.0: replica-set configuration](https://www.mongodb.com/docs/v8.0/reference/replica-configuration/)
- [MongoDB 8.0: replica-set status](https://www.mongodb.com/docs/v8.0/reference/command/replSetGetStatus/)
- [MongoDB 8.0: write concern](https://www.mongodb.com/docs/v8.0/reference/write-concern/)
- [MongoDB 8.0: hidden members](https://www.mongodb.com/docs/v8.0/core/replica-set-hidden-member/)

---

Previous: [Chapter 24 — CPU Memory Storage IOPS and Capacity](24-cpu-memory-storage-iops-and-capacity.md)  
Next: [Chapter 26 — Build a Three Member Replica Set](26-build-a-three-member-replica-set.md).
