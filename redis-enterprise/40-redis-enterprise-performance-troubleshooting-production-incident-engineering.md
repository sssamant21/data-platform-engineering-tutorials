# Chapter 40 --- Redis Enterprise Performance Troubleshooting & Production Incident Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 6 --- Observability, Reliability & Production Operations\
**Level:** Advanced → Production Incident & Performance Engineering\
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators,
Developers, Incident Responders\
**Lab type:** Symptom-first triage, client/server isolation, latency
diagnosis, CPU/memory/eviction incidents, connection saturation,
hot/big-key analysis, shard skew, network pressure,
replication/persistence impact, safe evidence collection, mitigation
drills, failure injection, RCA evidence, troubleshooting runbooks, and
production acceptance

------------------------------------------------------------------------

# 1. Objective

This chapter turns the previous architecture, reliability, and
observability chapters into an incident workflow.

The goal is not:

``` text
run every Redis command you know
```

The goal is:

``` text
confirm impact
    |
    v
identify the failing layer
    |
    v
collect evidence
    |
    v
test hypotheses
    |
    v
apply lowest-risk mitigation
    |
    v
verify recovery
    |
    v
identify root cause
```

By the end, you should be able to investigate:

-   high latency;
-   timeouts;
-   high CPU;
-   memory pressure;
-   eviction storms;
-   connection exhaustion;
-   reconnect storms;
-   hot keys;
-   big keys;
-   shard imbalance;
-   network saturation;
-   replication lag;
-   persistence pressure;
-   client-side bottlenecks;
-   retry amplification;
-   cache-source amplification;
-   failover-related degradation;
-   Active-Active regional issues;
-   monitoring blind spots.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not start with:

``` text
Redis is slow.
```

Start with evidence:

``` text
Which users?
Which service?
Which operation?
Which database?
Which shard/node?
When did it start?
What changed?
What resource changed at the same time?
```

------------------------------------------------------------------------

# Part 1 --- Incident Priorities

## 3. Order

During an incident:

``` text
1. Protect users.
2. Stabilize the system.
3. Preserve evidence.
4. Diagnose root cause.
5. Prevent recurrence.
```

Root-cause investigation should not delay a safe mitigation when user
impact is severe.

------------------------------------------------------------------------

# Part 2 --- First Five Minutes

## 4. Confirm Impact

Record:

``` text
incident start
affected service
affected Redis database
affected environment
error rate
P95/P99 latency
timeout rate
business impact
```

## 5. Check Scope

Determine:

``` text
one client?
one service?
one database?
one shard?
one node?
one region?
all Redis workloads?
```

Scope dramatically reduces the search space.

------------------------------------------------------------------------

# Part 3 --- Build the Timeline

## 6. Correlate

Capture:

``` text
first alert
first user impact
deployment
configuration change
traffic spike
failover
backup
persistence event
node event
network event
```

Do not rely on memory after the incident.

------------------------------------------------------------------------

# Part 4 --- Client vs. Redis

## 7. Critical Split

High application Redis latency can come from:

``` text
application
connection pool
DNS
TLS
network
Redis
retry behavior
```

Before tuning Redis, determine whether requests are actually reaching
Redis slowly.

------------------------------------------------------------------------

# Part 5 --- Latency Decomposition

## 8. Model

``` text
application Redis latency
=
pool wait
+
connect/TLS/DNS if applicable
+
network
+
Redis processing
+
response transfer
+
retry delay
```

Measure as many components as possible.

------------------------------------------------------------------------

# Part 6 --- Application Evidence

## 9. Capture

``` text
Redis operation
P50/P95/P99
timeouts
connection errors
pool wait
retry count
payload size
fallback/source latency
```

Avoid logging raw sensitive keys.

------------------------------------------------------------------------

# Part 7 --- Redis Baseline

## 10. Compare With Normal

Capture:

``` text
ops/sec
CPU
memory
connections
network
evictions/sec
expirations/sec
replication
persistence
per-shard metrics
```

Compare with known normal and peak baselines.

------------------------------------------------------------------------

# Part 8 --- Safe Redis Inspection

## 11. Useful Commands

Depending on permissions/version:

``` redis
INFO
INFO memory
INFO stats
INFO clients
INFO replication
INFO persistence
```

Use Redis Enterprise product metrics as the authoritative operational
view where appropriate.

------------------------------------------------------------------------

# Part 9 --- Avoid Dangerous Diagnostics

## 12. Production Safety

Do not respond to an incident by running:

``` redis
KEYS *
```

on a large production database.

For a separately authorized nonproduction investigation only, a scoped example is:

``` redis
SCAN 0 MATCH 'tutorial:chapter40:*' COUNT 100
```

**Expected:** A cursor and zero or more matching keys. Repeat with the returned cursor until `0`, including empty intermediate batches. `COUNT` is a hint, and a scan is not a consistent snapshot. During real incidents, prefer approved telemetry or bounded sampling; do not launch a full production keyspace scan without impact/ownership review.

Also avoid unbounded diagnostics that materially increase production
load.

------------------------------------------------------------------------

# Part 10 --- High Latency Decision Tree

## 13. Flow

``` text
Application latency high?
        |
        +--> pool wait high? --> client pool/concurrency
        |
        +--> Redis latency high?
        |       |
        |       +--> CPU high? --> workload/hot key/command
        |       +--> memory pressure? --> eviction/OOM
        |       +--> one shard? --> skew/hot key
        |       +--> network high? --> big values/traffic
        |
        +--> Redis latency normal?
                |
                +--> network/DNS/TLS/client/retry
```

------------------------------------------------------------------------

# Part 11 --- High CPU

## 14. Questions

When CPU rises:

``` text
Did ops/sec rise?
Did command mix change?
Did one shard rise?
Did value size rise?
Did a hot key appear?
Did background work begin?
```

CPU is a symptom, not a root cause.

------------------------------------------------------------------------

# Part 12 --- CPU With Higher Traffic

## 15. Capacity

If:

``` text
CPU ↑
ops/sec ↑
latency ↑
```

the workload may have exceeded safe capacity.

Confirm whether traffic growth is legitimate or retry-amplified.

------------------------------------------------------------------------

# Part 13 --- CPU Without Higher Traffic

## 16. Investigate

If:

``` text
CPU ↑
ops/sec flat
```

look for:

``` text
more expensive commands
larger values
hot-key concentration
background operations
changed data structures
```

------------------------------------------------------------------------

# Part 14 --- Single Hot Shard

## 17. Pattern

``` text
database CPU average moderate
one shard CPU near saturation
P99 latency high
```

Likely areas:

``` text
hot key
hash-tag concentration
tenant skew
poor key distribution
```

------------------------------------------------------------------------

# Part 15 --- Hot Key

## 18. Evidence

Use:

``` text
application top-key-family telemetry
per-shard traffic
per-shard CPU
request distribution
```

Do not depend solely on production-wide key scans.

------------------------------------------------------------------------

# Part 16 --- Hot-Key Mitigation

## 19. Options

Depending on semantics:

``` text
local/application cache
request coalescing
refresh-ahead
replicated logical copies
key decomposition
rate limiting
source protection
```

Do not split a key if doing so breaks required atomicity.

------------------------------------------------------------------------

# Part 17 --- Big Key

## 20. Symptoms

``` text
network spikes
tail latency
client CPU
large response time
memory pressure
slow mutation/deletion
```

Use bounded inspection such as:

``` redis
MEMORY USAGE <key>
STRLEN <key>
HLEN <key>
LLEN <key>
SCARD <key>
ZCARD <key>
XLEN <key>
```

according to data type.

------------------------------------------------------------------------

# Part 18 --- Big-Key Mitigation

## 21. Options

``` text
reduce payload
compress where measured beneficial
split object where semantics allow
use hashes for partial field access
paginate/bound collection access
UNLINK large disposable keys where appropriate
```

Do not redesign blindly during an incident.

------------------------------------------------------------------------

# Part 19 --- Memory Pressure

## 22. Evidence

Check:

``` text
used memory
memory limit
headroom
key growth
value growth
TTL coverage
evictions
fragmentation/RSS where relevant
```

------------------------------------------------------------------------

# Part 20 --- Memory Growth

## 23. Questions

``` text
Are keys increasing?
Are values larger?
Did TTL disappear?
Did persistent keys increase?
Did a new namespace appear?
Did traffic/data ingestion change?
```

------------------------------------------------------------------------

# Part 21 --- Eviction Storm

## 24. Pattern

``` text
memory near limit
evictions/sec rises
hit ratio falls
source QPS rises
source latency rises
Redis misses increase
```

This can create a feedback loop.

------------------------------------------------------------------------

# Part 22 --- Eviction Feedback Loop

## 25. Flow

``` text
memory pressure
   |
eviction
   |
cache miss
   |
source request
   |
latency/retry
   |
more pressure
```

Protect the source while addressing Redis memory.

------------------------------------------------------------------------

# Part 23 --- OOM / Write Rejection

## 26. Check

Depending on policy/configuration, memory exhaustion may reject writes
rather than evict.

Capture:

``` text
memory policy
headroom
error text
workload
key/value growth
```

------------------------------------------------------------------------

# Part 24 --- TTL Problems

## 27. Missing TTL

A cache namespace unexpectedly containing persistent keys can cause
steady memory growth.

Sample safely and use application ownership/telemetry to validate TTL
policy.

------------------------------------------------------------------------

# Part 25 --- Expiration Storm

## 28. Pattern

Many keys populated together with identical TTL can expire together.

Symptoms:

``` text
expiration spike
miss spike
source spike
latency spike
```

Mitigations include TTL jitter, refresh-ahead, and source protection.

------------------------------------------------------------------------

# Part 26 --- Connection Exhaustion

## 29. Symptoms

``` text
pool wait
pool timeout
connection errors
high connection count
new-connection spike
```

Determine whether exhaustion is client-side, server-side, or both.

------------------------------------------------------------------------

# Part 27 --- Connection Leak

## 30. Pattern

``` text
connections steadily rise
traffic stable
connections do not return
```

Investigate client lifecycle and connection ownership.

------------------------------------------------------------------------

# Part 28 --- Connection-Per-Request

## 31. Anti-Pattern

Repeatedly creating connections adds:

``` text
TCP
TLS
authentication
socket setup
```

and can cause avoidable latency and server pressure.

Use correctly sized pools.

------------------------------------------------------------------------

# Part 29 --- Pool Too Small

## 32. Pattern

``` text
Redis healthy
pool utilization 100%
pool wait high
application Redis latency high
```

Increase only after validating concurrency and Redis capacity.

------------------------------------------------------------------------

# Part 30 --- Pool Too Large

## 33. Risk

An oversized pool multiplied across:

``` text
pods
workers
services
```

can create excessive server connections.

Calculate fleet-wide connection budget.

------------------------------------------------------------------------

# Part 31 --- Reconnect Storm

## 34. Trigger

Often follows:

``` text
failover
network interruption
certificate rotation
Redis restart
```

Use bounded reconnects with backoff/jitter.

------------------------------------------------------------------------

# Part 32 --- Network Saturation

## 35. Evidence

Check:

``` text
bytes/sec
packet loss
RTT
retransmission where available
large values
cross-zone/region routing
```

Equal ops/sec does not imply equal network load.

------------------------------------------------------------------------

# Part 33 --- Client CPU

## 36. Often Missed

Large payloads, serialization, compression, TLS, and response processing
can saturate application CPU while Redis remains healthy.

Correlate client CPU with Redis call latency.

------------------------------------------------------------------------

# Part 34 --- Serialization Regression

## 37. Pattern

A deployment changes:

``` text
payload schema
serialization format
compression
object size
```

and Redis latency appears to rise.

Measure encoded bytes and client encode/decode time.

------------------------------------------------------------------------

# Part 35 --- Retry Storm

## 38. Pattern

``` text
initial failure
   |
aggressive retries
   |
more Redis traffic
   |
more failure
```

Track retry ratio.

------------------------------------------------------------------------

# Part 36 --- Retry Mitigation

## 39. Use

``` text
bounded attempts
backoff
jitter
deadline awareness
idempotency
circuit breaking where appropriate
```

Do not use infinite retries.

------------------------------------------------------------------------

# Part 37 --- Pipeline Problems

## 40. Oversized Pipeline

A very large pipeline can create:

``` text
buffering
large responses
tail latency
client memory pressure
unfairness
```

Tune batch size by measurement.

------------------------------------------------------------------------

# Part 38 --- No Pipelining

## 41. RTT-Bound Workload

Many tiny sequential commands can be dominated by round trips.

Consider bounded pipelining or appropriate multi-key commands when
semantics allow.

------------------------------------------------------------------------

# Part 39 --- Expensive Command Pattern

## 42. Investigate

Look for workload changes involving:

``` text
large collections
broad scans
large result sets
server-side scripts
heavy transformations
```

Validate exact command behavior before attributing cost.

------------------------------------------------------------------------

# Part 40 --- Lua Script Incident

## 43. Risks

Long/unbounded Lua logic can block useful Redis work.

Check:

``` text
recent script deployment
script execution pattern
input size
loop bounds
hot key
```

Keep production scripts small and bounded.

------------------------------------------------------------------------

# Part 41 --- Transaction Contention

## 44. WATCH Retries

High contention can create repeated optimistic transaction conflicts.

Track application retry counts and hot entities.

Lua or different data modeling may be more appropriate for some atomic
updates.

------------------------------------------------------------------------

# Part 42 --- Distributed Lock Incident

## 45. Symptoms

``` text
lock acquisition latency
lock timeout
retry storm
hot lock key
expired lease
duplicate work
```

Check lease sizing and ownership semantics.

------------------------------------------------------------------------

# Part 43 --- Rate-Limiter Incident

## 46. Hot Limiter

A global rate-limit key can become a hot coordination point.

Check:

``` text
limiter key distribution
request rate
Lua execution
regional behavior
```

------------------------------------------------------------------------

# Part 44 --- Pub/Sub Incident

## 47. Symptoms

``` text
subscriber disconnect
missed events
slow subscriber
large messages
fan-out pressure
```

Remember: plain Pub/Sub is not durable replay.

------------------------------------------------------------------------

# Part 45 --- Streams Incident

## 48. Signals

``` text
stream growth
consumer lag
PEL growth
oldest pending age
retry rate
DLQ rate
consumer health
```

Do not treat every pending entry as failed work.

------------------------------------------------------------------------

# Part 46 --- Stream Backlog

## 49. Capacity

If:

``` text
producer rate > consumer capacity
```

backlog grows.

Estimate:

``` text
net catch-up rate
=
consumer capacity - producer rate
```

when consumer capacity exceeds production.

------------------------------------------------------------------------

# Part 47 --- Replication Lag

## 50. Causes

Check:

``` text
write rate
network
replica CPU
replica memory
full sync
persistence activity
large writes
```

------------------------------------------------------------------------

# Part 48 --- Repeated Full Sync

## 51. Investigate

``` text
replica restart
network instability
backlog too small
peak replication traffic
resource pressure
```

Repeated full sync can itself increase load.

------------------------------------------------------------------------

# Part 49 --- Failover Degradation

## 52. Timeline

Break down:

``` text
failure detection
promotion
routing
client reconnect
application stabilization
```

The Redis promotion time alone is not the application RTO.

------------------------------------------------------------------------

# Part 50 --- Persistence Pressure

## 53. Correlate

When RDB/AOF activity overlaps with high traffic, monitor:

``` text
CPU
memory/COW
storage latency
network
application latency
```

Do not disable durability impulsively during an incident without
understanding RPO impact.

------------------------------------------------------------------------

# Part 51 --- Backup Pressure

## 54. Check

If performance degradation overlaps backup:

``` text
backup start/end
network
storage
CPU
memory
dataset size
```

Use product-specific evidence before concluding causation.

------------------------------------------------------------------------

# Part 52 --- Active-Active Incident

## 55. Geo Diagnosis

Check:

``` text
local Redis health
inter-region network
geo replication delay
catch-up
regional capacity
application routing
```

Remote staleness can be a consistency-model effect rather than local
Redis slowness.

------------------------------------------------------------------------

# Part 53 --- Region Misrouting

## 56. Pattern

A regional application accidentally uses a remote Redis endpoint.

Symptoms:

``` text
higher RTT
higher application Redis latency
local Redis underused
```

Validate endpoint/configuration.

------------------------------------------------------------------------

# Part 54 --- Kubernetes Incident

## 57. Check

``` text
pod restarts
node pressure
CPU throttling
memory limits
network policy
DNS
secret rotation
autoscaling
```

Redis client problems can originate from the application platform.

------------------------------------------------------------------------

# Part 55 --- DNS

## 58. Symptoms

``` text
connection setup slow
intermittent resolution
only new connections affected
existing connections healthy
```

Measure DNS separately.

------------------------------------------------------------------------

# Part 56 --- TLS

## 59. Symptoms

``` text
handshake errors
certificate errors
new connections fail
existing pooled connections survive
```

Check certificate rotation and trust chain.

------------------------------------------------------------------------

# Part 57 --- Authentication

## 60. Distinguish

Authentication failures can look like availability failures to an
application.

Check secret version and rotation timing before blaming Redis
performance.

------------------------------------------------------------------------

# Part 58 --- Monitoring Blind Spot

## 61. Missing Evidence

If Redis metrics disappear during the incident, investigate the
monitoring pipeline independently.

Use:

``` text
application metrics
logs
host telemetry
Redis Enterprise UI/API
```

as alternate evidence where available.

------------------------------------------------------------------------

# Part 59 --- Change Correlation

## 62. Ask

``` text
What changed in the previous 5/15/60 minutes?
```

Check:

``` text
application deploy
Redis config
ACL/certificate
traffic source
data sync
batch job
maintenance
infrastructure
```

------------------------------------------------------------------------

# Part 60 --- Known Workload Windows

## 63. Baseline Separately

If batch/data-sync jobs are known to increase Redis load, establish
separate baselines for:

``` text
steady state
batch window
maintenance window
```

Do not confuse known workload effects with unrelated incidents.

------------------------------------------------------------------------

# Part 61 --- Evidence Collection Template

## 64. Minimum Set

``` text
UTC/local timestamp
application error rate
application Redis P95/P99
timeouts
pool wait
retries
Redis ops/sec
CPU
memory
evictions/sec
connections
network
per-shard metrics
replication
persistence
recent changes
```

------------------------------------------------------------------------

# Part 62 --- Before/After Windows

## 65. Compare

Collect:

``` text
15-30 min before incident
incident window
15-30 min after recovery
```

This supports RCA.

------------------------------------------------------------------------

# Part 63 --- Hypothesis Table

## 66. Use

  -----------------------------------------------------------------------
  Hypothesis        Supporting        Contradicting     Next Test
                    Evidence          Evidence          
  ----------------- ----------------- ----------------- -----------------
  Hot shard         One shard CPU     None yet          Check key
                    high                                distribution

  Pool exhaustion   Pool wait high    Redis CPU normal  Check pool sizing

  Memory pressure   Evictions rising  Memory near limit Check key/value
                                                        growth
  -----------------------------------------------------------------------

Do not lock onto the first plausible explanation.

------------------------------------------------------------------------

# Part 64 --- Mitigation Selection

## 67. Prefer Reversible Actions

Examples:

``` text
reduce abusive workload
rate limit
disable/reduce retries
shift traffic safely
increase source protection
scale supported capacity
roll back recent change
```

Avoid high-risk configuration changes without evidence.

------------------------------------------------------------------------

# Part 65 --- Change One Thing

## 68. During Diagnosis

When possible, make one controlled mitigation at a time and record:

``` text
timestamp
change
expected effect
actual effect
```

This preserves causal evidence.

------------------------------------------------------------------------

# Part 66 --- Scaling

## 69. Not Always the Fix

Adding capacity can help genuine saturation.

It may not fix:

``` text
single hot key
bad client pool
remote-region routing
retry storm
large object
incorrect TTL
```

Scale based on bottleneck evidence.

------------------------------------------------------------------------

# Part 67 --- Restart

## 70. Caution

Restart can temporarily clear symptoms while destroying evidence.

Use only when operationally justified and record evidence first when
possible.

------------------------------------------------------------------------

# Part 68 --- Flush

## 71. Never as Generic Fix

Do not use:

``` redis
FLUSHDB
FLUSHALL
```

as a troubleshooting technique.

Cache clearing can create a source-protection incident.

------------------------------------------------------------------------

# Part 69 --- Forcing Expiration/Deletion

## 72. Caution

Mass deletion can cause:

``` text
CPU
memory churn
source misses
network
latency
```

Use bounded deletion and understand downstream effects.

------------------------------------------------------------------------

# Part 70 --- Recovery Verification

## 73. Do Not Stop at Green

Verify:

``` text
application error rate normal
P99 normal
pool wait normal
Redis resources stable
evictions controlled
source stable
replication healthy
redundancy restored
```

------------------------------------------------------------------------

# Part 71 --- Root Cause

## 74. Separate

Document:

``` text
trigger
root cause
contributing factors
impact
detection gap
mitigation
prevention
```

Avoid attributing root cause solely from correlation.

------------------------------------------------------------------------

# Part 72 --- Blameless RCA

## 75. Focus

Use language centered on:

``` text
system conditions
controls
design assumptions
monitoring gaps
process improvements
```

rather than individual blame.

------------------------------------------------------------------------

# Part 73 --- Corrective Actions

## 76. Categories

``` text
application
Redis configuration
capacity
data model
client behavior
observability
runbook
testing
deployment guardrail
```

Assign owner and due date outside the tutorial workflow.

------------------------------------------------------------------------

# Part 74 --- Hands-On Lab

## 77. Safety

Use a disposable Redis/Redis Enterprise environment.

Do not intentionally create production saturation.

------------------------------------------------------------------------

# Part 75 --- Baseline Generator

## 78. Python

``` python
import os
import time
import redis

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD") or None,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

for i in range(20000):
    key = f"tutorial:chapter40:key:{i % 1000}"
    r.set(key, str(i), ex=300)
    r.get(key)

    if i % 2000 == 0:
        print("operations:", i)
```

Capture baseline telemetry.

------------------------------------------------------------------------

# Part 76 --- Latency Lab

## 79. Percentiles

Measure client P50/P95/P99 before and during each injected condition.

Always compare to baseline.

------------------------------------------------------------------------

# Part 77 --- Pool Exhaustion Lab

## 80. Small Pool

Use a deliberately small `BlockingConnectionPool` with bounded workers.

Observe:

``` text
pool wait
timeouts
application latency
Redis CPU
```

The expected lesson is that client latency can rise while Redis remains
healthy.

------------------------------------------------------------------------

# Part 78 --- Connection Churn Lab

## 81. Bounded

Compare connection reuse with repeatedly constructing/closing clients.

Observe:

``` text
connection rate
latency
CPU
TLS cost if enabled
```

------------------------------------------------------------------------

# Part 79 --- Hot-Key Lab

## 82. Workload

Send most requests to:

``` text
tutorial:chapter40:hot
```

and a minority across many cold keys.

Observe shard/resource skew.

------------------------------------------------------------------------

# Part 80 --- Big-Value Lab

## 83. Controlled

Create bounded values such as:

``` text
1 KB
100 KB
1 MB
```

Measure latency and network effects.

Do not create unbounded large objects.

------------------------------------------------------------------------

# Part 81 --- Memory Pressure Lab

## 84. Disposable Instance

Approach a pre-defined safe lab threshold.

Observe:

``` text
memory
headroom
evictions/OOM
latency
```

Stop before host instability.

------------------------------------------------------------------------

# Part 82 --- Expiration Storm Lab

## 85. Same TTL

Create bounded keys with one identical TTL.

Observe expiration/miss behavior.

Repeat with jitter.

------------------------------------------------------------------------

# Part 83 --- Retry Storm Lab

## 86. Controlled

Inject temporary connection failures.

Compare:

``` text
immediate aggressive retry
vs.
bounded exponential backoff + jitter
```

Measure request amplification.

------------------------------------------------------------------------

# Part 84 --- Network Latency Lab

## 87. Disposable Network

Inject controlled network delay where the platform permits.

Compare:

``` text
Redis processing health
application Redis latency
```

This demonstrates why client latency and server latency must be
separated.

------------------------------------------------------------------------

# Part 85 --- Replication Lag Lab

## 88. HA Environment

Generate write load and temporarily constrain/disconnect a disposable
replica.

Observe lag and recovery.

------------------------------------------------------------------------

# Part 86 --- Failover Lab

## 89. Measure

Record:

``` text
failure time
detection
promotion
client reconnect
application recovery
```

Correlate reconnect traffic.

------------------------------------------------------------------------

# Part 87 --- Persistence Correlation Lab

## 90. Where Supported

Observe Redis/application telemetry during a controlled persistence
operation.

Do not assume impact; measure it.

------------------------------------------------------------------------

# Part 88 --- Shard-Skew Lab

## 91. Clustered Lab

Use key patterns/hash tags that intentionally concentrate traffic, then
compare with distributed keys.

Observe per-shard differences.

------------------------------------------------------------------------

# Part 89 --- Failure Injection

## 92. Failure 1 --- Client Pool Exhaustion

Verify high application latency with healthy Redis server metrics.

## 93. Failure 2 --- Hot Key

Verify traffic/CPU concentration.

## 94. Failure 3 --- Big Value

Verify network and tail-latency increase.

## 95. Failure 4 --- Memory Pressure

Verify headroom and eviction/OOM signals.

## 96. Failure 5 --- Expiration Storm

Verify miss/source amplification.

## 97. Failure 6 --- Retry Storm

Verify request amplification.

## 98. Failure 7 --- Network Delay

Verify server/client latency divergence.

## 99. Failure 8 --- Replication Degradation

Verify lag and redundancy signals.

## 100. Failure 9 --- Failover/Reconnect Storm

Verify application recovery timeline.

## 101. Failure 10 --- Hot Shard

Verify database average hides per-shard saturation.

------------------------------------------------------------------------

# Part 90 --- Troubleshooting Matrix

## 102. Symptoms

  -----------------------------------------------------------------------
  Symptom                 First Checks            Common Areas
  ----------------------- ----------------------- -----------------------
  High P99                Pool, Redis latency,    Hot key, pool, network
                          shard CPU, network      

  High CPU                Ops/sec, command mix,   Traffic, expensive work
                          shard skew              

  Memory growth           Keys, values, TTL       Missing TTL, growth

  Evictions               Memory, hit ratio,      Working-set pressure
                          source                  

  Timeouts                Pool, network, Redis    Saturation/retries
                          P99                     

  Connections high        Deploy, pool, churn     Leak/reconnect

  One shard hot           Distribution, tags      Hot key/skew

  Replication lag         Network, writes,        Capacity/sync
                          replica                 

  Remote staleness        Region/routing          Geo replication

  Redis healthy, app slow Pool/network/client     Client bottleneck
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Part 91 --- Runbook: High Latency

## 103. Procedure

``` text
1. Confirm user impact and time window.
2. Capture application P95/P99 and errors.
3. Check pool wait/timeouts.
4. Compare Redis-side latency.
5. Check ops/sec and command mix.
6. Check per-shard CPU/latency.
7. Check memory/evictions.
8. Check network and value sizes.
9. Correlate recent changes.
10. Apply lowest-risk mitigation and verify.
```

------------------------------------------------------------------------

# Part 92 --- Runbook: High CPU

## 104. Procedure

``` text
1. Confirm affected database/node/shard.
2. Compare ops/sec with baseline.
3. Check one-shard vs all-shard impact.
4. Check hot-key/key-family telemetry.
5. Check value sizes/command mix.
6. Check retries.
7. Check background operations.
8. Reduce avoidable workload.
9. Scale only if saturation is genuine.
10. Verify CPU and P99 recovery.
```

------------------------------------------------------------------------

# Part 93 --- Runbook: Memory / Eviction

## 105. Procedure

``` text
1. Confirm memory/headroom.
2. Measure eviction rate.
3. Check key/value growth.
4. Check TTL coverage.
5. Identify big keys/key families.
6. Check hit ratio/source load.
7. Protect source systems.
8. Apply approved capacity/data fix.
9. Verify eviction/source recovery.
10. Update capacity forecast.
```

------------------------------------------------------------------------

# Part 94 --- Runbook: Connection Exhaustion

## 106. Procedure

``` text
1. Check application pool.
2. Check server connections.
3. Check pool wait/timeouts.
4. Check connection creation rate.
5. Check deployment/autoscaling/failover.
6. Identify leaks or connection-per-request.
7. Add bounded backpressure/reuse.
8. Validate fleet connection budget.
9. Confirm recovery.
10. Add/adjust alerting.
```

------------------------------------------------------------------------

# Part 95 --- Runbook: Hot Key / Hot Shard

## 107. Procedure

``` text
1. Identify hot shard.
2. Compare peers.
3. Identify hot key/key family.
4. Check hash tags/tenant skew.
5. Confirm business semantics.
6. Reduce abusive traffic if necessary.
7. Apply safe caching/coalescing/distribution.
8. Verify shard balance.
9. Verify P99.
10. Update data-model guardrails.
```

------------------------------------------------------------------------

# Part 96 --- Runbook: Replication Lag

## 108. Procedure

``` text
1. Measure lag/freshness.
2. Check write rate.
3. Check network.
4. Check replica CPU/memory.
5. Check full/partial sync.
6. Check persistence overlap.
7. Reduce avoidable pressure.
8. Restore healthy replication.
9. Confirm redundancy.
10. Review RPO/capacity.
```

------------------------------------------------------------------------

# Part 97 --- Runbook: Retry Storm

## 109. Procedure

``` text
1. Confirm original failure.
2. Measure retry ratio.
3. Identify retrying services.
4. Reduce retry attempts.
5. Add/verify backoff and jitter.
6. Enforce deadlines.
7. Protect Redis/source dependencies.
8. Recover underlying dependency.
9. Confirm traffic normalizes.
10. Correct retry policy.
```

------------------------------------------------------------------------

# Part 98 --- Runbook: Failover Degradation

## 110. Procedure

``` text
1. Confirm failover timeline.
2. Confirm new primary/database health.
3. Measure client reconnects.
4. Check connection pool recovery.
5. Check new-primary capacity.
6. Check replication restoration.
7. Check application errors/P99.
8. Stabilize traffic.
9. Restore redundancy.
10. Record application RTO and loss evidence.
```

------------------------------------------------------------------------

# Part 99 --- Runbook: Network / Remote Endpoint

## 111. Procedure

``` text
1. Compare client vs Redis-side latency.
2. Check DNS.
3. Check RTT/packet loss.
4. Check endpoint/region.
5. Check TLS handshake failures.
6. Check bytes/sec/value size.
7. Correct routing/network issue.
8. Verify reconnect.
9. Confirm application P99.
10. Add route/network monitoring.
```

------------------------------------------------------------------------

# Part 100 --- Runbook: Monitoring Blind Spot

## 112. Procedure

``` text
1. Confirm telemetry gap.
2. Identify missing source.
3. Use alternate evidence.
4. Check metrics endpoint/exporter.
5. Check auth/TLS/network.
6. Restore collection.
7. Validate dashboards.
8. Validate alert delivery.
9. Document blind period.
10. Add meta-monitoring.
```

------------------------------------------------------------------------

# Part 101 --- Incident Worksheet

## 113. Header

``` text
Incident:
Date:
Environment:
Redis database:
Services:
Incident commander:
Redis owner:
Start:
Detection:
Mitigation:
Recovery:
```

## 114. Impact

``` text
User impact:
Error rate:
P95:
P99:
Timeout rate:
Business impact:
```

## 115. Redis Evidence

``` text
Ops/sec:
CPU:
Memory:
Evictions/sec:
Expirations/sec:
Connections:
Network:
Hot shard:
Replication:
Persistence:
```

## 116. Client Evidence

``` text
Pool utilization:
Pool wait:
Reconnects:
Retries:
Client CPU:
Payload size:
```

## 117. Change Evidence

``` text
Deployments:
Configuration:
Traffic:
Batch/data sync:
Failover:
Maintenance:
Network:
```

------------------------------------------------------------------------

# Part 102 --- RCA Template

## 118. Fields

``` text
Summary:
Customer/user impact:
Start/end:
Detection:
Trigger:
Root cause:
Contributing factors:
Why safeguards did not prevent it:
Mitigation:
Recovery validation:
Corrective actions:
Monitoring improvements:
Runbook improvements:
```

------------------------------------------------------------------------

# Part 103 --- Performance Baseline Template

## 119. Record

  Signal             Normal   Peak   Incident
  ---------------- -------- ------ ----------
  P50                              
  P95                              
  P99                              
  Ops/sec                          
  CPU                              
  Memory                           
  Evictions/sec                    
  Connections                      
  Network in/out                   
  Retry rate                       

------------------------------------------------------------------------

# Part 104 --- Mitigation Decision Table

## 120. Examples

  Evidence                    Safer First Action
  --------------------------- ------------------------------------
  Retry storm                 Reduce/bound retries
  Pool exhaustion             Fix pool/backpressure
  Hot key                     Coalesce/cache/rate-limit
  Memory pressure             Protect source + capacity/data fix
  Remote routing              Restore local endpoint
  One hot shard               Fix distribution/hot-key pattern
  Genuine global saturation   Scale supported capacity
  Bad deployment              Roll back where safe

------------------------------------------------------------------------

# Part 105 --- Escalation Package

## 121. Vendor/Platform Support

Prepare:

``` text
exact timestamps/time zone
Redis Enterprise version
database/topology
affected endpoints
impact
metrics
logs
recent changes
reproduction
actions already taken
```

Redact secrets.

------------------------------------------------------------------------

# Part 106 --- Production Acceptance Checklist

## 122. Incident Readiness

-   [ ] Application Redis P95/P99 available.
-   [ ] Client pool metrics available.
-   [ ] Retry metrics available.
-   [ ] Database ops/sec available.
-   [ ] CPU/memory/network available.
-   [ ] Per-shard metrics available where supported.
-   [ ] Eviction/expiration rates available.
-   [ ] Replication metrics available.
-   [ ] Persistence metrics available.
-   [ ] Backup health available.
-   [ ] Hot-key/key-family telemetry strategy defined.
-   [ ] Big-key investigation procedure defined.
-   [ ] Connection budget documented.
-   [ ] Memory headroom target documented.
-   [ ] Normal/peak baseline documented.
-   [ ] Change/deployment markers available.
-   [ ] Incident worksheet available.
-   [ ] RCA template available.
-   [ ] High-latency runbook tested.
-   [ ] High-CPU runbook tested.
-   [ ] Memory/eviction runbook tested.
-   [ ] Connection runbook tested.
-   [ ] Hot-key/shard runbook tested.
-   [ ] Replication runbook tested.
-   [ ] Retry-storm runbook tested.
-   [ ] Failover runbook tested.
-   [ ] Network runbook tested.
-   [ ] Monitoring-blind-spot runbook tested.
-   [ ] Failure drills completed.
-   [ ] Escalation package template ready.
-   [ ] Post-recovery validation defined.

------------------------------------------------------------------------

# Knowledge Validation

## 123. Questions

1.  What should be established before saying "Redis is slow"?
2.  Why is incident scope important?
3.  What components make up application Redis latency?
4.  Why can Redis be healthy while application latency is high?
5.  Why should P99 be compared with baseline?
6.  Why can average database CPU hide an incident?
7.  What evidence suggests a hot key?
8.  What evidence suggests a big value?
9.  Why can memory eviction amplify source load?
10. What causes an expiration storm?
11. How does a small client pool cause apparent Redis latency?
12. Why is an oversized pool also dangerous?
13. What causes reconnect storms?
14. Why should network bytes/sec be inspected?
15. How can client CPU cause apparent Redis slowness?
16. What is retry amplification?
17. Why can an oversized pipeline hurt latency?
18. Why can long Lua scripts be dangerous?
19. Which signals indicate a Streams backlog?
20. What can cause replication lag?
21. Why can repeated full sync worsen an incident?
22. Why is application RTO longer than promotion time?
23. Why should persistence impact be measured rather than assumed?
24. How can Active-Active remote staleness differ from local latency?
25. Why should recent changes be placed on the incident timeline?
26. Why should mitigations be reversible where possible?
27. Why does adding capacity not solve every Redis problem?
28. Why should evidence be captured before restart when possible?
29. What should post-recovery validation include?
30. What must exist before a team is production incident-ready?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 124. Lab Completion

-   [ ] Generated baseline workload.
-   [ ] Captured normal P50/P95/P99.
-   [ ] Captured Redis resource baseline.
-   [ ] Tested client pool exhaustion.
-   [ ] Tested connection churn.
-   [ ] Tested hot key.
-   [ ] Tested big value.
-   [ ] Tested memory pressure.
-   [ ] Tested expiration storm.
-   [ ] Compared TTL jitter.
-   [ ] Tested retry storm.
-   [ ] Tested network delay.
-   [ ] Tested replication lag.
-   [ ] Tested failover/reconnect.
-   [ ] Observed persistence correlation.
-   [ ] Tested shard skew.
-   [ ] Completed ten failure scenarios.
-   [ ] Used troubleshooting matrix.
-   [ ] Reviewed ten incident runbooks.
-   [ ] Completed incident worksheet.
-   [ ] Completed RCA template.
-   [ ] Completed baseline table.
-   [ ] Completed mitigation decision table.
-   [ ] Completed escalation package.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 125. Lab Cleanup

Discover only Chapter 40 keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter40:*'
```

Review matches.

Delete confirmed lab keys in bounded batches:

``` redis
UNLINK <confirmed-key>
```

Remove only disposable monitoring rules, network impairment, resource
limits, and test clients created for the lab.

Restore all lab topology and client settings.

Never use:

``` redis
KEYS tutorial:chapter40:*
FLUSHDB
FLUSHALL
```

against a shared or production database.

------------------------------------------------------------------------

# 126. Key Takeaways

1.  Start Redis incidents with user impact, scope, time, and evidence.
2.  Application Redis latency includes much more than Redis execution
    time.
3.  Client pool wait, DNS, TLS, network, and retries can mimic Redis
    slowness.
4.  P95/P99 are essential for tail-latency incidents.
5.  High CPU is a symptom; correlate it with traffic, commands, values,
    and shard distribution.
6.  Cluster averages can hide one saturated shard.
7.  Hot keys and big keys create different failure modes and require
    different fixes.
8.  Memory pressure can trigger eviction and source-amplification
    feedback loops.
9.  Missing TTLs and synchronized TTLs are common cache reliability
    risks.
10. Connection pools can be both too small and too large.
11. Reconnect storms often appear after failover or network events.
12. Network throughput matters as much as command count for large-value
    workloads.
13. Client serialization and CPU can cause apparent Redis latency.
14. Aggressive retries can turn a small failure into a larger outage.
15. Pipeline size must be bounded and measured.
16. Long server-side scripts and high-contention coordination can create
    latency.
17. Streams incidents require lag, PEL, retry, and DLQ evidence.
18. Replication lag should be correlated with network, write rate, sync,
    and replica capacity.
19. Failover analysis must include client reconnect and application
    stabilization.
20. Persistence and backup correlation should be measured rather than
    assumed.
21. Active-Active incidents require regional routing and geo-replication
    evidence.
22. Recent changes belong on every incident timeline.
23. Prefer low-risk, reversible mitigations.
24. Verify full application recovery before closing the incident.
25. A strong RCA separates trigger, root cause, contributing factors,
    detection gaps, mitigation, and prevention.

------------------------------------------------------------------------

# 127. References

Validate diagnostic commands, Redis Enterprise metrics, product
behavior, and operational procedures against the exact versions
deployed.

Recommended official documentation areas:

-   Redis Enterprise monitoring
-   Redis Enterprise metrics
-   Redis Enterprise troubleshooting
-   Redis latency monitoring
-   Redis `INFO`
-   Redis memory optimization
-   Redis key eviction
-   Redis pipelining
-   Redis replication
-   Redis persistence
-   Redis ACL/TLS troubleshooting
-   Redis Enterprise Active-Active monitoring
-   Redis Enterprise support diagnostics
-   Redis client connection management
-   Prometheus/Grafana incident monitoring
-   SRE incident response and postmortem practices

------------------------------------------------------------------------

# Next Chapter

**Chapter 41 --- Redis Enterprise Capacity Planning, Scaling & Resource
Engineering**

Chapter 41 will cover:

-   workload characterization
-   memory sizing
-   CPU sizing
-   network sizing
-   connection budgets
-   shard count
-   shard placement
-   dataset growth
-   headroom
-   replication overhead
-   persistence overhead
-   failover capacity
-   Active-Active capacity
-   vertical vs. horizontal scaling
-   scale triggers
-   forecasting
-   load testing
-   capacity failure injection
-   troubleshooting
-   production runbooks
-   acceptance validation
