# 101 — Least Privilege and SQL Access-Control Principles

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · **PostgreSQL 18 lab target** · **Audience:** data engineers, application engineers, DBRE/SRE, analysts

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [SQL lab](../labs/101-least-privilege-access-control.sql) · [Previous: 100](../part-10-performance/100-lab-10-baseline-tune-and-remeasure-a-slow-query.md) · Next: 102 — Users, roles, GRANT, REVOKE, and ownership (planned)

## 1. Outcomes and prerequisites (0–5 minutes)

You will be able to explain least privilege, separate authentication from authorization, inventory object privileges, design a read-only reporting role, distinguish table from schema privileges, recognize ownership and default-privilege risks, and propose a safe access-review workflow. Review [004 — database objects](../part-01-fundamentals/004-databases-schemas-tables-rows-columns.md).

**Scenario:** A fictional reporting service reads synthetic retail orders. It should not modify rows, create objects, access unrelated schemas, or inherit administrative rights. A separate ingestion service requires writes, but only to designated staging tables. DBREs approve the role design; application and data owners define the required operations.

## 2. Core principles and threat model (5–15 minutes)

**Authentication** verifies who connects. **Authorization** determines what that identity may do. **Least privilege** means only necessary actions, objects, environments, and duration. **Separation of duties** prevents a routine reporting identity from becoming an owner or administrator. **Defense in depth** adds network controls, TLS, secrets management, auditing, and application-layer tenant checks.

SQL privileges are not universally portable. Standard SQL includes `GRANT` and `REVOKE`, but role membership, schema usage, ownership, default privileges, row-level security, and effective access checks differ among products.

| Identity | Legitimate need | Not required |
|---|---|---|
| reporting_reader | SELECT on approved reporting views | INSERT, UPDATE, DELETE, CREATE, ownership |
| ingest_writer | INSERT/UPDATE on approved staging objects | superuser, access to unrelated patient or billing data |
| migration_deployer | approved DDL during a controlled deployment | permanent use as an application login |
| dbre_operator | monitored operational diagnostics and approved maintenance | routine application transactions using an admin account |

**PostgreSQL nuance:** `USAGE` on a schema permits name resolution, not SELECT on its tables. Table SELECT alone is insufficient without schema USAGE. Object owners have inherent control over owned objects; `REVOKE` does not make an owner equivalent to an ordinary reader. Roles can inherit rights through membership; audit *effective* access, not just directly granted ACL entries. `PUBLIC` means every role, not a named team. Database CONNECT, schema USAGE, object privileges, sequence privileges, and function EXECUTE are separate dimensions. New functions commonly grant EXECUTE to PUBLIC by default unless controlled. PostgreSQL 15+ defaults differ from older versions for the public schema; always inspect rather than assume.

## 3. Worked design and SQL examples (15–30 minutes)

**Illustrative PostgreSQL 18 design — review only; DO NOT execute against production:**

```sql
-- Requires approved ownership/role administration, isolated test environment.
CREATE ROLE reporting_reader NOLOGIN;
GRANT USAGE ON SCHEMA reporting TO reporting_reader;
GRANT SELECT ON reporting.daily_sales TO reporting_reader;
-- A separate, non-admin login may receive membership after approval:
-- GRANT reporting_reader TO reporting_app;
```

`NOLOGIN` creates a group role; it is not a service identity. `GRANT SELECT` is scoped to one approved object. The example assumes `reporting.daily_sales` already exists and is authorized for this audience. A view is not automatically a security boundary: review its owner, dependencies, `security_invoker` setting, RLS behavior, and sensitive columns. Do not expose `SELECT *` from unrestricted base tables.

**Portable principle:** request only SELECT for a reporting workload. **PostgreSQL-specific audit:**

```sql
SELECT current_database(), current_user, session_user;
SELECT has_schema_privilege(current_user, 'pg_catalog', 'USAGE') AS can_resolve_catalog;
SELECT has_database_privilege(current_user, current_database(), 'CONNECT') AS can_connect;
```

These introspection functions are PostgreSQL-specific. They show the *current session's* effective privileges and do not certify an application's full entitlement set. A production review also inventories role memberships, object ownership, PUBLIC grants, default privileges, and actual application identity.

**Avoid false confidence:** `REVOKE ALL ON TABLE ... FROM role` may leave access through another role or PUBLIC. Privilege checks are object- and context-specific. `SECURITY DEFINER` routines and permissive views can expose data beyond direct table grants. Tenant isolation requires separately reviewed RLS policies or application controls, not merely a SELECT grant.

## 4. Hands-on read-only lab (30–50 minutes)

Use a disposable PostgreSQL 18 database named `sql_tutorials`, an unprivileged lab login, and no production credentials. From repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/101-least-privilege-access-control.sql
```

The [lab](../labs/101-least-privilege-access-control.sql) starts a read-only transaction, checks PostgreSQL major version and database identity, uses local timeouts, checks the current identity and database/catalog privileges, and compares a synthetic permissions matrix against an explicit allowlist. It does **not** create users, grant permissions, query sensitive business tables, or mutate persistent objects.

**Expected synthetic matrix (calculated, not observed):** reporting_reader has exactly one allowed operation, SELECT on reporting.daily_sales; ingest_writer has INSERT and UPDATE on staging.orders; migration_deployer has CREATE on staging; there are four allowed assignments, zero forbidden assignments, and zero missing assignments. The fixture is a *policy model*, not evidence of actual PostgreSQL ACL state.

Exercises: (A) explain why a reporting role should not own its view; (B) identify which additional schema permission is required for SELECT; (C) describe how role membership or PUBLIC could defeat a simplistic REVOKE; (D) sketch a quarterly review recording business owner, justification, approver, expiration, and effective access evidence.

## 5. Validation, troubleshooting and operational guardrails (50–55 minutes)

- **Permission denied for schema:** verify USAGE on the intended schema and the application's actual session role; never solve by granting superuser.
- **Permission denied for relation:** inspect table/view SELECT, membership, object ownership, and whether the query references additional objects.
- **Unexpected access:** check PUBLIC grants, inherited memberships, security-definer routines, views, default privileges, and search_path.
- **Cannot connect:** database CONNECT, authentication rules, network access and TLS are separate checks.
- **Access change procedure:** data owner approves purpose and scope; security reviews sensitive access; DBRE implements with peer review, expiry where appropriate, audit evidence, and a tested revocation/rollback plan. Use a dedicated isolated instance for grant/revoke experiments.
- **Safety:** never run DDL, GRANT/REVOKE, or privilege probing against production from this tutorial. The supplied lab uses only synthetic CTEs and safe introspection; catalog privileges depend on the test identity and are displayed, not asserted as universal constants.

## 6. Review questions and answers (55–60 minutes)

1. **Authentication versus authorization?** Identity verification versus permission to act.
2. **Why not give a reporting service table ownership?** Ownership confers object control beyond SELECT.
3. **What does schema USAGE grant?** Name resolution, not table SELECT.
4. **Does REVOKE from one role guarantee no access?** No; inherited memberships and PUBLIC can still grant access.
5. **Why does a view need review?** Its owner, security mode, dependencies, policies, and selected columns determine exposure.
6. **Is the lab a live entitlement audit?** No; it models a synthetic policy and displays limited session introspection.
7. **Who approves a new reporting grant?** The accountable data owner, with security/DBRE controls according to policy.

## References

- [PostgreSQL 18 — Privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [PostgreSQL 18 — Database Roles](https://www.postgresql.org/docs/18/user-manag.html)
- [PostgreSQL 18 — GRANT](https://www.postgresql.org/docs/18/sql-grant.html)
- [PostgreSQL 18 — Privilege inquiry functions](https://www.postgresql.org/docs/18/functions-info.html)
- [PostgreSQL 18 — Row security policies](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [PostgreSQL 18 — CREATE VIEW](https://www.postgresql.org/docs/18/sql-createview.html)

**Validation state:** Authored; targeted static/manual reasoning only. Independent editorial review, full SQL syntax/link QA, and actual isolated PostgreSQL 18 runtime execution with retained evidence pending.
