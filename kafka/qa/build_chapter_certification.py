#!/usr/bin/env python3
"""Generate an evidence-conservative Kafka chapter certification inventory."""
import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTER = re.compile(r"^(\d{3})-[^/]+\.md$")
FIELDS = ["chapter", "path", "title", "markdown_present", "static_qa",
          "runtime_qa", "certification", "evidence", "notes"]

def inventory():
    chapters = {}
    for path in ROOT.rglob("*.md"):
        if "qa" in path.relative_to(ROOT).parts:
            continue
        match = CHAPTER.match(path.name)
        if not match:
            continue
        number = int(match.group(1))
        if number in chapters:
            raise ValueError(f"Duplicate chapter {number:03}: {path} and {chapters[number]}")
        chapters[number] = path
    rows = []
    for n in range(1, 121):
        path = chapters.get(n)
        title = ""
        if path:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        rows.append({
            "chapter": f"{n:03}", "path": str(path.relative_to(ROOT)) if path else "",
            "title": title, "markdown_present": "YES" if path else "NO",
            "static_qa": "NOT_ATTRIBUTED",
            "runtime_qa": "NOT_TESTED",
            "certification": "NOT_CERTIFIED",
            "evidence": "",
            "notes": "Shared Kafka and Strimzi smoke tests do not certify this chapter."
                     if path else "Chapter markdown missing; investigate."
        })
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "qa" / "evidence"))
    args = parser.parse_args()
    rows = inventory()
    dest = Path(args.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / "chapter-certification.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "scope": "Kafka chapters 001-120",
        "expected_chapters": 120,
        "markdown_present": sum(r["markdown_present"] == "YES" for r in rows),
        "markdown_missing": [r["chapter"] for r in rows if r["markdown_present"] == "NO"],
        "chapter_runtime_certified": 0,
        "certification_policy": "No chapter is certified without mapped lab IDs, execution results, and per-lab evidence.",
        "shared_smoke_tests": "Separate integration gates; not attributed to individual chapters.",
    }
    (dest / "chapter-certification-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["markdown_present"] == 120 else 1

if __name__ == "__main__":
    raise SystemExit(main())
