# 11 — Rolling upgrades and patching

> **Draft for peer review · Technical owner:** DBRE/SRE  
> **Stakeholders / approval:** Application/Data: client, pipelines and tests; Security and Change Authority: required approvals  
> **Version scope:** Elasticsearch REST APIs; 7.17 compatibility baseline and revalidate on deployed version  
> **Change class:** Follow organizational incident/change policy; explicit approval before mutations.

## When to use

Use for supported patch/minor upgrades and planned major-version migration. Do not assume every upgrade supports rolling mode.

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
  -X GET "$ES_URL/"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cat/nodes?v&h=name,version,roles,master"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_cluster/health?pretty"
```
```bash
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  -X GET "$ES_URL/_snapshot?pretty"
```

Review official source→target version-specific upgrade matrix, plugins, security/clients, templates, deprecated settings, index compatibility and available snapshots.

## Approved procedure

1. Verify supported path and upgrade order against **the exact** deployed and target version documentation; major-version upgrades often require a different sequence or staged intermediate upgrades.
2. Test a representative staging upgrade; obtain Data, Application and platform signoff.
3. Establish pre-change snapshot/restore evidence, capacity, expected failure coverage and stop conditions.
4. Use vendor/provider-approved per-node or deployment upgrade workflow, monitoring shard recovery and client traffic between steps.
5. Validate application search, ingestion, alerts, authentication, backups, ILM and cost after the rollout.

## Version and supportability go/no-go checklist
An upgrade procedure is **deployment-specific**: self-managed nodes, Elastic Cloud, ECE/ECK and managed third-party platforms have different orchestration and rollback limits. Record current/target version and build, supported hop-by-hop path, plugin and client compatibility, OS/JDK support, tier/node upgrade order, deprecations, security settings and peer-reviewed release notes. Elasticsearch 7.17 is out of support as of January 2026; an upgrade plan should address this risk.

**Read-only cluster inventory before requesting change.**

```bash
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_nodes?filter_path=nodes.*.name,nodes.*.version,nodes.*.roles,nodes.*.plugins.name&pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cluster/health?pretty"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_cat/recovery?v&active_only=true"
curl --fail-with-body -sS --basic -u "$ES_USER" "$ES_URL/_snapshot?pretty"
```

**Gates.** (1) Supported upgrade path and provider sequencing documented; (2) staging dress rehearsal completed with same plugins, ingest and representative search traffic; (3) recoverable, tested snapshot; (4) failure-domain and replica headroom, plus expected surge resources; (5) explicit client/SDK and application compatibility review; (6) write/ingest behavior under mixed versions; (7) post-upgrade tests and named approvers. Do not assume in-place downgrade is supported.
**During upgrade.** Perform only the vendor-approved node order. Between stages, verify cluster master stability, shard recoveries, node versions, heap, CPU, ingestion lag, query error rates and authentication, and compare against the approved SLO envelope. Pause automatically for red health, loss of healthy shard copies, unexpected client incompatibility, or sustained rejects.
**Evidence.** Change ticket contains versions by node before/after, staging findings, complete backup proof, client and schema compatibility results, API output, monitoring charts, last good state, data validation and escalation/rollback plan. Recovery usually means deploying a compatible replacement and restoring supported snapshots, not rolling binaries backward.

## Stop / escalate

Stop on compatibility failure, missing/unsafe shard copies, sustained service impact, failed snapshot evidence or unsupported rollback path.

## Success criteria and evidence

Attach version inventory, approved upgrade path, stage test results, health and client test results, incident/change references.

## Rollback / recovery

Downgrades may be unsupported. Plan rollback using validated snapshots and a supported replacement deployment, not an in-place binary downgrade.

## Official references

- https://www.elastic.co/docs/deploy-manage/upgrade
- https://www.elastic.co/support/eol
