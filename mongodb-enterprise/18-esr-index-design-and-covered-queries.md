# 18 — ESR Index Design and Covered Queries

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Compare Equality–Sort–Range and Equality–Range–Sort indexes for broad and selective ranges, then prove and deliberately break query coverage.  
**Audience:** Developers, Data Engineers, DBREs and SREs  
**Time:** 75–105 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Community-compatible or Enterprise training server; standalone or replica-set primary, with an unsharded ordinary collection.

## 1. Design for the complete query

Chapter 17 showed why an index used by a query can still leave filtering and sorting work. This chapter adds a range predicate and a narrow result projection.

The synthetic use case is a tenant's newest OPEN work items whose score meets a threshold. A broad threshold admits many items. A high threshold admits only a few. The filter, ordering, limit and projection are the same shape; parameter selectivity changes the work.

ESR is a design guideline:

- **Equality:** fixed tenant and status identify a group.
- **Sort:** sequence descending supplies newest-first results.
- **Range:** score greater than or equal to a threshold narrows eligibility.

Putting sort before range can preserve index order and allow early stopping at the page limit. Putting a highly selective range before sort can reduce candidates, while requiring a blocking sort of those candidates. Neither arrangement is universally fastest.

A covered query answers its predicates and projection using index keys without fetching collection documents. Coverage and efficient scanning are separate properties. An index can cover a query while examining many keys or leaving a sort.

## 2. Two candidate indexes

| Candidate | Key order | Intended benefit | Work to inspect |
|---|---|---|---|
| ESR | tenantId, status, seq descending, score | Ordered page traversal | Keys examined before enough scores qualify |
| ERS | tenantId, status, score, seq descending | Narrow score bounds | Blocking sort across qualifying score groups |
| ESR plus payload projection | Same ESR index, extra returned field | Correct richer response | Document fetches because payload is absent |
| ESR plus default _id projection | Same ESR index, implicit _id | Correct result including identity | Document fetches because _id is absent |

The equality fields lead both candidates. Their relative order is also a workload choice: a tenant-leading index has a tenant prefix; a status-leading index has a different prefix. This lab keeps tenant first.

The range is across score values, so ERS cannot directly supply a global seq-descending order over that range. A score equality would be a different case.

The fixture uses a unique sequence within each tenant and fixes tenant/status in the query. That makes seq alone deterministic here. Real APIs with duplicate sort values need an explicit tie-breaker, as Chapter 15 demonstrated.

## 3. Prerequisites and permissions

Complete Chapters 15 and 17. Connect using the approved training connection from Chapter 06. Use the replica-set primary if applicable.

The user needs database-scoped collection creation, read/write, createIndex, listIndexes, dropIndex, collection statistics and cleanup access for this lab database. No profiling, failover, topology change or cluster administration is required.

Do not reuse a production collection or alter application indexes for this experiment. Use ordinary scalar keys and default simple collation. Arrays, null predicates, partial indexes, custom collation and sharding require separate coverage analysis.

In mongosh:

```javascript
const labName18 = "mongodb_enterprise_tutorial_ch18";
const lab18 = db.getSiblingDB(labName18);
printjson({ serverVersion: db.version(), database: labName18 });
if (lab18.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
lab18.createCollection("workItems");
const items18 = lab18.workItems;
function check18(condition, message) {
  if (!condition) throw new Error(message);
}
```

Record mongosh --version separately. An older deployment must use matching version documentation and record deviations; a successful syntax check on a local Node.js installation is not a server compatibility test.

## 4. Create a bounded fixture

Create ten tenants, each with 2,000 OPEN items. Each tenant has scores 0–999 repeated twice. Sequence is 0–1999, with larger values treated as newer. This deliberate distribution makes expected cardinality straightforward.

```javascript
let batch18 = [];
for (let tenant = 0; tenant < 10; tenant++) {
  for (let seq = 0; seq < 2000; seq++) {
    batch18.push({
      _id: tenant * 2000 + seq,
      tenantId: "tenant-" + String(tenant).padStart(2, "0"),
      status: "OPEN",
      seq: seq,
      score: seq % 1000,
      payload: "Synthetic payload " + tenant + "/" + seq
    });
    if (batch18.length === 1000) {
      items18.insertMany(batch18);
      batch18 = [];
    }
  }
}
check18(items18.countDocuments({}) === 20000, "Wrong total count");
check18(items18.countDocuments({ tenantId: "tenant-03" }) === 2000,
        "Wrong tenant count");
check18(items18.countDocuments({
  tenantId: "tenant-03", status: "OPEN", score: { $gte: 100 }
}) === 1800, "Wrong broad-range count");
check18(items18.countDocuments({
  tenantId: "tenant-03", status: "OPEN", score: { $gte: 995 }
}) === 10, "Wrong selective-range count");
check18(items18.getIndexes().length === 1, "Unexpected initial indexes");
```

All items are OPEN so status is a fixed equality key, not a selective key in this dataset. Tenant narrows the collection to 2,000 records. The score predicate then admits 1,800 or 10 records. Do not generalize these proportions to production.

The fixture correlates score and sequence. That correlation affects ordered scans and is intentional evidence about this particular dataset. Benchmark realistic skew and correlation before making a production choice.

## 5. Define a projection and correctness oracle

The lean response returns tenantId, status, seq and score, explicitly excluding _id. All four fields will be present in both experimental indexes.

```javascript
const projection18 = {
  _id: 0, tenantId: 1, status: 1, seq: 1, score: 1
};
const sort18 = { seq: -1 };
function query18(threshold, hint, projection = projection18) {
  const cursor = items18.find({
    tenantId: "tenant-03",
    status: "OPEN",
    score: { $gte: threshold }
  }, projection).sort(sort18).limit(20);
  return hint === undefined ? cursor : cursor.hint(hint);
}
function expectedSeq18(threshold) {
  const values = [];
  for (let seq = 1999; seq >= 0; seq--) {
    if (seq % 1000 >= threshold) values.push(seq);
    if (values.length === 20) break;
  }
  return values;
}
function verify18(threshold, rows) {
  check18(JSON.stringify(rows.map(r => Number(r.seq))) ===
          JSON.stringify(expectedSeq18(threshold)),
          "Wrong page sequence for threshold " + threshold);
  check18(rows.every(r => r.tenantId === "tenant-03" &&
    r.status === "OPEN" && Number(r.score) >= threshold),
    "Wrong tenant/status/range scope");
}
verify18(100, query18(100, { $natural: 1 }).toArray());
verify18(995, query18(995, { $natural: 1 }).toArray());
```

Expected broad page is seq 1999 through 1980. Expected selective page is 1999 through 1995 followed by 999 through 995. The selective query returns ten rows, rather than filling the requested maximum of twenty.

This independent fixture calculation checks result correctness for every index path. It does not use the output of one server plan as the expected answer for another.

## 6. Capture execution evidence

```javascript
function stages18(node, result = new Set()) {
  if (!node || typeof node !== "object") return result;
  if (typeof node.stage === "string") result.add(node.stage);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) {
      value.forEach(child => stages18(child, result));
    } else if (value && typeof value === "object") {
      stages18(value, result);
    }
  }
  return result;
}
function measure18(label, cursor) {
  const explain = cursor.explain("executionStats");
  const stats = explain.executionStats;
  check18(stats && stats.executionSuccess, label + " did not succeed");
  const result = {
    label,
    returned: stats.nReturned,
    keys: stats.totalKeysExamined,
    documents: stats.totalDocsExamined,
    millis: stats.executionTimeMillis,
    stages: [...stages18(explain.queryPlanner.winningPlan)]
  };
  printjson(result);
  return { result, explain };
}
const baseline18 = measure18("broad-collection-scan",
  query18(100, { $natural: 1 }));
check18(baseline18.result.documents === 20000,
        "Expected complete collection scan");
check18(baseline18.result.returned === 20, "Wrong baseline page size");
```

Keep the full explain output in addition to the summary. The helper traverses only the winning plan. Rejected plans must not cause a false claim that the winning plan fetched or sorted.

Explain with executionStats executes query work. Its timing is a small isolated observation, not a production latency benchmark. Explain also does not represent existing plan-cache behavior: it ignores existing entries and does not populate them.

## 7. Create ESR and ERS candidates

```javascript
const esrName18 = "tenant_status_seq_score";
const ersName18 = "tenant_status_score_seq";
items18.createIndex(
  { tenantId: 1, status: 1, seq: -1, score: 1 },
  { name: esrName18 }
);
items18.createIndex(
  { tenantId: 1, status: 1, score: 1, seq: -1 },
  { name: ersName18 }
);
printjson(items18.getIndexes());
```

The names identify the ordering. Both contain the same fields but are not interchangeable. Creating a second index with the same fields in another order incurs another physical index and maintenance cost.

## 8. Compare a broad range

```javascript
verify18(100, query18(100, esrName18).toArray());
verify18(100, query18(100, ersName18).toArray());
const broadEsr18 = measure18("broad-ESR", query18(100, esrName18));
const broadErs18 = measure18("broad-ERS", query18(100, ersName18));
check18(broadEsr18.result.returned === 20 &&
        broadErs18.result.returned === 20, "Wrong broad result count");
check18(!broadEsr18.result.stages.includes("SORT"),
        "ESR did not supply sequence order");
check18(broadErs18.result.stages.includes("SORT"),
        "Expected ERS blocking sort across score range");
check18(broadEsr18.result.documents === 0 &&
        broadErs18.result.documents === 0,
        "Lean projection should be covered for both candidates");
```

Expected structural result: ESR streams in requested order and stops after a page; ERS sorts eligible score-range candidates. Both should fetch zero collection documents for the lean projection.

Record examined keys for both. The broad fixture's newest twenty records all qualify, favoring early stopping in ESR. ERS must consider eligible records across many score groups before it knows the newest page. Do not impose a universal key-count ratio or millisecond speedup.

A top-k sort may keep only the best twenty candidates in memory, yet still consume all eligible input. A limit does not erase the upstream candidate work.

## 9. Compare a highly selective range

```javascript
verify18(995, query18(995, esrName18).toArray());
verify18(995, query18(995, ersName18).toArray());
const narrowEsr18 = measure18("selective-ESR", query18(995, esrName18));
const narrowErs18 = measure18("selective-ERS", query18(995, ersName18));
check18(narrowEsr18.result.returned === 10 &&
        narrowErs18.result.returned === 10, "Wrong selective result count");
check18(!narrowEsr18.result.stages.includes("SORT"),
        "Unexpected ESR sort");
check18(narrowErs18.result.stages.includes("SORT"),
        "Expected ERS sort for selective range");
check18(narrowEsr18.result.documents === 0 &&
        narrowErs18.result.documents === 0, "Coverage was lost");
printjson({
  broad: { ESR: broadEsr18.result, ERS: broadErs18.result },
  selective: { ESR: narrowEsr18.result, ERS: narrowErs18.result }
});
```

ERS can tightly bound the score range and sort only ten matching entries. ESR keeps sequence order, but must establish that no other qualifying entries remain because the query returns fewer than the page limit. The server may optimize bounds and traversal; record its actual examined-key work instead of assuming one key examined for every tenant record.

The important decision is whether saving range-scan work outweighs sorting work for the measured distribution, page size and request mix. This lab demonstrates the choice and collects evidence; it does not guarantee ERS wins every selective-range timing test.

Use this worksheet:

| Query | Index | Returned | Keys examined | Documents examined | Blocking SORT | Measured milliseconds |
|---|---|---:|---:|---:|---|---:|
| Broad >=100 | ESR | 20 | Record | 0 expected | No expected | Record |
| Broad >=100 | ERS | 20 | Record | 0 expected | Yes expected | Record |
| Selective >=995 | ESR | 10 | Record | 0 expected | No expected | Record |
| Selective >=995 | ERS | 10 | Record | 0 expected | Yes expected | Record |

If assertions fail, capture full evidence and diagnose the environment rather than editing the expected property until it passes.

## 10. Prove coverage, not merely index usage

A nonempty covered result should have zero documents examined and no collection FETCH in the winning plan. Inspect both the counters and plan.

```javascript
check18(broadEsr18.result.returned > 0, "Coverage example returned nothing");
check18(broadEsr18.result.documents === 0, "Query fetched documents");
check18(!broadEsr18.result.stages.includes("FETCH"),
        "Winning plan contains a collection fetch");
const coveredRows18 = query18(100, esrName18).toArray();
check18(coveredRows18.every(r => !Object.hasOwn(r, "_id")),
        "_id was not excluded");
verify18(100, coveredRows18);
printjson(broadEsr18.explain.queryPlanner.winningPlan);
```

An empty result with zero document reads is not sufficient evidence of coverage. An IXSCAN alone is also insufficient: an index scan may feed FETCH.

Covering this lean page avoids document access for the query. It does not mean the index is free, the scan is selective, or the whole application has no storage reads.

## 11. Failure exercise: implicit _id breaks coverage

Remove the explicit _id exclusion. MongoDB includes _id by default in an inclusion projection, but this experimental index has no _id key.

```javascript
const accidentalProjection18 = {
  tenantId: 1, status: 1, seq: 1, score: 1
};
const accidentalRows18 = query18(
  100, esrName18, accidentalProjection18
).toArray();
verify18(100, accidentalRows18);
check18(accidentalRows18.every(r => Object.hasOwn(r, "_id")),
        "Expected default _id inclusion");
const accidental18 = measure18("implicit-id-fetch",
  query18(100, esrName18, accidentalProjection18));
check18(accidental18.result.documents > 0,
        "Expected fetch because _id is absent from candidate index");
```

The query remains correct and indexed. Coverage fails because the output contract now requires another field. The separate default _id index does not automatically merge _id values into this covered response.

Correction: if the API does not need _id, restore its exclusion. If it does need _id, do not drop a required response field for performance; evaluate an index that includes it and measure the added cost.

```javascript
const repaired18 = measure18("restored-id-exclusion",
  query18(100, esrName18, projection18));
check18(repaired18.result.documents === 0, "Coverage not restored");
verify18(100, query18(100, esrName18).toArray());
```

## 12. A required payload also breaks coverage

```javascript
const payloadProjection18 = {
  ...projection18, payload: 1
};
const payloadRows18 = query18(100, esrName18, payloadProjection18).toArray();
verify18(100, payloadRows18);
check18(payloadRows18.every(r => typeof r.payload === "string"),
        "Payload missing");
const payload18 = measure18("required-payload-fetch",
  query18(100, esrName18, payloadProjection18));
check18(payload18.result.documents > 0,
        "Expected document access for payload");
```

Fetching twenty bounded documents may be an acceptable design. Adding large payloads to an index can increase index size, cache pressure and write amplification. Compare the whole workload before widening an index.

A narrow list endpoint and a separate detail endpoint can have different projections. Their access-control and consistency contracts still need explicit design; coverage is an optimization, not a reason to change authorization.

## 13. Inspect the unhinted choice

```javascript
for (const threshold of [100, 995]) {
  verify18(threshold, query18(threshold).toArray());
  const chosen = measure18("unhinted-" + threshold, query18(threshold));
  printjson(chosen.explain.queryPlanner.winningPlan);
}
const stats18 = lab18.runCommand({ collStats: "workItems", scale: 1 });
check18(stats18.ok === 1, "Collection statistics failed");
printjson({ totalIndexSize: stats18.totalIndexSize, indexSizes: stats18.indexSizes });
```

Forced candidates isolate access paths for comparison. Unhinted explains show the optimizer's choices for this run. Do not deploy a permanent hint based on one fixture or assume that every production parameter gets a different cached plan.

Record both index sizes. Keep both indexes only if their demonstrated benefits justify their combined storage and maintenance costs. This lab keeps them until cleanup to preserve reproducible comparisons.

## 14. Troubleshooting

| Symptom | Evidence | Likely cause | Action |
|---|---|---|---|
| Docs examined above zero | Projection, winning FETCH, index fields | Implicit _id or an uncovered field | Restore intended projection or evaluate wider index |
| ESR still sorts | Equality predicates, sort, key pattern | Missing leading equality or changed ordering | Match complete contract and remeasure |
| ERS sort appears despite index | Score bounds and seq order | Range spans multiple score groups | Expected tradeoff; compare candidate volume |
| Covered query scans many keys | Bounds, returned rows, key count | Poor selectivity or range behind sort | Compare ERS and real distribution |
| Zero docs but no output | nReturned and fixture counts | Empty filter result | Use a known nonempty query to prove coverage |
| Hint rejected | Index names, hidden metadata | Missing/hidden index or typo | Correct candidate availability |
| Expected count differs | Fixture cardinality and concurrent writes | Partial load or altered data | Reset only reviewed chapter resources |
| Sharded plan differs | Namespace and shard-key/index metadata | Different routing/coverage requirements | Use stated unsharded lab or design separate test |

Keep sanitized full explain documents. Counters alone cannot explain an unexpected access path.

## 15. Production design boundaries

Choose from observed workloads, including broad/selective thresholds, limits, hot tenants, data correlation and write volume. Use representative concurrency and warm/cold working-set conditions for latency testing. A minimum elapsed time from a handful of shell runs is not an SLO.

Keep scalar BSON types consistent. Null equality predicates, multikey indexes and collation have additional coverage constraints. A sharded query through mongos also has shard-key requirements for coverage. Do not copy this unsharded conclusion to those cases.

Range-like predicates are not limited to numeric comparisons; regex and inequality operators need their own bounds analysis. Large $in lists can change planning/sort behavior across versions. Avoid encoding a universal list-length threshold into an application without version-specific verification.

Index-only reads still depend on index pages and cache residency. Track index size, memory pressure, storage latency and write cost when evaluating coverage. A wider index can save document fetches while harming other workload dimensions.

For a production change, capture original index definitions, identify named hints and query settings, build candidates under a reviewed resource plan, and measure representative traffic. Removing an index requires a recovery path that may involve a costly rebuild. Hiding preserves maintenance cost and offers a different reversal path, as Chapter 17 showed.

## 16. Cleanup

Capture evidence first. These commands affect only this chapter's database:

```javascript
check18(items18.countDocuments({}) === 20000, "Fixture unexpectedly changed");
verify18(100, query18(100, esrName18).toArray());
verify18(995, query18(995, ersName18).toArray());
if (lab18.getName() !== "mongodb_enterprise_tutorial_ch18") {
  throw new Error("Refusing cleanup outside the Chapter 18 training database");
}
const dropResult18 = lab18.dropDatabase();
check18(dropResult18.ok === 1, "Database cleanup command failed");
check18(lab18.getCollectionNames().length === 0, "Cleanup incomplete");
```

No server settings or external application indexes changed, so no configuration rollback is needed. Both experimental indexes disappear with the database.

## 17. Acceptance and evidence

- [ ] Recorded exact server/shell versions and unsharded deployment context.
- [ ] Verified 20,000 total items and both range cardinalities.
- [ ] Confirmed exact sequence results for all candidate paths.
- [ ] Compared broad and selective ESR/ERS work without assuming universal timing winners.
- [ ] ESR avoided blocking SORT; ERS sorted across score ranges.
- [ ] Nonempty lean queries examined zero collection documents.
- [ ] Implicit _id and required payload each introduced document fetches.
- [ ] Restoring _id exclusion restored coverage.
- [ ] Recorded unhinted plans and index sizes.
- [ ] Saved evidence and completed scoped cleanup.

**Evidence:** versions, fixture counts, exact sequence lists, index definitions, complete explain documents, comparison worksheet, coverage-failure/correction output, index sizes and cleanup. Runtime validation remains pending until these commands execute successfully on the stated MongoDB deployment.

## 18. Review questions

1. Why might ERS be preferable when a range admits very few records?
2. Why can ESR stop early for one threshold but not another?
3. Can a covered query still have a blocking sort or broad key scan?
4. Why does implicit _id inclusion prevent coverage in this lab?
5. Why does the separate _id index not solve that projection requirement?
6. When is fetching a small bounded page preferable to widening an index?
7. Which fixture correlations affect these comparisons?
8. Why are forced explains and production cached-plan behavior different evidence?

## 19. Official references

- [MongoDB 8.0: ESR guideline and selective range tradeoffs](https://www.mongodb.com/docs/v8.0/tutorial/equality-sort-range-guideline/)
- [MongoDB 8.0: query optimization and covered queries](https://www.mongodb.com/docs/v8.0/core/query-optimization/)
- [MongoDB 8.0: explain results and coverage evidence](https://www.mongodb.com/docs/v8.0/reference/explain-results/)
- [MongoDB 8.0: indexes and sorting](https://www.mongodb.com/docs/v8.0/tutorial/sort-results-with-indexes/)
- [MongoDB 8.0: cursor.explain](https://www.mongodb.com/docs/v8.0/reference/method/cursor.explain/)

---

Previous: [Chapter 17 — Single Field and Compound Indexes](17-single-field-and-compound-indexes.md)  
Next: [Chapter 19 — Multikey Partial Sparse and Unique Indexes](19-multikey-partial-sparse-and-unique-indexes.md).
