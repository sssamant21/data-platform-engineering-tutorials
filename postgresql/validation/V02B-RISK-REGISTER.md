# PostgreSQL V02-B — Safety-pattern triage register

**Date:** 2026-10-30 · **Source:** 37 matches retained in the [V02 parser evidence](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41054743458) · **Branch:** `qa/postgresql-v01-static-validation-20261030`.

**Scope:** Static review of all 37 risk-pattern entries in the first successful V02 audit. A match is a review candidate, *not* automatically a bug or executed command. Classification reflects the inspected script contents and, for edited cleanup/incident scripts, the revised QA branch. **No live PostgreSQL test has occurred.**

## Review inventory

| # | Source | Pattern | Classification | Finding and runtime gate |
|---:|---|---|---|---|
| 1 | `postgresql/labs/sql/032-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 2 | `postgresql/labs/sql/033-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 3 | `postgresql/labs/sql/033-investigate.sql` | reindex | REVIEW_RUNTIME | Concurrent REINDEX and invalid-index cleanup need standalone-session tests |
| 4 | `postgresql/labs/sql/034-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 5 | `postgresql/labs/sql/034-investigate.sql` | delete | BOUNDED_FIXTURE | DELETE WHERE id BETWEEN 20001 AND 30000; prove fixture identity |
| 6 | `postgresql/labs/sql/034-investigate.sql` | update | BOUNDED_FIXTURE | UPDATE WHERE id BETWEEN 1 AND 20000; prove fixture identity |
| 7 | `postgresql/labs/sql/035-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 8 | `postgresql/labs/sql/035-investigate.sql` | delete | BOUNDED_FIXTURE | DELETE bounded to ch035 fixture; test runtime and isolation |
| 9 | `postgresql/labs/sql/035-investigate.sql` | update | BOUNDED_FIXTURE | UPDATE bounded to ch035 fixture; test runtime and isolation |
| 10 | `postgresql/labs/sql/036-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 11 | `postgresql/labs/sql/036-investigate.sql` | delete | BOUNDED_FIXTURE | DELETE bounded to ch036 fixture; test runtime and isolation |
| 12 | `postgresql/labs/sql/036-investigate.sql` | update | BOUNDED_FIXTURE | UPDATE bounded to ch036 fixture; test runtime and isolation |
| 13 | `postgresql/labs/sql/037-investigate.sql` | delete | BOUNDED_FIXTURE | DELETE bounded to ch037 fixture; setup may append on rerun |
| 14 | `postgresql/labs/sql/037-investigate.sql` | update | BOUNDED_FIXTURE | UPDATE bounded to ch037 fixture; require dedicated database |
| 15 | `postgresql/labs/sql/038-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 16 | `postgresql/labs/sql/039-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 17 | `postgresql/labs/sql/040-cleanup.sql` | drop_schema | GATED_STATIC | Cluster/database/token guard; runtime denial tests pending |
| 18 | `postgresql/labs/sql/045-incident.sql` | update | GATED_STATIC | Deliberate corruption drill now guarded by incident token and cluster ID |
| 19 | `postgresql/labs/sql/047-cleanup.sql` | drop_schema | GATED_STATIC | Slot inactive/type checks plus cluster/database/token before slot drop |
| 20 | `postgresql/labs/sql/047-generate-wal.sql` | update | BOUNDED_FIXTURE | ON CONFLICT UPDATE of 2,000 bounded fixture IDs; runtime pending |
| 21 | `postgresql/labs/sql/048-cleanup.sql` | drop_schema | GATED_STATIC | Lab schema existence plus cluster/database/token guard |
| 22 | `postgresql/labs/sql/048-workload.sql` | update | BOUNDED_FIXTURE | ON CONFLICT UPDATE of 5,000 bounded fixture IDs; runtime pending |
| 23 | `postgresql/labs/sql/053-verify.sql` | delete | RLS_TEST | Tenant-owned test row inserted/deleted; verify real role restrictions |
| 24 | `postgresql/labs/sql/053-verify.sql` | update | RLS_TEST | Includes expected-denied cross-tenant update; assert SQLSTATE/runtime |
| 25 | `postgresql/labs/sql/078-rls-fixture.sql` | update | PRIVILEGE_TEXT | UPDATE privilege grant/policy declaration, not fixture modification |
| 26 | `postgresql/scripts/004-operations-lab.sh` | recursive_delete | GATED_STATIC | Nonroot lab-owned path/marker and mount check, explicit destroy token |
| 27 | `postgresql/scripts/004-operations-lab.sh` | pg_stop | GATED_STATIC | Stops identified disposable instances using PG_LAB_ROOT; runtime pending |
| 28 | `postgresql/scripts/011-provision-lab.sql` | update | PRIVILEGE_TEXT | GRANT UPDATE privilege; not a standalone UPDATE statement |
| 29 | `postgresql/scripts/011-role-access-inspection.sql` | truncate | PRIVILEGE_TEXT | TRUNCATE is queried as an access privilege, not executed |
| 30 | `postgresql/scripts/011-runtime-acceptance.sql` | truncate | EXPECTED_DENIAL | TRUNCATE attempted under restricted role, expected SQLSTATE 42501 |
| 31 | `postgresql/scripts/011-runtime-acceptance.sql` | delete | EXPECTED_DENIAL | DELETE attempted under restricted role, expected SQLSTATE 42501 |
| 32 | `postgresql/scripts/011-runtime-acceptance.sql` | update | ROLLED_BACK_FIXTURE | Transactional lab write explicitly ROLLBACK, runtime pending |
| 33 | `postgresql/scripts/017-provision-isolation-lab.sql` | update | PRIVILEGE_TEXT | GRANT UPDATE privilege; not a standalone UPDATE statement |
| 34 | `postgresql/scripts/017-reset-isolation-lab.sql` | update | GATED_RUNTIME_PENDING | Specific lab reset; checks role/DB/transactions/fixture shape |
| 35 | `postgresql/scripts/018-provision-lock-lab.sql` | update | PRIVILEGE_TEXT | GRANT UPDATE privilege; not a standalone UPDATE statement |
| 36 | `postgresql/scripts/018-reset-lock-lab.sql` | update | GATED_RUNTIME_PENDING | Specific lab reset; checks role/DB/transactions/fixture shape |
| 37 | `postgresql/scripts/020-reviewed-session-signal.sql` | backend_signal | GATED_RUNTIME_PENDING | Bounded PID/start/state/app/role and cancel/terminate confirmation; nonrollbackable signal |

## Classification counts

- **GATED_STATIC:** 13 matches
- **REVIEW_RUNTIME:** 1 match
- **BOUNDED_FIXTURE:** 10 matches
- **RLS_TEST:** 2 matches
- **PRIVILEGE_TEXT:** 5 matches
- **EXPECTED_DENIAL:** 2 matches
- **ROLLED_BACK_FIXTURE:** 1 match
- **GATED_RUNTIME_PENDING:** 3 matches

**Total matches triaged: 37/37.** These classes do not translate to enterprise approval.

## Confirmed code changes

- Removed automatic `DROP SCHEMA IF EXISTS ... CASCADE` from setup files 032–036.
- Added fail-closed three-input preflight to all 10 remaining `labs/sql/*-cleanup.sql` files, checking expected database, PostgreSQL 18 cluster system identifier and chapter-specific confirmation token, plus rejecting standby targets. Chapter 047 also retains slot state/type checks.
- Updated corresponding 10 lab guides so the manual cleanup command supplies the required variables.
- Guarded the deliberate `labs/sql/045-incident.sql` PITR failure injection with an exact database/cluster match, existence of its synthetic fixture and an incident-specific token; updated its lab guide.
- Added `validate_v02b.py` to fail CI if cleanup safeguards, guide arguments, or no-drop setup invariant regress.

## Open acceptance requirements

1. **Guard-negative tests:** on a disposable PG18 cluster, omit each variable and supply wrong database, wrong identifier, wrong token and standby; record nonzero exit and zero changes. Repeat with correctly approved values; verify precisely the intended lab objects were removed.
2. **Bounded DML:** verify affected row counts and schema ownership for Chapters 034–037, 047–048. Investigate repeated-run behavior of Chapter 037 setup before accepting its outputs.
3. **DDL and RLS:** validate concurrent index build/rebuild behavior and SQLSTATE-specific denial tests in the appropriate role.
4. **Shell destruction and session signals:** verify OS path/marker/ownership/mount protection and backend PID/application identity controls in isolated labs.
5. **Independent reviewer:** sign off on each candidate, test evidence and the absence of unaddressed production-impacting commands.

## Decision

**V02-B initial risk classification: completed (37/37). Automated protection regression: CI gate added. Technical and runtime safety acceptance: pending.** Preserve the V02-A full parser report separately; this is a supplementary human-reviewed triage register, not a replacement for CI evidence.
