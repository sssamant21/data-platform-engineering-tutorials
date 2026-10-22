# Chapter 085 — Kafka Enterprise Capacity, Performance and FinOps Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 17 — Capacity Planning, Performance and FinOps (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS, with Amazon MSK evaluation  
**Prerequisites:** Chapters 001–084; especially capacity (081), storage/partition (082), benchmarking (083), FinOps (084)  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This is an evidence-driven acceptance framework, not a certification of an existing Kafka cluster. Do not load-test production, weaken RF/minISR, reduce retention, alter PVCs, change KafkaNodePools, delete topics or resize MSK without approved change controls, data-owner signoff, replay/recovery evidence and SLO abort gates. Patient/PHI payloads are prohibited from labs.

## 1. Mission and exit criteria

Integrate **demand forecasting, storage and partition engineering, repeatable performance benchmarks, failure-zone capacity, cost allocation and reliability-aware FinOps** into one enterprise readiness decision.

The result is an auditable **capacity envelope**: maximum validated sustained and burst workload subject to Kafka durability, producer P99, consumer freshness, acknowledged event correctness, recovery objectives and cloud budget.

**Publication is not acceptance.** Each test must distinguish **Live**, **Tabletop**, **Not Applicable** and **Pending** with raw evidence and independent review.

## 2. Reference architecture and boundaries

```text
Business demand + workload owner + SLO + growth scenario
                         |
     compressed ingress / topics / partitions / RF
                         |
        +----------------+----------------+
        |                                 |
 KafkaNodePool broker/PVC              KRaft quorum
        |                                 |
 disk IOPS/MBps, CPU, memory          metadata, leaders
        |                                 |
        +-------------ISR/minISR----------+
                         |
       producer acks + consumer freshness
                         |
           synthetic event-ID ledger
                         |
      benchmarks, burst and failure reserve
                         |
   Strimzi/EKS versus MSK capacity alternatives
                         |
     retention, AZ transfer, storage, FinOps
                         |
       scorecard, risk register, SRE approval
```

Terraform/GitOps own approved infrastructure and CR desired state; Strimzi owns generated workloads; Kafka owns records and offsets. Git rollback does not reverse partition increases, data expiration, broker storage loss or offsets.

## 3. Acceptance matrix

| Critical gate | Minimum evidence | Reject when |
|---|---|---|
| Demand provenance | 30-day baseline, seasonality, peaks, missing data | estimates called measurements |
| Topic/partition design | RF/minISR, ordering, leader/replica skew | unsafe durability |
| Storage forecast | compressed ingress, retention, RF, overhead, skew | average-only sizing |
| Disk IOPS/throughput | volume latency, queues, caps, cleaner/recovery | unmeasured bottleneck |
| CPU/network | peak load, throttles, GC, cross-AZ traffic | unmodeled saturation |
| KRaft | controller quorum, metadata and partition churn | unhealthy quorum |
| Failure reserve | N-1 broker and AZ loss, ISR, recovery space | minISR violation |
| Benchmark | isolated workload, repeatable P99/throughput | missing raw evidence |
| Client correctness | unique acknowledged IDs matched to processed IDs | unexplained loss |
| Consumer freshness | lag and end-to-end processing delay | SLO violation |
| FinOps | region/date-priced compute, storage, transfer, ops | omitted material cost |
| Retention governance | topic-owner and replay/legal approval | unapproved deletion |
| Independent review | signed platform/SRE/security acceptance | missing signoff |

## 4. Forecast and capacity calculations

For compressed ingress \(r\) MiB/s, retention \(T\) seconds and RF:

\[
S_{logical}=rT/1024\quad\text{GiB},\qquad
S_{replicated}\approx S_{logical}RF.
\]

**Per-broker capacity is not** simply replicated GiB / brokers in a skewed cluster. Model actual partition assignment, index/segment overhead, compaction, reassignment, broker/AZ failure and reserve. Estimate disk **IOPS and MB/s separately**.

For consumer arrival rate \(\lambda\) and processing rate \(\mu\), backlog grows when \(\lambda>\mu\); when \(\mu>\lambda\), approximate drain time is backlog / \((\mu-\lambda)\). Verify with real event sizes and downstream bottlenecks.

**Illustrative sizing example, not live data:** 10 MiB/s compressed ingress, seven-day retention, RF=3, six brokers:
- Logical retained log ≈ 5,906.25 GiB.
- Replicated log ≈ 17,718.75 GiB.
- Balanced average ≈ 2,953.13 GiB/broker **before** skew, overhead and failure reserve.

Do not use these values to select production PVCs without workload-specific measurement.

## 5. Workload profiles and benchmark methodology

Define synthetic non-PHI payload distribution, key skew, producer acks/idempotence, partition count, RF/minISR, consumer group, client AZ and load generator resources. Run warm-up, steady, burst, cooldown and repeatability phases in an approved isolated environment.

Measure **offered**, **unique acknowledged**, and **unique processed** throughput separately. Include P95/P99 producer ack latency, consumer freshness, ISR, KRaft quorum, broker disk latency, network and generator saturation.

A high MB/s result with unexplained missing acknowledged events is an **automatic fail**.

## 6. N-1 broker and AZ failure reserve

Compute resource and placement headroom under single broker loss and an entire AZ loss. Check whether remaining ISR satisfies minISR and producer `acks=all`, whether controller quorum survives, and whether recovery traffic exceeds available disk/network bandwidth.

Use **tabletop** failure models unless separate isolated fault-injection approval exists. Document any failure mode that violates SLO/RPO/RTO; do not conceal it in averages.

## 7. FinOps and total cost of ownership

Include broker/EC2 hours, EBS/PVC provisioned storage and IOPS, cross-AZ/region transfer, consumer fan-out, Kafka Connect, observability, backup/recovery and SRE labor. For MSK, separate provisioned/serverless dimensions and use current region-specific pricing.

Compute cost per **useful GiB successfully acknowledged and processed**, not merely bytes sent. Retention reductions, RF changes and single-AZ placement are not acceptable savings if they violate durability, data governance or recovery.

## 8. Scaling and change decision matrix

| Proposed change | Capacity benefit | Reliability gate |
|---|---|---|
| Add Strimzi brokers | more CPU/network/disk distribution | placement, reassignment, ISR |
| Expand PVC | more local log storage | CSI support, backup, filesystem |
| Increase partitions | parallelism | irreversible count, key ordering, KRaft |
| Tune batching/compression | improved throughput | ack P99, CPU, client contract |
| Increase consumer replicas | processing parallelism | partition limit, downstream rate |
| Change retention | less retained storage | owner/legal/replay approval |
| Tiered storage | local storage relief | feature support, retrieval cost/RTO |
| MSK broker/storage scaling | managed capacity | quotas, maintenance, service limits |

Require before/after telemetry, reviewed risk, abort criteria and data correctness. Some changes require forward-fix rather than rollback.

## 9. Read-only Kubernetes/Strimzi preflight

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl get pvc -A
kubectl get storageclass
kubectl top nodes
```

Kafka topic and client checks require an authenticated client configuration. `kubectl top` needs metrics-server. A successful inventory is **not** evidence of benchmark or capacity acceptance.

## 10. Twenty enterprise capacity acceptance labs

### Lab 01 — Approve capacity capstone charter

**Procedure:** Define owners, environment, business SLO, cost ceiling, RPO/RTO, test isolation and signoffs.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Freeze versions and inventory

**Procedure:** Pin Kafka/Strimzi/EKS/MSK versions, Git SHA, KafkaNodePools, broker types, PVC and AZ topology.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Collect 30-day demand baseline

**Procedure:** Measure compressed bytes-in/out, event rate, peak, seasonality, topic growth and gaps.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Audit topic/partition design

**Procedure:** Record RF, minISR, partitions, leaders, cleanup.policy, retention and ordering contract.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Reconcile storage forecast

**Procedure:** Compare formula, actual PVC usage, segment/index overhead, skew and growth uncertainty.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Validate broker disk IOPS/throughput

**Procedure:** Correlate disk latency, IOPS, MBps, compaction, fetch and replication load.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Validate CPU, memory and network

**Procedure:** Check request handlers, GC, page cache, network saturation and AZ egress.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Validate KRaft and metadata headroom

**Procedure:** Inspect controller quorum, partition metadata churn and leadership health.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Assess N-1 broker capacity

**Procedure:** Model broker failure, ISR/minISR, recovery traffic, leader redistribution and spare disk.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Assess AZ-loss capacity

**Procedure:** Model rack placement, controller quorum, minISR, clients and recovery objectives.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Verify client correctness contract

**Procedure:** Specify unique acknowledged event IDs, processed IDs, duplicate/loss and freshness.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Validate benchmark reproducibility

**Procedure:** Review payload distribution, load generator isolation, warmup, repeats and P99.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Validate burst and backlog drain

**Procedure:** Model arrival/service rate, peak backlog, consumer parallelism and recovery time.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Compare scaling proposals

**Procedure:** Evaluate Strimzi KafkaNodePool/PVC and MSK broker/storage changes and rollback limits.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Reconcile cloud cost allocation

**Procedure:** Trace broker compute, PVC/EBS, cross-AZ, consumers, Connect and observability costs.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Review retention and compaction policy

**Procedure:** Obtain topic-owner, replay, data governance and legal retention approvals.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Evaluate FinOps alternatives

**Procedure:** Compare baseline, rightsize, tiered storage, retention and AZ transfer tradeoffs.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Exercise capacity incident tabletop

**Procedure:** Simulate disk full, ISR degradation, network bottleneck, backlog and cost anomaly.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Build acceptance dashboard

**Procedure:** Correlate throughput, P99, freshness, ISR, KRaft, disk headroom, budget and release SHA.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Independent enterprise acceptance

**Procedure:** Score all critical gates, preserve sanitized evidence, risk exceptions and SRE/security signoff.

**Required evidence:** UTC time, cluster and tool versions, raw data source, units, workload assumptions, expected/observed results, topic RF/minISR, KRaft quorum, broker/PVC utilization, client P99/freshness, event-ID ledger, cost source/date, **Live** vs **Tabletop**, risk/abort and independent reviewer. **Status: Pending** until executed.

## 11. Offline acceptance scorecard validator

Save as `validate_ch085_scorecard.py`. It validates a **reviewed input file**, not live Kafka or AWS resources.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("scorecard", help="Reviewed JSON evidence scorecard")
args = p.parse_args()
with open(args.scorecard, encoding="utf-8") as f:
    d = json.load(f)

required = ["domain_scores", "critical_gates", "independent_review",
            "live_evidence_verified", "missing_acknowledged_events",
            "unapproved_data_mutation", "evidence_ref"]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing fields: " + ", ".join(missing))

weights = {
    "forecast_storage": 20,
    "performance_correctness": 25,
    "failure_reserve": 20,
    "finops_governance": 15,
    "operations_runbooks": 10,
    "independent_review": 10,
}
scores = d["domain_scores"]
if set(scores) != set(weights):
    p.error("domain_scores keys must exactly match weights")
if any(not isinstance(scores[k], (int, float)) or not 0 <= scores[k] <= weights[k] for k in weights):
    p.error("scores outside allowed ranges")
if not isinstance(d["critical_gates"], dict) or not d["critical_gates"]:
    p.error("critical_gates must be a nonempty map")
total = sum(scores.values())
pass_all = (
    total >= 85
    and all(v is True for v in d["critical_gates"].values())
    and d["independent_review"] is True
    and d["live_evidence_verified"] is True
    and d["missing_acknowledged_events"] == 0
    and d["unapproved_data_mutation"] is False
    and bool(d["evidence_ref"])
)
print(json.dumps({"score": total, "maximum": 100, "pass": pass_all}, indent=2))
raise SystemExit(0 if pass_all else 1)
```

**Critical limitation:** This script trusts input values; an independent reviewer must validate the referenced raw telemetry and signed approvals. It cannot certify execution by itself.

## 12. Twelve integrated failure scenarios

### Scenario 01 — Model passes but one broker is nearly full

**Diagnosis:** Inspect partition skew and reassignment reserve; reject average-only sizing. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 02 — Projected savings depend on lowering RF

**Diagnosis:** Reject if durability/AZ/minISR contract would weaken. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 03 — Capacity benchmark ignores acknowledged event loss

**Diagnosis:** Reconcile unique IDs and fail acceptance. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 04 — Storage forecast assumes compaction always immediate

**Diagnosis:** Model cleaner backlog, segments and tombstone churn. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 05 — Consumer backlog cannot drain after burst

**Diagnosis:** Compare arrival/service rates, partition ceiling and downstream bottleneck. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 06 — KRaft controller cannot handle partition growth

**Diagnosis:** Assess metadata churn, quorum, controller resources and version. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 07 — Broker failure exhausts disk headroom

**Diagnosis:** Block scale-down; recalculate N-1 assignment and recovery space. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 08 — AZ loss violates ISR availability

**Diagnosis:** Revisit rack-aware placement, RF/minISR and controller quorum. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 09 — MSK quote omits data transfer

**Diagnosis:** Include AZ/region egress, clients, replication and Connect. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 10 — Tiered storage savings increase RTO

**Diagnosis:** Review retrieval latency, request costs, recovery and supported features. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 11 — Benchmark generator is bottleneck

**Diagnosis:** Separate client CPU/limits from broker capacity; rerun isolated. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

### Scenario 12 — Evidence incomplete or unreviewed

**Diagnosis:** Mark Pending/Fail, assign owner and block production acceptance. Cross-check workload baseline, per-partition skew, broker PVC/IOPS, Kafka KRaft quorum/ISR, producer P99, consumer freshness, unique event IDs and billing. **Response:** Block unsafe capacity/cost change, protect Kafka durability and preserve sanitized evidence. **Exit:** Corrected model, verified SLO, risk owner, RCA and independent review.

## 13. Eight production runbooks

### Runbook A — Capacity acceptance preflight

**Trigger/actions:** Verify change charter, data, SLO, versions, isolation and independent approvals. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook B — Broker disk saturation

**Trigger/actions:** Protect ISR, stop risky moves, verify per-broker skew and approved expansion. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook C — P99 and throughput regression

**Trigger/actions:** Correlate client ack latency, disk IOPS, CPU, network, partition skew and retries. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook D — Consumer freshness breach

**Trigger/actions:** Measure lag, service rate, rebalances and drain time; protect correctness. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook E — KRaft quorum/ISR degradation

**Trigger/actions:** Stop tests and scaling, check controller placement, RF/minISR and replicas. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook F — Cost anomaly or budget breach

**Trigger/actions:** Reconcile storage, network, broker hours, tiering, autoscale and price changes. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook G — Scaling decision and rollback

**Trigger/actions:** Require safe KafkaNodePool/MSK plan, storage lifecycle and data recovery caveats. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

### Runbook H — Final SRE/FinOps acceptance

**Trigger/actions:** Review all 20 evidence artifacts, score critical gates and sign risk register. **No-go:** unknown data correctness, unhealthy quorum/ISR, missing AZ reserve, unapproved retention or cost change, production stress without authorization. **Exit:** Healthy Kafka, accepted client SLO, reviewed forecast, documented savings and signed evidence.

## 14. Evidence package

```text
evidence-ch085/
  01-capstone-charter.md
  02-inventory-versions.md
  03-demand-baseline.csv
  04-topic-partition-config.csv
  05-storage-forecast.json
  06-disk-iops-throughput.csv
  07-cpu-memory-network.csv
  08-kraft-controller-headroom.md
  09-broker-failure-model.md
  10-az-failure-model.md
  11-event-ledger.csv
  12-benchmark-reproducibility.md
  13-burst-backlog-drain.md
  14-scaling-options.md
  15-cloud-cost-allocation.csv
  16-retention-governance.md
  17-finops-alternatives.md
  18-incident-tabletop.md
  19-acceptance-dashboard.md
  20-independent-signoff.md
  scorecard.json
  risk-register.md
```

Each artifact records source/UTC time, Kafka/Strimzi/EKS/MSK versions, raw observations, units, pricing region/date, expected/observed, **Live** versus **Tabletop**, owner, abort/recovery and independent reviewer. Missing files are **Pending**, not passed.

## 15. 100-point enterprise capacity acceptance

| Domain | Points | Critical |
|---|---:|---|
| Forecast, storage, partition and disk engineering | 20 | Yes |
| Performance, consumer freshness and event correctness | 25 | Yes |
| KRaft, ISR, N-1/AZ failure and recovery reserve | 20 | Yes |
| FinOps cost provenance and data governance | 15 | Yes |
| Operations, monitoring and incident runbooks | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced and representative live tests. **Automatic Fail:** fabricated measurements, unapproved production load, lost acknowledged events, degraded quorum/ISR without abort, missing AZ reserve, unsafe data-retention change or absent independent review.

**Current status:** **Not Ready / Pending**. This document contains the procedure and rubric; no live acceptance or security certification is claimed.

## 16. Part completion and next chapter

**Part 17 — Capacity Planning, Performance and FinOps (081–085) is fully published.** Chapter 081 covers forecasts; 082 storage/partitions; 083 performance validation; 084 cost governance; 085 enterprise acceptance.

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [Kubernetes](https://kubernetes.io/docs/), [AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html).

**Next:** Chapter 086 — Kafka Enterprise Security Architecture, Zero Trust and Governance Controls, beginning Part 18 — Security, Governance and Compliance.

---

**Verification boundary:** Publication confirms document availability only. Live workload baselines, benchmarking, cloud cost validation, failure drills and independent technical/security review remain Pending.
