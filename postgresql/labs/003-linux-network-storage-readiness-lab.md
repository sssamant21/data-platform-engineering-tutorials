# Lab 003 — Linux, Network and Storage Readiness

[Chapter 003](../chapters/003-linux-networking-and-storage-prerequisites.md)

## Objective and scope

Create a read-only readiness record for an existing PostgreSQL lab. Reference PostgreSQL 18 on Linux; record exact versions.

Use an authorized client login and, for self-managed deployment, authorized server-host access. Do not confuse client-host output with database-host output. Managed-service learners replace host-only checks with provider telemetry and record unavailable fields.

No package installation, sysctl changes, service restarts, permission changes, port scanning, storage benchmarking or database writes are required.

## 1. Prepare the evidence directory

From the repository root:

~~~bash
mkdir -p evidence/chapter003
~~~

Use Chapter 001's connection parameters and credential handling. Record client host, database endpoint, database host/container identity and UTC time in evidence/chapter003/readiness.md.

## 2. Inspect the Linux server

On the authorized server host:

~~~bash
date -u
uname -srmo
cat /etc/os-release
nproc
free -h
vmstat 1 5
~~~

Save relevant results, excluding sensitive metadata not needed for handover.

Expected: an identified OS/kernel, visible CPU count, memory report and interval activity. Explain why these do not automatically prove PostgreSQL's effective resource limits.

Find the actual service or container. For systemd, inspect the confirmed instance unit's MainPID and limits as shown in the chapter. Read the corresponding process limits/cgroup. Never use a guessed PID or a wrapper unit as proof.

For a container, record configured CPU/memory limits, current usage and OOM/throttling events from the actual runtime or cgroup. Do not modify them.

## 3. Verify the connection path

From the client:

~~~bash
pg_isready -h "$PGHOST" -p "$PGPORT" -t 5
psql -X -v ON_ERROR_STOP=1 \
  -c "SELECT current_database(), current_user, inet_server_addr(), inet_server_port();"
~~~

Expected: readiness succeeds and authenticated identity matches the intended instance. A null server address can represent a Unix socket.

For TCP, inspect DNS resolution with getent ahosts. On the server host, confirm the expected listener using ss -ltn. For socket connectivity use ss -lx and the configured socket directory.

Record each layer separately: resolution, listener/reachability, authentication and successful SQL.

## 4. Deliberate client-configuration mismatch

This exercise changes only one client attempt. Confirm no PostgreSQL lab instance is intentionally running on port 1, then run against loopback:

~~~bash
pg_isready -h 127.0.0.1 -p 1 -t 2
echo $?
~~~

Expected on the selected lab client: no response and exit status 2. If something unexpectedly listens there, record that condition and do not classify it as a database failure.

Run the correct endpoint probe again:

~~~bash
pg_isready -h "$PGHOST" -p "$PGPORT" -t 5
~~~

Expected: success. Explain why an incorrect client port can fail while the intended database remains available. Do not edit the server listener or firewall.

## 5. Map paths to storage

Using an authorized settings reader:

~~~sql
SELECT name, setting
FROM pg_settings
WHERE name IN ('data_directory','config_file','hba_file')
ORDER BY name;
~~~

On the actual self-managed host, substitute the confirmed data path into:

~~~bash
PG_LAB_DATA_PATH='/actual/server/data/path'
findmnt -T "$PG_LAB_DATA_PATH"
df -hT "$PG_LAB_DATA_PATH"
df -i "$PG_LAB_DATA_PATH"
ls -ld "$PG_LAB_DATA_PATH"
~~~

Identify the resolved WAL location and each user tablespace target through the approved topology/configuration record; inspect their mount capacity separately. Avoid reading full configuration files that may contain credentials.

Expected: actual mounts, byte/inode headroom and directory ownership identified. If intended separate storage maps to the root filesystem, treat this as a readiness gap. Do not mount or move files during inspection.

Optional, when already installed:

~~~bash
iostat -xz 1 5
~~~

Record the observed interval and device mapping. An idle interval cannot certify storage performance under workload.

## 6. Produce the readiness report

| Area | Evidence | Interpretation | Owner/action |
|---|---|---|---|
| OS/kernel and PostgreSQL version | | | |
| Host versus container boundary | | | |
| Actual service/process identity | | | |
| CPU and effective limit | | | |
| Memory limit, demand and OOM evidence | | | |
| Process/file descriptor limits | | | |
| DNS/listener/authenticated SQL | | | |
| Data/WAL/tablespace mount mapping | | | |
| Bytes, inodes and growth monitoring | | | |
| Storage durability/provider guarantees | | | |
| Time synchronization | | | |
| Permissions and security boundary | | | |

Use “unknown — named owner and due date” when evidence is unavailable. Capacity headroom under workload must remain unqualified until load/capacity testing is performed.

## 7. Cleanup and acceptance

Close psql sessions and clear PG_LAB_DATA_PATH if introduced only for this exercise. Restore any prior shell connection settings. No server-side changes need rollback.

Pass when:

- Evidence identifies the correct database host rather than only the client.
- CPU/memory observations are distinguished from effective service limits.
- Endpoint checks distinguish readiness from authentication.
- The deliberate wrong-port failure is explained without changing the server.
- Storage paths map to actual mounts and include inode/WAL considerations.
- Unknowns are assigned rather than reported as healthy.
- No production resources, settings or files were modified.

**Troubleshooting:** access denied → record authorization boundary; missing command → approved alternative or owned gap; unknown service unit → runtime discovery; unexpected mount → stop and escalate; wrong-port success → unexpected listener, not a lab pass.

**Evidence:** readiness.md plus timestamped command results. Reading the lab alone is not execution verification.
