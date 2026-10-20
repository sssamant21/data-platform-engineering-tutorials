# Chapter 053 — Kafka Multi-Zone Resilience, Disaster Recovery Architecture, RPO and RTO Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 11 — High Availability, Failover and Disaster Recovery (3/5)  
**Platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–052; especially 011–015, 036–052  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety boundary:** This chapter uses read-only discovery and approved tabletop/synthetic disaster exercises. Never disrupt a production availability zone, terminate KRaft voters, delete PVCs, reset production offsets, change live MirrorMaker 2 routing, switch production DNS or permit dual active writers. A real DR cutover requires a separately approved change plan, business authority and independent validation.

## 1. Mission and learning outcomes

Design Kafka resilience across Kubernetes nodes and availability zones, then evaluate cross-region disaster recovery. Translate business recovery objectives into partition-level and end-to-end recovery gates. Understand that **multi-AZ high availability is not the same as regional disaster recovery** and that asynchronous cross-cluster replication generally implies a nonzero data-loss window.

At completion, learners should be able to map KRaft controller quorum and broker ISR by zone; audit PV/CSI failure domains; compare single-cluster HA with independent-cluster DR; model MirrorMaker 2 replication and consumer offset translation; calculate defensible RPO/RTO; prevent split-brain writers; and prove recovery through unique-event reconciliation.

## 2. Reference topology and dependency map

```text
Region A (primary)                         Region B (standby)
  AZ-a    AZ-b    AZ-c                       AZ-d    AZ-e    AZ-f
  Broker  Broker  Broker                     Broker  Broker  Broker
  PVC     PVC     PVC                        PVC     PVC     PVC
  Ctr-A   Ctr-B   Ctr-C                      Ctr-D   Ctr-E   Ctr-F
       |     |     |                               |     |     |
       KRaft majority                             KRaft majority
             |                                          |
      source topics -- async replication / MM2 --> destination topics
             |                                          |
      source consumer                              DR consumer
             |                                          |
       durable sink                            idempotent DR sink
             \----------- event-ID reconciliation -----/
```

Both clusters need independently functional Kubernetes APIs, Strimzi reconcilers, storage, identity, network, TLS, observability and application dependencies. Shared DNS, IAM, KMS, Schema Registry or GitOps can undermine nominal regional independence.

## 3. Architecture decision table

| Pattern | Protects against | Important limitation | Required proof |
|---|---|---|---|
| Three-zone single Kafka cluster | selected node/AZ failures | not region outage; controller/ISR/PV placement matter | zone-loss quorum and ISR |
| Backup and restore | corruption, deletion, disaster recovery | restore time and backup age; Kafka log/metadata consistency | tested restore and replay |
| Independent DR Kafka cluster with MM2 | primary-cluster or region loss | asynchronous replication, offsets and split-brain | RPO watermark, cutover drill |
| Application dual write | some cross-region outage modes | ordering, consistency, conflict and dedup complexity | application-level integrity |
| Event source + deterministic replay | recoverable downstream state | source retention and replay throughput | full reconstruction and time budget |

Do not assume MirrorMaker 2 replicates every required artifact automatically. Review supported topic replication, internal topics, ACLs, consumer checkpoints/offset syncs, schema dependencies, Connect configuration and application-specific state separately.

## 4. RPO and RTO engineering

**RPO** is the maximum acceptable data loss measured against a clearly defined business event or acknowledged Kafka record. **RTO** is the maximum acceptable time to restore the agreed service function.

```text
accepted_source_watermark = latest source event ID / offset acknowledged under the contract
replicated_destination_watermark = latest source event ID durably available at destination
potential_loss_window = accepted events after destination watermark
observed_RPO_time = source acceptance time of latest unreplicated accepted event
                    minus source acceptance time of latest replicated accepted event
observed_RTO = durable service restoration UTC - declared incident start UTC
```

The watermark must be tracked **per source topic-partition**, not as a single scalar Kafka offset across topics. Event timestamps require trustworthy clocks and explicit timestamp semantics. For a failure with no source access, use the most recent independently observed source watermark and mark unknown gaps rather than claiming zero loss.

**Worked example (illustrative, not measured):** If the latest acknowledged source event was accepted at 10:00:30 UTC and the latest independently verified destination event at 10:00:18 UTC, the observed time-based replication gap is approximately **12 seconds** at that observation. This is not a guarantee that a subsequent outage will lose exactly 12 seconds of data. If service is declared unavailable at 10:02 UTC and fully verified at 10:17 UTC, observed RTO is **15 minutes**. Include incident declaration rules, validation delay and unresolved events in the business contract.

## 5. KRaft, ISR and AZ-loss failure budget

For `N` controller voters, majority is `floor(N/2)+1`; three voters tolerate one unavailable voter, not an arbitrary AZ loss. For each hypothetical failed zone, count surviving voters and per-partition eligible replicas.

For RF=3 and minISR=2, losing one replica can preserve `acks=all` write eligibility when the remaining two are in-sync and a leader is available. **Replica count alone does not prove zone safety**; all replicas might share one zone or storage dependency.

A Kubernetes PDB does not replace KRaft quorum, Kafka ISR or business SLO gates. PV zone affinity may prevent an apparently healthy replacement broker from mounting the original data.

## 6. Read-only Kubernetes and Kafka discovery

```bash
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc,pdb -o wide
kubectl -n kafka-lab get svc,endpointslices,networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl get storageclass
kubectl -n kafka-lab get kafka sre-kafka -o jsonpath='{.status.conditions}{"\n"}'
kubectl -n kafka-lab get kafkanodepool -o custom-columns=NAME:.metadata.name,ROLES:.spec.roles,REPLICAS:.spec.replicas

# Isolated lab CLI Pod and internal plaintext bootstrap ONLY.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-dr-synthetic

# Discover MM2 custom resources only if the installed Strimzi CRD supports them.
kubectl api-resources | grep -i kafkamirrormaker2
kubectl -n kafka-lab get kafkamirrormaker2
```

The synthetic topic and `kafka-cli` Pod are separately provisioned lab prerequisites. The 9092 listener is **not** a production template; production-like Kafka CLI requires TLS/SASL `--command-config`, RBAC and ACL review. Avoid exporting Secret contents, sensitive KafkaUser details or unredacted connector configs.

## 7. Twenty Kubernetes-first DR architecture labs

### Lab 01 — Define DR business contract

**Objective and procedure:** Obtain owner-approved per-topic RPO/RTO, retention, replay requirements, data-classification, service tier and maximum acceptable duplicates.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 02 — Map Kubernetes failure domains

**Objective and procedure:** Inventory cloud region, AZ, node, CSI topology, DNS, load balancers, identity, Kubernetes API and Strimzi operator dependencies.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 03 — Verify Kafka KRaft topology

**Objective and procedure:** Read controller voters, broker NodePools, quorum status and placement; model loss of one AZ without touching voters.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 04 — Audit broker rack awareness

**Objective and procedure:** Compare node zone labels, Strimzi rack configuration, topic replica placement, leaders, ISR and minISR.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 05 — Audit PV/CSI AZ affinity

**Objective and procedure:** Inspect StorageClass volumeBindingMode, PVC/PV node affinity, snapshots and restore compatibility across zones.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 06 — Inventory inter-zone network resilience

**Objective and procedure:** Inspect CNI, NetworkPolicy, listener DNS, per-broker endpoints, cross-AZ latency and TLS/SASL routing.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 07 — Build topic criticality register

**Objective and procedure:** Record owner, partitions, RF, minISR, retention, cleanup policy, data sensitivity, replay and DR tier.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 08 — Estimate single-AZ write availability

**Objective and procedure:** Model leader/replica placement, surviving ISR, acks=all and KRaft majority for each candidate failed AZ.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 09 — Identify region-wide dependencies

**Objective and procedure:** Map cloud IAM/KMS, secrets, container registry, GitOps, monitoring, schema registry, Kafka Connect and sink dependencies.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 10 — Compare DR architecture options

**Objective and procedure:** Evaluate multi-AZ single cluster, independent secondary cluster, MirrorMaker 2, application dual-write and external backups.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 11 — Model asynchronous replication RPO

**Objective and procedure:** Define source accepted-offset watermark, remote replicated-offset watermark and time-based lag with explicit clock assumptions.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 12 — Model RTO critical path

**Objective and procedure:** Estimate detection, approval, infrastructure recovery, DNS/client cutover, authentication, offset translation and sink validation.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 13 — Validate cross-cluster security posture

**Objective and procedure:** Review dedicated principals, TLS/mTLS/SASL, ACL, network isolation, KMS and secret lifecycle for a secondary cluster.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 14 — Inspect MirrorMaker 2 prerequisites

**Objective and procedure:** Inventory KafkaMirrorMaker2 CRD availability, supported connector configuration, topic selection, checkpoint/heartbeat semantics and monitoring.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 15 — Review consumer offset migration semantics

**Objective and procedure:** Distinguish source committed offsets, translated checkpoints, destination offsets and replay/deduplication boundaries.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 16 — Review schema and Connect dependencies

**Objective and procedure:** Verify schema compatibility, connector offsets, DLQs, external sink idempotence and recovery order.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 17 — Simulate single-zone loss as tabletop

**Objective and procedure:** Select an AZ, remove its brokers/controllers/PVs from an architecture worksheet, calculate surviving quorum/ISR and document gaps.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 18 — Simulate regional cutover as tabletop

**Objective and procedure:** Use a synthetic incident timeline to model replication lag, promotion approval, client endpoint switch and split-brain fencing.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 19 — Validate end-to-end recovery ledger

**Objective and procedure:** Reconcile acknowledged source unique IDs, replicated IDs, consumer commits, durable sink IDs, duplicates and freshness.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

### Lab 20 — Complete DR architecture acceptance

**Objective and procedure:** Run read-only preflight, submit diagrams, RPO/RTO worksheet, security review, failback plan and independent 100-point scorecard.

**Evidence and acceptance:** Record exact Kafka/Strimzi/Kubernetes versions, UTC source commands/queries, expected versus observed behavior, per-partition watermark where relevant, quorum/ISR safety, security boundary, rollback, owner and independent assessor. Mark **Pending** until actually executed; regional and AZ failure drills remain **Tabletop** unless separately approved and run.

## 8. DR topology and cutover policy as code (illustrative only)

The following is a **GitOps review artifact**, not a Kubernetes CRD or deployable Strimzi resource:

```yaml
service: sre-kafka-dr-synthetic
primaryRegion: region-a
secondaryRegion: region-b
recoveryContract:
  rpoSeconds: 60        # EXAMPLE only; replace with approved service contract
  rtoMinutes: 30        # EXAMPLE only; replace with approved service contract
  acceptedEventDefinition: producer-callback-success
  durableRecoveryDefinition: unique-event-committed-to-sink
replication:
  mode: asynchronous
  technology: KafkaMirrorMaker2
  topics:
    - sre-dr-synthetic
  requirePerPartitionWatermarks: true
cutover:
  requiresBusinessApproval: true
  requirePrimaryWriterFencing: true
  requireDestinationSecurityValidation: true
  requireConsumerOffsetTranslationReview: true
  requireSinkDeduplication: true
  requireRollbackAndFailbackPlan: true
  blockIfWatermarksUnknown: true
```

Do not assume a KafkaMirrorMaker2 CR can be copied across Strimzi releases. Validate its exact served API version and connector options before creating any test resources.

## 9. DR cutover and failback decision tree

```text
Primary unavailable?
  |
  +-- NO -> Continue HA recovery and protect quorum/ISR.
  |
  +-- YES -> Declare incident; identify business authority.
                 |
          Is secondary independently healthy and secured?
                 +-- NO -> BLOCK cutover / escalate.
                 |
                 +-- YES -> Is replication watermark known?
                               +-- NO -> record UNKNOWN RPO; business decision.
                               |
                               +-- YES -> quantify per-partition accepted-event gap.
                                             |
                                Fence primary writers / prevent split-brain.
                                             |
                                Approve endpoint + consumer offset mapping.
                                             |
                                Reconcile durable unique-event ledger.
                                             |
                                Monitor RTO/SLO and retain failback gates.
```

A primary may reappear after cutover. **Do not simply resume its producers**: authority and fencing must prevent simultaneous conflicting writes. Failback requires independently verified reverse data flow, offsets, replay, client routing, security and rollback.

## 10. Read-only DR verification script

Save as `verify-ch53.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPIC=sre-dr-synthetic
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Node zones'; kubectl get nodes -L topology.kubernetes.io/zone
echo '[3/12] Kafka and NodePools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Pods/PVCs'; kubectl -n "$NS" get pods,pvc -o wide
echo '[5/12] StorageClasses'; kubectl get storageclass
echo '[6/12] PDBs'; kubectl -n "$NS" get pdb
echo '[7/12] Services'; kubectl -n "$NS" get svc,endpointslices
echo '[8/12] Kafka conditions'; kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[9/12] Topic replica placement'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"
echo '[10/12] Kubernetes Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[11/12] MirrorMaker2 CRD discovery'
if kubectl api-resources -o name | grep -q '^kafkamirrormaker2s.kafka.strimzi.io$'; then
  kubectl -n "$NS" get kafkamirrormaker2
else
  echo 'UNKNOWN/NOT CONFIGURED: MirrorMaker2 CRD not discovered'
fi
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only primary-cluster DR inventory.'
echo 'NOT PROVEN: secondary cluster health, cross-region replication, RPO/RTO, failover, integrity or review.'
```

Run `chmod +x verify-ch53.sh && ./verify-ch53.sh | tee evidence-ch53/preflight.txt`. The script does not verify secondary-region health, replication watermarks or an RPO/RTO guarantee. The absence of a MirrorMaker2 CRD is not proof of an outage; document architecture selection.

## 11. Twelve DR failure scenarios

### Scenario 1 — AZ loss leaves controller quorum but under-minISR partitions

**Diagnose:** Separate metadata majority from per-topic write availability; block durability weakening. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 2 — AZ loss removes majority of controller voters

**Diagnose:** Declare metadata quorum outage; invoke supported DR escalation, not manual voter edits. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 3 — PV pinned to failed zone blocks broker scheduling

**Diagnose:** Check PV topology, CSI restore path and safe recovery before rescheduling. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 4 — Cross-zone latency causes ISR shrink

**Diagnose:** Inspect follower fetch, network RTT, disk and replication backlog. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 5 — Secondary cluster replication falls behind RPO

**Diagnose:** Compare source accepted watermark with destination committed watermark; hold cutover decision. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 6 — MirrorMaker 2 healthy but critical topic omitted

**Diagnose:** Validate allowlists, ACLs, connector task errors and topic mapping. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 7 — Destination offsets do not match source group offsets

**Diagnose:** Inspect checkpoint/offset-sync semantics and bounded replay/deduplication. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 8 — DR cutover creates dual active writers

**Diagnose:** Require writer fencing, authority decision and data reconciliation before accepting traffic. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 9 — Secondary cluster lacks required TLS/ACL identity

**Diagnose:** Check secure listeners, principals, KMS/Secret availability and least privilege. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 10 — Schema Registry unavailable during recovery

**Diagnose:** Validate schema IDs/compatibility and dependency restoration sequence. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 11 — Consumer resumes but sink data is incomplete

**Diagnose:** Trace unique event IDs and durable sink ledger, not only consumer lag. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

### Scenario 12 — Failback planned without reverse-replication validation

**Diagnose:** Block failback until direction, offsets, fencing and rollback are independently reviewed. Correlate Kubernetes AZ topology, KRaft quorum, partition ISR, PVC/CSI, MirrorMaker 2 tasks, source/destination watermarks, client callbacks and durable sink. **Decision:** Preserve security and durability, fence conflicting writers and obtain DR authority before cutover. **Evidence:** UTC timeline, RPO/RTO estimate with uncertainty, expected/observed result and independent reviewer.

## 12. Eight production DR runbooks

### Runbook A — DR architecture readiness and change gate

**Trigger and triage:** Validate per-topic RPO/RTO, controller quorum, ISR, PV topology, client SLO and owner approvals. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook B — Single-AZ loss and safe containment

**Trigger and triage:** Map failed zone to brokers/controllers/PVs, preserve acks/minISR, inspect quorum and choose approved recovery. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook C — Regional disaster declaration

**Trigger and triage:** Establish IC, failure scope, business authority, dependency inventory and secondary-cluster readiness. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook D — MirrorMaker 2 replication lag incident

**Trigger and triage:** Inspect connector tasks, ACLs, source/destination offsets, network, throughput and RPO breach. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook E — Secondary-cluster cutover

**Trigger and triage:** Require fencing, replication watermark, security, DNS/client change, replay/deduplication and evidence. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook F — Consumer offset and sink recovery

**Trigger and triage:** Validate checkpoints, offset translation, schema/Connect, sink idempotence and event ledger. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook G — Failback and split-brain prevention

**Trigger and triage:** Freeze conflicting writers, verify reverse replication, offset mapping, rollback and owner signoff. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

### Runbook H — RPO/RTO measurement and post-drill review

**Trigger and triage:** Calculate observed data-loss window and downtime, identify gaps, assign corrective actions and retest. **Safety:** No unapproved region cutover, Kafka quorum edits, topic deletion, offset reset, weakened minISR/acks, plaintext listener or wildcard ACL. **Exit:** Independent quorum/ISR, replication watermark, secure routing, unique-event reconciliation, RPO/RTO, stakeholder approval and action tracker.

## 13. Evidence package

```text
evidence-ch53/
  approved-dr-contract.md
  context-version-matrix.md
  preflight.txt
  region-az-node-dependency-map.md
  kraft-quorum-by-zone.md
  broker-rack-isr-by-zone.md
  pv-csi-zone-affinity.md
  cross-zone-network-tls.md
  topic-criticality-register.csv
  single-az-failure-worksheet.md
  region-dependency-map.md
  dr-pattern-decision-record.md
  source-destination-watermarks.csv
  rpo-rto-calculation.md
  secondary-security-checklist.md
  mirrormaker2-prerequisites.md
  consumer-checkpoint-offset-review.md
  schema-connect-dependencies.md
  zone-loss-tabletop.md
  region-cutover-tabletop.md
  accepted-processed-event-ledger.csv
  failback-fencing-plan.md
  independent-security-review.md
  independent-signoff.md
```

All evidence requires source, exact version, UTC timestamp, expected/observed result, redaction, owner, abort/rollback and reviewer. RPO and RTO remain **Unverified** until measured in an approved cross-cluster drill with representative workloads.

## 14. 100-point DR architecture acceptance

| Domain | Points | Critical |
|---|---:|---|
| Business RPO/RTO and recovery contract | 10 | Yes |
| KRaft quorum, broker rack and ISR by zone | 15 | Yes |
| Kubernetes topology, PVC/CSI and AZ dependencies | 15 | Yes |
| Secondary-cluster architecture and independence | 15 | Yes |
| Replication lag and per-partition RPO evidence | 15 | Yes |
| Consumer offsets, schema/Connect and sink recovery | 10 | Yes |
| Writer fencing, cutover and failback | 10 | Yes |
| Tabletop incidents and RTO validation plan | 5 | Yes |
| Independent security/technical review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. **Automatic Fail:** fabricated regional failover, unapproved production cutover, unquantified loss represented as zero, active-active split brain, missing durable-event reconciliation, weakened durability/security or absent independent review.

## 15. Cleanup, references and next chapter

Remove only chapter-owned synthetic Kafka clients, topics, test alerts and optional secondary test resources through approved GitOps. Preserve sanitized architecture, source/destination watermarks and corrective-action evidence. Never delete production PVCs, topics, offsets, operator-managed Secrets or replication checkpoints.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Kubernetes Topology Spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/).

**Next:** Chapter 054 — Kafka Cross-Cluster Replication, MirrorMaker 2, Offset Synchronization and Disaster Recovery Cutover.

---

**Verification boundary:** GitHub publication establishes document availability only. Cross-zone and cross-region drills, MirrorMaker 2 replication, RPO/RTO measurements, event integrity and independent technical/security acceptance remain Pending.
