# Page 02 — Elasticsearch DBRE Daily, Weekly, Monthly & Quarterly Operations

**Owner:** DBRE On-Call / Platform Reliability | **Status:** Draft | **Reference:** ES 7.17.x

## 1. Operating principle

Automate routine collection with Prometheus and Grafana; use manual DBRE review for anomalies, trends, unresolved risks and owner decisions. Every review must result in a documented status, exception or action ticket.

## 2. Daily production checklist

| ID | Check | Indicators | DBRE follow-up |
|---|---|---|---|
| D01 | Health | GREEN/YELLOW/RED, critical primaries | Investigate unexpected YELLOW and any RED promptly |
| D02 | Nodes | Present versus expected, joins/leaves | Correlate departures with host/ES logs |
| D03 | Allocation | Unassigned shards, recoveries, relocations | Explain and resolve blockers |
| D04 | JVM | Heap, GC, circuit breakers | Identify request/heap pressure |
| D05 | CPU | Data/coordinator/master-eligible node saturation | Correlate with workload and hot threads |
| D06 | Disk | Free bytes, watermarks, forecasts | Plan storage and resolve allocation limits |
| D07 | Search | Application P95/P99, errors, ES phase times | Escalate APP/DBRE jointly |
| D08 | Indexing | Throughput, retries, rejections, freshness | Escalate DATA when upstream issues |
| D09 | Thread pools | Queue size, **increase** in rejected counters | Diagnose congestion |
| D10 | Backups | Latest successful snapshot versus RPO | Escalate snapshot gaps |
| D11 | Incidents | Open incidents and CAPA actions | Update incident tickets |
| D12 | Monitoring | Scrape status, missing data, stale panels | Fix instrumentation gaps |

### Read-only daily command pack (Kibana Dev Tools)

~~~~http
GET /_cluster/health
GET /_cat/nodes?v&h=name,ip,node.role,master,cpu,heap.percent,ram.percent,uptime
GET /_cat/shards?v&h=index,shard,prirep,state,store,node,unassigned.reason
GET /_cat/allocation?v
GET /_cluster/pending_tasks
GET /_nodes/stats/jvm,process,os,fs,thread_pool,breaker
GET /_nodes/stats/indices/search,indexing,merge,query_cache,fielddata
GET /_slm/stats
~~~~

The SLM endpoint requires appropriate permissions and is only relevant where SLM is used. Limit index/shard output on large clusters. Counters require a time window; do not confuse cumulative rejections/evictions with current error rates.

**Daily evidence:** health screenshot/time-series link, exceptions, ticket IDs and assigned responders.

## 3. Weekly review

| ID | Review | Evidence / decision |
|---|---|---|
| W01 | Daily/weekly growth by index | Fastest-growing indices, growth owners |
| W02 | Shard size and distribution | Oversized/undersized shards and recovery impact |
| W03 | Search/query regression | P95/P99, query versus fetch, slow requests |
| W04 | Indexing regression | Index rate, freshness and rejections |
| W05 | Deleted documents | Trend and storage impact, not auto-force-merge |
| W06 | Merge/IO and recovery load | Throttling, CPU/disk pressure |
| W07 | Cache and fielddata | Rate of evictions versus latency/heap |
| W08 | Disk balance | Growth forecast and hotspot nodes |
| W09 | ILM / rollover errors | Stuck actions, write-index settings |
| W10 | Alert quality | Repeated, noisy, missed or stale alerts |
| W11 | Incidents / RCA actions | Overdue preventive measures |
| W12 | Operational toil | Automation candidates with safeguards |

~~~~http
GET /_cat/indices?v&h=health,index,pri,rep,docs.count,docs.deleted,store.size,pri.store.size&s=store.size:desc
GET /_cat/shards?v&h=index,shard,prirep,state,store,node
GET /_stats/docs,store,search,indexing,merge,query_cache,fielddata
GET /_ilm/status
GET /_all/_ilm/explain?only_errors=true
~~~~

**Storage:** primary store approximates logical index data excluding replicas; total store reflects current replica-inclusive shard storage. Preserve snapshots of measurements for calendar-based reporting.

**Deleted-document diagnostic:** deleted / (live + deleted) is an indicative Lucene document ratio, not a business-record deletion percentage. Nested docs can make values differ.

**Safety:** Do not force merge active write indices or modify ILM merely because a weekly metric is high.

## 4. Monthly review

| ID | Activity | Required output |
|---|---|---|
| M01 | 30/60/90-day capacity planning | Primary + physical growth projection, headroom |
| M02 | Per-index/owner growth summary | Top growth drivers and retention dependencies |
| M03 | Node role and compute utilization | Peak and steady CPU, heap, GC, disk, IO |
| M04 | Right-sizing analysis | Benefit, impact, benchmark and rollback |
| M05 | Restore-readiness review | Latest **tested restore** and RPO/RTO evidence |
| M06 | Incident RCA review | Repeat failures and corrective actions |
| M07 | Query workload review | Top expensive application patterns |
| M08 | Lifecycle / ownership | ILM errors, index owners, cleanup candidates |
| M09 | Security and credentials | Expiring certs, access concerns with SEC |
| M10 | ES support lifecycle | Unsupported version risk and upgrade backlog |
| M11 | Runbook validation | Tested dates, owner and broken links |

**Forecasting:** model planned ingestion, replicas, shards, reindex/merge headroom, translogs and temporary space. Do not assume a linear forecast captures peak growth, index rollover or retention changes.

**Right-sizing:** never reduce data or coordinating node compute purely from low average CPU. Benchmark peak concurrency, query/fetch latency, heap, rejections and rollback capacity with APP/PLT.

## 5. Quarterly review

- Validate HA and failure-domain design; simulate representative failover in staging.
- Complete authorized restore/DR exercise and compare measured RTO/RPO with targets.
- Review vendor support and upgrade/migration roadmap.
- Review access, ownership/RACI, runbook operability and on-call coverage.
- Assess architecture, shard topology, retention and long-range cost strategy.
- Publish risks, owner-assigned remediation actions and a review sign-off.

## 6. Candidate alert thresholds (not certified)

| Signal | Initial warning discussion | Critical determination |
|---|---|---|
| Cluster | Unexpected YELLOW >5m | RED or unavailable required primaries; assess impact |
| Disk | Sustained 75–80%, low projected headroom | High/flood watermark, write risk |
| JVM heap | Sustained >75% with trend | >85% with GC/rejections or service impact |
| CPU | >75% for 15m | >90% with workload impact |
| Rejections | Sustained new rejections | Rejections causing customer errors |
| Search | Above warning SLO | Approved severe SLO breach |
| Backup | One scheduled failure | Recovery point exceeds RPO |
| ILM | Persistent ERROR step | Retention/capacity deadline threatened |

Check actual configured disk watermark settings (often 85%, 90%, 95% defaults subject to version/configuration and max headroom). Thresholds must be calibrated to production workload and alert noise.

## 7. Reusable review record

| Field | Entry |
|---|---|
| Report date / review period | |
| Cluster / environment | |
| DBRE reviewer | |
| Cluster availability / SLO | |
| Search and indexing summary | |
| CPU / heap / disk trends | |
| Top 10 growing indices | |
| Shard / ILM / snapshot exceptions | |
| Risks and actions | |
| Ticket and owner | |
| Reviewer sign-off | |

## 8. Acceptance

- [ ] Checks have named on-call owners and Grafana links.
- [ ] Read-only diagnostic pack passes staging validation.
- [ ] Snapshot and freshness signals use actual approved RPO/SLO.
- [ ] Review templates and storage/growth history are available.
- [ ] First documented weekly and monthly reviews complete.
- [ ] Team approves cadence, thresholds and escalation routing.

## References
- [Nodes stats API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-nodes-stats)
- [Index stats API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-stats)
- [ILM troubleshooting](https://www.elastic.co/docs/troubleshoot/elasticsearch/index-lifecycle-management-errors)
