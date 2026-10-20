# 24 — CPU Memory Storage IOPS and Capacity

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Inventory effective resource limits, measure a bounded workload, distinguish logical/allocated/device capacity, and build explicit growth and I/O headroom calculations.  
**Audience:** DBREs, SREs and Platform Engineers  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; Linux observation commands require their stated tools. Record exact versions.  
**Deployment:** Community-compatible or Enterprise training mongod, standalone or replica-set primary, with unsharded ordinary collections.

## 1. Capacity is a workload envelope

A server size is useful only in relation to an accepted workload: read/write mix, query shapes, concurrency, document/index sizes, working set, retention, background tasks and latency objectives.

A system can have free disk capacity while saturating IOPS. It can stay below provisioned IOPS while hitting throughput or instance-level storage limits. It can have idle CPU while requests wait on storage, locks or connection pools. Increasing one resource does not automatically remove another bottleneck.

This chapter builds a measurement and calculation workflow. It does not prescribe a universal node size or run a destructive saturation test. Chapters 21–23 provide the query and storage-engine evidence needed to avoid sizing around unnecessary work.

## 2. Keep units and boundaries explicit

| Quantity | Meaning | Do not substitute |
|---|---|---|
| Logical BSON bytes | Application document representation | Allocated disk bytes |
| Collection storageSize | Allocation for document storage | Total filesystem usage |
| totalIndexSize | Allocation for collection indexes | Complete node storage |
| Filesystem free bytes | Available capacity on mounted filesystem | Provisioned IOPS/throughput |
| IOPS | Device operations per second | MongoDB requests per second |
| MiB/s | Bytes transferred per second divided by 2^20 | Decimal MB/s without conversion |
| CPU cores used | CPU-seconds consumed per wall-second | Host CPU percentage without denominator |
| WiredTiger cache bytes | Internal storage-engine cache | Total process/container memory |

Storage budgets also include oplog, journal, diagnostics/logs, internal data, temporary build/sort work and operational reserves. Backups on another service have their own capacity/cost policy; local backup staging still consumes local space.

Replica-set data-bearing members generally need their own full data/index capacity. Multiplying a per-member volume by member count estimates replicated storage cost, not one member's free space. Sharding changes distribution but does not remove replicas, skew or maintenance reserves.

## 3. Resource evidence worksheet

Before selecting a larger instance or volume, record:

| Resource | Configured/effective limit | Observed peak | Pressure evidence |
|---|---|---|---|
| CPU | vCPU count, CPU quota, container requests/limits | Cores used and run queue | Throttling, runnable work, latency |
| Memory | VM RAM, container limit, engine cache maximum | RSS, cache, OS/container working set | OOM, reclaim, swap, page faults |
| Storage capacity | Mounted volume bytes and free space | Allocated data/index/log growth | Forecast time-to-reserve, temp needs |
| Storage performance | Volume AND instance IOPS/throughput limits | Read/write operations and bytes | Latency, queue depth, throttling/burst limits |
| Network | Effective bandwidth/connection limits | Traffic, connections, retransmits | Replication lag or response transfer delay |
| Workload | Query shapes, request mix, concurrency | Arrival/completion rate, latency | Queue growth and retries |

Provider limits and instance specifications can change. Record the actual selected SKU/volume configuration and current provider documentation when sizing a real deployment; this tutorial uses synthetic capacities rather than quoting a current cloud price/performance table.

## 4. Prerequisites and permissions

Complete Chapters 05, 21 and 23. Connect using the approved training URI from Chapter 06. Use the primary for writes/index creation on a replica set.

The training operator needs collection/read/write/index/statistics/cleanup access on the chapter database and authorized serverStatus monitoring access. Optional OS observations require existing host access. This chapter does not install packages, change sysctls, resize volumes or alter resource limits.

In mongosh:

```javascript
const labName24 = "mongodb_enterprise_tutorial_ch24";
const lab24 = db.getSiblingDB(labName24);
const hello24 = db.adminCommand({ hello: 1 });
if (hello24.msg === "isdbgrid" || !hello24.isWritablePrimary) {
  throw new Error("Use a writable training mongod");
}
if (lab24.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
function check24(condition, message) {
  if (!condition) throw new Error(message);
}
const status24 = db.adminCommand({ serverStatus: 1 });
check24(status24.ok === 1, "serverStatus unavailable");
printjson({
  serverVersion: db.version(), host: status24.host,
  uptime: status24.uptime, processMemory: status24.mem,
  connections: status24.connections,
  wiredTigerMaximumCacheBytes: status24.wiredTiger &&
    status24.wiredTiger.cache["maximum bytes configured"]
});
```

Record mongosh --version and effective VM/container settings separately. serverStatus.mem is not a full container/node memory accounting report.

## 5. Optional Linux observations

Run on the authorized database host, not an unrelated bastion. Substitute the actual database data mount after inspecting deployment configuration.

```bash
lscpu
free -h
df -hT
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
vmstat 1 10
iostat -xz 1 10
```

These are read-only observations. iostat requires sysstat; if absent, record unavailable rather than installing software on a shared host as part of the lab. The first vmstat/iostat report can describe averages since boot; compare interval reports for the workload window.

Interpret device mapping carefully for LVM, RAID, cloud disks and container mounts. Filesystem free space and underlying device limits can have different boundaries. Do not sum parent/child device activity as independent I/O.

For containers, collect the actual cgroup CPU/memory limits and throttling counters through existing monitoring. Host free memory does not establish container headroom. On Kubernetes, record pod requests/limits, node allocatable capacity, OOM/throttling events and shared-node workloads.

No OS tuning commands are part of this chapter. In particular, older MongoDB recommendations for Transparent Huge Pages must not be copied blindly to MongoDB 8.0; check the version-specific production notes before a separate reviewed host change.

## 6. Build and measure a small fixture

Create 10,000 documents, each with a 1 KiB repeated synthetic payload. This compressible fixture is intentionally unsuitable as a universal storage ratio.

```javascript
lab24.createCollection("events");
const events24 = lab24.events;
const payload24 = "z".repeat(1024);
let batch24 = [];
const loadStart24 = Date.now();
for (let i = 0; i < 10000; i++) {
  batch24.push({
    _id: i, tenantId: "t" + (i % 10), seq: i,
    revision: 0, payload: payload24
  });
  if (batch24.length === 500) {
    events24.insertMany(batch24);
    batch24 = [];
  }
}
const loadElapsed24 = Date.now() - loadStart24;
events24.createIndex({ tenantId: 1, seq: -1 }, { name: "tenant_seq" });
check24(events24.countDocuments({}) === 10000, "Wrong total fixture");
check24(events24.countDocuments({ tenantId: "t3" }) === 1000,
        "Wrong tenant fixture");
const stats24 = lab24.runCommand({ collStats: "events", scale: 1 });
check24(stats24.ok === 1 && Number(stats24.count) === 10000,
        "Collection statistics mismatch");
printjson({
  documents: stats24.count,
  logicalBsonBytes: stats24.size,
  allocatedDocumentBytes: stats24.storageSize,
  allocatedIndexBytes: stats24.totalIndexSize,
  allocatedCollectionPlusIndexBytes: stats24.totalSize,
  indexSizes: stats24.indexSizes,
  loadElapsedMs: loadElapsed24
});
```

Keep scale: 1 so reported size fields are bytes. Interpret size, storageSize and totalIndexSize separately. The collection total excludes other node directories, journal/oplog and maintenance reserves.

Do not extrapolate this fixture's compression ratio to varied production documents. Small allocation granularity, existing free pages and compression all affect the measured relationship.

## 7. Run bounded application work and reconcile it

Read twenty newest events for one tenant ten times, then update exactly 500 records. No concurrent load generator is used.

```javascript
const expectedSeq24 = Array.from({ length: 20 }, (_, i) => 9993 - i * 10);
const readSamples24 = [];
for (let run = 0; run < 10; run++) {
  const started = Date.now();
  const rows = events24.find({ tenantId: "t3" })
    .sort({ seq: -1 }).limit(20).hint("tenant_seq").toArray();
  check24(JSON.stringify(rows.map(r => Number(r.seq))) ===
          JSON.stringify(expectedSeq24), "Read result mismatch");
  readSamples24.push(Date.now() - started);
}
const updateStart24 = Date.now();
const update24 = events24.updateMany(
  { _id: { $lt: 500 } }, { $inc: { revision: 1 } }
);
check24(update24.matchedCount === 500 && update24.modifiedCount === 500,
        "Wrong update scope");
check24(events24.countDocuments({ revision: 1 }) === 500,
        "Updated records did not reconcile");
check24(events24.countDocuments({ revision: 0 }) === 9500,
        "Untouched records changed");
printjson({
  readElapsedMsSamples: readSamples24,
  updateElapsedMs: Date.now() - updateStart24,
  updatedDocuments: update24.modifiedCount
});
```

If collecting OS metrics, align their timestamps with this window. A short serial fixture may finish before a useful host sampling interval. Record that limitation; do not infer peak capacity from an idle-looking graph.

These timings are tiny shell observations, not accepted QPS or P95 capacity. A production acceptance test needs representative query mix, arrival rate, concurrency, durability, background work and longer steady intervals.

## 8. CPU and memory reasoning

CPU utilization must state its denominator. Four cores used on an eight-vCPU VM is different from a pod limited to two cores on that VM. A single busy thread can constrain some work while aggregate CPU appears low.

Distinguish CPU saturation from storage wait and cgroup throttling. Increasing concurrency can increase queues and memory without increasing completed throughput. Inspect query work before purchasing more CPU.

Memory budget includes engine cache, filesystem cache, process overhead, connections, execution/sort/aggregation work and OS/shared workloads. Avoid adding overlapping exporter “working set” categories as if they were all independent allocations.

Use Chapter 23's cache/churn evidence and actual container/process metrics together. A database size larger than RAM does not automatically fail; the active working set and access patterns matter. A small database can still exhaust memory through unbounded query/concurrency behavior.

## 9. IOPS and throughput can constrain different workloads

Approximate transfer rate:

**MiB/s = operations/second × average bytes/operation ÷ 1,048,576**

Average request size and read/write mix matter. Device operations are not one-to-one with MongoDB requests because caching, compression, journaling, checkpoints and write amplification change physical work.

Use synthetic limits to compare two cases:

```javascript
const MiB24 = 1024 * 1024;
const GiB24 = 1024 * MiB24;
function ioEnvelope24(iops, bytesPerOperation, maxIops, maxMiBps) {
  check24(iops >= 0 && bytesPerOperation > 0 &&
          maxIops > 0 && maxMiBps > 0, "Invalid I/O model input");
  const mibps = iops * bytesPerOperation / MiB24;
  return {
    requestedIops: iops, requestedMiBps: mibps,
    iopsUtilization: iops / maxIops,
    throughputUtilization: mibps / maxMiBps,
    withinLimits: iops <= maxIops && mibps <= maxMiBps
  };
}
const smallIo24 = ioEnvelope24(4000, 4096, 3000, 125);
const largeIo24 = ioEnvelope24(1000, 256 * 1024, 3000, 125);
check24(smallIo24.requestedMiBps === 15.625 && !smallIo24.withinLimits,
        "Small-I/O example wrong");
check24(largeIo24.requestedMiBps === 250 && !largeIo24.withinLimits,
        "Large-I/O example wrong");
printjson({ smallIo: smallIo24, largeIo: largeIo24 });
```

The small-I/O case exceeds IOPS despite low throughput. The large-I/O case exceeds throughput despite staying below IOPS. These are arithmetic examples, not measured MongoDB demand.

Effective performance is bounded by the whole path: volume configuration, instance attachment limits, storage/controller/filesystem behavior and competing traffic. Burst credits or cached reads can make short observations misleading.

Latency and queue depth reveal pressure that utilization percentages alone may miss. Do not treat device busy percentage as a universal SSD saturation threshold.

## 10. Storage growth and reserves

Use projected data/index allocation plus explicit operational reserves. This synthetic worksheet assumes:

- Current allocated data/index: 500 GiB.
- Net allocated growth: 8 GiB/day.
- Planning horizon: 30 days.
- Oplog reserve: 50 GiB.
- Journal/log/diagnostic reserve: 20 GiB.
- Temporary maintenance reserve: 100 GiB.
- Target maximum planned occupancy: 75%.

```javascript
function storagePlan24(input) {
  check24(input.currentBytes >= 0 && input.growthBytesPerDay >= 0 &&
          input.days >= 0 && input.targetOccupancy > 0 &&
          input.targetOccupancy < 1, "Invalid storage inputs");
  const projectedDataBytes =
    input.currentBytes + input.growthBytesPerDay * input.days;
  const plannedUsedBytes = projectedDataBytes +
    input.oplogBytes + input.logsJournalBytes + input.maintenanceBytes;
  return {
    projectedDataBytes,
    plannedUsedBytes,
    minimumVolumeBytes: plannedUsedBytes / input.targetOccupancy
  };
}
const capacityInput24 = {
  currentBytes: 500 * GiB24,
  growthBytesPerDay: 8 * GiB24,
  days: 30,
  oplogBytes: 50 * GiB24,
  logsJournalBytes: 20 * GiB24,
  maintenanceBytes: 100 * GiB24,
  targetOccupancy: 0.75
};
const plan24 = storagePlan24(capacityInput24);
check24(plan24.projectedDataBytes / GiB24 === 740, "Wrong growth projection");
check24(plan24.plannedUsedBytes / GiB24 === 910, "Wrong reserve budget");
printjson({
  projectedDataGiB: plan24.projectedDataBytes / GiB24,
  plannedUsedGiB: plan24.plannedUsedBytes / GiB24,
  minimumVolumeGiB: plan24.minimumVolumeBytes / GiB24
});
```

The calculated minimum is approximately 1,213.33 GiB, before selecting an actual provisionable volume size. The 75% target and reserve values are teaching assumptions, not MongoDB hard limits or universal recommendations.

Maintenance reserve should reflect the chosen operation: index build, resharding, initial sync, migration or restore can have different temporary requirements. Model concurrent operations deliberately instead of reusing 100 GiB everywhere.

Forecast from measured allocated growth over representative intervals. Net growth includes deletes, reuse, retention changes and index changes; document count alone is insufficient.

## 11. Failure exercise: logical size is not filesystem usage

A faulty worksheet treats a collection's logical BSON size as the entire node's used space. Demonstrate a synthetic undercount without relying on this fixture's compression:

```javascript
const misleadingLogicalBytes24 = 100 * GiB24;
const actualAllocatedDataIndex24 = 180 * GiB24;
const otherNodeBytes24 = 40 * GiB24;
const volumeBytes24 = 300 * GiB24;
const wrongUsedFraction24 = misleadingLogicalBytes24 / volumeBytes24;
const correctedUsedFraction24 =
  (actualAllocatedDataIndex24 + otherNodeBytes24) / volumeBytes24;
check24(correctedUsedFraction24 > wrongUsedFraction24,
        "Expected logical-size undercount example");
printjson({
  incorrectPercent: wrongUsedFraction24 * 100,
  correctedPercent: correctedUsedFraction24 * 100
});
```

Diagnosis: mixed boundaries omitted allocated indexes and other node files. Correct by reconciling collection allocation, other database/internal allocation and filesystem observations without double-counting.

Logical bytes can also exceed compressed physical allocation. There is no universal direction or conversion factor. Compare each metric according to its definition rather than assuming size always equals disk use.

Deletion can free reusable space within files without immediately shrinking filesystem allocation. Do not promise instant volume reclamation from TTL or deleteMany.

## 12. Time to an operational reserve

A useful alert asks how long until free space reaches a chosen reserve at the observed growth rate:

```javascript
function daysToReserve24(freeBytes, reserveBytes, netGrowthBytesPerDay) {
  check24(freeBytes >= 0 && reserveBytes >= 0 &&
          netGrowthBytesPerDay >= 0, "Invalid forecast");
  if (freeBytes <= reserveBytes) return 0;
  if (netGrowthBytesPerDay === 0) return null;
  return (freeBytes - reserveBytes) / netGrowthBytesPerDay;
}
check24(daysToReserve24(300 * GiB24, 100 * GiB24, 8 * GiB24) === 25,
        "Time-to-reserve calculation wrong");
check24(daysToReserve24(100 * GiB24, 100 * GiB24, 8 * GiB24) === 0,
        "Reserve breach not detected");
check24(daysToReserve24(300 * GiB24, 100 * GiB24, 0) === null,
        "Zero-growth result should be indeterminate");
printjson({ daysUntilReserve: daysToReserve24(
  300 * GiB24, 100 * GiB24, 8 * GiB24
) });
```

A null result here means no finite forecast from a zero-growth assumption, not proof that the volume is permanently safe. Sudden imports, index builds or stalled cleanup can change growth.

Use warning/critical thresholds based on response lead time and operation reserves, not only fixed percentages. Capacity procurement and deployment time must fit inside the forecast margin.

## 13. Production acceptance test design

Define the target request mix, dataset/distribution, working set, arrival rate, concurrency, read/write concerns, connection pool and latency/error objectives. Include relevant TTL cleanup, checkpoints, backups, replication and maintenance overlap.

Increase workload in bounded reviewed steps while monitoring completion rate, queueing, resource pressure and errors. Define stop conditions before running: latency/error breach, replication lag, memory pressure or reserve depletion. Do not fill a production disk or exhaust memory to discover the limit.

Repeat representative peak intervals and validate results, not just request counts. Record bottlenecks and scaling assumptions. A larger instance test should prove the intended objective under the same contract.

For HA, size the surviving topology for expected traffic and recovery overlap; healthy steady-state capacity is not failover capacity. Replica-set acceptance follows in Chapters 25–32.

## 14. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Slow queries with spare CPU | Explain, storage latency, pool wait | I/O or waiting bottleneck | Fix evidenced constraint before adding cores |
| CPU below host maximum but pod throttles | Effective quota and throttling counters | Container CPU limit | Review limits and workload concurrency |
| High memory with modest cache | RSS/container metrics and execution workload | Other allocations or unbounded work | Assess total budget and query shape |
| Below IOPS limit but high disk latency | Bytes/s, queue, instance limit | Throughput/path bottleneck | Validate whole-path capacity |
| Free disk but write stalls | I/O service metrics | Performance rather than byte capacity | Address storage service rate |
| Document deletions do not shrink volume | Allocation/reuse and df | Freed space remains in files | Plan reuse/reclamation separately |
| Growth forecast misses reserve | Imports, index/maintenance changes | Nonrepresentative growth window | Reforecast with operation-aware scenarios |
| Lab graph appears idle | Sampling interval and workload duration | Short serial test | Record limit; use representative acceptance workload |

## 15. Cleanup

Save collection statistics, workload results and capacity assumptions first:

```javascript
check24(events24.countDocuments({}) === 10000, "Fixture changed");
check24(events24.countDocuments({ revision: 1 }) === 500,
        "Updated fixture changed");
if (lab24.getName() !== "mongodb_enterprise_tutorial_ch24") {
  throw new Error("Refusing cleanup outside the Chapter 24 training database");
}
const dropResult24 = lab24.dropDatabase();
check24(dropResult24.ok === 1, "Database cleanup command failed");
check24(lab24.getCollectionNames().length === 0, "Cleanup incomplete");
```

No infrastructure settings, limits or disk layouts changed. No configuration rollback is needed. Dropping the chapter database is not a promise of instant filesystem shrink.

## 16. Acceptance and evidence

- [ ] Recorded exact server/shell versions and effective CPU/memory/storage limits.
- [ ] Distinguished logical, allocated and filesystem capacity.
- [ ] Loaded and reconciled 10,000 records and exact read results.
- [ ] Verified 500 updated and 9,500 untouched documents.
- [ ] Recorded observation timing and short-lab limitations.
- [ ] Verified IOPS-bound and throughput-bound arithmetic examples.
- [ ] Built a growth forecast with explicit reserve/occupancy assumptions.
- [ ] Corrected a logical-size-only capacity mistake.
- [ ] Calculated time-to-reserve and handled zero growth.
- [ ] Defined representative production acceptance scope and completed cleanup.

**Evidence:** version/resource inventory, OS observation interval if available, collection sizes, result/update assertions, synthetic calculation inputs/outputs, forecast assumptions and cleanup. Runtime validation remains pending until executed. Arithmetic examples do not establish measured production capacity.

## 17. Review questions

1. Why can throughput saturate while IOPS remains below its limit?
2. Why is MongoDB request rate not equivalent to device IOPS?
3. Which allocations are absent from one collection's totalSize?
4. How does a pod's CPU limit change host utilization interpretation?
5. Why can low CPU coexist with poor request latency?
6. Which assumptions can invalidate a linear storage forecast?
7. Why must maintenance and failover overlap be part of capacity acceptance?
8. Why does this small serial workload not establish an accepted QPS limit?

## 18. Official references

- [MongoDB 8.0: production notes](https://www.mongodb.com/docs/v8.0/administration/production-notes/)
- [MongoDB 8.0: collection size/allocation statistics](https://www.mongodb.com/docs/v8.0/reference/command/collStats/)
- [MongoDB 8.0: serverStatus monitoring](https://www.mongodb.com/docs/v8.0/reference/command/serverStatus/)
- [MongoDB 8.0: WiredTiger cache and storage](https://www.mongodb.com/docs/v8.0/core/wiredtiger/)
- [MongoDB 8.0: storage FAQ](https://www.mongodb.com/docs/v8.0/faq/storage/)

---

Previous: [Chapter 23 — WiredTiger Cache Eviction and Checkpoints](23-wiredtiger-cache-eviction-and-checkpoints.md)  
Next: [Chapter 25 — Replica Set Architecture and Oplog](25-replica-set-architecture-and-oplog.md).
