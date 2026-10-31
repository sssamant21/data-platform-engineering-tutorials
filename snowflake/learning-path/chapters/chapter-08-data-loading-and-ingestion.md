# Chapter 08 — Snowflake Data Loading and Ingestion

**Learning path navigation:** [Previous: Chapter 07](chapter-07-troubleshooting-incident-response.md) | [All chapters](../README.md) | [Offline learner worksheet](../exercises/chapter-08-ingestion-tabletop.md)  
**Track:** Snowflake Learning Path — DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — offline source review only; independent review SKIPPED BY OWNER / NOT APPROVED; Snowflake runtime validation NOT RUN (deferred).  
**Audience:** Beginner DBRE/SRE, data platform engineers, administrators, analysts and application/data owners.  
**Offline prerequisites:** [Chapter 01](chapter-01-snowflake-fundamentals.md), this document and the worksheet. **No Snowflake account, CLI, warehouse, credentials or live data access is required.**  
**Future live-lab prerequisites (not authorized here):** Owner-approved nonproduction account and small warehouse, least-privilege role with scoped stage/target access, a controlled synthetic CSV file in a known stage, authorized test table, cost guardrail and secure evidence location. **Do not execute any SQL in the offline lesson.**

## Learning objectives

After this chapter a beginner should be able to:

1. Draw the path from a source file through a Snowflake stage to a target table.
2. Distinguish an internal stage from an external stage and a batch `COPY INTO` operation from continuous Snowpipe ingestion.
3. Explain CSV file formats, headers, types, bad rows and how `VALIDATION_MODE` differs from an actual load.
4. Interpret load-history errors, row counts and reconciliation without pretending hypothetical outcomes are actual query results.
5. Describe safe retry/replay decisions, least-privilege requirements and escalation ownership.

## 60-minute lesson plan

| Topic | Time |
|---|---:|
| Ingestion components, ownership and data flow | 10 min |
| Stages, file formats and loading patterns | 15 min |
| COPY validation, load history and troubleshooting | 15 min |
| Offline synthetic CSV incident exercise | 15 min |
| Five-question knowledge check and recap | 5 min |
| **Total** | **60 min** |

## Core concepts

### 1. Understand the ingestion path

~~~text
External system / source
          |
          v
 CSV, JSON or Parquet file in storage
          |
          v
   Internal or external STAGE
          |
          +-- Batch: COPY INTO <table>  ---> RAW/target table
          |
          +-- Snowpipe: file-arrival/event workflow ---> RAW/target table
                                                 |
                                                 v
                                   Quality checks / transformations
                                                 |
                                                 v
                                        Reports / applications
~~~

A **stage** is a location Snowflake can use to read data files. A **file format** describes how to interpret delimiters, headers, quoting, nulls and compression. A **target table** defines the columns and types receiving the parsed data. The source owner, cloud-storage/IAM owner, Snowflake DBRE/SRE and downstream data/application owner have different responsibilities.

| Component | Simple meaning | Common operational problem |
|---|---|---|
| Internal stage | File storage managed within the Snowflake account | Missing stage permission, incorrect file path |
| External stage | Connection to business-owned S3, Azure Blob or Google Cloud Storage | Cloud IAM/integration problems, wrong storage path, cost/region considerations |
| File format | Instructions for reading a CSV/JSON/Parquet payload | Header treated as data, wrong delimiter, conversion error |
| `COPY INTO <table>` | Warehouse-backed bulk ingestion from a stage | Mis-scoped files, duplicate replay decisions, partial/failed loads |
| Snowpipe | Managed continuous **file** ingestion using a pipe definition and event/notification or API-based triggering | Events not arriving, pipe suspended, cloud integration or load failures |
| Snowpipe Streaming | A different ingestion method for streamed rows rather than staged files | Do not confuse it with file-oriented Snowpipe |
| Load reconciliation | Compare authorized source records with accepted/rejected target outcomes | Counts differ, bad data, duplicate or missing files |

**DBRE/SRE responsibility:** Define safe diagnostics, permissions, monitoring, data-quality checks and change controls. **Data owner responsibility:** Approve business correctness and any replay/backfill. A warehouse or pipeline restart alone does not prove that data has arrived correctly.

### 2. Stage and file-format choices

For a simple **synthetic** CSV, suppose the file contains:

~~~text
order_id,region,amount
101,EAST,120
102,WEST,80
103,EAST,50
104,WEST,not_a_number
~~~

The first line is a **header**, not an order. The fourth order contains a value that cannot be converted to a numeric amount in a typed `NUMBER` target column. The three other rows are well-formed; that does **not** mean Snowflake loaded three rows.

Questions to consider: Does the source file have a header? Are blank values legal? How are fields quoted? Should an invalid amount be quarantined or should the entire file be rejected? Who approves any correction or replay?

**Production caution:** Do not store actual patient/customer identifiers in an instructional CSV or a public query-history export. Avoid placing cloud access keys in SQL or Git; use approved storage integrations and role controls.

### 3. Batch `COPY INTO` versus Snowpipe

- **Batch `COPY INTO`:** A warehouse executes an owner-authorized load from the stage. The command can select files and file-format options. It is appropriate for planned batch loads and controlled reprocessing.
- **Snowpipe:** Designed for continuous **file-based** ingestion; the Snowpipe service manages compute, and a pipe definition identifies the load. Event notification setup or supported triggering is separate from uploading a file. The files still need correct permissions/format and monitoring.
- **Snowpipe Streaming:** Distinct from stage-based file ingestion; introduces different client and operational requirements and is **not exercised in this chapter**.

Avoid claims that every file is loaded instantly, that matching filenames guarantee no duplicates across all designs, or that a retry/replay with `FORCE = TRUE` is inherently safe. In a real pipeline, confirm file-level history and business keys and obtain the ingestion/data owner’s approval.

### 4. How to use validation before loading

The following SQL is **instructional only; do not execute it in this offline lesson**. It assumes an authorized test table `DBRE_SRE_L8_ORDERS` with `ORDER_ID NUMBER, REGION VARCHAR, AMOUNT NUMBER`, an existing controlled stage `DBRE_SRE_L8_STAGE` containing the fictional file, and appropriate access/warehouse. **Neither the stage nor the table is created by this document.**

~~~sql
-- Illustration ONLY: validates staged file parsing without loading rows.
-- All objects and permissions must exist in a separately approved lab.
COPY INTO DBRE_SRE_L8_ORDERS
FROM @DBRE_SRE_L8_STAGE/orders/
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1
               FIELD_OPTIONALLY_ENCLOSED_BY = '"')
VALIDATION_MODE = RETURN_ERRORS;
~~~

**Expected behavior (hypothetical, not observed):** In validation mode, the command reports supported parsing/conversion issues rather than loading records. With this sample, `not_a_number` cannot be converted to `NUMBER`; whether an error row is visible depends on file availability, target definition and permissions.

**Important constraints:** `VALIDATION_MODE` is not supported for every `COPY` form, including COPY statements that transform data. Do not silently change it to a mutating load. Always review the official limitations and `ON_ERROR` policy. The default error behavior generally favors safety over silently skipping errors; any later decision to use `ON_ERROR = CONTINUE` requires a documented reconciliation strategy and approval.

### 5. Read-only load-history investigation

A verified live environment would use suitable Snowflake History APIs and permissions to answer: which files were processed, when, how many rows were parsed/loaded, and which errors occurred?

The following SQL is **an illustration for a future authorized session only; no account was queried**. It assumes the target table exists in the current database and schema, and that the role has visibility.

~~~sql
-- Illustration ONLY: 14-day Information Schema history.
SELECT FILE_NAME, LAST_LOAD_TIME, STATUS,
       ROW_COUNT, ROW_PARSED, ERROR_COUNT
FROM TABLE(
  INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'DBRE_SRE_L8_ORDERS',
    START_TIME => DATEADD('hour', -24, CURRENT_TIMESTAMP())
  )
)
ORDER BY LAST_LOAD_TIME DESC;
~~~

**Expected behavior (hypothetical):** Recent completed bulk `COPY INTO` and Snowpipe file loads can appear, with file-level status and counters. No history row may mean no eligible completed load, insufficient privileges, an incorrect context, historical limits, or changed table/pipe objects; **it is not proof of pipeline health**.

Source scope matters:

| Source | Typical scope and limits | Practical use |
|---|---|---|
| `INFORMATION_SCHEMA.COPY_HISTORY` table function | Recent **14 days**, role/object visibility requirements | Recent file-level load triage |
| `SNOWFLAKE.ACCOUNT_USAGE.COPY_HISTORY` | Historical view (approximately **365 days**), view-specific latency and approved access | Longer-term trends and audits |
| `QUERY_HISTORY` | SQL query execution telemetry, not a substitute for a business source-to-target reconciliation | Investigate slow/failed warehouse-backed loads |

Do not infer freshness from only an Account Usage view: it may lag behind a live incident. Treat error messages and filenames as potentially sensitive; report aggregated counts in shared tickets where appropriate.

### 6. Validation, reconciliation and idempotency

A trustworthy load acceptance process requires three independent questions:

1. **File arrival:** Did the expected source files arrive at the correct stage and path?
2. **Parsing and ingest:** Were the files accepted/processed by the intended pipeline, with errors accounted for?
3. **Business correctness:** Do expected distinct business records and amounts match the target, after permitted deduplication/quarantine rules?

For the fictional CSV above, a **paper-only** reconciliation might record four source data rows, three parseable rows and one invalid numeric field. A *hypothetical* strict `ABORT_STATEMENT` load should not be represented as having loaded three successful rows. The instructor must not claim actual `COPY_HISTORY` evidence, because no load has occurred.

**Replay caution:** Snowflake maintains load metadata for file deduplication under supported conditions. Replacing files, changing object identity, truncating/recreating a target, overriding the default behavior with `FORCE`, or re-running an ingestion process can change replay risk. Before any nonproduction replay, check source immutability, targeted file list, batch ID, business-key deduplication, downstream impact, rollback and owner approval.

### 7. On-call troubleshooting workflow

~~~text
Report missing/stale data
   |
   +-- Is source file expected and present?
   |     No -> upstream source/storage owner; check object path and event time
   |
   +-- Can Snowflake see the stage under approved permissions?
   |     No -> storage integration / role / security owner
   |
   +-- Does validation show delimiter, header or type conversion errors?
   |     Yes -> quarantine / producer correction under data-owner review
   |
   +-- Did COPY or Snowpipe process the file?
   |     No -> inspect pipe state, event delivery, eligibility/history
   |
   +-- Do target counts and freshness meet the business SLO?
         No -> reconcile, inspect transforms and dependencies
         Yes -> record evidence and close with owner validation
~~~

**Suggested SLI/SLO fields:** file arrival lag, end-to-end source-to-target freshness, load failure count, rejected-row ratio, number of unprocessed files, and per-workload Snowflake credits. Set targets with the application/data owner; this chapter does not propose a universal production threshold.

## Hands-on lab and expected results

**Offline exercise only:** Open the [Chapter 08 learner worksheet](../exercises/chapter-08-ingestion-tabletop.md) and solve it on paper. Do **not** execute the SQL above, create stages, run `COPY`, insert records, alter pipes or request privileged roles. All outcomes are instructional examples.

**Scenario:** The fictional orders CSV has four data rows including one malformed amount. A dashboard is stale even though a storage owner says a file was uploaded.

| Step | Student task | Expected reasoning (not observed results) |
|---|---|---|
| 1 | Draw source → stage → loader → target → dashboard | Staging/loader/transform dependencies are distinct |
| 2 | Explain why row 104 is suspect | Non-numeric amount cannot populate a typed `NUMBER` field |
| 3 | Explain `VALIDATION_MODE = RETURN_ERRORS` | Validation checks issues without loading data |
| 4 | Describe evidence sources | File listing, permitted COPY_HISTORY, pipe/job state and downstream freshness |
| 5 | Propose a retry/replay decision | Check history, quarantining, business keys, and obtain owner approval |

**Expected:** Four fictional data rows; three parseable numeric amounts totaling 250, including EAST 170 and WEST 80; one bad row. These are **paper calculations only**, not an observed successful load.  
**Pass:** Learner can explain the invalid row, validation-versus-load distinction, load-history scope and safe escalation without recommending a blind `FORCE` replay.

## DBRE/SRE troubleshooting quick reference

| Symptom | Check | Likely owner or escalation |
|---|---|---|
| No staged files | Source object URI/prefix, upload time, upstream batch | Source/storage owner |
| Stage permission error | Storage integration, role inheritance and stage privileges | IAM/Security + DBRE |
| Bad CSV amount/header | File format, type mapping, staged-file validation | Data engineering + producer |
| Snowpipe has no new rows | Notification delivery, pipe state/status and load history | Data engineering + platform |
| COPY reports skipped/duplicate file | Prior file-load metadata and object identity | DBRE + data owner; **never blindly FORCE** |
| Counts don't match | Source manifest, parse/error counts, target duplicates and transformations | Data owner + analytics |
| Dashboard remains stale | Ingestion lag, transformation tasks, refresh schedule and query layer | Data/app owner + DBRE |
| Unexpected credits | Warehouse uptime/size, Snowpipe usage, region transfer and meter scope | FinOps + platform |

## Knowledge check (with answers)

1. **What is a stage?** A location used by Snowflake to access files before they are loaded. Internal stages use account-managed storage; external stages point to supported externally managed cloud storage. A stage is not the final business table.
2. **What is a CSV file format?** The parsing rules for a file, including field delimiter, header handling, quoting and null interpretation. A wrong format can turn valid source files into load errors or incorrect values.
3. **What is the difference between `VALIDATION_MODE` and an actual `COPY INTO` load?** Validation attempts to inspect staged data for supported parsing/conversion issues **without loading rows**; an authorized load is a mutating operation. Validation has restrictions and does not prove downstream business correctness.
4. **Where can a DBRE check recent load activity?** The permitted `INFORMATION_SCHEMA.COPY_HISTORY` table function, with a **14-day** window, reports file-level status/error and counts; `ACCOUNT_USAGE.COPY_HISTORY` supplies longer history but can lag. Neither proves source files missing from a stage were expected to exist.
5. **What should happen before replaying a failed batch?** Confirm correct source files, per-file load state, parser issues, deduplication/business keys, downstream impact, approval and rollback. Blindly using `FORCE = TRUE` or broad privileges can introduce duplicates and risk.

**Instructor scoring:** Each question is 0, 1 or 2 points (10 total). Award 2 for the concept plus operational caveat, 1 for a correct term without a meaningful explanation, and 0 for incorrect or unsafe advice. Treat advice to load real customer/patient data, reveal credentials, silently discard errors or blindly replay as a critical safety miss requiring remediation irrespective of score. This grading is **offline pedagogy, not V03 runtime acceptance**.

## Operational safety and validation

- **V01/V02:** Author documentation and offline structural/consistency tests are the only available evidence; these tests do not compile/run Snowflake SQL.
- **V03:** **USER-DEFERRED / NOT RUN**. No training-account stage/table created, no file uploaded, no `COPY INTO` executed, no Snowpipe event emitted and no real query IDs/costs gathered.
- **V04:** **SKIPPED BY OWNER / NOT APPROVED**, and no external reviewer was assigned.
- **V05:** **NOT CERTIFIED**. No data-pipeline, security or production-operation acceptance follows from this chapter.
- **Data safety:** Use fictional examples only, no real patient/customer identifiers, raw secrets or unapproved replay.
- **Owner controls:** Any actual ingestion, reprocessing, pipe state change or storage-IAM modification requires a separate authorization and controlled nonproduction runbook.

## Continue into the full 90-chapter curriculum

For deeper material, follow the canonical chapters: [11 — Stages](../../11-stages-internal-external.md), [12 — File Formats](../../12-file-formats.md), [13 — COPY INTO](../../13-copy-into-bulk-data-loading.md), [15 — Data Loading Troubleshooting](../../15-data-loading-troubleshooting-validation.md), [16 — Snowpipe](../../16-snowpipe.md), [17 — Snowpipe Streaming](../../17-snowpipe-streaming.md), and [78 — Production Loading Troubleshooting](../../78-snowflake-data-loading-snowpipe-troubleshooting.md).

## Official documentation

- [Overview of data loading](https://docs.snowflake.com/en/user-guide/data-load-overview)
- [COPY INTO table: syntax and validation](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)
- [COPY_HISTORY table function](https://docs.snowflake.com/en/sql-reference/functions/copy_history)
- [COPY_HISTORY account usage view](https://docs.snowflake.com/en/sql-reference/account-usage/copy_history)
- [Snowpipe overview](https://docs.snowflake.com/en/user-guide/data-load-snowpipe-intro)

[Previous chapter](chapter-07-troubleshooting-incident-response.md) | [All chapters](../README.md)
