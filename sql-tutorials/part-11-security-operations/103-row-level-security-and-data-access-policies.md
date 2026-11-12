# 103 — Row-Level Security and Data-Access Policies

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · **PostgreSQL 18 target** · **Audience:** beginners, data engineers, application engineers, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only lab](../labs/103-row-level-security-data-access-policies.sql) · [Previous: 102](102-users-roles-grant-revoke-and-ownership.md) · Next: 104 — Sensitive data protection, masking, and audit requirements (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

After this lesson, distinguish object-level privileges from row-level policies; explain permissive and restrictive policies, default-deny behavior, USING versus WITH CHECK, policy bypass risks, and tenant-isolation verification. Prerequisite: [Chapter 102](102-users-roles-grant-revoke-and-ownership.md).

**Scenario:** A fictional SaaS reporting service stores orders for tenants 10 and 20 in one table. Authorized analysts should see only their tenant's rows, while a service identity should never accidentally gain cross-tenant access. All data below are synthetic.

## 2. Conceptual model and portability (5–15 minutes)

**Portable idea:** authorize at the object and row levels, enforce the policy in the data-access path, and test negative cases. **PostgreSQL-specific implementation:** `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`, `CREATE POLICY`, `USING`, `WITH CHECK`, `FORCE ROW LEVEL SECURITY`, and `pg_policies`. Other systems implement row filters differently; do not copy PostgreSQL syntax into Snowflake, SQL Server, BigQuery, or Oracle without adaptation.

| Concept | Meaning |
|---|---|
| Table GRANT | Determines whether a role may attempt SELECT/INSERT/UPDATE/DELETE on the table |
| RLS | Adds row visibility and/or modification conditions after applicable table privileges |
| `USING` | Filters existing rows visible for SELECT, UPDATE, and DELETE, according to command |
| `WITH CHECK` | Validates new row values for INSERT and UPDATE; violations raise errors |
| Permissive policy | Multiple applicable permissive policies combine with OR |
| Restrictive policy | Applicable restrictive policies combine with AND; at least one permissive policy must grant access |
| Default deny | When RLS is enabled and no applicable policy permits access, ordinary roles see no rows |
| Bypass | Superusers and roles with BYPASSRLS bypass policies; table owners normally bypass unless FORCE RLS is set |

RLS is not a substitute for table privileges, column-level protection, authentication, application authorization, or audit logging. PostgreSQL referential-integrity and uniqueness checks may bypass RLS to maintain integrity; errors can still leak information. Functions, views, SECURITY DEFINER routines, and connection pooling require explicit review.

## 3. Worked example (15–30 minutes)

**Illustrative PostgreSQL 18 DDL only — NOT executed by this chapter's lab.** Run only on a separate approved disposable instance, with dedicated test roles, and never against production.

```sql
-- Preconditions: tenant_orders exists and has a non-null tenant_id.
-- App role must not own the table, be superuser, or have BYPASSRLS.
ALTER TABLE tenant_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_orders FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_select ON tenant_orders
  FOR SELECT TO tenant_app
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::integer);

CREATE POLICY tenant_insert ON tenant_orders
  FOR INSERT TO tenant_app
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::integer);
```

A real design also needs scoped table grants and separately reviewed UPDATE/DELETE policies if those operations are required. If the setting is missing, `current_setting(..., true)` returns NULL, so equality is unknown and no row matches. If the setting is malformed, integer casting errors rather than silently allowing access. This is **not** an authentication mechanism: a client able to set `app.tenant_id` arbitrarily can impersonate another tenant. A trusted server-side identity-to-tenant binding, restricted database roles, and a tested connection-pool/session reset strategy are required. Avoid letting untrusted clients issue `SET` directly as a security boundary.

**Illustrative transaction-scoped tenant context:**

```sql
BEGIN;
SELECT set_config('app.tenant_id', '10', true); -- transaction-local
SELECT order_id, tenant_id, amount
FROM tenant_orders ORDER BY order_id;
ROLLBACK;
```

This transaction-scoped setting is useful for avoiding stale session state, but **does not by itself prove isolation**. Do not run it with real tenant data. The table owner, privileged roles, and security-definer/view ownership may change the effective security context. In PostgreSQL, views normally use the view owner's permissions and RLS context; `security_invoker = true` changes this to the invoking user's permissions and policies, subject to PostgreSQL version support and privileges.

**Expected synthetic policy evaluation (not a live RLS result):**

| Tenant context | Visible order IDs | Row count | Amount |
|---|---|---:|---:|
| 10 | 101, 102, 104 | 3 | 90.00 |
| 20 | 103, 105 | 2 | 60.00 |
| Missing | none | 0 | 0.00 |

A naive application `WHERE tenant_id = 10` is a useful filter but not a reliable access-control boundary if other query paths omit it. RLS can provide database-side defense in depth when roles, context, and bypass paths are properly controlled.

## 4. Hands-on read-only lab (30–50 minutes)

Run against an **isolated disposable PostgreSQL 18** database named `sql_tutorials` using an unprivileged lab identity. Never use production credentials.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/103-row-level-security-data-access-policies.sql
```

[Lab 103](../labs/103-row-level-security-data-access-policies.sql) runs inside `BEGIN READ ONLY` with version/database guards, local timeouts, inline synthetic rows, and a rollback. It **models** tenant filtering using ordinary SELECT predicates; it does not enable real RLS, create policies, alter roles, or inspect real tenant data. The lab checks two-way multiset equality using `EXCEPT ALL` and raises an exception on mismatches.

**Exercise A:** Verify tenant 10's three rows sum to 90.00. **Exercise B:** Verify tenant 20's two rows sum to 60.00. **Exercise C:** Verify no tenant-20 row appears in tenant-10's result. **Exercise D:** Explain why an absent tenant context should deny access. **Exercise E:** Design a separate *approved isolated* integration test that connects as the real application role and checks SELECT, INSERT, UPDATE, DELETE, owner bypass, and pooled-session behavior.

**Calculated expectations:** 5 total orders, tenant 10: 3 rows/90.00, tenant 20: 2 rows/60.00, missing context: 0 rows, cross-tenant leakage: 0, assertion mismatches: 0. These are static calculations, not observed PostgreSQL output.

## 5. Troubleshooting, safety, and operational review (50–55 minutes)

| Symptom | Investigation | Guardrail |
|---|---|---|
| App sees no rows | Check table GRANT, policy applicability, missing tenant context, NULL handling | Do not disable RLS as a quick fix |
| App sees every row | Check table ownership, BYPASSRLS, superuser, view/definer execution | Test as actual least-privilege login |
| INSERT rejected | Check `WITH CHECK` and tenant ID supplied | Do not weaken check to permit cross-tenant writes |
| Pool leaks prior tenant | Inspect transaction boundaries and context reset | Bind tenant to trusted identity and reset/rollback reliably |
| Unexpected policy composition | Inspect `pg_policies`, permissive OR/restrictive AND | Review all applicable policies, not one |
| Slow queries | Inspect plans and tenant-leading indexes on isolated representative data | Benchmark without removing security controls |

**DBRE/SRE change checklist:** data-owner approval, threat model, policy review, application identity mapping, test matrix (positive and negative), migration and rollback, audit evidence, performance baseline, connection-pool validation, and independent security sign-off. RLS policy changes may alter query results immediately; coordinate rollout and verify with least-privilege identities. Keep all production policy changes outside tutorials.

## 6. Review questions and answers (55–60 minutes)

1. **Does RLS replace GRANT?** No. Both object permissions and row policies matter.
2. **What happens with RLS enabled but no applicable permissive policy?** Ordinary access is denied by default.
3. **What differs between USING and WITH CHECK?** Existing-row visibility versus new/updated row acceptance.
4. **Do owners always obey RLS?** Not normally; FORCE RLS changes owner behavior, but superuser/BYPASSRLS still bypass.
5. **Why isn't a client-supplied tenant setting secure by itself?** The client can change it unless trusted infrastructure binds it to identity.
6. **Can permissive policies broaden access?** Yes, their conditions combine with OR.
7. **Does the lab prove PostgreSQL RLS works?** No. It tests a synthetic filtering model; isolated role-based integration tests are still required.

## References

- [PostgreSQL 18 — Row Security Policies](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [PostgreSQL 18 — CREATE POLICY](https://www.postgresql.org/docs/18/sql-createpolicy.html)
- [PostgreSQL 18 — ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html)
- [PostgreSQL 18 — pg_policies](https://www.postgresql.org/docs/18/view-pg-policies.html)
- [PostgreSQL 18 — CREATE VIEW (security_invoker)](https://www.postgresql.org/docs/18/sql-createview.html)

**Validation state:** authored for publication; manual expected-result reasoning only. Independent editorial review, automated parser-based SQL/link QA, and actual PostgreSQL 18 runtime validation are pending.
