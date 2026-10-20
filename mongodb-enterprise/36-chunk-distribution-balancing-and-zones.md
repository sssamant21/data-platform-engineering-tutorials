# 36 — Chunk Distribution Balancing and Zones

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 5 — Sharding and Scale  
**Goal:** Inspect range placement, rehearse a scoped manual migration, observe automatic correction of zone violations, reject overlapping zone ranges and remove all chapter-owned configuration.  
**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Time:** 120–150 minutes  
**Baseline:** MongoDB 8.0 and mongosh; reuse and record the pinned Chapter 35 image digest and exact versions.  
**Deployment:** Retained isolated `mongodb-ch35` cluster, with two routers, dedicated `cfg35` and data shards `shard35a`/`shard35b`. Community-compatible.  
**Prerequisites:** Chapters 33–35, healthy original cluster, completed Chapter 35 outage recovery and its 1001-document fixture, no concurrent migration/resharding/maintenance exercise, and cluster administration plus scoped CRUD access where authentication applies.

## 1. Placement is a policy and an observed state

**Use case:** An event service has two logical regions. Events tagged `east` should reside on eligible eastern shards and `west` events on western shards. Before treating this as a production placement policy, verify the key ranges, eligible shards, actual owners and application data.

A chunk is a catalog interval in shard-key order. Range migration changes ownership and copies data; splitting an interval creates finer catalog boundaries without itself moving the data. A zone associates key ranges with eligible shards. Creating a zone range does not synchronously move every affected document to its intended destination.

The lab creates a small owned collection, aligns its boundaries, stages its east/west data on the wrong shards while collection balancing is paused, defines zones, and enables collection balancing. Automatic movement to eligible shards is the acceptance evidence. A manual migration alone is not proof that the balancer works.

## 2. What to measure

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| Chunk bounds and owners | Catalog placement and interval granularity | Equal bytes, equal QPS or equal latency |
| Logical reads through mongos | Application-visible documents under routing/filtering | Completion of donor-side physical cleanup |
| Distribution/storage output | Per-shard storage observations at that time | A workload demand measurement |
| Balancer enabled state | Cluster policy permits balancing | A round is currently running or can migrate this namespace |
| Collection balancing setting | Namespace participates in automatic balancing | Manual migrations are prohibited |
| Collection compliance result | Catalog needs/no longer needs placement correction at that moment | Application correctness, good key design or healthy resource headroom |
| Zone memberships and ranges | Placement policy and eligible destinations | Proven physical geography, regulatory compliance or disaster isolation |

Modern balancing considers data distribution and policy rather than aiming for an identical chunk count. Small collections can remain uneven without meeting a size-based migration threshold. Do not generate hundreds of megabytes or change global range-size settings just to force a demonstration.

Automatic splitting behavior also differs from older tutorials: on this baseline, the old autosplit switches do not restore historical insert-triggered splitting. Manual splits below provide deliberate boundaries for this fixture. Migrations, balancing and automatic merging can subsequently change granularity.

## 3. Zone-key design and migration tradeoffs

The chapter collection uses `{region:1,eventId:1}`, both ranged. The region prefix makes the placement policy expressible; the event suffix provides distinct tuples within a region. This is a teaching key, not a throughput recommendation. An increasing suffix can still concentrate new writes at a boundary within a hot region.

| Zone | Eligible shard | Inclusive lower bound | Exclusive upper bound | Fixture documents |
|---|---|---|---|---|
| `CH36_EAST` | `shard35a` | `{region:"east",eventId:MinKey}` | `{region:"east",eventId:MaxKey}` | 420 |
| `CH36_WEST` | `shard35b` | `{region:"west",eventId:MinKey}` | `{region:"west",eventId:MaxKey}` | 180 |

Every fixture event ID is an ordinary string, so it lies between these sentinel bounds. Adjacent keyspace outside these two intervals is unzoned. An actual sentinel-valued document at an exclusive maximum is outside the zone; do not generalize this policy to arbitrary BSON values without reviewing bounds.

A zone with one eligible shard constrains capacity to that shard. To distribute a region across multiple shards, the zone needs multiple eligible destinations and suitable key granularity. Hashing a region prefix would express placement in hashed keyspace rather than meaningful region order. For hashed keys, manual `moveChunk` selection uses actual catalog bounds, not `sh.moveChunk` with an unhashed document predicate.

Migration consumes donor/recipient CPU, cache, disk, network and replication capacity. The metadata handoff and physical removal are separate stages. Keep application reads through `mongos`; summing raw direct-shard counts during migration can count donor remnants as though they were application duplicates.

## 4. Resume and verify the Chapter 35 cluster

Use **Bash** in the original `mongodb-ch35` folder, with its `.env`, `compose.yaml` and complete Chapter 35 scripts. If you removed the original project/data, execute Chapter 35 again through acceptance first. This chapter does not invent a replacement for its retained prerequisite fixture.

```bash
dc() { docker compose -p mongodb-ch35 -f compose.yaml "$@"; }
set -a
source .env
set +a
dc ps -a
dc start cfg1 cfg2 cfg3 a1 a2 a3 b1 b2 b3
docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh --nodb --quiet --eval 'load("/scripts/lib35.js"); for (const s of sets35) wait35(s.name, () => ready35(s));'
dc start r1 r2
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
```

`start` resumes existing containers; if they no longer exist, follow Chapter 35's retained-volume resume procedure and validate ownership first. Router readiness can require a bounded retry of the read-only verifier. Do not continue past a failed prerequisite check.

Connect to `mongos`; sections 5–12 use this **same session**:

```bash
docker run --rm -it --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017,r2:27017/?readPreference=primary&serverSelectionTimeoutMS=5000'
```

No host ports or additional networks are needed. The lab retains Chapter 35's isolation and synthetic-data boundary. In an authenticated cluster, approved cluster management privileges are distinct from fixture CRUD permissions; a permission error is not the intended failure exercise.

## 5. Guard ownership and record original configuration

```javascript
load("/scripts/lib35.js");
router35();
for (const s of sets35) wait35("preflight " + s.name, () => ready35(s));
const name36 = "mongodb_enterprise_tutorial_ch36";
const ns36 = name36 + ".events";
const lab36 = db.getSiblingDB(name36);
const catalog36 = db.getSiblingDB("config");
const zones36 = ["CH36_EAST", "CH36_WEST"];
const wc36 = { w: "majority", j: true, wtimeout: 10000 };
check35(lab36.getCollectionNames().length === 0, "Chapter database exists; inspect before rerunning");
check35(!catalog36.collections.findOne({ _id: ns36 }), "Unexpected existing catalog namespace");
check35(catalog36.tags.countDocuments({ ns: ns36 }) === 0 &&
  catalog36.tags.countDocuments({ tag: { $in: zones36 } }) === 0, "Chapter zone names/ranges already used");
const originalShards36 = catalog36.shards.find({}).toArray();
check35(originalShards36.length === 2 && originalShards36.every(s => !s.draining &&
  !(s.tags || []).some(t => zones36.includes(t))), "Unexpected draining shard or zone membership");
const globalEnabled36 = sh.getBalancerState();
const globalSettings36 = catalog36.settings.findOne({ _id: "balancer" });
check35(globalEnabled36 === true, "Global balancer disabled; resolve existing lab state before this exercise");
check35(!globalSettings36 || !globalSettings36.activeWindow,
        "Existing balancing window; resolve lab scheduling before this exercise");
const ownership36 = {
  _id: "ownership", namespace: ns36, zones: zones36,
  globalEnabled: globalEnabled36, globalSettings: globalSettings36,
  shardTags: originalShards36.map(s => ({ shard: s._id, tags: [...(s.tags || [])].sort() })),
  priorCollectionBalancing: true, priorAutoMerger: true,
  phase: "owned-fresh-namespace", createdAt: new Date()
};
check35(lab36.control.insertOne(ownership36, { writeConcern: wc36 }).acknowledged,
        "Ownership record not acknowledged");
printjson(ownership36);
printjson({ server: db.version(), shell: version(), globalEnabled: globalEnabled36 });
```

Save this ownership record in your external lab evidence as well. It survives a shell interruption in the owned `control` collection. Fresh namespace defaults establish the prior balancing/AutoMerger behavior; this is not a mechanism for resetting an existing collection's custom settings.

Global balancing stays enabled throughout. The lab does not change a balancing window, migration throttle, chunk-size setting, shard membership in a replica set or process parameter. If somebody else changes global policy while you work, investigate instead of overwriting their change.

## 6. Observe the existing hashed collection without changing it

```javascript
const ns35Baseline36 = "mongodb_enterprise_tutorial_ch35.events";
const existing35Meta36 = catalog36.collections.findOne({ _id: ns35Baseline36 });
check35(existing35Meta36 && existing35Meta36.uuid, "Chapter 35 sharded metadata missing");
const existing35Chunks36 = catalog36.chunks.find({ uuid: existing35Meta36.uuid }).toArray();
printjson(existing35Chunks36.map(c => ({ shard: c.shard, min: c.min, max: c.max })));
db.getSiblingDB("mongodb_enterprise_tutorial_ch35").events.getShardDistribution();
printjson(db.adminCommand({ balancerCollectionStatus: ns35Baseline36 }));
printjson(db.adminCommand({ balancerStatus: 1 }));
```

Record observed owners, chunk counts and distribution for the hashed collection. Do not manually move its ranges to make a screenshot look symmetric. A compliant tiny collection is not evidence that the cluster can sustain a production ingestion rate.

## 7. Create the isolated ranged fixture and pause its automation

```javascript
check35(lab36.createCollection("events").ok === 1, "Create failed");
const events36 = lab36.events;
events36.createIndex({ region: 1, eventId: 1 }, { name: "region_event" });
const created36 = db.adminCommand({ shardCollection: ns36, key: { region: 1, eventId: 1 } });
check35(created36.ok === 1, "Sharding failed: " + EJSON.stringify(created36));
sh.disableBalancing(ns36);
check35(catalog36.collections.findOne({ _id: ns36 }).noBalance === true, "Collection balancing not paused");
const mergeOff36 = db.adminCommand({ configureCollectionBalancing: ns36, enableAutoMerger: false });
check35(mergeOff36.ok === 1, "Cannot pause AutoMerger for fixture boundaries");
const meta36 = catalog36.collections.findOne({ _id: ns36 });
check35(meta36.key.region === 1 && meta36.key.eventId === 1 && meta36.uuid &&
        meta36.allowMigrations !== false, "Unexpected collection key/UUID/migration policy");
check35(lab36.control.updateOne({ _id: "ownership" },
  { $set: { uuid: meta36.uuid, phase: "collection-automation-paused" } },
  { writeConcern: wc36 }).matchedCount === 1, "Ownership checkpoint missing");
const fixture36 = Array.from({ length: 600 }, (_, i) => ({
  _id: "ch36-" + String(i).padStart(4, "0"),
  eventId: "event-" + String(i).padStart(4, "0"),
  region: i < 420 ? "east" : "west", seq: i, revision: 1,
  payload: "x".repeat(128)
}));
const inserted36 = events36.insertMany(fixture36, { ordered: true, writeConcern: wc36 });
check35(inserted36.acknowledged && Object.keys(inserted36.insertedIds).length === 600,
        "Fixture insertion incomplete");
function verifyData36() {
  const docs = events36.find({}).sort({ seq: 1 }).toArray();
  check35(docs.length === 600, "Wrong fixture total");
  for (let i = 0; i < 600; i++) {
    const d = docs[i];
    check35(d._id === "ch36-" + String(i).padStart(4, "0") &&
      d.eventId === "event-" + String(i).padStart(4, "0") && d.seq === i &&
      d.region === (i < 420 ? "east" : "west") && d.revision === 1 &&
      d.payload === "x".repeat(128), "Fixture mismatch at " + i);
  }
  const total = events36.aggregate([{ $group: { _id: null, n: { $sum: 1 },
    seqSum: { $sum: "$seq" } } }]).toArray()[0];
  check35(total.n === 600 && total.seqSum === 179700, "Fixture sum mismatch");
  check35(events36.countDocuments({ region: "east" }) === 420 &&
    events36.countDocuments({ region: "west" }) === 180, "Region count mismatch");
  return total;
}
printjson(verifyData36());
```

Collection-level balancing and AutoMerger are paused only for this new namespace. Manual migration remains available; `disableBalancing` is different from prohibiting migrations. The AutoMerger pause keeps manual boundaries stable while you stage placement. The command above uses `enableAutoMerger`, available in this baseline; it does not depend on the newer `enableBalancing` command option introduced in 8.0.10.

Any uncertain write must be reconciled before replay. Do not drop/recreate a partially populated namespace to hide an unexplained failure. Section 15 provides recovery cleanup even after loss of this interactive session.

## 8. Split at the four zone boundaries

```javascript
const eastMin36 = { region: "east", eventId: MinKey };
const eastMax36 = { region: "east", eventId: MaxKey };
const westMin36 = { region: "west", eventId: MinKey };
const westMax36 = { region: "west", eventId: MaxKey };
function chunks36() { return catalog36.chunks.find({ uuid: meta36.uuid }).toArray(); }
function same36(a, b) { return EJSON.stringify(a) === EJSON.stringify(b); }
for (const boundary of [eastMin36, eastMax36, westMin36, westMax36]) {
  if (!chunks36().some(c => same36(c.min, boundary))) {
    const split36 = sh.splitAt(ns36, boundary);
    check35(split36.ok === 1, "Split failed: " + EJSON.stringify(split36));
  }
}
function exactChunk36(min, max) {
  const matches = chunks36().filter(c => same36(c.min, min) && same36(c.max, max));
  check35(matches.length === 1, "Expected one exact fixture range; inspect catalog");
  return matches[0];
}
printjson(exactChunk36(eastMin36, eastMax36));
printjson(exactChunk36(westMin36, westMax36));
printjson(chunks36().map(c => ({ min: c.min, max: c.max, shard: c.shard })));
printjson(verifyData36());
```

Expected: one exact east interval and one exact west interval, plus intervals covering the rest of keyspace. Do not assert a production collection must have this small fixture's exact total chunk count. The splits alone preserve all 600 documents and do not establish movement to another shard.

`MinKey` and `MaxKey` are BSON values, not the strings `"MinKey"` and `"MaxKey"`. Keep the complete compound-key field order/types in boundaries. Never manufacture bounds by converting BSON catalog values to ordinary JSON strings.

## 9. Rehearse a manual migration before defining zones

```javascript
function moveExact36(min, max, to) {
  check35(["shard35a", "shard35b"].includes(to), "Destination outside owned cluster");
  const old = exactChunk36(min, max);
  if (old.shard !== to) {
    const moved = db.adminCommand({ moveChunk: ns36, bounds: [old.min, old.max], to });
    check35(moved.ok === 1, "Migration failed: " + EJSON.stringify(moved));
    wait35("range owner " + to, () => exactChunk36(min, max).shard === to);
    printjson({ from: old.shard, to, min: old.min, max: old.max, moved });
  }
  printjson(verifyData36());
}
const eastOriginal36 = exactChunk36(eastMin36, eastMax36).shard;
const eastOther36 = eastOriginal36 === "shard35a" ? "shard35b" : "shard35a";
moveExact36(eastMin36, eastMax36, eastOther36);
moveExact36(eastMin36, eastMax36, eastOriginal36);
// Deliberately stage both nonempty ranges on the future ineligible shard.
moveExact36(eastMin36, eastMax36, "shard35b");
moveExact36(westMin36, westMax36, "shard35a");
check35(exactChunk36(eastMin36, eastMax36).shard === "shard35b" &&
  exactChunk36(westMin36, westMax36).shard === "shard35a", "Wrong staged placement");
check35(lab36.control.updateOne({ _id: "ownership" },
  { $set: { phase: "wrong-placement-staged" } }, { writeConcern: wc36 }).matchedCount === 1,
  "Checkpoint failed");
```

The out-and-back move proves a real ownership change even if initial placement differs between runs. The later two moves stage a known zone violation; zones are not yet defined, so these are currently legal placements.

A command timeout does not prove that ownership stayed on the source. Re-read exact current bounds/owner and reconcile data before repeating a migration. No `forceJumbo`, replication-throttle override or synchronous donor-deletion option is used. A committed owner change does not prove old physical copies have already been removed. Do not delete donor documents manually.

## 10. Define eligible shards and zone ranges

```javascript
function command36(result, label) {
  check35(result && result.ok === 1, label + ": " + EJSON.stringify(result));
}
command36(sh.addShardToZone("shard35a", "CH36_EAST"), "East membership");
command36(sh.addShardToZone("shard35b", "CH36_WEST"), "West membership");
command36(sh.updateZoneKeyRange(ns36, eastMin36, eastMax36, "CH36_EAST"), "East range");
command36(sh.updateZoneKeyRange(ns36, westMin36, westMax36, "CH36_WEST"), "West range");
function policy36() {
  const ranges = catalog36.tags.find({ ns: ns36 }).sort({ tag: 1 }).toArray();
  check35(ranges.length === 2, "Expected exactly two zone ranges");
  for (const [zone, min, max, shard] of [
    ["CH36_EAST", eastMin36, eastMax36, "shard35a"],
    ["CH36_WEST", westMin36, westMax36, "shard35b"]
  ]) {
    const range = ranges.find(r => r.tag === zone);
    check35(range && same36(range.min, min) && same36(range.max, max), "Zone bounds mismatch");
    const eligible = catalog36.shards.find({ tags: zone }).toArray().map(s => s._id).sort();
    check35(same36(eligible, [shard]), "Unexpected eligible shard for " + zone);
  }
  return ranges;
}
printjson(policy36());
check35(catalog36.collections.findOne({ _id: ns36 }).noBalance === true,
        "Fixture balancing unexpectedly enabled during staging");
const violation36 = db.adminCommand({ balancerCollectionStatus: ns36 });
command36(violation36, "Compliance query");
check35(exactChunk36(eastMin36, eastMax36).shard === "shard35b" &&
  exactChunk36(westMin36, westMax36).shard === "shard35a", "Staged owners changed unexpectedly");
printjson(violation36);
printjson(verifyData36());
```

Expected: policy records exist, east remains on B and west on A, and those owners are outside their eligible zones. Record the compliance response separately, including whether it reports `zoneViolation` while collection balancing is paused. Do not replace the actual response with an expected one or equate a paused namespace's status with completed correction. Configuration acknowledgement is not placement acceptance.

## 11. Enable collection balancing and verify automatic correction

```javascript
const balanceStarted36 = Date.now();
sh.enableBalancing(ns36);
check35(catalog36.collections.findOne({ _id: ns36 }).noBalance !== true,
        "Collection balancing not enabled");
wait35("automatic zone placement", () => {
  const east = exactChunk36(eastMin36, eastMax36);
  const west = exactChunk36(westMin36, westMax36);
  return east.shard === "shard35a" && west.shard === "shard35b";
}, 600000);
const compliant36 = db.adminCommand({ balancerCollectionStatus: ns36 });
command36(compliant36, "Final compliance query");
check35(compliant36.balancerCompliant === true, "Placement still requires correction");
printjson({ elapsedMs: Date.now() - balanceStarted36,
  east: exactChunk36(eastMin36, eastMax36), west: exactChunk36(westMin36, westMax36),
  compliant: compliant36 });
printjson(policy36());
printjson(verifyData36());
events36.getShardDistribution();
check35(lab36.control.updateOne({ _id: "ownership" },
  { $set: { phase: "automatic-zone-placement-verified" } },
  { writeConcern: wc36 }).matchedCount === 1, "Checkpoint failed");
```

The ten-minute bound is an operational stop point, not a convergence SLA. No manual migration is used during this wait. If it times out, inspect collection/global policy, logs, topology, active migrations, recipient capacity and replication; keep the fixture/evidence. A manual correction can help diagnose access but does not make the automatic-balancer acceptance pass.

The intentionally wrong zone placement supplies a policy reason to migrate even though the fixture is too small for an ordinary size-imbalance demonstration. Final east/west application counts remain 420/180. That asymmetry follows the fixture and its one-shard-per-zone policy; it is not a failed attempt to reach 300/300. Preserve the actual distribution output, including any donor-remnant effects, separately from logical verification.

AutoMerger remains paused for this namespace until cleanup so the two exact intervals remain stable for subsequent checks. Other collections retain their existing behavior.

## 12. Failure exercise: overlapping zone ranges

**Trigger:** Attempt a third range spanning the already configured east/west ranges. **Expected:** `RangeOverlapConflict`, code 178 on this baseline. **Diagnosis:** Range overlap is invalid policy; valid adjacent nonoverlapping ranges are different from a spanning overlap. **Repair:** Preserve the two correct ranges and verify their placement rather than deleting them to accommodate the bad request.

```javascript
const policyBeforeFailure36 = EJSON.stringify(policy36());
let overlapError36 = null;
try {
  const bad36 = db.adminCommand({ updateZoneKeyRange: ns36,
    min: eastMin36, max: westMax36, zone: "CH36_EAST" });
  if (bad36.ok !== 1) overlapError36 = bad36;
} catch (e) {
  overlapError36 = { code: e.code, codeName: e.codeName, errmsg: String(e) };
}
check35(overlapError36 && (overlapError36.code === 178 ||
  overlapError36.codeName === "RangeOverlapConflict"), "Expected overlap rejection; preserve actual result");
printjson(overlapError36);
check35(EJSON.stringify(policy36()) === policyBeforeFailure36, "Valid zone policy changed");
check35(exactChunk36(eastMin36, eastMax36).shard === "shard35a" &&
  exactChunk36(westMin36, westMax36).shard === "shard35b", "Placement changed unexpectedly");
printjson(verifyData36());
```

Do not count authorization, command syntax or network errors as overlap rejection. If the server unexpectedly accepts the request or changes the policy, preserve the response and actual `config.tags` state, stop progression and use the owned-name cleanup procedure after diagnosis. The normal failure path requires no destructive repair because the invalid change never committed.

## 13. Production review and operational limits

Validate a proposed placement policy against actual shard location, storage/capacity, backups, monitoring and application routing. Lab shard names `A`/`B` and labels `east`/`west` do not prove geographic or regulatory residency. Replicas and backup destinations also need review.

Prepare an eligible destination before moving data: resource headroom, healthy replication, network throughput and indexes matter. Membership changes can initiate migrations; removing a shard from a zone is not a harmless label edit if it makes existing placement invalid. A zone with no eligible destination cannot converge.

Prefer normal balancing for routine placement. Use manual splits/migrations for a specific reviewed need, with bounded scope and before/after data checks. Investigate repeated key values, jumbo/indivisible ranges, replication lag and migration errors instead of repeatedly forcing movement. A hot document remains hot when moved; placement alone does not redistribute its write contention.

For large collections, assess balancer thresholds using the exact version and actual collection range-size configuration. Global windows can defer correction. Balancing activity competes with application and backup traffic. Do not change global thresholds, enable forced jumbo movement or start defragmentation as an incident reflex. Planned resharding/redistribution is covered later and has its own capacity/recovery requirements.

## 14. Troubleshooting

| Symptom | Evidence | Likely cause | Action |
|---|---|---|---|
| Chunk counts differ but no migration occurs | Compliance result, bytes, configured range size | Difference below threshold or allowed policy | Record actual condition; do not infer failure from chunk count alone |
| Collection remains on wrong-zone shard | Tags, eligible shards, bounds, global/collection policy | Balancing paused, window, migration restriction or failing migration | Diagnose each gate and recipient health; avoid manual success substitution |
| `zoneViolation` persists | Full range/owner map and logs | Invalid placement still needs correction | Restore eligible capacity and wait within an agreed bound |
| Split rejects the boundary | Exact command, BSON fields/types, current bounds | Already split, missing full key or invalid bound | Read current catalog; do not retry fabricated JSON bounds |
| Hashed manual movement fails | Selector and key pattern | Document `find` used for hashed key | Use current BSON catalog `bounds` with the command |
| Zone range overlaps another | Code/name, current ranges | Intersecting policy intervals | Redesign nonoverlapping ranges; preserve valid policy |
| No shard is eligible for a zone | Zone memberships and shard health | Missing/removed eligible destination | Add approved capacity/membership after assessing data movement |
| Logical counts differ after migration | mongos exact ID/value verification, errors | Mutation, partial fixture or consistency problem | Stop acceptance; reconcile evidence and diagnose |
| Physical storage exceeds logical data | Distribution and migration cleanup state | Donor remnants, indexes, storage allocation | Separate cleanup/storage from logical correctness; never delete donor copies by hand |
| Manual boundaries disappear | AutoMerger/configuration and catalog | Automatic merge or concurrent maintenance | Verify namespace pause/ownership; do not assert one static layout universally |
| Cleanup cannot restore memberships | Recorded baseline and current tags | Shared-name conflict or concurrent change | Preserve ledger and resolve ownership; remove only chapter-owned tags |

## 15. Scoped cleanup and interruption recovery

Normal completion removes the Chapter 36 fixture and both owned zone definitions/memberships, restoring the new namespace's defaults before dropping it. Preserve evidence first. Chapter 37 can use the original Chapter 35 cluster; no Chapter 36 zone restriction is carried forward implicitly.

Save **`scripts/cleanup36.js`** and execute it in a **fresh mongosh process**. It reads the persistent ownership record, so it can also clean up after an interrupted split, migration or zone step. If the ledger is missing, do not invent a baseline; use the external evidence and inspect ownership first.

```javascript
load("/scripts/lib35.js");
router35();
for (const spec of sets35) wait35("cleanup " + spec.name, () => ready35(spec));
const cleanName36 = "mongodb_enterprise_tutorial_ch36";
const cleanNs36 = cleanName36 + ".events";
const cleanLab36 = db.getSiblingDB(cleanName36);
const cleanCatalog36 = db.getSiblingDB("config");
const cleanZones36 = ["CH36_EAST", "CH36_WEST"];
const record36 = cleanLab36.control.findOne({ _id: "ownership" });
check35(record36 && record36.namespace === cleanNs36 &&
  EJSON.stringify(record36.zones) === EJSON.stringify(cleanZones36), "Missing/wrong ownership record");
check35(cleanLab36.getCollectionNames().every(n => ["events", "control"].includes(n)),
        "Unexpected collections; preserve chapter database");
check35(record36.priorCollectionBalancing === true && record36.priorAutoMerger === true,
        "Unexpected prior fixture defaults");
check35(sh.getBalancerState() === record36.globalEnabled &&
  EJSON.stringify(cleanCatalog36.settings.findOne({ _id: "balancer" })) ===
  EJSON.stringify(record36.globalSettings), "Global policy changed; inspect instead of overwriting");
const ownedRanges36 = cleanCatalog36.tags.find({ ns: cleanNs36 }).toArray();
check35(ownedRanges36.every(r => cleanZones36.includes(r.tag)), "Unexpected zone range; inspect ownership");
check35(cleanCatalog36.tags.countDocuments({ tag: { $in: cleanZones36 }, ns: { $ne: cleanNs36 } }) === 0,
        "Owned zone name now used by another namespace; stop cleanup");
const cleanMeta36 = cleanCatalog36.collections.findOne({ _id: cleanNs36 });
if (cleanMeta36) {
  check35(!record36.uuid || EJSON.stringify(cleanMeta36.uuid) === EJSON.stringify(record36.uuid),
          "Namespace UUID changed; preserve replacement collection");
  sh.disableBalancing(cleanNs36);
}
// Remove ranges using their exact recorded current BSON bounds; never edit config.tags directly.
for (const r of ownedRanges36) {
  const removed = sh.updateZoneKeyRange(cleanNs36, r.min, r.max, null);
  check35(removed.ok === 1, "Zone range removal failed");
}
for (const s of cleanCatalog36.shards.find({ tags: { $in: cleanZones36 } }).toArray()) {
  for (const zone of (s.tags || []).filter(t => cleanZones36.includes(t))) {
    check35(sh.removeShardFromZone(s._id, zone).ok === 1, "Zone membership removal failed");
  }
}
check35(cleanCatalog36.tags.countDocuments({ ns: cleanNs36 }) === 0 &&
  cleanCatalog36.shards.countDocuments({ tags: { $in: cleanZones36 } }) === 0,
  "Owned zone configuration remains");
for (const baseline of record36.shardTags) {
  const s = cleanCatalog36.shards.findOne({ _id: baseline.shard });
  check35(s && EJSON.stringify([...(s.tags || [])].sort()) === EJSON.stringify(baseline.tags),
          "Original shard tags differ; preserve evidence");
}
if (cleanMeta36) {
  const restored = db.adminCommand({ configureCollectionBalancing: cleanNs36, enableAutoMerger: true });
  check35(restored.ok === 1, "AutoMerger default restoration failed");
  sh.enableBalancing(cleanNs36);
  check35(cleanCatalog36.collections.findOne({ _id: cleanNs36 }).noBalance !== true,
          "Collection balancing default not restored");
}
check35(cleanLab36.getName() === "mongodb_enterprise_tutorial_ch36",
        "Refusing cleanup outside the Chapter 36 training database");
check35(cleanLab36.dropDatabase().ok === 1, "Owned database removal failed");
check35(cleanLab36.getCollectionNames().length === 0 &&
  !cleanCatalog36.collections.findOne({ _id: cleanNs36 }) &&
  cleanCatalog36.tags.countDocuments({ ns: cleanNs36 }) === 0,
  "Namespace cleanup incomplete");
printjson({ cleaned: cleanName36, globalBalancerUnchanged: true, shardTagsRestored: true });
```

If a migration is active, retain its response/logs and allow it to resolve before cleanup; disabling collection balancing does not undo an in-flight ownership handoff. A transient conflict must be diagnosed and retried within a bounded window. The script intentionally stops on unexpected policy/UUID/tag changes rather than removing another exercise's state.

```bash
docker run --rm --network mongodb-ch35_cluster -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?readPreference=primary&serverSelectionTimeoutMS=5000' --quiet --file /scripts/cleanup36.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
docker run --rm --network mongodb-ch35_cluster -e EXPECTED_COUNT=1001 -v "$PWD/scripts:/scripts:ro" "$MONGO_IMAGE" mongosh 'mongodb://r2:27017/?serverSelectionTimeoutMS=5000' --quiet --file /scripts/verify35.js
```

On `r2`, also confirm that the Chapter 36 database has no collections and that its namespace/zone ranges are absent from the catalog. Do not replay the cleanup after its ownership record has been removed; verify the final state read-only instead.

Dropping the fixture reverses this lab's data/configuration footprint; it does not move valuable production data back to former shards. The manual out-and-back exercise records its original owner for immediate placement reversal before zones. Removing a zone permits future placement changes; it does not synchronously restore historical ownership. No global Docker teardown, pruning or config-database drop is needed.

## 16. Acceptance, evidence and review

- [ ] Recorded original pinned versions, healthy topology and Chapter 35's 1001-document verification.
- [ ] Recorded global balancer policy and original shard tags; owned zone names were initially unused.
- [ ] Created only the Chapter 36 fixture/control collections and scoped their automation changes.
- [ ] Reconciled all 600 exact documents, east 420, west 180 and seq sum 179700.
- [ ] Verified full compound BSON boundaries and real out-and-back manual ownership movement.
- [ ] Staged east on B and west on A, verified both policy violations and recorded the compliance response.
- [ ] Enabled collection balancing and observed automatic correction without manual intervention during the wait.
- [ ] Verified final eligible placement, compliance and unchanged logical data.
- [ ] Classified overlapping range rejection and verified valid policy remained intact.
- [ ] Removed owned ranges/memberships/namespace, restored defaults and original shard tags, and preserved global policy.
- [ ] Reverified Chapter 35 data/topology through both routers and cleanup through r2.

**Evidence:** Ownership record, baseline catalog/distribution/status, supporting index/key/UUID, split bounds, manual movement responses, exact fixture verification, zone policy and staged violation, timed automatic owner changes, compliance result, failure error/policy checks and cleanup outputs. Record not exercised/failed steps honestly. Runtime validation remains pending until this lab executes on the recorded environment.

**Review questions:**

1. Why can unequal chunk counts be compatible with an acceptable collection state?
2. What is the difference between a split, a migration and donor cleanup?
3. Why are bounds inclusive at the minimum and exclusive at the maximum?
4. Why is `disableBalancing` different from disabling migrations?
5. What evidence distinguishes automatic correction from a successful manual move?
6. Why do the final counts remain 420/180 rather than 300/300?
7. How does a zone with only one eligible shard limit growth?
8. Why must hashed chunk moves preserve BSON catalog bounds?
9. What happens if valid zone ranges exist but no eligible shard is available?
10. Why does removing a zone not constitute restoration of historical data placement?

## 17. Official references

- [MongoDB 8.0: sharded cluster balancer](https://www.mongodb.com/docs/v8.0/core/sharding-balancer-administration/)
- [MongoDB 8.0: data partitioning with chunks](https://www.mongodb.com/docs/v8.0/core/sharding-data-partitioning/)
- [MongoDB 8.0: balancerCollectionStatus](https://www.mongodb.com/docs/v8.0/reference/command/balancerCollectionStatus/)
- [MongoDB 8.0: moveChunk](https://www.mongodb.com/docs/v8.0/reference/command/moveChunk/)
- [MongoDB 8.0: splitAt](https://www.mongodb.com/docs/v8.0/reference/method/sh.splitAt/)
- [MongoDB 8.0: updateZoneKeyRange](https://www.mongodb.com/docs/v8.0/reference/method/sh.updateZoneKeyRange/)
- [MongoDB 8.0: manage shard zones](https://www.mongodb.com/docs/v8.0/tutorial/manage-shard-zone/)
- [MongoDB 8.0: configureCollectionBalancing](https://www.mongodb.com/docs/v8.0/reference/command/configureCollectionBalancing/)
- [MongoDB 8.0: disableBalancing](https://www.mongodb.com/docs/v8.0/reference/method/sh.disableBalancing/)
- [MongoDB server error names](https://github.com/mongodb/mongo/blob/master/src/mongo/base/error_codes.yml)

---

Previous: [Chapter 35 — Build a Sharded Lab Cluster](35-build-a-sharded-lab-cluster.md)  
Next: **[Chapter 37 — Targeted Queries Scatter Gather and Hot Shards](37-targeted-queries-scatter-gather-and-hot-shards.md)**.
