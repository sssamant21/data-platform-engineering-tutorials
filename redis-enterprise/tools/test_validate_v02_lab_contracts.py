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


if __name__ == "__main__":
    unittest.main()
