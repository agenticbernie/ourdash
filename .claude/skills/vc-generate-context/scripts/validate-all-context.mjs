#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const strict = process.argv.includes("--strict");
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

function warn(message) {
  if (strict) failures.push(message);
  else warnings.push(message);
}

function exists(relPath) {
  return fs.existsSync(path.join(root, relPath));
}

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), "utf8");
}

const contextFile = "process/context/all-context.md";

// Bare-kit mode: process/context/all-context.md is intentionally absent in a freshly
// cloned kit template. All checks in this validator require a populated context file,
// so skip them entirely and exit 0 with a clear notice.
if (!exists(contextFile)) {
  process.stderr.write(
    "[bare-kit mode] process/context/all-context.md absent — skipping per-project context-doc checks (kit template not yet set up).\n",
  );
  console.log(JSON.stringify({ checkedFile: contextFile, lineCount: 0, strict, warnings: [], failures: [] }, null, 2));
  process.exit(0);
}

let lineCount = 0;
if (exists(contextFile)) {
  const text = read(contextFile);
  const lines = text.split("\n");
  lineCount = lines.length;

  // Strip leading YAML frontmatter (---\n...\n---\n) before checking for heading,
  // so files that begin with frontmatter are not falsely flagged.
  const textWithoutFrontmatter = text.startsWith("---")
    ? text.replace(/^---\n[\s\S]*?\n---\n/, "")
    : text;
  if (!/^#\s+/.test(textWithoutFrontmatter)) fail(`${contextFile} missing top-level heading`);
  for (const section of ["Repository Structure", "Technology Stack"]) {
    if (!text.includes(`## ${section}`)) fail(`${contextFile} missing ${section} section`);
  }
  if (!/Last updated:\s*\d{4}-\d{2}-\d{2}/i.test(text)) {
    fail(`${contextFile} missing Last updated date in YYYY-MM-DD format`);
  } else {
    const dateText = text.match(/Last updated:\s*(\d{4}-\d{2}-\d{2})/i)?.[1];
    const updatedAt = new Date(`${dateText}T00:00:00Z`);
    const ageDays = Math.floor((Date.now() - updatedAt.getTime()) / 86400000);
    if (ageDays > 14) warn(`${contextFile} is ${ageDays} days old; consider generate-context refresh`);
  }
  if (!/Repo HEAD|git rev-parse HEAD|commit/i.test(text)) {
    warn(`${contextFile} does not include repo HEAD or commit metadata`);
  }
  if (!/References|Source references|Key files/i.test(text)) {
    warn(`${contextFile} does not include an obvious source references section`);
  }
  if (!/Open Questions|Outstanding Work/i.test(text)) {
    warn(`${contextFile} does not include Open Questions or Outstanding Work`);
  }
  if (!text.includes("process/context/all-context.md")) {
    warn(`${contextFile} does not mention the context router`);
  }
  if (text.includes("process/plans/")) {
    warn(`${contextFile} mentions legacy process/plans/ path`);
  }
  if (/sk-[A-Za-z0-9_-]{20,}|BEGIN (RSA|OPENSSH|PRIVATE) KEY|DATABASE_URL=.*:.*@/.test(text)) {
    fail(`${contextFile} appears to contain a secret-like value`);
  }

  const concreteRefs = [];
  for (const match of text.matchAll(/`((?:apps|packages|process|\.claude|\.codex|\.agents)\/[^`\s]+)`/g)) {
    const ref = match[1].replace(/[.,;:]$/, "");
    if (/[{}[*\]]/.test(ref)) continue;
    concreteRefs.push(ref);
  }
  const missingRefs = concreteRefs.filter((ref) => !exists(ref));
  if (missingRefs.length > 0) {
    warn(`${contextFile} has ${missingRefs.length} concrete refs that do not exist`);
  }
}

const result = {
  checkedFile: contextFile,
  lineCount,
  strict,
  warnings,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
