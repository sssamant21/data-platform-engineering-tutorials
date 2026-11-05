# Chapter 14 Lab — PostgreSQL Incident Triage and Bounded Lock-Wait Diagnosis

**Status:** Written, **not executed**; independent review pending · **Reference:** PostgreSQL 17 · **Platform:** Windows 11 PowerShell + Docker Desktop (Linux containers), or equivalent local Docker shell · **Duration:** 35 minutes within the chapter's 60-minute session.

[Chapter 14](../../chapters/14-troubleshooting-and-incident-response.md) · [Learning path](../../README.md) · [Progress](../../STATUS-TRACKER.md)

## Objectives and 60-minute teaching context

| Minutes | Activity |
|---|---|
| 0–10 | Incident response workflow and production guardrails (chapter) |
| 10–20 | Connection and lock fundamentals (chapter) |
| 20–25 | Lab prerequisites and environment preflight |
| 25–30 | Start disposable PostgreSQL and capture baseline |
| 30–45 | Three-session blocking experiment |
| 45–50 | Read-only diagnostics: deadlocks, replication and storage |
| 50–55 | Safe rollback, cleanup and evidence |
| 55–60 | Incident summary, troubleshooting and acceptance |

**Architecture:** one disposable PostgreSQL 17 container, three separate interactive psql clients connected via docker exec. Session A holds a row lock; Session B waits for that row; Session C observes the blocking graph. A and B **ROLLBACK** so the synthetic data returns to its initial state.

~~~text
PowerShell terminal A -> psql A -> BEGIN / UPDATE id=1 (holds row lock)
PowerShell terminal B -> psql B -> UPDATE id=1 (waits, bounded by 30s)
PowerShell terminal C -> psql C -> pg_stat_activity / pg_blocking_pids
                              |
                       same local container
~~~

## 0. Prerequisites and safety gate (5 minutes)

- Docker Desktop running with Linux containers, PostgreSQL 17 image available or downloadable, three terminal windows and enough local disk space for a small disposable database.
- No production connectivity, AWS resources, Kubernetes deployment, host port publishing, bind mounts or named volumes are needed.
- All data is synthetic. The lab password is a throwaway value **only** for this isolated container; do not use it in production.
- **Stop** if a container with the same name already exists. Inspect rather than automatically replacing it.
- Run all commands only in your personal/non-production Docker context. Verify context and container identity before cleanup.

In PowerShell:

~~~powershell
docker context show
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter "name=pg-ir-ch14"
~~~

**Expected:** Docker responds, OS type is linux, and there is no existing pg-ir-ch14 container. If the container exists, stop this exercise and determine its ownership; do **not** overwrite or delete it.

## 1. Start the isolated PostgreSQL 17 container (5 minutes)

~~~powershell
docker run -d --name pg-ir-ch14 --label dbre.training.owner=chapter-14 -e POSTGRES_PASSWORD=TrainingOnly_Ch14_ChangeMe postgres:17
$LabContainerId = (docker inspect --format '{{.Id}}' pg-ir-ch14).Trim()
$LabDockerContext = (docker context show).Trim()
Write-Output "Record privately: context=$LabDockerContext container_id=$LabContainerId"
docker exec pg-ir-ch14 pg_isready -U postgres -d postgres
docker exec pg-ir-ch14 psql -X -U postgres -d postgres -c "SELECT current_database(), current_user, current_setting('server_version') AS version, pg_is_in_recovery();"
~~~

**Expected:** readiness eventually reports accepting connections; server version starts with 17, current database/user are postgres, pg_is_in_recovery is false. The image is not pinned to a minor patch release; record the actual server_version. No host TCP port is exposed.

If readiness initially fails while initdb runs, wait and retry. Do not substitute an existing server or modify another chapter's container.

Open **three independent PowerShell terminals** (A, B, C). In each run:

~~~powershell
docker exec -it pg-ir-ch14 psql -X -U postgres -d postgres
~~~

The SQL below runs **inside psql**, not in PowerShell. Keep terminals clearly labeled; \q exits psql. If a command is still waiting, do not type further SQL into that same session until it returns.

## 2. Baseline and synthetic table (5 minutes; terminal A)

~~~sql
SELECT now() AS observed_at, current_database() AS db,
       current_user AS observer, pg_is_in_recovery() AS is_standby;
SHOW max_connections;
SHOW superuser_reserved_connections;
SHOW reserved_connections;
SHOW lock_timeout;
SHOW statement_timeout;

CREATE TABLE public.incident_ch14 (
    id integer PRIMARY KEY,
    status text NOT NULL
);
INSERT INTO public.incident_ch14(id, status)
VALUES (1, 'ready'), (2, 'ready');
SELECT id, status FROM public.incident_ch14 ORDER BY id;
~~~

**Expected:** two rows, both status=ready. These CREATE/INSERT commands are the **only committed application-data changes** in the exercise. If the table already exists, stop and inspect; do not TRUNCATE or DROP an unknown object. On a clean container this is a first-run-only step.

In terminal C, inspect baseline sessions and deadlocks:

~~~sql
SELECT datname, state, wait_event_type, count(*) AS sessions
FROM pg_stat_activity
WHERE backend_type='client backend'
GROUP BY datname, state, wait_event_type
ORDER BY sessions DESC;

SELECT datname, deadlocks, stats_reset
FROM pg_stat_database
WHERE datname=current_database();
~~~

**Expected:** several client backends (three psql sessions); deadlock count ordinarily 0 on a fresh instance. Counts vary and may include transient connections.

## 3. Generate one bounded lock wait (10–15 minutes)

**Read this entire section before starting.** The waiting statement is deliberately time-limited to **30 seconds**; the lock holder is protected by a **90-second idle-in-transaction timeout**. If the waiter times out before you observe it, use the recovery steps and repeat only in this disposable environment. Never use this pattern against a shared or production database.

### Terminal A — hold a row lock

~~~sql
SET application_name='ch14_blocker';
BEGIN;
SET LOCAL idle_in_transaction_session_timeout='90s';
UPDATE public.incident_ch14 SET status='uncommitted_A' WHERE id=1;
SELECT pg_backend_pid() AS blocker_pid;
~~~

**Expected:** UPDATE 1; the transaction stays open. The row is locked and its update is **not committed**. The idle-in-transaction timeout may terminate this session if left idle for 90 seconds, automatically rolling back; this is a safety backstop, not a normal production remediation technique.

### Terminal B — try to update the same row

~~~sql
SET application_name='ch14_waiter';
BEGIN;
SET LOCAL lock_timeout='30s';
SET LOCAL statement_timeout='45s';
UPDATE public.incident_ch14 SET status='uncommitted_B' WHERE id=1;
~~~

**Expected:** the UPDATE **waits** until terminal A releases its row lock, or returns a lock-timeout error after about 30 seconds (SQLSTATE 55P03). Keep terminal B waiting while immediately switching to terminal C.

### Terminal C — inspect the blocking graph

~~~sql
SELECT now() AS observed_at,
       a.pid AS waiting_pid, a.application_name,
       a.state, a.wait_event_type, a.wait_event,
       pg_blocking_pids(a.pid) AS blocking_pids,
       now()-a.query_start AS query_age
FROM pg_stat_activity AS a
WHERE a.application_name IN ('ch14_blocker','ch14_waiter')
ORDER BY a.application_name;

SELECT a.pid, a.application_name,
       a.wait_event_type, a.wait_event,
       pg_blocking_pids(a.pid) AS blocking_pids
FROM pg_stat_activity AS a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0;

SELECT pid, locktype, mode, granted,
       relation::regclass AS relation_name
FROM pg_locks
WHERE database=(SELECT oid FROM pg_database WHERE datname=current_database())
  AND relation IS NOT NULL
ORDER BY pid, granted LIMIT 30;
~~~

**Expected while B is waiting:** ch14_waiter has a non-empty blocking_pids array containing A's backend PID. Its wait_event_type should commonly be Lock, often with wait_event transactionid. The exact pg_locks rows vary; do not require a visible row-level lock entry. If no blocker appears, B may already have timed out or A may have rolled back automatically. Confirm session states before repeating.

### Release safely — terminal A, then B

In terminal A, before the 90-second safety timeout:

~~~sql
ROLLBACK;
~~~

**Expected:** ROLLBACK; terminal B's waiting UPDATE may now complete with UPDATE 1 (provided its 30-second timeout has not expired).

In terminal B, after the waiting statement returns:

~~~sql
ROLLBACK;
~~~

If B timed out, the transaction is aborted; **ROLLBACK is still required**. If A disconnected due to idle-in-transaction timeout, its uncommitted work was rolled back; reconnect only if needed for observation. Never commit either experimental UPDATE.

In terminal C:

~~~sql
SELECT id, status FROM public.incident_ch14 ORDER BY id;
SELECT application_name, state, wait_event_type,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE application_name IN ('ch14_blocker','ch14_waiter');
~~~

**Expected:** two rows with status=ready. No active blocking chain for these clients. If status differs, **stop**; inspect which session committed before any cleanup.

## 4. Read-only incident triage practice (5 minutes; terminal C)

~~~sql
SELECT pid, application_name, state, wait_event_type, wait_event,
       now()-xact_start AS transaction_age
FROM pg_stat_activity
WHERE backend_type='client backend'
ORDER BY xact_start NULLS LAST;

SELECT datname, deadlocks, conflicts, stats_reset
FROM pg_stat_database WHERE datname=current_database();

SELECT pg_is_in_recovery() AS is_standby,
       pg_size_pretty(pg_database_size(current_database())) AS db_size;

SELECT application_name, state, sync_state, replay_lag
FROM pg_stat_replication;

SELECT status, flushed_lsn, latest_end_time
FROM pg_stat_wal_receiver;

SELECT slot_name, slot_type, active, restart_lsn, wal_status
FROM pg_replication_slots;

SELECT archived_count, failed_count, last_failed_time
FROM pg_stat_archiver;
~~~

**Expected:** on a standalone local instance, replication and WAL receiver views normally return **zero rows**; the archiver view exists even if archiving is disabled. A lack of rows is **not evidence** that an HA deployment is healthy or unhealthy. Deadlocks need not increase: this experiment creates a **wait**, not a circular dependency.

In PowerShell (outside psql), inspect **container** filesystem space:

~~~powershell
docker exec pg-ir-ch14 df -h /var/lib/postgresql/data
docker stats --no-stream pg-ir-ch14
~~~

**Expected:** filesystem capacity and container resource metrics; exact values depend on Docker Desktop. This is not the same as free storage on an AWS RDS instance or Kubernetes PVC.

## 5. Incident assessment exercise (5 minutes)

Write a concise incident note for this fictional scenario:

**Symptoms:** application checkout latency rose from 80 ms to 9 s; database connections increased; one transaction stayed open while another request waited for the same row.

Record:
1. UTC time, incident ID, affected service, SLO and evidence source.
2. Which backend blocked which, using PID and application_name, and what evidence established it.
3. Whether this was a lock wait or deadlock; the relevant SQLSTATE if the waiter timed out.
4. What you would check before suggesting pg_cancel_backend or pg_terminate_backend, and who must approve.
5. Why blindly increasing max_connections or deleting WAL is unsafe.
6. Which application, pool, database, storage and replication metrics establish recovery.
7. Rollback/stop conditions and preventive work: shorter transactions, consistent ordering, alert thresholds, reviewed retry/backoff behavior.

**Do not include live SQL text, secrets, customer identifiers or patient data in shared evidence.** This is a training write-up, not a production incident declaration.

## 6. Troubleshooting and guardrails

| Symptom | Likely cause | Safe response |
|---|---|---|
| Docker daemon unavailable | Docker Desktop/WSL engine stopped | Start local engine; rerun preflight |
| Container name exists | Prior exercise or another owner's resource | Inspect; do not replace automatically |
| PostgreSQL not ready | Image initialization still in progress | Wait and retry pg_isready |
| CREATE TABLE already exists | Lab was already run | Inspect identity; do not drop blindly |
| No blocker shown | B timed out, A rolled back, or monitoring was too late | Check terminal output and session state; repeat only in isolated lab |
| Terminal B shows 55P03 | lock_timeout expired | ROLLBACK B; ROLLBACK A if still open |
| Terminal B shows 25P02 | Transaction aborted after error | ROLLBACK B before further SQL |
| Terminal A disconnected | idle-in-transaction timeout fired | Confirm rollback in C; reconnect only to observe |
| Replication view empty | Single local primary | Record not applicable; do not fabricate lag |
| Stats or PID visibility restricted | Insufficient role privileges | Request approved monitoring role; do not elevate production permissions ad hoc |
| Final status not ready | Unintended commit or different target | Stop; inspect before destructive correction |

**Prohibited in this lab:** deadlock generation, connection floods, production session termination, failover/promotion, slot removal, pg_wal deletion, vacuum full, cluster-wide config changes and cloud resource creation.

## 7. Cleanup and rollback (deliberate, isolated)

First verify terminal A and B each completed **ROLLBACK**, and terminal C sees both rows unchanged. Exit all psql clients with \q.

To preserve evidence, leave the container stopped rather than deleting it. From PowerShell:

~~~powershell
$CurrentContext = (docker context show).Trim()
$CurrentId = (docker inspect --format '{{.Id}}' pg-ir-ch14).Trim()
$Ownership = (docker inspect --format '{{index .Config.Labels "dbre.training.owner"}}' pg-ir-ch14).Trim()
docker inspect --format '{{json .Mounts}}' pg-ir-ch14
if (-not $LabContainerId -or -not $LabDockerContext -or
    $CurrentContext -ne $LabDockerContext -or
    $CurrentId -ne $LabContainerId -or
    $Ownership -ne 'chapter-14') {
    throw 'STOP: Docker context, full container ID, or training ownership does not match creation evidence.'
}
docker stop $LabContainerId
~~~

Only after confirming the container is the disposable **pg-ir-ch14** you created and no evidence is needed, optionally remove it:

~~~powershell
# Recheck context, full ID, ownership label and mounts as above immediately before removal.
# Do not run in a fresh shell without the original recorded creation values.
docker rm -v $LabContainerId
docker ps -a --no-trunc --filter "id=$LabContainerId"
~~~

**Important:** The PowerShell variables must come from the original creation session or securely retained creation record. If missing, do not reconstruct them from the current container and do not remove it. Inspect mounts and stop if any mount is shared or ownership uncertain. Record absence of the container after removal as cleanup evidence.

**Warning:** removing this container permanently discards its ephemeral database data. No host port or named external volume was created. The PostgreSQL 17 image may create an anonymous data volume, which `docker rm -v` removes only for this verified disposable container. Do not prune unrelated volumes. Do not use docker system prune, docker volume prune, or commands targeting other containers.

## 8. Acceptance and evidence checklist

- [ ] Verified local Docker context, container identity, PostgreSQL major version 17, and database identity.
- [ ] Started three independent psql sessions with no host port exposure.
- [ ] Created exactly two synthetic rows.
- [ ] Demonstrated A holding an uncommitted row lock and B waiting with a bounded timeout.
- [ ] Observed a blocking PID using pg_blocking_pids, or documented a missed observation without inventing results.
- [ ] Distinguished a lock wait from SQLSTATE 40P01 deadlock behavior.
- [ ] Rolled back both transactions and confirmed both statuses remained ready.
- [ ] Inspected connection counts, transaction age, replication views and filesystem capacity.
- [ ] Produced a sanitized incident summary, approval boundary and prevention plan.
- [ ] If executed, saved **actual** timestamps, PostgreSQL version, redacted outputs and test operator separately.
- [ ] Marked runtime validation **only after execution evidence** and independent review **only after a second reviewer approves**.

**Current evidence status:** No lab execution or independent sign-off has been performed in the course publication workflow. Expected observations above are predictions, not test results. No production certification is implied.

## Official references

- [PostgreSQL 17 monitoring statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17 viewing locks](https://www.postgresql.org/docs/17/monitoring-locks.html)
- [PostgreSQL 17 explicit locking and deadlocks](https://www.postgresql.org/docs/17/explicit-locking.html)
- [PostgreSQL 17 connection settings](https://www.postgresql.org/docs/17/runtime-config-connection.html)
- [PostgreSQL 17 client timeouts](https://www.postgresql.org/docs/17/runtime-config-client.html)
- [PostgreSQL 17 replication](https://www.postgresql.org/docs/17/runtime-config-replication.html)
