---
name: protocol:all-development-protocols
description: "Router for shared development protocols: read order and file roles for the protocol folder."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 0
  required: true
  read_when: "any substantial planning, research, validation, or implementation task — read first to route into the protocol folder"
---

# Development Protocols

Canonical shared workflow rules for this repository live here.

Use this folder for durable, repo-specific operating instructions that must stay aligned across Claude, Codex, and future agent systems. Keep tool-specific bootstrapping in `AGENTS.md` and `CLAUDE.md`, but keep the actual shared protocol content here.

## Read Order

1. `vc-system-behavior/` — complete system behavior reference, 12-file split (start here: `vc-system-behavior/01-overview.md` is the entrypoint). The legacy 186KB monolith is archived at `archive/vc-system-behavior-reference_ARCHIVED_09-06-26.md` (read-only history).
2. `orchestration.md`
3. `implementation-standards.md`
4. `plan-lifecycle.md`
5. `phase-programs.md`
6. `context-maintenance.md`
7. `communication-standards.md`
8. `vc-autoresearch-spec.md` (optional deep reference — read only when designing or deeply understanding the autoresearch gap-loop primitive)
9. `autopilot.md` — Autopilot Mode trigger phrases, consolidated clarification, provisional goal block format, mode markers, per-gate decision policy, hard stops, and deactivation rules. Read when: user says autopilot / autonomous mode / /autopilot trigger phrases, or when understanding orchestrator §Autonomy Mode integration.

## File Roles

- `vc-system-behavior/` (12-file split — canonical live reference; `01-overview.md` entrypoint)
  Authoritative end-to-end system behavior reference: every phase, every required skill (with
  REQUIRED vs CONDITIONAL labels), both test loops, /goal block format, phase program inner loop,
  infrastructure gaps (D1/H4/G1/I2), and before/after hardening table. Split into numbered files
  01-overview … 12-reference. The legacy single-file monolith is archived (read-only) at
  `archive/vc-system-behavior-reference_ARCHIVED_09-06-26.md`.
- `orchestration.md`
  Delegation rules, subagent status protocol, context isolation, feature-scope routing, intent clarification rules, validate gate and skip conditions, BLOCKED escalation path, two-tier fan-out escalation, and research-first rules for service-shaped work.
- `implementation-standards.md`
  Durable implementation standards, file-size guidance, error-handling preferences, quality gates, and commit hygiene.
- `plan-lifecycle.md`
  How plans are named, where they live, when to use feature folders, how EXECUTE handoff works, and how mixed legacy plan shapes should be treated.
- `phase-programs.md`
  How to run large multi-phase programs: umbrella plan, per-phase plan split, required 10-step loop, blocker handling, and foundation-vs-expansion boundaries.
- `context-maintenance.md`
  How `process/context/` is organized, when to create or split groups, how to keep `all-context.md` accurate, and how long-lived knowledge differs from feature plans.
- `communication-standards.md`
  How agents write human-facing output: answer-first (BLUF), plain language, TL;DR, no filler. Single source of truth for output style; CLAUDE.md, AGENTS.md, prose-producing agents, and report/spec/closeout/clarify skills point here instead of restating it.
- `vc-autoresearch-spec.md` (optional deep reference; `read_order: 7`, `required: false`)
  Deeper design reference for the `vc-autoresearch` loop primitive (the find-gaps → fix → repeat bookkeeper wired into PVL and EVL): canonical domain configs, iteration-report frontmatter schema, and TSV log format. The operative contract is `.claude/skills/vc-autoresearch/SKILL.md`; this file is the design rationale behind it.
- `autopilot.md`
  Autopilot Mode protocol: trigger phrase detection, consolidated clarification round (one-round rule),
  provisional goal block format (9 fields, ≤4000 chars, EXECUTE CONSENT required), [MODE: AUTOPILOT | X]
  marker syntax, [AUTOPILOT CONTEXT] injection schema for subagents, AUTOPILOT_ACTIVATED signal,
  V6/V7 (UPDATE) variant, per-gate autonomous decision policy, hard stops, deactivation rules, and
  phase-program interaction. Complements orchestration.md §Autonomy Mode.

- `references/program-goal-charter-template.md`
  Blank and filled Program Goal Charter template for phase-program umbrella plans. Read when building
  an umbrella plan or needing the compressed session-goal block format. Canonical content also mirrored
  at `.claude/skills/vc-generate-phase-program/references/program-goal-charter-template.md`.

Note: Protocol procedures for intent clarification, parallel strategy scoring, validate fan-out,
and closeout are now in the corresponding skills. See `process/context/all-context.md` skill
registry for skill names (`vc-intent-clarify`, `vc-agent-strategy-compare`, `vc-validate-findings`,
`vc-generate-closeout`, `vc-risk-evidence-pack`, `vc-generate-phase-program`).

## Maintenance Rules

- Update these files first when shared workflow behavior changes.
- When `AGENTS.md`, `CLAUDE.md`, agent prompts, hook reminders, or skill guides describe shared repo workflow, they should point here instead of duplicating large blocks.
- After changing protocol files, re-run the relevant validators and any hook tests that resolve rule paths.
- **Discovery frontmatter:** every file in this folder (recursive, incl. `vc-system-behavior/`) carries
  leading YAML frontmatter (`name: protocol:<slug>`, `description`, `date`,
  `metadata: {node_type, type: protocol, read_order, required, read_when}`) so `vc-context-discovery`
  can route on it. `note.md` is the single intentional exception (raw scratch dump). Enforced by
  `node .claude/skills/vc-audit-context/scripts/validate-protocol-discovery.mjs` (run via `vc-audit-context`).
