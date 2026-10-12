# Lab 021 — Measure Database SLIs and Calculate Budgets

Audience: DBRE/SRE. PostgreSQL 18. Runtime execution pending.
[Chapter](../chapters/021-database-slis-slos-and-error-budgets.md) · [Evaluator](../scripts/021-slo-evaluate.py) · [Probe](../scripts/021-lab-operation-probe.py)

## Measurement contract

This synthetic operation opens a new psql connection to the disposable primary, reads one isolated row with FOR UPDATE, validates value 100 and rolls back. Availability-good means the complete command exits successfully with the expected value. Timely-good additionally means total client elapsed duration is at most 250 ms. The denominator includes every recorded eligible operation, including errors.

Elapsed time uses a monotonic clock and includes process startup, connection establishment and SQL. UTC completion timestamps assign events to reporting windows. This measurement excludes application pool checkout, real business transactions, COMMIT durability and replica freshness. Use it to learn definitions and arithmetic, not to declare a production SLO met.

Use a 99.9% availability target and 99% timely-success target for teaching. Three samples cannot establish either target. Low-volume output remains explicit.

## 1. Guard and provision

Start the Chapter 004 disposable cluster as its non-root Linux owner; export its PG_LAB_ROOT. Finish earlier concurrency labs. Work from repository root, adjusting script paths if needed. In operator terminal O:

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
  PGAPPNAME=c021_control PGOPTIONS='-c statement_timeout=5s -c lock_timeout=1s' \
    psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
[[ "$(admin -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(admin -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
[[ "$(admin -Atc "SELECT current_setting('server_version_num')::int BETWEEN 180000 AND 189999")" == t ]] || exit 2
~~~

Provision once in O:

~~~bash
admin <<'SQL'
BEGIN;
CREATE SCHEMA c021_slo AUTHORIZATION lab_admin;
CREATE TABLE c021_slo.probe (id integer PRIMARY KEY, value integer NOT NULL);
INSERT INTO c021_slo.probe VALUES (1,100);
GRANT USAGE ON SCHEMA c021_slo TO lab_app, lab_observer;
GRANT SELECT, UPDATE ON c021_slo.probe TO lab_app;
GRANT SELECT ON c021_slo.probe TO lab_observer;
COMMIT;
SQL
~~~

An existing schema is a precondition failure; investigate its owner. No passwords are printed. The probe independently checks the lab directory, marker, private passfile, client version and server identity before creating evidence.

The probe writes new private CSV files beneath PG_LAB_ROOT/c021-evidence. Existing filenames are refused. If repeating a phase, choose a new basename and retain the old evidence. Raw error text and SQL parameter values are not recorded.

## 2. Baseline and slow success

In O:

~~~bash
python3 postgresql/scripts/021-lab-operation-probe.py --output baseline.csv --mode fast --count 3
python3 postgresql/scripts/021-lab-operation-probe.py --output slow.csv --mode slow --count 3
~~~

Baseline should record successful operations; elapsed time may exceed 250 ms on a slow host. Do not alter observed values to match an expectation.

Slow mode introduces a 400 ms server sleep inside the isolated transaction before reading. Expect success 1 with duration greater than 250 ms. These are availability-good and timely-bad. The one-second statement budget still bounds each statement; lock budget is 500 ms and total transaction budget two seconds.

The probe is serial and makes at most 20 operations per invocation. It is not a load generator or periodic production health check.

## 3. Contention produces failed operations

In terminal H, repeat the shell guard/export block above, then open a bounded actor:

~~~bash
PGAPPNAME=c021_holder \
PGOPTIONS='-c statement_timeout=30s -c lock_timeout=2s -c transaction_timeout=120s -c idle_in_transaction_session_timeout=120s -c idle_session_timeout=0' \
  psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab
~~~

Inside H:

~~~sql
\set VERBOSITY verbose
BEGIN;
UPDATE c021_slo.probe SET value=101 WHERE id=1;
~~~

Leave H at its prompt. In O, while H still holds the lock:

~~~bash
python3 postgresql/scripts/021-lab-operation-probe.py --output blocked.csv --mode fast --count 3
~~~

Expect three success 0 events as the probe's FOR UPDATE encounters its lock budget. Failures count against both availability and timely success even if their measured duration is short. The probe records outcome flags, not a diagnostic SQLSTATE; use controlled client/server evidence separately when diagnosing failure cause.

In H issue ROLLBACK and \q before the two-minute guard expires. In O:

~~~bash
python3 postgresql/scripts/021-lab-operation-probe.py --output recovered.csv --mode fast --count 3
admin -c 'SELECT value FROM c021_slo.probe WHERE id=1;'
~~~

Expect successful recovered operations and value 100. If H timed out before blocked measurements, the samples may succeed. Diagnose ordering and repeat with new evidence filenames.

No cancellation, termination, cluster outage or role default changes are required.

## 4. Freeze a window and calculate

Capture one fixed UTC end after all samples:

~~~bash
REPORT_END="$(python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())')"
python3 postgresql/scripts/021-slo-evaluate.py "$PG_LAB_ROOT/c021-evidence/slow.csv" \
  --end "$REPORT_END" --window-seconds 3600 --latency-ms 250 \
  --availability-target 0.999 --latency-target 0.99
python3 postgresql/scripts/021-slo-evaluate.py "$PG_LAB_ROOT/c021-evidence/blocked.csv" \
  --end "$REPORT_END" --window-seconds 3600 --latency-ms 250 \
  --availability-target 0.999 --latency-target 0.99
~~~

Keep REPORT_END with the evidence. Ensure the chosen window contains your sample timestamps. Start is included; end is excluded. A late report cannot silently redefine the original observation period.

For three slow successful events, availability-good = 3, timely-good = 0. Availability burn = 0. Timely allowance = 0.03 bad events; three timely failures consume 100 times that allowance. For three blocked failures, availability allowance = 0.003; consumption = 1000 times allowance. Both files should be LOW_VOLUME with the default minimum of 100 events.

These ratios illustrate tiny event populations, not a statistically supported forecast or automatic page. Budget consumed and burn rate are numerically equal here because both use the same observed event window; alerting systems compare burn across different windows.

## 5. Aggregate counts, not percentages

Combine matching files with one header; event IDs are unique for each probe invocation:

~~~bash
python3 - "$PG_LAB_ROOT/c021-evidence" <<'PY'
import csv, sys
from pathlib import Path
directory = Path(sys.argv[1])
names = ["baseline.csv", "slow.csv", "blocked.csv", "recovered.csv"]
with (directory / "combined.csv").open("x", newline="", encoding="utf-8") as output:
    writer = None
    for name in names:
        with (directory / name).open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if writer is None:
                writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
                writer.writeheader()
            writer.writerows(reader)
PY
python3 postgresql/scripts/021-slo-evaluate.py "$PG_LAB_ROOT/c021-evidence/combined.csv" \
  --end "$REPORT_END" --window-seconds 3600
~~~

For the expected ordering there are 12 eligible events, nine successes and three availability failures. Timely-good depends on real baseline/recovered durations; it cannot exceed six because the slow successes and blocked failures are timely-bad.

Compare this event-weighted result with an unweighted average after taking a phase with a different count. Explain why averaging percentages would bias the result. Do not mix different operation contracts or environments into this file.

## 6. Exercise measurement boundaries offline

Copy a synthetic CSV into a separate temporary working directory, not over live evidence. Give it events at the window start, just before end and exactly at end; verify only the first two are counted. Add eligible 0 for a documented exclusion and verify it is reported separately.

Evaluate a header-only file: quality must be NO_EVENTS and SLI/burn must be null. This means no observed events, not verified health. A missing file is an error. Duplicate IDs, naive timestamps, nonfinite durations, negative durations and invalid flag values must be rejected.

For arithmetic independent of PostgreSQL, generate 200,000 events with 80 unsuccessful outcomes in the reporting window. Availability should be 0.9996, allowance 200 and consumption 0.4 at target 0.999. Keep synthetic data clearly labeled.

The evaluator cannot detect an instrumentation path that dropped all failed requests. Propose an independent coverage signal and explain how missing telemetry would be escalated separately from low legitimate traffic.

## 7. Draft a service policy and clean up

Write a one-page contract with consumer, operation, endpoint, good predicates, targets, rolling/calendar window, source, coverage monitor, exclusions, owners and budget decision policy. Describe one actionable fast-burn alert and its short/long windows without treating this tiny lab sample as a production threshold.

Record how pool wait, retries and uncertain commit outcomes will be measured. Add freshness and restore/recovery requirements if the workload needs them. Do not count a rollback-only probe as commit durability evidence.

Confirm H is closed and no probe is running. In O:

~~~bash
admin -c "SELECT pid,backend_start,application_name,state FROM pg_stat_activity WHERE datname='ops_lab' AND application_name IN ('c021_holder','c021_probe');"
admin <<'SQL'
BEGIN;
DROP TABLE c021_slo.probe;
DROP SCHEMA c021_slo;
COMMIT;
SELECT to_regnamespace('c021_slo') IS NULL AS fixture_removed;
SQL
~~~

Required: no actor/probe sessions and fixture_removed true. Resolve any remaining actor through its terminal before retrying bounded cleanup. Preserve private CSV evidence and report outputs; no server settings or role defaults need restoration.

Acceptance requires real baseline, slow, blocked and recovered observations, fixed-window calculations, boundary/invalid-input results, the SLI contract and cleanup evidence. Offline evaluator tests do not verify PostgreSQL behavior or production telemetry coverage.
