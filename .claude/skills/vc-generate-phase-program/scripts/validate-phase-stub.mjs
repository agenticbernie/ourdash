#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const root = (() => {
  try {
    return execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
  } catch {
    return process.cwd();
  }
})();

const args = process.argv.slice(2);
const strict = args.includes("--strict");
const inputPaths = args.filter((arg) => !arg.startsWith("--"));
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

function warn(message) {
  if (strict) failures.push(message);
  else warnings.push(message);
}

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), "utf8");
}

function hasSection(text, name) {
  return new RegExp(`^##\\s+${name}\\b`, "im").test(text);
}

function isStubActivePath(relPath) {
  return (
    /^process\/features\/[^/]+\/active\//.test(relPath) ||
    /^process\/features\/[^/]+\/completed\//.test(relPath)
  );
}

function resolvePath(inputPath) {
  if (path.isAbsolute(inputPath)) {
    return path.relative(root, inputPath);
  }
  return inputPath;
}

function validatePhaseStub(relPath) {
  const absPath = path.join(root, relPath);

  if (!fs.existsSync(absPath)) {
    fail(`${relPath} does not exist on disk`);
    return null;
  }
  if (!relPath.endsWith(".md")) {
    fail(`${relPath} is not a markdown file`);
    return null;
  }
  if (!isStubActivePath(relPath)) {
    warn(`${relPath} is not under process/features/*/active/ or process/features/*/completed/ — skipping path check`);
  }

  const text = read(relPath);
  const lines = text.split("\n");
  const localFailuresBefore = failures.length;
  const localWarningsBefore = warnings.length;

  // YAML frontmatter: line 1 must be ---
  if (lines[0] !== "---") {
    fail(`${relPath} missing YAML frontmatter (line 1 must be '---')`);
  }

  // Extract frontmatter block
  const fmEnd = lines.indexOf("---", 1);
  const frontmatter = fmEnd > 0 ? lines.slice(1, fmEnd).join("\n") : "";

  // Must contain type: plan
  if (!/type:\s*plan/.test(frontmatter)) {
    fail(`${relPath} YAML frontmatter does not contain 'type: plan'`);
  }

  // Must NOT contain phase: umbrella
  if (/phase:\s*umbrella/.test(frontmatter)) {
    fail(`${relPath} is an umbrella plan — use validate-umbrella-artifact.mjs instead`);
    return null;
  }

  // Must contain a phase: field (non-umbrella value)
  if (!/phase:\s*\S+/.test(frontmatter)) {
    fail(`${relPath} YAML frontmatter missing 'phase:' field`);
  }

  // Required: ## Phase Loop Progress
  if (!hasSection(text, "Phase Loop Progress")) {
    fail(`${relPath} missing '## Phase Loop Progress' section`);
  } else {
    // Canonical 7-step inner loop (umbrella C-3): R -> I -> P -> PVL -> E -> EVL -> UP.
    // Phase stubs emit these as numbered list items `1.`..`7.` with phase-name labels.
    // Key on the phase-name label (the stable token), accepting any legitimate list
    // shape: leading indentation, checkbox markers `[ ]`/`[x]`/`[X]`, or a bare
    // numbered prefix `N.`. We accept either the checkbox or numbered list form.
    const stepMarkers = [
      { label: "RESEARCH", re: /RESEARCH/i },
      { label: "INNOVATE", re: /INNOVATE/i },
      { label: "PLAN", re: /PLAN(?:-SUPPLEMENT)?/i },
      { label: "PVL", re: /\bPVL\b/i },
      { label: "EXECUTE", re: /EXECUTE/i },
      { label: "EVL", re: /\bEVL\b/i },
      { label: "UPDATE PROCESS", re: /UPDATE\s*PROCESS/i },
    ];
    // A line counts as a step line if it is a list item (indented `-`/`*` with an
    // optional `[ ]`/`[x]`/`[X]` checkbox, OR a numbered `N.` prefix) AND it names the
    // canonical phase.
    const stepLineRe = /^\s*(?:[-*]\s*(?:\[[ xX]\]\s*)?|\d+[.)]\s*)/;
    const stepLines = lines.filter((l) => stepLineRe.test(l));
    const missingMarkers = stepMarkers
      .filter((m) => !stepLines.some((l) => m.re.test(l)))
      .map((m) => m.label);
    if (missingMarkers.length > 0) {
      fail(`${relPath} Phase Loop Progress missing step markers: ${missingMarkers.join(", ")}`);
    }
  }

  // Required: at least one of ## Implementation Checklist, ## Objective, or ## Purpose
  const hasChecklist = hasSection(text, "Implementation Checklist");
  const hasObjective = hasSection(text, "Objective");
  const hasPurpose = hasSection(text, "Purpose");
  if (!hasChecklist && !hasObjective && !hasPurpose) {
    fail(`${relPath} missing at least one of: '## Implementation Checklist', '## Objective', or '## Purpose'`);
  }

  // Required: ## Validate Contract
  if (!hasSection(text, "Validate Contract")) {
    fail(`${relPath} missing '## Validate Contract' section`);
  }

  // Warnings
  if (!hasSection(text, "Exit Gate")) {
    warn(`${relPath} missing '## Exit Gate' section (recommended)`);
  }

  if (!hasSection(text, "Blast Radius")) {
    warn(`${relPath} missing '## Blast Radius' section (recommended)`);
  }

  if (!/Umbrella plan:|umbrella.*plan/i.test(text)) {
    warn(`${relPath} no back-reference to umbrella plan found (recommended)`);
  }

  if (!/\*\*Validate-contract required/.test(text)) {
    warn(`${relPath} Phase Loop Progress missing bold '**Validate-contract required' warning (recommended)`);
  }

  return {
    path: relPath,
    failures: failures.length - localFailuresBefore,
    warnings: warnings.length - localWarningsBefore,
    lines: lines.length,
  };
}

// Determine which plans to check
let planPaths = [];

if (inputPaths.length > 0) {
  planPaths = inputPaths.map(resolvePath);
} else {
  // Auto-scan for phase stub plans (excluding umbrella files)
  const featureBase = path.join(root, "process/features");
  if (fs.existsSync(featureBase)) {
    const features = fs.readdirSync(featureBase);
    for (const feature of features) {
      for (const subdir of ["active", "completed"]) {
        const dir = path.join(featureBase, feature, subdir);
        if (fs.existsSync(dir)) {
          const files = fs.readdirSync(dir);
          for (const file of files) {
            if (file.endsWith(".md") && !file.includes("umbrella")) {
              planPaths.push(`process/features/${feature}/${subdir}/${file}`);
            }
          }
        }
      }
    }
  }
  if (planPaths.length === 0) {
    warnings.push("No phase stub plans found in process/features/*/active/ or process/features/*/completed/");
  }
}

const checkedPlans = [];
for (const relPath of planPaths) {
  const result = validatePhaseStub(relPath);
  if (result) checkedPlans.push(result);
}

const result = {
  checkedPlans,
  strict,
  warnings,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
