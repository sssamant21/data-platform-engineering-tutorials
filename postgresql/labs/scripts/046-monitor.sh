#!/usr/bin/env bash
set -euo pipefail
# Read-only monitoring example. Configure PGHOST, PGPORT, PGUSER and credentials securely.
# Invoke from repository root. Does not back up, restore or delete data.
export PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-5}"
psql -X -v ON_ERROR_STOP=1 -d "${PGDATABASE:-postgres}" \
  -f postgresql/labs/sql/046-monitor.sql
echo "Monitoring query completed. This does not verify backup recoverability."
