#!/usr/bin/env python3
"""Static audit for the 120-chapter Kubernetes-first Kafka curriculum.

Usage (from any directory):
    python kafka/qa/audit_curriculum.py --root kafka --output kafka/qa/evidence/repository-audit.json

No cloud credentials, Kafka cluster, external Python packages or network access required.
Exit codes: 0 PASS, 1 FAIL, 2 invalid invocation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

CHAPTER_NAME = re.compile(r"^(\d{3})-[\w.-]+\.md$")
MARKDOWN_LINK = re.compile(r"!?(?:\[[^\]]*\])\((?:<([^>]+)>|([^)]*))\)")
REFERENCE_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", re.MULTILINE)
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
LINKED_CHAPTER = re.compile(r"(?:^|/)(\d{3})-[^/]+\.md$")
SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "javascript:")


def markdown_links(text: str) -> list[str]:
    # Inline links, images and reference definitions; ignore fenced code.
    out = []
    for line in outside_fences(text).splitlines():
        for m in MARKDOWN_LINK.finditer(line):
            dest = (m.group(1) or m.group(2) or "").strip()
            if dest and not dest.startswith(("'", '"')):
                # Strip optional Markdown link title from simple non-angle destinations.
                if " " in dest and not dest.startswith("#"):
                    dest = dest.split(" ", 1)[0]
                out.append(dest)
    for m in REFERENCE_DEF.finditer(outside_fences(text)):
        out.append(m.group(1) or m.group(2))
    return out


def outside_fences(text: str) -> str:
    lines = []
    fence_char = None
    fence_len = 0
    for line in text.splitlines():
        m = FENCE.match(line)
        if m:
            token, tail = m.groups()
            if fence_char is None:
                fence_char, fence_len = token[0], len(token)
            elif token[0] == fence_char and len(token) >= fence_len and not tail.strip():
                fence_char, fence_len = None, 0
            lines.append("")
        else:
            lines.append(line if fence_char is None else "")
    return "\n".join(lines)


def fences_balanced(text: str) -> bool:
    # Do not assume all fences use exactly three backticks.
    fence_char = None
    fence_len = 0
    for line in text.splitlines():
        m = FENCE.match(line)
        if not m:
            continue
        token, tail = m.groups()
        if fence_char is None:
            fence_char, fence_len = token[0], len(token)
        elif token[0] == fence_char and len(token) >= fence_len and not tail.strip():
            fence_char, fence_len = None, 0
    return fence_char is None


def slugs(text: str) -> set[str]:
    found = set()
    collisions = Counter()
    for line in outside_fences(text).splitlines():
        m = HEADING.match(line)
        if not m:
            continue
        title = re.sub(r"<[^>]+>", "", m.group(1))
        title = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", title)
        title = title.lower().strip()
        title = re.sub(r"[^\w\- ]", "", title, flags=re.UNICODE)
        title = re.sub(r"\s+", "-", title)
        collisions[title] += 1
        suffix = collisions[title] - 1
        found.add(title if suffix == 0 else f"{title}-{suffix}")
    return found


def audit(root: Path) -> dict:
    issues = []
    def issue(severity, code, path, detail):
        issues.append({"severity": severity, "code": code, "path": path, "detail": detail})

    if not root.is_dir() or not (root / "README.md").is_file():
        raise ValueError(f"Kafka root must contain README.md: {root}")

    chapter_files = sorted(p for p in root.rglob("*.md") if CHAPTER_NAME.fullmatch(p.name))
    chapter_by_number = {}
    for p in chapter_files:
        n = int(CHAPTER_NAME.fullmatch(p.name).group(1))
        chapter_by_number.setdefault(n, []).append(p)
    for n in range(1, 121):
        matches = chapter_by_number.get(n, [])
        if not matches:
            issue("error", "MISSING_CHAPTER_FILE", "", f"Chapter {n:03d} missing")
        elif len(matches) > 1:
            issue("error", "DUPLICATE_CHAPTER_NUMBER", "", f"Chapter {n:03d}: {', '.join(str(x.relative_to(root)) for x in matches)}")
    for n in sorted(chapter_by_number):
        if n > 120 or n < 1:
            issue("warning", "OUT_OF_SCOPE_CHAPTER", "", f"Chapter {n:03d}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    readme_refs = []
    for link in markdown_links(readme):
        decoded = unquote(urlsplit(link).path)
        m = LINKED_CHAPTER.search(decoded)
        if m:
            readme_refs.append((int(m.group(1)), decoded))
    index_counts = Counter(n for n, _ in readme_refs)
    for n in range(1, 121):
        if index_counts[n] == 0:
            issue("error", "MISSING_README_CHAPTER_LINK", "README.md", f"Chapter {n:03d}")
        elif index_counts[n] > 1:
            issue("warning", "DUPLICATE_README_CHAPTER_LINK", "README.md", f"Chapter {n:03d} has {index_counts[n]} links")

    checked_links = 0
    scanned = 0
    for p in sorted(root.rglob("*.md")):
        # Include supplementary docs in link and fence checks.
        rel = p.relative_to(root).as_posix()
        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeError as e:
            issue("error", "ENCODING_ERROR", rel, str(e))
            continue
        scanned += 1
        if not content.strip():
            issue("error", "EMPTY_MARKDOWN", rel, "Empty file")
        if not fences_balanced(content):
            issue("error", "UNCLOSED_CODE_FENCE", rel, "Unbalanced fenced code block")
        for dest in markdown_links(content):
            if dest.startswith(SKIP_SCHEMES) or dest.startswith("//"):
                continue
            parsed = urlsplit(dest)
            if parsed.scheme or parsed.netloc:
                continue
            target = (p.parent / unquote(parsed.path)).resolve() if parsed.path else p.resolve()
            checked_links += 1
            # Reject traversal outside repository root; allows sibling dirs within kafka.
            try:
                target.relative_to(root.resolve())
            except ValueError:
                issue("warning", "EXTERNAL_RELATIVE_PATH", rel, dest)
                continue
            if not target.exists():
                issue("error", "BROKEN_RELATIVE_LINK", rel, dest)
            elif parsed.fragment and target.suffix.lower() == ".md":
                fragment = unquote(parsed.fragment).lower()
                try:
                    target_slugs = slugs(target.read_text(encoding="utf-8"))
                except UnicodeError:
                    continue
                if fragment not in target_slugs and not fragment.startswith("user-content-"):
                    issue("warning", "UNVERIFIED_HEADING_ANCHOR", rel, dest)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "target_chapters": 120,
        "actual_numbered_chapter_files": len(chapter_files),
        "unique_chapter_numbers": len(chapter_by_number),
        "readme_numbered_links": len(readme_refs),
        "readme_unique_chapter_numbers": len(index_counts),
        "markdown_files_scanned": scanned,
        "local_links_checked": checked_links,
        "errors": sum(i["severity"] == "error" for i in issues),
        "warnings": sum(i["severity"] == "warning" for i in issues),
        "status": "FAIL" if any(i["severity"] == "error" for i in issues) else "PASS",
        "issues": issues,
        "scope_note": "Static Markdown audit only; does not execute labs or validate Kubernetes/Kafka semantics."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("kafka"))
    parser.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/repository-audit.json"))
    args = parser.parse_args()
    try:
        report = audit(args.root.resolve())
    except (OSError, ValueError) as e:
        print(f"Audit invocation failed: {e}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']}: {report['actual_numbered_chapter_files']} chapter files, "
          f"{report['markdown_files_scanned']} Markdown files, "
          f"{report['local_links_checked']} local links, "
          f"{report['errors']} errors, {report['warnings']} warnings")
    print(f"Evidence: {args.output}")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
