# 27 — Read Preference Read Concern and Write Concern

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 4 — Replication and High Availability  
**Goal:** Separate routing, visibility and acknowledgement contracts; verify explicit concerns and causal-session reads; reproduce an unsatisfiable acknowledgement without treating it as write rollback.  
**Audience:** Developers, DBREs, SREs and Data Engineers  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Community-compatible or Enterprise three-data-member training replica set from Chapter 26. No topology changes.

## 1. Three independent questions

| Setting | Question answered | What it does not answer |
|---|---|---|
| Read preference | Which eligible member serves a read? | Whether its data is the newest globally |
| Read concern | Which visibility/consistency boundary applies? | Which member is selected |
| Write concern | What acknowledgement is required before success? | Whether all members applied the write or the client knows every error outcome |

Do not describe secondary reads as simply “eventually consistent” without stating concerns and session behavior. Do not describe primary reads as automatically linearizable. The routing choice and the consistency contract are separate.

The lab uses a stable synthetic business identifier and explicit settings. It does not modify deployment defaults or induce failover.

## 2. Read routing tradeoffs

| Mode | Selection behavior | Application implication |
|---|---|---|
| primary | Select primary | No ordinary secondary fallback |
| primaryPreferred | Prefer primary; secondary fallback when unavailable | Results may come from a different freshness boundary during fallback |
| secondary | Select eligible secondary | Read fails if none is selectable |
| secondaryPreferred | Prefer secondary; primary fallback | Does not guarantee a secondary served the read |
| nearest | Select within latency window among eligible members | Network proximity is not recency |

Tag sets and maxStalenessSeconds can narrow eligible secondary selection. Max staleness is an estimated selection constraint, not a strict per-document age guarantee. It has version-specific minimum requirements; do not use it as a millisecond freshness SLA.

Secondary routing can offload some reads but adds secondary workload that competes with replication. Measure lag, storage/cache pressure and application tolerance. Writes remain directed to the primary through a replica-set-aware client.

## 3. Read visibility and acknowledgement

| Concern | Teaching interpretation | Boundary |
|---|---|---|
| local read | Read locally available data | Data may not be majority committed and can roll back |
| majority read | Read majority-committed data available on selected member | Does not mean the latest write is already applied there |
| linearizable read | Stronger real-time single-document read contract under prerequisites | Primary only; use bounded operation time and compatible predicates |
| snapshot read | Point-in-time consistency where supported | Operation/session/transaction support must be checked |
| w: 1 write | Primary acknowledgement | Does not establish replicated majority durability |
| w: majority write | Required voting data-member acknowledgement | Does not mean every secondary is current |
| j: true | Require journal durability under the write concern | Not a backup or an independent replication count |
| wtimeout | Bound acknowledgement waiting | Does not undo a successfully performed write |

MongoDB 8.0 majority acknowledgement can precede secondary application of the durable oplog entry. A causal majority read may therefore wait for the selected secondary to reach the necessary state.

Implicit defaults depend on topology/configuration and can be overridden at different levels. Inspect and document them rather than assuming every deployment uses identical defaults. This chapter sets operation concerns explicitly and never calls setDefaultRWConcern.

## 4. Prerequisites and connection

Retain or rebuild the three-member project from Chapter 26. All three members must be healthy voting data-bearing members, with no arbiter, delay or hidden configuration introduced.

From the same Compose folder:

```bash
docker compose -p mongodb-ch26 ps
docker compose -p mongodb-ch26 exec a mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=10000"
```

For another approved training set, use its actual authenticated/TLS URI and reachable hosts. The Chapter 26 internal names are not host-side addresses.

The operator needs read/write/create/drop access for this chapter database and status/configuration inspection. No concern-default or topology administration is required. This lab is unsuitable for a one-member set because the routing and three-member acknowledgement assertions would lose their intended meaning.

In mongosh:

```javascript
const labName27 = "mongodb_enterprise_tutorial_ch27";
const lab27 = db.getSiblingDB(labName27);
function check27(condition, message) {
  if (!condition) throw new Error(message);
}
const hello27 = db.adminCommand({ hello: 1 });
check27(hello27.setName && hello27.isWritablePrimary,
        "Connect through a primary-capable replica-set URI");
const config27 = db.adminCommand({ replSetGetConfig: 1 }).config;
check27(config27.members.length === 3 &&
        config27.members.every(m =>
          m.arbiterOnly !== true && m.hidden !== true &&
          (m.votes === undefined || Number(m.votes) === 1) &&
          !(Number(m.secondaryDelaySecs || 0) > 0)),
        "Use the ordinary three-data-member lab topology");
const status27 = db.adminCommand({ replSetGetStatus: 1 });
check27(status27.members.filter(m =>
  m.stateStr === "PRIMARY" && m.health === 1).length === 1 &&
  status27.members.filter(m =>
  m.stateStr === "SECONDARY" && m.health === 1).length === 2,
  "Training topology is not healthy");
check27(lab27.getCollectionNames().length === 0,
        "Chapter database exists; review before resetting");
printjson({ version: db.version(), setName: hello27.setName,
            primary: hello27.primary, members: status27.members.map(m =>
              ({ name: m.name, state: m.stateStr, health: m.health })) });
```

Record mongosh --version separately. The check is a starting observation, not a guarantee that roles remain stable throughout the lab.

## 5. Insert fixtures under distinct write concerns

```javascript
lab27.createCollection("events");
const events27 = lab27.events;
const majorityConcern27 = { w: "majority", j: true, wtimeout: 10000 };
const one27 = events27.insertOne({
  _id: "primary-ack", revision: 0, payload: "Synthetic primary acknowledgement"
}, { writeConcern: { w: 1, j: true, wtimeout: 10000 } });
check27(one27.acknowledged, "Primary acknowledgement missing");
const majority27 = events27.insertOne({
  _id: "majority-ack", revision: 0, payload: "Synthetic majority acknowledgement"
}, { writeConcern: majorityConcern27 });
check27(majority27.acknowledged, "Majority acknowledgement missing");
check27(events27.countDocuments({}) === 2, "Fixture count mismatch");
```

Both operations can look identical on a healthy quiet set. That does not make their acknowledgement guarantees identical. The w: 1 example also requests primary journal durability; it still does not require majority replication.

Do not claim this healthy run demonstrated rollback risk or availability under failure. Later chapters test those conditions.

## 6. Read the same fixture with explicit concern

```javascript
const localRows27 = events27.find({ _id: "majority-ack" })
  .readPref("primary").readConcern("local").maxTimeMS(5000).toArray();
const majorityRows27 = events27.find({ _id: "majority-ack" })
  .readPref("primary").readConcern("majority").maxTimeMS(5000).toArray();
check27(localRows27.length === 1 && majorityRows27.length === 1,
        "Known majority fixture not visible on primary");
check27(Number(localRows27[0].revision) === 0 &&
        Number(majorityRows27[0].revision) === 0, "Fixture changed");
printjson({ localRows: localRows27, majorityRows: majorityRows27 });
```

Matching outputs on a healthy set do not prove equivalence of read concerns. Majority read concern addresses committed visibility; primary routing alone does not supply that contract.

Keep maxTimeMS and server-selection timeout distinct. One bounds server operation execution; the other bounds client member selection. Write-concern timeout has another scope. Request deadlines must account for the full path and retries.

## 7. Inspect a secondary-routed query and its limitation

```javascript
const secondaryPlan27 = events27.find({ _id: "majority-ack" })
  .readPref("secondary").readConcern("majority").maxTimeMS(5000)
  .explain("executionStats");
printjson({
  serverInfo: secondaryPlan27.serverInfo,
  returned: secondaryPlan27.executionStats.nReturned,
  winningPlan: secondaryPlan27.queryPlanner.winningPlan
});
check27(secondaryPlan27.serverInfo &&
        secondaryPlan27.serverInfo.host, "Explain server identity unavailable");
```

Correlate serverInfo.host/port with current member identity; container hostnames can differ from advertised service aliases. Do not equate a shell's administrative hello command with the destination of every application read.

This read may return zero if the selected secondary has not applied the fixture yet. Majority acknowledgement alone does not force that immediate application read to wait for this particular write. Do not make a timing race into an assertion that every immediate secondary read must be stale or current.

A plain majority secondary read is not the same as the causal-session exercise below. The explain itself is separate from actual application cursor execution and does not prove a cached request plan.

## 8. Causal session: majority write followed by majority secondary read

Use one causally consistent session sequentially. Its operation time establishes the dependency for the subsequent read.

```javascript
const session27 = db.getMongo().startSession({ causalConsistency: true });
try {
  const sessionLab27 = session27.getDatabase(labName27);
  const write27 = sessionLab27.events.insertOne({
    _id: "causal-event", revision: 1,
    payload: "Synthetic session dependency"
  }, { writeConcern: majorityConcern27 });
  check27(write27.acknowledged, "Causal write not acknowledged");
  const causalRows27 = sessionLab27.events.find({ _id: "causal-event" })
    .readPref("secondary").readConcern("majority").maxTimeMS(10000).toArray();
  check27(causalRows27.length === 1 &&
          Number(causalRows27[0].revision) === 1,
          "Causal secondary read did not observe prior session write");
  printjson({
    operationTime: session27.getOperationTime(),
    rows: causalRows27
  });
} finally {
  session27.endSession();
}
```

The causal read can wait for the selected secondary to reach the dependency. If the operation times out, preserve the error and topology evidence; do not weaken the read concern and count the weaker read as a pass.

This exercises read-your-writes for the stated session/concern combination. It is not a multi-operation transaction or a universal ordering guarantee between unrelated clients. Cross-session causal dependencies require explicit supported time propagation and compatible concerns.

Do not run parallel operations on this session. A session's sequential dependency and an application's arbitrary concurrent requests are different models.

## 9. Failure exercise: unsatisfiable acknowledgement

Request acknowledgement from four data-bearing members on the three-member set. The raw command lets you inspect writeConcernError separately from command status.

```javascript
const impossible27 = lab27.runCommand({
  insert: "events",
  documents: [{
    _id: "ack-failure-event", revision: 1,
    payload: "Synthetic unsatisfiable acknowledgement"
  }],
  writeConcern: { w: 4, j: true, wtimeout: 2000 }
});
printjson(impossible27);
check27(impossible27.ok === 1, "Unexpected top-level command failure");
check27(!impossible27.writeErrors ||
        impossible27.writeErrors.length === 0, "Unexpected write validation error");
check27(impossible27.writeConcernError,
        "Expected unsatisfiable write-concern error");
const afterError27 = events27.find({ _id: "ack-failure-event" })
  .readPref("primary").readConcern("local").maxTimeMS(5000).toArray();
check27(afterError27.length === 1,
        "Expected performed write despite failed acknowledgement contract");
printjson({
  writeConcernError: impossible27.writeConcernError,
  reconciledState: afterError27
});
```

Diagnosis: the requested acknowledgement cannot be satisfied by this topology. The write can still be performed. ok: 1 alone does not mean the entire requested contract succeeded; inspect writeErrors and writeConcernError as well.

This is an unsatisfiable-concern exercise, not a network timeout injection. A real wtimeout likewise does not undo successful modifications, but reproducing it by stopping members belongs in a controlled failure lab.

Correction: reconcile the existing operation, then make a guarded update using a supported majority concern instead of inserting the same business event again:

```javascript
const repaired27 = events27.updateOne(
  { _id: "ack-failure-event", revision: 1 },
  { $set: { revision: 2, reconciled: true } },
  { writeConcern: majorityConcern27 }
);
check27(repaired27.modifiedCount === 1, "Guarded reconciliation failed");
check27(events27.countDocuments({ _id: "ack-failure-event" }) === 1,
        "Reconciliation duplicated event identity");
check27(Number(events27.findOne({ _id: "ack-failure-event" }).revision) === 2,
        "Corrected revision missing");
```

A guarded update protects this synthetic transition. Production reconciliation must decide the business outcome and durability requirement explicitly; reading one primary local value is not sufficient to declare every uncertain outcome durable.

## 10. Classify command evidence correctly

The following pure helper is a teaching classification aid, not a driver's retry policy:

```javascript
function outcome27(result) {
  if (Number(result.ok) !== 1) return "command-failure";
  if (result.writeErrors && result.writeErrors.length > 0) return "write-error";
  if (result.writeConcernError) return "acknowledgement-failure-reconcile";
  return "requested-contract-acknowledged";
}
check27(outcome27({ ok: 1, writeConcernError: { code: 100 } }) ===
        "acknowledgement-failure-reconcile", "Concern error misclassified");
check27(outcome27({ ok: 1, writeErrors: [{ code: 11000 }] }) ===
        "write-error", "Duplicate misclassified");
check27(outcome27({ ok: 0 }) === "command-failure", "Command failure misclassified");
check27(outcome27({ ok: 1, n: 1 }) ===
        "requested-contract-acknowledged", "Success misclassified");
```

A network error can occur without any server response to classify. Error labels, retryable-write identity, operation phase and driver semantics must guide that case. Do not turn this helper into an automatic replay engine.

## 11. Choosing an application contract

| Use case | Candidate policy | Validation needed |
|---|---|---|
| Critical identity update | Majority write, explicit read policy and reconciliation | Uncertain outcomes and failover behavior |
| Read after own write on secondary | Causal session with majority write/read | Session propagation, waiting and deadlines |
| Tolerant reporting read | Reviewed secondary routing/concern | Lag tolerance, completeness and replica load |
| Strict real-time single-document read | Linearizable primary read under prerequisites | Predicates, maxTimeMS and latency/availability |
| Stable multi-document transactional view | Supported snapshot transaction/read design | Transaction boundary and retry semantics |

These are starting policies, not universal defaults. A linearizable read is not a multi-document transaction. Nearest does not mean latest. Majority does not remove every race between unrelated clients.

Document what the caller may observe during fallback, elections and lag. Define business idempotency and deadlines alongside server concerns. Keep read and write contracts visible in driver configuration and tests.

## 12. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Secondary route cannot select member | Read preference, health and timeout | No eligible secondary or inaccessible addresses | Restore topology/connectivity; do not silently change contract |
| Majority secondary read misses recent write | Session dependency and member progress | Plain read lacks causal dependency | Use intended session/consistency policy |
| Causal read waits or times out | Operation time, lag, maxTimeMS | Secondary has not applied dependency | Diagnose lag and request deadline |
| ok: 1 with concern error | Complete command result | Write occurred but acknowledgement failed | Reconcile rather than replay blindly |
| w: 4 fails on this set | Configured data members | Unsatisfiable concern | Choose supported business policy |
| Primary read differs from expectation | Concern and concurrent writes | Routing mistaken for isolation/recency | Define correct read contract |
| Fallback changes serving member | Preference mode and actual destination | Preferred mode permits fallback | Verify application tolerates fallback |
| Default behavior differs across deployments | Topology/default/driver settings | Implicit or overridden concerns | Inventory and set explicit intended policy |

## 13. Production and test boundaries

This lab observes a healthy topology and a configuration-level acknowledgement failure. It does not force replication lag, partition members, elect a new primary or measure rollback. Healthy equal outputs are insufficient evidence for those behaviors.

Test concern policies under the actual failure modes in later chapters, including exhausted request deadlines and ambiguous acknowledgements. Capture operation IDs, errors/labels, serving member and sanitized concern settings.

Avoid reducing concerns merely to remove visible errors. That can change durability or visibility while hiding the underlying availability problem. Conversely, stronger concerns can add waiting and availability requirements; validate them against the business objective.

## 14. Cleanup

Save operation results, causal session evidence and reconciliation output before cleanup:

```javascript
check27(events27.countDocuments({}) === 4, "Unexpected final fixture count");
check27(Number(events27.findOne({ _id: "ack-failure-event" }).revision) === 2,
        "Reconciliation state changed");
if (lab27.getName() !== "mongodb_enterprise_tutorial_ch27") {
  throw new Error("Refusing cleanup outside the Chapter 27 training database");
}
const dropResult27 = lab27.dropDatabase();
if (dropResult27.ok !== 1) throw new Error("Chapter 27 database cleanup failed");
check27(lab27.getCollectionNames().length === 0, "Cleanup incomplete");
```

The session was ended and no defaults or member configuration changed. Keep the Chapter 26 project for subsequent HA labs, or use its explicit owned-project cleanup when finished. Do not remove shared resources from this chapter.

## 15. Acceptance and evidence

- [ ] Recorded versions and healthy three-data-member configuration.
- [ ] Distinguished routing, visibility and acknowledgement.
- [ ] Verified explicit primary and majority writes and primary reads.
- [ ] Inspected secondary query execution without asserting an immediate freshness race.
- [ ] Verified causal majority read-your-writes on a secondary.
- [ ] Reproduced an unsatisfiable concern and inspected performed-write state.
- [ ] Reconciled the stable event with a guarded majority update.
- [ ] Classified command/write/acknowledgement errors separately.
- [ ] Documented failure-test limits and completed scoped cleanup.

**Evidence:** versions/topology, concern settings, fixture outputs, secondary explain identity, session operation time, complete failed concern response, reconciliation assertions and cleanup. Runtime validation remains pending until executed successfully.

## 16. Review questions

1. Why does primary routing not automatically make a read linearizable?
2. Why can a majority-acknowledged write still require a causal secondary read to wait?
3. Which preferred modes allow fallback, and why does that affect the application contract?
4. Why does write-concern failure not imply write rollback?
5. Which timeout bounds member selection, server execution and acknowledgement waiting?
6. Why is a causal session different from a transaction?
7. Why does ok: 1 not alone prove write contract success?
8. Which guarantees remain untested by this healthy-topology lab?

## 17. Official references

- [MongoDB 8.0: read preference](https://www.mongodb.com/docs/v8.0/core/read-preference/)
- [MongoDB 8.0: read concern](https://www.mongodb.com/docs/v8.0/reference/read-concern/)
- [MongoDB 8.0: write concern and acknowledgement errors](https://www.mongodb.com/docs/v8.0/reference/write-concern/)
- [MongoDB 8.0: causal consistency combinations](https://www.mongodb.com/docs/v8.0/core/causal-consistency-read-write-concerns/)
- [MongoDB 8.0: default concerns](https://www.mongodb.com/docs/v8.0/reference/mongodb-defaults/)
- [MongoDB specifications: read/write concern result handling](https://specifications.readthedocs.io/en/latest/read-write-concern/read-write-concern/)

---

Previous: [Chapter 26 — Build a Three Member Replica Set](26-build-a-three-member-replica-set.md)  
Next: [Chapter 28 — Elections Stepdown and Planned Maintenance](28-elections-stepdown-and-planned-maintenance.md).
