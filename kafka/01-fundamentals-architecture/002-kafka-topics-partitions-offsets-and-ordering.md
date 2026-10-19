# Chapter 002 — Kafka Topics, Partitions, Offsets and Ordering
## Kubernetes-first primary labs — KafkaTopic partitions, keys and offsets

**Platform:** Kubernetes, Strimzi Operator, KRaft and KafkaNodePool. **Source of truth:** [Shared Kubernetes Lab Foundation](../kubernetes/README.md). **Execution:** Pending. **Security review:** Pending.

**Prerequisite:** Follow the [Kubernetes-first Kafka Lab Platform](../kubernetes/README.md) for operator/CRD version checks, Kafka cluster manifests, namespace, CLI Pod, KafkaTopic and evidence collection. Use `kubectl` rather than Docker Compose for all new exercises. Commands and CRD schemas require validation against the installed Strimzi release.

**Lab A:** Create a KafkaTopic with three partitions, RF=3, min ISR=2; inspect `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml`. **Lab B:** From the tools Pod, send `customer-1:created`, `customer-1:paid`, `customer-2:created` with `--property parse.key=true --property key.separator=:`; read back with `--property print.key=true --property print.partition=true --property print.offset=true`. **Validate:** same key routes consistently under unchanged partitioning, offsets rise within each partition, no total cross-partition order. **Failure:** changed partition count or key serializer may break ordering assumptions. **Runbook:** capture KafkaTopic YAML, partition assignments, consumer lag and event IDs before any reassignment.

**Automated acceptance baseline:** `kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s`; `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc`; `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml` (if created); and a bounded produce/consume smoke test from the Kafka CLI Pod. Save exit codes and sanitized outputs. A successful manifest apply alone is not a pass.

**Legacy note:** The original Docker Compose examples preserved later in this chapter are **superseded historical reference**, not the supported primary lab. Do not execute their destructive commands as part of the Kubernetes workflow. Their Docker-specific assessment steps must be interpreted using the Kubernetes replacement above.

---


**Track:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 01 — Kafka Fundamentals and Architecture  
**Audience:** Kafka administrators, SREs, DBREs, platform engineers  
**Prerequisite:** Chapter 001, Docker Engine and Docker Compose  
**Lab scope:** Disposable single-broker Kafka 4.1.x KRaft environment; no production data

> **Operational boundary:** Commands here are designed for an isolated lab. Never delete topics, reset consumer offsets, or change partition counts on production topics without change approval, dependency analysis, and a tested recovery plan.

## 1. Learning objectives

After this chapter you should be able to:

1. Explain topics, partition IDs, keys, offsets, log end offsets, and consumer positions.
2. Predict ordering guarantees and identify when key-based routing is required.
3. Distinguish log append order from end-to-end application processing order.
4. Create, inspect, and alter a topic; understand why increasing partitions changes key mapping.
5. Diagnose consumer lag and distinguish replay from data loss.
6. Demonstrate retention-independent offset behavior and build repeatable lab checks.
7. Apply a safe SRE runbook for ordering, lag, and partition-count incidents.

## 2. Architecture and data model

A Kafka topic is a named logical stream. Each topic contains one or more partitions. Each partition is an append-only ordered log identified by a numeric partition ID. A record includes a key (optional), value, timestamp, headers (optional), and a topic-partition-offset coordinate.

```text
                      topic: orders
 producer with key       |
 customer-42             +-- partition 0: [offset 0] [offset 1] [offset 2] ...
        |                +-- partition 1: [offset 0] [offset 1] ...
        +-- partitioner  +-- partition 2: [offset 0] [offset 1] ...
                                   |
                          consumer group: billing
                          one active member per
                          partition within a group
```

Offsets are **partition-local** positions, not globally ordered message IDs. Offset 15 on partition 0 cannot be compared chronologically with offset 15 on partition 2. Kafka can retain gaps in visible offsets because of transactions, compaction, and retention. An offset is not a timestamp.

### 2.1 Ordering contract

- Records appended to **one partition** have a defined log order.
- Kafka does **not** guarantee a single total order across all partitions of a topic.
- With a stable key, compatible partitioner, and unchanged partition count, records for that key normally route to the same partition.
- Null-key routing is not an ordering strategy. Producer batching and sticky partition selection can distribute unkeyed records.
- Multiple concurrent producers, retries, application concurrency, and downstream parallel processing can change the order observed by an application. For strict per-key processing, serialize work by key and design producer delivery settings accordingly.
- Idempotent production helps prevent retry-induced duplication and preserves eligible per-partition ordering under its protocol constraints; it does not create cross-partition ordering or application-level exactly-once behavior.
- **Increasing the number of partitions can remap existing keys** for common hash/modulo partitioning strategies; existing records are not redistributed automatically. A key can then have historical records in an old partition and new records in another.

### 2.2 Offsets and consumer progress

| Term | Meaning | SRE implication |
|---|---|---|
| Earliest available offset | First currently readable position for a partition | May advance after retention |
| Log end offset (LEO) | Position immediately after the last appended record | Not itself an existing record |
| Consumer position | Next offset a consumer will fetch | May be ahead of committed offset |
| Committed offset | Next offset saved for a consumer group to resume from | Commit after processing to favor at-least-once |
| Consumer lag | Difference between end position and committed/consumed position, depending on measurement | A rising value is a symptom, not root cause |
| Last stable offset (LSO) | Boundary visible to read_committed consumers in transactional scenarios | Can lag LEO while transactions are open |

An offset commit records the **next** offset to consume. If a consumer successfully processes offset 7, committing 8 expresses that progress. Crashes between processing and commit can cause reprocessing; committing before processing risks losing work from the application's perspective.

## 3. Partition count and operational trade-offs

More partitions increase potential consumer-group parallelism and may distribute broker work, but also add metadata, file handles, replication work, rebalance overhead, and operational complexity. A group with 6 consumers reading a 3-partition topic can have at most 3 actively assigned consumers for that topic at a time.

Partition-count changes are generally **one-way** through normal topic administration: increasing is supported, reducing is not. Repartitioning an existing keyed workload safely often requires a new topic, migration, and controlled cutover.

For production planning, estimate required throughput, per-partition capacity, consumer concurrency, key skew, and growth. Validate with benchmarks rather than a universal “partitions per broker” rule.

## 4. Hands-on lab: create and inspect topic

Use the Chapter 001 lab cluster if it is already running. The following commands assume the broker container is named `kafka`; set `KAFKA_CONTAINER` to your actual container name if different. The commands execute Kafka CLI tools **inside** the container, so the bootstrap endpoint is `localhost:9092` as seen from that container; adjust if your listener differs.

```bash
export KAFKA_CONTAINER="${KAFKA_CONTAINER:-kafka}"
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:9092 >/dev/null

docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic sre-orders \
  --partitions 3 --replication-factor 1

docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --describe --topic sre-orders
```

**Expected:** `sre-orders` reports partition IDs 0, 1, and 2, each with one replica and one leader. Replication factor 1 is **lab-only** and cannot tolerate broker loss.

### 4.1 Produce keyed records

`parse.key=true` and `key.separator=:` make the portion before the colon the record key.

```bash
printf '%s\n' \
  'customer-42:order-created' \
  'customer-42:payment-authorized' \
  'customer-42:order-shipped' \
  'customer-99:order-created' \
| docker exec -i "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 \
    --topic sre-orders \
    --property parse.key=true \
    --property key.separator=:
```

Read records from the beginning with partition, offset, and key printed. A bounded `timeout` prevents a console consumer from waiting indefinitely for more messages.

```bash
timeout 20s docker exec "$KAFKA_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic sre-orders \
  --from-beginning --group sre-lab-reader \
  --property print.partition=true \
  --property print.offset=true \
  --property print.key=true \
  --max-messages 4
```

**Expected:** four records are read. All three `customer-42` records should share a partition in this controlled single-producer test, and their offsets within that partition should increase. Output from a multi-partition consumer may interleave partitions; do not interpret that interleaving as a global order.

### 4.2 Observe committed offsets and lag

```bash
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group sre-lab-reader
```

**Expected:** topic partitions with `CURRENT-OFFSET`, `LOG-END-OFFSET`, and `LAG`. The console consumer's final commit timing and group state can affect immediate results. Retry the describe command after a few seconds if the group has not stabilized.

### 4.3 Inspect offsets by timestamp-independent boundary

```bash
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic sre-orders --time -1

docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic sre-orders --time -2
```

`-1` requests latest positions and `-2` earliest available positions. Expect three partition entries in each output. On a fresh topic without retention cleanup, earliest positions will normally be zero.

## 5. Automated smoke tests

Save as `verify-ch02.sh` and run on a disposable lab cluster. This checks topic partition count and basic keyed routing without assuming which numeric partition the key hashes to.

```bash
#!/usr/bin/env bash
set -euo pipefail
C="${KAFKA_CONTAINER:-kafka}"
CLI=/opt/kafka/bin
BS=localhost:9092
TOPIC=sre-ch02-verify-$(date +%s)-$$

run() { docker exec "$C" "$CLI/$1" "${@:2}"; }
trap 'run kafka-topics.sh --bootstrap-server "$BS" --delete --topic "$TOPIC" >/dev/null 2>&1 || true' EXIT

run kafka-topics.sh --bootstrap-server "$BS" --create \
  --topic "$TOPIC" --partitions 3 --replication-factor 1 >/dev/null

desc="$(run kafka-topics.sh --bootstrap-server "$BS" --describe --topic "$TOPIC")"
count="$(printf '%s\n' "$desc" | grep -cE 'Partition: [0-9]+[[:space:]]' || true)"
test "$count" -eq 3 || { echo "FAIL: expected 3 partitions; found $count"; exit 1; }

printf 'stable-key:one\nstable-key:two\nstable-key:three\n' | \
  docker exec -i "$C" "$CLI/kafka-console-producer.sh" \
    --bootstrap-server "$BS" --topic "$TOPIC" \
    --property parse.key=true --property key.separator=:

records="$(timeout 20s docker exec "$C" "$CLI/kafka-console-consumer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" --from-beginning \
  --property print.partition=true --property print.key=true --max-messages 3)"

test "$(printf '%s\n' "$records" | grep -c 'stable-key' || true)" -eq 3 || \
  { echo "FAIL: expected 3 records"; exit 1; }
partitions="$(printf '%s\n' "$records" | sed -nE 's/.*Partition:([0-9]+).*/\1/p' | sort -u)"
test "$(printf '%s\n' "$partitions" | grep -c . || true)" -eq 1 || \
  { echo "FAIL: stable key appeared in multiple partitions or formatter changed"; exit 1; }
echo "PASS: 3 partitions and 3 stable-key records on one partition"
```

**Note:** CLI output formatting can vary by Kafka version. If the test fails on formatting alone, inspect `--describe` and console-consumer output and update the parser; do not assume a functional broker failure.

## 6. Failure injection and incident simulations

### Scenario A — Key skew / hot partition

**Symptom:** one partition's log end offset grows much faster than peers, consumers show uneven lag, broker network or disk utilization is imbalanced.

**Lab:** produce hundreds of records with the same key; compare `kafka-get-offsets.sh --time -1` across partitions.

**Cause:** key cardinality and distribution, not necessarily an undersized cluster.

**Response:** confirm producer key distribution, per-partition ingress, and consumer assignment. Do not blindly increase partition count: this can change key routing and ordering semantics. Consider application-level key sharding only when per-entity ordering constraints permit it.

### Scenario B — Unexpected replay after restart

**Symptom:** consumer reprocesses messages after a restart.

**Cause candidates:** processing completed but offsets were not committed; group ID changed; `auto.offset.reset` applied when no valid committed offset exists.

**Response:** check group ID, committed offset, application checkpointing, processing acknowledgments, and transaction/commit behavior. Design idempotent consumers and use commit-after-processing for at-least-once semantics.

### Scenario C — Missing historical records

**Symptom:** consumer requests an offset older than the earliest available offset.

**Cause candidates:** time/size retention, administrative deletion, topic recreation, compaction semantics.

**Response:** compare earliest/latest offsets; inspect retention configuration and data age. Restore from an independently verified archive or upstream replay if required. **Resetting a group offset does not restore deleted Kafka data.**

### Scenario D — Ordering regression after partition increase

**Symptom:** same entity's events appear in different partitions after an increase.

**Cause:** partitioner remapping; ordering was only guaranteed within each partition.

**Response:** stop unsafe migration, document old/new partition mapping, evaluate consumer fencing and ordered cutover, and plan a new topic with a stable partitioning contract if necessary.

## 7. Troubleshooting decision table

| Symptom | First checks | Safe next action |
|---|---|---|
| Topic missing | Bootstrap address, cluster ID, topic spelling, ACLs | Validate target cluster before creating |
| Lag grows | Producer ingress, consumer processing latency, rebalances, hot partitions | Identify bottleneck before scaling |
| Same key in multiple partitions | Key serialization, partitioner, partition-count changes, multiple producers | Compare historical topic metadata and producer configuration |
| Consumer reads no records | Group committed position, `auto.offset.reset`, earliest/latest | Use a **new lab group** to test replay |
| Offset gaps | Retention, compaction, transactions | Avoid interpreting gaps as corruption |
| Consumer count exceeds partitions | Group assignments | Right-size group or redesign partition strategy |
| Ordering differs in database | Async handlers, retries, concurrency, idempotency | Trace event key and per-key processing path |

## 8. Production SRE runbook: ordering or lag incident

**Trigger:** breached lag SLO, out-of-order entity updates, or unexplained replay.

1. **Declare scope:** record cluster, topic, group, partitions, time window, affected entity keys, business impact, and incident owner.
2. **Preserve evidence:** capture topic description, partition count, earliest/latest offsets, consumer-group offsets, broker metrics, deployment history, and producer partitioner configuration.
3. **Protect data:** pause risky administrative changes; do not delete topics or reset offsets during triage.
4. **Localize:** determine whether the issue is ingress skew, broker replication/storage, consumer rebalance/processing, or downstream concurrency.
5. **Mitigate:** scale consumers only up to useful partition concurrency; reduce costly processing; throttle producers when approved; isolate poison records using a documented dead-letter strategy.
6. **Validate:** compare per-partition lag trends, end-to-end event age, application error rates, and entity sequence invariants.
7. **Recover:** for replay, use a tested idempotent path and an approved offset-reset procedure **only with consumers stopped**; snapshot current committed positions before any reset.
8. **Close:** capture root cause, customer impact, prevention work, alert tuning, and follow-up owner.

**Suggested observability:** records/sec and bytes/sec by topic, consumer lag by partition, maximum event age, rebalance rate, failed processing count, broker under-replicated partitions, disk usage, and end-to-end per-key sequence violations. Lag alone does not establish correctness.

## 9. Production design checklist

- [ ] Document key schema and ordering contract for each critical topic.
- [ ] Choose partition count based on measured throughput, concurrency, and expected growth.
- [ ] Use replication factor appropriate for production failure domains; RF=1 is not HA.
- [ ] Define retention and recovery source; distinguish retention from committed offsets.
- [ ] Specify producer delivery, idempotence, retries, and consumer commit strategy.
- [ ] Establish per-partition and end-to-end lag SLOs and alert thresholds.
- [ ] Test consumer rebalances, crash/restart, duplicate delivery, and key skew.
- [ ] Require migration review for partition-count changes.
- [ ] Secure authentication, authorization, encryption, and audit logging.

## 10. Assessment — 10 points

1. (1) Why is an offset not globally unique within a topic?
2. (1) What does committing offset 21 mean?
3. (1) Why can a six-member consumer group have idle members on a three-partition topic?
4. (1) Does increasing partitions redistribute old records?
5. (1) Why can increasing partitions break per-key ordering assumptions?
6. (1) What does `--time -1` show?
7. (1) Give two causes of consumer replay.
8. (1) Why might LSO differ from LEO?
9. (1) What is the first safe response to suspected ordering regression?
10. (1) Can offset reset recover records deleted by retention?

**Answer key:** (1) partition-local; (2) next record to read is 21; (3) at most one active group member per partition; (4) no; (5) keys can remap; (6) latest positions; (7) uncommitted work/group change/etc.; (8) open transactions; (9) preserve evidence and stop risky changes; (10) no.

## 11. Cleanup

Only delete the disposable topics created for this lab. Do **not** remove Chapter 001 topics or shared lab infrastructure unless no longer needed.

```bash
docker exec "$KAFKA_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --delete --topic sre-orders
```

## 12. Further reading and next chapter

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kafka operations documentation](https://kafka.apache.org/documentation/#operations)
- [Kafka consumer configuration](https://kafka.apache.org/documentation/#consumerconfigs)

**Next:** Chapter 003 — Kafka Producers, Consumers and Message Delivery Semantics.

---

**Publication status:** Published source chapter. **Live execution:** Pending. **Security review:** Pending. Lab output is illustrative until independently verified.
