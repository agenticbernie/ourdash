#!/usr/bin/env node
// Validates a vc-agent-strategy-compare OUTPUT artifact (markdown).
// FAIL unless all 4 strategy names appear; if the 7-signal table has any empty
// signal/score cell or fewer than 7 data rows; or if either cost guard (>30, >100)
// is absent.
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

const target = process.argv.slice(2).find((a) => !a.startsWith("--"));

if (!target) {
  fail("Usage: node validate-strategy-compare-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. All 4 strategy names (with accepted aliases).
  const strategies = [
    { label: "sequential", re: /\bsequential\b/i },
    { label: "parallel-subagents", re: /parallel[- ]subagents|\bparallel\b/i },
    { label: "workflow", re: /\bworkflow\b/i },
    { label: "agent-team", re: /agent[- ]team|vc-team/i },
  ];
  for (const s of strategies) {
    if (!s.re.test(text)) {
      fail(`${target} missing strategy: ${s.label}`);
    }
  }

  // 2. 7-signal table: require >= 7 data rows, none with an empty score column.
  // Parse markdown table rows (lines starting with `|`, excluding separator rows).
  const tableRows = text
    .split("\n")
    .filter((l) => /^\s*\|/.test(l))
    .filter((l) => !/^\s*\|[\s|:-]+\|?\s*$/.test(l)); // drop separator rows
  // Drop a header row if present (heuristic: first row containing "signal").
  const dataRows = [];
  let sawHeader = false;
  for (const row of tableRows) {
    if (!sawHeader && /signal/i.test(row)) {
      sawHeader = true;
      continue;
    }
    dataRows.push(row);
  }
  if (dataRows.length < 7) {
    fail(`${target} 7-signal table has ${dataRows.length} data rows; require >= 7`);
  } else {
    for (const row of dataRows.slice(0, 7)) {
      const cells = row.split("|").map((c) => c.trim()).filter((c, i, arr) => i !== 0 && i !== arr.length - 1);
      // require at least 2 columns and no empty cell among them
      if (cells.length < 2 || cells.some((c) => c.length === 0)) {
        fail(`${target} 7-signal table has an empty cell in row: ${row.trim()}`);
      }
    }
  }

  // 3. Both cost guards present.
  if (!/>\s*30\b/.test(text)) {
    fail(`${target} missing '> 30' agent-count cost guard`);
  }
  if (!/>\s*100\b/.test(text)) {
    fail(`${target} missing '> 100' cost guard`);
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
