# Chapter 097 — Kafka Enterprise Platform Build, GitOps Deployment and End-to-End Streaming Implementation

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 20 — Final Enterprise SRE Capstone (2/5)  
**Primary platform:** Kubernetes + Strimzi KRaft on Amazon EKS; Amazon MSK alternative  
**Prerequisites:** Chapters 001–096 and an approved disposable EKS lab  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** The commands and manifests in this chapter are templates for a disposable, isolated lab only. Do not apply them to production. Pin and validate Strimzi/Kafka/Kubernetes versions before use. All examples use synthetic IDs, not real healthcare PHI. Confirm explicit context, quotas, RBAC, budget, change approval and rollback before mutation. A published build plan is not evidence that it was deployed.

## 1. Mission and target deliverable

Turn Chapter 096's approved reference architecture into a **GitOps-managed Kafka KRaft streaming platform** on EKS with separated controllers and brokers, durable PVCs, private authenticated listeners, least-privilege Kafka users, synthetic topics, producers/consumers, Kafka Connect, observability, automated smoke validation and independent deployment acceptance.

The chapter distinguishes **build artifacts** from **runtime proof**. No cluster deployment is claimed in this publication.

## 2. End-to-end build architecture

```text
Git repository (reviewed changes + CI policy gates)
      |
      +--> Terraform / EKS and network prerequisites
      +--> GitOps controller (Argo CD or Flux)
                |
           Strimzi operator
                |
         Kafka CR + KafkaNodePools
           /                \
   KRaft controllers       brokers across AZs
                                |
                     TLS/auth + Kafka ACL
                                |
        synthetic producer -> topic -> consumer
                                |          |
                           Kafka Connect  synthetic sink
                                |          |
                          DLQ/schema     event ledger
                                +----------+
                                     |
                            metrics / alerts / audit
                                     |
                        evidence + independent signoff
```

## 3. Repository layout and ownership

```text
kafka-capstone/
  infrastructure/eks/          # reviewed IaC and cost estimate
  platform/strimzi/            # pinned operator installation
  platform/kafka/              # Kafka CR, KafkaNodePools, topics, users
  platform/network/            # namespace and NetworkPolicies
  platform/observability/      # ServiceMonitors, alerts and dashboards
  applications/producer/       # synthetic producer, metrics, tests
  applications/consumer/       # idempotent sink, metrics, tests
  applications/connect/        # approved connector plugin/config
  gitops/                      # Argo CD or Flux app manifests
  tests/                       # policy, smoke, reconciliation
  evidence/                    # sanitized UTC execution proof
```

Require pull requests, signed reviews, secret scans, manifest validation, policy checks, environment overlays and a clear GitOps reconciliation owner.

## 4. EKS and Strimzi prerequisites

- Approved nonproduction EKS context with sufficient CPU, memory, EBS CSI storage, private networking and three AZs if testing AZ resilience.
- Strimzi operator/CRDs installed using an explicitly pinned, supported release.
- Dedicated controller and broker node pools with topology spread and rack-aware broker placement.
- IAM/IRSA or Pod Identity scoped to required AWS resources; no wildcard access.
- Metrics stack, audit logging, secrets provider and change/rollback controls.

Do not mix operator and CRD versions. Validate the Strimzi-supported Kafka version and KRaft mode before creating resources.

## 5. Kubernetes-first sample manifests

These examples illustrate resource structure. They are **not guaranteed compatible with every Strimzi release**; adjust supported Kafka CR schema and image/version settings based on the pinned operator release.

### 5.1 KafkaNodePool controller

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: controllers
  namespace: kafka-capstone-lab
  labels:
    strimzi.io/cluster: capstone-kafka
spec:
  replicas: 3
  roles: [controller]
  storage:
    type: persistent-claim
    size: 20Gi
    deleteClaim: false
```

### 5.2 KafkaNodePool broker

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers
  namespace: kafka-capstone-lab
  labels:
    strimzi.io/cluster: capstone-kafka
spec:
  replicas: 3
  roles: [broker]
  storage:
    type: persistent-claim
    size: 100Gi
    deleteClaim: false
```

### 5.3 Kafka CR skeleton

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: capstone-kafka
  namespace: kafka-capstone-lab
spec:
  kafka:
    # Kafka version, metadataVersion and additional fields must match pinned Strimzi.
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
    config:
      default.replication.factor: 3
      min.insync.replicas: 2
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

**Version caveat:** Exact CR requirements vary with Strimzi releases, including Kafka version fields, node pool enablement and KRaft metadata version. Do not apply the skeleton without schema validation and documented version pinning.

### 5.4 Synthetic Kafka topic

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: synthetic-encounter-events
  namespace: kafka-capstone-lab
  labels:
    strimzi.io/cluster: capstone-kafka
spec:
  partitions: 12
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 604800000
    cleanup.policy: delete
```

### 5.5 Least-privilege producer identity

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: synthetic-producer
  namespace: kafka-capstone-lab
  labels:
    strimzi.io/cluster: capstone-kafka
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: synthetic-encounter-events
          patternType: literal
        operations: [Write, Describe]
        host: "*"
```

**Authorization caveat:** KafkaUser simple ACLs require a supported broker authorization configuration; some versions/configurations need additional broker settings. Wildcard `host` is illustrative, not recommended for broad production access. Producer/consumer/Connect principals should be separate and scoped.

## 6. GitOps deployment sequence

1. Approve isolated environment, pinned versions and namespace quotas.
2. Validate CRDs and install Strimzi operator with supported configuration.
3. Create namespace, EBS storage class prerequisites and controller/broker node pools.
4. Apply Kafka CR; wait for Kafka and KRaft quorum readiness.
5. Apply KafkaTopic and KafkaUser after broker authorization and TLS are validated.
6. Deploy synthetic producer/consumer, Connect, DLQ and sink workloads.
7. Deploy dashboards, alerting and audit collection.
8. Execute synthetic end-to-end reconciliation and record evidence.
9. Review changes and promote only after independent gates pass.

GitOps sync waves/health checks should prevent clients from starting before Kafka users/topics are ready. Avoid competing manual and GitOps ownership of the same resource.

## 7. Producer/consumer reference contract

Each synthetic record should contain `event_id`, `synthetic_subject_id`, `event_time_utc`, `event_type`, `schema_version` and an explicitly non-sensitive payload. Partition by stable synthetic subject ID when per-subject order matters.

Producer: `acks=all`, idempotence enabled, bounded retries, clear error reporting and acknowledged-ID ledger. Consumer: group ID, explicit offset/side-effect ordering, idempotent upsert by `event_id`, lag/freshness metrics and a sink reconciliation endpoint.

Do not assume Kafka producer exactly-once semantics extend automatically to Snowflake, Elasticsearch, Redis or other external sinks.

## 8. Kafka Connect and CDC sandbox

Use a supported, licensed connector plugin pinned to a known version. For CDC, use a disposable database and document WAL/binlog/oplog retention, source snapshot semantics, schema evolution, connector/task offsets and DLQ.

Connector-specific behavior matters: `errors.tolerance=all` can silently skip records without proper DLQ and alerting. Never publish credentials in connector JSON or logs.

## 9. Security, privacy and data lifecycle

Enforce internal TLS, least-privilege Kafka ACLs, scoped Kubernetes RBAC, EKS network segmentation, secrets/KMS rotation, private subnets, schema classification, topic ownership, DLQ encryption and approved retention.

Kafka compaction/tombstones do not guarantee secure erasure of mirrored, cached, backed-up or sink copies. Include data lineage and legal hold approvals.

## 10. Observability and acceptance signals

Measure KRaft controller majority, broker availability, ISR/under-minISR, offline partitions, disk/IOPS, producer ack P99 and error rate, consumer lag/freshness, Connect task health, DLQ count, secret expiry, auth failures and downstream event reconciliation.

Define owner-approved thresholds and SLOs. A running Pod is not proof of Kafka quorum health or end-to-end delivery.

## 11. Read-only preflight and post-deploy inspection

```bash
kubectl config current-context
kubectl get crd | grep kafka.strimzi.io
kubectl get kafka,kafkanodepool,kafkatopic,kafkauser -A
kubectl get pods -A -l strimzi.io/kind=Kafka -o wide
kubectl get pvc -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Commands are read-only and must not be interpreted as deployment evidence until actually executed. Sanitized output should include UTC time, versions and exact context.

## 12. Twenty enterprise platform build labs

### Lab 01 — Establish isolated build prerequisites

**Procedure:** Verify EKS context, permissions, quota, Strimzi compatibility, GitOps and synthetic data boundary.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 02 — Create capstone repository layout

**Procedure:** Define infra, platform, Kafka CRs, apps, policies, tests and evidence folders.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 03 — Provision or select approved EKS lab

**Procedure:** Review dedicated node pools, multi-AZ topology, storage, networking and cost.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 04 — Install and pin Strimzi operator

**Procedure:** Plan CRD/operator version compatibility, namespace, RBAC and deployment checks.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 05 — Define KRaft controller node pool

**Procedure:** Create reviewed isolated KafkaNodePool spec with quorum placement and storage.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 06 — Define broker node pool

**Procedure:** Create reviewed KafkaNodePool broker placement, PVC, resource requests and topology.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 07 — Create Kafka custom resource

**Procedure:** Set supported KRaft settings, internal listeners, replication and observability.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 08 — Verify Kafka quorum and broker readiness

**Procedure:** Check controller majority, Kafka CR status, Pods, PVC and leader/ISR baseline.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 09 — Create namespace and network policies

**Procedure:** Restrict ingress/egress to approved clients, operator, DNS and monitoring.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 10 — Configure KafkaUser and ACLs

**Procedure:** Define least-privilege synthetic producer, consumer and Connect identities.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 11 — Configure TLS and secrets

**Procedure:** Review certificate issuer, rotation, ExternalSecrets and no plaintext credentials.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 12 — Define Kafka topics and schemas

**Procedure:** Create synthetic topic contracts, partition/RF/minISR, retention and DLQ.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 13 — Deploy synthetic producer workload

**Procedure:** Implement unique event IDs, acks=all, idempotence, bounded retry and metrics.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 14 — Deploy synthetic consumer workload

**Procedure:** Implement group offsets, idempotent sink writes, lag and freshness metrics.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 15 — Deploy Kafka Connect/CDC sandbox

**Procedure:** Use synthetic source, restricted plugin, offsets, DLQ and source log safety.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 16 — Deploy synthetic downstream sink

**Procedure:** Use deterministic ID-based materialization and queryable verification.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 17 — Integrate GitOps promotion

**Procedure:** Define Argo CD/Flux ownership, validation, sync waves and drift handling.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 18 — Integrate observability and alerts

**Procedure:** Expose Kafka/Strimzi/client/Connect metrics, ISR/quorum, P99 and lag.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 19 — Run isolated end-to-end smoke validation

**Procedure:** Reconcile acknowledged IDs, sink records, consumer lag and basic restart.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

### Lab 20 — Complete deployment acceptance

**Procedure:** Record manifests, versions, evidence, risk exceptions and independent review.

**Required evidence:** UTC timestamp, explicit isolated context/namespace, Kafka/Strimzi/Kubernetes versions, pinned Git revision, manifest diff/validation, expected/observed, controller quorum, ISR/minISR, synthetic event IDs, rollback, security/privacy review, **Design** vs **Live Executed**, owner and independent reviewer. **Status: Pending** until executed.

## 13. Offline manifest inventory validator

Save as `validate_ch097_manifest_inventory.py`. This checks a **synthetic JSON deployment inventory**; it does not validate CRDs or prove live deployment.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("inventory", help="Reviewed deployment inventory JSON")
args = p.parse_args()
with open(args.inventory, encoding="utf-8") as f:
    d = json.load(f)
required = ["environment", "namespace", "strimzi_version", "kafka_version",
            "git_revision", "controllers", "brokers", "topic_replicas",
            "topic_min_isr", "synthetic_only", "secrets_in_git",
            "controller_quorum_verified", "isr_verified",
            "end_to_end_ids_reconciled", "independent_review", "evidence_ref"]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing: " + ", ".join(missing))
nums = ["controllers", "brokers", "topic_replicas", "topic_min_isr"]
if any(type(d[k]) is not int for k in nums):
    p.error("topology fields must be integers")
checks = {
    "disposable_environment": d["environment"] == "disposable-lab",
    "namespace_scoped": d["namespace"] == "kafka-capstone-lab",
    "version_pinned": bool(d["strimzi_version"] and d["kafka_version"] and d["git_revision"]),
    "controller_quorum": d["controllers"] >= 3 and d["controllers"] % 2 == 1,
    "broker_replication": d["brokers"] >= 3 and 1 <= d["topic_min_isr"] <= d["topic_replicas"] <= d["brokers"],
    "synthetic_data": d["synthetic_only"] is True,
    "no_secrets_in_git": d["secrets_in_git"] is False,
    "quorum_verified": d["controller_quorum_verified"] is True,
    "isr_verified": d["isr_verified"] is True,
    "end_to_end_verified": d["end_to_end_ids_reconciled"] is True,
    "independent_review": d["independent_review"] is True,
    "evidence_reference": bool(d["evidence_ref"])
}
passed = all(checks.values())
print(json.dumps({"checks": checks, "pass": passed}, indent=2))
raise SystemExit(0 if passed else 1)
```

**Limitations:** The validator trusts inventory assertions, does not check Strimzi API compatibility, effective ACLs, actual quorum, AZ placement, PVC health, data correctness or independent signatures. Use live cluster evidence for production readiness.

## 14. Twelve deployment failure scenarios

### Scenario 01 — Strimzi CRD/operator mismatch

**Diagnosis:** Block rollout; pin supported version matrix and reconcile CRDs. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 02 — KRaft controller quorum never forms

**Diagnosis:** Inspect voter IDs, listeners, DNS, scheduling, TLS and storage. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 03 — Broker PVC Pending across AZs

**Diagnosis:** Review storage class topology, PV binding, node placement and quota. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 04 — Kafka custom resource remains NotReady

**Diagnosis:** Inspect Strimzi status, broker logs, quorum, listeners and secrets. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 05 — NetworkPolicy blocks inter-broker replication

**Diagnosis:** Restore only approved ports and verify ISR/quorum. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 06 — KafkaUser ACL denies intended client

**Diagnosis:** Inspect principal, topic/group resource and least-privilege rules. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 07 — TLS handshake fails after secret rotation

**Diagnosis:** Review SAN, CA overlap, issuer and client trust bundle. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 08 — GitOps overwrites emergency remediation

**Diagnosis:** Reconcile desired state, approvals and rollback ownership. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 09 — Producer duplicates after retry

**Diagnosis:** Check idempotence and reconcile unique synthetic IDs. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 10 — Consumer commits offset before sink effect

**Diagnosis:** Review processing/commit order and sink idempotency. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 11 — Connect task crashes or DLQ grows

**Diagnosis:** Inspect task logs, plugin, converter, schema and source/sink offsets. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

### Scenario 12 — Smoke test passes but sink omits IDs

**Diagnosis:** Fail acceptance until independent end-to-end ledger reconciles. Inspect Strimzi operator and Kafka CR status, KRaft quorum, KafkaNodePool/PVC, GitOps desired state, listener/TLS/ACL, producer/consumer/Connect and synthetic sink ledger. **Response:** Stop promotion, preserve durable data, apply reviewed rollback/forward-fix and capture sanitized evidence. **Exit:** Healthy quorum/ISR, secure clients, reconciled synthetic IDs, RCA and independent signoff.

## 15. Eight production platform runbooks

### Runbook A — Preflight and environment isolation

**Trigger/actions:** Verify context, quotas, approvals, synthetic data and rollback. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook B — Strimzi and KRaft deployment recovery

**Trigger/actions:** Inspect CRD/operator, KafkaNodePool, quorum, PVC and supported versions. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook C — Broker/partition and storage readiness

**Trigger/actions:** Validate ISR/minISR, rack placement, capacity and volume health. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook D — Kafka identity and TLS recovery

**Trigger/actions:** Review KafkaUser, ACL, cert trust, secrets and revocation. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook E — GitOps deployment and drift response

**Trigger/actions:** Identify owner, compare desired/live, rollback or forward-fix. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook F — Producer/consumer correctness recovery

**Trigger/actions:** Inspect acknowledgements, offsets, retries, lag and sink ledger. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook G — Connect/CDC and downstream sink recovery

**Trigger/actions:** Protect source retention, task offsets, DLQ and sink idempotence. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

### Runbook H — Platform smoke acceptance and signoff

**Trigger/actions:** Validate evidence, SLO, security gates and independent review. **No-go:** wrong context, unsupported Strimzi version, missing controller majority, unsafe RF/minISR, exposed secrets, real PHI, unexplained acknowledged-ID loss or unapproved change. **Exit:** Validated manifests, healthy Kafka, stable clients/Connect, reconciled synthetic IDs and reviewed evidence.

## 16. Evidence package

```text
evidence-ch097/
  01-build-prerequisites.md
  02-repository-layout.md
  03-eks-lab.md
  04-strimzi-operator.md
  05-kraft-controller-pool.md
  06-broker-pool.md
  07-kafka-cr.md
  08-quorum-isr.md
  09-network-policies.md
  10-kafkauser-acls.md
  11-tls-secrets.md
  12-topics-schemas.md
  13-producer.md
  14-consumer.md
  15-connect-cdc.md
  16-synthetic-sink.md
  17-gitops-promotion.md
  18-observability.md
  19-end-to-end-smoke.md
  20-independent-deployment-review.md
  deployment-inventory.json
  acceptance-scorecard.md
```

Each artifact includes UTC time, exact environment and versions, Git revision, **Design** vs **Live Executed**, expected/observed, resource status, synthetic ledger, security/rollback, exceptions and independent reviewer.

## 17. 100-point enterprise deployment acceptance

| Domain | Points | Critical |
|---|---:|---|
| EKS, Strimzi, KRaft and broker deployment | 25 | Yes |
| TLS, ACL, networking and secrets | 20 | Yes |
| Topics, producers, consumers and event correctness | 20 | Yes |
| Kafka Connect/CDC and sink integration | 15 | Yes |
| GitOps, observability and recovery | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced by approved live deployment. **Automatic Fail:** unsupported version, lost quorum, unsafe replication, exposed credentials/PHI, unauthorized access, missing acknowledged synthetic IDs, no rollback or fabricated evidence.

**Current status:** **Pending**. Manifests and deployment workflow are published, but no live platform build, smoke test or independent review is claimed.

## 18. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html), [Argo CD](https://argo-cd.readthedocs.io/).

**Next:** Chapter 098 — Kafka Enterprise SRE Operations, Incident Response, Backup, Recovery and Upgrade Capstone.

---

**Verification boundary:** Publication confirms document availability only. Live EKS/Strimzi deployment, GitOps promotion, synthetic pipeline correctness, alerts and independent technical/security review remain Pending.
