# Chapter 004 — Kafka Replication, Leaders, ISR and Fault Tolerance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 01 — Kafka Fundamentals and Architecture  
**Audience:** Kafka administrators, SREs, DBREs and platform engineers  
**Prerequisites:** Chapters 001–003; Docker and a disposable Kafka lab  
**Publication:** Complete | **Live lab execution:** Pending | **Security review:** Pending

> **Safety boundary:** This chapter introduces deliberate broker failures. Execute only against the disposable three-broker lab described below. Do not restart production brokers, reassign replicas, enable unclean leader election, or change durability settings without an approved maintenance or incident plan.

## 1. Learning objectives

After completing this chapter, you should be able to:

1. Explain leader and follower replicas, replication factor, and the in-sync replica set (ISR).
2. Distinguish the high watermark (HW), log end offset (LEO), and last stable offset (LSO).
3. Describe the interaction of `acks=all`, `min.insync.replicas`, and ISR shrinkage.
4. Recognize leader election, leader epoch changes, and the risk of unclean leader election.
5. Identify the limits of a single-broker lab and provision an isolated three-broker KRaft cluster.
6. Simulate a broker failure, inspect partition leadership, and verify recovery.
7. Diagnose under-replicated partitions and produce a safe production runbook.

## 2. Kafka replication architecture

A topic is divided into partitions. Each partition has one leader replica and zero or more follower replicas. Producers and consumers normally interact with the leader; followers replicate the partition log.

```text
                        Topic: orders, partition 0
                      Replication factor (RF) = 3

Producer ---> Broker 1: LEADER   log: [0][1][2][3][4]
                     |                  |
                     +---- fetch ------> Broker 2: FOLLOWER [0][1][2][3][4]
                     |
                     +---- fetch ------> Broker 3: FOLLOWER [0][1][2][3]

ISR: {1,2,3}   Leader: 1   min.insync.replicas: 2
```

Replication factor is the number of assigned copies, **not** the number currently healthy. The ISR is the subset of replicas sufficiently caught up with the leader according to Kafka's replica synchronization rules. A replica can remain assigned but fall out of ISR if it lags beyond configured thresholds.

### 2.1 Essential terminology

| Term | Definition | Operational implication |
|---|---|---|
| Leader | Replica serving reads/writes for a partition | Leader loss requires election |
| Follower | Replica fetching data from the leader | Lagging followers can leave ISR |
| RF | Total configured replica count | RF=1 has no replica redundancy |
| ISR | Replicas considered in sync | Affects durable acknowledgments and leader eligibility |
| HW | Offset boundary through which records are replicated to ISR and eligible for normal visibility | A record above HW may be lost after leader change |
| LEO | Position after the last record in a replica's log | Different replicas may have different LEOs |
| LSO | Transaction-aware visibility boundary for `read_committed` consumers | Can be behind HW due to open transactions |
| Leader epoch | Monotonic identifier for leader terms | Used to detect stale leaders and divergent logs |
| Offline partition | Partition with no usable leader | Clients cannot normally read/write it |
| Under-replicated partition | One or more assigned replicas are not in ISR | Availability/durability risk |
| Under-min-ISR partition | ISR count below configured minimum | `acks=all` writes can fail |

The HW and LSO are offset boundaries, not globally unique record IDs. In a healthy nontransactional partition, LSO may coincide with HW, but they represent different concepts.

## 3. Producer durability matrix

Assume RF=3, `min.insync.replicas=2`, and a healthy leader.

| Condition | ISR count | `acks=all` | `acks=1` |
|---|---:|---|---|
| All replicas in sync | 3 | Accepted if request succeeds and replication requirements are met | Leader-only acknowledgment |
| One follower out of ISR | 2 | Can succeed | Can succeed, but weaker durability |
| Only leader in ISR | 1 | Rejected due to insufficient ISR | May still succeed, increasing loss risk |
| No leader | 0 | Fails until leadership restored | Fails until leadership restored |

`min.insync.replicas` is enforced for writes requesting `acks=all`; it is **not** a substitute for replication or failure-domain separation. With `acks=1`, the broker may acknowledge before followers have replicated the data.

A majority quorum is critical to **KRaft metadata** consensus, but data-partition ISR and write acknowledgment are separate mechanisms. Do not equate Kafka's partition replication with a generic majority-commit protocol.

## 4. Leader election and failure modes

### 4.1 Clean election

When the leader fails, Kafka can elect an eligible ISR replica as the new leader. The partition may be temporarily unavailable during the transition. Clients refresh metadata and retry as configured.

### 4.2 Unclean election

If no eligible in-sync replica is available, enabling unclean leader election may restore availability by electing an out-of-sync replica **at the cost of possible acknowledged data loss**. Production defaults and effective per-topic settings must be inspected. For critical data, prefer preserving consistency and investigating the outage rather than casually enabling unclean election.

### 4.3 Preferred leader

The preferred replica is the first replica in the assignment list. Actual leadership can move during failures and maintenance. A nonpreferred leader is not inherently an incident; assess load, placement, and policy before moving leadership.

### 4.4 Broker versus controller failure

In KRaft, metadata controllers manage cluster metadata and leadership decisions; brokers store and serve partition data. Some small labs combine broker and controller roles, but production architectures should follow supported sizing, controller quorum, and failure-domain guidance. A three-controller quorum tolerates one controller failure **for metadata availability**, assuming a healthy majority; that is distinct from a partition's RF and ISR.

## 5. Isolated three-broker lab

The previous chapters' RF=1 single-node lab cannot demonstrate follower lag or leader failover. This chapter uses an **independent three-node combined broker/controller KRaft lab**, suitable for learning but **not production architecture**.

### 5.1 Requirements

- Docker Engine and Docker Compose plugin.
- Three free host ports: `19192`, `19193`, `19194`.
- At least approximately 6 GiB free RAM for the lab environment; tune for your host.
- Kafka container image `apache/kafka:4.1.0`, subject to availability in your environment.
- A dedicated directory, e.g. `kafka-ch04-lab`.

Use a fixed three-voter KRaft quorum for this self-contained learning cluster. All nodes must share the same cluster ID and controller voter configuration.

### 5.2 Create the cluster ID

```bash
mkdir -p kafka-ch04-lab
cd kafka-ch04-lab

docker run --rm apache/kafka:4.1.0 \
  /opt/kafka/bin/kafka-storage.sh random-uuid
```

Copy the printed ID to `CLUSTER_ID` in a local `.env` file:

```bash
# Replace this placeholder with the UUID printed above.
printf 'CLUSTER_ID=%s\n' 'REPLACE_WITH_GENERATED_CLUSTER_ID' > .env
```

**Do not commit** a real environment file containing secrets; the ID itself is not a credential. Kafka image startup configuration and KRaft quorum settings are version-specific. Inspect container logs and the image's published examples if startup behavior differs.

### 5.3 Docker Compose

Save as `compose.yaml`:

```yaml
services:
  broker1:
    image: apache/kafka:4.1.0
    hostname: broker1
    container_name: kafka-ch04-broker1
    ports:
      - "19192:19192"
    environment:
      CLUSTER_ID: ${CLUSTER_ID}
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@broker1:9093,2@broker2:9093,3@broker3:9093"
      KAFKA_LISTENERS: "INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19192"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://broker1:9092,EXTERNAL://localhost:19192"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - broker1-data:/var/lib/kafka/data
  broker2:
    image: apache/kafka:4.1.0
    hostname: broker2
    container_name: kafka-ch04-broker2
    ports:
      - "19193:19193"
    environment:
      CLUSTER_ID: ${CLUSTER_ID}
      KAFKA_NODE_ID: 2
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@broker1:9093,2@broker2:9093,3@broker3:9093"
      KAFKA_LISTENERS: "INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19193"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://broker2:9092,EXTERNAL://localhost:19193"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - broker2-data:/var/lib/kafka/data
  broker3:
    image: apache/kafka:4.1.0
    hostname: broker3
    container_name: kafka-ch04-broker3
    ports:
      - "19194:19194"
    environment:
      CLUSTER_ID: ${CLUSTER_ID}
      KAFKA_NODE_ID: 3
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@broker1:9093,2@broker2:9093,3@broker3:9093"
      KAFKA_LISTENERS: "INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19194"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://broker3:9092,EXTERNAL://localhost:19194"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - broker3-data:/var/lib/kafka/data
volumes:
  broker1-data:
  broker2-data:
  broker3-data:
```

**Version note:** Kafka 4.x supports KRaft quorum configurations whose bootstrap/format requirements vary by static versus dynamic quorum mode. This Compose file uses the fixed voter-list pattern and assumes the official image's startup script formats fresh storage consistently. If a particular 4.1.x image rejects the configuration, do not reuse partially formatted volumes with a different cluster ID; inspect `docker compose logs`, consult the version-matched image instructions, and rebuild the disposable lab cleanly. Do not apply unverified quorum workarounds to production.

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=80
```

Wait for the brokers and metadata quorum to initialize before proceeding. All three containers should be running; startup can take tens of seconds.

## 6. Lab A — Topic replication and ISR inspection

Run Kafka tools inside broker1, where the internal listener is reachable:

```bash
export KAFKA_CH04=kafka-ch04-broker1

docker exec "$KAFKA_CH04" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --create --if-not-exists --topic sre-replication-ch04 \
  --partitions 3 --replication-factor 3 \
  --config min.insync.replicas=2

docker exec "$KAFKA_CH04" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-replication-ch04
```

**Expected:** three partitions, each with three assigned replicas and an ISR containing three broker IDs once replication is caught up. Replica and leader assignments can vary.

Record each partition's leader, replicas, and ISR. A healthy RF=3 topic should not show offline partitions or persistent under-replication.

## 7. Lab B — Produce and consume replicated data

```bash
printf '%s\n' \
  'order-1:created' \
  'order-1:paid' \
  'order-2:created' \
| docker exec -i "$KAFKA_CH04" /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server broker1:9092 \
  --topic sre-replication-ch04 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true \
  --property key.separator=:

timeout 30s docker exec "$KAFKA_CH04" \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server broker1:9092 \
  --topic sre-replication-ch04 --from-beginning \
  --property print.key=true --property print.partition=true \
  --property print.offset=true --max-messages 3
```

**Expected:** all three records are readable; records sharing `order-1` use the same partition in this stable-key test. `acks=all` requires ISR conditions to be met, but the console-producer lab is not a substitute for formal durability testing.

## 8. Lab C — Leader failover

First capture partition leaders:

```bash
docker exec "$KAFKA_CH04" /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-replication-ch04
```

Select a partition whose leader is **broker2 (node ID 2)** if one exists. If none does, choose another leader broker and adapt the stop command and bootstrap endpoint so that the CLI remains on a running node.

For the example below, stop broker2:

```bash
docker compose stop broker2
sleep 15

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-replication-ch04
```

**Expected:** partitions previously led by broker2 elect another eligible ISR leader, and the ISR excludes broker2 after failure detection. A temporary election delay is normal. Because combined-role nodes also participate in the controller quorum, stopping one node leaves two of three controllers; stopping a second combined-role node can lose metadata quorum and is **outside the safe scope of this lab**.

If broker2 was not leader for any partition, the test demonstrates follower loss and ISR shrinkage rather than leader failover. Record the distinction.

Recover:

```bash
docker compose start broker2
sleep 20

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-replication-ch04
```

**Expected:** broker2 rejoins ISR after catching up. Leadership need not automatically return to broker2.

## 9. Lab D — Verify write safety during one-broker outage

With broker2 stopped **and both other nodes healthy**, an RF=3, min ISR=2 topic can generally continue accepting `acks=all` writes. Test on the disposable topic:

```bash
docker compose stop broker2
sleep 15
printf '%s\n' 'order-3:created-during-outage' | \
  docker exec -i kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server broker1:9092 \
  --topic sre-replication-ch04 \
  --producer-property acks=all \
  --producer-property delivery.timeout.ms=15000 \
  --property parse.key=true --property key.separator=:

docker compose start broker2
```

**Expected:** the write succeeds if an eligible leader is elected and at least two replicas remain in ISR. If it fails, inspect topic ISR, broker logs, and controller health. Do **not** weaken `min.insync.replicas` to make the lab pass.

## 10. Automated smoke test

Save as `verify-ch04.sh` in the Compose directory:

```bash
#!/usr/bin/env bash
set -euo pipefail
C=kafka-ch04-broker1
BS=broker1:9092
CLI=/opt/kafka/bin
TOPIC="sre-ch04-check-$(date +%s)-$$"

run() { docker exec "$C" "$CLI/$1" "${@:2}"; }
cleanup() {
  run kafka-topics.sh --bootstrap-server "$BS" \
    --delete --topic "$TOPIC" >/dev/null 2>&1 || true
}
trap cleanup EXIT

test "$(docker compose ps --status running --services | grep -c '^broker[123]$')" -eq 3 || \
  { echo 'FAIL: three brokers must be running'; exit 1; }

run kafka-topics.sh --bootstrap-server "$BS" --create \
  --topic "$TOPIC" --partitions 1 --replication-factor 3 \
  --config min.insync.replicas=2 >/dev/null

# Poll for ISR convergence rather than assuming instant replication.
ready=0
for attempt in $(seq 1 30); do
  desc="$(run kafka-topics.sh --bootstrap-server "$BS" --describe --topic "$TOPIC")"
  if printf '%s\n' "$desc" | grep -Eq 'Isr: [0-9]+,[0-9]+,[0-9]+'; then
    ready=1
    break
  fi
  sleep 2
done
test "$ready" -eq 1 || { echo 'FAIL: ISR did not reach 3 replicas'; exit 1; }

printf 'health-check-001\n' | docker exec -i "$C" \
  "$CLI/kafka-console-producer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --producer-property acks=all

result="$(timeout 20s docker exec "$C" "$CLI/kafka-console-consumer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --from-beginning --max-messages 1)"

test "$result" = 'health-check-001' || \
  { echo "FAIL: unexpected consumed value: $result"; exit 1; }

echo 'PASS: RF=3, ISR=3, acknowledged produce and consume'
```

```bash
chmod +x verify-ch04.sh
./verify-ch04.sh
```

**Limitations:** This checks initial replica health and basic messaging; it does not prove crash consistency, rack diversity, or the behavior of a production controller quorum. CLI output may vary by version.

## 11. Incident simulations and troubleshooting

### Scenario A — Under-replicated partitions

**Signal:** `UnderReplicatedPartitions > 0` or topic description shows ISR smaller than replicas.

**Investigate:** broker liveness, replica fetch lag, network latency, disk I/O, CPU saturation, throttling, log directory errors, and deployment changes.

**Response:** restore follower health and observe ISR convergence. Do not immediately increase RF or force reassignment; first understand whether the issue is transient or systemic.

### Scenario B — Under-min-ISR and failed writes

**Signal:** producer receives `NotEnoughReplicas` or `NotEnoughReplicasAfterAppend` with `acks=all`.

**Investigate:** effective topic `min.insync.replicas`, ISR count, RF, and leader health.

**Response:** prioritize restoring replicas and protecting durability. Lowering min ISR may improve availability while weakening guarantees; require explicit business-risk approval.

### Scenario C — Offline partitions

**Signal:** partition leader unavailable, client metadata errors, request timeouts.

**Investigate:** leader election, broker availability, controller quorum, replica assignment, and whether any ISR member remains.

**Response:** restore eligible replicas and metadata quorum. Avoid unclean election unless authorized and data-loss risk is accepted.

### Scenario D — Repeated leader movement

**Signal:** leader election rate rises, latency spikes, producers retry.

**Investigate:** broker restarts, unstable nodes, controller connectivity, network partitions, storage stalls, and placement imbalance.

**Response:** stabilize infrastructure and confirm leader distribution after recovery. Avoid repeatedly forcing preferred-leader election during active incidents.

### Scenario E — Replica cannot rejoin ISR

**Signal:** follower remains out of ISR after broker restart.

**Investigate:** log directory failure, disk capacity, fetcher errors, corrupted data, throttling, version incompatibility, and authentication failures.

**Response:** preserve logs, resolve underlying cause, and allow supported replica catch-up. Never delete broker data directories on a production cluster as an ad hoc fix.

## 12. Production SRE runbook — replication and leader incident

**Trigger:** sustained under-replication, offline partitions, produce failures, or leader election instability.

1. **Declare impact:** record affected cluster, topics, partitions, tenants, producer/consumer errors, and customer-facing symptoms.
2. **Capture evidence:** topic descriptions, leader/ISR snapshots, controller health, broker logs, replication metrics, disk and network utilization.
3. **Assess quorum and blast radius:** distinguish controller-quorum health from partition-leader health; check whether failures span racks or zones.
4. **Preserve durability:** do not lower `min.insync.replicas`, enable unclean election, or reset storage without formal approval.
5. **Restore infrastructure:** recover failed brokers, disks, network paths, or controller connectivity one failure domain at a time.
6. **Track convergence:** verify replica fetch progress, ISR recovery, offline partition count, and producer error rate.
7. **Validate application recovery:** check end-to-end event completeness, consumer lag, processing age, and duplicate handling.
8. **Close incident:** document acknowledged-data risk, outage duration, root cause, mitigations, and corrective actions.

### Observability and alerts

- `UnderReplicatedPartitions` and `UnderMinIsrPartitionCount`.
- `OfflinePartitionsCount` and unexpected leader elections.
- `UncleanLeaderElectionsPerSec` (any occurrence warrants investigation).
- Replica fetch lag, follower catch-up time, ISR shrink/expand rates.
- Broker request latency, produce error rate, disk utilization and I/O wait.
- Controller quorum health and election changes.
- End-to-end event age, consumer lag, and business-level completeness.

Metric names and availability differ by Kafka release and exporter. Confirm exact JMX attributes and dashboard mappings for the deployed version.

## 13. Production architecture checklist

- [ ] Use supported KRaft controller topology and appropriate failure domains.
- [ ] Document replication factor and min ISR for critical topics.
- [ ] Require `acks=all` for workflows that need stronger acknowledged-write durability.
- [ ] Distribute replicas across racks/zones and validate broker rack configuration.
- [ ] Disable or explicitly govern unclean leader election according to business requirements.
- [ ] Alert on under-replication, offline partitions, unclean elections, and producer errors.
- [ ] Define safe rolling maintenance and upgrade procedures.
- [ ] Test one-broker failure, slow follower, network partition, and restoration.
- [ ] Validate disk, network, and replication capacity under degraded conditions.
- [ ] Establish restore/replay sources and documented RPO/RTO targets.

## 14. Assessment — 100 points

| Exercise | Points |
|---|---:|
| Explain leader, follower, RF, and ISR | 10 |
| Differentiate HW, LEO, and LSO | 10 |
| Explain `acks=all` with `min.insync.replicas` | 10 |
| Describe clean versus unclean election | 10 |
| Provision isolated three-broker KRaft lab | 10 |
| Create RF=3 topic and inspect ISR | 10 |
| Demonstrate a one-broker outage and recovery | 10 |
| Explain controller quorum versus partition ISR | 10 |
| Diagnose an under-min-ISR write failure | 10 |
| Write a safe replication incident runbook | 10 |

**Pass target:** 80/100, with safe lab completion and an accurate recovery explanation. Do not mark execution complete until tested.

## 15. Cleanup

**Warning:** The following commands destroy only this chapter's dedicated lab containers and volumes. Confirm your working directory contains the intended `compose.yaml`.

```bash
docker compose ps
docker compose down -v
```

Keep the lab if you plan to reuse it in Chapter 005; in that case, do not run cleanup yet. Never apply `down -v` to a shared environment.

## 16. References

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kafka operations guide](https://kafka.apache.org/documentation/#operations)
- [Kafka configuration reference](https://kafka.apache.org/documentation/#brokerconfigs)
- [KRaft documentation](https://kafka.apache.org/documentation/#kraft)

**Next:** Chapter 005 — Kafka Architecture and Failure Recovery Capstone Lab.

---

**Verification policy:** GitHub publication is separate from running the lab and conducting a security review. Commands, output, and version-specific startup behavior must be independently tested before marking them verified.
