# Chapter 12 --- Cache-Aside Pattern

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Foundation → Production Cache Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Cache hit/miss implementation, source fallback, TTL,
invalidation, concurrency, failure injection, observability, stampede
analysis, and production runbooks

------------------------------------------------------------------------

# 1. Objective

Cache-aside, also called lazy loading, is one of the most common Redis
caching patterns.

The application owns the caching workflow.

On a read:

``` text
Application
    |
    v
Check Redis
    |
    +---- hit ----> Return cached value
    |
    +---- miss ---> Read source of truth
                       |
                       v
                   Cache result
                       |
                       v
                    Return
```

On a source update, a common pattern is:

``` text
Update source of truth
        |
        v
Invalidate cached key
```

The next read repopulates Redis.

Redis' current cache-aside guidance describes this same core model:
check Redis first, fall back to the primary store on a miss, populate
Redis with a TTL, and invalidate cached data after the underlying record
changes.

By the end, you should be able to:

-   Explain cache-aside architecture.
-   Implement hit and miss paths.
-   Select cache keys and TTLs.
-   Populate Redis safely after source reads.
-   Invalidate cache entries after source writes.
-   Explain bounded staleness.
-   Handle missing source records.
-   Understand cache stampede behavior.
-   Implement single-flight/stampede protection concepts.
-   Handle Redis failure separately from source failure.
-   Use bounded retries.
-   Design observability for hit rate and fallback load.
-   Identify stale-cache race conditions.
-   Build production cache-aside runbooks.

------------------------------------------------------------------------

# 2. When Cache-Aside Fits

Cache-aside is a strong fit when:

``` text
workload is read-heavy
many reads repeat
source reads are expensive
only part of the dataset is hot
application can tolerate bounded staleness
application can own cache logic
```

Examples:

``` text
user profiles
product records
provider/reference information
configuration lookups
API response caching
database query results
```

------------------------------------------------------------------------

# 3. When It May Not Fit

Review alternatives when:

``` text
every read must see the latest committed source state
cache warm-up misses are unacceptable
the complete dataset must always be preloaded
application cannot own invalidation
write ordering is extremely complex
```

Cache-aside is not automatically the best pattern for every workload.

------------------------------------------------------------------------

# Part 1 --- Read Path

## 4. Cache Hit

A hit is the fast path:

``` text
1. Build cache key.
2. Read Redis.
3. Value exists.
4. Deserialize/validate.
5. Return value.
```

The source system is not queried.

------------------------------------------------------------------------

## 5. Example

Key:

``` text
cache:profile:1001
```

Command:

``` redis
GET cache:profile:1001
```

If Redis returns:

``` json
{"id":"1001","name":"Alice","status":"active"}
```

the application can return that cached object.

------------------------------------------------------------------------

# Part 2 --- Cache Miss

## 6. Miss Flow

``` text
1. Build key.
2. GET Redis.
3. Redis returns nil.
4. Query source.
5. Source returns record.
6. Serialize record.
7. SET Redis with TTL.
8. Return record.
```

Example:

``` redis
SET cache:profile:1001 '{"id":"1001","name":"Alice"}' EX 300
```

------------------------------------------------------------------------

## 7. Why TTL Is Required

Without expiration, cache-aside can become:

``` text
populate once
serve indefinitely
```

if invalidation fails.

TTL provides a bounded lifetime for cached state.

Explicit invalidation and TTL complement each other.

------------------------------------------------------------------------

# Part 3 --- Source of Truth

## 8. Redis Is Usually Not the Authoritative Store

In this pattern:

``` text
PostgreSQL / MongoDB / API / another authoritative service
```

is the source of truth.

Redis is:

``` text
performance optimization
```

This distinction drives failure handling.

If Redis loses one cache entry:

``` text
rebuild from source
```

If the source loses the authoritative record:

``` text
Redis is not automatically the recovery authority
```

------------------------------------------------------------------------

# Part 4 --- Key Design

## 9. Key Pattern

Recommended structure:

``` text
cache:<service>:<entity>:<id>:<version>
```

Example:

``` text
cache:patient360:profile:1001:v2
```

Benefits:

``` text
ownership
namespace isolation
entity clarity
schema versioning
safe scanning
```

------------------------------------------------------------------------

## 10. Versioning

Suppose v1 cached:

``` json
{"first_name":"Alice"}
```

and v2 expects:

``` json
{"name":{"first":"Alice"}}
```

A new key version:

``` text
cache:profile:1001:v2
```

can avoid interpreting old serialized data as the new schema.

------------------------------------------------------------------------

# Part 5 --- Basic Python Implementation

## 11. Dependencies

Conceptually:

``` bash
pip install redis
```

Use the client/version approved by your organization.

------------------------------------------------------------------------

## 12. Simple Cache-Aside

``` python
import json
import redis

r = redis.Redis(
    host="redis.example.internal",
    port=6379,
    decode_responses=True,
)

CACHE_TTL = 300

def cache_key(profile_id: str) -> str:
    return f"cache:profile:{profile_id}:v1"

def get_profile_from_source(profile_id: str):
    # Replace with real database/API lookup.
    return {
        "id": profile_id,
        "name": "Alice",
        "status": "active",
    }

def get_profile(profile_id: str):
    key = cache_key(profile_id)

    cached = r.get(key)
    if cached is not None:
        return json.loads(cached)

    profile = get_profile_from_source(profile_id)

    if profile is None:
        return None

    r.set(
        key,
        json.dumps(profile),
        ex=CACHE_TTL,
    )

    return profile
```

This demonstrates the core pattern.

Production code requires stronger error handling and observability.

------------------------------------------------------------------------

# Part 6 --- Hit/Miss Metrics

## 13. Instrument the Decision

The application should distinguish:

``` text
cache_hit
cache_miss
cache_error
source_success
source_error
cache_population_success
cache_population_error
```

Without these signals, troubleshooting becomes guesswork.

------------------------------------------------------------------------

## 14. Hit Ratio

Conceptually:

``` text
hit ratio =
cache hits / (cache hits + cache misses)
```

Example:

``` text
hits   = 900,000
misses = 100,000
```

Hit ratio:

``` text
90%
```

But hit ratio alone is not enough.

Also measure:

``` text
latency
source QPS
source errors
Redis errors
```

------------------------------------------------------------------------

# Part 7 --- Write / Update Path

## 15. Invalidate on Write

A robust cache-aside update flow is:

``` text
1. Update source of truth.
2. If source update succeeds, delete cached key.
3. Next read repopulates from source.
```

Example:

``` redis
UNLINK cache:profile:1001:v1
```

or:

``` redis
DEL cache:profile:1001:v1
```

Use the appropriate deletion semantics for your object size and
environment.

**Safety/expected result:** `cache:profile:1001:v1` is a **conceptual application key**, not a tutorial-owned key to delete in a shared database. Do not execute either command without confirming key ownership, the correct environment, and an authorized invalidation workflow. `DEL`/`UNLINK` return the number of keys removed (usually `1` when present or `0` when absent). Demonstrate deletion only on a synthetic, isolated lab key.

------------------------------------------------------------------------

## 16. Why Source First?

Dangerous ordering:

``` text
1. Delete cache.
2. Source update fails.
```

Now the cache was invalidated even though authoritative data did not
change.

That may be survivable, but it causes an unnecessary miss.

More dangerous races can occur under concurrency.

A common baseline is:

``` text
source write succeeds
then invalidate cache
```

------------------------------------------------------------------------

# Part 8 --- Why Not Blindly Rewrite the Cache?

## 17. Update Both Systems

Pattern:

``` text
1. Update database.
2. Update Redis with same object.
```

This appears efficient but introduces more synchronization logic.

Potential problems:

``` text
database update succeeds
cache update fails

concurrent writers reorder updates

serialization differs

cache TTL accidentally changes

partial updates create inconsistent object
```

For classic cache-aside, invalidation is often simpler.

------------------------------------------------------------------------

# Part 9 --- Staleness Window

## 18. TTL-Bounded Staleness

Suppose:

``` text
TTL = 5 minutes
```

If invalidation fails after a source update, stale data can remain until
expiration.

Therefore TTL provides a fallback bound.

This is why both are useful:

``` text
invalidation -> fast freshness
TTL          -> eventual expiration safety net
```

------------------------------------------------------------------------

# Part 10 --- Missing Records

## 19. Cache Miss for Nonexistent ID

Request:

``` text
profile:99999999
```

Redis misses.

Source returns:

``` text
not found
```

If nothing is cached, every request repeats the source query.

This can be expensive.

------------------------------------------------------------------------

## 20. Negative Caching

Store a sentinel:

``` text
cache:profile:99999999 -> NOT_FOUND
```

with a short TTL.

Example:

``` redis
SET cache:profile:99999999:missing 1 EX 30
```

This reduces repeated source queries.

But a newly created record can remain hidden until the negative entry
expires or is invalidated.

------------------------------------------------------------------------

# Part 11 --- Cache Stampede

## 21. Problem

Popular key:

``` text
cache:product:123
```

expires.

At that moment:

``` text
500 requests arrive
```

Each does:

``` text
Redis miss
-> source query
```

Now:

``` text
500 source queries
```

may run for one logical object.

This is a cache stampede / thundering-herd problem.

------------------------------------------------------------------------

## 22. Why It Matters

The source system can experience:

``` text
connection-pool exhaustion
CPU spike
query latency
timeouts
retry amplification
```

Caching can accidentally amplify load precisely when the cache stops
helping.

------------------------------------------------------------------------

# Part 12 --- Single-Flight Concept

## 23. Goal

For one missing key:

``` text
one caller loads source
other callers wait/retry cache briefly
```

Conceptually:

``` text
Request A -> miss -> acquires loader lock -> source
Request B -> miss -> lock unavailable -> wait
Request C -> miss -> lock unavailable -> wait
                         |
                         v
                  A populates Redis
                         |
             B/C read cached value
```

Redis' current cache-aside examples use a lock/single-flight technique
to reduce concurrent source loads for popular misses.

------------------------------------------------------------------------

# Part 13 --- Lock Acquisition

## 24. Basic Lock Pattern

Conceptually:

``` redis
SET cache:lock:profile:1001 <unique-token> NX PX 5000
```

If successful:

``` text
this caller becomes loader
```

If not:

``` text
another caller is loading
```

The lock must have an expiration so an abandoned lock does not persist
forever.

------------------------------------------------------------------------

## 25. Unique Token

Never release a lock simply with:

``` redis
DEL lock-key
```

without ownership validation.

A caller whose lock expired could accidentally delete a newer caller's
lock.

Use a unique token and atomic compare-and-delete logic, commonly
implemented with a Lua script.

Distributed locking is a deeper subject; this chapter uses the mechanism
only to explain cache single-flight behavior.

------------------------------------------------------------------------

# Part 14 --- Lock TTL

## 26. Loader Duration

If:

``` text
source p99 = 2 seconds
lock TTL = 500 ms
```

the lock can expire while the source query is still running.

Another caller can then acquire it and start another load.

Choose the lock lifetime using observed worst-case source behavior plus
a controlled safety margin.

------------------------------------------------------------------------

# Part 15 --- Waiting Callers

## 27. Do Not Spin Aggressively

Bad:

``` text
while missing:
    GET
    GET
    GET
    GET
```

This can create Redis load.

Use:

``` text
short bounded wait
backoff
jitter
maximum wait
fallback/error policy
```

------------------------------------------------------------------------

# Part 16 --- Redis Failure

## 28. Cache Is an Optimization

If Redis is temporarily unavailable, some applications can bypass cache
and read the source.

Conceptually:

``` text
Redis error
   |
   v
Can source safely absorb fallback?
   |
   +-- yes -> bounded source fallback
   |
   +-- no  -> degrade / fail according to policy
```

This decision must be capacity-aware.

------------------------------------------------------------------------

## 29. Dangerous Fail-Open

Suppose:

``` text
normal source traffic = 5,000 QPS
application traffic   = 100,000 QPS
cache hit ratio       = 95%
```

If Redis fails and every request immediately hits the source:

``` text
source demand may jump toward 100,000 QPS
```

A cache outage can become a database outage.

Fail-open must be engineered, not assumed.

------------------------------------------------------------------------

# Part 17 --- Source Failure

## 30. Cache Miss + Source Down

If:

``` text
Redis miss
source unavailable
```

the application cannot populate the missing value.

Possible policies:

``` text
return error
serve approved stale value from another mechanism
degrade functionality
retry within strict bounds
```

The correct behavior is workload-specific.

------------------------------------------------------------------------

# Part 18 --- Redis Write Failure After Source Read

## 31. Sequence

``` text
Redis miss
source read succeeds
Redis SET fails
```

Should the user request fail?

Often:

``` text
No.
```

The source read succeeded and Redis is only an optimization.

The application can return the source value while recording a cache
population failure.

But this increases future source load until cache writes recover.

------------------------------------------------------------------------

# Part 19 --- Redis Read Failure

## 32. Distinguish Miss from Error

These are different:

``` text
Redis returns nil -> cache miss
Redis timeout     -> cache error
```

Do not report both as:

``` text
cache miss
```

Otherwise a Redis outage can masquerade as poor hit rate.

------------------------------------------------------------------------

# Part 20 --- Source Read Race with Update

## 33. Stale Repopulation Race

Timeline:

``` text
T1 Request A cache miss
T2 A reads old source value V1
T3 Writer updates source to V2
T4 Writer invalidates cache
T5 A writes V1 into Redis
```

Result:

``` text
stale V1 reappears after invalidation
```

TTL eventually removes it, but the race is real.

------------------------------------------------------------------------

## 34. Mitigation Options

Depending on correctness requirements:

``` text
versioned records
source version/timestamp validation
event-driven invalidation
short TTL
write fencing/version checks
delayed second invalidation in selected designs
```

There is no universal solution.

Consistency requirements must drive the design.

------------------------------------------------------------------------

# Part 21 --- Cache Key Collision

## 35. Shared Redis

Bad:

``` text
profile:1001
```

used by multiple applications with different schemas.

Better:

``` text
cache:billing:profile:1001:v1
cache:patient360:profile:1001:v3
```

Namespaces prevent accidental cross-service collisions.

------------------------------------------------------------------------

# Part 22 --- Serialization

## 36. Treat Cache Data as a Schema

If caching JSON:

``` text
serializer
field names
types
version
compatibility
```

matter.

Do not assume:

``` text
it's only cache
```

means serialization can be unmanaged.

------------------------------------------------------------------------

## 37. Corrupt Cached Value

If deserialization fails:

``` text
record cache_decode_error
invalidate the corrupt entry when safe
read source
repopulate with valid representation
```

Avoid repeatedly failing on the same corrupt object.

------------------------------------------------------------------------

# Part 23 --- Production Python Pattern

## 38. Safer Baseline

``` python
import json
import logging
import random
import redis

log = logging.getLogger(__name__)

CACHE_TTL = 300
TTL_JITTER = 60

class SourceError(Exception):
    pass

def key_for(profile_id: str) -> str:
    return f"cache:profile:{profile_id}:v1"

def ttl_with_jitter() -> int:
    return CACHE_TTL + random.randint(0, TTL_JITTER)

def read_source(profile_id: str):
    # Replace with authoritative lookup.
    return {
        "id": profile_id,
        "name": "Alice",
        "status": "active",
    }

def get_profile(r: redis.Redis, profile_id: str):
    key = key_for(profile_id)

    try:
        cached = r.get(key)
    except redis.RedisError:
        log.exception("cache_read_error")
        cached = None

    if cached is not None:
        try:
            return json.loads(cached)
        except (TypeError, json.JSONDecodeError):
            log.exception("cache_decode_error")
            try:
                r.unlink(key)
            except redis.RedisError:
                log.exception("cache_cleanup_error")

    profile = read_source(profile_id)

    if profile is None:
        return None

    try:
        r.set(
            key,
            json.dumps(profile),
            ex=ttl_with_jitter(),
        )
    except redis.RedisError:
        log.exception("cache_population_error")

    return profile
```

This still needs production metrics, timeouts, connection pooling,
security, and workload-specific source protection.

------------------------------------------------------------------------

# Part 24 --- Invalidation Function

## 39. Source-First Update

Conceptual:

``` python
def update_profile(r, profile_id, changes):
    updated = update_source(profile_id, changes)

    if not updated:
        raise SourceError("Source update failed")

    try:
        r.unlink(key_for(profile_id))
    except redis.RedisError:
        log.exception("cache_invalidation_error")

    return updated
```

If invalidation fails:

``` text
source is authoritative
TTL bounds stale cache lifetime
alert/metric should capture invalidation failure
```

For low-staleness workloads, stronger remediation may be required.

------------------------------------------------------------------------

# Part 25 --- Timeouts

## 40. Cache Timeout

The cache exists to reduce latency.

If a cache read is allowed to wait:

``` text
10 seconds
```

while the source normally responds in:

``` text
100 ms
```

the timeout policy defeats the purpose.

Set timeouts using measured latency and service requirements.

------------------------------------------------------------------------

## 41. Source Timeout

Source fallback also needs strict timeouts.

Without them:

``` text
cache miss
-> source hangs
-> application threads/tasks accumulate
-> pool exhaustion
```

------------------------------------------------------------------------

# Part 26 --- Retries

## 42. Redis Retry

Retry only when:

``` text
failure is plausibly transient
operation is safe
retry budget remains
```

Use:

``` text
bounded attempts
backoff
jitter
```

Do not retry indefinitely.

------------------------------------------------------------------------

## 43. Source Retry

Source retries are even more dangerous during a cache outage because
many requests may already be falling through.

Coordinate:

``` text
retry limits
circuit breaking
source capacity
request deadline
```

------------------------------------------------------------------------

# Part 27 --- Observability

## 44. Application Metrics

Capture:

``` text
cache_hit_total
cache_miss_total
cache_error_total
cache_decode_error_total
cache_population_total
cache_population_error_total
cache_invalidation_total
cache_invalidation_error_total
source_read_total
source_read_error_total
singleflight_wait_total
```

------------------------------------------------------------------------

## 45. Latency Metrics

Separate:

``` text
cache_read_latency
source_read_latency
cache_write_latency
request_latency
```

Do not only measure end-to-end latency.

------------------------------------------------------------------------

## 46. Redis Metrics

Correlate application signals with:

``` text
operations/sec
CPU
memory
evictions
connections
latency
network
shard distribution
```

------------------------------------------------------------------------

## 47. Source Metrics

Correlate:

``` text
source QPS
source latency
connection pool
CPU
I/O
errors
timeouts
```

A caching incident spans both systems.

------------------------------------------------------------------------

# Hands-On Lab

## 48. Lab Architecture

Use:

``` text
Python application
Redis
simulated primary store
```

No external database is required.

------------------------------------------------------------------------

## 49. Simulated Source

``` python
import time

SOURCE = {
    "1001": {
        "id": "1001",
        "name": "Alice",
        "status": "active",
    }
}

source_reads = 0

def read_source(profile_id):
    global source_reads
    source_reads += 1
    time.sleep(0.2)
    return SOURCE.get(profile_id)
```

This intentionally simulates an expensive source.

------------------------------------------------------------------------

## 50. Lab Cache Function

``` python
import json

def get_profile(r, profile_id):
    key = f"tutorial:chapter12:profile:{profile_id}"

    cached = r.get(key)
    if cached is not None:
        return "HIT", json.loads(cached)

    value = read_source(profile_id)

    if value is None:
        return "MISS-NOT-FOUND", None

    r.set(key, json.dumps(value), ex=60)
    return "MISS", value
```

------------------------------------------------------------------------

## 51. Lab 1 --- First Read

Ensure key is absent:

``` redis
UNLINK tutorial:chapter12:profile:1001
```

Call:

``` python
print(get_profile(r, "1001"))
```

Expected:

``` text
MISS
source_reads increments
Redis populated
```

------------------------------------------------------------------------

## 52. Lab 2 --- Second Read

Call again:

``` python
print(get_profile(r, "1001"))
```

Expected:

``` text
HIT
source_reads does not increment
```

------------------------------------------------------------------------

## 53. Lab 3 --- Verify Redis

``` redis
GET tutorial:chapter12:profile:1001
TTL tutorial:chapter12:profile:1001
```

Expected:

``` text
serialized profile
positive TTL
```

------------------------------------------------------------------------

# Part 28 --- Update Lab

## 54. Update Source

``` python
SOURCE["1001"]["status"] = "inactive"
```

Redis still contains old value until invalidated or expired.

Verify:

``` redis
GET tutorial:chapter12:profile:1001
```

------------------------------------------------------------------------

## 55. Invalidate

``` redis
UNLINK tutorial:chapter12:profile:1001
```

Call:

``` python
print(get_profile(r, "1001"))
```

Expected:

``` text
MISS
new source value loaded
cache repopulated
```

------------------------------------------------------------------------

# Part 29 --- Missing Record Lab

## 56. Query Missing ID

``` python
print(get_profile(r, "9999"))
print(get_profile(r, "9999"))
```

Without negative caching:

``` text
source queried twice
```

This demonstrates repeated-miss load.

------------------------------------------------------------------------

## 57. Add Negative Cache

Conceptual:

``` python
NOT_FOUND = "__NOT_FOUND__"

def get_profile_with_negative_cache(r, profile_id):
    key = f"tutorial:chapter12:profile:{profile_id}"

    cached = r.get(key)

    if cached == NOT_FOUND:
        return None

    if cached is not None:
        return json.loads(cached)

    value = read_source(profile_id)

    if value is None:
        r.set(key, NOT_FOUND, ex=15)
        return None

    r.set(key, json.dumps(value), ex=60)
    return value
```

------------------------------------------------------------------------

# Part 30 --- Stampede Lab

## 58. Simulate Concurrent Misses

Remove key:

``` redis
UNLINK tutorial:chapter12:profile:1001
```

Run multiple workers at nearly the same time.

Conceptual Python:

``` python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=20) as pool:
    results = list(
        pool.map(
            lambda _: get_profile(r, "1001"),
            range(20),
        )
    )

print("source_reads =", source_reads)
```

Without protection, several workers can read the source concurrently.

------------------------------------------------------------------------

## 59. Analyze

Ask:

``` text
How many requests?
How many source reads?
What was source latency?
What if this were 10,000 requests?
```

This is the stampede problem.

------------------------------------------------------------------------

# Part 31 --- Single-Flight Lab Concept

## 60. Acquire Loader Lock

``` python
import uuid

lock_key = "tutorial:chapter12:lock:profile:1001"
token = str(uuid.uuid4())

acquired = r.set(
    lock_key,
    token,
    nx=True,
    px=5000,
)
```

If:

``` text
acquired = true
```

load source.

Otherwise:

``` text
wait briefly
recheck cache
```

------------------------------------------------------------------------

## 61. Safe Release Concept

Use atomic compare-and-delete logic.

Conceptual Lua:

``` lua
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
```

Do not delete a lock you no longer own.

------------------------------------------------------------------------

# Failure Injection

## 62. Failure 1 --- Redis Read Failure

Simulate Redis unavailable.

Expected application decision:

``` text
record cache_error
determine whether bounded source fallback is safe
```

Do not classify as ordinary cache miss.

------------------------------------------------------------------------

## 63. Failure 2 --- Source Failure on Miss

Scenario:

``` text
Redis miss
source throws timeout
```

Expected:

``` text
no valid value available
return/degrade according to application policy
```

Do not cache an arbitrary error as valid data.

------------------------------------------------------------------------

## 64. Failure 3 --- Cache Population Failure

Scenario:

``` text
source succeeds
Redis SET fails
```

For many cache-aside workloads:

``` text
return source result
record cache_population_error
```

Expect increased future source load.

------------------------------------------------------------------------

## 65. Failure 4 --- Invalidation Failure

Scenario:

``` text
source update succeeds
Redis delete fails
```

Risk:

``` text
stale value remains until TTL
```

Monitor and alert based on freshness criticality.

------------------------------------------------------------------------

## 66. Failure 5 --- Stampede

Scenario:

``` text
popular key expires
1,000 concurrent requests miss
```

Risk:

``` text
source overload
```

Mitigations:

``` text
single-flight
TTL jitter
refresh-ahead
source protection
```

------------------------------------------------------------------------

## 67. Failure 6 --- Stale Repopulation Race

Timeline:

``` text
miss
old source read begins
source updated
cache invalidated
old read writes stale value
```

Review consistency requirements and mitigation.

------------------------------------------------------------------------

## 68. Failure 7 --- Corrupt Cached JSON

Set:

``` redis
SET tutorial:chapter12:profile:1001 '{broken-json' EX 60
```

Application should:

``` text
detect decode failure
record metric
remove/ignore bad cache
read source
repopulate
```

------------------------------------------------------------------------

## 69. Failure 8 --- Retry Storm

Scenario:

``` text
Redis fails
all app instances retry Redis repeatedly
then retry source repeatedly
```

Result:

``` text
Redis recovery pressure
source overload
thread/pool exhaustion
```

Use bounded retry budgets.

------------------------------------------------------------------------

## 70. Failure 9 --- Cache Key Collision

Two services use:

``` text
profile:1001
```

with incompatible schemas.

Result:

``` text
cross-service corruption
decode errors
incorrect responses
```

Fix:

``` text
service-specific namespace
schema version
```

------------------------------------------------------------------------

## 71. Failure 10 --- TTL Too Long

Invalidation silently fails.

TTL:

``` text
24 hours
```

Business freshness:

``` text
5 minutes
```

Result:

``` text
unacceptable stale data
```

TTL must be a defensible fallback bound.

------------------------------------------------------------------------

# Troubleshooting

## 72. Hit Ratio Suddenly Drops

Check:

``` text
deployment changed key format?
TTL changed?
mass expiration?
evictions?
Redis restarted/recovered?
cache writes failing?
working set changed?
```

------------------------------------------------------------------------

## 73. Source QPS Suddenly Rises

Check:

``` text
cache hit ratio
Redis errors
expiration wave
evictions
cache population errors
new application instances
key-version rollout
```

------------------------------------------------------------------------

## 74. Stale Data Reported

Check:

``` text
source current value
cached value
TTL
last source update
invalidation logs
cache population race
schema/version
```

------------------------------------------------------------------------

## 75. Redis Healthy but Source Overloaded

Possible causes:

``` text
low hit ratio
TTL too short
stampede
negative misses
key mismatch
cache not populated
```

Redis health alone does not prove the caching layer is effective.

------------------------------------------------------------------------

## 76. High Redis Traffic but Low Hit Ratio

Check:

``` text
many one-time keys
poor cacheability
too-short TTL
key cardinality explosion
repeated misses
lock polling
```

Caching every request pattern may waste Redis capacity.

------------------------------------------------------------------------

# Production Runbooks

## 77. Runbook --- Cache Hit Ratio Drop

``` text
1. Record incident time.
2. Identify affected service/namespace.
3. Compare current and baseline hit ratio.
4. Check Redis errors.
5. Check evictions.
6. Check TTL changes.
7. Check recent deployment.
8. Check key format/version changes.
9. Check cache population errors.
10. Check source QPS/latency.
11. Check mass expiration.
12. Stabilize source load.
13. Correct cache behavior.
14. Validate hit ratio recovery.
```

------------------------------------------------------------------------

## 78. Runbook --- Cache Stampede

``` text
1. Identify hot key/namespace.
2. Measure concurrent misses.
3. Measure source QPS.
4. Check source latency/errors.
5. Check expiration timing.
6. Reduce retry amplification.
7. Apply source protection.
8. Use single-flight where appropriate.
9. Add/adjust TTL jitter.
10. Consider refresh-ahead.
11. Validate source recovery.
12. Load-test the corrected design.
```

------------------------------------------------------------------------

## 79. Runbook --- Stale Cache

``` text
1. Identify exact key.
2. Retrieve cached value.
3. Retrieve authoritative value.
4. Check TTL.
5. Check source update timestamp/version.
6. Check invalidation event/log.
7. Check cache population timing.
8. Check concurrent read/write race.
9. Invalidate affected cache safely.
10. Correct application ordering/design.
11. Add regression test.
12. Monitor recurrence.
```

------------------------------------------------------------------------

## 80. Runbook --- Redis Cache Outage

``` text
1. Confirm Redis failure scope.
2. Measure application fallback rate.
3. Measure source-system headroom.
4. Prevent unbounded source fallback.
5. Apply rate limiting/circuit breaking as designed.
6. Reduce retry amplification.
7. Restore Redis service.
8. Warm cache gradually if required.
9. Monitor source load during recovery.
10. Validate hit ratio recovery.
11. Review why cache failure affected source.
```

------------------------------------------------------------------------

## 81. Runbook --- Invalidation Failure

``` text
1. Confirm source update succeeded.
2. Identify affected cache key.
3. Check current cached value.
4. Check TTL remaining.
5. Retry invalidation only if safe and bounded.
6. Invalidate exact affected key.
7. Check broader invalidation failure rate.
8. Check Redis connectivity/errors.
9. Validate next read repopulates fresh data.
10. Review alerting and freshness exposure.
```

------------------------------------------------------------------------

# Part 32 --- Production Design Template

## 82. Cache-Aside Design

``` text
Service:
Entity:
Source of truth:
Cache namespace:
Serialization:
Schema version:
Positive TTL:
TTL jitter:
Negative caching:
Negative TTL:
Invalidation trigger:
Single-flight:
Lock TTL:
Redis timeout:
Source timeout:
Redis retry:
Source retry:
Fail-open policy:
Source fallback limit:
Hit-ratio target:
Freshness requirement:
Monitoring:
Owner:
Runbook:
```

------------------------------------------------------------------------

# Part 33 --- SLO Considerations

## 83. Cache SLO Is Not Just Redis Uptime

A caching layer can be:

``` text
Redis available
```

but still fail its purpose because:

``` text
hit ratio collapsed
data is stale
cache population is broken
source is overloaded
```

Service objectives should consider:

``` text
request latency
cache effectiveness
freshness
fallback health
```

------------------------------------------------------------------------

# Production Acceptance Checklist

## 84. Cache-Aside Readiness

-   [ ] Source of truth documented.
-   [ ] Cache namespace documented.
-   [ ] Key schema versioned where needed.
-   [ ] Serialization defined.
-   [ ] Positive TTL documented.
-   [ ] TTL jitter reviewed.
-   [ ] Freshness requirement documented.
-   [ ] Invalidation workflow documented.
-   [ ] Source-first write ordering reviewed.
-   [ ] Invalidation failure behavior defined.
-   [ ] Negative caching decision documented.
-   [ ] Negative TTL documented if used.
-   [ ] Stampede risk reviewed.
-   [ ] Single-flight strategy defined where needed.
-   [ ] Lock ownership/release safe if locking is used.
-   [ ] Redis timeout documented.
-   [ ] Source timeout documented.
-   [ ] Redis retry bounded.
-   [ ] Source retry bounded.
-   [ ] Fail-open behavior capacity-tested.
-   [ ] Redis errors distinguished from misses.
-   [ ] Decode errors handled.
-   [ ] Cache population errors handled.
-   [ ] Hit/miss metrics available.
-   [ ] Source fallback metrics available.
-   [ ] Cache latency available.
-   [ ] Source latency available.
-   [ ] Hit-ratio-drop runbook available.
-   [ ] Stampede runbook available.
-   [ ] Stale-cache runbook available.
-   [ ] Redis-outage runbook available.
-   [ ] Invalidation-failure runbook available.

------------------------------------------------------------------------

# Knowledge Validation

## 85. Questions

You should be able to answer:

1.  What is cache-aside?
2.  Who owns source fallback in cache-aside?
3.  What happens on a cache hit?
4.  What happens on a cache miss?
5.  Why should cached values usually have TTLs?
6.  Why is Redis not normally the source of truth in this pattern?
7.  Why should cache keys be namespaced?
8.  Why can schema versioning be useful?
9.  What is a cache hit ratio?
10. Why is hit ratio alone insufficient?
11. What is a common source-update/invalidation order?
12. Why is invalidation often simpler than rewriting the cache?
13. How does TTL bound stale data after invalidation failure?
14. What is negative caching?
15. Why should negative TTL often be short?
16. What is a cache stampede?
17. What is single-flight?
18. Why must a loader lock expire?
19. Why must lock release verify ownership?
20. Why can fail-open overload the source?
21. What is the difference between a Redis miss and Redis error?
22. What should happen if source read succeeds but cache population
    fails?
23. What is the stale-repopulation race?
24. Why do cache and source need separate latency metrics?
25. Why should cache outage recovery consider source-system capacity?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 86. Lab Completion

-   [ ] Implemented simulated source.
-   [ ] Implemented basic cache-aside function.
-   [ ] Demonstrated first-read miss.
-   [ ] Demonstrated second-read hit.
-   [ ] Verified cached value.
-   [ ] Verified TTL.
-   [ ] Updated source.
-   [ ] Demonstrated stale cached copy before invalidation.
-   [ ] Invalidated key.
-   [ ] Demonstrated fresh repopulation.
-   [ ] Demonstrated repeated missing-record source reads.
-   [ ] Implemented/reviewed negative caching.
-   [ ] Simulated concurrent misses.
-   [ ] Measured source-read amplification.
-   [ ] Reviewed single-flight lock acquisition.
-   [ ] Reviewed ownership-safe lock release.
-   [ ] Completed Redis-read-failure scenario.
-   [ ] Completed source-failure scenario.
-   [ ] Completed cache-population-failure scenario.
-   [ ] Completed invalidation-failure scenario.
-   [ ] Completed stampede scenario.
-   [ ] Reviewed stale-repopulation race.
-   [ ] Completed corrupt-cache scenario.
-   [ ] Reviewed retry storm.
-   [ ] Reviewed key collision.
-   [ ] Reviewed excessive TTL.
-   [ ] Reviewed all production runbooks.

------------------------------------------------------------------------

# 87. Lab Cleanup

Find chapter keys:

``` redis
SCAN 0 MATCH 'tutorial:chapter12:*' COUNT 100
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

# 88. Key Takeaways

1.  Cache-aside keeps Redis outside the authoritative data store and
    lets the application control caching.
2.  A cache hit avoids the source read.
3.  A cache miss reads the source and populates Redis.
4.  TTL provides a bounded stale-data safety net.
5.  Source updates commonly invalidate the cache rather than attempting
    dual-write synchronization.
6.  Redis misses and Redis failures are different operational events.
7.  Cache population failure does not always need to fail a successful
    source read.
8.  Fail-open behavior can overload the source and must be
    capacity-engineered.
9.  Negative caching protects sources from repeated nonexistent-key
    lookups.
10. Popular-key expiration can create a cache stampede.
11. Single-flight can reduce duplicate source reads during concurrent
    misses.
12. Lock ownership must be validated before release.
13. Read/write races can repopulate stale data even after invalidation.
14. Cache effectiveness requires application, Redis, and source
    observability together.
15. Cache-aside is simple conceptually but requires deliberate failure
    engineering in production.

------------------------------------------------------------------------

# 89. References

Current Redis documentation describes cache-aside as an
application-controlled pattern in which Redis is checked first, a cache
miss falls back to the primary store, the result is cached with a TTL,
and writes commonly invalidate the cache so a later read reloads
authoritative data.

Current Redis client examples also demonstrate stampede protection with
a single-flight style lock, short-lived negative caching as a production
consideration, namespace isolation, and TTL selection based on
acceptable staleness.

Validate client APIs, command behavior, and production implementation
details against the exact Redis and client-library versions deployed.

Recommended official documentation areas:

-   Redis cache-aside
-   redis-py cache-aside
-   `GET`
-   `SET`
-   `DEL`
-   `UNLINK`
-   `TTL`
-   Lua scripting
-   client connection and retry configuration

------------------------------------------------------------------------

# Next Chapter

**Chapter 13 --- Cache Updates, Invalidation & Consistency**

Chapter 13 will go deeper into:

-   invalidation strategies
-   delete vs update
-   write ordering
-   concurrent readers/writers
-   stale repopulation
-   delayed double delete
-   version-based protection
-   event-driven invalidation
-   CDC-driven invalidation
-   multi-instance applications
-   partial updates
-   failure windows
-   consistency models
-   failure injection
-   production invalidation runbooks
