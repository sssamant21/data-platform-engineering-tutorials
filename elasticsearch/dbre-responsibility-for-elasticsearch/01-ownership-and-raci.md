# Page 01 — Elasticsearch DBRE Ownership, Responsibilities & RACI

**Owner:** Elasticsearch DBRE | **Status:** Draft | **Review cycle:** Quarterly
**Applies to:** Production, staging, QA and development; self-managed and managed services with documented provider boundaries.

## 1. Mission and boundaries

DBRE is accountable for **Elasticsearch platform reliability**: availability, operational performance, shard/index management, capacity, backups, recovery, monitoring, upgrades and safe maintenance. It supports, but does not exclusively own, application query design, business data correctness, retention decisions, cloud infrastructure and enterprise security policy.

**Required outcome:** Every production cluster, major index/data domain and operational change has a named accountable owner and escalation path.

## 2. Teams

| Code | Team | Primary responsibility |
|---|---|---|
| DBRE | Database Reliability Engineering | Elasticsearch administration, health, SLO diagnostics, backups, technical recovery |
| APP | Application Engineering | Search behavior, query semantics, integration, application SLO and functional validation |
| PLT | Platform / Infrastructure SRE | Compute, OS, Kubernetes, network, cloud storage and infrastructure provisioning |
| DATA | Data Engineering / Business Data Owner | Source correctness, ingestion contracts, business retention and deletion authorization |
| SEC | Security / Compliance | Security policy, access policy, audit, privacy and compliance |
| SM | Service / Change Management | Enterprise change approval, major incident coordination and communications |

**RACI:** A=one accountable decision owner, R=execution, C=consult, I=informed, —=not ordinarily involved. Assign exactly one A per activity; multiple Rs are allowed.

## 3. RACI — Reliability, performance, capacity

| Activity | DBRE | APP | PLT | DATA | SEC | SM |
|---|---|---|---|---|---|---|
| Elasticsearch cluster health and node/shard recovery | A/R | I | C | I | I | I |
| JVM, GC, circuit breaker and node-level ES tuning | A/R | C | C | — | — | I |
| Application query design, result size and pagination | C | A/R | I | C | — | I |
| Elasticsearch execution diagnostics and cluster tuning | A/R | C | C | I | — | I |
| Business-facing search availability/latency SLO | R | A/R | C | C | — | I |
| Indexing infrastructure performance | A/R | C | C | R | — | I |
| Upstream pipeline correctness and freshness | C | C | I | A/R | — | I |
| Per-index growth, shard planning and capacity forecast | A/R | C | R | C | — | I |
| Underlying VM, disk, cloud network and Kubernetes | C | I | A/R | I | C | I |
| Cost/right-sizing technical recommendation | A/R | C | R | I | — | C |

## 4. RACI — Indices, data, security, recovery and incidents

| Activity | DBRE | APP | PLT | DATA | SEC | SM |
|---|---|---|---|---|---|---|
| Index settings, allocation, templates and shards | A/R | C | C | C | — | I |
| Application mapping semantics and compatibility | C | A/R | I | C | — | I |
| Alias/write-index cutover technical execution | A/R | R | I | C | — | I |
| Lifecycle implementation (ILM) | A/R | C | I | C | C | I |
| Business retention/deletion authorization | R | C | I | A/R | C | C |
| Approved index deletion execution | A/R | C | I | C | I | C |
| Source-to-index data correctness | I | R | I | A | I | — |
| Snapshot policy and restore execution | A/R | C | R | C | C | I |
| Snapshot repository infrastructure | C | I | A/R | I | C | I |
| Post-recovery application validation | R | A/R | C | C | I | I |
| Security policy and privilege approval | R | C | C | I | A/R | I |
| Elasticsearch RBAC implementation | R | C | C | — | A | I |
| ES technical incident response and RCA | A/R | R | R | C | C | I |
| Major incident coordination | R | R | R | I | C | A/R |
| Production change authorization (formal) | R | C | C | C | C | A/R |
| Platform upgrade technical delivery | A/R | R | R | C | C | C |

**RACI distinction:** DATA is accountable for **business permission to delete**; DBRE is accountable for **safe technical execution**. SM provides formal change authorization when policy requires it.

## 5. Required DBRE responsibilities

### 5.1 Availability and HA
- Monitor cluster health, elected master, node departures, primary/replica availability, allocation deciders and recovery delays.
- Establish cluster failure-domain and replica policies with platform/application owners.
- Validate failover and post-recovery application functionality.

### 5.2 Performance and indexing
- Investigate search/fetch times, thread-pool rejections, breaker trips, heap/GC, disk and merge activity.
- Partner with APP on query profiles, aggregations, fan-out, pagination, routing and returned document size.
- Partner with DATA on indexing throughput, upstream lag, retries and write failures.

### 5.3 Data/index lifecycle
- Own shard plan, rollover configuration, aliases, index templates and technical ILM operation.
- Request source-data ownership, retention and disposal approvals from DATA before implementing destructive changes.
- Never equate zero documents, no aliases, old creation date or missing observed traffic with safe deletion.

### 5.4 Capacity, upgrades and cost
- Forecast primary and total storage, shard sizes, compute utilization and recovery headroom.
- Recommend right-sizing with peak-load evidence, rollback procedures and application SLO validation.
- Inventory Elasticsearch versions and track vendor support exposure and approved upgrade plans.

### 5.5 Backup, DR and security
- Configure and monitor snapshot scheduling; verify with controlled test restores and measured RPO/RTO.
- Implement access controls consistent with SEC policy; apply least privilege, audit and credential rotation.
- Coordinate repository permissions and storage connectivity with PLT.

## 6. Change approval matrix

| Action | Technical execution | Required gate |
|---|---|---|
| Health and stats inspection | DBRE | Authorized read-only role |
| Alert threshold tuning | DBRE | DBRE review and applicable change policy |
| Replica/refresh setting change | DBRE | Impact review, rollback and change approval |
| Alias cutover/reindex | DBRE | APP validation, DATA where appropriate, change approval |
| Force merge | DBRE | Capacity/IO assessment, maintenance approval |
| Node right-sizing/upgrade | PLT + DBRE | APP benchmark, DBRE review, change approval |
| Snapshot restore | DBRE | Recovery authorization and application validation |
| Index deletion | DBRE | Written DATA approval, APP impact check, change record |
| Emergency data-loss-risk action | Designated responders | Incident commander and authorized data-risk acceptance |

**High-risk changes require:** affected resources, baseline, impact, owner, approval, execution plan, rollback/recovery, validation and evidence links. Never have a single engineer request, authorize and execute an irreversible deletion without independent approval.

## 7. Ownership register (one record per cluster)

| Field | Value |
|---|---|
| Cluster ID / name | TBD |
| Environment / provider / region | TBD |
| Exact ES version and lifecycle status | TBD |
| Application services and index owners | TBD |
| DBRE primary / backup and on-call schedule | TBD |
| APP / PLT / DATA / SEC contacts | TBD |
| Availability, latency and freshness SLOs | TBD |
| Business recovery priority, RPO and RTO | TBD |
| Snapshot repository and validated recovery evidence | TBD |
| Grafana dashboards, alerts and runbooks | TBD |
| Change authorization / escalation links | TBD |
| Last ownership review | TBD |

## 8. Incident escalation

- **DBRE lead:** RED/YELLOW conditions, unavailable shards, heap/breakers, indexing/search execution, snapshots, ES configuration.
- **APP lead:** user-facing latency, query optimization, request fan-out and business recovery verification.
- **PLT lead:** hosts, disks, Kubernetes, storage, cloud networking and infrastructure provisioning.
- **DATA lead:** source correctness, ingestion contract, retention/deletion authorization.
- **SEC lead:** authentication incidents, sensitive data, audit and privileges.
- **SM/incident commander:** major incident priority, coordination and approved communications.

## 9. Acceptance criteria

- [ ] Every production cluster has named primary and backup DBRE owners.
- [ ] All six partner teams review and approve RACI.
- [ ] Formal and business-data approval rights are recorded separately.
- [ ] Incident escalation, recovery and backup ownership are clear.
- [ ] Unsupported versions and lifecycle exceptions have named owners.
- [ ] Cluster register, dashboards and runbooks are linked in Confluence.
- [ ] DBRE lead and relevant stakeholder representatives sign off.

**Completion:** RACI approved and production cluster ownership records verified; publishing this page is not sufficient.

## References

- [Elastic security privileges](https://www.elastic.co/docs/reference/elasticsearch/security-privileges)
- [Elastic snapshot and restore](https://www.elastic.co/docs/deploy-manage/tools/snapshot-and-restore)
- [Elastic support lifecycle](https://www.elastic.co/support/eol)
