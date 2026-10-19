# Chapter 001 — Kafka Architecture and Distributed Streaming Fundamentals
## Kubernetes-first primary labs — Architecture and Kubernetes CRDs

**Platform:** Kubernetes, Strimzi Operator, KRaft and KafkaNodePool. **Source of truth:** [Shared Kubernetes Lab Foundation](../kubernetes/README.md). **Execution:** Pending. **Security review:** Pending.

**Prerequisite:** Follow the [Kubernetes-first Kafka Lab Platform](../kubernetes/README.md) for operator/CRD version checks, Kafka cluster manifests, namespace, CLI Pod, KafkaTopic and evidence collection. Use `kubectl` rather than Docker Compose for all new exercises. Commands and CRD schemas require validation against the installed Strimzi release.

**Lab A:** Deploy a version-compatible Strimzi operator and KRaft Kafka/KafkaNodePool manifests from the shared guide. Inspect `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide` and explain how the operator, controllers, brokers, Services and PVCs map to the architecture. **Lab B:** Create `sre-lab-events` via KafkaTopic and send two events from the CLI Pod. **Validation:** Kafka Ready=True, six role-specific Pods in the HA variant, topic metadata accessible, both events consumed. **Troubleshooting:** Kafka CR not Ready → inspect Strimzi operator logs, storage class, CRD schema and Pod events. **Runbook:** preserve Kafka CR, PVCs and logs before changes.

**Automated acceptance baseline:** `kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s`; `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc`; `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml` (if created); and a bounded produce/consume smoke test from the Kafka CLI Pod. Save exit codes and sanitized outputs. A successful manifest apply alone is not a pass.

**Legacy note:** The original Docker Compose examples preserved later in this chapter are **superseded historical reference**, not the supported primary lab. Do not execute their destructive commands as part of the Kubernetes workflow. Their Docker-specific assessment steps must be interpreted using the Kubernetes replacement above.

---


**Part:** 01 — Kafka Fundamentals and Architecture  
**Audience:** Kafka administrators, SREs, DBREs and platform engineers  
**Lab scope:** disposable local environment only

## Learning objectives

Explain event streaming, brokers, topics, partitions, offsets, consumer groups, replication, ISR, leaders, and KRaft metadata management. Deploy a single-node Kafka KRaft lab, publish and consume events, inspect topic metadata, and practice a safe recovery.

## 1. Core architecture

Apache Kafka is a distributed, append-only event log. Producers publish records to topics. Each topic is divided into ordered partitions; ordering is guaranteed within a partition, not across the topic. Brokers host partition replicas. A partition leader handles reads and writes while followers replicate. Consumers track offsets, and members of a consumer group divide assigned partitions among themselves.

KRaft replaces ZooKeeper for metadata management. In production, use dedicated controllers with a fault-tolerant quorum, multiple brokers across failure domains, and replicated topics. This single-node lab intentionally provides no high availability.

```text
Producer(s) --> Kafka Broker --> Topic: orders
                                  |-- Partition 0: offset 0,1,2...
                                  |-- Partition 1: offset 0,1,2...
                                  +-- Partition 2: offset 0,1,2...
                                         |
                                         v
                                  Consumer Group
KRaft Controller --> cluster metadata and leadership decisions
```

### Reliability vocabulary

- **Replication factor:** number of replicas per partition.
- **ISR:** replicas sufficiently caught up to qualify as in-sync.
- **acks=all:** producer waits for acknowledgment from all replicas required by the broker's ISR rules; combine with appropriate `min.insync.replicas` for durability.
- **Consumer lag:** distance between the latest offsets and a consumer group's committed progress; assess alongside processing latency.
- **RPO/RTO:** acceptable data loss and recovery time, established by business requirements and tested by recovery drills.

## 2. Prerequisites

Docker with Compose v2, 2+ GB available memory, and ports 9092/9093 available. Use a pinned, reviewed Apache Kafka image version for reproducibility; the example below uses `apache/kafka:4.1.0` and should be validated against the current upstream image documentation before use.

## 3. Hands-on lab: start a KRaft broker

Create an empty directory, then save the following as `compose.yaml`:

```yaml
services:
  kafka:
    image: apache/kafka:4.1.0
    hostname: kafka
    container_name: kafka-ch001
    ports:
      - "127.0.0.1:9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
```

This configuration uses plaintext and single replicas for local learning only. Never expose it to untrusted networks.

```bash
docker compose up -d
docker compose ps
docker exec kafka-ch001 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

## 4. Topic and message lifecycle

```bash
docker exec kafka-ch001 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic orders --partitions 3 --replication-factor 1
docker exec kafka-ch001 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic orders
printf 'order-1001\norder-1002\n' | docker exec -i kafka-ch001 /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic orders
docker exec kafka-ch001 /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic orders --from-beginning --timeout-ms 10000
```

Expected: topic reports three partitions, one replica each, and the consumer prints both orders (the timeout command may exit nonzero after reading available records). Do not assume a cross-partition order.

## 5. Automated smoke validation

Save as `smoke-test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
KAFKA="/opt/kafka/bin"
docker exec kafka-ch001 "$KAFKA/kafka-topics.sh" --bootstrap-server localhost:9092 --describe --topic orders | grep -q 'PartitionCount: 3'
docker exec kafka-ch001 "$KAFKA/kafka-broker-api-versions.sh" --bootstrap-server localhost:9092 >/dev/null
echo 'PASS: broker reachable and orders topic has three partitions'
```

Run `bash smoke-test.sh`. This validates metadata and reachability, not replication durability or end-to-end delivery guarantees.

## 6. SRE incident simulation

**Scenario:** the broker becomes unavailable.

1. Record baseline health with `docker compose ps` and `kafka-topics.sh --describe`.
2. Run `docker compose stop kafka` and observe that metadata requests fail.
3. Run `docker compose start kafka`; wait for readiness, then rerun `bash smoke-test.sh`.
4. Capture recovery duration, command outputs, and any missing messages. Do not claim zero data loss without a durability test.

**Troubleshooting matrix**

| Symptom | Likely cause | Investigation | Recovery |
|---|---|---|---|
| Bootstrap timeout | broker stopped | `docker compose ps`, `docker compose logs kafka` | start broker, verify readiness |
| Connection refused | listener or port issue | inspect listener settings and published ports | correct configuration, restart lab |
| Topic absent | topic never created | `kafka-topics.sh --list` | create topic after verifying target cluster |
| Consumer sees nothing | offsets already advanced or wrong topic | inspect group offsets and topic | use fresh group or `--from-beginning` in lab |
| Only one replica | deliberate lab setting | describe topic | production requires multi-broker design |

## 7. Production runbook: broker unreachable

**Trigger:** failed client requests, broker unavailable alert, or controller metadata instability.

1. Declare severity according to customer impact; note cluster, region, broker ID, and first alert time.
2. Check broker reachability, listener/DNS configuration, TLS/SASL errors, disk space, JVM health, and network connectivity.
3. Review controller quorum health and offline partitions; avoid simultaneous controller or broker restarts.
4. Evaluate replication health and availability before restarting a broker or changing placement.
5. Follow approved change and incident processes. Do not delete logs, reformat storage, or force unsafe leader elections.
6. Verify produce/consume success, ISR recovery, consumer lag trends, and customer-facing SLIs.
7. Record incident timeline, evidence, contributing factors, and follow-up actions.

## 8. Assessment (10 points)

1. Explain why Kafka ordering is per partition (2).
2. Distinguish broker leadership from KRaft controller leadership (2).
3. Explain the purpose of ISR and `acks=all` (2).
4. Demonstrate topic creation and metadata inspection (2).
5. Demonstrate broker recovery and a passing smoke test (2).

**Pass criterion:** 8/10, with a working lab and evidence of recovery.

## 9. Cleanup

```bash
docker compose down -v
```

This removes disposable lab data. Never run destructive cleanup commands against a shared or production cluster.

## Verification status

- Documentation authored and published: yes, subject to repository confirmation.
- Commands executed in a live Kafka environment: not yet.
- Security and production change review: pending.
