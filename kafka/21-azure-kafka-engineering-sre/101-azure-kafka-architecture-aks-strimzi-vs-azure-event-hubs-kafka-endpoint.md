# Chapter 101 — Azure Kafka Architecture: AKS + Strimzi vs Azure Event Hubs Kafka Endpoint

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (1/10)  
**Deployment choices:** Apache Kafka KRaft on Azure Kubernetes Service (AKS) using Strimzi; Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 001–100 and Azure subscription with approved nonproduction access  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Scope:** Azure Event Hubs is **not** an Apache Kafka broker deployment. Its Kafka-compatible endpoint supports a subset of Kafka client behavior and is subject to Azure service tiers, API compatibility, auth, quotas, retention and regional capabilities. Do not assume full broker-admin, Kafka Streams, transactions, compaction, Kafka ACL or KRaft semantics. Confirm features against current Microsoft documentation and test the exact client version. All examples are design/inspection steps for a disposable lab with synthetic data, never real patient information.

## 1. Learning objectives

1. Distinguish running **Apache Kafka** on AKS from consuming a **Kafka-compatible managed event streaming endpoint**.
2. Design Azure networking, AKS/Strimzi/KRaft controller/broker topology and storage.
3. Evaluate Event Hubs protocol compatibility, identity, capacity, retention and DR limitations.
4. Compare Kafka producer/consumer/Connect behavior, observability, operational responsibility and FinOps.
5. Produce an architecture decision record (ADR), SLO/RPO/RTO requirements and evidence plan.

## 2. Architecture decision matrix

| Decision dimension | AKS + Strimzi KRaft | Azure Event Hubs Kafka endpoint |
|---|---|---|
| Engine | Apache Kafka brokers and KRaft controllers | Azure-managed Event Hubs service with Kafka protocol endpoint |
| Operations | Customer owns broker upgrades, storage, replication, quorum and operator | Azure owns service infrastructure; customer owns client configs, quotas and integration |
| Kubernetes | AKS, Strimzi CRDs, KafkaNodePool, KafkaTopic, KafkaUser | AKS optional for client apps; Event Hubs itself is not a KafkaNodePool |
| Kafka admin/config | Kafka/Strimzi-supported topic and broker administration | Service-defined management APIs and Kafka protocol subset; verify compatibility |
| Authentication | TLS/SCRAM or other Strimzi-supported mechanisms, Kafka ACLs | Azure-supported Kafka authentication (e.g., SASL mechanisms) and Azure authorization model |
| Storage | Azure Disk/PVC, AZ affinity, backup strategy owned by team | Managed event retention/capacity and tier-specific features |
| Scaling | Brokers, partitions, disk, CPU, network, ISR and controllers | Event Hubs namespace/hub capacity, partitions and service quotas |
| HA/DR | Kafka replication and approved cross-region replication/restore | Azure service availability and tier-specific Geo-DR/data replication capabilities |
| Portability | Fuller Kafka ecosystem compatibility, subject to deployed versions | Kafka-client interoperability where endpoint features are supported |
| Cost | AKS compute, Azure Disk, network, operator and on-call | Event Hubs pricing tier, capacity, retention and network |

**Default decision:** Choose AKS+Strimzi if application correctness depends on broker-level Kafka APIs, customized Kafka configs or full ecosystem features. Consider Event Hubs if a managed Kafka-protocol ingress service satisfies **tested** API/retention/identity requirements and reduces operational burden. The choice is workload-dependent, not a blanket performance claim.

## 3. Two reference architectures

### A. Apache Kafka on AKS

```text
GitOps + Azure Policy + Key Vault + managed identities
                        |
                private Azure AKS
                        |
                  Strimzi operator
                        |
        Kafka CR + KafkaNodePools (KRaft)
            /                      \
    3 controllers               3+ brokers
     across AZs                 across AZs
                                   |
                           Azure Disk PVCs
                                   |
                 internal TLS/SASL/ACL listeners
                                   |
     synthetic producer -> topics -> consumer / Connect
               |                         |
          ack-ID ledger              sink ledger
               +-------------------------+
                             |
                Azure Monitor / Prometheus
```

### B. Event Hubs Kafka-compatible endpoint

```text
Azure subscription / resource group / policy
                         |
                Event Hubs namespace
                         |
              Event hub + partitions
                         |
         Kafka protocol endpoint over TLS
                         |
      synthetic Kafka producer / consumer
                |                  |
            ack-ID ledger      sink ledger
                +------------------+
                         |
             Azure Monitor / diagnostics
```

Do not use Strimzi Kafka CRDs to administer Event Hubs. Provision Event Hubs through supported Azure management interfaces/IaC.

## 4. Azure prerequisites and read-only inventory

```bash
az account show --query '{subscription:id,tenant:tenantId,name:name}' -o json
az group list --query '[].{name:name,location:location}' -o table
az aks list --query '[].{name:name,resourceGroup:resourceGroup,location:location}' -o table
az eventhubs namespace list --query '[].{name:name,resourceGroup:resourceGroup,location:location,sku:sku.name}' -o table
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get storageclass
```

These commands require Azure CLI, appropriate permissions and configured kubectl context. They are read-only examples, not evidence of execution.

## 5. AKS + Strimzi KRaft topology

Reference production design: three dedicated KRaft controllers across failure domains and three or more brokers with rack-aware replicas, RF=3/minISR=2, persistent storage, private listeners and capacity for N-1 recovery.

Validate exact Strimzi/Kafka/AKS support and KafkaNodePool CR schema. Strimzi operator and CRDs must be version-aligned. For a smaller disposable lab, explicitly label non-HA compromises rather than claiming production resilience.

### KafkaNodePool broker example (schema must match pinned Strimzi)

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

**Warning:** Azure Disk volumes are zone-bound; inspect CSI StorageClass, `WaitForFirstConsumer`, node placement, disk limits and PV reclaim policy. An unplanned PVC deletion can destroy Kafka broker state.

## 6. Azure networking, identity and security

- AKS: private clusters where appropriate, VNet/subnet segmentation, NSGs, DNS, ingress/egress policy, Workload Identity, Key Vault CSI/External Secrets, Kubernetes RBAC and Kafka ACL.
- Event Hubs: supported TLS/SASL client authentication, Azure role assignments/SAS policies, private endpoints, namespace firewall and approved Kafka client bootstrap endpoint.
- Do not reuse Strimzi KafkaUser ACL manifests for Event Hubs authorization. Do not store namespace connection strings in Git or logs.

**Compatibility caution:** Event Hubs' supported SASL mechanisms and OAuth options vary by documentation and client setup. Use Microsoft-authored client examples for the selected tier/version rather than guessing an OAuth flow.

## 7. Synthetic producer/consumer reference contract

Record fields: `event_id`, `synthetic_subject_id`, `event_time_utc`, `event_type`, `schema_version` and a synthetic payload. Partition by stable synthetic subject ID where per-subject ordering matters.

Client-side reliability goals: bounded retry/backoff, delivery error reporting, acknowledgement ledger, consumer group lag/freshness and idempotent downstream upserts. Confirm supported producer idempotence/transaction behavior for **each** platform and client version before promising exactly-once semantics.

## 8. Kafka Connect/CDC and ecosystem compatibility

On AKS+Strimzi, Kafka Connect runs as separate workers and may use Strimzi KafkaConnect CRs with approved plugins. Test schema converters, source log retention, offsets, DLQ and sink side effects.

On Event Hubs, external Kafka Connect workers and clients may be compatible with supported protocol APIs, but plugins can depend on unsupported broker/admin/transaction features. Test actual connector/plugin versions, topic provisioning and task recovery; do not assume parity.

## 9. Observability and SLO design

| Signal | AKS + Strimzi | Event Hubs |
|---|---|---|
| Kafka broker/ISR/KRaft | Direct broker/operator metrics | Not exposed as customer-managed brokers |
| Producer success/P99 | Kafka client metrics | Kafka client metrics |
| Consumer lag/freshness | Kafka consumer metrics | Consumer/application metrics and supported Azure metrics |
| Storage/throughput | Azure Disk + broker metrics | Service throughput/capacity/throttling metrics |
| Auth/network | Kafka logs, TLS, AKS/VNet | Azure diagnostics, client logs and networking |
| DR | Kafka replication and restore proof | Tier-specific service replication/Geo-DR and client recovery proof |

Define owner-approved SLOs and RPO/RTO. A healthy Azure resource does not prove downstream data correctness.

## 10. Azure HA, DR and cost

AKS: account for zone-aware KRaft majority, broker replicas, Azure Disk topology, multi-region Kafka replication, schema/config backups, restore and operational toil. Event Hubs: inspect tier-specific availability, failover aliases versus event data replication, throughput units/processing units, retention, quotas and cross-region behavior.

Cost comparisons must include storage, ingress/egress, cross-zone transfer, monitoring, Key Vault, backups and on-call, not only headline hourly pricing.

## 11. Twenty Azure architecture and compatibility labs

### Lab 01 — Map Azure Kafka deployment options

**Procedure:** Compare AKS+Strimzi, Event Hubs Kafka endpoint, and existing Kafka portability requirements.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Define regulated synthetic event requirements

**Procedure:** Record throughput, ordering, retention, sovereignty, RPO/RTO, ACL, schema and privacy boundaries.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Inspect Azure subscriptions and resource governance

**Procedure:** Verify tenant, subscription, region, resource group, tags, policy, quotas and approved budgets.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Design Azure VNet and private connectivity

**Procedure:** Plan AKS subnets, private endpoints, DNS, egress, NSGs and approved client paths.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Design AKS KRaft controller quorum

**Procedure:** Plan 3 controllers across AZs with majority and compatible Strimzi node pools.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Design AKS Kafka broker topology

**Procedure:** Plan RF=3/minISR=2, rack awareness, AZ placement, PVC topology and N-1 capacity.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Compare Azure Disk storage profiles

**Procedure:** Assess Premium SSD v2, Premium SSD, throughput/IOPS and PVC reclaim policies.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Design Event Hubs namespace and hub

**Procedure:** Document partitions, throughput/capacity units, retention and Kafka endpoint constraints.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Compare Kafka API and operational semantics

**Procedure:** Identify admin API, broker settings, transactions, topic management and feature gaps.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Design Azure identities and Kafka authentication

**Procedure:** Compare KafkaUser TLS/SCRAM/ACL with Event Hubs supported OAuth/SAS mechanisms.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Design synthetic producer path

**Procedure:** Specify bootstrap endpoint, client properties, acks, idempotence and event-ID ledger.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Design synthetic consumer and sink

**Procedure:** Specify consumer groups, checkpoints/offsets, idempotent sink and freshness oracle.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Design Connect/CDC integration

**Procedure:** Assess supported Connect workers, plugin compatibility, source retention and DLQ.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Design AKS/Strimzi observability

**Procedure:** Plan broker/controller metrics, Azure Monitor, Prometheus, logs and alerting.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Design Event Hubs observability

**Procedure:** Plan Azure Monitor metrics, ingress/egress, throttling, consumer lag and diagnostic logs.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Design HA and region DR

**Procedure:** Compare AZ failure domains, replication, Geo-DR features and data replication guarantees.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Design capacity and cost model

**Procedure:** Compare AKS nodes, disks, network, operator overhead and Event Hubs capacity/billing.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Design GitOps and change controls

**Procedure:** Plan IaC, Argo CD/Flux, Azure policy, version pinning, reviews and rollback.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Design failure-mode tabletop

**Procedure:** Evaluate AKS broker loss, controller quorum, Azure Disk, Event Hubs quota and auth.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Complete architecture decision record

**Procedure:** Choose platform based on verified API support, SLO/RPO/RTO, security and operational cost.

**Acceptance evidence:** Azure subscription/region and isolated environment, Azure CLI/AKS/Strimzi/Kafka/client versions, pinned Git SHA, architecture assumptions, expected/observed, synthetic event IDs where applicable, security/cost/DR implications, **Design/Tabletop/Live** state, owner and independent reviewer. **Status: Pending** until executed.

## 12. Offline architecture decision validator

Save as `validate_ch101_azure_architecture.py`. This is a **design-review consistency check** and does not verify cloud service features, costs or live deployment.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("adr", help="Reviewed Azure Kafka architecture decision JSON")
args = p.parse_args()
with open(args.adr, encoding="utf-8") as f:
    d = json.load(f)
required = [
    "environment", "platform", "azure_region", "functional_compatibility_reviewed",
    "network_private", "identity_reviewed", "synthetic_only", "slo_defined",
    "rpo_rto_defined", "cost_reviewed", "rollback_plan", "independent_review",
    "evidence_ref"
]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
checks = {
    "isolated_lab": d["environment"] == "disposable-lab",
    "supported_choice": d["platform"] in ("aks-strimzi", "eventhubs-kafka-endpoint"),
    "region": bool(d["azure_region"]),
    "compatibility": d["functional_compatibility_reviewed"] is True,
    "private_network": d["network_private"] is True,
    "identity": d["identity_reviewed"] is True,
    "synthetic_data": d["synthetic_only"] is True,
    "slo": d["slo_defined"] is True,
    "rpo_rto": d["rpo_rto_defined"] is True,
    "cost": d["cost_reviewed"] is True,
    "rollback": bool(d["rollback_plan"]),
    "independent_review": d["independent_review"] is True,
    "evidence": bool(d["evidence_ref"]),
}
passed = all(checks.values())
print(json.dumps({"checks": checks, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitation:** Self-reported flags do not prove API compatibility, actual Azure role permissions, HA, live event correctness or reviewer independence.

## 13. Twelve Azure platform failure scenarios

### Scenario 01 — AKS broker Pod pending due to Azure Disk zone affinity

**Diagnosis:** Check CSI, PVC binding, node AZ, scheduler and volume limits. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 02 — KRaft controller majority lost after correlated zone failure

**Diagnosis:** Stop disruptive changes and redesign voter placement/recovery. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 03 — Azure Disk IOPS cap drives ISR shrink

**Diagnosis:** Inspect IOPS, throughput, queue depth and replica catch-up. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 04 — Event Hubs Kafka client receives authentication failure

**Diagnosis:** Review documented OAuth/SAS settings, namespace scope and TLS. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 05 — Event Hubs rejects unsupported Kafka admin behavior

**Diagnosis:** Validate documented Kafka endpoint API support; redesign workflow. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 06 — Event Hubs throughput or quota throttles producers

**Diagnosis:** Review namespace capacity, throttling and safe retry/backoff. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 07 — Client assumes broker ACL semantics on Event Hubs

**Diagnosis:** Map Azure RBAC/SAS authorization and least privilege explicitly. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 08 — Kafka Connect plugin depends on broker-specific features

**Diagnosis:** Run compatibility test and inspect task/offset/DLQ behavior. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 09 — Producer timeout creates ambiguous delivery

**Diagnosis:** Reconcile acknowledged and sink event IDs before replay. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 10 — Consumer lag persists after service recovery

**Diagnosis:** Inspect processing, partitions, checkpoints and downstream backpressure. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 11 — Region failover preserves endpoint but not latest events

**Diagnosis:** Distinguish metadata/alias failover from replicated event data. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

### Scenario 12 — Cross-cloud migration changes ordering or retention

**Diagnosis:** Validate per-key partition mapping, replay, TTL and business correctness. Correlate Azure networking/identity/quotas, Kafka client errors, AKS KRaft/ISR or Event Hubs diagnostics, source/sink event IDs, retention and owner-approved SLO. **Response:** Stop unsafe change, preserve synthetic data and restore supported service behavior. **Exit:** Architecture compatibility verified, stable delivery, approved RPO/RTO, RCA and independent signoff.

## 14. Eight production SRE runbooks

### Runbook A — Azure Kafka platform selection and approval

**Trigger/actions:** Verify functional requirements, API compatibility, SLO, RPO/RTO and ADR. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook B — AKS Strimzi KRaft topology review

**Trigger/actions:** Check controller quorum, brokers, RF/minISR, AZ and PVC. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook C — Azure networking and identity recovery

**Trigger/actions:** Inspect private DNS, endpoints, firewall, TLS and authorization. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook D — Azure Disk and Kafka performance recovery

**Trigger/actions:** Inspect storage limits, broker pressure, ISR and headroom. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook E — Event Hubs Kafka client incident

**Trigger/actions:** Check supported protocol/auth, quotas, throttling and consumer state. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook F — Producer/consumer/Connect correctness

**Trigger/actions:** Reconcile event IDs, offsets, DLQ, CDC and downstream effects. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook G — Azure HA/DR and region cutover

**Trigger/actions:** Verify replication semantics, restore, measured RPO/RTO and client endpoints. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

### Runbook H — Architecture acceptance and change signoff

**Trigger/actions:** Review costs, security, tests, evidence, exceptions and decision. **No-go:** wrong Azure subscription, unapproved production change, unsupported Kafka API assumption, lost KRaft majority, sensitive data exposure, missing restore proof or unexplained acknowledged event loss. **Exit:** Secure and supported architecture, reconciled synthetic events, owner approval and reviewed evidence.

## 15. Evidence package

```text
evidence-ch101/
  01-azure-platform-options.md
  02-synthetic-requirements.md
  03-subscription-governance.md
  04-vnet-private-connectivity.md
  05-kraft-controller-topology.md
  06-broker-az-storage.md
  07-azure-disk.md
  08-eventhubs-namespace.md
  09-kafka-api-compatibility.md
  10-identity-auth.md
  11-producer.md
  12-consumer.md
  13-connect-cdc.md
  14-aks-observability.md
  15-eventhubs-observability.md
  16-ha-dr.md
  17-capacity-cost.md
  18-gitops.md
  19-failure-tabletop.md
  20-architecture-decision.md
  azure-kafka-adr.json
  architecture-acceptance.md
```

## 16. 100-point Azure Kafka architecture acceptance

| Domain | Points | Critical |
|---|---:|---|
| Azure platform choice and Kafka API compatibility | 25 | Yes |
| AKS/KRaft or Event Hubs topology, network and security | 20 | Yes |
| Producer/consumer/Connect data correctness | 20 | Yes |
| Observability, SLO, HA and DR design | 15 | Yes |
| Capacity, Azure cost and GitOps operations | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Design-review pass:** ≥85/100 with every critical architecture gate reviewed. **Live platform acceptance:** separate, requires executed tests and verified event correctness. **Automatic fail:** unsupported Kafka protocol feature relied upon, unsafe controller majority, missing authorization, PHI exposure, unproven event correctness or fabricated live evidence.

**Current status:** Published architecture chapter; live labs and independent security review **Pending**.

## 17. References and next chapter

- [Microsoft Azure Event Hubs for Apache Kafka](https://learn.microsoft.com/azure/event-hubs/azure-event-hubs-kafka-overview)
- [Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/)
- [Azure Event Hubs documentation](https://learn.microsoft.com/azure/event-hubs/)
- [Strimzi documentation](https://strimzi.io/documentation/)
- [Apache Kafka documentation](https://kafka.apache.org/documentation/)

**Next:** Chapter 102 — Provision AKS, Networking, Storage and Strimzi KRaft.

---

**Verification boundary:** Publication is not evidence of Azure deployment, Kafka endpoint compatibility testing, performance benchmarking or independent security review.
