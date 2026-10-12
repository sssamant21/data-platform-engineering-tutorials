# 73 — Query Slowness Investigation Runbook

Part 10 — Troubleshooting and Production Projects

**Audience:** DBREs, SREs, Developers and on-call engineers.  
**Goal:** Locate the latency boundary, collect bounded evidence, reproduce inefficient query work, verify a correction without changing results, and close the incident with service recovery evidence.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set; exact recorded mongosh and Python 3.11+ for offline fixture checks. Core lab is Community-compatible; sharded/managed deployments require their own scope review.  
**Status:** Written; JavaScript/Python syntax and offline fixture checks complete; live explain/query/incident acceptance pending.  
**Prerequisites:** Chapters 17–24, 27, 37, 63 and 69–71; current service objectives, member inventory and maintenance ownership.  
**Estimated time:** 60–90 minutes for the lab; incident triage should start immediately with bounded observations.

## 1. Incident contract and first response

Start with the affected service, tenant/workload, namespace, UTC window, observed latency/error change and comparison baseline. Preserve the exact query filter, projection, sort, collation, limit, pagination, read preference/concern and client timeout settings through an approved restricted evidence path.

A slow request can spend time before MongoDB receives it, inside query execution, waiting for results/getMore, during network transfer or during application processing. A fast explain alone does not clear the database or application.

The lab demonstrates excessive scan/sort work using a deliberately forced collection scan, a compound-index correction, a field-type mismatch and an owned hidden-index regression/restoration. It verifies deterministic result identity and work reduction. It does not claim the small fixture will be slow in milliseconds or reproduce production saturation.

Acceptance requires:

- Latency boundary and incident scope documented.
- Matching bounded query results before/after correction.
- Completed explain statistics, not just an index name.
- Correct typing and tenant scope retained.
- Index regression detected, restored and reverified.
- Service, resource and correctness evidence accepted before closure.

## 2. Triage the latency boundary

| Boundary | Evidence | Next investigation |
|---|---|---|
| Before database command | Client pool wait, server selection, DNS/TLS/connect time | Chapter 63 client lifecycle and Chapter 74 connectivity |
| Active database operation | Scoped currentOp, logs/profiler, completed plan work | Index/selectivity/sort/contention and resource context |
| Result transfer/getMore | Batch count, response size, network and cursor timing | Projection, pagination, payload and cursor lifecycle |
| After retrieval | Application trace and serialization/rendering time | Service implementation and downstream dependencies |
| Broad deployment slowdown | Multiple query shapes, CPU/I/O/cache/replication | Chapter 75 resource incident and Chapter 76 topology |

Compare affected versus unaffected services and members. Do not infer causation from one high utilization panel. Connect query work with the same UTC resource/trace interval.

If user impact is severe, apply an already accepted service mitigation such as bounding ingestion/concurrency or load shedding while evidence is captured. Unbounded retries can amplify demand. A timeout increase alone can extend queue occupancy without fixing the bottleneck.

## 3. Bounded initial evidence

Use the accepted TLS/SCRAM connection and an observer authorized for the required commands. Application queries use the replica-set-aware URI; member-local diagnostics need explicit member identity.

```javascript
printjson({ observedAt: new Date(), server: db.version(), hello: db.hello() });
var admin = db.getSiblingDB("admin");
var status = admin.runCommand({ serverStatus: 1 });
if (status.ok !== 1) throw new Error("Process evidence failed");
printjson({ host: status.host, pid: status.pid, uptime: status.uptime,
  connections: status.connections, opcounters: status.opcounters,
  opLatencies: status.opLatencies });
```

Use Chapter 69's valid counter intervals and host/PVC/cloud disk mapping. Review replication, background ingestion, maintenance and recent index/schema/configuration changes. Lifetime totals are not incident-window rates.

To inspect only active operations tagged for a known synthetic/lab scope, an authorized observer can run:

```javascript
printjson(db.getSiblingDB("admin").aggregate([
  { $currentOp: { allUsers: true, idleConnections: false } },
  { $match: { active: true, "command.comment": /^ch73-/ } },
  { $project: { _id: 0, opid: 1, ns: 1, secs_running: 1,
                waitingForLock: 1, "command.comment": 1 } },
  { $limit: 20 }
]).toArray());
```

This is an in-progress snapshot, not completed execution evidence.[1] Fast commands may finish before the observation; no match does not prove no requests ran. Adjust the approved incident filter to the actual namespace/comment contract rather than dumping all command payloads. Sharded currentOp scope/IDs require router/shard review.

Do not kill an operation merely because it is old. Identify its owner, purpose, read/write/transaction scope and recovery behavior before using the deployment's accepted cancellation procedure.

## 4. Explain interpretation and limitations

Start with the exact query and a bounded scope. `queryPlanner` describes planning; `executionStats` runs the operation to collect work, so it can add load. Review estimated cost and target before running a production explain that might scan a large dataset.

| Evidence | Interpretation |
|---|---|
| nReturned | Results produced by the explained operation, including its limit |
| totalDocsExamined | Document work; compare to results and selectivity |
| totalKeysExamined | Index work; an index can still scan many keys |
| Winning-plan tree | Bounds, fetch, blocking sort and engine-specific stages |
| executionTimeMillis | One server execution observation; not application P99 |
| Actual logs/profiler/traces | Real operation context, workload and client timing |

MongoDB explain ignores the plan cache and does not cache its winning plan.[2] A good explain therefore does not prove that ordinary production executions used that plan. Preserve real execution evidence and inspect version-specific plan/cache/query-settings context when diagnosing a regression.

Explain output differs between engines/versions. Read complete trees and per-shard work where applicable. Do not build an incident conclusion around a single hardcoded stage path. For zero-result queries, examined/returned division is undefined; report the work directly.

## 5. Lab setup — synthetic multi-tenant workload

Connect through Chapter 42's lifecycle identity. Create a fresh owned namespace on the retained primary. This fixture contains 20,000 modest documents; do not increase it to production scale to manufacture latency.

```javascript
var labName = "mongodb_enterprise_ch73_slowness";
var lab = db.getSiblingDB(labName);
function check(condition, message) { if (!condition) throw new Error(message); }
check(lab.getCollectionInfos().length === 0, "Namespace already exists");
check(db.hello().isWritablePrimary === true, "Expected writable primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch73", createdAt: new Date() });
var baseTime = ISODate("2026-01-01T00:00:00Z");
for (var batch = 0; batch < 20; batch++) {
  var rows = [];
  for (var offset = 0; offset < 1000; offset++) {
    var i = batch * 1000 + offset;
    rows.push({ _id: i, tenant: "tenant-" + (i % 100), seq: i,
      createdAt: new Date(baseTime.getTime() + i * 1000),
      amount: i % 1000, payload: "synthetic" });
  }
  lab.events.insertMany(rows, { writeConcern: { w: "majority", wtimeout: 10000 } });
}
check(lab.events.countDocuments({}) === 20000, "Fixture count mismatch");
var filter = { tenant: "tenant-7", createdAt: { $gte: baseTime } };
var projection = { _id: 1, tenant: 1, seq: 1, createdAt: 1 };
var ordering = { createdAt: -1, _id: -1 };
function cursor(tag) {
  return lab.events.find(filter, projection).sort(ordering).limit(10)
    .maxTimeMS(10000).comment(tag);
}
var expectedIds = [19907, 19807, 19707, 19607, 19507,
                   19407, 19307, 19207, 19107, 19007];
function verify(rows) {
  check(rows.length === 10, "Expected ten rows");
  check(EJSON.stringify(rows.map(r => r._id)) === EJSON.stringify(expectedIds),
        "Identity/order mismatch");
  check(rows.every(r => r.tenant === "tenant-7"), "Tenant boundary changed");
}
```

Expected: 200 rows belong to tenant-7; latest ten IDs are 19907 down to 19007 at steps of 100. `_id` supplies a deterministic tie-breaker. Production duplicate timestamps make stable ordering important even though this fixture has unique times.

## 6. Lab A — inefficient scan/sort evidence

Force natural scan on the owned fixture to reproduce a known inefficient path. The forced baseline is pedagogical; do not claim the production planner chose it.

```javascript
var baselineRows = cursor("ch73-baseline").hint({ $natural: 1 }).toArray();
verify(baselineRows);
var baselineExplain = cursor("ch73-baseline-explain").hint({ $natural: 1 })
  .explain("executionStats");
check(baselineExplain.executionStats.nReturned === 10, "Explain result count mismatch");
check(baselineExplain.executionStats.totalDocsExamined >= 20000,
      "Expected full fixture document work");
printjson(baselineExplain);
```

Expected: correct latest ten results, full fixture scan work and a sort-related execution path. Capture actual keys/documents examined, elapsed time and plan tree. A low millisecond execution time on this small cached fixture does not invalidate the excessive-work diagnosis.

Look for production analogues: broad tenant/date predicates, unsupported sorts, deep offset pagination, excessive result size, unanchored searches and inefficient joins/unwinds. Verify each against the exact query contract and completed evidence.

## 7. Lab B — compound index and equivalence

Create an owned candidate index with tenant equality followed by the ordered timestamp and tie-breaker. This supports the fixture's tenant-scoped latest-row query.

```javascript
lab.events.createIndex({ tenant: 1, createdAt: -1, _id: -1 }, {
  name: "tenant_created_id"
});
var indexedRows = cursor("ch73-indexed").hint("tenant_created_id").toArray();
verify(indexedRows);
check(EJSON.stringify(indexedRows) === EJSON.stringify(baselineRows),
      "Index correction changed result documents");
var indexedExplain = cursor("ch73-indexed-explain").hint("tenant_created_id")
  .explain("executionStats");
check(indexedExplain.executionStats.nReturned === 10, "Indexed explain result mismatch");
check(indexedExplain.executionStats.totalDocsExamined <
      baselineExplain.executionStats.totalDocsExamined, "Document work did not improve");
check(indexedExplain.executionStats.totalKeysExamined > 0, "Expected indexed key work");
printjson(indexedExplain);
var unhintedRows = cursor("ch73-unhinted").toArray();
verify(unhintedRows);
printjson(cursor("ch73-unhinted-explain").explain("executionStats"));
```

Expected: identical projected documents/order and much lower document work for the forced indexed path. Inspect the unhinted plan separately rather than assuming a hint proves the real planner's choice. Projection includes `seq`, which is not in the candidate index, so the lab does not claim covered execution.

An index adds write, storage and cache costs. Review representative workloads, collation, data distribution and index build headroom before a production change. Do not add multiple speculative indexes during an incident without testing the specific supported query.

## 8. Lab C — field-type failure and repair

An index cannot correct a filter using the wrong BSON type. Compare a Date predicate with an ISO-formatted string predicate in the owned fixture.

```javascript
var wrongType = lab.events.find({ tenant: "tenant-7",
  createdAt: { $gte: baseTime.toISOString() } }, projection)
  .sort(ordering).limit(10).maxTimeMS(10000).toArray();
check(wrongType.length === 0, "Expected type-bracketed string/date mismatch");
var repairedRows = cursor("ch73-type-repaired").toArray();
verify(repairedRows);
printjson({ malformedFilterRows: wrongType.length, repairedRows: repairedRows.length });
```

Expected: the string range returns zero; the Date range returns the correct ten IDs. This negative test demonstrates correctness failure, not just slower execution. Mixed stored types require their own schema inventory and controlled migration from Chapter 11; blindly coercing every source value can change meaning.

Preserve exact types in incident reproduction. An anonymized query that converts Dates/ObjectIds to strings may no longer reproduce the application's actual plan or results.

## 9. Lab D — index regression, diagnosis and restoration

Hide the known originally visible candidate to reproduce a planner-support regression. The unhinted query still has a correct fallback; explicit use of the hidden index should fail.[3]

```javascript
var originalIndex = lab.events.getIndexes().find(x => x.name === "tenant_created_id");
check(originalIndex && originalIndex.hidden !== true, "Expected visible owned index");
check(lab.runCommand({ collMod: "events", index: {
  name: "tenant_created_id", hidden: true
} }).ok === 1, "Hide failed");
var hidden = lab.events.getIndexes().find(x => x.name === "tenant_created_id");
check(hidden && hidden.hidden === true, "Hidden metadata absent");
var rejected = false;
try { cursor("ch73-hidden-hint").hint("tenant_created_id").toArray(); }
catch (error) {
  rejected = true;
  printjson({ expectedHiddenHintFailure: true, code: error.code, message: error.message });
}
check(rejected, "Hidden-index hint unexpectedly accepted");
verify(cursor("ch73-fallback").toArray());
printjson(cursor("ch73-fallback-explain").explain("executionStats"));
```

Confirm the actual error is the expected hidden-index hint failure; a transport or permission error is not a passed drill. Capture index metadata, fallback plan and workload correctness. In production, correlate a recent index/setting change with actual executions rather than merely observing temporal proximity.

Restore this fixture's originally visible index even after an interrupted drill, after verifying ownership/current state:

```javascript
var lab = db.getSiblingDB("mongodb_enterprise_ch73_slowness");
check(lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch73" }) !== null,
      "Ownership missing");
check(lab.runCommand({ collMod: "events", index: {
  name: "tenant_created_id", hidden: false
} }).ok === 1, "Visibility restoration failed");
var restoredIndex = lab.events.getIndexes().find(x => x.name === "tenant_created_id");
check(restoredIndex && restoredIndex.hidden !== true, "Index remains hidden");
verify(cursor("ch73-restored").hint("tenant_created_id").toArray());
check(lab.events.countDocuments({}) === 20000, "Fixture state changed");
print("PASS: owned regression reversed and query contract restored");
```

The sequential mongosh session retains `cursor`, `verify` and fixture variables. If reconnecting after interruption, reestablish those helpers from Section 5 without rerunning data creation. Do not reuse a populated namespace as a fresh fixture.

## 10. Logs, profiler and application evidence

Correlate tagged actual operations with a bounded log/profiler window from Chapter 22 and trace timing from the affected service. Fast operations may not appear in slow logs. Profiler settings, filters and sampled records need a recorded original state, scoped permissions, payload handling and restoration.[4]

This lab does not enable profiling or lower deployment-wide slow thresholds. If production evidence needs profiling, use the previously accepted controlled procedure and restore exact prior settings, including any existing filter. Do not enable level 2 indefinitely or treat slow-log threshold changes as harmless global sampling.

Explain is one execution experiment. Real traces should separate pool wait, selection/connect, command duration, getMore/result transfer and application processing. Multiple batches and a large payload can dominate a request even when an individual query is indexed.

Keep request IDs/query details in controlled logs/traces rather than unbounded monitoring labels. Store only the minimum evidence needed for the incident and redact sensitive values without changing relevant BSON types or selectivity in the reproduction.

## 11. Mitigation selection and stop conditions

| Finding | Candidate mitigation | Verification |
|---|---|---|
| Excess document/key scan | Correct predicate/index or selective scope | Same results plus reduced completed work |
| Blocking sort | Supported sort/index or bounded query design | Stable order and actual sort/work/latency evidence |
| Oversized results | Projection, bounded page size and cursor pagination | Application contract and payload/getMore timing |
| Deep skip | Seek-based pagination with stable key | No missing/duplicate records under declared update semantics |
| Pool wait/retry storm | Bound concurrency/pools/retries and deadlines | Client wait/error metrics and recovery behavior |
| CPU/cache/storage pressure | Reduce competing demand or remediate proven resource limit | Application latency plus relevant host/process metrics |
| Sharded fan-out/skew | Review shard-targeting predicate/key and per-shard work | Correct results and actual routing/placement evidence |
| Index/setting regression | Restore recorded supported state | Real query execution and service recovery |

Select one bounded change, state its expected effect and preserve the before evidence. Stop if correctness changes, replication/history headroom deteriorates, resource reserve falls below the agreed budget or service errors increase. A hint can be a reviewed tactical control but may become unsuitable as data/distribution changes; do not silently hardcode it permanently.

Avoid unconditional cache clearing, index rebuilding or process restarting as query-slowness fixes. They can erase evidence, increase cold-cache work and introduce availability risk. Data deletion or storage repair requires separate recovery ownership.

## 12. Recovery verification and incident closure

Verify the affected service's actual SLI and correctness, not only the lab query. Compare similar workload windows, relevant tenants and peak/batch behavior. Do not attribute a latency improvement to an index if traffic dropped or a competing job ended at the same time without acknowledging those factors.

Record before/after query shape, typed predicates, indexes/settings, plan work, payload size, client timing, host/member resource context and UTC change boundary. Keep unresolved hypotheses separate from supported findings.

The RCA should describe trigger, contributing conditions, evidence, mitigation and prevention. Prevention may include schema/index review, query size limits, client backoff/concurrency, performance tests, capacity headroom and alert coverage. Assign an owner and measurable acceptance for each action.

## 13. Offline fixture and result-contract checker

Save as `ch73_fixture_check.py` and run with Python 3.11+. It checks the declared identities/order and exposes a missing-tenant-filter regression. It does not execute MongoDB query planning.

```python
rows = [{"_id": i, "tenant": "tenant-" + str(i % 100), "seq": i}
        for i in range(20000)]
selected = sorted((row for row in rows if row["tenant"] == "tenant-7"),
                  key=lambda row: row["seq"], reverse=True)[:10]
expected = [19907, 19807, 19707, 19607, 19507,
            19407, 19307, 19207, 19107, 19007]
assert [row["_id"] for row in selected] == expected
assert sum(row["tenant"] == "tenant-7" for row in rows) == 200
unscoped = sorted(rows, key=lambda row: row["seq"], reverse=True)[:10]
assert [row["_id"] for row in unscoped] != expected
assert any(row["tenant"] != "tenant-7" for row in unscoped)
print("PASS: fixture identities/order and tenant-scope regression checked")
```

A faster query with a missing tenant predicate is a correctness/security regression, not an optimization. This offline check makes that acceptance boundary explicit.

## 14. Troubleshooting matrix

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Explain fast, request slow | Client trace, payload and getMore timings | Pre/post-command or network latency | Locate boundary and verify service-level recovery |
| Index used but work high | Bounds, keys/docs examined and selectivity | Broad/poorly ordered index or range | Test exact query/index candidate; preserve results |
| Zero results after “fix” | BSON types, filter and fixture identity | Type mismatch or incorrect predicate | Restore exact typed contract; reconcile results |
| Correct results but sort expensive | Plan tree, sort/payload and index options | Unsupported sort/collation | Evaluate matching index or query redesign |
| Latest page unstable | Tie-breaker and concurrent mutations | Non-deterministic order/deep offset | Define stable seek contract and acceptance |
| Plan differs from explain | Real logs/profiler, cache/settings/index history | Explain bypasses plan cache | Inspect actual execution context before remediation |
| CurrentOp shows nothing | Comment/filter, polling window and completed logs | Operation finished before observation | Use completed evidence; record snapshot limitation |
| Profiler/log overhead increases | Profiling settings, volume and resource impact | Excessive capture or payload | Restore prior scope/settings and verify collection health |
| One shard dominates | Per-shard work, routing and resource metrics | Skew/hot placement or fan-out | Use Chapter 37/76 routing investigation |
| Timeout raised, queue worsens | Concurrent demand, retries and pool wait | Work retained longer without capacity fix | Bound demand/deadlines; verify correctness and recovery |

## 15. Acceptance evidence and scoped cleanup

| Check | Expected evidence |
|---|---|
| Incident scope | Service/namespace/member, UTC window, exact typed query and client contract |
| Fixture | 20,000 rows; 200 tenant-7 rows; declared latest ten IDs |
| Baseline | Correct results and full forced-scan document work |
| Candidate | Identical projected results; fewer docs examined; actual key/plan evidence |
| Unhinted execution | Correct query results and separately captured plan |
| Type drill | Wrong string predicate returns zero; Date predicate correct |
| Regression/reversal | Hidden metadata/hint failure; restored visibility/hinted results |
| Closure | Actual service/resource/correctness acceptance and owned follow-up |

Save nonsecret full explain output and relevant live query/trace evidence before cleanup. Restore the owned index first, then run through the accepted lifecycle identity:

```javascript
var labName = "mongodb_enterprise_ch73_slowness";
var lab = db.getSiblingDB(labName);
check(lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch73" }) !== null,
      "Ownership missing");
var index = lab.events.getIndexes().find(x => x.name === "tenant_created_id");
check(index && index.hidden !== true, "Restore owned index before cleanup");
check(lab.dropDatabase().ok === 1, "Owned cleanup failed");
check(db.getSiblingDB(labName).getCollectionInfos().length === 0,
      "Cleanup left collections");
print("PASS: chapter-owned slowness fixture removed");
```

Keep the retained deployment, global profiler/logging settings, FTDC and other chapter data under their existing owners. Local fixture script/evidence may remain until its lab retention policy expires.

Review questions:

1. Why does indexed execution not prove low query work?
2. Why can explain differ from the ordinary cached execution path?
3. Which client boundaries can explain miss entirely?
4. How does result equivalence protect an optimization decision?
5. Why are typed anonymized predicates necessary for reproduction?
6. Why does currentOp absence not prove the workload was absent?
7. What additional evidence is needed for sharded slowness?
8. What closes the incident beyond an improved explain time?

## 16. Official references and validation status

1. [MongoDB 8.0 — currentOp aggregation stage](https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/currentOp/).
2. [MongoDB 8.0 — Explain Results](https://www.mongodb.com/docs/v8.0/reference/explain-results/).
3. [MongoDB 8.0 — Hidden Indexes](https://www.mongodb.com/docs/v8.0/core/index-hidden/).
4. [MongoDB 8.0 — Database Profiler](https://www.mongodb.com/docs/v8.0/tutorial/manage-the-database-profiler/).

Documentation reviewed on 2026-10-12. The forced baseline, fixture, result checks, observation scope and incident gates are teaching designs. JavaScript/Python syntax and actual offline fixture/scope assertions were checked. These checks do not validate live server plan shapes, work counters, BSON comparison behavior, permissions, profiling or application latency. No live MongoDB incident lab was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline fixture acceptance complete. Runtime validation remains pending until the authorized query-plan, type, regression/restoration and cleanup drills are executed with evidence.

Previous: [Chapter 72 — Cost Optimization and Enterprise License Planning](72-cost-optimization-and-enterprise-license-planning.md).  
Next: Chapter 74 — Connection Authentication and TLS Troubleshooting.
