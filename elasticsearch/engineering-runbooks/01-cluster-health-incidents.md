# 01 — Cluster health and incident troubleshooting

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Application Engineering and Data Engineering according to impact  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for red/yellow cluster health, failing node, unassigned shard or degraded search/indexing service.

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

Capture a timestamped baseline and affected service/indices:

```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/health?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/nodes?v&h=name,ip,node.role,cpu,heap.percent,ram.percent,disk.used_percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason,node"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/pending_tasks?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X POST "$ES_URL/_cluster/allocation/explain?pretty"
```

Use allocation explain *without a body* to diagnose one unassigned shard; target a specific shard in an approved JSON body when necessary. Record upstream application error rates and recent changes.

## Approved procedure

1. Open/update incident; confirm impact, assigned incident commander and communication channel.
2. Separate cluster/node/storage causes from mapping, traffic, ingestion, and query causes; inspect host/cloud alerts.
3. Determine why shards are unassigned before considering reroute or allocation changes. Do not force-allocate stale primaries or clear cluster blocks blindly.
4. Identify least-disruptive supported mitigation; obtain approval for any risky setting change.
5. Monitor cluster health, recovery progress, latency, rejects and disk for the agreed stabilization interval.

## Stop / escalate

Stop if recovery threatens data integrity, unexplained node departures continue, disk crosses the approved critical threshold or there is no identified safe rollback. Escalate to incident command and Elastic/provider support as required.

## Success criteria and evidence

Record incident timeline, before/after `/_cluster/health`, unassigned shard count, error rates, customer impact, fix validation and corrective-action owner.

## Rollback / recovery

Revert *only the specific reversible configuration change* recorded in the ticket. For suspected data loss use the snapshot/restore runbook; never improvise destructive shard allocation.

## Official references

- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/cluster-health
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cluster-allocation-explain
