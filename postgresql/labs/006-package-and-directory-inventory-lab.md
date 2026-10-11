# Lab 006 — Package and Directory Inventory

[Chapter 006](../chapters/006-installation-packages-and-directory-layout.md) · [Inventory SQL](../scripts/006-path-inventory.sql)

## Objective and routes

Build an evidence-backed installation manifest and live-instance directory map.

**Reference:** PostgreSQL 18 on Linux. Use the running Chapter 004 lab for inventory-only execution, or a separate fresh Debian/Ubuntu VM for the installation route.

Choose and record exactly one route:

- **Inventory-only:** no package changes; identify installed binaries, packages and a running lab instance.
- **Fresh installation plus inventory:** review and perform the chapter's approved repository/package procedure on a disposable VM, then initialize the Chapter 004 lab as the non-root lab account.

Do not run package installation against an existing production host for this exercise. Root/administrator access is only needed for the installation route; runtime inspection uses authorized accounts.

## 1. Record the baseline

On the intended database host:

~~~bash
mkdir -p evidence/chapter006
date -u
cat /etc/os-release
uname -m
type -a psql
systemctl list-units --type=service --all 'postgresql*'
~~~

If psql or systemd is absent, record that fact and use the chosen platform's appropriate tools. Do not conceal missing prerequisites as successful checks.

For Debian/Ubuntu, collect:

~~~bash
dpkg-query -W postgresql-18 postgresql-client-18 postgresql-common
apt-cache policy postgresql-18 postgresql-client-18
pg_lsclusters
~~~

For a PGDG RPM installation, collect the corresponding versioned package query and repository information. Unversioned distribution packages require their actual names.

## 2. Installation route, if selected

Review the official repository support list for your exact OS and architecture. Follow Chapter 006's helper, candidate review, package simulation and installation steps.

Record:

- Repository/source and signature-verification policy.
- Complete candidate package versions.
- Dependency plan before installation.
- Actual installed versions afterward.
- Any automatically initialized or started instance.
- Service/listener changes compared with baseline.

Expected: PostgreSQL 18 server/client packages from the approved source. If candidates are absent, signatures fail or the transaction has unexpected removals, stop.

After installation, use Chapter 004's script as the non-root lab account to create its separate primary/standbys. Do not initialize over a default package-managed data directory.

Inventory-only learners skip this mutation step and label package installation **not performed**.

## 3. Verify executable provenance

~~~bash
command -v psql
command -v postgres
command -v initdb
command -v pg_ctl
psql --version
postgres --version
initdb --version
pg_ctl --version
pg_basebackup --version
~~~

If needed, select the verified major-18 directory in PATH as described in the chapter.

On Debian-family installations, compare a wrapper and a versioned executable:

~~~bash
dpkg -S "$(command -v psql)"
dpkg -S /usr/lib/postgresql/18/bin/psql
~~~

The first path can belong to postgresql-common while the second belongs to the versioned client package. Interpret the evidence rather than requiring identical package ownership.

On RPM installations use rpm -qf with the actual executable path. A source build may have no package owner; record its build provenance instead.

If available:

~~~bash
pg_config --version
pg_config --bindir
pg_config --pkglibdir
~~~

Record whether this pg_config belongs to the selected major. Do not infer the running server version solely from it.

## 4. Inspect the actual Chapter 004 primary

Use your actual PG_LAB_ROOT:

~~~bash
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5
export PGAPPNAME=chapter006-inventory

psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -f postgresql/scripts/006-path-inventory.sql \
  > evidence/chapter006/paths.txt \
  2> evidence/chapter006/paths-errors.txt
echo $?
~~~

Expected: status 0 and settings/tablespace/extension results. If restricted values are hidden or a function is denied, document the boundary and have an approved settings reader collect that section.

The Chapter 004 manual lab usually has configuration inside its data directory. A package-managed instance may use external configuration paths. Record actual values; neither layout is universally required.

The default pg_default and pg_global tablespaces normally have empty external locations. An empty value is not evidence of missing storage.

## 5. Map SQL paths to filesystem paths

On the actual lab host, use the exact data_directory value:

~~~bash
PG_LAB_DATA_PATH="$PG_LAB_ROOT/primary"
ls -ld "$PG_LAB_DATA_PATH"
cat "$PG_LAB_DATA_PATH/PG_VERSION"
readlink -f "$PG_LAB_DATA_PATH/pg_wal"
findmnt -T "$PG_LAB_DATA_PATH"
df -hT "$PG_LAB_DATA_PATH"
~~~

Expected: owned data directory, major 18, resolved WAL location and backing mount.

For this lab, pg_wal is normally an ordinary directory; readlink -f still resolves the path. If your deployment has a separate WAL target or external tablespace, inspect its actual target and mount independently.

Confirm the paths returned for config_file, hba_file and ident_file exist on the server. Inspect directory/file metadata rather than exporting sensitive configuration contents.

## 6. Compare package and lab lifecycle

On Debian-family systems, pg_lsclusters may list only package-managed clusters, not Chapter 004's manual instances.

Compare:

~~~bash
pg_ctl -D "$PG_LAB_ROOT/primary" status
psql -X -w -v ON_ERROR_STOP=1 \
  -h 127.0.0.1 -p 55432 -U lab_observer -d ops_lab \
  -c "SELECT current_setting('server_version'), inet_server_port(), pg_is_in_recovery();"
~~~

Expected: manual primary running, port 55432, PostgreSQL 18 and false for recovery.

Explain why absence from pg_lsclusters does not prove the manual lab is down. Likewise, a package-managed unit's status does not describe this separate manual primary.

## 7. Create the manifest

Write evidence/chapter006/installation-manifest.md:

| Field | Required evidence |
|---|---|
| Route | Inventory-only or fresh installation plus inventory |
| OS/architecture | Actual host values |
| Source | Distribution, PGDG repository, image or custom build |
| Package/build versions | Complete identifiers |
| Executables | Selected paths and ownership |
| Server endpoint/version | Authenticated SQL result |
| Data/config/authentication | Effective paths |
| WAL/tablespaces | Resolved locations and mounts |
| Logs | Collector/service/runtime destination |
| Extensions | Available versus installed distinction |
| Service supervision | Package manager, manual pg_ctl or runtime |
| Patch policy | Accountable owner and approved review process |
| Gaps | Unknowns with owner and follow-up |

Do not put passwords or full sensitive configuration in the manifest.

## 8. Cleanup, troubleshooting and acceptance

No database state changes are needed for inventory. Close sessions and restore shell variables introduced for this exercise. Keep newly installed lab binaries for future chapters. If retiring the disposable Chapter 004 instances, use its guarded stop/destroy procedure.

Do not purge packages, delete default clusters or remove shared repositories as an automatic cleanup step.

Pass when:

- The selected route is documented truthfully.
- Package/build source and exact versions are known.
- Client executable identity is distinguished from server identity.
- Effective data/config/WAL paths map to the actual server filesystem.
- Package-managed and manual instance inventories are reconciled.
- Extension availability is distinguished from installation.
- No unrelated instance or repository was changed.

Troubleshooting: missing candidate → supported repository/OS review; wrong PATH → selected major directory; unexpected cluster → inventory before action; restricted path → authorized reader; invalid mount → stop and engage platform owner.

Static authoring checks do not certify actual package installation or running PostgreSQL.
