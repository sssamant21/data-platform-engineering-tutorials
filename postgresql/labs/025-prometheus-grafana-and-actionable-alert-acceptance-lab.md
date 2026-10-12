# Lab 025 — Monitoring and Alert Acceptance

Audience: DBRE/SRE. PostgreSQL 18. Live execution pending.
[Chapter](../chapters/025-prometheus-grafana-and-actionable-alert-acceptance.md) · [Assets](../monitoring/025/prometheus.yml)

## Scope and prerequisites

Use the running Chapter 004 primary and existing lab_observer role. PostgreSQL is not stopped or reconfigured. Faults affect only this lab's exporter connection/process. Notifications go only to a loopback receiver, never a real pager.

Install postgres_exporter v0.20.1 from its official release with platform/checksum verification. Also provide Prometheus with its matching promtool, Alertmanager with amtool, and a private Grafana instance. Record exact versions; importing JSON is not proof of Grafana acceptance.

Use separate foreground terminals O (operator), E (exporter), P (Prometheus), A (Alertmanager), R (receiver). Keep ports 9187, 9090, 9093 and 19093 free. Bind all services to loopback. Follow your Grafana instance's authentication procedure; do not enable anonymous access.

## 1. Guard and prepare private evidence

In O, from repository root as the non-root Chapter 004 owner:

~~~bash
set -euo pipefail
test -n "$PG_LAB_ROOT"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable
admin() {
  PGAPPNAME=c025_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
[[ "$(admin -Atc "SELECT count(*) FROM pg_roles WHERE rolname='c025_missing_role'")" == 0 ]] || exit 2
umask 077
evidence="$PG_LAB_ROOT/c025-evidence"
[[ ! -L "$evidence" ]] || exit 2
mkdir -p -m 700 "$evidence"
[[ -d "$evidence" && -O "$evidence" ]] || exit 2
MONITOR_DIR="$(pwd)/postgresql/monitoring/025"
export MONITOR_DIR
postgres_exporter --version
prometheus --version
promtool --version
alertmanager --version
amtool --version
~~~

Retain version outputs privately. The exporter version must be 0.20.1 for this contract. If your installation differs, first review its flags/metric names and test the adapted artifacts.

Copy only the existing observer password into a separate private file; the Chapter 004 passfile format is known and narrowly validated:

~~~bash
python3 - "$PG_LAB_ROOT/credentials.pgpass" "$evidence/observer.password" <<'PY'
from pathlib import Path
import os, re, stat, sys
source, target = map(Path, sys.argv[1:])
info = source.stat()
assert not source.is_symlink() and stat.S_ISREG(info.st_mode)
assert info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600
matches = []
for line in source.read_text().splitlines():
    fields = line.split(":")
    if len(fields) == 5 and fields[:4] == ["127.0.0.1","55432","*","lab_observer"]:
        assert re.fullmatch(r"[0-9a-fA-F]{48}",fields[4])
        matches.append(fields[4])
assert len(matches) == 1
with target.open("x", encoding="utf-8") as output:
    output.write(matches[0])
os.chmod(target,0o600)
PY
printf '{}\n' > "$evidence/exporter.yml"
~~~

Never print the password or put it in a DSN, command line or config committed to Git. Existing password evidence is refused. If repeating, resolve the prior attempt before creating new secrets.

## 2. Validate rules and configurations

~~~bash
(
  cd "$MONITOR_DIR"
  promtool check config prometheus.yml
  promtool check rules rules.yml
  promtool test rules rules.test.yml
  amtool check-config alertmanager.yml
)
~~~

Expected: actual tool success, including seven rule fixtures with 45 alert expectations. These cover healthy, pending/firing, transient failure, database connection failure, collection error, missing metric, absent target and recovery. YAML parsing alone does not validate PromQL or expected alert timing.

If tests fail, retain the tool version/output and resolve the contract before starting the stack. Do not replace these tests with a Python imitation of PromQL.

## 3. Start a loopback stack

In each terminal export PG_LAB_ROOT and MONITOR_DIR to the guarded values. Do not copy secret contents.

R, from repository root:

~~~bash
python3 postgresql/scripts/025-lab-alert-receiver.py --output notifications.jsonl
~~~

A:

~~~bash
cd "$MONITOR_DIR"
alertmanager --config.file=alertmanager.yml \
  --web.listen-address=127.0.0.1:9093 --cluster.listen-address="" \
  --storage.path="$PG_LAB_ROOT/c025-evidence/alertmanager-data"
~~~

P:

~~~bash
cd "$MONITOR_DIR"
prometheus --config.file=prometheus.yml --web.listen-address=127.0.0.1:9090 \
  --storage.tsdb.path="$PG_LAB_ROOT/c025-evidence/prometheus-data" \
  --storage.tsdb.retention.time=2h --storage.tsdb.retention.size=100MB
~~~

E, initially with the real observer account:

~~~bash
unset DATA_SOURCE_NAME DATA_SOURCE_URI_FILE DATA_SOURCE_USER_FILE DATA_SOURCE_PASS
unset PG_EXPORTER_EXTEND_QUERY_PATH PG_EXPORTER_CONSTANT_LABELS
export DATA_SOURCE_URI='127.0.0.1:55432/ops_lab?sslmode=disable&connect_timeout=3&application_name=c025_exporter&options=-c%20statement_timeout%3D3000'
export DATA_SOURCE_USER=lab_observer
export DATA_SOURCE_PASS_FILE="$PG_LAB_ROOT/c025-evidence/observer.password"
export PG_EXPORTER_COLLECTION_TIMEOUT=5s
export PG_EXPORTER_DISABLE_DEFAULT_METRICS=false
export PG_EXPORTER_AUTO_DISCOVER_DATABASES=false
export PG_EXPORTER_METRIC_PREFIX=pg
postgres_exporter --config.file="$PG_LAB_ROOT/c025-evidence/exporter.yml" \
  --web.listen-address=127.0.0.1:9187 --collector.stat_database \
  --no-collector.stat_statements
~~~

These processes remain in their own foreground terminals; use Ctrl+C only on those processes during faults/cleanup. Do not use broad process-name kills.

## 4. Verify baseline metrics and Grafana

In O:

~~~bash
curl --fail --max-time 10 http://127.0.0.1:9187/metrics > "$evidence/baseline-metrics.txt"
curl --fail --max-time 10 http://127.0.0.1:9090/api/v1/targets > "$evidence/targets.json"
curl --fail --max-time 10 --get --data-urlencode 'query=up{job="postgres-lab"}' \
  http://127.0.0.1:9090/api/v1/query
curl --fail --max-time 10 --get --data-urlencode 'query=pg_up{job="postgres-lab"}' \
  http://127.0.0.1:9090/api/v1/query
~~~

After a few scrapes, expect up=1, pg_up=1 and pg_exporter_last_scrape_error=0. Inspect HELP/TYPE and labels for required metrics, including pg_stat_database_xact_commit and numbackends. Resolve collector errors rather than hiding their alert.

Add a Prometheus data source pointing to http://127.0.0.1:9090 in your private Grafana. Import grafana-dashboard.json through dashboard import and choose that source. If Grafana is containerized/on another host, localhost refers to that process's network namespace; adapt the private connection path deliberately.

Select ops_lab and UTC. Compare stat-panel values with raw Prometheus queries. Internal transaction rates need several samples; they are not application request rates. Record exporter, database and collection-health panels separately. Do not transform missing data into a green zero-error or one-available value.

## 5. Fault: exporter unavailable, database still healthy

In E press Ctrl+C to stop only this exporter. Leave PostgreSQL running. In O verify a direct approved database SELECT and inspect Prometheus targets/rules:

~~~bash
admin -c 'SELECT 1;'
curl --fail --max-time 10 http://127.0.0.1:9090/api/v1/rules > "$evidence/rules-exporter-fault.json"
~~~

Observe pending then firing for PgExporterScrapeFailed after its condition persists for a minute plus scrape/evaluation alignment. PgDatabaseProbeFailed should not fire simply because the exporter disappeared.

R's private notifications.jsonl must receive the correct firing alert labels through Alertmanager. Detection/delivery time includes rule evaluation and the configured grouping delays; measure it.

Restart E with the unchanged observer settings and exporter command. Expect up=1 and PgExporterScrapeFailed resolving, followed by a resolved notification. Grafana should show missing database telemetry while the exporter is unavailable, not fabricate database health.

## 6. Fault: authentication failure, exporter HTTP still healthy

In E stop the exporter, change only its account to the verified nonexistent role, then restart the same command:

~~~bash
export DATA_SOURCE_USER=c025_missing_role
postgres_exporter --config.file="$PG_LAB_ROOT/c025-evidence/exporter.yml" \
  --web.listen-address=127.0.0.1:9187 --collector.stat_database \
  --no-collector.stat_statements
~~~

Do not create that role or modify HBA/passwords. Expect HTTP scrape up=1 while pg_up=0. PgDatabaseProbeFailed should become firing after the minute hold, with local firing delivery. A collection-error alert is gated to a successful database connection so it should not duplicate this authentication case.

Restore E: Ctrl+C, DATA_SOURCE_USER=lab_observer, then the normal exporter command. Require restored metrics, resolved rule state and resolved notification. Confirm application/database evidence remained healthy through the injected monitoring credential failure.

Other conditions are covered by promtool fixtures. Missing-target and partial-collection live tests remain additional acceptance work if you deploy those paths in production; do not claim they were injected by these two faults.

## 7. Evaluate usefulness and clean up

Inspect the local receiver records. It keeps status and selected routing/identity labels, not annotations or full raw webhook payload. Confirm owner/severity/environment/cluster/instance identify the intended operational scope.

Write one acceptance record with versions, metric contract, tool outputs, dashboard/no-data observations, pending/firing/resolved times, local delivery and each alert's first diagnostic action. Production route acceptance still requires an approved destination and real on-call escalation testing.

After resolved deliveries, Ctrl+C in E, P, A and R. Stop any Grafana instance created solely for this lab through its own lifecycle. In O:

~~~bash
admin -c "SELECT pid,backend_start,application_name FROM pg_stat_activity WHERE application_name='c025_exporter';"
rm -- "$evidence/observer.password"
~~~

Require no exporter backend; resolve a remaining connection through its owned process. Remove only the derived password file, not credentials.pgpass or unrelated data. No roles, server settings or schema fixtures were changed. Keep private metrics/config/test/notification evidence and lab TSDB data until the retention review.

Acceptance is incomplete without actual promtool success and live firing/resolved delivery. Structural checks in the authoring environment do not prove exporter compatibility, PromQL semantics, Grafana rendering or Alertmanager delivery.
