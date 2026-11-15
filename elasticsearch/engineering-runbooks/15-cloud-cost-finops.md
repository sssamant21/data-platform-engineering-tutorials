# 15 — Elasticsearch cloud cost optimization and FinOps

> **Draft for peer review · Technical owner:** FinOps (cost reporting)  
> **Stakeholders / approval:** DBRE/SRE: safe capacity; Data Engineering + Business: retention; Application: demand  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for monthly actual-versus-budget reviews, cost anomalies and planned efficiency improvements.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cluster/stats?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri.store.size,store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/nodes?v&h=name,roles,cpu,heap.percent,disk.used_percent"
```

REST endpoints do **not** expose authoritative cloud billing data. Combine them with cloud provider invoices, tags, commitments, data-transfer/storage bills and allocated business-service costs.

## Approved procedure

1. FinOps compiles monthly costs by environment/service/owner with actual, forecast, budget and anomalies.
2. DBRE provides node sizes, storage/shard utilization, reservations, uptime and performance headroom.
3. Data Engineering and Business Owner provide demand growth and retention needs; Application gives search/QPS forecasts.
4. Rank candidate changes by estimated savings, complexity, risk, performance impact and recovery cost; include temporary double-storage for reindex.
5. Execute optimizations only via reviewed DBRE change runbook, then verify service SLOs and realized savings after bill-cycle reconciliation.

## Stop / escalate

Stop if proposed savings compromise approved reliability, data retention, security or recovery requirements. No unilateral FinOps reduction of production capacity.

## Success criteria and evidence

Record owner, cost baseline, forecast, approval, infrastructure/service metrics, realized savings and business impact.

## Rollback / recovery

If optimization violates reliability gates, DBRE leads supported reversal while FinOps updates forecast and variance.

## Official references

- https://www.finops.org/framework/
- https://www.elastic.co/docs/deploy-manage/production-guidance/optimize-performance
