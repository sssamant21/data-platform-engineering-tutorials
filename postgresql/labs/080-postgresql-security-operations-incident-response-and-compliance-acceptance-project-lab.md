# Chapter 080 — Security Operations, Incident Response and Compliance Acceptance Lab

**PostgreSQL 18 · Disposable security capstone · Runtime pending**

## 1. Prerequisites and safety

Use an isolated PostgreSQL 18 cluster and lab identities from Chapters 076–079, or equivalent fresh disposable fixtures. Enable an approved log collector and separate redacted evidence storage. Assign incident commander, DBRE, security, application and evidence recorder roles. Do not test credential compromise, privilege changes or TLS downgrade on production.

## 2. Preflight

Record system inventory, incident contacts, approved RPO/RTO, secret/certificate rotation procedure, backup decryption/restore plan and change rollback. Run [080 read-only SQL](../labs/sql/080-security-incident-inspect.sql) as an authorized administrator. Capture UTC baseline and role membership.

## 3. Scenario A — Failed authentication

From a lab-only client, attempt login with an incorrect secret. Confirm PostgreSQL logs and central collector capture timestamp, source and role without exposing the attempted password. Verify authorized application connections continue to succeed.

## 4. Scenario B — Privilege drift

In the disposable lab only, use an approved admin to grant an unnecessary privilege to a test identity. Detect the drift via role/ACL inspection, preserve before/after evidence and revoke the lab-only grant. Verify application CRUD remains functional and prohibited DDL remains denied.

## 5. Scenario C — Tenant isolation

Connect independently as two nonprivileged tenant roles. Attempt cross-tenant SELECT, INSERT, UPDATE and DELETE against the Chapter 078 fixture. Verify denials and audit events. If any cross-tenant data is exposed, mark FAIL, stop and preserve evidence.

## 6. Scenario D — Secret and TLS recovery

Rotate a disposable credential through a controlled channel, validate new connections and rejection of the old secret. Test `sslmode=verify-full` with trusted and untrusted certificates. Never disable production TLS to test an insecure path.

## 7. Scenario E — Audit collector outage

Simulate a lab-only collector interruption, confirm an alert, restore delivery and identify any evidence gap. Record detection-to-recovery time and whether events were buffered or lost.

## 8. Scenario F — Encrypted backup restore

Restore a copy of encrypted lab backup into an isolated target using separately governed key access. Verify a transaction marker, key recovery, integrity and restore duration. Do not revoke or delete real KMS keys.

## 9. Incident closure

Build a UTC timeline with detection, approval, containment, investigation, recovery, validation and follow-up actions. Complete [080 acceptance scorecard](../labs/acceptance/080-security-acceptance-scorecard.csv) and [incident evidence template](../labs/acceptance/080-security-incident-evidence-template.md). Obtain signoff only for executed controls.

**Runtime:** pending; simulated controls and missing provider evidence remain NOT VERIFIED.
