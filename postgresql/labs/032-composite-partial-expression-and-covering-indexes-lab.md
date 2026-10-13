# Chapter 032 — Hands-on DBRE/SRE Index Design Lab

**Baseline:** PostgreSQL 18. **Isolation:** dedicated schema, disposable database recommended. **Do not run against production.**

## Prerequisites

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/032-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/032-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/032-cleanup.sql
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
