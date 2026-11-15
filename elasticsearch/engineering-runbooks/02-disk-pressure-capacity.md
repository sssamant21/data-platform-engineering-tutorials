# 02 — Disk pressure and storage expansion

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Data Engineering: index growth; Business/Data: retention; FinOps: cost; Application: impact  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for forecast disk exhaustion, watermark alerts, imbalance across data nodes, or planned expansion.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/allocation?v&bytes=gb&h=node,shards,disk.indices,disk.used,disk.avail,disk.total,disk.percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri,rep,docs.count,store.size,pri.store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cluster/settings?include_defaults=true&filter_path=**.disk.watermark*,**.disk.threshold_enabled"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/stats/fs?pretty"
```

Capture worst-node utilization (not only average), free GB, allocation and disk growth by tier; check snapshots, segment merges, ongoing relocation and reindex jobs.

## Approved procedure

1. Calculate 30/60/90-day headroom and proposed storage increase with replica, relocation, merge and reindex overhead.
2. Compare supported options: add capacity, move workloads, reduce retained data under approved policy, or optimize indexing strategy; document FinOps forecast.
3. Obtain platform change approval and application/data-impact signoff. **Do not disable disk watermarks** as routine mitigation.
4. Perform cloud/platform resize using the provider-approved workflow (outside Elasticsearch REST API); monitor shard allocation and recovery.
5. Recheck disk, write failures, cluster health and sustained growth after stabilization.

## Stop / escalate

Stop for unexpected lost shard copies, flood-stage blocks, worsening write failures or inadequate headroom. Escalate to incident response instead of proceeding as routine maintenance.

## Success criteria and evidence

Attach per-node before/after disk GB and percent, aggregate used GB, forecast, approved cost estimate, alerts resolved and open follow-ups.

## Rollback / recovery

Use the provider's tested capacity rollback only when safe. Avoid shrinking storage below actual data + recovery headroom. Follow restore procedures if data loss occurs.

## Official references

- https://www.elastic.co/docs/troubleshoot/elasticsearch/fix-watermark-errors
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cat-allocation
