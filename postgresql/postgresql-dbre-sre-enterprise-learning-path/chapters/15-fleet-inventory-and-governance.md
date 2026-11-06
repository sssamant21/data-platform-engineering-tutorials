# Chapter 15 — Fleet Inventory and Governance

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Audience:** DBRE, SRE, database/platform engineering, application owners  
**Duration:** 60 minutes | **Status:** Authored; lab execution and independent review pending  
**Lab:** [Chapter 15 — Fleet Inventory and Governance](../labs/chapter-15/README.md)

> Educational, non-production exercise. A database inventory is an operational control, not proof of security, backup recoverability, or production readiness.

## Learning outcomes

By the end, you should be able to (1) define the boundary of a PostgreSQL fleet, (2) distinguish automatically discoverable metadata from owner-attested governance records, (3) collect a safe baseline from PostgreSQL 17, (4) detect and triage configuration drift without changing production settings, (5) design evidence and exception workflows across self-managed, AWS RDS, and Kubernetes deployments.

## Prerequisites and assumptions

- Familiarity with Chapters 01–14, especially platform ownership, backups, and monitoring.
- Docker Desktop/Engine with a running Linux container backend; `docker` CLI; a terminal (PowerShell or POSIX shell). No cloud account or Kubernetes cluster required.
- **Reference runtime:** PostgreSQL 17 official Docker image, isolated and bound to localhost. SQL examples use PostgreSQL 17 catalogs and views; check compatibility before use on other versions.
- Permission to create/delete a disposable local Docker container and volume. No access to a real fleet is assumed.

## 60-minute teaching outline

| Minutes | Topic | Output |
|---|---|---|
| 0–8 | Why fleet inventory is a reliability prerequisite | Inventory boundary and risks |
| 8–18 | Fleet model, identity and ownership | Required field schema |
| 18–28 | Discovery architecture across platforms | Source-of-truth and evidence map |
| 28–40 | Read-only PostgreSQL metadata and baselines | Inventory and drift observations |
| 40–52 | Hands-on lab: synthetic fleet and governance | Exception and owner review |
| 52–60 | Acceptance, limitations and operational handoff | Signed-off training checklist |

## 1. Fundamentals: what is a fleet?

A **fleet** is the set of PostgreSQL clusters and managed instances the organization operates or is accountable for. A cluster may host multiple databases; an application may use multiple clusters. Do not confuse *database*, *instance*, *cluster*, *service endpoint*, *replica*, and *application*.

- **Cluster/instance identity:** stable ID from the platform control plane, plus environment, account/project, region/site, namespace, and cluster lineage. DNS name alone is not a reliable identity: endpoints can be reassigned.
- **Database inventory:** database name, owner role, size and usage signals. These are discovered **per cluster**, not a complete enterprise inventory by themselves.
- **Business ownership:** application/service, accountable owner, escalation contact, business criticality, retention and classification. These must be attested by owners; PostgreSQL cannot infer them.
- **Reliability ownership:** DBRE/SRE on-call, RPO/RTO objectives, backup policy, restore-test evidence, HA topology, monitoring, runbook, last successful recovery exercise.
- **Governance state:** last observed timestamp, evidence source, approved baseline version, drift/exception ticket, reviewer, next review date, lifecycle status.

**Never treat absence of client sessions, a database role, or an alias as proof that a database is unused.** Before deletion or decommission, corroborate dependency graphs, scheduled/batch workloads, owner approval, backup retention, and change-management controls.

## 2. Reference architecture

```text
Self-managed host agent / PostgreSQL SQL snapshot --+
RDS API (authorized read-only discovery) -------------+--> collector --> normalized inventory
Kubernetes operator + cluster API (read-only) --------+                      |
                                                                            v
                                                          CMDB / service catalog + owner attestations
                                                                            |
                                                  baseline engine --> drift findings --> tickets
                                                                            |
                                                    dashboards / periodic reviews / audit evidence
```

The collector should be **read-only by default**, use least-privilege identities, redact secrets, timestamp observations, and track the difference between **unknown**, **not applicable**, **observed**, and **owner-attested**. It must not change a setting or grant privileges as a side effect of discovery.

**Data flow:** collect platform identity first, correlate with PostgreSQL metadata, enrich with owner-provided service metadata, compare approved policy, then route exceptions. Maintain provenance for every field. A successful SQL query alone does not establish complete fleet coverage.

## 3. Minimum inventory schema

| Field | Source | Validation |
|---|---|---|
| `fleet_asset_id`, `platform_asset_id`, `environment` | CMDB + platform API | Unique, stable, reconciled |
| `platform`, `account/project`, `region/site`, `namespace` | Control plane | Present or explicit N/A |
| `postgres_major`, `minor`, `last_patch_date` | Server + release process | Supported-version policy |
| `database_name`, `database_role_owner`, `database_bytes` | `pg_database` and functions | Timestamp and cluster ID |
| `app_service`, `business_owner`, `dbre_owner`, `oncall` | Service catalog/attestation | Named, current, review date |
| `classification`, `residency`, `retention` | Data governance | Owner approved; avoid raw sensitive data |
| `rpo_target`, `rto_target`, `backup_policy`, `restore_evidence` | Recovery program | Evidence freshness; not merely configured |
| `ha_mode`, `replica_count`, `monitoring`, `runbook` | Platform + operations | Topology and alerts confirmed |
| `baseline_version`, `drift_state`, `exception_id` | Policy engine | Ticketed deviations and expiry |
| `observed_at`, `source`, `collector_version` | Collector | Traceable and stale-data detection |

A single PostgreSQL cluster can host several application databases with different owners and classifications. Record cluster-level controls separately from database-level and application-level controls; do not silently copy an RPO target from one database to every other database.

## 4. Read-only PostgreSQL discovery

Execute on an **authorized, isolated PostgreSQL 17 instance** using `psql`. The full reproducible examples are in [inventory.sql](../labs/chapter-15/inventory.sql).

```sql
SELECT current_setting('server_version') AS version,
       pg_is_in_recovery() AS is_standby,
       pg_postmaster_start_time() AS started_at;

SELECT datname,
       pg_get_userbyid(datdba) AS role_owner,
       pg_database_size(oid) AS bytes
FROM pg_database
WHERE datallowconn AND NOT datistemplate
ORDER BY datname;

SELECT name, setting, unit, source, pending_restart
FROM pg_settings
WHERE name IN ('max_connections', 'shared_buffers', 'wal_level',
               'password_encryption', 'ssl')
ORDER BY name;
```

**Interpretation:** the first query is an observation at a point in time, not proof of HA. `pg_database` lists databases in the connected cluster, not the fleet. `pg_settings` reports current session-visible configuration and restart state; it does not replace reading deployment manifests, parameter groups or operator specifications. Role owners are **database authorization roles**, not business owners. `pg_stat_database` counters can reset; never interpret a low counter as proof of no use.

The lab also reads `pg_roles` metadata without retrieving password hashes. Do **not** query `pg_authid`, dump secrets, enumerate application query text, or export connection strings in an inventory report.

## 5. Configuration baselines and drift

A baseline is a **versioned, environment-specific policy**, not one global list of “best” numbers. Examples: approved major version, `password_encryption`, logging requirements, TLS enforcement at every applicable network boundary, backup/restore coverage, and alert routing. `max_connections` and `shared_buffers` are workload- and platform-dependent; an illustrative mismatch is a review item, not a command to set a value.

The [drift.sql](../labs/chapter-15/drift.sql) exercise compares a **synthetic** policy with observed values and returns `MATCH` or `REVIEW`; it never calls `ALTER SYSTEM`, `SET`, or `pg_reload_conf()`. Distinguish:

1. **Approved variation** — platform or workload-specific exception with expiry.
2. **Unapproved drift** — open ticket, assign owner, assess blast radius and schedule remediation.
3. **Unknown/stale** — discovery or attestation gap; not automatically “compliant.”
4. **High-risk control failure** — escalate per policy; do not self-remediate a live database without authorization.

Record change provenance, maintenance windows, rollback plans, and a post-change validation checkpoint before changing live settings.

## 6. Platform-specific discovery boundaries

| Platform | Discovery mechanism | Limitations and ownership |
|---|---|---|
| Bare metal / VM | Host inventory, `pg_settings`, SQL catalogs, backup/monitoring tools | DBRE owns OS/storage, patching, TLS, backup and HA coordination unless delegated |
| Amazon RDS for PostgreSQL | Authorized `aws rds describe-db-instances`, tags, parameter groups, backup metadata, SQL | AWS manages host layers; customer still owns workload configuration, roles, data policy, restore testing. AWS CLI calls are **optional read-only**; may generate API activity |
| Kubernetes operator | Read-only `kubectl get clusters` for installed operator CRDs, StatefulSets/PVCs, secrets **metadata only**, SQL | Namespace is not an ownership record; operator/CRD version and backup policy require verification. **Do not** dump Secret objects |

Optional commands **only with pre-existing authorized access** (not part of required lab):

```bash
# AWS CLI v2, read-only, may produce audit events; no resources created:
aws rds describe-db-instances --region YOUR_REGION \
  --query 'DBInstances[?Engine==`postgres`].[DBInstanceIdentifier,EngineVersion,DBInstanceStatus,MultiAZ]' \
  --output table

# Kubernetes, only if CloudNativePG CRD is already installed:
kubectl get clusters.postgresql.cnpg.io -A
```

The AWS result is not guaranteed to include every Aurora topology or every region/account; design separate discovery for those. Use a deliberate account/region matrix and tag reconciliation. Kubernetes access must be scoped to metadata; never assume the presence of a CRD or operator.

## 7. Governance operating model

| Activity | Accountable | Contributors | Evidence |
|---|---|---|---|
| Register new PostgreSQL asset | Platform/DBRE service owner | Provisioning automation | Asset ID, region, cluster lineage |
| Attest application and data ownership | Application/business owner | DBRE, security | Service catalog record, classification |
| Maintain baselines and exceptions | DBRE lead / security per policy | SRE, application | Policy version, ticket, expiry |
| Verify backup and restore readiness | DR/DBRE owner | Application | Restore logs, measured RPO/RTO, approval |
| Review stale, orphaned, EOL assets | Service owner | DBRE, finance, security | Owner review and change request |
| Approve decommission | Authorized business/data owner | DBRE, security, compliance | Dependency check, retention/legal hold, backup and change approval |

**Suggested review cadence (example, not a universal standard):** daily discovery reconciliation, weekly drift triage, monthly owner attestation for high-criticality assets, quarterly recovery evidence review, and exception expiry reminders. Tailor to policy.

## 8. Common failure modes and troubleshooting

- **Missing databases:** connected to the wrong cluster, insufficient visibility, only one account/region scanned, or collector failed. Verify cluster identity and coverage.
- **Wrong owner:** `datdba` shows a PostgreSQL role, not the business owner. Correlate with service catalog and ask for attestation.
- **False drift:** policy uses a different major version, unit, session context, parameter group or operator default. Normalize values and capture `source`.
- **Unexpected zero activity:** `pg_stat_database` counters may reset, idle/batch workloads may be rare, and collector timing matters. Do not infer deletion eligibility.
- **Sensitive export:** avoid usernames, IPs, endpoint hostnames and classification details in broadly shared reports unless access controls require them; redact before sharing.
- **Stale evidence:** use `observed_at`, collector health, and source freshness SLAs; stale does not equal compliant.

## 9. Guardrails and rollback

All chapter SQL is read-only. The lab setup creates only disposable synthetic roles/databases in a named Docker container. Cleanup removes that **specific** container and named volume after verifying their identity. No production deletion, privilege changes, forced restarts, cloud provisioning or operator deployment is permitted. If a policy mismatch is found, record it; do not apply a fix automatically. The rollback for the local lab is to remove its disposable assets; production remediation requires an approved, tested rollback and evidence.

## 10. Acceptance checklist

- [ ] Explain the distinction between a cluster, database, platform asset and application service.
- [ ] Produce a schema with asset identity, owners, classification, recovery targets, policy and provenance.
- [ ] Collect a safe, timestamped PostgreSQL 17 metadata snapshot from the isolated lab.
- [ ] Identify a synthetic configuration mismatch without modifying the server.
- [ ] Record one example exception with owner, priority, expiry and evidence source.
- [ ] Explain why database role ownership and low usage counters are not sufficient for decommission.
- [ ] Explain optional AWS/Kubernetes discovery limitations and access requirements.
- [ ] Demonstrate scoped cleanup, and distinguish authored, executed, reviewed and production-certified status.

## Official references (checked 2026-11-02)

- [PostgreSQL 18 — System catalogs](https://www.postgresql.org/docs/18/catalogs.html)
- [PostgreSQL 18 — `pg_database`](https://www.postgresql.org/docs/18/catalog-pg-database.html)
- [PostgreSQL 18 — `pg_roles`](https://www.postgresql.org/docs/18/view-pg-roles.html)
- [PostgreSQL 18 — `pg_settings`](https://www.postgresql.org/docs/18/view-pg-settings.html)
- [PostgreSQL 18 — Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [AWS CLI v2 — describe-db-instances](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html)
- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
- [Kubernetes API access controls](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

**Next:** Chapter 16 — Security, Roles, Secrets and Compliance.
