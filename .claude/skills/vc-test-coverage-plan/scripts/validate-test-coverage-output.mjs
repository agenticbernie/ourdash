#!/usr/bin/env node
// Validates a vc-test-coverage-plan OUTPUT artifact (markdown).
// FAIL unless every blast-radius area name appears in a tier-assignment table row.
// FAIL unless the all-tests.md routing chain is referenced. FAIL unless each
// enumerated gap has resolution letters A/B/C/D adjacent.
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
  fail("Usage: node validate-test-coverage-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);
  const lines = text.split("\n");

  // 1. all-tests.md routing chain referenced.
  if (!/all-tests\.md/.test(text)) {
    fail(`${target} does not reference the all-tests.md routing chain`);
  }

  // 2. Blast-radius areas: parse the area list, then assert each appears in a tier row.
  // Areas are listed after a "Blast Radius" heading as bullet/`code` items; tier rows
  // are table rows whose first cell contains one of the 4 tier words.
  const tierWord = /(fully-automated|hybrid|agent-probe|known-gap)/i;
  const tierRows = lines.filter((l) => /^\s*\|/.test(l) && tierWord.test(l));

  // Collect area names: lines under a "Blast Radius Areas" section formatted as
  // `- area: ...` or `- \`area\``.
  const areas = [];
  let inAreaSection = false;
  for (const line of lines) {
    if (/^#{1,6}\s+.*blast.?radius.*area/i.test(line)) {
      inAreaSection = true;
      continue;
    }
    if (inAreaSection && /^#{1,6}\s+/.test(line)) {
      inAreaSection = false;
    }
    if (inAreaSection) {
      const m = line.match(/^\s*[-*]\s+`?([^`:|]+?)`?\s*(?:[:—-]|$)/);
      if (m) areas.push(m[1].trim());
    }
  }

  if (areas.length === 0) {
    fail(`${target} has no blast-radius area list (expected a 'Blast Radius Areas' section)`);
  }
  const tierRowsBlob = tierRows.join("\n");
  for (const area of areas) {
    if (!tierRowsBlob.includes(area)) {
      fail(`${target} blast-radius area '${area}' has no tier-assignment table row`);
    }
  }

  // 3. Each enumerated gap has A/B/C/D resolution letters adjacent.
  // A "gap row" is a table row in the Gap Resolution table (contains a Gap description
  // and the four-option cell). We scan rows that come after a "Gap" + "Resolution"
  // header and require A) B) C) D) tokens in the row.
  let inGapTable = false;
  for (const line of lines) {
    if (/\|\s*gap\s*\|\s*resolution/i.test(line)) {
      inGapTable = true;
      continue;
    }
    if (inGapTable) {
      if (!/^\s*\|/.test(line)) {
        inGapTable = false;
        continue;
      }
      if (/^\s*\|[\s|:-]+\|?\s*$/.test(line)) continue; // separator row
      const hasAll = /\bA\)/.test(line) && /\bB\)/.test(line) && /\bC\)/.test(line) && /\bD\)/.test(line);
      if (!hasAll) {
        fail(`${target} gap row missing one of A/B/C/D resolution letters: ${line.trim()}`);
      }
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
