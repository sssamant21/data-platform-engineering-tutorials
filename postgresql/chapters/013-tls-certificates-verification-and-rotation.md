# Chapter 013 — TLS Certificates, Verification and Rotation

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18 on Linux; lab OpenSSL 3.x.
**Duration:** 90–120 minutes. **Prerequisites:** Chapters 004, 008, 009 and 012.
**Status:** Authored and statically reviewed; PostgreSQL execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](012-pg-hba-conf-authentication-and-connection-diagnosis.md) · [Hands-on lab](../labs/013-tls-certificates-verification-and-rotation-lab.md) · [Certificate generator](../scripts/013-generate-lab-certificates.sh) · [Served-certificate probe](../scripts/013-tls-peer-probe.py) · [Inspection SQL](../scripts/013-tls-inspection.sql)

## 1. Operational problem and objectives

A certificate renewal succeeded on disk, yet clients still see the old leaf. Another client encrypts traffic but accepts the wrong server identity. A deployment adds hostssl while leaving a broad host rule that still admits plaintext connections.

DBRE/SRE operators must verify encryption, server identity, authentication, application access and renewal behavior. This chapter teaches certificate/key/chain validation, client verification modes, HBA enforcement and a measured rotation procedure. The lab rotates a leaf certificate and its key under one test CA and proves what a fresh connection actually receives.

## 2. Separate encryption, identity and authentication

| Requirement | Evidence | What it does not prove |
|---|---|---|
| Encrypted database session | pg_stat_ssl for the authenticated backend | Correct name or trusted issuer |
| Trusted server certificate | Client chain validation against approved roots | Correct hostname unless checked |
| Intended server identity | verify-full with intended hostname/IP | Database login or SQL authority |
| Authentication | Successful SCRAM or other approved login | Every operation is authorized |
| Authorization | Representative restricted SQL | Certificate policy |
| Client certificate identity | Server-side certificate validation/mapping | Appropriate object permissions |

Server TLS does not require client certificates. The lab combines a verified server certificate with SCRAM. Mutual TLS adds a separate client certificate lifecycle and identity-mapping contract.

ssl_ca_file on the server validates client certificates. It does not distribute trust for the server's certificate to ordinary clients. Client trust comes from its driver/trust store, such as libpq sslrootcert.

## 3. Inventory certificates and keys

Record issuer/chain, subject alternative names (SANs), serial, validity, SHA-256 fingerprint, algorithm, file ownership, consumers and renewal owner. Include primary/standby endpoints, proxies and poolers that terminate TLS.

The SAN must cover the hostname or IP the client verifies. Service aliases and direct node names can require different certificates or SAN entries. Routing traffic to a new hostname does not make the old certificate valid for it.

The server certificate file starts with the leaf and may include intermediates in chain order. Clients normally receive the root through their trust store. Keep CA signing keys away from database hosts in production; the lab's private local CA is only an exercise fixture.

A server-owned private key is normally 0600 on Unix. PostgreSQL also supports a documented root-owned/group-readable arrangement. Verify the server account can traverse parent directories and read the key. Handle key backups and deployment artifacts under the approved secret policy.

Offline checks include:

~~~bash
openssl x509 -in "$TLS013/leaf-v1.crt" -noout \
  -subject -issuer -serial -dates -ext subjectAltName -fingerprint -sha256
openssl x509 -in "$TLS013/leaf-v1.crt" -checkend 86400 -noout
openssl verify -CAfile "$TLS013/ca.crt" -purpose sslserver \
  -verify_hostname postgresql-lab.invalid "$TLS013/leaf-v1.crt"
~~~

Run after lab preparation. checkend's exit status flags expiry within the selected window; choose production lead time from issuance/distribution/rollback needs rather than the lab's one-day example.

Compare certificate/key public components with a key-type-independent method. A readable certificate, valid chain and correct SAN do not prove the private key matches.

## 4. Client verification modes

| Libpq sslmode | Behavior |
|---|---|
| disable | No TLS |
| allow / prefer | Can permit non-TLS connections according to negotiation/fallback |
| require | Requires TLS; not an explicit hostname-verification contract |
| verify-ca | Requires TLS and trusted chain |
| verify-full | Adds hostname/IP verification |

For compatibility, require can perform CA verification when a root certificate file exists. Set verification explicitly instead of relying on that implicit behavior. Other drivers have their own option names and trust-store semantics; test the exact application driver/version.

When host and hostaddr are both supplied, libpq can use hostaddr as the network target while host supplies the identity for verification and credential lookup. The lab uses a reserved .invalid DNS name with an explicit loopback address, avoiding DNS/hosts-file changes.

GSS encryption can take precedence in some client configurations. The exercise explicitly disables it to make the observed TLS transport unambiguous. Unix-domain sockets do not use PostgreSQL TLS; a socket login does not validate remote TLS.

## 5. Availability and enforcement are separate

ssl=on makes TLS available on the PostgreSQL TCP endpoint. It does not reject plaintext by itself. Enforce the complete HBA policy and run negative connection tests.

For this lab, an early hostnossl reject blocks plaintext for lab_app/ops_lab. The original host SCRAM rule still admits that identity through TLS. Production can use explicit hostssl allows and narrowly reviewed rejects, but must review every overlapping rule.

Choose minimum protocol versions and cipher policy against approved client compatibility and the installed OpenSSL/PostgreSQL build. Avoid copying universal cipher strings between deployments.

pg_stat_ssl shows negotiated protocol/cipher for a session. Its client_dn/issuer_dn describe client certificate information, not the server leaf fingerprint. Observe the actual served leaf during a fresh handshake to prove renewal.

The supplied peer probe performs PostgreSQL SSLRequest negotiation at fixed loopback port 55432, validates name/chain with Python SSL and compares the returned leaf's DER fingerprint. It does not authenticate or execute SQL. Closing before database startup can produce a startup-disconnect log; correlate it with the known probe.

## 6. Rotate a leaf with evidence

1. Inventory endpoints, trust stores, current pair and intended names. Preserve a valid previous pair and rollback authority.
2. Obtain the replacement through the approved CA. Validate SAN, dates, chain, usage, key match and permissions offline.
3. Stage the complete matching pair through the deployment owner. Prevent a reload between certificate and corresponding key changes.
4. Reload through the authorized lifecycle owner and inspect logs.
5. Prove a fresh handshake returns the new fingerprint/serial, then test authenticated SQL and a representative application operation.
6. Observe client reconnects and let retained sessions drain under the deployment policy.
7. Retain evidence and retire the prior secret pair after its rollback window closes.

On the Linux baseline, certificate/key files are read at startup and reload. A reload error can retain the old loaded SSL configuration, even when disk/settings evidence describes a new proposal. A successful signal result is insufficient. Startup can fail when referenced files are invalid.

Existing sessions do not renegotiate onto the new leaf because configuration reloads. Expiry/revocation normally affects new validation/handshakes; it does not automatically terminate all existing sessions. Include reconnect behavior in acceptance.

Passphrase-protected keys require an operational passphrase command and applicable reload support. Do not assume unattended startup/reload can answer an interactive prompt. The lab uses unencrypted private keys with private filesystem permissions; production secret handling is deployment-specific.

## 7. CA rotation and mutual TLS

Replacing a CA differs from renewing a leaf under the same trusted CA. Distribute a reviewed client trust bundle with old/new roots first, verify compatibility, rotate server chains, reconnect clients, then remove old trust after the migration window. Include every alternate endpoint and pool.

For client certificates, plan server-side trust overlap, client renewal, identity mapping and revocation separately. cert authentication and SCRAM with clientcert verification have different semantics. An encrypted login alone does not establish mutual TLS.

The lab proves same-CA leaf/key rotation. It does not implement CA overlap, intermediate-chain renewal, CRL/OCSP policy or mutual TLS acceptance.

## 8. Troubleshooting and rollback

| Symptom | Evidence | Action |
|---|---|---|
| Encryption succeeds, name fails | Client host and SANs | Correct intended name/certificate |
| Unknown issuer | Client roots and served chain | Repair trust distribution/missing intermediate |
| Old leaf remains served | Fresh fingerprint and reload logs | Diagnose loading error |
| Key unreadable | Mode/owner and parent traversal | Repair approved secret access |
| Key/certificate mismatch | Public-key digests | Stage a matching pair |
| Plaintext still succeeds | Ordered HBA and exact identity | Correct full policy |
| Only pooler access works | TLS termination on each hop | Test both transport contracts |
| New sessions fail, old ones work | Rotation/reconnect timeline | Restore valid pair/policy |

Stop for an untrusted issuer, wrong identity, expired leaf, mismatched key, unknown client support or unresolved reload errors. Do not weaken verification to make renewal appear successful.

Rollback restores the previous valid pair/configuration, reloads it, verifies the served leaf and tests fresh SQL. An expired or compromised old certificate is not a valid rollback target; use approved emergency issuance/containment.

Monitor expiry, unexpected issuer/fingerprint, reload errors, verification failures and plaintext-policy violations. Renewal lead time must cover distribution and retry contingencies. Never put private keys or sensitive connection strings in alert labels.

## 9. Acceptance and references

Pass requires verified encrypted SCRAM, correctly classified wrong-CA/name failures, plaintext rejection, v1→v2 served-leaf evidence, retained-session/reconnect behavior, rollback and original-lab restoration. PostgreSQL runtime evidence remains pending until execution.

- [Server TLS](https://www.postgresql.org/docs/18/ssl-tcp.html)
- [Libpq verification](https://www.postgresql.org/docs/18/libpq-ssl.html)
- [Connection/TLS settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [HBA](https://www.postgresql.org/docs/18/auth-pg-hba-conf.html)
- [TLS negotiation](https://www.postgresql.org/docs/18/protocol-flow.html)
- [OpenSSL req](https://docs.openssl.org/3.0/man1/openssl-req/)
- [OpenSSL x509](https://docs.openssl.org/3.0/man1/openssl-x509/)
- [Python SSL](https://docs.python.org/3/library/ssl.html)

**Next:** Chapter 014 — Secrets Rotation and Service Account Lifecycle.
