#!/usr/bin/env node
// Validates that a phase plan contains all 4 required sections.
// FAIL unless ALL of: an Implementation Checklist (any `## ...Checklist`), Blast
// Radius, Verification Evidence, and a Test-Infra-Improvement-Notes section are present.
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

function hasSection(text, namePattern) {
  return new RegExp(`^##\\s+${namePattern}`, "im").test(text);
}

const target = process.argv.slice(2).find((a) => !a.startsWith("--"));

if (!target) {
  fail("Usage: node validate-phase-plan-completeness.mjs <phase-plan-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  const required = [
    { label: "Implementation Checklist", pattern: ".*Checklist" },
    { label: "Blast Radius", pattern: "Blast Radius" },
    { label: "Verification Evidence", pattern: "Verification Evidence" },
    {
      label: "Test Infra Improvement Notes",
      pattern: "Test Infra(structure)? Improvement( Notes)?",
    },
  ];

  for (const r of required) {
    if (!hasSection(text, r.pattern)) {
      fail(`${target} missing required section: ## ${r.label}`);
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
