#!/usr/bin/env node
// Enforces discovery frontmatter on every process/development-protocols/**/*.md file.
// Recursive + nested-metadata-aware: unlike validate-context-discovery.mjs's flat
// parseFrontmatter, this reads one level of `metadata:` nesting so metadata.type /
// read_order / required / read_when are actually checked.
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const root = execSync("git rev-parse --show-toplevel").toString().trim();
const failures = [];
const warnings = [];

// Intentional exclusion: note.md is a raw Q&A scratch dump (no H1, no stable identity).
// It is NOT a routable protocol doc and is deliberately exempt from frontmatter.
const EXCLUDE = new Set(["process/development-protocols/note.md"]);

function walk(dir, out = []) {
  const abs = path.join(root, dir);
  if (!fs.existsSync(abs)) return out;
  for (const entry of fs.readdirSync(abs, { withFileTypes: true })) {
    const rel = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(rel, out);
    else if (rel.endsWith(".md")) out.push(rel);
  }
  return out;
}

function stripQuotes(v) {
  const t = v.trim();
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1);
  }
  return t;
}

// Nested-aware leading-frontmatter parser. Returns { top, metadata } or null.
function parseFrontmatter(relPath) {
  const buf = fs.readFileSync(path.join(root, relPath), "utf8");
  const lines = buf.split("\n");
  if (lines[0].trim() !== "---") return null;
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) return null;

  const top = {};
  const metadata = {};
  let inMetadata = false;
  for (let i = 1; i < end; i++) {
    const line = lines[i];
    if (line.trim() === "" || line.trim().startsWith("#")) continue;
    const indent = line.length - line.trimStart().length;
    const m = line.trim().match(/^([A-Za-z0-9_-]+):(.*)$/);
    if (!m) continue;
    const key = m[1];
    const rawVal = m[2].trim();
    if (key === "metadata" && rawVal === "") {
      inMetadata = true;
      continue;
    }
    if (inMetadata && indent >= 2) {
      metadata[key] = stripQuotes(rawVal);
    } else {
      inMetadata = false;
      if (rawVal !== "") top[key] = stripQuotes(rawVal);
    }
  }
  return { top, metadata };
}

const all = walk("process/development-protocols");
const covered = all.filter((f) => !EXCLUDE.has(f));
let checked = 0;

for (const file of covered) {
  const fm = parseFrontmatter(file);
  if (!fm) {
    failures.push(`${file} is missing leading YAML frontmatter`);
    continue;
  }
  checked += 1;
  const { top, metadata } = fm;
  if (!top.name) failures.push(`${file} frontmatter missing name`);
  else if (!top.name.startsWith("protocol:")) {
    failures.push(`${file} name "${top.name}" must start with "protocol:"`);
  }
  if (!top.description) failures.push(`${file} frontmatter missing description`);
  if (!top.date) failures.push(`${file} frontmatter missing date`);
  if (metadata.type !== "protocol") {
    failures.push(`${file} metadata.type is "${metadata.type ?? "missing"}", expected "protocol"`);
  }
  if (metadata.node_type === undefined) failures.push(`${file} metadata.node_type missing`);
  if (metadata.read_order === undefined) failures.push(`${file} metadata.read_order missing`);
  else if (!/^\d+$/.test(metadata.read_order)) {
    failures.push(`${file} metadata.read_order "${metadata.read_order}" is not an integer`);
  }
  if (metadata.required === undefined) failures.push(`${file} metadata.required missing`);
  else if (metadata.required !== "true" && metadata.required !== "false") {
    failures.push(`${file} metadata.required "${metadata.required}" must be true|false`);
  }
  if (!metadata.read_when) failures.push(`${file} metadata.read_when missing`);
}

const result = {
  checkedProtocolDocs: checked,
  excluded: [...EXCLUDE],
  warnings,
  failures,
};

console.log(JSON.stringify(result, null, 2));

if (failures.length > 0) {
  process.exitCode = 1;
}
