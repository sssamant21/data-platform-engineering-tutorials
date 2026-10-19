# 77 — Production Data Modeling and Query Tuning Project

Part 10 — Troubleshooting and Production Projects

**Audience:** Developers, Data Engineers, DBREs and SREs.  
**Goal:** Design a tenant-scoped work queue, enforce its schema/identity contract, tune ordered queries, verify pagination and guarded updates, and assemble a production acceptance packet.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set; exact recorded mongosh and Python 3.11+ for offline contract checks. Core project is Community-compatible.  
**Status:** Written; syntax and offline modeling/pagination checks complete; live database and representative performance acceptance pending.  
**Prerequisites:** Chapters 9–21, 27, 41–42, 63, 68–73; accepted deployment, application identity and monitoring/capacity contract.  
**Estimated time:** 90–120 minutes for the bounded fixture; production workload validation is a separate stage.

## 1. Project requirements and acceptance contract

Build a synthetic tenant work queue. A card needs task identity, status, creation time, revision and a small checklist in one response. Historical events can grow independently and belong in a separate collection. No real patient or production data is used.

| Access pattern | Required behavior | Model/index decision |
|---|---|---|
| Latest open cards for one tenant | Stable newest-first order, bounded page | Equality tenant/status plus time/identity sort |
| One task detail | Tenant-scoped identity and complete bounded checklist | Unique tenant/externalId index |
| Status transition | Reject stale revision and return declared outcome | Single-document compare-and-set update |
| History lookup | Separate, bounded time window | Reference by tenant/task identity; independent lifecycle |
| Subsequent page | Continue from a typed stable ordering key | Seek predicate with time plus identity tie-breaker |

Acceptance requires valid typed documents, enforced business uniqueness, identical baseline/indexed results, reduced completed query work, safe tenant-scoped pagination, rejected invalid/stale operations and an explicit production rollout/recovery plan.

The fixture establishes correctness and query work. It does not establish production P99, throughput, failover resilience or recovery capacity. Those need representative data, concurrency and the later project stages.

## 2. Model design and tradeoffs

Embed the bounded checklist because it is read with the card and fits the task's single-document update boundary. Keep unbounded historical events separate. This follows access-pattern-driven modeling rather than copying a relational table layout mechanically.[1]

The task owns its current status and revision. A separate history collection is not automatically transactionally consistent with a task update. If every status change requires a durable event record, define a supported transaction/outbox or another proven capture contract. This project tests only the single-document task transition; it does not claim audit atomicity.

Avoid copying mutable external profile data into every task without a refresh/reconciliation owner. If summaries are denormalized, record source identity/version, freshness and repair behavior. Keep sensitive fields outside queue projections unless the caller needs them.

Tenant predicates are part of application authorization/correctness. A tenant field and index do not independently enforce row-level access; scoped identities/application policy must be reviewed. Never accept faster queries obtained by removing tenant filtering.

## 3. Schema and index contracts

The project uses BSON Date for creation time, an integer revision, a bounded three-item checklist and a closed status set. A validator enforces critical field types and bounds; application validation still owns business transitions and caller identity.[2]

Unique `{tenant, externalId}` expresses business identity within a tenant. The queue index uses equality fields first, then the requested order. ESR is a design guideline; alternate range selectivity/order tradeoffs need actual query evidence.[3]

Index costs include builds, writes, cache and storage. Do not add an index for every filter combination without a weighted workload and capacity review. Collation, partial predicates, arrays/multikey and sort directions must match the actual application contract.

## 4. Connection, permissions and owned setup

Connect using Chapter 42's verified TLS/SCRAM procedure to the retained primary. The lifecycle identity creates the owned namespace, validator and indexes. A separate application identity should receive only required reads/updates on its approved scope. Observation needs authorized explain/metadata access.

Record exact server/FCV, shell, topology, identities, UTC start and relevant monitor window. Run the following blocks sequentially in one mongosh session. Stop if an assertion fails; do not rerun fixture creation over partial state.

```javascript
var labName = "mongodb_enterprise_ch77_modeling";
var lab = db.getSiblingDB(labName);
function check(condition, message) { if (!condition) throw new Error(message); }
check(lab.getCollectionInfos().length === 0, "Namespace already exists");
check(db.hello().isWritablePrimary === true, "Expected writable primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch77", createdAt: new Date() });
var created = lab.createCollection("tasks", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["tenant", "externalId", "status", "createdAt", "revision", "checklist"],
    properties: {
      tenant: { bsonType: "string" }, externalId: { bsonType: "string" },
      status: { enum: ["open", "done"] }, createdAt: { bsonType: "date" },
      revision: { bsonType: "int", minimum: 1 },
      checklist: { bsonType: "array", maxItems: 3, items: {
        bsonType: "object", required: ["label", "done"],
        properties: { label: { bsonType: "string" }, done: { bsonType: "bool" } }
      } }
    }
  } }, validationLevel: "strict", validationAction: "error"
});
check(created.ok === 1, "Schema creation failed");
lab.tasks.createIndex({ tenant: 1, externalId: 1 }, {
  name: "tenant_external_unique", unique: true
});
var base = ISODate("2026-01-01T00:00:00Z");
for (var batch = 0; batch < 10; batch++) {
  var rows = [];
  for (var offset = 0; offset < 1000; offset++) {
    var i = batch * 1000 + offset;
    rows.push({ _id: i, tenant: "tenant-" + (i % 10), externalId: "task-" + i,
      status: Math.floor(i / 10) % 2 === 0 ? "open" : "done",
      createdAt: new Date(base.getTime() + i * 1000), revision: NumberInt(1),
      checklist: [{ label: "receive", done: true }, { label: "review", done: false },
                  { label: "complete", done: false }] });
  }
  lab.tasks.insertMany(rows, { writeConcern: { w: "majority", wtimeout: 10000 } });
}
check(lab.tasks.countDocuments({}) === 10000, "Fixture count mismatch");
check(lab.tasks.countDocuments({ tenant: "tenant-3", status: "open" }) === 500,
      "Tenant/status distribution mismatch");
```

Expected: 10,000 tasks, 1,000 per tenant and 500 open cards for tenant-3. Fixture status is independent of tenant parity. A validator does not impose maximum total document size below MongoDB's own limit; production needs payload/embedding bounds appropriate to the service.

## 5. Project stage A — baseline query and correctness

Use a fixed upper creation-time boundary for the closed fixture. The fixed bound prevents a newly inserted card after that boundary from joining this pagination demonstration.

```javascript
var upper = new Date(base.getTime() + 10000 * 1000);
var queueFilter = { tenant: "tenant-3", status: "open", createdAt: { $lt: upper } };
var cardProjection = { _id: 1, tenant: 1, externalId: 1, status: 1,
                       createdAt: 1, revision: 1 };
var queueOrder = { createdAt: -1, _id: -1 };
function queue(tag) {
  return lab.tasks.find(queueFilter, cardProjection).sort(queueOrder).limit(5)
    .maxTimeMS(10000).comment(tag);
}
var expectedFirst = [9983, 9963, 9943, 9923, 9903];
function ids(rows) { return rows.map(row => row._id); }
var baseline = queue("ch77-baseline").hint({ $natural: 1 }).toArray();
check(EJSON.stringify(ids(baseline)) === EJSON.stringify(expectedFirst), "Queue identity/order failed");
check(baseline.every(row => row.tenant === "tenant-3" && row.status === "open"),
      "Queue tenant/status boundary failed");
var baselineExplain = queue("ch77-baseline-explain").hint({ $natural: 1 }).explain("executionStats");
check(baselineExplain.executionStats.nReturned === 5, "Baseline explain count mismatch");
check(baselineExplain.executionStats.totalDocsExamined >= 10000, "Expected forced scan work");
printjson(baselineExplain);
```

The forced scan is a known inefficient reference, not a claim about the production planner. Capture examined keys/documents, sort behavior and actual completed plan. Explain bypasses the plan cache; it does not prove ordinary cached requests chose that plan.[4]

## 6. Project stage B — tuned queue and read contract

```javascript
lab.tasks.createIndex({ tenant: 1, status: 1, createdAt: -1, _id: -1 }, {
  name: "tenant_status_created_id"
});
var tuned = queue("ch77-tuned").hint("tenant_status_created_id").toArray();
check(EJSON.stringify(tuned) === EJSON.stringify(baseline), "Tuning changed projected results");
var tunedExplain = queue("ch77-tuned-explain").hint("tenant_status_created_id")
  .explain("executionStats");
check(tunedExplain.executionStats.nReturned === 5, "Tuned explain count mismatch");
check(tunedExplain.executionStats.totalDocsExamined <
      baselineExplain.executionStats.totalDocsExamined, "Document work did not reduce");
check(tunedExplain.executionStats.totalKeysExamined > 0, "Expected indexed key work");
printjson(tunedExplain);
var ordinary = queue("ch77-ordinary").toArray();
check(EJSON.stringify(ordinary) === EJSON.stringify(baseline), "Unhinted correctness changed");
printjson(queue("ch77-ordinary-explain").explain("executionStats"));
```

Expected: identical latest five cards and lower document work for the hinted indexed candidate. Inspect unhinted behavior independently. The projection includes externalId/revision outside the queue index; this project does not claim a covered query.

A five-row query returning correct data quickly on a small warm fixture is not production latency acceptance. Test representative tenant sizes, open/done skew, projection/checklist payload, cold/warm behavior, writes and concurrency before rollout.

## 7. Project stage C — stable seek pagination

For descending `(createdAt, _id)`, continue strictly after the final key using a tenant/status-preserving OR predicate. Carry the fixed upper bound and filter contract into subsequent requests.

```javascript
var last = tuned[tuned.length - 1];
var nextFilter = { $and: [queueFilter, { $or: [
  { createdAt: { $lt: last.createdAt } },
  { createdAt: last.createdAt, _id: { $lt: last._id } }
] }] };
var second = lab.tasks.find(nextFilter, cardProjection).sort(queueOrder).limit(5)
  .maxTimeMS(10000).comment("ch77-page-two").toArray();
check(EJSON.stringify(ids(second)) === EJSON.stringify([9883, 9863, 9843, 9823, 9803]),
      "Second page identity/order mismatch");
check(new Set(ids(tuned).concat(ids(second))).size === 10, "Pagination repeated identities");
check(second.every(row => row.tenant === "tenant-3" && row.status === "open"),
      "Pagination scope changed");
```

Expected: no overlap and exact next five IDs. This is a closed fixture, not a snapshot guarantee for a changing queue. Concurrent status/time updates can change membership or ordering; define whether users accept live pagination or require a snapshot/export protocol.

Production cursors should bind tenant, filter/schema version, order, upper boundary and typed last key, with integrity/expiry controls from Chapter 15. Reject a cursor reused under a different tenant/filter. Do not expose an untrusted raw query document as the pagination API.

## 8. Project stage D — schema and uniqueness failures

Trigger invalid timestamp and duplicate business identity writes. Inspect the exact error and prove failed writes did not change the accepted data.

```javascript
var beforeCount = lab.tasks.countDocuments({});
var invalidRejected = false;
try {
  lab.tasks.insertOne({ _id: 20000, tenant: "tenant-3", externalId: "invalid-date",
    status: "open", createdAt: base.toISOString(), revision: NumberInt(1), checklist: [] });
} catch (error) {
  if (error.code !== 121) throw error;
  invalidRejected = true;
}
var duplicateRejected = false;
try {
  lab.tasks.insertOne({ _id: 20001, tenant: "tenant-3", externalId: "task-3",
    status: "open", createdAt: base, revision: NumberInt(1), checklist: [] });
} catch (error) {
  if (error.code !== 11000) throw error;
  duplicateRejected = true;
}
check(invalidRejected && duplicateRejected, "Negative constraint tests failed");
check(lab.tasks.countDocuments({}) === beforeCount, "Failed writes changed fixture count");
```

Expected: validation code 121 and uniqueness code 11000; count remains 10,000. In production an existing schema migration must identify/quarantine old invalid data before strict enforcement. Do not bypass validation to hide producer defects.

## 9. Project stage E — guarded status transition and stale update

Use tenant/business identity, current state and revision as the update predicate. No separate history record is written in this exercise.

```javascript
var change = lab.tasks.updateOne({ tenant: "tenant-3", externalId: "task-3",
  status: "open", revision: NumberInt(1) }, {
  $set: { status: "done" }, $inc: { revision: NumberInt(1) }
}, { writeConcern: { w: "majority", wtimeout: 10000 } });
check(change.modifiedCount === 1, "Expected accepted status transition");
var stale = lab.tasks.updateOne({ tenant: "tenant-3", externalId: "task-3",
  status: "open", revision: NumberInt(1) }, {
  $set: { status: "done" }, $inc: { revision: NumberInt(1) }
});
check(stale.matchedCount === 0, "Stale revision unexpectedly accepted");
var state = lab.tasks.findOne({ tenant: "tenant-3", externalId: "task-3" });
check(state.status === "done" && Number(state.revision) === 2, "Transition state mismatch");
var restore = lab.tasks.updateOne({ tenant: "tenant-3", externalId: "task-3",
  status: "done", revision: NumberInt(2) }, {
  $set: { status: "open" }, $inc: { revision: NumberInt(1) }
}, { writeConcern: { w: "majority", wtimeout: 10000 } });
check(restore.modifiedCount === 1, "Owned state restoration failed");
var restored = lab.tasks.findOne({ tenant: "tenant-3", externalId: "task-3" });
check(restored.status === "open" && Number(restored.revision) === 3, "Restored state mismatch");
check(lab.tasks.countDocuments({ tenant: "tenant-3", status: "open" }) === 500,
      "Open queue count not restored");
```

Expected: one accepted transition, rejected stale match and a restored open task at revision 3. Restoring business state is a new transition; do not roll the revision backward to make the original fixture appear unchanged.

On ambiguous acknowledgement, reconcile identity/revision/state before retrying. A stale zero-match can mean a concurrent change or an already applied operation; it is not automatically a transport failure. Define application conflict/idempotency behavior explicitly.

## 10. Offline project contract checker

Save as `ch77_contract.py`. It verifies declared fixture distribution, closed-scope pagination and a simplified compare-and-set boundary without a database connection.

```python
rows = [{"id": i, "tenant": "tenant-" + str(i % 10),
         "status": "open" if (i // 10) % 2 == 0 else "done", "time": i}
        for i in range(10000)]
queue = sorted((r for r in rows if r["tenant"] == "tenant-3" and r["status"] == "open"),
               key=lambda r: (r["time"], r["id"]), reverse=True)
assert len(queue) == 500
first, second = queue[:5], queue[5:10]
assert [r["id"] for r in first] == [9983, 9963, 9943, 9923, 9903]
assert [r["id"] for r in second] == [9883, 9863, 9843, 9823, 9803]
assert len({r["id"] for r in first + second}) == 10
last = first[-1]
seek = [r for r in queue if (r["time"], r["id"]) < (last["time"], last["id"])][:5]
assert seek == second
state = {"status": "open", "revision": 1}
def transition(expected_revision, expected_status, new_status):
    if state["revision"] != expected_revision or state["status"] != expected_status:
        return False
    state.update(status=new_status, revision=state["revision"] + 1)
    return True
assert transition(1, "open", "done")
assert not transition(1, "open", "done")
assert transition(2, "done", "open") and state["revision"] == 3
print("PASS: distribution, seek ordering and guarded transition model")
```

The offline model does not establish BSON serialization, server atomicity or concurrent transaction behavior. Those remain live acceptance items.

## 11. Production workload and migration acceptance

Capture a weighted query/write inventory, representative tenant skew and growth. Test required latency/error objectives with controlled concurrency and actual client pool/deadline settings. Include writes and index build/storage cost, member-failure load and recovery headroom.

For an existing application, version the schema and cursor/API contracts. Use the Chapter 68 migration method and closed-scope reconciliation; do not assume creating a new validator/index migrates old data. Define how old/new writers coexist and how rejected records are repaired.

If maintaining separate task history or derived queue summaries, prove transaction/outbox/CDC semantics and repair behavior before claiming consistency. For warehouse integration, use Chapter 67's direct MongoDB-to-Snowflake path and its checkpoint/reconciliation contract.

| Acceptance area | Required evidence |
|---|---|
| Correctness/security | Tenant/status filters, exact IDs/order, data types and caller access |
| Performance | Real client latency/errors, workload mix and completed query work |
| Writes | Guarded updates, ambiguity/retry behavior and index overhead |
| Capacity | Member/storage/cache reserve and forecast under peak/failure load |
| Recovery | Backup/restore, failover and required history alignment |
| Rollout | Versioned schema/cursors, migration reconciliation and reversal/recovery |

Do not accept only a hinted microbenchmark. Test ordinary executions and preserve actual log/profiler/trace context from Chapters 22, 69 and 73. A lower examined-documents count is useful evidence but not the entire service acceptance.

## 12. Troubleshooting and corrective actions

| Symptom | Evidence | Cause to test | Corrective action and verification |
|---|---|---|---|
| Correct queue count, wrong cards | Tenant/status filters and ordered IDs | Scope/order regression | Restore exact contract; compare projected results |
| Indexed query still scans broadly | Bounds, key/document work and skew | Unsuitable key order or selectivity | Test weighted workload alternatives with equivalence |
| Page repeats/misses records | Typed cursor/order and concurrent changes | Unstable order or undefined live-page semantics | Bind cursor contract and choose snapshot/live policy |
| Schema rejects producer | Original typed payload and code 121 | String Date/revision or oversized checklist | Correct producer/migrate data; verify accepted types |
| Duplicate business identity | Unique index and scope | Writer retries or missing identity owner | Reconcile stable identity; retain required uniqueness |
| Stale update returns zero | Current revision/state and request identity | Concurrent/already applied transition | Apply explicit conflict/idempotency response |
| Audit history diverges | Task/event publication boundary | Separate writes without atomic capture | Adopt proven transaction/outbox or repair contract |
| Read tuning hurts writes | Index size/build/write latency | Added maintenance/cache cost | Review net workload acceptance and rollback |
| Small lab fast, production slow | Tenant sizes, payload, concurrency and resources | Unrepresentative fixture/cache | Repeat representative acceptance before rollout |

## 13. Project evidence and cleanup

| Stage | Expected result |
|---|---|
| Schema/fixture | 10,000 tasks; tenant-3 has 500 open cards; validator/unique index recorded |
| Baseline/tuning | Exact latest five IDs; identical projected results; lower candidate document work |
| Seek page | Exact next five IDs, no overlap and retained tenant/status scope |
| Failure drills | Codes 121/11000; unchanged count |
| State transition | Revision 1→2, stale match rejected, restored open at revision 3 |
| Offline checks | Fixture/page/state model passed |
| Production packet | Representative workload, capacity/security/recovery and migration evidence |

Save nonsecret plans/index/options and result identities. Verify restored business state before owned cleanup through the lifecycle identity:

```javascript
var labName = "mongodb_enterprise_ch77_modeling";
var lab = db.getSiblingDB(labName);
check(lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch77" }) !== null,
      "Ownership missing");
var restored = lab.tasks.findOne({ tenant: "tenant-3", externalId: "task-3" });
check(restored && restored.status === "open" && Number(restored.revision) === 3,
      "Finish transition restoration before cleanup");
check(lab.tasks.countDocuments({}) === 10000, "Fixture count requires reconciliation");
check(lab.dropDatabase().ok === 1, "Owned cleanup failed");
check(db.getSiblingDB(labName).getCollectionInfos().length === 0, "Collections remain");
print("PASS: chapter-owned modeling project removed");
```

If interrupted, inspect the owned namespace/revision before resuming a stage. Reestablish helper variables after reconnecting without recreating populated fixtures. Retain the cluster, other chapter resources and local project evidence under their existing lifecycle.

Review questions:

1. Why is bounded checklist embedding different from unbounded history embedding?
2. Why do tenant indexes not replace application authorization?
3. What does result equivalence add to an index experiment?
4. Why is a seek page not automatically a snapshot of a changing queue?
5. Why should restoring task status increase rather than decrease revision?
6. What is missing from independently writing a task and its history event?
7. What production evidence is absent from this small bounded fixture?
8. How would a schema/cursor change be rolled out and reconciled?

## 14. DBRE/SRE extension — workload-driven performance acceptance and safe rollout

This extension turns the synthetic project into an auditable production-readiness exercise. It does not authorize applying schema migrations or index changes to a production namespace without application/data-owner approval.

### 14.1 Representative workload and data contracts

Define a **versioned workload profile** before benchmarking: tenant cardinality and skew, document size distribution, checklist size, event-history growth, status selectivity, arrival rate, concurrent writers/readers, batch peaks, pagination depth and expected failure-mode load. Preserve BSON types, sort/collation, read/write concerns and client retry policies.

| Contract | Required proof | Failure mode |
|---|---|---|
| Tenant isolation | Cross-tenant access tests at API authorization boundary and tenant-filtered DB query | An index alone is not access control |
| Unique business identity | Duplicate insertion rejected by exact unique index, including expected collation/partial scope | Duplicate task identifiers |
| Schema evolution | Old and new clients accepted/rejected as intended under staged validator rollout | Existing documents or clients unexpectedly rejected |
| Stable pagination | Deterministic sort with unique tie-breaker, typed seek cursor and bounded page size | Missing/duplicated rows under ties or mutable ordering |
| Concurrent transitions | Stale revision rejected; exactly one accepted compare-and-set result | Lost update or duplicated side effect |
| History consistency | Explicit transactional/outbox/capture contract and failure reconciliation | Task state and audit history diverge |
| Query tuning | Equivalent result identities and order; examined work and tail latency measured | Fast incorrect result or regressions in rare query shapes |

A seek cursor is not automatically a consistent snapshot when the queue changes between pages. Document that limitation or choose an explicitly accepted snapshot/reconciliation strategy.

### 14.2 Benchmark and acceptance design

1. Capture a **pre-change** baseline with application P50/P95/P99 latency, throughput, timeout/error rate, pool checkout, query shape, keys/docs examined, memory/cache, disk latency/IOPS and replication history.
2. Use representative **sanitized/synthetic** data at realistic cardinality and skew; never copy sensitive production records into a public tutorial.
3. Benchmark at steady state, peak, write-heavy bursts, and **one-member-down** recovery load, with the same driver settings and read/write concerns.
4. Separate warm-cache and cold-cache observations, index build overhead and background ingestion. Repeat trials and record sample size and measurement window.
5. Compare the baseline and candidate **result sets, ordering and business invariants** before interpreting latency changes.
6. Set explicit service-specific acceptance thresholds, rollback triggers and resource budgets before running the candidate. Avoid universal performance numbers.
7. Validate schema/index changes through a staged application rollout; preserve compatibility for mixed client versions and record the recovery path.
8. Observe actual post-change service metrics over a representative cycle, not only a single `explain` result.

### 14.3 Safe schema and index rollout

Use a **prepare → dual-compatible → migrate → enforce → retire** lifecycle. First deploy clients that tolerate old/new fields and cursor versions, then backfill bounded batches with resumable checkpoints and reconciliation. Only tighten schema validation when existing documents and every supported writer satisfy the new contract.

For index changes, inventory exact existing specifications and apply Chapter 71's owner approval. A hidden index remains maintained; hiding does not model storage/write-cost savings. Index removal is a separate, potentially expensive change. Verify memory, disk and replication headroom before builds and migrations.

Never use an unbounded `updateMany`, `dropIndex` or validation-mode change as an automatic response to a slow-query alert. Reconcile interrupted writes and checkpoints before retries.

### 14.4 Production acceptance manifest

Save as `ch77-performance-acceptance.json`:

```json
{
  "chapter": 77,
  "change_id": "NOT_ASSIGNED",
  "application_owner": "NOT_ASSIGNED",
  "dbre_reviewer": "NOT_ASSIGNED",
  "workload_profile": "NOT_RECORDED",
  "tenant_isolation_verified": false,
  "schema_and_uniqueness_verified": false,
  "pagination_and_concurrency_verified": false,
  "history_consistency_contract_verified": false,
  "query_result_equivalence_verified": false,
  "peak_and_failure_mode_benchmark_passed": false,
  "slo_and_resource_budgets_passed": false,
  "rollback_and_mixed_version_plan_reviewed": false,
  "post_rollout_observation_passed": false,
  "evidence_references": []
}
```

Save as `ch77_performance_gate.py`:

```python
import json
from pathlib import Path

p = json.loads(Path("ch77-performance-acceptance.json").read_text(encoding="utf-8"))
checks = (
    "tenant_isolation_verified", "schema_and_uniqueness_verified",
    "pagination_and_concurrency_verified",
    "history_consistency_contract_verified",
    "query_result_equivalence_verified",
    "peak_and_failure_mode_benchmark_passed",
    "slo_and_resource_budgets_passed",
    "rollback_and_mixed_version_plan_reviewed",
    "post_rollout_observation_passed",
)
missing = [key for key in checks if p.get(key) is not True]
for key in ("change_id", "application_owner", "dbre_reviewer", "workload_profile"):
    if not isinstance(p.get(key), str) or not p[key].strip() or p[key].startswith("NOT_"):
        missing.append(key)
if not isinstance(p.get("evidence_references"), list) or not p["evidence_references"]:
    missing.append("evidence_references")
if missing:
    raise SystemExit("NOT ACCEPTED: " + ", ".join(missing))
print("PASS: declared acceptance fields complete; independent evidence review required")
```

Run `python ch77_performance_gate.py`. The untouched template must fail. A PASS confirms **declarations only**; it does not establish real throughput, correctness, security or failover readiness without reviewed artifacts.

### 14.5 Incident rollback and sign-off

Stop the rollout on cross-tenant exposure, incorrect results, lost-update anomalies, unexpected schema rejection, query latency/error regression, storage pressure, replica lag or missing monitoring. Restore the last approved application/query version and compatible index/validator state where supported. **Backfilled or deleted data may require reconciliation/restore**, not a simple settings reversal.

The acceptance packet must include service-owner and DBRE sign-off, exact tested versions, pre/post workload data, failure cases, rollback proof, known limitations, and follow-up ownership. Record unexecuted live tests as **NOT RUN**, not passed.

---

## 15. Official references and validation status

1. [MongoDB 8.0 — Data Modeling](https://www.mongodb.com/docs/v8.0/data-modeling/).
2. [MongoDB 8.0 — Schema Validation](https://www.mongodb.com/docs/v8.0/core/schema-validation/).
3. [MongoDB 8.0 — ESR Guideline](https://www.mongodb.com/docs/v8.0/tutorial/equality-sort-range-rule/).
4. [MongoDB 8.0 — Explain Results](https://www.mongodb.com/docs/v8.0/reference/explain-results/).

Documentation reviewed on 2026-10-12. The work-queue contract, fixture, index/page assertions and guarded transition are teaching designs. JavaScript/Python syntax and actual offline fixture/pagination/transition assertions were checked. These checks do not validate live MongoDB schema enforcement, uniqueness, query work, BSON updates, concurrent clients or production performance. No live modeling project was executed in the authoring environment.

**Chapter completion:** Written and statically reviewed; offline project-contract acceptance complete. Runtime validation remains pending until authorized schema/query/pagination/failure/transition drills and owned cleanup are executed with evidence.

Previous: [Chapter 76 — Replication Elections and Sharding Troubleshooting](76-replication-elections-and-sharding-troubleshooting.md).  
Next: Chapter 78 — HA Failover and Application Resilience Project.
