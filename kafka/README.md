# Apache Kafka Administration, SRE & Platform Engineering

A 120-chapter, production-oriented curriculum for Kafka administrators, SREs, DBREs and platform engineers. Labs target modern KRaft-based Kafka; commands must be tested in isolated environments before production use.

## Kubernetes-first curriculum standard

**Required for every chapter (001–120):** Kubernetes is the primary execution environment. Deploy and administer Apache Kafka in KRaft mode with the Strimzi Operator and Kubernetes custom resources. Use `kubectl`, Kubernetes manifests, Pods, Services, PVCs, StorageClasses, NetworkPolicies, Secrets, and operator-managed rolling operations for the main labs. Local clusters may use kind/minikube; cloud examples should prioritize Amazon EKS and explain AKS/GKE differences where relevant. Prefer supported Strimzi/Kafka version combinations and check the release-specific CRD schema. Production labs require RBAC, TLS/authentication, capacity planning, monitoring, backup and safe rollback. Docker Compose is optional legacy/reference material only, **not** the primary lab platform.

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

- [015 — Kafka Brokers, Topics, Replication and Kubernetes Reliability Acceptance Capstone](03-brokers-topics-partitions-replication/015-kafka-brokers-topics-replication-kubernetes-reliability-acceptance-capstone.md)

- [016 — Kafka Producer Architecture, Acknowledgments, Retries and Idempotence on Kubernetes](04-producers-consumers-consumer-groups/016-kafka-producer-architecture-acknowledgments-retries-and-idempotence-on-kubernetes.md)

- [017 — Kafka Consumer Architecture, Poll Loop, Offset Management and Kubernetes Workload Reliability](04-producers-consumers-consumer-groups/017-kafka-consumer-architecture-poll-loop-offset-management-and-kubernetes-workload-reliability.md)

- [018 — Kafka Consumer Groups, Rebalancing Protocols and Kubernetes Horizontal Scaling](04-producers-consumers-consumer-groups/018-kafka-consumer-groups-rebalancing-protocols-and-kubernetes-horizontal-scaling.md)

- [019 — Kafka Delivery Semantics, Transactions, Exactly-Once Processing and Kubernetes Recovery](04-producers-consumers-consumer-groups/019-kafka-delivery-semantics-transactions-exactly-once-processing-and-kubernetes-recovery.md)

- [020 — Kafka Producer and Consumer Reliability, Kubernetes Scaling and Exactly-Once Acceptance Capstone](04-producers-consumers-consumer-groups/020-kafka-producer-consumer-reliability-kubernetes-scaling-and-exactly-once-acceptance-capstone.md)

- [021 — Kafka Log Segments, Storage Internals, Retention and Kubernetes Persistent Volume Reliability](05-storage-retention-compaction-tiered-storage/021-kafka-log-segments-storage-internals-retention-and-kubernetes-persistent-volume-reliability.md)

- [022 — Kafka Retention Policies, Segment Lifecycle, Storage Capacity and Kubernetes Operational Governance](05-storage-retention-compaction-tiered-storage/022-kafka-retention-policies-segment-lifecycle-storage-capacity-and-kubernetes-operational-governance.md)

- [023 — Kafka Log Compaction, Tombstones, Keyed State Recovery and Kubernetes Reliability](05-storage-retention-compaction-tiered-storage/023-kafka-log-compaction-tombstones-keyed-state-recovery-and-kubernetes-reliability.md)

- [024 — Kafka Tiered Storage, Remote Log Lifecycle, Object Storage Security and Kubernetes Disaster Recovery](05-storage-retention-compaction-tiered-storage/024-kafka-tiered-storage-remote-log-lifecycle-object-storage-security-and-kubernetes-disaster-recovery.md)

- [025 — Kafka Storage Reliability, Retention, Compaction and Tiered Storage Kubernetes SRE Capstone](05-storage-retention-compaction-tiered-storage/025-kafka-storage-reliability-retention-compaction-tiered-storage-kubernetes-sre-capstone.md)

- [026 — Kafka Networking Architecture, Kubernetes Services, Listeners and Broker Connectivity Troubleshooting](06-networking-security-tls-sasl-acls/026-kafka-networking-architecture-kubernetes-services-listeners-and-broker-connectivity-troubleshooting.md)

- [027 — Kafka TLS, Certificate Management, Strimzi Listener Encryption and Kubernetes Secret Rotation](06-networking-security-tls-sasl-acls/027-kafka-tls-certificate-management-strimzi-listener-encryption-and-kubernetes-secret-rotation.md)

- [028 — Kafka SASL Authentication, SCRAM Credentials, OAuth Integration and Kubernetes Identity Operations](06-networking-security-tls-sasl-acls/028-kafka-sasl-authentication-scram-credentials-oauth-integration-and-kubernetes-identity-operations.md)

- [029 — Kafka ACLs, Authorization, Multi-Tenant Isolation and Kubernetes Security Governance](06-networking-security-tls-sasl-acls/029-kafka-acls-authorization-multi-tenant-isolation-and-kubernetes-security-governance.md)

- [030 — Kafka Networking, TLS, SASL and Authorization Kubernetes Security Reliability Capstone](06-networking-security-tls-sasl-acls/030-kafka-networking-tls-sasl-and-authorization-kubernetes-security-reliability-capstone.md)

- [031 — Kafka Performance Fundamentals, Throughput, Latency and Kubernetes Benchmarking](07-performance-tuning-benchmarking/031-kafka-performance-fundamentals-throughput-latency-and-kubernetes-benchmarking.md)

- [032 — Kafka Producer Performance Tuning, Batching, Compression, Idempotence and Kubernetes Workload Optimization](07-performance-tuning-benchmarking/032-kafka-producer-performance-tuning-batching-compression-idempotence-and-kubernetes-workload-optimization.md)

- [033 — Kafka Consumer Performance Tuning, Fetch Optimization, Group Parallelism and Kubernetes Scaling](07-performance-tuning-benchmarking/033-kafka-consumer-performance-tuning-fetch-optimization-group-parallelism-and-kubernetes-scaling.md)

- [034 — Kafka Broker Performance Tuning, JVM, Network, Storage and Kubernetes Resource Optimization](07-performance-tuning-benchmarking/034-kafka-broker-performance-tuning-jvm-network-storage-and-kubernetes-resource-optimization.md)

- [035 — Kafka End-to-End Performance Benchmarking, Capacity Acceptance and Kubernetes SRE Capstone](07-performance-tuning-benchmarking/035-kafka-end-to-end-performance-benchmarking-capacity-acceptance-and-kubernetes-sre-capstone.md)

- [036 — Kafka Observability Architecture, JMX Exporter, Prometheus, Grafana and Kubernetes Monitoring Foundations](08-monitoring-metrics-observability/036-kafka-observability-architecture-jmx-exporter-prometheus-grafana-and-kubernetes-monitoring-foundations.md)

- [037 — Kafka Broker, KRaft, Producer and Consumer Metrics, PromQL and Advanced Grafana Dashboards](08-monitoring-metrics-observability/037-kafka-broker-kraft-producer-consumer-metrics-promql-and-advanced-grafana-dashboards.md)

- [038 — Kafka Centralized Logging, Kubernetes Log Pipelines, Audit Events and Incident Forensics](08-monitoring-metrics-observability/038-kafka-centralized-logging-kubernetes-log-pipelines-audit-events-and-incident-forensics.md)

- [039 — Kafka Distributed Tracing, OpenTelemetry, Client Correlation and End-to-End Streaming Observability](08-monitoring-metrics-observability/039-kafka-distributed-tracing-opentelemetry-client-correlation-and-end-to-end-streaming-observability.md)

- [040 — Kafka Observability, Alerting, SLO Dashboards and Incident Detection SRE Capstone](08-monitoring-metrics-observability/040-kafka-observability-alerting-slo-dashboards-and-incident-detection-sre-capstone.md)

- [041 — Kafka Reliability Engineering, SLIs, SLOs, Error Budgets and Kubernetes Service Ownership](09-sre-slis-slos-reliability/041-kafka-reliability-engineering-slis-slos-error-budgets-and-kubernetes-service-ownership.md)

- [042 — Kafka Reliability Alerting, Multiwindow Burn Rates, Error-Budget Policies and Production Change Gates](09-sre-slis-slos-reliability/042-kafka-reliability-alerting-multiwindow-burn-rates-error-budget-policies-and-production-change-gates.md)

- [043 — Kafka Reliability Incident Management, On-Call Operations, Escalation and Blameless Postmortems](09-sre-slis-slos-reliability/043-kafka-reliability-incident-management-on-call-operations-escalation-and-blameless-postmortems.md)

- [044 — Kafka SRE Toil Reduction, Reliability Automation, Operational Readiness and Continuous Improvement](09-sre-slis-slos-reliability/044-kafka-sre-toil-reduction-reliability-automation-operational-readiness-and-continuous-improvement.md)

- [045 — Kafka Enterprise Reliability, SLO Governance and SRE Operational Readiness Capstone](09-sre-slis-slos-reliability/045-kafka-enterprise-reliability-slo-governance-and-sre-operational-readiness-capstone.md)

- [046 — Kafka Troubleshooting Methodology, Evidence Collection and Kubernetes Incident Triage](10-troubleshooting-incident-response/046-kafka-troubleshooting-methodology-evidence-collection-and-kubernetes-incident-triage.md)

- [047 — Kafka Broker, KRaft Controller, Replication and Storage Failure Troubleshooting](10-troubleshooting-incident-response/047-kafka-broker-kraft-controller-replication-and-storage-failure-troubleshooting.md)

- [048 — Kafka Producer, Consumer, Consumer Group and End-to-End Data Delivery Troubleshooting](10-troubleshooting-incident-response/048-kafka-producer-consumer-consumer-group-and-end-to-end-data-delivery-troubleshooting.md)

- [049 — Kafka Networking, TLS, SASL, ACL and Kubernetes Connectivity Incident Troubleshooting](10-troubleshooting-incident-response/049-kafka-networking-tls-sasl-acl-and-kubernetes-connectivity-incident-troubleshooting.md)

- [050 — Kafka Production Incident Response, Recovery, RCA and Troubleshooting Acceptance Capstone](10-troubleshooting-incident-response/050-kafka-production-incident-response-recovery-rca-and-troubleshooting-acceptance-capstone.md)

- [051 — Kafka High Availability Architecture, Failure Domains and Kubernetes Resilience](11-high-availability-failover-disaster-recovery/051-kafka-high-availability-architecture-failure-domains-and-kubernetes-resilience.md)

- [052 — Kafka Broker Failover, Leader Elections, ISR Recovery and Safe Kubernetes Maintenance](11-high-availability-failover-disaster-recovery/052-kafka-broker-failover-leader-elections-isr-recovery-and-safe-kubernetes-maintenance.md)

- [053 — Kafka Multi-Zone Resilience, Disaster Recovery Architecture, RPO and RTO Engineering](11-high-availability-failover-disaster-recovery/053-kafka-multi-zone-resilience-disaster-recovery-architecture-rpo-and-rto-engineering.md)

- [054 — Kafka Cross-Cluster Replication, MirrorMaker 2, Offset Synchronization and Disaster Recovery Cutover](11-high-availability-failover-disaster-recovery/054-kafka-cross-cluster-replication-mirrormaker2-offset-synchronization-and-disaster-recovery-cutover.md)

- [055 — Kafka High Availability, Cross-Region Failover and Disaster Recovery Simulation Capstone](11-high-availability-failover-disaster-recovery/055-kafka-high-availability-cross-region-failover-and-disaster-recovery-simulation-capstone.md)

- [056 — Kafka Connect Architecture, Distributed Workers and Connector Lifecycle](12-kafka-connect-cdc-schema-management/056-kafka-connect-architecture-distributed-workers-and-connector-lifecycle.md)

- [057 — Kafka Connect Source and Sink Connectors, Data Movement and Production Reliability](12-kafka-connect-cdc-schema-management/057-kafka-connect-source-and-sink-connectors-data-movement-and-production-reliability.md)

- [058 — Change Data Capture with Kafka Connect, Debezium and Database Reliability Engineering](12-kafka-connect-cdc-schema-management/058-change-data-capture-kafka-connect-debezium-database-reliability-engineering.md)

- [059 — Kafka Schema Registry, Avro, Protobuf, JSON Schema and Compatibility Engineering](12-kafka-connect-cdc-schema-management/059-kafka-schema-registry-avro-protobuf-json-schema-compatibility-engineering.md)

- [060 — Kafka Connect, CDC and Schema Management Production Reliability Capstone](12-kafka-connect-cdc-schema-management/060-kafka-connect-cdc-schema-management-production-reliability-capstone.md)

- [061 — Kafka Streams Architecture, Processing Topologies and Stateful Stream Processing](13-kafka-streams-stream-processing/061-kafka-streams-architecture-processing-topologies-stateful-stream-processing.md)

- [062 — Kafka Streams Stateless Processing, Joins, Aggregations and Event-Time Windows](13-kafka-streams-stream-processing/062-kafka-streams-stateless-processing-joins-aggregations-event-time-windows.md)

- [063 — Kafka Streams State Stores, RocksDB, Changelog Topics and Fault-Tolerant Recovery](13-kafka-streams-stream-processing/063-kafka-streams-state-stores-rocksdb-changelog-topics-fault-tolerant-recovery.md)

- [064 — Kafka Streams Exactly-Once Processing, Transactions, Rebalancing and Recovery Engineering](13-kafka-streams-stream-processing/064-kafka-streams-exactly-once-processing-transactions-rebalancing-recovery-engineering.md)

- [065 — Kafka Streams Production Observability, Performance, Failure Recovery and Reliability Acceptance Capstone](13-kafka-streams-stream-processing/065-kafka-streams-production-observability-performance-failure-recovery-reliability-acceptance-capstone.md)

- [066 — Advanced Kafka on Kubernetes: Strimzi Operator Architecture, KRaft and GitOps Foundations](14-advanced-kubernetes-strimzi-gitops/066-advanced-kafka-kubernetes-strimzi-operator-architecture-kraft-gitops-foundations.md)

- [067 — Strimzi KafkaNodePools, Scheduling, Storage, Availability and Production Operations](14-advanced-kubernetes-strimzi-gitops/067-strimzi-kafkanodepools-scheduling-storage-availability-production-operations.md)

- [068 — Strimzi Kafka Security, Network Policies, TLS, Authentication and Multi-Tenant Isolation](14-advanced-kubernetes-strimzi-gitops/068-strimzi-kafka-security-network-policies-tls-authentication-multi-tenant-isolation.md)

- [069 — Strimzi GitOps, Argo CD/Flux, Progressive Delivery and Policy-as-Code](14-advanced-kubernetes-strimzi-gitops/069-strimzi-gitops-argocd-flux-progressive-delivery-policy-as-code.md)

- [070 — Advanced Strimzi GitOps Production Operations and Kubernetes Reliability Acceptance Capstone](14-advanced-kubernetes-strimzi-gitops/070-advanced-strimzi-gitops-production-operations-kubernetes-reliability-acceptance-capstone.md)

- [071 — Amazon MSK Architecture, Networking, IAM and Production Administration](15-amazon-msk-aws-kafka-operations/071-amazon-msk-architecture-networking-iam-production-administration.md)

- [072 — Amazon MSK Provisioning, Broker Configuration, Storage Scaling and Kafka Cluster Operations](15-amazon-msk-aws-kafka-operations/072-amazon-msk-provisioning-broker-configuration-storage-scaling-cluster-operations.md)

- [073 — Amazon MSK Monitoring, Performance, Scaling and SRE Incident Response](15-amazon-msk-aws-kafka-operations/073-amazon-msk-monitoring-performance-scaling-sre-incident-response.md)

- [074 — Amazon MSK Security, Multi-VPC Connectivity, Disaster Recovery and Production Change Management](15-amazon-msk-aws-kafka-operations/074-amazon-msk-security-multi-vpc-connectivity-disaster-recovery-production-change-management.md)

- [075 — Amazon MSK Enterprise SRE Operations, Disaster Recovery and Security Acceptance Capstone](15-amazon-msk-aws-kafka-operations/075-amazon-msk-enterprise-sre-operations-disaster-recovery-security-acceptance-capstone.md)

- [076 — Kafka Infrastructure as Code with Terraform, GitOps and CI/CD Automation](16-automation-terraform-ci-cd/076-kafka-infrastructure-as-code-terraform-gitops-ci-cd-automation.md)

- [077 — Kafka CI/CD Pipelines, Policy-as-Code, Security Scanning and Progressive Delivery](16-automation-terraform-ci-cd/077-kafka-ci-cd-pipelines-policy-as-code-security-scanning-progressive-delivery.md)

- [078 — Kafka GitOps Drift Detection, Automated Reconciliation and Safe Rollback Engineering](16-automation-terraform-ci-cd/078-kafka-gitops-drift-detection-automated-reconciliation-safe-rollback-engineering.md)

- [079 — Kafka Automation Observability, Release Reliability, Compliance Evidence and SRE Runbooks](16-automation-terraform-ci-cd/079-kafka-automation-observability-release-reliability-compliance-evidence-sre-runbooks.md)

- [080 — Kafka Enterprise Automation, GitOps, CI/CD and Reliability Acceptance Capstone](16-automation-terraform-ci-cd/080-kafka-enterprise-automation-gitops-ci-cd-reliability-acceptance-capstone.md)

- [081 — Kafka Capacity Planning, Workload Forecasting and Reliability-Aware Scaling](17-capacity-planning-performance-finops/081-kafka-capacity-planning-workload-forecasting-reliability-aware-scaling.md)

- [082 — Kafka Storage, Partition and Broker Capacity Engineering for Production Workloads](17-capacity-planning-performance-finops/082-kafka-storage-partition-broker-capacity-engineering-production-workloads.md)

- [083 — Kafka Performance Benchmarking, Load Testing and Capacity Validation Engineering](17-capacity-planning-performance-finops/083-kafka-performance-benchmarking-load-testing-capacity-validation-engineering.md)

- [084 — Kafka Cloud Cost Optimization, Storage Lifecycle and Reliability-Aware FinOps](17-capacity-planning-performance-finops/084-kafka-cloud-cost-optimization-storage-lifecycle-reliability-aware-finops.md)

- [085 — Kafka Enterprise Capacity, Performance and FinOps Acceptance Capstone](17-capacity-planning-performance-finops/085-kafka-enterprise-capacity-performance-finops-acceptance-capstone.md)

- [086 — Kafka Enterprise Security Architecture, Zero Trust and Governance Controls](18-security-governance-compliance/086-kafka-enterprise-security-architecture-zero-trust-governance-controls.md)

- [087 — Kafka Identity, Access Management, Secrets and Certificate Lifecycle Engineering](18-security-governance-compliance/087-kafka-identity-access-management-secrets-certificate-lifecycle-engineering.md)

- [088 — Kafka Data Governance, Privacy, Retention and Compliance Engineering](18-security-governance-compliance/088-kafka-data-governance-privacy-retention-compliance-engineering.md)

- [089 — Kafka Security Observability, Threat Detection and Incident Response Automation](18-security-governance-compliance/089-kafka-security-observability-threat-detection-incident-response-automation.md)

- [090 — Kafka Enterprise Security, Governance and Compliance Acceptance Capstone](18-security-governance-compliance/090-kafka-enterprise-security-governance-compliance-acceptance-capstone.md)

- [091 — Kafka Chaos Engineering Foundations, Failure Injection Safety and Game Day Design](19-chaos-engineering-resilience-validation/091-kafka-chaos-engineering-foundations-failure-injection-safety-game-day-design.md)

- [092 — Kafka Broker, Partition and KRaft Failure Injection and Recovery Engineering](19-chaos-engineering-resilience-validation/092-kafka-broker-partition-kraft-failure-injection-recovery-engineering.md)

- [093 — Kafka Network, Storage and Availability Zone Chaos Engineering](19-chaos-engineering-resilience-validation/093-kafka-network-storage-availability-zone-chaos-engineering.md)

- [094 — Kafka Producer, Consumer, Kafka Connect and Streaming Pipeline Chaos Engineering](19-chaos-engineering-resilience-validation/094-kafka-producer-consumer-connect-streaming-pipeline-chaos-engineering.md)

- [095 — Kafka Enterprise Chaos Engineering, Resilience Game Day and Reliability Acceptance Capstone](19-chaos-engineering-resilience-validation/095-kafka-enterprise-chaos-engineering-resilience-game-day-reliability-acceptance-capstone.md)

- [096 — Kafka Enterprise SRE Capstone Architecture, Requirements and Production Readiness](20-final-enterprise-sre-capstone/096-kafka-enterprise-sre-capstone-architecture-requirements-production-readiness.md)

- [097 — Kafka Enterprise Platform Build, GitOps Deployment and End-to-End Streaming Implementation](20-final-enterprise-sre-capstone/097-kafka-enterprise-platform-build-gitops-deployment-end-to-end-streaming-implementation.md)

- [098 — Kafka Enterprise SRE Operations, Incident Response, Backup, Recovery and Upgrade Capstone](20-final-enterprise-sre-capstone/098-kafka-enterprise-sre-operations-incident-response-backup-recovery-upgrade-capstone.md)

- [099 — Kafka Enterprise Reliability Validation, Chaos Game Day, Performance and Disaster Recovery Acceptance](20-final-enterprise-sre-capstone/099-kafka-enterprise-reliability-validation-chaos-game-day-performance-disaster-recovery-acceptance.md)

- [100 — Kafka Enterprise SRE Final Assessment, Production Readiness and Operational Certification Capstone](20-final-enterprise-sre-capstone/100-kafka-enterprise-sre-final-assessment-production-readiness-operational-certification-capstone.md)

## Multi-cloud expansion — Chapters 101–120

The original 100 chapters are published. **Part 21 (101–110): Microsoft Azure Kafka** and **Part 22 (111–120): Google Cloud Kafka** are planned, with publication and live validation tracked separately. See [Cloud Expansion Roadmap](CLOUD-EXPANSION-ROADMAP.md) for all 20 chapter titles, architecture choices and quality gates.

- [101 — Azure Kafka Architecture: AKS + Strimzi vs Azure Event Hubs Kafka Endpoint](21-azure-kafka-engineering-sre/101-azure-kafka-architecture-aks-strimzi-vs-azure-event-hubs-kafka-endpoint.md)

## Chapter quality standard

Each chapter includes learning objectives, architecture, technical explanations, runnable isolated labs, validation and automated checks, failure scenarios, troubleshooting, production runbooks, and assessment. Production changes require review and backups. Lab execution and security review are tracked separately from publication.

See [STATUS.md](STATUS.md) for publication and verification status.
