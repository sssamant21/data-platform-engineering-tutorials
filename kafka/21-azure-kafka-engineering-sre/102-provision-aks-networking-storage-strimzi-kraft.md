# Chapter 102 — Provision AKS, Networking, Storage and Strimzi KRaft

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (2/10)  
**Platform:** Microsoft Azure Kubernetes Service (AKS), Strimzi, Apache Kafka KRaft, Azure Disk CSI  
**Prerequisites:** Chapter 101; approved disposable Azure subscription/resource group, budget and Azure CLI  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** The examples are for an approved disposable lab. Azure resource creation incurs cost. Never run mutating commands against an unknown subscription, AKS context or production environment. Pin supported AKS/Kubernetes/Strimzi/Kafka versions; review current Microsoft and Strimzi schemas. Never put secrets or healthcare PHI in manifests, logs or synthetic messages. Do not delete PVCs or resource groups without explicit ownership and backup review.

## 1. Objectives and deployment outcome

Provision an isolated AKS foundation for Kafka KRaft, with controlled Azure networking, Workload Identity, Azure Disk CSI, Strimzi operator, separate controller and broker node pools, private Kafka TLS listener, RF/minISR, synthetic topic/client path, monitoring, GitOps and independent acceptance evidence.

**Architecture boundary:** This chapter deploys **Apache Kafka brokers on AKS**. It does not provision Azure Event Hubs; Event Hubs Kafka compatibility is covered in Chapter 101 and Chapter 104.

## 2. Reference architecture

```text
Azure subscription / budget / policy
               |
        Resource group + VNet
               |
        Private AKS cluster
               |
     System pool + Kafka node pools
               |
         Strimzi operator
               |
      Kafka CR / KafkaNodePools
        /                 \
  3 KRaft controllers    3 Kafka brokers
  across AZs             across AZs
        |                    |
  Azure Disk PVCs       Azure Disk PVCs
                             |
                    private TLS listener
                             |
          synthetic producer -> topic -> consumer
                     |                   |
              acknowledged IDs       sink IDs
                     +-------------------+
                              |
                     Prometheus / Azure Monitor
```

Three controllers and three brokers are a production HA **reference topology**, not a guarantee of zone resilience. Confirm AZ placement, rack-aware replication, disk topology, node and network capacity, supported Strimzi version and controller majority.

## 3. Version and safety matrix

Record actual supported versions before applying any manifest.

| Component | Validation |
|---|---|
| Azure CLI | `az version` and authenticated tenant/subscription |
| AKS/Kubernetes | `az aks get-versions --location <region>`; confirm supported version |
| Azure Disk CSI | `kubectl get csidriver`; inspect StorageClass and zone constraints |
| Strimzi | Pin a documented release compatible with target Kafka/Kubernetes |
| Kafka/KRaft | Pin supported Kafka and metadata version per Strimzi release |
| GitOps | Pin Argo CD/Flux version and resource ownership |
| Client/Connect | Verify TLS/auth, Kafka protocol, schema and plugin compatibility |

No literal Kafka/Strimzi version is prescribed here because operator CRD requirements change across releases.

## 4. Azure preflight — read-only commands

```bash
az account show --query '{subscription:id,tenant:tenantId,name:name}' -o json
az account list -o table
az provider show -n Microsoft.ContainerService --query registrationState -o tsv
az provider show -n Microsoft.Compute --query registrationState -o tsv
az provider show -n Microsoft.Network --query registrationState -o tsv
az aks get-versions --location eastus -o table
az vm list-usage --location eastus -o table
kubectl config get-contexts
```

Replace `eastus` with an approved region. **Do not infer** that a region, SKU or quota is available from this example.

## 5. Reviewed IaC and resource layout

```text
azure-kafka-lab/
  terraform/
    versions.tf
    providers.tf
    network.tf
    aks.tf
    identity.tf
    outputs.tf
    variables.tf
  kubernetes/
    namespaces/
    strimzi/
    kafka/
      kafka.yaml
      nodepool-controllers.yaml
      nodepool-brokers.yaml
      topic-synthetic.yaml
      users/
    networkpolicies/
    monitoring/
    applications/
  gitops/
  tests/
  evidence/
```

Recommended Azure resources: dedicated tagged resource group; non-overlapping VNet/subnets; private AKS with OIDC and Workload Identity; dedicated Kafka node pools; Azure Disk CSI storage; Key Vault-backed secrets; Azure Monitor; private DNS and approved egress. Review Terraform plan and Azure Policy before apply.

## 6. AKS creation template — DO NOT RUN WITHOUT APPROVAL

The following is an **illustrative command structure**, not a fully validated cluster deployment. A production-like topology also requires approved VNet/subnets, private DNS connectivity, user node pools, zones, disk/CSI, identity and node sizing.

```bash
# Replace placeholders and run only in an approved disposable subscription.
az account set --subscription "<APPROVED_SUBSCRIPTION_ID>"
az group create --name "<LAB_RESOURCE_GROUP>" --location "<APPROVED_REGION>"
az aks create \
  --resource-group "<LAB_RESOURCE_GROUP>" \
  --name "<LAB_AKS_NAME>" \
  --location "<APPROVED_REGION>" \
  --enable-managed-identity \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --node-count 3 \
  --node-vm-size "<APPROVED_VM_SKU>" \
  --network-plugin azure \
  --enable-private-cluster
```

**Preflight caveat:** AKS CLI flags, private-cluster networking and zone support are version- and region-dependent. Validate with `az aks create --help`, Azure documentation and an approved `what-if`/IaC plan. Do not assume this template includes all security controls or works in every subscription.

## 7. Verify cluster context and storage

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
kubectl get csidriver
kubectl get pods -A
```

Review whether the Azure Disk StorageClass uses `WaitForFirstConsumer`, appropriate disk SKU and PVC retention. EBS is an AWS term; on AKS use **Azure Disk CSI**, not EBS CSI.

## 8. Strimzi operator and KRaft resources

Install the **pinned** Strimzi release using its official version-specific installation instructions and approved namespace/RBAC. Verify CRDs and operator readiness:

```bash
kubectl get crd | grep kafka.strimzi.io
kubectl get pods -A -l name=strimzi-cluster-operator
kubectl get kafka,kafkanodepool -A
```

### 8.1 KRaft controller KafkaNodePool template

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: controllers
  namespace: kafka-azure-lab
  labels:
    strimzi.io/cluster: azure-kafka
spec:
  replicas: 3
  roles: [controller]
  storage:
    type: persistent-claim
    size: 20Gi
    deleteClaim: false
```

### 8.2 Broker KafkaNodePool template

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers
  namespace: kafka-azure-lab
  labels:
    strimzi.io/cluster: azure-kafka
spec:
  replicas: 3
  roles: [broker]
  storage:
    type: persistent-claim
    size: 100Gi
    deleteClaim: false
```

**Compatibility warning:** The exact Kafka CR/KafkaNodePool API versions, required fields, metadata version and KRaft options depend on pinned Strimzi release. Validate against installed CRDs and operator release documentation before any apply. Add AZ topology spread, affinity, node selectors, rack-awareness, resources, JVM settings and StorageClass selection before treating this as a complete production design.

### 8.3 Kafka CR skeleton

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: azure-kafka
  namespace: kafka-azure-lab
spec:
  kafka:
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
    config:
      default.replication.factor: 3
      min.insync.replicas: 2
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

This is a **schema review skeleton**, not a guaranteed apply-ready manifest. Broker authorization must be explicitly configured for KafkaUser ACLs according to supported Strimzi release.

## 9. Network, identity and secret controls

Use Azure Workload Identity for supported workload-to-Azure authentication, Key Vault/CSI or External Secrets for approved secret delivery, scoped Kubernetes RBAC, KafkaUser identities and ACLs, TLS listener and certificate rotation, Azure NSG/VNet segmentation, NetworkPolicies and audited GitOps changes.

Test inter-broker, controller, operator, client, DNS and monitoring flows. A default-deny policy without carefully scoped allows can cause KRaft quorum or replication failures.

## 10. Synthetic topic and client acceptance

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: synthetic-encounter-events
  namespace: kafka-azure-lab
  labels:
    strimzi.io/cluster: azure-kafka
spec:
  partitions: 12
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 604800000
```

Publish synthetic events with `event_id`, `synthetic_subject_id`, `event_time_utc` and `schema_version`. Validate `acks=all`, idempotence, authorized TLS/SASL, consumer group offsets, idempotent sink writes and acknowledged-ID reconciliation.

**Do not** assume producer exactly-once semantics extend to external sinks.

## 11. Observability and reliability gates

Monitor KRaft controller majority, Kafka/Strimzi reconciliation, offline partitions, under-minISR, ISR shrink, Azure Disk IOPS/throughput/latency, PVC usage, broker CPU/heap, client P99, consumer lag/freshness, Connect task health, auth failures and secret expiry.

Define service-owner-approved SLOs. Recovery requires both healthy Kafka state and reconciled synthetic downstream records.

## 12. Twenty hands-on AKS provisioning labs

### Lab 01 — Azure subscription and budget preflight

**Procedure:** Validate subscription, quota, region, permissions, tags and cleanup approval.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Design AKS VNet and subnets

**Procedure:** Allocate CIDRs, DNS, private endpoints, NAT/egress and network policy.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Provision isolated resource group

**Procedure:** Use tagged IaC with explicit environment identity and destroy plan.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Provision AKS cluster

**Procedure:** Pin supported Kubernetes release, OIDC issuer, Workload Identity and node pools.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Validate kubectl context and RBAC

**Procedure:** Verify target context, API permissions and namespace isolation.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Configure Azure Disk CSI storage

**Procedure:** Review disk CSI, Premium SSD profile, WaitForFirstConsumer and AZ topology.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Install supported Strimzi operator

**Procedure:** Pin operator release, install CRDs and verify namespace/RBAC and readiness.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Create Kafka controller node pool

**Procedure:** Define three KRaft controllers, AZ placement and persistent storage.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Create Kafka broker node pool

**Procedure:** Define three brokers, resources, Azure Disk PVCs and rack-aware topology.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Deploy Kafka CR with private TLS listener

**Procedure:** Validate CR schema, KRaft version and replication/minISR.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Inspect controller quorum

**Procedure:** Use supported Kafka admin tooling to confirm majority and metadata health.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Inspect broker replicas and partitions

**Procedure:** Verify RF=3/minISR=2, ISR, leader placement and partition readiness.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Apply least-privilege Kafka identities

**Procedure:** Configure KafkaUser authentication, ACLs and secret delivery.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Apply Kubernetes NetworkPolicies

**Procedure:** Allow approved DNS/operator/replication/client/monitoring traffic only.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Deploy synthetic topic and producer

**Procedure:** Use acks=all, idempotence where supported and event-ID ledger.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Deploy synthetic consumer and sink

**Procedure:** Verify consumer group lag, offsets and idempotent sink effects.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Configure Azure Monitor and Prometheus

**Procedure:** Collect broker/KRaft, PVC, disk IOPS, client and Connect metrics.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Test non-destructive readiness

**Procedure:** Verify Pod, PVC, quorum, ISR, client auth and synthetic ID reconciliation.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Review GitOps rollback and cleanup

**Procedure:** Review drift, supported rollback, PVC reclaim, backups and cost teardown.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Complete independent build acceptance

**Procedure:** Capture evidence, exceptions, SLOs, reviewer approval and next steps.

**Evidence:** UTC time, approved Azure subscription/region, AKS context, Strimzi/Kafka/Kubernetes versions, Git SHA, expected/observed, Kubernetes/Azure status, synthetic event ledger, security/rollback/cost controls, **Design/Tabletop/Live** state and independent reviewer. **Status: Pending** until executed.

## 13. Offline AKS readiness validator

Save as `validate_ch102_aks_readiness.py`. This validates a **reviewed JSON deployment inventory**, not live Azure/Kubernetes resources.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("inventory", help="Reviewed AKS Kafka lab inventory JSON")
args = p.parse_args()
with open(args.inventory, encoding="utf-8") as f:
    d = json.load(f)
required = ["environment", "azure_subscription_reviewed", "aks_context_reviewed",
            "strimzi_version", "kafka_version", "controllers", "brokers",
            "replication_factor", "min_isr", "azure_disk_csi_verified",
            "private_network_verified", "tls_auth_verified",
            "kraft_quorum_verified", "isr_verified",
            "synthetic_events_reconciled", "secrets_in_git",
            "independent_review", "evidence_ref"]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
numeric = ["controllers", "brokers", "replication_factor", "min_isr"]
if any(type(d[k]) is not int for k in numeric):
    p.error("topology values must be integers")
checks = {
    "disposable": d["environment"] == "disposable-lab",
    "subscription": d["azure_subscription_reviewed"] is True,
    "context": d["aks_context_reviewed"] is True,
    "versions": bool(d["strimzi_version"] and d["kafka_version"]),
    "controller_majority": d["controllers"] >= 3 and d["controllers"] % 2 == 1,
    "replication": d["brokers"] >= 3 and 1 <= d["min_isr"] <= d["replication_factor"] <= d["brokers"],
    "azure_disk": d["azure_disk_csi_verified"] is True,
    "private_network": d["private_network_verified"] is True,
    "tls_auth": d["tls_auth_verified"] is True,
    "kraft": d["kraft_quorum_verified"] is True,
    "isr": d["isr_verified"] is True,
    "event_correctness": d["synthetic_events_reconciled"] is True,
    "no_git_secrets": d["secrets_in_git"] is False,
    "independent_review": d["independent_review"] is True,
    "evidence": bool(d["evidence_ref"]),
}
passed = all(checks.values())
print(json.dumps({"checks": checks, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitation:** Self-reported JSON cannot verify actual Azure quota, node AZs, PVC topology, quorum, Kafka data correctness or reviewer identity. Require primary evidence.

## 14. Twelve AKS deployment failure scenarios

### Scenario 01 — AKS quota or VM SKU capacity blocks node provisioning

**Diagnosis:** Review regional quota, SKU availability and node pool sizing. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 02 — Private AKS API cannot be reached

**Diagnosis:** Check DNS, VNet, route, identity and authorized jump host. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 03 — Azure Disk PVC remains Pending

**Diagnosis:** Inspect StorageClass, CSI controller, AZ affinity and node placement. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 04 — Strimzi CRD version mismatches operator

**Diagnosis:** Stop apply, pin release and validate schema/upgrade compatibility. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 05 — KRaft controller Pods start without quorum

**Diagnosis:** Check voters, networking, listeners, storage and supported versions. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 06 — Broker pods remain unschedulable

**Diagnosis:** Review CPU/memory requests, anti-affinity, taints and disk limits. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 07 — Kafka CR stays NotReady

**Diagnosis:** Inspect operator events, node pools, secrets, storage and controller health. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 08 — Replication falls below minISR

**Diagnosis:** Stop risky changes and recover follower brokers safely. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 09 — NetworkPolicy blocks inter-broker traffic

**Diagnosis:** Review policy flows, restore only required ports and validate ISR. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 10 — TLS/SASL authentication fails

**Diagnosis:** Check CA trust, listener config, user secret and ACL. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 11 — Synthetic producer acknowledges but sink misses events

**Diagnosis:** Reconcile IDs, consumer offsets and sink writes before promotion. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

### Scenario 12 — GitOps or cleanup threatens retained PVC data

**Diagnosis:** Stop deletion, review reclaim policy, backups and recovery plan. Correlate Azure CLI/AKS status, operator events, KafkaNodePool/PVC, controller quorum, broker ISR, TLS/ACL, producer/consumer and GitOps. **Response:** Stop unsafe changes, preserve durable state and apply reviewed forward-fix/rollback. **Exit:** Supported deployment, healthy quorum/ISR, secure clients, reconciled synthetic IDs and independent signoff.

## 15. Eight production SRE runbooks

### Runbook A — Azure and AKS preflight

**Trigger/actions:** Verify subscription, resource group, version, budget and target context. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook B — Private network and DNS troubleshooting

**Trigger/actions:** Inspect VNet/subnets, routing, NSG, private endpoints and cluster access. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook C — Azure Disk/PVC recovery

**Trigger/actions:** Inspect CSI, AZ affinity, capacity, IOPS and reclaim policy. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook D — Strimzi/KRaft controller recovery

**Trigger/actions:** Inspect operator, CRD, KafkaNodePool, controller majority and metadata. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook E — Broker/ISR and replication recovery

**Trigger/actions:** Review leaders, RF/minISR, rack placement and follower catch-up. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook F — Identity, TLS and NetworkPolicy recovery

**Trigger/actions:** Check KafkaUser, ACL, CA, secrets and approved flows. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook G — Producer/consumer and monitoring validation

**Trigger/actions:** Reconcile synthetic IDs, client errors, lag, metrics and alerts. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

### Runbook H — GitOps rollback and lab teardown

**Trigger/actions:** Protect persistent data, review rollback and remove approved disposable resources. **No-go:** unknown subscription/context, unapproved production mutation, controller majority risk, PVC deletion, unsupported Strimzi/Kafka version, exposed credentials or unexplained acknowledged-ID loss. **Exit:** Verified Azure/AKS state, stable Kafka and clients, rollback evidence and independent review.

## 16. Evidence package

```text
evidence-ch102/
  01-azure-preflight.md
  02-vnet-subnets.md
  03-resource-group.md
  04-aks-provision.md
  05-context-rbac.md
  06-azure-disk-csi.md
  07-strimzi-operator.md
  08-kraft-controllers.md
  09-kafka-brokers.md
  10-kafka-cr.md
  11-quorum.md
  12-isr-partitions.md
  13-kafka-identities.md
  14-networkpolicies.md
  15-synthetic-producer.md
  16-synthetic-consumer.md
  17-azure-monitor.md
  18-readiness.md
  19-gitops-cleanup.md
  20-independent-acceptance.md
  aks-readiness-inventory.json
  cost-and-cleanup-approval.md
```

## 17. 100-point AKS build acceptance

| Domain | Points | Critical |
|---|---:|---|
| Azure subscription, VNet, AKS and Azure Disk | 25 | Yes |
| Strimzi/KRaft quorum, broker replication and PVC | 25 | Yes |
| TLS, ACL, identity and network isolation | 20 | Yes |
| Synthetic producer/consumer correctness | 15 | Yes |
| Monitoring, GitOps, cleanup and independent review | 15 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently verified using live isolated-cluster evidence. **Automatic Fail:** unapproved Azure mutation, unsafe quorum/ISR, missing storage durability, exposed secrets/PHI, unsupported operator version or missing acknowledged synthetic IDs.

**Current status:** Published; live Azure deployment and independent technical/security review **Pending**.

## 18. References and next chapter

- [Azure Kubernetes Service documentation](https://learn.microsoft.com/azure/aks/)
- [Azure Disk CSI on AKS](https://learn.microsoft.com/azure/aks/azure-disk-csi)
- [Strimzi documentation](https://strimzi.io/documentation/)
- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Azure CLI reference](https://learn.microsoft.com/cli/azure/)

**Next:** Chapter 103 — Azure Kafka Identity, Entra ID, TLS, SASL, ACL and Secrets.

---

**Verification boundary:** Publication confirms chapter availability only. No AKS deployment, Kafka quorum verification, Azure Disk performance test, live synthetic pipeline or independent review is claimed.
