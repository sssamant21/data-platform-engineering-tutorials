# Chapter 15 --- Cache Stampede, Thundering Herd & Source Protection

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 2 --- Caching & Application Engineering\
**Level:** Intermediate → Production Cache Reliability Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Stampede reproduction, concurrent-load simulation,
synchronized-expiration analysis, TTL jitter, single-flight loader
locks, ownership-safe release, stale-while-revalidate, refresh-ahead,
source protection, failure injection, recovery storms, load testing,
troubleshooting, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Caching is not production-safe merely because normal requests are fast.

A production design must remain stable when:

``` text
a hot key expires
many keys expire together
the cache is cold
Redis is impaired
the source becomes slow
clients retry
a deployment changes the key namespace
traffic returns after an outage
```

The central engineering question is:

> When Redis cannot immediately satisfy a request, how much work is
> allowed to reach the authoritative source?

Chapter 14 introduced stampede risk while comparing read-through and
write patterns. This chapter makes source protection the primary
subject.

By the end, you should be able to:

-   Explain cache stampede and thundering-herd mechanics.
-   Quantify source amplification.
-   Identify synchronized-expiration risk.
-   Recognize hot-key regeneration risk.
-   Apply TTL jitter correctly.
-   Implement single-flight/request coalescing.
-   Design ownership-safe Redis loader locks.
-   Size lock TTLs against refresh latency.
-   Use bounded waiter behavior.
-   Design refresh-ahead.
-   Use stale-while-revalidate where business semantics permit it.
-   Apply negative caching carefully.
-   Prevent retry amplification.
-   Apply backoff and jitter.
-   Bound source concurrency.
-   Use rate limiting and circuit breaking as source-protection
    controls.
-   Plan cold-cache recovery and cache warming.
-   Prevent recovery storms.
-   Define observability and alerting.
-   Load-test cache-loss scenarios.
-   Troubleshoot and recover from stampede incidents.

------------------------------------------------------------------------

# 2. Core Production Principle

Redis reduces source traffic only while requests are actually absorbed
by the cache.

A design that normally produces:

``` text
20,000 application reads/sec
99% cache hit ratio
~200 source reads/sec
```

may expose the source to thousands of reads per second when the cache
becomes cold.

Therefore:

``` text
cache capacity
```

and:

``` text
source fallback capacity
```

are separate engineering concerns.

The source must be protected even when Redis is healthy but data is
missing.

------------------------------------------------------------------------

# Part 1 --- Stampede Mechanics

## 3. Normal Cache-Aside Path

``` text
Application
   |
   v
Redis
   |
 hit
   |
   v
Return
```

On a miss:

``` text
Application
   |
   v
Redis
   |
 miss
   |
   v
Source
   |
   v
Populate Redis
   |
   v
Return
```

The danger appears when many callers enter the miss path together.

------------------------------------------------------------------------

## 4. Stampede Window

Suppose:

``` text
request rate = 5,000/sec
source latency = 500 ms
```

If a hot key expires, approximately 2,500 requests can arrive during one
500 ms regeneration window.

Without coordination, many may perform identical source work.

------------------------------------------------------------------------

## 5. Source Amplification

Normal:

``` text
1,000 callers
999 cache hits
1 source lookup
```

Stampede:

``` text
1,000 callers
many simultaneous misses
hundreds of source lookups
```

The additional source work is not new business demand.

It is duplicate regeneration work.

------------------------------------------------------------------------

# Part 2 --- Thundering Herd

## 6. Broader Meaning

A thundering herd occurs when many workers become runnable or retry the
same dependency at approximately the same time.

Examples:

``` text
cache expiration
service recovery
lock release
fixed-delay retries
connection restoration
scheduled refresh
batch start
```

A cache stampede is one important thundering-herd pattern.

------------------------------------------------------------------------

# Part 3 --- Synchronized Expiration

## 7. Identical TTL Population

If 100,000 keys are loaded together with:

``` redis
EX 300
```

they may become eligible for expiration in the same time region.

The resulting miss wave can transfer traffic to the source.

------------------------------------------------------------------------

## 8. Why Batch Population Is Risky

Common triggers:

``` text
cache warm job
deployment startup
nightly refresh
bulk import
namespace migration
mass invalidation
```

The write operation may look harmless.

The failure occurs one TTL later.

------------------------------------------------------------------------

# Part 4 --- Hot Keys

## 9. Hot-Key Regeneration

One key can create a stampede even when every other key has
well-distributed TTLs.

Examples:

``` text
global configuration
popular product
homepage payload
tenant metadata
shared reference data
```

------------------------------------------------------------------------

## 10. TTL Jitter Is Not Enough for One Hot Key

Jitter changes *when* the hot key expires.

It does not change how many requests arrive after it expires.

A hot key normally requires request coalescing, stale serving,
refresh-ahead, or another regeneration-control strategy.

------------------------------------------------------------------------

# Part 5 --- TTL Jitter

## 11. Formula

``` text
effective TTL =
base TTL + random jitter
```

Example:

``` text
base = 300 sec
jitter = 0..60 sec
```

------------------------------------------------------------------------

## 12. Design Guidance

Jitter should be large enough to distribute load meaningfully but should
not violate the data's freshness requirement.

Do not blindly add large random TTLs to data with strict expiration
semantics.

------------------------------------------------------------------------

# Part 6 --- Single Flight / Request Coalescing

## 13. Goal

For one missing logical object:

``` text
many callers
      |
      v
one source regeneration
```

Other callers wait, retry the cache, receive bounded stale data, or
follow another controlled policy.

------------------------------------------------------------------------

## 14. Desired Flow

``` text
A -> MISS -> obtains loader lock -> source
B -> MISS -> lock busy -----------+
C -> MISS -> lock busy -----------+--> wait/retry cache
D -> MISS -> lock busy -----------+

A -> populate cache -> release
B/C/D -> cache HIT
```

------------------------------------------------------------------------

# Part 7 --- Loader Lock Design

## 15. Acquisition

Conceptually:

``` redis
SET tutorial:chapter15:lock:item:1001 <unique-token> NX EX 5
```

The lock value identifies the owner.

The TTL provides crash recovery.

------------------------------------------------------------------------

## 16. Ownership-Safe Release

Do not blindly:

``` redis
DEL lock-key
```

A previous owner's lease may have expired and a new owner may now hold
the lock.

Use atomic compare-and-delete.

``` lua
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
```

------------------------------------------------------------------------

## 17. Double Check

After acquiring the lock:

``` text
read cache again
```

Another worker may have populated the key between the original miss and
lock acquisition.

------------------------------------------------------------------------

# Part 8 --- Lock TTL Engineering

## 18. Inputs

Measure:

``` text
source p50 latency
source p95 latency
source p99 latency
serialization time
network time
application pause risk
cache write time
```

------------------------------------------------------------------------

## 19. Too Short

If the lock expires before regeneration completes:

``` text
worker A still loading
lock expires
worker B obtains lock
worker B also loads
```

Duplicate source work returns.

------------------------------------------------------------------------

## 20. Too Long

A very long TTL delays recovery when the owner dies.

Treat the lock as a bounded lease, not permanent ownership.

------------------------------------------------------------------------

# Part 9 --- Waiter Behavior

## 21. Do Not Wait Forever

Waiters require:

``` text
maximum wait time
jittered polling
cancellation/error behavior
stale fallback policy
```

Unbounded waiting converts a source problem into application worker
exhaustion.

------------------------------------------------------------------------

# Part 10 --- Refresh-Ahead

## 22. Concept

Refresh a hot object before hard expiration.

``` text
fresh
 |
refresh threshold reached
 |
one worker refreshes
 |
old value remains available
```

Refresh-ahead reduces the probability that user requests encounter a
fully missing hot key.

------------------------------------------------------------------------

## 23. Candidate Selection

Refresh-ahead is useful when:

``` text
key is predictably hot
source regeneration is expensive
freshness window is known
refresh cost is acceptable
```

Do not continuously refresh cold data merely because it exists.

------------------------------------------------------------------------

# Part 11 --- Stale-While-Revalidate

## 24. Soft and Hard Expiration

``` text
fresh window
     |
soft expiration
     |
bounded stale window
     |
hard expiration
```

During the stale window, callers can receive the previous value while
one worker refreshes it.

------------------------------------------------------------------------

## 25. Business Constraint

Stale serving is a business-data decision, not merely a Redis
optimization.

Do not serve stale values when current state is required for
authorization, safety, financial correctness, or another strict
contract.

------------------------------------------------------------------------

# Part 12 --- Negative Caching

## 26. Repeated Not-Found Requests

A missing entity can itself become a hot key.

A short negative TTL can prevent repeated source lookups.

------------------------------------------------------------------------

## 27. Risk

A long negative TTL can hide a newly created object.

Use shorter TTLs and explicit invalidation where required.

------------------------------------------------------------------------

# Part 13 --- Retry Amplification

## 28. Failure Multiplier

Suppose:

``` text
1,000 failed cache fills
3 immediate retries each
```

The application can generate thousands of additional dependency calls.

Retries are load.

------------------------------------------------------------------------

## 29. Backoff and Jitter

Use:

``` text
bounded attempts
exponential backoff
random jitter
```

Avoid synchronized fixed-delay retry loops.

------------------------------------------------------------------------

# Part 14 --- Source Concurrency Protection

## 30. Per-Key Lock Limitation

Per-key locking prevents duplicate loads for the same key.

It does not protect against:

``` text
100,000 different missing keys
```

------------------------------------------------------------------------

## 31. Global/Per-Service Limits

Consider:

``` text
semaphore
bounded worker pool
rate limiter
queue
bulkhead
admission control
```

Protect source capacity explicitly.

------------------------------------------------------------------------

# Part 15 --- Rate Limiting

## 32. Purpose

Rate limiting answers:

> How much fallback traffic may enter the source during a degraded cache
> state?

Limits can be:

``` text
per service
per tenant
per source
per operation
per priority class
```

------------------------------------------------------------------------

# Part 16 --- Circuit Breakers

## 33. Purpose

When the source is already failing, repeatedly sending regeneration
traffic can worsen recovery.

A circuit breaker can temporarily stop or sharply reduce calls after a
failure threshold.

------------------------------------------------------------------------

## 34. States

Conceptually:

``` text
CLOSED
  |
failure threshold
  v
OPEN
  |
cooldown
  v
HALF-OPEN
  |
probe success/failure
```

Circuit breakers require careful thresholds and observability.

------------------------------------------------------------------------

# Part 17 --- Redis Failure Fallback

## 35. Dangerous Design

``` text
Redis error
   |
   v
unlimited source fallback
```

A Redis incident can become a database incident.

------------------------------------------------------------------------

## 36. Controlled Degradation

Depending on workload semantics:

``` text
bounded source fallback
local cache
bounded stale data
rate limiting
circuit breaking
optional-feature disablement
controlled error
```

------------------------------------------------------------------------

# Part 18 --- Cold Cache

## 37. Causes

``` text
new deployment namespace
cache flush
database recreation
migration
major invalidation
new region
disaster recovery
```

Cold-cache behavior must be capacity-tested.

------------------------------------------------------------------------

# Part 19 --- Cache Warming

## 38. Controlled Warming

Prefer:

``` text
prioritize hottest objects
limit source concurrency
measure source latency
ramp gradually
stop when source degrades
```

Do not warm the entire keyspace at unlimited speed.

------------------------------------------------------------------------

# Part 20 --- Recovery Storm

## 39. Failure Pattern

``` text
Redis/source unavailable
requests accumulate/retry
dependency returns
all callers retry
dependency fails again
```

Recovery traffic can be more dangerous than the original failure.

------------------------------------------------------------------------

## 40. Recovery Controls

Use:

``` text
jitter
rate limits
gradual concurrency ramp
circuit-breaker half-open probes
priority
bounded backlog drain
```

------------------------------------------------------------------------

# Part 21 --- Source Capacity Model

## 41. Required Inputs

``` text
peak application reads/sec
normal cache hit ratio
degraded cache hit ratio
source sustainable reads/sec
source burst capacity
source p95/p99 latency
maximum cache-fill concurrency
retry policy
number of application instances
```

------------------------------------------------------------------------

## 42. Fallback Calculation

Conceptually:

``` text
source QPS =
application QPS × miss ratio
```

At:

``` text
20,000 QPS
1% misses
```

source demand is approximately:

``` text
200 QPS
```

At 50% misses:

``` text
10,000 QPS
```

If sustainable source capacity is 2,000 QPS, unlimited fallback is
unsafe.

------------------------------------------------------------------------

# Part 22 --- Protection Budget

## 43. Define It Explicitly

Example:

``` text
source sustainable = 2,000 QPS
normal direct load = 500 QPS
reserved headroom = 500 QPS
cache-fill budget = 1,000 QPS
```

The exact numbers must come from measurement, not assumption.

------------------------------------------------------------------------

# Part 23 --- Observability Model

## 44. Cache Metrics

``` text
cache_hit_total
cache_miss_total
cache_hit_ratio
cache_refresh_total
cache_refresh_error_total
stale_served_total
negative_cache_hit_total
```

------------------------------------------------------------------------

## 45. Coordination Metrics

``` text
loader_lock_acquired_total
loader_lock_contended_total
loader_wait_seconds
loader_wait_timeout_total
refresh_inflight
```

------------------------------------------------------------------------

## 46. Source Metrics

``` text
source_request_total
source_latency
source_error_total
source_timeout_total
source_inflight
source_rate_limited_total
circuit_breaker_state
```

------------------------------------------------------------------------

# Part 24 --- Alerting

## 47. Useful Correlations

Alerting should detect combinations such as:

``` text
cache hit ratio down
+
source QPS up
+
source latency up
```

or:

``` text
lock contention up
+
refresh latency up
```

Do not alert only on Redis CPU.

------------------------------------------------------------------------

# Part 25 --- Source Amplification Ratio

## 48. Concept

For a defined miss population:

``` text
source regeneration calls / cache misses
```

A hot-key burst with:

``` text
100 misses
100 source calls
```

shows no coalescing.

If:

``` text
100 misses
1 source call
```

single-flight protection is working.

------------------------------------------------------------------------

# Part 26 --- Hands-On Lab --- Reproduce and Prevent a Cache Stampede

## 18. Lab Objectives

You will:

1.  simulate a slow source;
2.  implement naive cache-aside;
3.  generate concurrent requests;
4.  reproduce a hot-key stampede;
5.  implement single-flight locking;
6.  add TTL jitter;
7.  compare source-call counts;
8.  test lock recovery;
9.  implement stale-while-revalidate;
10. inject source slowdown/failure;
11. validate source protection.

## 19. Prerequisites

Required:

-   Redis or Redis Enterprise endpoint;
-   Python 3.9+;
-   `redis-cli`;
-   Python `redis` package.

Install:

``` bash
python -m pip install redis
```

Environment variables:

Linux/macOS:

``` bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=''
```

Windows Command Prompt:

``` cmd
set REDIS_HOST=localhost
set REDIS_PORT=6379
set REDIS_PASSWORD=
```

Windows PowerShell:

``` powershell
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
$env:REDIS_PASSWORD=""
```

Do not commit production credentials into lab files. **Two deployment modes:** The defaults are for an **isolated, local, unauthenticated sandbox only**. For a remote or Enterprise lab endpoint, set `REDIS_TLS=1`, supply a trusted `REDIS_CA`, and provision `REDIS_PASSWORD` via your approved secret mechanism (never directly in a committed file). Where required, set `REDIS_USER`, `REDIS_CLIENT_CERT` and `REDIS_CLIENT_KEY`. The Python examples below reject non-loopback connections unless TLS is enabled. For a remote/staging lab, the CLI wrapper and Python programs in this chapter use the same privately provided `REDISCLI_AUTH` credential (Python also accepts `REDIS_PASSWORD` from an approved secret source). Keep the Bash session open throughout the lab, then unset credentials as part of the final cleanup. The plain `redis-cli` localhost example below is ONLY for a dedicated loopback-only, unauthenticated sandbox.

## 20. Verify Connectivity

Without authentication:

``` bash
redis-cli -h localhost -p 6379 PING
```

Expected:

``` text
PONG
```

Authenticated **nonproduction Redis Software/Enterprise** example (Bash). Use your approved endpoint, port, and trusted Redis database proxy certificate. Avoid credentials on the command line and never turn off TLS verification:

``` bash
export REDIS_HOST="lab-redis.example.test"
export REDIS_PORT="10000"
export REDIS_TLS="1"  # mandatory for non-loopback hosts
export REDIS_CA="/secure/path/proxy_cert.pem"
export REDIS_USER=""  # replace if a named Redis ACL user is required
test -r "$REDIS_CA"
read -r -s -p "Staging database password: " REDISCLI_AUTH
echo
export REDISCLI_AUTH

# Define ONCE in this Bash shell, then use rcli for every command below.
rcli() {
  if [[ "$REDIS_TLS" == "1" ]]; then
    test -r "$REDIS_CA" || return 2
    if [[ -n "$REDIS_USER" ]]; then
      redis-cli --tls --cacert "$REDIS_CA" --user "$REDIS_USER" -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
    else
      redis-cli --tls --cacert "$REDIS_CA" -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
    fi
  elif [[ "$REDIS_HOST" == "localhost" || "$REDIS_HOST" == "127.0.0.1" || "$REDIS_HOST" == "::1" ]]; then
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
  else
    echo "REFUSED: non-loopback Redis connection without TLS" >&2
    return 2
  fi
}
test "$(rcli PING)" = "PONG"
echo "PASS: secure staging Redis connectivity"
```

**Expected:** `PONG` and the PASS message for an authorized staging identity on a reachable, certificate-validated endpoint. The `rcli` function persists only in the current Bash session: **run the later example blocks in that same session**. For a loopback-only test sandbox, explicitly choose `REDIS_TLS=0`, `REDIS_HOST=localhost`, and the appropriate local port before defining the function. A named ACL identity can use `REDIS_USER`; mutual TLS deployments must add approved client `--cert`/`--key` options to this wrapper before using the lab (do not bypass client-certificate requirements). Never substitute `--insecure` or `-a <password>` for troubleshooting convenience; record failures instead. See the [Redis Software CLI guidance](https://redis.io/docs/latest/operate/rs/references/cli-utilities/redis-cli/) and [TLS instructions](https://redis.io/docs/latest/operate/rs/security/encryption/tls/enable-tls/).

## 21. Create the Stampede Lab

Create `chapter15_stampede_lab.py`:

``` python
import json
import os
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import redis

HOST = os.getenv("REDIS_HOST", "localhost")
PORT = int(os.getenv("REDIS_PORT", "6379"))
PASSWORD = os.getenv("REDISCLI_AUTH") or os.getenv("REDIS_PASSWORD") or None
USE_TLS = os.getenv("REDIS_TLS", "0") == "1"
CA_FILE = os.getenv("REDIS_CA")
if HOST not in {"localhost", "127.0.0.1", "::1"} and not USE_TLS:
    raise RuntimeError("Remote lab Redis connections require REDIS_TLS=1")
if USE_TLS and not CA_FILE:
    raise RuntimeError("TLS is enabled: supply trusted REDIS_CA certificate path")
client_options = {
    "host": HOST, "port": PORT, "password": PASSWORD,
    "username": os.getenv("REDIS_USER") or None,
    "decode_responses": True,
    "socket_connect_timeout": 3, "socket_timeout": 3,
}
if USE_TLS:
    client_options.update(ssl=True, ssl_ca_certs=CA_FILE, ssl_cert_reqs="required")
    if os.getenv("REDIS_CLIENT_CERT") and os.getenv("REDIS_CLIENT_KEY"):
        client_options.update(
            ssl_certfile=os.environ["REDIS_CLIENT_CERT"],
            ssl_keyfile=os.environ["REDIS_CLIENT_KEY"],
        )
r = redis.Redis(**client_options)

CACHE_KEY = "tutorial:chapter15:item:1001"
LOCK_KEY = "tutorial:chapter15:lock:item:1001"

SOURCE_LATENCY = 0.30
CACHE_TTL = 5
LOCK_TTL = 5

source_calls = 0
source_counter_lock = threading.Lock()

RELEASE_LOCK = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""

def reset_source_counter():
    global source_calls
    with source_counter_lock:
        source_calls = 0

def source_lookup(item_id):
    global source_calls
    with source_counter_lock:
        source_calls += 1

    time.sleep(SOURCE_LATENCY)
    return {
        "id": item_id,
        "name": "chapter-15-demo",
        "generated_at": time.time(),
    }

def naive_get(item_id):
    value = r.get(CACHE_KEY)
    if value is not None:
        return json.loads(value)

    data = source_lookup(item_id)
    r.set(CACHE_KEY, json.dumps(data), ex=CACHE_TTL)
    return data

def protected_get(item_id):
    value = r.get(CACHE_KEY)
    if value is not None:
        return json.loads(value)

    token = str(uuid.uuid4())
    acquired = r.set(LOCK_KEY, token, nx=True, ex=LOCK_TTL)

    if acquired:
        try:
            # Double-check after obtaining ownership.
            value = r.get(CACHE_KEY)
            if value is not None:
                return json.loads(value)

            data = source_lookup(item_id)
            ttl = CACHE_TTL + random.randint(0, 2)
            r.set(CACHE_KEY, json.dumps(data), ex=ttl)
            return data
        finally:
            r.eval(RELEASE_LOCK, 1, LOCK_KEY, token)

    # Another worker is rebuilding the cache.
    for _ in range(30):
        time.sleep(random.uniform(0.02, 0.08))
        value = r.get(CACHE_KEY)
        if value is not None:
            return json.loads(value)

    raise RuntimeError("Timed out waiting for cache regeneration")

def run_load_test(name, function, workers=50):
    r.delete(CACHE_KEY)
    r.delete(LOCK_KEY)
    reset_source_counter()

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(function, 1001) for _ in range(workers)]
        for future in futures:
            future.result()

    elapsed = time.perf_counter() - start

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)
    print(f"Concurrent requests : {workers}")
    print(f"Source calls        : {source_calls}")
    print(f"Elapsed seconds     : {elapsed:.3f}")
    print(f"Cache exists        : {bool(r.exists(CACHE_KEY))}")
    print(f"Cache TTL           : {r.ttl(CACHE_KEY)}")

if __name__ == "__main__":
    print("Redis ping:", r.ping())

    run_load_test(
        "TEST 1 - NAIVE CACHE-ASIDE",
        naive_get,
        workers=50,
    )

    run_load_test(
        "TEST 2 - SINGLE-FLIGHT PROTECTION",
        protected_get,
        workers=50,
    )
```

## 22. Run the Baseline

``` bash
python chapter15_stampede_lab.py
```

A typical naive result may resemble:

``` text
TEST 1 - NAIVE CACHE-ASIDE
Concurrent requests : 50
Source calls        : 50
```

The exact count varies with scheduling, but many workers can reach the
source during the miss window.

The protected test should be much closer to:

``` text
TEST 2 - SINGLE-FLIGHT PROTECTION
Concurrent requests : 50
Source calls        : 1
```

This is the central acceptance result:

``` text
many callers
+
one cache regeneration
```

## 23. Increase Concurrency

Change:

``` python
workers=50
```

to:

``` python
workers=200
```

Run again.

Compare source calls between naive and protected implementations.

The protected implementation should continue coalescing requests for the
same key.

## 24. Inspect the Hot Key

``` bash
rcli GET tutorial:chapter15:item:1001
rcli TTL tutorial:chapter15:item:1001
rcli PTTL tutorial:chapter15:item:1001
```

Inspect the lock while regeneration is active:

``` bash
rcli GET tutorial:chapter15:lock:item:1001
rcli PTTL tutorial:chapter15:lock:item:1001
```

**Expected observations:** While the synthetic cache entry is present, `GET` returns JSON and `TTL`/`PTTL` report a positive remaining lifetime. The lock may already have expired: a missing `GET` returns nil and `PTTL` returns `-2`. Do not treat the lock's disappearance after completion as failure; investigate only while a lock owner is actively regenerating data.

## 25. Force the Hot-Key Miss

``` bash
rcli DEL tutorial:chapter15:item:1001
```

**Expected:** `DEL` returns integer `1` if the disposable key exists or `0` if it has already expired. This deliberately forces a **cold-cache miss** for a synthetic lab record. Run only in a dedicated, approved test database with no shared clients.

Immediately run the concurrent test again.

This models the critical window immediately after hot-key expiration or
invalidation.

## 26. TTL Jitter Experiment

Create synchronized keys:

``` bash
rcli SET tutorial:chapter15:jitter:1 value EX 60
rcli SET tutorial:chapter15:jitter:2 value EX 60
rcli SET tutorial:chapter15:jitter:3 value EX 60
rcli SET tutorial:chapter15:jitter:4 value EX 60
rcli SET tutorial:chapter15:jitter:5 value EX 60
```

Check:

``` bash
rcli TTL tutorial:chapter15:jitter:1
rcli TTL tutorial:chapter15:jitter:2
rcli TTL tutorial:chapter15:jitter:3
rcli TTL tutorial:chapter15:jitter:4
rcli TTL tutorial:chapter15:jitter:5
```

**Expected:** Each fresh `SET ... EX 60` returns `OK`, and immediately sampled TTLs are positive integers no greater than 60. `TTL=-2` means the key expired (or was absent), not that the TLS endpoint changed. Differences in TTL between calls are normal.

Now distribute expirations:

``` python
import os
import random
import redis

HOST = os.getenv("REDIS_HOST", "localhost")
PORT = int(os.getenv("REDIS_PORT", "6379"))
USE_TLS = os.getenv("REDIS_TLS", "0") == "1"
if HOST not in {"localhost", "127.0.0.1", "::1"} and not USE_TLS:
    raise RuntimeError("Remote lab Redis connections require REDIS_TLS=1")
client_options = {
    "host": HOST, "port": PORT,
    "password": os.getenv("REDISCLI_AUTH") or os.getenv("REDIS_PASSWORD") or None,
    "username": os.getenv("REDIS_USER") or None,
    "decode_responses": True,
}
if USE_TLS:
    if not os.getenv("REDIS_CA"):
        raise RuntimeError("REDIS_CA required for remote/TLS Redis")
    client_options.update(ssl=True, ssl_ca_certs=os.environ["REDIS_CA"], ssl_cert_reqs="required")
r = redis.Redis(**client_options)

for i in range(1, 11):
    ttl = 60 + random.randint(0, 30)
    r.set(f"tutorial:chapter15:jitter:{i}", "value", ex=ttl)
    print(f"tutorial:chapter15:jitter:{i} -> {ttl}s")
```

The resulting TTLs should be spread over a range instead of expiring
together.

------------------------------------------------------------------------

# Part 34 --- Stale-While-Revalidate Lab

## 27. Create `chapter15_stale_cache.py`

``` python
import json
import os
import random
import time
import uuid

import redis

HOST = os.getenv("REDIS_HOST", "localhost")
PORT = int(os.getenv("REDIS_PORT", "6379"))
PASSWORD = os.getenv("REDISCLI_AUTH") or os.getenv("REDIS_PASSWORD") or None
USE_TLS = os.getenv("REDIS_TLS", "0") == "1"
CA_FILE = os.getenv("REDIS_CA")
if HOST not in {"localhost", "127.0.0.1", "::1"} and not USE_TLS:
    raise RuntimeError("Remote lab Redis connections require REDIS_TLS=1")
if USE_TLS and not CA_FILE:
    raise RuntimeError("TLS is enabled: supply trusted REDIS_CA certificate path")
client_options = {
    "host": HOST, "port": PORT, "password": PASSWORD,
    "username": os.getenv("REDIS_USER") or None,
    "decode_responses": True,
    "socket_connect_timeout": 3, "socket_timeout": 3,
}
if USE_TLS:
    client_options.update(ssl=True, ssl_ca_certs=CA_FILE, ssl_cert_reqs="required")
    if os.getenv("REDIS_CLIENT_CERT") and os.getenv("REDIS_CLIENT_KEY"):
        client_options.update(
            ssl_certfile=os.environ["REDIS_CLIENT_CERT"],
            ssl_keyfile=os.environ["REDIS_CLIENT_KEY"],
        )
r = redis.Redis(**client_options)

CACHE_KEY = "tutorial:chapter15:stale:item:1001"
LOCK_KEY = "tutorial:chapter15:stale:lock:item:1001"

SOFT_TTL = 10
HARD_TTL = 30
LOCK_TTL = 5

RELEASE_LOCK = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""

def source_lookup():
    time.sleep(0.5)
    return {
        "id": 1001,
        "value": "source-value",
        "generated_at": time.time(),
    }

def write_cache(data):
    payload = {
        "data": data,
        "fresh_until": time.time() + SOFT_TTL,
    }
    r.set(
        CACHE_KEY,
        json.dumps(payload),
        ex=HARD_TTL + random.randint(0, 5),
    )

def read_cache():
    raw = r.get(CACHE_KEY)
    if raw is None:
        return None, "missing"

    payload = json.loads(raw)

    if time.time() <= payload["fresh_until"]:
        return payload["data"], "fresh"

    return payload["data"], "stale"

def refresh_if_owner():
    token = str(uuid.uuid4())
    acquired = r.set(LOCK_KEY, token, nx=True, ex=LOCK_TTL)

    if not acquired:
        return False

    try:
        data = source_lookup()
        write_cache(data)
        return True
    finally:
        r.eval(RELEASE_LOCK, 1, LOCK_KEY, token)

def get_value():
    data, state = read_cache()

    if state == "fresh":
        print("Serving FRESH value")
        return data

    if state == "stale":
        print("Serving STALE value")
        refreshed = refresh_if_owner()
        if refreshed:
            print("This worker refreshed the cache")
        else:
            print("Another worker is refreshing the cache")
        return data

    print("Cache missing; rebuilding")

    if refresh_if_owner():
        data, _ = read_cache()
        return data

    for _ in range(30):
        time.sleep(0.05)
        data, _ = read_cache()
        if data is not None:
            return data

    raise RuntimeError("Unable to rebuild cache")

if __name__ == "__main__":
    print(get_value())
```

Run:

``` bash
python chapter15_stale_cache.py
```

First run:

``` text
Cache missing; rebuilding
```

Run again immediately:

``` text
Serving FRESH value
```

Wait longer than the 10-second soft TTL but less than the hard TTL and
run again:

``` text
Serving STALE value
This worker refreshed the cache
```

The stale value remains available while refresh is coordinated.

> In a real application, refresh can be dispatched asynchronously so the
> stale-serving request does not wait for source regeneration.

------------------------------------------------------------------------

# Part 40 --- Initial Failure Injection

## 28. Slow Source Test

Temporarily increase:

``` python
time.sleep(0.5)
```

to:

``` python
time.sleep(4)
```

Run concurrent requests.

Observe:

-   regeneration duration;
-   lock TTL;
-   waiter behavior;
-   stale serving;
-   source-call count.

If regeneration can exceed the lock TTL, either choose a safer TTL or
implement a carefully designed lease-extension mechanism.

## 29. Source Failure Test

Temporarily replace:

``` python
def source_lookup():
    time.sleep(0.5)
    raise RuntimeError("simulated source failure")
```

Define the intended production behavior.

Where data semantics permit it, a useful policy may be:

``` text
serve bounded stale value
+
record refresh failure
+
back off before next refresh
```

Do not serve stale data when correctness, authorization, security, or
other business requirements require current data.

## 30. Lock Owner Failure

Create a lock:

``` bash
rcli SET tutorial:chapter15:testlock owner-1 NX EX 5
```

**Expected:** `OK` for an absent key; a nil/null reply indicates that an existing key blocked `NX`. Use a dedicated lab database and do **not** delete a key you do not own to force the example to pass.

Verify:

``` bash
rcli GET tutorial:chapter15:testlock
rcli TTL tutorial:chapter15:testlock
```

**Expected:** `GET` returns `owner-1` while present; `TTL` returns 1–5 seconds when promptly observed. A key may expire before the inspection; in that case `GET` is nil and `TTL` is `-2`. Neither outcome justifies deleting an unrelated lock.

Do not delete it.

After expiration:

``` bash
rcli EXISTS tutorial:chapter15:testlock
```

Expected:

``` text
(integer) 0
```

The TTL prevents a crashed owner from leaving an indefinite lock.

------------------------------------------------------------------------

# Part 41 --- Lab Observability

## 31. Application Metrics

Track metrics such as:

``` text
cache_hits_total
cache_misses_total
cache_hit_ratio
cache_refresh_total
cache_refresh_failures_total
cache_stale_served_total
cache_lock_acquired_total
cache_lock_contention_total
cache_wait_timeout_total
```

## 32. Source Metrics

Track:

``` text
source_requests_total
source_latency
source_errors
source_timeouts
source_concurrency
```

## 33. Redis Metrics

Observe:

-   operation latency;
-   operations/sec;
-   memory utilization;
-   evictions;
-   expirations;
-   client connections;
-   network throughput;
-   CPU utilization;
-   database availability.

The useful incident correlation is often:

``` text
cache misses ↑
source requests ↑
source latency ↑
application latency ↑
```

## 34. Source Amplification

A useful conceptual metric is:

``` text
source lookups / cache misses
```

Without coordination:

``` text
100 misses
100 source lookups
ratio = 1.0
```

With effective single flight:

``` text
100 misses
1 source lookup
ratio = 0.01
```

The exact metric definition can be adapted to the application, but the
objective is to detect redundant source work.

------------------------------------------------------------------------

# Part 42 --- Initial Troubleshooting

## 35. Database/API Load Suddenly Increased

Check, in order:

1.  application cache hit ratio;
2.  cache miss rate;
3.  recent key expiration or invalidation events;
4.  Redis connectivity errors/timeouts;
5.  source QPS and latency;
6.  retry rate;
7.  hot-key traffic;
8.  refresh/lock contention;
9.  source concurrency.

A cache-hit-ratio drop aligned with a source-QPS spike is a strong
signal.

## 36. One Hot Key Overloads the Source

Validate:

``` text
request rate
cache TTL
source latency
lock behavior
```

Preferred pattern:

``` text
single-flight regeneration
+
stale-while-revalidate where safe
```

TTL jitter alone cannot prevent a stampede on one hot key.

## 37. Redis Failure Overloads the Database

Look for:

``` text
Redis error -> unlimited source fallback
```

Replace it with bounded behavior:

``` text
Redis error
   |
   +-- stale/local cache where safe
   +-- source concurrency limit
   +-- rate limiting
   +-- circuit breaker
   +-- controlled degradation
```

## 38. Lock Contention Is High

High contention may indicate:

-   extremely hot key;
-   slow source;
-   expensive regeneration;
-   cache TTL too short;
-   lock TTL too short;
-   failed cache writes;
-   repeated refresh failure.

Check refresh latency before treating lock contention as a Redis
performance problem.

## 39. Multiple Workers Still Reach the Source

Possible causes:

-   lock TTL expires before refresh completes;
-   workers use different lock-key names;
-   lock acquisition result is ignored;
-   lock is deleted without ownership verification;
-   cache is not double-checked after lock acquisition;
-   Redis errors bypass coordination;
-   multiple application layers use inconsistent cache logic.

------------------------------------------------------------------------

# Production Safety

## 40. Avoid Broad Cache Flushes

Do not use these as routine production troubleshooting actions:

``` text
FLUSHDB
FLUSHALL
```

A warm cache can become cold instantly, transferring traffic to the
source.

## 41. Avoid Mass Synchronized Invalidation

Deleting a very large key population at once can produce the same
cold-cache effect.

Use controlled invalidation and staged warming where practical.

## 42. Avoid Synchronized Refresh Schedules

If every worker refreshes at exactly midnight, the refresh system itself
can become a thundering herd.

Use scheduling jitter where appropriate.

## 43. Cold-Cache Testing

A production readiness test should include:

``` text
empty cache
+
representative request concurrency
+
realistic source latency
```

Measure whether the source remains within safe capacity.

------------------------------------------------------------------------

------------------------------------------------------------------------

# Part 43 --- Load-Test Methodology

## 90. Test Profiles

Do not validate stampede protection with only one sequential client.

Test:

``` text
warm-cache steady state
single hot-key expiration
many synchronized expirations
cold cache
slow source
source errors
Redis timeout
application restart
recovery after dependency outage
```

------------------------------------------------------------------------

## 91. Measurements

Capture:

``` text
request throughput
p50/p95/p99 application latency
cache hit ratio
source QPS
source p95/p99 latency
source inflight
lock contention
waiter timeout
errors
stale responses
```

------------------------------------------------------------------------

## 92. Pass Condition

A test does not pass merely because all requests eventually return.

It passes when:

``` text
source remains within sustainable capacity
application behavior follows the defined degradation contract
no uncontrolled retry amplification occurs
recovery is stable
```

------------------------------------------------------------------------

# Failure Injection

## 93. Failure 1 --- Hot-Key Expiration

Delete only the isolated lab key while concurrent callers are active.

Expected:

``` text
one/few controlled regeneration operations
not one source call per caller
```

------------------------------------------------------------------------

## 94. Failure 2 --- Synchronized Expiration

Populate many training keys with the same TTL.

Expected in the unprotected case:

``` text
miss wave
source load spike
```

Repeat with jitter.

Expected:

``` text
expiration spread
lower instantaneous source demand
```

------------------------------------------------------------------------

## 95. Failure 3 --- Slow Source

Increase simulated source latency beyond normal.

Check:

``` text
lock TTL
waiter timeout
source inflight
duplicate regeneration
```

------------------------------------------------------------------------

## 96. Failure 4 --- Lock Owner Crash

Allow the owner to disappear without explicit unlock.

Expected:

``` text
lease expires
future regeneration can proceed
```

------------------------------------------------------------------------

## 97. Failure 5 --- Lock TTL Too Short

Configure a refresh longer than the lock TTL.

Expected:

``` text
second owner can appear
duplicate source work becomes possible
```

This demonstrates why TTL sizing is a measured engineering decision.

------------------------------------------------------------------------

## 98. Failure 6 --- Source Error

Return simulated source failures.

Expected:

``` text
bounded retry
no cache poisoning
circuit/rate controls according to policy
stale value only if permitted
```

------------------------------------------------------------------------

## 99. Failure 7 --- Redis Unavailable

Simulate Redis connectivity failure in an isolated test environment.

Expected:

``` text
no unlimited source fall-through
```

Validate the application's degraded-mode contract.

------------------------------------------------------------------------

## 100. Failure 8 --- Retry Storm

Configure many callers to retry simultaneously.

Observe source amplification.

Repeat with exponential backoff and jitter.

------------------------------------------------------------------------

## 101. Failure 9 --- Cold Cache

Remove only the dedicated training key population.

Generate representative concurrency.

Expected:

``` text
source concurrency remains bounded
```

------------------------------------------------------------------------

## 102. Failure 10 --- Recovery Storm

Restore the simulated dependency after a failure period.

Expected:

``` text
traffic ramps within source capacity
not all waiting work released at once
```

------------------------------------------------------------------------

# Troubleshooting

## 103. Source QPS Suddenly High

Check:

``` text
cache hit ratio
recent invalidation
expired-key behavior
deployment/key namespace
Redis errors
retry volume
hot keys
```

------------------------------------------------------------------------

## 104. Redis Healthy but Database Slow

Do not stop at Redis infrastructure metrics.

Check:

``` text
cache misses
source fallback
loader concurrency
lock contention
source latency
```

Redis can be healthy while application cache behavior overloads the
source.

------------------------------------------------------------------------

## 105. Lock Contention High

Check:

``` text
key request rate
refresh duration
source latency
cache TTL
lock TTL
cache-write success
```

High contention may be evidence of a hot key, not Redis saturation.

------------------------------------------------------------------------

## 106. Multiple Loaders Still Reach Source

Check:

``` text
same lock-key construction
NX result handling
lock TTL
ownership-safe release
double-check after acquisition
Redis error bypass path
```

------------------------------------------------------------------------

## 107. Waiter Timeouts High

Check:

``` text
refresh latency
source health
lock owner health
poll interval
wait timeout
cache population errors
```

------------------------------------------------------------------------

## 108. Source Recovers then Fails Again

Suspect a recovery storm.

Check:

``` text
retry synchronization
backlog
cache warming
concurrency ramp
circuit breaker
rate limiter
```

------------------------------------------------------------------------

# Production Runbooks

## 109. Runbook --- Active Cache Stampede

``` text
1. Confirm cache-hit-ratio drop.
2. Confirm source-QPS increase.
3. Identify hot/missing keys or synchronized-expiration population.
4. Measure source latency and saturation.
5. Reduce uncontrolled retries.
6. Apply source concurrency/rate limits.
7. Serve bounded stale data only where approved.
8. Prevent broad cache invalidation.
9. Warm critical keys gradually.
10. Monitor source recovery.
11. Confirm cache hit ratio recovers.
12. Confirm application latency recovers.
13. Preserve incident metrics.
14. Correct TTL/coalescing design.
```

------------------------------------------------------------------------

## 110. Runbook --- Hot-Key Stampede

``` text
1. Identify the hot key.
2. Measure requests/sec.
3. Measure regeneration duration.
4. Confirm single-flight behavior.
5. Check lock TTL.
6. Check ownership-safe release.
7. Check double-read after acquisition.
8. Enable/repair stale or refresh-ahead policy if approved.
9. Validate source-call count.
10. Validate request latency.
```

------------------------------------------------------------------------

## 111. Runbook --- Cold Cache Recovery

``` text
1. Estimate hot working set.
2. Measure source sustainable capacity.
3. Set cache-fill concurrency budget.
4. Prioritize hottest/critical objects.
5. Warm gradually.
6. Monitor source p95/p99 latency.
7. Pause/rate-reduce if source degrades.
8. Add jittered TTLs.
9. Validate hit-ratio recovery.
10. Confirm no synchronized future expiry was created.
```

------------------------------------------------------------------------

## 112. Runbook --- Redis Failure With Source Fallback

``` text
1. Confirm Redis impairment.
2. Measure fallback source QPS.
3. Activate source protection.
4. Disable unlimited retries.
5. Apply controlled degradation.
6. Use stale/local cache only where approved.
7. Restore Redis connectivity.
8. Ramp normal traffic.
9. Validate source recovers.
10. Validate cache repopulation does not create a new storm.
```

------------------------------------------------------------------------

## 113. Runbook --- Recovery Storm

``` text
1. Confirm dependency has recovered.
2. Keep concurrency bounded.
3. Keep jittered retries enabled.
4. Probe health gradually.
5. Ramp cache fills in stages.
6. Monitor source latency/errors.
7. Stop ramp if saturation returns.
8. Drain waiting work within capacity.
9. Confirm stable steady state.
10. Review recovery thresholds.
```

------------------------------------------------------------------------

# Part 44 --- Capacity Review Template

## 114. Workload Review

``` text
Service:
Cache database:
Source:
Peak application QPS:
Normal hit ratio:
Expected degraded hit ratio:
Source normal QPS:
Source sustainable QPS:
Source burst QPS:
Source p95 latency:
Source p99 latency:
Hot keys:
Base TTL:
TTL jitter:
Soft TTL:
Hard TTL:
Refresh-ahead threshold:
Max loader concurrency:
Rate limit:
Retry attempts:
Backoff:
Circuit-breaker threshold:
Cold-cache warming plan:
Recovery ramp:
Owner:
```

------------------------------------------------------------------------

# Production Acceptance Checklist

## 115. Stampede Protection

-   [ ] Hot keys identified.
-   [ ] Synchronized-expiration risk reviewed.
-   [ ] TTL jitter defined where appropriate.
-   [ ] Single-flight behavior implemented for expensive hot misses.
-   [ ] Loader locks use unique owner tokens.
-   [ ] Lock release validates ownership.
-   [ ] Lock TTL is based on measured refresh latency.
-   [ ] Cache is rechecked after lock acquisition.
-   [ ] Waiter timeout is bounded.
-   [ ] Waiter polling uses jitter.
-   [ ] Refresh-ahead reviewed.
-   [ ] Stale-serving policy documented.
-   [ ] Negative-cache policy documented.
-   [ ] Retry count bounded.
-   [ ] Retry backoff/jitter implemented.
-   [ ] Source concurrency bounded.
-   [ ] Source rate limit documented.
-   [ ] Circuit-breaker behavior reviewed.
-   [ ] Redis-failure fallback bounded.
-   [ ] Cold-cache behavior load tested.
-   [ ] Cache warming rate limited.
-   [ ] Recovery storm tested.
-   [ ] Source-capacity model documented.
-   [ ] Dashboards correlate cache and source behavior.
-   [ ] Incident runbooks available.

------------------------------------------------------------------------

# Knowledge Validation

## 116. Questions

You should be able to answer:

1.  What is a cache stampede?
2.  How is it related to a thundering herd?
3.  Why can Redis remain healthy during a stampede?
4.  How does source amplification occur?
5.  Why are synchronized TTLs dangerous?
6.  What problem does TTL jitter solve?
7.  Why does TTL jitter not fully protect one hot key?
8.  What is single-flight/request coalescing?
9.  Why must a loader lock have an expiration?
10. Why must lock release verify ownership?
11. Why should the cache be checked again after lock acquisition?
12. What happens when lock TTL is shorter than refresh duration?
13. Why must waiter behavior be bounded?
14. What is refresh-ahead?
15. What is stale-while-revalidate?
16. What is the difference between soft and hard TTL?
17. When is stale serving inappropriate?
18. Why use negative caching?
19. How can retries amplify an incident?
20. Why is jitter important for retries?
21. Why is per-key locking insufficient during a fully cold cache?
22. What is a source concurrency budget?
23. How does a circuit breaker protect a failing source?
24. Why can Redis failure overload a database?
25. What is a recovery storm?
26. How should cache warming be rate limited?
27. Which metrics prove single-flight is working?
28. Why should cold-cache behavior be load tested?
29. What determines safe fallback QPS?
30. What conditions must be met before declaring stampede protection
    production-ready?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 117. Lab Completion

-   [ ] Reproduced naive hot-key stampede.
-   [ ] Measured source-call amplification.
-   [ ] Implemented TTL jitter.
-   [ ] Implemented single-flight protection.
-   [ ] Used unique lock owner token.
-   [ ] Used ownership-safe Lua release.
-   [ ] Verified double-check behavior.
-   [ ] Increased concurrent clients.
-   [ ] Tested lock owner expiration.
-   [ ] Tested too-short lock TTL concept.
-   [ ] Implemented stale-while-revalidate lab.
-   [ ] Tested soft expiration.
-   [ ] Tested hard expiration behavior.
-   [ ] Simulated slow source.
-   [ ] Simulated source failure.
-   [ ] Reviewed negative caching.
-   [ ] Reviewed retry backoff/jitter.
-   [ ] Reviewed source concurrency controls.
-   [ ] Reviewed rate limiting.
-   [ ] Reviewed circuit breaking.
-   [ ] Tested cold-cache behavior.
-   [ ] Reviewed recovery-storm behavior.
-   [ ] Completed all failure scenarios.
-   [ ] Reviewed all production runbooks.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 118. Lab Cleanup

Use the same trusted Bash shell and the existing TLS-aware `rcli` function. Begin with a **read-only** scoped inventory; each `SCAN` reply contains a cursor and matching keys, and you must manually iterate the returned cursor until it reaches 0. `COUNT` is only a hint. For Redis Software clustered configurations, review product-specific scan visibility and placement before inferring that one scan covers every shard.

``` bash
rcli SCAN 0 MATCH 'tutorial:chapter15:*' COUNT 100
```

Confirm this is the **dedicated, owner-approved Chapter 15 lab database** and that the following five exact synthetic records are yours. Then delete **only these known keys** and check each key individually:

``` bash
for key in \
  tutorial:chapter15:item:1001 \
  tutorial:chapter15:lock:item:1001 \
  tutorial:chapter15:stale:item:1001 \
  tutorial:chapter15:stale:lock:item:1001 \
  tutorial:chapter15:testlock
do
  rcli UNLINK "$key"
  test "$(rcli EXISTS "$key")" = "0"
done
echo "PASS: five known lab keys are absent"
```

Delete jitter keys only after confirming they belong to this lab. Run cleanup commands through the same `rcli` function on the **approved isolated lab endpoint**, not a new/default localhost connection. Never delete a wildcard pattern without inspecting the returned keys, ownership, and client impact.

**Expected for exact-key cleanup:** `UNLINK` returns 1 for a present key (or 0 for a key that expired); `EXISTS` on each known key returns 0 after cleanup. The return counts may differ if keys already expired.

When all Chapter 15 lab exercises have finished, clear the interactive secret and client connection variables from the Bash environment:

``` bash
unset REDISCLI_AUTH REDIS_PASSWORD
unset -f rcli
```

**Expected:** This removes those shell variables and function from the current session; it does not revoke any independently stored identity, nor establish that every lab artifact was deleted.

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

------------------------------------------------------------------------

# 119. Key Takeaways

1.  A cache stampede is a source-protection failure, not necessarily a
    Redis infrastructure failure.
2.  Synchronized expiration can transfer large request bursts to the
    source.
3.  TTL jitter spreads expiration but does not by itself protect one hot
    key.
4.  Single-flight/request coalescing prevents duplicate regeneration for
    the same object.
5.  Loader locks require unique ownership tokens, bounded TTLs, and
    ownership-safe release.
6.  Refresh latency must drive lock-TTL engineering.
7.  Waiters must have bounded behavior.
8.  Refresh-ahead can prevent predictable hot keys from becoming fully
    missing.
9.  Stale-while-revalidate can protect latency and source capacity when
    bounded staleness is acceptable.
10. Negative caching can absorb repeated requests for missing entities.
11. Retries can multiply load and must use bounds, backoff, and jitter.
12. Per-key locking does not protect against many unique misses.
13. Source concurrency and rate limits must reflect measured source
    capacity.
14. Circuit breakers can reduce pressure on an already failing source.
15. Redis failure must not automatically become unlimited database
    fallback.
16. Cold-cache and recovery behavior must be load tested.
17. Cache warming must be gradual and source-aware.
18. Recovery storms can cause a second outage after the original
    dependency recovers.
19. Cache, application, and source metrics must be correlated.
20. Production acceptance requires proving the source stays within
    capacity during degraded cache conditions.

------------------------------------------------------------------------

# 120. References

Validate commands and behavior against the exact Redis/Redis Enterprise
and client versions deployed.

Recommended official documentation areas:

-   Redis `GET`
-   Redis `SET`
-   `NX`
-   key expiration and TTL
-   `DEL`
-   `UNLINK`
-   Lua scripting / atomic server-side execution
-   Redis client connection behavior
-   Redis Enterprise database availability
-   Redis Enterprise observability
-   Redis persistence and replication
-   caching architecture and invalidation patterns

Single-flight, stale-while-revalidate, refresh-ahead, rate limiting, and
circuit breaking are application architecture patterns. Their exact
implementation depends on the application framework, Redis client,
source system, consistency contract, and failure model.

------------------------------------------------------------------------

# Next Chapter

**Chapter 16 --- Cache Warming, Refresh-Ahead & Cold-Start Engineering**

Chapter 16 will go deeply into:

-   cold-cache mechanics
-   working-set discovery
-   cache preloading
-   demand-driven warming
-   refresh-ahead scheduling
-   hot-key prioritization
-   source-aware warm rates
-   deployment warming
-   failover warming
-   regional recovery
-   TTL distribution
-   warming observability
-   failure injection
-   production runbooks
