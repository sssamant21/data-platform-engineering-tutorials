# Page 05 — Elasticsearch Capacity Planning, Index Growth & Cost Optimization

**Document ID:** ES-DBRE-OPS-005  
**Owner:** Elasticsearch DBRE  
**Version:** 1.0 — Proposed  
**Status:** DRAFT — NOT CERTIFIED FOR PRODUCTION  
**Reference platform:** Elasticsearch 7.17.x; validate exact service/provider compatibility  
**Cadence:** Daily collection, weekly exceptions, monthly planning, quarterly architecture review  
**Partners:** Application, Data Engineering, Platform/Cloud, Security, Finance/FinOps, Change Management

> **Safety:** This document supplies read-only inspection and planning examples. No production capacity change, index deletion, force merge, reindex, replica reduction, ILM change or node resize is authorized by publication of this guide.

## 1. Purpose and outcomes

Standardize how DBRE measures Elasticsearch growth, forecasts infrastructure needs, plans shard size, evaluates node resource efficiency and proposes safe cost reductions. **Capacity decisions must preserve application SLOs, recovery objectives, redundancy, disk headroom and peak-load resilience.**

Deliverables:
1. Cluster and **per-index** logical/physical growth history.
2. Daily, weekly, monthly, quarterly, semiannual and annual reports.
3. 30/60/90-day storage, shard and compute forecasts, including uncertainty.
4. Data/coordinating/master-eligible node capacity reviews.
5. Approved right-sizing proposals backed by staging/load test and rollback plans.
6. Auditable action backlog and post-change validation evidence.

## 2. Ownership and decision rights

| Activity | Accountable | Responsible / consulted |
|---|---|---|
| ES shard and capacity design | DBRE | APP, DATA, PLT |
| Per-index source/owner/retention mapping | DATA | DBRE, APP |
| Monitoring, measurement and forecast | DBRE | PLT, FinOps |
| Application query workload/SLO acceptance | APP | DBRE |
| Cloud compute/storage configuration changes | PLT | DBRE, APP |
| Business data deletion/retention approval | DATA | DBRE, APP, SEC |
| Formal production change approval | Change Management | DBRE, PLT, APP |
| Cost accounting and actual savings confirmation | FinOps | DBRE, PLT |

**Not a cost optimization:** Reducing replica count, changing retention or deleting business indices without required authorization and recovery review.

## 3. Inventory and workload classification

Create one row per cluster, index family, node role and critical workload.

| Field | What to capture |
|---|---|
| Cluster/environment/provider/version | Exact deployment, region and support status |
| Node role/count/specs | Data, coordinating-only, master-eligible, ingest; vCPU, RAM, heap, disk, instance/SKU |
| Availability topology | Zones, replica policies, allocation awareness, failure-domain behavior |
| Current data | Primary bytes, all-shard bytes, per-node filesystem used/free |
| Indices | Name/UUID, business owner, alias/data stream, retention, shard count |
| Workload | Requests/s, indexing docs/s, peak concurrency, aggregations, p95/p99, routing, size/page depth |
| Recovery | RPO, RTO, largest shard, observed relocation/restore throughput |
| Economics | SKU, billing period, cost basis, storage, snapshots, network and licenses |
| Constraints | Approved SLOs, compliance/data-retention, index lifecycle, maintenance window |

Separate **application search** from ingestion, recovery, batch jobs, high-cardinality aggregations and planned reindex loads. Averages can mask evening/weekend and month-end peaks.

## 4. Read-only Elasticsearch capacity command pack

Execute in Kibana Dev Tools with approved monitoring permissions. CAT responses are intended for human inspection; persist numeric time series via monitoring/automation.

~~~~http
# Cluster, node roles, and resource utilization
GET /_cluster/health
GET /_cat/nodes?v&h=name,node.role,master,cpu,heap.percent,ram.percent,uptime
GET /_cat/allocation?v
GET /_nodes/stats/os,process,jvm,fs,thread_pool

# Primary and total index storage
GET /_cat/indices?v&bytes=gb&h=health,index,pri,rep,docs.count,docs.deleted,store.size,pri.store.size

# Per-shard physical size (includes primaries and replicas)
GET /_cat/shards?v&bytes=gb&h=index,shard,prirep,state,store,node

# Detailed index storage and merges
GET /your-index-name/_stats/docs,store,merge,segments

# Current and default disk allocation settings
GET /_cluster/settings?include_defaults=true

# Node info: effective roles, OS and settings (avoid sharing sensitive settings)
GET /_nodes/os,settings

# Index lifecycle state
GET /your-index-name/_ilm/explain
~~~~

Do not publish raw /_nodes/settings output into open tickets: it may include infrastructure-sensitive settings. Use redaction and access controls. If collecting all indices in a large cluster creates overhead, collect only changed or at-risk indices.

## 5. Storage definitions — do not mix units

| Measure | Meaning | Use |
|---|---|---|
| **Primary store bytes** | Sum of allocated primary shard data on disk | Logical index growth approximation without replica duplication |
| **Total index store bytes** | Primaries plus allocated replicas | Replica-inclusive index footprint |
| **Filesystem data-path usage** | ES data filesystem used/free | Allocation watermarks and actual capacity |
| **Snapshot repository bytes** | Backup/object-storage usage | Separate cost and recovery-budget item |
| **Transient headroom** | Merge, recovery, translog, reindex and operational spikes | Safety margin; not business-retained storage |
| **Documents** | Lucene document statistics; nested docs may increase count | Trend only, not a guaranteed business record count |

Index total store can differ from filesystem usage because translogs, operating system/filesystem overhead, unallocated capacity and temporary operations are not fully represented by index store totals. **Do not sum all-shard store and then multiply by replica factor again.**

### Core formulas

- **Net primary growth over interval:** primary_bytes(t₂) − primary_bytes(t₁).
- **Average daily primary growth:** net primary growth / number of measured days.
- **Projected primary bytes (simple baseline):** latest primary bytes + (daily net growth × forecast days).
- **Nominal replica-inclusive index bytes:** projected primary bytes × (1 + planned replicas), **only** when replicas are fully allocated, uniform and no other tier/storage factor applies.
- **Required storage:** projected stored bytes + recovery/reindex/merge/translog headroom + safety reserve (estimate by actual platform, not a universal factor).
- **Usable capacity:** physical capacity constrained by configured disk allocation limits, overhead and failure-domain requirements; **not** 100% of raw disks.
- **Days to capacity limit:** remaining **usable** free bytes / projected net daily physical growth, when growth > 0. Use conservative forecast and node-level bottleneck.

### Worked example — illustration, not live cluster data

Suppose an index family has 4 TB of primary data, adds 40 GB of *net* primary data per day, and uses one fully allocated replica.

| Horizon | Primary data (illustrative decimal units) | Nominal all-shard index data |
|---|---:|---:|
| Today | 4.0 TB | 8.0 TB |
| 30 days | 5.2 TB | 10.4 TB |
| 60 days | 6.4 TB | 12.8 TB |
| 90 days | 7.6 TB | 15.2 TB |

**Not included:** retention/rollover changes, missing replicas, merge or reindex space, skew, filesystem overhead, snapshots, failover capacity and atypical ingestion peaks. Never use this example as an actual sizing recommendation.

## 6. Per-index growth reporting model

Persist **daily UTC snapshots** keyed by cluster identifier and stable index identifier/UUID plus name, business owner, application/family, alias, timestamp and observed metrics.

Suggested record schema:

| Field | Description |
|---|---|
| snapshot_utc | Collection timestamp at a consistent daily cutoff |
| cluster_id, environment | Stable source |
| index_uuid, index_name | Identity and current name |
| application, business_owner, index_family | Reporting ownership and rollover grouping |
| primary_store_bytes | Logical index-size proxy |
| total_store_bytes | Primary + allocated replica data |
| primary_shards, replica_shards | Configuration and observed allocation context |
| docs_live, docs_deleted | Lucene document trend |
| lifecycle_phase, write_index | Context for creation/rollover/retention |
| data_capture_status | successful, partial, stale, missing |

**Calendar reporting:**

| Window | Comparison |
|---|---|
| Daily | End-of-day minus prior end-of-day |
| Weekly | Same weekday, seven days before |
| Monthly | Calendar month-end minus previous month-end |
| Quarterly | Quarter-end minus previous quarter-end |
| Semiannual | Current half-year end minus prior half-year end |
| Annual | Year-end minus previous year-end |

Handle newly created indices, rollover generations, deletions and partial scrapes explicitly. Negative net growth can be legitimate (retention/expunging/rollover), not an error. Produce **gross additions, removals, and net growth** at application/index-family level when individual index churn makes simple comparisons misleading.

### Required stakeholder views

1. Total primary versus physical storage.
2. Top 10 largest index families and individual indices.
3. Top 10 fastest absolute-growth indices (GB/day).
4. Top 10 fastest relative-growth indices (%/day), with minimum-size filter to avoid tiny-index noise.
5. Per-index daily/weekly/monthly/quarterly/half-year/year history.
6. Per-node disk pressure and tier/zone imbalance.
7. Shard size and count distribution.
8. 30/60/90-day capacity forecast, scenarios and projected breach date.
9. Owner-attributed drivers and planned ingestion/retention changes.
10. Exportable monthly/quarterly report with source time, data quality and approved actions.

## 7. Prometheus/Grafana examples

Examples target the Prometheus Community Elasticsearch Exporter **when per-index collection is enabled**. Validate actual metric names and labels before enabling dashboards. Avoid double counting if multiple exporters expose the same full-cluster statistics.

Primary bytes by cluster/index:

~~~~promql
sum by (cluster, index) (
  elasticsearch_indices_store_size_bytes_primary
)
~~~~

Replica-inclusive bytes by cluster/index:

~~~~promql
sum by (cluster, index) (
  elasticsearch_indices_store_size_bytes_total
)
~~~~

Largest ten indices:

~~~~promql
topk(10, sum by (cluster, index) (elasticsearch_indices_store_size_bytes_primary))
~~~~

Seven-day primary change for indices present at both timestamps:

~~~~promql
sum by (cluster, index) (elasticsearch_indices_store_size_bytes_primary)
-
sum by (cluster, index) (elasticsearch_indices_store_size_bytes_primary offset 7d)
~~~~

Per-data-path disk used ratio (check exporter data path labels and sample duplication):

~~~~promql
100 * (
  1 -
  elasticsearch_filesystem_data_available_bytes
  /
  elasticsearch_filesystem_data_size_bytes
)
~~~~

The seven-day subtraction **does not include new or deleted indices** without matched historical samples; use historical snapshots and lineage reporting to produce authoritative period totals. Gauge sampling/rollover is not an event counter; do not use rate() on storage gauge as an unqualified growth truth.

### Suggested Grafana dashboard layout

- **Row A: Executive:** primary/physical TB, 7d/30d growth, forecast runway, SLO status.
- **Row B: Index growth:** top absolute and relative growth, searchable per-index history, index-family rollup.
- **Row C: Capacity:** data-path free space, watermark proximity, max/median used %, zone skew.
- **Row D: Workload:** search/indexing throughput, p95/p99, rejection rates, coordinating CPU/heap.
- **Row E: Shards:** size distribution, large shards, count/node and slow recovery risk.
- **Row F: FinOps:** instance/storage/snapshot line items, proposed versus realized savings.

Data export must include measurement definitions, period boundaries, source coverage and missing-data caveats.

## 8. Shard and index architecture review

Elastic's general shard guidance is **roughly 10–50 GB per shard** and usually **under 200 million Lucene documents per shard** as starting rules, not hard limits. Workload, indexing pattern and recovery-time tests govern the actual target.

### Weekly checks

- Flag unusually large primary shards and too many tiny shards.
- Compare size distribution by node, index family, tier and failure zone.
- Examine replica recovery duration and storage/headroom for largest shards.
- Review search fan-out, aggregate reduce cost and application routing.
- Plan new rollover/index templates rather than repeatedly tuning unchanged hot indices.
- Assess reindex necessity and its temporary storage and network/IO requirements.

### Example planning method

For an anticipated 240 GB primary index and a candidate 40 GB average primary shard target, **240 / 40 = 6 primary shards** as a preliminary design estimate. Validate at the shard and workload level, including indexing/query parallelism and fault-domain constraints.

Do **not** calculate shard count by counting only current data nodes, assume index-size limits universally, or change existing primary shard count in place without a supported strategy.

### Exception policy

Document why an index intentionally exceeds a guideline, including performance/recovery evidence, owner, next review date and capacity safeguards. Shard tuning must not break application routing, alias strategy or write semantics.

## 9. Node-role capacity and right-sizing

Evaluate data, coordinating, dedicated master-eligible and ingest nodes separately. Equal node sizes are **not** a requirement: role-specific CPU, heap, memory, network and scheduling determine capacity.

### Illustrative proposal under review

| Node role | Before | Candidate after | Key concern |
|---|---|---|---|
| Data node | 32 vCPU | 16 vCPU | Indexing/search concurrency, merge/recovery and CPU pressure |
| Coordinating-only node | 32 vCPU | 8 vCPU | Fan-out, query/aggregation reduce work, request concurrency and CPU saturation |

**These are proposal examples, not verified current settings or approvals.** CPU capacity is reduced 50% for the data-node example and 75% for the coordinating-node example; *cost savings are not implied to match those percentages*.

Changing machine/SKU or CPU availability may affect Elasticsearch effective processor count and thread-pool behavior; RAM/heap/disk/network performance may also change. Inspect instance specifications and effective runtime settings. Never assume equal heap or disk throughput will remain after resizing.

### Required baseline (minimum recommended evidence)

- 14–30 days of data capturing weekdays, weekends, major jobs and peak windows.
- Node role, effective CPU count, CPU throttling, heap/GC, breaker trips.
- Disk size/free space, IOPS/throughput and shard allocation distribution.
- Application p50/p95/p99 latency, success rate, timeouts and query throughput.
- Search query/fetch phase mean, queues, rejection **rate**, indexing throughput/freshness.
- Snapshot/recovery performance, largest shard and observed failover latency.
- Planned seasonal/workload growth, new indices and cost baseline.

### Staging and load-test matrix

| Test | Workload | Required acceptance |
|---|---|---|
| T01 Steady state | Normal day traffic and ingestion | App SLO and resource headroom |
| T02 Peak | Observed peak concurrency and batch jobs | App SLOs, no sustained rejections |
| T03 Burst | Higher-than-observed justified spike | Graceful backpressure, no outage |
| T04 Query fan-out | Multi-index search, aggregations, large results | Stable coordinator latency/CPU |
| T05 Indexing | Burst/bulk loads plus concurrent searches | Index freshness and SLOs maintained |
| T06 Node failure | Lose one eligible node/failure domain in staging | Required primaries/replicas recover within approved objectives |
| T07 Recovery | Shard relocation/restart at peak-safe load | Recovery headroom and performance |
| T08 Snapshot | Snapshot while application is active | Recovery coverage and acceptable impact |
| T09 Rollback | Restore previous resource settings | Proven recovery path without data integrity regression |

Do not perform failure injection in production without separately approved exercises.

### Go/no-go criteria

**GO only if:** APP, DBRE and PLT approve test results; sufficient peak, growth and failure headroom exists; expected shard placement is feasible; SLO, RPO/RTO and rollback criteria are met; change window/incident coverage is agreed.

**NO-GO:** Repeated latency SLO breaches, sustained rejections, disk watermark exposure, missing primary shards, prolonged recovery, insufficient rollback capacity, unknown index ownership, failed backup coverage or missing approval.

### Production change sequence (approval required)

1. Capture immutable before-state evidence and change ticket.
2. Confirm fresh, appropriately recoverable snapshots and rollback infrastructure.
3. Execute a staged/rolling platform-specific resize with node quorum, zones and shard recovery verified between steps.
4. Do not resize multiple failure domains in parallel without explicit validated design.
5. Monitor Elasticsearch and APP SLIs during each stage; pause on rollback trigger.
6. Conduct 24h/72h/7d post-change observations that cover representative peak workloads (extend for weekly cycles).
7. Confirm FinOps measured billing changes after a full comparable billing period.

**Rollback triggers:** Critical ES cluster degradation, app error/SLO breach, sustained CPU/GC/rejection pressure, unacceptable indexing freshness, recovery objective violation or loss of allocation headroom. Rollback must include revalidation of primaries/replicas and application workflows.

## 10. Disk watermark, resilience and temporary headroom

Common Elasticsearch defaults are **low 85%, high 90%, flood stage 95%** (with possible max-headroom and version/provider-specific behavior). Read actual cluster settings. Do not plan around 95% usage as nominal steady-state capacity.

Plan for:
- Failure of a data node and reallocation of shards onto remaining eligible nodes.
- Replicas in required availability zones / allocation-awareness constraints.
- Temporary duplicate index storage during reindex/cutover and recovery.
- Merge and translog space under peak writes.
- Snapshot repository sizing and network bandwidth.
- Disk imbalance: cluster-wide averages can conceal one hot node at the threshold.

**Danger:** Reducing replicas, disabling allocation/disk protections or deleting data to reach a cost target is not an acceptable shortcut.

## 11. Cost optimization and benefits measurement

Track actual line items:

| Cost component | Measurement | Control |
|---|---|---|
| Compute | Instance/SKU/node-hour billed | Right-size role-by-role after benchmarks |
| Block/managed disk | Provisioned and/or used GB, IOPS, throughput | Data tiers, retained headroom, planned disk size |
| Snapshot/object storage | Stored GB, API requests, retention | Owner-approved recovery and retention policy |
| Network | Cross-zone/region egress, replication | Test topology and resilience consequences |
| Operations | On-call incidents, maintenance and restore effort | Automation with safeguards |
| License/managed service | Version/features/node or resource pricing | Contract and feature constraints |

**Net realized savings = comparable pre-change cost − comparable post-change cost − one-time change/validation costs** (clearly specify whether recurring or first-period). Account for traffic, storage growth and non-CPU costs. FinOps validates billing; DBRE validates reliability after savings.

Prefer in order: query/application improvements, eliminate duplicated **approved** storage, fix retention/rollover design, correct oversharding, then role-specific compute resizing. Do not sacrifice SLO/DR requirements for speculative savings.

## 12. Monthly capacity report template

| Section | Required fields |
|---|---|
| Executive status | Service SLO, key risks, recommended decisions |
| Capacity | Primary TB, physical index TB, data-path free TB, node maxima |
| Growth | Net/gross additions, 7d/30d, top 10 growing indices, owner |
| Forecast | 30/60/90d baseline and peak scenarios, breach projection |
| Shards | Largest shards, distribution, count per node and trend |
| Performance | APP p95/p99, CPU/heap peaks, rejection increases, indexing freshness |
| Resilience | Single-node failure headroom, recovery time, latest validated restore |
| FinOps | Billed baseline, scenario cost, evidence and expected/realized savings |
| Decisions | Change proposal, owner, approval, ticket, due date |

### Change proposal record

- Cluster/provider/version; current/target SKU and exact vCPU/RAM/heap/disk.
- Business objective and owner-approved SLO/RPO/RTO.
- Baseline date range and peak-event coverage.
- Before/after load test evidence and failure/recovery test.
- Capacity forecast, shard layout and disk watermark headroom.
- Technical and financial benefits with confidence/risk.
- Change ticket, approvers, maintenance window, communications.
- Rolling execution steps, abort/rollback triggers and validation owner.
- 24h/72h/7d hypercare results and final billing assessment.

## 13. Acceptance criteria — Milestone 5

- [ ] Cluster/node/role and index-owner inventory complete.
- [ ] Per-index UTC primary and physical bytes are collected daily with lineage.
- [ ] Daily, weekly, monthly, quarterly, semiannual and annual growth reports match retained history.
- [ ] Forecasts include 30/60/90-day scenarios, peak demand and failure headroom.
- [ ] Watermarks and free-space constraints validated against actual configuration.
- [ ] Largest shard/recovery times assessed against current workload.
- [ ] Data and coordinating node role-specific baselines reviewed.
- [ ] Proposed downsizing passes documented peak, recovery and rollback tests in staging.
- [ ] APP, DBRE, PLT, Change Management and FinOps reviews recorded.
- [ ] No uncontrolled index deletion/replica reduction performed.
- [ ] Grafana panels and exporter metric/label mappings verified live.
- [ ] Post-change SLO, failover and actual-billing evidence captured.
- [ ] Confluence/GitHub links and operational reports reviewed.

**Completion criterion:** A reviewed capacity baseline and forecast, validated per-index growth reporting, approved node-role strategy and tested operational change controls exist. Draft publication alone **does not** satisfy the milestone.

## 14. References

- [Elastic — Size your shards](https://www.elastic.co/docs/deploy-manage/production-guidance/optimize-performance/size-shards)
- [Elastic — Disk watermark errors](https://www.elastic.co/docs/troubleshoot/elasticsearch/fix-watermark-errors)
- [Elastic — High CPU troubleshooting](https://www.elastic.co/docs/troubleshoot/elasticsearch/high-cpu-usage)
- [Elastic — CAT indices API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cat-indices)
- [Elasticsearch 7.17 reference](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/index.html)
- [Prometheus Community Elasticsearch Exporter metrics](https://github.com/prometheus-community/elasticsearch_exporter/blob/master/metrics.md)

---

**Publication note:** Guidance has been drafted and reviewed for structure, not tested against a live cluster. Verify APIs and monitoring metric labels against the actual Elasticsearch 7.17 and exporter versions; applicable provider restrictions and operational approvals take precedence.
