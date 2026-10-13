# Chapter 053 — PostgreSQL Row-Level Security and Secure Application Access

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Design, implement, test and operate Row-Level Security (RLS) for a shared-table, multi-tenant PostgreSQL application. Demonstrate that authenticated application identities can only read and modify rows permitted by policy, even when SQL statements omit tenant filters. This chapter follows [Chapter 052 — Authentication and TLS](052-postgresql-authentication-pg-hba-conf-and-tls-security.md).

## 2. Security boundaries

```text
TLS + authentication -> LOGIN role -> table GRANT -> RLS policy -> permitted rows
                                              |
                                   connection pool / app context
```

RLS supplements, rather than replaces, authentication, object GRANTs, parameterized SQL, trusted tenant authorization, auditing and secure connection handling.

When RLS is enabled on a table and no applicable policy grants access, normal users are denied access to its rows (default deny). A role still needs appropriate table privileges before RLS is evaluated.

## 3. Policy semantics

```sql
ALTER TABLE app.orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY orders_select ON app.orders
FOR SELECT TO app_reader
USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY orders_write ON app.orders
FOR INSERT TO app_writer
WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

- `USING` restricts which existing rows are visible or eligible for SELECT, UPDATE and DELETE.
- `WITH CHECK` restricts new row values for INSERT and UPDATE.
- `FOR ALL` policies can apply to multiple commands; omitted WITH CHECK for a policy that applies to writes can inherit the USING expression, subject to PostgreSQL's policy rules.
- Permissive policies (the default) are OR-combined for a command; restrictive policies are AND-combined with the permissive result. At least one permissive policy must permit access.
- Policies are scoped to roles, but roles can acquire policy applicability through membership. Test effective identities, not merely definitions.

**Important:** a custom GUC such as `app.tenant_id` is not a trusted identity assertion. A client able to run arbitrary SQL can often change it. Never use client-writable session variables alone as the security boundary against hostile or compromised tenants.

## 4. Who can bypass RLS?

Superusers and roles with `BYPASSRLS` bypass RLS. Table owners normally bypass RLS unless `ALTER TABLE ... FORCE ROW LEVEL SECURITY` is used; owners retain powerful DDL rights and can change policies. Roles that inherit owner privileges can also undermine intended boundaries.

Use separate NOLOGIN table owner, migration identity and low-privilege application login roles. Ensure the application login is not an owner, superuser or BYPASSRLS role. `FORCE ROW LEVEL SECURITY` is defense in depth for owner queries, not a protection against a malicious owner able to alter the table.

## 5. Tenant identity patterns

| Pattern | Benefits | Risks |
|---|---|---|
| Dedicated DB role per tenant | Tenant identity tied to authenticated DB role | Role lifecycle and connection pool complexity |
| Shared app role + tenant session setting | Operationally simple | Session context is client-writable; SQL injection can switch tenants |
| Trusted gateway / SECURITY DEFINER API | Centralizes authorization | Requires careful function ownership, pinned search_path and argument validation |
| Database-per-tenant | Stronger operational separation | Higher administration overhead |

For untrusted clients, prefer a database-verifiable identity or a trusted service boundary that prevents arbitrary SQL and independently authorizes tenant claims. The lab uses **dedicated tenant login roles** and a fixed role-to-tenant mapping in the policy, avoiding user-controlled tenant context as the sole boundary.

## 6. Reference policy: trusted role mapping

```sql
CREATE TABLE app.tenant_memberships (
    db_role name PRIMARY KEY,
    tenant_id uuid NOT NULL
);
REVOKE ALL ON app.tenant_memberships FROM PUBLIC;

CREATE POLICY tenant_orders_select ON app.orders
FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM app.tenant_memberships m
    WHERE m.db_role = current_user AND m.tenant_id = orders.tenant_id
  )
);
```

**Caution:** direct policy queries of a private mapping table run with the querying user's privileges and can produce `permission denied`. The complete lab instead uses a small, carefully owned `SECURITY DEFINER` lookup function with a fixed `search_path`; only trusted administrators can change its mapping. Review function EXECUTE grants and ownership carefully.

## 7. Application and connection-pool rules

- Never share an unrestricted tenant identity across mutually untrusted callers.
- Prefer transaction pooling only when tenant context is bound and cleared safely within each transaction; do not assume a pooled session preserves correct tenant identity.
- With trusted app-only session context, use `SET LOCAL` within an explicit transaction and reset it automatically at transaction end; still validate claims at the application boundary.
- Use prepared statements and parameterized queries; RLS does not prevent SQL injection or side channels.
- Re-test policies after schema migrations, role changes, pooler configuration changes and PostgreSQL upgrades.

## 8. Monitoring and incident response

Inspect `pg_policies`, `pg_class.relrowsecurity`, `pg_class.relforcerowsecurity`, role attributes and table ACLs. Audit privileged DDL, policy changes and unexpected cross-tenant result counts. A query returning zero rows can mean an RLS restriction, an incorrect role, or simply no data; correlate identity and policies before diagnosing.

| Symptom | Likely cause | Response |
|---|---|---|
| All rows invisible | No applicable permissive policy | Inspect pg_policies and effective role |
| INSERT rejected | WITH CHECK fails | Verify tenant assignment and role mapping |
| UPDATE unexpectedly blocked | USING or WITH CHECK fails | Evaluate old and new row constraints |
| Tenant data leak | Owner/BYPASSRLS or permissive OR policy | Stop exposure; inspect effective identity and policies |
| Mapping function permission denied | EXECUTE grant or definer privilege | Check function owner, search_path and ACL |
| Cross-tenant results after pooling | Session identity/context reuse | Isolate sessions and correct pooler lifecycle |

## 9. Production deployment runbook

1. Inventory application roles, tenant model, existing data quality, tables and migrations.
2. Backfill and validate tenant IDs; reject NULL/unknown ownership before enabling policies.
3. Deploy tested policies and role mappings in staging with negative tests.
4. Enable RLS in an approved window, confirm application query and DML paths, and monitor errors.
5. Use independent tests for two or more tenants, including SELECT/INSERT/UPDATE/DELETE and joins.
6. Verify no runtime role has owner/BYPASSRLS/SUPERUSER privilege.
7. For rollback, prefer reverting faulty policy definitions while maintaining isolation. **Do not simply disable RLS in production to restore functionality.**

## 10. Hands-on lab and acceptance

The [Chapter 053 lab](../labs/053-postgresql-row-level-security-and-secure-application-access-lab.md) provisions a dedicated disposable database with two tenants and a definer-controlled mapping, then runs positive and negative assertions. Includes provisioning, verification and cleanup instructions.

**Acceptance:** tenant A cannot read, insert, update or delete tenant B rows; policy violations are rejected; application roles cannot change mapping or bypass RLS; pooled context risks are documented. **Runtime:** pending.

## Official references

- [Row security policies](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [CREATE POLICY](https://www.postgresql.org/docs/18/sql-createpolicy.html)
- [Security definer functions](https://www.postgresql.org/docs/18/sql-createfunction.html)
- [Role attributes](https://www.postgresql.org/docs/18/role-attributes.html)

**Next:** Chapter 054 — PostgreSQL Auditing, Logging and Security Monitoring.
