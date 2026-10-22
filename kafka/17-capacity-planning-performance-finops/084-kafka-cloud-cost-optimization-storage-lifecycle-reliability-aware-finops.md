# Chapter 084 — Kafka Cloud Cost Optimization, Storage Lifecycle and Reliability-Aware FinOps

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 17 — Capacity Planning, Performance and FinOps (4/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS, with Amazon MSK provisioned/serverless comparison  
**Prerequisites:** Chapters 001–083; Kafka retention, broker metrics, AWS billing and Kubernetes storage  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** FinOps is not a justification for unapproved data deletion, weaker replication, reduced minISR, premature retention, storage downsizing or loss of Kafka replay/recovery. Use read-only inventory and offline models. No cost estimate is a live quote; validate region/date/service-specific prices before approving changes.

## 1. Mission and outcomes

Optimize Kafka total cost of ownership (TCO) while preserving durability, availability, recovery and data governance. Attribute compute, provisioned storage, replication, AZ/network transfer, tiered storage, consumers, Kafka Connect and operations to workloads. Compare Strimzi on EKS with Amazon MSK options using measured demand, cost drivers and reliability reserves.

By completion, readers can construct a cost allocation model, identify safe retention and storage lifecycle opportunities, assess rightsizing without violating SLO, and implement cost anomaly governance with independent approval.

## 2. Kafka FinOps cost architecture

```text
Application producers / Kafka Connect / CDC
               |
      compressed ingress bytes
               |
    partition leaders + RF replicas
       |               |
 broker CPU/RAM     PVC/EBS/IOPS
       |               |
 AZ placement       log retention/compaction
       +-------+-------+
               |
    consumers / cross-AZ / cross-region
               |
        network transfer costs
               |
  Strimzi/EKS operations OR Amazon MSK
               |
      FinOps allocation + budget alerts
               |
    SLO, ISR, replay, audit and approval
```

Total cost includes more than broker instance hours. A cheaper configuration that breaks recovery, consumer freshness or patient-data retention is not an optimization.

## 3. Cost data contract

| Cost driver | Measurement | Attribution |
|---|---|---|
| Broker compute | instance/node hours, CPU/RAM allocation | KafkaNodePool/team |
| Storage | provisioned GiB-month, IOPS/MBps tiers | PVC/topic estimates |
| Replication | RF, follower traffic, recovery | topic and AZ |
| Network | cross-AZ, inter-region, Internet egress | topic/consumer/connector |
| Retention | retention.ms/bytes, compaction | topic owner |
| Tiered storage | remote GiB, requests, retrieval | eligible topics |
| Kafka Connect | worker CPU, connector traffic | pipeline |
| MSK | broker/serverless pricing dimensions | cluster/account |
| Operations | on-call, upgrades, backup/recovery | platform cost center |

Use official cloud cost exports and measured Kafka telemetry; avoid treating estimated per-topic allocation as exact billing.

## 4. Reliability-aware optimization constraints

**Non-negotiable gates:** KRaft quorum, RF/minISR, AZ placement, acknowledged event correctness, replay and regulatory retention, producer P99, consumer freshness, RPO/RTO, security and approved change windows.

A FinOps proposal must include before/after baseline, failure-mode capacity, estimated savings, SLO impact, rollback or forward-fix and data-owner signoff. Retention reduction and data expiration are generally not reversible.

## 5. Compute and broker rightsizing

Measure CPU, heap, page cache, disk IOPS/throughput, network, request-handler saturation and partition leader skew at peaks. Compare alternative node-pool sizes or MSK broker classes using the same durability configuration and failure reserve.

Avoid "average CPU is low, halve brokers" logic. A broker/AZ failure may consume spare capacity needed for ISR recovery.

## 6. Storage lifecycle and retention

For compressed ingest \(r\) MiB/s, retention \(T\) seconds and RF:

\[
S_{replicated}\approx rT\,RF/1024\quad\text{GiB}
\]

This ignores compaction, segment/index overhead, recovery space, skew and retention.bytes. Reducing retention changes the time available for consumer replay and incident recovery. Every topic needs a data owner, approved policy and lineage review.

**Compacted topics:** Cleaner activity and key churn govern physical savings. Tombstones, dirty ratio, segment rolling and cleaner I/O can delay reclamation. Do not infer savings solely from logical retention settings.

## 7. Cross-AZ and cross-region network economics

Replication traffic is roughly ingress × (RF-1) in steady state before overhead/retries, but **billable** transfer depends on replica placement, clients, AWS service rules and region. Consumer fan-out, Kafka Connect and MirrorMaker can dominate traffic.

Moving replicas into one AZ to save transfer cost can undermine availability. Quantify both cost and AZ-loss risk.

## 8. Tiered storage tradeoffs

Check Kafka/MSK distribution and version support, local retention semantics, remote object-storage API charges, retrieval/egress, recovery latency, cache misses, data protection and monitoring. Tiered storage may lower local disk needs but can raise request costs or extend replay/recovery time.

Do not claim tiered storage is universally available in Strimzi or all MSK offerings.

## 9. MSK provisioned, serverless and EKS comparisons

**Strimzi/EKS:** account for EC2 nodes, EBS/PVC, load balancing, observability, support, upgrades, operator work and SRE labor.

**MSK provisioned:** broker hours, provisioned storage/throughput, transfer and managed operational characteristics.

**MSK Serverless:** different capacity, throughput, partition and billing dimensions; validate workload fit and current limits.

Use current official price sheets and region-specific quotes. AWS Savings Plans apply to eligible compute usage, not automatically to every MSK charge.

## 10. Cost allocation and unit economics

Useful metrics:
- Cost per **GiB successfully acknowledged and processed** by the application.
- Cost per million events with defined payload/replication semantics.
- Monthly cost per topic/team, with confidence ranges.
- Storage provisioned versus used and projected days-to-full.
- Cross-AZ transfer per useful GiB.
- SLO/error-budget cost of proposed optimization.

Use acknowledged unique event IDs to avoid rewarding apparent cheapness caused by dropped messages.

## 11. Read-only inventory

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pvc -A
kubectl get storageclass
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl top nodes
```

For AWS accounts with approved read-only permissions, use billing/Cost Explorer exports and MSK/EKS inventory. Never include account identifiers, credentials or patient payloads in public evidence.

## 12. Twenty Kubernetes-first FinOps labs

### Lab 01 — Establish Kafka cost baseline

**Procedure:** Collect 30-day cloud bills, Kafka topics, EKS/MSK clusters, account tags and owner mapping.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 02 — Allocate broker compute costs

**Procedure:** Map Strimzi node-pool CPU/memory or MSK broker hours to teams and workloads.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 03 — Allocate replicated storage costs

**Procedure:** Model compressed ingress, retention, RF, PVC provisioned GiB and storage class.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 04 — Analyze cross-AZ traffic

**Procedure:** Estimate follower replication, client ingress/egress, recovery and mirror traffic.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 05 — Analyze client and Connect egress

**Procedure:** Map consumer fan-out, Kafka Connect sinks, MirrorMaker and cross-region transfer.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 06 — Review Kafka retention policies

**Procedure:** Identify topic owners, retention.ms/bytes, compaction, replay and compliance requirements.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 07 — Review log compaction economics

**Procedure:** Model key churn, tombstones, cleaner I/O and effective storage reduction.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 08 — Assess tiered storage

**Procedure:** Compare local vs remote retention, feature compatibility, restore latency and API charges.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 09 — Review PVC provisioned versus used

**Procedure:** Compare capacity reservation, IOPS/throughput tier, CSI limits and growth.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 10 — Review broker rightsizing

**Procedure:** Compare observed CPU, heap, network, IOPS and peak/AZ-failure reserves.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 11 — Review partition overhead

**Procedure:** Estimate tiny partition metadata/segment overhead and controller resource costs.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 12 — Compare Strimzi and MSK TCO

**Procedure:** Model operations, support, compute, storage, data transfer, labor and availability.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 13 — Assess MSK provisioned versus serverless

**Procedure:** Compare applicable service limits, pricing dimensions and workload elasticity.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 14 — Evaluate commitment discounts

**Procedure:** Review Savings Plans/RI applicability for EKS compute and MSK service terms.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 15 — Identify nonproduction waste

**Procedure:** Find idle test clusters, excess retention, unused topics and forgotten workloads.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 16 — Build reliability-aware scenarios

**Procedure:** Compare baseline, +50% growth, broker failure and AZ-loss headroom.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 17 — Model cost per useful GiB

**Procedure:** Divide total monthly cost by acknowledged and processed application data.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 18 — Define FinOps alerting

**Procedure:** Design budget thresholds, forecast variance and anomaly ownership.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 19 — Design safe optimization rollout

**Procedure:** Use approval, canary, ISR, client SLO and rollback/forward-fix gates.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

### Lab 20 — Independent FinOps acceptance

**Procedure:** Review pricing sources, calculations, data protection, SLO, savings and signoff.

**Expected evidence:** UTC time, billing window, source/region/currency, pricing date, owner allocation, raw Kafka and cloud metrics, assumptions, forecast range, RF/minISR/AZ reserves, client SLO, data-retention approval, estimated savings, abort/rollback and independent reviewer. **Status: Pending** until executed. Cost-changing and retention actions remain **Tabletop** unless approved in isolated infrastructure.

## 13. Offline Kafka cost model

Save as `kafka_finops_model.py`. Rates are **user-supplied assumptions**, not current cloud prices.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("--broker-hours", type=float, required=True)
p.add_argument("--broker-usd-hour", type=float, required=True)
p.add_argument("--storage-gib-month", type=float, required=True)
p.add_argument("--storage-usd-gib-month", type=float, required=True)
p.add_argument("--network-gib", type=float, required=True)
p.add_argument("--network-usd-gib", type=float, required=True)
p.add_argument("--useful-gib", type=float, required=True)
args = p.parse_args()
vals = vars(args)
if any(v < 0 for v in vals.values()) or args.useful_gib <= 0:
    p.error("cost inputs must be nonnegative; useful GiB must be positive")
compute = args.broker_hours * args.broker_usd_hour
storage = args.storage_gib_month * args.storage_usd_gib_month
network = args.network_gib * args.network_usd_gib
total = compute + storage + network
print(json.dumps({
    "compute_usd": round(compute, 2),
    "storage_usd": round(storage, 2),
    "network_usd": round(network, 2),
    "modeled_total_usd": round(total, 2),
    "usd_per_useful_gib": round(total / args.useful_gib, 4),
    "warning": "Excludes support, ops, observability, taxes, discounts, IOPS and other charges"
}, indent=2))
```

Example with **illustrative rates only**:

```bash
python kafka_finops_model.py \
  --broker-hours 4320 --broker-usd-hour 0.30 \
  --storage-gib-month 12000 --storage-usd-gib-month 0.08 \
  --network-gib 5000 --network-usd-gib 0.01 \
  --useful-gib 3000
```

Expected modeled compute $1,296, storage $960, network $50, total $2,306, and $0.7687 per useful GiB. **Not an AWS price quote.**

## 14. Twelve FinOps failure scenarios

### Scenario 01 — Storage savings plan deletes required history

**Diagnosis:** Stop retention change, review legal/application retention and replay. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 02 — Reducing RF undermines availability

**Diagnosis:** Reject change; inspect minISR, AZ placement and durability contract. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 03 — Downsizing brokers causes P99 regression

**Diagnosis:** Review peak load, network/IOPS and failure-zone reserve. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 04 — Cross-AZ charges spike after rebalance

**Diagnosis:** Inspect replica/client placement, recovery traffic and transfer metering. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 05 — Compaction savings do not appear

**Diagnosis:** Review key churn, cleaner backlog, tombstones and segment roll. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 06 — Tiered storage costs exceed forecast

**Diagnosis:** Inspect API operations, retrieval, cache misses and egress. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 07 — MSK Serverless comparison omits limits

**Diagnosis:** Recheck workload, throughput, partitions, compatibility and current pricing. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 08 — Idle-topic detection flags active compliance data

**Diagnosis:** Require owner approval, audit, retention and downstream lineage. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 09 — Savings Plan incorrectly attributed to MSK

**Diagnosis:** Separate eligible EC2/EKS compute from managed Kafka charges. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 10 — Budget alert misses storage autoscaling

**Diagnosis:** Check cost tags, forecast windows and service-specific metrics. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 11 — Low cost per GiB hides data loss

**Diagnosis:** Reconcile acknowledged/processed unique events and SLO. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

### Scenario 12 — Price model uses stale rates

**Diagnosis:** Refresh official price source, region, date and taxes/discount assumptions. Correlate billing dimensions, retention/RF, Kafka ISR, AZ placement, PVC metrics, producer/consumer event correctness and SLO. **Response:** Block unsafe optimization, restore supported reversible settings or invoke data recovery, document impact and escalate. **Exit:** Reliable Kafka, valid cost attribution, reviewed savings and RCA.

## 15. Eight production runbooks

### Runbook A — Kafka cost anomaly response

**Trigger/actions:** Correlate billing dimensions with ingest, replication, retention, AZ and scaling. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook B — Retention optimization approval

**Trigger/actions:** Validate owner, legal hold, replay, restore and data deletion impact. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook C — Broker rightsizing change

**Trigger/actions:** Confirm P99, ISR, failure reserve, approved maintenance and rollback. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook D — Cross-AZ network optimization

**Trigger/actions:** Review rack placement, replication, consumer locality and availability. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook E — Tiered storage evaluation

**Trigger/actions:** Check compatibility, retrieval cost, recovery SLO and data lifecycle. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook F — Idle resource cleanup

**Trigger/actions:** Confirm topic/workload owners, evidence, approvals and recovery. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook G — FinOps forecast breach

**Trigger/actions:** Recompute scenarios, annotate pricing changes and escalate budget risks. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

### Runbook H — Quarterly cost/reliability review

**Trigger/actions:** Verify cost savings against SLO, event correctness and independent acceptance. **No-go:** missing data owner, destructive retention, reduced ISR/availability, unreviewed cloud costs, missing replay plan or compromised data correctness. **Exit:** Verified SLO, audited savings, preserved recovery and independent signoff.

## 16. Evidence package

```text
evidence-ch084/
  cost-baseline.csv
  compute-allocation.md
  storage-allocation.csv
  az-transfer-analysis.md
  consumer-connect-egress.md
  retention-policy-review.md
  compaction-economics.md
  tiered-storage-eligibility.md
  pvc-provisioned-used.md
  broker-rightsizing.md
  partition-overhead.md
  strimzi-vs-msk-tco.md
  msk-serverless-evaluation.md
  commitment-discounts.md
  nonproduction-waste.md
  reliability-scenarios.md
  cost-per-useful-gib.json
  budget-alerting.md
  safe-rollout-plan.md
  independent-finops-acceptance.md
  scorecard.md
```

Each artifact records UTC time, region, currency, pricing source/date, raw input, units, confidence, **Live** vs **Tabletop**, data owner, SLO/ISR risk, abort/rollback and reviewer.

## 17. 100-point reliability-aware FinOps assessment

| Domain | Points | Critical |
|---|---:|---|
| Cost inventory, attribution and price provenance | 20 | Yes |
| Retention, compaction and storage lifecycle | 20 | Yes |
| Compute, network and MSK/Strimzi TCO | 20 | Yes |
| Kafka durability, recovery and SLO protection | 20 | Yes |
| Forecast, anomaly alerts and change governance | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced. **Automatic Fail:** fabricated cost data, unapproved data deletion, weakening RF/minISR, unexplained missing events, missing owner authorization or absent independent review.

## 18. References and next chapter

**References:** [AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/).

**Next:** Chapter 085 — Kafka Enterprise Capacity, Performance and FinOps Acceptance Capstone.

---

**Verification boundary:** Publication proves document availability only. Live cost exports, retention tests, cloud pricing validation, scaling changes and independent technical/security review remain Pending.
