# Chapter 049 — Kafka Networking, TLS, SASL, ACL and Kubernetes Connectivity Incident Troubleshooting

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 10 — Troubleshooting and Incident Response (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–048, especially 026–030, 036–048  
**Status:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Run only in an approved disposable Kubernetes environment with dedicated KafkaUser and synthetic topic/group. Never disable TLS/SASL/ACLs, enable anonymous access, copy passwords/private keys to logs, open broad NetworkPolicies, patch Strimzi-owned Pods directly or affect production listeners. High-risk cloud firewall, CA and broker listener changes require separately approved maintenance. All live validation remains Pending.

## 1. Mission

Diagnose Kafka client connectivity and authorization incidents across DNS, Kafka bootstrap and advertised listeners, Kubernetes Services/EndpointSlices, CNI/NetworkPolicy, TLS trust and certificate rotation, SASL/SCRAM and mTLS identities, topic/group/transactional ACLs, and external load balancers. Use evidence to distinguish transport failures from authentication and authorization errors while preserving security and durability.

## 2. Connectivity request path

```text
Application Pod (producer/consumer)
    |
    +-- CoreDNS -> bootstrap Service -> EndpointSlice -> broker Pod
    |                                         |
    |                                  Kafka metadata response
    |                                         |
    +-- broker advertised DNS/port <----------+
              |
      CNI / NetworkPolicy / LB / firewall
              |
      TCP connection + TLS handshake
              |
      SASL or mTLS authentication
              |
      Kafka principal + ACL authorization
              |
      Topic partition / consumer coordinator
              |
      producer callback / consumer event ledger
```

A reachable bootstrap Service is not proof that the client can reach **every advertised broker endpoint**. Kafka metadata may direct the client to broker hostnames/ports inaccessible from the client's network zone.

## 3. Layered diagnostic matrix

| Symptom | Layer | First evidence | Safe response |
|---|---|---|---|
| UnknownHostException | DNS | client Pod resolver, Service, advertised name | correct approved DNS/listener |
| Connection refused/timeout | TCP/routing | endpoints, policy, LB, Pod readiness | isolate path |
| SSLHandshakeException | TLS | public cert chain, SAN, truststore, expiry | approved trust/identity fix |
| SaslAuthenticationException | SASL | mechanism, KafkaUser, redacted logs | correct approved identity |
| TopicAuthorizationException | ACL | principal, resource, operation | least-privilege grant review |
| GroupAuthorizationException | ACL/group | group ID and group ACL | scoped group permission |
| Bootstrap works, produce fails | advertised listener | metadata broker endpoints | correct network reachability |
| Intermittent reset | LB/CNI/host | conntrack, idle timeout, CPU and logs | bounded network remediation |

**Security boundary:** Authentication proves identity; authorization permits operations. A successful TLS handshake does not prove the client is authorized to Describe/Read/Write the requested topic or group.

## 4. Strimzi and Kubernetes-first read-only diagnostics

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,kafkauser,pods,svc,endpointslices -o wide
kubectl -n kafka-lab get networkpolicy
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp

# Inspect Kafka listener configuration and conditions; review before sharing output.
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.listeners}{"\n"}{.status.conditions}{"\n"}'

# Inspect bootstrap and broker Services and endpoint routing.
kubectl -n kafka-lab get svc -l strimzi.io/cluster=sre-kafka -o wide
kubectl -n kafka-lab get endpointslices -l kubernetes.io/service-name=sre-kafka-kafka-bootstrap

# Verify KRaft quorum through an approved lab Kafka CLI Pod.
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status

# Time-bounded synthetic client logs (substitute actual Pod).
kubectl -n kafka-lab logs SYNTHETIC_CLIENT_POD --since=15m --timestamps --tail=300
```

Use actual listener names and Strimzi API version discovered from the cluster. The plaintext internal 9092 bootstrap is for disposable lab inventory only. Secure Kafka CLI operations require the version-supported `--command-config` with approved TLS/SASL properties and scoped Kafka ACLs.

## 5. TLS and identity triage

- Validate the public certificate's subject, SANs, issuer, notBefore/notAfter and chain against the client's trusted CA bundle. Do not disable hostname verification.
- For Strimzi-managed CAs, distinguish broker/server certificate rotation from client certificate or trust-bundle rollout. Review operator version-specific procedures and CA renewal/replace phases.
- SASL mechanism and `security.protocol` must match the listener. A valid KafkaUser CR does not prove the application Pod loaded its current credentials.
- With mTLS, validate the client certificate chain, principal mapping and ACLs. Never export a private key for troubleshooting.
- ACL diagnosis must include resource type, resource name/pattern, principal, host and operation; granting wildcard All is not an acceptable shortcut.
- External listeners must expose bootstrap **and per-broker advertised endpoints** through the approved LB/Ingress/NodePort strategy; TLS termination and hostname design require version-specific validation.

## 6. Twenty Kubernetes-first hands-on labs

### Lab 01 — Authorize connectivity incident lab

**Objective and procedure:** Confirm isolated namespace, cluster context, test KafkaUser, synthetic topic, incident owner, redaction, abort conditions and no-production-security-bypass rule.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 02 — Inventory Strimzi listeners and Services

**Objective and procedure:** Read Kafka CR listeners, bootstrap and broker Services, TLS/auth settings, endpoints and external exposure without printing credentials.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 03 — Validate KRaft and Kafka baseline

**Objective and procedure:** Record quorum, Kafka Ready, NodePools, Pods, PVCs, partition ISR and synthetic producer callback SLI.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 04 — Inspect bootstrap DNS

**Objective and procedure:** Resolve bootstrap Service from approved client Pod; compare A/AAAA answers, search domains and CoreDNS errors.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 05 — Inspect broker advertised listeners

**Objective and procedure:** Compare metadata-returned broker hostnames/ports with actual DNS and network reachability from client zone.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 06 — Inspect Kubernetes EndpointSlices

**Objective and procedure:** Check Service selectors, EndpointSlices, Pod readiness, targetPort and network topology for broker listeners.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 07 — Inspect NetworkPolicy ingress and egress

**Objective and procedure:** Evaluate namespace and Pod selectors, DNS egress, listener ports and default-deny behavior without broad allow-all changes.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 08 — Inspect CNI and kube-proxy path

**Objective and procedure:** Correlate CNI policies, node routing, service proxy mode, conntrack saturation and Pod-to-Service reachability.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 09 — Validate TLS certificate chain

**Objective and procedure:** Inspect public certificate metadata, trust roots, intermediate chain, SAN/hostname verification and expiry without exporting keys.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 10 — Validate Strimzi CA rotation posture

**Objective and procedure:** Review cluster/client CA lifecycle, renewal windows, KafkaUser Secret references and application trust rollout dependencies.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 11 — Diagnose SASL mechanism mismatch

**Objective and procedure:** Compare broker listener auth with client SASL mechanism, security protocol, JAAS source and redacted broker errors.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 12 — Diagnose SCRAM authentication failure

**Objective and procedure:** Check KafkaUser CR type, principal, Secret version and client rollout; never reveal password values.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 13 — Diagnose mTLS client identity

**Objective and procedure:** Check KafkaUser TLS authentication, client certificate principal, CA trust and expiry; validate least-privilege mapping.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 14 — Diagnose topic and group ACL denial

**Objective and procedure:** Correlate principal, resource, operation, topic/group names and denial logs; request narrowly scoped authorization.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 15 — Diagnose transactional.id authorization

**Objective and procedure:** Validate transactional producer identity and ACL permissions separately from topic Write and group Read.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 16 — Inspect cross-namespace and cross-cluster routing

**Objective and procedure:** Review namespace policy, DNS, ingress/load balancer exposure, private endpoints and cloud firewall rules.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 17 — Inspect load balancer and idle timeouts

**Objective and procedure:** Correlate connection resets, TCP keepalive, proxy/LB idle timeout, TLS termination design and broker metadata routing.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 18 — Run bounded synthetic DNS failure drill

**Objective and procedure:** Use a test-only client configured with an intentionally invalid hostname; record error, restore and confirm no broker changes.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 19 — Run bounded synthetic ACL-denial drill

**Objective and procedure:** Use a dedicated restricted KafkaUser against a synthetic topic/group; capture authorization failure and restore approved access.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

### Lab 20 — Complete incident triage and acceptance

**Objective and procedure:** Correlate DNS, Service, TLS/SASL, ACL, KRaft/ISR, client SLI and ledger; produce timeline and 100-point assessor evidence.

**Evidence and acceptance:** Record exact Kubernetes context, Strimzi/Kafka/client versions, source command, UTC timestamp, expected and observed DNS/TCP/TLS/auth outcome, synthetic topic/group, Kafka quorum/ISR, redaction, rollback, owner and independent assessor. Mark **Pending** until live execution. All drills are client-only and bounded.

## 7. Safe synthetic connectivity drills

**DNS drill:** Configure only a synthetic client Pod with an intentionally nonexistent bootstrap hostname. Capture resolver failure and application callback classification, restore approved bootstrap and verify client recovery.

**ACL drill:** Use a dedicated restricted KafkaUser against a synthetic topic/group. Capture expected authorization denial without altering production ACLs, then restore only the test client's approved identity. Never disable authorizers or authentication.

**TLS drill:** Prefer an offline test of certificate expiry/hostname mismatch with synthetic certificates and a test client. Do not rotate production Kafka CAs or weaken hostname verification to manufacture failures.

**Abort:** Stop immediately if a non-lab namespace, real client, production Kafka listener, credential, quorum/ISR or security control is affected.

## 8. Read-only verification script

Save as `verify-ch49.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
echo '[1/12] Context'; kubectl config current-context
echo '[2/12] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" --for=condition=Ready --timeout=120s
echo '[3/12] Kafka and NodePools'
kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[4/12] Kafka listener configuration'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.spec.kafka.listeners}{"\n"}'
echo '[5/12] Pods and Services'
kubectl -n "$NS" get pods,svc -o wide
echo '[6/12] EndpointSlices'
kubectl -n "$NS" get endpointslices -o wide
echo '[7/12] NetworkPolicies'
kubectl -n "$NS" get networkpolicy
echo '[8/12] KafkaUser inventory (metadata only)'
kubectl -n "$NS" get kafkauser -o custom-columns=NAME:.metadata.name,AUTH:.spec.authentication.type
echo '[9/12] Kafka conditions'
kubectl -n "$NS" get kafka "$CLUSTER" -o jsonpath='{.status.conditions}{"\n"}'
echo '[10/12] Kubernetes Events'
kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[11/12] DNS system Pods'
kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide
echo '[12/12] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" --bootstrap-server "$BS" describe --status
echo 'PASS: read-only connectivity inventory.'
echo 'NOT PROVEN: secure TLS/SASL handshake, ACL acceptance, external routing, client SLO or independent security review.'
```

Run `chmod +x verify-ch49.sh && ./verify-ch49.sh | tee evidence-ch49/preflight.txt`. Cluster-scoped DNS Pod inventory may be restricted by RBAC; record the permission limitation instead of expanding privileges.

## 9. Twelve troubleshooting scenarios

### Scenario 1 — Bootstrap DNS resolves but broker metadata hostname fails

**Detect and diagnose:** Inspect advertised listeners and per-broker DNS from client network zone. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 2 — Service has no ready EndpointSlices

**Detect and diagnose:** Inspect selector, Pod readiness, listener target ports and Strimzi reconciliation. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 3 — Default-deny NetworkPolicy blocks DNS

**Detect and diagnose:** Inspect UDP/TCP 53 egress and DNS namespace selectors without allow-all. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 4 — TLS handshake fails after CA rotation

**Detect and diagnose:** Compare truststore, intermediate chain, SAN and certificate rollout timing. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 5 — Certificate expired on one client

**Detect and diagnose:** Check public certificate dates and KafkaUser Secret version without exposing private key. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 6 — SASL mechanism mismatch

**Detect and diagnose:** Compare listener auth, security.protocol, SASL mechanism and redacted logs. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 7 — SCRAM credentials rotated but Pod stale

**Detect and diagnose:** Review Secret resource version and application rollout; never log password. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 8 — mTLS principal not mapped as expected

**Detect and diagnose:** Inspect certificate subject, principal mapping and ACL decision. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 9 — Topic Write allowed but Describe denied

**Detect and diagnose:** Check exact resource/operation ACL and Kafka client metadata needs. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 10 — Consumer group authorization failure

**Detect and diagnose:** Distinguish group Read ACL from topic Read/Describe and coordinator reachability. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 11 — External load balancer reaches bootstrap but not brokers

**Detect and diagnose:** Validate advertised broker endpoints, LB routing and network firewalls. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

### Scenario 12 — Intermittent connection resets under load

**Detect and diagnose:** Inspect LB idle timeout, conntrack, TLS errors, CPU and Kafka request queue. Correlate client errors with Strimzi listener configuration, Service/EndpointSlice, DNS, NetworkPolicy, TLS/SASL/ACL decisions and Kafka KRaft/ISR health. **Recover:** Apply approved least-privilege, security-preserving change; verify producer callbacks and unique processed event IDs. **Evidence:** Redacted UTC timeline, source queries, version and owner.

## 10. Eight production SRE runbooks

### Runbook A — Kafka bootstrap and advertised listener connectivity

**Trigger and first response:** Confirm client zone, DNS, bootstrap Service, metadata broker endpoints, routing and approved listener configuration. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook B — Kubernetes DNS, EndpointSlice and CNI failures

**Trigger and first response:** Inspect CoreDNS, Service/EndpointSlice, Pod readiness, NetworkPolicy, CNI and node routing. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook C — TLS certificate expiry and trust-chain incident

**Trigger and first response:** Validate certificate metadata, SAN, trust chain, CA rotation and approved rollout without exporting keys. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook D — SASL/SCRAM authentication failure

**Trigger and first response:** Correlate mechanism, principal, KafkaUser Secret reference, rotation and client rollout; preserve secrets. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook E — mTLS identity and KafkaUser certificate failure

**Trigger and first response:** Inspect client cert metadata, Strimzi CA trust, principal mapping and least privilege. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook F — Kafka ACL and authorization-denied incident

**Trigger and first response:** Map principal, topic/group/transactional resource and denied operation; use reviewed minimal ACL fix. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook G — Cross-network LB and cloud firewall incident

**Trigger and first response:** Check private endpoint, DNS, LB health, broker advertised listeners and idle timeout. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

### Runbook H — Secure connectivity recovery and incident closure

**Trigger and first response:** Verify KRaft/ISR, producer callbacks, consumer unique-event ledger, TLS/auth, SLO and rollback evidence. **Safety:** Preserve TLS, authentication, authorization and KRaft/ISR; prohibit broad allow-all fixes and credential export. **Recovery gate:** Recheck secure client connection, scoped authorization, Kafka SLO, event ledger, alert routing, GitOps approval and postincident owner.

## 11. Evidence package

```text
evidence-ch49/
  approval-and-scope.md
  context-version-matrix.md
  preflight.txt
  listener-and-service-inventory.md
  kraft-isr-baseline.md
  bootstrap-dns.md
  advertised-broker-endpoints.md
  endpointslice-readiness.md
  networkpolicy-analysis.md
  cni-kubeproxy-conntrack.md
  tls-chain-san-expiry.md
  ca-rotation-readiness.md
  sasl-mechanism-review.md
  scram-kafkauser-review.md
  mtls-principal-review.md
  topic-group-acl-denials.md
  transactional-id-acls.md
  cross-namespace-cloud-routing.md
  load-balancer-idle-timeout.md
  synthetic-dns-drill.md
  synthetic-acl-drill.md
  client-slo-and-event-ledger.csv
  incident-timeline.md
  security-review.md
  independent-signoff.md
```

All evidence requires exact source, version, UTC timestamp, expected/observed result, redaction, owner, rollback and assessor. A simulated test is labeled Simulated; missing tests remain Pending.

## 12. 100-point secure connectivity incident assessment

| Domain | Points | Critical |
|---|---:|---|
| Approval, isolation and safety | 10 | Yes |
| Kafka listener and advertised endpoint analysis | 15 | Yes |
| Kubernetes DNS, Service, EndpointSlice and CNI | 15 | Yes |
| NetworkPolicy, LB and firewall diagnosis | 10 | Yes |
| TLS trust, certificate and CA rotation | 15 | Yes |
| SASL/SCRAM, mTLS and KafkaUser identities | 15 | Yes |
| Topic/group/transactional ACLs | 10 | Yes |
| Synthetic drills and client recovery | 5 | Yes |
| Independent security/technical review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. **Automatic Fail:** disabling TLS/SASL/ACLs, broad unrestricted access, credential/private-key exposure, unapproved production listener changes, fabricated drills, unexplained event loss or missing independent review.

## 13. Cleanup, references and next chapter

Remove only chapter-owned synthetic client Pods, test KafkaUser/topic and test rules through approved GitOps. Preserve sanitized evidence and corrective actions. Do not delete operator-managed Secrets, production Kafka topics, offsets, PVCs or shared monitoring.

**References:** [Apache Kafka Security](https://kafka.apache.org/documentation/#security), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [Kubernetes DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/).

**Next:** Chapter 050 — Kafka Production Incident Response, Recovery, RCA and Troubleshooting Acceptance Capstone.

---

**Verification boundary:** GitHub publication verifies only document availability. Live DNS/TLS/SASL/ACL drills, connectivity recovery, security review and independent technical acceptance remain Pending.
