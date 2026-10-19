# Apache Kafka Administration, SRE & Platform Engineering

A 100-chapter, production-oriented curriculum for Kafka administrators, SREs, DBREs and platform engineers. Labs target modern KRaft-based Kafka; commands must be tested in isolated environments before production use.

## Kubernetes-first curriculum standard

**Required for every chapter (001–100):** Kubernetes is the primary execution environment. Deploy and administer Apache Kafka in KRaft mode with the Strimzi Operator and Kubernetes custom resources. Use `kubectl`, Kubernetes manifests, Pods, Services, PVCs, StorageClasses, NetworkPolicies, Secrets, and operator-managed rolling operations for the main labs. Local clusters may use kind/minikube; cloud examples should prioritize Amazon EKS and explain AKS/GKE differences where relevant. Prefer supported Strimzi/Kafka version combinations and check the release-specific CRD schema. Production labs require RBAC, TLS/authentication, capacity planning, monitoring, backup and safe rollback. Docker Compose is optional legacy/reference material only, **not** the primary lab platform.

**Migration status:** Chapters 001–009 now include Kubernetes-first Strimzi lab sections and link to the [shared Kubernetes lab foundation](kubernetes/README.md). Their original Docker Compose sections remain marked as superseded historical references; complete replacement/removal of those sections and live validation are pending. Chapter 010 onward must be Kubernetes-native from initial publication. Publication, live lab execution, security review and Kubernetes compliance are separate statuses.

## Curriculum

| Part | Chapters | Theme |
|---|---|---|
| 01 | 001–005 | Kafka Fundamentals and Architecture |
| 02 | 006–010 | Installation, KRaft and Cluster Administration |
| 03 | 011–015 | Brokers, Topics, Partitions and Replication |
| 04 | 016–020 | Producers, Consumers and Consumer Groups |
| 05 | 021–025 | Storage, Retention, Compaction and Tiered Storage |
| 06 | 026–030 | Networking, Security, TLS, SASL and ACLs |
| 07 | 031–035 | Performance Tuning and Benchmarking |
| 08 | 036–040 | Monitoring, Metrics and Observability |
| 09 | 041–045 | SRE, SLIs, SLOs and Reliability |
| 10 | 046–050 | Troubleshooting and Incident Response |
| 11 | 051–055 | High Availability, Failover and Disaster Recovery |
| 12 | 056–060 | Kafka Connect, CDC and Schema Management |
| 13 | 061–065 | Kafka Streams and Streaming Operations |
| 14 | 066–070 | Kubernetes, Strimzi and GitOps |
| 15 | 071–075 | AWS MSK and Managed Kafka Operations |
| 16 | 076–080 | Automation, Terraform and CI/CD |
| 17 | 081–085 | Capacity Planning, Scaling and FinOps |
| 18 | 086–090 | Security, Governance, Compliance and Auditing |
| 19 | 091–095 | Advanced Reliability and Chaos Engineering |
| 20 | 096–100 | Enterprise Kafka SRE Final Capstone |

## Published chapters

- [001 — Kafka Architecture and Distributed Streaming Fundamentals](01-fundamentals-architecture/001-kafka-architecture-and-distributed-streaming-fundamentals.md)
- [002 — Kafka Topics, Partitions, Offsets and Ordering](01-fundamentals-architecture/002-kafka-topics-partitions-offsets-and-ordering.md)
- [003 — Kafka Producers, Consumers and Message Delivery Semantics](01-fundamentals-architecture/003-kafka-producers-consumers-and-message-delivery-semantics.md)
- [004 — Kafka Replication, Leaders, ISR and Fault Tolerance](01-fundamentals-architecture/004-kafka-replication-leaders-isr-and-fault-tolerance.md)
- [005 — Kafka Architecture and Failure Recovery Capstone Lab](01-fundamentals-architecture/005-kafka-architecture-and-failure-recovery-capstone-lab.md)
- [006 — Kafka Installation, Configuration and KRaft Cluster Bootstrap](02-installation-kraft-cluster-administration/006-kafka-installation-configuration-and-kraft-cluster-bootstrap.md)
- [007 — KRaft Controller Quorum Architecture, Metadata Log and Controller Operations](02-installation-kraft-cluster-administration/007-kraft-controller-quorum-architecture-metadata-log-and-controller-operations.md)
- [008 — Kafka Broker Configuration, Dynamic Settings and Cluster Administration](02-installation-kraft-cluster-administration/008-kafka-broker-configuration-dynamic-settings-and-cluster-administration.md)
- [009 — Kafka Broker Lifecycle, Rolling Restarts, Maintenance and Upgrade Operations](02-installation-kraft-cluster-administration/009-kafka-broker-lifecycle-rolling-restarts-maintenance-and-upgrade-operations.md)

- [010 — Enterprise Kafka on Kubernetes: KRaft Cluster Administration and Reliability Acceptance Capstone](02-installation-kraft-cluster-administration/010-enterprise-kafka-on-kubernetes-kraft-cluster-administration-reliability-acceptance-capstone.md)

- [011 — Kafka Brokers, Kubernetes Scheduling, Storage and Partition Placement](03-brokers-topics-partitions-replication/011-kafka-brokers-kubernetes-scheduling-storage-and-partition-placement.md)

- [012 — Kafka Topic Administration, Partition Design and Kubernetes Operator Management](03-brokers-topics-partitions-replication/012-kafka-topic-administration-partition-design-and-kubernetes-operator-management.md)

- [013 — Kafka Partition Reassignment, Replica Balancing and Kubernetes Broker Scaling](03-brokers-topics-partitions-replication/013-kafka-partition-reassignment-replica-balancing-and-kubernetes-broker-scaling.md)

- [014 — Kafka Replication Internals, ISR Management and Kubernetes Failure Recovery](03-brokers-topics-partitions-replication/014-kafka-replication-internals-isr-management-and-kubernetes-failure-recovery.md)

## Chapter quality standard

Each chapter includes learning objectives, architecture, technical explanations, runnable isolated labs, validation and automated checks, failure scenarios, troubleshooting, production runbooks, and assessment. Production changes require review and backups. Lab execution and security review are tracked separately from publication.

See [STATUS.md](STATUS.md) for publication and verification status.
