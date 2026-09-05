#!/usr/bin/env node
// post-write-plan-check.mjs — PostToolUse(Write) hook (single-file artifact validators).
//
// When a Write targets a known plan-artifact file under process/**, run the matching
// structure validator on the written path and surface the result. The first matching rule
// in ROUTES wins, so the more specific umbrella/phase-stub rules must precede the generic
// plan rule (umbrella and phase-stub files also contain `_PLAN_`). Non-artifact writes are
// a clean no-op. Fail-open: advisory only, never blocks the write (always exits 0).
//
// Wired validators (Bucket A — one file each):
//   *umbrella_PLAN_*.md     -> vc-generate-phase-program/scripts/validate-umbrella-artifact.mjs
//   phase-*_PLAN_*.md       -> vc-generate-phase-program/scripts/validate-phase-stub.mjs
//   process/**/*_PLAN_*.md  -> vc-generate-plan/scripts/validate-plan-artifact.mjs
// Whole-tree scan validators (context/plans/harness groups) run from the Stop hook
// (stop-validator-sweep.mjs), not here.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const HOOK_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HOOK_DIR, "..", "..");

// Ordered: first match wins. Specific (umbrella, phase-stub) before generic plan.
const ROUTES = [
  {
    label: "umbrella-artifact",
    re: /(^|\/)[^/]*umbrella_PLAN_[^/]*\.md$/,
    validator: ".claude/skills/vc-generate-phase-program/scripts/validate-umbrella-artifact.mjs",
  },
  {
    label: "phase-stub",
    re: /(^|\/)phase-\d[^/]*_PLAN_[^/]*\.md$/,
    validator: ".claude/skills/vc-generate-phase-program/scripts/validate-phase-stub.mjs",
  },
  {
    label: "plan-artifact",
    re: /(^|\/)process\/.*_PLAN_.*\.md$/,
    validator: ".claude/skills/vc-generate-plan/scripts/validate-plan-artifact.mjs",
  },
];

function readPayload() {
  try {
    const raw = fs.readFileSync(0, "utf8").trim();
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function extractWrittenPath(payload) {
  const input = payload.tool_input || payload.toolInput || {};
  return input.file_path || input.filePath || input.path || "";
}

function main() {
  const payload = readPayload();
  const writtenPath = extractWrittenPath(payload);
  if (!writtenPath) process.exit(0);

  const route = ROUTES.find((r) => r.re.test(writtenPath));
  if (!route) process.exit(0); // Not a known artifact write — no-op.

  const validatorAbs = path.join(REPO_ROOT, route.validator);
  if (!fs.existsSync(validatorAbs)) {
    console.log(`post-write-plan-check: validator not found at ${route.validator} — skipping.`);
    process.exit(0);
  }

  const relPath = path.isAbsolute(writtenPath)
    ? path.relative(REPO_ROOT, writtenPath)
    : writtenPath;

  const result = spawnSync("node", [validatorAbs, relPath], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });

  const out = (result.stdout || "").trim();
  const err = (result.stderr || "").trim();
  if (out) console.log(`post-write-plan-check: ${route.label} validation for ${relPath}:\n${out}`);
  if (err) console.log(`post-write-plan-check: ${err}`);

  // Fail-open: never block the write; advisory only.
  process.exit(0);
}

try {
  main();
} catch (error) {
  console.log(`post-write-plan-check: hook error (ignored): ${error && error.message}`);
  process.exit(0);
}
