# Lab 012 — HBA, Authentication and Connection Diagnosis

**Audience:** DBRE/SRE. **Baseline:** Chapter 004 PostgreSQL 18 Linux lab.
**Duration:** 75–100 minutes. **Runtime verification:** pending.

[Chapter](../chapters/012-pg-hba-conf-authentication-and-connection-diagnosis.md) · [Lab setup](004-reproducible-postgresql-operations-lab.md) · [HBA staging helper](../scripts/012-hba-lab.py) · [Inspection SQL](../scripts/012-authentication-inspection.sql)

Use two terminals under the non-root lab OS account. This lab stages a narrow app rejection and a malformed HBA file on the disposable primary. It never sets trust, changes passwords, opens remote listening addresses or promotes standbys. The helper modifies disk only; SQL/pg_ctl reloads are separate explicit steps.

## 1. Guard and prepare in Terminal B

Export the existing PG_LAB_ROOT and run from the repository's postgresql directory. Recreate Chapter 004 if the transient lab disappeared.

~~~bash
: "${PG_LAB_ROOT:?Export the disposable Chapter 004 lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGAPPNAME=chapter012-lab
export PGGSSENCMODE=disable
umask 077
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
app_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW hba_file')" == "$PG_LAB_ROOT/primary/pg_hba.conf" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
python3 scripts/012-hba-lab.py prepare
~~~

Prepare requires the exact three-rule Chapter 004 HBA baseline and a fresh evidence-012 directory. It refuses unexplained changes. It saves the original HBA and creates private empty/wrong/socket password files without printing credentials.

No other configuration writer may operate during this exercise. The helper detects unknown file contents and checks for an intervening edit, but it is not a lock shared by PostgreSQL/configuration management. Keep exclusive ownership of this lab session.

Record baseline inspection:

~~~bash
lab_sql -f scripts/012-authentication-inspection.sql \
  > "$PG_LAB_ROOT/evidence-012/baseline.txt"
app_sql -c 'SELECT current_user,current_database(),inet_client_addr(),inet_server_port();'
~~~

Expected lab_app, ops_lab, client 127.0.0.1 and port 55432. Require no HBA parse errors.

In Terminal A, repeat the connection environment setup, then open and keep a successful app session:

~~~bash
psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
~~~

Also keep a verified administrator session available if desired. Retain OS access to the lab root in case fresh SQL access fails.

## 2. Compare TCP and Unix socket paths

Terminal B:

~~~bash
PGPASSFILE="$PG_LAB_ROOT/evidence-012/socket.pgpass" \
  psql -X -w -v ON_ERROR_STOP=1 -h "$PG_LAB_ROOT/socket" -p 55432 \
  -U lab_app -d ops_lab \
  -c 'SELECT current_user,inet_client_addr(),inet_server_addr();'
~~~

Expected successful lab_app authentication, with NULL network addresses for the Unix socket. The first local rule applies; the TCP host rule does not. The helper supplied a password-file entry for this explicit nondefault socket directory because the original IPv4 entry is not the socket lookup match.

The baseline deliberately uses SCRAM for both transports. Do not change local authentication to peer during this exercise.

## 3. Missing credential and wrong credential are different failures

Run these in Terminal B; expected failure branches keep the exercise progressing without accepting any arbitrary error as success:

~~~bash
if PGPASSFILE="$PG_LAB_ROOT/evidence-012/empty.pgpass" app_sql \
  -c 'SELECT 1;' > "$PG_LAB_ROOT/evidence-012/no-password.txt" 2>&1; then
  echo 'Unexpected success: stop and investigate the credential/method source.'
else
  echo 'Connection failed; inspect no-password.txt for the missing-password cause.'
fi
if PGPASSFILE="$PG_LAB_ROOT/evidence-012/wrong.pgpass" app_sql \
  -c 'SELECT 1;' > "$PG_LAB_ROOT/evidence-012/wrong-password.txt" 2>&1; then
  echo 'Unexpected success: stop and investigate.'
else
  echo 'Connection failed; inspect wrong-password.txt for password authentication failure.'
fi
app_sql -c 'SELECT 1;'
~~~

Expected: the first failure indicates no supplied password under -w; the second indicates password authentication failed; the original passfile succeeds. Compare timestamps with the protected primary log. A generic nonzero exit, refused port, wrong database or syntax error does not satisfy these checks.

No real credential was rotated. Do not paste the password files into evidence or enable shell tracing around secrets.

## 4. First-match rejection and existing-session behavior

Stage a rule before the original broad host allow:

~~~bash
python3 scripts/012-hba-lab.py reject
lab_sql -f scripts/012-authentication-inspection.sql \
  > "$PG_LAB_ROOT/evidence-012/reject-on-disk.txt"
lab_sql -c 'SELECT pg_reload_conf();'
~~~

Expected staged first rule:

~~~text
hostnossl ops_lab lab_app 127.0.0.1/32 reject
~~~

Require no file parse error. Within a bounded ten-second observation window, attempt fresh app connections:

~~~bash
if app_sql -c 'SELECT 1;' > "$PG_LAB_ROOT/evidence-012/rejected.txt" 2>&1; then
  echo 'Not yet rejected: check reload/logs and retry within the observation window.'
else
  echo 'Inspect rejected.txt: require an explicit HBA rejection for this connection tuple.'
fi
pg_isready -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab -t 5
lab_sql -c 'SELECT 1;'
~~~

Expected fresh app rejection even though the later original host rule allows SCRAM. No fallthrough occurs. pg_isready can still report accepting connections; the admin connection succeeds because the reject targets only lab_app/ops_lab.

In Terminal A's already connected app session:

~~~sql
SELECT current_user,1 AS existing_session_still_usable;
~~~

Expected success. HBA reload did not disconnect it. This is why a retained pool connection cannot prove that new connections work.

Restore and prove fresh app admission:

~~~bash
python3 scripts/012-hba-lab.py restore
lab_sql -c 'SELECT pg_reload_conf();'
app_sql -c 'SELECT current_user;'
~~~

Allow a bounded reload observation window. Require successful fresh admission before moving on.

## 5. Malformed disk rules and a failed reload

This step intentionally reloads an invalid file **only in this guarded disposable lab**. In production, stop at the parse error and restore valid contents.

~~~bash
python3 scripts/012-hba-lab.py malformed
lab_sql -f scripts/012-authentication-inspection.sql \
  > "$PG_LAB_ROOT/evidence-012/malformed-on-disk.txt"
lab_sql -c 'SELECT count(*) AS parse_errors FROM pg_hba_file_rules WHERE error IS NOT NULL;'
~~~

Expected at least one parse error for not_an_auth_method. Record its file/line/error. No valid policy should be approved from this file.

Now deliberately demonstrate signal versus acceptance:

~~~bash
lab_sql -c 'SELECT pg_reload_conf();'
tail -n 60 "$PG_LAB_ROOT/logs/primary.log"
app_sql -c 'SELECT current_user,1;'
~~~

Expected: reload signal delivery, a server log error/failure loading HBA, and successful app authentication using the prior valid loaded policy. Wait up to ten seconds for the log evidence. If the log has not shown the failed reload, a successful connection alone does not prove retention.

Do not restart while the file is malformed. Restore immediately:

~~~bash
python3 scripts/012-hba-lab.py restore
lab_sql -c 'SELECT pg_reload_conf();'
lab_sql -c 'SELECT count(*) AS parse_errors FROM pg_hba_file_rules WHERE error IS NOT NULL;'
app_sql -c 'SELECT 1;'
python3 scripts/012-hba-lab.py status
~~~

Expected zero parse errors, successful fresh app connection and disk state original. Verify reload completion in logs; a disk hash does not prove loaded-policy restoration.

## 6. Classify authorization separately

The original lab_app can read public.lab_probe but does not have DELETE. Test through its real login:

~~~bash
app_sql <<'SQL'
DO $check$
BEGIN
  BEGIN
    EXECUTE 'DELETE FROM public.lab_probe WHERE false';
  EXCEPTION WHEN insufficient_privilege THEN
    RAISE NOTICE 'PASS: authenticated, but DELETE denied (42501)'; RETURN;
  END;
  RAISE EXCEPTION 'FAIL: DELETE unexpectedly allowed';
END
$check$;
SQL
~~~

Expected 42501 after successful authentication. Do not change HBA or passwords to repair an object privilege. The WHERE false probe deletes no rows even if access is unexpectedly broader; the script then fails.

## 7. Restoration, replication reconnect and evidence

Close Terminal A's app session with \q. Confirm the original HBA is restored and loaded before reconnecting the entire disposable topology:

~~~bash
python3 scripts/012-hba-lab.py status
lab_sql -f scripts/012-authentication-inspection.sql \
  > "$PG_LAB_ROOT/evidence-012/final.txt"
bash scripts/004-operations-lab.sh stop
bash scripts/004-operations-lab.sh start
app_sql -c 'SELECT current_user,current_database();'
~~~

Use the Chapter 009 timeout procedure if any lifecycle command fails. The stop/start sequence intentionally interrupts this disposable lab; it verifies new standby replication connections rather than merely observing old streaming sessions. The start helper verifies the primary, two recovering standbys and a replicated probe.

Acceptance report:

| Evidence | Required observation |
|---|---|
| Baseline | Correct primary/HBA path; no parse errors |
| TCP/socket | Both SCRAM logins work through distinct transport rules |
| Empty passfile | Missing-password failure |
| Wrong passfile | Password-authentication failure |
| Rejection | First matching reject wins over later allow |
| Readiness | pg_isready distinguished from authenticated success |
| Existing session | Remains usable across HBA policy reload |
| Malformed reload | Disk parse error, server reload failure, old valid policy retained |
| Authorization | Authenticated login; forbidden DELETE yields 42501 |
| Restoration | Original disk file, successful reload and fresh SQL |
| Reconnect | Primary and two standbys return; replication probe passes |

Finally remove copied/probe credential files:

~~~bash
python3 scripts/012-hba-lab.py clean-secrets
~~~

Retain sanitized error outputs and configuration evidence, not password files. Keep the lab for Chapter 013 or use Chapter 004's guarded stop/destroy procedure.

## 8. If interrupted mid-exercise

Use the known backup and helper to restore disk, then reload through the OS owner if SQL is unavailable:

~~~bash
python3 scripts/012-hba-lab.py restore
pg_ctl -D "$PG_LAB_ROOT/primary" reload
~~~

Execute this only with the guarded lab identity and data directory. If the helper refuses unknown contents, inspect the unexpected edit; do not override its guard or blindly overwrite another writer's work. Reload while the server is running, verify logs/fresh connections, and only then proceed to lifecycle operations.
