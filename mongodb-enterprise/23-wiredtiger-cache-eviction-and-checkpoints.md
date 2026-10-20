# 23 — WiredTiger Cache Eviction and Checkpoints

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Collect comparable WiredTiger snapshots around bounded reads/writes, distinguish gauges from counters, observe checkpoints and diagnose misleading cache-pressure conclusions.  
**Audience:** DBREs, SREs and Platform Engineers  
**Time:** 90–120 minutes, including a bounded checkpoint observation window  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions and available metric names.  
**Deployment:** Self-managed Community or Enterprise training mongod using WiredTiger; standalone or replica-set primary. Not mongos.

## 1. Cache occupancy is not a diagnosis

WiredTiger keeps working pages in its internal cache. MongoDB also benefits from the operating system's filesystem cache. Process memory additionally includes connections, execution work, allocators and other components. WiredTiger cache bytes are not equivalent to mongod RSS or total container memory.

A busy cache is often doing useful work. High occupancy becomes actionable when combined with sustained read churn, eviction work, dirty-data pressure, application-thread involvement, storage latency and foreground latency. Do not declare an incident from one occupancy percentage.

This chapter observes normal bounded work. It intentionally does not fill memory, shrink cache aggressively, create long-running transactions or change internal eviction parameters to manufacture an incident. A small lab may produce no meaningful eviction; that is an observation, not a failed exercise.

## 2. Four related mechanisms

| Mechanism | Purpose | Evidence boundary |
|---|---|---|
| Internal cache | Hold working pages used by the storage engine | Engine bytes/pages, not complete process memory |
| Eviction | Make space by removing/reconciling eligible pages | Healthy background work and pressure must be distinguished |
| Checkpoint | Establish a consistent on-disk storage-engine point | Periodic persistence, not a per-write acknowledgement |
| Journal | Support recovery of changes between checkpoints | Different from query caching, backup and replication durability |

Dirty pages contain changes that still need storage-engine processing. Evicting clean pages and reconciling dirty pages have different work. Active snapshots/transactions can affect what history/pages remain needed.

MongoDB configures periodic checkpoints, commonly around a 60-second interval. Runtime duration and workload can affect observation. Do not require a checkpoint to occur at an exact wall-clock second.

Write concern, journaling and replica-set durability have distinct contracts. A successfully observed checkpoint is not proof of a backup restore, high availability or a majority-acknowledged write policy. Do not delete journal or WiredTiger files as an operational cleanup technique.

## 3. What to collect before changing anything

Record server version, storage engine, member/host, uptime, configured cache maximum, container/VM memory limits, storage type and workload interval. A container memory limit and the host's RAM are not interchangeable.

Use the actual reported maximum cache bytes for interpretation. Do not infer a safe custom cache setting from a generic percentage of host memory without checking deployment limits and other memory users.

Useful metric groups:

| Metric class | Example | Interpretation |
|---|---|---|
| Gauge | bytes currently in the cache | Point-in-time occupancy |
| Gauge | tracked dirty bytes in the cache | Current dirty-data estimate |
| Configuration/gauge | maximum bytes configured | Denominator for occupancy |
| Cumulative counter | pages read into cache | Difference over a comparable interval |
| Cumulative counter | pages written from cache | Engine page-write work over interval |
| Cumulative counter | modified/unmodified pages evicted | Eviction activity, if exposed |
| Duration gauge | most recent checkpoint time | Last observed checkpoint duration |
| Cumulative duration | checkpoint total time | Delta of accumulated checkpoint time |

Metric labels can change with bundled WiredTiger versions. Preserve actual output keys and unavailable fields. Never map a missing metric to zero simply to make a dashboard complete.

## 4. Prerequisites and permissions

Complete Chapters 03, 05 and 21–22. Connect using the approved training URI from Chapter 06. The training operator needs serverStatus monitoring access, plus collection/read/write/index/cleanup access on the chapter database.

The built-in clusterMonitor role can supply relevant monitoring privileges, but this chapter does not grant roles. Use an already authorized operator. No cache resizing, process restart, profiler activation or global parameter changes are required.

In mongosh:

```javascript
const labName23 = "mongodb_enterprise_tutorial_ch23";
const lab23 = db.getSiblingDB(labName23);
const hello23 = db.adminCommand({ hello: 1 });
if (hello23.msg === "isdbgrid") throw new Error("Connect to mongod, not mongos");
if (!hello23.isWritablePrimary) throw new Error("Use a writable training server");
if (lab23.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
function check23(condition, message) {
  if (!condition) throw new Error(message);
}
const initialStatus23 = db.adminCommand({ serverStatus: 1 });
check23(initialStatus23.ok === 1, "serverStatus unavailable");
check23(initialStatus23.storageEngine &&
        initialStatus23.storageEngine.name === "wiredTiger",
        "This lab requires WiredTiger");
printjson({
  serverVersion: db.version(),
  host: initialStatus23.host,
  uptime: initialStatus23.uptime,
  storageEngine: initialStatus23.storageEngine,
  replicaSet: hello23.setName || null
});
```

Record mongosh --version and deployment memory/storage configuration separately. serverStatus metrics belong to the entire process, not this database alone. Shared workloads can contribute during every observation interval.

## 5. Build a version-aware snapshot helper

For these short lab intervals, numeric conversion is convenient. Production collectors should preserve large integer precision; cumulative BSON 64-bit counters may exceed JavaScript's exact integer range.

```javascript
function metric23(group, name) {
  if (!group || !Object.hasOwn(group, name)) return null;
  const value = Number(group[name]);
  return Number.isFinite(value) ? value : null;
}
function snapshot23(label) {
  const status = db.adminCommand({ serverStatus: 1 });
  check23(status.ok === 1 && status.wiredTiger, "WiredTiger status unavailable");
  const cache = status.wiredTiger.cache || {};
  const transaction = status.wiredTiger.transaction || {};
  const sample = {
    label, host: status.host, uptime: Number(status.uptime),
    timestamp: status.localTime,
    cacheMaximum: metric23(cache, "maximum bytes configured"),
    cacheBytes: metric23(cache, "bytes currently in the cache"),
    dirtyBytes: metric23(cache, "tracked dirty bytes in the cache"),
    pagesRead: metric23(cache, "pages read into cache"),
    pagesWritten: metric23(cache, "pages written from cache"),
    unmodifiedEvicted: metric23(cache, "unmodified pages evicted"),
    modifiedEvicted: metric23(cache, "modified pages evicted"),
    checkpointRunning: metric23(transaction, "transaction checkpoint currently running"),
    checkpointGeneration: metric23(transaction, "transaction checkpoint generation"),
    checkpointRecentMs: metric23(transaction, "transaction checkpoint most recent time (msecs)"),
    checkpointTotalMs: metric23(transaction, "transaction checkpoint total time (msecs)"),
    rawCache: cache,
    rawTransaction: transaction
  };
  check23(sample.timestamp instanceof Date, "Snapshot timestamp unavailable");
  check23(sample.cacheMaximum !== null && sample.cacheMaximum > 0,
          "Cache maximum unavailable");
  check23(sample.cacheBytes !== null, "Cache occupancy unavailable");
  return sample;
}
function occupancy23(sample) {
  return {
    cachePercent: 100 * sample.cacheBytes / sample.cacheMaximum,
    dirtyPercent: sample.dirtyBytes === null ? null :
      100 * sample.dirtyBytes / sample.cacheMaximum
  };
}
function counterDelta23(before, after, key) {
  if (before.host !== after.host || after.uptime < before.uptime) {
    return { delta: null, ratePerSecond: null, note: "Different process/reset" };
  }
  if (before[key] === null || after[key] === null) {
    return { delta: null, ratePerSecond: null, note: "Metric unavailable" };
  }
  const seconds = (after.timestamp - before.timestamp) / 1000;
  const delta = after[key] - before[key];
  if (seconds <= 0 || delta < 0) {
    return { delta: null, ratePerSecond: null, note: "Invalid interval or counter reset" };
  }
  return { delta, ratePerSecond: delta / seconds };
}
function compare23(before, after) {
  const counters = {};
  for (const key of ["pagesRead", "pagesWritten", "unmodifiedEvicted",
                     "modifiedEvicted", "checkpointTotalMs"]) {
    counters[key] = counterDelta23(before, after, key);
  }
  const result = {
    from: before.label, to: after.label,
    beforeOccupancy: occupancy23(before),
    afterOccupancy: occupancy23(after), counters
  };
  printjson(result);
  return result;
}
const beforeLoad23 = snapshot23("before-load");
printjson({ label: beforeLoad23.label, ...occupancy23(beforeLoad23) });
printjson(Object.keys(beforeLoad23.rawCache).sort());
printjson(Object.keys(beforeLoad23.rawTransaction).sort());
```

The helper compares counters only across the same reported host and nondecreasing uptime. A production identity should also track process start/restart identity explicitly; hostname alone is insufficient.

Dirty percentage uses configured cache maximum as denominator. If your monitoring system defines a different ratio, label it precisely. Gauges may rise or fall; do not apply monotonic-counter rate logic to cacheBytes.

## 6. Load a bounded fixture

Create 8,000 documents with roughly 2 KiB of synthetic repeated payload each, plus ordinary metadata and an index. Compression means logical payload bytes are not a disk-size or cache-size prediction.

```javascript
lab23.createCollection("workload");
const workload23 = lab23.workload;
const payload23 = "x".repeat(2048);
let batch23 = [];
for (let i = 0; i < 8000; i++) {
  batch23.push({
    _id: i, tenantId: "t" + (i % 8), seq: i,
    revision: 0, payload: payload23
  });
  if (batch23.length === 500) {
    workload23.insertMany(batch23);
    batch23 = [];
  }
}
workload23.createIndex({ tenantId: 1, seq: -1 }, { name: "tenant_seq" });
check23(workload23.countDocuments({}) === 8000, "Wrong fixture total");
check23(workload23.countDocuments({ tenantId: "t3" }) === 1000,
        "Wrong tenant fixture count");
const afterLoad23 = snapshot23("after-load");
compare23(beforeLoad23, afterLoad23);
```

An index build and insert workload can contribute cache/page-write activity. The interval also includes validation reads. State those boundaries rather than attributing every server-wide counter change to one insert batch.

## 7. Read twice without claiming a cold-cache benchmark

Scan the named fixture while projecting payload, consume the cursor completely and verify the result:

```javascript
function scan23(label) {
  const started = Date.now();
  let count = 0;
  let payloadCharacters = 0;
  const cursor = workload23.find({}, { _id: 1, payload: 1 })
    .hint({ $natural: 1 }).batchSize(250);
  while (cursor.hasNext()) {
    const row = cursor.next();
    count++;
    payloadCharacters += row.payload.length;
  }
  check23(count === 8000, "Scan omitted fixture records");
  check23(payloadCharacters === 8000 * 2048, "Payload reconciliation failed");
  const result = { label, count, payloadCharacters, elapsedMs: Date.now() - started };
  printjson(result);
  return result;
}
const beforeRead23 = snapshot23("before-read");
const firstRead23 = scan23("first-read");
const afterFirstRead23 = snapshot23("after-first-read");
const secondRead23 = scan23("second-read");
const afterSecondRead23 = snapshot23("after-second-read");
compare23(beforeRead23, afterFirstRead23);
compare23(afterFirstRead23, afterSecondRead23);
```

The fixture may already be cached from insertion. A first scan here is not a cold read. A second scan may need few additional engine page reads, but do not require zero or a faster wall time.

Pages read into WiredTiger cache are not equivalent to physical device I/O: the filesystem cache can serve reads. Pair engine counters with storage latency/throughput and OS evidence before blaming a disk bottleneck.

The shell elapsed time includes transferring/materializing documents and looping through results. It is not the storage engine's isolated service time.

## 8. Write changes and inspect dirty/page-write behavior

Update only the first 1,000 known records, then reconcile the modified state:

```javascript
const beforeWrite23 = snapshot23("before-write");
const updated23 = workload23.updateMany(
  { _id: { $lt: 1000 } },
  { $inc: { revision: 1 } }
);
check23(updated23.matchedCount === 1000 && updated23.modifiedCount === 1000,
        "Wrong update scope");
check23(workload23.countDocuments({ revision: 1 }) === 1000,
        "Updated revisions did not reconcile");
check23(workload23.countDocuments({ revision: 0 }) === 7000,
        "Untouched revisions changed");
const afterWrite23 = snapshot23("after-write");
compare23(beforeWrite23, afterWrite23);
printjson({
  beforeDirtyBytes: beforeWrite23.dirtyBytes,
  afterDirtyBytes: afterWrite23.dirtyBytes
});
```

Dirty bytes can increase, or background work can process them before the next snapshot. Do not assert an exact dirty-byte increase from a logical update count. The gauges represent current engine state, not a one-to-one byte ledger for application writes.

Pages written can arise from checkpoint/reconciliation work and other databases. A successful update acknowledgement does not require this sample to show a completed checkpoint.

## 9. Observe checkpoint progress with a bounded window

Record checkpoint metric names available on your version. Prefer generation progress; use increasing cumulative checkpoint duration as supporting evidence when generation is unavailable.

```javascript
function checkpointAdvanced23(before, after) {
  if (before.host !== after.host || after.uptime < before.uptime) return false;
  if (before.checkpointGeneration !== null &&
      after.checkpointGeneration !== null &&
      after.checkpointGeneration > before.checkpointGeneration) return true;
  return before.checkpointTotalMs !== null &&
         after.checkpointTotalMs !== null &&
         after.checkpointTotalMs > before.checkpointTotalMs;
}
const checkpointStart23 = snapshot23("checkpoint-start");
check23(checkpointStart23.checkpointGeneration !== null ||
        checkpointStart23.checkpointTotalMs !== null,
        "No chosen checkpoint progress metric; inspect raw version-specific output");
const checkpointDeadline23 = Date.now() + 180000;
let checkpointEnd23 = checkpointStart23;
while (Date.now() < checkpointDeadline23) {
  sleep(5000);
  checkpointEnd23 = snapshot23("checkpoint-observation");
  if (checkpointAdvanced23(checkpointStart23, checkpointEnd23)) break;
}
check23(checkpointAdvanced23(checkpointStart23, checkpointEnd23),
        "No checkpoint progress within lab window; preserve evidence and diagnose");
printjson({
  startGeneration: checkpointStart23.checkpointGeneration,
  endGeneration: checkpointEnd23.checkpointGeneration,
  currentlyRunning: checkpointEnd23.checkpointRunning,
  recentDurationMs: checkpointEnd23.checkpointRecentMs,
  totalDurationMs: checkpointEnd23.checkpointTotalMs
});
compare23(checkpointStart23, checkpointEnd23);
```

Generation advancement shows progress/start rather than independently proving completion. A currently-running value of zero is an instantaneous observation. Do not call these checks a crash-recovery or backup-consistency test.

The 180-second window is a teaching observation budget. If it expires, record the available metrics, server logs and workload context. Do not force fsync, restart the server or alter checkpoint scheduling to manufacture a pass.

## 10. Failure exercise: a counter reset creates a false rate

Use synthetic snapshots to test interpretation logic. This does not restart a server:

```javascript
const syntheticBefore23 = {
  host: "training", uptime: 1000, timestamp: new Date("2026-01-01T00:00:00Z"),
  pagesRead: 10000
};
const syntheticAfter23 = {
  host: "training", uptime: 10, timestamp: new Date("2026-01-01T00:00:10Z"),
  pagesRead: 50
};
const resetResult23 = counterDelta23(
  syntheticBefore23, syntheticAfter23, "pagesRead"
);
check23(resetResult23.delta === null, "Reset was misinterpreted as a valid delta");
printjson(resetResult23);
const validAfter23 = {
  host: "training", uptime: 1010, timestamp: new Date("2026-01-01T00:00:10Z"),
  pagesRead: 10100
};
const validResult23 = counterDelta23(
  syntheticBefore23, validAfter23, "pagesRead"
);
check23(validResult23.delta === 100 && validResult23.ratePerSecond === 10,
        "Valid rate calculation failed");
```

Diagnosis: subtracting cumulative counters across process resets creates invalid negative deltas. Correct by breaking the interval at the reset and collecting a new baseline. Do not clamp a negative delta to zero and present it as measured inactivity.

Likewise, unavailable metrics are unknown rather than zero. This logic exercise validates arithmetic only; it does not prove monitoring behavior during failover.

## 11. Build an evidence-based pressure hypothesis

| Observation pattern | Possible explanation | Additional evidence needed |
|---|---|---|
| High occupancy, stable low latency | Useful working set in cache | Sustained churn, eviction and memory trend |
| Rising page reads, high storage latency | Working-set misses plus slow storage | Physical device I/O and query shapes |
| Dirty pressure with prolonged checkpoints | Write/reconciliation backlog | Write rate, storage throughput, checkpoint logs |
| Application-thread eviction rising | Foreground work assisting eviction | Request latency and concurrent workload |
| Low engine cache but high RSS/container usage | Other memory users or allocation behavior | Process/OS/container metrics |
| Few evictions in this lab | Fixture fits or pages are already warm | Larger representative workload, without unsafe pressure |
| Long-lived snapshots during pressure | History must remain available | Current transactions/snapshot age and application ownership |

These are hypotheses, not automatic root causes. Do not infer a cache size increase from one row. Broad queries, excessive concurrency, unsuitable indexes or a storage bottleneck can drive churn that more cache only masks temporarily.

Use actual available cache metric keys to identify application-thread eviction/read/write counters; their names differ by release. Record exact units and meanings before wiring alerts.

## 12. Production capacity and incident practice

Capture aligned intervals across WiredTiger, application latency, CPU, RSS/container memory, page faults, storage latency/queueing and replication lag. Include maintenance/index builds, backups, initial sync and TTL deletion because they can compete with foreground work.

Leave memory for the filesystem cache and other process/OS needs. Increasing internal cache can reduce room for those consumers. On Kubernetes, review limits, OOM events and node pressure, not just the host's free RAM.

Checkpoint durations should be compared with workload and storage service time. A periodic spike alone is insufficient evidence of a fault; sustained backlog and foreground impact make the case stronger.

Long transactions and historical reads can retain storage-engine history. Investigate owner and business purpose before interrupting them; use a reviewed operational response rather than blanket transaction termination.

Do not adjust wiredTigerEngineRuntimeConfig or internal eviction thresholds as a routine first fix. Such settings require version-specific expert guidance. Prefer reducing unnecessary work, validating indexes, shaping concurrency, correcting resource limits or addressing proven storage capacity problems.

Recovery evidence belongs in dedicated labs. This chapter does not simulate power loss, election, disk-full conditions or OOM, and does not establish durability or failover acceptance.

## 13. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| wiredTiger status absent | storageEngine, hello, privileges | Wrong process/engine or unauthorized status | Connect to authorized WiredTiger mongod |
| Metric null in helper | Raw keys and exact version | Name not exposed on this build | Preserve unavailable state; map documented actual metric |
| Negative counter delta | Host, uptime, timestamps | Restart/reset or mixed member samples | Start new baseline |
| Cache near maximum | Occupancy plus latency/churn | Normal residency or genuine pressure | Correlate before tuning |
| No eviction increase | Fixture size and warm state | Small workload fits cache | Record limitation; do not force memory exhaustion |
| Dirty bytes fall after updates | Checkpoint/reconciliation timing | Background work processed changes | Interpret as gauge, not failed write |
| Checkpoint polling times out | Raw transaction keys, logs, uptime | Missing mapping or delayed progress | Diagnose and mark observation unvalidated |
| Scan slow but engine reads low | Client timing, payload, network | Serialization/transfer or other waiting | Measure full request components |
| RSS exceeds cache bytes | Process/container/OS metrics | Additional memory users | Assess total memory budget |

## 14. Cleanup

Capture summaries and selected raw metric groups first. Validate data before dropping only this chapter database:

```javascript
check23(workload23.countDocuments({}) === 8000, "Fixture count changed");
check23(workload23.countDocuments({ revision: 1 }) === 1000,
        "Updated state changed");
if (lab23.getName() !== "mongodb_enterprise_tutorial_ch23") {
  throw new Error("Refusing cleanup outside the Chapter 23 training database");
}
const dropResult23 = lab23.dropDatabase();
check23(dropResult23.ok === 1, "Database cleanup command failed");
check23(lab23.getCollectionNames().length === 0, "Cleanup incomplete");
const afterCleanup23 = snapshot23("after-cleanup");
printjson({ label: afterCleanup23.label, ...occupancy23(afterCleanup23) });
```

Cache occupancy, RSS and filesystem allocation need not immediately return to their prelab values. Dropping a database is not a cache-flush command or a guarantee of instant OS memory/disk reclamation.

No server parameters, cache limits or profiler settings changed, so no configuration rollback is required. Do not restart or remove storage-engine files to make cleanup metrics look identical.

## 15. Acceptance and evidence

- [ ] Recorded exact versions, WiredTiger engine, host/uptime and deployment memory/storage limits.
- [ ] Collected actual cache/transaction metric keys and preserved unavailable fields.
- [ ] Loaded/reconciled 8,000 records and 1,000 tenant records.
- [ ] Consumed two full scans without calling the first a cold-cache test.
- [ ] Reconciled 1,000 modified records and 7,000 untouched records.
- [ ] Compared counter deltas separately from occupancy/dirty gauges.
- [ ] Observed checkpoint progress or recorded a diagnostic failure.
- [ ] Rejected a synthetic reset interval and verified valid-rate arithmetic.
- [ ] Explained cache occupancy versus process memory and physical disk I/O.
- [ ] Captured evidence and completed scoped cleanup.

**Evidence:** versions/host/uptime, infrastructure limits, metric names, snapshot timestamps, gauge/counter comparisons, scan totals/timings, update assertions, checkpoint observations, reset-classification results and cleanup. Runtime validation remains pending until the lab runs on the stated deployment.

## 16. Review questions

1. Why does high cache occupancy alone not establish memory pressure?
2. How can a page read into WiredTiger cache avoid physical device I/O?
3. Why can dirty bytes decrease immediately after an update interval?
4. Which metrics need deltas and which should remain point-in-time gauges?
5. What does checkpoint generation progress prove, and what does it not prove?
6. Why must counter intervals break across restarts or member changes?
7. Why can increasing engine cache harm the total memory budget?
8. Which evidence distinguishes broad-query churn from inadequate storage performance?

## 17. Official references

- [MongoDB 8.0: WiredTiger engine, cache and checkpoints](https://www.mongodb.com/docs/v8.0/core/wiredtiger/)
- [MongoDB 8.0: serverStatus WiredTiger metrics](https://www.mongodb.com/docs/v8.0/reference/command/serverStatus/)
- [MongoDB 8.0: self-managed storage FAQ](https://www.mongodb.com/docs/v8.0/faq/storage/)
- [MongoDB 8.0: server parameter boundaries](https://www.mongodb.com/docs/v8.0/reference/parameters/)
- [MongoDB 8.0: transaction production considerations](https://www.mongodb.com/docs/v8.0/core/transactions-production-consideration/)

---

Previous: [Chapter 22 — Profiling Slow Queries and Query Statistics](22-profiling-slow-queries-and-query-statistics.md)  
Next: [Chapter 24 — CPU Memory Storage IOPS and Capacity](24-cpu-memory-storage-iops-and-capacity.md).
