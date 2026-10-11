# Chapter 009 — systemd, Startup, Shutdown and Crash Recovery

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18 on Linux.
**Time:** 60–90 minutes plus evidence review.
**Prerequisites:** Chapters 004, 006, 007 and 008.
**Status:** Authored and statically reviewed; lab execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](008-configuration-precedence-reloads-and-restarts.md) · [Hands-on lab](../labs/009-service-lifecycle-and-crash-recovery-lab.md) · [Inspection SQL](../scripts/009-lifecycle-inspection.sql)

## 1. Operational problem and objectives

An application reports connection failures after maintenance. The service wrapper says active, but the database is still recovering. Another operator starts PostgreSQL manually, while the supervisor is attempting a restart. A third operator deletes a PID file to get past an error. Each action can make an ordinary service incident harder to resolve.

By the end of this chapter, you can identify the owner of a PostgreSQL process, distinguish service state from database readiness, choose a shutdown mode deliberately, and follow crash recovery without repeatedly interrupting it. You can also collect evidence that clients reconnected, transactions behaved as expected and replication resumed.

The chapter covers self-managed Linux services. For managed databases, the provider controls the host lifecycle. For an HA deployment, the cluster manager may control PostgreSQL: follow its maintenance and fencing procedure before changing the service.

## 2. Establish one lifecycle owner

Use the package service manager for a packaged deployment, the cluster manager for an HA deployment, and the Chapter 004 script for its disposable instances. Record the control path in the runbook. Mixing control paths can produce restart races and incorrect supervisor state.

The PostgreSQL server runs under its dedicated unprivileged operating-system identity. Root may administer systemd, but must not launch the database server as root. Verify the binary version, data directory, configuration path and process identity together; a port number alone is insufficient identification.

| Layer | Evidence | What it establishes |
|---|---|---|
| Service definition | Unit file, drop-ins, ExecStart and ExecStop | Intended binary, identity and lifecycle commands |
| Supervisor runtime | ActiveState, SubState, MainPID and Result | What the service manager believes happened |
| PostgreSQL process | Process command line and data directory | Which instance actually runs |
| Database connection | Server version, start time, role and settings | Whether the intended instance accepts SQL |
| Workload | Bounded representative transaction | Whether users can perform the required operation |
| Replication | Sender state and standby probe visibility | Whether downstream operation resumed |

A distribution may supply an umbrella unit whose active state does not describe an individual database instance. A unit enabled for boot may be stopped now; a running unit may be disabled for boot. Record both properties, then test the database.

## 3. Inspect systemd without changing the service

This exercise is optional on a host without systemd. On a systemd host, discover units before selecting one:

~~~bash
systemctl --version
systemctl list-unit-files 'postgresql*' --no-pager
systemctl list-units --all 'postgresql*' --no-pager
~~~

Set the exact instance unit discovered on your host. The following name is an example, not a portable default:

~~~bash
PG_UNIT='postgresql@18-main.service'
systemctl show "$PG_UNIT" \
  -p Id -p LoadState -p ActiveState -p SubState -p MainPID \
  -p User -p ExecStart -p ExecStop -p Restart -p Result \
  -p TimeoutStartUSec -p TimeoutStopUSec -p KillMode
systemctl cat "$PG_UNIT"
journalctl -u "$PG_UNIT" --since '30 minutes ago' \
  --no-pager -n 100 -o short-iso
~~~

Read-only inspection may still require journal permissions. Unit definitions, arguments and logs can contain sensitive information; redact evidence before sharing it. Database logs may be redirected to files or the logging collector rather than appearing fully in the journal.

Check the installed host manuals because properties and package integration depend on the systemd and distribution versions. Treat upstream systemd documentation as a reference, not proof of the installed unit's behavior.

Important distinctions:

- PostgreSQL configuration reload and systemd daemon reload affect different configuration layers. Editing a service drop-in requires the service manager to reread its unit definition; this does not apply PostgreSQL settings.
- A service restart includes a stop and a start. Determine the effective stop mode from the unit or wrapper, rather than assuming it is fast.
- Type=notify requires PostgreSQL built with systemd support. A copied unit can wait for a readiness notification that an incompatible binary never sends.
- Startup and stop timeouts, restart policy and kill behavior must accommodate the deployment. A recovery operation can exceed an ordinary startup duration. Evaluate measured recovery time and escalation needs before changing timeouts.
- Automatic restart is useful only with bounded retry and actionable alerting. Repeated recovery interruption can prolong an outage.

This chapter does not install a second supervisor around the Chapter 004 instances.

## 4. Startup is a sequence of operational checks

Before starting an instance, verify storage mounts, ownership, free space, configuration validity, expected binary and absence of a conflicting server. Reconcile an existing PID file with the actual process and its start time. PostgreSQL uses the PID file to protect its data directory; removing it is not a first-line repair.

Capture server output. In the manual lab, the established control command is:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" \
  -l "$PG_LAB_ROOT/logs/primary.log" -w -t 30 start
~~~

Execute this only after the lab guard described in the exercise, and only when the server is confirmed stopped. A wait timeout reports that the caller did not observe completion within its budget. It does not prove that the server has exited. Inspect status and logs before issuing another start.

The readiness chain is: process exists, PostgreSQL completes startup or recovery, a client authenticates to the intended endpoint, and a representative operation succeeds. A standby can be ready for permitted reads while still reporting recovery. For this lab, the primary must report pg_is_in_recovery() = false, and both standbys must report true.

pg_isready helps distinguish accepting, rejecting and unreachable endpoints. It is not an authenticated workload test, a durability test or proof that the endpoint is the expected primary.

## 5. Shutdown modes and transaction consequences

Choose the mode according to the maintenance objective and client impact. PostgreSQL implements these signals at the supervisor process; do not reproduce them by killing arbitrary backend processes.

| Mode | pg_ctl option | Server signal | Operational behavior | Next start |
|---|---|---|---|---|
| Smart | -m smart | SIGTERM | Rejects new connections and waits for existing sessions to end | Clean startup after shutdown finishes |
| Fast | -m fast | SIGINT | Disconnects sessions, aborts active transactions and shuts down cleanly | Clean startup |
| Immediate | -m immediate | SIGQUIT | Terminates without normal clean shutdown | Crash recovery required |

Fast is normally appropriate for a coordinated maintenance interruption when clients can reconnect and retry safely. Smart can be held open by an idle connection pool, so drain pools and bound the operator's wait. A timeout from pg_ctl does not withdraw a smart shutdown request: new connections remain rejected while existing sessions finish.

Immediate is deliberate failure injection in this disposable lab. It is not a routine method to speed up maintenance. SIGKILL bypasses orderly PostgreSQL signal handling; do not use it as the default response to a slow stop. If a production process cannot stop, escalate with process, storage and supervisor evidence before taking exceptional action.

After any disconnect, clients need new sessions. An application that loses its connection around COMMIT may not know whether the transaction committed. Safe retries require application-specific idempotency or reconciliation; blindly resubmitting a payment or job is unsafe.

## 6. What crash recovery proves

PostgreSQL uses WAL to bring persistent database state to a consistent condition after an unclean shutdown. Recovery processes WAL as needed and resolves transaction visibility. A transaction that never committed must not become visible merely because some of its changes reached disk.

In the lab, commit one identifiable row with synchronous_commit on, leave a second insert uncommitted, interrupt the primary, then check both rows after startup. With the baseline durability settings and functioning storage, the acknowledged committed row should remain visible and the unfinished row should be absent.

This is a process-crash experiment. It does not simulate power loss, damaged storage, lost WAL, point-in-time restore or host loss. It does not prove remote durability: the two lab standbys replicate asynchronously. Do not infer an HA RPO from recovery of the same primary.

Keep fsync and full_page_writes enabled. Disabling durability settings changes what the test can establish. Recovery duration depends on WAL work, checkpoint history and storage performance; the tiny lab is not a production RTO estimate.

Log messages may include interrupted shutdown, recovery/redo work and readiness. Exact wording varies. A very small experiment may show little redo work. Record the messages actually observed rather than inventing expected log lines.

## 7. Production maintenance and incident procedure

1. Identify the instance, lifecycle owner, deployment topology and authorized change window. Confirm backup/recovery readiness and application retry behavior.
2. Record role, version, start time, replication state, client errors and current supervisor configuration. Establish an external application probe.
3. Drain or pause traffic as required. Confirm HA automation will not conflict with the maintenance operation.
4. Use the approved owner to request the planned shutdown mode. Watch client impact and the database log, not just the command's exit code.
5. Start through the same owner. If startup exceeds its budget, examine process state, recovery progress and storage evidence.
6. Verify authenticated SQL, intended primary/standby roles, representative transactions, replication and application reconnection.
7. End maintenance only after signals stabilize. Retain outage timestamps and unresolved differences.

**Stop conditions:** uncertain instance identity, unexpected writable node, missing data mount, storage errors, conflicting lifecycle owners, or repeated unexplained termination. Do not promote a standby or rebuild a node as an incidental “restart fix.”

**Recovery boundary:** restore a known valid configuration for a configuration failure; investigate storage and recovery errors before another lifecycle request. Preserve logs and data. Do not remove WAL, delete control files or use pg_resetwal to force a normal startup. Such actions can destroy the basis for recovery and require a separate expert-led plan.

## 8. Diagnosis and observability

| Symptom | Evidence to collect | Next action |
|---|---|---|
| Wrapper active, connection fails | Instance unit, endpoint, MainPID, PostgreSQL log | Identify the actual instance and startup phase |
| Startup wait expires | Process status and timestamped recovery log | Determine whether startup continues; avoid overlapping starts |
| Port already occupied | Listener owner and command line | Resolve the conflicting instance |
| Smart stop waits | Existing sessions and connection-pool state | Drain clients; verify shutdown completion |
| Repeated recovery starts | Journal result, restart policy, OOM and storage evidence | Stabilize the termination cause |
| Primary returns, standby does not stream | Sender/receiver logs and retained WAL | Diagnose replication; do not promote reflexively |
| SQL accepts connections, app still fails | Pool reconnects, endpoint, auth and representative request | Repair the affected client dependency |

Alert on failed authenticated probes, unexpected role changes, restart frequency, recovery duration beyond the deployment's agreed budget and replication disruption. Correlate these with service-manager failures, kernel OOM events and storage errors. A green service state should never suppress a failing user-facing availability signal.

Use the accompanying read-only SQL snapshot before and after the exercise. Retain its timestamp, PostgreSQL start time and role together; uptime alone is not service availability.

## 9. Acceptance and official references

The chapter's lab passes only when evidence shows bounded smart shutdown, fast shutdown aborting an unfinished transaction, immediate shutdown followed by recovery, the committed fixture retained, unfinished fixtures absent, both standbys streaming and clients reconnecting. Restore the original topology and remove only the owned test fixtures. Runtime evidence remains pending until you execute the lab.

- [PostgreSQL 18: starting the server](https://www.postgresql.org/docs/18/server-start.html)
- [PostgreSQL 18: shutting down the server](https://www.postgresql.org/docs/18/server-shutdown.html)
- [PostgreSQL 18: pg_ctl](https://www.postgresql.org/docs/18/app-pg-ctl.html)
- [PostgreSQL 18: WAL introduction](https://www.postgresql.org/docs/18/wal-intro.html)
- [PostgreSQL 18: asynchronous commit](https://www.postgresql.org/docs/18/wal-async-commit.html)
- [systemd upstream systemctl manual source](https://github.com/systemd/systemd/blob/main/man/systemctl.xml)
- [systemd upstream service manual source](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml)

**Next:** Chapter 010 — Configuration Drift and Baseline Acceptance.
