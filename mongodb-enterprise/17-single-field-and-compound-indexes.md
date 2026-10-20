# 17 — Single Field and Compound Indexes

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Compare a collection scan, a single-field index and a compound index against the same bounded query, then diagnose a sort-direction mismatch.  
**Audience:** Developers, Data Engineers, DBREs and SREs  
**Time:** 75–100 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions before running.  
**Deployment:** Community-compatible or Enterprise training server; standalone or replica-set primary. Use an unsharded collection for this lab.

## 1. An index serves a query contract

An index stores ordered keys and references to documents. Reads can use those keys to avoid examining every document. Inserts, deletes and updates to indexed fields also maintain index entries, so an index spends storage and write resources to improve particular reads.

Start with a real query contract: filter, sort, projection, limit and data distribution. “Index every field” is not a workload design. An index that appears in a plan can still examine many keys, fetch many documents or leave a blocking sort.

This chapter uses a synthetic work queue. Each tenant asks for its newest OPEN tasks, ordered by creation time and identifier. The result must contain the right tenant and status in a deterministic order. Performance improvements must preserve that result.

Chapter 18 develops equality/sort/range tradeoffs and covered queries. Chapter 19 handles multikey, partial, sparse and unique behavior. Here, keep scalar fields and ordinary indexes so the effects of key order are visible.

## 2. Single-field versus compound keys

| Index | Useful contract | Limitation to inspect |
|---|---|---|
| { tenantId: 1 } | Select one tenant | Status and ordering can require further work |
| { tenantId: 1, status: 1, createdAt: -1, _id: -1 } | Select tenant/status, return newest tasks | Status-only access lacks the leading tenant prefix |
| { tenantId: 1, status: 1, createdAt: -1, _id: 1 } | Same filter, different tie order | Does not supply createdAt descending AND _id descending |
| { createdAt: 1 } | Global chronological access | Tenant/status selectivity may be poor |

A compound key has an order. The leading prefixes of the main index are tenantId, tenantId/status, and tenantId/status/createdAt. Matching a later field does not make it a new leading prefix.

For equality predicates on both tenant and status, their order in the query document does not need to match their order in the index. Index key order still matters for other query shapes.

For a scalar single-field index, traversal can supply either ascending or descending ordering. For compound sorting, reverse traversal reverses the entire relevant ordering, not just one requested field. With tenant/status fixed, the main index supplies createdAt descending/_id descending and its complete reverse. It does not supply createdAt descending/_id ascending.

An index on _id already exists by default on this ordinary collection. Including _id as a final compound key provides the tie-break ordering within the tenant/status/time group; it does not replace the unique _id index.

## 3. Prerequisites and permissions

Complete Chapters 05–08 and 15. Connect using your approved training URI and credentials from Chapter 06. Do not paste passwords into the chapter or evidence.

The training user needs read/write, collection creation, index creation, index listing, index removal and database cleanup permissions on this chapter database. The hide/unhide exercise requires the corresponding index-modification privilege. A database-scoped role such as readWrite can supply relevant lab permissions; verify your actual custom role.

This lab intentionally does not need serverStatus, profiler configuration or cluster reconfiguration. For replica sets, connect to the primary for index changes. Do not run these index experiments against a production collection.

In mongosh:

```javascript
const labName17 = "mongodb_enterprise_tutorial_ch17";
const lab17 = db.getSiblingDB(labName17);
printjson({ serverVersion: db.version(), database: labName17 });
if (lab17.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
lab17.createCollection("tasks");
const tasks17 = lab17.tasks;
function check17(condition, message) {
  if (!condition) throw new Error(message);
}
```

Record mongosh --version separately. Explain structure can change between versions and execution engines; compare counters and the actual winning plan rather than copying a screenshot from another version.

## 4. Build a deterministic fixture

Create 20,000 small scalar documents in batches of 1,000. Ten tenants receive 2,000 tasks each. Status alternates independently within each tenant, so tenant-03 receives 1,000 OPEN tasks and 1,000 CLOSED tasks. Consecutive task pairs share a timestamp, making the identifier tie-break meaningful.

```javascript
const baseTime17 = Date.parse("2026-01-01T00:00:00Z");
let batch17 = [];
for (let i = 0; i < 20000; i++) {
  const tenantNumber = i % 10;
  const withinTenant = Math.floor(i / 10);
  batch17.push({
    _id: i,
    tenantId: "tenant-" + String(tenantNumber).padStart(2, "0"),
    status: withinTenant % 2 === 0 ? "OPEN" : "CLOSED",
    createdAt: new Date(baseTime17 + Math.floor(i / 2) * 1000),
    payload: "Synthetic task " + i
  });
  if (batch17.length === 1000) {
    tasks17.insertMany(batch17);
    batch17 = [];
  }
}
check17(tasks17.countDocuments({}) === 20000, "Wrong fixture count");
check17(tasks17.countDocuments({ tenantId: "tenant-03" }) === 2000,
        "Wrong tenant count");
check17(tasks17.countDocuments({
  tenantId: "tenant-03", status: "OPEN"
}) === 1000, "Wrong tenant/status count");
printjson(tasks17.getIndexes());
```

The initial index list should contain only _id_. If it contains other indexes, resolve the fixture setup before comparing plans. Do not proceed with a partially loaded dataset.

## 5. Define the result and evidence contract

The canonical query returns 20 newest OPEN tasks for tenant-03:

```javascript
const filter17 = { tenantId: "tenant-03", status: "OPEN" };
const order17 = { createdAt: -1, _id: -1 };
const projection17 = {
  _id: 1, tenantId: 1, status: 1, createdAt: 1, payload: 1
};
function query17(hint) {
  const cursor = tasks17.find(filter17, projection17)
    .sort(order17).limit(20);
  return hint === undefined ? cursor : cursor.hint(hint);
}
const expectedIds17 = Array.from({ length: 20 }, (_, n) => 19983 - n * 20);
function verifyRows17(rows) {
  check17(rows.length === 20, "Wrong page size");
  check17(JSON.stringify(rows.map(r => Number(r._id))) ===
          JSON.stringify(expectedIds17), "Wrong result order");
  check17(rows.every(r =>
    r.tenantId === "tenant-03" && r.status === "OPEN"),
    "Query escaped tenant/status scope");
}
verifyRows17(query17({ $natural: 1 }).toArray());
```

The newest eligible identifier is 19983, followed by 19963, 19943 and so on. This is derived from the fixture, rather than treating a baseline query as the only correctness oracle.

Projection includes payload, which is absent from the experimental compound index. Therefore the index must fetch returned documents. This chapter does not claim a covered query.

Collect explain output using executionStats. It runs the query plan; it is not a free metadata inspection.

```javascript
function planStages17(node, stages = new Set()) {
  if (!node || typeof node !== "object") return stages;
  if (typeof node.stage === "string") stages.add(node.stage);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) {
      value.forEach(item => planStages17(item, stages));
    } else if (value && typeof value === "object") {
      planStages17(value, stages);
    }
  }
  return stages;
}
function evidence17(label, explain) {
  const stats = explain.executionStats;
  check17(stats && stats.executionSuccess, label + " execution failed");
  const stages = [...planStages17(explain.queryPlanner.winningPlan)];
  const summary = {
    label,
    nReturned: stats.nReturned,
    totalKeysExamined: stats.totalKeysExamined,
    totalDocsExamined: stats.totalDocsExamined,
    executionTimeMillis: stats.executionTimeMillis,
    winningStages: stages
  };
  printjson(summary);
  return summary;
}
const baseline17 = evidence17("collection-scan",
  query17({ $natural: 1 }).explain("executionStats"));
check17(baseline17.nReturned === 20, "Baseline returned wrong count");
check17(baseline17.totalDocsExamined === 20000,
        "Baseline did not scan the complete fixture");
check17(baseline17.winningStages.includes("COLLSCAN"),
        "Inspect unexpected baseline plan");
```

Inspect the full explain output if an assertion fails. The helper traverses only the winning plan, avoiding false positives from rejected plans. It is a teaching aid, not a universal explain parser for sharded or future server layouts.

## 6. Measure the single-field index

```javascript
tasks17.createIndex({ tenantId: 1 }, { name: "tenant_asc" });
verifyRows17(query17("tenant_asc").toArray());
const single17 = evidence17("single-field",
  query17("tenant_asc").explain("executionStats"));
check17(single17.nReturned === 20, "Single-field returned wrong count");
check17(single17.totalDocsExamined === 2000,
        "Expected examination of this tenant's documents");
check17(single17.totalKeysExamined >= 2000,
        "Expected scanning this tenant's index range");
check17(single17.winningStages.includes("SORT"),
        "Expected a blocking sort with tenant-only index");
```

Expected change: document examination falls from 20,000 to 2,000. The index selects the tenant, but the query still checks status and sorts the matching candidates. A limit of 20 does not mean only 20 documents were examined.

Do not assert exact milliseconds or a fixed speedup. Small runs may show zero milliseconds, warm cache effects and noise. Examined-work counters and sort behavior give clearer structural evidence here.

The explicit hint isolates one access path. It does not demonstrate what the optimizer chooses without a hint, nor does it establish that an application should permanently hint this index.

## 7. Build the compound index

```javascript
const compoundName17 = "tenant_status_created_id";
const compoundKey17 = {
  tenantId: 1, status: 1, createdAt: -1, _id: -1
};
tasks17.createIndex(compoundKey17, { name: compoundName17 });
printjson(tasks17.getIndexes());
verifyRows17(query17(compoundName17).toArray());
const compound17 = evidence17("compound",
  query17(compoundName17).explain("executionStats"));
check17(compound17.nReturned === 20, "Compound returned wrong count");
check17(compound17.totalDocsExamined === 20,
        "Expected fetching only the returned documents");
check17(compound17.totalKeysExamined <= 25,
        "Unexpectedly broad index scan; inspect bounds");
check17(!compound17.winningStages.includes("SORT"),
        "Compound index did not supply the requested order");
check17(compound17.totalDocsExamined < single17.totalDocsExamined,
        "Compound access did not reduce document examination");
```

On this unsharded scalar fixture, expect about 20 examined keys and 20 fetched documents, with no blocking SORT. The tenant and status equality bounds identify a contiguous group, and the remaining keys provide newest-first order. The early limit stops traversal after the requested page.

If the counters differ, preserve the full plan, index metadata, version and fixture counts. Do not adjust the assertion merely to make a run pass. Check hint selection, key direction, collation, field types and unexpected concurrent writes.

Now inspect the optimizer-selected plan without forcing an index:

```javascript
verifyRows17(query17().toArray());
const chosenExplain17 = query17().explain("executionStats");
evidence17("optimizer-selected", chosenExplain17);
printjson(chosenExplain17.queryPlanner.winningPlan);
```

The compound index is a strong candidate. Record what the server actually chooses. Explain ignores existing plan-cache entries and does not populate the plan cache; an explain result is not proof of the exact cached plan used by a production request.

## 8. Prefixes and a changed query shape

Force the compound index for a tenant-only query, which uses its leading prefix:

```javascript
const prefixExplain17 = tasks17.find({ tenantId: "tenant-03" })
  .hint(compoundName17).explain("executionStats");
const prefix17 = evidence17("tenant-prefix", prefixExplain17);
check17(prefix17.nReturned === 2000, "Prefix query returned wrong count");
```

Compare a status-only query using a forced compound path with a forced collection scan:

```javascript
const statusScan17 = evidence17("status-only-forced-compound",
  tasks17.find({ status: "OPEN" }).hint(compoundName17)
    .explain("executionStats"));
const statusNatural17 = evidence17("status-only-natural",
  tasks17.find({ status: "OPEN" }).hint({ $natural: 1 })
    .explain("executionStats"));
check17(statusScan17.nReturned === 10000 &&
        statusNatural17.nReturned === 10000,
        "Status-only results differ");
```

Status alone omits the leading tenant prefix. A forced index scan can still traverse keys and filter them; seeing an index in this forced plan does not establish an efficient status lookup. Inspect bounds and examined work instead of asserting that every non-prefix query must produce COLLSCAN.

If global OPEN-task access is a real workload, design and measure an index for that separate contract. Do not add one solely to make this exercise's forced plan look better.

## 9. Failure exercise: the wrong tie-break direction

Create an index that almost matches the query but has ascending _id after descending createdAt:

```javascript
const wrongName17 = "tenant_status_created_id_wrong";
tasks17.createIndex(
  { tenantId: 1, status: 1, createdAt: -1, _id: 1 },
  { name: wrongName17 }
);
verifyRows17(query17(wrongName17).toArray());
const wrong17 = evidence17("wrong-sort-direction",
  query17(wrongName17).explain("executionStats"));
check17(wrong17.winningStages.includes("SORT"),
        "Expected blocking sort for mixed direction mismatch");
check17(wrong17.totalDocsExamined > compound17.totalDocsExamined,
        "Expected more fetched candidates with mismatched ordering");
```

The result remains correct because MongoDB performs the required sort. The failure is extra work, not an incorrect page. Diagnose by comparing the requested sort, compound key directions and winning SORT stage.

Correction: use the already-created matching compound index, verify result identity and confirm the sort stage disappears.

```javascript
verifyRows17(query17(compoundName17).toArray());
const corrected17 = evidence17("corrected-sort-direction",
  query17(compoundName17).explain("executionStats"));
check17(!corrected17.winningStages.includes("SORT"),
        "Correction did not remove blocking sort");
tasks17.dropIndex(wrongName17);
```

No production index is changed. Capture before/after plans before removing the chapter's experimental index.

## 10. Reversible index-removal rehearsal

A prefix index may be redundant when an ordinary compound index already serves that access pattern. Do not infer interchangeability when uniqueness, sparse/partial predicates, collation or other options differ. Check other workloads before removing anything.

In this isolated database, hide the tenant-only index, verify the normal query, and unhide it:

```javascript
tasks17.hideIndex("tenant_asc");
try {
  const hidden17 = tasks17.getIndexes().find(i => i.name === "tenant_asc");
  check17(hidden17 && hidden17.hidden === true, "Index not hidden");
  verifyRows17(query17().toArray());
  evidence17("tenant-index-hidden",
    query17().explain("executionStats"));
} finally {
  tasks17.unhideIndex("tenant_asc");
}
check17(tasks17.getIndexes().find(i => i.name === "tenant_asc").hidden !== true,
        "Index not restored");
```

Hidden indexes are maintained on writes and still consume storage. Hiding tests planner availability; it does not measure the write/storage savings of dropping an index. A hidden index cannot be explicitly hinted. Do not reuse the tenant_asc hint while it is hidden.

If your authorized training role cannot hide indexes, record that exercise as unvalidated rather than escalating privileges without a reason. Continue only after restoring any index you did hide.

## 11. Storage and write-cost evidence

```javascript
const collectionStats17 = lab17.runCommand({
  collStats: "tasks", scale: 1
});
check17(collectionStats17.ok === 1, "collStats failed");
printjson({
  count: collectionStats17.count,
  totalIndexSize: collectionStats17.totalIndexSize,
  indexSizes: collectionStats17.indexSizes
});
```

Record sizes for _id_, tenant_asc and tenant_status_created_id. Actual bytes depend on engine, compression, data and server version; do not prescribe a universal size ratio.

Every retained index adds maintenance work. To quantify write cost, use a separate controlled benchmark with the same fixture, batch sizes, concurrency, durability settings and index sets. Do not compare an idle single insert with an index build and call the difference a production write regression.

A production index build can compete for CPU, I/O, memory and disk. Replica-set build coordination and maintenance procedures need their own deployment-specific plan; this small lab is not that plan.

## 12. Troubleshooting

| Symptom | Evidence | Likely cause | Action |
|---|---|---|---|
| Hint fails | getIndexes, exact name, hidden flag | Typo, absent or hidden index | Fix name or restore intended availability |
| Index used but many keys examined | Bounds, filter, key pattern | Weak selectivity or missing prefix | Design for measured query shapes |
| Blocking SORT remains | Sort and index direction, winning plan | Key order/direction mismatch | Align the complete sort contract |
| Result order differs | Returned IDs, fixture count | Missing tie-break or wrong sort | Restore deterministic ordering |
| Docs examined remain above page size | Projection, FETCH, residual filter | Candidate documents must be checked | Inspect predicate support and coverage |
| Index build unauthorized | Namespace and roles | Missing createIndex privilege | Use authorized database-scoped role |
| Build affects latency | CPU, storage latency, free space, replica health | Resource competition | Use reviewed build window and recovery plan |
| Unhinted plan differs from forced plan | Full explain, data distribution | Optimizer chose another candidate | Compare work and actual workload evidence |

Do not use totalKeysExamined alone as the objective. A broad index scan might examine fewer documents yet take longer under a specific storage/cache workload. Correctness, latency, throughput and write cost all matter.

## 13. Production application

For a tenant work queue, document the supported filter and sort shapes, expected tenant sizes, hot-tenant skew, status selectivity, page limits and retention. Keep authorization scope independent from index design: a tenant index does not enforce access control.

Review existing index options and all dependent query shapes before removing a prefix index. Search application code for named hints and inspect observed access patterns over a representative interval. An index unused during a short observation window may serve infrequent maintenance or recovery work.

Capture the full index definition before a change. Hiding provides a fast reversal through unhide; dropping requires rebuilding, which takes time and resources. Do not confuse these rollback paths.

Array values, custom collation, partial predicates and sharding can change conclusions. This chapter intentionally excludes them from the fixture. Revalidate when any of those conditions enter the real contract.

## 14. Cleanup and rollback

Restore a hidden tenant index first if the exercise was interrupted. Use this chapter's database only:

```javascript
const tenantIndex17 = tasks17.getIndexes().find(i => i.name === "tenant_asc");
if (tenantIndex17 && tenantIndex17.hidden === true) {
  tasks17.unhideIndex("tenant_asc");
}
verifyRows17(query17(compoundName17).toArray());
check17(tasks17.countDocuments({}) === 20000, "Fixture changed");
if (lab17.getName() !== "mongodb_enterprise_tutorial_ch17") {
  throw new Error("Refusing cleanup outside the Chapter 17 training database");
}
const dropResult17 = lab17.dropDatabase();
check17(dropResult17.ok === 1, "Database cleanup command failed");
check17(lab17.getCollectionNames().length === 0, "Cleanup incomplete");
```

Dropping the named lab database removes its data and experimental indexes. Keep evidence before cleanup. No container, cluster settings or other databases are changed by this chapter.

## 15. Acceptance and evidence

- [ ] Recorded exact MongoDB/mongosh versions and an unsharded training context.
- [ ] Loaded 20,000 tasks with validated tenant/status counts.
- [ ] Verified the exact same 20 result identifiers for every canonical query.
- [ ] Collection scan examined the full fixture.
- [ ] Single-field index reduced document examination but retained a sort.
- [ ] Matching compound index fetched the page without a blocking sort.
- [ ] Recorded unhinted optimizer choice separately from forced comparisons.
- [ ] Diagnosed mixed sort-direction extra work and verified correction.
- [ ] Restored the hidden index and recorded storage evidence.
- [ ] Captured evidence and dropped only the named chapter database.

**Evidence:** version inventory, index definitions, result IDs, full explain outputs and summary counters, failure/correction plans, hide/unhide metadata, index sizes and cleanup outcome. Runtime validation stays pending until the lab runs on the specified deployment; static syntax checks do not prove access-path behavior.

## 16. Review questions

1. Why can a query returning 20 documents examine 20,000 documents?
2. What work does the tenant-only index leave for the canonical query?
3. Why is _id part of the compound index despite its separate default index?
4. Which reverse sort can the compound index support after tenant/status equality?
5. Why is a forced index plan insufficient evidence of planner preference?
6. When is a prefix index unsafe to remove based only on its key pattern?
7. Why does hiding an index not measure its write-maintenance cost?
8. What changes would require revalidating this lab's conclusions?

## 17. Official references

- [MongoDB 8.0: single-field indexes](https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-single/)
- [MongoDB 8.0: compound indexes and prefixes](https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-compound/)
- [MongoDB 8.0: indexes and sort order](https://www.mongodb.com/docs/v8.0/tutorial/sort-results-with-indexes/)
- [MongoDB 8.0: cursor.explain](https://www.mongodb.com/docs/v8.0/reference/method/cursor.explain/)
- [MongoDB 8.0: hideIndex](https://www.mongodb.com/docs/v8.0/reference/method/db.collection.hideIndex/)
- [MongoDB 8.0: createIndex](https://www.mongodb.com/docs/v8.0/reference/method/db.collection.createIndex/)

---

Previous: [Chapter 16 — Transactions Sessions and Retry Semantics](16-transactions-sessions-and-retry-semantics.md)  
Next: [Chapter 18 — ESR Index Design and Covered Queries](18-esr-index-design-and-covered-queries.md).
