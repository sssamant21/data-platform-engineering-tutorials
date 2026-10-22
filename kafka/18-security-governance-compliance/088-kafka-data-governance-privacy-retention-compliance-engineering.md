# Chapter 088 — Kafka Data Governance, Privacy, Retention and Compliance Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 18 — Security, Governance and Compliance (3/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS, with Amazon MSK and Snowflake/CDC integration examples  
**Prerequisites:** Chapters 001–087; Kafka topics, retention/compaction, Kafka Connect, Schema Registry, ACLs and privacy controls  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** This chapter is an engineering control framework, not legal advice or HIPAA certification. Never upload or publish PHI/PII, patient identifiers, credentials, sensitive schemas or real event payloads. Retention, compaction and tombstones are not a guaranteed individual-record erasure mechanism; Kafka logs, replicas, tiered storage, backups, mirrors, consumers and sinks require separate evaluation. Destructive changes require data-owner, privacy/legal and change approval.

## 1. Mission and outcomes

Design end-to-end Kafka data governance for sensitive enterprise and healthcare streaming workloads. Establish **data ownership, classification, schema contracts, lineage, purpose-limited access, retention, deletion workflows, encryption, audit, data residency and compliance evidence**.

Readers will build a topic governance register, map CDC→Kafka→consumer/sink lineage, assess retention versus legal hold and replay, evaluate privacy risks of logs/DLQs and produce an independent acceptance scorecard.

## 2. Healthcare streaming data flow and trust boundaries

```text
Source of truth: PostgreSQL / MongoDB / operational systems
                        |
              CDC / Kafka Connect
                        |
       Kafka topic + schema + ownership
       /        |          |          \
    ACLs     retention   compaction   replicas
       \        |          |          /
        Kafka broker PVC / KRaft metadata
                        |
          consumers, DLQ, MirrorMaker
               |                  |
       Snowflake/analytics     search/cache
               |                  |
         downstream copies, backups
                        |
        lineage + privacy/legal workflow
                        |
       deletion/hold audit and signoff
```

Kafka may transport sensitive data but is rarely the sole system of record. A privacy request or incident must account for **every materialized downstream copy**, not just a Kafka topic.

## 3. Topic governance register

| Field | Required information |
|---|---|
| Topic and environment | unique name, cluster, owner |
| Data classification | public/internal/confidential/regulated |
| Sensitive fields | classified field names; no sample PHI |
| Source and sinks | CDC source, consumers, warehouses, DLQs |
| Schema | registry subject/version, compatibility policy |
| Retention | retention.ms, retention.bytes, cleanup.policy |
| Legal/privacy | retention basis, hold, deletion request process |
| Identity | allowed producer/consumer principals and purpose |
| Residency | region, AZ, mirror/backup locations |
| Evidence | reviewer, approval date, exceptions and expiry |

Unknown owners, missing lineage or ambiguous retention basis are **governance failures** requiring remediation before destructive changes.

## 4. Schema and field-level classification

Use schema contracts to document field sensitivity, allowed consumers, compatibility and validation. Schema Registry compatibility checks alone do not enforce data minimization or prevent PHI in optional fields.

Apply upstream tokenization/pseudonymization when appropriate and approved. Avoid treating pseudonymized identifiers as automatically anonymous. Validate re-identification risk and downstream joinability.

## 5. Retention and compaction semantics

Kafka `retention.ms` and `retention.bytes` apply to log retention according to segment lifecycle and configuration. Deletion is generally segment-based; lowering a setting does **not** instantly erase every record. `cleanup.policy=compact` retains the latest value per key subject to cleaner behavior; tombstones are not universal secure erasure.

**Key caveats:** active segments, replicas, snapshots, tiered/remote storage, MirrorMaker, Connect sinks, consumer local state and backups may retain copies. Consumer replay windows and incident recovery depend on approved retention.

## 6. Deletion requests, legal holds and audit

A deletion request should be routed through the organization's privacy/legal process. Determine identity, lawful basis, scope, holds and each downstream copy; plan authorized source/sink deletion or retention according to policy. Kafka's append-only design can make per-record erasure difficult without architectural changes.

Never promise complete erasure from Kafka merely because a tombstone was produced. Preserve evidence of the approved decision, technical actions, verification and exceptions without recording sensitive subject data in public repositories.

## 7. Lineage across CDC, Connect, Snowflake and consumers

Track topic producers, Kafka Connect source/sink connectors, dead-letter queues, MirrorMaker, consumer groups, transformations, warehouses, caches and backups. Include schema evolution, DLQ routing and historical data replays.

**Healthcare example:** an EMPI-related event may be produced from a clinical system, enriched and delivered to analytics/search; all consumers and copies must be classified and authorized. Use synthetic identifiers only in labs.

## 8. Encryption, authorization and regional residency

Use TLS for clients/inter-broker/controller where supported; encrypt EBS/PVC, object stores and backups with governed keys. Apply Kafka ACLs and Kubernetes/cloud IAM separately. Restrict cross-region replication according to data residency and contractual constraints.

Cross-AZ replication for resilience differs from cross-region movement for residency; do not weaken RF/minISR to avoid transfer charges.

## 9. Privacy-aware observability

Metrics, traces, logs, headers and DLQs can leak identifiers even when Kafka payloads are encrypted. Use redaction, sampling, controlled label cardinality, access restrictions, encryption and bounded retention. Prefer opaque correlation IDs that are not patient identifiers.

Audit administrative/config/ACL changes, secret rotation, connector changes and data access where supported. Kafka does not provide comprehensive per-record read audit by default; document detection limitations.

## 10. AWS MSK and Kubernetes control mapping

For Strimzi/EKS, review KafkaUser ACLs, operator RBAC, NetworkPolicies, PVC/KMS, Secret delivery, GitOps and cluster audit. For MSK, review supported IAM/SASL/TLS, KMS, VPC/network, broker logs and cloud audit.

Map each control to a specific owner and evidence source. Compliance frameworks require organization-specific risk assessment; technical settings alone are insufficient.

## 11. Read-only Kubernetes inventory

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool,kafkauser -A
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl get pvc -A
kubectl get networkpolicy -A
kubectl get secrets -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.type
```

Use authenticated Kafka topic configuration inventory in a restricted environment; sanitize topic names and principal identifiers if they are sensitive. Never export Secret values or patient payloads.

## 12. Twenty Kubernetes-first governance labs

### Lab 01 — Create Kafka data inventory

**Procedure:** Map topics, business owners, data stewards, schema versions and retention class.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 02 — Classify sensitive fields

**Procedure:** Identify synthetic examples of PHI/PII, financial and operational metadata without real records.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 03 — Map end-to-end lineage

**Procedure:** Trace CDC source, Kafka topic, Connect sink, Snowflake/search/analytics and downstream copies.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 04 — Review schema contracts

**Procedure:** Audit schema compatibility, field sensitivity labels and backward/forward evolution.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 05 — Review topic naming and ownership

**Procedure:** Assess naming standards, environment segregation, ownership and exception process.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 06 — Inventory retention configurations

**Procedure:** Capture retention.ms, retention.bytes, cleanup.policy and tiered storage settings.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 07 — Model retention expiration

**Procedure:** Tabletop segment lifecycle, replica logs, compaction and downstream replay impact.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 08 — Review compaction and tombstones

**Procedure:** Assess delete markers, min/max compaction lag and cleaner capacity.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 09 — Design deletion request workflow

**Procedure:** Map data subject request to source, Kafka, backups, sinks and audit without executing.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 10 — Review legal hold conflicts

**Procedure:** Document preservation orders, retention suspension and authorized governance decisions.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 11 — Review encryption and KMS

**Procedure:** Audit TLS, EBS/PVC, object storage, backup keys and rotation owners.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 12 — Review topic/consumer ACLs

**Procedure:** Check purpose limitation, least privilege, service identity and access recertification.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 13 — Assess Kafka Connect governance

**Procedure:** Inventory connectors, SMTs, DLQs, sink permissions and sensitive payload handling.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 14 — Review observability privacy

**Procedure:** Inspect log/trace/metric labels for identifiers and retention/redaction policies.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 15 — Review backup and DR retention

**Procedure:** Compare snapshots, MirrorMaker, tiered storage and restored-copy deletion behavior.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 16 — Evaluate regional data residency

**Procedure:** Map AZ/region, MSK/EKS networking, cross-region mirroring and contractual restrictions.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 17 — Build data quality checks

**Procedure:** Design schema validation, null/format constraints, deduplication and quarantine.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 18 — Review audit evidence

**Procedure:** Map admin/config/ACL changes, access, deletion approvals and immutable evidence.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 19 — Tabletop privacy incident

**Procedure:** Simulate sensitive data leak via DLQ, logs or unauthorized consumer.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

### Lab 20 — Independent compliance acceptance

**Procedure:** Validate owners, control mapping, exception register, privacy review and signoff.

**Expected evidence:** UTC time, Kafka/Strimzi/Kubernetes/MSK version, synthetic-only examples, topic owner/classification, lineage, retention and hold basis, ACL/data residency, observed versus expected controls, privacy/legal approval, **Live** versus **Tabletop**, risk/rollback and independent reviewer. **Status: Pending** until executed. Data deletion, retention changes and incident exercises are **Tabletop** unless separately approved.

## 13. Offline topic governance register validator

Save as `validate_topic_governance.py`. This validates a **sanitized JSON register**; it does not prove compliance or perform Kafka deletion.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("register", help="Sanitized topic governance register JSON")
args = p.parse_args()
with open(args.register, encoding="utf-8") as f:
    rows = json.load(f)
if not isinstance(rows, list) or not rows:
    p.error("expected nonempty list")
required = {
    "topic", "owner", "classification", "source", "consumers",
    "retention_policy", "deletion_workflow", "region",
    "privacy_review", "evidence_ref"
}
findings = []
for i, row in enumerate(rows, 1):
    if not isinstance(row, dict):
        findings.append(f"row {i}: not an object")
        continue
    missing = required - set(row)
    if missing:
        findings.append(f"row {i}: missing {sorted(missing)}")
        continue
    if any(not str(row[k]).strip() for k in
           ("topic", "owner", "classification", "source", "retention_policy",
            "deletion_workflow", "region", "evidence_ref")):
        findings.append(f"row {i}: blank governance field")
    if not isinstance(row["consumers"], list):
        findings.append(f"row {i}: consumers must be a list")
    if row["privacy_review"] is not True:
        findings.append(f"row {i}: privacy review pending")
print(json.dumps({"topics": len(rows), "findings": findings, "pass": not findings}, indent=2))
raise SystemExit(0 if not findings else 1)
```

**Limitations:** The script trusts the register and cannot discover undocumented consumers, replicas, backups, legal holds or false approvals. Independent source-of-truth and privacy review are required.

## 14. Twelve governance and privacy failure scenarios

### Scenario 01 — Retention too short for replay

**Diagnosis:** Escalate owner, stop change and assess recoverability before expiration. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 02 — Compacted topic retains deleted value

**Diagnosis:** Investigate tombstones, cleaner lag, old replicas, backups and sinks. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 03 — Deletion request ignores downstream copies

**Diagnosis:** Use lineage inventory and verify all authorized systems. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 04 — Legal hold conflicts with deletion

**Diagnosis:** Escalate to legal/privacy for documented decision; do not self-adjudicate. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 05 — PHI leaks into Kafka log or trace

**Diagnosis:** Contain, redact, preserve forensic evidence and notify privacy response. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 06 — Schema change exposes new identifier

**Diagnosis:** Require classification and contract review before promotion. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 07 — DLQ contains sensitive payload

**Diagnosis:** Restrict ACLs, encrypt, minimize payload and define retention. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 08 — Cross-region mirroring violates residency

**Diagnosis:** Pause unsafe replication and obtain compliance review. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 09 — Backup retains data past intended window

**Diagnosis:** Review retention and deletion policy for recoverable copies. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 10 — Topic has no accountable owner

**Diagnosis:** Mark governance gate failed and block destructive changes. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 11 — Kafka ACL permits unrelated analytics consumer

**Diagnosis:** Audit principal access and enforce purpose-limited grants. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

### Scenario 12 — Compliance dashboard reports false pass

**Diagnosis:** Trace controls to raw evidence, mark pending and remediate. Trace source/topic/consumer/sink lineage, retention and legal hold, Kafka ACLs, logs/DLQ, backups, residency and audit evidence. **Response:** Contain, stop unauthorized processing or destructive change, preserve forensics, notify owners/privacy and document decision. **Exit:** Classified and authorized data flows, verified downstream disposition, incident RCA and independent review.

## 15. Eight production governance runbooks

### Runbook A — Topic onboarding and classification

**Trigger/actions:** Assign owner, schema, retention, ACLs, lineage and privacy controls. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook B — Retention policy change

**Trigger/actions:** Verify replay, consumer lag, legal hold, backups, approvals and forward-fix. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook C — Data subject deletion request

**Trigger/actions:** Route through privacy/legal and system owners; track all copies and evidence. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook D — Compaction/tombstone investigation

**Trigger/actions:** Inspect cleaner metrics, segment lifecycle, backups and sink materialization. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook E — Sensitive payload incident

**Trigger/actions:** Contain exposure, rotate access if needed, preserve evidence and notify privacy. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook F — Schema governance violation

**Trigger/actions:** Quarantine incompatible event, review contracts and repair downstream consumers. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook G — Cross-region data residency breach

**Trigger/actions:** Stop unauthorized flow safely, assess copies and restore approved topology. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

### Runbook H — Quarterly compliance recertification

**Trigger/actions:** Review topics, owners, ACLs, retention, lineage, audit and exceptions. **No-go:** unknown topic owner, unauthorized data deletion, unreviewed legal hold, sensitive payload in evidence, unexplained downstream copy or missing privacy signoff. **Exit:** Audited policy, validated data lineage, stable Kafka SLO and independent compliance review.

## 16. Evidence package

```text
evidence-ch088/
  topic-governance-register.json
  field-classification.md
  source-to-sink-lineage.md
  schema-contracts.md
  naming-ownership.md
  retention-inventory.csv
  retention-expiration-tabletop.md
  compaction-tombstones.md
  deletion-request-workflow.md
  legal-hold-review.md
  encryption-kms.md
  topic-consumer-acls.md
  kafka-connect-governance.md
  observability-privacy.md
  backup-dr-retention.md
  regional-residency.md
  data-quality.md
  audit-evidence.md
  privacy-incident-tabletop.md
  independent-compliance-acceptance.md
  scorecard.md
```

Each artifact includes UTC time, source/version, **Live** versus **Tabletop**, expected/observed result, owner, privacy/legal decision, risk/rollback and independent reviewer. Never store subject identifiers or PHI.

## 17. 100-point governance acceptance

| Domain | Points | Critical |
|---|---:|---|
| Ownership, classification and lineage | 25 | Yes |
| Retention, compaction, deletion and legal holds | 25 | Yes |
| Identity, encryption and residency | 15 | Yes |
| Schema, DLQ, logs and data quality | 15 | Yes |
| Audit, incident response and governance evidence | 10 | Yes |
| Independent privacy/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced. **Automatic Fail:** exposed PHI, unapproved deletion, missing legal hold review, undocumented sensitive consumer, fabricated evidence or absent independent privacy/security review.

**Current status:** **Pending**. No live privacy assessment, erasure guarantee or compliance certification is claimed.

## 18. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html).

**Next:** Chapter 089 — Kafka Security Observability, Threat Detection and Incident Response Automation.

---

**Verification boundary:** Publication confirms document availability only. Live lineage verification, deletion workflows, compliance controls and independent privacy/security review remain Pending.
