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

**Next unreviewed milestone:** Chapter 04 semantic SQL/shell review, followed by remaining chapters and external-link checks. No independent sign-off or production certification is implied.
