# 003 — Linux, Networking and Storage Prerequisites

[Master plan](../MASTER-PLAN.md) · [Previous chapter](002-architecture-processes-memory-storage-and-wal.md) · [Hands-on lab](../labs/003-linux-network-storage-readiness-lab.md)

## 1. Operational problem and objectives

A database can have sensible PostgreSQL settings yet fail because its service sees a smaller memory limit than the host, its data volume did not mount, its endpoint resolves incorrectly or its storage cannot sustain WAL flushes.

DBRE and SRE teams must verify the environment PostgreSQL actually uses. This chapter teaches a read-only prerequisite review rather than prescribing universal Linux tuning values.

**Reference:** PostgreSQL 18 on Linux. Record the exact distribution, kernel, PostgreSQL version and deployment type.  
**Audience:** DBRE/SRE only.  
**Prerequisites:** Chapters 001–002, an existing lab instance and authorized host access where available.  
**Effort:** approximately 60–90 minutes including the lab.

After the lab you should be able to map a database to its host or container resource boundary, confirm paths and mounts, distinguish network failures from authentication failures and produce an owned readiness gap list.

## 2. Deployment boundaries

| Deployment | Evidence available | Responsibility |
|---|---|---|
| Linux VM or bare metal | Host tools, service unit, process limits and mounts | Review the actual service host |
| Container | Container configuration, cgroups and mounted volumes | Check both container limits and backing host/storage |
| Kubernetes | Pod resources, node, PVC and operator configuration | Coordinate with platform owners; do not change operator-managed state directly |
| Managed PostgreSQL | SQL and provider telemetry/configuration | Replace inaccessible host checks with provider evidence |

Your laptop's free memory, filesystem or clock is not evidence about a remote database host. A WSL terminal is a useful Linux client, but its measurements describe WSL unless you connect to the server host.

## 3. Host and service identity

Capture a UTC timestamp and identify the host:

~~~bash
date -u
uname -srmo
cat /etc/os-release
hostname
~~~

Verify the PostgreSQL service unit instead of assuming its name:

~~~bash
systemctl list-units --type=service --all 'postgresql*'
~~~

Package layouts can have a wrapper unit and one or more instance units. A wrapper appearing active does not prove that your particular database instance is running.

For the confirmed instance unit:

~~~bash
PG_LAB_UNIT='postgresql@18-main.service'
systemctl show "$PG_LAB_UNIT" \
  -p ActiveState -p SubState -p MainPID -p User \
  -p MemoryMax -p TasksMax -p LimitNOFILE
~~~

The name above is an example, not a portable default. If the instance is supervised by an operator or container runtime, use that runtime's identity and configuration instead. Do not start or restart a service during prerequisite collection.

## 4. CPU, memory and process limits

~~~bash
nproc
free -h
vmstat 1 5
~~~

nproc describes processing capacity visible to the command; service affinity and cgroup quota can impose additional restrictions. free describes memory available in its execution context and may not reveal a container's hard limit.

In vmstat, inspect runnable work, swap activity, CPU composition and trends. The first report generally covers activity since boot; subsequent interval reports are better for the short observation window. Load average is not CPU utilization.

Inspect the actual service process when authorized:

~~~bash
cat /proc/CONFIRMED_POSTMASTER_PID/limits
cat /proc/CONFIRMED_POSTMASTER_PID/cgroup
~~~

Replace the placeholder with the verified server PID. A shell's ulimit does not prove the already running service's limits. File descriptor limits, process/task limits and memory budgets should reflect the topology and concurrency.

For cgroup v2, the service's resolved cgroup directory can expose:

| File | Interpretation |
|---|---|
| memory.current | Current charged memory |
| memory.max | Configured memory ceiling; max means no limit at this level |
| memory.events | Memory-pressure/OOM event counters |
| cpu.max | CPU quota and period |
| cpu.stat | CPU usage and throttling counters |
| pids.max | Process/task ceiling |

Check the actual path and any ancestor constraints; do not assume /sys/fs/cgroup describes the server's leaf group. cgroup v1 has different interfaces.

PostgreSQL uses shared memory and other OS resources. Consult the selected version's kernel-resource guidance if startup fails. Do not copy historical semaphore or shared-memory sysctl formulas without matching the OS and PostgreSQL memory implementation.

The Linux OOM killer can terminate PostgreSQL processes. Diagnose kernel/cgroup events and workload demand together; changing PostgreSQL memory values alone may not address the resource boundary.

## 5. Network path and connection layers

Troubleshoot in layers:

1. Client connection parameters and intended endpoint.
2. DNS resolution.
3. Route, network policy and server reachability.
4. Listener and port.
5. TLS, authentication and database access.
6. Actual application request.

From the client, using explicit lab values:

~~~bash
getent ahosts "$PGHOST"
pg_isready -h "$PGHOST" -p "$PGPORT" -t 5
psql -X -v ON_ERROR_STOP=1 \
  -c "SELECT current_database(), current_user, inet_server_addr(), inet_server_port();"
~~~

DNS inspection applies to a TCP hostname, not a Unix-socket directory. The readiness check does not prove successful authentication. A refused connection and a timeout suggest different classes of problem; retain the exact error.

On the authorized server host:

~~~bash
ss -ltn
ss -lx
~~~

TCP listeners and Unix sockets are different paths. Match the expected address and port. Process identity details can require additional privileges.

PostgreSQL listen_addresses controls which interfaces accept TCP connections; pg_hba.conf governs connection authentication rules. Firewalls, cloud rules and Kubernetes policies are separate layers. Do not widen listeners or set trust authentication as a diagnostic shortcut.

Production clients should use the agreed TLS verification policy and correct hostname. Certificate validation failures are evidence about the security/identity path, not justification to disable verification.

## 6. Storage paths, capacity and durability

An authorized settings reader can collect paths:

~~~sql
SELECT name, setting
FROM pg_settings
WHERE name IN ('data_directory','config_file','hba_file')
ORDER BY name;
~~~

Confirm the server path and namespace before inspecting it. PostgreSQL configuration may live outside the data directory.

On a self-managed lab host:

~~~bash
PG_LAB_DATA_PATH='/actual/server/data/path'
findmnt -T "$PG_LAB_DATA_PATH"
df -hT "$PG_LAB_DATA_PATH"
df -i "$PG_LAB_DATA_PATH"
ls -ld "$PG_LAB_DATA_PATH"
~~~

Replace the path before running. Check data, resolved WAL path and actual tablespace targets independently. A path intended for a separate volume can accidentally reside on the root filesystem when its mount is missing.

Review byte capacity, inode availability, mount options, ownership and the storage class's latency/IOPS/throughput characteristics. A volume with enough free bytes can still constrain throughput. Database size functions do not measure free storage.

If available, collect interval I/O:

~~~bash
iostat -xz 1 5
~~~

Ignore the initial since-boot report when interpreting interval behavior. Device mapping, queueing, await, IOPS and throughput must be correlated with PostgreSQL and provider telemetry. Percent utilization alone is not a universal saturation test for modern devices.

Storage must honor durability operations and the required power-loss guarantees. Do not disable fsync or weaken storage flush behavior to improve a benchmark. Backups require their own destination and failure-domain review; a directory on the same failing volume is not isolation.

Synthetic write benchmarks are outside this read-only check. Run them only on disposable test storage with an explicit workload and cleanup plan.

## 7. Time and security prerequisites

Collect clock evidence on the server and client:

~~~bash
date -u
~~~

On a system using systemd time services, timedatectl status provides additional information. Other platforms may use chrony or provider-managed time synchronization. Record the actual time source and observed synchronization evidence.

Clock consistency supports incident correlation, certificate validity and authentication workflows. It does not itself prove database recovery correctness.

The PostgreSQL OS account, database roles and automation identities have different scopes. Validate data-directory ownership and service identity without recursively changing permissions. Review SELinux/AppArmor or provider access failures with the platform/security owner rather than disabling enforcement.

## 8. Production procedure, monitoring and recovery

**Prechecks:** confirm the database target, host identity, authorized access, resource boundary and maintenance restrictions.

**Collection:** bounded read-only commands, no recursive filesystem scans, no benchmark writes and no credential exports. If a tool is absent, record the gap; do not install packages during incident collection without the normal change procedure.

**Stop conditions:** wrong host, missing mount, wrong data path, unsupported namespace or access failure. Record evidence and escalate to the responsible owner.

**Verification:** compare SQL identity with host/container identity and attach timestamps. Persistent settings are not changed by this chapter, so closing sessions is sufficient rollback.

| Signal | Operational action |
|---|---|
| Shrinking free space or inodes | Forecast exhaustion time and respond before capacity is reached |
| OOM events or sustained memory pressure | Correlate workload, service limits and headroom |
| CPU throttling with service latency | Check quota, concurrency and workload |
| Storage latency/queue growth | Correlate database waits and device/provider limits |
| Endpoint failures | Separate DNS, listener, policy, TLS and authentication |
| Clock drift or sync loss | Engage platform owner and preserve time-window context |

Choose alert windows and thresholds from the service objective and measured environment. Do not label prerequisites “passed” from one idle sample.

## 9. Troubleshooting and acceptance

| Symptom | Safe next step |
|---|---|
| Host has memory; container OOMs | Inspect effective cgroup limits and events |
| Service active; SQL unavailable | Verify instance unit, listener and logs |
| Intended data disk looks unused | Map the actual data path to its mount |
| Free bytes available; writes fail | Check inodes, quotas, permissions and exact database error |
| Local socket works; remote TCP fails | Check listener, route/policy and authentication layers |
| Tools missing | Use approved equivalent telemetry and record limitation |
| Provider hides host resources | Attach provider configuration/metrics and responsibility boundary |

Complete the [readiness lab](../labs/003-linux-network-storage-readiness-lab.md). Passing requires an evidence-backed inventory and assigned gaps; full load qualification comes later.

**Next:** Chapter 004 — Build a Reproducible PostgreSQL Operations Lab.

## 10. Official references

- [PostgreSQL 18 kernel resources](https://www.postgresql.org/docs/18/kernel-resources.html)
- [Connections and authentication settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [Cluster creation and ownership](https://www.postgresql.org/docs/18/creating-cluster.html)
- [Storage reliability](https://www.postgresql.org/docs/18/wal-reliability.html)
- [Monitoring disk usage](https://www.postgresql.org/docs/18/diskusage.html)
- [Linux cgroup v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
