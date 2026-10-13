# Chapter 078 — PostgreSQL Row-Level Security, Data Protection and Audit Controls

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Enforce tenant isolation with PostgreSQL Row-Level Security (RLS), protect sensitive data through layered controls and capture trustworthy audit evidence. Extends [Chapter 076 — Roles and Privileges](076-postgresql-security-architecture-roles-and-privileges.md) and [Chapter 077 — Authentication and TLS](077-postgresql-authentication-pg-hba-conf-tls-and-connection-security.md).

**Security invariant:** a session authenticated as tenant A cannot read, insert, update or delete tenant B's records, even when it holds table-level DML privileges.

## 2. Security boundaries

```text
Client identity + TLS + authentication
              |
          LOGIN role
              |
     database/schema/table GRANT
              |
       RLS policy evaluation
              |
      permitted tenant rows
              |
   audit evidence + retention
```

RLS complements, rather than replaces, table grants. It does not secure filesystem backups, logical exports, application logs, query text, monitoring data or secrets.

## 3. PostgreSQL RLS mechanics

- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` activates RLS. With no applicable policy, ordinary users are denied row access by default.
- `USING` controls which existing rows are visible/eligible for SELECT, UPDATE and DELETE.
- `WITH CHECK` controls which new row values may be inserted or produced by UPDATE.
- Policies are command-specific (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `ALL`) and may target roles.
- Permissive policies are OR-combined; restrictive policies are AND-combined, but at least one applicable permissive policy is required.
- Table owners normally bypass RLS unless `FORCE ROW LEVEL SECURITY` is enabled. Superusers and roles with `BYPASSRLS` bypass it regardless; do not use these as application accounts.
- Referential-integrity checks and certain internal operations may bypass RLS to preserve database integrity; do not treat RLS as a complete inference-proof isolation boundary.
- `TRUNCATE` and `REFERENCES` are not controlled by row security; deny these privileges to tenant accounts.

## 4. Identity binding and tenant isolation

For a simple, robust lab, bind each tenant to a distinct LOGIN role and use `current_user` in the policy. This avoids trusting arbitrary session variables that an untrusted SQL client can set.

```sql
CREATE POLICY tenant_select ON app.tenant_orders
FOR SELECT TO ch078_tenant_a,ch078_tenant_b
USING (tenant_role = current_user);

CREATE POLICY tenant_insert ON app.tenant_orders
FOR INSERT TO ch078_tenant_a,ch078_tenant_b
WITH CHECK (tenant_role = current_user);

CREATE POLICY tenant_update ON app.tenant_orders
FOR UPDATE TO ch078_tenant_a,ch078_tenant_b
USING (tenant_role = current_user)
WITH CHECK (tenant_role = current_user);

CREATE POLICY tenant_delete ON app.tenant_orders
FOR DELETE TO ch078_tenant_a,ch078_tenant_b
USING (tenant_role = current_user);
```

In pooled applications using one shared database role, `current_user` cannot distinguish tenants. A user-settable `current_setting('app.tenant_id')` alone is **not an authentication boundary** when arbitrary SQL execution is possible. Use an independently authenticated identity mapping, tightly controlled transaction-scoped context, carefully reviewed SECURITY DEFINER interface, or distinct database roles. Validate behavior with your pooler and ORM, including transaction reuse and error paths.

## 5. Owner and bypass hazards

Never connect tenant applications as the table owner or a `BYPASSRLS` role. Use a separate NOLOGIN owner, `FORCE ROW LEVEL SECURITY` where appropriate, and test the effective privileges of all service accounts. Restrict membership that permits `SET ROLE` into owner or privileged roles. Do not assume a policy protects queries executed by superusers.

## 6. Data protection beyond RLS

| Data path | Controls |
|---|---|
| Network transit | TLS `verify-full`, restricted endpoints and credential rotation |
| Storage / backups | Disk encryption, managed keys, backup access control and restore tests |
| Sensitive columns | Narrow column grants, views or approved masking/tokenization |
| Application output | Redaction, parameterized queries and least-privilege APIs |
| Monitoring and logs | Avoid secrets/PHI/PII in query text, logs, metrics labels and traces |
| Replication and exports | Dedicated permissions, secure channels and downstream controls |
| Retention/deletion | Documented lifecycle, legal hold and backup retention boundaries |

RLS filters rows, not sensitive columns within allowed rows. Column privileges and security-reviewed views may be needed; evaluate view ownership and `security_invoker` behavior. Use explicit threat modeling for timing/error and unique-key inference channels.

## 7. Audit controls

PostgreSQL built-in logs can record connections, disconnections, errors and selected statements. The `pgaudit` extension can provide richer statement/object audit coverage **when installed and configured**; it is not built into every PostgreSQL deployment or managed service.

Recommended audit fields: UTC time, database, session ID, authenticated user, effective user, client address, application name, command/object, result/error and incident correlation ID. Avoid logging parameter values containing sensitive data. Ship logs to a restricted, tamper-resistant destination with access control, retention and alerting. Do not claim built-in logging proves every row read or captures old/new row values; specialized application audit events or reviewed triggers may be required.

## 8. Audit and RLS inspection

```sql
SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
FROM pg_policies WHERE schemaname='app';

SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='app' AND c.relkind IN ('r','p');
```

Use [078 inspection SQL](../labs/sql/078-rls-and-audit-inspect.sql) for additional role and configuration review. Validate access with independent tenant login sessions, not only `SET ROLE`.

## 9. Incident troubleshooting

| Symptom | Potential cause | Investigation |
|---|---|---|
| Tenant sees zero rows | Missing permissive SELECT policy or identity mismatch | `current_user`, grants, `pg_policies` |
| INSERT rejected | `WITH CHECK` fails | Verify row tenant identity |
| UPDATE unexpectedly succeeds | Overly broad permissive policy | Inspect all policies and OR composition |
| Owner sees every row | Owner bypass | Check owner and FORCE RLS |
| Cross-tenant access | Privileged role, pool context leak, broad policy | Stop affected writes, preserve evidence, review sessions |
| Audit gap | Logging/pgaudit not enabled or collector failure | Check settings, extension, retention and delivery |
| Query slowdown | Policy predicates lack supporting indexes | Explain plans under tenant role; index tenant keys |

## 10. Safe rollout

1. Inventory sensitive tables, owners, app roles, pools, query patterns and data flows.
2. Create a threat model, including superuser, owner, shared-role and arbitrary SQL cases.
3. Add tenant-key constraints and appropriate indexes; verify uniqueness rules and FK semantics.
4. Write explicit SELECT/INSERT/UPDATE/DELETE policies; keep owners separate.
5. Test all CRUD and negative scenarios with actual nonprivileged sessions.
6. Stage with representative performance and transaction pooling behavior.
7. Roll out behind approved change control with logs and rollback plan.
8. Audit policy drift after migrations, restores, role changes and upgrades.

## 11. Hands-on lab and acceptance

Use [Chapter 078 lab](../labs/078-postgresql-row-level-security-data-protection-and-audit-controls-lab.md), [fixture SQL](../labs/sql/078-rls-fixture.sql), [inspection SQL](../labs/sql/078-rls-and-audit-inspect.sql) and [acceptance scorecard](../labs/acceptance/078-rls-audit-scorecard.csv).

**PASS requires:** isolated tenant reads/writes, denied cross-tenant INSERT/UPDATE/DELETE, owner and BYPASSRLS behavior documented, sensitive-column controls verified, audit events delivered and evidence redacted. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/ddl-rowsecurity.html
- https://www.postgresql.org/docs/18/sql-createpolicy.html
- https://www.postgresql.org/docs/18/runtime-config-logging.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.pgaudit.org/

**Next:** Chapter 079 — PostgreSQL Encryption, Secrets Management and Security Hardening.
