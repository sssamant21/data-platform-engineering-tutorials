# Kafka curriculum QA — automated repository audit

This directory contains the first **offline, read-only** QA gate for the 120-chapter Kafka curriculum.

## Requirements

- Python 3.10 or newer
- A complete checkout of `sssamant21/data-platform-engineering-tutorials`
- No pip packages, cloud credentials or Kafka cluster required

## Run from Windows PowerShell

```powershell
git clone https://github.com/sssamant21/data-platform-engineering-tutorials.git
cd data-platform-engineering-tutorials
python kafka/qa/audit_curriculum.py --root kafka --output kafka/qa/evidence/repository-audit.json
if ($LASTEXITCODE -ne 0) { throw "Kafka repository audit failed: $LASTEXITCODE" }
Get-Content kafka/qa/evidence/repository-audit.json
```

If the repository is already cloned, run `git pull --ff-only` and start at the `python` command.

## What is checked

1. Exactly one numbered chapter file for each chapter 001–120.
2. Exactly one numbered README link per chapter, with no omissions.
3. Every Markdown file in `kafka/` for empty files and unclosed code fences.
4. Relative Markdown links and image links, resolved relative to the source file.
5. Heading fragments in linked Markdown (best-effort warning).
6. Machine-readable evidence with issue code, file, severity and detail.

**PASS** means no critical static errors. Warnings require human review. This does not establish valid Kafka commands, YAML schema compatibility, runtime lab success, security sign-off or production readiness.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Static checks passed (warnings possible) |
| 1 | Static errors found |
| 2 | Invalid input or filesystem failure |

## Evidence policy

Generated JSON should be attached to the QA review with the checkout commit SHA, Python version, UTC timestamp and reviewer identity. Do not upload cloud credentials or secrets.

## Next automation gates

- Add a syntax-aware fenced-block extractor and validate only complete manifests and scripts.
- Pin test versions and execute Kubernetes schema validation against a disposable cluster.
- Run synthetic Kafka producer/consumer labs with independent event-ID reconciliation.
- Require technical and security reviewer sign-off before certification.

**Publication is not runtime certification.**
