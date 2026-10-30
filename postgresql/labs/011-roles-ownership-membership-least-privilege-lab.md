# Lab 011 — Roles, Ownership, Membership and Least Privilege

**Audience:** DBRE/SRE. **Environment:** disposable Chapter 004 PostgreSQL 18 primary and two standbys.
**Duration:** 90–120 minutes. **Runtime verification:** pending.

[Chapter](../chapters/011-roles-ownership-membership-and-least-privilege.md) · [Existing lab setup](004-reproducible-postgresql-operations-lab.md) · [Provisioning SQL](../scripts/011-provision-lab.sql) · [Runtime acceptance SQL](../scripts/011-runtime-acceptance.sql) · [Inventory SQL](../scripts/011-role-access-inspection.sql)

This exercise creates only c011_db and five c011_* roles. It does not grant the existing lab_app additional authority or change ops_lab's ACLs. Role/database creation is replicated by the existing physical standbys. Perform all changes on the primary.

## 1. Guard and preflight

Run from the repository's postgresql directory under the non-root lab OS account. Export the existing PG_LAB_ROOT printed by Chapter 004; recreate that lab if its transient directory disappeared.

~~~bash
: "${PG_LAB_ROOT:?Export the disposable Chapter 004 lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGAPPNAME=chapter011-lab
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U lab_admin -d ops_lab "$@"
}
c011_admin() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U lab_admin -d c011_db "$@"
}
c011_runtime() {
  psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U c011_runtime -d c011_db "$@"
}
c011_deploy() {
  psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
    -U c011_deploy -d c011_db "$@"
}
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
~~~

The two restricted functions deliberately prompt for their own passwords on every connection. Do not place passwords in commands, SQL examples or evidence. -W prompts interactively; run these commands at a real terminal, not a noninteractive CI job.

Provisioning rejects occupied names. If a previous attempt left partial objects, inspect them and use the scoped cleanup below after verifying their identity; do not overwrite or adopt them silently.

## 2. Provision the access contract

~~~bash
lab_sql -f scripts/011-provision-lab.sql
~~~

The script creates:

| Role | Login | Membership/authority |
|---|---|---|
| c011_owner | No | Owns c011_db, c011_data and fixtures |
| c011_reader | No | Schema USAGE and table SELECT |
| c011_writer | No | Inherits reader; table INSERT/UPDATE; sequence USAGE |
| c011_runtime | Yes | Inherits writer; cannot SET ROLE to writer or owner |
| c011_deploy | Yes | No inherited owner authority; explicit SET ROLE owner allowed |

All five roles have no superuser, database-creation, role-creation, replication or RLS-bypass attribute. The dedicated database removes PUBLIC CONNECT/TEMPORARY and grants CONNECT only to the two new logins and the existing observer. lab_admin retains its existing superuser access.

Set passwords interactively using the existing administrator:

~~~bash
lab_sql
~~~

At the psql prompt:

~~~text
SET password_encryption = 'scram-sha-256';
\password c011_runtime
\password c011_deploy
\q
~~~

Enter separate disposable passwords when prompted, and retain them privately for this session. No password appears in the provisioning file. A role was created without a password until this step; that is not evidence of a working login.

Collect the bounded inventory through the observer:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
  -U lab_observer -d c011_db -f scripts/011-role-access-inspection.sql
~~~

Retain membership options, owners, default ACLs and effective privilege matrices. Do not read pg_authid/password verifier fields.

## 3. Positive and negative runtime acceptance

~~~bash
c011_runtime -f scripts/011-runtime-acceptance.sql
~~~

Enter the runtime password. Expected: real session_user/current_user both c011_runtime; SELECT, INSERT RETURNING and UPDATE RETURNING succeed; seven negative tests report PASS with SQLSTATE 42501:

- DELETE.
- TRUNCATE.
- CREATE in the application schema.
- ALTER of the owner table.
- SET ROLE to the owner.
- SET ROLE to the writer despite inherited writer privileges.
- Delegating writer membership to the deployment identity.

The script wraps probes in a transaction and rolls back ordinary writes. Sequence values can advance despite rollback; a missing number is not a privilege failure.

Every negative block catches only insufficient_privilege. Other errors fail the script. If a forbidden operation succeeds, the script raises an exception; the transaction aborts and the connection closes without committing its changes. Do not mark a failed authentication attempt as a passing negative test.

## 4. Explicit migration identity and future-object grants

Connect through the actual migration login:

~~~bash
c011_deploy
~~~

First establish identity and the membership distinction:

~~~sql
SELECT session_user,current_user;
SELECT pg_has_role(current_user,'c011_owner','MEMBER') AS member,
       pg_has_role(current_user,'c011_owner','USAGE') AS inherited_owner,
       pg_has_role(current_user,'c011_owner','SET') AS may_assume_owner;
~~~

Expected: member true, inherited_owner false, may_assume_owner true.

As an intentionally forbidden operation:

~~~sql
SELECT * FROM c011_data.jobs;
~~~

Expected SQLSTATE 42501 (usually schema permission denied). Because this interactive connection uses ON_ERROR_STOP, psql returns to its prompt after the error; it is outside a transaction. Do not execute this expected error inside an unhandled script.

Explicitly assume the owner and create the next fixture:

~~~sql
SET ROLE c011_owner;
SELECT session_user,current_user;
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
CREATE TABLE c011_data.future_jobs(id bigserial PRIMARY KEY,payload text NOT NULL);
INSERT INTO c011_data.future_jobs(payload) VALUES ('future-owner-fixture');
COMMIT;
RESET ROLE;
\q
~~~

Expected: while switched, session_user remains c011_deploy and current_user is c011_owner. The table and sequence owner are c011_owner. Repeat the inventory to verify owner and defaults.

Test the future table through runtime:

~~~bash
c011_runtime <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT id,payload FROM c011_data.future_jobs;
INSERT INTO c011_data.future_jobs(payload) VALUES ('future-runtime-rollback') RETURNING id;
ROLLBACK;
SQL
~~~

Expected: read and insert succeed without a manual GRANT for this new table. Table and sequence defaults both mattered. No owner membership was given to runtime.

## 5. Creator drift: ownership transfer does not replay defaults

Create an intentionally wrong-creator fixture as lab_admin:

~~~bash
c011_admin <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
CREATE TABLE c011_data.creator_drift(id integer PRIMARY KEY,payload text NOT NULL);
INSERT INTO c011_data.creator_drift VALUES (1,'creator-drift-fixture');
ALTER TABLE c011_data.creator_drift OWNER TO c011_owner;
COMMIT;
SELECT has_table_privilege('c011_runtime','c011_data.creator_drift','SELECT')
       AS runtime_select_after_owner_transfer;
SQL
~~~

Expected false: changing the owner did not apply that role's future-object ACL policy.

Prove the actual denial:

~~~bash
c011_runtime <<'SQL'
DO $check$
BEGIN
  BEGIN
    PERFORM payload FROM c011_data.creator_drift;
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: wrong-creator table denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: wrong-creator table unexpectedly readable';
END
$check$;
SQL
~~~

Repair the existing table's explicit ACL as its owner, without changing the runtime's membership:

~~~bash
c011_admin <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SET LOCAL ROLE c011_owner;
GRANT SELECT ON c011_data.creator_drift TO c011_reader;
GRANT INSERT,UPDATE ON c011_data.creator_drift TO c011_writer;
COMMIT;
SQL
c011_runtime -c 'SELECT id,payload FROM c011_data.creator_drift;'
~~~

Expected successful read. The process correction is still to create future application objects as c011_owner; the existing-object repair alone does not fix a migration tool's identity.

## 6. Revoke, prove denial, restore the exact membership

Remove just this exercise's runtime membership:

~~~bash
c011_admin -c 'REVOKE c011_writer FROM c011_runtime;'
~~~

Use a fresh runtime session and catch only the expected denial:

~~~bash
c011_runtime <<'SQL'
DO $check$
BEGIN
  BEGIN
    PERFORM payload FROM c011_data.jobs;
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: runtime access removed (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: another privilege path still allows access';
END
$check$;
SQL
~~~

The runtime can still authenticate/connect through its explicit database grant, but loses schema/table access through writer → reader. This is different from disabling login.

Restore the precise original edge:

~~~bash
c011_admin -c 'GRANT c011_writer TO c011_runtime WITH INHERIT TRUE, SET FALSE, ADMIN FALSE;'
c011_runtime -f scripts/011-runtime-acceptance.sql
bash scripts/004-operations-lab.sh verify
~~~

Expected: all runtime checks pass again and the original three-node topology remains healthy.

## 7. Acceptance evidence

| Evidence | Required result |
|---|---|
| Version/endpoint | PG18, correct disposable primary |
| Runtime/deploy logins | Real authentication with separate credentials |
| Powerful role attributes | False for all five new roles |
| Membership graph | Exactly the intended three edges/options |
| Object ownership | c011_owner for intended schema, tables and sequences |
| Existing-table runtime probes | SELECT/INSERT/UPDATE succeed |
| Seven forbidden operations | SQLSTATE 42501, no unexpected success |
| Future-table probes | Access supplied by creator-scoped defaults |
| Creator drift | Owner transfer alone fails; explicit ACL repair works |
| Membership revoke/restore | Fresh-session denial, then restored probes |
| Original lab | One primary, two standbys, successful replication probe |
| Cleanup | Dedicated database and all five roles absent |

Retain actual commands, output, timestamps and unexpected differences. This does not verify HBA alternatives, TLS, RLS or security-definer functions. Execution remains pending until this lab is run.

## 8. Scoped cleanup

Close every c011_runtime/c011_deploy/observer session connected to c011_db. This cleanup intentionally destroys only the exercise's dedicated database and its fixtures. Preserve sanitized evidence first.

Run from ops_lab as lab_admin:

From the guarded Chapter 004 primary, record the exact cluster identifier using `lab_sql -Atc 'SELECT system_identifier FROM pg_control_system();'`, compare it with the lab's instance identity and independently verify `SHOW data_directory`, ownership of `c011_db`, expected roles and absence of sessions. The cleanup script refuses mismatched identity and requires a chapter-specific approval token. **Replace the placeholder manually and never run this on production or shared staging.**

~~~bash
lab_sql -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID \
  -v confirm_cleanup=011-DROP-ROLES-DB \
  -f scripts/011-cleanup-lab.sql
bash scripts/004-operations-lab.sh verify
~~~

Expected: no remaining names, and original topology/probe pass. No FORCE database drop, DROP OWNED or CASCADE is used. If DROP ROLE reports another dependency, inspect it; do not widen deletion scope. A partial provisioning failure before the database existed needs an inspected, name-specific cleanup of only the roles actually created.
