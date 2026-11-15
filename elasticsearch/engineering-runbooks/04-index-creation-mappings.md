# 04 — Index creation and mapping changes

> **Draft for peer review · Technical owner:** Data Engineering  
> **Stakeholders / approval:** DBRE/SRE: platform impact; Application: query contract; Index Owner: data purpose  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for onboarding a data source, modifying schema, index naming, analyzer or template.

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
  -X GET "$ES_URL/_cat/indices?v&h=index,health,pri,rep,docs.count,store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_index_template?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/health?pretty"
```

Obtain field types, cardinality, expected document IDs, ingest volume, update/deletion behavior, retention, query patterns, alias and growth estimate.

## Approved procedure

1. Data Engineering prepares an approved request including source-to-target mapping, desired index templates, dynamic mapping policy and sample documents.
2. DBRE reviews shard/replica/refresh and resource impact; Application Engineering tests query/filter/aggregation compatibility.
3. Apply *the reviewed* index payload, never illustrative defaults:

```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 -X PUT "$ES_URL/approved-index-v1" \
 -H 'Content-Type: application/json' --data-binary @approved-index.json
```

4. Verify mappings/settings and write alias, then run sample ingestion to nonproduction first.
5. For incompatible mapping-type changes, use a new index and the reindex/alias-cutover procedure instead of attempting an in-place type change.

## Production schema approval checklist
**Required schema contract.** Include business domain, source entity and SLA, unique ID, expected updates/deletes, primary routing key and mapping requirements; record field cardinality, search/filter/aggregation patterns, analyzer choices, index naming, write/read alias names, initial data size, forecast growth, retention and security classification. Data Engineering signs the contract; DBRE reviews performance/capacity; Application signs query compatibility.

**Before applying approved payloads:**

```bash
export ES_INDEX="approved-index-v1"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_index_template?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/indices/$ES_INDEX?v&h=index,health,pri,rep,docs.count"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/health?pretty"
```

The named index query returning 404 can be expected **only if index creation has not occurred**; distinguish that from connectivity or privilege errors. Review template precedence and whether dynamic mapping is restricted. A PUT index request can create resources immediately; never use unapproved sample mappings against production.
**After creation (read-only evidence).**

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/$ES_INDEX/_mapping?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/$ES_INDEX/_settings?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/aliases?v&h=alias,index,is_write_index"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/shards/$ES_INDEX?v"
```

**Acceptance.** Verified fields have intended types; exact aliases target expected indices; the write alias has a single intended write destination; index capacity/shard count conform to approved standards; a staging ingest sample and representative application queries pass. For mapping type changes, build a new index and use the reindex/cutover runbook; do not claim that changing existing field types in place is reversible.

## Stop / escalate

Stop on unexpected dynamic fields, incompatible mappings, error spikes, shard/limit risk, or applications addressing physical indices directly where an alias contract is required.

## Success criteria and evidence

Record mappings, schema tests, representative queries, source-to-target reconciliation and approvals in Jira.

## Rollback / recovery

For new unused test indices, use scoped approved deletion. For production mapping changes, rollback usually requires the prior index/alias and safe data reconciliation; do not assume mapping type changes can be undone.

## Official references

- https://www.elastic.co/docs/manage-data/data-store/mapping
- https://www.elastic.co/docs/manage-data/data-store/index-basics
