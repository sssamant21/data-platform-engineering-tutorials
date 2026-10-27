# Chapter 035 bounded application performance and recovery capstone

The independent runner integrates three fresh application repetitions with six matched
secure broker IO-thread microbenchmarks. It reuses the validated persistent metrics
fixture and accepted security/native tools/consumer replay helpers through trusted
source bundles. The shared broker helper now uses its actual chapter number in log
paths, preserving Chapter034 behavior. Fixture ownership annotation034 identifies the
inherited instrumented disposable fixture; it does not authorize another cluster.

Each application repetition uses a fresh six-partition RF3/minISR2 topic/group and a
new file on a uniquely owned non-broker standard/RWO sink PVC.1200 distinct sequential
IDs are explicitly round-robin partitioned, with1024byte padded synthetic values and
Kafka CreateTime. Producer acks=all/idempotence, SCRAM over TLS, hostname validation,
manual consumer commits, immutable images, token-free non-root clients and bounded
resources remain mandatory. This application payload/distribution is separate from
the native random-payload microbenchmark; their rates are not compared as equivalent.

Four short functional phases generate120warmup records at cap100/s,360baseline at
200/s,360burst at400/s while the actual consumer is paused after a confirmed barrier,
and360recovery at100/s after release. Counts and offered caps are fixed, while actual
elapsed/acknowledged rates are measured. The consumer continues polling while paused.
The test must observe the exact360record committed backlog, sample positive net drain
while new ingress is still arriving, and finish with all six committed offsets equal
to captured ends200. No offsets are reset or directly altered.

The consumer validates every event and key/partition, runs a one-millisecond synthetic
handler, writes a single-writer ledger, forces the file, then commits processed offsets.
Accepted IDs must match the reloaded durable ledger exactly, with duplicates classified
and no missing accepted IDs. Raw created/forced-completion timestamps, handler+force
samples and producer send-to-success wait samples are retained. Reported nearest-rank
p50/p95/p99/max are independently reconciled against those raw samples. Producer wait,
handler+fsync time, event age and committed lag are separate measurements. Ledger file
timestamps are sink-attempt times; forced-completion timestamps come from actual
post-force observations. Shared-clock CreateTime/event-age is not distributed clock
certification or an external database commit SLA.

Actual per-broker JMX samples and ISR/quorum health polling run during application
processing. Application client cgroup snapshots remain distinct from broker metrics.
Lag samples preserve captured ends, commits, accepted and forced counts and timing.
The early observed committed-lag decline supplies an explicitly sampled net-drain
estimate; it is not inferred from native fetch throughput or fitted to the entire
recovery window. Batching and sampling limitations remain visible.

A separate120record topic exercises the accepted forced-file checkpoint/exit23 before
commit, fresh-process reload, twelve replay attempts suppressed and exact committed
catch-up. The owned failed Job/Pod UID relationship, checkpoint and exact exit23 are
required. OOM/authentication/other failures cannot pass as fault injection. Every
application/replay Pod must mount the same verified owned PVC/PV UID/node binding.
Only this synthetic sink is written; broker PVCs/segments are never edited or deleted.
This is process-level at-least-once/idempotent-file evidence, not DB exactly-once,
node/power-loss durability, attachment failover or multi-zone certification.

After functional phases, the six accepted matched broker trials use unchanged secure
native tools and actual per-broker request/JVM/GC/cgroup observations. Candidate8→10
IO threads and every finally rollback to8 use UID/resourceVersion/full-spec guarded
Strimzi patches, server dry-run, observed-generation readiness and fresh effective
configuration verification. Broker identities/restarts, fullISR and quorum must hold.
No direct broker Pod/JVM mutation or reliability/security reduction is permitted.

The additional functional budget is3720 x1024byte values, separately reported from
native trial payloads. All Jobs, HTTP/API/native clients, catch-up and the40minute
workflow are bounded. Evidence is sanitized before upload, with source/config/fixture
hashes and failed stages retained. Prior chapter successes are historical provenance,
never substituted for fresh same-head capstone results.

The capacity model reproduces the manuscript arithmetic as ILLUSTRATIVE, excluding
index/record overhead, retries/recovery, retention behavior and reserve capacity.
Its per-broker average applies only if balanced; it is not measured sizing.

Supported CI acceptance is deliberately narrower than full manuscript acceptance.
Application groups use one actual consumer each; the complete producer/consumer tuning
matrices and1/3/6/8member scaling sweep are not rerun here. The representative30minute
soak is BLOCKED_NOT_EXECUTED because required provider latency, page-cache attribution
and approved representative telemetry are absent. Business SLO approval, independent
assessor, broker-only handler saturation isolation, cloud/CSI reliability and production
capacity remain pending. Score is null, full capstone NOT_YET_ACCEPTED, enterprise
NOT_CERTIFIED. A supported runtime PASS never changes those open gates.

References: [Kafka4 consumer settings](https://kafka.apache.org/40/configuration/consumer-configs/),
[Kafka4 broker settings](https://kafka.apache.org/40/generated/kafka_config.html),
[Strimzi0.47 configuration](https://strimzi.io/docs/operators/0.47.0/configuring.html).
