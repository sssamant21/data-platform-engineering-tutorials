#!/usr/bin/env python3
"""PostgreSQL curriculum V01 static structure and Markdown-link validator.

Read-only by default. Uses only the Python standard library.
Run from any directory:
  python postgresql/validation/validate_v01.py
  python postgresql/validation/validate_v01.py --json-out /tmp/pg-v01.json
No PostgreSQL server is required. This does NOT certify runtime lab execution.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
FENCE = re.compile(r"^\s{0,3}((?:\x60{3,})|(?:~{3,}))")
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^)\n]+)\)")
CHAPTER_LINK = re.compile(r"chapters/(\d{3})-[^) \n]+\.md")
NUMBERED_FILE = re.compile(r"^(\d{3})-[^/]+\.md$")


def numbered_inventory(folder):
    files = sorted(folder.glob("*.md"))
    by_number = {}
    invalid = []
    for path in files:
        match = NUMBERED_FILE.match(path.name)
        if match:
            by_number.setdefault(int(match.group(1)), []).append(path)
        else:
            invalid.append(str(path.relative_to(REPO)))
    return files, by_number, invalid


def check_markdown(path):
    issues = []
    relative_links = 0
    opening = None
    opening_line = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if opening is None:
                opening = marker
                opening_line = lineno
            elif marker[0] == opening[0] and len(marker) >= len(opening) and not line[fence.end():].strip():
                opening = None
            continue
        if opening is not None:
            continue
        # Avoid interpreting Markdown examples inside inline code as links.
        line = re.sub(r"\x60[^\x60\n]+\x60", "", line)
        for match in INLINE_LINK.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<"):
                raw = raw.split(">", 1)[0][1:]
            else:
                raw = re.split(r'\s+["\x27]', raw, maxsplit=1)[0]
            if not raw or raw.startswith(("#", "//")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw):
                continue
            target_path = unquote(urlsplit(raw).path)
            if not target_path:
                continue
            relative_links += 1
            dest = (path.parent / target_path).resolve()
            if not dest.is_relative_to(REPO) or not dest.exists():
                issues.append({
                    "kind": "missing_local_target",
                    "file": str(path.relative_to(REPO)),
                    "line": lineno,
                    "target": raw,
                })
    if opening is not None:
        issues.append({
            "kind": "unclosed_fence",
            "file": str(path.relative_to(REPO)),
            "line": opening_line,
        })
    return issues, relative_links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, help="Save machine-readable evidence to the given path")
    args = parser.parse_args()
    errors = []
    warnings = []
    expected = set(range(1, 101))
    chapter_files, chapters, invalid_chapters = numbered_inventory(ROOT / "chapters")
    lab_files, labs, invalid_labs = numbered_inventory(ROOT / "labs")
    for label, numbered, invalid in (
        ("chapters", chapters, invalid_chapters),
        ("top_level_labs", labs, invalid_labs),
    ):
        missing = sorted(expected - set(numbered))
        extra = sorted(set(numbered) - expected)
        duplicate = sorted(n for n, paths in numbered.items() if len(paths) != 1)
        if missing or extra or duplicate or invalid:
            errors.append({
                "kind": "numbering_or_inventory",
                "scope": label,
                "missing": missing,
                "extra": extra,
                "duplicate": duplicate,
                "unnumbered": invalid,
            })
    nav = {}
    for filename in ("README.md", "PROGRESS.md", "MASTER-PLAN.md"):
        path = ROOT / filename
        if not path.exists():
            errors.append({"kind": "missing_index", "file": filename})
            continue
        refs = {int(x) for x in CHAPTER_LINK.findall(path.read_text(encoding="utf-8"))}
        missing = sorted(expected - refs)
        nav[filename] = {"linked_chapters": len(refs & expected), "missing_numbers": missing}
        if missing:
            errors.append({"kind": "incomplete_chapter_navigation", "file": filename, "missing": missing})
    md_files = sorted(ROOT.rglob("*.md"))
    link_total = 0
    for path in md_files:
        problems, count = check_markdown(path)
        errors.extend(problems)
        link_total += count
    for path in chapter_files:
        if path.stat().st_size < 3000:
            warnings.append({"kind": "short_chapter_review", "file": str(path.relative_to(REPO)), "bytes": path.stat().st_size})
    for path in lab_files:
        if path.stat().st_size < 2000:
            warnings.append({"kind": "short_lab_review", "file": str(path.relative_to(REPO)), "bytes": path.stat().st_size})
    report = {
        "version": "V01",
        "scope": "static filesystem inventory, Markdown local targets, code fences, and chapter navigation",
        "runtime_testing": "NOT_EXECUTED",
        "overall": "FAIL" if errors else "PASS_STATIC_ONLY",
        "summary": {
            "chapter_files": len(chapter_files),
            "top_level_labs": len(lab_files),
            "markdown_files_scanned": len(md_files),
            "relative_links_checked": link_total,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "navigation": nav,
        "errors": errors,
        "warnings": warnings,
    }
    output = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output + "\n", encoding="utf-8")
    print(output)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
