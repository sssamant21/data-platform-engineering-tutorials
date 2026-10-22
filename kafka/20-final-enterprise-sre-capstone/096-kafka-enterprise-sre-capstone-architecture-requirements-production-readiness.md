# Chapter 096 — Kafka Enterprise SRE Capstone Architecture, Requirements and Production Readiness

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 20 — Final Enterprise SRE Capstone (1/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on Amazon EKS; Amazon MSK alternative  
**Prerequisites:** Chapters 001–095  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety and scope:** This chapter establishes a reference architecture and readiness criteria, not an approved production deployment. Use only synthetic healthcare-like events; no PHI/PII, secrets or real patient identifiers in labs/evidence. Production Kafka, IAM, EKS, networking, CDC, retention and DR changes require owner, security/privacy and change approval. Never treat a published design as a tested system.

## 1. Capstone mission

Design a production-ready, auditable Kafka streaming platform integrating **Kafka brokers and KRaft controllers, Strimzi on EKS, private networking, least-privilege identities, schema/data governance, Connect/CDC, producer/consumer correctness, observability, HA/DR, capacity/FinOps, upgrades and SRE operations**.

The final five chapters are progressive: **096 architecture/readiness; 097 build and deployment; 098 operations/incident recovery; 099 reliability validation; 100 final enterprise assessment**.

## 2. Business requirements and service boundaries

Example synthetic healthcare workload: producers publish encounter-change events keyed by synthetic patient identifier; Kafka retains approved events; Connect/CDC and consumer applications feed an operational read model, search, analytics warehouse and cache. This is a reference workload, not a claim about any existing user system.

| Requirement | Design artifact | Acceptance gate |
|---|---|---|
| Search and streaming freshness | dataflow and freshness SLO | approved owner-defined threshold |
| Durable ingestion | ack semantics and RF/minISR | no unexplained acknowledged-event loss |
| Multi-AZ availability | broker/controller placement | N-1 model reviewed |
| Secure processing | mTLS/SASL/IAM, ACL and network policy | denied unauthorized access |
| Data governance | classification, retention, lineage, legal holds | privacy/security signoff |
| Recovery | RPO/RTO and runbooks | tested restore evidence |
| Operations | metrics, SLO, on-call, incident command | alert delivery demonstrated |
| Cost | 12-month capacity/FinOps model | budget owner approval |

All numeric SLOs, throughput, data size, RPO/RTO and budget are **inputs** from workload owners, not universal Kafka defaults.

## 3. Reference enterprise architecture

```text
                         business / privacy / security
                                      |
                        identity, schema, retention policy
                                      |
         producer / database CDC -> Kafka bootstrap (TLS/auth)
                                      |
                        Kafka brokers across AZ a/b/c
                      (topics, RF/minISR, partition leaders)
                                      |
                 KRaft controller quorum across failure domains
                                      |
          +---------------------------+------------------------+
          |                           |                        |
      consumer groups            Kafka Connect           Kafka Streams
          |                           |                        |
   operational read model       warehouse/search         derived topics
          |                           |                        |
        Redis cache             analytics index         DLQ / replay
          +---------------------------+------------------------+
                                      |
                       lineage + synthetic event ledger
                                      |
             Prometheus/Grafana + alerts + audit/SIEM
                                      |
            SRE on-call + GitOps/IaC + DR and change management
```

Use Kafka as a streaming log, not the authoritative transactional source for every domain. Define which system owns truth and how updates, replay and downstream materialization are reconciled.

## 4. Kafka/KRaft and failure-domain design

KRaft metadata controllers require a majority of configured voters; broker RF/minISR governs partition write availability separately. Design controllers and brokers across appropriate failure domains with rack awareness, controlled listener security, node pool separation and version-supported quorum configuration.

For example, RF=3 and minISR=2 can preserve acks=all writes after one **in-sync** replica loss when a leader and two ISR replicas remain. Actual AZ resilience depends on per-partition replica placement and surviving capacity. Never infer N-1 resilience from RF alone.

## 5. EKS/Strimzi platform blueprint

Define Strimzi operator ownership, Kafka and KafkaNodePool resources, namespace boundaries, RBAC, dedicated node pools, topology spread/anti-affinity, requests/limits, EBS storage class, PV/PVC lifecycle, PDBs, network policies and observability.

A PDB is not a guarantee against node/AZ outages. EBS PVs are AZ-bound; recovery must respect volume topology and broker identity. Use supported Strimzi/Kafka version combinations and staging validation.

## 6. Capacity and performance engineering

Size by peak ingress/egress, event size, replication traffic, retention, compaction, partition count, consumer concurrency, network, disk IOPS/throughput, heap/page cache and failure reserve.

A simplified **logical payload storage** estimate before compression and overhead:

`daily_ingest_bytes = peak_or_planned_events_per_second × average_event_bytes × 86400`

`replicated_retained_bytes ≈ daily_ingest_bytes × retention_days × replication_factor`

Add headroom for uneven partition distribution, segment overhead, reassignments, compaction, recovery, growth and EBS utilization limits. Treat these as planning estimates, not disk forecasts without measured compression and real workload distribution.

## 7. Security and governance blueprint

Review listener encryption, authentication (mTLS/SASL and MSK IAM where supported), Kafka ACLs, K8s RBAC, AWS IAM/KMS, private subnets, VPC rules, network policies, ExternalSecrets/secret lifecycle and certificate rotation.

Map data owners, topic classification, schema compatibility, retention, DLQ, mirrors, Connect sinks, backups, access audit and legal hold. Kafka tombstones/compaction are **not guaranteed secure erasure**; track copies through all sinks and backups.

## 8. Producer, consumer, Connect and CDC correctness

Set producer acks, idempotence, retry and timeout policy; distinguish acknowledged from ambiguous/unacknowledged writes. Define partition keys, group scaling, offset commits, rebalance safety, DLQ policy and downstream idempotency.

Connect/CDC continuity depends on connector semantics and source log retention. End-to-end exactly-once business effects cannot be assumed solely from Kafka producer transactions. Use unique synthetic event IDs and independently reconcile sink materialization.

## 9. Observability and SRE operations

Critical signals: under-minISR/under-replicated partitions, offline partitions, KRaft controller quorum, request P99/errors, broker CPU/disk/IOPS/network, producer retry/ack rates, consumer lag/freshness, Connect task status, CDC source lag, TLS expiry, auth/ACL denials and downstream reconciliation.

Define owner-specific SLOs, error budgets, alert thresholds, on-call escalation, dashboards, incident timeline, capacity review, change freeze criteria and runbooks.

## 10. HA, backup and DR

Define RPO/RTO, restore responsibilities and evidence for Kafka metadata/config, topic data, consumer offsets, schema contracts, Connect offsets, credentials, sink state and source CDC position. MirrorMaker or cross-region replication may be asynchronous and does not alone guarantee zero data loss or automatic client cutover.

Document KRaft quorum restoration, EKS/AZ topology, storage restore, cross-region network/IAM and post-restore event reconciliation. Include legal holds, retention and data residency.

## 11. CI/CD, GitOps and change management

Use Terraform/IaC for EKS/network/MSK boundaries where appropriate; GitOps for Strimzi CRs, Kafka topics/users and platform config. Gate on schema compatibility, RBAC/ACL scope, secret scans, policy checks, version compatibility, resource quotas, topology safety and rollback.

Avoid uncontrolled concurrent reconciliation or unreviewed broker config changes. Staging rollout and evidence are required before production promotion.

## 12. Read-only platform inventory

```bash
kubectl config current-context
kubectl get nodes -L topology.kubernetes.io/zone
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get pvc -A
kubectl get networkpolicy,pdb -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Commands depend on installed Strimzi CRDs. Sanitize metadata before sharing; do not retrieve secret values or regulated payloads.

## 13. Twenty architecture and production-readiness labs

### Lab 01 — Define business and technical charter

**Procedure:** Document synthetic healthcare-like events, scope, owners, SLO, RPO/RTO and privacy boundary.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 02 — Create platform context and cluster inventory

**Procedure:** Capture EKS/Kubernetes, Strimzi/KRaft, Kafka, MSK and managed dependencies.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 03 — Map end-to-end data architecture

**Procedure:** Diagram producers, Kafka, Connect/CDC, consumers, DLQ, Redis/search/warehouse sinks.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 04 — Create workload demand profile

**Procedure:** Specify events/sec, size distribution, retention, burst, consumer groups and growth.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 05 — Select broker/controller topology

**Procedure:** Review KRaft controller quorum, broker AZ/rack placement, RF/minISR and failure domain.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 06 — Size Kafka capacity

**Procedure:** Estimate partition count, storage replication, disk reserve, network and CPU.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 07 — Design Kubernetes isolation

**Procedure:** Review namespaces, node pools, affinity, topology spread, PDBs and storage class.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 08 — Design private connectivity

**Procedure:** Review bootstrap/advertised listeners, TLS, DNS, VPC and network policies.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 09 — Design identities and access

**Procedure:** Map service accounts, Kafka principals, ACLs, secrets, rotation and MSK IAM.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 10 — Define data contracts and governance

**Procedure:** Classify synthetic fields, schema, retention, DLQ, ownership and lineage.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 11 — Define producer delivery semantics

**Procedure:** Set acks/idempotence/retry/timeout assumptions and acknowledged event ledger.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 12 — Define consumer correctness

**Procedure:** Set partition keys, group scaling, offset commit, dedupe and freshness.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 13 — Define Connect and CDC resilience

**Procedure:** Plan source log retention, task HA, schema change, sink idempotency and replay.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 14 — Define observability and alerting

**Procedure:** Select Kafka ISR/quorum, request P99, consumer lag, Connect state, EBS and SLO metrics.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 15 — Define operational SLO and error budgets

**Procedure:** Set measurement windows, burn rates, paging and incident escalation.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 16 — Define backup and disaster recovery

**Procedure:** Set metadata/config backups, topic data strategy, MirrorMaker/MSK boundaries and DR drills.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 17 — Define upgrade and change management

**Procedure:** Specify compatibility, staging gates, Strimzi/Kafka upgrades, rollback and GitOps.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 18 — Define capacity and FinOps controls

**Procedure:** Model cost, storage retention, cross-AZ traffic, MSK versus Strimzi and forecast.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 19 — Define incident and chaos readiness

**Procedure:** Review runbooks, quorum/ISR safety, approved fault plans and client correctness.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

### Lab 20 — Complete architecture acceptance review

**Procedure:** Score critical gates, risks, evidence owners and independent signoff.

**Required evidence:** UTC time, platform/version and environment, requirement owner, assumption and threat/risk, architecture diagram or sanitized configuration, expected/observed control, SLO/RPO/RTO, approval, remediation, **Design/Tabletop** vs **Live Verified**, and independent reviewer. **Status: Pending** until completed and reviewed.

## 14. Offline readiness scorecard validator

Save as `validate_ch096_readiness.py`. It checks a reviewed JSON scorecard; it cannot prove a real cluster is production-ready.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("scorecard", help="Reviewed enterprise architecture scorecard JSON")
args = p.parse_args()
with open(args.scorecard, encoding="utf-8") as f:
    d = json.load(f)
weights = {
    "requirements_and_ownership": 15,
    "kraft_replication_topology": 20,
    "security_privacy_governance": 20,
    "streaming_correctness": 15,
    "observability_slo": 10,
    "ha_dr_capacity_finops": 10,
    "independent_review": 10,
}
required = ["scores", "critical_gates", "live_evidence_verified",
            "independent_sre_review", "independent_security_review",
            "independent_privacy_review", "evidence_ref"]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
scores = d["scores"]
if not isinstance(scores, dict) or set(scores) != set(weights):
    p.error("scores must exactly match weighted domains")
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
    and d["independent_sre_review"] is True
    and d["independent_security_review"] is True
    and d["independent_privacy_review"] is True
    and bool(d["evidence_ref"])
)
print(json.dumps({"score": total, "maximum": 100, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitation:** Passing proves only internal scorecard consistency, not architecture safety, actual HA, successful recovery or compliance. Independent review of source evidence remains mandatory.

## 15. Twelve enterprise architecture failure scenarios

### Scenario 01 — SLO and business ownership undefined

**Diagnosis:** Block readiness; obtain workload owners, freshness and recovery objectives. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 02 — KRaft controller quorum shares failure domain

**Diagnosis:** Redesign voter placement and validate N-1 majority. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 03 — RF/minISR cannot survive single AZ loss

**Diagnosis:** Revisit partition replica assignment, broker capacity and AZ topology. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 04 — Partition count or throughput under-sized

**Diagnosis:** Forecast producer/consumer load, broker/network/disk and growth reserve. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 05 — Storage retention cost exceeds budget

**Diagnosis:** Revisit approved retention, tiering, compliance and storage capacity. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 06 — Kafka ACL wildcard permits unauthorized read

**Diagnosis:** Reject access design and validate principal/topic/group scope. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 07 — Secret rotation causes client outage

**Diagnosis:** Require staged trust overlap, recovery and independent change approval. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 08 — CDC source log expires during Kafka outage

**Diagnosis:** Define monitoring, retention headroom and resnapshot recovery. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 09 — Sink exactly-once assumption unsupported

**Diagnosis:** Define end-to-end synthetic ledger and idempotent downstream effects. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 10 — Observability lacks KRaft or under-minISR alerts

**Diagnosis:** Block production readiness until critical detection works. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 11 — DR plan omits downstream state and legal holds

**Diagnosis:** Map data copies, recovery boundaries, lineage and privacy signoff. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

### Scenario 12 — Architecture approved without live evidence

**Diagnosis:** Mark design accepted only; keep runtime/production gates pending. Review platform ownership, RF/minISR, KRaft majority, AZ/EBS topology, Kafka auth/ACL, producer/consumer semantics, Connect/CDC, SLO and RPO/RTO. **Response:** Block production promotion, assign remediation owner, preserve sanitized evidence and review with SRE/security/privacy. **Exit:** Documented correction, updated architecture and independent signoff.

## 16. Eight production-readiness runbooks

### Runbook A — Architecture readiness review

**Trigger/actions:** Confirm scope, assumptions, ownership, NFRs, diagrams and risks. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook B — Kafka quorum and replica safety

**Trigger/actions:** Review KRaft voters, RF/minISR, placement and capacity. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook C — Networking and identity acceptance

**Trigger/actions:** Validate private connectivity, TLS, ACLs, IAM and secret lifecycle. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook D — Streaming data correctness

**Trigger/actions:** Reconcile synthetic producer acknowledgements, consumers, Connect and sinks. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook E — Performance and capacity readiness

**Trigger/actions:** Review baseline, forecasts, storage, AZ headroom and FinOps. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook F — Observability and incident response

**Trigger/actions:** Validate alerts, on-call, SLO/error budget and rollback. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook G — DR and upgrade readiness

**Trigger/actions:** Review restore evidence, RPO/RTO, change compatibility and staging. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

### Runbook H — Final architecture signoff

**Trigger/actions:** Score readiness, exceptions, evidence gaps and independent reviewers. **No-go:** unknown owner, unsupported version, controller majority risk, unverified RF/minISR, exposed PHI/secrets, no SLO/DR evidence, unapproved change or missing independent review. **Exit:** Reviewed design, accepted risk register, named owners and stage-gated production plan.

## 17. Evidence package

```text
evidence-ch096/
  01-business-charter.md
  02-platform-inventory.md
  03-data-architecture.md
  04-workload-profile.md
  05-broker-controller-topology.md
  06-capacity-sizing.md
  07-kubernetes-isolation.md
  08-private-connectivity.md
  09-identity-acl.md
  10-data-governance.md
  11-producer-semantics.md
  12-consumer-correctness.md
  13-connect-cdc.md
  14-observability.md
  15-slo-error-budget.md
  16-backup-dr.md
  17-upgrade-gitops.md
  18-finops-forecast.md
  19-chaos-incident-readiness.md
  20-independent-architecture-review.md
  risk-register.md
  architecture-scorecard.json
```

Each artifact includes UTC time, exact environment/version, **Design/Tabletop** vs **Live Verified**, requirements and owner, expected/observed, critical gates, evidence links, exceptions, remediation and independent reviewer.

## 18. 100-point enterprise architecture acceptance

| Domain | Points | Critical |
|---|---:|---|
| Requirements, ownership and workload profile | 15 | Yes |
| KRaft, replication, topology and platform safety | 20 | Yes |
| Security, privacy and governance | 20 | Yes |
| Streaming correctness and data contracts | 15 | Yes |
| Observability, SLO and incident readiness | 10 | Yes |
| HA/DR, capacity and FinOps | 10 | Yes |
| Independent SRE/security/privacy review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced and independent review. **Automatic Fail:** unauthorized access, unsafe controller quorum, under-minISR baseline, unknown regulated-data lineage, unexplained acknowledged event loss, missing DR plan or fabricated live results.

**Current status:** **Pending**. This is a published reference architecture, not a live-tested or production-approved Kafka platform.

## 19. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 097 — Kafka Enterprise Platform Build, GitOps Deployment and End-to-End Streaming Implementation.

---

**Verification boundary:** Publication confirms document availability only. Live platform deployment, client/sink correctness, performance, DR and independent technical/security review remain Pending.
