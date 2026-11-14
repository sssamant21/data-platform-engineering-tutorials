# Chapter 25 --- Redis Rate Limiting, Quotas & Traffic Protection

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Intermediate → Production Traffic Protection Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Fixed-window limiting, atomic counters, TTL-safe
initialization, sliding-window limiting, token-bucket limiting, burst
control, per-user/per-tenant quotas, distributed concurrency, hot-key
analysis, fail-open/fail-closed policy, failure injection,
observability, troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Rate limiting protects systems from workloads that arrive faster than
they can safely process.

Examples:

``` text
API requests per user
requests per tenant
login attempts per identity
expensive search requests
source-database calls
cache-miss regeneration
background-job submissions
```

Redis is often used because it provides fast atomic operations, TTLs,
server-side scripting, and shared state across application instances.

By the end, you should be able to:

-   Explain rate limiting and quotas.
-   Distinguish rate, concurrency, and capacity limits.
-   Implement fixed-window counters.
-   Avoid counter/TTL races.
-   Explain boundary bursts.
-   Implement a sliding-window limiter.
-   Understand token-bucket behavior.
-   Configure sustained rate and burst capacity.
-   Apply per-user and per-tenant limits.
-   Understand hierarchical limits.
-   Make limiter decisions atomically.
-   Control hot-key pressure.
-   Define fail-open vs. fail-closed behavior.
-   Protect downstream dependencies.
-   Observe allowed, rejected, and error decisions.
-   Inject limiter failures.
-   Troubleshoot production incidents.
-   Build production runbooks and acceptance criteria.

------------------------------------------------------------------------

# 2. Core Production Principle

A rate limiter is not just:

``` text
counter < limit
```

A production limiter needs:

``` text
identity
rate
window or refill model
burst policy
atomic decision
TTL/state cleanup
failure behavior
observability
capacity
```

The limit must correspond to the capacity or policy you are actually
trying to protect.

------------------------------------------------------------------------

# Part 1 --- Rate vs. Concurrency

## 3. Rate

Rate answers:

``` text
How many operations may begin over time?
```

Example:

``` text
100 requests / second
```

------------------------------------------------------------------------

## 4. Concurrency

Concurrency answers:

``` text
How many operations may be in flight simultaneously?
```

Example:

``` text
maximum 20 source queries at once
```

A rate limiter does not automatically enforce concurrency.

For slow downstream systems, both may be needed.

------------------------------------------------------------------------

# Part 2 --- Quotas

## 5. Quota

A quota usually controls consumption over a larger period.

Examples:

``` text
10,000 requests/day
1,000 exports/hour
100 expensive jobs/tenant/day
```

Quota semantics may differ from short-term traffic shaping.

------------------------------------------------------------------------

# Part 3 --- Limiter Identity

## 6. Choose the Dimension

Possible dimensions:

``` text
user
tenant
API key
IP
endpoint
resource
operation type
service
```

Do not create a limiter whose identity can be trivially bypassed or
whose key cardinality becomes uncontrolled.

------------------------------------------------------------------------

# Part 4 --- Fixed Window

## 7. Concept

For:

``` text
limit = 100/minute
```

create a counter for each minute window.

Conceptual key:

``` text
ratelimit:user:1001:20261008T2205
```

Increment each request.

Reject after 100.

------------------------------------------------------------------------

# Part 5 --- Fixed-Window Boundary Burst

## 8. Weakness

A client can send:

``` text
100 requests at 12:00:59
+
100 requests at 12:01:00
```

Although each window respects 100/minute, 200 requests can arrive within
roughly one second around the boundary.

This may be unacceptable for downstream protection.

------------------------------------------------------------------------

# Part 6 --- Counter + TTL

## 9. Cleanup

Rate-limit state should normally expire.

Example:

``` text
INCR counter
EXPIRE counter
```

**This is intentionally schematic, non-executable pseudocode illustrating an unsafe two-command sequence.** The literal `EXPIRE counter` is also missing the required timeout argument: runnable Redis syntax is `EXPIRE key seconds`. Do **not** use the illustrated two-command sequence as a safe rate-limit implementation. Instead, the later Lua lab shows how to initialize a counter and its expiration atomically, subject to the validated Redis version and application semantics.

But performing these as unrelated client commands can create
race/failure problems.

------------------------------------------------------------------------

# Part 7 --- TTL Race

## 10. Failure

If:

``` text
INCR succeeds
client crashes
EXPIRE never executes
```

the limiter key may remain indefinitely.

Use an atomic pattern for counter initialization and expiration.

------------------------------------------------------------------------

# Part 8 --- Atomic Fixed Window

## 11. Lua Pattern

``` lua
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("PEXPIRE", KEYS[1], ARGV[1])
end

if current > tonumber(ARGV[2]) then
    return {0, current}
end

return {1, current}
```

Inputs:

``` text
ARGV[1] = window TTL ms
ARGV[2] = limit
```

Return:

``` text
1 -> allowed
0 -> rejected
```

plus current count.

------------------------------------------------------------------------

# Part 9 --- Fixed-Window Key Design

## 12. Time Bucket

The application can derive the bucket:

``` text
floor(timestamp / window_size)
```

and construct:

``` text
rate:{tenant}:endpoint:bucket
```

Time-source consistency matters.

------------------------------------------------------------------------

# Part 10 --- Server vs. Client Time

## 13. Clock Consideration

Distributed application instances may have clock skew.

For algorithms that depend strongly on time, define the trusted time
source and validate its behavior.

Do not casually mix inconsistent clocks.

------------------------------------------------------------------------

# Part 11 --- Sliding Window

## 14. Goal

A sliding-window limiter considers a moving interval rather than a fixed
calendar bucket.

Example:

``` text
at most 100 requests during the previous 60 seconds
```

This reduces boundary-burst behavior.

------------------------------------------------------------------------

# Part 12 --- Sliding Log

## 15. Sorted-Set Concept

Use a sorted set:

``` text
score = request timestamp
member = unique request ID
```

For each request:

``` text
remove entries older than window
count current entries
if below limit:
    add request
    allow
else:
    reject
```

These steps should be atomic.

------------------------------------------------------------------------

# Part 13 --- Sliding-Window Cost

## 16. Tradeoff

Compared with a simple counter, sliding logs require more:

``` text
memory
commands/work
per-request state
cleanup
```

Use when the improved accuracy justifies the cost.

------------------------------------------------------------------------

# Part 14 --- Unique Members

## 17. Avoid Collisions

If sorted-set member is only:

``` text
timestamp
```

two requests at the same timestamp may collide.

Use a unique request identifier where the algorithm requires distinct
events.

------------------------------------------------------------------------

# Part 15 --- Sliding-Window Lua

## 18. Atomic Flow

A bounded script can:

``` text
remove expired entries
count active entries
conditionally add current request
set TTL
return decision
```

Keep window size and cardinality bounded by policy.

------------------------------------------------------------------------

# Part 16 --- Token Bucket

## 19. Concept

A token bucket models:

``` text
tokens refill over time
request consumes token(s)
bucket has maximum capacity
```

This supports:

``` text
sustained rate
+
controlled burst
```

------------------------------------------------------------------------

# Part 17 --- Token Bucket Parameters

## 20. Fields

``` text
refill rate
bucket capacity
request cost
current tokens
last refill time
```

Example:

``` text
refill = 10 tokens/sec
capacity = 50
cost = 1/request
```

A quiet client can accumulate up to 50 tokens and then burst.

------------------------------------------------------------------------

# Part 18 --- Burst Capacity

## 21. Explicit Policy

Burst is not an accident.

If:

``` text
rate = 10/sec
capacity = 50
```

the system intentionally permits a short burst larger than the sustained
rate.

Set capacity based on downstream tolerance.

------------------------------------------------------------------------

# Part 19 --- Weighted Requests

## 22. Request Cost

Not all operations cost the same.

Example:

``` text
simple lookup = 1 token
expensive report = 10 tokens
large export = 25 tokens
```

Weighted limiting can better represent downstream cost.

------------------------------------------------------------------------

# Part 20 --- Leaky-Bucket Concept

## 23. Traffic Smoothing

A leaky-bucket-style model aims to release work at a controlled pace.

It is useful conceptually when:

``` text
bursty arrivals
must become smoother downstream work
```

Queueing and worker systems may be more natural than a pure request
rejection limiter for some use cases.

------------------------------------------------------------------------

# Part 21 --- Per-User Limits

## 24. Example

``` text
user 1001 -> 20 requests/sec
user 1002 -> 20 requests/sec
```

This prevents one user from consuming all shared capacity.

------------------------------------------------------------------------

# Part 22 --- Per-Tenant Limits

## 25. Shared Budget

A tenant may contain many users.

Example:

``` text
user limit   = 20/sec
tenant limit = 500/sec
```

Both can apply.

------------------------------------------------------------------------

# Part 23 --- Hierarchical Limiting

## 26. Layers

A request may need to satisfy:

``` text
user limit
tenant limit
service/global limit
dependency limit
```

Be careful: multiple limiter checks increase Redis work and can require
atomic design if all limits must be consumed consistently.

------------------------------------------------------------------------

# Part 24 --- Global Limit

## 27. Hot-Key Risk

A global counter such as:

``` text
ratelimit:global
```

can become a hot key at high request volume.

The limiter itself must not become the bottleneck it is trying to
prevent.

------------------------------------------------------------------------

# Part 25 --- Sharded Redis

## 28. Distribution

Per-user or per-tenant keys naturally distribute better than one global
key.

However, multi-key atomic hierarchical limits may require compatible
placement.

Review Redis Enterprise topology and cluster slot requirements.

------------------------------------------------------------------------

# Part 26 --- Hash Tags

## 29. Co-Location

Where required:

``` text
rate:{tenant-1001}:tenant
rate:{tenant-1001}:user:2001
```

can place related keys together in Redis Cluster-style slotting.

Use only when atomic co-location is required.

Avoid creating unnecessary hot slots.

------------------------------------------------------------------------

# Part 27 --- Limit Rejection

## 30. Response

A rejected request should have defined behavior.

Possible application response:

``` text
HTTP 429
retry-after guidance
clear error code
```

Do not let clients retry immediately without bounds.

------------------------------------------------------------------------

# Part 28 --- Retry-After

## 31. Useful Signal

Where possible, provide an estimate of when capacity becomes available.

This reduces blind retry behavior.

The calculation depends on the limiter algorithm.

------------------------------------------------------------------------

# Part 29 --- Retry Amplification

## 32. Danger

If rejected clients immediately retry:

``` text
limit reached
 -> reject
 -> retry
 -> reject
 -> retry
```

traffic can increase.

Clients need:

``` text
backoff
jitter
retry cap
```

------------------------------------------------------------------------

# Part 30 --- Fail-Open

## 33. Policy

If Redis is unavailable:

``` text
allow request
```

This preserves application availability but removes protection.

Appropriate only when overload/abuse risk is acceptable.

------------------------------------------------------------------------

# Part 31 --- Fail-Closed

## 34. Policy

If Redis is unavailable:

``` text
reject request
```

This preserves the control boundary but reduces availability.

Appropriate when exceeding the limit is more dangerous than rejecting
traffic.

------------------------------------------------------------------------

# Part 32 --- Fail-Open vs. Fail-Closed

## 35. Must Be Explicit

Document per limiter:

``` text
Redis timeout:
Redis connection failure:
script error:
unknown state:
```

Do not allow accidental client-library behavior to choose the business
policy.

------------------------------------------------------------------------

# Part 33 --- Local Emergency Limiter

## 36. Degraded Mode

Some systems use a conservative process-local fallback during Redis
failure.

Tradeoffs:

``` text
not globally coordinated
may preserve partial protection
requires separate capacity assumptions
```

Treat it as a deliberate degraded mode, not equivalent to the
distributed limiter.

------------------------------------------------------------------------

# Part 34 --- Dependency Protection

## 37. Source Capacity

Suppose database safely handles:

``` text
2,000 expensive queries/sec
```

A service-level limiter can help keep offered load below that capacity.

Leave headroom for:

``` text
other services
background jobs
recovery traffic
operational variance
```

------------------------------------------------------------------------

# Part 35 --- Cache Miss Protection

## 38. Combine Controls

During a cache incident:

``` text
misses -> source
```

Use Chapter 15 controls:

``` text
single-flight
source concurrency limit
rate limit
circuit breaker
stale serving where safe
```

Rate limiting is one layer, not the entire protection strategy.

------------------------------------------------------------------------

# Part 36 --- Quota Reset

## 39. Calendar Semantics

Daily/monthly quotas require precise definitions:

``` text
timezone
reset boundary
DST behavior
billing period
late events
```

Do not assume "day" is universally unambiguous.

------------------------------------------------------------------------

# Part 37 --- Cardinality

## 40. Key Count

A limiter may create one key per:

``` text
user
tenant
endpoint
window
```

Estimate:

``` text
active identities × active windows
```

TTL cleanup is essential.

------------------------------------------------------------------------

# Part 38 --- Memory Capacity

## 41. Estimate

For sliding logs, memory roughly grows with:

``` text
active identities
×
requests retained per window
```

This can be much larger than fixed-window counters.

Benchmark representative cardinality.

------------------------------------------------------------------------

# Part 39 --- Eviction

## 42. Limiter State Must Be Protected

If rate-limit keys are evicted under memory pressure:

``` text
counter disappears
client receives fresh budget
```

That can weaken enforcement.

Review Chapter 17 memory policy and isolate critical limiter state
appropriately.

------------------------------------------------------------------------

# Part 40 --- TTL Expiration

## 43. Expiration Storm

Millions of limiter keys with identical expiration patterns can
concentrate cleanup work.

Key/window design and workload distribution matter.

------------------------------------------------------------------------

# Part 41 --- Observability

## 44. Decision Metrics

Track:

``` text
rate_limit_requests_total
rate_limit_allowed_total
rate_limit_rejected_total
rate_limit_errors_total
```

------------------------------------------------------------------------

## 45. Policy Metrics

Track bounded labels such as:

``` text
limiter_name
algorithm
decision
service
```

Avoid high-cardinality user IDs or raw keys as metric labels.

------------------------------------------------------------------------

## 46. Latency Metrics

Track:

``` text
rate_limit_check_duration_seconds
Redis command/script latency
```

A limiter on every request is part of the request latency path.

------------------------------------------------------------------------

## 47. Saturation Metrics

Useful:

``` text
rejection ratio
remaining budget distribution
hot limiter keys
Redis CPU
Redis ops/sec
network
memory
```

------------------------------------------------------------------------

# Part 42 --- Alerting

## 48. Conditions

Alert on sustained:

``` text
unexpected rejection spike
limiter error spike
Redis latency
fail-open activation
fail-closed activation
memory pressure
hot-key concentration
```

A normal policy rejection is not automatically an infrastructure
incident.

------------------------------------------------------------------------

# Part 43 --- Hands-On Lab

## 49. Objectives

You will:

1.  implement fixed-window limiting;
2.  make counter + TTL atomic;
3.  reproduce boundary bursts;
4.  implement sliding-window limiting;
5.  implement token bucket;
6.  test burst capacity;
7.  test weighted requests;
8.  test per-user/per-tenant limits;
9.  simulate Redis errors;
10. test fail-open/fail-closed;
11. inject hot-key pressure;
12. clean up safely.

------------------------------------------------------------------------

## 50. Prerequisites

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

# Part 44 --- Fixed-Window Lab

## 51. Lua Script

``` lua
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("PEXPIRE", KEYS[1], ARGV[1])
end

local limit = tonumber(ARGV[2])

if current > limit then
    return {0, current}
end

return {1, current}
```

------------------------------------------------------------------------

# Part 45 --- Python Lab

## 52. Create `chapter25_rate_limit_lab.py`

``` python
import math
import os
import time
import uuid

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

FIXED_SCRIPT = """
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("PEXPIRE", KEYS[1], ARGV[1])
end

local limit = tonumber(ARGV[2])

if current > limit then
    return {0, current}
end

return {1, current}
"""

SLIDING_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local cutoff = now - window

redis.call(
    "ZREMRANGEBYSCORE",
    key,
    "-inf",
    cutoff
)

local count = redis.call(
    "ZCARD",
    key
)

if count >= limit then
    redis.call(
        "PEXPIRE",
        key,
        window
    )

    return {0, count}
end

redis.call(
    "ZADD",
    key,
    now,
    member
)

redis.call(
    "PEXPIRE",
    key,
    window
)

return {1, count + 1}
"""

TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]

local now_ms = tonumber(ARGV[1])
local refill_per_sec = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl_ms = tonumber(ARGV[5])

local values = redis.call(
    "HMGET",
    key,
    "tokens",
    "last_ms"
)

local tokens = tonumber(values[1])
local last_ms = tonumber(values[2])

if not tokens then
    tokens = capacity
end

if not last_ms then
    last_ms = now_ms
end

local elapsed_ms = math.max(
    0,
    now_ms - last_ms
)

local refill = (
    elapsed_ms / 1000.0
) * refill_per_sec

tokens = math.min(
    capacity,
    tokens + refill
)

local allowed = 0

if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
end

redis.call(
    "HSET",
    key,
    "tokens",
    tokens,
    "last_ms",
    now_ms
)

redis.call(
    "PEXPIRE",
    key,
    ttl_ms
)

return {
    allowed,
    tostring(tokens)
}
"""


def fixed_window(
    identity,
    limit=5,
    window_ms=10000,
):
    bucket = int(
        time.time() * 1000
    ) // window_ms

    key = (
        f"tutorial:chapter25:fixed:"
        f"{identity}:{bucket}"
    )

    return r.eval(
        FIXED_SCRIPT,
        1,
        key,
        window_ms + 1000,
        limit,
    )


def sliding_window(
    identity,
    limit=5,
    window_ms=10000,
):
    now_ms = int(
        time.time() * 1000
    )

    key = (
        f"tutorial:chapter25:sliding:"
        f"{identity}"
    )

    member = (
        f"{now_ms}:{uuid.uuid4()}"
    )

    return r.eval(
        SLIDING_SCRIPT,
        1,
        key,
        now_ms,
        window_ms,
        limit,
        member,
    )


def token_bucket(
    identity,
    refill_per_sec=2,
    capacity=5,
    cost=1,
):
    now_ms = int(
        time.time() * 1000
    )

    key = (
        f"tutorial:chapter25:bucket:"
        f"{identity}"
    )

    ttl_ms = int(
        max(
            60000,
            (
                capacity
                / refill_per_sec
            )
            * 2000,
        )
    )

    return r.eval(
        TOKEN_BUCKET_SCRIPT,
        1,
        key,
        now_ms,
        refill_per_sec,
        capacity,
        cost,
        ttl_ms,
    )


if __name__ == "__main__":
    print("PING:", r.ping())

    print()
    print("FIXED WINDOW")

    for i in range(1, 8):
        print(
            i,
            fixed_window(
                "user-1001",
                limit=5,
                window_ms=10000,
            ),
        )

    print()
    print("SLIDING WINDOW")

    for i in range(1, 8):
        print(
            i,
            sliding_window(
                "user-2001",
                limit=5,
                window_ms=10000,
            ),
        )

    print()
    print("TOKEN BUCKET")

    for i in range(1, 8):
        print(
            i,
            token_bucket(
                "user-3001",
                refill_per_sec=2,
                capacity=5,
                cost=1,
            ),
        )
```

------------------------------------------------------------------------

# Part 46 --- Run Lab

## 53. Execute

``` bash
python chapter25_rate_limit_lab.py
```

Expected pattern:

``` text
first requests -> allowed
later requests -> rejected
```

Exact token values and timing vary.

------------------------------------------------------------------------

# Part 47 --- Fixed-Window Boundary Lab

## 54. Test

Use a small window such as:

``` text
5 seconds
```

Send requests near the end of one window and immediately at the
beginning of the next.

Observe the boundary burst.

This demonstrates why fixed-window limiting may be insufficient for
strict smoothing.

------------------------------------------------------------------------

# Part 48 --- Sliding-Window Lab

## 55. Inspect State

``` redis
ZRANGE tutorial:chapter25:sliding:user-2001 0 -1 WITHSCORES
```

Observe request timestamps retained inside the active window.

------------------------------------------------------------------------

# Part 49 --- Token-Bucket Burst Lab

## 56. Capacity

Configure:

``` text
refill = 2/sec
capacity = 5
```

After the bucket is full, send five requests rapidly.

Expected:

``` text
five may be allowed
additional immediate requests rejected
```

Wait and observe refill.

------------------------------------------------------------------------

# Part 50 --- Weighted Request Lab

## 57. Cost

Call:

``` python
token_bucket(
    "tenant-1001",
    refill_per_sec=10,
    capacity=20,
    cost=5,
)
```

A cost-5 operation consumes more budget than a cost-1 request.

------------------------------------------------------------------------

# Part 51 --- Per-User and Per-Tenant Lab

## 58. Two Layers

Concept:

``` python
user_ok = token_bucket(
    "user:2001",
    refill_per_sec=5,
    capacity=10,
    cost=1,
)

tenant_ok = token_bucket(
    "tenant:1001",
    refill_per_sec=50,
    capacity=100,
    cost=1,
)
```

For strict all-or-nothing consumption across multiple limiter keys,
separate sequential checks may be insufficient.

Design atomic hierarchical consumption carefully and account for cluster
key placement.

------------------------------------------------------------------------

# Part 52 --- Fail-Open Lab

## 59. Wrapper

Concept:

``` python
def allow_fail_open(check):
    try:
        return check()
    except redis.RedisError:
        return [1, "fail-open"]
```

Use only where policy explicitly permits bypass during Redis failure.

------------------------------------------------------------------------

# Part 53 --- Fail-Closed Lab

## 60. Wrapper

``` python
def allow_fail_closed(check):
    try:
        return check()
    except redis.RedisError:
        return [0, "fail-closed"]
```

Again, this is a business/reliability policy, not merely a coding
preference.

------------------------------------------------------------------------

# Part 54 --- Concurrency Test

## 61. Distributed Clients

Run multiple processes against the same identity.

Validate:

``` text
total allowed requests
```

not merely each process's local result.

The purpose of Redis is shared limiter state across application
instances.

------------------------------------------------------------------------

# Part 55 --- Hot-Key Test

## 62. Global Key

In a disposable environment, direct many workers at one limiter
identity.

Measure:

``` text
ops/sec
Redis CPU
latency
rejections
```

Compare with traffic distributed across many identities.

------------------------------------------------------------------------

# Part 56 --- Failure Injection

## 63. Failure 1 --- Counter Without TTL

Demonstrate why separate non-atomic initialization can leave state
without expiration.

Then use the atomic script.

------------------------------------------------------------------------

## 64. Failure 2 --- Boundary Burst

Send maximum traffic at the end and start of adjacent fixed windows.

Observe short-term burst above the nominal sustained rate.

------------------------------------------------------------------------

## 65. Failure 3 --- Sliding-Window Cardinality

Increase limit/window traffic in a disposable environment.

Observe sorted-set cardinality and memory.

------------------------------------------------------------------------

## 66. Failure 4 --- Token-Bucket Burst Too Large

Configure excessive capacity.

Observe downstream burst.

Reduce capacity to match dependency tolerance.

------------------------------------------------------------------------

## 67. Failure 5 --- Retry Storm

Have rejected clients retry immediately.

Observe offered traffic.

Then add client backoff and jitter.

------------------------------------------------------------------------

## 68. Failure 6 --- Redis Unavailable / Fail-Open

Interrupt Redis in a disposable environment.

Verify requests follow the documented fail-open policy.

Measure the downstream impact.

------------------------------------------------------------------------

## 69. Failure 7 --- Redis Unavailable / Fail-Closed

Repeat with fail-closed policy.

Verify controlled rejection.

------------------------------------------------------------------------

## 70. Failure 8 --- Hot Global Limiter

Drive high concurrency through one global key.

Observe concentration.

Review whether a hierarchical/distributed design is needed.

------------------------------------------------------------------------

## 71. Failure 9 --- Limiter State Eviction

In an isolated constrained environment, create memory pressure that can
evict limiter state.

Observe whether a client receives a reset budget.

Critical limiter state should not silently depend on an unsafe eviction
configuration.

------------------------------------------------------------------------

## 72. Failure 10 --- Clock Skew

Simulate clients passing inconsistent timestamps to a time-sensitive
algorithm.

Observe incorrect refill/window behavior.

Define and enforce a trusted time strategy.

------------------------------------------------------------------------

# Part 57 --- Troubleshooting

## 73. Too Many Requests Allowed

Check:

``` text
algorithm
limit
burst capacity
window boundary
key identity
TTL
eviction
multiple Redis databases
clock source
```

------------------------------------------------------------------------

## 74. Too Many Requests Rejected

Check:

``` text
wrong identity mapping
limit too low
token refill calculation
stale state
TTL
weighted request cost
clock issue
```

------------------------------------------------------------------------

## 75. Counter Never Resets

Check:

``` text
TTL exists
atomic initialization
key naming
window calculation
```

------------------------------------------------------------------------

## 76. Redis CPU High

Check:

``` text
limiter calls/sec
hot global key
sliding-window sorted sets
script complexity
hierarchical checks
```

------------------------------------------------------------------------

## 77. Memory High

Check:

``` text
active identities
TTL
sliding-window cardinality
quota retention
orphaned keys
```

------------------------------------------------------------------------

## 78. Latency High

Check:

``` text
Redis latency
script duration
network
hot keys
large sorted sets
multiple limiter layers
```

------------------------------------------------------------------------

## 79. Fail-Open Activated Unexpectedly

Check:

``` text
Redis timeout
connection pool
DNS/network
script errors
client fallback code
```

Fail-open events should be observable.

------------------------------------------------------------------------

## 80. Tenant Limit Incorrect

Check whether all tenant traffic maps to the same intended identity and
Redis state.

Watch for:

``` text
tenant aliases
region-specific keys
multiple databases
hashing differences
```

------------------------------------------------------------------------

# Part 58 --- Production Runbooks

## 81. Runbook --- Rejection Spike

``` text
1. Identify limiter/policy.
2. Measure rejection ratio.
3. Confirm traffic volume.
4. Confirm configured limit.
5. Check downstream health.
6. Check Redis latency/errors.
7. Check key identity mapping.
8. Check algorithm state.
9. Adjust only with capacity evidence.
10. Confirm rejection rate normalizes.
```

------------------------------------------------------------------------

## 82. Runbook --- Limiter Allows Excess Traffic

``` text
1. Confirm actual allowed rate.
2. Identify algorithm.
3. Check fixed-window boundary effect.
4. Check burst capacity.
5. Check TTL.
6. Check eviction.
7. Check clock source.
8. Check distributed clients share state.
9. Protect downstream immediately if needed.
10. Correct policy and retest.
```

------------------------------------------------------------------------

## 83. Runbook --- Redis Limiter Failure

``` text
1. Confirm Redis error.
2. Identify affected limiter.
3. Apply documented fail-open/fail-closed policy.
4. Protect downstream capacity.
5. Stop uncontrolled retries.
6. Restore Redis/client connectivity.
7. Validate limiter state.
8. Monitor recovery burst.
9. Confirm policy enforcement.
10. Review degraded-mode behavior.
```

------------------------------------------------------------------------

## 84. Runbook --- Hot Limiter Key

``` text
1. Identify hot key/policy.
2. Measure operations/sec.
3. Measure Redis CPU/latency.
4. Determine why key is global.
5. Review per-tenant/per-resource partitioning.
6. Preserve required global protection.
7. Avoid unsafe approximate bypass.
8. Load-test redesigned policy.
9. Monitor shard distribution.
10. Document capacity.
```

------------------------------------------------------------------------

## 85. Runbook --- Limiter Memory Growth

``` text
1. Measure limiter key count.
2. Measure TTL coverage.
3. Identify algorithm.
4. Measure sorted-set cardinality.
5. Check quota retention.
6. Check orphaned keys.
7. Correct expiration.
8. Bound window/cardinality.
9. Recalculate capacity.
10. Confirm memory stabilizes.
```

------------------------------------------------------------------------

# Part 59 --- Rate-Limit Design Template

## 86. Fields

``` text
Service:
Limiter name:
Protected dependency:
Identity:
Algorithm:
Sustained rate:
Burst capacity:
Window:
Request cost:
Per-user limit:
Per-tenant limit:
Global limit:
TTL:
Time source:
Expected identities:
Expected calls/sec:
Expected Redis ops/sec:
Fail-open or fail-closed:
Retry-after behavior:
Client backoff:
Eviction protection:
Cluster placement:
Metrics:
Owner:
```

------------------------------------------------------------------------

# Part 60 --- Capacity Worksheet

## 87. Record

``` text
Downstream safe capacity:
Existing baseline load:
Reserved headroom:
Limiter target:
Expected peak clients:
Expected identities:
Redis checks/request:
Peak limiter checks/sec:
Expected state/key count:
Expected memory:
Redis CPU headroom:
Network headroom:
```

A limiter should be derived from capacity, not arbitrary round numbers.

------------------------------------------------------------------------

# Part 61 --- Algorithm Decision Guide

## 88. Fixed Window

Choose when:

``` text
simple policy
boundary burst acceptable
low state cost desired
```

------------------------------------------------------------------------

## 89. Sliding Window

Choose when:

``` text
moving-window accuracy matters
boundary burst is undesirable
higher state/CPU cost is acceptable
```

------------------------------------------------------------------------

## 90. Token Bucket

Choose when:

``` text
sustained rate + explicit burst capacity
```

are natural policy requirements.

------------------------------------------------------------------------

# Production Acceptance Checklist

## 91. Traffic Protection

-   [ ] Protected resource documented.
-   [ ] Limiter identity documented.
-   [ ] Rate vs. concurrency requirement separated.
-   [ ] Algorithm selected intentionally.
-   [ ] Limit derived from capacity/policy.
-   [ ] Burst behavior documented.
-   [ ] Fixed-window boundary behavior tested where applicable.
-   [ ] Counter + TTL atomicity tested.
-   [ ] Sliding-window cardinality tested where applicable.
-   [ ] Token refill tested where applicable.
-   [ ] Weighted request behavior tested where applicable.
-   [ ] Per-user limit tested.
-   [ ] Per-tenant limit tested.
-   [ ] Global/hierarchical design reviewed.
-   [ ] Hot-key risk tested.
-   [ ] Time source documented.
-   [ ] Fail-open/fail-closed policy documented.
-   [ ] Redis outage behavior tested.
-   [ ] Retry/backoff behavior tested.
-   [ ] Limiter state eviction risk reviewed.
-   [ ] Memory capacity reviewed.
-   [ ] Rejection metrics available.
-   [ ] Limiter errors observable.
-   [ ] Production runbooks validated.

------------------------------------------------------------------------

# Knowledge Validation

## 92. Questions

You should be able to answer:

1.  What is rate limiting?
2.  How does rate differ from concurrency?
3.  What is a quota?
4.  What determines limiter identity?
5.  How does a fixed-window limiter work?
6.  What is the fixed-window boundary-burst problem?
7.  Why must counter initialization and TTL be atomic?
8.  What is a sliding-window limiter?
9.  Why can sliding windows consume more memory?
10. Why should sorted-set members be unique?
11. What is a token bucket?
12. What is refill rate?
13. What is bucket capacity?
14. How does bucket capacity control bursts?
15. What are weighted requests?
16. What is hierarchical limiting?
17. Why can a global limiter become a hot key?
18. Why can immediate retries amplify traffic?
19. What is fail-open?
20. What is fail-closed?
21. Why must failure policy be explicit?
22. How can rate limiting protect a database?
23. Why is rate limiting only one part of cache-miss source protection?
24. Why do quota reset semantics require timezone decisions?
25. Why does limiter cardinality matter?
26. What happens if limiter state is evicted?
27. Why does clock consistency matter?
28. Which metrics should be monitored?
29. Why should limits be based on downstream capacity?
30. What must pass before a limiter is production-ready?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 93. Lab Completion

-   [ ] Implemented fixed-window limiter.
-   [ ] Used atomic counter + TTL.
-   [ ] Tested allow/reject behavior.
-   [ ] Reproduced fixed-window boundary burst.
-   [ ] Implemented sliding-window limiter.
-   [ ] Inspected sorted-set state.
-   [ ] Implemented token bucket.
-   [ ] Tested token refill.
-   [ ] Tested burst capacity.
-   [ ] Tested weighted request cost.
-   [ ] Reviewed per-user limiting.
-   [ ] Reviewed per-tenant limiting.
-   [ ] Reviewed hierarchical atomicity.
-   [ ] Implemented fail-open wrapper.
-   [ ] Implemented fail-closed wrapper.
-   [ ] Tested distributed clients.
-   [ ] Tested hot-key pressure.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed troubleshooting.
-   [ ] Reviewed five production runbooks.
-   [ ] Completed rate-limit design template.
-   [ ] Completed capacity worksheet.
-   [ ] Completed algorithm decision guide.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 94. Lab Cleanup

Discover:

``` bash
redis-cli --scan --pattern 'tutorial:chapter25:*'
```

Delete only confirmed Chapter 25 training keys in bounded batches with
`UNLINK`.

Examples:

``` text
tutorial:chapter25:fixed:*
tutorial:chapter25:sliding:*
tutorial:chapter25:bucket:*
```

Use `SCAN` to discover exact keys before deleting them.

Do not use:

``` redis
KEYS tutorial:chapter25:*
FLUSHDB
FLUSHALL
```

against a shared or production database.

------------------------------------------------------------------------

# 95. Key Takeaways

1.  Rate limiting controls operations over time; concurrency limiting
    controls simultaneous work.
2.  Quotas and short-term traffic shaping are related but distinct
    controls.
3.  Limiter identity must match the resource or consumer being
    controlled.
4.  Fixed-window counters are simple but permit boundary bursts.
5.  Counter creation and TTL assignment should be atomic.
6.  Sliding windows improve moving-window accuracy at higher state and
    processing cost.
7.  Token buckets naturally represent sustained rate plus explicit burst
    capacity.
8.  Weighted requests can model different operation costs.
9.  Per-user and per-tenant controls can protect fairness and shared
    capacity.
10. Hierarchical limiting requires careful atomicity and topology
    design.
11. Global limiter keys can become hot keys.
12. Rejected clients need backoff and jitter to avoid retry
    amplification.
13. Fail-open preserves availability but removes protection.
14. Fail-closed preserves the control boundary but rejects traffic
    during limiter failure.
15. Failure policy must be an explicit business/reliability decision.
16. Limiter state requires TTL, memory capacity, and eviction
    protection.
17. Time-sensitive algorithms require a defined time source.
18. A limiter on every request must itself meet latency and availability
    objectives.
19. Limits should be based on downstream capacity or explicit product
    policy.
20. Production readiness requires atomic decisions, realistic load
    testing, failure-mode testing, observability, and runbooks.

------------------------------------------------------------------------

# 96. References

Validate exact command, scripting, topology, and client behavior against
the Redis, Redis Enterprise, and client-library versions deployed.

Recommended official Redis documentation areas:

-   `INCR`
-   `EXPIRE`
-   `PEXPIRE`
-   `TTL`
-   `PTTL`
-   `ZADD`
-   `ZCARD`
-   `ZREMRANGEBYSCORE`
-   `HSET`
-   `HMGET`
-   Redis programmability / Lua
-   Redis Cluster
-   Redis Cluster hash tags
-   Redis latency monitoring
-   Redis memory management
-   Redis eviction policies
-   Redis Enterprise monitoring

Rate limiting is a traffic-control and capacity-protection problem, not
only a Redis scripting exercise. Production policies should be derived
from business requirements and downstream capacity, then tested under
concurrency, burst traffic, Redis failures, retries, and memory
pressure.

------------------------------------------------------------------------

# Next Chapter

**Chapter 26 --- Redis Connection Management, Pooling & Client
Reliability**

Chapter 26 will cover:

-   connection lifecycle
-   connection pooling
-   pool sizing
-   connection reuse
-   connect/read/write timeouts
-   retry behavior
-   TCP/TLS overhead
-   connection storms
-   idle connections
-   health checks
-   DNS/topology changes
-   Redis Enterprise endpoints
-   client-side backpressure
-   failover behavior
-   observability
-   failure injection
-   troubleshooting
-   production runbooks
-   acceptance validation
