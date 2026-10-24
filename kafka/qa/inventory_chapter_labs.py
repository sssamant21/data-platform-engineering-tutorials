#!/usr/bin/env python3
"""Phase 5: inventory chapter lab signals without asserting runtime certification."""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CHAPTER = re.compile(r"^\d{3}[-_].*\.md$", re.I)
FENCE = re.compile(r"^\s*`{3,}(\w+)?", re.M)
SHELL = {"bash", "sh", "shell", "console", "powershell"}
K8S = {"yaml", "yml"}
RISK = re.compile(r"\b(kubectl\s+delete|helm\s+uninstall|kafka-topics(?:\.sh)?[^\n]*--delete|rm\s+-rf)\b", re.I)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("kafka"))
    p.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/chapter-certification-inventory.json"))
    args = p.parse_args()
    if not args.root.is_dir():
        p.error(f"missing root: {args.root}")
    chapters = sorted(f for f in args.root.rglob("*.md")
                      if CHAPTER.fullmatch(f.name)
                      and not any(part in {"qa", "evidence", "node_modules", ".git"} for part in f.parts))
    records = []
    for file in chapters:
        data = file.read_text(encoding="utf-8")
        languages = [m.group(1).lower() if m.group(1) else "" for m in FENCE.finditer(data)]
        records.append({
            "chapter": str(file.as_posix()),
            "fenced_blocks": len(languages),
            "shell_blocks": sum(x in SHELL for x in languages),
            "yaml_blocks": sum(x in K8S for x in languages),
            "has_lab_language": bool(re.search(r"\b(lab|hands.on|exercise|validation)\b", data, re.I)),
            "potentially_destructive_commands": bool(RISK.search(data)),
            "certification": "NOT_CERTIFIED",
            "runtime_evidence": None,
            "notes": "Inventory only; requires mapped executable test and successful evidence."
        })
    counts = Counter(r["certification"] for r in records)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Read-only Markdown discovery; no chapter commands executed.",
        "chapter_count": len(records),
        "certification_counts": dict(counts),
        "runtime_certified_count": 0,
        "chapters": records
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    csv_path = args.output.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]) if records else ["chapter", "certification"])
        writer.writeheader()
        writer.writerows(records)
    print(f"Chapter inventory: {len(records)} discovered, 0 runtime-certified by this scan.")
    print(f"Evidence: {args.output} and {csv_path}")
    if not chapters:
        print("ERROR: no chapter files discovered")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
