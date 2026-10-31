# Page 06 — Elasticsearch Backup, Disaster Recovery & Restore Testing

**Document ID:** ES-DBRE-OPS-006  
**Owner:** Elasticsearch DBRE  
**Version:** 1.0 — Proposed  
**Status:** DRAFT — NOT CERTIFIED FOR PRODUCTION  
**Reference:** Elasticsearch 7.17.x (confirm provider-specific features)  
**Partners:** Platform/Cloud SRE, Application Engineering, Data Engineering/Data Owners, Security, Incident and Change Management  
**Cadence:** Daily monitoring; weekly exception review; monthly restore evidence; quarterly DR simulation

> **Safety:** PUT/POST examples below are for **authorized isolated staging or change-controlled execution only**. No live infrastructure changes are authorized by this document. No destructive whole-cluster delete/overwrite commands are provided.

## 1. Purpose and requirements

The DBRE team must maintain tested, auditable recovery procedures for:
- Off-cluster Elasticsearch snapshots and SLM scheduling.
- Repository configuration, access and availability.
- Individual index/data-stream recovery and disaster-level cluster recovery.
- Business-defined Recovery Point Objective (RPO), Recovery Time Objective (RTO), and data correctness.
- Security-sensitive cluster and feature-state backups.
- Provider and version compatibility across AWS and Azure.
- Regular fault/restore exercises, evidence and remediation actions.

**RPO** is the maximum permitted age of the recoverable business data at a failure. **RTO** is the maximum permitted time from a defined incident start to business service recovery. Both require agreement by application/data/service owners.

### Sample business recovery tiers (illustrations, not adopted SLOs)

| Tier | Candidate RPO | Candidate RTO | Required planning |
|---|---|---|---|
| 1 Critical search | 15 minutes | 2 hours | Frequent verified backups or alternative replay/replication; full-load DR test |
| 2 Important service | 1 hour | 4 hours | Tested restores, index/alias recovery, app validation |
| 3 Rebuildable search | 24 hours | 24 hours | Source replay/reindex with recovery capacity |

A 15-minute snapshot schedule **does not guarantee** a 15-minute RPO. Snapshot completion delay, a failed run, per-shard capture interval and replication/replay availability all matter.

## 2. Ownership and approvals

| Activity | Accountable | Responsible / consulted |
|---|---|---|
| SLM policy and snapshot completion monitoring | DBRE | DBRE, PLT |
| Repository storage, network, role/IAM | PLT | PLT, DBRE, SEC |
| Retention and protected-data coverage | DATA | DATA, SEC, DBRE |
| Technical restore operation | DBRE | DBRE, PLT |
| Application correctness, search and SLO verification | APP | APP, DATA, DBRE |
| Service RPO/RTO and recovery priority | Application Service Owner | APP, DATA, DBRE |
| Security policy, audit, credentials | SEC | SEC, PLT |
| Major incident command and communications | Incident Management | All response teams |
| Formal production change authorization | Change Management | DBRE, PLT, APP, DATA |
| DR exercise evidence and runbook versioning | DBRE | DBRE, APP, PLT |

Every cluster/repository has a named primary and backup operational owner, service recovery owner, security classification and escalation contact.

## 3. Inventory and backup coverage register

| Field | Mandatory detail |
|---|---|
| Cluster/environment/provider/ES version | Exact source and target build |
| Repository | Name, type, region, account, base path, writer and reader owners |
| Scope | Index patterns, data streams, backing indices, exclusions and aliases |
| Business owner | Data classification, retention and legal requirements |
| Snapshot/SLM | Policy, UTC schedule, expected completion, minimum generations |
| RPO/RTO | Approved by service owner |
| Recovery | Tested index restore, cluster restore plan, data replay strategy |
| Security | Credentials/role ownership, encryption, least privilege and audit |
| Compatibility | Snapshot version, index creation version, Elastic Stack features |
| Evidence | Latest successful snapshot, latest restore drill, ticket/runbook link |

Snapshot contents commonly cover **open indices, data streams, their aliases and selected cluster metadata**. With included global state, supported feature states can include security, Kibana and other system data. Assess and protect them appropriately.

**Not backed up in Elasticsearch snapshots:** node configuration files, Elasticsearch keystore, TLS private keys, realm configuration files, registered repository definitions and transient settings. Protect these separately with secure configuration management and document how to reconstruct the nodes.

**Important:** A cluster snapshot does not represent an atomic, exact same-time image of every shard. For critical consistency requirements, preserve upstream data change watermarks and replay/reconciliation evidence.

## 4. Repository security, availability and integrity

1. Keep backups outside the Elasticsearch node failure domain; evaluate secondary region/account protection.
2. **Only one Elasticsearch cluster may write to a shared repository.** Register it read-only on secondary/DR clusters to protect metadata.
3. Encrypt storage and network transport; use audited least-privilege cloud IAM/managed identity and separate protected credentials.
4. Do not manually alter, partially copy or delete repository objects. Generic object-storage lifecycle expiry may corrupt snapshot structure if it removes Elasticsearch-managed files.
5. Manage regular retention with supported SLM/Elasticsearch operations; document legal holds and needed historic recovery points.
6. Treat backups that contain feature-state/security data as sensitive; control who can read and modify them.
7. Capacity-plan repository storage, API requests, network transport, restore throughput and disaster region unavailability.
8. When moving repository contents across storage locations, require a consistent, complete, supported transfer with no concurrent writes and verify the new repository before trusting it.
9. Repository access by different ES versions requires explicit compatibility checks; a newer version can change repository metadata that an older version cannot read safely.
10. Repository verification and even a successful snapshot do **not** replace full restore validation.

### AWS and Azure ownership

AWS S3 repository access uses compatible Elasticsearch repository support plus separately approved bucket and IAM permissions. Azure repository access uses corresponding Azure storage container, client credentials/managed identity support, and Elasticsearch repository module/plugin configuration. **Elasticsearch Basic Authentication does not grant object-store repository permissions.** Managed services may restrict snapshot repository APIs and types.

## 5. Read-only health and inventory commands (Kibana Dev Tools)

~~~~http
# Current SLM policy/status and historical statistics
GET /_slm/status
GET /_slm/policy
GET /_slm/stats

# Repositories and named snapshot metadata
GET /_snapshot/_all
GET /_snapshot/your-repository/_all
GET /_snapshot/your-repository/_current
GET /_snapshot/your-repository/your-snapshot-name
GET /_snapshot/_status

# Platform readiness and recovery
GET /_cluster/health
GET /_cat/shards?v&h=index,shard,prirep,state,node
GET /_cat/recovery?v&active_only=true
~~~~

Read-only APIs still require privileges and can add load. Restrict output and access appropriately. Snapshot policy invocation success may indicate only that **snapshot creation started**. Inspect the named snapshot state and shard outcomes; count only **SUCCESS** snapshots that contain the intended coverage as valid recovery points.

## 6. Reference repository registration (change-controlled examples)

### S3 staging repository (self-managed)

~~~~http
# Do not run without approved IAM, plugin/module compatibility and change control
PUT /_snapshot/staging_s3_backup
{
  "type": "s3",
  "settings": {
    "bucket": "example-es-backup-bucket",
    "base_path": "staging/cluster-a"
  }
}
~~~~

### Azure staging repository (self-managed)

~~~~http
# Secure Azure client credentials are configured separately
PUT /_snapshot/staging_azure_backup
{
  "type": "azure",
  "settings": {
    "container": "example-es-backup",
    "base_path": "staging/cluster-a"
  }
}
~~~~

These examples are deliberately not a complete security/IAM setup. Confirm the exact 7.17 plugin/module, repository settings, cloud connectivity, credentials and managed-provider restrictions before use.

### Read-only DR registration

When source and DR clusters access the **same repository**, DR must register the location and repository type with the read-only setting enabled:

~~~~json
{
  "settings": {
    "readonly": true
  }
}
~~~~

The above is a settings fragment, not a complete repository request. Do not apply it without the source repository type and storage configuration.

### Repository verification — elevated operational action

~~~~http
POST /_snapshot/your-repository/_verify
~~~~

This requires change authorization and tests repository connectivity, **not** full backup restorable data or application recovery.

## 7. Snapshot Lifecycle Management policy

Create policies that meet the recovery tier with enough margin for backup duration and failures, and govern retention based on business/legal requirements. SLM retention runs separately and applies to snapshots created by that SLM policy.

### Example: daily authorized staging policy (Elasticsearch 7.17)

~~~~http
# CONFIGURATION CHANGE — DO NOT RUN IN PRODUCTION WITHOUT APPROVAL
PUT /_slm/policy/staging-daily-es-backup
{
  "schedule": "0 30 1 * * ?",
  "name": "<staging-es-backup-{now/d}>",
  "repository": "staging_s3_backup",
  "config": {
    "indices": "*",
    "include_global_state": true,
    "ignore_unavailable": false,
    "partial": false
  },
  "retention": {
    "expire_after": "30d",
    "min_count": 5,
    "max_count": 50
  }
}
~~~~

The schedule is **01:30 UTC daily**. It does **not** meet a 15-minute RPO. Global-state inclusion requires feature-state data classification and security review.

### Policy checks and controlled manual test

~~~~http
# READ ONLY
GET /_slm/policy/staging-daily-es-backup
GET /_slm/stats

# CHANGE-CONTROLLED: starts a new snapshot in staging
POST /_slm/policy/staging-daily-es-backup/_execute
~~~~

After execution, obtain the created snapshot name and monitor until it completes, then inspect state, shard coverage, metadata and recovery age. SLM retention limits apply **per policy**; manually created snapshots or another policy's snapshots are not necessarily pruned by this policy.

## 8. Snapshot validation and RPO monitoring

Daily DBRE evidence:
- Latest completed snapshot ID, start and end timestamps in UTC.
- Snapshot state SUCCESS versus FAILED, PARTIAL or IN_PROGRESS.
- Total/failed/successful shard count and required index/data-stream coverage.
- Latest safe restore point and calculated age versus RPO.
- Repository permission, retention and storage-health exceptions.
- Last validated restore date, application owner and RTO result.

**Do not:** infer protection from SLM scheduling alone, count partial snapshots as complete, or set a 15-minute RPO merely because snapshot frequency is 15 minutes.

### RPO calculation

- Incident timestamp = agreed failure boundary T_fail.
- Recoverable data timestamp = demonstrated latest restored/fully replayable business-data watermark T_recoverable.
- **Observed data-loss window = T_fail − T_recoverable**, using measured evidence and conservative treatment of snapshot start/end timing.

For indices derived from PostgreSQL, MongoDB or Snowflake, an upstream change log, replay mechanism or source-of-truth reconciliation may be needed to prove the exact recoverable watermark.

## 9. Restore strategy by incident scenario

| Incident | Candidate recovery | Key risk |
|---|---|---|
| Accidental deletion of one index | Restore a **renamed** index, validate, authorize cutover | Lost writes since snapshot; alias collision |
| Incorrect update/corrupt records | Renamed restore for comparison and reconciliation | Do not overwrite good current documents |
| Data-node outage | Prefer healthy replica recovery before snapshot restore | Node and zone headroom |
| Whole cluster failure | Provision compatible cluster; recover config/data and APP dependencies | Version, feature state, credentials, routing |
| Regional outage | Tested secondary-region cluster/repository or rebuild/replay | Secondary storage availability and WAN throughput |
| Derived search index | Reindex/replay from source of truth when RTO allows | Source completeness and mapping contract |
| Cloud migration | Compatible/tested restore or supported remote reindex | Provider limitations, IAM, index creation version |

System feature-state restore is a **separate restricted playbook** because restoring security state can overwrite authentication data and lock out operators. Entire-cluster recovery may require deleting or closing existing indices, special handling for ILM/feature tasks and a clearly scoped emergency procedure.

## 10. Staging index restore — isolated rename example

**Preconditions:** approved staging change, correctly registered/read-only target repository, named SUCCESS snapshot, version and index creation compatibility, adequate disk, index mapping/alias review, and a data owner-approved non-PHI validation dataset.

~~~~http
# READ ONLY: confirm the selected snapshot
GET /_snapshot/your-repository/your-snapshot-name

# CHANGE CONTROL: restore an index using a DIFFERENT name
POST /_snapshot/your-repository/your-snapshot-name/_restore
{
  "indices": "example-index",
  "ignore_unavailable": false,
  "include_global_state": false,
  "include_aliases": false,
  "rename_pattern": "(.+)",
  "rename_replacement": "restore-test-$1"
}

# READ ONLY: monitor recovery and verify index stats
GET /_cluster/health/restore-test-example-index?wait_for_status=yellow&timeout=30s
GET /_cat/recovery/restore-test-example-index?v
GET /restore-test-example-index/_stats/docs,store,search
GET /restore-test-example-index/_count
~~~~

**Warning:** This is not read-only: even a renamed restore creates index metadata, uses storage and may impact cluster load. It must **not** be executed directly in production. Ensure no current name/alias conflict, inspect restore completion and validate all required primaries, mappings, analyzer compatibility, and application queries.

Restore to an existing **open** index is not supported. An existing **closed** index has primary shard count constraints. Data stream recovery additionally requires a compatible data-stream-enabled index template. This guide deliberately does not include full-cluster destructive overwrite commands.

### Restore acceptance

- Snapshot version, each index creation version and feature compatibility verified.
- Named restored index/data stream and intended aliases confirmed.
- No failed primary shards; allocation and disk remain safe.
- Counts and approved content samples reconcile to source backup, not necessarily current production.
- Data Owner confirms acceptable RPO and upstream replay/freshness if needed.
- APP verifies authentication, endpoint routing, queries, aggregations and p95/p99.
- DBRE documents restoration duration and residual performance/recovery risk.

## 11. RTO measurement and end-to-end recovery

Capture UTC timestamps for:
1. Incident start/detection.
2. Incident commander authorizes recovery.
3. New cluster environment available.
4. Repository access and snapshot selection succeed.
5. Restore starts.
6. Restore and shard recovery complete.
7. Required replay/reconciliation completes.
8. Application endpoint, auth, DNS, search/write paths pass tests.
9. Business owner accepts service restoration.

**Observed RTO = time of business service acceptance − agreed incident-start time.** Avoid counting only Elasticsearch snapshot restore time; provisioning, network, secrets, DNS and application validations may dominate.

### Worked illustrative example

For an application with approved example RPO **1 hour** and RTO **4 hours**:
- Incident begins 12:00 UTC; latest verified recoverable business watermark is 11:30 UTC → observed data-loss window **30 minutes**.
- Service and business workflow accepted at 14:45 UTC → observed RTO **2 hours 45 minutes**.
- RPO/RTO **pass only if** required data completeness, search functions and access controls are validated.

## 12. Disaster recovery exercise matrix

| ID | Test | Evidence required |
|---|---|---|
| DR01 | Scheduled backup misses/fails | Alert, owner, recovery action |
| DR02 | Repository access denied or network outage | IAM/network root cause and fallback |
| DR03 | Non-production index accidentally deleted | Renamed restore and reconciliation |
| DR04 | One data node lost | Replica recovery, shard assignment, SLO |
| DR05 | Entire staging cluster unavailable | Rebuild, snapshot restore, functional approval |
| DR06 | Credential/secret/certificate recovery | Approved break-glass and secure config recreation |
| DR07 | Snapshot or index version incompatible | Compatibility gate blocks unsafe restore |
| DR08 | Zone/region outage simulation | Secondary-region backup access and end-to-end RTO |
| DR09 | Upstream ingestion replay | Completeness, deduplication, freshness |
| DR10 | Large-index recovery under load | Recovery throughput/headroom and application performance |
| DR11 | System/feature-state restoration (restricted) | Security and Kibana compatibility, avoid lockout |
| DR12 | DR failback / rollback | Data reconciliation and client endpoint switch |

Suggested operational cadence (requires stakeholder approval): weekly snapshot exception review, monthly isolated restore, quarterly DR tabletop and periodic full end-to-end recovery exercise. Do not destructively test in production without separate approval.

## 13. Cross-cloud AWS source to Azure target considerations

**Example migration requiring explicit validation:** AWS-managed Elasticsearch Service 7.10.2 → Azure self-managed Elasticsearch 7.17.x. This is **not automatically certified** by basic HTTP authentication or numeric version comparison.

1. Confirm whether AWS source is Amazon Elasticsearch Service, Amazon OpenSearch Service, or another provider; determine underlying snapshot format/API and supported repository types.
2. Identify a customer-accessible S3 repository and whether snapshots are owned and accessible versus managed-only snapshots.
3. Validate source IAM role/trust and bucket permissions separately from Elasticsearch HTTP Basic Authentication, with no secrets in tickets.
4. Check snapshot **and each index creation version** compatibility, feature states, index mappings and plugins on 7.17.x.
5. Verify Azure target repository module/plugin and storage client configuration. S3 and Azure Blob repositories must not be treated as interchangeable simply because files are copied.
6. Avoid copying an actively changing S3 snapshot repository by object-level scripts as an assumed safe migration. Use a vendor-supported, consistent transfer strategy or an alternative supported index migration/reindex plan.
7. Test a small named index in an isolated environment before attempting wider migration; compare documents, mappings, aliases, analyzers, security and application results.
8. Measure transfer, restoration, replay and endpoint switch against agreed RPO/RTO; gain APP/DATA sign-off.

If the approach requires unsupported repository manipulation, stop and select a tested supported method. Confirm the source ability to reindex remotely, availability of source documents, networking and authentication.

## 14. Backup/DR monitoring and alerting

| Metric/event | Proposed action |
|---|---|
| Latest completed required snapshot age approaches approved RPO | Warn before RPO breach |
| No complete recoverable snapshot within approved RPO | Critical alert and incident escalation |
| FAILED or PARTIAL snapshot for required index family | Investigate shard errors and scope |
| SLM execution failures or delayed completion | Verify policy, repository and node health |
| Repository inaccessible or multiple writers detected | Incident; stop conflicting write operations with approval |
| Repository storage growth or retention failure | Capacity/FinOps review |
| Overdue restore exercise | Raise compliance/reliability task |
| Measured RTO or RPO fails in exercise | Prioritized preventive action and escalation |

Use Elasticsearch snapshot status plus cloud telemetry and the exercise register, not only exporter metrics. Alert payloads should include cluster, repository, policy/snapshot ID, UTC times, data owner, recovery deadline, and runbook; never put PHI/EMPI or secrets in labels.

## 15. Troubleshooting guide

| Symptom | Read-only diagnostics | Owner |
|---|---|---|
| Snapshot missing | SLM policy, run stats, repository snapshot list | DBRE |
| Running snapshot too long | Current snapshot status and cluster load | DBRE / PLT |
| Snapshot PARTIAL/FAILED | Failed shard reasons and ES logs | DBRE / PLT |
| Repository access denied | Cloud IAM role, storage connectivity | PLT / SEC |
| Repository corruption warning | Repository and cluster logs, competing writer check | DBRE / PLT |
| RPO breach | Latest successful snapshot and source replay watermark | DBRE / DATA |
| Restore rejects index | Open-index collision, snapshot/index version, allocation | DBRE |
| Slow restore | Network/object-store latency, disk, recovery limits | DBRE / PLT |
| APP still failing post-restore | DNS/endpoint, aliases, mappings, auth, query semantics | APP / DBRE |
| Authentication after feature restore fails | Security state overwrite / break-glass plan | SEC / DBRE |

Never repair repository corruption by manually editing its files. Escalate to Elastic/provider and use documented repository recovery guidance.

## 16. Production restore decision and change gates

Before any production restore:
1. Incident ID, business impact, commander and DR executor identified.
2. Source snapshot SUCCESS, correct scope and version compatibility independently reviewed.
3. Latest recoverable watermark/estimated data loss confirmed with DATA/APP.
4. Target environment/shard/disk/network capacity validated.
5. Security, encryption, repository access and credential recovery in place.
6. Index/alias, feature-state, ILM and application dependencies assessed.
7. Detailed execution plan, expected writes, replay and rollback/failback designed.
8. Approvals from DBRE, APP, DATA, PLT and incident/change authority recorded as applicable.
9. Business-service validation tests, success criteria and abort triggers agreed.
10. UTC timeline and evidence location established.

Do not perform unapproved wildcard deletion, restore of the security feature state, cluster-wide overwrite, or disable authentication/disk protections to accelerate restoration.

## 17. Evidence and reporting templates

### Daily snapshot health report

| Field | Entry |
|---|---|
| Date, cluster, owner | |
| Repository / SLM policy | |
| Latest snapshot ID / SUCCESS state | |
| Start/end UTC and age versus RPO | |
| Required indices, shards, feature scope | |
| Failures, partials, permissions or storage alarms | |
| Incident/ticket, next action, accountable owner | |

### Monthly controlled restore report

| Field | Entry |
|---|---|
| Drill ID / change ticket / participants | |
| Environment and exact versions | |
| Snapshot ID and source index | |
| Target index name and read-only repository control | |
| Snapshot completeness and restore duration | |
| Reconciliation, mappings and app test results | |
| Business recovery point and observed RPO | |
| Total observed RTO and step timing | |
| Findings, corrective actions and sign-off | |

### Quarterly DR readiness summary

Capture backup coverage, missed policies, recovery tests and gaps, region dependencies, feature-state/security plan, RPO/RTO performance, cost/capacity constraints, approvals and owner-assigned follow-up tasks.

## 18. Milestone 6 acceptance criteria

- [ ] Every production cluster has an approved recovery tier, owner, RPO and RTO.
- [ ] Required index, data-stream, cluster and feature-state backup coverage documented.
- [ ] Separate secure backup of node configuration, keystore and TLS assets documented.
- [ ] Snapshot repository off-cluster, secured, audited and single-writer rule enforced.
- [ ] SLM policy, retention and real snapshot completion monitored.
- [ ] RECENT SUCCESS snapshot meets actual recoverability requirements.
- [ ] One isolated staging restore passes data and application reconciliation.
- [ ] Large-scale/region DR tabletop and timed exercise performed.
- [ ] Verified business RPO/RTO measured including provisioning and endpoint validation.
- [ ] Restore permissions and emergency break-glass procedures tested.
- [ ] Cross-cloud/version compatibility and provider constraints recorded.
- [ ] Alert routing, storage retention, no-data and escalation reviewed.
- [ ] Production restore authorization and failback controls approved.
- [ ] Evidence register updated and stakeholders sign off.

**Definition of done:** Actual recovery procedures and monitoring must be validated, measured and signed off; publishing this Markdown does not certify disaster recovery.

## 19. References

**Elasticsearch 7.17 version-specific:**
- [Snapshot and restore overview](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/snapshot-restore.html)
- [Register repository; read-only sharing](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/snapshots-register-repository.html)
- [Take snapshots and configure SLM](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/snapshots-take-snapshot.html)
- [Restore snapshots; rename-on-restore](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/snapshots-restore-snapshot.html)

**Cross-version background (verify relevance to 7.17):**
- [Backup contents and compatibility](https://www.elastic.co/docs/deploy-manage/tools/snapshot-and-restore)
- [Repository corruption handling](https://www.elastic.co/docs/troubleshoot/elasticsearch/diagnosing-corrupted-repositories)
- [Elastic support lifecycle](https://www.elastic.co/support/eol)

---

**Document status:** Draft only. No Elasticsearch commands, cloud repository changes, production restores, disaster injection, or live RPO/RTO tests were executed during publication.
