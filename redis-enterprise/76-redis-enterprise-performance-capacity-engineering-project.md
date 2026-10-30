# Chapter 76 --- Redis Enterprise Performance & Capacity Engineering Project

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 13 --- Production Projects & Final Acceptance\
**Level:** Advanced → Production Performance & Capacity Engineering
Project\
**Audience:** SREs, DBREs, Redis Administrators, Platform Engineers,
Performance Engineers, Application Engineers, Capacity Engineers\
**Lab type:** End-to-end workload characterization, performance
baselining, latency and throughput analysis, command profiling, memory
engineering, hot-key detection, shard/node analysis, network and
persistence qualification, load testing, saturation testing, N-1
testing, capacity forecasting, scaling thresholds, regression gates,
runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Redis is often described as fast.

That statement is not a production performance specification.

A production Redis Enterprise platform must answer:

``` text
How fast?
At what workload?
At what concurrency?
With what value size?
With what command mix?
At what utilization?
With what replication?
During what failure?
With what growth?
```

Performance engineering establishes the operating envelope.

Capacity engineering ensures the platform remains inside that envelope
as workload changes.

This project integrates concepts from:

``` text
memory forensics
command complexity
latency forensics
network troubleshooting
shard placement
benchmarking
HA/failover
FinOps
```

into a single production qualification process.

By the end, you should be able to:

-   define a representative Redis workload;
-   measure operations/sec and bandwidth;
-   establish latency distributions;
-   distinguish client, network, proxy, and Redis latency;
-   analyze command mix and complexity;
-   identify hot keys and hot shards;
-   analyze memory and fragmentation;
-   identify connection pressure;
-   measure node and shard resource utilization;
-   determine saturation knees;
-   test concurrency and pipelining;
-   test large values and expensive commands;
-   test persistence/background activity;
-   test N-1/failure-state capacity;
-   forecast growth;
-   define scaling thresholds;
-   create performance regression gates;
-   build a capacity model;
-   produce a production qualification report.

------------------------------------------------------------------------

# 2. Core Production Principle

Do not size Redis from average utilization.

Size it from:

``` text
representative peak workload
+
failure-state workload
+
growth
+
operational headroom
```

------------------------------------------------------------------------

# Part 1 --- Project Deliverables

## 3. Required Outputs

The project should produce:

``` text
workload profile
baseline report
latency profile
throughput profile
resource profile
memory profile
hot-key/shard analysis
saturation curve
N-1 test
capacity model
growth forecast
scaling thresholds
regression gates
runbooks
acceptance result
```

------------------------------------------------------------------------

# Part 2 --- Scope

## 4. Define

Record:

``` text
environment
cluster
database
application
owners
test window
traffic source
SLO
```

------------------------------------------------------------------------

# Part 3 --- Production Safety

## 5. Rule

Do not perform uncontrolled saturation testing in production.

Use:

``` text
representative nonproduction
isolated benchmark environment
controlled approved production test
```

depending on organizational policy.

------------------------------------------------------------------------

# Part 4 --- Workload Characterization

## 6. First Step

Before benchmarking, understand the real workload.

Record:

``` text
GET %
SET %
MGET %
hash %
set %
sorted set %
Streams %
JSON %
Search %
Vector %
Lua/functions %
transactions %
```

------------------------------------------------------------------------

# Part 5 --- Operations per Second

## 7. Measure

Capture:

``` text
average ops/sec
P95 ops/sec
peak ops/sec
burst ops/sec
```

Do not use only daily average.

------------------------------------------------------------------------

# Part 6 --- Read/Write Ratio

## 8. Example

``` text
90% read
10% write
```

behaves differently from:

``` text
20% read
80% write
```

especially with persistence and replication.

------------------------------------------------------------------------

# Part 7 --- Key Count

## 9. Record

``` text
current keys
growth/day
expiration/day
deletion/day
```

------------------------------------------------------------------------

# Part 8 --- Value Size

## 10. Distribution

Measure:

``` text
P50
P95
P99
max
```

for representative value sizes.

------------------------------------------------------------------------

# Part 9 --- Key Size

## 11. Important

Averages can hide large outliers.

Use safe sampling and:

``` text
MEMORY USAGE <key>
```

where appropriate.

------------------------------------------------------------------------

# Part 10 --- Data Structure Cardinality

## 12. Measure

For collections:

``` text
hash fields
set members
sorted-set members
list length
stream length
```

Large cardinality affects command cost.

------------------------------------------------------------------------

# Part 11 --- TTL Profile

## 13. Record

``` text
no TTL %
short TTL
medium TTL
long TTL
expiration bursts
```

------------------------------------------------------------------------

# Part 12 --- Connection Profile

## 14. Record

``` text
steady connections
peak connections
new connections/sec
TLS handshakes
pool size
```

------------------------------------------------------------------------

# Part 13 --- Client Concurrency

## 15. Measure

``` text
threads
workers
pods
connections per pod
in-flight requests
```

------------------------------------------------------------------------

# Part 14 --- Traffic Pattern

## 16. Classify

``` text
steady
diurnal
bursty
batch-driven
event-driven
cron-driven
```

------------------------------------------------------------------------

# Part 15 --- Batch Jobs

## 17. Important

Document known:

``` text
ETL
data sync
cache warming
reporting
rebuild
```

that changes Redis load.

------------------------------------------------------------------------

# Part 16 --- Workload Profile Template

## 18. Record

``` text
Application:
Database:
Peak ops/sec:
Read/write ratio:
Command mix:
P50 value:
P95 value:
P99 value:
Max value:
Key count:
Growth/day:
TTL profile:
Connections:
Concurrency:
Batch jobs:
```

------------------------------------------------------------------------

# Part 17 --- SLO

## 19. Define

Examples:

``` text
P95 latency
P99 latency
error rate
availability
```

Performance testing needs pass/fail criteria.

------------------------------------------------------------------------

# Part 18 --- Client-Side Latency

## 20. Measure

Application-observed latency includes:

``` text
pool wait
DNS
connect
TLS
network
proxy
Redis execution
response transfer
client processing
```

------------------------------------------------------------------------

# Part 19 --- Redis Command Execution

## 21. Distinguish

Server command execution time is only one component of end-to-end
latency.

Use SLOWLOG/command statistics appropriately.

------------------------------------------------------------------------

# Part 20 --- Latency Distribution

## 22. Capture

``` text
P50
P95
P99
P99.9
max
```

Tail latency matters.

------------------------------------------------------------------------

# Part 21 --- Average Latency

## 23. Warning

Average can look healthy while a meaningful fraction of users experience
poor latency.

------------------------------------------------------------------------

# Part 22 --- Baseline Window

## 24. Choose

Capture representative:

``` text
normal
peak
batch
quiet
```

windows.

------------------------------------------------------------------------

# Part 23 --- Baseline Metrics

## 25. Redis

Collect:

``` text
ops/sec
latency
errors
connections
memory
evictions
expirations
CPU
network
replication
```

------------------------------------------------------------------------

# Part 24 --- Infrastructure Metrics

## 26. Collect

``` text
node CPU
node memory
network bytes
packets/retransmits
storage IOPS/throughput/latency
Kubernetes CPU throttling
pod restarts/OOM
```

where applicable.

------------------------------------------------------------------------

# Part 25 --- Baseline Table

## 27. Example

  Metric          Normal   Peak   SLO/Limit
  ------------- -------- ------ -----------
  ops/sec                       
  P95                           
  P99                           
  CPU                           
  memory                        
  network                       
  connections                   

------------------------------------------------------------------------

# Part 26 --- Command Inventory

## 28. Identify

Use supported command statistics/observability to determine:

``` text
calls
time
time/call
```

for important commands.

------------------------------------------------------------------------

# Part 27 --- SLOWLOG

## 29. Use

SLOWLOG can identify commands whose Redis execution exceeds configured
threshold.

Understand what it includes/excludes before interpreting.

------------------------------------------------------------------------

# Part 28 --- Complexity

## 30. Analyze

A command's cost depends on:

``` text
algorithmic complexity
collection cardinality
number of returned elements
payload size
```

------------------------------------------------------------------------

# Part 29 --- O(1) Is Not Free

## 31. Example

A GET is logically simple, but a very large value can still cause:

``` text
memory copy
network transfer
client deserialization
```

latency.

------------------------------------------------------------------------

# Part 30 --- Collection Reads

## 32. Risk

Commands returning an entire large collection can create:

``` text
CPU
network
event-loop delay
client memory
```

pressure.

------------------------------------------------------------------------

# Part 31 --- Safe Iteration

## 33. Principle

Prefer bounded iteration patterns such as:

``` text
SCAN
HSCAN
SSCAN
ZSCAN
```

where semantics permit.

------------------------------------------------------------------------

# Part 32 --- KEYS

## 34. Production

Avoid:

``` text
KEYS *
```

on shared production workloads.

Use controlled SCAN patterns.

------------------------------------------------------------------------

# Part 33 --- Large Delete

## 35. Consider

Large synchronous deletions can create latency.

Use supported asynchronous deletion such as:

``` text
UNLINK
```

where appropriate.

------------------------------------------------------------------------

# Part 34 --- Lua / Functions

## 36. Measure

Long server-side execution can block or consume significant processing
capacity.

Benchmark representative scripts.

------------------------------------------------------------------------

# Part 35 --- Transactions

## 37. Measure

Transactions change request grouping and execution behavior.

Test actual application patterns.

------------------------------------------------------------------------

# Part 36 --- Pipeline

## 38. Benefit

Pipelining can improve throughput by reducing round-trip overhead.

------------------------------------------------------------------------

# Part 37 --- Pipeline Risk

## 39. Excessive Batching

Very large pipelines can create:

``` text
burst CPU
large responses
client memory
queueing
```

Find a practical batch size.

------------------------------------------------------------------------

# Part 38 --- MGET / Multi-Key

## 40. Payload

A single operation can return many values.

Measure:

``` text
keys/request
bytes/request
latency
```

------------------------------------------------------------------------

# Part 39 --- JSON

## 41. Performance

Benchmark:

``` text
full document reads
path reads
partial updates
document size
```

------------------------------------------------------------------------

# Part 40 --- Search

## 42. Performance

Measure:

``` text
query type
filters
result count
sorting
payload
index size
```

------------------------------------------------------------------------

# Part 41 --- Vector

## 43. Performance

Measure:

``` text
K
dimension
algorithm
filters
concurrency
recall
P95/P99
```

------------------------------------------------------------------------

# Part 42 --- Streams

## 44. Performance

Measure:

``` text
XADD rate
consumer rate
pending entries
lag
batch size
```

------------------------------------------------------------------------

# Part 43 --- Memory Baseline

## 45. Capture

Use supported product metrics and, **only where supported and permitted**, inspect database/server memory through an approved, authenticated and certificate-validated Redis endpoint (for example, in an authorized interactive Redis CLI session):

``` redis
INFO memory
```

**Expected:** A section of memory statistics with name/value lines such as `used_memory:` and `used_memory_rss:`; actual metric availability and the scope of the response depend on Redis Software/Enterprise version, deployment, and ACL permissions. Do not confuse a single `INFO` reply with a complete multi-node or multi-shard cluster capacity report. Use the Redis Enterprise monitoring API/dashboard and cluster metrics for authoritative capacity analysis; if the command is restricted, record that fact rather than bypassing access controls.

Track:

``` text
used_memory
RSS
peak
fragmentation
overhead
```

------------------------------------------------------------------------

# Part 44 --- Memory Headroom

## 46. Required

Capacity must include:

``` text
dataset growth
allocator overhead
buffers
replication
background operations
failure state
```

------------------------------------------------------------------------

# Part 45 --- Fragmentation

## 47. Investigate

High fragmentation can make physical memory pressure much larger than
logical dataset size.

Use Chapter 69 methods.

------------------------------------------------------------------------

# Part 46 --- Evictions

## 48. Interpret

Eviction can indicate:

``` text
intended cache behavior
or
insufficient memory
```

depending on design.

------------------------------------------------------------------------

# Part 47 --- Expiration

## 49. Monitor

Large expiration waves can create load patterns.

Correlate with latency.

------------------------------------------------------------------------

# Part 48 --- Big Keys

## 50. Identify

Use safe sampling.

Measure:

``` text
memory
cardinality
payload
access frequency
```

------------------------------------------------------------------------

# Part 49 --- Hot Keys

## 51. Definition

A hot key receives disproportionately high traffic.

Potential effects:

``` text
hot shard
CPU skew
network skew
latency
```

------------------------------------------------------------------------

# Part 50 --- Hot Key vs Big Key

## 52. Distinguish

A key can be:

``` text
big but cold
small but hot
big and hot
```

Each needs different mitigation.

------------------------------------------------------------------------

# Part 51 --- Hot Tenant

## 53. Multi-Tenant

One tenant can dominate Redis resources.

Track ownership/namespace where possible.

------------------------------------------------------------------------

# Part 52 --- Shard Profile

## 54. Record

For each shard:

``` text
CPU
memory
ops/sec
network
role
node
```

------------------------------------------------------------------------

# Part 53 --- Node Profile

## 55. Record

``` text
CPU
memory
network
storage
connections
hosted shards
```

------------------------------------------------------------------------

# Part 54 --- Skew

## 56. Compare

Look for:

``` text
CPU skew
memory skew
network skew
connection skew
```

------------------------------------------------------------------------

# Part 55 --- Balanced Memory ≠ Balanced Performance

## 57. Important

A node/shard can have normal memory but high CPU because of hot traffic.

------------------------------------------------------------------------

# Part 56 --- Network Profile

## 58. Measure

``` text
ingress
egress
packets
retransmissions
latency
```

------------------------------------------------------------------------

# Part 57 --- Bytes per Operation

## 59. Formula

``` text
bytes/op
=
network bytes / operations
```

Track changes over time.

------------------------------------------------------------------------

# Part 58 --- Large Response

## 60. Risk

Large response payloads can cause high client latency even when Redis
execution is fast.

------------------------------------------------------------------------

# Part 59 --- TLS

## 61. Benchmark

TLS has CPU/handshake cost.

Use persistent connections and realistic connection churn.

------------------------------------------------------------------------

# Part 60 --- Connection Churn

## 62. Test

Compare:

``` text
persistent pooled connections
vs
connect per request
```

The latter is usually far more expensive.

------------------------------------------------------------------------

# Part 61 --- DNS / Endpoint

## 63. Separate

Benchmark should avoid confusing:

``` text
DNS
load balancer
proxy
Redis
```

latency.

Measure layers where possible.

------------------------------------------------------------------------

# Part 62 --- Persistence

## 64. Test

For databases using persistence, measure workload during relevant
background persistence behavior.

------------------------------------------------------------------------

# Part 63 --- Backup

## 65. Test

Measure application SLO while backup runs.

Backup must fit the operating envelope.

------------------------------------------------------------------------

# Part 64 --- Replication

## 66. Include

Replication consumes:

``` text
network
CPU
memory/buffers
```

and must be represented in production qualification.

------------------------------------------------------------------------

# Part 65 --- Failover

## 67. Test

Performance qualification is incomplete if it tests only
all-nodes-healthy state.

------------------------------------------------------------------------

# Part 66 --- N-1

## 68. Definition

Test the required failure scenario with one node/resource unavailable
where architecture requires it.

------------------------------------------------------------------------

# Part 67 --- N-1 Questions

## 69. Measure

``` text
P95/P99
CPU
memory
network
errors
connections
recovery
```

------------------------------------------------------------------------

# Part 68 --- Recovery Load

## 70. Important

After failure, recovery itself consumes resources.

Measure:

``` text
serving traffic
+
recovery
```

------------------------------------------------------------------------

# Part 69 --- Load Test Design

## 71. Representative

A useful test models:

``` text
command mix
value sizes
key distribution
TTL
connections
concurrency
read/write ratio
```

------------------------------------------------------------------------

# Part 70 --- Synthetic Benchmark Limitation

## 72. Warning

A simple:

``` text
SET/GET tiny value
```

benchmark does not qualify a complex production workload.

------------------------------------------------------------------------

# Part 71 --- redis-benchmark

## 73. Use

`redis-benchmark` can be useful for controlled protocol/command
experiments.

Do not mistake it for complete application performance qualification.

------------------------------------------------------------------------

# Part 72 --- Application Load Generator

## 74. Better for End-to-End

Use an application-aware load generator when serialization, pooling,
TLS, retries, or business behavior matters.

------------------------------------------------------------------------

# Part 73 --- Warm-Up

## 75. Before Measurement

Allow:

``` text
connections
caches
JIT/runtime
working set
```

to stabilize where relevant.

------------------------------------------------------------------------

# Part 74 --- Test Stages

## 76. Recommended

``` text
baseline
50%
75%
100%
125%
150%
```

of expected peak, adjusted for safety and environment.

------------------------------------------------------------------------

# Part 75 --- Step Load

## 77. Purpose

Increment load in controlled steps and observe the performance curve.

------------------------------------------------------------------------

# Part 76 --- Saturation Knee

## 78. Definition

The saturation knee is where additional load causes disproportionate
latency/error growth.

------------------------------------------------------------------------

# Part 77 --- Example

## 79. Pattern

``` text
50k ops/s -> P99 2 ms
75k ops/s -> P99 3 ms
90k ops/s -> P99 5 ms
100k ops/s -> P99 20 ms
110k ops/s -> P99 80 ms
```

The safe operating point is below the collapse region.

------------------------------------------------------------------------

# Part 78 --- Throughput Ceiling

## 80. Not the Target

Maximum benchmark throughput is not the production operating target.

Leave headroom.

------------------------------------------------------------------------

# Part 79 --- Error Curve

## 81. Track

At each load step:

``` text
timeouts
connection errors
command errors
retries
```

------------------------------------------------------------------------

# Part 80 --- CPU Curve

## 82. Track

Plot conceptually:

``` text
load -> CPU
```

Look for sustained saturation.

------------------------------------------------------------------------

# Part 81 --- Latency Curve

## 83. Track

``` text
load -> P95/P99
```

This is often more useful than one maximum throughput number.

------------------------------------------------------------------------

# Part 82 --- Memory Curve

## 84. Track

For stateful load:

``` text
time/load -> memory
```

separate traffic effects from dataset growth.

------------------------------------------------------------------------

# Part 83 --- Network Curve

## 85. Track

``` text
load -> network bytes/sec
```

to detect bandwidth limits.

------------------------------------------------------------------------

# Part 84 --- Concurrency Sweep

## 86. Test

Hold workload approximately constant and vary client concurrency.

Find where more concurrency stops improving throughput and increases
latency.

------------------------------------------------------------------------

# Part 85 --- Pipeline Sweep

## 87. Test

Compare bounded pipeline sizes.

Record:

``` text
throughput
P99
client memory
response size
```

------------------------------------------------------------------------

# Part 86 --- Value-Size Sweep

## 88. Test

Example:

``` text
1 KB
10 KB
100 KB
1 MB
```

only within safe, relevant workload bounds.

------------------------------------------------------------------------

# Part 87 --- Read/Write Sweep

## 89. Test

Compare representative mixes.

Writes may add replication/persistence cost.

------------------------------------------------------------------------

# Part 88 --- Hot-Key Test

## 90. Test

Compare:

``` text
uniform keys
skewed keys
single hot key
```

in an isolated environment.

------------------------------------------------------------------------

# Part 89 --- TTL Storm Test

## 91. Test

Create controlled keys with aligned expirations.

Observe expiration load.

Then compare TTL jitter.

------------------------------------------------------------------------

# Part 90 --- Connection Storm

## 92. Test

Simulate controlled reconnect burst.

Measure:

``` text
TLS
connections
CPU
latency
errors
```

------------------------------------------------------------------------

# Part 91 --- Retry Amplification

## 93. Test

Compare clients:

``` text
immediate aggressive retry
vs
bounded retry + backoff + jitter
```

Use nonproduction.

------------------------------------------------------------------------

# Part 92 --- Persistence Test

## 94. Test

Run representative load while persistence/background activity occurs.

Measure SLO.

------------------------------------------------------------------------

# Part 93 --- Backup Test

## 95. Test

Run representative load during backup.

Measure SLO and infrastructure.

------------------------------------------------------------------------

# Part 94 --- Failure Test

## 96. Test

Under approved load, inject supported node/failure event.

Measure:

``` text
error spike
P99
reconnect
recovery
```

------------------------------------------------------------------------

# Part 95 --- Soak Test

## 97. Purpose

Run representative load long enough to detect:

``` text
memory growth
connection leak
fragmentation
queue buildup
thermal/resource drift
```

------------------------------------------------------------------------

# Part 96 --- Burst Test

## 98. Purpose

Validate short traffic spikes above normal peak.

------------------------------------------------------------------------

# Part 97 --- Stop Conditions

## 99. Define Before Test

Examples:

``` text
P99 > safety threshold
error rate > threshold
CPU sustained critical
memory unsafe
network saturation
source system impact
```

------------------------------------------------------------------------

# Part 98 --- Test Evidence

## 100. Capture

``` text
test version
configuration
dataset
load generator
command mix
metrics
start/end
result
```

------------------------------------------------------------------------

# Part 99 --- Reproducibility

## 101. Requirement

A benchmark without reproducible configuration is weak evidence.

Version the test definition.

------------------------------------------------------------------------

# Part 100 --- Capacity Model

## 102. Inputs

``` text
peak ops/sec
peak memory
peak network
peak connections
P99
failure state
growth
```

------------------------------------------------------------------------

# Part 101 --- Memory Capacity

## 103. Concept

``` text
required memory
=
peak physical requirement
+
growth
+
failure/operational headroom
```

------------------------------------------------------------------------

# Part 102 --- CPU Capacity

## 104. Concept

Use observed workload curves.

Avoid assuming CPU scales perfectly linearly.

------------------------------------------------------------------------

# Part 103 --- Network Capacity

## 105. Concept

``` text
required bandwidth
=
peak application traffic
+
replication
+
recovery/background traffic
+
headroom
```

------------------------------------------------------------------------

# Part 104 --- Connection Capacity

## 106. Include

``` text
steady connections
failover reconnect
deployment surge
autoscaling surge
```

------------------------------------------------------------------------

# Part 105 --- Shard Capacity

## 107. Include

``` text
memory/shard
CPU/shard
network/shard
recovery size
```

------------------------------------------------------------------------

# Part 106 --- Failure-State Model

## 108. Required

Calculate capacity with the expected failed component removed.

------------------------------------------------------------------------

# Part 107 --- Growth Forecast

## 109. Track

``` text
GB/day
keys/day
ops growth/month
connections growth/month
network growth/month
```

------------------------------------------------------------------------

# Part 108 --- Linear Forecast

## 110. Simple

``` text
future = current + growth_rate * time
```

Useful only when trend is approximately linear.

------------------------------------------------------------------------

# Part 109 --- Seasonal Growth

## 111. Better

Account for:

``` text
daily
weekly
monthly
business events
```

patterns.

------------------------------------------------------------------------

# Part 110 --- Product Launch

## 112. Scenario

Add explicit expected workload from new applications/features rather
than relying only on historical trend.

------------------------------------------------------------------------

# Part 111 --- 30-Day Forecast

## 113. Operational

Can the current platform safely handle the next month?

------------------------------------------------------------------------

# Part 112 --- 90-Day Forecast

## 114. Planning

Enough time to:

``` text
procure
scale
test
change
```

before emergency.

------------------------------------------------------------------------

# Part 113 --- 12-Month Forecast

## 115. Strategic

Useful for:

``` text
budget
architecture
licenses
regional expansion
```

------------------------------------------------------------------------

# Part 114 --- Scaling Threshold

## 116. Define

A threshold should trigger before safety headroom disappears.

------------------------------------------------------------------------

# Part 115 --- Memory Threshold

## 117. Base On

``` text
growth rate
lead time
failure headroom
```

not a universal percentage.

------------------------------------------------------------------------

# Part 116 --- CPU Threshold

## 118. Base On

Sustained peak behavior and P99 curve.

------------------------------------------------------------------------

# Part 117 --- Network Threshold

## 119. Base On

Application plus replication/recovery needs.

------------------------------------------------------------------------

# Part 118 --- Connection Threshold

## 120. Base On

Steady + reconnect/deployment surge.

------------------------------------------------------------------------

# Part 119 --- Lead Time

## 121. Important

If scaling requires two weeks of approval/provisioning/testing, alert
before capacity is exhausted within two weeks.

------------------------------------------------------------------------

# Part 120 --- Capacity Risk Date

## 122. Formula Concept

``` text
days to threshold
=
remaining safe capacity / daily growth
```

------------------------------------------------------------------------

# Part 121 --- Performance Regression

## 123. Definition

A new version/configuration performs materially worse than approved
baseline.

------------------------------------------------------------------------

# Part 122 --- Regression Gate

## 124. Compare

``` text
P95
P99
throughput
CPU/op
bytes/op
memory/op or dataset
errors
```

------------------------------------------------------------------------

# Part 123 --- Software Upgrade

## 125. Test

Benchmark before/after:

``` text
Redis Enterprise upgrade
client upgrade
Operator upgrade
Kubernetes change
```

where performance risk exists.

------------------------------------------------------------------------

# Part 124 --- Application Release

## 126. Test

A code release can change:

``` text
command mix
payload size
TTL
connection behavior
retry
```

without changing Redis.

------------------------------------------------------------------------

# Part 125 --- Data Model Change

## 127. Test

Examples:

``` text
HASH -> JSON
new Search index
new vector dimension
larger objects
```

require new capacity baseline.

------------------------------------------------------------------------

# Part 126 --- Regression Threshold

## 128. Example Concept

Fail qualification if:

``` text
P99 exceeds SLO
errors exceed SLO
capacity headroom falls below approved requirement
```

Use service-specific thresholds.

------------------------------------------------------------------------

# Part 127 --- Performance Dashboard

## 129. Include

``` text
ops/sec
P95/P99
errors
CPU
memory
network
connections
evictions
replication
```

------------------------------------------------------------------------

# Part 128 --- Capacity Dashboard

## 130. Include

``` text
current
peak
safe threshold
growth
days to threshold
N-1 capacity
```

------------------------------------------------------------------------

# Part 129 --- Per-Database View

## 131. Include

``` text
memory
ops
connections
latency
owner
growth
```

------------------------------------------------------------------------

# Part 130 --- Per-Shard View

## 132. Include

``` text
CPU
memory
network
ops
placement
```

where supported.

------------------------------------------------------------------------

# Part 131 --- Lab Namespace

## 133. Use

``` text
tutorial:chapter76:*
```

for synthetic lab keys.

------------------------------------------------------------------------

# Part 132 --- Lab 1: Workload Profile

## 134. Exercise

Build the complete workload profile from representative telemetry.

------------------------------------------------------------------------

# Part 133 --- Lab 2: Baseline

## 135. Exercise

Capture 30+ minutes of representative nonproduction or approved traffic.

Record P50/P95/P99 and resources.

------------------------------------------------------------------------

# Part 134 --- Lab 3: Command Profile

## 136. Exercise

Collect command statistics before/after workload.

Identify top commands by:

``` text
calls
total time
time/call
```

------------------------------------------------------------------------

# Part 135 --- Lab 4: Value Size

## 137. Exercise

Generate bounded values of different sizes.

Measure:

``` text
latency
network
memory
```

------------------------------------------------------------------------

# Part 136 --- Lab 5: Pipeline

## 138. Exercise

Compare no pipeline vs several bounded pipeline sizes.

Find practical throughput/latency balance.

------------------------------------------------------------------------

# Part 137 --- Lab 6: Hot Key

## 139. Exercise

Compare uniform and skewed key access.

Observe shard/node skew.

------------------------------------------------------------------------

# Part 138 --- Lab 7: Step Load

## 140. Exercise

Increase load gradually.

Build:

``` text
ops/sec -> P99
ops/sec -> CPU
ops/sec -> errors
```

curves.

------------------------------------------------------------------------

# Part 139 --- Lab 8: N-1

## 141. Exercise

In an approved disposable environment, test representative workload with
required component unavailable.

Measure SLO and recovery.

------------------------------------------------------------------------

# Part 140 --- Lab 9: Soak

## 142. Exercise

Run sustained representative load.

Look for:

``` text
memory growth
fragmentation
connection growth
latency drift
```

------------------------------------------------------------------------

# Part 141 --- Lab 10: Capacity Forecast

## 143. Exercise

Using current peak + growth:

calculate:

``` text
30-day
90-day
12-month
```

capacity scenarios.

------------------------------------------------------------------------

# Part 142 --- Failure Scenario 1: Hot Key

## 144. Test

Identify whether CPU/network skew follows a single key.

Document data-model mitigation.

------------------------------------------------------------------------

# Part 143 --- Failure Scenario 2: Big Value

## 145. Test

Show server execution may remain low while end-to-end latency/network
rises.

------------------------------------------------------------------------

# Part 144 --- Failure Scenario 3: Oversized Pipeline

## 146. Test

Increase batch size until tail latency worsens.

Identify safe operating range.

------------------------------------------------------------------------

# Part 145 --- Failure Scenario 4: Connection Storm

## 147. Test

Generate controlled reconnect burst.

Validate pool/backoff behavior.

------------------------------------------------------------------------

# Part 146 --- Failure Scenario 5: TTL Storm

## 148. Test

Compare synchronized expirations vs jittered expirations.

------------------------------------------------------------------------

# Part 147 --- Failure Scenario 6: Persistence Pressure

## 149. Test

Measure representative workload during persistence/background activity.

------------------------------------------------------------------------

# Part 148 --- Failure Scenario 7: Backup Pressure

## 150. Test

Measure workload during backup.

------------------------------------------------------------------------

# Part 149 --- Failure Scenario 8: Node Failure Under Peak

## 151. Test

Validate N-1 SLO and recovery headroom.

------------------------------------------------------------------------

# Part 150 --- Failure Scenario 9: Retry Amplification

## 152. Test

Compare aggressive retry vs bounded exponential backoff/jitter.

------------------------------------------------------------------------

# Part 151 --- Failure Scenario 10: Growth Exceeds Forecast

## 153. Tabletop

Double expected growth rate.

Calculate new capacity-risk date and scaling action.

------------------------------------------------------------------------

# Part 152 --- Troubleshooting Matrix

## 154. Common Problems

  Symptom                              Investigate
  ------------------------------------ -------------------------------------
  high P99, low Redis execution time   network/client/payload
  high P99 + CPU                       command complexity/hot key
  memory rising                        growth/TTL/fragmentation
  one shard hot                        key/tenant distribution
  network high                         payload/large result/replication
  throughput plateaus                  CPU/network/client/concurrency
  more concurrency worsens latency     saturation/queueing
  backup causes latency                CPU/network/storage/background load
  N-1 fails SLO                        insufficient failure headroom
  capacity surprises                   bad workload/growth model

------------------------------------------------------------------------

# Part 153 --- Runbook 1: Redis Latency Regression

## 155. Procedure

``` text
1. confirm client P95/P99.
2. compare Redis command execution.
3. inspect command mix.
4. inspect CPU/memory/network.
5. inspect hot keys/shards.
6. inspect recent changes.
7. mitigate bottleneck.
8. compare against baseline.
```

------------------------------------------------------------------------

# Part 154 --- Runbook 2: Capacity Risk

## 156. Procedure

``` text
1. identify constrained resource.
2. measure peak.
3. calculate growth.
4. calculate failure headroom.
5. calculate risk date.
6. choose scale/optimize action.
7. qualify change.
8. update forecast.
```

------------------------------------------------------------------------

# Part 155 --- Runbook 3: Hot Key / Hot Shard

## 157. Procedure

``` text
1. identify hot shard.
2. identify key/tenant/command.
3. measure CPU/network impact.
4. determine logical vs placement cause.
5. redesign/distribute/rate-limit as appropriate.
6. retest.
7. validate SLO.
8. update guardrail.
```

------------------------------------------------------------------------

# Part 156 --- Runbook 4: Memory Pressure

## 158. Procedure

``` text
1. capture INFO MEMORY/metrics.
2. separate dataset/overhead/RSS.
3. inspect growth/TTL.
4. inspect big keys.
5. inspect fragmentation.
6. inspect evictions.
7. remediate root cause/scale.
8. validate headroom.
```

------------------------------------------------------------------------

# Part 157 --- Runbook 5: Throughput Saturation

## 159. Procedure

``` text
1. identify saturation knee.
2. inspect CPU.
3. inspect network.
4. inspect command mix/payload.
5. inspect client concurrency.
6. inspect shard skew.
7. optimize/scale.
8. rerun step test.
```

------------------------------------------------------------------------

# Part 158 --- Runbook 6: Connection Pressure

## 160. Procedure

``` text
1. measure connections/churn.
2. inspect client pools.
3. inspect deployment/autoscaling.
4. inspect TLS handshakes.
5. add backoff/jitter.
6. reduce unnecessary churn.
7. retest reconnect event.
8. validate peak capacity.
```

------------------------------------------------------------------------

# Part 159 --- Runbook 7: N-1 Capacity Failure

## 161. Procedure

``` text
1. preserve failure test evidence.
2. identify saturated resource.
3. quantify missing headroom.
4. scale/optimize.
5. verify placement.
6. repeat N-1 test.
7. validate recovery load.
8. approve only after SLO passes.
```

------------------------------------------------------------------------

# Part 160 --- Runbook 8: Performance Regression Gate

## 162. Procedure

``` text
1. run approved baseline workload.
2. run candidate version/config.
3. compare latency/throughput/errors.
4. compare CPU/memory/network.
5. identify material regressions.
6. reject or remediate.
7. rerun.
8. record acceptance.
```

------------------------------------------------------------------------

# Part 161 --- Performance Qualification Template

## 163. Record

``` text
Application:
Database:
Test version:
Dataset:
Command mix:
Peak target:
Concurrency:
Connections:
P50:
P95:
P99:
Errors:
CPU:
Memory:
Network:
N-1 result:
Pass/Fail:
```

------------------------------------------------------------------------

# Part 162 --- Capacity Model Template

## 164. Record

``` text
Resource:
Current peak:
Safe threshold:
Failure-state peak:
Growth rate:
30-day forecast:
90-day forecast:
12-month forecast:
Lead time:
Risk date:
Action:
```

------------------------------------------------------------------------

# Part 163 --- Regression Template

## 165. Record

``` text
Baseline version:
Candidate version:
Workload:
P95 delta:
P99 delta:
Throughput delta:
CPU delta:
Memory delta:
Network delta:
Error delta:
Decision:
```

------------------------------------------------------------------------

# Part 164 --- Production Acceptance

## 166. Workload

-   [ ] command mix documented;
-   [ ] read/write ratio documented;
-   [ ] value-size distribution documented;
-   [ ] key/cardinality profile documented;
-   [ ] TTL profile documented;
-   [ ] connections/concurrency documented;
-   [ ] peak/burst traffic documented.

## 167. Performance

-   [ ] P50/P95/P99 baseline documented;
-   [ ] server vs end-to-end latency understood;
-   [ ] command statistics reviewed;
-   [ ] SLOWLOG reviewed where appropriate;
-   [ ] big keys reviewed;
-   [ ] hot keys/shards reviewed;
-   [ ] network profile documented;
-   [ ] pipeline/concurrency behavior qualified.

## 168. Capacity

-   [ ] memory model documented;
-   [ ] fragmentation reviewed;
-   [ ] CPU headroom documented;
-   [ ] network headroom documented;
-   [ ] connection headroom documented;
-   [ ] shard/node skew reviewed;
-   [ ] failure-state capacity documented;
-   [ ] N-1 tested where required.

## 169. Testing / Forecasting

-   [ ] step load completed;
-   [ ] saturation knee identified;
-   [ ] burst test completed;
-   [ ] soak test completed;
-   [ ] persistence/backup impact tested where applicable;
-   [ ] failure test completed;
-   [ ] 30/90-day forecast created;
-   [ ] annual scenario created;
-   [ ] scaling thresholds defined;
-   [ ] lead time included;
-   [ ] regression gate implemented.

## 170. Operational Readiness

-   [ ] ten failure scenarios completed;
-   [ ] eight runbooks reviewed;
-   [ ] performance qualification report complete;
-   [ ] capacity model complete;
-   [ ] acceptance result signed off.

------------------------------------------------------------------------

# 171. Knowledge Validation

1.  Why is "Redis is fast" not a production performance specification?
2.  What information belongs in a workload profile?
3.  Why should peak and burst ops/sec be measured?
4.  Why should value-size distribution include percentiles and max?
5.  Why does collection cardinality matter?
6.  Why should connection churn be measured?
7.  Why must performance tests have an SLO?
8.  What components can contribute to client-observed latency?
9.  Why is average latency insufficient?
10. What does SLOWLOG help identify?
11. Why can an O(1) command still be expensive?
12. Why are unbounded collection reads dangerous?
13. Why can excessive pipelining increase tail latency?
14. What is the difference between a big key and hot key?
15. Why can balanced memory coexist with CPU skew?
16. What does bytes/op reveal?
17. Why should TLS connection churn be benchmarked?
18. Why must persistence and backup be included in qualification?
19. What is N-1 capacity?
20. Why must recovery load be included in failure testing?
21. Why is a tiny-value GET/SET benchmark insufficient?
22. What is a saturation knee?
23. Why is maximum throughput not the production target?
24. Why should concurrency be swept rather than maximized?
25. What does a soak test reveal?
26. What belongs in a capacity model?
27. Why should scaling thresholds include lead time?
28. What is a capacity risk date?
29. What is a performance regression gate?
30. What must pass before Redis performance/capacity is
    production-ready?

------------------------------------------------------------------------

# 172. Hands-On Acceptance Checklist

-   [ ] Built workload profile.
-   [ ] Captured normal and peak baseline.
-   [ ] Captured P50/P95/P99.
-   [ ] Reviewed command statistics.
-   [ ] Reviewed SLOWLOG where appropriate.
-   [ ] Measured value-size distribution.
-   [ ] Measured key/cardinality profile.
-   [ ] Reviewed TTL distribution.
-   [ ] Reviewed connections/concurrency.
-   [ ] Reviewed memory/fragmentation.
-   [ ] Identified big keys.
-   [ ] Tested hot-key skew.
-   [ ] Built shard/node heatmap.
-   [ ] Measured network bytes/op.
-   [ ] Tested bounded pipeline sizes.
-   [ ] Tested value-size effect.
-   [ ] Tested concurrency.
-   [ ] Completed step load.
-   [ ] Identified saturation knee.
-   [ ] Completed burst test.
-   [ ] Completed soak test.
-   [ ] Tested persistence/backup impact where applicable.
-   [ ] Completed N-1 test where required.
-   [ ] Tested reconnect behavior.
-   [ ] Built memory/CPU/network/connection model.
-   [ ] Built 30/90-day forecast.
-   [ ] Built annual scenario.
-   [ ] Defined scaling thresholds.
-   [ ] Defined capacity risk date.
-   [ ] Built regression gate.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed eight runbooks.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 173. Cleanup

Remove only disposable Chapter 76 benchmark data.

For:

``` text
tutorial:chapter76:*
```

use controlled:

``` text
SCAN
+
UNLINK
```

Do not use:

``` text
FLUSHDB
FLUSHALL
```

on shared environments.

Stop/remove temporary:

``` text
load generators
benchmark clients
fault injection
temporary monitoring
temporary test databases
```

through approved procedures.

Confirm:

``` text
no synthetic load remains
no failure injection remains
normal topology
normal application latency
normal CPU/memory/network
test keys removed
benchmark evidence preserved
```

------------------------------------------------------------------------

# 174. Key Takeaways

1.  Production performance must be defined by workload, latency,
    throughput, resource use, and failure conditions.
2.  Capacity planning must use representative peaks rather than
    averages.
3.  Command mix, value size, key distribution, TTL, connections, and
    concurrency are fundamental workload inputs.
4.  End-to-end latency includes client, DNS, connection, TLS, network,
    proxy, Redis, payload, and client-processing time.
5.  P95/P99/P99.9 reveal behavior that averages hide.
6.  Command statistics and SLOWLOG help isolate Redis execution cost.
7.  Algorithmic complexity, cardinality, result count, and payload size
    all influence command cost.
8.  Large values can cause high network/client latency even when Redis
    command execution is fast.
9.  Pipelining improves throughput only up to a practical operating
    point.
10. Big keys and hot keys are different problems.
11. Shard/node analysis must include CPU, memory, network, and traffic
    skew.
12. Memory capacity includes allocator, buffers, replication, background
    work, growth, and failure headroom.
13. Persistence, backup, replication, and recovery must be part of
    performance qualification.
14. N-1 testing proves whether the platform can meet SLO during required
    failure scenarios.
15. Synthetic benchmarks must reproduce meaningful production workload
    characteristics.
16. Step-load testing reveals the saturation knee.
17. Maximum benchmark throughput should not become the production
    operating target.
18. Concurrency and pipeline sizes should be experimentally qualified.
19. Soak testing exposes leaks, fragmentation, and long-duration drift.
20. Burst testing validates short demand spikes.
21. Capacity models must include memory, CPU, network, connections,
    shards, failure state, and growth.
22. Forecasts should include 30-day, 90-day, and strategic scenarios.
23. Scaling thresholds must account for provisioning/change lead time.
24. Performance regression gates protect production from software,
    client, infrastructure, and data-model changes.
25. Production acceptance requires a reproducible workload, measured
    operating envelope, failure-state qualification, capacity forecast,
    scaling triggers, tested runbooks, and documented pass/fail
    evidence.

------------------------------------------------------------------------

# 175. References

Validate all Redis Enterprise performance metrics, administrative
commands, benchmark behavior, shard/node observability, persistence,
replication, failover, and Kubernetes resource behavior against the
exact deployed versions and current official documentation.

Recommended documentation areas:

-   Redis Enterprise performance and sizing
-   Redis Enterprise monitoring and metrics
-   Redis Enterprise shards and proxies
-   Redis Enterprise high availability
-   Redis Enterprise persistence
-   Redis Enterprise backup
-   Redis Enterprise Auto Tiering / Flex where applicable
-   Redis command documentation and time complexity
-   Redis SLOWLOG
-   Redis INFO / command statistics
-   redis-benchmark
-   Redis pipelining
-   Redis memory optimization
-   Redis Search
-   RedisJSON
-   Redis vector search
-   Redis Streams
-   Redis Enterprise Kubernetes Operator
-   Kubernetes CPU/memory resource management
-   organizational SLO and performance-test standards

------------------------------------------------------------------------

# Next Chapter

**Chapter 77 --- Redis Enterprise Security Hardening &
Credential-Rotation Project**

Chapter 77 will integrate security architecture, threat boundaries, TLS,
certificate lifecycle, authentication, ACL least privilege, service
identities, secret management, credential rotation without outage,
network segmentation, Kubernetes RBAC/NetworkPolicy, privileged access,
audit evidence, vulnerability/version posture, break-glass access,
incident response, security validation, failure scenarios, runbooks, and
final security acceptance.
