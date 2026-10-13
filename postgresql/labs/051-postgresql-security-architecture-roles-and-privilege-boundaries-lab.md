# Chapter 051 — Security Architecture, Roles and Privilege Boundaries Lab

**Target:** Disposable PostgreSQL 18 database. **Status:** Authored; runtime validation pending.

## Preflight

Use a dedicated lab database `ch051_lab`, created by a privileged lab administrator. Never run against production or a shared database. The lab scripts use fixed role names; verify they are absent before provisioning.

```powershell
psql -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d postgres -c "CREATE DATABASE ch051_lab"
psql -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d ch051_lab -f postgresql/labs/sql/051-provision.sql
psql -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d ch051_lab -f postgresql/labs/sql/051-verify.sql
```

Use a local disposable PostgreSQL instance and secure credential handling. Do not embed passwords in scripts or commit them.

## Lab tasks

1. Inspect login vs NOLOGIN roles and memberships.
2. Verify `ch051_reader` has SELECT but no INSERT, UPDATE, DELETE or CREATE on the lab schema.
3. Verify `ch051_writer` can SELECT/INSERT/UPDATE/DELETE but cannot create tables or drop owner tables.
4. Verify new owner-created tables receive the intended default privileges.
5. Verify application roles have neither SUPERUSER nor BYPASSRLS.
6. Review `\dp ch051.*` and `\ddp` output.

The verification SQL uses `has_*_privilege` and produces PASS/FAIL columns. These checks are metadata assertions; also conduct connection tests as separate low-privilege identities if passwords/identity switching are configured. A superuser's successful query does not prove application access.

## Expected negative tests

Connect as `ch051_reader` in the isolated lab (using separately configured credentials) and attempt INSERT into `ch051.events`; expect `permission denied`. Connect as `ch051_writer` and attempt CREATE TABLE in `ch051`; expect `permission denied`. Avoid changing role passwords in committed SQL.

## Cleanup

**Only if the database is disposable and dedicated to Chapter 051:** drop the entire lab database from a separate `postgres` connection after disconnecting lab sessions, then drop the lab roles after confirming no remaining dependencies. Do not run `DROP OWNED` or `REASSIGN OWNED` on a shared database.

## Acceptance

Record PostgreSQL version, role ACLs, default privilege ACLs, positive/negative tests, expected errors, and operator signoff. **Runtime execution pending.**
