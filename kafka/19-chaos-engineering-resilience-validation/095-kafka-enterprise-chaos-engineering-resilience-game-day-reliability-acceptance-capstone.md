# Chapter 095 — Kafka Enterprise Chaos Engineering, Resilience Game Day and Reliability Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 19 — Chaos Engineering and Resilience Validation (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS; Amazon MSK managed-service comparison  
**Prerequisites:** Chapters 001–094, especially 091–094  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This capstone defines enterprise game-day readiness, not permission to inject production faults. Use synthetic events and a disposable, approved cluster. Do not disrupt production Kafka brokers/controllers, network, AZs, EBS/PVCs, CDC or healthcare feeds. Enforce exact Kubernetes context/namespace/target allowlists, bounded duration, Kafka quorum/ISR, source/sink correctness, hard abort, rollback and incident command. Never include PHI or secrets in evidence.

## 1. Mission and acceptance objectives

Integrate **Chapter 091 (chaos safety), 092 (broker/partition/KRaft), 093 (network/storage/AZ) and 094 (producer/consumer/Connect/streaming)** into an enterprise resilience validation program.

The capstone evaluates whether Kafka maintains or recovers **acknowledged-event durability, KRaft metadata quorum, RF/minISR availability, producer/consumer correctness, Connect/CDC continuity, downstream freshness and operational incident response** under explicitly bounded faults.

**Published is not Live Executed.** Independent review, production authorization and legal/privacy approvals are separate gates.

## 2. Enterprise game-day architecture

```text
Change owner + incident commander + independent approver
                         |
         resilience hypothesis + baseline SLO
                         |
             isolated Strimzi KRaft cluster
           /            |              \
        brokers     controllers      PVC / AZ / VPC
           |            |              |
        Kafka topics + RF/minISR + leader/ISR
                         |
       synthetic producer -> consumer / Connect
                         |
               sink and CDC lineage
                         |
            acknowledged/sink ID ledger
                         |
          metrics, logs, traces, alerting
                         |
       bounded fault -> hard stop -> recovery
                         |
       reconciliation + RCA + risk register
                         |
             independent acceptance gate
```

A healthy broker dashboard is not sufficient to prove that a healthcare pipeline delivered its events correctly. Acks, sink effects and business freshness require separate reconciliation.

## 3. Non-negotiable game-day gates

| Gate | Evidence | No-go |
|---|---|---|
| Change authority | written scope, owner, incident command | unapproved target |
| Environment isolation | disposable cluster, context/namespace/UID | production context |
| Kafka durability | RF/minISR and ISR baseline | existing under-minISR |
| KRaft control plane | controller voter majority | quorum loss risk |
| Data correctness | unique synthetic ack/sink ledger | unexplained missing IDs |
| Storage/network | PVC free space, IOPS, VPC/AZ map | no recovery reserve |
| Client/Connect | SLO, CDC log retention, sink health | irreversible duplicate risk |
| Detection | alert routing, dashboards and observers | missing telemetry |
| Fault controls | single target, bounded duration, abort | unbounded injection |
| Review | independent SRE/security acceptance | missing signoff |

**Abort immediately** on missing acknowledged events, loss of controller majority, unexpected under-minISR, real-data exposure, excessive blast radius, unbounded lag or failed rollback.

## 4. Kafka broker and KRaft resilience

Model broker leader loss, follower lag, partition leadership and replica catch-up. For RF=3/minISR=2, one healthy in-sync replica loss may preserve acks=all writes, but only when the surviving ISR and leader are available.

KRaft controller quorum is separate from broker ISR. Model voter majority and AZ placement; never inject a controller majority failure in production. Unclean leader election is not an acceptable shortcut for an availability test.

## 5. Network, storage and AZ resilience

Model client-to-broker and broker-to-broker loss separately. Include DNS, advertised listeners, TLS, NetworkPolicy, VPC security groups, cross-AZ throughput and KRaft controller links.

For EBS/PVC, model IOPS/throughput/queue depth and AZ-bound volume topology. Avoid destructive disk-fill tests. A single-AZ outage is correlated across nodes, replicas, controllers and storage; demonstrate N-1 survivability from actual placement, not RF alone.

## 6. End-to-end pipeline correctness

Track unique **synthetic producer-acknowledged IDs** and independently observed downstream materializations. Consumer lag of zero is not proof of sink durability; duplicates, offset commits, retries and business side effects must be reconciled.

Kafka Connect worker/task restart and CDC source outage can cause replay, duplicate sink writes or source log expiry. Validate connector-specific semantics, DLQ, schema contracts, source log windows and sink idempotency.

## 7. Failure injection orchestration and stop logic

Prefer offline models and tabletop first, then approved isolated client faults, then one bounded broker or network fault if all gates pass. Every fault must have a named owner, fault TTL, exact target, rollback and observer.

Chaos controllers must have narrowly scoped RBAC and auditable operations. Automatic fault stop must not be the only rollback; prepare human-driven forward-fix and incident escalation.

## 8. Reliability metrics and recovery evidence

| Metric | Before | During | After | Gate |
|---|---|---|---|---|
| Producer acknowledged throughput | baseline | observe | restore | workload SLO |
| Producer P99/error rate | baseline | observe | recover | workload SLO |
| Kafka under-minISR partitions | zero | critical stop | zero | durability |
| KRaft quorum majority | healthy | preserved | healthy | metadata |
| ISR and under-replicated partitions | healthy | observe | full recovery | replica safety |
| Consumer lag/freshness | baseline | observe | drain | freshness SLO |
| Connect/CDC source lag | baseline | observe | recover | source log window |
| Sink reconciliation | all expected IDs | record | no unexplained gaps | correctness |

Measure **MTTD, MTTR, ISR recovery, lag drain, data correctness and incident communication latency**. Compare against approved RPO/RTO/SLO objectives.

## 9. Read-only Kubernetes/EKS preflight

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool,kafkaconnect -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pdb -A
kubectl get pvc -A
kubectl get networkpolicy -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Some CRDs require installation; omit unavailable kinds only after documenting the environment. Read-only metadata must still be sanitized before sharing.

## 10. Twenty enterprise game-day acceptance labs

### Lab 01 — Authorize enterprise resilience game day

**Procedure:** Set isolated cluster scope, business owner, incident commander, security approval and kill switch.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Build complete Kafka failure-domain inventory

**Procedure:** Map KRaft controllers, brokers, AZs, PVC, clients, Connect, sinks and dependencies.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Define end-to-end SLO and RPO/RTO

**Procedure:** Set approved throughput, P99, freshness, correctness and recovery objectives.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Capture healthy Kafka baseline

**Procedure:** Record RF/minISR, ISR, leader stability, controller quorum and resource headroom.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Establish synthetic event ledger

**Procedure:** Capture unique acknowledged producer IDs and independently verified sink IDs.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Validate chaos RBAC and target allowlist

**Procedure:** Confirm isolated context, namespace, UID selectors, duration and audit.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Assess broker interruption hypothesis

**Procedure:** Model single broker loss, leader election, ISR and producer retry.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Assess follower lag and catch-up

**Procedure:** Model replica recovery bandwidth, disk capacity and under-replication duration.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Assess KRaft controller interruption

**Procedure:** Validate quorum majority and controller recovery without unsafe majority loss.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Assess broker network partition

**Procedure:** Model replication loss, minISR and safe fault termination.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Assess DNS and client network degradation

**Procedure:** Model bootstrap, advertised listener, retries and consumer heartbeat.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Assess EBS/PVC storage pressure

**Procedure:** Model IOPS/throughput/queue depth and capacity without destructive disk fill.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Assess single-AZ outage

**Procedure:** Check broker rack placement, controller voters and N-1 capacity.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Assess producer crash and ambiguous acks

**Procedure:** Reconcile synthetic IDs and idempotent retry semantics.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Assess consumer rebalance and replay

**Procedure:** Validate offset commits, lag, duplicate side effects and recovery.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Assess Connect worker/CDC outage

**Procedure:** Verify source log retention, task restart, DLQ and sink correctness.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Assess schema and downstream failure

**Procedure:** Model incompatible schema, sink backpressure and streaming state restore.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Exercise incident command tabletop

**Procedure:** Simulate detection, escalation, abort, recovery, privacy and communications.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Build evidence and risk remediation register

**Procedure:** Record expected/observed, fault timeline, gaps, owners and due dates.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Conduct independent resilience acceptance

**Procedure:** Review scorecard, critical gates, correctness evidence and formal signoff.

**Required evidence:** UTC time, exact isolated cluster/context/namespace/target, Kafka/Strimzi/EKS versions, approved hypothesis, RF/minISR and quorum, synthetic producer/sink IDs, baseline and fault SLO, fault duration, expected/observed, alert timeline, abort/rollback, recovery, **Tabletop** vs **Live**, business owner and independent reviewer. **Status: Pending** until executed.

## 11. Offline enterprise chaos acceptance validator

Save as `validate_ch095_chaos_acceptance.py`. This validates a **reviewed synthetic scorecard**, not Kafka live state.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("scorecard", help="Reviewed synthetic chaos scorecard JSON")
args = p.parse_args()
with open(args.scorecard, encoding="utf-8") as f:
    d = json.load(f)
weights = {
    "safety_and_baseline": 20,
    "broker_kraft_isr": 20,
    "network_storage_az": 20,
    "pipeline_correctness": 20,
    "recovery_and_incident_command": 10,
    "independent_review": 10,
}
required = [
    "scores", "critical_gates", "live_evidence_verified",
    "independent_sre_review", "independent_security_review",
    "acknowledged_event_loss", "unapproved_production_fault",
    "evidence_ref"
]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
scores = d["scores"]
if not isinstance(scores, dict) or set(scores) != set(weights):
    p.error("scores must match weighted domains")
if any(type(scores[k]) not in (int, float) or not 0 <= scores[k] <= weights[k]
       for k in weights):
    p.error("score out of range")
gates = d["critical_gates"]
if not isinstance(gates, dict) or not gates:
    p.error("critical_gates must be a nonempty object")
total = sum(scores.values())
passed = (
    total >= 85 and all(v is True for v in gates.values())
    and d["live_evidence_verified"] is True
    and d["independent_sre_review"] is True
    and d["independent_security_review"] is True
    and d["acknowledged_event_loss"] is False
    and d["unapproved_production_fault"] is False
    and bool(d["evidence_ref"])
)
print(json.dumps({"score": total, "maximum": 100, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitations:** The validator trusts the scorecard and cannot verify cluster isolation, acknowledged IDs, sink correctness, actual quorum, alert delivery or independent signatures. An offline pass is not a live acceptance or permission for production faults.

## 12. Twelve enterprise chaos failure scenarios

### Scenario 01 — Fault starts in production context

**Diagnosis:** Abort and escalate; prevent all non-allowlisted targets. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 02 — Broker loss triggers unexpected minISR violation

**Diagnosis:** Stop, restore replicas and reassess RF/AZ placement. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 03 — Controller fault threatens majority

**Diagnosis:** Abort, preserve quorum and use approved KRaft recovery. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 04 — Network chaos disconnects unrelated workloads

**Diagnosis:** Contain blast radius and review network controller permissions. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 05 — PVC pressure endangers Kafka logs

**Diagnosis:** Stop synthetic load and preserve disk safety and replica catch-up. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 06 — AZ failure removes too many replicas

**Diagnosis:** Fail N-1 gate and redesign rack-aware placement. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 07 — Producer ack ledger reveals missing event

**Diagnosis:** Fail correctness gate and investigate delivery/recovery. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 08 — Consumer replay duplicates irreversible effects

**Diagnosis:** Protect sink, review idempotence and commit boundaries. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 09 — CDC source log expires during outage

**Diagnosis:** Escalate data recovery and resnapshot decision. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 10 — DLQ/schema failure leaks sensitive payload

**Diagnosis:** Contain and initiate privacy/security incident response. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 11 — Recovery SLO exceeded despite healthy brokers

**Diagnosis:** Investigate consumer lag, Connect sink and downstream backlog. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

### Scenario 12 — Scorecard claims success without live evidence

**Diagnosis:** Mark pending; require independent execution and review. Correlate broker ISR/minISR, KRaft quorum, network/AZ/PVC metrics, producer acknowledgements, consumer commits, Connect/CDC source offsets, sink ledger, SLO and incident timeline. **Response:** Abort fault, protect data durability, restore service, preserve sanitized evidence and notify incident command. **Exit:** Reconciled synthetic IDs, restored Kafka/client SLO, documented RCA, risk owner and independent review.

## 13. Eight production resilience runbooks

### Runbook A — Enterprise chaos preflight

**Trigger/actions:** Verify charter, isolated context, owner, baseline, event ledger and rollback. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook B — Broker/partition recovery

**Trigger/actions:** Restore leader/ISR, monitor under-minISR, client acknowledgements and catch-up. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook C — KRaft quorum protection

**Trigger/actions:** Preserve majority and execute only supported controlled recovery. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook D — Network/DNS impairment response

**Trigger/actions:** Stop fault, restore listener/DNS routes and verify client freshness. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook E — EBS/PVC and AZ recovery

**Trigger/actions:** Protect volume topology, disk reserve, replica placement and recovery capacity. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook F — Producer/consumer correctness incident

**Trigger/actions:** Reconcile unique synthetic IDs, offsets, duplicates and downstream effects. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook G — Connect/CDC and sink restoration

**Trigger/actions:** Protect source retention, restart safely and validate sink materialization. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

### Runbook H — Game day closeout and acceptance

**Trigger/actions:** Record incident timeline, SLO results, action owners and independent signoff. **No-go:** production fault without approval, lost KRaft majority, unexpected under-minISR, missing acknowledged events, no abort/rollback, real PHI in evidence or fabricated live results. **Exit:** Fault removed, Kafka and pipeline recovered, full evidence timeline and independent acceptance.

## 14. Evidence package

```text
evidence-ch095/
  01-game-day-charter.md
  02-failure-domain-map.md
  03-slo-rpo-rto.md
  04-kafka-baseline.md
  05-event-ledger.json
  06-chaos-rbac.md
  07-broker-interruption.md
  08-replica-catchup.md
  09-kraft-controller.md
  10-broker-network.md
  11-dns-client-network.md
  12-ebs-pvc.md
  13-az-survivability.md
  14-producer-crash.md
  15-consumer-rebalance.md
  16-connect-cdc.md
  17-schema-sink.md
  18-incident-tabletop.md
  19-risk-remediation.md
  20-independent-acceptance.md
  scorecard.json
  approved-exceptions.md
```

Each artifact includes UTC time, exact environment and source/version, **Tabletop** vs **Live**, hypothesis, baseline, fault start/stop, expected/observed, synthetic ID reconciliation, abort/rollback, recovery SLO, owner and independent reviewer.

## 15. 100-point enterprise chaos acceptance

| Domain | Points | Critical |
|---|---:|---|
| Safety, approvals, baseline and observability | 20 | Yes |
| Broker, KRaft and ISR resilience | 20 | Yes |
| Network, storage and AZ resilience | 20 | Yes |
| Producer/consumer/Connect end-to-end correctness | 20 | Yes |
| Recovery, incident command and runbooks | 10 | Yes |
| Independent SRE/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced by approved live tests and reviewers. **Automatic Fail:** unapproved production fault, lost controller majority, unexpected under-minISR, missing acknowledged IDs, uncontrolled privacy exposure, absent abort/rollback or fabricated evidence.

**Current status:** **Not Ready / Pending**. The chapter is published, but the enterprise resilience game day has not been executed or independently approved.

## 16. Part completion and next chapter

**Part 19 — Chaos Engineering and Resilience Validation (091–095) is fully published.** Chapter 091 establishes safety, 092 broker/KRaft recovery, 093 network/storage/AZ resilience, 094 streaming pipeline correctness, and 095 integrated enterprise acceptance.

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 096 — Kafka Enterprise SRE Capstone Architecture, Requirements and Production Readiness, beginning Part 20 — Final Enterprise SRE Capstone.

---

**Verification boundary:** Publication confirms document availability only. Live fault injection, synthetic event reconciliation, SLO recovery measurements and independent SRE/security review remain Pending.
