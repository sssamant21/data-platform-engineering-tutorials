# Chapter 112 — Provision GKE, Networking, Storage and Strimzi KRaft

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (2/10)  
**Primary platform:** GKE Standard + Strimzi Kafka KRaft  
**Prerequisite:** Chapter 111  
**Publication:** Published; **live labs:** pending; **independent technical/security review:** pending.

> **Safety:** Only provision a disposable, approved GCP project with billing alerts and cleanup ownership. Pin a Strimzi/Kafka version pair from the official compatibility matrix. Commands are examples, not evidence of execution. Never apply placeholders, leak secrets, or delete shared PVCs.

## 1. Mission and outcomes

Provision a reproducible Kafka lab on GKE, including VPC/subnet/IP ranges, zone-aware Kubernetes scheduling, persistent storage, the Strimzi operator, separate KRaft controller/broker node pools, TLS clients, monitoring and safe teardown. Produce an architecture record, tested IaC, event-ID reconciliation and a cost report.

## 2. Architecture

```text
GCP project / VPC / regional GKE Standard
  ├─ approved private nodes and network egress
  ├─ Strimzi operator (pinned release)
  ├─ KafkaNodePool controllers: KRaft metadata quorum
  ├─ KafkaNodePool brokers: Kafka logs on CSI PVCs
  ├─ Kafka, KafkaTopic, KafkaUser CRs
  ├─ synthetic producer and idempotent consumer Pods
  └─ Prometheus/Grafana + Cloud Monitoring
```

A regional GKE control plane does not itself guarantee broker or controller zone separation. Inspect actual pod and PVC placement and plan capacity after one-zone failure.

## 3. Preflight: project, version, network and cost

```powershell
gcloud auth list
gcloud config get-value project
gcloud billing projects describe YOUR_PROJECT_ID
gcloud container clusters list --project YOUR_PROJECT_ID
kubectl config current-context
```

Record project, billing owner, region, quotas, GKE release channel, Strimzi release, Kafka version, node SKU, disk SKU, VPC and subnet. Budgets issue alerts but do not impose a hard spending cap. Plan GKE secondary ranges for Pods and Services, private control-plane access, DNS, Cloud NAT or approved egress, and Workload Identity Federation for GKE. Prefer reviewed Terraform for reproducible infrastructure.

## 4. Provision GKE Standard

**Illustrative only:** network/subnet must exist; verify current gcloud flags, regional node counts, authorized endpoint access and total charges before running.

```bash
gcloud container clusters create kafka-lab \
  --project YOUR_PROJECT_ID \
  --region us-central1 \
  --release-channel regular \
  --enable-ip-alias \
  --enable-private-nodes \
  --network kafka-lab-vpc \
  --subnetwork kafka-lab-subnet \
  --workload-pool YOUR_PROJECT_ID.svc.id.goog \
  --num-nodes 1
```

This is a **lab reference**, not a complete hardened production command. Confirm GKE Standard node pools, machine type, firewall, authorized control-plane access and per-zone capacity with platform owners. Retrieve credentials only for the approved cluster:

```powershell
gcloud container clusters get-credentials kafka-lab --region us-central1 --project YOUR_PROJECT_ID
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
```

## 5. Storage engineering

Use the supported GKE Persistent Disk CSI driver and a StorageClass appropriate to measured Kafka IOPS, throughput and latency. Verify zonal PV binding and reclaim behavior. Example disposable-lab StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: kafka-balanced-lab
provisioner: pd.csi.storage.gke.io
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Delete
parameters:
  type: pd-balanced
```

**Warning:** Delete reclaim policy may delete underlying disks when claims/PVs are removed. For production, choose an approved retention and backup policy; Kafka replication is not backup.

## 6. Strimzi and KRaft deployment

Install a pinned, supported Strimzi release using its version-specific official Helm chart or manifests. Record source, checksum and CRD compatibility. Verify the operator and CRDs before applying Kafka custom resources:

```powershell
kubectl get crd | Select-String kafka.strimzi.io
kubectl get deployments -n kafka
kubectl get pods -n kafka
kubectl get kafkanodepool -n kafka
```

The namespace must exist before installation. The following **version-sensitive reference** must be adapted to the installed CRD, selected Kafka version and security policy:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: controllers
  namespace: kafka
  labels:
    strimzi.io/cluster: gke-kafka
spec:
  replicas: 3
  roles: [controller]
  storage:
    type: persistent-claim
    size: 20Gi
    class: kafka-balanced-lab
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers
  namespace: kafka
  labels:
    strimzi.io/cluster: gke-kafka
spec:
  replicas: 3
  roles: [broker]
  storage:
    type: persistent-claim
    size: 100Gi
    class: kafka-balanced-lab
---
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: gke-kafka
  namespace: kafka
spec:
  kafka:
    version: REPLACE_WITH_SUPPORTED_KAFKA_VERSION
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

Depending on Strimzi release, additional annotations, fields or role constraints may be required. **Do not apply the placeholder version.** Verify CRDs and operator release notes; configure rack awareness, anti-affinity/topology spread, memory/CPU requests, security and monitoring before applying. Validate with `kubectl apply --dry-run=server -f gke-kafka.yaml` after replacing placeholders. A successful dry run does not prove quorum or zone resilience.

## 7. Identity, client access and smoke test

TLS encryption does not automatically imply authentication. Configure a supported listener authentication mechanism, KafkaUser and least-privilege ACLs; mount CA and client secrets into Kubernetes Pods with read-only volumes. Deploy version-pinned synthetic producer/consumer workloads with stable `event_id`, `aggregate_id` and payload hash. Require producer acknowledgements, durable idempotent sink effects, explicit offset commits and reconciliation of missing/duplicate IDs. Never use real regulated data.

## 8. Observability and reliability gates

Verify controller quorum, broker readiness, ISR, KafkaTopic reconciliation, PVC health, disk latency, node zone distribution, producer errors, p99 latency, consumer lag, Pod restarts and cost. Use actual exported metric names rather than assuming exporter labels. Test a bounded broker failure only in a disposable lab and verify accepted-event IDs after recovery.

## 9. Kubernetes-first hands-on labs (20)

Each lab must document exact version, prerequisite, command, expected result, actual result, rollback and timestamped PASS/FAIL evidence.

| # | Lab | Required evidence |
|---|---|---|
| 01 | Project, IAM and budget preflight | Sanitized command/metrics, result, rollback |
| 02 | GKE network and secondary IP ranges | Sanitized command/metrics, result, rollback |
| 03 | Private cluster endpoint design | Sanitized command/metrics, result, rollback |
| 04 | Regional node placement | Sanitized command/metrics, result, rollback |
| 05 | Workload Identity Federation | Sanitized command/metrics, result, rollback |
| 06 | Kubernetes namespace/RBAC | Sanitized command/metrics, result, rollback |
| 07 | NetworkPolicy baseline | Sanitized command/metrics, result, rollback |
| 08 | CSI driver and StorageClass | Sanitized command/metrics, result, rollback |
| 09 | PVC binding and topology | Sanitized command/metrics, result, rollback |
| 10 | Strimzi version compatibility | Sanitized command/metrics, result, rollback |
| 11 | Install pinned operator | Sanitized command/metrics, result, rollback |
| 12 | Validate Strimzi CRDs | Sanitized command/metrics, result, rollback |
| 13 | KRaft controller node pool | Sanitized command/metrics, result, rollback |
| 14 | KRaft broker node pool | Sanitized command/metrics, result, rollback |
| 15 | Kafka cluster bootstrap | Sanitized command/metrics, result, rollback |
| 16 | Verify quorum and ISR | Sanitized command/metrics, result, rollback |
| 17 | TLS listener and KafkaUser | Sanitized command/metrics, result, rollback |
| 18 | Topic and client smoke test | Sanitized command/metrics, result, rollback |
| 19 | Broker disruption and recovery | Sanitized command/metrics, result, rollback |
| 20 | Cost audit and cleanup | Sanitized command/metrics, result, rollback |

**Execution protocol:** verify project and context → baseline quorum/ISR and IDs → make one approved isolated change → capture metrics and alerts → restore health → reconcile IDs → clean up only owned resources. Lab publication does not establish that a test passed.

## 10. Failure scenarios (12)

| # | Scenario | Recovery requirement |
|---|---|---|
| 1 | GCP permission denied | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 2 | IP range exhausted | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 3 | Private endpoint inaccessible | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 4 | Unschedulable broker | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 5 | PVC Pending | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 6 | CSI provisioning failure | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 7 | Operator reconcile error | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 8 | Unsupported Kafka CR schema | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 9 | KRaft quorum unavailable | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 10 | ISR degradation | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 11 | TLS authentication failure | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |
| 12 | Orphaned disks and unexpected cost | Correlate GKE/Strimzi/Kafka evidence; contain, restore and reconcile |

For each scenario capture trigger, blast radius, alert, severity, timeline, rollback and preventive action. No destructive shared-cluster tests.

## 11. Production SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | GKE provisioning | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 2 | VPC and DNS | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 3 | Storage/PVC recovery | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 4 | Strimzi operator | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 5 | KRaft quorum | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 6 | Broker ISR | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 7 | TLS client access | Assess impact → read-only triage → approved mitigation → validate → RCA |
| 8 | Rollback and teardown | Assess impact → read-only triage → approved mitigation → validate → RCA |

Each runbook requires an owner, escalation, exact safe commands, stop criteria, recovery sign-off and evidence retention.

## 12. 100-point acceptance

| Gate | Points |
|---|---:|
| GCP IAM, VPC and cost controls | 15 |
| GKE cluster, scheduling and zones | 15 |
| CSI storage, PVC and disk performance | 15 |
| Strimzi and KRaft health | 20 |
| TLS, client authentication and ACLs | 10 |
| Synthetic event correctness | 10 |
| Observability and recovery | 10 |
| Evidence, rollback and cleanup | 5 |
| **Total** | **100** |

Proposed pass ≥85, with mandatory healthy quorum, validated zone placement, no unexplained missing accepted IDs, no critical security findings and independent review. **Runtime certification remains pending** until live tests pass.

## 13. Evidence manifest

```yaml
chapter: 112
environment: isolated-gke-lab
gcp_project: REDACTED
gke_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
controller_zones: []
broker_zones: []
storage_class: REPLACE
lab_results: []
accepted_event_ids: null
missing_event_ids: null
cost_review: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 14. Next chapter

**Chapter 113 — Google Cloud Kafka IAM, TLS, Authentication, ACL and Secrets.**
