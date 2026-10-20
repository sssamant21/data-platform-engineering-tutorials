# 34 — Shard Key Selection and Workload Analysis

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 5 — Sharding and Scale  
**Goal:** Measure key cardinality/frequency and workload bounds, run candidate analysis, diagnose a missing supporting index and produce an evidence-based key shortlist.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions/image digest.  
**Deployment:** Owned Chapter 26 `rs26`. Real data/index/analyzer operations run on an unsharded collection; no collection is sharded or resharded here. Community-compatible.  
**Prerequisites:** Chapters 17–24 and 33, healthy original set, no active automation/failure exercise, scoped access plus analyzer privileges where authentication applies.

## 1. Select a workload contract before a key

A shard key influences placement and routing. It must support growth, request patterns and operational constraints together. High cardinality alone does not ensure balanced demand; high query coverage alone does not prevent a hot value.

**Use case:** A tenant event service has one large tenant and a mixture of recent-event lists, exact lookups and global reports. The design must assess whether a tenant can be split while preserving acceptable query cost.

| Dimension | Evidence to collect | Decision question |
|---|---|---|
| Cardinality | Distinct full-key tuples | Is there enough granularity for intended scale? |
| Value frequency | Largest repeated tuple and proportion | Can one indivisible value dominate storage/work? |
| Insert progression | Key behavior over time | Will fresh writes concentrate at one boundary? |
| Read/write bounds | Weighted predicates and update/delete identities | Which operations provide useful routing information? |
| Tenant skew | Bytes, QPS, write rate and resource work | Must a single tenant span shards? |
| Constraints | Uniqueness, arrays, collation, zones and changes | Is the candidate legally and operationally usable? |

Record peak periods and growth, not only a quiet daily average. Do not adopt a key because one example query contains it.

## 2. Candidate tradeoffs

| Candidate | Benefit to investigate | Risk to investigate |
|---|---|---|
| `{status:1}` | Simple categorical filtering | Low distinct count and many repeated values |
| `{createdAt:1}` | Chronological range locality | Increasing inserts can concentrate at the newest boundary |
| `{tenantId:"hashed"}` | Equality-based tenant routing; disperses different tenants | Every occurrence of one tenant still has the same hash |
| `{eventId:"hashed"}` | Many distinct event values; disperses increasing IDs | Tenant-only queries lack the leading field |
| `{tenantId:1,createdAt:1}` | Tenant/time bounds and more distinct tuples | Hot tenant's newest-time boundary can still concentrate writes |
| `{tenantId:1,eventId:1}` | Tenant prefix and precise event equality | Increasing event IDs can create within-tenant boundary pressure |
| `{tenantId:1,eventId:"hashed"}` | Fine-grained values within a tenant | Tenant-only queries can span multiple ranges/shards |

These are candidates, not production prescriptions. Hashing the suffix can help distribute distinct values within a tenant; it cannot split repeated occurrences of the same full key or eliminate a workload dominated by one document.

Supporting query indexes and routing keys serve related but different purposes. A targeted request can still perform expensive local work. A compound prefix can provide bounds without guaranteeing exactly one shard under future placement.

## 3. Constraints and analyzer evidence

Review shard-key index, multikey/array, uniqueness, collation and zone requirements against the exact version. A unique index on an unsharded collection is not proof that the same uniqueness contract is enforceable after sharding. Hashed-index uniqueness and compound hashed-key restrictions also need explicit review.

`analyzeShardKey` supports candidate analysis on an ordinary replica set in this baseline. Key-characteristic metrics come from document analysis; read/write-distribution metrics require captured query samples. Its supporting-index rules differ from the exact index required for actual sharding.

This lab uses full document sampling for a small fixture, with `readWriteDistribution:false` initially. It does not present empty query metrics as proof of efficient routing. Optional read sampling later records whether usable samples were actually captured.

On an actual sharded cluster, run these cluster analysis commands through `mongos`, not directly against a `--shardsvr` replica set. This lab does not enable sharding, change FCV or alter any process-wide sampling parameter.

## 4. Environment and ownership

Use the original Compose folder and independent client:

```bash
docker compose -p mongodb-ch26 -f compose.yaml ps
docker run --rm -it --network mongodb-ch26_replica mongo:8.0 mongosh "mongodb://a:27017,b:27017,c:27017/?replicaSet=rs26&readPreference=primary&serverSelectionTimeoutMS=5000"
```

Use the approved image digest and record versions/resource headroom. No additional ports are published. Analyzer privileges are separate from ordinary CRUD/index privileges; authenticated deployments need approved access. Permission errors are not evidence of an empty dataset or a good key.

```javascript
const hosts34 = ["a:27017", "b:27017", "c:27017"];
const name34 = "mongodb_enterprise_tutorial_ch34";
const lab34 = db.getSiblingDB(name34);
const wc34 = { w: "majority", j: true, wtimeout: 10000 };
function check34(condition, message) { if (!condition) throw new Error(message); }
function healthy34(s) {
  return s && s.ok === 1 && s.set === "rs26" && s.members.length === 3 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "PRIMARY").length === 1 &&
    s.members.filter(m => m.health === 1 && m.stateStr === "SECONDARY").length === 2;
}
function direct34(host) {
  check34(hosts34.includes(host), "Host outside owned lab");
  const c = new Mongo("mongodb://" + host + "/?directConnection=true&serverSelectionTimeoutMS=5000");
  c.setReadPref("secondaryPreferred");
  return c;
}
const hello34 = db.adminCommand({ hello: 1 });
check34(hello34.setName === "rs26" && hello34.msg !== "isdbgrid", "Unexpected deployment");
check34(healthy34(db.adminCommand({ replSetGetStatus: 1 })), "Topology not ready");
check34(lab34.getCollectionNames().length === 0, "Chapter database exists; inspect before rerunning");
const originalConfig34 = EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config);
printjson({ version: db.version(), deployment: "unsharded rs26 analysis" });
```

## 5. Seed a skewed but deterministic dataset

The fixture has 600 events: 420 for `tenant-0`, and 20 each for `tenant-1` through `tenant-9`. Event IDs and creation times increase with insertion order. All data is synthetic.

```javascript
check34(lab34.createCollection("events").ok === 1, "Collection creation failed");
check34(lab34.createCollection("workload_shapes").ok === 1, "Workload collection creation failed");
const events34 = lab34.events;
const epoch34 = new Date("2026-01-01T00:00:00Z").getTime();
function expectedEvent34(i) {
  return { _id: "event-" + String(i).padStart(4, "0"),
    eventId: "event-" + String(i).padStart(4, "0"), seq: i,
    tenantId: i < 420 ? "tenant-0" : "tenant-" + (1 + Math.floor((i - 420) / 20)),
    createdAt: new Date(epoch34 + i * 1000),
    status: i % 3 === 0 ? "open" : "closed", revision: 1 };
}
for (let batch = 0; batch < 6; batch++) {
  const docs = Array.from({ length: 100 }, (_, j) => expectedEvent34(batch * 100 + j));
  check34(events34.insertMany(docs, { writeConcern: wc34 }).acknowledged,
          "Fixture batch not acknowledged; reconcile IDs");
}
function validFixture34(rows) {
  return rows.length === 600 && rows.every((r, i) => {
    const e = expectedEvent34(i);
    return r._id === e._id && r.eventId === e.eventId && Number(r.seq) === i &&
      r.tenantId === e.tenantId && r.createdAt.getTime() === e.createdAt.getTime() &&
      r.status === e.status && Number(r.revision) === 1;
  });
}
function verifyAll34() {
  for (const host of hosts34) {
    const c = direct34(host).getDB(name34).events;
    const end = Date.now() + 30000;
    let rows;
    do { rows = c.find().sort({ seq: 1 }).toArray(); if (validFixture34(rows)) break; sleep(500); }
    while (Date.now() < end);
    check34(validFixture34(rows), "Fixture differs on " + host);
  }
}
verifyAll34();
```

Expected: every member has the exact 600 identities and payloads. A majority acknowledgement alone does not establish every secondary's readiness; verify it before optional secondary-side analysis.

## 6. Measure full-key cardinality and frequency

Use bounded aggregation on the owned small collection:

```javascript
function frequency34(groupKey) {
  return events34.aggregate([
    { $group: { _id: groupKey, frequency: { $sum: 1 } } },
    { $sort: { frequency: -1 } }
  ]).toArray();
}
const tenantFrequency34 = frequency34("$tenantId");
const statusFrequency34 = frequency34("$status");
const eventFrequency34 = frequency34("$eventId");
const tenantEventFrequency34 = frequency34({ tenantId: "$tenantId", eventId: "$eventId" });
check34(tenantFrequency34.length === 10 && Number(tenantFrequency34[0].frequency) === 420,
        "Tenant skew differs");
check34(statusFrequency34.length === 2 && Number(statusFrequency34[0].frequency) === 400,
        "Status cardinality/frequency differs");
check34(eventFrequency34.length === 600 && eventFrequency34.every(r => Number(r.frequency) === 1),
        "Event cardinality differs");
check34(tenantEventFrequency34.length === 600, "Compound cardinality differs");
printjson({ tenantDistinct: tenantFrequency34.length, topTenant: tenantFrequency34[0],
  topTenantDocumentPercent: 100 * Number(tenantFrequency34[0].frequency) / 600,
  statusDistinct: statusFrequency34.length, eventDistinct: eventFrequency34.length,
  tenantEventDistinct: tenantEventFrequency34.length });
```

Expected: 10 tenants, hot tenant 70% of documents, two status values and 600 distinct event/full compound values. Document percentage is not QPS, bytes or CPU percentage. Production analysis must separately collect request demand and record size.

Hashing does not create new distinct original tenant values: the repeated hot tenant remains one repeated hashed value. More distinct suffix tuples provide splitting granularity, but do not by themselves prove balanced placement or insert throughput.

## 7. Build supporting indexes and run real key-characteristic analysis

Create only indexes on the owned fixture. These ascending indexes support candidate analysis; they do not automatically satisfy the exact hashed index specification required for actual sharding.

```javascript
const indexSpecs34 = [
  { key: { status: 1 }, name: "candidate_status" },
  { key: { createdAt: 1 }, name: "candidate_createdAt" },
  { key: { tenantId: 1 }, name: "candidate_tenant" },
  { key: { eventId: 1 }, name: "candidate_event" },
  { key: { tenantId: 1, createdAt: 1 }, name: "candidate_tenant_time" },
  { key: { tenantId: 1, eventId: 1 }, name: "candidate_tenant_event" }
];
for (const spec of indexSpecs34) events34.createIndex(spec.key, { name: spec.name });
const candidates34 = [
  { name: "status-ranged", key: { status: 1 }, distinct: 2 },
  { name: "time-ranged", key: { createdAt: 1 }, distinct: 600 },
  { name: "tenant-hashed", key: { tenantId: "hashed" }, distinct: 10 },
  { name: "event-hashed", key: { eventId: "hashed" }, distinct: 600 },
  { name: "tenant-time", key: { tenantId: 1, createdAt: 1 }, distinct: 600 },
  { name: "tenant-event", key: { tenantId: 1, eventId: 1 }, distinct: 600 },
  { name: "tenant-event-hashed", key: { tenantId: 1, eventId: "hashed" }, distinct: 600 }
];
const keyResults34 = [];
for (const candidate of candidates34) {
  const result = events34.analyzeShardKey(candidate.key, {
    keyCharacteristics: true, readWriteDistribution: false, sampleRate: 1
  });
  check34(result.keyCharacteristics, "Characteristic metrics missing: " + candidate.name);
  check34(Number(result.keyCharacteristics.numDistinctValues) === candidate.distinct,
          "Analyzer cardinality differs: " + candidate.name);
  keyResults34.push({ candidate: candidate.name, key: candidate.key,
    metrics: result.keyCharacteristics });
}
printjson(keyResults34);
```

This exercises the actual analyzer, not a custom hash function. Record sampled-document count, repeated-value metrics and monotonicity output. Do not require monotonicity to be known for every candidate: index/candidate form and implementation limitations can make it `unknown`. It is not the same as proving a future write hotspot.

Full sampling is appropriate only for this small owned fixture. On production datasets, review analyzer overhead, supporting indexes, sampling scope and read preference; do not blindly use `sampleRate:1` across large collections. Cardinality equality assertions here rely on a frozen synthetic dataset, not concurrent production data.

## 8. Store a weighted workload inventory

This inventory is a synthetic planning input, separate from server-captured query samples:

```javascript
const shapeRows34 = [
  { _id: "tenant-recent", count: 600, equalityFields: ["tenantId"], rangeFields: ["createdAt"] },
  { _id: "tenant-event", count: 250, equalityFields: ["tenantId", "eventId"], rangeFields: [] },
  { _id: "event-only", count: 100, equalityFields: ["eventId"], rangeFields: [] },
  { _id: "global-status", count: 50, equalityFields: ["status"], rangeFields: [] }
];
check34(lab34.workload_shapes.insertMany(shapeRows34, { writeConcern: wc34 }).acknowledged,
        "Workload inventory not acknowledged");
const weightedRequests34 = shapeRows34.reduce((n, r) => n + Number(r.count), 0);
check34(weightedRequests34 === 1000, "Workload weights differ");
function boundClass34(candidate, shape) {
  const fields = Object.keys(candidate.key);
  let prefix = 0;
  while (prefix < fields.length && shape.equalityFields.includes(fields[prefix])) prefix++;
  if (prefix === fields.length) return "full-key-equality";
  if (prefix > 0) return "leading-equality-prefix";
  if (candidate.key[fields[0]] !== "hashed" && shape.rangeFields.includes(fields[0]))
    return "leading-range";
  return "no-leading-bound-in-model";
}
function workloadSummary34(candidate) {
  const counts = {};
  for (const shape of shapeRows34) {
    const category = boundClass34(candidate, shape);
    counts[category] = (counts[category] || 0) + Number(shape.count);
  }
  return { candidate: candidate.name, weightedRequests: weightedRequests34, counts };
}
const weightedResults34 = candidates34.map(workloadSummary34);
check34(weightedResults34.find(r => r.candidate === "tenant-hashed")
  .counts["full-key-equality"] === 850, "Tenant equality coverage differs");
check34(weightedResults34.find(r => r.candidate === "event-hashed")
  .counts["full-key-equality"] === 350, "Event equality coverage differs");
check34(weightedResults34.find(r => r.candidate === "tenant-event-hashed")
  .counts["leading-equality-prefix"] === 600, "Compound prefix coverage differs");
printjson(weightedResults34);
```

This classifier recognizes only the declared equality/range fields. It does not parse MongoDB expressions or predict an executed target count. A leading equality prefix can span shards; a leading range can intersect many ranges. Keep these labels distinct from single-shard/multi-shard/scatter-gather metrics returned by real analysis.

## 9. Execute representative fixture queries

Check correctness before using query shapes as design evidence:

```javascript
const recent34 = events34.find({ tenantId: "tenant-0",
  createdAt: { $gte: new Date(epoch34 + 400000), $lt: new Date(epoch34 + 420000) } })
  .sort({ createdAt: 1 }).toArray();
check34(recent34.length === 20 && Number(recent34[0].seq) === 400 &&
  Number(recent34[19].seq) === 419, "Tenant/time query differs");
const exact34 = events34.findOne({ tenantId: "tenant-1", eventId: "event-0420" });
check34(exact34 && Number(exact34.seq) === 420, "Exact tenant/event query differs");
check34(events34.findOne({ eventId: "event-0420" }).tenantId === "tenant-1",
        "Event-only lookup differs");
check34(events34.countDocuments({ status: "open" }) === 200, "Global status query differs");
printjson(events34.find({ tenantId: "tenant-0", createdAt: { $gte: new Date(epoch34 + 400000) } })
  .sort({ createdAt: 1 }).hint("candidate_tenant_time").explain("executionStats"));
```

The explain checks local index work on `rs26`; it cannot show actual sharded destinations. Record result correctness, keys/documents examined and sort behavior without converting this tiny experiment into a production latency benchmark.

An event-only lookup can be locally indexed while providing no leading tenant bound for a tenant-first compound key. Local index efficiency and cluster routing must be assessed separately.

## 10. Failure exercise: candidate analysis without its supporting index

Drop only the owned compound candidate index and reproduce a characteristics-only analysis failure. Restore it in `finally` before proceeding:

```javascript
const savedIndex34 = events34.getIndexes().find(i => i.name === "candidate_tenant_event");
check34(savedIndex34, "Repair source index missing");
try {
  events34.dropIndex(savedIndex34.name);
  let missingIndexRejected34 = false;
  try {
    const missing34 = events34.analyzeShardKey({ tenantId: 1, eventId: 1 }, {
      keyCharacteristics: true, readWriteDistribution: false, sampleRate: 1
    });
    missingIndexRejected34 = missing34.ok === 0 && Number(missing34.code) === 20;
    printjson(missing34);
  } catch (error) {
    printjson({ code: error.code, message: error.message });
    missingIndexRejected34 = Number(error.code) === 20;
  }
  check34(missingIndexRejected34, "Expected IllegalOperation for missing supporting index");
} finally {
  events34.createIndex(savedIndex34.key, { name: savedIndex34.name });
}
const repairedAnalysis34 = events34.analyzeShardKey({ tenantId: 1, eventId: 1 }, {
  keyCharacteristics: true, readWriteDistribution: false, sampleRate: 1
});
check34(Number(repairedAnalysis34.keyCharacteristics.numDistinctValues) === 600,
        "Restored index/analyzer verification failed");
verifyAll34();
```

Diagnosis: the analysis contract requires a supporting index. Correction: restore the exact small fixture index and reverify its candidate metrics. This is not proof that actual sharding would accept every candidate's current index form.

If a different error occurs, preserve it rather than claiming the intended failure passed. Permission, endpoint, version and data issues must be distinguished. The finally block restores this deliberately nonunique simple fixture index; production index restoration must preserve all relevant options.

## 11. Optional bounded read sampling

This section changes sampling only for the newly created chapter namespace. It performs bounded reads and restores the previous sampling configuration. It does not claim production workload representativeness or sampled-write coverage.

```javascript
let samplingChanged34 = false;
let samplingPrior34 = null;
let sampleEvidence34 = null;
try {
  const enabled34 = db.adminCommand({ configureQueryAnalyzer: name34 + ".events",
    mode: "full", samplesPerSecond: 5 });
  check34(enabled34.ok === 1, "Query sampling configuration failed");
  samplingPrior34 = enabled34.oldConfiguration || null;
  samplingChanged34 = true;
  check34(!enabled34.oldConfiguration || enabled34.oldConfiguration.mode !== "full",
          "Unexpected active sampling on fresh namespace; inspect ownership");
  for (let i = 0; i < 200; i++) {
    const tenant = "tenant-" + (i % 10);
    if (i % 4 === 0) events34.find({ eventId: "event-" + String(i % 600).padStart(4, "0") }).limit(1).toArray();
    else events34.find({ tenantId: tenant }).limit(5).toArray();
    sleep(200);
  }
  sampleEvidence34 = events34.analyzeShardKey({ tenantId: 1, eventId: "hashed" }, {
    keyCharacteristics: false, readWriteDistribution: true
  });
  printjson(sampleEvidence34);
} finally {
  if (samplingChanged34) {
    const restore34 = { configureQueryAnalyzer: name34 + ".events",
      mode: samplingPrior34 && samplingPrior34.mode === "full" ? "full" : "off" };
    if (restore34.mode === "full") restore34.samplesPerSecond = samplingPrior34.samplesPerSecond;
    const disabled34 = db.adminCommand(restore34);
    check34(disabled34.ok === 1, "Sampling restoration failed; resolve before leaving lab");
    samplingChanged34 = false;
    printjson(disabled34);
  }
}
```

The loop makes 200 reads with about 40 seconds of deliberate pacing plus request time. Sampling activation/refresh and asynchronous persistence can leave few or no samples in a short run. Inspect actual sample counts and record insufficient evidence where appropriate; do not repeatedly run unbounded traffic until percentages look convincing.

The sampled mix differs from the weighted planning inventory. Compare their scopes explicitly. No update/delete sample mix is created here, so missing/zero write-distribution evidence does not prove optimal write routing. Document sampling rate and query samples-per-second are separate controls.

Because this database/collection is newly owned and fresh, normal restoration is `mode:"off"`. Unexpected prior sampling configuration indicates a violated preflight assumption; preserve it and resolve ownership before continuing. If optional analysis is unsupported or unauthorized, record the response and leave it not exercised, with any successful sampling change reverted.

## 12. Decision memo for the synthetic service

| Candidate | Fixture/workload evidence | Decision for further testing |
|---|---|---|
| status-ranged | Two values; largest repeats 400/600 | Reject as the sole scale-out key for this service |
| time-ranged | 600 values, increasing time; 60% shapes have time ranges | Assess append-boundary pressure; not preferred without further design |
| tenant-hashed | Ten values; one tenant 70% of documents; 85% full-key equality | Tenant routing useful, but hot tenant remains concentrated |
| event-hashed | 600 values; 35% full-key equality coverage | Distribution candidate with tenant-query routing cost |
| tenant-time | 600 full tuples; 85% tenant-prefix/full-bound workload | Locality candidate; verify hot tenant's newest-write pressure |
| tenant-event | 600 full tuples; 25% full equality, 60% prefix | Verify within-tenant insert progression and placement |
| tenant-event-hashed | Same tuple count and workload equality categories | Shortlist if splitting a large tenant is required and tenant-list costs acceptable |

The shortlist is a hypothesis for Chapter 35 and subsequent routing/load labs. It is not authorization to shard a production collection. Before selecting it, assess actual peak workload, tenant bytes/QPS, uniqueness, query/transaction semantics, zones, missing values and growth.

Persist the real analyzer output and assumptions in your design review. Specify acceptance targets for per-shard work, target counts, latency, ingestion, migration and recovery. Do not collapse these into an arbitrary “best key” score.

## 13. Troubleshooting and production analysis

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Analyzer missing characteristics | Raw response and supporting index | Unsupported/missing index or command options | Verify characteristics-only contract and index rules |
| Analyzer returns Unauthorized | Identity and privilege/error | CRUD access does not imply analysis access | Use approved analyzer permissions |
| Distribution values zero/missing | Sample counts and sampling state | No usable sampled operations | Mark evidence insufficient, not efficient routing |
| Monotonicity unknown | Candidate/index form and returned metrics | Documented analysis limitation | Use insert/time evidence; do not invent a result |
| Hashed tenant still hot | Repeated tenant values and demand | Same value maps to same hash | Consider full-key granularity and query tradeoffs |
| High cardinality but new writes concentrated | Key progression and real hot-range metrics | Increasing boundary or hot prefix | Test insertion patterns under representative load |
| Local explain good but many shards queried | Router target evidence and predicate | Index efficiency mistaken for routing | Review leading bounds and placement |
| Cannot enforce intended uniqueness after sharding | Unique index/key definitions | Cluster uniqueness constraints | Redesign/verify contract before conversion |
| Sampling remains enabled | Configure response, process termination | Cleanup failed or shell interrupted | Restore this owned namespace's sampling state |

Schedule production analysis deliberately; account for query-sample storage/retention, sensitive predicates, index-build resource work and monitoring. Do not modify internal sampled-query collections directly. Fresh collection names do not grant authority to inspect unrelated production data.

## 14. Cleanup and verification

If the shell was interrupted during optional sampling, run the namespace-specific off command before cleanup. It is safe to issue for this owned existing fixture:

```javascript
const samplingOff34 = db.adminCommand({ configureQueryAnalyzer: name34 + ".events", mode: "off" });
check34(samplingOff34.ok === 1, "Sampling not disabled; preserve response and resolve before cleanup");
verifyAll34();
check34(events34.getIndexes().some(i => i.name === "candidate_tenant_event"),
        "Failure exercise index not restored");
const storedShapes34 = lab34.workload_shapes.find().toArray();
check34(storedShapes34.length === 4 && storedShapes34.every(s => {
  const expected = shapeRows34.find(e => e._id === s._id);
  return expected && Number(s.count) === expected.count &&
    JSON.stringify(s.equalityFields) === JSON.stringify(expected.equalityFields) &&
    JSON.stringify(s.rangeFields) === JSON.stringify(expected.rangeFields);
}), "Workload inventory differs");
check34(EJSON.stringify(db.adminCommand({ replSetGetConfig: 1 }).config) ===
        originalConfig34, "Replica configuration changed");
check34(healthy34(db.adminCommand({ replSetGetStatus: 1 })), "Topology not ready");
check34(lab34.getName() === "mongodb_enterprise_tutorial_ch34",
        "Refusing cleanup outside the Chapter 34 training database");
check34(lab34.dropDatabase().ok === 1, "Chapter cleanup failed");
for (const host of hosts34) {
  const d = direct34(host).getDB(name34);
  const end = Date.now() + 30000;
  while (Date.now() < end && d.getCollectionNames().length !== 0) sleep(500);
  check34(d.getCollectionNames().length === 0, "Cleanup not applied: " + host);
}
```

If sampling commands are unavailable/unauthorized and the optional section never successfully changed sampling, omit the off command and record why; do not treat inability to configure it as proof a change occurred. If sampling was enabled, resolve restoration before finishing. Dropping the owned collection also disables its sampling configuration, but explicit restoration gives clearer evidence.

Retain the original replica set and preserve analysis outputs. Internal sample records expire according to the configured server policy; do not remove system collections to accelerate cleanup. No shard key, balancer, FCV, role, topology, network or storage setting changed.

## 15. Acceptance and evidence

- [ ] Recorded versions, ownership, healthy topology and analyzer permissions.
- [ ] Reconciled all 600 deterministic documents on every member.
- [ ] Verified hot-tenant frequency, low-cardinality status and full compound cardinality.
- [ ] Created owned indexes and captured real candidate key-characteristic output.
- [ ] Kept monotonicity unknown/sample limitations explicit where returned.
- [ ] Compared weighted equality/prefix/range categories without claiming target counts.
- [ ] Verified local query correctness and index explain separately from routing.
- [ ] Reproduced missing-index analysis failure and restored its exact fixture index.
- [ ] Recorded optional query sampling as exercised/not exercised with actual sample counts.
- [ ] Produced a conditional shortlist and documented remaining production checks.
- [ ] Restored sampling if changed, verified unchanged topology and scoped cleanup.

**Evidence:** fixture/frequency results, index specs, analyzer output, weighted shapes, query assertions/explain, failure/repair response, optional sampling results and cleanup. Runtime validation remains pending until executed. A replica-set candidate analysis does not validate actual sharded distribution, future target counts or production throughput. Chapter 35 builds the live cluster for the next tests.

## 16. Review questions

1. Why does hashing tenantId not divide a single repeated tenant value?
2. How can a compound suffix increase splitting granularity without guaranteeing balanced load?
3. Why are document frequency and request demand separate measurements?
4. What differs between an analyzer-supporting index and an actual hashed shard-key index?
5. Why is a prefix-bound category not a promise of one destination shard?
6. What should zero query-distribution metrics mean without usable samples?
7. Why can monotonicity remain unknown even when document chronology is known?
8. Which production constraints can invalidate an otherwise promising candidate?

## 17. Official references

- [MongoDB 8.0: choose a shard key](https://www.mongodb.com/docs/v8.0/core/sharding-choose-a-shard-key/)
- [MongoDB 8.0: analyzeShardKey](https://www.mongodb.com/docs/v8.0/reference/command/analyzeShardKey/)
- [MongoDB 8.0: configureQueryAnalyzer](https://www.mongodb.com/docs/v8.0/reference/command/configureQueryAnalyzer/)
- [MongoDB 8.0: hashed sharding](https://www.mongodb.com/docs/v8.0/core/hashed-sharding/)
- [MongoDB 8.0: shard keys](https://www.mongodb.com/docs/v8.0/core/sharding-shard-key/)

---

Previous: [Chapter 33 — Sharded Cluster Architecture](33-sharded-cluster-architecture.md)  
Next: **[Chapter 35 — Build a Sharded Lab Cluster](35-build-a-sharded-lab-cluster.md)**.
