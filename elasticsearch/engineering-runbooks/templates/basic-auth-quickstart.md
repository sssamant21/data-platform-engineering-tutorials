# Basic Authentication with curl — shared setup

Use HTTP Basic Authentication with a username and an interactive password prompt. **No client certificate or CA certificate file is required by this environment.** For HTTPS, curl verifies the server using its normal operating-system or configured trust store.

## Bash / Linux / WSL2

```bash
export ES_URL='https://es.example.internal:9200'
export ES_USER='es-readonly-operator'
# curl prompts for a password when --user receives only the username.
curl --fail-with-body --silent --show-error --basic --user "$ES_USER" \
  "$ES_URL/_cluster/health?pretty"
```

## Windows PowerShell

```powershell
$env:ES_URL = 'https://es.example.internal:9200'
$env:ES_USER = 'es-readonly-operator'
curl.exe --fail-with-body --silent --show-error --basic --user "$env:ES_USER" `
  "$env:ES_URL/_cluster/health?pretty"
```

- Use **`curl.exe`** in PowerShell because `curl` can be an alias.
- `--basic --user "$ES_USER"` specifies only the username; curl prompts for the password. Never include credentials in Git, Jira, URLs, or shell commands.
- For scheduled jobs, use an approved secrets mechanism; do not embed secrets in source control or command arguments.
- **Do not use `-k` or `--insecure`**. With HTTPS, normal trust-store verification remains active even without certificate-file flags. If the server is not trusted, have the platform/security team correct its trust configuration instead of bypassing verification.
- Use a least-privilege operator account. Mutating commands require reviewed privileges and approvals.
- Older curl versions may require `--fail` rather than `--fail-with-body`.
- Check `GET /` to confirm target cluster identity and Elasticsearch version before running version-sensitive commands.

Reference: https://www.elastic.co/docs/deploy-manage/security/httprest-clients-security
