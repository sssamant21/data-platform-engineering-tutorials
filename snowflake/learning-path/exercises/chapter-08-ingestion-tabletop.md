# Chapter 08 — Offline Learner Exercise: Snowflake Ingestion

**Learning mode:** Paper/tabletop only. No account, warehouse, storage integration, Snowpipe setup or Snowflake SQL execution.  
**Related chapter:** [08 — Data Loading and Ingestion](../chapters/chapter-08-data-loading-and-ingestion.md).  
**Answer policy:** Learner worksheet **without model answers**; instructors may use the knowledge-check explanations in the chapter after collecting responses. Do not publish real user information or credentials.

## Scenario — a file reached storage, but the report is stale

An upstream system reports that `orders_2026_10_31.csv` was uploaded to a **fictional** cloud path at 10:00 UTC. The downstream report did not receive its latest update. You have no Snowflake account access for this lesson.

~~~text
order_id,region,amount
101,EAST,120
102,WEST,80
103,EAST,50
104,WEST,not_a_number
~~~

### Part A — Architecture (5 minutes)

Draw a diagram showing: source producer, cloud storage, internal or external stage, a batch `COPY INTO` or Snowpipe loader, target table, transformation pipeline and report. Label **who owns each handoff**.

**Diagram/owner notes:** `[answer in approved private workspace]`

### Part B — File validation (5 minutes)

Identify the header, the numeric conversion issue and the different meanings of **file arrived**, **parsed successfully**, and **loaded into target**. Explain how a CSV format's delimiter/header options affect results.

**Suspect row and impact:** `[answer privately]`

### Part C — Safe ingestion triage (5 minutes)

Without running commands, explain which evidence you would request from the storage owner, the Snowflake DBRE and the data engineering team. What are the limits of the 14-day Information Schema `COPY_HISTORY` view, and what changes when using a historical Account Usage view?

**Requested evidence and why:** `[answer privately]`

### Part D — Retry and data-quality decision (5 minutes)

Your team proposes reloading all files using `FORCE = TRUE`. Explain why this can be risky and identify the **minimum approvals, replay scope, deduplication checks and rollback conditions** required first. Do not propose production writes.

**Safe decision and owners:** `[answer privately]`

## Five learner knowledge questions

1. What is a stage and how does it differ from a target table?
2. What does a CSV file-format definition control and what happens when the definition is wrong?
3. How does `VALIDATION_MODE = RETURN_ERRORS` differ from a mutating load?
4. Where would you look for recent file-level load history, and why might history have gaps?
5. What questions must be answered before rerunning a failed or skipped batch?

**My five answers:** `[record privately; do not commit]`

## Safety and final handoff

- [ ] All data was fictional; no real customer/patient record, cloud secret or identity was used.
- [ ] No SQL was run; no account, stage, pipe or target table was changed.
- [ ] No simulated output was described as a real `COPY_HISTORY` or `QUERY_ID` result.
- [ ] No blanket `ON_ERROR = CONTINUE` or `FORCE = TRUE` action was proposed without reconciliation and approval.
- [ ] Notes and any future assessment remain in an approved private learning location.

**Status:** `NOT ASSESSED`. V03 real Snowflake testing **USER-DEFERRED / NOT RUN**. V04 reviewer assignment **SKIPPED BY OWNER / NOT APPROVED**. V05 **NOT CERTIFIED**.

[Return to Chapter 08](../chapters/chapter-08-data-loading-and-ingestion.md) | [Learning Path](../README.md)
