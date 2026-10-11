# 40 — Scaling and Sharding Acceptance Lab

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 5 — Sharding and Scale  
**Goal:** Demonstrate a verified transition from one to two shard owners, measure a fixed workload without inventing scaling claims, verify router-outage continuity, and assemble evidence for the sharding acceptance decision.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes, plus production-size capacity testing outside this lab.  
**Baseline:** MongoDB 8.0 and mongosh; retain Chapter 35's image digest and exact version/FCV inventory.  
**Deployment:** Retained isolated `mongodb-ch35`, dedicated `cfg35`, registered data shards `shard35a`/`shard35b`, routers `r1`/`r2`. Community-compatible.  
**Prerequisites:** Chapters 33–39; their cleanup complete; original three-member replica sets healthy and Chapter 35's 1001-document fixture intact; exclusive use of the disposable cluster; temporary migration/resource headroom; scoped monitoring, sharding administration and chapter CRUD privileges where authentication applies.

## 1. What this acceptance lab proves

**Use case:** An event service has a large tenant and several smaller tenants. Its collection initially resides on one shard even though the deployment has two. Before treating the second shard as useful capacity, the team must prove that eligible data can move there, queries reach the intended owners, writes reconcile and endpoint recovery preserves the application contract.

This lab creates an owned compound-key collection, stages all its ranges on shard A, then moves two ranges to B. It does not add a third shard, resize containers or alter the original Chapter 35 collection. The second registered shard already exists; the exercise makes it an owner for this workload.

| Claim | Required evidence |
|---|---|
| Both shards own application data | Exact catalog ranges plus routed fixture-to-range accounting |
| The large tenant is divisible | Distinct suffix values, deliberate split and owners on both shards |
| Point reads target one shard | Winning and executed explain targets, exact returned record |
| Tenant/global reads can fan out | Actual explain targets and complete record reconciliation |
| Majority writes survive normal operation | Acknowledgement, majority read-back and confirmed reset |
| One router outage has a surviving endpoint | Fresh client through r2, then both restored endpoints verified |
| Production capacity is adequate | Separate representative load, latency, resource and failure testing |

Manual range migration is evidence of supported placement control. It is not evidence that the automatic balancer corrected this collection. That separate acceptance belongs to Chapter 36. Refinement/resharding evidence belongs to Chapter 38, and shard/config-member recovery to Chapter 39.

## 2. Define the workload and success criteria first

The fixture contains 1200 events: tenant 0 has 600; tenants 1–6 have 100 each. Every document has a globally unique chapter ID and distinct integer `seq`. The shard key is `{tenantId:1,seq:1}`; an additional `{seq:1}` index supports the deliberately untargeted lookup.

Each workload run performs **120 reads** and **12 write probes**, each probe consisting of a majority update, majority read-back and majority reset. Operations are serial and small. Every result is checked against the deterministic fixture; errors fail the run rather than being excluded from its timing summary.

| Read class | Operations per run | Predicate/result |
|---|---:|---|
| Full-key point | 90 | `{tenantId,seq}`; one exact event |
| Small-tenant list | 20 | `{tenantId:5}`; 100 exact events |
| Suffix-only point | 10 | `{seq}`; one event, without the tenant prefix |

The ratios are a synthetic workload contract, not observed production traffic. Review real tenant skew, query predicates, write/update distribution, retention and growth before recommending a key. The compound suffix creates split opportunities within tenant 0; it does not solve a single hot document or guarantee evenly distributed future inserts.

All functional gates must pass. Latency/resource gates for a real deployment must be set from its SLO and measured workload before the test. No arbitrary sub-millisecond or throughput target is imposed on this Docker fixture.

## 3. Placement plan and routing tradeoff

The plan uses four contiguous half-open catalog intervals. Bounds are BSON compound keys; `MinKey`/`MaxKey` are sentinels, not ordinary tenant or sequence values.

| Range | Minimum inclusive | Maximum exclusive | Fixture events | Baseline owner | Distributed owner |
|---|---|---|---:|---|---|
| R0 | `{tenantId:MinKey,seq:MinKey}` | `{tenantId:0,seq:300}` | 300 | A | A |
| R1 | `{tenantId:0,seq:300}` | `{tenantId:1,seq:MinKey}` | 300 | A | B |
| R2 | `{tenantId:1,seq:MinKey}` | `{tenantId:4,seq:MinKey}` | 300 | A | A |
| R3 | `{tenantId:4,seq:MinKey}` | `{tenantId:MaxKey,seq:MaxKey}` | 300 | A | B |

After distribution, each shard owns 600 fixture events. Tenant 0 spans A and B, so listing all its events now involves both shards; a full-key point remains targeted. A single-shard tenant read and equal document ownership are different goals.

This exact 600/600 result follows from deliberate fixture counts and manual boundaries. It is not a general balancer guarantee for bytes, disk occupancy, CPU, request rate or migration thresholds. Old physical copies may await asynchronous range deletion; logical ownership is not identical to physical storage reclamation.

## 4. Verify the environment and collect the baseline

Use **Bash** in the original Chapter 35 directory, retaining `.env`, `compose.yaml`, `scripts/lib35.js` and `scripts/verify35.js`. Rebuild Chapter 35 completely if its original volumes/data were discarded.

```bash
dc() { docker compose -p mongodb-ch35 -f compose.yaml "$@"; }
set -a
source .env
set +a
mkdir -p scripts evidence-ch40
client40() {
  docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?serverSelectionTimeoutMS=5000&connectTimeoutMS=3000&socketTimeoutMS=30000' --quiet --file "/scripts/$1"
}
dc ps -a
dc stats --no-stream > evidence-ch40/before-resources.txt
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/' --quiet --file /scripts/verify35.js
```

Record image digest, versions/FCV, actual host/volume free space and container OOM state. Resolve earlier chapter namespaces, active migration/resharding work, replica degradation and conflicting administrative changes before starting. Small fixture size does not remove the need for available recipient storage and healthy replication.

The chapter changes only its own collection's placement and automation flags. It records global policy and shard tags to detect external changes; it does not alter cluster balancing windows, migration throttles, process parameters or topology.

## 5. Shared fixture, ownership and range helpers

Save **`scripts/lib40.js`**:

```javascript
load("/scripts/lib35.js");
const name40 = "mongodb_enterprise_tutorial_ch40";
const ns40 = name40 + ".events";
const lab40 = db.getSiblingDB(name40);
const catalog40 = db.getSiblingDB("config");
const wc40 = { w: "majority", j: true, wtimeout: 10000 };
function equal40(a, b) { return EJSON.stringify(a) === EJSON.stringify(b); }
function tenant40(seq) { return seq < 600 ? 0 : 1 + Math.floor((seq - 600) / 100); }
function fixture40() {
  return Array.from({ length: 1200 }, (_, i) => ({
    _id: "ch40-" + String(i).padStart(4, "0"), tenantId: tenant40(i), seq: i,
    revision: 1, payload: "event-" + i
  }));
}
function boundaries40() {
  return [{ tenantId: MinKey(), seq: MinKey() }, { tenantId: 0, seq: 300 },
    { tenantId: 1, seq: MinKey() }, { tenantId: 4, seq: MinKey() },
    { tenantId: MaxKey(), seq: MaxKey() }];
}
function range40(seq) { return seq < 300 ? 0 : seq < 600 ? 1 : seq < 900 ? 2 : 3; }
function owners40(phase) {
  check35(["baseline", "distributed"].includes(phase), "Unknown placement phase");
  return phase === "baseline" ? Array(4).fill("shard35a") :
    ["shard35a", "shard35b", "shard35a", "shard35b"];
}
function meta40() {
  const m = catalog40.collections.findOne({ _id: ns40 });
  check35(m && m.uuid && m.unsplittable !== true &&
    equal40(m.key, { tenantId: 1, seq: 1 }) && !m.reshardingFields,
    "Unexpected owned collection metadata");
  return m;
}
function policy40() {
  check35(typeof sh.isAutoMergerEnabled === "function", "Required shell helper unavailable");
  return { balancer: sh.getBalancerState(), autoMerger: sh.isAutoMergerEnabled(),
    balancerDocument: catalog40.settings.findOne({ _id: "balancer" }),
    shardTags: catalog40.shards.find({}).sort({ _id: 1 }).toArray()
      .map(s => ({ id: s._id, tags: [...(s.tags || [])].sort() })) };
}
function ownership40() {
  const saved = lab40.control.findOne({ _id: "ownership" });
  check35(saved && saved.owner === "chapter40" && saved.ns === ns40, "Missing ownership record");
  check35(equal40(meta40().uuid, saved.uuid), "Owned collection replaced");
  check35(equal40(policy40(), saved.policy), "Global policy or shard tags changed");
  const original = catalog40.collections.findOne({ _id: "mongodb_enterprise_tutorial_ch35.events" });
  check35(original && equal40(original.uuid, saved.originalUUID), "Original fixture replaced");
  return saved;
}
function checkpoint40(fields) {
  const result = lab40.control.updateOne({ _id: "ownership", owner: "chapter40" },
    { $set: fields }, { writeConcern: wc40 });
  check35(result.acknowledged && result.matchedCount === 1, "Checkpoint update failed");
}
function placement40(phase) {
  const ranges = catalog40.chunks.find({ uuid: meta40().uuid })
    .sort({ "min.tenantId": 1, "min.seq": 1 }).toArray();
  const bounds = boundaries40(), owners = owners40(phase);
  check35(ranges.length === 4, "Expected four ranges");
  for (let i = 0; i < 4; i++) {
    check35(equal40(ranges[i].min, bounds[i]) && equal40(ranges[i].max, bounds[i + 1]) &&
      ranges[i].shard === owners[i], "Wrong bounds/owner for R" + i);
  }
  return ranges;
}
function exactDocs40(actual, expected) {
  check35(actual.length === expected.length, "Incomplete query result");
  for (let i = 0; i < expected.length; i++) {
    for (const field of ["_id", "tenantId", "seq", "revision", "payload"]) {
      check35(actual[i][field] === expected[i][field], "Mismatch at " + i + "/" + field);
    }
  }
}
function verify40() {
  const docs = lab40.events.find({}).sort({ seq: 1 }).readConcern("majority")
    .maxTimeMS(10000).toArray();
  exactDocs40(docs, fixture40());
  check35(new Set(docs.map(d => d._id)).size === 1200, "Duplicate IDs");
  const sum = docs.reduce((n, d) => n + d.seq, 0);
  check35(sum === 719400, "Wrong sequence total");
  const tenants = Array.from({ length: 7 }, (_, t) => docs.filter(d => d.tenantId === t).length);
  check35(equal40(tenants, [600, 100, 100, 100, 100, 100, 100]), "Wrong tenant distribution");
  return { count: docs.length, sum, tenants };
}
function names40(node, out = new Set()) {
  if (!node || typeof node !== "object") return out;
  if (typeof node.shardName === "string") out.add(node.shardName);
  for (const [key, value] of Object.entries(node)) {
    if (!["rejectedPlans", "allPlansExecution"].includes(key)) names40(value, out);
  }
  return out;
}
function explain40(query, expectedTargets, expectedCount) {
  const e = lab40.events.find(query).maxTimeMS(10000).explain("executionStats");
  printjson({ query, explain: e });
  const planned = [...names40(e.queryPlanner.winningPlan)].sort();
  const executed = [...names40(e.executionStats.executionStages)].sort();
  check35(equal40(planned, [...expectedTargets].sort()) &&
    equal40(executed, [...expectedTargets].sort()), "Wrong explain targets");
  check35(e.executionStats.nReturned === expectedCount, "Wrong explain result count");
}
```

All fixture calculations use actual key ordering for these integer values. `range40` is a deterministic mapping of this fixture, not a BSON comparison utility for arbitrary production keys. Helpers reject unexpected UUID, key, policy or tags instead of treating a concurrent change as part of this test.

## 6. Create four ranges owned by shard A

Save **`scripts/setup40.js`**. Run once on a fresh chapter namespace.

```javascript
load("/scripts/lib40.js");
router35();
for (const spec of sets35) {
  check35(ready35(spec), "Original set unhealthy");
  const admin = seeded35(spec).getDB("admin");
  const fcv = admin.runCommand({ getParameter: 1, featureCompatibilityVersion: 1 });
  check35(fcv.ok === 1 && fcv.featureCompatibilityVersion.version === "8.0" &&
    !fcv.featureCompatibilityVersion.targetVersion, "FCV not stable at 8.0");
  printjson({ set: spec.name, version: admin.runCommand({ buildInfo: 1 }).version, fcv });
}
check35(lab40.getCollectionNames().length === 0 &&
  !catalog40.collections.findOne({ _id: ns40 }), "Chapter namespace exists; reconcile first");
for (const n of [36, 37, 38, 39]) {
  check35(db.getSiblingDB("mongodb_enterprise_tutorial_ch" + n).getCollectionNames().length === 0,
    "Prior chapter cleanup incomplete");
}
const original = catalog40.collections.findOne({ _id: "mongodb_enterprise_tutorial_ch35.events" });
check35(original && original.uuid, "Original fixture metadata missing");
const policy = policy40();
check35(lab40.createCollection("events").ok === 1, "Cannot create fixture");
lab40.events.createIndex({ tenantId: 1, seq: 1 });
lab40.events.createIndex({ seq: 1 });
check35(db.adminCommand({ shardCollection: ns40, key: { tenantId: 1, seq: 1 } }).ok === 1,
  "Cannot shard fixture");
check35(sh.disableBalancing(ns40).ok === 1, "Cannot pause collection balancing");
check35(db.adminCommand({ configureCollectionBalancing: ns40, enableAutoMerger: false }).ok === 1,
  "Cannot pause collection AutoMerger");
check35(lab40.control.insertOne({ _id: "ownership", owner: "chapter40", ns: ns40,
  uuid: meta40().uuid, originalUUID: original.uuid, policy, phase: "preparing", at: new Date() },
  { writeConcern: wc40 }).acknowledged, "Ownership checkpoint failed");
const bounds = boundaries40();
for (const middle of bounds.slice(1, -1)) check35(sh.splitAt(ns40, middle).ok === 1, "Split failed");
for (let i = 0; i < 4; i++) {
  const range = catalog40.chunks.findOne({ uuid: meta40().uuid, min: bounds[i] });
  check35(range && equal40(range.max, bounds[i + 1]), "Wrong staged range");
  if (range.shard !== "shard35a") check35(db.adminCommand({ moveChunk: ns40,
    bounds: [bounds[i], bounds[i + 1]], to: "shard35a" }).ok === 1, "Staging move failed");
}
const inserted = lab40.events.insertMany(fixture40(), { writeConcern: wc40 });
check35(inserted.acknowledged && Object.keys(inserted.insertedIds).length === 1200,
  "Insert uncertain/incomplete; reconcile before retry");
placement40("baseline");
printjson(verify40());
checkpoint40({ phase: "baseline", fixtureReadyAt: new Date() });
printjson({ baselineReady: true, imageInventoryRequired: true, shell: version(), router: db.version() });
```

```bash
client40 setup40.js > evidence-ch40/setup.json
```

No zone is attached to this fixture. Collection-level balancing/AutoMerger stay paused until cleanup so the planned bounds remain stable. Manual migration is still available. If setup fails, keep the output and inspect the ownership record, catalog and documents; replaying setup can duplicate writes or split already split ranges.

## 7. Functional verification and representative explains

Save **`scripts/verify40.js`**:

```javascript
load("/scripts/lib40.js");
wait35("router registration", () => { router35(); return true; });
for (const spec of sets35) wait35("healthy " + spec.name, () => ready35(spec));
const saved = ownership40();
check35(["baseline", "distributed"].includes(saved.phase), "Unresolved preparation/migration phase");
const owners = owners40(saved.phase);
const targets = [...new Set(owners)].sort();
printjson({ phase: saved.phase, ranges: placement40(saved.phase), data: verify40() });
const expectedCounts = {};
for (let i = 0; i < 1200; i++) expectedCounts[owners[range40(i)]] =
  (expectedCounts[owners[range40(i)]] || 0) + 1;
printjson({ logicalOwnedFixtureCounts: expectedCounts,
  note: "Reconciled routed data mapped to verified ranges; not direct physical shard counts" });
explain40({ tenantId: 0, seq: 42 }, [owners[0]], 1);
explain40({ tenantId: 0, seq: 342 }, [owners[1]], 1);
explain40({ tenantId: 0 }, [...new Set(owners.slice(0, 2))], 600);
explain40({ tenantId: 5 }, [owners[3]], 100);
explain40({ seq: 987 }, targets, 1);
explain40({}, targets, 1200);
const findings = lab40.checkMetadataConsistency({ checkIndexes: true }).toArray();
printjson({ metadataAndIndexFindings: findings });
check35(findings.length === 0, "Metadata/index inconsistency");
printjson({ verified: true, at: new Date(), router: db.getMongo().toString() });
```

```bash
client40 verify40.js > evidence-ch40/baseline-verification.json
```

This verification derives document ownership from two observations: every routed document matches the fixture, and each key falls in a verified catalog interval. It does not read application data directly from shard members or mistake orphan copies for extra logical documents. The metadata consistency cursor is fully consumed, with no concurrent index DDL.

## 8. Run and report the baseline workload

Save **`scripts/workload40.js`**. The same script runs in both placement phases and during the router exercise.

```javascript
load("/scripts/lib40.js");
router35();
const saved = ownership40();
check35(["baseline", "distributed"].includes(saved.phase), "Workload requires stable placement");
placement40(saved.phase);
verify40();
const fixture = fixture40();
const times = { fullKeyPoint: [], tenantList: [], suffixPoint: [], writeProbe: [] };
function readCase40(label, query, expected) {
  const start = Date.now();
  const docs = lab40.events.find(query).sort({ seq: 1 }).readConcern("majority")
    .maxTimeMS(5000).toArray();
  const elapsed = Date.now() - start;
  exactDocs40(docs, expected);
  times[label].push(elapsed);
}
const began = Date.now();
for (let round = 0; round < 10; round++) {
  for (let k = 0; k < 9; k++) {
    const seq = (round * 113 + k * 137) % 1200;
    readCase40("fullKeyPoint", { tenantId: tenant40(seq), seq }, [fixture[seq]]);
  }
  for (let k = 0; k < 2; k++) readCase40("tenantList", { tenantId: 5 },
    fixture.filter(d => d.tenantId === 5));
  const seq = (round * 97 + 987) % 1200;
  readCase40("suffixPoint", { seq }, [fixture[seq]]);
}
for (let probe = 0; probe < 12; probe++) {
  const seq = probe * 100;
  const query = { tenantId: tenant40(seq), seq, _id: fixture[seq]._id };
  const start = Date.now();
  const update = lab40.events.updateOne(query, { $set: { revision: 2 } }, { writeConcern: wc40 });
  check35(update.acknowledged && update.matchedCount === 1, "Probe write uncertain/unmatched");
  const docs = lab40.events.find(query).readConcern("majority").maxTimeMS(5000).toArray();
  exactDocs40(docs, [{ ...fixture[seq], revision: 2 }]);
  const reset = lab40.events.updateOne(query, { $set: { revision: 1 } }, { writeConcern: wc40 });
  check35(reset.acknowledged && reset.matchedCount === 1, "Probe reset uncertain/unmatched");
  times.writeProbe.push(Date.now() - start);
}
function summary40(values) {
  check35(values.length > 0, "No workload observations");
  const sorted = [...values].sort((a, b) => a - b);
  const p = q => sorted[Math.ceil(q * sorted.length) - 1];
  return { samples: sorted.length, minMS: sorted[0], medianMS: p(0.5),
    p95MS: p(0.95), maxMS: sorted[sorted.length - 1] };
}
check35(times.fullKeyPoint.length === 90 && times.tenantList.length === 20 &&
  times.suffixPoint.length === 10 && times.writeProbe.length === 12, "Incomplete workload");
const finalData = verify40();
printjson({ workloadPassed: true, phase: saved.phase, at: new Date(),
  router: db.getMongo().toString(), readOperations: 120, updateOperations: 24,
  writeReadBackOperations: 12, wallMS: Date.now() - began,
  statistics: Object.fromEntries(Object.entries(times).map(([key, values]) => [key, summary40(values)])),
  rawMilliseconds: times, finalData });
```

```bash
client40 workload40.js > evidence-ch40/baseline-workload.json
dc stats --no-stream > evidence-ch40/baseline-resources.txt
```

Timing uses `Date.now()` milliseconds and includes client command/response overhead; very fast requests may record 0 ms. Write-probe duration covers update, read-back and reset, not one business-write latency. The sample count is too small for strong tail-latency conclusions. All errors stop the run; no success-only latency report is a passing workload.

The script does not execute explain for every request or measure real concurrent saturation. Representative explain evidence is separate. A serial run's operations per wall second is not maximum throughput, and warmer caches in the second run are a confounder. Preserve raw timings and resource observations instead of claiming a percentage speedup from a tiny difference.

## 9. Redistribute the same key to use both shards

Save **`scripts/distribute40.js`**:

```javascript
load("/scripts/lib40.js");
router35();
for (const spec of sets35) check35(ready35(spec), "Unhealthy set before migration");
const saved = ownership40();
check35(["baseline", "redistributing"].includes(saved.phase), "Wrong migration checkpoint");
verify40();
checkpoint40({ phase: "redistributing", migrationIntentAt: new Date() });
const bounds = boundaries40(), desired = owners40("distributed");
const ranges = catalog40.chunks.find({ uuid: saved.uuid }).toArray();
check35(ranges.length === 4, "Unexpected granularity; stop migration");
for (let i = 0; i < 4; i++) {
  const range = catalog40.chunks.findOne({ uuid: saved.uuid, min: bounds[i] });
  check35(range && equal40(range.max, bounds[i + 1]) &&
    ["shard35a", "shard35b"].includes(range.shard), "Unexpected range before migration");
  if (range.shard !== desired[i]) {
    checkpoint40({ lastIntentRange: i, lastIntentDestination: desired[i] });
    const started = Date.now();
    const response = db.adminCommand({ moveChunk: ns40,
      bounds: [bounds[i], bounds[i + 1]], to: desired[i] });
    printjson({ range: i, response, elapsedMS: Date.now() - started });
    check35(response.ok === 1, "Migration did not succeed; inspect before retry");
  }
  ownership40();
  printjson({ afterRange: i, reconciledData: verify40() });
}
printjson({ finalRanges: placement40("distributed"), finalData: verify40() });
checkpoint40({ phase: "distributed", distributedAt: new Date() });
```

```bash
client40 distribute40.js > evidence-ch40/migration.json
client40 verify40.js > evidence-ch40/distributed-verification.json
```

R1 and R3 move to B; the key pattern and UUID stay unchanged. Migration responses, actual owners and exact routed data are acceptance evidence. No `_waitForDelete`, forced jumbo move or global range-size adjustment is used.

If the client loses contact, a migration may have committed despite an uncertain response. Inspect actual range ownership and outstanding work first. This script can resume the same recorded `redistributing` intent once the earlier operation has resolved: it checks UUID/bounds and skips a range already at its desired destination. It is not an instruction to start overlapping migrations or change the intended destinations after a failure.

## 10. Compare routing and repeat the fixed workload

```bash
client40 workload40.js > evidence-ch40/distributed-workload.json
dc stats --no-stream > evidence-ch40/distributed-resources.txt
dc logs --since 15m --tail 200 a1 a2 a3 b1 b2 b3 r1 r2 > evidence-ch40/migration-and-workload-logs.txt
```

Fill this comparison from the saved output; these are expected functional observations, not fabricated runtime measurements:

| Observation | Baseline | Distributed |
|---|---|---|
| Catalog owners for this collection | A | A and B |
| Logical fixture documents per owner | A:1200, B:0 | A:600, B:600 |
| Tenant-0 point at seq 42 | A | A |
| Tenant-0 point at seq 342 | A | B |
| Tenant-0 list | A; 600 events | A+B; 600 events |
| Tenant-5 list | A; 100 events | B; 100 events |
| Suffix-only seq lookup | Observed owner targets | A+B; one logical result |
| Completed workload | 120 reads, 12 verified probes | Same operation counts |
| Latency/resources | Record actual values | Record actual values |

A suffix-only predicate does not supply the compound prefix. Its local `{seq:1}` index may make shard-local evaluation efficient while the router still needs multiple shards. Conversely, splitting tenant 0 can spread full-key points but increases the fan-out of tenant-wide requests. Key design must reflect the mix of both.

Equal event counts do not establish equal physical bytes or load. Large payloads, indexes, working sets and request frequency can make one shard expensive. Test skew and growth, and monitor each shard independently.

## 11. Verify continuity through the surviving router

Stop only r1 after distribution. Fresh clients explicitly use r2; this checks the surviving endpoint rather than asserting driver retry behavior for an existing session.

```bash
date -u +%FT%TZ > evidence-ch40/router-stop-time.txt
dc stop -t 30 r1
if docker run --rm --network mongodb-ch35_cluster "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?serverSelectionTimeoutMS=3000&connectTimeoutMS=2000' --quiet --eval 'db.adminCommand({ping:1})' > evidence-ch40/stopped-r1.txt 2>&1; then
  dc start r1
  exit 1
fi
docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000&socketTimeoutMS=30000' --quiet --file /scripts/verify40.js > evidence-ch40/surviving-r2-verification.json
docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000&socketTimeoutMS=30000' --quiet --file /scripts/workload40.js > evidence-ch40/surviving-r2-workload.json
dc start r1
client40 verify40.js > evidence-ch40/restored-r1-verification.json
docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000&socketTimeoutMS=30000' --quiet --file /scripts/verify40.js > evidence-ch40/restored-r2-verification.json
```

The expected r1 connection failure must actually be a connection/selection failure, not a missing image, Docker failure or malformed command. Inspect its saved output. If any r2 check fails, start r1 immediately and preserve the error; do not continue with another fault.

This outage proves explicit endpoint continuity and recovery in the owned topology. Existing application connections, load balancers, pool behavior, sessions, transactions and automatic driver retries require a separate test with the real client. Chapter 39's full-shard outage also shows why router redundancy cannot make an unavailable data range readable.

## 12. Capacity acceptance worksheet

Use the actual service's expected peak and growth to fill this worksheet before approving production scale. Mark unavailable measurements as **not tested**.

| Area | Input/test | Acceptance decision |
|---|---|---|
| Data growth | Current bytes/indexes, retention and monthly growth by tenant | Adequate shard capacity and expansion lead time |
| Working set | Hot data/index footprint versus usable cache | Bounded eviction/read amplification under expected load |
| Read/write load | Representative concurrency, predicate mix and burst profile | SLO and error budget met with recorded test duration |
| Largest tenant | Point and list/write load, indivisible values, monotonic growth | Granularity and destinations support real request distribution |
| Replication | Lag, oplog retention and rebuild/catch-up duration | Recovery fits loss/availability goals |
| Movement overhead | Recipient space, temporary copies, I/O and range deletion | Migration coexists with workload/backup safely |
| Failure capacity | Surviving members/routers, affected shard classes | Required degraded-mode service remains within contract |
| Cost | Data/config/router compute, storage, backup and network | Spend justified by measured needs, not nominal shard count |

Do not extrapolate a Docker run on one host into AZ resilience or production performance. Adding a shard also creates migration, replication, monitoring and backup obligations. An overloaded single document, weak local index or broad query may need a different fix even when more capacity is available.

For production performance testing, use the application's supported driver, representative datasets and a controlled load generator. Record warm-up, duration, concurrency, server/client budgets, successful and failed operations, p50/p95/p99, resource saturation, replication lag and backpressure. Test movement and relevant failure modes separately. This serial fixture is a functional gate before that work.

## 13. Assemble the Part 5 evidence packet

Use the previous chapter outputs rather than rerunning all their administrative changes together. Link real evidence files and record **pass**, **fail** or **not tested** for each row. Written chapters are not executed tests.

| Topic | Chapter | Evidence required |
|---|---|---|
| Architecture/identity | 33, 35 | Config/data roles, exact registered sets, redundant routers |
| Key/workload suitability | 34 | Cardinality/frequency, query and write mix, growth/skew review |
| Automatic placement policy | 36 | Zone definitions, staged violation, observed automatic correction, cleanup |
| Routing and local efficiency | 37, 40 | Winning/executed targets, returned records, local work and hotspot tradeoffs |
| Key evolution | 38 | Missing-index repair, refinement invariants, terminal resharding outcome, reconciliation |
| Failure/recovery | 39, 40 | Member/shard/router outages, scoped impact, acknowledged-write reconciliation |
| Integrated distribution | 40 | Same UUID/key, changed owners, exact fixture, matched workloads |
| Recovery from backup | Future backup/recovery chapters | Validated restore set and executed restore; currently not proved here |
| Production capacity/security | Separate reviewed exercises | SLO/capacity load and security gates; not inferred from this lab |

An acceptance statement should name scope, environment, versions, actual tests, failed/not-tested gates, owner and next action. For example: “The two-shard training fixture passed the functional gates on the recorded build. Production load, backup restore and client-session recovery remain not tested.” Use that statement only after actual execution; static checks alone leave functional runtime gates pending.

This chapter closes the written sharding section. It does not convert the repository's runtime or canonical counters into passes without execution evidence.

## 14. Troubleshooting and interrupted-write reconciliation

| Failure | Evidence | Next action |
|---|---|---|
| Namespace exists before setup | Ownership record, UUID, exact collections/data | Reconcile prior run; do not replay inserts |
| Migration timeout/disconnect | Response/logs, actual bounds/owners, outstanding work | Resolve prior outcome, then resume the same intent if safe |
| More/fewer than four ranges | Collection automation, catalog, concurrent changes | Diagnose changed granularity; do not fabricate planned bounds |
| Tenant list fans out unexpectedly | Prefix predicate and executed targets | Check actual range owners; splitting can legitimately add fan-out |
| Suffix-only lookup is locally indexed but broad | Explain targets and local execution | Improve routing predicate if application semantics permit |
| Metadata/index findings | Fully consumed cursor, versions, recent DDL | Preserve findings and investigate; no catalog editing |
| Revision mismatch after workload | Exact owned probe and timeout/reset output | Reconcile only the known probe; investigate other changes |
| Timing improves sharply in second run | Warm-up/cache and raw timings | Repeat representative performance tests; do not call it linear scaling |
| Policy/UUID guard fails | Saved and current state | Stop; determine external/replacement change before cleanup |

The only modified fixture field is `revision` on sequences `0,100,...,1100`. A timeout can leave an update or reset outcome unknown. Restore any stopped services, inspect those exact documents with majority reads, and compare every field with `fixture40()` before changing anything.

In an interactive **mongosh connected to a router**, after diagnosing an interrupted workload, use this guarded reconciliation only for chapter probe revisions:

```javascript
load("/scripts/lib40.js");
router35();
ownership40();
const expected40 = fixture40();
for (let probe = 0; probe < 12; probe++) {
  const seq = probe * 100;
  const query = { tenantId: tenant40(seq), seq, _id: expected40[seq]._id };
  const docs = lab40.events.find(query).readConcern("majority").maxTimeMS(5000).toArray();
  printjson({ probe: seq, documents: docs });
  check35(docs.length === 1 && [1, 2].includes(docs[0].revision), "Unexpected probe state");
  exactDocs40([{ ...docs[0], revision: 1 }], [expected40[seq]]);
}
```

Save those observations. Only if they establish the chapter's interrupted probe writes, reset confirmed revision-2 probes:

```javascript
for (let probe = 0; probe < 12; probe++) {
  const seq = probe * 100;
  const query = { tenantId: tenant40(seq), seq, _id: expected40[seq]._id, revision: 2 };
  const result = lab40.events.updateOne(query, { $set: { revision: 1 } }, { writeConcern: wc40 });
  check35(result.acknowledged, "Probe reset uncertain");
  printjson({ seq, result });
}
printjson(verify40());
```

This idempotent training-field reset is not a general replay strategy for business writes. Any other missing document, duplicate ID or field mismatch remains a failed acceptance gate requiring investigation.

## 15. Guarded cleanup and original-fixture verification

Restore the original services before cleanup:

```bash
dc start cfg1 cfg2 cfg3 a1 a2 a3 b1 b2 b3 r1 r2
client40 verify40.js
```

Save **`scripts/cleanup40.js`**:

```javascript
load("/scripts/lib40.js");
router35();
for (const spec of sets35) check35(ready35(spec), "Restore original members first");
const saved = ownership40();
check35(["baseline", "distributed"].includes(saved.phase), "Resolve preparation/migration first");
placement40(saved.phase);
verify40();
const collections = lab40.getCollectionNames();
check35(collections.length === 2 && collections.every(n => ["events", "control"].includes(n)),
  "Unexpected collection; stop cleanup");
check35(catalog40.tags.countDocuments({ ns: ns40 }) === 0, "Unexpected owned namespace zone");
check35(sh.enableBalancing(ns40).ok === 1, "Cannot restore collection default");
check35(db.adminCommand({ configureCollectionBalancing: ns40, enableAutoMerger: true }).ok === 1,
  "Cannot restore collection AutoMerger default");
check35(lab40.dropDatabase().ok === 1, "Scoped drop failed");
check35(!catalog40.collections.findOne({ _id: ns40 }) &&
  catalog40.tags.countDocuments({ ns: ns40 }) === 0, "Catalog cleanup incomplete");
check35(equal40(policy40(), saved.policy), "Global maintenance policy changed");
printjson({ cleanupComplete: true, originalFixtureRetained: true, policy: policy40() });
```

```bash
client40 cleanup40.js > evidence-ch40/cleanup.json
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/' --quiet --eval 'const n="mongodb_enterprise_tutorial_ch40"; if(db.getSiblingDB(n).getCollectionNames().length || db.getSiblingDB("config").collections.findOne({_id:n+".events"})) throw new Error("Chapter cleanup incomplete"); print("Chapter 40 namespace absent");'
dc ps -a
```

Cleanup accepts a verified baseline or distributed phase. An interrupted `redistributing` phase must be resolved before dropping the fixture; inspect and resume its existing intent after any outstanding migration finishes. An interrupted preparation requires inspection of the exact owned UUID and partial data, not rerunning the fresh setup blindly.

Preserve evidence and the Chapter 35 cluster. No volume deletion, Docker pruning, shard removal, replica reinitialization or global configuration reset is required. Dropping an owned training fixture is not a rollback plan for migrated production data.

## 16. Acceptance checklist and review questions

- [ ] Recorded image digest, patch/shell versions, stable FCV and healthy original topology.
- [ ] Owned compound-key fixture has 1200 unique IDs, expected tenant counts and sum 719,400.
- [ ] Baseline four ranges belong to A; full data and representative routing pass.
- [ ] Baseline workload completes all 120 reads and 12 reconciled write probes.
- [ ] R1/R3 migration outcomes resolve; key/UUID stay unchanged and A/B each own 600 logical events.
- [ ] Distributed routing shows targeted full-key points and intended tenant/global fan-out.
- [ ] Identical distributed workload passes; raw timings/resources retained without unsupported scaling claims.
- [ ] r1 failure is a genuine connection failure; r2 verification/workload passes; both restored endpoints pass.
- [ ] Complete chapter metadata/index consistency check has no findings.
- [ ] Previous chapter runtime evidence is linked or marked not tested, without invented passes.
- [ ] Capacity, actual driver recovery and backup restore limitations are recorded.
- [ ] Chapter namespace removed; original 1001-document fixture passes through both routers; global policy/tags preserved.

**Evidence:** Setup/ownership inventory, exact ranges and reconciled counts, before/after explains, raw workload timings and acknowledgements, migration responses/owners, resource/log observations, outage error, surviving/restored endpoint checks, full metadata cursor, acceptance worksheet and cleanup. Record actual failures and timings. Runtime lab validation remains pending until these steps execute on the recorded deployment.

**Review questions:**

1. Why does registering two shards not prove that this collection uses both?
2. Which suffix makes tenant 0 divisible, and what request now fans out?
3. How can logical data be balanced while request load remains skewed?
4. Why does a `{seq:1}` index not guarantee targeted routing for this compound key?
5. What does manual migration leave unproven about the automatic balancer?
6. Why are physical donor bytes different from current logical range ownership?
7. How do you resolve an unknown migration or write outcome before replaying work?
8. Why can't this serial timing run establish production maximum throughput?
9. Which previous sharding and recovery gates still need their own evidence?
10. What production capacity and backup checks must precede a real expansion decision?

## 17. References and next chapter

- [MongoDB 8.0: sharding](https://www.mongodb.com/docs/v8.0/sharding/)
- [MongoDB 8.0: choose a shard key](https://www.mongodb.com/docs/v8.0/core/sharding-choose-a-shard-key/)
- [MongoDB 8.0: balancer and migration behavior](https://www.mongodb.com/docs/v8.0/core/sharding-balancer-administration/)
- [MongoDB 8.0: moveChunk](https://www.mongodb.com/docs/v8.0/reference/command/moveChunk/)
- [MongoDB 8.0: explain](https://www.mongodb.com/docs/v8.0/reference/method/cursor.explain/)
- [MongoDB 8.0: metadata consistency](https://www.mongodb.com/docs/v8.0/reference/method/db.checkMetadataConsistency/)
- [Chapter 35 — Build a Sharded Lab Cluster](35-build-a-sharded-lab-cluster.md)
- [Chapter 36 — Chunk Distribution Balancing and Zones](36-chunk-distribution-balancing-and-zones.md)
- [Chapter 37 — Targeted Queries Scatter Gather and Hot Shards](37-targeted-queries-scatter-gather-and-hot-shards.md)
- [Chapter 38 — Resharding and Shard Key Refinement](38-resharding-and-shard-key-refinement.md)
- [Chapter 39 — Sharded Cluster Administration and Recovery](39-sharded-cluster-administration-and-recovery.md)

Next: **[Chapter 41 — Users Roles and Least Privilege](41-users-roles-and-least-privilege.md)**.
