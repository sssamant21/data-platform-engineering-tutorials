# 008 — Configuration Precedence, Reloads and Restarts

[Master plan](../MASTER-PLAN.md) · [Previous chapter](007-initialization-checksums-locale-and-encoding.md) · [Hands-on lab](../labs/008-configuration-precedence-reload-restart-lab.md) · [Inspection SQL](../scripts/008-configuration-inspection.sql)

## 1. Operational problem and objectives

A configuration file can contain the intended value while a session uses another value. A reload can return success while a restart-only setting remains pending. Restoring one file may leave an ALTER SYSTEM override or role default in effect.

DBRE/SRE operators must inspect both the requested configuration and the running session, then prove the chosen activation and rollback path.

**Reference:** PostgreSQL 18. **Prerequisite:** Chapter 004's disposable three-instance lab and Chapters 005–007. **Effort:** 60–90 minutes. Persistent changes and restarts belong only to the lab in this chapter.

After the lab you should distinguish sources, identify activation context, apply reloadable changes, verify a restart-required change and restore every modified layer.

## 2. Configuration sources and precedence

For settings that permit these scopes, increasing precedence is broadly:

| Layer | Example | Activation/scope |
|---|---|---|
| Built-in default | Compiled default | Base value |
| Main file/includes | postgresql.conf and ordered includes | Context determines activation |
| ALTER SYSTEM file | postgresql.auto.conf | Overrides the main configuration file |
| Server command line | postgres -c | Overrides file sources |
| Database default | ALTER DATABASE SET | New sessions in that database |
| Role default | ALTER ROLE SET | New sessions for that login |
| Role-in-database default | ALTER ROLE IN DATABASE SET | New matching sessions |
| Client startup options | PGOPTIONS/options | That connection |
| Session SQL | SET | That session |
| Transaction-local SQL | SET LOCAL | Within the transaction |

This table does not grant authority to change a setting or bypass startup-only restrictions. Context and privileges still control which layers are valid.

Within a file, later entries can supersede earlier entries. Included configuration is processed at its include position; include_dir files follow the documented filename ordering. postgresql.auto.conf is another source, not a replacement copy of the main file.

A connection pool can preserve old backend-session defaults until it reconnects or explicitly resets them. Changing a login default does not rewrite already-open sessions.

## 3. Inspect the effective setting

~~~sql
SELECT name, setting, unit, context, source,
       reset_val, sourcefile, sourceline, pending_restart
FROM pg_catalog.pg_settings
WHERE name IN ('statement_timeout','log_min_duration_statement','shared_buffers')
ORDER BY name;
~~~

Interpretation:

| Field | Operational meaning |
|---|---|
| setting/unit | Current session value and implicit unit |
| context | Permitted activation/change context |
| source | Winning source for this session |
| reset_val | Value RESET would restore in this session |
| sourcefile/sourceline | Origin where visible/applicable |
| pending_restart | File-driven change awaiting restart |

reset_val is not automatically the factory default. A session RESET can return to a login/database-derived default.

sourcefile may be null because the source is not a file or because access is restricted. Do not conclude “no override” from a null without reviewing visibility.

## 4. Context determines activation

| Typical context | Operational treatment |
|---|---|
| internal | Not an ordinary configurable setting |
| postmaster | Requires server restart |
| sighup | Reload configuration |
| backend / superuser-backend | Backend-start restrictions; reconnect and check permissions |
| user / superuser | Can support session changes, subject to privilege |

Use pg_settings for the actual parameter and PostgreSQL version. Do not classify by the parameter's name alone.

For this lab, log_min_duration_statement is reloadable and shared_buffers requires restart. statement_timeout can be changed locally for a session/transaction.

Reload does not disconnect all clients and is not a restart. Restart interrupts connections and can roll back active transactions depending on shutdown mode.

## 5. File intent versus running state

~~~sql
SELECT sourcefile, sourceline, name, setting, applied, error
FROM pg_catalog.pg_file_settings
WHERE name IN ('log_min_duration_statement','shared_buffers')
   OR error IS NOT NULL
ORDER BY seqno;
~~~

This view inspects current file contents, not merely the last successfully activated configuration. It can support preflight review, but does not replace activation/log checks or guarantee successful startup.

An unapplied entry may be superseded, invalid or otherwise not applicable. Read error and ordering context; applied=false alone is not proof of syntax failure.

Some file parse errors affect more than one setting. Stop on errors rather than testing a restart blindly.

The view is privileged by default. Use an authorized administrative connection for file diagnostics; do not give monitoring users broad privileges simply to avoid an access error.

## 6. ALTER SYSTEM versus session defaults

ALTER SYSTEM writes persistent settings to postgresql.auto.conf. It is not a session SET and cannot be used inside a transaction block.

~~~sql
ALTER SYSTEM SET log_min_duration_statement='1000ms';
SELECT pg_reload_conf();
~~~

The reload function signals configuration reload; its true result is not confirmation that every requested value has become effective. Inspect a fresh session, pg_settings and logs afterward.

ALTER SYSTEM RESET removes that named override. It does not universally restore all sources. A lower-priority file, command-line option or login default may then become effective.

Avoid RESET ALL during rollback of a single-setting change: it can remove unrelated configuration. Restore only the layers owned by the change.

Declarative operators and managed services can own configuration differently or reject ALTER SYSTEM. Use their supported control path instead of creating drift.

## 7. Database, role and transaction behavior

Database/role defaults apply at connection startup. Test with a new connection, not SET ROLE in an existing session.

Example on the disposable lab:

~~~sql
ALTER ROLE lab_app IN DATABASE ops_lab SET statement_timeout='9s';
~~~

A new matching connection should report 9s. An already connected application backend retains its earlier default unless separately changed.

Within that new session:

~~~sql
SET statement_timeout='7s';
BEGIN;
SET LOCAL statement_timeout='2s';
SHOW statement_timeout;
ROLLBACK;
SHOW statement_timeout;
RESET statement_timeout;
SHOW statement_timeout;
~~~

Expected sequence: 2s inside the transaction, 7s after rollback and 9s after RESET. The transaction-local value does not overwrite the session or login default.

## 8. Restart procedure

A postmaster-context change requires:

1. Approved window and client impact review.
2. Baseline/settings-source capture.
3. Valid file contents and resource feasibility.
4. Correct service/instance identity.
5. Controlled shutdown/start using the owning supervisor.
6. Authenticated SQL and application verification.
7. Topology and replication verification.

In the manual Chapter 004 lab, pg_ctl owns lifecycle. A systemd/operator-managed deployment must use its supported supervisor.

Do not issue a direct restart to an operator-managed process and expect the control plane to remain consistent. Changing one primary's file does not automatically update its standbys.

A failed start needs logs and restored valid configuration, not repeated restarts or removing internal database files.

## 9. Rollback and monitoring

Keep a change record covering previous effective values, persistent overrides, login defaults, source files and exact modified layers.

| Change layer | Rollback boundary |
|---|---|
| SET LOCAL | Transaction end |
| Session SET | RESET or session close, respecting baseline defaults |
| Role/database default | Restore original default; reconnect affected sessions |
| ALTER SYSTEM | Remove or restore named override; reload/restart as context requires |
| File edit | Restore reviewed content; activate appropriately |
| Restart-only parameter | May need a second restart for full baseline restoration |

Verification must cover both the requested rollback and effective session value. pending_restart should clear after the intended final restart.

Monitor reload errors, restart timing, startup failures, changed application latency and unexpected disconnects. No alert should treat successful signal delivery as configuration acceptance.

## 10. Troubleshooting and acceptance

| Symptom | Safe next check |
|---|---|
| File changed; session did not | Source precedence, session override and activation context |
| Reload true; value unchanged | File errors, restart requirement and overriding sources |
| Role default not visible | New matching login/database session and client options |
| RESET produces unexpected value | reset_val and startup default layers |
| pending_restart remains | Correct instance, valid file value and actual restart |
| Rollback still differs | Hidden auto.conf, role/database or command-line override |
| Operator reverses change | Declarative source of truth |

Complete the lab with before/change/rollback evidence and successful replication verification. Lab execution must be recorded separately from static review.

**Next:** Chapter 009 — systemd, Startup, Shutdown and Crash Recovery.

## 11. Official references

- [Setting parameters](https://www.postgresql.org/docs/18/config-setting.html)
- [ALTER SYSTEM](https://www.postgresql.org/docs/18/sql-altersystem.html)
- [pg_settings](https://www.postgresql.org/docs/18/view-pg-settings.html)
- [pg_file_settings](https://www.postgresql.org/docs/18/view-pg-file-settings.html)
- [ALTER ROLE](https://www.postgresql.org/docs/18/sql-alterrole.html)
- [ALTER DATABASE](https://www.postgresql.org/docs/18/sql-alterdatabase.html)
- [SET and SET LOCAL](https://www.postgresql.org/docs/18/sql-set.html)
- [pg_ctl](https://www.postgresql.org/docs/18/app-pg-ctl.html)
- [Administrative functions](https://www.postgresql.org/docs/18/functions-admin.html)
