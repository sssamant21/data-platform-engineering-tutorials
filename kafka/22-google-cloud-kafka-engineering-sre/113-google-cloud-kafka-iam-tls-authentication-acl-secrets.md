# Chapter 113 — Google Cloud Kafka IAM, TLS, Authentication, ACL and Secrets

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (3/10)  
**Primary platform:** GKE + Strimzi Apache Kafka KRaft  
**Comparison:** Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 111–112; approved isolated GCP project, GKE cluster and supported Strimzi installation  
**Publication:** Published; **live labs:** pending; **independent security review:** pending; **runtime certification:** not claimed

> **Safety:** Use synthetic records and disposable identities only. Never expose private keys, tokens, Secret data, healthcare records or production certificates in command output, commits or evidence. Do not rotate live credentials or change production IAM, ACLs or NetworkPolicies from this tutorial. Confirm installed Strimzi release and managed-service authentication documentation before applying examples.

## 1. Learning objectives

Build a defense-in-depth security model for Kafka clients and brokers on GKE: distinguish Google Cloud IAM, Kubernetes RBAC, Kafka authorization and transport identity; establish secure client authentication; integrate secrets without static cloud keys; rehearse rotation and incident response; and document managed Kafka differences.

**Deliverables:** threat model, identity matrix, TLS chain evidence, Kafka ACL matrix, secret lifecycle plan, monitoring and rollback, 20 labs, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Identity and trust architecture

```text
GCP project / IAM / Workload Identity Federation
  └─ GKE namespace and Kubernetes ServiceAccount
      ├─ Kubernetes RBAC controls Kubernetes API
      ├─ Secret Manager / approved secret synchronization
      └─ Kafka client Pod
          ├─ trusted broker CA → TLS encryption/verification
          ├─ client mTLS or supported SASL authentication
          └─ Kafka ACL authorization → topic and group

Strimzi operator → KafkaUser and listener management
Kafka KRaft brokers/controllers → internal authenticated links

Managed Kafka alternative:
  Google-managed broker infrastructure; service-specific
  IAM, authentication, network and authorization capabilities
```

**Important:** GCP IAM permission to read a Secret does **not** grant Kafka topic access. Kubernetes RBAC is not a Kafka ACL. TLS encryption without a configured client authentication mechanism does not establish client identity.

## 3. Threat model and trust boundaries

| Threat | Control | Evidence |
|---|---|---|
| Stolen client credential | Short-lived access where supported, restricted ACL, rotation | Credential inventory and audit |
| Rogue Pod accessing Kafka | Namespace isolation, NetworkPolicy, Kafka authentication | Negative connection test |
| Overprivileged producer | Topic-scoped Kafka ACLs | Denied unauthorized topic write |
| Overprivileged consumer | Topic read and group ACLs | Denied unauthorized group |
| MITM/hostname mismatch | TLS certificate verification and correct advertised DNS | Handshake test |
| Secret exposure in Git/logs | Secret Manager, Git scanning, redaction | Review and alert |
| Cloud identity misuse | Workload Identity Federation, least-privilege IAM | IAM policy audit |

Review encryption at rest, backup encryption, audit retention and data classification separately.

## 4. Read-only preflight

```powershell
gcloud config get-value project
gcloud auth list
gcloud container clusters list
kubectl config current-context
kubectl get namespaces
kubectl get kafka,kafkauser -A
kubectl get serviceaccounts -n kafka
kubectl get role,rolebinding -n kafka
kubectl get networkpolicy -A
kubectl get pods -n kafka -o wide
```

Do not run `kubectl get secret -o yaml` for evidence: base64 is not encryption. Audit Secret names and metadata without disclosing values.

## 5. Workload Identity Federation for GKE

Prefer GKE Workload Identity Federation to downloadable service-account keys. Bind a dedicated Kubernetes ServiceAccount to only the required Google Cloud permissions and validate access using the supported identity model for the installed GKE version. For Secret Manager, grant access to specific secrets, not project-wide secret administrator privileges.

**Reference ServiceAccount:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kafka-client
  namespace: kafka-apps
```

Create via reviewed GitOps and bind to the intended Google identity/principal using the current GKE documentation. Do not assume an IAM service-account annotation is required in every identity mode. Test that authorized Pods can read only approved secrets and unrelated Pods cannot.

## 6. Kafka TLS and mTLS on Strimzi

Strimzi internal TLS listener example (adapt to installed CRD):

```yaml
listeners:
  - name: tls
    port: 9093
    type: internal
    tls: true
    authentication:
      type: tls
```

This is a fragment of `Kafka.spec.kafka.listeners`, not a standalone resource. Configure the client truststore to verify the Strimzi cluster CA and broker hostnames, and use a KafkaUser TLS identity. Never disable hostname verification to make a lab pass.

**KafkaUser reference (lab-only):**

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: orders-producer
  namespace: kafka
  labels:
    strimzi.io/cluster: gke-kafka
spec:
  authentication:
    type: tls
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: gke.orders.v1
          patternType: literal
        operations: [Write, Describe]
        host: "*"
```

Prerequisite: Kafka broker authorization and compatible Strimzi User Operator must be configured; otherwise the ACL declaration alone does not enforce policy. The `host: "*"` entry means any network origin **for this authenticated principal**, so network restrictions still matter. For production, evaluate narrower constraints and separate producer/consumer identities.

## 7. Kafka consumer permissions

A consumer typically needs topic `Read`/`Describe` and group `Read` permissions, plus any additional operation required by the actual client workflow. Use a separate KafkaUser for the consumer. Avoid wildcard topic/group permissions unless justified. Validate **negative tests**: producer cannot read unrelated topics, consumer cannot write to the source topic, and both are denied unauthorized groups.

## 8. Secret Manager and Kubernetes secret delivery

Use an approved external-secrets controller, Secret Manager CSI integration or application runtime retrieval with least-privilege Workload Identity Federation. Verify supported controller versions, refresh behavior, TLS rotation, failure modes and audit logs. Do not embed secret payloads in YAML or shell history.

**Rotation procedure:**
1. Inventory dependent workloads and expiry/renewal window.
2. Create replacement identity or credential without immediately revoking the old one when supported.
3. Update secret source; verify synchronization and application reload behavior.
4. Canary test TLS/authentication and Kafka ACL behavior.
5. Roll clients gradually and monitor failures, retries and lag.
6. Revoke old credential after all clients are confirmed migrated.
7. Record audit evidence and rollback constraints.

For broker CA rotation, use the installed Strimzi version's supported CA lifecycle procedures; client certificate rotation and broker CA rotation have different blast radii.

## 9. Network isolation

Use private VPC routing, approved firewall paths and Kubernetes NetworkPolicies to constrain client access to Kafka bootstrap **and advertised broker addresses**. Ensure CNI/network policy enforcement is enabled in GKE. Account for DNS and operator communications before applying default deny.

**Reference policy for review** (requires adapting Pod labels and ports to actual clients/listeners):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: restrict-kafka-clients
  namespace: kafka-apps
spec:
  podSelector:
    matchLabels:
      app: kafka-client
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kafka
      ports:
        - protocol: TCP
          port: 9093
```

This policy is intentionally incomplete for most deployments: DNS and other required egress may be blocked, and Kafka broker ports/listener exposure can vary. Test against actual DNS, advertised listeners, service topology and platform policy before enforcement.

## 10. Managed Kafka security comparison

For Google Cloud Managed Service for Apache Kafka, verify current supported client authentication, IAM authorization, TLS requirements, private connectivity, credential management and audit logging from service documentation. Do not assume Strimzi KafkaUser CRs or Kubernetes NetworkPolicies control managed brokers. Test client bootstrap, authorization errors and revocation behavior using the exact managed cluster version and supported APIs.

## 11. Monitoring and incident evidence

Alert on certificate expiry, authentication failures, ACL denial spikes, secret synchronization errors, unusual identity access, suspicious client origin and unauthorized configuration changes. Correlate Google Cloud Audit Logs, GKE logs, Strimzi reconciliation and Kafka client errors using UTC timestamps and incident IDs. Redact principals and resource identifiers when necessary; never log credential material.

## 12. Hands-on labs (20)

Each lab requires owner, prerequisites, exact versions, commands, expected/actual result, negative authorization tests, cleanup and PASS/FAIL evidence.

| # | Lab | Evidence |
|---|---|---|
| 01 | GCP identity and project preflight | Sanitized policy/config, test outcome and rollback |
| 02 | GKE Workload Identity Federation review | Sanitized policy/config, test outcome and rollback |
| 03 | Kubernetes RBAC least privilege | Sanitized policy/config, test outcome and rollback |
| 04 | Strimzi listener inventory | Sanitized policy/config, test outcome and rollback |
| 05 | Kafka broker TLS chain inspection | Sanitized policy/config, test outcome and rollback |
| 06 | Create lab KafkaUser mTLS identity | Sanitized policy/config, test outcome and rollback |
| 07 | Kafka ACL least privilege | Sanitized policy/config, test outcome and rollback |
| 08 | Producer authentication smoke test | Sanitized policy/config, test outcome and rollback |
| 09 | Consumer group ACL smoke test | Sanitized policy/config, test outcome and rollback |
| 10 | Negative authorization test | Sanitized policy/config, test outcome and rollback |
| 11 | Secret Manager IAM audit | Sanitized policy/config, test outcome and rollback |
| 12 | External Secrets/CSI integration review | Sanitized policy/config, test outcome and rollback |
| 13 | Credential rotation overlap rehearsal | Sanitized policy/config, test outcome and rollback |
| 14 | Certificate expiry monitoring | Sanitized policy/config, test outcome and rollback |
| 15 | NetworkPolicy namespace isolation | Sanitized policy/config, test outcome and rollback |
| 16 | Private bootstrap and broker DNS test | Sanitized policy/config, test outcome and rollback |
| 17 | Managed Kafka IAM/auth compatibility | Sanitized policy/config, test outcome and rollback |
| 18 | Audit logging and sensitive-data redaction | Sanitized policy/config, test outcome and rollback |
| 19 | Incident credential revocation tabletop | Sanitized policy/config, test outcome and rollback |
| 20 | Security acceptance and cleanup | Sanitized policy/config, test outcome and rollback |

**Lab protocol:** confirm project/context → capture existing access baseline → apply one reviewed lab-only change → test permitted and denied operations → monitor audit/auth errors → restore prior policy → record evidence. Never print Secret values.

## 13. Failure scenarios (12)

| # | Failure | Recovery objective |
|---|---|---|
| 1 | GCP IAM deny | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 2 | Workload Identity binding mismatch | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 3 | Expired broker certificate | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 4 | Missing client trust anchor | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 5 | mTLS identity mismatch | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 6 | Kafka topic ACL deny | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 7 | Consumer group ACL deny | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 8 | Secret sync stale | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 9 | Rotation outage | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 10 | DNS/private network denial | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 11 | Excessive RBAC grant | Identify layer of denial, preserve logs, apply least-privilege fix, retest |
| 12 | Managed Kafka auth mechanism mismatch | Identify layer of denial, preserve logs, apply least-privilege fix, retest |

For each scenario record trigger, scope, severity, expected alerts, recovery timeline, rollback and prevention. Simulate compromise only with disposable credentials.

## 14. SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | IAM access denied | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 2 | Kafka TLS handshake failure | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 3 | Kafka ACL authorization failure | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 4 | Secret sync incident | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 5 | Credential rotation | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 6 | Certificate expiry emergency | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 7 | NetworkPolicy/DNS incident | Triage → preserve audit → contain → approved remediation → verify → RCA |
| 8 | Credential compromise response | Triage → preserve audit → contain → approved remediation → verify → RCA |

Every runbook includes owner, escalation, safe commands, decision points, recovery sign-off and evidence retention.

## 15. 100-point security acceptance

| Gate | Points |
|---|---:|
| GCP IAM and Workload Identity Federation | 15 |
| Kubernetes RBAC and workload isolation | 10 |
| TLS/mTLS and certificate lifecycle | 20 |
| KafkaUser authentication and ACLs | 15 |
| Secret Manager and rotation | 15 |
| NetworkPolicy and private connectivity | 10 |
| Managed Kafka security compatibility | 5 |
| Audit, incident runbooks and evidence | 10 |
| **Total** | **100** |

**Proposed pass:** ≥85/100 plus mandatory denied unauthorized access, validated client identity, no critical security findings, successful credential rotation rehearsal and independent security review. Publication does not certify live security controls.

## 16. Evidence manifest

```yaml
chapter: 113
environment: isolated-gke-lab
gcp_project: REDACTED
gke_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
identity_model: REPLACE
listener_authentication: REPLACE
secret_delivery: REPLACE
lab_results: []
negative_acl_tests: pending
rotation_test: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 17. Next chapter

**Chapter 114 — Google Cloud Managed Service for Apache Kafka Operations and Compatibility.**
