# Chapter 57 --- Redis Enterprise Vector Search, Embeddings & Semantic Retrieval Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 10 --- Migration, Data Services & Advanced Capabilities\
**Level:** Advanced → AI Retrieval / Production Search Engineering\
**Audience:** AI Engineers, Developers, SREs, DBREs, Platform Engineers,
Redis Administrators, Application Architects\
**Lab type:** Vector modeling, embeddings, FLAT/HNSW index design, KNN
retrieval, metadata filtering, hybrid search, ingestion, re-embedding,
memory/capacity, recall/latency benchmarking, RAG integration,
observability, failure injection, troubleshooting, runbooks, and
production acceptance

------------------------------------------------------------------------

# 1. Objective

Vector Search allows Redis to retrieve objects based on similarity
rather than only exact keys or lexical terms.

A typical architecture is:

``` text
source content
   |
embedding model
   |
vector
   |
Redis document
   |
vector index
   |
query vector
   |
K-nearest-neighbor search
   |
ranked results
```

For AI applications, this often becomes part of a retrieval pipeline:

``` text
user question
   |
embedding model
   |
query vector
   |
Redis Vector Search
   |
metadata filter / hybrid search
   |
top-K context
   |
LLM
   |
response
```

Production vector search is not only an index command.

You must engineer:

``` text
embedding model compatibility
vector dimensions
data type
distance metric
index algorithm
metadata
memory
recall
latency
ingestion
re-embedding
security
observability
recovery
```

By the end of this chapter, you should be able to:

-   explain vector-search architecture;
-   define embedding contracts;
-   choose vector dimensions and storage types;
-   choose a similarity metric;
-   understand FLAT and HNSW tradeoffs;
-   build vector schemas;
-   ingest vector documents;
-   execute KNN retrieval;
-   combine vector and metadata filters;
-   design hybrid lexical/vector retrieval;
-   measure recall and latency;
-   estimate vector/index memory;
-   manage embedding-model upgrades;
-   plan re-embedding;
-   integrate retrieval with RAG safely;
-   troubleshoot vector-search failures;
-   define production runbooks and acceptance gates.

------------------------------------------------------------------------

# 2. Core Production Principle

A vector has meaning only relative to the model and transformation that
created it.

Treat this as a contract:

``` text
embedding model
+
model version
+
preprocessing
+
dimension
+
numeric type
+
distance metric
=
vector compatibility contract
```

Do not mix incompatible embeddings in the same retrieval population
without an explicit design.

------------------------------------------------------------------------

# Part 1 --- What Is an Embedding?

## 3. Concept

An embedding converts content into a numeric vector.

Example:

``` text
"reset my password"
   |
embedding model
   |
[0.12, -0.44, 0.08, ...]
```

Semantically similar content should generally be represented closer in
the model's vector space.

------------------------------------------------------------------------

# Part 2 --- Vector Dimensions

## 4. Fixed Length

A model may produce vectors with a fixed dimension:

``` text
384
768
1024
1536
3072
...
```

The index definition must match the actual vector dimension.

A dimension mismatch is a correctness/configuration error.

------------------------------------------------------------------------

# Part 3 --- Numeric Representation

## 5. Vector Type

Common vector storage types include supported floating-point
representations such as:

``` text
FLOAT32
```

and other types where supported.

The type affects:

``` text
memory
precision
client serialization
compatibility
```

Use only types supported by the deployed Redis version and Search
capability.

------------------------------------------------------------------------

# Part 4 --- Raw Vector Memory

## 6. Approximation

For `FLOAT32`:

``` text
raw vector bytes
≈
dimension × 4
```

Example:

``` text
1536 × 4
=
6144 bytes
≈ 6 KB/vector
```

For one million vectors:

``` text
~6 GB
```

of raw vector payload alone.

This excludes:

``` text
key/document overhead
metadata
index structures
replication
allocator overhead
headroom
```

------------------------------------------------------------------------

# Part 5 --- Similarity Metrics

## 7. Purpose

A vector index needs a distance/similarity metric supported by the
product.

Common concepts include:

``` text
cosine
L2 / Euclidean
inner product
```

The correct metric depends on the embedding model and application
design.

------------------------------------------------------------------------

# Part 6 --- Metric Compatibility

## 8. Do Not Guess

If an embedding model is intended to use cosine similarity, changing to
another metric can change ranking behavior.

Record the metric as part of the embedding contract.

------------------------------------------------------------------------

# Part 7 --- Normalization

## 9. Model-Dependent

Some pipelines normalize vectors before storage/query.

Others do not.

Do not introduce normalization casually.

Use the embedding model's intended retrieval procedure and test it.

------------------------------------------------------------------------

# Part 8 --- Vector Source Object

## 10. Document Example

Conceptually:

``` json
{
  "id": "doc-1001",
  "title": "Password Reset Guide",
  "content": "Steps for resetting a user password...",
  "category": "support",
  "tenant": "acme",
  "embedding_model": "model-v1",
  "embedding": [0.12, -0.34, 0.56]
}
```

The vector is only one part of the retrieval object.

The three numeric values are illustrative only. Actual embedding dimensions, normalization, and index configuration must match the selected model and retrieval design.

------------------------------------------------------------------------

# Part 9 --- Metadata

## 11. Why

Metadata supports filtering and operational ownership.

Examples:

``` text
tenant
document type
language
region
access level
source
timestamp
embedding version
```

------------------------------------------------------------------------

# Part 10 --- Access-Control Metadata

## 12. Critical

Do not retrieve documents the user is not authorized to see.

Where vector retrieval serves protected content, authorization metadata
and application enforcement must be part of the query design.

Semantic similarity must never bypass access control.

------------------------------------------------------------------------

# Part 11 --- Key Design

## 13. Example

``` text
ai:kb:document:<id>
```

or an environment/service-specific namespace.

Do not put sensitive document text into key names.

------------------------------------------------------------------------

# Part 12 --- Lab Namespace

## 14. Safety

Use:

``` text
tutorial:chapter57:doc:<id>
```

and an isolated lab index:

``` text
idx:tutorial:chapter57:vector
```

------------------------------------------------------------------------

# Part 13 --- Source Model

## 15. HASH or JSON

Vector fields can be associated with supported source structures such as
HASH or JSON depending on the deployed product capabilities.

Choose based on:

``` text
document model
metadata
application updates
Search schema
client support
```

------------------------------------------------------------------------

# Part 14 --- FLAT Index

## 16. Concept

A FLAT vector search approach conceptually compares the query against
the candidate vector population more directly.

Advantages can include:

``` text
high exactness
simple recall behavior
```

Tradeoff:

``` text
search cost grows with vector population
```

Use exact vendor documentation for algorithm behavior and supported
configuration.

------------------------------------------------------------------------

# Part 15 --- HNSW Index

## 17. Concept

HNSW is an approximate nearest-neighbor graph-based approach.

Advantages:

``` text
fast retrieval at larger scale
```

Tradeoffs:

``` text
additional index memory
build/update cost
recall vs latency tuning
```

------------------------------------------------------------------------

# Part 16 --- FLAT vs HNSW

## 18. Decision

Compare:

``` text
dataset size
latency SLO
recall target
memory
write/update rate
build time
operational complexity
```

Do not choose HNSW merely because it is commonly used.

------------------------------------------------------------------------

# Part 17 --- Recall

## 19. Definition

Recall measures whether approximate search returns the relevant
neighbors expected from a trusted reference.

Conceptually:

``` text
recall@K
=
relevant expected neighbors returned
/
relevant expected neighbors
```

Define the exact evaluation method for your application.

------------------------------------------------------------------------

# Part 18 --- Latency vs Recall

## 20. Tradeoff

Approximate search tuning often trades:

``` text
more search effort
   ->
better recall
   ->
more latency/CPU
```

Production qualification must evaluate both.

------------------------------------------------------------------------

# Part 19 --- HNSW Build Parameters

## 21. Awareness

HNSW implementations expose parameters that influence:

``` text
graph connectivity
construction effort
memory
recall
```

Use exact Redis documentation for the deployed version.

Do not copy tuning values from unrelated datasets.

------------------------------------------------------------------------

# Part 20 --- Runtime Search Parameters

## 22. Awareness

Supported runtime parameters can affect how much work approximate search
performs.

Benchmark:

``` text
latency
recall
CPU
```

together.

------------------------------------------------------------------------

# Part 21 --- Vector Index Schema

## 23. Concept

A vector schema defines:

``` text
source field/path
algorithm
numeric type
dimension
distance metric
algorithm parameters
```

This schema must match the embedding pipeline exactly.

------------------------------------------------------------------------

# Part 22 --- Example Schema Concept

## 24. Pseudocode

A representative Search index may conceptually include:

``` text
title      TEXT
category   TAG
tenant     TAG
model      TAG
embedding  VECTOR HNSW
```

with vector attributes such as:

``` text
TYPE FLOAT32
DIM <dimension>
DISTANCE_METRIC COSINE
```

Use exact current `FT.CREATE` syntax for the deployed Redis version.

------------------------------------------------------------------------

# Part 23 --- Binary Encoding

## 25. Client Responsibility

Vector query/storage values are often transferred in binary numeric
representation.

The client must correctly encode:

``` text
numeric type
endianness/representation expected by client/server
dimension
```

Use the selected SDK's supported vector API/examples.

------------------------------------------------------------------------

# Part 24 --- Python Vector Encoding Lab

## 26. Example

For a synthetic `FLOAT32` vector:

``` python
import numpy as np

vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
blob = vector.tobytes()
```

The index dimension in this example must be:

``` text
4
```

Use synthetic vectors for the lab.

------------------------------------------------------------------------

# Part 25 --- Synthetic Vector Dataset

## 27. Build

Create a small deterministic dataset.

Example conceptual vectors:

``` text
doc1 [1.0, 0.0, 0.0, 0.0]
doc2 [0.9, 0.1, 0.0, 0.0]
doc3 [0.0, 1.0, 0.0, 0.0]
doc4 [0.0, 0.0, 1.0, 0.0]
```

This makes expected similarity easier to reason about.

------------------------------------------------------------------------

# Part 26 --- KNN Search

## 28. Concept

K-nearest-neighbor search asks:

``` text
return the K vectors closest to query vector Q
```

Example:

``` text
K = 10
```

Do not set K much larger than the application actually needs without
qualification.

------------------------------------------------------------------------

# Part 27 --- Distance Score

## 29. Interpret Correctly

Search results can include a distance/similarity score depending on
query configuration.

Do not assume:

``` text
higher always means better
```

or:

``` text
lower always means better
```

without understanding the chosen metric and API semantics.

------------------------------------------------------------------------

# Part 28 --- Top-K

## 30. Application Design

A RAG system may retrieve:

``` text
top 5
top 10
top 20
```

More results increase:

``` text
Redis work
network
reranking work
LLM context
token cost
```

Benchmark retrieval quality and total application cost.

------------------------------------------------------------------------

# Part 29 --- Metadata Filtering

## 31. Example

Before vector similarity, restrict candidates to:

``` text
tenant = acme
category = support
language = en
```

This can improve:

``` text
security
relevance
efficiency
```

depending on the workload and query plan.

------------------------------------------------------------------------

# Part 30 --- Tenant Filter

## 32. Mandatory Where Required

For multi-tenant data:

``` text
vector similarity
```

must not replace:

``` text
tenant authorization
```

Enforce tenant boundaries.

------------------------------------------------------------------------

# Part 31 --- Hybrid Search

## 33. Concept

Hybrid retrieval combines:

``` text
lexical/metadata criteria
+
vector similarity
```

Example:

``` text
category = documentation
AND
semantic similarity to "password reset"
```

------------------------------------------------------------------------

# Part 32 --- Lexical + Semantic

## 34. Why

Vector search can capture semantic similarity.

TEXT search can capture exact terms.

Combining them can improve retrieval for some applications.

Measure quality rather than assuming hybrid is always better.

------------------------------------------------------------------------

# Part 33 --- Reranking

## 35. Optional Layer

A retrieval architecture may use:

``` text
Redis top 50
   |
reranker
   |
top 5
```

Reranking can improve quality but adds:

``` text
latency
compute
cost
dependency
```

------------------------------------------------------------------------

# Part 34 --- Chunking

## 36. RAG Data Modeling

Long documents are often divided into chunks before embedding.

Chunk design affects:

``` text
retrieval quality
vector count
memory
context quality
```

------------------------------------------------------------------------

# Part 35 --- Chunk Size

## 37. Tradeoff

Very large chunks:

``` text
fewer vectors
less precise retrieval
more context per hit
```

Very small chunks:

``` text
more vectors
more memory
potentially better localization
less context per hit
```

Benchmark on real evaluation questions.

------------------------------------------------------------------------

# Part 36 --- Chunk Overlap

## 38. Tradeoff

Overlap can preserve context across boundaries.

But it increases:

``` text
vector count
memory
duplicate retrieval
ingestion cost
```

------------------------------------------------------------------------

# Part 37 --- Document-to-Chunk Relationship

## 39. Metadata

Store enough metadata to reconstruct:

``` text
source document
chunk order
source URL/reference
version
tenant
```

without exposing unauthorized data.

------------------------------------------------------------------------

# Part 38 --- Embedding Pipeline

## 40. Flow

``` text
source
 -> extract
 -> clean
 -> chunk
 -> embed
 -> validate dimension
 -> write Redis
 -> index
 -> validate retrieval
```

Every step should be observable.

------------------------------------------------------------------------

# Part 39 --- Embedding Model Version

## 41. Store It

Record model/version with each vector or dataset generation.

Example:

``` text
embedding_model = support-embedding-v3
```

This makes migrations and debugging possible.

------------------------------------------------------------------------

# Part 40 --- Preprocessing Version

## 42. Also Important

Changes to:

``` text
cleaning
chunking
normalization
language handling
```

can change vectors even if the model name is unchanged.

Version the preprocessing pipeline when necessary.

------------------------------------------------------------------------

# Part 41 --- Model Upgrade

## 43. Do Not Mix Blindly

Old vectors:

``` text
model-v1
```

New query:

``` text
model-v2
```

may not be comparable.

Treat embedding-model upgrades as data migrations.

------------------------------------------------------------------------

# Part 42 --- Re-Embedding Strategy

## 44. Pattern

``` text
build new embeddings
write to new field/index/population
validate
compare retrieval quality
switch queries
retain rollback window
retire old vectors/index
```

------------------------------------------------------------------------

# Part 43 --- Blue/Green Vector Index

## 45. Example

``` text
idx:kb:vector:v1
idx:kb:vector:v2
```

This can support model/schema transitions if sufficient capacity exists.

------------------------------------------------------------------------

# Part 44 --- Dual-Index Capacity

## 46. Critical

During re-embedding:

``` text
old vectors/index
+
new vectors/index
```

may coexist.

This can require substantial temporary memory.

Capacity-plan before migration.

------------------------------------------------------------------------

# Part 45 --- Incremental Ingestion

## 47. New/Changed Content

The pipeline should support:

``` text
new document
updated document
deleted document
```

Do not rebuild the entire corpus for every small change unless
intentionally designed.

------------------------------------------------------------------------

# Part 46 --- Deletion

## 48. Propagate

If source content is removed, define how Redis vector documents/index
entries are removed.

This matters for:

``` text
correctness
security
retention
```

------------------------------------------------------------------------

# Part 47 --- Stale Embeddings

## 49. Detect

A source document can change while its vector remains old.

Track:

``` text
source version/hash
embedding timestamp
embedding model
```

to identify stale vectors.

------------------------------------------------------------------------

# Part 48 --- Idempotent Ingestion

## 50. Design

Repeated ingestion of the same source version should not create
uncontrolled duplicate chunks/vectors.

Use deterministic identifiers where appropriate.

------------------------------------------------------------------------

# Part 49 --- Ingestion Errors

## 51. Classify

Examples:

``` text
source fetch failure
parse failure
embedding API failure
dimension mismatch
Redis write failure
indexing failure
metadata validation failure
```

------------------------------------------------------------------------

# Part 50 --- Retry

## 52. Bounded

Embedding generation can be expensive.

Use:

``` text
bounded retry
backoff
jitter
idempotency
dead-letter/recovery workflow
```

------------------------------------------------------------------------

# Part 51 --- Embedding API Rate Limit

## 53. Protect

External embedding services may enforce:

``` text
requests/min
tokens/min
concurrency
```

The ingestion pipeline should apply backpressure.

------------------------------------------------------------------------

# Part 52 --- Secrets

## 54. Protect

Do not store embedding API credentials:

``` text
inside Redis documents
in source code
in logs
```

Use approved secret management.

------------------------------------------------------------------------

# Part 53 --- Sensitive Content

## 55. Data Governance

Before embedding content, determine whether the source is permitted to
be sent to the selected embedding service and stored in Redis.

Apply:

``` text
classification
tenant boundaries
retention
access control
audit
```

------------------------------------------------------------------------

# Part 54 --- Retrieval Authorization

## 56. Defense in Depth

Authorization should be enforced by application logic and appropriate
metadata filters.

Do not trust semantic ranking to preserve access boundaries.

------------------------------------------------------------------------

# Part 55 --- Prompt Injection Boundary

## 57. RAG Safety

Retrieved text is data, not trusted instructions.

A malicious document can contain:

``` text
"ignore previous instructions..."
```

The application/LLM layer must treat retrieved content as untrusted
context.

Redis Vector Search retrieves content; it does not make content
trustworthy.

------------------------------------------------------------------------

# Part 56 --- Retrieval Quality Dataset

## 58. Build

Create a labeled evaluation set:

``` text
question
expected relevant documents/chunks
```

Use it to measure:

``` text
recall@K
precision-related metrics where appropriate
MRR/NDCG where useful
```

Choose metrics that match the application.

------------------------------------------------------------------------

# Part 57 --- Ground-Truth Search

## 59. Reference

For approximate-search evaluation, use a trusted reference
method/dataset to estimate expected nearest neighbors.

For small datasets, exact/FLAT-style evaluation can be useful where
supported.

------------------------------------------------------------------------

# Part 58 --- Recall@K

## 60. Example

If expected relevant chunks are:

``` text
A, B, C
```

and top-K returns:

``` text
A, C, D
```

then the evaluation should calculate recall according to the defined
ground-truth methodology.

Be consistent across tests.

------------------------------------------------------------------------

# Part 59 --- Latency

## 61. Record

For each query class:

``` text
P50
P95
P99
```

Also record:

``` text
K
filters
algorithm
dataset size
concurrency
```

------------------------------------------------------------------------

# Part 60 --- Query Classes

## 62. Example

``` text
V1 vector only
V2 vector + tenant filter
V3 vector + metadata filters
V4 hybrid TEXT + vector
V5 high-K retrieval
```

Benchmark separately.

------------------------------------------------------------------------

# Part 61 --- Dataset Scale

## 63. Important

Test at representative vector counts.

Performance across:

``` text
10,000 vectors
```

does not automatically predict:

``` text
100 million vectors
```

------------------------------------------------------------------------

# Part 62 --- Memory Model

## 64. Estimate

Conceptually:

``` text
raw vectors
+
source documents
+
vector index
+
metadata indexes
+
replication
+
allocator overhead
+
headroom
```

Use measured Redis Enterprise metrics for final capacity decisions.

------------------------------------------------------------------------

# Part 63 --- HNSW Memory

## 65. Additional Structure

HNSW requires graph/index structures beyond raw vectors.

Measure actual index memory with representative data and configuration.

------------------------------------------------------------------------

# Part 64 --- Replication

## 66. Capacity

HA replicas can multiply the physical memory/storage/network
requirements of vector data/indexes.

Include redundancy in sizing.

------------------------------------------------------------------------

# Part 65 --- Growth

## 67. Forecast

Track:

``` text
new source documents/day
chunks/document
vectors/day
average vector bytes
index growth
retention/deletion
```

------------------------------------------------------------------------

# Part 66 --- Query Concurrency

## 68. Test

Increase concurrent vector queries gradually.

Measure:

``` text
successful QPS
P99
CPU
memory
network
errors
```

------------------------------------------------------------------------

# Part 67 --- Top-K Scaling

## 69. Test

Compare:

``` text
K=5
K=10
K=50
K=100
```

Measure both retrieval quality and system cost.

------------------------------------------------------------------------

# Part 68 --- Filter Selectivity

## 70. Test

Compare metadata filters matching:

``` text
0.1%
1%
10%
50%
```

of the corpus.

------------------------------------------------------------------------

# Part 69 --- Hybrid Query Test

## 71. Measure

Compare:

``` text
vector only
lexical only
hybrid
```

for:

``` text
quality
P99
CPU
```

------------------------------------------------------------------------

# Part 70 --- Ingestion Benchmark

## 72. Measure

Track:

``` text
embeddings/sec
Redis writes/sec
indexing throughput
CPU
memory
network
errors
```

------------------------------------------------------------------------

# Part 71 --- Query + Ingestion

## 73. Production-Like

Run retrieval while new vectors are ingested.

Measure:

``` text
query P99
ingestion throughput
CPU
memory
```

------------------------------------------------------------------------

# Part 72 --- Index Build

## 74. Qualification

Building a large vector index can consume substantial resources.

Plan:

``` text
capacity
duration
query impact
write impact
stop conditions
```

------------------------------------------------------------------------

# Part 73 --- Failover Under Vector Load

## 75. Test

During an approved nonproduction failover:

``` text
run vector queries
measure errors
measure P99
measure reconnect
measure recovery
```

------------------------------------------------------------------------

# Part 74 --- Backup / Recovery

## 76. Validate

Recovery acceptance must verify:

``` text
source documents
vector fields
index definitions/state
query correctness
```

not merely key count.

------------------------------------------------------------------------

# Part 75 --- Migration

## 77. Inventory

For vector workloads record:

``` text
embedding model
dimension
type
distance metric
algorithm
index parameters
metadata schema
document count
index memory
```

This is part of the migration contract.

------------------------------------------------------------------------

# Part 76 --- Observability

## 78. Retrieval Metrics

Track:

``` text
vector QPS
P50/P95/P99
errors
K
result count
query class
filters
```

------------------------------------------------------------------------

# Part 77 --- Quality Metrics

## 79. Track Offline / Controlled Evaluation

``` text
recall@K
retrieval success
no-result rate
relevance evaluation
```

Infrastructure metrics alone cannot prove retrieval quality.

------------------------------------------------------------------------

# Part 78 --- Ingestion Metrics

## 80. Track

``` text
documents discovered
chunks created
embedding successes/failures
dimension failures
Redis write failures
indexing failures
stale vectors
ingestion lag
```

------------------------------------------------------------------------

# Part 79 --- Model Metadata

## 81. Dashboard

Expose:

``` text
active embedding model/version
active vector index
dimension
algorithm
last re-embedding
```

This helps incident diagnosis.

------------------------------------------------------------------------

# Part 80 --- Failure Scenario 1

## 82. Dimension Mismatch

Send a vector with the wrong dimension.

Expected:

``` text
fail fast
classify error
do not retry indefinitely
```

------------------------------------------------------------------------

# Part 81 --- Failure Scenario 2

## 83. Wrong Numeric Type

Encode the query vector using an incompatible numeric representation.

Validate client-side contract checks.

------------------------------------------------------------------------

# Part 82 --- Failure Scenario 3

## 84. Wrong Model

Generate query vectors with model v2 against a model-v1 corpus.

Measure retrieval-quality degradation.

------------------------------------------------------------------------

# Part 83 --- Failure Scenario 4

## 85. Missing Tenant Filter

In a synthetic multi-tenant dataset, intentionally omit the tenant
filter.

Validate security tests detect cross-tenant candidates.

------------------------------------------------------------------------

# Part 84 --- Failure Scenario 5

## 86. High K

Request an unnecessarily large K.

Measure latency, response size, and downstream context cost.

------------------------------------------------------------------------

# Part 85 --- Failure Scenario 6

## 87. Broad Metadata Filter

Run a low-selectivity query.

Observe CPU/P99.

------------------------------------------------------------------------

# Part 86 --- Failure Scenario 7

## 88. Ingestion Backlog

Throttle embedding generation or Redis writes.

Validate backlog/lag alerting and backpressure.

------------------------------------------------------------------------

# Part 87 --- Failure Scenario 8

## 89. Duplicate Ingestion

Replay the same synthetic source batch.

Validate deterministic/idempotent behavior.

------------------------------------------------------------------------

# Part 88 --- Failure Scenario 9

## 90. Re-Embedding Capacity Pressure

Create a second lab vector population/index.

Validate dual-index memory stop conditions.

------------------------------------------------------------------------

# Part 89 --- Failure Scenario 10

## 91. Failover Under Query Load

Run approved vector traffic during failover.

Validate client recovery and retrieval availability.

------------------------------------------------------------------------

# Part 90 --- Troubleshooting Matrix

## 92. Common Problems

  Symptom                         Investigate
  ------------------------------- -----------------------------------------
  no vector results               index, field/path, query syntax, data
  dimension error                 model output vs schema
  poor relevance                  model, preprocessing, metric, chunking
  high P99                        K, algorithm, filters, concurrency, CPU
  memory high                     vector dimension, count, HNSW, replicas
  wrong tenant results            missing/incorrect authorization filter
  new content missing             ingestion lag, write/indexing failure
  quality dropped after upgrade   mixed embedding models/preprocessing
  reindex causes pressure         dual-index capacity, build load
  failover errors                 client reconnect, timeout, retry

------------------------------------------------------------------------

# Part 91 --- Runbook 1: Vector Index Design

## 93. Procedure

``` text
1. define retrieval use case.
2. select embedding model.
3. record model/version.
4. record dimension/type.
5. select distance metric.
6. choose FLAT/HNSW.
7. define metadata filters.
8. estimate memory.
9. benchmark recall/latency.
10. approve.
```

------------------------------------------------------------------------

# Part 92 --- Runbook 2: Poor Retrieval Quality

## 94. Procedure

``` text
1. reproduce evaluation query.
2. verify model/version.
3. verify preprocessing.
4. verify dimension/metric.
5. inspect chunking.
6. inspect metadata filters.
7. compare exact/reference results.
8. retune/re-embed and re-evaluate.
```

------------------------------------------------------------------------

# Part 93 --- Runbook 3: Slow Vector Query

## 95. Procedure

``` text
1. classify query.
2. record K.
3. record filters/selectivity.
4. record algorithm/settings.
5. inspect CPU/memory/network.
6. compare concurrency.
7. benchmark tuning.
8. validate recall after optimization.
```

------------------------------------------------------------------------

# Part 94 --- Runbook 4: Ingestion Failure

## 96. Procedure

``` text
1. identify failed pipeline stage.
2. validate source.
3. validate embedding service.
4. validate dimension/type.
5. validate Redis write.
6. validate index visibility.
7. replay idempotently.
8. confirm lag recovered.
```

------------------------------------------------------------------------

# Part 95 --- Runbook 5: Embedding Model Upgrade

## 97. Procedure

``` text
1. define target model contract.
2. estimate dual-index capacity.
3. build new embeddings.
4. build new index/population.
5. run quality benchmark.
6. run performance benchmark.
7. canary query traffic.
8. switch and retain rollback window.
```

------------------------------------------------------------------------

# Part 96 --- Runbook 6: Vector Memory Pressure

## 98. Procedure

``` text
1. measure vector count.
2. measure dimension/type.
3. measure source/index memory.
4. inspect replicas.
5. inspect dual indexes.
6. forecast growth.
7. reduce unsafe growth or scale.
8. validate headroom.
```

------------------------------------------------------------------------

# Part 97 --- Runbook 7: Cross-Tenant Retrieval

## 99. Procedure

``` text
1. stop affected query path if required.
2. identify missing/incorrect filter.
3. preserve evidence.
4. validate authorization logic.
5. correct query construction.
6. test tenant isolation.
7. redeploy safely.
8. complete security incident process.
```

------------------------------------------------------------------------

# Part 98 --- Runbook 8: Vector Recovery Validation

## 100. Procedure

``` text
1. restore/recover approved environment.
2. validate document count.
3. validate vector fields.
4. validate index definition/state.
5. run known KNN queries.
6. run metadata isolation tests.
7. run recall/performance sample.
8. record recovery acceptance.
```

------------------------------------------------------------------------

# Part 99 --- Vector Design Template

## 101. Record

``` text
Use case:
Owner:
Source:
Document/chunk key:
Embedding model:
Model version:
Preprocessing version:
Dimension:
Numeric type:
Distance metric:
Algorithm:
Index parameters:
Metadata filters:
Tenant isolation:
Expected vectors:
Growth/day:
K:
Recall target:
P99 SLO:
```

------------------------------------------------------------------------

# Part 100 --- Re-Embedding Template

## 102. Record

``` text
Current model:
Target model:
Current dimension:
Target dimension:
Current index:
Target index:
Documents:
Chunks:
Temporary memory:
Ingestion duration:
Quality gate:
Performance gate:
Canary:
Rollback:
Old-index retirement:
```

------------------------------------------------------------------------

# Part 101 --- RAG Retrieval Template

## 103. Record

``` text
Question type:
Embedding model:
Tenant/security filter:
Metadata filters:
Vector K:
Lexical criteria:
Hybrid strategy:
Reranker:
Final context count:
Max context size:
Retrieval timeout:
Fallback:
Quality metric:
```

------------------------------------------------------------------------

# Part 102 --- Production Acceptance

## 104. Embedding Contract

-   [ ] model/version recorded;
-   [ ] preprocessing recorded;
-   [ ] dimension validated;
-   [ ] numeric type validated;
-   [ ] metric validated;
-   [ ] mixed-model prevention defined.

## 105. Data Model

-   [ ] key/chunk model documented;
-   [ ] source relationship stored;
-   [ ] metadata defined;
-   [ ] tenant/access metadata defined;
-   [ ] deletion propagation defined;
-   [ ] stale-vector detection defined.

## 106. Index

-   [ ] FLAT/HNSW decision documented;
-   [ ] parameters benchmarked;
-   [ ] memory measured;
-   [ ] growth forecasted;
-   [ ] replication/headroom included;
-   [ ] rebuild/recovery procedure defined.

## 107. Quality

-   [ ] labeled evaluation set exists;
-   [ ] recall@K or appropriate metric measured;
-   [ ] chunking evaluated;
-   [ ] K evaluated;
-   [ ] metadata/hybrid strategy evaluated;
-   [ ] model upgrade quality gate defined.

## 108. Performance

-   [ ] P50/P95/P99 recorded;
-   [ ] concurrency tested;
-   [ ] K scaling tested;
-   [ ] filter selectivity tested;
-   [ ] query + ingestion tested;
-   [ ] failover-under-load tested;
-   [ ] dual-index capacity tested.

## 109. Security / Operations

-   [ ] tenant isolation tested;
-   [ ] sensitive-content policy reviewed;
-   [ ] secrets externalized;
-   [ ] retrieved content treated as untrusted context;
-   [ ] ingestion metrics monitored;
-   [ ] retrieval metrics monitored;
-   [ ] quality metrics monitored;
-   [ ] ten failure scenarios completed;
-   [ ] eight runbooks reviewed.

------------------------------------------------------------------------

# 110. Knowledge Validation

1.  What is an embedding?
2.  Why is vector dimension fixed by the model?
3.  How do you estimate raw FLOAT32 vector bytes?
4.  Why must the distance metric match the embedding design?
5.  Why might normalization matter?
6.  Why store metadata with vectors?
7.  Why is tenant filtering a security requirement?
8.  What is FLAT search?
9.  What is HNSW?
10. What is recall@K?
11. Why is there a recall/latency tradeoff?
12. What belongs in the vector schema contract?
13. Why must binary vector encoding match the schema?
14. What does top-K mean?
15. Why can large K be expensive?
16. What is hybrid search?
17. What is reranking?
18. Why does chunk size matter?
19. Why does chunk overlap increase capacity?
20. Why store embedding-model version?
21. Why treat model upgrades as migrations?
22. What is blue/green vector indexing?
23. Why is dual-index capacity important?
24. How do stale embeddings occur?
25. Why should ingestion be idempotent?
26. Why is a quality evaluation dataset required?
27. Why are infrastructure metrics insufficient for retrieval quality?
28. Why test query and ingestion concurrently?
29. Why treat retrieved RAG content as untrusted?
30. What must pass before a vector-search workload is production-ready?

------------------------------------------------------------------------

# 111. Hands-On Acceptance Checklist

-   [ ] Defined vector use case.
-   [ ] Recorded embedding contract.
-   [ ] Calculated raw vector size.
-   [ ] Created synthetic FLOAT32 vectors.
-   [ ] Created isolated lab documents.
-   [ ] Created FLAT or HNSW lab index where supported.
-   [ ] Ran KNN query.
-   [ ] Inspected distance scores.
-   [ ] Tested K values.
-   [ ] Tested metadata filter.
-   [ ] Tested tenant filter.
-   [ ] Tested hybrid query where supported.
-   [ ] Created chunk metadata.
-   [ ] Tested idempotent ingestion.
-   [ ] Tested stale-vector detection.
-   [ ] Built retrieval-quality dataset.
-   [ ] Measured recall/quality.
-   [ ] Recorded P50/P95/P99.
-   [ ] Tested query concurrency.
-   [ ] Tested filter selectivity.
-   [ ] Tested query + ingestion.
-   [ ] Measured index memory.
-   [ ] Tested dual-index capacity.
-   [ ] Tested dimension mismatch.
-   [ ] Tested wrong numeric type.
-   [ ] Tested wrong embedding model.
-   [ ] Tested missing tenant filter.
-   [ ] Tested high K.
-   [ ] Tested ingestion backlog.
-   [ ] Tested duplicate ingestion.
-   [ ] Tested failover under vector load.
-   [ ] Completed eight runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 112. Cleanup

Inspect the Chapter 57 lab vector index before removal.

Remove only the confirmed lab index using the exact safe index-drop
syntax for the deployed Redis version.

Be careful with any option that can delete underlying documents.

List lab keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter57:*'
```

Review matches and remove confirmed disposable keys with `UNLINK`.

Remove temporary:

``` text
synthetic embedding files
load generators
evaluation datasets containing test-only data
temporary credentials
temporary dashboards/alerts
test indexes
```

Never use `FLUSHDB` or `FLUSHALL` against a shared or production
database.

------------------------------------------------------------------------

# 113. Key Takeaways

1.  Vector search is a complete retrieval system, not merely a vector
    field.
2.  Embedding model/version, preprocessing, dimension, type, and metric
    form a compatibility contract.
3.  Raw vector memory can be substantial even before index overhead.
4.  FLAT and HNSW have different scale, recall, latency, and memory
    characteristics.
5.  Approximate retrieval must be measured for recall as well as
    latency.
6.  Metadata is essential for relevance, ownership, and security.
7.  Tenant authorization must not depend on semantic similarity.
8.  Top-K affects Redis load, network, reranking, and LLM context cost.
9.  Hybrid lexical/vector retrieval should be evaluated rather than
    assumed superior.
10. Chunking strongly affects quality and capacity.
11. Chunk overlap increases vector count and duplicate context risk.
12. Embedding model version should be stored and observable.
13. Model upgrades are data migrations.
14. Blue/green vector indexes can reduce migration risk but require
    temporary capacity.
15. Ingestion should support new, changed, and deleted content.
16. Stale vectors need explicit detection.
17. Ingestion should be idempotent and backpressured.
18. Sensitive-content and embedding-provider policies must be reviewed.
19. Retrieved RAG content is untrusted context.
20. A labeled evaluation set is required for retrieval-quality
    measurement.
21. Query classes should include K, filters, algorithm, and dataset
    size.
22. Vector capacity includes documents, indexes, metadata, replicas, and
    headroom.
23. Query + ingestion concurrency should be qualified.
24. Recovery must validate retrieval correctness, not just key
    restoration.
25. Production acceptance requires quality, latency, capacity, security,
    ingestion, recovery, and operational evidence together.

------------------------------------------------------------------------

# 114. References

Validate vector syntax, algorithms, parameters, field types, query
options, and lifecycle behavior against the exact deployed Redis/Redis
Enterprise version and current official Redis documentation.

Recommended documentation areas:

-   Redis Vector Search
-   Redis Search / Query Engine
-   vector field definitions
-   KNN queries
-   FLAT vector indexes
-   HNSW vector indexes
-   hybrid queries and filters
-   RedisJSON integration
-   Redis Enterprise sizing and observability
-   Redis Enterprise backup/restore
-   Redis client vector examples
-   embedding-model provider documentation
-   application security and data-governance standards

------------------------------------------------------------------------

# Next Chapter

**Chapter 58 --- Redis Enterprise Vector Search Performance, Capacity &
Retrieval Quality Engineering**

Chapter 58 will deepen vector operations with large-scale capacity
modeling, HNSW tuning, recall/latency curves, concurrency, filter
selectivity, vector-memory forecasting, ingestion/query contention, hot
tenants, index-build/rebuild qualification, production SLOs, regression
testing, failure engineering, and operational runbooks.
