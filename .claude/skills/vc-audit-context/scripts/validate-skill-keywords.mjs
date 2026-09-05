#!/usr/bin/env node
// Validator: every .claude/skills/*/SKILL.md MUST carry a non-empty top-level
// `trigger_keywords:` scalar AND a `layer:` scalar in {actor, contract, helper}.
// Also asserts the generated skills catalog is in sync (delegates to
// generate-skills-catalog.mjs --check). Exits 1 on any failure.
import { execSync } from "node:child_process";
import { listSkillDirs, parseFrontmatter, exists, abs } from "./shared-skill-utils.mjs";

const VALID_LAYERS = new Set(["actor", "contract", "helper"]);

const failures = [];
const warnings = [];

const skills = listSkillDirs();
let checked = 0;
const tally = { actor: 0, contract: 0, helper: 0 };

for (const skill of skills) {
  const rel = `.claude/skills/${skill}/SKILL.md`;
  if (!exists(rel)) {
    failures.push(`${rel}: SKILL.md missing`);
    continue;
  }
  checked += 1;
  const parsed = parseFrontmatter(rel);
  const fm = parsed?.fields || {};

  const kw = (fm.trigger_keywords || "").trim();
  if (!kw) {
    failures.push(`${rel}: missing or empty 'trigger_keywords'`);
  } else if (kw.split(",").map((s) => s.trim()).filter(Boolean).length === 0) {
    failures.push(`${rel}: 'trigger_keywords' has no usable keywords`);
  }

  const layer = (fm.layer || "").trim();
  if (!layer) {
    failures.push(`${rel}: missing 'layer'`);
  } else if (!VALID_LAYERS.has(layer)) {
    failures.push(`${rel}: invalid layer '${layer}' (must be one of ${[...VALID_LAYERS].join(", ")})`);
  } else {
    tally[layer] += 1;
  }
}

// Catalog sync gate.
try {
  execSync("node .claude/skills/vc-audit-context/scripts/generate-skills-catalog.mjs --check", {
    cwd: abs("."),
    stdio: "pipe",
  });
} catch (err) {
  const out = (err.stderr || err.stdout || "").toString().trim();
  failures.push(`generated-skills-catalog.json is stale: ${out || "run generate-skills-catalog.mjs --write"}`);
}

const result = {
  checkedSkills: checked,
  tally,
  warnings,
  failures,
};
console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
