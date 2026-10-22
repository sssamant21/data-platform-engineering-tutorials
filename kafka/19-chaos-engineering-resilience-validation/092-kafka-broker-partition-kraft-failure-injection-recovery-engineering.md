# Chapter 092 — Kafka Broker, Partition and KRaft Failure Injection and Recovery Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 19 — Chaos Engineering and Resilience Validation (2/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS; Amazon MSK recovery comparison  
**Prerequisites:** Chapters 001–091; replication, RF/minISR, leaders/ISR, KRaft, Strimzi KafkaNodePool, SLOs and chaos safety  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** All experiments are design/tabletop until a separate isolated-cluster change approval. Never delete production broker/controller Pods, modify quorum voters, isolate production AZs, fill PVCs or enable unclean leader election. Confirm explicit kube context, namespace and target UID; preserve ISR/minISR, controller majority, synthetic acknowledged-event correctness and abort/rollback. Do not use PHI.

## 1. Mission and learning outcomes

Engineer bounded failure-injection and recovery experiments for **Kafka brokers, partition leaders, follower replicas, ISR/minISR, disk/network paths and KRaft controllers**. Validate whether acknowledged synthetic events remain correct, clients recover, replication converges and the control plane retains majority.

Readers will design broker/leader/follower fault tests, model controller majority, measure recovery time and produce a signed resilience acceptance package.

## 2. Broker and KRaft failure-domain architecture

```text
Synthetic producer -> Kafka partition leaders -> replicas
        |                    |                   |
    ack ledger            broker A/B/C        ISR/minISR
        |                    |                   |
Synthetic consumer <--- fetch / rebalance <-----+
        |
    processed-ID ledger

Strimzi KafkaNodePool + operator
        |
KRaft controller voters (separate quorum majority)
        |
Kafka metadata, leader election and placement
        |
Prometheus / logs / incident command
        |
bounded isolated fault -> abort -> recovery -> reconciliation
```

**Broker replication and controller metadata quorum are distinct reliability planes.** RF=3/minISR=2 may tolerate a single healthy replica loss for acks=all writes, but actual availability depends on current ISR, rack/AZ placement and leader election. A three-voter controller quorum requires two voters to remain available.

## 3. Preflight gates and experiment charter

| Gate | Required proof |
|---|---|
| Environment | disposable cluster, context/namespace/Pod UID allowlisted |
| Authorization | change owner, independent approver, incident commander |
| Kafka | healthy controller majority, no under-minISR partitions |
| Replication | documented RF/minISR, rack/AZ placement, leader/ISR baseline |
| Storage | broker/PVC reserve for replica recovery and reassignment |
| Clients | synthetic producer acks and consumer event-ledger validation |
| Observability | ISR, leader election, broker, quorum, producer P99 and lag |
| Safety | single bounded fault, duration, abort, rollback and communications |

If any gate is missing, run **tabletop only**.

## 4. Partition leadership and ISR failure mechanics

Partition leaders serve produce requests; followers replicate log data and join ISR when sufficiently caught up. A leader failure triggers election among eligible replicas according to broker/controller state and configuration.

With `acks=all`, the producer's successful acknowledgement is conditioned by Kafka replication semantics and `min.insync.replicas`; it is not proof of an end-to-end sink commit. Validate client idempotence, retry policy, delivery timeout, and unique acknowledged IDs. Avoid unclean leader election because it can sacrifice acknowledged-data safety.

## 5. KRaft controller quorum engineering

KRaft stores cluster metadata in a quorum of controllers. The ability to elect a controller leader depends on a majority of configured voters and supported quorum reconfiguration procedures for the deployed Kafka version.

A broker Pod restart must not be treated as equivalent to controller loss. **Never inject a fault that removes the controller majority** in production. Model AZ-correlated failures and controller placement before any isolated test.

## 6. Strimzi/Kubernetes behavior

Strimzi reconciles Kafka and KafkaNodePool resources. PodDisruptionBudgets limit supported voluntary evictions, not node/AZ failures or every direct Pod deletion. Stateful storage and broker identity must survive expected restarts; inspect PVC/PV reclaim policy and scheduling constraints.

Chaos tooling needs narrow RBAC, explicit target selectors, TTL and audit. Do not grant broad namespace or cluster delete privileges to an experiment runner.

## 7. Failure modes and recovery measures

| Fault | Expected signal | Recovery gate |
|---|---|---|
| Broker Pod interruption | leader election, ISR shrink, client retries | leader stable, ISR restored |
| Follower unavailable | under-replicated partitions, fetch lag | replica caught up |
| Broker disk I/O slowdown | request P99, log flush latency, ISR changes | disk normal, catch-up complete |
| Broker network split | replication lag, leader churn, timeouts | connectivity and ISR stable |
| Controller leader loss | controller election, metadata request latency | healthy voter majority |
| Controller majority loss | metadata/control-plane outage | tabletop; avoid live destructive test |
| Hot partition failover | broker load imbalance | P99/throughput within SLO |

Track **time to detect, time to restore writes, time to full ISR, time to drain consumer lag and time to reconcile synthetic IDs** separately.

## 8. Read-only Kubernetes and Kafka preflight

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get pdb -A
kubectl get pvc -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

For Kafka internals, use an authenticated read-only admin client in a restricted environment to inspect topic descriptions, ISR and quorum status. Exact CLI paths, Kafka version flags and authentication config differ; never publish client credentials.

## 9. Twenty broker/partition/KRaft resilience labs

### Lab 01 — Verify failure experiment authorization

**Procedure:** Confirm disposable cluster, explicit context, target Pod UID, owner, window and rollback.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Capture broker/partition baseline

**Procedure:** Inventory leaders, replicas, ISR, under-minISR partitions and client event ledger.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Capture KRaft quorum baseline

**Procedure:** Map voter IDs, leader, controller placement, network and metadata health.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Model one broker loss

**Procedure:** Calculate RF/minISR availability and affected partition leadership.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Design isolated broker Pod restart

**Procedure:** Define bounded fault, PDB limitations, Kafka health probes and abort thresholds.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Model leader election and client retry

**Procedure:** Predict metadata refresh, acks=all outcomes and producer timeout/duplicate risk.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Model follower replica failure

**Procedure:** Predict ISR shrink, catch-up and recovery bandwidth.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Review partition skew during fault

**Procedure:** Inspect hot partitions, disk utilization and broker capacity reserve.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Model unclean leader election risk

**Procedure:** Confirm safety posture; never enable unsafe election for test convenience.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Design under-minISR safety alarm

**Procedure:** Define critical stop when acks=all writes lose required in-sync replicas.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Design broker disk I/O fault

**Procedure:** Model throttling, log flush, lag and replica recovery without filling prod disks.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Design broker network partition

**Procedure:** Separate client-to-broker and broker-to-broker faults; protect KRaft quorum.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Design single controller interruption

**Procedure:** Validate majority-voter math and controlled isolated recovery.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Model controller majority loss

**Procedure:** Tabletop metadata outage and avoid destructive live quorum-breaking tests.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Review Strimzi reconciliation during failure

**Procedure:** Observe desired state, KafkaNodePool, Pod scheduling and operator events.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Measure producer event correctness

**Procedure:** Compare acknowledged synthetic IDs against consumed durable IDs and duplicates.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Measure consumer recovery

**Procedure:** Track rebalance duration, group stability, lag and downstream freshness.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Measure ISR and replica catch-up

**Procedure:** Track under-replicated duration, disk/network reserve and full restoration.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Validate abort/forward-fix plan

**Procedure:** Define immediate stop, escalation, replacement and evidence preservation.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Independent broker/KRaft acceptance

**Procedure:** Review hypothesis, fault boundary, event correctness, recovery and signoff.

**Required evidence:** UTC time, exact isolated context/namespace/Pod UID, Kafka/Strimzi/KRaft versions, RF/minISR, quorum voters, hypothesis, baseline SLO, synthetic acknowledged/consumed event IDs, expected/observed ISR/leader behavior, fault/abort/recovery timeline, **Tabletop** vs **Live**, owner, rollback and independent reviewer. **Status: Pending** until executed.

## 10. Offline replication and quorum safety validator

Save as `validate_fault_safety.py`. This is a **conservative static model**, not a live Kafka ISR or quorum check.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("plan", help="Reviewed synthetic broker/controller fault plan JSON")
args = p.parse_args()
with open(args.plan, encoding="utf-8") as f:
    d = json.load(f)
required = [
    "environment", "replication_factor", "min_insync_replicas",
    "healthy_isr", "replicas_removed", "controller_voters",
    "controllers_removed", "isolated_context_verified",
    "telemetry_ready", "rollback_approved", "evidence_ref"
]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
ints = required[1:7]
if any(type(d[k]) is not int for k in ints):
    p.error("replication/quorum values must be integers")
rf, misr, isr, removed, voters, lost = (d[k] for k in ints)
valid = (rf >= 1 and 1 <= misr <= rf and 0 <= isr <= rf
         and 0 <= removed <= rf and voters >= 1 and 0 <= lost <= voters)
remaining_isr = isr - removed
remaining_voters = voters - lost
majority = voters // 2 + 1
checks = {
    "valid_configuration": valid,
    "replication_writes_survive_model": valid and remaining_isr >= misr,
    "kraft_quorum_survives_model": valid and remaining_voters >= majority,
    "isolated_environment": d["environment"] == "disposable-lab",
    "context_verified": d["isolated_context_verified"] is True,
    "telemetry_ready": d["telemetry_ready"] is True,
    "rollback_approved": d["rollback_approved"] is True,
    "evidence_reference": bool(d["evidence_ref"])
}
passed = all(checks.values())
print(json.dumps({"checks": checks, "remaining_isr_model": remaining_isr,
                  "remaining_controller_voters_model": remaining_voters,
                  "required_controller_majority": majority,
                  "ready_for_separate_approval": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Model limitations:** Assumes removed replicas were in ISR, ignores partition-specific placement, dynamic controller membership, rack failure correlations, leader election, storage and network health. Passing does not authorize a live experiment.

## 11. Twelve broker/KRaft failure scenarios

### Scenario 01 — Broker restart causes minISR write unavailability

**Diagnosis:** Abort; restore healthy replicas and review RF/minISR and placement. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 02 — Leader election triggers producer timeouts

**Diagnosis:** Assess retry/idempotence and reconcile acknowledged event IDs. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 03 — Follower replica never rejoins ISR

**Diagnosis:** Inspect fetcher lag, storage, network and replica assignment. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 04 — Controller quorum loses majority

**Diagnosis:** Stop fault, preserve state and follow controlled quorum recovery procedure. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 05 — Unclean leader election threatens data

**Diagnosis:** Reject unsafe setting; investigate availability without accepting data loss. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 06 — Strimzi operator recreates unexpected broker

**Diagnosis:** Check KafkaNodePool desired state, GitOps drift and scheduling. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 07 — Broker PVC becomes read-only or full

**Diagnosis:** Protect log integrity, capacity and restore using approved storage runbook. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 08 — Network partition causes repeated leader churn

**Diagnosis:** Restore network, inspect ISR and broker/controller connectivity. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 09 — Producer acknowledges missing events

**Diagnosis:** Treat as correctness incident; reconcile ledger and halt experiment. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 10 — Consumer group duplicates side effects

**Diagnosis:** Review offset commit ordering, idempotency and sink semantics. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 11 — Fault target resolves to production Pod

**Diagnosis:** Abort immediately; require context and UID allowlisting. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

### Scenario 12 — Metrics disappear during failover

**Diagnosis:** Mark experiment inconclusive and restore telemetry before retest. Review Kafka leader/ISR, under-minISR, broker storage/network, controller voter majority, Strimzi reconciliation, producer acknowledgement ledger and consumer lag. **Response:** Stop the bounded fault, restore availability without sacrificing data durability, preserve UTC evidence and notify incident command. **Exit:** Healthy quorum/ISR, reconciled acknowledged IDs, stable clients, RCA and independent approval.

## 12. Eight production recovery runbooks

### Runbook A — Broker fault preflight

**Trigger/actions:** Verify isolated context, RF/minISR, quorum, PDB, storage reserve and SLO. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook B — Broker restart recovery

**Trigger/actions:** Stop fault, monitor leader election, ISR, clients and event ledger. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook C — Partition leader/ISR instability

**Trigger/actions:** Review replicas, leader, minISR, disk/network and client acks. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook D — KRaft controller recovery

**Trigger/actions:** Protect voter majority, avoid ad hoc metadata changes and restore quorum. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook E — Broker storage failure

**Trigger/actions:** Contain I/O fault, validate PVC, log dirs, reassignment and free capacity. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook F — Broker network isolation

**Trigger/actions:** Restore replication/client paths, inspect rack/AZ connectivity and ISR. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook G — Producer/consumer correctness

**Trigger/actions:** Reconcile synthetic IDs, duplicate handling, lag and sink integrity. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

### Runbook H — Post-fault RCA and acceptance

**Trigger/actions:** Document timeline, recovery objectives, failed assumptions and independent review. **No-go:** unknown context, production target, controller majority risk, under-minISR baseline, absent event ledger, unsafe leader election, no abort or rollback. **Exit:** Fault removed, leaders/ISR and quorum stable, synthetic event correctness verified, client SLO recovered and evidence reviewed.

## 13. Evidence package

```text
evidence-ch092/
  01-authorization.md
  02-partition-baseline.md
  03-kraft-quorum-baseline.md
  04-broker-loss-model.md
  05-broker-restart-design.md
  06-leader-election-client-retry.md
  07-follower-isr.md
  08-partition-skew.md
  09-unclean-election-review.md
  10-minisr-alarm.md
  11-broker-disk-io.md
  12-broker-network-partition.md
  13-controller-interruption.md
  14-controller-majority-tabletop.md
  15-strimzi-reconciliation.md
  16-producer-event-ledger.md
  17-consumer-recovery.md
  18-replica-catchup.md
  19-abort-forward-fix.md
  20-independent-acceptance.md
  fault-safety-plan.json
  scorecard.md
```

Every artifact must include UTC time, environment, Kafka/Strimzi version, **Tabletop** vs **Live**, hypothesis, baseline, target, fault duration, expected/observed, acknowledged-event reconciliation, abort/rollback, SLO recovery and independent reviewer.

## 14. 100-point broker and KRaft acceptance

| Domain | Points | Critical |
|---|---:|---|
| Fault authorization, baseline and telemetry | 20 | Yes |
| RF/minISR, leader and ISR resilience | 25 | Yes |
| KRaft quorum and failure-domain safety | 20 | Yes |
| Producer/consumer correctness and recovery | 20 | Yes |
| Runbooks, rollback and evidence | 5 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced. **Automatic Fail:** unapproved production fault, quorum loss, unexpected under-minISR, missing acknowledged event IDs, unsafe unclean election, no abort control or fabricated live results.

**Current status:** **Pending**. No live broker/partition/controller fault is claimed.

## 15. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 093 — Kafka Network, Storage and Availability Zone Chaos Engineering.

---

**Verification boundary:** Publication confirms document availability only. Live fault injection, ISR/quorum recovery timing, synthetic event reconciliation and independent technical/security review remain Pending.
