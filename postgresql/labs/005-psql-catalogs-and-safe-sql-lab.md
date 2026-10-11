# Lab 005 — psql, Catalogs and Safe Administrative SQL

[Chapter 005](../chapters/005-psql-system-catalogs-and-safe-administrative-sql.md) · [Inspection script](../scripts/005-safe-catalog-inspection.sql)

## Objective and prerequisites

Use the running Chapter 004 primary and ops_lab database to inspect metadata and rehearse safe SQL behavior. Reference PostgreSQL 18; record exact versions.

Use lab_observer for monitoring and lab_app for table access. The lab_admin role is not needed for these exercises. Passwords remain in the protected Chapter 004 password file.

The rollback exercise writes only an uncommitted row to the lab fixture. It belongs in the disposable environment, not production.

## 1. Establish the connection

With your actual PG_LAB_ROOT exported:

~~~bash
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5
export PGAPPNAME=chapter005-lab
mkdir -p evidence/chapter005
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab
~~~

Inside psql:

~~~sql
\conninfo
SELECT current_database(), current_user, inet_server_port(), pg_is_in_recovery();
\pset pager off
\x auto
\timing on
\dn
\dt public.*
\d public.lab_probe
~~~

Expected: ops_lab, lab_observer, port 55432 and false for recovery. Object descriptions should show the Chapter 004 fixture.

Close with backslash-q before shell commands.

## 2. Run a bounded metadata script

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -v schema_name=public \
  -f postgresql/scripts/005-safe-catalog-inspection.sql \
  > evidence/chapter005/catalogs.txt \
  2> evidence/chapter005/catalogs-errors.txt
echo $?
~~~

Expected: exit 0, identity plus catalog results, transaction COMMIT and no SQL error in stderr.

The script defaults to public if schema_name is not provided. Its read-only transaction has local statement/lock timeouts and a trusted catalog search_path.

Compare pg_class results with information_schema.tables. The observer can see public.lab_probe's catalog entry, but normally lacks application-table rights. Information schema may therefore omit it.

To prove the access boundary, run this deliberately failing check:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -c "SELECT * FROM public.lab_probe LIMIT 1;"
echo $?
~~~

Expected with the unmodified Chapter 004 grants: permission error and nonzero status. Do not grant extra rights to make this observer query pass.

## 3. Test literal and identifier quoting

From the shell, use an application login:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab \
  -v sample="O'Reilly" -v schema_name=public <<'SQL'
SELECT :'sample' AS safely_quoted_value;
SELECT count(*) FROM :"schema_name".lab_probe;
SQL
~~~

Expected: the literal O'Reilly intact and a valid count from public.lab_probe. Single-quote variable interpolation represents a value; double-quote interpolation represents an identifier. The quoted heredoc prevents shell expansion of the SQL.

Correct quoting does not replace authorization or target verification.

## 4. Demonstrate read-only rejection interactively

Connect as lab_app:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
~~~

Run these commands **one at a time**, checking each response:

~~~sql
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT current_database(), current_user;
INSERT INTO public.lab_probe(id,payload) VALUES (5005,'must-not-write');
ROLLBACK;
~~~

Expected: the INSERT is rejected because the transaction is read-only. In interactive mode, ON_ERROR_STOP returns control to the prompt; issue ROLLBACK to clear the failed transaction.

Confirm:

~~~sql
SHOW transaction_read_only;
SELECT count(*) FROM public.lab_probe WHERE id=5005;
~~~

Expected on this primary: off and 0 for the unused exercise ID. If id 5005 already existed before the lab, use another verified-unused ID consistently; never delete someone else's row.

## 5. Rehearse a normal write followed by rollback

First ensure the selected exercise ID is absent. In the same application session:

~~~sql
SELECT count(*) FROM public.lab_probe WHERE id=5005;
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
INSERT INTO public.lab_probe(id,payload) VALUES (5005,'rollback-demo');
SELECT id,payload FROM public.lab_probe WHERE id=5005;
ROLLBACK;
SELECT count(*) FROM public.lab_probe WHERE id=5005;
~~~

Expected: before count 0, row visible to your transaction after INSERT, after count 0.

Rollback restores the logical outcome for this row; it does not promise zero WAL generation or immediate reversal of all physical storage effects. External side effects and other SQL operations need their own analysis.

Close the session with backslash-q. Do not leave it idle in transaction.

## 6. Demonstrate script failure handling

Create a small deliberate error script:

~~~bash
cat > evidence/chapter005/expected-error.sql <<'SQL'
SELECT 1 / 0 AS deliberate_failure;
SELECT 'must-not-run' AS unexpected_continuation;
SQL

if psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -f evidence/chapter005/expected-error.sql \
  > evidence/chapter005/error-test-out.txt \
  2> evidence/chapter005/error-test-err.txt; then
  echo "FAIL: expected a script error"
else
  status=$?
  printf 'Observed psql failure status: %s\n' "$status"
fi
~~~

Expected: division-by-zero error, script failure status 3 and no result for must-not-run. The shell conditional is necessary because this failure is intentional.

Do not generalize this into rollback of previously committed commands. This particular script contains no writes.

## 7. Export one catalog dataset

~~~bash
psql -X -w --csv -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -c "SELECT extname,extversion FROM pg_catalog.pg_extension ORDER BY extname;" \
  > evidence/chapter005/extensions.csv
echo $?
~~~

Expected: status 0, one CSV header and extension rows. This file is on the client, not the server. Retain stderr separately if your workflow requires it.

## 8. Cleanup and acceptance

All exercise transactions must end. No grants, persistent settings or committed application rows should change. Keep the evidence files but review endpoint/role metadata before sharing. Restore shell connection settings introduced for the lab.

| Check | Pass condition |
|---|---|
| Identity | Correct endpoint, database, role and primary state |
| Metadata | Catalog inventory succeeds with bounded timeouts |
| Visibility | Observer metadata access distinguished from application data access |
| Quoting | Apostrophe value and schema identifier handled correctly |
| Read-only | Write rejected and failed transaction cleared |
| Rollback | Temporary exercise row absent after rollback |
| Error handling | Script stops at intentional error; caller sees failure |
| Export | Single valid catalog CSV dataset |
| Cleanup | No open transaction, new grants or persistent setting change |
| Evidence | Actual versions, outputs and limitations recorded |

**Troubleshooting:** hidden metadata → check role/view semantics; syntax error on colon-variable → use psql stdin/file, not a driver or mixed -c; transaction-aborted error → ROLLBACK; empty CSV → check status and privileges; unexpected row/endpoint → stop and reconcile lab state.

The chapter is authored independently of actual lab execution. Mark verified only when these checks run successfully.
