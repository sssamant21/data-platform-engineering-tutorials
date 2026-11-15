# 10 — Cluster scaling and compute right-sizing

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Application + Data: SLA/workload confirmation; FinOps: financial review; Change Authority: relevant approvals  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for CPU/memory/node resizing, adding/removing data nodes or coordinating nodes and cloud-cost optimization.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/nodes?v&h=name,roles,cpu,heap.percent,ram.percent,disk.used_percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/stats/jvm,os,fs,thread_pool?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cluster/stats?pretty"
```

Collect 2+ weeks of peak/trend CPU, heap/GC, disk, latency, search/index QPS, query sizes, rejection rates, shard sizes and failure headroom.

## Approved procedure

1. Propose before/after node specs, topology, resource constraints, cost impact, acceptance thresholds, and rollback configuration.
2. Data and Application teams approve forecast loads and service-impact expectations; FinOps validates savings assumptions.
3. Execute changes through the cloud/platform provider procedure in the approved change window; **not by ad hoc Elasticsearch cluster-setting changes**.
4. Validate node joins/shard allocation/recovery, end-to-end search/index behavior, metrics and rollback readiness.
5. Maintain enhanced monitoring across a defined stabilization period and only then record savings.

## Stop / escalate

Abort on persistent rejects, sustained high JVM/GC, unassigned primaries, disk headroom loss, or p95/p99 above agreed SLO.

## Success criteria and evidence

Record actual new capacity, baseline and post-change charts, search/index latency, error budgets and realized vs expected cost.

## Rollback / recovery

Return to the prior supported compute profile if capacity test fails; verify provider rollback sequence and cluster health first.

## Official references

- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/cluster-health
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-nodes-stats
