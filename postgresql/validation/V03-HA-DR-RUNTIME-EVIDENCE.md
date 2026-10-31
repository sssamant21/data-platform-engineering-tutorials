# PostgreSQL V03 — Chapters 045, 049–050 HA/DR Runtime Evidence

**Evidence date:** 2026-10-31 UTC  
**Branch:** `qa/postgresql-v03-slot-preflight-20261030`  
**Disposition:** **ISOLATED_LAB_PASS / ENTERPRISE_HA_DR_NOT_CERTIFIED**

This evidence records verified GitHub Actions runs against fresh, non-root, **network-disabled PostgreSQL 18** containers. No production database or shared environment was used.

## Verified run A — Chapter 045 independent PITR recovery

- [Successful workflow run #41154850818](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41154850818); harness: [v03_pitr_disposable.py](v03_pitr_disposable.py).
- Source identity, PG18 major and ephemeral data-directory checks: **PASS**.
- `pg_basebackup` and `pg_verifybackup` with backup manifest: **PASS**.
- Committed `known-good` marker and named WAL restore point before deliberately corrupting 100 synthetic rows: **PASS**.
- WAL segment archive after the bad update and separate newly copied restored PGDATA: **PASS**.
- Recovery paused at named point, `recovery.signal` plus `restore_command`, and exact source-cluster identifier: **PASS**.
- Existing `045-verify.sql` on recovered target checked 1,000 valid rows, known-good marker, **zero corrupted rows**: **PASS**.
- Wrong recovered-PGDATA path rejected with nonzero `psql` exit: **PASS**.
- **Observed laboratory incident-to-verification interval: 1.872 seconds.** Includes this synthetic workload only; does not establish operational RTO, business data-loss tolerance or application cutover.
- No target promotion was performed. Source and recovery data directories were not overwritten by an unsafe generic cleanup.

## Verified run B — Chapters 049–050 planned local HA switchover

- [Successful workflow run #41154724454](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41154724454); harness: [v03_ha_disposable.py](v03_ha_disposable.py).
- Exact Chapter 004 18.x three-node topology and explicit stage tokens: **PASS**.
- Committed marker `id=490` replayed on both standbys before any shutdown: **PASS**.
- **Planned local shutdown fence:** original A and unused standby 2 stopped, old TCP writer port refused connections before promotion: **PASS (lab only)**.
- Promoted the selected candidate only after local fence checks; WAL timeline **00000001 → 00000002** and new writer **55433** confirmed: **PASS**.
- Exactly one reachable lab writer; pre-fence acknowledged marker survived promotion: **PASS**.
- **Observed synthetic-marker loss: zero** for this one witnessed acknowledged transaction; async replication does not guarantee zero loss for arbitrary writes.
- **Observed laboratory service restoration: 0.376 seconds**, measured local stop through SQL read smoke test; not measured application traffic restoration.
- `pg_rewind --dry-run`: **PASS**; preserved old primary PGDATA; **actual rewind NOT EXECUTED**.
- Fresh `pg_basebackup -R` to a separate empty directory, `standby.signal` / `primary_conninfo`, and catch-up as standby on old loopback port **55432**: **PASS**. This is a rebuild demonstration, **not** an in-place former-primary rewind.

## New isolated actual-rewind test — pending final runtime evidence

- Harness: [v03_rewind_disposable.py](v03_rewind_disposable.py).
- Workflow: [PostgreSQL V03 Disposable Actual Rewind Acceptance](../../.github/workflows/postgresql-v03-actual-rewind-disposable.yml).
- This newly added test is not equivalent to the already verified dry-run and fresh-backup rebuild. It checks a bounded in-place rewind only on a newly generated, identified Chapter 004 data directory with a preserved copy of the original.
- **Current status in this evidence document:** **PENDING confirmation of the actual job's outcome**. A green result must additionally show safe standby startup, post-promotion marker replay and exactly one writable node.
- Independently proven production fencing, real application failover and business RPO/RTO must not be inferred from successful CI.

## Safety constraints and explicit exclusions

| Gate | Disposition |
|---|---|
| PostgreSQL 18 isolated PITR backed by physically verified backup and WAL replay | LAB PASS |
| PostgreSQL 18 controlled planned switchover with local stop/port refusal | LAB PASS |
| Old primary independently fenced across host, storage, orchestration, network, and client access paths | **NOT PROVEN** |
| Actual `pg_rewind` of former primary and rollback/failure behavior | **NOT EXECUTED** |
| Real application DNS/proxy routing and read/write smoke-test cutover | **NOT EXECUTED** |
| Enterprise HA RPO/RTO against approved SLO thresholds | **NOT MEASURED** |
| Enterprise PITR RPO/RTO and durable remote WAL archive | **NOT MEASURED / NOT PROVEN** |
| Chaos/forced crash, archive gaps, lagged candidate, standby conflict and fail-closed manual approvals | **PENDING** |
| Independent DBRE/security/application owner validation and formal production authorization | **PENDING** |

## Mandatory next acceptance actions

1. Review CI logs, confirm all static and runtime workflows on the final code-bearing commit, and have an independent DBRE reviewer attest to the lab isolation boundary.
2. Run an **independently fenced** failover rehearsal in approved staging, demonstrating that old A cannot return as writer due to a surviving restart or bypass route. Stop immediately when uncertain.
3. Execute a separately reviewed in-place `pg_rewind` on an intentionally backed-up and confirmed isolated former-primary target, plus failure injection and rebuild fallback.
4. Validate real application routing, archive durability and retention, measured HA and PITR business RPO/RTO, recovered business invariants and alerts.
5. Fill every mandatory Chapter 050 scorecard row with an operator, UTC timestamps, exit codes/log evidence and independent sign-off. **Do not merge/certify based only on these disposable CI results.**
