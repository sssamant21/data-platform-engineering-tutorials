#!/usr/bin/env python3
"""Select Kafka chapter runtime tests affected by a push (no untrusted code execution)."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED = tuple(f"{i:03d}" for i in range(1, 16))
CHAPTER = re.compile(r"(?:^|/)(\d{3})-[^/]+\.(?:md|py)$")
RUNNER = re.compile(r"^kafka/qa/run_chapter_(\d{3})\.py$")
WORKFLOW = re.compile(r"^\.github/workflows/kafka-chapter-(\d{3})\.yml$")

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
    for path in paths:
        if path.startswith("kafka/qa/evidence/"):
            continue
        if path in ("kafka/qa/select_changed_chapters.py",
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
    if shared:
        selected.update(SUPPORTED)
    return sorted(selected)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    files = changed(args.before, args.after)
    selected = select(files)
    payload = {"include": [{"chapter": ch, "fixture": (
        "strimzi-three-node-ch004.yaml" if ch in ("004", "005", "007", "009", "010", "011", "012", "013", "014", "015")
        else "strimzi-single-node.yaml")} for ch in selected]}
    Path(args.output).write_text(json.dumps({"changed_files": files, "chapters": selected,
                                              "matrix": payload}, indent=2) + "\n")
    print(json.dumps(payload, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
