#!/usr/bin/env python3
"""V01 Redis Enterprise curriculum static audit. Never connects to Redis.

Checks the current 01-80 chapter layout, Markdown fences and local file links,
plus Python code-block syntax. It deliberately does NOT execute tutorial code.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import textwrap
from pathlib import Path
from urllib.parse import unquote, urlsplit

EXPECTED_CHAPTERS = 80
CHAPTER = re.compile(r"^(\d{2})-[^/]+\.md$")
TITLE = re.compile(r"^#\s+Chapter\s+0*(\d+)\b", re.I)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")
LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>\n]+>|[^)\n]+)\)")
PYTHON_LANGUAGES = {"python", "python3", "py"}


def issue(severity: str, check: str, path: str, line: int, detail: str) -> dict:
    return {"severity": severity, "check": check, "path": path,
            "line": line, "detail": detail}


def extract_blocks_and_prose(text: str, path: str, findings: list[dict]):
    """Return (fenced blocks, prose preserving original source line numbers)."""
    blocks = []
    prose = []
    opening = None
    content = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        fence = FENCE.match(line)
        if opening is None:
            if fence:
                language = fence.group(2).strip().split(None, 1)[0].lower() if fence.group(2).strip() else ""
                opening = (fence.group(1)[0], len(fence.group(1)), language, line_number)
                content = []
            else:
                prose.append((line_number, line))
        elif fence and fence.group(1)[0] == opening[0] and len(fence.group(1)) >= opening[1] and not fence.group(2).strip():
            blocks.append({"language": opening[2], "line": opening[3],
                           "source": "\n".join(content)})
            opening = None
        else:
            content.append(line)
    if opening is not None:
        findings.append(issue("error", "unclosed_fence", path, opening[3],
                              "Opening code fence has no matching closing fence"))
    return blocks, prose


def audit(root: Path, expected: int = EXPECTED_CHAPTERS,
          strict_python: bool = False, minimum_bytes: int = 12000) -> dict:
    root = root.resolve()
    findings: list[dict] = []
    chapters = []
    summary = {"expected_chapters": expected, "chapters_found": 0,
               "code_blocks": 0, "python_blocks": 0, "python_syntax_errors": 0,
               "relative_links_checked": 0, "errors": 0, "warnings": 0}
    if not root.is_dir():
        findings.append(issue("error", "missing_root", str(root), 0,
                              "Redis Enterprise chapter directory does not exist"))
        summary["errors"] = 1
        return {"phase": "V01", "scope": "offline static checks only; no Redis execution",
                "summary": summary, "findings": findings, "chapters": chapters}

    files = sorted(path for path in root.glob("*.md") if CHAPTER.fullmatch(path.name))
    summary["chapters_found"] = len(files)
    by_number = {}
    for path in files:
        by_number.setdefault(int(CHAPTER.fullmatch(path.name).group(1)), []).append(path.name)
    for number in range(1, expected + 1):
        if number not in by_number:
            findings.append(issue("error", "missing_chapter", "redis-enterprise/", 0,
                                  f"Chapter {number:02d} is missing"))
    for number, names in sorted(by_number.items()):
        if len(names) > 1:
            findings.append(issue("error", "duplicate_chapter", "redis-enterprise/", 0,
                                  f"Chapter {number:02d} has multiple files: {names}"))
        if not 1 <= number <= expected:
            findings.append(issue("error", "unexpected_chapter", "redis-enterprise/", 0,
                                  f"Chapter number {number:02d} is outside 01-{expected:02d}"))

    repo_root = root.parent
    for path in files:
        name = path.name
        rel = path.relative_to(repo_root).as_posix()
        number = int(CHAPTER.fullmatch(name).group(1))
        text = path.read_text(encoding="utf-8-sig")
        chapter = {"number": number, "path": rel, "bytes": len(text.encode("utf-8")),
                   "code_blocks": 0, "python_blocks": 0, "relative_links": 0}
        chapters.append(chapter)
        if chapter["bytes"] < minimum_bytes:
            findings.append(issue("warning", "short_chapter", rel, 1,
                                  f"Only {chapter['bytes']} bytes; review depth and lab coverage"))
        first_title = next(((i, line) for i, line in enumerate(text.splitlines(), 1)
                            if line.startswith("# ")), None)
        if first_title is None or not (match := TITLE.match(first_title[1])) or int(match.group(1)) != number:
            findings.append(issue("error", "chapter_title", rel,
                                  first_title[0] if first_title else 1,
                                  "First H1 must identify the correct Chapter NN"))

        blocks, prose = extract_blocks_and_prose(text, rel, findings)
        chapter["code_blocks"] = len(blocks)
        summary["code_blocks"] += len(blocks)
        for block in blocks:
            if block["language"] in PYTHON_LANGUAGES:
                chapter["python_blocks"] += 1
                summary["python_blocks"] += 1
                try:
                    ast.parse(textwrap.dedent(block["source"]), filename=rel)
                except SyntaxError as exc:
                    summary["python_syntax_errors"] += 1
                    findings.append(issue("error" if strict_python else "warning",
                                          "python_syntax", rel,
                                          block["line"] + (exc.lineno or 1),
                                          f"Python fenced example cannot be parsed: {exc.msg}"))

        for line_no, line in prose:
            for match in LINK.finditer(line):
                target = match.group(1).strip()
                if target.startswith("<") and target.endswith(">"):
                    target = target[1:-1]
                else:
                    target = re.split(r"\s+[\"']", target, maxsplit=1)[0]
                if not target or target.startswith("#") or target.startswith("//"):
                    continue
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                file_part = unquote(parsed.path)
                resolved = (repo_root / file_part.lstrip("/") if file_part.startswith("/")
                            else path.parent / file_part).resolve()
                chapter["relative_links"] += 1
                summary["relative_links_checked"] += 1
                if not resolved.is_relative_to(repo_root):
                    findings.append(issue("error", "outside_repository_link", rel, line_no,
                                          f"Relative link escapes repository: {target}"))
                elif not resolved.exists():
                    findings.append(issue("error", "broken_relative_link", rel, line_no,
                                          f"Target does not exist: {target}"))

    summary["errors"] = sum(f["severity"] == "error" for f in findings)
    summary["warnings"] = sum(f["severity"] == "warning" for f in findings)
    return {"phase": "V01", "scope": "offline static checks only; no Redis execution",
            "summary": summary, "findings": findings, "chapters": chapters}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parents[1],
                        help="Path containing 01-80 chapter Markdown files")
    parser.add_argument("--expected", type=int, default=EXPECTED_CHAPTERS)
    parser.add_argument("--strict-python", action="store_true",
                        help="Fail on non-parsing illustrative Python snippets")
    parser.add_argument("--json-file", type=Path,
                        help="Write an audit result JSON file at this location")
    args = parser.parse_args(argv)
    result = audit(args.root, expected=args.expected, strict_python=args.strict_python)
    if args.json_file:
        args.json_file.parent.mkdir(parents=True, exist_ok=True)
        args.json_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = result["summary"]
    print(f"Redis Enterprise V01: {summary['chapters_found']}/{summary['expected_chapters']} chapters; "
          f"{summary['code_blocks']} fenced blocks; {summary['python_blocks']} Python blocks; "
          f"{summary['relative_links_checked']} relative links", flush=True)
    print(f"Findings: {summary['errors']} errors, {summary['warnings']} warnings "
          f"({summary['python_syntax_errors']} Python syntax warnings/errors)")
    for finding in result["findings"]:
        print(f"{finding['severity'].upper()}: {finding['path']}:{finding['line']} "
              f"[{finding['check']}] {finding['detail']}")
    print("LIMITATION: Static audit only. Code blocks were not executed; Redis runtime, "
          "TLS, HA, backup and recovery remain unverified.")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
