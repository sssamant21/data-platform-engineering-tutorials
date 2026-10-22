# Chapter 105 — Azure Kafka Producers, Consumers, Topics and Data Pipelines

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (5/10)  
**Primary platform:** AKS/Kubernetes, Strimzi-managed Kafka KRaft  
**Comparison:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 101–104 and shared Kubernetes lab foundation  
**Publication:** Published upon commit · **Live execution:** Pending · **Independent security/technical review:** Pending

> **Safety:** All mutations are isolated to a disposable, approved lab namespace. Confirm cluster context and cloud charges first. Never place secrets in Git or terminal history. Event Hubs compatibility must be validated per client version and tier; Kafka protocol support is not full Kafka feature equivalence.

## 1. Mission and learning outcomes

Operate a complete synthetic event pipeline on AKS using Kubernetes-managed producer and consumer workloads, Strimzi KafkaTopic resources, observable consumer groups, retry and dead-letter strategies, and safe rollback. Compare the portable client subset with Event Hubs without assuming feature parity.

**Acceptance outcomes:** verifiable event identity and ordering, bounded lag, restart recovery, least-privilege access, capacity evidence, and a documented operational go/no-go.

## 2. Architecture

```text
 AKS namespace: kafka-apps
 ┌──────────────────┐    TLS/SASL     ┌──────────────────────────┐
 │ producer Deployment├───────────────►│ Strimzi Kafka KRaft      │
 │ stable event_id/key│               │ KafkaTopic: orders.v1    │
 └──────────────────┘               └─────────────┬────────────┘
                                                   │
 ┌──────────────────┐                  ┌────────────▼────────────┐
 │ DLQ: orders.dlq  │◄──reject────────│ consumer Deployment      │
 │ owner + replay   │                  │ explicit offset commits  │
 └──────────────────┘                  └────────────┬────────────┘
                                                   │
                                       metrics + reconciliation
 Comparison only: AKS client → Azure Event Hubs Kafka endpoint
 ```

**Data contract:** `event_id` (unique UUID), `aggregate_id` (partition key), `event_time` (UTC), `schema_version`, `payload`. Consumers deduplicate using a durable store or transactional business sink; Kafka offsets alone do not provide end-to-end exactly-once effects.

## 3. Prerequisites and safety preflight

```powershell
kubectl config current-context
kubectl auth can-i get pods -n kafka
kubectl get kafka -A
kubectl get kafkatopic -A
kubectl get pods -n kafka -o wide
```

Use the namespace and cluster names discovered above; examples assume a lab Kafka cluster called `lab-kafka` in namespace `kafka`. Confirm the actual bootstrap service with `kubectl get svc -n kafka`. Apply manifests only after reviewing CRD version and the deployed Strimzi release. Do not create or change production topics for these exercises.

## 4. Topic design with Strimzi

The following example assumes Strimzi topic management is enabled and the Kafka cluster label matches `lab-kafka`.

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: orders-v1
  namespace: kafka
  labels:
    strimzi.io/cluster: lab-kafka
spec:
  topicName: orders.v1
  partitions: 6
  replicas: 3
  config:
    retention.ms: 86400000
    min.insync.replicas: 2
```

Save as `orders-topic.yaml`, then validate:

```powershell
kubectl apply --dry-run=server -f orders-topic.yaml
kubectl apply -f orders-topic.yaml
kubectl get kafkatopic orders-v1 -n kafka -o yaml
```

**Safety gates:** Three replicas require at least three suitable brokers; `min.insync.replicas=2` with producer `acks=all` prioritizes durability. A partition increase changes key-to-partition mapping and can disrupt ordering assumptions; partition count cannot simply be reduced in place.

## 5. Producer design

Recommended starting configuration for a Kafka-native lab (verify broker/client versions):

```properties
bootstrap.servers=lab-kafka-kafka-bootstrap.kafka.svc:9093
security.protocol=SSL
acks=all
enable.idempotence=true
retries=2147483647
delivery.timeout.ms=120000
request.timeout.ms=30000
linger.ms=5
compression.type=snappy
max.in.flight.requests.per.connection=5
```

Mount TLS trust and client credentials from Kubernetes Secrets using read-only volumes. Use a KafkaUser and appropriate Strimzi authorization rules; do not disable TLS certificate verification. The port and protocol above are illustrative: inspect actual listener configuration before using them.

For Event Hubs, use a separate, tested SASL_SSL or supported OAuth configuration and provision event hubs through Azure management APIs. Do not copy Kafka-native administration assumptions to Event Hubs.

## 6. Consumer design

```properties
group.id=orders-processor-v1
enable.auto.commit=false
auto.offset.reset=earliest
max.poll.records=250
max.poll.interval.ms=300000
session.timeout.ms=45000
```

Commit an offset only after the business side effect succeeds or after an invalid record is durably quarantined. `auto.offset.reset=earliest` applies only when no valid committed offset exists; it does not reset an established group. Use bounded concurrency, graceful termination, readiness checks, and idempotent sink writes. Scale consumers based on lag and partition count, not CPU alone.

## 7. Kubernetes workload template

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-consumer
  namespace: kafka-apps
spec:
  replicas: 2
  selector:
    matchLabels: {app: orders-consumer}
  template:
    metadata:
      labels: {app: orders-consumer}
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: consumer
          image: registry.example.invalid/orders-consumer@sha256:REPLACE_WITH_VERIFIED_DIGEST
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: lab-kafka-kafka-bootstrap.kafka.svc:9093
            - name: KAFKA_GROUP_ID
              value: orders-processor-v1
          resources:
            requests: {cpu: 250m, memory: 256Mi}
            limits: {cpu: "1", memory: 512Mi}
          volumeMounts:
            - {name: kafka-tls, mountPath: /etc/kafka/tls, readOnly: true}
      volumes:
        - name: kafka-tls
          secret:
            secretName: orders-client-tls
```

This is a **template, not a runnable application image**. Build, scan and publish the synthetic consumer image, supply a verified digest, configure the application to load mounted TLS material, create the namespace and Secret, then perform a server-side dry run. Ensure application code handles SIGTERM, in-flight work, and commit completion.

## 8. End-to-end correctness and DLQ

Producer generates `event_id` and uses `aggregate_id` as the key. Consumer validates schema, processes with a durable deduplication key, and records success. Invalid messages are published to `orders.dlq` with original topic, partition, offset, error class, schema version, event ID and timestamp, avoiding sensitive payload leakage. Only commit source offsets after DLQ acknowledgement. DLQ replay is a separately approved operation with rate limits and audit trail.

Reconcile **unique IDs, duplicates, missing IDs, hash mismatches, out-of-order events per key and final sink effects**. Count equality by itself is insufficient. During dual-write migration, maintain independent checkpoints; do not assume source offsets map to Event Hubs offsets.

## 9. Observability and SLOs

Measure producer error rate, delivery latency, retry rate, record throughput, consumer lag, rebalance rate, processing latency, DLQ growth, duplicate rate and end-to-end reconciliation mismatches. On AKS also inspect pod restarts, throttling, memory, PVC saturation, broker ISR and KRaft health. For Event Hubs compare Azure Monitor throttling, ingress/egress and consumer metrics where supported.

**Example lab objectives (not production guarantees):** successful accepted events ≥99.9%, p99 end-to-end latency <5 s at stated test load, zero unexplained missing event IDs, no unreviewed DLQ growth, and recovery within 10 minutes for controlled pod restarts. Record load and measurement windows.

## 10. Hands-on lab matrix (20)

For each lab, capture context, manifest revision, commands, sanitized output, metrics and rollback result. Do not label PASS without execution evidence.

| # | Lab | Evidence |
|---|---|---|
| 01 | Namespace/RBAC inventory | Capture command, expected output, timestamp, PASS/FAIL |
| 02 | Kafka cluster health | Capture command, expected output, timestamp, PASS/FAIL |
| 03 | Topic CR creation | Capture command, expected output, timestamp, PASS/FAIL |
| 04 | Partition/replication verification | Capture command, expected output, timestamp, PASS/FAIL |
| 05 | Producer configuration | Capture command, expected output, timestamp, PASS/FAIL |
| 06 | Consumer deployment | Capture command, expected output, timestamp, PASS/FAIL |
| 07 | Consumer-group offset baseline | Capture command, expected output, timestamp, PASS/FAIL |
| 08 | Key-based ordering | Capture command, expected output, timestamp, PASS/FAIL |
| 09 | Idempotent producer retries | Capture command, expected output, timestamp, PASS/FAIL |
| 10 | Manual offset commit | Capture command, expected output, timestamp, PASS/FAIL |
| 11 | Consumer scaling | Capture command, expected output, timestamp, PASS/FAIL |
| 12 | Backpressure/load test | Capture command, expected output, timestamp, PASS/FAIL |
| 13 | Pod restart recovery | Capture command, expected output, timestamp, PASS/FAIL |
| 14 | Poison-message DLQ | Capture command, expected output, timestamp, PASS/FAIL |
| 15 | Schema compatibility | Capture command, expected output, timestamp, PASS/FAIL |
| 16 | TLS/auth failure | Capture command, expected output, timestamp, PASS/FAIL |
| 17 | NetworkPolicy isolation | Capture command, expected output, timestamp, PASS/FAIL |
| 18 | Event Hubs connectivity comparison | Capture command, expected output, timestamp, PASS/FAIL |
| 19 | Event ID reconciliation | Capture command, expected output, timestamp, PASS/FAIL |
| 20 | Rollback and evidence review | Capture command, expected output, timestamp, PASS/FAIL |

### Lab execution pattern

1. Verify namespace, service accounts, credentials, network policy and Kafka CR status.
2. Run server-side manifest validation and apply only to the disposable lab.
3. Generate a bounded synthetic batch with stable event IDs and partition keys.
4. Capture producer acknowledgements, consumer commits and downstream deduplication outcomes.
5. Inject only the lab-specific failure; observe lag, retries, DLQ and recovery.
6. Reconcile all IDs and offsets, then revert manifests or restore lab state.

**Suggested read-only commands:**

```powershell
kubectl get deployments,pods -n kafka-apps
kubectl describe deployment orders-consumer -n kafka-apps
kubectl logs deployment/orders-consumer -n kafka-apps --tail=100
kubectl get kafkatopic -n kafka
kubectl get kafka -n kafka
```

## 11. Failure scenarios (12)

| # | Scenario | Response |
|---|---|---|
| 1 | Broker pod unavailable | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 2 | KRaft controller quorum degradation | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 3 | Producer request timeout | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 4 | Consumer group rebalance storm | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 5 | Offset commit failure | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 6 | Retention expiry before replay | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 7 | Schema incompatibility | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 8 | Poison record | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 9 | Partition hot spot | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 10 | TLS credential expiration | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 11 | Event Hubs throttling/quota | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |
| 12 | Network/DNS outage | Diagnose from pod logs, Kafka metrics and event IDs; recover in isolated lab, preserve evidence |

Each scenario requires a trigger, precondition, expected alarm, evidence, safe containment, recovery criterion and post-recovery reconciliation. Never inject disruptive faults into a shared or production cluster.

## 12. SRE runbooks (8)

| # | Runbook | Workflow |
|---|---|---|
| 1 | Producer delivery degradation | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 2 | Consumer lag escalation | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 3 | Poison message containment | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 4 | Topic misconfiguration | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 5 | Credential rotation | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 6 | Event Hubs throttling | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 7 | Partition imbalance | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |
| 8 | Cutover/rollback | Assess impact → collect evidence → contain → approved remediation → validate offsets and IDs → document |

For every runbook document severity, owner, rollback authority, timestamped command log, SLO impact, change record, and a follow-up preventive action.

## 13. Capacity and security controls

Calculate ingress bytes/sec from peak events/sec × encoded record size including protocol overhead; estimate partition hot spots rather than only aggregate throughput. Size brokers and PVCs for retention, replication, headroom and recovery. On Event Hubs, evaluate the purchased tier's ingress/egress, partition, connection, request, retention and networking constraints from current provider documentation. Use managed identity/Entra integration where supported, least-privilege authorization, Key Vault-backed secret rotation and restricted egress. Do not record connection strings in evidence.

## 14. 100-point acceptance assessment

| Gate | Points |
|---|---:|
| AKS/Strimzi health and safe manifests | 15 |
| Topic design and durability | 10 |
| Producer delivery, keys and retries | 15 |
| Consumer commits, scaling and recovery | 15 |
| DLQ and schema governance | 10 |
| End-to-end reconciliation | 15 |
| Observability, SLO and capacity | 10 |
| Security, rollback and review evidence | 10 |
| **Total** | **100** |

**Suggested pass threshold:** ≥85/100, with mandatory zero missing event IDs, no critical security findings, and demonstrated rollback. A written assessment does not constitute a completed runtime certification.

## 15. Evidence template

```yaml
chapter: 105
environment: isolated-aks-lab
cluster_context: REPLACE
strimzi_version: REPLACE
kafka_version: REPLACE
client_version: REPLACE
commit_sha: REPLACE
executed_at_utc: null
lab_results: []
event_ids_sent: null
event_ids_confirmed: null
event_ids_missing: null
dlq_count: null
rollback_test: pending
technical_review: pending
security_review: pending
runtime_certified: false
```

## 16. Cleanup and next chapter

Delete only chapter-owned lab resources after confirming ownership and retention requirements. Never remove a shared Kafka cluster, namespace, PVC or Event Hubs namespace as part of generic cleanup.

**Next:** Chapter 106 — Azure Kafka Observability, Azure Monitor, Prometheus and SLOs.
