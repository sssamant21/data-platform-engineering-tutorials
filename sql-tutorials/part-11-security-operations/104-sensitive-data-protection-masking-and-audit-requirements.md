# 104 — Sensitive Data Protection, Masking, and Audit Requirements

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · **Target: PostgreSQL 18** · **Audience:** beginner data engineers, analysts, application engineers, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Synthetic read-only lab](../labs/104-sensitive-data-masking-audit.sql) · [Previous: 103](103-row-level-security-and-data-access-policies.md) · Next: 105 — Locks, blocking, deadlocks, and troubleshooting (planned)

## 1. Objectives, prerequisites, and scenario (0–5 minutes)

After this chapter, you can (1) classify sensitive fields and distinguish pseudonymization, masking, hashing, tokenization and encryption; (2) build least-exposure query projections; (3) explain why a masked SELECT is not a security boundary; (4) design useful audit evidence without logging secrets; (5) validate redaction and audit completeness on synthetic records. Prerequisite: [103 — Row-Level Security](103-row-level-security-and-data-access-policies.md).

**Scenario:** A fictional healthcare claims reporting team needs aggregate claim totals and a support-friendly contact view. The source may contain identifiers, email addresses and claims amounts. The tutorial uses **invented** names and addresses only; no patient or production records.

## 2. Concepts and responsibility boundaries (5–15 minutes)

| Technique | Purpose | Important limitation |
|---|---|---|
| Data minimization | Avoid collecting/selecting unnecessary fields | Requires inventory and retention decisions |
| Masking/redaction | Show a limited representation (for example, `***@example.test`) | A SELECT expression alone does not stop direct table access |
| Pseudonymization/tokenization | Replace identifiers with controlled surrogates | Reidentification may remain possible; token vault must be protected |
| One-way hashing | Compare or verify suitable inputs without storing plaintext | Unsalted hashes of low-entropy values (emails/IDs) are guessable |
| Encryption in transit/at rest | Protect transport and storage | Authorized query results can still expose plaintext |
| Access controls | Enforce who can read which columns/rows | Need privilege review, policy tests, and bypass-path checks |
| Auditing | Record who accessed/changed what and when | Query logs can themselves leak sensitive literals |

**Portable SQL idea:** project only necessary columns and use `CASE`, `SUBSTRING`, `POSITION` where supported. String syntax and behavior vary across vendors. **PostgreSQL-specific:** `split_part`, `left`, `pg_catalog` views, `security_invoker` views, `pgaudit` extension (if separately installed), and database role semantics. PostgreSQL does **not** provide a universal built-in dynamic data-masking policy feature equivalent to every other platform. Do not assume `pg_stat_activity` or standard PostgreSQL logs are a complete audit trail.

**Classification example:** `claim_id` internal identifier (restricted); `member_email` direct identifier (sensitive); `claim_amount` financial/health-context data (restricted); `claim_status` operational field (context-dependent); `tenant_id` isolation attribute. Classify in your own governance program; this table is not a regulatory determination. HIPAA/PHI requirements, where applicable, need organizational legal/compliance assessment, not just a SQL mask.

## 3. Worked SQL patterns and expected results (15–30 minutes)

### A. Least-exposure projection — portable concept

```sql
-- Synthetic inline rows. No table access or writes.
WITH claims(claim_id, tenant_id, member_email, amount, status) AS (
  VALUES (201,10,'alex@example.test',40.00,'PAID'),
         (202,10,'blair@example.test',60.00,'OPEN'),
         (203,20,'casey@example.test',25.00,'PAID'),
         (204,20,'drew@example.test',75.00,'OPEN')
)
SELECT tenant_id, status, COUNT(*) AS claim_count, SUM(amount) AS total_amount
FROM claims
GROUP BY tenant_id, status
ORDER BY tenant_id, status;
```

Expected: tenant 10 OPEN 1/60.00, PAID 1/40.00; tenant 20 OPEN 1/75.00, PAID 1/25.00. The result intentionally excludes email addresses. Aggregate outputs can still disclose sensitive information for very small groups: apply minimum group sizes, suppression, or differential privacy where the threat model requires them.

### B. Redacted contact view — PostgreSQL-specific illustration

```sql
WITH contacts(email) AS (
  VALUES ('alex@example.test'), ('blair@example.test')
)
SELECT left(split_part(email, '@', 1), 1) || '***@' ||
       split_part(email, '@', 2) AS masked_email
FROM contacts ORDER BY email;
```

Expected: `a***@example.test` and `b***@example.test`. This is **display masking**, not anonymization: first letter and domain remain visible. For malformed, NULL, internationalized, or unusually short addresses, define explicit handling; do not silently leak unmasked values.

### C. A safe access boundary requires grants and policy design

**Illustrative PostgreSQL 18 DDL — do NOT run in the read-only lab:**

```sql
-- Only on a separate approved disposable database, after role review.
-- A dedicated view owner must not expose the base table through other grants.
CREATE VIEW support_claims WITH (security_barrier = true) AS
SELECT claim_id, tenant_id, status,
       left(split_part(member_email, '@', 1), 1) || '***@' ||
       split_part(member_email, '@', 2) AS masked_email
FROM claims;
-- Separately grant SELECT on this view to a least-privilege support role.
-- Revoke direct access to claims and verify effective privileges.
```

A `security_barrier` view helps constrain optimizer reordering of potentially leaky functions; it does not replace privilege isolation, nor guarantee leak-proof behavior. View ownership and RLS context matter: PostgreSQL views use owner privileges by default; `security_invoker = true` changes the access model and may require base-table grants, defeating a view-only design. Choose and test the model deliberately. Column grants, default privileges, function permissions, `COPY`, exports, backups, replicas, BI extracts and service logs also belong in the threat model. Never assume masking is sufficient for compliance.

### D. Audit requirements

Minimum useful audit fields: UTC event timestamp, actor/service identity, approved request/correlation ID, operation, object or dataset identifier, authorization outcome, policy version, and protected event integrity/retention metadata. Record **metadata rather than full SQL parameters or sensitive result values**. Application audit events and database audit facilities are complementary, not interchangeable. PostgreSQL `log_statement` can log SQL literals; consider log access, redaction, retention and vendor/extension behavior before enabling any logging in a sensitive environment. The `pgaudit` extension requires installation/configuration and operational testing; it is not automatically available.

## 4. Hands-on lab (30–50 minutes)

Run only with an unprivileged identity against a disposable **PostgreSQL 18** database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/104-sensitive-data-masking-audit.sql
```

[Lab 104](../labs/104-sensitive-data-masking-audit.sql) uses a read-only transaction, version/database guard, local timeouts, inline fictional claims, deterministic aggregation and masking, synthetic audit-event metadata, two-way `EXCEPT ALL` assertions, and `ROLLBACK`. It does **not** create roles, views, audit extensions, or logging configuration.

**Exercises:** (A) identify fields not needed for the report; (B) explain why email masking still leaves reidentification risk; (C) verify all four synthetic claim rows are represented in the aggregate; (D) find any synthetic audit events missing required metadata; (E) propose a least-privilege integration test for a support role on a disposable database.

**Calculated expected output:** four claims; total 200.00; four grouped report rows; masked contacts `a***@example.test`, `b***@example.test`, `c***@example.test`, `d***@example.test`; three synthetic audit events, zero missing metadata; zero assertion mismatches. These are **calculated**, not observed PostgreSQL execution results.

## 5. Troubleshooting, guardrails and DBRE/SRE checklist (50–55 minutes)

| Symptom | Investigate | Safe response |
|---|---|---|
| Masked view looks correct but raw emails are readable | Base-table grants, ownership, inherited roles, other views, exports | Remove unauthorized paths through approved change management; test as actual role |
| Missing audit entries | App-to-DB attribution, failed queries, extension configuration, logging gaps | Document coverage and test both successful and denied access |
| Logs contain sensitive literals | Query logging, error traces, bind parameters, BI tooling | Restrict and sanitize logs, review retention and access; do not paste real logs into tutorials |
| Hashes appear reversible by guessing | Low-entropy input, absent keyed design, weak secret handling | Review keyed/tokenized design with security team |
| Aggregates reveal individuals | Tiny groups, repeated differencing queries | Apply suppression/minimum cohort controls where appropriate |
| Policy change causes broken queries | Effective privileges, RLS, view owner, application role | Stage and regression-test; do not bypass security to restore service |

**Production change gate:** data owner + security approval, classification inventory, purpose limitation, threat model, service identity, approved audit scope, log retention, backup/export exposure, least-privilege verification, negative tests, rollback, monitoring and independent sign-off. Never execute production permission, logging or schema changes from a tutorial.

## 6. Review questions with answers (55–60 minutes)

1. **Is a masked SELECT sufficient to protect the base table?** No; enforce permissions and verify every access path.
2. **Is `a***@example.test` anonymous?** No; it retains identifying clues.
3. **Does encryption at rest protect a SELECT result from an authorized but overprivileged user?** No.
4. **Can PostgreSQL query logging expose sensitive values?** Yes, depending on configuration and SQL.
5. **What does an audit record need to support an investigation?** Trusted actor, time, action, object, outcome, correlation and retention/integrity controls.
6. **Does this lab test real PostgreSQL audit logging or grants?** No; it tests only a synthetic metadata and redaction model.
7. **What must be tested before a masking view is deployed?** Direct base-table denial, role inheritance, view ownership/RLS, export paths, negative tests and expected results.

## References

- [PostgreSQL 18 — Privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [PostgreSQL 18 — CREATE VIEW](https://www.postgresql.org/docs/18/sql-createview.html)
- [PostgreSQL 18 — Row Security Policies](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [PostgreSQL 18 — Error Reporting and Logging](https://www.postgresql.org/docs/18/runtime-config-logging.html)
- [pgAudit project documentation](https://github.com/pgaudit/pgaudit)
- [NIST Privacy Framework](https://www.nist.gov/privacy-framework)

**Validation state:** authored/published after GitHub confirmation; targeted manual/static inspection only. Independent editorial review, comprehensive automated SQL parser/link QA and actual isolated PostgreSQL 18 execution remain pending.
