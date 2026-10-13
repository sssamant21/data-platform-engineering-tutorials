# Chapter 083 — PostgreSQL Configuration Management, Infrastructure as Code and Drift Detection

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Manage PostgreSQL configuration as a versioned, reviewed, testable operational contract. Reconcile **desired state**, **configuration files/control plane**, and **effective runtime state**, and detect drift before it becomes an incident.

Builds on [Chapter 082 — Version Upgrades](082-postgresql-version-upgrades-compatibility-testing-and-rollback-planning.md) and earlier chapters covering HA, backup, performance and security.

## 2. Sources of truth and precedence

```text
Git/IaC desired state -> Terraform / Ansible / Operator / provider API
                                  |
                          postgresql.conf
                           include files
                         postgresql.auto.conf
                                  |
                      PostgreSQL config processing
                                  |
               pg_settings: effective value + source
                                  |
                       actual runtime behavior
```

PostgreSQL settings can also be overridden at command line, database, role or session level depending on parameter context. `postgresql.auto.conf` is maintained by `ALTER SYSTEM` and generally takes precedence over ordinary configuration files. `pg_settings.source`, `sourcefile`, `sourceline`, `context` and `pending_restart` help explain effective settings. Some settings are only visible to sufficiently privileged roles.

**Do not assume** `SHOW work_mem` in an administrator session represents a different application's role/session overrides.

## 3. Configuration categories

| Category | Examples | Change behavior |
|---|---|---|
| Postmaster/startup | `shared_buffers`, `max_connections`, `shared_preload_libraries` | Requires server restart |
| SIGHUP/reload | `log_min_duration_statement`, `work_mem` default | Reload for configuration-file change; scope may vary |
| Session/user | `statement_timeout`, `search_path` | Role/database/session precedence |
| HA/replication | `wal_level`, `max_wal_senders`, `synchronous_standby_names` | Coordinate across topology |
| Security | `ssl`, `password_encryption`, HBA policy | Review client and admin access |
| Managed service | Parameter groups/provider settings | Provider-controlled apply/restart rules |

Always confirm the actual `pg_settings.context` and `pending_restart` on the deployed PostgreSQL version rather than relying only on generic categories.

## 4. Read-only drift inspection

```sql
SELECT name,setting,unit,source,sourcefile,sourceline,context,pending_restart
FROM pg_settings
WHERE name IN ('shared_buffers','max_connections','work_mem',
 'statement_timeout','log_min_duration_statement','shared_preload_libraries')
ORDER BY name;

SELECT sourcefile,sourceline,name,setting,applied,error
FROM pg_file_settings ORDER BY sourcefile,sourceline;
```

`pg_file_settings` reports parsed configuration-file entries, including overridden and invalid entries; it is **not** a substitute for `pg_settings` or role/database override inspection. A failed reload can leave previously active settings in effect. `pg_reload_conf()` requests reload; check logs and effective values afterward.

## 5. IaC ownership patterns

- **Terraform:** manage database infrastructure, networking, parameter groups, storage, backups, encryption, IAM and lifecycle policy. Treat plan output as review evidence, not proof of active PostgreSQL values.
- **Ansible:** manage packages, configuration templates, permissions, services and ordered reload/restart operations; enforce idempotence and protect credentials with an approved secret backend.
- **Kubernetes operators:** use the operator CRD as the supported interface; do not edit generated StatefulSets or config files that reconciliation will overwrite.
- **RDS/Aurora/managed services:** use provider parameter groups/API, observe apply methods and pending reboot states, and respect unsupported superuser/filesystem operations.
- **Self-managed HA:** coordinate changes through Patroni/HA controller configuration where applicable; avoid bypassing dynamic configuration and creating node-level drift.

Assign one authoritative owner per setting and infrastructure resource. Mixing `ALTER SYSTEM`, manual file edits, Terraform and operator reconciliation without clear precedence creates recurring drift.

## 6. Baseline as code

Use a reviewed baseline file with fields: setting, expected value, unit, scope, environment, owner, reason, change ticket, restart requirement and verification query. Do not store secrets or private keys in baseline CSVs.

Example desired state:

```text
name,expected_setting,scope,owner
log_min_duration_statement,1000,cluster,DBRE
statement_timeout,0,cluster,DBRE
```

Values are **lab examples**, not universal production recommendations. Define environment-specific performance/security thresholds and compare normalized units before marking a mismatch.

## 7. Drift detection workflow

1. Collect desired state from approved Git revision and deployed IaC state.
2. Query `pg_settings`, `pg_file_settings`, `pg_db_role_setting` and provider pending-change APIs.
3. Normalize values and units; compare role/database scope and `pending_restart`.
4. Classify **approved temporary exception**, **unapproved drift**, **pending restart**, or **measurement gap**.
5. Evaluate operational impact, especially memory, WAL, replication, auth and logging.
6. Open a tracked remediation with owner and change approval; avoid automatic restarts on detection alone.
7. Apply through the authoritative controller, verify effective state and close evidence.

A change can be pending in a cloud parameter group but not yet active in PostgreSQL; track both states.

## 8. Safe change and rollback

**Preflight:** capture baseline, backups/HA health, current values and source, application SLO, change owner, expected reload/restart impact and rollback.

**Change:** apply a reviewed Git/IaC change, inspect plan/diff, roll out to staging, validate, then deploy to production with topology-aware order. For restart-required parameters, use approved HA maintenance and failover procedures.

**Verify:** compare expected vs active `pg_settings`, check `pending_restart=false` for the changed setting, inspect logs, test connections and application workloads, monitor replication and resource utilization.

**Rollback:** revert the approved declaration, redeploy through the same owner, and perform necessary reload/restart with approval. Do not simply `ALTER SYSTEM RESET` if another controller will reapply the undesired value. Preserve the incident timeline and configuration diff.

## 9. Common incidents

| Symptom | Likely cause | Diagnosis |
|---|---|---|
| Value differs from Git | Manual ALTER SYSTEM, CLI, role or provider override | Check `pg_settings.source` and `pg_db_role_setting` |
| Change appears ineffective | Pending restart or failed reload | `pending_restart`, `pg_file_settings.error`, logs |
| Setting keeps reverting | Operator/HA controller reconciliation | Inspect controller source of truth |
| Nodes differ | Partial rollout or per-node override | Collect all instances and compare |
| Unexpected memory pressure | Overlarge `work_mem` or `max_connections` | Review per-session/role values and concurrency |
| Replica instability | Uncoordinated WAL/HA settings | Review replication topology and apply order |
| Terraform plan clean but DB differs | Out-of-band edits or provider pending apply | Compare provider state and SQL runtime |

## 10. Lab and acceptance

Use [Chapter 083 lab](../labs/083-postgresql-configuration-management-infrastructure-as-code-and-drift-detection-lab.md), [inspection SQL](../labs/sql/083-configuration-drift-inspect.sql), [baseline CSV](../labs/acceptance/083-configuration-baseline.csv), and [acceptance scorecard](../labs/acceptance/083-configuration-drift-scorecard.csv).

**PASS requires:** desired state versioned, drift detected, source identified, approved remediation applied, effective values verified, pending restarts reconciled, application health preserved and rollback demonstrated. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/config-setting.html
- https://www.postgresql.org/docs/18/view-pg-settings.html
- https://www.postgresql.org/docs/18/view-pg-file-settings.html
- https://www.postgresql.org/docs/18/sql-altersystem.html
- https://www.postgresql.org/docs/18/catalog-pg-db-role-setting.html

**Next:** Chapter 084 — PostgreSQL Maintenance Automation, Scheduling and Operational Runbooks.
