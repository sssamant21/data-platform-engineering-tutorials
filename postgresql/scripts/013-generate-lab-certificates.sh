#!/usr/bin/env bash
# Disposable PG18 lab PKI only; no database configuration changes.
set -Eeuo pipefail
umask 077
: "${PG_LAB_ROOT:?Export the Chapter 004 disposable lab root}"
[[ "$(id -u)" != 0 ]] || { echo 'Use the non-root lab OS account.' >&2; exit 2; }
[[ "$PG_LAB_ROOT" =~ ^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+$ ]] || exit 2
[[ -d "$PG_LAB_ROOT" && ! -L "$PG_LAB_ROOT" && -O "$PG_LAB_ROOT" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/LAB_MARKER")" == postgresql18-dbre-sre-disposable ]] || exit 2
[[ -d "$PG_LAB_ROOT/primary" && ! -L "$PG_LAB_ROOT/primary" && -O "$PG_LAB_ROOT/primary" ]] || exit 2
[[ "$(cat "$PG_LAB_ROOT/primary/PG_VERSION")" == 18 ]] || exit 2
[[ "$(openssl version)" == 'OpenSSL 3.'* ]] || { echo 'Use OpenSSL 3.x.' >&2; exit 2; }
TLS013="$PG_LAB_ROOT/tls-013"
[[ ! -e "$TLS013" && ! -L "$TLS013" ]] || { echo 'Preserve existing PKI; use a fresh lab for a rerun.' >&2; exit 2; }

# GENERATION_BODY: fixture tests execute this body separately from the OS guard.
mkdir -m 700 "$TLS013"
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 7 \
  -keyout "$TLS013/ca.key" -out "$TLS013/ca.crt" -subj '/CN=Chapter013-Lab-CA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 7 \
  -keyout "$TLS013/wrong-ca.key" -out "$TLS013/wrong-ca.crt" -subj '/CN=Chapter013-Untrusted-CA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
cat > "$TLS013/leaf.ext" <<'EXT'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:postgresql-lab.invalid,IP:127.0.0.1
EXT
for version in 1 2; do
  openssl req -new -newkey rsa:2048 -nodes -sha256 \
    -keyout "$TLS013/leaf-v$version.key" -out "$TLS013/leaf-v$version.csr" \
    -subj '/CN=postgresql-lab.invalid'
  openssl x509 -req -in "$TLS013/leaf-v$version.csr" \
    -CA "$TLS013/ca.crt" -CAkey "$TLS013/ca.key" \
    -set_serial "0x130$version" -days 2 -sha256 \
    -extfile "$TLS013/leaf.ext" -out "$TLS013/leaf-v$version.crt"
  openssl verify -CAfile "$TLS013/ca.crt" -purpose sslserver \
    -verify_hostname postgresql-lab.invalid "$TLS013/leaf-v$version.crt"
  chmod 600 "$TLS013/leaf-v$version.key"
done
python3 - "$PG_LAB_ROOT" "$TLS013" <<'PY'
import os,re,stat,sys
from pathlib import Path
root,tls=map(Path,sys.argv[1:])
path=root/"credentials.pgpass"
st=path.lstat()
if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
    raise SystemExit("Expected owned, private Chapter 004 credential file")
matches=[]
for line in path.read_text().splitlines():
    fields=line.split(":")
    if len(fields)==5 and fields[:4]==["127.0.0.1","55432","*","lab_app"]:
        matches.append(fields[4])
if len(matches)!=1 or not re.fullmatch(r"[0-9a-f]{48}",matches[0]):
    raise SystemExit("Unexpected Chapter 004 app credential structure")
with (tls/"app.pgpass").open("x") as handle:
    os.fchmod(handle.fileno(),0o600)
    for host in ("127.0.0.1","postgresql-lab.invalid","wrong-name.invalid"):
        handle.write(f"{host}:55432:ops_lab:lab_app:{matches[0]}\n")
PY
printf '%s\n' 'Test PKI generated. Never commit CA keys, leaf keys or app.pgpass.'
