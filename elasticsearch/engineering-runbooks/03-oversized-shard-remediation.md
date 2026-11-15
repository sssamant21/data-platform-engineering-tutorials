# 03 — Oversized shard remediation and planned reindexing

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Data Engineering: mappings/data validation; Application: functional signoff; FinOps: capacity cost  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use when shard size causes unacceptable recovery, merges, disk I/O, query latency or breaches approved workload-specific shard standards.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/shards?v&bytes=gb&h=index,shard,prirep,state,store,node"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri,rep,docs.count,pri.store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/stats/indices/merge?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cluster/health?pretty"
```

Review 10–50 GB as a **starting guideline**, not an absolute limit. Validate candidate primary-shard count against routing, data growth, search fan-out, and hardware. Alternative actions such as rollover may be safer for write-heavy time-series data.

## Approved procedure

1. Approve destination index name, mappings/settings, shard count, document IDs/routing, data update strategy, and read/write aliases. Verify `_source` is enabled.
2. Confirm capacity for source **plus** destination **plus replicas and transient operations**; verify snapshots and rollback window.
3. Request authorized destination creation using the reviewed JSON payload (do not auto-copy source mappings/settings):

```bash
# AFTER approval only; approved-destination.json holds the exact mappings/settings.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 --cacert "$ES_CA_CERT" -X PUT "$ES_URL/approved-destination-v2" \
 -H 'Content-Type: application/json' --data-binary @approved-destination.json
```

4. Run an approved asynchronous reindex payload with explicit source/destination, throttling and conflict policy:

```bash
# approved-reindex.json must define source.index and dest.index; reviewed by Data Engineering.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 --cacert "$ES_CA_CERT" -X POST \
 "$ES_URL/_reindex?wait_for_completion=false&requests_per_second=100" \
 -H 'Content-Type: application/json' --data-binary @approved-reindex.json
```

5. Capture returned task ID; monitor via `GET /_tasks/<task_id>` and monitor cluster/rejections/disk. Cancellation, if supported, is best effort and leaves partially copied documents.
6. Reconcile records and updates before cutover (snapshot-based reindex does **not** include later writes). Establish write pause, replay/dual-write, or verified delta capture per application design.
7. Perform an approved atomic alias update per runbook 05; validate representative searches, routing and write path.
8. Keep source index during the approved rollback retention period; no immediate source deletion.

## Stop / escalate

Stop if task failures, missing documents, unhandled source updates, uneven shard distribution, source/target mapping mismatch, unacceptable latency or storage headroom breach.

## Success criteria and evidence

Show final primary shard sizes, count reconciliation + key-based sampling, source/update catch-up evidence, application tests, alias state, latency/rejection baseline, actual temporary disk/cost.

## Rollback / recovery

If the source remains current and alias rollback is safe, atomically restore aliases. Once writes go to destination, reversing aliases alone is **not** sufficient: arrange verified reverse catch-up/replay before any rollback. Never delete original index until confirmed safe.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-reindex
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-update-aliases
- https://www.elastic.co/docs/reference/elasticsearch/index-lifecycle-actions/
