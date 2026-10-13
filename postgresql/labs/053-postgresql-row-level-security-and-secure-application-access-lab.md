# Chapter 053 — Row-Level Security and Secure Application Access Lab

**PostgreSQL 18 · Dedicated disposable database · Runtime validation pending.**

## 1. Safety and setup

Use a **new isolated** PostgreSQL database named `ch053_lab`, accessed by a lab administrator. Confirm the five lab roles are not in use anywhere else on the server. Never run against production. The test switches session authorization to simulate real tenant identities; use an authorized superuser in this disposable environment.

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -c "CREATE DATABASE ch053_lab"
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch053_lab -f postgresql/labs/sql/053-provision.sql
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch053_lab -f postgresql/labs/sql/053-verify.sql
```

The provision script refuses to run outside `ch053_lab`. Roles have no passwords: `SET SESSION AUTHORIZATION` is used for isolated test assertions; for real application connection tests, provision credentials through a secret manager.

## 2. Architecture

Two login roles (`ch053_tenant_a`, `ch053_tenant_b`) share `ch053.orders`. The table is owned by a separate NOLOGIN role. A protected role-to-tenant mapping is readable only through a tightly scoped SECURITY DEFINER function that resolves the authenticated `session_user`. Its owner is the lab administrator; the function pins `search_path` and schema-qualifies objects.

## 3. Verification

The script checks:
- A sees only A's row, B sees only B's row.
- A can insert/update/delete its own rows but cannot insert or change B rows.
- B cannot read A's row.
- Both tenant roles have no SUPERUSER/BYPASSRLS and no CREATE on schema.
- Both tenant roles cannot SELECT the protected mapping table.

Policy tests use `SET SESSION AUTHORIZATION` to test the actual identity instead of assuming superuser visibility reflects RLS.

## 4. Expected evidence

Record PostgreSQL version, `pg_policies`, `relrowsecurity`, role attributes, positive row counts, rejected cross-tenant writes and the script exit status. Capture any unexpected results as a **FAIL**. Inspect `pg_stat_activity` and audit logs if failures occur.

## 5. Cleanup

From the `postgres` maintenance database, after closing lab sessions and confirming the database is exclusively for this chapter, drop `ch053_lab` and then remove the three lab roles (`ch053_owner`, `ch053_tenant_a`, `ch053_tenant_b`). Do not use `DROP OWNED` or `REASSIGN OWNED` on shared databases.

**Acceptance:** both tenants pass all isolation assertions. **Runtime:** pending.
