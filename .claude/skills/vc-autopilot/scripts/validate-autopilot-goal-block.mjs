#!/usr/bin/env node
// Validates a vc-autopilot provisional goal block artifact (markdown).
// FAIL (exit 1) if any of the 9 required fields are missing, if EXECUTE CONSENT
// does not contain "standing-granted", or if total character count exceeds 4000.
// WARN (exit 0) if TEST GATES contains "TBD" (V7 UPDATE not yet run).
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
  fail("Usage: node validate-autopilot-goal-block.mjs <artifact-path>");
} else if (!exists(target)) {
  fail(`${target} does not exist on disk`);
} else {
  const text = read(target);

  // 1. Required field presence checks (exact string match, each must appear on its own line).
  const requiredFields = [
    "SESSION GOAL:",
    "ENTRY PHASE:",
    "REMAINING PHASES:",
    "CLARIFICATIONS LOCKED:",
    "EXECUTE CONSENT:",
    "DECISION POLICY:",
    "HARD STOPS:",
    "TEST GATES:",
    "START:",
  ];

  for (const field of requiredFields) {
    if (!text.includes(field)) {
      fail(`${target} missing required field: ${field}`);
    }
  }

  // 2. EXECUTE CONSENT special rule: must contain the literal text "standing-granted".
  if (text.includes("EXECUTE CONSENT:")) {
    const executeConsentLine = text
      .split("\n")
      .find((line) => line.includes("EXECUTE CONSENT:"));
    if (executeConsentLine && !executeConsentLine.includes("standing-granted")) {
      fail(
        `${target} EXECUTE CONSENT field found but does not contain "standing-granted" — got: ${executeConsentLine.trim()}`
      );
    }
  }

  // 3. Character limit: total block must be <= 4000 characters.
  if (text.length > 4000) {
    fail(
      `${target} exceeds 4000-character limit — actual length: ${text.length} characters`
    );
  }

  // 4. WARN if TEST GATES contains TBD (V7 UPDATE variant not yet emitted — not a failure).
  if (text.includes("TEST GATES:")) {
    const testGatesLine = text
      .split("\n")
      .find((line) => line.includes("TEST GATES:"));
    if (testGatesLine && testGatesLine.includes("TBD")) {
      warn(
        `${target} TEST GATES field contains "TBD" — V7 (UPDATE) variant has not been emitted yet; replace with real gate commands after VALIDATE runs`
      );
    }
  }

  // 5. Optional LANE field check: if present, value must be one of quick|fast|full.
  //    If absent entirely, that is fine — LANE is optional (backward compatible).
  const validLaneValues = ["quick", "fast", "full"];
  let laneStatus = "absent";
  if (text.includes("LANE:")) {
    const laneLine = text
      .split("\n")
      .find((line) => line.trimStart().startsWith("LANE:"));
    if (laneLine) {
      const laneValue = laneLine.replace(/^.*LANE:\s*/, "").trim();
      if (!validLaneValues.includes(laneValue)) {
        fail(
          `${target} LANE field present but value is invalid: "${laneValue}" — expected one of: quick, fast, full`
        );
        laneStatus = `invalid: ${laneValue}`;
      } else {
        laneStatus = laneValue;
      }
    }
  }
}

// Print warnings.
for (const w of warnings) {
  console.log(`WARN: ${w}`);
}

if (failures.length > 0) {
  for (const f of failures) {
    console.log(`FAIL: ${f}`);
  }
  process.exitCode = 1;
} else {
  // Recompute laneStatus for the PASS message (it was declared inside the else block above).
  let laneStatusMsg = "absent";
  if (target && fs.existsSync(path.resolve(process.cwd(), target))) {
    const txt = fs.readFileSync(path.resolve(process.cwd(), target), "utf8");
    if (txt.includes("LANE:")) {
      const ll = txt.split("\n").find((line) => line.trimStart().startsWith("LANE:"));
      if (ll) {
        const lv = ll.replace(/^.*LANE:\s*/, "").trim();
        laneStatusMsg = ["quick", "fast", "full"].includes(lv) ? lv : `invalid: ${lv}`;
      }
    }
  }
  console.log(
    `PASS: ${target ?? "<no target>"} — all required fields present, LANE field: ${laneStatusMsg}${warnings.length > 0 ? ` (${warnings.length} warning(s))` : ""}`
  );
}
