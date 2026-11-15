# 08 — Search and indexing performance troubleshooting

> **Draft for peer review · Technical owner:** DBRE/SRE (platform diagnosis)  
> **Stakeholders / approval:** Application: query behavior; Data Engineering: ingestion/mappings  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for search latency, high queue/rejection counts, indexing backlog or CPU/heap spikes.

## Execution guardrails (all environments)

- **Status: DRAFT — not production-certified.** These are human-operated procedures; obtain the required Jira/change approvals, validate against the deployed version in staging, and attach evidence before production use.
- Identify cluster UUID/name, environment, deployment/version, authorized operator, ticket and rollback owner. Do **not** assume a green cluster alone makes a change safe.
- Use scoped, least-privilege accounts. Protect credentials; never paste passwords or personal/health data in tickets, logs or Git. Do not disable TLS verification (`-k` / `--insecure`).
- Substitute the exact approved index/alias. Never run mutating commands with wildcard patterns, `_all`, or on system/managed indices unless an explicitly approved platform procedure requires them.
- The commands below use curl Basic Authentication with a **username only**; curl prompts for the password (avoid embedding `user:password` in shell history or process arguments). No client or CA certificate file is passed. For HTTPS, normal server certificate verification remains enabled. Windows PowerShell uses `curl.exe`.

```bash
export ES_URL="https://es.example.internal:9200"
export ES_USER="your-least-privilege-user"
# Baseline: verify target cluster and authenticated identity.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  "$ES_URL/"
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  "$ES_URL/_security/_authenticate"
```

On PowerShell: `curl.exe --basic --user "$env:ES_USER" "$env:ES_URL/_cluster/health?pretty"` (first set `$env:ES_URL`, `$env:ES_USER`). For Windows curl builds lacking `--fail-with-body`, use `--fail` and inspect the response. JSON request files are checked into the change ticket after removing sensitive values; never commit real credentials.

## Prechecks / read-only diagnostics

```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_nodes/stats/jvm,os,fs,thread_pool?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_nodes/stats/indices/search,indexing,merge,query_cache,fielddata?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/thread_pool/search,write?v&h=node_name,name,active,queue,rejected,completed"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_nodes/hot_threads?threads=3&ignore_idle_threads=true"
```

Compare before/after rate deltas, not cumulative counts alone; align Grafana and Kafka consumer lag, request volume, p95/p99 and recent releases.

## Approved procedure

1. Determine whether latency is client-side, coordinator-side, data-node, ingestion contention, or disk/merge bound.
2. Application team provides exact query shape, `size`, sort/aggregation behavior, routing, concurrency and timeouts; profile controlled test queries outside peak traffic.
3. Data Engineering reviews mapping/cardinality, source changes, document growth and bulk writer settings.
4. DBRE evaluates shard fan-out, unbalanced nodes, GC, CPU, disk contention, caches, thread pools and rejections.
5. Implement approved low-risk query/pipeline fixes first; treat infrastructure configuration changes as separate reviewed changes.
6. Repeat representative load test and monitor for regression.

## Stop / escalate

Stop if experimentation increases production load, repeated circuit breakers occur, or cluster stability degrades; use incident process.

## Success criteria and evidence

Attach query fingerprints, latency distribution, load and data size, before/after queue/rejection deltas, capacity effects and signoff.

## Rollback / recovery

Revert the identified application/pipeline/config change with owners' agreement; validate performance and correctness before closing.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-nodes-stats
- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-profile
