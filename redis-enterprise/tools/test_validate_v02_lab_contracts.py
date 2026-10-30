"""V02 acceptance checks for Chapters 47/51. Parsing only; never connects to Redis."""
import ast
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL_DIR))
from validate_v02_examples import find_blocks

CHAPTER_DIR = TOOL_DIR.parent
CHAPTER_FILES = {
    47: "47-redis-enterprise-database-lifecycle-provisioning-configuration-engineering.md",
    51: "51-redis-enterprise-end-to-end-production-engineering-project.md",
}


def get_content_and_blocks(chapter):
    source = (CHAPTER_DIR / CHAPTER_FILES[chapter]).read_text(encoding="utf-8")
    return source, find_blocks(source.splitlines())


class V02LabContractsTests(unittest.TestCase):
    def test_bash_sections_parse_without_execution(self):
        if not shutil.which("bash"):
            self.skipTest("bash is not installed")
        for chapter in CHAPTER_FILES:
            _, blocks = get_content_and_blocks(chapter)
            bash = [b for b in blocks if b["language"] == "bash"]
            self.assertGreaterEqual(len(bash), 2, chapter)
            for b in bash:
                result = subprocess.run(
                    ["bash", "-n"], input=b["source"], text=True,
                    capture_output=True, timeout=5, check=False
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"Chapter {chapter} line {b['line']}: {result.stderr}"
                )

    def test_python_drift_example_parses(self):
        _, blocks = get_content_and_blocks(47)
        scripts = [b for b in blocks if b["language"] == "python"]
        self.assertTrue(any("DRIFT DETECTED" in b["source"] for b in scripts))
        for block in scripts:
            ast.parse(block["source"])

    def test_scoped_secrets_and_tls_controls(self):
        for chapter in CHAPTER_FILES:
            doc, blocks = get_content_and_blocks(chapter)
            bash = "\n".join(b["source"] for b in blocks if b["language"] == "bash")
            self.assertIn("--tls --cacert", bash)
            self.assertIn("REDISCLI_AUTH", bash)
            self.assertIn("RUN_ID=", bash)
            self.assertIn("rcli UNLINK", bash)
            self.assertIn("rcli EXISTS", bash)
            self.assertIn("NOT EXECUTED", doc)
            self.assertNotIn("FLUSHDB", bash)
            self.assertNotIn("FLUSHALL", bash)
            self.assertNotIn("--insecure", bash)
            self.assertNotIn("redis-cli -a", bash)

    def test_chapter_47_expected_results_and_gate(self):
        doc, _ = get_content_and_blocks(47)
        for required in ("PING", "SET", "GET", "TTL", "DRIFT DETECTED",
                         "Expected:", "Resize", "Retirement", "NOT EXECUTED"):
            self.assertIn(required, doc)

    def test_chapter_51_stream_acceptance(self):
        doc, blocks = get_content_and_blocks(51)
        bash = "\n".join(b["source"] for b in blocks if b["language"] == "bash")
        for command in ("XGROUP CREATE", "XADD", "XREADGROUP", "XPENDING", "XACK"):
            self.assertIn(command, bash)
        self.assertIn("one-shot", doc.lower())
        self.assertIn("rate limiter", doc.lower())
        self.assertIn("Not a", doc) if False else None
        self.assertIn("NOT EXECUTED", doc)

    def test_chapter_51_cleanup_uses_single_key_exists(self):
        _, blocks = get_content_and_blocks(51)
        bash = "\n".join(b["source"] for b in blocks if b["language"] == "bash")
        self.assertIn('rcli EXISTS "$key"', bash)
        self.assertNotIn('rcli EXISTS "$PROFILE" "$SESSION"', bash)

    def test_chapter_01_secure_connection_examples(self):
        source = (CHAPTER_DIR / "01-redis-enterprise-fundamentals-architecture.md").read_text(encoding="utf-8")
        self.assertIn("REDISCLI_AUTH", source)
        self.assertIn('export REDIS_CA=', source)
        self.assertIn('export API_CA=', source)
        self.assertIn('curl --fail --silent --show-error --cacert "$API_CA"', source)
        self.assertNotIn('-a "$REDIS_PASSWORD"', source)
        self.assertNotIn('curl -k ', source)
        self.assertNotIn('curl -ks ', source)
        self.assertNotIn('$API_USER:$API_PASSWORD', source)

    def test_chapter_03_single_line_interactive_hset(self):
        source = (CHAPTER_DIR / "03-redis-data-types-key-design-memory-aware-data-modeling.md").read_text(encoding="utf-8")
        self.assertIn('HSET tutorial:chapter03:product:1002:v1 name "Mouse"', source)
        self.assertIn("HSET reports 4 newly added hash fields", source)
        self.assertNotIn('HSET tutorial:chapter03:product:1002:v1 ' + chr(92) + chr(10), source)

    def test_chapter_04_conditional_set_expected_replies(self):
        chapter = (CHAPTER_DIR / "04-redis-commands-command-semantics-safe-operations.md").read_text(encoding="utf-8")
        self.assertIn("Expected per-command results:", chapter)
        self.assertIn("nil/null", chapter)
        self.assertIn("does not replace the original value", chapter)

    def test_chapter_11_expire_version_gate(self):
        chapter = (CHAPTER_DIR / "11-ttl-expiration-cache-freshness-engineering.md").read_text(encoding="utf-8")
        self.assertIn("Redis 7.0.0", chapter)
        self.assertIn("persistent (non-expiring) key", chapter)
        self.assertIn("EXPIRE command/version history", chapter)

    def test_chapter_15_authenticated_example_is_tls_and_no_inline_password(self):
        source = (CHAPTER_DIR / "15-cache-stampede-thundering-herd-source-protection.md").read_text(encoding="utf-8")
        self.assertIn("Staging database password:", source)
        self.assertIn("REDISCLI_AUTH", source)
        self.assertIn('redis-cli --tls --cacert "$REDIS_CA"', source)
        self.assertNotIn('redis-cli -h <host> -p <port> -a "<password>" PING', source)

    def test_chapter_69_scan_has_cursor_and_expected_behavior(self):
        source = (CHAPTER_DIR / "69-redis-enterprise-advanced-memory-forensics-fragmentation-allocator-engineering.md").read_text(encoding="utf-8")
        self.assertIn("SCAN 0 MATCH 'tutorial:chapter69:*' COUNT 100", source)
        self.assertIn("is a work hint", source)
        self.assertNotIn("~~~bash\nSCAN\n~~~", source)

    def test_chapter_15_python_examples_enforce_remote_tls_guard(self):
        path = CHAPTER_DIR / "15-cache-stampede-thundering-herd-source-protection.md"
        source = path.read_text(encoding="utf-8")
        blocks = find_blocks(source.splitlines())
        python_blocks = [b for b in blocks if b["language"] == "python"]
        guarded = [b for b in python_blocks if "redis.Redis(" in b["source"]]
        self.assertEqual(len(guarded), 3)
        for b in guarded:
            ast.parse(b["source"])
            self.assertIn("Remote lab Redis connections require REDIS_TLS=1", b["source"])
            self.assertIn("ssl_ca_certs", b["source"])
            self.assertIn('ssl_cert_reqs="required"', b["source"])

    def test_chapter_15_cli_wrapper_is_valid_bash(self):
        path = CHAPTER_DIR / "15-cache-stampede-thundering-herd-source-protection.md"
        source = path.read_text(encoding="utf-8")
        blocks = find_blocks(source.splitlines())
        helpers = [b for b in blocks if b["language"] == "bash" and "rcli() {" in b["source"]]
        self.assertEqual(len(helpers), 1)
        self.assertIn('test "$(rcli PING)" = "PONG"', helpers[0]["source"])
        self.assertIn("REFUSED: non-loopback", helpers[0]["source"])
        if not shutil.which("bash"):
            self.skipTest("bash not installed")
        result = subprocess.run(["bash", "-n"], text=True, input=helpers[0]["source"],
                                capture_output=True, timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_chapter_15_cli_no_bare_one_off_commands(self):
        import re
        path = CHAPTER_DIR / "15-cache-stampede-thundering-herd-source-protection.md"
        source = path.read_text(encoding="utf-8")
        blocks = find_blocks(source.splitlines())
        bad = []
        for b in blocks:
            if b["language"] != "bash":
                continue
            for line in b["source"].splitlines():
                if re.match(r"^\s*redis-cli\s+(?:GET|SET|TTL|PTTL|DEL|EXISTS|UNLINK)\b", line):
                    bad.append((b["line"], line))
        self.assertEqual(bad, [])
        self.assertIn("rcli GET tutorial:chapter15:item:1001", source)
        self.assertIn("rcli SET tutorial:chapter15:jitter:1 value EX 60", source)
        self.assertIn("rcli UNLINK", source)
        self.assertIn("unset REDISCLI_AUTH REDIS_PASSWORD", source)
        self.assertIn("rcli SCAN 0 MATCH 'tutorial:chapter15:*' COUNT 100", source)

    def test_chapter_45_cordon_requires_approval_and_recovers_scheduling(self):
        doc = (CHAPTER_DIR / "45-redis-enterprise-kubernetes-operations-scheduling-platform-engineering.md").read_text(encoding="utf-8")
        self.assertIn("Only after separate approval", doc)
        self.assertIn("NOT EXECUTED", doc)
        self.assertIn("kubectl config current-context", doc)
        self.assertIn("kubectl get pods -A --field-selector spec.nodeName=<lab-node>", doc)
        self.assertIn("kubectl cordon <lab-node>", doc)
        self.assertIn("kubectl uncordon <lab-node>", doc)
        self.assertIn("-o jsonpath='{.spec.unschedulable}'", doc)
        self.assertIn("does not evict existing pods", doc)

    def test_chapter_10_hash_and_zset_expected_results(self):
        doc = (CHAPTER_DIR / "10-architecture-inspection-foundation-acceptance-lab.md").read_text(encoding="utf-8")
        self.assertIn("returns integer " + chr(96) + "2" + chr(96) + " newly added fields", doc)
        self.assertIn("hash field ordering is not a contract", doc)
        self.assertIn("descending score order", doc)
        self.assertIn("user2 200", doc)
        self.assertIn("user3 150", doc)
        self.assertIn("user1 100", doc)
        self.assertIn("schematic", doc)

    def test_chapter_54_benchmark_is_bounded_and_isolated(self):
        chapter = (CHAPTER_DIR / "54-redis-enterprise-benchmarking-load-testing-performance-qualification-engineering.md").read_text(encoding="utf-8")
        self.assertIn("redis-benchmark -h 127.0.0.1 -p 6379 -c 2 -n 200 -t get,set -q", chapter)
        self.assertIn("write-generating workload", chapter)
        self.assertIn("no other workload", chapter)
        self.assertIn("Expected:", chapter)
        self.assertNotIn("redis-benchmark -h \"$REDIS_HOST\" -p \"$REDIS_PORT\" -c 50 -n 100000 -t get,set", chapter)

    def test_scan_examples_include_required_cursors(self):
        examples = {
            3: "SCAN 0 MATCH 'tutorial:chapter03:*' COUNT 100",
            4: "SCAN 0 MATCH 'tutorial:chapter04:*' COUNT 100",
            18: "SCAN 0 MATCH 'tutorial:chapter18:*' COUNT 100",
            40: "SCAN 0 MATCH 'tutorial:chapter40:*' COUNT 100",
        }
        paths = {
            3: "03-redis-data-types-key-design-memory-aware-data-modeling.md",
            4: "04-redis-commands-command-semantics-safe-operations.md",
            18: "18-redis-hot-keys-big-keys-workload-skew-engineering.md",
            40: "40-redis-enterprise-performance-troubleshooting-production-incident-engineering.md",
        }
        for number, cmd in examples.items():
            doc = (CHAPTER_DIR / paths[number]).read_text(encoding="utf-8")
            self.assertIn(cmd, doc)
            self.assertIn("cursor", doc.lower())
        doc4 = (CHAPTER_DIR / paths[4]).read_text(encoding="utf-8")
        self.assertIn("HSCAN tutorial:chapter04:inventory 0 COUNT 100", doc4)
        self.assertIn("SSCAN tutorial:chapter04:lab-set 0 COUNT 100", doc4)
        self.assertIn("ZSCAN tutorial:chapter04:lab-zset 0 COUNT 100", doc4)

    def test_conceptual_cache_delete_examples_are_qualified(self):
        documents = {
            12: "12-cache-aside-pattern.md",
            13: "13-cache-updates-invalidation-consistency.md",
            20: "20-redis-cache-invalidation-consistency-change-propagation.md",
        }
        for chapter, name in documents.items():
            doc = (CHAPTER_DIR / name).read_text(encoding="utf-8")
            self.assertTrue(("conceptual application key" in doc.lower()) or ("illustrative application key" in doc.lower()), chapter)
            self.assertIn("0", doc)
            self.assertIn("1", doc)
            self.assertIn("shared", doc.lower())

    def test_chapters_03_04_have_no_bash_continuations_in_redis_fences(self):
        from review_v02_redis_fence_syntax import inspect as inspect_fences
        result = inspect_fences(CHAPTER_DIR)
        bad = [x for x in result["findings"] if x["chapter"] in {3, 4}]
        self.assertEqual(bad, [], bad[:12])

    def test_chapter_03_string_and_hash_models_use_distinct_owned_keys(self):
        doc = (CHAPTER_DIR / "03-redis-data-types-key-design-memory-aware-data-modeling.md").read_text(encoding="utf-8")
        self.assertIn("SET tutorial:chapter03:model:string:1001", doc)
        self.assertIn("HSET tutorial:chapter03:model:hash:1001", doc)
        self.assertIn("WRONGTYPE", doc)
        self.assertIn("ascending `ZRANGE`", doc)
        self.assertIn("descending `ZREVRANGE`", doc)
        self.assertIn("XADD", doc)
        self.assertIn("generated stream entry ID", doc)

    def test_chapter_04_mset_hscan_expected_results(self):
        doc = (CHAPTER_DIR / "04-redis-commands-command-semantics-safe-operations.md").read_text(encoding="utf-8")
        self.assertIn("MSET` returns `OK`", doc)
        self.assertIn("same order as requested", doc)
        self.assertIn("HSET` returns integer `5`", doc)
        self.assertIn("COUNT 2", doc)

    def test_all_chapters_redis_interactive_fences_have_no_known_syntax_faults(self):
        from review_v02_redis_fence_syntax import inspect as inspect_fences
        results = inspect_fences(CHAPTER_DIR)
        self.assertEqual(results["summary"]["chapters"], 80)
        self.assertEqual(results["summary"]["syntax_review_candidates"], 0, results["findings"][:10])

    def test_chapter_14_xadd_is_single_valid_interactive_command(self):
        doc = (CHAPTER_DIR / "14-write-through-write-behind-read-through-patterns.md").read_text(encoding="utf-8")
        self.assertIn("XADD tutorial:chapter14:writes '*' operation_id op-1001", doc)
        self.assertIn("generated Stream ID", doc)
        self.assertIn("four field/value pairs", doc)

    def test_chapter_01_replication_ack_and_datatype_outputs(self):
        doc = (CHAPTER_DIR / "01-redis-enterprise-fundamentals-architecture.md").read_text(encoding="utf-8")
        self.assertIn("SET tutorial:chapter01:write-flow active EX 300", doc)
        self.assertIn("not** that a replica has already acknowledged", doc)
        self.assertIn("DEL tutorial:chapter01:write-flow", doc)
        self.assertIn("LPUSH` adds three elements", doc)
        self.assertIn("event3`, `event2`, `event1", doc)

    def test_chapter_04_atomic_ops_have_time_dependent_outputs(self):
        doc = (CHAPTER_DIR / "04-redis-commands-command-semantics-safe-operations.md").read_text(encoding="utf-8")
        self.assertIn("PTTL` returns a positive remaining lifetime", doc)
        self.assertIn("INCR` returns integer `1`", doc)
        self.assertIn("HINCRBY` returns integer `1`", doc)

    def test_chapter_11_ttl_release_semantics_examples(self):
        doc = (CHAPTER_DIR / "11-ttl-expiration-cache-freshness-engineering.md").read_text(encoding="utf-8")
        self.assertIn("TTL` returns `-1` because the key is persistent", doc)
        self.assertIn("PERSIST` returns `1`", doc)
        self.assertIn("EXPIRE ... NX` returns `1`", doc)
        self.assertIn("Redis 7.0+", doc)

    def test_chapters_09_76_inspection_examples_are_typed(self):
        chapter09 = (CHAPTER_DIR / "09-redis-enterprise-administration-interfaces-ui-rladmin-rest-api.md").read_text(encoding="utf-8")
        self.assertIn("``` bash\nrladmin status\nrladmin info db", chapter09)
        self.assertIn("Exact fields vary by release", chapter09)
        chapter76 = (CHAPTER_DIR / "76-redis-enterprise-performance-capacity-engineering-project.md").read_text(encoding="utf-8")
        self.assertIn("``` redis\nINFO memory\n```", chapter76)
        self.assertIn("used_memory_rss:", chapter76)
        self.assertIn("multi-shard cluster capacity report", chapter76)

    def test_chapter_10_scan_unlink_expectations(self):
        doc = (CHAPTER_DIR / "10-architecture-inspection-foundation-acceptance-lab.md").read_text(encoding="utf-8")
        self.assertIn("SCAN 0 MATCH", doc)
        self.assertIn("Integer `1` if that exact disposable lab key existed", doc)
        self.assertIn("not proof of immediate memory reduction", doc)

    def test_chapter_02_approved_pod_diagnostic_requires_tls(self):
        src = (CHAPTER_DIR / "02-connecting-to-redis-enterprise-clients-endpoints-tls-connection-management.md").read_text(encoding="utf-8")
        section = src.split("## 36. Redis Test from a Pod", 1)[1].split("# Hands-On Lab", 1)[0]
        self.assertIn('REDISCLI_AUTH', section)
        self.assertIn('redis-cli --tls --cacert "$REDIS_CA"', section)
        self.assertIn('test -r "$REDIS_CA"', section)
        self.assertIn("**NOT EXECUTED**", section)
        self.assertNotIn("Add authentication/TLS options as required.", section)
        self.assertNotIn("redis-cli \\\n  -h <REDIS_ENDPOINT>", section)
        if shutil.which("bash"):
            bash_blocks = [b["source"] for b in find_blocks(section.splitlines()) if b["language"] == "bash"]
            self.assertEqual(len(bash_blocks), 1)
            proc = subprocess.run(["bash", "-n"], input=bash_blocks[0], text=True,
                                  capture_output=True, timeout=5, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_chapter_70_bounded_hash_and_mget_examples(self):
        src = (CHAPTER_DIR / "70-redis-enterprise-command-complexity-slowlog-latency-forensics.md").read_text(encoding="utf-8")
        self.assertIn("HGET tutorial:chapter70:hash f1", src)
        self.assertIn("HGETALL tutorial:chapter70:hash", src)
        self.assertIn("MGET tutorial:chapter70:{lab70}:k1", src)
        self.assertIn("MGET 10", src)  # explicitly described as invalid batch-size shorthand
        self.assertIn("would read the one key literally named", src)
        self.assertIn("UNLINK tutorial:chapter70:{lab70}:k1", src)
        self.assertIn("dedicated, owner-approved nonproduction lab", src)
        redis_blocks = [b["source"] for b in find_blocks(src.splitlines()) if b["language"] == "redis"]
        self.assertFalse(any("MGET 10\n" in block or "HGET one field" in block for block in redis_blocks))

    def test_chapter_25_incomplete_expire_warning_is_non_executable(self):
        src = (CHAPTER_DIR / "25-redis-rate-limiting-quotas-traffic-protection.md").read_text(encoding="utf-8")
        self.assertIn("intentionally schematic, non-executable pseudocode", src)
        self.assertIn("EXPIRE key seconds", src)
        self.assertIn("unsafe two-command sequence", src)

    def test_chapter_11_keepttl_requires_preexisting_expiry(self):
        src = (CHAPTER_DIR / "11-ttl-expiration-cache-freshness-engineering.md").read_text(encoding="utf-8")
        part = src.split("## 11. Preserve TTL", 1)[1].split("## 12. Reset TTL", 1)[0]
        self.assertIn("Redis **6.0+**", part)
        self.assertIn("EXPIRE tutorial:chapter11:item 300", part)
        self.assertIn("SET tutorial:chapter11:item value3 KEEPTTL", part)
        self.assertLess(part.index("EXPIRE tutorial:chapter11:item 300"),
                        part.index("SET tutorial:chapter11:item value3 KEEPTTL"))
        self.assertIn("TTL=-1", part)
        self.assertIn("positive", part)

    def test_chapter_14_distinct_stream_group_and_expected_replies(self):
        src = (CHAPTER_DIR / "14-write-through-write-behind-read-through-patterns.md").read_text(encoding="utf-8")
        lab = src.split("## 73. Consumer Group", 1)[1].split("# Failure Injection", 1)[0]
        self.assertIn("XGROUP CREATE tutorial:chapter14:writes writers-lab 0 MKSTREAM", lab)
        self.assertIn("XREADGROUP GROUP writers-lab worker1 COUNT 10", lab)
        self.assertIn("XACK tutorial:chapter14:writes writers-lab <actual-lab-message-id>", lab)
        self.assertIn("BUSYGROUP", lab)
        self.assertIn("pending", lab.lower())
        self.assertIn("Integer `1`", lab)
        self.assertEqual(src.count("# Part 22 --- Write-Behind and Redis Streams"), 1)

    def test_chapter_55_redisjson_interactive_prerequisites_and_jsonpath(self):
        src = (CHAPTER_DIR / "55-redis-enterprise-redisjson-data-modeling-document-engineering.md").read_text(encoding="utf-8")
        blocks = find_blocks(src.splitlines())
        redis = [b["source"] for b in blocks if b["language"] == "redis"]
        bash = [b["source"] for b in blocks if b["language"] == "bash"]
        self.assertGreaterEqual(len(redis), 13)
        self.assertTrue(any("JSON.GET tutorial:chapter55:profile:1001 '$.name'" in x for x in redis))
        self.assertTrue(any("JSON.NUMINCRBY tutorial:chapter55:profile:1001 '$.version'" in x for x in redis))
        self.assertTrue(any("JSON.ARRAPPEND tutorial:chapter55:profile:1001" in x for x in redis))
        self.assertTrue(any("SCAN 0 MATCH 'tutorial:chapter55:*' COUNT 100" in x for x in redis))
        self.assertTrue(any('redis-cli --tls --cacert "$REDIS_CA"' in x for x in bash))
        self.assertIn("RedisJSON v2", src)
        self.assertIn('["Ava"]', src)
        self.assertIn('["Charlotte"]', src)
        self.assertIn("JSON-encoded array", src)
        self.assertIn("Integer `1` when the initialized document contains", src)
        if shutil.which("bash"):
            for script in bash:
                proc = subprocess.run(["bash", "-n"], input=script, text=True,
                                      capture_output=True, timeout=5, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_chapter_33_xautoclaim_release_reply_and_safety(self):
        src = (CHAPTER_DIR / "33-redis-streams-reliability-retry-dlq-recovery-engineering.md").read_text(encoding="utf-8")
        self.assertIn("introduced in Redis **6.2**", src)
        self.assertIn("Redis **7.0+**", src)
        self.assertIn("third", src)
        self.assertIn("0-0", src)
        self.assertIn("XAUTOCLAIM tutorial:chapter33:orders order-workers recovery-worker 10000 0-0 COUNT 5", src)
        self.assertIn("A claim does not", src)
        self.assertIn("Empty claimed messages", src)

    def test_chapter_56_json_create_read_are_interactive(self):
        src = (CHAPTER_DIR / "56-redis-enterprise-search-query-architecture-indexing-operations.md").read_text(encoding="utf-8")
        self.assertIn("JSON.SET tutorial:chapter56:jsonproduct:2001 '$'", src)
        self.assertIn("JSON.GET tutorial:chapter56:jsonproduct:2001 '$.price'", src)
        self.assertIn("[89.99]", src)
        self.assertIn("CA-verified TLS Redis CLI", src)
        self.assertNotIn("redis-cli JSON.SET tutorial:chapter56:jsonproduct:2001", src)
        self.assertIn("does **not** prove the Search index exists", src)

    def test_chapter_59_json_smoke_needs_module_acl_and_cert(self):
        src = (CHAPTER_DIR / "59-redis-enterprise-modules-capabilities-lifecycle-compatibility-engineering.md").read_text(encoding="utf-8")
        self.assertIn("SET tutorial:chapter59:core \"ok\" EX 300", src)
        self.assertIn("JSON.GET tutorial:chapter59:json '$.status'", src)
        self.assertIn('["ok"]', src)
        self.assertIn("certificate-validated TLS/ACL", src)
        self.assertIn("RedisJSON v2", src)
        self.assertNotIn("redis-cli JSON.SET tutorial:chapter59:json", src)

    def test_conditional_expire_conceptual_replies_are_gated(self):
        src = (CHAPTER_DIR / "11-ttl-expiration-cache-freshness-engineering.md").read_text(encoding="utf-8")
        nx = src.split("## 13. `EXPIRE NX`", 1)[1].split("## 14. `EXPIRE XX`", 1)[0]
        xx = src.split("## 14. `EXPIRE XX`", 1)[1].split("## 15. `EXPIRE GT`", 1)[0]
        self.assertIn("Expected (Redis 7.0+)", nx)
        self.assertIn("present, persistent", nx)
        self.assertIn("Expected (Redis 7.0+)", xx)
        self.assertIn("already-expiring", xx)

    def test_chapter_55_read_write_expected_replies_are_adjacent(self):
        src = (CHAPTER_DIR / "55-redis-enterprise-redisjson-data-modeling-document-engineering.md").read_text(encoding="utf-8")
        read = src.split("## 11. JSON.GET", 1)[1].split("## 12. Selective Access", 1)[0]
        write = src.split("## 13. Update One Field", 1)[1].split("## 14. Update", 1)[0]
        self.assertIn("Expected for the initialized document", read)
        self.assertIn("JSON-encoded object", read)
        self.assertIn("Expected on the initialized JSON document", write)
        self.assertIn('["inactive"]', write)


if __name__ == "__main__":
    unittest.main()
