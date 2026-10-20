# Chapter 051 — Kafka High Availability Architecture, Failure Domains and Kubernetes Resilience

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 11 — High Availability, Failover and Disaster Recovery (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–050, especially 011–015, 021–025, 036–050  
**Publication:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use an approved disposable Kubernetes environment. All broker, controller, zone-loss and storage-failure simulations in this chapter are tabletop/synthetic. Do not kill production Pods, drain nodes, change KRaft voter membership, delete PVCs, enable unclean leader election, reduce min.insync.replicas, weaken acks, bypass TLS/SASL/ACLs or assume cross-zone PV portability. Review the exact Kafka/Strimzi/Kubernetes version combination before any maintenance.

## 1. Mission

Design and assess Kafka high availability from the client to broker replicas, KRaft metadata quorum, Kubernetes scheduling, persistent storage and cloud availability zones. Build a failure-domain model, determine tolerable failures, identify shared dependencies and verify that recovery objectives are supported by observable evidence and approved runbooks.

## 2. Learning objectives

- Separate **availability**, **durability**, **recoverability**, **RPO** and **RTO** and link them to application SLIs.
- Design broker replica placement and ISR/minISR policy for realistic node/zone failure domains.
- Analyze KRaft controller quorum majority independently from broker data-plane health.
- Inspect Strimzi KafkaNodePool roles, rack awareness, operator-owned Pod scheduling, PDBs and storage topology.
- Identify single points of failure in DNS, listeners, network policy, CSI, cloud IAM and downstream sinks.
- Validate safe maintenance and tabletop failover against error-budget and data-integrity gates.

## 3. Reference failure-domain architecture

```text
                 Synthetic clients (TLS/SASL)
                           |
                 bootstrap / broker DNS
                           |
      +--------------------+--------------------+
      |                    |                    |
   Zone A               Zone B               Zone C
      |                    |                    |
  Broker A             Broker B             Broker C
  PVC / CSI            PVC / CSI            PVC / CSI
      \                    |                    /
       \--- Kafka partition replicas / ISR ---/
      |                    |                    |
 Controller voter A   Controller voter B   Controller voter C
      \                    |                    /
             KRaft metadata quorum
                           |
            Strimzi / Kubernetes API
                           |
               Observability + GitOps
```

This diagram is a **reference pattern**, not a claim that the lab already spans three zones. A local kind/minikube cluster can validate API and metadata checks but cannot establish real cloud AZ resilience. Confirm actual NodePool roles and placement; Strimzi supports distinct broker/controller node pools on compatible releases.

## 4. High availability mathematics and failure limits

**KRaft quorum:** With `N` voting controllers, a majority of `floor(N/2)+1` is required. The maximum simultaneously unavailable voters while retaining majority is `floor((N-1)/2)`. For three voters this is one; for five voters this is two. Placement matters: three voters in one zone still have a single-zone failure domain.

**Kafka partition availability:** Replication factor `RF` determines the number of assigned replicas, while `ISR` tracks caught-up replicas. With producer `acks=all`, writes may fail when ISR falls below `min.insync.replicas`. A three-replica topic with minISR=2 can tolerate one unavailable replica **for acknowledged writes only if the remaining replicas are eligible and the leader can serve**. Leader elections, network partitions and application timeouts can still cause temporary unavailability.

**Durability caveat:** Replication and `acks=all` reduce risk but are not substitutes for backup, integrity validation or an RPO contract. Unclean leader election may lose committed records and is not an HA shortcut.

## 5. Kubernetes and Strimzi resilience checklist

| Layer | Design decision | Evidence |
|---|---|---|
| Controller | odd voting set, distinct failure domains, supported quorum recovery | KRaft quorum CLI, node pool roles, topology |
| Broker | RF, ISR/minISR, rack awareness, leadership distribution | topic describe, broker rack config |
| Kubernetes | anti-affinity, topology spread, PDB, requests/limits | Pod spec, NodePool, PDB, node labels |
| Storage | PV zone binding, CSI capability, capacity, backup | PVC/PV/StorageClass, CSI events |
| Network | bootstrap + per-broker DNS, secure listeners, multi-zone path | Service/EndpointSlice, TLS, policy |
| Application | idempotent producer, retries, consumer replay, idempotent sink | callbacks, offsets, unique ledger |
| SRE | SLO burn, quorum/ISR alerting, missing-data detection | alert tests and dashboards |
| Change | GitOps approvals, maintenance gate, rollback | PR, diff, owner and review |

**Strimzi ownership:** Never patch operator-owned StatefulSets/Pods directly to enforce placement. Change supported Kafka/KafkaNodePool CR fields through approved GitOps after checking CRD schema and release-specific operator behavior.

## 6. Read-only HA discovery commands

```bash
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab get pdb,svc,endpointslices,networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get kafkanodepool -o yaml
kubectl -n kafka-lab get pvc -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,VOLUME:.spec.volumeName,CLASS:.spec.storageClassName
kubectl get pv -o custom-columns=NAME:.metadata.name,CLASS:.spec.storageClassName,ZONE:.metadata.labels.topology\\.kubernetes\\.io/zone

# Isolated lab CLI Pod and internal plaintext bootstrap ONLY.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-ha-synthetic
```

Do not commit unreviewed full resource YAML; inspect for sensitive annotations and references. Production-like Kafka clients require TLS/SASL, least-privilege ACLs and appropriate `--command-config`. The `kafka-cli` Pod and synthetic topic must be provisioned separately under approved lab manifests.

## 7. Twenty Kubernetes-first HA labs

### Lab 01 — Approve HA architecture and resilience scope

**Objective and procedure:** Record disposable Kubernetes context, Kafka service tier, business SLO, RPO/RTO objectives, owner, abort conditions, change freeze and test-only boundaries.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 02 — Capture topology and version baseline

**Objective and procedure:** Record Strimzi/Kafka/Kubernetes versions, KRaft mode, CRD schema, broker/controller node pools, Pod distribution, PVs and GitOps revision.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 03 — Map regional and zonal failure domains

**Objective and procedure:** Enumerate regions, zones, nodes, storage topology, CNI, cloud dependencies, client paths and shared-control-plane failure modes.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 04 — Map KRaft controller quorum

**Objective and procedure:** Identify controller-only versus mixed roles, configured voters, controller placement, majority tolerance and supported version-specific quorum diagnostics.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 05 — Map broker replica placement

**Objective and procedure:** Inspect topic replication factor, partition leader/replica placement, broker racks, ISR and minISR for isolated synthetic topic.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 06 — Audit rack awareness and topology labels

**Objective and procedure:** Compare broker rack identity and Kubernetes node topology labels; document how Strimzi rack configuration is supported by installed version.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 07 — Audit Pod anti-affinity and topology spread

**Objective and procedure:** Inspect NodePools and operator-generated Pod scheduling, node selectors, affinity, tolerations and topology spread constraints.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 08 — Audit PodDisruptionBudgets

**Objective and procedure:** Inspect operator-generated PDBs and voluntary eviction safety; document limits when quorum/ISR or replicas are already degraded.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 09 — Audit broker PVC topology and durability

**Objective and procedure:** Inspect StorageClass volumeBindingMode, PV node affinity, CSI replication assumptions and restore/zone availability.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 10 — Audit controller and broker resource isolation

**Objective and procedure:** Review CPU/memory requests, QoS, limits, JVM/GC, controller network and node pool capacity headroom.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 11 — Validate listener and network resilience

**Objective and procedure:** Inspect bootstrap/broker endpoints, TLS, DNS, LB and NetworkPolicy across approved client failure domains.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 12 — Validate producer durability policy

**Objective and procedure:** Review acks=all, idempotence, retries, RF/minISR and client callback evidence; document limits of Kafka acknowledgment guarantees.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 13 — Validate consumer recovery design

**Objective and procedure:** Review group membership, rebalances, offset commit, processing idempotency, replay and downstream sink availability.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 14 — Build SLO and error-budget failure matrix

**Objective and procedure:** Model single broker, single node, zone loss, controller quorum, PVC failure, network partition and observability blind spots.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 15 — Simulate single broker loss via tabletop

**Objective and procedure:** Use synthetic broker-unavailable evidence; estimate expected ISR/leader outcomes without deleting or restarting Pods.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 16 — Simulate controller voter loss via tabletop

**Objective and procedure:** Evaluate majority availability and supported recovery escalation; do not alter voters or kill controller Pods.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 17 — Simulate availability-zone loss via tabletop

**Objective and procedure:** Map affected brokers, controller voters, PVs, listeners and consumer processing to RPO/RTO acceptance.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 18 — Simulate storage or CSI disruption via tabletop

**Objective and procedure:** Analyze PVC Pending, offline log directories and zonal PV pinning; choose safe recovery and backup validation.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 19 — Validate resilience alerting and runbooks

**Objective and procedure:** Check alert coverage for quorum, ISR, unavailable partitions, SLO burn, PVC/CSI, node pressure and missing telemetry.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

### Lab 20 — Complete HA readiness and independent review

**Objective and procedure:** Run read-only inventory, record evidence, score 100-point rubric and obtain architecture/security reviewer signoff.

**Expected evidence:** Approved context, exact software versions, UTC timestamp, command/query, expected/observed topology or failure behavior, KRaft quorum and ISR safety, client SLO, rollback/abort criteria and independent assessor. Mark **Pending** until live execution; simulated zone/controller/storage failures are explicitly labeled Tabletop.

## 8. Example resilience policy (review before deployment)

The following is a **design sketch**, not a version-independent Strimzi manifest. Confirm `KafkaNodePool` and `Kafka` CRD schemas and rack-awareness configuration against the installed release. Keep broker and controller scheduling/placement under operator control.

```yaml
# GitOps policy inputs, NOT a Kubernetes resource.
service: synthetic-kafka-ha
targetZones: 3
controllerVoters: 3
brokerReplicas: 3
topicReplicationFactor: 3
topicMinInSyncReplicas: 2
producerAcks: all
uncleanLeaderElection: false
approvalRequiredFor:
  - node-drain
  - controller-quorum-change
  - broker-storage-change
  - partition-reassignment
  - zone-failover
evidenceRequired:
  - kraft-quorum
  - topic-isr
  - pvc-csi-health
  - client-callback-sli
  - consumer-freshness
  - unique-event-ledger
```

A three-zone, three-broker design can tolerate some single-zone failures only when broker/controller voters, storage and networking are genuinely independent. A Kubernetes `topologySpreadConstraint` or PDB alone does not guarantee HA.

## 9. Read-only verification script

Save as `verify-ch51.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPIC=sre-ha-synthetic
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Zone labels'; kubectl get nodes -L topology.kubernetes.io/zone
echo '[3/12] Kafka and NodePools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Pods'; kubectl -n "$NS" get pods -o wide
echo '[5/12] PVCs'; kubectl -n "$NS" get pvc -o wide
echo '[6/12] StorageClasses'; kubectl get storageclass
echo '[7/12] PDBs'; kubectl -n "$NS" get pdb
echo '[8/12] NetworkPolicies'; kubectl -n "$NS" get networkpolicy
echo '[9/12] Kafka conditions'; kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[10/12] Topic replicas and ISR'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"
echo '[11/12] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only HA inventory completed.'
echo 'NOT PROVEN: actual zone resilience, failover, RPO/RTO, data integrity or independent review.'
```

Run `chmod +x verify-ch51.sh && ./verify-ch51.sh | tee evidence-ch51/preflight.txt`. If the Kafka cluster is unavailable, preserve partial evidence; an inventory failure is not permission to force controller or broker changes.

## 10. Twelve failure-domain scenarios

### Scenario 1 — One broker unavailable during acks=all traffic

**Diagnose:** Assess partition leadership, RF/minISR, ISR and client callbacks. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 2 — Controller voter loss but majority retained

**Diagnose:** Verify remaining quorum, leader election and change freeze. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 3 — Loss of controller majority

**Diagnose:** Declare metadata outage and escalate version-supported quorum recovery; no ad-hoc voter edits. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 4 — Single AZ outage with uneven replica placement

**Diagnose:** Map racks, ISR, controller voters, clients and PVs to affected partitions. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 5 — PodDisruptionBudget permits unsafe concurrent maintenance

**Diagnose:** Inspect PDB and application-specific ISR/quorum gates; block drain. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 6 — PersistentVolume pinned to failed zone

**Diagnose:** Inspect PV node affinity, CSI behavior and approved DR/restore procedure. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 7 — Cross-zone network partition

**Diagnose:** Differentiate broker replica fetch from controller quorum and client metadata reachability. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 8 — Kafka CR Ready but application SLO fails

**Diagnose:** Reconcile callbacks, event age and sink ledger. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 9 — Client cannot reach newly elected broker leader

**Diagnose:** Inspect advertised listener, DNS, LB and NetworkPolicy. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 10 — Insufficient capacity after zone loss

**Diagnose:** Review headroom, resource quotas, Pod Pending and storage saturation. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 11 — Consumer rebalance storm during node maintenance

**Diagnose:** Review group churn, max.poll.interval, sink idempotence and Pod rollout. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

### Scenario 12 — Prometheus absent during failover

**Diagnose:** Treat SLO as Unknown and validate CLI plus client ledger. Correlate controller majority, broker leader/ISR, Pod/PVC topology, DNS/TLS, producer callbacks, consumer freshness and missing telemetry. **Decision:** Block unsafe changes, escalate owner and choose supported, approved recovery. **Acceptance:** Redacted UTC evidence, expected vs observed outcome, event ledger and independent reviewer.

## 11. Eight production HA runbooks

### Runbook A — HA architecture readiness review

**Trigger and first response:** Validate zone/node/PV maps, controller majority, broker RF/ISR, SLO and signoff before changes. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook B — Broker or node loss

**Trigger and first response:** Check Pod/Node, partition leader/ISR, producer callbacks, consumer freshness and safe capacity. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook C — KRaft controller quorum degradation

**Trigger and first response:** Inspect metadata quorum, voter placement, logs, network and supported recovery escalation. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook D — AZ outage and multi-zone recovery

**Trigger and first response:** Map failed domain, controller/broker/PV impact, client connectivity, approved rollback and DR decision. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook E — Pod drain and rolling maintenance safety

**Trigger and first response:** Validate PDB, ISR, controller majority, node capacity and Strimzi-approved operations. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook F — Storage/PVC/CSI resilience failure

**Trigger and first response:** Inspect PV topology, mounts, disk health, data integrity and approved restore plan. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook G — Secure network and listener failover

**Trigger and first response:** Validate DNS, per-broker advertised endpoints, TLS/SASL/ACL and client retry behavior. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

### Runbook H — SLO recovery, data reconciliation and postmortem

**Trigger and first response:** Reconcile accepted unique IDs, durable sink, alert freshness, RPO/RTO evidence and corrective actions. **Safety gates:** No unsafe KRaft voter mutation, broker PVC deletion, unclean election or minISR/acks weakening. **Exit criteria:** Approved mitigation, quorum/ISR evidence, application SLO and unique-event reconciliation, alert recovery and postincident owner.

## 12. Evidence package

```text
evidence-ch51/
  approval-and-service-slo.md
  context-version-matrix.md
  preflight.txt
  region-zone-node-dependency-map.md
  kraft-voter-quorum-placement.md
  broker-rack-replica-isr.md
  node-topology-affinity.md
  pdb-drain-safety.md
  pvc-pv-csi-zone-binding.md
  controller-broker-capacity.md
  secure-listener-connectivity.md
  producer-durability-contract.md
  consumer-replay-idempotence.md
  slo-error-budget-failure-matrix.md
  broker-loss-tabletop.md
  controller-voter-loss-tabletop.md
  zone-loss-tabletop.md
  storage-csi-tabletop.md
  ha-alerting-coverage.md
  accepted-processed-ledger.csv
  readiness-scorecard.md
  independent-security-review.md
  independent-signoff.md
```

Evidence requires exact version, source, UTC timestamp, expected and observed result, redaction, owner, rollback/abort and assessor. A single-zone local lab cannot earn multi-zone failover acceptance without actual cross-zone infrastructure and independent validation.

## 13. 100-point HA architecture assessment

| Domain | Points | Critical |
|---|---:|---|
| Scope, service tier, RPO/RTO and safety | 10 | Yes |
| KRaft controller quorum and placement | 15 | Yes |
| Broker replica placement, ISR/minISR and durability | 15 | Yes |
| Kubernetes topology, scheduling and PDB | 15 | Yes |
| PVC/PV/CSI and zone storage resilience | 15 | Yes |
| Secure listeners and application failover | 10 | Yes |
| SLO, error budget, alerts and telemetry | 5 | Yes |
| Failure-domain tabletop and recovery gates | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced. **Automatic Fail:** fabricated zone failover, quorum voter manipulation, unsafe PVC deletion, weakened durability, security bypass, missing unique-event reconciliation, absent independent review or untested production readiness claims.

## 14. Cleanup, references and next chapter

Remove only chapter-owned synthetic clients, topic and test alerts via approved GitOps. Preserve sanitized topology and decision evidence. Never delete production PVCs, offsets, topics, KafkaUser Secrets or monitoring data.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes Topology Spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/), [Kubernetes PDBs](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 052 — Kafka Broker Failover, Leader Elections, ISR Recovery and Safe Kubernetes Maintenance.

---

**Verification boundary:** GitHub publication confirms the document exists, not that HA, zonal failover, RPO/RTO, live drills or independent security review have passed.
