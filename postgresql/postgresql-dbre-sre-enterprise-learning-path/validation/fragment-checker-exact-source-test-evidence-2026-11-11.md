# Exact-source PostgreSQL 18 fragment-checker regression evidence — 2026-11-11

**Scope:** Independent 20-chapter enterprise learning path only. **Documentation baseline:** PostgreSQL 18. **Test category:** offline unit regression; **not** a live HTML-fragment or PostgreSQL database validation.

## Source provenance

Retrieved both files from GitHub `main` using the GitHub connector, transferred their complete text into a temporary isolated execution directory, and checked Git blob hashes using `git hash-object`. The hashes match the blobs returned by GitHub:

| File | Git blob SHA (GitHub and executed copy) |
| --- | --- |
| `validation/check_pg18_fragments.py` | `59d5627c68c76edc52c3b3e880b379e989be7437` |
| `validation/test_check_pg18_fragments.py` | `3c877c065db486ed96a23a3bb49effa001570662` |

This establishes **exact-source** provenance of the two tested Python files despite the lack of a full Git checkout. It does not establish a full repository-wide checkout or audit.

## Execution

- Runtime: Python 3.13.5, isolated local temporary directory; no Docker, PostgreSQL server, or psql used.
- Command: `cd /tmp/pg18-validation && python -m unittest discover -s . -p 'test_check_pg18_fragments.py' -v`
- Result: **10 tests run, 10 passed, 0 failures, 0 errors**, in 0.009 seconds.
- Covered: exact HTML id, legacy named anchor, text-only false positive, wrong-version redirect, same-version different-page redirect, unexpected-host redirect, non-HTML response, oversize response, HTTP 404, DNS failure.
- All tests use mocks; passing them does **not** establish that the three remote PostgreSQL 18 fragments exist.

## Live fragment attempt and blocker

Ran `python /tmp/pg18-validation/check_pg18_fragments.py` on 2026-11-11 at approximately 11:57 UTC. All three targets returned `status=unverified` with `URLError: [Errno -3] Temporary failure in name resolution`:

1. `runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET`
2. `sql-createtable.html#SQL-CREATETABLE-STORAGE-PARAMETERS`
3. `functions-admin.html#FUNCTIONS-ADMIN-DBSIZE`

No remote fragment is marked present or missing. Local `git ls-remote` also failed to resolve `github.com`. Docker and psql were unavailable. No database lab was executed, no production or cloud services accessed, and no destructive action performed.

## Remaining gates

1. From a network-enabled environment, execute `python validation/check_pg18_fragments.py --output validation/pg18-fragment-results.json`; review actual HTTP status, redirect and HTML id/name evidence before recording anchor outcomes.
2. Complete outstanding external URL and relative/fragment resolution in `validation/reference-resolution-audit.md` without repeating the completed link inventories.
3. Migrate labs to PostgreSQL 18 individually using fresh isolated volumes mounted at `/var/lib/postgresql`, verify server identity, capture real command/output and cleanup evidence, and advance per-lab status only after actual execution.
4. Keep historical PostgreSQL 17 evidence, independent technical review and production certification as separate gates.

**Status change:** exact-source offline fragment-checker regression suite **passed**; live reference resolution and PostgreSQL 17/18 lab runtime validation **remain pending**.
