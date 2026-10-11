# Lab 001 — Operational Ownership and Readiness

[Chapter 001](../chapters/001-postgresql-responsibilities-for-dbre-and-sre.md) · [Master plan](../MASTER-PLAN.md)

## Objective

Build a small operational evidence pack and demonstrate why endpoint readiness is different from authenticated SQL and successful workload execution.

**Reference environment:** PostgreSQL 17, psql and pg_isready; Bash on Linux, macOS or WSL. Record the exact versions.  
**Duration:** 45–60 minutes.  
**Required access:** an existing disposable PostgreSQL instance and an authorized login with CONNECT. An approved observer with monitoring visibility is preferred. No superuser is required for the exercises.  
**Production impact:** the two-session pg_sleep exercise belongs in a disposable lab only. It consumes one extra connection for 30 seconds. No restart, promotion, DDL or persistent configuration changes are performed.

If you do not have an instance yet, complete environment provisioning in Chapter 004 before attempting this lab. Do not invent output or mark it verified.

## 1. Record the environment

From the repository root, configure the lab endpoint:

~~~bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=postgres
export PGUSER=YOUR_AUTHORIZED_LAB_ROLE
export PGCONNECT_TIMEOUT=5
export PGAPPNAME=chapter001-observer

psql --version
pg_isready --version
psql -X -v ON_ERROR_STOP=1 -c "SELECT version();"
~~~

Use the supplied lab credentials through your approved mechanism. Never paste them into the evidence pack. For a Unix socket, PGHOST can be the configured socket directory.

Record host, port, database, environment label, deployment type, server/client version and the authorized role. A null inet_server_addr() later can simply mean a Unix-socket connection.

## 2. Run two independent probes

~~~bash
pg_isready -t 5
psql -X -v ON_ERROR_STOP=1   -c "SELECT current_database(), current_user, pg_is_in_recovery();"
~~~

Expected pattern for a reachable lab server:

- pg_isready reports “accepting connections” and exits with status 0.
- psql returns your explicit database and authorized role.
- pg_is_in_recovery() is false for a typical standalone instance or primary and true for an instance in recovery.

Interpretation: the first result is endpoint readiness; the second proves this role can connect and execute this particular SQL. Neither proves a business transaction or recovery capability.

Record unexpected failures rather than silently changing the endpoint or role.

## 3. Collect the baseline

~~~bash
mkdir -p evidence/chapter001
psql -X -v ON_ERROR_STOP=1   -f postgresql/scripts/001-first-response-snapshot.sql   > evidence/chapter001/baseline.txt
~~~

Check the command's exit status immediately:

~~~bash
echo $?
~~~

Expected status: 0. On error, inspect terminal stderr and stop. Do not treat a partial output file as a successful snapshot.

Identify these six facts:

1. Connected identity, endpoint and database.
2. Server version and current recovery state.
3. Server start timestamp.
4. Connection distribution by database, role and application.
5. Selected configuration values and their units.
6. Database footprint and cumulative counter reset timestamps.

Do not calculate throughput from a single cumulative sample. Do not call database size “free disk space.”

## 4. Controlled observation exercise

Open **Terminal A** using the same lab endpoint and authorized role. Run:

~~~bash
PGAPPNAME=chapter001-workload psql -X -v ON_ERROR_STOP=1   -c "SELECT pg_sleep(30);"
~~~

While it is running, use **Terminal B**:

~~~bash
psql -X -v ON_ERROR_STOP=1   -c "SELECT pid, application_name, state, wait_event_type, wait_event
      FROM pg_stat_activity
      WHERE application_name = 'chapter001-workload';"
~~~

Expected during the sleep: a session labeled chapter001-workload, state active, wait_event_type Timeout and wait_event PgSleep. If the row is absent, verify both terminals point to the same instance and repeat the bounded exercise. If details are hidden, document the observer's visibility boundary and ask the lab administrator to review access.

This session is deliberately waiting. “Active” is not equivalent to “using CPU,” and this wait is not a storage bottleneck.

Let the session finish normally. Repeat the query: the short-lived connection should disappear. No cancellation is needed.

## 5. Demonstrate a workload timeout

On the disposable lab:

~~~bash
PGAPPNAME=chapter001-timeout psql -X -v ON_ERROR_STOP=1   -c "SET statement_timeout = '500ms'; SELECT pg_sleep(2);"
~~~

Check the result immediately:

~~~bash
echo $?
~~~

Expected: an error indicating cancellation due to statement timeout, with nonzero psql status. This is an intentional failed probe. The setting applies to this connection; exiting restores the lab baseline without a persistent change.

Then run:

~~~bash
pg_isready -t 5
psql -X -v ON_ERROR_STOP=1 -c "SELECT 1 AS authenticated_probe;"
~~~

Expected: readiness still succeeds and the authenticated probe returns 1. A failed SQL workload does not necessarily mean the PostgreSQL endpoint is unavailable.

Write a short explanation of how an application timeout can occur while a basic health check passes. A real incident still requires its actual wait, query, resource and application evidence.

## 6. Create the ownership and readiness record

Create evidence/chapter001/ownership.md with:

| Field | Your lab entry |
|---|---|
| Environment and service | |
| DBRE / SRE / application / platform owner | |
| Escalation route | |
| Endpoint, database and role | |
| Deployment and exact version | |
| Recovery state and known topology | |
| Availability and latency objective | |
| RPO and RTO for a named scenario | |
| Backup destination and retention | |
| Last verified restore evidence | |
| Storage and WAL capacity evidence | |
| Monitoring and runbook links | |
| Unknowns with owner and due date | |

For a lab, a named exercise owner is sufficient. For backup, HA and capacity fields not yet established, enter “unknown” and a follow-up owner. This is an ownership exercise, not proof that those capabilities exist.

## 7. Write an incident-style observation

Use this template:

- UTC observation time:
- Target environment and endpoint:
- User impact: synthetic lab probe only.
- Readiness result:
- Authenticated SQL result:
- Controlled workload result:
- Observed wait and session state:
- What the evidence supports:
- What remains unknown:
- Action taken and why:
- Verification result:
- Follow-up owner:

Example conclusion: “The endpoint accepted connections and SELECT 1 succeeded. The bounded pg_sleep workload was cancelled by its session statement timeout. No database outage or storage bottleneck was established.”

## 8. Cleanup

- Confirm both short-lived exercise sessions have exited.
- Close any remaining lab psql connections with backslash-q.
- Keep the evidence pack locally; review it before sharing. Metadata can expose internal endpoint and account names.
- If these environment variables were introduced only for this lab, clear them:

~~~bash
unset PGHOST PGPORT PGDATABASE PGUSER PGCONNECT_TIMEOUT PGAPPNAME
~~~

If your shell already had connection settings before the exercise, restore the prior values instead of clearing them.

## 9. Acceptance checklist

| Check | Pass condition |
|---|---|
| Identity | Database, role, version and environment recorded correctly |
| Readiness | Endpoint readiness distinguished from authenticated SQL |
| Snapshot | Script exits 0; values interpreted with units and visibility limitations |
| Controlled wait | Sleep session observed and wait explained correctly |
| Timeout | Failed workload observed while subsequent probes succeed |
| Ownership | All required fields populated or assigned as owned unknowns |
| Cleanup | Exercise sessions ended; no persistent settings changed |
| Handover | Another operator can explain results from the evidence alone |

**Evidence files:** baseline.txt, ownership.md and your incident-style observation.

**Completion rule:** reading this lab is not a lab pass. Record the environment and actual output when executed.
