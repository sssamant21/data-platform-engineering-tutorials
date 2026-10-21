# Chapter 071 — Amazon MSK Architecture, Networking, IAM and Production Administration

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 15 — Amazon MSK and AWS Kafka Operations (1/5)  
**Primary application platform:** Amazon EKS / Kubernetes clients connecting to Amazon MSK  
**Kafka platform:** Amazon MSK managed brokers (not Strimzi-managed brokers)  
**Prerequisites:** Chapters 001–070; AWS VPC, IAM, EKS, Kafka client administration  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Default all work to read-only AWS/EKS inventory and approved isolated lab accounts. Never create chargeable MSK clusters, modify VPC routes/security groups, expose public listeners, associate production credentials, upgrade brokers or change encryption without change approval. AWS capabilities and supported Kafka versions differ by MSK deployment type, region and date: confirm against current AWS documentation before execution.

## 1. Mission and learning outcomes

Design and administer Amazon Managed Streaming for Apache Kafka (MSK) with **Kubernetes-first clients running on EKS**. Understand the managed-service responsibility boundary, MSK cluster architecture, VPC connectivity, IAM/SASL and SCRAM/TLS authentication, EKS identity, monitoring, capacity, change management and production incident response.

By completion, learners can trace an EKS Pod to MSK broker, explain which Kafka operations AWS manages versus customers, audit least-privilege authentication, interpret monitoring and produce a defensible operational readiness package.

## 2. Architecture and responsibility boundaries

```text
 GitOps-managed EKS workload
    Kubernetes ServiceAccount
               |
    EKS Pod Identity / IRSA
               |
       AWS SDK credentials
               |
 EKS Pod -> VPC networking / DNS
               |
 Security groups / routes / endpoints
               |
  Amazon MSK bootstrap brokers
               |
  TLS + SASL/IAM or SCRAM (as configured)
               |
     Managed Kafka brokers
      AZ1     AZ2     AZ3
               |
  topics / partitions / replicas / ISR
               |
 CloudWatch / Open Monitoring / logs
```

**AWS manages** MSK broker infrastructure and supported managed lifecycle functions. **Customers remain responsible** for network reachability, IAM/ACL authorization, topic design, partitioning, retention, application correctness, client retries, capacity, monitoring and recovery objectives. EKS is a client runtime; deploying MSK does **not** create Strimzi KafkaNodePools or grant Kubernetes Pods access automatically.

## 3. Provisioned versus serverless MSK

| Dimension | Provisioned MSK | MSK Serverless |
|---|---|---|
| Broker sizing | customer selects supported broker/storage configuration | managed service capacity abstraction |
| Operational controls | more broker/cluster configuration choices | different supported feature and quota set |
| Networking | VPC/private connectivity with deployment-specific options | validate supported VPC and access model |
| Scaling | customer plans capacity, partition and throughput | elastic within service-specific limits |
| Monitoring | CloudWatch and supported enhanced/open monitoring | check available metrics by service type |
| Suitability | predictable/high-control workloads | supported variable workloads with simpler operations |

Do not assume every authentication mechanism, Kafka API, region, connectivity option or monitoring feature is identical between the two. Record the deployment type before recommending a command.

## 4. Multi-AZ architecture and Kafka durability

Provisioned MSK commonly uses brokers distributed across multiple Availability Zones. Validate the actual cluster subnet/AZ topology, replication factor, min.insync.replicas, partition leaders, under-replicated partitions, client acks and broker recovery time.

**Critical distinction:** MSK's managed infrastructure availability does not remove the need for Kafka-level RF/minISR correctness or tested application failover. A broker-count increase does not by itself rebalance all partitions.

## 5. AWS identity and read-only inventory

Use an approved SSO profile. Replace `AWS_PROFILE_NAME` and `AWS_REGION` with actual values.

```bash
export AWS_PROFILE=AWS_PROFILE_NAME
export AWS_REGION=AWS_REGION
aws sts get-caller-identity
aws kafka list-clusters-v2 --region "$AWS_REGION"
aws kafka list-clusters --region "$AWS_REGION"
aws eks list-clusters --region "$AWS_REGION"
```

After identifying an authorized **provisioned** cluster ARN:

```bash
export MSK_ARN='arn:aws:kafka:REGION:ACCOUNT:cluster/NAME/UUID'
aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka list-nodes --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
```

Some commands, response fields and ARN/resource types are deployment-specific. For serverless clusters, inspect supported APIs and skip broker-node operations that do not apply.

## 6. EKS networking and broker reachability

**Packet path:** EKS Pod -> Pod ENI/node network -> subnet route -> VPC or approved cross-VPC connectivity -> broker ENI -> listener. Verify security groups, NACLs, DNS, AZ/subnet placement and all broker-advertised endpoints.

A bootstrap broker address is only the first step. Kafka clients obtain metadata and then connect to **individual broker endpoints**. A successful TCP connection to one bootstrap host does not prove produce/consume connectivity.

```bash
kubectl config current-context
kubectl -n kafka-clients get pods -o wide
kubectl -n kafka-clients get serviceaccount
kubectl -n kafka-clients get networkpolicy
kubectl -n kafka-clients get events --sort-by=.metadata.creationTimestamp
```

For a pre-approved debug Pod containing `getent`, `openssl` and a Kafka client:

```bash
# Run only inside an approved nonproduction debug Pod.
kubectl -n kafka-clients exec POD_NAME -- getent hosts BROKER_DNS
kubectl -n kafka-clients exec POD_NAME -- openssl s_client -connect BROKER_DNS:PORT -servername BROKER_DNS -verify_return_error
```

Replace placeholders with **the actual listener returned by MSK**. TLS handshake alone does not validate Kafka IAM/SCRAM authorization. Never print credentials.

## 7. IAM authorization for MSK

For MSK IAM authentication, the client uses the supported SASL/IAM mechanism and AWS credentials. On EKS, use IRSA or EKS Pod Identity where supported, with a **dedicated service account and role per application or tenant**. Confirm the client library/plugin supports the selected mechanism.

Typical permissions may include cluster connect/describe, topic describe/read/write, and group describe/alter. The exact action names, resource ARN patterns, and dependent permissions must be checked against the current AWS MSK IAM authorization documentation. Avoid blanket `kafka-cluster:*` on `*` in production.

**Policy review checklist:**
- AWS account, region, cluster ARN and topic/group resource ARNs are correct.
- Role trust restricts the intended EKS identity.
- Topic and consumer-group scope is least privilege.
- Kafka administrative permissions are separate from application roles.
- Authentication failure logs and denied actions are monitored.
- Cross-account and multi-VPC policies are reviewed independently.

## 8. TLS, SCRAM and encryption

- **In transit:** prefer encrypted client-broker and inter-broker traffic; verify actual cluster encryption settings and TLS trust.
- **At rest:** inspect MSK-managed storage encryption and any customer-managed KMS key configuration/grants.
- **SCRAM:** for supported provisioned deployments, review AWS Secrets Manager secret association, required naming/format, KMS access, client mechanism and rotation.
- **IAM:** use AWS credentials, not KafkaUser Strimzi CRs; IAM authorization and Kafka ACLs are different authorization models.
- **Certificate rotation:** stage trust and test clients; do not disable hostname validation to fix TLS issues.

## 9. Kubernetes-first client identity

An EKS service account should map to the approved IAM role using either **IRSA** or **EKS Pod Identity**. These are different credential delivery mechanisms with distinct trust/association setup. Do not assume a Pod automatically receives permissions from its node IAM role.

```bash
kubectl -n kafka-clients get serviceaccount -o yaml
kubectl -n kafka-clients get pods -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName,NODE:.spec.nodeName
aws eks describe-cluster --name EKS_CLUSTER_NAME --region "$AWS_REGION"
```

Review annotations/associations and IAM trust without dumping tokens or secrets. Verify AWS SDK credential resolution in an approved synthetic client Pod, then perform an authenticated Kafka producer/consumer smoke test.

## 10. Network security and connectivity options

Same-VPC, VPC peering, Transit Gateway, VPN/Direct Connect and MSK-managed multi-VPC connectivity have different routing, DNS, account and support requirements. Verify the chosen architecture is supported for the cluster type, authentication mode and region. Do not equate a reachable private IP with authorized Kafka protocol access.

## 11. CloudWatch and Open Monitoring

Inspect supported metrics for broker CPU, network, disk, partitions, ISR, client connections, request latency, consumer lag and storage growth. Availability and cost of enhanced monitoring, broker log delivery and Open Monitoring/JMX vary by MSK type/configuration.

```bash
aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
aws logs describe-log-groups --region "$AWS_REGION"
```

Capture dimension names from actual CloudWatch metric responses rather than assuming all metrics exist. EKS client metrics and distributed traces must be correlated with MSK broker metrics to identify application impact.

## 12. Capacity and change planning

Track partitions per broker, throughput, retention, storage headroom, broker CPU/network, replication catch-up and recovery window. Account for broker replacement and AZ outage scenarios. MSK storage expansion, broker scaling and version upgrades are service-specific operations with constraints; review the current AWS support matrix and maintenance behavior.

**Change gates:** owner approval, backup/DR plan, RF/minISR, client SLO, AWS quotas, security impact, expected cost, rollback feasibility and post-change validation.

## 13. Twenty Kubernetes-first MSK labs

### Lab 01 — Define MSK architecture decision

**Procedure:** Compare provisioned versus serverless support, broker control, workload constraints, cost and region-specific availability.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 02 — Identify AWS account and region

**Procedure:** Confirm caller identity, active profile, approved region and nonproduction boundaries.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 03 — Inventory MSK clusters

**Procedure:** List provisioned/serverless clusters, ARNs, states, tags, Kafka versions and owners.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 04 — Inspect cluster details

**Procedure:** Review broker type, number, AZs, storage, encryption, monitoring and cluster state.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 05 — Inspect VPC and subnets

**Procedure:** Map private subnets, route tables, AZs, CIDRs and MSK broker ENIs.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 06 — Inspect EKS-to-MSK path

**Procedure:** Map EKS Pod-to-node/VPC routing, security groups, DNS and Kafka listeners.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 07 — Inspect security groups

**Procedure:** Review least-privilege ingress from approved EKS workloads and broker outbound requirements.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 08 — Review bootstrap endpoints

**Procedure:** Compare IAM, TLS and SCRAM bootstrap strings with configured client mechanism.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 09 — Review IAM authentication

**Procedure:** Validate cluster/topic/group action scopes, IAM principal mapping and policy review.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 10 — Review IRSA or Pod Identity

**Procedure:** Confirm EKS service account to AWS role trust and least privilege.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 11 — Review TLS and encryption

**Procedure:** Check in-transit encryption, KMS at rest, key grants and CA trust.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 12 — Review SCRAM Secrets Manager

**Procedure:** Inspect secret ARN naming, KMS permissions, association and rotation design.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 13 — Review Kafka ACL separation

**Procedure:** Explain Kafka ACL requirements for SCRAM/mTLS and IAM authorization differences.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 14 — Review Kafka client DNS

**Procedure:** Validate EKS Pod DNS, broker advertised endpoints and VPC resolution.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 15 — Review multi-VPC connectivity

**Procedure:** Compare peering, Transit Gateway and supported MSK managed connectivity.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 16 — Review CloudWatch monitoring

**Procedure:** Inventory broker/cluster metrics, enhanced monitoring and log delivery.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 17 — Review Prometheus and Open Monitoring

**Procedure:** Inspect supported JMX/Node exporter integration and collection cost.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 18 — Review quotas and capacity

**Procedure:** Review broker throughput, partitions, connection limits, storage growth and recovery headroom.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 19 — Review change and backup strategy

**Procedure:** Record supported MSK operations, version upgrades, recovery and DR constraints.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

### Lab 20 — Perform acceptance tabletop

**Procedure:** Document end-to-end EKS client auth/connectivity smoke, alerts, risks and reviewer.

**Evidence and acceptance:** Record AWS account alias (not secret identifiers), region, MSK cluster type, exact Kafka/MSK/EKS/client versions, UTC time, approved role, source command, sanitized network/identity mapping, expected and observed result, Kafka client SLO, owner, abort/rollback and independent reviewer. Mark **Pending** until executed. Any network mutation, chargeable deployment, secret association or fault injection is **Tabletop** until approved.

## 14. Read-only AWS/EKS verification script

Save as `verify-ch71.sh`. Set `AWS_PROFILE`, `AWS_REGION`, `MSK_ARN` and `EKS_NS` in the approved environment.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:?Set approved AWS_PROFILE}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${MSK_ARN:?Set provisioned MSK cluster ARN}"
EKS_NS="${EKS_NS:-kafka-clients}"
echo '[1/9] AWS identity'; aws sts get-caller-identity
echo '[2/9] MSK clusters'; aws kafka list-clusters-v2 --region "$AWS_REGION"
echo '[3/9] MSK cluster'; aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[4/9] Bootstrap brokers'; aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[5/9] EKS context'; kubectl config current-context
echo '[6/9] EKS client Pods'; kubectl -n "$EKS_NS" get pods -o wide
echo '[7/9] ServiceAccounts'; kubectl -n "$EKS_NS" get serviceaccount
echo '[8/9] NetworkPolicy'; kubectl -n "$EKS_NS" get networkpolicy
echo '[9/9] Events'; kubectl -n "$EKS_NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only AWS/EKS inventory only.'
echo 'NOT PROVEN: broker reachability, IAM/TLS Kafka auth, client correctness, DR or security review.'
```

`get-bootstrap-brokers` and cluster details can reveal internal endpoint metadata: sanitize before sharing. For serverless MSK, adjust inventory to supported cluster APIs and do not assume node-level fields.

## 15. Twelve troubleshooting scenarios

### Scenario 1 — EKS Pod cannot resolve bootstrap DNS

**Diagnosis:** Check VPC DNS settings, CoreDNS, network path and broker endpoint region. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 2 — Bootstrap succeeds but metadata brokers fail

**Diagnosis:** Check all advertised broker endpoints, security groups, routing and DNS. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 3 — IAM authentication denied

**Diagnosis:** Inspect SASL mechanism, IAM role credentials, action/resource ARNs and trust. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 4 — IRSA or Pod Identity credentials unavailable

**Diagnosis:** Inspect service account annotations/associations, role trust, SDK support and token flow. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 5 — SCRAM handshake fails

**Diagnosis:** Check Secrets Manager association, username/password, KMS and mechanism. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 6 — TLS handshake fails

**Diagnosis:** Inspect CA trust, hostname validation, clock and endpoint type. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 7 — Cross-VPC clients time out

**Diagnosis:** Review connectivity mode, routing, DNS, security groups and supported topology. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 8 — Security group allows too broad access

**Diagnosis:** Restrict to approved sources, record risk and review blast radius. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 9 — Broker CPU or network saturation

**Diagnosis:** Inspect MSK metrics, partition skew, client rates and broker sizing. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 10 — Storage pressure rises

**Diagnosis:** Inspect retention, partition count, storage scaling capability and alert thresholds. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 11 — Kafka client throttling or disconnects

**Diagnosis:** Inspect broker connections, authentication, quotas, retries and application latency. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

### Scenario 12 — CloudWatch green but applications fail

**Diagnosis:** Validate synthetic EKS TLS/IAM produce-consume, group lag and event correctness. Correlate EKS Pod identity, DNS, routes, broker advertised addresses, SG/NACL, listener TLS/SASL, IAM/SCRAM authorization, MSK broker metrics and client retry/lag. **Response:** Freeze unsafe changes, preserve redacted evidence, restore least privilege and verified connectivity, then reconcile synthetic event IDs. **Exit:** Measured or explicitly tabletop recovery, owner approval and RCA.

## 16. Eight production runbooks

### Runbook A — EKS-to-MSK connectivity outage

**Trigger/response:** Trace Pod DNS, node networking, VPC routing, security groups, listener and bootstrap metadata. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook B — MSK IAM authorization incident

**Trigger/response:** Inspect role trust, policy resource patterns, auth logs and least-privilege recovery. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook C — SCRAM/TLS authentication incident

**Trigger/response:** Review Secrets Manager association, cert trust, endpoint and client config. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook D — Cross-VPC access failure

**Trigger/response:** Check managed connectivity eligibility, routes, DNS and network ACLs. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook E — Broker capacity and storage pressure

**Trigger/response:** Inspect CPU, throughput, partitions, storage, retention and supported scaling. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook F — MSK maintenance and version upgrade

**Trigger/response:** Check AWS support matrix, change window, client SLO and rollback constraints. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook G — Security exposure or credential compromise

**Trigger/response:** Contain access, rotate, preserve redacted logs and escalate. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

### Runbook H — Independent MSK operational acceptance

**Trigger/response:** Verify IAM/TLS, EKS client smoke, CloudWatch, DR, change control and signoff. **No-go:** broad network exposure, missing encryption, leaked credentials, unsafe RF/minISR, unreviewed chargeable MSK change or unsupported rollback. **Exit:** Healthy MSK and EKS client paths, authenticated produce/consume, restored SLO, sanitized incident evidence and independent approval.

## 17. Evidence package

```text
evidence-ch71/
  msk-architecture-decision.md
  aws-account-region-identity.md
  msk-cluster-inventory.md
  cluster-az-broker-configuration.md
  vpc-subnet-route-map.md
  eks-to-msk-packet-path.md
  security-groups-review.md
  bootstrap-listener-inventory.md
  iam-policy-action-resource-matrix.md
  eks-irsa-pod-identity-trust.md
  tls-kms-encryption.md
  scram-secrets-manager.md
  kafka-acl-iam-differences.md
  dns-advertised-brokers.md
  multi-vpc-connectivity.md
  cloudwatch-monitoring.md
  open-monitoring-jmx.md
  quotas-partitions-storage.md
  change-upgrade-dr-plan.md
  client-smoke-and-independent-acceptance.md
  scorecard.md
```

Each artifact needs UTC time, AWS region, exact supported deployment type/version, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, owner, abort/rollback and reviewer.

## 18. 100-point MSK production-readiness assessment

| Domain | Points | Critical |
|---|---:|---|
| MSK architecture and AWS responsibility boundary | 15 | Yes |
| VPC/EKS connectivity and DNS | 20 | Yes |
| IAM/IRSA/Pod Identity and TLS/SCRAM security | 25 | Yes |
| Monitoring, capacity and Kafka durability | 15 | Yes |
| Change management, DR and incident runbooks | 15 | Yes |
| Synthetic EKS client correctness | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** unapproved public exposure, broad IAM credentials, leaked secret, TLS validation disabled, fabricated live smoke, unreviewed data-impacting change or absent independent security review.

## 19. References and next chapter

**References:** [Amazon MSK Developer Guide](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [MSK IAM Access Control](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control.html), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 072 — Amazon MSK Provisioning, Broker Configuration, Storage Scaling and Kafka Cluster Operations.

---

**Verification boundary:** Chapter published; live EKS-to-MSK network testing, IAM/TLS Kafka client smoke, capacity validation and independent technical/security review remain Pending.
