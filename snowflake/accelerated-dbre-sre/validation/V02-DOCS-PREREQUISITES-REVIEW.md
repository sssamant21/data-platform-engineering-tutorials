# V02 — Documentation Links and Prerequisite Consistency Audit

**Review date:** 2026-10-31  
**Scope:** Seven Snowflake accelerated DBRE/SRE 60-minute lesson Markdown files and the offline instructor materials.  
**Method:** Source inspection, relative-link checks in static CI, official-doc URL spot checks in the Snowflake documentation, and a new offline regression suite. **No live Snowflake queries or account credentials were used.**

## Findings and corrections

| Finding | Severity | Issue | Correction |
|---|---|---|---|
| SF-036 | P2 | Every lesson said an authorized training account was a prerequisite, which unnecessarily blocks the **offline** 420-minute lecture/tabletop track | Split into **offline prerequisites (no account/CLI needed)** and **deferred V03 live-lab prerequisites** in all seven lessons |
| SF-037 | P2 | Live lab prerequisites lacked a clear level-specific role, namespace, visibility and approval summary | Documented scratch-schema/temporary-object isolation (L1/L3), selected database and query history (L2), monitoring grants (L4), security-audit approval (L5), separate writable recovery approval (L6), incident-history permissions (L7) |
| SF-038 | P2 | L3 and L7 used an old official Query Profile URL that redirected to the more general Query History/Query Profile page | Replaced with canonical [Snowsight Query History and Query Profile](https://docs.snowflake.com/en/user-guide/ui-snowsight-activity) documentation |
| SF-039 | P2 | README teaching flow assumed live execution while describing a completely offline course | Changed to **hypothetical results and tabletop evidence by default**; real outcomes only after authorized V03 resume |
| SF-040 | P2 | No dedicated automated guard against reintroducing required live Snowflake access for offline attendees | Created [offline prerequisite and documentation tests](test_docs_prerequisites.py) to check all seven course contracts, official reference format and internal navigation |
| SF-041 | P3 | The deliverables were spread across validation references without a single instructor handoff/index | Published the [final offline release-package inventory](OFFLINE-RELEASE-INVENTORY.md), including artifact map, owner roles, CI boundary and deferred gates |

## Current reference spot check (2026-10-31)

The following **specific documentation URLs were opened successfully** in Snowflake's current docs. This list documents the reviewed pages only; it is **not** a guarantee that every external URL stays live indefinitely.

| Level(s) | Verified official reference |
|---|---|
| 1 | [Snowflake architecture](https://docs.snowflake.com/en/user-guide/intro-key-concepts); [warehouses](https://docs.snowflake.com/en/user-guide/warehouses-overview) |
| 2, 3, 7 | [Query History table functions](https://docs.snowflake.com/en/sql-reference/functions/query_history); [Snowsight Query History/Profile](https://docs.snowflake.com/en/user-guide/ui-snowsight-activity) |
| 4 | [Warehouse Load History](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history); [Warehouse Metering History](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history); [Account Usage](https://docs.snowflake.com/en/sql-reference/account-usage) |
| 5 | [Access control](https://docs.snowflake.com/en/user-guide/security-access-control-overview); [SHOW GRANTS](https://docs.snowflake.com/en/sql-reference/sql/show-grants); [CURRENT_SECONDARY_ROLES](https://docs.snowflake.com/en/sql-reference/functions/current_secondary_roles); [Login History](https://docs.snowflake.com/en/sql-reference/account-usage/login_history) |
| 6 | [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel); [AT/BEFORE](https://docs.snowflake.com/en/sql-reference/constructs/at-before); [parameters](https://docs.snowflake.com/en/sql-reference/parameters); [Fail-safe](https://docs.snowflake.com/en/user-guide/data-failsafe); [replication/failover](https://docs.snowflake.com/en/user-guide/account-replication-intro) |

**Internal Markdown links:** The existing `validate_courses.py` ensures each relative link it encounters resolves to an actual local repository file. This is a check of paths, **not** a guarantee that the referenced article's content is semantically accurate.

## Level-specific offline vs live prerequisite matrix

| Level | Offline teaching prerequisites | Future live V03 prerequisites (NOT RUN) |
|---|---|---|
| L1 Fundamentals | Markdown guide, fictional orders, paper exercise | Owner-authorized account, small warehouse, instructor-controlled **empty** scratch schema and collision-free TEMP name |
| L2 Administration | Markdown, simulated role/warehouse history | Least-privilege role/warehouse, accessible selected database and visible `INFORMATION_SCHEMA` history |
| L3 Performance | Markdown, paper workload and simulated Query Profile | Small warehouse, scratch schema, isolated TEMP name and actual permitted query/profile visibility |
| L4 Observability/FinOps | Markdown, hypothetical historic usage metrics | Approved read-only monitoring grants for relevant `SNOWFLAKE.ACCOUNT_USAGE` views; expect data lag |
| L5 Security/Governance | Markdown, paper role/access review; synthetic-only data | Least-privilege role, separately authorized audit access when using `LOGIN_HISTORY` |
| L6 Recovery/DR | Markdown, hypothetical retention/incident timeline | Existing authorized scratch DB/table for read-only checks; **separate written approval** for optional permanent table/recovery changes |
| L7 Incident Response | Markdown, fictional incident and SLO cases | Nonproduction role plus current-session history; separate approval for account-wide monitoring, no cancellations |

## Decision and limitations

- **Documentation author review:** Corrected. The user can teach all seven lessons offline without creating a Snowflake account or running SQL.
- **Official URL verification:** The named Snowflake URLs were spot-checked as reachable on 2026-10-31; an instructor should recheck before reuse. Official documentation changes after this date may require re-review.
- **Offline QA CI:** To be recorded after GitHub Actions completes for the final branch.
- **V03 SQL runtime:** **USER-DEFERRED / NOT RUN 0/7**. No actual query outputs, credit charges, permissions or QUERY_ID evidence.
- **V04 independent human review:** **PENDING**. No external DBA/Security/Data Owner/instructor approval implied.
- **V05 production certification:** **NOT CERTIFIED**. PR #43 remains DRAFT; do not merge or certify based solely on documentation QA.

Next action only when requested: independent document/curriculum review or, later, manual controlled V03 with owner-approved Snowflake training access.
