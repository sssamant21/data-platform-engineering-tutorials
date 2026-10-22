# Chapter 114 — Google Cloud Managed Service for Apache Kafka Operations and Compatibility

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (4/10)  
**Execution model:** Kubernetes client Pods on GKE; Google Cloud-managed Kafka brokers  
**Prerequisites:** Chapters 111–113, approved GCP project, GKE context, network access and budget  
**Publication:** Published · **Live labs:** Pending · **Independent review:** Pending · **Runtime certification:** Not claimed

> **Safety and accuracy:** Google Cloud Managed Service for Apache Kafka evolves. Verify regional availability, Kafka versions, pricing, API surface, IAM/SASL/TLS requirements, quota and DR behavior using current official documentation and actual service metadata. Never assume every Apache Kafka broker setting or administrative operation is exposed. Use synthetic data and isolated resources; do not provision billable infrastructure without approval.

## 1. Learning outcomes

Operate Google-managed Kafka from a Kubernetes-first SRE perspective. Separate provider-owned broker lifecycle from customer-owned client connectivity, identity, topic governance, event correctness, observability, quotas, cost and recovery. Produce a **verified compatibility matrix** and a defensible go/no-go migration decision.

**Deliverables:** managed versus self-managed responsibility matrix, security/network map, Kafka API test results, synthetic event reconciliation, capacity/SLO evidence, 20 labs, 12 failure scenarios, 8 runbooks and a 100-point acceptance assessment.

## 2. Reference architecture

```text
GCP project / VPC
  GKE application namespaces
    ├─ synthetic producer Deployment
    ├─ idempotent consumer Deployment
    ├─ workload identity + approved credential delivery
    ├─ private DNS and network path
    └─ Prometheus / client metrics
                 |
         TLS + supported authentication
                 |
 Google Cloud Managed Service for Apache Kafka
    ├─ Google-managed broker infrastructure
    ├─ service-exposed administration/quotas
    ├─ Cloud Monitoring and service health
    └─ supported Kafka client interfaces
                 |
         sink checkpoint + DLQ
                 |
      event_id reconciliation
```

A GKE ServiceAccount does not itself authorize Kafka operations. Verify the service's supported authentication and authorization model, principal mapping and exact client configuration.

## 3. Operational responsibility matrix

| Capability | Strimzi Kafka on GKE | Google-managed Kafka |
|---|---|---|
| Broker and controller rollout | Platform team | Provider-managed |
| Kubernetes placement and PVCs | Platform team | Not customer-managed |
| Client Deployments and Pod identity | Application/platform team | Application/platform team |
| Network path and DNS | Customer | Customer plus service endpoint design |
| Topic/data contracts | Customer | Customer |
| Supported topic administration | Kafka/Strimzi tooling | Verify service-supported APIs |
| Metrics and alert ownership | Customer | Shared: service metrics plus client instrumentation |
| Quotas/capacity | VM, disk, broker and partition sizing | Service-specific capacity/quotas |
| Backup/DR | Customer-designed | Validate documented service capabilities |
| Event correctness | Customer | Customer |
| Security incident response | Customer | Shared responsibility and provider escalation |

## 4. Read-only discovery and access validation

Run from PowerShell; replace placeholders and confirm the active account:

```powershell
gcloud config get-value project
gcloud auth list
gcloud services list --enabled --project YOUR_PROJECT_ID
gcloud container clusters list --project YOUR_PROJECT_ID
kubectl config current-context
kubectl get nodes -o wide
kubectl get serviceaccounts -n kafka-apps
kubectl get networkpolicy -n kafka-apps
```

Before relying on any managed Kafka `gcloud` subcommand, confirm it is present in the installed Google Cloud CLI and verify its documented syntax with `gcloud help` and the service's current reference. Capture actual service cluster identifiers, region, supported endpoints, networking, credentials, Kafka version and service quotas. Do not invent endpoint hostnames.

## 5. Kubernetes client configuration

Use a version-pinned Kafka client image deployed as a Kubernetes Job for bounded tests. Mount approved CA certificates and client credentials via Secret Manager integration or a controlled Kubernetes Secret. Never store secrets in a ConfigMap or Git.

Illustrative Job skeleton; **not executable until image, endpoint, auth configuration and namespace are supplied**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kafka-managed-smoke
  namespace: kafka-apps
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      serviceAccountName: kafka-client
      restartPolicy: Never
      containers:
        - name: client
          image: REPLACE_WITH_PINNED_KAFKA_CLIENT_IMAGE
          command: ["/bin/sh", "-c"]
          args:
            - |
              test -f /etc/kafka/client.properties || exit 2
              kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --command-config /etc/kafka/client.properties --list
          env:
            - name: BOOTSTRAP
              value: REPLACE_WITH_VERIFIED_BOOTSTRAP
          volumeMounts:
            - name: client-auth
              mountPath: /etc/kafka
              readOnly: true
      volumes:
        - name: client-auth
          secret:
            secretName: kafka-client-auth
```

This Job is deliberately fail-closed. Verify that the selected image includes the CLI, that client properties use the **service-supported** security protocol, and that the Secret has the expected key. Some managed service configurations may require different identity and credential delivery; adapt only after official compatibility verification.

## 6. Kafka client compatibility matrix

Create one row per actual dependency and label each **verified supported**, **verified unsupported**, or **unknown**. Unknown is a blocker for migration approval when the feature is required.

| Dependency | Test | Decision rule |
|---|---|---|
| Producer `acks`, idempotence | Acknowledged event-ID test | No unexplained loss; supported client config |
| Consumer groups and commits | Restart/rebalance | No missing sink effects |
| Topic creation/configuration | Authorized Admin API smoke test | API and config verified |
| Partition keys and ordering | Per-key sequence validation | Contract preserved |
| Transactions | Supported API and fencing test | Explicitly verify; never assume |
| Log compaction | Topic configuration and semantics | Explicitly verify |
| Kafka Connect | Exact connector/version test | Operationally supported |
| Kafka Streams | Stateful processing and recovery | Explicitly verify |
| ACLs/authentication | Positive and negative tests | Least privilege enforced |
| Retention/replay | Replay from checkpoint | Recovery objective met |
| Schema registry | Compatibility and ID mapping | No schema breakage |
| Cross-region DR | Documented feature and drill | Measured RPO/RTO |

## 7. End-to-end synthetic correctness protocol

1. Create an approved synthetic topic and record partition count and configuration.
2. Generate immutable `event_id`, `aggregate_id`, `sequence`, `schema_version`, and payload hash.
3. Persist the set of successfully acknowledged producer IDs independently.
4. Consume into an idempotent sink; commit offsets only after the sink operation or durable DLQ decision.
5. Compare acknowledged IDs with unique sink IDs, payload hashes, duplicates and per-key order.
6. Repeat after consumer restart and transient network interruption.
7. Record both successful operations and expected denials.

A successful CLI connection is **not** evidence that the application semantics or migration are safe. Kafka offsets in two different clusters are not interchangeable without a tested mapping strategy.

## 8. Performance, quotas and FinOps

Capture events/s, encoded message sizes, partition skew, producer p95/p99, retry rate, consumer lag, network throughput, managed service capacity/quotas, GKE client CPU and memory, and Cloud Monitoring metrics. Identify whether failures are client-side, network, authorization or service quota-related before proposing scaling.

Monthly total cost should include managed Kafka capacity, any separately billed storage/retention, cross-zone/region networking, GKE client compute, logging/metrics, DR and operational support. Use actual region, billing SKU and dated price source; do not invent current pricing.

## 9. Monitoring and incident response

Define alerts for producer failure/error budget, p99 latency, consumer lag, processing backlog, DLQ growth, auth failures, quota throttling and service health. Validate metric names from the deployed service and instrument client applications independently. Record incident timeline in UTC and separate provider-side outages from customer-side configuration errors. For provider incidents, preserve request IDs and escalation evidence without exposing credentials or payloads.

## 10. Hands-on labs (20)

Each lab must have a prerequisite, command or manifest, expected behavior, actual output, cleanup, rollback and timestamped PASS/FAIL. No lab is marked executed by publication.

| # | Lab | Evidence |
|---|---|---|
| 01 | Discover project, regions and quotas | Client/service evidence, compatibility verdict, rollback |
| 02 | Verify GKE client Pod identity | Client/service evidence, compatibility verdict, rollback |
| 03 | Review VPC connectivity and DNS | Client/service evidence, compatibility verdict, rollback |
| 04 | Inspect managed cluster metadata | Client/service evidence, compatibility verdict, rollback |
| 05 | Inspect broker endpoints and certificates | Client/service evidence, compatibility verdict, rollback |
| 06 | Validate supported client authentication | Client/service evidence, compatibility verdict, rollback |
| 07 | Create test topic with supported API | Client/service evidence, compatibility verdict, rollback |
| 08 | Describe topic configuration and partitions | Client/service evidence, compatibility verdict, rollback |
| 09 | Run producer acknowledgement smoke test | Client/service evidence, compatibility verdict, rollback |
| 10 | Run consumer group and offset smoke test | Client/service evidence, compatibility verdict, rollback |
| 11 | Test unauthorized topic operation | Client/service evidence, compatibility verdict, rollback |
| 12 | Verify key ordering with synthetic events | Client/service evidence, compatibility verdict, rollback |
| 13 | Measure throughput and producer p99 | Client/service evidence, compatibility verdict, rollback |
| 14 | Monitor consumer lag and rebalance | Client/service evidence, compatibility verdict, rollback |
| 15 | Review Cloud Monitoring coverage | Client/service evidence, compatibility verdict, rollback |
| 16 | Test client reconnect on transient errors | Client/service evidence, compatibility verdict, rollback |
| 17 | Compare Kafka Admin API support | Client/service evidence, compatibility verdict, rollback |
| 18 | Evaluate Connect/Streams feature dependencies | Client/service evidence, compatibility verdict, rollback |
| 19 | Build migration and rollback decision | Client/service evidence, compatibility verdict, rollback |
| 20 | Cost, incident and evidence acceptance | Client/service evidence, compatibility verdict, rollback |

### Representative smoke-test commands

From an approved Kafka client Pod with service-supported properties:

```bash
kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --command-config /etc/kafka/client.properties --list
kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --command-config /etc/kafka/client.properties --describe --topic managed.lab.events
kafka-consumer-groups.sh --bootstrap-server "$BOOTSTRAP" --command-config /etc/kafka/client.properties --list
```

Each command may be restricted by service policy or authorization; record the exact response and do not treat unsupported operations as evidence of an outage. The topic name is illustrative and must exist before description.

## 11. Failure scenarios (12)

| # | Scenario | Triage and recovery |
|---|---|---|
| 1 | Provisioning quota exhausted | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 2 | Private DNS resolution failure | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 3 | Firewall or route blocks broker | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 4 | Client identity rejected | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 5 | TLS hostname mismatch | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 6 | Topic Admin API unsupported | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 7 | Producer throttled | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 8 | Consumer offset/lag divergence | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 9 | Partition key skew | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 10 | Managed service degraded | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 11 | Schema/Connect incompatibility | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |
| 12 | Migration cutover data mismatch | Identify responsible layer, capture evidence, contain, validate recovery and reconcile IDs |

For each scenario capture severity, blast radius, expected alert, actual metric, escalation, stop condition and preventive action. Run fault injection only against disposable client workloads, not the managed service control plane.

## 12. SRE runbooks (8)

| # | Runbook | Standard workflow |
|---|---|---|
| 1 | Managed Kafka service health triage | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 2 | GKE client connectivity | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 3 | Authentication and authorization | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 4 | Producer throughput/throttling | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 5 | Consumer lag and offsets | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 6 | Topic/configuration change | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 7 | Migration rollback | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |
| 8 | Cost and quota escalation | Confirm impact → read-only evidence → customer/provider boundary → approved mitigation → verify → RCA |

Every runbook needs an owner, escalation path, safe commands, communication plan, rollback, SLO/RPO/RTO impact and evidence retention.

## 13. Migration gates and rollback

Before cutover: freeze topic/data-contract assumptions, approve client and security compatibility, run parallel synthetic tests, capture producer acknowledgement IDs and sink checkpoints, define dual-write risk controls, establish cutover fencing and a verified rollback route. Do not permit uncontrolled dual-active writers. Measure actual recovery objectives and event reconciliation, not just broker reachability.

## 14. 100-point acceptance

| Gate | Points |
|---|---:|
| Managed service responsibility and inventory | 10 |
| Private connectivity and client identity | 15 |
| Authentication and negative authorization | 15 |
| Kafka API and feature compatibility | 20 |
| Producer/consumer correctness | 15 |
| Observability and incident response | 10 |
| Capacity, quotas and FinOps | 5 |
| Migration rollback and evidence | 10 |
| **Total** | **100** |

**Proposed pass:** ≥85/100, no unknown critical API dependency, no unexplained missing acknowledged IDs, no critical security issue, approved rollback and independent review. Publication is not a successful migration test.

## 15. Evidence manifest

```yaml
chapter: 114
environment: isolated-gke-managed-kafka-lab
gcp_project: REDACTED
region: REPLACE
managed_cluster: REPLACE
managed_service_version: REPLACE
client_image_digest: REPLACE
auth_mechanism: REPLACE
compatibility_matrix: []
lab_results: []
accepted_event_ids: null
missing_event_ids: null
quota_observations: []
cost_review: pending
migration_decision: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Next chapter

**Chapter 115 — Google Cloud Kafka Producers, Consumers, Topics and Data Pipelines.**
