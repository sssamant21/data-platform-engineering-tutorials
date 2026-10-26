#!/usr/bin/env python3
"""Select Kafka chapter runtime tests affected by a push (no untrusted code execution)."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED = tuple(f"{i:03d}" for i in range(1, 28))
CHAPTER = re.compile(r"(?:^|/)(\d{3})-[^/]+\.(?:md|py)$")
RUNNER = re.compile(r"^kafka/qa/run_chapter_(\d{3})\.py$")
WORKFLOW = re.compile(r"^\.github/workflows/kafka-chapter-(\d{3})\.yml$")

# Known storage dependencies avoid rerunning unrelated chapters for each new lab.
SCOPED_RUNTIME = {
    "kafka/qa/runtime/StorageAcceptance.java": ("021", "022", "025"),
    "kafka/qa/runtime/strimzi-three-node-persistent-ch021.yaml": ("021", "022", "023", "024", "025", "026"),
    "kafka/qa/run_chapter_021.py": ("021", "022", "023", "024", "025", "026", "027"),
    "kafka/qa/run_chapter_020.py": ("020", "025"),
    "kafka/qa/run_chapter_022.py": ("022", "025"),
    "kafka/qa/run_chapter_023.py": ("023", "025"),
    "kafka/qa/run_chapter_024.py": ("024", "025"),
    "kafka/qa/runtime/CompactionAcceptance.java": ("023", "025"),
    "kafka/qa/runtime/TieredPreflight.java": ("024",),
    "kafka/qa/runtime/NetworkAcceptance.java": ("026",),
    "kafka/qa/security_acceptance.py": ("027",),
    "kafka/qa/runtime/TlsAcceptance.java": ("027",),
    "kafka/qa/runtime/strimzi-three-node-mtls-ch027.yaml": ("027",),
}

def changed(before, after):
    zero = "0" * 40
    if before == zero:
        cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", after]
    else:
        cmd = ["git", "diff", "--name-only", f"{before}..{after}"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return [x for x in result.stdout.splitlines() if x]

def select(paths):
    selected = set()
    shared = False
    selector_changed = False
    for path in paths:
        if path.startswith("kafka/qa/evidence/"):
            continue
        if path == "kafka/qa/select_changed_chapters.py":
            selector_changed = True
            continue
        if path in SCOPED_RUNTIME:
            selected.update(ch for ch in SCOPED_RUNTIME[path] if ch in SUPPORTED)
            continue
        if path in ("kafka/qa/runtime_acceptance.py",
                    ".github/workflows/kafka-qa-orchestrator.yml"):
            shared = True
            continue
        for regex in (RUNNER, WORKFLOW, CHAPTER):
            match = regex.search(path)
            if match:
                chapter = match.group(1)
                if chapter in SUPPORTED:
                    selected.add(chapter)
                break
        else:
            if path.startswith("kafka/qa/runtime/") or path.startswith("kafka/kubernetes/"):
                shared = True
    if shared or (selector_changed and not selected):
        selected.update(SUPPORTED)
    return sorted(selected)

def fixture_for(chapter):
    if chapter == "027":
        return "strimzi-three-node-mtls-ch027.yaml"
    if chapter in ("021", "022", "023", "024", "025", "026"):
        return "strimzi-three-node-persistent-ch021.yaml"
    if chapter in ("004", "005", "007", "009", "010", "011", "012", "013", "014", "015", "016", "017", "018", "019", "020"):
        return "strimzi-three-node-ch004.yaml"
    return "strimzi-single-node.yaml"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    files = changed(args.before, args.after)
    selected = select(files)
    payload = {"include": [{"chapter": ch, "fixture": fixture_for(ch)} for ch in selected]}
    Path(args.output).write_text(json.dumps({"changed_files": files, "chapters": selected,
                                              "matrix": payload}, indent=2) + "\n")
    print(json.dumps(payload, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
