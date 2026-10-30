# Chapter 053 — Row-Level Security and Secure Application Access Lab

**PostgreSQL 18 · Dedicated disposable database · Runtime validation pending.**

**Safety update (V02-D):** Use the independently verified **Chapter 004 disposable PostgreSQL 18 primary** (127.0.0.1:55432, `lab_admin`), not the host's default PostgreSQL service. Before creating `ch053_lab`, verify the Chapter 004 `PG_LAB_ROOT/LAB_MARKER`, that the data directory is `$PG_LAB_ROOT/primary`, that this primary is not in recovery, and that the intended database and chapter roles do not already exist. Do not overwrite an occupied database or use a production/shared cluster. Set `PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"`, record the cluster system identifier with `SELECT system_identifier FROM pg_control_system();` and manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the commands below. The provision/event SQL refuses mismatches and runs its changes transactionally; independently review the connection and privileges before invoking the role/database creation commands. Follow the separate, reviewed cleanup only after all chapter-owned dependencies and sessions are verified. **Live negative tests pending.**

## 1. Safety and setup

Use a **new isolated** PostgreSQL database named `ch053_lab`, accessed by a lab administrator. Confirm the five lab roles are not in use anywhere else on the server. Never run against production. The test switches session authorization to simulate real tenant identities; use an authorized superuser in this disposable environment.

```powershell
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d postgres -c "CREATE DATABASE ch053_lab"
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ch053_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_stage=053-PROVISION -f postgresql/labs/sql/053-provision.sql
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ch053_lab -f postgresql/labs/sql/053-verify.sql
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
