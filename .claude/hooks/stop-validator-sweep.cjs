#!/usr/bin/env node
// stop-validator-sweep.cjs — Stop hook (whole-tree scan validators, Bucket B).
//
// At turn end, look at which tracked files are dirty (git working tree vs HEAD). For each
// validator GROUP whose path pattern has dirty files, run that group's validators and surface
// any failures/warnings. Groups with no dirty files are skipped, so a normal coding turn that
// never touches .claude/ or process/ is a clean no-op.
//
// Warn-only by design: this hook NEVER blocks (always exits 0). It prints an advisory summary
// so the agent/user notices harness/context/plan drift without interrupting the flow.
//
// Single-file artifact validators (umbrella/phase-stub/plan) are handled by the PostToolUse
// hook (post-write-plan-check.mjs) instead — this hook owns only the tree scans.

const path = require("node:path");
const fs = require("node:fs");
const { spawnSync } = require("node:child_process");

const HOOK_DIR = __dirname;
const REPO_ROOT = path.resolve(HOOK_DIR, "..", "..");

// Each group runs only when at least one dirty file matches `pathRe`.
const GROUPS = [
  {
    name: "harness",
    pathRe: /^\.claude\/(agents|skills)\/|^process\/development-protocols\//,
    validators: [
      "vc-audit-vc/scripts/validate-agent-parity.mjs",
      "vc-audit-vc/scripts/validate-skills.mjs",
      "vc-audit-vc/scripts/validate-guide-sync.mjs",
      "vc-audit-vc/scripts/validate-protocol-wiring.mjs",
      "vc-audit-vc/scripts/validate-kit-portability.mjs",
      "vc-audit-vc/scripts/validate-skill-invocation-wiring.mjs",
    ],
  },
  {
    name: "context",
    pathRe: /^process\/context\//,
    validators: [
      "vc-audit-context/scripts/validate-context-discovery.mjs",
      "vc-audit-context/scripts/validate-protocol-discovery.mjs",
      "vc-audit-context/scripts/validate-skill-keywords.mjs",
      "vc-audit-context/scripts/validate-skill-routing.mjs",
      "vc-audit-context/scripts/validate-skill-cross-refs.mjs",
      "vc-audit-context/scripts/validate-skill-dependencies.mjs",
      "vc-audit-context/scripts/validate-confusable-skills.mjs",
      "vc-generate-context/scripts/validate-all-context.mjs",
    ],
  },
  {
    name: "plans",
    pathRe: /^process\/(features|general-plans)\/.*\/(active|backlog)\//,
    validators: [
      "vc-audit-plans/scripts/validate-plan-inventory.mjs",
      "vc-audit-plans/scripts/validate-umbrella-state.mjs",
      "vc-audit-plans/scripts/validate-phase-reports.mjs",
      "vc-audit-plans/scripts/validate-phase-plan-completeness.mjs",
      "vc-audit-plans/scripts/validate-backlog-notes.mjs",
      "vc-audit-plans/scripts/validate-eval-coverage.mjs",
    ],
  },
];

function readPayload() {
  try {
    const raw = fs.readFileSync(0, "utf8").trim();
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function dirtyFiles() {
  // Staged + unstaged + untracked, repo-relative. Empty on any git error.
  const res = spawnSync("git", ["status", "--porcelain", "-z"], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  if (res.status !== 0 || !res.stdout) return [];
  // -z entries: "XY <path>\0" (rename uses two \0-separated paths; we keep both halves).
  return res.stdout
    .split("\0")
    .map((e) => e.replace(/^.. /, "").trim())
    .filter(Boolean);
}

// Pull failure/warning counts out of a validator's JSON output when possible.
function summarize(stdout) {
  try {
    const obj = JSON.parse(stdout);
    const fails = Array.isArray(obj.failures) ? obj.failures.length : 0;
    const warns = Array.isArray(obj.warnings) ? obj.warnings.length : 0;
    return { fails, warns, parsed: true };
  } catch {
    return { fails: 0, warns: 0, parsed: false };
  }
}

function main() {
  const payload = readPayload();
  // Prevent any chance of a Stop-hook loop.
  if (payload.stop_hook_active) process.exit(0);

  const dirty = dirtyFiles();
  if (!dirty.length) process.exit(0);

  const lines = [];
  for (const group of GROUPS) {
    if (!dirty.some((f) => group.pathRe.test(f))) continue;

    for (const rel of group.validators) {
      const abs = path.join(REPO_ROOT, ".claude/skills", rel);
      if (!fs.existsSync(abs)) continue;
      const res = spawnSync("node", [abs], { cwd: REPO_ROOT, encoding: "utf8" });
      const out = (res.stdout || "").trim();
      const { fails, warns, parsed } = summarize(out);

      if (fails > 0) {
        lines.push(`  [FAIL ${fails}] ${group.name}: ${path.basename(rel)}`);
      } else if (!parsed && res.status !== 0) {
        // Non-JSON output AND non-zero exit — surface as a possible failure.
        lines.push(`  [FAIL?] ${group.name}: ${path.basename(rel)} (exit ${res.status})`);
      } else if (warns > 0) {
        lines.push(`  [warn ${warns}] ${group.name}: ${path.basename(rel)}`);
      }
    }
  }

  if (lines.length) {
    console.log(
      "stop-validator-sweep: harness/context/plan validators on dirty files (advisory, non-blocking):\n" +
        lines.join("\n") +
        "\nRun the matching vc-audit-* skill for full details.",
    );
  }
  process.exit(0);
}

try {
  main();
} catch (error) {
  console.log(`stop-validator-sweep: hook error (ignored): ${error && error.message}`);
  process.exit(0);
}
