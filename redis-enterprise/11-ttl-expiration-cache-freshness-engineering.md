# Chapter 11 --- TTL, Expiration & Cache Freshness Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Foundation → Production Cache Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** TTL semantics, expiration behavior, freshness design,
jitter, sliding expiration, TTL auditing, failure injection,
troubleshooting, and production acceptance

------------------------------------------------------------------------

# 1. Objective

TTL is not simply a Redis cleanup setting.

For a cache, TTL is part of the application's correctness model.

It controls:

``` text
how long cached data can remain valid
when Redis can reclaim cached objects
how often the source system is revisited
how much stale data the application may serve
whether many keys expire simultaneously
how much memory the cache consumes
```

A poor TTL design can create:

``` text
stale data
memory growth
cache misses
source-system overload
cache avalanche
unexpected persistent keys
incorrect session lifetime
unexpected key deletion
```

By the end, you should be able to:

-   Explain Redis expiration semantics.
-   Use `SET` with expiration atomically.
-   Use `EXPIRE`, `PEXPIRE`, `EXPIREAT`, and related TTL inspection
    commands.
-   Interpret `TTL` return values correctly.
-   Understand how normal `SET` replacement affects TTL.
-   Use `KEEPTTL` when appropriate.
-   Distinguish fixed TTL from sliding TTL.
-   Select TTLs from freshness requirements.
-   Apply TTL jitter.
-   Explain synchronized-expiration risk.
-   Audit cache namespaces for missing TTLs.
-   Connect TTL design to memory and source-system capacity.
-   Troubleshoot unexpected expiration.
-   Troubleshoot keys that never expire.
-   Build a production cache-freshness policy.

------------------------------------------------------------------------

# 2. Why TTL Is an Architecture Decision

Consider a patient/provider/reference-data cache.

If the source changes at:

``` text
10:00:00
```

but the cached copy has:

``` text
TTL = 24 hours
```

the application may continue serving the old value long after the source
changed.

The Redis command is working correctly.

The cache design is wrong for the required freshness.

TTL must therefore begin with:

``` text
business freshness requirement
```

not:

``` text
pick a convenient number
```

------------------------------------------------------------------------

# Part 1 --- Core Expiration Semantics

## 3. Atomic TTL at Creation

Preferred cache creation:

``` redis
SET tutorial:chapter11:profile:1001 '{"status":"active"}' EX 300
```

This performs:

``` text
write value
+
set expiration
```

in one command.

That is safer than:

``` redis
SET key value
EXPIRE key 300
```

because a failure between those commands can leave a persistent key.

------------------------------------------------------------------------

## 4. Seconds vs Milliseconds

Seconds:

``` redis
EXPIRE key 300
```

Milliseconds:

``` redis
PEXPIRE key 300000
```

With `SET`:

``` redis
SET key value EX 300
SET key value PX 300000
```

Choose the precision the application actually needs.

------------------------------------------------------------------------

## 5. Absolute Expiration

Redis also supports absolute expiration.

Conceptually:

``` redis
EXPIREAT key <unix-seconds>
PEXPIREAT key <unix-milliseconds>
```

And `SET` supports absolute expiration options such as:

``` text
EXAT
PXAT
```

This can be useful when many objects must expire at a known business
timestamp.

But synchronized absolute expiration can also create load spikes.

------------------------------------------------------------------------

# Part 2 --- TTL Inspection

## 6. `TTL`

``` redis
TTL key
```

Returns remaining lifetime in seconds.

Important results:

``` text
positive integer = remaining TTL
-1               = key exists but has no expiration
-2               = key does not exist
```

These distinctions are operationally important.

------------------------------------------------------------------------

## 7. `PTTL`

``` redis
PTTL key
```

Provides millisecond-level remaining lifetime.

Use it when seconds are too coarse for the application or test.

------------------------------------------------------------------------

## 8. Persistent Key

Example:

``` redis
SET tutorial:chapter11:persistent value
TTL tutorial:chapter11:persistent
```

Expected:

``` text
-1
```

For a namespace that requires TTL, this is a policy violation.

------------------------------------------------------------------------

## 9. Missing Key

``` redis
TTL tutorial:chapter11:not-there
```

Expected:

``` text
-2
```

Do not confuse:

``` text
-1 = exists, persistent
-2 = absent
```

------------------------------------------------------------------------

# Part 3 --- `SET` and TTL Replacement

## 10. TTL Can Be Lost on Replacement

Create:

``` redis
SET tutorial:chapter11:item value1 EX 300
TTL tutorial:chapter11:item
```

Then:

``` redis
SET tutorial:chapter11:item value2
TTL tutorial:chapter11:item
```

A successful normal `SET` replacement discards the previous TTL unless
an expiration option preserving or replacing it is used.

This is a common production bug.

------------------------------------------------------------------------

## 11. Preserve TTL

Where supported:

``` redis
SET tutorial:chapter11:item value3 KEEPTTL
```

Then:

``` redis
TTL tutorial:chapter11:item
```

The existing TTL is retained.

Use this only when preserving the old expiration is semantically
correct.

------------------------------------------------------------------------

## 12. Reset TTL

If every cache refresh should start a new five-minute freshness window:

``` redis
SET tutorial:chapter11:item value4 EX 300
```

This intentionally creates a new expiration deadline.

------------------------------------------------------------------------

# Part 4 --- Conditional Expiration

**Version gate:** The conditional `EXPIRE NX`, `XX`, `GT`, and `LT` options were introduced in Redis 7.0.0. Confirm the exact Redis engine/version and Redis Software/Enterprise compatibility before using these examples. In particular, Redis treats a persistent (non-expiring) key as having an infinite TTL when evaluating `GT`/`LT`: a `GT` request cannot extend that infinite deadline, while a suitable `LT` request can introduce a finite expiry. `EXPIRE` returns integer `1` when the expiration is applied, or `0` when it is not.

Reference: [Redis EXPIRE command/version history](https://redis.io/docs/latest/commands/expire/).

## 13. `EXPIRE NX`

Conceptually:

``` redis
EXPIRE key 300 NX
```

Set expiration only if the key currently has no expiry.

Useful when:

``` text
add a TTL only to persistent keys
```

without replacing an existing expiration policy.

------------------------------------------------------------------------

## 14. `EXPIRE XX`

Conceptually:

``` redis
EXPIRE key 300 XX
```

Apply only when an expiration already exists.

------------------------------------------------------------------------

## 15. `EXPIRE GT` and `LT`

Modern Redis supports conditional expiration modes that can compare the
proposed expiration with the current one.

Use cases can include policies such as:

``` text
only extend lifetime
only shorten lifetime
```

Validate exact semantics against the deployed Redis release before
embedding them in application logic.

------------------------------------------------------------------------

# Part 5 --- `PERSIST`

## 16. Remove Expiration

``` redis
PERSIST key
```

removes the expiration from an existing key.

This changes:

``` text
temporary
```

to:

``` text
persistent
```

Use carefully.

For cache namespaces where every key must expire, `PERSIST` should
usually be restricted by application design or ACL policy.

------------------------------------------------------------------------

# Part 6 --- Expiration Internals

## 17. Expiration Is Not Just a Background Timer per Key

Redis does not need one operating-system timer for every expiring key.

At a conceptual level, expiration is handled through mechanisms that
identify expired keys during access and through active expiration work.

The implementation has evolved across Redis releases.

The operational lesson is:

> Do not design capacity assuming millions of expirations have zero CPU
> cost.

------------------------------------------------------------------------

## 18. Passive / Access-Time Expiration Concept

When a key is accessed, Redis can recognize that its expiration time has
passed and treat it as expired.

Conceptually:

``` text
client requests key
       |
       v
expiration checked
       |
   +---+---+
   |       |
valid    expired
   |       |
return   remove/treat absent
```

------------------------------------------------------------------------

## 19. Active Expiration Concept

Redis also performs active work to discover and remove expired keys
rather than waiting for every expired key to be accessed.

This prevents large populations of expired-but-never-read keys from
remaining indefinitely.

Exact algorithms and tuning behavior are version-dependent.

------------------------------------------------------------------------

# Part 7 --- Cache Freshness

## 20. Freshness Requirement

Ask:

> How old may this cached value be before it becomes unacceptable?

Examples:

``` text
feature configuration: 30 seconds
provider directory: 15 minutes
reference code set: 6 hours
static metadata: 24 hours
```

These are examples only.

Your TTL must come from the application's actual freshness requirement.

------------------------------------------------------------------------

## 21. TTL Is Not the Same as Freshness Guarantee

Suppose:

``` text
TTL = 5 minutes
```

The source changes one second after the cache entry is created.

Without invalidation or refresh, the cache can remain stale for almost
five minutes.

Therefore:

``` text
TTL = maximum cache lifetime
```

does not automatically mean:

``` text
source-to-cache freshness is always exactly TTL
```

------------------------------------------------------------------------

# Part 8 --- TTL Selection Framework

## 22. Inputs

Choose TTL using:

``` text
data volatility
business stale-data tolerance
source-system capacity
cache hit-rate target
traffic volume
object size
invalidation capability
refresh capability
failure behavior
```

------------------------------------------------------------------------

## 23. Example Decision Matrix

  Data Class        Change Rate     Stale Tolerance   Example TTL Strategy
  ----------------- --------------- ----------------- -------------------------
  Dynamic status    High            Low               Short
  User preference   Medium          Medium            Moderate + invalidation
  Reference data    Low             High              Longer
  Negative lookup   Depends         Usually short     Short
  Session           Policy-driven   Strict            Session lifetime

Do not turn these categories into universal values.

------------------------------------------------------------------------

# Part 9 --- Fixed TTL

## 24. Definition

Fixed TTL:

``` text
expiration is set at creation/refresh
reads do not extend it
```

Example:

``` redis
SET cache:item:1001 value EX 300
```

Repeated reads do not reset the expiration.

------------------------------------------------------------------------

## 25. When Fixed TTL Fits

Useful when:

``` text
freshness must be bounded from the last source fetch
reads should not prolong stale data
```

This is common for cache-aside.

------------------------------------------------------------------------

# Part 10 --- Sliding TTL

## 26. Definition

Sliding expiration extends the key's lifetime based on activity.

Conceptually:

``` text
read key
if valid:
    refresh expiration
```

Example:

``` redis
GET session:abc
EXPIRE session:abc 1800
```

Application libraries may provide more integrated patterns.

------------------------------------------------------------------------

## 27. Sliding TTL Risk

A frequently accessed key may remain indefinitely.

For:

``` text
session inactivity timeout
```

this may be correct.

For:

``` text
cached source record
```

it may allow stale data to live forever.

Do not apply sliding TTL universally.

------------------------------------------------------------------------

# Part 11 --- Absolute Lifetime + Sliding Idle Timeout

## 28. Two-Dimensional Lifetime

Some workloads require both:

``` text
idle timeout
absolute maximum lifetime
```

Example session:

``` text
idle timeout = 30 minutes
absolute lifetime = 12 hours
```

A session should not survive beyond 12 hours even if continuously
active.

This often requires application metadata/design beyond a single simple
TTL.

------------------------------------------------------------------------

# Part 12 --- TTL Jitter

## 29. Synchronized Expiration Problem

Suppose one million cache entries are loaded at deployment time with:

``` text
TTL = exactly 3600 seconds
```

One hour later, many can expire around the same time.

Result:

``` text
cache misses surge
source database traffic surges
application latency increases
source may overload
```

This is often called a cache avalanche pattern.

------------------------------------------------------------------------

## 30. Add Jitter

Instead of:

``` text
TTL = 3600
```

use a controlled distribution such as:

``` text
base TTL = 3600
jitter = random 0..600
effective TTL = 3600..4200
```

or a symmetric policy if the freshness budget permits it.

The jitter range must respect the application's maximum stale-data
tolerance.

------------------------------------------------------------------------

## 31. Example Python

``` python
import random

base_ttl = 3600
jitter = random.randint(0, 600)
ttl = base_ttl + jitter
```

Then:

``` python
redis_client.set(key, value, ex=ttl)
```

Do not use jitter to exceed an absolute business freshness limit.

------------------------------------------------------------------------

# Part 13 --- Negative Caching TTL

## 32. Missing Data

Suppose the source returns:

``` text
customer not found
```

Caching that result can protect the source from repeated misses.

But a long negative TTL can hide a newly created record.

Therefore negative cache entries often require a deliberately shorter
TTL than positive entries.

Negative caching is covered more deeply later in Part 2.

------------------------------------------------------------------------

# Part 14 --- TTL and Memory

## 33. Missing TTL Causes Growth

Suppose a cache creates:

``` text
1 million new keys/day
```

and keys never expire.

Even if each key is small:

``` text
memory grows continuously
```

until:

``` text
eviction
OOM/write rejection depending on policy
capacity expansion
manual cleanup
```

TTL is part of memory lifecycle engineering.

------------------------------------------------------------------------

## 34. TTL Does Not Replace Capacity Planning

A cache can still exceed memory before keys expire.

Example:

``` text
100 GB/hour ingestion
TTL = 4 hours
```

Steady-state data can approach hundreds of GB plus overhead.

Estimate:

``` text
arrival rate
x average object size
x retention window
+ Redis overhead
+ replication overhead
+ safety headroom
```

------------------------------------------------------------------------

# Part 15 --- TTL Auditing

## 35. Why Audit

Application bugs can create persistent keys even when the design
requires expiration.

Examples:

``` text
missing EX option
SET replacement removed TTL
migration script omitted expiration
manual operator write
incorrect client-library behavior
```

------------------------------------------------------------------------

## 36. Safe Namespace Scan

Use:

``` redis
SCAN 0 MATCH 'cache:profile:*' COUNT 100
```

For each returned key:

``` redis
TTL <key>
```

Classify:

``` text
positive = expiring
-1 = policy violation if TTL required
-2 = key disappeared during scan
```

A changing keyspace means audit tools must tolerate keys
appearing/disappearing.

------------------------------------------------------------------------

# Part 16 --- Example TTL Auditor

## 37. Python Pattern

``` python
import redis

r = redis.Redis(
    host="redis.example.internal",
    port=6379,
    decode_responses=True,
)

cursor = 0
missing_ttl = []

while True:
    cursor, keys = r.scan(
        cursor=cursor,
        match="cache:profile:*",
        count=500,
    )

    for key in keys:
        ttl = r.ttl(key)
        if ttl == -1:
            missing_ttl.append(key)

    if cursor == 0:
        break

print("Persistent keys:", len(missing_ttl))
```

For production-scale auditing:

``` text
rate-limit
batch
monitor Redis load
avoid logging sensitive key names
use approved credentials
```

------------------------------------------------------------------------

# Part 17 --- TTL Distribution Audit

## 38. Do Not Check Only Missing TTL

Also analyze TTL distribution.

Example:

  TTL Range           Keys
  ------------ -----------
  Persistent            50
  0--5 min          10,000
  5--30 min        100,000
  30--60 min       500,000
  60--61 min     5,000,000

A huge concentration around one deadline can indicate avalanche risk.

------------------------------------------------------------------------

# Part 18 --- Expiration and Source Capacity

## 39. Cache Miss Cost

If an expired key causes:

``` text
database query
API request
Snowflake query
Elasticsearch request
expensive computation
```

expiration rate influences downstream capacity.

A Redis TTL policy is therefore also a source-protection policy.

------------------------------------------------------------------------

## 40. Model Expiration Load

Suppose:

``` text
6,000,000 keys
TTL = 1 hour
uniform refresh
```

Average theoretical expiration/refresh demand can be approximated as:

``` text
6,000,000 / 3600
≈ 1,667 keys/sec
```

Real traffic is rarely perfectly uniform.

Use this as a capacity-estimation starting point, not a guarantee.

------------------------------------------------------------------------

# Part 19 --- Refresh-Ahead

## 41. Concept

Instead of waiting for expiration:

``` text
key expires
request misses
request waits for source
```

a system may refresh popular keys before expiry.

Conceptually:

``` text
TTL remaining below threshold
        |
        v
background refresh
        |
        v
new value + new TTL
```

------------------------------------------------------------------------

## 42. Tradeoffs

Benefits:

``` text
fewer user-facing misses
smoother source load
```

Costs:

``` text
more refresh complexity
possible unnecessary source calls
coordination requirements
race conditions
```

Use only when justified.

------------------------------------------------------------------------

# Part 20 --- Stale-While-Revalidate Concept

## 43. Conceptual Pattern

Some application architectures allow:

``` text
serve slightly stale cached data
+
refresh asynchronously
```

This can reduce latency and source pressure.

But it requires explicit stale-data semantics.

Redis TTL alone does not implement the entire pattern.

------------------------------------------------------------------------

# Hands-On Lab

## 44. Lab Safety

Use:

``` text
tutorial:chapter11:
```

Do not use production customer keys.

------------------------------------------------------------------------

## 45. Lab 1 --- Basic TTL

``` redis
SET tutorial:chapter11:basic value EX 120
TTL tutorial:chapter11:basic
```

Expected:

``` text
positive value <= 120
```

------------------------------------------------------------------------

## 46. Lab 2 --- Millisecond TTL

``` redis
SET tutorial:chapter11:ms value PX 10000
PTTL tutorial:chapter11:ms
```

Expected:

``` text
positive value <= 10000
```

------------------------------------------------------------------------

## 47. Lab 3 --- Persistent Key

``` redis
SET tutorial:chapter11:persistent value
TTL tutorial:chapter11:persistent
```

Expected:

``` text
-1
```

------------------------------------------------------------------------

## 48. Lab 4 --- Missing Key

``` redis
TTL tutorial:chapter11:does-not-exist
```

Expected:

``` text
-2
```

------------------------------------------------------------------------

## 49. Lab 5 --- TTL Lost by `SET`

``` redis
SET tutorial:chapter11:replace value1 EX 300
TTL tutorial:chapter11:replace

SET tutorial:chapter11:replace value2
TTL tutorial:chapter11:replace
```

Expected final TTL:

``` text
-1
```

This is one of the most important lab observations.

------------------------------------------------------------------------

## 50. Lab 6 --- `KEEPTTL`

``` redis
SET tutorial:chapter11:keep value1 EX 300
TTL tutorial:chapter11:keep

SET tutorial:chapter11:keep value2 KEEPTTL
TTL tutorial:chapter11:keep
```

Expected:

``` text
TTL remains positive
```

------------------------------------------------------------------------

## 51. Lab 7 --- Reset Freshness Window

``` redis
SET tutorial:chapter11:refresh value1 EX 60
TTL tutorial:chapter11:refresh

SET tutorial:chapter11:refresh value2 EX 300
TTL tutorial:chapter11:refresh
```

Expected final TTL:

``` text
near 300
```

------------------------------------------------------------------------

## 52. Lab 8 --- `EXPIRE`

``` redis
SET tutorial:chapter11:expire value
EXPIRE tutorial:chapter11:expire 120
TTL tutorial:chapter11:expire
```

------------------------------------------------------------------------

## 53. Lab 9 --- `PERSIST`

``` redis
PERSIST tutorial:chapter11:expire
TTL tutorial:chapter11:expire
```

Expected:

``` text
-1
```

------------------------------------------------------------------------

## 54. Lab 10 --- Conditional Expiration

``` redis
EXPIRE tutorial:chapter11:expire 120 NX
TTL tutorial:chapter11:expire
```

Then test supported conditional variants in your deployed release.

------------------------------------------------------------------------

# Part 21 --- Jitter Lab

## 55. Generate TTLs

Python:

``` python
import random

for i in range(20):
    ttl = 300 + random.randint(0, 60)
    print(i, ttl)
```

Observe:

``` text
expiration times are distributed
```

rather than all being exactly:

``` text
300
```

------------------------------------------------------------------------

## 56. Create Jittered Keys

Example application logic:

``` python
import random
import redis

r = redis.Redis(host="localhost", port=6379)

for i in range(20):
    ttl = 300 + random.randint(0, 60)
    r.set(
        f"tutorial:chapter11:jitter:{i}",
        "value",
        ex=ttl,
    )
```

------------------------------------------------------------------------

## 57. Inspect TTL Spread

Use:

``` redis
SCAN 0 MATCH 'tutorial:chapter11:jitter:*' COUNT 100
```

Then inspect selected TTLs.

Expected:

``` text
not all keys have identical remaining TTL
```

------------------------------------------------------------------------

# Part 22 --- Sliding Expiration Lab

## 58. Create Session

``` redis
SET tutorial:chapter11:session:abc user1001 EX 60
```

Wait briefly:

``` redis
TTL tutorial:chapter11:session:abc
```

Then simulate activity:

``` redis
GET tutorial:chapter11:session:abc
EXPIRE tutorial:chapter11:session:abc 60
TTL tutorial:chapter11:session:abc
```

Observe that the idle lifetime was renewed.

------------------------------------------------------------------------

## 59. Design Question

Would you do the same for:

``` text
cache:patient:1001
```

If the cache must never be more than five minutes old from source
retrieval:

``` text
No.
```

Repeated reads should not indefinitely preserve stale source data.

------------------------------------------------------------------------

# Failure Injection

## 60. Failure 1 --- Missing TTL

Create:

``` redis
SET tutorial:chapter11:bug:no-ttl value
```

Symptom:

``` redis
TTL tutorial:chapter11:bug:no-ttl
```

returns:

``` text
-1
```

Production consequence:

``` text
unbounded cache retention
memory growth
```

------------------------------------------------------------------------

## 61. Failure 2 --- Update Removes TTL

Create:

``` redis
SET tutorial:chapter11:bug:update value1 EX 300
SET tutorial:chapter11:bug:update value2
TTL tutorial:chapter11:bug:update
```

Expected:

``` text
-1
```

Root cause:

``` text
update path omitted expiration semantics
```

------------------------------------------------------------------------

## 62. Failure 3 --- TTL Too Short

Scenario:

``` text
source call = 200 ms
traffic = 20,000 requests/sec
TTL = 1 second
```

Potential outcome:

``` text
low hit ratio
source overload
high application latency
```

Fix is not automatically:

``` text
make TTL huge
```

Balance freshness and source capacity.

------------------------------------------------------------------------

## 63. Failure 4 --- TTL Too Long

Scenario:

``` text
business requires data within 5 minutes
TTL = 24 hours
no invalidation
```

Potential outcome:

``` text
stale application behavior
```

This is a correctness issue.

------------------------------------------------------------------------

## 64. Failure 5 --- Synchronized Expiration

Scenario:

``` text
2 million keys loaded at 01:00
all TTL = 3600
```

At approximately 02:00:

``` text
mass expiration
miss surge
source surge
```

Mitigation candidates:

``` text
TTL jitter
refresh spreading
refresh-ahead
source protection
```

------------------------------------------------------------------------

## 65. Failure 6 --- Sliding TTL Applied to Source Cache

Scenario:

``` text
source cache TTL = 5 minutes
every read resets TTL to 5 minutes
hot key read continuously
```

Result:

``` text
key may never refresh
```

Potentially severe stale-data bug.

------------------------------------------------------------------------

## 66. Failure 7 --- Negative TTL Too Long

Scenario:

``` text
user not found
negative cache TTL = 24 hours
user created 5 minutes later
```

Application may continue returning:

``` text
not found
```

until negative cache expires or is invalidated.

------------------------------------------------------------------------

## 67. Failure 8 --- TTL Without Capacity Model

Scenario:

``` text
ingestion = 50 GB/hour
TTL = 12 hours
database memory = 200 GB
```

Even though keys expire, expected retained data volume can far exceed
available memory.

TTL does not eliminate capacity engineering.

------------------------------------------------------------------------

# Troubleshooting

## 68. Cache Memory Keeps Growing

Check:

``` text
new key creation rate
TTL policy
persistent-key count
TTL distribution
average value size
eviction policy
application update path
```

------------------------------------------------------------------------

## 69. Key Disappeared Unexpectedly

Check:

``` text
TTL
expiration timestamp
application delete/invalidation
eviction
database configuration
key naming collision
```

Do not assume every missing key expired.

------------------------------------------------------------------------

## 70. Key Never Expires

Check:

``` redis
TTL key
```

If:

``` text
-1
```

review:

``` text
creation path
update path
PERSIST usage
migration
manual operations
```

------------------------------------------------------------------------

## 71. TTL Suddenly Changed

Check:

``` text
SET with new expiration
EXPIRE/PEXPIRE
application refresh
sliding expiration
migration
manual command
```

Use application logs/audit data where available.

------------------------------------------------------------------------

## 72. Source System Spikes Periodically

Correlate:

``` text
Redis expiration pattern
cache miss rate
source QPS
deployment/cache warm-up time
```

Look for synchronized TTLs.

------------------------------------------------------------------------

## 73. High Miss Rate

Check:

``` text
TTL too short
cache invalidation frequency
key naming mismatch
cache write failures
eviction
working-set size
```

TTL is only one possible cause.

------------------------------------------------------------------------

# Production Runbooks

## 74. Runbook --- Missing TTL Investigation

``` text
1. Identify affected namespace.
2. Confirm namespace requires expiration.
3. Sample using SCAN.
4. Check TTL for sampled keys.
5. Count/classify persistent keys safely.
6. Identify creation path.
7. Identify update path.
8. Check recent deployment.
9. Check PERSIST/manual operations.
10. Fix application logic.
11. Determine safe remediation for existing keys.
12. Avoid mass expiration at one identical timestamp.
13. Monitor memory.
14. Re-audit namespace.
```

------------------------------------------------------------------------

## 75. Runbook --- Cache Avalanche Investigation

``` text
1. Record incident time.
2. Check cache miss rate.
3. Check Redis latency.
4. Check source-system QPS.
5. Check source latency/errors.
6. Inspect TTL distribution.
7. Identify synchronized expiration.
8. Reduce retry amplification.
9. Protect source system.
10. Restore cache gradually.
11. Introduce approved TTL jitter.
12. Review refresh strategy.
13. Validate post-change load distribution.
```

------------------------------------------------------------------------

## 76. Runbook --- Stale Cache Investigation

``` text
1. Identify key/namespace.
2. Identify source-of-truth value.
3. Compare cached value.
4. Check key TTL.
5. Determine cache creation time if available.
6. Review TTL requirement.
7. Review invalidation path.
8. Review sliding-expiration behavior.
9. Review update path.
10. Correct cache entry safely.
11. Fix application freshness design.
12. Add monitoring/test coverage.
```

------------------------------------------------------------------------

## 77. Runbook --- TTL Policy Change

``` text
1. Define business freshness requirement.
2. Capture current TTL.
3. Measure hit rate.
4. Measure source QPS.
5. Measure source capacity.
6. Estimate working-set memory.
7. Model new TTL.
8. Define jitter.
9. Test in non-production.
10. Roll out gradually.
11. Monitor cache hit rate.
12. Monitor Redis memory.
13. Monitor source QPS/latency.
14. Validate stale-data behavior.
15. Record final policy.
```

------------------------------------------------------------------------

# Part 23 --- TTL Policy Template

## 78. Per-Namespace Policy

``` text
Namespace:
Owner:
Purpose:
Source of truth:
Positive TTL:
Negative TTL:
Jitter:
Fixed/sliding:
Absolute max lifetime:
Invalidation:
Refresh-ahead:
Maximum stale tolerance:
Expected key count:
Average object size:
Expected memory:
Source capacity:
Monitoring:
Runbook:
```

------------------------------------------------------------------------

# Part 24 --- Monitoring Requirements

## 79. Observe

At minimum, correlate:

``` text
key count
memory usage
evictions
cache hit/miss behavior
source QPS
source latency
application latency
persistent-key audit
TTL distribution
```

A TTL metric without application/source context is incomplete.

------------------------------------------------------------------------

# Production Acceptance Checklist

## 80. Cache Freshness Readiness

-   [ ] Every cache namespace has an owner.
-   [ ] Source of truth documented.
-   [ ] Freshness requirement documented.
-   [ ] Positive TTL documented.
-   [ ] Negative TTL documented where applicable.
-   [ ] Fixed vs sliding behavior documented.
-   [ ] Absolute lifetime documented where required.
-   [ ] Jitter policy documented.
-   [ ] Invalidation strategy documented.
-   [ ] Refresh strategy documented.
-   [ ] Application creates TTL atomically where appropriate.
-   [ ] Update path does not accidentally remove TTL.
-   [ ] `KEEPTTL` usage reviewed.
-   [ ] `PERSIST` usage controlled.
-   [ ] Missing-TTL audit available.
-   [ ] TTL distribution audit available.
-   [ ] Working-set memory modeled.
-   [ ] Source-system load modeled.
-   [ ] Avalanche risk reviewed.
-   [ ] Stale-data risk reviewed.
-   [ ] Cache-miss monitoring available.
-   [ ] Source-QPS monitoring available.
-   [ ] Missing-TTL runbook available.
-   [ ] Avalanche runbook available.
-   [ ] Stale-cache runbook available.
-   [ ] TTL change runbook available.

------------------------------------------------------------------------

# Knowledge Validation

## 81. Questions

You should be able to answer:

1.  Why is TTL a correctness decision?
2.  Why is `SET key value EX n` safer than separate `SET` and `EXPIRE`
    for cache creation?
3.  What does a positive `TTL` result mean?
4.  What does `TTL = -1` mean?
5.  What does `TTL = -2` mean?
6.  What happens to an existing TTL after a normal successful `SET`
    replacement?
7.  What does `KEEPTTL` do?
8.  What does `PERSIST` do?
9.  What is the difference between fixed and sliding TTL?
10. Why can sliding TTL be dangerous for source-data caches?
11. What is an absolute lifetime?
12. What is TTL jitter?
13. Why can synchronized expiration overload a source?
14. Why must jitter respect stale-data tolerance?
15. What is negative caching?
16. Why might negative TTL be shorter?
17. Why does TTL not replace memory capacity planning?
18. Why should TTL distribution be audited?
19. Why must a TTL audit tolerate disappearing keys?
20. What is refresh-ahead?
21. What is stale-while-revalidate conceptually?
22. How can an update path accidentally create persistent keys?
23. Why should cache hit/miss and source QPS be correlated?
24. What is the first step when a cache key never expires?
25. Why should a TTL change be treated as a production capacity change?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 82. Lab Completion

-   [ ] Created a key with `EX`.
-   [ ] Created a key with `PX`.
-   [ ] Verified positive TTL.
-   [ ] Verified `TTL = -1`.
-   [ ] Verified `TTL = -2`.
-   [ ] Demonstrated TTL loss after normal `SET`.
-   [ ] Demonstrated `KEEPTTL`.
-   [ ] Reset a freshness window.
-   [ ] Used `EXPIRE`.
-   [ ] Used `PERSIST`.
-   [ ] Reviewed conditional expiration.
-   [ ] Generated jittered TTL values.
-   [ ] Created jittered keys.
-   [ ] Inspected TTL spread.
-   [ ] Demonstrated sliding expiration.
-   [ ] Completed missing-TTL failure injection.
-   [ ] Completed update-removes-TTL failure injection.
-   [ ] Reviewed short-TTL failure.
-   [ ] Reviewed long-TTL failure.
-   [ ] Reviewed synchronized-expiration failure.
-   [ ] Reviewed sliding-TTL stale-cache failure.
-   [ ] Reviewed negative-cache failure.
-   [ ] Reviewed capacity-model failure.
-   [ ] Reviewed all TTL runbooks.

------------------------------------------------------------------------

# 83. Lab Cleanup

Find only chapter keys:

``` redis
SCAN 0 MATCH 'tutorial:chapter11:*' COUNT 100
```

Delete exact lab keys:

``` redis
UNLINK <exact-key>
```

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

------------------------------------------------------------------------

# 84. Key Takeaways

1.  TTL is part of cache correctness, not merely cleanup.
2.  Cache freshness requirements should drive TTL selection.
3.  Atomic value-plus-expiration creation avoids persistent-key race
    conditions.
4.  `TTL = -1` means an existing key has no expiry; `-2` means the key
    is absent.
5.  Normal `SET` replacement can remove an existing TTL.
6.  `KEEPTTL` preserves expiration when that is the intended semantic.
7.  Fixed and sliding expiration solve different problems.
8.  Sliding expiration can indefinitely preserve stale source data.
9.  TTL jitter can reduce synchronized expiration and source-load
    spikes.
10. Missing TTLs can create uncontrolled memory growth.
11. A TTL does not guarantee that the database has enough memory for the
    retention window.
12. TTL distribution matters, not just average TTL.
13. Cache expiration behavior must be correlated with source-system
    capacity.
14. Negative cache entries need their own freshness policy.
15. TTL changes should be tested and monitored like production capacity
    changes.

------------------------------------------------------------------------

# 85. References

The current Redis command documentation confirms that `SET` supports
`EX`, `PX`, `EXAT`, `PXAT`, and `KEEPTTL`, and that a normal successful
`SET` replacement discards an existing TTL unless expiration behavior is
explicitly supplied. `TTL` returns remaining lifetime and distinguishes
persistent keys from absent keys. Modern `EXPIRE` also supports
conditional modes such as `NX`, `XX`, `GT`, and `LT`.

Validate exact command availability and expiration behavior against the
Redis / Redis Enterprise version deployed in your environment.

Recommended official documentation areas:

-   `SET`
-   `EXPIRE`
-   `TTL`
-   `PTTL`
-   `PERSIST`
-   key expiration
-   Redis keyspace
-   Redis Software command compatibility

------------------------------------------------------------------------

# Next Chapter

**Chapter 12 --- Cache-Aside Pattern**

Chapter 12 will cover:

-   cache-aside architecture
-   read path
-   miss path
-   source fallback
-   cache population
-   write/update path
-   race conditions
-   stale-cache behavior
-   TTL integration
-   source protection
-   retry behavior
-   Python implementation
-   failure injection
-   cache hit/miss observability
-   production cache-aside runbooks
