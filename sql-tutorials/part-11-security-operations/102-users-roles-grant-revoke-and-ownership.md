# 102 — Users, Roles, GRANT, REVOKE, and Ownership

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · **PostgreSQL 18 lab target** · **Audience:** beginners, data engineers, application engineers, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [SQL lab](../labs/102-users-roles-grant-revoke-ownership.sql) · [Previous: 101](101-least-privilege-and-sql-access-control-principles.md) · Next: 103 — Row-level security and data-access policies (planned)

## 1. Outcomes and prerequisites (0–5 minutes)

After this chapter, explain login versus group roles, inspect role memberships, reason about effective privileges, distinguish object ownership from GRANT, design least-privilege access, and plan a reversible authorization change. Review [Chapter 101](101-least-privilege-and-sql-access-control-principles.md) first.

**Scenario:** A fictional retail reporting application needs read access to an approved view; an ingestion service needs limited writes to staging. The data owner approves the dataset and purpose, security reviews risk, and DBRE implements reviewed permissions. All examples use fictional identifiers; never use production credentials.

## 2. Core concepts and portable versus PostgreSQL SQL (5–15 minutes)

A **role** is an authorization principal. In PostgreSQL, a role with `LOGIN` can authenticate; a `NOLOGIN` role groups privileges. SQL products differ: some distinguish users and roles explicitly, and managed platforms may restrict administrative operations.

| Concept | Practical meaning | PostgreSQL 18 detail |
|---|---|---|
| Login role | Identity that can connect | `CREATE ROLE ... LOGIN` |
| Group role | Reusable bundle of privileges | `CREATE ROLE ... NOLOGIN` |
| Membership | Makes privileges available through another role | `GRANT group_role TO login_role`; inheritance and `SET ROLE` options matter |
| Object grant | Permits specified action on specified object | `GRANT SELECT ON TABLE ... TO ...` |
| Schema grant | Enables name lookup, or object creation if CREATE granted | `GRANT USAGE ON SCHEMA ...` |
| Ownership | Controls alteration, dropping, and grant administration | Not equivalent to SELECT; owners have inherent rights |
| PUBLIC | Implicit group of all roles | Check inherited/public privileges before assuming a REVOKE removed access |

**Portable concept:** `GRANT` and `REVOKE` express object authorization. **Dialect-specific:** PostgreSQL role creation, membership options, `ALTER DEFAULT PRIVILEGES`, `has_*_privilege` functions, and ownership transfer syntax. SQL Server users/schemas and Snowflake role hierarchies follow different semantics.

## 3. Worked examples: approved change plan (15–30 minutes)

**Illustrative PostgreSQL 18 DDL — documentation only, never run on production or in the read-only lab.** Execute only in an explicitly approved disposable environment under an authorized test administrator after reviewing ownership and dependencies.

```sql
-- Prerequisites: the approved reporting schema and view already exist.
CREATE ROLE retail_report_reader NOLOGIN;
GRANT USAGE ON SCHEMA reporting TO retail_report_reader;
GRANT SELECT ON TABLE reporting.daily_sales TO retail_report_reader;
-- After creating a separate non-admin test login through an approved process:
-- GRANT retail_report_reader TO retail_report_app;
```

A view can expose data based on its owner and security configuration; assess dependencies, RLS, and sensitive columns. Do not assume a view is automatically safe. A schema USAGE grant alone cannot read tables, and SELECT on a table without schema USAGE may not permit qualified access.

**Revoke planning:** A direct `REVOKE SELECT ON TABLE reporting.daily_sales FROM retail_report_reader` removes that particular grant, not rights through another group, PUBLIC, or ownership. PostgreSQL owners retain inherent control even after an explicit revoke. Membership revocation and object privilege revocation are distinct changes. Record a before/after effective-access test with the actual application identity, and a rollback plan; avoid blanket `REVOKE ... FROM PUBLIC` without dependency analysis.

**Default privileges:** A grant on existing tables does not automatically cover future tables. `ALTER DEFAULT PRIVILEGES` controls privileges for objects created later by a particular creating role; it does not retroactively change existing objects. Sequences may need separate privileges, and routine EXECUTE grants warrant review.

**Read-only PostgreSQL-specific discovery:**

```sql
SELECT current_user, session_user, current_database();
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole
FROM pg_catalog.pg_roles
WHERE rolname = current_user;
SELECT has_database_privilege(current_user, current_database(), 'CONNECT');
```

These report the current session and a subset of its role properties, not a comprehensive security audit. Querying `pg_roles` is generally available, but organizational access controls and privileges can vary.

## 4. Hands-on lab (30–50 minutes)

Use a **disposable PostgreSQL 18** database named `sql_tutorials`, an unprivileged lab login, and no real credentials or data. Run from the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/102-users-roles-grant-revoke-ownership.sql
```

The [read-only SQL lab](../labs/102-users-roles-grant-revoke-ownership.sql) checks database and server major version, applies transaction-local timeouts, shows session identity, and evaluates a **synthetic authorization model**. No roles, grants, owners, schemas, or persistent tables are changed.

**Model:** Three fictional principals: `retail_reader`, `retail_app`, and `ingest_writer`. `retail_app` is a member of `retail_reader`; the group has SELECT on `reporting.daily_sales`. `ingest_writer` has INSERT on `staging.orders`. A proposed direct UPDATE on the reporting view is rejected by the allowlist.

**Calculated expected results (not observed):** 3 principals, 1 membership, 2 approved object grants, 1 rejected candidate grant, 0 missing/extra approved grants. The lab compares expected and modeled approved grants in both directions using `EXCEPT ALL`. It does **not** simulate PostgreSQL's full privilege engine or prove live entitlements.

**Exercises:** (A) Why should the app login not own the reporting view? (B) Which permissions permit a qualified SELECT from the view? (C) If a direct grant is revoked but access remains, what other paths should you inspect? (D) Design a change record: requester, data owner, approval, role, object, action, environment, expiration, test evidence, and rollback.

## 5. Troubleshooting and safety (50–55 minutes)

| Symptom | Diagnose safely | Avoid |
|---|---|---|
| Permission denied for schema | Inspect USAGE and actual session identity | Granting CREATE or superuser |
| Permission denied for relation | Check object SELECT, schema USAGE, membership, view dependencies | Blanket grants on all tables |
| Access remains after REVOKE | Check other roles, PUBLIC, ownership, security-definer routines | Claiming revoke success without an effective-access test |
| New tables inaccessible | Check object creator and default privileges | Assuming existing-table grants cover future tables |
| Unexpected admin rights | Inspect role attributes and membership options | Using admin accounts for applications |

Use least privilege, peer review, a scoped maintenance/change process, explicit rollback and post-change audit evidence. Never run grant/revoke/ownership changes against production as part of training. Role or ownership changes may have broad effects and should be tested independently on a disposable instance.

## 6. Review questions and answers (55–60 minutes)

1. **Can a NOLOGIN role authenticate?** No; it groups privileges.
2. **Does schema USAGE grant SELECT?** No; the object also needs an appropriate privilege.
3. **Does GRANT SELECT make a role the owner?** No; ownership is separate.
4. **Can REVOKE a single grant remove every access path?** No; memberships, PUBLIC, and ownership may still apply.
5. **Do default privileges modify existing objects?** No; they affect future objects created by the relevant role.
6. **Does the lab create real roles?** No; it evaluates synthetic rows and displays session metadata.
7. **What proves effective access?** A scoped, authorized test under the actual identity, plus privilege/membership review—not a modeled policy alone.

## References

- [PostgreSQL 18 — Database roles](https://www.postgresql.org/docs/18/user-manag.html)
- [PostgreSQL 18 — Role membership](https://www.postgresql.org/docs/18/role-membership.html)
- [PostgreSQL 18 — Privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [PostgreSQL 18 — GRANT](https://www.postgresql.org/docs/18/sql-grant.html)
- [PostgreSQL 18 — REVOKE](https://www.postgresql.org/docs/18/sql-revoke.html)
- [PostgreSQL 18 — ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)
- [PostgreSQL 18 — Privilege inquiry functions](https://www.postgresql.org/docs/18/functions-info.html)

**Validation:** Authored for publication; targeted static/manual inspection only. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime execution with retained evidence are pending.
