# Semantic validation progress — independent PostgreSQL enterprise track

**Review date:** 2026-11-04  
**Branch reviewed:** `main`  
**Scope:** `postgresql/postgresql-dbre-sre-enterprise-learning-path/`

## Validation boundaries

This is a source-level technical review, **not** executed lab evidence, independent sign-off, or production certification. All 20 chapters and 20 lab READMEs are authored according to the track's README, master TOC and status tracker. Runtime validation remains **0/20**. No commands were run against a PostgreSQL server.

## Chapter 02 — relational design and constraints

**Files reviewed:**
- [Chapter 02 lesson](../chapters/02-databases-schemas-tables-and-relationships.md)
- [Chapter 02 lab](../labs/chapter-02/README.md)

**Static semantic checks:**
- PostgreSQL 17-compatible constructs: identity columns, `NUMERIC(12,2)`, `TIMESTAMPTZ`, PK/UNIQUE/FK/CHECK constraints, `CREATE SCHEMA`, `CREATE INDEX`, catalog queries, `SAVEPOINT`, and `ROLLBACK TO SAVEPOINT`.
- PowerShell Docker invocations target the named `pg-fleet-lab` container; SQL and `psql` meta-commands are distinguished.
- Inserts create two customers, two products, one order and one order item when the database starts empty. The notebook order total is `2 * 9.50 = 19.00`; generated IDs are not assumed fixed.
- Two deliberate constraint violations occur inside separate transactions with savepoint recovery. These errors are expected and must not be treated as successful all-green SQL script execution.
- The chapter explicitly warns about repeated execution, production DDL, and foreign-key index assumptions.
- Chapter-to-lab and lab-to-chapter relative paths are consistent by inspection; official reference URLs are present but have **not yet been HTTP-checked**.

**Review result:** No confirmed source-level SQL/PowerShell defect in the reviewed Chapter 02 examples. This does not prove runtime correctness.

**Operational caution:** The lab requires a disposable PostgreSQL 17 Docker instance prepared in Chapter 01. Its `CREATE SCHEMA` and seed inserts are not idempotent; the lab explicitly says to run once in a clean database and inspect existing objects before rerunning. Do not automate a reset/drop.

## Execution availability and evidence requirements

The current validation environment has no `docker`, `psql`, or `shellcheck` executable on PATH. Therefore Chapter 02 remains **not executed**. No synthetic terminal output is recorded as test evidence.

When an isolated PostgreSQL 17 runtime is available, record:
1. Image digest and `SELECT version()`; container/database identity and disposable-environment confirmation.
2. Each executed SQL/PowerShell command and sanitized stdout/stderr with timestamps.
3. Table row counts `2/2/1/1`, order total `19.00`, both intentional constraint errors and successful savepoint recovery.
4. Index inventory, database/schema identity, cleanup or retained-disposable-instance decision.
5. Test reviewer, actual pass/fail result, and evidence artifact location.

Do not change the track's runtime-validation status until this evidence exists.

## Remaining work

- Semantic review Chapters 03–20 (and re-check any prior work only if the evidence is missing); SQL, shell, PowerShell, and provider-specific command safety.
- Resolve all internal relative links and verify external official documentation URLs.
- Execute labs only in explicitly disposable PostgreSQL 17 environments; AWS and Kubernetes provider exercises remain optional and must not create costs or affect live infrastructure.
- Obtain independent technical review separately from source-level checks and runtime execution.

## Official PostgreSQL 17 references

- [Data definition](https://www.postgresql.org/docs/17/ddl.html)
- [Constraints](https://www.postgresql.org/docs/17/ddl-constraints.html)
- [psql](https://www.postgresql.org/docs/17/app-psql.html)
- [Transactions](https://www.postgresql.org/docs/17/tutorial-transactions.html)

## Chapter 03 — transactions, ACID and two-session MVCC

**Files reviewed:** [lesson](../chapters/03-sql-transactions-acid-and-mvcc.md) and [lab](../labs/chapter-03/README.md). **Review type:** source-level semantic inspection only; no PostgreSQL runtime execution.

- The lab explicitly separates PowerShell Docker commands from SQL in interactive `psql` and requires distinct backend PIDs for Sessions A and B. `BEGIN ISOLATION LEVEL READ COMMITTED` and `BEGIN ISOLATION LEVEL REPEATABLE READ` are PostgreSQL 17-compatible transaction forms.
- Seed balances are 100.00/100.00. The atomic transfer of 25 yields 75.00/125.00 (sum 200.00). The explicit rollback temporarily shows 65.00 and restores 75.00; savepoint rollback temporarily shows 70.00 and restores 75.00. The intentional `CHECK (balance >= 0)` error is followed by `ROLLBACK TO SAVEPOINT`, allowing `COMMIT`.
- Under READ COMMITTED, A reads 75.00, B commits a subtraction of 5, then A reads 70.00. Under REPEATABLE READ, A first reads 70.00 and establishes its snapshot, B commits an addition of 3, A continues to read 70.00 until COMMIT and reads 73.00 afterward. Final balances 73.00/125.00 (sum 198.00) are arithmetically consistent and the deliberate non-conservation is disclosed.
- `pg_stat_activity` is read-only. The lab calls for promptly committing A's short diagnostic transaction and disconnecting both sessions. It does not prescribe backend termination or destructive database cleanup. Existing database/table collisions are flagged for manual inspection, not automatic dropping.
- Relative chapter/lab links are consistent by inspection. PostgreSQL 17 official documentation URLs are listed; HTTP reachability has not yet been verified. No confirmed semantic defect was identified in this pass.

**Runtime evidence required:** capture disposable container identity/image digest, PostgreSQL version, two distinct backend PIDs, the ordered interleaved A/B transcript, intended constraint error and recovery, transaction isolation settings, final balances, session disconnect/cleanup confirmation and sanitized timestamps. Until actual execution, Chapter 03 remains **not runtime verified**.

**Chapter 04 review is recorded below.** No independent sign-off or production certification is implied.

## Chapter 04 — WAL, shared buffers and checkpoints

**Files reviewed:** [lesson](../chapters/04-postgresql-internals-wal-buffers-and-checkpoints.md) and [lab](../labs/chapter-04/README.md). **Review type:** source-level semantic inspection only; not a PostgreSQL execution result.

- The preflight checks Docker Linux mode, the named disposable `pg-fleet-lab` container, PostgreSQL 17 and `pg_is_in_recovery() = false` before database creation. The lab checks for a pre-existing `training_ch04` database and stops rather than dropping it.
- The SQL creates a synthetic table with a PostgreSQL 17 identity column, captures `pg_current_wal_lsn()` using interactive `psql` `\\gset`, inserts 2,000 generated rows in one transaction, then computes a WAL byte-distance with `pg_wal_lsn_diff()`. The quoted `:'start_lsn'::pg_lsn` and `:'end_lsn'::pg_lsn` substitutions require the same interactive `psql` session; the instructions state this.
- `pg_stat_wal`, `pg_stat_checkpointer`, `pg_stat_bgwriter`, `pg_stat_io`, `pg_stat_database` and `pg_replication_slots` are used read-only. The lesson correctly distinguishes PostgreSQL 17 checkpointer statistics from older `pg_stat_bgwriter` checkpoint columns. The ratio query protects against division by zero via `NULLIF`.
- The lab does not force `CHECKPOINT`, reset statistics, change durability settings, manipulate replication slots, or delete WAL. It correctly warns that LSN differences and cumulative WAL counters need not match and that an unchanged checkpoint counter is acceptable.
- **Operational limitation:** the exercise uses a superuser inside a disposable local container. This is not a least-privilege monitoring-role template for production. The lab intentionally retains the separate database; eventual cleanup requires an independently confirmed disposable environment.
- Chapter/lab relative navigation links are consistent by inspection. Official PostgreSQL 17 URLs are present but **HTTP reachability and complete external-reference validation are pending**.

**Review result:** No confirmed source-level defect in Chapter 04. **Runtime status: not executed.** Required evidence: PostgreSQL image digest, version and identity, preflight outputs, initial database-existence check, sanitized interactive `psql` transcript, 2,000-row count, both LSNs and positive byte-distance, WAL/checkpointer/bgwriter/I/O observations, configuration and slot inventory, and explicit cleanup/retention decision. No reviewer approval or production certification is inferred.

**Next unreviewed milestone:** Chapter 05 — index and query-plan SQL/shell semantics; continue external-reference checks and isolated runtime preparation.

## Chapter 05 — indexes, query plans and performance

**Files reviewed:** [lesson](../chapters/05-indexes-query-plans-and-performance.md) and [lab](../labs/chapter-05/README.md). **Scope:** static semantic review of PostgreSQL 17 SQL, PowerShell/Docker preflight, sample arithmetic, index and EXPLAIN safety. **Not executed.**

- The preflight checks Linux Docker, named container, PostgreSQL version and database absence before creating `training_ch05`; the lab does not overwrite an existing database. Interactive `psql` SQL is separated from PowerShell commands.
- The 200,000-row `generate_series` workload produces exactly 2,000 distinct customers with 100 events each. Every tenth row is pending, yielding 20,000 pending rows. `GENERATED ALWAYS AS IDENTITY`, `TIMESTAMPTZ` arithmetic, `FILTER`, `ANALYZE`, and `EXPLAIN (ANALYZE, BUFFERS)` are PostgreSQL 17-compatible constructs.
- The composite B-tree index on `(customer_id, created_at DESC)` can support equality-filtered ordered top-20 retrieval; it does not guarantee a specific plan or latency. The optional `WHERE status = 'pending'` partial index matches the literal query predicate. The lesson appropriately notes that `INCLUDE (amount)` does not cover `event_id` and cannot by itself guarantee an index-only scan.
- `pg_indexes`, `pg_class`, `pg_namespace`, `pg_stat_user_indexes`, `pg_relation_size`, `pg_indexes_size` and `pg_total_relation_size` are appropriate for the stated read-only inventory. The broad predicate `customer_id BETWEEN 1 AND 2000` matches all synthetic rows, making a sequential scan plausible, not mandatory.
- The lab correctly warns that EXPLAIN ANALYZE executes statements, limits measured statements to read-only SELECT, and avoids forcing planner settings, destructive drops, production DDL or arbitrary index removal. Repeated execution is intentionally non-idempotent and requires inspection first.
- Relative lesson/lab navigation paths are consistent by source inspection. PostgreSQL 17 official documentation URLs are listed; external HTTP reachability is **not verified** in this review.

**Result:** No confirmed source-level semantic defect in Chapter 05. **Runtime remains not executed**; independent review and certification remain pending.

**Evidence needed:** disposable container identity and image digest, `SELECT version()`, database absence preflight, insert result and counts (200000/20000/2000), before/after actual EXPLAIN plans and buffer/timing measurements, index inventory and sizes, optional partial-index status, final database identity and retention/cleanup decision. Capture sanitized transcripts and timestamps; never substitute example plans for observed output.

**Next unreviewed milestone:** Chapter 06 — bare-metal PostgreSQL operational semantics and safe local exercises; then continue Chapters 07–20 and external URL verification.

## Chapter 06 — bare-metal operations and container persistence

**Files reviewed:** [lesson](../chapters/06-postgresql-on-bare-metal.md) and [lab](../labs/chapter-06/README.md). **Review type:** source-level SQL/PowerShell/Bash and operational safety inspection; **not executed**.

- The lesson correctly distinguishes self-managed Linux-host ownership from the local Docker simulation; the lab does not claim to test systemd integration, physical durability, host kernel settings, independent HA or recovery.
- The dedicated lab names (`pg-baremetal-ch06`, `pg_baremetal_ch06_data`, `training_ch06`, loopback port `55436`) are consistently used. Preflight checks for existing resources and a listening port are read-only, and the procedure explicitly stops rather than deleting unknown resources.
- The `postgres:17` Docker invocation uses PowerShell backtick continuation and a named volume mounted at `/var/lib/postgresql/data`. The training-only `POSTGRES_PASSWORD` is disclosed as inspectable metadata, and `docker inspect` output is specifically excluded from unrestricted evidence. The image tag is mutable: record the actual image digest during execution.
- `SELECT current_database(), current_user, version()`, `pg_is_in_recovery()`, `SHOW data_directory/config_file/hba_file/ident_file`, `pg_settings`, `pg_hba_file_rules`, `pg_stat_database`, `pg_database_size` and `pg_postmaster_start_time()` are compatible with PostgreSQL 17. The `pg_hba_file_rules` query is diagnostic only and does not alter authentication.
- The marker DDL and insert use `ON_ERROR_STOP=1`, and the expected single `(1, 'persisted')` row follows from the clean database assumption. Re-running DDL is intentionally not idempotent and requires identity inspection. The optional `docker stop --time 60` and `docker start` apply only to the confirmed disposable container; a subsequent marker read demonstrates local persistence, not recovery certification.
- The optional Linux-host commands (`hostnamectl`, `systemctl list-units`, `lsblk`, `df`, `ss`) are read-only, explicitly restricted to approved non-production staging. The lab avoids restarting host services or changing firewall/kernel settings. No destructive cleanup command is provided; retained volume ownership must be confirmed before any eventual deletion.
- Internal lesson/lab navigation paths are consistent by inspection. Official PostgreSQL 17 reference URLs are listed but **external HTTP reachability has not yet been checked**.

**Result:** No confirmed source-level defect found in Chapter 06 during this review. **Runtime status: not executed; independent review: pending; production certification: not established.**

**Runtime evidence required:** record Docker/host versions, Linux-container mode, image digest, absence of pre-existing names/port listener, actual container and database identity, PostgreSQL version and role, configuration/HBA results, scoped storage/resource observations, marker insertion and row count, optional stop/start timestamps and persistence, sanitized logs, and a documented retention/cleanup decision. No observed outputs were fabricated.

**Next unreviewed milestone:** Chapter 07 — AWS RDS architecture and optional provider steps; verify cloud actions remain explicitly optional and cost-safe. External reference checks and isolated PostgreSQL 17 runtime execution remain outstanding.


## Chapter 07 — Amazon RDS for PostgreSQL and cost-free comparison lab

**Files reviewed:** [lesson](../chapters/07-postgresql-on-aws-rds.md) and [lab](../labs/chapter-07/README.md). **Review date:** 2026-11-04. **Scope:** PostgreSQL 17 SQL semantics, PowerShell/Docker commands, AWS CLI inventory safety, architecture distinctions, backup/restore and evidence. **Static review only; no PostgreSQL or AWS commands executed.**

- The lab checks for existing `training_ch07`, `training_ch07_restore` databases and cluster-wide `ch07_reader` role before creating anything. It uses the pre-existing disposable `pg-fleet-lab` container and synthetic data. `CREATE SCHEMA`, identity-column DDL, three event inserts, `pg_settings`, `pg_stat_database`, `pg_stat_activity` and database-size queries are compatible with PostgreSQL 17.
- `CREATE ROLE ch07_reader NOLOGIN NOSUPERUSER`, explicit CONNECT/USAGE/SELECT grants and `SET ROLE` demonstrate privilege separation without adding a login or exposing a password. The SELECT count should be 3; the INSERT under the reader role is an **intentional permission-denied negative test**. `RESET ROLE` restores the original effective role. This local superuser exercise does not simulate RDS `rds_superuser`.
- The `pg_dump -Fc` archive and `pg_restore` into `training_ch07_restore` form a valid local logical-backup exercise; expected restored count is 3. This is not a proof of independent-host recovery, AWS managed backup, PITR, RPO/RTO, or regional DR. An existing restore database causes the preflight to stop instead of overwriting it.
- Optional AWS CLI commands use only `sts get-caller-identity`, `rds describe-db-instances` and `rds describe-db-clusters` with existing authorized identifiers. They do not create, modify, fail over or delete cloud resources. The lesson explicitly states cloud access is optional and calls for sanitizing account/resource metadata.
- Architecture descriptions distinguish Single-AZ, Multi-AZ DB instance (non-readable standby), Multi-AZ DB cluster (readable instances) and asynchronous read replicas. The documented 0–35-day DB-instance and 1–35-day Multi-AZ cluster backup retention, differing creation defaults and 0/nonzero change outage warning match the AWS backup-retention reference checked on 2026-11-04: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.BackupRetention.html .
- The Database Insights documentation URL was reachable on 2026-11-04 and now describes Database Insights: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.Overview.html . These **two URLs only** were HTTP-checked; the remaining external URLs and all cross-file links still need systematic verification.
- Internal lesson/lab/TOC navigation paths are consistent by source inspection. Cleanup intentionally retains isolated databases and the role; no automated DROP or cloud resource teardown is performed.

**Result:** No confirmed source-level defect identified in the Chapter 07 SQL, PowerShell or optional AWS CLI examples. **Runtime: not executed (0/20 track labs). Independent review: pending. Production certification: not established.** The expected permission error is not an all-green command run.

**Runtime evidence needed:** disposable container identity and PostgreSQL version/image digest; absence-of-name checks; actual SQL transcript and three-row count; effective-role change, successful SELECT and expected denied INSERT; `RESET ROLE` and unchanged count; backup archive metadata, restore exit status and restored count; cleanup/retention decision; timestamps and sanitized evidence. Mark AWS inventory `SKIPPED` unless real authorized output exists. Do not use sample outputs as evidence.

**Next unreviewed milestone:** Chapter 08 — PostgreSQL on Kubernetes, including manifest safety, operator assumptions and optional provider exercises. Continue systematic external-link verification and isolated PostgreSQL 17 runtime preparation.


## Chapter 08 — PostgreSQL on Kubernetes: operator and persistence review

**Files inspected:** [lesson](../chapters/08-postgresql-on-kubernetes.md), [lab](../labs/chapter-08/README.md), [CloudNativePG example](../labs/chapter-08/cluster-example.yaml). **Review date:** 2026-11-04. **Review type:** source-level only; Docker, PostgreSQL, Kubernetes and cloud operations were not executed.

- The CloudNativePG custom resource uses `apiVersion: postgresql.cnpg.io/v1`, `kind: Cluster`, one instance, a 1Gi storage request and `bootstrap.initdb` with database/owner `app`. The lesson and manifest consistently describe this as a **review-only, non-HA** example, not a deployable production topology. Operator installation, namespace existence, CRD schema, storage class and PostgreSQL image selection must be checked against an actual installed operator before applying it anywhere. This is a schema plausibility review, **not** a Kubernetes API-server dry-run or CRD validation.
- The default PowerShell lab uses `postgres:17`, loopback port `55438`, container `pg-k8s-lab`, named volume `pg_k8s_ch08_data` and database `appdb`. Docker inspection, `pg_isready`, `psql`, `pg_database_size`, `pg_current_wal_lsn` and `pg_stat_activity` commands are syntactically plausible for the stated environment. The preflight checks container and volume name collisions; **port 55438 availability is stated as a prerequisite but not explicitly tested before `docker run`**. A port bind failure is recoverable by inspection, not permission to delete other resources.
- The marker table uses `CREATE TABLE IF NOT EXISTS`, a primary key and `INSERT ... ON CONFLICT DO NOTHING`. In a clean database the expected row is `persist-01 / created-before-restart`. On a rerun an existing marker could contain another value: the upsert intentionally preserves it, so compare the observed value rather than assuming an overwrite. `docker restart` and the post-restart SELECT test persistence in the **same named volume**, not Kubernetes failover, recovery, PITR, durability under node loss, RPO or RTO.
- Optional `kubectl config current-context`, `cluster-info`, `get crd`, `get namespaces`, `get clusters`, `get pods`, `get pvc` and `get events` are read-only inventory operations. The lab requires prior authorization and a known non-production context. These commands can still expose operational metadata, so evidence must be sanitized. The lab does **not** invoke `kubectl apply`, install an operator, provision cloud resources or cause intentional disruption.
- The cleanup section explicitly marks `docker stop`, `docker rm` and `docker volume rm` as manual, destructive and local-only; do not run automatically. The chapter correctly separates PV/PVC persistence, independent backups, operator reconciliation and fencing. A single instance is not HA and a StatefulSet is not itself PostgreSQL HA.
- Internal chapter-to-lab and lab-to-manifest paths were resolved by fetching their exact GitHub files. Official Kubernetes, PostgreSQL and CloudNativePG reference URLs are listed; **systematic HTTP reachability and versioned operator-reference verification remain pending**. The chapter links to the CloudNativePG `devel` bootstrap documentation and warns against assuming development-branch examples match a deployed release.

**Result:** No confirmed blocking SQL/PowerShell/manifest defect found in this source inspection. **Actionable improvement (low severity):** add an explicit read-only local port availability check before the Docker start command in a later guarded edit; this is not proof of a current failure. **Runtime: not executed. Independent review: pending. Production certification: not established.**

**Evidence required before runtime status can advance:** Docker client/server versions and Linux mode, container and volume ownership preflight, loopback port availability, immutable PostgreSQL image digest and `SELECT version()`, actual marker before/after restart, restart/readiness timestamps, volume mount inspection, database/WAL/session observations, sanitized transcripts, a retained-volume or explicitly authorized cleanup decision, and a separate manifest worksheet. Mark optional Kubernetes steps `SKIPPED` unless actual authorized output is captured. Do not infer Kubernetes operator behavior from the Docker exercise.

**Next unreviewed milestone:** Chapter 09 — enterprise PostgreSQL architecture selection. Continue external reference checks and isolated PostgreSQL 17 runtime validation when genuinely available.


## Chapter 09 — Enterprise architecture selection and temporary-table scoring

**Review date:** 2026-11-04. **Files reviewed:** [lesson](../chapters/09-selecting-the-right-enterprise-postgresql-architecture.md) and [lab](../labs/chapter-09/README.md). **Method:** source-level SQL/PowerShell/architecture review only; no PostgreSQL, Docker, AWS or Kubernetes execution.

- The lab's Docker preflight uses `docker version`, a name-filtered `docker ps`, `pg_isready`, and `psql -c 'SELECT version()'`. The name filter can match partial names, so the operator must still confirm the exact disposable `pg-fleet-lab` identity before any `docker exec`. No resource creation or deletion occurs in this chapter.
- PostgreSQL 17 supports the used `CREATE TEMP TABLE`, table `CHECK` constraints, `CREATE TEMP VIEW`, `IS TRUE`, `ROUND(numeric, 2)`, `CROSS JOIN`, `UPDATE`, `SHOW`, `pg_is_in_recovery()` and `pg_database_size()` syntax. The interactive single-session requirement is essential: all temporary relations disappear at disconnect. `architecture_weights` has a sum-to-100 CHECK but no single-row constraint; a second valid weight row would duplicate candidate rows in the CROSS JOIN. This is a **low-severity robustness limitation**, not a failure of the documented clean-session example. Avoid reuse of a modified session.
- Recalculated weighted scores from the documented inserts: bare metal/VM **3.25**, RDS Multi-AZ instance **3.90**, RDS Multi-AZ cluster **3.70**, Kubernetes CNPG **3.55**. The baseline ordering (three eligible, CNPG blocked), residency-change ordering (CNPG and bare metal eligible), and NULL extension gate behavior follow from the view definition. `IS TRUE` correctly treats FALSE and NULL as not passing; preference scores remain visible for blocked candidates but never make them eligible.
- Architecture discussion correctly distinguishes RDS Multi-AZ DB instance non-readable standby from Multi-AZ DB cluster readable standby topology; backup/replication claims are not presented as demonstrated RPO/RTO. CloudNativePG and AWS examples are optional, read-only inventory commands and may disclose metadata; no provisioning, operator install, failover or charge-incurring operation is required.
- Internal lesson/lab/TOC and Chapter 01 prerequisite links are consistent by path inspection. Official PostgreSQL 17, AWS RDS, Kubernetes and CloudNativePG references are included, but **HTTP reachability and deployed-version compatibility have not been independently checked in this review**. Do not interpret author-supplied “checked” dates as verification evidence from this audit.
- **Cleanup:** `\\q` ends the `psql` session and drops temporary objects; no database, container, volume or cloud deletion is authorized. An ADR generated from the fictional data must remain provisional, not production approval.

**Result:** No confirmed blocking SQL or PowerShell defect. **Actionable improvement (low severity):** enforce exactly one weights row if the example is later made reusable, and strengthen exact-container identity preflight. **Runtime: not executed (0/20). Independent review: pending. Production certification: not established.**

**Runtime evidence required:** Docker client/server version, exact disposable container identity, PostgreSQL 17 version and image digest, sanitized baseline SQL, temp object creation and inserts, actual four baseline scores and gate ordering, changed-residency and NULL-gate outputs, total weight 100, ADR marked provisional, session exit and absence of persistent changes. Optional AWS/Kubernetes inspection should be recorded as SKIPPED unless authorized evidence exists.

**Next unreviewed milestone:** Chapter 10 — streaming replication and high availability; prioritize single-writer, failover/fencing and cleanup safety. Complete remaining external-link checks separately before any runtime certification.


## Chapter 10 — physical streaming replication and single-writer safety

**Review date:** 2026-11-04. **Files inspected:** [lesson](../chapters/10-streaming-replication-and-high-availability.md) and [lab](../labs/chapter-10/README.md). **Method:** source-level PostgreSQL 17 SQL, PowerShell/Docker, sequencing and operational-risk review. **Not executed.**

- The lab isolates its names (`pg-ha10-primary`, `pg-ha10-standby`, `pg-ha10-net`, two named volumes), publishes no database ports, and explicitly stops on existing resource collisions. Both instances share one Docker host, so this is replication instruction, not an HA/fencing/RPO demonstration. The network is internal, not a substitute for host security.
- PostgreSQL 17-compatible commands include `CREATE ROLE ... REPLICATION LOGIN`, `pg_basebackup -Fp -Xs -P -R -C -S`, `pg_is_in_recovery()`, `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_replication_slots`, `pg_last_wal_receive_lsn()`, `pg_last_wal_replay_lsn()` and `pg_wal_lsn_diff()`. The primary/standby read-only queries and slot-size estimate are appropriate; WAL position gap is not exact retained disk bytes.
- The setup order is meaningful: create primary and replication role/HBA, prepare the empty standby volume, run base backup with `-R` and slot creation, install restricted `.pgpass`, start standby, then test primary writes and standby read-only behavior. The standby INSERT must fail; it is not an all-success script. Async replay can lag, so a first standby SELECT may fail before table creation is replayed; retry SELECT only.
- **Actionable robustness improvement (medium):** the documented `pg_basebackup` uses `PGPASSWORD` while its connection string references a `passfile` that does not yet exist. Environment-password fallback should allow authentication, but the future standby relies on the separately created `.pgpass`. Add an explicit check that the standby's generated `primary_conninfo` references the intended passfile, without printing credentials, before first startup. A failed or interrupted base backup can leave an allocated slot and partially populated volume; the current instructions correctly forbid blind reruns or slot deletion.
- **Actionable safety improvement (low):** Docker `--filter name=pg-ha10-` is a substring match, not an exact identity/ownership assertion. Inspect exact container/volume/network names before any creation or optional cleanup. The optional cleanup is irreversible and must remain manual; no promotion, forced failover, network partition, replication-slot deletion or live-system operation is authorized.
- PostgreSQL official documentation links are present in lesson and lab; **HTTP reachability of these Chapter 10 URLs and comprehensive cross-track link validation are not established by this review**. The lab uses static training-only credentials; sanitize transcripts, avoid exporting `docker inspect` environment values, and never reuse credentials outside disposable labs.

**Result:** No confirmed blocking SQL syntax defect identified by source inspection. The passfile-order dependency and exact-identity preflight warrant additional explicit checks before runtime acceptance. **Runtime: not executed (track 0/20). Independent review: pending. Production certification: not established.**

**Evidence required:** Docker client/server and Linux mode, exact resource identity and new-volume confirmation, PostgreSQL 17 minor version and image digest, primary/standby recovery flags, sanitized `pg_basebackup` exit status and slot state, credential-file permission metadata (not contents), streaming sender/receiver observations, replicated synthetic row, intentional standby write rejection with nonzero exit status, WAL/LSN observations, timestamped cleanup/retention decision and explicit no-promotion/no-fencing statement. Do not report measured RPO/RTO.

**Next unreviewed milestone:** Chapter 11 — backup, restore, PITR and disaster recovery. Continue official-reference checks; isolated runtime execution remains pending.


## Chapter 11 — physical backup, named PITR and recovery safety

**Review date:** 2026-11-04. **Files inspected:** [lesson](../chapters/11-backup-restore-pitr-and-disaster-recovery.md) and [lab](../labs/chapter-11/README.md). **Method:** source-level PostgreSQL 17 SQL, PowerShell/Docker, ordered PITR and destructive-operation safety review. **Not executed.**

- PostgreSQL 17 constructs and tools are consistent with the intended scenario: `pg_basebackup -Fp -Xs -P -c fast`, `pg_verifybackup`, `pg_create_restore_point`, `pg_walfile_name`, `pg_switch_wal`, `pg_stat_archiver`, `recovery.signal`, `restore_command`, `recovery_target_name`, and `recovery_target_action=promote`. These are source-level plausibility checks, not observed command successes.
- Sequence is essential: create dedicated volumes and primary; insert baseline; take/verify physical backup; commit safe row 2; create named restore point once; make deliberately bad post-target changes; switch WAL and poll for the named-point segment; stop source; copy base files into an empty separate volume; start recovery with archive mounted read-only; verify only baseline and safe row survive. A missing target segment or incorrect restored row set must fail acceptance.
- **Confirmed documentation/guardrail improvement fixed:** the lab previously labeled a timer starting *after* the base-copy operation as “restore-start-to-verified-query.” It now explicitly labels the measurement as restored-container-start-to-verified-query and discloses excluded copy time. A strict exact-container `docker inspect --format '{{.State.Running}}'` assertion was also added after source stop, before any restored writable container can start. [Fix commit](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/443af39d64aa93165e600b7b4b3818f2ea24817f).
- **Remaining caution:** name-filtered Docker preflight is not a complete ownership guarantee; independently confirm exact names and fresh empty volumes. The lab's same-host archive, plaintext training password and superuser are disposable teaching choices, not enterprise backup security. The source shutdown check is not independent production fencing. Do not automatically run the destructive cleanup block.
- **Internal navigation:** chapter/lab links and their links to course home/TOC/status are path-consistent by source inspection. Official PostgreSQL 17 and provider reference URLs are present; systematic external HTTP checks across the track remain incomplete.

**Result:** One confirmed timing-label defect corrected and an additional single-writer safety assertion added. No confirmed blocking PostgreSQL 17 syntax defect from source inspection. **Runtime: not executed (0/20); independent review: pending; production certification: not established.**

**Runtime evidence needed:** Docker server/version and immutable image digest; exact fresh container/volume identity; PostgreSQL version and archive settings; successful base backup and verify exit statuses; actual source row changes and named restore-point segment; archive polling evidence; exact source-stopped state before restored writable startup; recovery logs, recovered two-row data and count, actual startup-to-query duration with separate base-copy timing if full recovery measurement is desired; sanitized timestamps and cleanup/retention decision. No cloud, failover or production actions authorized.

**Next unreviewed milestone:** Chapter 12 — monitoring, alerting and observability, followed by Chapters 13–20. Comprehensive internal/external reference checks and isolated PostgreSQL 17 runtime tests remain pending.


## Chapter 12 — monitoring, alerting and observability

**Review date:** 2026-11-04. **Files inspected:** [lesson](../chapters/12-monitoring-alerting-and-observability.md) and [lab](../labs/chapter-12/README.md). **Method:** source-level PostgreSQL 17 SQL, PowerShell/Docker, PromQL, YAML and operational-safety review; no commands executed.

- PostgreSQL 17 monitoring SQL uses supported `pg_stat_activity`, `pg_stat_database`, `pg_stat_wal`, `pg_stat_checkpointer`, `pg_stat_replication`, `pg_stat_user_tables`, `pg_stat_clear_snapshot()`, `pg_database_size()` and `pg_is_in_recovery()`. `num_timed`, `num_requested`, `write_time` and `sync_time` are the PostgreSQL 17 checkpointer-view fields. `pg_stat_replication` should be empty for this standalone topology. Statistics are cumulative/asynchronous; changes are not guaranteed to appear immediately, and reset timestamps must be compared before calculating deltas.
- The synthetic insert creates 5,000 rows and the update affects the first 1,000 identity values on a **fresh** instance; expected counts are 5,000 total and 1,000 updated. This expectation depends on a clean table/sequence and is not an idempotent rerun. Stop on an existing container or table; never drop another user's objects to make the example pass.
- The lab uses a dedicated Docker network and container with loopback-bound PostgreSQL, exporter and Prometheus ports. Docker `--filter name=...` is not an exact identity check, and ports 55434/9188/9099 are required but not actively preflight-tested. **Actionable low-severity guardrail:** add explicit exact-name and port-bind checks before creation; do not remove conflicting resources automatically.
- The optional exporter uses a non-superuser monitoring role granted `pg_monitor` and database `CONNECT`. `pg_monitor` has broader observability access than a minimal custom role; sanitize exporter output and logs. Static demo credentials in `docker run -e` and SQL are visible in local process history/metadata and must never be used outside isolated labs. The exporter image tag and its `--datasource.uri` flag have **not** been runtime-verified.
- The Prometheus YAML here-document is syntactically plausible, with a service-name target on the private Docker network; Windows bind-mount path interpretation and image-tag availability remain runtime-dependent. The three PromQL expressions are valid query forms, but `pg_stat_database_numbackends` may be absent depending on exporter collectors/version. `up == 0` does not detect an entirely missing series; the lesson correctly calls for separate missing-series alert handling.
- **Actionable cleanup limitation (low severity):** the combined `docker stop`/`docker rm -v` commands name optional containers even when they were not started. They can return errors in core-only runs; follow the preceding instruction to skip absent optional resources and verify exact ownership before any destructive command. Avoid automatically running cleanup in validation.
- Chapter-to-lab, lab-to-chapter and course navigation relative links are consistent by inspection. Official PostgreSQL, Prometheus, Grafana and exporter references are listed; **HTTP reachability and current exporter/Prometheus release-tag compatibility were not independently established in this review**.

**Result:** No confirmed blocking PostgreSQL 17 SQL syntax defect identified by static inspection. The port/identity preflight and optional cleanup robustness issues remain actionable improvements, not demonstrated runtime failures. **Runtime: not executed (0/20). Independent review: pending. Production certification: not established.**

**Runtime evidence required:** Docker server/client and image digests, exact resource/port preflight, PostgreSQL 17 version and identity, baseline and post-workload statistics with reset timestamps, actual 5,000/1,000 row counts, session-state evidence, sanitized SQL transcript, optional exporter role attributes and scrape metrics, optional Prometheus target/query evidence, and explicit retained-resource or approved cleanup proof. Mark optional components SKIPPED unless actually executed. Never infer app SLO compliance from `up` or `pg_up`.

**Next unreviewed milestone:** Chapter 13 — VACUUM, autovacuum, bloat and maintenance. Comprehensive link and external-reference verification and disposable runtime testing remain pending.


## Chapter 13 — VACUUM, autovacuum, bloat and maintenance

**Review date:** 2026-11-04. **Files inspected:** [lesson](../chapters/13-vacuum-autovacuum-bloat-and-maintenance.md) and [lab](../labs/chapter-13/README.md). **Method:** source-level PostgreSQL 17 SQL, PowerShell/Docker, expected arithmetic, maintenance risk and cleanup inspection. **No SQL/Docker execution.**

- The lab uses its own `pg-maint-ch13` container, with no published host port or cloud resources. Its Docker PowerShell commands are plausible. The name-filtered `docker ps -a --filter "name=pg-maint-ch13"` is not an exact ownership assertion: before creation and especially optional `docker stop`/`docker rm -v`, check exact container identity and ensure no unrelated resource is affected. **Low-severity safety improvement:** add exact-name and image/ownership assertions, and capture evidence before deleting the container/anonymous volume.
- PostgreSQL 17-compatible constructs include `GENERATED ALWAYS AS IDENTITY`, `generate_series`, `repeat(md5(...), 8)`, `ANALYZE`, `FILTER (WHERE ...)`, `pg_stat_clear_snapshot()`, `pg_stat_user_tables`, `pg_stat_progress_vacuum`, `age(datfrozenxid)`, `mxid_age(datminmxid)`, `age(relfrozenxid)`, `mxid_age(relminmxid)`, and standalone `VACUUM (VERBOSE, ANALYZE) public.maintenance_ch13`. VACUUM must not run inside a transaction block. No `VACUUM FULL`, autovacuum disabling, backend termination, slot deletion, or global tuning is instructed.
- On a new container, `generate_series(1,20000)` inserts 20,000 rows. The even-ID UPDATE changes 10,000; the `event_id % 10 = 1` DELETE removes 2,000 odd IDs, so exactly **18,000** remain and **10,000** are processed. This depends on a fresh identity sequence and no prior data; the lab warns against blind reruns.
- The lesson's simple autovacuum trigger example is arithmetically consistent: 50 + 0.2 × 1,000,000 = 200,050. It correctly treats `n_dead_tup` as an estimate, ordinary VACUUM as primarily internal-space reuse, and XID freeze thresholds as distinct from emergency exhaustion. The PostgreSQL 17 trigger description is explicitly simplified; insert-driven vacuuming and table overrides are separately acknowledged.
- **Interpretation caution (low):** the lab runs `ANALYZE` before churn and waits only one second before reading asynchronous statistics. Autovacuum or page pruning may intervene; neither an exact dead-tuple estimate nor a fixed physical-size reduction is an acceptance invariant. Check actual `VACUUM` completion and row count; if counters lag, retry a fresh statistics snapshot. The SQL `SELECT pg_sleep(1)` returns a void value and is not a failed query.
- The optional `docker rm -v` irreversibly removes anonymous-volume data. It is gated on explicit ownership and retained-evidence checks, but **runtime validation must not automatically invoke it** without recording container/volume identity and successful cleanup proof. The training password is inspectable in container metadata; redact it from logs and evidence.
- Lesson/lab and course-navigation relative paths are consistent by manual source inspection. Official PostgreSQL 17 documentation URLs are present; **systematic HTTP verification and whole-track link validation remain pending**.

**Result:** No confirmed blocking PostgreSQL 17 SQL defect in this source-level pass. The exact Docker identity/cleanup guardrail is an actionable low-severity improvement; no source file changed in this pass. **Runtime: not executed (0/20). Independent review: pending. Production certification: not established.**

**Runtime evidence required:** Docker server/version and Linux mode; exact fresh container identity, image digest and PostgreSQL 17 version; preflight and baseline XID/autovacuum settings; actual 20,000-row insert, 10,000-row UPDATE, 2,000-row DELETE and 18,000/10,000 counts; pre/post vacuum estimates and sizes; standalone VACUUM exit/verbose messages and later `last_vacuum` or `vacuum_count`; final XID horizons; sanitized timestamps, evidence paths, and deliberate retention or verified cleanup. Expected counts are not execution evidence.

**Next unreviewed milestone:** Chapter 14 — troubleshooting and incident response. Continue systematic internal/external reference checks, then execute labs only when an isolated PostgreSQL 17 runtime is available.


## Chapter 14 — incident triage and bounded lock-wait diagnosis

**Review date:** 2026-11-04. **Files inspected:** [lesson](../chapters/14-troubleshooting-and-incident-response.md) and [lab](../labs/chapter-14/README.md). **Method:** source-level PostgreSQL 17 SQL, PowerShell/Docker, three-session sequencing, incident mitigation and cleanup review. **No commands executed.**

- PostgreSQL 17 diagnostic constructs are consistent with the intended scenario: `pg_stat_activity`, `pg_blocking_pids(pid)`, `cardinality()`, `pg_locks`, `pg_stat_database`, `pg_stat_replication`, `pg_stat_wal_receiver`, `pg_replication_slots`, `pg_stat_archiver`, `SHOW reserved_connections`, and `SHOW superuser_reserved_connections`. The lesson correctly differentiates ordinary lock timeout (55P03) from deadlock detection (40P01), and cautions that `EXPLAIN ANALYZE` executes queries.
- **Required three-terminal order:** initialize the fresh synthetic table; open independent A/B/C psql clients; A begins and updates id=1 without commit; B begins and issues its conflicting UPDATE with `SET LOCAL lock_timeout='30s'` and `statement_timeout='45s'`; C observes the blocking PID *while B is waiting*; A rolls back; B rolls back after its UPDATE completes or errors; C verifies both rows remain `ready`. A's `idle_in_transaction_session_timeout='90s'` is a backstop and can disconnect the holder before observation. A missed 30-second window is **not** evidence of a failed lock mechanism.
- The lab uses no host port, bind mount, named volume, production connection, deadlock generation, connection flood, promotion, WAL deletion or cloud resource. Both experimental updates are uncommitted; the initial two-row CREATE/INSERT remains committed until optional verified disposable-container removal. `docker rm -v` is destructive and must remain manual and ownership-gated.
- **Actionable low-severity guardrail:** `docker ps -a --filter "name=pg-ir-ch14"` is a substring/regex name filter, not a definitive exact-name ownership test. Before starting or deleting the container, add an exact `docker container inspect pg-ir-ch14` identity check and explicitly verify the current Docker context is an isolated personal/non-production context. The cleanup `docker inspect --format '{{.Name}} {{.Config.Image}}'` is useful but does not alone establish ownership.
- **Actionable evidence improvement:** record the exact backend PIDs, UTC timing of A/B/C steps, whether B timed out or succeeded, both ROLLBACK results, and the final two unchanged rows. Preserve the actual `pg_blocking_pids` output; do not mark the blocking observation passed if the waiter timed out before C sampled it. Collect Docker image digest, PostgreSQL 17 minor version, context, and explicit container stop/removal proof; redact credentials and SQL text containing sensitive data.
- Internal lesson/lab/course navigation links are path-consistent by source inspection. Official PostgreSQL 17 reference URLs are listed; **systematic whole-track internal link resolution and external HTTP verification are still pending**. No independent review or production certification has been obtained.

**Result:** No confirmed blocking SQL or PowerShell semantic defect found in this source review. The exact Docker identity check is an outstanding low-severity hardening task. **Runtime: not executed (0/20); independent review: pending; production certification: not established.** Docker/psql execution was not attempted in this review, so tool availability is not newly established.

**Next unreviewed milestone:** Chapter 15 — fleet inventory and governance. Continue reference verification and reserve PostgreSQL 17 runtime acceptance for genuinely isolated, evidenced execution.


## Chapter 15 — fleet inventory and governance

**Review date:** 2026-11-05. **Files inspected:** [lesson](../chapters/15-fleet-inventory-and-governance.md), [lab](../labs/chapter-15/README.md), [setup.sql](../labs/chapter-15/setup.sql), [inventory.sql](../labs/chapter-15/inventory.sql), [drift.sql](../labs/chapter-15/drift.sql), plus course README, TOC, tracker and prior semantic evidence. **Method:** static PostgreSQL 17 SQL/psql, Docker Bash/PowerShell, expected results, governance and safety inspection. **Not executed.**

- **SQL semantics:** `CREATE ROLE ... NOLOGIN`, `CREATE DATABASE ... OWNER`, `CREATE SCHEMA IF NOT EXISTS ... AUTHORIZATION`, `ON CONFLICT DO NOTHING`, `pg_control_system()`, `pg_database_size(oid)`, `pg_get_userbyid(datdba)`, `pg_roles`, `pg_settings`, and `pg_stat_database` are plausible PostgreSQL 17 constructs. `\\gexec` and `\\connect` require `psql -f` and autocommit; the lab supplies both. The setup changes database connection twice, then inventory/drift reconnect explicitly to `postgres`. No PostgreSQL 17 runtime syntax test was performed.
- **Expected results:** fresh setup creates two NOLOGIN owner roles, two databases, two schemas and two tables; each table receives two synthetic rows. Repeated `INSERT ... ON CONFLICT DO NOTHING` can return `INSERT 0 0`. The drift baseline intentionally compares `max_connections=200` to a stock-image value often near 100; actual values may differ. No setting is modified. Database role ownership is correctly distinguished from business attestation; two databases on one server do not imply two fleet members.
- **Operational guardrails:** the Docker name filters are anchored (`^/pg-fleet-ch15$` and `^pg-fleet-ch15-data$`), and cleanup checks chapter label plus named mount before `docker rm -f` and `docker volume rm`. **Actionable improvement (medium):** explicitly verify Docker context/daemon identity and the exact *absence* of container and volume before creation; independently verify the named volume belongs only to this training container before deletion. The existing label/mount check is necessary but not sufficient proof of ownership. Never automatically execute cleanup or overwrite existing resources.
- **PowerShell and shell:** Bash line continuations are explicitly replaced with a single-line PowerShell `docker run`. The other Docker commands are single-line and shell-neutral. The local loopback port 55415 is specified but no active preflight bind test is provided; add one before runtime acceptance. Password is training-only but visible in Docker metadata; sanitize evidence and do not reuse it.
- **Potential accuracy limitation (low):** `pg_control_system()` is a privileged observation, and `pg_settings`/statistics have visibility and reset limitations. The course explicitly documents these boundaries. The `LEFT JOIN` drift query maps a missing setting to `REVIEW`; a future collector should distinguish missing/unknown from an actual mismatched value, rather than classifying it as ordinary drift.
- **References:** relative links between lesson, lab, three SQL scripts and course navigation are path-consistent by inspection of fetched files. Official PostgreSQL 17, Docker, AWS CLI and CloudNativePG URLs are present. **External HTTP reachability and systematic whole-track link validation have not been established in this pass.** The heading “checked 2026-11-02” in authored files is not independent verification in this review.

**Result:** Source-level semantic review completed for Chapter 15 with no confirmed blocking PostgreSQL 17 syntax defect. Medium-severity resource-provenance/cleanup preflight improvement and low-severity missing-setting classification improvement remain open; no lesson or lab source changed. **Runtime: not executed (0/20). Independent review: pending. Production certification: not established.**

**Runtime evidence required:** Docker client/server/context and Linux mode; exact empty resource preflight and port availability; pinned image digest and PostgreSQL 17 minor version; successful setup SQL exit codes and actual two-database/two-row counts; sanitized inventory outputs and system-identifier handling; actual drift output including `source`; synthetic owner-attestation record; precise named volume/container ownership, cleanup or retention proof, and timestamps. Do not count illustrative output as execution evidence.

**Next unreviewed milestone:** Chapter 16 — security, roles, secrets and compliance. Complete systematic internal/external reference checks before declaring the full static audit complete; then pursue isolated runtime evidence.


## Chapter 16 — security, roles, secrets and compliance

**Files reviewed:** [lesson](../chapters/16-security-roles-secrets-and-compliance.md), [lab](../labs/chapter-16/README.md), track README, MASTER-TOC, STATUS-TRACKER, and earlier semantic review evidence. **Scope:** source-level PostgreSQL 17 SQL and Bash/Docker semantics, expected results, privilege boundaries and cleanup. **No execution performed.**

- **PostgreSQL 17 semantics:** `CREATE ROLE ... NOLOGIN/LOGIN`, `SET ROLE`, schema ownership, `GRANT USAGE`, table grants, `ALTER DEFAULT PRIVILEGES FOR ROLE ... IN SCHEMA`, and role flag queries are compatible by inspection. The administrative local socket session can `SET ROLE` to the synthetic roles. Default membership inheritance is assumed for `ch16_login`; capture actual membership options and `current_user` at runtime. Default privileges apply to future tables created by `ch16_owner`, not the existing `tickets` table.
- **Expected results:** one initial ticket, SELECT succeeds under `ch16_login` via `ch16_reader`, INSERT fails before writer membership, INSERT succeeds after `GRANT ch16_writer TO ch16_login`, and count becomes two. The role remains non-superuser and lacks CREATEDB, CREATEROLE, REPLICATION and BYPASSRLS. These are expected, **not observed**, results.
- **Confirmed test-harness weakness corrected:** the negative-test heredoc was followed only by an informational `echo`, which could mask an unexpected zero exit status in an overall shell invocation. The lab now captures `$?` immediately and exits nonzero if the denied INSERT unexpectedly succeeds. **Remaining limitation:** a nonzero exit alone is not sufficient proof of the *intended* permission denial; an operator must inspect sanitized stderr for `permission denied for table tickets` and rule out connection or syntax errors.
- **Operational safety improvement (medium, open):** the preflight checks Docker context and an anchored container-name filter but does not programmatically require an approved disposable context or assert that the name is absent. Cleanup uses `docker rm -f -v`, which is destructive to the named container and its anonymous volumes. Before any runtime test, verify exact container identity, disposable context, mounts and data ownership, and retain cleanup proof. The bootstrap password is visible in container metadata; do not capture or publish it.
- **Scope limitations:** local admin socket `SET ROLE` does not validate SCRAM, TLS, password rotation, network authentication, audit log retention or enterprise compliance. These are discussion-only controls. No production identity or data is used.
- **References:** chapter-to-lab and track navigation paths match fetched files by inspection. The PostgreSQL 17 official links are plausible version-scoped documentation targets, but independent HTTP checks for this chapter and whole-track link resolution remain pending.

**Result:** Chapter 16 semantic review recorded; one confirmed negative-test guard fixed in the lab. **Runtime validated: 0/20; independent review: pending; production certification: not established.** No Docker, PostgreSQL or cloud commands were executed.

**Runtime evidence required:** approved isolated Docker context; container name absence and image digest; `SELECT version()`; setup SQL exit status; role memberships and flags; reader SELECT and exact denial message plus nonzero exit; writer INSERT and count 2; sanitized timestamps and SQL/CLI outputs; inspected mounts and confirmed cleanup/retention decision.

**Next unreviewed milestone:** Chapter 17 — lifecycle, upgrades and automation. Continue systematic internal/external reference verification and record runtime blockers without claiming execution.


## Chapter 17 — lifecycle, upgrades and automation

**Review date:** 2026-11-05. **Files inspected:** [lesson](../chapters/17-lifecycle-upgrades-and-automation.md), [lab](../labs/chapter-17/README.md), track README, MASTER-TOC, STATUS-TRACKER and prior semantic-review evidence. **Method:** source-only PostgreSQL 17 SQL, shell/PowerShell, upgrade semantics, sequencing, expected outcomes and destructive-operation review. **No Docker/psql execution.**

- **PostgreSQL 17 SQL:** `SHOW server_version`, `current_setting('server_version_num')`, `pg_extension`, `pg_database.datallowconn`, `CREATE TABLE`, `BEGIN; SET LOCAL lock_timeout = '3s'; ALTER TABLE ... ADD COLUMN ... DEFAULT 'new'; COMMIT;`, and `ALTER TABLE ... DROP COLUMN` are compatible by inspection. Each `psql -c` executes in a separate connection; the transaction-bound `SET LOCAL` is scoped to its own ALTER statement. Multiple SQL commands passed to one `-c` string are executed as a single request, with transactional behavior to account for when diagnosing partial failure. No actual server syntax acceptance has been established.
- **Expected observations:** a fresh container begins with `postgres` as database and user and a `server_version_num` starting `17`; `plpgsql` is normally present. The synthetic row receives status `new`; dropping the status column returns the row to its two-column shape; dropping the table removes only the synthetic object. These are expected results, not runtime evidence. An additive schema change and its inverse do not constitute a PostgreSQL major-upgrade or application rollback test.
- **Confirmed operational safety gap (medium, open):** `docker container inspect pg-dbre-ch17` is described as expected to fail, but its failure is not programmatically asserted; the sequence does not validate an approved local disposable Docker context or an exact image/container/mount ownership record before `docker stop` and `docker rm -v`. A name collision makes `docker run` fail safely, but a human continuing subsequent commands could execute against the pre-existing named container. **Action:** require explicit stop-on-failed-preflight, inspect exact resource identity and context before every `docker exec`/cleanup, and never delete a resource not created in this lab. Do not automate cleanup until this is addressed.
- **Portability:** the snippets use single-line Docker and SQL commands that can be entered in Bash or PowerShell. Docker daemon availability, Linux mode, image digest and exact PostgreSQL 17 patch version were not tested. The training password passed with `-e` is exposed in Docker metadata/process history; sanitize transcripts and avoid reuse.
- **Upgrade accuracy:** the lesson correctly distinguishes minor binary patching from major upgrades and notes that `pg_upgrade`, dump/restore and logical replication require separately rehearsed cutover/recovery. `DROP COLUMN` is safe only for this disposable synthetic table; it is not a general rollback for real schema/data changes. Backup, restore, HA sequencing and application compatibility remain planning-only.
- **References:** chapter-to-lab and course navigation paths are consistent by fetched source inspection. PostgreSQL versioning, upgrade, `pg_upgrade`, backup, ALTER TABLE, AWS RDS, CloudNativePG and Docker documentation URLs are provided; **systematic external HTTP reachability and whole-track link verification remain pending**. No independent source verification was performed in this pass.

**Result:** Chapter 17 semantic source review completed; no confirmed PostgreSQL 17 SQL syntax defect. One medium-severity Docker context/resource-provenance guardrail remains open; no lesson or lab file modified. **Semantic reviews recorded: 16/20; runtime validated: 0/20; independent review: pending; production certification: not established.**

**Runtime evidence required:** approved isolated Docker context and Linux server version, exact absent-name preflight, pinned image digest, container ID and mounts, PostgreSQL 17 minor version, actual SQL exit codes and version/extension inventory, row/column state before and after reversible migration, lock-timeout behavior if encountered, sanitized command transcript, and explicit retained-resource or verified cleanup evidence. No production/cloud upgrade execution authorized.

**Next unreviewed milestone:** Chapter 18 — capacity planning, performance and FinOps. Then Chapters 19–20, systematic internal/external link verification, and genuinely isolated PostgreSQL 17 runtime validation.


## Chapter 18 — capacity planning, performance and FinOps

**Review date:** 2026-11-05. **Files inspected:** [lesson](../chapters/18-capacity-planning-performance-and-finops.md), [lab](../labs/chapter-18/README.md), track README, MASTER-TOC, STATUS-TRACKER, original static audit and previous semantic evidence. **Method:** source-level PostgreSQL 17 SQL, Docker/shell/PowerShell, capacity arithmetic, expected results and cleanup safety. **No PostgreSQL/Docker runtime execution.**

- **PostgreSQL 17 SQL:** `CREATE TABLE` with integer primary key, `generate_series`, `repeat(md5(g::text),8)`, `ANALYZE`, `pg_database_size`, `pg_total_relation_size`, `pg_table_size`, `pg_indexes_size`, `pg_stat_user_tables`, `pg_stat_wal.wal_bytes/wal_records`, and `EXPLAIN (ANALYZE, BUFFERS)` on a bounded SELECT are compatible by source inspection. Separate `psql -c` sessions mean cumulative-stat snapshots are not shared between commands. The lab does not reset statistics or change production configuration.
- **Expected workload:** first insert generates 10,000 unique primary keys; second generates keys 10001–20000; the UPDATE matches 2,000 existing keys, yielding 20,000 rows (assuming a fresh isolated table). The primary-key index can support the bounded SELECT but the actual plan, timing, size and WAL delta must be observed rather than predicted. `ANALYZE` refreshes estimates; asynchronous cumulative statistics may lag.
- **Forecast independently recalculated:** 200 + 26×(4/8/12) = 304/408/512 GiB. With a **30% free-space target**, divide by 0.70: 434.286/582.857/731.429 GiB; rounding up to whole GiB gives **435/583/732 GiB** as written. This is illustrative, not measured or a complete provisioned-storage/backup/WAL/replica cost estimate.
- **Safety finding (medium, open):** `docker container inspect pg-dbre-ch18` is expected to fail but its status is not programmatically enforced before later `docker exec` or `docker rm -v`. A pre-existing name conflict stops `docker run`, yet blindly continuing could operate on someone else's container. `docker context show` is mentioned only in troubleshooting; the main preflight does not assert a specifically approved disposable Docker context, container provenance, or mount ownership. **Action:** implement fail-closed context/name/created-container-ID checks and require matching ID/mounts before SQL and teardown; never remove an unknown resource. The password is exposed via Docker metadata; redact it from evidence.
- **Evidence precision (low, open):** the lab captures WAL counters twice but asks for timestamps without providing a reproducible timestamp capture command; add timestamped output or evidence wrapper before runtime acceptance. `docker inspect --format '{{.Image}}'` returns an image ID, not by itself an immutable registry digest; capture `docker image inspect` RepoDigests when available, plus the image ID and PostgreSQL patch version.
- **Cleanup:** `DROP TABLE ch18_capacity` is limited to synthetic data only if the container identity has first been proven. `docker rm -v` deletes anonymous volumes attached to the named container; its use is **not safe merely because the name matches**. Capture mount inspection and post-cleanup absence evidence. No cleanup was performed in this review.
- **References:** lesson-to-lab path and navigation references are consistent by inspection; official PostgreSQL 17 and Docker URLs are present. Full HTTP reachability, anchor checking and whole-track link verification remain **pending**.

**Result:** Chapter 18 semantic review recorded, **17/20** chapters with semantic review evidence. No confirmed blocking PostgreSQL 17 SQL syntax or forecast arithmetic defect by source inspection. Medium-severity container provenance/cleanup guardrail and low-severity evidence precision remain open. **Runtime validated: 0/20; independent review: pending; production certification: not established.**

**Runtime acceptance evidence required:** approved isolated Docker context and engine mode; exact absence of name; container ID and mounts created by this lab; PostgreSQL 17 version and image ID/digest; actual insert/update exit statuses, 10,000→20,000 row counts, size/stat snapshots, timestamped WAL counter differences, actual bounded EXPLAIN, forecast worksheet, sanitized transcripts, and verified cleanup/retention. No production, cloud or user services may be touched.

**Next unreviewed milestone:** Chapter 19 — application requirement gathering and database design; then Chapter 20, systematic reference verification and disposable PostgreSQL 17 runtime testing.


## Chapter 19 — application requirement gathering and database design

**Review date:** 2026-11-05. **Files inspected:** [lesson](../chapters/19-application-requirement-gathering-and-database-design.md), [lab](../labs/chapter-19/README.md), track README, MASTER-TOC, STATUS-TRACKER and existing semantic audit. **Method:** source-level PostgreSQL 17 SQL, shell/PowerShell portability, prerequisite and session ordering, constraint behavior, expected results, safety and cleanup. **Not executed.**

- **SQL semantics:** `GENERATED ALWAYS AS IDENTITY`, `timestamptz`, `CHECK`, `REFERENCES`, `generate_series`, `now()`, `(g || ' hours')::interval`, `EXPLAIN (ANALYZE, BUFFERS)`, `CREATE INDEX` and `ANALYZE` are compatible with PostgreSQL 17 by source inspection. The heredoc transaction creates the schema, tables and inserts atomically, then the count SELECT runs after COMMIT. The PowerShell alternative copies only the SQL transaction into a file; it must execute the subsequent count SELECT separately, otherwise the stated 1000/5000 verification is not performed. Each `docker exec ... psql -c` starts a separate connection. No actual parser or runtime verification was performed.
- **Expected synthetic outcomes:** `generate_series(1,1000)` inserts 1,000 distinct external IDs with identity patient IDs 1–1000 in a fresh cluster. The appointment expression `(g % 1000)+1` for g=1..5000 references only those IDs, creating 5,000 appointments, five per patient. The orphan LEFT JOIN should return 0. The negative INSERT references missing patient 999999, so a foreign-key violation (SQLSTATE 23503) is expected and no invalid row should persist. The actual SQLSTATE, exit status and unchanged count require runtime evidence.
- **Query plans:** before/after index comparisons are appropriately non-deterministic. The composite `(patient_id,scheduled_at)` index can support the equality filter plus ordering, but small-table planner choices and measured latency cannot be inferred from source. `EXPLAIN ANALYZE` executes the SELECT; it is bounded and read-only here.
- **Medium-severity safety gap (open):** `docker container inspect pg-dbre-ch19` is merely described as expected to fail; the sequence does not fail closed on name collision, assert an approved disposable Docker context, or record a container ID/mount provenance before later `docker exec` and `docker rm -f -v`. A user continuing after a failed `docker run` could operate on an existing container. Require an enforced absent-name check, context approval, unique ID capture and exact ID/mount recheck before execution and teardown. Do not delete any unknown container or volume. The `POSTGRES_PASSWORD` environment variable is visible in Docker metadata; sanitize evidence.
- **Low-severity test-harness improvement (open):** the expected foreign-key failure is demonstrated without an explicit assertion of both nonzero `psql` status and SQLSTATE 23503; capture sanitized stderr and test failure specificity, then re-query appointment count. Use `-v ON_ERROR_STOP=1` consistently. For PowerShell, include the post-COMMIT count query explicitly in the alternative instructions.
- **Prerequisites and scope:** no published host port; requires Linux Docker engine and local image pull. Readiness may need retries. The ADR is a manually completed artifact, not a runtime performance/reliability acceptance test; all sample SLO/RPO/RTO figures remain hypothetical and unapproved. No real patient data or paid services are required.
- **References:** the lesson-to-lab link and README/MASTER-TOC navigation paths are consistent with fetched track files. Official PostgreSQL 17 and Docker documentation URLs are provided; independent external HTTP checks, anchor resolution and systematic whole-track link validation remain pending. Do not infer reachability from plausible URLs.

**Result:** Chapter 19 source-level semantic review recorded; **18/20** chapter reviews. No confirmed blocking PostgreSQL 17 SQL syntax defect by inspection. Medium-severity Docker context/resource provenance and low-severity negative-test/PowerShell parity issues remain open. **Runtime validated: 0/20; independent review: pending; production certification: not established.**

**Runtime acceptance evidence required:** approved disposable Docker context, daemon/engine mode, absent-name preflight, image ID/digest, container ID and mounts, PostgreSQL 17 patch version, transaction exit code, actual 1000/5000 counts, orphan count 0, SQLSTATE 23503 with unchanged appointment count, actual before/after plans, completed ADR with unapproved targets marked, sanitized timestamps/transcripts, and verified cleanup or retention record.

**Next unreviewed milestone:** Chapter 20 — enterprise capstone; then systematic internal/external reference verification and isolated PostgreSQL 17 runtime validation.


## Chapter 20 — enterprise DBRE/SRE capstone

**Review date:** 2026-11-05. **Files inspected:** [lesson](../chapters/20-enterprise-postgresql-dbre-sre-capstone.md), [lab](../labs/chapter-20/README.md), track README, MASTER-TOC, STATUS-TRACKER, prior semantic evidence. **Method:** source inspection only; no Docker/psql execution.

- **PostgreSQL 17 syntax:** identity PKs, foreign key, CHECK, `generate_series`, `now() + (n || ' hours')::interval`, transaction ROLLBACK, `EXPLAIN (ANALYZE, BUFFERS)` on SELECT, `pg_stat_database`, `pg_stat_user_tables`, `pg_constraint` and `regnamespace` cast are plausible for PostgreSQL 17. No parser/runtime test occurred.
- **Expected results:** clean initialization yields 1,000 synthetic patients, 5,000 appointments (five per patient), one FK, and appointment 1 remains `scheduled` after rollback. Actual plans, timing, DB size and cumulative statistics are nondeterministic and must be captured rather than assumed. Heredoc requires a POSIX shell (Git Bash/WSL on Windows); PowerShell is not an equivalent interpreter for this snippet.
- **Confirmed safety weakness corrected:** previously, a failed `docker run` could be followed manually by `docker exec` against an existing named container; the lab now uses `set -eu` for fail-fast shell sequencing, displays Docker context and requires Linux engine mode. Cleanup is commented out by default and requires inspection of exact container ID, image and mounts before manual removal. These safeguards do **not** prove context ownership; human verification against the creation record remains mandatory. No destructive command was executed.
- **Other limitations:** `POSTGRES_PASSWORD` in Docker environment is inspectable and must be redacted; container health may require retries. A single unexposed container does not validate TLS, authentication hardening, HA, PITR, SLO or RPO/RTO. The design tabletop and rubric are educational review artifacts, not certification.
- **References:** chapter-to-lab link resolves by fetched source inspection. Official PostgreSQL 17, AWS, CloudNativePG and Docker URLs are present; systematic external HTTP and whole-track internal-link verification remain **pending**.

**Result:** Chapter 20 semantic source review recorded; **19/20** chapters have semantic review evidence in this report (Chapter 01 is not recorded here and must be checked against the original static audit before claiming 20/20). **Runtime: 0/20; independent review: pending; production certification: not established.**

**Runtime evidence required:** approved disposable Docker context, Docker/Linux engine version, image ID and digest, exact created container ID/mounts, PostgreSQL 17 patch version, sanitized command/exit-code transcript, observed 1000/5000 counts, rollback status, one FK, actual EXPLAIN and stats, ADR and risk register, and verified cleanup/retention evidence. Never infer executed status from this review.

**Next:** Reconcile Chapter 01 semantic coverage against original static audit, then systematically verify internal and external references and outstanding safety findings. Execute disposable PostgreSQL 17 labs only when runtime tooling is genuinely available.


## Chapter 01 — semantic evidence reconciliation (2026-11-05)

**Files reviewed:** [lesson](../chapters/01-postgresql-fundamentals-and-architecture.md), [lab](../labs/chapter-01/README.md), track README, MASTER-TOC, STATUS-TRACKER, and this existing review log. **Source-level review only; no PostgreSQL or Docker execution.**

- PostgreSQL 17 syntax reviewed: identity primary keys, foreign key, generated sample rows, `EXPLAIN (ANALYZE, BUFFERS)` on SELECT, explicit rollback/commit, catalog statistics, `pg_dump -Fc`, `createdb`, and `pg_restore`. No confirmed SQL syntax defect identified by inspection.
- Fresh `appdb` creates 100 customers and 50,000 orders. Each customer receives 500 orders under modulo distribution; `order_id=1` exists only under the fresh-database prerequisite. Rollback preserves `paid`; the later commit changes it to `shipped`. Logical restore should contain 50,000 orders, but no actual count has been observed.
- **Confirmed safety/test-harness weakness corrected:** previous Step 0 merely asked users to confirm names and volume availability; Step 1 could continue after a failed Docker run, and Step 9 presented immediately executable destructive cleanup. Added fail-closed name/volume/port checks, explicit Docker engine/context inspection, Docker-run failure stop, commented cleanup, and identity requirements. The Docker context is still subject to human confirmation; the script cannot prove resource ownership.
- **Confirmed test-harness weakness corrected:** previous restore invocation did not request `pg_restore --exit-on-error` or assert its exit status. Added both before claiming success. Further per-command error checks, independent restore target, and evidence automation remain open improvements.
- **Portability limitation:** the Chapter 01 preflight uses Windows PowerShell `Get-NetTCPConnection`; Linux/macOS Docker users need an equivalent local-port check and must not assume this PowerShell block works there. The lesson/lab internal relative links are consistent by source inspection; complete automated relative-link resolution and external HTTP verification remain pending.
- **Risk limitation:** `postgres:17` is a mutable tag and demo password is exposed to Docker metadata. Actual image digest, disposable engine ownership, sanitized logs and secret handling require runtime confirmation. The restore is a separate database within the same instance, not independent-node DR or PITR.

**Runtime evidence gate:** Capture approved local Docker context and endpoint, image digest, container and volume IDs/mounts, PostgreSQL version, fresh database identity, SQL transcript, 100/50000 row counts, both actual EXPLAIN plans, rollback/commit outputs, backup archive metadata, `pg_restore` exit status and restored count, plus explicit retention or cleanup proof. **Chapter 01 remains NOT EXECUTED; track runtime validation 0/20.** Independent review and production certification remain pending.

**Next:** systematically verify track-only relative links and external official documentation URLs; triage remaining Docker ownership and negative-test assertions before disposable PostgreSQL 17 runtime execution. The earlier `Remaining work` and `Next unreviewed milestone` notes in this append-only historical log describe past states and should not be interpreted as current progress.


## Reference verification checkpoint — 2026-11-05 (Chapters 02–04)

**Scope and method:** Read the current `main` README, MASTER-TOC, STATUS-TRACKER, prior semantic evidence, and all six Chapter 02–04 lesson/lab Markdown files. Extracted inline Markdown link destinations from these six files. This is a targeted reference checkpoint, **not** a whole-track reference or anchor audit.

- **Inline references inventoried:** 56 occurrences across six files (including repeated navigation links): Chapter 02 lesson 12, lab 7; Chapter 03 lesson 12, lab 6; Chapter 04 lesson 12, lab 7. 
- **Track-local relative destinations:** Navigation paths resolve lexically to the existing track structure (README, MASTER-TOC, STATUS-TRACKER, the chapter/lab pairs, and preceding lab prerequisites). These were inspected against the fetched file paths; this does not certify anchors or reference-style links.
- **Cross-curriculum references:** The Chapter 02 reference to `postgresql/chapters/031-b-tree-and-other-index-types-operational-tradeoffs.md` and Chapter 03 reference to `postgresql/chapters/016-mvcc-snapshots-and-tuple-visibility.md` were individually fetched from GitHub `main` and confirmed to exist. Neither file was modified.
- **External URLs:** HTTP retrieval succeeded for PostgreSQL 17 `ddl-identity-columns.html`, `mvcc-intro.html`, and `wal-reliability.html`; each returned the matching versioned documentation title. Other external destinations in Chapters 02–04 were inventoried but **not** HTTP-tested in this checkpoint.
- **Confirmed broken links:** None among the individually fetched destinations and HTTP-tested URLs. **Unverified:** other external URLs, anchors, reference-style links, and full-track coverage. No corrective edit justified from this sample.
- **Runtime evidence:** No PostgreSQL/Docker/psql commands executed; runtime status remains **0/20**. Independent review and production certification remain pending.

**Next:** Continue Chapters 05–19 reference resolution and systematically verify remaining external URLs and anchors; record only confirmed failures and remediation. Preserve all track-only edit boundaries.


## Documentation-reference audit checkpoint — 2026-11-05 — Chapters 05–08

**Scope:** Eight files: chapter lessons and lab READMEs for Chapters 05, 06, 07 and 08. This is a reference-inventory and targeted HTTP verification checkpoint, **not** completion of the whole-track link audit or PostgreSQL runtime execution.

- Parsed **99 inline Markdown link occurrences** (Chapter 05: 14 lesson + 9 lab; Chapter 06: 14 + 8; Chapter 07: 23 + 9; Chapter 08: 15 + 7). These counts include repeated targets, and exclude links that may be encoded as reference-style definitions, autolinks or raw HTML.
- Track-local navigation targets match the known track inventory: README, MASTER-TOC, STATUS-TRACKER, lesson/lab counterparts and Chapter 08 `cluster-example.yaml`. This is a **path-inventory comparison**, not a fresh filesystem resolution of every target or an anchor check.
- Targeted HTTP retrieval succeeded for PostgreSQL 17 multicolumn index documentation (`https://www.postgresql.org/docs/17/indexes-multicolumn.html`), AWS RDS `USER_PerfInsights.Overview.html`, and CloudNativePG development bootstrap documentation (`https://cloudnative-pg.io/docs/devel/bootstrap/`). Other external links in these eight files have **not** been individually HTTP-tested.
- **Documentation maintenance finding (low):** The AWS URL now displays an **Overview of Database Insights on Amazon RDS** rather than the older Performance Insights overview. Review Chapter 07 terminology against the current AWS monitoring product and pricing/retention documentation; URL reachability alone does not establish that the original lesson wording remains current.
- **Version-pinning finding (low):** Chapter 08 links to CloudNativePG `/docs/devel/bootstrap/`. This URL resolves, but explicitly serves a moving development-version manual. For a reproducible operator lab, choose a supported, pinned CloudNativePG release and verify the YAML against that release before any Kubernetes execution. Do not silently replace the URL until the lesson's operator version is established.
- No broken URL is confirmed in the three targeted HTTP checks. No provider, Kubernetes, Docker or PostgreSQL runtime tests were executed.

**Remaining:** Check every remaining URL in Chapters 05–08; scan Chapters 09–20 and all supporting files for inline, reference-style, HTML and anchor links; validate case-sensitive paths and redirects; remediate confirmed errors without editing the separate 100-chapter curriculum. Runtime status remains **0/20**, independent review pending, production certification not established.


## Documentation-reference audit checkpoint — 2026-11-05 — Chapters 09–12

**Scope:** Fetched current `main` README, MASTER-TOC, STATUS-TRACKER, existing semantic-review evidence and eight chapter/lab files (Chapters 09–12). This is a **partial inline-link inventory and targeted external verification**, not a full anchor/reference-style audit. No lessons were changed.

- **82 inline Markdown link occurrences inventoried:** Chapter 09 lesson 14 + lab 10; Chapter 10 lesson 12 + lab 7; Chapter 11 lesson 13 + lab 6; Chapter 12 lesson 13 + lab 7. Repeated navigation and duplicate URLs count separately. Regex extraction does not cover reference definitions, autolinks, raw HTML or links embedded in unusual Markdown syntax.
- **Track-local destinations observed:** README, MASTER-TOC, STATUS-TRACKER, lesson/lab counterpart paths and Chapter 09's Chapter 01 lab prerequisite. Their relative path forms match the known track inventory by inspection; full filesystem/anchor resolution is still outstanding.
- **External references inventoried:** PostgreSQL 17 replication, base backup, WAL recovery, monitoring, and roles; AWS RDS Multi-AZ; CloudNativePG pinned 1.28 documentation; Kubernetes persistent volumes; postgres_exporter, Prometheus, and Grafana. The PostgreSQL 17 WAL configuration page (`https://www.postgresql.org/docs/17/runtime-config-wal.html`) was retrieved successfully and its Recovery Target section was visible in the page TOC. The exact fragment `#RUNTIME-CONFIG-WAL-RECOVERY-TARGET` was **not** independently browser-resolved. Other external URLs remain unverified by HTTP in this checkpoint.
- **No confirmed broken reference** in the individually fetched files and targeted page. Do not infer all 82 links are valid; links with anchors, cross-repository targets and all other HTTP URLs still require systematic checking.
- **Safety/validation boundaries:** No Docker, PostgreSQL, cloud, failover or Kubernetes runtime operations executed. All 20 semantic reviews remain recorded; **runtime-validated 0/20**, independent review pending, production certification not established.

**Next:** Continue the reference inventory with Chapters 13–16, then 17–20 and supporting scripts/YAML; perform exhaustive external reachability, case-sensitive path, reference-style and anchor resolution before closing this gate. Afterwards triage previously recorded Docker ownership and negative-test assertion findings before any disposable PostgreSQL 17 runtime testing.


## Documentation-reference audit checkpoint — 2026-11-05 — Chapters 13–16

**Scope:** Re-read current `main` README, MASTER-TOC, STATUS-TRACKER and this semantic evidence log; fetched eight Chapter 13–16 lesson/lab Markdown files. This checkpoint inventories inline links and highlights safety follow-ups; it is **not** full HTTP, fragment, or runtime validation.

- **78 inline Markdown link occurrences:** Chapter 13 lesson 12 + lab 7; Chapter 14 lesson 14 + lab 9; Chapter 15 lesson 11 + lab 10; Chapter 16 lesson 10 + lab 5. Counts include repeated navigation destinations. No reference-style link definitions were detected by a line-anchored definition scan in these eight files; raw HTML, autolinks and anchors are not exhaustively parsed.
- **Local targets observed:** lesson/lab counterparts, track README, MASTER-TOC, STATUS-TRACKER, and Chapter 15 `inventory.sql` and `drift.sql`. Relative paths were compared lexically with the established track inventory, **not** all fetched individually. No confirmed broken local link in this sample.
- **External targets inventoried:** PostgreSQL 17 vacuuming, monitoring, locking, security and catalog documentation; AWS CLI RDS instance listing; CloudNativePG; Kubernetes RBAC; Docker Hub Postgres. **None were HTTP-retrieved in this checkpoint.** Thus no claim of verified external reachability or fragments is made.
- **Safety follow-up (medium, not a confirmed defect):** Chapter 15 lab contains `docker rm -f pg-fleet-ch15` and Chapter 16 lab contains `docker rm -f -v pg-dbre-ch16`. Their surrounding text warns about destructive cleanup, but runtime execution must enforce container identity/context/mount ownership and verify disposable resources before invoking these commands. Chapter 13 and 14 use `docker rm -v` with similar ownership requirements. Do not execute these cleanup steps against unverified containers.
- **No SQL, Docker, psql, Kubernetes or cloud execution** was performed. All 20 semantic reviews remain recorded; **runtime-validated 0/20**. Independent review and production certification are still outstanding.

**Next:** Inventory Chapters 17–20 and supporting files; complete exhaustive HTTP, reference-style, case-sensitive path and anchor checks for all chapters. Then remediate confirmed safety/test-harness defects before isolated PostgreSQL 17 runtime testing.


## Documentation-reference audit checkpoint — 2026-11-05 — Chapters 17–20

**Scope and method:** Re-read track README, MASTER-TOC, STATUS-TRACKER and the existing semantic audit; fetched the four Chapter 17–20 lessons and four lab READMEs from GitHub main. Extracted inline Markdown link destinations and line-anchored reference definitions. This is a **source inventory**, not an exhaustive HTTP/anchor audit or runtime validation.

- **54 inline Markdown link occurrences across eight files:** Chapter 17 lesson 8 + lab 4; Chapter 18 lesson 8 + lab 5; Chapter 19 lesson 8 + lab 5; Chapter 20 lesson 10 + lab 6. The lesson-to-lab targets for all four chapters and Chapter 20 lab-to-lesson target match the known repository paths. No reference-style definitions were found by a line-anchored scan in these eight files. Autolinks, HTML and fragment resolution still need comprehensive checking.
- **External destinations inventoried but not HTTP-verified in this checkpoint:** PostgreSQL 17 upgrade, ALTER TABLE, size functions, statistics, EXPLAIN, DDL, security, backup and HA manuals; AWS RDS upgrade docs; CloudNativePG; Docker documentation. URL presence does **not** imply reachability or current version correctness.
- **Safety follow-up:** Chapter 17 uses `docker rm -v pg-dbre-ch17`; Chapter 18 uses `docker rm -v pg-dbre-ch18`; Chapter 19 uses `docker rm -f -v pg-dbre-ch19`; Chapter 20 cleanup is commented out. Confirm Docker context, resource ownership, exact container ID, mounts and disposable nature before executing any cleanup. This is an outstanding safety gate, not evidence that a destructive command was executed.
- **No confirmed broken link** in the lexical path sample. **Not verified:** all external URLs, anchors, reference-style/HTML/autolinks in the rest of the track, redirects and case-sensitive resolution. Previous Chapters 02–16 checkpoint counts are inventories, not exhaustive pass results. The whole-track reference gate therefore remains **open**.
- **Execution:** No Docker, PostgreSQL, Kubernetes or cloud workloads were run; **0/20 labs runtime validated**. Independent review and production certification remain pending.

**Next:** Audit supporting files and complete exhaustive internal path, reference-style, fragment and HTTP checks across the entire track; resolve confirmed errors and safety/test-harness weaknesses before isolated PostgreSQL 17 runtime tests. Do not modify the separate 100-chapter curriculum.


## 2026-11-06 — Relative-link resolution, Chapters 14–20

**Scope:** The seven chapter lessons (14–20) and their seven matching lab READMEs on GitHub `main`. Reviewed against the complete, non-truncated recursive repository tree (73 entries within this independent track). This is **static link-target resolution only**, not HTTP verification, anchor checking, runtime execution or independent approval.

- **14 Markdown files inspected** (7 lessons and 7 lab READMEs).
- **21 ordinary inline relative Markdown links** checked by normalizing each destination relative to its source file and resolving it against the GitHub repository tree. **0 missing file targets found.** This includes any cross-track destinations as read-only checks; no other curriculum files were modified.
- **51 distinct external URLs inventoried** in this batch. HTTP response status, redirects, fragment identifiers, and PostgreSQL 18 semantic correctness are **not verified**. Reference-style links, raw HTML links and autolinks were **not exhaustively parsed** in this batch.
- Earlier run notes reported 18 Markdown files checked, but without a committed, reproducible per-file result. This batch is a separate explicitly bounded check, **not a claim that all track links are validated**.

**Next:** Complete remaining unverified link forms and external endpoint/anchor checks across the entire track; then address confirmed safety findings and begin version-specific PostgreSQL 18 lab migration. The official PostgreSQL 18 documentation remains authoritative; historical PostgreSQL 17 audit sections above are preserved. **PostgreSQL 18 runtime acceptance: 0/20.** No Docker, psql, cloud, Kubernetes, destructive operations, or independent certification were performed in this check.


## PostgreSQL 18 external-reference checkpoint — 2026-11-06 — Chapter 01 lesson

**Scope and method:** Re-read the current track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline policy and historical semantic evidence. Fetched Chapter 01 lesson and lab from GitHub main. Individually retrieved all six distinct external links in the Chapter 01 lesson against the official PostgreSQL 18 documentation, and checked the returned page titles and version labels. This is a bounded HTTP/page-identity check, not a whole-track anchor or semantic certification.

| Chapter 01 lesson URL | Observed PostgreSQL 18 page | Result |
|---|---|---|
| https://www.postgresql.org/docs/18/tutorial.html | Part I — Tutorial | Retrieved; correct version |
| https://www.postgresql.org/docs/18/mvcc.html | Chapter 13 — Concurrency Control | Retrieved; correct version |
| https://www.postgresql.org/docs/18/wal.html | Chapter 28 — Reliability and the Write-Ahead Log | Retrieved; correct version |
| https://www.postgresql.org/docs/18/monitoring-stats.html | 27.2 — The Cumulative Statistics System | Retrieved; correct version |
| https://www.postgresql.org/docs/18/app-pgdump.html | pg_dump | Retrieved; correct version |
| https://www.postgresql.org/docs/18/app-pgrestore.html | pg_restore | Retrieved; correct version |

**Result:** Six of six checked Chapter 01 lesson documentation endpoints resolved to the expected PostgreSQL 18 manual pages; no confirmed broken endpoint in this subset. No URL fragments were present in this six-URL subset. Other track links, redirect chains, reference-style definitions, HTML/autolinks and external anchors remain outside this checkpoint. HTTP retrieval alone does not establish SQL/runtime correctness. The Chapter 01 lab still explicitly uses `postgres:17` and `pg_fleet_data:/var/lib/postgresql/data`; do not change its image tag without a separate PostgreSQL 18 volume and identity/mount migration. No Docker/psql execution, cloud charges, or cleanup operations occurred. **PostgreSQL 18 runtime validated: 0/20; independent review and production certification pending.**

**Next:** Continue PostgreSQL 18 external documentation endpoint/fragment checks from Chapter 02 onward; address outstanding container ownership safeguards before a separately evidenced, isolated PostgreSQL 18 Chapter 01 migration.


## PostgreSQL 18 external-reference checkpoint — 2026-11-06 — Chapter 02 lesson and lab

**Scope and method:** Re-read current main README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, and historical semantic evidence; fetched Chapter 02 lesson and lab. Individually retrieved the eight distinct PostgreSQL 18 manual endpoints referenced by these two files and checked version and page topic. This is a bounded HTTP/page-identity audit, not comprehensive anchor or runtime validation.

| Source | PostgreSQL 18 documentation page | HTTP/page identity |
|---|---|---|
| Lesson | `manage-ag-createdb.html` — Creating a Database | Retrieved; version/topic correct |
| Lesson | `ddl-schemas.html` — Schemas | Retrieved; version/topic correct |
| Lesson and lab | `ddl-constraints.html` — Constraints | Retrieved; version/topic correct |
| Lesson | `ddl-identity-columns.html` — Identity Columns | Retrieved; version/topic correct |
| Lesson | `datatype.html` — Data Types | Retrieved; version/topic correct |
| Lab | `ddl.html` — Data Definition | Retrieved; version/topic correct |
| Lab | `information-schema.html` — Information Schema | Retrieved; version/topic correct |
| Lab | `app-psql.html` — psql | Retrieved; version/topic correct |

**Result:** 8/8 distinct PostgreSQL 18 manual URLs resolved to the intended page/topic; none has a fragment in this subset. Chapter 02 lesson also links to a separate curriculum index chapter; this cross-track link was not HTTP-verified here and no file outside this independent track was edited. Remaining HTML/autolinks, reference-style links, all other track external endpoints and anchor resolution remain pending.

**Actionable safety finding (medium; existing issue, now pinpointed):** Chapter 02 lab's PowerShell prerequisite executes a version/role query but checks only `$LASTEXITCODE`, then asks the learner to visually inspect `17|f`. A successful SQL exit code alone does not enforce the required major-version and primary-role identity. Before any unattended execution, capture the result and assert exact parsed major and `pg_is_in_recovery() = false`; keep the independently recorded Docker context/full ID, image, mount and label checks. Do not reuse this PostgreSQL 17 mount for 18. This checkpoint records the issue rather than changing a historical 17-targeted lab during the pending version migration.

**Execution and gates:** No Docker, psql, AWS, Kubernetes or destructive operations executed. Existing Chapter 02 lab remains PostgreSQL 17-targeted; PostgreSQL 18 runtime validation **0/20**, independent review and production certification pending. Next: Chapter 03 external-reference checks, then address safety assertions and migrate Chapter 01 to a fresh PostgreSQL 18 volume under the baseline policy.


## 2026-11-06 — Chapter 03 lab source-integrity repair

**Confirmed high-priority finding:** On current `main`, `labs/chapter-03/README.md` contained an interrupted PowerShell `if` expression in the opening preflight, an unclosed fenced code block, and a duplicated copy of lab sections appended after the official documentation links. This made the safety preflight non-executable as written and obscured the intended two-session sequence. The issue was confirmed by fetching the complete source; it is not a runtime observation.

**Scoped remediation:** Restored the existing Docker context, full container ID, owner label, image, mount, readiness and server-role checks into a single complete PowerShell fence; made the PostgreSQL 17 primary-version result a fail-closed string assertion (`17|f`); retained the original Chapter 03 SQL lab sequence and expected results once; removed the malformed duplicate. The corrected lab was fetched from `main` after commit `c5978034870bfb60fd9145820093ee052c393140`; the repaired file has one Chapter 03 setup sequence and balanced Markdown fences. This is a **static source-integrity fix**, not PowerShell parsing or PostgreSQL execution evidence.

**Version boundary:** The Chapter 03 lab remains deliberately `postgres:17` with the 17 data mount; PostgreSQL 18 is the documentation baseline, not a runtime certification. No Docker/psql test, external URL endpoint check, or destructive cleanup was executed. **Runtime validated: 0/20.** Independent review and production certification remain pending.

**Next:** Verify Chapter 03 PostgreSQL 18 external documentation endpoints/anchors and continue the outstanding track-wide reference audit; then migrate labs to isolated PostgreSQL 18 containers using fresh volumes mounted at `/var/lib/postgresql`, never reusing the 17 volume.


## 2026-11-06 — Chapter 03 PostgreSQL 18 documentation endpoint checkpoint

**Scope:** Inspected the current `main` Chapter 03 lesson and lab after the earlier source-integrity repair. Enumerated all PostgreSQL manual links in those two files and retrieved each unique endpoint from the official PostgreSQL 18 manual. This is a documentation endpoint/page-topic check only; it is not an executable SQL, PowerShell, runtime, full-fragment, or whole-track link certification.

| PostgreSQL 18 URL suffix | Source | Retrieved page/topic | Result |
|---|---|---|---|
| `transaction-iso.html` | Lesson + lab | 13.2 Transaction Isolation | Pass: endpoint and topic |
| `mvcc.html` | Lesson | Chapter 13 Concurrency Control | Pass: endpoint and topic |
| `explicit-locking.html` | Lesson | 13.3 Explicit Locking | Pass: endpoint and topic |
| `monitoring-stats.html` | Lesson + lab | 27.2 Cumulative Statistics System | Pass: endpoint and topic |
| `sql-rollback-to.html` | Lesson | ROLLBACK TO SAVEPOINT | Pass: endpoint and topic |
| `mvcc-intro.html` | Lab | 13.1 Introduction | Pass: endpoint and topic |
| `sql-savepoint.html` | Lab | SAVEPOINT | Pass: endpoint and topic |

**Result:** 7/7 distinct official PostgreSQL 18 URLs retrieved with matching version and subject; 9 URL occurrences across lesson and lab. No fragment identifiers in this subset. No broken PostgreSQL manual endpoint confirmed here. Cross-curriculum relative link and unexamined HTML/reference-style links are not covered by this endpoint checkpoint.

**Limitations and gates:** Chapter 03's lab still targets PostgreSQL 17; the earlier static repair does not prove PowerShell syntax execution or transaction ordering on a running database. No Docker, psql, cloud, failover, or destructive cleanup operation was executed. PostgreSQL 18 runtime-validated labs remain **0/20**. Independent review and production certification remain pending.

**Next:** Continue official PostgreSQL 18 documentation endpoint/anchor verification with Chapter 04, then reconcile known container ownership/identity checks and safely migrate individual labs using fresh isolated PostgreSQL 18 volumes mounted at `/var/lib/postgresql` (not the PostgreSQL 17 data mount).


## 2026-11-06 — Chapter 04 lab source-integrity repair

**Confirmed high-priority defect:** The Chapter 04 lab README had a truncated PowerShell major-version preflight expression and unclosed code fence before Step 1. A second copy of the lab was appended after its official references. The malformed preflight was not safely executable as written.

**Scoped fix:** Restored the PostgreSQL 17 version check with a fail-closed `^17[0-9]{4}$` assertion and an explicit `pg_is_in_recovery() = false` check, closed the PowerShell fence, retained one copy of the existing Step 1–8 SQL sequence, and removed the duplicated tail (~9.7 KB). Fetched the repaired file from `main`: exactly one Step 1 heading and 28 Markdown fence delimiters (14 pairs). Commit: `95a21cbc185dd9065e89cac8734fcb51ca947db1`.

**Limits:** Static source repair only; no PowerShell parser, Docker, psql, SQL or destructive test executed. The lab remains PostgreSQL 17-targeted, with legacy volume layout, and must not be represented as PostgreSQL 18 runtime-validated. PostgreSQL 18 runtime evidence remains **0/20**; independent review and production certification pending. The separate 100-chapter curriculum was not changed.

**Next:** Check Chapter 04's six distinct official PostgreSQL 18 documentation endpoints and any anchors, then continue the track-wide reference audit. Address the recorded container identity/ownership guardrails before migrating Chapter 01 to a fresh isolated PostgreSQL 18 volume mounted at `/var/lib/postgresql`.


## 2026-11-06 — Chapter 04 PostgreSQL 18 official-reference endpoint checkpoint

**Scope and method:** Re-read track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline policy, prior static/semantic audit progress, and the current Chapter 04 lesson and repaired lab on `main`. Extracted version-pinned PostgreSQL documentation URLs from both Chapter 04 sources and retrieved each distinct URL directly from the official PostgreSQL 18 manual. This is an endpoint/version/topic check, not a fragment, command-execution, or whole-track certification.

| PostgreSQL 18 URL suffix | Official page topic | Endpoint/topic result |
|---|---|---|
| `wal-intro.html` | 28.3 Write-Ahead Logging (WAL) | Pass |
| `wal-configuration.html` | 28.5 WAL Configuration | Pass |
| `monitoring-stats.html` | 27.2 The Cumulative Statistics System | Pass |
| `continuous-archiving.html` | 25.3 Continuous Archiving and PITR | Pass |
| `wal-reliability.html` | 28.1 Reliability | Pass |
| `functions-admin.html` | 9.28 System Administration Functions | Pass |

**Result:** 6/6 distinct official PostgreSQL 18 endpoints returned PostgreSQL 18 pages with matching topics. The lesson contains six occurrences and the lab five, for eleven occurrences. No fragment anchors were present in these extracted official-manual URLs. This does not establish that SQL examples or expected values are correct under PostgreSQL 18.

**Outstanding:** Verify Chapter 05 onward and remaining external/reference-style links, redirects, raw HTML, and anchors; address recorded ownership/cleanup and fail-closed identity checks before unattended execution. Chapter 04's repaired lab remains PostgreSQL 17-targeted, not migrated. No Docker, PowerShell, psql, destructive, cloud or Kubernetes tests executed. PostgreSQL 18 runtime-validated: **0/20**. Independent review and production certification pending. Historical PostgreSQL 17 evidence retained unchanged.

**Next:** Chapter 05 official PostgreSQL 18 documentation endpoint audit, then continue the reference gate before safe PG18 lab migration using fresh volumes mounted at `/var/lib/postgresql` and verified `PGDATA=/var/lib/postgresql/18/docker`.


## 2026-11-06 — Chapter 05 PostgreSQL 18 reference audit (partial) and duplicate-section finding

**Scope:** Re-read track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, and the prior semantic-review report. Inspected Chapter 05 lesson and lab on main. Extracted 10 distinct official PostgreSQL 18 documentation URLs across the two files (8 lesson, 7 lab; 5 shared).

**Verified official endpoints and topics (5/10):** `using-explain.html` (Using EXPLAIN), `indexes-multicolumn.html` (Multicolumn Indexes, including PostgreSQL 18 skip scan), `indexes-partial.html` (Partial Indexes), `indexes-examine.html` (Examining Index Usage), and `sql-createindex.html` (CREATE INDEX). All five returned PostgreSQL 18 manual pages matching the referenced topic. No URL fragments in this verified subset. **Not yet verified:** `indexes.html`, `indexes-index-only-scans.html`, `sql-analyze.html`, `sql-explain.html`, `indexes-types.html`. No claim is made for their endpoint/anchor status.

**Confirmed documentation mismatch fixed:** Chapter 05 lab labeled its official references “PostgreSQL 17” even though the URLs point to PostgreSQL 18. Both occurrences of that heading now explicitly state the PostgreSQL 18 documentation baseline while preserving the PostgreSQL 17 lab runtime status. Verified the published file after the commits `bf8b41cdaf094b50529b515624051bb91411aa0a` and `9af926c5dba2a7f9c971e3b77a3b75f4164f7dd4`.

**New actionable source-integrity finding:** The Chapter 05 lab has **two copies of the official-reference heading**, indicating a possible duplicated tail. Do not delete the second section blindly: inspect and diff all repeated lab sections, preserve any unique steps or expected results, and repair in a separate scoped commit with a fence/step-count check. Review PostgreSQL 18 planner skip-scan behavior before asserting leftmost-column rules or deterministic EXPLAIN plans. These are source-level findings, not executed tests.

**Status and limitations:** Historical PostgreSQL 17 semantic reviews remain recorded; this pass checked only five official endpoints and did not execute Docker, PowerShell, psql, SQL, destructive, cloud or Kubernetes commands. PostgreSQL 18 runtime-validated remains **0/20**; independent review and production certification remain pending. The separate 100-chapter curriculum was not modified.

**Next:** Inspect Chapter 05 duplicated sections and reconcile without losing unique lab content; finish its five outstanding official endpoints and other reference/anchor checks; then continue Chapter 06 and the remaining reference gate before isolated PostgreSQL 18 lab migration using new version-appropriate volumes.


## 2026-11-06 — Chapter 05 duplicate-tail repair and PostgreSQL 18 endpoint completion

**Confirmed defect and scoped repair:** The Chapter 05 lab had a truncated PowerShell Docker-name filter in Step 0, an unclosed PowerShell fence, and a duplicated Step 1–9 tail appended after the first official-reference section. Compared both sequences: the duplicate repeated the same SQL workload, expected counts, EXPLAIN, index, acceptance and troubleshooting sections; its extra preflight lines were restored into the original Step 0 rather than discarded. Commit `ed870188e3d29e6468a92fb439bd3a2e71095cb0` repaired the filter and fence, restored container label/image/volume/ID checks, added a fail-closed PostgreSQL 17 primary assertion, and removed the duplicate. Post-commit GitHub fetch matched the replacement content: 25,248 → 14,551 characters; exactly one Step 0–9 sequence, one reference section, and 26 balanced fence delimiters (13 pairs). This is a **static integrity check**, not PowerShell parsing or database execution. A human must still compare the recorded Chapter 01 full container ID and Docker endpoint before running any command.

**PostgreSQL 18 reference completion:** The remaining five Chapter 05 official documentation endpoints were retrieved from the PostgreSQL 18 manual and matched their subjects: `indexes.html` (Chapter 11 Indexes), `indexes-index-only-scans.html` (Index-Only Scans and Covering Indexes), `sql-analyze.html` (ANALYZE), `sql-explain.html` (EXPLAIN), and `indexes-types.html` (Index Types). Combined with the five endpoints previously verified, Chapter 05 has **10/10 distinct PostgreSQL 18 manual endpoints checked for page/version/topic**. This does not establish anchor, redirect, non-PostgreSQL reference, SQL execution, or planner-result verification. PostgreSQL 18 skip-scan and plan-selection behavior still require lab-specific reconciliation.

**Gates:** Chapter 05 remains intentionally PostgreSQL 17-targeted with the legacy volume mount; do not substitute `postgres:18` without a fresh volume at `/var/lib/postgresql` and verified `PGDATA=/var/lib/postgresql/18/docker`. No Docker, psql, PowerShell, cloud, or destructive test was executed. PostgreSQL 18 runtime-validated labs: **0/20**. Independent review and production certification: pending. The separate 100-chapter curriculum was not modified.

**Next:** Resume official PostgreSQL 18 reference and source-integrity audit at Chapter 06; complete remaining track-wide links, anchors and safeguards before isolated PostgreSQL 18 runtime migration.


## 2026-11-06 — Chapter 06 lab source-integrity checkpoint

**Scope:** Re-read the track README, master TOC, status tracker, PostgreSQL 18 baseline policy and existing semantic-review evidence, then inspected Chapter 06 lesson and lab on GitHub main.

**Confirmed high-priority defect:** The Chapter 06 lab Step 1 PowerShell preflight was truncated inside the 64-character container-ID regex, leaving an unterminated fence and an embedded duplicate of Steps 2–11 after the first reference section. This made the safety checks unreliable and could expose learners to an unsafe stop/start sequence.

**Scoped repair:** Commit `c73435ac81a4183b7e397fd863ab8ede5e191a97` restores the full container-ID assertion, checks image, track/lab labels and named volume at the PostgreSQL 17 mount target, and closes the PowerShell fence. Preserved the original full Step 2–11 sequence, including the optional restart identity checks, and removed the duplicated tail. GitHub re-fetch matched the replacement file exactly. Static checks: 22,201 → 13,790 characters; one ordered Step 0–11 sequence; 26 balanced tilde-fence delimiters. This is **source-integrity review only**; PowerShell parsing and SQL execution were not performed.

**Remaining Chapter 06 findings:** The lesson's header still says “Reference version: PostgreSQL 17” despite the PostgreSQL 18 documentation baseline; distinguish documentation baseline from legacy lab runtime in a separate careful revision. The Step 1 container preflight checks only the captured container metadata, not a saved independent Docker daemon endpoint; the optional restart must remain blocked unless identity and context are independently established. Review all eight lesson and six lab PostgreSQL 18 manual URLs for endpoint, topic and anchor correctness, then continue track-wide external reference checks. Check actual SQL and PowerShell output in an isolated disposable environment before claiming runtime validation.

**Safety/status:** The lab remains `postgres:17` with `/var/lib/postgresql/data` and has not been migrated to PostgreSQL 18. A future migration requires a new volume mounted at `/var/lib/postgresql`, verified `PGDATA=/var/lib/postgresql/18/docker`, exact version/image identity and cleanup proof. No Docker, PowerShell, psql, destructive, cloud or Kubernetes operations were executed. PostgreSQL 18 runtime validation: **0/20**. Independent review and production certification remain pending. The separate 100-chapter curriculum was not changed.

**Next:** Verify Chapter 06 PostgreSQL 18 documentation endpoints and resolve remaining identity/cleanup safeguards, then resume Chapter 07 without repeating completed chapters.


## 2026-11-07 — Chapter 06 PostgreSQL 18 documentation endpoint checkpoint

**Scope:** Re-read the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline policy, prior semantic-review evidence, and Chapter 06 lesson/lab on main. Retrieved the eight distinct official PostgreSQL 18 manual URLs in Chapter 06 (eight lesson references, six lab references; six shared). Each resolved to a PostgreSQL 18 page with the intended topic: `runtime.html` (server setup), `server-start.html` (startup), `runtime-config-file-locations.html` (file locations), `storage-file-layout.html` (database file layout), `auth-pg-hba-conf.html` (HBA), `app-pg-ctl.html` (pg_ctl), `view-pg-settings.html` (pg_settings), and `monitoring-stats.html` (statistics). **Endpoint/version/topic: 8/8 pass.** These direct reference URLs have no fragments. No exhaustive inline-anchor, raw HTML, redirect or non-manual reference audit is implied.

**Confirmed metadata fix:** Chapter 06 lesson previously labeled its reference version PostgreSQL 17 despite linking to the PostgreSQL 18 manual. Updated only its header to distinguish **documentation baseline PostgreSQL 18** from **legacy lab runtime PostgreSQL 17 (not PG18-validated)**. Commit `67a3789135912151123c4e764c59f1d76424abc0`; fetched the changed file from main and verified exact content.

**Actionable safety finding (not yet fixed):** The Chapter 06 optional stop/start guard checks the saved Docker context *name*, container ID, image tag, labels and mount, but does not independently pin and compare the Docker daemon endpoint or immutable image digest. Require independent creation-time daemon/endpoint evidence and digest checks before any unattended disruptive action. Some read-only and SQL commands still use the mutable container name rather than the captured ID. Do not execute optional stop/start until ownership is independently established. No Docker, PowerShell, psql, SQL, destructive, AWS or Kubernetes exercise was executed.

**Gates:** Chapter 06 remains postgres:17 using /var/lib/postgresql/data; PostgreSQL 18 migration must use a fresh volume at /var/lib/postgresql with verified PGDATA=/var/lib/postgresql/18/docker. PG18 runtime-validated **0/20**; independent review and production certification pending. Historical PG17 audit retained. Separate 100-chapter curriculum unchanged.

**Next:** Chapter 07 source-integrity and official-reference audit, then complete outstanding track-wide anchors/external links and safety controls before isolated PG18 runtime migration.


## 2026-11-07 — Chapter 07 source-integrity repair

**Scope:** Re-read track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE and existing semantic audit, then compared Chapter 07 lesson and lab. The lab had a truncated PowerShell Docker name filter in Step 0, an unclosed code fence and two duplicate tails of Steps 1–11/reference material. The three Step 1–11 bodies matched exactly; preserved the first full sequence and reference block. Commit `cb224444ef3666731251a98fa5a4e444ed179c55` restored the preflight and removed duplicate tails. GitHub main re-fetch confirmed 38,391 → 14,580 characters, 26 balanced Markdown fences and one Step 1 heading.

**Safety:** Preflight now asserts unique container, full ID shape, expected label/image/volume, PostgreSQL 17 major version and writable primary. Human comparison with independently retained Chapter 01 Docker daemon endpoint, container ID and volume remains mandatory; it is not programmatically enforced. The legacy PostgreSQL 17 mount remains `/var/lib/postgresql/data`. No Docker, psql, PowerShell, AWS or destructive operations executed. PostgreSQL 18 runtime-validated: **0/20**. No independent review or production certification.

**Outstanding:** Verify Chapter 07 PostgreSQL 18 documentation endpoints and AWS external references, validate negative-test sequencing and `pg_dump`/`pg_restore` outputs in an isolated runtime, and reconcile future PostgreSQL 18 migration using a new volume at `/var/lib/postgresql` with verified `PGDATA=/var/lib/postgresql/18/docker`. Do not modify the separate 100-chapter curriculum.


## 2026-11-07 — Chapter 07 documentation and restore-safety checkpoint

**Scope:** Inspected the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline policy, prior audit, and Chapter 07 lesson/lab on main. Inspected the Chapter 07 lesson and lab reference inventory: three distinct PostgreSQL 18 manual endpoints (`app-pgdump.html`, `app-pgrestore.html`, `view-pg-settings.html`) and AWS RDS documentation URLs. Independently opened all three PostgreSQL 18 manual endpoints and the AWS PITR and Database Insights overview endpoints; all five resolved and matched their intended subjects. **Verified: 3/3 distinct PostgreSQL manual endpoints and 2 AWS endpoints.** The other AWS links, redirect behavior, fragments, raw HTML and internal anchors are **not yet exhaustively checked**; do not treat the entire Chapter 07 link inventory as passed.

**Metadata correction:** The lesson header formerly described PostgreSQL 17 as the local reference without explicitly distinguishing the new documentation baseline. Commit `42fc7b7d256fb67171c792f2aca1a109986574f1` now labels PostgreSQL 18 as the documentation baseline and PostgreSQL 17 as the legacy, not-PG18-validated local lab runtime. Re-fetched from GitHub main to verify.

**Actionable static finding (pending fix):** The Chapter 07 PowerShell backup/restore sequence does not assert `$LASTEXITCODE` after `pg_dump`, `createdb`, `pg_restore` and the restored row-count query. A failed dump or restore could be missed if learners continue; add fail-closed exit checks and assert the restored count equals exactly three before accepting evidence. Use `pg_restore --exit-on-error` (and preferably `--single-transaction` for this isolated archive) after checking command compatibility. Do not automatically overwrite an existing restore database. Record expected negative-test error and verify it is a permissions error rather than another failure. PostgreSQL 18 documentation confirms custom-format dumps use pg_restore and that pg_restore's default can continue after SQL errors unless `--exit-on-error` is specified.

**Safety/status:** The lab remains `postgres:17` with `/var/lib/postgresql/data`. Docker daemon endpoint and full container identity still require independent comparison with Chapter 01 creation evidence. No Docker, PowerShell, psql, AWS, destructive or cloud commands were executed; the five endpoint checks were documentation retrieval only. PostgreSQL 18 runtime validation **0/20**. Independent review and production certification pending. Do not touch the separate 100-chapter curriculum.

**Next:** Repair Chapter 07 backup/restore fail-closed assertions in a scoped commit, finish its remaining AWS links/internal anchors, then proceed to Chapter 08 source integrity and documentation references.


## 2026-11-07 — Chapter 07 fail-closed backup/restore repair

**Scope and prior state:** Inspected the track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, prior semantic audit and Chapter 07 lab on GitHub main. Resumed the recorded outstanding Chapter 07 restore-safety finding; did not repeat earlier chapter reviews.

**Confirmed repair:** Commit `709e9e7e2d553a274eeb2808dc45e65e48c2002d` replaces the permissive five-command dump/restore example with explicit exit-status checks, an exact source count of three, preexisting restore-database and archive collision checks, nonempty archive assertion, `pg_restore --exit-on-error --single-transaction`, and an exact restored row-count assertion. Docker commands use the captured full container ID rather than a mutable name. On failure the sequence stops without automatically dropping any object. Re-fetched the changed lab from GitHub main and confirmed exact content, 26 balanced Markdown fence delimiters, and presence of both count assertions.

**Remaining limitations and gates:** These are source-level PowerShell and SQL checks only; no PowerShell parser, Docker, PostgreSQL, psql, AWS, or destructive execution occurred. The independent Docker daemon endpoint/container identity comparison is still a manual prerequisite. The expected negative INSERT error is not yet asserted programmatically; it remains a guided interactive exercise. PostgreSQL 18 runtime evidence remains **0/20**, and Chapter 07 remains PostgreSQL 17-targeted with its original mount. Any PG18 migration must use a fresh isolated volume mounted at `/var/lib/postgresql` with verified `PGDATA=/var/lib/postgresql/18/docker`; never repurpose the PG17 volume. Independent review and production certification pending. No changes outside the independent learning path.

**Next:** Complete outstanding Chapter 07 AWS references/internal anchors and negative-test safeguards, then Chapter 08 source integrity and documentation references.


## 2026-11-07 — Chapter 07 AWS documentation and navigation checkpoint

**Scope:** Re-read the independent track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, prior static audit and this validation log; resumed the unfinished Chapter 07 AWS reference gate after the committed backup/restore fix. Reviewed Chapter 07 lesson/lab links without repeating completed PostgreSQL manual endpoint checks.

**Documentation checks (retrieved page and matched title/topic):** The eight previously outstanding distinct AWS documentation URLs all resolved to the intended topics: RDS for PostgreSQL (CHAP_PostgreSQL), rds_superuser role, Multi-AZ DB instance, Multi-AZ DB cluster, DB instance read replicas, automated backups, backup retention, and parameter-group association. The previously checked PITR and Database Insights pages bring Chapter 07's **10/10 distinct AWS reference URLs** to page/topic verified. No URL fragments occur in the Chapter 07 lesson or lab external references. This is retrieval/topic checking, **not** a guarantee against future redirects or provider behavior changes.

**Internal navigation:** Reviewed all relative Markdown links in the Chapter 07 lesson and lab. They point to the track README, MASTER-TOC, STATUS-TRACKER, the Chapter 07 lesson/lab reciprocal links, and the Chapter 01 prerequisite lab. Their targets are present in the previously recorded track tree; no internal fragment links were found. This is a Chapter 07-only link check, not track-wide exhaustive anchor validation.

**Remaining source-level safety finding:** The intentional Chapter 07 negative INSERT under SET ROLE ch07_reader is described as an expected permissions error but is not programmatically asserted. In a future isolated test, capture SQLSTATE **42501** (insufficient_privilege), prove that the role is ch07_reader before the attempt, RESET ROLE even on error, and assert that row count remains three. An unrelated failure must not count as a successful negative test. Preserve the instructional interactive example until a carefully reviewed fail-closed harness is added. Backup/restore exit-code checks are already repaired in commit 709e9e7; do not duplicate that work.

**Version/safety gates:** PostgreSQL 18 documentation remains authoritative; Chapter 07's existing container is PostgreSQL 17-targeted. No Docker, PowerShell, psql, AWS CLI, destructive, cloud or Kubernetes execution was performed in this checkpoint. PG18 runtime evidence remains **0/20**. PG18 migration requires a fresh isolated volume mounted at /var/lib/postgresql and verified PGDATA=/var/lib/postgresql/18/docker, never reuse the PG17 mount or data. Independent review and production certification remain pending. No file outside this independent track was changed.

**Next:** Inspect Chapter 08 lesson, lab and CloudNativePG example for source integrity, prerequisites, external references, version-specific guidance, and Kubernetes resource-safety controls; continue track-wide link/anchor and negative-test review before runtime migration.


## 2026-11-07 — Chapter 08 source-integrity checkpoint

**Scope:** Re-read track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, historical semantic evidence, Chapter 08 lesson, lab and CloudNativePG example manifest. Source-only review; no database or Kubernetes commands executed.

**Confirmed defect and repair:** Chapter 08 lab's Docker startup preflight was truncated in its 64-character container-ID regex, swallowing the password warning and corrupting Markdown structure. A second copy of Steps 2–7, worksheets, cleanup and references followed the first complete sequence. Commit `3b5e0a60a0df4c0271a8a9a3be7b5af788c55a26` restores a fail-closed container-ID assertion and checks the inspected full ID, chapter/track labels, expected PostgreSQL 17 image tag and named volume at the PostgreSQL 17 mount. It restores the demonstration-password warning and removes the duplicate tail. Re-fetched main and verified exact replacement content; size 24,627 → 16,632 characters; 26 balanced Markdown fences; one Steps 2–7 sequence. This is **not** PowerShell parser or runtime validation.

**Manifest review:** The review-only CloudNativePG YAML declares `postgresql.cnpg.io/v1`, one instance, 1Gi storage and initdb owner/database. It is not HA and lacks backups, explicit PostgreSQL image/version, storage class, security, monitoring and resource policies. Do not apply without a compatible installed operator, approved namespace and separate environment review. Chapter 08 lesson still labels PostgreSQL 17 as its reference instead of explicitly separating the PostgreSQL 18 documentation baseline; metadata reconciliation remains open. The lesson links to a CloudNativePG development-branch bootstrap page; prefer version-pinned documentation for an installed operator and verify links before certification.

**Open safety findings:** Optional Docker restart checks context name, ID, labels and mount, but not independently captured daemon endpoint or immutable image digest; therefore restart is **blocked pending independent creation evidence**. Its commands also need explicit exit-code/readiness and marker-value assertions before claiming persistence. Manual cleanup contains destructive volume removal and must remain approval-gated. Optional `kubectl` inventory requires explicit non-production context authorization and must never mutate a cluster. Review the PostgreSQL 18 and Kubernetes/CloudNativePG documentation endpoints, internal links, YAML compatibility and expected results next.

**Version/status:** Lab remains `postgres:17` with `/var/lib/postgresql/data`; no PostgreSQL 18 migration or runtime test occurred. PG18 migration requires a fresh disposable volume mounted at `/var/lib/postgresql` and verification of `PGDATA=/var/lib/postgresql/18/docker`. PostgreSQL 18 runtime-validated 0/20. Independent review and production certification pending. No files outside this independent track changed.

**Next:** Reconcile Chapter 08 version metadata, verify its documentation endpoints and strengthen restart/persistence checks before Chapter 09. Do not repeat completed Chapter 01–07 reviews.


## 2026-11-07 — Chapter 08 Markdown integrity follow-up

**Scope:** Re-read README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, and prior semantic progress before inspecting Chapter 08 lesson/lab. Source-only checks; no Docker, PowerShell, psql, Kubernetes or cloud execution.

**Confirmed defects:** Despite the earlier deduplication checkpoint, Chapter 08 lab still had an opening PowerShell fence inside an unclosed PowerShell block in Step 1, and a trailing orphan fragment after Official references (including a stray failed-container assertion and repeated preflight text). These were removed/repaired in commit `3424612405d997819eccb5e7bd2e85e8dc52b69c`. The resulting source has 24 balanced Markdown fence delimiters; this is a structural source check, not a PowerShell parser result.

**Version metadata:** Chapter 08 lesson now explicitly distinguishes the PostgreSQL 18 documentation baseline from the legacy PostgreSQL 17 lab target (commit `5993dc2aeb3f45bb4531d4df40ba7e59d0faac49`). No PostgreSQL 18 image, PGDATA, mount, runtime status or historical PostgreSQL 17 evidence was changed.

**Outstanding:** Verify official PostgreSQL 18, Kubernetes and CloudNativePG reference destinations and anchors; review operator-version pinning and the optional restart's independent daemon/image identity, fail-closed exit/readiness checks and marker assertions. Do not execute restart or destructive cleanup without independently recorded creation identity and explicit disposable-resource approval. PostgreSQL 18 runtime validation remains 0/20; independent review and production certification remain pending. Continue Chapter 08 safety and link checks, then Chapter 09. No edits outside the independent track.


## 2026-11-07 — Chapter 08 restart guardrail hardening (static only)

**Scope:** Re-read the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, prior semantic audit and Chapter 08 lesson/lab. Resumed the outstanding Chapter 08 Docker restart-safety finding without repeating completed Chapter 01–07 reviews.

**Source change:** Chapter 08 lab now captures Docker daemon ID and immutable local image ID during creation. Before the optional restart, the PowerShell example requires retained creation-session context, daemon ID, full container ID, chapter/track labels, exact PostgreSQL 17 image tag and image ID, and expected named-volume mount. It checks the synthetic marker's exact value and count before disruption, checks restart/readiness exit codes, and checks marker value/count and mount again afterward. PostgreSQL commands use `psql -X -A -t -v ON_ERROR_STOP=1`. Source commits: `7313df12f0fb2823bdcb8023928b1a544f4d4c2b` and follow-up `ca6ef369c337bff7de61e065d5d4cf72b664c2a9` (removed an accidentally duplicated trailing section introduced during editing). Final source was re-fetched: 24 balanced fence delimiters and one sequence of Chapters 0–7.

**Limitations:** Static review only; no PowerShell parser, Docker, PostgreSQL or Kubernetes runtime execution. A Docker daemon ID and local image ID are additional safeguards, not independent proof of authorized ownership; verify original creation records and registry digest where available before disruption. Optional cleanup still requires explicit authorization and independent identity comparison. No claim of persistence or runtime success. Chapter 08 remains PostgreSQL 17-targeted with the legacy mount `/var/lib/postgresql/data`. PostgreSQL 18 migration requires a new isolated volume at `/var/lib/postgresql`, verifying `PGDATA=/var/lib/postgresql/18/docker`. PG18 runtime-validated: **0/20**. Independent review and production certification pending.

**Next:** Check Chapter 08 PostgreSQL 18, Kubernetes and CloudNativePG URLs and operator-version compatibility; then proceed to Chapter 09 source integrity. No changes outside this independent track.


## 2026-11-07 — Chapter 08 CloudNativePG reference pinning and operator boundary (source review)

**Prerequisites reviewed:** Track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE and prior semantic audit. This checkpoint resumes the open Chapter 08 documentation finding; it does not repeat prior source repairs or runtime tests.

**Verified external reference:** The lesson's CloudNativePG development-branch bootstrap URL was replaced with the stable version-pinned [CloudNativePG 1.28 bootstrap documentation](https://cloudnative-pg.io/docs/1.28/bootstrap/). The versioned [1.28 API reference](https://cloudnative-pg.io/docs/1.28/cloudnative-pg.v1/) describes the `bootstrap.initdb` configuration used in the illustrative manifest. The [CloudNativePG 1.28 overview](https://cloudnative-pg.io/docs/1.28/) states that the operator directly manages database Pods/PVCs and does **not** use StatefulSets; the lesson now distinguishes the generic Kubernetes StatefulSet reference from the operator's implementation. Version 1.28 is a documentation snapshot, **not** an assertion of an installed or approved operator version. The live cluster's Kubernetes/operator/PostgreSQL compatibility, CRD schema and image digest remain unverified.

**Source change:** Chapter 08 documentation note now requires checking installed operator release, supported Kubernetes/PostgreSQL versions, CRDs, image identity, storage class, namespace, RBAC and ownership before any deployment. Commit `b95b5bd17835b4889f7ede77d990f8625d85074d`; post-commit fetch confirmed the pinned URL and updated note.

**Remaining gate:** Independently resolve all Chapter 08 PostgreSQL 18/Kubernetes links and anchors, review manifest against the *actual* operator release, then begin Chapter 09 source-integrity/reference checks. No Kubernetes, Docker, SQL or cloud resources were run or changed. Legacy lab remains PostgreSQL 17-targeted; PostgreSQL 18 runtime validation **0/20**; independent review and production certification pending. No files outside this independent track modified.


## 2026-11-07 — Chapter 08 official reference destination verification

**Scope and baseline:** Re-read the track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE and existing semantic-review-progress report; inspected Chapter 08 lesson and lab. This is a URL destination/topic verification checkpoint, not a repeat of prior code repairs. PostgreSQL 18 is the documentation baseline; the lab still targets PostgreSQL 17.

**Verified distinct destinations (7):** PostgreSQL 18 [monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html) and [continuous archiving/PITR](https://www.postgresql.org/docs/18/continuous-archiving.html) both resolve and match the chapter's monitoring and recovery topics. Kubernetes [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/), [persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/) and [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/) resolve and match their respective topics. The previously pinned [CloudNativePG 1.28 bootstrap](https://cloudnative-pg.io/docs/1.28/bootstrap/) endpoint resolves and explicitly identifies release 1.28 and initdb bootstrap. These are live page/destination checks, not validation of installed software, exact CRD compatibility, or all possible anchors.

**Outstanding:** The general https://cloudnative-pg.io/docs/ destination and internal relative links were inventoried but not independently resolved in this checkpoint; do not mark exhaustive Chapter 08 links complete. Kubernetes documentation is unpinned and may change; operator 1.28 is only a reference snapshot. Manifest schema, installed operator/CRD, PostgreSQL image digest, restart/cleanup authorization and executable lab behavior remain unverified. The existing historical PostgreSQL 17 audit is preserved. No Docker, SQL, PowerShell, Kubernetes or cloud commands executed. PostgreSQL 18 runtime-validated labs: **0/20**; independent review and production certification pending.

**Next:** Finish Chapter 08 remaining general documentation and relative-link resolution, then begin Chapter 09 lesson/lab source integrity and semantic safeguards. Do not run destructive or failover tests outside disposable approved environments.


## 2026-11-07 — Chapter 08 remaining source-integrity checkpoint

Re-read track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline and prior audit. Chapter 08 lesson and lab Markdown links were inventoried. The lesson's relative targets are the track README, MASTER-TOC, STATUS-TRACKER, Chapter 08 lab and `labs/chapter-08/cluster-example.yaml`; the lab points to the chapter, track README and manifest. These are path-level observations, **not** an exhaustive independent anchor/HTTP check. The general CloudNativePG documentation landing page remains an unverified live endpoint.

**Confirmed critical source defect:** Chapter 08 lab preflight ended with an incomplete PowerShell regex/conditional (`$labImageId -notmatch '^sha256:[a-f0-9]{64}`), which would make the code block unusable. Corrected the condition to require an immutable local image ID and fail closed on mismatch. Commit `e0c246009ae63d2c788ae1a12079edb154ca8124`. An intermediate edit (`11be6e3c0a74e74655d2a6c991c396151a9a9f72`) unintentionally duplicated material because of replacement-string interpolation; the corrective commit restored the prior lesson verbatim except for the intended one-line condition. No runtime execution occurred. Verify the final file independently before using it.

**Outstanding:** PostgreSQL server major-version and writable-primary checks in the initial Chapter 08 startup preflight, full independent link resolution, Docker daemon/volume identity proof before cleanup, PostgreSQL 18 image/mount migration and genuine isolated runtime evidence. Chapter 09 source-integrity review is next after this checkpoint. PostgreSQL 18 runtime validation remains **0/20**; independent review and production certification remain pending. No changes outside this independent track.


## 2026-11-07 — Chapter 09 architecture lab fail-closed preflight (static review)

**Prerequisites inspected:** Track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, prior semantic-review progress, and Chapter 09 lesson/lab. Earlier Chapter 08 findings were not re-reviewed. Chapter 09 uses synthetic weighted scores and temporary SQL objects; expected Scenario A and B score arithmetic was checked by inspection, **not** by PostgreSQL execution.

**Confirmed source gap and correction:** Chapter 09 previously printed `server_version_num` but never enforced PostgreSQL 17, and its interactive `psql` invocation did not enable `ON_ERROR_STOP`. The lab now checks the returned version against `^17[0-9]{4}$`, fails closed unless `pg_is_in_recovery()` is false, uses the captured full container ID for SQL checks, and enables `-X -v ON_ERROR_STOP=1` for the interactive session. Source commit: `8d3a00f249f8fc892192789ed5576b0fe8ef0636`; final lab was fetched from `main` and exact content compared.

**Remaining Chapter 09 findings:** Docker context and container ID still require independent comparison to Chapter 01 creation evidence; the current preflight cannot independently establish authorized ownership. A stronger negative test should assert unknown/false mandatory gates and verify that blocked candidates never become approved. Review all Chapter 09 relative links and PostgreSQL 18/AWS/CloudNativePG endpoints and anchors before closing the documentation gate. Chapter 09 lesson metadata still references the legacy PG17 lab and should explicitly identify PG18 as documentation baseline. No Docker, PowerShell, SQL, AWS, Kubernetes or destructive operation was executed. PG18 runtime-validated **0/20**; independent review and production certification pending. No files outside the independent learning path changed.

**Next:** Reconcile Chapter 09 lesson version metadata and link targets, then continue Chapter 09 negative-test assertions and Chapter 10 source review. Preserve historical PostgreSQL 17 audit evidence.


## 2026-11-07 — Chapter 09 source-integrity recovery and documentation metadata

Re-read track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline and previous semantic audit before resuming the earliest unfinished Chapter 09 checkpoint. The lab on main contained a **broken, unclosed PostgreSQL 17 PowerShell version assertion** and an **accidentally duplicated ~13 KB trailing fragment** after the first official reference list. These defects made the documented preflight unusable despite earlier claims of repair. Corrected the complete major-version assertion and writable-primary check, restored the closing PowerShell fence and Section 1 heading, and removed the duplicate trailing content. Final source structure: **28 Markdown fence delimiters (balanced)**, one Section 1, and one official references section. Source corrective commits: `494fa711cc3f59baa9dec356b1666ce62f6d61ab`, `bf8806c9af10ed2b4a3aab82e8c9f6e31c52c1d8`, `1a0fb13e622ec3d8600c00b95bbe2aaea9d41e60`. The first two intermediate commits are superseded by the third; only the final source should be used. Chapter 09 lesson metadata now explicitly separates PostgreSQL 18 documentation from its legacy PostgreSQL 17 lab (commit `6f0912170c983a8f249621ba6a4459bce01edcc3`).

**Limitations and next gate:** Static inspection only; no PowerShell parser, Docker daemon, PostgreSQL server, or SQL runtime was used. Verify final GitHub source again; test the preflight in a genuinely isolated approved Docker environment and retain exact sanitized evidence before any runtime status promotion. Chapter 09 unknown/false mandatory-gate assertions and full external/relative link/anchor resolution remain open. Docker ownership must be independently established from Chapter 01 creation evidence. PostgreSQL 18 runtime validation remains **0/20**; independent review and production certification pending. The separate 100-chapter curriculum was not edited.


## 2026-11-07 — Chapter 09 mandatory-gate negative assertions (PostgreSQL 18 documentation baseline)

- **Source:** [Chapter 09 lab](../labs/chapter-09/README.md). Reviewed the existing fictional decision matrix and the prior PostgreSQL 17 safety preflight; did not repeat the completed Chapter 09 structural repair.
- **Finding:** The prior lab described blocked and unknown mandatory gates but lacked executable, separately observable negative assertions for both conditions. Its display-only query could be mistaken for a test pass without checking gate outcomes.
- **Correction:** Added four read-only Boolean assertions (with session-local temporary-table updates) for Scenario B RDS residency failures, CNPG team-readiness failure, CNPG unknown extension gate, and restored eligibility. Expected result is `pass = t` for each query; a returned `f` is explicitly a failure even when `psql ON_ERROR_STOP` does not raise an error.
- **Version boundary:** SQL syntax reviewed against the PostgreSQL 18 documentation baseline; the lab itself remains PostgreSQL 17-targeted and unexecuted. This is **static review only**, not PostgreSQL 17 or 18 runtime evidence.
- **Safety:** No persistent SQL objects, production databases, Kubernetes, AWS resources, Docker restart, or destructive cleanup authorized. Temporary objects vanish when the session exits. Docker ownership still depends on independent Chapter 01 creation evidence.
- **Next:** Verify Chapter 09 official URLs/anchors and internal links; then start Chapter 10 source-integrity and replication/fencing semantic review. Isolated runtime evidence and independent certification remain outstanding.


## 2026-11-07 — Chapter 09 internal-link resolution and targeted external reference verification

**Prerequisites inspected:** README.md, MASTER-TOC.md, STATUS-TRACKER.md, POSTGRESQL-18-BASELINE.md, prior static/semantic evidence, Chapter 09 lesson and lab on main. Earlier structural and negative-gate repairs were not repeated. Documentation baseline is PostgreSQL 18; the lab remains PostgreSQL 17-targeted.

**Internal relative links:** All 10 Markdown relative-link occurrences in the Chapter 09 lesson and lab were resolved to existing files on GitHub main (eight occurrences in the lesson, two in the lab; repeated targets included). Verified destinations include the version policy, track README, TOC, tracker, Chapter 09 lesson/lab cross-links and Chapter 01 prerequisite lab. This is file-existence verification, not an exhaustive heading-anchor/reference-definition audit.

**Targeted live external checks:** PostgreSQL 18 CREATE TABLE reference (`https://www.postgresql.org/docs/18/sql-createtable.html`) resolves and documents temporary tables; AWS Multi-AZ DB instance reference (`https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html`) resolves and explicitly states its standby cannot serve read traffic. Both align with the chapter's intended topics. Remaining distinct external URLs (including CREATE VIEW, PostgreSQL monitoring/archiving, AWS Multi-AZ DB cluster/region support, CloudNativePG 1.28 and Kubernetes PV) have **not** been independently checked in this checkpoint; do not close the external-link gate or assert installed-operator compatibility.

**Execution/approval boundary:** Read-only repository/documentation checks only. No PostgreSQL, Docker, PowerShell, Kubernetes or AWS runtime commands executed. No PostgreSQL 18 lab migration or runtime validation claimed (0/20); independent review and production certification remain pending. No files outside the independent 20-chapter track modified.

**Next:** Resolve Chapter 09's remaining external destinations/anchors, then review Chapter 10's PostgreSQL 17 replication setup, physical slot/basebackup ordering, fail-closed assertions and PG18 documentation/mount migration risks before isolated execution.


## 2026-11-07 — Chapter 10 replication safety review: version boundary and open defects

**Inputs inspected:** track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, existing semantic evidence, Chapter 09 lesson/lab, Chapter 10 lesson/lab on main. Earlier Chapter 09 work was not repeated. PostgreSQL 18 official documentation is the technical reference baseline; the existing Chapter 10 lab still targets PostgreSQL 17.

**Confirmed documentation inconsistency fixed:** Chapter 10 lesson metadata still called PostgreSQL 17 its reference version, while the lab's heading said 'Official PostgreSQL 17 references' but linked to /docs/18/ URLs. Updated both to identify the PostgreSQL 18 documentation baseline explicitly while preserving the historical PostgreSQL 17 lab target and evidence boundary. No image, volume, PGDATA, command, or expected-output migration was attempted.

**Open safety/semantic findings (not yet corrected or executed):**
1. Chapter 10 setup performs Docker creation and role/HBA/slot changes without a fail-closed PowerShell wrapper or independently captured creation-time IDs. The later cleanup instructions demand those records, so a learner following the lab verbatim cannot meet its own cleanup evidence gate. Add creation-time Docker daemon/context, immutable image ID, full container/network/volume IDs, labels and mount evidence before any later deletion; stop on unexpected pre-existing resources or failed commands.
2. The `pg_basebackup -R -C -S ha10_standby_slot` step can leave a created replication slot or partially populated standby volume on failure. The lab warns against reruns, but needs explicit read-only failure inspection, safe stop conditions, and an approved isolated reset procedure; never drop a slot or delete a volume merely by name.
3. The example places a fixed plaintext replication password in shell arguments and `.pgpass` in the data volume. It is training-only but may appear in shell history/process metadata. Require sanitized evidence, avoid copying credential-bearing `primary_conninfo` or `.pgpass`, and verify mode/ownership without printing secrets.
4. The standby insert is an intentional error and must be checked for nonzero exit code plus expected recovery/read-only SQLSTATE/message, not just visually observed. The asynchronous replay check must wait for a specific synthetic marker with bounded retries; do not count a transient missing table/row as success.
5. For PostgreSQL 18 migration, `postgres:17` and `/var/lib/postgresql/data` must not be blindly replaced. Use a new isolated PG18 volume mounted at `/var/lib/postgresql`, default PGDATA `/var/lib/postgresql/18/docker`, and verify image digest, identity, permissions, actual server version and cleanup independently. Keep PG17 historical records intact.

**Verification scope:** Two track-only documentation corrections committed and fetched back from main. Static inspection only; no Docker, psql, PowerShell, Kubernetes, AWS, replication, promotion, cleanup or destructive execution. No PostgreSQL 17/18 runtime validation, independent approval or production certification claimed. Status remains 0/20 runtime-validated.

**Next:** Address the Chapter 10 first-run provenance/partial-failure guards in a small reviewed change, verify remaining Chapter 09 external references and Chapter 10 PG18 official reference destinations, then pursue isolated runtime evidence when prerequisites are available.


## 2026-11-07 — Chapter 10 first-run provenance and partial-backup safety checkpoint

Inspected track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, prior semantic report and Chapter 10 lab on main. The earliest unresolved Chapter 10 provenance/partial-failure gate was addressed without modifying the separate PostgreSQL curriculum.

**Source correction:** Added a PowerShell guided preflight that checks Docker context, Linux engine, exact-name resource collisions and immutable local postgres:17 image ID. Added creation-time network/volume/image inspection and full container-ID/mount capture instructions. Added explicit pg_basebackup nonzero-exit stop gate with read-only replication-slot and standby-volume inspection; prohibits automatic rerun, slot drop or volume deletion. These are source-level safeguards, not proof of dedicated Docker ownership or a concurrency-safe resource reservation.

**Publication integrity:** Initial commit `146032b27f937d8f6575cbb8e5d4713aa39dcffe` inadvertently duplicated later lab sections. Follow-up corrective commit `f3411d1420ee2df7f3d855cd30b423918cd7050c` restored the original single-copy sections while retaining the intended safeguards. Treat the first commit as superseded. Final source has one numbered Section 1 through 11 sequence, plus Section 0a. No test execution claimed.

**Open:** The PowerShell example is a guided preflight and needs PowerShell parser/runtime verification; further fail-closed command checking, secret handling, standby write-rejection assertion, bounded replay polling and external link verification remain pending. The legacy lab still targets PostgreSQL 17; PostgreSQL 18 is documentation-only. No Docker, psql, PowerShell, failover, cloud or cleanup execution. Runtime 0/20; independent review and certification pending.

**Next:** Complete Chapter 10 credential and replication assertions, then verify documentation endpoints; execute only in approved disposable Docker environments with genuine evidence.


## 2026-11-07 — Chapter 10 preflight integrity correction (static only)

Fetched the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, prior audit and Chapter 10 lab from GitHub main. Found the Chapter 10 Section 0a PowerShell image-ID conditional truncated mid-regex, leaving an unclosed code fence, and a duplicate network/volume creation block preceding Section 1. This made the prior reported preflight safeguard unusable and risked repeating resource creation. Repaired the complete immutable-image-ID assertion, added fail-closed exact-name container/volume/network inventory checks, consolidated creation in Section 1, and added immediate exit-code checks for creation commands. Commit `fa54ebbc5fbb18dc4da4ad5581671d2bcf8abeee`. Fetched final source from main: 40 balanced tilde-fence delimiters, exactly one Section 1, complete image-ID regex. These are source inspections, not PowerShell parsing or runtime execution.

**Still open:** Verify actual PowerShell behavior; enforce independent creation-time ownership evidence; review replication password exposure and `.pgpass` handling, bounded asynchronous replay assertions, standby write-rejection exit-code assertions, and PostgreSQL 18 migration. No Docker/psql/cloud commands or destructive operations executed. PostgreSQL 18 runtime evidence 0/20; independent review and production certification pending. Historical PostgreSQL 17 findings retained. Next: Chapter 10 credential and replay/write-rejection assertions.

### 2026-11-07 — Chapter 10 bounded replication acceptance (static source correction)

- **Scope:** Chapter 10 lab only; PostgreSQL 18 documentation baseline, PostgreSQL 17 legacy lab runtime. Source commit [7eeba7a](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/7eeba7a7bc058b346e24460ef3a63e3bebbd5d73).
- **Confirmed gap:** Prior Chapter 10 replication test used a single unbounded standby SELECT with manual retries and a standby write attempt whose expected failure was not programmatically distinguished from unrelated errors.
- **Correction:** Added fail-closed primary DDL/DML exit checks, a 15-attempt / 2-second bounded exact-marker standby poll, and a write-rejection assertion requiring both nonzero `psql` exit status and verbose SQLSTATE `25006`. The polling window is approximately 30 seconds plus command execution time, not a strict wall-clock timeout.
- **Static verification:** Re-fetched updated lab from GitHub `main`; exact content matched committed source; 40 tilde-fence markers remained balanced. No PowerShell, Docker or PostgreSQL commands were executed. These are **unexecuted acceptance examples**, not runtime proof.
- **Remaining:** Validate PowerShell stderr/exit-code capture and SQLSTATE matching on an isolated PostgreSQL 17 container; strengthen replication secret handling and `pg_basebackup` exit-code checks; verify external documentation links; migrate PG18 image and volume mount safely in separate scoped work. Runtime validated: **0/20**; independent review and production certification pending.


### 2026-11-07 — Chapter 10 SQLSTATE matcher and basebackup exit gate (static only)

Reviewed the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, existing evidence and current Chapter 10 lab. Confirmed two executable-source defects: the PowerShell single-quoted `-notmatch` regex used `\\s` (literal backslash plus s) rather than `\s` (whitespace), making the expected verbose `ERROR:  25006:` assertion fail; and `pg_basebackup` described checking exit status but lacked an immediate fail-closed `$LASTEXITCODE` check. Corrected both in [source commit df268e4](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/df268e412e9f9771d50a9e76531c7e7b32972d09). The backup now throws immediately on nonzero exit before later standby actions. The SQLSTATE check still requires a nonzero psql exit plus the exact expected code.

**Limits:** Static text-level verification only. No PowerShell parser, Docker, psql or PostgreSQL execution, no secret handling or cleanup proof. Additional issues remain: hard-coded replication secrets exposed in command/process metadata; Section 2–5 command failure checks; actual PowerShell stderr capture behavior; and reference validation. PG17 remains the legacy runtime target; PG18 is the documentation baseline and **0/20 PG18 labs runtime validated**. Independent review and production certification pending. Next: credential exposure and fail-closed startup/standby checks, then official reference verification.


### 2026-11-08 — Chapter 10 setup exit gates and passfile metadata (static only)

Reviewed track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, prior semantic evidence, and Chapter 10 lab on main. Added immediate PowerShell `$LASTEXITCODE` fail-closed checks for primary/standby container creation, replication-role SQL, HBA append/reload, standby volume permission initialization and `.pgpass` creation. Added an executable assertion that `.pgpass` is owned by the postgres UID and mode 0600, without printing its contents. Explicitly documented that static lab credentials remain exposed in command history/Docker metadata and are **not acceptable for shared/production environments**. Source commit [1e59522](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/1e59522e02a9168a4129a8519dba85722ceaedde). Re-fetched main and confirmed exact source content and 40 balanced tilde fence delimiters.

**Limits/open:** Source-level inspection only; no PowerShell parser, Docker or PostgreSQL execution. `pg_isready` and remaining observation queries still need consistent exit handling; verify PowerShell native stderr/SQLSTATE behavior, hard-coded secret remediation, first-run resource ownership and cleanup proof, and external references. Historical PostgreSQL 17 lab target unchanged; PostgreSQL 18 documentation baseline remains in force; **0/20 PG18 labs runtime validated**. Independent review and production certification pending. Separate 100-chapter curriculum untouched.


### 2026-11-08 — Chapter 10 startup and observation exit gates (static only)

Inspected the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, previous semantic audit and current Chapter 10 lab. Found 13 `docker exec` readiness/observation commands in Sections 2, 5 and 8 without immediate native exit-status gates. Added fail-closed `$LASTEXITCODE` assertions after each. Source commit [e7ec838](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/e7ec8388269e896b3cd97d6db2dcc20d82d595ca). Re-fetched main and confirmed exact content and 40 balanced Markdown tilde fences. These assertions check command execution, not semantic query results: actual role/streaming/slot state still requires executable assertions. No Docker, PowerShell or PostgreSQL commands executed; no cleanup performed.

**Open:** hard-coded disposable credentials, PowerShell stderr/SQLSTATE capture, `pg_basebackup` behavior and first-run provenance, external documentation/anchor checks, and genuine isolated PG17/PG18 runtime evidence. PostgreSQL 18 is the documentation baseline; Chapter 10 remains PG17-targeted. PG18 runtime 0/20; independent review and production certification pending. No files outside the independent track changed.


### 2026-11-08 — Chapter 10 role and streaming-state assertions (static only)

Inspected the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, historical static audit and Chapter 10 source. Prior checkpoint added native exit gates, but successful queries could still return unexpected values. Added Section 5a to assert primary `pg_is_in_recovery() = f`, standby `= t`, exactly one lab sender `streaming|async`, and exactly one standby receiver `streaming|ha10_standby_slot`; bounded retries (15 attempts, 2 seconds) stop on query failure or timeout. Source commit [2d0319d](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/2d0319dae769e9266568bd3f9616f61da90c9552). These are **source-level assertions only**; no PowerShell parser, Docker, psql or PostgreSQL runtime was executed, and no cleanup proof was produced. Remaining: credentials, PowerShell native stderr behavior, external documentation anchors, safe ownership/cleanup, PG17/PG18 isolated execution. PostgreSQL 18 documentation baseline remains authoritative; Chapter 10 is still PG17-targeted. Runtime validated 0/20, independent review and certification pending. No edits outside the independent track.


### 2026-11-08 — Chapter 10 role/HBA/slot observation exit gates (static only)

Inspected the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline, prior semantic evidence and Chapter 10 lab on main. Confirmed three read-only observation gaps: role inspection, HBA inspection and the replication-slot/standby-volume metadata inspection sequence could continue after a native command failed. Added `psql -X -v ON_ERROR_STOP=1` to role/HBA inspections and immediate `$LASTEXITCODE` stop gates after those two queries, the slot query and volume metadata inspection. Source commit [866ae42](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/866ae42cd2c136e7556f6666cde57ae3d1ec75b6). No other curriculum files changed.

**Limits and next:** This is source-level verification only, not PowerShell parsing or Docker/PostgreSQL execution. A successful observation exit code does not assert expected role/HBA/slot values. Continue with value assertions, credential exposure mitigation and remaining reference verification. Historical PG17 lab remains unchanged in runtime target; PG18 is the authoritative documentation baseline, with **0/20 PG18 labs runtime-validated**. Independent approval and production certification remain pending.


### 2026-11-08 — Chapter 10 role, HBA and physical-slot value gates (static only)

Inspected the independent track README, MASTER-TOC, STATUS-TRACKER, POSTGRESQL-18-BASELINE, previous semantic audit and Chapter 10 lab on GitHub main. The prior checkpoint added native exit-code checks but still accepted unexpected successful query values. Added explicit fail-closed PowerShell/psql scalar assertions for the replication role (REPLICATION=true, SUPERUSER=false, LOGIN=true), exactly one matching parsed SCRAM HBA replication rule, and the newly created physical slot being inactive before standby startup. Source commit [21be8ba](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/21be8ba1e147d891003b575a875fc330e97e2dd2). Re-fetched source from main and verified identical content and 46 balanced tilde fence delimiters.

**Limitations:** Source-level review only. PostgreSQL 17 behavior of `pg_hba_file_rules` array comparisons, PowerShell array capture, and all expected output must still be executed in an isolated runtime. No Docker, PowerShell, psql, cloud, destructive actions or cleanup occurred. Credentials remain hard-coded in disposable examples; further mitigation and comprehensive internal/external URL/anchor checks remain open. PostgreSQL 18 is the documentation baseline, while this lab remains PostgreSQL 17-targeted; 0/20 runtime-validated. Independent review and production certification pending. Next: test assertion semantics, verify remaining references, then proceed to approved disposable PostgreSQL runtime evidence.


## 2026-11-08 — Chapter 10 bounded startup readiness correction (PostgreSQL 18 documentation baseline)

**Scope:** Chapter 10 lab only. Inspected the track README, master TOC, status tracker, PostgreSQL 18 baseline policy, previous semantic-review evidence and current Chapter 10 lab on `main`. This checkpoint does not repeat the 20 historical semantic reviews.

**Confirmed source defect:** Immediately after `docker run -d`, the primary and standby `pg_isready` checks threw on the first nonzero result, even though the surrounding instructions explicitly allowed PostgreSQL initialization and standby startup time. A normal, transient `pg_isready` exit 1 (rejecting connections) or 2 (no response) could therefore terminate the lab before the documented replication assertions. This was a sequencing and expected-results defect, not a demonstrated server failure.

**Correction:** Replaced each single-shot readiness gate with at most 30 probes, two-second pauses only after transient exit 1/2, immediate failure on other exit statuses, and a hard stop after timeout. Later SQL and replication-state assertions remain fail-closed; no automatic restart, slot deletion, promotion or cleanup was introduced. The expected-results text now matches the bounded startup behavior. [Scoped source commit](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/a13e3574d0421288dbed6cb277172cbdb513052f).

**Verification:** Re-fetched the committed lab from GitHub `main` and compared the entire content; 46 Markdown fence delimiters remain balanced. **Static source verification only:** no PowerShell interpreter, Docker daemon, `pg_isready`, `psql` or PostgreSQL server was executed for this checkpoint. A loop's success and timing cannot be claimed without real runtime evidence.

**Remaining gates:** Validate PowerShell command/exit behavior and exact SQLSTATE capture in an approved isolated context; review replication credentials and generated `primary_conninfo`/passfile handling without exposing secrets; complete whole-track internal/external reference verification; migrate lab image, mounts and expectations separately to PostgreSQL 18 using fresh version-appropriate volumes; execute and capture sanitized runtime and cleanup/retention evidence. Existing PostgreSQL 17 historical notes are preserved. Runtime validation remains 0/20; independent review and production certification remain pending.


## Chapter 10 — provenance inspection failure gates (2026-11-08)

**Scope:** Chapter 10 replication lab, following the previously recorded bounded readiness and configuration-assertion reviews. PostgreSQL 18 remains the documentation baseline; these are PostgreSQL 17-targeted lab instructions. **Method:** source-only PowerShell control-flow inspection; no Docker, PowerShell, or PostgreSQL commands were executed.

**Confirmed weakness corrected:** The creation-time provenance block previously ran Docker context, image, network and volume inspections without testing their exit codes. A failed inspection could be followed by subsequent commands, making the evidence incomplete while appearing successful. The lab now fails closed on changed Docker context/image identity and nonzero image/network/volume inspection statuses; the separate post-creation primary/standby inspection examples also stop on nonzero exit codes. This does **not** independently verify that labels, mounts or consumers match the expected values: the owner must inspect and record them before proceeding or cleanup. Resource names and labels alone are not ownership proof.

**Static verification:** Source edit scoped to [Chapter 10 lab](../labs/chapter-10/README.md); Markdown fences remained balanced. The source was fetched again from GitHub main after publication. **Runtime:** not executed; 0/20 runtime-validated. No PG18 migration, independent sign-off, or production certification is implied.

**Next:** Strengthen expected-value checks on the creation-time resource metadata, address plaintext training credentials, finish external-reference verification, and execute only on an approved isolated disposable Docker context with actual version, image, command, outcome and cleanup evidence.

## 2026-11-08 — Chapter 10 creation-time resource metadata assertion gate

**Baseline:** PostgreSQL 18 documentation; **lab runtime target:** historical PostgreSQL 17. **Review:** source-level only, no Docker, PowerShell or PostgreSQL execution.

- Continued from the recorded Chapter 10 provenance follow-up rather than repeating earlier semantic reviews. Confirmed that successful Docker inspection alone did not enforce the intended resource label values or empty-network condition.
- Added a pre-start, read-only PowerShell assertion for exact `training.track=pg-enterprise-ch10` labels on both named volumes and the named network, and for zero network consumers. Each command's exit code, output cardinality and expected value are checked. An unexpected result stops the lab without cleanup or mutation.
- The gate runs **after** network/volume creation and **before** primary startup. Existing container identity and mount provenance must still be recorded at creation time. Labels can be spoofed; they do not establish exclusive ownership or authorize deletion.
- **Limitations:** PowerShell and Docker CLI behavior is unexecuted. Creation-time identity assertions for container mounts/consumers, credential handling, documentation endpoint verification and PostgreSQL 18 image/mount migration remain open. Historical PostgreSQL 17 evidence is preserved.
- **Next:** Verify the label/consumer checks in an approved disposable Docker context, then add fail-closed post-creation container image/mount assertions and audit external references. Keep PostgreSQL 18 runtime status at 0/20 until genuine execution and cleanup evidence exists.


## 2026-11-08 — Chapter 10 post-creation image and mount assertions (static only)

**Documentation baseline:** PostgreSQL 18; **historical lab target:** PostgreSQL 17. Inspected the independent track README, master TOC, status tracker, PG18 baseline, previous semantic audit and Chapter 10 lab. Continued the earliest recorded outstanding provenance checkpoint rather than re-reviewing all twenty chapters.

**Finding and change:** Previously, successful `docker inspect` calls displayed container metadata but did not fail on a mismatched image ID, ownership label or named data-volume mount. Added a read-only PowerShell assertion block that checks full container ID shape, image ID against preflight, `training.track` label, and exactly one named volume mount at the PG17 data path. It fails closed without removing or restarting resources. Run the primary-only check after primary creation, then the combined check after standby creation. [Source commit](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/07b612e11fa5d5c4ab2a8873a4ba8adc542ac34e). Re-fetched `main` and confirmed exact updated content and balanced Markdown fences.

**Limitations:** This is a static control-flow review; PowerShell formatting and Docker behavior have **not** been executed. The block does not prove exclusive ownership or authorize cleanup. The lab still exposes disposable hard-coded credentials, and comprehensive internal/external reference checks remain incomplete. PG18 migration must use a **new** volume mounted at `/var/lib/postgresql`, not the legacy PG17 mount. Runtime evidence remains **0/20**; independent review and production certification remain pending. No cloud, Docker, psql or destructive operations were performed. No changes to the separate 100-chapter curriculum.

**Next:** Resolve Chapter 10 PowerShell native-command and Docker-format behavior in an isolated environment, strengthen secret handling and cleanup evidence, and finish outstanding reference verification before runtime status advances.


## 2026-11-08 — Chapter 10 corrupted source recovery and provenance sequencing (static only)

**Confirmed critical source defect:** The Chapter 10 README on main contained a truncated PowerShell regular expression in the new container-provenance block, followed by a duplicated tail of the lab after the first official-reference section. The malformed fence left later headings inside a code block, and the assertion could not execute. This was discovered by checking actual source continuity rather than trusting the previously recorded balanced-fence claim.

**Correction:** Replaced the broken combined loop with a PowerShell function checking exact container ID, image ID, ownership label, and one expected named PG17 data-volume mount. Added explicit calls immediately after each corresponding container creation; removed the duplicate corrupted tail. [Assertion repair](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/9afdeccb5d0e0dea8a094d948a024c7459b4b83b) and [duplicate-tail cleanup](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/3f155e3241d9eaab5286a9a7b0df94ea791cac9b).

**Verification:** GitHub main re-fetch after cleanup; one Chapter 2 heading, one official-reference section and **50 balanced tilde fence delimiters**. This is static source verification only; no PowerShell parser, Docker, PostgreSQL or cleanup commands were executed. The function requires the approved preflight session and is **not** PG18 mount compatible. Existing PG17 historical evidence remains intact. Runtime status stays **0/20**; independent review and production certification pending.

**Next:** Verify PowerShell/Docker formatting and the negative-test SQLSTATE behavior in an approved disposable runtime; review credential exposure and remaining links. Migrate PG18 only with a fresh volume mounted at `/var/lib/postgresql` and verified `PGDATA=/var/lib/postgresql/18/docker`. No separate 100-chapter curriculum edits.
