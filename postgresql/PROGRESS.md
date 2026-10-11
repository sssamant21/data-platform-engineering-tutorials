# PostgreSQL DBRE/SRE Tutorial Progress

Status definitions: **Planned** = curriculum entry only; **Authored** = chapter and lab written; **Reviewed** = content and static checks reviewed; **Lab verified** = actual execution evidence retained. Completion requires lab verification as described in the master plan.

| Chapter | Content | Review | Lab execution | Publication |
|---|---|---|---|---|
| [001](chapters/001-postgresql-responsibilities-for-dbre-and-sre.md) | Authored | Static links, fences and bounded SQL reviewed | Pending; no PostgreSQL runtime available in authoring environment | Published with this tracker |
| [002](chapters/002-architecture-processes-memory-storage-and-wal.md) | Authored | Static review | Pending; no PostgreSQL runtime in authoring environment | Published with this tracker |
| [003](chapters/003-linux-networking-and-storage-prerequisites.md) | Authored | Bash syntax, fences and cross-links reviewed | Pending; target-host and PostgreSQL lab not executed | Published with this tracker |
| [004](chapters/004-build-a-reproducible-postgresql-operations-lab.md) | Authored | Bash/Python syntax, help command and cross-links reviewed | Pending; no PostgreSQL runtime available | Published with this tracker |
| [005](chapters/005-psql-system-catalogs-and-safe-administrative-sql.md) | Authored | Bash syntax, fences, links and metadata SQL reviewed | Pending; no PostgreSQL runtime available | Published with this tracker |
| [006](chapters/006-installation-packages-and-directory-layout.md) | Authored | Bash syntax, links and metadata SQL reviewed | Pending; package installation/runtime not performed | Published with this tracker |
| [007](chapters/007-initialization-checksums-locale-and-encoding.md) | Authored | Bash/Python syntax, links and metadata SQL reviewed | Pending; PostgreSQL runtime not available | Published with this tracker |
| [008](chapters/008-configuration-precedence-reloads-and-restarts.md) | Authored | Bash syntax, links and metadata SQL reviewed | Pending; activation/restart lab not executed | Published with this tracker |
| [009](chapters/009-systemd-startup-shutdown-and-crash-recovery.md) | Authored | Bash syntax, links, fences and metadata SQL reviewed | Pending; service lifecycle/crash-recovery lab not executed | Published with this tracker |
| [010](chapters/010-configuration-drift-and-baseline-acceptance.md) | Authored | Bash/Python syntax, comparison-helper synthetic cases, links and bounded SQL reviewed | Pending; drift and baseline acceptance lab not executed | Published with this tracker |
| [011](chapters/011-roles-ownership-membership-and-least-privilege.md) | Authored | Links, fences, PG18 membership semantics and bounded SQL manually reviewed; no shell/SQL parser available | Pending; role and privilege lab not executed; execution environment unavailable | Published with this tracker |
| [012](chapters/012-pg-hba-conf-authentication-and-connection-diagnosis.md) | Authored | Bash/Python syntax, links, fences and bounded SQL reviewed; 12 helper filesystem fixture cases (top-level lab guard mocked) plus root-refusal check passed | Pending; authentication/HBA reload and reconnect lab not executed; no PostgreSQL runtime | Published with this tracker |
| [013](chapters/013-tls-certificates-verification-and-rotation.md) | Authored | Bash/Python syntax, links and bounded SQL reviewed; OpenSSL certificate fixtures and 5 peer-probe cases against a simulated SSLRequest endpoint passed; fixture generation bypassed the OS guard | Pending; PostgreSQL TLS authentication/reload/rotation lab not executed; no PostgreSQL runtime | Published with this tracker |
| [014](chapters/014-secrets-rotation-and-service-account-lifecycle.md) | Authored | Bash syntax, links, fences and SQL structure manually reviewed; read-only inventory, rollback probes and scoped session filters checked; no SQL parser | Pending; password/expiry/NOLOGIN/session-retirement lab not executed; no PostgreSQL runtime | Published with this tracker |
| 015–100 | Planned | Pending | Pending | Plan only |

**Next:** Chapter 015 — Audit Logging, Network Isolation and Security Acceptance.
