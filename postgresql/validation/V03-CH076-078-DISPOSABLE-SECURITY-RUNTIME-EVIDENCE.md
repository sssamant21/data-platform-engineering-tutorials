# PostgreSQL V03 — Chapters 076 and 078 Disposable Security Runtime Evidence

**Status:** **69/69 actual PostgreSQL 18 checks passed**.  
**Executed workflow:** [#41544831279](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41544831279) — completed PASS. Separate push workflow [#41544822162](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41544822162) also completed PASS.  
**Runtime implementation:** [v03_ch076_078_security_disposable.py](v03_ch076_078_security_disposable.py)  
**Workflow:** [postgresql-v03-ch076-078-security.yml](../../.github/workflows/postgresql-v03-ch076-078-security.yml)  
**Certification:** **NOT_CERTIFIED**; independent security review and staging acceptance remain **PENDING**.

## Actual runtime boundaries

The runner creates **one disposable PostgreSQL 18 Docker server** with Docker `--network none`, no published host ports, localhost TCP on port 55432 and a uniquely named PostgreSQL data directory inside a temporary container filesystem. It supplies the *observed* system identifier and PGDATA to the one-time guarded Chapter 076/078 SQL scripts. All resources are removed with the disposable container after the job.

**Important:** CI deliberately uses `POSTGRES_HOST_AUTH_METHOD=trust` inside that isolated container to permit independent per-role sessions without test credentials. This validates real PostgreSQL LOGIN-role permissions and RLS enforcement, **not** password authentication, SCRAM, TLS, identity-provider access, HBA restrictions or production security configuration. Never copy this trust configuration to a shared or remotely accessible database.

## Positive and negative execution matrix

| Area | Actual PostgreSQL check | Outcome |
|---|---|---|
| Fixture targeting | PostgreSQL 18/version, observed PGDATA/system identifier, localhost and stage token | PASS |
| Fixture refusal | Missing/wrong system ID, wrong PGDATA, wrong stage, wrong database, wrong calling role | PASS |
| Fixture reuse | Prior schema/database and cluster-wide roles prevent reapplying each chapter | PASS |
| 076 application | Actual login, INSERT/SELECT/UPDATE/DELETE, table/sequence privileges | PASS |
| 076 analyst | Separate LOGIN SELECT permitted, INSERT/UPDATE denied with SQLSTATE 42501 | PASS |
| 076 monitor | Monitoring view readable, application INSERT denied | PASS |
| 076 membership | Membership SET option false; SET ROLE attempts rejected | PASS |
| 076 default privileges | Owner-created future table inherits allowed grants; admin-created table does not | PASS |
| 078 RLS | FORCE ROW LEVEL SECURITY set; tenant roles have no BYPASSRLS | PASS |
| 078 isolation | Tenant A and B each see only their rows; cross-tenant SELECT is invisible | PASS |
| 078 mutations | Own-row INSERT/DELETE allowed; cross-tenant INSERT/UPDATE rejected with SQLSTATE 42501; other tenant's row preserved | PASS |
| 078 sensitive columns | Secret-note column SELECT rejected for both tenant roles | PASS |

The test emits **69 recorded checks** and requires all to succeed. The GitHub Actions artifact contains only synthetic case names and PASS booleans, with no SQL row content, passwords, external endpoints, private keys or patient information.

## Pending acceptance — do not infer from CI

- **Chapter 076:** Real SCRAM/password authentication, privileged role provisioning by a controlled identity system, audit trail, session/pool behavior, service-account rotation, security approval.
- **Chapter 077:** TLS server certificate SAN validation, client `sslmode=verify-full`, HBA first-match behavior, plaintext/untrusted-CA/wrong-host/wrong-password rejection. **No Chapter 077 runtime has been executed by this milestone.**
- **Chapter 078:** Real password and TLS identity enforcement, tenant context in a connection pool, logging/pgaudit, privileged owner bypass/forced policy edge cases, independent security review. Owner and superuser semantics must not be confused with tenant safety.
- **Chapters 079–080:** Secrets management, encrypted backup/key recovery, audit collector incidents and provider evidence remain unverified.
- **Chapters 071–075:** Independent old-primary fencing, DCS/quorum, HA routing, failover and multi-zone/region resilience remain **NOT VERIFIED / NO_GO**. Do not execute a promotion/partition solely because this CI passed.
- **Enterprise certification:** Independent DBRE, security and application-owner review and source-authenticated evidence in an approved private system are still required.

The lab **does not contact any external cluster or run any production/staging operation**. The green run supports a narrow PostgreSQL 18 disposable security milestone only.

**Next suggested validation:** Chapter 077 isolated TLS/SCRAM/pg_hba positive/negative tests, followed by Chapter 079/080 security control verification. Keep [PR #48](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/48) draft and unmerged until independent review. Separate [PR #46](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/46) and [Issue #47](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/47) concern Chapters 061–070; Chapter 050 V04-G remains blocked under [Issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45).
