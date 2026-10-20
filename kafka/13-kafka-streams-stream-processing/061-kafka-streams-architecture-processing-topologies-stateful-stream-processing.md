# Chapter 061 — Kafka Streams Architecture, Processing Topologies and Stateful Stream Processing

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 13 — Kafka Streams and Stream Processing (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–060; Java 17+ and Kafka Streams library compatible with the selected Kafka client release  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use disposable Kafka topics, synthetic events, dedicated application IDs and an isolated Kubernetes namespace. Do not delete production Streams internal topics, change `application.id`, reset production offsets, delete RocksDB state or enable exactly-once claims without understanding the transactional boundary. Lab commands are examples requiring installed-version and security validation.

## 1. Mission and learning objectives

Build and operate a Kafka Streams Java application as a Kubernetes workload against Strimzi-managed Kafka KRaft. Learn the distinction between a **logical processor topology**, its **physical stream tasks**, **local state stores**, **changelog and repartition topics**, and **standby replicas**. Evaluate event-time windows, state restoration, task movement, Kafka transactional processing guarantees, observability and production rollback.

At the end, the learner can explain how an input record becomes an output record, locate the owner of a stateful task, inspect the topology, estimate restore time and recognize why a healthy Pod does not prove correct processing.

## 2. Architecture and data flow

```text
Kafka input topic (key = customer_id)
        |
   Source processor
        |
   filter / mapValues
        |
   groupByKey / aggregate
        |
   RocksDB state store <---- Kafka changelog topic
        |
   output processor ------> Kafka output topic
        |
   Streams application instances in Kubernetes
        |               |
   active tasks      standby replicas (optional)
        |
   Kafka KRaft cluster + consumer group + transactions
```

**Streams is a client library**, not a Kafka broker feature or a separate cluster. A Streams application runs as ordinary JVM processes, here inside Kubernetes Pods. Kafka assigns input topic partitions to stream tasks. Stateful operators materialize local state, typically backed by RocksDB and changelog topics, which support restoration after process loss.

## 3. Processor topology vs physical task

| Concept | Meaning | Reliability concern |
|---|---|---|
| `StreamsBuilder` | DSL topology construction | stable operator and store names |
| `KStream` | unbounded keyed record stream | key ordering and serialization |
| `KTable` | changelog/upsert view by key | tombstones and materialization |
| `GlobalKTable` | full table replicated per instance | memory/storage scaling |
| Stream task | physical execution unit for input partitions | assignment and skew |
| State store | local materialized processor state | disk, restore and changelog |
| Repartition topic | internal shuffle for key changes | ACL, RF, network and cost |
| Changelog topic | durable log of state updates | restore time and availability |
| Standby task | warm state copy (where configured) | cost and failure-domain placement |

Increasing Pods beyond available tasks may add no processing throughput. Scaling input partitions can increase task parallelism but may alter partition assignment, key routing and state restore behavior.

## 4. Processing guarantees and correctness

Kafka Streams offers at-least-once processing and Kafka-scoped exactly-once processing (for supported versions, `exactly_once_v2`). Kafka transactions can atomically coordinate Kafka output records and consumed offsets in supported topologies; they do **not** make arbitrary external HTTP/database side effects exactly once. Processing guarantees require compatible brokers, transactional producer authorization and adequate replication/minISR.

Record-level **business deduplication** and an independent event-ID ledger remain necessary when correctness spans external systems. Consumer lag, RUNNING state and Kafka transaction success are not a complete end-to-end integrity proof.

## 5. Event-time, windows and state

- **Event time:** timestamp extracted from record metadata or payload according to an explicit timestamp extractor.
- **Processing time:** wall-clock time when an application processes the record.
- **Grace:** accepted lateness beyond a window's nominal end; late records beyond grace may be dropped by windowed operations.
- **Suppression:** delay intermediate window results until a defined condition, trading latency and buffering for finality.
- **Retention:** window state retention must support window size plus grace and any implementation constraints.
- **State restore:** application reconstructs local stores from changelog and input records as applicable; estimate bytes, throughput and disk headroom.

A simple count by key is a useful first stateful exercise before introducing windows, joins, foreign-key lookups or interactive queries.

## 6. Runnable Java example: keyed running counts

Create a disposable Maven project. This sample intentionally uses String Serdes, a fixed input/output topic and no external sink. Pin `kafka-streams` to a version approved for the Kafka client/broker matrix.

```xml
<!-- pom.xml dependency excerpt: supply the rest of a normal Maven project -->
<dependency>
  <groupId>org.apache.kafka</groupId>
  <artifactId>kafka-streams</artifactId>
  <version>${kafka.version}</version>
</dependency>
```

```java
package sre.kafka.ch61;

import java.util.Properties;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;

public final class RunningCounts {
    public static void main(String[] args) {
        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "sre-ch61-counts-v1");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG,
                  System.getenv().getOrDefault("KAFKA_BOOTSTRAP", "localhost:9092"));
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG,
                  Serdes.String().getClass());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG,
                  Serdes.String().getClass());
        props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG,
                  StreamsConfig.AT_LEAST_ONCE);
        // Production: load TLS/SASL from approved Secrets, not source code.
        StreamsBuilder builder = new StreamsBuilder();
        builder.stream("sre-ch61-input", Consumed.with(Serdes.String(), Serdes.String()))
               .filter((key, value) -> key != null && value != null)
               .groupByKey(Grouped.with(Serdes.String(), Serdes.String()))
               .count(Materialized.as("sre-ch61-counts-store"))
               .toStream()
               .mapValues(String::valueOf)
               .to("sre-ch61-counts", Produced.with(Serdes.String(), Serdes.String()));
        Topology topology = builder.build();
        System.out.println(topology.describe());
        KafkaStreams streams = new KafkaStreams(topology, props);
        Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
        streams.start();
    }
}
```

The program emits updated per-key running counts as strings. Example input keys `customer-a`, `customer-a`, `customer-b` should yield updates 1, 2 and 1 respectively (subject to Kafka ordering within each key's partition). It does not implement deduplication by event ID; duplicate input events increase counts.

## 7. Kubernetes Deployment design sketch

The following is a **reference Deployment**, requiring a prebuilt, approved image and Kafka TLS/SASL configuration before use. The placeholder image cannot be deployed as-is.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-ch61-streams
  namespace: kafka-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: sre-ch61-streams}
  template:
    metadata:
      labels: {app: sre-ch61-streams}
    spec:
      terminationGracePeriodSeconds: 90
      containers:
        - name: streams
          image: registry.example.invalid/sre/ch61-streams@sha256:REPLACE_WITH_REAL_DIGEST
          env:
            - name: KAFKA_BOOTSTRAP
              value: sre-kafka-kafka-bootstrap.kafka-lab.svc:9093
          resources:
            requests: {cpu: "250m", memory: "512Mi"}
            limits: {cpu: "1", memory: "1Gi"}
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            capabilities: {drop: ["ALL"]}
```

A production version needs client TLS/SASL Secrets, matching listener and KafkaUser ACLs, appropriate read/write permissions for the RocksDB state directory, Pod security, probes aligned with restore behavior, topology spread, disruption policy and resource sizing. Do not mark the Deployment ready based only on Pod readiness. An ephemeral state directory is recoverable from changelogs but can make restarts expensive; PVC choices require operational tradeoff analysis.

## 8. Kubernetes-first read-only preflight

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,svc,pvc -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get deploy sre-ch61-streams -o wide
kubectl -n kafka-lab get pods -l app=sre-ch61-streams -o wide
```

A missing example Deployment is expected before installation; record **NOT DEPLOYED**, not a test pass. Production bootstrap ports and authentication differ by listener configuration.

## 9. Twenty Kubernetes-first Streams labs

### Lab 01 — Validate disposable Kubernetes context

**Procedure:** Confirm cluster context, namespace, Strimzi CRDs and change approval before any deployment.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 02 — Verify Kafka KRaft baseline

**Procedure:** Inspect Kafka, KafkaNodePool, broker/controller Pods, PVC, listeners, RF and ISR.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 03 — Design application topology

**Procedure:** Draw source, filter, mapValues, groupByKey, count, state store and sink.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 04 — Design input key and partitioning

**Procedure:** Use stable customer key, partition count, per-key ordering and serialization contract.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 05 — Review Java/Streams build

**Procedure:** Pin Kafka Streams dependency compatible with brokers and approved Java runtime; build immutable container.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 06 — Review Streams app identity

**Procedure:** Design application.id, consumer group behavior, Kafka ACLs and internal changelog/repartition topics.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 07 — Validate processing guarantee

**Procedure:** Compare at-least-once with exactly_once_v2 Kafka transactional scope and downstream external side effects.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 08 — Inspect topology graph

**Procedure:** Capture Topology.describe() output and map repartition and state-store nodes.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 09 — Design state store

**Procedure:** Select RocksDB persistent key-value store, changelog retention, local disk and restore budget.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 10 — Design window and grace policy

**Procedure:** Compare event-time timestamp extractor, tumbling/hopping/session windows, grace and late record behavior.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 11 — Design materialization and query model

**Procedure:** Plan named state store, interactive query locality, metadata and service ownership.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 12 — Review Streams Kubernetes deployment

**Procedure:** Check image digest, security context, resource requests/limits, Secret, NetworkPolicy and PodDisruptionBudget.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 13 — Inspect task assignment

**Procedure:** Map stream tasks to topic partitions, active tasks, standby replicas and instance count.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 14 — Measure consumer and processing lag

**Procedure:** Collect records-lag-max, commit latency, processing rate, task count and end-to-end freshness.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 15 — Model Pod restart

**Procedure:** Predict task migration, RocksDB state restore, changelog replay and at-least-once duplicates.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 16 — Model disk pressure

**Procedure:** Review RocksDB write amplification, state dir/PVC or ephemeral storage and eviction safeguards.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 17 — Model partition scaling

**Procedure:** Assess task redistribution, repartition topics, key routing, changelog state and rollout compatibility.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 18 — Model poison-pill record

**Procedure:** Define deserialization exception handler policy, DLQ or quarantine design and loss accounting.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 19 — Review upgrade and rollback

**Procedure:** Validate topology compatibility, state store naming, application.id and savepoint-like expectations.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

### Lab 20 — Complete reliability acceptance

**Procedure:** Reconcile input IDs/output counts, SLO, restore RTO, security evidence and independent reviewer.

**Validation:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, topology output, expected/observed key counts, active/standby task placement, processing lag, state restore, security boundary, rollback/abort and independent reviewer. Record **Pending** until live execution. Pod failure, topic partition changes and state deletion remain tabletop without an approved disposable test plan.

## 10. Read-only verification script

Save as `verify-ch61.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/8] Context'; kubectl config current-context
echo '[2/8] Kafka KRaft'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/8] Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/8] Services'; kubectl -n "$NS" get svc -o wide
echo '[5/8] Storage'; kubectl -n "$NS" get pvc -o wide
echo '[6/8] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[7/8] Streams app'
if kubectl -n "$NS" get deploy sre-ch61-streams >/dev/null 2>&1; then
  kubectl -n "$NS" get deploy sre-ch61-streams -o wide
  kubectl -n "$NS" get pods -l app=sre-ch61-streams -o wide
else
  echo 'NOT DEPLOYED: sre-ch61-streams'
fi
echo '[8/8] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only Kubernetes inventory.'
echo 'NOT PROVEN: topology correctness, event counts, state restore, SLO or security review.'
```

Run `chmod +x verify-ch61.sh && ./verify-ch61.sh | tee evidence-ch61/preflight.txt`. A script exit code of zero means inventory commands succeeded, **not** that Streams workloads or stateful processing have been validated.

## 11. Twelve troubleshooting scenarios

### Scenario 1 — Streams Pod CrashLoopBackOff

**Diagnosis:** Inspect Java logs, bootstrap TLS/SASL, topology exceptions and memory. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 2 — Task stuck in REBALANCING

**Diagnosis:** Inspect member churn, assignor logs, cooperative rebalance, network and broker health. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 3 — RocksDB state restore takes too long

**Diagnosis:** Inspect changelog size, restore throughput, state.dir storage and standby placement. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 4 — Consumer lag increases

**Diagnosis:** Inspect CPU, GC, poll latency, downstream producer throttling and partition skew. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 5 — Unexpected output duplicates

**Diagnosis:** Review processing.guarantee, transaction commit, replay and external sink idempotency. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 6 — Missing events after exception

**Diagnosis:** Review deserialization/processing exception handlers, skip policies and event-ID ledger. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 7 — State store corrupted or missing

**Diagnosis:** Inspect filesystem health, changelog availability and supported rebuild procedure. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 8 — Disk full in state directory

**Diagnosis:** Inspect RocksDB compaction, changelog growth, pod ephemeral limits and volume capacity. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 9 — Windowed aggregation incorrect

**Diagnosis:** Inspect event-time timestamps, grace, timezone and late-event policy. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 10 — Repartition topic ACL denied

**Diagnosis:** Check application.id derived internal topic names and least privilege. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 11 — Topology upgrade breaks state compatibility

**Diagnosis:** Review store names, serdes, changelog schema and safe versioned rollout. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

### Scenario 12 — Interactive query returns stale/partial data

**Diagnosis:** Review active task ownership, standby staleness, metadata routing and SLO. Correlate Kafka quorum/ISR, Streams thread/task state, consumer lag, RocksDB storage, changelog offsets, topology metadata, JVM logs and input/output event IDs. **Response:** Preserve state and internal topics, protect Kafka durability, use approved rollout/rollback and validate counts after recovery. **Evidence:** UTC timeline, redacted diagnostics, observed vs expected result and reviewer.

## 12. Eight production runbooks

### Runbook A — Streams app readiness and preflight

**Trigger and response:** Check Kafka quorum/ISR, namespace, app identity, image, TLS, ACL and input/output topics. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook B — Processing lag and throughput regression

**Trigger and response:** Review records-lag-max, task assignment, partition skew, CPU/GC, downstream backpressure and rollback. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook C — State store recovery

**Trigger and response:** Review changelog, RocksDB state.dir, restore progress, standby, storage and RTO. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook D — Rebalance and Pod loss

**Trigger and response:** Correlate Pod eviction, consumer group transitions, task reassignment and output integrity. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook E — Event-time and window correctness

**Trigger and response:** Verify timestamp extractor, window boundaries, grace, suppression and late-record accounting. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook F — Poison-pill and serialization incident

**Trigger and response:** Quarantine payloads, preserve IDs, inspect serde/handler policy and replay safely. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook G — Topology change and rollback

**Trigger and response:** Review application.id, store names, serde compatibility, versioned rollout and state migration. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

### Runbook H — SLO recovery and acceptance

**Trigger and response:** Reconcile input/output IDs, restore lag, delivery guarantees, RCA, security and independent approval. **Safety:** No production application.id change, offset reset, internal topic deletion, RocksDB state wipe, ACL bypass or unapproved topology migration. **Exit:** Healthy tasks, bounded lag and restore, reconciled counts and IDs, recovered SLO, RCA and independent approval.

## 13. Operational SLI/SLO design

| Signal | Measurement | Alert concept |
|---|---|---|
| Input-to-output freshness | source timestamp to output acknowledgment | sustained breach of approved freshness budget |
| Records lag | max lag per Streams task/partition | persistent upward trend |
| State restoration | bytes remaining / restore throughput | restore projected beyond RTO |
| Thread/task health | RUNNING vs ERROR/REBALANCING | failed task or prolonged rebalance |
| Processing errors | deserialize/processing/production exceptions | nonzero error rate or silent skips |
| RocksDB/storage | disk usage, compaction, write stall | approaching volume headroom |
| Event integrity | accepted IDs vs output IDs and expected counts | missing/duplicate business effects |

Metrics/JMX names and reporter support vary by Kafka Streams client version. Define SLOs with business owners; no numeric threshold is universally safe.

## 14. Evidence package

```text
evidence-ch61/
  approved-streams-charter.md
  context-kafka-streams-jdk-version-matrix.md
  preflight.txt
  kraft-isr-storage-baseline.md
  topology-diagram-and-describe.txt
  input-key-partition-contract.md
  pom-and-immutable-image-provenance.md
  streams-app-identity-kafka-acl.md
  processing-guarantee-boundary.md
  state-store-changelog-retention.md
  event-time-window-grace-design.md
  interactive-query-ownership.md
  deployment-security-resource-review.md
  task-assignment-standby-plan.md
  streams-jmx-lag-slo.md
  pod-loss-state-restore-tabletop.md
  rocksdb-disk-pressure-tabletop.md
  partition-scaling-tabletop.md
  poison-pill-policy.md
  topology-upgrade-rollback.md
  input-output-event-ledger.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

Every artifact must include exact version, UTC timestamp, expected/observed result, **Live** vs **Tabletop**, redaction, owner, rollback and independent reviewer.

## 15. 100-point Kafka Streams SRE assessment

| Domain | Points | Critical |
|---|---:|---|
| Architecture, topology and key contract | 15 | Yes |
| Strimzi/KRaft/Kubernetes security and deployment | 15 | Yes |
| Stream tasks, partitioning and rebalance | 10 | Yes |
| Stateful RocksDB/changelog and restore | 15 | Yes |
| Processing guarantee and event integrity | 15 | Yes |
| Event-time/windows and serialization | 10 | Yes |
| Metrics, lag and capacity SLO | 10 | Yes |
| Runbooks, rollback and incident response | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated execution, deleted internal topics, unreviewed state reset, missing event integrity, secret exposure, unsupported external exactly-once claims or absent independent review.

## 16. Cleanup, references and next chapter

Remove only chapter-owned synthetic input/output topics, application resources and alerts after approval and evidence retention. Preserve internal changelog/repartition topics and state until the application is intentionally retired with an approved procedure.

**References:** [Apache Kafka Streams](https://kafka.apache.org/documentation/streams/), [Kafka Streams Developer Guide](https://docs.confluent.io/platform/current/streams/developer-guide/overview.html), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/).

**Next:** Chapter 062 — Kafka Streams Stateless Processing, Joins, Aggregations and Event-Time Windows.

---

**Verification boundary:** Publication proves document availability only. Live topology execution, state restore, correctness, security and independent SRE acceptance remain Pending.
