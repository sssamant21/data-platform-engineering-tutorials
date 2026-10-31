# Snowflake Learning Path — DBRE / SRE / Beginners

**Eight complete chapters | 60 minutes each | 480 minutes total**

A straightforward chapter-by-chapter introduction to Snowflake for DBRE/SRE engineers, administrators, developers, analysts, data engineers and other stakeholders. Start with fundamentals and progress through daily operations, performance, cost, access control, recovery and incident response.

**Mode:** The chapters support **offline reading, paper exercises and instructor-led discussion without Snowflake access**. SQL examples are written teaching material and have **NOT** been executed against Snowflake as part of this track.

## Start learning — Chapters 01–08

| Chapter | Read the tutorial | Duration | What you learn |
|---|---|---:|---|
| 01 | [Snowflake Fundamentals](chapters/chapter-01-snowflake-fundamentals.md) | 60 min | Storage, compute, cloud services, accounts, databases, schemas, rows, columns, SQL |
| 02 | [Snowflake Administration](chapters/chapter-02-snowflake-administration.md) | 60 min | Warehouse administration, users, roles, permissions and query history |
| 03 | [Performance and Query Optimization](chapters/chapter-03-performance-query-optimization.md) | 60 min | Query Profile, pruning, execution time, queueing and safe tuning |
| 04 | [Monitoring, Observability and Cost](chapters/chapter-04-monitoring-observability-cost.md) | 60 min | Usage history, dashboards, credits, SLOs and cost interpretation |
| 05 | [Security, RBAC and Governance](chapters/chapter-05-security-rbac-governance.md) | 60 min | Least privilege, auditing, masking and access troubleshooting |
| 06 | [Data Recovery and Disaster Recovery](chapters/chapter-06-data-recovery-disaster-recovery.md) | 60 min | Time Travel, UNDROP, clones, Fail-safe, RPO and RTO |
| 07 | [Troubleshooting and Incident Response](chapters/chapter-07-troubleshooting-incident-response.md) | 60 min | Incident triage, query evidence, rollback planning and blameless RCA |
| 08 | [Data Loading and Ingestion](chapters/chapter-08-data-loading-and-ingestion.md) | 60 min | Stages, CSV formats, COPY INTO validation, Snowpipe, file-level load history and safe replays |

**Suggested learning sequence:** Finish Chapters 01–02 first, then follow 03–08. Every chapter has a timed agenda, core concepts, examples for offline study, expected results, a troubleshooting quick reference, knowledge questions and source documentation.

## Learner and instructor materials

| Material | Purpose |
|---|---|
| [Beginner glossary](../accelerated-dbre-sre/validation/BEGINNER-SNOWFLAKE-GLOSSARY.md) | 70 key terms explained in plain language |
| [Learner workbook](../accelerated-dbre-sre/validation/LEARNER-OFFLINE-WORKBOOK.md) | 35 answer-free questions, seven exercises and a final tabletop |
| [Course delivery checklist](../accelerated-dbre-sre/validation/COURSE-DELIVERY-CHECKLIST.md) | Teach all seven sessions, with each five-part 60-minute agenda |
| [Instructor guide](../accelerated-dbre-sre/validation/INSTRUCTOR-OFFLINE-ACCEPTANCE.md) | Teaching guidance and expected reasoning |
| [Instructor answer keys](../accelerated-dbre-sre/validation/INSTRUCTOR-ANSWER-KEY-RUBRICS.md) | Keep separate until learner assessment is complete |
| [Chapter 08 ingestion worksheet](exercises/chapter-08-ingestion-tabletop.md) | Answer-free fictional CSV and ingestion troubleshooting exercise |
| [Learning-path status](STATUS.md) | Chapter readiness and deferred validation boundaries |

For an independent knowledge assessment, distribute the learner workbook first. The full chapter files include knowledge-check answers, so they are best used as study materials rather than closed-book test sheets.

## How to study without an account

1. Open a chapter and review the basic terms and architecture/operational concepts.
2. Read its SQL examples, **but do not execute them**. Identify required roles, permissions, cost considerations and expected behavior.
3. Complete the matching workbook activity using the fictional/synthetic data.
4. Explain how you would troubleshoot an error without elevated privileges or production changes.
5. Use the chapter quiz for reinforcement and keep any filled-in learner notes in a private approved location.

## Relationship to the other Snowflake tutorials

Chapters **01–07** are a **learning-path presentation of the original seven accelerated tutorials**. Their teaching content is copied into the `chapters/` folder so learners can read and navigate it directly. **Chapter 08 is new, independently authored introductory content** on data loading and ingestion, linked to canonical Snowflake chapters 11–17 and 78. The original [seven-course accelerated DBRE/SRE track](../accelerated-dbre-sre/README.md) and its supporting materials remain intact. If the original seven lessons are revised, synchronize their chapter copies to prevent drift. The accelerated course and its separate seven-lesson tests remain unchanged.

The larger, more advanced **90-chapter Snowflake curriculum** remains separate in [Snowflake's master curriculum](../MASTER-LAYOUT.md). None of its existing chapter numbers or completion claims are changed by this learning path.

## Current release and validation boundaries

- **Chapter authoring:** 8/8 chapters published to the feature branch and prepared for offline teaching.
- **Offline static checks:** The [learning-path validator](validation/test_learning_path.py) checks the eight chapter files, relative links, 60-minute agendas and source parity of the original seven, and [Chapter 08 regression tests](validation/test_chapter_08_ingestion.py) cover the ingestion exercise and evidence/safety boundaries. Final GitHub Actions outcome is recorded in [STATUS.md](STATUS.md). No Snowflake access or SQL execution is claimed.
- **V03 real Snowflake SQL execution:** **USER-DEFERRED / NOT RUN (0/7 original accelerated labs; Chapter 08 also NOT RUN)**. No actual query IDs, costs or restore evidence.
- **V04 independent reviewer assignment:** **SKIPPED BY OWNER / NOT APPROVED**. Not a successful review.
- **V05 production certification:** **NOT CERTIFIED**.
- **Publication:** [draft PR #43](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/43), **not yet merged into main**.

No Snowflake access or passwords are needed for this offline learning path.
