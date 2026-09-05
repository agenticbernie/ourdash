#!/usr/bin/env node
// Validates a vc-validate-findings OUTPUT artifact (markdown).
// FAIL unless BOTH layers are evidenced (Layer 1 / Layer 2 labels). FAIL if the
// net-gate derivation is wrong: if any per-layer verdict is FAIL/BLOCKED, the net
// gate MUST be BLOCKED. FAIL if the net gate string is not an allowed value.
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
  fail("Usage: node validate-findings-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. Both layers evidenced.
  if (!/Layer 1/i.test(text)) {
    fail(`${target} missing Layer 1 evidence`);
  }
  if (!/Layer 2/i.test(text)) {
    fail(`${target} missing Layer 2 evidence`);
  }

  // 2. Net gate must be exactly one allowed value.
  const allowedNetGates = ["PASS", "CONDITIONAL", "BLOCKED"];
  const netMatch = text.match(/net gate\s*[:=]?\s*\*{0,2}\s*(PASS|CONDITIONAL|BLOCKED)\b/i);
  if (!netMatch) {
    fail(`${target} net gate string is missing or not one of ${allowedNetGates.join("/")}`);
  } else {
    const netGate = netMatch[1].toUpperCase();

    // 3. Per-layer verdict tokens: any FAIL or BLOCKED layer verdict forces net BLOCKED.
    // Parse status cells from the Layer tables (Status: X or | ... | X | rows).
    const verdictTokens = (text.match(/\b(PASS|CONCERN|FAIL|BLOCKED)\b/gi) || []).map((t) =>
      t.toUpperCase(),
    );
    const hasFailingLayer = verdictTokens.some((t) => t === "FAIL" || t === "BLOCKED");
    if (hasFailingLayer && netGate !== "BLOCKED") {
      fail(
        `${target} net-gate derivation wrong: a FAIL/BLOCKED layer verdict is present but net gate is ${netGate} (must be BLOCKED)`,
      );
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
