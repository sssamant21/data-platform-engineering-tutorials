# Chapter 047 — Kafka Broker, KRaft Controller, Replication and Storage Failure Troubleshooting

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 10 — Troubleshooting and Incident Response (2/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–046, especially Chapters 011–015, 021–025, 036–046  
**Status:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use approved disposable Kubernetes clusters and synthetic Kafka clients. Do not kill production brokers/controllers, modify KRaft voter sets, delete broker PVCs, reset consumer offsets, force unclean leader election, weaken min.insync.replicas or acks, bypass TLS/ACLs or manually patch Strimzi-owned Pods/StatefulSets. Simulate high-risk quorum/storage failures using tabletop or synthetic metrics, not real destructive operations.

## 1. Mission

Troubleshoot Kafka broker, KRaft controller, partition replication and storage incidents using a systematic Kubernetes-first workflow. Separate client-visible availability from cluster readiness, diagnose metadata quorum and ISR conditions, correlate Kafka metrics with Strimzi/Kubernetes Pod and PVC state, and choose evidence-based recovery without compromising durability or data integrity.

## 2. Failure-domain architecture

```text
Producer (acks=all) -------> Kafka partition leader
      |                             |
 callback SLI                  follower replicas / ISR
      |                             |
      +-----------+-----------------+
                  |
              broker Pods
            log dirs / PVC / CSI
                  |
          KRaft metadata quorum
           controller node pools
                  |
          Strimzi reconciliation
          Kafka + KafkaNodePool CR
                  |
     Kubernetes nodes / storage / network
                  |
       Prometheus / logs / traces
```

**Key distinction:** A KRaft controller quorum issue affects metadata coordination; a broker/data-plane problem affects partition leaders, replica fetch and client requests. They can overlap, but a single red metric does not prove the root cause. Kafka CR Ready is not sufficient to assert that producer acknowledgments or downstream processing meet SLOs.

## 3. Broker, controller and replication failure signatures

| Symptom | Candidate causes | Independent evidence | Safety action |
|---|---|---|---|
| No metadata quorum leader | voter/network/CPU/disk instability | metadata-quorum CLI, controller logs | freeze risky changes |
| Under-minISR | follower lag, broker/storage/network issue | partition describe, metrics, callbacks | preserve acks/minISR |
| Offline partitions | no eligible leader, log-dir outage | topic metadata, broker logs | avoid unclean election |
| Broker CrashLoopBackOff | JVM/OOM, config, mount errors | Pod describe, logs, CSI events | avoid repeated forced restart |
| PVC Pending | storage provisioning/topology/CSI | PVC events, StorageClass, nodes | do not delete PVC |
| High request latency | disk/CPU/GC/network/quota | broker queues, JVM, I/O, producer SLI | investigate bottleneck |
| Stalled Strimzi reconcile | invalid CR, RBAC, operator/API issue | CR conditions, operator logs | GitOps-approved correction |
| Missing metrics | exporter/target failure | scrape freshness, CLI | mark Unknown, not healthy |

## 4. Durability and recovery guardrails

- **Replication factor (RF)** is the configured replica count; **ISR** is the set of sufficiently caught-up replicas. `min.insync.replicas` combined with producer `acks=all` sets an acknowledgment condition, not an absolute data-loss guarantee under all failure modes.
- Under-minISR is a safety condition, not a prompt to lower `min.insync.replicas`.
- Unclean leader election can trade data durability for availability and must not be used casually to recover an incident.
- A controller voter majority is required for a healthy KRaft metadata quorum. Use supported version-specific recovery procedures; do not manually manipulate quorum membership.
- Broker PVCs contain Kafka data. Deleting or recreating them without an approved restore/reassignment plan can cause irreversible loss.
- Strimzi owns reconciliation of Kafka and KafkaNodePool resources. Use reviewed CR/GitOps changes and supported maintenance procedures rather than direct workload patches.

## 5. Read-only Kubernetes and Kafka diagnostics

```bash
# Confirm scope, versions and desired state.
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get kafka sre-kafka -o yaml
kubectl -n kafka-lab get kafkanodepool -o yaml

# Inspect KRaft quorum from an isolated Kafka CLI Pod.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status

# Inspect a dedicated synthetic topic's replication state.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-triage-synthetic

# Inspect a specific broker Pod, selected from inventory.
kubectl -n kafka-lab describe pod BROKER_POD_NAME
kubectl -n kafka-lab logs BROKER_POD_NAME --since=15m --timestamps --tail=300
```

These are isolated-lab examples with a plaintext internal listener; production-like clients must use TLS/SASL and least-privilege ACLs. Kafka Pod naming and Strimzi resource API versions vary; discover actual names and CRD schema before use. Do not commit full `get ... -o yaml` output without checking for sensitive annotations or references.

## 6. Twenty Kubernetes-first hands-on labs

### Lab 01 — Approve broker and storage incident scope

**Objective and procedure:** Document isolated cluster, incident owner, Kafka version, synthetic topic, security controls, change freeze, abort conditions and explicit no-broker-disruption policy.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 02 — Inventory KafkaNodePool roles and topology

**Objective and procedure:** Inspect broker/controller node pools, replica counts, labels, rack/failure-domain placement and operator-managed workload ownership.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 03 — Baseline KRaft quorum

**Objective and procedure:** Use kafka-metadata-quorum.sh describe --status to capture leader, leader epoch, high watermark, voters and observer state where supported.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 04 — Baseline broker and partition metadata

**Objective and procedure:** Inspect Kafka Ready, broker Pods, KafkaTopic, partition leaders, replication factor, ISR, offline/under-replicated partition metrics and synthetic callback SLI.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 05 — Differentiate broker failure from controller failure

**Objective and procedure:** Compare client data-plane requests with metadata quorum/controller symptoms, node roles, logs and network reachability.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 06 — Inspect Strimzi reconciliation and generation

**Objective and procedure:** Compare Kafka and KafkaNodePool desired specs, observed generation, Ready conditions, operator logs and GitOps commit; avoid manual StatefulSet/Pod mutations.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 07 — Inspect Kubernetes Pod readiness and restarts

**Objective and procedure:** Check waiting reasons, probes, restarts, OOMKilled, scheduling constraints, resource limits and node pressure.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 08 — Inspect PersistentVolumeClaim and CSI health

**Objective and procedure:** Record PVC Bound state, StorageClass, PV topology, attach/mount events, capacity and CSI errors; never delete broker PVCs.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 09 — Inspect disk throughput, queue and latency

**Objective and procedure:** Compare disk utilization, IOPS, throughput, queue depth, fsync and log flush latency; identify cloud storage bottlenecks.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 10 — Inspect log directory health

**Objective and procedure:** Review Kafka log directory metrics and broker error logs, distinguish offline log directories from temporary disk pressure and avoid log-directory deletion.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 11 — Inspect replication and follower catch-up

**Objective and procedure:** Correlate ISR shrink/expand, fetcher lag, network/IO saturation, under-minISR and producer acks=all errors.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 12 — Inspect unclean leader election risk

**Objective and procedure:** Review topic/broker configuration and durability policy; never enable unclean leader election to mask an outage.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 13 — Inspect metadata/controller logs

**Objective and procedure:** Collect bounded, redacted controller and broker logs, controller event timing, leader elections and reconciliation warnings.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 14 — Inspect broker CPU, heap and GC

**Objective and procedure:** Correlate throttling, OOM, heap/GC, request handler queues and replica fetcher behavior without arbitrary tuning.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 15 — Inspect listener/TLS/network failure

**Objective and procedure:** Validate advertised listeners, Services/endpoints, DNS, NetworkPolicy, TLS/SASL and ACLs without disabling authentication.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 16 — Validate KRaft metrics freshness

**Objective and procedure:** Cross-check metadata quorum CLI against Prometheus controller/broker metrics; explicitly mark stale/absent telemetry Unknown.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 17 — Run synthetic producer error triage

**Objective and procedure:** Inject client-only callback failures, verify quorum/ISR unaffected, capture acknowledgments/retries, restore and reconcile unique accepted IDs.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 18 — Run synthetic storage-pressure tabletop

**Objective and procedure:** Use historical/synthetic disk latency and PVC scenarios to choose safe capacity remediation; do not fill broker disks.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 19 — Run recovery and change-gate tabletop

**Objective and procedure:** Practice BLOCK/EXCEPTION/APPROVE decisions for under-minISR, quorum risk, PVC pressure and Strimzi rollouts with owner approval.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

### Lab 20 — Complete independent failure triage assessment

**Objective and procedure:** Run read-only verifier, build evidence timeline, validate data-integrity and recovery criteria, review security and score 100-point rubric.

**Validation and evidence:** Record approved context, Kafka/Strimzi version, exact query or command, UTC timestamp, hypothesis, expected/observed result, Kafka quorum/ISR impact, client SLI, rollback/abort criteria and independent reviewer. Mark **Pending** until executed. No destructive broker/controller/PVC actions are authorized by this chapter.

## 7. Read-only incident inventory script

Save as `verify-ch47.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/12] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Pods'
kubectl -n "$NS" get pods -o wide
echo '[5/12] PVCs'
kubectl -n "$NS" get pvc -o wide
echo '[6/12] Kafka conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[7/12] Kafka NodePool roles'
kubectl -n "$NS" get kafkanodepool -o jsonpath='{range .items[*]}{.metadata.name}{" roles="}{.spec.roles}{"\n"}{end}'
echo '[8/12] StorageClasses'
kubectl get storageclass
echo '[9/12] Strimzi operator inventory'
kubectl get deployments -A | grep -i strimzi || true
echo '[10/12] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[11/12] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only broker/controller/storage inventory.'
echo 'NOT PROVEN: incident root cause, ISR health for all topics, live failure drills or security acceptance.'
```

Run `chmod +x verify-ch47.sh && ./verify-ch47.sh | tee evidence-ch47/preflight.txt`. A failed Kafka Ready check during an incident is useful evidence; do not stop the overall investigation solely because this preflight exits early.

## 8. Safe failure simulation design

**Producer-only failure:** Inject bounded errors into a dedicated synthetic producer; compare callback error rate, retries, Kafka quorum/ISR and downstream unique-event reconciliation. Restore client and verify recovery.

**Storage failure tabletop:** Supply synthetic PVC Pending, CSI attach timeout, high disk queue and offline log-directory evidence. Ask the operator to classify the failure and choose approved capacity/storage remediation; do not fill or delete broker disks.

**KRaft quorum tabletop:** Use a recorded/synthetic controller leader-loss scenario to practice incident declaration, change freeze, owner escalation and supported recovery decision; do not kill controllers or edit voter configuration.

**Abort:** End the exercise if any unapproved namespace, real on-call route, Kafka quorum/ISR, sensitive credential or production workload is affected.

## 9. Twelve failure troubleshooting scenarios

### Scenario 1 — Broker Pod CrashLoopBackOff

**Detect and diagnose:** Check container exit reason, JVM/OOM, mounted log directories, config and Strimzi reconciliation. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 2 — KRaft controller leader unknown

**Detect and diagnose:** Compare metadata quorum CLI, controller logs, voter connectivity and API freshness; freeze changes. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 3 — Under-minISR with acks=all failures

**Detect and diagnose:** Inspect RF/minISR, ISR, follower lag, storage and network; preserve durability. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 4 — Offline partition after broker restart

**Detect and diagnose:** Inspect partition metadata, leader eligibility, storage availability and controller logs. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 5 — PVC Pending and broker unschedulable

**Detect and diagnose:** Inspect StorageClass, CSI, topology, quota and Pod scheduling events; avoid PVC deletion. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 6 — Broker disk nearly full

**Detect and diagnose:** Correlate retention, segment growth, filesystem capacity and storage forecasts; approve capacity remediation. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 7 — High disk latency and replica lag

**Detect and diagnose:** Compare disk queue, fsync, follower fetch and network; avoid unsafe concurrency spikes. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 8 — Kafka Ready but synthetic producer errors

**Detect and diagnose:** Inspect client listener/auth, quotas, partition ISR and callback SLI. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 9 — Frequent controller elections

**Detect and diagnose:** Review KRaft voters, network, CPU/GC, node churn and version-specific metrics. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 10 — Log directory marked offline

**Detect and diagnose:** Review broker errors, CSI/PV mount, filesystem and storage node; escalate supported recovery. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 11 — Prometheus ISR gauge stale

**Detect and diagnose:** Compare Kafka CLI partition describe and target timestamps; report monitoring blind spot. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

### Scenario 12 — Strimzi reconciliation blocked by invalid spec

**Detect and diagnose:** Inspect CR conditions, schema, operator logs and GitOps diff; use approved rollback. Correlate KRaft quorum, partition ISR, Kafka CR conditions, Pod/PVC/CSI events, storage/CPU/GC metrics and client SLO. **Mitigate:** Use only owner-approved, version-supported actions with rollback and durability protections. **Verify:** Recheck quorum, ISR, synthetic callbacks and unique accepted/processed IDs; preserve redacted UTC timeline.

## 10. Eight production SRE runbooks

### Runbook A — Broker crash and Pod readiness

**Trigger and first response:** Verify incident scope, Pod exit reasons, Kafka/NodePool Ready, logs, storage mounts, safe recovery and callback SLI. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook B — KRaft controller/quorum degradation

**Trigger and first response:** Confirm leader/voter status and controller connectivity, freeze changes, escalate to Kafka SRE and preserve quorum. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook C — Under-minISR and partition unavailability

**Trigger and first response:** Inspect RF, ISR, leader, follower lag and acks=all failures; never weaken durability to hide errors. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook D — PVC/CSI attachment and mount failure

**Trigger and first response:** Inspect PV/PVC/StorageClass, node topology, CSI events, filesystem health and approved recovery. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook E — Disk latency, capacity and offline log directory

**Trigger and first response:** Correlate throughput, IOPS, queue, fsync, retention and offline log-dir signals; use approved capacity actions. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook F — Broker CPU, heap, GC and request saturation

**Trigger and first response:** Correlate JVM and Pod resource pressure, request queues, replication lag and recent workload changes. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook G — Strimzi reconciliation and GitOps drift

**Trigger and first response:** Compare CR observed generation, operator logs, desired spec, RBAC and approved rollback. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

### Runbook H — Incident recovery, event integrity and postmortem

**Trigger and first response:** Verify KRaft/ISR, client callback and unique processing ledgers, alert resolution, communications and corrective actions. **Evidence:** Capture exact versions, UTC timeline, Kafka/KRaft/ISR, Strimzi CR, Pod/PVC and application SLI. **Recovery gate:** Owner-approved change, independent safety verification, no unaccounted synthetic events, restored monitoring and documented follow-up.

## 11. Evidence package

```text
evidence-ch47/
  approval-and-scope.md
  version-and-context.md
  preflight.txt
  kafkanodepool-roles-and-topology.md
  kraft-quorum-status.md
  broker-partition-isr-baseline.md
  broker-controller-failure-domain.md
  strimzi-reconciliation.md
  pod-readiness-restarts.md
  pvc-csi-health.md
  disk-throughput-latency.md
  log-directory-health.md
  replication-follower-catchup.md
  durability-policy-review.md
  controller-broker-redacted-logs.md
  cpu-heap-gc.md
  listener-tls-network.md
  prometheus-freshness.md
  synthetic-producer-drill.md
  storage-pressure-tabletop.md
  quorum-isr-recovery-tabletop.md
  incident-timeline.md
  accepted-processed-ledger.csv
  security-review.md
  independent-signoff.md
```

Every artifact requires actual source, software version, UTC time, expected/observed result, owner, redaction, safety/rollback decision and assessor. Tabletop outcomes must be labeled Simulated; publication is not live execution.

## 12. 100-point broker/controller/storage troubleshooting assessment

| Domain | Points | Critical |
|---|---:|---|
| Safety approval, scope and ownership | 10 | Yes |
| KRaft quorum/controller diagnostics | 15 | Yes |
| Broker Pod, Strimzi and Kubernetes diagnosis | 15 | Yes |
| Partition leader, ISR and durability analysis | 15 | Yes |
| PVC/CSI, disk capacity and I/O diagnosis | 15 | Yes |
| CPU/JVM, networking and TLS diagnosis | 10 | Yes |
| Monitoring freshness and client SLI correlation | 5 | Yes |
| Synthetic drill and recovery decision | 10 | Yes |
| Independent security/technical review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. **Automatic Fail:** fabricated execution, unsafe broker/controller/PVC disruption, enabling unclean election without approved recovery, weakening acks/minISR, exposed Secrets, data-integrity gap or absent independent review.

## 13. Cleanup, references and next chapter

Remove only chapter-owned synthetic clients and test alerts via approved GitOps. Preserve sanitized evidence and action backlog. Do not delete Kafka PVCs, production offsets, shared metrics stores or operator-managed Secrets.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes debugging](https://kubernetes.io/docs/tasks/debug/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Google SRE Book — Managing Incidents](https://sre.google/sre-book/managing-incidents/).

**Next:** Chapter 048 — Kafka Producer, Consumer, Consumer Group and End-to-End Data Delivery Troubleshooting.

---

**Verification boundary:** GitHub publication verifies document availability only. Live drills, failure recovery, data integrity, security review and independent technical acceptance remain Pending.
