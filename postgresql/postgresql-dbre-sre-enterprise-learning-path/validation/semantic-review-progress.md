# Semantic validation progress — independent PostgreSQL enterprise track

**Review date:** 2026-11-04  
**Branch reviewed:** `main`  
**Scope:** `postgresql/postgresql-dbre-sre-enterprise-learning-path/`

## Validation boundaries

This is a source-level technical review, **not** executed lab evidence, independent sign-off, or production certification. All 20 chapters and 20 lab READMEs are authored according to the track's README, master TOC and status tracker. Runtime validation remains **0/20**. No commands were run against a PostgreSQL server.

## Chapter 02 — relational design and constraints

**Files reviewed:**
- [Chapter 02 lesson](../chapters/02-databases-schemas-tables-and-relationships.md)
- [Chapter 02 lab](../labs/chapter-02/README.md)

**Static semantic checks:**
- PostgreSQL 17-compatible constructs: identity columns, `NUMERIC(12,2)`, `TIMESTAMPTZ`, PK/UNIQUE/FK/CHECK constraints, `CREATE SCHEMA`, `CREATE INDEX`, catalog queries, `SAVEPOINT`, and `ROLLBACK TO SAVEPOINT`.
- PowerShell Docker invocations target the named `pg-fleet-lab` container; SQL and `psql` meta-commands are distinguished.
- Inserts create two customers, two products, one order and one order item when the database starts empty. The notebook order total is `2 * 9.50 = 19.00`; generated IDs are not assumed fixed.
- Two deliberate constraint violations occur inside separate transactions with savepoint recovery. These errors are expected and must not be treated as successful all-green SQL script execution.
- The chapter explicitly warns about repeated execution, production DDL, and foreign-key index assumptions.
- Chapter-to-lab and lab-to-chapter relative paths are consistent by inspection; official reference URLs are present but have **not yet been HTTP-checked**.

**Review result:** No confirmed source-level SQL/PowerShell defect in the reviewed Chapter 02 examples. This does not prove runtime correctness.

**Operational caution:** The lab requires a disposable PostgreSQL 17 Docker instance prepared in Chapter 01. Its `CREATE SCHEMA` and seed inserts are not idempotent; the lab explicitly says to run once in a clean database and inspect existing objects before rerunning. Do not automate a reset/drop.

## Execution availability and evidence requirements

The current validation environment has no `docker`, `psql`, or `shellcheck` executable on PATH. Therefore Chapter 02 remains **not executed**. No synthetic terminal output is recorded as test evidence.

When an isolated PostgreSQL 17 runtime is available, record:
1. Image digest and `SELECT version()`; container/database identity and disposable-environment confirmation.
2. Each executed SQL/PowerShell command and sanitized stdout/stderr with timestamps.
3. Table row counts `2/2/1/1`, order total `19.00`, both intentional constraint errors and successful savepoint recovery.
4. Index inventory, database/schema identity, cleanup or retained-disposable-instance decision.
5. Test reviewer, actual pass/fail result, and evidence artifact location.

Do not change the track's runtime-validation status until this evidence exists.

## Remaining work

- Semantic review Chapters 03–20 (and re-check any prior work only if the evidence is missing); SQL, shell, PowerShell, and provider-specific command safety.
- Resolve all internal relative links and verify external official documentation URLs.
- Execute labs only in explicitly disposable PostgreSQL 17 environments; AWS and Kubernetes provider exercises remain optional and must not create costs or affect live infrastructure.
- Obtain independent technical review separately from source-level checks and runtime execution.

## Official PostgreSQL 17 references

- [Data definition](https://www.postgresql.org/docs/17/ddl.html)
- [Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)
- [psql](https://www.postgresql.org/docs/17/app-psql.html)
- [Transactions](https://www.postgresql.org/docs/17/tutorial-transactions.html)

## Chapter 03 — transactions, ACID and two-session MVCC

**Files reviewed:** [lesson](../chapters/03-sql-transactions-acid-and-mvcc.md) and [lab](../labs/chapter-03/README.md). **Review type:** source-level semantic inspection only; no PostgreSQL runtime execution.

- The lab explicitly separates PowerShell Docker commands from SQL in interactive `psql` and requires distinct backend PIDs for Sessions A and B. `BEGIN ISOLATION LEVEL READ COMMITTED` and `BEGIN ISOLATION LEVEL REPEATABLE READ` are PostgreSQL 17-compatible transaction forms.
- Seed balances are 100.00/100.00. The atomic transfer of 25 yields 75.00/125.00 (sum 200.00). The explicit rollback temporarily shows 65.00 and restores 75.00; savepoint rollback temporarily shows 70.00 and restores 75.00. The intentional `CHECK (balance >= 0)` error is followed by `ROLLBACK TO SAVEPOINT`, allowing `COMMIT`.
- Under READ COMMITTED, A reads 75.00, B commits a subtraction of 5, then A reads 70.00. Under REPEATABLE READ, A first reads 70.00 and establishes its snapshot, B commits an addition of 3, A continues to read 70.00 until COMMIT and reads 73.00 afterward. Final balances 73.00/125.00 (sum 198.00) are arithmetically consistent and the deliberate non-conservation is disclosed.
- `pg_stat_activity` is read-only. The lab calls for promptly committing A's short diagnostic transaction and disconnecting both sessions. It does not prescribe backend termination or destructive database cleanup. Existing database/table collisions are flagged for manual inspection, not automatic dropping.
- Relative chapter/lab links are consistent by inspection. PostgreSQL 17 official documentation URLs are listed; HTTP reachability has not yet been verified. No confirmed semantic defect was identified in this pass.

**Runtime evidence required:** capture disposable container identity/image digest, PostgreSQL version, two distinct backend PIDs, the ordered interleaved A/B transcript, intended constraint error and recovery, transaction isolation settings, final balances, session disconnect/cleanup confirmation and sanitized timestamps. Until actual execution, Chapter 03 remains **not runtime verified**.

**Chapter 04 review is recorded below.** No independent sign-off or production certification is implied.

## Chapter 04 — WAL, shared buffers and checkpoints

**Files reviewed:** [lesson](../chapters/04-postgresql-internals-wal-buffers-and-checkpoints.md) and [lab](../labs/chapter-04/README.md). **Review type:** source-level semantic inspection only; not a PostgreSQL execution result.

- The preflight checks Docker Linux mode, the named disposable `pg-fleet-lab` container, PostgreSQL 17 and `pg_is_in_recovery() = false` before database creation. The lab checks for a pre-existing `training_ch04` database and stops rather than dropping it.
- The SQL creates a synthetic table with a PostgreSQL 17 identity column, captures `pg_current_wal_lsn()` using interactive `psql` `\\gset`, inserts 2,000 generated rows in one transaction, then computes a WAL byte-distance with `pg_wal_lsn_diff()`. The quoted `:'start_lsn'::pg_lsn` and `:'end_lsn'::pg_lsn` substitutions require the same interactive `psql` session; the instructions state this.
- `pg_stat_wal`, `pg_stat_checkpointer`, `pg_stat_bgwriter`, `pg_stat_io`, `pg_stat_database` and `pg_replication_slots` are used read-only. The lesson correctly distinguishes PostgreSQL 17 checkpointer statistics from older `pg_stat_bgwriter` checkpoint columns. The ratio query protects against division by zero via `NULLIF`.
- The lab does not force `CHECKPOINT`, reset statistics, change durability settings, manipulate replication slots, or delete WAL. It correctly warns that LSN differences and cumulative WAL counters need not match and that an unchanged checkpoint counter is acceptable.
- **Operational limitation:** the exercise uses a superuser inside a disposable local container. This is not a least-privilege monitoring-role template for production. The lab intentionally retains the separate database; eventual cleanup requires an independently confirmed disposable environment.
- Chapter/lab relative navigation links are consistent by inspection. Official PostgreSQL 17 URLs are present but **HTTP reachability and complete external-reference validation are pending**.

**Review result:** No confirmed source-level defect in Chapter 04. **Runtime status: not executed.** Required evidence: PostgreSQL image digest, version and identity, preflight outputs, initial database-existence check, sanitized interactive `psql` transcript, 2,000-row count, both LSNs and positive byte-distance, WAL/checkpointer/bgwriter/I/O observations, configuration and slot inventory, and explicit cleanup/retention decision. No reviewer approval or production certification is inferred.

**Next unreviewed milestone:** Chapter 05 — index and query-plan SQL/shell semantics; continue external-reference checks and isolated runtime preparation.

## Chapter 05 — indexes, query plans and performance

**Files reviewed:** [lesson](../chapters/05-indexes-query-plans-and-performance.md) and [lab](../labs/chapter-05/README.md). **Scope:** static semantic review of PostgreSQL 17 SQL, PowerShell/Docker preflight, sample arithmetic, index and EXPLAIN safety. **Not executed.**

- The preflight checks Linux Docker, named container, PostgreSQL version and database absence before creating `training_ch05`; the lab does not overwrite an existing database. Interactive `psql` SQL is separated from PowerShell commands.
- The 200,000-row `generate_series` workload produces exactly 2,000 distinct customers with 100 events each. Every tenth row is pending, yielding 20,000 pending rows. `GENERATED ALWAYS AS IDENTITY`, `TIMESTAMPTZ` arithmetic, `FILTER`, `ANALYZE`, and `EXPLAIN (ANALYZE, BUFFERS)` are PostgreSQL 17-compatible constructs.
- The composite B-tree index on `(customer_id, created_at DESC)` can support equality-filtered ordered top-20 retrieval; it does not guarantee a specific plan or latency. The optional `WHERE status = 'pending'` partial index matches the literal query predicate. The lesson appropriately notes that `INCLUDE (amount)` does not cover `event_id` and cannot by itself guarantee an index-only scan.
- `pg_indexes`, `pg_class`, `pg_namespace`, `pg_stat_user_indexes`, `pg_relation_size`, `pg_indexes_size` and `pg_total_relation_size` are appropriate for the stated read-only inventory. The broad predicate `customer_id BETWEEN 1 AND 2000` matches all synthetic rows, making a sequential scan plausible, not mandatory.
- The lab correctly warns that EXPLAIN ANALYZE executes statements, limits measured statements to read-only SELECT, and avoids forcing planner settings, destructive drops, production DDL or arbitrary index removal. Repeated execution is intentionally non-idempotent and requires inspection first.
- Relative lesson/lab navigation paths are consistent by source inspection. PostgreSQL 17 official documentation URLs are listed; external HTTP reachability is **not verified** in this review.

**Result:** No confirmed source-level semantic defect in Chapter 05. **Runtime remains not executed**; independent review and certification remain pending.

**Evidence needed:** disposable container identity and image digest, `SELECT version()`, database absence preflight, insert result and counts (200000/20000/2000), before/after actual EXPLAIN plans and buffer/timing measurements, index inventory and sizes, optional partial-index status, final database identity and retention/cleanup decision. Capture sanitized transcripts and timestamps; never substitute example plans for observed output.

**Next unreviewed milestone:** Chapter 06 — bare-metal PostgreSQL operational semantics and safe local exercises; then continue Chapters 07–20 and external URL verification.
