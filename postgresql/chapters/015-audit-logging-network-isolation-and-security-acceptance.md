# Chapter 015 — Audit Logging, Network Isolation and Security Acceptance

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18 on Linux.
**Duration:** 90–120 minutes; optional pgAudit track adds 45–60 minutes.
**Prerequisites:** Chapters 004 and 011–014.
**Status:** Authored and statically reviewed; PostgreSQL/network acceptance execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](014-secrets-rotation-and-service-account-lifecycle.md) · [Hands-on lab](../labs/015-audit-network-isolation-security-acceptance-lab.md) · [Inspection SQL](../scripts/015-security-acceptance-inspection.sql) · [Acceptance report template](../projects/015-security-acceptance-report.md)

## 1. Operational problem and objectives

A database is reachable only through a private endpoint, but an overly broad firewall still permits unexpected sources. Another team enables statement logging and assumes every logged write committed. During an incident, the logs contain client-supplied labels but no dependable correlation to the authenticated identity or configuration change.

Security acceptance needs observed behavior and retained evidence. This chapter joins least privilege, authentication, TLS and credential lifecycle with logging and network controls. You will define audit requirements, distinguish logging from durable transaction evidence, assess exposure on the actual client path and produce a reviewable Module 03 acceptance report.

The lab demonstrates bounded core logging, a denied application operation, HBA rejection and optional pgAudit records. It does not claim a loopback-only environment validates production firewalls, centralized retention or every security control.

## 2. Define the audit contract

| Question | Evidence to require |
|---|---|
| Who connected? | Authenticated identity, login role, source/path and time |
| Which operation occurred? | Selected event class, object and statement metadata |
| Which authority was used? | Login/execution identity and relevant role changes |
| Was it allowed? | Success or error classification, including SQLSTATE where available |
| Did it commit? | Transaction/application evidence appropriate to the requirement |
| Where is evidence retained? | Destination, access controls, retention, collection health and retrieval |
| Can it be altered or lost? | Administrative boundaries and delivery/failure tests |

Choose events deliberately: authentication failures, administrative role/grant changes, DDL, selected data access and writes, configuration changes and credential lifecycle actions. Requirements vary by service/data sensitivity. Do not enable every event on a busy cluster before evaluating volume, latency and data exposure.

application_name is useful correlation metadata, but the client can supply it. Pair it with authenticated role, database, source, session/backend identity and time. It is not trustworthy proof of who performed a business action.

## 3. Core logs and audit-oriented records

Core PostgreSQL logs support connection, disconnection, error and statement evidence. They are valuable operational signals, but statement logging is not a complete audit system.

PostgreSQL 18 log_connections is a string accepting selected aspects or all. Older production versions commonly expose a boolean. Use the version-specific definition. Failed authentication is logged independently of enabling successful connection messages.

A useful text prefix can include time, PID, session ID, role/database, client address, application name and SQLSTATE. Structured CSV/JSON logs reduce parsing ambiguity when supported and configured. Both csvlog and jsonlog need the logging collector; enabling the collector requires startup. The manual Chapter 004 lab instead redirects stderr to its known log file.

Statement/error text can contain sensitive literals. Parameter-suppression settings do not redact literals embedded directly in SQL. Avoid logging password-bearing statements, tokens, personal data or sensitive payloads as part of a test.

A logged statement does not prove COMMIT. Errors, rolled-back transactions and failed parsing/execution have different logging behavior. Correlate transaction boundaries and application reconciliation evidence when the requirement is committed business state.

The logging collector is designed to avoid losing messages, so overloaded logging can block server work. Other destinations/pipelines may drop messages. The end-to-end collection path still requires delivery, retention and outage testing; a local log entry does not establish durable central evidence.

## 4. pgAudit: scope, compatibility and limits

pgAudit provides audit-oriented event records through PostgreSQL's logging facility. Select the release/package matching the PostgreSQL major: pgAudit 18.x is the PostgreSQL 18 track. Pin the exact package/extension version in the report.

It requires shared_preload_libraries, which involves a restart. Preserve existing preload libraries rather than replacing their list blindly. Install/create the extension before enabling its audit setting so DDL event-trigger metadata is available.

Session classes include READ, WRITE, DDL, ROLE, FUNCTION and MISC_SET. Object auditing can target particular relation access but is not a replacement for all administrative-event coverage. Choose scope against requirements and validate representative permitted/denied operations.

pgAudit settings are not inherited through ordinary role membership, and SET ROLE does not load another role's configured defaults. Verify settings for actual login paths rather than assuming a group policy automatically applies.

Keep parameter logging off unless the approved evidence contract requires it. Statement text can still contain literals. Audit relation expansion can multiply log records; benchmark representative workload and test log-volume failure behavior.

pgAudit is best-effort, not transactional durability. An entry can exist for work later rolled back; a committed transaction can lose its audit record under failure. It also cannot make evidence tamper-proof against an administrator who controls the host/logging path. Use separation of duties and protected external collection for those requirements.

The optional lab uses synthetic data and session-scoped audit settings. It does not establish global audit coverage for every login or install an external immutable log store.

## 5. Network isolation has multiple layers

| Layer | Control/evidence | Boundary |
|---|---|---|
| Listener | listen_addresses, port, OS listeners | Which local interfaces accept database TCP |
| Host/container exposure | Firewall, published ports and routing | Who can reach the listener |
| Cloud network | Reviewed security rules/subnets/routes | Permitted source/destination paths |
| Kubernetes | Service exposure and supported network policy | Actual pod/node/namespace path |
| HBA | Ordered tuple/method rules | Database admission after reaching PostgreSQL |
| TLS | Verified client/server contract | Protected transport and identity |
| Roles/objects | Effective permissions | What an admitted session can do |

A private DNS name is not a firewall. HBA rejection does not prove that network traffic could not reach the server. Conversely, a TCP connection success does not prove authentication.

listen_addresses changes require restart. HBA usually reloads on Linux. Do not change listener binding or firewall rules casually during an authentication incident. Keep the established administration/recovery path.

Account for poolers, proxies, NAT, containers, IPv6 and alternate read/write endpoints. Verify from both an intended source and a controlled forbidden source you are authorized to use. Capture the actual source PostgreSQL sees. Avoid remote scanning outside the test scope.

## 6. Evidence collection and retention

Collect time-synchronized records with endpoint, major/minor version, logging configuration and change reference. Retrieve events through the real production pipeline, not only a local tail. Establish an ingestion-lag SLO, delivery-failure alert and a known synthetic canary.

Estimate raw daily volume from measured average bytes/event × events/second × 86400. Include expansion, bursts, transport, indexing and retention overhead. No universal retention duration or size threshold fits every deployment.

Protect logs and backups with access controls, approved encryption and lifecycle rules. Keep logs from filling the database's data volume. Test collectors during restart, rotation and destination outage in a disposable environment; a normal local filesystem snapshot does not prove crash-safe retention.

Use sanitized fixtures and unique correlation tokens. Confirm secrets are excluded, but do not claim a grep proves absence of all sensitive data.

## 7. Production change and rollback

Precheck audit requirements, log ownership/destination, capacity, parsing, existing preload libraries, version compatibility, client paths and recovery access. Stage one reviewed change through the owning deployment system and run bounded canary events.

Stop for unknown exposure, a broken administration path, secret leakage, missing required events, log backlog, unexpected disk growth or unacceptable latency impact. Do not disable a mandatory control simply to make acceptance pass; investigate or keep the gate pending.

Rollback logging settings to the recorded source/value and verify new sessions. Preload changes need the lifecycle procedure and a restart; disabling an extension setting does not remove its loaded library. Restore network rules through their source of truth and re-test allowed/forbidden sources before ending the change.

The lab resets only overrides it proved absent before the exercise and removes only its synthetic schema. It does not install firewalls or alter cloud/Kubernetes rules.

## 8. Diagnose security evidence gaps

| Symptom | Evidence | Next action |
|---|---|---|
| Connection logged, read not captured | Statement/audit scope and login settings | Add the reviewed access event coverage |
| Wrong user attributed | Login/execution identity, pooler and SET ROLE history | Repair identity correlation |
| Denied operation absent from audit | Core error log and extension semantics | Validate the intended failure-event pipeline |
| Local event absent centrally | Collection offsets/lag/restart/rotation | Diagnose delivery, not database grants |
| HBA denies, TCP still reaches server | Listener and actual network controls | Separate admission from network isolation |
| Expected private source becomes NAT | Route/proxy path and server-visible client | Adjust the reviewed source contract |
| Log volume jumps | Classes/relation expansion and workload | Reduce approved scope or increase supported capacity |
| Logged write later absent | Transaction/error/application state | Distinguish execution from commit |

## 9. Module 03 security acceptance

Use the accompanying report to review Chapters 011–015. Require evidence for least privilege, allowed/denied HBA, verified TLS, secret rotation/adoption, old-session retirement, intended/forbidden network sources and audit delivery/retrieval.

Mark every gate Pass, Fail, Pending or Not applicable with a reason and reviewer. A skipped mandatory audit or production-path test remains Pending. A green loopback lab does not establish production security acceptance or regulatory compliance.

## 10. Official references

- [PostgreSQL 18 logging](https://www.postgresql.org/docs/18/runtime-config-logging.html)
- [Connection/listener settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [HBA](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)
- [pgAudit official project](https://github.com/pgaudit/pgaudit)
- [TLS](https://www.postgresql.org/docs/18/ssl-tcp.html)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Next:** Chapter 016 — MVCC, Snapshots and Tuple Visibility.
