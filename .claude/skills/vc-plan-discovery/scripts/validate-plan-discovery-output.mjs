#!/usr/bin/env node
// Validates a vc-plan-discovery OUTPUT artifact (markdown).
// FAIL if any of the 5 folder sections is absent, or if the surfaced-frontmatter
// block does not contain all 4 field labels (name, description, feature, phase).
// Exit-code-1-on-failure pattern (mirrors validate-plan-artifact.mjs): push to
// failures[], never throw for a check failure.
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

function warn(message) {
  warnings.push(message);
}

function exists(relPath) {
  return fs.existsSync(path.resolve(root, relPath));
}

function read(relPath) {
  return fs.readFileSync(path.resolve(root, relPath), "utf8");
}

const target = process.argv.slice(2).find((a) => !a.startsWith("--"));

if (!target) {
  fail("Usage: node validate-plan-discovery-output.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 5 folder sections per vc-plan-discovery/SKILL.md Output Format:
  // Active Plans / Backlog / Completed / Reports / References
  const sections = [
    { label: "Active Plans / same-feature", re: /^#{2,3}\s+.*(active plans|same-feature)/im },
    { label: "Backlog", re: /^#{2,3}\s+.*backlog/im },
    { label: "Completed / other-feature", re: /^#{2,3}\s+.*(completed|other[- ]feature)/im },
    { label: "Reports", re: /^#{2,3}\s+.*reports/im },
    { label: "References / refs", re: /^#{2,3}\s+.*(references|refs)/im },
  ];
  for (const s of sections) {
    if (!s.re.test(text)) {
      fail(`${target} missing folder section: ${s.label}`);
    }
  }

  // Surfaced-frontmatter block must contain all 4 field labels.
  const frontmatterFields = ["name", "description", "feature", "phase"];
  for (const field of frontmatterFields) {
    if (!new RegExp(`\\b${field}\\b`, "i").test(text)) {
      fail(`${target} surfaced frontmatter missing field label: ${field}`);
    }
  }
}

const result = {
  target: target ?? null,
  warnings,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
