# Chapter 012 — pg_hba.conf, Authentication and Connection Diagnosis

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18 on Linux.
**Duration:** 75–100 minutes with the lab. **Prerequisites:** Chapters 004, 009–011.
**Status:** Authored and statically reviewed; PostgreSQL lab execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](011-roles-ownership-membership-and-least-privilege.md) · [Hands-on lab](../labs/012-hba-authentication-and-connection-diagnosis-lab.md) · [Inspection SQL](../scripts/012-authentication-inspection.sql) · [Guarded lab helper](../scripts/012-hba-lab.py)

## 1. Operational problem and objectives

A service reports “database unavailable.” The database process is healthy, but a newly deployed client connects through a different address or transport. Another service has an expired credential. During remediation, a broad HBA allow rule is appended below a reject rule and nothing improves.

The operator's task is to identify the failing connection stage and the specific rule, identity or client setting responsible. This chapter teaches HBA selection, password-method compatibility, client credential lookup and evidence-based diagnosis. Its lab creates narrow, reversible failures while preserving administrative and replication access.

Success means you can distinguish reachability, transport negotiation, authentication, database admission and object authorization. You can repair the relevant layer and prove recovery using a fresh connection from the affected identity.

## 2. Diagnose the connection in stages

Use explicit endpoint, port, database and role values. Record the actual application driver version and connection options; a local psql connection may take a different path.

| Stage | Evidence | Typical failure |
|---|---|---|
| Name/address resolution | Resolved addresses and selected target | Wrong DNS result, IPv4/IPv6 mismatch |
| Listener/network | Listener owner, route/firewall, bounded connection attempt | Refused connection or timeout |
| Encryption negotiation | Client TLS/GSS settings and server support | Certificate verification or protocol failure |
| HBA selection | Transport, source address, database, login role and rule order | No applicable rule or explicit rejection |
| Authentication | Method, account eligibility and credential source | Wrong password, incompatible verifier/client, peer mismatch |
| Database admission | Requested database and CONNECT privilege | Missing database or permission denied |
| Session/operation | Effective role, object privileges and SQLSTATE | Relation/schema/sequence permission denied |

The server-visible source address may be a proxy, pooler or NAT address. Inspect it from the actual path rather than assuming the application's pod IP is what HBA sees. With a pooler, distinguish application-to-pooler authentication from pooler-to-PostgreSQL authentication.

pg_isready provides server readiness information. It does not prove that the named user authenticated or can use the database. Use a bounded authenticated SQL probe, then a representative application operation. A connection failure's client exit code alone is too broad to identify its cause.

## 3. HBA is an ordered connection policy

Discover the active HBA path with SHOW hba_file. It need not be inside the data directory. Review includes, rule order and file ownership before editing.

A rule describes connection type, database, user, address where applicable, authentication method and optional method-specific controls. PostgreSQL selects the first matching rule. Authentication failure at that rule does not fall through to a later allow rule. If nothing matches, access is denied.

| Record type | Applies to | Operational implication |
|---|---|---|
| local | Unix-domain sockets | No network address field; may use peer or password authentication |
| host | TCP connections | Can match encrypted and unencrypted traffic |
| hostssl | TLS TCP connections | Requires server TLS support/configuration |
| hostnossl | TCP without TLS | Useful for an explicit non-TLS policy |
| hostgssenc / hostnogssenc | TCP classified by GSS encryption | Review client/server GSS settings separately |

A hostssl rule does not force all traffic to use TLS if a later host rule still allows unencrypted connections. Enforce the intended complete policy and verify actual client transport; certificate setup and verification are Chapter 013.

The address field matches the server-observed client address. IPv4 and IPv6 entries have distinct matching behavior. Using localhost may resolve to a different address family than an explicit 127.0.0.1 connection. Hostname HBA rules also depend on forward/reverse resolution.

Database replication matches physical replication connections, not logical replication's ordinary database connection. A user entry prefixed with + matches role membership, while a bare name matches that named login. Keep replication rules explicit and test reconnects after a policy change.

PostgreSQL 18 supports HBA includes and include-directory ordering. File layout does not make overlapping rules independent: evaluate the resulting sequence. Avoid overly broad rules that obscure a narrower intended policy.

## 4. Read the disk view without confusing it with loaded policy

pg_hba_file_rules exposes rule order, source file/line, matching fields, method and parse errors. By default its access is restricted to superusers. The chapter's inspection script is read-only and uses short statement/lock timeouts.

~~~sql
SHOW hba_file;
SELECT rule_number,file_name,line_number,type,database,user_name,
       address,auth_method,error
FROM pg_hba_file_rules
ORDER BY rule_number NULLS LAST,file_name,line_number;
~~~

This view reads the current files. It is not a history of the last successfully loaded configuration or a record of the rule selected for every connection. Parsing cleanly also does not establish that a rule is correctly scoped.

On Linux, reload the server after a reviewed HBA change. A reload signal does not disconnect existing sessions. Verify new connections because retained pool sessions can hide a broken admission policy.

If HBA reload fails due to an invalid file, the server can retain the previously loaded valid rules. The lab demonstrates this deliberately: disk inspection reports an error while an authenticated connection still succeeds. Do not restart an instance with known invalid HBA contents. On Windows, subsequent connections apply HBA changes differently; the Linux reload exercise is not a Windows procedure.

A true pg_reload_conf() result reports signal delivery, not complete policy acceptance. Use server logs, error-free file inspection and actual positive/negative client probes together.

## 5. Password methods and account state

For self-managed password authentication, prefer SCRAM with compatible clients and a reviewed migration plan. PostgreSQL 18 deprecates MD5 password support.

| Method | Reliability/security consideration |
|---|---|
| scram-sha-256 | Requires a SCRAM verifier and compatible client |
| md5 | Deprecated; a SCRAM-stored password can trigger SCRAM even with this HBA method |
| password | Sends the password in clear form at the protocol layer; requires a protected transport |
| peer | Uses the local OS identity on supported socket connections, optionally through mapping |
| cert / external methods | Require separate certificate/identity-provider policy and dependency checks |
| trust | Accepts the claimed identity without password verification; not a routine incident workaround |

password_encryption controls how newly set passwords are stored. Changing it does not convert existing stored passwords. Reset credentials through an approved secret-rotation process, check client support, then verify fresh connections.

Inspect rolcanlogin, password expiry and the intended login identity. Password expiry governs password authentication, not every external authentication mechanism, and does not terminate existing sessions. A role's LOGIN attribute and database/object privileges remain separate concerns.

Do not publish password verifiers or dump pg_authid to diagnose an ordinary incident. Server-side details may be more specific than the client error; correlate protected logs with time, identity and endpoint.

## 6. Credential lookup and transport traps

Libpq can obtain settings from connection arguments, service files and environment variables. Hidden PGOPTIONS, PGSERVICE or password settings can make a copied command behave differently. Record safe parameter names and sources; redact secret-bearing URLs and strings.

A password file uses host:port:database:user:password entries and selects the first matching entry. Wildcards and ordering can select an unintended credential. Unix permissions must prevent group/world access, or the password file is ignored. Escape colon/backslash characters when constructing general entries.

With an explicitly selected nondefault Unix-socket directory, password-file lookup uses that host path. Libpq also searches localhost when the socket path matches its compiled default, or no host/hostaddr is specified. The Chapter 004 password file contains explicit 127.0.0.1 entries, so this lab's custom socket directory needs its own matching credential entry even though its local HBA method is also SCRAM. Changing transport can change both the HBA rule and the password-file match.

psql -w disables password prompting; it does not guarantee that a password was supplied. A missing credential produces a client-side failure rather than proof of a server password mismatch. psql -W prompts, but a prompt alone does not establish that the chosen server rule requires password authentication.

The lab uses explicit loopback targets, fresh sessions and private probe files. It never prints real passwords or embeds them in SQL.

## 7. Safe policy change procedure

1. Identify the instance, actual HBA path, deployment owner and affected client path.
2. Preserve a protected backup and establish an out-of-band operating-system recovery path. Keep a verified administrator session open.
3. Inventory current matching rules, includes, account state, encryption mode and replication requirements.
4. Stage a narrowly scoped change through the owning configuration system. Check file parsing before reload.
5. Reload through the authorized control path. Inspect logs and test fresh authorized, rejected and administrative connections.
6. Verify replication reconnect capability, pool reconnection and application operations. An existing streaming connection alone does not test admission.
7. Record evidence, remove temporary exceptions and retain a reviewed rollback source.

**Stop conditions:** unknown HBA path, uncertain source address, missing recovery access, parse errors, concurrent configuration writers, unintended weakening of transport/authentication, or a proposal to add broad trust access. Do not broaden the network policy to compensate for the wrong credential.

**Rollback:** restore the exact reviewed file/include set, reload and verify fresh connections. Restoring disk contents alone does not prove that the running policy reverted. If SQL access is lost, use the established OS control path to restore/reload; do not disable authentication globally.

## 8. Incident diagnosis and signals

| Symptom | Next evidence | Targeted action |
|---|---|---|
| Connection refused | Listener/port and instance status | Correct endpoint or startup problem |
| Connection timeout | Route, firewall and server load | Isolate network/acceptance delay |
| No HBA entry / explicit reject | Actual tuple and ordered policy | Repair the intended scoped rule |
| Password authentication failed | Credential source, account state, method/client support | Correct or rotate the affected credential |
| Peer authentication failed | OS identity, requested role and mapping | Use the intended local identity or transport |
| Missing password under -w | Passfile match, permissions and settings | Supply the correct protected credential source |
| Database CONNECT denied | Effective database privilege | Repair the reviewed database grant |
| Object permission denied | Schema/table/sequence and memberships | Follow Chapter 011 authorization diagnosis |
| Rules parse cleanly, app still denied | Loaded-state evidence and actual client path | Check reload and connection tuple |
| Disk has errors, app still connects | Reload error and previous policy | Restore valid contents before any restart |

Monitor authentication failures by identity/source, rejected admission, connection latency, HBA reload errors and dependency failures for external authentication. Correlate with recent deployment/secret changes. Avoid putting passwords or full sensitive connection strings into alert labels.

## 9. Acceptance and official references

Acceptance requires expected TCP/socket logins, correct classification of missing/wrong credentials, first-match rejection without fallback, existing-session behavior, invalid-reload evidence, restoration and a fresh replication reconnect check. The lab's no-TLS loopback transport is a disposable baseline; it does not validate a production TLS policy.

- [HBA configuration](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)
- [HBA inspection view](https://www.postgresql.org/docs/18/view-pg-hba-file-rules.html)
- [Authentication methods](https://www.postgresql.org/docs/18/auth-methods.html)
- [Password authentication](https://www.postgresql.org/docs/18/auth-password.html)
- [Peer authentication](https://www.postgresql.org/docs/18/auth-peer.html)
- [Libpq connection parameters](https://www.postgresql.org/docs/18/libpq-connect.html)
- [Password files](https://www.postgresql.org/docs/18/libpq-pgpass.html)
- [pg_isready](https://www.postgresql.org/docs/18/app-pg-isready.html)

**Next:** Chapter 013 — TLS Certificates, Verification and Rotation.
