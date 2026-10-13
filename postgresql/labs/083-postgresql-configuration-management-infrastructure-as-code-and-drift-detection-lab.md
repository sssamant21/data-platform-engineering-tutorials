# Chapter 083 — Configuration Management, Infrastructure as Code and Drift Detection Lab

**PostgreSQL 18 · Disposable cluster only · Runtime pending**

## 1. Safety and setup

Use a disposable PostgreSQL 18 instance. Keep a separate privileged session and known-good configuration. Do not change production `max_connections`, `shared_buffers`, `wal_level`, TLS or replication settings to simulate drift.

## 2. Capture desired and effective state

Copy [083 baseline](../labs/acceptance/083-configuration-baseline.csv) into a lab-specific reviewed declaration. Run [083 inspection SQL](../labs/sql/083-configuration-drift-inspect.sql). Record PostgreSQL version, source, units, context, pending restart and UTC time.

## 3. Create a controlled drift

As a lab administrator, first record the original `log_min_duration_statement` value and source. Execute:

```sql
ALTER SYSTEM SET log_min_duration_statement = '250ms';
SELECT pg_reload_conf();
```

Reconnect and verify `pg_settings` reports the new value, source and pending restart status. Compare to the baseline expected value. Note: this lab uses a reloadable logging parameter to avoid a restart; it may increase logging volume.

## 4. Diagnose the source

Inspect `pg_settings.source`, `pg_file_settings` and `pg_db_role_setting`. Confirm the drift originates from `postgresql.auto.conf` / ALTER SYSTEM and is not a role/session override. Capture the difference in a change ticket.

## 5. Remediate and verify

For a disposable cluster with no other owner of the setting, use:

```sql
ALTER SYSTEM RESET log_min_duration_statement;
SELECT pg_reload_conf();
```

Verify that the original configuration-file value is active and that no unexpected pending restart remains. If the initial source was already `postgresql.auto.conf`, do **not** use RESET as rollback: restore its original value instead. In managed/operator environments, apply changes through the authoritative controller.

## 6. Restart-required tabletop

Inspect `shared_buffers` context and `pending_restart` without changing it. Document HA-safe rolling restart, replica health checks and rollback. Do not force a restart just to complete this lab.

## 7. Acceptance

Complete [083 scorecard](../labs/acceptance/083-configuration-drift-scorecard.csv). Mark any unexecuted IaC deployment, multi-node comparison or restart test NOT VERIFIED. Preserve redacted evidence and clean up lab-only changes.

**Runtime:** pending.
