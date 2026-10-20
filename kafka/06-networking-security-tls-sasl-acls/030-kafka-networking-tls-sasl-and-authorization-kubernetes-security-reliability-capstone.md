# Chapter 030 — Kafka Networking, TLS, SASL and Authorization Kubernetes Security Reliability Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 06 — Networking, Security, TLS, SASL and ACLs (5/5)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft Kafka  
**Prerequisites:** Chapters 026–029; Kafka/KafkaNodePool/KafkaTopic/KafkaUser CRDs; approved secure Kafka clients  
**Audience:** Kafka SRE, DBRE, platform security, IAM, application SRE and incident command teams  
**Publication:** Published · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety boundary:** Execute only in an approved disposable Kubernetes cluster. Do not change production Kafka listeners, CA trust anchors, SCRAM credentials, superusers, authorizers, ACLs, Kubernetes NetworkPolicies or Secret RBAC to perform this capstone. Do not weaken TLS hostname verification, expose private keys/passwords/tokens, or simulate failures by deleting production Secrets or broker Pods. All write operations require GitOps review and rollback. Publication is **not** operational acceptance.

## 1. Capstone mission and success criteria

This capstone integrates Chapter 026 networking and advertised listeners, Chapter 027 TLS/mTLS and certificate lifecycle, Chapter 028 SCRAM/OAuth identity, and Chapter 029 ACL and tenant isolation. The goal is to prove that **authenticated, authorized tenant traffic stays available and isolated during controlled platform changes and failures**.

The acceptance standard is evidence-driven:

- Every advertised broker endpoint resolves and is reachable from intended client networks.
- TLS certificate chain and hostname verification succeed without bypass.
- SCRAM or mTLS identities map to expected Kafka principals.
- Authorized tenant operations succeed; cross-tenant operations fail **at the Kafka authorization layer**.
- Kubernetes ServiceAccounts, Secrets, RBAC and NetworkPolicies enforce intended boundaries.
- Certificate/credential rotation is recoverable, with observed application impact.
- KRaft quorum, ISR, broker readiness, producer acknowledgments and consumer lag stay within defined SLOs.
- Incidents have actionable runbooks, rollback gates, owners and sanitized evidence.
- OAuth is a **conditional integration gate** requiring an actual supported IdP and Strimzi/Kafka integration; no simulated token flow is reported as live success.

## 2. Production-like reference architecture

```text
    GitOps PR + approval + policy validation + signed evidence
                            |
                            v
               Strimzi Cluster Operator
                  Kafka / KafkaNodePool
                  KafkaUser / KafkaTopic
                            |
         +------------------+-------------------+
         |                                      |
 tenant-a namespace                       tenant-b namespace
  Pod + ServiceAccount                     Pod + ServiceAccount
  SCRAM Secret A                           SCRAM Secret B
  CA trust bundle                          CA trust bundle
  NetworkPolicy A                          NetworkPolicy B
         |                                      |
         +--------- Kubernetes DNS/Service -----+
                            |
                   Kafka SASL_SSL listener
                   TLS server identity + SAN
                   SCRAM-SHA-512 / mTLS
                            |
                     Kafka authorizer
                      /            \
             Tenant A topic       Tenant B topic
             Tenant A group       Tenant B group
                            |
              KRaft controllers + Kafka brokers
              PVCs / ISR / client telemetry
                            |
              Alerts / audit / SLO / incident
```

Kubernetes namespace separation, NetworkPolicy, Secret RBAC and Kafka ACLs are **complementary**; no single control substitutes for another.

## 3. Scope and threat model

| Asset | Threat | Primary control | Evidence |
|---|---|---|---|
| Bootstrap/advertised DNS | Misdirection or outage | Verified DNS/SAN/endpoints | Per-broker connection test |
| Kafka traffic | Interception | TLS and hostname verification | Handshake evidence |
| Client identity | Credential theft/replay | Secret RBAC, rotation, short-lived credentials | Access/rotation audit |
| Topic data | Cross-tenant read/write | Kafka ACLs and fail-closed authorization | Positive/negative tests |
| KRaft metadata | Control-plane disruption | Broker/controller isolation, operator readiness | Quorum health |
| OAuth token | Invalid issuer/audience/signature | Verified OIDC validation | IdP integration evidence |
| Kubernetes Secrets | Unauthorized reads | Namespace RBAC, Pod mount scoping, encryption | Access review |
| Change process | Accidental security outage | GitOps, canary, rollback | Approval and timeline |
| Availability | Auth failures and listener misconfiguration | SLO/alerts/runbooks | Failure drill |
| Audit trail | Missing or sensitive logs | Redaction, access/retention policies | Security review |

**Assumptions:** Dedicated disposable cluster; Kafka RF3/minISR2 for test topics; compatible Strimzi/Kafka versions; approved client image pinned by digest; correct TLS-enabled listener; secure admin access. Verify all before executing.

## 4. Hard stop conditions

Stop and record **Blocked** if any of these is true:

1. Current context points to production or a shared cluster without explicit change approval.
2. Kafka or KRaft quorum is degraded before testing.
3. Installed CRD/Strimzi version does not support the proposed auth/authorization.
4. Kafka listener has no TLS or client disables hostname verification.
5. Tenant principal mapping or default-deny behavior is unverified.
6. No approved rollback path for the listener, credential or ACL change.
7. Any evidence would expose private keys, passwords, raw OAuth tokens or customer data.
8. Monitoring and incident owner are unavailable for an active failure drill.

## 5. Test inventory and naming

```text
Kubernetes namespace (broker): kafka-lab
Kafka cluster:                sre-kafka
Kafka CLI Pod:                kafka-cli
Legacy lab bootstrap:        sre-kafka-kafka-bootstrap:9092 (plaintext; baseline only)
Secure listener:             configured SASL_SSL or mTLS listener (discover status)
Tenant A principal:          tenant-a-client-ch30
Tenant B principal:          tenant-b-client-ch30
Tenant A topic:              tenant-a.orders.ch30
Tenant B topic:              tenant-b.orders.ch30
Tenant A consumer group:     tenant-a-group-ch30
Tenant B consumer group:     tenant-b-group-ch30
Evidence directory:          evidence-ch30/
```

The secure bootstrap endpoint is **not** assumed to be 9093, 9094 or 9095; read `Kafka.status.listeners`. Do not confuse a successful plaintext 9092 baseline with a TLS/SASL acceptance test.

## 6. Lab 01 — Baseline and approval

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch30
kubectl config current-context | tee evidence-ch30/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,svc,pvc -o wide \
  | tee evidence-ch30/baseline.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch30/listener-status.txt
```

Record cluster owner, ticket, reviewer, test window, abort conditions and rollback approver. **Acceptance:** healthy baseline and approved disposable environment.

## 7. Lab 02 — Version and capability matrix

```bash
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch30/kafka-crd.txt
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch30/kafkauser-crd.txt
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}' \
  | tee evidence-ch30/listener-spec.txt
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.authorization}{"\n"}' \
  | tee evidence-ch30/authorizer-spec.txt
```

Check Kafka, Strimzi, Kubernetes, Kafka client and IdP plugin versions. Verify User Operator scope and whether `simple` authorization is supported. **Acceptance:** signed compatibility matrix; unsupported integrations explicitly Pending.

## 8. Lab 03 — DNS and Kubernetes Service path

```bash
kubectl -n kafka-lab get svc -l strimzi.io/cluster=sre-kafka -o wide \
  | tee evidence-ch30/services.txt
kubectl -n kafka-lab get endpointslice \
  -l kubernetes.io/service-name=sre-kafka-kafka-bootstrap \
  -o wide | tee evidence-ch30/bootstrap-endpoints.txt
kubectl -n kafka-lab get networkpolicy -o wide \
  | tee evidence-ch30/networkpolicies.txt
```

From an approved diagnostic Pod, resolve the actual secure bootstrap and each advertised broker DNS name, then test TCP connectivity to the reported ports. Avoid assuming all broker connections use the bootstrap Service. **Acceptance:** every endpoint reachable from intended namespace, no unapproved egress.

## 9. Lab 04 — Verify TLS chain, SAN and expiry

Inspect **certificate-only** metadata from the correct Strimzi CA Secret after confirming installed release and Secret key names. Do not export private keys.

```bash
umask 077
mkdir -p .secrets-ch30
kubectl -n kafka-lab get secret sre-kafka-cluster-ca-cert \
  -o jsonpath='{.data.ca\.crt}' \
  | base64 -d > .secrets-ch30/cluster-ca.crt
openssl x509 -in .secrets-ch30/cluster-ca.crt \
  -noout -subject -issuer -dates -fingerprint -sha256 \
  | tee evidence-ch30/ca-metadata.txt
```

Verify the live server certificate for bootstrap **and advertised brokers** using an approved TLS diagnostic client and hostname validation. mTLS endpoints may reject handshakes without client credentials. **Acceptance:** chain/SAN/expiry valid; no `ssl.endpoint.identification.algorithm=` bypass.

## 10. Lab 05 — Secure listener and authenticated principal

A production-like secure listener uses `tls: true` with supported Strimzi `authentication.type: scram-sha-512` or `tls`. OAuth requires an actual supported plugin and IdP.

Use a pinned approved Kafka client image and mounted Secret credentials; securely generate client properties in a restricted ephemeral file (mode 0600). **Never put passwords into command-line arguments, shell history or Git.**

```bash
# Run INSIDE an approved client Pod after client.properties exists:
# /opt/kafka/bin/kafka-topics.sh \
#   --bootstrap-server "$SECURE_BOOTSTRAP" \
#   --command-config /etc/kafka/client.properties --list
```

Confirm authenticated principal from trusted broker/authentication audit evidence, not from Pod or Secret names alone. **Acceptance:** TLS hostname verified, SASL/mTLS succeeded, correct principal recorded.

## 11. Lab 06 — Provision two isolated KafkaTopics

Save `tenant-topics-ch30.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: tenant-a.orders.ch30
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
  name: tenant-b.orders.ch30
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
kubectl apply --dry-run=server -f tenant-topics-ch30.yaml
# Only after change approval:
kubectl apply -f tenant-topics-ch30.yaml
kubectl -n kafka-lab get kafkatopic tenant-a.orders.ch30 tenant-b.orders.ch30 \
  -o wide | tee evidence-ch30/tenant-topics.txt
```

**Acceptance:** topics Ready and healthy RF3/minISR2. Topic Operator may be scoped to a namespace; validate scope first.

## 12. Lab 07 — Provision two least-privilege KafkaUsers

**Illustrative Tenant A KafkaUser; requires supported User Operator and Kafka `simple` authorization:**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: tenant-a-client-ch30
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
          name: tenant-a.orders.ch30
          patternType: literal
        operations: [Read, Write, Describe]
        host: "*"
      - resource:
          type: group
          name: tenant-a-group-ch30
          patternType: literal
        operations: [Read]
        host: "*"
```

Tenant B uses only its own topic/group. Host `*` is not a network isolation control; apply separate Kubernetes policies. Do not add broad topic/group wildcards or Cluster `All`. **Acceptance:** KafkaUsers Ready, expected principals, no cross-tenant ACLs.

## 13. Lab 08 — Positive tenant tests

For each tenant, using **its own** secure client identity:

1. Describe only its own topic.
2. Produce a unique synthetic record with `acks=all`.
3. Consume from its own topic with its assigned consumer group.
4. Verify received record matches produced record.
5. Record client auth principal, latency and result.

Use a unique test ID (for example `ch30-a-001`) and never rely on hardcoded offsets. **Acceptance:** A→A and B→B succeed with correct Kafka principals and no authorization bypass.

## 14. Lab 09 — Cross-tenant negative tests

Using Tenant A identity, attempt to describe/produce/consume Tenant B topic and join Tenant B group. Repeat in reverse.

**Required distinction:** A rejected TLS handshake or wrong SCRAM password does **not** prove ACL isolation. The client must first authenticate successfully, then receive a Kafka authorization denial for forbidden resources.

**Acceptance:** all cross-tenant operations denied by Kafka authorizer; any successful unauthorized read/write is an automatic **Fail**.

## 15. Lab 10 — Kafka ACL inventory and default-deny

From an approved secure administrative client:

```bash
# /opt/kafka/bin/kafka-acls.sh \
#   --bootstrap-server "$SECURE_BOOTSTRAP" \
#   --command-config /etc/kafka/admin.properties --list
```

Review effective ACLs, superusers, wildcard/prefix patterns and `allow.everyone.if.no.acl.found` behavior. Do not modify authorizer configuration in this lab. **Acceptance:** explicit fail-closed posture and no cross-tenant grants; record a security finding if default-open behavior exists.

## 16. Lab 11 — Kubernetes RBAC and Secret boundary

```bash
kubectl -n kafka-lab get serviceaccounts \
  | tee evidence-ch30/serviceaccounts.txt
kubectl -n kafka-lab get role,rolebinding -o wide \
  | tee evidence-ch30/rbac.txt
kubectl -n kafka-lab get secrets -l strimzi.io/cluster=sre-kafka \
  -o custom-columns=NAME:.metadata.name,TYPE:.type \
  | tee evidence-ch30/secret-metadata.txt
```

Review dedicated tenant namespaces/service accounts, Secret mounts, restricted read permissions and audit logs. The client Pod's ability to mount a named Secret does not require its ServiceAccount to have Kubernetes API Secret `get` permission. **Acceptance:** tenant access matrix and no unauthorized Secret exposure.

## 17. Lab 12 — NetworkPolicy boundary and broker continuity

Review namespace egress and broker ingress policies against:

- Client-to-bootstrap and client-to-advertised broker flows.
- Kafka inter-broker and KRaft controller communication.
- Strimzi Operator, User Operator, Topic Operator and metrics access.
- DNS, IdP/JWKS egress and certificate infrastructure where needed.

Do not apply default-deny policies to brokers without an approved flow matrix. **Acceptance:** tenant connectivity allowed, unauthorized paths denied, KRaft quorum and ISR healthy.

## 18. Lab 13 — Credential renewal and application recovery

Choose a disposable SCRAM KafkaUser or mTLS client and a supported Strimzi credential renewal method.

1. Record old credential metadata without values.
2. Approve rotation and client rollout plan.
3. Update credential through supported operator mechanism.
4. Verify Secret propagation and application reload/restart.
5. Re-authenticate, produce/consume and check lag.
6. Confirm stale credentials are rejected when policy requires.
7. Record downtime, retries and rollback.

**Do not assume** SCRAM password overlap or automatic application reload. For production, consider parallel principals and staged migration. **Acceptance:** actual renewal/reconnect evidence or Pending; no secret leakage.

## 19. Lab 14 — Certificate and CA rotation tabletop

Model leaf renewal separately from CA key replacement. Review:

- Old/new trust overlap and client truststore distribution.
- Every advertised broker SAN and DNS identity.
- Client applications that require restart after Secret updates.
- Operator-supported CA rotation mechanics for installed Strimzi.
- Rollback feasibility, time-to-expiry and maintenance windows.
- KRaft/ISR health throughout rolling reconciliation.

**Acceptance:** signed CA rotation plan, client owner inventory and abort thresholds. **Live CA rotation is not required** and must not be performed without separate approval.

## 20. Lab 15 — OAuth/OIDC conditional integration

If a supported IdP and Strimzi/Kafka OAuth plugin exist, validate:

1. Trusted issuer and exact audience.
2. JWKS HTTPS trust, cache and signing-key rotation.
3. Token expiry, not-before, clock skew and refresh.
4. Principal claim mapping and Kafka ACLs.
5. IdP/JWKS outage behavior without fail-open bypass.
6. No raw access tokens or client secrets in evidence.

Without a real supported IdP, mark **OAuth: Pending / Not in lab scope** and assess the design only. Do not count a tabletop as successful token authentication.

## 21. Lab 16 — Controlled networking failure game day

Use a **disposable client Pod** to simulate:

- Wrong bootstrap DNS.
- Closed or incorrect listener port.
- Missing DNS resolution.
- Wrong advertised broker endpoint in a **client-side test harness**, without editing broker advertised listeners.

Capture whether errors occur at DNS, TCP, TLS, SASL or metadata-discovery stages. Restore the client configuration and verify all advertised broker endpoints. **Acceptance:** correct failure classification, recovery time and no broker configuration mutation.

## 22. Lab 17 — TLS/SASL negative-test game day

Use a disposable client and approved synthetic identities:

- Wrong CA: TLS chain failure.
- Wrong hostname: SAN verification failure.
- Wrong SCRAM password: SASL authentication failure.
- Correct identity, unauthorized topic: Kafka ACL denial.
- Correct identity and permitted topic: success.

Never disable TLS verification or log credentials to make a test pass. **Acceptance:** five distinct expected outcomes with sanitized evidence.

## 23. Lab 18 — ACL rollback and break-glass tabletop

Scenario: an approved ACL change accidentally denies an application.

1. Detect increased authorization denials.
2. Identify affected principal/resource and latest GitOps diff.
3. Freeze further unrelated changes.
4. Use approved time-bound administrative access if needed.
5. Restore only the minimum prior ACL.
6. Re-run positive and cross-tenant negative tests.
7. Reconcile GitOps and revoke temporary admin privilege.

**Acceptance:** rollback owner, target recovery time, audit log and no wildcard privilege left behind.

## 24. Lab 19 — Observability, SLIs and SLOs

Define baseline and acceptance thresholds **before** the game day:

| SLI | Measurement | Example objective (adapt) |
|---|---|---|
| Authenticated client success | Successful secure client operations / attempts | ≥99.9% outside approved drill |
| Authorization correctness | Forbidden cross-tenant requests denied | 100% |
| TLS validity | Valid chain + SAN across endpoints | 100% |
| Client reconnect time | Rotation/failure to successful authenticated operation | ≤5 minutes |
| Producer durability | Acknowledged `acks=all` synthetic records recovered | 100% |
| Consumer recovery | Time until synthetic backlog drains | ≤10 minutes |
| Kafka cluster health | Kafka Ready, KRaft quorum, ISR stable | No unplanned degradation |
| Secret governance | Unauthorized Secret reads detected/blocked | Zero tolerated |

Example SLOs are **design targets, not observed measurements**. Validate metric sources and dashboards for installed Kafka/Strimzi version. Separate Kafka auth failures, TLS errors, ACL denials, DNS issues and client bugs.

## 25. Lab 20 — Read-only automated capstone preflight

Save `verify-ch30.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BIN=/opt/kafka/bin
BS=sre-kafka-kafka-bootstrap:9092

echo '[1/10] Kubernetes context'
kubectl config current-context

echo '[2/10] Kafka readiness'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/10] Strimzi API versions'
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'

echo '[4/10] Listener spec and status'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[5/10] Kafka authorizer declaration'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.authorization}{"\n"}'

echo '[6/10] Services and EndpointSlices'
kubectl -n "$NS" get svc -l "strimzi.io/cluster=$CLUSTER"
kubectl -n "$NS" get endpointslice \
  -l kubernetes.io/service-name=sre-kafka-kafka-bootstrap

echo '[7/10] KafkaUser/Topic inventory'
kubectl -n "$NS" get kafkauser,kafkatopic

echo '[8/10] RBAC and NetworkPolicy inventory'
kubectl -n "$NS" get role,rolebinding,networkpolicy

echo '[9/10] Secret metadata only'
kubectl -n "$NS" get secrets -l "strimzi.io/cluster=$CLUSTER" \
  -o custom-columns=NAME:.metadata.name,TYPE:.type

echo '[10/10] KRaft metadata quorum (legacy plaintext lab path)'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: read-only Kubernetes/Kafka security inventory.'
echo 'NOT PROVEN: TLS/SASL authentication, effective ACLs, cross-tenant denials, rotation or OAuth.'
```

```bash
chmod +x verify-ch30.sh
./verify-ch30.sh | tee evidence-ch30/preflight.txt
```

**Interpretation:** this script performs inventory and KRaft health checks. A PASS is **not** capstone acceptance; live secure-client tests and independent review are required.

## 26. Twelve production failure scenarios

### 26.1 Bootstrap DNS resolves but advertised broker DNS fails
**Signal:** bootstrap succeeds, metadata requests time out. **Diagnose:** broker advertised endpoints and namespace DNS. **Recover:** approved DNS/listener correction.

### 26.2 TLS server certificate expires
**Signal:** TLS handshake errors. **Diagnose:** broker cert `notAfter`, operator reconciliation. **Recover:** supported renewal and client verification.

### 26.3 SAN mismatch on one broker
**Signal:** intermittent failures by partition leader. **Diagnose:** advertised broker hostname versus cert SAN. **Recover:** supported listener/certificate correction.

### 26.4 Client CA trust stale after rotation
**Signal:** new broker cert rejected by a client cohort. **Diagnose:** truststore version and Secret propagation. **Recover:** staged CA trust distribution and client reload.

### 26.5 SCRAM password rotated before client reload
**Signal:** authentication spike. **Diagnose:** KafkaUser Secret version and client rollout. **Recover:** coordinated supported credential recovery.

### 26.6 OAuth audience or issuer mismatch
**Signal:** token rejected despite valid signature. **Diagnose:** `aud`, `iss`, trusted IdP config. **Recover:** correct approved token issuance/validation.

### 26.7 JWKS outage or key rollover
**Signal:** token validation failure. **Diagnose:** IdP availability, JWKS cache, signing key ID. **Recover:** restore trusted JWKS path without disabling signature validation.

### 26.8 Cross-tenant topic access succeeds
**Signal:** unauthorized read/write. **Diagnose:** wildcard ACL, default-open authorizer or superuser. **Recover:** contain, revoke, investigate as security incident.

### 26.9 Consumer group denied after ACL change
**Signal:** group authorization exception. **Diagnose:** principal/group ACL and GitOps diff. **Recover:** restore least-privilege Group Read.

### 26.10 NetworkPolicy blocks controller/broker traffic
**Signal:** KRaft/ISR instability. **Diagnose:** CNI deny logs and control-plane flow matrix. **Recover:** approved NetworkPolicy rollback.

### 26.11 Kubernetes Secret exposed to another tenant
**Signal:** unauthorized API Secret access. **Diagnose:** RoleBindings, Pod mounts, audit events. **Recover:** contain, rotate affected credentials and review access.

### 26.12 GitOps reconciliation reintroduces a removed ACL
**Signal:** privileged grant reappears. **Diagnose:** desired state and operator reconciliation. **Recover:** correct source of truth and verify effective ACLs.

## 27. Troubleshooting decision tree

```text
Client operation fails
  |
  +-- DNS fails? -> CoreDNS, Service, advertised host
  |
  +-- TCP fails? -> Service/EndpointSlice, NetworkPolicy, LB/firewall
  |
  +-- TLS fails? -> CA, SAN, expiry, client cert, protocol
  |
  +-- SASL fails? -> mechanism, username/password, token/JWKS
  |
  +-- Kafka authorization fails? -> principal, ACL, resource pattern
  |
  +-- Kafka request times out? -> ISR, leader, quotas, broker health
  |
  +-- Only one tenant affected? -> identity, ACL, namespace and rollout
  |
  +-- After change? -> compare GitOps diff, Secret version and timeline
```

Avoid inferring ACL correctness from network failures or successful authentication from a Kubernetes Secret existing.

## 28. Eight production runbooks

### Runbook A — Secure Kafka listener outage
1. Declare incident and identify affected listener/client cohorts.
2. Check DNS, TCP, TLS, SASL and advertised broker endpoints in order.
3. Capture Kafka/Strimzi readiness, quorum and ISR.
4. Restore last approved listener/client config through controlled change.
5. Verify all broker endpoints and synthetic produce/consume.
6. Document incident timeline, customer impact and prevention.

### Runbook B — TLS/CA certificate incident
1. Identify expiring or invalid certificate and issuer.
2. Review chain, SAN, CA ownership and client trust cohorts.
3. Use supported operator/PKI renewal or staged trust recovery.
4. Roll clients if required, without bypassing hostname validation.
5. Confirm TLS, principal, ACL and application SLO.
6. Improve expiry monitoring and rotation rehearsals.

### Runbook C — SCRAM credential rotation outage
1. Locate affected KafkaUser, Secret version and client rollout.
2. Confirm TLS path and SASL mechanism.
3. Coordinate approved credential recovery/parallel principal migration.
4. Reload clients safely and test authenticated operations.
5. Verify stale credentials rejected where required.
6. Record outage, rotation ordering and corrective action.

### Runbook D — OAuth/JWKS failure
1. Confirm token validation layer and affected IdP/client cohort.
2. Check issuer, audience, expiry, JWKS TLS and key IDs.
3. Restore IdP/JWKS availability or supported key cache behavior.
4. Keep signature/issuer/audience validation enforced.
5. Validate token refresh and Kafka ACLs.
6. Review IdP dependency SLO and incident response.

### Runbook E — Cross-tenant authorization incident
1. Treat unauthorized access as a security incident.
2. Contain offending principal/ACL and preserve audit logs.
3. Inspect default-open, wildcard/prefix and superuser permissions.
4. Revoke unsafe grants and rotate credentials if warranted.
5. Prove both directions of tenant isolation.
6. Coordinate security/privacy review and recertification.

### Runbook F — Kubernetes RBAC/NetworkPolicy incident
1. Identify affected namespace, Pod identity and flow.
2. Review Secret access, ServiceAccounts and CNI denies.
3. Restore approved network/control-plane flows.
4. Revoke excessive Kubernetes permissions and rotate exposed credentials.
5. Verify KRaft quorum, ISR and secure client access.
6. Document policy test gaps and prevention.

### Runbook G — GitOps authorization rollback
1. Identify offending KafkaUser/authorization PR.
2. Freeze additional ACL mutations and assess blast radius.
3. Restore reviewed least-privilege source of truth.
4. Wait for operator reconciliation and inspect effective ACLs.
5. Re-run positive/negative tenant tests.
6. Audit break-glass privileges and close incident.

### Runbook H — Security reliability game day
1. Obtain approval and capture baseline/SLOs.
2. Run TLS/SASL and tenant positive/negative tests.
3. Inject only client-side controlled failures.
4. Execute incident classification and recovery runbooks.
5. Verify no Secret leakage, no unplanned broker degradation.
6. Publish evidence, deviations and independent signoff.

## 29. Evidence package

```text
evidence-ch30/
  approval-and-scope.md
  context.txt
  baseline.txt
  kafka-crd.txt
  kafkauser-crd.txt
  listener-spec.txt
  listener-status.txt
  authorizer-spec.txt
  services.txt
  bootstrap-endpoints.txt
  networkpolicies.txt
  ca-metadata.txt
  tls-endpoint-validation.md
  sasl-principal-validation.md
  tenant-topics.txt
  tenant-a-allowed.md
  tenant-b-allowed.md
  cross-tenant-denied.md
  effective-acls-redacted.txt
  serviceaccounts.txt
  rbac.txt
  secret-metadata.txt
  credential-rotation.md
  ca-rotation-tabletop.md
  oauth-conditional-integration.md
  network-failure-drill.md
  auth-failure-drill.md
  acl-rollback-tabletop.md
  slos-and-observations.md
  preflight.txt
  incident-timeline.md
  security-review.md
  assessor-signoff.md
```

Evidence must distinguish **Pass**, **Fail**, **Blocked**, **Pending** and **Not Applicable**. Include time, tool/client versions, expected/actual behavior, impact, reviewer and redacted references. Never store client passwords, private keys, JWTs, raw Secret data or production payloads in public repositories.

## 30. Final 100-point assessment

| Domain | Points | Mandatory gate |
|---|---:|---|
| Architecture, threat model and change approval | 10 | Yes |
| Kubernetes DNS/Services/advertised broker path | 10 | Yes |
| TLS chain, SAN and certificate validity | 10 | Yes |
| Live SASL/mTLS authentication and principal mapping | 15 | Yes |
| Least-privilege ACL inventory and default-deny | 10 | Yes |
| Own-tenant positive produce/consume | 10 | Yes |
| Cross-tenant negative authorization tests | 15 | Yes |
| Kubernetes Secret/RBAC/NetworkPolicy isolation | 5 | Yes |
| Credential rotation and rollback readiness | 5 | Yes |
| Monitoring, runbooks, evidence and independent signoff | 10 | Yes |
| **Total** | **100** | |

**Pass threshold:** ≥85/100 **and all mandatory gates passed**. Any unauthorized cross-tenant read/write, secret exposure, disabled TLS verification or unapproved production mutation is an **automatic Fail**. OAuth, when within the approved deployment scope, requires an additional live integration gate (issuer, audience, JWKS, token refresh and failure behavior) before claiming production readiness.

## 31. Exit criteria and Part 06 handoff

- [ ] Kafka/Strimzi version compatibility confirmed.
- [ ] DNS and all advertised endpoints verified.
- [ ] TLS certificate chain and SAN validated.
- [ ] Secure client authentication and principal mapping demonstrated.
- [ ] Default-deny ACL behavior confirmed.
- [ ] Tenant A/B positive and negative tests passed.
- [ ] Kubernetes Secret/RBAC/NetworkPolicy controls reviewed.
- [ ] SCRAM or client certificate rotation recovery validated.
- [ ] OAuth live integration completed if applicable; otherwise clearly Pending/Out of scope.
- [ ] SLOs, alert routing, incident runbooks and rollback rehearsed.
- [ ] Independent security reviewer and Kafka SRE assessor signed off.

**Cleanup:** Remove only disposable tenant topics, KafkaUsers and test Pods after approval; retain sanitized evidence. Do not remove secure listeners, authorizers or operator-managed CA Secrets without a separate reviewed change.

**References:** [Apache Kafka Security](https://kafka.apache.org/documentation/#security), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/), [RFC 5802 SCRAM](https://www.rfc-editor.org/rfc/rfc5802), [RFC 7628 OAuth SASL](https://www.rfc-editor.org/rfc/rfc7628).

**Part 06 complete — 5/5 chapters published (026–030).**

**Next:** Chapter 031 — Kafka Performance Fundamentals, Throughput, Latency and Kubernetes Benchmarking.

---

**Verification boundary:** GitHub publication does not establish live execution, secure deployment, operational readiness or independent security approval. All live and security acceptance gates remain Pending until assessed against real evidence.
