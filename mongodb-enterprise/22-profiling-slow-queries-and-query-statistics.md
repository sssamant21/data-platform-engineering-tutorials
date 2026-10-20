# 22 — Profiling Slow Queries and Query Statistics

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Capture narrowly tagged real query operations, compare their examined work before/after an index, restore diagnostic configuration, and distinguish profiler evidence from query-shape statistics.  
**Audience:** DBREs, SREs, Developers and Data Engineers  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Core lab on a self-managed Community or Enterprise training mongod, standalone or replica-set primary, with unsharded data. Optional query-statistics branch requires an eligible Atlas deployment.

## 1. Observe requests that actually ran

Chapter 21 used explain to investigate possible execution paths. The profiler records selected operations that actually execute. Diagnostic logs provide another operation-level source. Query statistics aggregate observations by normalized shape rather than storing a chronological list of all requests.

| Source | Best question | Practical limit |
|---|---|---|
| Explain | How does this query execute in a controlled run? | Does not establish the cached plan used by a past request |
| Database profiler | What work did selected actual operations perform? | Collection retention, capture selection and overhead limit completeness |
| Diagnostic slow-operation log | Which logged operations crossed the configured selection? | Sampling, logging configuration, rotation and member scope matter |
| Query statistics | Which recorded shapes consume aggregate work? | Availability, sampling, memory retention and output compatibility matter |
| Application tracing | Where did end-to-end time go? | Needs correlation with server-side evidence |

A request can be slow because of broad scanning, sorting, storage reads, concurrency, pool waits or network/result consumption. One source rarely proves the entire cause.

The lab uses explicit comments to correlate a known pair of synthetic operations. It does not manufacture a multi-second query or lower the global slow threshold merely to obtain records.

## 2. Configuration scope matters

Profiler levels are:

- 0: profiler off.
- 1: selected operations, using a threshold or configured filter.
- 2: all operations; unsuitable for this bounded capture exercise.

When set through the profile command or shell helper, the profiling level and filter are database-scoped. slowms and sampleRate are process-wide settings. Changing them from one database can affect diagnostic behavior for others on that mongod.

A configured filter replaces threshold/sample selection for profiler and slow-query log lines. Setting level zero stops profile collection writes but does not remove the filter's diagnostic-log effect. Restoration must therefore restore the filter as well as the level.

MongoDB 8.0 distinguishes operation duration from workingMillis for slow-operation selection. Inspect available fields and the exact version documentation; do not assume the configured slow threshold represents all client-visible waiting.

This lab changes only the chapter database's level/filter and leaves global slowms/sampleRate untouched. The filter can also affect diagnostic logging for that database during the short window.

## 3. Prerequisites, permissions and deployment boundaries

Use the approved training URI from Chapter 06. Connect to a self-managed mongod, not mongos. The database profiler cannot be enabled on mongos; router slow logs and relevant shard/member observations are separate.

The operator needs:

- Collection creation/read/write/index/cleanup privileges on the chapter database.
- enableProfiler access for this database.
- Permission to read this database's system.profile collection.
- Existing authorized log access only for the optional diagnostic-log correlation.

Verify custom roles explicitly; ordinary application permissions may not include profiling. No role grants, process parameters or production logging changes are part of this lab.

Atlas command support depends on tier and service restrictions. Use a supported dedicated training deployment for any Atlas branch; M0/Flex restrictions are not repaired by retrying the same unsupported command.

In mongosh:

```javascript
const labName22 = "mongodb_enterprise_tutorial_ch22";
const lab22 = db.getSiblingDB(labName22);
const hello22 = db.adminCommand({ hello: 1 });
printjson({
  serverVersion: db.version(),
  database: labName22,
  replicaSet: hello22.setName || null,
  mongos: hello22.msg === "isdbgrid",
  writablePrimary: hello22.isWritablePrimary
});
if (hello22.msg === "isdbgrid") {
  throw new Error("Core lab requires mongod; profiling is unavailable on mongos");
}
if (!hello22.isWritablePrimary) {
  throw new Error("Use a writable training server or replica-set primary");
}
if (lab22.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
function check22(condition, message) {
  if (!condition) throw new Error(message);
}
```

Record mongosh --version separately. Replica-set profile records are local diagnostic evidence, not a replicated cluster-wide ledger. Capture member identity and connection context when comparing observations.

## 4. Build the fixture before enabling capture

Six tenants each have 2,000 requests. Every fourth sequence is OPEN. The recent interval starts at sequence 1800.

```javascript
lab22.createCollection("requests");
const requests22 = lab22.requests;
let batch22 = [];
for (let tenant = 0; tenant < 6; tenant++) {
  for (let seq = 0; seq < 2000; seq++) {
    batch22.push({
      _id: tenant * 2000 + seq,
      tenantId: "t" + tenant,
      status: seq % 4 === 0 ? "OPEN" : "CLOSED",
      seq,
      payload: "Synthetic request " + tenant + "/" + seq
    });
    if (batch22.length === 1000) {
      requests22.insertMany(batch22);
      batch22 = [];
    }
  }
}
check22(requests22.countDocuments({}) === 12000, "Wrong fixture total");
check22(requests22.countDocuments({
  tenantId: "t3", status: "OPEN", seq: { $gte: 1800 }
}) === 50, "Wrong fixture interval count");
const filter22 = {
  tenantId: "t3", status: "OPEN", seq: { $gte: 1800 }
};
const expectedSeq22 = Array.from({ length: 20 }, (_, i) => 1996 - i * 4);
function verify22(rows) {
  check22(JSON.stringify(rows.map(r => Number(r.seq))) ===
          JSON.stringify(expectedSeq22), "Wrong response sequence");
  check22(rows.every(r => r.tenantId === "t3" && r.status === "OPEN" &&
    Number(r.seq) >= 1800), "Response scope changed");
}
function request22(comment, hint) {
  return requests22.find(filter22)
    .sort({ seq: -1 }).limit(20).batchSize(100)
    .comment(comment).hint(hint).toArray();
}
```

The twenty small records fit the requested initial batch. This keeps the main comparison on the initial find rather than distributing it over getMore operations. Larger responses or smaller batches need cursor-aware analysis.

## 5. Capture original configuration and a recovery command

Read the chapter database's profiling status before changing it:

```javascript
const originalProfile22 = lab22.getProfilingStatus();
printjson(originalProfile22);
check22(Number(originalProfile22.was) === 0,
        "Expected profiling off on new disposable database; investigate existing policy");
check22(!Object.hasOwn(originalProfile22, "filter"),
        "Existing profiler filter requires a separate reviewed capture plan");
const restoreOptions22 = {
  filter: Object.hasOwn(originalProfile22, "filter")
    ? originalProfile22.filter : "unset"
};
print("Recovery command for this capture:");
print("db.getSiblingDB(" + JSON.stringify(labName22) +
      ").setProfilingLevel(" + Number(originalProfile22.was) + ", " +
      EJSON.stringify(restoreOptions22) + ")");
```

Save the printed original status and recovery command before starting capture. This lab requires an initially unconfigured disposable database. Do not overwrite an inherited diagnostic policy and then assume an empty restoration is adequate.

The saved slowms/sampleRate values are evidence. The restoration command does not reset them because this lab does not change them and should not overwrite another operator's concurrent process-wide change.

## 6. Run a filtered capture with guaranteed normal-path restoration

Use a unique run ID and two exact comments. The filter requires the chapter namespace and those comments; it does not select every slow query or every command.

```javascript
const runId22 = "ch22-" + new ObjectId().toHexString();
const baselineComment22 = runId22 + "-baseline";
const indexedComment22 = runId22 + "-indexed";
const captureFilter22 = {
  ns: labName22 + ".requests",
  "command.comment": { $in: [baselineComment22, indexedComment22] }
};
const captureStart22 = new Date();
let captureFailure22 = null;
try {
  const enabled22 = lab22.setProfilingLevel(1, { filter: captureFilter22 });
  check22(enabled22.ok === 1, "Filtered profiling was not enabled");
  const current22 = lab22.getProfilingStatus();
  check22(Number(current22.was) === 1, "Wrong capture level");

  verify22(request22(baselineComment22, { $natural: 1 }));
  requests22.createIndex(
    { tenantId: 1, status: 1, seq: -1 },
    { name: "tenant_status_seq" }
  );
  verify22(request22(indexedComment22, "tenant_status_seq"));
} catch (error) {
  captureFailure22 = error;
  print("Capture failed: " + error.message);
} finally {
  const restored22 = lab22.setProfilingLevel(
    Number(originalProfile22.was), restoreOptions22
  );
  check22(restored22.ok === 1, "Profiler restoration failed; use recovery command");
}
const afterProfile22 = lab22.getProfilingStatus();
check22(Number(afterProfile22.was) === Number(originalProfile22.was),
        "Profiling level not restored");
check22(!Object.hasOwn(afterProfile22, "filter"),
        "Lab filter remains active; use recovery command");
printjson({ runId: runId22, restoredStatus: afterProfile22 });
if (captureFailure22) throw captureFailure22;
```

The filter captures matching operations even if they are fast. These are **selected operation records**, not proof that both queries crossed a slow threshold.

The finally block handles ordinary exceptions in the active shell. It cannot run if the client is killed or disconnected before execution reaches it. Reconnect to the same server/database and use the saved recovery command in that case.

The index build and unrelated fixture/metadata work are not targeted by the exact comment filter. Keep the capture window short regardless; filtering is not zero-cost.

## 7. Read narrow operation evidence after restoration

```javascript
const profileRows22 = lab22.getCollection("system.profile").find({
  ts: { $gte: captureStart22 },
  ns: labName22 + ".requests",
  "command.comment": { $in: [baselineComment22, indexedComment22] }
}).sort({ ts: 1 }).toArray();
check22(profileRows22.length >= 2, "Missing tagged profile evidence");
const baselineRecords22 = profileRows22.filter(
  r => r.command && r.command.comment === baselineComment22
);
const indexedRecords22 = profileRows22.filter(
  r => r.command && r.command.comment === indexedComment22
);
check22(baselineRecords22.length > 0 && indexedRecords22.length > 0,
        "One comparison operation was not captured");
function largestScan22(rows) {
  return rows.reduce((best, row) =>
    Number(row.docsExamined || 0) > Number(best.docsExamined || 0)
      ? row : best);
}
const baselineRecord22 = largestScan22(baselineRecords22);
const indexedRecord22 = largestScan22(indexedRecords22);
function summary22(record) {
  return {
    timestamp: record.ts,
    operation: record.op,
    comment: record.command && record.command.comment,
    planSummary: record.planSummary,
    returned: record.nreturned,
    keysExamined: record.keysExamined,
    docsExamined: record.docsExamined,
    millis: record.millis,
    workingMillis: record.workingMillis,
    hasSortStage: record.hasSortStage,
    responseLength: record.responseLength,
    shapeHash: record.planCacheShapeHash || record.queryHash || null,
    planCacheKey: record.planCacheKey || null
  };
}
printjson({
  baseline: summary22(baselineRecord22),
  indexed: summary22(indexedRecord22)
});
check22(Number(baselineRecord22.docsExamined) === 12000,
        "Expected baseline full scan");
check22(Number(indexedRecord22.docsExamined) === 20,
        "Expected indexed page fetch");
check22(Number(baselineRecord22.nreturned) === 20 &&
        Number(indexedRecord22.nreturned) === 20,
        "Profile record response counts differ");
check22(Number(indexedRecord22.docsExamined) <
        Number(baselineRecord22.docsExamined), "No examined-work improvement");
```

Expected structural change: 12,000 examined documents become twenty while the response remains identical. The compound index still fetches payload, so this is not a covered response.

Field availability differs by operation, version and execution engine. A missing workingMillis, hasSortStage or hash field should be recorded as unavailable, not silently converted into proof of zero work. Preserve full synthetic records locally for diagnosis, while sharing only sanitized summaries.

## 8. Failure exercise: wrong comment yields no evidence

Reproduce a correlation typo against the already captured records:

```javascript
const wrongComment22 = indexedComment22 + "-typo";
const wrongMatchCount22 = lab22.getCollection("system.profile").countDocuments({
  ts: { $gte: captureStart22 },
  "command.comment": wrongComment22
});
check22(wrongMatchCount22 === 0, "Unexpected typo-comment record");
const correctedMatchCount22 = lab22.getCollection("system.profile").countDocuments({
  ts: { $gte: captureStart22 },
  "command.comment": indexedComment22
});
check22(correctedMatchCount22 > 0, "Corrected correlation still empty");
```

Diagnosis: the evidence query asked for a comment never used. The absence does not prove the request never ran or that the profiler is broken. Correct the identifier and verify a matching record.

For actual capture gaps, inspect the server/member, namespace, time window, filter, permissions, cursor completion and capped collection rollover. Do not respond by turning on level 2 globally.

## 9. Aggregate selected records without calling them an SLO

```javascript
const grouped22 = lab22.getCollection("system.profile").aggregate([
  { $match: {
    ts: { $gte: captureStart22 },
    ns: labName22 + ".requests",
    "command.comment": { $in: [baselineComment22, indexedComment22] }
  } },
  { $group: {
    _id: "$command.comment",
    capturedOperations: { $sum: 1 },
    totalMillis: { $sum: "$millis" },
    totalDocsExamined: { $sum: "$docsExamined" },
    totalKeysExamined: { $sum: "$keysExamined" },
    totalReturned: { $sum: "$nreturned" }
  } },
  { $sort: { _id: 1 } }
]).toArray();
check22(grouped22.length === 2, "Expected two comment groups");
printjson(grouped22);
```

These totals describe selected operations captured in this window. They are not a complete traffic inventory or statistically meaningful P95. Capturing only slow operations biases latency distributions; averaging captured slow requests cannot describe all requests.

Averages also hide hot-tenant and parameter skew. Pair normalized shape grouping with representative parameter classes and complete application metrics.

## 10. Slow-log correlation and cursor boundaries

If you have existing log access on the same training mongod, search its diagnostic log for the exact runId22 and namespace. Profiler filters also affect diagnostic selection. Preserve the configured level/filter and log component context when interpreting what appears.

Do not assume every profiler record has an identical diagnostic line, or that every log file covers the same member/time range. Structured log field names differ from profile document names.

For larger responses, inspect initial find and getMore records, cursor IDs, originatingCommand and inherited comments where available. Cursor batches are operation records, not independent business requests. Summing their returned rows can describe response work only after deduplicating/correlating the cursor lifecycle correctly.

A slow getMore can reflect later result production or batch consumption. A single fast initial find does not establish a fast full query. Application tracing should record full cursor consumption, not just cursor construction.

## 11. Optional Atlas query-statistics branch

MongoDB 8.0 documentation describes $queryStats as enabled on Atlas deployments of at least M10, and labels its output unsupported/stability-sensitive. Do not promise the stage works on every self-managed Community/Enterprise server or build an immutable production parser around its current schema.

Run this read-only branch only on an independently authorized eligible Atlas training deployment with queryStatsRead privilege. Transformed identifier output additionally requires queryStatsReadTransformed. An existing appropriate monitoring role may provide them; this chapter does not grant roles.

The stage runs on admin and must be first. It is not a collection stage. For the untransformed synthetic namespace branch:

```javascript
// Optional: run only on an eligible authorized Atlas training connection.
const queryStatsDatabase22 = db.getSiblingDB("admin");
const statsEntries22 = queryStatsDatabase22.aggregate([
  { $queryStats: {} },
  { $match: {
    "key.queryShape.cmdNs.db": labName22,
    "key.queryShape.cmdNs.coll": "requests"
  } },
  { $limit: 10 },
  { $project: { _id: 0, key: 1, queryShapeHash: 1, metrics: 1 } }
]).toArray();
printjson(statsEntries22);
```

If you use a different Atlas training database for the optional branch, substitute its actual namespace. The core self-managed fixture does not automatically exist on Atlas. Run authorized representative queries there first, without copying real sensitive payloads into a teaching dataset.

Record enabled/available status, version, member/router, namespace, returned schema and collection window. Zero entries can reflect sampling, unsupported operations, completion timing, eviction or namespace mismatch; it is not proof of zero traffic.

Metrics such as execution counts and timing aggregates describe recorded shape entries. Keep microsecond/millisecond units explicit when interpreting output. Counts can change across snapshots; use a consistent key and check resets/eviction before calculating deltas.

Normalization can combine different literal parameters. Comments do not supply a stable per-request ledger in shape statistics. A high aggregate cost can represent a frequent modest query or a few costly queries; investigate both frequency and per-execution work.

Identifier transformation can reduce namespace/field-name exposure when sharing results, but requires a managed HMAC key and appropriate privileges. Do not hardcode a production transformation key in this tutorial. Query normalization is not a blanket permission to publish internal namespace or workload details.

Unsupported command, feature-disabled and authorization failures have different remedies. Record the precise error and the skipped branch. Do not enable internal query-statistics parameters to bypass the documented deployment boundary.

## 12. Troubleshooting

| Symptom | Evidence | Cause to check | Corrective action |
|---|---|---|---|
| No tagged profile record | Status/filter, server, namespace, time/comment | Capture/correlation mismatch or rollover | Correct the narrow evidence query and repeat a bounded capture |
| Profile command unauthorized | Command, database role | Missing enableProfiler/read access | Use an authorized diagnostic operator |
| Profiling unavailable on router | hello response | Connected to mongos | Use router logs and reviewed member-level evidence |
| Records are fast despite level 1 | Active filter | Filter, not slow threshold, selected them | Describe selected capture correctly |
| Other database log volume changes | Global slowms/sampleRate changes | Process-wide settings altered elsewhere | Review operator/configuration history |
| Level zero but log filter persists | getProfilingStatus filter | Filter was not unset/restored | Apply saved recovery command |
| docsExamined high but millis low | Dataset/cache context | Warm small fixture still scans broadly | Assess structural work and realistic load |
| Profiler averages differ from tracing | Selection and cursor boundaries | Biased sample or missing client waits | Compare consistent scopes and full requests |
| $queryStats fails or empty | Version/tier/privileges/error and namespace | Unsupported branch or no recorded entries | Record limit; use available profiler/log evidence |

system.profile is a capped diagnostic collection, not durable incident storage. Export sanitized evidence promptly if rollover would lose it. Do not assume profile data is a backup or audit trail.

## 13. Production capture runbook

1. Define the incident question, target namespace/member and observation window.
2. Read existing diagnostic settings and coordinate with the operator who owns them.
3. Select a bounded filter or reviewed threshold/sample strategy. Account for process-wide versus database-scoped settings.
4. Record the rollback command and storage/log exposure before enabling capture.
5. Correlate representative real requests using sanitized comments and application trace IDs; avoid sensitive values in comments.
6. Capture operation work, errors, response volume and relevant server metrics, then restore settings promptly.
7. Group by shape/parameter class and identify scan, sort, fetch, waiting or result-volume hypotheses.
8. Test a correctness-preserving improvement using Chapter 21, then validate actual traffic.
9. Retain sanitized evidence with defined access/retention and document sampling gaps.

Comments may appear in server diagnostics. Use a nonsensitive correlation ID, not a patient identifier, token or password. Restrict raw diagnostic access because commands can contain literal values.

Profiler overhead adds work to the system being measured. Start narrow and watch foreground latency and diagnostic storage. Do not turn on exhaustive capture indefinitely.

## 14. Cleanup and verified restoration

The normal capture already restored the level/filter. Verify again before dropping the lab database:

```javascript
const finalProfile22 = lab22.getProfilingStatus();
check22(Number(finalProfile22.was) === Number(originalProfile22.was),
        "Profiler level still differs");
check22(!Object.hasOwn(finalProfile22, "filter"),
        "Capture filter remains; restore before cleanup");
check22(requests22.countDocuments({}) === 12000, "Fixture changed");
verify22(request22(runId22 + "-cleanup", "tenant_status_seq"));
if (lab22.getName() !== "mongodb_enterprise_tutorial_ch22") {
  throw new Error("Refusing cleanup outside the Chapter 22 training database");
}
const dropResult22 = lab22.dropDatabase();
check22(dropResult22.ok === 1, "Database cleanup command failed");
check22(lab22.getCollectionNames().length === 0, "Cleanup incomplete");
```

If capture ended abruptly, run the saved recovery command first and verify status. Dropping data is not a substitute for configuration restoration. The optional read-only query-statistics branch requires no setting rollback and makes no promise to erase in-memory aggregate observations.

## 15. Acceptance and evidence

- [ ] Recorded versions, mongod/member context and diagnostic privileges.
- [ ] Verified 12,000 requests and the exact twenty-row response.
- [ ] Saved original profiling status and a reconnect recovery command.
- [ ] Captured only the two tagged request operations through a narrow filter.
- [ ] Verified baseline/indexed results and examined-work reduction.
- [ ] Restored level and filter without changing global thresholds/sample rate.
- [ ] Diagnosed a correlation typo without widening capture.
- [ ] Distinguished selected records from slow-threshold/SLO evidence.
- [ ] Recorded optional query-statistics eligibility and actual branch outcome.
- [ ] Saved sanitized evidence and completed scoped cleanup.

**Evidence:** versions/member, original/restored status, run ID, filter/recovery command, result sequences, sanitized operation summaries, expected scan counters, typo/correction counts, optional statistics schema/outcome and cleanup. Runtime validation remains pending until the lab executes successfully.

## 16. Review questions

1. Why can this level-1 lab capture a very fast query?
2. Which settings are database-scoped and which affect the whole process?
3. Why is disabling profiling alone insufficient restoration after setting a filter?
4. Why are profile records not a complete request history?
5. How can getMore records change interpretation of one business request?
6. Why does a mean of captured slow operations not represent overall latency?
7. What limits the optional $queryStats branch on MongoDB 8.0?
8. Which client-visible waits require application evidence beyond profiler work?

## 17. Official references

- [MongoDB 8.0: database profiler and configuration scope](https://www.mongodb.com/docs/v8.0/tutorial/manage-the-database-profiler/)
- [MongoDB 8.0: setProfilingLevel and filter restoration](https://www.mongodb.com/docs/v8.0/reference/method/db.setProfilingLevel/)
- [MongoDB 8.0: database profiler output fields](https://www.mongodb.com/docs/v8.0/reference/database-profiler/)
- [MongoDB 8.0: $queryStats requirements and output limitations](https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/queryStats/)
- [MongoDB 8.0: find command and comments](https://www.mongodb.com/docs/v8.0/reference/command/find/)

---

Previous: [Chapter 21 — Explain Plans and Query Optimization](21-explain-plans-and-query-optimization.md)  
Next: [Chapter 23 — WiredTiger Cache Eviction and Checkpoints](23-wiredtiger-cache-eviction-and-checkpoints.md).
