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
  -X GET "$ES_URL/_cat/allocation?v&bytes=gb&h=node,shards,disk.indices,disk.used,disk.avail,disk.total,disk.percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri,rep,docs.count,store.size,pri.store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/settings?include_defaults=true&filter_path=**.disk.watermark*,**.disk.threshold_enabled"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_nodes/stats/fs?pretty"
```

Capture worst-node utilization (not only average), free GB, allocation and disk growth by tier; check snapshots, segment merges, ongoing relocation and reindex jobs.

## Approved procedure

1. Calculate 30/60/90-day headroom and proposed storage increase with replica, relocation, merge and reindex overhead.
2. Compare supported options: add capacity, move workloads, reduce retained data under approved policy, or optimize indexing strategy; document FinOps forecast.
3. Obtain platform change approval and application/data-impact signoff. **Do not disable disk watermarks** as routine mitigation.
4. Perform cloud/platform resize using the provider-approved workflow (outside Elasticsearch REST API); monitor shard allocation and recovery.
5. Recheck disk, write failures, cluster health and sustained growth after stabilization.

## Production capacity decision guide
Track both the **most utilized data node** and total physical storage; averages can conceal one node crossing a watermark. Compare effective configured watermarks (`GET /_cluster/settings?include_defaults=true`) with actual disk usage. Defaults vary by version and deployment; do not assume a static threshold.

**Collect the capacity baseline (read-only).**

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/allocation?v&bytes=gb&h=node,shards,disk.indices,disk.used,disk.avail,disk.total,disk.percent"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri,rep,docs.count,pri.store.size,store.size"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/settings?include_defaults=true&pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/health?pretty"
```

**Sizing model.** Project per-tier *primary bytes × (1 + planned replica count)*, adding anticipated daily growth × forecast days, uneven placement, segment merge, relocation, failure and concurrent reindex headroom. Quote both usable disk and physical provisioned disk, and identify whether the projected limiting node reaches the approved early-warning threshold within the provisioning lead time. Clearly identify whether figures are GB or GiB.
**Decision matrix.** If growth is sustained, request expansion or tier rebalancing; if retention is the driver, obtain Data Engineering + Business Owner approval before changing policy; if a one-time reindex doubles peak storage, temporarily add capacity and approve the cost through FinOps; if flood-stage blocks writes, initiate the incident process rather than performing a routine cleanup.
**Go/no-go.** A resize needs provider-specific steps, required service capacity, tested rollback, approved outage tolerance, cost estimate, and application ingestion-rate verification. Do not treat lowering watermarks, deleting unapproved data, or clearing blocks while disk remains full as remediation.
**Exit.** Record per-node max used%, total free GB, allocation health, absence of persistent write block errors, growth-rate estimate, and monitoring through the approved stabilization period. Savings or recovered disk are recorded **after** merges/deletions settle; distinguish logical deleted data from actual disk reclaimed.

## Stop / escalate

Stop for unexpected lost shard copies, flood-stage blocks, worsening write failures or inadequate headroom. Escalate to incident response instead of proceeding as routine maintenance.

## Success criteria and evidence

Attach per-node before/after disk GB and percent, aggregate used GB, forecast, approved cost estimate, alerts resolved and open follow-ups.

## Rollback / recovery

Use the provider's tested capacity rollback only when safe. Avoid shrinking storage below actual data + recovery headroom. Follow restore procedures if data loss occurs.

## Official references

- https://www.elastic.co/docs/troubleshoot/elasticsearch/fix-watermark-errors
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cat-allocation
