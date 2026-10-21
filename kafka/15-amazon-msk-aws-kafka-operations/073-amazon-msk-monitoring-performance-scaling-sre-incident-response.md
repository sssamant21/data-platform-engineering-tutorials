# Chapter 073 — Amazon MSK Monitoring, Performance, Scaling and SRE Incident Response

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 15 — Amazon MSK and AWS Kafka Operations (3/5)  
**Primary application platform:** Amazon EKS / Kubernetes Kafka clients  
**Kafka platform:** Amazon MSK provisioned; serverless differences explicitly noted  
**Prerequisites:** Chapters 001–072, AWS CloudWatch, EKS, Kafka performance and SLOs  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter uses read-only inventory and tabletop incident drills by default. Do not induce broker failures, delete topics, change Kafka configuration, scale MSK, weaken IAM/TLS, expose exporter endpoints or alter production alert routing without approval. MSK metrics, dimensions, monitoring tiers and features vary by cluster type and region; verify in the current AWS service documentation.

## 1. Mission and learning objectives

Build an end-to-end operational monitoring and incident response program for Amazon MSK with EKS Kafka clients. Connect CloudWatch broker health to Kafka replication and producer/consumer correctness, design useful SLOs and alerting, distinguish capacity bottlenecks from client/network failures, and prepare safe scaling decisions and incident runbooks.

By completion, readers can diagnose broker CPU/network/storage saturation, ISR degradation, consumer lag, IAM/TLS errors, CloudWatch gaps and change-related regressions, while keeping publication, live validation and independent security review separate.

## 2. Production observability architecture

```text
 EKS producers / consumers
   |  latency, retries, lag, errors, event ledger
   v
 VPC DNS / TLS / IAM / broker advertised endpoints
   |
 Amazon MSK brokers and Kafka partitions
   |      |           |
 CloudWatch metrics  broker logs  Open Monitoring (if supported)
   |      |           |
   +------+-----------+
          |
  SLO dashboards + alerts + on-call
          |
  incident command -> mitigation -> recovery -> RCA
```

**Critical principle:** MSK control-plane `ACTIVE`, healthy CloudWatch CPU and green EKS Pods do not prove Kafka application availability or event correctness. Always correlate authenticated synthetic produce/consume, consumer lag and a unique event-ID ledger.

## 3. Monitoring modes and availability

| Mode | What it provides | Operational constraint |
|---|---|---|
| CloudWatch default metrics | supported cluster/broker metrics | metric set depends on deployment type |
| Enhanced monitoring | additional broker/topic dimensions where supported | higher cost/cardinality |
| Open Monitoring | supported JMX/Node exporter metrics for provisioned clusters | secure VPC reachability and scrape limits |
| Broker log delivery | authentication, request and broker events | redaction, retention and ingestion cost |
| EKS client telemetry | producer/consumer metrics and traces | application instrumentation required |

Do not assume serverless supports all provisioned broker-level metrics or exporter features. Inspect actual `AWS/Kafka` metrics before designing alerts.

## 4. Read-only AWS/EKS metric discovery

```bash
export AWS_PROFILE=YOUR_APPROVED_PROFILE
export AWS_REGION=YOUR_REGION
export MSK_ARN='arn:aws:kafka:REGION:ACCOUNT:cluster/NAME/UUID'
aws sts get-caller-identity
aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
aws logs describe-log-groups --region "$AWS_REGION"
kubectl config current-context
kubectl -n kafka-clients get pods -o wide
```

Inspect real metric dimensions and periods before constructing `get-metric-data` requests. CloudWatch metrics can have publication delays and sparse series; absence of a datapoint is not proof of zero.

## 5. Broker health metrics and interpretation

| Metric family | Signal | First investigation |
|---|---|---|
| CPU | broker processing saturation | hot partitions, request load, broker type |
| Network in/out | throughput and replication pressure | ingress/egress, client fetch, replica catch-up |
| Storage utilization | capacity and log growth | retention, compaction, skew, autoscaling |
| Under-replicated partitions | ISR cannot keep pace | broker/disk/network/leader health |
| Offline partitions | availability risk | leader election and broker state |
| Leader count | skew and broker pressure | partition assignment and hot leaders |
| Request latency/queues | client SLO risk | disk, network, CPU, request throttling |
| Connections | client churn/limits | TLS/IAM failures, client retry storm |
| Consumer lag | freshness/processing | group rebalance, slow processing, hot partitions |

Metric names and dimensions must be confirmed from the current MSK metric catalog for the selected deployment and monitoring level.

## 6. SLOs, SLIs and alert design

Suggested SLI definitions (thresholds are **illustrative only**):

- **Producer availability:** successful acknowledged synthetic writes / attempted synthetic writes.
- **Producer latency:** end-to-end P95/P99 for acknowledged writes.
- **Consumer freshness:** event creation to successful processing time, with clock-skew handling.
- **Event correctness:** expected synthetic event IDs reconciled against observed outputs, duplicates and missing IDs.
- **Kafka durability risk:** under-replicated/offline partitions and minISR breaches.
- **Authentication health:** rate of IAM/SASL/TLS failures, grouped by principal/client type.

Example **policy exercise**, not a universal production SLO: 99.9% successful synthetic writes over 30 days. Choose thresholds with application owners and error budget. Alerts should combine **impact** (client error/latency/lag) and **cause** (broker CPU, ISR, disk) to avoid alert floods.

## 7. CloudWatch dashboard and alarm engineering

Create dashboards from actual cluster dimensions and metric availability. Use broker-level views for imbalance; aggregate metrics can hide a single hot broker. Include EKS producer/consumer telemetry and a runbook link per alert.

```bash
# Read-only alarm inventory:
aws cloudwatch describe-alarms --region "$AWS_REGION"
aws cloudwatch list-dashboards --region "$AWS_REGION"
```

Recommended alarms: sustained under-replicated/offline partitions, disk pressure, request latency regression, broker CPU/network saturation, consumer lag/freshness, client authentication errors and failed cluster operations. Avoid unbounded metric cardinality and account for CloudWatch cost.

## 8. Performance diagnosis decision tree

```text
 Client latency/timeout?
    |
    +-- DNS/TLS/IAM failure? -> network/auth runbook
    |
    +-- Kafka URP/offline partitions? -> replication/availability runbook
    |
    +-- Broker CPU/network/disk saturated? -> hot partition/capacity runbook
    |
    +-- Consumer lag only? -> group/processing/downstream runbook
    |
    +-- Metrics missing? -> monitoring-tier/log/collector runbook
    |
    +-- No obvious infrastructure issue?
           -> trace client retries, event IDs, partition keys and SLO
```

Never increase broker count before distinguishing hot partition keys, uneven leaders, downstream consumer slowness and broker resource limits. Adding brokers alone does not guarantee replica/leader redistribution.

## 9. Capacity and scaling decision framework

| Observation | Candidate action | Required safety gate |
|---|---|---|
| CPU/network saturation | broker type/count, producer batching | client SLO, ISR, cost |
| Partition/leader skew | controlled reassignment | ISR and data durability |
| Storage growth | retention review, supported expansion/autoscaling | retention policy, billing |
| Consumer lag | optimize consumer/downstream, add parallelism if partitions permit | ordering and correctness |
| Client auth storm | fix credential or policy issue | least privilege |
| Replication backlog | restore broker/network/disk health | minISR and fault budget |

Scaling MSK is an AWS control-plane operation with eligibility, cooldown, supported types and potentially rolling effects. Treat changes as production maintenance, not instant fixes.

## 10. EKS client metrics and troubleshooting

Instrument Kafka clients for request errors, retries, batch size, compression, delivery latency, queue time, consumer poll duration, rebalances, lag and processing time. Correlate with Kubernetes Pod restarts, CPU throttling, memory pressure, DNS and node networking.

A producer `send()` invocation does not equal acknowledged durable delivery. For synthetic tests, wait for acknowledgments, record partition/offset, then verify consumer processing and event-ID reconciliation.

## 11. Incident command and recovery

1. Establish severity from client SLO impact and data correctness, not only MSK cluster status.
2. Freeze unsafe broker/cluster operations if ISR/quorum or storage is degraded.
3. Identify affected regions, EKS namespaces, IAM roles, topics, groups and tenants.
4. Capture UTC timeline, CloudWatch dimensions, MSK operation history, logs and synthetic event ledger.
5. Choose least-risk mitigation: fix auth/network, relieve hot client, restore capacity or escalate AWS support.
6. Validate producer/consumer recovery, lag catch-up, ISR and data integrity.
7. Record RTO/RPO observations, communication timeline, RCA and follow-up owner.

## 12. Twenty hands-on MSK monitoring and SRE labs

### Lab 01 — Define MSK SLO and error budget

**Objective and procedure:** Specify producer availability/latency, consumer freshness, durability and synthetic event correctness.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 02 — Inventory MSK monitoring level

**Objective and procedure:** Record cluster type, CloudWatch basic/enhanced metrics, Open Monitoring and broker logs.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 03 — Inspect CloudWatch dimensions

**Objective and procedure:** Discover actual AWS/Kafka metrics by cluster/broker/topic, period and region.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 04 — Build broker CPU dashboard

**Objective and procedure:** Track CPU user/system/idle, peak and imbalance by broker.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 05 — Build network saturation dashboard

**Objective and procedure:** Correlate BytesIn/Out, network errors, replication and client egress.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 06 — Build disk/storage dashboard

**Objective and procedure:** Review KafkaDataLogsDiskUsed, storage utilization, IOPS and throughput where exposed.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 07 — Monitor ISR and offline partitions

**Objective and procedure:** Capture UnderReplicatedPartitions, OfflinePartitionsCount and minISR risk.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 08 — Monitor leader/partition skew

**Objective and procedure:** Track leaders and partition count per broker; map hot partitions.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 09 — Monitor producer request latency

**Objective and procedure:** Correlate request queues, throttle, client acks, retries and end-to-end latency.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 10 — Monitor consumer lag and freshness

**Objective and procedure:** Use supported MSK lag metrics and independent EKS client consumer telemetry.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 11 — Review connection and auth errors

**Objective and procedure:** Correlate broker connections, TLS/SASL/IAM errors and EKS credential expiry.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 12 — Review broker logs and retention

**Objective and procedure:** Check CloudWatch Logs/S3/Firehose delivery options, redaction and cost.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 13 — Review Prometheus Open Monitoring

**Objective and procedure:** Assess JMX/Node exporters, VPC access, scraping, labels and cardinality.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 14 — Review EKS client telemetry

**Objective and procedure:** Correlate Pod restarts, CPU throttling, DNS, network, retries and Kafka lag.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 15 — Build alert routing and burn rates

**Objective and procedure:** Map alerts to SLO burn, on-call ownership, deduplication and runbook.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 16 — Analyze throughput bottleneck

**Objective and procedure:** Separate producer, broker CPU/network/disk, hot partition and consumer causes.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 17 — Review scaling decision

**Objective and procedure:** Compare broker count/type, storage, reassignment, client tuning and costs.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 18 — Rehearse broker/AZ incident

**Objective and procedure:** Tabletop ISR, availability, lag, RTO, stakeholder communications and AWS support.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 19 — Rehearse authentication incident

**Objective and procedure:** Tabletop IAM/TLS/SCRAM denial and credential/network isolation.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

### Lab 20 — Complete operational acceptance

**Objective and procedure:** Score dashboards, alert tests, runbooks, SLO evidence and independent review.

**Expected evidence:** AWS region, cluster type and version, EKS context, UTC time, source command/query, actual metric name/dimensions/period, baseline, alert/SLO or failure hypothesis, expected/observed result, client event IDs, owner, abort/rollback and reviewer. Mark **Pending** until executed. Fault injection and scaling remain **Tabletop** without explicitly approved disposable infrastructure.

## 13. Read-only monitoring verification script

Save as `verify-ch73.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:?Set approved AWS_PROFILE}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${MSK_ARN:?Set approved MSK cluster ARN}"
NS="${EKS_NS:-kafka-clients}"
echo '[1/10] Identity'; aws sts get-caller-identity
echo '[2/10] Cluster'; aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[3/10] MSK operations'; aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[4/10] Metric catalog'; aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
echo '[5/10] Alarms'; aws cloudwatch describe-alarms --region "$AWS_REGION"
echo '[6/10] Dashboards'; aws cloudwatch list-dashboards --region "$AWS_REGION"
echo '[7/10] Log groups'; aws logs describe-log-groups --region "$AWS_REGION"
echo '[8/10] EKS context'; kubectl config current-context
echo '[9/10] Client Pods'; kubectl -n "$NS" get pods -o wide
echo '[10/10] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only monitoring inventory only.'
echo 'NOT PROVEN: Kafka client SLO, alarm firing, broker performance, RTO or independent review.'
```

Inventory may be incomplete due to IAM permissions or pagination. A script exit of zero is not evidence of operational readiness.

## 14. Twelve troubleshooting scenarios

### Scenario 1 — Broker CPU spikes and client latency rises

**Diagnosis:** Inspect hot partitions, request queues, network, GC and producer batch/retry patterns. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 2 — UnderReplicatedPartitions grows

**Diagnosis:** Inspect broker state, disk/network, replication lag, broker operation and ISR. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 3 — OfflinePartitionsCount nonzero

**Diagnosis:** Check leader availability, broker health and cluster metadata. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 4 — Storage free space collapses

**Diagnosis:** Inspect retention, compaction, broker imbalance, autoscaling and supported expansion. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 5 — Producer timeouts but brokers healthy

**Diagnosis:** Check EKS network, IAM/TLS, request size, acks, retries and throttling. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 6 — Consumer lag increases sharply

**Diagnosis:** Check consumer processing, partition skew, rebalances, fetch and downstream dependency. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 7 — Broker traffic unbalanced

**Diagnosis:** Check partition leaders, hot keys, replica placement and reassignment plan. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 8 — CloudWatch metric missing

**Diagnosis:** Check cluster type, monitoring tier, dimension, period and publishing delay. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 9 — Prometheus scrape fails

**Diagnosis:** Inspect exporter support, security group, VPC routing, TLS and service discovery. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 10 — TLS/SASL/IAM errors spike

**Diagnosis:** Check certificate expiry, role trust, SDK credentials, auth policy and denied actions. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 11 — Scaling change degrades availability

**Diagnosis:** Pause; inspect cluster operation, ISR, client SLO and recovery gates. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

### Scenario 12 — MSK green but events missing

**Diagnosis:** Reconcile synthetic event IDs, producer ack, consumer offset and data retention. Correlate UTC CloudWatch series, MSK operation state, EKS client errors, TLS/IAM, Kafka ISR/minISR, partition placement, storage and event-ID ledger. **Response:** Stop unsafe changes, preserve redacted evidence, choose the least-risk mitigation and communicate impact. **Exit:** Restored SLO, measured or explicitly tabletop recovery, RCA and independent reviewer.

## 15. Eight production runbooks

### Runbook A — Broker saturation and high latency

**Trigger/response:** Correlate CPU/network/disk/partition skew, EKS clients and approved scaling. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook B — ISR degradation or offline partitions

**Trigger/response:** Protect RF/minISR, stop rolling operations, escalate and verify leader recovery. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook C — Storage exhaustion risk

**Trigger/response:** Inspect retention, CloudWatch, broker skew, autoscaling and supported storage expansion. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook D — Consumer lag and freshness incident

**Trigger/response:** Identify slow groups, rebalances, downstream pressure and end-to-end freshness. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook E — EKS-to-MSK authentication/network outage

**Trigger/response:** Trace Pod identity, DNS, advertised brokers, SG, TLS and IAM/SCRAM. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook F — Observability blind spot

**Trigger/response:** Check metric tier, CloudWatch ingestion, exporters, log delivery and alert gaps. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook G — Scaling or upgrade incident

**Trigger/response:** Stop unsafe change, check AWS operation, ISR, client SLO and recovery. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

### Runbook H — SRE incident command and RCA

**Trigger/response:** Set severity, timeline, stakeholder updates, RTO/RPO, evidence and follow-up. **No-go:** unknown broker state, lost minISR, missing client correctness, exposed credentials, unsupported scaling or unapproved fault injection. **Exit:** Kafka durability, authenticated client success, lag catch-up, restored SLO, sanitized evidence and owner approval.

## 16. Evidence package

```text
evidence-ch73/
  slo-error-budget.md
  monitoring-tier-inventory.md
  cloudwatch-metric-dimensions.md
  broker-cpu-dashboard.md
  broker-network-dashboard.md
  storage-dashboard.md
  isr-offline-partitions.md
  leader-partition-skew.md
  producer-latency.md
  consumer-lag-freshness.md
  connection-auth-failures.md
  broker-log-delivery.md
  prometheus-open-monitoring.md
  eks-client-telemetry.md
  alerts-burn-rate.md
  throughput-root-cause.md
  scaling-decision.md
  broker-az-incident-tabletop.md
  auth-incident-tabletop.md
  independent-operations-acceptance.md
  scorecard.md
```

Every artifact must include UTC time, AWS region, exact cluster/monitoring type, expected/observed result, **Live** vs **Tabletop**, sanitized metrics, owner, rollback/abort and independent reviewer.

## 17. 100-point SRE monitoring and incident assessment

| Domain | Points | Critical |
|---|---:|---|
| MSK monitoring architecture and metric accuracy | 20 | Yes |
| Broker replication, CPU/network/storage dashboards | 20 | Yes |
| Client SLO, freshness and event correctness | 20 | Yes |
| Alert design, logs and Prometheus integration | 15 | Yes |
| Performance, scaling and capacity decisions | 10 | Yes |
| Incident response, RTO/RPO and RCA | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** fabricated live evidence, ignored data correctness gap, unreviewed scaling, exposed credentials, missing ISR risk response or absent independent review.

## 18. References and next chapter

**References:** [Amazon MSK Monitoring](https://docs.aws.amazon.com/msk/latest/developerguide/monitoring.html), [Amazon MSK Developer Guide](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 074 — Amazon MSK Security, Multi-VPC Connectivity, Disaster Recovery and Production Change Management.

---

**Verification boundary:** Chapter publication proves document availability only. Live CloudWatch dashboard validation, alert firing, authenticated EKS Kafka smoke, scaling, incident drills and independent technical/security review remain Pending.
