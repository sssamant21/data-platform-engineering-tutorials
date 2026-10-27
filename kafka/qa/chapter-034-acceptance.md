# Chapter 034 broker metrics, controlled IO tuning and effective rollback

The independent runner `python kafka/qa/run_chapter_034.py` uses the chapter-specific
persistent Kafka4.0.0/KRaft/Strimzi0.47.0 fixture. Its JMX exporter is configured before
broker startup, exposes only internal port9404, and does not modify successful prior
fixtures. Clients retain SCRAM-SHA-512 over TLS, hostname verification, scoped ACLs,
non-root resource limits and token-free ServiceAccounts. Cluster DescribeConfigs is an
explicit additional read-only client privilege; clients have no AlterConfigs privilege.

The six measured trials repeat baseline8 versus candidate10 IO threads three times in
alternating order. Each uses a fresh six-partition RF3/minISR2 topic,1200 deterministic
1KiB records, fixed400records/s offered cap, acks=all, idempotence, unchanged native
client settings, exact payload/byte reconciliation and captured committed catch-up.
A separate120record warmup is excluded from statistics. Neither improvement nor a
production configuration selection is asserted.

Each change is a minimal Strimzi Kafka resource JSON patch with UID, resourceVersion
and full-spec tests, preceded by server dry-run. The dedicated chapter annotation,
kind node, Kafka version and durability settings are mandatory. Observed generation
and Ready must converge; a stale Ready condition cannot authorize load. Actual Admin
DescribeConfigs must show the expected effective value on all three brokers before
and after load. Every attempt has a finally rollback through Strimzi, followed by a
fresh owned verification Job proving effective8, RF3/fullISR and KRaft health. Changed
broker UIDs/restarts fail the experiment. No Pod, broker JVM, PVC or segment file is
manually mutated, and security/replication settings are never reduced.

Actual per-broker HTTP JMX samples are captured before, during and after native load.
All three brokers require finite nonnegative request counts and stage p95/p99 samples
for Produce, FetchConsumer and FetchFollower, positive traffic deltas, full replication
health, network idle fractions, raw combined-role handler meter, approved actual heap maximum and JVM GC
cumulative count/time in milliseconds. Missing telemetry fails the supported measurement rather than
being filled with zero. Raw timestamped samples remain in logs. Per-broker reservoir
percentiles include background activity; they are neither averaged across brokers nor
presented as isolated interval or business-handler p99. Cumulative GC deltas do not
prove pause p99 or allocation behavior. The approved heap/container difference is a
budget, not measured free memory or page cache.

Read-only broker cgroup CPU/throttling counters, memory.current and raw io.stat are
captured around the whole trial/reconciliation harness. Their scope explicitly includes
monitoring and operator work. Block-device counters are not attributed to a specific
PVC and cannot establish cloud IOPS limits, latency, burst credits or CSI reliability.
The common fixture inventory verifies actual persistent bindings, readiness, disk
headroom, resource pressure and stable broker identities. Native process health polling
aborts on full-ISR/leader/quorum violations. Instrumentation failures fail acceptance;
all clients, Jobs, HTTP/API/native processes and workflow execution are bounded.

JSON retains public profile/source/fixture hashes, all repeated results, effective
configuration, exact guarded transition and rollback proof, per-broker raw/derived
measurements, failed stages and diagnostics. Shared producer behavior is reused by a
validated source bundle rather than copied. The changed-chapter selector chooses the
new metrics fixture; the default producer/consumer harness behavior is unchanged.

Single-host kind has shared storage and dual-role brokers. This is supported functional
instrumentation and an operator-managed configuration/rollback microbenchmark, not
production capacity or enterprise certification. JVM/resource rolling experiments,
allocation profiling, GC pause distributions, attributed node page cache, provider disk
latency/IOPS, sustained load, quota fairness, TLS/plaintext overhead comparisons and
independent signoff remain NOT_EXECUTED/PENDING. Full manuscript assessment remains
NOT_YET_ACCEPTED and enterprise certification NOT_CERTIFIED.

Version-specific references: [Kafka4 broker settings](https://kafka.apache.org/40/generated/kafka_config.html#num.io.threads),
[tagged dynamic thread configuration](https://github.com/apache/kafka/blob/4.0.0/core/src/main/scala/kafka/server/DynamicBrokerConfig.scala),
[Strimzi0.47 configuration](https://strimzi.io/docs/operators/0.47.0/configuring.html),
[tagged exporter mappings](https://github.com/strimzi/strimzi-kafka-operator/blob/0.47.0/examples/metrics/kafka-metrics.yaml).

Kafka4 combined-mode metric correction: the [broker pool](https://github.com/apache/kafka/blob/4.0.0/core/src/main/scala/kafka/server/BrokerServer.scala)
and [controller pool](https://github.com/apache/kafka/blob/4.0.0/core/src/main/scala/kafka/server/ControllerServer.scala)
use the same RequestHandlerAvgIdlePercent meter name. Each pool records time normalized
by its own thread count in [KafkaRequestHandler](https://github.com/apache/kafka/blob/4.0.0/core/src/main/scala/kafka/server/KafkaRequestHandler.scala).
The combined raw MeanRate was about1.97 on the first run. It is retained without
clamping, division or a false broker-only0..1 bound. Broker-only handler saturation
remains NOT_ISOLATED; network idle and all health/configuration/data checks retain
their independent assertions. Heap and GC beans are explicitly mapped from java.lang Memory/GarbageCollector; the first exporter did not provide the assumed default JVM collector series. The failed first attempt is preserved.
