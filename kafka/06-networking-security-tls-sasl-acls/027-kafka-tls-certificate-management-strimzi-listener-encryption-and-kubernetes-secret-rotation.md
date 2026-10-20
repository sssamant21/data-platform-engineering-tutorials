# Chapter 027 — Kafka TLS, Certificate Management, Strimzi Listener Encryption and Kubernetes Secret Rotation

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 06 — Networking, Security, TLS, SASL and ACLs (2/5)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft Kafka  
**Prerequisites:** Chapters 001–026; Kubernetes Secrets, DNS, PKI and Kafka listener fundamentals  
**Audience:** Kafka SREs, DBREs, Kubernetes platform engineers, security and PKI operators  
**Publication:** Published · **Live lab execution:** Pending · **Independent security review:** Pending

> **Safety boundary:** Never disable TLS verification, publish private keys, rotate production CAs without a compatibility and rollback plan, edit operator-managed certificates by hand, or switch a production listener from plaintext to TLS without coordinating all clients. The tutorial foundation's port 9092 is an isolated plaintext listener; this chapter adds a **separate lab TLS listener** only after verifying the installed Strimzi version and change approval. Treat any generated Secret or client keystore as sensitive and keep it out of Git and shared evidence.

## 1. Learning objectives

After this chapter, you can:

1. Explain TLS server authentication, mutual TLS (mTLS), CA chains, SANs, truststores and certificate expiry.
2. Distinguish encryption, Kafka principal authentication and ACL authorization.
3. Configure a supported Strimzi TLS listener through the Kafka CR and GitOps.
4. Discover Strimzi-generated CA and client trust material safely.
5. Validate server identity and hostname verification from a Kubernetes client Pod.
6. Provision and rotate client certificates with approved Strimzi KafkaUser mechanisms.
7. Plan CA rotation, certificate renewal, secret propagation and rollback.
8. Diagnose PKIX, expired certificate, hostname mismatch and client-auth failures.
9. Implement monitoring, security gates, production runbooks and evidence-based acceptance.

## 2. Reference architecture

```text
       Approved Kafka client Pod
           |   trusted CA certificate
           |   optional client cert + private key
           v
       Kafka TLS bootstrap Service
           |  TLS handshake / server certificate SAN
           v
     Strimzi-managed Kafka brokers (KRaft)
       |           |            |
       +-- broker TLS identities +
       |           |
       +-- Kafka authentication principal
                   |
             Kafka authorization / ACLs

 Strimzi Cluster Operator -> Kafka CR / KafkaUser CR
        |                       |
        +-- CA and certificate management
        +-- Kubernetes Secrets (RBAC restricted)
        +-- supported rolling reconciliation

 GitOps change review -> policy -> controlled rollout -> verification
```

**Encryption is not authorization.** A TLS listener can encrypt traffic without authenticating clients by certificate. Mutual TLS verifies a client certificate and maps an identity to a Kafka principal; the principal still needs appropriate authorization to access topics/groups.

## 3. TLS handshake and trust semantics

| Layer | Question | Failure example |
|---|---|---|
| DNS | Can client resolve bootstrap and advertised broker names? | Unknown host |
| TCP | Can client reach listener port? | Connection timeout |
| TLS version/cipher | Do endpoints negotiate a supported protocol? | Handshake failure |
| Server chain | Is broker certificate signed by a trusted CA? | PKIX path building failed |
| Hostname | Does SAN match the advertised broker DNS? | No subject alternative DNS name |
| Client identity | Does listener require a valid client certificate? | Bad certificate / authentication failed |
| Kafka principal | Is identity mapped to intended principal? | Unexpected user identity |
| ACLs | Can principal perform requested operation? | TopicAuthorizationException |

A successful TLS handshake is **not** proof that Kafka metadata discovery, all broker endpoints or topic authorization works.

## 4. Strimzi certificate ownership and rotation

Strimzi commonly manages cluster CA and client CA certificates through operator-managed Kubernetes Secrets. Exact Secret names, key names, renewal thresholds and CA rotation behavior depend on the installed Strimzi release and Kafka CR configuration. Inspect the actual resources and documentation before use.

Do **not** patch CA Secrets directly or manually restart every broker. A CA renewal/rotation can require overlapping trust periods and coordinated client updates. Distinguish:

- **Broker certificate renewal:** leaf certificate replacement, usually preserving CA trust.
- **Client certificate renewal:** identity credential replacement, with client reload/restart behavior.
- **CA certificate renewal:** new CA certificate using an existing key (where supported).
- **CA key replacement:** trust-anchor change; much higher risk requiring staged client trust.
- **External CA / custom listener certificate:** operator-supported configuration and external PKI ownership.

Certificate automation must account for applications that load truststores only at startup.

## 5. TLS listener choices and security model

A supported Strimzi internal listener can provide server TLS with no client certificate authentication, or mutual TLS with `authentication.type: tls` when supported. Production should enforce approved authentication, authorization and network boundaries.

**Illustrative Kafka CR fragment — NOT a standalone manifest:**

```yaml
spec:
  kafka:
    listeners:
      - name: tlslab
        port: 9094
        type: internal
        tls: true
        authentication:
          type: tls
```

Apply only after confirming `9094` is unused, `tlslab` meets Strimzi listener naming constraints, `KafkaUser` TLS auth is supported, and the cluster has adequate capacity for a controlled reconciliation. The existing lab listener on 9092 remains unchanged.

## 6. Preflight: identify the exact operator and CRD capabilities

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
mkdir -p evidence-ch27
kubectl config current-context | tee evidence-ch27/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,svc -o wide \
  | tee evidence-ch27/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch27/kafka-crd-versions.txt
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}' \
  | tee evidence-ch27/kafkauser-crd-versions.txt
```

**Acceptance:** approved disposable cluster, compatible Strimzi/Kafka versions, CRD API versions and baseline Ready status. **Stop** if the cluster is shared or the change is not approved.

## 7. Lab 01 — Inventory TLS listeners without exposing secrets

```bash
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}' \
  | tee evidence-ch27/listeners.txt
kubectl -n kafka-lab get svc -l strimzi.io/cluster=sre-kafka -o wide \
  | tee evidence-ch27/services.txt
kubectl -n kafka-lab get kafka sre-kafka -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch27/listener-status.txt
```

Map listener name, port, TLS enabled, authentication mode, bootstrap address and client network. Do not assume `9093` is always TLS or that listener names imply authentication.

**Acceptance:** actual listener inventory and trust-boundary diagram.

## 8. Lab 02 — Identify certificate Secrets safely

```bash
kubectl -n kafka-lab get secrets \
  -l strimzi.io/cluster=sre-kafka \
  -o custom-columns=NAME:.metadata.name,TYPE:.type \
  | tee evidence-ch27/secret-inventory.txt
```

Some Strimzi Secrets may not have the expected label. Cross-check the documented cluster CA Secret name using metadata only. **Do not** run `kubectl get secret -o yaml` into evidence, because it includes base64-encoded private keys and credentials. Base64 is not encryption.

**Acceptance:** Secret ownership, certificate purpose, access policy and renewal owner documented.

## 9. Lab 03 — Review server certificate metadata

After confirming the correct CA **certificate-only** key in the approved Secret:

```bash
# Certificate-only export to a restricted local directory;
# verify key name and Secret name from the installed Strimzi release.
umask 077
mkdir -p .secrets-ch27
kubectl -n kafka-lab get secret sre-kafka-cluster-ca-cert \
  -o jsonpath='{.data.ca\.crt}' \
  | base64 -d > .secrets-ch27/cluster-ca.crt
openssl x509 -in .secrets-ch27/cluster-ca.crt \
  -noout -subject -issuer -dates -fingerprint -sha256 \
  | tee evidence-ch27/cluster-ca-metadata.txt
```

This exports a **public CA certificate**, not a private key. If the Secret or key is absent, stop and inspect the installed Strimzi docs. Avoid checking even certificate bundles into Git without policy review; certificate metadata is usually sufficient evidence.

**Acceptance:** CA subject, issuer, validity dates, fingerprint and owner recorded.

## 10. Lab 04 — Create a reviewed TLS listener change

Create a GitOps pull request adding the `tlslab` internal TLS listener to the existing Kafka CR. Preserve all existing listeners and unrelated Kafka CR fields.

Preflight with server-side dry run on the **full reviewed Kafka CR**:

```bash
kubectl apply --dry-run=server -f reviewed-kafka-ch27.yaml
```

Use the repository's established reconciliation workflow. After approval:

```bash
kubectl -n kafka-lab wait kafka/sre-kafka \
  --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.status.listeners}{"\n"}' \
  | tee evidence-ch27/tls-listener-status.txt
```

**Acceptance:** a new TLS listener appears in status; no regression to existing clients; broker quorum/ISR remain healthy. If a full CR manifest is unavailable, mark the change Pending rather than applying the fragment.

## 11. Lab 05 — Create a least-privilege mTLS KafkaUser

**Illustrative CR, subject to installed CRD and user-operator support:**

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaUser
metadata:
  name: sre-tls-client-ch27
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
          name: sre-tls-ch27
          patternType: literal
        operations:
          - Read
          - Write
          - Describe
        host: "*"
      - resource:
          type: group
          name: sre-tls-ch27-group
          patternType: literal
        operations:
          - Read
        host: "*"
```

**Critical:** the `KafkaUser.spec.authorization` field is valid only when the cluster's Kafka authorization mechanism and Strimzi User Operator support it. Kafka broker authorization must be configured consistently. The example scopes ACL resources, but `host: "*"` is not a network restriction; apply NetworkPolicies and identity governance. Some clusters use a different authorizer, so do not apply until schema and policy are verified.

**Acceptance:** user CR reconciles and client certificate Secret is created through the operator. If authorization is not configured, mark the ACL test Pending and do not claim least-privilege enforcement.

## 12. Lab 06 — Certificate chain and client identity review

For the generated KafkaUser Secret, inspect metadata and key names without printing data:

```bash
kubectl -n kafka-lab get secret sre-tls-client-ch27 \
  -o go-template='{{range $k,$v := .data}}{{printf "%s\n" $k}}{{end}}' \
  | tee evidence-ch27/client-secret-key-names.txt
```

Typical Strimzi-generated KafkaUser TLS Secrets may include `user.crt`, `user.key`, `user.p12`, `user.password` and `ca.crt`, depending on release and configuration. Treat all private-key and password values as confidential. Extract only to an approved restricted workspace or mount the Secret directly into a disposable client Pod.

**Acceptance:** client certificate issuer, validity, expected principal and private-key access controls reviewed; no secret contents in Git or logs.

## 13. Lab 07 — Mount client identity into an approved Pod

**Pod excerpt (illustrative, not a complete runnable Pod):**

```yaml
spec:
  serviceAccountName: approved-kafka-client
  containers:
    - name: kafka-client
      image: <PINNED_APPROVED_KAFKA_CLIENT_IMAGE>
      volumeMounts:
        - name: kafka-user-identity
          mountPath: /etc/kafka/client-identity
          readOnly: true
  volumes:
    - name: kafka-user-identity
      secret:
        secretName: sre-tls-client-ch27
        defaultMode: 0400
```

Use an approved immutable image digest, restricted service account, non-root user, filesystem permissions compatible with the Pod security context and scoped network egress. **Never paste client passwords into shell command arguments** because they may appear in process listings or logs.

**Acceptance:** Pod can read only its mounted client identity; no broad namespace Secret-list permissions.

## 14. Lab 08 — Validate TLS with Kafka CLI

Kafka client configuration for a PKCS#12 keystore/truststore is release-dependent. The client must use `security.protocol=SSL` and appropriate truststore/keystore paths and passwords.

**Illustrative client properties template (not complete until provisioned):**

```properties
security.protocol=SSL
ssl.endpoint.identification.algorithm=https
ssl.truststore.type=PKCS12
ssl.truststore.location=/etc/kafka/client-identity/ca.p12
ssl.keystore.type=PKCS12
ssl.keystore.location=/etc/kafka/client-identity/user.p12
# Passwords are injected by approved Secret mechanisms, never committed.
```

Confirm actual Secret keys and truststore format; a PEM CA file requires the supported PEM client configuration rather than a nonexistent `ca.p12`. Use the `bootstrapServers` address reported by the Kafka CR listener status.

```bash
# Run inside an approved Pod that already has a valid client.properties:
# /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$TLS_BOOTSTRAP" \
#   --command-config /etc/kafka/client.properties --list
```

**Acceptance:** successful Kafka metadata operation using TLS, verified server hostname and authenticated principal. This gate is **Pending** until a real supported client properties file is provisioned.

## 15. Lab 09 — Verify server hostname identity

Use an approved diagnostic Pod with `openssl` and access to the CA certificate. When the listener supports direct TLS negotiation:

```bash
# Example only; replace DNS and port from actual listener status.
# openssl s_client -connect kafka-bootstrap.example.internal:9094 \
#   -servername kafka-bootstrap.example.internal \
#   -CAfile /etc/kafka/ca.crt -verify_return_error \
#   -verify_hostname kafka-bootstrap.example.internal
```

Inspect SANs, validity and certificate chain. For Kafka mTLS, an OpenSSL handshake without a client certificate may fail by design; that does not prove server TLS is broken. Prefer a fully configured Kafka client to validate the end-to-end path.

**Acceptance:** verified SAN for bootstrap **and each advertised broker endpoint**; no disabling hostname verification.

## 16. Lab 10 — TLS negative tests in an isolated client

Run controlled tests with an approved disposable client Pod:

1. Wrong CA trust bundle → expect PKIX/unknown issuer failure.
2. Correct CA, wrong hostname → expect SAN mismatch.
3. Expired **test** client certificate → expect authentication failure if mTLS enforced.
4. Correct certificate but missing topic ACL → expect authorization failure.
5. Correct identity and ACL → expect authorized metadata/produce/consume.

Never create an expired production certificate or modify the broker CA to simulate failure. Preserve sanitized client logs and classify each failure by layer.

**Acceptance:** five distinct outcomes demonstrated or explicitly marked Pending.

## 17. Lab 11 — Client certificate renewal workflow

For a disposable KafkaUser managed by Strimzi:

1. Capture existing certificate serial, expiry, fingerprint and Secret resourceVersion.
2. Confirm Strimzi User Operator renewal behavior and whether applications reload mounted Secrets.
3. Request renewal using **documented operator-supported mechanisms** for the installed release.
4. Confirm updated Secret data and new certificate metadata.
5. Roll/reload the disposable client if it does not dynamically reload credentials.
6. Verify Kafka metadata, producer acknowledgments and consumer replay.
7. Retain old/new fingerprint and change timeline without private-key exposure.

**Acceptance:** actual renewed credential and successful authenticated client reconnection. Never force regeneration by deleting production Secrets.

## 18. Lab 12 — CA rotation tabletop and trust overlap

Design a staged CA rotation:

```text
T0: current CA trusted, current broker/client leaf certs active
T1: publish new CA trust anchor alongside old CA (supported mechanism)
T2: confirm all clients trust both anchors
T3: issue/roll broker and client leaf certs using new CA
T4: verify each advertised endpoint, principal and ACL
T5: remove old CA only after approved overlap and full inventory
```

Strimzi's actual CA renewal/key replacement behavior and trust propagation must follow its installed version's documentation. A Kubernetes Secret update may not trigger automatic reload inside an application. Rollback after CA key replacement can be constrained; document a recovery path **before** T1.

**Acceptance:** certificate inventory, client ownership, staged schedule, rollback, abort thresholds and security signoff.

## 19. Lab 13 — Kubernetes Secret and RBAC audit

```bash
kubectl -n kafka-lab auth can-i get secrets \
  --as=system:serviceaccount:kafka-lab:default \
  | tee evidence-ch27/default-sa-secret-access.txt
kubectl -n kafka-lab get role,rolebinding -o wide \
  | tee evidence-ch27/namespace-rbac.txt
kubectl -n kafka-lab get serviceaccounts \
  | tee evidence-ch27/serviceaccounts.txt
```

The impersonation check may be forbidden to the operator running the command; that is an authorization limitation, not proof of deny. Audit the real client service account's permissions and Pod Secret mounts. Avoid collecting full RoleBinding subjects or internal identities in public artifacts without redaction.

**Acceptance:** least-privilege review for Secret get/list/watch, workload identity, audit logs and at-rest encryption policy.

## 20. Lab 14 — Certificate-expiry monitoring and alerts

Monitor:

- CA, broker and client certificate `notAfter` timestamps.
- Renewal failure events and Strimzi reconciliation health.
- TLS handshake failure rate by listener and client cohort.
- Certificate hostname mismatch and untrusted CA errors.
- Kafka authentication failures versus authorization denials.
- Secret update propagation and client reload status.
- Producer/consumer availability during rotations.

Alert thresholds must account for organizational PKI lead times and business change freezes. Use real exporter/Strimzi metrics and documented certificate discovery rather than inventing a portable Prometheus metric name.

**Acceptance:** alert inventory with owner, expiry lead time, escalation and runbook links.

## 21. Lab 15 — TLS listener change rollback tabletop

Scenario: adding a new TLS listener succeeds but an application accidentally switches to it without a truststore.

**Safe response:**

1. Stop the client rollout, not the Kafka brokers.
2. Compare client configuration with listener status and certificate SAN.
3. Restore the last known working client configuration.
4. Fix trust/identity in the isolated client.
5. Verify Kafka metadata, produce/consume and all broker endpoints.
6. Remove the disposable TLS listener only through an approved Strimzi GitOps change after dependency checks.

**Acceptance:** client and platform rollback plans documented, with explicit owner and abort thresholds.

## 22. Lab 16 — Read-only automated certificate preflight

Save `verify-ch27.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BIN=/opt/kafka/bin
BS=sre-kafka-kafka-bootstrap:9092

echo '[1/7] Kubernetes context'
kubectl config current-context

echo '[2/7] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/7] Kafka listener declarations'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}'

echo '[4/7] Listener status'
kubectl -n "$NS" get kafka "$CLUSTER" \
  -o jsonpath='{.status.listeners}{"\n"}'

echo '[5/7] Strimzi certificate Secret metadata only'
kubectl -n "$NS" get secrets -l "strimzi.io/cluster=$CLUSTER" \
  -o custom-columns=NAME:.metadata.name,TYPE:.type

echo '[6/7] Kafka CRD API versions'
kubectl get crd kafkas.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'
kubectl get crd kafkausers.kafka.strimzi.io \
  -o jsonpath='{.spec.versions[*].name}{"\n"}'

echo '[7/7] Isolated plaintext foundation metadata (not TLS proof)'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --list

echo 'PASS: read-only Strimzi/Kafka metadata preflight.'
echo 'NOT PROVEN: TLS handshake, SAN, mTLS, ACL, Secret renewal, CA rotation or client recovery.'
```

```bash
chmod +x verify-ch27.sh
./verify-ch27.sh | tee evidence-ch27/preflight.txt
```

**Security note:** the script never prints Secret values. It validates only inventory and the existing plaintext lab bootstrap. A successful run must not be represented as a TLS security pass.

## 23. Ten production failure scenarios

### 23.1 Expired broker certificate
**Signal:** clients fail TLS handshakes after expiry. **Diagnose:** cert `notAfter`, operator renewal logs. **Recover:** supported certificate renewal and coordinated client verification.

### 23.2 Expired client certificate
**Signal:** mTLS authentication failure. **Diagnose:** KafkaUser Secret certificate metadata, app reload. **Recover:** approved client renewal, reload and ACL verification.

### 23.3 Unknown certificate authority
**Signal:** PKIX validation errors. **Diagnose:** client truststore and CA chain. **Recover:** approved trust distribution; never disable validation.

### 23.4 Advertised broker SAN mismatch
**Signal:** bootstrap works but broker connections fail hostname checks. **Diagnose:** advertised DNS and broker cert SANs. **Recover:** supported listener/certificate configuration.

### 23.5 CA key replacement without overlap
**Signal:** widespread client failures. **Diagnose:** trust anchors by application cohort. **Recover:** execute staged trust recovery plan.

### 23.6 Kubernetes Secret changed but client did not reload
**Signal:** renewed Secret, old credential still in use. **Diagnose:** application reload support and Pod start time. **Recover:** controlled client rollout.

### 23.7 Client mTLS succeeds but ACL denies
**Signal:** `TopicAuthorizationException`. **Diagnose:** authenticated principal and resource ACL. **Recover:** least-privilege KafkaUser/ACL change.

### 23.8 Incorrect TLS listener port or protocol
**Signal:** connection reset/handshake failure. **Diagnose:** Strimzi listener status and client `security.protocol`. **Recover:** correct client config.

### 23.9 Secret RBAC overexposure
**Signal:** unapproved service account can read client private keys. **Diagnose:** Role/RoleBinding, Pod mounts, audit logs. **Recover:** revoke access, rotate affected credentials and investigate.

### 23.10 Broker rolling certificate update affects ISR
**Signal:** ISR drops or producer latency spikes during reconciliation. **Diagnose:** operator rollout events, broker health and client retries. **Recover:** halt changes via supported operator workflow and restore health.

## 24. Troubleshooting matrix

| Symptom | First check | Second check | Owner |
|---|---|---|---|
| PKIX path building failed | CA truststore | Certificate chain | PKI/platform |
| Hostname verification failed | SAN vs advertised DNS | Listener config | Kafka SRE |
| Bad certificate | Client cert validity | Client CA trust | Kafka security |
| TLS handshake timeout | NetworkPolicy/DNS | Service/EndpointSlice | Network SRE |
| SASL auth failure | Protocol/mechanism | Credential source | IAM |
| ACL denied | Principal | Resource ACL | Kafka security |
| Old cert after rotation | Secret version | Client reload | App SRE |
| Broker renewal failed | Strimzi reconciliation | CA ownership | Kafka platform |
| CA expiry approaching | Expiry alert | Rotation lead time | PKI |
| ISR drops during rollout | Broker readiness | Rolling operation | Kafka SRE |

## 25. Six production runbooks

### Runbook A — Broker TLS outage
1. Declare impact, listener and affected client networks.
2. Check DNS/TCP then TLS handshake, chain, SAN and expiry.
3. Capture Strimzi reconciliation and broker readiness.
4. Restore approved certificate/listener configuration without weakening verification.
5. Validate all advertised brokers and producer/consumer health.
6. Record timeline, change source and prevention.

### Runbook B — Client certificate expiry
1. Identify affected KafkaUser and application cohort.
2. Inspect sanitized certificate metadata and Secret version.
3. Request supported renewal and distribute new identity.
4. Trigger controlled client reload/restart if necessary.
5. Verify mTLS principal, ACL and application SLO.
6. Improve expiry alert lead time.

### Runbook C — CA rotation
1. Inventory all listeners, clients and trust anchors.
2. Establish overlapping trust and rollback/abort criteria.
3. Execute operator-supported CA rotation stages.
4. Verify broker/client certificates and every advertised endpoint.
5. Remove old trust only after all cohorts pass.
6. Preserve security and availability signoff.

### Runbook D — Secret exposure
1. Contain unauthorized Secret access and preserve audit logs.
2. Determine affected identities, client keys and scope.
3. Revoke permissions and rotate exposed credentials.
4. Confirm authenticated clients and ACLs still work.
5. Investigate downstream misuse and notification obligations.
6. Harden RBAC, encryption and Secret access monitoring.

### Runbook E — TLS listener migration
1. Review current and target listener endpoints and security.
2. Deploy parallel supported TLS listener through GitOps.
3. Validate a canary client end-to-end.
4. Migrate application cohorts gradually with monitoring.
5. Roll back clients if handshake/availability degrades.
6. Retire plaintext listener only after verified zero dependencies.

### Runbook F — Certificate-related game day
1. Obtain approval and isolate diagnostic clients.
2. Capture Kafka health and current cert fingerprints.
3. Test wrong CA, wrong hostname and unauthorized principal.
4. Validate alerts, classification and recovery actions.
5. Reconfirm Kafka health and no Secret disclosure.
6. Publish evidence and assessor signoff.

## 26. Evidence package and acceptance checklist

```text
evidence-ch27/
  change-approval.md
  context.txt
  inventory.txt
  kafka-crd-versions.txt
  kafkauser-crd-versions.txt
  listeners.txt
  services.txt
  listener-status.txt
  secret-inventory.txt
  cluster-ca-metadata.txt
  tls-listener-status.txt
  client-secret-key-names.txt
  certificate-chain-review.md
  mtls-client-connection.md
  hostname-verification.md
  tls-negative-tests.md
  client-renewal.md
  ca-rotation-tabletop.md
  namespace-rbac.txt
  certificate-alerts.md
  rollback-tabletop.md
  preflight.txt
  security-review.md
  assessor-signoff.md
```

- [ ] Approved isolated cluster and reviewed listener change.
- [ ] Broker and client CA ownership documented.
- [ ] TLS listener status and every advertised broker endpoint verified.
- [ ] CA chain and hostname verification passed.
- [ ] mTLS client principal and topic/group ACLs verified.
- [ ] No private keys, keystore passwords or Kubernetes Secret values in Git/evidence.
- [ ] Certificate expiry alerting and renewal owners assigned.
- [ ] Client renewal executed or marked Pending.
- [ ] CA rotation tabletop reviewed; live rotation only if separately approved.
- [ ] Independent security and operational signoff captured.

## 27. Assessment — 100 points

| Domain | Points | Evidence |
|---|---:|---|
| TLS/PKI architecture and trust model | 10 | Design review |
| Listener and Strimzi compatibility | 10 | Kafka CR/status |
| CA and certificate inventory | 10 | Safe metadata |
| TLS server chain and SAN verification | 15 | Live handshake |
| mTLS KafkaUser and authenticated principal | 15 | Live client |
| Least-privilege ACL and RBAC review | 10 | Denied/allowed tests |
| Client renewal and Secret propagation | 10 | Rotation evidence |
| CA rotation and rollback planning | 5 | Tabletop |
| Alerting, troubleshooting and runbooks | 10 | Monitoring and scenarios |
| Independent security review | 5 | Signed approval |
| **Total** | **100** | |

**Pass:** ≥85/100, no critical security violations, and live TLS handshake, mTLS identity and authorization gates passed. A read-only metadata preflight or plaintext client test cannot earn TLS execution credit. If the installed Strimzi version or authorizer does not support the lab's assumed KafkaUser ACL configuration, adapt through approved mechanisms and record deviations.

## 28. Cleanup and next chapter

Delete only disposable KafkaUser and client Pods after review; a listener should be removed only via approved Kafka CR/GitOps change after confirming no clients depend on it. Preserve sanitized evidence and destroy local private-key copies using organizational secure handling procedures.

**References:** [Apache Kafka security documentation](https://kafka.apache.org/documentation/#security), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/), [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/), [TLS 1.3 RFC 8446](https://www.rfc-editor.org/rfc/rfc8446).

**Next:** Chapter 028 — Kafka SASL Authentication, SCRAM Credentials, OAuth Integration and Kubernetes Identity Operations.

---

**Verification boundary:** Publication establishes that the chapter is available on GitHub; certificate rotation, TLS/mTLS handshakes, ACL tests and independent security validation remain Pending until executed and reviewed.
