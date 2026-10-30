# Chapter 051 — Security Architecture, Roles and Privilege Boundaries Lab

**Target:** Disposable PostgreSQL 18 database. **Status:** Authored; runtime validation pending.

**Safety update (V02-D):** Use the independently verified **Chapter 004 disposable PostgreSQL 18 primary** (127.0.0.1:55432, `lab_admin`), not the host's default PostgreSQL service. Before creating `ch051_lab`, verify the Chapter 004 `PG_LAB_ROOT/LAB_MARKER`, that the data directory is `$PG_LAB_ROOT/primary`, that this primary is not in recovery, and that the intended database and chapter roles do not already exist. Do not overwrite an occupied database or use a production/shared cluster. Set `PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"`, record the cluster system identifier with `SELECT system_identifier FROM pg_control_system();` and manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the commands below. The provision/event SQL refuses mismatches and runs its changes transactionally; independently review the connection and privileges before invoking the role/database creation commands. Follow the separate, reviewed cleanup only after all chapter-owned dependencies and sessions are verified. **Live negative tests pending.**

## Preflight

Use a dedicated lab database `ch051_lab`, created by a privileged lab administrator. Never run against production or a shared database. The lab scripts use fixed role names; verify they are absent before provisioning.

```powershell
psql -X -v ON_ERROR_STOP=1 -h localhost -h 127.0.0.1 -p 55432 -U lab_admin -d postgres -c "CREATE DATABASE ch051_lab"
psql -X -v ON_ERROR_STOP=1 -h localhost -h 127.0.0.1 -p 55432 -U lab_admin -d ch051_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_stage=051-PROVISION -f postgresql/labs/sql/051-provision.sql
psql -X -v ON_ERROR_STOP=1 -h localhost -h 127.0.0.1 -p 55432 -U lab_admin -d ch051_lab -f postgresql/labs/sql/051-verify.sql
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
