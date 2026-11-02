# Chapter 076 — Security Architecture, Roles and Privileges Lab

**PostgreSQL 18 · Disposable lab only · Runtime pending**

## 1. Safety

Run only in a disposable PostgreSQL 18 instance with a dedicated `ch076_lab` database. Creating roles requires elevated administration privileges. Do not execute the fixture against production or an existing shared database. Role names are cluster-wide; confirm no collisions.

## 2. Provision lab

As an authorized administrator, run the [fixture SQL](../labs/sql/076-security-role-fixture.sql) from the repository root:

```bash
# Run only after Chapter 004 lab owner verified PG_LAB_ROOT/LAB_MARKER,
# data_directory, system_identifier, unused ch076_ roles and database.
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -v expected_system_id=REPLACE_WITH_OBSERVED_SYSTEM_ID \
  -v "expected_lab_pgdata=$PG_LAB_ROOT/primary" \
  -v confirm_stage=076-CREATE-LAB-FIXTURE \
  -f postgresql/labs/sql/076-security-role-fixture.sql
```

The fixture first checks the observed PostgreSQL 18 system ID, localhost-only Chapter 004 primary, exact PGDATA, role, one-time token, unused database and cluster-wide roles. **These checks are not sufficient by themselves to authenticate that a host is disposable**; independently verify `LAB_MARKER` and root ownership before execution. An interruption can leave partially created cluster-wide roles; stop for operator review instead of rerunning or automatically deleting. The fixture creates a dedicated database, owner role, group roles, sample table and sequence, and narrowly scoped grants. It deliberately creates LOGIN roles **without passwords**; for actual login tests, set temporary secrets through a secret manager or use an approved local authentication method. Do not put credentials in Git.

## 3. Effective permission tests

Connect separately as each test identity (do not merely `SET ROLE` when testing LOGIN behavior):

- `ch076_app_login`: SELECT/INSERT/UPDATE/DELETE on `app.orders` should succeed; CREATE TABLE in `app` should fail.
- `ch076_analyst_login`: SELECT should succeed; INSERT, UPDATE and DELETE should fail.
- `ch076_monitor_login`: observe approved monitoring views; confirm no application write access.
- `ch076_owner`: NOLOGIN; use only through authorized migration context, not application sessions.

Run read-only [inspection SQL](../labs/sql/076-security-roles-and-privileges-inspect.sql) as an administrator.

## 4. Default privilege test

As the authorized owner context, create `app.future_orders` and verify inherited grants on the new table. Confirm future tables created by **another** role do not automatically receive `ch076_owner` defaults. Record current_user and session_user for each migration.

## 5. Negative tests

Verify runtime roles cannot CREATE in schema, ALTER or DROP owner objects, grant themselves additional roles, read unrelated schemas or use `SET ROLE` when the membership SET option is false. Test PUBLIC permissions and search_path using the inspection queries.

## 6. Acceptance and cleanup

Fill [scorecard](../labs/acceptance/076-security-access-scorecard.csv). Capture SQLSTATE for expected permission denials, not only error text.

After preserving evidence, remove the **disposable** database and roles using an explicit administrator-approved cleanup plan. Revoke memberships and clear owned objects/dependencies before DROP ROLE. Do not run broad `DROP OWNED` in shared databases.

**Disposable PostgreSQL 18 V03 evidence:** [Real runtime test](../validation/V03-CH076-078-DISPOSABLE-SECURITY-RUNTIME-EVIDENCE.md) verified the Chapter 076 guarded role setup, distinct database LOGIN sessions, CRUD permissions, analyst/monitor denials, default grants and forbidden `SET ROLE` cases as part of **69/69 checks PASS**. The harness uses a network-isolated Docker container with **trust authentication**; password-based authentication, TLS, a production-like credential store, and independent security acceptance remain **PENDING / NOT CERTIFIED**.

**Runtime:** pending; unexecuted permission tests are NOT VERIFIED.
