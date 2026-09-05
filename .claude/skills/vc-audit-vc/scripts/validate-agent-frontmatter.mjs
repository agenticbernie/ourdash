#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

let root;
try {
  root = execSync("git rev-parse --show-toplevel", {
    stdio: ["pipe", "pipe", "pipe"],
  })
    .toString()
    .trim();
} catch {
  root = process.cwd();
}

const strict = process.argv.includes("--strict");
const agentFlagIdx = process.argv.indexOf("--agent");
const singleAgentArg =
  agentFlagIdx !== -1 ? process.argv[agentFlagIdx + 1] : null;

const VALID_EFFORT_VALUES = new Set(["low", "medium", "high", "max"]);

const globalFailures = [];
const globalWarnings = [];
const checkedAgents = [];

function parseFrontmatter(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const block = match[1];
  const result = {};

  let currentKey = null;
  let currentListLines = null;

  for (const raw of block.split(/\r?\n/)) {
    // List item continuation
    const listItemMatch = raw.match(/^  - (.*)$/);
    if (listItemMatch && currentListLines !== null) {
      currentListLines.push(listItemMatch[1].trim());
      continue;
    }

    // Flush pending list
    if (currentKey !== null && currentListLines !== null) {
      result[currentKey] = currentListLines;
      currentKey = null;
      currentListLines = null;
    }

    // Inline list  key: [a, b]
    const inlineListMatch = raw.match(/^([A-Za-z0-9_-]+):\s*\[(.*)\]\s*$/);
    if (inlineListMatch) {
      const vals = inlineListMatch[2]
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean);
      result[inlineListMatch[1]] = vals;
      continue;
    }

    // Empty list  key: []
    const emptyListMatch = raw.match(/^([A-Za-z0-9_-]+):\s*\[\]\s*$/);
    if (emptyListMatch) {
      result[emptyListMatch[1]] = [];
      continue;
    }

    // Key with no value — start of a block list
    const blockKeyMatch = raw.match(/^([A-Za-z0-9_-]+):\s*$/);
    if (blockKeyMatch) {
      currentKey = blockKeyMatch[1];
      currentListLines = [];
      continue;
    }

    // Plain key: value
    const kvMatch = raw.match(/^([A-Za-z0-9_-]+):\s*(.+)$/);
    if (kvMatch) {
      result[kvMatch[1]] = kvMatch[2].trim().replace(/^["']|["']$/g, "");
      continue;
    }
  }

  // Flush trailing list
  if (currentKey !== null && currentListLines !== null) {
    result[currentKey] = currentListLines;
  }

  return result;
}

function checkAgent(agentPath) {
  const rel = path.relative(root, agentPath);
  const agentName = path.basename(agentPath, ".md");
  let agentFailures = 0;
  let agentWarnings = 0;

  let text;
  try {
    text = fs.readFileSync(agentPath, "utf8");
  } catch (e) {
    globalFailures.push(`${rel}: cannot read file — ${e.message}`);
    agentFailures++;
    checkedAgents.push({ path: rel, failures: agentFailures, warnings: agentWarnings });
    return;
  }

  const fm = parseFrontmatter(text);
  if (!fm) {
    globalFailures.push(`${rel}: no YAML frontmatter block found`);
    agentFailures++;
    checkedAgents.push({ path: rel, failures: agentFailures, warnings: agentWarnings });
    return;
  }

  // --- Check: effort ---
  if (!("effort" in fm)) {
    const msg = `${rel}: missing required field 'effort' (valid: low|medium|high|max)`;
    globalFailures.push(msg);
    agentFailures++;
  } else if (!VALID_EFFORT_VALUES.has(fm.effort)) {
    const msg = `${rel}: invalid effort value '${fm.effort}' (valid: low|medium|high|max)`;
    globalFailures.push(msg);
    agentFailures++;
  }

  // --- Check: skills ---
  if (!("skills" in fm)) {
    const msg = `${rel}: missing required field 'skills' (must be a non-empty list)`;
    globalFailures.push(msg);
    agentFailures++;
  } else {
    const skillsVal = fm.skills;
    if (!Array.isArray(skillsVal)) {
      const msg = `${rel}: 'skills' must be a list, got scalar value`;
      globalFailures.push(msg);
      agentFailures++;
    } else if (skillsVal.length === 0) {
      const msg = `${rel}: 'skills' list is empty — at minimum vc-context-discovery is expected`;
      if (strict) {
        globalFailures.push(msg);
        agentFailures++;
      } else {
        globalWarnings.push(msg);
        agentWarnings++;
      }
    }
  }

  // --- Check: disallowedTools ---
  if (!("disallowedTools" in fm)) {
    const msg = `${rel}: missing field 'disallowedTools' (should be a list, may be empty [])`;
    if (strict) {
      globalFailures.push(msg);
      agentFailures++;
    } else {
      globalWarnings.push(msg);
      agentWarnings++;
    }
  } else {
    const dtVal = fm.disallowedTools;
    if (!Array.isArray(dtVal)) {
      const msg = `${rel}: 'disallowedTools' must be a list, got scalar value`;
      globalFailures.push(msg);
      agentFailures++;
    }
  }

  // --- Check: hooks block ---
  // At P2 time: if hooks is present, it must reference agent-write-guard.mjs.
  // Absence of hooks is allowed (only WARN if strict — P3/P5 will strengthen this).
  // NOTE: the simple frontmatter parser cannot handle nested YAML blocks (hooks > PreToolUse > hooks > command).
  // Use a raw text scan of the frontmatter block instead to detect the agent-write-guard.mjs reference.
  if ("hooks" in fm) {
    const fmMatch = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    const fmRaw = fmMatch ? fmMatch[1] : "";
    if (!fmRaw.includes("agent-write-guard.mjs")) {
      const msg = `${rel}: 'hooks' block present but does not reference agent-write-guard.mjs`;
      globalFailures.push(msg);
      agentFailures++;
    }
  }
  // hooks absent: no action at P2 time (P5 will add the FAIL gate)

  checkedAgents.push({ path: rel, failures: agentFailures, warnings: agentWarnings });
}

// Determine agent file(s) to check
let agentFiles = [];

if (singleAgentArg) {
  // --agent can be an absolute path, relative to cwd, or a basename resolved from .claude/agents/
  const resolved = path.isAbsolute(singleAgentArg)
    ? singleAgentArg
    : path.resolve(process.cwd(), singleAgentArg);

  if (fs.existsSync(resolved)) {
    agentFiles = [resolved];
  } else {
    // Try resolving as a basename under .claude/agents/
    const inAgentsDir = path.join(root, ".claude/agents", singleAgentArg);
    const withExt = inAgentsDir.endsWith(".md") ? inAgentsDir : inAgentsDir + ".md";
    if (fs.existsSync(withExt)) {
      agentFiles = [withExt];
    } else {
      globalFailures.push(`--agent '${singleAgentArg}': file not found`);
    }
  }
} else {
  // Auto-discover all .md files under .claude/agents/
  const agentsDir = path.join(root, ".claude/agents");
  if (fs.existsSync(agentsDir)) {
    agentFiles = fs
      .readdirSync(agentsDir, { withFileTypes: true })
      .filter((e) => e.isFile() && e.name.endsWith(".md"))
      .map((e) => path.join(agentsDir, e.name))
      .sort();
  } else {
    globalFailures.push(`.claude/agents/ directory not found`);
  }
}

for (const agentPath of agentFiles) {
  checkAgent(agentPath);
}

const result = {
  checkedAgents,
  strict,
  warnings: globalWarnings,
  failures: globalFailures,
};

console.log(JSON.stringify(result, null, 2));

if (globalFailures.length > 0) {
  process.exitCode = 1;
}
