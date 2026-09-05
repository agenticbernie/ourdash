#!/usr/bin/env node
// Auto-discovery for vc-context-discovery.
// Lists nested files under context/protocol/feature/plan roots and extracts ONLY
// the leading YAML frontmatter block of each .md file (no whole-file parsing).
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const root = execSync("git rev-parse --show-toplevel").toString().trim();

// --- arg parsing -----------------------------------------------------------
const args = process.argv.slice(2);
let feature = null;
let asJson = false;
let matchQuery = null;
let emitRouting = false;
let checkRouting = false;
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--json") asJson = true;
  else if (a === "--emit-routing") emitRouting = true;
  else if (a === "--check-routing") checkRouting = true;
  else if (a === "--match") {
    matchQuery = args[++i];
    if (!matchQuery) {
      console.error("--match requires a value");
      process.exit(2);
    }
  } else if (a.startsWith("--match=")) {
    matchQuery = a.slice("--match=".length);
  } else if (a === "--feature") {
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

// Read only the first ~60 lines and extract a leading `---` frontmatter block.
// Minimal line parser: top-level `key: value` plus one level of `metadata:` nesting.
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
  if (end === -1) return null; // no closing delimiter within window

  const top = {};
  const metadata = {};
  let inMetadata = false;
  for (let i = 1; i < end; i++) {
    const line = head[i];
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

  // keywords: comma-separated scalar -> array of lowercase terms
  const keywords = (top.keywords ?? "")
    .split(",")
    .map((k) => k.trim().toLowerCase())
    .filter(Boolean);
  // related: inline YAML list `[context:a, context:b]` -> array of slug strings
  const related = (top.related ?? "")
    .replace(/^\[|\]$/g, "")
    .split(",")
    .map((s) => s.trim().replace(/^["']|["']$/g, ""))
    .filter(Boolean);

  return {
    name: top.name ?? null,
    description: top.description ?? null,
    keywords,
    related,
    date: top.date ?? null,
    type: top.type ?? metadata.type ?? null,
    feature: top.feature ?? metadata.feature ?? null,
    phase: top.phase ?? metadata.phase ?? null,
    readOrder: metadata.read_order ?? null,
    required: metadata.required === "true",
    readWhen: metadata.read_when ?? null,
    hasFrontmatter: true,
  };
}

function describe(relPath) {
  const fm = relPath.endsWith(".md") ? readFrontmatter(relPath) : null;
  return { path: relPath, fm };
}

// --- collect ---------------------------------------------------------------
const contextFiles = walk("process/context").map(describe);
const protocolFiles = walk("process/development-protocols").map(describe);
const generalPlanFiles = walk("process/general-plans/active").map(describe);

let featureFiles = [];
if (feature) {
  featureFiles = walk(`process/features/${feature}`).map(describe);
}

// --- keyword matching + routing generation ---------------------------------
const ROUTER = "process/context/all-context.md";
const ROUTING_START = "<!-- GENERATED:routing -->";
const ROUTING_END = "<!-- /GENERATED:routing -->";

function contextDocsWithFm() {
  return contextFiles.filter((d) => d.path.endsWith(".md") && d.fm && d.fm.hasFrontmatter);
}

function groupOf(relPath) {
  // process/context/{group}/all-{group}.md -> {group}; root all-context.md -> null
  const rest = relPath.replace(/^process\/context\//, "");
  const parts = rest.split(path.sep);
  return parts.length > 1 ? parts[0] : null;
}

function groupEntrypoints() {
  return contextDocsWithFm()
    .filter((d) => /(^|\/)all-[^/]+\.md$/.test(d.path) && groupOf(d.path))
    .sort((a, b) => a.path.localeCompare(b.path));
}

function buildRoutingBlock() {
  const eps = groupEntrypoints();
  const rootRows = [
    "| `process/context/all-context.md` | any substantial planning, research, review, or implementation task |",
    ...eps.map((d) => `| \`${d.path}\` | ${d.fm.readWhen || d.fm.description || "—"} |`),
  ];
  const groupRows = eps.length
    ? eps.map((d) => `| \`${groupOf(d.path)}/\` | \`${d.path}\` | ${d.fm.description || "—"} |`)
    : ["| (no groups yet — populated during STUDY phase, then regenerated by `--emit-routing`) | | |"];

  return [
    ROUTING_START,
    "| File | Read when |",
    "|---|---|",
    ...rootRows,
    "",
    "## Current Context Groups",
    "",
    "| Group | Entry point | Scope |",
    "|---|---|---|",
    ...groupRows,
    ROUTING_END,
  ].join("\n");
}

function currentRoutingBlock(text) {
  const s = text.indexOf(ROUTING_START);
  const e = text.indexOf(ROUTING_END);
  if (s === -1 || e === -1 || e < s) return null;
  return text.slice(s, e + ROUTING_END.length);
}

if (emitRouting || checkRouting) {
  if (!fs.existsSync(path.join(root, ROUTER))) {
    process.stderr.write(`[bare-kit mode] ${ROUTER} absent — nothing to ${emitRouting ? "emit" : "check"}.\n`);
    process.exit(0);
  }
  const text = fs.readFileSync(path.join(root, ROUTER), "utf8");
  const existing = currentRoutingBlock(text);
  if (existing === null) {
    console.error(`${ROUTER} has no <!-- GENERATED:routing --> markers; cannot manage routing block.`);
    process.exit(2);
  }
  const fresh = buildRoutingBlock();
  if (checkRouting) {
    if (existing.trim() !== fresh.trim()) {
      console.error(`${ROUTER} routing block is STALE — run discover-context.mjs --emit-routing to rebuild.`);
      process.exit(1);
    }
    console.log(`${ROUTER} routing block is in sync.`);
    process.exit(0);
  }
  fs.writeFileSync(path.join(root, ROUTER), text.replace(existing, fresh));
  console.log(`Rewrote routing block in ${ROUTER} (${groupEntrypoints().length} group entrypoint(s)).`);
  process.exit(0);
}

if (matchQuery) {
  const tokens = (matchQuery.toLowerCase().match(/[a-z0-9]+/g) || []).filter((t) => t.length > 2);
  const scored = contextDocsWithFm()
    .map((d) => {
      const kws = d.fm.keywords || [];
      let score = 0;
      const hits = [];
      for (const t of tokens) {
        if (kws.some((k) => k === t || k.includes(t) || t.includes(k))) { score += 1; hits.push(t); }
      }
      return { d, score, hits };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || a.d.path.localeCompare(b.d.path));

  // append related siblings of the top hits (deduped, not already matched)
  const matchedPaths = new Set(scored.map((x) => x.d.path));
  const byName = new Map(contextDocsWithFm().map((d) => [d.fm.name, d]));
  const siblings = [];
  for (const { d } of scored) {
    for (const rel of d.fm.related || []) {
      const sib = byName.get(rel);
      if (sib && !matchedPaths.has(sib.path)) {
        matchedPaths.add(sib.path);
        siblings.push({ from: d.fm.name, sib });
      }
    }
  }

  if (asJson) {
    console.log(JSON.stringify({
      query: matchQuery,
      matches: scored.map((x) => ({ path: x.d.path, score: x.score, hits: x.hits, name: x.d.fm.name, description: x.d.fm.description })),
      related: siblings.map((s) => ({ path: s.sib.path, name: s.sib.fm.name, via: s.from })),
    }, null, 2));
    process.exit(0);
  }

  const out = [`Keyword matches for: "${matchQuery}" (read in order)`];
  if (scored.length === 0) out.push("  (no keyword matches — fall back to all-context.md routing table)");
  for (const x of scored) out.push(`  [${x.score}] ${x.d.path} — ${x.d.fm.description ?? "—"}  (hits: ${x.hits.join(", ")})`);
  if (siblings.length) {
    out.push("");
    out.push("Related siblings (load alongside the above):");
    for (const s of siblings) out.push(`  ${s.sib.path} — ${s.sib.fm.description ?? "—"}  (related via ${s.from})`);
  }
  console.log(out.join("\n"));
  process.exit(0);
}

// --- output ----------------------------------------------------------------
function line(d) {
  if (d.fm && (d.fm.name || d.fm.description)) {
    return `  ${d.path} (name: ${d.fm.name ?? "—"} — description: ${d.fm.description ?? "—"})`;
  }
  return `  ${d.path}`;
}

// Richer renderer for protocol files: name — description — read_when, with a [REQUIRED] tag.
function protocolLine(d) {
  if (!(d.fm && (d.fm.name || d.fm.description))) return `  ${d.path}`;
  const tag = d.fm.required ? "[REQUIRED] " : "";
  return `  ${tag}${d.path} (name: ${d.fm.name ?? "—"} — description: ${d.fm.description ?? "—"} — read_when: ${d.fm.readWhen ?? "—"})`;
}

// Sort protocols: required first, then by numeric read_order, then by path.
function sortedProtocols(list) {
  return [...list].sort((a, b) => {
    const ar = a.fm?.required ? 0 : 1;
    const br = b.fm?.required ? 0 : 1;
    if (ar !== br) return ar - br;
    const ao = Number(a.fm?.readOrder ?? 99);
    const bo = Number(b.fm?.readOrder ?? 99);
    if (ao !== bo) return ao - bo;
    return a.path.localeCompare(b.path);
  });
}

function withFm(list) {
  return list.filter((d) => d.fm && (d.fm.name || d.fm.description));
}
function withoutFm(list) {
  return list.filter((d) => !(d.fm && (d.fm.name || d.fm.description)));
}

if (asJson) {
  const out = {
    feature: feature ?? null,
    context: contextFiles.map((d) => ({ path: d.path, ...(d.fm ?? { hasFrontmatter: false }) })),
    protocols: protocolFiles.map((d) => ({ path: d.path, ...(d.fm ?? { hasFrontmatter: false }) })),
    features: featureFiles.map((d) => ({ path: d.path, ...(d.fm ?? { hasFrontmatter: false }) })),
    generalPlansActive: generalPlanFiles.map((d) => ({ path: d.path, ...(d.fm ?? { hasFrontmatter: false }) })),
  };
  console.log(JSON.stringify(out, null, 2));
  process.exit(0);
}

const lines = [];
lines.push("Context files with frontmatter:");
for (const d of withFm(contextFiles)) lines.push(line(d));

lines.push("");
lines.push("Protocol files (required first, then read order):");
for (const d of sortedProtocols(protocolFiles)) lines.push(protocolLine(d));

if (feature) {
  lines.push("");
  lines.push(`Feature files (by subfolder) — ${feature}:`);
  // group by the subfolder directly under the feature root (active/completed/backlog/reports/references)
  const base = `process/features/${feature}/`;
  const groups = new Map();
  for (const d of featureFiles) {
    const rest = d.path.startsWith(base) ? d.path.slice(base.length) : d.path;
    const sub = rest.split(path.sep)[0] || ".";
    if (!groups.has(sub)) groups.set(sub, []);
    groups.get(sub).push(d);
  }
  for (const sub of [...groups.keys()].sort()) {
    lines.push(`  [${sub}/]`);
    for (const d of groups.get(sub)) lines.push(line(d));
  }
}

lines.push("");
lines.push("Active general plans:");
for (const d of generalPlanFiles) lines.push(line(d));

lines.push("");
lines.push("Files without frontmatter (path only):");
const noFm = [
  ...withoutFm(contextFiles),
  ...withoutFm(protocolFiles),
  ...withoutFm(featureFiles),
  ...withoutFm(generalPlanFiles),
];
for (const d of noFm) lines.push(`  ${d.path}`);

console.log(lines.join("\n"));
process.exit(0);
