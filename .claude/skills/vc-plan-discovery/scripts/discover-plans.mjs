#!/usr/bin/env node
// Auto-discovery for vc-plan-discovery.
// Scans plan roots per the SKILL scope rules and extracts ONLY the leading YAML
// frontmatter block of each .md file (no whole-file parsing). Self-contained:
// the frontmatter parser is duplicated here so the skill is independently portable.
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const root = execSync("git rev-parse --show-toplevel").toString().trim();

// --- arg parsing -----------------------------------------------------------
const args = process.argv.slice(2);
let feature = null;
let asJson = false;
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--json") asJson = true;
  else if (a === "--feature") {
    feature = args[++i];
    if (!feature) {
      console.error("--feature requires a value");
      process.exit(2);
    }
  } else if (a.startsWith("--feature=")) {
    feature = a.slice("--feature=".length);
  } else {
    console.error(`unknown flag: ${a}`);
    process.exit(2);
  }
}

// --- helpers ---------------------------------------------------------------
function walk(dir, out = []) {
  const abs = path.join(root, dir);
  if (!fs.existsSync(abs)) return out; // never throw on missing root
  for (const entry of fs.readdirSync(abs, { withFileTypes: true })) {
    const rel = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(rel, out);
    else out.push(rel);
  }
  return out;
}

function stripQuotes(v) {
  const t = v.trim();
  if (
    (t.startsWith('"') && t.endsWith('"')) ||
    (t.startsWith("'") && t.endsWith("'"))
  ) {
    return t.slice(1, -1);
  }
  return t;
}

function readFrontmatter(relPath) {
  let head;
  try {
    const buf = fs.readFileSync(path.join(root, relPath), "utf8");
    head = buf.split("\n", 80);
  } catch {
    return null;
  }
  if (head.length === 0 || head[0].trim() !== "---") return null;

  let end = -1;
  for (let i = 1; i < head.length; i++) {
    if (head[i].trim() === "---") {
      end = i;
      break;
    }
  }
  if (end === -1) return null;

  const top = {};
  const metadata = {};
  let inMetadata = false;
  for (let i = 1; i < end; i++) {
    const lineStr = head[i];
    if (lineStr.trim() === "" || lineStr.trim().startsWith("#")) continue;
    const indent = lineStr.length - lineStr.trimStart().length;
    const m = lineStr.trim().match(/^([A-Za-z0-9_-]+):(.*)$/);
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

  return {
    name: top.name ?? null,
    description: top.description ?? null,
    date: top.date ?? null,
    type: top.type ?? metadata.type ?? null,
    feature: top.feature ?? metadata.feature ?? null,
    phase: top.phase ?? metadata.phase ?? null,
    hasFrontmatter: true,
  };
}

function describe(relPath) {
  const fm = relPath.endsWith(".md") ? readFrontmatter(relPath) : null;
  return { path: relPath, fm };
}

// --- classify into buckets -------------------------------------------------
// Bucket by path segment. active/backlog/completed by folder; reports/references
// by either a sibling legacy dir OR a _REPORT_/_REF_ co-located filename.
function bucketOf(relPath) {
  const base = path.basename(relPath);
  if (/\/reports\//.test(relPath) || /_REPORT_/.test(base)) return "reports";
  if (/\/references\//.test(relPath) || /_REF_/.test(base)) return "references";
  if (/\/active\//.test(relPath)) return "active";
  if (/\/backlog\//.test(relPath)) return "backlog";
  if (/\/completed\//.test(relPath)) return "completed";
  return null;
}

const buckets = { active: [], backlog: [], completed: [], reports: [], references: [] };
const seen = new Set();

function add(relPath) {
  if (seen.has(relPath)) return;
  if (!relPath.endsWith(".md")) return;
  const b = bucketOf(relPath);
  if (!b) return;
  seen.add(relPath);
  buckets[b].push(describe(relPath));
}

// --- collect per scope rules ----------------------------------------------
// Same feature: ALL subfolders (active/backlog/completed + legacy reports/references).
if (feature) {
  for (const f of walk(`process/features/${feature}`)) add(f);
}

// Other feature folders: active/ only.
const featuresRoot = path.join(root, "process/features");
if (fs.existsSync(featuresRoot)) {
  for (const entry of fs.readdirSync(featuresRoot, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    if (entry.name === feature) continue;
    for (const f of walk(`process/features/${entry.name}/active`)) add(f);
  }
}

// general-plans/active: always.
for (const f of walk("process/general-plans/active")) add(f);

// --- output ----------------------------------------------------------------
if (asJson) {
  const out = { feature: feature ?? null };
  for (const k of Object.keys(buckets)) {
    out[k] = buckets[k].map((d) => ({ path: d.path, ...(d.fm ?? { hasFrontmatter: false }) }));
  }
  console.log(JSON.stringify(out, null, 2));
  process.exit(0);
}

function entry(d) {
  const name = d.fm?.name ?? path.basename(d.path);
  const desc = d.fm?.description ?? "(no frontmatter)";
  return `- [${name}]: ${desc} (${d.path})`;
}

const lines = [];
const sections = [
  ["Active Plans", "active"],
  ["Backlog", "backlog"],
  ["Completed", "completed"],
  ["Reports", "reports"],
  ["References", "references"],
];
for (const [title, key] of sections) {
  lines.push(`### ${title}`);
  for (const d of buckets[key]) lines.push(entry(d));
  lines.push("");
}
lines.push(
  `Found ${buckets.active.length} active, ${buckets.backlog.length} backlog, ` +
    `${buckets.completed.length} completed, ${buckets.reports.length} reports, ` +
    `${buckets.references.length} references`,
);

console.log(lines.join("\n"));
process.exit(0);
