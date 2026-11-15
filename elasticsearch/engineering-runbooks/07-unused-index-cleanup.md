# 07 — Unused-index cleanup automation

> **Draft for peer review · Technical owner:** DBRE/SRE (automation, scheduling)  
> **Stakeholders / approval:** Index Owner: candidate verification/approval; Data Engineering: data requirements; Application: dependencies; FinOps: savings  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for staged, recurring cleanup according to the explicit approved environment-specific eligibility rules.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/indices?v&h=index,docs.count,creation.date.string,store.size"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/aliases?v&h=alias,index,is_write_index"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_nodes/stats/indices/indexing?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/allocation?v&bytes=gb&h=node,disk.used,disk.avail,disk.percent"
```

An index may be eligible under an agreed policy (e.g., no alias + age), but the **Index Owner verifies and approves the candidate list or the governing reusable rules**. Keep system/managed index exclusions and active reindex/write protection.

## Approved procedure

1. Index Owner supplies business eligibility, retention exceptions, scope, required frequency and approval evidence.
2. DBRE implements dry-run-only discovery first, with allowlisted scopes, exclusion controls, idempotent logging and report artifacts.
3. Data Engineering and Application Engineering confirm relevant ingestion/consumer dependencies where required by governance.
4. Obtain recurring automation approval, then schedule at the agreed cadence. For production, obey the organization's explicit deletion authorization model.
5. Perform scoped deletion **only via the approved automation**. Do not use ad hoc wildcard `DELETE` commands.
6. Record completed/failed deletions and after-stabilization disk measurements.

## Stop / escalate

Disable execution and escalate on unexpected candidate volume, active writes, missing approval, data hold, snapshot gap, mapping/alias swap in progress, or abnormal cluster pressure.

## Success criteria and evidence

Report candidates, approved scope, deleted/failed index names, operator/job ID, disk before/after (worst-node and aggregate), GB reclaimed and FinOps impact estimate; evidence must be retained per policy.

## Rollback / recovery

Pause future runs and preserve evidence; data deletion itself is not reversible. If a snapshot exists, initiate approved index-specific restore procedure and reconcile newer writes.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-delete
- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-snapshot-restore
