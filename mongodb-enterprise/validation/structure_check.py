#!/usr/bin/env python3
"""Read-only L0 structure and local-link validation for the 80-chapter curriculum."""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

CHAPTER = re.compile(r"^(\d{2})-.*\.md$")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^#{1,6}\s+\S", re.M)

def audit(root):
    chapters = {}
    errors = []
    warnings = []
    for path in sorted(root.glob("*.md")):
        match = CHAPTER.fullmatch(path.name)
        if not match:
            continue
        number = int(match.group(1))
        if number in chapters:
            errors.append(f"Duplicate chapter {number:02d}: {path.name}")
        chapters[number] = path
    for number in range(1, 81):
        if number not in chapters:
            errors.append(f"Missing chapter {number:02d}")
    for number, path in sorted(chapters.items()):
        if not 1 <= number <= 80:
            errors.append(f"Unexpected numbered chapter: {path.name}")
        content = path.read_text(encoding="utf-8")
        if not HEADING.search(content):
            errors.append(f"{path.name}: no Markdown heading")
        if len(FENCE.findall(content)) % 2:
            errors.append(f"{path.name}: unbalanced code fences")
        for target in LINK.findall(content):
            target = target.strip().split("#", 1)[0].split("?", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if " " in target:
                warnings.append(f"{path.name}: manual link review: {target}")
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                warnings.append(f"{path.name}: link outside curriculum: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.name}: missing local link: {target}")
    return {
        "schema": "mongodb-phase4-structure-v1",
        "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "level": "L0",
        "chapters_found": len(chapters),
        "expected_chapters": 80,
        "passed": not errors,
        "runtime_certified": False,
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "Does not execute chapter scripts or MongoDB commands",
            "Does not validate Markdown anchor fragments or remote URLs",
            "Does not establish security, backup, runtime or production readiness"
        ]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"Not a directory: {args.root}")
    result = audit(args.root)
    data = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(data, encoding="utf-8")
    else:
        print(data, end="")
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
