# Lab 013 — TLS Verification and Certificate Rotation

**Audience:** DBRE/SRE. **Baseline:** Chapter 004 PG18 Linux lab; OpenSSL 3.x.
**Duration:** 90–120 minutes. **PostgreSQL runtime verification:** pending.

[Chapter](../chapters/013-tls-certificates-verification-and-rotation.md) · [Setup](004-reproducible-postgresql-operations-lab.md) · [Generator](../scripts/013-generate-lab-certificates.sh) · [Peer probe](../scripts/013-tls-peer-probe.py) · [Inspection SQL](../scripts/013-tls-inspection.sql)

Use two terminals under the non-root lab OS account, from the repository's postgresql directory. This enables primary TLS and temporarily rejects plaintext for lab_app only. Administrative and replication rules stay available. Keep standbys unpromoted.

## 1. Guard and original-state evidence

~~~bash
: "${PG_LAB_ROOT:?Export the Chapter 004 disposable lab root}"
[[ "$(id -u)" != 0 ]] || exit 2
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ "$(psql --version)" =~ PostgreSQL\)\ 18\. ]] || exit 2
unset PGOPTIONS PGSERVICE PGSERVICEFILE PGPASSWORD PGHOSTADDR PGDATABASE PGTARGETSESSIONATTRS
export PGPASSFILE="$PG_LAB_ROOT/credentials.pgpass"
export PGCONNECT_TIMEOUT=5 PGSSLMODE=disable PGGSSENCMODE=disable PGAPPNAME=chapter013-lab
umask 077
TLS013="$PG_LAB_ROOT/tls-013"
lab_sql() {
  psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ops_lab "$@"
}
tls_app() {
  psql -X -w -v ON_ERROR_STOP=1 \
    -d "host=postgresql-lab.invalid hostaddr=127.0.0.1 port=55432 dbname=ops_lab user=lab_app sslmode=verify-full sslrootcert=$TLS013/ca.crt passfile=$TLS013/app.pgpass gssencmode=disable connect_timeout=5" "$@"
}
bash scripts/004-operations-lab.sh verify
[[ "$(lab_sql -Atc 'SHOW data_directory')" == "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW hba_file')" == "$PG_LAB_ROOT/primary/pg_hba.conf" ]] || exit 2
[[ "$(lab_sql -Atc 'SHOW ssl')" == off ]] || exit 2
[[ "$(lab_sql -Atc 'SELECT pg_is_in_recovery()')" == f ]] || exit 2
lab_sql -c "SELECT name,setting,source,sourcefile FROM pg_settings
WHERE name IN ('ssl','ssl_cert_file','ssl_key_file');"
lab_sql -c "SELECT sourcefile,name,setting,error FROM pg_file_settings
WHERE error IS NOT NULL OR (sourcefile LIKE '%/postgresql.auto.conf'
AND name IN ('ssl','ssl_cert_file','ssl_key_file'));"
~~~

Require no file errors or auto-conf entries for those three settings, and the original Chapter 004 values/sources. Otherwise stop: RESET must not erase a pre-existing override. Record these outputs before changing anything.

Prepare/reuse Chapter 012's guarded HBA backup:

~~~bash
if [[ ! -e "$PG_LAB_ROOT/evidence-012" ]]; then
  python3 scripts/012-hba-lab.py prepare
fi
python3 scripts/012-hba-lab.py status
bash scripts/013-generate-lab-certificates.sh
~~~

Require HBA disk state original. The generator refuses an occupied tls-013 directory. It creates a seven-day CA, two two-day leaves with different keys/serials, an unrelated CA and a private app passfile. These are disposable fixtures, not production issuance guidance.

## 2. Offline validation

~~~bash
openssl x509 -in "$TLS013/leaf-v1.crt" -noout -serial -dates -ext subjectAltName
openssl x509 -in "$TLS013/leaf-v1.crt" -checkend 86400 -noout
openssl verify -CAfile "$TLS013/ca.crt" -purpose sslserver \
  -verify_hostname postgresql-lab.invalid "$TLS013/leaf-v1.crt"
openssl x509 -in "$TLS013/leaf-v1.crt" -pubkey -noout |
  openssl pkey -pubin -outform DER | openssl dgst -sha256
openssl pkey -in "$TLS013/leaf-v1.key" -pubout -outform DER | openssl dgst -sha256
~~~

Expected matching public-key digests, valid usage/chain/name and at least one day remaining. Repeat for v2: it must match its own key and differ from v1. Stop on a mismatch.

## 3. Activate v1 and enforce app TLS

Set both paths before reloading. No concurrent configuration writer or reload is allowed:

~~~bash
lab_sql -v cert_path="$TLS013/leaf-v1.crt" -v key_path="$TLS013/leaf-v1.key" <<'SQL'
SELECT format('ALTER SYSTEM SET ssl_cert_file = %L', :'cert_path') \gexec
SELECT format('ALTER SYSTEM SET ssl_key_file = %L', :'key_path') \gexec
ALTER SYSTEM SET ssl = on;
SELECT pg_reload_conf();
SQL
tail -n 60 "$PG_LAB_ROOT/logs/primary.log"
python3 scripts/013-tls-peer-probe.py --cafile "$TLS013/ca.crt" \
  --expect-cert "$TLS013/leaf-v1.crt"
tls_app -f scripts/013-tls-inspection.sql
~~~

Allow a bounded ten-second reload observation window. Require peer exit 0/v1 fingerprint, authenticated lab_app, ssl true and negotiated protocol/cipher. If the binary lacks SSL support, stop and rebuild with a compatible binary.

Reject plaintext for the app:

~~~bash
python3 scripts/012-hba-lab.py reject
lab_sql -c 'SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL;'
lab_sql -c 'SELECT pg_reload_conf();'
tls_app -c 'SELECT current_user,current_database();'
~~~

Require zero parse errors. The early hostnossl reject applies only to lab_app/ops_lab; TLS SCRAM uses the original host rule.

## 4. Negative acceptance

~~~bash
if psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab \
  -c 'SELECT 1;' > "$TLS013/plaintext-error.txt" 2>&1; then
  echo 'FAIL: plaintext admitted; inspect policy before continuing.'
else
  echo 'Require explicit HBA rejection in plaintext-error.txt.'
fi
if psql -X -w -d "host=postgresql-lab.invalid hostaddr=127.0.0.1 port=55432 dbname=ops_lab user=lab_app sslmode=verify-full sslrootcert=$TLS013/wrong-ca.crt passfile=$TLS013/app.pgpass gssencmode=disable connect_timeout=5" \
  -c 'SELECT 1;' > "$TLS013/untrusted-error.txt" 2>&1; then
  echo 'FAIL: unrelated CA accepted.'
else
  echo 'Require certificate-chain verification failure in untrusted-error.txt.'
fi
if psql -X -w -d "host=wrong-name.invalid hostaddr=127.0.0.1 port=55432 dbname=ops_lab user=lab_app sslmode=verify-full sslrootcert=$TLS013/ca.crt passfile=$TLS013/app.pgpass gssencmode=disable connect_timeout=5" \
  -c 'SELECT 1;' > "$TLS013/hostname-error.txt" 2>&1; then
  echo 'FAIL: wrong server identity accepted.'
else
  echo 'Require server-name mismatch in hostname-error.txt.'
fi
~~~

A generic nonzero exit is insufficient: password, DNS, refused connection and SQL errors are not passing TLS failures. hostaddr pins attempts to loopback, and the scoped passfile includes the tested host names. Do not repair deliberate failures by weakening sslmode.

## 5. Rotate and prove v2

In Terminal A, repeat only the environment/functions from step 1. Open tls_app interactively; record backend PID and its pg_stat_ssl row, then leave the connection alive.

Terminal B:

~~~bash
lab_sql -v cert_path="$TLS013/leaf-v2.crt" -v key_path="$TLS013/leaf-v2.key" <<'SQL'
SELECT format('ALTER SYSTEM SET ssl_cert_file = %L', :'cert_path') \gexec
SELECT format('ALTER SYSTEM SET ssl_key_file = %L', :'key_path') \gexec
SELECT pg_reload_conf();
SQL
python3 scripts/013-tls-peer-probe.py --cafile "$TLS013/ca.crt" \
  --expect-cert "$TLS013/leaf-v2.crt"
tls_app -f scripts/013-tls-inspection.sql
~~~

Within ten seconds require v2 fingerprint and fresh authenticated TLS success. Peer exit 1 means a different leaf is served; exit 2 means negotiation/verification/probe failure. Inspect logs before retrying or restarting.

Terminal A: execute SELECT current_user,1; on the retained connection. Expected success; it did not renegotiate onto the new leaf. Close with \q, reconnect and verify SQL.

pg_stat_ssl cannot report the server leaf fingerprint. Retained-session usability and fresh peer fingerprint are separate evidence.

## 6. Rehearse rollback

~~~bash
lab_sql -v cert_path="$TLS013/leaf-v1.crt" -v key_path="$TLS013/leaf-v1.key" <<'SQL'
SELECT format('ALTER SYSTEM SET ssl_cert_file = %L', :'cert_path') \gexec
SELECT format('ALTER SYSTEM SET ssl_key_file = %L', :'key_path') \gexec
SELECT pg_reload_conf();
SQL
python3 scripts/013-tls-peer-probe.py --cafile "$TLS013/ca.crt" \
  --expect-cert "$TLS013/leaf-v1.crt"
tls_app -c 'SELECT 1;'
~~~

Require the served v1 fingerprint and fresh SQL success. This proves rollback while v1 remains valid/trusted; it does not establish CA rotation.

## 7. Restore and remove secrets

Close experimental sessions. Restore HBA, then remove only the three introduced overrides:

~~~bash
python3 scripts/012-hba-lab.py restore
lab_sql -c 'SELECT pg_reload_conf();'
lab_sql <<'SQL'
ALTER SYSTEM RESET ssl;
ALTER SYSTEM RESET ssl_cert_file;
ALTER SYSTEM RESET ssl_key_file;
SELECT pg_reload_conf();
SQL
lab_sql -c "SELECT name,setting,pending_restart FROM pg_settings
WHERE name IN ('ssl','ssl_cert_file','ssl_key_file');"
lab_sql -c 'SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL;'
lab_sql -c "SELECT name,setting FROM pg_file_settings WHERE sourcefile LIKE '%/postgresql.auto.conf' AND name IN ('ssl','ssl_cert_file','ssl_key_file');"
psql -X -w -h 127.0.0.1 -p 55432 -U lab_app -d ops_lab -c 'SELECT 1;'
bash scripts/004-operations-lab.sh verify
~~~

Require ssl off in a fresh session, original cert/key settings, no introduced auto-conf entries, zero HBA errors and original topology/probe success. Use the bounded reload observation window.

Retain sanitized fingerprints, serials, dates, client failures and rotation timestamps. After confirming no server setting references tls-013 and all experimental sessions are closed:

~~~bash
[[ "$TLS013" == "$PG_LAB_ROOT/tls-013" && -d "$TLS013" \
   && ! -L "$TLS013" && -O "$TLS013" ]] || exit 2
rm -- "$TLS013/ca.key" "$TLS013/wrong-ca.key" \
  "$TLS013/leaf-v1.key" "$TLS013/leaf-v2.key" "$TLS013/app.pgpass"
python3 scripts/012-hba-lab.py clean-secrets
~~~

Public certificates and sanitized evidence may remain. Do not publish CA keys, server keys or password files. For a rerun, preserve evidence and create a fresh lab rather than bypassing the occupied-directory guard.

| Acceptance evidence | Required result |
|---|---|
| Offline validation | Valid SAN/chain/dates and matching keys |
| v1 | Fresh served fingerprint and verified SCRAM session |
| Negative tests | Correct plaintext, wrong-CA and wrong-name failures |
| Rotation | Fresh v2 fingerprint and SQL success |
| Retained session | Remains usable; reconnection succeeds |
| Rollback | v1 served again with fresh SQL |
| Restoration | Original HBA/settings; primary/two standbys healthy |
| Secret cleanup | Copied app password and private keys removed |

Mark PostgreSQL execution pending until these outputs are observed. This is same-CA leaf/key rotation, not mutual TLS or CA-overlap acceptance.

If interrupted, keep OS/admin recovery access. Restore the original HBA and introduced SSL settings through the lab owner. If new SQL fails, first restore/reload a known valid certificate pair through the OS control path. Do not restart with missing/invalid referenced files or broaden authentication to trust.
