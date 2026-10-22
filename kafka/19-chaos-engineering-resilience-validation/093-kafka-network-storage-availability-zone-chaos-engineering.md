# Chapter 093 — Kafka Network, Storage and Availability Zone Chaos Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 19 — Chaos Engineering and Resilience Validation (3/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on Amazon EKS; Amazon MSK comparison  
**Prerequisites:** Chapters 001–092; Kafka RF/minISR, KRaft, EKS networking, PVC/EBS, AZ placement, SLOs and safe chaos  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter specifies offline models and tabletop experiments. Do not inject network loss, DNS failure, EBS throttling, PVC fullness, node isolation or AZ faults in production. Never block controller quorum, reduce minISR, corrupt Kafka log directories or write synthetic disk-fill files to real broker volumes. Any isolated live fault requires written approval, exact kube context/namespace/target UID, duration, telemetry, abort and rollback. Use synthetic events only.

## 1. Mission and learning outcomes

Engineer controlled **network, storage and availability-zone failure experiments** for Kafka on Kubernetes and Amazon MSK. Evaluate client-to-broker latency, broker replication loss, DNS/advertised listeners, VPC connectivity, EBS/PVC I/O, volume topology and correlated AZ outages without compromising acknowledged data or KRaft quorum.

Readers will build fault-domain maps, model per-zone ISR and controller-majority survivability, define observability/abort gates, quantify recovery reserve and document independent resilience acceptance.

## 2. Multi-AZ architecture and failure boundaries

```text
                  EKS VPC / private subnets
     +----------------+----------------+----------------+
     | AZ-a           | AZ-b           | AZ-c           |
     | Broker A       | Broker B       | Broker C       |
     | Controller 1   | Controller 2   | Controller 3   |
     | EBS PVC A      | EBS PVC B      | EBS PVC C      |
     +----------------+----------------+----------------+
                 |         |         |
           broker replication / KRaft quorum
                 |         |         |
           producers / consumers / Connect
                         |
               synthetic event ledger
                         |
          Prometheus + logs + incident command
                         |
          bounded fault -> stop -> recover
```

**Placement matters:** RF=3 does not guarantee one-AZ resilience if multiple replicas share an AZ. Likewise, three controllers only tolerate a single controller loss if the remaining voters can form a majority. EBS volumes are AZ-scoped and cannot simply attach to nodes in another AZ.

## 3. Experiment charter and baseline

Every experiment needs a hypothesis, steady-state SLO, authorized target, failure mode, expected Kafka behavior, maximum fault duration, abort thresholds, recovery plan, owner and independent reviewer.

Baseline: producer acked IDs, P99, errors and retry rate; consumer lag/freshness; partition leader/ISR and under-minISR; KRaft voter health; disk IOPS/throughput/latency/queue depth; PVC usage; broker-to-broker network RTT/throughput; DNS; cross-AZ traffic; client SLO and recovery headroom.

## 4. Network chaos design

### 4.1 Client-to-broker impairment

Latency and loss can increase producer retries, request timeouts, metadata refreshes and consumer heartbeats. Evaluate delivery.timeout.ms, request.timeout.ms, acks, idempotence and retry semantics. Reconcile **acknowledged event IDs**, not just error counters.

### 4.2 Broker-to-broker impairment

Replication latency may shrink ISR, elevate under-replicated partitions and eventually violate minISR. Do not continue an experiment after critical replication safety gates fail. Track catch-up time and broker network reserve after the fault stops.

### 4.3 KRaft and DNS

Controller listener connectivity is distinct from client/broker data paths. Isolating a controller majority can prevent metadata progress. DNS or advertised.listeners errors may look like broker outages; diagnose endpoint resolution, security groups, TLS SANs and client metadata separately.

## 5. Storage chaos design

Kafka storage performance is governed by log segment activity, page cache, disk throughput/IOPS, replica fetch, compaction and recovery. EBS throttling can increase producer P99, ISR lag and controller/broker request delays.

Never test disk-full behavior by filling production PVCs. Use isolated disposable volumes or offline capacity models. Review volume type limits, filesystem, PV topology, reclaim policy, storage-class expansion, node capacity and broker recovery reserve.

## 6. Availability zone resilience

An AZ outage is a **correlated failure** of nodes, network paths and AZ-bound EBS volumes. Verify each zone's replica placement, controller voter distribution and remaining cluster capacity. A Kafka cluster can retain metadata quorum yet lose writes for partitions whose ISR drops below minISR, or vice versa.

For EKS, Pod rescheduling cannot move an AZ-bound EBS PVC to another AZ. Durable recovery may require replacement broker capacity, reassignment or restoration using supported Strimzi/Kafka procedures. Never delete PVs to force recovery.

## 7. MSK-specific boundaries

Amazon MSK manages broker infrastructure and availability differently from self-managed Strimzi. Do not assume access to MSK broker Pods, disks or arbitrary fault-injection controls. Use AWS-supported monitoring and approved test clusters; model AZ loss, client connectivity, IAM and recovery with service-specific constraints.

## 8. Network, storage and AZ failure matrix

| Fault | Kafka signal | Safety boundary |
|---|---|---|
| Client latency/loss | P99, retries, timeout | no missing acknowledged IDs |
| Replication loss | ISR shrink, fetch lag | stop before under-minISR |
| DNS failure | bootstrap/connect errors | preserve broker/controller paths |
| Controller partition | quorum/metadata errors | never remove majority |
| EBS IOPS throttle | queue, disk latency, P99 | stop before replica durability risk |
| PVC near full | disk utilization, log errors | no real broker disk fill |
| Node/PVC detach | scheduling and broker readiness | preserve PV/PVC identity |
| Single AZ outage | replicas/controllers unavailable | tabletop until safe N-1 proven |

## 9. Read-only Kubernetes/EKS preflight

```bash
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get pvc,pv -A
kubectl get storageclass
kubectl get pdb -A
kubectl get networkpolicy -A
```

These commands are read-only but may expose infrastructure metadata; sanitize outputs. Some resource combinations or flags vary by Kubernetes version. No command here authorizes fault injection.

## 10. Twenty network, storage and AZ chaos labs

### Lab 01 — Approve network/storage/AZ chaos scope

**Procedure:** Verify disposable cluster, explicit context, fault limits, owner and rollback.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Inventory EKS and Kafka failure domains

**Procedure:** Map nodes, subnets, AZs, broker/controller placement, PVC and network.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Capture producer and consumer baseline

**Procedure:** Record synthetic acknowledged IDs, throughput, P99, lag and freshness.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Capture network baseline

**Procedure:** Measure broker/client RTT, packet loss, connection churn and replication throughput.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Capture storage baseline

**Procedure:** Measure PVC free space, latency, IOPS, queue depth and replica fetch lag.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Validate RF/minISR across AZs

**Procedure:** Calculate surviving ISR for each AZ loss and current replica placement.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Validate KRaft voter AZ placement

**Procedure:** Model controller majority under one-zone and network isolation failures.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Design client-to-broker latency fault

**Procedure:** Define bounded latency, expected retries/timeouts and SLO abort.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Design broker-to-broker packet loss

**Procedure:** Model ISR shrink and follower catch-up while preserving quorum.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Design DNS/service discovery fault

**Procedure:** Review bootstrap/advertised listeners, CoreDNS and cached metadata.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Design VPC security group misconfiguration

**Procedure:** Tabletop blocked broker, client and controller paths; include rollback.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Design cross-AZ network degradation

**Procedure:** Model replication bandwidth, latency, cost and fault containment.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Design EBS/PVC IOPS throttling

**Procedure:** Model storage saturation, request P99 and replica recovery headroom.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Design PVC near-full condition

**Procedure:** Use synthetic capacity model rather than writing to production disks.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Design node/PV detach recovery

**Procedure:** Review AZ-bound volumes, scheduling constraints and StatefulSet identity.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Design single-AZ failure tabletop

**Procedure:** Assess remaining broker ISR, controller majority, clients and capacity.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Design recovery after AZ restoration

**Procedure:** Plan broker rescheduling, replica catch-up, lag drain and stability.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Assess managed MSK fault limitations

**Procedure:** Separate MSK service-managed failover from EKS Pod/network experiments.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Review stop conditions and evidence

**Procedure:** Check ISR/quorum, acknowledged IDs, lag, storage, blast radius and kill switch.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Independent network/storage/AZ acceptance

**Procedure:** Review models, evidence, incident response, privacy and safety signoff.

**Required evidence:** UTC time, isolated context/namespace, Kafka/Strimzi/EKS/MSK version, AZ and broker/controller map, RF/minISR, baseline network/storage SLIs, synthetic acknowledged/consumed event IDs, hypothesis, expected/observed, fault duration, abort, recovery, **Tabletop** versus **Live**, owner and independent reviewer. **Status: Pending** until executed.

## 11. Offline AZ survivability validator

Save as `validate_az_survivability.py`. It models one AZ failure from a **synthetic topology JSON**; it does not query live ISR or certify recovery.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("topology", help="Reviewed synthetic Kafka/AZ topology JSON")
args = p.parse_args()
with open(args.topology, encoding="utf-8") as f:
    d = json.load(f)
required = ["controllers", "partitions", "environment", "evidence_ref"]
if any(k not in d for k in required):
    p.error("missing required fields")
controllers = d["controllers"]
partitions = d["partitions"]
if not isinstance(controllers, list) or not controllers or not isinstance(partitions, list) or not partitions:
    p.error("controllers and partitions must be nonempty lists")
if any(not isinstance(x, str) or not x for x in controllers):
    p.error("controllers must be AZ strings")
zones = sorted(set(controllers).union(
    z for part in partitions if isinstance(part, dict)
    for z in part.get("isr_zones", []) if isinstance(z, str)
))
if not zones:
    p.error("no zones")
outcomes = []
for failed in zones:
    voters = sum(z != failed for z in controllers)
    majority = len(controllers) // 2 + 1
    write_ok = True
    for part in partitions:
        if not isinstance(part, dict) or type(part.get("min_isr")) is not int:
            p.error("each partition requires integer min_isr")
        isr = part.get("isr_zones")
        if not isinstance(isr, list) or not isr or any(not isinstance(z, str) for z in isr):
            p.error("invalid isr_zones")
        if not 1 <= part["min_isr"] <= len(isr):
            p.error("invalid min_isr")
        if sum(z != failed for z in isr) < part["min_isr"]:
            write_ok = False
    outcomes.append({"failed_az": failed, "controller_majority": voters >= majority,
                     "all_partitions_min_isr": write_ok})
passed = d["environment"] == "disposable-lab" and bool(d["evidence_ref"]) and all(
    x["controller_majority"] and x["all_partitions_min_isr"] for x in outcomes)
print(json.dumps({"single_az_outcomes": outcomes, "model_pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitations:** The model assumes a single controller voter per listed entry, treats each ISR replica as a zone string, ignores network partitions, client routing, leader election, storage topology, capacity and dynamic quorum changes. Independent real-world verification is required.

## 12. Twelve network/storage/AZ failure scenarios

### Scenario 01 — Latency fault causes producer timeout

**Diagnosis:** Correlate retries, acks, leader metadata and acknowledged ID ledger. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 02 — Broker replication packet loss shrinks ISR

**Diagnosis:** Stop fault and restore network before minISR is violated. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 03 — CoreDNS failure breaks bootstrap

**Diagnosis:** Inspect DNS, cached metadata, advertised listeners and recovery. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 04 — NetworkPolicy blocks controller listener

**Diagnosis:** Restore approved flows while protecting KRaft quorum. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 05 — Cross-AZ bandwidth saturates recovery

**Diagnosis:** Throttle reassignment and preserve client SLO and replica durability. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 06 — EBS throttling increases broker P99

**Diagnosis:** Check volume limits, queue depth, IOPS and replica fetch lag. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 07 — PVC near-full threatens log integrity

**Diagnosis:** Stop fault and execute approved capacity recovery without deletion. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 08 — AZ-bound PVC prevents rescheduling

**Diagnosis:** Review volume topology and restore compatible node/AZ placement. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 09 — AZ loss removes controller majority

**Diagnosis:** Abort live test and use tabletop until quorum placement corrected. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 10 — One AZ loss removes too many replicas

**Diagnosis:** Fail readiness and redesign rack awareness/RF/minISR. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 11 — MSK experiment assumes Pod access

**Diagnosis:** Use supported service-managed operations; do not imply broker Pod control. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

### Scenario 12 — Observability fails during network fault

**Diagnosis:** Mark experiment inconclusive and restore telemetry before retest. Correlate network RTT/loss, DNS, broker ISR/minISR, KRaft majority, EBS/PVC metrics, node/AZ placement, producer event ledger and consumer freshness. **Response:** Stop fault, restore network/storage paths, protect Kafka durability and preserve evidence. **Exit:** Healthy quorum/ISR, reconciled synthetic IDs, stable P99/lag, documented RCA and independent review.

## 13. Eight production recovery runbooks

### Runbook A — Network chaos preflight

**Trigger/actions:** Verify isolated context, VPC/AZ map, ISR/quorum, SLO, allowlist and rollback. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook B — Client/broker network degradation

**Trigger/actions:** Stop impairment, verify DNS/listeners, reconcile producer/consumer state. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook C — Broker replication partition

**Trigger/actions:** Restore inter-broker connectivity, monitor ISR and catch-up. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook D — DNS and service discovery outage

**Trigger/actions:** Inspect CoreDNS, bootstrap DNS, advertised endpoints and cached metadata. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook E — EBS/PVC I/O saturation

**Trigger/actions:** Stop synthetic load, verify volume limits, free space and request latency. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook F — PVC detach and scheduling recovery

**Trigger/actions:** Review AZ affinity, PV/PVC identity, StatefulSet and broker readiness. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook G — AZ outage resilience response

**Trigger/actions:** Protect controller majority and ISR; restore service and plan replica catch-up. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

### Runbook H — Post-chaos evidence and acceptance

**Trigger/actions:** Reconcile event IDs, recovery SLO, cost/capacity and independent review. **No-go:** unknown context, real broker disk fill, unapproved network isolation, controller majority risk, ISR/minISR breach, missing event ledger or absent abort/rollback. **Exit:** Fault removed, broker/controller paths healthy, ISR restored, client SLO recovered and evidence reviewed.

## 14. Evidence package

```text
evidence-ch093/
  01-chaos-scope.md
  02-failure-domain-inventory.md
  03-client-baseline.md
  04-network-baseline.md
  05-storage-baseline.md
  06-az-replica-placement.md
  07-kraft-voter-placement.md
  08-client-latency-design.md
  09-replication-loss-design.md
  10-dns-failure-design.md
  11-vpc-policy-tabletop.md
  12-cross-az-degradation.md
  13-ebs-throttling.md
  14-pvc-capacity.md
  15-pv-topology.md
  16-az-outage-tabletop.md
  17-az-recovery.md
  18-msk-limits.md
  19-abort-and-evidence.md
  20-independent-acceptance.md
  az-topology.json
  scorecard.md
```

Each artifact includes UTC time, source/version, **Tabletop** vs **Live**, baseline, hypothesis, expected/observed, zone/target, fault duration, synthetic ID reconciliation, abort/recovery, data safety and independent reviewer.

## 15. 100-point network/storage/AZ acceptance

| Domain | Points | Critical |
|---|---:|---|
| Fault authorization and baseline telemetry | 20 | Yes |
| Network/DNS/broker replication resilience | 20 | Yes |
| Storage/PVC/EBS safety and recovery reserve | 20 | Yes |
| AZ survivability, KRaft quorum and RF/minISR | 25 | Yes |
| Client correctness, runbooks and evidence | 5 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** unapproved production fault, controller majority loss, under-minISR breach, missing acknowledged events, destructive PVC fill, unknown data location or fabricated results.

**Current status:** **Pending**. No live network, storage or AZ failure injection is claimed.

## 16. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Storage](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [AWS EBS](https://docs.aws.amazon.com/ebs/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 094 — Kafka Producer, Consumer, Kafka Connect and Streaming Pipeline Chaos Engineering.

---

**Verification boundary:** Publication confirms document availability only. Live network/storage/AZ faults, client correctness and independent technical/security review remain Pending.
