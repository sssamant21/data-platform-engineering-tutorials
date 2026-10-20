# 19 — Multikey Partial Sparse and Unique Indexes

**Status:** Written; static review complete; runtime lab validation pending  
**Part:** 3 — Indexes and Performance  
**Goal:** Verify array indexing, distinguish missing from null, measure partial-index eligibility and enforce scoped uniqueness with reproducible failures.  
**Audience:** Developers, Data Engineers, DBREs and SREs  
**Time:** 90–120 minutes  
**Baseline:** MongoDB 8.0 and mongosh; record exact versions.  
**Deployment:** Community-compatible or Enterprise training server; standalone or replica-set primary. All collections in this lab are unsharded.

## 1. Index properties change semantics

Chapters 17–18 compared access paths for ordinary scalar indexes. This chapter introduces properties that affect which documents enter an index and which writes MongoDB accepts.

| Property | Meaning | Common mistaken assumption |
|---|---|---|
| Multikey | MongoDB indexes values from arrays automatically | An index proves two predicates matched the same array element |
| Partial | Only documents satisfying a filter enter the index | The index can answer every query on its key fields |
| Sparse | Documents missing the indexed field are omitted | Explicit null is omitted too |
| Unique | Duplicate indexed keys across documents are rejected | A unique array index removes duplicates inside an array |

These properties are not interchangeable. An index can be both partial and unique. A sparse index can be unique. Multikey behavior follows the data rather than an option named multikey.

Do not combine sparse and partialFilterExpression in one index definition. Choose the intended membership rule explicitly. Use separate collections below to avoid one experiment's constraints masking another.

## 2. Prerequisites and connection context

Complete Chapters 09, 17 and 18. Connect using the approved training URI from Chapter 06. Use the primary for writes/index changes on a replica set.

The user needs collection creation, read/write, index creation/listing/removal and cleanup privileges on this chapter database. No server configuration changes are needed.

The examples use default simple collation and scalar string email values where stated. Addresses are synthetic example.test values, not real accounts. Sharded unique-index restrictions and collation-specific comparisons require separate design.

In mongosh:

```javascript
const labName19 = "mongodb_enterprise_tutorial_ch19";
const lab19 = db.getSiblingDB(labName19);
printjson({ serverVersion: db.version(), database: labName19 });
if (lab19.getCollectionNames().length !== 0) {
  throw new Error("Chapter database already exists; review before resetting");
}
function check19(condition, message) {
  if (!condition) throw new Error(message);
}
function ids19(cursor) {
  return cursor.toArray().map(r => Number(r._id)).sort((a, b) => a - b);
}
function expectIds19(cursor, expected, message) {
  check19(JSON.stringify(ids19(cursor)) === JSON.stringify(expected), message);
}
function expectDuplicate19(action, message) {
  let caught = false;
  try { action(); } catch (error) {
    caught = Number(error.code) === 11000;
    printjson({ code: error.code, message: error.message });
    if (!caught) throw error;
  }
  check19(caught, message);
}
function stages19(node, result = new Set()) {
  if (!node || typeof node !== "object") return result;
  if (typeof node.stage === "string") result.add(node.stage);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) {
      value.forEach(child => stages19(child, result));
    } else if (value && typeof value === "object") {
      stages19(value, result);
    }
  }
  return result;
}
```

Record mongosh --version separately. Keep the shell session open because later blocks use these helpers. Duplicate-key failures are expected only where explicitly caught. Other failures should stop the lab.

## 3. Multikey: one document, multiple indexed values

```javascript
lab19.createCollection("catalog");
const catalog19 = lab19.catalog;
catalog19.insertMany([
  { _id: 1, tenantId: "t1", title: "Queue", tags: ["ops", "db"] },
  { _id: 2, tenantId: "t1", title: "Cache", tags: ["cache"] },
  { _id: 3, tenantId: "t2", title: "Storage", tags: ["ops", "storage"] }
]);
catalog19.createIndex(
  { tenantId: 1, tags: 1 }, { name: "tenant_tags" }
);
expectIds19(
  catalog19.find({ tenantId: "t1", tags: "ops" }).hint("tenant_tags"),
  [1], "Wrong scalar-to-array membership result"
);
const tagExplain19 = catalog19.find({ tenantId: "t1", tags: "ops" })
  .hint("tenant_tags").explain("executionStats");
check19(tagExplain19.executionStats.nReturned === 1,
        "Wrong tag result count");
printjson(tagExplain19.queryPlanner.winningPlan);
```

Inspect the IXSCAN's isMultiKey and multiKeyPaths metadata in the full winning plan. MongoDB creates multikey behavior automatically because tags contains arrays. Matching tags: "ops" tests element membership; it does not require the entire array to equal that string.

A compound index with a scalar tenant and one array tags field is supported. An independent second array in the same document/key pattern is a different case.

## 4. Failure exercise: parallel independent arrays

Attempt a compound index over two independent array fields:

```javascript
lab19.createCollection("parallelArrays");
const parallel19 = lab19.parallelArrays;
parallel19.insertOne({
  _id: 1, tags: ["ops", "db"], regions: ["east", "west"]
});
let parallelFailure19 = false;
try {
  parallel19.createIndex({ tags: 1, regions: 1 }, { name: "tags_regions" });
} catch (error) {
  parallelFailure19 = Number(error.code) === 171 ||
    error.codeName === "CannotIndexParallelArrays" ||
    /parallel arrays/i.test(error.message);
  printjson({ code: error.code, codeName: error.codeName, message: error.message });
  if (!parallelFailure19) throw error;
}
check19(parallelFailure19, "Expected parallel-array index rejection");
check19(!parallel19.getIndexes().some(i => i.name === "tags_regions"),
        "Failed index unexpectedly exists");
check19(parallel19.countDocuments({}) === 1, "Fixture disappeared");
```

Diagnosis: this index would combine two independently varying arrays in one document. Do not erase either business field merely to make the index build pass.

For this synthetic access pattern, correct by using separate indexes and validating each membership query:

```javascript
parallel19.createIndex({ tags: 1 }, { name: "tags_only" });
parallel19.createIndex({ regions: 1 }, { name: "regions_only" });
expectIds19(parallel19.find({ tags: "ops" }).hint("tags_only"),
            [1], "Tag lookup failed");
expectIds19(parallel19.find({ regions: "east" }).hint("regions_only"),
            [1], "Region lookup failed");
```

These separate indexes do not guarantee an efficient combined tags-and-regions query. Measure that contract independently; redesign into related entities if the workload requires it. Multiple dotted paths inside a shared array of embedded documents have more nuanced bounds rules than this independent-array example.

## 5. Same-element semantics still need $elemMatch

```javascript
lab19.createCollection("measurements");
const measurements19 = lab19.measurements;
measurements19.insertMany([
  { _id: 1, values: [70, 100] },
  { _id: 2, values: [85] },
  { _id: 3, values: [60] }
]);
measurements19.createIndex({ values: 1 }, { name: "values_idx" });
expectIds19(
  measurements19.find({ values: { $gte: 80, $lte: 90 } })
    .hint("values_idx"),
  [1, 2], "Unexpected independent-element predicate result"
);
expectIds19(
  measurements19.find({ values: { $elemMatch: { $gte: 80, $lte: 90 } } })
    .hint("values_idx"),
  [2], "Same-element interval result is wrong"
);
const sameElementExplain19 = measurements19.find({
  values: { $elemMatch: { $gte: 80, $lte: 90 } }
}).hint("values_idx").explain("executionStats");
printjson(sameElementExplain19.queryPlanner.winningPlan);
```

Without $elemMatch, values 100 and 70 can satisfy the two conditions in different elements. With $elemMatch, one element must be in the interval. The latter also allows intersecting bounds for this array predicate; inspect indexBounds.

An index accelerates the query's actual semantics. It does not repair an incorrectly specified business condition. Queries returning the array itself are not covered by this multikey index. Multikey coverage has additional constraints, including $elemMatch use; do not copy Chapter 18's scalar coverage assertions here.

## 6. Sparse: missing and null are different

```javascript
lab19.createCollection("optionalContacts");
const optional19 = lab19.optionalContacts;
optional19.insertMany([
  { _id: 1, email: "a@example.test" },
  { _id: 2 },
  { _id: 3, email: null },
  { _id: 4, email: "b@example.test" }
]);
optional19.createIndex({ email: 1 }, { name: "email_sparse", sparse: true });
expectIds19(optional19.find({ email: { $exists: true } })
  .hint("email_sparse"), [1, 3, 4], "Sparse membership incorrect");
expectIds19(optional19.find({ email: { $exists: false } }),
            [2], "Missing-field lookup incorrect");
expectIds19(optional19.find({ email: null }),
            [2, 3], "Null equality should include missing and explicit null");
```

The sparse index includes document 3 because the field exists, despite its null value. It omits document 2 because email is missing.

A normal query that needs omitted documents should not use an incomplete sparse access path. Explicit hints can override that protection. Reproduce the danger only on this known fixture:

```javascript
expectIds19(optional19.find({}).hint({ $natural: 1 }),
            [1, 2, 3, 4], "Full fixture mismatch");
expectIds19(optional19.find({}).hint("email_sparse"),
            [1, 3, 4], "Expected sparse-hint omission");
```

The forced sparse scan omits the missing-field document. This is a deliberately incomplete result, not an acceptable optimization. Remove the hint when the contract is “all contacts.”

Compound sparse indexes have membership rules depending on their component types; do not generalize this single-field experiment to every compound sparse definition.

## 7. Sparse plus unique: multiple missing, only one null

```javascript
lab19.createCollection("sparseUnique");
const sparseUnique19 = lab19.sparseUnique;
sparseUnique19.createIndex({ email: 1 }, {
  name: "email_sparse_unique", sparse: true, unique: true
});
sparseUnique19.insertMany([{ _id: 1 }, { _id: 2 }]);
sparseUnique19.insertOne({ _id: 3, email: null });
expectDuplicate19(
  () => sparseUnique19.insertOne({ _id: 4, email: null }),
  "Second explicit null should conflict"
);
sparseUnique19.insertOne({ _id: 5, email: "a@example.test" });
expectDuplicate19(
  () => sparseUnique19.insertOne({ _id: 6, email: "a@example.test" }),
  "Duplicate string should conflict"
);
expectIds19(sparseUnique19.find({}), [1, 2, 3, 5],
            "Rejected sparse-unique inserts changed state");
```

Uniqueness is enforced for entries included in the index. Missing email documents are outside this sparse index; explicit null and string values are inside it.

If the business rule is “unique string emails while allowing any number of missing/null placeholders,” use a partial unique rule with a string-type filter rather than assuming sparse implements it.

## 8. Partial indexes: business membership and query eligibility

Create a larger bounded fixture of jobs, only a fraction of which are OPEN:

```javascript
lab19.createCollection("jobs");
const jobs19 = lab19.jobs;
let jobBatch19 = [];
for (let i = 0; i < 1000; i++) {
  jobBatch19.push({
    _id: i,
    tenantId: "t" + (i % 5),
    status: Math.floor(i / 5) % 4 === 0 ? "OPEN" : "CLOSED",
    seq: i,
    payload: "Synthetic job " + i
  });
  if (jobBatch19.length === 100) {
    jobs19.insertMany(jobBatch19);
    jobBatch19 = [];
  }
}
jobs19.createIndex({ tenantId: 1, seq: -1 }, {
  name: "open_tenant_seq",
  partialFilterExpression: { status: "OPEN" }
});
check19(jobs19.countDocuments({}) === 1000, "Wrong job fixture");
check19(jobs19.countDocuments({ tenantId: "t1", status: "OPEN" }) === 50,
        "Wrong OPEN tenant count");
const openRows19 = jobs19.find({ tenantId: "t1", status: "OPEN" })
  .sort({ seq: -1 }).limit(5).hint("open_tenant_seq").toArray();
check19(JSON.stringify(openRows19.map(r => Number(r.seq))) ===
        JSON.stringify([981, 961, 941, 921, 901]), "Wrong OPEN page");
const openPlan19 = jobs19.find({ tenantId: "t1", status: "OPEN" })
  .sort({ seq: -1 }).limit(5).hint("open_tenant_seq")
  .explain("executionStats");
printjson(openPlan19.queryPlanner.winningPlan);
```

The query includes the partial condition, so this access path can supply a complete OPEN result. An arbitrary tenant-only query also needs CLOSED jobs, which are absent from the partial index.

```javascript
const allTenantRows19 = jobs19.find({ tenantId: "t1" })
  .sort({ seq: -1 }).limit(5).toArray();
check19(JSON.stringify(allTenantRows19.map(r => Number(r.seq))) ===
        JSON.stringify([996, 991, 986, 981, 976]), "Incomplete tenant page");
const allTenantPlan19 = jobs19.find({ tenantId: "t1" })
  .sort({ seq: -1 }).limit(5).explain("executionStats");
printjson(allTenantPlan19.queryPlanner.winningPlan);
```

Inspect that the normal plan does not rely on open_tenant_seq to supply an incomplete tenant-only result. A query must imply the index filter for normal eligible use. Do not insert status: OPEN into a query merely to make the index usable if the caller requested all statuses.

Do not force a partial index for a query outside its membership contract. Retain the natural full-result oracle when evaluating new predicates or hints.

## 9. Partial unique: scope the business identity

Enforce unique string email values within each tenant:

```javascript
lab19.createCollection("tenantContacts");
const contacts19 = lab19.tenantContacts;
contacts19.createIndex({ tenantId: 1, email: 1 }, {
  name: "tenant_string_email_unique",
  unique: true,
  partialFilterExpression: { email: { $type: "string" } }
});
contacts19.insertMany([
  { _id: 1, tenantId: "t1", email: "a@example.test" },
  { _id: 2, tenantId: "t2", email: "a@example.test" },
  { _id: 3, tenantId: "t1" },
  { _id: 4, tenantId: "t1" },
  { _id: 5, tenantId: "t1", email: null },
  { _id: 6, tenantId: "t1", email: null }
]);
expectDuplicate19(
  () => contacts19.insertOne({
    _id: 7, tenantId: "t1", email: "a@example.test"
  }),
  "Same-tenant duplicate should fail"
);
expectIds19(contacts19.find({}), [1, 2, 3, 4, 5, 6],
            "Unexpected partial-unique state");
```

The same string is allowed across different tenants. Multiple missing and null values are outside the filter. This index does not validate every document's schema: wrong types can fall outside the constraint. Pair the rule with schema validation when the application requires scalar string or null values.

Type predicates have array matching semantics. Do not treat this filter as a complete guarantee that email is a scalar string; validate shape as a separate contract.

Default simple collation compares string keys according to its rules. It does not implement your email normalization policy. Define normalization, preserve original display values if needed, and validate duplicates using the exact intended collation/key representation.

## 10. Failure exercise: excluded document enters the constraint

A null placeholder can exist until an update changes it into a duplicate indexed string:

```javascript
expectDuplicate19(
  () => contacts19.updateOne({ _id: 5 }, {
    $set: { email: "a@example.test" }
  }),
  "Transition into conflicting partial index should fail"
);
check19(contacts19.findOne({ _id: 5 }).email === null,
        "Rejected update changed the placeholder");
contacts19.updateOne({ _id: 5 }, {
  $set: { email: "b@example.test" }
});
check19(contacts19.findOne({ _id: 5 }).email === "b@example.test",
        "Corrected update failed");
```

Diagnosis: the document entered the partial membership set and conflicted with the existing tenant/email key. Correct by resolving business identity or using an actually distinct value, not by dropping the constraint.

A business rule limited to active documents can use a different partial filter. Reactivating archived records may then trigger a duplicate failure. Test state transitions as well as inserts.

## 11. Ordinary unique indexes treat missing as a key

```javascript
lab19.createCollection("ordinaryUnique");
const ordinary19 = lab19.ordinaryUnique;
ordinary19.createIndex({ externalId: 1 }, {
  name: "external_unique", unique: true
});
ordinary19.insertOne({ _id: 1 });
expectDuplicate19(
  () => ordinary19.insertOne({ _id: 2 }),
  "Second missing externalId should fail"
);
expectDuplicate19(
  () => ordinary19.insertOne({ _id: 3, externalId: null }),
  "Null should conflict with existing missing-field key"
);
ordinary19.insertOne({ _id: 4, externalId: "ext-4" });
expectIds19(ordinary19.find({}), [1, 4], "Wrong ordinary-unique state");
```

For a single-field ordinary unique index, missing and null map to the null index key. Only one document with that key is allowed. Compound unique indexes enforce uniqueness of the complete key tuple, so their missing/null behavior must be reasoned about across all components.

## 12. Unique multikey does not deduplicate an array

```javascript
lab19.createCollection("aliases");
const aliases19 = lab19.aliases;
aliases19.createIndex({ aliases: 1 }, {
  name: "aliases_unique", unique: true
});
aliases19.insertOne({ _id: 1, aliases: ["alpha", "alpha", "beta"] });
check19(aliases19.findOne({ _id: 1 }).aliases.length === 3,
        "Unique index unexpectedly rewrote array");
expectDuplicate19(
  () => aliases19.insertOne({ _id: 2, aliases: ["beta", "gamma"] }),
  "Alias shared across documents should fail"
);
aliases19.insertOne({ _id: 3, aliases: ["gamma"] });
expectIds19(aliases19.find({}), [1, 3], "Wrong unique-multikey state");
```

Repeated key values generated by one document are allowed here. A value shared with another document is rejected. Use validation or deliberate array update operations when duplicate elements within one document are forbidden; uniqueness across documents is a different invariant.

## 13. Unique index builds require clean existing data

```javascript
lab19.createCollection("migration");
const migration19 = lab19.migration;
migration19.insertMany([
  { _id: 1, tenantId: "t1", externalId: "dup", source: "first" },
  { _id: 2, tenantId: "t1", externalId: "dup", source: "second" },
  { _id: 3, tenantId: "t2", externalId: "dup", source: "other-tenant" }
]);
const duplicateGroups19 = migration19.aggregate([
  { $group: {
    _id: { tenantId: "$tenantId", externalId: "$externalId" },
    ids: { $push: "$_id" }, count: { $sum: 1 }
  } },
  { $match: { count: { $gt: 1 } } }
]).toArray();
check19(duplicateGroups19.length === 1 &&
        Number(duplicateGroups19[0].count) === 2,
        "Duplicate preview did not identify the conflict");
printjson(duplicateGroups19);
expectDuplicate19(
  () => migration19.createIndex({ tenantId: 1, externalId: 1 }, {
    name: "tenant_external_unique", unique: true
  }),
  "Expected duplicate data to prevent unique build"
);
check19(!migration19.getIndexes().some(i => i.name === "tenant_external_unique"),
        "Rejected unique index unexpectedly exists");
```

Do not automatically delete a duplicate. In the lab, assign the second synthetic record a corrected identifier while preserving both records:

```javascript
migration19.updateOne({ _id: 2 }, { $set: { externalId: "corrected-2" } });
migration19.createIndex({ tenantId: 1, externalId: 1 }, {
  name: "tenant_external_unique", unique: true
});
check19(migration19.countDocuments({}) === 3, "Correction lost records");
expectDuplicate19(
  () => migration19.insertOne({
    _id: 4, tenantId: "t1", externalId: "dup"
  }),
  "Completed unique index did not reject conflict"
);
```

In production, the preflight grouping must mirror the intended membership rule, key normalization and collation. Missing/null, arrays and partial filters complicate that preview. Coordinate concurrent writes so new duplicates cannot appear between preflight and enforcement; the build itself remains an enforcement check.

## 14. Troubleshooting

| Symptom | Evidence | Cause to check | Action |
|---|---|---|---|
| Parallel-array rejection | Document shapes, key pattern, error | Independent arrays in a compound multikey index | Redesign access pattern; do not erase data blindly |
| Array range matches unexpected record | Actual array and predicate | Different elements satisfy different conditions | Use $elemMatch when same-element semantics are required |
| Sparse query omits records | Hint, missing-field counts | Forced index cannot represent all documents | Remove incomplete hint |
| Second null insert fails | Index options and existing key | Null is present/indexed | Use correct partial membership if business policy allows it |
| Partial index not chosen | Filter implication, full plan | Query needs excluded documents | Keep correct query semantics; design another access path |
| Duplicate error on update | Before/after membership, conflicting tuple | Document entered constrained set | Resolve identity and verify rejected update left state intact |
| Unique build fails | Duplicate grouping, null/missing/types | Existing conflicting keys | Reconcile data with business approval, then rebuild |
| Repeated array values remain | Unique index and array contents | Constraint is across documents | Validate or deduplicate array separately |

Duplicate-key errors are evidence of constraint enforcement, not a generic transient failure. Blindly retrying the same conflicting input will not repair it.

## 15. Production considerations

Document the invariant in business language: global identifier uniqueness, tenant-scoped identity, active-only identity, or uniqueness only for typed optional values. Choose index membership to match that rule and validate document shape separately.

Sparse and partial indexes can reduce index entries, but membership-changing updates add/remove entries. Measure build resources, index sizes, write contention and query work for realistic data. Array cardinality can substantially increase multikey maintenance work; keep arrays bounded.

Use complete query results as the primary correctness check. An index-backed plan returning fewer records is not a performance improvement when it violates the requested scope.

Unique rules affect writes and application error handling. Map conflicts to a clear business response, preserve operation identity for reconciliation, and avoid exposing another tenant's confidential record in an error message.

Before changing a constraint, capture its exact key pattern, unique flag, filter, sparse setting and collation. Dropping a unique index removes enforcement; hiding a unique index does not remove its uniqueness enforcement. Hiding is therefore not a rehearsal of accepting conflicting writes.

Sharded collections have specific requirements for unique indexes, including shard-key-prefix constraints. This unsharded lab does not validate a sharded identity model. TTL membership and lifecycle follow in Chapter 20.

## 16. Cleanup and rollback

Capture index definitions, expected failure codes, query result IDs and plans first. This lab changed no cluster settings or application resources.

```javascript
check19(contacts19.countDocuments({}) === 6, "Unexpected contact count");
check19(contacts19.findOne({ _id: 5 }).email === "b@example.test",
        "Corrected contact state missing");
check19(migration19.countDocuments({}) === 3, "Migration state mismatch");
if (lab19.getName() !== "mongodb_enterprise_tutorial_ch19") {
  throw new Error("Refusing cleanup outside the Chapter 19 training database");
}
const dropResult19 = lab19.dropDatabase();
check19(dropResult19.ok === 1, "Database cleanup command failed");
check19(lab19.getCollectionNames().length === 0, "Cleanup incomplete");
```

The named database owns every fixture and index in this chapter. Do not run a blanket cleanup against unrelated databases. A production uniqueness change would need a separate recovery plan; deleting a teaching database is not such a plan.

## 17. Acceptance and evidence

- [ ] Recorded exact server/shell versions and unsharded context.
- [ ] Verified multikey tag membership and inspected multikey metadata.
- [ ] Reproduced parallel-array rejection and validated separate access paths.
- [ ] Distinguished independent-element and same-element predicates.
- [ ] Proved sparse excludes missing but includes explicit null.
- [ ] Reproduced deliberately incomplete sparse-hinted results.
- [ ] Verified sparse unique missing/null behavior.
- [ ] Verified partial query completeness and tenant-scoped string uniqueness.
- [ ] Rejected a membership-changing duplicate update and preserved state.
- [ ] Distinguished ordinary unique and unique-multikey behavior.
- [ ] Reconciled duplicate fixture data before a successful unique build.
- [ ] Captured evidence and completed scoped cleanup.

**Evidence:** versions, complete index options, fixture/result IDs, winning plans and bounds, duplicate/parallel-array error codes, post-failure state checks, corrected migration and cleanup. Runtime validation remains pending until this lab is executed on the specified environment.

## 18. Review questions

1. Why does a unique multikey index allow repeated values within one document?
2. Why can a sparse index contain explicit null but omit a missing field?
3. How can an index hint change result completeness?
4. What must a query imply to use a partial index safely?
5. Why can updating a null placeholder fail under a partial unique index?
6. What other contract is needed besides a type-filtered unique index?
7. Why must duplicate preflight match collation and membership?
8. Why does hiding a unique index leave duplicate enforcement active?

## 19. Official references

- [MongoDB 8.0: multikey indexes](https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-multikey/)
- [MongoDB 8.0: multikey bounds and $elemMatch](https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-multikey/multikey-index-bounds/)
- [MongoDB 8.0: partial indexes](https://www.mongodb.com/docs/v8.0/core/index-partial/)
- [MongoDB 8.0: sparse indexes](https://www.mongodb.com/docs/v8.0/core/index-sparse/)
- [MongoDB 8.0: unique indexes](https://www.mongodb.com/docs/v8.0/core/index-unique/)
- [MongoDB 8.0: hidden indexes](https://www.mongodb.com/docs/v8.0/core/index-hidden/)

---

Previous: [Chapter 18 — ESR Index Design and Covered Queries](18-esr-index-design-and-covered-queries.md)  
Next: [Chapter 20 — TTL Retention and Index Lifecycle](20-ttl-retention-and-index-lifecycle.md).
