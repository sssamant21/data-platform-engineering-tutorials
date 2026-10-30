# Chapter 54 --- Redis Enterprise Benchmarking, Load Testing & Performance Qualification Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 10 --- Migration, Data Services & Advanced Capabilities\
**Level:** Advanced → Production Performance Engineering\
**Audience:** SREs, DBREs, Platform Engineers, Redis Administrators,
Performance Engineers, Application Owners\
**Lab type:** Workload modeling, baseline benchmarking,
application-realistic load, warm-up, step load, saturation analysis,
payload testing, pipelining, connection scaling, skew/hot-key testing,
N-1 testing, failover under load, soak testing, failure injection,
troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

A Redis benchmark that produces a large operations-per-second number
does not prove that a production workload is safe.

Production qualification must answer:

``` text
Can the system meet its latency and throughput objectives
under representative workload
with production-like data
at expected peak
with required failure headroom
for the required duration?
```

This chapter builds a repeatable methodology for qualifying Redis
Enterprise performance.

By the end, you should be able to:

-   define a representative workload model;
-   distinguish microbenchmarking from production qualification;
-   establish an idle and loaded baseline;
-   warm the system correctly;
-   run step-load tests;
-   identify the saturation knee;
-   analyze P50/P95/P99/P99.9 latency;
-   test value-size and command-mix effects;
-   test connection and pipeline behavior;
-   test hot keys and shard skew;
-   validate N-1 capacity;
-   test failover under load;
-   perform soak testing;
-   define stop conditions;
-   preserve performance evidence;
-   compare test runs;
-   create production performance acceptance gates.

------------------------------------------------------------------------

# 2. Core Production Principle

The goal is not:

``` text
maximum possible throughput
```

The goal is:

``` text
maximum safe throughput
while meeting SLOs
with required failure and recovery headroom
```

------------------------------------------------------------------------

# Part 1 --- Benchmark vs Qualification

## 3. Microbenchmark

A microbenchmark isolates a narrow operation.

Example:

``` text
SET
GET
PING
```

It is useful for:

``` text
basic latency
network comparison
configuration comparison
regression detection
```

It does not automatically represent the application.

## 4. Production Qualification

Production qualification includes:

``` text
real command mix
realistic key distribution
representative value sizes
TTL behavior
connection count
pipeline behavior
read/write ratio
persistence
replication
failure conditions
application SLO
```

------------------------------------------------------------------------

# Part 2 --- Test Questions

## 5. Define Before Testing

Examples:

``` text
Can Redis sustain 50k ops/sec at P99 < 10 ms?
What happens at 2× normal peak?
Where is the saturation knee?
Can the cluster survive one node/failure-domain loss?
What is failover impact at peak?
How many application connections are safe?
What value size causes network saturation?
Does pipelining improve throughput without unacceptable P99?
Can the system run at peak for four hours without degradation?
```

A test without a question often produces data without a decision.

------------------------------------------------------------------------

# Part 3 --- Workload Model

## 6. Record

``` text
normal ops/sec
peak ops/sec
burst ops/sec
read/write ratio
command mix
key count
working set
value-size distribution
TTL distribution
connection count
pipeline size
hot-key distribution
growth rate
```

------------------------------------------------------------------------

# Part 4 --- Command Mix

## 7. Example

``` text
GET      60%
SET      20%
HGET     10%
HSET      5%
INCR      3%
other     2%
```

Do not benchmark only GET if production uses hashes, writes, Streams,
scripts, or transactions.

------------------------------------------------------------------------

# Part 5 --- Read/Write Ratio

## 8. Why It Matters

Writes can create additional work through:

``` text
replication
persistence
AOF
snapshot copy-on-write
Active-Active replication
backup interaction
```

A 95% read workload and a 50% write workload can have very different
capacity profiles.

------------------------------------------------------------------------

# Part 6 --- Value-Size Distribution

## 9. Measure Percentiles

Record:

``` text
P50 value size
P95
P99
maximum
```

Testing only tiny values can hide:

``` text
network pressure
serialization cost
memory growth
replication traffic
```

------------------------------------------------------------------------

# Part 7 --- Key Distribution

## 10. Uniform vs Realistic

A uniform random-key benchmark can hide production skew.

Real workloads may have:

``` text
hot tenants
hot users
hot sessions
popular objects
time-based concentration
```

Test both uniform and representative skew.

------------------------------------------------------------------------

# Part 8 --- TTL Distribution

## 11. Include Expiration

Record:

``` text
persistent keys
short TTL
medium TTL
long TTL
```

Expiration can produce background work and synchronized expiration
behavior.

------------------------------------------------------------------------

# Part 9 --- Working Set

## 12. Dataset vs Working Set

The total dataset may be 500 GB while only 50 GB is frequently accessed.

Performance tests should model the active working set rather than only
total storage.

------------------------------------------------------------------------

# Part 10 --- Test Environment

## 13. Document

``` text
Redis Enterprise version
node count
node type
CPU
RAM
network
storage
shards
replicas
persistence
database memory
eviction policy
TLS
client location
client CPU
```

Without environment metadata, results are difficult to reproduce.

------------------------------------------------------------------------

# Part 11 --- Environment Similarity

## 14. Production-Like

Match production where practical:

``` text
software version
topology
node size
network path
TLS
persistence
replication
data distribution
client behavior
```

If the environment differs, document the difference.

------------------------------------------------------------------------

# Part 12 --- Load Generator Capacity

## 15. Critical

The load generator can become the bottleneck.

Monitor:

``` text
client CPU
client memory
network
connections
event-loop/thread saturation
serialization
```

Never conclude Redis saturated if the generator cannot produce more
load.

------------------------------------------------------------------------

# Part 13 --- Clock Synchronization

## 16. Time

Ensure systems have reliable time synchronization.

This matters for:

``` text
timeline correlation
latency analysis
failover timing
incident evidence
```

------------------------------------------------------------------------

# Part 14 --- Baseline

## 17. Idle Baseline

Before load, record:

``` text
CPU
memory
network
connections
latency
replication
persistence
storage
```

## 18. Normal-Load Baseline

Then run representative normal traffic and record the same metrics.

------------------------------------------------------------------------

# Part 15 --- Warm-Up

## 19. Why

The first minutes may include:

``` text
cold connections
cold application caches
JIT/runtime warm-up
empty Redis cache
initial allocations
DNS/TLS setup
```

Do not mix warm-up with steady-state measurement unless cold-start
behavior is the test objective.

------------------------------------------------------------------------

# Part 16 --- Warm-Up Procedure

## 20. Example

``` text
5 min low load
10 min normal load
wait for metrics to stabilize
start measurement window
```

Use workload-appropriate durations.

------------------------------------------------------------------------

# Part 17 --- Step-Load Testing

## 21. Method

Increase load gradually.

Example:

``` text
10k ops/sec
20k
30k
40k
50k
60k
...
```

Hold each step long enough to observe stable behavior.

------------------------------------------------------------------------

# Part 18 --- Why Step Load

## 22. Benefit

Step testing shows how:

``` text
latency
CPU
network
connections
errors
```

change as load increases.

It helps reveal the saturation knee.

------------------------------------------------------------------------

# Part 19 --- Saturation Knee

## 23. Definition

The saturation knee is the region where additional load begins producing
disproportionate latency or errors.

Conceptually:

``` text
load increases modestly
but
P99 increases sharply
```

Production capacity should retain headroom below this point.

------------------------------------------------------------------------

# Part 20 --- Throughput

## 24. Measure

Record:

``` text
requested operations/sec
successful operations/sec
failed operations/sec
```

Do not report attempted throughput as successful throughput.

------------------------------------------------------------------------

# Part 21 --- Latency Percentiles

## 25. Record

At minimum:

``` text
P50
P95
P99
```

For latency-sensitive workloads consider:

``` text
P99.9
```

Averages can hide severe tail latency.

------------------------------------------------------------------------

# Part 22 --- Error Rate

## 26. Track

Classify:

``` text
connect errors
TLS/auth errors
timeouts
Redis errors
pool errors
application errors
```

Do not combine every failure into one generic error counter.

------------------------------------------------------------------------

# Part 23 --- CPU

## 27. Observe Per Node / Shard

Cluster-average CPU can hide a hot shard.

Monitor:

``` text
average
maximum
per-node
per-shard where available
```

------------------------------------------------------------------------

# Part 24 --- Memory

## 28. Observe

Track:

``` text
used memory
headroom
fragmentation
evictions
growth
```

Load tests should not accidentally convert into uncontrolled memory-fill
tests unless intended.

------------------------------------------------------------------------

# Part 25 --- Network

## 29. Observe

Track:

``` text
bytes/sec
packets/sec
errors/drops
client network
server network
```

Large values can make network the first bottleneck.

------------------------------------------------------------------------

# Part 26 --- Connections

## 30. Observe

Record:

``` text
active connections
connection creation rate
reconnects
pool wait
```

A benchmark that creates a connection per command tests connection setup
more than Redis command throughput.

------------------------------------------------------------------------

# Part 27 --- redis-benchmark Awareness

## 31. Purpose

`redis-benchmark` can be useful for controlled Redis microbenchmarks.

Use it to explore:

``` text
simple commands
concurrency
payload sizes
pipeline behavior
```

Do not treat default output as production capacity certification.

------------------------------------------------------------------------

# Part 28 --- Basic Lab

## 32. Disposable Environment — Bounded Microbenchmark

**This is a write-generating workload, not a read-only diagnostic.** Do not point it at an existing production or shared Redis endpoint: `SET` can overwrite keys, and even a small test creates request, CPU and memory pressure. Obtain the lab owner's approval, confirm the exact target instance, capacity budget and stop conditions, and ensure it contains **no other workload**.

For an explicitly dedicated, disposable **local loopback-only** Redis sandbox with no authentication or TLS (never an Enterprise/remote endpoint), use a minimal smoke test:

``` bash
test "${REDIS_HOST:-127.0.0.1}" = "127.0.0.1"
redis-benchmark -h 127.0.0.1 -p 6379 -c 2 -n 200 -t get,set -q
```

**Expected:** The command prints `GET` and `SET` throughput summaries (requests/second), and can include percentile latency output depending on client version. **No throughput or latency number is guaranteed.** Record both client/server versions, host, load, CPU, network, memory, and actual results. A failed connectivity/permission check means `FAIL`, not that Redis performance is inadequate.

The previous `-c 50 -n 100000` example could generate considerable unapproved load, so it is **not** the default lab. A representative throughput test must use a dedicated approved staging database, agreed client concurrency/request budget, workload isolation, TLS/authentication compatible with the installed benchmark version, and a stop trigger. Benchmark utilities can generate or overwrite their test keys, so isolate the complete database/instance rather than relying only on a key prefix.

**STOP** if client errors, memory/eviction or application latency exceed the approved threshold. Never assume a benchmark run is safe because the command itself is syntactically valid, and never put secrets in CLI arguments or logs.

Official reference: [Redis benchmark utility, options and limitations](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/benchmarks/).

------------------------------------------------------------------------

# Part 29 --- Payload Test

## 33. Example Concept

Run the same workload with:

``` text
100 B
1 KB
10 KB
100 KB
```

Compare:

``` text
throughput
P99
network
CPU
memory
```

------------------------------------------------------------------------

# Part 30 --- Concurrency Test

## 34. Example

Compare:

``` text
10 clients
50
100
500
```

Stop when predefined safety limits are reached.

------------------------------------------------------------------------

# Part 31 --- Pipeline Test

## 35. Compare

``` text
pipeline 1
pipeline 5
pipeline 10
pipeline 50
pipeline 100
```

Measure throughput and tail latency.

Large pipelines can improve throughput while worsening burstiness or
per-request latency.

------------------------------------------------------------------------

# Part 32 --- Application-Realistic Generator

## 36. Better Qualification

Build or use a load generator that reproduces:

``` text
actual command mix
actual key pattern
actual value sizes
actual TTL
actual connections
actual pipeline
actual serialization
```

This should be the primary qualification workload.

------------------------------------------------------------------------

# Part 33 --- Synthetic Namespace

## 37. Safety

Use:

``` text
tutorial:chapter54:<test>:<id>
```

Never mix performance-test keys with production business keys.

------------------------------------------------------------------------

# Part 34 --- Preload

## 38. Prepare Dataset

Before read-heavy testing, preload enough synthetic data to represent
the expected working set.

Record:

``` text
key count
memory
value distribution
TTL
```

------------------------------------------------------------------------

# Part 35 --- Cache Hit Ratio

## 39. For Cache Workloads

Measure:

``` text
hits
misses
source requests
```

A benchmark that produces 100% hits may not model production miss
behavior.

------------------------------------------------------------------------

# Part 36 --- Source Protection

## 40. Cache Miss Testing

If testing cache misses, protect the backing source with:

``` text
concurrency limit
rate limit
synthetic source
```

Do not overload a real production database for a Redis benchmark.

------------------------------------------------------------------------

# Part 37 --- Hot-Key Test

## 41. Method

Compare:

``` text
uniform keys
10% traffic to one key family
50% traffic to one hot key
```

Observe per-shard CPU and P99.

------------------------------------------------------------------------

# Part 38 --- Tenant Skew

## 42. Multi-Tenant

Simulate:

``` text
many normal tenants
one large tenant
```

Validate noisy-neighbor behavior.

------------------------------------------------------------------------

# Part 39 --- Large-Key Test

## 43. Controlled

Test representative large values or collections.

Observe:

``` text
latency
network
CPU
memory
client serialization
```

Do not create unbounded objects.

------------------------------------------------------------------------

# Part 40 --- TTL Storm Test

## 44. Compare

Scenario A:

``` text
many keys same TTL
```

Scenario B:

``` text
TTL + jitter
```

Observe expiration behavior and source/cache impact.

------------------------------------------------------------------------

# Part 41 --- Write-Heavy Test

## 45. Include Persistence

Run representative writes while monitoring:

``` text
replication
AOF
snapshot/rewrite
storage
network
```

------------------------------------------------------------------------

# Part 42 --- Persistence Interaction

## 46. Test During Background Work

Where safe, test representative load while persistence activity occurs.

Measure impact on P99 and throughput.

------------------------------------------------------------------------

# Part 43 --- Backup Interaction

## 47. Qualification

If production backups overlap traffic, test or otherwise qualify that
combination.

------------------------------------------------------------------------

# Part 44 --- Connection Scale Test

## 48. Model Fleet

Use the Chapter 53 connection budget.

Test representative:

``` text
pods
workers
pool size
```

Measure connection creation and steady-state behavior.

------------------------------------------------------------------------

# Part 45 --- Startup Storm Test

## 49. Simulate

Start many disposable clients together.

Measure:

``` text
connections/sec
TLS/auth cost
P99
errors
```

------------------------------------------------------------------------

# Part 46 --- Reconnect Storm Test

## 50. Simulate

Force approved lab reconnect behavior.

Validate:

``` text
backoff
jitter
connection recovery
Redis stability
```

------------------------------------------------------------------------

# Part 47 --- N-1 Capacity

## 51. Requirement

A highly available service should be evaluated when one required
capacity component is unavailable.

Conceptually:

``` text
peak workload
+
one node/failure domain unavailable
```

must remain within the approved SLO if that is the service requirement.

------------------------------------------------------------------------

# Part 48 --- N-1 Test

## 52. Nonproduction / Approved Exercise

Run representative peak load.

Remove or isolate one approved failure-domain component using the
supported platform procedure.

Measure:

``` text
P99
errors
CPU
memory
network
connections
recovery
```

------------------------------------------------------------------------

# Part 49 --- Failover Under Load

## 53. Critical

Do not test failover only at idle.

Run representative load during failover and measure:

``` text
error burst
latency spike
reconnects
retry amplification
recovery time
```

------------------------------------------------------------------------

# Part 50 --- Recovery Capacity

## 54. After Failure

The system may need capacity for:

``` text
replication catch-up
rebalancing
reconnect
backlog processing
```

Performance qualification continues after service becomes reachable.

------------------------------------------------------------------------

# Part 51 --- Soak Testing

## 55. Purpose

Short tests can miss:

``` text
memory growth
connection leaks
fragmentation
backlog growth
periodic jobs
persistence interaction
thermal/resource drift
```

Run a representative workload for an appropriate duration.

------------------------------------------------------------------------

# Part 52 --- Soak Metrics

## 56. Trend

Track over time:

``` text
P99
CPU
memory
fragmentation
connections
errors
network
replication
persistence
backlog
```

Look for drift, not just threshold breaches.

------------------------------------------------------------------------

# Part 53 --- Burst Test

## 57. Model Real Spikes

Example:

``` text
normal = 20k ops/sec
burst = 60k for 30 sec
```

Measure recovery after the burst.

------------------------------------------------------------------------

# Part 54 --- Queueing

## 58. Warning

Near saturation, queues can grow rapidly.

Symptoms:

``` text
P99 rises
pool wait rises
timeouts rise
throughput stops increasing
```

This is a strong signal that useful capacity is exhausted.

------------------------------------------------------------------------

# Part 55 --- Little's Law Awareness

## 59. Concept

For stable systems:

``` text
concurrency ≈ throughput × latency
```

If throughput is high and latency rises, required concurrency also
rises, potentially increasing connection and queue pressure.

------------------------------------------------------------------------

# Part 56 --- Stop Conditions

## 60. Define Before Test

Examples:

``` text
P99 > approved limit
error rate > approved limit
CPU reaches unsafe sustained level
memory headroom below minimum
evictions unexpectedly begin
replication becomes unhealthy
source dependency becomes unsafe
storage/network limit reached
```

Do not improvise safety limits during the test.

------------------------------------------------------------------------

# Part 57 --- Abort Procedure

## 61. Required

The test operator must know how to:

``` text
stop generators
reduce load
remove synthetic traffic
restore topology
validate recovery
```

------------------------------------------------------------------------

# Part 58 --- Test Isolation

## 62. Production

Avoid unapproved destructive performance tests in production.

Prefer:

``` text
dedicated performance environment
staging
isolated database
approved production read-only observation
```

------------------------------------------------------------------------

# Part 59 --- Change One Variable

## 63. Comparison

When testing an optimization, change one major variable at a time where
practical.

Otherwise attribution becomes difficult.

------------------------------------------------------------------------

# Part 60 --- Repeatability

## 64. Run Multiple Times

A single run can be noisy.

Repeat important tests and compare distributions.

------------------------------------------------------------------------

# Part 61 --- Evidence Metadata

## 65. Every Run

Record:

``` text
test ID
date/time
commit/config version
Redis version
topology
client version
dataset
workload
duration
operator
```

------------------------------------------------------------------------

# Part 62 --- Result Table

## 66. Example

    Load   Success ops/s   P50   P95   P99   Errors   Max CPU
  ------ --------------- ----- ----- ----- -------- ---------
     10k                                            
     20k                                            
     30k                                            
     40k                                            

------------------------------------------------------------------------

# Part 63 --- Capacity Curve

## 67. Plot

Useful plots include:

``` text
load vs P99
load vs successful throughput
load vs max CPU
load vs errors
load vs network
```

The shape often communicates capacity better than a single number.

------------------------------------------------------------------------

# Part 64 --- Regression Comparison

## 68. Compare Versions

Use the same workload to compare:

``` text
before vs after client upgrade
before vs after Redis upgrade
before vs after node change
before vs after configuration change
```

------------------------------------------------------------------------

# Part 65 --- Statistical Caution

## 69. Avoid False Precision

Performance varies.

Do not claim:

``` text
exact production capacity = 53,417 ops/sec
```

when the environment and workload vary.

Use an operating envelope with safety headroom.

------------------------------------------------------------------------

# Part 66 --- Headroom

## 70. Production Capacity

If saturation occurs near:

``` text
100k ops/sec
```

that does not mean 100k should be the production target.

Reserve capacity for:

``` text
bursts
failures
recovery
maintenance
growth
```

------------------------------------------------------------------------

# Part 67 --- Failure Scenario 1

## 71. Generator Saturation

Expected:

``` text
requested load stops increasing
client CPU reaches limit
Redis still has headroom
```

Lesson: validate generator capacity.

------------------------------------------------------------------------

# Part 68 --- Failure Scenario 2

## 72. Hot Shard

Concentrate keys safely.

Expected:

``` text
one shard/node saturates before cluster average
```

------------------------------------------------------------------------

# Part 69 --- Failure Scenario 3

## 73. Network Saturation

Increase payload size.

Observe network throughput and latency.

------------------------------------------------------------------------

# Part 70 --- Failure Scenario 4

## 74. Pool Saturation

Limit client pool while increasing concurrency.

Observe pool wait and application P99.

------------------------------------------------------------------------

# Part 71 --- Failure Scenario 5

## 75. TTL Storm

Create synchronized synthetic expirations.

Compare with jitter.

------------------------------------------------------------------------

# Part 72 --- Failure Scenario 6

## 76. Write/Persistence Pressure

Increase writes during approved persistence activity.

Observe P99 and storage behavior.

------------------------------------------------------------------------

# Part 73 --- Failure Scenario 7

## 77. N-1

Remove approved capacity under load.

Measure degraded-state headroom.

------------------------------------------------------------------------

# Part 74 --- Failure Scenario 8

## 78. Failover

Trigger approved failover under load.

Measure client and Redis recovery.

------------------------------------------------------------------------

# Part 75 --- Failure Scenario 9

## 79. Reconnect Storm

Reconnect many clients together.

Validate backoff/jitter.

------------------------------------------------------------------------

# Part 76 --- Failure Scenario 10

## 80. Long Soak

Run sustained load and detect memory/connection/backlog drift.

------------------------------------------------------------------------

# Part 77 --- Troubleshooting Matrix

## 81. Common Results

  Symptom                       Investigate
  ----------------------------- --------------------------------------------
  throughput flat, CPU low      generator, network, pool, command mix
  P99 rises sharply             saturation, queueing, hot shard, network
  cluster avg CPU normal        per-shard/per-node skew
  errors at high concurrency    connections, pool, timeouts
  write test much slower        persistence, replication, storage
  large values slow             network, serialization, memory
  failover causes long outage   client reconnect/retry/DNS
  soak degrades over time       leak, fragmentation, backlog, periodic job
  benchmark good, app bad       unrealistic workload/model
  N-1 fails                     insufficient failure headroom

------------------------------------------------------------------------

# Part 78 --- Runbook 1: Performance Baseline

## 82. Procedure

``` text
1. Record environment.
2. Record workload.
3. Warm system.
4. Run normal load.
5. Record P50/P95/P99.
6. Record CPU/memory/network.
7. Record connections/errors.
8. Store evidence.
```

------------------------------------------------------------------------

# Part 79 --- Runbook 2: Step Load

## 83. Procedure

``` text
1. Define steps.
2. Define hold duration.
3. Define stop conditions.
4. Warm system.
5. Run each step.
6. Record metrics.
7. Identify saturation knee.
8. Define safe envelope.
```

------------------------------------------------------------------------

# Part 80 --- Runbook 3: Hot-Key Test

## 84. Procedure

``` text
1. Establish uniform baseline.
2. Introduce controlled skew.
3. Observe per-shard CPU.
4. Observe P99.
5. Increase skew carefully.
6. Stop at safety gate.
7. Compare results.
8. document mitigation.
```

------------------------------------------------------------------------

# Part 81 --- Runbook 4: N-1 Test

## 85. Procedure

``` text
1. Confirm approvals.
2. Run representative peak.
3. Record baseline.
4. remove approved capacity.
5. Measure degraded state.
6. measure recovery.
7. restore topology.
8. validate healthy state.
```

------------------------------------------------------------------------

# Part 82 --- Runbook 5: Failover Under Load

## 86. Procedure

``` text
1. Run representative workload.
2. record baseline.
3. trigger approved failover.
4. measure errors/P99.
5. measure reconnect/retries.
6. measure recovery time.
7. validate redundancy.
8. store evidence.
```

------------------------------------------------------------------------

# Part 83 --- Runbook 6: Soak Test

## 87. Procedure

``` text
1. define duration.
2. warm system.
3. run steady workload.
4. trend latency.
5. trend memory/connections.
6. inspect persistence/backlog.
7. inspect drift.
8. close with health validation.
```

------------------------------------------------------------------------

# Part 84 --- Runbook 7: Performance Regression

## 88. Procedure

``` text
1. reproduce baseline workload.
2. compare versions/config.
3. confirm environment equality.
4. identify changed metric.
5. isolate one variable.
6. repeat test.
7. determine regression.
8. accept, remediate, or rollback.
```

------------------------------------------------------------------------

# Part 85 --- Runbook 8: Test Abort

## 89. Procedure

``` text
1. stop load generators.
2. stop synthetic writers.
3. confirm traffic falling.
4. restore topology if changed.
5. validate Redis health.
6. validate dependencies.
7. preserve evidence.
8. document trigger.
```

------------------------------------------------------------------------

# Part 86 --- Performance Test Plan Template

## 90. Record

``` text
Test ID:
Owner:
Question:
Environment:
Redis version:
Topology:
Dataset:
Working set:
Command mix:
Read/write:
Value sizes:
TTL:
Connections:
Pipeline:
Normal load:
Peak load:
Burst:
Duration:
Stop conditions:
Failure test:
Expected result:
```

------------------------------------------------------------------------

# Part 87 --- Result Template

## 91. Record

``` text
Test ID:
Successful ops/sec:
P50:
P95:
P99:
P99.9:
Errors:
Max node CPU:
Max shard CPU:
Memory:
Network:
Connections:
Evictions:
Replication:
Persistence:
Generator CPU:
Pass/Fail:
Notes:
```

------------------------------------------------------------------------

# Part 88 --- Capacity Qualification

## 92. Gate

A workload should not be approved only because it reaches the requested
throughput.

Require:

``` text
latency PASS
errors PASS
capacity PASS
failure headroom PASS
recovery PASS
soak PASS
```

------------------------------------------------------------------------

# Part 89 --- Production Acceptance

## 93. Workload

-   [ ] normal/peak/burst defined;
-   [ ] command mix defined;
-   [ ] read/write ratio defined;
-   [ ] key/value distribution defined;
-   [ ] TTL defined;
-   [ ] connections defined;
-   [ ] pipeline behavior defined.

## 94. Environment

-   [ ] Redis version recorded;
-   [ ] topology recorded;
-   [ ] node resources recorded;
-   [ ] persistence/replication recorded;
-   [ ] network/storage recorded;
-   [ ] generator capacity validated.

## 95. Tests

-   [ ] idle baseline;
-   [ ] normal baseline;
-   [ ] warm-up;
-   [ ] step load;
-   [ ] saturation knee;
-   [ ] payload sizes;
-   [ ] concurrency;
-   [ ] pipeline;
-   [ ] hot key/skew;
-   [ ] TTL storm;
-   [ ] write/persistence;
-   [ ] connection scale;
-   [ ] startup/reconnect storm;
-   [ ] N-1;
-   [ ] failover under load;
-   [ ] soak;
-   [ ] burst.

## 96. Evidence

-   [ ] P50/P95/P99 recorded;
-   [ ] successful throughput recorded;
-   [ ] errors classified;
-   [ ] max node/shard CPU recorded;
-   [ ] memory/network/connections recorded;
-   [ ] capacity curves stored;
-   [ ] test metadata stored;
-   [ ] stop conditions honored.

------------------------------------------------------------------------

# 97. Knowledge Validation

1.  Why is maximum ops/sec not production capacity?
2.  What is the difference between a microbenchmark and qualification?
3.  Why define a test question first?
4.  Why model command mix?
5.  Why does read/write ratio matter?
6.  Why measure value-size distribution?
7.  Why test key skew?
8.  What is a working set?
9.  Why monitor the load generator?
10. Why warm the system?
11. What is step-load testing?
12. What is the saturation knee?
13. Why use P99 instead of only average?
14. Why record successful rather than attempted throughput?
15. Why inspect per-shard CPU?
16. Why can large values become network-bound?
17. What is `redis-benchmark` useful for?
18. Why is it insufficient by itself?
19. Why preload representative data?
20. Why test cache misses carefully?
21. Why test synchronized TTLs?
22. Why test persistence interaction?
23. Why test connection scale?
24. What is N-1 capacity?
25. Why test failover under load?
26. What can soak tests reveal?
27. Why define stop conditions before testing?
28. Why repeat important tests?
29. Why reserve production headroom below saturation?
30. What evidence is required to approve production capacity?

------------------------------------------------------------------------

# 98. Hands-On Acceptance Checklist

-   [ ] Documented performance questions.
-   [ ] Built workload model.
-   [ ] Recorded test environment.
-   [ ] Validated generator capacity.
-   [ ] Captured idle baseline.
-   [ ] Captured normal-load baseline.
-   [ ] Completed warm-up.
-   [ ] Completed step-load test.
-   [ ] Identified saturation knee.
-   [ ] Recorded P50/P95/P99.
-   [ ] Tested payload sizes.
-   [ ] Tested concurrency.
-   [ ] Tested pipeline sizes.
-   [ ] Built application-realistic workload.
-   [ ] Preloaded representative dataset.
-   [ ] Tested hit/miss behavior.
-   [ ] Tested hot-key skew.
-   [ ] Tested tenant skew.
-   [ ] Tested large values.
-   [ ] Tested TTL storm/jitter.
-   [ ] Tested write/persistence interaction.
-   [ ] Tested connection scale.
-   [ ] Tested startup/reconnect storms.
-   [ ] Completed N-1 test.
-   [ ] Completed failover-under-load test.
-   [ ] Completed soak test.
-   [ ] Completed burst test.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed eight runbooks.
-   [ ] Stored test evidence.
-   [ ] Completed production acceptance.

------------------------------------------------------------------------

# 99. Cleanup

List only Chapter 54 synthetic keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter54:*'
```

Review matches and remove confirmed disposable keys with `UNLINK`.

Remove temporary:

``` text
load generators
synthetic clients
failure rules
test DNS/network changes
temporary dashboards
temporary alerts
test datasets
```

Restore any topology changed during approved N-1/failover testing.

Never use `FLUSHDB` or `FLUSHALL` against a shared or production
database.

------------------------------------------------------------------------

# 100. Key Takeaways

1.  Production qualification is not a contest for the largest ops/sec
    number.
2.  Test the real workload model, not only simple GET/SET.
3.  Value sizes, TTLs, key distribution, and command mix matter.
4.  The load generator must be proven capable.
5.  Warm-up and measurement windows should be separated.
6.  Step load reveals how latency changes with demand.
7.  The saturation knee is more useful than a single maximum-throughput
    number.
8.  Tail latency is critical.
9.  Successful throughput matters more than attempted throughput.
10. Per-shard metrics can reveal bottlenecks hidden by cluster averages.
11. `redis-benchmark` is useful but not sufficient for production
    certification.
12. Application-realistic load should be the primary qualification
    workload.
13. Hot-key and tenant-skew tests are essential.
14. TTL storms should be tested where expiration is significant.
15. Persistence and backup can change write performance.
16. Connection scale and reconnect behavior are part of capacity.
17. N-1 capacity must be tested for HA services.
18. Failover should be tested under representative load.
19. Recovery capacity matters after availability returns.
20. Soak tests expose time-dependent failures.
21. Burst tests should include recovery behavior.
22. Stop conditions must be defined before testing.
23. Repeatability and evidence are required for useful comparisons.
24. Production capacity should include failure, recovery, maintenance,
    burst, and growth headroom.
25. Performance acceptance requires latency, errors, capacity, failure,
    recovery, and soak results together.

------------------------------------------------------------------------

# 101. References

Validate tools, metrics, command behavior, and architecture against the
exact Redis Enterprise version and current official Redis documentation.

Recommended documentation areas:

-   Redis Enterprise performance and sizing
-   Redis Enterprise architecture
-   Redis Enterprise persistence
-   Redis Enterprise replication and high availability
-   Redis Enterprise observability
-   Redis Enterprise Active-Active
-   `redis-benchmark`
-   Redis pipelining
-   Redis latency monitoring
-   Redis memory optimization
-   Redis client documentation
-   cloud/network/storage performance documentation

------------------------------------------------------------------------

# Next Chapter

**Chapter 55 --- Redis Enterprise RedisJSON Data Modeling & Document
Engineering**

Chapter 55 will cover document modeling, JSON paths, CRUD and partial
updates, TTL strategy, indexing interaction, memory/value-size
considerations, schema evolution, concurrency, client integration,
performance testing, observability, failure scenarios, troubleshooting,
runbooks, and production acceptance.
