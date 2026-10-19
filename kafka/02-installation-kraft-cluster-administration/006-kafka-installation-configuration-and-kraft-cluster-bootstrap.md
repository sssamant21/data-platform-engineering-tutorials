# Chapter 006 — Kafka Installation, Configuration and KRaft Cluster Bootstrap
## Kubernetes-first primary labs — Strimzi operator installation and cluster bootstrap

**Platform:** Kubernetes, Strimzi Operator, KRaft and KafkaNodePool. **Source of truth:** [Shared Kubernetes Lab Foundation](../kubernetes/README.md). **Execution:** Pending. **Security review:** Pending.

**Prerequisite:** Follow the [Kubernetes-first Kafka Lab Platform](../kubernetes/README.md) for operator/CRD version checks, Kafka cluster manifests, namespace, CLI Pod, KafkaTopic and evidence collection. Use `kubectl` rather than Docker Compose for all new exercises. Commands and CRD schemas require validation against the installed Strimzi release.

**Lab A:** Install a release-compatible Strimzi operator in an isolated Kubernetes cluster and confirm Kafka/KafkaNodePool CRDs. **Lab B:** Apply the shared KRaft Kafka/KafkaNodePool template after substituting a supported Kafka version and validating the installed CRD with server-side dry run. **Lab C:** Inspect Stateful workload Pods, PVCs, bootstrap Service and controller quorum. **Lab D:** Produce/consume from a version-matched CLI Pod and verify persistence across a **supported operator-managed restart**; never delete PVCs. **Validation:** Kafka Ready=True, metadata quorum status readable, all expected Pods and volumes present. **Runbook:** check Strimzi operator logs, PVC provisioning, StorageClass and node scheduling before attempting recovery.

**Automated acceptance baseline:** `kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s`; `kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc`; `kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml` (if created); and a bounded produce/consume smoke test from the Kafka CLI Pod. Save exit codes and sanitized outputs. A successful manifest apply alone is not a pass.

**Legacy note:** The original Docker Compose examples preserved later in this chapter are **superseded historical reference**, not the supported primary lab. Do not execute their destructive commands as part of the Kubernetes workflow. Their Docker-specific assessment steps must be interpreted using the Kubernetes replacement above.

---


**Track:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 02 — Installation, KRaft and Cluster Administration  
**Audience:** Kafka administrators, SREs, DBREs and platform engineers  
**Prerequisites:** Chapters 001–005; Linux fundamentals; Docker Compose; Bash  
**Target:** Apache Kafka 4.1.x (KRaft)  
**Publication:** Complete | **Live lab:** Pending | **Security review:** Pending

> **Operational safety:** This chapter creates a disposable cluster with PLAINTEXT listeners. It is not a production deployment. Never format an existing Kafka data directory, change `cluster.id`, or modify controller quorum membership on a live cluster without an approved, version-specific procedure and verified recovery plan.

## 1. Learning objectives

After completing this chapter you should be able to:

1. Explain Kafka 4.x KRaft architecture and the role of metadata controllers.
2. Compare broker-only, controller-only, and combined node roles.
3. Plan cluster IDs, node IDs, listener endpoints, and persistent storage.
4. Bootstrap a disposable Kafka cluster using the official container image.
5. Understand static versus dynamic KRaft controller quorums and version-dependent formatting.
6. Inspect cluster metadata quorum, broker connectivity, and topic creation.
7. Diagnose common bootstrap failures using repeatable checks.
8. Prepare an installation and recovery runbook for enterprise operations.

## 2. KRaft architecture

Kafka 4.x uses KRaft for cluster metadata management rather than ZooKeeper. Metadata controllers replicate cluster metadata through a Raft-based quorum; brokers host topic partitions and serve client traffic.

```text
                      Kafka clients
                           |
                 bootstrap / advertised
                       broker listener
                           |
          +----------------+----------------+
          |                                 |
      Broker node 4                     Broker node 5
      partition logs                    partition logs
          |                                 |
          +----------- metadata -----------+
                           |
                KRaft controller quorum
              +------------+------------+
              |            |            |
         Controller 1  Controller 2  Controller 3
             metadata log + leader election
```

**Controller quorum versus partition replication:** controller quorum determines availability of metadata decisions; topic replica ISR determines durability and availability of topic data. They are separate failure domains and have different operational signals.

### 2.1 Node roles

| Role | `process.roles` | Primary responsibility | Typical use |
|---|---|---|---|
| Controller only | `controller` | Metadata quorum participation | Preferred production separation at scale |
| Broker only | `broker` | Store and serve topic partitions | Production data plane |
| Combined | `broker,controller` | Both functions on one node | Small disposable labs; evaluate support and risk for real deployments |

A three-controller quorum can tolerate one controller loss while retaining a majority. Three controllers are not the same thing as three data replicas. Use failure-domain-aware placement and an odd-sized controller quorum appropriate for the supported deployment.

### 2.2 Essential identifiers and paths

| Setting | Purpose | Failure if wrong |
|---|---|---|
| `node.id` | Unique identity of broker/controller node | Identity collision, startup failure |
| `cluster.id` | Shared identity written during storage format | Cluster mismatch; do not regenerate for an existing cluster |
| `process.roles` | Broker, controller, or combined | Incorrect topology |
| `controller.listener.names` | Listener(s) for controller communication | Quorum connectivity failures |
| `listeners` | Network interfaces and ports bound locally | Port collision or unreachable listener |
| `advertised.listeners` | Endpoints returned to Kafka clients | Clients connect to bootstrap but fail after metadata |
| `listener.security.protocol.map` | Map listener names to security protocols | Authentication/handshake failures |
| `inter.broker.listener.name` | Listener used by broker-to-broker traffic | Replication connectivity failures |
| `log.dirs` | Topic data storage paths | Capacity, permission, persistence problems |
| `metadata.log.dir` | Optional dedicated metadata-log directory | Quorum metadata storage availability |

### 2.3 Static versus dynamic quorum

KRaft quorum setup depends on Kafka release and chosen quorum mode. A **static** quorum commonly uses `controller.quorum.voters`; a **dynamic** quorum uses a bootstrap/controller membership workflow and supports membership changes through supported administrative procedures. Formatting flags and initial-controller bootstrap differ by mode.

Do not mix the two modes or assume a static-voter Compose example can be converted to dynamic quorum by adding one property. For any production installation, pin the Kafka release and follow that version's official KRaft bootstrap and upgrade instructions.

## 3. Installation planning checklist

Before provisioning Kafka, define:

- Kafka distribution and pinned version; verify artifact provenance and image digests.
- CPU, memory, JVM heap, page cache, disk IOPS, disk throughput, and storage capacity.
- Controller quorum size, rack/zone topology, network RTT, and failure domains.
- Broker counts, expected partitions, replica placement, replication factor, and min ISR.
- DNS, listener naming, client access paths, TLS/SASL, ACLs, and certificate rotation.
- Data and metadata storage persistence, backup/recovery strategy, and RPO/RTO.
- Monitoring, log shipping, change control, secrets management, and audit retention.
- Rolling upgrade and rollback compatibility constraints.

**Production security:** require encrypted and authenticated listeners where appropriate, restrictive network access, separate administrative principals, least-privilege ACLs, and secrets outside Git. The lab deliberately omits these controls for isolation and clarity.

## 4. Hands-on lab — isolated single-node KRaft bootstrap

This first lab uses the official Apache Kafka image and a disposable container. It is the simplest way to confirm installation, Kafka CLI paths, and broker readiness before more advanced cluster administration.

### 4.1 Prerequisites

```bash
docker --version
docker compose version
docker pull apache/kafka:4.1.0
```

Create a new directory that is not used by previous chapters:

```bash
mkdir -p kafka-ch06-lab
cd kafka-ch06-lab
```

### 4.2 Docker Compose

Save as `compose.yaml`:

```yaml
services:
  kafka:
    image: apache/kafka:4.1.0
    container_name: kafka-ch06
    hostname: kafka
    ports:
      - "19092:19092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:9093"
      KAFKA_LISTENERS: "INTERNAL://:9092,CONTROLLER://:9093,EXTERNAL://:19092"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka:9092,EXTERNAL://localhost:19092"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "INTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
    volumes:
      - kafka-data:/var/lib/kafka/data

volumes:
  kafka-data:
```

The image's startup helper is expected to initialize fresh KRaft storage for this disposable example. Kafka 4.1.x quorum-mode details can vary with image startup defaults; inspect the container's logs and official image documentation if the static-voter configuration is rejected. **Do not format existing volumes or improvise production quorum changes.**

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose logs --tail=100 kafka
```

### 4.3 Readiness validation

```bash
docker exec kafka-ch06 /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka:9092
```

**Expected:** broker API versions are returned. This confirms the broker can respond on the internal listener; it does not prove production readiness or replica durability.

## 5. Lab A — Cluster identity and metadata quorum

Inspect quorum status using the version-matched CLI:

```bash
docker exec kafka-ch06 /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka:9092 describe --status
```

Expected output typically includes the cluster ID, leader ID, leader epoch, high watermark, and voter information. Exact fields vary by Kafka version and quorum mode.

Inspect quorum replication:

```bash
docker exec kafka-ch06 /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server kafka:9092 describe --replication
```

**Interpretation:** a one-controller quorum has no controller fault tolerance. Do not claim it is highly available. For a production three-controller quorum, compare controller replication and leader stability across nodes.

## 6. Lab B — Topic lifecycle and producer/consumer smoke test

```bash
docker exec kafka-ch06 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --create \
  --topic sre-bootstrap-ch06 \
  --partitions 3 --replication-factor 1

docker exec kafka-ch06 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --describe \
  --topic sre-bootstrap-ch06

printf 'bootstrap-event-001\nbootstrap-event-002\n' | \
  docker exec -i kafka-ch06 /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka:9092 --topic sre-bootstrap-ch06 \
  --producer-property acks=all

timeout 30s docker exec kafka-ch06 /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 --topic sre-bootstrap-ch06 \
  --from-beginning --max-messages 2
```

**Expected:** two events are consumed. With replication factor 1, `acks=all` acknowledges the single replica only and does not provide broker-failure tolerance.

## 7. Lab C — Listener and advertised endpoint validation

Kafka clients first connect to a bootstrap server, then use the broker endpoints returned in metadata. A wrong advertised listener can make bootstrap succeed while subsequent requests fail.

From the host, test the external listener:

```bash
# Requires a Kafka CLI installed on the host, or use an appropriate
# container on the host network with matching advertised endpoints.
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:19092
```

If the host does not have Kafka CLI installed, use a compatible client on the host instead. The external listener advertises `localhost:19092`, which is correct only for a client on the same Docker host. Remote clients need a routable advertised hostname; do not expose this PLAINTEXT lab port to untrusted networks.

**Failure exercise:** review the difference between `listeners` (bind addresses) and `advertised.listeners` (client metadata addresses). Do not deliberately break a shared cluster's listener settings.

## 8. Lab D — Persistence and restart

Check that data survives a container restart while the named Docker volume remains intact:

```bash
docker compose restart kafka
sleep 15

docker exec kafka-ch06 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 --describe \
  --topic sre-bootstrap-ch06

timeout 30s docker exec kafka-ch06 /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 --topic sre-bootstrap-ch06 \
  --from-beginning --max-messages 2
```

**Expected:** the topic and both events remain. If not, investigate volume mounts, startup formatting, and log directory settings. Never use `docker compose down -v` before completing the persistence test.

## 9. Automated acceptance test

Save as `verify-ch06.sh` in the lab directory:

```bash
#!/usr/bin/env bash
set -euo pipefail
C=kafka-ch06
BS=kafka:9092
CLI=/opt/kafka/bin
TOPIC="sre-ch06-verify-$(date +%s)-$$"

run() { docker exec "$C" "$CLI/$1" "${@:2}"; }
cleanup() {
  run kafka-topics.sh --bootstrap-server "$BS" \
    --delete --topic "$TOPIC" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo '[1/5] Validate container'
docker inspect -f '{{.State.Running}}' "$C" | grep -qx true

echo '[2/5] Validate broker API'
run kafka-broker-api-versions.sh --bootstrap-server "$BS" >/dev/null

echo '[3/5] Validate metadata quorum'
run kafka-metadata-quorum.sh --bootstrap-server "$BS" \
  describe --status >/dev/null

echo '[4/5] Create topic and produce'
run kafka-topics.sh --bootstrap-server "$BS" --create \
  --topic "$TOPIC" --partitions 1 --replication-factor 1 >/dev/null
printf 'kafka-ch06-health\n' | docker exec -i "$C" \
  "$CLI/kafka-console-producer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --producer-property acks=all

echo '[5/5] Consume and compare'
value="$(timeout 30s docker exec "$C" "$CLI/kafka-console-consumer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --from-beginning --max-messages 1)"
test "$value" = 'kafka-ch06-health' || \
  { echo "FAIL: unexpected value: $value"; exit 1; }

echo 'PASS: Kafka KRaft bootstrap, metadata, topic and message path'
```

```bash
chmod +x verify-ch06.sh
./verify-ch06.sh
```

**Test scope:** this smoke test checks a single-node disposable cluster only. It does not verify controller fault tolerance, security, disaster recovery, or performance SLOs.

## 10. Production architecture — separate controllers and brokers

A common production architecture separates controller and broker roles:

```text
             Controllers                  Brokers
         +----------------+         +----------------+
         | controller-1   |         | broker-4       |
         | controller-2   | <-----> | broker-5       |
         | controller-3   |         | broker-6       |
         +----------------+         +----------------+
           metadata quorum           data replication
```

**Planning rules:**

1. Place controllers across independent failure domains where supported.
2. Keep controller storage latency predictable and monitor metadata log replication.
3. Use unique node IDs and stable hostnames.
4. Configure broker and controller listeners separately.
5. Keep metadata-log storage durable; do not reformat existing metadata storage.
6. Pin compatible broker/controller versions and plan upgrades using supported procedures.
7. Set topic RF and min ISR according to availability/durability requirements.
8. Verify ACLs, TLS/SASL, monitoring, and backup/recovery procedures before production.

## 11. Troubleshooting matrix

| Symptom | Likely cause | Safe first check |
|---|---|---|
| Container exits on startup | Invalid KRaft quorum config, storage formatting, port conflict | Container logs and effective configuration |
| `InconsistentClusterIdException` | Storage belongs to another cluster | Inspect volume and cluster ID; do not reformat production storage |
| `Duplicate node.id` | Node identity collision | Compare configs across all nodes |
| Metadata quorum unavailable | Controller reachability, majority loss, DNS | Quorum status and controller logs |
| Client bootstrap succeeds but produce fails | Incorrect advertised listeners | Inspect returned broker metadata and network routes |
| Topic create fails | Missing broker/controller readiness, ACLs, RF too high | Check broker count, topic configs, auth |
| Data disappears after restart | Ephemeral storage or accidental volume deletion | Inspect mounts and startup logs |
| ISR remains degraded | Replica network/disk issue | Broker logs and replica metrics |
| High metadata latency | Controller load, disk stalls, network RTT | Controller CPU, disk and quorum replication |
| Authentication failures | TLS/SASL mismatch or wrong principal | Client and broker security configuration |

## 12. Production SRE incident scenarios

### Scenario A — New broker cannot join

**Signal:** node is running but never becomes available for partition assignment.

**Investigate:** node ID uniqueness, cluster ID, inter-broker listener, DNS, credentials, KRaft registration, broker logs.

**Response:** fix the configuration or network issue; preserve existing data volumes. Do not create a new cluster ID for a joining broker.

### Scenario B — Controller quorum loses majority

**Signal:** metadata operations stall; leader election cannot progress reliably.

**Investigate:** controller reachability, disk I/O, node failures, quorum status, and election logs.

**Response:** restore enough original controller voters to regain a majority using supported procedures. Avoid arbitrary voter-list edits or storage reformatting.

### Scenario C — Wrong advertised listener

**Signal:** Kafka CLI connects to bootstrap but producer/consumer traffic times out.

**Investigate:** client network namespace, advertised hostnames, broker metadata, firewalls, TLS/SASL configuration.

**Response:** correct advertised endpoints through reviewed configuration change, test from each client network, and validate all broker addresses.

### Scenario D — Accidental data volume loss

**Signal:** topics disappear after restart or the broker reports a new cluster identity.

**Investigate:** volume deletion, log directory mapping, orchestration changes, cluster ID, backups, storage events.

**Response:** stop destructive automation, preserve remaining disks, invoke tested backup/restore or upstream replay. Do not assume offset resets recover deleted data.

### Scenario E — Configuration drift

**Signal:** broker behavior differs across nodes or after restart.

**Investigate:** deployed config checksums, environment overrides, dynamic broker configs, GitOps/IaC change history.

**Response:** compare effective configurations, restore approved desired state, and roll changes safely.

## 13. Production runbook — KRaft bootstrap or controller incident

**Trigger:** new cluster bootstrap failure, broker registration failure, controller quorum degradation, or metadata operation outage.

1. **Establish scope:** cluster ID, Kafka version, controller/broker topology, affected services, and customer impact.
2. **Freeze risky changes:** no reformatting, quorum membership changes, volume deletion, or unapproved rolling restarts.
3. **Preserve evidence:** effective configs, node IDs, metadata quorum status, storage mounts, logs, and change history.
4. **Identify failure plane:** controller quorum, broker registration, client listener, security, or partition replication.
5. **Restore supported quorum:** recover network, storage, or failed original controllers; escalate to version-specific recovery procedure if necessary.
6. **Validate broker registration:** verify API connectivity, topic metadata, leader availability, and ISR health.
7. **Validate application path:** bounded produce/consume test, consumer lag, end-to-end event completeness.
8. **Communicate risk:** clarify whether there is a metadata outage, data availability issue, or suspected data loss.
9. **Close:** capture timeline, root cause, prevention work, runbook improvements, and owner.

**Key metrics:** active controller count, controller election rate, metadata quorum replication lag, offline partitions, under-replicated partitions, broker registration failures, request latency, and end-to-end processing age. Exact metrics depend on Kafka version and monitoring exporter.

## 14. Operational readiness checklist

- [ ] Kafka version and container/artifact digest pinned and reviewed.
- [ ] Controller topology and quorum bootstrap mode documented.
- [ ] Node IDs, cluster ID, listeners, and storage paths verified.
- [ ] Data and metadata volumes persistent and monitored.
- [ ] Broker/controller failure domains independently assessed.
- [ ] TLS/SASL, ACLs, secrets, and audit logging implemented for production.
- [ ] RF/min ISR and producer durability settings reviewed.
- [ ] Cluster startup, restart, and recovery tested in staging.
- [ ] Monitoring, alerting, backup, and incident response prepared.
- [ ] Rollback, upgrade, and disaster recovery plans approved.

## 15. Assessment — 100 points

| Task | Points |
|---|---:|
| Explain KRaft controllers versus brokers | 10 |
| Distinguish static and dynamic quorum setup | 10 |
| Document node/cluster identity requirements | 10 |
| Deploy disposable single-node Kafka 4.1.x | 10 |
| Inspect metadata quorum status | 10 |
| Create and describe a topic | 10 |
| Produce and consume test events | 10 |
| Demonstrate restart persistence | 10 |
| Diagnose an advertised-listener failure | 10 |
| Produce a safe controller incident runbook | 10 |

**Passing target:** 80/100, including a safe bootstrap and persistence test. Mark live execution complete only after actual test evidence exists.

## 16. Cleanup

The following commands affect **only the dedicated `kafka-ch06-lab` Compose project**. Inspect the current directory and container names first.

```bash
docker compose ps
docker compose down
```

This retains the named volume. To permanently remove disposable lab data after preserving any needed evidence:

```bash
docker compose down -v
```

**Warning:** `-v` permanently removes Kafka log storage in this lab. Never run it against production or a shared environment.

## 17. References and next chapter

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kafka operations and KRaft](https://kafka.apache.org/documentation/#kraft)
- [Kafka configuration reference](https://kafka.apache.org/documentation/#brokerconfigs)
- [Official Apache Kafka container image](https://hub.docker.com/r/apache/kafka)

**Next:** Chapter 007 — KRaft Controller Quorum Architecture, Metadata Log and Controller Operations.

---

**Verification boundary:** Publishing this source to GitHub does not certify that the lab has been executed or security-reviewed. Commands must be validated against the pinned Kafka release and actual deployment topology.
