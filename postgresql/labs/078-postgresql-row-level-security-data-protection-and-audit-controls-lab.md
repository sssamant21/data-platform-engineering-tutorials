# Chapter 078 — Row-Level Security, Data Protection and Audit Controls Lab

**PostgreSQL 18 · Disposable lab only · Runtime pending**

## 1. Safety

Use a disposable PostgreSQL 18 instance. The fixture creates cluster-wide LOGIN roles and a dedicated `ch078_lab` database. Never run in production. Roles have no stored passwords in the fixture; provision lab credentials securely outside Git before testing separate client sessions.

## 2. Setup

As a lab administrator, run:

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/078-rls-fixture.sql
```

Inspect policies with [078 read-only SQL](../labs/sql/078-rls-and-audit-inspect.sql).

## 3. Tenant isolation

Connect as `ch078_tenant_a` using a real client login. Verify SELECT returns only tenant A rows, INSERT of an A row succeeds, INSERT of a B row fails, UPDATE cannot move A row into B, DELETE cannot remove B rows. Repeat as `ch078_tenant_b`. Check SQLSTATE, result row counts and request IDs.

## 4. Owner and privileged bypass

As the authorized administrator, document table owner and `relforcerowsecurity`. Confirm neither tenant is the owner nor has `BYPASSRLS`. Use a separate **lab-only** test to show the difference between owner bypass and `FORCE ROW LEVEL SECURITY`; do not grant BYPASSRLS to tenant roles.

## 5. Column and audit controls

Attempt to SELECT the sensitive `secret_note` column as a tenant; access must be denied while allowed columns remain readable. Inspect `log_connections`, `log_disconnections` and `log_statement` settings. If pgaudit is available, configure it in the disposable lab following its installation requirements and capture redacted audit events. If unavailable, mark pgaudit-specific coverage NOT VERIFIED.

## 6. Pooling risk tabletop

Explain why setting `app.tenant_id` from an untrusted SQL client is not a secure identity boundary. Document an approved alternative and verify transaction pool context cleanup if a pooler is part of the lab.

## 7. Acceptance and cleanup

Complete [078 scorecard](../labs/acceptance/078-rls-audit-scorecard.csv). Preserve redacted logs and test results. Clean up only the disposable database and lab roles after reviewing dependencies; do not run blanket cleanup against shared clusters.

**Runtime:** pending.
