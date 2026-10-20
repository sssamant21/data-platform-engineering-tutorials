# Chapter 066 — Advanced Kafka on Kubernetes: Strimzi Operator Architecture, KRaft and GitOps Foundations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 14 — Advanced Kubernetes, Strimzi and GitOps (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–065; Kubernetes RBAC, GitOps and Kafka operations  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use a disposable namespace/cluster, synthetic topics and an approved operator/Kafka version matrix. Do not install or upgrade an operator, edit KRaft controller membership, delete PVCs, mutate production Kafka CRs, or enable external listeners without reviewed change control. This chapter is a design and lab guide, not evidence of a tested deployment.

## 1. Mission and learning objectives

Understand how Strimzi reconciles Kubernetes custom resources into a KRaft-based Kafka cluster, how KafkaNodePools and operators divide responsibilities, and how to manage desired state through GitOps safely. By the end, readers can identify the CRD/Operator/Cluster boundary, design failure domains, review reconciliation drift, plan rolling changes and construct a gated GitOps promotion workflow.

## 2. Control plane architecture

```text
Git repository (reviewed desired state)
                 |
        Argo CD / Flux controller
                 |
       Kafka / KafkaNodePool CRs
                 |
       Strimzi Cluster Operator
                 |
  +--------------+-----------------+
  |              |                 |
KRaft         Kafka broker     Services, Secrets,
controllers   node pools       PVCs, ConfigMaps
  |              |
  +---- Kafka metadata quorum ----+
                 |
       KafkaTopic / KafkaUser
                 |
       Topic Operator / User Operator
                 |
     producers, consumers, Streams,
         Kafka Connect and clients
```

**Ownership:** GitOps owns reviewed Strimzi custom resources; Strimzi owns generated workloads and dependent resources. Avoid having Argo CD/Flux directly overwrite operator-generated broker/controller Pods or workload controllers.

## 3. Strimzi component boundaries

| Component | Primary responsibility | SRE failure signal |
|---|---|---|
| Cluster Operator | Kafka/KafkaNodePool reconciliation | NotReady, reconcile errors |
| Topic Operator | KafkaTopic lifecycle where configured | topic drift, ACL/config errors |
| User Operator | KafkaUser authentication/authorization | missing Secret, ACL/auth failure |
| Kafka CR | desired Kafka cluster/listeners/config | invalid schema or NotReady |
| KafkaNodePool CR | controller/broker roles, replicas, storage | Pending Pods, PVC/placement |
| KRaft controllers | metadata quorum | controller loss, quorum risk |
| Brokers | partition leaders, logs, ISR | under-replication, disk/CPU pressure |
| GitOps controller | desired state delivery and drift | sync failure, unsafe pruning |

Confirm exact resource API versions, operator components and supported Kafka versions from the **installed Strimzi release**. Do not assume a particular version's CRD fields are universal.

## 4. KRaft and node-pool design

KRaft controllers form a metadata quorum. Broker nodes serve producers/consumers and partition data. Strimzi KafkaNodePools express node roles, replica counts, storage and scheduling for supported releases. Separate controller and broker pools where appropriate for scale and fault isolation; test topology against Kubernetes node/zone capacity.

- Design controller quorum as an odd number where practical; losing a majority prevents metadata progress.
- Place controllers across independent failure domains with stable durable storage.
- Ensure broker replicas and minISR allow the intended maintenance/failure budget.
- Review zone-aware placement, anti-affinity, PDB, rack awareness and disk IOPS.
- Do not assume broker Pod Ready implies healthy quorum or partition durability.

## 5. Kubernetes read-only inventory

```bash
kubectl config current-context
kubectl get ns
kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
kubectl get deploy -A | grep -i strimzi
kubectl -n kafka-lab get kafka,kafkanodepool,pods,svc,pvc -o wide
kubectl -n kafka-lab get kafka -o yaml
kubectl -n kafka-lab get kafkanodepool -o yaml
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl explain kafka.spec
kubectl explain kafkanodepool.spec
```

Treat YAML as sensitive: redaction may be required before sharing. If the cluster or operator is absent, record **NOT INSTALLED**, not a pass.

## 6. GitOps repository design

```text
kafka-platform/
  operator/
    README.md
    version-matrix.md
    crds/
    release/
  base/
    kafka/
    nodepools/
    topics/
    users/
    networkpolicy/
    monitoring/
  overlays/
    lab/
    staging/
    production/
  policies/
    kafka-cr-validation.md
    admission-security.md
  tests/
    kafka-smoke/
    k8s-inventory/
  evidence/
    acceptance-template.md
```

Recommended delivery order: approved CRDs/operator installation first, operator readiness second, Kafka/KafkaNodePool desired state third, KafkaTopic/KafkaUser fourth, smoke/monitoring last. The actual sync waves or Flux dependencies must match the installed controller and release.

## 7. GitOps review and dry-run examples

```bash
# Read-only validation and review before sync
kubectl config current-context
kubectl api-resources | grep -E 'kafka|Kafka'
kubectl explain kafka.spec
kubectl explain kafkanodepool.spec
git diff --check
git status --short
# After rendering overlays, validate against the target API server:
kubectl apply --dry-run=server -f rendered-lab.yaml
```

`rendered-lab.yaml` is an output of an approved Kustomize/Helm pipeline, not a file provided by this chapter. Server dry-run validates schema/admission only; it does **not** prove Kafka health, storage performance, TLS correctness or data safety.

## 8. Reference KafkaNodePool manifests

The following illustrates the concept for Strimzi releases supporting `strimzi.io/v1`; **validate installed CRDs** before applying.

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
```

These are **templates**, not deployable cluster guarantees. Pair them with a release-compatible Kafka CR, listener/TLS/SASL, resource limits, StorageClass, rack/zone placement and approved security policy. PVC persistence does not replace tested backup/DR.

## 9. Reconciliation, upgrades and rollback

- **Reconciliation:** GitOps changes a Kafka CR; the Strimzi operator translates it into managed resources and status. Check desired vs observed generation, conditions, events and broker health.
- **Drift:** If an engineer patches a generated resource directly, the operator may overwrite it. Fix the declarative source of truth instead.
- **Rolling changes:** Confirm controller quorum, ISR/minISR, available disk, maintenance approval and rollback/abort before operator-managed restarts.
- **Operator upgrades:** Check Kubernetes/Strimzi/Kafka compatibility, CRD schema evolution, release notes and supported migration order.
- **Kafka upgrades:** Some metadata/protocol/storage changes are not trivially reversible. Define restore/fallback strategy rather than assuming `git revert` reverses broker state.

## 10. Twenty Kubernetes-first foundation labs

### Lab 01 — Approve platform charter

**Procedure:** Define owner, scope, supported Kafka/Strimzi/Kubernetes versions, RTO/RPO, security and abort criteria.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 02 — Confirm kubectl context

**Procedure:** Verify current context, namespaces, RBAC and no production mutation.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 03 — Inventory operator release

**Procedure:** Inspect Strimzi Deployment, version, image digest, watch namespaces and CRDs.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 04 — Inspect Strimzi reconciliation

**Procedure:** Map Kafka CR desired state to operator logs, status conditions and broker/controller Pods.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 05 — Inspect KRaft controllers

**Procedure:** Review quorum voter roles, controller Pod topology, health and storage.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 06 — Inspect KafkaNodePools

**Procedure:** Map node pool roles, replica counts, PVC templates, resources and scheduling.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 07 — Review Kafka CR schema

**Procedure:** Use kubectl explain and server-side dry-run to validate installed CRD version.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 08 — Review KafkaTopic lifecycle

**Procedure:** Inspect Topic Operator ownership, topic RF/partitions and change constraints.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 09 — Review KafkaUser lifecycle

**Procedure:** Inspect User Operator authentication, ACL scope and Secret management.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 10 — Inspect listeners

**Procedure:** Map internal/external bootstrap, TLS, SASL and network exposure.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 11 — Review storage and PVC safety

**Procedure:** Inspect StorageClass, expansion support, volume binding, node pools and retention.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 12 — Review resource sizing

**Procedure:** Assess CPU, heap, page cache, disk IOPS and broker/controller isolation.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 13 — Review rack and topology

**Procedure:** Inspect zone labels, rack awareness, anti-affinity and failure domains.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 14 — Create GitOps repo skeleton

**Procedure:** Design base/overlays and approved environments with pinned operator/CRDs.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 15 — Review Argo CD/Flux sync ordering

**Procedure:** Plan operator CRDs first, operator second, Kafka/KafkaNodePool resources third.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 16 — Review policy gates

**Procedure:** Plan schema, security, resource, TLS, image and immutable provenance checks.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 17 — Review drift and ownership

**Procedure:** Distinguish Strimzi-managed generated workloads from Git-owned custom resources.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 18 — Review rolling operations

**Procedure:** Map operator-managed changes, readiness, ISR/minISR and safe maintenance windows.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 19 — Review upgrade rollback

**Procedure:** Assess CRD compatibility, Kafka metadata/version migration and backup/restore limits.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

### Lab 20 — Complete foundation acceptance

**Procedure:** Produce change diff, inventory, topology, evidence, risks and independent review.

**Evidence:** Capture exact Kafka/Strimzi/Kubernetes versions, UTC command, Git revision, desired/observed resources, Kafka quorum/ISR, ACL/TLS, storage and failure domains, owner, rollback/abort and independent reviewer. Mark **Pending** until executed. Operator install, upgrade and fault injection require approved isolated infrastructure.

## 11. Read-only verification script

Save as `verify-ch66.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] Strimzi operator'; kubectl get deploy -A | grep -i strimzi || true
echo '[3/9] CRDs'; kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
echo '[4/9] Kafka and node pools'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[5/9] Pods'; kubectl -n "$NS" get pods -o wide
echo '[6/9] PVCs'; kubectl -n "$NS" get pvc -o wide
echo '[7/9] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[8/9] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[9/9] Installed schema'; kubectl explain kafka.spec
echo 'PASS: read-only Kubernetes inventory only.'
echo 'NOT PROVEN: GitOps reconciliation, KRaft quorum, TLS, broker availability or independent review.'
```

Run `chmod +x verify-ch66.sh && ./verify-ch66.sh | tee evidence-ch66/preflight.txt`. A successful inventory is not an operational readiness test.

## 12. Twelve troubleshooting scenarios

### Scenario 1 — Kafka CR stuck NotReady

**Diagnosis:** Check status conditions, operator logs, PVC, storage, listener and resource conflicts. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 2 — KafkaNodePool Pods Pending

**Diagnosis:** Check quotas, PVC binding, affinity, taints, topology and node resources. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 3 — KRaft controller quorum degraded

**Diagnosis:** Check controller availability, network, disks and supported recovery procedures. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 4 — Operator reconciliation loop

**Diagnosis:** Inspect status, events, drift, unsupported fields and webhook/schema errors. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 5 — GitOps attempts to manage generated StatefulSets

**Diagnosis:** Review ownership boundaries and ignore rules; Git should own Strimzi CRs. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 6 — CRD mismatch after operator upgrade

**Diagnosis:** Check installed CRD schema, release compatibility and conversion/upgrade plan. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 7 — TLS listener fails

**Diagnosis:** Check Secret, cert trust, SAN, service DNS and KafkaUser auth. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 8 — External listener unexpectedly exposed

**Diagnosis:** Check load balancer/ingress, advertised addresses, network policy and approval. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 9 — PVC full during broker roll

**Diagnosis:** Check partition leadership, disk headroom, ISR and safe storage expansion. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 10 — KafkaTopic drift/partition change

**Diagnosis:** Inspect Topic Operator status, partition constraints and data ownership. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 11 — Rolling restart threatens minISR

**Diagnosis:** Check broker health, replication, controller quorum and abort gates. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

### Scenario 12 — GitOps sync reports Healthy but clients fail

**Diagnosis:** Check bootstrap connectivity, authentication, ACL, producer/consumer smoke and business SLO. Correlate Git revision, CRD schema, Strimzi reconciliation status, Kubernetes events, Kafka quorum/ISR, PVC, listener and client errors. **Response:** Freeze unsafe GitOps prune/changes, protect data and quorum, follow approved remediation and verify client smoke. **Evidence:** UTC timeline, desired/observed diff, security, rollback and reviewer.

## 13. Eight production runbooks

### Runbook A — Operator and CRD health

**Trigger/response:** Check operator Pod, logs, watched namespaces, installed CRDs and status. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook B — KRaft controller quorum incident

**Trigger/response:** Check quorum, controller Pods, PVC and authorized recovery. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook C — KafkaNodePool scheduling and storage

**Trigger/response:** Review node pool role, PVC, taints, quotas, affinity and disk. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook D — Listener/TLS/KafkaUser outage

**Trigger/response:** Review listener endpoints, cert trust, SASL, ACL and NetworkPolicy. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook E — GitOps drift and failed sync

**Trigger/response:** Inspect source revision, sync order, CR ownership, diff and revert. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook F — Operator-managed rolling change

**Trigger/response:** Confirm ISR/minISR, controller quorum, maintenance approval and abort criteria. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook G — Strimzi/Kafka upgrade rollback

**Trigger/response:** Validate compatibility, backup, CRD, Kafka metadata and reversibility. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

### Runbook H — Independent platform acceptance

**Trigger/response:** Reconcile health, smoke, durability, security, SLO and signoff. **Abort/no-go:** lost controller quorum, ISR below approved durability budget, unreviewed PVC deletion, unsafe CRD upgrade, exposed listener or GitOps prune of operator-managed data. **Exit:** Reconciled desired state, healthy KRaft/brokers, bounded client latency, signed RCA and independent approval.

## 14. Evidence package

```text
evidence-ch66/
  charter-raci-version-matrix.md
  kubectl-context-rbac.md
  strimzi-operator-release-crds.md
  operator-reconciliation-status.md
  kraft-controller-quorum.md
  nodepool-roles-placement.md
  installed-crd-schema.md
  kafkatopic-lifecycle.md
  kafkauser-acl-secret-review.md
  listener-tls-sasl-network.md
  pvc-storageclass-expansion.md
  cpu-memory-disk-sizing.md
  rack-zone-topology.md
  gitops-repo-layout.md
  argocd-flux-sync-order.md
  policy-gates.md
  drift-ownership.md
  rolling-operations.md
  upgrade-rollback-plan.md
  kafka-client-smoke.md
  independent-technical-security-review.md
  readiness-scorecard.md
```

Each artifact requires UTC timestamp, exact versions, Git revision, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, owner, abort/rollback and independent reviewer.

## 15. 100-point Strimzi/GitOps foundation assessment

| Domain | Points | Critical |
|---|---:|---|
| Operator architecture, CRDs and reconciliation | 20 | Yes |
| KRaft quorum, node pools and durability | 20 | Yes |
| Kubernetes storage, placement and capacity | 15 | Yes |
| KafkaUser, listener, TLS/SASL and network security | 15 | Yes |
| GitOps source of truth, sync and drift | 15 | Yes |
| Upgrade/rollback, incident runbooks and evidence | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated live evidence, lost quorum due to unreviewed mutation, deleted production PVCs, unsupported rollback assumption, secret exposure, unsafe external listener or absent independent review.

## 16. References and next chapter

**References:** [Strimzi Documentation](https://strimzi.io/documentation/), [Apache Kafka Documentation](https://kafka.apache.org/documentation/), [Kubernetes Documentation](https://kubernetes.io/docs/), [Argo CD](https://argo-cd.readthedocs.io/), [Flux](https://fluxcd.io/flux/).

**Next:** Chapter 067 — Strimzi KafkaNodePools, Scheduling, Storage, Availability and Production Operations.

---

**Verification boundary:** Publication proves document availability only. Live operator installation, GitOps reconciliation, KRaft recovery, client smoke and independent security review remain Pending.
