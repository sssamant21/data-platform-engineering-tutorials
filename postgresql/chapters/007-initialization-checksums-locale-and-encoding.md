# 007 — Initialization, Checksums, Locale and Encoding

[Master plan](../MASTER-PLAN.md) · [Previous chapter](006-installation-packages-and-directory-layout.md) · [Hands-on lab](../labs/007-initialization-checksums-locale-encoding-lab.md) · [Inspection SQL](../scripts/007-initialization-inventory.sql)

## 1. Operational problem and objectives

Initialization establishes properties that shape storage, text behavior and future recovery. An inherited shell locale, an incompatible database template or an unplanned collation-library change can create operational problems long after installation.

This chapter teaches explicit initialization choices and their verification. It does not modify production checksums or intentionally corrupt files.

**Audience:** DBRE/SRE only. **Reference:** PostgreSQL 18. **Prerequisites:** Chapter 006, PostgreSQL 18 server tools, a non-root lab OS account and the Chapter 004 primary. **Effort:** 60–90 minutes.

After the lab you should be able to initialize a fresh cluster safely, verify checksums offline, inspect database locale/provider/encoding and distinguish character conversion errors from database corruption.

## 2. Initialization versus database creation

| Operation | Scope | Operational boundary |
|---|---|---|
| Package installation | Programs and supporting files | Does not universally initialize or start an instance |
| initdb | A new instance's initial database cluster | Fresh directory, owning OS identity and matching major |
| CREATE DATABASE | One database inside a running instance | Database privileges, template and compatible locale/encoding |
| Physical standby bootstrap | Copy of an existing cluster | Preserves primary data representation; not independent initialization |

initdb creates initial system catalogs and template databases. A standby is normally built from a physical copy of its primary, not independently initialized and later “attached.”

template1 is normally the default source for database creation; template0 provides a pristine template suitable for explicit alternative locale/encoding choices. Do not customize template0.

## 3. Initialization decision record

Record before executing:

| Choice | Why DBRE/SRE needs it |
|---|---|
| Binary major/minor/build | Data compatibility and repeatability |
| OS owner and directory | Service access and isolation |
| Encoding | Allowed text representation |
| Locale provider and locale | Ordering and character classification |
| Checksums | Detection of certain page-corruption problems |
| Authentication/bootstrap login | Initial access boundary |
| WAL location and segment policy | Storage/recovery topology |
| Storage mounts and capacity | Prevent initialization on the wrong filesystem |

For the teaching cluster, use UTF8, explicit libc/C locale, checksums and SCRAM. A production locale is a business and compatibility decision, not a generic tuning default.

Run initialization as the intended non-root OS account. Reject an existing nonempty directory. Do not delete data or rerun initdb to repair an existing server.

Example, on a dedicated fresh lab directory:

~~~bash
initdb -D "$PG_INIT_LAB_ROOT/data" \
  -U init_lab_admin --pwprompt \
  --auth-local=scram-sha-256 --auth-host=scram-sha-256 \
  --encoding=UTF8 --locale-provider=libc --locale=C \
  --data-checksums
~~~

The password is prompted rather than placed on the command line. This chapter's isolated initialization directory is not started; checks can run offline.

## 4. Checksums: detection, not repair

PostgreSQL 18 enables data checksums by default during initialization. The lab specifies the option explicitly to make its intent reproducible. Do not infer older clusters' settings from a new-version default.

Checksums help detect certain data-page corruption. They are not encryption, a backup, a full logical consistency guarantee or an automatic repair mechanism. Successful verification is evidence about the checked data at that point, not future safety.

Inspect a running instance:

~~~sql
SHOW data_checksums;
~~~

For an offline check:

~~~bash
pg_checksums --check -D "$PG_INIT_LAB_ROOT/data"
~~~

The server must be cleanly shut down. Use matching-major tools and the correct data directory. A scan has I/O cost; scheduling a full check on large production data is a planned operation.

A failure requires evidence preservation, storage investigation and a supported recovery plan. Do not mask it with ignore_checksum_failure, zero damaged pages or overwrite files.

Enabling/disabling checksums on an existing cluster changes persistent state and has topology implications. That procedure is outside this lab; keep primary, standbys and physical recovery workflows consistent when planning such a change.

## 5. Encoding: representation and conversion

server_encoding describes a database's stored text encoding. client_encoding determines the encoding expected on that client connection. PostgreSQL converts when supported; an unrepresentable character can produce an error.

UTF8 is a sensible baseline for these labs. SQL_ASCII should not be used as a workaround for invalid source data; it weakens validation and shifts problems elsewhere.

Inspect:

~~~sql
SHOW server_encoding;
SHOW client_encoding;
SELECT length(U&'\20AC') AS characters,
       octet_length(U&'\20AC') AS bytes;
~~~

On the UTF8 lab, the euro character has one character and three bytes. Character count and byte count are different measures.

An encoding error can occur while storage and checksums are healthy. Preserve the source data's known encoding and validate conversion before migration. Changing client_encoding does not rewrite a database's stored encoding.

## 6. Locale and collation providers

| Provider | Source of behavior | Operational consideration |
|---|---|---|
| libc | OS locale facilities | Installed locales and OS/library changes |
| ICU | ICU locale support | Build support, locale choice and library version |
| builtin | PostgreSQL-provided behavior | Supported version/provider locale names |

PostgreSQL 18 supports builtin provider locales including C, C.UTF-8 and PG_UNICODE_FAST. Do not apply these options blindly to older versions.

Locale influences text sorting and character classification. A byte-oriented C collation is different from language-specific linguistic ordering. Nondeterministic collation choices can also affect equality semantics; select them intentionally with application owners.

Inventory OS libc locales with locale -a, but do not treat that list as the complete list of ICU or builtin provider choices.

Two databases with UTF8 can still sort/classify text differently because their providers/locales differ. Conversely, a small sample producing the same order does not prove two collations equivalent.

## 7. Database creation and compatibility boundaries

On the disposable primary, separate standalone statements can create comparison databases:

~~~sql
CREATE DATABASE chapter007_libc
  TEMPLATE template0 ENCODING 'UTF8'
  LOCALE_PROVIDER libc LOCALE 'C';

CREATE DATABASE chapter007_builtin
  TEMPLATE template0 ENCODING 'UTF8'
  LOCALE_PROVIDER builtin LOCALE 'C'
  BUILTIN_LOCALE 'PG_UNICODE_FAST';
~~~

Confirm the names are unused before execution. CREATE DATABASE cannot run inside an explicit transaction block. Use separate psql commands or an interactive session; do not combine them into a single multi-statement -c request.

Database encoding and core locale/provider properties are chosen at creation. Changing them for existing data generally requires a planned migration/rebuild rather than a session SET. Physical replication does not provide an independent locale experiment on a standby.

## 8. Collation version drift

An OS or ICU upgrade can change collation definitions used by indexes and other objects. Recorded versus actual provider version is useful evidence, where available.

A mismatch warning is not fixed merely by refreshing its recorded version. Identify affected objects, rebuild them appropriately, verify behavior and then refresh metadata through the supported procedure. Refreshing alone does not validate the rebuild.

Database default collations and named collation objects have related but distinct refresh operations. Use the correct scope and dependencies. Production reindexing can have lock, I/O and availability implications; it belongs in a reviewed change plan.

Do not induce a version mismatch by editing catalogs or library files in this lab. Capture metadata and explain the recovery order instead.

## 9. Bounded inspection

Run the companion SQL using the approved observer:

~~~bash
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -f postgresql/scripts/007-initialization-inventory.sql
~~~

Expected: current encoding/checksum settings and database locale/provider records. Null collation version values can be legitimate for unversioned providers/locales; they are not automatically a mismatch.

The catalog fields in this script target PostgreSQL 18. Adapt for older versions rather than assuming identical column names. On a managed service, use the provider-supported versions and privileges; initdb/pg_checksums may be inaccessible.

## 10. Production procedure and troubleshooting

**Prechecks:** version/build, clean target, owner, mounts, locale availability, template compatibility and authentication policy.

**Stop conditions:** unexpected existing data, wrong tool major, unsupported provider, incompatible locale/encoding, checksum failures or unknown topology.

**Verification:** retain initialization output, checksum result and connected metadata. Check representative text behavior and restore/migration assumptions before production acceptance.

**Rollback:** a newly created disposable database can be dropped after closing its sessions. Changing an existing database's encoding/collation or checksum policy is not undone by restoring a shell variable. Preserve backups and use a planned recovery workflow.

| Symptom | Safe next step |
|---|---|
| initdb refuses root/nonempty directory | Correct OS identity or choose a new verified-empty target |
| Locale unavailable | Confirm provider and installed locale inventory |
| Template incompatibility | Use reviewed template0 creation with explicit choices |
| ICU unsupported | Verify build/provider; do not silently substitute behavior |
| Character cannot be represented | Diagnose source/target encoding rather than storage corruption |
| pg_checksums refuses running cluster | Schedule a clean shutdown of the correct target |
| Version mismatch warning | Plan dependent-object rebuild before metadata refresh |

Monitor checksum failures and collation warnings through logs/statistics with owned escalation. No failures should be normalized away.

Complete the linked lab; execution evidence is required for verification.

**Next:** Chapter 008 — Configuration Precedence, Reloads and Restarts.

## 11. Official references

- [initdb](https://www.postgresql.org/docs/18/app-initdb.html)
- [pg_checksums](https://www.postgresql.org/docs/18/app-pgchecksums.html)
- [Locale](https://www.postgresql.org/docs/18/locale.html)
- [Collation](https://www.postgresql.org/docs/18/collation.html)
- [Character sets](https://www.postgresql.org/docs/18/multibyte.html)
- [CREATE DATABASE](https://www.postgresql.org/docs/18/sql-createdatabase.html)
- [Database catalog](https://www.postgresql.org/docs/18/catalog-pg-database.html)
- [Collation rebuild and refresh](https://www.postgresql.org/docs/18/sql-altercollation.html)
