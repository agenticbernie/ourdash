#!/usr/bin/env node
// Validates that every completed phase in an umbrella plan has its report file on disk.
// Arg = umbrella/program plan path. Parse `## Program Status Table` (or
// `## Phase Ordering`) for phases marked complete/VERIFIED. For each, resolve its
// report path from `## Durable Report Destinations` and FAIL unless the file exists.
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

function exists(absOrRel) {
  return fs.existsSync(path.isAbsolute(absOrRel) ? absOrRel : path.resolve(root, absOrRel));
}

function read(relPath) {
  return fs.readFileSync(path.resolve(root, relPath), "utf8");
}

function sectionBody(text, headingRe) {
  const lines = text.split("\n");
  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (headingRe.test(lines[i])) {
      start = i;
      break;
    }
  }
  if (start === -1) return null;
  const body = [];
  for (let i = start + 1; i < lines.length; i++) {
    if (/^##\s+/.test(lines[i])) break;
    body.push(lines[i]);
  }
  return body.join("\n");
}

const target = process.argv.slice(2).find((a) => !a.startsWith("--"));

if (!target) {
  fail("Usage: node validate-phase-reports.mjs <umbrella-plan-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);
  const umbrellaDir = path.dirname(path.resolve(root, target));

  // 1. Find completed phases from the status table (or phase ordering).
  const statusBody =
    sectionBody(text, /^##\s+Program Status Table/i) ||
    sectionBody(text, /^##\s+Phase Ordering/i);
  if (statusBody === null) {
    fail(`${target} missing '## Program Status Table' / '## Phase Ordering' section`);
  }

  // 2. Parse the Durable Report Destinations table: phase -> report path.
  const destBody = sectionBody(text, /^##\s+Durable Report Destinations/i);
  if (destBody === null) {
    fail(`${target} missing '## Durable Report Destinations' section`);
  }

  if (statusBody !== null && destBody !== null) {
    const completePhases = [];
    for (const row of statusBody.split("\n")) {
      if (!/^\s*\|/.test(row)) continue;
      if (/phase/i.test(row) && /status/i.test(row)) continue; // header
      const m = row.match(/phase\s*(\d+)/i);
      if (!m) continue;
      if (/✅|verified|\bcomplete\b|\bdone\b/i.test(row)) completePhases.push(m[1]);
    }

    // Build phase -> report path map from destinations table.
    const destMap = new Map();
    for (const row of destBody.split("\n")) {
      if (!/^\s*\|/.test(row)) continue;
      const m = row.match(/phase\s*(\d+)/i);
      if (!m) continue;
      const pathMatch = row.match(/([^\s|]+\.md)/);
      if (pathMatch) destMap.set(m[1], pathMatch[1].trim());
    }

    for (const p of completePhases) {
      const reportPath = destMap.get(p);
      if (!reportPath) {
        fail(`${target} Phase ${p} marked complete but has no Durable Report Destination entry`);
        continue;
      }
      // Report path may be repo-relative or relative to the umbrella folder.
      const repoRel = exists(reportPath);
      const umbrellaRel = fs.existsSync(path.resolve(umbrellaDir, reportPath));
      if (!repoRel && !umbrellaRel) {
        fail(`${target} Phase ${p} report file missing on disk: ${reportPath}`);
      }
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
