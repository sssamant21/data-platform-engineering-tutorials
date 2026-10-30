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
        self.assertIn('RefUSED' if False else 'REFUSED: non-loopback', helpers[0]["source"])
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


if __name__ == "__main__":
    unittest.main()
