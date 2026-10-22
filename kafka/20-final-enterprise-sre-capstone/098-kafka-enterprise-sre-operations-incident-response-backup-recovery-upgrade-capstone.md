# Chapter 098 — Kafka Enterprise SRE Operations, Incident Response, Backup, Recovery and Upgrade Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 20 — Final Enterprise SRE Capstone (3/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on Amazon EKS; Amazon MSK operational comparison  
**Prerequisites:** Chapters 001–097  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter provides production-oriented **runbooks and isolated-lab designs**, not authorization to change a production cluster. Never remove KRaft voters, delete PVCs, force unclean leader election, run unsupported Kafka downgrades, or execute unapproved DR cutovers. Use synthetic events only; no PHI, secrets or patient identifiers in evidence. Restore, upgrade and failure tests require change approval, backups, rollback/forward-fix and independent reviewers.

## 1. Mission and operating model

Build an enterprise SRE operating model for Kafka: **SLO-based detection, incident command, broker/KRaft/ISR troubleshooting, producer/consumer/Connect correctness, backup and restore, AZ/region DR, version-safe upgrades, post-incident RCA and independent operational acceptance**.

Operational readiness is not established by documentation alone. Each runbook needs evidence of approved rehearsal, measured recovery and reviewer signoff.

## 2. Incident architecture and escalation

```text
Kafka / KRaft / EKS / EBS / clients / Connect
                  |
        metrics + logs + traces
                  |
        SLO alerts + anomaly detection
                  |
          on-call SRE / DBRE
                  |
       incident commander + severity
                  |
       mitigation + change freeze
                  |
       Kafka state + client ledger
                  |
       recovery + business validation
                  |
         RCA / COA / acceptance
```

Separate infrastructure health from **business correctness**: healthy broker Pods do not prove that acknowledged synthetic events reached a consumer, warehouse, search index or downstream sink.

## 3. Service levels and critical alerting

| Signal | Critical interpretation | Response |
|---|---|---|
| Under-minISR partitions | acks=all write availability/durability risk | protect ISR and restore replicas |
| Offline partitions | partition availability outage | inspect leaders, quorum and replicas |
| KRaft controller majority | metadata/control-plane risk | preserve voters, stop disruptive changes |
| Producer errors/P99 | ingest SLO impact | correlate acks, retries and leader election |
| Consumer lag/freshness | downstream service delay | inspect processing, group and sink |
| Connect/CDC task failures | source/sink pipeline risk | inspect offsets, DLQ and log retention |
| EBS latency/capacity | replication and write latency risk | inspect IOPS, queue, volume and node |
| TLS/auth failures | connectivity or access issue | review certificate and ACL changes |
| Event-ledger mismatch | end-to-end data correctness incident | halt replay and reconcile IDs |

Alert thresholds, error-budget burn rates and SEV levels are workload-specific and must be approved by service owners.

## 4. Broker, ISR and KRaft incident response

Start with read-only evidence: Kafka CR/Pod status, leader and ISR per partition, under-minISR and offline partitions, controller voter health, broker disk/network and recent GitOps changes.

For a broker outage, distinguish follower loss, leader loss, disk pressure and AZ correlation. Avoid raising write availability by lowering minISR or enabling unclean leader election without an explicit data-loss decision from authorized owners.

For KRaft, controller majority and metadata state require version-specific supported procedures. Do not delete quorum metadata, modify voter sets ad hoc or conflate controller leader failover with broker partition leadership.

## 5. Producer/consumer and Connect correctness

Producer timeouts can be ambiguous: a broker may have accepted a record even if the client did not receive the acknowledgement. Track unique synthetic IDs, producer idempotence and transaction semantics.

Consumer offset commits may precede or follow sink side effects; replay can duplicate external writes. Validate idempotent sink materialization, consumer lag drain, rebalance stability and source-to-sink freshness.

Connect/CDC incidents require task status, connector offsets, source log retention, DLQ and schema evolution checks. Do not resnapshot or reset offsets without source/sink owner approval and data reconciliation.

## 6. Backup scope and recovery semantics

**Kafka is not automatically a backup system.** Topic replication protects availability from some failures but not necessarily accidental deletion, bad producer writes, corruption propagated to replicas or region-wide loss.

Back up or reproducibly manage:
- GitOps manifests, topic configs, KafkaUser/ACL and infrastructure configuration.
- Kafka records via an approved topic-data backup/export or replicated secondary cluster with measured recovery point.
- Schema registry contracts, Connect configuration/offsets, consumer group recovery state, secrets references and certificate lifecycle.
- Source CDC position, DLQ, sink materializations, retention/legal hold and lineage.

Do not assume that snapshots of live broker PVCs independently form a consistent, portable Kafka cluster backup. Validate backup/restore procedures for the deployed Kafka/KRaft/Strimzi versions.

## 7. Restore and disaster recovery design

A clean-room restore drill should provision an isolated cluster, restore or replay topic data using a supported method, rebuild metadata/config and security, validate offsets/consumer state, restart Connect safely and reconcile synthetic event IDs.

Cross-region replication is commonly asynchronous. Measure lag and potential unreplicated tail; define RPO and cutover policy, client DNS/endpoint updates, credentials, network and downstream consistency. **Never promise zero data loss without end-to-end evidence.**

EBS volumes are AZ-scoped; node or AZ recovery must respect PV topology and Kafka broker identity.

## 8. Upgrade and rollback engineering

Validate the exact supported Kafka, Strimzi, Kubernetes, EKS, JVM and client/connector compatibility matrix. Use staging first, pinned images/manifests, GitOps PRs, maintenance window, backups, canary checks and phased rollout.

Kafka metadata and protocol upgrades may have irreversible steps; **rollback of manifests is not necessarily a supported Kafka downgrade**. Define forward-fix, restore and cutover alternatives before production change.

Monitor KRaft quorum, leader/ISR, P99, lag, Connect, disk and synthetic event correctness throughout.

## 9. Read-only incident inventory

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get pvc -A
kubectl get pdb -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Commands are read-only; CRD availability varies. Use version-specific authenticated Kafka admin clients to inspect partition and KRaft state. Sanitize outputs before storing evidence.

## 10. Twenty SRE operations and recovery labs

### Lab 01 — Establish operational readiness charter

**Procedure:** Document environment, on-call, RACI, SLO, escalation, change windows and evidence owner.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 02 — Capture Kafka and KRaft baseline

**Procedure:** Inventory brokers/controllers, RF/minISR, ISR, quorum, topics, PVC and versions.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 03 — Define SLO and alert routing

**Procedure:** Review producer ack P99, errors, consumer freshness, Connect/CDC and under-minISR.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 04 — Create incident severity matrix

**Procedure:** Map data correctness, quorum, partition availability, lag and privacy to severity.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 05 — Build incident timeline template

**Procedure:** Specify UTC timestamps, commander, communications, hypothesis and decisions.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 06 — Investigate broker failure

**Procedure:** Correlate leader election, ISR, request P99, storage and Strimzi reconciliation.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 07 — Investigate KRaft quorum instability

**Procedure:** Review voter majority, controller connectivity, metadata requests and safe recovery.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 08 — Investigate replication and partition issues

**Procedure:** Assess under-minISR, under-replicated partitions, follower lag and reassignment.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 09 — Investigate EBS/PVC saturation

**Procedure:** Review disk capacity, IOPS/throughput, queue depth and AZ-bound volume topology.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 10 — Investigate client delivery failures

**Procedure:** Review producer acknowledgements, retry/idempotence and synthetic event ledger.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 11 — Investigate consumer lag and rebalances

**Procedure:** Correlate group assignments, offsets, downstream backpressure and freshness.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 12 — Investigate Kafka Connect/CDC outage

**Procedure:** Check worker/task health, DLQ, source log window, offsets and sink correctness.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 13 — Design configuration and metadata backup

**Procedure:** Inventory GitOps, Kafka topic/ACL configs, certificates, secrets references and restore scope.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 14 — Design topic data backup and replication

**Procedure:** Compare approved export, cross-cluster replication, retention, lag and RPO.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 15 — Design isolated restore drill

**Procedure:** Specify clean-room cluster, recovered offsets, schemas, clients and event reconciliation.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 16 — Design multi-AZ and cross-region DR

**Procedure:** Define failure-domain recovery, MirrorMaker limitations, DNS/client cutover and RTO.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 17 — Design Strimzi/Kafka upgrade plan

**Procedure:** Review supported version matrix, preflight, controller/broker sequencing and rollback limits.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 18 — Design Kubernetes/EKS and storage upgrade

**Procedure:** Review node draining, PDB, EBS CSI, storage, quota and Kafka availability.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 19 — Exercise incident tabletop and RCA

**Procedure:** Run synthetic SEV exercise, communications, mitigations and corrective actions.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

### Lab 20 — Complete independent operations acceptance

**Procedure:** Score runbooks, backup/restore evidence, upgrade gates and signoff.

**Required evidence:** UTC timestamp, isolated environment/context, Kafka/Strimzi/EKS version, incident hypothesis, baseline SLO and quorum/ISR, expected/observed, synthetic acknowledged/sink IDs, recovery and rollback plan, RPO/RTO where relevant, **Tabletop** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until performed.

## 11. Offline incident/DR readiness validator

Save as `validate_ch098_operational_readiness.py`. It validates a reviewed **synthetic JSON readiness manifest**; it does not test a real restore, upgrade or incident response.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("manifest", help="Reviewed synthetic operations readiness JSON")
args = p.parse_args()
with open(args.manifest, encoding="utf-8") as f:
    d = json.load(f)
required = [
    "environment", "incident_commander", "on_call_owner", "slo_defined",
    "kraft_quorum_verified", "min_isr_verified", "backup_scope_documented",
    "restore_drill_live_verified", "rpo_rto_measured",
    "upgrade_compatibility_reviewed", "rollback_or_forward_fix_approved",
    "event_ids_reconciled", "independent_sre_review",
    "independent_security_review", "evidence_ref"
]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
checks = {
    "isolated_environment": d["environment"] == "disposable-lab",
    "incident_ownership": bool(d["incident_commander"] and d["on_call_owner"]),
    "slo": d["slo_defined"] is True,
    "kraft_quorum": d["kraft_quorum_verified"] is True,
    "min_isr": d["min_isr_verified"] is True,
    "backup_scope": d["backup_scope_documented"] is True,
    "live_restore": d["restore_drill_live_verified"] is True,
    "measured_rpo_rto": d["rpo_rto_measured"] is True,
    "upgrade_review": d["upgrade_compatibility_reviewed"] is True,
    "rollback": d["rollback_or_forward_fix_approved"] is True,
    "data_correctness": d["event_ids_reconciled"] is True,
    "sre_review": d["independent_sre_review"] is True,
    "security_review": d["independent_security_review"] is True,
    "evidence": bool(d["evidence_ref"])
}
passed = all(checks.values())
print(json.dumps({"checks": checks, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitations:** The validator trusts self-reported flags and cannot verify Kafka data durability, restore completeness, measured RPO/RTO, supported upgrades or reviewer identity. Attach actual evidence before any production acceptance.

## 12. Twelve enterprise incident scenarios

### Scenario 01 — Broker restart triggers unexpected unavailable partitions

**Diagnosis:** Protect ISR/minISR, inspect leader elections and recover healthy replicas. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 02 — KRaft controller majority becomes unavailable

**Diagnosis:** Stop changes, preserve voter metadata and follow supported quorum recovery. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 03 — EBS latency causes ISR shrink and P99 regression

**Diagnosis:** Review IOPS/throughput/queue depth, recovery reserve and broker load. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 04 — Producer reports timeout but event is committed

**Diagnosis:** Reconcile acknowledged/ambiguous synthetic IDs before application replay. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 05 — Consumer lag persists after broker recovery

**Diagnosis:** Investigate downstream sink, partition skew, rebalance and processing capacity. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 06 — Connect source task fails after log expiry

**Diagnosis:** Protect source retention, assess snapshot/recovery and data owner approval. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 07 — Backup restores configs but not event data

**Diagnosis:** Reject RPO claim and validate complete backup scope and topic offsets. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 08 — Cross-region mirror has unreplicated tail

**Diagnosis:** Measure replication lag and reconcile cutover RPO explicitly. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 09 — Upgrade changes Kafka protocol compatibility

**Diagnosis:** Stop rollout, inspect supported upgrade path and client/connector versions. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 10 — GitOps reverts emergency configuration

**Diagnosis:** Coordinate desired state, incident commander and reviewed forward-fix. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 11 — Rollback would require unsupported downgrade

**Diagnosis:** Use documented restore/forward-fix; never assume metadata downgrade. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

### Scenario 12 — RCA closes without end-to-end correctness

**Diagnosis:** Block closure until acknowledged IDs and downstream effects reconcile. Correlate Kafka/KRaft state, leader/ISR, broker disk/network, Strimzi and EKS events, producer/consumer/Connect offsets, synthetic event ledger, change history and SLO. **Response:** Declare incident severity, freeze risky changes, restore durability and service, coordinate data replay and preserve sanitized evidence. **Exit:** Kafka and pipeline stable, event correctness reconciled, recovery objectives assessed, RCA and independent signoff.

## 13. Eight production SRE runbooks

### Runbook A — Incident intake, SEV and command

**Trigger/actions:** Validate symptoms, SLO impact, owner, change freeze and communications. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook B — Broker/ISR and partition availability

**Trigger/actions:** Inspect leader, replicas, minISR, storage, rack placement and safe restoration. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook C — KRaft controller quorum protection

**Trigger/actions:** Preserve majority, collect logs, avoid ad hoc voter manipulation and restore safely. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook D — Producer/consumer correctness

**Trigger/actions:** Reconcile synthetic acknowledged IDs, offsets, duplicate side effects and freshness. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook E — Connect/CDC and sink incident

**Trigger/actions:** Protect source log window, task offsets, DLQ and downstream consistency. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook F — Backup, restore and DR cutover

**Trigger/actions:** Validate scope, RPO/RTO, replica lag, client cutover and recovery evidence. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook G — Kafka/Strimzi/EKS upgrade and rollback

**Trigger/actions:** Review compatibility, staging, phased rollout, abort and restore limits. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

### Runbook H — Post-incident RCA and acceptance

**Trigger/actions:** Document timeline, contributing factors, actions, ownership and independent review. **No-go:** unknown environment, unsupported upgrade/downgrade, controller majority risk, unapproved PVC deletion, missing data backup, unexplained acknowledged event loss, PHI exposure or absent rollback. **Exit:** Verified restoration, client correctness, SLO/RPO/RTO evidence, change record and independent review.

## 14. Evidence package

```text
evidence-ch098/
  01-operating-charter.md
  02-kafka-kraft-baseline.md
  03-slo-alert-routing.md
  04-incident-severity.md
  05-incident-timeline.md
  06-broker-failure.md
  07-kraft-quorum.md
  08-replication-isr.md
  09-ebs-pvc.md
  10-producer-ledger.md
  11-consumer-lag.md
  12-connect-cdc.md
  13-config-metadata-backup.md
  14-topic-data-backup.md
  15-clean-room-restore.md
  16-az-region-dr.md
  17-kafka-strimzi-upgrade.md
  18-eks-storage-upgrade.md
  19-incident-rca-tabletop.md
  20-independent-operations-acceptance.md
  operational-readiness.json
  rpo-rto-scorecard.md
```

Every artifact includes UTC time, exact environment and version, **Tabletop** vs **Live Executed**, hypothesis, baseline, change/incident owner, expected/observed, recovery timeline, event ledger, rollback, evidence and independent reviewer.

## 15. 100-point enterprise SRE operations acceptance

| Domain | Points | Critical |
|---|---:|---|
| SLO, observability, on-call and incident command | 20 | Yes |
| Broker/KRaft/ISR incident recovery | 20 | Yes |
| Producer/consumer/Connect correctness | 15 | Yes |
| Backup, restore, RPO/RTO and DR evidence | 25 | Yes |
| Kafka/Strimzi/EKS upgrade and rollback safety | 10 | Yes |
| Independent SRE/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced, including live restore/DR rehearsal in an approved isolated environment. **Automatic Fail:** unapproved production change, unsafe controller quorum, under-minISR data-risk acceptance without authorization, missing backup/restore evidence, unexplained acknowledged event loss, unsupported downgrade or fabricated live results.

**Current status:** **Pending**. Publication is verified; live incident/restore/upgrade rehearsals and independent review are not claimed.

## 16. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 099 — Kafka Enterprise Reliability Validation, Chaos Game Day, Performance and Disaster Recovery Acceptance.

---

**Verification boundary:** Publication confirms document availability only. Live incident response, restore, upgrade, RPO/RTO measurement and independent SRE/security review remain Pending.
