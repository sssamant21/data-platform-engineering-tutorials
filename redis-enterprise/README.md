# Redis Enterprise — Production Engineering Curriculum

**Status:** 80 of 80 chapters published. This index is the navigation entry point for DBRE, SRE, Redis administrators, application engineers, and platform teams.

> **Validation:** Publication does not establish that examples, lab steps, product-version compatibility, or production acceptance have been verified. The [V01 static audit](validation/V01-STATIC-AUDIT-2026-10-30.md) is separate from live Redis testing.

**Start:** [Chapter 01 — Fundamentals & Architecture](01-redis-enterprise-fundamentals-architecture.md) · **Finish:** [Chapter 80 — Production Readiness Acceptance](80-redis-enterprise-final-production-readiness-acceptance-project.md)

**References:** [Master curriculum](MASTER-LAYOUT.md) · [Publication status](STATUS.md) · [Offline review history](REVIEW.md) · [V01 audit report](validation/V01-STATIC-AUDIT-2026-10-30.md)

## Chapter index

### Part 1 — Foundations & Architecture

- **01** — [Redis Enterprise Fundamentals & Architecture](01-redis-enterprise-fundamentals-architecture.md)
- **02** — [Connecting to Redis Enterprise — Clients, Endpoints, TLS & Connection Management](02-connecting-to-redis-enterprise-clients-endpoints-tls-connection-management.md)
- **03** — [Redis Data Types, Key Design & Memory-Aware Data Modeling](03-redis-data-types-key-design-memory-aware-data-modeling.md)
- **04** — [Redis Commands, Command Semantics & Safe Operations](04-redis-commands-command-semantics-safe-operations.md)
- **05** — [Redis Enterprise Databases, Endpoints & Configuration](05-redis-enterprise-databases-endpoints-configuration.md)
- **06** — [Redis Enterprise Nodes, Shards, Proxies & Placement](06-redis-enterprise-nodes-shards-proxies-placement.md)
- **07** — [Hash Slots, Key Distribution & Sharding Internals](07-hash-slots-key-distribution-sharding-internals.md)
- **08** — [Replication Architecture & Primary/Replica Behavior](08-replication-architecture-primary-replica-behavior.md)
- **09** — [Redis Enterprise Administration Interfaces — UI, rladmin & REST API](09-redis-enterprise-administration-interfaces-ui-rladmin-rest-api.md)
- **10** — [Architecture Inspection & Foundation Acceptance Lab](10-architecture-inspection-foundation-acceptance-lab.md)

### Part 2 — Caching & Application Engineering

- **11** — [TTL, Expiration & Cache Freshness Engineering](11-ttl-expiration-cache-freshness-engineering.md)
- **12** — [Cache-Aside Pattern](12-cache-aside-pattern.md)
- **13** — [Cache Updates, Invalidation & Consistency](13-cache-updates-invalidation-consistency.md)
- **14** — [Write-Through, Write-Behind & Read-Through Patterns](14-write-through-write-behind-read-through-patterns.md)
- **15** — [Cache Stampede, Thundering Herd & Source Protection](15-cache-stampede-thundering-herd-source-protection.md)
- **16** — [Cache Warming, Refresh-Ahead & Cold-Start Engineering](16-cache-warming-refresh-ahead-cold-start-engineering.md)
- **17** — [Redis Eviction Policies, Memory Pressure & Cache Survival Engineering](17-redis-eviction-policies-memory-pressure-cache-survival-engineering.md)
- **18** — [Redis Hot Keys, Big Keys & Workload Skew Engineering](18-redis-hot-keys-big-keys-workload-skew-engineering.md)
- **19** — [Redis TTL Strategy, Expiration Engineering & Data Freshness](19-redis-ttl-strategy-expiration-engineering-data-freshness.md)
- **20** — [Redis Cache Invalidation, Consistency & Change Propagation](20-redis-cache-invalidation-consistency-change-propagation.md)

### Part 3 — Application Reliability & Command Engineering

- **21** — [Redis Pipelining, Batching & Round-Trip Optimization](21-redis-pipelining-batching-round-trip-optimization.md)
- **22** — [Redis Transactions, WATCH & Atomic Update Patterns](22-redis-transactions-watch-atomic-update-patterns.md)
- **23** — [Redis Lua Scripting & Server-Side Atomic Logic](23-redis-lua-scripting-server-side-atomic-logic.md)
- **24** — [Redis Distributed Locks, Leases & Coordination Patterns](24-redis-distributed-locks-leases-coordination-patterns.md)
- **25** — [Redis Rate Limiting, Quotas & Traffic Protection](25-redis-rate-limiting-quotas-traffic-protection.md)
- **26** — [Redis Connection Management, Pooling & Client Reliability](26-redis-connection-management-pooling-client-reliability.md)
- **27** — [Redis Pipelining, Batching & High-Throughput Command Engineering](27-redis-pipelining-batching-high-throughput-command-engineering.md)
- **28** — [Redis Serialization, Compression & Value-Size Engineering](28-redis-serialization-compression-value-size-engineering.md)
- **29** — [Redis Key Naming, Namespaces & Keyspace Design](29-redis-key-naming-namespaces-keyspace-design.md)
- **30** — [Redis Multi-Tenancy, Isolation & Noisy-Neighbor Engineering](30-redis-multi-tenancy-isolation-noisy-neighbor-engineering.md)

### Part 4 — Messaging, Persistence, HA & Geo

- **31** — [Redis Pub/Sub, Messaging & Real-Time Event Delivery](31-redis-pubsub-messaging-real-time-event-delivery.md)
- **32** — [Redis Streams, Consumer Groups & Durable Event Processing](32-redis-streams-consumer-groups-durable-event-processing.md)
- **33** — [Redis Streams Reliability, Retry, DLQ & Recovery Engineering](33-redis-streams-reliability-retry-dlq-recovery-engineering.md)
- **34** — [Redis Persistence: RDB, AOF & Durability Engineering](34-redis-persistence-rdb-aof-durability-engineering.md)
- **35** — [Redis Replication, High Availability & Failover Engineering](35-redis-replication-high-availability-failover-engineering.md)
- **36** — [Redis Backup, Restore & Disaster Recovery Engineering](36-redis-backup-restore-disaster-recovery-engineering.md)
- **37** — [Redis Enterprise Active-Active, Geo-Distribution & Multi-Region Engineering](37-redis-enterprise-active-active-geo-distribution-multi-region-engineering.md)

### Part 5 — Security

- **38** — [Redis Enterprise Security, Authentication, Authorization & TLS Engineering](38-redis-enterprise-security-authentication-authorization-tls-engineering.md)

### Part 6 — Observability, Reliability, Change & Governance

- **39** — [Redis Enterprise Observability, Metrics, Alerting & SLO Engineering](39-redis-enterprise-observability-metrics-alerting-slo-engineering.md)
- **40** — [Redis Enterprise Performance Troubleshooting & Production Incident Engineering](40-redis-enterprise-performance-troubleshooting-production-incident-engineering.md)
- **41** — [Redis Enterprise Capacity Planning, Scaling & Resource Engineering](41-redis-enterprise-capacity-planning-scaling-resource-engineering.md)
- **42** — [Redis Enterprise Upgrades, Maintenance & Change Engineering](42-redis-enterprise-upgrades-maintenance-change-engineering.md)
- **43** — [Redis Enterprise Automation, APIs, CLI & Infrastructure-as-Code Engineering](43-redis-enterprise-automation-api-cli-iac-engineering.md)
- **44** — [Redis Enterprise Governance, Standards & Operational Readiness Engineering](44-redis-enterprise-governance-standards-operational-readiness-engineering.md)

### Part 7 — Platform, Cloud & Database Service Operations

- **45** — [Redis Enterprise Kubernetes Operations, Scheduling & Platform Engineering](45-redis-enterprise-kubernetes-operations-scheduling-platform-engineering.md)
- **46** — [Redis Enterprise Cloud Infrastructure, Networking & Storage Engineering](46-redis-enterprise-cloud-infrastructure-networking-storage-engineering.md)
- **47** — [Redis Enterprise Database Lifecycle, Provisioning & Configuration Engineering](47-redis-enterprise-database-lifecycle-provisioning-configuration-engineering.md)

### Part 8 — Production Operations

- **48** — [Redis Enterprise Production Readiness, Operational Acceptance & Go-Live Engineering](48-redis-enterprise-production-readiness-operational-acceptance-go-live-engineering.md)
- **49** — [Redis Enterprise Incident Management, RCA & Corrective Action Engineering](49-redis-enterprise-incident-management-rca-corrective-action-engineering.md)
- **50** — [Redis Enterprise SRE Runbooks, Day-2 Operations & Production Operations Handbook](50-redis-enterprise-sre-runbooks-day2-production-operations-handbook.md)

### Part 9 — Integrated Project

- **51** — [Redis Enterprise End-to-End Production Engineering Project](51-redis-enterprise-end-to-end-production-engineering-project.md)

### Part 10 — Migration, Data Services & Advanced Capabilities

- **52** — [Redis Enterprise Data Migration, Import/Export & Cutover Engineering](52-redis-enterprise-data-migration-import-export-cutover-engineering.md)
- **53** — [Redis Enterprise Client SDK Compatibility & Application Integration Engineering](53-redis-enterprise-client-sdk-compatibility-application-integration-engineering.md)
- **54** — [Redis Enterprise Benchmarking, Load Testing & Performance Qualification Engineering](54-redis-enterprise-benchmarking-load-testing-performance-qualification-engineering.md)
- **55** — [Redis Enterprise RedisJSON Data Modeling & Document Engineering](55-redis-enterprise-redisjson-data-modeling-document-engineering.md)
- **56** — [Redis Enterprise Search & Query Architecture, Indexing & Operations](56-redis-enterprise-search-query-architecture-indexing-operations.md)
- **57** — [Redis Enterprise Vector Search, Embeddings & Semantic Retrieval Engineering](57-redis-enterprise-vector-search-embeddings-semantic-retrieval-engineering.md)
- **58** — [Redis Enterprise Vector Search Performance, Capacity & Retrieval Quality Engineering](58-redis-enterprise-vector-search-performance-capacity-retrieval-quality-engineering.md)
- **59** — [Redis Enterprise Modules/Capabilities Lifecycle & Compatibility Engineering](59-redis-enterprise-modules-capabilities-lifecycle-compatibility-engineering.md)
- **60** — [Redis Enterprise Auto Tiering / Flex Architecture & Operations](60-redis-enterprise-auto-tiering-flex-architecture-operations.md)

### Part 11 — Advanced Kubernetes, Active-Active & Platform Engineering

- **61** — [Redis Enterprise Kubernetes Operator Architecture & Reconciliation](61-redis-enterprise-kubernetes-operator-architecture-reconciliation.md)
- **62** — [REC, REDB, RERC & REAADB Resource Administration](62-redis-enterprise-rec-redb-rerc-reaadb-resource-administration.md)
- **63** — [Redis Enterprise Kubernetes Storage, Networking & Failure Engineering](63-redis-enterprise-kubernetes-storage-networking-failure-engineering.md)
- **64** — [Redis Enterprise Kubernetes Upgrade, Backup & Recovery Operations](64-redis-enterprise-kubernetes-upgrade-backup-recovery-operations.md)
- **65** — [Redis Enterprise Active-Active CRDT Semantics & Conflict Engineering](65-redis-enterprise-active-active-crdt-semantics-conflict-engineering.md)
- **66** — [Redis Enterprise Active-Active Operations, Monitoring & Failure Recovery](66-redis-enterprise-active-active-operations-monitoring-failure-recovery.md)
- **67** — [Redis Enterprise Active-Active Regional Cutover, Rejoin & Failback Engineering](67-redis-enterprise-active-active-regional-cutover-rejoin-failback-engineering.md)
- **68** — [Redis Enterprise Multi-Cluster / Multi-Environment Platform Standards](68-redis-enterprise-multi-cluster-multi-environment-platform-standards.md)

### Part 12 — Advanced Operations, FinOps & Resilience

- **69** — [Redis Enterprise Advanced Memory Forensics, Fragmentation & Allocator Engineering](69-redis-enterprise-advanced-memory-forensics-fragmentation-allocator-engineering.md)
- **70** — [Redis Enterprise Command Complexity, SLOWLOG & Latency Forensics](70-redis-enterprise-command-complexity-slowlog-latency-forensics.md)
- **71** — [Redis Enterprise Proxy, Endpoint & Network Path Troubleshooting Engineering](71-redis-enterprise-proxy-endpoint-network-path-troubleshooting-engineering.md)
- **72** — [Redis Enterprise Shard Rebalancing, Resharding & Placement Operations](72-redis-enterprise-shard-rebalancing-resharding-placement-operations.md)
- **73** — [Redis Enterprise Cost Optimization & FinOps Engineering](73-redis-enterprise-cost-optimization-finops-engineering.md)
- **74** — [Redis Enterprise Configuration Drift, Compliance & Audit Automation](74-redis-enterprise-configuration-drift-compliance-audit-automation.md)
- **75** — [Redis Enterprise Business Continuity, Regional DR & Failback Project](75-redis-enterprise-business-continuity-regional-dr-failback-project.md)

### Part 13 — Production Projects & Final Acceptance

- **76** — [Redis Enterprise Performance & Capacity Engineering Project](76-redis-enterprise-performance-capacity-engineering-project.md)
- **77** — [Redis Enterprise Security Hardening & Credential-Rotation Project](77-redis-enterprise-security-hardening-credential-rotation-project.md)
- **78** — [Redis Enterprise Kubernetes Production Operations Project](78-redis-enterprise-kubernetes-production-operations-project.md)
- **79** — [Redis Enterprise Incident, Recovery & Resilience Game-Day Project](79-redis-enterprise-incident-recovery-resilience-game-day-project.md)
- **80** — [Redis Enterprise Final Production Readiness & Acceptance Project](80-redis-enterprise-final-production-readiness-acceptance-project.md)

## Suggested learning paths

- **Foundations and application teams:** Start with Chapters 01–20, followed by 21–30.
- **DBRE/SRE operational readiness:** Continue with 34–50 and the final acceptance projects 75–80.
- **Kubernetes/Active-Active:** Explore 45–46 and 61–68 after completing the HA and security foundations.
- **Advanced data services:** Chapters 52–60 cover migration, integration, JSON, Search, vector search, and related capabilities.

## Validation and lab safety

Run write, failover, security-negative, and recovery exercises only in dedicated test or staging environments with approval and isolated resources. Review all release-sensitive commands against the actual Redis Enterprise / Redis Software release. The navigation index covers chapter discovery; sequential **previous/next links inside chapters** are a separate editorial improvement and are not yet claimed as complete.
