#!/usr/bin/env node
// Validates a vc-generate-closeout OUTPUT artifact (markdown).
// FAIL unless all 8 closeout items are present; if no verbatim drift-threshold
// phrase is present; or if the archive-readiness classification is not exactly one
// of the 3 allowed states (zero or >=2 present -> FAIL).
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
  fail("Usage: node validate-closeout-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. All 8 closeout items present (label keywords, per vc-generate-closeout/SKILL.md Packet Schema).
  const items = [
    { label: "1 Selected plan path", re: /selected plan path/i },
    { label: "2 Closeout classification", re: /closeout classification/i },
    { label: "3 What was finished", re: /what was finished/i },
    { label: "4 What was verified vs still unverified", re: /verified.{0,12}unverified/i },
    { label: "5 Cleanup done vs still needed", re: /cleanup done.{0,12}still needed/i },
    { label: "6 Single best next valid state", re: /single best next valid state/i },
    { label: "7 Commit-checkpoint recommendation", re: /commit[- ]checkpoint recommendation/i },
    { label: "8 Regression status", re: /regression status/i },
  ];
  for (const it of items) {
    if (!it.re.test(text)) {
      fail(`${target} missing closeout item: ${it.label}`);
    }
  }

  // 2. Verbatim drift-threshold phrase (one of the three literals from SKILL.md).
  const driftPhrases = [
    "UPDATE PROCESS available if you want.",
    "Recommend UPDATE PROCESS -- significant changes detected.",
    "Strongly recommend UPDATE PROCESS -- harness/protocol files touched.",
  ];
  if (!driftPhrases.some((p) => text.includes(p))) {
    fail(`${target} missing verbatim drift-threshold phrase (LOW/MEDIUM/HIGH literal)`);
  }

  // 3. Exactly one of the 3 archive-readiness classification states.
  const states = [
    "Ready for UPDATE PROCESS archival",
    "Keep in active/testing",
    "Needs PLAN/UPDATE PROCESS reconciliation",
  ];
  const present = states.filter((s) => text.includes(s));
  if (present.length !== 1) {
    fail(
      `${target} must contain exactly one classification state; found ${present.length} (${present.join(", ") || "none"})`,
    );
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
