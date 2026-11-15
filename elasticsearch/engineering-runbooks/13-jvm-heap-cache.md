# 13 — JVM, heap, cache and memory troubleshooting

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Application: query load; Data Engineering: mappings/ingestion  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for GC pauses, heap near circuit-breaker limits, fielddata/query-cache pressure, OOM or node crashes.

## Execution guardrails (all environments)

- **Status: DRAFT — not production-certified.** These are human-operated procedures; obtain the required Jira/change approvals, validate against the deployed version in staging, and attach evidence before production use.
- Identify cluster UUID/name, environment, deployment/version, authorized operator, ticket and rollback owner. Do **not** assume a green cluster alone makes a change safe.
- Use scoped, least-privilege accounts. Protect credentials; never paste passwords or personal/health data in tickets, logs or Git. Do not disable TLS verification (`-k` / `--insecure`).
- Substitute the exact approved index/alias. Never run mutating commands with wildcard patterns, `_all`, or on system/managed indices unless an explicitly approved platform procedure requires them.
- The commands below use curl Basic Authentication with a **username only**; curl securely prompts for the password (avoid embedding `user:password` in shell history or process arguments). The same command is available as `curl.exe` in Windows PowerShell.

```bash
export ES_URL="https://es.example.internal:9200"
export ES_USER="your-least-privilege-user"
export ES_CA_CERT="/path/to/elastic-ca.pem"
# Baseline: verify target cluster and authenticated identity.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" "$ES_URL/"
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" "$ES_URL/_security/_authenticate"
```

On PowerShell: `curl.exe --basic --user "$env:ES_USER" --cacert "$env:ES_CA_CERT" "$env:ES_URL/_cluster/health?pretty"` (first set `$env:ES_URL`, `$env:ES_USER`, `$env:ES_CA_CERT`). For Windows curl builds lacking `--fail-with-body`, use `--fail` and inspect the response. JSON request files are checked into the change ticket after removing sensitive values; never commit real credentials.

## Prechecks / read-only diagnostics

```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/stats/jvm,breaker,indices?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/stats/indices/fielddata,query_cache,request_cache,segments?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/hot_threads?threads=5&ignore_idle_threads=true"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/nodes?v&h=name,heap.percent,ram.percent,cpu,uptime"
```

Look at time trends of heap and GC, node roles, circuit-breaker events, mapping types, agg/query workload and off-heap/OS memory.

## Approved procedure

1. Identify workload trigger and whether event aligns with deployments, bulk ingestion, fielddata aggregations or shard relocations.
2. Review field usage and `text` aggregations; prefer `keyword` fields where appropriate and data-team approved mapping redesign over fielddata enablement.
3. Check query sizes, aggregations, shard counts, caches and task concurrency; fix source demand before considering memory expansion.
4. DBRE evaluates node sizing and JVM settings using the supported deployment guidance; use separate approved capacity change.
5. Validate heap/GC, rejects, search p95/p99 and node stability.

## Stop / escalate

Stop on repeated OOM, circuit-breaker storm or node loss; declare incident. Avoid clearing caches as a routine fix (can increase load) and never tune JVM blindly.

## Success criteria and evidence

Provide symptom timeline, allocation/cache statistics, workloads correlated, mitigation and outcome metrics.

## Rollback / recovery

Rollback offending query/pipeline or approved config change; track follow-up actions to address root cause.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-nodes-stats
- https://www.elastic.co/docs/reference/elasticsearch/configuration-reference/circuit-breaker-settings
