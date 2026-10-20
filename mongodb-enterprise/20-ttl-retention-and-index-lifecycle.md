# 20 — TTL Retention and Index Lifecycle

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Verify asynchronous TTL deletion, repair an invalid expiration field, change retention with collMod and rehearse reversible query-index changes.  
**Audience:** Developers, Data Engineers, DBREs and SREs  
**Time:** 90–120 minutes, including bounded TTL observation windows  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Community-compatible or Enterprise training server; standalone or replica-set primary. Ordinary unsharded collections, not time-series collections.

## 1. TTL is retention cleanup, not a deadline service

A TTL index removes whole documents when an indexed BSON date becomes old enough. Its expiration setting is in seconds. An index with expireAfterSeconds: 0 treats the field as an absolute expiration timestamp; a positive duration treats it as a reference timestamp plus that duration.

Deletion is asynchronous. Expired documents can remain after their deadline while background work waits or competes for resources. Applications that must reject expired sessions, tokens or jobs must check their expiration condition during use; they cannot rely solely on physical disappearance.

TTL is not a backup, archive or recovery mechanism. Deleting from the live collection does not define how long backups, exports or downstream copies retain the data. A business retention policy needs those boundaries too.

| Contract | Example | TTL role |
|---|---|---|
| Per-document deadline | expiresAt with duration zero | Background cleanup after each deadline |
| Fixed age | createdAt with duration 86400 | Cleanup after one day from stored creation time |
| Sliding idle age | lastSeenAt with fixed duration | Updates to lastSeenAt extend retention |
| Access expiry | Reject a session after expiresAt | Application evaluates deadline even before deletion |
| Historical archive | Keep older events elsewhere | Separate copy/reconciliation process before removal |

TTL uses the stored date, not insertion time. Updating the date changes eligibility. Choosing createdAt versus lastSeenAt therefore changes the business rule.

## 2. Restrictions and lifecycle distinctions

For ordinary collections, TTL uses a single-field index. A compound tenant/date query index is not a TTL replacement. Keep a single-field expiration index for cleanup and design query indexes separately.

Missing expiration fields, strings and other non-date values do not expire through this ordinary TTL rule. Arrays containing dates use the earliest date for expiration; TTL removes the whole document, not one array element. Validate scalar date shape when that is the intended contract.

Hiding an index removes it from query-planner consideration. It does not stop TTL expiration, uniqueness enforcement or index maintenance. To stop future TTL work for a particular collection, use a reviewed change to its TTL configuration/index; hiding is not that change. Work already underway and data already deleted require separate reasoning.

Dropping an index removes that index. Recreating it costs resources and, for TTL, may immediately make existing old documents eligible. An index lifecycle runbook must distinguish metadata reversal from data recovery.

## 3. Prerequisites and permissions

Complete Chapters 05–06 and 17–19. Connect using the approved training URI; use the primary on a replica set. TTL deletion runs on the primary and its deletes replicate to secondaries.

The user needs database-scoped collection/read/write/index permissions, collMod access for retention changes and index hiding, and dropDatabase for cleanup. A custom role may need additional collMod privileges beyond ordinary application read/write. Do not change roles or global TTL monitor settings to make the lab pass.

No cluster configuration changes are required. Optional serverStatus TTL counters require separate monitoring privilege; omit that optional observation if unavailable.

In mongosh:

```javascript
const labName20 = "mongodb_enterprise_tutorial_ch20";
const lab20 = db.getSiblingDB(labName20);
if (lab20.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
const hello20 = db.adminCommand({ hello: 1 });
printjson({
  serverVersion: db.version(),
  serverTime: hello20.localTime,
  replicaSet: hello20.setName || null,
  writablePrimary: hello20.isWritablePrimary
});
if (!hello20.isWritablePrimary) {
  throw new Error("Use a writable training server or replica-set primary");
}
function check20(condition, message) {
  if (!condition) throw new Error(message);
}
function serverNow20() {
  const value = db.adminCommand({ hello: 1 }).localTime;
  check20(value instanceof Date, "Server clock not available");
  return value;
}
function ttlOption20(collection, name) {
  const found = collection.getIndexes().find(i => i.name === name);
  check20(found !== undefined, "Index missing: " + name);
  return Number(found.expireAfterSeconds);
}
function waitAbsent20(collection, ids, timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const remaining = collection.countDocuments({ _id: { $in: ids } });
    if (remaining === 0) {
      printjson({ removedIds: ids, observation: "absent" });
      return;
    }
    sleep(1000);
  }
  printjson(collection.find({ _id: { $in: ids } }).toArray());
  throw new Error("TTL observation window elapsed; diagnose rather than force-delete");
}
```

Record mongosh --version separately. Fixtures derive dates from server time to reduce client-clock ambiguity. Date.now in the polling helper only bounds observation duration; it does not calculate server expiration eligibility.

The 180-second observation window is a lab budget, not a MongoDB deletion guarantee. If it expires, preserve evidence and investigate. Do not manually delete target documents and call that TTL validation.

## 4. Absolute expiration with BSON dates

```javascript
lab20.createCollection("sessions");
const sessions20 = lab20.sessions;
const now20 = serverNow20().getTime();
sessions20.insertMany([
  { _id: "expired", expiresAt: new Date(now20 - 3600000), state: "old" },
  { _id: "future", expiresAt: new Date(now20 + 7 * 86400000), state: "valid" },
  { _id: "wrong-type", expiresAt: new Date(now20 - 3600000).toISOString(),
    state: "invalid-date-shape" },
  { _id: "missing", state: "no-expiration-field" }
]);
check20(sessions20.countDocuments({}) === 4, "Wrong session fixture");
sessions20.createIndex({ expiresAt: 1 }, {
  name: "expires_at_ttl", expireAfterSeconds: 0
});
check20(ttlOption20(sessions20, "expires_at_ttl") === 0,
        "Wrong absolute TTL setting");
waitAbsent20(sessions20, ["expired"]);
check20(sessions20.findOne({ _id: "future" }) !== null,
        "Future session was removed");
check20(sessions20.findOne({ _id: "wrong-type" }) !== null,
        "String field unexpectedly expired");
check20(sessions20.findOne({ _id: "missing" }) !== null,
        "Missing field unexpectedly expired");
```

Expected state: expired is gone; future, wrong-type and missing remain. An ISO-looking string is not a BSON date. The test deliberately proves that invalid shape can defeat retention rather than pretending all old-looking values expire.

## 5. Failure exercise: repair the date contract

Inspect actual stored types:

```javascript
printjson(sessions20.aggregate([
  { $project: { expiresAt: 1, storedType: { $type: "$expiresAt" } } },
  { $sort: { _id: 1 } }
]).toArray());
const badSession20 = sessions20.findOne({ _id: "wrong-type" });
const parsed20 = new Date(badSession20.expiresAt);
check20(!Number.isNaN(parsed20.getTime()), "Invalid fixture timestamp");
sessions20.updateOne({ _id: "wrong-type" }, {
  $set: { expiresAt: parsed20, state: "repaired" }
});
waitAbsent20(sessions20, ["wrong-type"]);
check20(sessions20.findOne({ _id: "missing" }) !== null,
        "Repair affected missing-field fixture");
```

Diagnosis: the field had string type, so TTL did not expire it. Correcting it to a past BSON date makes it eligible for asynchronous deletion. Capture the type evidence before repair because the document may disappear quickly afterward.

Prevent recurrence with a validator requiring a scalar date:

```javascript
const validatorResult20 = lab20.runCommand({
  collMod: "sessions",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["expiresAt"],
      properties: { expiresAt: { bsonType: "date" } }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});
check20(validatorResult20.ok === 1, "Validator change failed");
let validationFailure20 = false;
try {
  sessions20.insertOne({ _id: "rejected-string", expiresAt: "2026-01-01" });
} catch (error) {
  validationFailure20 = Number(error.code) === 121;
  printjson({ code: error.code, message: error.message });
  if (!validationFailure20) throw error;
}
check20(validationFailure20, "Expected invalid-date rejection");
check20(sessions20.findOne({ _id: "rejected-string" }) === null,
        "Rejected write persisted");
```

Adding validation does not retroactively remove or fix existing invalid documents. The earlier missing fixture remains and is intentionally recorded as unresolved historical data. In production, preview and reconcile such records before claiming retention coverage.

## 6. Whole-document expiration for date arrays

Use a separate collection so the session validator does not interfere:

```javascript
lab20.createCollection("arrayDeadlines");
const arrays20 = lab20.arrayDeadlines;
const arrayNow20 = serverNow20().getTime();
arrays20.insertOne({
  _id: "mixed-deadlines",
  expiresAt: [
    new Date(arrayNow20 - 3600000),
    new Date(arrayNow20 + 7 * 86400000)
  ],
  payload: "Whole document will expire"
});
arrays20.createIndex({ expiresAt: 1 }, {
  name: "array_deadline_ttl", expireAfterSeconds: 0
});
waitAbsent20(arrays20, ["mixed-deadlines"]);
```

The earliest date makes the whole record eligible despite another future date. TTL does not prune just the expired array value. If records contain independently expiring subitems, design their storage or a separate cleanup process accordingly.

## 7. Change age retention with collMod

Create an age-based collection with a generous initial duration. The old item is two hours old but initially protected by a one-year age limit.

```javascript
lab20.createCollection("events");
const events20 = lab20.events;
const ageNow20 = serverNow20().getTime();
events20.insertMany([
  { _id: "old-event", createdAt: new Date(ageNow20 - 7200000) },
  { _id: "future-event", createdAt: new Date(ageNow20 + 7 * 86400000) }
]);
const originalRetention20 = 365 * 86400;
events20.createIndex({ createdAt: 1 }, {
  name: "created_age_ttl", expireAfterSeconds: originalRetention20
});
check20(ttlOption20(events20, "created_age_ttl") === originalRetention20,
        "Original retention mismatch");
check20(events20.findOne({ _id: "old-event" }) !== null,
        "Old fixture unexpectedly absent before reduction");
const proposedRetention20 = 60;
const previewCutoff20 = new Date(
  serverNow20().getTime() - proposedRetention20 * 1000
);
const previewIds20 = events20.find({
  createdAt: { $type: "date", $lte: previewCutoff20 }
}).toArray().map(r => r._id);
check20(JSON.stringify(previewIds20) === JSON.stringify(["old-event"]),
        "Unexpected deletion preview");
printjson({ proposedRetentionSeconds: proposedRetention20,
            cutoff: previewCutoff20, eligibleIds: previewIds20 });
const shorter20 = lab20.runCommand({
  collMod: "events",
  index: { name: "created_age_ttl", expireAfterSeconds: proposedRetention20 }
});
check20(shorter20.ok === 1, "Retention change failed");
check20(ttlOption20(events20, "created_age_ttl") === 60,
        "Retention metadata did not change");
waitAbsent20(events20, ["old-event"]);
check20(events20.findOne({ _id: "future-event" }) !== null,
        "Future event disappeared");
```

Use collMod to change an existing TTL duration. Repeating createIndex with a different expiration option is not the duration-change workflow.

This preview is valid for the scalar date fixture. Arrays, missing/type issues, partial membership and concurrent writes require a more complete production preview.

Restore the original metadata and prove the data is still absent:

```javascript
const restored20 = lab20.runCommand({
  collMod: "events",
  index: { name: "created_age_ttl", expireAfterSeconds: originalRetention20 }
});
check20(restored20.ok === 1, "Retention metadata rollback failed");
check20(ttlOption20(events20, "created_age_ttl") === originalRetention20,
        "Original duration not restored");
check20(events20.findOne({ _id: "old-event" }) === null,
        "Deleted event unexpectedly returned");
```

Increasing retention changes future eligibility. It does not resurrect deleted documents. A production rollback must distinguish restoring the setting from restoring data through a validated backup/recovery path.

## 8. Hiding TTL does not pause deletion

```javascript
lab20.createCollection("hiddenExpiry");
const hiddenExpiry20 = lab20.hiddenExpiry;
hiddenExpiry20.createIndex({ expiresAt: 1 }, {
  name: "hidden_expiry_ttl", expireAfterSeconds: 0
});
hiddenExpiry20.hideIndex("hidden_expiry_ttl");
try {
  check20(hiddenExpiry20.getIndexes().find(
    i => i.name === "hidden_expiry_ttl"
  ).hidden === true, "TTL index not hidden");
  hiddenExpiry20.insertOne({
    _id: "hidden-old",
    expiresAt: new Date(serverNow20().getTime() - 3600000)
  });
  waitAbsent20(hiddenExpiry20, ["hidden-old"]);
} finally {
  hiddenExpiry20.unhideIndex("hidden_expiry_ttl");
}
check20(hiddenExpiry20.getIndexes().find(
  i => i.name === "hidden_expiry_ttl"
).hidden !== true, "TTL hidden setting not restored");
```

Expected result: deletion occurs while the index is hidden. This is a semantics test, not a recommended retention stop procedure. The finally block restores planner visibility even if polling fails.

Do not use hideIndex as an emergency response to accidental TTL deletion. Stop the reviewed deletion mechanism and preserve evidence using deployment-specific procedures; restore already deleted data separately.

## 9. Convert an ordinary single-field index to TTL

MongoDB 8.0 supports adding TTL expiration to an existing eligible single-field index through collMod. Test the conversion on an empty disposable collection:

```javascript
lab20.createCollection("conversion");
const conversion20 = lab20.conversion;
conversion20.createIndex({ expiresAt: 1 }, { name: "expires_regular" });
check20(!Object.hasOwn(conversion20.getIndexes().find(
  i => i.name === "expires_regular"
), "expireAfterSeconds"), "Index already had TTL");
const converted20 = lab20.runCommand({
  collMod: "conversion",
  index: { name: "expires_regular", expireAfterSeconds: 0 }
});
check20(converted20.ok === 1, "TTL conversion failed");
check20(ttlOption20(conversion20, "expires_regular") === 0,
        "Converted metadata missing");
conversion20.insertOne({
  _id: "converted-old",
  expiresAt: new Date(serverNow20().getTime() - 3600000)
});
waitAbsent20(conversion20, ["converted-old"]);
```

A production conversion must preview eligible data before enabling TTL. An existing index can make conversion easy mechanically while making a large deletion backlog immediately eligible operationally.

To return this empty lab index to ordinary behavior, drop and recreate the captured ordinary definition:

```javascript
check20(conversion20.countDocuments({}) === 0, "Conversion fixture not empty");
conversion20.dropIndex("expires_regular");
conversion20.createIndex({ expiresAt: 1 }, { name: "expires_regular" });
check20(!Object.hasOwn(conversion20.getIndexes().find(
  i => i.name === "expires_regular"
), "expireAfterSeconds"), "Ordinary definition not restored");
```

This drop/recreate rehearsal is safe because the collection is empty and disposable. It is not a low-cost rollback promise for a large live index.

## 10. Rehearse query-index retirement separately

A query index can be hidden before retirement to observe planner behavior, with unhide as a quick reversal. Use a separate non-TTL fixture:

```javascript
lab20.createCollection("lookup");
const lookup20 = lab20.lookup;
lookup20.insertMany(Array.from({ length: 200 }, (_, i) => ({
  _id: i, tenantId: "t" + (i % 5), seq: i
})));
lookup20.createIndex({ tenantId: 1, seq: -1 }, { name: "tenant_seq_lookup" });
const capturedDefinition20 = lookup20.getIndexes().find(
  i => i.name === "tenant_seq_lookup"
);
printjson(capturedDefinition20);
function lookupQuery20() {
  return lookup20.find({ tenantId: "t1" }).sort({ seq: -1 }).limit(5);
}
function verifyLookup20() {
  check20(JSON.stringify(lookupQuery20().toArray().map(r => Number(r.seq))) ===
    JSON.stringify([196, 191, 186, 181, 176]), "Lookup result changed");
}
verifyLookup20();
lookup20.hideIndex("tenant_seq_lookup");
try {
  verifyLookup20();
  printjson(lookupQuery20().explain("executionStats").queryPlanner.winningPlan);
} finally {
  lookup20.unhideIndex("tenant_seq_lookup");
}
verifyLookup20();
```

Correctness should remain intact while the access path may get worse. Hiding does not remove write maintenance or storage cost. Named hints to the hidden index can fail; identify those dependencies before a production rehearsal.

Capture options before dropping. Recreate only this lab's simple definition:

```javascript
lookup20.dropIndex("tenant_seq_lookup");
verifyLookup20();
lookup20.createIndex(capturedDefinition20.key, {
  name: capturedDefinition20.name
});
verifyLookup20();
check20(lookup20.getIndexes().some(i => i.name === "tenant_seq_lookup"),
        "Query index not recreated");
```

A real index manifest must preserve all relevant options: collation, unique, sparse, partial filter, TTL, hidden state and other supported settings. Do not pass a raw getIndexes document including server-generated fields straight to createIndex.

## 11. Observability and failure diagnosis

Optional, only if your training account has monitoring access:

```javascript
// Optional monitoring observation; skip if serverStatus is unauthorized.
const optionalTtlStatus20 = db.adminCommand({ serverStatus: 1 });
printjson(optionalTtlStatus20.metrics && optionalTtlStatus20.metrics.ttl);
```

These counters are server-wide and cumulative, not per-collection proof that this fixture expired. Counter deltas can include other workloads; restarts reset the context. Pair them with the exact fixture ID checks.

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Deadline passed but record remains | Server time, BSON type, index metadata, polling duration | Async backlog, wrong type or absent TTL | Diagnose; do not claim an exact deletion SLA |
| Old-looking timestamp never expires | Aggregated $type | String or missing field | Reconcile data and validate date shape |
| Record with future array date disappears | Complete date array | Earliest date controlled whole-document expiration | Use scalar deadline or redesign subitem retention |
| Retention reduction causes deletion wave | Eligible count, delete rate, I/O, replication lag | Large historical backlog | Preview and stage cleanup/change under a reviewed plan |
| Hidden TTL keeps deleting | hidden flag plus expireAfterSeconds | Expected hidden-index semantics | Use appropriate retention change, not hiding |
| Setting restored but data absent | Metadata and record checks | Rollback cannot resurrect deleted data | Use tested recovery path |
| Disk usage does not fall immediately | Logical count, collection/storage metrics, filesystem usage | Freed space can remain allocated for reuse | Measure separately; do not promise immediate OS shrink |
| collMod denied | Role and failing namespace | Missing index/collection modification privilege | Use authorized operational role |
| Polling budget exhausted | Full fixture and metadata, primary state | Delay or setup problem | Mark run failed/pending and preserve evidence |

Do not lower global TTL monitor intervals or force delete fixtures merely to produce a passing result.

## 12. Production retention-change runbook

1. Define the retention field and unit, affected document classes, application expiration checks and downstream/backup policy.
2. Inventory exact versions, collection type, index options, BSON types and date distributions.
3. Preview newly eligible records, including partial membership and array semantics if present. Estimate deletion backlog and resource demand.
4. Confirm a tested recovery path before a destructive retention reduction. Capture the current metadata and a reviewable change plan.
5. If backlog is large, reconcile/archive data and consider controlled bounded deletions before enabling or shortening TTL. Do not issue an unbounded cleanup just to reduce backlog.
6. Apply the reviewed index/retention change, then observe foreground latency, delete activity, storage pressure, replication lag and remaining expired backlog.
7. Verify application behavior and data completeness against the policy; record actual deletion lag rather than assuming a fixed schedule.
8. If reverting, restore the intended configuration and recover deleted records separately when required.

This is an operational sequence, not proof that this lab validated high-volume deletion, backup restoration or failover. Those require dedicated environment-specific exercises.

Index retirement likewise needs representative query evidence, named-hint dependency checks, retained definitions, a hide/unhide observation window and a rebuild plan. An index unused during a short sample may serve rare maintenance or recovery work.

TTL deletion can generate replication and change-stream activity. Downstream consumers need to handle deletes and retention semantics deliberately. Retention is not evidence that every external copy has been erased.

## 13. Cleanup

Save timing observations, index definitions, type/failure output, retention preview and post-change state before cleanup. Restore the hidden flag if an exercise was interrupted:

```javascript
const expiryIndex20 = hiddenExpiry20.getIndexes().find(
  i => i.name === "hidden_expiry_ttl"
);
if (expiryIndex20 && expiryIndex20.hidden === true) {
  hiddenExpiry20.unhideIndex("hidden_expiry_ttl");
}
const lookupIndex20 = lookup20.getIndexes().find(
  i => i.name === "tenant_seq_lookup"
);
if (lookupIndex20 && lookupIndex20.hidden === true) {
  lookup20.unhideIndex("tenant_seq_lookup");
}
check20(ttlOption20(events20, "created_age_ttl") === originalRetention20,
        "Age-retention metadata was not restored");
if (lab20.getName() !== "mongodb_enterprise_tutorial_ch20") {
  throw new Error("Refusing cleanup outside the Chapter 20 training database");
}
const dropResult20 = lab20.dropDatabase();
check20(dropResult20.ok === 1, "Database cleanup command failed");
check20(lab20.getCollectionNames().length === 0, "Cleanup incomplete");
```

Every affected collection belongs to this named database. No cluster settings, shared containers or other databases are touched. If the lab stopped before a collection was created, inspect existing collections and clean up the chapter database deliberately rather than executing helpers referencing missing variables.

## 14. Acceptance and evidence

- [ ] Recorded exact server/shell versions, server time and writable deployment context.
- [ ] Expired BSON-date fixture disappeared within the observed lab budget.
- [ ] Future, missing and string-date fixtures behaved as specified.
- [ ] Repaired a string date and observed subsequent expiration.
- [ ] Validator rejected a new string expiration field.
- [ ] Earliest date in an array expired the whole document.
- [ ] Previewed and applied a retention reduction with collMod.
- [ ] Restored duration metadata without claiming deleted data returned.
- [ ] Hidden TTL still expired a fixture and was unhidden.
- [ ] Converted an ordinary index to TTL and restored the empty ordinary definition.
- [ ] Rehearsed query-index hide/unhide/drop/recreate with stable results.
- [ ] Saved evidence and completed scoped cleanup.

**Evidence:** versions/server time, index definitions/options, polling timestamps and outcomes, BSON types, validator error, eligible-record preview, retention metadata before/after, post-rollback absence, hidden-state checks, query result IDs and cleanup. Runtime validation remains pending until executed successfully; the written polling helper is not evidence that TTL deletion has occurred.

## 15. Review questions

1. Why must an application reject expired sessions before TTL cleanup finishes?
2. What differs between expiresAt with duration zero and createdAt with a positive duration?
3. Why does a date-looking string remain in the TTL collection?
4. Which array date controls expiration, and what unit of data is deleted?
5. Why is hiding a TTL index ineffective as a deletion pause?
6. What can restoring expireAfterSeconds reverse, and what requires recovery?
7. Why can TTL reduce document counts without immediately reducing filesystem usage?
8. What evidence is needed before shortening retention on a large live collection?

## 16. Official references

- [MongoDB 8.0: TTL indexes, restrictions and asynchronous deletion](https://www.mongodb.com/docs/v8.0/core/index-ttl/)
- [MongoDB 8.0: expire data with TTL](https://www.mongodb.com/docs/v8.0/tutorial/expire-data/)
- [MongoDB 8.0: collMod and TTL changes](https://www.mongodb.com/docs/v8.0/reference/command/collMod/)
- [MongoDB 8.0: hidden-index behavior](https://www.mongodb.com/docs/v8.0/core/index-hidden/)
- [MongoDB 8.0: schema validation](https://www.mongodb.com/docs/v8.0/core/schema-validation/)

---

Previous: [Chapter 19 — Multikey Partial Sparse and Unique Indexes](19-multikey-partial-sparse-and-unique-indexes.md)  
Next: [Chapter 21 — Explain Plans and Query Optimization](21-explain-plans-and-query-optimization.md).
