# Chapter 115 — Google Cloud Kafka Producers, Consumers, Topics and Data Pipelines

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 22 — Google Cloud Kafka Engineering & SRE (5/10)  
**Primary execution:** Kubernetes producer/consumer Deployments and Jobs on GKE  
**Kafka backends:** Strimzi-managed Kafka KRaft or Google Cloud Managed Service for Apache Kafka  
**Prerequisites:** Chapters 111–114, isolated GKE cluster, approved Kafka backend, working TLS/authentication  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending · **Runtime certification:** Not claimed

> **Safety:** Use synthetic data only. Never ingest real patient information, credentials or regulated payloads into tutorial topics. Do not run replay, topic deletion, retention reduction, partition expansion or offset reset against production. Verify managed-service compatibility, current API support and actual quotas before use.

## 1. Mission and learning outcomes

Implement a reproducible Kafka pipeline on GKE, prove producer acknowledgement and consumer processing semantics, manage topics and partition keys, handle poison records and schema changes, and verify correctness through event-ID reconciliation. Compare self-managed and managed Kafka backends without assuming identical administration or configuration.

**Deliverables:** topic contract, deployment manifests, producer/consumer config, durable sink and DLQ design, observability, recovery playbook, 20 hands-on labs, 12 failure scenarios, 8 runbooks and 100-point acceptance.

## 2. Kubernetes-first pipeline architecture

```text
GKE namespace kafka-apps
  synthetic-event-producer Job/Deployment
       | key=aggregate_id, event_id, schema_version
       | acks=all, idempotent producer, bounded retries
       v
Kafka topic: synthetic.patient-events.v1
  backend A: GKE Strimzi KRaft
  backend B: Google Cloud Managed Kafka (verified APIs)
       |
  consumer group on GKE
       | validate schema + event ID
       ├── durable idempotent sink → commit offset
       └── durable DLQ/quarantine → commit only after quarantine
       |
  reconciliation: accepted IDs vs sink/DLQ
       |
  Prometheus / Cloud Monitoring / SLO alerts
```

**Delivery semantics:** Kafka producer idempotence helps avoid duplicate records from retried sends within its supported guarantees. It does not by itself provide exactly-once effects in an external database. Use an idempotency key or transactional sink and commit offsets after durable processing. Treat DLQ records as unresolved business outcomes until reviewed.

## 3. Topic and partition design

Use a stable topic naming convention, explicit owner, retention, partition count, expected event size, schema contract and lifecycle policy. Choose `aggregate_id` as the key when per-aggregate ordering matters; events with different keys may be processed out of order.

**Strimzi KafkaTopic reference** (requires compatible CRD and at least three brokers):

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: synthetic-patient-events-v1
  namespace: kafka
  labels:
    strimzi.io/cluster: gke-kafka
spec:
  topicName: synthetic.patient-events.v1
  partitions: 6
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

Do **not** apply this CR to managed Kafka; use only its documented supported administration interface. Increasing partitions can alter key-to-partition mapping for future records. Retention is not a backup mechanism.

## 4. Producer reliability

Recommended starting point for the lab: `acks=all`, `enable.idempotence=true`, `retries` enabled with bounded delivery timeout, appropriate `max.in.flight.requests.per.connection`, batching and compression tuned from measurements. Producer settings must be checked against the exact client library version and backend. Acknowledgement does not prove the event reached the downstream sink.

**Synthetic event contract:**

```json
{
  "event_id": "lab-000001",
  "aggregate_id": "synthetic-subject-0001",
  "sequence": 1,
  "schema_version": 1,
  "event_time": "2026-10-22T00:00:00Z",
  "event_type": "synthetic.visit.recorded",
  "payload": {"facility_code": "LAB", "category": "test"}
}
```

Record `event_id`, key, payload hash, producer acknowledgement status and timestamp outside Kafka for reconciliation. No actual PHI is required.

## 5. Consumer processing and offset discipline

Consumers must handle rebalance, partition revocation, backpressure, poison records, shutdown and replay. For external sinks, turn off automatic offset commit when implementing manual durable processing.

```text
poll batch
  for each record:
    validate schema and idempotency key
    if already applied: treat as success
    else persist sink effect durably
    on permanent validation error: persist durable DLQ entry
  commit only offsets whose preceding records are durably resolved
```

**Caution:** Offset commits are per topic partition. Do not commit past an unresolved earlier record in that partition. On rebalance, stop accepting new work for revoked partitions, finish or safely abandon in-flight records and commit only completed offsets.

## 6. GKE Deployment skeleton

Version-pin the image digest and supply approved TLS/auth settings using Secrets. This is a configuration template, not a working application image:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: synthetic-kafka-consumer
  namespace: kafka-apps
spec:
  replicas: 2
  selector:
    matchLabels:
      app: synthetic-kafka-consumer
  template:
    metadata:
      labels:
        app: synthetic-kafka-consumer
    spec:
      serviceAccountName: kafka-client
      terminationGracePeriodSeconds: 60
      containers:
        - name: consumer
          image: REPLACE_WITH_PINNED_IMAGE_DIGEST
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: REPLACE_WITH_VERIFIED_BOOTSTRAP
            - name: KAFKA_TOPIC
              value: synthetic.patient-events.v1
            - name: KAFKA_GROUP_ID
              value: synthetic-sink-v1
            - name: KAFKA_ENABLE_AUTO_COMMIT
              value: "false"
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              memory: 512Mi
```

Add probes, metrics, client certificate mounts, topology spread and PodDisruptionBudget only after validating actual application behavior. Environment variable names are application-specific; the image must implement them.

## 7. CLI smoke test

Run from an approved Kafka client Pod that has the required CLI tools and an authenticated `client.properties` file:

```bash
kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --command-config /etc/kafka/client.properties --describe --topic synthetic.patient-events.v1
kafka-consumer-groups.sh --bootstrap-server "$BOOTSTRAP" --command-config /etc/kafka/client.properties --describe --group synthetic-sink-v1
```

Some commands may require topic/group existence and Admin API permissions. Managed Kafka must be checked for API support. A healthy consumer group alone does not prove end-to-end correctness.

## 8. DLQ and schema governance

Define an explicit schema version and compatibility policy. Validate events before business processing; send permanently invalid events to a durable DLQ with original topic/partition/offset, error class, event ID and sanitized metadata. Do not include credentials or PHI in the DLQ. Retry transient failures with bounded backoff; never spin indefinitely on poison records. Use an owner-approved replay process with deduplication and audit trail.

## 9. Performance and SLO engineering

Measure accepted event rate, failed sends, p50/p95/p99 acknowledgement latency, consumer processing p99, max lag, rebalance frequency, partition skew, DLQ rate, duplicate effects and missing accepted IDs. Test steady state, burst, broker/client restart and slow sink. Compare GKE CPU/memory with Kafka broker or managed-service quota signals. Set alerts on both technical lag and business processing delay.

## 10. Hands-on labs (20)

Each lab needs exact image/client versions, prerequisites, commands, expected and observed outputs, timestamped evidence, rollback and PASS/FAIL. No lab is marked executed by publication.

| # | Lab | Evidence |
|---|---|---|
| 01 | Verify GKE and broker connectivity | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 02 | Review topic naming and retention | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 03 | Create synthetic source topic | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 04 | Inspect partition assignment and leaders | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 05 | Configure producer acks and idempotence | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 06 | Generate deterministic synthetic event IDs | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 07 | Verify per-key ordering | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 08 | Measure producer retries and latency | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 09 | Deploy consumer group on GKE | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 10 | Observe rebalance and assignment | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 11 | Implement idempotent sink behavior | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 12 | Commit offsets after durable sink write | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 13 | Handle poison records and DLQ | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 14 | Replay from safe checkpoint | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 15 | Test bounded backpressure | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 16 | Validate schema compatibility gate | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 17 | Rotate client credentials safely | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 18 | Simulate consumer Pod restart | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 19 | Compare managed and Strimzi backend behavior | Kafka/GKE metrics, event-ID reconciliation, rollback |
| 20 | Reconcile IDs, SLOs and cost evidence | Kafka/GKE metrics, event-ID reconciliation, rollback |

**Lab execution protocol:** verify cluster context and cost scope → baseline topic, ISR and client health → generate bounded synthetic events → apply one controlled test → observe metrics → reconcile accepted IDs with sink and DLQ → restore baseline → record results.

## 11. Failure scenarios (12)

| # | Failure | Recovery requirement |
|---|---|---|
| 1 | Topic authorization denied | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 2 | Partition leader unavailable | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 3 | Producer timeout and retry | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 4 | Hot key partition skew | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 5 | Consumer group rebalance storm | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 6 | Offset commit before sink durability | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 7 | Poison event blocking progress | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 8 | DLQ retention exhausted | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 9 | Schema incompatibility | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 10 | Client TLS certificate expiry | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 11 | Backpressure and retention overrun | Triage client/broker/sink, contain, recover, reconcile and document prevention |
| 12 | Replay duplicate side effects | Triage client/broker/sink, contain, recover, reconcile and document prevention |

Each scenario records severity, blast radius, alert, timeline, affected event IDs, stop condition, rollback and follow-up. Do not perform destructive experiments on shared infrastructure.

## 12. SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | Producer error spike | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 2 | Consumer lag incident | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 3 | Topic/partition degradation | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 4 | DLQ surge | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 5 | Schema rollback | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 6 | Client credential outage | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 7 | Replay and reconciliation | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |
| 8 | Pipeline deployment rollback | Impact → read-only diagnosis → approved mitigation → verify sink correctness → RCA |

Every runbook identifies on-call ownership, safe commands, escalation, RPO/RTO and SLO impact, communication and evidence retention.

## 13. 100-point acceptance

| Gate | Points |
|---|---:|
| Topic contract and partition design | 15 |
| Producer reliability and acknowledgement evidence | 15 |
| Consumer groups and offset correctness | 20 |
| Idempotent sink and DLQ | 20 |
| Schema evolution and replay safety | 10 |
| Kubernetes deployment and security | 10 |
| SLO monitoring, recovery and evidence | 10 |
| **Total** | **100** |

**Proposed pass:** ≥85/100, zero unexplained missing accepted IDs, no unapproved duplicate external effects, durable handling of poison records, no critical security issues and independent review. A passing document review is not runtime certification.

## 14. Evidence manifest

```yaml
chapter: 115
environment: isolated-gke-kafka-pipeline
backend: REPLACE_STRIMZI_OR_MANAGED
gke_context: REPLACE
client_image_digest: REPLACE
topic: synthetic.patient-events.v1
partitions: 6
producer_accepted_ids: null
sink_unique_ids: null
dlq_unresolved_ids: null
missing_accepted_ids: null
duplicate_sink_effects: null
p99_latency_ms: null
max_consumer_lag: null
lab_results: []
technical_review: pending
security_review: pending
runtime_certified: false
```

## 15. Next chapter

**Chapter 116 — Google Cloud Kafka Observability, Cloud Monitoring, Prometheus and SLOs.**
