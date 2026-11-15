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
  -X GET "$ES_URL/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason,node"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X POST "$ES_URL/_cluster/allocation/explain?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/recovery?v&h=index,shard,time,type,stage,source_node,target_node,files_percent,bytes_percent"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/settings?include_defaults=true&pretty"
```

Review disk watermarks, available data roles, tier allocation filters, delayed allocation, recovery bandwidth and snapshot/repository health.

## Approved procedure

1. Locate affected exact shard and classify missing primary versus replica, recoverable copy versus unavailable copy.
2. Consult allocation-explain deciders and node logs to understand why allocation is denied or delayed.
3. Fix underlying capacity/topology/tier/filter cause through approved platform change; do not bypass safety by arbitrarily allocating stale primaries.
4. Monitor recovery and avoid concurrent high-throughput reindex/merge jobs.
5. If no valid copy remains, escalate to snapshot restore and data-loss assessment.

## Exact-shard allocation investigation
**Distinguish red (primary unavailable) from yellow (replica unavailable)** before choosing remediation. Determine whether an active healthy copy exists elsewhere, whether allocation deciders reject the shard, and whether the cause is node loss, tier filter, awareness, disk headroom, recovery throttling or a failed index operation. `/_cluster/allocation/explain` may return information about a different unassigned shard if called without a body; target the exact shard when evidence is needed.

**Read-only inventory.**

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason,node"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/recovery?v&active_only=true"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/settings?include_defaults=true&pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/allocation?v&bytes=gb"
```

**Target an identified unassigned shard (diagnostic POST, no cluster mutation).** Edit the JSON with a shard/index from the `/_cat/shards` output; example `primary:false` is for an unassigned replica only.

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" \
  -X POST "$ES_URL/_cluster/allocation/explain?pretty" \
  -H "Content-Type: application/json" \
  --data-binary @approved-allocation-explain.json
```

Example content for `approved-allocation-explain.json` (replace exact values after inspection):

```json
{ "index": "approved-index", "shard": 0, "primary": false }
```

**Decision tree.** If disk decider rejects placement, follow disk-capacity procedure. If tier/awareness rules prevent placement, request a topology review; never silently weaken zone redundancy. If the only copy was lost, declare potential data-loss incident and use snapshot recovery. If relocation is already progressing, avoid concurrent forced reroutes. Force-allocating a stale primary with data-loss acceptance is intentionally **excluded** from this runbook and requires a separate exceptional recovery authorization.
**Closure.** Re-run exact-shard state, capture previously blocking deciders, confirm intended number of active replicas for the protected indices, application availability and complete recovery; document exceptions still open and their risk owners.

## Stop / escalate

Stop on data-loss risk, lack of valid shard copies, rapidly growing unassigned primary count or unexpected cluster state change.

## Success criteria and evidence

Record allocation explanations, action taken, shard recovery duration and final index/application checks.

## Rollback / recovery

Undo only recorded reversible allocation filters if approved. For missing copies, use tested snapshot recovery rather than unsafe reroute.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cluster-allocation-explain
- https://www.elastic.co/docs/reference/elasticsearch/rest-apis/index-recovery
