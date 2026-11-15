# 06 — Data retention and ILM implementation

> **Draft for peer review · Technical owner:** DBRE/SRE (implementation)  
> **Stakeholders / approval:** Data Engineering + Business Owner: jointly define/approve retention; Index Owner: index applicability; Legal/Compliance as needed  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use when establishing or changing Elasticsearch retention, rollover and lifecycle policy.

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
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_ilm/policy?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_ilm/status?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" -X GET "$ES_URL/_cat/indices?v&h=index,creation.date.string,docs.count,store.size"
```

For a specific target index, check `GET /<index>/_ilm/explain` and current policy/template assignment. Confirm indices may include historical updates, legal holds or non-time-based access requirements.

## Approved procedure

1. Data Engineering and Business Owner jointly document approved retention periods, business purpose, legal/hold exceptions and change effective date.
2. DBRE assesses lifecycle compatibility, capacity, recovery and delete timing, including ingestion/update behavior.
3. Implement approved ILM policy and target/template association using version-specific API and reviewed JSON:

```bash
# Controlled change, not a sample retention policy.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
 --cacert "$ES_CA_CERT" -X PUT "$ES_URL/_ilm/policy/approved-policy-name" \
 -H 'Content-Type: application/json' --data-binary @approved-ilm-policy.json
```

4. Check `GET /approved-index-000001/_ilm/explain`; verify which indices and creation/origination dates make deletion eligible.
5. Execute staging pilot, then monitor lifecycle steps, errors and unexpected candidate changes. A policy update may affect already-managed indices depending on phase behavior.

## Stop / escalate

Stop if hold exclusions, update-to-old-index requirements, restore windows or approved business retention cannot be demonstrated. Never use a cost-saving objective to override retention approval.

## Success criteria and evidence

Record policy version, affected indices, effective date, Data + Business signoff, per-index ILM explain, retained-volume forecast and monitoring owner.

## Rollback / recovery

Restore the approved prior policy version for future actions; this does not undo indices already deleted. For deleted data, use snapshot recovery only if covered by a valid snapshot and approved process.

## Official references

- https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management
- https://www.elastic.co/docs/troubleshoot/elasticsearch/index-lifecycle-management-errors
