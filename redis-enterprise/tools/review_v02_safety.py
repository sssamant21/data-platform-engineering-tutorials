#!/usr/bin/env python3
"""Inventory EVERY flagged V02 Redis Enterprise command fence for human safety review.

Offline only: parses Markdown, never connects to Redis or executes examples.
A match means REVIEW, not UNSAFE. Intent cannot be certified by heuristics.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path

from validate_v02_examples import CHAPTER, find_blocks, SAFETY_PATTERNS, COMMAND_LANGS


def short(value: str, limit: int = 150) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit].replace("|", r"\|")


def nearby_text(lines: list[str], block: dict) -> tuple[str, str]:
    """Nearby prose; includes headings but avoids relying on this for verdicts."""
    before = []
    for line in reversed(lines[max(0, block["start"] - 18):block["start"]]):
        if re.match(r"^ {0,3}(?:\x60{3,}|~{3,})", line):
            break
        if line.strip() and not line.strip().startswith("---"):
            before.append(line)
    after = []
    for line in lines[block["end"] + 1:block["end"] + 13]:
        if re.match(r"^ {0,3}(?:\x60{3,}|~{3,})", line):
            break
        if line.strip() and not line.strip().startswith("---"):
            after.append(line)
    return short(" ".join(reversed(before[-5:])), 240), short(" ".join(after[:5]), 240)


def audit(root: Path) -> dict:
    findings = []
    for path in sorted(root.glob("*.md")):
        if not CHAPTER.fullmatch(path.name):
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for block in find_blocks(lines):
            source = block["source"]
            # Match the existing V02 scanner's predicate exactly.
            language = block["language"]
            explicit = (language in COMMAND_LANGS and
                        any(line.strip() and not line.lstrip().startswith("#")
                            for line in source.splitlines()))
            command = re.compile(
                r"^\s*(?:redis-cli|rladmin|kubectl|curl|docker|python(?:3)?|"
                r"GET|SET|MGET|HGET|HSET|EXPIRE|TTL|DEL|UNLINK|SCAN|INFO|PING|"
                r"XADD|XREADGROUP|XACK|FT\.SEARCH|JSON\.SET|ZADD|SADD|"
                r"FLUSHALL|FLUSHDB|KEYS)\b", re.I)
            untyped = language in {"text", "", "plaintext"} and any(
                command.search(line) for line in source.splitlines())
            if not (explicit or untyped):
                continue
            before, after = nearby_text(lines, block)
            for name, pattern in SAFETY_PATTERNS:
                match = pattern.search(source)
                if not match:
                    continue
                offset = source[:match.start()].count("\n")
                # Never print credential values from example commands.
                context_line = source.splitlines()[offset]
                if name == "inline_redis_password":
                    context_line = re.sub(r"(-a\s+)\S+", r"\1[REDACTED]", context_line)
                finding = {
                    "id": f"{int(path.name[:2]):02d}:{block['line']}:{name}",
                    "chapter": int(path.name[:2]),
                    "file": path.name,
                    "fence_line": block["line"],
                    "match_line": block["line"] + 1 + offset,
                    "pattern": name,
                    "language": language or "unlabeled",
                    "matched_line": short(context_line, 165),
                    "before": before,
                    "after": after,
                    "verdict": "NEEDS_CONTEXT_REVIEW",
                }
                findings.append(finding)
    return {"phase": "V02 safety review",
            "scope": "offline context inventory; each flagged block-pattern pair requires human adjudication",
            "summary": {"candidates": len(findings),
                        "by_pattern": dict(sorted(Counter(x["pattern"] for x in findings).items())),
                        "chapters_with_matches": len(set(x["chapter"] for x in findings))},
            "findings": findings}


def as_markdown(result: dict) -> str:
    lines = [
        "# Redis Enterprise V02 — Complete Safety Pattern Review Queue",
        "",
        "**These are candidate examples, NOT confirmed unsafe instructions.** Review context and classify each command before editing or approving. The audit does not run commands.",
        "",
        f"Total block-pattern findings: **{len(result['findings'])}**.",
        "",
        "| ID | Match line | Pattern | Example excerpt | Previous prose | Following prose | Verdict |",
        "|---|---:|---|---|---|---|---|",
    ]
    for f in result["findings"]:
        lines.append(f"| {f['id']} | {f['match_line']} | {f['pattern']} | "
                     f"{f['matched_line']} | {f['before']} | {f['after']} | "
                     f"{f['verdict']} |")
    lines.append("")
    lines.append("**Verdict rules:** prohibited/negative example, approved isolated lab, actionable recommended command requiring correction, conceptual-only, or needs further review. A negative word nearby is insufficient for an automated verdict.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--json-file", type=Path)
    ap.add_argument("--markdown-file", type=Path)
    ap.add_argument("--expected", type=int)
    args = ap.parse_args()
    result = audit(args.root)
    if args.json_file:
        args.json_file.parent.mkdir(parents=True, exist_ok=True)
        args.json_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.markdown_file:
        args.markdown_file.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_file.write_text(as_markdown(result), encoding="utf-8")
    print("SAFETY SUMMARY:", json.dumps(result["summary"], sort_keys=True))
    for item in result["findings"]:
        print("SAFETY CANDIDATE:", json.dumps(item, sort_keys=True))
    if args.expected is not None and len(result["findings"]) != args.expected:
        print(f"MISMATCH: expected {args.expected}, got {len(result['findings'])}")
        return 1
    print("Safety flags require independent contextual review; no live Redis commands executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
