# Level 5 — Snowflake Security, RBAC, and Governance

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — static review pending; live Snowflake validation NOT RUN  
**Audience:** DBRE/SRE, IAM, security, governance and data platform teams  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Explain role hierarchy, investigate access errors and design safe governance controls without modifying live privileges.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| Identity and authentication patterns | 10 min |
| Roles and least privilege | 15 min |
| Data masking, row policies and audits | 10 min |
| Read-only RBAC investigation lab | 20 min |
| Review | 5 min |
| **Total** | **60 min** |

## Core concepts
### Identity and authentication
Snowflake supports enterprise authentication options including SSO and strong authentication mechanisms. Workload identities should be managed separately from interactive human users. Require approved MFA/SSO posture, secrets rotation and ownership for automation. Do not paste credentials, tokens or private keys into tutorials or SQL worksheets.

### Role-based access control
A user receives account roles; roles inherit privileges and may inherit from other roles. A typical SELECT path requires suitable USAGE on the database and schema plus SELECT on the table, and warehouse USAGE for compute. Policies such as managed access schemas centralize grant decisions. Prefer a role per purpose over broad grants to PUBLIC.

### Important roles
ACCOUNTADMIN is powerful and should not be the normal operating role. SECURITYADMIN handles security administration, USERADMIN manages identities and roles, SYSADMIN handles many objects, and custom operational roles should be least privileged.

### Governance concepts
- **Masking policies** control visibility of sensitive column values to authorized roles.
- **Row access policies** govern which rows a query can expose.
- **Tags and classifications** help identify sensitive assets.
- **Audit history** helps explain authentication and access behavior.
- Governance features can depend on Snowflake edition, permissions, licensing and configuration.

Healthcare-style examples must use **synthetic data**. Never put actual patient names, dates of birth, email addresses, or identifiers in lab tables or exported query history.

### A sample approval path
Application owner requests SELECT → data owner approves → security reviews access and masking → administrator grants to a role in a change window → validation confirms effective rights → access is periodically recertified.

## Hands-on lab and expected results
### Step 1 — Confirm active principal
~~~sql
SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES();
~~~
Expected: the active principal and roles. `CURRENT_SECONDARY_ROLES()` returns a JSON-encoded VARCHAR describing the requested/activated secondary roles, not a relational list. The active primary role alone may not describe effective access.

### Step 2 — Review the roles assigned to the current user
~~~sql
SHOW GRANTS;
~~~
Expected: roles granted to the **current user**. Without arguments, `SHOW GRANTS` is equivalent to `SHOW GRANTS TO USER current_user`; it is not an inventory of every object privilege in the account.

### Step 3 — Inspect available roles and a designated table
~~~sql
SHOW ROLES;
-- Replace with an approved table in your environment:
-- SHOW GRANTS ON TABLE DBRE_SRE_LAB.TRAINING.ORDERS;
~~~
Expected: visible roles. The commented command requires replacing the identifier and permission to inspect grants.

### Step 4 — Analyze a hypothetical denial (paper exercise)
A user can access \`DBRE_SRE_LAB\` but sees "insufficient privileges" on \`TRAINING.ORDERS\`. Draw a chain of required permissions: warehouse USAGE → database USAGE → schema USAGE → table SELECT. Check the active role and ownership; **do not issue GRANT statements** as a lab step.

### Step 5 — Explain policy-based security
Design a hypothetical analyst role permitted to see regional totals but not individual patient contact information. Identify where a secure view, masking policy, row access policy or aggregation may be appropriate.

**Pass:** document the minimal privilege set, a request approval chain, and the verification needed after granting access.

### Read-only security audit (optional)
With an approved security-monitoring role, inspect **aggregated** login outcomes using the [Level 5 smoke script](validation/runtime/level-05-smoke.sql). `SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY` can lag up to two hours; a missing event is not evidence that no login attempt occurred. Avoid retaining raw usernames, IP addresses or authentication error messages in training artifacts. Without the correct privilege, record the step as **BLOCKED**, not PASS.

## DBRE/SRE troubleshooting quick reference
| Symptom | Evidence | Escalation |
|---|---|---|
| Failed sign-in | Approved login audit + IdP status | IAM/security |
| Access denied | CURRENT_ROLE, SHOW GRANTS, object chain | Data owner/security |
| Unexpected sensitive values | Masking/row policies and active role | Security incident response |
| Key rotation failure | Workload identity and credential owner | IAM / platform |

Production GRANT/REVOKE changes require explicit authorization, ticketing and rollback plans; no credential or sensitive data should be exposed in screenshots.

## Knowledge check (with answers)
1. **What is least privilege?** Only permissions required for a role's purpose.
2. **Can a table SELECT work without required parent USAGE grants?** Generally not.
3. **What protects individual sensitive column values?** Masking or an appropriate secure data-access design.
4. **Should labs contain real patient records?** No.
5. **What should a DBRE do before granting access?** Obtain owner approval and verify privilege scope.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[26 Authentication](../26-snowflake-authentication.md), [27 Role Hierarchy](../27-rbac-role-hierarchy.md), [33 Dynamic Masking](../33-dynamic-data-masking.md), [35 Governance](../35-tags-classification-governance.md)

## Official documentation
- https://docs.snowflake.com/en/user-guide/security-access-control-overview
- https://docs.snowflake.com/en/sql-reference/sql/show-grants
- https://docs.snowflake.com/en/sql-reference/functions/current_secondary_roles
- https://docs.snowflake.com/en/sql-reference/account-usage/login_history
- https://docs.snowflake.com/en/sql-reference/account-usage

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
