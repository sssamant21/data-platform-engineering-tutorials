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
  -X GET "$ES_URL/_cat/shards?v&bytes=gb&h=index,shard,prirep,state,store,node"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/indices?v&bytes=gb&h=index,pri,rep,docs.count,pri.store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_nodes/stats/indices/merge?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/health?pretty"
```

Review 10–50 GB as a **starting guideline**, not an absolute limit. Validate candidate primary-shard count against routing, data growth, search fan-out, and hardware. Alternative actions such as rollover may be safer for write-heavy time-series data.

## Approved procedure

1. Approve destination index name, mappings/settings, shard count, document IDs/routing, data update strategy, and read/write aliases. Verify `_source` is enabled.
2. Confirm capacity for source **plus** destination **plus replicas and transient operations**; verify snapshots and rollback window.
3. Request authorized destination creation using the reviewed JSON payload (do not auto-copy source mappings/settings):

```bash
# AFTER approval only; approved-destination.json holds the exact mappings/settings.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 -X PUT "$ES_URL/approved-destination-v2" \
 -H 'Content-Type: application/json' --data-binary @approved-destination.json
```

4. Run an approved asynchronous reindex payload with explicit source/destination, throttling and conflict policy:

```bash
# approved-reindex.json must define source.index and dest.index; reviewed by Data Engineering.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 -X POST \
 "$ES_URL/_reindex?wait_for_completion=false&requests_per_second=100" \
 -H 'Content-Type: application/json' --data-binary @approved-reindex.json
```

5. Capture returned task ID; monitor via `GET /_tasks/<task_id>` and monitor cluster/rejections/disk. Cancellation, if supported, is best effort and leaves partially copied documents.
6. Reconcile records and updates before cutover (snapshot-based reindex does **not** include later writes). Establish write pause, replay/dual-write, or verified delta capture per application design.
7. Perform an approved atomic alias update per runbook 05; validate representative searches, routing and write path.
8. Keep source index during the approved rollback retention period; no immediate source deletion.

## Shard-size remediation acceptance criteria and commands
**Trigger is an observed workload problem, not shard size alone.** Capture primary shard size distribution, query/fetch latency, merge throttling, disk I/O, and recovery duration. Evaluate rollover or shrink/split constraints before selecting reindexing. For an already-populated index whose desired primary-shard count cannot be changed directly, a destination index plus reindex may be required.

**Baseline and explicit scope.** Replace the example with the *approved existing physical index name*, not an alias spanning multiple indices.

```bash
export ES_SOURCE="approved-existing-index"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/shards/$ES_SOURCE?v&bytes=gb&h=index,shard,prirep,state,store,node"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/$ES_SOURCE/_stats/docs,store,merge,search,indexing?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/$ES_SOURCE/_mapping?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/$ES_SOURCE/_settings?pretty"
```

**Sizing approval.** Document primary-store GB (not the total including replicas), target shard count, expected size after reindex, routing skew, 30/90-day growth, maximum shards per node, and effect on search fan-out. 10–50 GB is only a starting guideline; measure representative searches, fetch latency, merges, and recovery in nonproduction. Forecast peak storage for *both full copies plus replicas* and transient operations.
**Execution gates.** (1) Approved destination mapping, settings, routing and ingest pipeline; (2) tested recovery point/snapshot; (3) source and destination write strategy (write pause, replay, or audited delta capture); (4) resource throttling and operator monitoring; (5) alias cutover and rollback owner; (6) Jira maintenance authorization. If any item is missing, do not start.
**Task verification.** Save the task ID returned by asynchronous `_reindex` and use this read-only query; replace the placeholder with the returned ID.

```bash
export ES_TASK_ID="replace-with-returned-task-id"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_tasks/$ES_TASK_ID?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/shards/approved-destination-v2?v&bytes=gb&h=index,shard,prirep,state,store,node"
```

**Reconciliation gate.** Compare source/destination key coverage, totals by business partition, rejected/failed documents, transformed values, routing semantics and the last source write acknowledged before cutover. Raw `_count` parity alone is insufficient if documents are updated or deduplicated.
**Exit and rollback.** Validate new shard sizes, query p95/p99, rejected operations, recovery behavior, data equivalence and alias targets; preserve source for the approved period. After the destination receives new writes, alias reversal alone is **not safe** without reverse replay or reconciliation.

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
