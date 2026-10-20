# Chapter 052 — Kafka Broker Failover, Leader Elections, ISR Recovery and Safe Kubernetes Maintenance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 11 — High Availability, Failover and Disaster Recovery (2/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–051, especially 011–015, 041–051  
**Status:** Published · **Live lab validation:** Pending · **Independent technical/security review:** Pending

> **Safety:** All broker, controller, node-drain and storage-failure exercises in this chapter are tabletop or read-only. Never delete production Kafka Pods/PVCs, drain nodes, manipulate KRaft voter membership, force unclean leader election, weaken acks/minISR, bypass TLS/SASL/ACLs or patch operator-owned StatefulSets directly. Any actual rolling maintenance requires a separately approved Strimzi-version-specific runbook and change window.

## 1. Mission

Learn how Kafka partition leadership, ISR membership, broker recovery and KRaft controller quorum interact with Kubernetes Pod lifecycle, PodDisruptionBudgets, PV topology and Strimzi reconciliation. Plan maintenance that preserves Kafka durability and service SLOs, stop safely when conditions degrade, and verify end-to-end client recovery.

## 2. Key concepts and learning objectives

- Distinguish a **partition leader election** (data-plane partition leadership) from a **KRaft controller leader election** (metadata quorum).
- Explain why RF, ISR, minISR, acks=all and unclean leader election govern availability/durability tradeoffs.
- Identify safe rolling-maintenance prerequisites: controller quorum, ISR, broker/Pod/PVC health, PDB, capacity, network and SLO.
- Investigate leader skew, follower catch-up, under-replicated/offline partitions and broker return-to-service.
- Coordinate Strimzi-supported operations through GitOps rather than direct operator-owned workload edits.
- Validate producer callbacks, consumer freshness and unique durable sink reconciliation after failover.

## 3. Architecture and failure transitions

```text
 Producer (acks=all) -> Partition leader (broker A)
                              |
                     ISR followers B and C
                              |
                     log dirs / PVC / CSI
                              |
                 Kafka metadata / KRaft quorum
                    controller voters
                              |
                    Strimzi reconciler
                              |
             Kubernetes Pods / Nodes / PDB
                              |
          synthetic callbacks / consumer sink
```

**Partition failover:** When a partition leader becomes unavailable, an eligible in-sync replica can become leader through the metadata/controller path. Client metadata refresh and retries may introduce temporary errors; correctness is verified by acknowledged unique events, not a green Pod count.

**KRaft quorum:** A controller majority is necessary for metadata coordination. It is distinct from the number of in-sync partition replicas. Do not assume a healthy ISR proves controller majority or vice versa.

**PDB caution:** A PodDisruptionBudget limits certain voluntary evictions; it does not guarantee Kafka ISR/minISR, metadata quorum or safe simultaneous Strimzi rolling actions. Verify application-level gates independently.

## 4. Failover safety matrix

| Condition | Read-only evidence | Decision |
|---|---|---|
| KRaft leader/voter majority unknown | quorum CLI, controller logs | BLOCK |
| Under-minISR or offline partition | topic describe, metrics, callbacks | BLOCK |
| Broker Pod/PVC not healthy | Pod/PVC/CSI events | BLOCK |
| Missing telemetry | Prometheus target freshness, Kafka CLI | UNKNOWN / ESCALATE |
| PDB disallows eviction | `kubectl get pdb` | BLOCK |
| PV zone affinity incompatible with target node | PV/PVC, node labels | BLOCK |
| SLO burn or unreconciled accepted events | client ledger, event age | BLOCK |
| Change owner/rollback missing | ticket, GitOps diff | BLOCK |
| All checks healthy and independently approved | signed evidence | ELIGIBLE FOR REVIEW, not automatic execution |

## 5. Read-only Kubernetes and Kafka diagnostic commands

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc,pdb -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl get nodes -L topology.kubernetes.io/zone -o wide
kubectl -n kafka-lab get kafka sre-kafka -o jsonpath='{.status.conditions}{"\n"}'
kubectl -n kafka-lab get kafkanodepool -o custom-columns=NAME:.metadata.name,ROLES:.spec.roles,REPLICAS:.spec.replicas

# KRaft quorum from an isolated CLI Pod; plaintext listener is lab-only.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status

# Synthetic topic leader, replica and ISR metadata.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-failover-synthetic

# Inspect actual broker Pod chosen from inventory.
kubectl -n kafka-lab describe pod BROKER_POD_NAME
kubectl -n kafka-lab logs BROKER_POD_NAME --since=15m --timestamps --tail=300
```

Check the installed Strimzi/Kafka release and CRD schema before using any operator feature. Production-like CLI requires TLS/SASL and approved `--command-config`. Avoid committing full YAML or logs before sensitivity review.

## 6. Twenty Kubernetes-first failover and maintenance labs

### Lab 01 — Approve failover and maintenance change charter

**Objective and procedure:** Document namespace, version matrix, approved maintenance window, owner, change ticket, backups, synthetic topic, abort and rollback gates.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 02 — Inventory Kafka KRaft and Strimzi topology

**Objective and procedure:** Read Kafka/NodePool CR, broker/controller roles, voter count, node placement, operator status and GitOps revision.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 03 — Baseline partition leadership and ISR

**Objective and procedure:** Capture topic leader, RF, ISR, minISR, offline partitions, under-replicated partitions and synthetic producer callbacks.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 04 — Baseline KRaft metadata quorum

**Objective and procedure:** Run metadata-quorum describe --status; identify leader, voter majority and controller stability before any change.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 05 — Inspect broker Pod and Node health

**Objective and procedure:** Review Pod readiness, restarts, node conditions, pressure, kubelet events and CPU/memory/storage headroom.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 06 — Inspect PDB and voluntary eviction constraints

**Objective and procedure:** Read PDB allowedDisruptions and identify why it does not independently guarantee Kafka ISR or KRaft safety.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 07 — Inspect Pod placement and AZ resilience

**Objective and procedure:** Compare broker/controller node pools, zone labels, anti-affinity, topology spread and PV zone affinity.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 08 — Inspect Strimzi rolling update mechanics

**Objective and procedure:** Review Kafka CR generation, operator logs and release-supported rolling maintenance controls; avoid direct Pod deletion.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 09 — Observe leader election from historical evidence

**Objective and procedure:** Analyze a bounded synthetic or historical broker failover timeline, leader change, client retry and replica catch-up.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 10 — Model preferred leader balance

**Objective and procedure:** Review leader distribution and supported preferred-leader behavior; no production election triggers.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 11 — Model under-minISR during rolling maintenance

**Objective and procedure:** Compute how one unavailable replica affects acks=all and identify stop/go gates per partition.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 12 — Model controller voter availability during maintenance

**Objective and procedure:** Calculate majority under concurrent failures and require independent KRaft quorum gate.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 13 — Inspect storage recovery and follower catch-up

**Objective and procedure:** Correlate PVC/CSI health, log directory status, follower fetch lag, network and disk latency.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 14 — Validate producer failover behavior

**Objective and procedure:** Review idempotence, retries, delivery timeout, callbacks and acknowledged unique-event ledger.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 15 — Validate consumer failover behavior

**Objective and procedure:** Review coordinator transitions, rebalances, offset commits, event age, sink idempotency and recovery SLO.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 16 — Practice maintenance preflight in read-only mode

**Objective and procedure:** Run safe verifier, capture evidence and explicitly choose PROCEED/BLOCK/ESCALATE without changing Kafka state.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 17 — Run synthetic client-only leader-unreachable drill

**Objective and procedure:** Configure a dedicated test client with an invalid broker endpoint, capture metadata/retry failures, restore and reconcile.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 18 — Run broker-failure tabletop

**Objective and procedure:** Use synthetic broker unavailability and ISR evidence to rehearse escalation, maintenance cancellation and recovery.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 19 — Run node-drain tabletop

**Objective and procedure:** Evaluate Pod eviction, PDB, quorum/ISR, PVC topology and approved Strimzi orchestration; do not drain shared nodes.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

### Lab 20 — Complete independent maintenance acceptance

**Objective and procedure:** Verify SLO, quorum, ISR, synthetic event reconciliation, security, change record, 100-point rubric and signoff.

**Evidence and acceptance:** Record approved Kubernetes context, Kafka/Strimzi version, UTC timestamp, exact command/query, expected and observed state, quorum/ISR gate, producer/consumer SLO, rollback/abort condition and independent reviewer. Mark **Pending** until executed. Broker/controller/PVC/node failure simulations must remain tabletop.

## 7. Version-aware maintenance sequence (planning only)

```text
1. Create change ticket and review Strimzi-supported maintenance mechanism.
2. Confirm synthetic and production SLO visibility, independent client ledger.
3. Verify controller voter majority and metadata quorum health.
4. Verify topic leaders, ISR/minISR, offline/under-replicated partitions.
5. Verify broker/controller Pods, node placement, PDB, PV topology, capacity.
6. Confirm operator Ready, CR generation, GitOps revision and no competing roll.
7. Approve one bounded operator-supported maintenance step.
8. Revalidate quorum, ISR, client callbacks, freshness and PVC after each step.
9. If any gate fails: STOP, escalate and follow approved rollback/recovery.
10. Close only after unique-event reconciliation and independent signoff.
```

This is not an executable production maintenance procedure. Rolling update annotations, KafkaNodePool controls and supported restart behavior vary by Strimzi release and require the vendor documentation for the installed version.

## 8. Read-only verification script

Save as `verify-ch52.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPIC=sre-failover-synthetic
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Kafka and NodePools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/12] Broker/controller Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/12] PVC inventory'; kubectl -n "$NS" get pvc -o wide
echo '[5/12] PDB inventory'; kubectl -n "$NS" get pdb
echo '[6/12] Zone topology'; kubectl get nodes -L topology.kubernetes.io/zone
echo '[7/12] Kafka conditions'; kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[8/12] Kafka NodePool roles'; kubectl -n "$NS" get kafkanodepool -o custom-columns=NAME:.metadata.name,ROLES:.spec.roles,REPLICAS:.spec.replicas
echo '[9/12] Topic ISR'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" --bootstrap-server "$BS" --describe --topic "$TOPIC"
echo '[10/12] Kubernetes Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[11/12] StorageClasses'; kubectl get storageclass
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only maintenance preflight inventory.'
echo 'NOT PROVEN: actual failover, maintenance safety, data integrity, SLO or independent approval.'
```

Run `chmod +x verify-ch52.sh && ./verify-ch52.sh | tee evidence-ch52/preflight.txt`. Inventory success does not authorize maintenance; missing synthetic topic or RBAC access must be recorded explicitly.

## 9. Twelve failover troubleshooting scenarios

### Scenario 1 — Broker fails during a rolling maintenance

**Diagnosis:** Stop changes; inspect partition leaders/ISR, Pod/PVC, operator reconciliation and client SLO. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 2 — ISR shrinks below minISR

**Diagnosis:** Block further broker maintenance and preserve acks=all/minISR. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 3 — KRaft quorum majority threatened by drain

**Diagnosis:** Cancel drain and escalate supported controller recovery. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 4 — PDB allows eviction but partition unavailable

**Diagnosis:** Explain why Kubernetes disruption allowance is not Kafka-level safety. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 5 — Follower never rejoins ISR after broker return

**Diagnosis:** Inspect fetcher lag, log-dir errors, disk/network saturation and replica health. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 6 — Preferred leader distribution skewed after recovery

**Diagnosis:** Review leadership balance and supported version-specific balancing actions. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 7 — Pod stuck Terminating or Pending

**Diagnosis:** Inspect finalizers, CSI mount, scheduling and operator status without forced deletion. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 8 — PersistentVolume pinned to unavailable AZ

**Diagnosis:** Assess topology, recovery plan and approved storage restoration. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 9 — Producer timeouts during leader election

**Diagnosis:** Correlate callbacks, retry/backoff, metadata refresh and durability settings. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 10 — Consumer rebalances and duplicates during failover

**Diagnosis:** Reconcile group assignment, offset commits and sink idempotency. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 11 — Strimzi reconciliation stuck mid-roll

**Diagnosis:** Inspect CR conditions, operator logs, node pool and supported maintenance procedures. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

### Scenario 12 — Dashboard green while accepted events missing

**Diagnosis:** Use producer callback and durable sink ledger; keep incident open. Correlate KRaft quorum, topic leader/ISR, Strimzi CR, Pod/PDB/PVC/CSI, client callbacks, consumer freshness and telemetry age. **Response:** Stop unsafe changes, preserve durability, obtain owner approval and use version-supported recovery. **Verification:** Redacted UTC evidence, unique-event reconciliation and independent review.

## 10. Eight production SRE runbooks

### Runbook A — Kafka maintenance change preflight

**Trigger and first response:** Require quorum/ISR, Pod/PVC, PDB, SLO, GitOps revision, capacity, rollback and owner signoff. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook B — Broker leader failover incident

**Trigger and first response:** Inspect leaders, ISR, broker Pod, controller metadata and synthetic callback errors. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook C — Under-minISR maintenance abort

**Trigger and first response:** Freeze rolling changes, preserve durability and diagnose follower catch-up. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook D — KRaft controller quorum safety

**Trigger and first response:** Verify voter majority, leader and controller logs; prohibit ad-hoc voter changes. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook E — Strimzi-supported rolling maintenance

**Trigger and first response:** Use reviewed CR/operator procedures and wait for safety gates between steps. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook F — Node drain and eviction readiness

**Trigger and first response:** Review PDB, topology, PV affinity, broker/controller placement and rollback. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook G — Follower replication and storage recovery

**Trigger and first response:** Inspect replica fetch, disk I/O, PVC/CSI and supported reassignment/restore. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

### Runbook H — Recovery verification and incident closure

**Trigger and first response:** Reconcile acknowledged unique IDs, consumer sink, event age, alert freshness and corrective actions. **Safety:** Never use unclean leader election or minISR/acks weakening to hide a failed gate; no direct operator-owned Pod deletion or PVC removal. **Exit criteria:** Approved recovery, healthy quorum/ISR, client SLO, durable sink ledger, monitoring and corrective-action owner.

## 11. Evidence package

```text
evidence-ch52/
  maintenance-charter-approval.md
  context-version-matrix.md
  preflight.txt
  nodepool-controller-broker-topology.md
  topic-leader-isr-baseline.md
  kraft-quorum-baseline.md
  pod-node-health.md
  pdb-eviction-analysis.md
  zone-and-pv-placement.md
  strimzi-rolling-maintenance.md
  leader-election-timeline.md
  leader-balance-analysis.md
  min-isr-change-gates.md
  controller-majority-gates.md
  pvc-csi-follower-catchup.md
  producer-callback-ledger.csv
  consumer-freshness-ledger.csv
  maintenance-go-no-go.md
  synthetic-client-drill.md
  broker-failure-tabletop.md
  node-drain-tabletop.md
  independent-technical-security-review.md
  readiness-scorecard.md
```

All evidence must include exact source/version, UTC time, expected/observed result, owner, redaction, rollback/abort and assessor. Tabletop outcomes are not live failover evidence.

## 12. 100-point failover and maintenance assessment

| Domain | Points | Critical |
|---|---:|---|
| Change scope, safety, owner and rollback | 10 | Yes |
| KRaft controller quorum and roles | 15 | Yes |
| Partition leader, ISR/minISR and durability | 15 | Yes |
| Strimzi operator and GitOps rolling controls | 15 | Yes |
| Kubernetes PDB, nodes and zone placement | 10 | Yes |
| PVC/CSI, follower recovery and disk safety | 10 | Yes |
| Producer/consumer failover SLO and ledger | 10 | Yes |
| Tabletop incidents, abort and recovery gates | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and every critical gate evidenced. **Automatic Fail:** unapproved broker/controller disruption, unsafe node drain, direct PVC deletion, ad-hoc quorum voter edits, unclean election, weakened durability/security, missing event reconciliation, fabricated drills or absent independent review.

## 13. Cleanup, references and next chapter

Remove only chapter-owned synthetic clients, topics and alerts through approved GitOps. Preserve redacted evidence and action tracker. Never delete production topics, offsets, PVCs, operator-managed Secrets or monitoring stores.

**References:** [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes PodDisruptionBudgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [Kubernetes Node Drain](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/), [Kubernetes Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).

**Next:** Chapter 053 — Kafka Multi-Zone Resilience, Disaster Recovery Architecture, RPO and RTO Engineering.

---

**Verification boundary:** GitHub publication establishes document availability only. Live failover, rolling maintenance, recovery SLO, data-integrity and independent security acceptance remain Pending.
