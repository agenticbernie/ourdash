#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

let root;
try {
  root = execSync('git rev-parse --show-toplevel', { stdio: ['pipe', 'pipe', 'pipe'] }).toString().trim();
} catch {
  // Not a git repository — fall back to process.cwd() so the script still works on new projects.
  root = process.cwd();
}
const failures = [];
const warnings = [];
const ignoredSkillFrontmatter = new Set(["sync-from-riper5", "sync-to-riper5"]);

function fail(message) {
  failures.push(message);
}

function warn(message) {
  warnings.push(message);
}

function exists(relPath) {
  return fs.existsSync(path.join(root, relPath));
}

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), "utf8");
}

function walk(dir, predicate, out = []) {
  const abs = path.join(root, dir);
  if (!fs.existsSync(abs)) return out;
  for (const entry of fs.readdirSync(abs, { withFileTypes: true })) {
    const rel = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(rel, predicate, out);
    else if (!predicate || predicate(rel)) out.push(rel);
  }
  return out;
}

function assertContains(file, needle) {
  if (!exists(file)) {
    fail(`${file} missing`);
    return;
  }
  if (!read(file).includes(needle)) {
    fail(`${file} does not mention ${needle}`);
  }
}

function listDirs(relPath) {
  const abs = path.join(root, relPath);
  if (!fs.existsSync(abs)) return [];
  return fs
    .readdirSync(abs, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

function listFiles(relPath, extension) {
  const abs = path.join(root, relPath);
  if (!fs.existsSync(abs)) return [];
  return fs
    .readdirSync(abs, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(extension))
    .map((entry) => entry.name.replace(new RegExp(`${extension}$`), ""))
    .sort();
}

function getGroupEntrypoint(group) {
  const canonical = `process/context/${group}/all-${group}.md`;
  return exists(canonical) ? canonical : null;
}

const legacyEntrypoints = [
  "process/context/README.md",
  // Legacy flat tests entrypoint. The canonical path is the grouped tests router;
  // a flat process/context/tests.md file is a
  // migrated-away legacy shape and must NOT be re-created. (Kept as a guard — this
  // literal flags the legacy flat file if it reappears, and does NOT match the
  // canonical grouped path.)
  "process/context/tests.md",
  ...walk("process/context", (rel) => /\/README\.md$/.test(rel) || /\/[^/]+-README\.md$/.test(rel)),
];

function parseFrontmatter(file) {
  const text = read(file);
  const match = text.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return {};
  return Object.fromEntries(
    match[1]
      .split("\n")
      .map((line) => line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/))
      .filter(Boolean)
      .map((match) => [match[1], match[2].replace(/^["']|["']$/g, "")]),
  );
}

function normalizeForParity(text) {
  return text.replace(/\r\n/g, "\n").replace(/[ \t]+$/gm, "").trim();
}

const agentsSkills = path.join(root, ".agents/skills");
if (!fs.existsSync(agentsSkills)) {
  fail(".agents/skills missing");
} else {
  const real = fs.realpathSync(agentsSkills);
  const expected = fs.realpathSync(path.join(root, ".claude/skills"));
  if (real !== expected) fail(".agents/skills does not resolve to .claude/skills");
}

for (const skill of ["vc-audit-context", "vc-audit-plans", "vc-generate-context", "vc-generate-plan"]) {
  const file = `.claude/skills/${skill}/SKILL.md`;
  const codexPath = `.agents/skills/${skill}/SKILL.md`;
  if (!exists(file)) fail(`${file} missing`);
  if (!exists(codexPath)) fail(`${codexPath} missing`);
  if (exists(file)) {
    const fm = parseFrontmatter(file);
    // YAML name uses vc- prefix matching folder name convention
    if (fm.name !== skill) fail(`${file} frontmatter name is ${fm.name || "missing"}, expected ${skill}`);
    if (!fm.description) fail(`${file} frontmatter description missing`);
  }
}

const skillDirs = listDirs(".claude/skills");
let checkedSkills = 0;
for (const skill of skillDirs) {
  const file = `.claude/skills/${skill}/SKILL.md`;
  const codexPath = `.agents/skills/${skill}/SKILL.md`;
  if (!exists(file)) {
    fail(`${file} missing`);
    continue;
  }
  if (!exists(codexPath)) fail(`${codexPath} missing`);
  checkedSkills += 1;

  const fm = parseFrontmatter(file);
  if (!ignoredSkillFrontmatter.has(skill) && (!fm.name || !fm.description)) {
    fail(`${file} missing name/description frontmatter`);
  }
  if (ignoredSkillFrontmatter.has(skill) && (!fm.name || !fm.description)) {
    warn(`${file} has incomplete frontmatter but is intentionally ignored`);
  }
}

const claudeAgents = listFiles(".claude/agents", ".md");
const codexAgents = listFiles(".codex/agents", ".toml");
for (const agent of claudeAgents) {
  if (!codexAgents.includes(agent)) fail(`.codex/agents/${agent}.toml missing`);
}
for (const agent of codexAgents) {
  if (!claudeAgents.includes(agent)) fail(`.claude/agents/${agent}.md missing`);
}

// Bare-kit mode: process/context/all-context.md is intentionally absent in a freshly
// cloned kit template. Skip all per-project context-doc checks in that case — they
// require a populated context tree that vc-setup creates after install.
const router = "process/context/all-context.md";
const bareKitMode = !exists(router);

if (bareKitMode) {
  process.stderr.write(
    "[bare-kit mode] process/context/all-context.md absent — skipping per-project context-doc checks (kit template not yet set up).\n",
  );
}

const routerText = bareKitMode ? "" : read(router);

if (!bareKitMode) {
  const contextDocs = walk("process/context", (rel) => rel.endsWith(".md")).sort();
  for (const doc of contextDocs) {
    if (doc === router) continue;
    const relFromContext = doc.replace(/^process\/context\//, "");
    const group = relFromContext.split("/")[0];
    const groupEntrypoint = getGroupEntrypoint(group);
    const indexedByRouter = routerText.includes(relFromContext) || routerText.includes(doc);
    const indexedByGroup = groupEntrypoint && read(groupEntrypoint).includes(path.basename(doc));

    if (relFromContext.includes("/") && !groupEntrypoint) {
      fail(`context group ${group} is missing all-${group}.md`);
    }
    if (!indexedByRouter && !indexedByGroup) {
      fail(`${doc} is not indexed by process/context/all-context.md or its group entrypoint`);
    }
  }

  // --- frontmatter routing contract: keyword coverage + related-link integrity ---
  // Build a slug registry (context:{slug}) across all context docs first.
  const contextDocNames = new Set();
  for (const doc of contextDocs) {
    if (doc === router) continue;
    const name = parseFrontmatter(doc).name;
    if (name) contextDocNames.add(name);
  }
  for (const doc of contextDocs) {
    if (doc === router) continue;
    const fm = parseFrontmatter(doc);
    // keywords: required, non-empty — this is the --match routing surface.
    const keywords = (fm.keywords || "")
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    if (keywords.length === 0) {
      // Warn, not fail: pre-existing context docs created before the keyword-routing
      // contract should not break a project's lint on sync. New docs get keywords from
      // the seeds; backfill old ones at UPDATE-PROCESS. Dangling `related` and routing
      // drift below remain hard failures (real breakage, opt-in only).
      warn(`${doc} has empty/missing 'keywords' frontmatter (recommended for keyword routing; backfill at UPDATE-PROCESS — see vc-context-discovery)`);
    }
    // related: every listed slug must resolve to a real context: doc (no dangling cross-links).
    const related = (fm.related || "")
      .replace(/^\[|\]$/g, "")
      .split(",")
      .map((s) => s.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);
    for (const slug of related) {
      if (!contextDocNames.has(slug)) {
        fail(`${doc} 'related' references ${slug} which resolves to no context doc (dangling cross-link)`);
      }
    }
  }

  // --- generated routing block must be in sync with frontmatter on disk ---
  if (routerText.includes("<!-- GENERATED:routing -->")) {
    try {
      execSync(
        `node ${JSON.stringify(path.join(root, ".claude/skills/vc-context-discovery/scripts/discover-context.mjs"))} --check-routing`,
        { cwd: root, stdio: ["pipe", "pipe", "pipe"] },
      );
    } catch {
      fail(`${router} GENERATED:routing block is stale — run discover-context.mjs --emit-routing to rebuild`);
    }
  }

  for (const dir of fs.readdirSync(path.join(root, "process/context"), { withFileTypes: true })) {
    if (dir.isDirectory() && !getGroupEntrypoint(dir.name)) {
      fail(`process/context/${dir.name}/ is missing all-${dir.name}.md`);
    }
  }

  for (const legacy of legacyEntrypoints) {
    if (exists(legacy)) {
      fail(`legacy context entrypoint still exists: ${legacy}`);
    }
  }

  for (const file of [
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/agents/vc-update-process-agent.md",
    ".codex/agents/vc-update-process-agent.toml",
    ".claude/agents/vc-research-agent.md",
    ".codex/agents/vc-research-agent.toml",
    ".claude/skills/vc-generate-context/SKILL.md",
    ".claude/skills/vc-generate-context/references/generate-context.md",
  ]) {
    assertContains(file, "process/context/all-context.md");
  }
}

const criticalHookParityPairs = [
  [
    ".claude/hooks/scout-block/broad-pattern-detector.cjs",
    ".codex/hooks/scout-block/broad-pattern-detector.cjs",
  ],
];

for (const [claudeFile, codexFile] of criticalHookParityPairs) {
  if (!exists(claudeFile) || !exists(codexFile)) continue;
  if (normalizeForParity(read(claudeFile)) !== normalizeForParity(read(codexFile))) {
    fail(`${codexFile} has drift from ${claudeFile}`);
  }
}

const staleWorkflowPatterns = [
  { pattern: "docs-manager", reason: "use update-process-agent for project context/process docs" },
  { pattern: "project-manager", reason: "use update-process-agent for plan/process sync" },
  { pattern: "docs/codebase-summary", reason: "use process/context/all-context.md routing" },
  { pattern: "docs/design-guidelines", reason: "use process/context/ui/ or relevant feature context references" },
  { pattern: "validate-docs", reason: "use audit-context validator" },
  { pattern: "process/context/<group>", reason: "placeholder should not look like a concrete ref" },
  { pattern: ".claude/commands/", reason: "Claude command aliases are retired from the active shared workflow surface" },
  { pattern: "vc:plan", reason: "planning ownership was absorbed into vc-generate-plan + plan-agent" },
  { pattern: "vc:research", reason: "research ownership was absorbed into research-agent" },
  { pattern: "vc:cook", reason: "execution ownership was absorbed into execute-agent" },
  { pattern: "vc:fix", reason: "bug-fix ownership was absorbed into debugger + execute-agent" },
  { pattern: "vc:code-review", reason: "review ownership was absorbed into code-reviewer" },
  { pattern: "/vc:journal", reason: "journal handoff is not part of the surviving default workflow surface" },
];
// In bare-kit mode, skip scanning process/context/ files for stale patterns
// (the directory may not exist yet). Kit-structural files (.claude, .codex, AGENTS.md)
// are always scanned.
const staleWorkflowFiles = [
  "AGENTS.md",
  "CLAUDE.md",
  ...walk(".claude/agents", (rel) => rel.endsWith(".md")),
  ...walk(".codex/agents", (rel) => rel.endsWith(".toml")),
  ...walk(".claude/skills", (rel) => rel.endsWith(".md") && !rel.includes("/scripts/")),
  ...walk(".claude/hooks", (rel) => rel.endsWith(".cjs") || rel.endsWith(".json")),
  ...walk(".codex/hooks", (rel) => rel.endsWith(".cjs") || rel.endsWith(".json")),
  ...(bareKitMode ? [] : walk("process/context", (rel) => rel.endsWith(".md"))),
];

for (const file of staleWorkflowFiles) {
  if (!exists(file)) continue;
  const lines = read(file).split("\n");
  for (const [index, line] of lines.entries()) {
    for (const { pattern, reason } of staleWorkflowPatterns) {
      if (!line.includes(pattern)) continue;
      if (
        line.includes("formerly taught") ||
        line.includes("previously taught") ||
        line.includes("previously spread across") ||
        line.includes("previously split across") ||
        line.includes("migration sources only") ||
        line.includes("absorbed into") ||
        line.includes("absorbed here")
      ) {
        continue;
      }
      if (pattern === "vc:plan" && /vc:plan-\w/.test(line)) continue;
      if (pattern === "docs-manager" && line.includes("not `./docs`")) continue;
      fail(`${file}:${index + 1} contains stale ${pattern} reference (${reason})`);
    }
    if (line.includes("`./docs`") && !line.includes("not `./docs`")) {
      fail(`${file}:${index + 1} references legacy ./docs path (use process/context/all-context.md)`);
    }
  }
}

// Concrete-ref validation: in bare-kit mode, process/context/ docs are absent by design,
// so refs from .claude/.codex files pointing to them would false-fail. Skip in bare-kit mode.
let concreteRefs = [];
if (!bareKitMode) {
  const filesWithRefs = [
    "AGENTS.md",
    ...walk(".claude", (rel) => rel.endsWith(".md") || rel.endsWith(".json")),
    ...walk(".codex", (rel) => rel.endsWith(".toml") || rel.endsWith(".json")),
    ...walk("process/context", (rel) => rel.endsWith(".md")),
  ];

  for (const file of filesWithRefs) {
    if (!exists(file)) continue;
    // Strip HTML comments (including multi-line) before scanning for backtick refs.
    // Commented-out example content is not live routing and must not trigger path checks.
    const text = read(file).replace(/<!--[\s\S]*?-->/g, "");
    for (const match of text.matchAll(/`(process\/context\/[^`\s]+)`/g)) {
      const ref = match[1].replace(/[.,;:]$/, "");
      if (/[{}[*\]]/.test(ref)) continue;
      concreteRefs.push({ file, ref });
    }
  }

  for (const { file, ref } of concreteRefs) {
    if (!exists(ref)) fail(`${file} references missing ${ref}`);
  }

  const contextDocsForCheck = walk("process/context", (rel) => rel.endsWith(".md")).sort();
  if (contextDocsForCheck.length > 0 && !routerText.includes("Context Group Lifecycle")) {
    fail(`${router} missing Context Group Lifecycle section`);
  }

  if (routerText.includes("Suggested future groups")) {
    warn("context group migration is planned but not fully executed yet");
  }
}

const result = {
  checkedContextDocs: bareKitMode ? 0 : walk("process/context", (rel) => rel.endsWith(".md")).length,
  checkedConcreteRefs: concreteRefs.length,
  checkedSkills,
  checkedClaudeAgents: claudeAgents.length,
  checkedCodexAgents: codexAgents.length,
  warnings,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
