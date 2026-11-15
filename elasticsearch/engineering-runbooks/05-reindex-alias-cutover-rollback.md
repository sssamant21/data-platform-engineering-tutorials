# 05 — Reindexing, alias cutover and rollback

> **Draft for peer review · Technical owner:** DBRE/SRE (operational execution)  
> **Stakeholders / approval:** Data Engineering: correctness; Application: search/write acceptance; Index Owner: approval  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for mapping changes, index redesign, shard remediation, or migration between physical indices.

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
  -X GET "$ES_URL/_alias?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/indices?v&h=index,pri,rep,docs.count,store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/health?pretty"
```

Confirm alias target(s), **read alias versus write alias**, routing/filter behavior, and whether alias intentionally targets multiple indices. Inventory writers beyond the application (Kafka consumers, bulk jobs, replay services).

## Approved procedure

1. Approve source/destination, data reconciliation method, cutover gate, write pause/replay plan, rollback deadline and validation owners.
2. Reindex using the reviewed source/destination JSON (runbook 03). Capture `created`, `updated`, `version_conflicts`, `failures` and expected record counts.
3. Ensure in-flight writes are reconciled. Verify application behavior on the new index **without prematurely moving production aliases**.
4. Review the exact atomic alias payload for this particular alias topology. If a separate write alias exists, migrate it explicitly; preserve alias routing and filter attributes.
5. Execute only after the go/no-go checkpoint:

```bash
# approved-alias-actions.json, reviewed by Data Engineering + Application + DBRE.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 -X POST "$ES_URL/_aliases" \
 -H 'Content-Type: application/json' --data-binary @approved-alias-actions.json
```

6. Verify alias mapping; test writes and searches, including routed/multi-index queries and expected filtering.
7. Keep source index for the approved stabilization period.

## Canonical zero-loss cutover protocol
**Separate read and write contracts.** Record every application and Kafka/ETL writer, their physical target or alias, any routing and filter settings, and the last source checkpoint (offset/LSN/event ID). Agree whether to freeze writes, replay deltas, or perform a verified dual-write. If there is no complete update-capture mechanism, approve a bounded write pause; a large reindex is not an ongoing replication service.

**Read-only pre-cutover snapshots.**

```bash
export ES_READ_ALIAS="approved-read-alias"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_alias/$ES_READ_ALIAS?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/aliases?v&h=alias,index,is_write_index"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/health?pretty"
```

**Cutover sequence:**
1. Freeze or reconcile writes according to the approved ingestion plan; prove all Kafka offsets/replay checkpoints or source version watermarks are accounted for.
2. Verify destination mapping/aliases, expected document keys, application queries (including EMPI routing if used), and query SLA. Run tests against the new physical index without changing production aliases.
3. Approve the *exact* `approved-alias-actions.json` diff. For a one-target read alias, this generally removes the old target and adds the new; for write aliases, ensure exactly one intended `is_write_index`. Preserve relevant alias filters and routing; do not re-create them from memory.
4. Issue the existing `_aliases` request once, capture `acknowledged`, then immediately read back alias state and run search plus write smoke tests.
5. Re-enable or redirect writers under the agreed sequencing. Monitor for a defined stabilization interval, preserving old index and evidence.
**Stop conditions:** unknown writers, lagging offsets, key mismatch, missing alias filter/routing, write failures, unexpected multi-index alias selection, high indexing rejects or failed smoke tests. Escalate before partial fallback.
**Rollback classification:** Read-only cutover with unchanged source may allow alias reversal. Write cutover requires verified reverse replay of any destination-only writes *before* alias reversal. Document an explicit latest safe rollback time, recovery owner and post-cutover-write reconciliation test.
**Jira closure:** old/new aliases JSON, operator/time, approved alias actions diff, application and Data Engineering signoffs, query p95/p99, missing record count, final writer checkpoint and old-index retention deadline.

## Stop / escalate

Abort cutover if unconsumed Kafka offsets, document-count discrepancies, open writes, unknown index clients, failed functional tests, or unapproved alias actions.

## Success criteria and evidence

Save before/after alias JSON, completeness checks, failed task stats, latest writes accounted for, application approval, rollback owner, and health/latency.

## Rollback / recovery

For a read-only cutover, restoring the alias may be sufficient if old data remains current. For a write cutover, first reconcile destination-only writes back into a supported source; an alias reversal without this creates data loss.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-update-aliases
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-reindex
- https://www.elastic.co/docs/manage-data/data-store/aliases
