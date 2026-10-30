# Chapter 55 --- Redis Enterprise RedisJSON Data Modeling & Document Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 10 --- Migration, Data Services & Advanced Capabilities\
**Level:** Intermediate → Advanced Production Data Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators, Application Architects\
**Lab type:** JSON document modeling, JSONPath CRUD, partial updates,
arrays/objects, TTL, schema evolution, concurrency, memory engineering,
Search integration, client integration, benchmarking, observability,
failure injection, troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

RedisJSON allows applications to store and manipulate structured JSON
documents directly in Redis.

Instead of storing an opaque JSON string:

``` text
profile:1001
    ->
"{\"name\":\"Ava\",\"status\":\"active\"}"
```

applications can work with document paths:

``` text
profile:1001
    |
    +-- $.name
    +-- $.status
    +-- $.address.city
    +-- $.preferences
```

This can improve application ergonomics, partial updates, and
integration with Redis Search.

But RedisJSON does not remove the need for production engineering.

You still need to design:

``` text
key boundaries
document size
schema evolution
TTL
concurrency
memory
indexing
security
capacity
observability
```

By the end of this chapter, you should be able to:

-   determine when RedisJSON is appropriate;
-   design JSON document boundaries;
-   use JSONPath safely;
-   create/read/update/delete documents;
-   perform partial updates;
-   work with arrays and nested objects;
-   design TTL and invalidation behavior;
-   evolve schemas safely;
-   reason about concurrent updates;
-   measure document memory and payload size;
-   understand RedisJSON and Search boundaries;
-   integrate application clients;
-   benchmark document workloads;
-   monitor production behavior;
-   troubleshoot common failures;
-   define production acceptance gates.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not choose RedisJSON merely because the source data is JSON.

Choose it when structured document operations provide meaningful value.

Ask:

``` text
Do we need path-level access?
Do we need partial updates?
Do we need Search indexing over document fields?
Do we need atomic document operations?
Is Redis the correct system for this data?
```

------------------------------------------------------------------------

# Part 1 --- RedisJSON Use Cases

## 3. Good Candidates

Examples:

``` text
profile cache
product/catalog cache
configuration documents
feature metadata
session documents
API response cache
searchable application objects
```

## 4. Poor Candidates

RedisJSON may not be appropriate when:

``` text
the value is tiny and opaque
the application always replaces the whole object
the data is huge
Redis should not be the source of truth
another structure is simpler
the workload is primarily relational
```

------------------------------------------------------------------------

# Part 2 --- RedisJSON vs JSON String

## 5. Opaque String

Traditional pattern:

``` bash
SET profile:1001 '{"name":"Ava","status":"active"}'
```

Redis sees the value primarily as a string.

Application code parses it.

## 6. RedisJSON

Conceptually:

``` bash
JSON.SET profile:1001 $ '{"name":"Ava","status":"active"}'
```

RedisJSON understands document structure and paths.

------------------------------------------------------------------------

# Part 3 --- Key Boundary

## 7. One Document per Entity

A common design:

``` text
profile:<id>
product:<id>
session:<id>
```

Avoid putting an entire application's dataset into one giant JSON
document.

Large shared documents increase:

``` text
contention
payload size
memory impact
update blast radius
```

------------------------------------------------------------------------

# Part 4 --- Lab Namespace

## 8. Safety

Use:

``` text
tutorial:chapter55:profile:<id>
```

All lab data must remain isolated from business keys.

------------------------------------------------------------------------

# Part 5 --- Basic Document

## 9. Example

``` json
{
  "id": "1001",
  "name": "Ava",
  "status": "active",
  "address": {
    "city": "Charlotte",
    "state": "NC"
  },
  "tags": ["premium", "mobile"],
  "version": 1
}
```

------------------------------------------------------------------------

# Part 6 --- Create

## 10. JSON.SET

Example:

``` bash
redis-cli JSON.SET tutorial:chapter55:profile:1001 '$' \
'{"id":"1001","name":"Ava","status":"active","address":{"city":"Charlotte","state":"NC"},"tags":["premium","mobile"],"version":1}'
```

Validate exact JSONPath syntax against the deployed RedisJSON/Redis
version.

------------------------------------------------------------------------

# Part 7 --- Read Whole Document

## 11. JSON.GET

``` bash
redis-cli JSON.GET tutorial:chapter55:profile:1001
```

Whole-document reads can be convenient but may transfer unnecessary
data.

------------------------------------------------------------------------

# Part 8 --- Read a Path

## 12. Selective Access

``` bash
redis-cli JSON.GET tutorial:chapter55:profile:1001 '$.name'
```

and:

``` bash
redis-cli JSON.GET tutorial:chapter55:profile:1001 '$.address.city'
```

Selective reads can reduce application-side parsing and payload
transfer.

------------------------------------------------------------------------

# Part 9 --- Partial Update

## 13. Update One Field

``` bash
redis-cli JSON.SET tutorial:chapter55:profile:1001 '$.status' '"inactive"'
```

The application does not need to fetch, modify, and rewrite the entire
document.

------------------------------------------------------------------------

# Part 10 --- Nested Object

## 14. Update

``` bash
redis-cli JSON.SET tutorial:chapter55:profile:1001 '$.address.city' '"Raleigh"'
```

Document paths should be treated as part of the application data
contract.

------------------------------------------------------------------------

# Part 11 --- Numbers

## 15. Numeric Operations

Where supported, RedisJSON provides numeric operations.

Example concept:

``` bash
redis-cli JSON.NUMINCRBY tutorial:chapter55:profile:1001 '$.version' 1
```

This avoids a client read-modify-write cycle for simple numeric changes.

------------------------------------------------------------------------

# Part 12 --- Arrays

## 16. Append

Example:

``` bash
redis-cli JSON.ARRAPPEND tutorial:chapter55:profile:1001 '$.tags' '"web"'
```

Validate:

``` bash
redis-cli JSON.GET tutorial:chapter55:profile:1001 '$.tags'
```

------------------------------------------------------------------------

# Part 13 --- Array Length

## 17. Inspect

``` bash
redis-cli JSON.ARRLEN tutorial:chapter55:profile:1001 '$.tags'
```

Do not allow arrays to grow without bounds.

------------------------------------------------------------------------

# Part 14 --- Delete a Path

## 18. JSON.DEL

Example:

``` bash
redis-cli JSON.DEL tutorial:chapter55:profile:1001 '$.address.state'
```

Path deletion can be safer than replacing an entire document when only
one field must be removed.

------------------------------------------------------------------------

# Part 15 --- Delete Document

## 19. Key Removal

Removing the key removes the document.

For lab cleanup, prefer:

``` text
SCAN
+
UNLINK
```

for confirmed disposable keys.

------------------------------------------------------------------------

# Part 16 --- JSON.TYPE

## 20. Inspect

Use the supported JSON type inspection command to validate path types.

Type awareness is useful for:

``` text
schema validation
debugging
migration
client compatibility
```

------------------------------------------------------------------------

# Part 17 --- JSON.OBJKEYS / Object Inspection

## 21. Controlled Use

Object inspection can help understand a document during development and
troubleshooting.

Avoid repeatedly enumerating very large objects in hot production paths.

------------------------------------------------------------------------

# Part 18 --- Document Modeling

## 22. Embed vs Separate

Suppose a profile has 1,000 activity records.

Option A:

``` text
one giant profile JSON
```

Option B:

``` text
profile:<id>
activity:<id>:<event>
```

Consider:

``` text
read pattern
update pattern
TTL
size
contention
Search indexing
lifecycle
```

------------------------------------------------------------------------

# Part 19 --- Bounded Documents

## 23. Avoid Unlimited Growth

Risky pattern:

``` text
document.events += forever
```

This can create a giant key.

Use:

``` text
bounded arrays
separate keys
Streams
source database
```

depending on the workload.

------------------------------------------------------------------------

# Part 20 --- Document Size

## 24. Measure

Track:

``` text
P50
P95
P99
maximum
```

document size.

Large documents affect:

``` text
memory
network
serialization
replication
backup
migration
latency
```

------------------------------------------------------------------------

# Part 21 --- Memory Usage

## 25. Measure Actual Redis Memory

For controlled keys:

``` bash
redis-cli MEMORY USAGE tutorial:chapter55:profile:1001
```

Do not estimate Redis memory only from raw JSON text size.

------------------------------------------------------------------------

# Part 22 --- Path Read vs Whole Read

## 26. Benchmark

Compare:

``` text
whole JSON.GET
selected field JSON.GET
```

for representative documents.

Measure:

``` text
response bytes
P99
client CPU
```

------------------------------------------------------------------------

# Part 23 --- Path Update vs Whole Rewrite

## 27. Benchmark

Compare:

``` text
replace entire document
```

with:

``` text
update one path
```

for representative workloads.

------------------------------------------------------------------------

# Part 24 --- TTL

## 28. TTL Is Key-Level

Redis expiration is associated with the key.

Conceptually:

``` text
document key -> TTL
```

not independently with each JSON field.

Design field lifecycles accordingly.

------------------------------------------------------------------------

# Part 25 --- Set TTL

## 29. Example

``` bash
redis-cli EXPIRE tutorial:chapter55:profile:1001 3600
```

Validate:

``` bash
redis-cli TTL tutorial:chapter55:profile:1001
```

------------------------------------------------------------------------

# Part 26 --- TTL Reset Risk

## 30. Application Behavior

When updating JSON content, verify whether the application workflow
preserves the intended key TTL.

Do not assume every write path has the desired expiration behavior.

Test it.

------------------------------------------------------------------------

# Part 27 --- Different Field Lifetimes

## 31. Model Separately

If fields need radically different lifetimes:

``` text
profile identity = hours
temporary token = minutes
history = days
```

one document may be the wrong boundary.

Separate keys can provide independent TTLs.

------------------------------------------------------------------------

# Part 28 --- Cache Invalidation

## 32. Document Cache

If RedisJSON stores cached source data, define:

``` text
TTL
explicit invalidation
change propagation
source-of-truth behavior
stale tolerance
```

RedisJSON does not solve cache invalidation automatically.

------------------------------------------------------------------------

# Part 29 --- Source of Truth

## 33. Explicit

Document whether RedisJSON is:

``` text
cache
derived store
session store
authoritative state
```

Recovery and persistence requirements depend on this classification.

------------------------------------------------------------------------

# Part 30 --- Schema Evolution

## 34. Documents Change

Example version 1:

``` json
{
  "name": "Ava"
}
```

Version 2:

``` json
{
  "name": {
    "first": "Ava",
    "last": "Smith"
  }
}
```

This can break:

``` text
clients
JSONPath
Search indexes
serialization
```

------------------------------------------------------------------------

# Part 31 --- Schema Version

## 35. Optional Pattern

Include:

``` json
{
  "schema_version": 2
}
```

when explicit document-version handling is useful.

Do not add versioning without a migration strategy.

------------------------------------------------------------------------

# Part 32 --- Additive Evolution

## 36. Safer Pattern

Adding optional fields is often easier than changing a field's type.

Example:

``` text
old client ignores new field
new client understands new field
```

Validate actual client behavior.

------------------------------------------------------------------------

# Part 33 --- Type Change

## 37. High Risk

Changing:

``` text
status: "1"
```

to:

``` text
status: 1
```

can affect:

``` text
JSONPath behavior
application deserialization
Search schema
queries
```

Treat type changes as migrations.

------------------------------------------------------------------------

# Part 34 --- Backward Compatibility

## 38. Rolling Deployment

During deployment, old and new application versions may run
simultaneously.

Documents must be compatible with both versions during the overlap
window or the rollout must explicitly control access.

------------------------------------------------------------------------

# Part 35 --- Schema Migration

## 39. Pattern

``` text
inventory versions
deploy compatible readers
migrate documents
validate
deploy writers for new schema
retire old schema support
```

Avoid changing every document and every client simultaneously without
rollback planning.

------------------------------------------------------------------------

# Part 36 --- Concurrency

## 40. Lost Update

Application A:

``` text
GET document
```

Application B:

``` text
GET document
```

A modifies field X and writes whole document.

B modifies field Y and writes its stale whole document.

B may overwrite A's update.

------------------------------------------------------------------------

# Part 37 --- Partial Update Advantage

## 41. Reduce Blast Radius

Path-level updates can reduce lost-update risk when independent fields
are changed.

They do not solve every concurrency problem.

------------------------------------------------------------------------

# Part 38 --- Version Field

## 42. Optimistic Concurrency

A version field can help detect stale application state.

Example concept:

``` text
version = 10
client expects 10
update
version -> 11
```

For strict atomic compare-and-update semantics, use supported atomic
mechanisms and test them carefully.

------------------------------------------------------------------------

# Part 39 --- Transactions / Lua

## 43. Complex Atomic Logic

Where a document update depends on multiple conditions or keys, consider
supported transaction or server-side scripting patterns.

Keep scripts bounded and observable.

------------------------------------------------------------------------

# Part 40 --- Multi-Key Atomicity

## 44. Design

A JSON document is one Redis key.

If a business operation spans multiple keys, document-level operations
alone do not make the entire business operation atomic.

------------------------------------------------------------------------

# Part 41 --- Search Integration

## 45. Boundary

Redis Search can index fields from JSON documents where supported.

Think of:

``` text
JSON document
   |
indexed fields
   |
Search index
```

Document storage and Search indexing are related but distinct
operational concerns.

------------------------------------------------------------------------

# Part 42 --- Index Only Needed Fields

## 46. Avoid Over-Indexing

Indexing every field can increase:

``` text
memory
write cost
indexing work
complexity
```

Index fields required by real queries.

------------------------------------------------------------------------

# Part 43 --- Schema and Index Coordination

## 47. Important

A JSON schema change can require Search schema/index changes.

Coordinate:

``` text
document rollout
index rollout
query rollout
```

------------------------------------------------------------------------

# Part 44 --- Search Consistency

## 48. Validate

After document updates, understand the expected Search indexing behavior
and measure application-visible consistency according to the deployed
product/version.

------------------------------------------------------------------------

# Part 45 --- Key Prefix

## 49. Search Scope

Use clear key prefixes so indexes can target intended document families.

Example:

``` text
app:profile:
```

Avoid accidental indexing of unrelated keys.

------------------------------------------------------------------------

# Part 46 --- Client Integration

## 50. SDK Support

Validate that the selected client version supports the required
RedisJSON commands and response formats.

Do not assume framework abstractions expose every capability correctly.

------------------------------------------------------------------------

# Part 47 --- Raw Command Escape Hatch

## 51. Caution

Some clients allow direct command execution.

If used:

``` text
centralize it
test response types
handle errors
pin compatibility
```

Avoid scattering raw RedisJSON command strings throughout application
code.

------------------------------------------------------------------------

# Part 48 --- Serialization Boundary

## 52. Avoid Double Encoding

Risky design:

``` text
RedisJSON document
contains
string field holding another entire JSON document
```

unless this is intentional.

Prefer native structured fields where useful.

------------------------------------------------------------------------

# Part 49 --- Null vs Missing

## 53. Semantics

Applications must distinguish where required:

``` text
field absent
```

from:

``` json
{"field": null}
```

This can affect application and Search behavior.

------------------------------------------------------------------------

# Part 50 --- Numbers

## 54. Precision

Validate numeric behavior for the application's range and language
runtime.

Do not silently assume all languages represent every numeric value
identically.

------------------------------------------------------------------------

# Part 51 --- Dates

## 55. Explicit Representation

JSON has no universal native date type.

Choose a documented representation such as:

``` text
ISO-8601 string
epoch timestamp
```

according to application/query requirements.

------------------------------------------------------------------------

# Part 52 --- Binary Data

## 56. Avoid Casual Embedding

Base64-encoding large binary objects inside JSON increases size.

Large binaries may belong in object storage with Redis storing
metadata/reference information.

------------------------------------------------------------------------

# Part 53 --- Sensitive Data

## 57. Minimize

Do not store sensitive fields merely because RedisJSON can store them.

Apply:

``` text
data classification
least privilege
encryption in transit
retention
logging controls
```

------------------------------------------------------------------------

# Part 54 --- Observability

## 58. Track

Useful metrics:

``` text
JSON command latency
ops/sec
errors
document size
memory
key count
evictions
network
CPU
Search indexing/query metrics where used
```

------------------------------------------------------------------------

# Part 55 --- Application Metrics

## 59. Track

``` text
whole-document reads
path reads
whole rewrites
partial updates
serialization time
payload bytes
cache hit/miss
schema version
```

------------------------------------------------------------------------

# Part 56 --- Slow Operation Investigation

## 60. Ask

``` text
Is the document large?
Is the path complex?
Is the network response large?
Is the client deserializing slowly?
Is Search indexing involved?
Is the shard hot?
```

------------------------------------------------------------------------

# Part 57 --- Capacity Model

## 61. Approximation

Estimate:

``` text
documents
× average Redis memory per document
+
indexes
+
replication
+
headroom
```

Use measured `MEMORY USAGE` samples rather than raw source JSON bytes
alone.

------------------------------------------------------------------------

# Part 58 --- Growth Model

## 62. Forecast

Track:

``` text
new documents/day
average document growth
TTL expiration
retention
index growth
```

------------------------------------------------------------------------

# Part 59 --- Benchmark Plan

## 63. Test

At minimum compare:

``` text
whole read
path read
whole rewrite
path update
array append
numeric update
Search-indexed write where used
```

across representative document sizes.

------------------------------------------------------------------------

# Part 60 --- Small Document Test

## 64. Example

Use a compact profile document.

Measure:

``` text
ops/sec
P99
memory
response bytes
```

------------------------------------------------------------------------

# Part 61 --- Medium Document Test

## 65. Example

Add nested objects and arrays.

Repeat the same measurements.

------------------------------------------------------------------------

# Part 62 --- Large Document Test

## 66. Controlled

Use a bounded large synthetic document.

Observe:

``` text
P99
network
memory
client CPU
```

Stop at predefined safety limits.

------------------------------------------------------------------------

# Part 63 --- Partial vs Whole Update Test

## 67. Compare

For the same document:

``` text
replace entire document
update one path
```

Record latency and network/application cost.

------------------------------------------------------------------------

# Part 64 --- Search-Indexed Write Test

## 68. Where Used

Compare write behavior:

``` text
without Search index
with required Search index
```

Do not interpret the difference as a RedisJSON defect; indexing adds
work.

------------------------------------------------------------------------

# Part 65 --- TTL Test

## 69. Validate

Create a document with a short lab TTL.

Update paths.

Verify expected TTL behavior after each operation.

------------------------------------------------------------------------

# Part 66 --- Schema Compatibility Lab

## 70. Test

Create:

``` text
schema v1
schema v2
```

Run old and new synthetic readers.

Document compatibility failures.

------------------------------------------------------------------------

# Part 67 --- Concurrent Update Lab

## 71. Test

Run two workers updating different fields.

Compare:

``` text
whole-document rewrite
path-level update
```

Observe lost-update behavior.

------------------------------------------------------------------------

# Part 68 --- Memory Lab

## 72. Measure

For 100, 1,000, and 10,000 representative lab documents, record:

``` text
Redis memory
average per document
growth
```

Use an isolated environment.

------------------------------------------------------------------------

# Part 69 --- Hot Document Lab

## 73. Test

Concentrate requests on one synthetic document.

Observe:

``` text
shard CPU
P99
network
```

------------------------------------------------------------------------

# Part 70 --- Failure Scenario 1

## 74. Invalid JSON

Send malformed JSON.

Expected:

``` text
command fails
application classifies validation error
no retry storm
```

------------------------------------------------------------------------

# Part 71 --- Failure Scenario 2

## 75. Missing Path

Attempt an operation against a missing path.

Validate application handling.

------------------------------------------------------------------------

# Part 72 --- Failure Scenario 3

## 76. Type Mismatch

Attempt a numeric/array operation on the wrong field type.

Validate fail-fast behavior.

------------------------------------------------------------------------

# Part 73 --- Failure Scenario 4

## 77. Oversized Document

Create a bounded large synthetic document.

Validate latency, memory, and alerting.

------------------------------------------------------------------------

# Part 74 --- Failure Scenario 5

## 78. Unbounded Array

Simulate growth in a lab.

Validate detection and size controls.

------------------------------------------------------------------------

# Part 75 --- Failure Scenario 6

## 79. Schema Change

Change a field type.

Run an old client.

Validate compatibility controls.

------------------------------------------------------------------------

# Part 76 --- Failure Scenario 7

## 80. Concurrent Whole Rewrite

Use two workers.

Demonstrate lost-update risk.

------------------------------------------------------------------------

# Part 77 --- Failure Scenario 8

## 81. TTL Surprise

Update a short-lived document and verify whether the intended TTL
remains.

------------------------------------------------------------------------

# Part 78 --- Failure Scenario 9

## 82. Search Schema Mismatch

Where Search is available, create a controlled mismatch between document
field assumptions and index/query expectations.

Validate detection.

------------------------------------------------------------------------

# Part 79 --- Failure Scenario 10

## 83. Memory Pressure

Load bounded synthetic JSON documents until an approved lab threshold.

Validate alerts and stop conditions before unsafe exhaustion.

------------------------------------------------------------------------

# Part 80 --- Troubleshooting Matrix

## 84. Common Problems

  -----------------------------------------------------------------------
  Symptom                             Investigate
  ----------------------------------- -----------------------------------
  JSON command slow                   document size, path, network, shard
                                      CPU

  memory higher than expected         measured object overhead, indexes,
                                      replicas

  update overwrites fields            whole rewrite, stale client state

  TTL incorrect                       write path, EXPIRE behavior, cache
                                      policy

  old client fails                    schema/type change

  Search misses document              index schema, prefix, indexing
                                      state

  write latency increases             document size, indexing,
                                      persistence

  array grows continuously            missing bound/retention

  app CPU high                        serialization/deserialization

  one shard hot                       hot document/key distribution
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Part 81 --- Runbook 1: Document Design Review

## 85. Procedure

``` text
1. Identify use case.
2. classify source of truth.
3. define key boundary.
4. define document schema.
5. define size limit.
6. define TTL.
7. define update pattern.
8. define Search fields.
9. define concurrency.
10. approve.
```

------------------------------------------------------------------------

# Part 82 --- Runbook 2: Large Document

## 86. Procedure

``` text
1. measure document size.
2. measure MEMORY USAGE.
3. identify growing fields.
4. identify read/write pattern.
5. split unbounded data if needed.
6. validate Search impact.
7. benchmark revised model.
8. monitor recurrence.
```

------------------------------------------------------------------------

# Part 83 --- Runbook 3: Schema Change

## 87. Procedure

``` text
1. inventory current versions.
2. identify client compatibility.
3. identify Search impact.
4. deploy compatible readers.
5. migrate documents.
6. validate.
7. deploy new writers.
8. retire old schema support.
```

------------------------------------------------------------------------

# Part 84 --- Runbook 4: TTL Issue

## 88. Procedure

``` text
1. record expected TTL.
2. inspect actual TTL.
3. identify write/update path.
4. reproduce in lab.
5. correct TTL logic.
6. validate invalidation.
7. test expiration.
8. monitor.
```

------------------------------------------------------------------------

# Part 85 --- Runbook 5: Lost Update

## 89. Procedure

``` text
1. identify conflicting writers.
2. determine whole vs path update.
3. inspect stale read-modify-write.
4. define atomicity requirement.
5. implement version/atomic pattern.
6. load test.
7. validate correctness.
8. monitor conflicts.
```

------------------------------------------------------------------------

# Part 86 --- Runbook 6: Search Integration Failure

## 90. Procedure

``` text
1. validate document exists.
2. validate key prefix.
3. validate JSON field/path.
4. validate Search schema.
5. validate field type.
6. inspect indexing/query state.
7. test representative query.
8. record fix.
```

------------------------------------------------------------------------

# Part 87 --- Runbook 7: Memory Growth

## 91. Procedure

``` text
1. measure key count.
2. measure document sizes.
3. measure TTL distribution.
4. inspect unbounded arrays/objects.
5. inspect Search index growth.
6. calculate growth rate.
7. apply retention/model fix.
8. validate headroom.
```

------------------------------------------------------------------------

# Part 88 --- Runbook 8: RedisJSON Performance

## 92. Procedure

``` text
1. classify operation.
2. measure P99.
3. measure document size.
4. compare path vs whole access.
5. inspect shard CPU/network.
6. inspect client serialization.
7. inspect Search/persistence impact.
8. benchmark remediation.
```

------------------------------------------------------------------------

# Part 89 --- Data Model Template

## 93. Record

``` text
Document:
Key pattern:
Owner:
Source of truth:
Schema version:
Expected count:
Average size:
P99 size:
Maximum size:
TTL:
Update pattern:
Concurrency:
Search indexes:
Sensitive fields:
Growth:
```

------------------------------------------------------------------------

# Part 90 --- Schema Change Template

## 94. Record

``` text
Current schema:
Target schema:
Field changes:
Type changes:
Old-client compatibility:
New-client compatibility:
Search impact:
Migration:
Rollback:
Validation:
```

------------------------------------------------------------------------

# Part 91 --- Production Acceptance

## 95. Data Model

-   [ ] RedisJSON use case justified;
-   [ ] key/document boundary defined;
-   [ ] source-of-truth role defined;
-   [ ] schema documented;
-   [ ] size limits defined;
-   [ ] unbounded arrays avoided;
-   [ ] sensitive data reviewed.

## 96. Lifecycle

-   [ ] TTL documented;
-   [ ] TTL update behavior tested;
-   [ ] invalidation defined;
-   [ ] schema evolution defined;
-   [ ] rolling compatibility tested;
-   [ ] migration/rollback defined.

## 97. Concurrency

-   [ ] writers identified;
-   [ ] whole-rewrite risk reviewed;
-   [ ] path updates used where appropriate;
-   [ ] version/atomicity strategy defined where needed;
-   [ ] multi-key atomicity requirements documented.

## 98. Search

-   [ ] only required fields indexed;
-   [ ] prefixes defined;
-   [ ] schema coordinated with documents;
-   [ ] indexed write cost tested;
-   [ ] Search validation completed.

## 99. Performance

-   [ ] P50/P95/P99 document sizes measured;
-   [ ] `MEMORY USAGE` sampled;
-   [ ] path vs whole read tested;
-   [ ] partial vs whole update tested;
-   [ ] large document tested;
-   [ ] hot document tested;
-   [ ] memory growth forecasted.

## 100. Operations

-   [ ] RedisJSON metrics monitored;
-   [ ] application metrics monitored;
-   [ ] ten failure scenarios completed;
-   [ ] eight runbooks reviewed;
-   [ ] capacity headroom validated;
-   [ ] cleanup tested.

------------------------------------------------------------------------

# 101. Knowledge Validation

1.  When is RedisJSON preferable to an opaque JSON string?
2.  Why should one giant JSON document usually be avoided?
3.  What does `JSON.SET` do?
4.  Why use path-level reads?
5.  Why use partial updates?
6.  Why should arrays be bounded?
7.  Why measure actual Redis memory?
8.  How can whole-document reads affect network cost?
9.  At what level does Redis TTL apply?
10. Why can different field lifetimes require separate keys?
11. Does RedisJSON solve cache invalidation?
12. Why classify Redis as cache vs authoritative state?
13. Why can schema evolution break clients?
14. Why are field type changes risky?
15. Why must rolling deployments consider old and new clients?
16. What is a lost update?
17. How can path updates reduce lost-update risk?
18. When is a version field useful?
19. Does one JSON document make a multi-key business operation atomic?
20. How does Redis Search relate to JSON?
21. Why avoid indexing every field?
22. Why coordinate Search and document schema changes?
23. Why centralize raw RedisJSON commands?
24. What is double encoding?
25. Why distinguish missing from null?
26. Why define date representation explicitly?
27. Why avoid large binary blobs in JSON?
28. Which RedisJSON metrics should be monitored?
29. Why benchmark Search-indexed writes separately?
30. What must pass before a RedisJSON model is production-ready?

------------------------------------------------------------------------

# 102. Hands-On Acceptance Checklist

-   [ ] Created Chapter 55 JSON document.
-   [ ] Read whole document.
-   [ ] Read nested path.
-   [ ] Updated one path.
-   [ ] Updated nested object.
-   [ ] Performed numeric operation.
-   [ ] Appended array value.
-   [ ] Measured array length.
-   [ ] Deleted a path.
-   [ ] Measured `MEMORY USAGE`.
-   [ ] Applied and validated TTL.
-   [ ] Tested TTL after updates.
-   [ ] Compared whole vs path reads.
-   [ ] Compared whole rewrite vs path update.
-   [ ] Created small/medium/large documents.
-   [ ] Tested schema v1/v2.
-   [ ] Tested old/new client compatibility.
-   [ ] Tested concurrent updates.
-   [ ] Tested hot document.
-   [ ] Tested invalid JSON.
-   [ ] Tested missing path.
-   [ ] Tested type mismatch.
-   [ ] Tested bounded large document.
-   [ ] Tested unbounded-growth detection.
-   [ ] Tested schema type change.
-   [ ] Tested TTL surprise.
-   [ ] Tested Search integration where available.
-   [ ] Tested memory-pressure stop conditions.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed eight production runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 103. Cleanup

List only Chapter 55 lab keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter55:*'
```

Review matches and remove only confirmed disposable keys with `UNLINK`.

Remove temporary:

``` text
Search indexes created for the lab
synthetic clients
load generators
temporary dashboards
temporary alerts
schema-test artifacts
```

Never use `FLUSHDB` or `FLUSHALL` against a shared or production
database.

------------------------------------------------------------------------

# 104. Key Takeaways

1.  RedisJSON is useful when structured document operations add value.
2.  JSON source data alone is not a reason to use RedisJSON.
3.  Document boundaries should match lifecycle and access patterns.
4.  Avoid giant shared documents.
5.  Path-level reads can reduce unnecessary transfer.
6.  Partial updates can reduce application work and overwrite risk.
7.  Arrays and nested objects must remain bounded.
8.  Measure actual Redis memory, not only raw JSON bytes.
9.  TTL applies to the Redis key/document rather than independently to
    each field.
10. Different field lifetimes may require separate keys.
11. RedisJSON does not solve cache invalidation.
12. Source-of-truth classification determines durability and recovery
    requirements.
13. Schema changes require application compatibility planning.
14. Field type changes should be treated as migrations.
15. Rolling deployments can expose old and new clients simultaneously.
16. Whole-document read-modify-write can create lost updates.
17. Path updates reduce but do not eliminate concurrency concerns.
18. Multi-key operations require separate atomicity design.
19. Redis Search indexing adds memory and write work.
20. Index only fields needed by actual queries.
21. Search schema and JSON schema must evolve together.
22. Serialization, payload size, and client CPU are part of performance.
23. Large documents affect network, replication, backup, and migration.
24. Production monitoring should include document-size and schema
    behavior.
25. RedisJSON production readiness requires correctness, compatibility,
    capacity, observability, and failure testing together.

------------------------------------------------------------------------

# 105. References

Validate commands, JSONPath behavior, indexing integration, and client
APIs against the exact deployed Redis/Redis Enterprise version and
current official Redis documentation.

Recommended documentation areas:

-   Redis JSON
-   JSON.SET
-   JSON.GET
-   JSON.DEL
-   JSON.NUMINCRBY
-   JSON.ARRAPPEND
-   JSON.ARRLEN
-   JSONPath
-   Redis Search with JSON
-   Redis key expiration
-   Redis memory optimization
-   Redis transactions and scripting
-   Redis client libraries
-   Redis Enterprise observability and sizing

------------------------------------------------------------------------

# Next Chapter

**Chapter 56 --- Redis Enterprise Search & Query Architecture, Indexing
& Operations**

Chapter 56 will cover Search architecture, JSON/hash indexing, schema
design, prefixes, field types, text/tag/numeric/geo fields, query
patterns, index creation and lifecycle, write amplification, memory,
query correctness, index rebuilds, client integration, observability,
failure scenarios, troubleshooting, runbooks, and production acceptance.
