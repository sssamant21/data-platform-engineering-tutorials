# Chapter 032 — Hands-on DBRE/SRE Index Design Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `032-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**Baseline:** PostgreSQL 18. **Isolation:** dedicated schema, disposable database recommended. **Do not run against production.**

## Prerequisites

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/032-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/032-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=032-DROP -f postgresql/labs/sql/032-cleanup.sql
```

Run from repository root, against a disposable local PostgreSQL instance. Scripts intentionally use ordinary CREATE INDEX and run outside application traffic. Save plan outputs separately if evidence is required.

## Six investigations

1. **Baseline:** collect row counts, plans, buffer reads and baseline table size.
2. **Composite:** compare tenant/time ordering with and without the index; inspect leftmost and range predicates.
3. **Partial:** compare the literal `status = 'open'` with other statuses; observe generic prepared-plan limitations.
4. **Expression:** compare `lower(email)` with raw equality and verify semantic differences.
5. **Covering:** compare INCLUDE payload with the same filter; check `Heap Fetches` before and after a lab-only VACUUM.
6. **Lifecycle:** capture size and catalog definitions, discuss write amplification, deployment locks and cleanup.

For repeatable timing, collect several default-planner measurements after warm-up. Do not turn `enable_seqscan=off` into an acceptance configuration. The planner may choose sequential scans when the fixture is small.

## Evidence table

| Test | Query/predicate | Plan node | Actual rows | Buffers | Heap Fetches | Index bytes | Decision |
|---|---|---|---|---|---|---|---|
| Baseline | | | | | | | |
| Composite | | | | | | | |
| Partial | | | | | | | |
| Expression | | | | | | | |
| Covering | | | | | | | |

## Acceptance and safety

Check result correctness, inspect unexpected seq scans, compare storage, identify write-path impact and confirm the cleanup schema is removed. The lab does not establish production latency, WAL volume or concurrency behavior.

**Status:** Scripts authored; PostgreSQL 18 runtime execution pending.
