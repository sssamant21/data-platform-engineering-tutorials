# 21 — Explain Plans and Query Optimization

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Diagnose examined work and blocking operations, compare candidate plans, and verify that a faster-looking query preserves the original result contract.  
**Audience:** Developers, Data Engineers, DBREs and SREs  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Community-compatible or Enterprise training server; standalone or replica-set primary. Unsharded ordinary collection.

## 1. Start with a question, not a stage name

An explain plan describes how MongoDB can execute a query. It is useful for answering specific questions:

- Did the query scan the collection or a bounded index range?
- Did it fetch documents or answer from index keys?
- Did an index provide order, or did a blocking sort remain?
- How much upstream work produced the requested page?
- Did a proposed rewrite change the result?

An IXSCAN is not a performance verdict. A COLLSCAN is not automatically a production incident. A small collection, broad result or unusual workload can make different access paths reasonable. Explain connects the query contract to work performed; application latency still depends on concurrency, cache, I/O, network and result consumption.

Chapters 17–20 established index semantics. This chapter combines them into a repeatable investigation rather than introducing another index type.

## 2. Choose the right verbosity

| Mode | What to inspect | Limit |
|---|---|---|
| queryPlanner | Winning plan, index bounds, rejected candidates | Does not provide full execution counters |
| executionStats | Completed winning-plan work and counters | Executes query work; timing is not an application benchmark |
| allPlansExecution | Winning completion plus partial candidate trial statistics | Rejected candidates did not all run to completion |

Compare complete runs using explicit candidate hints when you need completed per-candidate counters. Do not compare a rejected plan's partial trial count with a winning plan's full count and conclude that the rejected plan is cheaper.

Explain ignores existing plan-cache entries and does not populate the cache. It is not proof of which cached plan a live request used. In MongoDB 8.0, planCacheShapeHash is available alongside the older queryHash field; planCacheKey also depends on available indexes. Hashes are correlation aids, not unique business identifiers or a substitute for the full shape.

## 3. Read the plan and counters together

| Evidence | Interpretation | Follow-up |
|---|---|---|
| COLLSCAN | Collection traversal | Compare scope and collection size |
| IXSCAN and indexBounds | Index traversal and key intervals | Check whether bounds match intended selectivity |
| FETCH | Collection documents are read | Determine residual filter or required output fields |
| SORT | Explicit ordering work | Check compound key order, direction and equality prefix |
| nReturned | Rows returned by completed operation | Compare with correctness oracle |
| totalKeysExamined | Index entries examined | Compare with result count and bounds |
| totalDocsExamined | Document examinations, not necessarily unique documents | Inspect fetch/filter work |
| executionTimeMillis | Server explain timing | Use cautiously; do not treat as client P95 |

Explain structures vary by execution engine and operation. A winningPlan can contain queryPlan and slotBasedPlan. Aggregation explain may place its cursor plan under stages rather than at the top level. Sharded output has additional per-shard and merge context. Do not build a production parser that assumes every plan is winningPlan.inputStage.inputStage.

Sort spill and memory evidence depend on stage, version and execution shape. Inspect available execution-stage fields such as usedDisk and spills when present; absence of a field is not a universal proof that no memory pressure occurred.

## 4. Prerequisites and lab scope

Complete Chapters 17–18. Connect using the approved training URI from Chapter 06. Use the primary for index changes if working on a replica set.

The user needs collection creation, read/write, index creation/listing/removal and database cleanup privileges on this chapter database. No profiler activation, plan-cache clearing, query settings or cluster changes are required.

In mongosh:

```javascript
const labName21 = "mongodb_enterprise_tutorial_ch21";
const lab21 = db.getSiblingDB(labName21);
printjson({ serverVersion: db.version(), database: labName21 });
if (lab21.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
lab21.createCollection("requests");
const requests21 = lab21.requests;
function check21(condition, message) {
  if (!condition) throw new Error(message);
}
```

Record mongosh --version separately. The JavaScript helpers below are scoped to this unsharded lab, not a universal parser for every explain response.

## 5. Build a fixture with independent query dimensions

Ten tenants have 3,000 requests each. Within each tenant, every third request is OPEN and the rest CLOSED. Sequence increases with recency. Requests at sequences 2700 and above form the canonical recent interval.

```javascript
let batch21 = [];
for (let tenant = 0; tenant < 10; tenant++) {
  for (let seq = 0; seq < 3000; seq++) {
    batch21.push({
      _id: tenant * 3000 + seq,
      tenantId: "tenant-" + String(tenant).padStart(2, "0"),
      status: seq % 3 === 0 ? "OPEN" : "CLOSED",
      seq,
      durationMs: (seq * 17) % 1000,
      payload: "Synthetic request " + tenant + "/" + seq
    });
    if (batch21.length === 1000) {
      requests21.insertMany(batch21);
      batch21 = [];
    }
  }
}
check21(requests21.countDocuments({}) === 30000, "Wrong total fixture");
check21(requests21.countDocuments({
  tenantId: "tenant-03", status: "OPEN", seq: { $gte: 2700 }
}) === 100, "Wrong canonical interval count");
check21(requests21.getIndexes().length === 1, "Unexpected initial indexes");
```

Synthetic payload makes document fetches necessary for the full response. Use this small bounded fixture to inspect access paths; it does not establish production working-set behavior.

## 6. Define the original response contract

Return the newest twenty recent OPEN requests for tenant-03. Tenant, status and interval are all required semantics, not optional optimization hints.

```javascript
const filter21 = {
  tenantId: "tenant-03", status: "OPEN", seq: { $gte: 2700 }
};
const projection21 = {
  _id: 1, tenantId: 1, status: 1, seq: 1, durationMs: 1, payload: 1
};
const expectedSeq21 = Array.from({ length: 20 }, (_, i) => 2997 - i * 3);
function cursor21(hint) {
  const cursor = requests21.find(filter21, projection21)
    .sort({ seq: -1 }).limit(20);
  return hint === undefined ? cursor : cursor.hint(hint);
}
function verify21(rows) {
  check21(rows.length === 20, "Wrong page size");
  check21(JSON.stringify(rows.map(r => Number(r.seq))) ===
          JSON.stringify(expectedSeq21), "Wrong ordered sequence");
  check21(rows.every(r => r.tenantId === "tenant-03" &&
    r.status === "OPEN" && Number(r.seq) >= 2700),
    "Response violated scope");
}
verify21(cursor21({ $natural: 1 }).toArray());
```

Expected seq values begin 2997, 2994 and 2991. The independent arithmetic oracle prevents a rewrite from declaring its own incorrect output to be the new expected answer.

## 7. Capture a baseline without confusing rejected plans

```javascript
function winningStages21(node, result = new Set()) {
  if (!node || typeof node !== "object") return result;
  if (typeof node.stage === "string") result.add(node.stage);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) {
      value.forEach(child => winningStages21(child, result));
    } else if (value && typeof value === "object") {
      winningStages21(value, result);
    }
  }
  return result;
}
function summarize21(label, explain) {
  const stats = explain.executionStats;
  check21(stats && stats.executionSuccess, label + " execution failed");
  const summary = {
    label,
    returned: stats.nReturned,
    keys: stats.totalKeysExamined,
    documents: stats.totalDocsExamined,
    millis: stats.executionTimeMillis,
    stages: [...winningStages21(explain.queryPlanner.winningPlan)],
    shapeHash: explain.queryPlanner.planCacheShapeHash ||
               explain.queryPlanner.queryHash || null,
    planCacheKey: explain.queryPlanner.planCacheKey || null
  };
  printjson(summary);
  return summary;
}
const baselineExplain21 = cursor21({ $natural: 1 }).explain("executionStats");
const baseline21 = summarize21("baseline-natural", baselineExplain21);
check21(baseline21.returned === 20, "Wrong baseline output count");
check21(baseline21.documents === 30000, "Expected full baseline traversal");
check21(baseline21.stages.includes("COLLSCAN"), "Unexpected baseline access");
check21(baseline21.stages.includes("SORT"), "Expected baseline sort");
```

Preserve the full explain, not just this summary. Examine executionStages for where work occurred. Stage-level counters describe local stages; do not sum every stage's returned count as if each represented different documents.

The forced natural scan creates a controlled reference. It is not an instruction to hint production traffic.

## 8. Form hypotheses and compare completed candidate runs

Hypothesis A: tenant-only indexing reduces scope but leaves status/range filtering and sort. Hypothesis B: the compound index binds tenant/status and traverses the sequence interval in response order.

```javascript
requests21.createIndex({ tenantId: 1 }, { name: "tenant_only" });
requests21.createIndex(
  { tenantId: 1, status: 1, seq: -1 },
  { name: "tenant_status_seq" }
);
verify21(cursor21("tenant_only").toArray());
verify21(cursor21("tenant_status_seq").toArray());
const tenantExplain21 = cursor21("tenant_only").explain("executionStats");
const compoundExplain21 = cursor21("tenant_status_seq").explain("executionStats");
const tenant21 = summarize21("tenant-only", tenantExplain21);
const compound21 = summarize21("compound", compoundExplain21);
check21(tenant21.documents === 3000, "Tenant-only scope mismatch");
check21(tenant21.stages.includes("SORT"), "Expected tenant-only sort");
check21(compound21.returned === 20, "Compound count mismatch");
check21(compound21.documents === 20, "Expected fetching the requested page");
check21(!compound21.stages.includes("SORT"), "Compound left blocking sort");
check21(compound21.keys <= 25, "Unexpectedly broad compound scan");
printjson(compoundExplain21.queryPlanner.winningPlan);
```

Inspect indexName, direction, indexBounds and residual filters. The projection contains payload and durationMs, so FETCH is expected for the compound path. Index usage is useful here because examined work falls and sort disappears while results stay identical.

If counters or stages differ, record the exact version, index definitions and fixture counts. Check unexpected collation, schema/type variation or concurrent writes. Do not change the assertions merely to make a run pass.

## 9. Inspect candidate trials without overinterpreting them

```javascript
const plannerOnly21 = cursor21().explain("queryPlanner");
printjson({
  winningPlan: plannerOnly21.queryPlanner.winningPlan,
  rejectedPlans: plannerOnly21.queryPlanner.rejectedPlans
});
const candidates21 = cursor21().explain("allPlansExecution");
summarize21("unhinted-allPlansExecution", candidates21);
printjson(candidates21.executionStats.allPlansExecution || []);
verify21(cursor21().toArray());
```

Record the optimizer-selected winner. A strong candidate is tenant_status_seq, but the actual response is the evidence. Do not require a fixed number of rejected plans or trial records: eligible candidates, shortcuts and engine behavior can change the output.

The top-level executionStats describes completed winning execution. Entries in allPlansExecution describe partial trials captured during selection. A low returned count or low work count for a rejected plan can simply mean it lost before completion.

Named hints bypass parts of ordinary candidate selection and can change explain timing. A lower hinted executionTimeMillis does not by itself prove a beneficial permanent hint.

## 10. Failure exercise: limit before filter changes results

An engineer might try to “reduce work” by taking the newest twenty tenant records before selecting OPEN status. That is a different query.

```javascript
const wrongPipeline21 = [
  { $match: { tenantId: "tenant-03", seq: { $gte: 2700 } } },
  { $sort: { seq: -1 } },
  { $limit: 20 },
  { $match: { status: "OPEN" } },
  { $project: projection21 }
];
const wrongRows21 = requests21.aggregate(wrongPipeline21).toArray();
check21(wrongRows21.length === 6, "Unexpected failure fixture result");
check21(JSON.stringify(wrongRows21.map(r => Number(r.seq))) !==
        JSON.stringify(expectedSeq21),
        "Wrong rewrite unexpectedly preserved canonical page");
printjson({ wrongResultCount: wrongRows21.length,
            wrongSequence: wrongRows21.map(r => r.seq) });
```

It returns only six OPEN requests from the newest twenty requests of any status. The original contract requires the newest twenty OPEN requests. A faster run with fewer results is not an optimization of that contract.

Correct by applying all required filters before the top-k boundary:

```javascript
const correctPipeline21 = [
  { $match: filter21 },
  { $sort: { seq: -1 } },
  { $limit: 20 },
  { $project: projection21 }
];
const correctRows21 = requests21.aggregate(correctPipeline21).toArray();
verify21(correctRows21);
const aggregationExplain21 = requests21.explain("executionStats")
  .aggregate(correctPipeline21);
printjson(aggregationExplain21);
```

Inspect the aggregate's actual output structure. The cursor plan may be top-level or under a stages/$cursor object depending on optimization and engine. Do not feed it into the find-only summary helper and mistake a missing executionStats path for no work.

The optimizer can move independent matches earlier and coalesce sort/limit under suitable conditions. It cannot arbitrarily move a filter across a limit when that would change semantics. Avoid claims that manually adding an early projection always improves performance; MongoDB already performs field-dependency optimization.

## 11. Coverage experiment: reduce fetches only if the contract allows it

For a separate lean list response that does not require payload or duration, project only fields in the compound index and exclude _id:

```javascript
const leanProjection21 = {
  _id: 0, tenantId: 1, status: 1, seq: 1
};
const leanRows21 = requests21.find(filter21, leanProjection21)
  .sort({ seq: -1 }).limit(20).hint("tenant_status_seq").toArray();
verify21(leanRows21);
const leanExplain21 = requests21.find(filter21, leanProjection21)
  .sort({ seq: -1 }).limit(20).hint("tenant_status_seq")
  .explain("executionStats");
const lean21 = summarize21("lean-covered-contract", leanExplain21);
check21(lean21.returned > 0 && lean21.documents === 0,
        "Nonempty lean response not covered");
check21(!lean21.stages.includes("FETCH"), "Lean winning plan fetched");
```

This is explicitly a different response contract. It preserves identifiers in the form of sequence within fixed tenant scope and result eligibility, but omits original detail fields. It is appropriate only when callers accept that lean interface.

Do not silently remove required output to win a benchmark. Alternatively measure a wider index against storage/write cost or keep a small bounded fetch. Chapter 18 explains that coverage does not guarantee narrow key work.

## 12. Empty results and amplification ratios

Ratios can summarize targeting, but never divide by zero or interpret an empty result as evidence of coverage:

```javascript
function amplification21(summary) {
  if (summary.returned === 0) {
    return { keysPerReturned: null, docsPerReturned: null,
             note: "Empty result; inspect absolute work and bounds" };
  }
  return {
    keysPerReturned: summary.keys / summary.returned,
    docsPerReturned: summary.documents / summary.returned
  };
}
printjson({
  baseline: amplification21(baseline21),
  tenant: amplification21(tenant21),
  compound: amplification21(compound21),
  lean: amplification21(lean21)
});
const emptyExplain21 = requests21.find({
  tenantId: "tenant-does-not-exist", status: "OPEN", seq: { $gte: 2700 }
}, projection21).sort({ seq: -1 }).limit(20)
  .hint("tenant_status_seq").explain("executionStats");
const empty21 = summarize21("empty-result", emptyExplain21);
check21(empty21.returned === 0, "Empty fixture unexpectedly matched");
check21(amplification21(empty21).docsPerReturned === null,
        "Empty-result ratio mishandled");
```

For this baseline, 30,000 examined documents produce twenty returned rows. That ratio is a diagnostic signal, not a universal alert threshold. Broad exports legitimately return many records; empty probes can legitimately examine some keys. Evaluate query shape, frequency and absolute workload.

## 13. Bridge explain evidence to application latency

Run ordinary queries to completion if measuring client-visible time. Constructing a cursor without consuming it does not measure the full response.

```javascript
const samples21 = [];
for (let run = 0; run < 5; run++) {
  const started = Date.now();
  const rows = cursor21().toArray();
  const elapsed = Date.now() - started;
  verify21(rows);
  samples21.push({ run, elapsedMs: elapsed, rows: rows.length });
}
printjson(samples21);
```

These five shell observations include client/server interaction and materialization for a tiny fixture. They are not reliable production percentiles or a controlled cold-cache comparison. Do not clear caches, restart servers or flush plan caches to make the experiment look cleaner.

When application latency remains high despite a narrow plan, investigate connection-pool waiting, retries, network/TLS, result serialization, getMore activity, server contention and storage/cache pressure. Explain alone cannot allocate end-to-end latency to those components.

Use profiler/log/metrics evidence for actual requests in Chapter 22. Avoid enabling expensive diagnostics globally as a reflex.

## 14. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| IXSCAN but high work | Bounds, keys/docs examined, residual filters | Weak selectivity or unsuitable compound order | Compare completed candidate paths |
| SORT despite index | Full sort and key pattern | Equality prefix or direction mismatch | Align complete ordering and verify results |
| Rejected candidate appears cheap | allPlansExecution trial versus winning completion | Incomplete trial statistics | Run candidate to completion under controlled hint |
| Empty query appears covered | nReturned, projection and plan | No documents needed because no matches | Prove coverage with a nonempty fixture |
| “Optimized” pipeline returns fewer rows | Exact sequence comparison | Limit/filter semantics changed | Restore contract before performance evaluation |
| Aggregate summary has missing fields | Full aggregate explain | Different output layout/engine | Inspect $cursor/stages or optimized top-level plan |
| Shell timing differs from explain | Fully consumed result, request context | Different selection/network/materialization work | Separate server work from client latency |
| Plan changed after index modification | Definitions, shape hash, planCacheKey | Candidate set changed | Recollect current plans and real request evidence |

Keep rejected-plan details separate from winning-plan assertions. Do not recursively search the whole explain for FETCH or SORT and then attribute a rejected candidate's stages to the winner.

## 15. Production investigation workflow

1. Capture a sanitized query shape, parameter class, sort, projection, limit, collation and connection/read settings.
2. Define expected result semantics and a correctness oracle or reconciliation method.
3. Collect baseline explain and actual-request latency/work evidence over a representative interval.
4. Identify the expensive operation: broad scan, fetch/filter, sort, join, grouping or excessive result volume.
5. Form one concrete hypothesis and compare candidate paths or a semantics-preserving rewrite.
6. Verify exact result equivalence before evaluating latency, throughput, index size and write impact.
7. Review rollout and reversal paths, including named hints and index/query-setting dependencies.
8. Observe representative production traffic after rollout and retain evidence of both benefit and regressions.

Keep values and payloads sanitized without hiding type, cardinality or bounds information needed for diagnosis. Tenant skew and range parameters can materially change plans even when the query looks similar.

Do not use permanent hints as a substitute for workload analysis. Query settings and plan-cache operations are version-specific operational tools and need their own deliberate scope; this chapter does not change either.

## 16. Cleanup

Save fixture counts, full plans, comparison summaries, wrong/correct pipeline outputs and timing caveats before cleanup:

```javascript
verify21(cursor21("tenant_status_seq").toArray());
check21(requests21.countDocuments({}) === 30000, "Fixture changed");
if (lab21.getName() !== "mongodb_enterprise_tutorial_ch21") {
  throw new Error("Refusing cleanup outside the Chapter 21 training database");
}
const dropResult21 = lab21.dropDatabase();
check21(dropResult21.ok === 1, "Database cleanup command failed");
check21(lab21.getCollectionNames().length === 0, "Cleanup incomplete");
```

All data and indexes belong to the named chapter database. No shared settings or external application resources were changed. Dropping the lab database is the only required cleanup.

## 17. Acceptance and evidence

- [ ] Recorded exact server/shell versions and unsharded context.
- [ ] Verified fixture cardinality and exact canonical result sequence.
- [ ] Captured collection-scan baseline and completed hinted candidate comparisons.
- [ ] Explained winning-plan versus rejected-plan/trial evidence.
- [ ] Inspected bounds, fetched documents and blocking sort behavior.
- [ ] Reproduced incorrect limit-before-filter semantics and repaired the pipeline.
- [ ] Verified nonempty lean coverage without presenting it as the original full response.
- [ ] Handled empty-result ratios without division by zero.
- [ ] Consumed ordinary cursors for timing and documented measurement limits.
- [ ] Saved evidence and completed scoped cleanup.

**Evidence:** versions, query contract, index definitions, fixture/result assertions, all full explain documents, candidate counters, aggregation correction, empty-result handling, timing samples and cleanup. Runtime lab validation remains pending until these commands run successfully on the stated deployment.

## 18. Review questions

1. Why does an IXSCAN not prove that a query is efficient?
2. Why cannot partial rejected-plan trial counters be compared directly with full winning execution?
3. What does explain tell you about an existing production cached plan?
4. Why does moving a filter after a limit change this lab's result?
5. When is a covered lean response an acceptable interface change?
6. Why are zero document examinations for an empty query insufficient proof of coverage?
7. Which end-to-end latency components are outside explain's evidence?
8. What correctness evidence must precede a production optimization claim?

## 19. Official references

- [MongoDB 8.0: explain results and execution counters](https://www.mongodb.com/docs/v8.0/reference/explain-results/)
- [MongoDB 8.0: cursor.explain verbosity](https://www.mongodb.com/docs/v8.0/reference/method/cursor.explain/)
- [MongoDB 8.0: query plans and plan-cache behavior](https://www.mongodb.com/docs/v8.0/core/query-plans/)
- [MongoDB 8.0: query optimization](https://www.mongodb.com/docs/v8.0/core/query-optimization/)
- [MongoDB 8.0: aggregation pipeline optimization](https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-optimization/)

---

Previous: [Chapter 20 — TTL Retention and Index Lifecycle](20-ttl-retention-and-index-lifecycle.md)  
Next: [Chapter 22 — Profiling Slow Queries and Query Statistics](22-profiling-slow-queries-and-query-statistics.md).
