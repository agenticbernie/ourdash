---
name: protocol:implementation-standards
description: "Durable implementation standards, file-size guidance, error-handling preferences, quality gates, and commit hygiene."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 3
  required: false
  read_when: "writing or reviewing code — engineering standards and quality gates"
---

# Implementation Standards

## Core Principles

- Follow YAGNI, KISS, and DRY.
- Read `process/context/all-context.md` first, then load only the relevant context group or root file.
- Prefer updating existing files over creating parallel "enhanced" variants.
- Implement real code paths rather than mock-only stand-ins unless the user explicitly asks for a mock or stub.

## Code Organization

- Use descriptive kebab-case filenames.
- Keep TypeScript and JavaScript source files roughly under 200 lines when practical; split by responsibility when files become hard to reason about.
- Prefer focused modules, helpers, and composition over large mixed-purpose files.
- Markdown planning, context, agent, and skill files are exempt from the 200-line rule.

## Implementation Behavior

- Follow established architecture and local code patterns before inventing new ones.
- In utility or helper layers, prefer result objects over throwing when the local repo pattern expects recoverable errors.
- Handle edge cases and error paths deliberately.
- Prioritize readable, maintainable code over clever abstractions.

## Tooling

- Use `pnpm`, not `npm`.
- Use Context7 for library and API docs or setup guidance.
- Use `gh` for GitHub automation when needed.
- For database debugging, follow the current repo stack and context docs; do not assume Drizzle or SQLite unless the specific package actually uses them.

## Quality Gates

- Ensure code is syntactically valid and compiles where applicable.
- Run all fully-automated gates listed in the validate-contract (or all relevant test commands from `tests/all-tests.md` if no validate-contract exists). Fix failures. Re-run. Do not report DONE while a fully-automated gate fails in the blast radius of this plan.
- Run hybrid gates per preconditions in the validate-contract. Record outcome. If failure may be caused by this plan's changes (not an unrelated external flake), fix and re-run before DONE.
- Run agent probe gates listed in the validate-contract. Record outcome and agent judgment. Probe failure in the blast radius = investigate before DONE.
- Iterate-until-green for fully-automated tiers; record outcomes for hybrid/probe tiers. "I ran it and it failed" is not DONE. DONE means green for all fully-automated gates in the blast radius.
- Use code review or reviewer agents for meaningful implementation changes.
- Do not wave away failing tests just to force a green status.
- Read `process/context/all-context.md` AND run `find process/context/ -type f` to see every available file across all context groups. Follow the routing table to pick which files to actually load. Do not hardcode specific paths — the router plus full file listing is the stable contract.
- At each implementation step, re-read the active plan file and any existing phase reports before starting work. Write new findings (gaps, test failures, plan deviations, context learnings) to the phase report before ending the step. This is how context survives compaction and informs upcoming phases.

## Risky Work Evidence Contract

See skill: invoke `vc-risk-evidence-pack` for the full 6-class definitions, 5-artifact schema, and auto-stop rule.

## Commit Hygiene

- Keep commits focused on the requested change.
- Never commit secrets or credentials.
- Use clean professional commit messages, ideally conventional-commit style when it fits the change.
- **Commit on `main` by default.** This repo's local default branch is `main`; commit directly to it
  when the user asks for a commit. Do NOT create a feature branch first — this overrides the generic
  "if on the default branch, branch first" harness default. Only branch when the user explicitly asks
  for a feature branch or PR.

## Agent Frontmatter Conventions

All agent files at `.claude/agents/*.md` carry structured YAML frontmatter controlling
runtime behavior. Fields in scope for this program:

- `effort` — token-budget hint for the spawning model. Valid values: `low`, `medium`, `high`, `max`.
  Use `max` for opus-based execution agents (vc-execute-agent, vc-fast-mode-agent, vc-quick-fix-agent),
  `high` for planning/validation agents on sonnet, `medium` for lightweight agents, `low` for vc-git-manager.
- `skills` — list of skill slugs preloaded into the agent context window. Each slug must resolve to a
  real directory under `.claude/skills/`. Drop any slug that does not resolve; record as a known-gap
  in the phase report.
- `disallowedTools` — list of Claude tool names the agent may not invoke. Enforced by the spawning harness.
  Do not list a tool the agent legitimately needs. Reconcile against the agent's `tools:` grant first.
- `hooks` — PreToolUse blocks per-agent for identity-aware advisory write-guard. Shape:
  ```yaml
  hooks:
    PreToolUse:
      - matcher: "Write"
        hooks:
          - type: command
            command: "node .claude/hooks/agent-write-guard.mjs --agent <agent-slug> --allowlist '<glob>'"
  ```
  The hook emits advisory JSON to stderr and always exits 0 (never hard-blocks).
- `background` — set `true` on vc-tester ONLY. All loop-driving agents omit or set false.

**Known gap — CLAUDE_CODE_EFFORT_LEVEL env override:** If the `CLAUDE_CODE_EFFORT_LEVEL` environment
variable is set in the shell, it overrides the `effort:` frontmatter field for all agents in that
session, making the per-agent effort values inert. This is a Claude Code harness behavior (not a
vc-system bug). The `effort:` field documents intent and is applied when the env var is absent.
Re-check this gap if Claude Code changes the env-override precedence in a future release.
