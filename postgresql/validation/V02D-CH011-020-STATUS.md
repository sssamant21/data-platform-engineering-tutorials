# PostgreSQL V02-D — Chapter 011–020 Technical and Safety Review

**Date:** 2026-10-30 · **QA branch:** `qa/postgresql-v01-static-validation-20261030`  
**Status:** **Targeted static technical review and regression tests PASS; manual semantic review incomplete; PostgreSQL 18 runtime and enterprise certification NOT EXECUTED.**

## Evidence

- [Passing V02 GitHub Actions #41062449652](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41062449652)
- [Chapters 011–020 deterministic regression tests](test_v02d_ch011_020.py): **10/10 PASS**
- [Chapters 001–010 prior regression tests](test_v02d_ch001_010.py): **8/8 PASS**
- [V02 parser](validate_v02.py): **159/159 SQL files parsed**, 13 standalone Python, 5 Bash, 2 PowerShell and YAML/JSON parsing pass; **0 syntax errors**
- [V02-B cleanup guard presence](validate_v02b.py): pass for prior ten schema-cleanup scripts.
- [V02-C embedded-code scanner](validate_v02c.py): 792 fenced blocks; 666 syntax passes, 22 manual context items (21 context placeholders; one psql-meta-only), 48 possible-destructive blocks and 107 nearby-evidence phrasing flags. These are **heuristics**, not confirmed defects.
- PostgreSQL 18 documentation: [predefined roles](https://www.postgresql.org/docs/18/predefined-roles.html), [SET ROLE](https://www.postgresql.org/docs/18/sql-set-role.html), [client timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html), [server-signaling functions](https://www.postgresql.org/docs/18/functions-admin.html).

**Review boundary:** All snippets remain unexecuted on a PostgreSQL server. The new tests exercise repository contracts, the Chapter 012 HBA state data parser and Chapter 017 retry code with mock connections only.

## Chapter-by-chapter triage

| Chapter | Source and lab checks | Static review outcome | Required runtime proof |
|---|---|---|---|
| **011** Roles, ownership, membership | 011 provision, inventory, runtime denial and **new guarded cleanup** | Membership `INHERIT`/`SET` separation and deliberate SQLSTATE 42501 checks identified; inline destructive cleanup replaced | Authenticate as real runtime/deploy roles, prove allowed/denied operations, validate default ACLs and guarded teardown |
| **012** HBA and authentication | 012 HBA Python staging helper and inspection | Static HBA-state regression tests passed (known original/reject/malformed states; rejects unknown state); no trust auth introduced | Exercise HBA precedence, wrong password vs missing password, malformed reload rejection and restoration |
| **013** TLS certificates | 013 certificate Bash, TLS peer probe Python, SQL inspection | Offline PKI/peer fingerprints and `verify-full` workflow mapped to lab; no CA keys published | Generate lab certificates, prove name/CA failures, peer certificate rotation, previous session vs new session, recovery |
| **014** Secret rotation/service accounts | 014 provision, access-denial and account inventory, **new guarded cleanup** | Distinguishes password rotation from existing-session revocation; original inline database/role teardown replaced | Check old/new credentials and NOLOGIN, target only reviewed idle old session, verify dependencies before dropping blue |
| **015** Audit/network isolation | 015 inspection SQL and lab | Core logging vs optional pgAudit, listener/HBA vs firewall isolation and redaction boundaries documented | Validate actual log classes, rollback of overrides and optional pgAudit on matching build |
| **016** MVCC and snapshots | 016 provisioning and observer SQL | Read-only snapshot, tuple `xmin`/`xmax`, slot and prepared-xact visibility identified | Run two-session snapshots, verify tuple visibility and vacuum caveats in isolation |
| **017** Isolation and retry | 017 provision/reset/observer SQL and transaction retry Python | **Deterministic retry logic tests passed:** commit-time 40001 retry, 40P01 exhaustion, nonretryable 42501, rollback failure, invalid autocommit/attempt limits and jitter | Execute read-committed, repeatable-read and serializable schedules; observe 40001/40P01 with actual database |
| **018** Blocking/deadlocks | 018 provision/reset and recursive-lock query | Directed blocker graph is bounded; deadlock tests acknowledge nondeterministic victim | Generate C→B→A blocking chain, 40P01 event, bounded NOWAIT/strong locks and cleanup |
| **019** Long transactions and timeouts | 019 read-only inspection | Documents 57014/55P03/25P02, `transaction_timeout`, idle timeout and observer-vs-actor scope | Confirm PostgreSQL 18-specific timeout precedence and SQLSTATEs in real connections |
| **020** Session cancellation/termination | 020 snapshot and **hardened signal helper** | Adds exact cluster system identifier, expected data directory, lab_admin role, loopback endpoint to PID/start/query/app/state checks; lab updated | Positive, wrong cluster, wrong token, stale PID, changed query, wrong app, idle-cancel and terminate-negative tests |

Chapter/lab link and required-asset checks for all ten chapters are enforced in the CI suite. These are targeted static checks, not a certification of every example's actual PostgreSQL semantics.

## Remediation details

### PG-V02D-011 — Chapter 011 privileged database/role teardown (HIGH; statically mitigated)

Original lab contained inline `DROP DATABASE c011_db` followed by five `DROP ROLE` statements after an identity/ownership check. A broadly accessible copy/paste was risky, and that check did not prove the exact disposable cluster. New `scripts/011-cleanup-lab.sql` requires:

- Explicit `-v expected_system_id` and `-v confirm_cleanup=011-DROP-ROLES-DB`
- Exact `lab_admin`, `ops_lab`, loopback port 55432, PostgreSQL 18, primary, expected disposable data-directory shape and matching `pg_control_system().system_identifier`
- Exact `c011_db` database owner, all five expected role names and no live sessions in that database

The matching lab guide invokes the guarded script. The SQL can still fail midway on external role dependencies: **DDL across database/role deletion is not atomic**. Never re-run blindly after a partial deletion. Test both refusal and approved success in disposable PG18.

### PG-V02D-014 — Chapter 014 privileged database/role teardown (HIGH; statically mitigated)

New `scripts/014-cleanup-lab.sql` uses the same cluster identity and dedicated `014-DROP-ROLES-DB` token, verifies `c014_db` owner and the four roles expected to survive service-account retirement, and refuses active database sessions. The optional blue role is expected to have been retired earlier in the curriculum; its separate deletion remains a reviewed lab phase. Both lab instructions and CI file-presence checks were updated.

### PG-V02D-020 — Backend signaling had no SQL-level cluster identity guard (HIGH; statically mitigated)

`scripts/020-reviewed-session-signal.sql` now rejects missing `expected_system_id` and requires `lab_admin`, the expected `ops_lab` database, loopback 55432, a PostgreSQL 18 primary and the expected disposable data-directory shape before matching the independently supplied cluster system identifier. Existing exact PID, backend start, query start, state, application name, role and backend-type restrictions remain.

The lab operator must inspect and explicitly provide `PG_LAB_SYSTEM_ID_020`. Its separate interactive idle-cancel teaching example now also checks the disposable cluster identity rather than relying solely on the shell guard. PostgreSQL session signaling is **not reversible by SQL rollback**; true/false results require subsequent observation. These predicates **do not create production authorization**. No session signals were actually sent.

### PG-V02D-017 — Serializable transaction retry helper (MEDIUM; unit-tested)

New test suite mocks database connections, cursors, SQLSTATE errors, commit, rollback and close:
- Retry after a 40001 raised by `commit()`, on a fresh connection
- Exhaust 40P01 attempts and fail correctly
- Reject 42501 without retry
- Fail closed on rollback failure
- Refuse autocommit and invalid retry counts
- Refuse invalid jitter after rollback and close

The helper still needs a Psycopg 3 integration test with a real serialization/deadlock schedule. It deliberately does **not** cover out-of-transaction effects, idempotency keys, connection pool behavior or application deadlines.

## Current scanner accounting

The original V02-B source-file register contained 37 risk matches. Subsequent **guarded** Chapter 007, 011 and 014 cleanup files added three intentional `DROP DATABASE` patterns. The current V02 parser therefore records **40 risk-pattern matches**, not 40 vulnerabilities. The original 37-entry register remains a frozen initial triage; all three new candidates are documented here and in [Chapters 001–010 report](V02D-CH001-010-STATUS.md).

V02-C block counts can change as lab guides are corrected; use the corresponding workflow evidence for a commit-specific count.

## Open quality and runtime gates

1. Prove wrong-cluster, missing-token, incorrect-owner, missing-role, active-session and partially-deleted-state denials for Chapters 011/014 in a disposable PostgreSQL 18 cluster.
2. Exercise real HBA reloads, TLS certificate generation/verification, authentication and password rotation without exposing secrets.
3. Validate role/privilege and default ACL behavior; check actual SQLSTATE 42501 instead of assuming any error means a successful access denial.
4. Confirm `transaction_timeout`, idle-in-transaction/session timeout, concurrent-update anomaly, `40P01`, and `40001` behavior under controlled PostgreSQL 18 conditions.
5. Test Chapter 020 both positive and negative signals with reviewed PIDs while preserving role, database, system identifier, backend start and exact query state; independently confirm that no unexpected actor was signaled.
6. Capture timestamps, exact version, preconditions, commands, exit codes, observed values, rollback and independent reviewer sign-off.

## Decision and next

**Chapters 011–020: static source/contract review and 10/10 targeted tests PASS. Runtime/technical certification PENDING.** All changes are isolated to the QA branch, not `main`.

**Next:** V02-D Chapters **021–030**, including connection/session diagnostics, operational monitoring and action control as defined in the repository's published chapter sequence. Continue static semantic review and targeted deterministic tests, then begin isolated PostgreSQL 18 runtime gates with Chapter 004 when a disposable host is available.
