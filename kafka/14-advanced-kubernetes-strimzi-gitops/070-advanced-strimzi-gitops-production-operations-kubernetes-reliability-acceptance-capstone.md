# Chapter 070 — Advanced Strimzi GitOps Production Operations and Kubernetes Reliability Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 14 — Advanced Kubernetes, Strimzi and GitOps (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft + Argo CD or Flux  
**Prerequisites:** Chapters 001–069, especially 066–069  
**Status:** Published · **Live integrated labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Default Pod failures, KRaft controller loss, ISR degradation, PVC pressure, operator upgrade, GitOps drift/prune and rollback drills to **tabletop**. Perform live fault injection only in an explicitly approved disposable cluster with synthetic data. Never delete production PVCs, reset Kafka metadata, bypass TLS/ACL or enable unreviewed automatic pruning. A Git revert is not a Kafka data rollback.

## 1. Capstone mission and acceptance contract

Integrate Strimzi operator architecture, KafkaNodePool scheduling/storage, KRaft availability, TLS/ACL and tenant isolation, GitOps progressive delivery and policy-as-code into a single production-readiness acceptance exercise.

**Learning outcomes:** establish a version-pinned source of truth, validate operator/CRD reconciliation, prove Kafka durability and authenticated client behavior, rehearse failure response, evaluate irreversible changes, measure SLO/RTO, and obtain independent platform/SRE/security signoff.

## 2. Enterprise reference architecture

```text
                 Approved Git revision
                  /              \
          CI policy tests       security review
                  \              /
                 Argo CD or Flux
                        |
                Strimzi CR desired state
          Kafka / KafkaNodePool / KafkaTopic / KafkaUser
                        |
                 Strimzi Operators
                 /             \
         KRaft controllers     Kafka brokers
           metadata quorum    partition ISR
                |                 |
             durable PVC      durable PVC
                \                 /
            Kubernetes scheduler/CNI
                        |
               TLS/SASL Kafka clients
                        |
             SLO, audit and event ledger
                        |
             SRE incident + RCA + review
```

**Ownership:** GitOps owns reviewed Strimzi custom resources. Strimzi owns generated broker/controller workloads and operator-managed Secrets. Kubernetes owns Pod placement and storage binding. Kafka owns partition/metadata state. These layers have distinct health checks and rollback limits.

## 3. Acceptance gates

| Gate | Evidence required | No-go condition |
|---|---|---|
| Version compatibility | pinned Kafka/Strimzi/K8s/GitOps matrix | unsupported CRD/operator |
| Git provenance | signed/reviewed commit, rendered diff | unreviewed change |
| KRaft quorum | healthy controller voter majority | quorum degraded |
| Broker durability | ISR/minISR, URP and disk headroom | unsafe replication |
| Node placement | zones, rack awareness, PDB and PVC | correlated failure risk |
| TLS and auth | cert trust, KafkaUser ACL, synthetic smoke | plaintext/broad access |
| Tenant isolation | negative tests and NetworkPolicy | unauthorized access |
| GitOps safety | sync order, drift, prune protection | data deletion risk |
| Client correctness | synthetic input/output event ledger | missing/duplicate events |
| Recovery | measured or explicitly tabletop RTO/RPO | unsupported claims |
| Independent review | SRE/platform/security/business approvals | unsigned acceptance |

A green GitOps dashboard, Ready Kafka CR or healthy Pod is not proof of end-to-end Kafka client correctness.

## 4. Version and change control

Record Kafka and Strimzi versions, Kubernetes API/CRD versions, Argo CD/Flux versions, KRaft quorum configuration, StorageClass, CNI, KafkaNodePool roles, image digests, Git commit and operator release notes. Validate all examples against the **installed** Strimzi CRD schema.

Changes are classified:

- **Manifest-only and reversible** where reconciliation effects are understood.
- **Operator-managed rolling** changes that require quorum/ISR/client SLO gates.
- **Security-sensitive** changes to listeners, KafkaUser, Secrets or NetworkPolicy.
- **Potentially irreversible** Kafka metadata/storage/partition changes that require restore/fallback rather than assuming Git revert.

## 5. Kubernetes-first read-only baseline

```bash
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
kubectl get deploy -A | grep -i strimzi
kubectl -n kafka-lab get kafka,kafkanodepool,kafkatopic,kafkauser -o wide
kubectl -n kafka-lab get pods,pvc,svc,networkpolicy -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl explain kafka.spec
kubectl explain kafkanodepool.spec
```

Redact user-specific secrets and sensitive metadata from shared evidence. If the operator or cluster is absent, mark **NOT INSTALLED**, not a successful health check.

## 6. GitOps release design

```text
kafka-platform/
  operator/
  base/
    kafka/
    nodepools/
    topics/
    users/
    networkpolicy/
  overlays/
    lab/
    staging/
    production/
  gitops/
    argocd/
    flux/
  policies/
  tests/
    schema/
    client-smoke/
    security-negative/
  evidence/
    ch070/
```

Select **one** GitOps controller as the owner of each resource set. Sequence CRD/operator readiness before Kafka/KafkaNodePool, then KafkaTopic/KafkaUser, then client smoke. Require environment-specific approval and protection against destructive pruning.

## 7. Kafka health is a release gate

A Kafka release acceptance requires evidence for:

- KRaft controller quorum and metadata health.
- Broker count, partition leaders, replication factor and ISR/minISR.
- Under-replicated/offline partitions and storage I/O/headroom.
- KafkaNodePool Pod placement, PVC attachment and fault-domain spread.
- TLS/SASL client authentication, KafkaUser ACL and NetworkPolicy.
- Synthetic producer/consumer correctness, lag and latency against business SLO.
- GitOps/Strimzi reconciliation status and audit trail.

Use actual workload baselines and approved thresholds, not universal numbers. Do not perform live production disruptions to establish these baselines.

## 8. Safe progressive delivery

1. Create signed/reviewed PR with manifest diff, schema/policy/secret scans and risk classification.
2. Apply in disposable lab; inspect operator and Kafka health.
3. Promote identical versioned artifacts to staging and run synthetic client smoke.
4. Obtain security, platform and SRE approval for production.
5. Verify pre-change quorum/ISR/PVC/client SLO and maintenance window.
6. Reconcile only approved resources with destructive prune disabled or separately approved.
7. Monitor KRaft, broker ISR, disk, TLS/auth, client correctness and latency.
8. Abort on loss of quorum, unsafe ISR, unexplained event gaps, exposure or SLO breach.
9. Reconcile post-change evidence and obtain signoff.

## 9. Fault and recovery acceptance matrix

| Fault | Expected engineering response | Evidence |
|---|---|---|
| Broker Pod loss | ISR and leader recovery within approved budget | partition/lag timeline |
| Controller voter loss | quorum retains majority or recovery escalates | voter state and timestamps |
| Zone outage | controller and broker fault-domain tolerance | placement/PVC map |
| Disk pressure | throttle/alerts and safe capacity response | disk IOPS and latency |
| GitOps drift | source of truth restored without generated-resource conflict | Git revision/diff |
| Unsafe prune | halt before deletion and preserve PVC/data | controller audit |
| TLS/ACL regression | contain, restore least privilege and client smoke | auth/denial ledger |
| Operator upgrade incompatibility | freeze rollout, inspect CRD/version matrix | rollback/recovery plan |
| Client correctness gap | incident until event-ID reconciliation | expected/observed IDs |

The matrix is a **test plan**, not a claim of executed fault injection.

## 10. Twenty integrated Kubernetes-first capstone labs

### Lab 01 — Approve capstone charter

**Procedure:** Define Kafka availability/correctness SLO, RPO/RTO, tenant scope, owners and fault safety.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 02 — Inventory pinned versions

**Procedure:** Capture Kafka/Strimzi/Kubernetes, KRaft, Argo/Flux, CNI, storage, CRDs and image digests.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 03 — Review GitOps provenance

**Procedure:** Validate signed PR/revision, branch protection, rendering and admission checks.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 04 — Audit resource ownership

**Procedure:** Map Git-owned CRs to Strimzi-managed broker/controller resources and PVCs.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 05 — Validate CRD/operator sync ordering

**Procedure:** Check release matrix, CRD readiness, operator health and Kafka reconcile conditions.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 06 — Validate KRaft quorum and ISR

**Procedure:** Review controllers, broker RF/minISR, under-replicated partitions and abort gates.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 07 — Audit KafkaNodePool placement

**Procedure:** Review controller/broker roles, zone/rack topology, anti-affinity and PDB.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 08 — Audit storage and capacity

**Procedure:** Review PVC zone binding, IOPS, throughput, disk growth, page cache and restore budget.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 09 — Validate TLS/SASL/KafkaUser

**Procedure:** Review listener exposure, cert trust, ACL least privilege and rotation plan.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 10 — Validate NetworkPolicy/RBAC

**Procedure:** Review namespace isolation, ingress/egress, DNS and operator permissions.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 11 — Validate policy-as-code

**Procedure:** Exercise synthetic safe/unsafe Kafka CR, KafkaUser and PVC changes in review.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 12 — Validate Argo/Flux health

**Procedure:** Inspect sync status, source revision, reconciliation drift and safe prune settings.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 13 — Measure client SLO baseline

**Procedure:** Capture synthetic TLS produce/consume latency, success, lag and error budget.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 14 — Review progressive promotion

**Procedure:** Check lab/staging/prod gates, manual approval, immutable revision and rollback.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 15 — Model broker Pod disruption

**Procedure:** Tabletop ISR/minISR, task/partition leadership, PDB and SLO recovery.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 16 — Model controller loss

**Procedure:** Tabletop KRaft majority, zone failure, quorum recovery and unsafe actions.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 17 — Model storage pressure

**Procedure:** Tabletop PVC expansion, disk IOPS throttling, leader movement and abort.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 18 — Model GitOps drift/unsafe prune

**Procedure:** Tabletop CR drift, generated resource ownership and deletion protection.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 19 — Review incident response

**Procedure:** Rehearse on-call roles, alerts, communications, escalation, rollback and RCA.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

### Lab 20 — Independent acceptance

**Procedure:** Reconcile evidence, critical gates, score, owner signoff and remediation backlog.

**Expected evidence:** Exact Kafka/Strimzi/Kubernetes/GitOps versions, UTC timestamp, Git revision, Kubernetes context, expected/observed Kafka quorum/ISR, storage, security, synthetic client event IDs, SLO, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Any disruptive step remains **Tabletop** without approved disposable infrastructure.

## 11. Read-only verification script

Save as `verify-ch70.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/11] Context'; kubectl config current-context
echo '[2/11] Nodes/zones'; kubectl get nodes -L topology.kubernetes.io/zone
echo '[3/11] CRDs'; kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
echo '[4/11] Operator'; kubectl get deploy -A | grep -i strimzi || true
echo '[5/11] Kafka/node pools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[6/11] Topics/user metadata'; kubectl -n "$NS" get kafkatopic,kafkauser -o wide
echo '[7/11] Pods'; kubectl -n "$NS" get pods -o wide
echo '[8/11] PVC'; kubectl -n "$NS" get pvc -o wide
echo '[9/11] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[10/11] GitOps controllers'
if kubectl get crd applications.argoproj.io >/dev/null 2>&1; then kubectl get applications.argoproj.io -A; else echo 'Argo CD CRD not installed'; fi
if kubectl get crd kustomizations.kustomize.toolkit.fluxcd.io >/dev/null 2>&1; then kubectl get kustomizations.kustomize.toolkit.fluxcd.io -A; else echo 'Flux CRD not installed'; fi
echo '[11/11] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only inventory only.'
echo 'NOT PROVEN: Kafka quorum, authenticated smoke, RTO, security or independent acceptance.'
```

Run `chmod +x verify-ch70.sh && ./verify-ch70.sh | tee evidence-ch70/preflight.txt`. Inventory success does **not** certify readiness.

## 12. Twelve troubleshooting scenarios

### Scenario 1 — Operator reports NotReady after sync

**Diagnosis:** Inspect CRD/schema, operator logs, Kafka CR conditions, PVC and KafkaNodePool placement. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 2 — KRaft controller majority unavailable

**Diagnosis:** Stop rolling changes; assess voter placement, network and durable controller disks. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 3 — Broker under-replicated during roll

**Diagnosis:** Check minISR, partition leaders, disk/network and maintenance abort. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 4 — KafkaNodePool Pod Pending

**Diagnosis:** Inspect node taints, affinity, quota, PVC zone and capacity. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 5 — Disk I/O throttling breaks client SLO

**Diagnosis:** Correlate PVC limits, Kafka request latency, ISR catch-up and page cache. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 6 — Argo/Flux Healthy but Kafka unreachable

**Diagnosis:** Check advertised endpoints, TLS/SASL, ACL, NetworkPolicy and authenticated smoke. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 7 — GitOps tries to prune Kafka resources

**Diagnosis:** Freeze reconciliation, preserve PVC and audit resource ownership. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 8 — Operator reconciles manual patch away

**Diagnosis:** Review source CR, managed fields, desired state and Git revision. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 9 — Certificate rotation causes outage

**Diagnosis:** Inspect CA trust, SAN, Secret revision, listener and client rollout order. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 10 — Tenant cross-access unexpectedly succeeds

**Diagnosis:** Declare security incident, contain principal, inspect ACL and preserve audit. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 11 — Rolling upgrade cannot be reverted

**Diagnosis:** Assess Kafka metadata/CRD compatibility, recovery plan and data safety. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

### Scenario 12 — SLO dashboard green but event integrity fails

**Diagnosis:** Inspect committed input/output IDs, producer acknowledgments and consumer lag. Correlate UTC timeline, Git revision, CRD/operator reconciliation, Kafka KRaft quorum, ISR/minISR, PVC, TLS/ACL, Pod events and synthetic client SLO. **Response:** Freeze unsafe change/prune, preserve data, follow reviewed recovery, and reconcile expected vs observed client event IDs. **Exit:** Measured or explicitly tabletop recovery, remediation owner, RCA and independent reviewer.

## 13. Eight production runbooks

### Runbook A — Strimzi/Kafka reconciliation incident

**Trigger/response:** Correlate Git revision, CRD/operator status, KafkaNodePool, events and rollback. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook B — KRaft controller quorum recovery

**Trigger/response:** Protect controller voter majority, disks and approved recovery procedure. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook C — Broker ISR and client availability

**Trigger/response:** Review RF/minISR, partition leaders, rolling state and producer/consumer smoke. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook D — Storage and scheduling failure

**Trigger/response:** Review PVC zone binding, disk I/O, affinity, eviction and node replacement. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook E — TLS/ACL/tenant isolation incident

**Trigger/response:** Inspect principal, listener, NetworkPolicy, KafkaUser and security escalation. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook F — GitOps drift/prune emergency

**Trigger/response:** Freeze unsafe sync, audit resource ownership, preserve state and restore reviewed CRs. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook G — Production release rollback

**Trigger/response:** Classify reversible CR change vs irreversible Kafka state; apply approved recovery. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

### Runbook H — Enterprise readiness and RCA

**Trigger/response:** Reconcile event IDs, measured SLO/RTO, evidence, critical gates and signoff. **No-go:** controller majority lost, ISR below approved threshold, unreviewed PVC deletion, unsafe GitOps prune, credential exposure, unknown data correctness or unsupported rollback. **Exit:** Healthy Kafka/Strimzi/GitOps, authenticated client correctness, signed RCA and independent approval.

## 14. Evidence bundle

```text
evidence-ch70/
  capstone-charter-raci-slo.md
  pinned-version-and-provenance.md
  gitops-pr-policy-review.md
  ownership-map.md
  crd-operator-sync-order.md
  kraft-quorum-isr.md
  nodepool-zone-pdb.md
  pvc-disk-iops-capacity.md
  tls-sasl-kafkauser.md
  networkpolicy-rbac.md
  policy-negative-tests.md
  argocd-flux-sync-status.md
  synthetic-client-slo-baseline.md
  staged-promotion.md
  broker-pod-loss-tabletop.md
  controller-voter-loss-tabletop.md
  storage-pressure-tabletop.md
  unsafe-prune-drift-tabletop.md
  incident-communications-rca.md
  independent-sre-platform-security-business-signoff.md
  scorecard.md
```

Each artifact needs exact versions, UTC time, Git revision, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, owner, abort/rollback and independent reviewer.

## 15. 100-point enterprise reliability assessment

| Domain | Points | Critical |
|---|---:|---|
| Versioned GitOps provenance, policy and ownership | 15 | Yes |
| KRaft quorum, broker ISR and availability | 20 | Yes |
| KafkaNodePool scheduling, PVC, capacity and failure domains | 15 | Yes |
| TLS/SASL, ACL, NetworkPolicy and tenant isolation | 15 | Yes |
| Progressive release, drift/prune protection and rollback | 15 | Yes |
| Synthetic client SLO, correctness and incident response | 15 | Yes |
| Independent technical/security acceptance | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced, including representative live tests. **Automatic Fail:** fabricated live evidence, unreviewed data deletion, missing quorum/ISR safety, credential leak, unauthorized tenant access, unsupported rollback assumption or absent independent approval.

**Current readiness:** **Pending / Not Ready** until live integrated exercises, client event reconciliation, RTO/RPO measurements and independent review are completed.

## 16. References and transition

**References:** [Strimzi Documentation](https://strimzi.io/documentation/), [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/), [Argo CD](https://argo-cd.readthedocs.io/), [Flux](https://fluxcd.io/flux/).

**Part 14 — Advanced Kubernetes, Strimzi and GitOps is fully published (066–070).**

**Next:** Chapter 071 — Amazon MSK Architecture, Networking, IAM and Production Administration, beginning Part 15 — Amazon MSK and AWS Kafka Operations.

---

**Verification boundary:** Publication proves document availability only. Live fault injection, measured Kafka SLO/RTO, client correctness and independent technical/security review remain Pending.
