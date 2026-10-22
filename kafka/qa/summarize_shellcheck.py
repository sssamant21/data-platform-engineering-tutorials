#!/usr/bin/env python3
"""Summarize Kafka ShellCheck diagnostics without executing curriculum commands.

Usage: python kafka/qa/summarize_shellcheck.py
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("kafka/qa/evidence/shellcheck-automated.json"))
    parser.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/shellcheck-review.md"))
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8-sig"))
    blocks = report["blocks"]
    statuses = Counter(block.get("status", "UNKNOWN") for block in blocks)
    rules = Counter()
    by_chapter = defaultdict(list)
    for block in blocks:
        for diagnostic in block.get("diagnostics", []):
            rule = diagnostic.get("rule", "UNKNOWN")
            rules[rule] += 1
            by_chapter[block["path"]].append((block, diagnostic))
    lines = [
        "# Kafka embedded ShellCheck — automated review",
        "",
        "Static lint only; no Kafka labs or shell commands executed.",
        "",
        f"- Blocks scanned: **{len(blocks)}**",
        f"- Clean blocks: **{statuses['PASS']}**",
        f"- Blocks requiring review: **{statuses['REVIEW']}**",
        f"- Tool errors: **{statuses['ERROR']}**",
        f"- Incomplete scan: **{'no' if report.get('complete_scan') else 'yes'}**",
        "",
        "## Diagnostic rules",
        "",
        "| Rule | Occurrences |",
        "|---|---:|",
    ]
    lines.extend(f"| {rule} | {count} |" for rule, count in rules.most_common())
    lines += ["", "## Findings by chapter", ""]
    for chapter, items in sorted(by_chapter.items()):
        lines.extend([f"### `{chapter}`", "", "| Markdown line | Rule | Severity | Message |",
                      "|---:|---|---|---|"])
        for _, d in items:
            message = str(d.get("message", "")).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {d.get('line', '?')} | {d.get('rule', '?')} | {d.get('severity', '?')} | {message} |")
        lines.append("")
    if not by_chapter:
        lines.append("No diagnostics.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Reviewed {len(blocks)} blocks, {sum(rules.values())} diagnostics in {len(by_chapter)} chapters.")
    print(f"Review report: {args.output}")
    return 2 if statuses["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
