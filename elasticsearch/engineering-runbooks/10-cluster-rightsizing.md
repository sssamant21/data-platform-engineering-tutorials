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
  -X GET "$ES_URL/_cat/nodes?v&h=name,roles,cpu,heap.percent,ram.percent,disk.used_percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_nodes/stats/jvm,os,fs,thread_pool?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/stats?pretty"
```

Collect 2+ weeks of peak/trend CPU, heap/GC, disk, latency, search/index QPS, query sizes, rejection rates, shard sizes and failure headroom.

## Approved procedure

1. Propose before/after node specs, topology, resource constraints, cost impact, acceptance thresholds, and rollback configuration.
2. Data and Application teams approve forecast loads and service-impact expectations; FinOps validates savings assumptions.
3. Execute changes through the cloud/platform provider procedure in the approved change window; **not by ad hoc Elasticsearch cluster-setting changes**.
4. Validate node joins/shard allocation/recovery, end-to-end search/index behavior, metrics and rollback readiness.
5. Maintain enhanced monitoring across a defined stabilization period and only then record savings.

## Capacity baseline, staged rollout and service acceptance
**Establish workload equivalence.** The baseline must cover peak and typical search QPS, concurrent queries, indexing events/sec, bulk load, p95/p99 search latency, heap/GC, CPU, disk IOPS, network, index size, primary/replica count and shard recovery time. Include peak-hour and failure-domain test evidence; low average CPU alone is not a sizing argument.

**Read-only before/after collection.**

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_nodes?filter_path=nodes.*.name,nodes.*.roles,nodes.*.os.allocated_processors,nodes.*.jvm.mem.heap_max_in_bytes&pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_nodes/stats/os,process,jvm,fs,thread_pool?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/health?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/allocation?v&bytes=gb"
```

**Change request.** For each node role, state current/proposed size, node count/AZ distribution, traffic assumptions, monthly cloud price impact, extra rollback capacity, provider orchestration steps, expected service impact and 24-hour/7-day monitoring owner. Validate that coordinating nodes can handle concurrent fan-out and response serialization, not just data-node search CPU.
**Execution order.** Follow deployment-provider approved resize order and one bounded change at a time; wait for recoveries and service tests before proceeding. A hosted deployment resize is **not** performed through arbitrary `_cluster/settings` commands. Use the provider's capacity rollback method; restoring a previous size may not be instantaneous or possible without sufficient availability.
**Go/no-go and postchange.** Define objective thresholds in the Jira ticket before execution (search p95/p99, 429/5xx, node CPU, heap/GC, disk headroom, indexing lag and shard availability). DBRE leads go/no-go, Application validates functional and latency SLOs, Data Engineering validates data freshness, FinOps checks realized savings only after stable service.

## Stop / escalate

Abort on persistent rejects, sustained high JVM/GC, unassigned primaries, disk headroom loss, or p95/p99 above agreed SLO.

## Success criteria and evidence

Record actual new capacity, baseline and post-change charts, search/index latency, error budgets and realized vs expected cost.

## Rollback / recovery

Return to the prior supported compute profile if capacity test fails; verify provider rollback sequence and cluster health first.

## Official references

- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/cluster-health
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-nodes-stats
