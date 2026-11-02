# PostgreSQL V02-D — Chapters 071–080 Phase One Static Safety Review

**Date:** 2026-11-02  
**Scope:** HA-manager, multi-zone and multi-region DR (071–075), plus roles, authentication, RLS, encryption and security-operations labs (076–080).  
**Certification:** **NOT_CERTIFIED**. **Runtime:** NOT_EXECUTED. **Independent review:** PENDING.  
**Method:** Static chapter/lab inventory, high-risk SQL and documentation safety review, regression checks; no database or production system contacted.

## Findings and changes

| Finding | Severity | Evidence | Corrective action |
|---|---|---|---|
| PG-V02D-076 | HIGH | Original security fixture created six **cluster-wide roles** and a database without a target-identity check before the first DDL | Added one-time system ID/PGDATA/version/localhost/role/database/role-collision gate; recheck after `\\connect`; explicit stage token; fail with SQL exception instead of a successful `\\quit` |
| PG-V02D-078 | HIGH | Original RLS fixture created three **cluster-wide roles** and a database without target identity or existing-object guard | Added identical fail-closed checks and lab instructions for the Chapter 004 disposable cluster |
| PG-V02D-075 | MEDIUM | HA capstone marker used `CREATE TABLE IF NOT EXISTS` and `ON CONFLICT DO NOTHING`, concealing stale data | Changed example to fresh-table CREATE and plain unique-key INSERT; preexisting fixture must block the rehearsal |
| PG-V02D-071–074 | REVIEWED | HA, DCS quorum, partition and cross-region exercises are potentially destructive | Existing fencing and lab-only boundaries retained; **no failover or promotion** tested |
| PG-V02D-077/079/080 | REVIEWED | TLS, secrets, encrypted backup and incident scenarios require real credentials, keys and providers | Inspection and acceptance remain pending; no mocked provider assurance or insecure defaults added |

### Restrictions

For Chapters 076 and 078, the lab now instructs the operator to verify the Chapter 004 `PG_LAB_ROOT/LAB_MARKER`, ownership, actual system ID, exact PostgreSQL 18 PGDATA, role `lab_admin`, localhost port 55432, a **new** target database and **unused** role names. Each SQL fixture checks those values before creating any cluster-wide objects, then again before writing schema objects. It refuses unexpected existing database/role state or a missing stage token.

**No SQL parameter independently proves a host is disposable**: an operator could provide a production system ID. Verifying the lab marker, host isolation, credentials and source ownership is separately mandatory. `CREATE DATABASE` and role creation are not one globally atomic operation; a mid-script failure can leave partial resources. Do not blindly rerun or automatically drop roles and data.

### What the tests do and do not prove

The [Phase 1 offline suite](test_v02d_ch071_080_phase1.py) checks ten chapter/lab pairs, linked documentation, non-mutating inspection SQL, identity gates in Chapters 076/078, collision-failing Chapter 075 example, and explicit pending/fencing boundaries. The [CI workflow](../../.github/workflows/postgresql-v02d-ch071-080-phase1.yml) executes Python-only static inspection.

A green run proves the files contain expected safety contracts; it does **not** execute SQL, verify PostgreSQL 18 privilege or RLS semantics, authenticate TLS or keys, establish independent DCS/fencing, perform a production-like failover, or certify a control.

### Subsequent milestones

1. Execute Chapter 076/078 fixtures and separate-client positive/negative permission tests **only on disposable PostgreSQL 18**, including wrong system ID/PGDATA/role/token/existing-role/database cases, and review partial-creation behavior.
2. Validate Chapter 077 TLS hostname/CA/SCRAM rejection cases, Chapter 078 cross-tenant RLS+column restrictions, and Chapter 079/080 authentication/logging controls in an isolated, independently approved security lab.
3. Before running any 071–075 HA exercise, obtain **separately managed quorum and independently proven old-primary fencing**, routing controls, approved failure-injection and rollback. Simulated zones/regions do **not** count as actual resilience.
4. Retain an independent DBRE/security/application/DR owner review. No enterprise certification before authenticated evidence.

**Previous batch:** [PR #46](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/46) has 9/9 green CI checks and remains draft pending independent review [issue #47](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/47). Chapter 050 V04-G remains blocked in [issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45). Neither issue is resolved by this batch.
