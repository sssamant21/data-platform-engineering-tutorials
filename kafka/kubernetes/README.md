# Kubernetes-first Kafka Lab Platform — Chapters 001–040

**Status:** Reference lab design; live execution and security review pending.

All Kafka labs use **Kubernetes + Strimzi + KRaft** as the primary execution platform. Docker Compose instructions in older revisions are superseded. Use a disposable kind/minikube cluster locally or a dedicated EKS/AKS/GKE namespace with approved storage, IAM and security controls. Do not deploy plaintext examples to production.

## 1. Prepare an isolated Kubernetes cluster

```bash
kubectl config current-context
kubectl get nodes -o wide
kubectl get storageclass
kubectl create namespace kafka-lab --dry-run=client -o yaml | kubectl apply -f -
```

Install **a Strimzi Operator release explicitly compatible with your Kafka version and Kubernetes version**, using that release's official installation procedure and RBAC. Record operator image digest, CRD schema and Kafka version. Do not blindly install the newest Kafka binary against an older Strimzi release.

```bash
kubectl get deployments -A | grep -i strimzi
kubectl get crd | grep -E 'kafkas.kafka.strimzi.io|kafkanodepools.kafka.strimzi.io'
kubectl api-resources | grep -E '^kafkas|^kafkanodepools'
```

## 2. Kafka cluster manifest template

**Compatibility checkpoint:** The following is a reference for a Strimzi release supporting `strimzi.io/v1`, KafkaNodePool, and KRaft. Confirm exact `apiVersion`, required fields, storage syntax and Kafka version in the **installed** operator CRDs and its release examples. Replace `<SUPPORTED_KAFKA_VERSION>` with a Kafka version supported by that Strimzi release. If `strimzi.io/v1` is not supported, use the exact API version supplied by your operator, not a guessed conversion.

Save as `kafka-lab.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: controllers
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  replicas: 3
  roles:
    - controller
  storage:
    type: persistent-claim
    size: 10Gi
    deleteClaim: false
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: brokers
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: persistent-claim
    size: 20Gi
    deleteClaim: false
---
apiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: sre-kafka
  namespace: kafka-lab
spec:
  kafka:
    version: <SUPPORTED_KAFKA_VERSION>
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    config:
      auto.create.topics.enable: false
      default.replication.factor: 3
      min.insync.replicas: 2
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

**Before applying:** validate schema using `kubectl explain kafka.spec --api-version=kafka.strimzi.io/v1` and the matching Strimzi documentation. For older releases, additional KRaft/node-pool annotations or other fields may be required. **Never automatically convert a live cluster between KRaft modes.**

```bash
kubectl apply --dry-run=server -f kafka-lab.yaml
kubectl apply -f kafka-lab.yaml
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
```

**Lab capacity:** six Kafka Pods and six PVCs need adequate worker nodes, CPU, memory, and storage. For single-node kind/minikube, use a separate, explicitly non-HA one-broker/one-controller variant with lower resource demands and do not attempt quorum/failover tests. For chapters 004, 005, 007 and 009, use a multi-worker cluster with independent failure domains and enough resources to host three brokers and three controllers.

## 3. Common administration commands

Create a topic as a Strimzi resource:

```bash
cat > kafka-topic.yaml <<'YAML'
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-lab-events
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
YAML
kubectl apply --dry-run=server -f kafka-topic.yaml
kubectl apply -f kafka-topic.yaml
kubectl -n kafka-lab get kafkatopic sre-lab-events -o yaml
```

Kafka internal bootstrap DNS (same namespace): `sre-kafka-kafka-bootstrap:9092`. Kafka CLI examples use an **ephemeral tools Pod** with a version-matched Kafka image; replace `<SUPPORTED_KAFKA_VERSION>`:

```bash
kubectl -n kafka-lab run kafka-cli --restart=Never \
  --image="apache/kafka:<SUPPORTED_KAFKA_VERSION>" --command -- sleep 3600
kubectl -n kafka-lab wait pod/kafka-cli --for=condition=Ready --timeout=180s
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --topic sre-lab-events
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
```

A Pod running `sleep` may have a `Running` phase without a Ready condition if its image/command is invalid; check `kubectl describe pod` and logs if waiting fails.

Produce and consume:

```bash
printf 'customer-1:created\ncustomer-1:paid\n' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-lab-events --producer-property acks=all \
  --property parse.key=true --property key.separator=:

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-lab-events --from-beginning --max-messages 2
```

## 4. Kubernetes-first failure operations

**Never delete PVCs or KafkaNodePool resources to simulate a restart.** Identify the exact Pod and its role first:

```bash
kubectl -n kafka-lab get pods -o wide
kubectl -n kafka-lab get kafkanodepool
kubectl -n kafka-lab get kafka sre-kafka -o yaml
kubectl -n kafka-lab get events --sort-by=.lastTimestamp | tail -30
```

For a controlled broker fault in an isolated test cluster, select **one broker-role Pod** and record its name, UID, node and leader/ISR state. The Strimzi operator may automatically recreate it:

```bash
BROKER_POD=<EXACT_BROKER_POD_NAME>
kubectl -n kafka-lab delete pod "$BROKER_POD" --wait=false
kubectl -n kafka-lab get pods -w
```

This is an **abrupt Pod failure simulation**, not a graceful rolling restart. For maintenance use Strimzi's documented rolling-update/restart workflow and supported operator mechanisms. Do not stop two controllers, delete Kafka PVCs, or bypass Strimzi reconciliation. After recovery, check `Kafka` Ready condition, topic leaders and ISR, quorum health, client errors and lag.

## 5. Evidence and safety

Capture `kubectl get kafka,kafkanodepool,pods,pvc -o wide`, Strimzi operator logs, Kafka Pod logs, KafkaTopic status, quorum status, topic ISR snapshots, consumer lag and application SLIs. Redact tokens, certificates, private hostnames and business data. A successful `kubectl apply` is **not** evidence of a healthy Kafka deployment.

**Security:** Plaintext listener is for an isolated, trusted local lab only. Production requires supported TLS/authentication, KafkaUser/ACL configuration, Kubernetes RBAC, NetworkPolicies, secrets management, pod security, image provenance, multi-zone placement and tested backup/DR.

## 6. Cleanup

```bash
kubectl -n kafka-lab delete pod kafka-cli --ignore-not-found
kubectl -n kafka-lab delete kafkatopic sre-lab-events --ignore-not-found
```

Do not delete the Kafka cluster or PVCs unless you explicitly intend to destroy this dedicated lab and have retained all needed evidence.

## 7. Chapter mapping

| Chapter | Kubernetes lab emphasis |
|---|---|
| 001 | Strimzi KRaft architecture, CRDs, cluster readiness |
| 002 | KafkaTopic, partitions, keys, offsets and ordering |
| 003 | Producer/consumer workloads in Pods, groups, commits and replay |
| 004 | Three-broker replication, leader/ISR and one broker-Pod fault |
| 005 | End-to-end Kubernetes reliability capstone |
| 006 | Operator installation, KafkaNodePool, PVCs, Services and bootstrap |
| 007 | Controller quorum and metadata status from tools Pod |
| 008 | Kafka config via Strimzi Kafka/KafkaTopic resources; GitOps drift |
| 009 | Operator-managed rolling maintenance and safe Pod fault simulation |
| 010 | Kubernetes-native KRaft installation and reliability acceptance capstone |
| 011 | Broker scheduling, PVC storage, partition and leader placement |
| 012 | KafkaTopic lifecycle, partition sizing, operator reconciliation and retention |
| 013 | Strimzi broker scale-out, throttled reassignment and replica balancing |
| 014 | Replication internals, ISR, single broker-Pod failure and recovery |
| 015 | Brokers, topics, ISR, controlled fault and enterprise reliability acceptance capstone |
| 016 | Producer acks, idempotence, retries, batching and Kubernetes Job execution |
| 017 | Consumer poll loop, group offsets, Kubernetes Job and safe offset reset |
| 018 | Consumer group rebalancing, assignment, Kubernetes Deployment scaling and HPA design |
| 019 | Transactional producers, commit/abort visibility, exactly-once scope and Kubernetes recovery |
| 020 | Producer/consumer reliability, scaling, transactional isolation and Part 04 acceptance capstone |
| 021 | Log segments, retention, Strimzi broker PVCs, storage capacity and disk-pressure reliability |
| 022 | Retention policies, segment lifecycle, replay-window governance and Kubernetes storage capacity |
| 023 | Log compaction, tombstones, keyed-state bootstrap, cleaner metrics and Kubernetes recovery |
| 024 | Tiered storage compatibility, remote log lifecycle, object-store security and Kubernetes DR |
| 025 | Part 05 capstone: retention, compaction, storage headroom, consumer recovery and tiered storage acceptance |
| 026 | Kafka bootstrap/advertised listeners, Kubernetes Services, EndpointSlices, DNS, NetworkPolicies and broker connectivity |
| 027 | TLS and mTLS listeners, certificate chains, KafkaUser identity, Kubernetes Secret renewal and CA rotation |
| 028 | SASL_SSL, SCRAM credentials, OAuth/OIDC identity integration, Kubernetes Secret RBAC and credential rotation |
| 029 | Kafka ACLs, least-privilege authorization, tenant isolation, Kubernetes RBAC/NetworkPolicy and GitOps governance |
| 030 | Part 06 security reliability capstone: DNS/listeners, TLS, SASL, ACL tenant isolation, rotation, incident response and SLO acceptance |
| 031 | Performance fundamentals: producer/consumer benchmarking, throughput and tail latency, partitions, batching, storage and Kubernetes resource saturation |
| 032 | Producer tuning: batching, linger, compression, idempotence, retries, buffer backpressure, secure listeners and Kubernetes CPU/memory sizing |
| 033 | Consumer tuning: fetch sizing/wait, poll/commit safety, group rebalances, partition parallelism, Kubernetes scaling, lag and recovery |
| 034 | Broker tuning: request queues, JVM heap/GC, page cache, network/IO threads, PVC IOPS, CPU throttling, ISR and GitOps rollback |
| 035 | Part 07 capstone: end-to-end producer/broker/consumer benchmarking, capacity acceptance, failure recovery, security gates and GitOps rollback |
| 036 | Observability foundations: JMX exporter, KRaft/controller and operator metrics, Prometheus discovery, Grafana, alerting, RBAC and cardinality |
| 037 | Advanced Kafka metrics: KRaft quorum, ISR, broker request p99, PromQL, producer/consumer lag and event age, Grafana dashboards and metric correctness |
| 038 | Centralized logging: Kafka/KRaft/Strimzi logs, Kubernetes collectors, multiline parsing, secure sinks, audit coverage and incident forensics |
| 039 | OpenTelemetry tracing: Kafka W3C header propagation, producer/consumer spans, collector security, trace/log/metric correlation and event age |
| 040 | Part 08 capstone: Kafka/KRaft metrics, Grafana SLO dashboards, Alertmanager routing, logs/traces, synthetic incident drills and SRE acceptance |

**References:** [Strimzi documentation](https://strimzi.io/documentation/), [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Kubernetes documentation](https://kubernetes.io/docs/).
