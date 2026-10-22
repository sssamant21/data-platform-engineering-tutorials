# Chapter 099 — Kafka Enterprise Reliability Validation, Chaos Game Day, Performance and Disaster Recovery Acceptance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 20 — Final Enterprise SRE Capstone (4/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on Amazon EKS; Amazon MSK comparison  
**Prerequisites:** Chapters 001–098  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter defines a gated enterprise reliability campaign, not a completed performance test or production chaos authorization. Use an approved disposable cluster, synthetic events, explicit kube context/namespace/target allowlist, workload caps, fault TTL, incident commander and rollback. Never inject faults into production Kafka/KRaft, EBS, VPC, AZ, CDC or healthcare feeds. No PHI/PII or secrets in evidence.

## 1. Mission and acceptance outcome

Validate the Kafka platform designed in Chapter 096, built in Chapter 097 and operationalized in Chapter 098 against **measurable performance, failure-domain resilience, client/streaming correctness, backup/restore, cross-region disaster recovery, SLO detection and independent enterprise reliability gates**.

Chapter 099 is the last engineering validation capstone before Chapter 100's final assessment. **Documentation publication is not execution evidence.**

## 2. Integrated validation architecture

```text
Business SLO / RPO / RTO / security owner
                     |
         reliability test charter
                     |
  isolated EKS + Strimzi KRaft Kafka cluster
       /           |            \
    brokers     controllers    EBS/PVC + AZ
       |           |            |
       +---- topics RF/minISR --+
                     |
synthetic producer -> Kafka -> consumer / Connect
        |                        |
 acknowledged IDs         sink materialized IDs
        +------------+-----------+
                     |
          independent correctness oracle
                     |
  metrics + traces + alerts + incident command
                     |
    load / chaos / restore / DR tabletop
                     |
        abort -> recovery -> scorecard
                     |
       independent SRE/security signoff
```

## 3. Reliability hypotheses and no-go gates

| Hypothesis | Metric | Hard stop |
|---|---|---|
| Performance within SLO | producer P99, throughput, errors | error budget or saturation breach |
| Durable ingestion | acknowledged synthetic IDs | unexplained missing acknowledged ID |
| Partition resilience | leader/ISR, under-minISR | unexpected under-minISR |
| Metadata resilience | KRaft voter majority | controller majority threatened |
| Client recovery | consumer lag and freshness | unbounded lag or irreversible side effect |
| Connect/CDC continuity | source log window, task lag | log expiry or data gap risk |
| Storage safety | PVC free space, IOPS, queue | log corruption or critical disk reserve |
| DR readiness | measured RPO/RTO | unsupported cutover or missing restore proof |
| Security | ACL/TLS, data classification | PHI exposure or unauthorized access |

Workload owners must define numeric SLOs, RPO/RTO and allowable fault durations. Do not invent universal Kafka thresholds.

## 4. Performance engineering protocol

Measure a stable baseline, then controlled throughput ramp, burst and sustained soak in an isolated cluster. Capture request P50/P95/P99, producer errors/retries, broker CPU, network, disk IOPS/throughput/latency, page cache/heap, partition skew, consumer lag and Connect task backlog.

Use representative synthetic event sizes and keys. Compare steady-state, fault and recovery windows. A throughput increase is not acceptable if event correctness or minISR fails.

## 5. Broker and KRaft chaos campaign

Model single broker restart, partition leader movement, follower catch-up, under-replication and controller interruption while preserving KRaft majority. RF=3/minISR=2 does not guarantee N-1 AZ survivability without rack-aware replica distribution and capacity.

Unclean leader election, controller-majority loss and destructive PVC changes are excluded from live fault scope.

## 6. Network, storage and AZ campaign

Evaluate client/broker latency, broker replication loss, DNS, EBS/PVC throttling and correlated AZ outages. EBS volumes are AZ-bound; recovery depends on storage topology and broker identity. Model a single AZ outage tabletop before any independently approved isolated live experiment.

Track replication catch-up and backlog drain **after** fault removal, not merely first successful request.

## 7. Producer, consumer and Connect correctness

Use a synthetic event oracle: every successfully acknowledged unique producer event must be accounted for by the approved downstream semantics. Model ambiguous acknowledgements, consumer replay, sink idempotency, schema/DLQ, Connect task restarts, CDC log retention and stateful stream recovery.

Kafka's idempotent producer and transactions do not guarantee exactly-once external business side effects. For upserts/aggregations, build a domain-specific oracle rather than assuming one sink row per input.

## 8. Backup, restore and cross-region DR

A clean-room restore must prove recoverability of Kafka records **and** topic configs, schemas, ACLs, connector state, offsets and client/sink behavior. Replication alone is not a substitute for point-in-time recovery from accidental deletion or bad writes.

For cross-region DR, measure mirror lag and potential unreplicated tail, cutover timing, client endpoint/credential changes and downstream consistency. Treat RPO=0 as unproven unless end-to-end measured and supported.

## 9. Incident command and acceptance evidence

Assign incident commander, technical leads, change owner, security/privacy contact, observer and independent reviewer. Capture UTC start/stop, baseline, hypothesis, exact target, alerts, mitigations, abort, rollback, recovery, event reconciliation, RPO/RTO and action items.

**Tabletop**, **Simulated**, **Live Executed** and **Independently Reviewed** are distinct evidence states. Never upgrade status without corresponding proof.

## 10. Read-only platform inspection

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pvc -A
kubectl get pdb -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

The CRDs require Strimzi installation. These commands do not inject faults and are not execution evidence until run and saved.

## 11. Twenty enterprise reliability validation labs

### Lab 01 — Authorize integrated reliability campaign

**Procedure:** Define isolated lab, approvers, game-day commander, time box, abort and evidence scope.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 02 — Freeze architecture and version baseline

**Procedure:** Capture Kafka/Strimzi/EKS/client versions, Git SHA, topology and security config.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 03 — Verify synthetic data correctness oracle

**Procedure:** Build acknowledged-ID, consumer and sink ledgers with consistency boundaries.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 04 — Measure steady-state performance

**Procedure:** Benchmark ingest, P50/P95/P99, throughput, consumer freshness and Connect lag.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 05 — Measure burst and sustained load

**Procedure:** Define bounded load ramp, soak duration, error budget and saturation limits.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 06 — Validate partition distribution and skew

**Procedure:** Review leader count, hot partitions, broker disk/network/CPU and consumer parallelism.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 07 — Validate broker N-1 resilience

**Procedure:** Model leader failover, ISR/minISR and recovery headroom under one broker loss.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 08 — Validate KRaft controller N-1

**Procedure:** Model voter majority and metadata availability with a single controller interruption.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 09 — Validate replication network degradation

**Procedure:** Model ISR shrink, producer retries, broker catch-up and hard stop.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 10 — Validate EBS/PVC I/O pressure

**Procedure:** Model queue depth, IOPS/throughput throttling and disk recovery.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 11 — Validate single-AZ resilience

**Procedure:** Assess controller/replica placement, PV topology, N-1 capacity and client routing.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 12 — Validate producer crash correctness

**Procedure:** Reconcile acked/ambiguous IDs, idempotence and replay behavior.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 13 — Validate consumer restart correctness

**Procedure:** Assess rebalances, offset commits, duplicates and lag drain.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 14 — Validate Connect/CDC source outage

**Procedure:** Assess task failover, source log window, schema and sink reconciliation.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 15 — Validate DLQ and schema recovery

**Procedure:** Use synthetic poison event, quarantining, alerting and replay approvals.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 16 — Validate clean-room topic data restore

**Procedure:** Measure restore completeness, recovered offsets, schema/ACL and event ledger.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 17 — Validate cross-region DR tabletop

**Procedure:** Estimate mirror lag, cutover sequencing, RPO/RTO and client/sink recovery.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 18 — Validate alert and incident command

**Procedure:** Measure detection, paging, escalation, timeline, abort and RCA evidence.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 19 — Evaluate cost and recovery headroom

**Procedure:** Assess load costs, cross-AZ traffic, recovery bandwidth and FinOps guardrails.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 20 — Independent reliability acceptance review

**Procedure:** Score critical gates, record exceptions, attach proof and require signoff.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/EKS version and Git SHA, hypothesis, baseline SLO, exact fault/load target, duration, expected/observed, synthetic acknowledged/sink ID reconciliation, recovery timing, RPO/RTO when applicable, abort/rollback, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

## 12. Offline reliability acceptance validator

Save as `validate_ch099_reliability.py`. It checks a **reviewed synthetic JSON scorecard**; it does not run load tests, faults or restores.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("scorecard", help="Reviewed synthetic reliability scorecard JSON")
args = p.parse_args()
with open(args.scorecard, encoding="utf-8") as f:
    d = json.load(f)
weights = {
    "performance_slo": 20,
    "broker_kraft_replication": 20,
    "network_storage_az": 15,
    "pipeline_correctness": 15,
    "restore_dr_rpo_rto": 20,
    "independent_review": 10,
}
required = ["scores", "critical_gates", "live_evidence_verified",
            "acknowledged_event_loss", "unapproved_production_fault",
            "independent_sre_review", "independent_security_review", "evidence_ref"]
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
    p.error("critical_gates must be nonempty")
total = sum(scores.values())
passed = (
    total >= 85 and all(v is True for v in gates.values())
    and d["live_evidence_verified"] is True
    and d["acknowledged_event_loss"] is False
    and d["unapproved_production_fault"] is False
    and d["independent_sre_review"] is True
    and d["independent_security_review"] is True
    and bool(d["evidence_ref"])
)
print(json.dumps({"score": total, "maximum": 100, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitations:** A passing JSON scorecard does not verify actual Kafka metrics, event reconciliation, fault scope, restore completeness or reviewer identity. Attach independent primary evidence and repeat tests after remediation.

## 13. Twelve reliability campaign failure scenarios

### Scenario 01 — Load test saturates brokers before target throughput

**Diagnosis:** Stop ramp and inspect partition skew, CPU, disk, network and request P99. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 02 — Producer latency improves but acknowledged IDs disappear

**Diagnosis:** Fail correctness gate; do not accept performance-only results. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 03 — One broker loss breaches minISR

**Diagnosis:** Stop fault, restore replicas and revise placement or capacity. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 04 — KRaft controller loss breaks majority

**Diagnosis:** Abort and correct quorum topology before retesting. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 05 — Cross-AZ network fault causes widespread retries

**Diagnosis:** Restore network, measure ISR catch-up and reconcile client events. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 06 — EBS IOPS throttling causes replication lag

**Diagnosis:** Protect disk reserve, recover storage performance and track ISR. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 07 — AZ outage model shows controller majority lost

**Diagnosis:** Fail N-1 readiness and redesign voter placement. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 08 — Consumer lag remains elevated after fault ends

**Diagnosis:** Investigate sink backpressure, rebalance and partition skew. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 09 — Connect task restarts but CDC gap remains

**Diagnosis:** Review source log expiry, offsets, snapshot and sink reconciliation. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 10 — Restore contains topics but omits security/schema

**Diagnosis:** Reject recovery proof and validate complete recovery scope. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 11 — DR cutover exceeds approved RPO/RTO

**Diagnosis:** Document gap, redesign replication/cutover and repeat exercise. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

### Scenario 12 — Game-day report labels tabletop as live

**Diagnosis:** Reject acceptance; preserve provenance and independent review. Correlate load/P99, broker/KRaft/ISR, EBS/network/AZ, producer/consumer/Connect, synthetic event ledger, alerts and DR evidence. **Response:** Abort unsafe test, restore Kafka/data correctness, preserve sanitized UTC evidence and notify incident command. **Exit:** SLO recovered, all critical gates passed, discrepancies resolved, RCA and independent review.

## 14. Eight production reliability runbooks

### Runbook A — Reliability campaign preflight

**Trigger/actions:** Approve isolated targets, versions, synthetic oracle, telemetry, abort and rollback. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook B — Load and saturation response

**Trigger/actions:** Stop ramp, preserve broker/client SLO and analyze capacity bottlenecks. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook C — Broker/KRaft/ISR failure response

**Trigger/actions:** Restore quorum/replicas and reconcile acknowledged event IDs. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook D — Network/storage/AZ chaos recovery

**Trigger/actions:** Restore network, disk, PVC topology and replication health. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook E — Producer/consumer/Connect correctness

**Trigger/actions:** Reconcile acknowledgements, offsets, DLQ, CDC and sink effects. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook F — Backup/restore and DR acceptance

**Trigger/actions:** Verify data, schema, ACL, offsets, RPO/RTO and downstream state. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook G — Incident command and communications

**Trigger/actions:** Declare severity, freeze changes, capture timeline, alert and escalate. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

### Runbook H — Independent reliability signoff

**Trigger/actions:** Score critical gates, record exceptions, owners and re-test requirements. **No-go:** wrong context, unapproved production chaos, lost KRaft majority, unexpected under-minISR, missing acknowledged events, unsupported restore/cutover, no rollback or sensitive data exposure. **Exit:** Fault/load removed, cluster and clients stable, end-to-end ledger reconciled, recovery measured and independent review complete.

## 15. Evidence package

```text
evidence-ch099/
  01-campaign-authorization.md
  02-version-architecture-baseline.md
  03-synthetic-event-oracle.md
  04-steady-state-performance.md
  05-burst-soak-load.md
  06-partition-skew.md
  07-broker-n-minus-one.md
  08-kraft-controller-n-minus-one.md
  09-replication-network.md
  10-ebs-pvc.md
  11-az-resilience.md
  12-producer-crash.md
  13-consumer-restart.md
  14-connect-cdc.md
  15-schema-dlq.md
  16-clean-room-restore.md
  17-cross-region-dr.md
  18-incident-command.md
  19-capacity-finops.md
  20-independent-reliability-review.md
  reliability-scorecard.json
  exceptions-and-remediation.md
```

Every artifact includes UTC time, exact environment and version, **Tabletop** vs **Live Executed**, hypothesis, baseline, fault/load scope, expected/observed, synthetic event ledger, RPO/RTO, abort/rollback, evidence source and independent reviewer.

## 16. 100-point enterprise reliability acceptance

| Domain | Points | Critical |
|---|---:|---|
| Performance and SLO validation | 20 | Yes |
| Broker/KRaft/replication resilience | 20 | Yes |
| Network, storage and AZ resilience | 15 | Yes |
| Producer/consumer/Connect correctness | 15 | Yes |
| Backup/restore, DR and RPO/RTO | 20 | Yes |
| Independent SRE/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced by approved live tests, including restore validation. **Automatic Fail:** unapproved production fault, lost KRaft majority, unexpected under-minISR, unexplained acknowledged event loss, DR evidence gap, unsafe data handling or fabricated live results.

**Current status:** **Pending**. Chapter publication is complete; performance, chaos, restore, DR and independent review have not been executed.

## 17. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 100 — Kafka Enterprise SRE Final Assessment, Production Readiness and Operational Certification Capstone.

---

**Verification boundary:** Publication confirms document availability only. Live performance/chaos/restore/DR execution and independent SRE/security review remain Pending.
