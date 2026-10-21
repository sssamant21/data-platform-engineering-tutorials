# Chapter 072 — Amazon MSK Provisioning, Broker Configuration, Storage Scaling and Kafka Cluster Operations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 15 — Amazon MSK and AWS Kafka Operations (2/5)  
**Primary client runtime:** Amazon EKS / Kubernetes  
**Kafka platform:** Amazon MSK provisioned (with serverless contrasts)  
**Prerequisites:** Chapters 001–071, AWS IAM/VPC/EKS, Kafka replication and operations  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Change safety:** All AWS/EKS commands below are read-only unless explicitly designated as an illustrative change. Provisioned MSK brokers, storage, logs and network services incur charges. Do not provision, update, scale, rotate keys or upgrade production without cost approval, quorum/ISR gates, backups/DR, client SLO baseline and an approved rollback/recovery plan. AWS MSK capabilities vary by region, Kafka version, broker family and cluster type: validate against current AWS documentation.

## 1. Mission and objectives

Plan and administer the lifecycle of Amazon MSK clusters with production-safe broker configuration, capacity planning, EBS storage growth, partition placement, monitoring, Kafka version upgrades and EKS client acceptance. Distinguish AWS-managed broker infrastructure from customer-managed Kafka data and application reliability.

**Exit outcomes:** choose supported deployment type, design VPC/AZ topology, size brokers and partitions, inspect custom configuration revisions, plan storage/broker scaling, detect unsafe changes, and independently assess a Kafka production change.

## 2. Responsibility model and architecture

```text
    Git / Terraform / approved change ticket
                       |
             MSK control-plane API
                       |
          Provisioned MSK Kafka cluster
          +--------------------------+
          | broker AZ-a  broker AZ-b |
          |      broker AZ-c         |
          | EBS volumes / RF / ISR   |
          +--------------------------+
                       |
           private VPC / TLS / IAM
                       |
              EKS Kafka clients
                       |
          CloudWatch + client metrics
                       |
        SRE change gates and acceptance
```

AWS manages supported broker provisioning and infrastructure lifecycle. Customers own Kafka topic partitioning, RF/minISR, retention, quotas, client correctness, authentication policy, capacity, costs, disaster recovery and application-level SLOs.

## 3. Provisioning decision matrix

| Decision | Provisioned | Serverless |
|---|---|---|
| Broker sizing | Choose supported broker family/type and count | Managed abstraction; validate quotas |
| Kafka configuration | Supported cluster configuration revision | More limited controls; verify support |
| Storage | Supported broker storage settings and expansion | Service-managed storage abstraction |
| Networking/auth | Check cluster mode and selected mechanisms | Check supported serverless mechanisms |
| Scaling | Explicit broker/storage operations with constraints | Managed within service limits |
| Operations | Broker metrics and supported node-level inventory | Different observability/API model |

**Important:** Standard/Express broker capabilities, available versions, EBS settings and APIs can differ. Never apply a provisioned-cluster API to a serverless cluster without checking support.

## 4. Read-only discovery

Use an approved AWS SSO profile, region and EKS context.

```bash
export AWS_PROFILE=YOUR_APPROVED_PROFILE
export AWS_REGION=YOUR_REGION
aws sts get-caller-identity
aws kafka list-clusters-v2 --region "$AWS_REGION"
aws service-quotas list-service-quotas --service-code kafka --region "$AWS_REGION"
kubectl config current-context
kubectl -n kafka-clients get pods -o wide
```

After selecting an authorized **provisioned** cluster:

```bash
export MSK_ARN='arn:aws:kafka:REGION:ACCOUNT:cluster/NAME/UUID'
aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka list-nodes --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
```

Read the response's cluster type and configuration revision before proceeding. Sanitize cluster identifiers and private endpoints in shared evidence.

## 5. Broker and partition capacity engineering

Estimate **steady and peak ingress** (MiB/s), replication network amplification, consumer egress, retention days, partition count, partition leadership skew, storage overhead and failure-domain recovery budget.

Example **illustrative sizing**, not a broker recommendation:

```text
ingress = 25 MiB/s
retention = 3 days
replication factor = 3
logical retained bytes ≈ 25 × 86400 × 3 MiB
physical replicas ≈ logical bytes × 3 (before overhead)
recovery reserve = additional capacity for AZ/broker loss and catch-up
```

Kafka broker storage capacity is not the same as client logical retention. Include index/segment overhead, replication catch-up, log compaction and producer bursts. Plan CPU/network and partitions per broker separately; disk-only sizing is insufficient.

## 6. Custom MSK configuration lifecycle

MSK supports custom configuration revisions for supported provisioned clusters and properties. Capture current config ARN/revision and **effective Kafka settings** before proposing a change.

```bash
aws kafka list-configurations --region "$AWS_REGION"
# Replace with approved config ARN from the list:
aws kafka describe-configuration --arn CONFIG_ARN --region "$AWS_REGION"
aws kafka describe-configuration-revision --arn CONFIG_ARN --revision 1 --region "$AWS_REGION"
```

Review `num.partitions`, `default.replication.factor`, `min.insync.replicas`, `auto.create.topics.enable`, retention defaults and quotas only where supported. Cluster defaults do not override explicit topic configurations. A configuration update may roll brokers and can be constrained by Kafka version and MSK state.

## 7. Storage modes and expansion

MSK storage options vary by broker family and service release. For EBS-backed provisioned clusters, review broker volume size, storage throughput configuration, CloudWatch disk usage and supported update APIs.

**Storage expansion is not a generic reversible operation.** It may have service cooldowns, upper limits, billing impact and operational constraints. Never assume shrink is supported. Storage autoscaling requires appropriate Application Auto Scaling registration/policy and available metrics; monitor whether scaling actually occurs.

```bash
aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
aws application-autoscaling describe-scalable-targets --service-namespace kafka --region "$AWS_REGION"
aws application-autoscaling describe-scaling-policies --service-namespace kafka --region "$AWS_REGION"
```

Read-only checks do not establish that storage autoscaling is enabled or correctly configured; inspect actual targets, dimensions, policy and alarms.

## 8. Broker scaling and partition placement

Increasing broker count provides capacity but does **not** automatically guarantee balanced partition replicas, leadership or hot-key traffic. Review broker scaling eligibility, supported count increments, Kafka partition reassignment tooling, network/disk pressure and ISR recovery.

For scale-in, check all partitions and replicas, current leadership, broker drain/reassignment plan, disk utilization after removal and MSK API restrictions. Scale-in may be unsupported for particular cluster configurations; do not treat it as a routine reversible operation.

## 9. Broker type and Kafka version upgrades

MSK supports selected broker-type changes and Kafka upgrades according to release and configuration. Before changing:

1. Capture Kafka/MSK cluster version, broker type, configuration revision, authentication and client versions.
2. Check current AWS-supported source/target versions and upgrade restrictions.
3. Review KRaft/ZooKeeper architecture as applicable; do not assume controller architecture can be changed by a simple setting.
4. Validate client protocol, IAM/SASL libraries, schema and Streams/Connect compatibility.
5. Establish healthy RF/minISR, under-replicated partitions, storage/network headroom and SLO baseline.
6. Require maintenance approval, observed rollout checkpoints and recovery plan.
7. Verify Kafka event correctness and application latency after change.

Do not promise a Kafka downgrade or automatic rollback of a completed metadata/protocol upgrade.

## 10. EKS client acceptance

A successful MSK API response does not prove EKS client connectivity. Validate EKS service-account AWS identity, VPC/DNS and advertised broker endpoints, security groups, TLS certificate trust, IAM/SCRAM and topic/group permissions.

Use synthetic event IDs and capture:
- Producer success/acknowledgment, error/retry and latency.
- Consumer offset progress, lag, duplicate/missing event analysis.
- Broker ISR, leader movement, connections and CloudWatch metrics.
- Recovery time under approved **tabletop** fault cases.

## 11. Production change checklist

| Gate | Required evidence | Abort/no-go |
|---|---|---|
| Change approval | owner, window, cost and risk | missing approval |
| Service support | region/version/broker/storage compatibility | unsupported API |
| Kafka durability | RF/minISR, leaders and URP | degraded ISR |
| Capacity | CPU, network, disk, partition skew | insufficient headroom |
| Authentication | TLS/IAM/SCRAM, least privilege | auth regression |
| EKS smoke | producer/consumer event ledger | data gaps or SLO breach |
| Recovery | rollback feasibility and DR | no recovery plan |
| Observability | CloudWatch and client metrics | blind rollout |

## 12. Twenty hands-on MSK/EKS operational labs

### Lab 01 — Approve MSK provisioning charter

**Objective/procedure:** Record AWS account, region, cluster type, budget, VPC, Kafka version, RPO/RTO, tags and owners.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 02 — Check AWS identity and quotas

**Objective/procedure:** Use STS, Service Quotas and MSK API inventory to capture service limits and authorization.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 03 — Review deployment types

**Objective/procedure:** Compare provisioned Standard/Express broker options and serverless, validating regional support.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 04 — Design VPC/AZ topology

**Objective/procedure:** Map private subnets, security groups, DNS, cross-VPC constraints and EKS clients.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 05 — Validate encryption/authentication

**Objective/procedure:** Select TLS and IAM/SCRAM/mTLS supported by chosen cluster type; inspect KMS policy.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 06 — Design broker sizing

**Objective/procedure:** Model ingress/egress, partition density, replication traffic, CPU, network and storage.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 07 — Review broker count and rack spread

**Objective/procedure:** Inspect broker AZ distribution, RF/minISR and maintenance fault budget.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 08 — Review Kafka configuration

**Objective/procedure:** Inventory custom configuration ARN, revision, effective settings and restart impact.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 09 — Validate retention policies

**Objective/procedure:** Check topic cleanup.policy, retention.bytes/ms and delete versus compaction semantics.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 10 — Validate partition plan

**Objective/procedure:** Review partition count, consumer parallelism, leaders and future scale constraints.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 11 — Review storage modes

**Objective/procedure:** Compare supported provisioned EBS storage options and serverless storage abstraction.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 12 — Plan storage autoscaling

**Objective/procedure:** Inspect CloudWatch utilization, Application Auto Scaling target, ceiling and lag.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 13 — Review manual storage update

**Objective/procedure:** Assess supported API, cooldown, irreversibility and cost before any increase.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 14 — Plan broker scale out

**Objective/procedure:** Review update-broker-count support, capacity headroom and partition redistribution.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 15 — Plan broker scale in

**Objective/procedure:** Document eligibility, partition placement, ISR, disk pressure and change approvals.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 16 — Review broker type changes

**Objective/procedure:** Check supported instance transitions, rolling impact and version compatibility.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 17 — Review Kafka version upgrades

**Objective/procedure:** Inspect compatible versions, rolling upgrade restrictions, client compatibility and rollback.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 18 — Review EKS client smoke

**Objective/procedure:** Define IAM/TLS producer-consumer event ledger, latency, lag and failover acceptance.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 19 — Build CloudWatch alerting

**Objective/procedure:** Design broker CPU, network, disk, URP, connections, throttling and application SLO alerts.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

### Lab 20 — Complete production readiness

**Objective/procedure:** Reconcile cost, security, capacity, RTO/RPO, runbooks, approval and independent review.

**Validation and evidence:** Record approved AWS profile/account alias, region, MSK cluster type/version, EKS context, UTC timestamp, command or change plan, expected/observed state, RF/minISR, capacity/cost impact, client SLO, rollback/abort, owner and reviewer. Mark **Pending** until performed. Provisioning, scaling, upgrades and fault injection remain **Tabletop** unless explicitly authorized in an isolated paid lab.

## 13. Read-only acceptance script

Save as `verify-ch72.sh` and run with approved AWS identity, region, provisioned cluster ARN and EKS namespace.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:?Set approved AWS_PROFILE}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${MSK_ARN:?Set provisioned MSK cluster ARN}"
EKS_NS="${EKS_NS:-kafka-clients}"
echo '[1/10] AWS identity'; aws sts get-caller-identity
echo '[2/10] Cluster'; aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[3/10] Bootstrap'; aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[4/10] Broker inventory'; aws kafka list-nodes --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[5/10] Operations'; aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[6/10] Kafka configs'; aws kafka list-configurations --region "$AWS_REGION"
echo '[7/10] Metrics'; aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
echo '[8/10] EKS context'; kubectl config current-context
echo '[9/10] Client Pods'; kubectl -n "$EKS_NS" get pods -o wide
echo '[10/10] Client events'; kubectl -n "$EKS_NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only inventory only.'
echo 'NOT PROVEN: storage scaling, broker rebalancing, client correctness, DR or independent review.'
```

This script is not suitable for MSK serverless broker-node inspection. Do not mistake successful AWS API inventory for a passing Kafka production-readiness assessment.

## 14. Twelve troubleshooting scenarios

### Scenario 1 — CreateCluster fails with invalid subnets

**Diagnosis:** Check subnet AZ distinctness, CIDR, broker count and supported configuration. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 2 — Provisioning stuck or failed

**Diagnosis:** Inspect cluster state, events, quotas, IAM/KMS grants and AWS support escalation. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 3 — EKS clients cannot connect

**Diagnosis:** Check bootstrap type, SGs, DNS, routing, TLS and IAM/SCRAM. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 4 — Custom configuration rejected

**Diagnosis:** Check Kafka version compatibility, property validation and config revision. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 5 — Storage utilization exceeds threshold

**Diagnosis:** Review retention, partition distribution, expansion eligibility and alert response. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 6 — Autoscaling does not trigger

**Diagnosis:** Check target registration, CloudWatch metric, min/max and service limits. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 7 — Storage expansion cannot be rolled back

**Diagnosis:** Treat increase as capacity/cost commitment; review supported recovery options. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 8 — Broker scale-out leaves hot partitions

**Diagnosis:** Check leaders and reassignment; adding brokers alone does not redistribute all load. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 9 — Broker scale-in blocked

**Diagnosis:** Inspect partition replicas, disk headroom, broker availability and API constraints. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 10 — Broker update degrades ISR

**Diagnosis:** Pause change, check under-replicated partitions, network and client SLO. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 11 — Version upgrade has incompatible clients

**Diagnosis:** Check broker-client protocol, SASL/IAM library, configs and change gates. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

### Scenario 12 — Monitoring looks healthy but data is missing

**Diagnosis:** Compare synthetic event IDs, producer acks, consumer lag and retention. Correlate cluster operation state, AWS API errors, CloudWatch, Kafka ISR/minISR, broker placement, EKS network/auth and synthetic client SLO. **Response:** Stop unsafe changes, protect durability, preserve sanitized evidence, follow approved AWS-supported recovery and notify stakeholders. **Exit:** Measured or explicitly tabletop outcome, RCA, owner and reviewer.

## 15. Eight production runbooks

### Runbook A — MSK provisioning failure

**Trigger/response:** Inspect state, quotas, networking, encryption and CloudTrail; stop retries that incur cost. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook B — Broker saturation and partition skew

**Trigger/response:** Assess CPU, network, partitions, leaders, ISR and controlled reassignment. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook C — Storage pressure and expansion

**Trigger/response:** Review retention, disk alerts, supported resize/autoscaling and irreversibility. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook D — Broker count/type update

**Trigger/response:** Gate on supported API, RF/minISR, client SLO and rollback limitations. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook E — Kafka configuration change

**Trigger/response:** Review config revision, broker rollout impact, baseline and post-change smoke. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook F — Kafka version upgrade

**Trigger/response:** Validate AWS matrix, compatibility, backup/DR and no automatic downgrade assumption. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook G — EKS-to-MSK client outage

**Trigger/response:** Trace network, listener, IAM/TLS, DNS, advertised brokers and correctness. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

### Runbook H — Independent cluster acceptance

**Trigger/response:** Verify budget, security, capacity, SLO, fault domains, DR, evidence and signoff. **No-go:** unknown AWS region/type, unsupported change, unreviewed cost, lost Kafka durability, plaintext fallback, data deletion, missing DR or unsupported downgrade assumption. **Exit:** Stable MSK, Kafka ISR, EKS client event correctness, restored SLO, change audit and independent approval.

## 16. Evidence package

```text
evidence-ch72/
  provisioning-charter-budget.md
  identity-quotas.md
  deployment-type-decision.md
  vpc-subnet-az-topology.md
  tls-iam-scram-kms.md
  broker-capacity-model.md
  broker-rf-minisr.md
  kafka-configuration-revisions.md
  retention-compaction.md
  partition-plan.md
  storage-mode-review.md
  storage-autoscaling-review.md
  manual-storage-expansion-plan.md
  broker-scale-out-reassignment.md
  broker-scale-in-safety.md
  broker-type-change.md
  kafka-version-upgrade.md
  eks-synthetic-client-smoke.md
  cloudwatch-alerting.md
  independent-production-acceptance.md
  scorecard.md
```

Every artifact must include UTC time, exact AWS/Kafka/EKS versions, supported cluster type, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, risk, rollback/abort, owner and reviewer.

## 17. 100-point production operations assessment

| Domain | Points | Critical |
|---|---:|---|
| Architecture, quotas, networking and provisioning | 15 | Yes |
| Broker sizing, RF/minISR and partition placement | 20 | Yes |
| Configuration, retention and change control | 15 | Yes |
| Storage modes, autoscaling and expansion safety | 20 | Yes |
| Broker scaling, upgrade and recovery planning | 15 | Yes |
| EKS client smoke and observability | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated live evidence, unsupported storage shrink, unreviewed production cost, unsafe ISR, plaintext credentials, unapproved destructive operation or absent independent review.

## 18. References and next chapter

**References:** [Amazon MSK Developer Guide](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [MSK Storage](https://docs.aws.amazon.com/msk/latest/developerguide/msk-storage.html), [MSK Monitoring](https://docs.aws.amazon.com/msk/latest/developerguide/monitoring.html), [Apache Kafka](https://kafka.apache.org/documentation/), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html).

**Next:** Chapter 073 — Amazon MSK Monitoring, Performance, Scaling and SRE Incident Response.

---

**Verification boundary:** Chapter publication proves document availability only. Live provisioning, EKS client testing, broker/storage scaling, version upgrade and independent technical/security review remain Pending.
