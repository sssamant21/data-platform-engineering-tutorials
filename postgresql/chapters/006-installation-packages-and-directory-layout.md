# 006 — Installation, Packages and Directory Layout

[Master plan](../MASTER-PLAN.md) · [Previous chapter](005-psql-system-catalogs-and-safe-administrative-sql.md) · [Hands-on lab](../labs/006-package-and-directory-inventory-lab.md) · [Path inventory SQL](../scripts/006-path-inventory.sql)

## 1. Operational problem and objectives

“PostgreSQL is installed” does not establish which server binaries a service uses, which data directory it owns or whether the client on PATH matches the intended major version.

An installation can contain several PostgreSQL majors and multiple instances. Package installation, database initialization and service startup are separate lifecycle events, although some distributions combine them automatically.

**Audience:** DBRE/SRE only. **Reference major:** PostgreSQL 18. **Prerequisites:** Chapters 001–005 and an isolated Linux VM or the Chapter 004 environment. **Effort:** 60–90 minutes.

By the end you should be able to choose a supported installation source, review package changes, identify binary provenance, map live configuration/data paths and distinguish package rollback from data recovery.

## 2. Choose the deployment and source

| Installation route | Suitable use | Operational requirement |
|---|---|---|
| Distribution packages | Standard OS-managed deployments | Confirm available PostgreSQL major and vendor lifecycle |
| PostgreSQL project repository packages | Explicit major versions and project package stream | Approved signed repository, OS/architecture support and patch policy |
| Source build | Controlled custom requirements | Reproducible build, dependency and patch ownership |
| Container image | Container/operator deployment | Pin image identity, inspect entrypoint behavior and persistent storage |
| Managed service | Provider-operated engine | Use provider-supported versions, upgrade policy and responsibility boundary |

This chapter's installation exercise uses Debian/Ubuntu packages on a fresh disposable VM. The existing Chapter 004 lab can take the inventory-only route. RPM-family notes explain the corresponding differences; they are not a second mandatory installation.

Use the official distribution-specific download page to confirm current support before adding a repository. Do not guess a repository URL from another OS release or disable signature verification.

A generic package named postgresql may select the distribution's default major rather than 18. Select the explicit major package when using this curriculum.

## 3. Pre-installation evidence and boundaries

On the intended lab host:

~~~bash
date -u
cat /etc/os-release
uname -m
command -v psql || true
command -v postgres || true
systemctl list-units --type=service --all 'postgresql*'
ss -ltn
~~~

Record existing packages, instances, listeners and data locations before changing anything. If this is not an empty disposable host, use the inventory-only route unless an approved change plan covers it.

Installation requires an administrator. PostgreSQL initialization and the Chapter 004 script require the intended non-root database/lab account.

Reserve storage and identify mount points before starting an instance. Do not let a missing data mount redirect an initialization into the wrong filesystem.

## 4. Debian/Ubuntu installation example

First confirm your actual distribution release and architecture are supported by the official PostgreSQL Apt repository.

On a fresh lab VM, the project documents a packaged repository helper:

~~~bash
sudo apt update
sudo apt install postgresql-common
~~~

Review the installed helper and the repository changes it proposes:

~~~bash
less /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt update
~~~

The helper path is for the PostgreSQL project Apt workflow. If it is absent or the release is unsupported, stop and follow the current official instructions rather than downloading a substitute script from an unrelated source.

Inspect candidates and simulate installation:

~~~bash
apt-cache policy postgresql-18 postgresql-client-18
sudo apt-get -s install postgresql-18 postgresql-client-18
~~~

Expected: packages available from the approved source and a reviewed set of planned dependencies. Stop if the plan unexpectedly removes packages or affects an existing instance.

Install:

~~~bash
sudo apt install postgresql-18 postgresql-client-18
~~~

Server package installation can initialize or start a default instance through distribution tooling. Inspect the actual outcome; do not assume installation was binary-only.

~~~bash
pg_lsclusters
dpkg-query -W postgresql-18 postgresql-client-18 postgresql-common
dpkg -L postgresql-18
~~~

pg_lsclusters reports Debian-family cluster metadata, including major, name, port, status and paths. It is not a universal PostgreSQL command.

If a default package-managed instance exists, record it as a separate instance. Do not delete it to make this tutorial match an expected screenshot. Chapter 004's manual instances use different ports and directories.

## 5. RPM-family equivalent

For RHEL/Rocky/AlmaLinux and related systems, choose the exact platform, release and architecture on the official PostgreSQL RPM download page. Follow the generated repository setup for that platform.

After the approved repository is configured, inspect versioned candidates. For a PGDG installation, versioned packages commonly use names such as postgresql18 and postgresql18-server:

~~~bash
dnf info postgresql18 postgresql18-server
sudo dnf install --assumeno postgresql18 postgresql18-server
~~~

The assume-no command is a review step and can exit without performing a transaction. Install only after reviewing the candidate source and dependency plan:

~~~bash
sudo dnf install postgresql18 postgresql18-server
rpm -q postgresql18 postgresql18-server
rpm -ql postgresql18-server
~~~

Use package metadata as the authority for actual paths and service names. Distribution packages can use unversioned names and different layout.

Module-stream handling, initialization helpers and service enablement vary by OS/package source. Do not universally disable module streams or run an initialization helper over an existing data directory. Follow the selected repository's platform-specific instructions.

For the Chapter 004 manual lab, installing correct binaries is sufficient; its script initializes its own fresh directories. Package-managed service initialization and startup are covered separately.

## 6. Binary identity and PATH

Common examples, to verify rather than assume:

| Installation | Possible binary directory |
|---|---|
| Debian/Ubuntu versioned packages | /usr/lib/postgresql/18/bin |
| PGDG RPM versioned packages | /usr/pgsql-18/bin |
| Custom source build | Chosen installation prefix/bin |
| Container | Image-specific filesystem path |

Inspect:

~~~bash
type -a psql
command -v psql
psql --version
postgres --version
initdb --version
pg_ctl --version
pg_basebackup --version
~~~

Some distributions provide wrappers or symlinks. Package ownership and the running service executable give stronger evidence than an unqualified command name.

If installed, pg_config identifies one build's installation directories:

~~~bash
pg_config --version
pg_config --bindir
pg_config --sharedir
pg_config --pkglibdir
~~~

pg_config on PATH can describe a different installed build; it is not a query against the running database. It can also be absent when the corresponding package is not installed.

The connected server's version is authoritative for that endpoint:

~~~sql
SELECT current_setting('server_version') AS server_version,
       current_setting('server_version_num') AS server_version_num;
~~~

A client and server reporting different versions is a compatibility/ownership item, not automatic proof of failure. For these labs use the selected PostgreSQL 18 binaries consistently and record exact minor versions.

## 7. Directory map: discover from the running instance

| Category | How to identify it | Operational purpose |
|---|---|---|
| Binaries | Package file list and executable path | Patch/build provenance |
| Main configuration | config_file | Effective configuration entrypoint |
| Authentication | hba_file and ident_file | Connection and identity rules |
| Data | data_directory | Database files and internal state |
| WAL | Data directory/pg_wal, with resolved links | Recovery and retention capacity |
| Tablespaces | pg_tablespace and actual target paths | Additional persistent storage |
| Logs | Collector settings or service/container logging | Incident evidence and retention |
| Extensions | Available/installed extension metadata and matching packages | Compatibility and upgrade planning |
| Backups | Backup-tool configuration/inventory | Recovery chain and isolation |

Configuration can be outside the data directory. PGDATA or a service -D option can refer to the directory used to locate configuration, while data_directory points elsewhere. Discover effective settings rather than equating every path.

postgresql.auto.conf holds ALTER SYSTEM overrides. Include it in configuration review; precedence is covered in Chapter 008.

On the server host, resolve any WAL symlink and inspect actual tablespace mounts. Do not equate a tablespace entry with verified free space or assume a copied data directory includes externally located configuration and tablespaces.

Log directory settings are relevant when the logging collector is used. Without it, logs may belong to systemd, a container runtime or an operator. A relative log_directory is interpreted relative to the data directory.

## 8. Extensions and version provenance

~~~sql
SELECT extname,extversion FROM pg_catalog.pg_extension ORDER BY extname;
SELECT name,default_version,installed_version
FROM pg_catalog.pg_available_extensions
ORDER BY name LIMIT 30;
~~~

Available extension files and installed database extensions are different inventories. Some extensions also require matching shared libraries, preload settings or restart. Do not issue CREATE EXTENSION merely because a package is available.

Record the package source, complete package versions, repository configuration, OS release, architecture and installed extension versions. Retain a reproducible manifest without credentials.

Pin the exact versions used for acceptance evidence. Separately define how supported minor updates will be reviewed and rolled out; a permanently frozen vulnerable package is not a patch policy.

## 9. Production procedure and recovery boundaries

**Prechecks:** inventory existing instances, confirm approved source, inspect dependency plan, verify storage mounts, prepare backups and define restart impact.

**Stop conditions:** unsupported platform, unverified signature, missing candidate, package removal surprises, wrong major, unknown data-directory ownership or unplanned service changes.

**Verification:** check installed package identity, actual service/endpoint, server version, directory mapping and application connectivity. An installed package does not prove the service is usable.

**Rollback:** repository/package changes and database state are different. Reinstalling an older major cannot make a newer-major data directory compatible. Do not downgrade binaries over incompatible data or purge packages as a substitute for recovery. Use a reviewed upgrade/migration recovery plan.

For this disposable lab, leave newly installed binaries available for later chapters. Only remove a lab instance through the guarded Chapter 004 cleanup. Do not remove shared repositories, packages or default instances automatically.

## 10. Troubleshooting and acceptance

| Symptom | Evidence and next action |
|---|---|
| No PostgreSQL 18 candidate | Verify OS/architecture and approved repository metadata |
| Wrong psql version | Inspect wrappers, PATH and package ownership |
| Binary installed; service absent | Initialization/startup may be separate; inspect package workflow |
| SQL path differs from expected package path | Effective configuration or custom instance; map it explicitly |
| Default instance already running | Record it separately; do not overwrite |
| Extension library fails to load | Compare extension package, server major and runtime library path |
| Package review proposes removals | Stop and reconcile dependencies with platform owner |

Complete the inventory lab and record package provenance and live path mapping. Actual installation/runtime evidence is required before marking lab verified.

**Next:** Chapter 007 — Initialization, Checksums, Locale and Encoding.

## 11. Official references

- [Ubuntu packages](https://www.postgresql.org/download/linux/ubuntu/)
- [Debian packages](https://www.postgresql.org/download/linux/debian/)
- [RPM-family packages](https://www.postgresql.org/download/linux/redhat/)
- [PostgreSQL 18 file locations](https://www.postgresql.org/docs/18/runtime-config-file-locations.html)
- [Database file layout](https://www.postgresql.org/docs/18/storage-file-layout.html)
- [pg_config](https://www.postgresql.org/docs/18/app-pgconfig.html)
- [Versioning and upgrade policy](https://www.postgresql.org/support/versioning/)
- [Debian pg_lsclusters](https://manpages.debian.org/trixie/postgresql-common/pg_lsclusters.1.en.html)
