# Chapter 069 — Synchronous Replication and Commit Durability Lab

**PostgreSQL 18 · Disposable primary + two standbys · Runtime pending**

## 1. Safety and preflight

Use three disposable PostgreSQL 18 nodes with isolated PGDATA, separate ports, a verified backup and administrator access. Complete Chapter 067 primary/standby setup first. Ensure `application_name=standby_a` and `application_name=standby_b` are set on standby connections. Do not test blocking commits or stop standbys in production.

On the primary run:

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/069-synchronous-replication-inspect.sql
```

Record `pg_stat_replication` and `pg_stat_activity` baseline. Confirm both standbys are streaming. **Before any ALTER SYSTEM**, capture the original effective value, its configuration source and all rows for `synchronous_standby_names` in `pg_file_settings` (including whether `postgresql.auto.conf` currently sets it):

~~~sql
SELECT name,setting,source,sourcefile,sourceline
FROM pg_settings WHERE name='synchronous_standby_names';
SELECT sourcefile,name,setting,applied,error
FROM pg_file_settings WHERE name='synchronous_standby_names';
~~~

Store the original exact value and ownership in the private lab log. If a configuration manager owns it, use that manager for any lab configuration changes.

## 2. Fixture and baseline

On the disposable primary:

```sql
CREATE DATABASE ch069_lab;
```

Connect to ch069_lab:

```sql
CREATE TABLE public.commit_probe (
  event_id text PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
SET synchronous_commit = local;
INSERT INTO public.commit_probe(event_id) VALUES ('baseline-001');
```

Use client timing (`\timing on`) and capture latency over multiple transactions. A single commit time is not a reliable percentile.

## 3. Configure synchronous candidates

In an authorized lab administrator session on the primary:

```sql
ALTER SYSTEM SET synchronous_standby_names = 'FIRST 1 (standby_a, standby_b)';
SELECT pg_reload_conf();
```

Verify the effective setting and that an eligible standby has `sync_state='sync'`. Record any pending-restart state and configuration precedence; if an external config manager owns the setting, change it through that manager instead.

## 4. Compare acknowledgment levels

Run the following separately in a client session, recording p50/p95/p99 over repeated small transactions:

```sql
SET synchronous_commit = remote_write;
INSERT INTO public.commit_probe(event_id) VALUES ('remote-write-001');
SET synchronous_commit = on;
INSERT INTO public.commit_probe(event_id) VALUES ('sync-on-001');
SET synchronous_commit = remote_apply;
INSERT INTO public.commit_probe(event_id) VALUES ('remote-apply-001');
```

Repeat with unique IDs to build useful latency samples. Capture standby `write_lsn`, `flush_lsn` and `replay_lsn`.

## 5. Controlled standby outage

**Lab only:** stop the selected synchronous standby using the lab's normal service manager. Verify whether the remaining eligible standby takes over under FIRST 1. To demonstrate a blocked commit, ensure no eligible synchronous standby is available. Use the **single, bounded client invocation below**, not an unbounded stand-alone `psql` session.

Observe `SyncRep` waits from another session, but **do not rely on `statement_timeout` as a guaranteed client deadline for a synchronous-commit acknowledgement wait**. In the isolated Linux lab, separately bound the entire `psql` process with an operating-system client deadline, for example:

~~~bash
# Verified disposable PostgreSQL 18 endpoint only. Do not use in staging/production.
timeout --signal=TERM --kill-after=3s 9s \
  psql -X -v ON_ERROR_STOP=1 -h VERIFIED_LAB_PRIMARY -p VERIFIED_LAB_PORT \
    -U VERIFIED_LAB_ROLE -d ch069_lab \
    -c "SET statement_timeout='2000ms'" \
    -c "BEGIN; SET LOCAL synchronous_commit=on; INSERT INTO public.commit_probe(event_id) VALUES ('outage-test-unique-001'); COMMIT"
~~~

The timeout/termination is a **client-observed failure, not proof of transaction rollback**: PostgreSQL may already have committed locally while waiting for synchronous acknowledgement. In a separate observer session, verify `pg_stat_activity.wait_event='SyncRep'`, capture the client exit code, restore the disconnected standby, and reconcile the **unique event ID** on the primary and recovered standbys before deciding whether any idempotent retry is safe. A missing acknowledgement must not be interpreted as a missing row. The [actual disposable PG18 V03 test](../validation/V03-CH067-070-STREAMING-SYNC-EVIDENCE.md) confirmed this behavior with a separately bounded client and independently observed `SyncRep` wait. Do not run this test without a controlled disposable environment, validated rollback, and an authorized lab operator.

## 6. Quorum experiment

With both standbys healthy, set `synchronous_standby_names='ANY 2 (standby_a, standby_b)'` in the lab and verify `sync_state='quorum'`. Stop one standby and observe the impact using a bounded timeout. Restore both standbys.

## 7. Rollback — restore the exact previous configuration

**Do not run an unconditional `ALTER SYSTEM RESET synchronous_standby_names`.** If a value existed in `postgresql.auto.conf` before the exercise, RESET discards it rather than restoring it. Likewise, a config manager can override what ALTER SYSTEM changes.

Using the snapshot captured in Step 1, have the authorized lab administrator restore **the original exact configuration in the same owning layer**. If the parameter was absent from `postgresql.auto.conf` before the lab, the administrator may remove only the temporary lab override; if it was already present, restore its exact original value. If managed externally, revert through the configuration manager. Reload and recheck the effective setting, its `source`, `sourcefile`, `sourceline`, and all relevant `pg_file_settings` records. Document successful restoration and compare against the snapshot; a missing snapshot means **NO_GO**, not assumed success.

Reset the client session-level `synchronous_commit`, confirm writes and both standby connections, and check for blocked sessions. **Do not leave lab clients blocked.**

## 8. Acceptance

| Gate | Expected | Status |
|---|---|---|
| Both standbys connected | Streaming and named correctly | Pending |
| FIRST 1 selection | Eligible sync standby selected | Pending |
| remote_write/on/remote_apply | Latency and LSN evidence | Pending |
| Standby outage | Blocking/fallback behavior observed | Pending |
| Ambiguous commit handling | Idempotent reconciliation documented | Pending |
| Quorum mode | ANY 2 requires two acknowledgments | Pending |
| Rollback | Original effective configuration restored | Pending |
| Production isolation | No production endpoints changed | Pending |

**Disposable runtime evidence:** The [streaming and synchronous-commit runtime test](../validation/V03-CH067-070-STREAMING-SYNC-EVIDENCE.md) passed **42/42 checks** in an isolated PostgreSQL 18 container, including FIRST 1, ANY 2, a `SyncRep` wait, separate client deadline, transaction reconciliation and exact default-configuration restoration. This is not an independent-host HA test, a business latency/SLO benchmark or enterprise certification; full acceptance remains **PENDING**.

**Runtime:** pending.
