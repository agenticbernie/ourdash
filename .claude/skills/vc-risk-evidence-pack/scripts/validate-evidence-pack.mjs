#!/usr/bin/env node
// Validates a vc-risk-evidence-pack evidence-pack DIRECTORY.
// Positional arg is the evidence-pack root dir. FAIL unless all 5 named artifact
// files exist inside <dir>/harness/. FAIL unless <dir>/harness/review-decision.json
// parses as JSON and its decision field equals exactly APPROVE or REJECT.
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

const target = process.argv.slice(2).find((a) => !a.startsWith("--"));

if (!target) {
  fail("Usage: node validate-evidence-pack.mjs <evidence-pack-dir>");
} else {
  const harnessDir = path.resolve(root, target, "harness");
  if (!fs.existsSync(harnessDir) || !fs.statSync(harnessDir).isDirectory()) {
    fail(`${target}/harness/ does not exist or is not a directory`);
  } else {
    const requiredFiles = [
      "risk-gate.json",
      "context-snippets.json",
      "verification.json",
      "review-decision.json",
      "adversarial-validation.json",
    ];
    for (const f of requiredFiles) {
      if (!fs.existsSync(path.join(harnessDir, f))) {
        fail(`${target}/harness/ missing required artifact: ${f}`);
      }
    }

    // review-decision.json must parse and have decision === APPROVE | REJECT.
    const reviewPath = path.join(harnessDir, "review-decision.json");
    if (fs.existsSync(reviewPath)) {
      let parsed;
      try {
        parsed = JSON.parse(fs.readFileSync(reviewPath, "utf8"));
      } catch (err) {
        fail(`${target}/harness/review-decision.json is not valid JSON: ${err.message}`);
      }
      if (parsed && parsed.decision !== "APPROVE" && parsed.decision !== "REJECT") {
        fail(
          `${target}/harness/review-decision.json decision must be exactly APPROVE or REJECT (got ${JSON.stringify(parsed.decision)})`,
        );
      }
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
