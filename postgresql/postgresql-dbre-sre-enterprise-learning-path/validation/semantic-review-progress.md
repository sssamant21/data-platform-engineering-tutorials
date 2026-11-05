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
