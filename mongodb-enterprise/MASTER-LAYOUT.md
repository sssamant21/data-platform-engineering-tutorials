# MongoDB Enterprise — Complete Production Curriculum

**Audience:** Developers, Data Engineers, DBREs, SREs and Platform Engineers  
**Workflow:** Planned → Draft → Technical review → Lab validated → Canonical  
**Progress:** 41/80 written; 0/80 runtime validated.  
**Lab baseline:** MongoDB 8.0 syntax; record exact server, mongosh, driver, tool and operator versions in every lab. Existing 7.0 deployments require their own compatibility review. Enterprise-only exercises require authorized Enterprise binaries and entitlements; Community labs must not claim Enterprise feature validation.

## Part 1 — Foundations and Architecture

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 01 | [MongoDB Enterprise Fundamentals](01-mongodb-enterprise-fundamentals.md) | Create, query, update and verify a synthetic document collection | Written; runtime validation pending |
| 02 | [Document Model and BSON Types](02-document-model-and-bson-types.md) | Inspect BSON types, repair mismatches, verify EJSON and reject invalid documents | Written; runtime validation pending |
| 03 | [Server Architecture and WiredTiger](03-server-architecture-and-wiredtiger.md) | Collect WiredTiger snapshots, verify a bounded workload and distinguish storage sizes | Written; runtime validation pending |
| 04 | [Community Enterprise Advanced and Atlas](04-community-enterprise-advanced-and-atlas.md) | Inventory build/topology, verify a common contract and separate entitlement evidence | Written; runtime validation pending |
| 05 | [Lab Setup and Version Inventory](05-lab-setup-and-version-inventory.md) | Build authenticated persistent training server, inventory versions and test scoped access | Written; runtime validation pending |
| 06 | [mongosh Connections TLS and Authentication](06-mongosh-connections-tls-and-authentication.md) | Build verified TLS/SCRAM lab and distinguish transport, authentication and permission failures | Written; runtime validation pending |
| 07 | [Databases Collections and Namespaces](07-databases-collections-and-namespaces.md) | Inspect namespace metadata, reproduce a typo, verify read-only views and reverse a controlled rename | Written; runtime validation pending |
| 08 | [CRUD Filters Projections and Sorting](08-crud-filters-projections-and-sorting.md) | Verify bounded query contracts, guarded state transitions, upserts, bulk counts and scoped deletion | Written; runtime validation pending |

## Part 2 — Data Modeling and Application Development

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 09 | [Nested Documents and Arrays](09-nested-documents-and-arrays.md) | Verify precise nested/array updates, duplicate semantics, bounded summaries and shape repair | Written; runtime validation pending |
| 10 | [Embedding Versus Referencing](10-embedding-versus-referencing.md) | Compare equivalent models, reconcile copied data and detect cross-document consistency gaps | Written; runtime validation pending |
| 11 | [Schema Validation and Evolution](11-schema-validation-and-evolution.md) | Preview conversions, quarantine unresolved data, enforce versioned schema and restore lab originals | Written; runtime validation pending |
| 12 | [Updates Upserts and Bulk Writes](12-updates-upserts-and-bulk-writes.md) | Reconcile ordered/unordered partial success, replay desired states and classify pipeline conversions | Written; runtime validation pending |
| 13 | [Aggregation Pipeline Fundamentals](13-aggregation-pipeline-fundamentals.md) | Reconcile typed claims reports and repair stage-order/projection mistakes | Written; runtime validation pending |
| 14 | [Advanced Aggregations and Joins](14-advanced-aggregations-and-joins.md) | Detect join/unwind inflation and reconcile facets, line totals and ordered windows | Written; runtime validation pending |
| 15 | [Pagination and API Query Design](15-pagination-and-api-query-design.md) | Verify signed tenant-scoped seek cursors and reproduce offset instability under mutations | Written; runtime validation pending |
| 16 | [Transactions Sessions and Retry Semantics](16-transactions-sessions-and-retry-semantics.md) | Execute atomic transfers, verify abort/isolation and distinguish transaction/commit retries | Written; runtime validation pending |

## Part 3 — Indexes and Performance

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 17 | [Single Field and Compound Indexes](17-single-field-and-compound-indexes.md) | Compare scan/index work, verify sort support and rehearse reversible index hiding | Written; runtime validation pending |
| 18 | [ESR Index Design and Covered Queries](18-esr-index-design-and-covered-queries.md) | Compare ESR/ERS range tradeoffs and prove, break and restore query coverage | Written; runtime validation pending |
| 19 | [Multikey Partial Sparse and Unique Indexes](19-multikey-partial-sparse-and-unique-indexes.md) | Verify array semantics, index membership, scoped uniqueness and failed-write state | Written; runtime validation pending |
| 20 | [TTL Retention and Index Lifecycle](20-ttl-retention-and-index-lifecycle.md) | Observe TTL cleanup, repair dates, change retention and rehearse index lifecycle reversals | Written; runtime validation pending |
| 21 | [Explain Plans and Query Optimization](21-explain-plans-and-query-optimization.md) | Diagnose completed query work, interpret candidate trials and verify optimization correctness | Written; runtime validation pending |
| 22 | [Profiling Slow Queries and Query Statistics](22-profiling-slow-queries-and-query-statistics.md) | Capture tagged operations, compare real query work, restore profiling and assess statistics availability | Written; runtime validation pending |
| 23 | [WiredTiger Cache Eviction and Checkpoints](23-wiredtiger-cache-eviction-and-checkpoints.md) | Compare engine snapshots, observe checkpoint progress and diagnose cache/counter interpretation errors | Written; runtime validation pending |
| 24 | [CPU Memory Storage IOPS and Capacity](24-cpu-memory-storage-iops-and-capacity.md) | Reconcile bounded workload/resource evidence and calculate I/O, growth and maintenance headroom | Written; runtime validation pending |

## Part 4 — Replication and High Availability

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 25 | [Replica Set Architecture and Oplog](25-replica-set-architecture-and-oplog.md) | Inventory roles/votes, measure retained history and trace scoped writes into oplog evidence | Written; runtime validation pending |
| 26 | [Build a Three Member Replica Set](26-build-a-three-member-replica-set.md) | Build isolated three-member topology and verify discovery, majority writes and member convergence | Written; runtime validation pending |
| 27 | [Read Preference Read Concern and Write Concern](27-read-preference-read-concern-and-write-concern.md) | Verify routing/visibility/acknowledgement, causal secondary reads and concern-error reconciliation | Written; runtime validation pending |
| 28 | [Elections Stepdown and Planned Maintenance](28-elections-stepdown-and-planned-maintenance.md) | Rehearse sequential restarts, non-forced handoff and per-member data/readiness verification | Written; runtime validation pending |
| 29 | [Replication Lag and Oplog Sizing](29-replication-lag-and-oplog-sizing.md) | Measure lag/history, recover a bounded secondary outage and verify sizing/member-local resize | Written; runtime validation pending |
| 30 | [Initial Sync Resync and Member Replacement](30-initial-sync-resync-and-member-replacement.md) | Replace one secondary on fresh storage, reconcile clone/metadata and restore original volumes | Written; runtime validation pending |
| 31 | [Network Partitions Rollback and Consistency](31-network-partitions-rollback-and-consistency.md) | Partition one primary, reconcile majority history and classify rollback evidence after healing | Written; runtime validation pending |
| 32 | [Replica Set Failure and Recovery Lab](32-replica-set-failure-and-recovery-lab.md) | Reconcile bounded traffic through primary crash, quorum loss and full original-member recovery | Written; runtime validation pending |

## Part 5 — Sharding and Scale

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 33 | [Sharded Cluster Architecture](33-sharded-cluster-architecture.md) | Inspect deployment identity, verify synthetic routing boundaries/skew and optionally inventory a real router | Written; runtime validation pending |
| 34 | [Shard Key Selection and Workload Analysis](34-shard-key-selection-and-workload-analysis.md) | Compare candidate keys using skew, weighted query shapes, analyzer evidence, failure repair and scoped cleanup | Written; runtime validation pending |
| 35 | [Build a Sharded Lab Cluster](35-build-a-sharded-lab-cluster.md) | Build two shards and redundant routers, reconcile routed data and recover a router outage | Written; runtime validation pending |
| 36 | [Chunk Distribution Balancing and Zones](36-chunk-distribution-balancing-and-zones.md) | Verify manual range movement, automatic zone correction, overlap rejection and owned-policy cleanup | Written; runtime validation pending |
| 37 | [Targeted Queries Scatter Gather and Hot Shards](37-targeted-queries-scatter-gather-and-hot-shards.md) | Verify real query fan-out, distinguish local indexing, compare tenant/document demand and restore scoped placement | Written; runtime validation pending |
| 38 | [Resharding and Shard Key Refinement](38-resharding-and-shard-key-refinement.md) | Refine a key suffix, reshard to a hashed key, verify routing and data, and restore cluster policy | Written; runtime validation pending |
| 39 | [Sharded Cluster Administration and Recovery](39-sharded-cluster-administration-and-recovery.md) | Inventory topology, recover controlled member/shard outages, reconcile data and metadata, and clean up | Written; runtime validation pending |
| 40 | [Scaling and Sharding Acceptance Lab](40-scaling-and-sharding-acceptance-lab.md) | Verify one-to-two-shard distribution, repeat reconciled workloads, recover a router, and assemble acceptance evidence | Written; runtime validation pending |

## Part 6 — Enterprise Security and Governance

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 41 | [Users Roles and Least Privilege](41-users-roles-and-least-privilege.md) | Bootstrap access control, verify scoped roles and denials, rotate credentials, and clean up owned identities/data | Written; runtime validation pending |
| 42 | TLS Certificates and x509 Authentication | Demonstrate tls certificates and x509 authentication with evidence and cleanup | Planned |
| 43 | Enterprise External Authentication Compatibility | Demonstrate enterprise external authentication compatibility with evidence and cleanup | Planned |
| 44 | Enterprise Audit Configuration and Analysis | Demonstrate enterprise audit configuration and analysis with evidence and cleanup | Planned |
| 45 | Encryption at Rest and Key Management | Demonstrate encryption at rest and key management with evidence and cleanup | Planned |
| 46 | Client Side and Queryable Encryption | Demonstrate client side and queryable encryption with evidence and cleanup | Planned |
| 47 | Secrets Rotation and Access Review | Demonstrate secrets rotation and access review with evidence and cleanup | Planned |
| 48 | Security Hardening Acceptance Lab | Demonstrate security hardening acceptance lab with evidence and cleanup | Planned |

## Part 7 — Backup Recovery and Disaster Recovery

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 49 | Backup Architecture RPO and RTO | Demonstrate backup architecture rpo and rto with evidence and cleanup | Planned |
| 50 | mongodump mongorestore and Logical Recovery | Demonstrate mongodump mongorestore and logical recovery with evidence and cleanup | Planned |
| 51 | Consistent Snapshots and Restore Validation | Demonstrate consistent snapshots and restore validation with evidence and cleanup | Planned |
| 52 | Ops Manager Backup and Point in Time Recovery | Demonstrate ops manager backup and point in time recovery with evidence and cleanup | Planned |
| 53 | Accidental Delete and Drop Recovery | Demonstrate accidental delete and drop recovery with evidence and cleanup | Planned |
| 54 | Replica Set Disaster Recovery | Demonstrate replica set disaster recovery with evidence and cleanup | Planned |
| 55 | Sharded Cluster Backup and Disaster Recovery | Demonstrate sharded cluster backup and disaster recovery with evidence and cleanup | Planned |
| 56 | Restore Drill and Recovery Acceptance Project | Demonstrate restore drill and recovery acceptance project with evidence and cleanup | Planned |

## Part 8 — Administration Deployment and Integration

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 57 | Ops Manager Architecture and Prerequisites | Demonstrate ops manager architecture and prerequisites with evidence and cleanup | Planned |
| 58 | Ops Manager Automation Monitoring and Agents | Demonstrate ops manager automation monitoring and agents with evidence and cleanup | Planned |
| 59 | Linux Installation Configuration and Service Operations | Demonstrate linux installation configuration and service operations with evidence and cleanup | Planned |
| 60 | Kubernetes Operator Compatibility and Deployment | Demonstrate kubernetes operator compatibility and deployment with evidence and cleanup | Planned |
| 61 | Kubernetes Storage Scheduling and Maintenance | Demonstrate kubernetes storage scheduling and maintenance with evidence and cleanup | Planned |
| 62 | Rolling Upgrades FCV and Rollback Constraints | Demonstrate rolling upgrades fcv and rollback constraints with evidence and cleanup | Planned |
| 63 | Drivers Connection Pools Timeouts and Retries | Demonstrate drivers connection pools timeouts and retries with evidence and cleanup | Planned |
| 64 | Change Streams Resume Tokens and CDC | Demonstrate change streams resume tokens and cdc with evidence and cleanup | Planned |

## Part 9 — Specialized Data and Observability

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 65 | Time Series Collections and Retention | Demonstrate time series collections and retention with evidence and cleanup | Planned |
| 66 | GridFS Capped Collections and Workload Boundaries | Demonstrate gridfs capped collections and workload boundaries with evidence and cleanup | Planned |
| 67 | MongoDB to Snowflake Direct Integration | Demonstrate mongodb to snowflake direct integration with evidence and cleanup | Planned |
| 68 | Import Export Migration and Data Reconciliation | Demonstrate import export migration and data reconciliation with evidence and cleanup | Planned |
| 69 | Metrics Logs FTDC and Dashboard Design | Demonstrate metrics logs ftdc and dashboard design with evidence and cleanup | Planned |
| 70 | Alert Thresholds SLOs and Capacity Forecasting | Demonstrate alert thresholds slos and capacity forecasting with evidence and cleanup | Planned |
| 71 | Daily Administration and Maintenance Runbook | Demonstrate daily administration and maintenance runbook with evidence and cleanup | Planned |
| 72 | Cost Optimization and Enterprise License Planning | Demonstrate cost optimization and enterprise license planning with evidence and cleanup | Planned |

## Part 10 — Troubleshooting and Production Projects

| # | Chapter | Lab outcome | Status |
|---|---|---|---|
| 73 | Query Slowness Investigation Runbook | Demonstrate query slowness investigation runbook with evidence and cleanup | Planned |
| 74 | Connection Authentication and TLS Troubleshooting | Demonstrate connection authentication and tls troubleshooting with evidence and cleanup | Planned |
| 75 | Disk Pressure Cache Pressure and Resource Incidents | Demonstrate disk pressure cache pressure and resource incidents with evidence and cleanup | Planned |
| 76 | Replication Elections and Sharding Troubleshooting | Demonstrate replication elections and sharding troubleshooting with evidence and cleanup | Planned |
| 77 | Production Data Modeling and Query Tuning Project | Demonstrate production data modeling and query tuning project with evidence and cleanup | Planned |
| 78 | HA Failover and Application Resilience Project | Demonstrate ha failover and application resilience project with evidence and cleanup | Planned |
| 79 | Backup Restore and Disaster Recovery Project | Demonstrate backup restore and disaster recovery project with evidence and cleanup | Planned |
| 80 | Production Readiness and Final Acceptance Project | Demonstrate production readiness and final acceptance project with evidence and cleanup | Planned |

## Coverage boundaries

This is a production-focused curriculum, not a claim to cover every product feature or every supported version. Search/vector features and product-specific services must receive explicit deployment and edition checks before being added. External authentication, operator support, upgrades and encryption require version-specific documentation review. MongoDB→Snowflake integration is direct; Elasticsearch is not a required intermediary.
