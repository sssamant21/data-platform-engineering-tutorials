# PostgreSQL V08-B — Offline Guardrail Regression and Staging Readiness

**Execution date:** 2026-11-02 UTC  
**Status:** OFFLINE MOCKED TESTS PASSED; REAL STAGING NOT RUN  
**Files under test:** [V08-safe-preflight.py](V08-safe-preflight.py) and [V08-test-safe-preflight.py](V08-test-safe-preflight.py).

## Executed test evidence

- Locally reconstructed the original V08 launcher from the published GitHub file and verified its Git blob SHA, **be30f9bc99e8ba1d7072c9faa4d82b68f4171b8e**.
- Applied source-level security fixes, compiled the resulting Python source and verified the updated Git blob SHA, **ba43331de8582023e6c6744bf10f05fb843de822**.
- Executed **22 local unittest cases on Python 3.13.5** with all database subprocess calls mocked. **22 passed; 0 failures, 0 errors.**
- Verified the published test suite's Git blob matches the executed local suite, **c2fcdec0502bd76f29993f4c8038d3824de9f95b**.
- No real PostgreSQL or external network connection, production credentials, PITR or HA activity occurred.

### Confirmed safe behaviors

| ID | Offline test | Result |
|---|---|---|
| 01 | Missing execution approval | PASS: blocked |
| 02 | Target not in allowlist | PASS: blocked |
| 03 | Multiple-host host setting | PASS: blocked |
| 04 | Unix-socket host path | PASS: blocked |
| 05 | libpq conninfo string in database setting | PASS: blocked |
| 06 | TLS weaker than verify-full in remote staging | PASS: blocked |
| 07 | Password supplied in environment | PASS: blocked |
| 08 | PGSERVICE alternate connection | PASS: blocked |
| 09 | PGHOSTADDR alternate destination | PASS: blocked |
| 10 | Requested role mismatch | PASS: blocked |
| 11 | No independently reviewed SQL hash | PASS: blocked |
| 12 | Wrong SQL SHA-256 | PASS: blocked |
| 13 | SQL changed after approved hash | PASS: blocked |
| 14 | Allowlist world/group readable | PASS: blocked |
| 15 | Password file world/group readable | PASS: blocked |
| 16 | Evidence directory world/group accessible | PASS: blocked |
| 17 | psql unavailable | PASS: blocked |
| 18 | Actual database/role/version/standby identity mismatch | PASS: diagnostic SQL blocked |
| 19 | Identity query error | PASS: stopped |
| 20 | Read-only SQL subprocess error | PASS: no evidence marked as success |
| 21 | Simulated approved connection and two mocked queries | PASS: explicit endpoint arguments, bounded read-only options, verified SQL via stdin and private mode-0600 output |
| 22 | Only the Chapter 004 loopback lab may disable TLS | PASS: approved local mock permitted; port outside lab blocked |

The simulated success case is **not** a database query, SLO, PITR or production certification.

## Implemented hardening

- Require V08_EXPECT_SQL_SHA256, supplied from a separately approved immutable SQL artifact.
- Reject local SQL tampering, a symlinked SQL file, libpq multi-host lists, Unix socket paths and database/user connection strings.
- Bind psql to explicit -h/-p/-d/-U values, never relying on implicit libpq fallback, and set -w to disallow interactive password prompts.
- Pass the **same hash-verified SQL bytes** directly to psql stdin, eliminating a later re-open of the potentially changed local SQL file.
- Retain verified TLS, restrictive allowlist and password file permissions, no secrets in logs, bounded timeouts and private evidence output.
- Scope support to POSIX Linux/WSL, TCP hostname/IPv4, and simple PostgreSQL database/role identifiers. Excluded cases require separate adapter review.

## Run locally (offline only)

In Linux/WSL with Python 3.10+:

~~~~bash
python3 postgresql/dbre-responsibility-for-postgresql/qa/V08-test-safe-preflight.py
~~~~

The unit tests create synthetic temporary files, monkeypatch subprocess calls and write only **mocked** result files. They **do not** connect to real PostgreSQL.

**Important implementation concern:** The test harness writes a temporary synthetic SQL text to the adjacent V08-readonly-staging-preflight.sql file during each test. **Do not execute the suite directly inside a working repository without preserving/restoring that file**. For automation, the tests should first be isolated to a throwaway copy of the runner + SQL; until that isolation is implemented, run the tests only in a disposable directory.

## Remaining required real tests

- [ ] Approved staging target, change ticket and independent operator designated.
- [ ] Full preflight SQL run with actual restricted role/version and real output.
- [ ] Provider-specific TLS/IAM and exact network identity tested.
- [ ] Prometheus/Grafana alert routing and APP SLO tested.
- [ ] Isolated PITR restored with WAL and committed business watermark.
- [ ] HA independent old-primary fencing/single writer where relevant.
- [ ] Measured APP/DATA RPO/RTO, CDC/replica and restoration correctness.
- [ ] SEC/PLT/DBRE/APP/DATA/FIN/SM approval authenticated by a reviewer.
- [ ] Workload, connection and timeouts measured and supported in staging.

**Decision: OFFLINE_GUARDS_PASS / STAGING_NOT_RUN / NOT_CERTIFIED_FOR_PRODUCTION.**
