#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const args = new Set(process.argv.slice(2));
const outFlagIndex = process.argv.indexOf("--out");
const dryRun = args.has("--dry-run");

if (outFlagIndex === -1 || !process.argv[outFlagIndex + 1]) {
  console.error("Usage: export-benchmark-kit.mjs --out <directory> [--dry-run]");
  process.exitCode = 1;
  process.exit();
}

const repoRoot = execSync("git rev-parse --show-toplevel").toString().trim();
const outDir = path.resolve(process.argv[outFlagIndex + 1]);
const manifestPath = path.join(repoRoot, "vc-manifest.json");
const dotGitDirName = `.${"git"}`;

function toPosix(value) {
  return value.split(path.sep).join("/");
}

function fail(message) {
  console.error(message);
  process.exitCode = 1;
  process.exit();
}

if (!fs.existsSync(manifestPath)) {
  fail(`Missing manifest: ${manifestPath}`);
}

if (outDir === "/" || outDir === repoRoot) {
  fail(`Refusing unsafe output directory: ${outDir}`);
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const include = manifest.include ?? [];
const exclude = manifest.exclude ?? [];
const mergeFiles = new Set(manifest.merge ?? []);
const extraExclude = [
  /^\.claude\/skills\/[^/]+\/screenshots\//,
  /\.(png|jpg|jpeg|gif|webp|heic)$/i,
];
const textExt = new Set([
  ".cjs",
  ".js",
  ".json",
  ".md",
  ".mjs",
  ".py",
  ".sh",
  ".toml",
  ".ts",
  ".tsx",
  ".txt",
  ".yaml",
  ".yml",
]);

function escapeRegex(char) {
  return char.replace(/[|\\{}()[\]^$+?.]/g, "\\$&");
}

function globToRegex(glob) {
  let out = "^";
  for (let i = 0; i < glob.length; i += 1) {
    const char = glob[i];
    const next = glob[i + 1];
    if (char === "*" && next === "*") {
      out += ".*";
      i += 1;
    } else if (char === "*") {
      out += "[^/]*";
    } else if (char === "?") {
      out += "[^/]";
    } else {
      out += escapeRegex(char);
    }
  }
  return new RegExp(`${out}$`);
}

const includeRegexes = include.map(globToRegex);
const excludeRegexes = exclude.map(globToRegex);

function includeBase(glob) {
  const marker = glob.search(/[*?]/);
  const stable = marker === -1 ? glob : glob.slice(0, marker);
  const slash = stable.lastIndexOf("/");
  if (marker === -1) return glob;
  return slash === -1 ? "." : stable.slice(0, slash);
}

function walkFiles(absDir, out = []) {
  if (!fs.existsSync(absDir)) return out;
  for (const entry of fs.readdirSync(absDir, { withFileTypes: true })) {
    if (entry.name === dotGitDirName || entry.name === "node_modules") continue;
    const abs = path.join(absDir, entry.name);
    if (entry.isDirectory()) {
      walkFiles(abs, out);
    } else {
      out.push(abs);
    }
  }
  return out;
}

const candidateFiles = new Set();
for (const pattern of include) {
  const base = includeBase(pattern);
  const absBase = path.join(repoRoot, base);
  if (!fs.existsSync(absBase)) continue;
  const stat = fs.lstatSync(absBase);
  if (stat.isDirectory()) {
    for (const abs of walkFiles(absBase)) {
      candidateFiles.add(toPosix(path.relative(repoRoot, abs)));
    }
  } else {
    candidateFiles.add(toPosix(path.relative(repoRoot, absBase)));
  }
}

function isIncluded(rel) {
  return includeRegexes.some((regex) => regex.test(rel));
}

function isExcluded(rel) {
  return excludeRegexes.some((regex) => regex.test(rel)) || extraExclude.some((regex) => regex.test(rel));
}

const copiedFiles = [];
const skippedMergeFiles = [];

for (const rel of [...candidateFiles].sort()) {
  if (!isIncluded(rel) || isExcluded(rel)) continue;
  if (mergeFiles.has(rel)) {
    skippedMergeFiles.push(rel);
    continue;
  }
  copiedFiles.push(rel);
}

function ensureDir(abs) {
  fs.mkdirSync(abs, { recursive: true });
}

function writeFile(rel, body, generatedFiles) {
  const abs = path.join(outDir, rel);
  ensureDir(path.dirname(abs));
  fs.writeFileSync(abs, body);
  generatedFiles.push(rel);
}

function copyFile(rel) {
  const src = path.join(repoRoot, rel);
  const dest = path.join(outDir, rel);
  ensureDir(path.dirname(dest));
  const stat = fs.lstatSync(src);
  if (stat.isSymbolicLink()) {
    fs.symlinkSync(fs.readlinkSync(src), dest);
  } else if (textExt.has(path.extname(rel))) {
    fs.writeFileSync(dest, scrubText(fs.readFileSync(src, "utf8")));
  } else {
    fs.copyFileSync(src, dest);
  }
}

function token(...parts) {
  return parts.join("");
}

function scrubText(input) {
  return input
    .replaceAll(token("apps/", "flo", "wser-container"), "apps/source-container")
    .replaceAll(token("apps/", "flo", "wser"), "apps/source-app")
    .replaceAll(token("@", "flo", "wser", "/webapp"), "@benchmark/webapp")
    .replaceAll(token("FLO", "WSER"), "BENCHMARK")
    .replaceAll(token("Flo", "wser"), "BenchmarkProject")
    .replaceAll(token("flo", "wser"), "benchmark-project")
    .replaceAll(token("Open", "Claw"), "TaskRuntime")
    .replaceAll(token("Cloak", "Browser"), "TaskBrowser")
    .replaceAll(token("Supa", "base"), "hosted database");
}

function git(command) {
  try {
    return execSync(command, { cwd: repoRoot }).toString().trim();
  } catch {
    return "";
  }
}

const generatedFiles = [];
const sourceSha = git("git rev-parse HEAD");
const dirtyStatus = git("git status --short");
const dirtyFileCount = dirtyStatus.split("\n").filter(Boolean).length;

const genericClaude = `# CLAUDE.md

You are operating inside an isolated benchmark task repository.

Read AGENTS.md first for tool-specific notes, then read process/context/all-context.md and process/development-protocols/all-development-protocols.md before substantial work.

Use the bundled .claude/agents, .claude/skills, hooks, and process/development-protocols as the harness source of truth. Treat process/context/ as benchmark-local context only. Do not assume any source-project product context exists.

For benchmark tasks, route adaptively: use lightweight lanes for small fixes and fuller RIPER-5 planning, validation, and verification when the task scope warrants it. Do not pause for normal reversible gates when an autopilot benchmark instruction grants standing consent. Pause only for irreversible or outward-facing actions.
`;

const genericAgents = `# AGENTS.md - Benchmark Harness Adapter

CLAUDE.md is the source of truth for workflow behavior in this benchmark task.

Codex-specific notes:
- Skills live in .agents/skills, symlinked to .claude/skills.
- Agent identity lives in .claude/agents/*.md and .codex/agents/*.toml.
- Durable task knowledge belongs in process/context/.
- This snapshot is benchmark-local and intentionally excludes source-project feature plans, product context, and general-plan history.
`;

const genericAllContext = `---
name: context:all-context
description: "Benchmark-local generic context router"
date: 11-06-26
metadata:
  node_type: memory
  type: context
---

# Benchmark Context

This repository is an isolated benchmark task environment. It contains only the task files plus the exported harness.

## Routing

| Task type | Load first | Then load |
|---|---|---|
| any substantial task | process/context/all-context.md | process/development-protocols/all-development-protocols.md |
| test planning or verification | process/context/tests/all-tests.md | task-local test files |

## Rules

- Discover the task repository from the filesystem.
- Do not assume source-project-specific context.
- Create any task-specific plans under process/general-plans/active/ when the harness decides a plan is warranted.
`;

const genericAllTests = `---
name: context:all-tests
description: "Benchmark-local generic test router"
date: 11-06-26
metadata:
  node_type: memory
  type: context
---

# Benchmark Tests

Use task-local test files, package scripts, and README instructions as the authority. Prefer the smallest command that proves the requested behavior, then broaden only when risk warrants it.
`;

function genericContextStub(rel) {
  const slug = path.basename(rel, path.extname(rel));
  return `---
name: context:${slug}
description: "Benchmark-local compatibility stub for ${rel}"
date: 11-06-26
metadata:
  node_type: memory
  type: context
---

# Benchmark Context Stub

This file is generated so bundled harness guidance can resolve its documented context path in an isolated benchmark snapshot.

Use task-local files, benchmark instructions, and process/context/all-context.md as the authority. Do not assume source-project-specific context.
`;
}

const benchmarkProfile = `# Benchmark Harness Profile

Use this profile when the exported harness snapshot is injected into an isolated terminal benchmark task.

Instruction prepend:

\`\`\`text
ENTER AUTOPILOT MODE for this isolated benchmark task.

Use the local harness files already present in this repository. Treat the benchmark task instructions as the user request. Work autonomously until the task is solved or a hard stop is reached.

Autonomy boundaries:
- Standing consent is granted for reversible local file edits, local commands, local tests, and task-local planning artifacts.
- Do not pause for normal SPEC, PLAN, VALIDATE, or EXECUTE gates.
- Do pause before external network spend, credential mutation, publishing, destructive cleanup outside the task workspace, or any leaderboard submission.

Routing expectation:
- Use lightweight routing for small bounded fixes.
- Use fuller RIPER-5 planning, validation, and verification when task scope warrants it.
- Verify before declaring completion.
\`\`\`
`;

const harborAgentInit = `"""Benchmark harness custom agent package for Harbor."""
`;

const harborAgent = `"""Harbor custom agent scaffold for benchmark-harness snapshots.

This module is generated into the exported snapshot. It is not executed by the
exporter; the first live Harbor run remains an explicit hard stop.
"""

from __future__ import annotations

from pathlib import Path

from harbor.agents.installed.claude_code import ClaudeCode
from harbor.agents.installed.codex import Codex
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class BenchmarkHarnessCodexAgent(Codex):
    """Codex wrapper that uploads the exported harness snapshot.

    The wrapper keeps the benchmark task working directory as the run cwd and
    exposes the harness under /installed-agent/benchmark-harness. Harbor's
    built-in Codex agent still owns Codex CLI install, auth injection, model
    selection, and trajectory capture.
    """

    @staticmethod
    def name() -> str:
        return "benchmark-harness-codex"

    def version(self) -> str | None:
        return "snapshot-local"

    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        snapshot_root = Path(__file__).resolve().parents[1]
        await environment.upload_dir(snapshot_root, "/installed-agent/benchmark-harness")
        await self.exec_as_agent(
            environment,
            command="test -f /installed-agent/benchmark-harness/benchmark-profile.md",
        )

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        full_instruction = (
            "Use the benchmark harness snapshot at /installed-agent/benchmark-harness. "
            "First read /installed-agent/benchmark-harness/benchmark-profile.md and follow it.\\n\\n"
            f"Task instruction:\\n{instruction}"
        )
        await super().run(full_instruction, environment, context)


class BenchmarkHarnessClaudeCodeAgent(ClaudeCode):
    """Claude Code wrapper that uploads the exported harness snapshot.

    The wrapper keeps the benchmark task working directory as the run cwd and
    exposes the harness under /installed-agent/benchmark-harness. Harbor's
    built-in ClaudeCode agent still owns Claude Code CLI install, OAuth/API-key
    auth injection, model selection, and trajectory capture.
    """

    @staticmethod
    def name() -> str:
        return "benchmark-harness-claude-code"

    def version(self) -> str | None:
        return "snapshot-local"

    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        snapshot_root = Path(__file__).resolve().parents[1]
        await environment.upload_dir(snapshot_root, "/installed-agent/benchmark-harness")
        await self.exec_as_agent(
            environment,
            command="test -f /installed-agent/benchmark-harness/benchmark-profile.md",
        )

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        full_instruction = (
            "Use the benchmark harness snapshot at /installed-agent/benchmark-harness. "
            "First read /installed-agent/benchmark-harness/benchmark-profile.md and follow it.\\n\\n"
            f"Task instruction:\\n{instruction}"
        )
        await super().run(full_instruction, environment, context)


BenchmarkHarnessAgent = BenchmarkHarnessCodexAgent
`;

const harborRunbook = `# Harbor Runbook

This snapshot includes a generated custom Codex installed-agent for Harbor:

\`\`\`bash
harbor run \\
  -d terminal-bench/terminal-bench-2 \\
  --agent-import-path harbor_agents.benchmark_harness_agent:BenchmarkHarnessCodexAgent \\
  -m openai/gpt-5.5 \\
  -k 5 \\
  -n 4
\`\`\`

Live execution policy:

- Do not run the command above until the operator approves the first live benchmark spend.
- Use the same dataset, task subset, model, concurrency, timeout, and local machine state for the benchmark-harness run and the raw Codex baseline.
- Use raw Codex as the local baseline:

\`\`\`bash
harbor run -d terminal-bench/terminal-bench-2 -a codex -m openai/gpt-5.5 -k 5 -n 4
\`\`\`

Local no-spend checks:

\`\`\`bash
python -m py_compile harbor_agents/benchmark_harness_agent.py
test -f benchmark-profile.md
test -f benchmark-kit-manifest.json
test -L .agents/skills
\`\`\`
`;

if (!dryRun) {
  if (fs.existsSync(outDir)) {
    fail(`Output directory already exists: ${outDir}`);
  }
  ensureDir(outDir);
  for (const rel of copiedFiles) copyFile(rel);
  writeFile("CLAUDE.md", genericClaude, generatedFiles);
  writeFile("AGENTS.md", genericAgents, generatedFiles);
  writeFile("process/context/all-context.md", genericAllContext, generatedFiles);
  writeFile("process/context/tests/all-tests.md", genericAllTests, generatedFiles);
  for (const rel of [
    "process/context/tests.md",
    "process/context/tests/container-e2e.md",
    "process/context/container/all-container.md",
    "process/context/tests/browser-automation.md",
    "process/context/tests/browser-automation-live-rounds.md",
    "process/context/ui/all-ui.md",
    "process/context/ui/design.md",
    "process/context/infra/all-infra.md",
    "process/context/skills/all-skills.md",
    "process/context/skills/benchmark-project-skills.md",
    "process/context/skills/skill-apps.md",
    "process/context/workflows/all-workflows.md",
    "process/context/workflows/cf-workflows.md",
    "process/context/planning/all-planning.md",
  ]) {
    writeFile(rel, genericContextStub(rel), generatedFiles);
  }
  writeFile("process/context/generated-skills-catalog.json", "{}\n", generatedFiles);
  writeFile("benchmark-profile.md", benchmarkProfile, generatedFiles);
  writeFile("harbor_agents/__init__.py", harborAgentInit, generatedFiles);
  writeFile("harbor_agents/benchmark_harness_agent.py", harborAgent, generatedFiles);
  writeFile("harbor-runbook.md", harborRunbook, generatedFiles);

  for (const rel of [
    "process/general-plans/active/.keep",
    "process/general-plans/backlog/.keep",
    "process/general-plans/completed/.keep",
    "process/features/.keep",
  ]) {
    writeFile(rel, "", generatedFiles);
  }

  const symlinkTarget = "../.claude/skills";
  const symlinkPath = path.join(outDir, ".agents/skills");
  ensureDir(path.dirname(symlinkPath));
  fs.symlinkSync(symlinkTarget, symlinkPath);
  generatedFiles.push(".agents/skills");

  const generatedFilesWithManifest = [...generatedFiles, "benchmark-kit-manifest.json"];
  const snapshot = {
    generatedAt: new Date().toISOString(),
    sourceRepo: "source-repo",
    sourceSha,
    dirty: dirtyStatus.length > 0,
    dirtyFileCount,
    manifestVersion: manifest.version,
    copiedCount: copiedFiles.length,
    generatedCount: generatedFilesWithManifest.length,
    copiedFiles,
    generatedFiles: generatedFilesWithManifest,
    skippedMergeFiles,
    notes: [
      "CLAUDE.md and AGENTS.md are generated benchmark-safe files, not verbatim copies from the source repo.",
      "process/context is generated as a generic benchmark scaffold.",
      "Live Harbor or Terminal-Bench execution is intentionally outside this exporter.",
    ],
  };
  writeFile("benchmark-kit-manifest.json", `${JSON.stringify(snapshot, null, 2)}\n`, generatedFiles);
}

const result = {
  dryRun,
  outDir,
  sourceSha,
  dirty: dirtyStatus.length > 0,
  dirtyFileCount,
  copiedCount: copiedFiles.length,
  generatedCount: dryRun ? 0 : generatedFiles.length,
  skippedMergeFiles,
  copiedFiles,
};

console.log(JSON.stringify(result, null, 2));
