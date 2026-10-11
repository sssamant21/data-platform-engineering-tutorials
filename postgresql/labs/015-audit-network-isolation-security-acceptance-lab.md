# Lab 015 — Audit Evidence, Network Isolation and Security Acceptance

**Audience:** DBRE/SRE. **Baseline:** Chapter 004 PostgreSQL 18 Linux lab.
**Duration:** 90–120 minutes; optional pgAudit track adds 45–60 minutes.
**Runtime status:** Pending.

[Chapter](../chapters/015-audit-logging-network-isolation-and-security-acceptance.md) · [Setup](004-reproducible-postgresql-operations-lab.md) · [Inspection](../scripts/015-security-acceptance-inspection.sql) · [Report template](../projects/015-security-acceptance-report.md)

Use only the disposable primary. Complete cleanup from Chapters 013–014 first. The core track introduces three temporary logging overrides and one synthetic schema. It does not change credentials, listener interfaces, firewalls or cloud rules.

## 1. Guard and logging preconditions

~~~bash
: "${PG_LAB_ROOT:?Export the Chapter 004 disposable lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable PGAPPNAME=chapter015-control
umask 077
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
app_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab "$@"
}
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW listen_addresses')" == 127.0.0.1 ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW logging_collector')" == off ]] || exit 2
[[ "$(lab_sql -Atc "SELECT count(*) FROM pg_namespace WHERE nspname='c015_audit'")" == 0 ]] || exit 2
EVIDENCE_015="$PG_LAB_ROOT/evidence-015"
[[ ! -e "$EVIDENCE_015" && ! -L "$EVIDENCE_015" ]] || exit 2
mkdir -m 700 "$EVIDENCE_015"
START_LINE_015="$(wc -l < "$PG_LAB_ROOT/logs/primary.log")"
lab_sql -f scripts/015-security-acceptance-inspection.sql > "$EVIDENCE_015/baseline.txt"
lab_sql -c "SELECT name,setting,source,sourcefile FROM pg_settings
WHERE name IN ('log_connections','log_disconnections','log_line_prefix','log_statement','log_min_error_statement');"
lab_sql -c "SELECT sourcefile,name,setting,error FROM pg_file_settings
WHERE error IS NOT NULL OR (sourcefile LIKE '%/postgresql.auto.conf'
AND name IN ('log_connections','log_disconnections','log_line_prefix'));"
~~~

Require no file errors or auto-conf entries for the three changed parameters. Baseline connection logging must be empty/off, disconnections off, statement logging none, error statements error, and prefix the original Chapter 004 value. Preserve outputs; stop if another exercise left unexplained changes.

The log destination is the existing protected $PG_LAB_ROOT/logs/primary.log. Do not enable a collector or install a log shipper for this core track.

## 2. Enable bounded connection correlation

~~~bash
lab_sql <<'SQL'
ALTER SYSTEM SET log_connections = 'authentication,authorization';
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_line_prefix = '%m [%p] %c %u@%d %a %r %e ';
SELECT pg_reload_conf();
SQL
lab_sql -c "SELECT name,setting FROM pg_settings WHERE name IN ('log_connections','log_disconnections','log_line_prefix');"
~~~

Allow up to ten seconds for reload observation. These PG18 connection settings take effect on fresh connections. Do not run password changes or sensitive queries while statement/error logging is part of this experiment.

## 3. Generate synthetic administrative/read evidence

~~~bash
PGAPPNAME=chapter015-admin lab_sql <<'SQL'
SET statement_timeout='5s';
SET lock_timeout='1s';
SET log_statement='all';
BEGIN;
CREATE SCHEMA c015_audit AUTHORIZATION lab_admin;
CREATE TABLE c015_audit.probe(id integer PRIMARY KEY,payload text NOT NULL);
INSERT INTO c015_audit.probe VALUES (1,'synthetic-audit-fixture');
GRANT USAGE ON SCHEMA c015_audit TO lab_app;
GRANT SELECT ON c015_audit.probe TO lab_app;
SELECT id,payload FROM c015_audit.probe;
COMMIT;
SQL
PGAPPNAME=chapter015-reader app_sql -c 'SELECT id,payload FROM c015_audit.probe;'
if PGAPPNAME=chapter015-denied app_sql -c 'DELETE FROM c015_audit.probe WHERE false;' \
  > "$EVIDENCE_015/denied-client.txt" 2>&1; then
  echo 'FAIL: application DELETE unexpectedly allowed; stop and investigate.'
else
  echo 'Require relation permission denial (42501), not an arbitrary connection failure.'
fi
tail -n "+$((START_LINE_015+1))" "$PG_LAB_ROOT/logs/primary.log" > "$EVIDENCE_015/core-window.log"
rg -n 'chapter015-|c015_audit' "$EVIDENCE_015/core-window.log" \
  > "$EVIDENCE_015/core-events.txt"
~~~

Require successful administrative DDL/grant/read records, successful app authentication/disconnection and the denied app statement/error. The administrative session alone used log_statement all. The app's successful SELECT text is not required to appear; this demonstrates a core event-coverage gap, not complete application read auditing.

The client may not display SQLSTATE by default; correlate the prefix's error code and protected error record. Record session/PID/time and SQL outcome. Do not treat a logged statement as commit evidence without transaction/result reconciliation.

## 4. Assess exposure and HBA admission separately

Inspect listeners and confirm only expected loopback endpoints:

~~~bash
ss -lntp
~~~

Record address/port/process ownership for 55432–55434. Require no wildcard, non-loopback or unexpected IPv6 database listener. An OS listing alone does not establish cloud, container or proxy exposure.

A bounded TCP check:

~~~bash
python3 - <<'PY'
import socket
for port in (55432,55433,55434,55435):
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=2):
            reachable=True
    except OSError:
        reachable=False
    print(f"127.0.0.1:{port} TCP reachable={reachable}")
    if reachable != (port in (55432,55433,55434)):
        raise SystemExit("Unexpected listener reachability; investigate")
PY
~~~

55435 must be unused; if it is occupied, stop and identify it rather than stopping another service. These probes do not authenticate and may generate incomplete-startup log noise.

Demonstrate application admission denial with Chapter 012's known narrow rule:

~~~bash
if [[ ! -e "$PG_LAB_ROOT/evidence-012" ]]; then
  python3 scripts/012-hba-lab.py prepare
fi
python3 scripts/012-hba-lab.py status
python3 scripts/012-hba-lab.py reject
lab_sql -c 'SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL;'
lab_sql -c 'SELECT pg_reload_conf();'
if PGAPPNAME=chapter015-hba-denied app_sql -c 'SELECT 1;' \
  > "$EVIDENCE_015/hba-denied.txt" 2>&1; then
  echo 'Not rejected: inspect reload and repeat within the bounded window.'
else
  echo 'Require the explicit HBA rejection for the intended app tuple.'
fi
python3 scripts/012-hba-lab.py restore
lab_sql -c 'SELECT pg_reload_conf();'
app_sql -c 'SELECT 1;'
~~~

Require original disk state before staging, zero parse errors, expected denial and fresh restoration. HBA denied the login after PostgreSQL was reached; it did not create network-layer isolation.

Fill the report's production-source gates separately from authorized test clients in the actual deployment. Without those hosts/network controls, mark those gates Pending. Do not claim this loopback test proves firewall isolation.

## 5. Optional pgAudit 18.x track

If audit-oriented event records are a requirement, a skipped track remains Pending. The extension must be supplied by the approved PostgreSQL 18 package/build or managed-service mechanism; no package installation is performed by this lab.

Preconditions:

~~~bash
lab_sql -c "SELECT name,default_version,installed_version FROM pg_available_extensions WHERE name='pgaudit';"
lab_sql -c "SELECT name,setting,source FROM pg_settings WHERE name='shared_preload_libraries';"
lab_sql -c "SELECT name,setting FROM pg_file_settings WHERE sourcefile LIKE '%/postgresql.auto.conf' AND name='shared_preload_libraries';"
~~~

Require an available matching 18.x extension, not installed yet; the Chapter 004 preload list must be empty with no auto-conf entry. Otherwise stop and use a deployment-specific procedure preserving existing libraries/extension ownership.

~~~bash
lab_sql -c "ALTER SYSTEM SET shared_preload_libraries = 'pgaudit';"
bash scripts/004-operations-lab.sh stop
bash scripts/004-operations-lab.sh start
lab_sql -c 'CREATE EXTENSION pgaudit;'
PGAPPNAME=chapter015-pgaudit lab_sql <<'SQL'
SET statement_timeout='5s';
SET lock_timeout='1s';
SET pgaudit.log='read,write,ddl,role,misc_set';
SET pgaudit.log_parameter=off;
BEGIN;
CREATE TABLE c015_audit.audit_rollback(id integer);
INSERT INTO c015_audit.audit_rollback VALUES (1);
GRANT SELECT ON c015_audit.audit_rollback TO lab_app;
SET ROLE lab_app;
SELECT * FROM c015_audit.audit_rollback;
RESET ROLE;
ROLLBACK;
SQL
tail -n "+$((START_LINE_015+1))" "$PG_LAB_ROOT/logs/primary.log" > "$EVIDENCE_015/pgaudit-window.log"
rg -n 'chapter015-pgaudit.*AUDIT:' "$EVIDENCE_015/pgaudit-window.log" \
  > "$EVIDENCE_015/pgaudit-events.txt"
lab_sql -c "SELECT to_regclass('c015_audit.audit_rollback') AS rolled_back_table;"
~~~

Require audit records for selected classes and rolled_back_table NULL. Logged WRITE/DDL did not mean committed state. Audit settings were session-scoped and unchanged by SET ROLE; this does not verify global coverage for unrelated logins.

Before dropping the extension, confirm pgaudit.log is none in a fresh admin session. If it is set elsewhere, stop and investigate. Restore only the introduced preload entry:

~~~bash
lab_sql -c "SELECT current_setting('pgaudit.log') AS audit_scope;"
lab_sql -c 'DROP EXTENSION pgaudit;'
lab_sql -c 'ALTER SYSTEM RESET shared_preload_libraries;'
bash scripts/004-operations-lab.sh stop
bash scripts/004-operations-lab.sh start
~~~

Require original empty preload state after restart. Follow Chapter 009 for lifecycle timeout/failure; do not remove PID/WAL files to force startup.

## 6. Security acceptance and cleanup

Complete the report using actual evidence from Chapters 011–015. Core loopback checks do not establish production TLS, secret-store adoption, firewall paths, audit completeness or central retention. Keep unexecuted mandatory gates Pending.

After HBA is restored, remove only the synthetic schema and introduced settings:

~~~bash
lab_sql <<'SQL'
BEGIN;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
DROP TABLE c015_audit.probe;
DROP SCHEMA c015_audit;
COMMIT;
ALTER SYSTEM RESET log_connections;
ALTER SYSTEM RESET log_disconnections;
ALTER SYSTEM RESET log_line_prefix;
SELECT pg_reload_conf();
SQL
lab_sql -f scripts/015-security-acceptance-inspection.sql > "$EVIDENCE_015/final.txt"
python3 scripts/012-hba-lab.py status
python3 scripts/012-hba-lab.py clean-secrets
bash scripts/004-operations-lab.sh verify
~~~

Require original logging values/source, no introduced auto-conf entries, HBA original/error-free, schema absent, optional preload/extension restored, and original topology/probe success. Retain sanitized event evidence with protected access.

If cleanup finds unexpected objects, inspect their owner and origin; do not add CASCADE. If interrupted, preserve recovery access, restore HBA and the three known logging overrides, then reconcile optional extension/preload state before another restart.
