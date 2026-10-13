# Chapter 054 — PostgreSQL Auditing, Logging and Security Monitoring

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Build a defensible PostgreSQL security observability program: collect authentication and authorization evidence, monitor role/privilege and schema changes, use native logging and pgAudit appropriately, and investigate suspicious activity without leaking secrets or overloading the database. This chapter follows [Chapter 053 — Row-Level Security](053-postgresql-row-level-security-and-secure-application-access.md).

## 2. Security telemetry architecture

```text
Clients -> PostgreSQL authentication / authorization / SQL
                         |
                server logging collector
                         |
                log files / syslog / journald
                         |
                agent -> secure central store -> detections / dashboards
                         |
                retention + access control + incident evidence
```

PostgreSQL server logs and pgAudit provide **different** kinds of evidence. Native logs can report failed authentication, connection lifecycle, statements and errors according to settings. pgAudit provides structured session/object audit entries for configured statement classes, but requires an installed compatible extension and carefully selected scope. Neither replaces host, network, IAM or application audit logs.

## 3. Native logging controls

| Setting | Operational purpose | Caution |
|---|---|---|
| `logging_collector` | Collect server log output into files | Startup/restart requirement |
| `log_destination` | stderr, csvlog, jsonlog, syslog, etc. | Availability depends on platform |
| `log_line_prefix` | Correlate time, PID, user, DB, app, session | Ensure consistent identity fields |
| `log_connections` / `log_disconnections` | Connection lifecycle | High-volume pooler environments |
| `log_min_error_statement` | Statements producing errors | May expose literals/secrets |
| `log_min_duration_statement` | Slow statement evidence | Performance-oriented; sensitive query text |
| `log_statement` | Statement classes | Broad `all` is high-volume and sensitive |
| `log_lock_waits` | Long lock waits | Useful in investigations |
| `log_checkpoints` | Checkpoint activity | Operational correlation |
| `log_timezone` | Consistent timestamps | Prefer UTC |

Prefer structured `jsonlog` or `csvlog` where supported and compatible with the log pipeline. When using `stderr` text logs, ensure prefixes include time, PID, user, database, application and session identifiers. For forensic reliability, synchronize clocks and retain source metadata.

## 4. Read-only configuration audit

```sql
SELECT name,setting,unit,context,source,pending_restart
FROM pg_settings
WHERE name IN (
 'logging_collector','log_destination','log_line_prefix','log_connections',
 'log_disconnections','log_min_error_statement','log_min_duration_statement',
 'log_statement','log_lock_waits','log_checkpoints','log_timezone',
 'shared_preload_libraries'
)
ORDER BY name;

SELECT extname,extversion FROM pg_extension WHERE extname='pgaudit';
SELECT name,setting,source FROM pg_settings WHERE name LIKE 'pgaudit.%' ORDER BY name;
```

Do not assume pgAudit is available merely because it is listed in a tutorial. It must be installed for the correct PostgreSQL major version, included in `shared_preload_libraries` (requires restart), and `CREATE EXTENSION pgaudit` must be performed as required by the pgAudit release and deployment method.

## 5. pgAudit scope and tradeoffs

Common pgAudit session audit classes include `READ`, `WRITE`, `FUNCTION`, `ROLE`, `DDL`, `MISC`, and `MISC_SET` (consult the installed pgAudit release for exact options). Object auditing can narrow coverage using role-based object permissions. Audit volume can grow dramatically for high-throughput queries, and logged statements/parameters may include sensitive data.

**Example policy for a disposable test instance only:**

```conf
shared_preload_libraries = 'pgaudit'
pgaudit.log = 'role,ddl'
pgaudit.log_catalog = off
```

The `shared_preload_libraries` setting must preserve other existing libraries, and a server restart is required when changing it. Do not blindly overwrite this list. pgAudit's actual configuration is usually applied using supported GUC mechanisms after installation; validate in your environment.

## 6. Security events to monitor

- Repeated failed authentication from the same identity/source or many identities.
- New superuser, replication or BYPASSRLS privileges; changes to role membership and default privileges.
- `GRANT`, `REVOKE`, `ALTER ROLE`, `CREATE ROLE`, `DROP ROLE` and object ownership changes.
- `ALTER TABLE ... DISABLE ROW LEVEL SECURITY`, RLS policy changes and SECURITY DEFINER function modifications.
- Changes to `pg_hba.conf`, TLS files, logging settings and `shared_preload_libraries`.
- Unusual bulk reads, unexpected data exports, `COPY` activity and high-volume errors.
- Logging gaps, agent failures, clock skew, disk-full conditions and missing audit data.

For every alert, define baseline, severity, environment, identity, source, time window, suppression and an actionable runbook. Distinguish authorized migrations from unauthorized changes.

## 7. Investigation workflow

1. Establish incident scope, detection time and affected PostgreSQL cluster.
2. Preserve raw log files and centralized copies with timestamps, checksums and access controls.
3. Correlate PostgreSQL session/process identifiers, client address, application_name, database, authenticated role and SQLSTATE with proxy/app/host logs.
4. Inspect current `pg_roles`, `pg_auth_members`, `pg_policies`, `pg_default_acl`, `pg_stat_activity` and schema ownership; current catalog state is **not** historical proof of what happened.
5. Determine whether a privileged change, failed login, exfiltration or RLS bypass occurred. Avoid printing credentials or sensitive query parameters in shared tickets.
6. Contain using approved credential rotation, network restrictions or role changes, preserving a break-glass path.
7. Verify containment, restore approved grants/policies and document timeline, evidence gaps and follow-up actions.

## 8. Operational failure modes

| Symptom | Likely cause | Response |
|---|---|---|
| No audit entries | pgAudit not loaded, wrong scope, collector failure | Check preload, extension, GUC and pipeline |
| Excessive audit volume | Broad READ/WRITE/all logging | Reduce scope, sample where appropriate, capacity-plan |
| Missing client identity | Pooler or incomplete log prefix | Correlate proxy/application identity |
| Audit events arrive late | Collector backpressure | Check queue, disk and ingest delay |
| Authentication errors spike | Credential rotation, attack or bad rollout | Correlate sources and recent changes |
| Logs expose sensitive values | Broad statement/parameter logging | Restrict access, adjust capture and retention |
| Disk pressure from logs | Rotation/retention failure | Restore rotation, offload securely, preserve evidence |

## 9. Production acceptance and rollback

Define event coverage, required retention, central log delivery SLO, alert response owner, least-privilege access and evidence integrity. Pilot changes in a lab, measure event volume and performance, then roll out gradually. Rollback should restore previous GUCs and pipeline routing without deleting existing audit evidence. Log setting changes may require reload or restart depending on `pg_settings.context`.

## 10. Hands-on lab

The [Chapter 054 lab](../labs/054-postgresql-auditing-logging-and-security-monitoring-lab.md) includes a read-only logging audit, lab-only DDL and role events, controlled failed-authentication tests, a pgAudit availability check and an evidence worksheet. It does not modify production logging or install pgAudit automatically.

**Acceptance:** required security events are observable, correctly attributed, delivered centrally and retained; alert tests distinguish authorized from suspicious changes. **Runtime:** pending.

## Official references

- [Error reporting and logging](https://www.postgresql.org/docs/18/runtime-config-logging.html)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [pgAudit project](https://github.com/pgaudit/pgaudit)
- [Database roles](https://www.postgresql.org/docs/18/user-manag.html)

**Next:** Chapter 055 — PostgreSQL Security Hardening and Access Control Acceptance Lab.
