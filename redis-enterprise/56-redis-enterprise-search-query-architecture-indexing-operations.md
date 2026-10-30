# Chapter 56 --- Redis Enterprise Search & Query Architecture, Indexing & Operations

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 10 --- Migration, Data Services & Advanced Capabilities\
**Level:** Advanced → Production Search Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators, Application Architects\
**Lab type:** Search architecture, HASH/JSON indexing, schema design,
prefixes, field types, queries, sorting, pagination, aggregation
awareness, indexing cost, memory, index lifecycle, rebuilds, client
integration, benchmarking, observability, failure injection,
troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Redis Search adds secondary indexing and query capabilities over Redis
data.

A production design can look like:

``` text
application
   |
Redis client
   |
Redis Enterprise database
   |
   +-- HASH / JSON documents
   |
   +-- Search index
         |
         +-- TEXT
         +-- TAG
         +-- NUMERIC
         +-- GEO
         +-- other supported field capabilities
```

Search makes Redis more powerful, but indexing is not free.

Indexes consume:

``` text
memory
CPU
write processing
operational attention
schema ownership
```

By the end of this chapter, you should be able to:

-   explain Redis Search architecture;
-   choose HASH or JSON source models;
-   design key prefixes;
-   create search schemas;
-   choose TEXT, TAG, NUMERIC, and GEO fields;
-   write representative queries;
-   design sorting and pagination;
-   understand indexing/write amplification;
-   estimate index memory;
-   benchmark indexed workloads;
-   manage index lifecycle;
-   plan schema changes and rebuilds;
-   troubleshoot missing or slow results;
-   instrument Search;
-   define production runbooks and acceptance criteria.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not index fields because they exist.

Index fields because a real application query requires them.

A good Search design begins with:

``` text
query requirements
```

not:

``` text
document fields
```

------------------------------------------------------------------------

# Part 1 --- Search Architecture

## 3. Logical Model

``` text
Redis key
   |
HASH or JSON
   |
index definition
   |
indexed fields
   |
query
   |
results
```

The source object and the index are related but operationally distinct
concerns.

------------------------------------------------------------------------

# Part 2 --- Search Use Cases

## 4. Examples

Redis Search can support workloads such as:

``` text
product lookup
profile search
session/admin lookup
catalog filtering
autocomplete
numeric range filtering
geo filtering
document search
application metadata discovery
```

------------------------------------------------------------------------

# Part 3 --- When Not to Use Search

## 5. Avoid Unnecessary Indexing

If access is always:

``` text
GET exact-key
```

a secondary Search index may add cost without benefit.

Similarly, Redis Search is not automatically a replacement for every:

``` text
relational query
analytics engine
data warehouse
full enterprise search platform
```

Choose based on workload.

------------------------------------------------------------------------

# Part 4 --- Source Data Model

## 6. HASH

A Redis HASH can provide fields for indexing.

Conceptually:

``` text
product:1001
  name
  category
  price
  status
```

## 7. JSON

RedisJSON documents can also be indexed where supported.

Conceptually:

``` json
{
  "name": "Laptop",
  "category": "electronics",
  "price": 1299.99,
  "status": "active"
}
```

Choose based on application data and update requirements.

------------------------------------------------------------------------

# Part 5 --- Key Prefix

## 8. Scope

Use clear key families:

``` text
app:product:
app:profile:
app:order:
```

Then scope indexes to intended prefixes.

This helps prevent accidental indexing of unrelated keys.

------------------------------------------------------------------------

# Part 6 --- Lab Namespace

## 9. Safety

Use:

``` text
tutorial:chapter56:product:<id>
```

Use a dedicated lab index name such as:

``` text
idx:tutorial:chapter56:product
```

Never point a lab index at broad production prefixes.

------------------------------------------------------------------------

# Part 7 --- Query-First Design

## 10. Example Requirements

Suppose the application needs:

``` text
search product name
filter category
filter active status
filter price range
sort by price
```

This directly informs the index schema.

------------------------------------------------------------------------

# Part 8 --- Field Classification

## 11. Example

  Field      Query Requirement   Candidate Type
  ---------- ------------------- ----------------
  name       full-text search    TEXT
  category   exact/filter        TAG
  status     exact/filter        TAG
  price      range/sort          NUMERIC
  location   radius              GEO

Use exact capabilities supported by the deployed version.

------------------------------------------------------------------------

# Part 9 --- TEXT Fields

## 12. Purpose

TEXT is appropriate for tokenized/full-text search behavior.

Example concept:

``` text
name = "wireless noise cancelling headphones"
```

Queries may match terms rather than requiring exact full-string
equality.

------------------------------------------------------------------------

# Part 10 --- TAG Fields

## 13. Purpose

TAG is useful for exact categorical values such as:

``` text
active
premium
electronics
north-america
```

Do not use TEXT when exact categorical filtering is the real
requirement.

------------------------------------------------------------------------

# Part 11 --- NUMERIC Fields

## 14. Purpose

NUMERIC supports numeric filtering/ranges and related supported
operations.

Examples:

``` text
price
age
timestamp
score
```

------------------------------------------------------------------------

# Part 12 --- GEO Fields

## 15. Purpose

GEO supports location-based query use cases where available and
appropriate.

Validate coordinate format and application semantics.

------------------------------------------------------------------------

# Part 13 --- Sortable Fields

## 16. Cost

Making fields sortable can require additional index resources.

Only configure sorting for fields that actually require it.

------------------------------------------------------------------------

# Part 14 --- Stored / Returned Data

## 17. Response Design

Return only data required by the application where supported.

Avoid returning large documents if the UI needs only:

``` text
id
name
price
```

------------------------------------------------------------------------

# Part 15 --- HASH Lab Data

## 18. Create

``` bash
redis-cli HSET tutorial:chapter56:product:1001 \
  name "Wireless Headphones" \
  category "electronics" \
  status "active" \
  price "199.99"

redis-cli HSET tutorial:chapter56:product:1002 \
  name "Mechanical Keyboard" \
  category "electronics" \
  status "active" \
  price "129.99"

redis-cli HSET tutorial:chapter56:product:1003 \
  name "Standing Desk" \
  category "office" \
  status "inactive" \
  price "499.99"
```

------------------------------------------------------------------------

# Part 16 --- HASH Index

## 19. Example

A representative command may look like:

``` bash
redis-cli FT.CREATE idx:tutorial:chapter56:product \
  ON HASH \
  PREFIX 1 "tutorial:chapter56:product:" \
  SCHEMA \
  name TEXT \
  category TAG \
  status TAG \
  price NUMERIC SORTABLE
```

Validate syntax against the exact deployed Redis Search version.

------------------------------------------------------------------------

# Part 17 --- Index Inspection

## 20. FT.INFO

Use the supported index information command:

``` bash
redis-cli FT.INFO idx:tutorial:chapter56:product
```

Inspect:

``` text
document count
field/schema information
index size/memory indicators
indexing status/errors where exposed
```

------------------------------------------------------------------------

# Part 18 --- Full-Text Query

## 21. Example

``` bash
redis-cli FT.SEARCH idx:tutorial:chapter56:product 'headphones'
```

Validate expected product.

------------------------------------------------------------------------

# Part 19 --- TAG Filter

## 22. Example

``` bash
redis-cli FT.SEARCH idx:tutorial:chapter56:product '@category:{electronics}'
```

TAG escaping rules matter for special characters.

------------------------------------------------------------------------

# Part 20 --- Multiple Filters

## 23. Example

``` bash
redis-cli FT.SEARCH idx:tutorial:chapter56:product \
'@category:{electronics} @status:{active}'
```

------------------------------------------------------------------------

# Part 21 --- Numeric Range

## 24. Example

``` bash
redis-cli FT.SEARCH idx:tutorial:chapter56:product \
'@price:[100 250]'
```

Expected:

``` text
Keyboard
Headphones
```

based on the lab data.

------------------------------------------------------------------------

# Part 22 --- Sort

## 25. Example

``` bash
redis-cli FT.SEARCH idx:tutorial:chapter56:product \
'@category:{electronics}' \
SORTBY price ASC
```

Only rely on sorting behavior supported by the defined schema/version.

------------------------------------------------------------------------

# Part 23 --- Limit

## 26. Bound Results

Use bounded result windows.

Example:

``` bash
redis-cli FT.SEARCH idx:tutorial:chapter56:product '*' LIMIT 0 10
```

Do not request enormous result sets casually.

------------------------------------------------------------------------

# Part 24 --- Pagination

## 27. Risk

Deep offset pagination can become expensive depending on query shape and
product behavior.

Design UI/API pagination intentionally.

Benchmark realistic page depths.

------------------------------------------------------------------------

# Part 25 --- Count-Only Queries

## 28. Where Supported

If only a count is required, use supported query options that avoid
returning unnecessary documents.

Validate exact syntax/version.

------------------------------------------------------------------------

# Part 26 --- Return Projection

## 29. Minimize Payload

Where supported, return only required fields.

This reduces:

``` text
network
client parsing
response memory
```

------------------------------------------------------------------------

# Part 27 --- JSON Lab Data

## 30. Example

If RedisJSON and Search integration are available, use an **owner-approved isolated database** with module/index support verified for the deployed release. The following is one **interactive Redis command**, issued only after connecting through a securely authenticated, CA-verified TLS Redis CLI session (as established in the Chapter 55 lab). Do not paste `JSON.SET` directly into a host shell or run it on application-owned data:

``` redis
JSON.SET tutorial:chapter56:jsonproduct:2001 '$' '{"name":"Running Shoes","category":"sports","status":"active","price":89.99}'
```

**Expected:** `OK` when the module is available and the JSON is accepted; the document is created or replaced at this **exact lab key**. Optional verification:

``` redis
JSON.GET tutorial:chapter56:jsonproduct:2001 '$.price'
```

**Expected for the fresh document:** A JSON-encoded array containing `89.99` (schematically `[89.99]`, depending on RESP/client rendering). Module-not-available, ACL, TLS, or syntax errors are **FAIL/NOT EXECUTED**, not a reason to bypass security gates. The successful JSON write alone does **not** prove the Search index exists or is compatible.

Delete only this exact owned lab key after the exercise and verify that it is no longer required by subsequent lab steps; never delete shared business documents.

------------------------------------------------------------------------

# Part 28 --- JSON Index

## 31. Concept

A JSON index maps JSONPath expressions to Search field aliases.

Example structure:

``` text
$.name      -> name
$.category  -> category
$.status    -> status
$.price     -> price
```

Use exact `FT.CREATE ... ON JSON` syntax from the deployed product
documentation.

------------------------------------------------------------------------

# Part 29 --- JSONPath Coordination

## 32. Schema Contract

If application JSON changes:

``` text
$.price
```

to:

``` text
$.pricing.amount
```

the Search schema/query layer may also need to change.

Treat JSON paths as production contracts.

------------------------------------------------------------------------

# Part 30 --- Index Creation on Existing Data

## 33. Backfill

Creating an index over existing matching keys can require indexing work.

Plan for:

``` text
CPU
memory
duration
write workload
query behavior
```

Monitor indexing progress/state using supported metrics and commands.

------------------------------------------------------------------------

# Part 31 --- Indexing New Writes

## 34. Write Cost

An indexed write may involve:

``` text
update source object
extract indexed fields
update index structures
```

More indexed fields can mean more work.

------------------------------------------------------------------------

# Part 32 --- Write Amplification

## 35. Compare

Benchmark:

``` text
write without Search index
write with minimal index
write with broad index
```

Measure:

``` text
P99
CPU
memory
throughput
```

------------------------------------------------------------------------

# Part 33 --- Index Memory

## 36. Capacity

Search indexes consume memory beyond source key/value data.

Capacity planning must include:

``` text
source data
Search indexes
replication
working headroom
```

------------------------------------------------------------------------

# Part 34 --- Index Growth

## 37. Forecast

Track:

``` text
documents indexed
index memory
new documents/day
schema growth
sortable fields
text/tag cardinality
```

------------------------------------------------------------------------

# Part 35 --- High-Cardinality Fields

## 38. Review

Fields with many unique values can have different memory/query behavior
from low-cardinality fields.

Measure rather than guessing.

------------------------------------------------------------------------

# Part 36 --- TEXT Analysis

## 39. Query Semantics

TEXT behavior can include tokenization and language-related processing.

Validate:

``` text
case behavior
stemming
stop words
punctuation
language
```

against application requirements and exact product configuration.

------------------------------------------------------------------------

# Part 37 --- TAG Semantics

## 40. Exact Filtering

TAG is often better for fields such as:

``` text
tenant_id
status
category
region
```

when exact filtering is needed.

Validate separator/escaping behavior.

------------------------------------------------------------------------

# Part 38 --- Numeric Precision

## 41. Model Carefully

Ensure numeric representation is appropriate for:

``` text
prices
timestamps
scores
```

For money, application semantics and precision requirements must be
explicit.

------------------------------------------------------------------------

# Part 39 --- Query Construction

## 42. Do Not Concatenate Unsafely

User input should not be blindly inserted into query syntax.

Use:

``` text
validation
escaping
parameterization where supported
query-building library
```

according to the selected client/version.

------------------------------------------------------------------------

# Part 40 --- Query Limits

## 43. Guardrails

Application APIs should limit:

``` text
page size
query complexity
wildcards/prefixes where relevant
returned fields
timeout
```

Avoid allowing an external user to generate unbounded Search work.

------------------------------------------------------------------------

# Part 41 --- Wildcard / Broad Query

## 44. Cost Awareness

Queries matching very broad portions of the dataset can be expensive.

Benchmark representative broad queries and define application limits.

------------------------------------------------------------------------

# Part 42 --- Sorting

## 45. Query Design

Sorting can add work and schema/storage requirements.

Use only when needed.

Test:

``` text
filter only
filter + sort
```

------------------------------------------------------------------------

# Part 43 --- Aggregation Awareness

## 46. Separate Workload

Redis Search supports aggregation capabilities in supported versions.

Aggregation can be more expensive than simple lookup/filter queries.

Treat complex aggregations as a separate performance class.

------------------------------------------------------------------------

# Part 44 --- Query Classes

## 47. Define

Example:

``` text
Q1 exact TAG filter
Q2 TEXT search
Q3 numeric range
Q4 filter + sort
Q5 broad query
Q6 aggregation
```

Benchmark each class separately.

------------------------------------------------------------------------

# Part 45 --- Query SLO

## 48. Per Class

Define:

``` text
Q1 P99 < ...
Q2 P99 < ...
```

Do not hide expensive queries behind one global average.

------------------------------------------------------------------------

# Part 46 --- Client Integration

## 49. SDK

Validate the selected Redis client supports:

``` text
Search commands
response parsing
parameters
timeouts
TLS/auth
```

Pin and qualify client versions as covered in Chapter 53.

------------------------------------------------------------------------

# Part 47 --- Search Repository Layer

## 50. Centralize

Instead of scattering raw Search syntax through application code,
centralize:

``` text
index names
field names
query builders
escaping
pagination
response mapping
```

This simplifies schema evolution.

------------------------------------------------------------------------

# Part 48 --- Index Naming

## 51. Standard

Example:

``` text
idx:<service>:<entity>:v1
```

A versioned index name can help controlled schema transitions.

------------------------------------------------------------------------

# Part 49 --- Schema Change

## 52. Plan

Changing index schema can require:

``` text
new index
backfill/reindex
query validation
application switch
old index retirement
```

Do not assume every schema change can be performed in place safely.

------------------------------------------------------------------------

# Part 50 --- Blue/Green Index Pattern

## 53. Concept

``` text
idx:product:v1
idx:product:v2
```

Build and validate v2.

Switch application/query configuration.

Retire v1 after the rollback window.

Use only where supported and capacity allows both indexes temporarily.

------------------------------------------------------------------------

# Part 51 --- Dual Index Capacity

## 54. Important

During migration:

``` text
source data
+
old index
+
new index
```

may coexist.

Capacity must account for temporary peak memory.

------------------------------------------------------------------------

# Part 52 --- Index Drop

## 55. Caution

Understand whether an index-drop operation removes:

``` text
only index metadata
```

or can also delete underlying documents depending on command options.

Never execute destructive options without explicit validation.

------------------------------------------------------------------------

# Part 53 --- Index Rebuild

## 56. Plan

A rebuild procedure should include:

``` text
capacity
index creation
backfill
progress
query validation
cutover
rollback
old-index cleanup
```

------------------------------------------------------------------------

# Part 54 --- Data Migration

## 57. Search Is Part of Migration

When migrating Redis data, also inventory:

``` text
index definitions
JSON paths
prefixes
query clients
synonyms/dictionaries/configuration where used
```

Copying keys alone may not recreate Search behavior.

------------------------------------------------------------------------

# Part 55 --- Backup / Recovery

## 58. Validate

Understand what Redis Enterprise backup/restore preserves for the
deployed Search capability/version.

Recovery acceptance must validate:

``` text
documents
index definitions/state
queries
```

not only key count.

------------------------------------------------------------------------

# Part 56 --- HA / Failover

## 59. Test Search

During approved failover testing, include representative Search queries.

Measure:

``` text
errors
P99
reconnect
recovery
```

------------------------------------------------------------------------

# Part 57 --- Hot Query

## 60. Repeated Expensive Query

A single query pattern can consume disproportionate resources.

Observe query-class traffic and latency.

------------------------------------------------------------------------

# Part 58 --- Hot Tenant

## 61. Multi-Tenant

If one index serves multiple tenants, test tenant skew.

Protect against one tenant generating:

``` text
broad queries
deep pages
high QPS
```

------------------------------------------------------------------------

# Part 59 --- Query Caching at Application Layer

## 62. Consider Carefully

Frequently repeated deterministic query results may be cached by the
application where appropriate.

But caching adds:

``` text
invalidation
staleness
memory
complexity
```

Do not cache blindly.

------------------------------------------------------------------------

# Part 60 --- Observability

## 63. Index Metrics

Monitor supported indicators for:

``` text
index size/memory
document count
indexing state
indexing errors
```

------------------------------------------------------------------------

# Part 61 --- Query Metrics

## 64. Application Side

Track:

``` text
query class
QPS
P50/P95/P99
timeouts
errors
result count
page size
```

------------------------------------------------------------------------

# Part 62 --- Redis Metrics

## 65. Correlate

Track:

``` text
CPU
memory
network
connections
evictions
replication
persistence
```

Search latency must be interpreted with overall Redis health.

------------------------------------------------------------------------

# Part 63 --- Indexing Lag / Visibility

## 66. Validate Expectations

Where application correctness depends on newly written data becoming
searchable, measure actual visibility behavior for the deployed
product/version.

Define acceptable consistency semantics.

------------------------------------------------------------------------

# Part 64 --- Performance Baseline

## 67. Establish

For each query class record:

``` text
P50
P95
P99
successful QPS
result count
CPU
memory
network
```

------------------------------------------------------------------------

# Part 65 --- Dataset Scale

## 68. Test More Than Tiny Data

A query that is fast across 1,000 documents may behave differently
across millions.

Qualification should use a representative dataset scale or validated
extrapolation.

------------------------------------------------------------------------

# Part 66 --- Selectivity

## 69. Compare

Test queries that match:

``` text
0.01%
1%
10%
50%
```

of documents where relevant.

Broad-result queries may behave differently.

------------------------------------------------------------------------

# Part 67 --- Page Depth Test

## 70. Compare

Test:

``` text
first page
middle page
deep page
```

using the application's actual pagination strategy.

------------------------------------------------------------------------

# Part 68 --- Concurrent Query Test

## 71. Load

Run representative query classes concurrently.

Measure:

``` text
throughput
P99
CPU
errors
```

------------------------------------------------------------------------

# Part 69 --- Mixed Read/Write Search Test

## 72. Production-Like

Run:

``` text
Search queries
+
document updates
```

together.

Measure both query and write P99.

------------------------------------------------------------------------

# Part 70 --- Index Build Under Load

## 73. Qualification

Where operationally required, test building a new index while
representative traffic exists.

Define stop conditions.

------------------------------------------------------------------------

# Part 71 --- Failure Scenario 1

## 74. Wrong Prefix

Create an index using an incorrect lab prefix.

Expected:

``` text
documents missing
```

Validate diagnosis using index definition and key inspection.

------------------------------------------------------------------------

# Part 72 --- Failure Scenario 2

## 75. Wrong Field Type

Index/query a field using incompatible assumptions.

Validate schema/type troubleshooting.

------------------------------------------------------------------------

# Part 73 --- Failure Scenario 3

## 76. JSONPath Change

Change a synthetic JSON field path without updating the lab index.

Validate missing/stale query behavior.

------------------------------------------------------------------------

# Part 74 --- Failure Scenario 4

## 77. Broad Query

Run a controlled broad query against synthetic data.

Observe P99 and result volume.

------------------------------------------------------------------------

# Part 75 --- Failure Scenario 5

## 78. Deep Pagination

Run a controlled deep-page query.

Compare with shallow-page behavior.

------------------------------------------------------------------------

# Part 76 --- Failure Scenario 6

## 79. Hot Tenant

Generate high Search QPS from one synthetic tenant.

Observe resource and latency impact.

------------------------------------------------------------------------

# Part 77 --- Failure Scenario 7

## 80. Index Build Pressure

Create a new lab index over a representative synthetic dataset while
measuring CPU/memory/query P99.

------------------------------------------------------------------------

# Part 78 --- Failure Scenario 8

## 81. Memory Headroom

Create an additional lab index in an isolated environment.

Validate that capacity gates prevent unsafe memory exhaustion.

------------------------------------------------------------------------

# Part 79 --- Failure Scenario 9

## 82. Client Query Error

Send malformed Search syntax.

Validate:

``` text
clear application error
no infinite retry
no sensitive query logging
```

------------------------------------------------------------------------

# Part 80 --- Failure Scenario 10

## 83. Failover Under Search Load

Run approved Search load during failover.

Measure errors, P99, reconnects, and recovery.

------------------------------------------------------------------------

# Part 81 --- Troubleshooting Matrix

## 84. Common Problems

  Symptom                   Investigate
  ------------------------- --------------------------------------------
  document not found        prefix, schema, field/path, index state
  exact filter wrong        TEXT vs TAG, escaping
  numeric filter wrong      source type, schema type
  query slow                selectivity, sort, page depth, result size
  writes slow               number of indexes/fields, persistence, CPU
  memory high               index size, sortable fields, source data
  JSON fields missing       JSONPath/schema evolution
  one tenant impacts all    query QPS/complexity, isolation
  rebuild impacts latency   CPU/memory/headroom
  failover errors           client reconnect, timeout, retry

------------------------------------------------------------------------

# Part 82 --- Runbook 1: Index Design

## 85. Procedure

``` text
1. inventory query requirements.
2. identify source HASH/JSON.
3. define prefix.
4. classify fields.
5. select only required indexes.
6. define sorting.
7. estimate memory.
8. benchmark writes/queries.
9. review lifecycle.
10. approve.
```

------------------------------------------------------------------------

# Part 83 --- Runbook 2: Missing Document

## 86. Procedure

``` text
1. confirm source key exists.
2. confirm source type.
3. confirm index prefix.
4. confirm field/path.
5. confirm schema type.
6. inspect index state.
7. run minimal query.
8. correct and validate.
```

------------------------------------------------------------------------

# Part 84 --- Runbook 3: Slow Query

## 87. Procedure

``` text
1. classify query.
2. measure P99/result count.
3. inspect selectivity.
4. inspect sorting.
5. inspect pagination depth.
6. inspect returned fields.
7. inspect CPU/memory/network.
8. benchmark revised query.
```

------------------------------------------------------------------------

# Part 85 --- Runbook 4: High Index Memory

## 88. Procedure

``` text
1. measure source data.
2. measure index memory.
3. inventory indexed fields.
4. inventory sortable fields.
5. inspect unnecessary indexes.
6. estimate growth.
7. redesign if needed.
8. validate headroom.
```

------------------------------------------------------------------------

# Part 86 --- Runbook 5: Schema Change

## 89. Procedure

``` text
1. define target schema.
2. assess client/query compatibility.
3. estimate dual-index capacity.
4. build new index.
5. validate backfill.
6. validate queries.
7. switch clients.
8. retire old index after rollback window.
```

------------------------------------------------------------------------

# Part 87 --- Runbook 6: Index Rebuild

## 90. Procedure

``` text
1. confirm reason.
2. confirm capacity.
3. define stop conditions.
4. create replacement index.
5. monitor build.
6. validate document/query coverage.
7. cut over.
8. remove old index safely.
```

------------------------------------------------------------------------

# Part 88 --- Runbook 7: Search Incident

## 91. Procedure

``` text
1. confirm application impact.
2. classify query failures.
3. inspect Redis health.
4. inspect index state.
5. identify hot query/tenant.
6. reduce expensive traffic if required.
7. restore safe service.
8. preserve evidence/RCA.
```

------------------------------------------------------------------------

# Part 89 --- Runbook 8: Search Upgrade Validation

## 92. Procedure

``` text
1. record current behavior.
2. review release changes.
3. restore/build representative data.
4. run query regression suite.
5. run write benchmark.
6. run failover test.
7. canary application clients.
8. approve or rollback.
```

------------------------------------------------------------------------

# Part 90 --- Index Design Template

## 93. Record

``` text
Index:
Owner:
Source type:
Prefix:
Document count:
Growth:
Fields:
Field types:
Sortable fields:
Query classes:
Expected QPS:
P99 SLO:
Index memory:
Schema version:
Rebuild procedure:
Rollback:
```

------------------------------------------------------------------------

# Part 91 --- Query Template

## 94. Record

``` text
Query ID:
Purpose:
Filters:
TEXT fields:
TAG fields:
NUMERIC fields:
GEO fields:
Sort:
Page size:
Maximum page depth:
Returned fields:
Expected selectivity:
Expected QPS:
P99 SLO:
```

------------------------------------------------------------------------

# Part 92 --- Schema Change Template

## 95. Record

``` text
Current index:
Target index:
Reason:
Field additions:
Field removals:
Type changes:
JSONPath changes:
Capacity for coexistence:
Build plan:
Validation:
Client cutover:
Rollback:
Old-index retirement:
```

------------------------------------------------------------------------

# Part 93 --- Production Acceptance

## 96. Architecture

-   [ ] Search use case justified;
-   [ ] HASH/JSON source documented;
-   [ ] key prefix scoped;
-   [ ] query requirements documented;
-   [ ] index owner assigned.

## 97. Schema

-   [ ] TEXT fields justified;
-   [ ] TAG fields justified;
-   [ ] NUMERIC fields justified;
-   [ ] GEO fields justified where used;
-   [ ] sortable fields justified;
-   [ ] JSON paths validated;
-   [ ] schema versioning/change plan defined.

## 98. Performance

-   [ ] query classes benchmarked;
-   [ ] P50/P95/P99 recorded;
-   [ ] selectivity tested;
-   [ ] page depth tested;
-   [ ] mixed reads/writes tested;
-   [ ] indexed write cost measured;
-   [ ] index-build impact tested;
-   [ ] failover-under-load tested.

## 99. Capacity

-   [ ] source memory measured;
-   [ ] index memory measured;
-   [ ] replication/headroom included;
-   [ ] growth forecasted;
-   [ ] dual-index migration capacity validated;
-   [ ] stop conditions defined.

## 100. Operations

-   [ ] index metrics monitored;
-   [ ] query metrics monitored;
-   [ ] client errors classified;
-   [ ] rebuild runbook tested;
-   [ ] schema-change runbook tested;
-   [ ] backup/recovery Search validation defined;
-   [ ] ten failure scenarios completed;
-   [ ] eight production runbooks reviewed.

------------------------------------------------------------------------

# 101. Knowledge Validation

1.  Why should Search design start with query requirements?
2.  When is Search unnecessary?
3.  What source models can be indexed?
4.  Why are prefixes important?
5.  When should TEXT be used?
6.  When should TAG be used?
7.  When should NUMERIC be used?
8.  What is the cost of sortable fields?
9.  Why limit returned fields?
10. Why bound result sizes?
11. Why can deep pagination be expensive?
12. Why coordinate JSONPath with Search schema?
13. What happens when an index is created over existing data?
14. Why do indexes increase write cost?
15. Why must index memory be included in capacity planning?
16. Why test high-cardinality fields?
17. Why must user query input be escaped/validated?
18. Why define query classes?
19. Why have per-class SLOs?
20. Why centralize Search query construction?
21. Why version index names?
22. What is a blue/green index pattern?
23. Why does blue/green require extra memory?
24. Why is index-drop behavior operationally sensitive?
25. Why is Search part of migration planning?
26. Why validate Search after backup/restore?
27. Why test failover with Search traffic?
28. Why test query selectivity?
29. Why test mixed read/write workloads?
30. What must pass before a Search index is production-ready?

------------------------------------------------------------------------

# 102. Hands-On Acceptance Checklist

-   [ ] Created Chapter 56 HASH data.
-   [ ] Created scoped Search index.
-   [ ] Inspected index information.
-   [ ] Ran TEXT query.
-   [ ] Ran TAG filter.
-   [ ] Ran multiple filters.
-   [ ] Ran numeric range.
-   [ ] Ran sorted query.
-   [ ] Ran bounded query.
-   [ ] Tested return projection where supported.
-   [ ] Created JSON document where available.
-   [ ] Created/tested JSON index where available.
-   [ ] Tested existing-data index build.
-   [ ] Measured indexed write cost.
-   [ ] Measured index memory.
-   [ ] Tested high-cardinality behavior.
-   [ ] Tested query classes.
-   [ ] Tested page depths.
-   [ ] Tested selectivity.
-   [ ] Tested concurrent Search load.
-   [ ] Tested mixed Search/write load.
-   [ ] Tested index build under load.
-   [ ] Tested wrong prefix.
-   [ ] Tested wrong field type.
-   [ ] Tested JSONPath change.
-   [ ] Tested broad query.
-   [ ] Tested deep pagination.
-   [ ] Tested hot tenant.
-   [ ] Tested index memory stop conditions.
-   [ ] Tested malformed query handling.
-   [ ] Tested failover under Search load.
-   [ ] Completed eight runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 103. Cleanup

Inspect the lab index before removal:

``` bash
redis-cli FT.INFO idx:tutorial:chapter56:product
```

Remove only the confirmed Chapter 56 lab index using the exact supported
index-drop command and safe options for the deployed version.

Be especially careful with options that can delete underlying documents.

List Chapter 56 keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter56:*'
```

Review matches and remove confirmed disposable keys with `UNLINK`.

Never use `FLUSHDB` or `FLUSHALL` against a shared or production
database.

------------------------------------------------------------------------

# 104. Key Takeaways

1.  Redis Search is a secondary indexing/query capability over Redis
    data.
2.  Search design should begin with real query requirements.
3.  Exact-key workloads may not need Search.
4.  Scope indexes with deliberate key prefixes.
5.  TEXT and TAG solve different query problems.
6.  NUMERIC fields support numeric query requirements.
7.  Sortability has resource cost.
8.  Return only fields the application needs.
9.  Bound result sizes and pagination.
10. JSONPath becomes part of the Search schema contract.
11. Creating an index over existing data requires capacity and
    monitoring.
12. Every indexed field adds operational cost.
13. Search index memory must be included in capacity planning.
14. High-cardinality fields require measurement.
15. User-generated query syntax must be controlled.
16. Broad queries, sorting, aggregation, and deep pagination require
    qualification.
17. Define query classes and SLOs.
18. Centralize Search schema and query construction.
19. Versioned indexes can support controlled schema migration.
20. Blue/green index changes require temporary dual-index capacity.
21. Understand destructive index-drop options before execution.
22. Search definitions are part of migration and recovery planning.
23. Search must be tested during failover.
24. Mixed query/write tests are more representative than isolated tests.
25. Production readiness requires correctness, performance, capacity,
    lifecycle, observability, and recovery evidence together.

------------------------------------------------------------------------

# 105. References

Validate commands, field capabilities, query syntax, JSON integration,
lifecycle behavior, and metrics against the exact deployed Redis/Redis
Enterprise version and current official Redis documentation.

Recommended documentation areas:

-   Redis Search / Query Engine
-   FT.CREATE
-   FT.SEARCH
-   FT.INFO
-   FT.DROPINDEX
-   FT.AGGREGATE
-   RedisJSON integration
-   Search field types
-   query syntax
-   pagination and sorting
-   Redis Enterprise observability
-   Redis Enterprise sizing
-   Redis Enterprise backup/restore
-   Redis client libraries

------------------------------------------------------------------------

# Next Chapter

**Chapter 57 --- Redis Enterprise Vector Search, Embeddings & Semantic
Retrieval Engineering**

Chapter 57 will cover vector-search architecture, embeddings, vector
dimensions and distance metrics, HNSW/FLAT awareness, metadata filters,
hybrid search, ingestion pipelines, model/version compatibility, memory
and capacity, recall/latency tradeoffs, benchmarking, index lifecycle,
observability, failure scenarios, troubleshooting, runbooks, and
production acceptance.
