# 14 — Index data growth analysis and capacity forecasting

> **Draft for peer review · Technical owner:** Data Engineering (index growth)  
> **Stakeholders / approval:** DBRE/SRE: cluster capacity forecast; Business Owner + Data: retention; FinOps: forecast cost  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for weekly/monthly growth analysis, fastest-growing indices, projected disk needs and retention impacts.

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
  -X GET "$ES_URL/_cat/indices?v&bytes=gb&h=index,docs.count,pri.store.size,store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/shards?v&bytes=gb&h=index,prirep,store,node"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/allocation?v&bytes=gb&h=node,disk.used,disk.avail,disk.percent"
```

The APIs provide snapshots only. For daily/weekly/monthly/quarterly forecasts, collect metrics into Prometheus or a durable reporting store and compare time-stamped samples (avoid treating Elasticsearch counters as retained history).

## Approved procedure

1. Data Engineering attributes index size growth to new sources, record volume, schema changes, updates/deletes, and retention changes.
2. Publish per-index logical primary-store trends, document trends and estimated daily growth; investigate the top growers and anomalous deltas.
3. DBRE translates logical primary growth into physical capacity by replicas, data tier, merge overhead, relocation/failure headroom and worst-node usage.
4. Business Owner and Data Engineering verify retention assumptions; FinOps provides cloud price assumptions and variance.
5. Produce 30/60/90-day forecast with explicit baseline, estimation uncertainty, planned changes and action owner; schedule remediation before threshold breach.

## Repeatable index-level growth analysis
**Accountability:** Data Engineering produces index-by-index data growth, update/delete drivers and 30/60/90-day source volume projections. DBRE computes physical storage and failure/relocation headroom using actual shard placement and replicas. Business Owner + Data Engineering approve retention assumptions. FinOps models unit rates and cloud cost.

**Consistent read-only snapshot collection.** Capture at a fixed UTC time each day, store immutable CSV/JSON with cluster, tier, index, source owner and metric units; compare across equivalent intervals.

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri,rep,docs.count,docs.deleted,pri.store.size,store.size"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/shards?v&bytes=gb&h=index,shard,prirep,state,store,node"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/allocation?v&bytes=gb&h=node,disk.used,disk.avail,disk.total,disk.percent"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/health?pretty"
```

**Metric definitions.** Per-index *logical primary data* is `pri.store.size`; physical `store.size` includes replicas but may differ with relocating/recovering shards. `docs.count` can reflect nested documents; count and `docs.deleted` do not alone establish business record totals. Compute **daily net primary-store delta**, 7/30-day rolling median, and percent increase; identify the top index growers and indices with unusual deletes. Do not equate `docs.deleted` with immediately reclaimable bytes.
**Forecast methodology.** Project primary data by index using observed daily slope and known planned ingestion; multiply by approved replica factor, then account for tier-specific shard placement, segment merges, relocation and recoverability headroom, storage redundancy and peak node imbalance. Compare worst-node forecast to approved watermark thresholds and capacity-provisioning lead time; include a low/base/high scenario if growth is volatile.
**Output for review.** Per-index and per-tier growth tables, top 10 drivers, unexpected spikes, target capacity date, projected GB and cost change, 30/60/90-day forecasts, confidence and action owners. At least monthly, reconcile estimates with actuals and adjust the forecasting model; do not change retention solely to balance costs.

## Stop / escalate

Escalate unexpected acceleration, inconsistent data, unmanaged long-lived indices, or projected critical watermark before the capacity lead time.

## Success criteria and evidence

Attach graphs and CSV/export, top 10 growing indices, assumptions, 30/60/90 projections, capacity actions and cost impact.

## Rollback / recovery

If forecast model deviates, correct the baseline and assumptions rather than deleting data or lowering retention without approval.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cat-indices
- https://www.elastic.co/docs/troubleshoot/elasticsearch/fix-watermark-errors
