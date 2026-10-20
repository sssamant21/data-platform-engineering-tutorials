# Chapter 062 — Kafka Streams Stateless Processing, Joins, Aggregations and Event-Time Windows

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 13 — Kafka Streams and Stream Processing (2/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–061, especially Chapter 061 Streams architecture  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use synthetic records and isolated Kafka topics with a dedicated Streams `application.id`. Do not change production input partitions, delete internal changelog/repartition topics, reset offsets, wipe RocksDB state or claim external exactly-once side effects. Review client/broker/Strimzi compatibility and Kubernetes RBAC/TLS/SASL/ACL before deployment.

## 1. Mission and learning objectives

Build a Kafka Streams topology that performs stateless transformations, key-based joins, stateful aggregations and event-time windowed counts on Kubernetes. Explain temporal join semantics, repartition costs, local state, grace periods, late events, suppression and the correctness boundary of Kafka Streams exactly-once processing.

By the end, an SRE should be able to troubleshoot a missing join, distinguish a late event from lost data, estimate RocksDB and repartition capacity, and reconcile input event IDs with the intended output.

## 2. Architecture

```text
orders topic ------> filter/mapValues --+-- groupByKey / count --> changelog
                                        |
customers topic --> KTable materialize -+-- KStream-KTable join
                                        |
payments topic ---> KStream-KStream windowed join
                                        |
                           event-time window aggregate
                                        |
                       output Kafka topic + event ledger
                                        |
                      Strimzi KRaft / Kubernetes Streams Pods
```

Kafka Streams is a **client-side Java library**, not a broker-side execution engine. Joins and aggregations run in stream tasks distributed among application instances. Repartition topics shuffle keys when required; changelog topics protect state-store recovery.

## 3. Stateless transformations

| Operator | Behavior | Operational concern |
|---|---|---|
| `filter` / `filterNot` | include/exclude records | skipped-event accounting |
| `mapValues` | change value, preserve key | schema and data semantics |
| `map` | change key/value | repartition risk downstream |
| `flatMapValues` | zero/many values for one input | fan-out, memory and SLO |
| `peek` | observe records | side effects and privacy |
| `split` / `branch` | route by predicate | unmatched records and topic ACL |

Avoid external writes from stateless callbacks unless they are explicitly idempotent and failure-tested. Kafka Streams transactions do not encompass arbitrary HTTP/database effects.

## 4. Join semantics and correctness

| Join | Data model | Timing behavior | Key risk |
|---|---|---|---|
| KStream–KStream | two event streams | time-windowed, out-of-order events may join within grace | co-partitioning and event-time |
| KStream–KTable | event stream with current table view | lookup uses table state available when stream record is processed | table update order and missed lookups |
| KTable–KTable | two changelog tables | updates propagate as tables change | tombstones and materialization |
| KStream–GlobalKTable | stream with fully replicated table | local lookup; independent input partitioning | full-table replication cost |

A KStream–KTable join is **not** a historical temporal lookup unless the application explicitly implements that behavior. For KStream–KStream joins, Kafka Streams requires compatible partitioning/key serialization; join windows, grace and null-result timing must be reviewed for the specific client version.

## 5. Aggregations, windows and grace

- **Count:** a per-key stateful aggregation backed by a materialized store and changelog.
- **Tumbling:** fixed, non-overlapping windows (e.g. 5-minute windows).
- **Hopping:** overlapping windows, potentially generating multiple aggregates per input.
- **Session:** activity-based windows that merge when events fall within an inactivity gap.
- **Grace:** allowed lateness after a window end; beyond grace, late events may be dropped.
- **Suppression:** hold intermediate results until window close or another trigger; assess buffer size and latency.
- **Retention:** must support the window size plus grace and relevant implementation constraints.

Use event-time timestamps with explicit extraction policy. A clock-skewed producer, missing timestamp or replayed old event can change window membership. Count every intentionally filtered, dropped or quarantined record in the event integrity ledger.

## 6. Java topology: stateless filter and tumbling-window counts

This example uses String Serdes and event timestamps from Kafka record metadata. The Maven project must supply a compatible Kafka Streams dependency and a normal Java build. The Kafka bootstrap address is supplied by environment; production TLS/SASL requires an approved Secret-based configuration.

```java
package sre.kafka.ch62;

import java.time.Duration;
import java.util.Properties;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Grouped;
import org.apache.kafka.streams.kstream.Materialized;
import org.apache.kafka.streams.kstream.Produced;
import org.apache.kafka.streams.kstream.TimeWindows;
import org.apache.kafka.streams.kstream.Windowed;
import org.apache.kafka.streams.kstream.WindowedSerdes;

public final class WindowedCounts {
    public static void main(String[] args) {
        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "sre-ch62-windowed-v1");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG,
            System.getenv().getOrDefault("KAFKA_BOOTSTRAP", "localhost:9092"));
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG,
            Serdes.String().getClass());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG,
            Serdes.String().getClass());

        StreamsBuilder builder = new StreamsBuilder();
        builder.stream("sre-ch62-orders", Consumed.with(Serdes.String(), Serdes.String()))
            .filter((key, value) -> key != null && value != null && !value.isBlank())
            .groupByKey(Grouped.with(Serdes.String(), Serdes.String()))
            .windowedBy(TimeWindows.ofSizeAndGrace(Duration.ofMinutes(5),
                                                    Duration.ofMinutes(1)))
            .count(Materialized.as("sre-ch62-five-minute-counts"))
            .toStream()
            .to("sre-ch62-windowed-counts",
                Produced.with(WindowedSerdes.timeWindowedSerdeFrom(String.class, 300000L),
                              Serdes.Long()));

        KafkaStreams streams = new KafkaStreams(builder.build(), props);
        Runtime.getRuntime().addShutdownHook(new Thread(streams::close));
        streams.start();
    }
}
```

The example counts each accepted nonblank record per key and five-minute window; the output key is a **windowed key**. Its time-windowed serde and retention behavior must be validated with the chosen Kafka Streams version. It does not implement joins, deduplication, or suppression; those are separate lab extensions. To compare results, normalize window start/end and use a deterministic synthetic timestamp fixture.

## 7. Join pseudocode (version-dependent)

```java
// Illustrative DSL only; validate overloads and Serdes for your client version.
// KStream<String, Order> orders = ...
// KTable<String, Customer> customers = ...
// KStream<String, EnrichedOrder> enriched =
//     orders.join(customers, (order, customer) -> enrich(order, customer));
//
// KStream<String, Payment> payments = ...
// KStream<String, Reconciled> matched =
//     orders.join(payments,
//         (order, payment) -> reconcile(order, payment),
//         JoinWindows.ofTimeDifferenceAndGrace(
//             Duration.ofMinutes(5), Duration.ofMinutes(1)),
//         StreamJoined.with(orderKeySerde, orderValueSerde, paymentValueSerde));
```

When testing joins, capture the expected key, partition, event timestamp, window, match status, and number of output records. Explicitly test unmatched, duplicate, late and null/tombstone cases.

## 8. Kubernetes/Strimzi deployment review

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,svc,pvc -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get deploy sre-ch62-streams -o wide
```

Deploy a signed immutable image using GitOps, least-privilege KafkaUser ACLs for source/output/internal topics, nonroot security context, explicit CPU/memory requests, sufficient state-dir storage, PodDisruptionBudget and topology spread. Kafka Streams application Pods are not managed automatically by the Strimzi Kafka CR. A missing sample Deployment is expected before installation.

## 9. Twenty Kubernetes-first processing labs

### Lab 01 — Approve Streams exercise charter

**Procedure:** Document synthetic topic owners, processing semantics, data classifications, SLO, recovery and abort gates.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 02 — Inventory Strimzi Kafka and Kubernetes

**Procedure:** Read context, Kafka/KafkaNodePool CRDs, KRaft health, topic RF/ISR, PVC, Pods and policies.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 03 — Pin Kafka Streams client and JDK

**Procedure:** Record approved library/JDK versions, build dependencies, SBOM and immutable image digest.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 04 — Design stable event key

**Procedure:** Define key partitioning, event IDs, schema, timestamp and deterministic ordering assumptions.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 05 — Implement stateless filter

**Procedure:** Validate invalid/null event filtering and event-ID loss accounting.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 06 — Implement mapValues and flatMapValues

**Procedure:** Review one-to-one and one-to-many transformations, keys, fan-out and memory bounds.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 07 — Design branching and routing

**Procedure:** Compare split/branch semantics, unmatched records, downstream topic ACL and DLQ policy.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 08 — Validate KStream-to-KStream join

**Procedure:** Define co-partitioning, same-key matching, join window, grace, out-of-order and null semantics.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 09 — Validate KStream-to-KTable join

**Procedure:** Review table update semantics, lookup at stream event processing time and unmatched keys.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 10 — Review KTable-to-KTable join

**Procedure:** Assess changelog update propagation, materialization, tombstones and store sizing.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 11 — Build count and aggregate topology

**Procedure:** Define initializer/aggregator, key grouping, store name, changelog and dedup contract.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 12 — Review repartition topics

**Procedure:** Inspect key-changing operations, internal topic RF/ACL, network and disk costs.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 13 — Design tumbling window

**Procedure:** Select event-time timestamp extractor, window size, grace and retention.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 14 — Design hopping and session windows

**Procedure:** Compare overlapping windows, inactivity gaps, late merges and output volume.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 15 — Review suppression and final results

**Procedure:** Estimate suppression buffer growth, final window semantics and latency tradeoff.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 16 — Validate out-of-order and late events

**Procedure:** Define allowed lateness, discarded events, late-event SLI and replay policy.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 17 — Review deployment resource sizing

**Procedure:** Check Pod CPU/memory, RocksDB disk, state restore, topology spread and disruption.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 18 — Model rebalance and state recovery

**Procedure:** Rehearse active/standby task migration, changelog restoration and join/window correctness.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 19 — Review topology evolution and rollback

**Procedure:** Assess store names, serialization, repartition topics, application.id and safe release plan.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

### Lab 20 — Complete event integrity acceptance

**Procedure:** Reconcile input IDs, filtered IDs, join matches, window aggregates and output IDs with independent review.

**Acceptance evidence:** Capture exact Kafka/Strimzi/Streams/JDK versions, approved Kubernetes context, UTC command, expected/observed input/output IDs, key/window/join matrix, task and state-store metrics, security impact, rollback/abort and independent reviewer. Mark **Pending** until executed. Failure injection, repartition changes and state deletion are tabletop unless approved in a disposable environment.

## 10. Read-only Kubernetes verification script

Save as `verify-ch62.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/8] Context'; kubectl config current-context
echo '[2/8] Kafka/KRaft'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/8] Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/8] Storage'; kubectl -n "$NS" get pvc -o wide
echo '[5/8] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[6/8] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[7/8] Streams deployment'
if kubectl -n "$NS" get deploy sre-ch62-streams >/dev/null 2>&1; then
  kubectl -n "$NS" get deploy sre-ch62-streams -o wide
  kubectl -n "$NS" get pods -l app=sre-ch62-streams -o wide
else
  echo 'NOT DEPLOYED: sre-ch62-streams'
fi
echo '[8/8] KafkaUser metadata'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo 'PASS: read-only Kubernetes inventory.'
echo 'NOT PROVEN: joins, window correctness, late events, state restore or independent review.'
```

Run `chmod +x verify-ch62.sh && ./verify-ch62.sh | tee evidence-ch62/preflight.txt`. A successful inventory exit code is **not** a processing correctness pass.

## 11. Twelve troubleshooting scenarios

### Scenario 1 — Join produces zero matches despite input records

**Diagnosis:** Check key serdes, co-partitioning, event-time window and timestamp extractor. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 2 — Stream-table join unexpectedly misses prior value

**Diagnosis:** Check KTable materialization, processing order and join semantics. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 3 — Window counts are unexpectedly high

**Diagnosis:** Check duplicate events, hopping-window overlap and aggregation keys. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 4 — Late events silently disappear

**Diagnosis:** Inspect grace policy, dropped-record metrics and timestamp validity. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 5 — Suppression buffer grows without bound

**Diagnosis:** Review suppression limits, grace, window close and memory/disk pressure. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 6 — Repartition topic ACL denies access

**Diagnosis:** Review internal topic names, application.id, producer/consumer ACL and RF. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 7 — RocksDB state restore stalls

**Diagnosis:** Inspect changelog availability, disk I/O, restore throughput and Pod placement. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 8 — Schema change breaks aggregation

**Diagnosis:** Inspect serde, state store schema, versioned rollout and changelog compatibility. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 9 — Poison-pill record crashes stream thread

**Diagnosis:** Inspect deserialization handler, error policy, DLQ and event ledger. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 10 — High cardinality causes storage explosion

**Diagnosis:** Inspect key cardinality, window retention, store compaction and quotas. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 11 — Rolling deployment causes rebalance storm

**Diagnosis:** Inspect instance churn, graceful shutdown, PDB and task restoration. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

### Scenario 12 — External side effect duplicates despite EOS

**Diagnosis:** Review Kafka transactional boundary and sink idempotency. Correlate Kafka input/output IDs, task assignment, topic partitions, RocksDB changelog, window timestamps, grace, consumer lag and Kubernetes Pod logs. **Response:** Preserve state and internal topics, freeze unsafe changes, repair the contract and reconcile outputs. **Evidence:** UTC incident timeline, sanitized data, expected/observed fixture, rollback and independent reviewer.

## 12. Eight production runbooks

### Runbook A — Stateless transformation incident

**Trigger and response:** Inspect input IDs, filtering, routing, schema, exceptions and output reconciliation. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook B — KStream/KTable join mismatch

**Trigger and response:** Inspect keys, partitions, temporal assumptions, materialization and replay. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook C — Event-time/window incident

**Trigger and response:** Inspect timestamps, grace, late drops, retention, suppression and corrected aggregates. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook D — Repartition and changelog recovery

**Trigger and response:** Inspect internal topic ACL, RF/ISR, offsets, restore and storage. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook E — RocksDB state pressure

**Trigger and response:** Review disk, compaction, cardinality, retention and capacity rollback. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook F — Poison-pill and serialization failure

**Trigger and response:** Quarantine record, inspect serde, handler policy, event-ID accounting and replay. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook G — Topology upgrade and rollback

**Trigger and response:** Validate application.id, store names, serde, internal topics and change approval. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

### Runbook H — Streams correctness SLO acceptance

**Trigger and response:** Verify join/window result fixtures, freshness, lag, integrity, RCA and independent signoff. **Safety:** Never delete production repartition/changelog topics, reset offsets, change application.id, disable TLS/ACL or wipe state without a reviewed migration. **Exit:** Correct join/window results, bounded lag and state restore, reconciled event ledger, recovered SLO, RCA and independent signoff.

## 13. Correctness matrix and SLO design

| Fixture | Expected behavior | Evidence |
|---|---|---|
| Two same-key events in one tumbling window | count updates to 1 then 2 | key/window start and output |
| Same key across window boundary | separate counts | event timestamps |
| Two records in overlapping hopping windows | each may contribute to multiple windows | window membership |
| Late record within grace | update may be accepted | grace/timestamp and output |
| Late record beyond grace | dropped by windowed operator | dropped-record metrics/ledger |
| Join key absent from table | inner join emits no match | table state and event ID |
| Stream-stream match outside join window | no join output | both timestamps |
| Duplicate input event | extra count unless deduplicated | unique event-ID ledger |

SLOs should include processing freshness, join-match rate where meaningful, late/drop rate, task health, RocksDB restore time, repartition throughput, disk headroom and business reconciliation. Do not use a fixed universal lag threshold.

## 14. Evidence package

```text
evidence-ch62/
  approved-stream-processing-charter.md
  exact-version-kubernetes-matrix.md
  preflight.txt
  immutable-build-sbom.md
  stable-key-partition-contract.md
  stateless-filter-ledger.csv
  mapping-fanout-review.md
  branch-routing-dlq.md
  stream-stream-join-matrix.csv
  stream-table-join-matrix.csv
  table-table-join-matrix.csv
  aggregate-count-fixtures.csv
  repartition-topic-acl-rf.md
  tumbling-window-fixtures.csv
  hopping-session-window-matrix.csv
  suppression-buffer-plan.md
  late-event-drop-ledger.csv
  deployment-resources-security.md
  rebalance-state-restore-tabletop.md
  topology-rollback-plan.md
  input-output-event-ledger.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

All artifacts require exact version, UTC timestamp, expected/observed result, **Live** vs **Tabletop**, redaction, owner, rollback/abort and independent reviewer.

## 15. 100-point Streams processing assessment

| Domain | Points | Critical |
|---|---:|---|
| Stateless operators and event-ID accounting | 10 | Yes |
| KStream/KTable join semantics and co-partitioning | 20 | Yes |
| Aggregations, repartition and RocksDB state | 15 | Yes |
| Event-time windows, grace, suppression and late records | 20 | Yes |
| Kubernetes/Strimzi security, tasks and storage | 10 | Yes |
| Metrics, freshness, lag and correctness SLO | 10 | Yes |
| Recovery, rollback and runbooks | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and every critical gate independently evidenced. **Automatic Fail:** fabricated join/window tests, missing event-ID accounting, unreviewed state reset, internal topic deletion, secret exposure, unsupported exactly-once external claims or absent independent review.

## 16. Cleanup, references and next chapter

Remove only chapter-owned synthetic topics, app Pods and alerts after approved evidence retention. Preserve changelog/repartition topics and local state until the application is intentionally retired through a documented procedure.

**References:** [Apache Kafka Streams](https://kafka.apache.org/documentation/streams/), [Kafka Streams Developer Guide](https://docs.confluent.io/platform/current/streams/developer-guide/overview.html), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/).

**Next:** Chapter 063 — Kafka Streams State Stores, RocksDB, Changelog Topics and Fault-Tolerant Recovery.

---

**Verification boundary:** Publication proves document availability only. Live join/window execution, late-event correctness, state restore and independent security review remain Pending.
