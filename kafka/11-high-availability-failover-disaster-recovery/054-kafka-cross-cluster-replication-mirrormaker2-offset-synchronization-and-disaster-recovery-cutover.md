# Chapter 054 — Kafka Cross-Cluster Replication, MirrorMaker 2, Offset Synchronization and Disaster Recovery Cutover

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 11 — High Availability, Failover and Disaster Recovery (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–053, especially 041–053  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use two disposable, separately scoped Kafka clusters and synthetic topics. Real regional cutover, active-writer fencing, offset synchronization, KafkaMirrorMaker2 changes, production DNS and consumer group resets require explicit business approval. Never disable TLS/SASL/ACLs, copy Secret values to Git, delete production topics/PVCs, force controller quorum changes or claim zero data loss without independent evidence.

## 1. Mission

Operate and troubleshoot asynchronous cross-cluster replication with Apache Kafka MirrorMaker 2 (MM2) under Kubernetes and Strimzi. Define source/destination topic mappings, least-privilege cross-cluster security, replication monitoring, consumer checkpoint/offset translation, RPO/RTO measurement, writer fencing, DR cutover and failback. Understand exactly which properties MM2 does **not** replicate automatically.

## 2. Learning objectives

- Distinguish replication of records, topic configuration, consumer group checkpoints and application/external dependencies.
- Explain MirrorSourceConnector, MirrorCheckpointConnector and MirrorHeartbeatConnector roles.
- Validate Strimzi KafkaMirrorMaker2 resource availability and version-specific Connect configurations.
- Measure source accepted-to-destination durable replication lag using per-partition watermarks and unique synthetic event IDs.
- Review consumer group offset translation and active-group safety before switching consumers.
- Plan DR promotion with explicit source-writer fencing and prevent split-brain writes.
- Prove recovered service through end-to-end sink reconciliation and independent review.

## 3. Architecture and data flow

```text
     Region A / Primary                         Region B / Secondary
 +-------------------------+              +---------------------------+
 | Kafka KRaft source      |              | Kafka KRaft destination   |
 | topic: sre-dr-synthetic |              | topic: primary.sre-dr-*  |
 | source producer         |              | DR consumer + sink        |
 | source consumer group   |              | translated group offsets |
 +-----------+-------------+              +-------------+-------------+
             |                                          ^
             | secure source fetch                      | secure produce
             v                                          |
         MirrorMaker 2 / Kafka Connect workers ----------+
           |             |                 |
     MirrorSource   MirrorCheckpoint   MirrorHeartbeat
           |             |                 |
     topic records    group checkpoint   health signal
           +-------------+-----------------+
                         |
                metrics / RPO / alerts
```

Topic naming is configuration-dependent; `primary.` is an illustrative alias, not a universal requirement. Verify whether replication policy uses prefixed or identity topic names. MM2 is asynchronous; source acknowledgments do not automatically imply remote durability.

## 4. MirrorMaker 2 component responsibilities

| Component | Responsibility | Important limitation |
|---|---|---|
| MirrorSourceConnector | replicate selected source topic records | lag, exclusions, task errors and mappings matter |
| MirrorCheckpointConnector | emit translated consumer group checkpoints | not identical to immediate target group offset commit |
| MirrorHeartbeatConnector | emit heartbeat records | does not prove every topic replicated |
| Offset sync metadata | map source and target offset positions | offset mapping may be incomplete or delayed |
| Kafka Connect worker | run connector tasks and store internal state | must be healthy, secured and monitored |
| Strimzi KafkaMirrorMaker2 | declarative orchestration and status | exact CRD/schema vary by release |

**Consumer offset caveat:** A source committed offset and a destination numeric offset are not directly interchangeable. Offset translation requires valid sync metadata/checkpoints, topic mapping and a plan for reprocessing duplicates. Synchronizing a group that is actively processing in the destination can be unsafe; check the installed MM2 semantics.

## 5. DR cutover acceptance gates

| Gate | Required evidence | Decision if missing |
|---|---|---|
| Source/destination Kafka KRaft | independent quorum/ISR, broker/PVC readiness | BLOCK |
| Topic coverage | critical allowlist, partitions, RF/minISR | BLOCK |
| MM2 tasks | source/checkpoint/heartbeat status, error budget | BLOCK |
| Replication RPO | per-topic-partition source watermark vs destination unique-event ledger | UNKNOWN / business approval |
| Security | TLS/SASL/mTLS, ACL, network path, secret rotation | BLOCK |
| Consumer checkpoints | validated translation, replay and sink idempotence | BLOCK |
| Writer fencing | single authoritative writer, prevention of split-brain | BLOCK |
| Application recovery | accepted IDs vs durable sink, freshness, schema/Connect | KEEP incident open |
| Business authority | change ticket, incident commander, rollback and failback | BLOCK |

A healthy MM2 custom resource or heartbeat is not sufficient to certify a successful DR cutover.

## 6. Read-only two-cluster Kubernetes preflight

```bash
# Substitute explicitly approved Kubernetes contexts; do not assume current-context.
PRIMARY_CTX=lab-primary
SECONDARY_CTX=lab-secondary
NS=kafka-lab

for CTX in "$PRIMARY_CTX" "$SECONDARY_CTX"; do
  echo "=== $CTX ==="
  kubectl --context "$CTX" -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide
  kubectl --context "$CTX" -n "$NS" get svc,endpointslices,networkpolicy
  kubectl --context "$CTX" -n "$NS" get events --sort-by=.metadata.creationTimestamp
done

# Check installed Strimzi support before querying KafkaMirrorMaker2.
kubectl --context "$PRIMARY_CTX" api-resources | grep -i kafkamirrormaker2
kubectl --context "$PRIMARY_CTX" -n "$NS" get kafkamirrormaker2
kubectl --context "$PRIMARY_CTX" -n "$NS" get kafkamirrormaker2 -o wide

# Synthetic source topic and Kafka CLI Pod are separately provisioned.
kubectl --context "$PRIMARY_CTX" -n "$NS" exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-dr-synthetic
```

Plaintext 9092 is only an isolated lab listener. For secure clusters supply approved TLS/SASL client configs and scoped ACLs; never expose passwords, key material or full sensitive KafkaMirrorMaker2 manifests in evidence.

## 7. KafkaMirrorMaker2 configuration review sketch

The following is **illustrative pseudo-configuration**, not a deployable Strimzi CR. Obtain the served `KafkaMirrorMaker2` API schema for the installed Strimzi release and build the actual manifest through GitOps review.

```yaml
# Review-only configuration; not a Kubernetes object.
connectCluster: secondary
clusters:
  - alias: primary
    bootstrapServers: source-bootstrap:9093
    tls: reviewed-trust-material
    authentication: reviewed-identity
  - alias: secondary
    bootstrapServers: destination-bootstrap:9093
    tls: reviewed-trust-material
    authentication: reviewed-identity
mirrors:
  - sourceCluster: primary
    targetCluster: secondary
    topicsPattern: '^sre-dr-synthetic$'
    groupsPattern: '^sre-dr-synthetic-group$'
    sourceConnector: reviewed-MirrorSourceConnector
    checkpointConnector: reviewed-MirrorCheckpointConnector
    heartbeatConnector: reviewed-MirrorHeartbeatConnector
approvalGates:
  - topic-allowlist
  - independent-kraft-isr
  - tls-sasl-acl
  - checkpoint-offset-validation
  - source-writer-fencing
  - rpo-rto-evidence
```

Kafka Connect internal topics, replication policy, checkpoints, offset syncs, ACLs, secrets and target topic configuration require explicit review. Do not assume Schema Registry, Connect sink state or arbitrary application state are mirrored by MM2.

## 8. Twenty Kubernetes-first MirrorMaker 2 labs

### Lab 01 — Approve two-cluster DR scope

**Objective and procedure:** Record isolated primary/secondary contexts, namespaces, business RPO/RTO, owner, topic allowlist, credential boundaries, abort and failback gates.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 02 — Verify independent KRaft clusters

**Objective and procedure:** Inspect source/destination Kafka CR, NodePools, quorum, ISR, PVC, zones, Strimzi versions and operator health separately.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 03 — Discover MirrorMaker 2 CRD support

**Objective and procedure:** Use kubectl api-resources and explain installed Strimzi KafkaMirrorMaker2 schema/version and Connect runtime prerequisites.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 04 — Map source and destination listeners

**Objective and procedure:** Inspect secure bootstrap/per-broker DNS, cross-network routes, EndpointSlices, NetworkPolicy, firewall and advertised endpoints.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 05 — Validate dedicated replication identities

**Objective and procedure:** Review KafkaUser or external SASL/mTLS principals, least-privilege ACLs, Secret references and independent credential rotation.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 06 — Define explicit topic allowlist

**Objective and procedure:** Select synthetic topics, naming/alias strategy, exclusion of internal/control topics, partition mapping and destination retention.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 07 — Review replication factor and minISR

**Objective and procedure:** Confirm destination topic RF/minISR, KRaft majority, storage, quotas and resilience independent of source.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 08 — Plan MirrorMaker 2 deployment

**Objective and procedure:** Review KafkaMirrorMaker2 CR examples against served CRD and supported Strimzi docs, including clusters, mirrors, connectCluster and tasks.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 09 — Validate connector/task health

**Objective and procedure:** Inspect MirrorMaker 2 status, Kafka Connect workers, source connector tasks, errors, restarts and reconciliation without leaking secrets.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 10 — Measure per-partition replication watermark

**Objective and procedure:** Capture source acknowledged offsets and destination replicated event IDs; avoid comparing unrelated numeric offsets directly.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 11 — Measure time-based replication lag

**Objective and procedure:** Use source event acceptance UTC and destination durable availability UTC with clock assumptions and uncertainty.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 12 — Inspect heartbeat and checkpoint flows

**Objective and procedure:** Review MirrorHeartbeatConnector, MirrorCheckpointConnector, offset-sync semantics and configuration-dependent topic naming.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 13 — Review consumer offset translation

**Objective and procedure:** Distinguish source committed offsets, checkpoint translation, target consumer group offsets and when synchronization is safe.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 14 — Validate downstream schemas and Connect

**Objective and procedure:** Check schema registry, serializers, connectors, DLQ, sink idempotence and external dependencies outside MM2 replication.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 15 — Validate replication lag alerting

**Objective and procedure:** Define SLO, source/destination connectivity, task failures, lag, missing metrics and error-budget response.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 16 — Simulate source-client outage

**Objective and procedure:** Use a synthetic client-only wrong bootstrap to test failure signals and restore; do not stop primary brokers.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 17 — Simulate replication task failure tabletop

**Objective and procedure:** Model paused connector, lag growth, RPO breach, task restart decision and recovery throughput.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 18 — Rehearse destination cutover tabletop

**Objective and procedure:** Validate secondary quorum/ISR, topic parity, writer fencing, translated offsets, TLS/ACL, DNS/client routing and business approval.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 19 — Rehearse failback tabletop

**Objective and procedure:** Plan reverse replication, writer fencing, source of truth, conflict prevention, replay and safe rollback.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

### Lab 20 — Complete independent DR acceptance

**Objective and procedure:** Reconcile unique event ledger, measure RPO/RTO only when live evidence exists, score 100 points and obtain technical/security signoff.

**Evidence and acceptance:** Capture source/destination context and software versions, UTC command/query, expected/observed state, per-partition source/destination watermark where relevant, TLS/ACL safety, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Regional cutover and failback are **Tabletop** unless separately approved.

## 9. Replication watermark and RPO worksheet

```text
source_topic
source_partition
source_last_acked_offset
source_last_acked_utc
destination_topic
destination_partition
destination_last_verified_event_id
destination_last_verified_source_offset
destination_verified_utc
accepted_unique_event_count
replicated_unique_event_count
missing_unique_event_count
duplicates
clock_uncertainty
estimated_replication_lag_seconds
cutover_decision
```

**Do not subtract source offsets from target offsets** unless a verified offset translation mapping explicitly supports that calculation. For each source partition, reconcile unique synthetic event IDs and source offset metadata in the destination. If source watermarks cannot be observed during outage, record uncertainty and use last independently observed watermark. This is essential to avoid false zero-RPO claims.

## 10. DR cutover and failback state machine

```text
NORMAL_PRIMARY
    |
    +-- disaster declared + business approval --> EVALUATE_SECONDARY
                                                   |
                            quorum/ISR/ACL/MM2/RPO/offset checks
                                                   |
                              +-- failed --> HOLD_AND_ESCALATE
                              |
                              +-- passed --> FENCE_PRIMARY_WRITERS
                                                   |
                                            PROMOTE_SECONDARY
                                                   |
                                      ROUTE_CLIENTS_AND_CONSUMERS
                                                   |
                                   RECONCILE_UNIQUE_DURABLE_EVENTS
                                                   |
                                            DR_ACTIVE
                                                   |
                                   independent reverse-sync review
                                                   |
                                      FENCE_CONFLICTING_WRITERS
                                                   |
                                       APPROVED_FAILBACK
```

If primary recovers unexpectedly, do **not** resume writes there until the authoritative writer is established. No automated failback is permitted without validated reverse replication, offset translation, sink idempotence and business approval.

## 11. Read-only MM2 inventory verifier

Save as `verify-ch54.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
PRIMARY_CTX=lab-primary
SECONDARY_CTX=lab-secondary
NS=kafka-lab
CLUSTER=sre-kafka
BIN=/opt/kafka/bin
BS=sre-kafka-kafka-bootstrap:9092
TOPIC=sre-dr-synthetic
for CTX in "$PRIMARY_CTX" "$SECONDARY_CTX"; do
  echo "=== Context: $CTX ==="
  kubectl --context "$CTX" -n "$NS" get kafka,kafkanodepool,pods,pvc -o wide
  kubectl --context "$CTX" -n "$NS" get svc,endpointslices
  kubectl --context "$CTX" -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
  kubectl --context "$CTX" -n "$NS" exec kafka-cli -- \
    "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
done
echo '=== MM2 CRD and resources on primary context ==='
if kubectl --context "$PRIMARY_CTX" api-resources -o name | grep -q '^kafkamirrormaker2s.kafka.strimzi.io$'; then
  kubectl --context "$PRIMARY_CTX" -n "$NS" get kafkamirrormaker2 -o wide
else
  echo 'UNKNOWN/NOT CONFIGURED: KafkaMirrorMaker2 CRD not found'
fi
echo '=== Synthetic source topic ==='
kubectl --context "$PRIMARY_CTX" -n "$NS" exec kafka-cli -- \
  "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"
echo 'PASS: read-only cross-cluster MM2 inventory.'
echo 'NOT PROVEN: replication watermarks, offset sync, security, RPO/RTO, cutover or independent review.'
```

Run `chmod +x verify-ch54.sh && ./verify-ch54.sh | tee evidence-ch54/preflight.txt`. Replace both context names with confirmed test contexts; do not use this script to modify resources or authorize production cutover.

## 12. Twelve replication and cutover failure scenarios

### Scenario 1 — MM2 worker Ready but source connector task failed

**Diagnosis:** Check connector/task state, source auth, broker metadata and error logs. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 2 — Topic excluded by replication allowlist

**Diagnosis:** Review topicsPattern, ACLs, internal topic exclusions and topic mapping. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 3 — Destination topic has incorrect replication factor

**Diagnosis:** Review destination creation policy, KafkaTopic CR and minISR/zone safety. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 4 — Replication lag exceeds approved RPO

**Diagnosis:** Compare per-partition source watermark and destination durable ledger; block unreviewed cutover. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 5 — Source/destination offset numbers differ

**Diagnosis:** Explain MM2 topic remapping and checkpoint/offset-sync translation. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 6 — Consumer group offsets not migrated

**Diagnosis:** Review checkpoint connector, group activity, translated offsets and bounded replay. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 7 — Heartbeat healthy while critical records absent

**Diagnosis:** Verify topic data path, tasks and event-ID ledger; heartbeat is not proof of completeness. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 8 — Cross-region TLS trust fails after rotation

**Diagnosis:** Inspect certificate chain, SAN, truststore and approved credential rollout. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 9 — Replication principal has topic Read but lacks Describe

**Diagnosis:** Check exact resource/operation ACL and Connect worker needs. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 10 — DR cutover starts duplicate active producers

**Diagnosis:** Fence old writers and identify authoritative cluster before enabling new writes. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 11 — Schema Registry unavailable in DR region

**Diagnosis:** Restore schema compatibility and external dependencies before consumer acceptance. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

### Scenario 12 — Failback attempts before reverse lag reaches threshold

**Diagnosis:** Block until reverse watermarks, offset mapping, fencing and rollback are reviewed. Correlate KafkaMirrorMaker2/Connect status, Kafka KRaft/ISR, source and destination event ledger, TLS/ACL, client SLO and topic mappings. **Decision:** Freeze unapproved cutover, quantify RPO uncertainty and enforce writer fencing. **Evidence:** UTC timeline, redacted task/connector logs, per-partition watermarks, rollback and independent review.

## 13. Eight production DR runbooks

### Runbook A — MM2 deployment and readiness

**Trigger and first response:** Validate Strimzi CRD, Connect worker, two cluster identities, topic allowlist, security and task status. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook B — MM2 connector/task failure

**Trigger and first response:** Inspect KafkaMirrorMaker2 conditions, task logs, ACLs, source/destination network and backoff. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook C — Replication lag and RPO breach

**Trigger and first response:** Measure source accepted and destination durable per-partition watermarks, throughput and backlog. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook D — Consumer group checkpoint and offset migration

**Trigger and first response:** Validate checkpoint emission, offset-sync mapping, inactive group prerequisites and replay/deduplication. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook E — Cross-region TLS/SASL/ACL incident

**Trigger and first response:** Inspect advertised listeners, CA, SASL/mTLS identities, ACLs and NetworkPolicy without bypass. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook F — DR cutover and writer fencing

**Trigger and first response:** Require business approval, destination quorum/ISR, known loss window, writer fencing, routing and sink integrity. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook G — DR failback and split-brain prevention

**Trigger and first response:** Confirm authoritative writer, reverse replication, checkpoints, sink reconciliation and rollback. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

### Runbook H — RPO/RTO and data-integrity acceptance

**Trigger and first response:** Reconcile unique IDs, record measured downtime and uncertainty, alert recovery, security and independent signoff. **Safety:** Preserve quorum/ISR, authentication, least-privilege ACL, authoritative writer and destination data integrity; never reset shared offsets or enable dual writers. **Exit:** Signed business approval, secure routing, RPO/RTO evidence, unique-event reconciliation and corrective-action owner.

## 14. Evidence package

```text
evidence-ch54/
  approved-dr-change-charter.md
  source-destination-context-version-matrix.md
  preflight.txt
  independent-kraft-isr-pvc-health.md
  mm2-crd-schema-version.md
  secure-listener-dns-networkpath.md
  replication-principals-acls.md
  topic-allowlist-and-mapping.md
  destination-rf-minisr.md
  mm2-gitops-manifest-review.md
  connect-worker-task-health.md
  source-destination-event-watermarks.csv
  rpo-lag-worksheet.md
  heartbeat-checkpoint-offset-sync.md
  consumer-offset-translation.md
  schema-connect-sink-dependencies.md
  replication-lag-alerts.md
  synthetic-source-client-drill.md
  connector-failure-tabletop.md
  destination-cutover-tabletop.md
  failback-writer-fencing-tabletop.md
  accepted-processed-event-ledger.csv
  rto-incident-timeline.md
  independent-technical-security-review.md
  readiness-scorecard.md
```

Each artifact requires exact source, software version, UTC time, expected/observed result, owner, redaction, abort/rollback and reviewer. No evidence of real cross-region DR is implied by a tabletop exercise.

## 15. 100-point MirrorMaker 2 DR acceptance

| Domain | Points | Critical |
|---|---:|---|
| Scope, independent clusters, RPO/RTO and safety | 10 | Yes |
| Strimzi/MM2 CRD and Connect worker/task health | 15 | Yes |
| Topic coverage, RF/minISR and source/destination parity | 10 | Yes |
| TLS/SASL/ACL and cross-cluster connectivity | 10 | Yes |
| Per-partition replication watermark and RPO | 15 | Yes |
| Consumer checkpoints, offset sync and replay | 15 | Yes |
| Writer fencing, cutover and failback | 15 | Yes |
| End-to-end sink integrity and incident evidence | 5 | Yes |
| Independent security/technical review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced. **Automatic Fail:** fabricated MM2 execution, unauthorized production cutover, active-active split-brain, missing accepted-event reconciliation, source/target offset arithmetic without mapping, weakened durability/security or absent independent review.

## 16. Cleanup, references and next chapter

Remove only chapter-owned synthetic clients, test topics, test MirrorMaker 2 resources and test alerts via approved GitOps after evidence retention. Preserve sanitized watermarks and action tracker. Never delete production offsets, checkpoints, Kafka Connect internal topics, PVCs or operator-managed Secrets.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 055 — Kafka High Availability, Cross-Region Failover and Disaster Recovery Simulation Capstone.

---

**Verification boundary:** GitHub publication proves document availability only. Live MirrorMaker 2 replication, offset translation, DR cutover, RPO/RTO, data-integrity and independent security review remain Pending.
