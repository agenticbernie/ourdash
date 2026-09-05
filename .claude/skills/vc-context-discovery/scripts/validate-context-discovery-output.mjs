#!/usr/bin/env node
// Validates a vc-context-discovery OUTPUT artifact (markdown).
// FAIL if <8 numbered workflow steps; if routing-table reference does not precede
// the first deeper-file reference; or if the Context Envelope block is absent or
// does not contain all 10 C-2 fields in canonical order.
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
  fail("Usage: node validate-context-discovery-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. At least 8 numbered workflow steps.
  const numberedSteps = (text.match(/^\s*\d+\./gm) || []).length;
  if (numberedSteps < 8) {
    fail(`${target} has ${numberedSteps} numbered workflow steps; require >= 8`);
  }

  // 2. Routing-table reference must precede the first deeper-file reference.
  const routingIdx = text.search(/all-context\.md|routing table/i);
  // A deeper file is any process/context/<group>/ file other than all-context.md.
  const deeperMatch = text.match(/process\/context\/[a-z-]+\/(?!all-context\.md)[a-z0-9-]+\.md/i);
  const deeperIdx = deeperMatch ? text.indexOf(deeperMatch[0]) : -1;
  if (routingIdx === -1) {
    fail(`${target} missing routing-table reference (all-context.md / routing table)`);
  } else if (deeperIdx !== -1 && routingIdx > deeperIdx) {
    fail(
      `${target} routing-table reference (idx ${routingIdx}) does not precede first deeper-file reference (idx ${deeperIdx})`,
    );
  }

  // 3. Context Envelope: all 10 C-2 fields present AND in canonical order.
  const c2Fields = [
    "feature",
    "phase",
    "session-goal",
    "branch",
    "worktree",
    "context-group",
    "blast-radius-packages",
    "active-plan",
    "test-runner",
    "validate-contract",
  ];
  let lastIdx = -1;
  let orderBroken = false;
  for (const field of c2Fields) {
    const idx = text.indexOf(field);
    if (idx === -1) {
      fail(`${target} Context Envelope missing C-2 field: ${field}`);
      orderBroken = true;
    } else if (idx <= lastIdx) {
      fail(`${target} Context Envelope field out of canonical order: ${field}`);
      orderBroken = true;
    } else {
      lastIdx = idx;
    }
  }
  if (orderBroken && !c2Fields.some((f) => text.includes(f))) {
    fail(`${target} Context Envelope block appears absent`);
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
