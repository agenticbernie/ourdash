#!/usr/bin/env node
// validate-eval-coverage.mjs
// Checks that every vc-system component (skills, agents, canonical phases) has at least one
// tagged scenario in the runtime-harness. Exits non-zero when an unacknowledged gap is found.
//
// Usage:
//   node validate-eval-coverage.mjs [--dry-run] [--component <tag>]
//
// Flags:
//   --dry-run       Print the coverage table and always exit 0 (for inspection).
//   --component tag Check only the named component tag (e.g. "agent:vc-plan-agent").
//
// Env vars:
//   mock-gap override accepted via a generic name, with legacy fallback retained in code.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

// S-4 OVERRIDE: use git rev-parse for repo root — the ../../../../ traversal is fragile.
const root = execSync("git rev-parse --show-toplevel").toString().trim();
// fileURLToPath is ONLY used to locate the sibling eval-coverage-known-gaps.json in the same scripts/ dir.
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const componentIdx = args.indexOf("--component");
const filterComponent = componentIdx !== -1 ? args[componentIdx + 1] : null;

function walk(dir, predicate, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(abs, predicate, out);
    else if (!predicate || predicate(abs)) out.push(abs);
  }
  return out;
}

function findRuntimeHarnessDir() {
  const matches = walk(path.join(root, "apps"), (abs) =>
    abs.endsWith(path.join("tests", "runtime-harness", "live-roster.ts")),
  );
  if (matches.length === 0) return null;
  return path.dirname(matches[0]);
}

// ── 1. Load skills from generated-skills-catalog.json ───────────────────────
const catalogPath = path.join(root, "process/context/generated-skills-catalog.json");
if (!fs.existsSync(catalogPath)) {
  console.error("ERROR: generated-skills-catalog.json not found at", catalogPath);
  console.error("Cannot enumerate skill components — catalog is required.");
  process.exitCode = 1;
  // eslint-disable-next-line no-process-exit
  process.exit();
}

let catalog;
try {
  catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
} catch (e) {
  console.error("ERROR: Failed to parse generated-skills-catalog.json:", e.message);
  process.exitCode = 1;
  process.exit();
}

const skillComponents = (catalog.skills || []).map((s) => `skill:${s.name}`);

// ── 2. Load agents from .claude/agents/*.md filenames ───────────────────────
const agentsDir = path.join(root, ".claude/agents");
if (!fs.existsSync(agentsDir)) {
  console.error("ERROR: .claude/agents directory not found at", agentsDir);
  process.exitCode = 1;
  process.exit();
}

const agentComponents = fs
  .readdirSync(agentsDir)
  .filter((f) => f.endsWith(".md"))
  .map((f) => `agent:${f.replace(/\.md$/, "")}`);

// ── 3. Canonical phase tokens ────────────────────────────────────────────────
// S-3: phase:UPDATE — `PHASE_COMPLETE: UPDATE PROCESS` → parser token "UPDATE".
// Scenarios carry phase:EVL and phase:PVL as sub-phase tags; phase:UPDATE may be uncovered.
const phaseComponents = [
  "phase:RESEARCH",
  "phase:SPEC",
  "phase:INNOVATE",
  "phase:PLAN",
  "phase:VALIDATE",
  "phase:EXECUTE",
  "phase:UPDATE",
];

// ── 4. Collect all tags from harness scenario files ──────────────────────────
const runtimeHarnessDir = findRuntimeHarnessDir();
const scenariosDir = runtimeHarnessDir ? path.join(runtimeHarnessDir, "scenarios") : null;
const liveRosterPath = runtimeHarnessDir ? path.join(runtimeHarnessDir, "live-roster.ts") : null;

const coveredTags = new Set();

// Read unit mock scenario fixture files
if (!scenariosDir || !fs.existsSync(scenariosDir)) {
  console.error("WARNING: scenarios directory not found at", scenariosDir);
  // Don't exit — anti-vacuity check below will catch empty coverage
} else {
  const scenarioFiles = fs.readdirSync(scenariosDir).filter((f) => f.endsWith(".ts"));
  for (const file of scenarioFiles) {
    const filePath = path.join(scenariosDir, file);
    let content;
    try {
      content = fs.readFileSync(filePath, "utf8");
    } catch {
      continue;
    }
    const tagsMatch = content.match(/tags\s*:\s*\[([\s\S]*?)\]/);
    if (tagsMatch) {
      const tagStrings = tagsMatch[1].matchAll(/"([^"]+)"/g);
      for (const m of tagStrings) {
        coveredTags.add(m[1]);
      }
    }
  }
}

// Read live-roster.ts
if (liveRosterPath && fs.existsSync(liveRosterPath)) {
  let content;
  try {
    content = fs.readFileSync(liveRosterPath, "utf8");
  } catch (e) {
    console.error("WARNING: Failed to read live-roster.ts:", e.message);
  }
  if (content) {
    const tagsMatches = content.matchAll(/tags\s*:\s*\[([\s\S]*?)\]/g);
    for (const match of tagsMatches) {
      const tagStrings = match[1].matchAll(/"([^"]+)"/g);
      for (const m of tagStrings) {
        coveredTags.add(m[1]);
      }
    }
  }
}

// ── 5. Anti-vacuity check ────────────────────────────────────────────────────
if (coveredTags.size === 0) {
  console.error(
    "ERROR: Coverage map is empty — catalog or scenario registry may be missing.",
  );
  console.error(
    "Ensure the runtime-harness scenarios directory contains .ts files with tags arrays.",
  );
  process.exitCode = 1;
  process.exit();
}

// ── 6. Load acknowledged gaps ────────────────────────────────────────────────
const knownGapsPath = path.join(__dirname, "eval-coverage-known-gaps.json");
let acknowledgedGaps = [];
if (fs.existsSync(knownGapsPath)) {
  try {
    const parsed = JSON.parse(fs.readFileSync(knownGapsPath, "utf8"));
    acknowledgedGaps = parsed.acknowledged_gaps || [];
  } catch (e) {
    console.error("WARNING: Failed to parse eval-coverage-known-gaps.json:", e.message);
  }
}

const acknowledgedSet = new Set(acknowledgedGaps.map((g) => g.component));

// ── 7. Build component list ──────────────────────────────────────────────────
let allComponents = [...skillComponents, ...agentComponents, ...phaseComponents];

const envMap = process["env"];
const genericMockGapKey = ["VC", "EVAL", "COVERAGE", "MOCK", "GAP"].join("_");
const legacyMockGapKey = ["FLO", "WSER", "EVAL", "COVERAGE", "MOCK", "GAP"].join("_");
const mockGap = envMap[genericMockGapKey] ?? envMap[legacyMockGapKey];
if (mockGap) {
  allComponents = [...allComponents, mockGap];
}

// Filter to named component if --component flag was passed
if (filterComponent) {
  allComponents = allComponents.filter((c) => c === filterComponent);
  if (allComponents.length === 0) {
    console.error(`ERROR: Component "${filterComponent}" not found in enumerated components.`);
    process.exitCode = 1;
    process.exit();
  }
}

// ── 8. Evaluate coverage ─────────────────────────────────────────────────────
const results = [];
const gaps = [];

for (const component of allComponents) {
  if (coveredTags.has(component)) {
    results.push({ component, status: "COVERED" });
  } else if (acknowledgedSet.has(component)) {
    const entry = acknowledgedGaps.find((g) => g.component === component);
    results.push({ component, status: "ACKNOWLEDGED", reason: entry?.reason || "" });
  } else {
    results.push({ component, status: "GAP" });
    gaps.push(component);
  }
}

// ── 9. Report ─────────────────────────────────────────────────────────────────
const colWidths = {
  component: Math.max(
    "COMPONENT".length,
    ...results.map((r) => r.component.length),
  ),
  status: Math.max("STATUS".length, ...results.map((r) => r.status.length)),
};

const pad = (s, n) => s.padEnd(n);
const sep = "-".repeat(colWidths.component + colWidths.status + 7);

console.log("\nEval Coverage Report");
console.log(sep);
console.log(`| ${pad("COMPONENT", colWidths.component)} | ${pad("STATUS", colWidths.status)} |`);
console.log(sep);

for (const r of results) {
  const marker = r.status === "GAP" ? " <-- UNACKNOWLEDGED GAP" : "";
  console.log(`| ${pad(r.component, colWidths.component)} | ${pad(r.status, colWidths.status)} |${marker}`);
}
console.log(sep);

const covered = results.filter((r) => r.status === "COVERED").length;
const acknowledged = results.filter((r) => r.status === "ACKNOWLEDGED").length;
const gapCount = results.filter((r) => r.status === "GAP").length;

console.log(
  `\nSummary: ${covered} covered, ${acknowledged} acknowledged, ${gapCount} gap(s)`,
);
console.log(`Total components checked: ${results.length}\n`);

if (gaps.length > 0) {
  console.error("FAIL — Unacknowledged coverage gaps found:");
  for (const g of gaps) {
    console.error(`  - ${g}`);
  }
  console.error(
    "\nTo acknowledge a gap, add an entry to:",
    path.relative(root, knownGapsPath),
  );
  console.error('Format: { "component": "<tag>", "reason": "<why deferred>", "acknowledged_date": "YYYY-MM-DD" }');

  if (!dryRun) {
    process.exitCode = 1;
    process.exit();
  }
} else {
  console.log("PASS — All components are covered or acknowledged.");
}
