# Chapter 14 --- Write-Through, Write-Behind & Read-Through Patterns

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Intermediate → Production Cache Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Pattern comparison, synchronous and asynchronous write
simulations, queue behavior, ordering, duplicate handling, failure
injection, durability analysis, recovery, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Cache-aside is not the only caching architecture.

Production systems may also use:

``` text
read-through
write-through
write-behind / write-back
```

These patterns differ in:

``` text
who owns source access
when the source is updated
what the application considers success
where durability begins
how failures are recovered
how much consistency complexity exists
```

The names are simple.

The production consequences are not.

By the end, you should be able to:

-   Compare cache-aside, read-through, write-through, and write-behind.
-   Draw the request path for each pattern.
-   Explain synchronous and asynchronous write behavior.
-   Identify the durability boundary.
-   Explain acknowledgement risk.
-   Design write-behind queues.
-   Handle duplicate work.
-   Preserve write ordering where required.
-   Understand backpressure.
-   Define retry and dead-letter behavior.
-   Detect queue/backlog growth.
-   Recover from cache, worker, source, and queue failures.
-   Select a caching pattern based on workload requirements.

------------------------------------------------------------------------

# 2. Pattern Overview

At a high level:

  -----------------------------------------------------------------------
  Pattern                 Read Miss               Write Path
  ----------------------- ----------------------- -----------------------
  Cache-aside             Application reads       Application writes
                          source                  source and invalidates
                                                  cache

  Read-through            Cache/provider loads    Depends on write design
                          source                  

  Write-through           Cache layer             Source updated before
                          synchronously writes    success is returned
                          source                  

  Write-behind            Cache accepts write,    Success may occur
                          source updated          before source
                          asynchronously          persistence
  -----------------------------------------------------------------------

These are architectural descriptions.

Exact capabilities depend on the cache library, framework, Redis
deployment, and application implementation.

------------------------------------------------------------------------

# Part 1 --- Cache-Aside Review

## 3. Cache-Aside

``` text
Application
   |
   v
Redis
   |
 miss
   |
   v
Application
   |
   v
Source
```

The application explicitly owns:

``` text
Redis lookup
source fallback
cache population
invalidation
```

This was covered in Chapters 12 and 13.

------------------------------------------------------------------------

# Part 2 --- Read-Through

## 4. Concept

In read-through, the application asks a cache abstraction for data.

Conceptually:

``` text
Application
    |
    v
Cache / Data Access Layer
    |
    +---- hit ----> Return
    |
    +---- miss
           |
           v
        Source
           |
           v
        Populate
           |
           v
         Return
```

The source-loading logic is encapsulated behind the cache/data-access
layer.

------------------------------------------------------------------------

## 5. Cache-Aside vs Read-Through

Cache-aside:

``` text
application code explicitly handles miss
```

Read-through:

``` text
cache abstraction/provider handles miss loading
```

From the caller's perspective:

``` text
get(key)
```

may hide source access.

------------------------------------------------------------------------

## 6. Important Redis Clarification

Redis itself does not magically know how to query your PostgreSQL,
MongoDB, HTTP API, or other source just because a key is missing.

A read-through architecture requires:

``` text
application framework
cache provider
custom data-access layer
or another integration component
```

that knows how to load the authoritative data.

------------------------------------------------------------------------

# Part 3 --- Read-Through Advantages

## 7. Benefits

``` text
centralized read logic
consistent TTL behavior
less repeated application code
standardized metrics
standardized serialization
```

Multiple callers can share the same caching abstraction.

------------------------------------------------------------------------

## 8. Risks

``` text
hidden source latency
framework coupling
loader bugs affect many callers
stampede on popular misses
harder debugging if abstraction hides behavior
```

Observability must still expose:

``` text
hit
miss
source load
cache population
```

------------------------------------------------------------------------

# Part 4 --- Read-Through Flow

## 9. Hit

``` text
Application
   |
   v
Cache Provider
   |
 Redis hit
   |
   v
Return
```

------------------------------------------------------------------------

## 10. Miss

``` text
Application
   |
   v
Cache Provider
   |
 Redis miss
   |
   v
Source
   |
   v
Cache Redis
   |
   v
Return
```

The caller should not need to duplicate this logic.

------------------------------------------------------------------------

# Part 5 --- Write-Through

## 11. Concept

Write-through synchronously updates the authoritative store as part of
the write path.

Conceptually:

``` text
Application
    |
    v
Write-Through Layer
    |
    +----> Source
    |
    +----> Cache
    |
    v
Success
```

The exact ordering and transaction model matter.

------------------------------------------------------------------------

## 12. Success Semantics

A well-defined write-through architecture should answer:

> When do we return success to the caller?

Common requirement:

``` text
only after authoritative persistence succeeds
```

If Redis is merely a cache, the source remains the durability authority.

------------------------------------------------------------------------

# Part 6 --- Write-Through Ordering

## 13. Source First

Conceptually:

``` text
1. Write source.
2. Source commits.
3. Update/invalidate cache.
4. Return success.
```

If cache update fails:

``` text
source is still correct
cache can be repaired
```

This resembles synchronous cache maintenance after an authoritative
write.

------------------------------------------------------------------------

## 14. Cache First

Dangerous when Redis is not the authority:

``` text
1. Update Redis.
2. Source write fails.
```

Now:

``` text
cache contains data that never committed
```

Do not confuse fast cache acknowledgement with durable business success.

------------------------------------------------------------------------

# Part 7 --- Write-Through Failure Matrix

## 15. Source Failure

``` text
source write fails
```

Expected:

``` text
operation fails
cache should not claim committed new state
```

------------------------------------------------------------------------

## 16. Cache Failure After Source Commit

``` text
source commit succeeds
cache update fails
```

Possible response depends on contract.

Often:

``` text
authoritative write succeeded
record cache maintenance failure
invalidate/repair cache
```

Do not roll back a committed source write casually because cache
maintenance failed.

------------------------------------------------------------------------

# Part 8 --- Write-Through Advantages

## 17. Benefits

``` text
fresh cache after writes
centralized write behavior
reduced next-read miss
predictable application API
```

------------------------------------------------------------------------

## 18. Costs

``` text
write latency includes source latency
cache/source synchronization complexity
partial-failure handling
more dependency coupling
```

------------------------------------------------------------------------

# Part 9 --- Write-Behind / Write-Back

## 19. Concept

Write-behind acknowledges the application before the authoritative store
has necessarily been updated.

Conceptually:

``` text
Application
    |
    v
Redis / Write Buffer
    |
    v
Success returned
    |
    v
Queue / Worker
    |
    v
Source
```

This can improve write latency and batch source updates.

It also moves the durability boundary.

------------------------------------------------------------------------

# Part 10 --- Durability Boundary

## 20. Critical Question

If the application receives:

``` text
SUCCESS
```

where is the write durably stored?

Possibilities:

``` text
only Redis memory
Redis persistence
durable message queue
source database
```

These are not equivalent.

------------------------------------------------------------------------

## 21. Acknowledgement Risk

If success is returned while data exists only in volatile memory:

``` text
process/node/cluster failure
```

may lose an acknowledged business write.

For critical data, this may be unacceptable.

------------------------------------------------------------------------

# Part 11 --- Write-Behind Architecture

## 22. Safer Conceptual Design

``` text
Application
    |
    v
Cache / Write API
    |
    v
Durable Queue
    |
    +---- acknowledgement boundary
    |
    v
Workers
    |
    v
Source Database
```

Redis may participate in the caching layer, but a durable queue can
provide a stronger asynchronous handoff boundary.

The exact design depends on durability requirements.

------------------------------------------------------------------------

# Part 12 --- Write Queue

## 23. Queue Record

Example:

``` json
{
  "operation_id": "op-12345",
  "entity": "profile",
  "entity_id": "1001",
  "version": 42,
  "operation": "update",
  "payload": {
    "status": "inactive"
  }
}
```

Production events should avoid unnecessary sensitive data.

------------------------------------------------------------------------

# Part 13 --- Idempotency

## 24. Duplicate Delivery

Asynchronous systems should assume a write may be delivered more than
once.

Example:

``` text
worker writes source
worker crashes before acknowledging message
message delivered again
```

Without idempotency:

``` text
same logical operation can be applied twice
```

------------------------------------------------------------------------

## 25. Operation ID

Use:

``` text
operation_id
```

or another business idempotency key.

The source/writer can record that:

``` text
op-12345 already applied
```

and avoid duplicate side effects.

------------------------------------------------------------------------

# Part 14 --- Why Idempotency Matters

## 26. Non-Idempotent Example

Operation:

``` text
increment account balance by $100
```

Applied twice:

``` text
+$200
```

This is different from:

``` text
set status = inactive
```

which may naturally tolerate repetition.

Classify write semantics before choosing retry behavior.

------------------------------------------------------------------------

# Part 15 --- Ordering

## 27. Entity Updates

Suppose:

``` text
V41 -> active
V42 -> inactive
```

If V42 reaches the source first and V41 later:

``` text
source may regress to old state
```

if the writer does not enforce versions.

------------------------------------------------------------------------

## 28. Version Check

Source write logic should reject:

``` text
incoming version <= current version
```

when strict monotonic entity ordering is required.

This turns ordering correctness into an explicit rule.

------------------------------------------------------------------------

# Part 16 --- Partitioning

## 29. Preserve Per-Entity Order

A queue can partition by:

``` text
entity ID
customer ID
aggregate ID
```

so writes for one entity follow a consistent processing path.

Global ordering is usually unnecessary and expensive.

What matters is often:

``` text
per-entity ordering
```

------------------------------------------------------------------------

# Part 17 --- Queue Backlog

## 30. Backlog

If incoming write rate:

``` text
20,000/sec
```

and workers persist:

``` text
15,000/sec
```

backlog grows:

``` text
5,000/sec
```

After one hour:

``` text
18,000,000 pending operations
```

Write-behind capacity must be modeled mathematically.

------------------------------------------------------------------------

# Part 18 --- Queue Lag

## 31. Lag

Useful measures:

``` text
pending messages
oldest message age
consumer lag
writes/sec in
writes/sec out
source persistence latency
```

The oldest-message age is often more meaningful to business freshness
than queue depth alone.

------------------------------------------------------------------------

# Part 19 --- Backpressure

## 32. When Workers Cannot Keep Up

Options may include:

``` text
slow producers
reject writes
increase workers
increase batching
degrade noncritical functionality
```

Do not allow backlog to grow without bound.

------------------------------------------------------------------------

# Part 20 --- Batching

## 33. Benefit

Write-behind can combine many writes:

``` text
100 individual source writes
```

into a more efficient batch.

This can improve:

``` text
throughput
connection use
transaction overhead
```

------------------------------------------------------------------------

## 34. Cost

Batching increases:

``` text
time before persistence
failure blast radius
retry complexity
ordering complexity
```

Tune batch size and flush interval against durability and freshness
requirements.

------------------------------------------------------------------------

# Part 21 --- Coalescing

## 35. Multiple Updates to Same Entity

Queue:

``` text
V41 status=active
V42 status=pending
V43 status=inactive
```

Some workloads may only need:

``` text
V43
```

at the source.

Coalescing can reduce source writes.

But it is unsafe when intermediate operations have business meaning.

------------------------------------------------------------------------

# Part 22 --- Write-Behind and Redis Streams

## 36. Redis Streams Concept

Redis Streams can represent an append-oriented event/work stream.

Conceptual producer:

``` redis
XADD tutorial:chapter14:writes * entity_id 1001 version 42 status inactive
```

Consumer groups can distribute processing.

Whether Redis Streams is an appropriate durability boundary depends on:

``` text
Redis deployment
persistence
replication
recovery design
RPO
business criticality
```

Do not assume "stream" automatically means zero data loss.

------------------------------------------------------------------------

# Part 23 --- Stream Consumer

## 37. Conceptual Group

``` redis
XGROUP CREATE tutorial:chapter14:writes writers $ MKSTREAM
```

Consumer:

``` redis
XREADGROUP GROUP writers worker1 COUNT 10 BLOCK 5000 STREAMS tutorial:chapter14:writes >
```

After successful source persistence:

``` redis
XACK tutorial:chapter14:writes writers <message-id>
```

Validate exact commands and operational behavior against the deployed
Redis version.

------------------------------------------------------------------------

# Part 24 --- Acknowledge Only After Source Success

## 38. Worker Rule

Correct conceptual order:

``` text
read queue message
write source
source commit succeeds
ack queue message
```

If the worker crashes before acknowledgement:

``` text
message may be retried
```

Therefore:

``` text
source write must be idempotent
```

------------------------------------------------------------------------

# Part 25 --- Pending Messages

## 39. Worker Crash

A message delivered but not acknowledged can remain pending.

Production operations must support:

``` text
pending inspection
stale consumer recovery
claim/reassignment
retry
dead-letter policy
```

This is deeper queue engineering, but it is essential for write-behind
reliability.

------------------------------------------------------------------------

# Part 26 --- Dead-Letter Handling

## 40. Poison Write

Suppose one operation repeatedly fails because:

``` text
schema invalid
entity missing
constraint violation
bad payload
```

Retrying forever can block progress or waste resources.

Use a controlled dead-letter/error workflow.

Capture:

``` text
operation ID
reason
attempt count
timestamp
owner
```

Do not leak sensitive payloads into logs.

------------------------------------------------------------------------

# Part 27 --- Retry Strategy

## 41. Transient Failure

Examples:

``` text
source timeout
temporary connection error
short source failover
```

May justify:

``` text
bounded retry
exponential backoff
jitter
```

------------------------------------------------------------------------

## 42. Permanent Failure

Examples:

``` text
invalid schema
constraint violation
unknown operation type
```

Usually should not be retried indefinitely.

Classify failures.

------------------------------------------------------------------------

# Part 28 --- Read-After-Write

## 43. Write-Through

After successful write-through:

``` text
source committed
cache refreshed/invalidation completed according to contract
```

read-after-write can be designed predictably.

------------------------------------------------------------------------

## 44. Write-Behind

After application receives success:

``` text
source may still contain old value
```

If subsequent read bypasses the cache and queries the source:

``` text
old data may appear
```

The architecture must explicitly define read-after-write behavior.

------------------------------------------------------------------------

# Part 29 --- Cache as Temporary Authority

## 45. Write-Behind Implication

For some period:

``` text
Redis/cache layer has newer state than source
```

This is fundamentally different from classic cache-aside.

Operational procedures must understand which copy is newest during
backlog or outage.

------------------------------------------------------------------------

# Part 30 --- Source Outage

## 46. Write-Through During Source Outage

Typical result:

``` text
writes fail
```

because success requires source persistence.

------------------------------------------------------------------------

## 47. Write-Behind During Source Outage

Potentially:

``` text
writes continue
queue grows
```

until:

``` text
queue capacity
retention
memory/storage limit
business lag limit
```

is reached.

This can improve availability but creates recovery obligations.

------------------------------------------------------------------------

# Part 31 --- Recovery Rate

## 48. Catch-Up Capacity

If backlog:

``` text
10 million writes
```

and after source recovery:

``` text
incoming = 10k/sec
worker capacity = 12k/sec
```

net drain:

``` text
2k/sec
```

Time to drain:

``` text
10,000,000 / 2,000
= 5,000 seconds
≈ 83 minutes
```

Recovery capacity must exceed normal incoming load.

------------------------------------------------------------------------

# Part 32 --- Avoid Recovery Storm

## 49. Source Just Recovered

Do not instantly unleash unlimited workers.

Potential result:

``` text
source fails again
```

Use controlled ramp-up:

``` text
rate limits
batch limits
adaptive concurrency
source latency/error feedback
```

------------------------------------------------------------------------

# Part 33 --- Data Loss Window

## 50. RPO Question

If queue/cache is lost before source persistence:

``` text
how many acknowledged writes can be lost?
```

That is an RPO question.

Write-behind must have an explicit answer.

------------------------------------------------------------------------

# Part 34 --- Failure Domains

## 51. Avoid Shared Fate

If:

``` text
cache
write queue
worker
```

all depend on one node/failure domain, one failure can remove:

``` text
serving state
pending writes
processing capability
```

Design HA based on the business criticality.

------------------------------------------------------------------------

# Part 35 --- Read-Through + Write-Through

## 52. Combined Abstraction

Some architectures provide:

``` text
get -> read-through
put -> write-through
```

Application sees:

``` text
repository.get(id)
repository.put(entity)
```

while the repository/cache layer handles source/cache coordination.

This can simplify application code but centralizes correctness
responsibility in the abstraction.

------------------------------------------------------------------------

# Part 36 --- Read-Through + Write-Behind

## 53. Combined Model

Possible:

``` text
reads -> cache, load source on miss
writes -> cache immediately, persist source asynchronously
```

This offers low apparent latency.

It also creates the largest operational responsibility around:

``` text
durability
queue recovery
ordering
read consistency
```

Use only when those tradeoffs are intentional.

------------------------------------------------------------------------

# Part 37 --- Pattern Selection

## 54. Cache-Aside

Prefer when:

``` text
read-heavy
simple model desired
application can own caching
bounded staleness acceptable
```

------------------------------------------------------------------------

## 55. Read-Through

Prefer when:

``` text
central cache abstraction desired
multiple callers should share loader logic
framework/provider supports it well
```

------------------------------------------------------------------------

## 56. Write-Through

Prefer when:

``` text
source must be committed before success
fresh cache after writes is useful
synchronous source latency acceptable
```

------------------------------------------------------------------------

## 57. Write-Behind

Consider when:

``` text
write latency is critical
source batching is valuable
temporary source lag is acceptable
durable asynchronous pipeline exists
idempotency and ordering can be engineered
```

Avoid casual use for critical writes without strong durability design.

------------------------------------------------------------------------

# Part 38 --- Hands-On Read-Through Lab

## 58. Simulated Source

``` python
SOURCE = {
    "1001": {
        "id": "1001",
        "status": "active",
    }
}
```

------------------------------------------------------------------------

## 59. Read-Through Wrapper

``` python
import json

class ReadThroughRepository:
    def __init__(self, redis_client):
        self.r = redis_client

    def key(self, entity_id):
        return f"tutorial:chapter14:rt:{entity_id}"

    def load_source(self, entity_id):
        return SOURCE.get(entity_id)

    def get(self, entity_id):
        key = self.key(entity_id)

        cached = self.r.get(key)

        if cached is not None:
            return json.loads(cached)

        value = self.load_source(entity_id)

        if value is None:
            return None

        self.r.set(
            key,
            json.dumps(value),
            ex=120,
        )

        return value
```

The caller does not implement source fallback.

------------------------------------------------------------------------

## 60. Lab

``` python
repo = ReadThroughRepository(r)

print(repo.get("1001"))
print(repo.get("1001"))
```

Observe:

``` text
first call loads source
second call uses Redis
```

------------------------------------------------------------------------

# Part 39 --- Write-Through Lab

## 61. Simulated Source Write

``` python
def write_source(entity_id, value):
    SOURCE[entity_id] = value
```

------------------------------------------------------------------------

## 62. Write-Through Function

``` python
def write_through(r, entity_id, value):
    write_source(entity_id, value)

    key = f"tutorial:chapter14:wt:{entity_id}"

    r.set(
        key,
        json.dumps(value),
        ex=120,
    )

    return value
```

Production code must define what happens when Redis update fails after
source commit.

------------------------------------------------------------------------

## 63. Validate

``` python
value = {
    "id": "1001",
    "status": "inactive",
}

write_through(r, "1001", value)
```

Check:

``` python
print(SOURCE["1001"])
```

and:

``` redis
GET tutorial:chapter14:wt:1001
```

------------------------------------------------------------------------

# Part 40 --- Write-Behind Simulation

## 64. In-Memory Teaching Queue

For conceptual learning only:

``` python
from collections import deque

WRITE_QUEUE = deque()
```

This queue is not durable and is intentionally unsuitable for
production.

------------------------------------------------------------------------

## 65. Enqueue

``` python
def write_behind(entity_id, value, version):
    WRITE_QUEUE.append({
        "entity_id": entity_id,
        "value": value,
        "version": version,
    })

    return {
        "status": "accepted"
    }
```

Notice:

``` text
source has not been updated yet
```

------------------------------------------------------------------------

## 66. Worker

``` python
def process_one():
    if not WRITE_QUEUE:
        return

    item = WRITE_QUEUE.popleft()

    SOURCE[item["entity_id"]] = {
        **item["value"],
        "version": item["version"],
    }
```

------------------------------------------------------------------------

## 67. Observe Lag

Call:

``` python
write_behind(
    "1001",
    {"id": "1001", "status": "pending"},
    2,
)
```

Immediately inspect source.

Then:

``` python
process_one()
```

Inspect source again.

This demonstrates:

``` text
acknowledgement before source persistence
```

------------------------------------------------------------------------

# Part 41 --- Ordering Lab

## 68. Enqueue

``` python
write_behind(
    "1001",
    {"id": "1001", "status": "pending"},
    3,
)

write_behind(
    "1001",
    {"id": "1001", "status": "inactive"},
    4,
)
```

Correct processing order:

``` text
V3
V4
```

Reverse processing can regress state.

------------------------------------------------------------------------

## 69. Version-Aware Worker

Conceptually:

``` python
def process_versioned(item):
    current = SOURCE.get(item["entity_id"])

    current_version = (
        current.get("version", 0)
        if current
        else 0
    )

    if item["version"] <= current_version:
        return "STALE"

    SOURCE[item["entity_id"]] = {
        **item["value"],
        "version": item["version"],
    }

    return "APPLIED"
```

------------------------------------------------------------------------

# Part 42 --- Duplicate Lab

## 70. Duplicate Operation

Process the same operation twice.

For:

``` text
SET status = inactive
```

result may remain correct.

For:

``` text
increment balance
```

it may not.

Add an idempotency record for non-idempotent operations.

------------------------------------------------------------------------

# Part 43 --- Redis Streams Lab

## 71. Create Event

``` redis
XADD tutorial:chapter14:writes '*' operation_id op-1001 entity_id 1001 version 5 status inactive
```

**Expected:** `XADD` returns a generated Stream ID, which will vary by execution. In the same isolated lab database, `XRANGE tutorial:chapter14:writes - +` should include the new ID and the four field/value pairs. Do not assume the stream was empty or that its total length is fixed. The example uses a **single interactive Redis command**; Bash-style backslash continuation is not valid when the lines are pasted independently into an interactive `redis-cli` prompt.

------------------------------------------------------------------------

## 72. Inspect

``` redis
XRANGE tutorial:chapter14:writes - +
```

Use bounded ranges in large production streams.

------------------------------------------------------------------------

## 73. Consumer Group

In a dedicated lab:

``` redis
XGROUP CREATE tutorial:chapter14:writes writers 0 MKSTREAM
```

Read:

``` redis
XREADGROUP GROUP writers worker1 COUNT 10 STREAMS tutorial:chapter14:writes >
```

After successful simulated source write:

``` redis
XACK tutorial:chapter14:writes writers <message-id>
```

------------------------------------------------------------------------

# Failure Injection

## 74. Failure 1 --- Read-Through Loader Failure

``` text
Redis miss
source loader fails
```

Expected:

``` text
no value available
error/degraded response according to policy
```

Do not cache an arbitrary failure as valid data.

------------------------------------------------------------------------

## 75. Failure 2 --- Write-Through Source Failure

``` text
source write fails
```

Expected:

``` text
do not report durable success
```

------------------------------------------------------------------------

## 76. Failure 3 --- Write-Through Cache Failure

``` text
source commits
Redis update fails
```

Expected:

``` text
source remains authoritative
repair/invalidate cache
record cache maintenance failure
```

------------------------------------------------------------------------

## 77. Failure 4 --- Write-Behind Worker Down

Writes continue entering queue.

Observe:

``` text
queue depth grows
oldest age grows
source becomes increasingly behind
```

Alert before queue exhaustion.

------------------------------------------------------------------------

## 78. Failure 5 --- Source Down During Write-Behind

Workers fail.

Requirements:

``` text
bounded retry
backoff
queue retention
backpressure
source protection
```

------------------------------------------------------------------------

## 79. Failure 6 --- Duplicate Message

Worker writes source but crashes before acknowledgement.

Message is retried.

Without idempotency:

``` text
duplicate side effect possible
```

------------------------------------------------------------------------

## 80. Failure 7 --- Out-of-Order Writes

Process:

``` text
V10
then V9
```

A version-aware source should reject V9.

------------------------------------------------------------------------

## 81. Failure 8 --- Queue Loss

If application acknowledged writes before durable persistence and the
queue is lost:

``` text
acknowledged data may be lost
```

Document RPO explicitly.

------------------------------------------------------------------------

## 82. Failure 9 --- Backlog Exhaustion

Incoming rate exceeds processing rate for hours.

Potential:

``` text
memory/storage exhaustion
unacceptable source lag
write rejection
```

Backpressure must activate before catastrophic exhaustion.

------------------------------------------------------------------------

## 83. Failure 10 --- Recovery Storm

Source returns after outage.

Thousands of workers/batches immediately replay backlog.

Potential:

``` text
source overload
second outage
```

Ramp recovery deliberately.

------------------------------------------------------------------------

# Troubleshooting

## 84. Read-Through Latency High

Check:

``` text
hit ratio
source loader latency
cache population
stampede
Redis latency
```

The abstraction may hide source fallback from callers.

------------------------------------------------------------------------

## 85. Write-Through Latency High

Break down:

``` text
source write latency
Redis update latency
serialization
network
retry
```

Synchronous design includes dependency latency.

------------------------------------------------------------------------

## 86. Write-Behind Source Is Stale

Check:

``` text
queue depth
oldest message age
consumer lag
worker health
source errors
dead-letter count
```

------------------------------------------------------------------------

## 87. Queue Depth Normal but Age High

Possible:

``` text
low traffic with one stuck old message
partition-specific lag
poison message
```

Monitor both:

``` text
depth
age
```

------------------------------------------------------------------------

## 88. Source Regresses to Older Value

Check:

``` text
out-of-order delivery
missing version check
multiple writers
replay
```

------------------------------------------------------------------------

## 89. Duplicate Business Action

Check:

``` text
worker crash before ack
message redelivery
idempotency key
source transaction
retry logic
```

------------------------------------------------------------------------

# Production Runbooks

## 90. Runbook --- Read-Through Failure

``` text
1. Confirm Redis hit/miss behavior.
2. Check loader errors.
3. Check source availability.
4. Check source latency.
5. Check stampede behavior.
6. Check Redis population errors.
7. Apply source protection.
8. Restore loader/source.
9. Validate hit ratio.
10. Validate request latency.
```

------------------------------------------------------------------------

## 91. Runbook --- Write-Through Failure

``` text
1. Identify source-write result.
2. Identify cache-write result.
3. Do not confuse cache success with source commit.
4. If source failed, fail operation according to contract.
5. If source committed but cache failed, preserve source truth.
6. Invalidate/repair exact cache key.
7. Check broader Redis errors.
8. Validate next read.
9. Record partial-failure metric.
10. Review recurrence.
```

------------------------------------------------------------------------

## 92. Runbook --- Write-Behind Backlog

``` text
1. Measure queue depth.
2. Measure oldest message age.
3. Measure incoming rate.
4. Measure processing rate.
5. Check worker health.
6. Check source latency/errors.
7. Check retry volume.
8. Check poison/dead-letter items.
9. Apply backpressure if required.
10. Scale workers within source capacity.
11. Monitor drain rate.
12. Validate source catches up.
```

------------------------------------------------------------------------

## 93. Runbook --- Write-Behind Source Outage

``` text
1. Confirm source outage.
2. Stop aggressive retries.
3. Protect queue durability.
4. Measure backlog growth.
5. Estimate time to capacity limit.
6. Activate backpressure policy.
7. Communicate persistence lag.
8. Restore source.
9. Ramp consumers gradually.
10. Monitor source latency/errors.
11. Drain backlog.
12. Validate ordering and duplicates.
13. Confirm final source state.
```

------------------------------------------------------------------------

## 94. Runbook --- Duplicate / Out-of-Order Writes

``` text
1. Identify entity.
2. Capture current source version.
3. Capture operation IDs.
4. Capture event versions/order.
5. Stop unsafe replay if needed.
6. Reject stale versions.
7. Apply idempotency checks.
8. Repair source from authoritative business state.
9. Replay only safe operations.
10. Add regression test.
11. Monitor duplicate/stale-write metrics.
```

------------------------------------------------------------------------

## 95. Runbook --- Recovery After Queue Failure

``` text
1. Determine queue failure window.
2. Determine acknowledged-write window.
3. Determine durable messages recovered.
4. Identify potentially lost operations.
5. Compare with source state.
6. Reconcile using authoritative audit/event records.
7. Replay only idempotent/validated operations.
8. Validate per-entity versions.
9. Confirm business correctness.
10. Document actual RPO impact.
11. Correct durability design if required.
```

------------------------------------------------------------------------

# Part 44 --- Observability

## 96. Read-Through Metrics

``` text
read_through_hit_total
read_through_miss_total
loader_total
loader_error_total
loader_latency
cache_population_error_total
```

------------------------------------------------------------------------

## 97. Write-Through Metrics

``` text
write_through_total
source_write_latency
source_write_error_total
cache_write_latency
cache_write_error_total
partial_write_total
```

------------------------------------------------------------------------

## 98. Write-Behind Metrics

``` text
write_behind_accepted_total
queue_depth
queue_oldest_age
consumer_lag
worker_throughput
source_persist_latency
source_persist_error_total
retry_total
dead_letter_total
duplicate_total
stale_version_reject_total
```

------------------------------------------------------------------------

# Part 45 --- Capacity Model

## 99. Required Inputs

For write-behind:

``` text
peak incoming writes/sec
normal worker writes/sec
maximum worker writes/sec
source sustainable writes/sec
average message size
queue retention
maximum acceptable lag
recovery target
```

------------------------------------------------------------------------

## 100. Drain Formula

Conceptually:

``` text
net drain rate =
processing rate - incoming rate
```

Then:

``` text
drain time =
backlog / net drain rate
```

If:

``` text
processing rate <= incoming rate
```

the backlog never drains.

------------------------------------------------------------------------

# Part 46 --- Pattern Decision Template

## 101. Workload Review

``` text
Service:
Entity:
Read/write ratio:
Read latency target:
Write latency target:
Source latency:
Source availability:
Freshness requirement:
Read-your-writes requirement:
Strong consistency required:
Temporary source lag allowed:
Acknowledged data-loss tolerance:
RPO:
RTO:
Batching useful:
Ordering requirement:
Idempotency available:
Durable queue available:
Peak writes/sec:
Recovery capacity:
Selected pattern:
Rationale:
Owner:
```

------------------------------------------------------------------------

# Production Acceptance Checklist

## 102. Read-Through

-   [ ] Loader behavior documented.
-   [ ] Cache hit/miss visible.
-   [ ] Source fallback visible.
-   [ ] Loader timeout defined.
-   [ ] Stampede protection reviewed.
-   [ ] TTL defined.
-   [ ] Loader failure runbook available.

------------------------------------------------------------------------

## 103. Write-Through

-   [ ] Source remains authority.
-   [ ] Success semantics documented.
-   [ ] Source/cache ordering documented.
-   [ ] Source failure behavior documented.
-   [ ] Cache failure after source commit documented.
-   [ ] Partial failures monitored.
-   [ ] Read-after-write behavior validated.
-   [ ] Write-through runbook available.

------------------------------------------------------------------------

## 104. Write-Behind

-   [ ] Acknowledgement boundary documented.
-   [ ] Durability boundary documented.
-   [ ] RPO documented.
-   [ ] Queue durability reviewed.
-   [ ] Queue capacity modeled.
-   [ ] Queue depth monitored.
-   [ ] Oldest message age monitored.
-   [ ] Worker throughput monitored.
-   [ ] Source sustainable rate measured.
-   [ ] Backpressure policy defined.
-   [ ] Retry policy bounded.
-   [ ] Dead-letter policy defined.
-   [ ] Idempotency implemented.
-   [ ] Per-entity ordering reviewed.
-   [ ] Version fencing implemented where required.
-   [ ] Duplicate delivery tested.
-   [ ] Out-of-order delivery tested.
-   [ ] Worker crash tested.
-   [ ] Source outage tested.
-   [ ] Recovery ramp tested.
-   [ ] Backlog drain time modeled.
-   [ ] Queue-loss recovery runbook available.

------------------------------------------------------------------------

# Knowledge Validation

## 105. Questions

You should be able to answer:

1.  What is the difference between cache-aside and read-through?
2.  Why does Redis not automatically know how to load your source?
3.  What does write-through mean?
4.  When should write-through normally return success?
5.  Why is cache-first writing risky when Redis is not authoritative?
6.  What happens when source commits but cache update fails?
7.  What is write-behind?
8.  Why is the acknowledgement boundary critical?
9.  Why can write-behind lose acknowledged data?
10. What makes an asynchronous handoff durable?
11. Why must workers be idempotent?
12. How can a worker crash cause duplicate delivery?
13. Why does per-entity ordering matter?
14. How can versions prevent state regression?
15. What is queue backlog?
16. Why should oldest message age be monitored?
17. What is backpressure?
18. What are the benefits and risks of batching?
19. When is coalescing unsafe?
20. What role can Redis Streams play?
21. Why should a queue message be acknowledged after source persistence?
22. What is a poison message?
23. Why can write-behind improve availability during source outage?
24. Why is catch-up capacity important?
25. How do you select between cache-aside, read-through, write-through,
    and write-behind?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 106. Lab Completion

-   [ ] Implemented read-through wrapper.
-   [ ] Demonstrated read-through miss.
-   [ ] Demonstrated read-through hit.
-   [ ] Implemented write-through simulation.
-   [ ] Verified source state.
-   [ ] Verified cache state.
-   [ ] Implemented teaching write-behind queue.
-   [ ] Demonstrated acknowledgement before persistence.
-   [ ] Processed asynchronous write.
-   [ ] Simulated ordered versions.
-   [ ] Implemented/reviewed version-aware worker.
-   [ ] Tested duplicate operation concept.
-   [ ] Added Redis Stream lab event.
-   [ ] Inspected stream.
-   [ ] Reviewed consumer-group workflow.
-   [ ] Reviewed acknowledgement ordering.
-   [ ] Completed all ten failure scenarios.
-   [ ] Reviewed all six production runbooks.
-   [ ] Completed pattern decision template.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 107. Lab Cleanup

Find chapter keys:

``` redis
SCAN 0 MATCH 'tutorial:chapter14:*' COUNT 100
```

For the lab stream, delete it only if this is an isolated training
environment and cleanup is approved:

``` redis
UNLINK tutorial:chapter14:writes
```

Delete other exact lab keys:

``` redis
UNLINK <exact-key>
```

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

------------------------------------------------------------------------

# 108. Key Takeaways

1.  Read-through centralizes source loading behind a cache/data-access
    abstraction.
2.  Redis alone does not know how to fetch an application's
    authoritative data.
3.  Write-through keeps source persistence in the synchronous success
    path.
4.  Cache success must not be confused with authoritative source commit.
5.  Write-behind acknowledges before the source necessarily contains the
    write.
6.  The acknowledgement and durability boundaries must be explicitly
    documented.
7.  Asynchronous workers must expect duplicate delivery.
8.  Idempotency prevents retries from creating duplicate business
    effects.
9.  Version fencing protects against out-of-order state regression.
10. Write-behind requires queue-depth, lag, age, retry, and dead-letter
    observability.
11. Backpressure prevents unlimited backlog growth.
12. Recovery capacity must exceed normal incoming rate if a backlog is
    to drain.
13. Redis Streams can support queued processing, but durability still
    depends on the complete Redis persistence/HA/recovery design.
14. Write-behind can improve latency and temporary source-outage
    tolerance at the cost of much greater reliability complexity.
15. Pattern selection must begin with consistency, durability, latency,
    RPO/RTO, and source-capacity requirements rather than implementation
    convenience.

------------------------------------------------------------------------

# 109. References

Validate Redis commands, Redis Streams behavior, consumer-group
behavior, persistence, replication, acknowledgement semantics, client
APIs, and Redis Enterprise compatibility against the exact versions
deployed.

Recommended official documentation areas:

-   Redis caching patterns
-   `GET`
-   `SET`
-   `DEL`
-   `UNLINK`
-   Redis Streams
-   `XADD`
-   `XREADGROUP`
-   `XACK`
-   pending entries / consumer groups
-   Redis persistence
-   Redis replication and high availability
-   Redis Enterprise database durability and recovery

Read-through, write-through, and write-behind are architecture patterns.
Their exact durability and consistency properties depend on the
application framework, queue, source system, Redis configuration, and
failure-handling design.

------------------------------------------------------------------------

# Next Chapter

**Chapter 15 --- Cache Stampede, Thundering Herd & Source Protection**

Chapter 15 will go deeply into:

-   stampede mechanics
-   synchronized expiration
-   hot-key misses
-   single-flight
-   distributed loader locks
-   ownership-safe lock release
-   lock TTL sizing
-   request coalescing
-   TTL jitter
-   refresh-ahead
-   stale-while-revalidate
-   source rate limiting
-   circuit breakers
-   retry amplification
-   failure injection
-   load-test methodology
-   source-protection runbooks
