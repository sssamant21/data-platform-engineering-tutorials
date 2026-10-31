# Snowflake DBRE/SRE Lab Runtime Evidence — Template

**Purpose:** Record evidence for one lesson and one approved training run. This blank document is NOT proof that testing occurred.

| Field | Value |
|---|---|
| Level / course | |
| Revision SHA | |
| UTC execution start / end | |
| Environment classification | Training / staging (never production without change approval) |
| Snowflake edition / region | |
| Approved user/role identifier (redacted) | |
| Training warehouse and size | |
| Scratch database and schema (non-sensitive alias) | |
| Test owner / independent reviewer | |
| Ticket / approval reference | |
| Approximate warehouse credits | |
| Result | PASS / FAIL / BLOCKED — not executed by default |

## Executed tests

| Test ID | Query ID (redact if needed) | Expected | Actual output summary | PASS / FAIL / BLOCKED | Evidence location |
|---|---|---|---|---|---|
| Lx-01 | | | | | |
| Lx-02 | | | | | |
| Lx-03 | | | | | |
| Lx-04 | | | | | |

## Negative cases and safety checks

| Control | Result | Notes |
|---|---|---|
| Least-privilege authorization succeeds as designed | | |
| Unauthorized action is denied without privilege escalation | | |
| No protected customer/PHI data used | | |
| No credentials, raw bind variables or sensitive query text retained | | |
| Cleanup completed or approved for later | | |
| Compute cost and duration recorded | | |
| Rollback plan documented for changes | | |

## Review / defects
- Open issues:
- Technical reviewer:
- Data/security owner:
- Approval or rejection decision:
- Revalidation date:

**Certification rule:** The "PASS" outcome for one lab does not certify a production environment. Separate security, resilience and owner acceptance is mandatory.
