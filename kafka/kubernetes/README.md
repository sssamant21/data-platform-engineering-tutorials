# Kubernetes-first Kafka Lab Platform — Chapters 001–120 (101–120 planned)

**Status:** Reference lab design; live execution and security review pending. Chapters 101–120 extend the lab platform to AKS and GKE, and compare Azure Event Hubs Kafka compatibility with Google Cloud Managed Service for Apache Kafka. See [cloud expansion roadmap](../CLOUD-EXPANSION-ROADMAP.md).

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
| 041 | Reliability engineering: producer/consumer SLIs, SLOs, error budgets, multiwindow burn rates, Kafka/KRaft guardrails, ownership and change gates |
| 042 | SLO alerting: multiwindow fast/medium burn, error-budget math, Prometheus rules, Alertmanager routing, telemetry blind spots and GitOps change gates |
| 043 | Incident management: Kafka/KRaft triage, on-call escalation, incident command, synthetic client drills, communications, recovery and blameless postmortems |
| 044 | Toil reduction: Kubernetes read-only CronJobs, RBAC, GitOps safety, SLO and capacity reporting, idempotency, operational readiness and improvement |
| 045 | Part 09 capstone: enterprise SLO governance, Kafka/KRaft/ISR safety, Alertmanager, incident drills, GitOps gates, readiness assessment and signoff |
| 046 | Incident triage: Kafka/KRaft quorum, ISR, Strimzi CRs, Kubernetes Pods/PVCs, TLS/networking, producer/consumer evidence and synthetic drills |
| 047 | Broker/controller failures: KRaft quorum, ISR, Strimzi NodePools, PVC/CSI, disk I/O, replication, producer acknowledgments and safe incident recovery |
| 048 | Producer/consumer failures: callbacks, idempotence, transactions, rebalances, offset commits, lag, freshness, TLS/ACLs and end-to-end ledger reconciliation |
| 049 | Secure connectivity incidents: Kafka listeners, DNS, EndpointSlices, CNI/NetworkPolicy, TLS CA rotation, SASL/SCRAM, mTLS, Kafka ACLs and LB routing |
| 050 | Part 10 capstone: incident command, KRaft/ISR, PVC/CSI, client delivery, secure networking, telemetry, RCA, recovery and independent acceptance |
| 051 | HA architecture: KRaft voter quorum, broker rack/ISR, AZ failure domains, Kubernetes topology/PDB, PVC/CSI resilience, RPO/RTO and readiness |
| 052 | Failover/maintenance: partition leaders, KRaft quorum, ISR recovery, Strimzi rolling safety, PDB, node drain, PVC/CSI and client SLO gates |
| 053 | Multi-zone and cross-region DR: KRaft/ISR AZ placement, PV/CSI topology, MirrorMaker 2 architecture, RPO/RTO watermarks, writer fencing and cutover tabletop |
| 054 | Cross-cluster DR: Strimzi MirrorMaker 2, Kafka Connect tasks, topic mapping, per-partition replication watermarks, consumer checkpoints, offset translation, cutover and failback |
| 055 | Part 11 capstone: primary/secondary KRaft and ISR, multi-AZ/region failure tabletop, MirrorMaker 2, RPO/RTO, writer fencing, DR cutover, failback and acceptance |
| 056 | Kafka Connect: Strimzi KafkaConnect CR, distributed workers, connector/task lifecycle, internal config/offset/status topics, plugin security, REST isolation, DLQ and SLO |
| 057 | Source/sink reliability: Connect offsets, synthetic data ledger, converters, SMTs, task scaling, retries, DLQ, idempotent sink, source/sink freshness and replay |
| 058 | Debezium CDC/DBRE: PostgreSQL WAL/logical slots/publications, MySQL binlog, snapshots, source offsets, schema/tombstones, slot retention alerts, DB failover and sink reconciliation |
| 059 | Schema governance: Avro, Protobuf, JSON Schema, subject naming, compatibility matrix, registry TLS/ACL/HA, Connect converters, Debezium tombstones and registry DR |
| 060 | Part 12 capstone: integrated PostgreSQL WAL/slots, Debezium CDC, Kafka Connect offsets, schema registry, source-to-sink event reconciliation, DBRE capacity, SLO and recovery acceptance |
| 061 | Kafka Streams: Java DSL topology, KStream/KTable, stream tasks, RocksDB state stores, changelog/repartition topics, event-time, rebalance, state restore and SLO |
| 062 | Kafka Streams: stateless transforms, KStream/KTable joins, repartition topics, aggregations, event-time tumbling/hopping/session windows, grace, late records and correctness SLO |
| 063 | Kafka Streams: RocksDB state stores, changelog/repartition durability, standby tasks, warm/cold restore, ephemeral/PVC storage, compaction, recovery RTO and event integrity |
| 064 | Kafka Streams: exactly_once_v2, Kafka transactions, producer fencing, read_committed visibility, transactional ACL, coordinator, rebalancing, Kubernetes shutdown and event integrity |
| 065 | Kafka Streams capstone: production metrics, lag/freshness SLO, RocksDB/changelog restore, event-time joins/windows, EOS-v2 transactions, fault recovery and independent acceptance |
| 066 | Advanced Strimzi/KRaft: operator reconciliation, KafkaNodePool roles, KRaft quorum, PVCs, TLS/KafkaUser, GitOps source of truth, sync ordering, drift, safe rolling operations |
| 067 | KafkaNodePool operations: controller/broker roles, scheduling, affinity, rack/zone spread, PVC/storage performance, PDB, scaling, safe rolling maintenance and quorum/ISR |
| 068 | Strimzi security: TLS/SASL/OAuth, KafkaUser topic/group/TransactionalId ACLs, NetworkPolicy, Kubernetes RBAC, secrets rotation, tenant quotas and negative authorization tests |
| 069 | Strimzi GitOps: Argo CD/Flux reconciliation, CRD/operator ordering, Git provenance, policy-as-code, drift, staged promotion, prune protection and Kafka-aware rollback |
| 070 | Advanced Strimzi GitOps capstone: KRaft quorum, broker ISR, KafkaNodePool/PVC, tenant security, Argo/Flux release, policy gates, synthetic client SLO and independent acceptance |
| 071 | Amazon MSK with EKS clients: provisioned/serverless architecture, VPC/DNS/SG connectivity, IAM/IRSA/Pod Identity, TLS/SCRAM, CloudWatch, capacity and production administration |
| 072 | Amazon MSK provisioning and operations: broker sizing, Kafka config revisions, RF/minISR, partition placement, storage autoscaling/expansion, broker scaling, version upgrades and EKS client acceptance |
| 073 | Amazon MSK SRE monitoring: CloudWatch/Open Monitoring, broker CPU/network/disk, ISR/offline partitions, consumer lag, EKS client SLO, alerting, scaling diagnosis and incident response |
| 074 | Amazon MSK security/DR: IAM/TLS/SCRAM, EKS identity, cross-VPC and cross-account connectivity, replication, consumer offsets, RPO/RTO, failover/failback and production change controls |
| 075 | Amazon MSK enterprise capstone: EKS connectivity and identity, Kafka RF/minISR, CloudWatch/client SLO, regional replication, RPO/RTO, failover/failback, incident command and independent acceptance |
| 076 | Kafka IaC automation: Terraform AWS/EKS/MSK, GitOps Strimzi CR ownership, remote state, CI validation, policy-as-code, drift, promotion, rollback and authenticated client acceptance |
| 077 | Kafka CI/CD: GitLab pipelines, Terraform/schema validation, OPA/Kyverno, secret/image/SBOM scanning, GitOps sync, Kafka ISR/client smoke, canary SLO and safe rollback |
| 078 | Kafka GitOps drift: Argo CD/Flux diffs, Terraform/Strimzi ownership, safe self-heal, prune prevention, KafkaTopic/NodePool/PVC safety, break-glass, rollback and Kafka client correctness |
| 079 | Kafka automation observability: CI/CD and Terraform metrics, Argo/Flux/Strimzi reconciliation, release SLO, Kafka broker/EKS client event correctness, audit evidence and incident runbooks |
| 080 | Kafka enterprise automation capstone: Terraform state/plan, CI policy and supply-chain scans, GitOps/Strimzi ownership, KRaft quorum/ISR, EKS client correctness, canary rollback, audit and independent acceptance |
| 081 | Kafka capacity planning: compressed ingest, retention/RF storage model, broker disk/CPU/network, partitions/KRaft, consumer drain, AZ failure reserve, Strimzi/MSK scaling and FinOps forecasts |
| 082 | Kafka storage and partition engineering: PVC/CSI, per-partition skew, log segments, compaction, disk IOPS, KRaft metadata, ISR/AZ reserves, Strimzi node-pool and MSK scaling |
| 083 | Kafka performance benchmarking: isolated EKS producers/consumers, P99/throughput, event-ID correctness, partition/CPU/disk/network bottlenecks, KRaft/ISR abort gates, Strimzi/MSK sizing |
| 084 | Kafka reliability-aware FinOps: broker compute, provisioned storage, retention/compaction, AZ transfer, tiered storage, Strimzi/MSK TCO, cost per useful GiB and data/SLO protection |
| 085 | Kafka enterprise capacity/FinOps capstone: demand baseline, broker/partition/PVC sizing, benchmark correctness, KRaft/ISR N-1 and AZ reserve, cloud cost, governance and independent acceptance |
| 086 | Kafka zero-trust security: SASL/TLS/mTLS, ACL least privilege, KRaft controller isolation, Strimzi RBAC, NetworkPolicies, secrets/KMS, MSK IAM, audit and sensitive-data governance |
| 087 | Kafka identity lifecycle: Strimzi KafkaUser, SASL/SCRAM/mTLS, ACL scoping, cert/CA rotation, OAuth/MSK IAM, external secrets, KMS, break-glass and credential incident response |
| 088 | Kafka data governance and privacy: topic ownership, PHI classification, CDC lineage, schemas, retention/compaction, deletion/legal holds, backups, residency, ACLs and compliance evidence |
| 089 | Kafka security observability: broker auth/ACL detection, KRaft and Strimzi drift, Kubernetes/MSK audit, SIEM correlation, anomalous consumers/egress, privacy-safe telemetry and guarded incident automation |
| 090 | Kafka enterprise security capstone: identity/ACL, TLS/KRaft/Strimzi isolation, privacy lineage and retention, threat detection, guarded incident automation and independent security/privacy acceptance |
| 091 | Kafka chaos engineering: isolated failure hypotheses, broker/KRaft/ISR guardrails, AZ and disk failure modeling, PDBs, event correctness, game-day abort/rollback and independent readiness |
| 092 | Kafka broker/partition/KRaft chaos: leader election, ISR/minISR, replica catch-up, controller quorum, Strimzi recovery, broker disk/network faults, acknowledged event ledger and safe rollback |
| 093 | Kafka network/storage/AZ chaos: client/broker latency and packet loss, DNS, EBS/PVC throttling, volume topology, AZ survivability, RF/minISR, KRaft quorum and safe recovery |
| 094 | Kafka streaming pipeline chaos: producer acknowledgements/idempotence, consumer rebalances, Kafka Connect/CDC failures, schema/DLQ, sink backpressure, streaming state and end-to-end event reconciliation |
| 095 | Kafka enterprise chaos capstone: integrated broker/KRaft, ISR/minISR, network/storage/AZ, producer/consumer/Connect/CDC correctness, game-day command, recovery and independent reliability acceptance |
| 096 | Kafka enterprise SRE architecture capstone: KRaft/Strimzi/EKS topology, RF/minISR, private networking, identity/ACL, data governance, Connect/CDC, SLO, DR, GitOps, capacity/FinOps and readiness acceptance |
| 097 | Kafka enterprise platform build: EKS/Strimzi KRaft controllers/brokers, Kafka CRs/topics/users, TLS/ACL, GitOps, synthetic producer/consumer, Connect/CDC, observability and end-to-end smoke reconciliation |
| 098 | Kafka enterprise SRE operations: incident command, KRaft/ISR recovery, producer/consumer/Connect correctness, backup/restore, AZ/region DR, Kafka/Strimzi/EKS upgrades, RPO/RTO and RCA acceptance |
| 099 | Kafka enterprise reliability acceptance: performance/soak, broker/KRaft/ISR chaos, network/storage/AZ resilience, producer/consumer/Connect correctness, clean-room restore, cross-region DR and independent SLO/RPO/RTO gates |
| 100 | Kafka enterprise SRE final assessment: 100-chapter artifact inventory, KRaft/Strimzi/EKS readiness, security/governance, end-to-end streaming correctness, performance/SLO, incident/chaos, DR/upgrades and independent operational certification gates |
| 101 | Azure Kafka architecture: AKS/Strimzi KRaft vs Azure Event Hubs Kafka-compatible endpoint, Azure Disk/AZ, VNet/private networking, identities, client/Connect API compatibility, monitoring, HA/DR and FinOps |
| 102 | Azure AKS Kafka build: VNet/private networking, Workload Identity, Azure Disk CSI/PVC, Strimzi KRaft controllers/brokers, Kafka CR/topics/users, TLS/ACL, monitoring, synthetic clients and readiness acceptance |
| 103 | Azure Kafka identity and secrets: AKS Workload Identity/Entra federation, Key Vault CSI, Strimzi TLS/mTLS, KafkaUser SCRAM, Kafka ACLs, Event Hubs SAS/OAuth compatibility, rotation and negative auth tests |

**References:** [Strimzi documentation](https://strimzi.io/documentation/), [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Kubernetes documentation](https://kubernetes.io/docs/).
