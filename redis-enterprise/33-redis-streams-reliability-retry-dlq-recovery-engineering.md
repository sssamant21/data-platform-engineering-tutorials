# Chapter 33 --- Redis Streams Reliability, Retry, DLQ & Recovery Engineering

**Status:** Canonical\
**Track:** Redis Enterprise / Redis Software Production Engineering\
**Part:** Part 3 --- Messaging, Streaming & Event-Driven Engineering\
**Level:** Advanced → Production Stream Reliability Engineering\
**Audience:** Developers, SREs, DBREs, Platform Engineers, Redis
Administrators\
**Lab type:** Pending-entry lifecycle, crash recovery, retry
classification, delayed retry patterns, reclaim safety, poison-event
isolation, DLQ design, replay controls, idempotency, deduplication
windows, consumer fleet restart, outage catch-up, lag SLOs,
recovery-capacity modeling, failure injection, dashboards,
troubleshooting, runbooks, and production acceptance

------------------------------------------------------------------------

# 1. Objective

Chapter 32 introduced Redis Streams and consumer groups.

This chapter focuses on what happens when production processing fails.

A normal path is:

``` text
XADD
  |
  v
Stream
  |
  v
Consumer Group
  |
  v
Consumer
  |
  +--> success --> XACK
  |
  +--> failure --> retry / pending / recovery / DLQ
```

The difficult part is not receiving an event.

The difficult part is safely handling:

``` text
consumer crashes
timeouts
partial business commits
retries
duplicate delivery
poison messages
long outages
large backlogs
recovery storms
DLQ replay
```

By the end, you should be able to:

-   Explain the Pending Entries List lifecycle.
-   Detect abandoned work.
-   Size reclaim thresholds safely.
-   Distinguish retryable and non-retryable failures.
-   Prevent tight retry loops.
-   Design delayed retries.
-   Build bounded retry policies.
-   Isolate poison events.
-   Design a DLQ.
-   Replay DLQ events safely.
-   Design idempotent processing.
-   Define deduplication windows.
-   Recover after consumer fleet outages.
-   Model backlog catch-up time.
-   Define lag SLOs.
-   Protect downstream systems during recovery.
-   Build reliability dashboards.
-   Inject realistic failures.
-   Execute production runbooks.

------------------------------------------------------------------------

# 2. Core Production Principle

Redis Streams can preserve events and track pending delivery, but
application reliability is not automatic.

A production consumer must explicitly define:

``` text
when work is complete
when to ACK
what can retry
how long to retry
who recovers abandoned work
how duplicates are handled
where poison events go
how backlog is recovered
```

------------------------------------------------------------------------

# Part 1 --- Processing State Machine

## 3. Event Lifecycle

A useful model is:

``` text
NEW
 |
 v
DELIVERED
 |
 v
PENDING
 | \
 |  \ failure
 |   v
 | RETRY
 |   |
 |   +--> success --> ACKED
 |   |
 |   +--> exhausted --> DLQ
 |
 +--> success --> ACKED
```

This state machine should be documented for each consumer.

------------------------------------------------------------------------

# Part 2 --- Pending Entries List

## 4. PEL Purpose

For consumer groups, delivered but unacknowledged messages are tracked
as pending.

The PEL helps answer:

``` text
Which events are unfinished?
Which consumer owns them?
How long have they been idle?
How many times were they delivered?
```

------------------------------------------------------------------------

# Part 3 --- `XPENDING`

## 5. Summary

``` redis
XPENDING tutorial:chapter33:orders order-workers
```

Use detailed forms supported by your Redis version to inspect specific
pending entries and consumers.

------------------------------------------------------------------------

# Part 4 --- Healthy Pending Work

## 6. Pending Does Not Always Mean Broken

A message may be pending because:

``` text
consumer is actively processing it
downstream operation is slow but healthy
batch is still in progress
```

Do not reclaim simply because pending count is nonzero.

------------------------------------------------------------------------

# Part 5 --- Abandoned Work

## 7. Definition

An event is likely abandoned when:

``` text
owning consumer is gone
and
idle duration exceeds normal processing behavior
```

Both conditions matter.

------------------------------------------------------------------------

# Part 6 --- Reclaim Threshold

## 8. Measure First

Suppose normal processing is:

``` text
P50 = 200 ms
P95 = 2 s
P99 = 8 s
max expected = 20 s
```

A reclaim threshold of:

``` text
3 s
```

is unsafe.

A threshold such as:

``` text
60 s
```

may be more appropriate, depending on workload and failure objectives.

Do not copy this value blindly.

------------------------------------------------------------------------

# Part 7 --- Reclaim Risk

## 9. Concurrent Duplicate Processing

If Consumer A is still processing and Consumer B reclaims the same
event:

``` text
A -> business operation
B -> same business operation
```

Both may execute concurrently.

Idempotency must protect the business effect.

------------------------------------------------------------------------

# Part 8 --- `XCLAIM`

## 10. Explicit Claim

Conceptually:

``` redis
XCLAIM stream group recovery-worker <min-idle-ms> <stream-id>
```

Use when the recovery process has identified specific abandoned entries.

Validate exact syntax for the deployed Redis version.

------------------------------------------------------------------------

# Part 9 --- `XAUTOCLAIM`

## 11. Scanning Recovery

Where supported:

``` redis
XAUTOCLAIM stream group recovery-worker 60000 0-0 COUNT 100
```

**Version and environment gate:** `XAUTOCLAIM` was introduced in Redis **6.2**. This is **illustrative**, not a command to run against a production stream/group named `stream`/`group`. It changes ownership of pending entries and can trigger duplicate business processing if retry/idempotency controls are absent. Use a separately approved, populated, isolated lab stream and consumer group.

**Expected:** The reply includes a cursor-like stream ID to pass as the next `start` argument and a list of messages claimed whose idle time exceeds the threshold. The cursor `0-0` indicates this scan pass completed, **not** that the queue is permanently empty. In Redis **7.0+**, a *third* reply element lists pending IDs removed because their stream entries no longer exist; Redis 6.2 replies do not include that third deleted-ID list. `COUNT` bounds attempted claim work and does not guarantee exactly 100 returned records. A claim does not `XACK` those entries.

This can scan for sufficiently idle pending entries and claim them.

Use bounded `COUNT`; never lower a real application's recovery idle threshold simply to make a tutorial command return a result.

------------------------------------------------------------------------

# Part 10 --- Recovery Loop

## 12. Pattern

``` text
claim bounded batch
        |
        v
validate event
        |
        v
check idempotency
        |
        v
process
        |
   +----+----+
   |         |
 success   failure
   |         |
 XACK     retry/DLQ
```

------------------------------------------------------------------------

# Part 11 --- Failure Classification

## 13. Retryable

Examples may include:

``` text
temporary timeout
HTTP 503
temporary connection failure
short dependency outage
rate-limit response
```

------------------------------------------------------------------------

# Part 12 --- Non-Retryable

## 14. Examples

Potentially:

``` text
invalid schema
unsupported event version
missing mandatory field
permanent business validation failure
invalid identifier
```

Application semantics decide classification.

------------------------------------------------------------------------

# Part 13 --- Unknown Failure

## 15. Safe Policy

Do not automatically classify every unknown exception as infinitely
retryable.

Unknown failures should have:

``` text
bounded retries
telemetry
operator visibility
eventual quarantine
```

------------------------------------------------------------------------

# Part 14 --- Retry Budget

## 16. Define

Example:

``` text
attempt 1: immediate processing
attempt 2: after short delay
attempt 3: after longer delay
attempt 4: after longer delay
then DLQ/quarantine
```

The exact budget depends on dependency behavior and business
requirements.

------------------------------------------------------------------------

# Part 15 --- Retry Amplification

## 17. Equation

If:

``` text
original events = 10,000/sec
each failure retries 5 times
```

the system may create:

``` text
up to 50,000 additional attempts/sec
```

depending on implementation.

Retries consume real capacity.

------------------------------------------------------------------------

# Part 16 --- Tight Retry Loop

## 18. Anti-Pattern

``` text
fail
retry immediately
fail
retry immediately
...
```

This can overload:

``` text
Redis
consumer CPU
downstream database
HTTP service
logs
```

------------------------------------------------------------------------

# Part 17 --- Backoff

## 19. Pattern

Use increasing delays:

``` text
1 s
5 s
30 s
2 min
```

according to the failure class.

Add jitter when many consumers may retry together.

------------------------------------------------------------------------

# Part 18 --- Retry Scheduling

## 20. Streams Do Not Automatically Schedule Future Retries

A pending entry does not itself become a delayed scheduler.

Applications need an explicit retry design.

------------------------------------------------------------------------

# Part 19 --- Retry Design A: Leave Pending

## 21. Concept

Keep failed work pending and let a recovery process revisit it later.

Benefits:

``` text
simple
original stream ID retained
```

Risks:

``` text
PEL can grow
retry timing is application-managed
poison messages remain pending
```

------------------------------------------------------------------------

# Part 20 --- Retry Design B: Retry Stream

## 22. Concept

Move/copy retry metadata to a dedicated retry stream.

Example:

``` text
orders.events.retry
```

Fields:

``` text
original_event_id
original_stream_id
attempt
retry_after
failure_class
```

A retry scheduler/worker reintroduces eligible work.

------------------------------------------------------------------------

# Part 21 --- Retry Design C: Sorted-Set Scheduler

## 23. Concept

Use a sorted set:

``` text
score = retry timestamp
member = retry reference
```

Workers query due items.

This adds application complexity and atomicity requirements.

Use only when justified.

------------------------------------------------------------------------

# Part 22 --- Retry Metadata

## 24. Recommended

Track:

``` text
event ID
original stream ID
attempt
first failure time
last failure time
failure class
next retry time
```

Do not store sensitive exception payloads unnecessarily.

------------------------------------------------------------------------

# Part 23 --- Poison Event

## 25. Definition

A poison event fails consistently regardless of retry timing.

Example:

``` json
{
  "event_version": 999,
  "required_field": null
}
```

Repeated retries waste capacity.

------------------------------------------------------------------------

# Part 24 --- Poison Isolation

## 26. Policy

After bounded attempts:

``` text
capture diagnostic metadata
write to DLQ/quarantine
ACK original according to design
alert/measure
continue processing healthy events
```

------------------------------------------------------------------------

# Part 25 --- Dead-Letter Queue

## 27. Redis Stream DLQ

Example:

``` text
tutorial:chapter33:orders:dlq
```

DLQ entry:

``` text
event_id
original_stream
original_stream_id
event_type
attempt
failure_class
failure_reason_code
failed_at
```

------------------------------------------------------------------------

# Part 26 --- Payload Policy

## 28. Avoid Blind Copies

Copying the entire original payload into the DLQ may:

``` text
duplicate memory
duplicate sensitive data
increase persistence
increase retention cost
```

Decide whether to store:

``` text
full payload
sanitized payload
reference only
```

------------------------------------------------------------------------

# Part 27 --- DLQ Monitoring

## 29. Required Metrics

Track:

``` text
DLQ additions/sec
DLQ total length
oldest unresolved DLQ age
failure class
event type
producer version
```

------------------------------------------------------------------------

# Part 28 --- DLQ Ownership

## 30. Operational Requirement

Every DLQ needs:

``` text
owner
alert threshold
triage procedure
fix workflow
replay procedure
retention
```

------------------------------------------------------------------------

# Part 29 --- Replay Safety

## 31. Never Blindly Replay Everything

Before replay:

``` text
fix root cause
validate one event
confirm idempotency
confirm downstream capacity
rate-limit replay
monitor errors
```

------------------------------------------------------------------------

# Part 30 --- Replay Batch

## 32. Bounded

Example operational sequence:

``` text
replay 10
validate
replay 100
validate
increase gradually
```

Avoid sending a large DLQ directly into a recovering downstream system.

------------------------------------------------------------------------

# Part 31 --- Replay Identity

## 33. Preserve Event ID

A replayed event should preserve the business identity needed for
idempotency.

It may receive a new stream ID while retaining:

``` text
original event_id
original stream_id
replay_id
```

------------------------------------------------------------------------

# Part 32 --- Idempotency

## 34. Core Requirement

Consumers must assume that an event can be delivered more than once.

Design:

``` text
same event
+
multiple processing attempts
=
one intended business effect
```

------------------------------------------------------------------------

# Part 33 --- Database Constraint

## 35. Strong Pattern

For business records, an authoritative database uniqueness/version
constraint may provide stronger correctness than an expiring Redis
marker.

Example concept:

``` text
UNIQUE(event_id)
```

------------------------------------------------------------------------

# Part 34 --- State Version

## 36. Alternative

If events describe entity versions:

``` text
customer 1001 version 7
```

consumer can reject an already-applied or older version according to
domain semantics.

------------------------------------------------------------------------

# Part 35 --- Redis Deduplication Window

## 37. Bounded Suppression

For non-permanent deduplication:

``` redis
SET dedupe:event:abc123 1 NX EX 86400
```

This suppresses duplicates only while the marker exists.

------------------------------------------------------------------------

# Part 36 --- Deduplication Window

## 38. Sizing

The window should exceed the plausible duplicate/replay interval if
Redis markers are used.

Consider:

``` text
consumer outage
retry horizon
DLQ replay delay
deployment delay
retention
```

------------------------------------------------------------------------

# Part 37 --- Idempotency Race

## 39. Check-Then-Act Risk

Unsafe:

``` text
check marker
perform business action
write marker
```

Two consumers can race.

Use an atomic/authoritative design appropriate to the business effect.

------------------------------------------------------------------------

# Part 38 --- ACK Boundary

## 40. Failure Window

``` text
business commit succeeds
        |
        X crash
        |
        no ACK
```

The message will be eligible for recovery.

This is why ACK cannot replace idempotency.

------------------------------------------------------------------------

# Part 39 --- Consumer Fleet Outage

## 41. Scenario

Producer continues:

``` text
5,000 events/sec
```

Consumers are offline:

``` text
30 minutes
```

Backlog:

``` text
5,000 × 1,800
=
9,000,000 events
```

before considering retention and entry-size overhead.

------------------------------------------------------------------------

# Part 40 --- Catch-Up Capacity

## 42. Formula

If:

``` text
producer rate = P
consumer total rate = C
```

net catch-up rate:

``` text
C - P
```

only when:

``` text
C > P
```

------------------------------------------------------------------------

# Part 41 --- Catch-Up Time

## 43. Formula

``` text
catch-up time
=
backlog
/
(consumer capacity - producer rate)
```

Example:

``` text
backlog = 9,000,000
P = 5,000/sec
C = 8,000/sec
net = 3,000/sec

catch-up = 3,000 sec
≈ 50 minutes
```

assuming dependencies sustain the rate.

------------------------------------------------------------------------

# Part 42 --- Recovery Storm

## 44. Risk

Starting all consumers at maximum speed can overload:

``` text
database
HTTP dependencies
Redis
network
CPU
```

A backlog is not permission to ignore downstream capacity.

------------------------------------------------------------------------

# Part 43 --- Recovery Pacing

## 45. Controls

Use:

``` text
consumer concurrency
batch size
rate limit
dependency concurrency
retry budget
gradual replica scaling
```

------------------------------------------------------------------------

# Part 44 --- Lag SLO

## 46. Define Time, Not Only Count

Example:

``` text
99% of events processed within 60 seconds
```

This is often more meaningful than:

``` text
backlog < 10,000
```

because event rates change.

------------------------------------------------------------------------

# Part 45 --- Oldest Pending Age

## 47. Critical Signal

Track:

``` text
oldest pending age
```

A small pending count containing one 6-hour-old event may be more
concerning than 1,000 entries pending for 200 ms.

------------------------------------------------------------------------

# Part 46 --- Consumer Health

## 48. Useful Signals

``` text
consumer heartbeat
last successful event time
processing rate
error rate
pending count
oldest pending
reclaim count
```

------------------------------------------------------------------------

# Part 47 --- Zombie Consumer

## 49. Definition

A consumer may still exist in group metadata even though its process is
gone.

Operational cleanup must distinguish:

``` text
inactive metadata
from
pending work still assigned to it
```

Do not remove consumer metadata without understanding pending ownership.

------------------------------------------------------------------------

# Part 48 --- Consumer Deletion

## 50. Caution

Redis supports consumer-group administration commands that can remove
consumers.

Validate exact behavior regarding pending entries for the deployed Redis
version before using them operationally.

------------------------------------------------------------------------

# Part 49 --- Retention vs. Recovery

## 51. Recovery Window

Retention should cover at least the intended:

``` text
maximum outage
+
catch-up time
+
operational safety margin
```

subject to memory/capacity constraints.

------------------------------------------------------------------------

# Part 50 --- Retention Example

## 52. Scenario

If the system must tolerate:

``` text
2-hour consumer outage
+
1-hour catch-up
```

then a 30-minute retention policy is incompatible with that recovery
requirement.

------------------------------------------------------------------------

# Part 51 --- DLQ Retention

## 53. Separate Policy

DLQ events may need different retention from the primary stream.

Define:

``` text
maximum triage delay
audit requirement
replay requirement
sensitive-data policy
```

------------------------------------------------------------------------

# Part 52 --- Backpressure

## 54. Consumer Side

Bound:

``` text
batch size
workers
in-flight operations
downstream connections
```

Do not load huge batches into application memory merely because a
backlog exists.

------------------------------------------------------------------------

# Part 53 --- Producer Backpressure

## 55. When Possible

If lag becomes unsafe, systems may need to:

``` text
slow producers
reject low-priority work
shed optional events
switch to degraded mode
```

only where business semantics allow.

------------------------------------------------------------------------

# Part 54 --- Priority

## 56. Separate Workloads

If critical and bulk events share one stream/group, bulk backlog may
affect critical work.

Possible design:

``` text
critical stream
standard stream
bulk stream
```

But more streams increase operational complexity.

------------------------------------------------------------------------

# Part 55 --- Ordering vs. Parallelism

## 57. Tradeoff

More consumers improve parallelism but may complicate business ordering.

If events for the same entity must be processed in order, design
partitioning/version checks accordingly.

------------------------------------------------------------------------

# Part 56 --- Observability Dashboard

## 58. Producer Panel

Show:

``` text
events/sec
errors/sec
P95/P99 publish latency
event bytes
```

------------------------------------------------------------------------

## 59. Stream Panel

Show:

``` text
XLEN
memory
retention behavior
growth rate
```

------------------------------------------------------------------------

## 60. Consumer Group Panel

Show:

``` text
processing rate
lag
pending count
oldest pending age
consumer count
reclaim rate
```

------------------------------------------------------------------------

## 61. Reliability Panel

Show:

``` text
retry rate
retry exhausted
DLQ rate
DLQ length
duplicate suppressed
idempotency conflicts
```

------------------------------------------------------------------------

## 62. Dependency Panel

Show:

``` text
DB latency/errors
HTTP latency/errors
connection pool saturation
rate-limit responses
```

Correlate consumer problems with dependency health.

------------------------------------------------------------------------

# Part 57 --- Alerting

## 63. Alert on Trends

Useful alerts include:

``` text
lag SLO breach
oldest pending too old
DLQ rate > baseline
DLQ oldest age
consumer processing stopped
backlog growth sustained
retry amplification
```

------------------------------------------------------------------------

# Part 58 --- Hands-On Lab

## 64. Objectives

You will:

1.  create a stream/group;
2.  generate events;
3.  leave events pending;
4.  inspect PEL;
5.  simulate consumer crash;
6.  recover abandoned work;
7.  test reclaim threshold;
8.  create retry metadata;
9.  create poison event;
10. route it to DLQ;
11. test idempotency;
12. replay safely;
13. generate outage backlog;
14. calculate catch-up;
15. test recovery pacing.

------------------------------------------------------------------------

# Part 59 --- Prerequisites

## 65. Install

``` bash
python -m pip install redis
```

Environment:

``` text
REDIS_HOST
REDIS_PORT
REDIS_PASSWORD
```

Use an isolated disposable lab.

------------------------------------------------------------------------

# Part 60 --- Lab Keys

## 66. Names

``` text
tutorial:chapter33:orders
tutorial:chapter33:orders:retry
tutorial:chapter33:orders:dlq
tutorial:chapter33:dedupe:*
```

Consumer group:

``` text
order-workers
```

------------------------------------------------------------------------

# Part 61 --- Producer

## 67. Create Events

``` python
import os
import time
import uuid
import redis

r = redis.Redis(
    host=os.getenv(
        "REDIS_HOST",
        "localhost",
    ),
    port=int(
        os.getenv(
            "REDIS_PORT",
            "6379",
        )
    ),
    password=(
        os.getenv("REDIS_PASSWORD")
        or None
    ),
    decode_responses=True,
)

STREAM = "tutorial:chapter33:orders"

for i in range(100):
    r.xadd(
        STREAM,
        {
            "event_id":
                str(uuid.uuid4()),
            "event_version": "1",
            "event_type":
                "order.created",
            "order_id":
                str(1000 + i),
            "occurred_at":
                str(time.time()),
        },
    )
```

------------------------------------------------------------------------

# Part 62 --- Create Group

## 68. Command

``` redis
XGROUP CREATE tutorial:chapter33:orders order-workers 0 MKSTREAM
```

Handle `BUSYGROUP` safely in reusable startup code.

------------------------------------------------------------------------

# Part 63 --- Create Pending Work

## 69. Read Without ACK

``` redis
XREADGROUP GROUP order-workers worker-1 COUNT 5 STREAMS tutorial:chapter33:orders >
```

Do not ACK these entries yet.

------------------------------------------------------------------------

# Part 64 --- Inspect PEL

## 70. Command

``` redis
XPENDING tutorial:chapter33:orders order-workers
```

Record:

``` text
pending count
consumer
idle behavior
```

------------------------------------------------------------------------

# Part 65 --- Crash Simulation

## 71. Procedure

Treat `worker-1` as crashed.

Wait longer than the lab reclaim threshold.

Use a recovery consumer to claim the entries.

Do not use a short production threshold merely to make the lab faster.

------------------------------------------------------------------------

# Part 66 --- Auto-Claim

## 72. Example

Where supported:

``` redis
XAUTOCLAIM tutorial:chapter33:orders order-workers recovery-worker 10000 0-0 COUNT 5
```

**Expected only after the isolated lab has a valid `order-workers` group and unacknowledged messages idle for at least 10,000 ms:** A next cursor, zero to five claimed message IDs with fields, and (Redis 7.0+) a third list for deleted/missing entries. Empty claimed messages are **valid** if no entry qualifies; capture actual IDs instead of expecting deterministic timestamps. If group/key is missing, record the error and correct lab setup rather than creating/altering a shared group. Claims move ownership into `recovery-worker`'s pending entries; validate source writes and deduplication before acknowledging the specific IDs. A repeated recovery pass can reclaim other entries that have become eligible.

The 10-second value is for an isolated learning lab only.

Production values must be based on measured processing duration.

------------------------------------------------------------------------

# Part 67 --- Retry Metadata

## 73. Retry Stream Example

``` python
def schedule_retry(
    r,
    fields,
    stream_id,
    attempt,
    reason,
):
    retry_stream = (
        "tutorial:chapter33:"
        "orders:retry"
    )

    retry_after = (
        time.time()
        + min(
            60,
            2 ** attempt,
        )
    )

    r.xadd(
        retry_stream,
        {
            "event_id":
                fields["event_id"],
            "original_stream_id":
                stream_id,
            "attempt":
                str(attempt),
            "retry_after":
                str(retry_after),
            "failure_class":
                reason,
        },
    )
```

This demonstrates metadata design; a complete retry scheduler still
needs to enforce `retry_after`.

------------------------------------------------------------------------

# Part 68 --- Poison Event

## 74. Publish

``` redis
XADD tutorial:chapter33:orders * event_id poison-1 event_version 999 event_type order.created order_id 9999
```

Classify unsupported version as non-retryable according to lab policy.

------------------------------------------------------------------------

# Part 69 --- DLQ Function

## 75. Example

``` python
def send_to_dlq(
    r,
    stream_id,
    fields,
    attempt,
    reason,
):
    r.xadd(
        "tutorial:chapter33:"
        "orders:dlq",
        {
            "event_id":
                fields.get(
                    "event_id",
                    "",
                ),
            "original_stream_id":
                stream_id,
            "event_type":
                fields.get(
                    "event_type",
                    "",
                ),
            "attempt":
                str(attempt),
            "failure_class":
                reason,
            "failed_at":
                str(time.time()),
        },
    )
```

------------------------------------------------------------------------

# Part 70 --- Idempotency Lab

## 76. Learning Marker

``` python
def first_processing(
    r,
    event_id,
):
    key = (
        "tutorial:chapter33:"
        f"dedupe:{event_id}"
    )

    return bool(
        r.set(
            key,
            "1",
            nx=True,
            ex=3600,
        )
    )
```

Run the same event twice.

The second call should be detected as a duplicate within the one-hour
lab window.

------------------------------------------------------------------------

# Part 71 --- Idempotency Limitation

## 77. Important

The lab marker is not a universal exactly-once solution.

Problems include:

``` text
marker expiry
business-write race
Redis outage
marker loss
cross-system atomicity
```

Use an authoritative transactional/idempotent design for critical
business effects.

------------------------------------------------------------------------

# Part 72 --- DLQ Replay Lab

## 78. Procedure

1.  Fix the simulated consumer bug.
2.  Read one DLQ entry.
3.  Preserve `event_id`.
4.  Republish one corrected/replay event.
5.  Verify idempotency.
6.  Confirm success.
7.  ACK/delete/mark DLQ entry according to design.
8.  Increase replay batch gradually.

------------------------------------------------------------------------

# Part 73 --- Outage Backlog Lab

## 79. Procedure

1.  Stop consumers.
2.  Produce events for a fixed period.
3.  Record producer rate.
4.  Measure backlog.
5.  Restart one consumer.
6.  Measure processing rate.
7.  Add consumers gradually.
8.  calculate net catch-up.
9.  compare predicted vs. observed recovery.

------------------------------------------------------------------------

# Part 74 --- Catch-Up Calculator

## 80. Python

``` python
backlog = 900000
producer_rate = 500
consumer_rate = 800

net = (
    consumer_rate
    - producer_rate
)

if net <= 0:
    print(
        "Cannot catch up"
    )
else:
    seconds = backlog / net

    print(
        "catch-up seconds:",
        round(seconds, 1),
    )
```

------------------------------------------------------------------------

# Part 75 --- Recovery Pacing Lab

## 81. Compare

Run catch-up with:

``` text
1 consumer
2 consumers
4 consumers
```

Measure:

``` text
Redis CPU
dependency latency
dependency errors
processing rate
lag reduction
```

Stop scaling when another dependency becomes the bottleneck.

------------------------------------------------------------------------

# Part 76 --- Failure Injection

## 82. Failure 1 --- Consumer Crash

Crash after receiving but before ACK.

Verify PEL recovery.

------------------------------------------------------------------------

## 83. Failure 2 --- Crash After Business Commit

Simulate business success then crash before ACK.

Reclaim and verify idempotency prevents duplicate effect.

------------------------------------------------------------------------

## 84. Failure 3 --- Reclaim Too Early

Set an artificially low lab reclaim threshold.

Run a slow healthy consumer.

Observe duplicate concurrent processing risk.

------------------------------------------------------------------------

## 85. Failure 4 --- Infinite Retry

Retry a deterministic poison event without cap.

Observe amplification.

Then apply bounded attempts and DLQ.

------------------------------------------------------------------------

## 86. Failure 5 --- Retry Storm

Make a downstream dependency fail for all consumers.

Retry aggressively.

Observe increased request volume.

Add backoff/jitter and concurrency limits.

------------------------------------------------------------------------

## 87. Failure 6 --- DLQ Replay Storm

Replay many DLQ events simultaneously.

Observe downstream pressure.

Repeat with bounded replay.

------------------------------------------------------------------------

## 88. Failure 7 --- Deduplication Window Too Short

Use a very short marker TTL.

Wait for expiry.

Replay the same event.

Observe that duplicate suppression no longer exists.

------------------------------------------------------------------------

## 89. Failure 8 --- Fleet Outage

Stop all consumers while producer continues.

Measure backlog and recovery.

------------------------------------------------------------------------

## 90. Failure 9 --- Insufficient Catch-Up Capacity

Configure consumer throughput equal to or below producer throughput.

Observe that backlog never converges.

------------------------------------------------------------------------

## 91. Failure 10 --- Retention Shorter Than Recovery Objective

In a disposable lab, configure retention incompatible with the planned
outage window.

Demonstrate why retention and recovery objectives must be designed
together.

------------------------------------------------------------------------

# Part 77 --- Troubleshooting

## 92. Pending Count Increasing

Check:

``` text
consumer processing time
consumer errors
ACK failures
dependency latency
consumer crashes
```

------------------------------------------------------------------------

## 93. Old Pending Age Increasing

Check:

``` text
dead consumer
stuck processing
recovery worker
reclaim threshold
poison event
```

------------------------------------------------------------------------

## 94. Reclaim Rate High

Check:

``` text
consumer instability
threshold too low
processing slowdown
node/pod churn
network failures
```

High reclaim rate is not normal success.

------------------------------------------------------------------------

## 95. Retry Rate High

Check:

``` text
dependency outage
bad deployment
timeout settings
rate limiting
poison events
```

------------------------------------------------------------------------

## 96. DLQ Growing

Group by:

``` text
failure class
event type
producer version
consumer version
```

Look for systemic patterns.

------------------------------------------------------------------------

## 97. Duplicate Effects

Check:

``` text
ACK boundary
consumer crash
reclaim
idempotency race
dedupe retention
manual replay
```

------------------------------------------------------------------------

## 98. Backlog Not Shrinking

Calculate:

``` text
consumer rate - producer rate
```

If result is zero or negative, catch-up is mathematically impossible.

------------------------------------------------------------------------

## 99. Recovery Hurts Database

Reduce:

``` text
consumer replicas
concurrency
batch size
replay rate
```

Protect the database before accelerating backlog recovery.

------------------------------------------------------------------------

# Part 78 --- Production Runbooks

## 100. Runbook --- Growing PEL

``` text
1. Measure pending count.
2. Measure oldest pending age.
3. Identify owning consumers.
4. Check consumer health.
5. Compare idle age with processing P99.
6. Recover only abandoned work.
7. Process idempotently.
8. Quarantine poison events.
9. Verify PEL declines.
10. Correct root cause.
```

------------------------------------------------------------------------

## 101. Runbook --- Retry Storm

``` text
1. Measure original vs retry rate.
2. Identify failure class.
3. Check dependency health.
4. Cap consumer concurrency.
5. Stop immediate infinite retry.
6. Apply backoff/jitter.
7. Enforce retry budget.
8. DLQ permanent failures.
9. Verify dependency recovery.
10. Restore throughput gradually.
```

------------------------------------------------------------------------

## 102. Runbook --- DLQ Growth

``` text
1. Measure DLQ growth rate.
2. Group by failure reason.
3. Identify affected producer/consumer version.
4. Stop bad producer if necessary.
5. Fix root cause.
6. Validate one quarantined event.
7. Confirm idempotency.
8. Replay bounded batch.
9. Monitor downstream.
10. Continue until backlog is resolved.
```

------------------------------------------------------------------------

## 103. Runbook --- Consumer Fleet Outage Recovery

``` text
1. Confirm Redis/stream health.
2. Measure backlog.
3. Measure producer rate.
4. Determine downstream safe capacity.
5. Calculate required consumer capacity.
6. Start consumers gradually.
7. Recover abandoned pending entries.
8. Pace retries/replay.
9. Track lag until SLO restored.
10. Review outage/catch-up capacity.
```

------------------------------------------------------------------------

## 104. Runbook --- Duplicate Processing Incident

``` text
1. Identify duplicated event ID.
2. Identify all delivery attempts.
3. Check ACK timing.
4. Check reclaim history.
5. Check idempotency record/constraint.
6. Stop unsafe replay/retry if needed.
7. Correct business state.
8. Fix idempotency design.
9. Add duplicate telemetry.
10. Re-test crash-after-commit scenario.
```

------------------------------------------------------------------------

# Part 79 --- Reliability Design Template

## 105. Fields

``` text
Stream:
Consumer group:
Owner:
Processing SLO:
Producer rate:
Peak producer rate:
Consumer capacity:
Normal P50/P95/P99:
ACK point:
Retryable errors:
Non-retryable errors:
Unknown-error policy:
Retry attempts:
Backoff:
Jitter:
Retry scheduler:
Reclaim threshold:
Recovery consumer:
Idempotency mechanism:
Deduplication window:
DLQ:
DLQ owner:
DLQ retention:
Replay procedure:
Retention window:
Maximum outage objective:
Catch-up objective:
Lag SLO:
Pending alert:
Oldest-pending alert:
Dashboard:
Runbook:
```

------------------------------------------------------------------------

# Part 80 --- Reliability Capacity Worksheet

## 106. Backlog

``` text
backlog
=
producer rate
× outage duration
```

------------------------------------------------------------------------

## 107. Net Recovery

``` text
net recovery rate
=
consumer capacity
-
live producer rate
```

------------------------------------------------------------------------

## 108. Catch-Up

``` text
catch-up time
=
backlog
/
net recovery rate
```

when net recovery is positive.

------------------------------------------------------------------------

## 109. Retry Load

Approximate:

``` text
retry attempts/sec
=
failed events/sec
× average retries
```

Model this separately from original traffic.

------------------------------------------------------------------------

# Part 81 --- Lag SLO Example

## 110. Example

``` text
Normal:
P99 processing age < 30 seconds

Warning:
oldest unprocessed age > 60 seconds for 5 minutes

Critical:
oldest unprocessed age > 5 minutes
```

Thresholds must be derived from actual business requirements.

------------------------------------------------------------------------

# Part 82 --- Recovery Readiness Review

## 111. Questions

Before production:

``` text
How long can consumers be offline?
How much backlog accumulates?
Can retention preserve it?
Can consumers catch up?
Can dependencies survive catch-up?
How are abandoned messages recovered?
How are poison events isolated?
Can DLQ be replayed safely?
How are duplicates prevented?
```

------------------------------------------------------------------------

# Production Acceptance Checklist

## 112. Reliability Engineering

-   [ ] Event lifecycle documented.
-   [ ] ACK boundary documented.
-   [ ] Normal processing P50/P95/P99 measured.
-   [ ] PEL monitored.
-   [ ] Oldest pending age monitored.
-   [ ] Reclaim threshold based on measured processing.
-   [ ] Recovery worker tested.
-   [ ] Retryable failures defined.
-   [ ] Non-retryable failures defined.
-   [ ] Unknown-failure policy defined.
-   [ ] Retry count bounded.
-   [ ] Backoff configured.
-   [ ] Jitter considered.
-   [ ] Retry amplification measured.
-   [ ] Poison-event policy tested.
-   [ ] DLQ implemented where required.
-   [ ] DLQ monitored.
-   [ ] DLQ ownership assigned.
-   [ ] Replay procedure tested.
-   [ ] Replay rate bounded.
-   [ ] Idempotency mechanism tested.
-   [ ] Crash-after-commit test passed.
-   [ ] Deduplication window justified.
-   [ ] Retention supports recovery objective.
-   [ ] Consumer outage backlog modeled.
-   [ ] Catch-up capacity measured.
-   [ ] Recovery pacing tested.
-   [ ] Lag SLO defined.
-   [ ] Reliability dashboard implemented.
-   [ ] Production runbooks validated.

------------------------------------------------------------------------

# Knowledge Validation

## 113. Questions

You should be able to answer:

1.  What does the Pending Entries List represent?
2.  Why is a pending message not automatically a failed message?
3.  What makes work abandoned?
4.  Why must reclaim thresholds be based on processing latency?
5.  What can happen if work is reclaimed too early?
6.  What does `XCLAIM` do?
7.  What does `XAUTOCLAIM` help automate?
8.  What is a recovery consumer?
9.  What is a retryable failure?
10. What is a non-retryable failure?
11. Why should unknown failures have bounded retry?
12. What is retry amplification?
13. Why is immediate infinite retry dangerous?
14. Why add backoff and jitter?
15. Why do Streams not automatically provide delayed retry scheduling?
16. What is a retry stream?
17. What is a poison event?
18. What belongs in a DLQ?
19. Why does a DLQ need an owner?
20. Why must replay be rate-limited?
21. Why preserve the business event ID during replay?
22. Why is idempotency required even with ACK?
23. What is a deduplication window?
24. Why can a Redis dedupe marker be insufficient for permanent
    correctness?
25. How do you calculate outage backlog?
26. How do you calculate net catch-up rate?
27. Why can a consumer fleet fail to catch up?
28. Why should lag SLOs use time?
29. Why must retention align with recovery objectives?
30. What must pass before stream reliability is production-ready?

------------------------------------------------------------------------

# Hands-On Acceptance Checklist

## 114. Lab Completion

-   [ ] Created Chapter 33 stream/group.
-   [ ] Generated events.
-   [ ] Created pending entries.
-   [ ] Inspected PEL.
-   [ ] Simulated consumer crash.
-   [ ] Reclaimed abandoned work.
-   [ ] Tested low reclaim threshold risk.
-   [ ] Created retry metadata.
-   [ ] Classified retryable failure.
-   [ ] Classified non-retryable failure.
-   [ ] Injected poison event.
-   [ ] Created DLQ event.
-   [ ] Tested idempotency marker.
-   [ ] Reviewed idempotency limitations.
-   [ ] Replayed one DLQ event.
-   [ ] Used bounded replay.
-   [ ] Generated outage backlog.
-   [ ] Calculated catch-up capacity.
-   [ ] Tested recovery pacing.
-   [ ] Tested infinite retry failure.
-   [ ] Tested retry storm.
-   [ ] Tested DLQ replay storm.
-   [ ] Tested short dedupe window.
-   [ ] Tested insufficient catch-up capacity.
-   [ ] Tested retention/recovery mismatch.
-   [ ] Completed ten failure scenarios.
-   [ ] Completed troubleshooting.
-   [ ] Reviewed five production runbooks.
-   [ ] Completed reliability template.
-   [ ] Completed production acceptance checklist.

------------------------------------------------------------------------

# 115. Lab Cleanup

Discover only Chapter 33 keys:

``` bash
redis-cli --scan --pattern 'tutorial:chapter33:*'
```

Review all matches before deletion.

Delete confirmed lab keys in bounded batches using:

``` redis
UNLINK <confirmed-key>
```

Potential lab keys:

``` text
tutorial:chapter33:orders
tutorial:chapter33:orders:retry
tutorial:chapter33:orders:dlq
tutorial:chapter33:dedupe:*
```

Do not use:

``` redis
KEYS tutorial:chapter33:*
FLUSHDB
FLUSHALL
```

against a shared or production database.

------------------------------------------------------------------------

# 116. Key Takeaways

1.  The Pending Entries List is the center of consumer-group recovery.
2.  Pending work is not necessarily failed work.
3.  Reclaim only when work is genuinely abandoned.
4.  Reclaim thresholds must be based on measured processing latency.
5.  Premature reclaim can create concurrent duplicate processing.
6.  Retryable and non-retryable failures must be classified explicitly.
7.  Unknown failures should not retry forever.
8.  Retry attempts consume real capacity and can amplify outages.
9.  Use bounded retries with backoff and jitter.
10. Redis Streams do not automatically provide delayed retry scheduling.
11. Poison events must be isolated so healthy work can continue.
12. A DLQ requires monitoring, ownership, retention, and replay
    procedures.
13. Never blindly replay a large DLQ.
14. Preserve business event identity through retries and replay.
15. ACK does not eliminate duplicate-processing windows.
16. Idempotency is therefore fundamental.
17. Deduplication windows must cover realistic retry/replay horizons.
18. Consumer outages require explicit backlog and catch-up modeling.
19. Recovery throughput must exceed live producer throughput to catch
    up.
20. Recovery must be paced to protect downstream systems.
21. Lag SLOs should reflect business processing age, not only message
    counts.
22. Retention must support the maximum outage and catch-up objective.
23. Oldest pending age is a critical operational signal.
24. Reliability dashboards should correlate Streams with downstream
    dependency health.
25. Production readiness means proving crash, retry, poison-event,
    replay, outage, and catch-up behavior before an incident.

------------------------------------------------------------------------

# 117. References

Validate exact consumer-group, pending-entry, claiming, trimming, and
client behavior against the Redis, Redis Enterprise, and client-library
versions deployed.

Recommended official Redis documentation areas:

-   Redis Streams
-   Redis Streams consumer groups
-   `XREADGROUP`
-   `XACK`
-   `XPENDING`
-   `XCLAIM`
-   `XAUTOCLAIM`
-   `XGROUP`
-   `XINFO`
-   `XTRIM`
-   `XADD`
-   Redis Enterprise monitoring
-   redis-py Streams APIs

------------------------------------------------------------------------

# Next Chapter

**Chapter 34 --- Redis Persistence: RDB, AOF & Durability Engineering**

Chapter 34 will cover:

-   Redis in-memory durability model
-   RDB snapshots
-   AOF
-   fsync policies
-   RDB vs. AOF tradeoffs
-   restart recovery
-   data-loss windows
-   persistence overhead
-   disk latency
-   fork/copy-on-write considerations
-   rewrite behavior
-   storage capacity
-   backup vs. persistence
-   failure injection
-   restart validation
-   troubleshooting
-   production runbooks
-   acceptance validation
