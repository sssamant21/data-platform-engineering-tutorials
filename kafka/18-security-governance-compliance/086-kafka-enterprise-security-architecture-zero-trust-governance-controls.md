# Chapter 086 — Kafka Enterprise Security Architecture, Zero Trust and Governance Controls

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 18 — Security, Governance and Compliance (1/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS; Amazon MSK security comparison  
**Prerequisites:** Chapters 001–085; Kafka listeners, SASL/TLS, ACLs, KRaft, Kubernetes RBAC and AWS IAM  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** All exercises are read-only audits or isolated design/tabletop work. Never publish client secrets, PHI/PII, private keys, JAAS passwords or production ACL dumps. Do not disable TLS/authentication, rotate production credentials, modify ACLs, NetworkPolicies or operator RBAC without staged review, Kafka ISR/quorum checks and rollback.

## 1. Mission and outcomes

Build a **zero-trust Kafka security architecture** spanning application producers/consumers, Kafka brokers and KRaft controllers, Strimzi operators, Kafka Connect, Kubernetes networking, AWS IAM, secrets, encryption, observability and governance. Establish identity-based least privilege, explicit trust boundaries, verified encryption, policy-as-code, audit trails and independent security acceptance.

Readers will produce a threat model, access matrix, certificate/secret lifecycle, isolation controls, incident playbooks and a measurable control scorecard.

## 2. Trust boundary architecture

```text
Users / applications / CDC / Kafka Connect
              |
    workload identity + mTLS/SASL/IAM
              |
      NetworkPolicy / VPC boundaries
              |
     Kafka brokers (TLS listeners + ACLs)
       |                       |
   partition logs          KRaft quorum
   encrypted PVC           controller listener
       |                       |
    data owners         controller identity/ACL
       +----------+------------+
                  |
          Strimzi operator
       scoped RBAC + GitOps policy
                  |
   secrets manager / KMS / cert issuer
                  |
      audit, SIEM, incident response
```

**Zero trust** means each service identity is authenticated, authorized for specific resources, and observed; private VPC placement alone does not confer trust.

## 3. Threat model and attack paths

| Asset | Threat | Required defense |
|---|---|---|
| Topic data | unauthorized read or exfiltration | authn, ACLs, network, audit |
| Producer writes | injection/tampering | scoped Write, idempotence, schema |
| Consumer groups | offset manipulation | scoped group ACLs |
| KRaft metadata | controller takeover | isolated authenticated listeners |
| Kafka Connect | malicious plugin or secret theft | plugin provenance, egress limits |
| Strimzi operator | cluster-wide privilege escalation | least-privilege RBAC |
| Client credentials | leak or replay | secret store, rotation, short-lived identities |
| TLS trust | interception/spoofing | SAN/CA verification and rotation |
| PVC/backups | offline data access | encryption, KMS and backup RBAC |
| Logs/metrics | PHI/PII exposure | minimization, redaction, retention |

Maintain a data-flow diagram, attack tree, asset owner, risk severity, mitigation and verification evidence.

## 4. Kafka authentication and authorization

Kafka supports TLS transport and authentication options including mTLS, SASL/SCRAM and other deployment/version-specific mechanisms. MSK can support IAM-based authentication depending on cluster type and client configuration. **Kafka ACLs are not Kubernetes RBAC**; enforce both independently.

Use per-service principals, topic/group-scoped operations, limited admin identities, approved super.users and deny-by-default design. Wildcard resource ACLs and shared credentials require explicit exception and compensating controls.

## 5. KRaft controller isolation

Controller listeners are a critical control-plane boundary. Separate controller and broker roles when appropriate for deployment size and reliability; enforce authenticated encrypted controller communication, isolated networking, authorized metadata operations and fault-tolerant quorum placement.

Do not modify controller security settings or membership without an approved maintenance plan. A security change that destroys quorum is a production outage.

## 6. Strimzi, Kubernetes and GitOps controls

- Scope Strimzi operator service accounts, namespaces, Roles and ClusterRoles to supported requirements.
- Use NetworkPolicies and VPC security groups to permit required client, broker, replication, controller and operator flows.
- Use GitOps for reviewed desired state, but never commit secret values.
- Apply policy-as-code for privileged Pods, host access, unsigned images, missing resource limits and prohibited broker exposure.
- Pin operator and broker images, scan dependencies, and preserve a supply-chain inventory.

**Caution:** Default-deny NetworkPolicy requires a CNI that enforces policies and explicit rules for DNS, metrics and Kafka replication. Audit before rollout.

## 7. Secrets, certificate and key lifecycle

Prefer a supported secrets manager and controlled Kubernetes Secret sync, with encryption at rest, namespace RBAC and audit. Document identity owner, issuance, renewal, revocation, emergency rotation, client rollout order and validation.

For TLS, verify hostname/SAN, CA chain, expiry and client trust; avoid disabling hostname verification as a quick fix. Coordinate trust-root overlap and Kafka client reconnect behavior during rotation.

## 8. Encryption and data governance

Encrypt broker PVCs/EBS, backups, object stores and sensitive logs with appropriately controlled keys. Classify topics by data sensitivity, owner, retention, schema, consumer authorization and legal constraints.

Healthcare workloads require **data minimization and access audit**; Kafka is a transport, not a substitute for HIPAA risk analysis or organizational compliance controls. Never store live patient identifiers or payloads in training evidence.

## 9. AWS MSK security comparison

For MSK, document supported IAM/SASL/TLS client authentication, cluster policies where applicable, VPC security groups, private connectivity, encryption at rest and transit, CloudTrail/CloudWatch observability and KMS key controls. Verify actual MSK provisioned/serverless capabilities and region/version compatibility.

Do not assume Kafka-native ACLs and IAM policies are interchangeable for every MSK authentication mode.

## 10. Audit and detection architecture

Collect security-relevant broker/client auth failures, ACL denials, TLS failures, admin/config changes, operator reconciliation, GitOps changes, cloud IAM activity, unusual egress and credential rotation events. Centralize into SIEM with time synchronization, least-privilege access, retention and redaction.

Some Kafka authentication/audit events require explicit broker logging configuration and are not available as comprehensive access logs by default; document coverage gaps.

## 11. Read-only security inventory commands

```bash
kubectl config current-context
kubectl get kafka,kafkanodepool -A
kubectl get serviceaccount,role,rolebinding -A
kubectl get networkpolicy -A
kubectl get secrets -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.type
kubectl get pods -A -l strimzi.io/kind=Kafka
```

The Secrets command lists **metadata only**. Never run `kubectl get secret -o yaml` into evidence. Access to Kubernetes resources does not prove Kafka ACL effectiveness.

## 12. Twenty Kubernetes-first security labs

### Lab 01 — Create threat model

**Procedure:** Map brokers, controllers, clients, operators, Connect, Schema Registry and trust boundaries.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 02 — Inventory Kafka security listeners

**Procedure:** Inspect TLS/SASL mechanisms, listener exposure and anonymous access without disclosing secrets.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 03 — Review KRaft controller security

**Procedure:** Document controller listener authentication, quorum isolation and ACL authority.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 04 — Review Strimzi operator RBAC

**Procedure:** Inspect namespace scope, service accounts, role bindings and reconciliation permissions.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 05 — Review Kubernetes NetworkPolicies

**Procedure:** Map permitted client-to-broker, broker-to-broker and operator flows.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 06 — Validate broker TLS design

**Procedure:** Review certificates, SANs, trust roots, expiry, rotation and TLS verification.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 07 — Validate client authentication

**Procedure:** Review mTLS, SCRAM and supported OAuth mechanisms, service identities and lifecycle.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 08 — Audit Kafka ACL least privilege

**Procedure:** Enumerate topic/group/cluster operations per principal and detect wildcard privileges.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 09 — Review super.users and admin access

**Procedure:** Document break-glass identities, MFA/approval path and audit requirements.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 10 — Review secret distribution

**Procedure:** Inspect ExternalSecrets/Secrets Store, encryption at rest, RBAC and no plaintext in Git.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 11 — Assess encryption at rest

**Procedure:** Review EBS/PVC, KMS, MSK and backup encryption with key lifecycle.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 12 — Assess AWS MSK IAM access

**Procedure:** Document supported IAM auth, VPC endpoints, roles and service limits.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 13 — Review Kafka Connect isolation

**Procedure:** Inspect connector plugins, worker privileges, network egress and secret handling.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 14 — Review schema and payload governance

**Procedure:** Classify PII/PHI, schemas, data minimization and ownership.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 15 — Review audit trail coverage

**Procedure:** Map admin/config/ACL changes, access events, GitOps changes and retention.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 16 — Review image supply chain

**Procedure:** Check pinned digests, signatures, scanning and operator image provenance.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 17 — Assess incident response controls

**Procedure:** Tabletop credential leak, unauthorized access and topic data exfiltration.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 18 — Validate policy as code

**Procedure:** Draft Kyverno/OPA checks for namespace, images, secrets and broker exposure.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 19 — Review security monitoring

**Procedure:** Map TLS failures, auth denials, ACL failures, unusual egress and alert ownership.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

### Lab 20 — Independent zero-trust acceptance

**Procedure:** Score control evidence, risk exceptions, remediation owners and security signoff.

**Expected evidence:** UTC time, approved environment, Kafka/Strimzi/Kubernetes/MSK versions, sanitized control inventory, trust-boundary diagram, identity/permission mapping, expected/observed policy result, ISR/KRaft impact, risk/rollback, exception owner and independent security reviewer. **Status: Pending** until executed. Credential, ACL, RBAC and NetworkPolicy mutations are **Tabletop** without isolated change approval.

## 13. Offline security control assessment validator

Save as `validate_security_controls.py`. It checks a **reviewed JSON control report** only; it cannot inspect a live cluster.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("report", help="Reviewed JSON security control report")
args = p.parse_args()
with open(args.report, encoding="utf-8") as f:
    d = json.load(f)

required = [
    "identity_isolation", "tls_hostname_verification", "least_privilege_acls",
    "kraft_controller_isolation", "secrets_rotation_plan", "encryption_at_rest",
    "audit_coverage", "data_governance", "network_policy_review",
    "independent_security_review", "evidence_ref"
]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing fields: " + ", ".join(missing))
checks = {k: d[k] is True for k in required if k != "evidence_ref"}
checks["evidence_reference"] = bool(d["evidence_ref"])
print(json.dumps({"checks": checks, "pass": all(checks.values())}, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
```

**Limitation:** The script trusts the submitted booleans. Independent reviewers must inspect raw control evidence and verify no material exceptions are concealed.

## 14. Twelve security failure scenarios

### Scenario 01 — Anonymous listener exposed

**Diagnosis:** Identify scope, block exposure, rotate impacted credentials and investigate access. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 02 — TLS certificate expires

**Diagnosis:** Check SAN/trust chain, planned rotation and client reconnect SLO. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 03 — Wildcard ACL grants broad access

**Diagnosis:** Revoke only through approved staged change and verify client contracts. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 04 — SCRAM credential leaked

**Diagnosis:** Revoke/rotate, audit client access and reconcile incident timeline. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 05 — KRaft controller listener reachable externally

**Diagnosis:** Restrict network and identity, preserve quorum and inspect logs. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 06 — Strimzi operator RBAC overprivileged

**Diagnosis:** Review namespace scope and reduce privileges without breaking reconciliation. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 07 — MSK IAM policy overly broad

**Diagnosis:** Scope actions/resources and validate supported authorization behavior. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 08 — Kafka Connect plugin exfiltrates data

**Diagnosis:** Isolate workers, restrict egress, review plugin provenance and audit. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 09 — PHI appears in logs or traces

**Diagnosis:** Contain exposure, redact, restrict retention and notify privacy response. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 10 — Secret committed to Git

**Diagnosis:** Revoke first, scrub history per policy and prevent recurrence. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 11 — NetworkPolicy blocks replication

**Diagnosis:** Restore reviewed broker traffic while preserving isolation and ISR. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

### Scenario 12 — Audit gaps hide admin changes

**Diagnosis:** Correlate GitOps/cloud/Kafka logs, mark control failed and remediate. Review Kafka principal/topic/group permissions, TLS trust, Strimzi/Kubernetes RBAC, KRaft quorum, cloud IAM, network and audit coverage. **Response:** Contain, preserve logs, rotate or revoke safely, protect Kafka durability and invoke security/privacy incident process. **Exit:** Access restricted, clients functional, ISR/quorum healthy, documented blast radius, RCA and security signoff.

## 15. Eight production security runbooks

### Runbook A — Credential compromise

**Trigger/actions:** Revoke/rotate principal, scope blast radius, audit access and verify client recovery. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook B — Unauthorized Kafka ACL access

**Trigger/actions:** Identify resource/principal, block access, preserve logs and review policy. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook C — TLS certificate rotation

**Trigger/actions:** Stage trust roots, rotate certificates, validate clients and roll back safely. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook D — KRaft/controller security incident

**Trigger/actions:** Protect quorum, isolate control-plane traffic and verify metadata integrity. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook E — Strimzi RBAC/NetworkPolicy change

**Trigger/actions:** Review GitOps diff, canary clients, ISR and reconciliation status. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook F — MSK IAM/VPC incident

**Trigger/actions:** Validate role trust, security groups, auth logs and managed service behavior. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook G — Sensitive data exposure

**Trigger/actions:** Invoke privacy/security incident procedures, containment and data-owner review. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

### Runbook H — Quarterly zero-trust acceptance

**Trigger/actions:** Audit principals, ACLs, certs, secrets, images, logs and exceptions. **No-go:** unreviewed credential/ACL change, exposed PHI, unauthenticated listener, degraded ISR/quorum or missing incident audit. **Exit:** Least privilege restored, Kafka/client SLO stable, audit retained and independent security acceptance.

## 16. Evidence package

```text
evidence-ch086/
  threat-model.md
  listeners-authentication.md
  kraft-controller-security.md
  strimzi-rbac.md
  network-policy-review.md
  tls-certificate-lifecycle.md
  client-authentication.md
  kafka-acl-matrix.md
  break-glass-admin.md
  secret-distribution.md
  encryption-at-rest.md
  msk-iam-vpc.md
  connect-plugin-isolation.md
  payload-data-governance.md
  audit-coverage.md
  supply-chain.md
  security-incident-tabletop.md
  policy-as-code.md
  detection-monitoring.md
  independent-acceptance.md
  security-controls.json
  scorecard.md
```

Every artifact must include UTC time, source/version, sanitized output, **Live** versus **Tabletop**, expected/observed result, data-classification risk, change/rollback, owner and independent reviewer.

## 17. 100-point zero-trust acceptance assessment

| Domain | Points | Critical |
|---|---:|---|
| Threat model, identities and Kafka ACL least privilege | 25 | Yes |
| TLS, secrets, KMS and encryption | 20 | Yes |
| KRaft, Strimzi RBAC and network isolation | 20 | Yes |
| Data governance, audit and incident response | 20 | Yes |
| Supply chain, policy-as-code and MSK controls | 5 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical controls independently evidenced. **Automatic Fail:** plaintext secrets, unauthorized topic access, exposed unauthenticated broker, compromised controller isolation, missing data governance, fabricated test results or absent independent review.

**Current status:** **Pending**, not security-certified.

## 18. References and next chapter

**References:** [Apache Kafka Security](https://kafka.apache.org/documentation/#security), [Strimzi](https://strimzi.io/documentation/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 087 — Kafka Identity, Access Management, Secrets and Certificate Lifecycle Engineering.

---

**Verification boundary:** Publication confirms document availability only. Live authentication/authorization testing, penetration assessment and independent technical/security review remain Pending.
