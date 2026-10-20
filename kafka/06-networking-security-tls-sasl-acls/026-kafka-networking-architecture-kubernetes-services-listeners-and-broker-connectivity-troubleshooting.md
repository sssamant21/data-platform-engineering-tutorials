# Chapter 026 — Kafka Networking Architecture, Kubernetes Services, Listeners and Broker Connectivity Troubleshooting

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 06 — Networking, Security, TLS, SASL and ACLs (1/5)  
**Primary platform:** Kubernetes, Strimzi Operator and KRaft Kafka  
**Prerequisites:** Chapters 001–025, Kubernetes networking and DNS fundamentals  
**Audience:** Kafka SREs, DBREs, platform/network engineers and application operators  
**Status:** Published; live lab execution and independent security review pending

> **Production safety:** Work only in an approved disposable cluster. Do not expose Kafka plaintext listeners on the internet, disable TLS, alter production advertised listeners, patch Strimzi-managed Services/Pods, or broaden production NetworkPolicies. Capture a working configuration and rollback plan before any connectivity change. This chapter uses the existing `kafka-lab` foundation's internal listener for isolated exercises; production clients must use approved authentication and encryption.

## 1. Learning objectives

By completion, you should be able to:

1. Trace Kafka bootstrap, metadata discovery and direct broker connections.
2. Distinguish bind listeners, advertised listeners and Kubernetes Service addresses.
3. Explain Strimzi internal and external listener exposure options.
4. Diagnose DNS, routing, TLS, authorization and network-policy failures separately.
5. Validate Kubernetes Service, EndpointSlice, Pod and listener mappings.
6. Explain KRaft controller-plane versus broker/client connectivity.
7. Build repeatable connectivity checks, SLOs, runbooks and evidence.
8. Perform safe Kubernetes-first failure simulations and recovery validation.

## 2. Kafka networking mental model

```text
Kafka client Pod
    |
    | 1. DNS: sre-kafka-kafka-bootstrap.kafka-lab.svc
    v
Kubernetes bootstrap Service :9092
    |
    | 2. TCP/TLS + Kafka Metadata request
    v
Kafka broker Pod
    |
    | 3. Metadata: topic leaders and advertised broker endpoints
    v
Client opens connections to broker-0 / broker-1 / broker-2
    |                         |
    | 4. Produce/Fetch        | 5. Metadata refresh and leader changes
    v                         v
Partition leaders        Other broker endpoints

KRaft controller quorum: separate controller listeners / control-plane paths.
```

**Key principle:** the bootstrap address is **not** a proxy for all Kafka traffic. A successful bootstrap TCP connection does not prove the client can resolve and reach every advertised broker address. Kafka metadata can contain internal-only names, unreachable load balancers, incorrect ports or wrong listener security protocols.

## 3. Networking vocabulary and invariants

| Concept | Purpose | Common failure |
|---|---|---|
| `listeners` | Socket addresses the broker binds to | Wrong bind/interface/port |
| `advertised.listeners` | Addresses returned to clients in metadata | Client cannot resolve or reach broker |
| Bootstrap Service | Initial broker discovery | Service has no ready endpoints |
| Per-broker Service | Stable broker reachability for some listener types | Service points to wrong broker |
| Headless Service | DNS identity for broker Pods | DNS/endpoint readiness |
| EndpointSlice | Actual backing endpoints for Services | Empty or stale ready endpoints |
| NetworkPolicy | Pod ingress/egress filtering | DNS or broker port denied |
| TLS/SASL | Authentication and encryption | Handshake/credentials fail |
| KRaft controller listener | Metadata quorum communication | Controller quorum unhealthy |
| Inter-broker listener | Broker-to-broker communication | Replication and ISR degradation |

Kafka clients must use the correct listener's protocol and trust configuration. TCP success alone cannot validate Kafka metadata, TLS identity, authentication or ACLs.

## 4. Strimzi listener architecture

Strimzi manages broker listeners and associated Services, certificates and exposure resources from the `Kafka` custom resource. Supported listener types and configuration fields depend on the installed Strimzi release.

Typical choices:

- **Internal:** in-cluster clients via bootstrap and broker DNS/Services.
- **LoadBalancer:** per-broker load balancer exposure where supported, with DNS, firewall and cloud costs.
- **NodePort:** node-address reachability and stable advertised endpoints; requires carefully controlled network boundaries.
- **Ingress / Route:** only where the supported Strimzi listener implementation, SNI/TLS passthrough and platform requirements are satisfied.
- **ClusterIP:** cluster-scoped reachability, not a substitute for externally routable broker addresses.

Do not assume a single L7 HTTP ingress will route native Kafka protocol correctly. Kafka is not HTTP; TLS passthrough/SNI requirements matter for supported ingress modes.

### 4.1 Illustrative internal listener

```yaml
# Excerpt only: merge into the existing Kafka CR through approved GitOps.
# Validate schema against the installed Strimzi CRD before use.
spec:
  kafka:
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
```

This plaintext example matches the isolated tutorial foundation only. Production requires TLS and appropriate authentication, covered in Chapters 027–029. Never apply this excerpt as a standalone Kafka resource.

## 5. KRaft networking boundaries

KRaft controllers communicate over dedicated controller listeners and must maintain quorum. Kafka broker/client connectivity can fail while controller quorum is healthy; the reverse is also possible. Distinguish:

1. Client → bootstrap broker.
2. Client → partition leader broker.
3. Broker → broker replication.
4. Broker/controller → controller quorum.

Strimzi-managed KRaft node pools may separate broker and controller roles. Do not assume all Kafka Pods serve client requests or expose the same ports.

## 6. Lab preflight and evidence policy

```bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
mkdir -p evidence-ch26

kubectl config current-context | tee evidence-ch26/context.txt
kubectl -n "$NS" get kafka,kafkanodepool,pods,svc -o wide \
  | tee evidence-ch26/inventory.txt
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=900s
kubectl -n "$NS" get networkpolicy -o yaml \
  > evidence-ch26/networkpolicies.yaml
```

**Stop** if the context is production, cluster health is degraded, the CLI Pod is not lab-owned or security approval is missing.

## 7. Lab 01 — Map Services and EndpointSlices

```bash
kubectl -n kafka-lab get svc -l strimzi.io/cluster=sre-kafka -o wide \
  | tee evidence-ch26/services.txt
kubectl -n kafka-lab get endpointslices \
  -l kubernetes.io/service-name=sre-kafka-kafka-bootstrap -o yaml \
  | tee evidence-ch26/bootstrap-endpointslices.yaml
kubectl -n kafka-lab describe svc sre-kafka-kafka-bootstrap \
  | tee evidence-ch26/bootstrap-service.txt
```

Service label selectors and EndpointSlice labels must be verified from actual resources; some deployments use version-specific Strimzi labels. Check that ready endpoints exist and map to broker Pods. An EndpointSlice can include not-ready addresses; interpret readiness conditions rather than merely counting addresses.

**Acceptance:** bootstrap Service port, target port and ready endpoints documented.

## 8. Lab 02 — DNS resolution from the client Pod

The Kafka CLI image may not include `nslookup`, `dig`, `getent` or a shell. Check available tools first; use an **approved pinned diagnostic image** in an isolated namespace if required.

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 --list \
  | tee evidence-ch26/bootstrap-topic-list.txt
```

If permitted, run a DNS lookup from a separate approved diagnostics Pod for:

```text
sre-kafka-kafka-bootstrap.kafka-lab.svc.cluster.local
```

The cluster DNS suffix may differ; inspect Pod resolver configuration instead of assuming `cluster.local`.

**Acceptance:** DNS resolution and successful Kafka protocol request; if DNS tooling is absent, document the alternate diagnostic method.

## 9. Lab 03 — Capture effective listener configuration

```bash
kubectl -n kafka-lab get kafka sre-kafka \
  -o jsonpath='{.spec.kafka.listeners}' \
  | tee evidence-ch26/kafka-listeners.txt
kubectl -n kafka-lab get kafka sre-kafka -o yaml \
  > evidence-ch26/kafka-cr.yaml
kubectl -n kafka-lab get svc -o wide \
  > evidence-ch26/all-services.txt
```

Compare listener names, ports, TLS settings and Service addresses. Do not expose secrets in evidence; sanitize manifests and connection parameters before sharing.

**Acceptance:** a table of each listener, client network, advertised DNS, port, protocol and owner.

## 10. Lab 04 — Validate Kafka metadata, not just TCP

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  | tee evidence-ch26/broker-api-versions.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 --describe \
  | tee evidence-ch26/topic-metadata.txt
```

A complete API-versions result for all brokers is stronger evidence than a single TCP check, but not a guarantee that every application protocol/authentication path works. Capture all advertised broker endpoints via a compatible AdminClient metadata tool when available.

**Acceptance:** brokers reachable via their metadata endpoints; no unexplained connection errors.

## 11. Lab 05 — Verify broker leaders and replication connectivity

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status \
  | tee evidence-ch26/quorum.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-retention-ch25 \
  > evidence-ch26/example-topic.txt || true
```

The Chapter 025 topic may have been cleaned up; **absence is expected** and must not be misclassified as networking failure. Select a known existing lab topic instead. Confirm RF, ISR and leader presence without modifying cluster topology.

## 12. Lab 06 — Kubernetes network-policy discovery

```bash
kubectl -n kafka-lab get networkpolicy -o wide \
  | tee evidence-ch26/networkpolicy-list.txt
kubectl -n kafka-lab get pods --show-labels \
  | tee evidence-ch26/pod-labels.txt
kubectl -n kafka-lab get networkpolicy -o yaml \
  > evidence-ch26/networkpolicy-detail.yaml
```

Review ingress to brokers, egress from clients, DNS access to CoreDNS and controller/broker communication. Kubernetes NetworkPolicy enforcement depends on the CNI; no policy does **not** imply a universally open network when cloud firewalls/service meshes apply.

**Acceptance:** documented effective policy and explicit distinction between Kubernetes and cloud network controls.

## 13. Lab 07 — Non-disruptive negative test: invalid DNS

From a **disposable diagnostic client** (not a production app), attempt a Kafka metadata command with an intentionally invalid hostname and bounded timeout:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server nonexistent-ch26.invalid:9092 \
  --command-config /dev/null --list \
  2>&1 | tee evidence-ch26/invalid-dns.txt || true
```

The invalid hostname is reserved for negative testing. The CLI may retry for some time; run under an approved execution timeout or use a client configuration with short timeouts. `--command-config /dev/null` is suitable only for the isolated plaintext foundation; omit it for TLS/SASL configurations and use the proper secure client config.

**Acceptance:** failure classified as DNS/name-resolution, with no Kafka cluster changes.

## 14. Lab 08 — Non-disruptive negative test: wrong port

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:19092 --list \
  2>&1 | tee evidence-ch26/invalid-port.txt || true
```

The chosen port is a **deliberately invalid example** and should first be verified as unused in this lab. A wrong port typically causes connection refusal or timeout; do not misdiagnose it as an ACL error.

**Acceptance:** compare DNS, TCP, Kafka protocol and authentication failure signatures.

## 15. Lab 09 — Diagnose TLS versus network failures

Inspect the Kafka listener CR for `tls: true`, advertised DNS and certificate provisioning. Use an approved TLS-enabled diagnostic client only when a real TLS listener exists.

**Decision sequence:**

1. DNS lookup succeeds?
2. TCP connection to correct port succeeds?
3. TLS handshake and broker hostname verification succeed?
4. SASL authentication (if configured) succeeds?
5. Kafka metadata request succeeds?
6. Topic authorization succeeds?
7. Every advertised leader endpoint is reachable?

**Acceptance:** failure classification and safe remediation. Do not turn off certificate verification or TLS to make a test pass.

## 16. Lab 10 — External listener architecture review

Design three candidate deployments:

| Exposure | Advantages | Trade-offs |
|---|---|---|
| Internal Service | Simple in-cluster DNS | Not externally routable |
| LoadBalancer | Cloud-native external endpoints | Per-broker cost, security groups, DNS |
| Supported Ingress/Route | Centralized edge integration | TLS passthrough/SNI and operator compatibility |

For each record: bootstrap and per-broker DNS, client source CIDRs, TLS hostname validation, listener authentication, firewall/NetworkPolicy, certificate lifecycle, multi-AZ routing and cloud cost.

**Acceptance:** architecture review approved without enabling public access.

## 17. Lab 11 — Cross-namespace client connectivity design

Create a **paper design or isolated test namespace** for a client outside `kafka-lab`. Explain fully qualified bootstrap DNS, namespace egress policy, broker ingress policy and TLS trust distribution.

Do not apply blanket `0.0.0.0/0` allow rules or copy Secrets between namespaces. In clusters with default-deny policy, DNS egress and per-broker reachability both need explicit authorization.

**Acceptance:** reviewed least-privilege network flow matrix.

## 18. Lab 12 — Advertised listener failure tabletop

Scenario: a client reaches bootstrap but metadata advertises `broker-0.internal.svc` to an external network that cannot resolve it.

**Root cause:** advertised address is valid only inside Kubernetes.

**Remediation design:** supported Strimzi external listener with routable per-broker addresses and matching TLS SANs, plus firewall and DNS verification. Never manually edit broker server.properties inside operator-managed Pods.

**Acceptance:** end-to-end discovery flow diagram and rollback plan.

## 19. Lab 13 — Kubernetes Service endpoint readiness tabletop

Scenario: bootstrap Service resolves but has zero ready endpoints because brokers are not Ready.

Investigate:

```bash
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab describe svc sre-kafka-kafka-bootstrap
kubectl -n kafka-lab get endpointslices \
  -l kubernetes.io/service-name=sre-kafka-kafka-bootstrap -o yaml
kubectl -n kafka-lab get events --sort-by=.lastTimestamp
```

Separate probe failure, Pod scheduling, listener startup, broker registration and CNI faults. Do not bypass readiness to force traffic to unhealthy brokers.

## 20. Lab 14 — Network latency and DNS SLO design

Define metrics and thresholds appropriate to the application:

- DNS lookup error rate and p95/p99 resolution time.
- TCP connect success/latency by advertised broker endpoint.
- TLS handshake failures and certificate expiry horizon.
- Kafka request timeouts, connection creation and authentication errors.
- Produce/fetch p99 latency, retries and consumer event age.
- EndpointSlice ready endpoint count and broker Pod readiness.
- Under-replicated partitions, ISR changes and KRaft quorum health.
- NetworkPolicy/CNI denies, packet loss and retransmissions.

Collect actual metric names from the deployed exporters; do not invent portable Prometheus series. Document thresholds, severity, runbook link and owner.

## 21. Lab 15 — Automated read-only network acceptance

Save `verify-ch26.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
CLUSTER=sre-kafka
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin

echo '[1/7] Context'
kubectl config current-context

echo '[2/7] Kafka Ready'
kubectl -n "$NS" wait "kafka/$CLUSTER" \
  --for=condition=Ready --timeout=120s

echo '[3/7] Bootstrap Service and port'
kubectl -n "$NS" get svc "$CLUSTER-kafka-bootstrap" -o wide
kubectl -n "$NS" get svc "$CLUSTER-kafka-bootstrap" \
  -o jsonpath='{.spec.ports[*].port}{"\n"}' | grep -w 9092

echo '[4/7] EndpointSlice discovery'
kubectl -n "$NS" get endpointslices \
  -l "kubernetes.io/service-name=$CLUSTER-kafka-bootstrap" -o name \
  | grep -q .

echo '[5/7] Kafka metadata request'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --list

echo '[6/7] Broker API discovery'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS"

echo '[7/7] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo 'PASS: bootstrap metadata and basic discovery.'
echo 'NOT PROVEN: all ready EndpointSlice conditions, external routing, TLS, SASL, ACLs, per-broker p99 or failure recovery.'
```

```bash
chmod +x verify-ch26.sh
./verify-ch26.sh | tee evidence-ch26/acceptance.txt
```

**Limitations:** the script validates basic in-cluster bootstrap behavior, not all broker endpoints or secure external clients. The `9092` assumption applies only to the tutorial's isolated internal listener. For other listeners, adapt using approved security config and actual ports.

## 22. Ten production failure scenarios

### 22.1 Bootstrap DNS failure
**Signals:** `UnknownHostException`, failed DNS queries. **Check:** CoreDNS, Pod resolver, namespace/FQDN, NetworkPolicy DNS egress. **Recover:** correct DNS/routing without editing broker files.

### 22.2 Bootstrap succeeds, leader unreachable
**Signals:** metadata fetched, produce/fetch timeouts. **Check:** advertised broker names, per-broker Services and routes. **Recover:** supported Strimzi listener configuration.

### 22.3 Wrong listener security protocol
**Signals:** connection reset or handshake errors. **Check:** TLS/SASL settings versus listener. **Recover:** approved client configuration, not disabling security.

### 22.4 Certificate hostname mismatch
**Signals:** TLS hostname verification failure. **Check:** SANs and advertised DNS. **Recover:** approved certificate/listener rotation.

### 22.5 NetworkPolicy blocks DNS
**Signals:** DNS lookup timeout after policy rollout. **Check:** client egress and CoreDNS ingress. **Recover:** narrowly scoped DNS policy.

### 22.6 NetworkPolicy blocks broker port
**Signals:** bootstrap/leader TCP timeout. **Check:** selectors, namespaces, listener ports and CNI enforcement. **Recover:** least-privilege allow rules.

### 22.7 EndpointSlice has no ready broker
**Signals:** Service resolves, connections fail. **Check:** broker Pod readiness and operator reconciliation. **Recover:** root-cause Pod/broker failure.

### 22.8 Cloud LoadBalancer target unhealthy
**Signals:** external connection timeout, internal works. **Check:** LB target health, security groups, NACLs, firewall and advertised endpoint. **Recover:** supported cloud/Strimzi config.

### 22.9 KRaft controller communication disrupted
**Signals:** quorum errors, metadata changes stall. **Check:** controller listener and node-pool connectivity. **Recover:** restore quorum paths, avoid unsafe quorum manipulation.

### 22.10 Cross-zone packet loss and latency
**Signals:** ISR flaps, request p99 spikes. **Check:** node topology, CNI, cloud networking, network saturation. **Recover:** capacity/routing remediation and controlled balancing.

## 23. Troubleshooting decision matrix

| Symptom | First check | Second check | Escalation |
|---|---|---|---|
| Unknown host | DNS resolver | Service/FQDN | Platform DNS |
| Connection refused | Service/port | Pod listener | Kafka SRE |
| Timeout | NetworkPolicy | Firewall/LB route | Network SRE |
| TLS handshake failure | Protocol/SAN | Truststore/expiry | Security PKI |
| SASL auth failed | Mechanism/credentials | Broker auth config | IAM/security |
| Topic authorization failed | Principal identity | ACL/role | Kafka security |
| Bootstrap only works | Advertised broker DNS | Per-broker routes | Kafka platform |
| Replication degraded | ISR/broker logs | Inter-broker networking | Kafka SRE |
| Metadata quorum unhealthy | Controller Pods | Controller listener | Kafka/KRaft SRE |

## 24. Six production runbooks

### Runbook A — Client bootstrap outage
1. Identify affected client networks and listeners.
2. Check DNS, Service and EndpointSlice readiness.
3. Verify TCP, TLS and Kafka metadata sequentially.
4. Capture broker and operator events.
5. Restore approved networking without security bypass.
6. Verify producer/consumer SLO and publish timeline.

### Runbook B — Advertised listener mismatch
1. Record bootstrap address and metadata-advertised broker endpoints.
2. Test DNS and TCP reachability from actual client network.
3. Validate TLS SANs and protocol.
4. Change Strimzi Kafka listener config through GitOps.
5. Observe controlled reconciliation and all-broker reachability.
6. Validate client recovery and rollback evidence.

### Runbook C — NetworkPolicy regression
1. Correlate onset with policy change.
2. Inspect selectors, ingress, egress and DNS requirements.
3. Use CNI flow logs where available.
4. Apply minimal approved correction.
5. Validate broker, controller and client flows.
6. Record preventive policy tests.

### Runbook D — External load balancer outage
1. Check provider LB health, target registration and endpoint DNS.
2. Compare in-cluster versus external reachability.
3. Validate firewall/security groups and TLS passthrough.
4. Restore supported Strimzi/cloud resource config.
5. Test each advertised broker address.
6. Update multi-AZ resilience and cost analysis.

### Runbook E — TLS or authentication failure
1. Classify handshake versus authentication versus authorization.
2. Capture sanitized client and broker errors.
3. Inspect certificate chain, SAN, expiry and security protocol.
4. Restore approved certificates/credentials without weakening verification.
5. Validate identity and topic ACLs.
6. Audit rotation and alerting.

### Runbook F — Network reliability game day
1. Obtain approval and baseline Kafka quorum, ISR and p99.
2. Use only disposable diagnostic clients and non-disruptive negative tests.
3. Classify DNS, port and advertised-address failures.
4. Test recovery and alert routing.
5. Verify event reconciliation and no business impact.
6. Publish evidence, open risks and owner signoff.

## 25. Evidence package

```text
evidence-ch26/
  context.txt
  change-approval.md
  inventory.txt
  services.txt
  bootstrap-endpointslices.yaml
  bootstrap-service.txt
  bootstrap-topic-list.txt
  kafka-listeners.txt
  kafka-cr.yaml
  all-services.txt
  broker-api-versions.txt
  topic-metadata.txt
  quorum.txt
  networkpolicy-list.txt
  networkpolicy-detail.yaml
  pod-labels.txt
  invalid-dns.txt
  invalid-port.txt
  tls-protocol-review.md
  external-listener-design.md
  cross-namespace-flow-matrix.md
  endpoint-readiness-tabletop.md
  networking-slo.md
  acceptance.txt
  incident-review.md
  security-review.md
  assessor-signoff.md
```

Redact credentials, tokens, certificate private keys, sensitive DNS names and business data. Record command, timestamp, expected/actual result, Kafka/Strimzi versions, evidence path and reviewer. Mark unexecuted tests Pending.

## 26. Acceptance assessment — 100 points

| Domain | Points | Critical |
|---|---:|---|
| Kubernetes/Kafka topology and listener model | 10 | Yes |
| Service/EndpointSlice/DNS discovery | 10 | Yes |
| Metadata and advertised broker connectivity | 15 | Yes |
| KRaft and broker interconnect analysis | 10 | Yes |
| NetworkPolicy and cross-namespace controls | 10 | Yes |
| TLS/authentication failure classification | 10 | Yes |
| External listener design and risk review | 10 | No |
| Non-disruptive negative tests | 10 | No |
| Automated checks and monitoring/SLOs | 10 | No |
| Runbooks, evidence and independent signoff | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates evidenced. Do not award TLS/authentication execution credit if the lab only uses the plaintext internal foundation; a design review is not a successful secure-client handshake. Production acceptance requires real secure listener and client-network testing.

## 27. Cleanup and next chapter

All default labs are read-only or client-side negative tests. No broker/PVC cleanup is required. If an approved disposable diagnostic namespace or client Pod was created, delete only those owned resources after preserving evidence; do not delete Strimzi-managed Services, Kafka broker Pods or cluster networking.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/), [Kubernetes DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

**Next:** Chapter 027 — Kafka TLS, Certificate Management, Strimzi Listener Encryption and Kubernetes Secret Rotation.

---

**Verification boundary:** GitHub publication establishes document availability only. Live network testing, secure listener validation, failure drills and independent security approval remain pending.
