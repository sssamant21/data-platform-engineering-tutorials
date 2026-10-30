# Chapter 13 --- Cache Updates, Invalidation & Consistency

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Intermediate → Production Cache Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Invalidation ordering, concurrent reads/writes,
stale-repopulation races, version fencing, event-driven invalidation,
failure injection, consistency analysis, and production runbooks

------------------------------------------------------------------------

# 1. Objective

Caching becomes difficult when authoritative data changes.

Reading from Redis is simple:

``` text
GET key
```

The harder question is:

> What should happen to the cached value when the source of truth
> changes?

Incorrect invalidation can produce:

``` text
stale data
lost freshness
race conditions
out-of-order cache writes
persistent old values
unnecessary source load
cross-instance inconsistency
```

This chapter builds on Chapter 12's cache-aside pattern and focuses
specifically on cache consistency.

By the end, you should be able to:

-   Compare cache deletion with cache updating.
-   Explain source-first write ordering.
-   Identify invalidation failure windows.
-   Explain stale-repopulation races.
-   Understand delayed second invalidation as a mitigation pattern.
-   Use source versions or timestamps to prevent older data from
    overwriting newer cached state.
-   Design event-driven invalidation.
-   Understand CDC-driven cache invalidation.
-   Handle duplicate and out-of-order events.
-   Design idempotent invalidation consumers.
-   Reason about consistency guarantees.
-   Monitor invalidation health.
-   Troubleshoot stale-cache incidents.
-   Build production invalidation runbooks.

------------------------------------------------------------------------

# 2. Source of Truth

For classic cache-aside:

``` text
Authoritative Store
       |
       v
Application
       |
       v
Redis Cache
```

The authoritative store might be:

``` text
PostgreSQL
MongoDB
MySQL
API/service
document store
another durable system
```

Redis is the performance layer.

The cache must eventually reflect authoritative state.

------------------------------------------------------------------------

# 3. The Core Problem

Assume Redis contains:

``` json
{
  "id": "1001",
  "status": "active"
}
```

The source is updated to:

``` json
{
  "id": "1001",
  "status": "inactive"
}
```

Redis still contains:

``` text
active
```

until one of these occurs:

``` text
explicit invalidation
cache update
TTL expiration
version change
event-driven refresh
```

The consistency design determines how long the mismatch can exist.

------------------------------------------------------------------------

# Part 1 --- Strategy: Delete the Cache

## 4. Source Update Then Delete

Common cache-aside pattern:

``` text
1. Update source.
2. Commit succeeds.
3. Delete/invalidate cache key.
4. Next read misses.
5. Next read reloads source.
```

Conceptually:

``` text
Application
    |
    +----> Source UPDATE
    |         |
    |       success
    |
    +----> Redis UNLINK/DEL
```

------------------------------------------------------------------------

## 5. Why Deletion Is Attractive

Deleting avoids maintaining two representations during the write.

You do not need to guarantee:

``` text
source update format
==
cache serialization format
```

during the write transaction.

The next read reconstructs cache state from the authoritative source.

------------------------------------------------------------------------

# Part 2 --- Strategy: Update the Cache

## 6. Dual Update

Alternative:

``` text
1. Update source.
2. Update Redis.
```

This can reduce the next-read miss.

But now the application must keep:

``` text
source
cache
```

synchronized across separate systems.

------------------------------------------------------------------------

## 7. Dual-Write Failure

Timeline:

``` text
T1 source update succeeds
T2 Redis update fails
```

Result:

``` text
source = new
cache  = old
```

TTL may eventually repair it, but consistency is temporarily broken.

------------------------------------------------------------------------

## 8. Reverse Failure

If code does:

``` text
Redis update
then source update
```

and the source update fails:

``` text
cache = value that never became authoritative
```

This is usually worse.

For cache-aside, source-first ordering is the safer baseline.

------------------------------------------------------------------------

# Part 3 --- Strategy Comparison

## 9. Delete vs Update

  -----------------------------------------------------------------------
  Strategy                Advantage               Risk
  ----------------------- ----------------------- -----------------------
  Source then delete      Simple correctness      Next read misses
  cache                   model                   

  Source then update      Avoids next miss        Dual-write consistency
  cache                                           

  Cache then source       Fast cache change       Cache may represent
                                                  failed source write

  TTL only                Very simple             Staleness lasts until
                                                  expiration
  -----------------------------------------------------------------------

A production design may combine:

``` text
source update
+
cache invalidation
+
TTL safety net
```

------------------------------------------------------------------------

# Part 4 --- Write Ordering

## 10. Why Ordering Matters

Operations across:

``` text
database
Redis
```

are usually not one atomic transaction.

Therefore every ordering creates a failure window.

You must understand the window rather than pretending it does not exist.

------------------------------------------------------------------------

## 11. Recommended Baseline

For cache-aside:

``` text
BEGIN source transaction
UPDATE source
COMMIT source transaction
INVALIDATE cache
```

Only invalidate after the authoritative commit succeeds.

------------------------------------------------------------------------

# Part 5 --- Invalidation Failure

## 12. Failure Window

Timeline:

``` text
T1 source update commits V2
T2 Redis invalidation fails
```

State:

``` text
source = V2
cache  = V1
```

The TTL becomes the fallback repair mechanism.

------------------------------------------------------------------------

## 13. Operational Requirements

Measure:

``` text
cache_invalidation_total
cache_invalidation_error_total
```

Alert based on:

``` text
freshness criticality
failure rate
duration
affected namespace
```

Do not silently ignore invalidation failures.

------------------------------------------------------------------------

# Part 6 --- Concurrent Read/Write Race

## 14. Stale Repopulation

One of the most important cache-aside races:

``` text
T1 Reader A: Redis miss
T2 Reader A: starts source read -> V1
T3 Writer B: source update -> V2
T4 Writer B: invalidates Redis
T5 Reader A: finishes old source read V1
T6 Reader A: writes V1 into Redis
```

Final state:

``` text
source = V2
cache  = V1
```

The invalidation happened correctly, but stale data returned afterward.

------------------------------------------------------------------------

# Part 7 --- Why TTL Still Matters

## 15. Safety Bound

If stale V1 is accidentally repopulated:

``` text
TTL = 5 minutes
```

then the stale entry eventually disappears.

Without TTL:

``` text
stale value may persist indefinitely
```

TTL is not a complete consistency mechanism, but it limits damage.

------------------------------------------------------------------------

# Part 8 --- Delayed Second Invalidation

## 16. Concept

A mitigation sometimes used for read/write races:

``` text
1. Update source.
2. Invalidate cache.
3. Wait longer than expected in-flight stale read.
4. Invalidate same cache key again.
```

Conceptually:

``` text
source update
    |
invalidate
    |
short controlled delay
    |
invalidate again
```

This is often called delayed double deletion.

------------------------------------------------------------------------

## 17. What It Tries to Solve

If an old in-flight reader repopulates stale data after the first
invalidation:

``` text
second invalidation removes it
```

------------------------------------------------------------------------

## 18. Limitations

It is not a mathematical consistency guarantee.

Problems:

``` text
how long should delay be?
source read latency varies
network pauses vary
worker scheduling varies
second delete can fail
more Redis traffic
more application complexity
```

Use only after analyzing the actual race and correctness requirement.

------------------------------------------------------------------------

# Part 9 --- Version-Based Protection

## 19. Version the Source Record

Example authoritative records:

``` json
{
  "id": "1001",
  "status": "active",
  "version": 41
}
```

After update:

``` json
{
  "id": "1001",
  "status": "inactive",
  "version": 42
}
```

Now cache freshness can be reasoned about using:

``` text
version
```

rather than only timing.

------------------------------------------------------------------------

## 20. Cache Version

Cached object:

``` json
{
  "id": "1001",
  "status": "inactive",
  "version": 42
}
```

A stale reader holding:

``` text
version 41
```

should not overwrite cached:

``` text
version 42
```

------------------------------------------------------------------------

# Part 10 --- Atomic Version Check

## 21. Need for Atomicity

This is unsafe:

``` text
GET current cache
compare version in application
SET older/newer value
```

because another writer can change Redis between GET and SET.

Use an atomic mechanism such as:

``` text
Lua script
transaction pattern where appropriate
supported server-side conditional mechanism
```

------------------------------------------------------------------------

## 22. Conceptual Lua

For a simplified numeric-version side key:

``` lua
local current = redis.call("GET", KEYS[1])

if current and tonumber(current) >= tonumber(ARGV[1]) then
    return 0
end

redis.call("SET", KEYS[1], ARGV[1], "EX", ARGV[3])
redis.call("SET", KEYS[2], ARGV[2], "EX", ARGV[3])

return 1
```

A production implementation must ensure the version and value update
form a correct atomic model and that multi-key placement is compatible
with the deployment architecture.

------------------------------------------------------------------------

# Part 11 --- Version in the Cache Key

## 23. Alternative Design

Instead of:

``` text
cache:profile:1001
```

use:

``` text
cache:profile:1001:v42
```

Then newer versions do not overwrite older keys.

But the application must know which version is current.

This can require:

``` text
metadata key
source version lookup
event-driven version pointer
```

It trades overwrite races for key lifecycle complexity.

------------------------------------------------------------------------

# Part 12 --- Timestamp-Based Protection

## 24. Timestamp

A source may expose:

``` text
updated_at
```

Example:

``` text
2026-10-07T12:30:45Z
```

The cache can store it and reject older updates.

But timestamps require care:

``` text
clock consistency
timestamp precision
multiple writes at same timestamp
source semantics
```

A monotonic source version is often easier to reason about when
available.

------------------------------------------------------------------------

# Part 13 --- Event-Driven Invalidation

## 25. Architecture

Instead of the request path directly deleting Redis:

``` text
Source update
     |
     v
Event
     |
     v
Message Broker
     |
     v
Cache Invalidation Consumer
     |
     v
Redis
```

Possible event infrastructure:

``` text
Kafka
Amazon MSK
event bus
queue
CDC platform
```

------------------------------------------------------------------------

## 26. Benefits

``` text
decouples writer from cache
supports multiple cache consumers
centralizes invalidation logic
provides replay possibilities
can scale independently
```

------------------------------------------------------------------------

## 27. Risks

``` text
event delay
duplicate events
out-of-order events
consumer outage
poison events
broker outage
schema changes
replay behavior
```

Event-driven invalidation introduces distributed-system complexity.

------------------------------------------------------------------------

# Part 14 --- Event Payload

## 28. Example

``` json
{
  "event_type": "profile.updated",
  "profile_id": "1001",
  "version": 42,
  "occurred_at": "2026-10-07T12:30:45Z"
}
```

The invalidation consumer can derive:

``` text
cache:profile:1001:v1
```

and invalidate it.

Avoid putting unnecessary sensitive data into invalidation events.

------------------------------------------------------------------------

# Part 15 --- Idempotent Invalidation

## 29. Duplicate Events

Suppose the same event arrives twice.

Consumer performs:

``` redis
UNLINK cache:profile:1001:v1
```

twice.

The second delete simply finds the key absent.

This makes deletion naturally convenient for idempotent event
processing.

**Safety/expected result:** `cache:profile:1001:v1` is an illustrative application key, not a lab-owned namespace. Never paste it into an unapproved shared environment. In a dedicated synthetic test, the first `UNLINK` returns `1` if present and the second normally returns `0`; the example explains the keyspace effect, not memory-reclamation timing.

------------------------------------------------------------------------

# Part 16 --- Out-of-Order Events

## 30. Example

Events arrive:

``` text
version 42
then
version 41
```

If both only delete:

``` text
deleting an already absent key is generally harmless
```

If events rewrite cache contents:

``` text
version 41 could overwrite version 42
```

This is another reason invalidation is often simpler than event-driven
cache updating.

------------------------------------------------------------------------

# Part 17 --- CDC-Driven Invalidation

## 31. Change Data Capture

CDC observes authoritative data changes and emits change records.

Conceptually:

``` text
Database
   |
   v
CDC
   |
   v
Kafka / Event Stream
   |
   v
Invalidation Consumer
   |
   v
Redis
```

This can remove cache invalidation logic from individual writers.

------------------------------------------------------------------------

## 32. CDC Benefits

``` text
captures changes from multiple writers
centralized cache consistency
audit/replay capability
less application coupling
```

------------------------------------------------------------------------

## 33. CDC Risks

``` text
CDC lag
connector outage
consumer lag
schema changes
duplicate events
replay storms
incorrect key mapping
```

Monitor end-to-end invalidation lag.

------------------------------------------------------------------------

# Part 18 --- Invalidation Lag

## 34. Definition

Conceptually:

``` text
invalidation lag =
cache invalidation time - source commit time
```

If business tolerance is:

``` text
30 seconds
```

and CDC lag becomes:

``` text
10 minutes
```

the cache consistency SLO is violated even if Redis is healthy.

------------------------------------------------------------------------

# Part 19 --- Multi-Instance Applications

## 35. Local Memory + Redis

Some applications have:

``` text
L1 local process cache
L2 Redis
L3 source database
```

Now invalidation must consider:

``` text
all application instances
+
Redis
```

Deleting only Redis does not invalidate stale values already stored in
process memory.

------------------------------------------------------------------------

## 36. Multi-Level Invalidation

Conceptually:

``` text
Source change
    |
    v
Invalidation event
    |
    +----> Redis invalidation
    |
    +----> App instance A local cache
    |
    +----> App instance B local cache
    |
    +----> App instance C local cache
```

This requires coordinated invalidation or deliberately short local TTLs.

------------------------------------------------------------------------

# Part 20 --- Partial Updates

## 37. Cached Aggregate

Suppose cache contains:

``` json
{
  "id": "1001",
  "name": "Alice",
  "address": "A",
  "status": "active"
}
```

Source update changes only:

``` text
address
```

Should Redis patch only the address?

Possible, but now cache logic must reproduce source update semantics
correctly.

Simpler:

``` text
invalidate whole cached aggregate
```

when the next read can cheaply reconstruct it.

------------------------------------------------------------------------

# Part 21 --- Derived Cache Entries

## 38. One Source Change, Many Keys

A source update may affect:

``` text
cache:profile:1001
cache:profile-summary:1001
cache:search-result:region:north
cache:dashboard:customer:500
```

Invalidation becomes dependency management.

------------------------------------------------------------------------

## 39. Dependency Registry

For complex caching, document:

``` text
source entity
affected cache namespaces
invalidation trigger
owner
TTL fallback
```

Example:

  Source Entity   Cache Namespace     Trigger           TTL
  --------------- ------------------- ----------------- -------
  Profile         `cache:profile:*`   profile.updated   5 min
  Profile         `cache:summary:*`   profile.updated   2 min

------------------------------------------------------------------------

# Part 22 --- Broad Invalidation

## 40. Avoid Wildcard Deletes

Do not solve dependency complexity with:

``` text
find every matching production key and delete everything
```

Broad scans/deletes can create:

``` text
Redis load
mass cache misses
source overload
```

Prefer precise key derivation.

------------------------------------------------------------------------

# Part 23 --- Generational / Namespace Versioning

## 41. Generation Pattern

Instead of deleting millions of keys, applications can sometimes use a
generation:

``` text
cache:catalog:g17:item:1001
```

A new generation:

``` text
g18
```

causes applications to stop reading old-generation keys.

Old keys expire naturally.

------------------------------------------------------------------------

## 42. Tradeoff

Benefits:

``` text
fast logical invalidation
avoids mass delete
```

Costs:

``` text
temporary duplicate memory
generation coordination
old-key cleanup via TTL
```

Useful for large cache sets when designed carefully.

------------------------------------------------------------------------

# Part 24 --- Consistency Models

## 43. Strong Consistency

Every read sees the latest committed write.

Classic cache-aside generally does not provide this automatically across
independent source and cache systems.

If strict strong consistency is mandatory, caching strategy must be
designed accordingly.

------------------------------------------------------------------------

## 44. Eventual Consistency

Cache may temporarily differ from source but converges through:

``` text
invalidation
TTL
refresh
event processing
```

Many cache-aside systems operate here.

------------------------------------------------------------------------

## 45. Bounded Staleness

A useful cache requirement:

``` text
cached data may be at most N minutes stale
```

TTL plus invalidation monitoring can support this model.

Example:

``` text
maximum tolerated stale window = 5 minutes
```

Now TTL and invalidation SLOs have a business basis.

------------------------------------------------------------------------

# Part 25 --- Read-Your-Writes

## 46. Requirement

A user updates a record and immediately reads it.

They expect:

``` text
new value
```

But if cache invalidation is delayed:

``` text
old value may be returned
```

Possible solutions depend on architecture:

``` text
invalidate synchronously after commit
bypass cache for immediate follow-up read
session-local version knowledge
version-aware cache
```

Define whether read-your-writes is required.

------------------------------------------------------------------------

# Part 26 --- Failure Windows

## 47. Source Commit + Invalidation

Window:

``` text
source commit succeeds
invalidation not yet completed
```

Potential stale read.

------------------------------------------------------------------------

## 48. Event-Based Invalidation

Window:

``` text
source commit
event publish
broker
consumer
Redis delete
```

Each stage adds potential delay.

------------------------------------------------------------------------

## 49. TTL-Only

Window:

``` text
up to remaining TTL
```

Simple but often much larger.

------------------------------------------------------------------------

# Part 27 --- Observability

## 50. Required Metrics

Capture:

``` text
cache_invalidation_total
cache_invalidation_success_total
cache_invalidation_error_total
cache_invalidation_latency
cache_stale_detected_total
cache_version_reject_total
invalidation_event_total
invalidation_event_error_total
invalidation_consumer_lag
invalidation_age
```

------------------------------------------------------------------------

## 51. Correlate With

``` text
source update rate
cache hit rate
Redis errors
application latency
source latency
event-broker lag
consumer restarts
```

------------------------------------------------------------------------

# Part 28 --- Logging

## 52. Useful Structured Fields

Example:

``` json
{
  "event": "cache_invalidation",
  "namespace": "profile",
  "entity_id": "1001",
  "source_version": 42,
  "result": "success"
}
```

Do not log sensitive payloads unnecessarily.

------------------------------------------------------------------------

# Hands-On Lab

## 53. Lab Namespace

Use:

``` text
tutorial:chapter13:
```

Use a simulated authoritative store.

------------------------------------------------------------------------

## 54. Source Store

``` python
SOURCE = {
    "1001": {
        "id": "1001",
        "status": "active",
        "version": 1,
    }
}
```

------------------------------------------------------------------------

## 55. Cache Key

``` python
def cache_key(profile_id):
    return f"tutorial:chapter13:profile:{profile_id}"
```

------------------------------------------------------------------------

## 56. Read Function

``` python
import json

def get_profile(r, profile_id):
    key = cache_key(profile_id)

    cached = r.get(key)

    if cached is not None:
        return json.loads(cached)

    value = SOURCE.get(profile_id)

    if value is None:
        return None

    r.set(
        key,
        json.dumps(value),
        ex=120,
    )

    return value
```

------------------------------------------------------------------------

# Part 29 --- Basic Invalidation Lab

## 57. Populate

``` python
print(get_profile(r, "1001"))
```

Verify:

``` redis
GET tutorial:chapter13:profile:1001
TTL tutorial:chapter13:profile:1001
```

------------------------------------------------------------------------

## 58. Update Source

``` python
SOURCE["1001"] = {
    "id": "1001",
    "status": "inactive",
    "version": 2,
}
```

Redis still contains old data.

------------------------------------------------------------------------

## 59. Invalidate

``` redis
UNLINK tutorial:chapter13:profile:1001
```

Read again:

``` python
print(get_profile(r, "1001"))
```

Expected:

``` text
version 2
status inactive
```

------------------------------------------------------------------------

# Part 30 --- Invalidation Failure Lab

## 60. Simulate Failure

Conceptually:

``` text
source update succeeds
Redis temporarily unavailable
invalidation fails
```

Record:

``` text
source version
cached version
TTL remaining
```

Observe the stale-data window.

------------------------------------------------------------------------

# Part 31 --- Stale Repopulation Race Lab

## 61. Simulated Slow Read

``` python
import copy
import time

def slow_source_read(profile_id):
    value = copy.deepcopy(SOURCE[profile_id])
    time.sleep(2)
    return value
```

Sequence:

``` text
1. Remove cache.
2. Start slow read that captures version 1.
3. Update source to version 2.
4. Invalidate cache.
5. Allow slow reader to cache version 1.
```

Expected:

``` text
cache can become stale after invalidation
```

This is the critical race to understand.

------------------------------------------------------------------------

# Part 32 --- Version Comparison Lab

## 62. Read Cached Version

Cached JSON includes:

``` json
{
  "version": 2
}
```

Before replacing it with source data, compare versions.

Conceptually:

``` python
if incoming_version < cached_version:
    reject_cache_write()
```

But production comparison-and-write must be atomic.

------------------------------------------------------------------------

# Part 33 --- Event Invalidation Lab

## 63. Simulated Event

``` python
event = {
    "event_type": "profile.updated",
    "profile_id": "1001",
    "version": 3,
}
```

Consumer:

``` python
def handle_event(r, event):
    if event["event_type"] == "profile.updated":
        r.unlink(cache_key(event["profile_id"]))
```

Run twice.

Expected:

``` text
duplicate processing is harmless
```

------------------------------------------------------------------------

# Part 34 --- Out-of-Order Event Lab

## 64. Events

``` python
events = [
    {"profile_id": "1001", "version": 4},
    {"profile_id": "1001", "version": 3},
]
```

If handler only invalidates:

``` text
both are safe to process repeatedly
```

If handler writes cached data:

``` text
version ordering must be enforced
```

------------------------------------------------------------------------

# Failure Injection

## 65. Failure 1 --- Source Succeeds, Invalidation Fails

State:

``` text
source new
cache old
```

Mitigation:

``` text
TTL
retry if safe
alert
repair exact key
```

------------------------------------------------------------------------

## 66. Failure 2 --- Cache Updated Before Source, Source Fails

State:

``` text
cache contains uncommitted/non-authoritative value
```

Lesson:

``` text
do not treat cache as commit authority
```

------------------------------------------------------------------------

## 67. Failure 3 --- Stale Repopulation

State:

``` text
source V2
cache V1
```

after apparently successful invalidation.

Investigate concurrent source reads.

------------------------------------------------------------------------

## 68. Failure 4 --- Duplicate Event

Same invalidation event processed twice.

Expected with delete-based invalidation:

``` text
idempotent behavior
```

------------------------------------------------------------------------

## 69. Failure 5 --- Out-of-Order Cache Update Events

Events:

``` text
V42
V41
```

If consumer writes values blindly:

``` text
V41 may overwrite V42
```

Use version fencing or invalidate instead.

------------------------------------------------------------------------

## 70. Failure 6 --- Consumer Lag

Source:

``` text
V50
```

Redis:

``` text
V45
```

Invalidation consumer:

``` text
10 minutes behind
```

Redis may be perfectly healthy.

The consistency system is not.

------------------------------------------------------------------------

## 71. Failure 7 --- Local L1 Cache Not Invalidated

Redis is fresh.

Application instance still serves stale in-process value.

Troubleshoot every cache layer.

------------------------------------------------------------------------

## 72. Failure 8 --- Broad Invalidation Storm

Deployment invalidates:

``` text
millions of keys
```

simultaneously.

Potential result:

``` text
mass cache misses
source overload
Redis delete load
```

Use staged/generational strategies where appropriate.

------------------------------------------------------------------------

## 73. Failure 9 --- TTL Too Long for Failure Window

Invalidation fails.

TTL:

``` text
24 hours
```

Freshness requirement:

``` text
5 minutes
```

TTL safety net does not satisfy the business requirement.

------------------------------------------------------------------------

## 74. Failure 10 --- Derived Cache Missed

Source entity changes.

Primary cache invalidated:

``` text
cache:profile:1001
```

but derived cache remains:

``` text
cache:profile-summary:1001
```

Result:

``` text
partial consistency
```

Maintain dependency mapping.

------------------------------------------------------------------------

# Troubleshooting

## 75. User Reports Old Data

Start:

``` text
exact entity
source current value
cache current value
source version
cache version
TTL
```

Then build the timeline.

------------------------------------------------------------------------

## 76. Source New, Redis Old

Check:

``` text
invalidation called?
invalidation succeeded?
correct key?
correct namespace?
Redis connectivity?
consumer lag?
TTL?
```

------------------------------------------------------------------------

## 77. Redis Became Old After Successful Invalidation

Suspect:

``` text
stale repopulation race
out-of-order event
old writer
local cache layer
```

------------------------------------------------------------------------

## 78. Only Some App Instances Serve Old Data

Check:

``` text
L1/local cache
instance-specific configuration
event subscription
deployment version
```

Redis may not be the stale layer.

------------------------------------------------------------------------

## 79. Staleness Appears During High Load

Check:

``` text
consumer lag
source latency
in-flight reads
retry queues
broker lag
cache population races
```

High latency increases race windows.

------------------------------------------------------------------------

# Production Runbooks

## 80. Runbook --- Stale Cache Incident

``` text
1. Identify exact entity/key.
2. Read authoritative value.
3. Read cached value.
4. Capture source version/timestamp.
5. Capture cache version/timestamp.
6. Capture TTL.
7. Review source commit time.
8. Review invalidation log/event.
9. Review invalidation result.
10. Review consumer lag.
11. Review concurrent cache population.
12. Review local cache layers.
13. Invalidate exact stale key safely.
14. Validate next read.
15. Identify race/failure mechanism.
16. Implement permanent correction.
```

------------------------------------------------------------------------

## 81. Runbook --- Invalidation Error Spike

``` text
1. Confirm affected namespace.
2. Measure failure rate.
3. Check Redis connectivity.
4. Check authentication/authorization.
5. Check application deployment.
6. Check key construction.
7. Check source update rate.
8. Estimate stale-data exposure.
9. Apply bounded retry if safe.
10. Repair exact affected keys.
11. Monitor recovery.
12. Review TTL safety bound.
```

------------------------------------------------------------------------

## 82. Runbook --- Event Consumer Lag

``` text
1. Measure current lag.
2. Determine oldest unprocessed event.
3. Check consumer health.
4. Check broker health.
5. Check processing errors.
6. Check poison events.
7. Check Redis latency/errors.
8. Scale/recover consumer safely.
9. Avoid uncontrolled replay storm.
10. Monitor source and Redis load.
11. Confirm lag returns to target.
12. Validate cache freshness.
```

------------------------------------------------------------------------

## 83. Runbook --- Out-of-Order Update

``` text
1. Capture source current version.
2. Capture cached version.
3. Capture event versions/order.
4. Identify writer/consumer.
5. Stop blind cache updates if necessary.
6. Invalidate affected key.
7. Repopulate from source.
8. Add version fencing.
9. Test duplicate/out-of-order delivery.
10. Monitor version-reject metrics.
```

------------------------------------------------------------------------

## 84. Runbook --- Broad Cache Invalidation

``` text
1. Identify required cache scope.
2. Estimate key count.
3. Estimate Redis deletion load.
4. Estimate source miss load.
5. Determine whether precise invalidation is possible.
6. Consider namespace generation.
7. Add TTL/jitter where appropriate.
8. Stage rollout.
9. Protect source.
10. Monitor Redis.
11. Monitor source QPS/latency.
12. Stop/slow invalidation if downstream risk rises.
13. Validate cache rebuild.
```

------------------------------------------------------------------------

# Part 35 --- Design Review Template

## 85. Cache Consistency Design

``` text
Service:
Source of truth:
Cache namespace:
Cached entity:
Source version field:
Freshness requirement:
TTL:
Invalidation trigger:
Invalidation method:
Delete or update:
Write ordering:
Event-driven:
CDC-driven:
Expected event lag:
Duplicate handling:
Out-of-order handling:
Local cache layers:
Derived cache dependencies:
Version fencing:
Read-your-writes requirement:
Failure repair:
Metrics:
Alerts:
Owner:
Runbook:
```

------------------------------------------------------------------------

# Part 36 --- Consistency Decision Matrix

## 86. Example

  -----------------------------------------------------------------------
  Requirement                         Possible Design Direction
  ----------------------------------- -----------------------------------
  Minutes of staleness acceptable     Cache-aside + TTL

  Fast freshness after writes         Source-first + invalidation

  Multiple writers                    CDC/event-driven invalidation

  Duplicate events expected           Idempotent delete

  Out-of-order value updates          Version fencing

  Millions of related keys            Generational invalidation

  L1 + Redis caches                   Multi-layer invalidation

  Read-your-writes required           Synchronous
                                      invalidation/bypass/version-aware
                                      design
  -----------------------------------------------------------------------

This is an engineering guide, not a universal prescription.

------------------------------------------------------------------------

# Production Acceptance Checklist

## 87. Consistency Readiness

-   [ ] Source of truth documented.
-   [ ] Cache ownership documented.
-   [ ] Freshness requirement documented.
-   [ ] TTL satisfies stale-data safety bound.
-   [ ] Source-first write ordering reviewed.
-   [ ] Delete-vs-update strategy documented.
-   [ ] Invalidation failure behavior documented.
-   [ ] Stale-repopulation race reviewed.
-   [ ] Version field available where required.
-   [ ] Version fencing implemented where required.
-   [ ] Delayed second invalidation justified if used.
-   [ ] Event invalidation is idempotent.
-   [ ] Duplicate events tested.
-   [ ] Out-of-order events tested.
-   [ ] Consumer lag monitored.
-   [ ] CDC lag monitored where applicable.
-   [ ] L1/local caches included in design.
-   [ ] Derived-cache dependencies documented.
-   [ ] Broad invalidation risk reviewed.
-   [ ] Generational invalidation considered where appropriate.
-   [ ] Read-your-writes requirement documented.
-   [ ] Invalidation metrics available.
-   [ ] Stale-cache metrics available.
-   [ ] Stale-cache runbook available.
-   [ ] Invalidation-error runbook available.
-   [ ] Consumer-lag runbook available.
-   [ ] Out-of-order runbook available.
-   [ ] Broad-invalidation runbook available.

------------------------------------------------------------------------

# Knowledge Validation

## 88. Questions

You should be able to answer:

1.  Why does source-first ordering matter?
2.  Why is cache deletion often simpler than cache updating?
3.  What happens if source update succeeds but invalidation fails?
4.  How does TTL limit the impact?
5.  What is the stale-repopulation race?
6.  Why can stale data appear after successful invalidation?
7.  What is delayed double deletion trying to solve?
8.  Why is delayed double deletion not a full consistency guarantee?
9.  How can source versions improve cache correctness?
10. Why must version comparison and cache write be atomic?
11. What are the tradeoffs of versioned cache keys?
12. Why can timestamps be harder than monotonic versions?
13. What is event-driven invalidation?
14. Why is deletion naturally idempotent?
15. Why are out-of-order events more dangerous when they update values?
16. What is CDC-driven invalidation?
17. What is invalidation lag?
18. Why must local process caches participate in invalidation?
19. What are derived cache dependencies?
20. Why can broad invalidation overload the source?
21. What is generational invalidation?
22. What is bounded staleness?
23. Why does cache-aside not automatically provide strong consistency?
24. What is read-your-writes?
25. Which metrics reveal invalidation health?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 89. Lab Completion

-   [ ] Populated source and cache.
-   [ ] Updated source.
-   [ ] Observed stale cached data.
-   [ ] Invalidated exact key.
-   [ ] Verified fresh repopulation.
-   [ ] Simulated invalidation failure.
-   [ ] Measured TTL safety window.
-   [ ] Simulated stale-repopulation race.
-   [ ] Reviewed delayed second invalidation.
-   [ ] Added source versions.
-   [ ] Reviewed atomic version fencing.
-   [ ] Processed duplicate invalidation event.
-   [ ] Reviewed out-of-order event handling.
-   [ ] Reviewed CDC invalidation architecture.
-   [ ] Reviewed consumer lag.
-   [ ] Reviewed multi-level cache invalidation.
-   [ ] Reviewed derived cache dependencies.
-   [ ] Reviewed broad invalidation.
-   [ ] Reviewed generational invalidation.
-   [ ] Completed all ten failure scenarios.
-   [ ] Reviewed all production runbooks.

------------------------------------------------------------------------

# 90. Lab Cleanup

Find chapter keys:

``` redis
SCAN 0 MATCH 'tutorial:chapter13:*' COUNT 100
```

Delete only exact lab keys:

``` redis
UNLINK <exact-key>
```

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

------------------------------------------------------------------------

# 91. Key Takeaways

1.  Cache invalidation is a distributed consistency problem, not merely
    a Redis command.
2.  Source-first ordering prevents Redis from becoming the authority for
    an uncommitted write.
3.  Deleting cache entries is often easier to reason about than
    dual-writing values.
4.  Every source/cache ordering has a failure window.
5.  TTL is the fallback stale-data bound when invalidation fails.
6.  Concurrent readers can repopulate stale data after a correct
    invalidation.
7.  Delayed second invalidation can reduce a specific race but does not
    guarantee strong consistency.
8.  Monotonic source versions can prevent older data from replacing
    newer cache state.
9.  Event-driven invalidation must handle duplicates, ordering, lag, and
    replay.
10. Delete-based invalidation is naturally easier to make idempotent.
11. CDC can centralize invalidation across multiple source writers.
12. Consumer/CDC lag is a cache-freshness metric.
13. Local L1 caches and derived caches must be included in the
    consistency model.
14. Broad invalidation can create a source-system incident.
15. Production cache consistency must be defined using explicit
    freshness requirements and observable failure bounds.

------------------------------------------------------------------------

# 92. References

Validate all Redis command behavior, scripting behavior,
cluster/multi-key restrictions, client semantics, and Redis Enterprise
compatibility against the exact versions deployed.

Recommended official documentation areas:

-   Redis caching patterns
-   cache-aside
-   `SET`
-   `GET`
-   `DEL`
-   `UNLINK`
-   `EXPIRE`
-   `TTL`
-   Lua scripting
-   transactions
-   Redis keyspace notifications where relevant
-   Redis Streams where used for event processing
-   Redis Enterprise client and database behavior

Event-driven and CDC invalidation are architectural patterns whose exact
implementation depends on the source database, broker, CDC platform,
client framework, and consistency requirements.

------------------------------------------------------------------------

# Next Chapter

**Chapter 14 --- Write-Through, Write-Behind & Read-Through Patterns**

Chapter 14 will compare caching models and cover:

-   read-through
-   write-through
-   write-behind/write-back
-   source/cache ownership
-   synchronous vs asynchronous writes
-   durability boundaries
-   write queues
-   ordering
-   retries
-   duplicate writes
-   failure recovery
-   data-loss windows
-   consistency tradeoffs
-   hands-on simulations
-   production pattern-selection guidance
