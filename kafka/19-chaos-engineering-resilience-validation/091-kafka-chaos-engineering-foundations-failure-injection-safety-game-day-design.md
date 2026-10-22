# Chapter 091 — Kafka Chaos Engineering Foundations, Failure Injection Safety and Game Day Design

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 19 — Chaos Engineering and Resilience Validation (1/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS; Amazon MSK failure-domain tabletop  
**Prerequisites:** Chapters 001–090, especially Kafka replication/ISR, KRaft, SLOs, DR, capacity and security  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety first:** Chaos engineering is controlled hypothesis testing, not random destruction. All examples in this chapter are read-only preflight, offline modeling or tabletop design. Do not delete broker Pods, isolate nodes/AZs, block network traffic, fill PVCs, change Kafka configuration or run faults in production without an approved maintenance/game-day plan, dedicated incident command, hard abort conditions and independent review. No PHI or real patient events in experiments.

## 1. Mission and learning objectives

Design repeatable, measurable Kafka resilience experiments that validate **producer acknowledgement correctness, consumer freshness, ISR/minISR, KRaft controller quorum, broker recovery, failure-domain placement and operational incident response**.

By the end, the reader can define steady state and falsifiable hypotheses, estimate blast radius, choose fault injection mechanisms, enforce a safety envelope, build game-day timelines, document rollback and distinguish **Published**, **Tabletop**, **Live Executed** and **Independently Reviewed**.

## 2. Kafka chaos experiment architecture

```text
SRE / workload owner / change approver
                 |
       hypothesis + baseline SLO
                 |
      isolated Kafka KRaft cluster
       /          |            \
    brokers   controllers    clients
       |          |            |
    ISR/RF     quorum      ack IDs / lag
       \          |            /
        Prometheus + logs + traces
                 |
       bounded fault experiment
                 |
      kill switch + abort thresholds
                 |
        recovery and reconciliation
                 |
     evidence + RCA + independent gate
```

A broker restart may be safe with adequate RF/minISR, but **controller quorum** and **AZ placement** require independent evaluation. A PodDisruptionBudget protects only supported voluntary evictions, not every failure.

## 3. Scientific experiment contract

Every experiment must specify:

| Field | Example |
|---|---|
| Hypothesis | Losing one disposable broker will not lose acknowledged events |
| Steady state | no under-minISR partitions; healthy quorum; stable P99 and lag |
| Fault | one bounded broker Pod interruption in isolated namespace |
| Target | explicit allowlisted context/namespace/Pod UID |
| Blast radius | one broker; no simultaneous controller/zone faults |
| Abort | quorum at risk, minISR violation, missing acknowledged IDs or SLO breach |
| Recovery | fault removed, ISR restored, lag drained, client SLO stable |
| Evidence | UTC timeline, dashboards, unique event ledger, approved reviewers |

Do not equate zero producer errors with zero data loss. Compare **unique acknowledged event IDs** with durable processed IDs; document allowed retries/duplicates and delivery semantics.

## 4. Steady-state SLIs and reliability guardrails

Capture before, during and after: producer acknowledged rate and P99, request errors/timeouts, consumer lag and end-to-end freshness, ISR size, under-replicated and under-minISR partitions, leader changes, KRaft quorum health, broker CPU/disk/IOPS/network, and rebalance activity.

Use workload-specific thresholds from approved SLOs. No universal fixed P99 or lag threshold is safe for every healthcare pipeline.

## 5. Failure-domain model: broker, rack/AZ and KRaft

For RF=3 and minISR=2, a single lost replica may leave writes available when the remaining replicas are in sync; actual behavior depends on placement and ISR health. An AZ loss can remove multiple replicas and controllers, so simulate placement rather than assuming RF alone guarantees availability.

In a three-voter KRaft quorum, losing two voters prevents majority. Separate controller placement, network and recovery risks from broker log replication.

## 6. Fault injection options and boundaries

| Fault | Possible isolated mechanism | Risk |
|---|---|---|
| Client restart | restart disposable producer/consumer | duplicate/replay semantics |
| Broker Pod interruption | approved isolated Pod deletion | ISR shrink, leader election |
| Node drain | approved isolated node drain | multiple Pods, PDB limits |
| Network latency/loss | network emulator or chaos controller | timeouts, replication, quorum |
| Disk throttling | synthetic I/O load on disposable volume | disk latency, recovery |
| AZ loss | tabletop or dedicated isolated AZ fault | correlated replica/controller loss |
| IAM/credential failure | isolated synthetic client credential | auth outage, security response |
| Connect worker failure | isolated connector restart | offset replay, sink correctness |

Prefer client-side synthetic faults and offline models before broker, controller, disk or AZ experiments. Managed MSK does not provide the same Pod-level controls as Strimzi.

## 7. Game day roles, approvals and stop conditions

Assign incident commander, experiment operator, Kafka platform owner, application owner, observer and independent reviewer. Record explicit written scope, environment, allowed fault targets, duration, maintenance window, communications, escalation and abort authority.

**Hard stop:** unknown Kubernetes context, degraded quorum/ISR before test, missing telemetry, event correctness failure, production target, exposed PHI, unapproved fault, exceeded blast radius or failed rollback.

## 8. Kubernetes-first read-only preflight

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get pdb -A
kubectl get pvc -A
kubectl get networkpolicy -A
kubectl top nodes
```

`kubectl top` requires metrics-server. Commands are **inventory only** and do not authorize fault injection. Use separate explicit context allowlisting and change approval before any mutation.

## 9. Twenty safety-first chaos labs

### Lab 01 — Define chaos hypothesis

**Procedure:** State steady state, predicted impact, measurable abort and rollback.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Create experiment charter

**Procedure:** Assign incident commander, owner, approver, observer and communications channel.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Inventory Kafka failure domains

**Procedure:** Map brokers, KRaft controllers, racks/AZs, PVC, clients and consumers.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Classify workload criticality

**Procedure:** Set synthetic payload, RPO/RTO, availability, lag and producer P99 budgets.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Establish baseline telemetry

**Procedure:** Capture Kafka ISR, under-replicated partitions, disk, controller and client SLIs.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Check RF and minISR guardrails

**Procedure:** Model whether a broker or AZ failure would violate acks=all availability.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Assess controller quorum safety

**Procedure:** Verify quorum voter placement and exclude quorum-breaking tests.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Assess storage and reassignment reserve

**Procedure:** Calculate disk and network spare capacity during recovery.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Validate isolated namespace

**Procedure:** Review namespace quota, NetworkPolicy, workload separation and RBAC.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Review PodDisruptionBudgets

**Procedure:** Understand voluntary eviction guarantees and limitations during faults.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Define fault blast-radius limit

**Procedure:** Constrain target to one disposable broker/client and one bounded fault at a time.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Design broker Pod loss experiment

**Procedure:** Document hypothetical restart, ISR response, leader election and recovery.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Design consumer restart experiment

**Procedure:** Model rebalance, duplicate processing, lag and idempotency.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Design producer network impairment

**Procedure:** Specify latency/packet loss assumptions, retries, timeout and acknowledgement semantics.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Design broker disk pressure experiment

**Procedure:** Model throttling and disk-full response without filling production volumes.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Design AZ outage tabletop

**Procedure:** Evaluate racks, controller quorum, minISR and remaining network/disk.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Design recovery observation

**Procedure:** Measure detection, mitigation, ISR restoration, lag drain and P99 recovery.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Design stop and rollback controls

**Procedure:** Define manual kill switch, maximum duration and operator recovery commands.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Capture game day evidence

**Procedure:** Build timeline, hypothesis, expected/observed, failed assumptions and action items.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Run independent tabletop acceptance

**Procedure:** Review safety, coverage, approvals, evidence and readiness for isolated live drills.

**Required evidence:** UTC timestamp, exact cluster/context/namespace, Kafka/Strimzi/Kubernetes version, hypothesis, baseline SLO, RF/minISR and KRaft quorum, approved blast radius, expected/observed behavior, acknowledged event reconciliation, fault start/stop, abort and recovery, **Tabletop** versus **Live**, and independent reviewer. **Status: Pending** until executed.

## 10. Offline game-day readiness validator

Save as `validate_game_day.py`. It checks an **operator-reviewed JSON experiment charter**. It does not connect to Kafka, Kubernetes or AWS.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("charter", help="Reviewed game-day charter JSON")
args = p.parse_args()
with open(args.charter, encoding="utf-8") as f:
    d = json.load(f)
required_text = [
    "environment", "context", "namespace", "hypothesis", "steady_state",
    "fault_target", "blast_radius", "abort_conditions", "recovery_plan",
    "incident_commander", "approver", "evidence_ref"
]
required_bool = [
    "isolated_environment", "context_allowlisted", "telemetry_ready",
    "kraft_quorum_healthy", "min_isr_healthy", "client_event_ledger_ready",
    "rollback_reviewed", "independent_safety_review"
]
missing = [k for k in required_text + required_bool if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
checks = {k: isinstance(d[k], str) and bool(d[k].strip()) for k in required_text}
checks.update({k: d[k] is True for k in required_bool})
checks["no_production_target"] = str(d["environment"]).lower() not in ("prod", "production")
passed = all(checks.values())
print(json.dumps({"checks": checks, "ready_for_separate_approval": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Example synthetic input:** set `environment` to `disposable-lab`, all required text fields to meaningful nonempty strings, and all required booleans to `true`. The validator may then return `ready_for_separate_approval: true`, which is **not permission to run a fault**.

**Limitations:** The script trusts supplied assertions and cannot prove cluster isolation, permissions, healthy quorum, event correctness or a valid approval. Independent live preflight remains mandatory.

## 11. Twelve resilience experiment failure scenarios

### Scenario 01 — Experiment begins without baseline

**Diagnosis:** Abort; record baseline and expected steady state before injection. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 02 — Wrong kube context targeted

**Diagnosis:** Abort; use allowlisted context and explicit namespace verification. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 03 — Single broker failure violates minISR

**Diagnosis:** Reject test; reassess RF, placement and producer acks. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 04 — KRaft quorum lacks AZ resilience

**Diagnosis:** Limit to tabletop; fix quorum placement before failure injection. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 05 — Recovery exhausts broker disk

**Diagnosis:** Stop experiment; protect logs and reassignment reserve. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 06 — Consumer duplicates after rebalance

**Diagnosis:** Inspect offset commits, idempotency and downstream exactly-once assumptions. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 07 — Producer reports success despite missing IDs

**Diagnosis:** Reconcile acknowledged event ledger and treat as critical failure. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 08 — PodDisruptionBudget gives false confidence

**Diagnosis:** Distinguish voluntary disruptions from node/AZ faults. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 09 — Chaos controller has excessive RBAC

**Diagnosis:** Scope service account and reject broad delete permissions. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 10 — Observability fails during fault

**Diagnosis:** Stop; repair telemetry before live tests. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 11 — Abort switch does not restore service

**Diagnosis:** Escalate incident, execute preapproved forward-fix and capture timeline. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

### Scenario 12 — Game day is marked passed without execution

**Diagnosis:** Keep tabletop/pending status and require independent evidence. Correlate producer acknowledgements, unique event ledger, consumer lag, ISR/minISR, controller quorum, storage, networking, operator reconciliation and game-day timeline. **Response:** Stop fault, protect data durability, restore client SLO, preserve evidence and notify incident command. **Exit:** Reconciled acknowledged events, healthy Kafka, root cause and reviewed safeguards.

## 12. Eight production resilience runbooks

### Runbook A — Chaos preflight authorization

**Trigger/actions:** Validate isolated cluster, change window, owners, baseline and abort gates. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook B — Broker Pod failure drill

**Trigger/actions:** Verify RF/minISR, safe target, ISR, leader election and recovery. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook C — Client/network fault drill

**Trigger/actions:** Protect producer acks, retries, idempotency and consumer freshness. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook D — Storage-pressure simulation

**Trigger/actions:** Use offline models before any isolated disk fault; monitor PVC and IOPS. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook E — KRaft controller fault safety

**Trigger/actions:** Check quorum math and controller placement; avoid destructive production tests. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook F — Emergency abort and rollback

**Trigger/actions:** Stop fault, preserve state, recover Kafka/client SLO and notify command. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook G — Evidence and RCA collection

**Trigger/actions:** Record UTC timeline, dashboards, event ledger, hypothesis and actions. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

### Runbook H — Independent resilience readiness gate

**Trigger/actions:** Score blast radius, safety, telemetry, correctness and approvals. **No-go:** unapproved fault, production target, unhealthy KRaft quorum, ISR/minISR breach, missing telemetry, unbounded blast radius or unexplained acknowledged event loss. **Exit:** Fault removed, Kafka and clients recovered, evidence preserved and independent SRE review.

## 13. Evidence package

```text
evidence-ch091/
  01-chaos-hypothesis.md
  02-experiment-charter.json
  03-failure-domain-inventory.md
  04-workload-slo.md
  05-steady-state-baseline.md
  06-replication-guardrails.md
  07-kraft-quorum-model.md
  08-storage-reserve.md
  09-namespace-isolation.md
  10-pdb-review.md
  11-blast-radius.md
  12-broker-failure-design.md
  13-consumer-restart-design.md
  14-network-impairment-design.md
  15-disk-pressure-design.md
  16-az-failure-tabletop.md
  17-recovery-observations.md
  18-abort-and-rollback.md
  19-game-day-timeline.md
  20-independent-readiness.md
  risk-register.md
  acceptance-scorecard.md
```

Each artifact includes UTC time, source/version, **Tabletop** versus **Live**, baseline, hypothesis, expected/observed, target, fault duration, abort/rollback, unique event IDs, recovery SLO and independent reviewer.

## 14. 100-point chaos readiness assessment

| Domain | Points | Critical |
|---|---:|---|
| Hypothesis, baseline and observability | 20 | Yes |
| Kafka replication, KRaft and failure-domain safety | 25 | Yes |
| Fault isolation, blast radius and abort controls | 25 | Yes |
| Recovery, event correctness and SLO evidence | 15 | Yes |
| Game-day command, runbooks and risk register | 5 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced and independent review. **Automatic Fail:** production fault without approval, compromised quorum, unexpected minISR breach, acknowledged event loss, no abort control, PHI in evidence or fabricated execution results.

**Current status:** **Pending**. This chapter documents designs and readiness criteria only; no live chaos experiment is claimed.

## 15. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [Kubernetes PodDisruptionBudgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 092 — Kafka Broker, Partition and KRaft Failure Injection and Recovery Engineering.

---

**Verification boundary:** Publication confirms document availability only. Isolated fault injection, live client correctness checks, recovery measurements and independent technical/security review remain Pending.
