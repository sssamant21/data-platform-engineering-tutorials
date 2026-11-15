# Basic Authentication with curl — shared setup

**Never** write real passwords into Markdown, issue descriptions, shell history or command line flags. Prefer scoped credentials and validated HTTPS.

## Bash / Linux / WSL2

```bash
export ES_URL='https://es.example.internal:9200'
export ES_USER='es-readonly-operator'
export ES_CA_CERT='/secure/path/es-ca.pem'
# Curl prompts for password; --basic explicitly selects HTTP Basic auth.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  --cacert "$ES_CA_CERT" "$ES_URL/_cluster/health?pretty"
```

## Windows PowerShell

```powershell
$env:ES_URL = 'https://es.example.internal:9200'
$env:ES_USER = 'es-readonly-operator'
$env:ES_CA_CERT = 'C:\secure\es-ca.pem'
curl.exe --fail-with-body --silent --show-error --basic --user "$env:ES_USER" `
    --cacert "$env:ES_CA_CERT" "$env:ES_URL/_cluster/health?pretty"
```

- `curl` can be a PowerShell alias; prefer **`curl.exe`** for native curl semantics.
- `--user "$ES_USER"` (username without colon/password) prompts interactively. A scheduler should use an approved secret store or tightly permissioned curl configuration, not credentials in source control or process arguments.
- Do not use `-k` / `--insecure` for production. Verify certificate hostname and trust store. Disallow plaintext HTTP.
- Use a least-privilege account with appropriate monitor permissions for reads. Change operations require independently approved privilege grants.
- On older curl versions, replace `--fail-with-body` with `--fail` and examine the returned HTTP response body separately.
- API version compatibility matters; inspect `GET /` and record `version.number` before using a version-specific command.

Reference: https://www.elastic.co/docs/deploy-manage/security/httprest-clients-security
