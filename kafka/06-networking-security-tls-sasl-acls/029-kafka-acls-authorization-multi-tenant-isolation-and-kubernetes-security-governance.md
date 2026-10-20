# Chapter 029 — Kafka ACLs, Authorization, Multi-Tenant Isolation and Kubernetes Security Governance

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 06 — Networking, Security, TLS, SASL and ACLs (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft Kafka  
**Prerequisites:** Chapters 001–028, including TLS/mTLS, SASL/SCRAM and Kafka networking  
**Audience:** Kafka SREs, DBREs, platform engineers, security/IAM teams, data governance and application owners  
**Publication:** Published · **Live lab execution:** Pending · **Independent security review:** Pending

> **Production safety:** Do not enable or replace a production authorizer, modify super.users, revoke active production ACLs, grant wildcard access, change tenant identity mapping, or introduce default-deny policies without an approved impact analysis and recovery plan. Work in a disposable Kubernetes cluster. All examples require the installed Kafka/Strimzi release and authorizer to be validated before use. Kafka authentication is not authorization; Kubernetes RBAC and Kafka ACLs protect different resources.

## 1. Learning objectives

1. Explain Kafka principal/resource/operation/permission/host ACL semantics.
2. Design deny-by-default tenant permissions for topic, group, transactional ID and cluster operations.
3. Configure Strimzi-supported Kafka authorization and KafkaUser ACL reconciliation safely.
4. Verify authenticated principals from mTLS/SCRAM and OAuth integrations.
5. Prevent cross-tenant access with Kafka ACLs, namespace/RBAC boundaries and network controls.
6. Analyze prefixed versus literal ACL resource patterns and wildcard risks.
7. Build controlled allowed/denied tests, audit trails and permission drift checks.
8. Manage ACL changes via GitOps with change approvals and break-glass governance.
9. Troubleshoot `TopicAuthorizationException`, `GroupAuthorizationException` and principal mapping.
10. Execute security runbooks and a 100-point multi-tenant acceptance assessment.

## 2. Reference architecture

```text
Team A app Pod (namespace tenant-a)       Team B app Pod (namespace tenant-b)
  ServiceAccount A + Secret A                ServiceAccount B + Secret B
             |                                         |
      NetworkPolicy A                           NetworkPolicy B
             |                                         |
             +------------ TLS/SASL -------------------+
                                  |
                       Strimzi-managed Kafka
                       authenticated principal
                                  |
                    Kafka authorizer / ACLs
                         /                 \
               tenant-a topics       tenant-b topics
               tenant-a groups       tenant-b groups
                                  |
                  Audit, GitOps, reconciliation
```

**Trust boundaries:** Kubernetes namespace isolation is not a Kafka tenant boundary by itself. Kubernetes RBAC controls access to Kubernetes objects; Kafka ACLs control Kafka resources. NetworkPolicies control network flows, not topic authorization. Broker superusers bypass ordinary ACL constraints and require separate controls.

## 3. Kafka authorization fundamentals

An ACL commonly includes:

| Field | Meaning | Example |
|---|---|---|
| Principal | Authenticated Kafka identity | `User:tenant-a-producer` |
| Resource type | Topic, Group, Cluster, TransactionalId, DelegationToken where supported | Topic |
| Resource name | Exact name or prefix | `tenant-a.orders` |
| Pattern type | LITERAL or PREFIXED | LITERAL |
| Operation | Read, Write, Describe, Create, Alter, Delete, DescribeConfigs, AlterConfigs, IdempotentWrite, etc. | Write |
| Permission | ALLOW or DENY | ALLOW |
| Host | Client host match | `*` |

Operations and their implicit permission relationships vary by API. For example, producer idempotence, transactions and consumer group management can require permissions beyond a simple topic Write or Read. Consult the **Kafka version-specific authorization documentation** and test exact client behavior.

**Dangerous defaults:** some Kafka configurations permit operations when no ACL exists on a resource. Verify `allow.everyone.if.no.acl.found` and authorizer behavior; production tenant isolation should fail closed. Do not assume a missing ACL always means denied.

## 4. KRaft and Strimzi authorization compatibility

Modern KRaft clusters commonly use Kafka's `StandardAuthorizer`, but exact Strimzi `Kafka.spec.kafka.authorization` configuration, custom authorization options and user-operator ACL support depend on installed versions. The Strimzi `simple` authorization mode is an operator abstraction, not permission to copy broker `authorizer.class.name` blindly.

**Illustrative CR fragment, not a complete resource:**

```yaml
spec:
  kafka:
    authorization:
      type: simple
      superUsers:
        - CN=approved-kafka-admin
```

Do **not** apply the sample `superUsers` identity: actual principal mapping differs by TLS/SCRAM and version. Superuser names must be reviewed and tested. Confirm cluster/operator internal principals are supported before modifying authorization. Changing the authorizer can disrupt controller/broker operations and application traffic.

## 5. Tenant security model

For this chapter use two disposable tenants:

| Tenant | Topic | Consumer group | Identity | Intended access |
|---|---|---|---|---|
| A | `tenant-a.orders.ch29` | `tenant-a-consumer-ch29` | `tenant-a-client-ch29` | Read/Write/Describe own topic; Read own group |
| B | `tenant-b.orders.ch29` | `tenant-b-consumer-ch29` | `tenant-b-client-ch29` | Read/Write/Describe own topic; Read own group |

Expected: Tenant A cannot read/write Tenant B resources, and vice versa. Administrative principals are separate from application principals. Do not rely solely on topic naming conventions: **ACL enforcement must be proven**.

## 6. Preflight and evidence boundaries

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch29
kubectl config current-context | tee evidence-ch29/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,svc -o wide \
  | tee evidence-ch29/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.authorization}{"\n"}' \
  | tee evidence-ch29/authorization-config.txt
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch29/kafkauser-crd-versions.txt
```

**Stop** if production context, degraded quorum, unsupported CRD, absent authorization, no reviewed tenant identities or no approved test scope. Avoid publishing sensitive internal topology, real usernames, certificate material or credentials.

## 7. Lab 01 — Map principals, listeners and authorization

Inspect listener authentication modes and authorizer:

```bash
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}' \
  | tee evidence-ch29/listeners.txt
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch29/listener-status.txt
kubectl -n kafka-lab get kafkauser -o wide \
  | tee evidence-ch29/kafkauser-inventory.txt
```

Document actual authenticated principal names using approved Kafka audit/broker logs. A KafkaUser metadata name may not be the exact principal string for every authentication mechanism. **Acceptance:** principal-to-tenant map and correct secure listener.

## 8. Lab 02 — Review default-deny posture

Check approved effective Kafka authorizer configuration, especially `allow.everyone.if.no.acl.found`, superusers, cluster admin paths and existing ACLs. Strimzi may reject direct broker config properties that it owns; use supported CR fields and version-specific documentation.

**Acceptance:** documented fail-closed behavior, break-glass admin identity and verified control-plane health. If default-deny cannot be established in the disposable cluster, **stop** rather than reporting tenant isolation as passed.

## 9. Lab 03 — Create isolated KafkaTopic resources

Save `tenant-topics-ch29.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: tenant-a.orders.ch29
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 3600000
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: tenant-b.orders.ch29
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 3600000
```

```bash
kubectl apply --dry-run=server -f tenant-topics-ch29.yaml
kubectl apply -f tenant-topics-ch29.yaml
kubectl -n kafka-lab get kafkatopic \
  | tee evidence-ch29/topics.txt
```

**Acceptance:** both topics Ready, no topic auto-creation dependency and healthy RF3/minISR2. If topic operator configuration or API differs, adapt to installed release.

## 10. Lab 04 — Create least-privilege KafkaUser ACLs

The following **illustrative** Strimzi KafkaUser requires supported `simple` authorization and an enabled User Operator:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: tenant-a-client-ch29
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: tenant-a.orders.ch29
          patternType: literal
        operations: [Read, Write, Describe]
        host: "*"
      - resource:
          type: group
          name: tenant-a-consumer-ch29
          patternType: literal
        operations: [Read]
        host: "*"
```

Create the equivalent Tenant B KafkaUser using **only** Tenant B topic/group names. Do not grant Cluster `All`, Topic `All`, resource name `*` or wildcard-prefixed access to applications. Host `*` here does not replace NetworkPolicy; restrict client networks separately.

```bash
kubectl apply --dry-run=server -f tenant-a-user-ch29.yaml
kubectl apply --dry-run=server -f tenant-b-user-ch29.yaml
# Apply through approved GitOps after review.
```

**Acceptance:** KafkaUsers Ready, intended ACLs reconciled, and no extra tenant grants.

## 11. Lab 05 — Verify effective ACLs read-only

Use an approved administrative client configured for the actual secure listener:

```bash
# Inside approved admin client Pod with /etc/kafka/admin.properties:
# /opt/kafka/bin/kafka-acls.sh \
#   --bootstrap-server "$SECURE_BOOTSTRAP" \
#   --command-config /etc/kafka/admin.properties --list
```

`kafka-acls.sh` output can contain principal and resource names; redact sensitive information. Do not run ACL admin commands through the plaintext tutorial listener and mistake success for a secure auth test.

**Acceptance:** explicit Tenant A/B ACL inventory, no cross-tenant grants and no unexpected superuser exposure.

## 12. Lab 06 — Allowed produce/consume for Tenant A

From a restricted client Pod with Tenant A SCRAM identity, TLS trust and correct SASL_SSL config:

```bash
# Kafka client command examples inside the approved Pod:
# /opt/kafka/bin/kafka-console-producer.sh \
#   --bootstrap-server "$SECURE_BOOTSTRAP" \
#   --producer.config /etc/kafka/client.properties \
#   --topic tenant-a.orders.ch29
# /opt/kafka/bin/kafka-console-consumer.sh \
#   --bootstrap-server "$SECURE_BOOTSTRAP" \
#   --consumer.config /etc/kafka/client.properties \
#   --topic tenant-a.orders.ch29 \
#   --group tenant-a-consumer-ch29 --from-beginning --timeout-ms 10000
```

Produce only synthetic records. Capture counts and acknowledgments; do not log credentials. **Acceptance:** own-topic operations succeed, and authenticated principal is confirmed independently.

## 13. Lab 07 — Denied cross-tenant access

With Tenant A client credentials, attempt:

1. Describe `tenant-b.orders.ch29`.
2. Produce to `tenant-b.orders.ch29`.
3. Consume from `tenant-b.orders.ch29`.
4. Join `tenant-b-consumer-ch29`.

Use bounded timeouts and avoid auto-creating topics. Repeat symmetric tests for Tenant B against Tenant A.

**Acceptance:** every forbidden operation is denied by Kafka authorization; document actual exception and principal. A TCP timeout, TLS failure or invalid password is **not evidence** of an ACL denial.

## 14. Lab 08 — Group and transactional-ID authorization

Consumer group permissions are separate from topic permissions. Transactional producers can require transactional-ID permissions and additional cluster/topic operations depending on Kafka version and producer settings.

Design `tenant-a-tx-ch29` and `tenant-b-tx-ch29` resources. Only if transactional clients are available and approved, run positive and negative tests for each tenant. Never grant `TransactionalId:*` to applications.

**Acceptance:** documented minimum permissions for consumer groups and transactions, with live tests or Pending.

## 15. Lab 09 — Literal, prefixed and wildcard ACL review

Compare:

- LITERAL `tenant-a.orders.ch29`: one topic.
- PREFIXED `tenant-a.`: every resource whose name starts with that prefix.
- LITERAL `*`: wildcard resource matching, a dangerous broad grant.

A prefix policy requires enforceable tenant naming, namespace/resource admission controls and prevention of tenant-controlled names that impersonate other prefixes. Check inherited/implicit Kafka operations and `DENY` precedence with the installed authorizer.

**Acceptance:** approved resource-pattern matrix and explicit reasons for every prefix grant.

## 16. Lab 10 — Kubernetes namespace and Secret isolation

For stronger tenant isolation, design dedicated `tenant-a` and `tenant-b` namespaces and per-tenant ServiceAccounts. KafkaUser/Topic CR placement and Strimzi namespace-watching configuration depend on operator setup; do not assume CRs in every namespace are reconciled automatically.

```bash
kubectl -n kafka-lab get role,rolebinding -o wide \
  | tee evidence-ch29/rbac.txt
kubectl -n kafka-lab get serviceaccounts \
  | tee evidence-ch29/serviceaccounts.txt
kubectl -n kafka-lab get networkpolicy -o wide \
  | tee evidence-ch29/networkpolicies.txt
```

Check that tenant service accounts cannot read each other's Secrets or edit Kafka CRs. Verify actual permission with authorized RBAC review. Kubernetes RBAC denial does not prove Kafka topic isolation.

**Acceptance:** tenant identity/RBAC matrix and scoped Secret access.

## 17. Lab 11 — NetworkPolicy and client isolation review

Design namespace/Pod selectors allowing tenant client egress only to approved Kafka broker listener ports and DNS, with broker ingress scoped to approved tenant namespaces. CNI enforcement, service mesh behavior and external LB/firewall rules must be considered.

**Do not apply** a blanket default-deny NetworkPolicy to the Kafka broker namespace without accounting for inter-broker, KRaft controller, operator, metrics and DNS traffic.

**Acceptance:** flow matrix, policy dry-run/review and no interruption of Kafka control-plane communication.

## 18. Lab 12 — ACL GitOps change review

Create a pull request for a tenant ACL change with:

- Requester and resource owner.
- Business purpose and requested operations.
- Exact principal and LITERAL/PREFIXED resource.
- Expected positive and negative tests.
- Impact on existing consumers/producers.
- Expiry or periodic recertification date.
- Approver distinct from requester.
- Rollback and audit evidence.

For operator-managed KafkaUsers, update the KafkaUser CR rather than manually adding out-of-band ACLs that reconciliation may overwrite. Track emergency changes and reconcile back to Git.

**Acceptance:** approved least-privilege change and diff review.

## 19. Lab 13 — ACL drift and recertification

Compare desired KafkaUser ACLs with observed effective ACLs using an approved admin client. Flag:

- Unknown principals.
- Wildcard topic/group permissions.
- Privileged cluster operations.
- Stale tenant credentials.
- ACLs on deleted topics/groups.
- Differences between GitOps state and broker authorization.
- Superuser changes.

**Acceptance:** drift report with owner, severity, remediation ticket and evidence. Avoid automatic deletion until dependency review and incident risk are understood.

## 20. Lab 14 — Denial telemetry and security SLOs

Track:

- Authentication failures versus authorization denials.
- Denied topic/group/transaction operations by principal class.
- New wildcard ACLs and superuser changes.
- KafkaUser reconciliation failures.
- Secret access anomalies and certificate/password expiry.
- Tenant-level produce/fetch latency, consumer lag and availability.
- Kubernetes NetworkPolicy denies, broker health and KRaft quorum.

Metric names vary by Kafka/Strimzi/exporter version; validate deployed series. Ensure audit logging does not leak passwords, tokens, sensitive payloads or excessive personal data.

**Acceptance:** dashboards, alert thresholds, owner routing and reviewed retention.

## 21. Lab 15 — Break-glass and admin access tabletop

Scenario: a faulty ACL rollout blocks an application but admin identity remains available.

1. Identify exact affected principal/resource.
2. Freeze unrelated permission changes.
3. Use audited, time-bound break-glass admin access.
4. Restore the minimum required ACL via supported control plane.
5. Re-run positive and negative tests.
6. Reconcile GitOps state and revoke temporary admin access.
7. Perform post-incident recertification.

**Acceptance:** tested approval chain and least-privilege restoration plan; no permanent wildcard grants.

## 22. Lab 16 — Read-only automated governance preflight

Save `verify-ch29.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BIN=/opt/kafka/bin
BS=sre-kafka-kafka-bootstrap:9092

echo '[1/8] Context'
kubectl config current-context

echo '[2/8] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/8] Authorization declaration'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.authorization}{"\n"}'

echo '[4/8] Listener status'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[5/8] KafkaUser inventory'
kubectl -n "$NS" get kafkauser -o wide

echo '[6/8] Tenant topic inventory (optional)'
kubectl -n "$NS" get kafkatopic -o wide

echo '[7/8] Kubernetes RBAC/NetworkPolicy inventory'
kubectl -n "$NS" get role,rolebinding,networkpolicy -o wide

echo '[8/8] Baseline Kafka metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: read-only Kafka/Kubernetes governance inventory.'
echo 'NOT PROVEN: ACL deny-by-default, effective grants, cross-tenant denials or secure client auth.'
```

```bash
chmod +x verify-ch29.sh
./verify-ch29.sh | tee evidence-ch29/preflight.txt
```

**Acceptance:** script completes, or failed gates are recorded. This is an **inventory preflight**, not a security acceptance test.

## 23. Twelve production failure scenarios

### 23.1 Authenticated client cannot write
**Signal:** `TopicAuthorizationException`. **Check:** principal, topic ACL, resource pattern. **Recover:** approved least-privilege Write/Describe permission.

### 23.2 Consumer cannot join group
**Signal:** `GroupAuthorizationException`. **Check:** group ACL and client group.id. **Recover:** scoped Group Read permission.

### 23.3 Tenant A can read Tenant B topic
**Signal:** unexpected successful cross-tenant read. **Check:** wildcard/prefixed ACLs, superuser mapping and default-open behavior. **Recover:** security incident, revoke unintended grant, rotate credentials as warranted.

### 23.4 KafkaUser reconciles but ACL absent
**Signal:** KafkaUser Ready yet broker denies operation. **Check:** authorizer/User Operator compatibility and effective ACLs. **Recover:** supported reconciliation fix.

### 23.5 Prefix collision exposes another tenant
**Signal:** tenant controls resource under a shared prefix. **Check:** naming policy and prefix ACL. **Recover:** tighten patterns and enforce admission governance.

### 23.6 Emergency wildcard ACL remains active
**Signal:** privileged `*` grant after incident. **Check:** audit history and expiry. **Recover:** remove with approval after replacement least-privilege rules.

### 23.7 SCRAM identity maps to wrong principal
**Signal:** expected ACL does not match identity. **Check:** actual authenticated username/principal. **Recover:** identity mapping correction without broadening grants.

### 23.8 OAuth principal claim changes
**Signal:** sudden denials after IdP update. **Check:** subject/username claim and broker mapping. **Recover:** coordinated identity migration and ACL recertification.

### 23.9 Namespace RBAC allows Secret exfiltration
**Signal:** unauthorized Secret reads. **Check:** RoleBindings, service accounts, audit logs. **Recover:** contain, revoke, rotate and investigate.

### 23.10 NetworkPolicy blocks Kafka controller traffic
**Signal:** quorum instability following policy rollout. **Check:** controller/broker ports and CNI denies. **Recover:** restore approved control-plane paths.

### 23.11 Out-of-band ACL drift
**Signal:** broker ACLs differ from KafkaUser GitOps source. **Check:** reconciliation logs and admin changes. **Recover:** align desired state and remove unauthorized drift.

### 23.12 Transactional producer denied
**Signal:** transactional initialization/commit fails. **Check:** TransactionalId and other required operations. **Recover:** narrowly scoped permissions for actual producer workflow.

## 24. Troubleshooting matrix

| Symptom | Root cause candidate | First evidence | Owner |
|---|---|---|---|
| Topic authorization denied | Missing topic ACL | Effective ACL + principal | Kafka security |
| Group authorization denied | Missing Group Read | group.id + ACL | Kafka SRE |
| Transactional ID denied | Missing TxnId permission | transactional.id + ACL | App/Kafka |
| Cross-tenant access succeeds | Wildcard/prefix/superuser | Full ACL audit | Security incident |
| KafkaUser NotReady | User Operator/schema | CR status/events | Platform |
| ACL drift | Out-of-band mutation | Git vs broker diff | Governance |
| Secret access violation | RBAC/Pod mount | Kubernetes audit | Security |
| Broker quorum degraded | Policy/authorizer change | KRaft + CNI | Kafka SRE |
| Auth fails before ACL | TLS/SASL issue | Handshake/auth logs | IAM |
| New tenant cannot onboard | Namespace watch/ACL | Operator scope | Platform |

## 25. Eight production runbooks

### Runbook A — Topic authorization incident
1. Identify principal, resource, operation and listener.
2. Confirm TLS/SASL succeeded.
3. Inspect effective ACLs and KafkaUser status.
4. Apply approved minimum grant.
5. Re-run allowed and denied operations.
6. Document timeline and root cause.

### Runbook B — Cross-tenant data access incident
1. Contain unintended access and preserve audit evidence.
2. Identify wildcard/prefix grants, principals and accessed resources.
3. Revoke offending permissions using approved admin path.
4. Rotate credentials if exposure is suspected.
5. Verify negative cross-tenant tests.
6. Coordinate security/privacy response and corrective controls.

### Runbook C — ACL GitOps drift
1. Freeze unauthorized out-of-band changes.
2. Compare desired KafkaUser CRs with effective ACLs.
3. Identify operator reconciliation or manual mutations.
4. Correct through approved GitOps.
5. Re-run authorization tests.
6. Establish recurring drift detection.

### Runbook D — Tenant onboarding
1. Approve tenant identity, naming and data classification.
2. Provision secure listener/client identity.
3. Create tenant topic/group and scoped ACLs.
4. Configure Kubernetes namespace, RBAC and NetworkPolicy.
5. Run positive/negative acceptance.
6. Register owner, expiry and recertification.

### Runbook E — Tenant offboarding
1. Inventory clients, topics, groups and retention obligations.
2. Disable/revoke identity and ACLs with owner approval.
3. Verify no active application dependencies.
4. Apply data retention/deletion policies separately.
5. Remove disposable resources after approved hold period.
6. Archive audit and evidence.

### Runbook F — Privileged admin/break-glass
1. Obtain emergency approval and define time limit.
2. Use monitored dedicated admin identity.
3. Restore only necessary authorization.
4. Confirm no unintended cross-tenant permissions.
5. Revoke temporary privileges.
6. Complete incident audit.

### Runbook G — Kubernetes RBAC/Secret incident
1. Detect and contain unauthorized Kubernetes access.
2. Preserve audit logs and identify affected Secrets.
3. Remove broad RoleBindings and rotate impacted credentials.
4. Verify client access and Kafka authorization.
5. Validate network and namespace isolation.
6. Publish security review.

### Runbook H — Authorization game day
1. Obtain approval and baseline Kafka health.
2. Run own-topic positive tests for each tenant.
3. Run cross-tenant denied operations.
4. Exercise controlled ACL change and rollback tabletop.
5. Reconfirm ISR, KRaft and application health.
6. Sign off evidence and outstanding gaps.

## 26. Evidence package

```text
evidence-ch29/
  change-approval.md
  context.txt
  inventory.txt
  authorization-config.txt
  kafkauser-crd-versions.txt
  listeners.txt
  listener-status.txt
  kafkauser-inventory.txt
  topics.txt
  principal-mapping.md
  effective-acls-redacted.txt
  tenant-a-allowed.md
  tenant-b-allowed.md
  cross-tenant-denials.md
  group-transactional-id-tests.md
  prefix-wildcard-review.md
  rbac.txt
  serviceaccounts.txt
  networkpolicies.txt
  namespace-flow-matrix.md
  acl-gitops-review.md
  drift-report.md
  authorization-alerts.md
  break-glass-tabletop.md
  preflight.txt
  incident-review.md
  security-review.md
  assessor-signoff.md
```

Evidence must include expected/actual outcome, timestamps, versions, principal and resource **only where safe to disclose**, reviewer, and Pass/Fail/Pending. Never include private keys, SCRAM passwords, OAuth tokens, sensitive payloads or full unredacted internal identities in public GitHub artifacts.

## 27. Assessment — 100 points

| Domain | Points | Gate |
|---|---:|---|
| Authorization model and default-deny review | 10 | Critical |
| Principal and secure listener mapping | 10 | Critical |
| Tenant KafkaTopic/KafkaUser lifecycle | 10 | Critical |
| Effective ACL inventory and least privilege | 15 | Critical |
| Positive own-tenant produce/consume | 10 | Critical |
| Negative cross-tenant authorization tests | 15 | Critical |
| Group/transactional-ID permissions | 5 | Normal |
| Kubernetes RBAC/NetworkPolicy isolation | 10 | Critical |
| GitOps, drift detection and break-glass | 10 | Normal |
| Runbooks, audit evidence and signoff | 5 | Critical |
| **Total** | **100** | |

**Pass:** ≥85/100 and every critical gate passes. Any successful unauthorized cross-tenant read/write is an automatic **Fail**, regardless of numeric score. A read-only inventory or tabletop cannot substitute for live ACL denial evidence. If the installed Kafka/Strimzi version uses a different authorizer, document approved equivalent controls and test the actual enforcement path.

## 28. Cleanup and next chapter

Delete only owned disposable tenant topics, KafkaUsers and test Pods after retention and change approval. Do not delete operator-managed broker resources or live tenant data. Removing an authorizer or listener is a separate reviewed change with a dependency and rollback assessment.

**References:** [Apache Kafka Security and Authorization](https://kafka.apache.org/documentation/#security), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/).

**Next:** Chapter 030 — Kafka Networking, TLS, SASL and Authorization Kubernetes Security Reliability Capstone.

---

**Verification boundary:** GitHub publication establishes document availability only. Effective ACL enforcement, cross-tenant denial tests, security drills and independent review remain Pending until executed and signed off.
