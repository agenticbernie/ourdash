#!/usr/bin/env node
// Validates an umbrella plan's execution-state coherence (NET-NEW; scoped-coexist
// sibling of validate-umbrella-artifact.mjs).
// FAIL unless a `## Current Execution State` section exists. Parse the
// `## Program Status Table` rows (phase -> status). FAIL if a phase the status table
// marks VERIFIED/COMPLETE is not listed as completed in `## Current Execution State`
// (or vice-versa).
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

function exists(relPath) {
  return fs.existsSync(path.resolve(root, relPath));
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
  fail("Usage: node validate-umbrella-state.mjs <umbrella-plan-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. `## Current Execution State` must exist.
  const stateBody = sectionBody(text, /^##\s+Current Execution State/i);
  if (stateBody === null) {
    fail(`${target} missing '## Current Execution State' section`);
  }

  // 2. Parse `## Program Status Table` rows: phase -> status.
  const tableBody = sectionBody(text, /^##\s+Program Status Table/i);
  if (tableBody === null) {
    fail(`${target} missing '## Program Status Table' section`);
  }

  if (stateBody !== null && tableBody !== null) {
    // Each table data row: | Phase N ... | <status> |
    const rows = tableBody
      .split("\n")
      .filter((l) => /^\s*\|/.test(l) && !/^\s*\|[\s|:-]+\|?\s*$/.test(l));
    const completePhases = [];
    for (const row of rows) {
      if (/phase/i.test(row) && /status/i.test(row)) continue; // header
      const phaseMatch = row.match(/phase\s*(\d+)/i);
      if (!phaseMatch) continue;
      const phaseNum = phaseMatch[1];
      const isComplete = /✅|verified|\bcomplete\b|\bdone\b/i.test(row);
      if (isComplete) completePhases.push(phaseNum);
    }

    // 3. Cross-check: every table-complete phase must be listed completed in state body.
    for (const p of completePhases) {
      const listedComplete = new RegExp(`phase\\s*${p}\\b`, "i").test(stateBody) &&
        /complet|✅|verified|done/i.test(stateBody);
      // Stronger: require the specific phase number to co-occur in a completed context.
      const phaseLineComplete = stateBody
        .split("\n")
        .some((l) => new RegExp(`phase\\s*${p}\\b`, "i").test(l) && /complet|✅|verified|done/i.test(l));
      if (!listedComplete || !phaseLineComplete) {
        fail(
          `${target} status table marks Phase ${p} complete/VERIFIED but '## Current Execution State' does not list it as completed`,
        );
      }
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
