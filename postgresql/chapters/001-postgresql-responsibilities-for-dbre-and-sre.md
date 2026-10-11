# 001 — PostgreSQL Responsibilities for DBRE and SRE

[Master plan](../MASTER-PLAN.md) · [Hands-on lab](../labs/001-operational-ownership-and-readiness-lab.md)

## 1. Operational problem

A PostgreSQL endpoint can accept connections while an application cannot complete a request. A replica can be healthy while it serves stale data. A backup job can succeed while the team has never demonstrated a restore.

The DBRE/SRE responsibility is to turn these separate signals into evidence that the service is available, its data is protected and its failure modes are understood.

This chapter establishes ownership and a first diagnostic workflow. It does not require a high-availability deployment or authorize production failover.

**Audience:** DBRE and SRE teams only.  
**Estimated effort:** 45–60 minutes reading and 45–60 minutes for the lab.  
**Prerequisites:** basic SQL, a terminal and access to an existing disposable PostgreSQL instance. Chapter 004 will build the reusable multi-node lab.

## 2. Learning objectives

After this chapter, you should be able to:

- Describe DBRE and SRE responsibilities and name the accountable owner for each operational task.
- Distinguish endpoint readiness, authenticated connectivity and application success.
- Identify the database, server version, session role and recovery state before investigating.
- Collect a bounded first-response snapshot without changing persistent settings.
- Define service objectives and recovery requirements with service owners.
- Separate observations from assumptions and choose a proportionate next action.
- Create an ownership and readiness record that another on-call engineer can use.

## 3. DBRE and SRE ownership

DBRE applies reliability engineering to the database lifecycle: safe operation, recoverability, performance, access and change management. SRE coordinates end-to-end service reliability, including application behavior, infrastructure and incident response.

The following is a suggested team agreement, not a universal organizational rule. One person may hold both roles, but each responsibility still needs an accountable owner.

| Responsibility | Suggested accountable owner | Supporting teams | Required evidence |
|---|---|---|---|
| Database topology and configuration | DBRE | SRE/platform | Inventory, reviewed configuration and dependency map |
| User-facing availability and latency | Service SRE | DBRE/application | Service SLIs, SLOs and error budget |
| Database performance and capacity | DBRE | SRE/application | Workload baseline, waits, query evidence and capacity forecast |
| Backup and restore capability | DBRE | Platform/service owner | Restore results and achieved RPO/RTO |
| Replication and database failover | DBRE | SRE/platform | Fencing, client recovery and rejoin procedure |
| Database access and role review | DBRE | Security/application | Approved access inventory and review trail |
| Host, network and persistent storage | Platform SRE | DBRE | Capacity, fault-domain and recovery evidence |
| Application SQL and transaction design | Application owner | DBRE/SRE | Query plans, transaction behavior and load validation |
| Database schema change safety | DBRE | Application owner | Lock impact, rollout and rollback boundaries |
| Incident command and communication | Incident commander | DBRE/SRE/service owner | Timeline, impact and decision log |

For managed PostgreSQL, the provider operates parts of the underlying infrastructure. Your team still owns workload behavior, service objectives, access, configuration choices within provider limits and evidence of recovery. Document the exact boundary for the selected service.

For operator-managed PostgreSQL, an operator can automate reconciliation. The team must still prove storage recovery, fencing, backup restoration and correct client routing.

## 4. What reliability means for PostgreSQL

| Dimension | Operational question | Example evidence |
|---|---|---|
| Availability | Can the intended application operation complete? | Success rate for a representative service operation |
| Latency | Does it complete within the agreed objective? | Application latency distribution with workload and time window |
| Durability | What acknowledged data could be lost in this failure? | Commit policy, topology and tested failure results |
| Recoverability | Can we restore the required data in time? | Timestamped restore drill with validation |
| Capacity | How much headroom remains under expected growth? | Connection, CPU, memory, storage and WAL trends |
| Security | Can only authorized identities perform intended actions? | Role review, authentication policy and rotation evidence |
| Change safety | Can the change be applied and recovered safely? | Rehearsal, prechecks, stop conditions and postchecks |

A database process running is one signal. It does not establish all these dimensions.

### Example service objectives

These values are illustrative; negotiate actual values with the service owner.

- Availability: 99.9% successful eligible service operations over a rolling 30-day window.
- Latency: 99% of a defined interactive operation complete within 300 ms under the documented workload.
- Recovery: a nominated failure scenario has RPO of at most 5 minutes and RTO of at most 30 minutes.

Define eligible operations, measurement point, exclusions and minimum sample size. A database-only query does not replace a user-facing SLI. An idle server does not establish production capacity.

RPO is the tolerated data-loss window; RTO is the tolerated time to restore the agreed service. A backup schedule alone does not prove either objective. Recovery exercises must specify the failure scenario and the point at which the service counts as restored.

## 5. First-response workflow

1. Establish impact: affected service, start time, errors, latency and recent changes.
2. Confirm the target: endpoint, database, environment, server role and connected identity.
3. Separate readiness from authentication and workload behavior.
4. Gather a small baseline: uptime, activity, waits, database sizes and selected settings.
5. Correlate with application, host, network and storage evidence.
6. Choose a mitigation with an owner, expected benefit and stop condition.
7. Verify application recovery and retain evidence for follow-up.

Do not restart solely because latency increased. A restart can interrupt work, erase useful state and leave the underlying bottleneck unresolved.

## 6. Safe diagnostic entry point

The linked lab uses PostgreSQL 18 as the reference major version. Record the exact server and client versions used. Examples deliberately use a small set of established functions and views; use documentation matching your deployed major version.

Use an existing authorized lab login. A dedicated observer with CONNECT to the lab database and approved monitoring privileges is preferred. pg_monitor provides broad monitoring visibility and inherits other monitoring roles; it is not a grant to read all application tables. It can expose sensitive activity and settings, so assign it deliberately.

Do not put passwords into command-line URLs or evidence files. Use an approved credential mechanism, such as a properly protected password file. In production, use the required TLS verification policy; the local disposable lab may use a Unix socket.

Example Bash setup:

~~~bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=postgres
export PGUSER=YOUR_AUTHORIZED_LAB_ROLE
export PGCONNECT_TIMEOUT=5
export PGAPPNAME=chapter001-observer

pg_isready -t 5
psql -X -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user;"
~~~

Replace the role and endpoint. An already provisioned disposable instance is required; these commands do not install a server.

pg_isready reports whether an endpoint accepts connection attempts. Its success does not demonstrate that the supplied login is valid or that an application transaction succeeds. An authenticated SQL connection and a representative operation are separate checks.

## 7. Interpret the snapshot

Run the companion script from the repository root:

~~~bash
psql -X -v ON_ERROR_STOP=1   -f postgresql/scripts/001-first-response-snapshot.sql
~~~

| Observation | What it tells you | What it does not prove |
|---|---|---|
| pg_is_in_recovery() = true | The instance is in recovery, commonly a physical standby | That replay is current or promotion is safe |
| pg_is_in_recovery() = false | The instance is not in recovery | That clients reach the intended primary or all writes are allowed |
| transaction_read_only = on | The current transaction/session is read-only | The full topology or the application role's permissions |
| Client backend count | Current direct client sessions on this instance | Active business users or effective pool demand |
| wait_event_type = Lock | A backend is waiting on a lock-related event | The owner and business impact without further investigation |
| Recent server start time | The current instance started recently | Why it restarted or whether a failover happened |
| Large database size | Allocated database footprint | Filesystem free space or safe storage headroom |
| numbackends | Current sessions for a database | A cumulative session rate |
| xact_commit / xact_rollback | Cumulative transaction counters | Throughput without two samples and a measurement interval |

Use max_connections as a capacity input, not the complete admission budget. Reserved connections and provider or pool limits can affect usable capacity. Increasing it can increase resource pressure.

A single activity sample may miss transient problems. Query durations and wait events require context; pg_sleep deliberately generates a timeout wait in this chapter's lab and is not evidence of slow storage.

## 8. Operational ownership record

Create a record for each real database service:

| Field | Required entry |
|---|---|
| Service and environment | Service name, production/staging/lab |
| Owners | Accountable DBRE, SRE, application and platform owners |
| Escalation | On-call route and incident commander procedure |
| Endpoint and routing | Writer, reader and pool endpoints; routing owner |
| Deployment | Self-managed, provider service or selected operator |
| Version | Server major/minor, client and installed extension versions |
| Topology | Primary, standbys, regions/zones and fencing method |
| Authentication | Authorized login path, credential owner and TLS requirements |
| Objectives | Availability, latency, RPO and RTO with measurement definitions |
| Backup | Tool, destination, retention, last successful backup and last verified restore |
| Capacity | Storage/WAL limits, connection limits and growth forecast |
| Change control | Maintenance window, review path and rollback boundaries |
| Evidence | Dashboard, alert, runbook and restore-drill links |

Use “unknown — owner and due date” where evidence is missing. Do not report “healthy” because the inventory is incomplete.

## 9. Production procedure and stop conditions

**Prechecks:** identify the incident and target, confirm authorized read access, record UTC time and obtain existing service impact evidence.

**During collection:** use connection and statement timeouts, bounded result sets and an identifiable application_name. Avoid exporting query text or secrets unnecessarily. Do not wrap the collection in a long explicit transaction.

**Stop conditions:** unexpected environment, wrong role, restricted visibility, timeout, high collection cost or policy conflict. Preserve the error and escalate rather than granting yourself more access.

**Verification:** confirm that the diagnostic connection closes and that persistent configuration was not changed. Validate the service through its actual client path.

This chapter's SQL only reads metadata and changes session-local timeouts. Closing the session restores those session settings; no persistent rollback is required. Production mitigations such as cancellation, role changes, restart or failover require the corresponding later runbook.

## 10. Monitoring and alert ownership

| Signal | Alert design question | First investigation |
|---|---|---|
| Service errors and latency | Is the SLO being threatened over meaningful windows? | Application traces, errors and recent changes |
| Connection pressure | Is headroom shrinking or queueing harming requests? | Pools, client backends and resource limits |
| Disk/WAL growth | Will storage fill before operators can respond? | Free bytes, growth rate, retention and slots |
| Replication delay | Is the reader freshness or recovery objective breached? | Replay, transport, workload and topology |
| Backup or restore evidence | Is recoverability unproven or protection stale? | Backup history, WAL coverage and restore drill |
| Blocking and long transactions | Is business work delayed or maintenance blocked? | Blocking owner, transaction age and workload |

Each alert needs a responding owner, urgency, measurement window and runbook. Choose thresholds from service objectives and observed capacity rather than copying generic percentages.

## 11. Troubleshooting

| Symptom | Likely category | Safe next check |
|---|---|---|
| pg_isready succeeds; psql fails | Authentication, role, database or TLS policy | Exact psql error and selected connection parameters |
| psql connects to the wrong database | Implicit/default connection values | Explicit PGDATABASE and current_database() |
| Monitoring fields are null | Restricted visibility or no applicable value | Role membership and documented view semantics |
| Connection times out | Routing, network, endpoint or server admission | Resolve endpoint and check authorized network path |
| Read-only session reported | Standby or session/database/role configuration | Recovery state and transaction_read_only |
| No replication rows | No attached sender on that instance or wrong node | Topology record; do not conclude replication is healthy |
| High idle connection count | Pool behavior or oversized client concurrency | Pool settings and per-service connection ownership |
| Counters differ between samples unexpectedly | Reset, restart or measurement mismatch | stats_reset, server start time and sample interval |

## 12. Acceptance and next chapter

Complete the [hands-on lab](../labs/001-operational-ownership-and-readiness-lab.md).

You pass when another engineer can identify the target, interpret the snapshot, explain the controlled probe failure and use your ownership record without guessing.

**Next:** Chapter 002 — Architecture: Processes, Memory, Storage and WAL.

## 13. Official references

- [PostgreSQL 18 monitoring and statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 predefined roles](https://www.postgresql.org/docs/18/predefined-roles.html)
- [PostgreSQL 18 psql](https://www.postgresql.org/docs/18/app-psql.html)
- [PostgreSQL 18 pg_isready](https://www.postgresql.org/docs/18/app-pg-isready.html)
- [PostgreSQL 18 pg_settings](https://www.postgresql.org/docs/18/view-pg-settings.html)
