# Page 04 — Elasticsearch Incident Response & Troubleshooting

**Owner:** Elasticsearch DBRE On-Call | **Status:** Draft, not certified | **Reference:** Elasticsearch 7.17.x

## 1. Safety and incident sequence

**Detect → triage business impact → preserve evidence → diagnose read-only → obtain authorization for mutation → mitigate → validate ES and APP → communicate → blameless RCA.**

Classify P1 for major outage/unavailable critical business data; P2 for substantial degradation; P3 for limited persistent risk; P4 informational. Formal incident policy takes precedence. Record UTC timestamps, cluster/index, application impact, recent changes, on-call owner and mitigation history.

### First response (read-only, Kibana Dev Tools)

~~~~http
GET /_cluster/health
GET /_cat/nodes?v&h=name,ip,node.role,master,cpu,heap.percent,ram.percent,uptime
GET /_cat/shards?v&h=index,shard,prirep,state,store,node,unassigned.reason
GET /_cat/allocation?v
GET /_cluster/pending_tasks
GET /_nodes/stats/jvm,process,os,fs,thread_pool,breaker
GET /_nodes/stats/indices/search,indexing,merge,query_cache,fielddata,segments
GET /_cat/recovery?v&active_only=true
GET /_tasks?detailed=true
~~~~

Gather only the necessary data when cluster load is high. API metrics may reset with node/recovery changes. Retain Grafana time series, not only a single API snapshot.

## 2. ES-INC-001 — Cluster RED/YELLOW

**Symptoms:** unavailable primaries or replicas; unassigned shards; missing query results; stalled recovery.

~~~~http
GET /_cluster/health?level=indices
GET /_cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason
GET /_cluster/settings?include_defaults=true
GET /_cluster/allocation/explain
{
  "index": "your-index-name",
  "shard": 0,
  "primary": true
}
~~~~

Check node availability, disk watermarks, index allocation filtering, insufficient node roles, failed shard copies and allocation deciders. Fix the diagnosed constraint with change approval. **Never use allocate-stale-primary/accept_data_loss merely to obtain GREEN.** Validate active critical primaries, replica health and APP functions.

## 3. ES-INC-002 — Unexpected node loss

**Symptoms:** node count drops, repeated joins/leaves, relocation or failed requests.

~~~~http
GET /_cat/nodes?v
GET /_cluster/health
GET /_cat/recovery?v&active_only=true
GET /_nodes/stats/jvm,os,process,fs
~~~~

Inspect host/pod and systemd/service health, OOM logs, disks, network and master coordination. PLT owns infrastructure remediation, DBRE ES validation. Avoid uncoordinated multi-node restarts; verify expected nodes and recovered shard availability.

## 4. ES-INC-003 — Search slowness

**Symptoms:** increased APP P95/P99, 429/errors, query/fetch latency and search queue.

~~~~http
GET /_nodes/stats/indices/search
GET /_cat/thread_pool?v&h=node_name,name,active,queue,rejected,completed
GET /_nodes/hot_threads?threads=5
GET /_tasks?detailed=true&actions=*search*
GET /_cat/shards?v&h=index,shard,prirep,state,store,node
~~~~

Separate query versus fetch regression, co-ordinator CPU/heap, shard fan-out, request size/pagination, expensive aggregation/sort/script, merge/IO and recent changes. APP owns query code; DBRE execution analysis. Validate end-user latency, error rate and throughput, not only cluster GREEN.

## 5. ES-INC-004 — Heap, GC, circuit breakers

~~~~http
GET /_nodes/stats/jvm,breaker
GET /_nodes/stats/indices/fielddata,query_cache,segments
GET /_nodes/hot_threads?threads=5
~~~~

Review aggregation memory, fielddata mapping, concurrent requests, breaker trip rate, heap and GC. Reduce expensive request pressure with APP coordination. Do not blindly raise breaker limits, clear all caches or resize heap without review.

## 6. ES-INC-005 — Coordinating-node CPU saturation

~~~~http
GET /_cat/nodes?v&h=name,node.role,cpu,heap.percent,uptime
GET /_nodes/stats/os,process,jvm,thread_pool
GET /_nodes/hot_threads?threads=10
~~~~

Compare coordinator CPU, fan-out, reduce work, large result sets, search concurrency, data node pressure and recent capacity reductions. APP owns excessive query/result behavior; PLT supports scaling; DBRE validates. Return to approved capacity if right-sizing triggered an incident and change policy permits it.

## 7. ES-INC-006 — Disk watermarks and write blocks

~~~~http
GET /_cat/allocation?v
GET /_nodes/stats/fs
GET /_cluster/settings?include_defaults=true
GET /_cat/indices?v&h=index,pri,rep,store.size,pri.store.size&s=store.size:desc
~~~~

Common defaults: low 85%, high 90%, flood-stage 95%, subject to actual version/settings/max headroom. Prioritize restoring disk capacity and investigating growth, ILM and shard allocation. **Do not turn off disk protections or delete indices as an emergency shortcut.** Remove read-only blocks only after safe headroom returns and authorization is obtained where needed.

## 8. ES-INC-007 — Indexing backlog/write rejections

~~~~http
GET /_nodes/stats/indices/indexing,refresh,merge,translog
GET /_nodes/stats/indexing_pressure,thread_pool
GET /_cat/thread_pool?v&h=node_name,name,active,queue,rejected,completed
GET /your-index-name/_settings
~~~~

Review bulk batch size, client concurrency/backoff, ingest failures, refresh interval, replicas, merge pressure, upstream freshness and disk/CPU. Coordinate APP/DATA throttling; do not unilaterally disable production replicas. Verify document freshness and error-free indexing.

## 9. ES-INC-008 — Oversized shards, deleted docs, merge pressure

~~~~http
GET /_cat/shards?v&h=index,shard,prirep,state,store,node
GET /_cat/indices?v&h=index,docs.count,docs.deleted,store.size,pri.store.size
GET /your-index-name/_stats/docs,store,merge,segments
GET /_nodes/stats/indices/merge,segments
~~~~

Investigate primary shard size, delete/update patterns, indexing rate, merger time, throttling and disk IO. Prefer well-planned reindex/rollover and lifecycle fixes for structural problems. Force merge is resource intensive, can require substantial disk headroom, and should not be routine on a write-active index; Elasticsearch 7.17 force merge tasks are not generally cancellable.

## 10. ES-INC-009 — Query cache / fielddata

~~~~http
GET /_nodes/stats/indices/query_cache,fielddata
GET /_nodes/stats/jvm,breaker
GET /your-index-name/_stats/query_cache,fielddata
~~~~

Compare eviction **rates**, hit/miss patterns, heap, breaker events, aggregation fields and application latency. Cumulative evictions alone do not demonstrate an incident. Avoid automatic cache clears.

## 11. ES-INC-010 — Snapshot/recovery failures

~~~~http
GET /_slm/policy
GET /_slm/stats
GET /_snapshot/_all
GET /_snapshot/your-repository/_current
GET /_snapshot/your-repository/your-snapshot-name
~~~~

Check latest complete snapshot versus RPO, repository access, cloud permissions, failures and version/index compatibility. PLT supports repository infrastructure. Controlled repository verification and restores require authorized operations; a snapshot success or repository verification is **not** evidence of completed restore test.

## 12. ES-INC-011 — ILM or rollover failure

~~~~http
GET /_ilm/status
GET /_all/_ilm/explain?only_errors=true
GET /your-index-name/_ilm/explain
GET /your-index-name/_settings
~~~~

Check policy/phase/action/step, alias and write-index state, thresholds and allocation. Obtain approval before ILM retries, changes or any retention-related action.

## 13. ES-INC-012 — Authentication or authorization errors

Differentiate 401 authentication from 403 permissions; inspect RBAC, TLS/certificate, service credentials, rotation changes and secret integration with SEC/APP. Do not disable auth/TLS or share tokens in incident documentation. Restore approved least-privilege service access and confirm denial of unauthorized requests.

## 14. Escalation matrix

| Observation | DBRE | Partner |
|---|---|---|
| RED/unavailable critical primary | Technical incident lead | PLT + APP + Incident command |
| High search P99, coordinator CPU | ES diagnostic lead | APP for query/concurrency |
| Indexing lag or failures | ES diagnostic lead | DATA for pipeline |
| Disk full, node lost | ES diagnostic lead | PLT for storage/hosts |
| Snapshot stale | Snapshot investigation | PLT/cloud for repository |
| Incorrect data or deletion proposal | Technical support | DATA authorization, APP verification |
| Unauthorized access | Platform evidence | SEC incident lead |

## 15. Controlled mutation checklist

Actions requiring change/incident approval include: restart, replica/refresh change, allocation updates, force merge, reindex, alias cutover, snapshot restore, cache clear, role changes, ILM/retention modifications, and **any deletion**.

Before acting: incident/ticket, baseline, index and app dependencies, authorization, impact, rollback/recovery method, execution owner, time, validation and evidence. A snapshot is only recovery protection if verified appropriate and restorable.

## 16. Incident communication template

| Field | Entry |
|---|---|
| Incident ID / P-level | |
| Start UTC / cluster / application | |
| Confirmed impact (search, writes, freshness) | |
| Current health and leading evidence | |
| Diagnosed cause or uncertainty | |
| Mitigation, risk and approvals | |
| Next communication/checkpoint | |
| Technical lead and incident commander | |
| Recovery validation from APP/DBRE | |

Write factual, blameless updates. Do not assert root cause before evidence exists or claim service recovery based solely on cluster status.

## 17. Post-incident RCA

1. Impact statement and detection mechanism.
2. UTC timeline: event, alert, triage, mitigation, validation, closure.
3. Evidence: Elasticsearch stats/time series, node logs, sanitized query profiles, app SLIs, deployment/change records.
4. Primary triggering cause, contributing factors and detection gaps.
5. Immediate remediation and longer-term prevention, each with owner, due date and measurable acceptance.
6. Follow-up validation, improved alerts/runbooks and stakeholder review.

Avoid PHI, EMPI, emails, names, credentials and patient-level data in broadly shared evidence.

## 18. Milestone acceptance

- [ ] Twelve scenario runbooks reviewed by DBRE and incident partners.
- [ ] Read-only API syntax and permissions validated in staging.
- [ ] Remediation safety/change gates agreed and tested.
- [ ] P1/P2 incident routing and communication rehearsed.
- [ ] Business-service recovery validation documented.
- [ ] One representative tabletop or staging exercise complete.
- [ ] RCA format adopted with owner/action tracking.

**Completion:** Documentation alone does not certify runbooks; staging exercises and sign-off are required.

## References
- [Allocation explain API — 7.17](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/cluster-allocation-explain.html)
- [Node stats API — 7.17](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/cluster-nodes-stats.html)
- [Force merge API — 7.17](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/indices-forcemerge.html)
- [Snapshot REST APIs — 7.17](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/snapshot-restore-apis.html)
