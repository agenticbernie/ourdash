---
name: protocol:orchestration
description: "Delegation rules, subagent status protocol, context isolation, feature-scope routing, intent clarification, validate gate, BLOCKED escalation, two-tier fan-out, and research-first rules."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 2
  required: true
  read_when: "orchestrating phases, routing to subagents, fan-out/strategy decisions, validate gate, or BLOCKED escalation"
---

# Orchestration Protocol

## Delegation Context

When spawning subagents, always include:

1. Work context path: the git root for the primary files being touched
2. Plans path: `{work_context}/process/general-plans/active/` (plans inside `{slug}_{date}/` task subfolders)
3. Feature: optional, but required when the work belongs to a feature-scoped folder

Feature override paths:

- Plans: `{work_context}/process/features/{feature}/active/` (plans inside `{slug}_{date}/` task subfolders)
- Reports and references are co-located inside task folders (not sibling dirs); legacy `reports/` and `references/` sibling dirs are read-only

Rule: if the current shell CWD differs from the real work context, pass the work-context paths, not the shell CWD.

### Agent Frontmatter Conventions (spawn context)

Agent frontmatter fields (`effort`, `skills`, `disallowedTools`, `hooks`, `background`) are
documented in `process/development-protocols/implementation-standards.md`
§Agent Frontmatter Conventions. The `effort:` value aligns with the model selection policy
(max for opus agents, high for sonnet planners/validators, medium/low for lighter roles).
The per-agent `skills:` list preloads context window context for that agent's phase.
The `disallowedTools:` list is enforced by the harness and must be reconciled against the
agent's tool grant before applying. The `hooks:` PreToolUse(Write) block is advisory only
(the `agent-write-guard.mjs` script always exits 0).

## Feature Scope Detection

Before setting `Feature:` in a subagent prompt:

1. Check whether `process/features/{topic}/` already exists.
2. Check whether the request clearly belongs to an existing feature.
3. If the request is a new multi-phase product area or the user frames it as a substantial feature, create a feature folder first.
4. Otherwise default to `process/general-plans/active/`.

When creating a new feature folder:

```bash
mkdir -p process/features/{name}/{active,completed,backlog}
# Note: do NOT create reports/ or references/ — these are deprecated sibling dirs; new artifacts go inside task folders
```

**Feature artifact discovery:** When routing any agent to a feature-scoped task, pass the output of `find process/features/{feature}/ -type f | sort` alongside the context files. This gives the agent full visibility into all artifacts across `active/` (including task subfolders), `completed/`, `backlog/`, and legacy `references/` and `reports/` before it proposes anything, preventing duplication of past work or ignoring planned future work.

Then update both `AGENTS.md` and `CLAUDE.md` so the current-features list stays in sync.

## Subagent Status Protocol

Subagents must end with one of:

- `DONE`
- `DONE_WITH_CONCERNS`
- `BLOCKED`
- `NEEDS_CONTEXT`

Controller handling:

- Never ignore `BLOCKED` or `NEEDS_CONTEXT`.
- Never retry the exact same blocked approach three times.
- Treat correctness concerns as action items before moving on.
- Treat observational concerns as notes unless they create real scope or correctness risk.

`CONTEXT_PARTIAL` is NOT a subagent status code — it is an inline warning flag embedded in phase report bodies. Subagents with partial context must report one of the 4 canonical status codes (typically `DONE_WITH_CONCERNS`). `CONTEXT_PARTIAL: [reason]` appears in the Concerns field, not as a standalone status.

Recommended footer:

```md
**Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
**Summary:** [1-2 sentence summary]
**Concerns/Blockers:** [if applicable]
```

## Context Isolation

Subagents receive only the context they need.

Rules:

1. Provide a fresh task summary, not raw chat history.
2. List exact files to read or modify.
3. If following a plan, pass the exact selected plan file path and relevant phase excerpt.
4. Keep orchestration and coordination state in the main session.
5. Mention relevant shared skills when they match the task.
6. Team/orchestration helpers such as `team` or FAST-mode flows may not bypass the same human approval gates required by the canonical RIPER workflow.
7. **Context routing depth:** `all-*.md` entrypoints are routers, not the full knowledge. Subagents MUST follow the routing tables in `all-*.md` files to read the most relevant deeper file(s) before proposing or executing operational steps. Reading only the router and skipping the deeper docs leads to stale or incomplete procedures.
8. Summarize context rather than duplicate raw file contents in handoff prompts.
9. Reuse existing active plans and context files — always check active plan surfaces before creating new artifacts.

Prompt template:

```text
Task: [specific task description]
Files to modify: [list]
Files to read for context: [list]
Acceptance criteria: [list]
Constraints: [list]
Plan reference: [exact plan file path or phase path]

Work context: [project path]
Feature: [feature-name]
Reports: [reports path]
Plans: [plans path]
Relevant skills: [comma-separated skill names]
```

## Sequential vs Parallel Use

Chain subagents when work depends on prior outputs:

- Research -> design -> plan
- Plan -> implementation -> testing -> review

Run in parallel only when scopes are independent and integration boundaries are clear.

## Large Project Phase Programs

When a task is a large program rather than a normal single-plan feature, use
`process/development-protocols/phase-programs.md`.

Signals:

- 3 or more dependent phases
- repeated validation gates between milestones
- multi-package or multi-runtime scope
- the user explicitly wants durable phase-by-phase progress that survives compaction

Controller rules for phase programs:

1. keep one umbrella plan plus one selected current phase
2. do not run the whole program as one giant EXECUTE pass
3. for each phase, require the 10-step loop:
   - research subagent
   - execution approval checkpoint
   - execute subagent
   - validate subagent
   - regression checkpoint (against previously verified overlapping surfaces)
   - regression-found workflow (conditional, if regression detected)
   - durable report/context update
   - commit checkpoint (vc-git-manager for execution changes)
   - inter-phase UPDATE PROCESS (archive phase, capture learnings)
   - move-on recommendation
4. after each phase, update reports and downstream phase plans before advancing

**Compatibility note:** The 10-step loop above is the legacy orchestrator spawn-event view. The canonical 7-step inner loop (per phase) is defined in behavior-reference Section 8. Mapping:
- Step 1 (research subagent) = Step 1 RESEARCH
- Step 2 (execution approval checkpoint) = /goal block gate (Section 5 V7)
- Step 3 (execute subagent) = Step 5 EXECUTE
- Step 4 (validate subagent) = Step 4 PVL
- Step 5 (regression checkpoint) = Step 6 EVL
- Step 6 (report update) = Step 7 UPDATE PROCESS
- Step 7 (commit) = canonical commit timing (Section 8)
- Steps 8-10 (inter-phase) = phase boundary handoff

INNOVATE (Step 2) and PLAN-SUPPLEMENT (Step 3) from the 7-step are required sub-steps for each phase but are not shown as top-level orchestrator spawn events in this 10-step view. See behavior-reference Section 8 for the authoritative 7-step specification.

5. if the original program reaches a narrower scoped goal than the user's larger vision, split the
   remaining work into follow-up feature folders instead of stretching one project forever
6. the umbrella plan must carry a Program Goal Charter (north star, definition of done, what
   "verified" means, scope tiers → phase mapping, out-of-scope tier, hard safety constraints), and
   the kickoff must print the compressed copy-pasteable session-goal block in chat — see
   `process/development-protocols/phase-programs.md` ("Program Goal Charter" and "Kickoff
   Recommendation Format" step 5)

### Plan-Supplement Step (Phase Programs)

After research-agent returns findings, orchestrator spawns plan-agent in supplement
mode if research identified gaps, pre-conditions, or new items not in the current
phase plan checklist. Plan-agent in supplement mode:
- Reads research findings from conversation context
- Adds new checklist items, pre-conditions, or notes to the phase plan only
- Does NOT create new plan files
- Marks "n/a — research clean" and checks off 1b if nothing to add

This is Phase Loop Progress step 1b. It runs after 1a (research) and before
step 2 (validate). It is never skipped — it either adds items or marks n/a.

The validate-contract must follow full `.claude/skills/vc-validate-findings/references/example-validate-output.md`
format — partial contract (missing Plan updates applied / Execute-agent instructions / Test gates)
is treated as a placeholder.

### Current Execution State Format

The umbrella plan's `## Current Execution State` (or equivalent status section) must always include:
- Current loop step: `1a-research | 1b-plan-supplement | 2-validate | 3-execute | 4-update-process`
- Validate-contract status: `written (date)` or `not written`

This is the signal the orchestrator reads to choose which subagent to spawn next. When this information is missing from the umbrella plan, the orchestrator must infer it from the Phase Loop Progress checkboxes in the selected phase plan.

**Superseded by Section 6 canonical format:** The 2-field format above (current loop step + validate-contract status) is superseded by the canonical 8-field `## Current Execution State` format defined in behavior-reference Section 6 (Last updated / Current phase N of total / Phase N name / Phase N status / Phase N EVL / Phase N report / Next phase). The `update-process-agent` writes the 8-field format.

For orchestrator routing decisions: use the Phase Loop Progress checkboxes in the phase plan file (see Phase Program Pre-Routing Check below), NOT the umbrella `## Current Execution State` loop-step field.

### Phase Program Pre-Routing Check (7-step model)

Read `## Phase Loop Progress` section of the phase plan file.

| Phase State | Action |
|---|---|
| Step 1 (RESEARCH) | vc-research-agent |
| Step 2 (INNOVATE) | vc-innovate-agent |
| Step 3 (PLAN-SUPPLEMENT) | vc-plan-agent — supplement mode: update existing outer-loop phase plan; do NOT create a new plan file |
| Step 4 (PVL) OR validate-contract is placeholder | vc-validate-agent |
| Step 0 checkpoint shows "Dependency-BLOCKED" (detected from Phase Loop Progress checkbox notation — `Dependency-BLOCKED` text in Step 0) | Advance to Phase N+1 Step 0; do NOT spawn any agent for this phase |
| Step 4 checkbox marked BLOCKED-skipped (via `PHASE_SKIPPED: BLOCKED` signal) | Advance to Phase N+1 Step 0 — do NOT spawn vc-execute-agent for this phase; Steps 5–7 are not run |

**Supplement mode note:** Step 3 (PLAN-SUPPLEMENT) invokes vc-plan-agent in supplement mode. Supplement mode is required whenever the outer-loop phase plan file already exists. Creation mode applies only when no plan file exists yet for this phase.

After Step 3 completion (PHASE_COMPLETE: PLAN-SUPPLEMENT signal received): tick Step 3 checkbox; advance to Step 4 — spawn vc-validate-agent for inner PVL. The SUPPLEMENT_APPLIED signal routes differently (V7 PVL re-trigger — see behavior-reference Section 5 V7).

**Step 4 (PVL) — outer vs inner branch:**
- **Outer PVL** (umbrella plan present AND validate-contract absent from all phase plans): spawn vc-validate-agent agent-team — one vc-validate-agent per phase plan running concurrently. See behavior-reference Section 8 §Outer PVL for coordination token and registry initialization.
- **Inner PVL** (phase plan has existing validate-contract and Inner Loop Refresh Note triggers re-run): spawn single vc-validate-agent for the specific phase plan.

**Loop bookkeeping (vc-autoresearch):** the plan-validate-fix loop is run by the `vc-autoresearch` skill (`domain: plan`) as its shared bookkeeper — iteration counter, plateau detection, iteration report, regression flag, 10-cycle cap. The validate step itself fans out in parallel via `vc-validate-findings` (Layer 1 dimension agents + Layer 2 feasibility agents), owned by vc-validate-agent. When a CONDITIONAL/BLOCKED gap set spans independent plan sections, the orchestrator spawns **multiple parallel plan-fix agents**, one per independent gap group, partitioned so no two agents edit the same plan region; when gaps are interdependent or touch one section, fall back to a single plan-fix agent. See `.claude/skills/vc-autoresearch/SKILL.md` §PVL Wiring. **The ORCHESTRATOR executes this bookkeeping itself at every cycle boundary — no agent runs it implicitly; per-verdict routing table: §PVL/EVL Loop Routing.**
| Steps 1–4 done | vc-execute-agent |
| Step 6 (EVL) unchecked | Orchestrator runs EVL directly |
| Step 7 (UPDATE PROCESS) unchecked | vc-update-process-agent |

**Step 4b — generated-by check (runs when Steps 1–4 appear done):**
Pre-check: if Step 4 checkbox is marked "BLOCKED-skipped" (no validate-contract written): route to Phase N+1 Step 0 — do NOT run the generated-by check and do NOT spawn vc-execute-agent. Validate-contract absence for a BLOCKED-skipped phase is expected, not an error.
(Note: the Pre-Routing Check table above routes BLOCKED-skipped phases directly to Phase N+1 before reaching this check. Step 4b's pre-check is a safety fallback for cases where the checkbox text is ambiguous or the routing table is bypassed.)

Check the `generated-by:` field in the validate-contract.
- If `generated-by: outer-pvl`:
  - Scan the plan file for `## Inner Loop Refresh Note` with a date newer than the validate-contract date.
  - If note FOUND and note date > contract date → "inner R+I has run" = TRUE → re-run PVL from V1.
  - If note ABSENT or note date ≤ contract date → "inner R+I has run" = FALSE → do NOT re-run PVL.
- If `generated-by: inner-pvl: phase-N` → proceed to EXECUTE (inner PVL is already current).

  Note: "Re-run PVL from V1" means the orchestrator re-spawns vc-validate-agent for this plan. The spawned validate-agent starts at V1 naturally. The `## Inner Loop Refresh Note` date check inside validate-agent's V1 Step 4 will confirm re-validation is needed and will skip the early-exit, proceeding to V2 fan-out after completing V1 structural checks. No V1 structural checks are skipped.

**Signal exception — mid-program plan creation:** when vc-plan-agent creates a new plan mid-program (conflict resolution or phase insertion), it emits `MID_PROGRAM_PLAN_CREATED: [path] — inner PVL required` instead of `PHASE_COMPLETE: PLAN`. Orchestrator action: trigger inner PVL for that plan only; do NOT output a new /goal block; umbrella plan is unchanged. See behavior-reference Section 8 §MID_PROGRAM_PLAN_CREATED.

**Legacy 5-step plan mapping:** 1a → Step 1, 1b → Step 3, 2 → Step 4, 3 → Step 5, 4 → Step 7.

Never route to `vc-execute-agent` for a phase program phase without confirming
research and validate have completed. A placeholder validate-contract is not a
completed validate — "vc-validate-agent writes this section" is a placeholder.

Under a standing /goal, step 2 (execution approval checkpoint) is
STANDING-GRANTED but steps 1–4 of the Phase Loop Progress are never skipped.
They run and complete before execute begins.

### Stable Program Goal Format

Every phase program umbrella plan must include a `## Stable Program Goal` section
containing a copy-pasteable /goal block. Requirements:
- Hard limit: ≤ 4000 characters (the /goal command rejects longer blocks)
- Required sections (in order): TARGET / PER-PHASE LOOP / HARD STOPS /
  SAFETY / TEST GATES / VALIDATE CONTRACT / START
- PER-PHASE LOOP must state: research → validate → execute → update-process,
  validate never skipped, placeholder contract = blocked, every subagent first
  action runs vc-context-discovery + vc-plan-discovery, every phase-END invokes
  vc-agent-strategy-compare
  (Full canonical 7-step form: research → innovate → plan-supplement → pvl → execute → evl → update-process — abbreviated 4-step form acceptable in /goal block for character limit; see vc-system-behavior/11-phase-programs.md for full sequence.)
- TEST GATES must list all 5 validator commands with full paths
- START must name the current phase and loop step explicitly
- When updating the goal block after phases complete, re-verify char count before
  writing — compress if needed, never truncate required sections

## Intent Clarification

Before routing a new user request to a subagent, the orchestrator scores the request's
ambiguity using four binary signals (0-4), selects a tier (silent auto-route, inline
summary, or full checkpoint), and resolves intent in the main thread before delegating.

### Auto-Skip Conditions

These conditions force Tier 0 (silent auto-route) regardless of the ambiguity score:

- User said "go", "continue", "just do it", or similar continuation phrases
- Mid-phase-program execution (active phase plan is selected and approved)
- Trivial fix detection (single-file, under 15 lines, no schema/API/auth changes)
- Explicit mode command ("ENTER EXECUTE MODE", "ENTER RESEARCH MODE", etc.)
- Resuming an existing active plan
- Pure information questions ("What is X?", "How does Y work?") that map to a single obvious routing target

### Autonomy Mode

Autonomy is granted when the user says "you decide", "just do it", "full autonomy", "don't ask",
or when mid-phase-program context has the current phase plan selected and approved, or when the
user has answered Tier 2 questions and said "go".

Phrase matching rule: autonomy phrases must be standalone statements or sentence-initial. They do
NOT match when embedded in descriptive text ("just do the simple version" is not autonomy).

What autonomy means: all tiers collapse to Tier 0 for the current task chain; clarification
and routing summaries are skipped.

What autonomy does NOT override: the "ENTER EXECUTE MODE" approval gate, plan review checkpoint,
phase-program phase boundaries, and high-risk execution handoff gates.
- Subagent delegation (no-inline-execution) and the ban on direct orchestrator artifact writes remain mandatory under autonomy — autonomy removes approval pauses ONLY.

Exception: Autopilot Mode — the consolidated clarification round replaces the ENTER EXECUTE MODE
gate. See §Autopilot Trigger Routing.

**Autopilot Mode — Standing ENTER EXECUTE MODE Consent**
When a user triggers Autopilot Mode (via recognized phrase — see §Autopilot Trigger Routing),
the consolidated clarification round constitutes standing consent for ENTER EXECUTE MODE for the
duration of that run. The orchestrator does NOT issue a separate ENTER EXECUTE MODE prompt. The
EXECUTE CONSENT field in the provisional goal block records this consent explicitly.

This rule applies only to the current autopilot run. It does not persist across sessions unless
the provisional goal block (or its UPDATE variant) is re-pasted.

Full specification: `process/development-protocols/autopilot.md` §ENTER EXECUTE MODE Consent.

### Intent Revalidation After Research

After the research-agent completes, the orchestrator checks whether the original intent still holds.
If research reveals the request is fundamentally different from what was assumed, re-present a
Tier 1 routing summary with updated understanding. If research confirms the original intent,
proceed to SPEC, INNOVATE, or PLAN without re-asking. Do not repeat clarification that was already resolved.

**SPEC handoff signals (outer/standalone flow):** RESEARCH advances to SPEC by `ENTER SPEC MODE`
(or "go"); `vc-spec-agent` emits `PHASE_COMPLETE: SPEC` when the locked `*_SPEC_*.md` requirements
doc is written, after which the orchestrator advances to INNOVATE. If the user's intent for the
requirements doc is ambiguous and cannot be resolved interactively, `vc-spec-agent` stops with
`SPEC_INTENT_BLOCKED`. The phase-program INNER loop skips SPEC entirely — RESEARCH advances
directly to INNOVATE there (`R → I → P → PVL → E → EVL → UP`).

### FAST Mode Integration

Intent clarification fires BEFORE the fast-mode agent is spawned. The orchestrator scores and
clarifies in the main thread, then hands the clarified intent to the fast-mode-agent prompt.
Inside the fast-mode-agent, no additional clarification is needed because the intent is already
resolved.

### Fallback: Still Ambiguous After Tier 2

1. State what remains unclear in one sentence.
2. Ask one final direct question (not multiple-choice, just a plain question).
3. If still unresolvable after that, default to the research-agent with the narrowest reasonable scope.

Never loop clarification more than twice. Two rounds max, then route to research.

Full scoring formula, tier workflows, and question menu: invoke `vc-intent-clarify`.

## Autopilot Trigger Routing

When an autopilot trigger phrase is detected (see §Intent Routing — Autopilot Mode Trigger),
the orchestrator follows this sequence regardless of the current RIPER-5 phase:

**Full canonical specification:** `process/development-protocols/autopilot.md`. The rules below
are summary pointers only — autopilot.md is the single source of truth. Do not duplicate the
full spec here.

### Step 1 — Lane Detection + Situation Review (before clarification)

**Lane suffix detection (runs FIRST, before standard phrase matching):** Check whether the user message begins with `autopilot quick:`, `autopilot fast:`, or `autopilot full:` (standalone or sentence-initial). When matched:
- Extract the task description after the colon (trim leading whitespace).
- Set the lane (`quick` / `fast` / `full`) for the CLR and the provisional goal block `LANE:` field.
- Continue the standard flow below (situation review → CLR).
When no suffix is found, lane defaults to `full` (standard autopilot behavior unchanged).

**Situation review:** Detect the current RIPER-5 phase from on-disk artifacts:
- Session start (no artifacts): entry phase = RESEARCH
- SPEC file present: entry phase = post-SPEC (skip RESEARCH and SPEC)
- Plan file present: entry phase = post-PLAN
- Validate contract present with PASS/CONDITIONAL: entry phase = post-VALIDATE
Read `process/development-protocols/autopilot.md` §Trigger-Anywhere Detection Flow for the full
artifact-to-phase mapping table.

### Step 2 — Consolidated Clarification Round (exactly once)
Issue exactly ONE structured clarification round using `AskUserQuestion`. This is the sole user
interaction before the autonomous run begins. It covers:
- Intent restatement
- Scope, hard-stop, and gate-deviation questions (all dimensions needed)
- Autonomy boundaries confirmation (vc-intent-clarify Dimension 6, treated as CRITICAL)
- Strategy options for the first remaining phase

After the user responds, the session is fully locked — no more questions during the run
(except the three hard stops listed in §Autopilot Hard Stops below).

### Step 3 — Provisional Goal Block Emission
Emit the provisional goal block (≤4000 chars) in chat immediately after clarification resolves.
The block is copy-pasteable for session resume.
Required fields: SESSION GOAL / ENTRY PHASE / REMAINING PHASES (checklist) / CLARIFICATIONS
LOCKED / EXECUTE CONSENT / DECISION POLICY / HARD STOPS / TEST GATES / START.
Read `process/development-protocols/autopilot.md` §Provisional Goal Block Format for field
definitions and the EXECUTE CONSENT field requirement.

### Step 4 — Autonomous Run
Drive the full remaining RIPER-5 phase sequence without user gates, per the decision policy in
the provisional goal block. Apply /goal autonomous execution rules from §Autonomous /goal Phase
Program Execution and §BLOCKED Escalation Path, plus the autopilot-specific gate policies in
`process/development-protocols/autopilot.md` §Autonomous Run Rules.

Emit the AUTOPILOT_ACTIVATED signal once immediately after the provisional goal block is printed:

```
AUTOPILOT_ACTIVATED: [task description] — entry phase: [phase] — goal block emitted
```

### Autopilot Hard Stops (these still surface for user input)
- Irreversible / outward-facing actions not in the validate-contract
- Live-provider billed feasibility probe (`cost-class: needs-live-provider`)
- Cascade BLOCKED (two consecutive phases BLOCKED with no intervening PASS)
High-risk evidence pack is also manual-first always — see §High-Risk Execution Handoff.

### Autopilot Deactivation
Autopilot mode deactivates when:
- The run completes normally (UPDATE PROCESS phase finishes)
- The user explicitly says "stop autopilot", "pause autopilot", "exit autonomous mode", or similar
- A hard stop is triggered and the user chooses not to resume
- The session ends (deactivation is per-session — re-paste the goal block from disk to resume)
On deactivation: return to standard interactive RIPER-5 behavior.

### V7 Goal Block Update
When VALIDATE V7 completes during an autopilot run, the orchestrator emits an `(UPDATE)`
variant of the provisional goal block with real test gate commands substituted for TBD
placeholders. The original provisional block is NOT modified (chat history is immutable).

### Re-paste for Session Resume
Pasting the provisional or UPDATE goal block into a new session resumes autopilot from the
phase named in the START field, with clarifications and decision policy already active.
No new clarification round is issued.

### Maintenance pointer
**Single source of truth for Autopilot Mode:** `process/development-protocols/autopilot.md`.
Orchestration.md carries summary rules and pointers only. For full spec, gate policy table,
provisional block format, and D1 validator contract: read autopilot.md directly.

## Parallel Fan-Out Checkpoints

At these phase transitions, consult `vc-agent-strategy-compare` for the full signal-based
fan-out scoring and strategy options:

1. After initial research identifies multiple directions
2. After innovate surfaces 4+ architectural approaches
3. After plan creation — see the VALIDATE Gate section below (replaces ad-hoc plan validation fan-out)
4. After phase-program plan set creation
5. After non-trivial EXECUTE completion, before closeout

The fan-out protocol uses the same signal-count scoring as drift scoring. It recommends
parallel subagents ONLY for fire-and-forget fan-out where agents never need to see each
other's work; it recommends an **agent team** (named teammates + shared task list: TeamCreate +
TaskCreate/TaskUpdate + Agent with team_name/name + SendMessage, tracked by TaskList) whenever
agents must coordinate mid-execution — e.g. keeping blast radii disjoint across phase plans.
Parallel subagents have NO inter-agent channel and CANNOT coordinate; never pick them for work
that needs coordination.

### Strategy Selection at Every Phase Step

At the END of every RIPER-5 phase step (research/innovate/plan/validate/execute/update-process),
the active agent invokes `vc-agent-strategy-compare` to recommend the execution strategy for the
NEXT phase step. This is not optional and not only at VALIDATE V4. Specifically:
- End of RESEARCH → strategy recommendation for SPEC
- End of SPEC → strategy recommendation for INNOVATE
- End of INNOVATE → strategy recommendation for PLAN
- End of PLAN → strategy recommendation for VALIDATE
- End of VALIDATE (V4) → strategy recommendation for EXECUTE
- End of EXECUTE → strategy recommendation for UPDATE PROCESS

The orchestrator reads this recommendation before spawning the next subagent.

For multi-phase programs: `vc-generate-phase-program` invokes `vc-agent-strategy-compare`
for each individual phase during scaffold (not once at program level).

During autonomous /goal execution: orchestrator reads the per-phase strategy recommendation
from the kickoff charter before spawning each phase's first subagent.

## Two-Tier Fan-Out Escalation

When parallel subagents are recommended, use the appropriate tier:

### Tier 1: Lightweight Parallel Subagents (Default)

- Spawns existing agents in parallel via the Agent tool
- Each agent works independently with no inter-agent communication
- Orchestrator collects all outputs and synthesizes them
- Use when: agents work on independent dimensions, directions, or review concerns

### Tier 2: vc-team (Escalation)

- Full Agent Teams with worktree isolation and inter-agent messaging
- Use when: agents need adversarial debate, cross-layer implementation touching the same files,
  or results that depend on each other
- Escalation trigger: if any parallel agent's output could conflict with or depend on another
  parallel agent's output, use vc-team instead of Tier 1
- Tier 2 is an **agent team** with the full machinery: TeamCreate provisions named teammates,
  each gets a TaskCreate assignment, they coordinate via SendMessage, and TaskList tracks
  in-flight work. Spawning bare parallel Agent calls and *calling* it a team is the failure mode
  this tier exists to prevent — without TeamCreate + SendMessage there is no team, only
  uncoordinated subagents.

When in doubt, start with Tier 1. The orchestrator can always escalate to vc-team if the first
round reveals inter-dependencies.

Full signal scoring and strategy options: invoke `vc-agent-strategy-compare`.

## VC-PREDICT-DEEP-NEEDED Signal Routing

When vc-innovate-agent emits `VC-PREDICT-DEEP-NEEDED: [surface/pattern] — pausing for research subagent`:

1. Spawn vc-research-agent scoped to the named surface/pattern.
2. Pass research findings back to vc-innovate-agent as `Prior Research: [findings]` context in a re-spawn.
3. Do NOT tick the INNOVATE phase complete — PHASE_COMPLETE: INNOVATE fires only after the re-spawn completes normally.
4. vc-research-agent will emit `VC-PREDICT-RESEARCH-COMPLETE: [surface/pattern] — findings ready for vc-innovate re-spawn` (NOT `PHASE_COMPLETE: RESEARCH`) when completing this scoped research. On receipt: extract the `Prior Research:` findings block and include it as context in the vc-innovate-agent re-spawn prompt.

Note: `PHASE_COMPLETE: RESEARCH` emitted from a VC-PREDICT-DEEP-NEEDED scoped session is not expected — the agent emits `VC-PREDICT-RESEARCH-COMPLETE` instead. If `PHASE_COMPLETE: RESEARCH` is received, treat it as VC-PREDICT-RESEARCH-COMPLETE (same routing: re-spawn vc-innovate-agent with findings, do NOT advance inner loop Step 1).

Note on state tracking under /goal: The orchestrator tracks active VC-PREDICT-DEEP-NEEDED state implicitly from conversation context — the signal `VC-PREDICT-DEEP-NEEDED: [surface/pattern]` appears in the current session before the scoped research agent is spawned. Under /goal autonomous execution: if session context is lost (compaction or restart), treat any RESEARCH-complete signal as a normal `PHASE_COMPLETE: RESEARCH` (safe default — tick Step 1 RESEARCH as complete, but do NOT tick Step 2 INNOVATE; re-run INNOVATE in the next session which will re-trigger vc-predict normally).

This signal is listed in behavior-reference Section 3 §[I3] and the Signal Inventory. INNOVATE does not self-spawn the research subagent — it emits the signal and halts, waiting for the orchestrator to coordinate.

## VC-FEASIBILITY-PROBE-NEEDED Signal Routing

When vc-spec-agent, vc-innovate-agent, OR vc-validate-agent (Layer 2) emits `VC-FEASIBILITY-PROBE-NEEDED: [hypothesis] — cost-class: [class]` and halts:

0. **Resolve the cost/safety gate FIRST** (from the declared `cost-class`):
   - `cheap-local` → proceed, no gate.
   - `needs-container` → vc-debugger must use a **disposable** container only; NEVER `docker exec` the shared dev container (`app-*`) or shared Postgres. If no disposable container is available, the verdict will be `INCONCLUSIVE`.
   - `needs-live-provider` → requires explicit **double opt-in** from the user before dispatching (billed/live 3rd-party call). Under /goal: do NOT auto-grant — surface the opt-in request; if not granted, the verdict is `INCONCLUSIVE`.
   - `needs-browser` / `needs-cf` → ensure a browser session / `wrangler dev` sandbox is available; never drive a shared user session or a deployed production worker.
   The cost class is the agent's best guess; vc-debugger finalizes and records the actual class in the VERDICT's `## Probe Cost Class` section.
1. Spawn `vc-debugger` with the `vc-feasibility-test` playbook context, the hypothesis text, the resolved cost class, and the active task folder path.
2. `vc-debugger` runs the empirical probe and writes the VERDICT artifact: `{task_folder}/{slug}_FEASIBILITY_{dd-mm-yy}.md`.
3. `vc-debugger` emits `VC-FEASIBILITY-VERDICT-READY: [verdict keyword] — [full VERDICT file path]` (NOT `PHASE_COMPLETE:` — the emitting phase is NOT complete yet).
4. On receipt of `VC-FEASIBILITY-VERDICT-READY`: orchestrator reads the VERDICT file, extracts the `Prior Feasibility:` summary block, and re-spawns the emitting phase agent.
5. Re-spawn prompt includes: `Prior Feasibility: [hypothesis] — verdict: [VIABLE|NOT-VIABLE|INCONCLUSIVE] — licenses: [What this licenses] — forbids: [What this forbids] — uncertain: [What remains uncertain (known-gap)]` (the three lines verbatim from the VERDICT's `## Resulting Design Constraint` section).
6. Do NOT tick the emitting phase complete — PHASE_COMPLETE: SPEC, PHASE_COMPLETE: INNOVATE, or PHASE_COMPLETE: VALIDATE fires only after the re-spawn completes normally.

**Required Prior Feasibility density:** The orchestrator MUST pass AT MINIMUM: the original hypothesis text + the verdict keyword (VIABLE / NOT-VIABLE / INCONCLUSIVE) + the verbatim three-part `Resulting Design Constraint` (What this licenses / What this forbids / What remains uncertain). Passing only the verdict keyword without all three constraint parts violates the signal contract — the re-spawned agent needs `licenses` to lock the approach, `forbids` to reject dead ends, and `uncertain` to carry forward the known-gap.

Example re-spawn block:
```
Prior Feasibility: Does the gateway forward params.provider.sort? — verdict: NOT-VIABLE — licenses: Designs may rely on params.model and params.messages reaching the gateway unchanged. — forbids: Do not design any approach that depends on params.provider.sort being forwarded; the forwarding layer strips it. — uncertain: Whether params.provider.order survives is untested — treat as a known-gap until probed.
```

**Structural difference from VC-PREDICT-DEEP-NEEDED:**
- VC-PREDICT-DEEP-NEEDED spawns `vc-research-agent` for deeper context; VC-FEASIBILITY-PROBE-NEEDED spawns `vc-debugger` for an empirical probe.
- VC-PREDICT-DEEP-NEEDED produces research findings; VC-FEASIBILITY-PROBE-NEEDED produces a one-shot VERDICT artifact with a structured verdict and design constraint.
- VC-FEASIBILITY-PROBE-NEEDED can fire from SPEC (vc-spec-agent), INNOVATE (vc-innovate-agent), OR VALIDATE Layer 2 (vc-validate-agent dimension agents); VC-PREDICT-DEEP-NEEDED fires only from INNOVATE.
- When VALIDATE Layer 2 emits a probe: the orchestrator waits for ALL Layer 2 agents in the current V2 pass to complete (or emit a probe), then VALIDATE halts at the END of V2 before V3 synthesis. Multiple simultaneous probes from one V2 pass are batched; orchestrator resolves them (parallel where cost-class permits) and re-spawns vc-validate-agent ONCE with multiple `Prior Feasibility:` blocks.

**Under /goal autonomous execution:** The orchestrator routes `VC-FEASIBILITY-PROBE-NEEDED` without user input. Spawn vc-debugger, await `VC-FEASIBILITY-VERDICT-READY`, extract Prior Feasibility block, re-spawn the emitting agent. This is non-blocking in /goal context.

This signal is listed in `12-reference.md` §Signal Inventory. The emitting agent does not self-spawn the probe — it emits and halts, waiting for orchestrator coordination.

## QUICK FIX Lane

A deliberately light lane for small, low-risk fixes where full RIPER-5 (research-agent → plan →
validate → execute → tester) is disproportionate. It is lighter than FAST MODE: FAST MODE still
writes a plan file, writes a validate-contract, and pauses after VALIDATE; the QUICK FIX lane writes
neither artifact and runs no EVL. It covers the band *above* a trivial single-file edit but *below*
"needs a plan."

**Trigger:** `ENTER QUICK FIX MODE`, or intent keywords ("quick fix", "hotfix", "small fix",
"just patch"). Distinct from the **Trivial Fix** route (single-file, <15 lines → straight to
`vc-execute-agent`, no scout): QUICK FIX adds a cheap scout + confirm and allows multi-line / multi-file
edits within a small bounded scope.

**Protocol (orchestrator-driven — preserves §PVL/EVL "no inline execution"):**

1. **Read-only scout.** The orchestrator locates the gap with Grep/Read/Glob and drafts the exact
   edit. Reading inline is allowed; only *editing source* and *running gate commands* inline are
   forbidden. This replaces a full `vc-research-agent` spawn for small fixes.
2. **One-line confirm.** Emit `Quick fix: edit \`path:line\` — [what] to [why]. Proceed?` and wait.
   Under a standing `/goal`, auto-proceed (no user gate) unless the scope guard trips.
3. **One spawn.** Spawn `vc-quick-fix-agent` (opus) with the exact target (file + line + change). The
   agent re-checks scope, applies the edit, and runs a **scoped check on touched files only** —
   typecheck of the touched package and/or the single covering test file. It does NOT run the full
   suite and the orchestrator does NOT spawn `vc-tester` / run EVL.
4. **No plan file, no validate-contract, no EVL, no UPDATE PROCESS.** The orchestrator may still
   recommend a commit (via `vc-git-manager`) when the user asks.

**Scope guard (mandatory — the lane is VOID otherwise):** abort to full RESEARCH if the change
touches schema, auth, API contract, billing/credits, or migration surfaces, introduces a new
dependency/agent/runtime surface, spans multiple feature areas, or exceeds a small bounded size
(~100 lines). `vc-quick-fix-agent` emits `QUICK_FIX_ABORT: [target] — out of quick-fix scope
([reason]); route to RESEARCH.` and returns `BLOCKED`; on receipt the orchestrator re-routes to
`vc-research-agent`. **Exception — active autopilot lane:** under an active autopilot goal block, `QUICK_FIX_ABORT` instead escalates one lane up (quick → fast) per `autopilot.md` §Lanes — clarifications carry over, the orchestrator emits the one-line `escalated to fast: [reason]` notice, and does NOT re-route to RESEARCH. When unsure whether something qualifies, it does not — use RIPER-5.

**Why this is still no-inline-execution-compliant:** the orchestrator never edits source files and
never runs the scoped check itself — the spawned `vc-quick-fix-agent` does both. The orchestrator's
inline work is read-only scouting plus the confirm. An edit applied by the orchestrator in its own
shell remains a protocol violation here as everywhere else.

## VALIDATE Gate

VALIDATE is a mandatory phase between PLAN and EXECUTE (outer sequence: R → S → I → P → V → E; the phase-program INNER loop skips SPEC: R → I → P → PVL → E → EVL → UP).

### When VALIDATE runs

After `vc-plan-agent` creates or updates a plan file, before routing to `vc-execute-agent`.

### Skip conditions

VALIDATE may be skipped when ALL of the following are true:

1. The change is a single-file edit under 15 lines with no schema, auth, API, or billing surface
2. No new dependencies, agents, or runtime surfaces are introduced
3. The user explicitly skips with a stated reason ("skip VALIDATE — trivial rename")
4. Existing `## Validate Contract` with PASS gate — ask user: "Plan has an existing PASS validate-contract. Re-validate or proceed to EXECUTE?" Under /goal: if `## Inner Loop Refresh Note` exists in the plan file with a date newer than the existing validate-contract date → re-run PVL from V1; if no Refresh Note is found (or Refresh Note date ≤ contract date) → auto-proceed to EXECUTE (vc-validate-agent V1 will independently confirm via the same Refresh Note check). Do not use contract origin (outer vs inner) as the routing signal — the Refresh Note date is the authoritative trigger. **When the auto-proceed path fires, the orchestrator MUST relay the `V1 AUTO-PROCEED: ...` line verbatim in its own chat response — the literal token must appear in the main thread, not only inside the subagent transcript.**

When VALIDATE is skipped, note the skip reason in the plan file or handoff prompt. A plan without
a validate-contract must document why VALIDATE was skipped.

### What to pass to execute-agent after VALIDATE

When routing to vc-execute-agent after VALIDATE completes:
- Pass the validate-contract section path or note "inline in plan"
- Pass the gate status (PASS or CONDITIONAL) and any accepted concerns
- Pass the test gate commands from the validate-contract so execute-agent knows which tier to run

### Gate verdicts

- **PASS** — no FAILs and no unresolved CONCERNs. Proceed to EXECUTE.
- **CONDITIONAL** — one or more CONCERNs exist, but the user has reviewed and accepted the
  documented gaps. Proceed to EXECUTE with those gaps on record.
- **BLOCKED** — unresolved FAILs. Return to PLAN. Do not route to vc-execute-agent.

### BLOCKED Escalation Path

1. vc-validate-agent surfaces FAIL gap list.
2. Orchestrator invokes plan-validate-fix loop (vc-plan-agent supplements checklist addressing FAIL gaps); PVL re-runs from V1. Plan-agent emits `SUPPLEMENT_APPLIED: [plan path] — [N] gap(s) addressed` when supplement is complete. Orchestrator reacts: re-run PVL from V1. (Full SUPPLEMENT_APPLIED definition: behavior-reference Section 5 V7.)
3. If still BLOCKED after validate-fix loop: surface FAIL list to user with one-time choice: (a) revise plan further / (b) descope blocked items / (c) accept as CONDITIONAL.
4. If second validate also BLOCKED after user choice: orchestrator stops and asks user whether to continue or defer to backlog.
5. **Supplement cycle limit: 10 cycles maximum** (matching PVL supplement limit in behavior reference).
6. **Under /goal autonomous execution:** BLOCKED →
   1. Write backlog NOTE for blocked gaps.
   2. Append `status: BLOCKED-skipped — blast-radius claim unresolved; files never modified` to the phase's entry in `phase-blast-radius-registry.md` (if registry exists). Registry path (FLAT, inside the program task folder): `process/features/{feature}/active/{program-slug}_{date}/phase-blast-radius-registry.md` for feature-scoped programs, or `process/general-plans/active/{program-slug}_{date}/phase-blast-radius-registry.md` for general-plans programs. Use same path routing as the phase plan files (one registry per program folder).
   3. Continue to remaining phases without user input.

   **Step-class distinction:** The above applies to PVL BLOCKED (Step 4). For BLOCKED at R, I, plan-validate-fix, EXECUTE, EVL, or UPDATE PROCESS step types, see behavior-reference Section 8 `What Moves Forward Without User Input` §NEEDS_CONTEXT step-class rule.

   Under /goal inner PVL (Step 4): vc-validate-agent emits `PHASE_SKIPPED: BLOCKED — [phase N] backlog note written; advancing to Phase [N+1]`. Orchestrator detects this signal and advances Phase Loop Progress without waiting for PHASE_COMPLETE: VALIDATE.

   **Registry status vocabulary reminder:** writable values are `BLOCKED-skipped / DONE / SUPERSEDED / (no field)`. `status: BLOCKED` is a read-compatibility alias only — never write it in new entries; always write `status: BLOCKED-skipped`. See behavior-reference Section 8 §Valid status values for the complete vocabulary.

   Under /goal: step-class rules apply — behavior differs by which phase step the BLOCKED came from. See behavior-reference Section 8 §Step-class rule for full details (this rule applies to BLOCKED, NEEDS_CONTEXT, and CONTEXT_PARTIAL status codes at a given step — not only NEEDS_CONTEXT). For BLOCKED status at Steps 1-3, apply the same step-class rule as NEEDS_CONTEXT — see behavior-reference Section 8 §Step-class rule. Summary:
   - Steps 1-3 (R, I, plan-validate-fix) BLOCKED → `CONTEXT_PARTIAL` warning + continue with degraded quality
   - Step 4 (PVL) BLOCKED → skip entire phase + write backlog note
   - Step 5 (EXECUTE) BLOCKED → treat as EVL L1 failure + create follow-up plan stub
   - Steps 6-7 (EVL, UP) BLOCKED → continue with note; EVL can run partially

> **Escalation path differs by execution context:**
> - **Outside /goal:** Step 3 (user surface) fires at cycle 2. Step 4 (escalate-or-backlog) fires at cycle 3. Stop.
> - **Under /goal:** Step 3 user-surface is bypassed. Supplement cycles auto-continue. 10-cycle limit triggers user gate (cost-safety override).

Cascade BLOCKED (phase program hard stop): for consecutive BLOCKED phases in a phase program, see behavior-reference Section 8 §Cascade BLOCKED Protocol — this triggers a program-level hard stop distinct from standard single-phase BLOCKED escalation. The cascade check fires at Step 4 inner PVL when two consecutive phases in the registry are both BLOCKED-skipped.

## PHASE_RESTRUCTURE_NOTICE and CASCADE_BLOCKED Routing

**PHASE_RESTRUCTURE_NOTICE** (emitted by orchestrator from RESEARCH findings, or by vc-execute-agent mid-EXECUTE under /goal): treat as audit trail only — no agent spawn, no inner loop step advancement. Consume from the phase report.

**CASCADE_BLOCKED** (two consecutive phases BLOCKED in a phase program): this is a program-level hard stop. See behavior-reference Section 8 §Cascade BLOCKED Protocol for the full protocol — this is distinct from standard BLOCKED escalation and requires user input before continuing.

### Validate-Contract Required Fields

Every validate-contract written by `vc-validate-agent` MUST include a `generated-by:` field. Valid values:
- `generated-by: outer-pvl` — contract produced during the outer RIPER-5 loop (before inner-loop R+I have run for this phase)
- `generated-by: inner-pvl: phase-N` — contract produced during the inner-loop PVL pass for phase N

This field distinguishes outer-loop contracts from inner-loop contracts and drives the pre-routing re-validation decision (see Phase Program Pre-Routing Check Step 4b below).

`date: [YYYY-MM-DD]` — lowercase, machine-parseable. Same value as the display `Date:` field written at V6. Required for supersedes chain ordering by vc-plan-discovery and D2 validators. See behavior-reference Section 5 V6 for the complete required fields list.

Full V1-V7 sequence and validate-contract schema: invoke `vc-validate-findings` and
`vc-test-coverage-plan`.

## Plain-Language Gate Rendering

Required field names and signal strings (PHASE_COMPLETE:, Gate: PASS, SUPPLEMENT_APPLIED:, etc.) are verbatim anchors — do not change them. The surrounding prose can be as plain as the audience needs.

### PVL prompt (suggested plain rendering)

When asking the user whether to run the plan-validate loop automatically or step by step, use wording like:

> "Ready to check the plan. How would you like to proceed?
> (a) Automatic — I find issues, fix them, and re-check on my own, up to 10 tries.
> (b) Step-by-step — I show you each issue and wait for your approval before fixing."

Under a standing /goal the answer is always (a); no prompt is needed.

### EVL confirmation run message (suggested plain rendering)

When the orchestrator starts the execute-validate loop after EXECUTE, use wording like:

> "EXECUTE reported done. Running the gate tests independently to confirm everything is green — this is a required check, not optional, even when execute-agent said all gates passed."

### Hard rule: signal strings stay verbatim

Phase-end gate messages (`PHASE_COMPLETE: EXECUTE`, `Gate: PASS`, `Gate: CONDITIONAL`, `Gate: BLOCKED`, `SUPPLEMENT_APPLIED:`, `QUICK_FIX_ABORT:`) are signal strings the orchestrator matches exactly. They must appear word-for-word. Only the human-readable sentences around them may be reworded.

## Mode Detection — VALIDATE Trigger

After `vc-plan-agent` creates a plan file, the orchestrator auto-suggests VALIDATE before
routing to `vc-execute-agent`:

> "Plan complete. Run VALIDATE before EXECUTE? (recommended) — say ENTER VALIDATE MODE or skip with reason."

This auto-suggestion fires after every new plan file is created. It does not fire when:
- The plan already has a `## Validate Contract` section **AND** no `## Inner Loop Refresh Note` with a date newer than the validate-contract date exists (inner R+I has NOT run since the last contract was written). If a newer `## Inner Loop Refresh Note` exists: auto-suggest VALIDATE regardless of whether a contract already exists.
- The user has already said "skip VALIDATE" with a stated reason
- The change is trivially single-file (under 15 lines, no surface changes)

**Advisory:** Even when the skip condition appears satisfied, prefer routing to vc-validate-agent and letting V1 make the final auto-proceed decision via fresh file scan (V1 checks for newer Inner Loop Refresh Notes itself). The orchestrator's pre-routing check is based on cached state and may be stale. Never skip spawning vc-validate-agent solely based on the orchestrator's cached view.

If the user says "ENTER EXECUTE MODE" immediately after PLAN without having done VALIDATE and without a stated skip reason, the orchestrator must ask once: "Did you mean to skip VALIDATE? If so, say why (e.g. trivial change, already validated). Otherwise say ENTER VALIDATE MODE." Do not route to execute-agent until one of the above conditions is met.

## Gather Context for Execute and Tester

ALWAYS pass `process/context/all-context.md` (the root context router) AND run
`find process/context/ -type f` to produce a full recursive listing of all files under
`process/context/` when routing to `vc-execute-agent` or `vc-tester`.

Agents read the router, see all available files, then follow the routing table to decide
which to load. Do not hardcode specific deeper file paths — the router plus full file listing
is the stable contract.

Note: protocol files in `process/development-protocols/` are NOT under `process/context/`.
Agents needing `orchestration.md`, `plan-lifecycle.md`, or `phase-programs.md` must be
explicitly told to read them — they are not discoverable via the context router alone.

## Approval Gates Still Apply in Parallel

- `ENTER EXECUTE MODE` remains mandatory before substantial implementation work, even when `team` or FAST mode is used.
- A helper/orchestration skill may coordinate the work, but it does not become an alternate workflow owner.
- If the selected plan is a legacy multi-file structure, the orchestrator must still choose one primary plan file path and pass any supporting phase files explicitly.

## Post-EXECUTE Cleanup Checkpoint

After any non-trivial EXECUTE completion, the orchestrator must surface an explicit cleanup checkpoint before simply moving on.

The checkpoint should not be a vague "want cleanup?" prompt. It should include a short closeout
packet so the user can approve the next move quickly.

Full closeout packet schema, drift scoring, and move-on examples: invoke `vc-generate-closeout`.

Required closeout choices:

1. `ENTER UPDATE PROCESS MODE` when the selected plan is explicitly classified `Ready for UPDATE PROCESS archival` or when context/process reconciliation is needed.
2. Keep the selected plan in `active/` when implementation is code-complete but testing, manual verification, or user confirmation is still pending.
3. Return to PLAN when material deviations mean the selected plan no longer matches the implemented reality.

Rules:

- Keep the selected plan file path explicit in the closeout summary.
- Do not auto-transition into UPDATE PROCESS.
- Do not auto-archive a plan without a user-visible action.
- Do automatically recommend the next valid state when it is clear from the selected plan and latest verification.
- Do explicitly recommend a commit checkpoint when a selected phase is well-tested and validated.
- If cleanup/context capture is the only remaining safe action, say that directly instead of ending with a generic summary.
- If cleanup was skipped and active-plan debt accumulates, recommend `vc-audit-plans` as a maintenance follow-up.

## High-Risk Execution Handoff

When substantial implementation touches a high-risk class, the orchestrator should require a manual-first evidence handoff before treating the work as ready for finalize or review closure.

High-risk classes:

- auth or identity
- billing or credits
- schema/data migration or destructive data mutation
- public API contract changes
- deploy/runtime/container/proxy/gateway changes
- permission, secret, or trust-boundary logic

Controller rules:

1. Note the risk class in the task summary or selected plan context.
2–4. Full 5-artifact schema and auto-stop rule: invoke `vc-risk-evidence-pack`.
5. Keep this manual-first. Do not invent a blocking hook or alternate workflow owner.

## Research First for Service-Shaped Features

When a user proposes a new server, daemon, sidecar, agent, worker, or background process, route to research first before innovate or plan.

Research must check:

- existing analogous services in `packages/api/src/infra/` or `apps/`
- current deploy and bundling patterns
- current env and secret wiring patterns

## PVL/EVL Loop Routing (Orchestrator Is the Loop Driver)

Subagents are fire-and-forget: they emit a verdict and terminate. NO subagent can self-loop or spawn another phase agent — any instruction that reads as "the agent continues in the same session" is void. The ORCHESTRATOR drives both fix loops by re-spawning agents, and the ORCHESTRATOR executes the `vc-autoresearch` bookkeeping at every cycle boundary (Step 0 init, per-cycle iteration report, TSV row, plateau/cap/regression checks). "The loop is run by vc-autoresearch as bookkeeper" means: the orchestrator runs those steps itself — no agent performs them implicitly.

### PVL routing (plan-validate-fix)

On receiving vc-validate-agent's V7 verdict, route mechanically:

| Verdict received | Orchestrator action |
|---|---|
| `Gate: PASS` | Verify `grep -c 'Gate: PASS' <plan-file>` ≥ 1 → proceed toward EXECUTE (emit /goal block first). Append final TSV row (`loop_status: HALTED_SUCCESS`). |
| `Gate: CONDITIONAL`, first pass (no cycle row in `results.tsv` beyond baseline, or no TSV yet) | NOT terminal — never route to EXECUTE. Run bookkeeping Step 0 if needed (create task-folder `results.tsv` with header + baseline). Spawn vc-plan-agent (PVL-supplement mode) passing the SUPPLEMENT REQUEST block. **`PHASE_COMPLETE: VALIDATE` MUST NOT be emitted here — a first-pass `Gate: CONDITIONAL` (or `Gate: BLOCKED`) is never terminal. `PHASE_COMPLETE: VALIDATE` is only valid after `Gate: PASS` or after explicit user/known-gap acceptance of a CONDITIONAL that has completed at least one supplement cycle.** |
| `SUPPLEMENT_APPLIED: [plan path] — [N] gap(s) addressed` (from vc-plan-agent) | One PVL cycle completes: increment cycle counter; write `{plan-slug}-pvl-iteration-{NNN}_REPORT_{dd-mm-yy}.md`; append TSV row; re-spawn vc-validate-agent from V1 with the updated plan. |
| `Gate: CONDITIONAL` after N≥1 cycles | Check plateau (3 cycles without gap-count improvement) and cap (10 cycles). Neither hit → run another supplement cycle. Plateau/cap hit → surface to user (non-/goal) or accept remaining gaps as known-gaps (/goal); only then is EXECUTE legal. |
| `Gate: BLOCKED` | §BLOCKED Escalation Path below — supplement cycles count toward the same 10-cycle cap. |
| `VC-FEASIBILITY-PROBE-NEEDED` from Layer 2 (during V2 fan-out) | Wait for ALL Layer 2 agents to complete (or emit probe). Then: resolve cost-class gate (see §VC-FEASIBILITY-PROBE-NEEDED Signal Routing step 0). Spawn `vc-debugger` per probe. Await `VC-FEASIBILITY-VERDICT-READY` for each. Batch multiple probes: re-spawn `vc-validate-agent` ONCE from V1 with all `Prior Feasibility:` blocks. **No TSV row written. No PVL cycle counter incremented.** Validate-contract is NOT written during probe halt; "no contract + VC-FEASIBILITY-PROBE-NEEDED signal" IS the routing signal. |

**Mechanical gate before spawning vc-execute-agent (always run):** `grep -c 'Gate: PASS' <plan-file>` ≥ 1 OR `wc -l < {task_folder}/results.tsv` ≥ 3 (header + baseline + ≥1 cycle row) OR explicit user acceptance of CONDITIONAL gaps quoted in this session. None hold → do NOT spawn vc-execute-agent.

### EVL routing (execute-validate-fix)

On receiving `PHASE_COMPLETE: EXECUTE` (under /goal) or DONE/DONE_WITH_CONCERNS (interactive):

| Event | Orchestrator action |
|---|---|
| EXECUTE reports done — gates claimed green or not | ALWAYS spawn vc-tester for the EVL confirmation run: re-run the EXACT validate-contract gate commands. Execute-agent's internal iterate-until-green loop NEVER substitutes for this independent confirmation. Run bookkeeping Step 0 (ensure `results.tsv` baseline exists). |
| vc-tester: all gates pass | Append TSV row (`HALTED_SUCCESS`); continue EVL Steps → EVL HANDOFF SUMMARY → vc-update-process-agent. |
| vc-tester: ≥1 gate fails | One EVL cycle begins: increment cycle counter; **write `{plan-slug}-evl-iteration-{NNN}_REPORT_{dd-mm-yy}.md` FIRST — a TSV cycle row append is valid ONLY AFTER the matching iteration report file has been written (report first, TSV row second; a TSV row without its report is a bookkeeping violation)**; append TSV row; spawn vc-execute-agent (supplement mode) scoped to exactly the failing gate(s) — parallel fix agents when failing gates touch disjoint file groups; then re-spawn vc-tester to confirm. |
| 10 cycles reached or plateau | Under /goal: accept as known-gap, record in the phase report's `## Test Infra Gaps Found`, continue. Interactive: surface to user. |

**No inline execution (mechanical rule):** under `ENTER EXECUTE MODE` and throughout EVL, the orchestrator NEVER edits source files and NEVER runs validate-contract gate commands in its own shell. The gate run is valid ONLY when performed by a spawned vc-tester agent; the fix is valid ONLY when performed by a spawned vc-execute-agent. This holds regardless of change size — a one-line fix still requires the spawns. The trivial-fix inline path is VOID the moment a plan file with a validate-contract exists: "ENTER EXECUTE MODE for [plan]" ALWAYS means spawn vc-execute-agent with the plan path. An EXECUTE/EVL pass with zero Agent tool spawns is a protocol violation even if every gate ends green and all bookkeeping artifacts are correct — correct artifacts do not retroactively legitimize inline execution.

### Bookkeeping ownership (per `vc-autoresearch`)

| Item | Owner |
|---|---|
| Task-folder + `results.tsv` init, cycle counter, per-cycle `{NNN}` iteration reports, TSV rows, plateau/cap/regression checks, parallel-fix partitioning | Orchestrator (executing the vc-autoresearch steps directly) |
| V1–V7 gate sequence, SUPPLEMENT REQUEST format, validate-contract write, known-gap exclusion | vc-validate-agent |
| Which gate commands run, EVL HANDOFF SUMMARY format | vc-tester |
| Applying plan supplements / code fixes (scoped, no expansion) | vc-plan-agent / vc-execute-agent in supplement mode |

## EXECUTE-VALIDATE-LOOP (EVL)

**Owner:** orchestrator (loop COORDINATION runs in main thread, not delegated to a subagent — but the work inside the loop is still spawned: gate confirmation = vc-tester spawn; fixes = vc-execute-agent spawn. "Owner" never licenses the orchestrator to run gates or edit files itself; see §No inline execution above).
**Trigger:** execute-agent reports DONE or DONE_WITH_CONCERNS.
**Full spec:** behavior-reference Section 6.

Under /goal: canonical detection trigger is the `PHASE_COMPLETE: EXECUTE — ...` signal string emitted by execute-agent. The DONE/DONE_WITH_CONCERNS status code alone is insufficient under /goal because other agents also return DONE — the signal string is unambiguous. Both mechanisms are valid: signal string for /goal autonomous runs; status code for interactive sessions.

**Orchestrator EVL responsibilities (summary):**
1. Run EVL Steps 1–6 in the main thread.
2. At Step 6: write the EVL HANDOFF SUMMARY yaml block (6 fields: gates_green, known_gaps, follow_up_stubs, context_partial, preliminary_packet_path, closeout_classification).
3. Route to vc-update-process-agent with the EVL HANDOFF SUMMARY block in the handoff prompt.
4. Under /goal: all EVL steps are autonomous (no user gate) unless a EVL gate cannot be resolved after 10 execute-validate-fix loops — matching the behavior-reference Section 6 canonical cap. After 10 cycles: accept the gap as a known-gap, record in the phase report's ## Test Infra Gaps Found section, and continue.

**Loop bookkeeping (vc-autoresearch):** the execute-validate-fix loop is run by the `vc-autoresearch` skill (`domain: tests`) as its shared bookkeeper — it owns the iteration counter, plateau/regression detection, the TSV log, and the 10-cycle cap. vc-tester owns which validate-contract gate commands to run; orchestrator owns routing. When multiple independent gates fail across non-overlapping file groups, the orchestrator spawns **multiple parallel execute-fix agents** (vc-execute-agent in supplement mode), one per failing gate / file group, partitioned so no two agents edit the same file; when failing gates share files or a single root cause, fall back to a single execute-fix agent. See `.claude/skills/vc-autoresearch/SKILL.md` §EVL Wiring. **The ORCHESTRATOR executes this bookkeeping itself at every cycle boundary — no agent runs it implicitly; per-event routing table: §PVL/EVL Loop Routing.**

Under /goal autonomous execution: orchestrator emits and records `PHASE_COMPLETE: EVL — EVL HANDOFF SUMMARY emitted; preliminary packet written` to advance from Step 6 → Step 7 (UPDATE PROCESS).

**PHASE_COMPLETE: UPDATE PROCESS** — emitted by vc-update-process-agent when the phase closeout is complete. Format: `PHASE_COMPLETE: UPDATE PROCESS — [phase name] archived; phase report written; process commit invoked. Proceed to next phase Step 0.`

Orchestrator reaction: tick Step 7 (UPDATE PROCESS) checkbox → advance to Phase N+1 Step 0. Note: orchestrator matches on prefix `PHASE_COMPLETE: UPDATE PROCESS` — the suffix fields are informational and non-strict. Full spec in behavior-reference Section 7.

This section closes the F2 gap documented in behavior-reference Section 6.

## Regression Gate Validators

The core validator suite runs after every phase that touches harness artifacts:

```
node .claude/skills/vc-audit-vc/scripts/validate-agent-parity.mjs
node .claude/skills/vc-audit-vc/scripts/validate-skills.mjs
node .claude/skills/vc-audit-vc/scripts/validate-kit-portability.mjs
node .claude/skills/vc-audit-context/scripts/validate-context-discovery.mjs
node .claude/skills/vc-audit-plans/scripts/validate-plan-inventory.mjs     # (also conditional: run when plan inventory changed)
node .claude/skills/vc-audit-vc/scripts/validate-guide-sync.mjs
node .claude/skills/vc-audit-vc/scripts/validate-protocol-wiring.mjs
node .claude/skills/vc-audit-vc/scripts/validate-skill-invocation-wiring.mjs
node .claude/skills/vc-audit-vc/scripts/validate-agent-frontmatter.mjs
git diff --check                                                             # (merge-conflict marker check)
```

These additional validators are available for phase programs and plan artifact quality checks:

```
node .claude/skills/vc-generate-plan/scripts/validate-plan-artifact.mjs <plan.md>      # direct plan structure
node .claude/skills/vc-generate-phase-program/scripts/validate-umbrella-artifact.mjs <umbrella-plan.md>   # umbrella plan structure
node .claude/skills/vc-generate-phase-program/scripts/validate-phase-stub.mjs <phase-plan.md>             # phase stub structure
```

Run `validate-umbrella-artifact.mjs` after creating a new program umbrella plan. Run `validate-phase-stub.mjs` after generating phase stubs. These are not part of the core 5-validator suite but should be run by execute-agents operating within a phase program.

For VPS host or per-instance Docker operations specifically, inspect `WorkerNode` methods in `packages/api/src/infra/index.ts` before proposing a new host-side service. If a `WorkerNode` method already covers the operation, adding a new sidecar or host service is probably the wrong design.

## Intent Routing

The orchestrator's full request-routing logic. CLAUDE.md `## Routing` is a terse pointer to this
section; the authoritative detail lives here.

### Auto-Detection Patterns (summary)

- Feature requests → Step 0 skill discovery → vc-research-agent → SPEC → INNOVATE → PLAN → VALIDATE → EXECUTE
- Questions → vc-research-agent (non-trivial) or direct answer (trivial conceptual)
- Trivial fixes → vc-execute-agent directly (no plan required)
- Bug/debug → vc-debugger as default owner; helper skills like `vc-scout`, `vc-sequential-thinking`, and `vc-problem-solving` may assist
- UI/frontend → surface vc-frontend-design skill + vc-research-agent
- Refactor/simplify → vc-code-simplifier (pure style) or RESEARCH→PLAN→EXECUTE (behavioral)
- Missing context → suggest the `vc-generate-context` skill
- Existing plan file → scan process/general-plans/active/ and process/features/*/active/ (plans inside `{slug}_{date}/` task subfolders), confirm with user, resume from last phase

**Intent clarification**: Before auto-routing, the orchestrator scores request ambiguity per
`vc-intent-clarify` (see §Intent Clarification). Clear requests (score 0-1) auto-route silently.
Ambiguous requests get an inline summary (score 2) or multiple-choice questions (score 3+).

### 0. Skill Discovery (Do This First)

Before routing, run `node .claude/skills/vc-context-discovery/scripts/discover-skills.mjs` (reads
the generated skills catalog inventory) to list every skill grouped by layer with its
trigger keywords. Match keywords from the user request to surface relevant skills, and attach
candidate skill names to the subagent prompt.

**Rule:** When 1+ skills match the request, mention them to the user OR include them in the subagent
prompt context. Never silently skip relevant skills.

### 1. Detect Intent

- **Autopilot Mode Trigger** (keywords: "run autopilot", "full autopilot", "yolo autopilot",
  "autonomous mode", "/autopilot", "autopilot on [task]", "autopilot mode", "ENTER AUTOPILOT MODE";
  **lane-suffix variants**: `autopilot quick: [task]`, `autopilot fast: [task]`, `autopilot full: [task]`)
  → Trigger-anywhere routing: see §Autopilot Trigger Routing.
  → Detection rule: phrase must be standalone or sentence-initial. Phrases embedded in
    descriptive text ("the autopilot system is broken") do NOT trigger autopilot mode.
    Lane suffix variants follow the same rule ("just use autopilot fast: approach" does NOT trigger).
    Matching rule mirrors the Autonomy phrase-matching rule in §Intent Clarification §Autonomy Mode.
  → Full lane spec: `process/development-protocols/autopilot.md §Lanes`.

- **Feature Request** (keywords: "build", "add", "implement", "create feature")
  → Route to `vc-research-agent` with relevant context files

- **Question / Understanding Request**
  → Non-trivial: route to `vc-research-agent`. Trivial conceptual questions ("What is X?") may be answered directly by the orchestrator.

- **Trivial Fix**
  → Delegate lightweight quick-fix to `vc-execute-agent` (no plan file required).
  **Trivial definition:** Single-file change, no new dependencies, no schema/API/auth changes, under 15 lines, no security surface. Anything else is non-trivial.

- **Quick Fix** (keywords: "quick fix", "hotfix", "small fix", "just patch", or `ENTER QUICK FIX MODE`)
  → Run the QUICK FIX lane (see §QUICK FIX Lane): orchestrator read-only scout → one-line confirm →
  spawn `vc-quick-fix-agent`. Use for the band *above* trivial (multi-line / known target) but
  *below* "needs a plan" — bounded, no schema/auth/API/billing/migration surface. Aborts to RESEARCH
  if the scope guard trips.

- **Missing Context**
  → Suggest or invoke the `vc-generate-context` skill

- **Bug Fix / Debug Request** (keywords: "fix", "bug", "broken", "debug", "error")
  → For trivial: delegate to `vc-execute-agent` directly (no plan required)
  → For complex: Route to `vc-debugger` agent. Surface helper skills like `vc-scout`, `vc-sequential-thinking`, or `vc-problem-solving` when useful.

- **Existing Plan File Present**
  → Resume from relevant phase, don't recreate plan

- **UI / Frontend Request** (keywords: "page", "component", "design", "layout", "interface", "UI")
  → Surface `vc-frontend-design` skill alongside `vc-research-agent`. Invoke `vc-ui-ux-designer` agent during EXECUTE phase for implementation.

- **Documentation Question** (keywords: "how does X work", "API docs", "syntax", "version")
  → Activate `vc-docs-seeker` skill before routing to `vc-research-agent`

- **Refactor / Simplify** (keywords: "refactor", "clean up", "simplify", "reorganize")
  - *Pure style/readability* (named file, no behavior change): route directly to `vc-code-simplifier` agent
  - *Behavioral or architectural refactor*: full RESEARCH → PLAN → EXECUTE, then `vc-code-simplifier` as cleanup

- **Debug / Root Cause** (keywords: "debug", "why", "root cause", "investigate")
  → `vc-debugger` agent = default owner. Helper skills like `vc-scout`, `vc-sequential-thinking`, and `vc-problem-solving` may be layered in as needed.

**When multiple intents match** (e.g., UI bug with docs question), use this precedence:
1. Existing plan file in process/general-plans/active/ or process/features/*/active/ → always resume first
2. Explicit mode command (ENTER X MODE) → obey immediately
3. Bug/debug → debugging routing before feature routing
4. Feature request → RIPER-5 flow
5. UI specialization → surface vc-frontend-design alongside any of the above
6. Docs question → surface vc-docs-seeker alongside any of the above
When still ambiguous, ask the user one clarifying question before routing.

### 2. Gather Context

Always pass `process/context/all-context.md` and the full file listing before routing; check
existing active plans before creating new ones. Full context-discovery rules: §Gather Context for
Execute and Tester.

### 3. Route to Subagent

Route by current phase to the matching agent (understanding → `vc-research-agent`; requirements →
`vc-spec-agent`; options → `vc-innovate-agent`; plan → `vc-plan-agent`; validate / resume →
`vc-validate-agent`; implement → `vc-execute-agent`; fast → `vc-fast-mode-agent`; learnings →
`vc-update-process-agent`). See the RIPER-5 Phase Table in CLAUDE.md for triggers and artifacts.

### 4. Monitor Compliance

Ensure the subagent uses the correct mode prefix, stays within tool restrictions, doesn't skip
phases, and produces the expected artifact.
