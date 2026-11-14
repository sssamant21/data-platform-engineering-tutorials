# Chapter 70 --- Redis Enterprise Command Complexity, SLOWLOG & Latency Forensics

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 12 --- Advanced Operations, FinOps & Resilience\
**Level:** Advanced → Command-Level Performance & Incident Forensics\
**Audience:** SREs, DBREs, Redis Administrators, Platform Engineers,
Application Engineers, Performance Engineers\
**Lab type:** Command complexity, SLOWLOG, commandstats, latency
separation, CPU/event-loop pressure, big-key correlation, blocking
operations, Lua/functions, network/client diagnosis, controlled
reproduction, troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Redis is fast when operations are bounded and the workload matches the
data model.

A latency incident often starts with:

``` text
Redis is slow
```

That statement is too broad.

Observed application latency can include:

``` text
client pool wait
DNS
TCP/TLS
network
proxy
Redis queue/execution
serialization
application processing
```

Inside Redis, command cost depends on:

``` text
command complexity
key size/cardinality
result size
CPU
concurrency
scripts/functions
background activity
```

By the end of this chapter, you should be able to:

-   separate client, network, proxy, and server latency;
-   understand command complexity;
-   use `SLOWLOG` safely;
-   interpret `INFO commandstats`;
-   use latency evidence appropriate to the deployed version;
-   correlate slow commands with big keys;
-   identify large-result and blocking patterns;
-   analyze Lua/server-side logic;
-   investigate CPU/event-loop pressure;
-   detect command mix regressions;
-   reproduce latency safely;
-   build production command guardrails;
-   execute incident runbooks and acceptance gates.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not start by increasing timeouts.

First determine:

``` text
where the time is spent
```

Then fix the responsible layer.

------------------------------------------------------------------------

# Part 1 --- End-to-End Latency

## 3. Path

``` text
application
  |
client pool
  |
DNS/TCP/TLS
  |
network
  |
Redis Enterprise endpoint/proxy
  |
Redis shard
  |
command execution
  |
response path
```

------------------------------------------------------------------------

# Part 2 --- Application Latency

## 4. Measure

Application telemetry should include:

``` text
request latency
Redis call latency
pool wait
timeouts
retries
errors
```

------------------------------------------------------------------------

# Part 3 --- Client Pool Wait

## 5. Hidden Latency

A request can spend 200 ms waiting for a connection and 1 ms executing
in Redis.

Without pool metrics:

``` text
Redis call = 201 ms
```

may be misdiagnosed as server slowness.

------------------------------------------------------------------------

# Part 4 --- DNS

## 6. Diagnose

Intermittent connection setup latency may originate from:

``` text
DNS lookup
resolver failure
cache expiry
```

Separate connection establishment from command execution.

------------------------------------------------------------------------

# Part 5 --- TCP / TLS

## 7. Handshake

New connections require network setup and, when enabled, TLS
negotiation.

Connection reuse is important.

------------------------------------------------------------------------

# Part 6 --- Network RTT

## 8. Baseline

Measure normal network round-trip time between application and Redis
endpoint.

A 1 ms server command cannot produce a 50 ms end-to-end result if the
network path itself adds substantial latency.

------------------------------------------------------------------------

# Part 7 --- Redis Enterprise Proxy / Endpoint

## 9. Layer

Redis Enterprise can introduce routing/proxy components depending on
architecture.

Include endpoint/proxy health in the path analysis.

------------------------------------------------------------------------

# Part 8 --- Server Execution

## 10. Evidence

Use server-side metrics such as:

``` text
SLOWLOG
commandstats
CPU
latency metrics/events
database throughput
```

according to supported version/tooling.

------------------------------------------------------------------------

# Part 9 --- Command Complexity

## 11. Big-O

Redis documentation describes command complexity using notation such as:

``` text
O(1)
O(N)
O(log N)
O(N + M)
```

Complexity describes scaling behavior, not guaranteed wall-clock
latency.

------------------------------------------------------------------------

# Part 10 --- O(1) Does Not Mean Free

## 12. Important

An operation described as O(1) can still be expensive when:

``` text
value is huge
network payload is huge
serialization is expensive
CPU is saturated
```

------------------------------------------------------------------------

# Part 11 --- O(N)

## 13. Risk

For commands whose work grows with collection/keyspace size:

``` text
N = 10
```

may be trivial.

``` text
N = 10,000,000
```

may be dangerous.

------------------------------------------------------------------------

# Part 12 --- Complexity Review

## 14. Production

For high-volume application commands, document:

``` text
command
complexity
expected N
maximum N
result size
frequency
```

------------------------------------------------------------------------

# Part 13 --- Command Guardrail

## 15. Example

``` text
bounded collection size
bounded page size
bounded batch size
bounded result count
```

Application architecture should keep expensive operations bounded.

------------------------------------------------------------------------

# Part 14 --- SLOWLOG

## 16. Purpose

Redis SLOWLOG records commands whose server execution exceeds the
configured threshold.

It focuses on server-side execution time, not full client round-trip
time.

------------------------------------------------------------------------

# Part 15 --- SLOWLOG GET

## 17. Lab

``` bash
redis-cli SLOWLOG GET 20
```

Use the authenticated/TLS form required by your environment.

------------------------------------------------------------------------

# Part 16 --- SLOWLOG LEN

## 18. Check

``` bash
redis-cli SLOWLOG LEN
```

------------------------------------------------------------------------

# Part 17 --- SLOWLOG RESET

## 19. Caution

``` bash
redis-cli SLOWLOG RESET
```

destroys diagnostic history.

Do not reset production SLOWLOG during an incident unless evidence has
been captured and the action is approved.

------------------------------------------------------------------------

# Part 18 --- SLOWLOG Entry

## 20. Interpret

A SLOWLOG entry can contain concepts such as:

``` text
entry ID
timestamp
execution duration
command/arguments
client information
```

Exact format varies by Redis version.

------------------------------------------------------------------------

# Part 19 --- Execution Duration

## 21. Important

SLOWLOG duration generally represents time spent executing the command
on the Redis server.

It does not directly include:

``` text
client pool wait
network RTT
response transfer
application deserialization
```

------------------------------------------------------------------------

# Part 20 --- SLOWLOG Threshold

## 22. Configuration

Threshold configuration should balance:

``` text
signal
volume
overhead
```

Use Redis Enterprise-supported configuration procedures.

Do not change low-level settings blindly.

------------------------------------------------------------------------

# Part 21 --- Threshold Too High

## 23. Problem

If threshold is:

``` text
100 ms
```

but application SLO is:

``` text
P99 < 20 ms
```

SLOWLOG may miss commands relevant to the SLO.

------------------------------------------------------------------------

# Part 22 --- Threshold Too Low

## 24. Problem

An extremely low threshold can create excessive entries/noise.

Qualify in nonproduction.

------------------------------------------------------------------------

# Part 23 --- SLOWLOG Retention

## 25. Ring Buffer

SLOWLOG has bounded retention.

During a high-volume event, useful entries can roll out.

Capture evidence promptly.

------------------------------------------------------------------------

# Part 24 --- Commandstats

## 26. INFO

``` bash
redis-cli INFO commandstats
```

Common concepts include per-command:

``` text
calls
usec
usec_per_call
rejected_calls
failed_calls
```

depending on version.

------------------------------------------------------------------------

# Part 25 --- Commandstats Is Cumulative

## 27. Important

Counters may be cumulative since process/stat reset.

For incident analysis use deltas:

``` text
snapshot T1
snapshot T2
difference
```

------------------------------------------------------------------------

# Part 26 --- Calls Delta

## 28. Calculate

``` text
calls/sec
=
(calls_T2 - calls_T1) / interval
```

------------------------------------------------------------------------

# Part 27 --- CPU-Time Delta

## 29. Concept

For each command:

``` text
server command time/sec
=
(usec_T2 - usec_T1) / interval
```

This helps identify commands consuming significant server execution
time.

------------------------------------------------------------------------

# Part 28 --- Average Is Not Tail

## 30. Caution

`usec_per_call` is an average.

A command can have:

``` text
average = 100 us
P99 = 20 ms
```

Use SLOWLOG/latency distributions/APM for tail behavior.

------------------------------------------------------------------------

# Part 29 --- Command Mix

## 31. Baseline

Record normal:

``` text
GET %
SET %
MGET %
HGET %
HSET %
Z* %
SCAN %
EVAL %
Search %
```

as appropriate.

A command mix change can explain a latency regression.

------------------------------------------------------------------------

# Part 30 --- Command Mix Regression

## 32. Example

Before deployment:

``` text
95% GET
5% SET
```

After:

``` text
70% GET
10% SET
20% expensive collection/query operations
```

CPU may rise even at similar total ops/sec.

------------------------------------------------------------------------

# Part 31 --- CPU Saturation

## 33. Correlate

Look for:

``` text
CPU high
P99 high
SLOWLOG entries
command time increase
throughput plateau
```

------------------------------------------------------------------------

# Part 32 --- Event-Loop / Execution Serialization

## 34. Concept

Redis command processing has execution paths where long-running work can
delay other commands.

Do not interpret high aggregate throughput as proof that no command is
blocking latency-sensitive work.

------------------------------------------------------------------------

# Part 33 --- Long Command Effect

## 35. Example

``` text
fast GET
fast GET
very expensive command
fast GET waits
fast GET waits
```

One expensive operation can create tail latency for unrelated requests
on the affected execution path.

------------------------------------------------------------------------

# Part 34 --- Big Key Correlation

## 36. Investigate

For slow commands involving a specific key:

``` bash
redis-cli TYPE <key>
redis-cli MEMORY USAGE <key>
```

Then use type-specific cardinality commands.

------------------------------------------------------------------------

# Part 35 --- Hash

## 37. Example

``` bash
redis-cli HLEN <key>
```

Large field count can make some operations expensive.

------------------------------------------------------------------------

# Part 36 --- List

## 38. Example

``` bash
redis-cli LLEN <key>
```

Avoid unbounded range retrieval.

------------------------------------------------------------------------

# Part 37 --- Set

## 39. Example

``` bash
redis-cli SCARD <key>
```

Large set operations can be costly.

------------------------------------------------------------------------

# Part 38 --- Sorted Set

## 40. Example

``` bash
redis-cli ZCARD <key>
```

Bound range/result size.

------------------------------------------------------------------------

# Part 39 --- Stream

## 41. Example

``` bash
redis-cli XLEN <key>
```

Review trimming/retention and consumer behavior.

------------------------------------------------------------------------

# Part 40 --- Large Result Sets

## 42. Two Costs

A command may be fast to locate data but expensive to:

``` text
construct response
send response
deserialize response
```

End-to-end latency can therefore exceed SLOWLOG duration.

------------------------------------------------------------------------

# Part 41 --- MGET

## 43. Bounded Batching

`MGET` can reduce network round trips but an enormous batch can create:

``` text
large response
network burst
client memory pressure
```

Benchmark batch size.

------------------------------------------------------------------------

# Part 42 --- HMGET / Multi-Field Reads

## 44. Same Principle

Batching is useful until response size becomes excessive.

Bound it.

------------------------------------------------------------------------

# Part 43 --- LRANGE

## 45. Risk

Avoid requesting an entire huge list when the application needs a page.

Use bounded ranges.

------------------------------------------------------------------------

# Part 44 --- SMEMBERS

## 46. Risk

Returning all members of a huge set can produce large
server/network/client cost.

Design bounded alternatives when needed.

------------------------------------------------------------------------

# Part 45 --- HGETALL

## 47. Risk

For very large hashes:

``` text
HGETALL
```

can produce large results.

Retrieve only needed fields where practical.

------------------------------------------------------------------------

# Part 46 --- ZRANGE

## 48. Bound

Use bounded ranges.

Review options and complexity for the deployed Redis version.

------------------------------------------------------------------------

# Part 47 --- SCAN

## 49. Incremental

`SCAN` is preferable to blocking keyspace enumeration, but it is not
free.

A full scan over millions of keys still consumes work.

Throttle operational scans.

------------------------------------------------------------------------

# Part 48 --- KEYS

## 50. Production Guardrail

Avoid:

``` bash
KEYS *
```

on large production databases.

Use `SCAN` or supported management tooling.

------------------------------------------------------------------------

# Part 49 --- Collection Iteration

## 51. HSCAN / SSCAN / ZSCAN

Incremental iteration helps bound each call.

Still monitor cumulative workload.

------------------------------------------------------------------------

# Part 50 --- Delete Large Key

## 52. DEL

Synchronous deletion can be expensive for large complex structures.

Where supported and appropriate:

``` bash
UNLINK <key>
```

can reduce synchronous deletion work.

------------------------------------------------------------------------

# Part 51 --- Expiration Work

## 53. Correlate

Large expiration waves can contribute to CPU/latency.

Review TTL distribution.

------------------------------------------------------------------------

# Part 52 --- Lua / EVAL

## 54. Risk

Lua scripts execute server-side.

A long-running script can delay other operations.

------------------------------------------------------------------------

# Part 53 --- Script Complexity

## 55. Review

Document:

``` text
keys accessed
loops
collection cardinality
maximum runtime
result size
```

------------------------------------------------------------------------

# Part 54 --- Script Safety

## 56. Guardrail

Do not allow arbitrary unreviewed production scripts.

Treat server-side logic as production code.

------------------------------------------------------------------------

# Part 55 --- Redis Functions

## 57. Same Principle

Where Redis Functions are supported/used, apply:

``` text
code review
bounded work
testing
observability
version control
```

------------------------------------------------------------------------

# Part 56 --- Transactions

## 58. MULTI/EXEC

A large transaction can create a burst of queued operations.

Keep transaction scope bounded.

------------------------------------------------------------------------

# Part 57 --- WATCH Retry

## 59. Contention

High contention can cause optimistic transaction retries.

Application latency may rise even if each Redis command is fast.

------------------------------------------------------------------------

# Part 58 --- Blocking Commands

## 60. Intentional Blocking

Some commands intentionally wait for data/events.

Do not classify expected blocking time as server slowness without
understanding semantics.

------------------------------------------------------------------------

# Part 59 --- Blocking Connection Design

## 61. Separate

Use appropriate dedicated connections for blocking workloads rather than
starving general request pools.

------------------------------------------------------------------------

# Part 60 --- Pub/Sub

## 62. Slow Subscribers

A slow subscriber can create output-buffer/network concerns.

Review client buffer behavior and consumer health.

------------------------------------------------------------------------

# Part 61 --- Streams

## 63. Consumer Lag

Streams latency can arise from:

``` text
consumer lag
pending entries
application processing
```

not only Redis command execution.

------------------------------------------------------------------------

# Part 62 --- Search

## 64. Query Cost

Redis Search latency depends on:

``` text
query selectivity
filters
sorting
aggregation
result count
index size
```

Use Chapter 56/58 principles.

------------------------------------------------------------------------

# Part 63 --- Vector Search

## 65. Query Cost

Vector latency depends on:

``` text
index type
dimension
K
filters
search effort
concurrency
```

Do not diagnose vector queries from generic GET/SET assumptions.

------------------------------------------------------------------------

# Part 64 --- Pipelining

## 66. Benefit

Pipelining reduces network round trips.

But excessive pipeline depth can create:

``` text
server burst
large response
client memory
tail latency
```

Benchmark.

------------------------------------------------------------------------

# Part 65 --- Pipeline Depth

## 67. Test

Compare:

``` text
1
10
50
100
500
```

or workload-appropriate depths in nonproduction.

Find the throughput/latency knee.

------------------------------------------------------------------------

# Part 66 --- Batch Size

## 68. Same Tradeoff

Larger batch:

``` text
fewer RTTs
```

but:

``` text
larger burst
larger response
more queueing
```

------------------------------------------------------------------------

# Part 67 --- Retry Storm

## 69. Incident Amplifier

Latency causes timeout.

Timeout causes retry.

Retry increases load.

Load increases latency.

``` text
latency -> retry -> load -> more latency
```

Use bounded retries/backoff/jitter.

------------------------------------------------------------------------

# Part 68 --- Timeout Tuning

## 70. Principle

Timeout should reflect:

``` text
normal P99
network
request budget
failure detection goal
```

Increasing timeout does not fix expensive commands.

------------------------------------------------------------------------

# Part 69 --- Client Serialization

## 71. Separate

Large JSON/protobuf/etc. encoding/decoding can dominate
application-observed Redis latency.

Measure client-side CPU.

------------------------------------------------------------------------

# Part 70 --- Compression

## 72. Tradeoff

Compression can reduce:

``` text
network bytes
memory
```

while increasing:

``` text
client CPU
latency
```

Benchmark end-to-end.

------------------------------------------------------------------------

# Part 71 --- Network Packet Loss

## 73. Symptom

Server SLOWLOG may be clean while client P99 is high.

Check:

``` text
packet loss
retransmission
RTT
```

------------------------------------------------------------------------

# Part 72 --- Cross-Region Clients

## 74. Geography

If application and Redis are in different regions, network RTT may
dominate command latency.

Prefer locality when architecture allows.

------------------------------------------------------------------------

# Part 73 --- TLS CPU

## 75. Connection Churn

Frequent new TLS connections can increase CPU/latency.

Reuse connections.

------------------------------------------------------------------------

# Part 74 --- Proxy Saturation

## 76. Redis Enterprise

If endpoint/proxy resources are constrained, application latency can
rise even when shard command execution is healthy.

Monitor product-specific proxy metrics.

------------------------------------------------------------------------

# Part 75 --- Shard Skew

## 77. Hot Shard

A database can have:

``` text
average CPU healthy
one shard saturated
```

because of hot keys or uneven workload.

Inspect per-node/per-shard evidence where available.

------------------------------------------------------------------------

# Part 76 --- Hot Key

## 78. Correlate

A single heavily accessed key can concentrate command execution.

Use Chapter 18 techniques.

------------------------------------------------------------------------

# Part 77 --- Hot Tenant

## 79. Multi-Tenant

One tenant may dominate:

``` text
ops/sec
CPU
large queries
```

while platform averages appear acceptable.

Tag application telemetry by tenant where appropriate.

------------------------------------------------------------------------

# Part 78 --- Background Work

## 80. Correlate

Latency can coincide with:

``` text
persistence
backup
defrag
rebalancing
recovery
migration
```

Build a timeline.

------------------------------------------------------------------------

# Part 79 --- Latency Monitoring

## 81. Redis Tools

Redis provides latency diagnostic features in supported versions.

Use exact commands/settings documented for the deployed Redis Enterprise
version.

Examples in open-source Redis documentation may include latency
monitoring commands, but product configuration/support must be validated
before enabling/changing them.

------------------------------------------------------------------------

# Part 80 --- Latency Event Correlation

## 82. Goal

Correlate:

``` text
application P99
Redis latency event
SLOWLOG
CPU
commandstats
background event
```

------------------------------------------------------------------------

# Part 81 --- Latency Percentiles

## 83. Always Prefer Distribution

Track:

``` text
P50
P95
P99
P99.9
```

when available.

Average latency hides tail incidents.

------------------------------------------------------------------------

# Part 82 --- Throughput vs Latency

## 84. Saturation Curve

As load increases:

``` text
throughput rises
latency stable
```

then near saturation:

``` text
latency rises sharply
throughput plateaus
```

Find the knee before production.

------------------------------------------------------------------------

# Part 83 --- Queueing

## 85. Concept

Near saturation, small additional load can create disproportionate
latency.

Maintain headroom.

------------------------------------------------------------------------

# Part 84 --- Baseline Command Profile

## 86. Record

For normal production:

``` text
commands/sec
top commands by calls
top commands by server time
SLOWLOG rate
CPU
P99
```

------------------------------------------------------------------------

# Part 85 --- Delta Analysis

## 87. Incident

Compare:

``` text
healthy window
vs
slow window
```

Look for:

``` text
new command
call-rate increase
time-per-call increase
big-key growth
CPU change
```

------------------------------------------------------------------------

# Part 86 --- Command Cost Ranking

## 88. Useful

Rank commands by:

``` text
delta total server microseconds
```

not only call count.

A rare expensive command may matter more than millions of cheap GETs.

------------------------------------------------------------------------

# Part 87 --- Per-Call Regression

## 89. Useful

If:

``` text
HGETALL average time
```

increases 20x while call count stays constant, investigate key
growth/cardinality.

------------------------------------------------------------------------

# Part 88 --- Call-Rate Regression

## 90. Useful

If per-call cost is stable but calls increase 10x:

``` text
application traffic/retry/change
```

is likely.

------------------------------------------------------------------------

# Part 89 --- Result-Size Regression

## 91. Useful

Server execution may remain similar while network/application latency
rises because result payload became larger.

Measure bytes.

------------------------------------------------------------------------

# Part 90 --- Safe Reproduction

## 92. Nonproduction

Reproduce:

``` text
same command
same key cardinality
same value size
same concurrency
same pipeline
```

without copying sensitive production data.

------------------------------------------------------------------------

# Part 91 --- Synthetic Data

## 93. Namespace

Use:

``` text
tutorial:chapter70:*
```

in isolated lab.

------------------------------------------------------------------------

# Part 92 --- Lab 1: SLOWLOG

## 94. Exercise

1.  inspect current SLOWLOG settings through supported configuration;
2.  create bounded test workload;
3.  capture `SLOWLOG GET`;
4.  identify command/duration;
5.  correlate with client latency.

Do not lower thresholds on shared production just for the tutorial.

------------------------------------------------------------------------

# Part 93 --- Lab 2: Commandstats Delta

## 95. Exercise

Capture:

``` bash
redis-cli INFO commandstats
```

at T1.

Run a known workload.

Capture again at T2.

Calculate call/time deltas.

------------------------------------------------------------------------

# Part 94 --- Lab 3: Big Hash

## 96. Exercise

In a **dedicated, owner-approved nonproduction lab database** with a confirmed client identity, create a small synthetic hash and set its expiration using an authenticated, certificate-validated Redis CLI session. These are **Redis commands**, not commands to paste into a host shell:

``` redis
HSET tutorial:chapter70:hash f1 one f2 two f3 three
EXPIRE tutorial:chapter70:hash 300
HGET tutorial:chapter70:hash f1
HGETALL tutorial:chapter70:hash
```

**Expected for a previously absent key:** `HSET` returns `3` newly added fields, `EXPIRE` returns `1`, `HGET` returns `one`, and `HGETALL` returns all three field/value pairs in an unspecified order. Repeat runs can cause `HSET` to return `0`. This tiny sample only verifies command semantics; it **does not** demonstrate a meaningful large-hash performance difference. A real cardinality experiment requires a separately approved size/memory/latency budget and cleanup.

After measurement, remove only the exact synthetic lab key if you own it:

``` redis
UNLINK tutorial:chapter70:hash
```

**Expected:** `1` if it existed or `0` if it already expired. Never benchmark `HGETALL` against an unknown production-sized hash merely because this example succeeded.

------------------------------------------------------------------------

# Part 95 --- Lab 4: Large List Range

## 97. Exercise

Create bounded list.

Compare:

``` text
LRANGE 0 9
LRANGE 0 999
larger bounded range
```

Measure server and client latency.

------------------------------------------------------------------------

# Part 96 --- Lab 5: Batch Size

## 98. Exercise

Compare **bounded batch sizes of 10, 100, and 1,000 keys** only after a workload owner approves the maximum response size and client/Redis memory budget. These are *counts of key arguments*, not Redis commands: `MGET 10` would read the one key literally named `10`, not ten keys.

First verify the syntax with three synthetic keys in a dedicated isolated lab. For Redis Cluster compatibility, all example keys use the same hash tag (`{lab70}`):

``` redis
SET tutorial:chapter70:{lab70}:k1 one EX 300
SET tutorial:chapter70:{lab70}:k2 two EX 300
SET tutorial:chapter70:{lab70}:k3 three EX 300
MGET tutorial:chapter70:{lab70}:k1 tutorial:chapter70:{lab70}:k2 tutorial:chapter70:{lab70}:k3
```

**Expected:** Each `SET` returns `OK`; `MGET` returns `one`, `two`, `three` **in the requested key order**. Missing or expired keys can return nil; actual Redis CLI line formatting depends on the protocol/client. `MGET` requires explicit key names (`MGET key [key ...]`) and cost grows with the number and sizes of returned values.

For subsequent 10/100/1,000-key tests, prepare separately owner-approved synthetic data and supply an explicit list of those keys, while recording payload bytes, client P99, network and server resource usage. Do not run these larger variations against a shared endpoint.

Cleanup only the three known synthetic keys after the smoke test:

``` redis
UNLINK tutorial:chapter70:{lab70}:k1 tutorial:chapter70:{lab70}:k2 tutorial:chapter70:{lab70}:k3
```

**Expected:** An integer from 0 to 3, depending on how many keys still existed. Do not assume that a successful `MGET` qualifies a database for production-scale batching.

------------------------------------------------------------------------

# Part 97 --- Lab 6: Pipeline

## 99. Exercise

Compare pipeline depths.

Record:

``` text
throughput
P50
P95
P99
```

------------------------------------------------------------------------

# Part 98 --- Lab 7: Lua

## 100. Exercise

Use a harmless bounded script.

Compare constant work with a script whose loop size grows.

Observe server latency.

Do not create intentionally runaway scripts on shared Redis.

------------------------------------------------------------------------

# Part 99 --- Lab 8: Network Delay

## 101. Exercise

In an approved isolated environment, inject bounded network latency
between client and Redis.

Observe:

``` text
client P99 rises
SLOWLOG may remain unchanged
```

This proves layer separation.

------------------------------------------------------------------------

# Part 100 --- Lab 9: Pool Saturation

## 102. Exercise

Use a test client with deliberately small pool.

Increase concurrency.

Measure:

``` text
pool wait
Redis execution
end-to-end latency
```

------------------------------------------------------------------------

# Part 101 --- Lab 10: Retry Amplification

## 103. Exercise

In nonproduction, create bounded latency and compare:

``` text
no retry
immediate retry
backoff+jitter
```

Observe request amplification.

------------------------------------------------------------------------

# Part 102 --- Failure Scenario 1: Big HGETALL

## 104. Test

Grow a disposable hash and issue `HGETALL`.

Validate big-key correlation and bounded alternative.

------------------------------------------------------------------------

# Part 103 --- Failure Scenario 2: Huge MGET

## 105. Test

Request a large bounded batch.

Measure server, network, and client effects.

------------------------------------------------------------------------

# Part 104 --- Failure Scenario 3: KEYS-Like Keyspace Mistake

## 106. Tabletop/Lab

Do not run `KEYS *` on shared production.

Demonstrate safer `SCAN` behavior in isolated lab.

------------------------------------------------------------------------

# Part 105 --- Failure Scenario 4: Long Lua

## 107. Test

Use a safe bounded script that becomes measurably slower.

Observe SLOWLOG/latency.

------------------------------------------------------------------------

# Part 106 --- Failure Scenario 5: Pool Exhaustion

## 108. Test

Small client pool + high concurrency.

Verify pool wait dominates end-to-end latency.

------------------------------------------------------------------------

# Part 107 --- Failure Scenario 6: Network Latency

## 109. Test

Inject bounded network delay.

Verify server execution remains healthy while client P99 rises.

------------------------------------------------------------------------

# Part 108 --- Failure Scenario 7: Retry Storm

## 110. Test

Compare immediate retries with backoff/jitter.

Measure load amplification.

------------------------------------------------------------------------

# Part 109 --- Failure Scenario 8: Hot Key / Hot Shard

## 111. Test

Concentrate bounded lab traffic on one key.

Observe skew and latency.

------------------------------------------------------------------------

# Part 110 --- Failure Scenario 9: Background Activity

## 112. Test/Tabletop

Correlate a supported background operation with latency metrics in
nonproduction.

Separate correlation from causation.

------------------------------------------------------------------------

# Part 111 --- Failure Scenario 10: Command Mix Regression

## 113. Test

Change workload from mostly simple operations to a higher proportion of
expensive bounded collection operations.

Compare:

``` text
ops/sec
CPU
P99
commandstats
```

------------------------------------------------------------------------

# Part 112 --- Troubleshooting Matrix

## 114. Common Problems

  Symptom                           Investigate
  --------------------------------- -------------------------------------
  app latency high, SLOWLOG clean   pool/network/TLS/proxy/result size
  SLOWLOG has one key repeatedly    big/hot key
  CPU high, ops/sec unchanged       command mix/per-call cost
  calls jump after timeout          retry storm
  HGETALL slows over time           hash cardinality growth
  server time low, response slow    network/result/client serialization
  only one shard hot                hot key/skew
  latency during backup/rebalance   background work/capacity
  blocking consumers consume pool   connection design
  average healthy, P99 bad          tail commands/queueing/network

------------------------------------------------------------------------

# Part 113 --- Runbook 1: Redis Latency Incident

## 115. Procedure

``` text
1. capture application P50/P95/P99.
2. inspect pool wait/timeouts/retries.
3. inspect network RTT/loss.
4. inspect Redis CPU/throughput.
5. capture SLOWLOG.
6. capture commandstats deltas.
7. correlate keys/commands/background work.
8. mitigate root cause and validate P99.
```

------------------------------------------------------------------------

# Part 114 --- Runbook 2: SLOWLOG Investigation

## 116. Procedure

``` text
1. capture entries before rollover/reset.
2. rank by command/duration.
3. identify repeated keys/patterns.
4. inspect key type/cardinality/size.
5. compare command complexity.
6. identify application owner.
7. reproduce safely.
8. implement bounded operation.
```

------------------------------------------------------------------------

# Part 115 --- Runbook 3: CPU Saturation

## 117. Procedure

``` text
1. confirm CPU saturation scope.
2. capture commandstats deltas.
3. rank commands by total server time.
4. inspect call-rate/per-call changes.
5. inspect hot keys/shards.
6. inspect scripts/search/background work.
7. reduce expensive/amplified workload.
8. validate capacity/headroom.
```

------------------------------------------------------------------------

# Part 116 --- Runbook 4: Client Latency but Server Healthy

## 118. Procedure

``` text
1. confirm SLOWLOG/server P99 healthy.
2. inspect pool wait.
3. inspect DNS/connect/TLS.
4. inspect network RTT/loss.
5. inspect proxy/endpoint.
6. inspect response size.
7. inspect client serialization/CPU.
8. remediate client/path issue.
```

------------------------------------------------------------------------

# Part 117 --- Runbook 5: Big-Key Command

## 119. Procedure

``` text
1. identify key.
2. identify type/cardinality/memory.
3. identify command complexity/result size.
4. stop uncontrolled growth.
5. replace whole-collection operation with bounded access.
6. trim/split key if appropriate.
7. add size guardrail.
8. monitor regression.
```

------------------------------------------------------------------------

# Part 118 --- Runbook 6: Retry Storm

## 120. Procedure

``` text
1. confirm timeout/retry increase.
2. identify original latency trigger.
3. cap retries.
4. add backoff/jitter.
5. protect Redis/source systems.
6. restore latency.
7. validate request amplification removed.
8. update client policy.
```

------------------------------------------------------------------------

# Part 119 --- Runbook 7: Lua / Function Latency

## 121. Procedure

``` text
1. identify script/function.
2. capture runtime/frequency.
3. inspect loops/key cardinality.
4. identify owner/version.
5. disable/mitigate unsafe path if approved.
6. rewrite bounded logic.
7. load-test.
8. deploy with regression guardrail.
```

------------------------------------------------------------------------

# Part 120 --- Runbook 8: Command Mix Regression

## 122. Procedure

``` text
1. compare healthy/slow commandstats.
2. identify new/increased commands.
3. compare total server time.
4. correlate deployment/feature.
5. inspect key/result sizes.
6. rollback/limit workload if needed.
7. redesign/optimize.
8. update performance regression tests.
```

------------------------------------------------------------------------

# Part 121 --- Latency Forensics Template

## 123. Record

``` text
Incident:
Time:
Application P50/P95/P99:
Pool wait:
Timeouts:
Retries:
Network RTT/loss:
Redis CPU:
Ops/sec:
SLOWLOG:
Top commands by calls:
Top commands by server time:
Hot key/shard:
Background activity:
Recent change:
```

------------------------------------------------------------------------

# Part 122 --- Command Review Template

## 124. Record

``` text
Command:
Application:
Frequency:
Complexity:
Expected N:
Maximum N:
P50/P95/P99:
Result bytes:
Key cardinality:
Retry-safe?:
Guardrail:
Owner:
```

------------------------------------------------------------------------

# Part 123 --- Performance Baseline Template

## 125. Record

``` text
Workload:
Ops/sec:
Command mix:
Pipeline:
Connections:
Value size:
P50:
P95:
P99:
CPU:
Network:
SLOWLOG rate:
Top command time:
```

------------------------------------------------------------------------

# Part 124 --- Production Acceptance

## 126. Application / Client

-   [ ] Redis call latency instrumented;
-   [ ] pool wait instrumented;
-   [ ] timeouts monitored;
-   [ ] retries monitored;
-   [ ] bounded retry/backoff/jitter configured;
-   [ ] connection reuse implemented.

## 127. Redis

-   [ ] SLOWLOG operational procedure documented;
-   [ ] commandstats baselined;
-   [ ] CPU monitored;
-   [ ] per-shard/node evidence available where supported;
-   [ ] latency distributions monitored;
-   [ ] background operations correlated.

## 128. Data / Commands

-   [ ] high-volume commands inventoried;
-   [ ] complexity reviewed;
-   [ ] collection/result sizes bounded;
-   [ ] big-key guardrails implemented;
-   [ ] scripts/functions reviewed;
-   [ ] pipeline/batch sizes benchmarked;
-   [ ] hot-key detection available.

## 129. Incident Readiness

-   [ ] client-vs-server isolation procedure tested;
-   [ ] SLOWLOG runbook tested;
-   [ ] CPU runbook tested;
-   [ ] retry-storm runbook tested;
-   [ ] big-key runbook tested;
-   [ ] ten failure scenarios completed;
-   [ ] eight runbooks reviewed;
-   [ ] production acceptance completed.

------------------------------------------------------------------------

# 130. Knowledge Validation

1.  Why should Redis latency be separated into client, network, proxy,
    and server layers?
2.  How can pool wait be mistaken for Redis server latency?
3.  Why does network RTT matter even for fast commands?
4.  What does command Big-O complexity describe?
5.  Why does O(1) not guarantee low wall-clock latency?
6.  Why must O(N) commands be bounded?
7.  What does SLOWLOG measure?
8.  What important latency components does SLOWLOG not directly measure?
9.  Why should SLOWLOG not be reset casually during an incident?
10. Why should SLOWLOG threshold align with the application's SLO?
11. What does `INFO commandstats` provide?
12. Why should commandstats be analyzed as deltas?
13. Why is average `usec_per_call` insufficient for tail latency?
14. What is a command-mix regression?
15. How can one expensive command affect unrelated requests?
16. Why should slow commands be correlated with key cardinality?
17. Why can large results cause high client latency even when SLOWLOG is
    clean?
18. Why should `KEYS *` be avoided in large production keyspaces?
19. Why can long Lua/server-side logic be dangerous?
20. Why should blocking workloads use appropriate connection design?
21. What is the pipeline-depth tradeoff?
22. How does a retry storm form?
23. Why does increasing timeout not fix command complexity?
24. How can serialization/compression affect observed latency?
25. Why can one shard be saturated while cluster average CPU looks
    healthy?
26. Why should background work be included in the incident timeline?
27. Why are P95/P99 more useful than averages for latency incidents?
28. What is the saturation knee?
29. Why should commands be ranked by total server time as well as call
    count?
30. What must pass before Redis command-latency engineering is
    production-ready?

------------------------------------------------------------------------

# 131. Hands-On Acceptance Checklist

-   [ ] Mapped end-to-end Redis request path.
-   [ ] Instrumented pool wait in test client.
-   [ ] Measured network RTT.
-   [ ] Captured SLOWLOG.
-   [ ] Captured commandstats at T1/T2.
-   [ ] Calculated call deltas.
-   [ ] Calculated command-time deltas.
-   [ ] Built normal command-mix baseline.
-   [ ] Tested bounded big hash.
-   [ ] Compared HGET and HGETALL behavior.
-   [ ] Tested bounded LRANGE sizes.
-   [ ] Tested MGET batch sizes.
-   [ ] Tested pipeline depths.
-   [ ] Tested bounded Lua script.
-   [ ] Tested network-delay separation.
-   [ ] Tested client pool saturation.
-   [ ] Tested retry amplification.
-   [ ] Tested hot-key workload.
-   [ ] Correlated background operation.
-   [ ] Tested command-mix regression.
-   [ ] Built latency forensics template.
-   [ ] Built command review template.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed eight runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 132. Cleanup

Remove only disposable Chapter 70 lab keys.

For:

``` text
tutorial:chapter70:*
```

use safe:

``` text
SCAN
+
UNLINK
```

in controlled batches.

Do not use:

``` text
FLUSHDB
FLUSHALL
```

on shared environments.

Restore:

``` text
temporary network-delay rules
temporary test client settings
temporary SLOWLOG/latency configuration changes if any
temporary load generators
```

Do not reset production diagnostic history merely as tutorial cleanup.

Confirm:

``` text
no test load remains
normal connection count restored
normal latency restored
no temporary fault injection remains
```

------------------------------------------------------------------------

# 133. Key Takeaways

1.  Application-observed Redis latency includes more than Redis command
    execution.
2.  Pool wait, DNS, TCP/TLS, network, proxy, server execution, response
    transfer, and serialization should be separated.
3.  Command complexity describes scaling behavior, not guaranteed
    wall-clock time.
4.  Even O(1) commands can be expensive with huge values or saturated
    resources.
5.  O(N) and collection operations require explicit bounds.
6.  SLOWLOG is server-execution evidence, not end-to-end latency.
7.  SLOWLOG history should be preserved during incidents.
8.  Commandstats is most useful when compared as time-window deltas.
9.  Average command time does not reveal tail latency.
10. Command-mix changes can create latency even when total ops/sec stays
    constant.
11. One expensive operation can delay otherwise fast requests.
12. Slow commands should be correlated with key size/cardinality.
13. Large response payloads can create network/client latency that
    SLOWLOG does not show.
14. Incremental scans are safer than blocking keyspace enumeration.
15. Lua/functions should be treated as reviewed production code with
    bounded work.
16. Blocking commands require intentional client connection design.
17. Pipelining and batching trade round trips for burst size and
    queueing.
18. Retries can transform a small latency event into an overload
    incident.
19. Increasing timeout masks symptoms unless the actual latency source
    is addressed.
20. Cross-region/network problems can raise client P99 while server
    execution remains healthy.
21. Proxy or hot-shard saturation can be hidden by cluster averages.
22. Background persistence, backup, defrag, rebalance, and recovery
    belong in the incident timeline.
23. Tail percentiles and saturation curves are essential performance
    evidence.
24. Ranking commands by total server time can expose expensive
    low-frequency operations.
25. Production readiness requires client telemetry, SLOWLOG/commandstats
    baselines, bounded command/data patterns, safe retries, key-size
    controls, reproducible tests, and practiced runbooks.

------------------------------------------------------------------------

# 134. References

Validate SLOWLOG behavior, configuration fields, commandstats fields,
latency-monitoring features, command complexity, scripting/function
behavior, Redis Enterprise proxy metrics, and supported diagnostic
procedures against the exact deployed Redis/Redis Enterprise version and
current official Redis documentation.

Recommended documentation areas:

-   Redis command reference and complexity
-   Redis `SLOWLOG`
-   Redis `INFO commandstats`
-   Redis latency monitoring
-   Redis latency diagnosis
-   Redis pipelining
-   Redis transactions
-   Redis Lua scripting / Functions
-   Redis `SCAN`
-   Redis `UNLINK`
-   Redis client handling
-   Redis Enterprise observability
-   Redis Enterprise performance
-   Redis Enterprise proxy/network architecture
-   Redis Search performance
-   Redis vector search performance
-   client-library connection pooling and timeout documentation

------------------------------------------------------------------------

# Next Chapter

**Chapter 71 --- Redis Enterprise Proxy, Endpoint & Network Path
Troubleshooting Engineering**

Chapter 71 will focus on the path between applications and Redis
Enterprise: endpoint architecture, proxy routing, DNS, TCP, TLS, load
balancers, Kubernetes Services/EndpointSlices, NetworkPolicy,
firewalls/security groups, NAT/conntrack, MTU, packet loss, connection
resets, cross-zone/cross-region latency, packet captures where approved,
layer-by-layer troubleshooting, failure injection, runbooks, and
production acceptance.
