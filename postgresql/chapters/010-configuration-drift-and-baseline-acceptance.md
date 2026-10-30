# Chapter 010 — Configuration Drift and Baseline Acceptance

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18, Linux.
**Time:** 90–120 minutes including the Module 02 acceptance exercise.
**Prerequisites:** Chapters 004 and 006–009.
**Status:** Authored and statically reviewed; actual lab execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](009-systemd-startup-shutdown-and-crash-recovery.md) · [Hands-on lab](../labs/010-configuration-drift-and-baseline-acceptance-lab.md) · [CSV capture](../scripts/010-capture-baseline.sql) · [Comparison helper](../scripts/010-compare-baseline.py) · [Diagnostic SQL](../scripts/010-drift-inspection.sql)

## 1. Operational problem and learning objectives

Two servers have the same configuration-management revision, but one behaves differently. An emergency ALTER SYSTEM change remains in place, a new application connection inherits a role override, or a restart-only setting has been edited without being activated. A file checksum cannot tell you which of these states exists.

This chapter turns installation and service-operation evidence into a reviewed baseline. You will define the comparison scope, detect drift across configuration layers, distinguish authorized exceptions from unexplained differences, and verify restoration with both configuration evidence and operational probes.

The practical outcome is a baseline acceptance report that another operator can reproduce. Matching a CSV is one gate; it does not establish security, recoverability or workload suitability on its own.

## 2. Define what “baseline” means

A baseline is an approved operational contract for a particular deployment class and instance. It includes intended values, their owner, how they take effect, and evidence that they support the workload.

| Baseline layer | Example evidence | Acceptance question |
|---|---|---|
| Build and platform | Package origin, binary/minor version, extensions, OS limits | Is this the approved and supported build? |
| Storage and initialization | Mounts, ownership, checksums, locale and encoding | Does this instance match its initialization contract? |
| Service ownership | Unit/drop-ins or cluster-manager policy | Is there one authorized lifecycle controller? |
| Cluster settings | Effective value, unit, source, restart status | Is the approved setting active through the intended layer? |
| Persistent overrides | Auto-conf entries and include files | Are emergency changes accounted for? |
| Role/database/session | Login defaults, client options and pool reset behavior | Do actual workload sessions see the approved behavior? |
| Connectivity and authentication | Endpoint, role, TLS and authentication probes | Can intended clients connect through the required controls? |
| Operational behavior | Restart, replication and representative workload evidence | Does the deployment work after a change? |

Create separate baselines for primary and standby roles, resource classes and provider tracks. Instance paths and ports may intentionally differ. Do not weaken every comparison to make those differences disappear; use an instance manifest or a reviewed template with explicit substitutions.

Each exception should name the parameter, node/role/database scope, reason, change reference, owner, expiration or review date, activation requirement and evidence. An exception without an owner becomes permanent drift.

## 3. Compare desired, persisted, active and session state

Keep four questions separate:

1. **Desired:** what does reviewed configuration management intend?
2. **Persisted:** what will the server read from files and startup arguments?
3. **Active:** what does the running instance expose?
4. **Session:** what does this particular client connection observe?

The Chapter 008 precedence rules explain why these can disagree. Start diagnosis with a fresh authenticated connection using a known client environment. Record the database, login role, endpoint and collection time separately.

Use pg_settings for effective values and provenance. Its unit column tells you how to interpret normalized numeric settings: shared_buffers expressed in 8kB units is not a number of megabytes. sourcefile visibility requires suitable privileges; missing visibility must not be treated as proof that no file contributed the value.

A pending_restart value identifies a startup-only setting changed in the file but not yet activated. It deserves a separate acceptance gate even when the active value still matches the baseline.

Use pg_file_settings to inspect the current file contents and ordering. Its applied field does not certify that the running server has adopted a value: it describes whether that entry can contribute when the files are processed. Overridden entries and invalid entries require different interpretations. Check the error column, order, logs and active value together.

Role/database defaults are catalog state, not ordinary file entries. pg_db_role_setting exposes their scopes. A role-in-database exception can affect only one application path while an observer session appears normal. Inspect new application sessions as well as the administrative observer.

## 4. The bounded comparison helper

The accompanying capture SQL exports a deliberately small PostgreSQL 18 settings set:

- Connection profile: server_version, port and listen_addresses. The disposable data directory is verified separately using the Chapter 004 administrator/OS guard; it is not part of low-privilege app or observer CSV captures because configuration-path visibility may be restricted.
- Capacity: shared_buffers, max_connections and work_mem.
- Durability/replication: fsync, full_page_writes, synchronous_commit, wal_level and synchronous_standby_names.
- Logging: log_min_duration_statement.

The CSV includes the setting, unit, context, source, source file, pending-restart flag, major version and recovery role. It omits timestamps and process start time because these change normally; retain them in the evidence report. It deliberately omits connection strings, passwords and broad dumps of every setting.

Run capture in a fresh session, with quiet psql output and errors kept separate from CSV:

~~~bash
psql -X -q -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 \
  -U lab_observer -d ops_lab -f scripts/010-capture-baseline.sql \
  > "$PG_LAB_ROOT/evidence-010/observed.csv"
python3 scripts/010-compare-baseline.py \
  "$PG_LAB_ROOT/evidence-010/approved-observer.csv" \
  "$PG_LAB_ROOT/evidence-010/observed.csv"
~~~

Run this after the lab guard and evidence-directory preparation. Capture failure makes the snapshot invalid: do not approve a partial file.

The helper rejects malformed, empty, duplicate or incomplete input. It requires every allowlisted setting, PostgreSQL major 18 and consistent instance metadata. A baseline with a pending restart is rejected rather than silently accepted. It then compares fields exactly and fails if the current snapshot has any pending restart.

| Exit code | Meaning | Operator action |
|---|---|---|
| 0 | Selected fields match and no selected pending restart | Continue other acceptance gates |
| 1 | Drift or pending restart detected | Diagnose and classify |
| 2 | Bad input or unapproved baseline structure | Fix collection or baseline review |

The helper reads two local files and cannot change PostgreSQL. It is not a general configuration parser. It does not check every setting, persistent-but-inactive reloadable changes, invalid file entries, HBA behavior, credentials, role defaults outside the sampled login, minor versions, extensions or host state. Those remain explicit report items.

Do not generate an “approved” file from an incident node simply because it is reachable. First reconcile it with the desired deployment contract and review its provenance. Updating the baseline is a controlled change, not a way to suppress a failing comparison.

## 5. Diagnose differences before remediation

Run the diagnostic SQL as the lab administrative role, or an approved read-only monitoring role with sufficient access. It contains bounded metadata reads and no corrective SQL. File inspection views may require elevated privileges.

The report includes all pending-restart parameters, file errors/overrides for the selected settings, role/database defaults and authentication-file parse errors. The all-settings pending-restart check complements the comparison helper's smaller scope.

| Difference | Likely explanation | Verification |
|---|---|---|
| Same effective value, different source | An override duplicates the desired value | Inspect source file/catalog and decide who owns it |
| Active value differs from desired file | Higher-precedence layer, no reload or session override | Check startup arguments, auto-conf and fresh-session source |
| Active value matches; pending_restart is true | A future restart will activate another value | Inspect current file entry and planned restart |
| Observer matches; application differs | Role/database/client/session settings | Reconnect as the actual login and inspect defaults |
| File entry exists but applied=false | Superseded entry or invalid setting | Read error and ordering; do not delete blindly |
| File parse errors but server healthy | Running state predates bad persisted contents | Repair files before risking restart |
| Everything matches but latency regresses | Workload, plan, storage or concurrency change | Use performance evidence; configuration equality is not causality |

A true pg_reload_conf() result confirms the reload signal was sent, not that every proposed setting became effective. Check fresh observations and logs. Reload delivery can be asynchronous; use a bounded observation window before deciding it failed.

## 6. Remediate the owning layer

Find the layer that introduced drift and reconcile it with the approved source of truth. If configuration management owns a file, correct its desired definition and deployment. If an emergency ALTER SYSTEM entry is no longer needed, remove that specific entry and verify the lower-precedence value. Do not reset every auto-conf setting to remove one exception.

ALTER SYSTEM changes a file outside transactional rollback and must not run inside a transaction block. A compensating reset is a new change. Preserve the old value and source before executing it.

For role/database drift, restore the exact affected scope and reconnect clients as required. A reset removes that scoped override; it does not restore an arbitrary previously overwritten value. Before resetting, establish whether an override originally existed.

For restart-only changes, choose between reverting the persisted proposal or activating it through the authorized lifecycle owner. Do not restart solely because a comparison script returned nonzero. Check topology, application impact, HA automation and the change window first.

After correction, collect new snapshots, inspect file errors and all pending-restart flags, reconnect workload sessions, and verify replication and application probes. The corrective command's successful exit is not the acceptance result.

## 7. Module 02 baseline acceptance

The lab introduces three independent drift cases and restores each: a reloadable logging override, a client-session memory override, and a restart-only proposal. It then rehearses a failed start caused by a deliberately invalid setting in the guarded disposable primary and restores the saved configuration.

The final acceptance report brings together Chapters 006–010:

| Gate | Retained evidence | Pass condition |
|---|---|---|
| Installation/layout | Binary/version, package track, paths and service owner | Matches approved deployment contract |
| Initialization | Checksum state, locale, encoding and ownership | Matches the selected instance contract |
| Configuration | Desired definition, snapshots, diagnostic output | Explained provenance; no file errors or unresolved pending restart |
| Lifecycle | Clean stop/start and failed-start recovery evidence | Correct instance returns without competing supervisors |
| Connectivity | Fresh observer and application logins | Correct endpoint, roles and bounded probe results |
| Replication | Two senders and probe replay in Chapter 004 lab | Expected primary/standby roles and replicated probe |
| Change hygiene | Exception register and restored baseline | Test changes removed; production exceptions owned |
| Evidence quality | Times, commands, actual output and reviewer | Reproducible; execution gaps explicitly recorded |

Mark a gate pending if no execution evidence exists. A skipped systemd host test is “not applicable” only for a manual-lab deployment; it is still required for a production systemd deployment's own acceptance.

## 8. Production rollout and stop conditions

Collect drift read-only before scheduling remediation. Compare nodes by deployment role, correlate with recent changes, and determine application impact. Review each correction with its owner and apply it to one appropriate canary or maintenance target first.

Stop if identity is uncertain, the baseline has not been approved, file errors remain unexplained, the topology differs from expectations, a critical durability setting changed, or multiple writers are modifying configuration concurrently. Preserve current and desired evidence. Avoid auto-remediation that races a cluster manager or undoes an active emergency mitigation.

Monitor unexpected value/source changes, overdue exceptions, restart-only proposals, file errors, restart frequency, authenticated probes and replication health. Route urgent durability or connectivity differences differently from harmless formatting differences. Frequency and thresholds should reflect the deployment's change cadence and SLOs.

Baseline revisions need the reason, owner, scope, version compatibility, rollback boundary and workload evidence. Keep sensitive snapshots in access-controlled storage; publish only reviewed, sanitized examples.

## 9. Official references and next chapter

This chapter uses the latest stable documentation baseline currently published as PostgreSQL 18. Check version-specific fields and privileges for older versions and provider restrictions.

- [Setting parameters and configuration layers](https://www.postgresql.org/docs/18/config-setting.html)
- [pg_settings](https://www.postgresql.org/docs/18/view-pg-settings.html)
- [pg_file_settings](https://www.postgresql.org/docs/18/view-pg-file-settings.html)
- [pg_db_role_setting](https://www.postgresql.org/docs/18/catalog-pg-db-role-setting.html)
- [ALTER SYSTEM](https://www.postgresql.org/docs/18/sql-altersystem.html)
- [Authentication files](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)
- [pg_ctl](https://www.postgresql.org/docs/18/app-pg-ctl.html)

**Next:** Chapter 011 — Roles, Ownership, Membership and Least Privilege.
