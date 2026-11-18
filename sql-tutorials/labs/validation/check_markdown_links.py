#!/usr/bin/env python3
"""Parser-aware local Markdown link QA for SQL Tutorials. No database access.

Install: python -m pip install "markdown-it-py>=3,<5"
Run from repository root: python sql-tutorials/labs/validation/check_markdown_links.py
Optional: --json sql-tutorials/labs/validation/markdown-qa-results.json

Scope: all SQL Tutorials Markdown files, local inline/reference links, image sources and fragments, using parsed tokens.
External HTTP(S) URLs are counted, not network-tested. HTML hrefs and GitHub's
renderer-specific slug edge cases require separate review.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from markdown_it import MarkdownIt
except ImportError:
    sys.exit('Dependency missing: python -m pip install "markdown-it-py>=3,<5"')

ROOT = Path(__file__).resolve().parents[3]
SCOPE = ROOT / "sql-tutorials"
MD = MarkdownIt("commonmark")
HEADING_RE = re.compile(r"[^\w\- ]", re.UNICODE)


def github_slug(value):
    value = value.strip().lower()
    return HEADING_RE.sub("", value).replace(" ", "-")


def text_content(token):
    if token.type in ("text", "code_inline"):
        return token.content
    if token.type in ("softbreak", "hardbreak"):
        return " "
    return "".join(text_content(child) for child in (token.children or []))


def headings(path):
    tokens = MD.parse(path.read_text(encoding="utf-8"))
    counts = Counter()
    slugs = set()
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and index + 1 < len(tokens):
            base = github_slug(text_content(tokens[index + 1]))
            suffix = counts[base]
            counts[base] += 1
            slugs.add(base if suffix == 0 else f"{base}-{suffix}")
    return slugs


def links(tokens):
    for token in tokens:
        if token.type == "link_open":
            yield token.attrGet("href") or ""
        elif token.type == "image":
            yield token.attrGet("src") or ""
        if token.children:
            yield from links(token.children)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="output", type=Path)
    args = parser.parse_args()
    chapters = sorted(path for path in SCOPE.glob("part-*/*.md")
                      if re.match(r"^\d{3}-", path.name))
    # Include lab guides, validation evidence and other Markdown, not just chapters.
    # Otherwise broken links in these documents would silently escape QA.
    files = sorted(SCOPE.rglob("*.md"))
    counts_expected = {SCOPE / name for name in ("MASTER-TOC.md", "README.md", "STATUS-TRACKER.md")}
    for required in sorted(counts_expected):
        if required not in files:
            files.append(required)
    files = sorted(set(files))
    issues = []
    # A count of 120 files alone does not prove that chapters 001–120
    # are present exactly once or located in their expected ten-chapter parts.
    by_number = {}
    for path in chapters:
        number = int(path.name[:3])
        by_number.setdefault(number, []).append(path)
        expected_part = (number - 1) // 10 + 1 if 1 <= number <= 120 else None
        if expected_part is None or not path.parent.name.startswith(f"part-{expected_part:02d}-"):
            issues.append({"file": str(path.relative_to(ROOT)),
                           "issue": "chapter number outside expected part"})
    for number in range(1, 121):
        matches = by_number.get(number, [])
        if not matches:
            issues.append({"chapter": f"{number:03d}", "issue": "missing chapter number"})
        elif len(matches) > 1:
            issues.append({"chapter": f"{number:03d}", "issue": "duplicate chapter number",
                           "files": [str(p.relative_to(ROOT)) for p in matches]})
    counts = Counter()
    anchor_cache = {}
    for path in files:
        if not path.is_file():
            issues.append({"file": str(path.relative_to(ROOT)), "issue": "missing source"})
            continue
        counts["files"] += 1
        tokens = MD.parse(path.read_text(encoding="utf-8"))
        for href in links(tokens):
            counts["links"] += 1
            parts = urlsplit(href)
            if parts.scheme in ("http", "https"):
                counts["external_not_tested"] += 1
                continue
            if parts.scheme or parts.netloc or href.startswith("//"):
                counts["other_scheme_skipped"] += 1
                continue
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path.resolve()
            if not target.is_relative_to(ROOT.resolve()):
                issues.append({"file": str(path.relative_to(ROOT)), "href": href, "issue": "outside repository"})
                continue
            if not target.exists():
                issues.append({"file": str(path.relative_to(ROOT)), "href": href, "issue": "missing target"})
                continue
            counts["local_paths_ok"] += 1
            if parts.fragment:
                counts["fragments_checked"] += 1
                if target.suffix.lower() != ".md":
                    issues.append({"file": str(path.relative_to(ROOT)), "href": href, "issue": "fragment on non-Markdown target: manual review"})
                    continue
                if target not in anchor_cache:
                    anchor_cache[target] = headings(target)
                if unquote(parts.fragment) not in anchor_cache[target]:
                    issues.append({"file": str(path.relative_to(ROOT)), "href": href, "issue": "unmatched approximate GitHub heading slug"})
    report = {"scope": "all Markdown files under sql-tutorials, including 120 numbered chapters",
              "chapter_files": len(chapters), "counts": dict(counts),
              "issues": issues,
              "limitations": ["External URLs not requested over network",
                              "Raw HTML hrefs not parsed",
                              "GitHub heading-slug equivalence is approximate",
                              "SQL syntax and PostgreSQL 18 execution not tested"]}
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if issues or len(chapters) != 120 else 0


if __name__ == "__main__":
    sys.exit(main())
