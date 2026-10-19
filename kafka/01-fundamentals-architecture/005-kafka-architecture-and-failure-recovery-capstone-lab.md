# Chapter 005 — Kafka Architecture and Failure Recovery Capstone Lab
## Kubernetes-first primary labs — Kubernetes reliability capstone

**Platform:** Kubernetes, Strimzi Operator, KRaft and KafkaNodePool. **Source of truth:** [Shared Kubernetes Lab Foundation](../kubernetes/README.md). **Execution:** Pending. **Security review:** Pending.

**Prerequisite:** Follow the [Kubernetes-first Kafka Lab Platform](../kubernetes/README.md) for operator/CRD version checks, Kafka cluster manifests, namespace, CLI Pod, KafkaTopic and evidence collection. Use `kubectl` rather than Docker Compose for all new exercises. Commands and CRD schemas require validation against the installed Strimzi release.

**Capstone:** Validate Kafka Ready, three controllers, three brokers, PVC persistence, KafkaTopic RF=3/minISR=2, keyed production, consumer group replay, one broker-Pod failure, ISR restoration and business reconciliation. **Evidence:** before/during/after KafkaTopic metadata, `kubectl get pods,pvc`, metadata quorum status, producer acks, group offsets, Strimzi logs. **Acceptance:** no data loss claim without business event-ID comparison; do not delete PVCs; stop on under-min-ISR or quorum degradation. **Assessment (100):** architecture 10, CRDs 10, storage 10, topic 10, keyed ordering 10, delivery semantics 10, fault safety 10, ISR recovery 10, automation 10, incident report 10. Pass ≥85 with zero unsafe operations.

**Automated acceptance baseline:** `kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s`; `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc`; `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml` (if created); and a bounded produce/consume smoke test from the Kafka CLI Pod. Save exit codes and sanitized outputs. A successful manifest apply alone is not a pass.

**Legacy note:** The original Docker Compose examples preserved later in this chapter are **superseded historical reference**, not the supported primary lab. Do not execute their destructive commands as part of the Kubernetes workflow. Their Docker-specific assessment steps must be interpreted using the Kubernetes replacement above.

---


**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 01 — Kafka Fundamentals and Architecture (final capstone)  
**Prerequisites:** Chapters 001–004; Docker, Compose, Bash, Kafka CLI  
**Target:** Disposable three-broker Kafka 4.1.x KRaft lab from Chapter 004  
**Publication:** Complete | **Live execution:** Pending | **Security review:** Pending

> **Safety:** This capstone deliberately interrupts a broker, generates consumer replay, and tests degraded replication. Never run it against production or a shared Kafka cluster. Broker stop/start and topic deletion must be restricted to the dedicated lab. Do not weaken durability settings or perform unclean elections to pass a test.

## 1. Mission and acceptance criteria

You are the on-call Kafka SRE for a simulated order-processing platform. Your assignment is to deploy a resilient event stream, prove normal operation, handle one broker outage, identify offset and ordering implications, recover replica health, and prepare a concise incident report.

**Acceptance gates:**

1. Three KRaft broker/controller containers are healthy before injection.
2. Topic `sre-capstone-orders` has 3 partitions, replication factor 3, and `min.insync.replicas=2`.
3. At least six deterministic keyed events are produced with `acks=all`.
4. Consumer replay is demonstrated using a **new group**, without resetting an existing group's offsets.
5. Exactly one broker is stopped, and its loss is observed in partition leadership/ISR.
6. Writes succeed during one-broker loss **if** a leader and two ISR replicas remain.
7. The stopped broker is restarted; ISR returns to all three replicas.
8. Automated verification records pass/fail evidence.
9. Incident notes explain potential duplicate processing and durability limitations.
10. Cleanup is safe and scoped to disposable lab resources.

**Failure classification:** A failed acceptance gate is an investigation task, not permission to lower `min.insync.replicas`, force leader election, or delete Kafka data.

## 2. Architecture and assumptions

```text
                Producer (keyed order events)
                             |
                       acks=all
                             |
                 Topic: sre-capstone-orders
                   3 partitions / RF=3
                             |
           +-----------------+-----------------+
           |                 |                 |
        broker1           broker2           broker3
       KRaft node 1      KRaft node 2      KRaft node 3
       data + control    data + control    data + control
           |                 |                 |
           +-----------------+-----------------+
                             |
                  Consumer group billing
                             |
                    Idempotent sink
                   (simulated in lab)
```

This learning cluster combines broker and controller roles. A real production deployment should evaluate dedicated controller roles, zone/rack awareness, secure listeners, observability, capacity, backups, and organizational RPO/RTO requirements.

### 2.1 Core concepts assessed

- **Topic/partition:** partition-local ordering and offsets; no cross-partition total order.
- **Producer:** key selection, acknowledgments, retries, and idempotence.
- **Consumer:** position, committed offsets, replay windows, and group assignment.
- **Replication:** RF, ISR, leader changes, HW/LEO, and `min.insync.replicas`.
- **Recovery:** broker restart, replica catch-up, client retries, and evidence preservation.
- **SRE:** impact assessment, hypothesis testing, validation, and post-incident actions.

## 3. Prerequisite validation

Start the Chapter 004 dedicated Compose lab from its own directory. The Compose configuration and Kafka image version must be validated in your environment before this capstone; the lab has not been independently executed.

```bash
cd kafka-ch04-lab
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=50
```

Do not continue until all three broker containers are running and a bootstrap CLI command succeeds.

```bash
export KAFKA_CAPSTONE_CONTAINER=kafka-ch04-broker1
export KAFKA_CAPSTONE_BOOTSTRAP=broker1:9092

docker exec "$KAFKA_CAPSTONE_CONTAINER" \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" >/dev/null
```

**Preflight evidence:** capture `docker compose ps`, broker log snippets, and the command exit status. If Kafka 4.1.x startup reports quorum-format issues, fix the disposable environment using version-matched Kafka documentation before testing; never reuse storage with an unrelated cluster ID.

## 4. Lab A — Deploy the capstone topic

```bash
docker exec "$KAFKA_CAPSTONE_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --create --if-not-exists \
  --topic sre-capstone-orders \
  --partitions 3 --replication-factor 3 \
  --config min.insync.replicas=2

docker exec "$KAFKA_CAPSTONE_CONTAINER" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --describe --topic sre-capstone-orders
```

**Validate:** each partition has three assigned replicas, one leader, and eventually an ISR containing all three replicas. Record the leader broker ID for each partition.

**Note:** `--if-not-exists` does not enforce that a preexisting topic has the desired partition count, RF, or min ISR. Inspect the description; if it differs, stop and investigate rather than silently accepting the configuration.

## 5. Lab B — Produce a deterministic business event stream

```bash
cat > capstone-events.txt <<'EVENTS'
customer-101:order-101-created
customer-101:order-101-authorized
customer-101:order-101-fulfilled
customer-202:order-202-created
customer-202:order-202-authorized
customer-202:order-202-fulfilled
EVENTS

cat capstone-events.txt | docker exec -i "$KAFKA_CAPSTONE_CONTAINER" \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --topic sre-capstone-orders \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

Read back all six events:

```bash
timeout 30s docker exec "$KAFKA_CAPSTONE_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --topic sre-capstone-orders --from-beginning \
  --property print.key=true --property print.partition=true \
  --property print.offset=true --max-messages 6
```

**Expected:** each customer's events share a partition under the same producer partitioning configuration, and offsets increase within that partition. Output across partitions may interleave. **Do not infer global order** from terminal output.

## 6. Lab C — Consumer replay and offset inspection

Consume the six events with an isolated group:

```bash
timeout 30s docker exec "$KAFKA_CAPSTONE_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --topic sre-capstone-orders \
  --group sre-capstone-billing --from-beginning \
  --max-messages 6

docker exec "$KAFKA_CAPSTONE_CONTAINER" \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --describe --group sre-capstone-billing
```

The console consumer may commit on shutdown with a delay. If no offsets are immediately visible, wait briefly and inspect again. To replay without touching the billing group's offsets:

```bash
timeout 30s docker exec "$KAFKA_CAPSTONE_CONTAINER" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server "$KAFKA_CAPSTONE_BOOTSTRAP" \
  --topic sre-capstone-orders \
  --group "sre-capstone-audit-$(date +%s)" \
  --from-beginning --max-messages 6
```

**Incident lesson:** replay is normal Kafka behavior. A downstream database or payment system needs idempotency keyed by a stable business event ID; Kafka producer idempotence alone does not deduplicate external side effects.

## 7. Lab D — One-broker outage and leader election

**Choose one broker to stop** after inspecting leader distribution. This example stops `broker2`. Do not stop a second node: combined-role three-controller quorum would lose its majority.

Capture a baseline:

```bash
docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-capstone-orders > capstone-before.txt

docker compose stop broker2
sleep 20

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-capstone-orders > capstone-degraded.txt
```

Inspect:

```bash
cat capstone-before.txt
cat capstone-degraded.txt
```

**Expected:** broker2 is removed from ISR after failure detection; partitions formerly led by broker2 elect eligible new leaders. If broker2 led no partition, this is a follower-loss exercise, not a leader-failover proof. Record that distinction rather than claiming a successful leader-election test.

## 8. Lab E — Write during degraded replication

With broker2 stopped, broker1 and broker3 remain available:

```bash
printf 'customer-303:order-303-created\n' | \
  docker exec -i kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server broker1:9092 \
  --topic sre-capstone-orders \
  --producer-property acks=all \
  --producer-property delivery.timeout.ms=15000 \
  --property parse.key=true --property key.separator=:
```

**Expected:** a write can succeed with two healthy ISR replicas and `min.insync.replicas=2`. A failure may indicate incomplete leader election, ISR degradation, or client configuration issues. Inspect evidence; do not relax durability to make the test pass.

## 9. Lab F — Restore and validate ISR recovery

```bash
docker compose start broker2
sleep 30

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-capstone-orders > capstone-recovered.txt

cat capstone-recovered.txt
```

**Expected:** broker2 catches up and returns to ISR for all assigned partitions. Leadership may remain with the replacement leader. Compare before, degraded, and recovered descriptions.

## 10. Automated acceptance script

Save as `verify-capstone.sh` in the dedicated Compose directory. This is a **non-destructive health/functional smoke test** that creates and deletes only a uniquely named temporary topic. It does not itself stop a broker; failure injection remains a supervised exercise.

```bash
#!/usr/bin/env bash
set -euo pipefail

C=kafka-ch04-broker1
BS=broker1:9092
CLI=/opt/kafka/bin
TOPIC="sre-capstone-verify-$(date +%s)-$$"

run() { docker exec "$C" "$CLI/$1" "${@:2}"; }
cleanup() {
  run kafka-topics.sh --bootstrap-server "$BS" \
    --delete --topic "$TOPIC" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo '[1/5] Checking running broker containers'
for service in broker1 broker2 broker3; do
  docker compose ps --status running --services | grep -qx "$service" || \
    { echo "FAIL: $service is not running"; exit 1; }
done

echo '[2/5] Creating RF=3/minISR=2 verification topic'
run kafka-topics.sh --bootstrap-server "$BS" --create \
  --topic "$TOPIC" --partitions 1 --replication-factor 3 \
  --config min.insync.replicas=2 >/dev/null

echo '[3/5] Waiting for three ISR replicas'
ready=0
for attempt in $(seq 1 30); do
  desc="$(run kafka-topics.sh --bootstrap-server "$BS" --describe --topic "$TOPIC")"
  if printf '%s\n' "$desc" | grep -Eq 'Isr: [0-9]+,[0-9]+,[0-9]+'; then
    ready=1
    break
  fi
  sleep 2
done
test "$ready" -eq 1 || { echo 'FAIL: ISR did not converge to 3'; exit 1; }

echo '[4/5] Producing with acks=all'
printf 'capstone-health-event\n' | docker exec -i "$C" \
  "$CLI/kafka-console-producer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --producer-property acks=all

echo '[5/5] Reading the event'
value="$(timeout 30s docker exec "$C" "$CLI/kafka-console-consumer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --from-beginning --max-messages 1)"
test "$value" = 'capstone-health-event' || \
  { echo "FAIL: unexpected value: $value"; exit 1; }

echo 'PASS: 3 brokers, RF=3, ISR=3, minISR=2, produce and consume'
```

```bash
chmod +x verify-capstone.sh
./verify-capstone.sh
```

**Verification limitation:** A passing script validates only its own assertions. It does not prove zone isolation, production durability, failure recovery, consumer exactly-once processing, or security posture. Capture supervised failure-injection evidence separately.

## 11. Additional SRE incident exercises

### Incident 1 — Broker offline, ISR degraded

**Symptoms:** broker disappears; partition ISR shrinks; client retries increase.

**Hypothesis:** broker crash, storage pressure, network partition, or planned restart.

**Investigate:** container/broker status, logs, leader/ISR snapshots, controller quorum state.

**Recovery:** restore the affected broker, wait for replica catch-up, verify application processing.

### Incident 2 — Writes rejected below min ISR

**Symptoms:** `NotEnoughReplicas` or `NotEnoughReplicasAfterAppend` with `acks=all`.

**Hypothesis:** insufficient healthy replicas.

**Investigate:** RF, min ISR, assigned replicas, current ISR, broker errors.

**Recovery:** restore replication. Do not weaken min ISR without documented risk acceptance.

**Note:** The three-combined-node lab must **not** stop a second node merely to trigger this condition. Use a separately designed isolated scenario with supported fault injection if testing under-min-ISR behavior.

### Incident 3 — Duplicate order fulfillment

**Symptoms:** replayed record causes duplicate external side effect.

**Hypothesis:** processing succeeded before offset commit, then consumer crashed.

**Investigate:** business event ID, downstream idempotency, consumer offset commit, crash timeline.

**Recovery:** stop unsafe side effects, reconcile records, replay with deduplication.

### Incident 4 — Key ordering regression

**Symptoms:** related events are applied in the wrong order.

**Hypothesis:** changed partition count/partitioner, multiple producers, or parallel downstream processing.

**Investigate:** topic metadata history, event keys, partition/offset, processing concurrency.

**Recovery:** restore the key-to-partition contract or redesign ordered processing; avoid blind partition-count increases.

### Incident 5 — Controller quorum instability

**Symptoms:** metadata operations stall and elections are unstable.

**Hypothesis:** controller node/network failures, storage errors, quorum configuration mismatch.

**Investigate:** controller logs, KRaft quorum status, connectivity and cluster ID.

**Recovery:** restore a supported quorum carefully; never format a controller's production storage as a casual troubleshooting step.

## 12. Production SRE runbook

**Trigger:** one or more Kafka partitions are unavailable, under-replicated, or violating end-to-end delivery objectives.

1. **Open incident:** identify severity, impacted applications, topics, partitions, tenants, and owner.
2. **Freeze risky changes:** pause partition-count modifications, topic deletions, unclean elections, and offset resets.
3. **Capture evidence:** broker/controller health, ISR and leaders, consumer lag, produce errors, storage/network metrics, deployment history.
4. **Assess durability:** inspect RF, min ISR, effective producer acknowledgments, and potential acknowledged-data loss.
5. **Isolate cause:** distinguish broker loss, metadata quorum problems, network/storage bottlenecks, and consumer-side failures.
6. **Restore safely:** recover one failure domain at a time and monitor ISR catch-up.
7. **Validate:** test a bounded produce/consume path, event completeness, consumer lag, business idempotency, and latency.
8. **Communicate:** publish impact, timeline, residual risk, mitigation, and next update.
9. **Postmortem:** capture root cause, failed assumptions, alert gaps, runbook improvements, and assigned prevention work.

### Required incident evidence

| Evidence | Why it matters |
|---|---|
| Topic describe snapshots before/during/after | Demonstrates leader and ISR changes |
| Producer acknowledgment/error logs | Identifies write failures and ambiguous outcomes |
| Consumer group offsets and lag | Identifies replay or processing delays |
| Broker and controller logs | Distinguishes replication and metadata issues |
| Business event IDs | Enables downstream reconciliation |
| Recovery timeline | Measures detection and restoration time |

## 13. Capstone grading rubric — 100 points

| Requirement | Points |
|---|---:|
| Preflight checks and environment isolation | 10 |
| RF=3/minISR=2 topic configuration | 10 |
| Keyed production and ordering explanation | 10 |
| Consumer offset/replay demonstration | 10 |
| Accurate leader/ISR baseline | 10 |
| One-broker fault injection with evidence | 10 |
| Write verification under one-broker loss | 10 |
| Broker recovery and ISR convergence | 10 |
| Automated acceptance test and limitations | 10 |
| Incident report, safety decisions and runbook | 10 |

**Pass:** at least 85/100, with no unsafe action. **Part 01 completion:** all five chapters published and capstone assessed; publication alone does not imply a learner passed the capstone.

## 14. Example incident report template

```text
Incident ID:
Start / detection / mitigation / resolution timestamps:
Environment and Kafka version:
Affected topics and consumer groups:
Customer impact:
Pre-incident ISR and leaders:
Failure injected:
During-incident ISR and leaders:
Producer errors / acks configuration:
Consumer lag and replay observations:
Recovery steps:
Post-recovery ISR and application validation:
Data-loss or duplication assessment:
Root cause:
Corrective actions / owners / deadlines:
Evidence links:
```

## 15. Cleanup and retention of evidence

Save `capstone-before.txt`, `capstone-degraded.txt`, `capstone-recovered.txt`, and the incident report **outside** the disposable Docker volume before cleanup.

Delete only the capstone topic if retaining the lab for Chapter 006:

```bash
docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --delete --topic sre-capstone-orders
```

If completely finished with this **dedicated** Chapter 004/005 lab, confirm the Compose directory and run:

```bash
docker compose ps
docker compose down -v
```

**Warning:** `down -v` permanently deletes the lab's Kafka storage volumes. Do not use it in shared or production environments.

## 16. Reference material

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kafka operations](https://kafka.apache.org/documentation/#operations)
- [Kafka producer configuration](https://kafka.apache.org/documentation/#producerconfigs)
- [Kafka consumer configuration](https://kafka.apache.org/documentation/#consumerconfigs)

## 17. Part 01 retrospective and next milestone

This capstone closes **Part 01 — Kafka Fundamentals and Architecture**:

- Chapter 001: Kafka architecture and distributed streaming fundamentals.
- Chapter 002: topics, partitions, offsets, and ordering.
- Chapter 003: producers, consumers, and message delivery semantics.
- Chapter 004: replication, leaders, ISR, and fault tolerance.
- Chapter 005: architecture and failure recovery capstone.

**Next:** Chapter 006 — Kafka Installation, Configuration and KRaft Cluster Bootstrap, opening Part 02 — Installation, KRaft and Cluster Administration.

---

**Publication verification** confirms source content exists on GitHub; it does not confirm that Docker labs, fault injection, automated tests, or security controls have been executed or approved.
