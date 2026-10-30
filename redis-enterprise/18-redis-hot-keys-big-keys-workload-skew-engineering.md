# Chapter 18 --- Redis Hot Keys, Big Keys & Workload Skew Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Intermediate → Production Redis Workload Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Hot-key generation, big-key generation, access-skew
analysis, memory sizing, command-cost analysis, shard-concentration
reasoning, safe detection, mitigation experiments, failure injection,
observability, troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Two Redis problems are frequently confused:

``` text
hot key
```

and:

``` text
big key
```

They are not the same.

A hot key receives disproportionate traffic.

A big key consumes disproportionate memory or contains a large
collection/value.

A key can be:

``` text
hot but small
big but cold
hot and big
neither
```

The most dangerous case is often:

``` text
hot + big + expensive command
```

because traffic, CPU, memory, network, and latency can concentrate on
the same workload.

By the end, you should be able to:

-   Define hot keys and big keys precisely.
-   Distinguish traffic skew from size skew.
-   Explain why one key can dominate a Redis workload.
-   Understand shard-level concentration.
-   Identify network amplification.
-   Identify expensive operations on large collections.
-   Use safe key-size inspection techniques.
-   Use Redis diagnostic tooling carefully.
-   Build application-level hot-key telemetry.
-   Recognize hot-key cache stampedes.
-   Redesign problematic keys.
-   Split or aggregate data only when semantics permit.
-   Protect source systems when hot keys disappear.
-   Build observability and alerting.
-   Troubleshoot hot/big-key incidents.
-   Validate workload distribution before production.

------------------------------------------------------------------------

# 2. Core Production Principle

Average Redis metrics can hide severe workload concentration.

A cluster may appear healthy at the database level while:

``` text
one key
one shard
one operation
one client
```

receives a disproportionate share of work.

Always ask:

> Is the workload evenly distributed, or is a small portion of the
> keyspace dominating CPU, memory, network, or source regeneration?

------------------------------------------------------------------------

# Part 1 --- Hot Key Fundamentals

## 3. Definition

A hot key is a key that receives disproportionately high request volume
compared with the rest of the workload.

Example:

``` text
total Redis operations = 100,000/sec

key A = 40,000/sec
remaining 1,000,000 keys = 60,000/sec
```

Key A is operationally hot.

------------------------------------------------------------------------

## 4. Hot Does Not Mean Large

This can be hot:

``` redis
GET config:global
```

even if the value is only:

``` text
500 bytes
```

The problem is request concentration.

------------------------------------------------------------------------

# Part 2 --- Big Key Fundamentals

## 5. Definition

A big key is a key whose value or collection is unusually large relative
to normal workload expectations.

Examples:

``` text
large string
very large hash
very large list
very large set
very large sorted set
large stream
```

------------------------------------------------------------------------

## 6. Big Does Not Mean Hot

A 50 MB object requested once per day may be big but cold.

Its risks differ from a 1 KB key requested 50,000 times/sec.

------------------------------------------------------------------------

# Part 3 --- Four Workload Classes

## 7. Classification

``` text
                 SMALL              BIG
             +----------------+----------------+
COLD         | normal         | big/cold       |
             +----------------+----------------+
HOT          | hot/small      | hot/big        |
             +----------------+----------------+
```

Each quadrant requires different mitigation.

------------------------------------------------------------------------

# Part 4 --- Why Hot Keys Matter

## 8. Resource Concentration

A hot key can concentrate:

``` text
Redis command processing
network bandwidth
client connections
shard traffic
serialization/deserialization
application synchronization
source regeneration
```

------------------------------------------------------------------------

## 9. Sharded Systems

In a sharded Redis deployment, a key maps to one shard at a time.

A single extremely hot key therefore cannot automatically spread its
operations across all shards merely because more shards exist.

This is why:

``` text
cluster-wide average CPU
```

can look acceptable while one shard is overloaded.

------------------------------------------------------------------------

# Part 5 --- Why Big Keys Matter

## 10. Memory Concentration

One big value can consume the memory of thousands of ordinary cache
entries.

Big keys can contribute to:

``` text
memory pressure
evictions
network bursts
longer transfers
higher serialization cost
slow delete behavior
replication/recovery cost
```

------------------------------------------------------------------------

## 11. Collection Command Cost

For large collection data types, command complexity and result size
matter.

A large hash or sorted set is not automatically harmful if commands
access bounded subsets efficiently.

Danger appears when applications request or mutate excessive portions at
once.

------------------------------------------------------------------------

# Part 6 --- Hot + Big

## 12. Dangerous Combination

Suppose:

``` text
value size = 5 MB
request rate = 2,000 GET/sec
```

Approximate payload throughput alone is:

``` text
5 MB × 2,000/sec = 10,000 MB/sec
```

before considering protocol, network, replication, client processing,
and other overhead.

This architecture should be reviewed.

------------------------------------------------------------------------

# Part 7 --- Workload Skew

## 13. Uniform vs. Skewed

Uniform:

``` text
many keys receive similar traffic
```

Skewed:

``` text
small number of keys receive most traffic
```

Real application traffic is frequently skewed.

Capacity planning based only on:

``` text
total operations/sec / number of shards
```

can therefore be misleading.

------------------------------------------------------------------------

# Part 8 --- Zipf-Like Access

## 14. Popularity Distribution

Many systems exhibit a long-tail popularity pattern:

``` text
few objects = very popular
many objects = rarely used
```

This is normal.

The engineering task is to identify when the head of the distribution
becomes operationally unsafe.

------------------------------------------------------------------------

# Part 9 --- Hot-Key Causes

## 15. Common Causes

``` text
global configuration key
shared feature flag
homepage payload
popular product/entity
tenant metadata
leaderboard
rate-limit counter
shared lock
central queue
single session/state object
poor key design
```

------------------------------------------------------------------------

# Part 10 --- Accidental Hot Keys

## 16. Design Errors

Examples:

``` text
all users share one cache key
tenant ID omitted
date partition omitted
single global counter
all work pushed to one list
one lock protects unrelated entities
```

Always verify key cardinality against intended business dimensions.

------------------------------------------------------------------------

# Part 11 --- Big-Key Causes

## 17. Common Causes

``` text
unbounded list
unbounded stream
ever-growing set
large JSON document
whole result set cached as one string
large hash
large sorted-set leaderboard
missing retention
missing pagination
aggregation into one object
```

------------------------------------------------------------------------

# Part 12 --- Unbounded Collections

## 18. Growth Risk

A collection that only receives additions can become a big key over
time.

Example:

``` redis
LPUSH events <event>
```

without retention.

Or:

``` redis
XADD stream * ...
```

without an appropriate retention strategy.

Growth must be bounded by design.

------------------------------------------------------------------------

# Part 13 --- Safe Size Inspection

## 19. `MEMORY USAGE`

For a known key:

``` redis
MEMORY USAGE tutorial:chapter18:sample
```

This estimates memory associated with the key.

Interpret the result according to Redis version and data type.

------------------------------------------------------------------------

## 20. Data-Type Cardinality

Depending on type:

``` redis
STRLEN key
HLEN key
LLEN key
SCARD key
ZCARD key
XLEN key
```

These reveal logical size/cardinality, not necessarily complete memory
cost.

------------------------------------------------------------------------

# Part 14 --- Avoid Dangerous Discovery

## 21. `KEYS *`

Do not use:

``` redis
KEYS *
```

as a production discovery technique on a large keyspace.

Prefer controlled methods in an approved lab namespace or authorized diagnostic tooling:

``` redis
SCAN 0 MATCH 'tutorial:chapter18:*' COUNT 100
```

**Expected:** A cursor plus zero or more matching keys; continue with the returned cursor until `0`. `COUNT` is a hint. Duplicates and empty intermediate pages are possible, and a scan is not a consistent snapshot. This is an illustrative step, not authorization to enumerate a shared production database.

------------------------------------------------------------------------

# Part 15 --- Redis CLI Big-Key Analysis

## 22. Diagnostic Tooling

`redis-cli` provides diagnostic modes that can help identify large keys.

Exact options and behavior depend on the Redis CLI version.

Before running against production:

``` text
understand scan behavior
understand command cost
use approved credentials/TLS
run during an appropriate window
monitor impact
```

Do not treat diagnostic tooling as zero-cost.

------------------------------------------------------------------------

# Part 16 --- Hot-Key Detection

## 23. Application Telemetry

The most reliable hot-key visibility often comes from the
application/client layer.

Capture a safe representation such as:

``` text
key pattern
hashed key identity
operation
request count
latency
payload size
```

Avoid exposing sensitive key contents.

------------------------------------------------------------------------

## 24. Pattern-Level Metrics

Instead of logging every raw key:

``` text
patient:12345
patient:67890
```

record:

``` text
patient:{id}
```

plus safe cardinality/hotness metrics.

This improves observability without leaking identifiers.

------------------------------------------------------------------------

# Part 17 --- Redis Hot-Key Diagnostics

## 25. Server-Side Tools

Some Redis tooling can estimate hot keys under appropriate
policies/configuration.

Availability and usefulness depend on version and eviction
configuration.

Validate the exact tool before production use.

Application-level telemetry remains important because it reflects actual
business requests.

------------------------------------------------------------------------

# Part 18 --- Shard Concentration

## 26. One Key, One Placement

A single key's operations are handled by its owning shard.

If that key dominates traffic:

``` text
shard A = high CPU/network
shard B = normal
shard C = normal
```

Database averages can hide the hotspot.

------------------------------------------------------------------------

## 27. More Shards May Not Fix One Hot Key

Adding shards improves capacity for distributed workloads.

It does not automatically divide one key's traffic.

Mitigation may require changing application/key architecture.

------------------------------------------------------------------------

# Part 19 --- Network Amplification

## 28. Large Reads

Approximate payload bandwidth:

``` text
value size × reads/sec
```

Example:

``` text
2 MB × 500/sec
= ~1,000 MB/sec payload
```

This simplified calculation is enough to show why large frequently-read
values deserve review.

------------------------------------------------------------------------

# Part 20 --- Client Impact

## 29. Redis Is Only Part of the Path

Large values also affect:

``` text
client network
client memory
deserialization
garbage collection
application CPU
response latency
```

A Redis server can appear acceptable while clients struggle.

------------------------------------------------------------------------

# Part 21 --- Big Deletes

## 30. Prefer Non-Blocking Deletion Where Appropriate

For large disposable cache keys, `UNLINK` can move memory reclamation
work away from the synchronous command path.

Example:

``` redis
UNLINK tutorial:chapter18:big:1
```

Validate behavior against the deployed version.

Do not blindly delete application keys during an incident without
understanding regeneration impact.

------------------------------------------------------------------------

# Part 22 --- Big-Key Redesign

## 31. Split Only When Semantics Permit

A large object might be decomposed by:

``` text
entity
time range
page
tenant
logical component
```

But splitting increases:

``` text
key count
multi-key coordination
application complexity
consistency complexity
```

Do not split purely to make metrics look smaller.

------------------------------------------------------------------------

# Part 23 --- Avoid Over-Aggregation

## 32. One Giant Cached Response

Instead of:

``` text
tenant:1001:all-data
```

consider whether the application naturally accesses smaller independent
components.

Cache the unit that matches access semantics.

------------------------------------------------------------------------

# Part 24 --- Hot-Key Replication at Application Layer

## 33. Advanced Pattern

For immutable or safely replicated cache data, some architectures
intentionally create multiple logical copies:

``` text
hot:item:1001:0
hot:item:1001:1
hot:item:1001:2
```

and distribute reads.

This is an application architecture technique, not a universal Redis
fix.

It complicates:

``` text
invalidation
consistency
warming
memory
observability
```

Use only when the data semantics support it.

------------------------------------------------------------------------

# Part 25 --- Local Cache

## 34. Two-Level Caching

For extremely hot, slowly changing data:

``` text
application local cache
        |
        v
Redis
        |
        v
source
```

can reduce Redis traffic.

But local caches introduce:

``` text
per-instance staleness
invalidation complexity
memory duplication
deployment behavior
```

------------------------------------------------------------------------

# Part 26 --- Hot-Key Expiration

## 35. Stampede Risk

If a hot key expires:

``` text
thousands of callers
 -> Redis MISS
 -> source
```

Use Chapter 15 controls:

``` text
single-flight
refresh-ahead
stale-while-revalidate
TTL jitter where relevant
source concurrency limits
```

------------------------------------------------------------------------

# Part 27 --- Hot-Key Eviction

## 36. Same Regeneration Problem

A hot key may disappear because of memory pressure rather than TTL.

The source does not care why Redis missed.

Stampede protection must work for both expiration and eviction.

------------------------------------------------------------------------

# Part 28 --- Hot-Key Warming

## 37. Priority

Chapter 16 introduced warming tiers.

Known hot keys normally belong near the highest warming priority because
their absence produces disproportionate source load.

------------------------------------------------------------------------

# Part 29 --- Observability

## 38. Key/Pattern Metrics

Useful application metrics:

``` text
requests_by_key_pattern
requests_by_operation
top_key_share
top_10_key_share
payload_bytes
cache_miss_by_pattern
regeneration_count
```

------------------------------------------------------------------------

## 39. Shard Metrics

Monitor:

``` text
CPU by shard/node
operations/sec by shard
network by shard
latency by shard
memory by shard
connections
```

Exact Redis Enterprise metrics depend on version and topology.

------------------------------------------------------------------------

## 40. Big-Key Metrics

Useful signals:

``` text
value size distribution
collection cardinality
largest sampled keys
growth rate
large-response latency
large-delete activity
```

------------------------------------------------------------------------

# Part 30 --- Skew Metrics

## 41. Top-Key Share

Conceptually:

``` text
top key share =
requests to hottest key / total cache requests
```

Example:

``` text
hottest key = 25,000/sec
total = 100,000/sec

top key share = 25%
```

That deserves architectural review.

------------------------------------------------------------------------

## 42. Top-N Share

Also measure:

``` text
top 10 keys / total traffic
top 100 keys / total traffic
```

This distinguishes:

``` text
one extreme key
```

from:

``` text
a broader hot working set
```

------------------------------------------------------------------------

# Part 31 --- Hands-On Lab

## 43. Objectives

You will:

1.  create hot and cold keys;
2.  generate skewed access;
3.  create small and large values;
4.  measure memory usage;
5.  measure string length;
6.  create a large collection;
7.  inspect cardinality;
8.  estimate network amplification;
9.  simulate hot-key expiration;
10. apply single-flight reasoning;
11. clean up safely.

------------------------------------------------------------------------

## 44. Prerequisites

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

# Part 32 --- Generate Workload

## 45. Create `chapter18_hot_big_lab.py`

``` python
import os
import random
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

PREFIX = "tutorial:chapter18:"
HOT_KEY = PREFIX + "hot:global-config"
COLD_PREFIX = PREFIX + "cold:"
BIG_KEY = PREFIX + "big:payload"
LIST_KEY = PREFIX + "big:list"


def create_data():
    r.set(HOT_KEY, "H" * 1024, ex=600)

    for i in range(1, 1001):
        r.set(
            f"{COLD_PREFIX}{i}",
            "C" * 1024,
            ex=600 + random.randint(0, 120),
        )

    r.set(BIG_KEY, "B" * (2 * 1024 * 1024), ex=600)

    pipe = r.pipeline(transaction=False)

    for i in range(50000):
        pipe.rpush(LIST_KEY, f"event-{i}")

        if i % 1000 == 999:
            pipe.execute()

    pipe.execute()
    r.expire(LIST_KEY, 600)


def generate_skew(total_requests=100000):
    hot_requests = 0
    cold_requests = 0

    start = time.perf_counter()

    for _ in range(total_requests):
        if random.random() < 0.80:
            r.get(HOT_KEY)
            hot_requests += 1
        else:
            item = random.randint(1, 1000)
            r.get(f"{COLD_PREFIX}{item}")
            cold_requests += 1

    elapsed = time.perf_counter() - start

    print("Total requests :", total_requests)
    print("Hot requests   :", hot_requests)
    print("Cold requests  :", cold_requests)
    print("Hot share %    :", round(hot_requests / total_requests * 100, 2))
    print("Elapsed sec    :", round(elapsed, 3))


def inspect():
    print()
    print("=== SIZE INSPECTION ===")

    print("Hot MEMORY USAGE :", r.memory_usage(HOT_KEY))
    print("Hot STRLEN       :", r.strlen(HOT_KEY))

    print("Big MEMORY USAGE :", r.memory_usage(BIG_KEY))
    print("Big STRLEN       :", r.strlen(BIG_KEY))

    print("List MEMORY USAGE:", r.memory_usage(LIST_KEY))
    print("List LLEN        :", r.llen(LIST_KEY))


if __name__ == "__main__":
    print("PING:", r.ping())

    create_data()
    generate_skew()
    inspect()
```

------------------------------------------------------------------------

## 46. Run

``` bash
python chapter18_hot_big_lab.py
```

Expected pattern:

``` text
PING: True
Total requests : 100000
Hot requests   : ~80000
Cold requests  : ~20000
Hot share %    : ~80

=== SIZE INSPECTION ===
Hot MEMORY USAGE : ...
Hot STRLEN       : 1024
Big MEMORY USAGE : ...
Big STRLEN       : 2097152
List MEMORY USAGE: ...
List LLEN        : 50000
```

Exact memory values vary.

------------------------------------------------------------------------

# Part 33 --- Interpret the Lab

## 47. Hot but Small

``` text
tutorial:chapter18:hot:global-config
```

is:

``` text
small value
very high request share
```

This is a hot key.

------------------------------------------------------------------------

## 48. Big but Not Necessarily Hot

``` text
tutorial:chapter18:big:payload
```

is large but receives no repeated reads in the generated workload.

This is a big key, not automatically a hot key.

------------------------------------------------------------------------

## 49. Large Collection

``` text
tutorial:chapter18:big:list
```

demonstrates why collection cardinality and memory both matter.

Use bounded list operations in real applications.

------------------------------------------------------------------------

# Part 34 --- Safe Collection Access

## 50. Avoid Whole-Collection Reads

Do not casually retrieve an entire huge list:

``` redis
LRANGE key 0 -1
```

in production.

Prefer bounded access aligned with application semantics:

``` redis
LRANGE key 0 99
```

The correct range depends on the workload.

------------------------------------------------------------------------

# Part 35 --- Network Calculation Lab

## 51. Formula

For a string payload:

``` text
approx payload throughput =
value bytes × reads/sec
```

For:

``` text
2 MiB × 500 reads/sec
```

approximate payload:

``` text
1000 MiB/sec
```

This simplified number excludes protocol and other overhead but is
useful for architectural screening.

------------------------------------------------------------------------

# Part 36 --- Hot-Key Expiration Lab

## 52. Expire the Hot Key

In the isolated lab:

``` redis
DEL tutorial:chapter18:hot:global-config
```

Now imagine 10,000 callers simultaneously requesting it.

Without coordination:

``` text
10,000 misses
 -> potentially many source calls
```

With single-flight:

``` text
10,000 misses
 -> one controlled regeneration
```

Reuse Chapter 15's loader-lock pattern.

------------------------------------------------------------------------

# Part 37 --- Big-Key Delete Lab

## 53. Use `UNLINK`

For the isolated big list:

``` redis
UNLINK tutorial:chapter18:big:list
```

Recreate it before subsequent lab steps if needed.

This illustrates non-blocking key deletion semantics.

------------------------------------------------------------------------

# Part 38 --- Application Telemetry Lab

## 54. Count Key Patterns

A production application can maintain metrics such as:

``` text
cache_requests_total{pattern="global-config"}
cache_requests_total{pattern="product"}
cache_requests_total{pattern="tenant-config"}
```

Do not put high-cardinality raw keys directly into metrics labels.

------------------------------------------------------------------------

# Part 39 --- Failure Injection

## 55. Failure 1 --- Extreme Hot Key

Change the workload from:

``` text
80% hot-key traffic
```

to:

``` text
99% hot-key traffic
```

Observe how total throughput becomes dominated by one key.

------------------------------------------------------------------------

## 56. Failure 2 --- Hot-Key Expiration

Expire the hot key during concurrent traffic.

Observe miss amplification.

Then apply single-flight protection.

------------------------------------------------------------------------

## 57. Failure 3 --- Hot-Key Source Slowdown

Simulate slow regeneration for the hot key.

Expected risk:

``` text
longer miss window
more waiting callers
higher application latency
```

------------------------------------------------------------------------

## 58. Failure 4 --- Large String

Increase the big string size in the isolated lab.

Measure:

``` text
MEMORY USAGE
STRLEN
GET latency
client memory
```

Do not create extreme payloads on shared systems.

------------------------------------------------------------------------

## 59. Failure 5 --- Unbounded List

Increase list cardinality.

Observe:

``` text
LLEN
MEMORY USAGE
bounded range latency
```

This demonstrates the need for retention.

------------------------------------------------------------------------

## 60. Failure 6 --- Whole-Collection Read

Compare a bounded range with a full collection read in the isolated lab.

Observe response size and latency.

Do not repeat this experiment against large production collections.

------------------------------------------------------------------------

## 61. Failure 7 --- Hot + Big

Repeatedly read the large string.

Observe:

``` text
network throughput
client CPU
latency
Redis throughput
```

This combines size and frequency risk.

------------------------------------------------------------------------

## 62. Failure 8 --- Hot-Key Eviction

Under the isolated Chapter 17 memory-pressure environment, allow a hot
key to be evicted.

Observe source regeneration behavior.

------------------------------------------------------------------------

## 63. Failure 9 --- One-Shard Skew

In a sharded lab environment, generate traffic concentrated on one key.

Compare owning-shard metrics with database averages.

------------------------------------------------------------------------

## 64. Failure 10 --- Recovery Storm

Restore a hot key or source after failure while many clients retry.

Apply:

``` text
jitter
single-flight
bounded concurrency
gradual recovery
```

------------------------------------------------------------------------

# Part 40 --- Troubleshooting

## 65. One Shard Has High CPU

Check:

``` text
operations/sec by shard
hot keys
command mix
large payloads
large collections
client distribution
```

Do not conclude that the whole database needs scaling before checking
skew.

------------------------------------------------------------------------

## 66. Network High but CPU Moderate

Check:

``` text
large GET responses
large collection responses
hot + big keys
replication traffic
client response sizes
```

Payload volume can dominate without extreme command CPU.

------------------------------------------------------------------------

## 67. Memory Concentrated

Check:

``` text
big values
large collections
retention
TTL coverage
namespace growth
duplicate cache versions
```

------------------------------------------------------------------------

## 68. Latency Spikes on One Endpoint

Map:

``` text
endpoint
 -> cache key pattern
 -> Redis command
 -> payload size
 -> shard
```

Application tracing is extremely valuable here.

------------------------------------------------------------------------

## 69. Source QPS Spikes When One Key Disappears

This strongly suggests hot-key regeneration amplification.

Apply Chapter 15 stampede controls.

------------------------------------------------------------------------

## 70. Big-Key Analysis Finds a Large Key

Do not immediately delete it.

First determine:

``` text
owner
business purpose
traffic
TTL
regeneration cost
downstream impact
safe migration plan
```

------------------------------------------------------------------------

## 71. Hot-Key Mitigation Did Not Help

Check whether the true hotspot is:

``` text
key
key pattern
shared lock
queue
large payload
source query
client-side serialization
```

The apparent Redis hot key may be only one part of the path.

------------------------------------------------------------------------

# Part 41 --- Production Runbooks

## 72. Runbook --- Hot Key

``` text
1. Confirm traffic concentration.
2. Identify key/pattern safely.
3. Identify owning application.
4. Identify command mix.
5. Measure payload size.
6. Check owning shard metrics.
7. Check TTL/eviction behavior.
8. Check source regeneration cost.
9. Enable/validate single-flight.
10. Review refresh-ahead/local-cache options.
11. Redesign key distribution only if semantics permit.
12. Validate shard and application recovery.
```

------------------------------------------------------------------------

## 73. Runbook --- Big Key

``` text
1. Identify key safely.
2. Identify Redis data type.
3. Measure logical cardinality/length.
4. Measure memory usage.
5. Identify access pattern.
6. Identify command cost.
7. Identify owner.
8. Check TTL/retention.
9. Avoid unsafe full reads/deletes.
10. Design bounded migration or decomposition if justified.
11. Validate application behavior.
12. Add size guardrails.
```

------------------------------------------------------------------------

## 74. Runbook --- Hot + Big Key

``` text
1. Measure requests/sec.
2. Measure value/cardinality.
3. Estimate network throughput.
4. Measure shard CPU/network.
5. Measure client latency/CPU.
6. Protect regeneration.
7. Reduce full-object transfer where possible.
8. Evaluate decomposition/local caching/replication strategy.
9. Roll out gradually.
10. Confirm distribution and latency improve.
```

------------------------------------------------------------------------

## 75. Runbook --- Shard Skew

``` text
1. Compare per-shard operations.
2. Compare per-shard CPU.
3. Compare per-shard network.
4. Identify dominant keys/patterns.
5. Identify command mix.
6. Determine whether skew is expected.
7. Avoid scaling-only remediation for one-key hotspots.
8. Correct key/application architecture if needed.
9. Load test.
10. Validate post-change distribution.
```

------------------------------------------------------------------------

## 76. Runbook --- Growing Collection

``` text
1. Identify data type.
2. Measure cardinality.
3. Measure growth rate.
4. Identify producer.
5. Identify retention requirement.
6. Check consumer access pattern.
7. Define safe trim/retention design.
8. Test in non-production.
9. Roll out with monitoring.
10. Confirm bounded growth.
```

------------------------------------------------------------------------

# Part 42 --- Capacity Review Template

## 77. Fields

``` text
Service:
Redis database:
Key pattern:
Data type:
Average value size:
P95 value size:
Largest expected value:
Requests/sec:
Peak requests/sec:
Top-key share:
Top-10 share:
Owning shard:
Command mix:
Response bytes/sec:
TTL:
Growth rate:
Collection cardinality:
Source regeneration latency:
Source regeneration QPS limit:
Single-flight enabled?:
Refresh-ahead enabled?:
Local cache used?:
Mitigation:
Owner:
```

------------------------------------------------------------------------

# Part 43 --- Key Design Review

## 78. Template

``` text
Business object:
Current key:
Cardinality:
Tenant dimension included?:
Time dimension needed?:
Expected requests/key/sec:
Expected value size:
Maximum value size:
Expected collection growth:
TTL:
Retention:
Cross-key atomicity needed?:
Potential hot-key risk:
Potential big-key risk:
Shard-skew risk:
Proposed guardrail:
Owner:
```

------------------------------------------------------------------------

# Production Acceptance Checklist

## 79. Hot-Key Engineering

-   [ ] Top key/pattern traffic measured.
-   [ ] Top-N traffic share measured.
-   [ ] Per-shard metrics available.
-   [ ] Known hot keys documented.
-   [ ] Hot-key expiration tested.
-   [ ] Hot-key eviction behavior tested.
-   [ ] Single-flight/source protection validated.
-   [ ] Refresh-ahead reviewed.
-   [ ] Local caching reviewed where appropriate.
-   [ ] Retry amplification controlled.
-   [ ] Recovery storm tested.

------------------------------------------------------------------------

## 80. Big-Key Engineering

-   [ ] Value-size distribution measured.
-   [ ] Collection cardinality monitored.
-   [ ] Growth/retention defined.
-   [ ] Large response paths identified.
-   [ ] Full-collection operations reviewed.
-   [ ] Large-delete behavior reviewed.
-   [ ] Memory impact measured.
-   [ ] Network impact measured.
-   [ ] Client deserialization impact reviewed.
-   [ ] Size guardrails documented.
-   [ ] Safe migration/decomposition plan available where needed.

------------------------------------------------------------------------

# Knowledge Validation

## 81. Questions

You should be able to answer:

1.  What is a hot key?
2.  What is a big key?
3.  Can a small key be hot?
4.  Can a big key be cold?
5.  Why is hot + big especially risky?
6.  What is workload skew?
7.  Why can averages hide shard hotspots?
8.  Why does adding shards not automatically solve one hot key?
9.  How can large values amplify network traffic?
10. Why can clients suffer even when Redis CPU looks normal?
11. What causes accidental hot keys?
12. What causes unbounded big collections?
13. Which commands measure string/list/hash/set/zset/stream logical
    size?
14. What does `MEMORY USAGE` provide?
15. Why avoid `KEYS *`?
16. Why should production diagnostic scans be planned?
17. Why is application telemetry valuable for hot-key detection?
18. Why should raw keys generally not become metric labels?
19. What is top-key share?
20. What is top-N share?
21. How can a hot key cause a stampede?
22. Why does hot-key eviction have the same regeneration risk as
    expiration?
23. Why should known hot keys receive warming priority?
24. When might a local cache help?
25. What complexity does application-level key replication introduce?
26. Why can whole-collection reads be dangerous?
27. Why should a big key not be immediately deleted during an incident?
28. What should a shard-skew runbook verify?
29. How do you control growing collections?
30. What must pass before declaring hot/big-key readiness?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 82. Lab Completion

-   [ ] Created hot and cold keys.
-   [ ] Generated \~80% traffic to one key.
-   [ ] Measured hot-key share.
-   [ ] Created a 2 MiB string.
-   [ ] Measured `STRLEN`.
-   [ ] Measured `MEMORY USAGE`.
-   [ ] Created a 50,000-element list.
-   [ ] Measured `LLEN`.
-   [ ] Reviewed bounded collection access.
-   [ ] Calculated payload throughput.
-   [ ] Expired/deleted hot key in isolated lab.
-   [ ] Reviewed single-flight regeneration.
-   [ ] Used `UNLINK` for isolated big-key cleanup.
-   [ ] Reviewed safe application telemetry.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed troubleshooting review.
-   [ ] Reviewed production runbooks.
-   [ ] Completed capacity review.
-   [ ] Completed key-design review.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 83. Lab Cleanup

Discover chapter keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter18:*'
```

Delete only confirmed lab keys.

Examples:

``` redis
UNLINK tutorial:chapter18:hot:global-config
UNLINK tutorial:chapter18:big:payload
UNLINK tutorial:chapter18:big:list
```

Delete the isolated `tutorial:chapter18:cold:*` keys in bounded batches
after reviewing the namespace.

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

against a shared or production database.

------------------------------------------------------------------------

# 84. Key Takeaways

1.  Hot keys are traffic problems; big keys are size/cardinality
    problems.
2.  A key can be hot, big, both, or neither.
3.  Hot + big keys can concentrate CPU, memory, network, and client
    cost.
4.  Database averages can hide severe per-shard skew.
5.  One key maps to one owning shard at a time; more shards do not
    automatically split one key's traffic.
6.  Workload popularity is often naturally skewed.
7.  Accidental key-design errors can create artificial hotspots.
8.  Unbounded collections become big keys over time.
9.  Logical cardinality and memory usage are different measurements.
10. Diagnostic scans and big-key tooling must be used deliberately in
    production.
11. Application telemetry is often the best source of hot-key
    visibility.
12. Avoid raw high-cardinality key identities in metrics.
13. Large values amplify network and client-side costs.
14. Full reads of huge collections should be avoided.
15. `UNLINK` can be preferable for large disposable-key deletion where
    supported and appropriate.
16. Splitting a big key introduces additional consistency and
    application complexity.
17. Local caching can reduce Redis traffic for suitable hot, slowly
    changing data.
18. Hot-key expiration and eviction both require source-protection
    controls.
19. Known hot keys should influence warming priority.
20. Production readiness requires key/pattern telemetry, shard
    visibility, size guardrails, source protection, failure testing, and
    runbooks.

------------------------------------------------------------------------

# 85. References

Validate exact commands, diagnostic options, complexity, and behavior
against the Redis and Redis Enterprise versions deployed.

Recommended official Redis documentation areas:

-   `MEMORY USAGE`
-   `STRLEN`
-   `HLEN`
-   `LLEN`
-   `SCARD`
-   `ZCARD`
-   `XLEN`
-   `SCAN`
-   `UNLINK`
-   Redis CLI diagnostic modes
-   Redis command complexity documentation
-   Redis key eviction
-   Redis Cluster / sharding concepts
-   Redis Enterprise monitoring and shard metrics

Hot-key and big-key thresholds are workload-specific. Define guardrails
from application latency, value-size distribution, request rate, shard
capacity, network capacity, and source regeneration cost rather than
adopting arbitrary universal numbers.

------------------------------------------------------------------------

# Next Chapter

**Chapter 19 --- Redis TTL Strategy, Expiration Engineering & Data
Freshness**

Chapter 19 will go deeply into:

-   TTL design
-   freshness contracts
-   hard vs. soft expiration
-   TTL jitter
-   synchronized expiration
-   sliding expiration
-   absolute expiration
-   TTL selection by data class
-   expiration observability
-   stale-data risk
-   source load
-   expiration storms
-   refresh-ahead interaction
-   failure injection
-   troubleshooting
-   production runbooks
-   acceptance validation
