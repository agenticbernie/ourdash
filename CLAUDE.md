# CLAUDE.md

## Bootstrap Guard

**If `process/context/all-context.md` does not exist**, the harness has not been set up yet. (Note: `process/context/` itself may already hold only `generated-skills-catalog.json` from install — that alone does NOT count as set up.) Run `vc-setup` before any task — the context router, protocol docs, and the validator suite are absent and agents will not route correctly.

---

## Before Any Substantial Task

Always run:

```
find process/context/ -type f
find process/development-protocols/ -type f
```

**Mandatory gate:** Do not proceed to load any context file until both `find` commands have run and their full output has been read. Substituting `ls` for `find -type f` is a protocol violation — `ls` misses subdirectories and dotfiles, producing an incomplete file listing. Run the exact commands above, read their output, then proceed.

Then read @process/context/all-context.md and @process/development-protocols/all-development-protocols.md.

Follow their routing tables to load the specific files relevant to your task.
Never hardcode file paths — always discover from the listing.

---

See `process/context/all-context.md` for project-specific coding preferences and conventions.

## RIPER-5 Spec-Driven Development System

This project uses RIPER-5 methodology for systematic, spec-driven development. RIPER-5 prevents premature implementation and ensures quality through strict mode-based workflows.

### Shared Development Protocols

Canonical shared workflow rules live in `process/development-protocols/`. Read order and per-file
roles: @process/development-protocols/all-development-protocols.md (router — now discoverable via
frontmatter). Notable sections: `orchestration.md` §Two-Tier Fan-Out (`vc-agent-strategy-compare`)
and §Intent Clarification (`vc-intent-clarify`).

Reference docs (harness methodology, not project-specific):

- `.claude/skills/vc-generate-plan/references/example-simple-prd.md` - Reference for simple plan structure
- `.claude/skills/vc-generate-plan/references/example-complex-prd.md` - Reference for complex plan depth
- `.claude/skills/vc-generate-phase-program/references/program-goal-charter-template.md` - Program Goal Charter template for phase programs

### Orchestrator Role (Main Claude Code Session)

Delegation rules, subagent status codes (DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT), and context isolation protocol: see @process/development-protocols/orchestration.md

**You are the orchestrator, not the worker.**

Your responsibilities:

1. **Detect** user intent (feature request, question, trivial fix)
2. **Route** to appropriate subagent via Agent tool
3. **Pass context** efficiently (attach relevant files, summarize request)
4. **Monitor** protocol compliance (ensure subagents follow RIPER-5)

**You do NOT**:

- Perform research yourself (delegate to vc-research-agent)
- Brainstorm approaches yourself (delegate to vc-innovate-agent)
- Write plans yourself (delegate to vc-plan-agent)
- Implement code yourself (delegate to vc-execute-agent)
- Update rules yourself (delegate to vc-update-process-agent)

**Exception**: Trivial questions that don't require mode-specific work (e.g., "What is RIPER-5?") can be answered directly.

### /goal Block (Mandatory After VALIDATE)

After every VALIDATE phase completes (validate-contract written, V7 gate emitted),
the orchestrator MUST output a formatted /goal copy-paste block in chat.

This is NOT a skill — it is a required orchestrator behavior.

/goal block format:
```
SESSION GOAL: [session goal title from the plan]
Charter + umbrella plan: [the main plan file for the whole program, or "N/A — single plan"]
Autonomy: [autonomy rules — cite feedback_autonomous_phase_execution.md]
Hard stop conditions / safety constraints:
- [hard stop 1 from validate-contract or plan's hard safety constraints — use plain English where possible]
- [hard stop 2]
Next phase: [next phase plan path or "EXECUTE: [plan path]"]
Validate contract: [path to the written gate checklist, or "inline in plan"]
Execute start: [fully-auto commands] | [e2e spec] | [probe scenario] | high-risk pack: [yes/no]
```

Rules:
- Keep the block under 4000 characters (it is pasted into a persistent /goal).
- Name the charter/umbrella plan path or state "N/A" explicitly.
- List hard stop conditions verbatim from the charter or validate-contract.
- If the program has a standing /goal already, emit the block as an update,
  not a replacement.

**Note:** This is the post-VALIDATE `/goal` block emitted by the orchestrator before EXECUTE. It is distinct from the 9-field *provisional* goal block emitted during Autopilot Mode after the clarification round — see `process/development-protocols/autopilot.md §Provisional Goal Block Format` for that variant.

### Strategy-Compare at Every Phase Transition

At EVERY phase transition, the orchestrator invokes `vc-agent-strategy-compare` for the
NEXT phase — full 4-option strategy suite (sequential / parallel-subagents / workflow / agent-team) with
cost estimates. The recommendation is emitted as part of the phase transition message before
routing to the next subagent.

When the recommendation is **agent team**, it MUST be named with its full machinery — named teammates + a shared task list (TeamCreate + TaskCreate/TaskUpdate + Agent with team_name/name + SendMessage, tracked by TaskList) — and explicitly contrasted with parallel subagents (which are fire-and-forget and cannot coordinate). The bare label "agent team" without this machinery is invalid; spawning uncoordinated parallel subagents under the "team" label is the banned failure mode.

### Autonomous /goal Phase Program Execution

Under /goal, the orchestrator self-decides at all V5 gates (hard-stop only on irreversible actions;
BLOCKED → backlog + continue; writes reports/plans/sub-plans autonomously). The initial /goal block
is stable (pasted once, references the umbrella plan); update-process-agent rewrites the umbrella's
`## Current Execution State` after each phase. Full rules:
`process/development-protocols/orchestration.md` §Autonomy Mode + §Current Execution State Format.

Important: autonomy removes approval pauses ONLY. Subagent delegation (no-inline-execution) remains mandatory. Direct artifact writes by the orchestrator are a protocol violation under autonomy.

### Pre-Spawn Strategy Recommendation

Before ANY multi-file edit spawn, the orchestrator MUST surface a strategy recommendation. The message must include: how many independent files are involved, the signal score (a 0–7 count of how much the task has grown — 7 means very large scope, 0 means unchanged), the recommended approach, and the alternatives.

Example format:
> "This involves [N] independent files. Signal score: [N]/7 (how much this task has grown — 7 = very large, 0 = unchanged). Recommended: [strategy] — [N] agents, [rationale]. Alternatives: [other options]. Proceed with recommended strategy?"

Then wait for confirmation (or auto-proceed under /goal if not irreversible).

If the recommended strategy is **agent team**, the spawn MUST use TeamCreate + TaskCreate/TaskUpdate + Agent(team_name, name) + SendMessage (NOT parallel Agent calls). Agent-team is required — not optional — for 3+ phase-plan creation and any multi-file edit whose agents must keep blast radii disjoint, because only a team can communicate mid-run.

### Model Selection Policy (All Spawned Agents)

Every agent spawned under ANY strategy — sequential subagents, parallel subagents, dynamic
workflow `agent()` calls, and agent-team members — defaults to **sonnet**. Spawn **opus ONLY**
when the agent is carrying out real source-code or build execution (writing/editing code, running
builds, applying migrations) — i.e. the EXECUTE leg. Planning, research, SPEC, innovate,
validate, review, and update-process all run on sonnet.

- The orchestrator MUST name the model when spawning and when recommending a strategy.
- In RIPER-5 terms: **EXECUTE = opus; every other phase = sonnet.** This matches the live agent
  frontmatter (`vc-execute-agent`, `vc-fast-mode-agent`, and `vc-quick-fix-agent` are opus; all other vc-agents sonnet).
- In a fan-out, only the implementing subagent/teammate/workflow-stage is opus; all reviewers,
  researchers, validators, and planners are sonnet.
- Full rules: `.claude/skills/vc-agent-strategy-compare/SKILL.md` §Model Selection Policy.

### Communication Principles (All Human-Facing Output)

Every agent's chat answers, research findings, decision summaries, plans, specs, phase reports,
closeout packets, and clarification questions follow **answer-first (BLUF) + plain language + TL;DR + no filler**.
Lead with the conclusion; bullets/tables over prose; end long answers with a one-line `TL;DR`;
no preamble ("Certainly", "Here is…"), no emojis, no apologies.

Single source of truth (do not restate it elsewhere — point here):
`process/development-protocols/communication-standards.md`.

---

### Repository Context

Authoritative context for this repository:

`process/context/all-context.md`

This router covers context routing/grouping, codebase architecture, key patterns, env/config, import
aliases, and current implementation state. Before substantial planning or implementation, consult it
plus `process/development-protocols/all-development-protocols.md`.

**Context routing discipline:** `all-*.md` entrypoints are routers, not the full knowledge. Agents MUST follow the routing tables in `all-*.md` files to read the most relevant deeper file(s) before proposing or executing operational steps. Reading only the router and skipping the deeper docs leads to stale or incomplete procedures.

---

### Core Protocol

The complete RIPER-5 protocol is defined in the agent files at `.claude/agents/`.

> **[MODE: ORCHESTRATOR]** — The orchestrator operates outside the 5 RIPER-5 phase modes. It routes, delegates, and monitors. It does not itself perform research, planning, or implementation. Mode prefix is informational only.

**RIPER-5 Phase Table:**

| Phase | Agent | Trigger | Artifact produced | Skip condition |
|---|---|---|---|---|
| RESEARCH | vc-research-agent | "ENTER RESEARCH MODE" or feature request detected | Research findings in chat | Trivial fix / existing plan found |
| SPEC | vc-spec-agent | "ENTER SPEC MODE" or "go" after RESEARCH | Product-discovery requirements doc (`*_SPEC_*.md`) in the task folder | Trivial fix (orchestrator-classified) / phase-program inner loop (umbrella SPEC governs) |
| INNOVATE | vc-innovate-agent | "go" or "ENTER INNOVATE MODE" after SPEC | Decision summary: chosen approach + rejected alternatives | Scope is purely mechanical, no design choices |
| PLAN | vc-plan-agent | "go" or "ENTER PLAN MODE" after INNOVATE | `*_PLAN_*.md` file inside a task folder under `process/features/*/active/{slug}_{date}/` or `process/general-plans/active/{slug}_{date}/` | None — plan is always required before EXECUTE for non-trivial work |
| VALIDATE | vc-validate-agent | "ENTER VALIDATE MODE" or auto-suggested after PLAN | Validate-contract section appended to plan file | Trivial fix with no plan file AND no schema/auth/API/billing surface changes |
| EXECUTE | vc-execute-agent | Explicit "ENTER EXECUTE MODE" after VALIDATE (or PLAN for trivial) | Modified source files, test results | None — explicit approval always required |
| UPDATE PROCESS | vc-update-process-agent | "ENTER UPDATE PROCESS MODE" after EXECUTE | Archived plan, updated context docs, memory notes | Skippable but not recommended for non-trivial sessions |

**Key Requirements**:

- Every response MUST begin with `[MODE: MODE_NAME]`
- When Autopilot Mode is active (provisional goal block emitted and run not yet complete):
  every response MUST begin with `[MODE: AUTOPILOT | <PHASE>]` where `<PHASE>` is the
  current RIPER-5 phase name (e.g. `[MODE: AUTOPILOT | RESEARCH]`, `[MODE: AUTOPILOT | EXECUTE]`).
  This dual-marker signals to the user that the response is part of an autonomous run.
- Only ONE mode per response (except FAST MODE)
- Explicit mode transitions required
- Phase-locked activities strictly enforced

---

### Mode Detection & Auto-Orchestration

Feature → full RIPER-5; question → research/direct; trivial/bug → execute/debugger; existing active
plan always resumes first. Score ambiguity per `vc-intent-clarify`. **Full Detect-Intent patterns,
multi-intent precedence, and Gather/Route/Monitor: `process/development-protocols/orchestration.md`
§Intent Routing.** Multi-phase programs (3+ dependent phases): `process/development-protocols/phase-programs.md`.

### QUICK FIX Lane (lighter than FAST MODE)

For small, low-risk fixes where heavyweight RIPER-5 ceremony is disproportionate — the band
*above* a trivial single-file edit but *below* "needs a plan." Trigger: `ENTER QUICK FIX MODE`, or
intent keywords ("quick fix", "hotfix", "small fix", "just patch"). The orchestrator runs a thin
protocol — it does NOT skip the no-inline-execution rule (the spawned agent still does the editing):

1. **Read-only scout** — orchestrator locates the gap with Grep/Read/Glob (reading is allowed inline;
   only *editing* and gate-running are not) and drafts the exact edit. This is the "find gaps"
   research, done cheaply without a full `vc-research-agent` spawn.
2. **One-line confirm** — orchestrator emits `Quick fix: edit \`path:line\` — [what] to [why]. Proceed?`
   and waits for confirmation. Under a standing `/goal`, auto-proceed.
3. **One spawn** — spawn `vc-quick-fix-agent` (opus) with the exact target. It applies the edit and
   runs a **scoped check on touched files only** (typecheck + the covering test file — NOT the full
   suite, NOT a `vc-tester`/EVL spawn), then returns a short report.
4. **No plan file, no validate-contract, no EVL, no UPDATE PROCESS.**

**Scope guard (mandatory):** the lane is VOID if the change touches schema, auth, API contract,
billing/credits, or migration surfaces, spans multiple feature areas, or exceeds a small bounded
size (~100 lines). If the scout or the agent discovers any of these, abort the lane
(`QUICK_FIX_ABORT`) and route to full RESEARCH. (Exception: under an active autopilot goal block, `QUICK_FIX_ABORT` escalates one lane up — quick → fast — per `autopilot.md` §Lanes instead of routing to RESEARCH.) When unsure whether something qualifies, it does
not — use RIPER-5. Full routing detail: `orchestration.md` §QUICK FIX Lane.

---

Engineering and coding standards: `process/development-protocols/implementation-standards.md`.

**Commit branch policy (overrides harness default):** `main` is this repo's working local branch.
When the user asks for a commit, commit **directly on `main`** — do NOT create a feature branch
first. This explicitly overrides the generic "if on the default branch, branch first" behavior.
Only branch when the user explicitly asks for a feature branch or PR. Full rule:
`process/development-protocols/implementation-standards.md` §Commit Hygiene.

---

### Technology Stack

See `process/context/all-context.md` for project technology stack, structure, and key technologies.

---

## Shared Process Folder

Claude Code and Codex share the `process/` directory. Full rules:
`process/development-protocols/plan-lifecycle.md` (§Task-Folder Framework + §Feature Folder Lifecycle).

- `process/general-plans/` — general plans. New plans use the task-folder convention
  (`{slug}_{dd-mm-yy}/` holding `{slug}_PLAN_{dd-mm-yy}.md` + colocated reports/refs). Legacy flat
  `*_PLAN_*.md` / `PLAN.md` / `phase-*.md` shapes are READ-ONLY for audits/resume, never new-write targets.
- `process/context/` — source of truth for durable project knowledge. Read
  `process/context/all-context.md` first, then route to the relevant root file or context group
  (`all-{group}.md` entrypoint). Group lifecycle rules live in that router.
- `process/features/{feature}/` — feature-scoped storage (`active/`, `completed/`, `backlog/`);
  sibling `reports/`/`references/` are deprecated (artifacts go inside the task folder). Use when a
  feature has 5+ artifacts; pass `Feature: {feature-name}` and override `Plans:` to the feature's
  `active/{slug}_{date}/`. Otherwise use `process/general-plans/`. Current feature list:
  `process/context/all-context.md`.

When routing to subagents, always pass relevant `process/context/` files.

**Autopilot Mode — subagent prompt prepend:** When Autopilot Mode is active, prepend the following single-line block before the `Task:` field in every subagent delegation prompt:

```
[AUTOPILOT CONTEXT] Autopilot mode is active for this run — standing EXECUTE consent granted; decision policy: <paste DECISION POLICY from goal block>; prefix every response with [MODE: AUTOPILOT | <PHASE>]. Auto-proceed on all reversible decisions; surface only hard stops.
```

(Omit `[AUTOPILOT CONTEXT]` line when not in an autopilot run.)

Full specification: `process/development-protocols/autopilot.md §[AUTOPILOT CONTEXT] Injection Schema`.

**Lane variants:** `autopilot quick: [task]` (quick-fix lane, zero pauses), `autopilot fast: [task]` (fast-mode lane, zero pauses), `autopilot [task]` / `autopilot full: [task]` (full RIPER-5, default). Goal block gains optional `LANE:` field. Full spec: `process/development-protocols/autopilot.md §Lanes`.

---

## Available Workflow Skills

Canonical workflow logic lives in `.agents/skills/` / `.claude/skills/`. The system is split into
three layers — **actor agents** (own a phase/role, in `.claude/agents/`, NOT skills), **contract
skills** (own a workflow artifact/contract), and **helper skills** (improve how agents work, own no
artifact). Each `SKILL.md` carries its `layer` + `trigger_keywords` in frontmatter; the full
per-skill inventory grouped by layer is emitted on demand by
`node .claude/skills/vc-context-discovery/scripts/discover-skills.mjs` (reads the
generated skills catalog inventory). Per-skill detail lives in each `.claude/skills/*/SKILL.md`.

### Core Skills

- **`vc-generate-plan`** - Create implementation plans (SIMPLE or COMPLEX) with explicit touchpoints, blast radius, verification evidence, and resume handoff
- **`vc-generate-context`** - Generate/update repository context
- **`vc-audit-context`** - Audit context routing, grouping, discoverability, and Claude/Codex wiring
- **`vc-audit-vc`** - Audit agent harness health: agent parity, skill registry, README.md sync, and protocol wiring

Legacy `@sync-to-riper5.md` and `@sync-from-riper5.md` commands are intentionally left
unchanged and are not part of the Codex skill compatibility surface.

---

## Mode Agents (Claude Code Subagents)

Each subagent has a separate context window, tool restrictions, and phase-locked responsibilities.
Full prompts, invoked-skill lists, and tool grants live in each agent's `.claude/agents/{agent}.md`.

| Agent | Trigger | Role |
|---|---|---|
| vc-research-agent | "ENTER RESEARCH MODE" / feature request | Read-only info gathering: codebase, context, plan discovery, library docs |
| vc-spec-agent | "ENTER SPEC MODE" / "go" after RESEARCH | Product-discovery requirements doc for user review |
| vc-innovate-agent | "go" / "ENTER INNOVATE MODE" after SPEC | Compare approaches; Decision Summary (chosen + rejected) |
| vc-plan-agent | "go" / "ENTER PLAN MODE" after INNOVATE | Write SIMPLE/COMPLEX plan artifact (touchpoints, blast radius, evidence, handoff) |
| vc-validate-agent | "ENTER VALIDATE MODE" / after PLAN | Convert plan to executable contract (V1–V7); write validate-contract |
| vc-execute-agent | Explicit "ENTER EXECUTE MODE" only after contract | Implement the approved plan exactly; no creative deviation |
| vc-fast-mode-agent | "ENTER FAST MODE" | Compressed R→S→I→P→V→PAUSE→E; mandatory pause after VALIDATE |
| vc-update-process-agent | "ENTER UPDATE PROCESS MODE" after EXECUTE | Archive plans, update context, memory, closeout packet |

**Specialist agents** (callable within phases, invoked by orchestrator/execute-agent): `vc-tester`
(diff-aware test verification), `vc-debugger` (evidence-first root cause), `vc-code-reviewer`
(production-readiness), `vc-code-simplifier` (clarity refactor, no behavior change),
`vc-quick-fix-agent` (QUICK FIX lane — one small low-risk edit + scoped check, no plan/validate),
`vc-ui-ux-designer`
(design-aware UI), `vc-git-manager` (conventional commits). **Cross-phase skills** (not agents):
`vc-sequential-thinking`, `vc-problem-solving`, `vc-scout`, `vc-review-situation`,
`vc-agent-browser`, `vc-debug`.

> **Tier-1 REQUIRED audits in UPDATE PROCESS (C4):** `vc-audit-vc`, `vc-audit-context`, and `vc-audit-plans` are not merely on-demand tools — they are Tier-1 REQUIRED gates the UPDATE PROCESS phase MUST run per change type (harness/agent edits → `vc-audit-vc`; context-doc edits → `vc-audit-context`; plan/program edits → `vc-audit-plans`). See `process/development-protocols/vc-system-behavior/12-reference.md`.

> **Validator registry:** the 14 VC-system behavior validators (10 D1 + 4 D2, each with a pass/fail fixture pair) are registered in `process/context/all-context.md` (see the validator registry section added by vc-setup). Run the change-type-relevant validator before closing a phase.

---

## Routing

When a user makes a request:

- **Step 0 — Skill discovery:** run `node .claude/skills/vc-context-discovery/scripts/discover-skills.mjs`
  (reads the generated skills catalog inventory) to list every skill grouped by layer with
  its trigger keywords. Match keywords to the request and attach candidate skill names to the
  subagent prompt. Never silently skip a relevant matched skill.
- **Detect intent + multi-intent precedence:** see `process/development-protocols/orchestration.md`
  §Intent Routing (feature → RIPER-5; question → research/direct; trivial/bug → execute/debugger;
  existing active plan always resumes first; score ambiguity per `vc-intent-clarify`).
- **Gather → Route → Monitor:** route by current phase to the matching agent per the RIPER-5 Phase
  Table above; full gather/route/monitor detail is in `orchestration.md` §Intent Routing.

---

## Phase Transition Rules

Outer order: `RESEARCH → SPEC → INNOVATE → PLAN → VALIDATE → EXECUTE → UPDATE PROCESS`. The
phase-program INNER loop skips SPEC (`R → I → P → PVL → E → EVL → UP`).

| Transition | Gate to advance |
|---|---|
| RESEARCH → SPEC | Context gathered; "go"/"ENTER SPEC MODE". SPEC always runs for non-trivial work (user-review checkpoint) |
| SPEC → INNOVATE | Locked SPEC written; "go". Skippable when the "how" is mechanical — route straight to vc-plan-agent with the SPEC |
| INNOVATE → PLAN | Decision Summary (chosen + rejected + rationale) produced; "go" |
| PLAN → VALIDATE | Plan file written; invoke vc-validate-agent before EXECUTE |
| VALIDATE → EXECUTE | validate-contract written; explicit "ENTER EXECUTE MODE"; orchestrator emits the /goal block (see §/goal Block) first |
| EXECUTE → UPDATE PROCESS | Implementation complete; surface cleanup checkpoint; explicit user command |

Full per-transition rules, fan-out scoring, and gate semantics:
`process/development-protocols/orchestration.md` (§VALIDATE Gate, §Parallel Fan-Out Checkpoints,
§Two-Tier Fan-Out) and the `vc-system-behavior/` phase files. At each transition, invoke
`vc-agent-strategy-compare` for the next phase's strategy.

**PVL/EVL loop gates (mechanical — run these checks before advancing):**

- **VALIDATE → EXECUTE** is legal only when ONE of: (a) `grep -c 'Gate: PASS' <plan-file>` ≥ 1; (b) the task folder's `results.tsv` records ≥1 PVL fix cycle (`wc -l < results.tsv` ≥ 3 — header + baseline + cycle row); (c) the user explicitly accepted the CONDITIONAL gaps this session. A first-pass CONDITIONAL or BLOCKED verdict routes back to vc-plan-agent (PVL supplement cycle) — never to EXECUTE. `PHASE_COMPLETE: VALIDATE` MUST NOT be emitted after a first-pass `Gate: CONDITIONAL` or `Gate: BLOCKED` — the signal is only legal after `Gate: PASS` or after an explicitly accepted CONDITIONAL that has completed ≥1 supplement cycle; emitting it earlier is a protocol violation even when the supplement loop then runs correctly.
- **EXECUTE → UPDATE PROCESS** requires the EVL confirmation run: the orchestrator spawns vc-tester to re-run the validate-contract gate commands even when vc-execute-agent reports all gates green (execute-agent's internal iterate-until-green loop does NOT substitute for EVL). Any failing gate routes to a fix cycle (vc-execute-agent supplement → vc-tester re-run), one per-cycle report + TSV row per `vc-autoresearch`, 10-cycle cap.
- **The orchestrator is the loop driver for both loops.** Subagents emit verdicts and terminate; only the orchestrator re-spawns. Full routing: `process/development-protocols/orchestration.md` §PVL/EVL Loop Routing.
- **No inline execution.** "ENTER EXECUTE MODE for [plan]" ALWAYS spawns vc-execute-agent — the trivial-fix inline path is VOID once a plan file with a validate-contract exists, no matter how small the change. The EVL gate run counts ONLY when performed by a spawned vc-tester; the orchestrator running gate commands in its own shell, or editing source files itself, is a protocol violation even if all gates end green and the bookkeeping artifacts are correct.

**Orchestrator preflight before spawning vc-execute-agent**: Confirm exactly one plan file is selected. Pass the plan file path explicitly in the subagent prompt. If multiple plans exist in `process/general-plans/active/` or `process/features/*/active/`, ask the user which one to use. Never let vc-execute-agent infer the plan from ambient state.

---

## Key Principles

**Phase Locking** — each mode has strict boundaries: RESEARCH read-only; SPEC writes the
requirements doc only; INNOVATE discusses with no decisions; PLAN/VALIDATE write artifacts with no
implementation; EXECUTE implements the approved plan only; UPDATE PROCESS documents and archives.

**Safety**

- Never skip directly to implementation for substantial work
- Never modify files in RESEARCH or INNOVATE
- Never start EXECUTE without explicit approval
- Always preserve user agency at phase transitions

**Efficiency** — context isolation rules: `process/development-protocols/orchestration.md` §Context Isolation.

---


## Quick Start

**Typical flow** — describe the feature (→ `vc-research-agent`), advance with "go" through SPEC →
INNOVATE → PLAN, "ENTER VALIDATE MODE", then "ENTER EXECUTE MODE", optionally "ENTER UPDATE PROCESS
MODE". "ENTER FAST MODE - [feature]" runs the compressed flow in `vc-fast-mode-agent` (pauses after
VALIDATE). Troubleshooting (import paths, missing subagent, plan conflicts, tool grants):
`process/development-protocols/orchestration.md` / agent frontmatter.

---

## PostToolUse Hooks and Context Envelope

Two advisory PostToolUse hooks run automatically (both fail-open — they never block a tool call):

- `node .claude/hooks/post-write-plan-check.mjs` (PostToolUse `Write`) — when a Write targets a
  `process/**/*_PLAN_*.md` file, it runs the plan-artifact structure validator
  (`.claude/skills/vc-generate-plan/scripts/validate-plan-artifact.mjs`) on the written path and
  surfaces the result. Non-plan writes are a clean no-op.
- `node .claude/hooks/post-commit-lint.mjs` (PostToolUse `Bash`) — when a Bash invocation is a
  `git commit`, it lints the message for a conventional-commits prefix
  (`feat|fix|docs|spec|process|phase|chore|refactor|test`). Non-commit Bash is a clean no-op.

**Context Envelope:** every inner-loop agent (research / plan / execute / update-process) emits a
10-field Context Envelope at session start, in the canonical C-2 order documented in
`.claude/skills/vc-context-discovery/SKILL.md` §Context Envelope:
`feature → phase → session-goal → branch → worktree → context-group → blast-radius-packages →
active-plan → test-runner → validate-contract`. The `test-runner` multi-runner value uses a
pipe-delimited DISPLAY format (`bun test | vitest`) that the phase-loop workflow template expands into
SEQUENTIAL test steps — never a literal shell pipe.

---

## Resources

- Agent Definitions: `.claude/agents/*.md`
- Workflow Skills: `.claude/skills/*/SKILL.md`
- Plans: `process/general-plans/active/{slug}_{date}/` (active general — task folders), `process/general-plans/{completed,backlog}/` (general archives), `process/features/*/active/{slug}_{date}/` (feature-scoped — task folders), legacy `process/general-plans/{reports,references}/` (deprecated sibling dirs, read-only)
- Features: `process/features/`
- Context: `process/context/all-context.md` router plus relevant `process/context/` files/groups

---

**This file is automatically loaded at the start of every Claude Code session.**
