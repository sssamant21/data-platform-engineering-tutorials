# Chapter 16 — Security, Roles, Secrets and Compliance

**Audience:** DBRE/SRE, platform and application engineers. **Duration:** 60 minutes. **Status:** Authored, not runtime-validated or independently reviewed.

## Outcomes and prerequisites
Explain PostgreSQL identity and privilege boundaries; design least-privilege roles; evaluate TLS, `pg_hba.conf`, secret rotation and audit evidence. Prerequisites: Chapters 01–15, Docker Desktop with Linux containers, PostgreSQL 17 image, terminal with Docker CLI. All examples are for disposable local infrastructure; never apply to production.

## 60-minute teaching plan
| Minutes | Activity |
|---|---|
| 0–10 | Threat model and shared responsibility |
| 10–20 | Authentication versus authorization |
| 20–30 | Role hierarchy, schemas, default privileges |
| 30–45 | Run isolated role and privilege lab |
| 45–53 | TLS, secrets, auditing, compliance |
| 53–60 | Troubleshooting, evidence, acceptance |

## Architecture and fundamentals
Application → network boundary/TLS → `pg_hba.conf` authentication → login role → membership/inheritance → database CONNECT → schema USAGE → table privileges → row-level security (if configured). Authentication answers **who connects**; authorization answers **what can be done**. `PUBLIC` is the implicit group of all roles. Database, schema, sequence and table grants are distinct. `ALTER DEFAULT PRIVILEGES` affects only objects subsequently created by a specified creating role. Existing objects require separate grants. RLS is an additional policy layer, not a replacement for object privileges; table owners and roles with BYPASSRLS may bypass it.

### Recommended role model
- `app_owner`: NOLOGIN owner of schema/objects; not used by runtime connections.
- `app_reader`: NOLOGIN privilege bundle, SELECT only.
- `app_writer`: NOLOGIN privilege bundle, minimal DML.
- `app_login`: LOGIN role with membership in only required bundles; no SUPERUSER, CREATEDB, CREATEROLE, REPLICATION or BYPASSRLS.
- Separate migration identity from runtime application identity; use short-lived access and centralized secret management when available.

Use SCRAM-SHA-256 for password authentication; TLS with server certificate validation for remote connections. The lab intentionally uses local container socket connections and does **not** prove TLS, secret rotation or enterprise compliance. Avoid passwords in shell history, code, CI logs and connection strings; never rely on `trust` for remotely reachable production services. Inspect `pg_hba_file_rules` and `pg_settings` with appropriately privileged accounts. Record version, role grants, owner, access review, audit-retention policy and exception approvals; avoid recording credentials or patient data.

## Guided SQL examples
Run the [isolated lab](../labs/chapter-16/README.md). Example inspection:
```sql
SELECT current_user, session_user;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname LIKE 'ch16_%' ORDER BY rolname;
SELECT grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_schema='ch16_demo' AND table_name='tickets' ORDER BY grantee, privilege_type;
```
Expected: a runtime login without elevated role flags, a reader bundle with SELECT but no INSERT, and a writer bundle with explicitly scoped DML. Results depend on execution context and memberships.

## Enterprise guardrails and rollback
Never change `pg_hba.conf`, `password_encryption`, `ssl`, `PUBLIC` grants, RLS or role memberships on a live fleet without impact analysis, application-owner approval, staged connectivity testing and rollback. `REVOKE` can break running applications. Prefer isolated changes with tested service accounts, explicit maintenance windows and emergency access plans. Lab cleanup removes only uniquely named disposable container/volume objects; no production commands.

## Troubleshooting
| Symptom | Diagnosis | Safe action |
|---|---|---|
| `permission denied for schema` | Missing USAGE | Check schema grants, owner and effective role |
| `permission denied for table` | Missing table privilege | Check grants and membership; do not grant ALL |
| `permission denied for sequence` | Serial/identity sequence access | Grant only required sequence rights |
| `no pg_hba.conf entry` | Authentication rule mismatch | Inspect rules, source address, SSL mode; stage changes |
| `password authentication failed` | Invalid secret or auth mechanism | Verify secret manager reference and SCRAM support without exposing password |
| `must be owner of table` | DDL owner mismatch | Use controlled migration role, not superuser shortcut |

## Acceptance checklist
- [ ] Explain authentication, authorization and object ownership separately.
- [ ] Demonstrate reader SELECT succeeds and reader INSERT is denied.
- [ ] Demonstrate writer DML works without elevated flags.
- [ ] Identify schema/table/default privilege boundaries.
- [ ] Describe safe secret rotation, TLS verification and audit evidence.
- [ ] Confirm cleanup scope and record actual runtime evidence separately.

## Official references (PostgreSQL 17)
- [Database roles](https://www.postgresql.org/docs/17/user-manag.html)
- [Privileges](https://www.postgresql.org/docs/17/ddl-priv.html)
- [GRANT](https://www.postgresql.org/docs/17/sql-grant.html)
- [ALTER DEFAULT PRIVILEGES](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html)
- [Client authentication](https://www.postgresql.org/docs/17/client-authentication.html)
- [SCRAM authentication](https://www.postgresql.org/docs/17/auth-password.html)
- [SSL support](https://www.postgresql.org/docs/17/ssl-tcp.html)
- [Row security](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)
- [Error reporting and logging](https://www.postgresql.org/docs/17/runtime-config-logging.html)
