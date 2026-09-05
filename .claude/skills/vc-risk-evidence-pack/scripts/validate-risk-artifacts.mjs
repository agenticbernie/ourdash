#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const artifactDir = process.argv[2];

if (!artifactDir) {
  console.error("Usage: node .claude/skills/vc-risk-evidence-pack/scripts/validate-risk-artifacts.mjs <artifact-dir>");
  process.exit(1);
}

const root = path.resolve(process.cwd(), artifactDir);
const failures = [];
const warnings = [];

function readJson(filename) {
  const file = path.join(root, filename);
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function requireFields(filename, value, fields) {
  if (!value || typeof value !== "object") {
    failures.push(`${filename} missing or invalid JSON object`);
    return;
  }
  for (const field of fields) {
    if (!(field in value)) {
      failures.push(`${filename} missing ${field}`);
    }
  }
}

const riskGate = readJson("risk-gate.json");
const contextSnippets = readJson("context-snippets.json");
const verification = readJson("verification.json");
const reviewDecision = readJson("review-decision.json");
const adversarialValidation = readJson("adversarial-validation.json");

requireFields("risk-gate.json", riskGate, [
  "task",
  "planPath",
  "riskLevel",
  "riskClasses",
  "mustStopBeforeFinalize",
  "humanApprovalRequired",
  "why",
]);
requireFields("context-snippets.json", contextSnippets, ["task"]);
requireFields("verification.json", verification, ["task", "commands", "manualChecks", "result"]);
requireFields("review-decision.json", reviewDecision, ["task", "decision", "blockingFindings", "nonBlockingFindings", "notes"]);

if (riskGate && !["low", "medium", "high"].includes(riskGate.riskLevel)) {
  failures.push("risk-gate.json riskLevel must be low, medium, or high");
}

if (riskGate && !Array.isArray(riskGate.riskClasses)) {
  failures.push("risk-gate.json riskClasses must be an array");
}

if (verification && !Array.isArray(verification.commands)) {
  failures.push("verification.json commands must be an array");
}

if (verification && !Array.isArray(verification.manualChecks)) {
  failures.push("verification.json manualChecks must be an array");
}

if (reviewDecision && !["approved", "approved-with-concerns", "rejected"].includes(reviewDecision.decision)) {
  failures.push("review-decision.json decision must be approved, approved-with-concerns, or rejected");
}

if (riskGate?.riskLevel === "high" && !adversarialValidation) {
  warnings.push("high-risk pack is missing adversarial-validation.json");
}

console.log(JSON.stringify({
  artifactDir: root,
  warnings,
  failures,
}, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
