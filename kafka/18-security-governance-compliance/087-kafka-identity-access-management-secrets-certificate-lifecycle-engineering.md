# Chapter 087 — Kafka Identity, Access Management, Secrets and Certificate Lifecycle Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 18 — Security, Governance and Compliance (2/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on EKS, with Amazon MSK IAM comparison  
**Prerequisites:** Chapters 001–086; Kafka ACLs, SASL/TLS, Strimzi KafkaUser, KRaft, Kubernetes RBAC, IAM  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** All labs are read-only audits or offline/tabletop designs until separately approved in an isolated environment. Never output Kafka client passwords, Kubernetes Secret values, private keys, bearer tokens, patient identifiers or PHI. Credential rotation and ACL changes can cause production outages and must have owners, staged client rollout, ISR/KRaft monitoring and approved rollback/forward-fix.

## 1. Mission and learning outcomes

Engineer a **complete identity lifecycle** for Kafka producers, consumers, Kafka Connect, MirrorMaker, broker/controller services, Strimzi operator and Amazon MSK. Build least-privilege Kafka ACLs, segregated service identities, certificate trust and renewal, SCRAM credential rotation, supported OAuth/OIDC federation, cloud IAM and auditable break-glass procedures.

At the end, readers can distinguish Kubernetes RBAC, Kafka ACL authorization and AWS IAM; audit KafkaUser resources; design safe trust-root overlap; test authorization **denials** in isolated infrastructure; and manage compromised identities without weakening encryption or Kafka availability.

## 2. Identity and trust architecture

```text
GitOps policy and approved principal inventory
                |
  External Secrets / KMS / certificate issuer
                |
      Kubernetes Secret metadata
                |
  KafkaUser (Strimzi) + Kafka ACL desired state
                |
       Client authentication
       /        |          \
      mTLS    SCRAM     OAuth/MSK IAM*
                |
     Broker listener authorization
                |
     Topic + consumer-group ACLs
                |
  KRaft controller/broker service identities
                |
      audit, expiry and revocation

*Mechanisms depend on Kafka, Strimzi plugin and MSK cluster capabilities.
```

Private VPC placement and Kubernetes ServiceAccounts do not automatically grant Kafka topic access. Each trust boundary needs independent authorization.

## 3. Kafka authentication and ACL semantics

**Authentication** proves identity; **authorization** determines actions on Kafka resources. Kafka ACLs can scope `Topic`, `Group`, `Cluster`, `TransactionalId` and other supported resource types, with operations such as `Read`, `Write`, `Describe`, `Create` and `Alter`. Effective permission depends on ACL patterns, resource type, Kafka version and authorizer.

Design separate producer/consumer principals. A producer typically needs topic write-related operations; a consumer needs topic read and group access. Transactional producers and administration require additional narrowly scoped permissions. Test with actual clients rather than assuming a static matrix covers every protocol request.

## 4. Strimzi KafkaUser lifecycle

Strimzi can reconcile `KafkaUser` resources and associated authentication/authorization configuration when the User Operator is enabled and configured. Confirm operator capabilities and Kafka authorization mode; a KafkaUser CR does not imply that every external IAM/OAuth principal is managed identically.

**Illustrative review-only manifest (do not apply):**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: orders-consumer
  labels:
    strimzi.io/cluster: kafka-lab
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders
          patternType: literal
        operations: [Read, Describe]
      - resource:
          type: group
          name: orders-consumer
          patternType: literal
        operations: [Read]
```

Schema and resource versions vary by Strimzi release. Review the installed CRD before deploying. Never include generated password Secret data in Git.

## 5. mTLS and certificate lifecycle

A safe certificate design includes CA chain, SAN identity, expiry monitoring, issuer control, truststore management, overlapping trust, issuance/revocation and rollback planning. During CA replacement, clients must trust both old and new issuers during the migration window where supported.

Validate hostnames and certificates; do not set insecure verification flags to resolve failures. KRaft controller and inter-broker listeners require their own supported secure configuration and maintenance plan.

## 6. SCRAM credential rotation

SCRAM credentials are secrets, not identities by themselves. Maintain a principal owner, approved secret store, encrypted distribution, audit and rotation schedule. For near-zero downtime, consider introducing a new principal/credential and migrating clients before revoking the old one; changing a single password in place may interrupt clients.

Track authentication failures, consumer rebalances, lag, producer P99 and ISR throughout the change. Verify old credential rejection after revocation in an isolated authorized test.

## 7. OAuth/OIDC and cloud federation

OAuth support may require an appropriate Kafka authentication plugin or supported distribution/Strimzi configuration. Review issuer, JWKS, token audience, expiration, scopes, clock skew, key rotation and dependency availability. Avoid treating bearer tokens as permanent secrets.

For Amazon MSK IAM authentication, confirm cluster type, supported mechanisms/client libraries, IAM permissions and network path. IAM authorization and Kafka-native ACLs are not interchangeable across every MSK mode.

## 8. Kubernetes, EKS and secret delivery

Use scoped service accounts, RBAC, IRSA/Pod Identity where supported, encrypted Kubernetes Secrets and approved External Secrets/Secrets Store integration. Restrict who can read Secret **values**; even metadata can reveal service names and topology.

GitOps should contain references to secrets, not secret bytes. CI/CD must mask credentials and prevent secrets in logs, artifacts and Git history.

## 9. Least-privilege review and break-glass

Maintain an identity register: principal, workload owner, environment, topics/groups, operations, authentication method, secret issuer, expiry, emergency contact and recertification date.

Limit `super.users` and cluster-wide ACLs to audited administration. Break-glass access requires approval, short-lived credentials where possible, event recording, expiry and post-use review.

## 10. Read-only audit commands

```bash
kubectl config current-context
kubectl get kafka,kafkauser,kafkanodepool -A
kubectl get serviceaccount,role,rolebinding -A
kubectl get secrets -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,TYPE:.type
kubectl get certificates -A  # only if cert-manager CRDs are installed
```

Use `kubectl get kafkauser -A -o yaml` only in an approved restricted environment after sanitizing any sensitive metadata. Kafka ACL inventory requires an authenticated authorized Kafka admin client; do not expose its config.

## 11. Twenty Kubernetes-first identity labs

### Lab 01 — Map service identities

**Procedure:** Inventory producer, consumer, Connect, MirrorMaker, operator and controller principals; assign owners.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 02 — Inventory KafkaUser resources

**Procedure:** Review Strimzi KafkaUser auth type, ACL scopes and reconciled status without printing credentials.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 03 — Audit broker listener identity

**Procedure:** Review TLS, SASL mechanisms, listener separation, controller/broker identity and external endpoints.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 04 — Map Kafka ACL operations

**Procedure:** Build least-privilege matrix for Topic Read/Write/Describe, Group Read and Cluster operations.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 05 — Audit wildcard and super-user grants

**Procedure:** Flag broad resource patterns, prefixed ACLs, super.users and exception expiration.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 06 — Review mTLS certificate chain

**Procedure:** Inspect public certificate metadata, CA trust, SANs, expiry and client validation.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 07 — Review SCRAM credential lifecycle

**Procedure:** Document secret generation, rotation overlap, service owners and emergency revoke.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 08 — Review OAuth/OIDC federation

**Procedure:** Evaluate supported Kafka auth plugin, token audience, issuer, JWKS and refresh.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 09 — Review MSK IAM authorization

**Procedure:** Inventory IAM identity policies, cluster access, network path and authentication modes.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 10 — Review Kubernetes Secret metadata

**Procedure:** Check namespaces, Secret types, ownership, RBAC and encryption configuration.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 11 — Review external secret synchronization

**Procedure:** Document External Secrets/Secrets Store permissions, sync cadence and failure handling.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 12 — Audit certificate rotation automation

**Procedure:** Review cert-manager/Strimzi CA renewal policies, overlapping trust and rolling restarts.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 13 — Review key management

**Procedure:** Document KMS key owners, rotation, revocation, grants and backup decryptability.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 14 — Model credential blast radius

**Procedure:** Map which topics/groups and environments each credential can access.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 15 — Validate service-account isolation

**Procedure:** Review projected tokens, pod service accounts, IRSA/Pod Identity and scope.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 16 — Assess secret leak prevention

**Procedure:** Review Git secret scanning, CI masking, log redaction and incident response.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 17 — Tabletop certificate expiration

**Procedure:** Simulate expiring broker CA/client cert and verify safe rollout sequence.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 18 — Tabletop principal compromise

**Procedure:** Simulate leaked SCRAM/mTLS/IAM identity; scope, revoke, recover and audit.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 19 — Assess monitoring and audit

**Procedure:** Design alerts for auth failure spikes, TLS expiry, ACL denies and secret sync errors.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

### Lab 20 — Independent identity acceptance

**Procedure:** Review evidence, deny-by-default controls, rotation drills and signed exceptions.

**Expected evidence:** UTC timestamp, approved environment, Kafka/Strimzi/Kubernetes/MSK version, principal/resource owner, redacted configuration, expected versus observed authorization result, TLS/secret expiry, Kafka ISR/KRaft health, risk/abort, change approval and independent security reviewer. **Status: Pending** until executed. Authentication denial tests, secret rotations and ACL changes are **Tabletop** unless separately authorized in disposable infrastructure.

## 12. Offline identity policy verifier

Save as `verify_identity_register.py`. It validates a manually reviewed JSON register; it does **not** contact Kafka or prove ACL enforcement.

```python
#!/usr/bin/env python3
import argparse
import json
from datetime import date

p = argparse.ArgumentParser()
p.add_argument("register", help="Sanitized identity register JSON")
args = p.parse_args()
with open(args.register, encoding="utf-8") as f:
    entries = json.load(f)
if not isinstance(entries, list) or not entries:
    p.error("expected nonempty JSON list")

required = {"principal", "owner", "environment", "auth_method",
            "resources", "review_due", "evidence_ref"}
findings = []
for i, item in enumerate(entries, 1):
    if not isinstance(item, dict):
        findings.append(f"entry {i}: invalid object")
        continue
    missing = required - set(item)
    if missing:
        findings.append(f"entry {i}: missing {sorted(missing)}")
        continue
    if any(not str(item[k]).strip() for k in ("principal", "owner", "environment", "auth_method", "evidence_ref")):
        findings.append(f"entry {i}: blank required field")
    if not isinstance(item["resources"], list) or not item["resources"]:
        findings.append(f"entry {i}: no resource grants")
    for grant in item.get("resources", []):
        if not isinstance(grant, dict) or not grant.get("name") or not grant.get("operations"):
            findings.append(f"entry {i}: malformed grant")
        elif grant.get("name") == "*" or "All" in grant.get("operations", []):
            findings.append(f"entry {i}: broad grant requires exception")
    try:
        if date.fromisoformat(item["review_due"]) < date.today():
            findings.append(f"entry {i}: review overdue")
    except (TypeError, ValueError):
        findings.append(f"entry {i}: invalid review_due")
print(json.dumps({"entries": len(entries), "findings": findings, "pass": not findings}, indent=2))
raise SystemExit(0 if not findings else 1)
```

**Limitation:** This script only checks input shape, wildcard markers and dates. It cannot detect effective Kafka permissions, inherited cloud access, forged evidence or undocumented identities. Independent live authorization tests remain mandatory.

## 13. Twelve identity and secret failure scenarios

### Scenario 01 — Expired broker certificate blocks clients

**Diagnosis:** Check expiry/SAN/trust chain; stage CA overlap and recover without bypassing TLS. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 02 — Rotated SCRAM password breaks consumers

**Diagnosis:** Inspect client rollout order, old/new overlap, rebalances and lag. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 03 — KafkaUser ACL too broad

**Diagnosis:** Review patternType, operations, owners and safe staged narrowing. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 04 — KafkaUser reconciliation overrides manual ACL

**Diagnosis:** Treat GitOps/Strimzi as source of truth and review desired state. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 05 — OIDC issuer or JWKS unreachable

**Diagnosis:** Assess token validation, cache, clock skew, network and safe outage handling. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 06 — MSK IAM authentication denied

**Diagnosis:** Review identity policy, cluster permissions, signing client and connectivity. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 07 — ExternalSecret fails to refresh

**Diagnosis:** Check sync controller, provider IAM, expiry and reconciliation without exposing values. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 08 — mTLS SAN mismatch

**Diagnosis:** Correct certificate identity; never disable hostname verification. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 09 — Controller listener loses authentication

**Diagnosis:** Protect KRaft quorum and restore supported secured configuration. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 10 — Credential committed to repository

**Diagnosis:** Revoke/rotate immediately, investigate exposure and prevent future commits. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 11 — Break-glass principal remains active

**Diagnosis:** Review access approval, audit trail, expiry and emergency rotation. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

### Scenario 12 — Client credential reused across environments

**Diagnosis:** Separate prod/staging identities, topic scopes and secret stores. Correlate Kafka auth/ACL errors, TLS metadata, secret sync, Strimzi reconciliation, Kubernetes RBAC, IAM audit, client P99/lag and KRaft/ISR. **Response:** Contain or roll forward safely, preserve logs, revoke compromised access, maintain Kafka durability and document affected clients. **Exit:** Valid identity, least privilege, healthy Kafka, verified old-credential denial and signed incident review.

## 14. Eight production identity runbooks

### Runbook A — Kafka client certificate rotation

**Trigger/actions:** Inventory expiry, stage trust, issue certs, roll clients, monitor and retire old trust. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook B — SCRAM credential emergency rotation

**Trigger/actions:** Identify principals, generate new secret, coordinate clients, revoke and audit. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook C — KafkaUser ACL remediation

**Trigger/actions:** Review least-privilege diff, GitOps apply, client canary and rollback plan. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook D — MSK IAM access incident

**Trigger/actions:** Check policies, auth mode, identity trust, VPC path and cloud audit. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook E — External secret outage

**Trigger/actions:** Assess provider/sync failure, token expiry, fail closed and recover safely. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook F — Compromised service identity

**Trigger/actions:** Contain, revoke, scope Kafka topics/groups, preserve evidence and notify owners. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook G — KRaft/controller authentication recovery

**Trigger/actions:** Protect quorum, isolate listener changes and validate metadata/client availability. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

### Runbook H — Quarterly identity access recertification

**Trigger/actions:** Reconcile owners, dormant principals, ACLs, certs, secrets and exceptions. **No-go:** unapproved ACL/secret mutation, exposed credential, bypassed TLS verification, degraded ISR/quorum or unknown blast radius. **Exit:** Access restored or revoked correctly, Kafka/client SLO stable, audit retained and independent security signoff.

## 15. Evidence package

```text
evidence-ch087/
  identity-register.json
  kafkauser-inventory.md
  broker-listener-review.md
  acl-least-privilege.csv
  wildcard-superuser-review.md
  mtls-certificate-chain.md
  scram-rotation-plan.md
  oauth-oidc-federation.md
  msk-iam-review.md
  kubernetes-secret-metadata.md
  external-secret-sync.md
  certificate-automation.md
  kms-key-lifecycle.md
  credential-blast-radius.md
  service-account-isolation.md
  secret-leak-prevention.md
  certificate-expiry-tabletop.md
  principal-compromise-tabletop.md
  auth-monitoring.md
  independent-identity-acceptance.md
  scorecard.md
```

Each artifact includes UTC time, source/version, sanitized output, **Live** vs **Tabletop**, expected/observed result, owner, approval, rollback and independent reviewer. No secrets or PHI.

## 16. 100-point identity lifecycle acceptance

| Domain | Points | Critical |
|---|---:|---|
| Service identity and Kafka ACL least privilege | 25 | Yes |
| mTLS, SCRAM and certificate rotation | 25 | Yes |
| Kubernetes secret distribution and KMS | 15 | Yes |
| KRaft, OAuth/MSK IAM and environment isolation | 15 | Yes |
| Audit, compromise response and break-glass | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** leaked credentials, unauthenticated listener, overly broad unapproved grants, bypassed TLS verification, failed revocation, fabricated evidence or absent independent review.

**Current status:** **Pending**. No live identity or certificate rotation test is claimed.

## 17. References and next chapter

**References:** [Apache Kafka Security](https://kafka.apache.org/documentation/#security), [Strimzi](https://strimzi.io/documentation/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [cert-manager](https://cert-manager.io/docs/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html).

**Next:** Chapter 088 — Kafka Data Governance, Privacy, Retention and Compliance Engineering.

---

**Verification boundary:** Publication confirms document availability only. Live ACL denial tests, certificate rotations, secret synchronization and independent technical/security review remain Pending.
