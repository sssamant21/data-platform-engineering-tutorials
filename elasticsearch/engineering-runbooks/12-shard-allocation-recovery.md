# 12 — Shard allocation and recovery troubleshooting

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Data and Application teams if data access affected  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use when shards are unassigned, relocating too slowly or failing after a restart/node event.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason,node"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X POST "$ES_URL/_cluster/allocation/explain?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/recovery?v&h=index,shard,time,type,stage,source_node,target_node,files_percent,bytes_percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cluster/settings?include_defaults=true&pretty"
```

Review disk watermarks, available data roles, tier allocation filters, delayed allocation, recovery bandwidth and snapshot/repository health.

## Approved procedure

1. Locate affected exact shard and classify missing primary versus replica, recoverable copy versus unavailable copy.
2. Consult allocation-explain deciders and node logs to understand why allocation is denied or delayed.
3. Fix underlying capacity/topology/tier/filter cause through approved platform change; do not bypass safety by arbitrarily allocating stale primaries.
4. Monitor recovery and avoid concurrent high-throughput reindex/merge jobs.
5. If no valid copy remains, escalate to snapshot restore and data-loss assessment.

## Stop / escalate

Stop on data-loss risk, lack of valid shard copies, rapidly growing unassigned primary count or unexpected cluster state change.

## Success criteria and evidence

Record allocation explanations, action taken, shard recovery duration and final index/application checks.

## Rollback / recovery

Undo only recorded reversible allocation filters if approved. For missing copies, use tested snapshot recovery rather than unsafe reroute.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cluster-allocation-explain
- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/index-recovery
