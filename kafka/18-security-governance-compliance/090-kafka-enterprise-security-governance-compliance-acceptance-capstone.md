# Chapter 090 — Kafka Enterprise Security, Governance and Compliance Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 18 — Security, Governance and Compliance (5/5; final capstone)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS, with Amazon MSK controls  
**Prerequisites:** Chapters 001–089, especially 086–089  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security/privacy review:** Pending

> **Safety:** This capstone defines an acceptance process; it does not certify an existing cluster, satisfy HIPAA by itself or authorize production changes. Use synthetic non-PHI events and redacted metadata. No credential/ACL/NetworkPolicy mutation, secret rotation, retention change, broker isolation, penetration testing or automated revocation in production without explicit approval and Kafka quorum/ISR, client SLO, privacy and recovery safeguards.

## 1. Mission and exit criteria

Unify **zero-trust Kafka architecture (086), identity/secret lifecycle (087), privacy/retention governance (088) and threat detection/incident automation (089)** into a measurable enterprise security acceptance decision.

An accepted environment must demonstrate authenticated and encrypted Kafka listeners, least-privilege topic/group ACLs, isolated KRaft controllers, safe Strimzi/Kubernetes permissions, approved secret and certificate lifecycle, complete sensitive-data ownership/lineage, retention/legal-hold controls, privacy-safe audit, tested detection and independently reviewed incident procedures.

**Publication ≠ execution ≠ security certification.** All evidence must be explicitly marked **Live**, **Tabletop**, **Pending** or **Not Applicable** with rationale.

## 2. End-to-end trust and governance architecture

```text
Business data owner + security/privacy/legal policy
                        |
  approved identity, topic schema and classification
                        |
  app producer / CDC / Kafka Connect / consumer
                        |
         mTLS / SCRAM / OAuth / MSK IAM*
                        |
   network segmentation + broker Kafka ACLs
                        |
      Kafka topics, ISR, encrypted PVC/EBS
          |                      |
       KRaft quorum         replicas/retention
          |                      |
   Strimzi operator       DLQ / mirrors / sinks
          |                      |
  scoped K8s RBAC          data lineage / legal hold
          +-------------+--------+
                        |
       audit + SIEM + alert + on-call
                        |
       human-approved incident response
                        |
  evidence, risk exceptions and independent review

*Availability depends on Kafka/MSK distribution and version.
```

Kafka ACLs, Kubernetes RBAC, AWS IAM and privacy governance solve different authorization problems and must be assessed separately.

## 3. Critical acceptance control matrix

| Control | Required evidence | Automatic no-go |
|---|---|---|
| Listener authentication | TLS/SASL/mTLS/IAM config and isolated tests | anonymous external access |
| Kafka authorization | effective principal/topic/group grants and denial tests | unapproved wildcard |
| KRaft controller | secured listener, quorum and network isolation | exposed controller |
| Strimzi/K8s permissions | operator RBAC, service accounts and GitOps | excessive privilege |
| Network segmentation | CNI-enforced policies and VPC review | uncontrolled access |
| Certificate lifecycle | CA/SAN/expiry, rotation and rollback | bypassed TLS verification |
| Secrets/KMS | encrypted distribution, rotation, audit | leaked secret |
| Data classification | owner, fields, schema and purpose | unknown regulated data |
| Retention/deletion | owner/legal approval, replay, downstream copies | unapproved deletion |
| Residency | region/mirror/consumer mapping | unauthorized transfer |
| Security telemetry | broker/KRaft/operator/cloud audit and gaps | blind critical path |
| Threat response | tested alerts, human approval and recovery | destructive unapproved automation |
| Independent review | signed SRE/security/privacy acceptance | missing signoff |

## 4. Identity and certificate assurance

Inventory Kafka principals, KafkaUser desired state, broker listeners, controller identities, ACLs, super.users and admin break-glass. Verify per-workload topic/group scope and rotation ownership.

For mTLS and SCRAM, document issuance, renewal, staged trust overlap, revocation and client recovery. For MSK IAM, check supported cluster auth mode and policy scope; do not assume IAM and Kafka ACL behavior are identical across modes.

## 5. KRaft, Strimzi and Kubernetes boundaries

Protect controller quorum and authenticated inter-broker/controller listeners. Review operator reconciliation rights, CRD permissions, namespace boundaries, NetworkPolicies, VPC rules, image provenance and GitOps drift.

Do not test denial by disconnecting production brokers or controllers. NetworkPolicy changes can sever replication and monitoring; use disposable environments and rollback gates.

## 6. Data privacy, retention and legal obligations

Maintain a topic governance register: owner, classification, schema, producer, consumer, Connect source/sink, DLQ, mirrors, backups, retention, legal hold and residency. Use approved privacy/legal workflows for deletion requests and incident notification.

**Kafka compaction and tombstones are not guaranteed secure per-record erasure.** Copies may persist in segments, replicas, tiered storage, mirrors, backups, caches, consumer state and warehouses. Acceptance requires end-to-end lineage and authorized disposition, not an unverified deletion claim.

## 7. Security telemetry and detection validation

Map broker authentication/ACL signals, KafkaUser drift, KRaft quorum anomalies, Kubernetes audit, MSK CloudTrail/broker logs, secret sync failures, connector edits and network egress to SIEM correlation and on-call alerts.

Kafka does not inherently provide complete per-record read auditing. Explicitly document coverage gaps. Validate alert routing and detection quality with **synthetic labeled events** in an isolated environment.

## 8. Human-approved incident automation

Safe default automation: enrich ticket with sanitized principal/resource metadata, gather approved metrics, page owner and propose a reviewed runbook. ACL revocation, credential invalidation, network quarantine, broker restart and controller isolation require human authorization and Kafka availability impact review.

Protect healthcare data pipelines from overzealous containment by checking producer P99, consumer freshness, ISR/minISR, KRaft quorum and business recovery objectives.

## 9. Read-only Kubernetes/Strimzi preflight

```bash
kubectl config current-context
kubectl get kafka,kafkauser,kafkanodepool -A
kubectl get networkpolicy -A
kubectl get serviceaccount,role,rolebinding -A
kubectl get pvc -A
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl get secrets -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.type
```

Sanitize outputs; no Secret values, client passwords, tokens, PHI or real Kafka records. These commands demonstrate inventory access, not effective authorization or compliance.

## 10. Twenty enterprise security acceptance labs

### Lab 01 — Approve security capstone charter

**Procedure:** Set cluster boundary, data classification, security owner, evidence scope and independent reviewers.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 02 — Freeze asset and threat inventory

**Procedure:** Capture Kafka/KRaft/Strimzi/EKS/MSK versions, listeners, topics, clients and trust boundaries.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 03 — Validate authenticated listeners

**Procedure:** Review supported TLS/SASL/mTLS/IAM configurations and prohibit anonymous production access.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 04 — Validate Kafka ACL least privilege

**Procedure:** Reconcile KafkaUser/ACL grants to topic/group purpose and owners.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 05 — Validate KRaft control-plane isolation

**Procedure:** Review controller listener, authenticated communication, quorum placement and network exposure.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 06 — Validate Strimzi operator RBAC

**Procedure:** Review namespace permissions, service accounts, reconciliation and GitOps ownership.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 07 — Validate Kubernetes network segmentation

**Procedure:** Map broker, controller, operator, client, DNS and monitoring flows.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 08 — Validate TLS and CA lifecycle

**Procedure:** Inspect expiry, SAN, trust overlap, issuer controls and rotation runbook.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 09 — Validate secret distribution and revocation

**Procedure:** Review ExternalSecrets, KMS, encryption, RBAC, sync errors and compromise response.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 10 — Validate MSK IAM and VPC controls

**Procedure:** Review cluster authentication mode, policies, private endpoints and audit.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 11 — Validate topic classification and lineage

**Procedure:** Map source, Kafka topic, DLQ, Connect, sinks, mirrors, backups and data owner.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 12 — Validate schema and sensitive-field controls

**Procedure:** Review synthetic schemas, field classification, minimization and contract compatibility.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 13 — Validate retention and legal hold

**Procedure:** Review cleanup policy, compaction, replay, backups, deletion workflows and legal approval.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 14 — Validate cross-region residency

**Procedure:** Inspect MirrorMaker, Connect, MSK regions and unauthorized transfer risk.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 15 — Validate privacy-safe observability

**Procedure:** Review logs, traces, metrics and SIEM for secret/PHI leakage and access restrictions.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 16 — Validate threat detection coverage

**Procedure:** Review auth failures, ACL denials, KafkaUser drift, controller, IAM and egress alerts.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 17 — Validate alert routing and incident command

**Procedure:** Tabletop high-severity alerts, on-call escalation, privacy response and audit.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 18 — Validate guarded response automation

**Procedure:** Review human approvals, dry-run, blast radius, rollback and Kafka ISR/SLO safety.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 19 — Run integrated security incident tabletop

**Procedure:** Simulate credential compromise plus unauthorized consumer and retention/legal-hold conflict.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

### Lab 20 — Independent enterprise acceptance

**Procedure:** Score critical controls, record exceptions, signed evidence and follow-up owners.

**Required evidence:** UTC time, approved environment, Kafka/Strimzi/EKS/MSK versions, redacted control state, expected/observed result, principal/owner, Kafka ISR/KRaft health, data-classification and legal basis, alert routing, **Live** versus **Tabletop**, incident abort/rollback, risk exception and independent reviewer. **Status: Pending** until executed. Denial, rotation, network, deletion and response tests are **Tabletop** unless explicitly authorized in isolated infrastructure.

## 11. Offline capstone control validator

Save as `validate_ch090_security_capstone.py`. It checks an independently reviewed JSON scorecard, not live Kafka or legal compliance.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("scorecard", help="Sanitized reviewed security scorecard JSON")
args = p.parse_args()
with open(args.scorecard, encoding="utf-8") as f:
    d = json.load(f)
weights = {
    "zero_trust_identity": 25,
    "tls_secrets_kraft": 20,
    "privacy_retention_lineage": 20,
    "detection_response": 20,
    "operations_evidence": 5,
    "independent_review": 10,
}
required = ["scores", "critical_gates", "live_evidence_verified",
            "independent_security_review", "independent_privacy_review",
            "secrets_exposed", "unapproved_destructive_action", "evidence_ref"]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
scores = d["scores"]
if not isinstance(scores, dict) or set(scores) != set(weights):
    p.error("scores must exactly match weighted domains")
if any(type(scores[k]) not in (int, float) or not 0 <= scores[k] <= weights[k]
       for k in weights):
    p.error("scores out of bounds")
gates = d["critical_gates"]
if not isinstance(gates, dict) or not gates:
    p.error("critical_gates must be nonempty")
total = sum(scores.values())
passed = (
    total >= 85
    and all(v is True for v in gates.values())
    and d["live_evidence_verified"] is True
    and d["independent_security_review"] is True
    and d["independent_privacy_review"] is True
    and d["secrets_exposed"] is False
    and d["unapproved_destructive_action"] is False
    and bool(d["evidence_ref"])
)
print(json.dumps({"score": total, "maximum": 100, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitations:** The validator trusts submitted fields. An independent reviewer must verify source evidence, actual authorization denials, SIEM alert delivery, privacy decisions and documented exceptions. A successful script run alone is not certification.

## 12. Twelve integrated security failure scenarios

### Scenario 01 — Security pass despite anonymous listener

**Diagnosis:** Reject acceptance and remediate broker exposure with change approval. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 02 — Wildcard ACL exposes regulated topic

**Diagnosis:** Audit effective authorization, revoke safely and investigate access. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 03 — KRaft controller listener compromised

**Diagnosis:** Protect quorum and preserve logs while containing control-plane access. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 04 — Certificate rotation breaks consumers

**Diagnosis:** Stage trust overlap, recover clients and verify authentication safely. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 05 — Secret leak in Git or SIEM

**Diagnosis:** Revoke credentials, restrict evidence and initiate security/privacy response. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 06 — Strimzi RBAC permits cluster takeover

**Diagnosis:** Audit operator permissions and apply supported least-privilege remediation. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 07 — Deletion request ignores mirrored copy

**Diagnosis:** Trace all copies, privacy/legal holds and downstream deletion workflow. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 08 — Compaction assumed to guarantee erasure

**Diagnosis:** Reject claim; inspect segments, replicas, tiered storage and backups. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 09 — Cross-region consumer violates residency

**Diagnosis:** Contain unauthorized transfer and escalate to privacy/legal. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 10 — Detection rule silent during ACL attack

**Diagnosis:** Mark control failed, inspect source/collector/SIEM routing and retest. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 11 — Automated containment disrupts healthcare feed

**Diagnosis:** Require human approval, SLO impact, ISR safety and rollback. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

### Scenario 12 — Evidence appears complete but lacks reviewer

**Diagnosis:** Mark pending, require independent technical/privacy/security signoff. Correlate Kafka principal/ACL, TLS/SCRAM, Strimzi/Kubernetes RBAC, KRaft quorum/ISR, data lineage, retention/legal hold, SIEM, AWS audit and client SLO. **Response:** Contain with approved authority, protect Kafka durability, preserve sanitized forensic evidence and escalate to security/privacy. **Exit:** Verified least privilege, corrected governance, healthy Kafka, incident RCA and independent signoff.

## 13. Eight production security runbooks

### Runbook A — Enterprise security acceptance preflight

**Trigger/actions:** Validate inventory, authorization, sanitized data and reviewer assignment. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook B — Credential and certificate compromise

**Trigger/actions:** Revoke/rotate, preserve logs, assess affected topics and recover clients. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook C — Kafka ACL and KRaft security incident

**Trigger/actions:** Protect quorum/ISR, contain access and restore authorized operations. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook D — Strimzi/Kubernetes privilege escalation

**Trigger/actions:** Review operator RBAC, GitOps drift, service accounts and cluster audit. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook E — Sensitive data leakage and privacy response

**Trigger/actions:** Contain, identify copies, preserve forensics and coordinate legal/privacy. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook F — Retention/legal hold conflict

**Trigger/actions:** Pause destructive change, obtain authorized decision and verify replay/recovery. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook G — Security detection and SIEM outage

**Trigger/actions:** Restore telemetry, document blind spots and test alert routing. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

### Runbook H — Final security/compliance signoff

**Trigger/actions:** Reconcile all control evidence, exceptions, scores and remediation owners. **No-go:** exposed secrets, unknown data owner, unapproved destructive action, missing KRaft/ISR safety, undocumented downstream copies, SIEM blind spots or absent reviewer. **Exit:** Restored access controls, stable producer/consumer SLO, complete incident timeline, accepted exceptions and independent signoff.

## 14. Evidence package

```text
evidence-ch090/
  01-security-charter.md
  02-assets-threat-model.md
  03-authenticated-listeners.md
  04-acl-least-privilege.md
  05-kraft-controller-isolation.md
  06-strimzi-rbac.md
  07-network-segmentation.md
  08-tls-ca-lifecycle.md
  09-secret-revocation.md
  10-msk-iam-vpc.md
  11-topic-lineage.md
  12-schema-classification.md
  13-retention-legal-hold.md
  14-data-residency.md
  15-privacy-observability.md
  16-threat-detection.md
  17-incident-command.md
  18-guarded-automation.md
  19-integrated-tabletop.md
  20-independent-signoff.md
  scorecard.json
  risk-exceptions.md
```

Each artifact includes UTC time, source/version, sanitized evidence, **Live** vs **Tabletop**, expected/observed result, Kafka SLO/quorum impact, privacy/legal decision, owner, remediation deadline and independent reviewer.

## 15. 100-point enterprise security acceptance

| Domain | Points | Critical |
|---|---:|---|
| Zero-trust identities and least-privilege ACLs | 25 | Yes |
| TLS, secrets, KRaft and platform isolation | 20 | Yes |
| Data governance, privacy, retention and lineage | 20 | Yes |
| Threat detection and incident response | 20 | Yes |
| Operational evidence and runbooks | 5 | Yes |
| Independent technical/security/privacy review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates independently evidenced by approved live validation and reviewers. **Automatic Fail:** leaked credentials/PHI, unauthenticated exposed listener, unauthorized topic access, unapproved deletion, controller compromise, missing high-severity alert, fabricated evidence or absent independent review.

**Current status:** **Not Ready / Pending**. Publication alone does not constitute acceptance.

## 16. Part completion and next chapter

**Part 18 — Security, Governance and Compliance (086–090) is fully published.** Chapter 086 establishes zero-trust architecture; 087 identity lifecycle; 088 data governance; 089 detection/incident response; 090 enterprise acceptance.

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html).

**Next:** Chapter 091 — Kafka Chaos Engineering Foundations, Failure Injection Safety and Game Day Design, beginning Part 19 — Chaos Engineering and Resilience Validation.

---

**Verification boundary:** Publication confirms document availability only. Live security tests, alert delivery, incident exercises and independent technical/security/privacy review remain Pending.
