#!/usr/bin/env node
// Validates a vc-autoresearch iteration LOG (.tsv).
// FAIL if not tab-delimited with a header row. FAIL if the iteration counter (col 1)
// is not strictly monotonic increasing. FAIL unless a plateau/regression signal is
// recorded (saturation_status / loop_status column present). FAIL if any iteration
// index exceeds the 10-cycle cap. FAIL unless the domain field is exactly plan|tests.
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
  fail("Usage: node validate-autoresearch-log.mjs <log.tsv>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);
  const rawLines = text.split("\n").filter((l) => l.trim().length > 0);

  // The log may carry a leading `# domain: tests` metadata/legend comment line.
  const commentLines = rawLines.filter((l) => l.trimStart().startsWith("#"));
  const dataLines = rawLines.filter((l) => !l.trimStart().startsWith("#"));

  if (dataLines.length < 2) {
    fail(`${target} must have a header row plus at least one data row`);
  } else {
    const header = dataLines[0];
    // 1. Tab-delimited header.
    if (!header.includes("\t")) {
      fail(`${target} header row is not tab-delimited`);
    }
    const headerCols = header.split("\t").map((c) => c.trim());

    // 3. Plateau/regression signal column present.
    const hasSignalCol = headerCols.some((c) => /saturation_status|loop_status|plateau|regression/i.test(c));
    if (!hasSignalCol) {
      fail(`${target} missing a plateau/regression signal column (saturation_status / loop_status)`);
    }

    // 2 + 4. Iteration counter (col 1) strictly monotonic AND max <= 10.
    let prev = null;
    for (const line of dataLines.slice(1)) {
      const cols = line.split("\t");
      const iter = parseInt(cols[0], 10);
      if (Number.isNaN(iter)) {
        fail(`${target} non-integer iteration counter in row: ${line}`);
        continue;
      }
      if (prev !== null && iter <= prev) {
        fail(`${target} iteration counter not strictly increasing (${prev} -> ${iter})`);
      }
      if (iter > 10) {
        fail(`${target} iteration index ${iter} exceeds 10-cycle cap`);
      }
      prev = iter;
    }

    // 5. domain field exactly plan|tests. Look in comment legend OR a `domain` column value.
    const domainColIdx = headerCols.findIndex((c) => /^domain$/i.test(c));
    let domainValue = null;
    if (domainColIdx !== -1) {
      const firstData = dataLines[1].split("\t");
      domainValue = (firstData[domainColIdx] || "").trim();
    } else {
      const domComment = commentLines.find((l) => /domain\s*[:=]/i.test(l));
      if (domComment) {
        const m = domComment.match(/domain\s*[:=]\s*([a-z]+)/i);
        domainValue = m ? m[1].trim() : null;
      }
    }
    if (domainValue !== "plan" && domainValue !== "tests") {
      fail(`${target} domain field must be exactly 'plan' or 'tests' (got ${JSON.stringify(domainValue)})`);
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
