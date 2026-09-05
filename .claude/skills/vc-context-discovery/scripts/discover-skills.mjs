#!/usr/bin/env node
// Auto-discovery for the VC skill registry.
// Reads process/context/generated-skills-catalog.json and prints every skill
// GROUPED BY layer (actor / contract / helper), each line: name — purpose — keywords.
// This replaces the formerly-inline Skill Registry table in CLAUDE.md.
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

let root;
try {
  root = execSync("git rev-parse --show-toplevel", { stdio: ["pipe", "pipe", "pipe"] }).toString().trim();
} catch {
  // Not a git repository — fall back to process.cwd() so the script still works.
  root = process.cwd();
}

const args = process.argv.slice(2);
let asJson = false;
for (const a of args) {
  if (a === "--json") asJson = true;
  else {
    console.error(`unknown flag: ${a}`);
    process.exit(2);
  }
}

const catalogPath = path.join(root, "process/context/generated-skills-catalog.json");
if (!fs.existsSync(catalogPath)) {
  console.error("generated-skills-catalog.json missing; run generate-skills-catalog.mjs --write");
  process.exit(1);
}
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));

// First sentence of the description = purpose.
function firstSentence(desc) {
  if (!desc) return "";
  const trimmed = desc.trim();
  const dot = trimmed.indexOf(". ");
  return dot === -1 ? trimmed.replace(/\.$/, "") : trimmed.slice(0, dot);
}

const byLayer = { actor: [], contract: [], helper: [], other: [] };
for (const s of catalog.skills) {
  const bucket = byLayer[s.layer] ? s.layer : "other";
  byLayer[bucket].push(s);
}
for (const k of Object.keys(byLayer)) {
  byLayer[k].sort((a, b) => a.name.localeCompare(b.name));
}

if (asJson) {
  const out = {
    skillCount: catalog.skillCount,
    layers: {
      actor: byLayer.actor.map(toEntry),
      contract: byLayer.contract.map(toEntry),
      helper: byLayer.helper.map(toEntry),
      ...(byLayer.other.length ? { other: byLayer.other.map(toEntry) } : {}),
    },
  };
  console.log(JSON.stringify(out, null, 2));
  process.exit(0);
}

function toEntry(s) {
  return { name: s.name, purpose: firstSentence(s.description), triggerKeywords: s.triggerKeywords, layer: s.layer };
}

function printGroup(title, list) {
  console.log(title);
  if (list.length === 0) {
    console.log("  (none)");
  } else {
    for (const s of list) {
      const kws = (s.triggerKeywords || []).join(", ");
      console.log(`  ${s.name} — ${firstSentence(s.description)} — keywords: ${kws}`);
    }
  }
  console.log("");
}

console.log(`VC Skill Registry — ${catalog.skillCount} skills (grouped by layer)`);
console.log("");
console.log("Actor agents (agents, not skills — see .claude/agents/):");
console.log("  (the RIPER-5 phase + specialist agents live in .claude/agents/, not .claude/skills/)");
console.log("");
printGroup("Contract skills (own a workflow artifact/contract):", byLayer.contract);
printGroup("Helper skills (improve how agents work, own no artifact):", byLayer.helper);
if (byLayer.other.length) {
  printGroup("Unclassified (missing/invalid layer — fix frontmatter):", byLayer.other);
}
