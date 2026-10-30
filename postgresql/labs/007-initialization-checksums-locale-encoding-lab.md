# Lab 007 — Initialization, Checksums, Locale and Encoding

[Chapter 007](../chapters/007-initialization-checksums-locale-and-encoding.md) · [Inventory SQL](../scripts/007-initialization-inventory.sql)

## Objective and boundaries

Initialize a fresh **offline** PostgreSQL 18 cluster, check its checksums and compare database text settings on the separate Chapter 004 primary.

Required: matching-major initdb, pg_controldata, pg_checksums and psql; Bash/Python 3; a non-root OS user; the running Chapter 004 lab and its administrative login.

Do not run pg_checksums against the running Chapter 004 data directory. Do not enable/disable checksums, alter libraries or corrupt files.

## 1. Record prerequisites

~~~bash
id
initdb --version
pg_controldata --version
pg_checksums --version
psql --version
locale -a
~~~

Expected: non-root account, PostgreSQL major 18 tools and an OS locale inventory. ICU/builtin locale choices are not fully represented by locale -a.

Record exact versions in evidence/chapter007/acceptance.md:

~~~bash
mkdir -p evidence/chapter007
~~~

## 2. Create the isolated initialization target

Use a fresh terminal or save any existing PG_INIT_LAB_ROOT first. Never point this variable at an existing cluster:

~~~bash
umask 077
PG_INIT_LAB_ROOT="$(mktemp -d /tmp/postgresql-init-lab.XXXXXXXX)"
export PG_INIT_LAB_ROOT
printf '%s\n' "chapter007-offline-disposable" > "$PG_INIT_LAB_ROOT/LAB_MARKER"
printf 'Offline lab root: %s\n' "$PG_INIT_LAB_ROOT"

initdb -D "$PG_INIT_LAB_ROOT/data" \
  -U init_lab_admin --pwprompt \
  --auth-local=scram-sha-256 --auth-host=scram-sha-256 \
  --encoding=UTF8 --locale-provider=libc --locale=C \
  --data-checksums
~~~

Choose a lab-only password at the prompts. It is not used further because this cluster is not started. Keep initialization output without the password.

Expected: UTF8, libc/C, checksums enabled and successful initialization. If initdb fails, retain the root for diagnosis and do not mark this step passed.

No server startup, new listener or standby attachment is needed.

## 3. Verify checksums offline

~~~bash
pg_controldata "$PG_INIT_LAB_ROOT/data"
pg_checksums --check -D "$PG_INIT_LAB_ROOT/data"
echo $?
~~~

Expected: a cleanly shut-down cluster state, enabled checksum metadata, zero bad checksums and exit status 0.

The offline scan reads data; it does not demonstrate that a backup can restore it. Do not scan another cluster merely because this one passes.

If the check fails, preserve the error and stop. Do not alter pages or disable detection.

## 4. Inspect the existing primary's defaults

Use the **separate Chapter 004** PG_LAB_ROOT, not PG_INIT_LAB_ROOT:

~~~bash
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5
export PGAPPNAME=chapter007-inspection

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -f postgresql/scripts/007-initialization-inventory.sql \
  > evidence/chapter007/inventory-before.txt
echo $?
~~~

Expected: successful inventory with UTF8 and checksums on for the unmodified Chapter 004 primary. Save its provider/locale metadata.

## 5. Create comparison databases

Precheck as the authorized lab administrator:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -c "SELECT datname FROM pg_catalog.pg_database
      WHERE datname IN ('chapter007_libc','chapter007_builtin');"
~~~

Proceed only if neither name exists and this is the disposable primary. Do not drop an existing database to clear a conflict.

Run each CREATE DATABASE as a separate command:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -c "CREATE DATABASE chapter007_libc
      TEMPLATE template0 ENCODING 'UTF8'
      LOCALE_PROVIDER libc LOCALE 'C';"

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -c "CREATE DATABASE chapter007_builtin
      TEMPLATE template0 ENCODING 'UTF8'
      LOCALE_PROVIDER builtin LOCALE 'C'
      BUILTIN_LOCALE 'PG_UNICODE_FAST';"
~~~

Expected: both created. Do not use --single-transaction for this step. If the second creation fails, record the partial result and clean up only the database created by this run.

Repeat the inventory script and save inventory-after.txt. Expect both database rows with UTF8, distinct provider codes and builtin metadata identifying PG_UNICODE_FAST. Null version metadata can be legitimate.

## 6. Compare text behavior

For each database, execute the same queries:

~~~bash
for db in chapter007_libc chapter007_builtin; do
  psql -X -w -v ON_ERROR_STOP=1 \
    -h 127.0.0.1 -p 55432 -U lab_admin -d "$db" <<'SQL'
SHOW server_encoding;
SHOW client_encoding;
SELECT txt, upper(txt) AS uppercase
FROM (VALUES ('a'),('A'),(U&'\00E9'),(U&'\00DF')) AS sample(txt)
ORDER BY txt;
SELECT length(U&'\20AC') AS character_count,
       octet_length(U&'\20AC') AS byte_count,
       encode(convert_to(U&'\20AC','UTF8'),'hex') AS utf8_hex;
SQL
done
~~~

Expected in UTF8: euro character_count 1, byte_count 3 and utf8_hex e282ac. Record actual ordering/case results rather than inventing a universal language-specific order.

Different samples may reveal different provider behavior. Identical ordering for these four strings does not prove equivalent collation semantics.

## 7. Reproduce a representability error

On a comparison database:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d chapter007_libc \
  -c "SELECT convert_to(U&'\20AC','LATIN1');"
echo $?
~~~

Expected: nonzero status and an error because the euro character cannot be represented in LATIN1. This reads a literal; it does not corrupt or change stored data.

Verify the connection still works:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d chapter007_libc \
  -c "SELECT 1;"
~~~

Expected: 1. Explain encoding conversion failure separately from checksum/storage failure.

## 8. Discuss collation drift

Using the inventory's recorded and actual collation versions, write:

- Which providers/locales expose version metadata?
- Which values are null, and why is that not automatically an incident?
- What dependent objects might need rebuilding after a real library change?
- Why does refreshing version metadata alone not repair affected indexes?

Do not refresh versions, edit catalogs or downgrade libraries during this lab.

## 9. Cleanup

Close all sessions connected to the two comparison databases. **Do not paste an unguarded DROP DATABASE command**. Inspect the exact disposable primary and independently confirm its Chapter 004 lab marker, port, user, database, data directory, system identifier, object ownership and two created provider types:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -c "SELECT current_database(), current_user, inet_server_port(), current_setting('data_directory'), system_identifier FROM pg_control_system();"
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -c "SELECT datname, datlocprovider, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname IN ('chapter007_libc','chapter007_builtin');"
~~~

If this is **the disposable Chapter 004 cluster and both databases were created by this run**, replace the placeholder with the observed system identifier and invoke the fail-closed cleanup script:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_admin -d postgres \
  -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID \
  -v confirm_cleanup=007-DROP-DATABASES \
  -f postgresql/scripts/007-drop-lab-databases.sql
~~~

The script refuses wrong cluster, role, port, data directory, provider, owner, active sessions, PostgreSQL major or confirmation token. It requires **both** expected databases to exist: after a partial creation failure, do not attempt blind cleanup; inspect and use a separately reviewed plan. Two DROP DATABASE commands cannot be atomic. If cleanup is interrupted, examine which names remain before trying anything else.

If an open session blocks cleanup, identify and close your exercise session. Do not use FORCE to disconnect unrelated work.

Remove the never-started initialization cluster using this guarded local cleanup:

~~~bash
python3 - "$PG_INIT_LAB_ROOT" <<'PY'
from pathlib import Path
import os, re, shutil, sys
root = Path(sys.argv[1])
if not re.fullmatch(r"/tmp/postgresql-init-lab\.[A-Za-z0-9]+", str(root)):
    raise SystemExit("Unexpected disposable path")
if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.getuid():
    raise SystemExit("Expected an owned real lab directory")
if (root/"LAB_MARKER").read_text().strip() != "chapter007-offline-disposable":
    raise SystemExit("Lab marker mismatch")
if (root/"data/postmaster.pid").exists():
    raise SystemExit("Server/PID state requires investigation; not removing")
for line in Path("/proc/self/mountinfo").read_text().splitlines():
    mount = line.split()[4]
    if mount == str(root) or mount.startswith(str(root)+"/"):
        raise SystemExit("Nested mount detected; not removing")
shutil.rmtree(root)
print("Offline initialization lab removed")
PY
~~~

This permanently removes only the identified disposable cluster. Keep the Chapter 004 environment intact. Restore shell variables introduced for this exercise and retain nonsecret evidence.

## 10. Acceptance

| Check | Pass condition |
|---|---|
| Identity | Matching PostgreSQL 18 tools and non-root OS account |
| Initialization | Fresh target with explicit UTF8/libc/C/SCRAM/checksums |
| Offline check | Clean shutdown state and checksum scan exits 0 |
| Database creation | Two unused comparison names created standalone |
| Metadata | Provider, locale, encoding and versions recorded |
| Text | Actual ordering/classification and byte/character results retained |
| Conversion | Expected LATIN1 error distinguished from corruption |
| Drift reasoning | Rebuild-before-refresh procedure explained |
| Cleanup | Comparison databases and offline root removed without affecting main lab |

Actual command outputs are required before marking this lab verified. Static review is recorded separately.
