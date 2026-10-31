# Page 01 — PostgreSQL DBRE Ownership, Responsibilities & RACI

**Document ID:** PG-DBRE-OPS-001  
**Owner:** PostgreSQL DBRE team  
**Status:** DRAFT — NOT APPROVED FOR PRODUCTION  
**Scope:** PostgreSQL self-managed, AWS RDS for PostgreSQL/Aurora PostgreSQL, Azure PostgreSQL Flexible Server and Google Cloud SQL for PostgreSQL  
**Review:** Quarterly and after significant platform/application changes

## 1. Mission and purpose

The PostgreSQL DBRE team maintains the reliability, availability, performance, recoverability, scalability, security implementation, and cost efficiency of PostgreSQL services. Responsibility boundaries must be explicit between customer-run engines and managed cloud databases.

**DBRE owns:** database health, database configuration within allowed privileges, query execution diagnostics, locks, connection pressure, replication/WAL health, autovacuum and anti-wraparound, backup/PITR verification, recovery exercises, growth/capacity forecasting, schema/index maintenance governance, safe changes and database incidents.

**DBRE supports but does not solely own:** application SQL, code releases, business-data correctness, access/security policy, source-of-truth retention, underlying infrastructure/network, cloud service-level failures, account billing and approvals.

## 2. Role definitions

| Code | Team | Responsibility |
|---|---|---|
| DBRE | Database Reliability Engineering | PostgreSQL operations, diagnosis, replication/recovery, maintenance, tuning |
| APP | Application Engineering | SQL/application behavior, connection pools, transaction patterns, functional validation, service SLO |
| DATA | Data Engineering/Business Data Owner | Data correctness, migrations and retention/business disposition |
| PLT | Platform/Cloud SRE | Hosts/OS/containers/Kubernetes, networking, disks, DNS, cloud infrastructure, managed service configuration |
| SEC | Security/Compliance | Access/security policy, audit, privacy and legal hold requirements |
| FIN | FinOps/Finance | Cost attribution, budget authorization and measured savings |
| SM | Service/Change/Incident Management | Formal change approval and major incident leadership |
| CSP | Cloud service provider/vendor | Provider-managed engine infrastructure, HA/backup service mechanisms and supported escalations |

**RACI legend:** A=single accountable decision-maker, R=executor, C=consulted, I=informed, —=normally uninvolved. Assign exactly **one A per activity**. Multiple Rs allowed. RACI is a proposed team standard, not a statement that existing agreements have already been approved.

## 3. Reliability and performance RACI

| Activity | DBRE | APP | DATA | PLT | SEC | FIN | SM |
|---|---|---|---|---|---|---|---|
| Database operational health/availability | A/R | C | I | R | I | I | I |
| PostgreSQL performance, locks and wait diagnostics | A/R | R | C | C | I | I | I |
| Business-facing query/request latency SLO | R | A/R | C | I | I | I | I |
| SQL/query design and application connection pools | C | A/R | C | I | I | I | I |
| PostgreSQL configuration and parameters | A/R | C | C | R | C | I | C |
| Vacuum/autovacuum, analyze and bloat review | A/R | C | R | C | I | I | I |
| Replication/slots/WAL/standby operations | A/R | C | C | R | I | I | I |
| Database growth and storage forecast | A/R | C | C | R | I | C | I |
| Instance/volume/network provisioning | C | I | I | A/R | C | C | I |
| Index design to support application query semantics | R | A/R | C | I | I | I | I |
| PostgreSQL platform patch/upgrade technical work | A/R | R | C | R | C | I | C |
| Data migration/reconciliation | R | R | A/R | C | C | I | C |

## 4. Security, change, recovery and governance RACI

| Activity | DBRE | APP | DATA | PLT | SEC | FIN | SM |
|---|---|---|---|---|---|---|---|
| DB authentication/role and grant implementation | R | C | C | C | A | I | I |
| Encryption/TLS/access policy definition | R | C | C | R | A/R | I | I |
| Database backup/PITR policy and technical validation | A/R | C | C | R | C | I | I |
| Backup storage/managed cloud protection | R | I | I | A/R | C | I | I |
| Business recovery priorities and acceptable data loss | R | A | R | C | C | I | I |
| DR/failover execution and single-writer verification | A/R | R | R | R | C | I | C |
| Application recovery acceptance | R | A/R | R | C | I | I | I |
| Business retention/legal data disposal authorization | R | C | A/R | I | C | I | C |
| Database/partition/table/index retirement execution | A/R | R | C | I | C | I | C |
| PostgreSQL incident technical RCA | A/R | R | R | C | C | I | I |
| Major incident command and communications | R | R | R | R | C | I | A/R |
| Formal production change authorization | R | C | C | C | C | C | A/R |
| Compute/storage right-sizing technical recommendation | A/R | C | C | R | I | R | C |
| Business budget and billing approval | R | C | C | R | I | A/R | I |

**Separate accountabilities:** DATA authorizes destructive business data disposal; DBRE is accountable for safe technical execution; SM authorizes formal change when required. APP certifies functionality and SLOs after changes.

## 5. Self-managed versus managed-provider boundary

| Responsibility | Self-managed PostgreSQL | AWS RDS/Aurora / Azure Flexible Server / Google Cloud SQL |
|---|---|---|
| Host/OS, PostgreSQL service and storage engine | PLT and DBRE own operations | Provider manages underlying host/engine infrastructure |
| PostgreSQL parameters and allowed extensions | DBRE under PLT configuration/change controls | DBRE within provider parameter/extension restrictions |
| WAL archives, backup files | DBRE + PLT | Provider-managed backup/PITR service; customer config/validation remains |
| HA and failover mechanics | DBRE/PLT design and execute | Provider-managed HA behavior according to service tier/config |
| Query tuning, connection pooling, vacuum/index governance | DBRE + APP | DBRE + APP (same responsibilities, provider limits) |
| Authentication and data policies | SEC/DBRE/APP | SEC/DBRE/APP plus managed IAM/identity/network capabilities |
| Restore application correctness | APP + DATA + DBRE | APP + DATA + DBRE |
| Service incident investigation | DBRE, PLT, vendor if used | DBRE/PLT and provider support |

**Important distinctions:**
- RDS for PostgreSQL and Aurora PostgreSQL are different architecture/products; do not apply instance backup, storage or reader endpoint assumptions interchangeably.
- Managed PostgreSQL does not grant unrestricted Linux root or PostgreSQL superuser privileges.
- Azure Flexible Server HA, Cloud SQL HA and RDS Multi-AZ depend on explicitly selected configurations, service tier and region.
- Physical/logical replication and provider HA are not universally interchangeable with backup/PITR.

## 6. Mandatory production ownership register

| Field | Value |
|---|---|
| Service/account/cluster/instance | TBD |
| Deployment type/provider/region, exact engine version | TBD |
| Engine edition/service tier and support lifecycle | TBD |
| Primary/standby/read replicas and endpoint/port | TBD |
| DBA/DBRE primary, backup and on-call route | TBD |
| APP/DATA/PLT/SEC contacts, vendor support plan | TBD |
| Critical application/database owners | TBD |
| Availability, latency, freshness SLOs | TBD |
| RPO/RTO and recovery method | TBD |
| Backup retention, latest restore evidence | TBD |
| Expected replication, WAL slot and failover behavior | TBD |
| Disk/WAL/compute cost center and forecast | TBD |
| Runbook, Grafana/Prometheus, incident/change links | TBD |
| Last review/sign-off date | TBD |

## 7. Change approval and separation of duties

| Action | Minimum risk control |
|---|---|
| Read-only stats and metadata | Least-privilege monitoring role |
| Query-plan review | Use EXPLAIN without ANALYZE in production until execution impact assessed |
| Parameter tuning, connection limits, vacuum tuning | DBRE plan, APP impact assessment and change approval |
| CREATE/REINDEX INDEX CONCURRENTLY | Test capacity, DDL locking/transaction limitations and rollback |
| VACUUM FULL / CLUSTER / nonconcurrent REINDEX | Explicit maintenance window, storage and lock impact |
| Terminate backend / cancel SQL | APP transaction owner review, avoid system-critical processes |
| Drop replication slot / change WAL retention | DBRE + downstream DATA/APP approval, RPO and disk risk |
| Promote/failover standby | Incident commander, fencing/single-writer gate, APP/DATA validation |
| PITR/restore production | Recoverability, data-loss acceptance, recovery plan, approvals |
| Drop table/partition/schema/database | Written DATA+APP permission, legal hold, tested recovery, SM approval |
| Engine upgrade / instance resize | Staging verification, backup, rollback/cutover and hypercare |

A query or table showing no observed activity is NOT automatically unused. Retention is a business policy, not an index-stats inference.

## 8. Severity and escalation

P1: major business outage, unavailable primary, confirmed data loss or critical corruption. P2: sustained service SLO degradation, lag/backup/wraparound risk. P3: emerging bloat, growth, recurring locks and maintenance backlog. P4: informational optimization.

Route database issues to DBRE; code and pool behavior to APP; host/cloud infrastructure to PLT; data correctness and retention to DATA; security to SEC; high-impact provider faults to CSP; incident command and official updates to SM.

## 9. Milestone 1 acceptance

- [ ] Complete and verify production topology/ownership register.
- [ ] Name DBRE primary and secondary on-call owners.
- [ ] Validate division of DBRE/APP/DATA/PLT/SEC/FIN/SM responsibilities.
- [ ] Map self-managed, RDS/Aurora, Azure Flexible Server and Cloud SQL provider boundaries.
- [ ] Approve change and destructive-data authorization controls.
- [ ] Record backup/PITR/failover accountable owners and RPO/RTO.
- [ ] Record unsupported versions and upgrade plans.
- [ ] Obtain stakeholder review and sign-off.

## References

- [PostgreSQL administration and monitoring](https://www.postgresql.org/docs/current/monitoring.html)
- [PostgreSQL release lifecycle](https://www.postgresql.org/support/versioning/)
- [Amazon RDS for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/)
- [Google Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
