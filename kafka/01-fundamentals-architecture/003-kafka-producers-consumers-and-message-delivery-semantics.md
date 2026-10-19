# Chapter 003 — Kafka Producers, Consumers and Message Delivery Semantics
## Kubernetes-first primary labs — Producer and consumer Pods, groups and replay

**Platform:** Kubernetes, Strimzi Operator, KRaft and KafkaNodePool. **Source of truth:** [Shared Kubernetes Lab Foundation](../kubernetes/README.md). **Execution:** Pending. **Security review:** Pending.

**Prerequisite:** Follow the [Kubernetes-first Kafka Lab Platform](../kubernetes/README.md) for operator/CRD version checks, Kafka cluster manifests, namespace, CLI Pod, KafkaTopic and evidence collection. Use `kubectl` rather than Docker Compose for all new exercises. Commands and CRD schemas require validation against the installed Strimzi release.

**Lab A:** Launch the version-matched Kafka tools Pod, create an RF=3 topic, produce keyed records with `acks=all` and `enable.idempotence=true`. **Lab B:** Consume using `--group sre-consumer-ch03 --from-beginning --max-messages 2`; inspect `kafka-consumer-groups.sh --describe --group sre-consumer-ch03`. **Lab C:** Replay with a distinct group, never reset a live group's offsets. **Validate:** business event IDs remain unique and downstream writes must be idempotent; producer idempotence alone does not guarantee exactly-once external side effects. **Incident:** a Pod crash between DB write and offset commit causes replay. **Runbook:** reconcile event IDs, consumer offsets and sink transactions.

**Automated acceptance baseline:** `kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s`; `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc`; `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml` (if created); and a bounded produce/consume smoke test from the Kafka CLI Pod. Save exit codes and sanitized outputs. A successful manifest apply alone is not a pass.

**Legacy note:** The original Docker Compose examples preserved later in this chapter are **superseded historical reference**, not the supported primary lab. Do not execute their destructive commands as part of the Kubernetes workflow. Their Docker-specific assessment steps must be interpreted using the Kubernetes replacement above.

---


**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part 01:** Kafka Fundamentals and Architecture  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers  
**Prerequisites:** Chapters 001–002, Docker, running Kafka 4.1.x KRaft lab  
**Status:** Published; live execution and security review pending

> **Safety:** All write, delete, restart, and consumer-group commands are for a disposable lab. Never change production acknowledgments, consumer offsets, transactions, or topic settings without peer review and a rollback plan.

## 1. Learning objectives

By the end of this chapter you can:

1. Trace a record from producer serialization to broker append and consumer acknowledgment.
2. Distinguish at-most-once, at-least-once, and Kafka's scoped exactly-once semantics.
3. Explain producer acknowledgments, retries, idempotence, in-flight requests, and delivery timeouts.
4. Contrast consumer position with committed offset and explain replay windows.
5. Configure manual offset commits safely for at-least-once processing.
6. Describe Kafka transactions, read_committed isolation, and external side-effect limitations.
7. Execute labs, automated tests, and SRE incident runbooks.

## 2. End-to-end architecture

```text
 Application
     |
 key/value serializers + partitioner
     |
 producer accumulator / batches / retry / idempotent sequence
     |
 Kafka broker leader ---> partition log ---> replicas (when configured)
     |                                           |
     +-- produce acknowledgment <----------------+
     |
 consumer fetch -> deserialize -> process -> commit next offset
                                   |
                             external system
                         (DB, API, object store)
```

The producer determines the topic, partition, key and payload. The leader appends accepted records to its partition log. Replication and acknowledgment configuration govern durability. A consumer fetches records and tracks its **position** independently from its **committed offset**.

**Important:** An acknowledged write is not automatically a successful downstream business transaction. End-to-end correctness depends on consumer behavior, downstream idempotency, transactional boundaries, and failure recovery.

## 3. Producer reliability

| Setting | Meaning | Production concern |
|---|---|---|
| `acks=0` | Do not wait for broker acknowledgment | Can lose records without producer detecting failure |
| `acks=1` | Leader acknowledges after local append | Leader failure before replication may lose acknowledged data |
| `acks=all` | Leader waits for required in-sync replica acknowledgments | Stronger durability with suitable replication and `min.insync.replicas` |
| `enable.idempotence=true` | Deduplicates eligible producer retries using producer identity and sequence numbers | Protects against duplicate append from retries within supported producer session/protocol scope |
| `retries` | Retry retriable failures within delivery constraints | Never assume infinite retry guarantees |
| `delivery.timeout.ms` | Upper bound on time to report send success/failure, subject to documented behavior | Timeouts can leave ambiguous outcomes |
| `max.in.flight.requests.per.connection` | Concurrent unacknowledged requests | Ordering behavior depends on idempotence and retry settings |
| `linger.ms` / `batch.size` | Batching trade-offs | Latency vs throughput |

Kafka producer idempotence requires compatible settings (including `acks=all`, retries enabled, and max in-flight requests no greater than five). Modern Java clients commonly enable idempotence by default when there are no conflicting settings, but **always inspect the effective client configuration** rather than assuming a default across versions or libraries.

### 3.1 Durability is a cluster-level property

For a production three-replica topic, a typical starting point is replication factor 3, `min.insync.replicas=2`, and `acks=all`. These settings can reject writes when ISR shrinks below the minimum rather than silently accepting weaker durability. They do not replace rack/failure-domain placement, monitoring, storage reliability, or recovery testing.

Our single-broker lab uses replication factor 1, so it **cannot demonstrate quorum durability** or real replica-failure behavior.

### 3.2 Ambiguous outcomes

A producer timeout or lost acknowledgment does not prove the record was never appended. A caller retrying a business operation with a **new producer session** may create a logical duplicate even if Kafka producer idempotence is enabled. Assign a stable business event ID and design downstream deduplication when duplicates matter.

## 4. Consumer reliability

A consumer group coordinates partition assignment. Consumers periodically poll and process fetched records. Kafka stores committed offsets for the group in an internal topic; the committed value is the **next offset to consume**.

### 4.1 Delivery patterns

| Pattern | Processing and commit order | Trade-off |
|---|---|---|
| At-most-once | Commit before processing | Processing failures can lose work |
| At-least-once | Process, then commit | Crashes can replay already-processed work |
| Kafka transactional read-process-write | Commit produced Kafka records and consumed offsets in one Kafka transaction | Atomicity within Kafka's supported transaction scope; external systems need additional design |

**Exactly-once is not universal.** Kafka transactions can atomically commit Kafka output records and consumed offsets when applications correctly use transactional producers, `sendOffsetsToTransaction`, consumer group metadata, and `read_committed` downstream isolation. An HTTP request, email, or ordinary database write is **not** automatically included in that Kafka transaction.

For external databases, common strategies include idempotent upserts keyed by event ID, an inbox table with unique constraints, transactional outbox patterns, or connector-specific guarantees. Choose according to business correctness requirements.

### 4.2 Offset commit example

If a consumer reads offset 19, performs a durable database update, and commits offset 20, a crash before the commit may replay offset 19. If the database update is idempotent, replay is safe. If it commits 20 before the database update, a crash can skip the unprocessed record.

### 4.3 Rebalances and slow processing

When partition ownership changes, consumers must avoid processing stale assignments and committing progress for work that has not completed. Watch `max.poll.interval.ms`, `session.timeout.ms`, heartbeats, processing time, and assignment strategy. Poll-loop blocking can trigger rebalances and duplicate work. Concurrency requires careful per-partition completion tracking; never commit past unfinished earlier offsets.

## 5. Hands-on lab prerequisites

The following commands assume a running Kafka container named `kafka` from Chapter 001, with the Kafka scripts in `/opt/kafka/bin` and an accessible in-container listener at `localhost:9092`. Adapt `KAFKA_CONTAINER` and bootstrap address to your actual lab.

```bash
export KAFKA_CONTAINER="${KAFKA_CONTAINER:-kafka}"
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092 >/dev/null
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --create --if-not-exists \
  --topic sre-delivery-ch03 --partitions 3 --replication-factor 1
```

Expected: topic exists with three partitions. Use only disposable topic names and test data.

## 6. Lab A — Producer acknowledgments and keyed writes

```bash
printf '%s\n' \
  'account-7:deposit-event-001' \
  'account-7:withdrawal-event-002' \
  'account-9:deposit-event-003' \
| docker exec -i "$KAFKA_CONTAINER" \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 \
    --topic sre-delivery-ch03 \
    --producer-property acks=all \
    --producer-property enable.idempotence=true \
    --property parse.key=true \
    --property key.separator=:

timeout 20s docker exec "$KAFKA_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic sre-delivery-ch03 --from-beginning \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  --max-messages 3
```

**Validate:** three records are visible, and both `account-7` events have the same partition with increasing offsets. Do not assume any ordering between records in different partitions. `acks=all` with RF=1 is **not** highly available.

## 7. Lab B — Consumer group offset lifecycle

Create a distinct group to avoid affecting earlier exercises:

```bash
timeout 20s docker exec "$KAFKA_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic sre-delivery-ch03 \
  --group sre-ch03-billing \
  --from-beginning --max-messages 3 \
  --property print.offset=true

docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group sre-ch03-billing
```

**Observe:** group offsets may not appear immediately because the console consumer's commit behavior depends on its lifecycle and configuration. Rerun describe after a short delay. A group's committed offset, not the existence of records in the topic, controls normal restart position.

To inspect the end offsets without changing the group:

```bash
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 \
  --topic sre-delivery-ch03 --time -1
```

## 8. Lab C — Explicit manual commits with a Python client

This optional lab demonstrates process-before-commit with `confluent-kafka`. It runs on a machine that can reach a **client-accessible Kafka listener**. If Kafka advertises `localhost:9092` only inside the container, run the script inside a network-reachable environment or configure a correctly advertised host listener; do not assume container-local `localhost` is reachable from the host.

Install in an isolated Python environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install 'confluent-kafka>=2.5,<3'
export KAFKA_BOOTSTRAP='localhost:9092'
```

Save as `manual_commit.py`:

```python
import os
import sys
from confluent_kafka import Consumer, KafkaException

topic = "sre-delivery-ch03"
group = "sre-ch03-manual-" + os.environ.get("LAB_RUN_ID", "one")
consumer = Consumer({
    "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092"),
    "group.id": group,
    "enable.auto.commit": False,
    "auto.offset.reset": "earliest",
})
processed = 0
consumer.subscribe([topic])
try:
    while processed < 3:
        message = consumer.poll(10.0)
        if message is None:
            raise TimeoutError("No message received within 10 seconds")
        if message.error():
            raise KafkaException(message.error())
        # Replace this print with an idempotent, durable business operation.
        print(message.topic(), message.partition(), message.offset(),
              message.key(), message.value())
        # Synchronous commit of the next offset only after successful processing.
        consumer.commit(message=message, asynchronous=False)
        processed += 1
finally:
    consumer.close()
print(f"Processed and committed {processed} messages")
```

```bash
export LAB_RUN_ID="$(date +%s)"
python manual_commit.py
```

**Expected:** three records are processed and committed. This script is intentionally single-threaded and illustrative. A real application must handle cancellation, retries, poison messages, rebalance callbacks, idempotent side effects, and offset-commit errors.

## 9. Lab D — Controlled replay without resetting offsets

A new consumer group with `--from-beginning` can read retained data independently of the previous group:

```bash
timeout 20s docker exec "$KAFKA_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic sre-delivery-ch03 \
  --group "sre-ch03-replay-$(date +%s)" \
  --from-beginning --max-messages 3
```

**Expected:** retained records can be replayed. This does not alter the committed offsets of `sre-ch03-billing`. For a real replay, first assess downstream idempotency and retention coverage.

## 10. Automated validation

Save as `verify-ch03.sh`. It creates a unique disposable topic, produces three keyed messages, and validates basic fetch behavior without modifying an existing consumer group.

```bash
#!/usr/bin/env bash
set -euo pipefail
C="${KAFKA_CONTAINER:-kafka}"
BS=localhost:9092
CLI=/opt/kafka/bin
TOPIC="sre-ch03-check-$(date +%s)-$$"

run() { docker exec "$C" "$CLI/$1" "${@:2}"; }
cleanup() {
  run kafka-topics.sh --bootstrap-server "$BS" \
    --delete --topic "$TOPIC" >/dev/null 2>&1 || true
}
trap cleanup EXIT

run kafka-topics.sh --bootstrap-server "$BS" --create \
  --topic "$TOPIC" --partitions 1 --replication-factor 1 >/dev/null

printf 'id-1:one\nid-1:two\nid-1:three\n' | docker exec -i "$C" \
  "$CLI/kafka-console-producer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:

OUTPUT="$(timeout 20s docker exec "$C" "$CLI/kafka-console-consumer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --from-beginning --max-messages 3 --property print.key=true)"

COUNT="$(printf '%s\n' "$OUTPUT" | grep -c 'id-1' || true)"
test "$COUNT" -eq 3 || { echo "FAIL: expected 3 messages; got $COUNT"; exit 1; }
echo "PASS: producer acknowledged and consumer fetched 3 keyed messages"
```

```bash
chmod +x verify-ch03.sh
./verify-ch03.sh
```

**Limitation:** This smoke test validates basic connectivity and fetch behavior. It does **not** prove exactly-once processing, durability through broker loss, or a successful manual-commit crash recovery.

## 11. Production SRE incident simulations

### Incident 1 — Duplicate payment events

**Signal:** duplicate downstream payments after producer timeout or consumer restart.

**Hypotheses:** ambiguous producer outcome, retries across sessions, process-before-commit crash window, missing business-event deduplication.

**Investigate:** compare event IDs, Kafka topic-partition-offset, producer request logs, consumer commit history, and downstream unique keys.

**Mitigate:** stop unsafe non-idempotent side effects, implement or restore deduplication, then replay with approval. Do not delete Kafka messages to conceal duplicates.

### Incident 2 — Silent message loss

**Signal:** producer reports success but events are missing after broker failure.

**Hypotheses:** `acks=1`, insufficient replication, ISR instability, incorrect topic or cluster, producer errors ignored by caller.

**Investigate:** effective producer configs, topic replication factor, `min.insync.replicas`, ISR history, broker failures, error callbacks, and application event IDs.

**Mitigate:** restore healthy replication and durable write policy; reconcile missing events from authoritative source. Changing `acks` cannot reconstruct lost records.

### Incident 3 — Lag spike and rebalance storm

**Signal:** rising consumer lag, frequent assignment changes, long processing latency.

**Hypotheses:** `max.poll.interval.ms` exceeded, slow downstream service, group membership churn, key skew, oversized batches.

**Investigate:** poll interval, processing latency, rebalance metrics, partition lag distribution, consumer logs, deployment timeline.

**Mitigate:** control concurrency, optimize slow processing, reduce batch workload, right-size poll settings and consumer count; verify no unprocessed offsets were committed.

### Incident 4 — Transactional records invisible to consumer

**Signal:** `read_committed` consumer appears stalled while producer is writing.

**Hypotheses:** long-running or stuck open transaction; LSO behind LEO; transaction coordinator issue.

**Investigate:** transaction duration, producer transactional IDs, LSO/LEO differences, aborted transactions, coordinator logs.

**Mitigate:** fix or fence malfunctioning transactional producers using supported procedures; avoid casual transaction timeouts or offset resets in production.

## 12. Troubleshooting matrix

| Symptom | Likely cause | First safe check |
|---|---|---|
| `NotEnoughReplicas` | ISR below `min.insync.replicas` | Describe topic, inspect broker/replica health |
| `TimeoutException` on send | Broker/network pressure, unavailable partition, delivery deadline | Producer metrics, broker logs, request latency |
| Duplicate events | Retry ambiguity or consumer replay | Compare stable business event IDs |
| Consumer skips events | Commit-before-process or wrong group offset | Audit offset and processing sequence |
| Consumer lag grows | Processing bottleneck or rebalance | Per-partition lag, poll timing, downstream latency |
| `read_committed` lag differs from raw end | Open transactions | Inspect LSO and transactional producer health |
| Consumer cannot connect | Wrong advertised listener, DNS, TLS/SASL, ACL | Check broker metadata and client config |

## 13. Production runbook — delivery guarantee incident

**Trigger:** event loss, duplicate business action, consumer replay, or a delivery-related SLO breach.

1. **Scope:** capture cluster, topic, group, affected keys, event IDs, incident window, and business impact.
2. **Freeze risky actions:** avoid offset resets, topic deletion, uncontrolled replays, and unreviewed producer config changes.
3. **Preserve evidence:** save effective producer/consumer settings, group offsets, partition metadata, broker logs, and downstream transaction IDs.
4. **Classify:** identify whether records were never produced, not durably replicated, not consumed, not committed, or applied incorrectly downstream.
5. **Stabilize:** restore brokers/ISR, reduce client errors, address rebalances, or pause non-idempotent side effects as appropriate.
6. **Recover:** reconcile authoritative business events; use controlled replay with idempotent writes or deduplication; test on a small scope first.
7. **Verify:** confirm event completeness, duplicate suppression, processing latency, lag trend, and downstream state invariants.
8. **Postmortem:** document failure window, detection gaps, durability assumptions, remediation, and action owners.

**Key SLO/SLI examples:** accepted-to-durable-append success rate, end-to-end event processing age, per-partition lag, duplicate side-effect rate, failed produce requests, consumer rebalance rate, and under-replicated partitions.

## 14. Production readiness checklist

- [ ] Explicitly define the business delivery guarantee for each workflow.
- [ ] Validate producer `acks`, idempotence, retries, delivery timeouts, and error callbacks.
- [ ] Validate replication factor, ISR placement, and `min.insync.replicas`.
- [ ] Make downstream side effects idempotent where at-least-once replay is possible.
- [ ] Commit only fully processed offsets; handle rebalance and partial batch completion.
- [ ] Use Kafka transactions only where their atomicity scope matches the workflow.
- [ ] Establish safe replay, DLQ, and retention procedures.
- [ ] Alert on end-to-end processing delay and business correctness, not only broker health.
- [ ] Test crash-after-process-before-commit and ambiguous producer acknowledgment scenarios.
- [ ] Confirm authentication, encryption, ACLs, audit trails, and secrets handling.

## 15. Assessment — 100 points

| Question / exercise | Points |
|---|---:|
| Explain the difference among `acks=0`, `acks=1`, and `acks=all` | 10 |
| Explain why `acks=all` with RF=1 is not HA | 10 |
| Describe idempotent producer guarantees and limitations | 10 |
| Demonstrate a keyed producer and consumer lab | 10 |
| Explain committed offset versus current position | 10 |
| Implement and explain process-before-commit | 10 |
| Reproduce a replay using a new consumer group | 10 |
| Explain Kafka transaction boundaries and `read_committed` | 10 |
| Diagnose a duplicate side-effect incident | 10 |
| Draft a recovery plan with evidence, mitigation, and validation | 10 |

**Passing guideline:** 80/100 with the lab demonstrations and safety requirements completed. Record results only after independent execution.

## 16. Cleanup

Delete only the disposable lab topic after completing the exercises; deletion permanently removes its records.

```bash
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --topic sre-delivery-ch03
```

Do not delete unrelated topics or consumer groups. The automated verification script cleans up its uniquely named topic.

## 17. References

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Producer configuration](https://kafka.apache.org/documentation/#producerconfigs)
- [Consumer configuration](https://kafka.apache.org/documentation/#consumerconfigs)
- [Kafka design and delivery semantics](https://kafka.apache.org/documentation/#semantics)

**Next:** Chapter 004 — Kafka Replication, Leaders, ISR and Fault Tolerance.

---

**Publication:** Complete. **Live lab execution:** Pending. **Security review:** Pending. The command examples are educational and not a production approval.
