# Chapter 067 — Strimzi KafkaNodePools, Scheduling, Storage, Availability and Production Operations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 14 — Advanced Kubernetes, Strimzi and GitOps (2/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–066, especially 066  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Run exercises in a dedicated disposable Kubernetes/Strimzi environment. Never resize production PVCs, alter KRaft controller membership, delete KafkaNodePools, drain production nodes or force Kafka broker restarts without approved maintenance, backups, quorum/ISR gates and rollback. Version-specific CRDs must be checked against the installed operator.

## 1. Mission and learning objectives

Operate Strimzi KafkaNodePools as failure-aware Kubernetes infrastructure. Understand broker/controller role separation, Pod scheduling, zone/rack topology, PVC binding and expansion, disk performance, disruption budgets, broker scaling, rolling maintenance and incident recovery.

By the end, the reader can explain why a healthy Kubernetes Deployment is not a healthy Kafka cluster, how storage and node placement affect data durability, and how to plan a safe node-pool change with independent acceptance.

## 2. Architecture

```text
                   GitOps desired state
                           |
                   Kafka / KafkaNodePool
                           |
                    Strimzi Operator
             +-------------+-------------+
             |                           |
     controller node pool          broker node pool
      KRaft metadata quorum        Kafka data/ISR
             |                           |
        PVC / zone A,B,C           PVC / rack A,B,C
             |                           |
       K8s scheduler / storage provisioner / node lifecycle
                           |
                   Kafka client SLOs
```

A KafkaNodePool is a Strimzi custom resource specifying a set of Kafka nodes, their roles and storage/resource templates. Kubernetes schedules Pods and binds volumes; Kafka/Strimzi manage metadata, partitions and rolling operations. These are separate control loops with distinct failure signals.

## 3. KafkaNodePool roles and placement

| Design element | Why it matters | Review |
|---|---|---|
| `controller` role | KRaft metadata quorum | quorum majority and failure domains |
| `broker` role | partitions, leaders, ISR | RF/minISR and broker headroom |
| Separate pools | isolate controller and data workloads | node count and operational cost |
| Node selectors/affinity | constrain placement | node capacity and deadlock risk |
| Topology spread | distribute replicas across zones/nodes | skew and hard constraints |
| Rack awareness | Kafka replica placement | label consistency and reassignment |
| PDB | limits voluntary disruptions | availability during node drains |

A controller quorum generally needs a majority of configured voters. Do not equate broker replica count with KRaft controller voter count. For production, spread controller voters across fault domains where feasible.

## 4. Kubernetes scheduling mechanics

**NodeSelector:** exact label match. **Node affinity:** required or preferred rules. **Taints/tolerations:** allow scheduling onto tainted nodes but do not guarantee placement. **Pod anti-affinity:** avoids co-location, but strict rules can make Pods unschedulable. **Topology spread:** controls distribution across zones or hosts.

Before applying hard constraints, verify node labels, capacity, PVC zone compatibility and expected maintenance/failure cases.

```bash
kubectl get nodes -L topology.kubernetes.io/zone
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get kafkanodepool -o wide
kubectl -n kafka-lab describe pod <broker-pod-name>
```

Replace the placeholder with an actual Pod name. A Pending Pod often reflects multiple interacting constraints: zone-bound PVC, required anti-affinity, taint, quota or lack of CPU/memory.

## 5. Storage, PVCs and disk reliability

Kafka data logs need predictable throughput, low latency and enough headroom for retention, replication catch-up and partition movement. Strimzi persistent-claim storage must be supported by the installed operator/CRD. Check `StorageClass.allowVolumeExpansion` and provider-specific behavior before planning resize.

| Storage choice | Benefit | Risk |
|---|---|---|
| Durable PVC | persistence across some Pod reschedules | zone binding and attachment constraints |
| Local PV | high local I/O potential | node loss and replacement complexity |
| JBOD volumes | distribute log directories | per-volume failure and balancing complexity |
| Ephemeral volume | simple isolated lab | unsuitable for production durability assumptions |

**Do not delete PVCs to fix scheduling.** Verify whether a PVC can reattach in the target zone, whether the filesystem expands online, and how Strimzi handles the particular storage change.

## 6. KafkaNodePool reference manifests

The following are **illustrative**, not guaranteed valid for every Strimzi release. Validate the installed `strimzi.io/v1` CRD schema, storage and resource fields.

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: controllers
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  replicas: 3
  roles:
    - controller
  storage:
    type: persistent-claim
    size: 20Gi
    deleteClaim: false
  resources:
    requests:
      cpu: "500m"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: brokers
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: persistent-claim
    size: 100Gi
    deleteClaim: false
  resources:
    requests:
      cpu: "2"
      memory: "8Gi"
    limits:
      cpu: "4"
      memory: "12Gi"
```

These are lab sizing examples only. Real capacity depends on partitions, bytes/sec, RF, retention, heap, page cache, disk IOPS, CPU and recovery budget. Pair node pools with a compatible Kafka CR and approved TLS/SASL listeners.

## 7. Scaling is not partition rebalancing

Increasing KafkaNodePool broker replicas adds broker capacity, but Kafka partitions do **not** automatically redistribute evenly simply because new broker Pods exist. Plan partition/leader reassignment using a supported tool or operator-integrated workflow and verify ISR, traffic, disk, network and application latency.

Similarly, Kubernetes Cluster Autoscaler or Karpenter can add nodes to schedule Kafka Pods, but does not manage Kafka partition placement or KRaft controller membership.

## 8. Safe rolling maintenance gate

Before any operator-managed broker/controller roll:

1. Record exact Kafka/Strimzi versions, CR desired/observed generation and change approval.
2. Confirm healthy KRaft controller quorum, broker availability, ISR/minISR and no critical under-replicated partitions.
3. Confirm PVC capacity, disk I/O, zone placement, PDB and maintenance window.
4. Verify client SLO baseline and alert coverage.
5. Roll only through the supported Strimzi procedure; pause if quorum, ISR, latency or storage breaches abort thresholds.
6. Reconcile Kafka client smoke, offsets, partitions, Pods and storage before closure.

A `git revert` may restore a manifest but cannot automatically reverse Kafka metadata, partition movement or PVC changes.

## 9. Kubernetes-first read-only preflight

```bash
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get networkpolicy
kubectl explain kafkanodepool.spec
```

Capture `kubectl describe` only for approved objects and redact any credentials from shared evidence.

## 10. Twenty hands-on operational labs

### Lab 01 — Establish change charter

**Procedure:** Define cluster scope, owners, supported versions, capacity baseline, RTO/RPO and abort gates.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 02 — Inventory KRaft quorum

**Procedure:** Inspect KafkaNodePool controller roles, controller availability and metadata quorum signals.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 03 — Inventory broker node pools

**Procedure:** Capture replicas, node IDs, storage class, CPU/memory and per-zone placement.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 04 — Validate CRD schema

**Procedure:** Inspect installed KafkaNodePool CRD, role/storage fields and Kafka resource status.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 05 — Review scheduler constraints

**Procedure:** Inspect nodeSelector, tolerations, node affinity and hard/soft anti-affinity.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 06 — Review topology spread

**Procedure:** Check zone skew, node pool distribution, capacity and pending Pod behavior.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 07 — Review rack awareness

**Procedure:** Map broker rack labels, partition replica placement and ISR risk.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 08 — Inspect PVC binding

**Procedure:** Review PV/PVC status, storage class, volumeBindingMode and topology.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 09 — Assess storage throughput

**Procedure:** Baseline disk latency, IOPS, throughput, Kafka log flush and page cache.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 10 — Assess PVC expansion

**Procedure:** Review allowVolumeExpansion, filesystem growth and operator-supported procedures.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 11 — Assess JBOD storage

**Procedure:** Review per-volume log directory placement, balancing and recovery implications.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 12 — Review broker resource limits

**Procedure:** Inspect heap sizing, CPU throttling, memory, disk and eviction risk.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 13 — Review controller resources

**Procedure:** Inspect isolated controller capacity, disk persistence and network.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 14 — Assess safe scaling

**Procedure:** Compare node pool replica changes, partition reassignment and capacity headroom.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 15 — Review PodDisruptionBudget

**Procedure:** Check voluntary disruption safety versus KRaft quorum and minISR.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 16 — Review rolling maintenance

**Procedure:** Plan one-at-a-time change, leader movement, ISR recovery and abort.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 17 — Review drain/node replacement

**Procedure:** Assess node loss, PVC zone binding, storage reattach and controller safety.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 18 — Review autoscaling policy

**Procedure:** Explain why K8s node autoscaling does not automatically rebalance Kafka partitions.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 19 — Review security controls

**Procedure:** Inspect least privilege, TLS/SASL, KafkaUser, NetworkPolicy and Secret handling.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

### Lab 20 — Complete production readiness

**Procedure:** Capture risk register, synthetic smoke, rollback plan and independent review.

**Expected evidence:** Exact Strimzi/Kafka/Kubernetes versions, UTC command, Kubernetes context, desired/observed node-pool state, zone and PVC map, ISR/minISR, client SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Node drain, controller loss, broker failure and PVC resize are tabletop without approved disposable infrastructure.

## 11. Read-only verification script

Save as `verify-ch67.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] Nodes and zones'; kubectl get nodes -L topology.kubernetes.io/zone
echo '[3/9] Kafka and node pools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/9] Pods'; kubectl -n "$NS" get pods -o wide
echo '[5/9] PVC'; kubectl -n "$NS" get pvc -o wide
echo '[6/9] StorageClasses'; kubectl get storageclass
echo '[7/9] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[8/9] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[9/9] CRD'; kubectl explain kafkanodepool.spec
echo 'PASS: read-only Kubernetes inventory only.'
echo 'NOT PROVEN: quorum, ISR, storage throughput, rolling safety or independent review.'
```

Run `chmod +x verify-ch67.sh && ./verify-ch67.sh | tee evidence-ch67/preflight.txt`. Successful inventory does not certify availability or production readiness.

## 12. Twelve troubleshooting scenarios

### Scenario 1 — KafkaNodePool Pods remain Pending

**Diagnosis:** Inspect PVC zone binding, taints, affinity, quotas and insufficient node resources. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 2 — Broker Pods evicted

**Diagnosis:** Inspect ephemeral storage, memory pressure, QoS and node eviction events. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 3 — PVC cannot attach after reschedule

**Diagnosis:** Inspect zone mismatch, multi-attach, access mode and volume attachment. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 4 — Disk usage uneven across brokers

**Diagnosis:** Inspect partition placement, retention, skew and reassignment planning. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 5 — Broker disk latency rises

**Diagnosis:** Inspect cloud volume limits, compaction, page cache and throttling. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 6 — Controller quorum loses majority

**Diagnosis:** Stop unsafe maintenance; inspect controller Pods, PVCs, network and quorum. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 7 — Rollout blocked by minISR

**Diagnosis:** Inspect under-replicated partitions, broker availability and durability thresholds. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 8 — Rack awareness misconfigured

**Diagnosis:** Inspect node labels, broker rack config and replica assignments. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 9 — PodDisruptionBudget prevents drain

**Diagnosis:** Inspect allowed disruptions and health; never bypass without approval. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 10 — PVC expansion does not grow filesystem

**Diagnosis:** Inspect StorageClass expansion support, events, filesystem resize and operator procedure. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 11 — Broker count increased but hot partitions remain

**Diagnosis:** Inspect partition leadership and reassignment, not just Pod count. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

### Scenario 12 — GitOps repeatedly reverts manual changes

**Diagnosis:** Inspect source-of-truth CR, operator ownership and sync policy. Correlate Kafka/Strimzi CR status, Pod events, node labels, PVC/PV zones, broker ISR, controller quorum, disk I/O and client latency. **Response:** Stop unsafe maintenance, protect quorum and data, follow approved change/recovery, and reconcile client smoke. **Evidence:** UTC timeline, exact versions, expected/observed behavior, abort/rollback and reviewer.

## 13. Eight production runbooks

### Runbook A — Pending node pool Pods

**Trigger/response:** Inspect scheduling, PVC, affinity, quota and capacity before modifying desired state. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook B — Storage pressure and expansion

**Trigger/response:** Assess disk usage, IOPS, supported expansion, recovery and rollback. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook C — KRaft controller availability

**Trigger/response:** Protect quorum, stop rolling changes, inspect controller roles and escalate. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook D — Broker maintenance and rolling restart

**Trigger/response:** Verify ISR/minISR, one-at-a-time roll, Kafka health and abort. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook E — Node drain and zone loss

**Trigger/response:** Check PDB, PVC zone attachment, broker availability and fault domains. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook F — Capacity and hot partition incident

**Trigger/response:** Assess broker CPU, disk, leader skew and controlled reassignment. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook G — GitOps/Strimzi drift

**Trigger/response:** Review CRs, operator reconciliation, desired state and approved change. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

### Runbook H — Independent production acceptance

**Trigger/response:** Verify KRaft quorum, ISR, PVC, TLS/ACL, client smoke, SLO and signoff. **No-go:** controller majority unavailable, minISR at risk, unknown PVC data integrity, unreviewed node-pool deletion or unsupported storage change. **Exit:** Healthy KRaft quorum, broker/partition ISR, scheduled Pods, safe PVC state, restored client SLO, RCA and independent approval.

## 14. Capacity and availability acceptance matrix

| Signal | Required review | Typical risk |
|---|---|---|
| KRaft controller voter availability | majority across failure domains | metadata outage |
| Broker ISR/minISR | durability under one broker/zone loss | produce unavailability |
| PVC zone and attachment | Pod placement and storage binding | Pending broker |
| Disk latency/IOPS | peak ingest, replication and recovery | fetch/produce latency |
| CPU/memory/page cache | broker and controller sizing | throttling/OOM |
| Node pool rack spread | replica and controller placement | correlated outage |
| PDB allowed disruptions | maintenance feasibility | drain deadlock |
| Partition/leader skew | per-broker disk/network and traffic | hot broker |
| GitOps/Strimzi desired state | operator reconciliation | drift and surprise roll |
| Client synthetic smoke | produce/consume with approved TLS/SASL | hidden application outage |

## 15. Evidence package

```text
evidence-ch67/
  approved-charter-version-matrix.md
  preflight.txt
  kraft-quorum-inventory.md
  broker-nodepool-role-capacity.md
  crd-schema.md
  node-affinity-taint-toleration.md
  zone-topology-spread.md
  rack-awareness.md
  pvc-pv-binding.md
  disk-throughput-iops-baseline.md
  pvc-expansion-plan.md
  jbod-design-review.md
  broker-cpu-heap-pagecache.md
  controller-capacity.md
  scaling-reassignment-plan.md
  pdb-maintenance-plan.md
  node-drain-zone-loss-tabletop.md
  autoscaling-boundaries.md
  tls-sasl-acl-networkpolicy.md
  independent-production-readiness.md
  scorecard.md
```

Each artifact needs exact versions, UTC timestamp, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, owner, abort/rollback and reviewer.

## 16. 100-point node-pool operations assessment

| Domain | Points | Critical |
|---|---:|---|
| KafkaNodePool roles and KRaft quorum | 20 | Yes |
| Scheduling, rack awareness and failure domains | 20 | Yes |
| PVC, disk performance, expansion and storage safety | 20 | Yes |
| Capacity, scaling and partition reassignment | 15 | Yes |
| PDB, maintenance and node/zone recovery | 10 | Yes |
| TLS/SASL, GitOps, runbooks and client SLO | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced. **Automatic Fail:** fabricated live validation, unreviewed controller loss, deleted production PVC, unsafe ISR/minISR, unsupported rollback assumption, secret exposure or absent independent review.

## 17. References and next chapter

**References:** [Strimzi Documentation](https://strimzi.io/documentation/), [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Kubernetes Storage](https://kubernetes.io/docs/concepts/storage/), [Kubernetes Scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/).

**Next:** Chapter 068 — Strimzi Kafka Security, Network Policies, TLS, Authentication and Multi-Tenant Isolation.

---

**Verification boundary:** Chapter published; live node-pool scheduling, storage/rolling operations, controller failover and independent technical/security review remain Pending.
