# Page 07 — Elasticsearch Index Lifecycle Management & Safe Maintenance Automation

**Document ID:** ES-DBRE-OPS-007  
**Owner:** Elasticsearch DBRE Team  
**Version:** 1.0 — Proposed  
**Status:** DRAFT — NOT CERTIFIED FOR PRODUCTION  
**Reference:** Elasticsearch 7.17.x (verify provider/version-specific settings)  
**Applies to:** Production, Staging, QA, and Development  
**Cadence:** Continuous ILM checks; weekly discovery/reporting; monthly owner and policy review; quarterly retention/security audit  
**Partners:** Application Engineering (APP), Data Engineering/Business Data Owners (DATA), Platform/SRE (PLT), Security/Compliance (SEC), Service/Change Management (SM)

> **Mandatory safety policy:** Identifying a possibly unused index is NOT authorizing deletion. No automatic deletion workflow for inferred unused indices may operate until clear ownership, retention, dependency, backup, independent approval and recovery controls are established and certified. No production DELETE example appears in this document.

## 1. Objective and operating principles

The DBRE team will govern index retention and growth without risking business data loss, search outage, ingestion disruption or regulatory violations.

Outcomes:
1. A complete index owner / business retention register.
2. Correct and monitored ILM lifecycle policies for eligible data classes.
3. Weekly reports identifying **candidates for review**, not records approved for destruction.
4. Documented, independent business authorization before one-off index deletion.
5. Automated **read-only** discovery, validation and ticket generation with evidence.
6. Explicit restrictions on data streams, write indices, aliases, system/hidden indices and critical business indices.
7. Verifiable snapshots and tested recovery prerequisites.
8. Audited, limited execution and post-change APP/DBRE validation for any eventual approved deletion.
9. Clear maintenance metrics, corrective actions and stakeholder reporting.

**Separation of lifecycle types:**
- **A — Approved policy-driven retention:** ILM may delete indices automatically **only** after the retention class, policy, index patterns, protections and change control are approved, tested and monitored. Updating an ILM delete phase is itself a potentially destructive change.
- **B — Inferred-unused cleanup:** weekly automation **discovers and classifies** candidates. Humans decide whether business data is disposable. An approved, separately controlled executor may later perform an exact-name deletion under a valid change ticket.
- **C — Routine non-destructive maintenance:** rollover settings, shard planning, mappings, index templates, capacity reviews, and ILM error investigations with their own risk-appropriate change controls.

## 2. Ownership and RACI

| Activity | Accountable | Responsible / consulted |
|---|---|---|
| Define business data retention, archival and legal holds | DATA | DATA, SEC, APP |
| Elasticsearch ILM technical design and implementation | DBRE | DBRE, APP, DATA |
| Index owner/alias/ingestion dependency registry | DATA | DATA, APP, DBRE |
| Application query and ingestion dependency validation | APP | APP, DATA, DBRE |
| Weekly candidate discovery and evidence | DBRE | DBRE |
| Business authorization for irreversible index deletion | DATA | DATA, APP, SEC |
| Formal production change authorization | SM | DBRE, APP, DATA, PLT |
| Implementation of an approved exact-index operation | DBRE | DBRE |
| Snapshot storage, backup infrastructure and recovery | DBRE (technical recovery) / PLT (repository infrastructure) | DBRE, PLT, SEC |
| Legal/compliance exception and privilege policy | SEC | SEC, DATA, DBRE |
| Impact/functional validation after change | APP | APP, DATA, DBRE |
| Audit and cost/space reporting | DBRE | DBRE, DATA, FinOps |

**Two independent approvals:** Business Data Owner authorizes data disposition; APP confirms it is not functionally required. SM authorizes the change when policy requires it. One individual should not request, approve and execute irreversible deletion alone.

## 3. Data classification, policy and ownership register

Every production index family must be classified, including its aliases, data streams, write path and dependent applications.

| Field | Required value |
|---|---|
| Cluster ID/environment/provider/version | Exact source and support status |
| Index UUID and current name | Stable identity; record name and UUID together |
| Index family/application/functional domain | Source/use case and business purpose |
| Business Data Owner and APP owner | Named primary and backup contacts |
| Source of truth and rebuild path | ES-primary or derived; replay/cutover guidance |
| Data classification | PHI/PII/security exposure, encryption/audit |
| Retention and legal holds | Approved minimum/maximum, jurisdiction and exceptions |
| Policy name and effective ILM phase | Approved template/ILM policy and review date |
| Alias/data stream membership | Read aliases, write alias, backing-index relationships |
| Ingestion/writes | Direct index writes, bulk jobs, pipelines, scheduled updates |
| Reads/search | Direct index, alias, multi-index wildcard, cross-cluster searches, reports |
| Snapshot and restore | Required restore-point ID, last successful test |
| Candidate status and last reviewed | Review state, ticket ID, owner/approval |
| Expiration/review date | Revalidate approval and evidence before execution |

If ownership or retention is **unknown**, classify as **UNOWNED / HOLD**, assign an owner-discovery ticket and exclude from deletion.

### Example index policy classes

| Class | Lifecycle | Auto deletion? |
|---|---|---|
| Time-based operational logs/metrics | ILM rollover and approved age retention | Only under signed class policy |
| Business search indices used by applications | Managed rollover/archival/reindex as needed | No inferred-unused deletion |
| Patient or regulated data | Retention/legal-hold based, individual owner sign-off | Never from heuristic alone |
| Rebuildable staging/QA test data | Approved short retention with safeguards | Only within environment policy |
| Security, Kibana or hidden/system indices | Platform/feature controlled | Excluded from general cleanup |
| Active data-stream write backing index | Data stream / ILM lifecycle | Never delete as an orphan candidate |
| CCR follower or cross-cluster dependency | Replication-aware lifecycle | Excluded until replication owner approval |
| Indices under migration/reindex/cutover | Temporary hold | No deletion until signed migration completion |

## 4. Lifecycle architecture — ILM versus a cleanup job

**ILM** executes configured lifecycle actions: rollover in hot, optional warm/cold transitions, and a delete phase if the policy includes one. ILM may run automatically and does not ask for an interactive approval each time an index reaches a delete phase. Therefore **the policy approval is the deletion authorization contract**, and its pattern/scope must be constrained.

An unused-index detector is **not** a replacement for approved business retention. It does not automatically know if data remains contractually or legally necessary.

### Lifecycle semantics requiring 7.17 validation

- Rollover may target an alias/write index or a data stream; matching template, write alias and sequential name must be correct for alias-based rollover.
- Typical shard sizing uses 10–50 GB as an initial guideline, not a hard limit.
- Conditions are triggered according to max/min rollover semantics; empty write indices usually do **not** roll over by age alone.
- When an index rolls over, later ILM phase min_age is generally measured from the rollover time, not creation time. ILM origination date settings may affect the calculation.
- ILM policy updates can leave previously cached phase definitions in execution; inspect ILM explain before assuming all indices changed behavior immediately.
- Do not use current/latest-version-only lifecycle features without verifying support in Elasticsearch 7.17 and provider restrictions.

### Example: safe rollover-only staging policy (NO delete phase)

**This example changes cluster metadata. Execute only in authorized non-production testing.** It is deliberately not a production-ready retention rule.

~~~~http
# CHANGE-CONTROLLED: create a rollover-only policy
PUT /_ilm/policy/staging-rollover-only
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_primary_shard_size": "40gb",
            "max_age": "30d"
          }
        }
      }
    }
  }
}
~~~~

In a separate, approved template/bootstrap step, the index must be configured with the correct lifecycle policy, rollover alias and initial write-index assignment, or a suitable data-stream template.

**Do not add a delete phase** until DATA and SEC approve the exact retention period and APP verifies reader/ingestion dependencies. Rollover size/age conditions still require test evidence and may not trigger on empty indices.

### Approved retention-policy specification template (not runnable code)

| Field | Example / mandatory control |
|---|---|
| Business data class | e.g., approved operational metrics, not patient records |
| In-scope index pattern | Explicit narrowly bounded prefix and environment |
| Retention start and calculation | Document min_age and rollover-time implications |
| Deletion schedule | Approved duration and expected policy action |
| Exclusions | Write index, legal holds, active migration, protected indices |
| Snapshot / archive | Verified coverage appropriate to RPO/retention |
| Business owner | Named written authorization |
| Security/legal review | Approved retention and regulatory requirements |
| APP review | No application requirement beyond the planned retention |
| Rollback/recovery | Isolated tested restore/replay and data-loss boundaries |
| Staging evidence | Date, policy version, exact test results |
| Monitoring | ILM errors, phase transitions, delete audit, unexpected scope |
| Policy owner/expiry | Reapproval required after material scope changes |

**ILM wait_for_snapshot caution:** The delete-phase wait-for-snapshot action waits for a specified SLM policy to run successfully *after the wait begins* with index coverage. It is not proof that a test restore passed or that the backup meets an independently approved business RPO.

## 5. Candidate discovery definition — not a deletion definition

The following are **signals**, not sufficient criteria:

| Heuristic | What it suggests | What it cannot prove |
|---|---|---|
| Zero live documents | May be empty | May be intentional schema/bootstrap, future ingestion target or temporarily empty |
| No index aliases | Not accessed through an index alias | May be referenced by exact index name, wildcard, data stream, scheduled job, CCS or direct writes |
| No observed write operations for X days | Apparently inactive ingestion | Future/monthly/quarterly events, blocked jobs, collection gaps or restarts |
| No observed search operations for X days | Apparently little search activity | Business/DR/compliance need, cross-cluster consumers, monitoring gaps, reset stats |
| Index older than retention threshold | Candidate for policy review | Approved retention may be longer or under legal hold |
| Small store footprint | Low apparent capacity benefit | Useful reference index or required mapping/bootstrap |
| Large docs.deleted ratio | Index maintenance consideration | Safe business deletion or need for automatic force merge |

**X must be approved** for each data class and app. A possible 90-day observation window is a **proposed example, not a universal setting**. Quarterly or annual workflows require longer observation and explicit APP/DATA owner confirmation.

### Why Elasticsearch search statistics do not establish unused status

Elasticsearch index search/indexing statistics are operational **counters**, not an authoritative historical access audit. They may reset on node restart, may be unavailable for deleted/relocated shards, and may not uniquely map a search to a business application or index if the request uses aliases, wildcards, cross-cluster search or application caching. Absence of observed requests is **unknown** if telemetry is missing or the collection window is incomplete.

For robust evidence, correlate:
- Long-term Prometheus index statistics and exporter scrape-coverage.
- Application/APM query logs or API instrumentation with index and alias targeting.
- Approved audit/access logs where available and appropriate.
- Ingestion pipeline and scheduled batch job inventories.
- Source-data owner attestations and business search feature inventory.
- Index settings, aliases, data streams, templates and lifecycle references.
- Compliance/retention and legal holds.

Do not collect patient identifiers or full sensitive queries solely to determine index utilization.

## 6. Read-only candidate inventory — Elasticsearch 7.17 examples

These are monitoring/inspection requests; confirm privileges and large-cluster performance before regular execution.

~~~~http
# Environment health
GET /_cluster/health

# Indices with document counts, shard configuration and storage
GET /_cat/indices?v&h=health,index,uuid,pri,rep,docs.count,docs.deleted,store.size,pri.store.size

# Aliases (read and write)
GET /_alias
GET /your-index-name/_alias

# Data streams and backing indices
GET /_data_stream

# ILM policy state and errors
GET /_ilm/status
GET /_ilm/policy
GET /_all/_ilm/explain?only_errors=true
GET /your-index-name/_ilm/explain

# Index metadata / templates for known candidates
GET /your-index-name/_settings
GET /your-index-name/_mapping
GET /_index_template

# Time-series search and indexing stats, NOT a lifetime access audit
GET /your-index-name/_stats/search,indexing

# Shards, allocation and storage
GET /_cat/shards?v&h=index,shard,prirep,state,store,node
~~~~

**Guardrail:** CAT indices output may omit hidden, closed and system indices by default; do not assume inventory completeness. Use properly authorized, explicit metadata calls for the restricted set of resources. Avoid blanket wildcard expansion when exporting or modifying indices.

### Per-index evidence rows

| Signal | Example field |
|---|---|
| Current identity | index_name + index_uuid + cluster |
| docs.count, docs.deleted | Snapshot of Lucene counts |
| primary_store_bytes | Numeric current size |
| alias membership / is_write_index | Explicit GET alias response |
| data_stream backing / current write index | Exact data stream metadata |
| ILM lifecycle/policy/phase | Explain response |
| first/last observed usage time | Instrumented telemetry with coverage flag |
| read/write observation window | Number of complete days and source |
| scheduled future jobs / migration dependencies | APP/DATA confirmation |
| retention/legal hold | Signed Data Owner + Security record |
| current status | Candidate, Investigation, Hold, Approved, Rejected |

## 7. Exclusion rules and immutable guardrails

The weekly detector MUST mark the following as **BLOCKED / NO CLEANUP** until a separately reviewed exception exists:

1. System, hidden and security-feature-managed indices, including those used by Kibana and Elastic Stack features.
2. Any current data stream backing **write** index.
3. Any current write index for an application alias, and any index with unresolved alias semantics.
4. Indices with unknown owner, unknown retention or unknown application dependency.
5. Indices involved in active migration, reindexing, replay, backfill, DR test, legal hold or incident.
6. Indices required by CCR, cross-cluster searches, external reporting, periodic jobs or archive restoration.
7. Any source-of-truth index with no verified independent recoverable copy.
8. Indices with missing/stale/incomplete usage telemetry or cluster health problems.
9. Indices whose approved snapshot and restore-test evidence is missing where recovery is required.
10. Indices not covered by an explicit, still-valid application and business owner approval.

**High-risk mutation safeguards:**
- No wildcard DELETE, no _all, no bulk unknown names, no unrestricted loop.
- Do not disable Elasticsearch destructive_requires_name or reduce security privileges to execute.
- Use stable cluster ID + index UUID and **recheck index identity** immediately before a separate exact-name action. An index name can be deleted and recreated between discovery and execution.
- Require snapshot evidence appropriate to the approved retention/recovery need; a mere successful snapshot is not necessarily a tested restore.
- Quarantine/disable actions are **not** implicitly safe: removing aliases or blocking writes may break applications and require approval.
- Never hide/fix deletion errors with force; reconcile failures, audit results and stop.

## 8. Weekly read-only automation design

**Schedule:** weekly on a designated business day after monitoring retention and app owners confirm collection windows; do not use a cron job that automatically deletes indices.

### Workflow

1. Load approved cluster and environment allowlist from configuration.
2. Fetch cluster health, index UUID/name and metadata through read-only credentials.
3. Gather aliases, data-stream membership/write-index role, ILM policies, ownership registry and legal-hold state.
4. Join usage evidence across the full approved X-day window, with metric coverage and restart/collector-gap indicators.
5. Evaluate only candidate heuristics. Each match gets a reason and supporting evidence; missing evidence = HOLD.
6. Apply non-overridable protected-resource and ownership exclusions.
7. Generate a **candidate report** grouped by application/data owner, not a deletion queue.
8. Create/refresh ticket for Data Owner and APP to investigate; keep DBRE evidence.
9. Log decisions and expiry dates; no destructive operations, alias changes or ILM mutations.
10. Send weekly report to DBRE and stakeholders; archive prior reports for traceability.

### Example classification pseudocode (not executable deletion code)

~~~~python
def classify_index(index, evidence):
    if index.is_system_or_hidden or index.is_feature_managed:
        return "BLOCKED", "protected resource"
    if index.is_data_stream_write_index or index.is_alias_write_index:
        return "BLOCKED", "active write target"
    if evidence.legal_hold or evidence.active_migration_or_replay:
        return "BLOCKED", "hold or dependent operation"
    if not evidence.owner_known or not evidence.retention_known:
        return "HOLD", "ownership or retention missing"
    if not evidence.telemetry_complete:
        return "HOLD", "insufficient read/write observability"
    if not evidence.app_dependency_inventory_complete:
        return "HOLD", "application dependency review missing"

    signals = []
    if index.live_document_count == 0:
        signals.append("zero_live_documents")
    if not evidence.has_direct_or_alias_read_during_window:
        signals.append("no_observed_reads")
    if not evidence.has_direct_or_alias_write_during_window:
        signals.append("no_observed_writes")
    if index.alias_count == 0:
        signals.append("no_alias")

    if signals:
        return "CANDIDATE_REVIEW", ", ".join(signals)
    return "ACTIVE_OR_UNKNOWN", "no supported candidate signal"

# Output: evidence + owner-review ticket ONLY. No delete API.
~~~~

This is an architectural illustration. A production implementation must integrate real metadata, aliases, data-stream checks and telemetry; it cannot assume guessed fields exist in Elasticsearch responses.

## 9. Candidate lifecycle and approval state machine

| State | Owner | Entry/exit criteria |
|---|---|---|
| DISCOVERED | DBRE automation | Observed heuristics with complete source metadata |
| HOLD / BLOCKED | DBRE | Missing evidence or protected resource; no automatic escalation to delete |
| UNDER_REVIEW | APP + DATA | Owner and dependency validation requested |
| REJECTED / KEEP | DATA | Required index, regulated retention or recovery dependency |
| APPROVED_FOR_RETIREMENT | DATA + APP | Explicit disposition and functional impact approval |
| CHANGE_APPROVED | SM / Incident authority | Scope, exact identity, window, rollback and controls authorized |
| PRE_EXECUTION_REVALIDATION | DBRE executor | Identity/UUID, write role, holds, approvals, snapshot rechecked |
| EXECUTED | DBRE executor | Exact authorized operation with immutable audit trail |
| VALIDATED / CLOSED | APP + DBRE + DATA | Application health, retention outcome and storage impact verified |

Approval expires after a configurable, documented short period (example 7 days) or whenever the index UUID, aliases, write role, retention, legal hold, dependencies or change scope changes. **Never silently renew approval.** Unknown classification results must default to HOLD.

## 10. Production deletion authorization checklist

### Mandatory business and operational evidence

- [ ] Business Data Owner confirms exact index UUID/name and retention disposition.
- [ ] Application Owner confirms direct/alias/wildcard searches, ingestion, scheduled and periodic use cases have been reviewed.
- [ ] SEC/legal confirms retention and legal-hold status where applicable.
- [ ] DBRE confirms no current write-index/data-stream/system/feature/CCR/migration dependency.
- [ ] Read/write telemetry coverage is sufficient or an explicit evidence exception is signed.
- [ ] Exact index and shard storage identified; projected savings validated.
- [ ] Required backup SUCCESS and an appropriate test restore/replay route confirmed.
- [ ] App functionality, query routing, data reconciliation and change rollback/failback plans documented.
- [ ] Change ticket includes requester, two independent authorizers, executor, incident contact and expiry.
- [ ] Execution limited to explicitly approved index identity/name and environment.
- [ ] Immediate pre-execution recheck finds no new writes/dependencies/holds or identity change.
- [ ] Post-change APP validation and recovery monitoring plan approved.

**Rejection examples:** zero-doc test index still needed for the next scheduled batch; no alias but used via direct index name; index is under active backfill; legal hold unknown; missing telemetry; original index name recycled with a new UUID.

### Implementation authorization

Do not include a general purpose delete command in an on-call guide. Store the narrowly scoped production retirement executor in a restricted, audited operational procedure or reviewed code repository. The executor must verify approved exact names/UUIDs and provide a safe abort path before any mutation. Approval to delete one index does not authorize its aliases, siblings, wildcard expansions or source data.

## 11. Data-stream and alias special cases

- Elasticsearch does not allow deleting the **current write backing index of a data stream**; rollover makes the previous write index non-current, but older backing indices may still be needed for search or retention.
- Do not treat backing indices as independent orphan candidates merely because they lack ordinary aliases.
- Index aliases may represent read patterns, filters, routing or write targets. Alias removal can break search contracts and must be analyzed with APP.
- Multiple indices under one alias can be expected in long-lived enterprise search: one EMPI or business identifier may exist in several generations; no read traffic to a single index is not proof that it is unnecessary.
- For time-based append-mostly logs or metrics, approved data streams and ILM can simplify retention.
- For frequently updated patient/entity records, index aliases/explicit index routing, source updates and query semantics may require a custom lifecycle plan, not automatic time-series deletion.

## 12. Operational index maintenance — no automatic force merge

| Action | When to consider | Required safeguards |
|---|---|---|
| Rollover | Active index approaches approved shard target | Template/alias and APP validation |
| Index template updates | Need consistent mappings/settings for new indices | Version control and staging compatibility test |
| Reindex | Shard/layout/mapping changes required | Storage, ingest, alias cutover and full data validation |
| Force merge | Approved read-only/rolled-over workload with IO budget | Disk headroom, merge impact, recovery window; not routine for active writes |
| ILM error recovery | Policy/template/assignment stuck | Explain root cause; change ticket before mutation |
| Replica/refresh changes | Performance/capacity remediation | Availability/freshness analysis and rollback |
| Retention delete phase | Explicit class-approved data disposal | Strict pattern, legal review, snapshot/recovery gate |
| Unused-index retirement | Owner/APP-reviewed one-off candidate | Independent approval and audited executor |

**Force merge note:** Deleted Lucene docs can remain until segment merges; high docs.deleted alone does not justify automatically running force merge. In ES 7.17 force-merge work can be expensive and is not generally cancellable after starting. Schedule only after understanding IO, disk and live workload risks.

## 13. ILM troubleshooting and monitoring

Read-only checks:

~~~~http
GET /_ilm/status
GET /_ilm/policy
GET /_all/_ilm/explain?only_errors=true
GET /your-index-name/_ilm/explain
GET /your-index-name/_settings
GET /_alias
GET /_data_stream
GET /_cat/indices?v
~~~~

**Common blockers:** rollover alias not set, expected write index mismatch, missing matching index template, unavailable eligible shard allocation, source/replay dependencies, insufficient capacity, invalid lifecycle configuration, ILM policy execution permissions or cached phase definition behavior.

Do not blindly retry ILM or move an index to a later phase. Resolve configuration and validate state/action transitions in staging first. Alert when delete-phase behavior is inconsistent with signed retention scope.

### Required Grafana/Prometheus/reporting signals

| Signal | Purpose |
|---|---|
| Indices by approved retention class | Owner coverage and unclassified backlog |
| ILM ERROR count and oldest error | Catch blocked rollover/retention |
| Hot-index shard size and growth | Prevent oversize shards |
| Index family primary and total disk bytes | Growth and savings measurement |
| Candidate count by reason / owner | Weekly workload planning |
| HOLD/BLOCKED candidates and reason | Surface unsafe/incomplete evidence |
| Unreviewed/expired approval tickets | Governance compliance |
| Deleted-index audit history | Authorization and change verification |
| Snapshot/restore evidence per candidate | Recovery guarantee |
| Saved GB versus forecast GB | Actual benefit without double counting |
| Telemetry coverage/missing days | Avoid false-unused labels |
| App SLO and indexing freshness after changes | Validate no regression |

Avoid adding index UUID and patient IDs indiscriminately as long-lived high-cardinality metric labels; use a controlled inventory/reporting store for detailed row-level candidate evidence.

## 14. Weekly maintenance reporting template

| Field | Example / purpose |
|---|---|
| Report UTC period | Week start/end and collection coverage |
| Cluster/environment | Name and exact ES version |
| Index inventory | Total, per owner/class, active write targets |
| Potentially unused candidates | Candidate count, reason, evidence |
| HOLD/BLOCKED | Missing owners, legal holds, incomplete telemetry |
| ILM errors | Current action/step, duration, assigned ticket |
| Shard/growth | Top growing indices, risk from data tiers |
| Snapshot readiness | Latest required SUCCESS and restore test |
| Change requests | Pending approvals and expiry |
| Retirements | Approved exact index identities and audit records |
| Capacity impact | Primary/physical GB safely reclaimed, forecast delta |
| Application validation | Search, indexing and freshness before/after |
| Next action | Owner, deadline, ticket |

### Sample stakeholder summary

This week's automation identified **candidate indices for review only**. No indices were deleted automatically. Each candidate requires confirmation of business retention, application dependencies and recovery safeguards. Any approved retirement will proceed through the change-management process with an exact-index execution record.

## 15. Failure scenarios and safety tests

| Test | Scenario | Required result |
|---|---|---|
| T01 | Zero-doc index still used by future scheduled job | Candidate may be flagged, but APP review blocks deletion |
| T02 | No alias but direct-index application reference | HOLD/REJECT |
| T03 | Incomplete Prometheus metrics / ES node restart | HOLD, never infer no usage |
| T04 | Current data-stream write backing index | BLOCKED |
| T05 | ILM policy would delete protected class unexpectedly | Configuration rejected |
| T06 | Legal hold introduced after initial approval | Approval invalidated; abort |
| T07 | Index recreated under same name with new UUID | Abort stale approval |
| T08 | APP requests read-only preservation for historical search | REJECT delete |
| T09 | Snapshot available but no appropriate restore evidence | HOLD |
| T10 | Unexpected index family rollover and alias change | Re-evaluate exact membership |
| T11 | Delete executor receives wildcard or _all | Hard fail, log attempt |
| T12 | Owner approval expired or missing second approval | Abort |
| T13 | Index under migration/reindex/DR replay | BLOCKED |
| T14 | Approved retirement passes in isolated staging | Audited, exact-scope action; APP recovery validation |
| T15 | Report shows reclaimed index store but node disk unchanged | Investigate merge/filesystem/replica accounting |

Tests must use synthetic/sanitized data and dedicated staging resources. Do not perform destructive validation in production.

## 16. Implementation roadmap

| Phase | Work | Owner | Acceptance |
|---|---|---|---|
| M7-A | Create authoritative index ownership and retention register | DATA + DBRE | 100% production coverage or explicitly assigned unknown-owner tickets |
| M7-B | Audit existing aliases, data streams, ILM and templates | DBRE + APP | Dependency list and protected-resource exclusions |
| M7-C | Implement read-only candidate inventory/report job | DBRE | Automated weekly report, no write privilege |
| M7-D | Validate X-day read/write telemetry and gaps | DBRE + APP | Reliable coverage or HOLD behavior |
| M7-E | Define approvals and deletion/retention policy templates | DATA + SEC + SM | Signed governance standard |
| M7-F | Test approved ILM rollover and retention in staging | DBRE | Correct scope, timing and recovery evidence |
| M7-G | Test restricted exact-index retirement workflow in staging | DBRE + APP | All safety/abort tests pass |
| M7-H | Pilot stakeholder review weekly | DATA + APP + DBRE | Correctly classified candidate decisions |
| M7-I | Publish cost/capacity and governance reports | DBRE + FinOps | Savings calculations reconciled |
| M7-J | Formally certify operational procedure | All approvers | Sign-off and change/rollback records |

**Do not enable automated destructive operations as a prerequisite for completing the discovery/reporting phases.** The team can realize governance, reporting and maintenance benefits without activating deletion automation.

## 17. Production safeguards and acceptance

- [ ] Production index ownership, app dependency, sensitivity and retention classifications are documented.
- [ ] ILM policies, templates, data streams, aliases and write targets inventoried.
- [ ] Approved retention classes explicitly separate eligible ILM deletion from heuristic cleanup.
- [ ] Weekly discovery operates read-only and emits candidate tickets/reports, not delete calls.
- [ ] Zero-doc, no-alias, no-read/no-write heuristics treated only as candidate signals.
- [ ] Telemetry retention and coverage sufficient for the approved X-day observation windows.
- [ ] Exclusions enforce legal holds, system/hidden indices, live write targets, migrations and unknown owners.
- [ ] Independent DATA and APP approval plus SM/change authorization required for one-off deletion.
- [ ] Snapshot success/restore route and exact-index recovery plan verified where needed.
- [ ] Final pre-execution UUID, name, alias, write role and legal-hold recheck mandatory.
- [ ] No wildcard delete, _all, bypass of destructive safeguards or single-actor approval.
- [ ] ILM retention/delete policy staging test and scope/cached-phase review completed.
- [ ] All 15 safety scenarios tested in staging; adverse cases fail closed.
- [ ] Audit trail, app functional validation and measured storage impact retained.
- [ ] Quarterly owner/retention/governance review and runbook update assigned.
- [ ] DBRE, APP, DATA, SEC and SM formally approve operational adoption.

**Completion:** Milestone 7 is complete only after the read-only pipeline, owner classification, policy/approval workflow, negative safety tests and representative staging exercises pass and stakeholders sign off. Documentation publication is not production certification.

## 18. References

**Version-specific 7.17 guidance to validate on target deployment:**
- [Elasticsearch 7.17 index lifecycle management](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/index-lifecycle-management.html)
- [Elasticsearch 7.17 rollover action](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/ilm-rollover.html)
- [Elasticsearch 7.17 explain lifecycle](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/ilm-explain-lifecycle.html)
- [Elasticsearch 7.17 delete index](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/indices-delete-index.html)

**General/updated documentation (confirm release applicability):**
- [ILM phases and actions](https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management/index-lifecycle)
- [Rollover and write-index requirements](https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management/rollover)
- [Get aliases API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-get-alias-2)
- [Get data streams API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-get-data-stream)
- [Delete index protection and effects](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-delete)
- [ILM troubleshooting](https://www.elastic.co/docs/troubleshoot/elasticsearch/index-lifecycle-management-errors)
- [Snapshot and restore](https://www.elastic.co/docs/deploy-manage/tools/snapshot-and-restore)

---

**Document status:** Draft only. No production Elasticsearch commands, ILM changes, delete operations, cron deployment or live validation were performed during publication.
