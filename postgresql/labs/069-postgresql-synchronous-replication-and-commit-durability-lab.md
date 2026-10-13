# Chapter 069 — Synchronous Replication and Commit Durability Lab

**PostgreSQL 18 · Disposable primary + two standbys · Runtime pending**

## 1. Safety and preflight

Use three disposable PostgreSQL 18 nodes with isolated PGDATA, separate ports, a verified backup and administrator access. Complete Chapter 067 primary/standby setup first. Ensure `application_name=standby_a` and `application_name=standby_b` are set on standby connections. Do not test blocking commits or stop standbys in production.

On the primary run:

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/069-synchronous-replication-inspect.sql
```

Record `pg_stat_replication` and `pg_stat_activity` baseline. Confirm both standbys are streaming.

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

**Lab only:** stop the selected synchronous standby using the lab's normal service manager. Verify whether the remaining eligible standby takes over under FIRST 1. To demonstrate a blocked commit, ensure no eligible synchronous standby is available, then in a dedicated session:

```sql
SET synchronous_commit = on;
SET statement_timeout = '5s';
INSERT INTO public.commit_probe(event_id) VALUES ('outage-test-001');
```

Observe `SyncRep` waits from another session. After the timeout, **do not blindly retry**: inspect whether the transaction committed locally. Restart a standby and confirm replication catches up. A canceled or timed-out synchronous commit can have an ambiguous client-visible outcome.

## 6. Quorum experiment

With both standbys healthy, set `synchronous_standby_names='ANY 2 (standby_a, standby_b)'` in the lab and verify `sync_state='quorum'`. Stop one standby and observe the impact using a bounded timeout. Restore both standbys.

## 7. Rollback

```sql
ALTER SYSTEM RESET synchronous_standby_names;
SELECT pg_reload_conf();
```

Confirm the prior effective value is restored (configuration precedence can override ALTER SYSTEM). Reset session-level `synchronous_commit` and verify writes and both standbys. Do not leave lab clients blocked.

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

**Runtime:** pending.
