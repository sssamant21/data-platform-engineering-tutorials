# Snowflake Learning Path — Chapter Progress

**Scope:** `snowflake/learning-path/` (eight offline DBRE/SRE chapters).  
**Last updated:** 2026-10-31  
**Source:** [Snowflake Learning Path](README.md) adapted from the [accelerated course track](../accelerated-dbre-sre/README.md).  
**Delivery state:** CHAPTERS AUTHORED ON FEATURE BRANCH. The 90-chapter canonical Snowflake curriculum remains unchanged.

| Chapter | Topic | Markdown published | Offline automated QA | Actual Snowflake execution | Independent review |
|---|---|---|---|---|---|
| [01](chapters/chapter-01-snowflake-fundamentals.md) | Fundamentals | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [02](chapters/chapter-02-snowflake-administration.md) | Administration | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [03](chapters/chapter-03-performance-query-optimization.md) | Performance and Query Optimization | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [04](chapters/chapter-04-monitoring-observability-cost.md) | Monitoring and Cost | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [05](chapters/chapter-05-security-rbac-governance.md) | Security and Governance | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [06](chapters/chapter-06-data-recovery-disaster-recovery.md) | Data Recovery and DR | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [07](chapters/chapter-07-troubleshooting-incident-response.md) | Incident Response | Yes | [PASS — GitHub Actions #360](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41214151309) | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |
| [08](chapters/chapter-08-data-loading-and-ingestion.md) | Data Loading and Ingestion | Yes | Pending CI | NOT RUN | SKIPPED BY OWNER / NOT APPROVED |

**Progress:** **8/8 chapters authored**, each 60 minutes, **480 minutes total**. Original Chapters 01–07 passed prior offline CI; Chapter 08 and updated full-path tests require CI confirmation. The separate original seven-course accelerated track remains **7/7 / 420 minutes**.

## Acceptance boundaries

- A Markdown static check validates chapter structure, local references and selected offline safety language. It does not parse or execute the SQL examples.
- Chapters **01–07** were mirrored from the [accelerated source](../accelerated-dbre-sre/README.md); **Chapter 08** is a new ingestion lesson. Keep original-seven copies synchronized with their source; shared instructor materials remain in the accelerated track. [Chapter 08 learner exercise](exercises/chapter-08-ingestion-tabletop.md) is answer-free and offline.
- The repository has **not** run these Snowflake examples against a training account: **V03 USER-DEFERRED / NOT RUN (0/7 original accelerated labs; Chapter 08 also NOT RUN)**.
- Independent review assignment was **skipped by owner**: **V04 NOT PERFORMED / NOT APPROVED**.
- **V05 NOT CERTIFIED**. Neither offline course completion nor source QA supports production operational acceptance.
- [PR #43](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/43) remains draft and unmerged until explicitly authorized.

## Next teaching work

Use the [glossary](../accelerated-dbre-sre/validation/BEGINNER-SNOWFLAKE-GLOSSARY.md), [workbook](../accelerated-dbre-sre/validation/LEARNER-OFFLINE-WORKBOOK.md) and [session delivery plan](../accelerated-dbre-sre/validation/COURSE-DELIVERY-CHECKLIST.md) for offline onboarding. Learner assessments have not yet occurred.
