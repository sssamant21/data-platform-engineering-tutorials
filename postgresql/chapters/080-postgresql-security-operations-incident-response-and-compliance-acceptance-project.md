# Chapter 080 — PostgreSQL Security Operations, Incident Response and Compliance Acceptance Project

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime acceptance pending

## 1. Mission

Run an evidence-driven security operations and incident response capstone for PostgreSQL. Integrate [Chapter 076 — Roles and Privileges](076-postgresql-security-architecture-roles-and-privileges.md), [Chapter 077 — Authentication and TLS](077-postgresql-authentication-pg-hba-conf-tls-and-connection-security.md), [Chapter 078 — RLS and Audit](078-postgresql-row-level-security-data-protection-and-audit-controls.md), and [Chapter 079 — Encryption, Secrets and Hardening](079-postgresql-encryption-secrets-management-and-security-hardening.md).

**Acceptance principle:** detecting a security event is not sufficient; prove controlled containment, preserved evidence, restored least privilege, functioning recovery paths and accountable signoff.

## 2. Scope and operating model

```text
Identity + network + TLS + database roles + RLS
                    |
          logs / metrics / audit events
                    |
           detection and triage
                    |
          incident commander approval
                    |
      contain -> investigate -> recover
                    |
     validate -> lessons learned -> evidence
```

Security is shared among DBA/DBRE, SRE/platform, application, IAM/security, backup, and compliance teams. Document the cloud-provider shared responsibility boundary and where PostgreSQL configuration is managed externally.

## 3. Threat scenarios and control objectives

| Scenario | Signal | Safe response | Acceptance |
|---|---|---|---|
| Repeated invalid login | Authentication errors from unexpected source | Restrict source, rotate affected lab secret | Authorized clients continue working |
| Excessive application role privileges | Unexpected CREATEROLE/CREATE/BYPASSRLS or broad grants | Review dependencies, revoke only approved lab grants | App CRUD works, unauthorized DDL denied |
| Tenant isolation failure | Cross-tenant row visible | Suspend affected lab access, preserve query/role/policy evidence | RLS negative tests pass |
| Stolen application secret | Secret exposure in simulated evidence | Revoke/rotate credential, reconnect pools | Old credential rejected |
| TLS downgrade or certificate failure | Non-TLS session, failed verify-full | Correct CA/SAN/TLS config; do not downgrade | Trusted verify-full works, insecure path fails |
| Missing audit events | Logging/collector gap | Restore collector, test delivery and retention | Timestamped redacted events available |
| Backup/key compromise | Key or backup exposure suspicion | Isolate affected identities, assess key rotation | Isolated encrypted restore still possible |
| Suspicious privileged change | Unexpected role/policy/extension change | Freeze further change, inspect audit and change history | Owner approval and drift reconciliation |

## 4. Incident response lifecycle

### 4.1 Prepare

Inventory databases, hosts, service roles, owners, replication, backup identities, secret stores, encryption keys, logging destinations, retention and on-call contacts. Define severity, evidence handling and escalation. Maintain break-glass access with independent approval and tested audit logging.

### 4.2 Detect and triage

Correlate PostgreSQL authentication errors, role changes, RLS policy modifications, unexpected DDL, suspicious client addresses, replication/export activity, audit collector health and secrets-store access logs. Preserve UTC timestamps and source identity. SQL views show current configuration; they do **not** prove historical activity without logging.

### 4.3 Contain safely

Prioritize restricting the suspected credential/source or isolating a lab service, not indiscriminately terminating production sessions. Capture current role memberships, active sessions and audit logs before changes where safe. Assess transaction and application impact. Use an incident commander and change approval for production containment.

### 4.4 Investigate

Establish event timeline and scope: initial access, affected identities, objects, rows, backups, downstream consumers and possible exfiltration. Check privilege escalation, search_path and SECURITY DEFINER exposure, owner/BYPASSRLS bypass, audit gaps and retention. Protect evidence integrity, access and chain of custody.

### 4.5 Recover

Rotate affected credentials/certificates, restore least-privilege grants, correct RLS policies, validate TLS identity verification, restore logging and test backups/keys. Reconcile application transactions and data exposure. Re-enable traffic in controlled stages.

### 4.6 Review and improve

Document root causes and contributing conditions without blame. Assign corrective actions, owners and deadlines; update runbooks, alerts, access reviews, deployment controls and recovery drills.

## 5. Compliance evidence: controls, not certifications

Map each technical control to an organizational policy or relevant regulatory framework as applicable; do not claim HIPAA, SOC 2, PCI DSS or ISO certification from this lab. Evidence should be scoped to a system, date, owner and test result.

| Control domain | Example evidence |
|---|---|
| Access governance | Role inventory, least-privilege test, approvals and periodic review |
| Authentication | HBA ordering, SCRAM, MFA at control-plane/secret store where available |
| Encryption | TLS verification, encrypted volume/backup and KMS policy evidence |
| Tenant isolation | Independent nonprivileged CRUD negative tests |
| Auditability | Redacted event delivery, retention, integrity and alert test |
| Vulnerability management | Version/patch/extension inventory and remediation records |
| Recovery | Backup restore, key availability, RPO/RTO and application validation |
| Incident response | Incident timeline, approvals, containment and postmortem |

**Never attach secrets, tokens, private keys, raw sensitive rows or unredacted customer information** to compliance evidence.

## 6. Monitoring and response thresholds

Monitor repeated failed logins by role/source, unexpected privilege grants, login from new network locations, TLS policy violations, audit collector failures, backup/key access anomalies and RLS policy changes. Set thresholds from baseline and risk appetite; avoid assuming all failed logins are malicious. Alert routing and response ownership must be tested.

## 7. Production safety rules

- Run active failure injection only in a disposable environment.
- Never intentionally expose real credentials or customer data.
- Do not disable TLS/RLS or change privileged roles in production to simulate attacks.
- Treat audit log retention and privacy as separate requirements.
- Do not revoke an encryption key before confirming backup recovery and legal/retention obligations.
- If security evidence is incomplete, mark NOT VERIFIED; do not infer PASS from documentation alone.

## 8. Acceptance criteria

A security capstone **PASS** requires: authorized access preserved; unauthorized access denied; privilege escalation blocked; tenant isolation enforced; secret rotation and TLS verified; audit events captured and delivered; backup encryption and isolated restore verified; incident timeline and containment evidence recorded; rollback tested; and security/DBRE/application signoff.

A **FAIL** is mandatory for confirmed cross-tenant access, dual uncontrolled privileged paths, missing essential containment, or inability to recover encrypted backups. **NOT VERIFIED** applies to skipped tests, missing provider evidence or tabletop-only simulations.

## 9. Hands-on project

Use [Chapter 080 execution lab](../labs/080-postgresql-security-operations-incident-response-and-compliance-acceptance-project-lab.md), [read-only security inspection SQL](../labs/sql/080-security-incident-inspect.sql), [acceptance scorecard](../labs/acceptance/080-security-acceptance-scorecard.csv) and [incident evidence template](../labs/acceptance/080-security-incident-evidence-template.md).

**Runtime validation pending.**

## References

- https://www.postgresql.org/docs/18/auth-pg-hba-conf.html
- https://www.postgresql.org/docs/18/ddl-rowsecurity.html
- https://www.postgresql.org/docs/18/runtime-config-logging.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/predefined-roles.html
- https://www.nist.gov/cyberframework

**Next:** Chapter 081 — PostgreSQL Extensions, Compatibility and Operational Lifecycle.
