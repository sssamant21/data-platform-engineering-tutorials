# 65 — Time Series Collections and Retention

Part 9 — Specialized Data and Observability

**Audience:** Developers, Data Engineers, DBREs and SREs.  
**Goal:** Design a measurement collection, verify queries and demonstrate retention without confusing logical expiration with physical deletion.  
**Baseline:** MongoDB 8.0 / FCV 8.0; use the retained authenticated TLS replica set from Chapters 60–62. Core operations are Community-compatible; this lab does not validate Enterprise-only features. Record the exact server patch and mongosh release.  
**Status:** Written; static review complete; live MongoDB acceptance pending.  
**Prerequisites:** Chapters 11, 17–21, 24, 41–42 and 64; an accepted lab deployment and ownership record.  
**Estimated time:** 60–90 minutes, including bounded TTL observation.

## 1. Define the workload and acceptance contract

Use time series collections for repeated measurements with an event timestamp and stable series identity. Examples include node CPU samples, sensor readings and service latency measurements. This chapter uses synthetic node CPU data; no patient or production data is required.

Acceptance means more than successfully creating a collection. You will:

- Verify collection type, timestamp type, metadata and retention settings.
- Reconcile 120 measurements and two series with deterministic aggregates.
- Query a bounded interval and inspect the actual execution plan.
- Reject malformed timestamps and repair the producer representation.
- Observe separate global and metadata-specific retention policies.
- Disable and restore retention configuration while documenting irreversible deletions.
- Capture evidence and remove only the owned lab database.

Retain a normal collection when the application requires database-enforced uniqueness, arbitrary measurement updates, schema validation, transactional writes or change streams. MongoDB 8.0 time series collections have restrictions in these areas.[1] Chapter 64's collection watch consumer must not be pointed at this collection as if its CDC contract were supported.

## 2. Measurement model and bucket architecture

A logical measurement in this lab is:

```javascript
({
  ts: ISODate("2026-01-01T00:00:00Z"),
  meta: { tenant: "training", host: "node-a", metric: "cpu_pct" },
  sampleId: "node-a-0",
  value: 20
})
```

`ts` is the BSON Date used for time filtering and retention. `meta` identifies a stable series. `value` is the measurement. `sampleId` supports reconciliation, but is not a unique constraint.

MongoDB groups measurements into internal buckets, separating storage from the logical collection interface.[2] Applications insert and query the logical collection. Do not write, delete or alter indexes directly in `system.buckets.*`.

Keep metadata stable and consistently shaped. Putting a per-event ID, changing timestamp or current value in metadata creates additional series and can reduce bucket reuse. High series cardinality, sparse measurements and out-of-order arrivals can increase bucket overhead. Compression and index savings must be measured with representative data; a tiny fixture cannot establish a production ratio.

Choose event time deliberately. A backfill with old event timestamps may immediately qualify for expiration. A producer using future timestamps can keep data longer than intended. Store ingestion time separately if required and validate clock skew before accepting writes.

## 3. Bucketing and retention are separate controls

For MongoDB 8.0, the default granularity modes permit these bucket time spans:[3]

| Granularity | Maximum time span | Practical interpretation |
|---|---|---|
| `seconds` | 1 hour | Frequent measurements |
| `minutes` | 24 hours | Less frequent measurements |
| `hours` | 30 days | Sparse measurements |

These are bucket spans, not retention periods or fixed row counts. Buckets can close earlier because of other limits. A one-minute sampling interval does not force `granularity: "minutes"`; evaluate query windows, metadata cardinality and retention requirements together.

Custom `bucketMaxSpanSeconds` and `bucketRoundingSeconds` are available on this baseline. Set both to the same value and omit `granularity`.[2] The lab uses 60-second custom buckets to keep TTL observation practical. This is a teaching setting, not a production default.

Bucket intervals can be increased but cannot be reduced in place. `timeField`, `metaField` and collection type are creation-time choices.[1][2] A redesign requires a new collection, controlled copy, reconciliation and application routing change. Do not promise a rename-based cutover for time series collections.

## 4. Retention semantics and policy boundaries

Collection-level `expireAfterSeconds` applies to event time. An individual measurement crosses its logical threshold at `ts + retention`. Physical cleanup is asynchronous and bucket-aware; buckets become eligible based on their upper time boundary and configured expiration. The TTL monitor runs periodically and can lag under load.[3][4]

Consequences for operations:

- An expired measurement can still appear in a query before bucket cleanup.
- A query-time cutoff can enforce the application's visibility window while cleanup catches up.
- TTL is not an exact deletion deadline, backup policy or archive mechanism.
- Increasing retention or disabling it cannot recreate deleted measurements.
- Successful cleanup does not prove that the filesystem shrank; storage can remain allocated for reuse.

The application must define whether a report uses a fixed report cutoff or a moving current-time cutoff. Otherwise identical queries run at different times can produce different totals by design.

On this baseline, partial TTL indexes can apply a shorter policy to metadata-selected series. Their key is the time field and their partial filter uses metadata.[4] A longer partial policy cannot override a shorter collection policy. To retain selected data longer, design the global policy and selective shorter policies accordingly, or use separate collections.

## 5. Connection, permissions and version evidence

Connect using the accepted TLS/SCRAM settings from Chapter 42. Replace hosts, CA path and identity with your recorded lab values. The command prompts for the password; do not embed it in the URI or shell history.

```bash
mongosh 'mongodb://db1:27017,db2:27017,db3:27017/admin?replicaSet=rs0&authSource=admin' \
  --tls --tlsCAFile /path/to/lab-ca.pem \
  --username ch65_lab_admin --password
```

Use a scoped lab identity authorized for create/list collections, inserts, queries, create/drop indexes, `collMod` and database cleanup on the selected lab database. A separately authorized observer can collect FCV and server status. Production producers should receive only their required insert privileges; retention changes belong to a distinct administrative identity.

In the connected mongosh session:

```javascript
printjson({ server: db.version(), shell: version(), hello: db.hello() });
// Run through the authorized observer if this identity lacks cluster privileges.
printjson(db.getSiblingDB("admin").runCommand({
  getParameter: 1, featureCompatibilityVersion: 1
}));
```

Record edition, exact patch, FCV, topology, shell version, UTC time and namespace. Require a healthy writable primary. Do not change FCV for this chapter. Existing 7.0 environments need their own review; this chapter's validation status applies only to the recorded 8.0 lab.

## 6. Lab setup — claim an empty namespace

Run the numbered JavaScript blocks sequentially in the same mongosh session. On a failed step, stop and diagnose before continuing. The lab does not silently reuse a populated namespace.

```javascript
var labName = "mongodb_enterprise_ch65_timeseries";
var lab = db.getSiblingDB(labName);
function check(condition, message) {
  if (!condition) throw new Error(message);
}
function ok(result, message) {
  check(result.ok === 1, message + ": " + EJSON.stringify(result));
}
check(lab.getCollectionInfos().length === 0,
      "Namespace already exists: choose a fresh owned lab database");
check(db.hello().isWritablePrimary === true, "Connect to the writable primary");
lab.ownership.insertOne({
  _id: "ch65", owner: "mongodb-enterprise-tutorial",
  createdAt: new Date(), purpose: "synthetic time series acceptance"
});
ok(lab.createCollection("cpu_samples", {
  timeseries: {
    timeField: "ts", metaField: "meta",
    bucketMaxSpanSeconds: 60, bucketRoundingSeconds: 60
  },
  expireAfterSeconds: 86400
}), "create cpu_samples");
var info = lab.getCollectionInfos({ name: "cpu_samples" })[0];
check(info.type === "timeseries", "Expected time series collection");
check(info.options.timeseries.timeField === "ts", "Incorrect time field");
check(Number(info.options.expireAfterSeconds) === 86400, "Incorrect retention");
printjson(info);
```

Expected: a `timeseries` entry with `ts`, `meta`, custom bucket settings and 86400-second retention. Keep the ownership record as the cleanup boundary. Do not drop an existing database to make the first assertion pass.

## 7. Lab A — insert and reconcile deterministic measurements

Use the server's current clock as the fixture anchor. All samples are recent, avoiding interference from the one-day policy during the lab.

```javascript
var anchor = db.hello().localTime;
var start = new Date(anchor.getTime() - 60 * 60000);
var rows = [];
for (var i = 0; i < 60; i++) {
  for (var host of ["node-a", "node-b"]) {
    rows.push({
      ts: new Date(start.getTime() + i * 60000),
      meta: { tenant: "training", host: host, metric: "cpu_pct" },
      sampleId: host + "-" + i,
      value: host === "node-a" ? 20 + i : 40 + i
    });
  }
}
var inserted = lab.cpu_samples.insertMany(rows, {
  ordered: true, writeConcern: { w: "majority", wtimeout: 10000 }
});
check(inserted.acknowledged === true, "Insert not acknowledged");
check(lab.cpu_samples.countDocuments({}) === 120, "Expected 120 measurements");
var totals = lab.cpu_samples.aggregate([
  { $match: { "meta.tenant": "training", ts: { $gte: start, $lt: anchor } } },
  { $group: { _id: "$meta.host", n: { $sum: 1 },
              total: { $sum: "$value" }, average: { $avg: "$value" } } },
  { $sort: { _id: 1 } }
]).toArray();
check(totals.length === 2, "Expected two series");
check(totals[0]._id === "node-a" && Number(totals[0].n) === 60 &&
      totals[0].total === 2970 && totals[0].average === 49.5,
      "node-a reconciliation failed");
check(totals[1]._id === "node-b" && Number(totals[1].n) === 60 &&
      totals[1].total === 4170 && totals[1].average === 69.5,
      "node-b reconciliation failed");
printjson(totals);
```

Expected totals are `2970` and `4170`; expected averages are `49.5` and `69.5`. Do not rerun the insert block against the same namespace: it is deliberately not an idempotent ingestion implementation.

Time series collections do not provide a unique index for `sampleId`.[1] If ambiguous write outcomes or upstream redelivery are possible, design deduplication before accepting measurements or reconcile duplicates downstream. A time series collection alone does not establish exactly-once ingestion.

## 8. Lab B — bounded query and index evidence

Create an index for the application's tenant, host and time predicate. Inspect existing indexes first; the server may already have a default metadata/time index.

```javascript
printjson(lab.cpu_samples.getIndexes());
lab.cpu_samples.createIndex(
  { "meta.tenant": 1, "meta.host": 1, ts: 1 },
  { name: "tenant_host_ts" }
);
var cutoff = new Date(start.getTime() + 30 * 60000);
var predicate = {
  "meta.tenant": "training", "meta.host": "node-a",
  ts: { $gte: cutoff, $lt: anchor }
};
var selected = lab.cpu_samples.find(predicate, {
  _id: 0, ts: 1, value: 1, sampleId: 1
}).sort({ ts: 1 }).toArray();
check(selected.length === 30, "Expected 30 node-a measurements");
check(selected[0].value === 50 && selected[29].value === 79,
      "Time-window boundary mismatch");
printjson(lab.cpu_samples.find(predicate).sort({ ts: 1 })
  .explain("executionStats"));
printjson(lab.cpu_samples.find(predicate).sort({ ts: 1 })
  .hint("tenant_host_ts").explain("executionStats"));
```

Compare unhinted and hinted plans. Record returned measurements, keys/bucket documents examined, unpacking stages, sort behavior and execution time. Physical bucket work and logical measurement counts are different units. A hint demonstrates a candidate path; it does not prove the planner should always use that index. The 120-row lab establishes correctness, not production performance superiority.

For production, repeat representative time windows and metadata distributions with a retained dataset, both cache states and bounded concurrency. Keep tenant filtering explicit and verify that aggregations preserve expected counts.

## 9. Failure exercise — string timestamps

Trigger a malformed producer write and prove it did not silently change the collection.

```javascript
var beforeBad = lab.cpu_samples.countDocuments({});
var badRejected = false;
try {
  lab.cpu_samples.insertOne({
    ts: anchor.toISOString(),
    meta: { tenant: "training", host: "node-a", metric: "cpu_pct" },
    sampleId: "bad-string-date", value: 1
  });
} catch (error) {
  badRejected = true;
  printjson({ expectedFailure: true, code: error.code, message: error.message });
}
check(badRejected, "String timestamp unexpectedly accepted");
check(lab.cpu_samples.countDocuments({}) === beforeBad,
      "Rejected write changed measurement count");
```

Diagnosis: an ISO-formatted JSON string is not a BSON Date. Correct the producer serializer. Test the repaired value in a separate short-lived fixture so the deterministic CPU totals remain intact.

```javascript
ok(lab.createCollection("type_probe", {
  timeseries: { timeField: "ts", metaField: "meta", granularity: "seconds" }
}), "create type_probe");
var corrected = new Date(anchor.toISOString());
check(!Number.isNaN(corrected.getTime()), "Date parsing failed");
lab.type_probe.insertOne({ ts: corrected, meta: { host: "probe" }, value: 1 });
var types = lab.type_probe.aggregate([
  { $project: { _id: 0, type: { $type: "$ts" } } }
]).toArray();
check(types.length === 1 && types[0].type === "date", "Repair did not store Date");
printjson(types);
```

Expected: the original write fails, count remains 120, and the repaired probe reports `date`. Do not rely on collection schema validation to enforce all other measurement fields: this collection type does not support it on the baseline.[1] Validate metadata, units, ranges and required fields at ingestion.

## 10. Lab C — observe global TTL cleanup

Create a separate TTL fixture with automatic removal initially disabled. Insert an old series and a fresh series using different metadata. The old timestamp is well beyond the custom bucket span and the eventual 120-second policy.

```javascript
ok(lab.createCollection("ttl_probe", {
  timeseries: {
    timeField: "ts", metaField: "meta",
    bucketMaxSpanSeconds: 60, bucketRoundingSeconds: 60
  }
}), "create ttl_probe");
var ttlAnchor = db.hello().localTime;
lab.ttl_probe.insertMany([
  { ts: new Date(ttlAnchor.getTime() - 3600000),
    meta: { cohort: "expired" }, value: 1 },
  { ts: new Date(ttlAnchor.getTime() + 1800000),
    meta: { cohort: "control" }, value: 2 }
]);
check(lab.ttl_probe.countDocuments({}) === 2, "Expected two TTL fixtures");
ok(lab.runCommand({ collMod: "ttl_probe", expireAfterSeconds: 120 }),
   "enable TTL");
printjson(lab.getCollectionInfos({ name: "ttl_probe" })[0]);
```

The future-dated control is deliberate only for this synthetic drill, so it remains nonexpired throughout the bounded observation window. Production writers must reject unintended future clock skew. The stale fixture is eligible without waiting an hour for a default bucket to age out.

Observe once per poll, using this mongosh block. It may run for five minutes; do not interpret a timeout as proof that TTL is broken.

```javascript
function awaitAbsent(collection, filter, timeoutMs) {
  var deadline = Date.now() + timeoutMs;
  while (true) {
    var remaining = collection.countDocuments(filter);
    printjson({ observedAt: new Date(), remaining: remaining });
    if (remaining === 0) return true;
    if (Date.now() >= deadline) return false;
    sleep(5000);
  }
}
var globalRemoved = awaitAbsent(
  lab.ttl_probe, { "meta.cohort": "expired" }, 300000
);
check(globalRemoved, "TTL observation budget exceeded; capture diagnosis evidence");
check(lab.ttl_probe.countDocuments({ "meta.cohort": "control" }) === 1,
      "Nonexpired control missing");
```

Expected: the expired cohort disappears; the control remains. Record elapsed time and actual collection metadata. With the authorized observer, capture primary-local TTL counters before and after:

```javascript
printjson(db.getSiblingDB("admin").serverStatus().metrics.ttl);
```

Counters are cumulative and cover other namespaces; use deltas as supporting evidence, not as this fixture's exact row count. Compare only the same member and process uptime. TTL work occurs on the primary and deletions replicate.[4] Do not change the cluster's TTL monitor interval to make the exercise pass.

## 11. Lab D — metadata-specific shorter retention

This independent collection retains all measurements for one day, except the `short` tier, which receives a 120-second partial TTL policy. No policy is enabled for the short tier until its fixture count is checked.

```javascript
ok(lab.createCollection("tiered_samples", {
  timeseries: {
    timeField: "ts", metaField: "meta",
    bucketMaxSpanSeconds: 60, bucketRoundingSeconds: 60
  },
  expireAfterSeconds: 86400
}), "create tiered_samples");
var tierAnchor = db.hello().localTime;
lab.tiered_samples.insertMany([
  { ts: new Date(tierAnchor.getTime() - 3600000),
    meta: { tier: "short", host: "test-a" }, value: 1 },
  { ts: new Date(tierAnchor.getTime() - 3600000),
    meta: { tier: "standard", host: "test-b" }, value: 2 }
]);
check(lab.tiered_samples.countDocuments({}) === 2, "Expected two tier fixtures");
lab.tiered_samples.createIndex({ ts: 1 }, {
  name: "short_tier_ttl", expireAfterSeconds: 120,
  partialFilterExpression: { "meta.tier": "short" }
});
check(awaitAbsent(lab.tiered_samples, { "meta.tier": "short" }, 300000),
      "Partial TTL observation budget exceeded");
check(lab.tiered_samples.countDocuments({ "meta.tier": "standard" }) === 1,
      "Standard tier unexpectedly removed");
printjson(lab.tiered_samples.getIndexes());
```

Expected: short tier disappears while the one-hour-old standard tier remains under the one-day collection policy. Treat retention class as controlled metadata. Unauthorized changes to metadata can change deletion behavior.

Removing a partial policy means dropping the owned partial TTL index. Turning off collection-level expiration alone does not remove an independently configured partial TTL index.

```javascript
lab.tiered_samples.dropIndex("short_tier_ttl");
check(!lab.tiered_samples.getIndexes().some(x => x.name === "short_tier_ttl"),
      "Partial policy still exists");
```

This stops future enforcement by that index; it cannot restore the removed short-tier measurement.

## 12. Lab E — disable and restore global retention

Use `collMod` on the logical collection. Capture the original value before changing it.

```javascript
var savedRetention = Number(
  lab.getCollectionInfos({ name: "ttl_probe" })[0].options.expireAfterSeconds
);
check(savedRetention === 120, "Unexpected starting policy");
ok(lab.runCommand({ collMod: "ttl_probe", expireAfterSeconds: "off" }),
   "disable TTL");
var disabledInfo = lab.getCollectionInfos({ name: "ttl_probe" })[0];
printjson(disabledInfo);
check(disabledInfo.options.expireAfterSeconds === undefined ||
      disabledInfo.options.expireAfterSeconds === "off",
      "TTL disable metadata unexpected");
check(lab.ttl_probe.countDocuments({ "meta.cohort": "expired" }) === 0,
      "Previously removed data unexpectedly present");
ok(lab.runCommand({ collMod: "ttl_probe", expireAfterSeconds: savedRetention }),
   "restore TTL");
check(Number(lab.getCollectionInfos({ name: "ttl_probe" })[0]
  .options.expireAfterSeconds) === savedRetention, "Retention restoration failed");
```

Expected: metadata confirms expiration is disabled, then restored to 120. Previously deleted data remains absent. Restoring configuration is not data recovery.[3]

In production, preview the number and distribution of measurements that will become eligible before shortening retention. Use time predicates per retention class as logical candidate estimates; bucket eligibility and cleanup scheduling differ. Review disk I/O, replication lag and application latency during rollout. Pause or revert policy changes when agreed budgets are exceeded, but recover deleted data through a verified backup or retained upstream source.

## 13. Capacity, observability and recovery

Estimate retained logical measurements as `series × measurements/second/series × retention seconds`. For 10,000 hosts sampled once per minute for 30 days, the estimate is 432 million measurements. Apply measured stored bytes per measurement, indexes, replica copies, growth and maintenance headroom separately. Metadata cardinality, compression and lateness make extrapolating raw JSON bytes unreliable.

Track:

| Signal | Operational question |
|---|---|
| Write rate, errors and producer retries | Are valid measurements arriving without uncontrolled replay? |
| Event-time versus ingestion-time lag | Is old backfill consuming retention or entering already expired? |
| Series cardinality and bucket/storage growth | Did metadata changes fragment the workload? |
| Time-window query latency and execution work | Do important query windows remain bounded? |
| Expired logical measurement estimates and TTL progress | Is cleanup falling behind the intended policy? |
| Disk latency, replication lag and application P99 | Is cleanup competing with foreground work? |
| Collection options and partial TTL inventory | Does actual configuration match approved policy? |

An archive must be verified before expiration destroys its source. Reconcile counts and identities over closed time windows; retain handling for late arrivals. Recovery into a collection with active TTL can immediately remove old restored data. Restore into an isolated collection with reviewed expiration settings, verify timestamps and totals, and then decide the intended retention policy.

For schema or bucket redesign, create a new target with the desired options and copying mechanism supported by the exact patch. Quiesce or define an ingestion handoff, copy bounded windows, reconcile per-series totals and redirect applications through configuration. Keep the original until acceptance. Rebuilding a collection does not supply change streams or transactional writes to time series data.[1]

Sharding requires a separate design and version review. In the 8.0 documentation, time-field shard keys are deprecated and resharding support is gated to 8.0.10 or later on every shard.[1] Do not inherit generic sharding commands from Chapters 33–40 without checking time series support for the installed patch.

## 14. Troubleshooting

| Symptom | Evidence to collect | Likely cause | Corrective action and verification |
|---|---|---|---|
| Measurement insert rejected | Timestamp BSON type, server error, original count | String/missing/invalid time field | Repair serialization; verify Date and unchanged failed-write count |
| Expired samples still queryable | Options, bucket span, server time, TTL progress | Bucket window or background backlog | Enforce visibility cutoff; inspect primary cleanup and workload |
| Selected series vanish too early | Global policy and partial index inventory | Shorter effective policy or old event time | Correct policy/producer; recover deleted data from verified source |
| Disabling TTL does not stop all cleanup | Collection metadata plus partial indexes | Independent partial TTL still active | Review and remove the specific approved index; verify inventory |
| Duplicate aggregates | Sample identities and retry evidence | Redelivery without deduplication | Reconcile and fix ingestion contract; do not assume `_id` uniqueness protection |
| High storage growth | Metadata cardinality and late-data pattern | Excess series, sparse/out-of-order writes | Stabilize metadata and benchmark a new model |
| Range query slow | Actual plan, predicates, bucket work and latency | Broad window or unsuitable index | Narrow and test the real query; validate result equivalence |
| Bucket setting cannot be reversed | Original/new options and exact server error | In-place interval reduction unsupported | Build a new target and reconcile before routing change |
| CDC consumer has no supported stream | Collection type and driver/server error | Time series change streams unsupported | Use an upstream event log or reviewed alternate integration design |
| Disk remains allocated after expiration | Logical counts, storage stats and filesystem use | Reusable allocated storage | Revise capacity model; separately review supported space-reclamation options |

## 15. Acceptance record and cleanup

Record each result as passed, failed or not run. Do not convert a timed-out TTL observation into a pass by deleting the fixture manually.

| Check | Expected evidence |
|---|---|
| Environment | Exact patch, FCV, edition, mongosh, primary and UTC time |
| Collection contract | Type, time/meta fields, bucket options, global TTL |
| Reconciliation | 120 rows; node-a 2970/49.5; node-b 4170/69.5 |
| Query | 30 rows, first value 50, last 79; two execution plans |
| Failure and repair | String timestamp rejected; unchanged count; probe BSON Date |
| Global TTL | Expired cohort absent; future control retained; elapsed time |
| Partial TTL | Short cohort absent; standard cohort retained; index inventory |
| Policy recovery | Partial index removed; global setting disabled/restored; deleted data absent |
| Cleanup | Ownership checked; only this database dropped; absence verified |

Before cleanup, save nonsecret output to your evidence record. The retained replica set, operator resources, credentials and other chapter databases stay under their existing ownership lifecycle.

```javascript
check(lab.getName() === labName, "Cleanup namespace mismatch");
check(lab.ownership.findOne({
  _id: "ch65", owner: "mongodb-enterprise-tutorial"
}) !== null, "Ownership marker missing: investigate before cleanup");
ok(lab.dropDatabase(), "drop owned chapter database");
check(db.getSiblingDB(labName).getCollectionInfos().length === 0,
      "Cleanup left collections behind");
print("PASS: chapter-owned database removed");
```

If interrupted before cleanup, inspect the exact owned namespace and its policies before resuming. Do not rerun setup over partially completed fixtures.

### Review questions

1. Why can a sample remain queryable after its logical retention threshold?
2. Why should `sampleId` stay outside metadata, and why does it not enforce uniqueness?
3. What does a partial TTL policy do when its duration exceeds global retention?
4. Which data and configuration can be recovered after a retention reduction?
5. Why is Chapter 64's change-stream consumer unsuitable for this source collection?
6. What extra evidence is needed before choosing a production bucket interval?

## 16. Official references and validation status

1. [MongoDB 8.0 — Time Series Collection Limitations](https://www.mongodb.com/docs/v8.0/core/timeseries/timeseries-limitations/): collection, update, index, integration and sharding boundaries.
2. [MongoDB 8.0 — Set Granularity for Time Series Data](https://www.mongodb.com/docs/v8.0/core/timeseries/timeseries-granularity/): custom intervals and modification rules.
3. [MongoDB 8.0 — Automatic Removal for Time Series Collections](https://www.mongodb.com/docs/v8.0/core/timeseries/timeseries-automatic-removal/): global expiration, disabling it and bucket timing.
4. [MongoDB 8.0 — TTL Indexes](https://www.mongodb.com/docs/v8.0/core/index-ttl/): partial policies, cleanup behavior and monitoring.

Documentation reviewed on 2026-10-11. Fixture design, query assertions, future control, observation budgets and operational acceptance criteria are teaching choices. JavaScript blocks were syntax-checked and deterministic fixture arithmetic was checked during authoring. These checks do not validate server permissions, index execution, bucket behavior, TTL scheduling or cleanup against a live MongoDB instance. No MongoDB server or mongosh runtime was available in the authoring environment.

**Chapter completion:** Written and statically reviewed. Runtime acceptance remains pending until the retained authorized 8.0 lab is executed and the evidence above is recorded.

Previous: [Chapter 64 — Change Streams Resume Tokens and CDC](64-change-streams-resume-tokens-and-cdc.md).  
Next: Chapter 66 — GridFS Capped Collections and Workload Boundaries.
