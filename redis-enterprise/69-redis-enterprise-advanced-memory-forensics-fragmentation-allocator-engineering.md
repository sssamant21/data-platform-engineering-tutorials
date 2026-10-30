# Chapter 69 --- Redis Enterprise Advanced Memory Forensics, Fragmentation & Allocator Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 12 --- Advanced Operations, FinOps & Resilience\
**Level:** Advanced → Memory Internals, Incident Forensics & Capacity
Engineering\
**Audience:** SREs, DBREs, Redis Administrators, Platform Engineers,
Kubernetes Administrators, Performance Engineers\
**Lab type:** Redis memory anatomy, allocator/RSS analysis,
fragmentation, keyspace forensics, expiration/deletion behavior, fork
and copy-on-write pressure, Kubernetes/container OOM analysis, active
defragmentation, controlled memory experiments, troubleshooting,
runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Redis is memory-centric, but production memory troubleshooting is not
simply:

``` text
used_memory is high
```

Several layers can differ:

``` text
logical Redis dataset
      |
Redis allocator
      |
process RSS
      |
container/cgroup memory
      |
host/node memory
```

A database can show:

``` text
used_memory = moderate
RSS = high
```

or:

``` text
used_memory = near limit
RSS = acceptable
but incoming write burst = unsafe
```

or:

``` text
memory falls logically
RSS remains elevated
```

Each condition has different causes and remediation.

By the end of this chapter, you should be able to:

-   explain Redis memory layers;
-   interpret `INFO MEMORY`;
-   distinguish logical usage from RSS;
-   understand allocator behavior;
-   interpret fragmentation metrics carefully;
-   investigate big keys and large values;
-   understand deletion and expiration effects;
-   understand copy-on-write and fork-related pressure;
-   analyze persistence/backup memory interaction;
-   identify Kubernetes/container OOM risk;
-   reason about eviction and memory limits;
-   evaluate active defragmentation;
-   build memory incident evidence;
-   run controlled memory experiments;
-   execute production runbooks and acceptance gates.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not diagnose Redis memory from one number.

Always correlate:

``` text
Redis logical memory
allocator statistics
RSS
container/cgroup memory
host memory
dataset/key distribution
workload
persistence activity
recent changes
```

------------------------------------------------------------------------

# Part 1 --- Memory Layers

## 3. Conceptual Stack

``` text
Application data
    |
Redis objects/data structures
    |
Allocator-managed memory
    |
Process virtual/RSS memory
    |
Container/cgroup
    |
Operating system / node
```

------------------------------------------------------------------------

# Part 2 --- Logical Dataset

## 4. Meaning

Redis logical memory includes memory Redis accounts for internally.

Use supported Redis Enterprise observability plus Redis memory
statistics appropriate for your environment.

------------------------------------------------------------------------

# Part 3 --- INFO MEMORY

## 5. Lab

In an approved lab database:

``` bash
redis-cli INFO MEMORY
```

Important fields can vary by Redis version.

Common concepts include:

``` text
used_memory
used_memory_human
used_memory_rss
used_memory_peak
used_memory_overhead
used_memory_dataset
mem_fragmentation_ratio
allocator-related fields
```

Interpret exact fields using current version documentation.

------------------------------------------------------------------------

# Part 4 --- used_memory

## 6. Concept

`used_memory` represents memory allocated by Redis through its allocator
for Redis-managed purposes.

It is not identical to operating-system RSS.

------------------------------------------------------------------------

# Part 5 --- used_memory_rss

## 7. Concept

RSS represents memory pages resident for the Redis process from the
operating system's perspective.

Conceptually:

``` text
RSS != logical Redis memory
```

------------------------------------------------------------------------

# Part 6 --- Why RSS Can Be Higher

## 8. Causes

Possible contributors include:

``` text
allocator fragmentation
memory not returned to OS
copy-on-write pages
allocator arenas
process overhead
temporary activity
```

Do not attribute all RSS difference to one cause without evidence.

------------------------------------------------------------------------

# Part 7 --- Why RSS Can Be Lower

## 9. Interpretation

Under some conditions, not every allocated page is resident.

A low RSS relative to logical allocation can also require investigation.

Do not use one universal fragmentation rule.

------------------------------------------------------------------------

# Part 8 --- Peak Memory

## 10. Importance

Track historical peak.

A database currently using 20 GB may have recently reached 45 GB.

Peak explains:

``` text
allocator growth
capacity risk
previous workload burst
```

------------------------------------------------------------------------

# Part 9 --- Dataset vs Overhead

## 11. Distinguish

Memory can be consumed by:

``` text
actual values
keys
data-structure metadata
client buffers
replication
allocator overhead
other Redis internals
```

Dataset size alone does not equal total memory requirement.

------------------------------------------------------------------------

# Part 10 --- Per-Key Overhead

## 12. Small Keys

Millions of tiny keys can have substantial metadata overhead.

Example:

``` text
10 million tiny values
```

can consume far more than raw payload bytes.

Measure rather than estimating only from source-data size.

------------------------------------------------------------------------

# Part 11 --- MEMORY USAGE

## 13. Lab

For an isolated key:

``` bash
redis-cli MEMORY USAGE tutorial:chapter69:key1
```

Use sampling options only when appropriate for complex values and
supported by the deployed version.

------------------------------------------------------------------------

# Part 12 --- Key Size Distribution

## 14. Need Distribution

Do not report only:

``` text
average value = 2 KB
```

Track:

``` text
P50
P95
P99
max
```

Large tails matter.

------------------------------------------------------------------------

# Part 13 --- Big Keys

## 15. Risk

A big key can create:

``` text
memory concentration
latency
network payload
deletion cost
replication cost
backup/persistence impact
```

------------------------------------------------------------------------

# Part 14 --- redis-cli Big Keys

## 16. Awareness

Redis CLI provides diagnostic modes for key analysis in some versions.

Use production-safe procedures and understand scan cost before running
against a large shared database.

Prefer controlled sampling and supported Redis Enterprise tooling where
available.

------------------------------------------------------------------------

# Part 15 --- Never KEYS \* in Production

## 17. Guardrail

Avoid:

``` bash
KEYS *
```

on large production keyspaces.

Use incremental scanning with a valid Redis command, a **scoped lab namespace**, and a cursor that is continued until Redis returns 0:

``` redis
SCAN 0 MATCH 'tutorial:chapter69:*' COUNT 100
```

**Expected:** A cursor and a list of zero or more matching keys. The `COUNT` argument is a work hint, not a guarantee of exactly 100 keys. Repeat `SCAN <returned-cursor> MATCH 'tutorial:chapter69:*' COUNT 100` until the returned cursor is 0. Entries may appear multiple times while iterating, and the result is not a transactional snapshot. Execute only in an approved lab with appropriate permissions and rate limits; a large scan can still consume resources.

References: [SCAN behavior](https://redis.io/docs/latest/commands/scan/), [KEYS production caution](https://redis.io/docs/latest/commands/keys/).

------------------------------------------------------------------------

# Part 16 --- Memory Sampling

## 18. Safer Pattern

Conceptually:

``` text
SCAN subset
 -> MEMORY USAGE
 -> classify key prefix/type
 -> aggregate distribution
```

Throttle diagnostic tooling.

------------------------------------------------------------------------

# Part 17 --- Key Type Distribution

## 19. Record

Measure:

``` text
string
hash
list
set
sorted set
stream
JSON
other supported structures
```

Different structures have different memory characteristics.

------------------------------------------------------------------------

# Part 18 --- Cardinality

## 20. Collections

For large collections, record cardinality.

Examples:

``` bash
HLEN <hash>
LLEN <list>
SCARD <set>
ZCARD <zset>
XLEN <stream>
```

Use only commands appropriate to the key type.

------------------------------------------------------------------------

# Part 19 --- Unbounded Structures

## 21. Common Cause

Memory incidents often originate from:

``` text
list never trimmed
stream never trimmed
set grows forever
hash grows forever
no TTL
```

Treat boundedness as an application contract.

------------------------------------------------------------------------

# Part 20 --- TTL Distribution

## 22. Investigate

Classify:

``` text
no TTL
< 1 hour
1-24 hours
1-7 days
> 7 days
```

using safe sampling.

------------------------------------------------------------------------

# Part 21 --- Missing TTL

## 23. Cache Risk

For cache databases, unexpected persistent keys may cause slow memory
growth.

Identify which prefixes are expected to have TTL.

------------------------------------------------------------------------

# Part 22 --- TTL Storm

## 24. Pattern

If millions of keys receive nearly identical expiration:

``` text
large expiration wave
```

can create CPU/load effects.

Use TTL jitter where application semantics permit.

------------------------------------------------------------------------

# Part 23 --- Expiration Is Not Instant Physical Reclamation

## 25. Concept

Redis expiration mechanisms and allocator/OS behavior mean logical
deletion and OS-level RSS reduction are not the same event.

Do not expect:

``` text
expired 10 GB
=> RSS immediately drops 10 GB
```

------------------------------------------------------------------------

# Part 24 --- Delete Behavior

## 26. DEL vs UNLINK

For large keys, synchronous deletion can be expensive.

Where supported and appropriate:

``` bash
UNLINK <key>
```

allows asynchronous reclamation work.

Validate behavior for your version/workload.

------------------------------------------------------------------------

# Part 25 --- Safe Tutorial Cleanup

## 27. Pattern

For isolated tutorial keys:

``` text
SCAN tutorial:chapter69:*
 -> UNLINK batches
```

Never use `FLUSHDB`/`FLUSHALL` on shared environments.

------------------------------------------------------------------------

# Part 26 --- Allocator

## 28. Role

Redis commonly uses an allocator such as jemalloc depending on
build/version.

The allocator manages memory blocks between Redis and the operating
system.

------------------------------------------------------------------------

# Part 27 --- Allocator Arenas

## 29. Concept

Allocators can retain free memory for future reuse rather than
immediately returning pages to the operating system.

This can make:

``` text
RSS > current logical dataset
```

after large deletions.

------------------------------------------------------------------------

# Part 28 --- Fragmentation

## 30. Definition

Fragmentation broadly describes inefficiency between memory
requested/used and memory reserved/resident.

There are multiple layers:

``` text
internal allocator fragmentation
external allocator fragmentation
RSS overhead
```

Do not treat one ratio as a complete diagnosis.

------------------------------------------------------------------------

# Part 29 --- mem_fragmentation_ratio

## 31. Caution

This metric can be useful but can be misleading when:

``` text
dataset is small
RSS includes other overhead
temporary fork/COW activity exists
```

Always inspect absolute bytes.

------------------------------------------------------------------------

# Part 30 --- Ratio Example

## 32. Why Absolute Values Matter

Case A:

``` text
used = 100 MB
RSS = 200 MB
ratio ~2
```

Difference:

``` text
100 MB
```

Case B:

``` text
used = 100 GB
RSS = 150 GB
ratio ~1.5
```

Difference:

``` text
50 GB
```

Case B is operationally much more important despite the lower ratio.

------------------------------------------------------------------------

# Part 31 --- Fragmentation Bytes

## 33. Track

Conceptually:

``` text
RSS - allocator/logical memory
```

with version-specific allocator metrics.

Use both:

``` text
ratio
absolute bytes
```

------------------------------------------------------------------------

# Part 32 --- Fragmentation Pattern

## 34. Typical Trigger

A workload can:

``` text
allocate many objects
delete many objects
allocate different-sized objects
```

leaving allocator space difficult to reuse efficiently.

------------------------------------------------------------------------

# Part 33 --- Churn

## 35. High-Churn Workload

Examples:

``` text
short-lived cache keys
rapidly changing JSON documents
large value replacement
frequent collection resizing
```

Measure fragmentation over time.

------------------------------------------------------------------------

# Part 34 --- Active Defragmentation

## 36. Concept

Redis can support active defragmentation depending on
version/build/configuration.

It attempts to reorganize allocator memory.

It consumes CPU.

------------------------------------------------------------------------

# Part 35 --- Do Not Enable Blindly

## 37. Qualification

Before changing defragmentation settings:

``` text
verify product support
measure fragmentation bytes
measure CPU headroom
benchmark workload
test in nonproduction
```

------------------------------------------------------------------------

# Part 36 --- Defrag Tradeoff

## 38. Goal

``` text
lower memory fragmentation
```

cost:

``` text
additional CPU / work
```

Evaluate SLO impact.

------------------------------------------------------------------------

# Part 37 --- Defrag Experiment

## 39. Lab

In isolated nonproduction:

1.  load varied-size keys;
2.  measure logical memory/RSS;
3.  delete a controlled subset;
4.  measure again;
5.  observe allocator behavior;
6.  if supported, test approved defrag configuration;
7.  compare CPU/P99/RSS.

------------------------------------------------------------------------

# Part 38 --- Memory Purge

## 40. Awareness

Some Redis/allocator versions expose mechanisms that can request
allocator memory release.

Do not run memory purge commands in production without product support,
testing, and understanding latency/CPU impact.

------------------------------------------------------------------------

# Part 39 --- Fork

## 41. Persistence/Background Work

Some Redis persistence/background operations can involve process forking
depending on version/configuration.

Fork introduces copy-on-write considerations.

------------------------------------------------------------------------

# Part 40 --- Copy-on-Write

## 42. Concept

After fork:

``` text
parent and child initially share pages
```

When the parent modifies a shared page:

``` text
copy created
```

Memory pressure can temporarily rise.

------------------------------------------------------------------------

# Part 41 --- Write-Heavy Fork Risk

## 43. Pattern

Large dataset + high write rate + background persistence can increase
copy-on-write overhead.

Monitor during:

``` text
snapshot
backup/persistence operations
```

as applicable to the deployed architecture.

------------------------------------------------------------------------

# Part 42 --- COW Capacity

## 44. Headroom

Do not size Redis to:

``` text
99-100% physical/container memory
```

and assume persistence operations have no temporary overhead.

Maintain operational headroom.

------------------------------------------------------------------------

# Part 43 --- Fork Latency

## 45. Large Memory

Large memory processes can make fork-related operations operationally
significant.

Measure in representative environments.

------------------------------------------------------------------------

# Part 44 --- Persistence Interaction

## 46. Correlate

During memory incident, ask:

``` text
Did persistence start?
Did backup start?
Did write rate increase?
Did RSS jump?
Did latency change?
```

------------------------------------------------------------------------

# Part 45 --- Replication Buffers

## 47. Memory Consumer

Replication and client buffering can consume memory beyond raw dataset.

Inspect supported metrics when diagnosing unexplained growth.

------------------------------------------------------------------------

# Part 46 --- Client Output Buffers

## 48. Slow Consumers

Slow clients can accumulate output buffers.

Investigate:

``` text
large result sets
Pub/Sub consumers
blocked/slow network clients
```

using supported client diagnostics.

------------------------------------------------------------------------

# Part 47 --- Connection Count

## 49. Overhead

Each connection has memory overhead.

A connection storm can increase memory and CPU even if dataset size is
unchanged.

------------------------------------------------------------------------

# Part 48 --- Query Result Size

## 50. Risk

Commands returning very large results can create transient
memory/network pressure.

Bound:

``` text
page size
collection scans
search results
```

------------------------------------------------------------------------

# Part 49 --- Lua / Server-Side Logic

## 51. Risk

Server-side scripts/functions can create temporary allocations and long
execution.

Include them in incident review.

------------------------------------------------------------------------

# Part 50 --- Search Index Memory

## 52. Additional

Redis Search/vector capabilities can consume substantial memory beyond
source values.

Capacity models must include indexes.

------------------------------------------------------------------------

# Part 51 --- Vector Memory

## 53. Example

Raw FLOAT32 vector payload:

``` text
vector_count * dimension * 4 bytes
```

before index/metadata/replication overhead.

Chapter 58 provides deeper vector capacity engineering.

------------------------------------------------------------------------

# Part 52 --- JSON Memory

## 54. Document Model

JSON documents have representation/index overhead beyond raw serialized
payload.

Measure real memory usage.

------------------------------------------------------------------------

# Part 53 --- Streams

## 55. Retention

Untrimmed Streams can grow indefinitely.

Monitor:

``` text
length
retention
consumer state
```

------------------------------------------------------------------------

# Part 54 --- Consumer Groups

## 56. Pending State

Durable messaging structures have operational metadata.

Do not capacity-plan Streams from message payload alone.

------------------------------------------------------------------------

# Part 55 --- maxmemory

## 57. Concept

Redis memory limits and Redis Enterprise database memory configuration
should align with the product's supported architecture.

Do not change low-level settings outside supported management
procedures.

------------------------------------------------------------------------

# Part 56 --- Eviction

## 58. When Limit Reached

Depending on configured policy and workload, Redis may:

``` text
evict keys
reject writes
```

or behave according to product/database configuration.

Understand before incident.

------------------------------------------------------------------------

# Part 57 --- Eviction Is Not Capacity Planning

## 59. Principle

For cache:

``` text
eviction may be expected
```

For durable/non-cache data:

``` text
eviction may be unacceptable
```

Classify semantics.

------------------------------------------------------------------------

# Part 58 --- Eviction Rate

## 60. Monitor

Sudden increase in evictions can indicate:

``` text
working set > capacity
traffic change
TTL problem
key growth
```

------------------------------------------------------------------------

# Part 59 --- Hit Ratio

## 61. Cache Impact

If capacity pressure increases eviction:

``` text
cache hit ratio can fall
source-system load can rise
```

Memory incidents can propagate downstream.

------------------------------------------------------------------------

# Part 60 --- Kubernetes Memory

## 62. Layers

In Kubernetes:

``` text
Redis memory
process RSS
container usage
pod limit
node memory
```

must all be considered.

------------------------------------------------------------------------

# Part 61 --- Container Limit

## 63. OOM Risk

If process/container memory exceeds the cgroup limit, the container can
be terminated.

A Redis-level memory limit alone does not guarantee container safety if
other memory overhead is ignored.

------------------------------------------------------------------------

# Part 62 --- OOMKilled

## 64. Diagnose

``` bash
kubectl describe pod <pod> -n <namespace>
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

Look for:

``` text
OOMKilled
memory pressure
eviction
```

------------------------------------------------------------------------

# Part 63 --- Node Memory Pressure

## 65. Host

``` bash
kubectl describe node <node>
```

Check:

``` text
MemoryPressure
allocatable
requests/limits
other workloads
```

------------------------------------------------------------------------

# Part 64 --- Requests vs Limits

## 66. Scheduling

Kubernetes schedules primarily from requests, while limits constrain
runtime.

Incorrect requests can overpack nodes.

Incorrect limits can create OOM risk.

------------------------------------------------------------------------

# Part 65 --- Guaranteed/Burstable Awareness

## 67. QoS

Kubernetes QoS behavior can influence eviction priority.

Use platform standards appropriate to Redis Enterprise.

------------------------------------------------------------------------

# Part 66 --- Swap

## 68. Caution

Redis latency is highly sensitive to memory paging.

Follow Redis Enterprise and Kubernetes platform guidance for swap/memory
configuration.

------------------------------------------------------------------------

# Part 67 --- Node Overcommit

## 69. Risk

A node can appear to have enough requested memory while runtime usage
creates pressure.

Stateful Redis workloads need conservative capacity engineering.

------------------------------------------------------------------------

# Part 68 --- Memory Headroom

## 70. Components

Reserve for:

``` text
dataset growth
allocator overhead
RSS fragmentation
COW
connections/buffers
replication
indexes
recovery
OS/container overhead
```

------------------------------------------------------------------------

# Part 69 --- Capacity Formula

## 71. Conceptual

``` text
required memory
=
dataset
+ Redis overhead
+ index/module overhead
+ connection/buffer overhead
+ replication/persistence overhead
+ fragmentation allowance
+ growth
+ safety headroom
```

Use empirical measurement.

------------------------------------------------------------------------

# Part 70 --- Growth Forecast

## 72. Track

``` text
GB/day
keys/day
peak write rate
TTL/no-TTL ratio
index growth
```

Forecast threshold dates.

------------------------------------------------------------------------

# Part 71 --- Memory Slope

## 73. Diagnostic

A useful question:

``` text
Is memory flat, stepwise, cyclical, or continuously rising?
```

Patterns suggest different causes.

------------------------------------------------------------------------

# Part 72 --- Flat High Memory

## 74. Interpretation

Possible:

``` text
stable large dataset
allocator retained memory
healthy steady state
```

Need headroom assessment.

------------------------------------------------------------------------

# Part 73 --- Continuous Growth

## 75. Investigate

Possible:

``` text
missing TTL
unbounded collection
traffic growth
new key prefix
index growth
memory leak/bug
```

------------------------------------------------------------------------

# Part 74 --- Sawtooth

## 76. Pattern

Can correspond to:

``` text
batch load
expiration
periodic cleanup
persistence
```

Correlate workload.

------------------------------------------------------------------------

# Part 75 --- Step Change

## 77. Investigate

Ask:

``` text
deployment?
data migration?
new feature?
bulk load?
index creation?
traffic event?
```

------------------------------------------------------------------------

# Part 76 --- Prefix Forensics

## 78. Classify

Group sampled keys by prefix:

``` text
session:
cache:
profile:
search:
job:
```

Find which namespace drives growth.

------------------------------------------------------------------------

# Part 77 --- Owner Mapping

## 79. Important

Every major key prefix should have:

``` text
application
team
TTL expectation
data semantics
```

------------------------------------------------------------------------

# Part 78 --- Memory Incident Timeline

## 80. Build

``` text
T0 baseline
T1 memory slope changes
T2 deployment/job
T3 eviction/latency
T4 intervention
T5 recovery
```

------------------------------------------------------------------------

# Part 79 --- Evidence Before Restart

## 81. Preserve

A restart may remove useful allocator/RSS evidence.

Capture:

``` text
INFO MEMORY
keyspace stats
evictions
pod/container memory
node memory
events
recent changes
```

before restart if service safety allows.

------------------------------------------------------------------------

# Part 80 --- Restart Is Not Root Cause

## 82. Principle

Restart may reduce RSS temporarily.

If the workload/data model is unchanged:

``` text
problem can return
```

Find the cause.

------------------------------------------------------------------------

# Part 81 --- Controlled Lab Dataset

## 83. Namespace

Use:

``` text
tutorial:chapter69:*
```

only in a disposable lab database.

------------------------------------------------------------------------

# Part 82 --- Lab 1: Small Keys

## 84. Test

Create many small keys.

Measure:

``` text
raw payload estimate
MEMORY USAGE samples
used_memory change
RSS change
```

Observe metadata overhead.

------------------------------------------------------------------------

# Part 83 --- Lab 2: Large Values

## 85. Test

Create a bounded set of large values.

Measure:

``` text
per-key memory
network
latency
deletion behavior
```

------------------------------------------------------------------------

# Part 84 --- Lab 3: Mixed Sizes

## 86. Test

Create variable-sized keys, delete a subset, then create different-sized
keys.

Observe allocator/RSS behavior.

------------------------------------------------------------------------

# Part 85 --- Lab 4: TTL Expiration

## 87. Test

Create keys with short TTL.

Measure before and after:

``` text
key count
used_memory
RSS
```

Observe that the layers need not fall identically.

------------------------------------------------------------------------

# Part 86 --- Lab 5: DEL vs UNLINK

## 88. Test

On disposable large keys compare:

``` text
DEL
UNLINK
```

Measure latency and cleanup behavior.

------------------------------------------------------------------------

# Part 87 --- Lab 6: Connection Growth

## 89. Test

Increase test client connections within safe limits.

Measure:

``` text
connection count
memory
CPU
```

------------------------------------------------------------------------

# Part 88 --- Lab 7: Persistence/COW

## 90. High Risk

Only in approved nonproduction.

Run supported persistence/backup activity while generating controlled
writes.

Observe:

``` text
RSS
COW metrics if available
CPU
P99
```

------------------------------------------------------------------------

# Part 89 --- Lab 8: Fragmentation

## 91. Test

Use churn:

``` text
allocate
delete
replace different sizes
```

Measure:

``` text
used_memory
RSS
fragmentation ratio
absolute gap
```

------------------------------------------------------------------------

# Part 90 --- Lab 9: Active Defrag

## 92. Conditional

Only if supported/configurable in your environment.

Compare:

``` text
before fragmentation
after fragmentation
CPU
P99
RSS
```

------------------------------------------------------------------------

# Part 91 --- Lab 10: OOM Tabletop

## 93. Do Not Crash Shared Redis

Model:

``` text
Redis logical memory
RSS overhead
container limit
COW burst
```

and determine when OOM would occur.

Use a disposable isolated environment for any real OOM experiment.

------------------------------------------------------------------------

# Part 92 --- Failure Scenario 1: Missing TTL Growth

## 94. Test

Create a bounded lab prefix without TTL.

Confirm memory slope monitoring detects persistent growth.

------------------------------------------------------------------------

# Part 93 --- Failure Scenario 2: Big Key

## 95. Test

Create one large disposable collection/value.

Validate detection and safe removal.

------------------------------------------------------------------------

# Part 94 --- Failure Scenario 3: Fragmentation After Churn

## 96. Test

Create/delete mixed-size keys.

Validate ratio plus absolute-byte interpretation.

------------------------------------------------------------------------

# Part 95 --- Failure Scenario 4: Expiration Wave

## 97. Test

Create many lab keys with similar TTL.

Observe CPU/expiration behavior.

------------------------------------------------------------------------

# Part 96 --- Failure Scenario 5: Connection Storm

## 98. Test

Increase test connections.

Observe memory and CPU.

------------------------------------------------------------------------

# Part 97 --- Failure Scenario 6: Slow Consumer Buffer

## 99. Test

In isolated nonproduction, create a bounded slow-consumer scenario using
an appropriate workload.

Observe client/buffer metrics.

------------------------------------------------------------------------

# Part 98 --- Failure Scenario 7: Persistence Memory Spike

## 100. Test

Under approved lab conditions, combine write activity with
persistence/backup.

Measure RSS/COW.

------------------------------------------------------------------------

# Part 99 --- Failure Scenario 8: Container Limit Too Tight

## 101. Tabletop/Lab

Model a container limit that leaves insufficient overhead above Redis
logical memory.

Validate preflight catches OOM risk.

------------------------------------------------------------------------

# Part 100 --- Failure Scenario 9: Eviction Surge

## 102. Test

In an isolated cache database, safely approach configured memory
capacity.

Observe:

``` text
evictions
hit ratio
source fallback
```

Do not perform this on durable/shared data.

------------------------------------------------------------------------

# Part 101 --- Failure Scenario 10: Memory Growth After Deployment

## 103. Test/Tabletop

Correlate a simulated deployment with:

``` text
new key prefix
missing TTL
larger values
```

Practice evidence-based diagnosis.

------------------------------------------------------------------------

# Part 102 --- Troubleshooting Matrix

## 104. Common Problems

  -----------------------------------------------------------------------
  Symptom                             Investigate
  ----------------------------------- -----------------------------------
  used_memory rising continuously     key growth, TTL, collections,
                                      indexes

  RSS much higher than used_memory    allocator, fragmentation, COW

  memory falls but RSS stays high     allocator retention/fragmentation

  OOMKilled below expected dataset    RSS/COW/container overhead
  limit                               

  eviction surge                      working set vs capacity

  hit ratio drops                     eviction/TTL/workload

  memory jumps during backup          persistence/COW/buffers

  one prefix dominates memory         application data model

  connection count causes memory      client pooling/storm
  growth                              

  restart fixes temporarily           workload/allocator/root cause
                                      unresolved
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Part 103 --- Runbook 1: High Redis Memory

## 105. Procedure

``` text
1. capture INFO MEMORY/product metrics.
2. compare logical memory and RSS.
3. inspect growth slope.
4. inspect key/prefix/type distribution.
5. inspect TTL.
6. inspect evictions/connections/buffers.
7. correlate recent changes/jobs.
8. remediate cause and validate headroom.
```

------------------------------------------------------------------------

# Part 104 --- Runbook 2: High Fragmentation

## 106. Procedure

``` text
1. capture used memory/RSS.
2. calculate absolute gap.
3. inspect dataset size.
4. inspect recent delete/churn.
5. inspect persistence/COW.
6. verify allocator metrics.
7. evaluate supported defrag/purge/restart options.
8. validate CPU/P99 after remediation.
```

------------------------------------------------------------------------

# Part 105 --- Runbook 3: OOMKilled Redis Pod

## 107. Procedure

``` text
1. inspect pod termination reason.
2. inspect container limit/usage.
3. inspect node memory pressure.
4. capture Redis memory evidence if available.
5. inspect COW/persistence/connection event.
6. restore service through supported procedure.
7. correct sizing/headroom/root cause.
8. validate recurrence prevention.
```

------------------------------------------------------------------------

# Part 106 --- Runbook 4: Big Key Incident

## 108. Procedure

``` text
1. identify key safely.
2. identify type/cardinality/size.
3. identify owner/workflow.
4. assess latency/replication risk.
5. stop uncontrolled growth.
6. remove/trim using safe supported method.
7. redesign bounded data model.
8. add size monitoring.
```

------------------------------------------------------------------------

# Part 107 --- Runbook 5: Missing TTL Growth

## 109. Procedure

``` text
1. identify growing prefix.
2. sample TTL distribution.
3. confirm expected TTL contract.
4. identify deployment/code path.
5. stop new persistent growth.
6. expire/remove old data safely.
7. monitor memory slope.
8. add regression/alert.
```

------------------------------------------------------------------------

# Part 108 --- Runbook 6: Eviction Surge

## 110. Procedure

``` text
1. confirm eviction rate.
2. inspect memory/capacity.
3. inspect hit ratio.
4. identify growth/workload change.
5. protect source system.
6. scale or reduce working set.
7. validate eviction policy.
8. update capacity forecast.
```

------------------------------------------------------------------------

# Part 109 --- Runbook 7: Persistence/COW Pressure

## 111. Procedure

``` text
1. correlate memory spike with background operation.
2. inspect write rate.
3. inspect RSS/COW evidence.
4. inspect container/node headroom.
5. reduce competing workload if approved.
6. allow supported operation to complete/recover.
7. resize/tune through supported guidance.
8. update maintenance/capacity model.
```

------------------------------------------------------------------------

# Part 110 --- Runbook 8: Memory Regression After Release

## 112. Procedure

``` text
1. compare pre/post memory slope.
2. identify new prefixes/data types.
3. compare TTL.
4. compare value-size distribution.
5. compare connections/buffers.
6. rollback/mitigate application change if appropriate.
7. clean leaked/unbounded data safely.
8. add release memory regression test.
```

------------------------------------------------------------------------

# Part 111 --- Memory Forensics Template

## 113. Record

``` text
Database:
Time:
used_memory:
RSS:
Peak:
Fragmentation ratio:
Absolute RSS gap:
Key count:
Evictions:
Connections:
TTL distribution:
Largest prefixes:
Largest keys:
Persistence activity:
COW:
Container usage/limit:
Node memory:
Recent changes:
```

------------------------------------------------------------------------

# Part 112 --- Capacity Worksheet

## 114. Record

``` text
Dataset:
Redis overhead:
Index/module overhead:
Connections/buffers:
Replication:
Persistence/COW allowance:
Fragmentation allowance:
Growth:
Safety headroom:
Required total:
Current allocation:
Scale trigger:
```

------------------------------------------------------------------------

# Part 113 --- Keyspace Review Template

## 115. Record

``` text
Prefix:
Owner:
Type:
Key count:
P50 size:
P95 size:
P99 size:
Max size:
TTL expectation:
Observed TTL:
Growth/day:
Bounded?:
Action:
```

------------------------------------------------------------------------

# Part 114 --- Memory Incident Timeline Template

## 116. Record

``` text
Baseline:
Growth start:
Deployment/job:
Peak memory:
Eviction:
Latency:
OOM/restart:
Mitigation:
Recovery:
Root cause:
Corrective action:
```

------------------------------------------------------------------------

# Part 115 --- Production Acceptance

## 117. Observability

-   [ ] logical Redis memory monitored;
-   [ ] RSS monitored;
-   [ ] container memory monitored;
-   [ ] node memory monitored;
-   [ ] peak tracked;
-   [ ] eviction monitored;
-   [ ] connections monitored;
-   [ ] key growth monitored;
-   [ ] capacity forecast implemented.

## 118. Data Model

-   [ ] key prefixes owned;
-   [ ] TTL expectations documented;
-   [ ] large-key review implemented;
-   [ ] unbounded collections identified;
-   [ ] value-size distribution measured;
-   [ ] Streams/JSON/Search/vector overhead included where used.

## 119. Capacity

-   [ ] fragmentation allowance considered;
-   [ ] COW/persistence headroom considered;
-   [ ] connection/buffer overhead considered;
-   [ ] container limit safely above expected runtime requirement;
-   [ ] node capacity sufficient;
-   [ ] failure/maintenance headroom validated.

## 120. Operations

-   [ ] fragmentation runbook tested;
-   [ ] OOM runbook tested;
-   [ ] big-key runbook tested;
-   [ ] missing-TTL runbook tested;
-   [ ] eviction runbook tested;
-   [ ] persistence/COW runbook tested;
-   [ ] ten failure scenarios completed;
-   [ ] production acceptance completed.

------------------------------------------------------------------------

# 121. Knowledge Validation

1.  Why is `used_memory` insufficient by itself?
2.  What is RSS?
3.  Why can RSS exceed Redis logical memory?
4.  Why is peak memory useful?
5.  Why can millions of small keys consume significant overhead?
6.  What does `MEMORY USAGE` help investigate?
7.  Why should key-size distributions include P95/P99/max?
8.  Why are big keys risky?
9.  Why should `KEYS *` be avoided on large production databases?
10. Why should TTL distribution be sampled?
11. Why might RSS not fall immediately after expiration/deletion?
12. Why can `UNLINK` be safer for large-key cleanup?
13. What role does the memory allocator play?
14. Why can allocators retain memory?
15. Why is fragmentation ratio alone insufficient?
16. Why should fragmentation be measured in absolute bytes too?
17. What tradeoff does active defragmentation introduce?
18. What is copy-on-write?
19. Why can write-heavy persistence increase memory pressure?
20. Why must replication/client buffers be included in memory analysis?
21. How can a connection storm affect memory?
22. Why must Search/vector/JSON overhead be included?
23. Why is eviction not a substitute for capacity planning?
24. Why can eviction pressure affect source systems?
25. Why can Kubernetes OOM occur even if Redis logical memory looks
    below the container limit?
26. Why do requests and limits both matter?
27. What should memory headroom include?
28. Why should evidence be captured before restart when safe?
29. Why is restart not a root-cause fix?
30. What must pass before Redis memory engineering is production-ready?

------------------------------------------------------------------------

# 122. Hands-On Acceptance Checklist

-   [ ] Captured `INFO MEMORY` in lab.
-   [ ] Compared used memory and RSS.
-   [ ] Recorded peak memory.
-   [ ] Sampled `MEMORY USAGE`.
-   [ ] Built key-size distribution.
-   [ ] Identified key types.
-   [ ] Reviewed collection cardinality.
-   [ ] Sampled TTL distribution.
-   [ ] Tested many small keys.
-   [ ] Tested large values.
-   [ ] Tested mixed-size churn.
-   [ ] Tested TTL expiration.
-   [ ] Compared DEL and UNLINK.
-   [ ] Tested connection growth.
-   [ ] Tested persistence/COW in approved lab.
-   [ ] Measured fragmentation ratio and bytes.
-   [ ] Evaluated active defrag only if supported.
-   [ ] Modeled container OOM.
-   [ ] Tested missing-TTL detection.
-   [ ] Tested big-key detection.
-   [ ] Tested expiration wave.
-   [ ] Tested connection storm.
-   [ ] Tested slow-consumer scenario.
-   [ ] Tested eviction in isolated cache database.
-   [ ] Built memory capacity worksheet.
-   [ ] Built keyspace ownership review.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed eight runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 123. Cleanup

Remove only disposable Chapter 69 lab keys.

For:

``` text
tutorial:chapter69:*
```

use:

``` text
SCAN
+
UNLINK in controlled batches
```

Do not use:

``` text
FLUSHDB
FLUSHALL
```

on shared environments.

Restore any temporary lab configuration.

Confirm:

``` text
memory slope stable
RSS understood
no lab keys remain
no temporary connection load
no temporary persistence test running
no temporary defrag/config changes remain
```

------------------------------------------------------------------------

# 124. Key Takeaways

1.  Redis memory troubleshooting requires logical memory, allocator,
    RSS, container, and node views together.
2.  `used_memory` and RSS represent different layers.
3.  RSS can remain high after logical deletion because allocator/OS
    reclamation is not instantaneous.
4.  Peak memory explains historical allocator/capacity behavior.
5.  Small-key metadata can be a major capacity component.
6.  Key-size distributions are more useful than averages alone.
7.  Big keys create memory, latency, replication, and deletion risk.
8.  Production keyspace analysis should use safe incremental sampling
    rather than blocking enumeration.
9.  Missing TTL and unbounded collections are common causes of sustained
    memory growth.
10. Logical expiration and physical RSS reduction are different events.
11. `UNLINK` can reduce synchronous deletion work for suitable large
    keys.
12. Allocator behavior is central to fragmentation analysis.
13. Fragmentation ratios must be paired with absolute byte differences.
14. Active defragmentation trades CPU for memory compaction and must be
    qualified.
15. Persistence/background operations can introduce copy-on-write
    pressure.
16. Redis should retain headroom for COW, buffers, fragmentation,
    growth, and recovery.
17. Client/replication buffers and connection counts can materially
    affect memory.
18. Search, vector, JSON, and Streams require additional memory
    modeling.
19. Eviction policy must match data semantics.
20. Eviction pressure can reduce cache hit ratio and overload source
    systems.
21. Kubernetes container limits must include RSS and transient overhead,
    not only logical dataset.
22. Node memory pressure and pod OOM are different but related failure
    modes.
23. Memory slope shape is useful forensic evidence.
24. Capture evidence before restarting when service safety allows.
25. Production memory readiness requires data-model controls,
    observability, empirical capacity, fragmentation/COW headroom,
    Kubernetes sizing, and tested runbooks together.

------------------------------------------------------------------------

# 125. References

Validate memory fields, allocator behavior, active defragmentation
support/configuration, persistence behavior, copy-on-write metrics,
Redis Enterprise memory limits, and Kubernetes deployment guidance
against the exact deployed Redis/Redis Enterprise version and current
official documentation.

Recommended documentation areas:

-   Redis `INFO MEMORY`
-   Redis `MEMORY USAGE`
-   Redis memory optimization
-   Redis key eviction
-   Redis expiration
-   Redis `UNLINK`
-   Redis latency and big-key diagnostics
-   Redis active defragmentation
-   Redis persistence
-   Redis Enterprise memory management
-   Redis Enterprise database memory and eviction
-   Redis Enterprise observability
-   Redis Enterprise Search/JSON/vector memory guidance
-   Kubernetes memory requests/limits
-   Kubernetes OOM and node pressure
-   container/cgroup memory observability

------------------------------------------------------------------------

# Next Chapter

**Chapter 70 --- Redis Enterprise Command Complexity, SLOWLOG & Latency
Forensics**

Chapter 70 will move from memory forensics into command-level
performance forensics: command complexity, event-loop impact, SLOWLOG
interpretation, latency monitoring, large-result commands, blocking
operations, Lua/functions, big-key correlation, client/network latency
separation, CPU saturation, commandstats, controlled reproduction,
troubleshooting, runbooks, and production acceptance.
