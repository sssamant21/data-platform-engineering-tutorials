# Chapter 103 — Azure Kafka Identity, Entra ID, TLS, SASL, ACL and Secrets

**Curriculum:** Kafka Administration, SRE & Platform Engineering · **Part 21:** Azure Kafka Engineering & SRE (3/10)  
**Primary platform:** AKS + Strimzi-managed KRaft Kafka · **Comparison:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 026–030, 066–070, 101–102; AKS, Azure IAM, Kafka security  
**Publication:** Published · **Live execution:** Pending · **Independent security review:** Pending

> **Safety and scope:** All samples are nonproduction references. Do not print passwords, SAS connection strings, tokens, private keys or complete Kubernetes Secrets. Never disable TLS verification, open broker listeners publicly or use cluster-admin/superuser for application traffic. Azure Event Hubs is not a full Kafka broker; do not assume Strimzi Kafka ACLs, KafkaUser, mTLS, SCRAM or Kafka administration APIs apply to its Kafka endpoint. Verify current cloud/client support before implementation.

## 1. Learning objectives

Implement defense-in-depth identity, encryption, authentication and authorization for **AKS-hosted Kafka**, and accurately distinguish **Microsoft Entra ID + Azure RBAC** used for Azure resources from **Kafka-native SASL/mTLS + ACL** used by Strimzi Kafka. Integrate Azure Key Vault with Kubernetes safely, design credential rotation and demonstrate least-privilege synthetic clients.

## 2. Two different security planes

```text
AKS application Pod
  ├── Kubernetes ServiceAccount + AKS Workload Identity
  │     └── Entra federated credential -> Azure RBAC -> Key Vault / Azure APIs
  │
  └── Kafka client (independent Kafka credentials)
        ├── TLS server verification
        ├── Strimzi Kafka: SCRAM-SHA-512 or mTLS KafkaUser
        │       └── Kafka ACLs (topics, consumer groups, transactional IDs)
        └── Event Hubs Kafka endpoint: supported SASL mechanism
                └── SAS / Entra authorization and Azure RBAC where supported
```

**Key distinction:** An AKS Pod with a valid Entra workload identity does **not** automatically authenticate to a Strimzi Kafka broker. Kafka authentication requires a compatible listener, credential, client configuration and authorizer. Likewise, Kubernetes RBAC is not Kafka ACL authorization.

## 3. Identity and authorization matrix

| Resource/action | Identity | Authorization | Audit |
|---|---|---|---|
| AKS Kubernetes API | K8s user/SA (possibly Entra integrated) | Kubernetes RBAC | AKS audit logs |
| Key Vault secret read | Workload Identity / Entra principal | Azure RBAC or configured vault model | Key Vault diagnostics |
| Strimzi Kafka produce | SCRAM or client cert principal | Kafka topic ACL | Kafka broker/client auth logs |
| Strimzi Kafka consume | SCRAM or client cert principal | Topic and group ACL | Kafka auth logs and consumer metrics |
| Event Hubs Kafka endpoint | Supported SASL mechanism, SAS or OAuth as applicable | Event Hubs access policy / Azure data roles | Azure diagnostics |
| Secret read in AKS | Kubernetes SA/user | Kubernetes RBAC | Kubernetes audit |

Do not treat Azure control-plane roles (e.g. Contributor) as equivalent to Kafka topic write permissions.

## 4. AKS Workload Identity and Key Vault

Prerequisites: AKS OIDC issuer and Workload Identity enabled, a **federated identity credential** with the correct issuer/subject/audience, a dedicated Kubernetes service account, and minimal Azure role assignments. The client Pod must be configured for the chosen Workload Identity flow; the Kubernetes service-account annotation alone is not sufficient.

Read-only inventory:

```bash
az account show --query '{name:name,id:id,tenantId:tenantId}' -o json
az aks show -g RESOURCE_GROUP -n AKS_CLUSTER --query '{oidc:oidcIssuerProfile.issuerUrl,workloadIdentity:securityProfile.workloadIdentity}' -o json
kubectl config current-context
kubectl -n kafka-apps get sa -o yaml
kubectl -n kafka-apps get pods -o wide
az keyvault show -n KEY_VAULT --query '{name:name,enableRbacAuthorization:properties.enableRbacAuthorization,publicNetworkAccess:properties.publicNetworkAccess}' -o json
```

**Security:** never paste raw `kubectl get secret -o yaml` into tickets. Key Vault Secret Store CSI driver mounts are not the same as automatically refreshing application credentials: validate driver rotation behavior and client reload/restart.

## 5. Strimzi TLS listeners and KafkaUser

Use a **TLS listener** for every client path; prefer internal listeners for AKS workloads. Broker certs need correct DNS SANs and trusted CA. For external listeners, ensure advertised addresses match the certificate.

Illustrative Strimzi listener excerpt (merge into a version-compatible existing `Kafka` CR after schema validation):

```yaml
spec:
  kafka:
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
    authorization:
      type: simple
```

A separate mTLS listener can use `authentication.type: tls`. **Do not** use this snippet as a complete Kafka resource; Kafka/KRaft/NodePool requirements are version-specific. Apply changes only in an approved isolated cluster with GitOps review.

Illustrative least-privilege SCRAM KafkaUser (assuming a matching Kafka cluster label and enabled User Operator):

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: orders-reader
  namespace: kafka
  labels:
    strimzi.io/cluster: demo-kafka
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: orders.events
          patternType: literal
        operations: [Read, Describe]
      - resource:
          type: group
          name: orders-reader-
          patternType: prefix
        operations: [Read]
```

For producers, grant only the necessary topic Write/Describe (and additional operations where the selected idempotent/transactional client mode requires them). Kafka ACL resource matching is exact/prefix as configured; test **deny-by-default**.

## 6. SASL/SCRAM client configuration

Use `SASL_SSL`, broker trust material and SCRAM-SHA-512 only when matching the configured listener:

```properties
bootstrap.servers=demo-kafka-kafka-bootstrap.kafka.svc:9093
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
ssl.truststore.location=/etc/kafka/truststore.p12
ssl.truststore.type=PKCS12
# Obtain sasl.jaas.config via secret injection, not source control.
```

Do not put the JAAS password in Git, ConfigMaps, command history or logs. A KafkaUser generated Kubernetes Secret must be accessible only to its intended application; scope Kubernetes RBAC accordingly.

## 7. mTLS identity and certificate lifecycle

mTLS requires broker trust in the client certificate CA, client trust in the broker CA, matching Kafka principal identity and ACLs. Review expiry alarms, renewal sequencing, SAN/hostname verification, issuer rotation and client reload. Certificate authentication and TLS encryption are different controls: a TLS-encrypted listener does not necessarily require client certificates.

## 8. Azure Event Hubs Kafka authentication contrast

The Kafka-compatible endpoint uses a different service authorization model. A commonly supported pattern is **SASL_SSL with PLAIN** and Event Hubs connection-string credentials; Microsoft Entra/OAuth support depends on endpoint and client capability. Confirm current supported mechanisms before configuring production clients.

Illustrative **configuration shape only** (no real secret):

```properties
bootstrap.servers=EVENT_HUB_NAMESPACE.servicebus.windows.net:9093
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
# SASL username/password must come from a protected secret source.
# Do not commit Event Hubs connection strings or SAS keys.
```

A Kafka `KafkaUser` resource or Strimzi `simple` ACL cannot administer Event Hubs. Check Event Hubs namespace/entity permissions, supported Kafka APIs, client compatibility, consumer groups and quotas separately.

## 9. Defense in depth and threat model

| Threat | Control | Verification |
|---|---|---|
| Stolen Kafka password | Key Vault/K8s Secret scope, rotation, ACLs | deny and rotate test |
| Stolen SAS key | restricted Event Hubs policy, key rotation | auth denial after revocation |
| Broker impersonation | TLS CA and hostname validation | reject wrong certificate |
| Tenant cross-read | per-tenant principal and topic/group ACLs | denied synthetic read |
| Secret exposure in Pod | Kubernetes RBAC, CSI scope, no env/log dump | access audit |
| Compromised Azure identity | federated identity scope, least privilege | token/role audit |
| Network lateral movement | AKS NetworkPolicy, private endpoints, NSG | approved packet path |
| Expired client cert | alert and staged rotation | reconnect SLO |

## 10. Kubernetes-first hands-on labs (20)

### Lab 01 — Identity boundary inventory

**Procedure:** Map AKS identities, Strimzi operator, KafkaUser principals, Entra ID, Azure RBAC and Event Hubs authorization. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 02 — Inspect AKS Workload Identity

**Procedure:** Check OIDC issuer, service-account annotation, federated identity credential and role scope. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 03 — Inspect Key Vault access

**Procedure:** Validate vault RBAC, private endpoints, DNS, secret rotation ownership and audit policy. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 04 — Validate Secret Store CSI

**Procedure:** Inspect provider class, CSI mounts, synced secret policy and restart/rotation semantics. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 05 — Review Strimzi Kafka listener TLS

**Procedure:** Inspect listener type, certificate source, trust chain and TLS termination. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 06 — Validate broker certificate identity

**Procedure:** Check SAN/DNS names, expiry, key usage and TLS hostname validation. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 07 — Review mTLS KafkaUser

**Procedure:** Inspect certificate principal, secret distribution and ACL bindings. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 08 — Review SASL/SCRAM KafkaUser

**Procedure:** Inspect password generation, secret lifecycle, TLS and client JAAS mechanism. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 09 — Validate Kafka authorization

**Procedure:** Review simple ACL authorizer, topic/group patterns and least privilege. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 10 — Review Kafka superusers

**Procedure:** Ensure operator/broker principals only; no broad app admin access. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 11 — Review Kubernetes RBAC

**Procedure:** Check namespace-scoped access, Secret readers and impersonation. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 12 — Inspect AKS NetworkPolicy

**Procedure:** Validate Pod-to-broker traffic, DNS and egress to identity services. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 13 — Check Event Hubs SAS

**Procedure:** Review Kafka SASL_SSL PLAIN with namespace connection string stored securely. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 14 — Check Event Hubs OAuth

**Procedure:** Validate Microsoft Entra token-based Kafka auth only against currently supported endpoint/client docs. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 15 — Compare Event Hubs RBAC

**Procedure:** Map Azure data-plane roles to Event Hubs namespaces/entities; distinguish Kafka ACL semantics. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 16 — Run synthetic TLS smoke

**Procedure:** Plan nonproduction Kafka client handshake and expected failure on wrong trust root. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 17 — Run synthetic produce-consume

**Procedure:** Use approved namespace, topic/event hub, producer ID and consumer group; verify event ledger. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 18 — Exercise least-privilege denial

**Procedure:** Verify read-only principal cannot produce; record sanitized authorization failure. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 19 — Design rotation and revocation

**Procedure:** Document SCRAM password, TLS cert, Key Vault secret and SAS key/token response. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

### Lab 20 — Conduct security acceptance

**Procedure:** Review threat model, network boundaries, monitoring, cost, evidence and independent signoff. Use read-only inventory first; perform active tests only in an approved isolated namespace/cluster with test identities. For any credential/ACL mutation, require GitOps PR, reviewer, rollback and audit ticket.

**Expected outcome:** Evidence shows the intended identity boundary and **positive plus negative authorization behavior**; a denied action must fail safely without impacting other tenants.

**Evidence:** UTC timestamp, AKS/Strimzi/Kafka/CSI/client versions, redacted commands/manifests, expected/observed result, affected principal, broker/client logs, cleanup, owner and reviewer. **Execution state: Pending** until measured.

## 11. Read-only audit script

Save as `verify-ch103.sh`. This validates resource visibility, not real TLS/SASL/ACL enforcement. Never use broad secret dumps.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AKS_RG:?Set AKS resource group}"
: "${AKS_NAME:?Set AKS cluster}"
: "${KAFKA_NS:?Set Kafka namespace}"
: "${APP_NS:?Set app namespace}"
echo '[1/9] Azure identity'; az account show --query '{id:id,tenantId:tenantId}' -o json
echo '[2/9] AKS OIDC/Workload Identity'; az aks show -g "$AKS_RG" -n "$AKS_NAME" --query '{oidc:oidcIssuerProfile.issuerUrl,wi:securityProfile.workloadIdentity}' -o json
echo '[3/9] Kube context'; kubectl config current-context
echo '[4/9] Kafka listeners'; kubectl -n "$KAFKA_NS" get kafka -o name
echo '[5/9] KafkaUser names only'; kubectl -n "$KAFKA_NS" get kafkauser -o name
echo '[6/9] ServiceAccount names'; kubectl -n "$APP_NS" get sa -o name
echo '[7/9] NetworkPolicies'; kubectl -n "$APP_NS" get networkpolicy
echo '[8/9] CSI providers'; kubectl -n "$APP_NS" get secretproviderclass -o name || true
echo '[9/9] Pods'; kubectl -n "$APP_NS" get pods -o wide
echo 'PASS: inventory collected. NOT PROVEN: secret security, auth, ACL enforcement, rotation or live client smoke.'
```

If `SecretProviderClass` CRD is not installed, document the missing dependency instead of assuming Key Vault CSI integration is present.

## 12. Twelve failure scenarios and diagnostic paths

### Scenario 01 — TLS certificate hostname mismatch

**Diagnosis:** Check broker SAN, advertised host, truststore and listener config; never disable validation. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 02 — SCRAM auth fails

**Diagnosis:** Check username, mechanism, generated secret, TLS and KafkaUser readiness. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 03 — mTLS client rejected

**Diagnosis:** Check client certificate chain, validity, principal mapping and KafkaUser reconciliation. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 04 — ACL denies group join

**Diagnosis:** Inspect group READ and topic READ, resource pattern and principal identity. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 05 — ACL denies producer

**Diagnosis:** Inspect topic WRITE/DESCRIBE and transaction/idempotence requirements for client mode. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 06 — Pod cannot fetch Key Vault secret

**Diagnosis:** Check Workload Identity federation, Key Vault RBAC, DNS/private endpoint and CSI status. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 07 — Secret rotated but client still uses old value

**Diagnosis:** Check CSI refresh, app reload/restart strategy and rollout ordering. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 08 — Event Hubs Kafka auth fails

**Diagnosis:** Validate supported SASL mechanism, endpoint, connection string/token and entity authorization. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 09 — Entra token expires midstream

**Diagnosis:** Review token refresh callback, SDK support, clocks and retry policy. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 10 — Kubernetes RBAC exposes Kafka credentials

**Diagnosis:** Inspect Secret read permissions, service-account scope and audit logs. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 11 — External Kafka listener unreachable

**Diagnosis:** Trace AKS LoadBalancer/DNS/firewall/private link and TLS advertised host. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

### Scenario 12 — Monitoring shows healthy brokers but clients fail

**Diagnosis:** Correlate synthetic auth and produce-consume with broker logs and client metrics. Correlate Strimzi Kafka/User reconciliation, AKS Workload Identity, Kubernetes RBAC, Key Vault access logs, client TLS/SASL errors and Kafka authorizer denials. **Containment:** stop unsafe changes; preserve sanitized logs, revoke only the affected identity and maintain healthy tenant traffic. **Recovery:** re-run authorized positive/negative smoke; record SLO and owner signoff.

## 13. Eight SRE/security runbooks

### Runbook A — Compromised Kafka SCRAM credential

**Trigger and response:** Contain principal, rotate secret, restrict ACLs and reconcile affected clients. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook B — Kafka broker/client certificate expiry

**Trigger and response:** Stage trust chain, rotate certificates and verify authenticated client SLO. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook C — AKS Workload Identity failure

**Trigger and response:** Trace OIDC federation, SA annotation, role scope, Key Vault and token exchange. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook D — Event Hubs SAS key compromise

**Trigger and response:** Revoke/rotate keys with staged client migration and audit. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook E — Unauthorized Kafka topic access

**Trigger and response:** Inspect principal, ACL/RBAC grants, broker auth logs and least-privilege correction. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook F — Key Vault/CSI outage

**Trigger and response:** Preserve running clients, assess cached secrets, avoid plaintext fallback and restore. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook G — Cross-namespace tenant isolation breach

**Trigger and response:** Contain Secret/RBAC/network exposure, audit logs and tenant boundary review. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

### Runbook H — Security acceptance and rotation game day

**Trigger and response:** Verify auth, denied actions, TLS, observability, rotation, recovery and signoff. **Prerequisites:** approved identity inventory, secure rotation path, escalation contact, backup/recovery, synthetic client and rollback. **Exit:** revoked or restored identity verified, no leaked credentials, producer/consumer correctness, alert health, UTC evidence, RCA and independent review.

## 14. Monitoring and SLO gates

Capture Strimzi operator reconciliation errors, broker authentication/authorization failures (without secrets), client TLS handshake errors, SASL failure rate, Kafka producer/consumer availability, p95/p99 publish latency, consumer lag, Key Vault access failures, certificate expiry and secret rotation age. For Event Hubs, collect Azure Monitor namespace/entity metrics and Kafka client outcomes; do not assume Kafka broker JMX exists.

**Sample acceptance SLOs (illustrative):** ≥99.9% synthetic authenticated produce/consume success during the defined measurement window; zero unauthorized topic/group access; cert renewal tested before expiry; no secret plaintext in Git, logs or evidence. Set real SLOs from service requirements.

## 15. Evidence package

```text
evidence-ch103/
  security-architecture.md
  aks-entra-identity-matrix.md
  workload-identity-federation.md
  keyvault-rbac-private-network.md
  secret-store-csi-review.md
  strimzi-listeners-tls.md
  broker-certificate-chain.md
  kafkauser-mtls.md
  kafkauser-scram.md
  kafka-acl-topic-group.md
  kafka-superusers.md
  kubernetes-rbac.md
  networkpolicy.md
  eventhubs-sas.md
  eventhubs-oauth-support-check.md
  tls-negative-test.md
  produce-consume-ledger.md
  least-privilege-denial.md
  rotation-revocation.md
  independent-security-acceptance.md
  scorecard.md
```

Each file must state **Live** or **Tabletop**, UTC, environment, exact versions, expected/observed behavior, redacted proof, cleanup, owner and independent reviewer. Never store actual keys, JWTs, connection strings or private certificates.

## 16. 100-point security acceptance

| Domain | Points | Critical |
|---|---:|---|
| Identity architecture and Entra/Kafka boundary | 15 | Yes |
| AKS Workload Identity, Key Vault and secret access | 20 | Yes |
| TLS/mTLS and certificate lifecycle | 15 | Yes |
| SCRAM/SASL, Kafka ACLs and tenant isolation | 20 | Yes |
| Event Hubs SAS/OAuth/RBAC compatibility | 10 | Yes |
| Positive/negative client smoke and monitoring | 10 | Yes |
| Rotation, incident runbooks and evidence | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate independently evidenced. **Automatic fail:** plaintext credentials, disabled TLS verification, unauthorized cross-tenant access, broad production superuser, fabricated live test or absent independent security review.

## 17. References and next

- [Strimzi security documentation](https://strimzi.io/documentation/)
- [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Azure Key Vault CSI provider](https://learn.microsoft.com/en-us/azure/aks/csi-secrets-store-driver)
- [Azure Event Hubs for Apache Kafka](https://learn.microsoft.com/en-us/azure/event-hubs/azure-event-hubs-kafka-overview)
- [Apache Kafka security](https://kafka.apache.org/documentation/#security)

**Next:** Chapter 104 — Azure Event Hubs Kafka Compatibility, Limits and Client Migration.

**Verification boundary:** Publication confirms documentation only. Live AKS/Kafka/Key Vault tests, Event Hubs compatibility checks and independent security review remain Pending.
