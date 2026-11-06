# Chapter 20 --- Redis Cache Invalidation, Consistency & Change Propagation

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Intermediate → Production Cache Consistency Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Cache-aside invalidation, update/delete ordering,
stale-repopulation races, versioned values, event-driven invalidation,
idempotency, lost-event recovery, reconciliation, failure injection,
observability, troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Caching introduces another copy of data.

The moment an application has:

``` text
source of truth
+
Redis cached copy
```

it must answer:

> How does Redis learn that the source changed?

TTL alone may eventually correct stale data, but many workloads require
faster propagation.

By the end, you should be able to:

-   Define cache invalidation and consistency boundaries.
-   Identify the source of truth.
-   Explain cache-aside update and delete behavior.
-   Understand write/invalidation ordering.
-   Reproduce stale-repopulation races.
-   Prevent older data from overwriting newer cache state.
-   Use version-aware cache writes.
-   Understand delete invalidation.
-   Design event-driven invalidation.
-   Understand CDC-based propagation.
-   Explain Pub/Sub delivery limitations in an invalidation
    architecture.
-   Build idempotent consumers.
-   Detect lost or delayed invalidations.
-   Reconcile cache state after failures.
-   Observe invalidation lag and failures.
-   Troubleshoot stale-cache incidents.
-   Build production runbooks and acceptance criteria.

------------------------------------------------------------------------

# 2. Core Production Principle

The cache is usually not the source of truth.

For a cache-aside design:

``` text
authoritative source
        |
        v
      Redis
        |
        v
 application reads
```

Redis should be treated as a derived representation that can be:

``` text
missing
stale
evicted
expired
partially updated
temporarily unavailable
```

The application must remain correct under those conditions.

------------------------------------------------------------------------

# Part 1 --- Source of Truth

## 3. Ownership

Before designing invalidation, identify:

``` text
Who owns the authoritative record?
Who is allowed to update it?
Who creates the cache entry?
Who invalidates the cache?
Who detects propagation failure?
```

Ambiguous ownership produces stale-data incidents.

------------------------------------------------------------------------

## 4. Redis as Derived State

For ordinary caching:

``` text
database/source = truth
Redis = optimization
```

Do not reverse this relationship accidentally unless Redis is
intentionally the authoritative datastore for that use case.

------------------------------------------------------------------------

# Part 2 --- Why Invalidation Is Hard

## 5. Multiple Timelines

A write can involve:

``` text
application
database
Redis
message broker
CDC system
other application instances
```

Each component can:

``` text
succeed
fail
timeout
retry
reorder
delay
```

Consistency engineering is largely about controlling these timelines.

------------------------------------------------------------------------

# Part 3 --- Cache-Aside Read

## 6. Basic Flow

``` text
GET cache
  |
 HIT -> return
  |
 MISS
  |
 read source
  |
 populate cache
  |
 return
```

This is simple until a source update occurs concurrently.

------------------------------------------------------------------------

# Part 4 --- Update Invalidation

## 7. Common Pattern

A common cache-aside update flow is:

``` text
update source
   |
source commit succeeds
   |
invalidate Redis key
```

The next read repopulates from the new source state.

------------------------------------------------------------------------

## 8. Why Source First?

If Redis is invalidated first and the source update later fails:

``` text
cache deleted
source remains old
next read reloads old value
```

This may be acceptable for availability but it does not accomplish the
intended update.

More dangerous races can occur when reads overlap the write.

------------------------------------------------------------------------

# Part 5 --- Delete vs. Update Cache

## 9. Delete-on-Write

After updating the source:

``` redis
DEL cache:key
```

or, where appropriate:

``` redis
UNLINK cache:key
```

Then future reads rebuild the cache.

**Safety/expected result:** `cache:key` is a conceptual application key. Use only an approved disposable key for hands-on testing and never delete production/shared application data to prove the pattern. `DEL`/`UNLINK` return `1` if a key existed or `0` otherwise; source-of-truth write/commit and concurrent request ordering are application concerns beyond this single Redis command.

This avoids having the write path reproduce every cache transformation.

------------------------------------------------------------------------

## 10. Update-on-Write

Another design writes the new value directly to Redis after source
commit.

Benefits:

``` text
next read can hit immediately
```

Risks:

``` text
cache transformation duplicated
partial failure
ordering races
multiple cache representations
```

------------------------------------------------------------------------

# Part 6 --- The Classic Stale-Repopulation Race

## 11. Timeline

Consider:

``` text
Reader A -> cache MISS
Reader A -> reads source version 10

Writer B -> updates source to version 11
Writer B -> deletes cache

Reader A -> writes old version 10 into cache
```

Final state:

``` text
source = version 11
cache  = version 10
```

The invalidation succeeded, yet the cache became stale afterward.

------------------------------------------------------------------------

# Part 7 --- Why Delete Alone Is Not a Complete Consistency Protocol

## 12. In-Flight Readers

Deleting the key removes current cache state.

It does not cancel:

``` text
old source reads
in-flight loaders
delayed workers
retries
```

A stale writer can repopulate after invalidation.

------------------------------------------------------------------------

# Part 8 --- Version-Aware Values

## 13. Include Version

Cache payload:

``` json
{
  "id": 1001,
  "version": 11,
  "value": "new"
}
```

A version may come from:

``` text
monotonic record version
update sequence
source commit version
event sequence
logical revision
```

Use a value with ordering semantics appropriate to the source.

------------------------------------------------------------------------

# Part 9 --- Compare Before Replace

## 14. Goal

Do not allow:

``` text
version 10
```

to overwrite:

``` text
version 11
```

The compare-and-write must be atomic if multiple clients race.

------------------------------------------------------------------------

# Part 10 --- Lua Version Guard

## 15. Concept

For a simple lab, store:

``` text
version key
data key
```

and use Lua to compare the incoming version with the current cached
version before replacing it.

Production implementations must consider atomicity, data model,
cluster/shard placement, serialization, and failure semantics.

------------------------------------------------------------------------

# Part 11 --- Versioned Key Names

## 16. Alternative Pattern

Instead of overwriting:

``` text
product:1001
```

use:

``` text
product:1001:v11
```

and separately identify the current version.

This can make stale writes less destructive but introduces:

``` text
extra keys
cleanup
pointer/version management
memory overhead
```

------------------------------------------------------------------------

# Part 12 --- Namespace Versioning

## 17. Deployment-Level Invalidation

For broad schema/cache changes:

``` text
cache:v1:...
cache:v2:...
```

A new namespace avoids mixing incompatible representations.

Chapter 16 warming principles should be used to avoid a cold-start
storm.

------------------------------------------------------------------------

# Part 13 --- Delete Invalidation

## 18. Source Record Deleted

If the source record is removed:

``` text
delete source
 -> invalidate positive cache
 -> consider negative cache
```

Be careful that an in-flight old reader does not restore the deleted
record into Redis.

Version/tombstone strategies can help.

------------------------------------------------------------------------

# Part 14 --- Tombstones

## 19. Concept

A tombstone represents:

``` text
record intentionally deleted
```

with a version.

Example:

``` json
{
  "id": 1001,
  "version": 12,
  "deleted": true
}
```

An older version 11 loader should not overwrite version 12 deletion
state.

------------------------------------------------------------------------

# Part 15 --- TTL as Safety Net

## 20. TTL Is Still Valuable

Even with event-driven invalidation, TTL provides eventual cleanup when:

``` text
event is lost
consumer is down
bug skips invalidation
network fails
```

TTL should not be the only consistency mechanism when freshness
requirements demand faster correction.

------------------------------------------------------------------------

# Part 16 --- Event-Driven Invalidation

## 21. Flow

``` text
source update
   |
change event
   |
broker / event system
   |
cache invalidator
   |
Redis invalidate/update
```

This decouples source writes from cache consumers.

------------------------------------------------------------------------

# Part 17 --- Event Requirements

## 22. Useful Fields

An invalidation event often needs:

``` text
entity ID
entity type
operation
version
event ID
event timestamp
schema version
```

Do not publish sensitive payload fields unnecessarily.

------------------------------------------------------------------------

# Part 18 --- Idempotency

## 23. Duplicate Events Are Normal

Distributed delivery can produce duplicates.

Processing the same invalidation twice should remain safe.

Example:

``` text
DEL key
DEL key again
```

is naturally tolerant.

More complex update events need explicit idempotency/version checks.

------------------------------------------------------------------------

# Part 19 --- Event Ordering

## 24. Out-of-Order Example

Consumer receives:

``` text
version 12
then version 11
```

If it blindly writes both:

``` text
final cache = stale version 11
```

Version-aware processing should reject older events.

------------------------------------------------------------------------

# Part 20 --- Event Delay

## 25. Invalidation Lag

If source changes at:

``` text
10:00:00
```

but cache invalidation occurs at:

``` text
10:00:30
```

the cache may serve stale data for 30 seconds.

Track invalidation lag.

------------------------------------------------------------------------

# Part 21 --- Lost Events

## 26. Failure Mode

If an event never reaches the invalidator:

``` text
source changes
cache remains old
```

Recovery mechanisms can include:

``` text
TTL
replayable event log
CDC offsets
reconciliation
manual invalidation
```

------------------------------------------------------------------------

# Part 22 --- Redis Pub/Sub Considerations

## 27. Delivery Model

Redis Pub/Sub can be useful for real-time notifications, but an
invalidation design requiring durable replay must account for Pub/Sub's
delivery characteristics.

Do not assume that a disconnected consumer can automatically replay
missed Pub/Sub messages.

For durable invalidation pipelines, use a mechanism with the required
persistence/replay semantics.

------------------------------------------------------------------------

# Part 23 --- CDC-Based Invalidation

## 28. Change Data Capture

Conceptual flow:

``` text
database commit
   |
CDC
   |
durable event stream
   |
cache invalidator
   |
Redis
```

Advantages:

``` text
source-aligned changes
centralized propagation
replay potential depending on platform
```

Risks:

``` text
lag
schema evolution
ordering
duplicates
consumer failure
offset management
```

------------------------------------------------------------------------

# Part 24 --- Transactional Gap

## 29. Dual-Write Problem

Application performs:

``` text
1. database commit
2. publish invalidation event
```

If step 1 succeeds and step 2 fails, cache may remain stale.

This is a classic dual-write consistency problem.

Architectures may use:

``` text
transactional outbox
CDC
reconciliation
TTL safety net
```

depending on requirements.

------------------------------------------------------------------------

# Part 25 --- Transactional Outbox

## 30. Concept

Write:

``` text
business change
+
outbox record
```

within the source transaction.

A separate publisher emits the event.

This reduces the gap between committed source state and change-event
creation.

Implementation depends on the authoritative datastore.

------------------------------------------------------------------------

# Part 26 --- Reconciliation

## 31. Purpose

Reconciliation detects divergence after the fact.

Examples:

``` text
sample source vs. cache versions
replay changes after checkpoint
scan known entity set
compare update timestamps
```

Avoid expensive full-dataset comparisons unless explicitly designed and
capacity-tested.

------------------------------------------------------------------------

# Part 27 --- Consistency Levels

## 32. Define the Requirement

Possible contracts:

``` text
eventual within 5 minutes
eventual within 30 seconds
read-your-write
monotonic version
strict no-stale serving
```

Do not use the word "consistent" without defining the actual
requirement.

------------------------------------------------------------------------

# Part 28 --- Read-Your-Write

## 33. User Expectation

After a user updates an object, they may expect the next read to show
the update immediately.

Possible designs include:

``` text
invalidate before returning success
update cache after source commit
bypass cache temporarily
version-aware read
session-local knowledge
```

Each has tradeoffs.

------------------------------------------------------------------------

# Part 29 --- Multiple Cache Representations

## 34. Fan-Out Problem

One source record may appear in:

``` text
entity cache
search-result cache
summary cache
tenant aggregate
dashboard cache
```

A source update may require invalidating several key patterns.

Document dependency mapping.

------------------------------------------------------------------------

# Part 30 --- Avoid Wildcard Deletion

## 35. Production Safety

Do not solve dependency mapping with broad unsafe commands.

Avoid:

``` redis
KEYS pattern
```

on large production databases.

Prefer:

``` text
known derived keys
versioned namespaces
dependency indexes
controlled SCAN where justified
event-driven targeted invalidation
```

------------------------------------------------------------------------

# Part 31 --- Invalidation and Hot Keys

## 36. Hot-Key Risk

Invalidating a hot key immediately creates a miss window.

Combine invalidation with Chapter 15/16 controls:

``` text
single-flight
refresh-ahead
source protection
controlled warming
```

------------------------------------------------------------------------

# Part 32 --- Invalidation and Big Keys

## 37. Regeneration Cost

Invalidating a large expensive object may create:

``` text
large source query
large serialization
large Redis write
large network response
```

Chapter 18 big-key analysis should influence invalidation strategy.

------------------------------------------------------------------------

# Part 33 --- Observability

## 38. Invalidation Metrics

Track:

``` text
cache_invalidation_total
cache_invalidation_success_total
cache_invalidation_failure_total
cache_invalidation_latency_seconds
cache_invalidation_lag_seconds
```

------------------------------------------------------------------------

## 39. Event Metrics

Track:

``` text
events_received_total
events_duplicate_total
events_out_of_order_total
events_rejected_old_version_total
consumer_lag
consumer_errors
replay_count
```

------------------------------------------------------------------------

## 40. Consistency Metrics

Where feasible:

``` text
cache_version
source_version
stale_read_total
reconciliation_mismatch_total
```

Do not create unbounded high-cardinality metric labels.

------------------------------------------------------------------------

# Part 34 --- Hands-On Lab

## 41. Objectives

You will:

1.  create a simulated source;
2.  implement cache-aside reads;
3.  update source then invalidate;
4.  reproduce stale repopulation;
5.  add version-aware cache writes;
6.  process duplicate events;
7.  process out-of-order events;
8.  simulate lost invalidation;
9.  reconcile cache/source versions;
10. test delete tombstones;
11. inject failures;
12. clean up safely.

------------------------------------------------------------------------

## 42. Prerequisites

``` bash
python -m pip install redis
```

Windows CMD:

``` cmd
set REDIS_HOST=localhost
set REDIS_PORT=6379
set REDIS_PASSWORD=
```

PowerShell:

``` powershell
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
$env:REDIS_PASSWORD=""
```

Linux/macOS:

``` bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=''
```

------------------------------------------------------------------------

# Part 35 --- Version-Aware Lab

## 43. Create `chapter20_invalidation_lab.py`

``` python
import json
import os
import threading
import time

import redis

HOST = os.getenv("REDIS_HOST", "localhost")
PORT = int(os.getenv("REDIS_PORT", "6379"))
PASSWORD = os.getenv("REDIS_PASSWORD") or None

r = redis.Redis(
    host=HOST,
    port=PORT,
    password=PASSWORD,
    decode_responses=True,
)

KEY = "tutorial:chapter20:item:1001"
VERSION_KEY = "tutorial:chapter20:item:1001:version"

source_lock = threading.Lock()

source = {
    "id": 1001,
    "version": 1,
    "value": "version-1",
    "deleted": False,
}

VERSIONED_WRITE = """
local current = redis.call("GET", KEYS[1])

if current and tonumber(current) > tonumber(ARGV[1]) then
    return 0
end

redis.call("SET", KEYS[1], ARGV[1], "EX", ARGV[3])
redis.call("SET", KEYS[2], ARGV[2], "EX", ARGV[3])

return 1
"""


def source_read():
    with source_lock:
        return dict(source)


def source_update(value):
    with source_lock:
        source["version"] += 1
        source["value"] = value
        source["deleted"] = False
        return dict(source)


def source_delete():
    with source_lock:
        source["version"] += 1
        source["deleted"] = True
        source["value"] = None
        return dict(source)


def versioned_cache_write(record, ttl=120):
    payload = json.dumps(record)

    return r.eval(
        VERSIONED_WRITE,
        2,
        VERSION_KEY,
        KEY,
        record["version"],
        payload,
        ttl,
    )


def cache_read():
    raw = r.get(KEY)

    if raw is None:
        return None

    return json.loads(raw)


def invalidate():
    r.unlink(KEY, VERSION_KEY)


def read_through():
    cached = cache_read()

    if cached is not None:
        return cached, "hit"

    record = source_read()
    versioned_cache_write(record)

    return record, "miss"


if __name__ == "__main__":
    invalidate()

    print("Initial read:", read_through())

    updated = source_update("version-2")
    invalidate()

    print("Source updated:", updated)
    print("After invalidate:", read_through())
```

------------------------------------------------------------------------

## 44. Important Lua Note

The lab stores the version and payload in two keys.

In clustered/sharded Redis deployments, multi-key Lua operations require
compatible key placement.

For production, design key hash tags/data placement or use a data model
that preserves required atomicity within the deployed topology.

Do not copy a multi-key lab script into production without validating
cluster semantics.

------------------------------------------------------------------------

# Part 36 --- Run

## 45. Execute

``` bash
python chapter20_invalidation_lab.py
```

Expected pattern:

``` text
Initial read: (... version 1 ..., 'miss')
Source updated: ... version 2 ...
After invalidate: (... version 2 ..., 'miss')
```

------------------------------------------------------------------------

# Part 37 --- Reproduce Stale Repopulation

## 46. Unsafe Timeline

Conceptually:

``` python
old_record = source_read()       # version 2

new_record = source_update(
    "version-3"
)

invalidate()

# Delayed old loader tries to repopulate:
result = versioned_cache_write(
    old_record
)

print(result)
```

If version 3 has already been written to cache, the older version should
be rejected.

------------------------------------------------------------------------

# Part 38 --- Out-of-Order Event Lab

## 47. Process Version 5 Then Version 4

Create records:

``` python
event5 = {
    "id": 1001,
    "version": 5,
    "value": "v5",
    "deleted": False,
}

event4 = {
    "id": 1001,
    "version": 4,
    "value": "v4",
    "deleted": False,
}
```

Write version 5, then attempt version 4.

Expected:

``` text
version 4 must not replace version 5
```

------------------------------------------------------------------------

# Part 39 --- Duplicate Event Lab

## 48. Same Version Twice

Process version 5 twice.

Idempotent behavior should leave a valid version 5 state.

Whether equal versions are rewritten or skipped is an implementation
choice, but they must not corrupt state.

------------------------------------------------------------------------

# Part 40 --- Tombstone Lab

## 49. Delete

Source:

``` python
deleted = source_delete()
```

Cache a versioned tombstone.

Then attempt to write an older non-deleted record.

Expected:

``` text
older record rejected
```

This prevents resurrection of deleted state.

------------------------------------------------------------------------

# Part 41 --- Lost Event Lab

## 50. Simulate

``` text
source updates to version 10
invalidation event is "lost"
cache remains version 9
```

Now compare:

``` text
source version
cache version
```

A reconciliation process should detect the mismatch.

------------------------------------------------------------------------

# Part 42 --- Reconciliation Example

## 51. Simple Check

``` python
def reconcile():
    source_record = source_read()
    cached = cache_read()

    if cached is None:
        return "missing"

    if cached["version"] != source_record["version"]:
        return "mismatch"

    return "consistent"
```

Production reconciliation must be capacity-aware and avoid uncontrolled
full scans.

------------------------------------------------------------------------

# Part 43 --- Event Consumer Pseudocode

## 52. Version-Aware Consumer

``` python
def handle_event(event):
    current_version = get_cached_version(event.id)

    if current_version is not None:
        if current_version > event.version:
            return "old-event-rejected"

    apply_event_idempotently(event)

    return "applied"
```

The exact logic depends on whether events update the cache, invalidate
it, or write tombstones.

------------------------------------------------------------------------

# Part 44 --- Failure Injection

## 53. Failure 1 --- Source Commit Succeeds, Invalidation Fails

Expected:

``` text
source new
cache old
```

Recovery:

``` text
retry
event replay
TTL
reconciliation
```

------------------------------------------------------------------------

## 54. Failure 2 --- Invalidation Before Source Failure

Delete cache, then simulate source update failure.

Expected:

``` text
next read reloads old source value
```

Observe unnecessary cache churn and why ordering matters.

------------------------------------------------------------------------

## 55. Failure 3 --- Stale Loader Race

Pause a reader after source read.

Update source and invalidate.

Resume the reader.

Without version protection, old data can re-enter cache.

------------------------------------------------------------------------

## 56. Failure 4 --- Duplicate Event

Deliver the same event repeatedly.

Expected:

``` text
safe idempotent result
```

------------------------------------------------------------------------

## 57. Failure 5 --- Out-of-Order Events

Deliver:

``` text
v12
v11
```

Expected:

``` text
v11 cannot overwrite v12
```

------------------------------------------------------------------------

## 58. Failure 6 --- Lost Event

Drop one invalidation event.

Validate:

``` text
TTL safety net
reconciliation
replay
```

------------------------------------------------------------------------

## 59. Failure 7 --- Consumer Down

Stop the invalidation consumer while source updates continue.

Measure:

``` text
consumer lag
stale window
recovery rate
```

------------------------------------------------------------------------

## 60. Failure 8 --- Redis Unavailable

Source update succeeds while Redis invalidation is unavailable.

Do not roll back a committed source change merely because a disposable
cache is down unless business architecture explicitly requires such
coupling.

Record/retry invalidation through the approved mechanism.

------------------------------------------------------------------------

## 61. Failure 9 --- Hot-Key Invalidation

Invalidate a high-QPS key.

Observe source load.

Apply:

``` text
single-flight
refresh/warm controls
source concurrency limit
```

------------------------------------------------------------------------

## 62. Failure 10 --- Delete Resurrection

Delete source at version 20.

Allow delayed version 19 loader to attempt cache population.

A versioned tombstone should prevent resurrection.

------------------------------------------------------------------------

# Part 45 --- Troubleshooting

## 63. Cache Shows Old Data

Check:

``` text
source version
cache version
TTL
last invalidation
consumer lag
event version
refresh path
in-flight loaders
```

------------------------------------------------------------------------

## 64. Invalidation Succeeded but Stale Data Returned

Investigate stale repopulation:

``` text
reader started before update
source read old value
invalidation completed
reader populated old value afterward
```

Delete success alone does not rule this out.

------------------------------------------------------------------------

## 65. Staleness Appears Intermittent

Check:

``` text
multiple app instances
race conditions
event ordering
cache key variants
multiple derived caches
replicas/read paths
```

------------------------------------------------------------------------

## 66. Consumer Lag Increasing

Check:

``` text
event arrival rate
consumer throughput
Redis latency
source/event schema errors
retries
poison messages
downstream throttling
```

------------------------------------------------------------------------

## 67. Invalidations Missing

Check:

``` text
event creation
broker delivery
consumer subscription
offset/checkpoint
filter logic
key mapping
Redis command result
```

------------------------------------------------------------------------

## 68. Deletes Reappear

Strongly investigate:

``` text
in-flight old loaders
out-of-order events
missing tombstone/version guard
old retry queue
```

------------------------------------------------------------------------

## 69. Too Many Cache Deletes

Check whether one source update fans out to many derived cache keys.

Review cache granularity and dependency design.

------------------------------------------------------------------------

# Part 46 --- Production Runbooks

## 70. Runbook --- Stale Cache Incident

``` text
1. Identify affected entity/key pattern.
2. Confirm authoritative source value/version.
3. Read cached value/version safely.
4. Check TTL.
5. Check invalidation event.
6. Check consumer lag/errors.
7. Check stale-loader race.
8. Invalidate affected cache safely.
9. Protect source during regeneration.
10. Verify new version is cached.
11. Identify propagation failure.
12. Add preventive control.
```

------------------------------------------------------------------------

## 71. Runbook --- Invalidation Consumer Lag

``` text
1. Measure lag.
2. Measure event arrival rate.
3. Measure processing rate.
4. Check Redis latency/errors.
5. Check poison/retry events.
6. Scale consumers if partitioning/order semantics permit.
7. Protect Redis/source during catch-up.
8. Replay from safe checkpoint.
9. Validate cache versions.
10. Confirm lag returns to target.
```

------------------------------------------------------------------------

## 72. Runbook --- Lost Invalidation

``` text
1. Confirm source changed.
2. Confirm cache remains old.
3. Find expected event.
4. Determine where propagation stopped.
5. Invalidate/reconcile affected key.
6. Check adjacent events/entities.
7. Validate replay/checkpoint.
8. Confirm TTL safety net.
9. Repair delivery path.
10. Add alert/reconciliation if missing.
```

------------------------------------------------------------------------

## 73. Runbook --- Delete Resurrection

``` text
1. Confirm source record is deleted.
2. Inspect cached version/state.
3. Identify delayed writer/loader.
4. Stop unsafe repopulation path.
5. Apply current tombstone/version.
6. Reject older writes.
7. Clear stale derived representations.
8. Test concurrent delete/read race.
9. Add version guard.
10. Validate no resurrection.
```

------------------------------------------------------------------------

## 74. Runbook --- Hot-Key Invalidation

``` text
1. Measure key request rate.
2. Confirm invalidation requirement.
3. Confirm source capacity.
4. Enable/verify single-flight.
5. Invalidate/update safely.
6. Allow one controlled regeneration.
7. Monitor source latency.
8. Monitor cache misses.
9. Verify new version.
10. Confirm hit ratio recovers.
```

------------------------------------------------------------------------

# Part 47 --- Consistency Design Template

## 75. Fields

``` text
Service:
Source of truth:
Entity:
Cache key/pattern:
Cached representation:
Freshness requirement:
Read-your-write required?:
TTL:
Invalidation trigger:
Invalidation method:
Update vs. delete cache?:
Version field:
Version ordering:
Delete/tombstone strategy:
Event transport:
Replay supported?:
Duplicate handling:
Out-of-order handling:
Consumer lag target:
Reconciliation method:
Source protection:
Owner:
```

------------------------------------------------------------------------

# Part 48 --- Dependency Mapping

## 76. Derived Cache Inventory

``` text
Source entity:
  -> entity cache:
  -> summary cache:
  -> list/search cache:
  -> dashboard cache:
  -> tenant aggregate:
```

For each representation document:

``` text
key pattern
owner
TTL
invalidation trigger
rebuild cost
```

------------------------------------------------------------------------

# Production Acceptance Checklist

## 77. Consistency Engineering

-   [ ] Source of truth explicitly documented.
-   [ ] Cache is classified as derived or authoritative.
-   [ ] Freshness requirement documented.
-   [ ] Read-your-write requirement documented.
-   [ ] Update/invalidation ordering defined.
-   [ ] Stale-repopulation race tested.
-   [ ] Version-aware protection implemented where required.
-   [ ] Delete resurrection tested.
-   [ ] Tombstone strategy defined where required.
-   [ ] TTL safety net exists.
-   [ ] Event duplicates handled.
-   [ ] Out-of-order events handled.
-   [ ] Event lag monitored.
-   [ ] Lost-event recovery exists.
-   [ ] Consumer-down recovery tested.
-   [ ] Redis-unavailable invalidation path tested.
-   [ ] Reconciliation strategy documented.
-   [ ] Derived-cache dependency map exists.
-   [ ] Hot-key invalidation source protection tested.
-   [ ] Production runbooks validated.

------------------------------------------------------------------------

# Knowledge Validation

## 78. Questions

You should be able to answer:

1.  Why does caching create a consistency problem?
2.  What is the source of truth?
3.  What is cache-aside?
4.  Why is source-update-then-invalidate common?
5.  What is the stale-repopulation race?
6.  Why does successful deletion not prevent stale repopulation?
7.  What is a version-aware cache write?
8.  Why must compare-and-write be atomic?
9.  What are versioned key names?
10. What is namespace versioning?
11. What is a tombstone?
12. How does a tombstone prevent delete resurrection?
13. Why is TTL still useful with event-driven invalidation?
14. What fields belong in an invalidation event?
15. Why must event processing be idempotent?
16. What happens with out-of-order events?
17. What is invalidation lag?
18. How can lost events be recovered?
19. Why should Redis Pub/Sub not automatically be assumed to provide
    durable replay?
20. What is CDC-based invalidation?
21. What is the dual-write problem?
22. What is a transactional outbox?
23. What is reconciliation?
24. Why must a consistency requirement be stated precisely?
25. What is read-your-write?
26. Why are multiple derived cache representations difficult?
27. Why avoid wildcard production deletion?
28. Why is hot-key invalidation dangerous?
29. Why does big-key regeneration matter?
30. What must pass before cache consistency is production-ready?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 79. Lab Completion

-   [ ] Created simulated source.
-   [ ] Implemented cache-aside read.
-   [ ] Updated source and invalidated cache.
-   [ ] Reproduced stale-repopulation timeline.
-   [ ] Added version-aware cache write.
-   [ ] Reviewed clustered multi-key atomicity constraint.
-   [ ] Processed duplicate event.
-   [ ] Processed out-of-order event.
-   [ ] Created tombstone.
-   [ ] Prevented old-value resurrection.
-   [ ] Simulated lost event.
-   [ ] Built reconciliation check.
-   [ ] Reviewed version-aware event consumer.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed troubleshooting.
-   [ ] Reviewed five production runbooks.
-   [ ] Completed consistency design template.
-   [ ] Completed dependency map.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 80. Lab Cleanup

Discover:

``` bash
redis-cli --scan --pattern 'tutorial:chapter20:*'
```

Delete only confirmed training keys.

Examples:

``` redis
UNLINK tutorial:chapter20:item:1001
UNLINK tutorial:chapter20:item:1001:version
```

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

against a shared or production database.

------------------------------------------------------------------------

# 81. Key Takeaways

1.  Redis cache state is normally derived state, not the source of
    truth.
2.  Cache invalidation must begin with clear ownership.
3.  Source-update-then-invalidate is common but does not eliminate all
    races.
4.  In-flight readers can repopulate stale data after successful
    invalidation.
5.  Version-aware writes prevent older state from replacing newer state.
6.  Version comparisons must be atomic where concurrent writers race.
7.  Tombstones can prevent deleted data from being resurrected.
8.  TTL is an important safety net even with active invalidation.
9.  Event-driven invalidation introduces duplicates, ordering, lag, and
    delivery failure.
10. Consumers should be idempotent.
11. Older out-of-order events must not overwrite newer state.
12. Durable replay requirements must be matched to the event transport.
13. CDC can align cache propagation with committed source changes but
    still requires lag/error handling.
14. Dual writes create a failure gap between source commit and event
    publication.
15. Transactional outbox and CDC are common approaches to reducing that
    gap.
16. Reconciliation detects divergence that real-time propagation missed.
17. "Consistent" must be replaced with a measurable freshness/ordering
    contract.
18. Multiple derived cache representations require dependency mapping.
19. Hot-key invalidation requires source protection during regeneration.
20. Production readiness requires versioning, observability, recovery,
    race testing, and runbooks.

------------------------------------------------------------------------

# 82. References

Validate exact Redis command behavior and event-system guarantees
against the versions deployed.

Recommended official Redis documentation areas:

-   `GET`
-   `SET`
-   `DEL`
-   `UNLINK`
-   `EXPIRE`
-   `TTL`
-   `SCAN`
-   Lua scripting / server-side programmability
-   Redis Pub/Sub
-   Redis Streams where applicable
-   Redis caching patterns
-   Redis Cluster key placement/hash tags
-   Redis Enterprise monitoring

Cache invalidation, CDC, transactional outbox, versioning, tombstones,
and reconciliation are distributed-system/application architecture
patterns. Their implementation must be aligned with the authoritative
datastore, event platform, consistency requirement, topology, and
failure model.

------------------------------------------------------------------------

# Next Chapter

**Chapter 21 --- Redis Pipelining, Batching & Round-Trip Optimization**

Chapter 21 will cover:

-   network round trips
-   pipelining fundamentals
-   batching
-   throughput vs. latency
-   pipeline sizing
-   memory/backpressure
-   partial failures
-   cluster/shard considerations
-   transactional differences
-   client behavior
-   observability
-   failure injection
-   troubleshooting
-   production runbooks
-   acceptance validation
