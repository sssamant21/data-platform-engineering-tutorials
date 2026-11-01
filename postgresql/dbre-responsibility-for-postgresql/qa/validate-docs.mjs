#!/usr/bin/env node
/**
 * PostgreSQL DBRE responsibility documentation V01 static validator.
 * Usage (from repository root):
 *   node postgresql/dbre-responsibility-for-postgresql/qa/validate-docs.mjs
 *
 * Requires Node.js 18+, no external dependencies. Purely reads local files.
 * This checks Markdown and guarded command patterns, NOT SQL syntax or execution.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const qaDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(qaDir, "../../..");
const trackDir = path.join(root, "postgresql", "dbre-responsibility-for-postgresql");
const guideNames = [
  "01-ownership-and-raci.md",
  "02-daily-weekly-monthly-operations.md",
  "03-monitoring-alerting-slos.md",
  "04-incident-response-troubleshooting.md",
  "05-capacity-growth-finops.md",
  "06-backup-high-availability-disaster-recovery.md",
  "07-data-lifecycle-safe-maintenance.md",
];
const files = [...guideNames, "README.md", "VALIDATION.md"];
const failures = [];
const stats = [];
const unsafeLine = /^\s*(?:DROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX)\b|TRUNCATE\b|DELETE\s+FROM\b|ALTER\s+SYSTEM\b|SELECT\s+pg_(?:promote|terminate_backend|cancel_backend|drop_replication_slot)\s*\(|pg_resetwal\b|rm\s+-rf\b)/i;

for (const name of files) {
  const full = path.join(trackDir, name);
  if (!fs.existsSync(full)) {
    failures.push(name + ": missing required file");
    continue;
  }
  const body = fs.readFileSync(full, "utf8");
  const lines = body.split(/\r?\n/);
  let fence = null;
  let inTable = false;
  let expectedColumns = null;
  let codeBlocks = 0;
  let internalLinks = 0;
  let externalLinks = 0;
  const numbered = [];
  let referenceCount = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const f = line.match(/^\s*(~{3,}|`{3,})([A-Za-z0-9_-]*)\s*$/);
    if (f) {
      if (!fence) {
        fence = { marker: f[1], start: i + 1 };
        codeBlocks++;
        if (!f[2]) failures.push(name + ":" + (i + 1) + " fenced code block lacks language");
      } else if (fence.marker[0] === f[1][0] && f[1].length >= fence.marker.length) {
        fence = null;
      } else failures.push(name + ":" + (i + 1) + " mismatched fenced delimiter");
      continue;
    }
    if (fence) {
      if (unsafeLine.test(line)) failures.push(name + ":" + (i + 1) + " potentially destructive executable command");
      continue;
    }

    const n = line.match(/^## (\d+)\./);
    if (n) numbered.push(Number(n[1]));
    if (/^## References/.test(line)) referenceCount++;

    if (/^\s*\|/.test(line)) {
      if (!line.trim().endsWith("|")) failures.push(name + ":" + (i + 1) + " table row has no trailing pipe");
      const colCount = line.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/).length;
      if (!inTable) {
        expectedColumns = colCount;
        inTable = true;
      } else if (colCount !== expectedColumns) {
        failures.push(name + ":" + (i + 1) + " inconsistent Markdown table columns " + colCount + "/" + expectedColumns);
      }
    } else {
      inTable = false;
      expectedColumns = null;
    }

    for (const m of line.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/g)) {
      const target = m[1].trim().split("#")[0];
      if (!target || /^mailto:/i.test(target)) continue;
      if (/^https?:\/\//i.test(target)) {
        externalLinks++;
        continue; // Deliberately not checked over the network.
      }
      internalLinks++;
      const resolved = path.resolve(path.dirname(full), decodeURIComponent(target));
      if (!resolved.startsWith(root + path.sep) || !fs.existsSync(resolved)) {
        failures.push(name + ":" + (i + 1) + " unresolved local link " + target);
      }
    }
  }
  if (fence) failures.push(name + ": unclosed fence beginning at line " + fence.start);
  for (let i = 0; i < numbered.length; i++) {
    if (numbered[i] !== i + 1) failures.push(name + ": numbered sections not sequential at " + numbered[i]);
  }
  if (guideNames.includes(name)) {
    const number = name.slice(0, 2);
    const expectedId = "PG-DBRE-OPS-0" + number;
    if (!body.includes(expectedId)) failures.push(name + ": missing/mismatched document ID " + expectedId);
    if (!/\bDRAFT\b/i.test(body)) failures.push(name + ": missing draft indicator");
    if (referenceCount !== 1) failures.push(name + ": expected one References section");
    if (!/acceptance/i.test(body)) failures.push(name + ": missing acceptance criteria");
  }
  stats.push({ name, lines: lines.length, codeBlocks, internalLinks, externalLinks });
}

const parentReadme = path.join(root, "postgresql", "README.md");
if (!fs.existsSync(parentReadme)) failures.push("Missing PostgreSQL tutorial README");
else if (!fs.readFileSync(parentReadme, "utf8").includes("dbre-responsibility-for-postgresql/README.md")) {
  failures.push("PostgreSQL curriculum README lacks DBRE track navigation");
}

for (const stat of stats) {
  process.stdout.write(
    stat.name + ": " + stat.lines + " lines, " + stat.codeBlocks
    + " code blocks, " + stat.internalLinks + " local and "
    + stat.externalLinks + " external links\n"
  );
}
const sum = key => stats.reduce((total, s) => total + s[key], 0);
process.stdout.write(
  "\nTOTAL: " + stats.length + " files, " + sum("lines") + " lines, "
  + sum("codeBlocks") + " code blocks, " + sum("internalLinks")
  + " local links, " + sum("externalLinks") + " external links (not network-checked)\n"
);
if (failures.length) {
  process.stderr.write("\nV01 FAIL:\n" + failures.map(f => "- " + f).join("\n") + "\n");
  process.exitCode = 1;
} else {
  process.stdout.write("V01 PASS (static structure and local-link validation only).\n");
}
