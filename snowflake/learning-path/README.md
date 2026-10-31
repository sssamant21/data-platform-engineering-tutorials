# Snowflake Learning Path — DBRE / SRE / Beginners

**Seven complete chapters | 60 minutes each | 420 minutes total**

A straightforward chapter-by-chapter introduction to Snowflake for DBRE/SRE engineers, administrators, developers, analysts, data engineers and other stakeholders. Start with fundamentals and progress through daily operations, performance, cost, access control, recovery and incident response.

**Mode:** The chapters support **offline reading, paper exercises and instructor-led discussion without Snowflake access**. SQL examples are written teaching material and have **NOT** been executed against Snowflake as part of this track.

## Start learning — Chapters 01–07

| Chapter | Read the tutorial | Duration | What you learn |
|---|---|---:|---|
| 01 | [Snowflake Fundamentals](chapters/chapter-01-snowflake-fundamentals.md) | 60 min | Storage, compute, cloud services, accounts, databases, schemas, rows, columns, SQL |
| 02 | [Snowflake Administration](chapters/chapter-02-snowflake-administration.md) | 60 min | Warehouse administration, users, roles, permissions and query history |
| 03 | [Performance and Query Optimization](chapters/chapter-03-performance-query-optimization.md) | 60 min | Query Profile, pruning, execution time, queueing and safe tuning |
| 04 | [Monitoring, Observability and Cost](chapters/chapter-04-monitoring-observability-cost.md) | 60 min | Usage history, dashboards, credits, SLOs and cost interpretation |
| 05 | [Security, RBAC and Governance](chapters/chapter-05-security-rbac-governance.md) | 60 min | Least privilege, auditing, masking and access troubleshooting |
| 06 | [Data Recovery and Disaster Recovery](chapters/chapter-06-data-recovery-disaster-recovery.md) | 60 min | Time Travel, UNDROP, clones, Fail-safe, RPO and RTO |
| 07 | [Troubleshooting and Incident Response](chapters/chapter-07-troubleshooting-incident-response.md) | 60 min | Incident triage, query evidence, rollback planning and blameless RCA |

**Suggested learning sequence:** Finish Chapters 01–02 first, then follow 03–07. Every chapter has a timed agenda, core concepts, examples for offline study, expected results, a troubleshooting quick reference, knowledge questions and source documentation.

## Learner and instructor materials

| Material | Purpose |
|---|---|
| [Beginner glossary](../accelerated-dbre-sre/validation/BEGINNER-SNOWFLAKE-GLOSSARY.md) | 70 key terms explained in plain language |
| [Learner workbook](../accelerated-dbre-sre/validation/LEARNER-OFFLINE-WORKBOOK.md) | 35 answer-free questions, seven exercises and a final tabletop |
| [Course delivery checklist](../accelerated-dbre-sre/validation/COURSE-DELIVERY-CHECKLIST.md) | Teach all seven sessions, with each five-part 60-minute agenda |
| [Instructor guide](../accelerated-dbre-sre/validation/INSTRUCTOR-OFFLINE-ACCEPTANCE.md) | Teaching guidance and expected reasoning |
| [Instructor answer keys](../accelerated-dbre-sre/validation/INSTRUCTOR-ANSWER-KEY-RUBRICS.md) | Keep separate until learner assessment is complete |
| [Learning-path status](STATUS.md) | Chapter readiness and deferred validation boundaries |

For an independent knowledge assessment, distribute the learner workbook first. The full chapter files include knowledge-check answers, so they are best used as study materials rather than closed-book test sheets.

## How to study without an account

1. Open a chapter and review the basic terms and architecture/operational concepts.
2. Read its SQL examples, **but do not execute them**. Identify required roles, permissions, cost considerations and expected behavior.
3. Complete the matching workbook activity using the fictional/synthetic data.
4. Explain how you would troubleshoot an error without elevated privileges or production changes.
5. Use the chapter quiz for reinforcement and keep any filled-in learner notes in a private approved location.

## Relationship to the other Snowflake tutorials

This is a **new learning-path presentation of the existing seven accelerated tutorials**. The actual chapter content is copied into the `chapters/` folder so that learners can open and navigate it directly. The original [accelerated DBRE/SRE course track](../accelerated-dbre-sre/README.md) and its supporting materials remain intact. If the lessons are revised, synchronize both chapter copies to prevent drift.

The larger, more advanced **90-chapter Snowflake curriculum** remains separate in [Snowflake's master curriculum](../MASTER-LAYOUT.md). None of its existing chapter numbers or completion claims are changed by this learning path.

## Current release and validation boundaries

- **Chapter authoring:** 7/7 chapters published to the feature branch and prepared for offline teaching.
- **Offline static checks:** run the [learning-path validator](validation/test_learning_path.py) alongside the accelerated curriculum static tests.
- **V03 real Snowflake SQL execution:** **USER-DEFERRED / NOT RUN (0/7)**. No actual query IDs, costs or restore evidence.
- **V04 independent reviewer assignment:** **SKIPPED BY OWNER / NOT APPROVED**. Not a successful review.
- **V05 production certification:** **NOT CERTIFIED**.
- **Publication:** [draft PR #43](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/43), **not yet merged into main**.

No Snowflake access or passwords are needed for this offline learning path.
