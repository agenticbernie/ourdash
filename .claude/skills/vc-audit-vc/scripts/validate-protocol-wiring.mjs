#!/usr/bin/env node
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
  return fs.existsSync(path.join(root, relPath));
}

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), "utf8");
}

// --- Recursive walk (no SKIP_DIR needed — no node_modules in protocol dir) ---

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

// --- 1. List all .md files in process/development-protocols/ (recursive) ---

const protocolDir = "process/development-protocols";
const protocolFiles = [];

if (!fs.existsSync(path.join(root, protocolDir))) {
  fail(`${protocolDir}/ directory does not exist`);
} else {
  protocolFiles.push(...walk(protocolDir, (rel) => rel.endsWith(".md")));
}

// --- 2. For each agent, scan body for references to protocol files ---

const agentsDir = path.join(root, ".claude/agents");
const checkedAgents = [];

if (fs.existsSync(agentsDir)) {
  for (const entry of fs.readdirSync(agentsDir, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
    const agentFile = `.claude/agents/${entry.name}`;
    const text = read(agentFile);
    checkedAgents.push(entry.name);

    // Find all process/development-protocols/ references in agent body
    // Updated regex supports subdir paths like vc-system-behavior/06-innovate.md
    const refs = [...text.matchAll(/process\/development-protocols\/((?:[a-z0-9_-]+\/)*[a-z0-9_-]+\.md)/g)];
    for (const ref of refs) {
      const referencedFile = ref[1];
      const fullRef = `${protocolDir}/${referencedFile}`;
      if (!protocolFiles.includes(fullRef)) {
        warn(`${agentFile} references ${fullRef} which does not exist on disk`);
      }
    }
  }
}

// --- 3. Check that all-development-protocols.md lists all sibling protocol files ---

const allProtocolsFile = `${protocolDir}/all-development-protocols.md`;
if (exists(allProtocolsFile)) {
  const allProtocolsText = read(allProtocolsFile);
  for (const file of protocolFiles) {
    const basename = path.basename(file);
    if (basename === "all-development-protocols.md") continue;

    // Files in subdirectories are listed as a group via the subdir folder reference.
    // Check: if any parent path segment of this file is referenced in all-development-protocols.md
    // (e.g. vc-system-behavior/01-overview.md is covered by the `vc-system-behavior/` folder entry).
    const relToProtocolDir = path.relative(protocolDir, path.join(protocolDir, path.relative(protocolDir, path.join(root, protocolDir, path.relative(`${protocolDir}/`, file)))));
    const segments = file.replace(`${protocolDir}/`, "").split(path.sep);
    if (segments.length > 1) {
      // Subdir file: covered if the subdir name appears in the router doc
      const subdirRef = segments[0] + "/";
      if (!allProtocolsText.includes(subdirRef)) {
        fail(`${allProtocolsFile} does not reference subdir: ${subdirRef} (contains ${file})`);
      }
      continue;
    }

    // Root-level file: must appear by basename
    if (!allProtocolsText.includes(basename)) {
      fail(`${allProtocolsFile} does not list protocol file: ${basename} (path: ${file})`);
    }
  }
} else {
  fail(`${allProtocolsFile} does not exist`);
}

// --- 4. Check update-process-agent.md Category 5b scan list ---

const updateProcessAgent = ".claude/agents/vc-update-process-agent.md";
if (exists(updateProcessAgent)) {
  const text = read(updateProcessAgent);

  // Check that README.md is in the scan list
  if (!text.includes("README.md")) {
    warn(`${updateProcessAgent} Category 5b scan list does not include README.md`);
  }

  // Check that process/development-protocols/ is in the scan list
  if (!text.includes("process/development-protocols/")) {
    warn(`${updateProcessAgent} Category 5b scan list does not include process/development-protocols/`);
  }
} else {
  fail(`${updateProcessAgent} does not exist`);
}

const result = {
  checkedProtocols: protocolFiles.length,
  checkedAgents: checkedAgents.length,
  warnings,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
