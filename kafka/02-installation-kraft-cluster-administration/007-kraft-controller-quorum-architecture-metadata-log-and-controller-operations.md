# Chapter 007 — KRaft Controller Quorum Architecture, Metadata Log and Controller Operations
## Kubernetes-first primary labs — Controller quorum and metadata operations

**Platform:** Kubernetes, Strimzi Operator, KRaft and KafkaNodePool. **Source of truth:** [Shared Kubernetes Lab Foundation](../kubernetes/README.md). **Execution:** Pending. **Security review:** Pending.

**Prerequisite:** Follow the [Kubernetes-first Kafka Lab Platform](../kubernetes/README.md) for operator/CRD version checks, Kafka cluster manifests, namespace, CLI Pod, KafkaTopic and evidence collection. Use `kubectl` rather than Docker Compose for all new exercises. Commands and CRD schemas require validation against the installed Strimzi release.

**Lab A:** From the Kubernetes tools Pod, run `kafka-metadata-quorum.sh --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status` and `describe --replication`. **Lab B:** Map voter IDs to controller-role Pods using `kubectl -n kafka-lab get pods -o wide` and KafkaNodePool resources. **Lab C:** In an isolated HA lab only, inject failure into one controller Pod, observe election/quorum behavior, and allow Strimzi reconciliation; never stop two controllers. **Validation:** majority survives, metadata high watermark progresses, controller Pod returns and replication lag normalizes. **Runbook:** preserve controller storage, avoid cluster-ID regeneration, escalate unsupported voter changes.

**Automated acceptance baseline:** `kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s`; `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc`; `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml` (if created); and a bounded produce/consume smoke test from the Kafka CLI Pod. Save exit codes and sanitized outputs. A successful manifest apply alone is not a pass.

**Legacy note:** The original Docker Compose examples preserved later in this chapter are **superseded historical reference**, not the supported primary lab. Do not execute their destructive commands as part of the Kubernetes workflow. Their Docker-specific assessment steps must be interpreted using the Kubernetes replacement above.

---


**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 02 — Installation, KRaft and Cluster Administration  
**Audience:** Kafka SREs, administrators, platform engineers and DBREs  
**Prerequisites:** Chapters 001–006, Linux, Docker Compose, Kafka CLI  
**Target:** Apache Kafka 4.1.x KRaft  
**Publication:** Complete | **Live lab execution:** Pending | **Security review:** Pending

> **Safety:** Controller failures and quorum operations can make a Kafka cluster unavailable. Run failure injection only in the disposable three-node Chapter 004 lab. Never reformat metadata storage, change quorum voters, or stop a majority of controllers in production without an approved, version-specific procedure.

## 1. Learning objectives

You will learn to:

1. Explain KRaft metadata consensus and the active-controller role.
2. Distinguish controller quorum from broker partition ISR.
3. Interpret leader ID, leader epoch, high watermark, voters, observers and replication lag.
4. Describe static and dynamic quorum configuration differences.
5. Inspect controller quorum status with Kafka CLI tools.
6. Demonstrate one-controller failure and safe restoration in an isolated lab.
7. Diagnose controller-election instability, metadata lag and quorum loss.
8. Produce an enterprise SRE incident runbook and acceptance evidence.

## 2. KRaft control-plane architecture

KRaft uses a replicated metadata log to track topics, partitions, configurations, broker registrations and other cluster metadata. One controller acts as the active metadata leader; other controllers replicate metadata and can take over leadership when the quorum can elect a successor.

```text
                         Kafka clients
                               |
                       Kafka broker APIs
                               |
                +--------------+--------------+
                |                             |
             Broker 4                      Broker 5
                |                             |
                +---------- metadata ---------+
                               |
               KRaft metadata controller quorum
          +--------------------+--------------------+
          |                    |                    |
     Controller 1         Controller 2         Controller 3
       follower             LEADER               follower
          |                    |                    |
          +----------- replicated metadata log ----+
                               |
                      committed metadata
```

The **controller quorum** handles cluster metadata; **partition replicas and ISR** handle topic data. A healthy metadata quorum does not guarantee every partition has a leader, and a healthy partition ISR does not guarantee metadata administration can progress during a controller quorum outage.

### 2.1 Majority and fault tolerance

For a voting quorum of `2f+1` controllers, up to `f` voter failures can be tolerated while retaining a majority, assuming the remaining nodes can communicate and function. A three-voter quorum requires two voters to make progress. A five-voter quorum requires three. A one-controller lab has no controller fault tolerance.

**Important:** Availability depends on both node health and connectivity. Three controllers deployed in one failure domain are not equivalent to three controllers across independent failure domains.

### 2.2 Metadata log and snapshots

Controllers append metadata records to the replicated log. A committed metadata state can be reconstructed using the log and supported snapshots. Snapshots reduce replay cost; they are not a substitute for a tested disaster-recovery plan or durable storage.

Controller storage failure can affect the ability to elect leaders, create topics, change configuration, and manage partition leadership. Never delete or reformat controller metadata directories as an ad hoc troubleshooting step.

### 2.3 Leader epochs and fencing

Controller leadership is term/epoch based. The protocol prevents stale leaders from safely continuing to mutate metadata after leadership changes. In operations, a rising controller election count or repeated epoch changes is a sign to investigate network instability, disk latency, or controller restarts.

## 3. Quorum status terminology

| Field or concept | Meaning | SRE interpretation |
|---|---|---|
| `ClusterId` | Unique identity of the Kafka cluster | Must match intended deployment |
| `LeaderId` | Active metadata controller node ID | Can change after election |
| `LeaderEpoch` | Controller leadership term | Unexpected frequent changes suggest instability |
| `HighWatermark` | Committed metadata log boundary | Progress should resume after healthy quorum restored |
| `CurrentVoters` | Voting controllers | Determines quorum majority |
| `CurrentObservers` | Nonvoting metadata followers, when present | Not counted toward voting majority |
| `MaxFollowerLag` | Largest observed metadata follower lag | Sustained growth may signal replication issues |
| `MaxFollowerLagTimeMs` | Duration-related lag indicator, when reported | Investigate slow or disconnected followers |

Output fields depend on Kafka release and static/dynamic quorum mode. Do not write monitoring parsers that assume all versions expose identical formatting.

## 4. Static versus dynamic KRaft quorum

Kafka releases and bootstrap modes differ:

- **Static quorum:** voter set is configured using `controller.quorum.voters`; membership changes require careful version-supported procedures.
- **Dynamic quorum:** controller membership can be administered through supported bootstrap, add/remove controller workflows and metadata quorum commands, subject to Kafka version and configuration.
- **Migration:** do not switch quorum modes by changing a single setting on a running cluster. Consult version-specific upgrade/migration documentation.

For this chapter, reuse the **fixed three-voter** Chapter 004 Compose lab. It is deliberately a combined-role deployment and does not exercise dynamic membership modification.

## 5. Lab prerequisites and isolation

Use the dedicated Chapter 004 lab directory containing its `compose.yaml`, not the Chapter 006 single-node cluster.

```bash
cd kafka-ch04-lab
docker compose config --quiet
docker compose up -d
docker compose ps
```

Expected containers:

```text
kafka-ch04-broker1
kafka-ch04-broker2
kafka-ch04-broker3
```

Verify Kafka CLI connectivity from a running broker:

```bash
docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server broker1:9092 >/dev/null
```

**Startup caveat:** Kafka 4.1.x quorum bootstrapping is version- and image-specific. If the Chapter 004 static-voter Compose configuration is not accepted by the pinned image, fix the isolated bootstrap using official version-matched instructions before continuing. Do not alter live production quorum configuration to mimic this lab.

## 6. Lab A — Inspect controller quorum status

```bash
docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --status
```

Record the cluster ID, leader ID, leader epoch, high watermark, and voter list.

Inspect replication:

```bash
docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --replication
```

**Expected:** one active controller leader, three voting controllers in the fixed-voter lab, and followers making progress. Exact output depends on Kafka release and quorum mode.

### 6.1 Read-only snapshot capture

```bash
mkdir -p evidence-ch07

docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --status \
  > evidence-ch07/quorum-before.txt

docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --replication \
  > evidence-ch07/replication-before.txt
```

Do not publish real cluster IDs, private hostnames, credentials, or sensitive operational metadata to a public repository.

## 7. Lab B — Metadata operations with a healthy quorum

Create a disposable topic:

```bash
docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --create --if-not-exists \
  --topic sre-metadata-ch07 \
  --partitions 3 --replication-factor 3

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-metadata-ch07
```

**Expected:** metadata change is committed, topic appears, and partitions acquire leaders. Topic RF=3 is independent of the controller quorum's three voters even though the lab colocates the roles.

## 8. Lab C — Controlled controller failure

This lab stops **one combined-role node only**. The three-voter metadata quorum should retain two voters, but some topic replicas will also become unavailable until recovery.

First inspect the quorum leader. To avoid stopping the CLI's own container, this example stops `broker2`; whether broker2 was the active controller determines whether the test includes a controller-leader election or only follower loss.

```bash
docker compose stop broker2
sleep 20

docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --status

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-metadata-ch07
```

**Expected:** a two-voter majority remains available. If controller node 2 was leader, a new leader is elected; if it was a follower, the existing leader can remain. The topic may temporarily show reduced ISR, because the stopped node also hosts partition replicas.

**Safety limit:** do not stop another combined-role node. A second failure would remove the three-voter quorum's majority and can cause cluster metadata unavailability.

### 8.1 Restore the controller

```bash
docker compose start broker2
sleep 30

docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --status

docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --replication
```

**Expected:** all three voters are again available, and the restarted controller catches up with the metadata log. Leadership does not need to return to node 2.

## 9. Lab D — Validate metadata progress after recovery

```bash
docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --create --if-not-exists \
  --topic sre-metadata-recovery-ch07 \
  --partitions 1 --replication-factor 3

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --describe --topic sre-metadata-recovery-ch07
```

If the topic exists and acquires a leader, this demonstrates metadata administration after recovery. It does not prove all historical metadata is recoverable after catastrophic loss.

Capture post-recovery evidence:

```bash
docker exec kafka-ch04-broker1 \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server broker1:9092 describe --status \
  > evidence-ch07/quorum-after.txt
```

## 10. Automated read-only quorum health test

Save as `verify-ch07.sh` in the Chapter 004 Compose directory:

```bash
#!/usr/bin/env bash
set -euo pipefail
C=kafka-ch04-broker1
BS=broker1:9092
CLI=/opt/kafka/bin

echo '[1/4] Verify three containers running'
for service in broker1 broker2 broker3; do
  docker compose ps --status running --services | grep -qx "$service" || \
    { echo "FAIL: $service is not running"; exit 1; }
done

echo '[2/4] Verify broker API'
docker exec "$C" "$CLI/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[3/4] Verify metadata quorum status'
status="$(docker exec "$C" "$CLI/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status)"
printf '%s\n' "$status"
printf '%s\n' "$status" | grep -q 'LeaderId:' || \
  { echo 'FAIL: no leader field'; exit 1; }
printf '%s\n' "$status" | grep -q 'CurrentVoters:' || \
  { echo 'FAIL: no voters field'; exit 1; }

echo '[4/4] Verify metadata replication command'
docker exec "$C" "$CLI/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --replication >/dev/null

echo 'PASS: controller quorum CLI responds and broker is reachable'
```

```bash
chmod +x verify-ch07.sh
./verify-ch07.sh
```

**Limitations:** This checks CLI responsiveness and expected fields, not the actual number of healthy voters, metadata durability, or full failure tolerance. Review `CurrentVoters`, replication lag, and logs manually; adjust parsers if version output differs.

## 11. Failure and incident scenarios

### Scenario 1 — Controller leader election storm

**Symptoms:** frequent `LeaderEpoch` changes, metadata latency spikes, topic operations intermittently fail.

**Hypotheses:** network instability, controller CPU saturation, disk latency, repeated restarts, quorum placement issues.

**Investigate:** controller election metrics, logs, quorum status over time, storage latency, packet loss, change history.

**Mitigate:** stabilize the failing infrastructure and avoid simultaneous controller restarts. Do not force repeated elections.

### Scenario 2 — Metadata follower lag

**Symptoms:** `MaxFollowerLag` grows; one controller falls behind or fails to rejoin.

**Hypotheses:** disk throughput limits, high metadata churn, network issues, controller resource pressure.

**Investigate:** metadata replication output, controller storage metrics, network RTT, broker/controller logs.

**Mitigate:** restore follower performance and verify catch-up. Do not delete metadata storage to “resync” a production controller.

### Scenario 3 — Quorum majority lost

**Symptoms:** metadata changes stall; new leaders cannot be reliably elected; broker registrations or topic operations fail.

**Hypotheses:** two of three voters unavailable, network partition, incompatible quorum config, storage failures.

**Investigate:** reachability of original voters, cluster ID, node IDs, controller logs, quorum configuration.

**Mitigate:** restore the original majority via supported procedures. Arbitrary voter edits and reformatting can worsen recovery.

### Scenario 4 — Cluster ID mismatch

**Symptoms:** controller or broker fails to join; startup logs indicate cluster ID inconsistency.

**Hypotheses:** incorrect data volume, accidental format, copied storage, environment mismatch.

**Investigate:** deployment history, storage mount identity, `meta.properties` on the affected node, intended cluster ID.

**Mitigate:** preserve storage and establish correct provenance. Never regenerate the production cluster ID to force a join.

### Scenario 5 — Controller healthy, partitions offline

**Symptoms:** quorum reports a leader, but some topic partitions have no leader.

**Hypotheses:** broker failures, missing eligible ISR replicas, replica storage failure, partition-level issue.

**Investigate:** topic descriptions, offline partition metrics, ISR, broker health.

**Mitigate:** restore partition replicas; do not misdiagnose this as necessarily a controller quorum failure.

### Scenario 6 — Excessive metadata churn

**Symptoms:** high controller load, metadata propagation latency, topic administration delays.

**Hypotheses:** excessive topic/partition creation, frequent configuration changes, unstable brokers, automation loops.

**Investigate:** audit/change logs, topic counts, controller request rates, metadata log growth.

**Mitigate:** rate-limit or correct automation and reduce unnecessary metadata mutations.

## 12. Troubleshooting decision table

| Signal | Control plane or data plane? | First safe action |
|---|---|---|
| `LeaderId` absent / no majority | Control plane | Check controller connectivity and quorum |
| High metadata follower lag | Control plane | Inspect controller disk/network health |
| Topic describe shows offline partition | Data plane, possibly control-plane impact | Check leader/ISR and brokers |
| `NotEnoughReplicas` with `acks=all` | Data plane | Inspect ISR and min ISR |
| Cluster ID mismatch | Node identity/storage | Preserve storage and compare identity |
| Broker bootstrap works but clients time out | Client network/listener | Inspect advertised listeners |
| Frequent controller epochs | Control plane | Inspect controller election and restarts |

## 13. Production SRE runbook — KRaft controller incident

**Trigger:** controller quorum degradation, repeated elections, metadata unavailability, or controller replication lag.

1. **Declare incident:** capture cluster, environment, affected applications, start time, severity, and incident commander.
2. **Protect metadata:** halt controller restarts, formatting, membership changes, and destructive automation.
3. **Capture evidence:** quorum status and replication, controller logs, node IDs, cluster ID, storage mounts, network topology, and recent changes.
4. **Determine majority:** identify active voters, leader, unreachable voters, and network partitions; distinguish static from dynamic quorum mode.
5. **Assess data plane:** check offline partitions, ISR, produce errors, and consumer impact separately.
6. **Recover carefully:** restore original voters, storage, or network connectivity according to the deployed Kafka version's supported recovery procedure.
7. **Verify quorum:** stable leader epoch, advancing high watermark, acceptable follower lag, and successful metadata operations.
8. **Verify applications:** topic describe, bounded produce/consume, consumer lag, and event completeness.
9. **Communicate:** summarize service impact, metadata availability, potential data risk, mitigation, and ETA.
10. **Close:** document root cause, evidence, prevention tasks, runbook improvements, and owners.

**Never assume:** a recovered metadata leader implies all topic replicas have recovered or all business events have been processed.

## 14. Operational dashboards and SLOs

Monitor the following categories, adapting metric names to the Kafka release and exporter:

- Active controller and unexpected controller election rate.
- Metadata quorum leader epoch changes and follower replication lag.
- Metadata high watermark progress and snapshot/metadata log storage.
- Controller request latency, event queue latency, and CPU/disk/network saturation.
- Broker registration errors and cluster membership churn.
- Offline partitions, under-replicated partitions, and under-min-ISR partitions.
- Producer request failures and end-to-end consumer processing age.

**Example SLOs (illustrative, not universal):** metadata administration success at or above 99.9% per rolling 30 days, no sustained controller majority loss, and controller follower lag below an environment-specific threshold. Measure and tune based on actual workload and operational objectives.

## 15. Production readiness checklist

- [ ] Controller quorum mode and Kafka version documented.
- [ ] Controller voter count and failure-domain placement reviewed.
- [ ] Node IDs and cluster ID protected from accidental changes.
- [ ] Metadata storage persistent, monitored, and backed by a recovery strategy.
- [ ] Quorum health, leader epochs, and follower lag monitored.
- [ ] Broker and controller roles separated where appropriate.
- [ ] TLS/SASL, ACLs, network policy, and secrets management implemented.
- [ ] Safe rolling maintenance and controller recovery runbooks approved.
- [ ] One-controller failure and restoration tested in staging.
- [ ] Quorum disaster recovery and upgrade procedures version-validated.

## 16. Assessment — 100 points

| Requirement | Points |
|---|---:|
| Explain metadata log, snapshots and controller leadership | 10 |
| Explain majority quorum and failure tolerance | 10 |
| Distinguish controller quorum from partition ISR | 10 |
| Inspect quorum status and replication | 10 |
| Identify active leader and voters | 10 |
| Demonstrate one-controller failure safely | 10 |
| Restore controller and validate catch-up | 10 |
| Diagnose a metadata follower lag incident | 10 |
| Explain static versus dynamic quorum operations | 10 |
| Produce a safe controller recovery runbook | 10 |

**Pass target:** 80/100, including safe lab execution and correct interpretation of controller quorum behavior. Do not mark labs complete without captured evidence.

## 17. Cleanup

Delete only disposable topics created in this chapter:

```bash
docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --delete --topic sre-metadata-ch07

docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 \
  --delete --topic sre-metadata-recovery-ch07
```

Retain the three-node lab for Chapter 008 if desired. If destroying the dedicated environment, confirm the Compose project before `docker compose down -v`; this permanently removes its volumes.

## 18. References and next chapter

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kafka KRaft operations](https://kafka.apache.org/documentation/#kraft)
- [Kafka configuration reference](https://kafka.apache.org/documentation/#brokerconfigs)
- [Kafka metadata quorum CLI documentation](https://kafka.apache.org/documentation/#kraft)

**Next:** Chapter 008 — Kafka Broker Configuration, Dynamic Settings and Cluster Administration.

---

**Verification boundary:** GitHub publication confirms the chapter exists, not that its lab has been executed, its outputs reproduced, or its security controls independently approved.
