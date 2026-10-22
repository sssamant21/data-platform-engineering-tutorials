# Chapter 089 — Kafka Security Observability, Threat Detection and Incident Response Automation

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 18 — Security, Governance and Compliance (4/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS, with Amazon MSK security telemetry  
**Prerequisites:** Chapters 001–088; Kafka SASL/TLS, ACLs, KRaft, Strimzi, Prometheus, Kubernetes audit, AWS IAM and privacy controls  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use sanitized synthetic-only security events. Do not collect real patient payloads, secrets, bearer tokens, client passwords, private keys or full Kafka messages in SIEM evidence. Never automatically revoke production principals, alter ACLs, quarantine network traffic or restart KRaft controllers without human-approved incident command, dependency checks and rollback. Kafka does not guarantee per-record consumer-read audit by default.

## 1. Mission and outcomes

Build an enterprise **Kafka security detection and incident response program** spanning broker authentication, ACL authorization, KRaft controllers, Strimzi operators, Kubernetes RBAC and Secrets, Kafka Connect, AWS MSK IAM and VPC/network telemetry.

Readers will design a normalized event contract, correlate threat signals across layers, distinguish maintenance noise from attacks, create alert routing, measure detection coverage and engineer guarded automation with auditable approvals.

## 2. Detection architecture

```text
Kafka broker auth/ACL logs       KRaft controller events
          |                               |
Strimzi reconciliation        EKS audit / NetworkPolicy
          |                               |
AWS CloudTrail/MSK logs       VPC Flow Logs / Connect
          +-------------------------------+
                          |
             sanitized event normalization
                          |
              Prometheus + log pipeline
                          |
             SIEM correlation / detection
                          |
             alert severity + on-call owner
                          |
            human-approved response gate
                          |
      principal rotation / ACL remediation /
        egress containment / recovery
                          |
          evidence, privacy, RCA, retest
```

**Important:** Metrics, logs, audit trails and network flows each cover different behavior. No single telemetry stream proves which records a Kafka consumer read.

## 3. Threat model and observable signals

| Threat | Potential signal | Blind spot |
|---|---|---|
| Password guessing | repeated SASL failures | missing principal/source metadata |
| TLS spoofing | handshake/hostname failures | generic transport errors |
| Unauthorized topic access | ACL denials | not every client action logged |
| Excessive authorized reads | bytes-out, new groups, unusual client path | payload-level read attribution |
| Admin privilege escalation | ACL/config changes, GitOps and cloud audit | manual out-of-band changes |
| KRaft control-plane attack | controller listener errors, quorum instability | incomplete auth logging |
| Connect exfiltration | connector edits, sink egress and plugin change | encrypted destinations |
| Secret theft | Kubernetes API audit, cloud IAM access | Secret value access context |
| Certificate expiry | cert metadata, failed rotation | unmonitored truststores |
| SIEM tampering | collector gaps, missing logs and ingestion delay | logs removed before collection |

Use **correlation** rather than equating one authentication failure with an intrusion.

## 4. Kafka broker and client telemetry

Collect authentication failures, authorization denials where supported, broker listener changes, producer/consumer client errors, group rebalances, unusual bytes-out, connection churn and Kafka config/ACL changes. Restrict sensitive principal names and IP addresses in exported evidence; use stable pseudonyms when appropriate.

Kafka JMX metrics and exporter names vary by release and configuration. Review installed Kafka and Strimzi JMX mappings; do not invent guaranteed metric names.

## 5. KRaft, Strimzi and Kubernetes signals

Protect controller quorum and monitor listener authentication errors, leader changes, controller failover and metadata operations. Collect Strimzi operator events, KafkaUser reconciliation and GitOps diffs.

Kubernetes audit logs may record Secret API access and RBAC changes but can contain sensitive request metadata; apply approved policy and retention. NetworkPolicies require a supporting CNI, and dropped-packet observability is implementation-specific.

## 6. Amazon MSK and AWS security telemetry

Map CloudTrail IAM/MSK API activity, supported MSK broker logs and CloudWatch metrics, VPC Flow Logs, KMS events, role changes and EKS service-account identity. Verify logging options for the actual MSK cluster type/version and account configuration; managed service logs do not imply full Kafka record-access audit.

## 7. Normalized security event contract

```json
{
  "timestamp_utc": "2026-01-01T00:00:00Z",
  "environment": "isolated-lab",
  "source": "kafka-broker",
  "event_category": "authentication_failure",
  "principal_hash": "synthetic-hash",
  "resource_class": "listener",
  "severity": "medium",
  "correlation_id": "synthetic-event-001",
  "evidence_ref": "lab://synthetic/auth-001"
}
```

Do not include credentials, PHI, raw Kafka payloads, full tokens or unapproved personal identifiers. Use UTC source timestamps and preserve ingestion time to detect clock skew.

## 8. Detection engineering and SLO

Define rules for repeated auth failures, unexpected ACL grants, new admin principals, cert expiry, controller listener anomalies, new Kafka Connect sink destinations, unusual cross-region egress, log collection gaps and secret sync errors.

For each rule document **data source, query logic, false positives, severity, owner, runbook, suppression, test fixture and evidence**. Track MTTD, alert delivery, false-positive rate and coverage against synthetic labeled scenarios. A dashboard without tested alert routing is not an operational control.

## 9. Incident response automation boundaries

Automate **safe enrichment and notification first**: open a ticket, gather sanitized KafkaUser/ACL metadata, attach approved runbooks, route to on-call and flag potential scope. Identity revocation, ACL mutation, broker isolation and controller actions require explicit human approval and rollback/forward-fix planning.

An automated containment that disconnects a critical healthcare data pipeline may cause greater harm than the suspicious event; check application SLO, ISR/minISR and KRaft quorum before acting.

## 10. Read-only Kubernetes/EKS preflight

```bash
kubectl config current-context
kubectl get kafka,kafkauser,kafkanodepool -A
kubectl get networkpolicy -A
kubectl get serviceaccount,role,rolebinding -A
kubectl get pods -A -l strimzi.io/kind=Kafka
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Sanitize namespace, principal and event details before publication. Avoid `kubectl get secret -o yaml` and unrestricted log dumps. EKS control-plane logging, MSK broker logging and audit retention must be explicitly configured where supported.

## 11. Twenty Kubernetes-first detection labs

### Lab 01 — Define security telemetry contract

**Procedure:** Inventory Kafka broker, KRaft, Strimzi, EKS and MSK security event sources and gaps.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 02 — Map auth failure metrics

**Procedure:** Correlate SASL/TLS failures with source, principal and known maintenance windows.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 03 — Review ACL denial visibility

**Procedure:** Identify supported authorizer logs and avoid assuming comprehensive read auditing.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 04 — Monitor certificate expiry

**Procedure:** Build inventory of public cert metadata and alert on expiry and rotation failures.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 05 — Review KafkaUser drift

**Procedure:** Compare Strimzi KafkaUser desired state, ACLs, operator events and Git history.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 06 — Monitor KRaft security health

**Procedure:** Correlate controller quorum changes, listener auth failures and metadata errors.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 07 — Inspect Kubernetes audit coverage

**Procedure:** Verify approved API audit collection for RBAC, Secrets metadata and workload changes.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 08 — Inspect AWS CloudTrail/MSK signals

**Procedure:** Map IAM changes, MSK config updates, VPC changes and CloudWatch broker logs.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 09 — Review secret sync alerts

**Procedure:** Monitor External Secrets/Secrets Store sync errors without exporting secret values.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 10 — Review network egress anomalies

**Procedure:** Model client/broker AZ and VPC flow logs with authorized destinations.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 11 — Detect suspicious consumer access

**Procedure:** Correlate new principal, group membership, topic ACL changes and bytes-out spikes.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 12 — Detect Kafka Connect misuse

**Procedure:** Review connector create/update events, plugin provenance, DLQ and sink egress.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 13 — Build SIEM normalization

**Procedure:** Map timestamp, environment, source, principal hash, resource and event category.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 14 — Design alert deduplication

**Procedure:** Group bursts by principal/resource/time without hiding distinct high-severity attacks.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 15 — Exercise isolated detection test

**Procedure:** Inject only synthetic failed auth events in approved disposable Kafka environment.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 16 — Tabletop credential compromise

**Procedure:** Trace identity scope, containment, rotation, Kafka client recovery and audit.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 17 — Tabletop data exfiltration

**Procedure:** Use synthetic flow evidence to investigate unauthorized consumer and network egress.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 18 — Design guarded response automation

**Procedure:** Propose human-approved revoke/quarantine workflows with dry-run and rollback.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 19 — Measure detection quality

**Procedure:** Record precision, recall from labeled synthetic events, MTTD, false positives and gaps.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

### Lab 20 — Independent detection acceptance

**Procedure:** Review control coverage, alert routes, evidence retention and security signoff.

**Required evidence:** UTC time, approved isolated environment, Kafka/Strimzi/Kubernetes/MSK version, synthetic event fixture, expected versus observed detection, alert route, false positives, missing telemetry, owner, privacy review, **Live** versus **Tabletop**, abort/rollback and independent security reviewer. **Status: Pending** until executed. Credential/ACL/network containment remains **Tabletop** without separate approval.

## 12. Offline detection quality validator

Save as `validate_detection_evidence.py`. This evaluates labeled **synthetic** alert outcomes, not a live SIEM or Kafka cluster.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("fixtures", help="JSON list of synthetic detection results")
p.add_argument("--min-recall", type=float, default=0.90)
p.add_argument("--min-precision", type=float, default=0.80)
args = p.parse_args()
if not 0 <= args.min_recall <= 1 or not 0 <= args.min_precision <= 1:
    p.error("thresholds must be within 0..1")
with open(args.fixtures, encoding="utf-8") as f:
    rows = json.load(f)
if not isinstance(rows, list) or not rows:
    p.error("expected nonempty list")
if any(not isinstance(r, dict) or type(r.get("threat")) is not bool
       or type(r.get("alert")) is not bool or not r.get("evidence_ref")
       for r in rows):
    p.error("each row needs boolean threat/alert and evidence_ref")
tp = sum(r["threat"] and r["alert"] for r in rows)
fp = sum(not r["threat"] and r["alert"] for r in rows)
fn = sum(r["threat"] and not r["alert"] for r in rows)
tn = sum(not r["threat"] and not r["alert"] for r in rows)
precision = tp / (tp + fp) if tp + fp else 0.0
recall = tp / (tp + fn) if tp + fn else 0.0
passed = tp + fn > 0 and tp + fp > 0 and precision >= args.min_precision and recall >= args.min_recall
print(json.dumps({"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                  "precision": round(precision, 4), "recall": round(recall, 4),
                  "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitation:** The tool trusts labeled fixtures. Independent reviewers must validate SIEM queries, actual telemetry coverage, alert delivery, production safeguards and source evidence before certification.

## 13. Twelve security detection failure scenarios

### Scenario 01 — Authentication storm after rotation

**Diagnosis:** Separate expected reconnects from malicious guessing using rollout and client metadata. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 02 — ACL denial spike lacks principal context

**Diagnosis:** Review authorizer configuration and preserve minimal privacy-safe correlation. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 03 — Expired TLS cert is not alerted

**Diagnosis:** Check cert inventory, scrape failures, threshold and alert routing. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 04 — Compromised consumer downloads unusually fast

**Diagnosis:** Correlate ACL, group, bytes-out and VPC flow without claiming per-record audit. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 05 — KRaft listener attack impacts quorum

**Diagnosis:** Protect quorum, isolate listener, preserve logs and invoke incident command. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 06 — KafkaUser privileges drift from Git

**Diagnosis:** Compare operator reconciliation, manual ACL changes and GitOps events. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 07 — SIEM receives sensitive payloads

**Diagnosis:** Stop ingestion of sensitive fields, restrict access, redact and invoke privacy response. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 08 — Alert fatigue hides true compromise

**Diagnosis:** Review grouping, suppression, severity and escalation tests. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 09 — Automation revokes critical producer

**Diagnosis:** Require human approval, canary, dependency inventory and forward-fix. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 10 — MSK logging not enabled

**Diagnosis:** Document blind spots, configure approved sources and test ingestion. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 11 — Clock skew corrupts incident timeline

**Diagnosis:** Check NTP and preserve raw timestamps plus ingestion timestamps. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

### Scenario 12 — Connector exfiltration missed by network rule

**Diagnosis:** Map plugin, sink endpoint, service identity and allowed egress. Correlate broker/KRaft logs, Kafka ACL and KafkaUser desired state, EKS/CloudTrail audit, MSK metrics, network egress, Connect changes and client SLO. **Response:** Preserve sanitized evidence, contain only with approved authority, protect Kafka quorum/ISR and escalate privacy incidents. **Exit:** Root cause, verified detection, stable clients, documented scope and independent review.

## 14. Eight production incident runbooks

### Runbook A — Authentication attack triage

**Trigger/actions:** Identify scope, rate, sources, affected principals and authorized maintenance. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook B — Kafka ACL abuse containment

**Trigger/actions:** Freeze unsafe changes, review principal grants, preserve evidence and stage revoke. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook C — Certificate failure response

**Trigger/actions:** Validate trust chain and renewal, restore clients without bypassing TLS. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook D — KRaft control-plane security incident

**Trigger/actions:** Protect controller quorum and broker availability during containment. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook E — Sensitive data exfiltration investigation

**Trigger/actions:** Correlate consumer access, egress, Connect, logs and privacy/legal response. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook F — Strimzi operator or GitOps compromise

**Trigger/actions:** Audit RBAC, desired state, image provenance, reconciliation and drift. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook G — Detection pipeline outage

**Trigger/actions:** Check collectors, SIEM delivery, retention, alert routing and documented blind spots. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

### Runbook H — Post-incident evidence and recovery

**Trigger/actions:** Preserve timeline, remediation, data integrity, SLO, lessons and signoff. **No-go:** automated production credential revoke without approval, unsafe broker isolation, missing forensic preservation, PHI in evidence or unknown KRaft/ISR impact. **Exit:** Verified containment, Kafka/client SLO recovery, immutable incident timeline, control improvement and security signoff.

## 15. Evidence package

```text
evidence-ch089/
  telemetry-contract.md
  auth-failure-signals.md
  acl-denial-coverage.md
  certificate-expiry.md
  kafkauser-drift.md
  kraft-security-health.md
  kubernetes-audit.md
  cloudtrail-msk.md
  external-secret-alerts.md
  network-egress.md
  consumer-anomaly.md
  connect-abuse.md
  siem-normalization.json
  alert-deduplication.md
  synthetic-detection-test.json
  credential-compromise-tabletop.md
  exfiltration-tabletop.md
  guarded-automation.md
  detection-quality.json
  independent-security-acceptance.md
  scorecard.md
```

Every artifact includes UTC time, source/version, synthetic-only inputs, **Live** versus **Tabletop**, observed alert and routing, missing coverage, privacy review, owner, approval and independent reviewer.

## 16. 100-point security detection acceptance

| Domain | Points | Critical |
|---|---:|---|
| Telemetry coverage and privacy-safe collection | 25 | Yes |
| Threat rules, correlation and tested alert routing | 25 | Yes |
| Kafka/KRaft/Strimzi/MSK control-plane detection | 15 | Yes |
| Incident response, automation safeguards and recovery | 20 | Yes |
| Evidence quality, detection metrics and runbooks | 5 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** leaked sensitive payloads, unapproved destructive automation, missing high-severity alert route, fabricated detection results, compromised KRaft/ISR or absent independent review.

**Current status:** **Pending**. No live detection coverage, red-team validation or security certification is claimed.

## 17. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes Auditing](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/), [Amazon MSK Monitoring](https://docs.aws.amazon.com/msk/latest/developerguide/monitoring.html), [Prometheus](https://prometheus.io/docs/).

**Next:** Chapter 090 — Kafka Enterprise Security, Governance and Compliance Acceptance Capstone.

---

**Verification boundary:** Publication confirms document availability only. Live alert delivery, security simulation, incident automation testing and independent technical/security review remain Pending.
