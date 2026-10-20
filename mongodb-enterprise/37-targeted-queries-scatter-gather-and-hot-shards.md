# 37 — Targeted Queries Scatter Gather and Hot Shards

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 5 — Sharding and Scale  
**Goal:** Verify actual query fan-out, separate routing from shard-local indexing, reproduce a missing-prefix lookup and compare tenant-wide versus single-document request concentration before/after a range move.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions and reuse the pinned Chapter 35 image digest.  
**Deployment:** Retained isolated Chapter 35 cluster: `r1`/`r2`, `cfg35`, `shard35a`/`shard35b`. Community-compatible.  
**Prerequisites:** Chapters 33–36, healthy original topology and the 1001-document Chapter 35 fixture, Chapter 36 cleanup completed, no concurrent migration/resharding/workload exercise, and approved cluster administration/scoped CRUD privileges where authentication applies.

## 1. Routing, local work and demand are different questions

**Use case:** A tenant event API returns one event by its globally generated event ID. A local index makes that lookup efficient on each shard, but the API omits the tenant prefix of the shard key. The router still contacts both shards. Meanwhile, a large fraction of requests belongs to one tenant, so equal stored document counts do not imply equal request demand.

Diagnose three separate dimensions: which shards receive an operation, how much work each selected shard performs, and how requests concentrate over time. An operation can be targeted and expensive, or broadcast and locally efficient. A query returning one document does not prove that only one shard participated.

The lab uses a compound ranged key `{tenantId:1,eventId:1}`. It first places tenants 0–4 on A and tenants 5–9 on B. It then splits tenant 0 across A/B and repeats routing and workload checks. No production key is selected from these synthetic results.

## 2. Query-shape expectations

| Predicate | Routing information | Initial fixture expectation |
|---|---|---|
| Exact tenant plus event | Full compound key | One shard |
| Tenant equality | Leading key prefix | One shard under the initial placement |
| Event equality alone | Missing leading key field | Both shards |
| Tenant 0 or tenant 9 | Two separated prefix bounds | Both shards |
| Tenant range covering 4 and 5 | Range crosses the placement boundary | Both shards |
| Global status predicate | No shard-key bound | Both shards |

These are hypotheses to verify with real explain output and current catalog ownership. After tenant 0 spans A/B, its prefix-only query contacts both shards. Full-key point queries remain targeted. Prefix inclusion is useful but does not guarantee one shard for every future placement.

Read preference selects a replica-set member within a targeted shard; it does not supply a missing shard-key predicate. A local `hint` selects an index; it does not rewrite catalog placement. The lab uses primary reads, complete cursor consumption and no application writes during its measurements.

## 3. What constitutes evidence

| Evidence | Purpose | Interpretation limit |
|---|---|---|
| Catalog UUID/bounds/owners | Establish current placement | Not a request trace |
| Winning and executed explain shard names | Establish participating shards for that explained query | Not all production query shapes |
| Keys/docs examined and returned | Inspect local execution work | Examined work is not the same as fan-out |
| Fully consumed query results | Verify the application result contract | Does not measure sustained capacity |
| Bounded workload timings | Record this client/environment's elapsed times | Not a concurrency test or production p99 |
| Request counts assigned from frozen catalog | Model concentration for known full-key requests | Not observed per-shard server counters |

Keep the full raw explain alongside any summary. Explain format varies across engines and patch versions; unsupported parsing must produce an explicit review step, not an invented target count. Explain ignores the plan cache and does not populate it with its winner, so its execution time should not be treated as normal application latency.

## 4. Verify the retained cluster and clean namespace

Use **Bash** in the original `mongodb-ch35` folder with `.env`, `compose.yaml`, `scripts/lib35.js` and `scripts/verify35.js`. If paused, follow the Chapter 36 resume sequence. If the cluster was removed, rebuild and complete Chapter 35 first.

```bash
dc() { docker compose -p mongodb-ch35 -f compose.yaml "$@"; }
set -a
source .env
set +a
dc ps -a
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
```

Do not start this chapter if the prior zone exercise left owned ranges/memberships or failed its cleanup. Keep the same isolated network and synthetic-data boundary; no host ports, profiling changes, query sampling or background traffic are needed.

## 5. Shared fixture and explain helpers

Save **`scripts/lib37.js`**. It loads the Chapter 35 topology helpers once. Subsequent interactive blocks run in the same session; standalone verification/cleanup uses a fresh process.

```javascript
load("/scripts/lib35.js");
const name37 = "mongodb_enterprise_tutorial_ch37";
const ns37 = name37 + ".events";
const lab37 = db.getSiblingDB(name37);
const catalog37 = db.getSiblingDB("config");
const events37 = lab37.events;
const wc37 = { w: "majority", j: true, wtimeout: 10000 };
function id37(i) { return "event-" + String(i).padStart(4, "0"); }
function tenant37(i) { return "tenant-" + Math.floor(i / 100); }
function fixture37() {
  return Array.from({ length: 1000 }, (_, i) => ({
    _id: id37(i), eventId: id37(i), tenantId: tenant37(i), seq: i,
    status: i % 3 === 0 ? "open" : "closed", revision: 1, payload: "x".repeat(128)
  }));
}
function verify37() {
  const docs = events37.find({}).sort({ seq: 1 }).maxTimeMS(5000).toArray();
  check35(docs.length === 1000, "Wrong total");
  for (let i = 0; i < 1000; i++) {
    const d = docs[i];
    check35(d._id === id37(i) && d.eventId === id37(i) && d.tenantId === tenant37(i) &&
      d.seq === i && d.status === (i % 3 === 0 ? "open" : "closed") && d.revision === 1 &&
      d.payload === "x".repeat(128), "Fixture mismatch at " + i);
  }
  check35(docs.reduce((sum, d) => sum + d.seq, 0) === 499500, "Sequence sum mismatch");
  for (let i = 0; i < 10; i++) {
    check35(docs.filter(d => d.tenantId === "tenant-" + i).length === 100, "Tenant count mismatch");
  }
  return { documents: docs.length, seqSum: 499500, perTenant: 100 };
}
function meta37() {
  const m = catalog37.collections.findOne({ _id: ns37 });
  check35(m && m.uuid && m.key.tenantId === 1 && m.key.eventId === 1 &&
          m.unsplittable !== true, "Expected compound-key sharded collection");
  return m;
}
function chunks37() { return catalog37.chunks.find({ uuid: meta37().uuid }).toArray(); }
function equal37(a, b) { return EJSON.stringify(a) === EJSON.stringify(b); }
function exact37(min, max) {
  const found = chunks37().filter(c => equal37(c.min, min) && equal37(c.max, max));
  check35(found.length === 1, "Expected exact fixture interval; inspect current catalog");
  return found[0];
}
function split37(key) {
  if (!chunks37().some(c => equal37(c.min, key))) {
    const result = sh.splitAt(ns37, key);
    check35(result.ok === 1, "Split failed: " + EJSON.stringify(result));
  }
}
function move37(min, max, to) {
  check35(["shard35a", "shard35b"].includes(to), "Unexpected destination");
  const c = exact37(min, max);
  if (c.shard !== to) {
    const result = db.adminCommand({ moveChunk: ns37, bounds: [c.min, c.max], to });
    check35(result.ok === 1, "Move failed: " + EJSON.stringify(result));
    wait35("owner " + to, () => exact37(min, max).shard === to);
    printjson({ from: c.shard, to, bounds: [c.min, c.max], result });
  }
}
function names37(tree) {
  const found = new Set();
  function walk(v) {
    if (!v || typeof v !== "object") return;
    if (typeof v.shardName === "string") found.add(v.shardName);
    for (const [key, child] of Object.entries(v)) {
      if (!["rejectedPlans", "allPlansExecution"].includes(key)) walk(child);
    }
  }
  walk(tree);
  return [...found].sort();
}
function explain37(label, filter, expectedNames, expectedReturned, hint) {
  let cursor = events37.find(filter).comment("chapter37:" + label).maxTimeMS(5000);
  if (hint) cursor = cursor.hint(hint);
  const raw = cursor.explain("executionStats");
  printjson({ label, raw });
  const planned = names37(raw.queryPlanner && raw.queryPlanner.winningPlan);
  const executed = names37(raw.executionStats && raw.executionStats.executionStages);
  check35(planned.length > 0 && executed.length > 0,
          "Unsupported explain layout; inspect raw result before adapting parser");
  check35(equal37(planned, [...expectedNames].sort()) && equal37(executed, planned),
          "Unexpected planned/executed shards for " + label);
  check35(raw.executionStats.nReturned === expectedReturned, "Explain result count mismatch");
  const summary = { label, planned, executed, returned: raw.executionStats.nReturned,
    keysExamined: raw.executionStats.totalKeysExamined ?? null,
    docsExamined: raw.executionStats.totalDocsExamined ?? null,
    executionTimeMillis: raw.executionStats.executionTimeMillis ?? null };
  printjson(summary);
  return summary;
}
```

The parser traverses only the winning-plan and executed-stage subtrees. It skips rejected candidates rather than presenting optimizer trials as actual routing. It requires explicit shard-name evidence on this baseline. If your version nests explain differently, preserve raw output and adapt these two entry points after checking official format; do not replace a missing name with a guessed shard.

## 6. Create an owned fixture and freeze its placement controls

Connect through the routers:

```bash
docker run --rm -it --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017,r2:27017/?readPreference=primary&serverSelectionTimeoutMS=5000'
```

Sections 6–12 run in this session:

```javascript
load("/scripts/lib37.js");
router35();
for (const spec of sets35) wait35("preflight " + spec.name, () => ready35(spec));
check35(lab37.getCollectionNames().length === 0 &&
  !catalog37.collections.findOne({ _id: ns37 }), "Chapter namespace exists; inspect rerun");
check35(catalog37.tags.countDocuments({ ns: ns37 }) === 0 &&
  catalog37.tags.countDocuments({ tag: { $in: ["CH36_EAST", "CH36_WEST"] } }) === 0 &&
  catalog37.shards.countDocuments({ tags: { $in: ["CH36_EAST", "CH36_WEST"] } }) === 0,
  "Unexpected chapter zone configuration; complete prior cleanup");
const originalPolicy37 = {
  _id: "ownership", namespace: ns37, phase: "owned-fresh-namespace",
  globalBalancer: sh.getBalancerState(),
  globalSettings: catalog37.settings.findOne({ _id: "balancer" }),
  shardTags: catalog37.shards.find({}).toArray().map(s =>
    ({ shard: s._id, tags: [...(s.tags || [])].sort() })),
  priorCollectionBalancing: true, priorAutoMerger: true
};
check35(lab37.control.insertOne(originalPolicy37, { writeConcern: wc37 }).acknowledged,
        "Ownership record not acknowledged");
check35(lab37.createCollection("events").ok === 1, "Collection create failed");
events37.createIndex({ tenantId: 1, eventId: 1 }, { name: "tenant_event" });
const sharded37 = db.adminCommand({ shardCollection: ns37, key: { tenantId: 1, eventId: 1 } });
check35(sharded37.ok === 1, "Sharding failed: " + EJSON.stringify(sharded37));
sh.disableBalancing(ns37);
check35(meta37().noBalance === true && meta37().allowMigrations !== false,
        "Unexpected balancing/migration policy");
const paused37 = db.adminCommand({ configureCollectionBalancing: ns37, enableAutoMerger: false });
check35(paused37.ok === 1, "AutoMerger pause failed");
check35(lab37.control.updateOne({ _id: "ownership" },
  { $set: { uuid: meta37().uuid, phase: "automation-paused" } },
  { writeConcern: wc37 }).matchedCount === 1, "Checkpoint failed");
const batch37 = events37.insertMany(fixture37(), { ordered: true, writeConcern: wc37 });
check35(batch37.acknowledged && Object.keys(batch37.insertedIds).length === 1000,
        "Partial fixture; reconcile before replay");
printjson(verify37());
printjson(originalPolicy37);
printjson({ server: db.version(), shell: version() });
```

Save the ownership record outside the database with your evidence. Collection balancing and AutoMerger are paused only for this new namespace to keep comparisons stable. Global policy remains unchanged. No zones are added. A timeout can leave a write or migration committed; inspect persisted IDs/catalog state before replaying.

## 7. Establish equal document placement

```javascript
const allMin37 = { tenantId: MinKey, eventId: MinKey };
const middle37 = { tenantId: "tenant-5", eventId: MinKey };
const allMax37 = { tenantId: MaxKey, eventId: MaxKey };
split37(middle37);
move37(allMin37, middle37, "shard35a");
move37(middle37, allMax37, "shard35b");
check35(exact37(allMin37, middle37).shard === "shard35a" &&
  exact37(middle37, allMax37).shard === "shard35b", "Initial placement mismatch");
printjson(chunks37().map(c => ({ shard: c.shard, min: c.min, max: c.max })));
printjson({ logicalByPlacement: { shard35a: 500, shard35b: 500 } });
events37.getShardDistribution();
printjson(verify37());
```

The 500/500 logical assignment follows the verified fixture and frozen bounds. Distribution output is a separate physical observation and may reflect donor cleanup/storage allocation. Do not sum raw direct-shard collection counts to verify this routed fixture.

## 8. Verify routing with real explain results

```javascript
const both37 = ["shard35a", "shard35b"];
explain37("full-key-point", { tenantId: "tenant-0", eventId: id37(42) }, ["shard35a"], 1);
explain37("tenant-prefix", { tenantId: "tenant-0" }, ["shard35a"], 100);
explain37("event-without-prefix", { eventId: id37(42) }, both37, 1);
explain37("separated-tenants", { tenantId: { $in: ["tenant-0", "tenant-9"] } }, both37, 200);
explain37("cross-boundary-range", { tenantId: { $gte: "tenant-4", $lt: "tenant-6" } }, both37, 200);
explain37("global-status", { status: "open" }, both37, 334);
const tenantRows37 = events37.find({ tenantId: "tenant-0" }).sort({ eventId: 1 }).maxTimeMS(5000).toArray();
check35(tenantRows37.length === 100 && tenantRows37[0].eventId === id37(0) &&
  tenantRows37[99].eventId === id37(99), "Tenant result contract mismatch");
```

Expected shard names and result counts are asserted separately. A single returned event with two executed shard names is scatter-gather evidence. Two owners in the catalog alone would not prove that a specific query contacted both.

For each explain, inspect local scan/index stages, key bounds, filtering and shard-level work in the raw output. A merge stage name is useful context, but stage names alone are less robust than identifying the actual shard entries. Missing root examined-work fields must be recorded as unavailable; do not silently turn them into zero.

## 9. Failure exercise: index repair without routing repair

**Trigger:** The API lookup uses `eventId` alone. **Symptom:** One returned document, two participating shards. **First attempted repair:** Add a local event index. **Final correction:** Include the known tenant prefix in the lookup contract when the API semantics supply it.

```javascript
const scanLookup37 = explain37("unscoped-forced-key-scan", { eventId: id37(42) }, both37, 1, "tenant_event");
events37.createIndex({ eventId: 1 }, { name: "event_lookup" });
const indexedLookup37 = explain37("unscoped-indexed", { eventId: id37(42) }, both37, 1, "event_lookup");
const targetedLookup37 = explain37("tenant-scoped-indexed", { tenantId: "tenant-0", eventId: id37(42) },
  ["shard35a"], 1, "tenant_event");
const unscopedDoc37 = events37.findOne({ eventId: id37(42) });
const scopedDoc37 = events37.findOne({ tenantId: "tenant-0", eventId: id37(42) });
check35(unscopedDoc37 && scopedDoc37 && equal37(unscopedDoc37, scopedDoc37), "Lookup contract changed");
printjson({ before: scanLookup37, localIndexOnly: indexedLookup37, fullKey: targetedLookup37 });
```

The forced scans/hints make the local-work comparison controlled; they are not blanket production tuning recommendations. Inspect the actual examined counters and winning index before claiming reduced work. The event index does not reduce the two-shard fan-out. The full-key filter does under this placement.

This fixture generates unique event IDs, so the two filters return the same document. In a real API, use tenant identity from the authorized request/service context and preserve its intended semantics. If an operation is truly a global event lookup, arbitrarily inserting one tenant value can make the result incorrect. A mapping collection, different access path, or key/model redesign may be needed instead.

Do not copy older single-document write restrictions from a read example: write targeting rules depend on the command, driver and version. This chapter tests finds and actual result consumption; it does not establish `updateOne`, upsert or transaction routing behavior.

## 10. Model and execute a bounded tenant-heavy workload

The first mix reads each of tenant 0's 100 distinct events twice and performs 20 reads to tenant 9. The second mix repeats one tenant-0 event 200 times plus the same 20 cold reads. Both are deliberately concentrated; neither attempts to saturate CPU or produce a real incident.

```javascript
// Comparator is deliberately limited to this ASCII-string/sentinel fixture.
function scalarCompare37(a, b) {
  function rank(v) {
    if (v && v._bsontype === "MinKey") return -1;
    if (v && v._bsontype === "MaxKey") return 1;
    check35(typeof v === "string" && /^[\x20-\x7e]*$/.test(v), "Unsupported key type/string for fixture model");
    return 0;
  }
  const ra = rank(a), rb = rank(b);
  if (ra !== rb) return ra < rb ? -1 : 1;
  if (ra !== 0 || a === b) return 0;
  return a < b ? -1 : 1;
}
function keyCompare37(a, b) {
  return scalarCompare37(a.tenantId, b.tenantId) || scalarCompare37(a.eventId, b.eventId);
}
function owner37(key, ranges) {
  const matches = ranges.filter(c => keyCompare37(c.min, key) <= 0 && keyCompare37(key, c.max) < 0);
  check35(matches.length === 1, "Missing/ambiguous catalog owner");
  return matches[0].shard;
}
function requests37(singleDocument) {
  const hot = Array.from({ length: 200 }, (_, i) => singleDocument ? 0 : i % 100);
  const cold = Array.from({ length: 20 }, (_, i) => 900 + i);
  return [...hot, ...cold].map(seq => ({ seq, tenantId: tenant37(seq), eventId: id37(seq) }));
}
function workload37(label, singleDocument) {
  const ranges = chunks37();
  const fingerprint = EJSON.stringify(ranges.map(c => ({ min: c.min, max: c.max, shard: c.shard })));
  const requests = requests37(singleDocument);
  const modeledRequestsByOwner = { shard35a: 0, shard35b: 0 };
  const elapsed = [];
  const started = Date.now();
  for (const req of requests) {
    check35(Date.now() - started < 120000, "Workload deadline exceeded; stop and inspect");
    const key = { tenantId: req.tenantId, eventId: req.eventId };
    const owner = owner37(key, ranges);
    check35(Object.hasOwn(modeledRequestsByOwner, owner), "Owner outside expected shards");
    const t = Date.now();
    const docs = events37.find(key).comment("chapter37:" + label).maxTimeMS(5000).toArray();
    elapsed.push(Date.now() - t);
    check35(docs.length === 1 && docs[0].seq === req.seq && docs[0].revision === 1,
            "Workload result mismatch");
    modeledRequestsByOwner[owner]++;
    sleep(10);
  }
  check35(EJSON.stringify(chunks37().map(c => ({ min: c.min, max: c.max, shard: c.shard }))) === fingerprint,
          "Placement changed during workload; discard assignment model");
  const sorted = [...elapsed].sort((a, b) => a - b);
  const result = { label, completed: requests.length, modeledRequestsByOwner,
    clientMedianMs: sorted[Math.floor(sorted.length / 2)], clientMaxMs: sorted[sorted.length - 1],
    wallMs: Date.now() - started, sequential: true };
  printjson(result);
  return result;
}
const tenantBefore37 = workload37("tenant-hot-before", false);
check35(tenantBefore37.completed === 220 && tenantBefore37.modeledRequestsByOwner.shard35a === 200 &&
  tenantBefore37.modeledRequestsByOwner.shard35b === 20, "Initial request assignment mismatch");
printjson(verify37());
```

The measured timings are from actual sequential routed reads. Owner request counts are **catalog-derived assignments**, not collected server counters. Representative full-key explains corroborate routing; server telemetry or request traces are required to measure real per-shard QPS/CPU under concurrency. Equal 500/500 stored documents coexist here with a 200/20 planned request concentration.

The two-minute check bounds progression; an in-flight read also has its own server time limit and can outlast the next deadline check. A time limit is not a guarantee of exact client wall time. Abort the exercise on errors or resource pressure. No latency ratio, p99 target or cache-performance conclusion is asserted from this tiny sample.

## 11. Split the tenant's distinct values across shards

```javascript
const hotMiddle37 = { tenantId: "tenant-0", eventId: id37(50) };
const nextTenant37 = { tenantId: "tenant-1", eventId: MinKey };
split37(hotMiddle37);
split37(nextTenant37);
const hotRangeOriginal37 = exact37(hotMiddle37, nextTenant37).shard;
check35(hotRangeOriginal37 === "shard35a", "Unexpected original hot range owner");
move37(hotMiddle37, nextTenant37, "shard35b");
printjson(verify37());
printjson(chunks37().map(c => ({ min: c.min, max: c.max, shard: c.shard })));
explain37("tenant-prefix-after-split", { tenantId: "tenant-0" }, both37, 100);
explain37("hot-lower-point", { tenantId: "tenant-0", eventId: id37(0) }, ["shard35a"], 1);
explain37("hot-upper-point", { tenantId: "tenant-0", eventId: id37(99) }, ["shard35b"], 1);
explain37("cold-point", { tenantId: "tenant-9", eventId: id37(900) }, ["shard35b"], 1);
const tenantAfter37 = workload37("tenant-hot-after", false);
check35(tenantAfter37.modeledRequestsByOwner.shard35a === 100 &&
  tenantAfter37.modeledRequestsByOwner.shard35b === 120, "Split-tenant request assignment mismatch");
printjson({ logicalByPlacement: { shard35a: 450, shard35b: 550 } });
events37.getShardDistribution();
```

Moving only the upper half of tenant 0 changes its distinct-event workload from 200/20 to 100/120 assignments. This is a deliberately frozen manual placement comparison, not a claim that the balancer redistributes according to QPS or that latency improved. Tenant-only list operations now require both shards; distinct full-key point requests remain targeted. The distribution gain and prefix-query fan-out tradeoff must be evaluated together.

If a move times out, inspect bounds/owner and data before replay. Do not force movement or delete source documents. Catalog ownership can be committed while donor cleanup is still pending.

## 12. Show the single-document limitation and restore placement

```javascript
const documentHot37 = workload37("single-document-hot-after", true);
check35(documentHot37.modeledRequestsByOwner.shard35a === 200 &&
  documentHot37.modeledRequestsByOwner.shard35b === 20, "Single-document assignment mismatch");
explain37("repeated-hot-document", { tenantId: "tenant-0", eventId: id37(0) }, ["shard35a"], 1);
printjson({ tenantBefore: tenantBefore37, tenantAfter: tenantAfter37, documentHot: documentHot37 });
move37(hotMiddle37, nextTenant37, hotRangeOriginal37);
check35(exact37(hotMiddle37, nextTenant37).shard === "shard35a", "Placement restoration failed");
explain37("tenant-prefix-restored", { tenantId: "tenant-0" }, ["shard35a"], 100);
printjson(verify37());
check35(lab37.control.updateOne({ _id: "ownership" },
  { $set: { phase: "comparisons-complete-placement-restored" } },
  { writeConcern: wc37 }).matchedCount === 1, "Checkpoint failed");
```

The moved range never contained event 0. Repeated reads of that document remain concentrated on its current owner. Moving its range elsewhere would relocate the concentration; it would not divide one document into independently writable shards. Read preference/caching may help some read workloads with explicit freshness requirements, while write contention requires a suitable application/data model. Do not infer those benefits from this read-only fixture.

Placement returns to the original owner, but manual splits remain until AutoMerger/cleanup. A returned owner does not undo every catalog timestamp or physical allocation. Save all three workload results and raw explain evidence before cleanup.

## 13. Production diagnosis and correction choices

| Finding | Candidate action | Verification needed |
|---|---|---|
| Lookup broadcasts because it lacks a known tenant/key prefix | Correct the request/access path contract | Same intended result and reduced actual participating shards |
| Targeted operation scans too much locally | Improve supporting indexes, filter/selectivity and projection | Lower real examined work with correct result semantics |
| Tenant's distinct keys dominate one owner | Revisit granularity, placement and key strategy | Demand distribution, capacity, routing cost and migration overhead |
| One document dominates updates | Rework contention/aggregation/write model where appropriate | Correct concurrency semantics and measured write throughput |
| Global report legitimately needs all shards | Bound time/result size, schedule/materialize where appropriate | End-to-end latency and shard/router resource impact |
| Slow shard dominates broadcast latency | Diagnose its CPU/cache/storage/replication/query work | Time-correlated per-shard evidence rather than cluster averages |

Use application/driver metrics for latency, pool waits, retries and errors; combine them with per-shard CPU, cache pressure, disk latency, replication lag and namespace workload. Correlate query shape, parameter skew and time window. A global average can hide one overloaded shard.

Broad sorts, skip-based pagination and large results add local/merge/network work. A limit does not create a missing key bound. Test seek pagination and query-specific indexes from earlier chapters against the actual routing contract. Administrative query settings, profiling and sampling changes require explicit scoping/restoration; none are changed in this lab.

Separate read and write paths when designing remediation. Redistributing ranges, changing keys and adding cache can alter consistency, capacity and operational costs. A key that improves point requests may worsen tenant-wide lists or global reports. Validate with the production workload mix; resharding/refinement follows in Chapter 38.

## 14. Troubleshooting

| Symptom | Evidence | Cause to investigate | Action |
|---|---|---|---|
| One returned document, two shard names | Winning/executed explain entries | Missing leading key bound | Verify intended API contract; add the known bound or redesign access path |
| New index still shows two shards | Index stage plus shard entries | Local optimization did not change routing | Report both dimensions separately |
| Full key targets unexpected owner | UUID/bounds, values/types, raw explain | Placement/type/collation mismatch or concurrent move | Inspect live catalog; discard stale expectations |
| Prefix query changes from one to two targets | Before/after bounds and explain | Tenant spans multiple owners | Evaluate list-operation cost alongside point workload distribution |
| Parser finds no shard names | Full explain, server/shell versions | Explain layout differs | Adapt only after manual inspection; never guess zero/one targets |
| Explained counters and normal timing disagree | Raw explain, actual client timing, cache/pool state | Different plan-cache/network/workload conditions | Avoid treating explain duration as application p99 |
| Workload deadline or maxTimeMS fails | Exact error, resource metrics, completed count | Local pressure or slow path | Stop; preserve partial evidence and diagnose |
| Modeled request counts change unexpectedly | Frozen catalog fingerprint and workload IDs | Concurrent placement change or wrong key assignment | Discard model and rerun only after ownership/readiness review |
| Physical distribution differs from logical 450/550 | Migration/delete state and storage data | Donor remnants or allocation overhead | Verify routed IDs; do not delete physical duplicates manually |
| Hot-document demand persists after range split | Full-key owner and request mix | Contention concentrated in one indivisible document | Assess application semantics; moving another range cannot divide it |

## 15. Scoped cleanup and interruption recovery

Normal cleanup removes only Chapter 37's `events`/`control` namespace and restores the fresh collection's balancing/AutoMerger defaults first. No shared shard tags or global balancing policy are changed. The original Chapter 35 fixture remains for later chapters.

Save **`scripts/cleanup37.js`** and execute it in a fresh process. It also handles an interrupted lab whose interactive variables were lost. Capture the ownership record, fixture/routing evidence, workload outputs and current catalog first. If a migration is in flight, allow it to resolve and diagnose any transient conflict before cleanup; a collection pause does not reverse a committed move.

```javascript
load("/scripts/lib37.js");
router35();
for (const spec of sets35) wait35("cleanup " + spec.name, () => ready35(spec));
const saved37 = lab37.control.findOne({ _id: "ownership" });
check35(saved37 && saved37.namespace === ns37 && saved37.priorCollectionBalancing === true &&
  saved37.priorAutoMerger === true, "Missing/wrong ownership baseline");
check35(lab37.getCollectionNames().every(n => ["events", "control"].includes(n)),
        "Unexpected collection; preserve chapter database");
check35(sh.getBalancerState() === saved37.globalBalancer &&
  equal37(catalog37.settings.findOne({ _id: "balancer" }), saved37.globalSettings),
  "Global policy changed; inspect instead of overwriting");
check35(catalog37.tags.countDocuments({ ns: ns37 }) === 0, "Unexpected zone ranges; preserve state");
for (const baseline of saved37.shardTags) {
  const shard = catalog37.shards.findOne({ _id: baseline.shard });
  check35(shard && equal37([...(shard.tags || [])].sort(), baseline.tags), "Shared shard tags changed");
}
const current37 = catalog37.collections.findOne({ _id: ns37 });
if (current37) {
  check35(!saved37.uuid || equal37(current37.uuid, saved37.uuid), "Namespace UUID changed");
  const restore37 = db.adminCommand({ configureCollectionBalancing: ns37, enableAutoMerger: true });
  check35(restore37.ok === 1, "AutoMerger default restoration failed");
  sh.enableBalancing(ns37);
  check35(catalog37.collections.findOne({ _id: ns37 }).noBalance !== true,
          "Collection balancing default not restored");
}
check35(lab37.getName() === "mongodb_enterprise_tutorial_ch37",
        "Refusing cleanup outside the Chapter 37 training database");
check35(lab37.dropDatabase().ok === 1, "Owned database drop failed");
check35(lab37.getCollectionNames().length === 0 &&
  !catalog37.collections.findOne({ _id: ns37 }) && catalog37.tags.countDocuments({ ns: ns37 }) === 0,
  "Namespace cleanup incomplete");
printjson({ cleaned: name37, sharedPolicyUnchanged: true });
```

```bash
docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?readPreference=primary&serverSelectionTimeoutMS=5000' --quiet --file /scripts/cleanup37.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
```

On `r2`, also confirm that Chapter 37 has no collections/catalog namespace/zone ranges. After the ownership record is removed, verify cleanup read-only rather than replaying its script. A failed guard requires ownership review, not a forced deletion.

The out-and-back migration reverses the measured hot-range owner before normal cleanup. Dropping this owned fixture removes its remaining split/index footprint; it is not a production data-placement rollback. No config/system database drop, shared index deletion, volume removal or Docker prune is needed.

## 16. Acceptance, evidence and review

- [ ] Recorded pinned versions, healthy original topology, prior zone cleanup and Chapter 35's exact 1001 documents.
- [ ] Saved the ownership baseline and paused only the fresh fixture's collection automation.
- [ ] Verified 1000 exact fixture documents, 100 per tenant and seq sum 499500.
- [ ] Established two initial owners with 500/500 logical document assignment.
- [ ] Verified full-key, prefix, suffix-only, multi-prefix, key-range and global-status fan-out/counts using real explain.
- [ ] Reproduced the unscoped lookup; verified a local index retained fan-out while a correct full-key lookup reduced it.
- [ ] Executed the bounded sequential tenant-heavy workload with 200/20 catalog-derived assignments.
- [ ] Moved exactly 50 tenant-0 events and verified prefix fan-out changed while point requests remained targeted.
- [ ] Recorded 100/120 assignments for distinct tenant events and 200/20 for repeated reads of one document.
- [ ] Restored the hot range's owner and verified all data before cleanup.
- [ ] Restored fresh defaults, removed only chapter resources, preserved shared policy and checked cleanup through r2.
- [ ] Reverified original Chapter 35 data/topology through both routers.

**Evidence:** Versions, ownership record, UUID/bounds, logical verification and physical distribution, full raw explain plus summaries, local index specs, result equivalence, actual completed reads/timing, clearly labeled catalog-derived request assignments, migration/restoration responses and cleanup checks. Failed/unsupported steps must be recorded. Static checks do not count as runtime acceptance, and the bounded sequential workload does not establish production capacity or latency improvement.

**Review questions:**

1. Why can one returned result require two shards?
2. Why does an event lookup index not replace a missing tenant-prefix predicate?
3. How can a targeted operation still be slow?
4. Why does tenant equality target both shards after the split?
5. Why are catalog-derived request counts different from measured server QPS?
6. How can equal document placement coexist with unequal demand?
7. Why does splitting distinct values help a tenant-wide point workload but not one repeated document?
8. Why must the global lookup contract be preserved when adding a tenant filter?
9. What would you collect before claiming latency or throughput improvement?
10. What remains after owner restoration, and why is fixture cleanup a separate step?

## 17. Official references

- [MongoDB 8.0: routing with mongos](https://www.mongodb.com/docs/v8.0/core/sharded-cluster-query-router/)
- [MongoDB 8.0: explain results](https://www.mongodb.com/docs/v8.0/reference/explain-results/)
- [MongoDB 8.0: choose a shard key](https://www.mongodb.com/docs/v8.0/core/sharding-choose-a-shard-key/)
- [MongoDB 8.0: cursor hint](https://www.mongodb.com/docs/v8.0/reference/method/cursor.hint/)
- [MongoDB 8.0: cursor maxTimeMS](https://www.mongodb.com/docs/v8.0/reference/method/cursor.maxTimeMS/)
- [MongoDB 8.0: moveChunk](https://www.mongodb.com/docs/v8.0/reference/command/moveChunk/)
- [MongoDB 8.0: configureCollectionBalancing](https://www.mongodb.com/docs/v8.0/reference/command/configureCollectionBalancing/)

---

Previous: [Chapter 36 — Chunk Distribution Balancing and Zones](36-chunk-distribution-balancing-and-zones.md)  
Next: **[Chapter 38 — Resharding and Shard Key Refinement](38-resharding-and-shard-key-refinement.md)**.
