# Lab 014 — Credential Rotation and Service Account Lifecycle

**Audience:** DBRE/SRE. **Environment:** disposable Chapter 004 PostgreSQL 18 Linux lab.
**Duration:** 90–120 minutes. **PostgreSQL execution:** pending.

[Chapter](../chapters/014-secrets-rotation-and-service-account-lifecycle.md) · [Setup](004-reproducible-postgresql-operations-lab.md) · [Provisioning SQL](../scripts/014-provision-lab.sql) · [Access checks](../scripts/014-service-access-check.sql) · [Lifecycle inventory](../scripts/014-account-lifecycle-inspection.sql)

Use two interactive terminals. This creates only c014_db and five c014_* roles. It changes no original lab_app/admin/replication passwords or HBA rules. The isolated fixture is read-only to all three service identities.

The lab uses the original loopback SCRAM/no-TLS baseline after Chapter 013 cleanup. Production credential administration requires the verified protected transport from Chapter 013.

## 1. Guard and provision

Run from the repository's postgresql directory under the non-root lab OS account:

~~~bash
: "${PG_LAB_ROOT:?Export the Chapter 004 disposable lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable PGAPPNAME=chapter014-lab
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
c014_admin() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d c014_db "$@"
}
c014_login() {
  local role="$1"; shift
  case "$role" in c014_single|c014_blue|c014_green) ;; *) return 2;; esac
  psql -X -W -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U "$role" -d c014_db "$@"
}
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
lab_sql -f scripts/014-provision-lab.sql
~~~

Provisioning rejects occupied names. c014_owner owns the new database/schema/table; c014_reader grants schema USAGE and table SELECT. single/blue/green inherit reader with SET/ADMIN false, own no objects and have no powerful role attributes.

Set initial passwords interactively:

~~~bash
lab_sql
~~~

At psql:

~~~text
SET password_encryption = 'scram-sha-256';
\password c014_single
\password c014_blue
\password c014_green
\q
~~~

Use separate private disposable values. Refer to the initial single password as P1 and its replacement as P2 in your notes; do not write either value into the evidence. -W prompts through the terminal, including when SQL is supplied through a heredoc. Do not run this lab noninteractively.

## 2. Baseline real-login evidence

~~~bash
c014_login c014_single -f scripts/014-service-access-check.sql
c014_login c014_blue -f scripts/014-service-access-check.sql
c014_login c014_green -f scripts/014-service-access-check.sql
c014_admin -f scripts/014-account-lifecycle-inspection.sql
~~~

Expected: each login reads fixture ID 1, cannot INSERT (42501), cannot assume the owner (42501), and has the same reviewed access contract. Other failures do not count as a passing denial.

In Terminal A repeat only the environment/functions from step 1, open c014_single with P1, and leave it connected:

~~~bash
c014_login c014_single
~~~

At its prompt:

~~~sql
SELECT session_user,current_user,pg_backend_pid();
SELECT * FROM c014_data.probe;
~~~

## 3. Same-role replacement and rollback

Terminal B opens lab_sql interactively. Set SCRAM and use the password command to change c014_single to P2:

~~~text
SET password_encryption = 'scram-sha-256';
\password c014_single
\q
~~~

Attempt a **fresh** connection with c014_login c014_single and enter P1. Expected password-authentication failure. Repeat with P2 and the access script; expected success.

In Terminal A's already connected P1 session, SELECT * FROM c014_data.probe; still succeeds. Its connection does not prove P1 can authenticate again.

Rehearse rollback in this disposable lab: through lab_sql and the password command, restore P1. A fresh P1 login succeeds; a fresh P2 login fails. Retained sessions remain connected throughout.

This rollback is permitted only because the lab's P1 is known and uncompromised. Never restore a suspected compromised production credential. No secret-manager publication or application pool refresh is being executed here.

## 4. Password expiry does not end the existing session

Terminal B:

~~~bash
c014_admin -c "ALTER ROLE c014_single VALID UNTIL '2000-01-01 00:00:00+00';"
c014_admin -c "SELECT rolname,rolcanlogin,rolvaliduntil FROM pg_roles WHERE rolname='c014_single';"
~~~

Fresh c014_single login with P1 must fail. Confirm the past expiry and correlate protected server logs; the client may show a generic password-authentication error.

Terminal A's existing single connection still reads the fixture. Restore expiry and verify a new login:

~~~bash
c014_admin -c "ALTER ROLE c014_single VALID UNTIL 'infinity';"
c014_login c014_single -f scripts/014-service-access-check.sql
~~~

Close Terminal A's single session with \q.

## 5. Staged blue/green cutover

Both blue and green are valid during this bounded exercise overlap. Recheck their access probes and inventory; record the overlap start.

Terminal A opens the old identity with a dedicated application label:

~~~bash
PGAPPNAME=chapter014-blue-held c014_login c014_blue
~~~

Record pg_backend_pid() and leave the session idle outside a transaction. Terminal B verifies the replacement through a fresh login:

~~~bash
c014_login c014_green -f scripts/014-service-access-check.sql
c014_admin -f scripts/014-account-lifecycle-inspection.sql
~~~

Treat green as the selected consumer identity for the exercise. Production needs actual secret/config publication and every consumer class's reconnect evidence before this gate.

Disable blue admission without terminating its retained session:

~~~bash
c014_admin -c 'ALTER ROLE c014_blue NOLOGIN;'
~~~

A fresh blue login must fail for disabled login; inspect role state and server details, not merely the exit code. Terminal A's retained blue session still reads the fixture. This proves NOLOGIN is not session revocation.

Green's fresh access probe must continue passing.

## 6. Drain or terminate the identified old session

Normally close/drain old sessions deliberately. This lab demonstrates a targeted termination after replacement validation.

In Terminal B, enter the exact held blue PID recorded in Terminal A:

~~~bash
read -r -p 'Held Chapter 014 blue PID: ' HELD_BLUE_PID
[[ "$HELD_BLUE_PID" =~ ^[1-9][0-9]*$ ]] || exit 2
c014_admin -v held_pid="$HELD_BLUE_PID" <<'SQL'
SELECT pid,usename,datname,application_name,backend_start,state,xact_start
FROM pg_stat_activity
WHERE pid=:'held_pid'::integer AND usename='c014_blue'
  AND datname='c014_db' AND application_name='chapter014-blue-held'
  AND backend_type='client backend';
SQL
~~~

Require exactly the intended idle session with no active transaction. Record backend start and stop if the identity differs. The next command signals only that scoped idle backend:

~~~bash
c014_admin -v held_pid="$HELD_BLUE_PID" <<'SQL'
SET statement_timeout='10s';
SELECT pg_terminate_backend(pid,5000) AS terminated
FROM pg_stat_activity
WHERE pid=:'held_pid'::integer AND usename='c014_blue'
  AND datname='c014_db' AND application_name='chapter014-blue-held'
  AND backend_type='client backend' AND state='idle' AND xact_start IS NULL;
SQL
c014_admin -c "SELECT pid FROM pg_stat_activity WHERE usename='c014_blue';"
~~~

Expected one true termination result and no blue sessions. Zero matching rows is not a successful termination claim; reconcile whether the session already closed or no longer matches. A positive timeout result means termination completed within the wait, not just signal delivery.

Terminal A's old connection fails on its next command. Close it with \q. Do not let a client reconnect loop obscure retirement; blue NOLOGIN prevents its direct new login.

## 7. Revoke dependencies and retire blue

~~~bash
c014_admin -c 'ALTER ROLE c014_blue PASSWORD NULL;'
c014_admin -c 'REVOKE c014_reader FROM c014_blue;'
c014_admin -c 'REVOKE CONNECT ON DATABASE c014_db FROM c014_blue;'
c014_admin -f scripts/014-account-lifecycle-inspection.sql
~~~

Confirm blue owns no objects and has no remaining shared dependency rows. The dependency inventory reports database/catalog/OIDs; resolve other-database objects in their own database. Unknown references are a stop condition.

~~~bash
c014_admin -c 'DROP ROLE c014_blue;'
c014_login c014_green -f scripts/014-service-access-check.sql
bash scripts/004-operations-lab.sh verify
~~~

Expected role drop, green access and original topology/probe success. A dependency error must be investigated; do not use DROP OWNED or CASCADE to force retirement.

The point after clearing/destroying the old credential is a new rollback boundary. Re-enabling LOGIN alone would not recreate blue's password.

## 8. Acceptance and scoped cleanup

| Evidence | Required observation |
|---|---|
| Access contract | All service identities restricted to fixture reads |
| Same-role rotation | Old fresh password fails; replacement succeeds |
| Retained session | Continues after password change |
| Rollback | P1 restored consistently; P2 fresh auth fails |
| Expiry | Fresh auth fails while retained session works; expiry restored |
| Staged cutover | Green verified before blue disabled |
| NOLOGIN | New blue login denied; retained blue still works |
| Session retirement | Exact idle PID terminated or intentionally drained; none remain |
| Dependencies | Removed deliberately; blue role dropped |
| Original lab | Primary/two standbys and replication probe healthy |

Retain version, timestamps, role state, sanitized errors and observed outputs, without secret values/verifiers or session query text. Production secret-manager/pool adoption is outside this lab and remains a separate gate.

Close all c014_db sessions. Cleanup destroys only the exercise database and remaining dedicated roles:

~~~bash
lab_sql <<'SQL'
DO $guard$
BEGIN
  IF current_user <> 'lab_admin' OR current_database() <> 'ops_lab'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Wrong cleanup connection';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba
                 WHERE d.datname='c014_db' AND r.rolname='c014_owner') THEN
    RAISE EXCEPTION 'Unexpected/missing exercise database owner';
  END IF;
  IF EXISTS (SELECT FROM pg_stat_activity WHERE datname='c014_db') THEN
    RAISE EXCEPTION 'Close exercise database sessions before cleanup';
  END IF;
END
$guard$;
DROP DATABASE c014_db;
DROP ROLE IF EXISTS c014_blue;
DROP ROLE c014_single;
DROP ROLE c014_green;
DROP ROLE c014_reader;
DROP ROLE c014_owner;
SELECT rolname FROM pg_roles WHERE rolname IN
 ('c014_owner','c014_reader','c014_single','c014_blue','c014_green');
SELECT datname FROM pg_database WHERE datname='c014_db';
SQL
bash scripts/004-operations-lab.sh verify
~~~

Expected no dedicated names and original probe success. No FORCE drop or broad account termination is used. Partial setup/cleanup failures need inspected name-specific recovery; do not rerun provisioning over occupied names. Dispose of private lab password notes through the method used to retain them.
