#!/usr/bin/env node
// Validates backlog NOTE files in a backlog/ directory.
// Arg = a backlog dir path. FAIL unless every NOTE file in scope carries the required
// metadata: a `status` of BLOCKED / done-with-gap, an `item`/`id`, and a `reason`.
// An empty dir = pass (vacuously). FAIL only on a malformed NOTE.
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const failures = [];
const warnings = [];

function fail(message) {
  failures.push(message);
}

const target = process.argv.slice(2).find((a) => !a.startsWith("--"));

if (!target) {
  fail("Usage: node validate-backlog-notes.mjs <backlog-dir>");
} else {
  const dir = path.resolve(root, target);
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    fail(`${target} does not exist or is not a directory`);
  } else {
    // NOTE files: *.md (and *NOTE* files). Empty dir => vacuous pass.
    const noteFiles = fs
      .readdirSync(dir)
      .filter((f) => /\.md$/i.test(f) || /note/i.test(f))
      .filter((f) => fs.statSync(path.join(dir, f)).isFile());

    for (const f of noteFiles) {
      const text = fs.readFileSync(path.join(dir, f), "utf8");

      // status: must be one of BLOCKED / done-with-gap.
      const statusMatch = text.match(/status\s*[:=]\s*([A-Za-z-]+)/i);
      const statusVal = statusMatch ? statusMatch[1].toLowerCase() : null;
      if (statusVal !== "blocked" && statusVal !== "done-with-gap") {
        fail(`${target}/${f} missing valid 'status' (expected BLOCKED or done-with-gap; got ${JSON.stringify(statusVal)})`);
      }

      // item or id field.
      if (!/\b(item|id)\s*[:=]/i.test(text)) {
        fail(`${target}/${f} missing 'item'/'id' field`);
      }

      // reason field.
      if (!/\breason\s*[:=]/i.test(text)) {
        fail(`${target}/${f} missing 'reason' field`);
      }
    }
  }
}

console.log(JSON.stringify({ target: target ?? null, warnings, failures }, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
