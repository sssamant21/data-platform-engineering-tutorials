# Chapter 068 — Strimzi Kafka Security, Network Policies, TLS, Authentication and Multi-Tenant Isolation

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 14 — Advanced Kubernetes, Strimzi and GitOps (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–067, especially 026–030 and 066–067  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** All changes are for an approved disposable Kubernetes cluster and synthetic tenant data. Do not weaken TLS, grant wildcard production ACLs, publish external listeners, rotate real credentials, delete Secrets or run unauthorized cross-tenant access tests. Negative tests require explicit written approval. All examples are review templates and require installed-version CRD validation.

## 1. Mission and objectives

Build defense in depth for multi-tenant Kafka on Kubernetes: network segmentation, encrypted listeners, client identity, Kafka ACLs, Kubernetes RBAC, Secrets, quotas, audit and GitOps policy. The objective is to **prove both allowed access and denied access** without risking production tenants.

By completion, learners can map Kafka and Kubernetes trust boundaries, review Strimzi KafkaUser authentication, validate least-privilege ACL patterns, explain network connectivity constraints and prepare an independent security acceptance package.

## 2. Threat model and architecture

```text
 Tenant A namespace                      Tenant B namespace
 client SA + KafkaUser A                 client SA + KafkaUser B
         |                                        |
         +---- Kubernetes NetworkPolicy ---------+
                          |
                 TLS Kafka listener
                          |
              Broker authN + Kafka ACL
                   /             \
              topic-A/group-A   topic-B/group-B
                   |             |
              quotas + audit + data classification
                          |
                 Strimzi Operators
              (restricted K8s RBAC)
                          |
             GitOps desired state + policy
                          |
             KRaft controller quorum
```

**Trust boundaries:** Kubernetes ServiceAccount/RBAC governs Kubernetes API access; Kafka client identity/ACL governs Kafka protocol access. Kubernetes NetworkPolicy governs supported L3/L4 Pod traffic, **not** Kafka topic/group authorization. TLS protects transport but does not replace authorization or quotas.

## 3. Security controls matrix

| Layer | Control | Required verification |
|---|---|---|
| Kubernetes | namespace, RBAC, service account, admission | cannot mutate other tenant resources |
| Network | default-deny NetworkPolicy with approved exceptions | permitted Kafka paths work, others fail |
| Transport | TLS listener, trusted CA, SAN, expiry | encrypted handshake and cert validation |
| Identity | mTLS, SCRAM or supported OAuth | authenticated principal maps correctly |
| Kafka authorization | topic/group/TransactionalId ACL | explicit positive and negative tests |
| Credentials | Secrets/External Secrets, rotation | least privilege, no Git/log leakage |
| Resource isolation | quotas, partition/retention budgets | noisy neighbor contained |
| Observability | auth/ACL/TLS logs, policy drift | redacted audit and alert owner |
| Supply chain | pinned images, vulnerability review | reproducible signed provenance |
| GitOps | reviewed manifests and policy checks | unauthorized drift blocked |

**Caution:** Namespace isolation alone does not isolate Kafka tenants sharing a cluster. ACLs and identity boundaries are mandatory.

## 4. Listener and certificate engineering

- Prefer TLS-enabled listeners and require explicit approval for external exposure.
- Check Strimzi release-specific listener type, port, TLS, authentication and advertised endpoint fields.
- Clients must trust the issuing CA and verify hostname/SAN; do not disable certificate verification to work around mismatch.
- Record certificate issuance, expiration, CA rollover and client trust propagation order.
- For Kubernetes internal clients, include DNS and all advertised broker endpoints in NetworkPolicy design.
- For external clients, validate firewall, load balancer, DNS, authentication, public reachability and threat model.

## 5. KafkaUser and authorization patterns

KafkaUser supports release-dependent authentication and authorization features. Review the installed CRD before using examples.

```yaml
# Illustrative KafkaUser; validate against installed Strimzi CRD and cluster config.
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: tenant-a-producer
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: tenant-a.events
          patternType: literal
        operations:
          - Write
          - Describe
        host: "*"
```

This grants topic access only and is not a complete client deployment. Check whether a producer also needs idempotent/transactional permissions for its configured mode. Use distinct principals for producers, consumers, Streams, Connect and administrators; avoid broad wildcard topic/group grants. A `host: "*"` ACL is **not** a network firewall and must be paired with network controls.

## 6. Authentication mechanisms and operational tradeoffs

| Mechanism | Benefit | Operational risk |
|---|---|---|
| mTLS | certificate-based client identity and encrypted channel | CA trust, cert renewal, private-key handling |
| SCRAM | username/password authentication | secret leakage, rotation, password storage |
| OAuth/OIDC where supported | central token identity and policy integration | issuer/JWKS availability, audience, claims, token expiry |

Do not assume all Kafka/Strimzi versions support identical OAuth integration fields. Record supported release, token validation path, issuer, audience and clock-skew tolerance.

## 7. NetworkPolicy reference template

The following is a **restricted lab example**, not a complete production policy. Label selection and ports must match the actual Pods/listeners.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-approved-kafka-client
  namespace: kafka-lab
spec:
  podSelector:
    matchLabels:
      app: approved-tenant-a-client
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kafka-lab
          podSelector:
            matchLabels:
              strimzi.io/cluster: sre-kafka
      ports:
        - protocol: TCP
          port: 9093
```

**Limitations:** This permits egress from selected client Pods but does not configure broker ingress, DNS resolution, other broker listener ports or control-plane traffic. Strimzi-managed broker labels and ports vary by release and deployment. A complete deny-by-default design requires matching CNI enforcement and separate ingress/egress validation. A NetworkPolicy cannot constrain Kafka topic names.

## 8. Kubernetes and Strimzi read-only security inventory

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkauser,kafkatopic -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get serviceaccount,role,rolebinding
kubectl -n kafka-lab get svc -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl explain kafkauser.spec
kubectl explain kafka.spec.kafka.listeners
```

Do **not** dump Secrets or unredacted KafkaUser YAML into shared evidence. Inspect authorization metadata and only share sanitized excerpts.

## 9. Multi-tenant isolation and quotas

- Use per-tenant topic naming/ownership, KafkaUser principals and consumer group prefixes.
- Separate administrative identities from application identities; verify ACL inheritance/prefix matching and avoid unexpected wildcard grants.
- Review Kafka broker client quotas and any operator-supported quota fields against installed versions.
- Quotas mitigate shared-cluster contention but do not provide hard per-tenant CPU/disk isolation; account for shared partitions, controllers, network and storage.
- Limit topic partitions, replication, retention and throughput by an approved tenant capacity policy.
- Define PII classification, encryption, data retention, deletion and audit requirements independently of Kafka topic names.

## 10. GitOps security and secret rotation

Store **references** to secret managers or approved encrypted-secret resources in Git, never plaintext private keys, passwords or tokens. Use Git review and policy checks for listener exposure, wildcard ACLs, image pinning, resource quotas and privileged Pods. Operators may generate Secrets; avoid GitOps prune or overwrite of operator-managed credential resources.

Rotation plan: inventory principals and cert expiry; stage new trust where supported; rotate identity/credential through approved operator flow; verify all clients; revoke old credentials; retain redacted evidence. Rollback must not reactivate a compromised secret.

## 11. Twenty Kubernetes-first security labs

### Lab 01 — Security charter and tenant boundaries

**Procedure:** Define tenant identities, allowed topics/groups, data classification, owners and denied operations.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 02 — Operator and Kafka version inventory

**Procedure:** Capture Strimzi, Kafka, Kubernetes, installed CRDs and listener/auth support.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 03 — Trust boundary mapping

**Procedure:** Diagram clients, brokers, controllers, operators, API server and external entry points.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 04 — Listener exposure inventory

**Procedure:** Review bootstrap/advertised addresses, internal/external listeners and TLS requirements.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 05 — TLS certificate chain inspection

**Procedure:** Review broker cert SAN, CA chain, expiry, trust distribution and rotation owner.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 06 — KafkaUser TLS authentication

**Procedure:** Review operator-managed client certificate identity and least-privilege ACLs.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 07 — KafkaUser SCRAM authentication

**Procedure:** Review supported SCRAM mechanism, Secret lifecycle and brute-force monitoring.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 08 — OAuth/OIDC design review

**Procedure:** Verify release-specific listener support, issuer, audience, JWKS, token TTL and claims mapping.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 09 — ACL topic isolation

**Procedure:** Build per-tenant topic read/write/describe permission matrix.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 10 — ACL consumer group isolation

**Procedure:** Check group IDs, wildcard/prefix patterns and deny-by-default expectations.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 11 — TransactionalId and idempotence

**Procedure:** Review transactional ID authorization for Kafka Streams and producers.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 12 — NetworkPolicy ingress

**Procedure:** Review client namespace-to-broker connectivity, DNS and listener ports.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 13 — NetworkPolicy egress

**Procedure:** Review operator, brokers, DNS, OIDC/JWKS, monitoring and control-plane requirements.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 14 — Namespace and RBAC separation

**Procedure:** Review service accounts, role bindings, impersonation and operator watch scope.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 15 — Secret storage and rotation

**Procedure:** Review Kubernetes Secret access, external secret integration, rotation and audit.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 16 — Quotas and noisy-neighbor protection

**Procedure:** Review client quotas, topic partitions, retention, disk and throughput budgets.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 17 — Pod and image hardening

**Procedure:** Review non-root, capabilities, seccomp, image digest, vulnerabilities and volume access.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 18 — Audit and security observability

**Procedure:** Review auth failures, ACL denials, TLS handshake errors and privileged changes.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 19 — Negative authorization tests

**Procedure:** Plan synthetic cross-tenant produce, consume, group and transaction attempts.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

### Lab 20 — Independent tenant acceptance

**Procedure:** Reconcile positive/negative tests, data leakage controls, remediation and signoff.

**Evidence and acceptance:** Record approved scope, installed Kafka/Strimzi/Kubernetes versions, UTC time, exact principal/resource pattern, positive and negative expected result, observed authorization or network outcome, sanitized logs, owner, rollback/abort and independent security reviewer. Mark **Pending** until executed. Cross-tenant negative tests are **Tabletop** until authorized in an isolated environment.

## 12. Read-only verification script

Save as `verify-ch68.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] Kafka cluster'; kubectl -n "$NS" get kafka -o wide
echo '[3/9] KafkaUser metadata'; kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo '[4/9] Topics'; kubectl -n "$NS" get kafkatopic -o wide
echo '[5/9] NetworkPolicy'; kubectl -n "$NS" get networkpolicy
echo '[6/9] ServiceAccounts'; kubectl -n "$NS" get serviceaccount
echo '[7/9] RoleBindings'; kubectl -n "$NS" get rolebinding
echo '[8/9] Services'; kubectl -n "$NS" get svc -o wide
echo '[9/9] Installed CRD'; kubectl explain kafkauser.spec
echo 'PASS: read-only Kubernetes metadata inventory.'
echo 'NOT PROVEN: TLS trust, ACL denial, tenant isolation, secret rotation or security acceptance.'
```

Run `chmod +x verify-ch68.sh && ./verify-ch68.sh | tee evidence-ch68/preflight.txt`. Inventory success is **not** a security pass.

## 13. Twelve security failure scenarios

### Scenario 1 — TLS handshake fails after certificate rotation

**Diagnosis:** Check trust chain, SAN, CA bundle, client cache and certificate expiry. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 2 — KafkaUser Secret exists but authentication fails

**Diagnosis:** Check user readiness, listener mechanism, principal mapping and Secret version. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 3 — Producer denied on topic

**Diagnosis:** Check Write/Describe ACL, resource pattern, principal and listener auth. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 4 — Consumer joins unauthorized group

**Diagnosis:** Review Group ACL and prefix/wildcard scope; treat broad patterns as high risk. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 5 — Transactional producer fenced or denied

**Diagnosis:** Check TransactionalId ACL, producer identity, stale instance and broker coordinator. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 6 — OAuth tokens rejected

**Diagnosis:** Check issuer, audience, JWKS reachability, clock skew, claims and token expiry. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 7 — NetworkPolicy blocks Kafka metadata requests

**Diagnosis:** Check bootstrap and all advertised broker endpoints plus egress rules. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 8 — External listener unintentionally public

**Diagnosis:** Review Service/LoadBalancer, firewall, TLS/auth and incident containment. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 9 — Cross-tenant data read succeeds

**Diagnosis:** Declare security incident, revoke credentials, contain ACL and preserve audit. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 10 — Client quota throttling unexpectedly high

**Diagnosis:** Check client ID/principal mapping, shared identity and quota attribution. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 11 — Secret leaked in logs or Git

**Diagnosis:** Rotate credential, revoke old access, scrub artifacts and open incident. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

### Scenario 12 — Operator RBAC overprivileged

**Diagnosis:** Review ClusterRole/RoleBinding scope, namespace watch and admission policies. Correlate KafkaUser readiness, broker listener/auth logs, ACL principal and pattern, Kubernetes NetworkPolicy, Secret revision, client version and audit trail. **Response:** Preserve redacted evidence, contain unauthorized exposure, restore approved least privilege and escalate to security. **Exit:** Positive and negative synthetic tests, no known cross-tenant access, owner-approved remediation and independent signoff.

## 14. Eight production security runbooks

### Runbook A — TLS certificate expiry or rotation outage

**Trigger/response:** Inspect chain/SAN/expiry, validate rotation order and recover clients without plaintext fallback. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook B — Authentication or ACL outage

**Trigger/response:** Check principal, KafkaUser status, mechanism, resource pattern and least-privilege fix. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook C — Cross-tenant access incident

**Trigger/response:** Contain credentials, preserve audit, identify impacted topics and notify security owner. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook D — NetworkPolicy connectivity incident

**Trigger/response:** Map bootstrap/advertised endpoints, DNS, ingress/egress and rollback policy safely. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook E — OAuth/JWKS identity provider incident

**Trigger/response:** Inspect issuer/JWKS/token validity, time sync, approved failover and avoid auth bypass. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook F — Secret exposure and rotation

**Trigger/response:** Revoke/rotate, verify access, sanitize evidence and monitor replay attempts. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook G — Quota/noisy-neighbor incident

**Trigger/response:** Attribute principal/client IDs, enforce approved quotas and protect critical SLOs. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

### Runbook H — Independent multi-tenant security acceptance

**Trigger/response:** Review positive/negative tests, policy drift, RBAC, encryption, audit and signoff. **Abort/no-go:** plaintext fallback, wildcard production ACL without review, public listener without approval, credentials in logs/Git, unapproved cross-tenant testing or missing incident escalation. **Exit:** Restored encrypted/authenticated client connectivity, explicit authorization boundaries, sanitized audit, RCA and independent security approval.

## 15. Security SLI/SLO and acceptance matrix

| Signal | Required evidence | Escalation |
|---|---|---|
| TLS handshake failure rate | cert chain/SAN/expiry and client logs | rotation or trust incident |
| Kafka auth failure rate | principal/mechanism and broker logs | identity outage or attack |
| ACL denial rate | resource/pattern/principal audit | permission regression |
| Cross-tenant unauthorized success | negative test event ledger | immediate security incident |
| External listener exposure | Service/firewall/DNS inventory | contain unexpected exposure |
| Secret age and access | owner, rotation and RBAC | credential hygiene |
| Quota throttle rate | principal/client ID attribution | noisy-neighbor risk |
| GitOps policy violations | denied manifests, source revision | change governance |
| Kafka client SLO | synthetic TLS produce/consume | user-visible outage |

Do not set universal thresholds without tenant baseline and security policy. A single verified unauthorized cross-tenant read is a critical failure.

## 16. Evidence package

```text
evidence-ch68/
  security-charter-tenant-raci.md
  kafka-strimzi-kubernetes-version-matrix.md
  trust-boundary-threat-model.md
  listener-exposure-inventory.md
  tls-ca-san-expiry-rotation.md
  kafkauser-tls-identity.md
  kafkauser-scram-identity.md
  oauth-issuer-jwks-claims.md
  topic-acl-matrix.csv
  group-acl-matrix.csv
  transactional-id-authorization.md
  networkpolicy-ingress.md
  networkpolicy-egress-dns.md
  kubernetes-rbac-namespace-isolation.md
  secrets-access-rotation.md
  tenant-quotas-capacity.md
  pod-image-hardening.md
  security-audit-observability.md
  approved-negative-test-results.csv
  independent-security-acceptance.md
  scorecard.md
```

Every artifact needs UTC time, exact versions, approved scope, expected/observed result, **Live** vs **Tabletop**, redaction, owner, rollback/abort and reviewer. Never store private keys or tokens in evidence.

## 17. 100-point multi-tenant security assessment

| Domain | Points | Critical |
|---|---:|---|
| Threat model and trust boundaries | 10 | Yes |
| TLS listener, certificate and identity | 20 | Yes |
| KafkaUser topic/group/transactional ACL | 20 | Yes |
| NetworkPolicy and Kubernetes RBAC | 15 | Yes |
| Secret rotation and GitOps policy | 15 | Yes |
| Quotas, observability and incident runbooks | 10 | Yes |
| Positive/negative isolation tests | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** cross-tenant unauthorized success, leaked credential, unreviewed wildcard ACL, public listener without approval, TLS verification disabled, fabricated negative test or absent independent security review.

## 18. References and next chapter

**References:** [Strimzi Documentation](https://strimzi.io/documentation/), [Apache Kafka Security](https://kafka.apache.org/documentation/#security), [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

**Next:** Chapter 069 — Strimzi GitOps, Argo CD/Flux, Progressive Delivery and Policy-as-Code.

---

**Verification boundary:** Publication proves document availability only. Live TLS/ACL/NetworkPolicy tests, tenant negative testing and independent technical/security review remain Pending.
