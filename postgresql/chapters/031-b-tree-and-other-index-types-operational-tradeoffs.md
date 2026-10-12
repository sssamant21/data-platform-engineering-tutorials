# Chapter 031 — B-tree and Other Index Types: Operational Tradeoffs

**Audience:** DBRE and SRE only. **Baseline:** PostgreSQL 18. **Outcome:** select an access method from query semantics and validate its read benefit against storage, writes, maintenance and deployment risk.

## 1. Index selection starts with the operation

An index adds a maintained access path. It does not replace planner statistics or guarantee a faster query. Record the predicate, operator, column type, ordering, result fraction, representative parameters, concurrency and service objective before choosing a method.

Use Chapter 030's investigation process to establish the bottleneck. Adding indexes during a blocking incident can add load and new lock conflicts without addressing the cause.

## 2. Compare the built-in methods

| Method | Starting use case | Important boundary |
|---|---|---|
| B-tree | Equality, ranges and ordered retrieval | Usually the first candidate for sortable scalar values |
| Hash | Equality-only lookup | No range or ordinary ordered retrieval; benchmark against B-tree |
| GIN | Membership/containment over multiple components, such as arrays | Operator class determines supported predicates; update fan-out matters |
| GiST | Range/geometric/domain-specific searches | Semantics, recheck behavior and distance ordering depend on operator class |
| SP-GiST | Partitioned search structures, such as points or prefixes | Data distribution and supported class determine suitability |
| BRIN | Large physically correlated data, often time-ordered ingestion | Range summaries filter candidate blocks; not precise tuple locations |

Extensions can provide other methods/classes, such as bloom, trigram or spatial indexing. Confirm installation, support, backup/restore and upgrade compatibility before adopting them. This lab uses only core PostgreSQL types and methods.

## 3. B-tree as the operational baseline

B-tree is the default CREATE INDEX method. Test it first for ordinary equality/range workloads. Its order can support compatible ORDER BY and early LIMIT processing. Sorting a large fraction of a table can still favor a sequential scan plus sort.

A primary key normally creates a unique B-tree index; inspect existing definitions before adding another access path. PostgreSQL 18's ordinary UNIQUE indexes use B-tree. GiST-backed exclusion and temporal constraint designs are separate topics; do not treat a GiST search index as interchangeable with a unique scalar key.

Pattern matching is sensitive to expression, operator class and collation. A plain text B-tree is not a universal substring index. Composite, partial, expression and covering designs are developed in Chapter 032; access method choice is only one part of the definition.

## 4. Hash: a narrower contract

Hash stores hash codes for equality lookup. Hash collisions require checking actual values. It does not support ranges, uniqueness or ordinary key ordering. Evaluate duplicate distribution and bucket/overflow behavior together with measured size and read/write cost.

Modern PostgreSQL hash indexes are crash-recoverable and WAL-logged; old claims that they cannot survive recovery are not a basis for PostgreSQL 18 decisions. Still validate recovery and replication for the actual platform and workload. A smaller measured index is not automatically the better production choice if future queries need ranges.

## 5. GIN: component lookup and write fan-out

A GIN index maps components to matching rows: array elements, document terms or JSON components depending on its class. A query must use an operator supported by that class. Indexing an entire array with a default B-tree is not the same as indexing array membership.

Rows containing many distinct components can require substantial maintenance. GIN fastupdate can defer insertion work in a pending list, with cleanup behavior affecting latency. Monitor and budget that work under representative writes and vacuum activity. Turning fastupdate off does not flush existing pending entries.

JSONB operator-class choice changes the supported queries and size tradeoff. Do not choose a class from size alone. Full-text and JSON behavior need their own workload tests.

## 6. GiST and SP-GiST: choose the actual class

These methods supply infrastructure for specialized search strategies. A method name alone does not define supported operators, exactness or distance ordering.

The lab uses GiST range_ops for integer-range containment and SP-GiST's default point class for a point-in-box predicate. Those are core examples, not a comparison showing one method universally beats the other. Some classes support nearest-neighbor distance searches, which differ from ordinary scalar sorted scans.

Candidate matches can require heap rechecks, depending on the class and plan. Inspect actual plan evidence; a Recheck Cond by itself does not measure false-positive cost. Record rows removed by recheck and exact/lossy heap blocks where reported. Distribution, duplicates and geometric overlap can alter tree effectiveness.

## 7. BRIN: physical correlation is the key hypothesis

BRIN summarizes consecutive heap block ranges. A range scan can skip blocks whose summary cannot match, then recheck candidates in retained blocks. Its footprint can be small compared with a tuple-oriented index, but usefulness depends on layout and selectivity.

A time column in append order is a useful starting case. Backfills, updates or interleaved tenants can weaken correlation. A logically increasing timestamp does not prove physical clustering. Inspect scoped pg_stats.correlation and compare actual heap work.

pages_per_range trades summary granularity against index footprint and maintenance. A smaller range can filter more precisely at greater summary cost. Newly extended ranges require summarization; monitor that coverage and define a policy using vacuum, autosummarize or targeted BRIN summarization as appropriate. PostgreSQL 18 defaults autosummarize to off.

The lab compares identical 100-row time windows in physically ordered and scattered columns. If the scattered case chooses a sequential scan, that can be the correct cost decision. A lab-only diagnostic plan may expose how poor summaries behave, but it is not evidence that forcing an index improves production.

## 8. Account for the whole lifecycle

| Cost or risk | Operational evidence |
|---|---|
| Storage | Index bytes, growth, tablespace/free space and rebuild headroom |
| Writes | Representative INSERT/UPDATE/DELETE latency, WAL and replication impact |
| Cache | Heap/index working set and competing traffic |
| Maintenance | Build duration, vacuum work, rechecks and class-specific deferred work |
| Recovery | Restore duration and tested database/extension compatibility |
| Deployment | Lock budget, old transactions, build progress and failure handling |

Index presence can change update/HOT opportunities depending on which columns and methods are involved. Validate actual update behavior rather than assuming every extra index has the same cost.

Regular CREATE INDEX blocks writes while building but allows ordinary reads. CONCURRENTLY reduces that write-blocking behavior and performs additional work and waits; it is not lock-free or load-free. It cannot run inside a transaction block. Failed concurrent builds can leave invalid indexes that still consume maintenance work; inspect validity/readiness and use a reviewed recovery path.

This lab builds regular indexes only on an isolated fixture. Production rollout requires the workload's lock/I/O budget, progress observation and an explicit rollback. Constraint-backed indexes require dependency review before removal.

## 9. Prove benefit without forcing the conclusion

Keep the query, role, settings, data and measurement boundaries comparable. Capture default-planner plans before and after. With Chapter 027 safeguards, compare actual rows, heap/buffer work, execution time, rechecks and plan shape. Account for cache warming and repeat representative measurements in a controlled environment.

The planner may favor a sequential scan on a small table or a large result fraction. Validate statistics and predicates before concluding the index is unusable. Disabling sequential scans only discourages that path and is a scoped diagnostic, not a performance acceptance setting.

Usage counters are cumulative and can reset. A zero idx_scan over an incomplete interval does not prove an index is removable; rare jobs and integrity constraints matter. Record the access method, operator class, definition, owner and constraint role, not only its name.

## 10. Lab and acceptance

Run the [six-method lab](../labs/031-b-tree-and-other-index-types-operational-tradeoffs-lab.md). Produce a decision matrix with baseline/post-index plans, correct row counts, sizes, chosen scan paths, recheck behavior and a write/maintenance test plan.

The fixture demonstrates supported access paths and physical-layout effects. It does not establish production write amplification, recovery performance or stable latency percentiles. Those remain acceptance work for the target system.

**Authoring validation:** shell syntax, links, fences, SQL structure and synthetic fixture arithmetic reviewed. PostgreSQL runtime verification remains pending.

## Official PostgreSQL 18 references

- [Index types](https://www.postgresql.org/docs/18/indexes-types.html)
- [Index ordering](https://www.postgresql.org/docs/18/indexes-ordering.html)
- [Unique indexes](https://www.postgresql.org/docs/18/indexes-unique.html)
- [CREATE INDEX and concurrent builds](https://www.postgresql.org/docs/18/sql-createindex.html)
- [Hash](https://www.postgresql.org/docs/18/hash-index.html)
- [GIN](https://www.postgresql.org/docs/18/gin.html)
- [GiST](https://www.postgresql.org/docs/18/gist.html)
- [SP-GiST](https://www.postgresql.org/docs/18/spgist.html)
- [BRIN](https://www.postgresql.org/docs/18/brin.html)

**Next:** Chapter 032 — Composite, Partial, Expression and Covering Indexes.
