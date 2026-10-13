# Chapter 076 — PostgreSQL Security Architecture, Roles and Privileges

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Build a least-privilege PostgreSQL security architecture using login and NOLOGIN roles, object ownership, grants, schema boundaries, default privileges, role inheritance, audit queries and controlled access reviews. Security is a layered system: network controls, TLS, `pg_hba.conf`, authentication, SQL authorization, secret rotation, auditing and backup protection must work together.

## 2. Security architecture

```text
Identity / secret store / TLS / network policy
                    |
              pg_hba.conf
                    |
            PostgreSQL login role
                    |
           NOLOGIN group roles
                    |
      database -> schema -> tables/sequences/functions
                    |
           row-level security where needed
```

Do not conflate login ability, object ownership, membership and effective privileges. A role can own objects without LOGIN. A role with LOGIN should not automatically be a superuser or inherit unrelated administrative privileges.

## 3. Role design

| Role | LOGIN | Purpose | Boundaries |
|---|---|---|---|
| `ch076_owner` | NOLOGIN | Own schema and objects | Not used by application |
| `ch076_app_rw` | NOLOGIN | Runtime CRUD privilege bundle | No DDL, no ownership |
| `ch076_app_login` | LOGIN | Application connection | Member of runtime bundle only |
| `ch076_readonly` | NOLOGIN | SELECT bundle | No writes or DDL |
| `ch076_analyst_login` | LOGIN | Analyst connection | Member of read-only bundle |
| `ch076_monitor_login` | LOGIN | Monitoring | Narrowly scoped predefined monitoring role |

Prefer dedicated identities for applications, migrations, operators and automation. Use a separate migration identity that can `SET ROLE` to the owner when explicitly authorized. Avoid using `postgres` for routine application traffic.

## 4. PostgreSQL 18 membership semantics

PostgreSQL role membership supports distinct **INHERIT**, **SET**, and **ADMIN** options. `INHERIT` controls automatic use of privileges, `SET` controls `SET ROLE`, and `ADMIN` permits membership administration. Verify membership options with `pg_auth_members`; do not assume all three are equivalent. Review `CREATEROLE` and membership administration separately from superuser.

Illustrative membership:

```sql
GRANT ch076_app_rw TO ch076_app_login
  WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;
```

The login inherits CRUD but cannot `SET ROLE ch076_app_rw` or grant membership. Review version-specific syntax and permissions before using in a production environment.

## 5. Database, schema and object boundaries

PostgreSQL authorization is hierarchical but **not transitive**: database `CONNECT` does not grant schema `USAGE`, and schema `USAGE` does not grant table `SELECT`. Typical minimums:

```sql
GRANT CONNECT ON DATABASE ch076_lab TO ch076_app_rw;
GRANT USAGE ON SCHEMA app TO ch076_app_rw;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA app TO ch076_app_rw;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA app TO ch076_app_rw;
```

For a read-only bundle, grant CONNECT, schema USAGE and table SELECT. Sequence access is needed for certain insert patterns; `USAGE` on a sequence permits `nextval`. Do not grant `CREATE` on the application schema to runtime identities.

## 6. Ownership and default privileges

Only an object's owner (or authorized equivalent) can manage many object permissions and DDL operations. `ALTER DEFAULT PRIVILEGES` applies to **future objects created by the specified creating role**, not all roles, and does not retroactively modify existing objects. For migrations that `SET ROLE ch076_owner`:

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE ch076_owner IN SCHEMA app
GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO ch076_app_rw;

ALTER DEFAULT PRIVILEGES FOR ROLE ch076_owner IN SCHEMA app
GRANT SELECT ON TABLES TO ch076_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE ch076_owner IN SCHEMA app
GRANT USAGE,SELECT ON SEQUENCES TO ch076_app_rw;
```

Apply existing-object grants separately and audit both. Default privileges are scoped to the creating role and optionally schema; verify each migration tool's effective `current_user`.

## 7. PUBLIC and search_path risks

`PUBLIC` means all roles. Review database `CONNECT` and `TEMP`, schema `CREATE`, function `EXECUTE`, and extension ownership. In PostgreSQL 18, newly initialized databases normally have the `public` schema owned by `pg_database_owner`; defaults may differ in upgraded or customized databases. **Audit rather than assume**. Do not allow untrusted roles to create objects in schemas appearing on privileged `search_path`. Use schema-qualified objects and safe `search_path` for `SECURITY DEFINER` functions.

## 8. Predefined monitoring roles

`pg_monitor` aggregates monitoring privileges including `pg_read_all_settings`, `pg_read_all_stats` and `pg_stat_scan_tables`. Grant it only when needed: monitoring visibility can expose sensitive operational data. Do not grant `pg_read_server_files`, `pg_write_server_files`, `pg_execute_server_program`, `pg_signal_backend` or `BYPASSRLS` to application roles. Review other built-in roles separately.

## 9. Permission audits

Use [Chapter 076 inspection SQL](../labs/sql/076-security-roles-and-privileges-inspect.sql) to review LOGIN, SUPERUSER, CREATEROLE, CREATEDB, REPLICATION, BYPASSRLS, memberships, schema grants and default ACLs. Sample effective-access checks:

```sql
SELECT has_schema_privilege('ch076_app_login','app','USAGE');
SELECT has_table_privilege('ch076_app_login','app.orders','SELECT');
SELECT has_table_privilege('ch076_analyst_login','app.orders','INSERT');
```

Avoid trusting grants alone: test access with real nonprivileged login sessions. Object owner and superuser behavior can bypass ordinary ACL restrictions.

## 10. Operational security runbook

1. Inventory role owners, service accounts, expiry/rotation, group membership and schema owners.
2. Review effective privileges and sensitive predefined role membership.
3. Identify unexpected PUBLIC grants, broad schema CREATE and writable search_path exposure.
4. Use dedicated migration roles for DDL; review default ACLs and sequence grants.
5. Test revocation and access with least-privilege accounts in staging.
6. Apply approved grants/revocations with a rollback and session-impact plan.
7. Record who approved changes, role memberships and access-test evidence.
8. Repeat audits after migrations, restores, upgrades and incident response.

## 11. Hands-on lab and acceptance

Use [Chapter 076 lab](../labs/076-postgresql-security-architecture-roles-and-privileges-lab.md), [role fixture SQL](../labs/sql/076-security-role-fixture.sql), [inspection SQL](../labs/sql/076-security-roles-and-privileges-inspect.sql) and [acceptance scorecard](../labs/acceptance/076-security-access-scorecard.csv).

**PASS requires:** application CRUD without DDL; analyst SELECT without writes; owner separation; correct future-object privileges; no unwanted PUBLIC CREATE; controlled monitoring access; auditable membership options; and cleanup. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/user-manag.html
- https://www.postgresql.org/docs/18/role-membership.html
- https://www.postgresql.org/docs/18/ddl-priv.html
- https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html
- https://www.postgresql.org/docs/18/predefined-roles.html

**Next:** Chapter 077 — PostgreSQL Authentication, pg_hba.conf, TLS and Connection Security.
