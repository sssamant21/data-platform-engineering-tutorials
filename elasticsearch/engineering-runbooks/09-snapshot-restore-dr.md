# 09 — Snapshot, restore and disaster recovery

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Data/Business: RPO/RTO and retention; Application: restore acceptance; Security: access  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use to verify backup posture, test restores, recover from deletion or plan a DR exercise.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_snapshot?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_snapshot/approved-repository/_all?verbose=false"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_slm/status?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cluster/health?pretty"
```

Confirm repository access, repository encryption/location, identity/privileges, snapshot SUCCESS state, indices included, version compatibility and business-defined RPO/RTO. Do not rely on a success flag alone: test restore.

## Approved procedure

1. Approve recovery scope, snapshot ID, target, expected data loss, application downtime, and return plan.
2. Prefer **isolated target** with a unique renamed index for validation. Ensure adequate capacity and no target-name collision.
3. Create approved restore request JSON specifying indices, rename pattern/replacement, `include_global_state:false` and `include_aliases:false` unless intentionally approved.

```bash
# DANGEROUS if parameters are wrong: use a nonproduction target first.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 --cacert "$ES_CA_CERT" -X POST \
 "$ES_URL/_snapshot/approved-repository/approved-snapshot/_restore?wait_for_completion=false" \
 -H 'Content-Type: application/json' --data-binary @approved-restore.json
```

4. Monitor recovery and cluster health, validate data by counts/sample keys and query tests.
5. For production cutover, coordinate with data/app owners; restore is not a substitute for write reconciliation.

## Stop / escalate

Stop for unknown source snapshot, incompatible snapshot/index versions, insufficient disk, name collision, unexpected alias/global-state restoration, or missing authority.

## Success criteria and evidence

Attach verified restore status, index recovery completion, data validation, measured recovery time, data-loss window and business approval.

## Rollback / recovery

Preserve source/old indices and aliases until test acceptance. Roll back application routing if safe; account for writes received during failed cutover. Never overwrite live indices to make room without explicit recovery authorization.

## Official references

- https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-snapshot-restore
- https://www.elastic.co/docs/troubleshoot/elasticsearch/restore-from-snapshot
