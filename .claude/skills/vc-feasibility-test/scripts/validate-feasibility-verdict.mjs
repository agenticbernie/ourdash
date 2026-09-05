#!/usr/bin/env node
/**
 * Validate that a VERDICT artifact produced by vc-feasibility-test has all
 * required sections, a valid verdict keyword, a valid probe cost class, and the
 * three licenses/forbids/uncertain sub-labels in Resulting Design Constraint.
 *
 * Usage:
 *   node validate-feasibility-verdict.mjs <path-to-verdict-file>
 *
 * Exit 0: all required sections present, verdict + cost class valid, sub-labels present.
 * Exit 1: any required section missing OR verdict/cost-class invalid OR sub-labels missing.
 * Output: JSON { file, sectionsFound, verdictValue, costClass, failures }
 */

import fs from "node:fs";
import path from "node:path";

const filePath = process.argv[2];

if (!filePath) {
  console.error("Usage: node validate-feasibility-verdict.mjs <path-to-verdict-file>");
  process.exitCode = 1;
  process.exit();
}

const root = process.cwd();
const absPath = path.isAbsolute(filePath) ? filePath : path.join(root, filePath);

if (!fs.existsSync(absPath)) {
  console.error(`ERROR: File not found: ${filePath}`);
  process.exitCode = 1;
  process.exit();
}

const content = fs.readFileSync(absPath, "utf8");
const failures = [];

// ---------------------------------------------------------------------------
// Required section headers (case-insensitive, ## prefix).
// ---------------------------------------------------------------------------
const REQUIRED_SECTIONS = [
  "Hypothesis",
  "Mechanism Under Test",
  "Probe Family",
  "Probe Cost Class",
  "Probe Method",
  "Evidence Captured",
  "Verdict",
  "Resulting Design Constraint",
];

const VALID_VERDICTS = new Set(["VIABLE", "NOT-VIABLE", "INCONCLUSIVE"]);
const VALID_ORIGINATING_PHASES = new Set(["spec", "innovate", "pvl"]);
const VALID_COST_CLASSES = [
  "cheap-local",
  "needs-container",
  "needs-live-provider",
  "needs-browser",
  "needs-cf",
];
// The three sub-labels that MUST appear inside ## Resulting Design Constraint.
const REQUIRED_CONSTRAINT_LABELS = [
  "What this licenses",
  "What this forbids",
  "What remains uncertain",
];

// ---------------------------------------------------------------------------
// Check for presence of all 6 required sections.
// Match: a line that is exactly "## <section name>" (case-insensitive, trimmed).
// ---------------------------------------------------------------------------
const sectionsFound = [];

for (const section of REQUIRED_SECTIONS) {
  const re = new RegExp(`^##\\s+${section.replace(/\s+/g, "\\s+")}\\s*$`, "im");
  if (re.test(content)) {
    sectionsFound.push(section);
  } else {
    failures.push(`FAIL: missing required section: ## ${section}`);
  }
}

// ---------------------------------------------------------------------------
// Extract and validate the verdict value.
// Find the ## Verdict section, then scan subsequent non-empty lines for one
// of the 3 allowed keywords (case-insensitive).
// ---------------------------------------------------------------------------
let verdictValue = null;

const verdictSectionMatch = content.match(/^##\s+Verdict\s*$/im);
if (verdictSectionMatch) {
  // Extract text after the Verdict header until the next ## header or end of file
  const afterVerdict = content.slice(
    verdictSectionMatch.index + verdictSectionMatch[0].length,
  );
  const nextHeaderMatch = afterVerdict.match(/^##\s+/m);
  const verdictBlock = nextHeaderMatch
    ? afterVerdict.slice(0, nextHeaderMatch.index)
    : afterVerdict;

  // Scan lines for a valid verdict keyword
  for (const line of verdictBlock.split("\n")) {
    const trimmed = line.trim().toUpperCase();
    if (VALID_VERDICTS.has(trimmed)) {
      verdictValue = trimmed;
      break;
    }
  }

  if (!verdictValue) {
    failures.push(
      `FAIL: ## Verdict section found but no valid verdict keyword (expected one of: VIABLE, NOT-VIABLE, INCONCLUSIVE)`,
    );
  }
}
// If ## Verdict section is absent, it was already recorded as a missing section above.

// ---------------------------------------------------------------------------
// Validate the probe cost class (only if the section is present).
// Scan the ## Probe Cost Class block for one of the valid class tokens.
// ---------------------------------------------------------------------------
let costClass = null;

const costSectionMatch = content.match(/^##\s+Probe\s+Cost\s+Class\s*$/im);
if (costSectionMatch) {
  const afterCost = content.slice(
    costSectionMatch.index + costSectionMatch[0].length,
  );
  const nextHeaderMatch = afterCost.match(/^##\s+/m);
  const costBlock = (
    nextHeaderMatch ? afterCost.slice(0, nextHeaderMatch.index) : afterCost
  ).toLowerCase();

  for (const cls of VALID_COST_CLASSES) {
    if (costBlock.includes(cls)) {
      costClass = cls;
      break;
    }
  }

  if (!costClass) {
    failures.push(
      `FAIL: ## Probe Cost Class section found but no valid class (expected one of: ${VALID_COST_CLASSES.join(", ")})`,
    );
  }
}

// ---------------------------------------------------------------------------
// Validate the three required sub-labels inside Resulting Design Constraint.
// Match case-insensitively anywhere in the file body (they are bolded labels,
// e.g. "**What this licenses:**").
// ---------------------------------------------------------------------------
for (const label of REQUIRED_CONSTRAINT_LABELS) {
  const re = new RegExp(label.replace(/\s+/g, "\\s+"), "i");
  if (!re.test(content)) {
    failures.push(
      `FAIL: Resulting Design Constraint missing required sub-label: "${label}"`,
    );
  }
}

// ---------------------------------------------------------------------------
// Validate originating-phase field (required; must be in frontmatter or
// anywhere in document as "originating-phase: <value>").
// Valid values: spec | innovate | pvl
// ---------------------------------------------------------------------------
let originatingPhase = null;

const originMatch = content.match(/^originating-phase:\s*(\S+)\s*$/im);
if (!originMatch) {
  failures.push(
    `FAIL: missing required field: originating-phase (must be one of: ${[...VALID_ORIGINATING_PHASES].join(", ")})`,
  );
} else {
  originatingPhase = originMatch[1].toLowerCase();
  if (!VALID_ORIGINATING_PHASES.has(originatingPhase)) {
    failures.push(
      `FAIL: originating-phase has invalid value "${originMatch[1]}" (expected one of: ${[...VALID_ORIGINATING_PHASES].join(", ")})`,
    );
    originatingPhase = originMatch[1]; // preserve original for output
  }
}

const result = {
  file: filePath,
  sectionsFound,
  verdictValue,
  costClass,
  originatingPhase,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
