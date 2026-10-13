# Chapter 051 — PostgreSQL Security Architecture, Roles and Privilege Boundaries

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Learning outcomes

Design least-privilege PostgreSQL access with login and group roles, role membership, schema/object ownership, explicit GRANT/REVOKE, default privileges and role-boundary testing. This chapter begins the security track after [Chapter 050 — HA/DR Acceptance](050-high-availability-and-disaster-recovery-acceptance-project.md).

## 2. Security model

PostgreSQL authorization combines:
1. **Connection admission:** network exposure, TLS, `pg_hba.conf`, authentication and database `CONNECT`.
2. **Roles and membership:** login identities, non-login permission groups, `INHERIT` and `SET ROLE`.
3. **Object privileges:** database, schema, table, sequence, function and other object ACLs.
4. **Ownership:** owners can alter/drop objects and grant privileges; ownership is not the same as ordinary DML permission.
5. **Row-level security:** additional row visibility controls; not a replacement for schema/table permissions.
6. **Operational controls:** auditing, secret rotation, monitoring and periodic access review.

```text
Client identity (LOGIN)
    |  authentication + CONNECT
    v
Application role (NOLOGIN) -- membership --> runtime identity
    | schema USAGE
    | table SELECT/INSERT/UPDATE
    v
Application schema (owned by dedicated owner)
    |
    +-- tables / sequences / functions
```

## 3. Core role attributes

| Attribute | Purpose | Production guidance |
|---|---|---|
| `LOGIN` / `NOLOGIN` | Client identity vs permission group | Prefer NOLOGIN group roles |
| `SUPERUSER` | Bypasses most permission checks | Avoid for applications |
| `CREATEDB` | Create databases | Administrative scope only |
| `CREATEROLE` | Manage roles within PostgreSQL rules | Restrict to approved admins |
| `REPLICATION` | Replication connections and functions | Dedicated identities |
| `BYPASSRLS` | Bypass row-level security | Highly privileged |
| `INHERIT` / `NOINHERIT` | Automatic use of granted-role privileges | Design intentionally |
| `CONNECTION LIMIT` | Role connection limit | Not a substitute for pool controls |

In PostgreSQL 16+, role membership grants can specify `INHERIT`, `SET`, and `ADMIN` options. Evaluate these membership options explicitly instead of assuming every granted role is immediately usable or switchable.

## 4. Privilege boundaries and ownership

Use separate identities:
- **Object owner:** `NOLOGIN` role owning schema and tables; migrations run through a controlled owner context.
- **Application writer:** `LOGIN` identity belonging to an app-write permission group; DML only, no schema DDL.
- **Application reader:** `LOGIN` identity belonging to a read-only group; SELECT only.
- **Operational administrator:** separately authenticated, audited identity for approved changes.

For a schema, `USAGE` permits lookup of objects but does **not** grant SELECT/INSERT on its tables. Database `CONNECT` does not grant schema/table access. Table grants do not automatically grant sequence privileges; identity columns and serial sequences require separate evaluation. A role can also acquire rights via ownership, `PUBLIC`, other memberships or database defaults.

Avoid relying on the default `public` schema for application object creation. PostgreSQL 15+ defaults removed broad CREATE permission on the public schema for newly initialized databases, but upgraded clusters may retain older ACLs. **Inspect actual grants rather than assuming defaults.**

## 5. Safe reference architecture

```sql
-- Illustrative only; execute Chapter 051 lab in an isolated database.
CREATE ROLE app_owner NOLOGIN;
CREATE ROLE app_read NOLOGIN;
CREATE ROLE app_write NOLOGIN;
CREATE SCHEMA app AUTHORIZATION app_owner;
GRANT USAGE ON SCHEMA app TO app_read, app_write;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO app_read;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_write;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO app_write;
```

**Future tables are not covered by `GRANT ... ON ALL TABLES`.** Define `ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app` for objects created by that owner. Default privileges are tied to the creating role; privileges inherited from membership are not used to determine which role's defaults apply. Validate migrations create objects as the intended owner.

## 6. Default privileges and grant drift

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
  GRANT SELECT ON TABLES TO app_read;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_write;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
  GRANT USAGE, SELECT ON SEQUENCES TO app_write;
```

Run as `app_owner` or an appropriately authorized role. For functions, consider EXECUTE grants to `PUBLIC` and revoke them when unnecessary. Be aware that default `PUBLIC` function EXECUTE can expose newly created functions; handle creation/grants within a transaction if there is a transient exposure concern.

## 7. Inspection and verification

```sql
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles ORDER BY rolname;

SELECT r.rolname AS member, g.rolname AS granted_role,
       m.admin_option,m.inherit_option,m.set_option
FROM pg_auth_members m
JOIN pg_roles r ON r.oid=m.member
JOIN pg_roles g ON g.oid=m.roleid
ORDER BY 1,2;

SELECT nspname,pg_get_userbyid(nspowner) AS owner,nspacl
FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema';

SELECT defaclrole::regrole AS creator,defaclnamespace::regnamespace AS schema,
       defaclobjtype,defaclacl FROM pg_default_acl;
```

Also use `has_schema_privilege`, `has_table_privilege`, `has_sequence_privilege` and real negative-access tests. `\dp` and `\ddp` in `psql` help inspect object and default privileges.

## 8. Threat scenarios and troubleshooting

| Symptom / risk | Root cause | Safe response |
|---|---|---|
| Application can CREATE/DROP | Owner or broad membership | Separate owner and runtime roles |
| Reader can modify rows | Broad GRANT, PUBLIC, membership | Inspect effective grants and revoke unnecessary access |
| New tables inaccessible | Missing default privileges | Configure creator-specific defaults |
| INSERT fails on sequence | Sequence privileges absent | Grant minimal USAGE/SELECT as required |
| Role appears granted but access denied | Membership INHERIT/SET option | Inspect pg_auth_members |
| Unauthorized schema object shadowing | Unsafe search_path or CREATE | Lock down schema CREATE and qualify objects |
| Function escalation | SECURITY DEFINER with unsafe search_path | Review owner, function body and pinned search_path |
| RLS assumed sufficient | BYPASSRLS/owner privileges | Validate policy under actual identity |

## 9. Production change and rollback runbook

1. Inventory roles, dependencies, memberships, object owners and application service identities.
2. Export current grants/ownership and obtain change approval.
3. Test in a disposable database with positive and negative privilege assertions.
4. Apply narrowly scoped grants; avoid broad `PUBLIC` and `SUPERUSER` shortcuts.
5. Verify login, DML, migration and read-only flows; monitor permission-denied errors.
6. Roll back using captured ACLs/memberships, not an indiscriminate `GRANT ALL`.
7. Review access quarterly and after team/service ownership changes.

**Do not run `DROP ROLE`, `REASSIGN OWNED` or `DROP OWNED` as generic cleanup on shared systems; they can affect objects across databases.**

## 10. Lab and acceptance

The [Chapter 051 lab](../labs/051-postgresql-security-architecture-roles-and-privilege-boundaries-lab.md) provisions dedicated lab roles and schema, verifies intended DML permissions, confirms denied DDL/unauthorized writes and cleans up only lab-owned objects. Includes a SQL provisioning script and read-only verification script.

**Acceptance:** app reader can SELECT but not INSERT; writer can DML but not CREATE/DROP; owner can migrate; default privileges cover future tables; no SUPERUSER/BYPASSRLS for runtime identities. **Runtime:** pending.

## References

- [Database roles](https://www.postgresql.org/docs/18/user-manag.html)
- [Privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [Role membership](https://www.postgresql.org/docs/18/role-membership.html)
- [ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)

**Next:** Chapter 052 — PostgreSQL Authentication, pg_hba.conf and TLS Security.
