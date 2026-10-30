-- LAB ONLY. Signals are irreversible by SQL ROLLBACK.
-- Caller must first run the Chapter 020 shell guard and preview the target.
-- All -v variables are mandatory: action, confirm, target_pid,
-- target_start, target_state, target_query_start, target_app, expected_system_id.
-- action is cancel or terminate; confirm must be yes.
-- Zero rows means refused/not matched, not success. Never retry blindly.
\set ON_ERROR_STOP on
\pset pager off
\if :{?expected_system_id}
\else
  \echo 'Missing independently observed disposable cluster system identifier'
  SELECT 1/0;
\endif
\if :{?action}
\else
  \echo 'Missing action'
  SELECT 1/0;
\endif
\if :{?confirm}
\else
  \echo 'Missing confirm'
  SELECT 1/0;
\endif
\if :{?target_pid}
\else
  \echo 'Missing target_pid'
  SELECT 1/0;
\endif
\if :{?target_start}
\else
  \echo 'Missing target_start'
  SELECT 1/0;
\endif
\if :{?target_state}
\else
  \echo 'Missing target_state'
  SELECT 1/0;
\endif
\if :{?target_query_start}
\else
  \echo 'Missing target_query_start'
  SELECT 1/0;
\endif
\if :{?target_app}
\else
  \echo 'Missing target_app'
  SELECT 1/0;
\endif
SET statement_timeout = '8s';
SET lock_timeout = '1s';
SET TIME ZONE 'UTC';
-- CASE evaluates only the selected function arm. Filters never broaden a target.
SELECT clock_timestamp() AS action_at, a.pid, a.backend_start,
       a.application_name, a.state, a.query_start, :'action' AS requested_action,
       CASE :'action'
         WHEN 'cancel' THEN pg_cancel_backend(a.pid)
         WHEN 'terminate' THEN pg_terminate_backend(a.pid, 3000)
       END AS signal_result
FROM pg_stat_activity a
JOIN pg_roles r ON r.oid = a.usesysid
WHERE current_database() = 'ops_lab'
  AND current_user = 'lab_admin'
  AND inet_server_addr() = inet '127.0.0.1'
  AND inet_server_port() = 55432
  AND current_setting('data_directory') LIKE '/tmp/postgresql-dbre-lab.%/primary'
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text = :'expected_system_id')
  AND NOT pg_is_in_recovery()
  AND current_setting('server_version_num')::int BETWEEN 180000 AND 189999
  AND :'confirm' = 'yes'
  AND :'action' IN ('cancel','terminate')
  AND a.pid = :'target_pid'::integer AND a.pid > 0
  AND a.pid <> pg_backend_pid()
  AND a.backend_start = :'target_start'::timestamptz
  AND a.query_start = :'target_query_start'::timestamptz
  AND a.state = :'target_state'
  AND a.application_name = :'target_app'
  AND a.application_name IN ('c020_A','c020_B','c020_C')
  AND a.datname = 'ops_lab' AND a.usename = 'lab_app'
  AND a.backend_type = 'client backend' AND NOT r.rolsuper
  AND (:'action' <> 'cancel' OR a.state = 'active');
