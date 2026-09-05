#!/usr/bin/env node
// post-commit-lint.mjs — PostToolUse(Bash) hook.
//
// When a Bash invocation is a `git commit`, lint the commit message for a conventional-commits
// prefix (feat|fix|docs|spec|process|phase|chore|refactor|test, with optional scope and `!`).
// Non-commit Bash is a clean no-op. Mirrors the I/O + fail-open exit conventions of the existing
// `.cjs` hooks (read stdin payload, never throw, always exit 0 — advisory only).

import fs from "node:fs";

const CONVENTIONAL_PREFIX_RE =
  /^(feat|fix|docs|spec|process|phase|chore|refactor|test)(\([^)]+\))?!?:\s+\S/;

function readPayload() {
  try {
    const raw = fs.readFileSync(0, "utf8").trim();
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function extractCommand(payload) {
  const input = payload.tool_input || payload.toolInput || {};
  return input.command || "";
}

// Pull the commit message out of `git commit -m "..."` / `-m '...'`.
function extractCommitMessage(command) {
  const m =
    command.match(/-m\s+"((?:[^"\\]|\\.)*)"/) ||
    command.match(/-m\s+'((?:[^'\\]|\\.)*)'/);
  return m ? m[1] : null;
}

function isGitCommit(command) {
  return /\bgit\s+commit\b/.test(command);
}

function main() {
  const payload = readPayload();
  const command = extractCommand(payload);

  if (!command || !isGitCommit(command)) {
    // Not a git commit — no-op.
    process.exit(0);
  }

  const message = extractCommitMessage(command);
  if (message == null) {
    // commit without inline -m (e.g. editor-driven) — cannot lint here; no-op.
    process.exit(0);
  }

  const firstLine = message.split("\n")[0].trim();
  if (CONVENTIONAL_PREFIX_RE.test(firstLine)) {
    console.log(`post-commit-lint: conventional prefix OK — "${firstLine}"`);
  } else {
    console.log(
      `post-commit-lint: WARNING — commit message does not start with a conventional prefix ` +
        `(feat|fix|docs|spec|process|phase|chore|refactor|test): "${firstLine}"`,
    );
  }

  // Fail-open: advisory only; never block the commit.
  process.exit(0);
}

try {
  main();
} catch (error) {
  console.log(`post-commit-lint: hook error (ignored): ${error && error.message}`);
  process.exit(0);
}
