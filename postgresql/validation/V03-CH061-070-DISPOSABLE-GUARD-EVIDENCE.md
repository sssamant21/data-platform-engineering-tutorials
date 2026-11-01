# PostgreSQL V03 — Chapters 061–070 Disposable PG18 Fixture Guard Runtime

**Verified current guard scope:** **55/55 real disposable PostgreSQL 18 checks PASS** on [run #41312831290](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312831290). Chapters 064, 066, 068 and 070; **one isolated PostgreSQL 18 server** in GitHub Actions using Docker network mode `none`, localhost-only PostgreSQL and no host ports exposed.

**Enterprise certification:** NOT_CERTIFIED. **Actual staging:** NOT_EXECUTED. **No PITR/restore, replication quorum or HA switchover tested.** This gate applies only to the one-time lab SQL fixtures, a physical slot and bounded WAL workload.

## Test design

[The V03 disposable runtime harness](v03_ch061_070_fixture_guards.sh) runs real PostgreSQL 18 `psql` commands. Before execution, it verifies the isolated container network, local PostgreSQL version, data-directory identity and cluster system identifier. It creates four disposable databases and a low-privilege test login **inside that container only**. Database-created fixtures and the replication slot are uniquely named for these exercises; the container is destroyed after the run.

### Positive and negative acceptance

| Chapter | Positive path | Mandatory negative checks |
|---|---|---|
| 064 — PITR fixture | One-time schema and empty event table | Missing/wrong system ID, PGDATA, role, database, stage token and rerun |
| 066 — DR fixture | One-time schema, exactly one reference record | Wrong credentials/identity fields and reused fixture |
| 070 — HA marker | Exactly one committed synthetic marker | Wrong target identity and reused marker |
| 068 — Physical slot | Create physical slot, 1,000-row WAL workload, run an isolated real `pg_receivewal` consumer, **refuse cleanup while slot is active**, then stop consumer and perform guarded cleanup | Wrong system/port/role/database/stage, duplicate slot, duplicate workload, **active-slot deletion refusal**, unapproved cleanup and cleanup rerun |

**Each refusal must exit nonzero; syntax errors must not masquerade as a legitimate guard refusal.** All successful operations are checked against actual PostgreSQL object/row or slot state. The harness fails if a refusal succeeds or if an object invariant does not match. One-time setup uses identity-bound `psql` variables and PostgreSQL `RAISE EXCEPTION` with `ON_ERROR_STOP=1`, not a normal `psql` quit code.

### Acceptance evidence

- Earlier [guard workflow #41302526224](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41302526224): 51/51 PASS (later corrected SQL/refusal syntax). **Expanded active-consumer [workflow #41312831290](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312831290): 55/55 PASS**, including active physical slot refusal, intact-slot check, receiver shutdown and inactive-slot cleanup.
- On the **corrected head**, the V03 and V02 parser workflows must both pass. Evidence is retained as the synthetic-only `postgresql-v03-ch061070-fixture-guard-runtime` GitHub Actions artifact; no private source logs are uploaded.
- This test is safe to run only in the CI-disposable environment. It cannot be used to authorize a shared-cluster or production physical slot. An operator must not copy its hardcoded test credentials, defaults or slot name into a real environment.

## Limitations and next acceptance

1. The tested SQL guard rejects known bad metadata in an isolated container; self-declared cluster identity is **not** a cryptographic proof that a system is non-production.
2. An **active `pg_receivewal` consumer** was run in the disposable isolated container. The guarded cleanup **refused deletion while the slot was active**, preserved the slot, then allowed cleanup only after the known test consumer released it. This does **not** establish real CDC ownership, production capacity, client-side credential rotation, or safety of deletion on any shared cluster.
3. Chapters 061–063 and 065 still require actual dump/restore/backup verification and exit-code evidence.
4. Chapters 064 and 066 still require real base backup, archive continuity, isolated target-time PITR, and actual RPO/RTO. Chapters 067, 069 and 070 require multi-node replication, bounded synchronous commit behavior, independent fencing and HA-manager acceptance.
5. No staging signoff was performed. Chapter 050 V04-G remains blocked under [issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45), separate from draft PR #46.

**Decision:** Guarded disposable SQL lab **runtime verified** for this narrow scope only; overall Chapters 061–070 and enterprise HA/DR certification remain **PENDING / NOT_CERTIFIED**.
