#!/usr/bin/env node
// Validates a vc-intent-clarify OUTPUT artifact (markdown).
// FAIL if a restatement line is absent (unconditional, even for /goal). FAIL if no
// ambiguity score (0-7) is present. FAIL unless a mode is chosen as exactly one of
// simple/deep AND a reason/because justification follows it.
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
  fail("Usage: node validate-intent-clarify-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. Restatement present (unconditional — a /goal output must still emit it).
  if (!/restate(ment|d|s)?\b/i.test(text)) {
    fail(`${target} missing restatement line (required even under /goal)`);
  }

  // 2. Ambiguity score 0-7.
  if (!/score\D{0,8}[0-7]\b/i.test(text)) {
    fail(`${target} missing ambiguity score (integer 0-7)`);
  }

  // 3. Mode chosen as exactly one of simple/deep, with a reason/because justification.
  const hasSimple = /\bsimple\b/i.test(text);
  const hasDeep = /\bdeep\b/i.test(text);
  if (!hasSimple && !hasDeep) {
    fail(`${target} no mode chosen (expected one of simple/deep)`);
  } else if (hasSimple && hasDeep) {
    fail(`${target} ambiguous mode: both simple and deep present (choose exactly one)`);
  } else {
    if (!/\b(reason|because)\b/i.test(text)) {
      fail(`${target} mode chosen but no reason/because justification follows it`);
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
