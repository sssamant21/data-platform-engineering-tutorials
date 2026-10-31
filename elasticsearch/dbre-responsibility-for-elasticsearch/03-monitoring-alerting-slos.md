# Page 03 — Elasticsearch DBRE Monitoring, Alerting & SLOs

**Owner:** DBRE + Application SLO owners | **Status:** Draft | **Tools:** Prometheus, Grafana, Elasticsearch Exporter, Application APM

## 1. Monitoring model

Elasticsearch APIs → compatible exporter → Prometheus → Grafana/alert routing → DBRE/APP/PLT. Application search request instrumentation must supply **end-user latency and error SLIs**; Elasticsearch internal phase timers do not provide request P95/P99.

Collect node-level CPU/JVM/IO; per-index growth where enabled; shard detail only where justified (cardinality/overhead). Alert on missing exporter telemetry as well as unhealthy ES signals.

## 2. Dashboard catalog

| ID | Dashboard | Minimum panels |
|---|---|---|
| ES-01 | Executive cluster overview | Health, nodes, unassigned shards, SLO, alerts |
| ES-02 | Node/role health | Data/coordinator CPU, heap, GC, disk, breakers |
| ES-03 | Search and indexing | App P95/P99, errors, query/fetch operations, write rejections |
| ES-04 | Index and shards | Index count, primary/replica, allocation, shard sizes, ILM |
| ES-05 | Growth and forecast | Per-index primary/physical growth and forecasts |
| ES-06 | Heap/cache/merge | Query cache, fielddata, GC, merges, throttling |
| ES-07 | Backups and restore | Snapshot recency, failures, test-restore evidence |
| ES-08 | Business SLO/error budget | Availability, latency, freshness, burn rate |
| ES-09 | Alert and incident quality | Noise, response, recurrence and overdue RCA |

## 3. Example PromQL

**Assumptions:** Prometheus Community Elasticsearch Exporter; current deployed metrics and labels must be verified. Do not blindly copy queries into alerts. Add environment/cluster matchers and alert for missing data.

Cluster RED (exporter representation should be confirmed):

~~~~promql
max by (cluster) (elasticsearch_cluster_health_status{color="red"}) == 1
~~~~

Unassigned shards:

~~~~promql
max by (cluster) (elasticsearch_cluster_health_unassigned_shards)
~~~~

Heap utilization (check area label and node labels):

~~~~promql
100 *
elasticsearch_jvm_memory_used_bytes{area="heap"}
/
elasticsearch_jvm_memory_max_bytes
~~~~

CPU utilization:

~~~~promql
elasticsearch_os_cpu_percent
~~~~

Disk used estimate (validate mounted data-path labels):

~~~~promql
100 * (1 - elasticsearch_filesystem_data_available_bytes
  / elasticsearch_filesystem_data_size_bytes)
~~~~

Search query operations/s:

~~~~promql
sum by (cluster) (rate(elasticsearch_indices_search_query_total[5m]))
~~~~

Mean query-phase execution seconds/operation:

~~~~promql
sum by (cluster) (rate(elasticsearch_indices_search_query_time_seconds[5m]))
/
sum by (cluster) (rate(elasticsearch_indices_search_query_total[5m]))
~~~~

Index operations/s:

~~~~promql
sum by (cluster) (rate(elasticsearch_indices_indexing_index_total[5m]))
~~~~

New rejection rate:

~~~~promql
sum by (cluster, name, type) (rate(elasticsearch_thread_pool_rejected_count[5m]))
~~~~

Query-cache evictions/s:

~~~~promql
sum by (cluster, name) (rate(elasticsearch_indices_query_cache_evictions[5m]))
~~~~

Merge throttling seconds per second:

~~~~promql
sum by (cluster) (rate(elasticsearch_indices_merges_total_throttled_time_seconds_total[5m]))
~~~~

Primary storage by index (requires per-index collector; avoid double counting duplicate exporters):

~~~~promql
sum by (cluster, index) (elasticsearch_indices_store_size_bytes_primary)
~~~~

Top largest indices:

~~~~promql
topk(10, sum by (cluster, index) (elasticsearch_indices_store_size_bytes_primary))
~~~~

**Metric-label caution:** Exporter labels differ by version/configuration; a metric may lack a proposed label or use different labels. Confirm metadata, units and collector flags before deployment. A rate from a cumulative metric is different from its total value.

## 4. Per-index growth model

| Period | Definition |
|---|---|
| Daily | Latest primary-size sample minus yesterday's comparable sample |
| Weekly | Same index seven days earlier; track created/deleted/rolled-over indexes |
| Monthly | Calendar month-end minus previous month-end |
| Quarterly | Calendar quarter-end comparison |
| Semiannual | Six-month comparison |
| Annual | Calendar-year comparison |

Preserve daily snapshots with index ID/name and business owner. Do not misrepresent newly created/deleted indices as zero growth: report index churn separately. Track both primary logical bytes and actual physical/replica-inclusive bytes.

### Example 7-day comparison (only continuously present series)

~~~~promql
sum by (cluster,index) (elasticsearch_indices_store_size_bytes_primary)
-
sum by (cluster,index) (elasticsearch_indices_store_size_bytes_primary offset 7d)
~~~~

This comparison excludes unmatched series and does not implement a calendar-month reporting algorithm.

## 5. Application SLI/SLO definition

- **Search availability SLI:** eligible successful search requests / all eligible search requests.
- **Latency SLI:** eligible searches completed within target time / all eligible searches (agreed error treatment).
- **Freshness SLI:** eligible updates searchable inside agreed delay / eligible updates.
- **Recovery:** measured RPO and RTO from restore exercises.

**Example proposals requiring approval:** availability 99.9% per rolling 30 days; 95% of eligible searches <= 2 seconds; freshness and RPO/RTO defined by application and business data owner.

Example application instrumentation (metric is illustrative, not supplied by Elasticsearch):

~~~~promql
sum(increase(app_search_requests_total{service="patient-search",result="success"}[30d]))
/
sum(increase(app_search_requests_total{service="patient-search"}[30d]))
~~~~

Example classic histogram P95 (application-instrumented):

~~~~promql
histogram_quantile(0.95,
  sum by (le) (rate(app_search_request_duration_seconds_bucket{service="patient-search"}[5m]))
)
~~~~

**Error budget:** For a 99.9% request-success objective, the allowed unsuccessful request ratio is 0.1% during the measurement window. Request-success and wall-clock uptime objectives are not interchangeable. Define retries, timeouts and cancellations explicitly.

## 6. Candidate alert routing and severity

| Alert | Starting detection | Owner |
|---|---|---|
| Cluster RED / missing primaries | RED with short confirmation, assess impact immediately | DBRE |
| Unexpected sustained YELLOW | Beyond maintenance/recovery tolerance | DBRE |
| Exporter or expected metrics missing | 5 min no scrape/stale telemetry | DBRE/Monitoring |
| Node missing | Expected versus observed count/role | DBRE + PLT |
| Heap/GC pressure | Sustained heap with GC/latency | DBRE |
| Disk pressure | Actual watermarks or forecast risk | DBRE + PLT |
| New thread-pool rejections | Sustained rate plus workload impact | DBRE |
| Application P95/P99 breach | Agreed SLO threshold | APP + DBRE |
| Snapshot stale/failure | Recovery point approaching/exceeding RPO | DBRE + PLT |
| High index growth | Forecasted breach of planned headroom | DBRE + DATA |

**P1:** major outage, missing business-critical primaries, severe burn. **P2:** substantial degradation or availability risk. **P3:** sustained anomalous trends requiring work. **P4:** informational. Assign true severity based on business impact.

## 7. Sample Prometheus rule (illustrative)

~~~~yaml
groups:
  - name: elasticsearch-dbre
    rules:
      - alert: ElasticsearchClusterRed
        expr: max by (cluster) (elasticsearch_cluster_health_status{color="red"}) == 1
        for: 2m
        labels:
          severity: critical
          team: dbre
        annotations:
          summary: "Elasticsearch cluster RED"
          description: "Investigate unavailable primary shards and application impact."
      - alert: ElasticsearchExporterDown
        expr: up{job="elasticsearch-exporter"} == 0
        for: 5m
        labels:
          severity: warning
          team: dbre
        annotations:
          summary: "ES exporter scrape failed"
~~~~

Before production activation add environment selectors, target disappearance detection, dashboard/runbook links, team routing, missing-data behavior, recovery test and alert noise review.

## 8. Data quality, privacy and governance

- Confirm all expected nodes are scraped; avoid duplicating cluster-wide aggregates across exporters.
- Check histogram source and bucket labels; do not infer P95 from cumulative Elasticsearch query/fetch times.
- Keep PHI, EMPI, names, emails, tokens and high-cardinality customer IDs out of metric labels.
- Review exporter version and configured collectors before expecting per-index or snapshot metrics.
- Require staging rule testing and DBRE/APP sign-off.

## 9. Acceptance

- [ ] All 9 dashboard designs mapped to live metric sources.
- [ ] Per-index growth collectors and retention configured.
- [ ] Application P95/P99/availability/freshness SLI instrumentation verified.
- [ ] Alert severity, thresholds, no-data handling and on-call routing tested.
- [ ] Snapshot freshness tied to approved RPO.
- [ ] One production-baseline review and test notification completed.

## References
- [Elasticsearch Exporter metrics](https://github.com/prometheus-community/elasticsearch_exporter/blob/master/metrics.md)
- [Prometheus histograms](https://prometheus.io/docs/practices/histograms/)
- [Grafana missing data handling](https://grafana.com/docs/grafana/latest/alerting/guides/missing-data/)
