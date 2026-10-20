# Chapter 028 — Kafka SASL Authentication, SCRAM Credentials, OAuth Integration and Kubernetes Identity Operations

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 06 — Networking, Security, TLS, SASL and ACLs (3/5)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft Kafka  
**Prerequisites:** Chapters 001–027, especially Kafka listeners, TLS, KafkaUser and Kubernetes Secrets  
**Audience:** Kafka SREs, DBREs, IAM/security engineers, platform engineers and application operators  
**Publication:** Published · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety boundary:** All hands-on work is for an approved, disposable Kubernetes cluster. Never enable SASL/PLAIN without TLS, expose SCRAM passwords or OAuth tokens in Git/logs, weaken certificate validation, change production broker authentication in place, or grant broad ACLs to make a failed test pass. Use parallel secure listeners and canary clients when planning migrations. Operator-managed Secrets, KafkaUsers and listeners must be changed through supported Strimzi APIs and reviewed GitOps.

## 1. Outcomes and acceptance contract

At the end, you should be able to:

1. Distinguish TLS transport security from SASL authentication and Kafka authorization.
2. Explain SCRAM-SHA-512 credential storage, challenge-response, rotation and client configuration.
3. Provision an operator-managed SCRAM KafkaUser and mount credentials safely in a Kubernetes Pod.
4. Validate SASL_SSL from a real Kafka client, including TLS hostname verification.
5. Explain OAUTHBEARER, token acquisition, audience/issuer validation, JWKS and token refresh.
6. Compare Strimzi OAuth integration with an externally managed identity provider, including release compatibility.
7. Audit Kubernetes Secret access, service accounts, projected identity and least-privilege boundaries.
8. Diagnose authentication failures without confusing them with network, TLS or ACL failures.
9. Design zero-downtime credential migration and incident runbooks.
10. Produce an evidence-backed 100-point operational security assessment.

**Publication is not proof of security acceptance.** Passing requires live SASL_SSL authentication, correct principal, least-privilege authorization and reviewed credential rotation evidence.

## 2. Authentication stack and trust boundaries

```text
 Application Pod (dedicated Kubernetes ServiceAccount)
       |
       +-- TLS trust bundle (server identity / hostname)
       +-- SCRAM password Secret OR OAuth token acquisition
       |
       v
 Kafka SASL_SSL bootstrap listener
       |
       +-- TLS server authentication / encryption
       +-- SASL SCRAM or OAUTHBEARER exchange
       +-- authenticated Kafka principal
       |
       v
 Kafka authorizer -> topic/group/cluster permissions
       |
       v
 Partition leaders / advertised broker endpoints

 Strimzi Operator -> Kafka CR / KafkaUser CR / Secrets
 IAM / OIDC provider -> tokens / issuer / JWKS / policies
 Kubernetes RBAC -> Secret read access / workload boundaries
```

**Invariants:** Every advertised broker endpoint must be reachable and use compatible TLS/SASL configuration. Authentication proves an identity; it does not authorize operations. Kubernetes ServiceAccount identity is not automatically a Kafka principal. OIDC tokens must be validated by the configured broker-side authentication integration.

## 3. Mechanism comparison

| Mechanism | Credential | Primary advantages | Operational risks |
|---|---|---|---|
| SASL/SCRAM-SHA-512 | Username + password | Native Kafka mechanism, Strimzi KafkaUser integration | Password lifecycle, Secret access, rotation |
| SASL/SCRAM-SHA-256 | Username + password | Native Kafka mechanism | Compatibility and policy constraints |
| SASL/PLAIN | Username + password | Simple compatibility | Password sent within SASL exchange; TLS mandatory |
| SASL/OAUTHBEARER | Signed bearer token | Federation, short-lived identity | IdP/JWKS reachability, refresh, audience/issuer validation |
| TLS client authentication | Client certificate/private key | Strong PKI identity | Certificate/CA rotation, key protection |

SCRAM-SHA-512 refers to the SCRAM hashing mechanism, **not TLS encryption**. SCRAM still needs TLS to protect metadata and traffic. OAuth integration details depend on Kafka, Strimzi and the chosen authentication plugin.

## 4. Architecture decisions before deployment

Record:

- Kafka version, Strimzi version and served `Kafka`/`KafkaUser` CRD versions.
- Existing listener names, ports, TLS modes and client cohorts.
- Whether broker authorization is enabled and which authorizer is supported.
- Whether the Strimzi User Operator manages users/ACLs in this cluster.
- Credential issuance and rotation owners.
- Whether the application supports credential reload without restart.
- NetworkPolicy, Kubernetes RBAC, namespace boundaries and Secret encryption.
- OIDC issuer, JWKS, token audience, identity mapping, clock skew and fallback behavior.
- Alerting for authentication errors, Secret rotation and token-refresh failures.

**Do not assume** an OAuth authentication stanza supported in one Strimzi release works in another; validate the installed CRD and official operator documentation.

## 5. Lab foundation and prerequisites

This chapter continues the isolated foundation:

```text
Namespace:        kafka-lab
Kafka cluster:    sre-kafka
CLI Pod:          kafka-cli
Legacy lab port:  sre-kafka-kafka-bootstrap:9092 (plaintext only, isolated)
Secure listener:  SASL_SSL on an approved new port, e.g. 9095
KafkaUser:        sre-scram-client-ch28
Topic:            sre-auth-ch28
Consumer group:   sre-auth-ch28-group
```

The `9095` listener is **illustrative**, not assumed to exist. Its final bootstrap address must come from `Kafka.status.listeners`. Production-like tests must use a real TLS listener and client credentials.

## 6. Lab 01 — Capture baseline and change authority

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch28
kubectl config current-context | tee evidence-ch28/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,svc -o wide \
  | tee evidence-ch28/platform-baseline.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}' \
  | tee evidence-ch28/listeners.txt
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch28/listener-status.txt
```

Create `evidence-ch28/change-approval.md` with change ticket, cluster owner, IAM owner, security reviewer, exact resources, abort criteria, rollback and authorized test identities.

**Acceptance:** healthy disposable cluster, explicit permission, complete listener inventory.

## 7. Lab 02 — Validate Strimzi CRD and operator support

```bash
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch28/kafka-crd-versions.txt
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch28/kafkauser-crd-versions.txt
kubectl explain kafka.spec.kafka.listeners --api-version=kafka.strimzi.io/v1 \
  | tee evidence-ch28/listener-schema.txt
kubectl explain kafkauser.spec.authentication --api-version=kafka.strimzi.io/v1 \
  | tee evidence-ch28/kafkauser-schema.txt
```

If `v1` is not served, adapt commands and manifests to the supported API version. Verify User Operator and Kafka authorizer capabilities before provisioning users or ACLs.

**Acceptance:** documented compatibility matrix; no unsupported API assumptions.

## 8. Lab 03 — Design a parallel TLS + SCRAM listener

Illustrative fragment to merge into the **existing reviewed Kafka CR**, not a standalone resource:

```yaml
spec:
  kafka:
    listeners:
      - name: scramlab
        port: 9095
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
```

Keep all existing listeners and unrelated Kafka CR settings. Check port availability, listener naming constraints and the installed Strimzi schema.

```bash
kubectl apply --dry-run=server -f reviewed-kafka-ch28.yaml
# Apply only through the approved GitOps reconciliation workflow.
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch28/scram-listener-status.txt
```

**Acceptance:** secure listener Ready, old client traffic unaffected, no degraded ISR or KRaft quorum. If a full reviewed CR is unavailable, this gate remains Pending.

## 9. Lab 04 — Provision an operator-managed SCRAM user

Create `kafkauser-scram-ch28.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: sre-scram-client-ch28
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
          name: sre-auth-ch28
          patternType: literal
        operations:
          - Read
          - Write
          - Describe
        host: "*"
      - resource:
          type: group
          name: sre-auth-ch28-group
          patternType: literal
        operations:
          - Read
        host: "*"
```

**Compatibility guard:** `spec.authorization.type: simple` requires compatible Strimzi User Operator and Kafka authorizer configuration. If the cluster uses another authorization integration, adapt to that integration; do not claim these ACLs were enforced.

```bash
kubectl apply --dry-run=server -f kafkauser-scram-ch28.yaml
kubectl apply -f kafkauser-scram-ch28.yaml
kubectl -n kafka-lab get kafkauser sre-scram-client-ch28 \
  -o jsonpath='{.status.conditions}{"\n"}' \
  | tee evidence-ch28/kafkauser-status.txt
```

**Acceptance:** KafkaUser reconciles, username/identity and intended topic/group access documented.

## 10. Lab 05 — Inspect Secret metadata without exposing passwords

```bash
kubectl -n kafka-lab get secret sre-scram-client-ch28 \
  -o custom-columns=NAME:.metadata.name,TYPE:.type \
  | tee evidence-ch28/secret-metadata.txt
kubectl -n kafka-lab get secret sre-scram-client-ch28 \
  -o go-template='{{range $k,$v := .data}}{{printf "%s\n" $k}}{{end}}' \
  | tee evidence-ch28/secret-key-names.txt
```

A Strimzi SCRAM KafkaUser Secret commonly contains `password` and may contain additional connection metadata. Do not print `.data.password` or decode it into terminal logs. Base64 is not encryption.

**Acceptance:** Secret owner, access policy, rotation owner and resourceVersion recorded without credential values.

## 11. Lab 06 — Create the disposable authentication topic

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-auth-ch28
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    cleanup.policy: delete
    retention.ms: 3600000
```

Save as `kafkatopic-auth-ch28.yaml` and validate:

```bash
kubectl apply --dry-run=server -f kafkatopic-auth-ch28.yaml
kubectl apply -f kafkatopic-auth-ch28.yaml
kubectl -n kafka-lab get kafkatopic sre-auth-ch28 -o yaml \
  | tee evidence-ch28/topic-status.yaml
```

**Acceptance:** topic Ready, RF3/minISR2 and no unauthorized topic creation by application principals.

## 12. Lab 07 — Mount credentials in a restricted client Pod

Use an approved, pinned Kafka client image and a dedicated ServiceAccount. Mount the generated KafkaUser Secret and the correct cluster CA certificate Secret as **read-only** volumes:

```yaml
# Pod template excerpt; not a complete manifest.
spec:
  serviceAccountName: approved-sre-kafka-client
  containers:
    - name: client
      image: <APPROVED_IMAGE_DIGEST>
      volumeMounts:
        - name: scram-identity
          mountPath: /etc/kafka/scram
          readOnly: true
        - name: kafka-ca
          mountPath: /etc/kafka/ca
          readOnly: true
  volumes:
    - name: scram-identity
      secret:
        secretName: sre-scram-client-ch28
        defaultMode: 0440
    - name: kafka-ca
      secret:
        secretName: sre-kafka-cluster-ca-cert
        defaultMode: 0444
```

Validate actual CA Secret name and Pod file permissions for the non-root UID. Do not give the application ServiceAccount Kubernetes Secret-list permission: a Pod can mount a referenced Secret without the application needing to call the Kubernetes API to read it.

**Acceptance:** only the intended Pod accesses the credential, and its Secret is not injected into logs, shell arguments or public artifacts.

## 13. Lab 08 — Build SASL_SSL client configuration safely

Example `client.properties`:

```properties
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
ssl.endpoint.identification.algorithm=https
ssl.truststore.type=PEM
ssl.truststore.certificates=-----BEGIN CERTIFICATE-----
# This placeholder is NOT valid as written; provide a real approved CA PEM.
# The full certificate must be inserted by a secure init process.
-----END CERTIFICATE-----
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username="sre-scram-client-ch28" password="<INJECTED_AT_RUNTIME>";
```

**Do not commit this template as a working config.** In production-like labs, use an approved startup/init process to read the mounted CA and password, generate `client.properties` in a restricted in-memory or ephemeral volume with `0600` permissions, and avoid `set -x`, `env` dumps and process arguments. Kafka clients can use a PEM truststore configuration or a supported JKS/PKCS#12 truststore; verify the installed client version.

The **actual bootstrap address** must come from `Kafka.status.listeners` for `scramlab`, not from the plaintext 9092 foundation.

## 14. Lab 09 — Validate SCRAM authentication end to end

Run from the approved client Pod after securely generating `/etc/kafka/client.properties`:

```bash
/opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server "$SASL_BOOTSTRAP" \
  --command-config /etc/kafka/client.properties \
  --describe --topic sre-auth-ch28
```

Then use a producer with `acks=all` and a consumer in `sre-auth-ch28-group`. Record the authenticated principal using broker audit/authentication logs or an approved identity introspection method; never infer it solely from the Secret name.

**Acceptance:** TLS hostname verified, SCRAM authentication succeeds, metadata/produce/consume work, and topic/group authorization is enforced.

## 15. Lab 10 — Negative authentication and authorization tests

Use a disposable client and short bounded timeouts:

1. Wrong password, correct username → SASL authentication failure.
2. Wrong username → SASL authentication failure.
3. Wrong CA → TLS trust failure **before** SASL.
4. Correct SCRAM identity, unauthorized topic → authorization denial.
5. Correct identity and allowed topic → success.

Do not use real production passwords or log the bad password. Distinguish `SaslAuthenticationException`, TLS handshake exceptions and `TopicAuthorizationException`.

**Acceptance:** five distinct expected outcomes with sanitized logs; no ACL broadening.

## 16. Lab 11 — SCRAM password rotation and client reload

1. Record existing KafkaUser and Secret metadata, not the password.
2. Confirm supported Strimzi password rotation behavior for the installed release.
3. Prepare an approved credential change and client reload plan.
4. Rotate the **disposable** KafkaUser credential through supported operator mechanisms.
5. Ensure Secret propagation and application reload/restart are coordinated.
6. Validate new credential authentication, producer acknowledgments and consumer replay.
7. Revoke stale credential use and document overlap or interruption.
8. Roll back only through the documented supported recovery path.

**Critical:** a SCRAM password update may invalidate the old credential before all clients reload. Do not promise seamless overlap unless the chosen identity design explicitly supports it. Consider parallel principals and staged client migration for production.

**Acceptance:** rotation timing, actual authenticated reconnection, no exposed credential, measured service impact.

## 17. Lab 12 — OAuth/OIDC architecture and compatibility review

Kafka's `OAUTHBEARER` mechanism is standardized, but broker-side token validation and Strimzi listener OAuth support are **integration-specific**. Validate the chosen plugin/Strimzi release and IdP.

Required decisions:

| Parameter | Validation |
|---|---|
| Issuer | Exact trusted `iss`, no wildcard trust |
| Audience | Kafka-specific `aud` enforced |
| JWKS | Trusted HTTPS endpoint, cache, key rotation |
| Signature | Approved algorithms and key IDs |
| Expiry | `exp`, `nbf`, clock skew |
| Principal mapping | Stable subject/client ID and tenant boundary |
| Token acquisition | Workload identity or confidential client flow |
| Token refresh | Before expiry, with bounded retry/backoff |
| Authorization | Kafka ACL/RBAC mapping |
| Failure mode | IdP/JWKS outage, cache expiry, fail closed |
| Audit | Token metadata only, never raw token |
| Revocation | Document short-lived-token limits and IdP behavior |

**Acceptance:** signed compatibility and threat-model review; OAuth live integration remains Pending until a real supported IdP and broker plugin are available.

## 18. Lab 13 — OAuth listener configuration design

**Illustrative only**; do not apply without validating installed Strimzi release:

```yaml
spec:
  kafka:
    listeners:
      - name: oauthlab
        port: 9096
        type: internal
        tls: true
        authentication:
          type: oauth
          validIssuerUri: https://idp.example.invalid/realms/kafka-lab
          jwksEndpointUri: https://idp.example.invalid/realms/kafka-lab/protocol/openid-connect/certs
          userNameClaim: preferred_username
```

The example uses `.invalid` to prevent accidental reliance on a real IdP. Exact fields, additional issuer/audience requirements and plugin configuration vary by Strimzi version. Do not set `checkIssuer: false` or disable signature validation to make a lab pass.

**Acceptance:** validated schema and design; deployment only after supported IdP, certificates, audience enforcement and approval.

## 19. Lab 14 — OAuth token lifecycle and failure tabletop

Scenario sequence:

1. Client obtains short-lived access token through an approved identity flow.
2. Client connects over TLS and performs SASL/OAUTHBEARER.
3. Broker validates signature, issuer, audience and expiration.
4. Broker maps subject to Kafka principal.
5. Kafka authorizer checks topic/group permission.
6. Client refreshes token before expiry.
7. IdP/JWKS becomes unavailable; assess cached-key behavior and expiry.
8. Rotate signing key; validate JWKS refresh and uninterrupted authorized access.

Do not print tokens, JWT claims containing personal data, client secrets or signing keys into evidence.

**Acceptance:** timeline, retry policy, security decision and measured or explicitly Pending integration evidence.

## 20. Lab 15 — Kubernetes workload identity and Secret RBAC

Compare:

- Mounted SCRAM Secret with restricted Pod access.
- OAuth client credentials stored in a Secret (higher rotation burden).
- Federated workload identity where the IdP/cloud supports it.
- Kubernetes ServiceAccount token projection with intended audience and expiry, **only if the IdP and Kafka integration explicitly trust/exchange it**.

```bash
kubectl -n kafka-lab get serviceaccounts \
  | tee evidence-ch28/serviceaccounts.txt
kubectl -n kafka-lab get role,rolebinding -o wide \
  | tee evidence-ch28/rbac-inventory.txt
kubectl -n kafka-lab auth can-i get secrets \
  --as=system:serviceaccount:kafka-lab:approved-sre-kafka-client \
  | tee evidence-ch28/client-secret-rbac.txt
```

The impersonation check requires authorization to impersonate; a forbidden response is **not** a proof of denied Secret access. Use a permitted RBAC review if necessary.

**Acceptance:** least-privilege identity map, token audience design, no broad Secret-list privileges, approved rotation ownership.

## 21. Lab 16 — Authentication monitoring and SLOs

Monitor:

- SASL authentication success/failure by listener and principal class.
- TLS handshake errors separately from SASL errors.
- ACL authorization denials and unusual permission changes.
- SCRAM Secret rotation age, failed User Operator reconciliations.
- OAuth token refresh failures, expiration headroom, JWKS fetch errors.
- Kafka request latency, producer retries, consumer lag and ISR.
- Broker listener availability and KRaft quorum health.

Use actual metrics available in the installed Kafka/Strimzi exporters; avoid inventing universal metric names. Define alert severity, owner, runbook, false-positive handling and secret-safe log retention.

**Acceptance:** dashboards/alert rules with validated metric sources and tested routing, or Pending.

## 22. Lab 17 — Read-only automated identity preflight

Save `verify-ch28.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BIN=/opt/kafka/bin
BS=sre-kafka-kafka-bootstrap:9092

echo '[1/8] Context and Kafka readiness'
kubectl config current-context
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[2/8] Listener inventory'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[3/8] KafkaUser CRD API versions'
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'

echo '[4/8] KafkaUser presence (optional)'
if kubectl -n "$NS" get kafkauser sre-scram-client-ch28 >/dev/null 2>&1; then
  kubectl -n "$NS" get kafkauser sre-scram-client-ch28 \
    -o jsonpath='{.status.conditions}{"\n"}'
else
  echo 'PENDING: disposable SCRAM KafkaUser not created'
fi

echo '[5/8] Secret metadata only (optional)'
if kubectl -n "$NS" get secret sre-scram-client-ch28 >/dev/null 2>&1; then
  kubectl -n "$NS" get secret sre-scram-client-ch28 \
    -o custom-columns=NAME:.metadata.name,TYPE:.type
else
  echo 'PENDING: SCRAM Secret not created'
fi

echo '[6/8] Kubernetes service accounts'
kubectl -n "$NS" get serviceaccounts

echo '[7/8] Broker metadata quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[8/8] Baseline plaintext metadata only'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --list

echo 'PASS: read-only identity inventory preflight.'
echo 'NOT PROVEN: SASL_SSL, SCRAM authentication, ACL enforcement, rotation or OAuth integration.'
```

```bash
chmod +x verify-ch28.sh
./verify-ch28.sh | tee evidence-ch28/preflight.txt
```

**Limitations:** successful preflight proves neither secure authentication nor token validity. All execution gates require real secure client tests.

## 23. Twelve failure scenarios

### 23.1 SCRAM password changed before clients reload
**Signal:** sudden `SaslAuthenticationException`. **Check:** Secret version, client rollout, User Operator events. **Recover:** supported credential restoration or coordinated replacement.

### 23.2 SASL mechanism mismatch
**Signal:** broker rejects requested mechanism. **Check:** listener auth type and `sasl.mechanism`. **Recover:** correct client mechanism; do not enable weaker broker modes.

### 23.3 SASL_SSL client connects to plaintext listener
**Signal:** disconnect/handshake errors. **Check:** bootstrap port and `security.protocol`. **Recover:** use secure listener address.

### 23.4 Wrong CA bundle
**Signal:** TLS trust failure before SASL. **Check:** broker CA and client truststore. **Recover:** distribute correct approved CA.

### 23.5 SCRAM succeeds but ACL denies
**Signal:** topic/group authorization exception. **Check:** principal and resource ACL. **Recover:** least-privilege grant after owner approval.

### 23.6 OAuth token expired
**Signal:** authentication failure after `exp`. **Check:** refresh schedule and clock skew. **Recover:** renew token using approved flow.

### 23.7 OAuth audience mismatch
**Signal:** token rejected despite valid signature. **Check:** exact Kafka audience. **Recover:** correct IdP/client audience configuration.

### 23.8 OAuth issuer mismatch
**Signal:** token rejected. **Check:** `iss`, broker trusted issuer. **Recover:** fix approved issuer trust, never disable issuer validation.

### 23.9 JWKS endpoint unavailable
**Signal:** token validation errors or cached-key limitations. **Check:** DNS, TLS, network egress, cache. **Recover:** restore IdP/JWKS connectivity with fail-closed policy.

### 23.10 IdP signing-key rotation breaks validation
**Signal:** unknown `kid`, signature validation failure. **Check:** JWKS refresh and rotation overlap. **Recover:** supported key publication/refresh.

### 23.11 Kubernetes Secret leaked
**Signal:** unauthorized access audit. **Check:** RBAC, mounts, CI logs. **Recover:** revoke, rotate, investigate and report.

### 23.12 User Operator reconciliation stalled
**Signal:** KafkaUser NotReady, missing credentials/ACLs. **Check:** operator events, CRD compatibility, authorizer. **Recover:** restore operator reconciliation and verify effective broker identity.

## 24. Troubleshooting matrix

| Symptom | Layer | Primary evidence | Owner |
|---|---|---|---|
| DNS failure | Network | Resolver/Service | Platform |
| TLS handshake failure | TLS | Chain/SAN/expiry | PKI |
| SCRAM auth failure | SASL | Mechanism, Secret version | Kafka SRE |
| OAuth token rejection | OIDC | Issuer/audience/JWKS/expiry | IAM |
| Topic authorization failure | ACL | Principal/resource | Kafka security |
| Consumer group denied | ACL | Group permissions | Kafka security |
| Secret not updated in Pod | Kubernetes | Secret version/Pod reload | App SRE |
| KafkaUser NotReady | Strimzi | User Operator events | Kafka platform |
| Authentication spike during rollout | Change | Cohort timeline | Incident command |
| Token refresh storms | Client/IdP | Retry policy and IdP limits | IAM/SRE |

## 25. Eight production runbooks

### Runbook A — SCRAM authentication outage
1. Identify affected listeners, users and client cohorts.
2. Confirm TLS/port health before diagnosing SASL.
3. Compare KafkaUser and Secret version with client reload.
4. Restore approved credentials without exposing them.
5. Verify authenticated principal, ACL and application health.
6. Record timeline and prevention.

### Runbook B — SCRAM password rotation
1. Inventory clients and current credential lifecycle.
2. Approve change, rollback and reload sequence.
3. Use supported operator-managed rotation.
4. Roll/reload clients in controlled cohorts.
5. Validate produce/consume and stale credential rejection.
6. Publish rotation evidence.

### Runbook C — OAuth token validation failure
1. Capture sanitized error class and affected principal cohort.
2. Validate TLS, issuer, audience, expiration and signature.
3. Check JWKS endpoint health and cache/rotation behavior.
4. Restore trusted IdP configuration; never bypass validation.
5. Test token refresh and Kafka authorization.
6. Review alerts and IdP resilience.

### Runbook D — IdP/JWKS outage
1. Declare incident scope and token TTL impact.
2. Assess cached keys and time-to-expiry.
3. Restore network/IdP availability and bounded client retries.
4. Preserve fail-closed policy and avoid emergency wildcard trust.
5. Verify refreshed tokens and Kafka service recovery.
6. Document dependency SLO and DR actions.

### Runbook E — Kubernetes Secret exposure
1. Contain unauthorized access and preserve audit records.
2. Determine affected credentials and consumers.
3. Revoke access and rotate impacted SCRAM/client secrets.
4. Review CI logs, Pod mounts and RBAC.
5. Validate authentication/authorization after remediation.
6. Complete security incident review.

### Runbook F — KafkaUser reconciliation failure
1. Inspect KafkaUser conditions and operator health.
2. Validate CRD version and authorization integration.
3. Check Secret ownership and user reconciliation logs.
4. Repair supported configuration through GitOps.
5. Verify actual broker authentication and ACLs.
6. Record operator and platform follow-ups.

### Runbook G — Secure listener migration
1. Inventory current client endpoints and security modes.
2. Deploy parallel SASL_SSL listener after approval.
3. Canary a dedicated least-privilege client.
4. Migrate cohorts with retries, latency and auth monitoring.
5. Roll back clients on unexpected errors.
6. Retire legacy listener only after verified zero dependencies.

### Runbook H — Authentication game day
1. Confirm disposable cluster and change authority.
2. Capture healthy baseline and redaction controls.
3. Exercise wrong password, wrong CA and unauthorized topic.
4. Test alert classification and incident routing.
5. Restore successful client authentication and Kafka health.
6. Publish evidence and independent signoff.

## 26. Evidence package

```text
evidence-ch28/
  change-approval.md
  context.txt
  platform-baseline.txt
  listeners.txt
  listener-status.txt
  kafka-crd-versions.txt
  kafkauser-crd-versions.txt
  listener-schema.txt
  kafkauser-schema.txt
  scram-listener-status.txt
  kafkauser-status.txt
  secret-metadata.txt
  secret-key-names.txt
  topic-status.yaml
  client-security-review.md
  scram-authentication.md
  scram-negative-tests.md
  scram-rotation.md
  oauth-compatibility.md
  oauth-threat-model.md
  oauth-token-lifecycle.md
  serviceaccounts.txt
  rbac-inventory.txt
  client-secret-rbac.txt
  authentication-alerts.md
  preflight.txt
  incident-review.md
  security-review.md
  assessor-signoff.md
```

For every gate record timestamp, Kafka/Strimzi versions, expected/actual outcome, redacted evidence, reviewer and Pass/Fail/Pending. Never include raw SCRAM passwords, JAAS files containing secrets, OAuth access tokens, private keys or Kubernetes Secret values.

## 27. Assessment — 100 points

| Domain | Points | Acceptance |
|---|---:|---|
| Authentication architecture and threat model | 10 | Reviewed trust boundaries |
| Strimzi listener/CRD compatibility | 10 | Validated full CR |
| SCRAM KafkaUser and Secret governance | 10 | Reconciled user, safe metadata |
| Live SASL_SSL SCRAM handshake | 15 | Real authenticated client |
| Least-privilege topic/group authorization | 10 | Allowed and denied operations |
| SCRAM rotation and client reload | 10 | Measured live recovery |
| OAuth issuer/audience/JWKS design | 10 | Compatibility/security review |
| OAuth token lifecycle and outage tabletop | 5 | Signed analysis |
| Kubernetes identity, RBAC and alerting | 10 | Verified controls |
| Runbooks, negative tests and independent signoff | 10 | Evidence and assessor |
| **Total** | **100** | |

**Pass:** ≥85/100 with no critical security failures, verified SASL_SSL, correct principal and ACL enforcement. If OAuth is in production scope, live OIDC/JWKS integration and token-refresh testing are mandatory additional acceptance gates. A tabletop cannot substitute for live authentication evidence.

## 28. Cleanup and next chapter

After approval, delete only the disposable KafkaTopic/KafkaUser and owned client Pods. Removing a SASL listener is a separate reviewed Kafka CR/GitOps change and must wait until no clients depend on it. Preserve redacted evidence; destroy local credential copies through approved procedures. Do not delete Strimzi operator or broker Secrets manually.

**References:** [Apache Kafka security](https://kafka.apache.org/documentation/#security), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [RFC 5802 — SCRAM](https://www.rfc-editor.org/rfc/rfc5802), [RFC 7628 — SASL OAuth](https://www.rfc-editor.org/rfc/rfc7628), [OpenID Connect](https://openid.net/developers/how-connect-works/).

**Next:** Chapter 029 — Kafka ACLs, Authorization, Multi-Tenant Isolation and Kubernetes Security Governance.

---

**Verification boundary:** GitHub publication confirms document availability only. SASL_SSL, SCRAM rotation, OAuth integration, ACL enforcement and independent security review remain Pending until live evidence and signoff are recorded.
