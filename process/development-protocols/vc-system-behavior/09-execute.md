---
name: protocol:vc-system-behavior-09-execute
description: "EXECUTE phase reference: implementation rules, deviation handling, EVL, and inner-loop execution."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing the EXECUTE phase"
---

# EXECUTE Phase

## What This Phase Does

EXECUTE implements exactly what the approved plan specifies. No creative changes. No scope additions. The agent runs until all plan checklist items are done or a hard stop is hit.

---

## Agent and Tools

**Agent:** `vc-execute-agent` (OPUS)

**Tools:** Full access — Read, Write, Edit, Delete, Grep, Glob, Bash

**Entry:** Only via explicit `ENTER EXECUTE MODE`. Never auto-enter.

**Autonomy rule:** Once EXECUTE begins (user trigger or /goal paste), the agent runs the full Level 1 per-section loop autonomously — TDD-first, test gates enforced, iterate until green. No user input is needed unless hard-stop conditions are hit.

---

## Orchestrator Preflight (Before Spawning)

All of these must be true before the orchestrator spawns execute-agent:

- `## Validate Contract` is present in the plan file
- User said `ENTER EXECUTE MODE` explicitly
- Exactly ONE plan file path is passed in the subagent prompt
- /goal block was output in chat

---

## Session Start Skills (Run in Order, All Required)

These run before any code changes.

> **Single-trip rule (PHASE-GATES).** EXECUTE has exactly two routine user touchpoints: an **entry** gate — the `ENTER EXECUTE MODE` trigger, which is itself the resolution of VALIDATE's exit gate (intent + strategy already settled there; the Tier-0 skills below run as silent prep, not a second pause) — and an **exit** Phase-End Recommendation Gate (EVL closeout, single round-trip). No mid-phase user pauses for routine work. **Under `/goal` a true run pauses for nothing** — both gates auto-proceed, and every would-be stop (high-risk finalize, hard-stop-class deviation, pre-phase-research findings) becomes a **backlog note + continue** instead. The interactive-only stops below apply only when NOT under `/goal`. See `12-reference.md` PHASE-GATES.

**[E-S0] vc-intent-clarify** (Tier 0) — Required first.

Restate the scope of what is being executed: plan path and phase name. Do **NOT** add a separate confirmation pause — intent + strategy were settled at VALIDATE's exit gate that produced `ENTER EXECUTE MODE`. This restatement is silent prep.

### Per-Stage Pre-Research Approval Pause (interactive only; complex single-file multi-stage plans)

**Scope:** this applies ONLY to a **complex single-file plan with multiple stages** (one plan file, several `## Stage N` blocks executed in sequence). It does NOT apply to a multi-phase **program** — there each phase already runs its own full RIPER-5 loop (including a RESEARCH phase with its own entry/exit gates), so per-stage pre-research approval is already covered by that loop and must not be duplicated here.

For a complex multi-stage plan: before implementing a stage that opens with a pre-implementation research/exploration step, the agent surfaces its findings + intended approach and **pauses for approval before writing code** (per `feedback_execute_workflow.md`: pre-stage research does not auto-flow into edits). Post-stage summaries must state what is now functional and what the user can test.

**Under `/goal`:** no pause. The agent proceeds on its own recommendation, records the findings/approach as a progress note, and continues. Anything that would otherwise stop (including hard-stop-class deviations) becomes a backlog note + continue (see Deviation Handling).

**[E-S1] vc-context-discovery** (Tier 0) — Required.

Load context. Part A (directory) + Part B (frontmatter → Context Envelope).

**[E-S2] vc-plan-discovery** (Tier 0) — Required.

Run alongside E-S1. Find related plans.

**[E-S3] vc-review-situation** (Tier 0) — Required.

Read the plan's `## Current Execution State` and `## Phase Loop Progress` to understand what was done and what remains.

SIMPLE plan / Phase 1 fallback: if those sections don't exist, skip E-S3 and read `## Implementation Checklist` as the authoritative task list instead.

**[E-S4] vc-agent-strategy-compare** (Tier 0) — Required.

Confirm execution strategy for this plan (sequential vs parallel vs workflow vs team).

**[E-S5] Read selected plan.**

Read: Touchpoints, Public Contracts, Blast Radius, Verification Evidence, Resume Handoff, and `## Validate Contract`. Extract test gate commands from the validate-contract. Use exact commands — never invent them.

---

## Skills During Implementation

**[E1] vc-scout** (Tier 1) — Required before any breaking change.

Scan the import chain to determine blast radius before modifying a file that other packages import.

**[E2] vc-sequential-thinking** (Tier 1) — Required when plan step ordering is unclear.

Use this to resolve step ordering before proceeding.

**[E3] vc-docs-seeker** (Tier 1) — Required when any library API call signature is unclear.

Do not guess API signatures.

**[E4] vc-scenario** (Tier 2) — Required after implementing any new function, endpoint, or export.

Run before running tests. Surface edge cases before they become test failures.

**[E5] vc-security** (Tier 2) — Required before marking any high-risk section complete.

High-risk sections are: auth, billing, container, secrets, public API.

**[E6] vc-problem-solving** (Tier 2) — Required before escalating BLOCKED.

Exhaust problem-solving techniques before returning to PLAN mode.

**[E7] vc-agent-strategy-compare** (Tier 0) — Required at the end of each major section.

---

## Level 1 — Per-Section Iterate-Until-Green Loop

Fires after each plan section. Runs autonomously — no user input between sections.

```
For each plan section:
  1. Implement section per checklist items
  2. Read test gates from ## Validate Contract (EXACT commands — never invent)
  3. Run fully-automated tier gates for this section
  4. GREEN → mark section complete ✓ → move to next section
  5. RED → identify root cause → fix → re-run → repeat
  6. After 3 attempts OR structurally impossible:
     a. Document gap (what failed, why unresolvable)
     b. Classify: product-breakage / test-breakage / harness-drift / stale-command-drift
     c. Create follow-up plan stub in process/features/{feature}/active/
     d. Mark section as done-with-gap → continue to next section
        DO NOT block whole phase for one section's unresolvable gap

  Follow-up plan stub required shape:
  - YAML frontmatter: name, feature, phase, date (required)
  - ## Session Goal — what this stub fixes
  - ## Implementation Checklist — at minimum: the failing gate command + root cause discovered
  - ## Blast Radius — files the fix will touch
  - ## Verification Evidence — the exact test command that must go green
  - Does NOT require: Touchpoints, Public Contracts, or a Validate Contract
  - Location: process/features/{feature}/active/ for feature work
              process/general-plans/active/ for general work

  7. Hybrid tier: run + record outcome + fix only if within blast radius
  8. Agent-probe tier: run + record judgment + escalate if blocking
  9. Known-gap tier: record judgment + continue
```

> **No-contract fallback:** When no validate-contract exists (legacy plans, trivial fixes), the loop reads the plan's `## Verification Evidence` section as the fully-automated gate set.

---

## EXECUTE-VALIDATE-LOOP (EVL) — Level 2

EVL fires after execute-agent reports DONE. The orchestrator owns EVL, not execute-agent.

Level 1 = per-section inline (inside execute-agent).
EVL = cross-section integration (orchestrator-owned, post-DONE).
Level 1 green does not mean EVL can be skipped.

### Execute-Validate-Fix Loop (Within EVL)

When EVL finds a failing gate, an execute-validate-fix loop fires:

- Scoped exactly to the failing gate — no broader changes or scope expansion.
- Receives: gap description, failing test command, exact relevant plan section.
- Fixes only that gap.
- If the root cause requires broader changes: create a follow-up plan stub instead.

**Scope rule:** A fix is "scoped to the failing gate" if ALL changed files are:
(a) already in the current phase's validate-contract blast-radius, AND
(b) the change does not add new public API surface or schema fields.

If either condition fails → create a follow-up plan stub instead.

Exception: renaming import paths to match a new file location is always within scope, regardless of how many files reference it. This is mechanical repair, not scope expansion.

**Cycle limit:** 10 execute-validate-fix loop iterations maximum. After 10 cycles on the same gate: create a follow-up plan stub, classify the gap, and accept it as a known-gap. Under /goal, no user approval is needed at the 10-cycle limit.

### EVL Mode Selection

The EVL run-mode (auto-run vs step-by-step) is NOT a separate pause. It is folded into the exit **Phase-End Recommendation Gate** (EVL closeout) as one of the run options. The EVL gate sequence (Steps 1–6) is internal machine work, not a user round-trip.

**Under /goal:** Always auto-run. No user prompt.

**Outside /goal:** The exit gate surfaces this choice once (sticky for the full EVL):
> "Ready to start EVL. How do you want to run it?
> (a) Auto-run — run gate commands → if failing: execute-agent fixes → re-run gates → repeat until all green or 10-cycle cap.
> (b) Step-by-step — present failing gates → you confirm → execute-agent applies fix → re-run gates → present results → confirm → loop or move forward.
> Recommendation: [auto-run | step-by-step] because [one-line reason]."

In **auto-run mode** (vc-autoresearch behavior): the orchestrator automatically routes back to vc-execute-agent on gate failure, then re-runs tester gates without pausing.
In **step-by-step mode**: the orchestrator pauses after each gate run result and after each execute-fix before re-running.

The loop automatically routes back to vc-execute-agent each time EVL finds a failing gate. After the fix, gates re-run from the start. This continues until all gates pass, HALT_PLATEAU, or 10-cycle cap.

**This loop is run by the `vc-autoresearch` skill** (`domain: tests`, `verify:` = the
validate-contract gate commands) as its bookkeeper — autoresearch owns the iteration
counter, plateau/regression detection, the TSV log, and the 10-cycle cap; vc-tester and
vc-execute-agent keep their own gate-running and supplement mechanics. See `vc-autoresearch`
SKILL.md §EVL Wiring.

**Parallel fix agents:** When multiple independent gates fail across non-overlapping file
groups, the orchestrator spawns **multiple parallel execute-fix agents** — one per failing
gate / file group, partitioned so no two agents edit the same file, each scoped to exactly
its gate. When failing gates share files or a single root cause, use a single execute-fix
agent.

### EVL Steps

```
EVL Steps:
  1. Invoke vc-generate-closeout → 9-field closeout packet
     (9-field packet definition: see Section 7 §vc-generate-closeout — 9 Required Fields. All 9 fields are required. The preliminary packet from EVL Step 1 is superseded by the authoritative U-S5 closeout at UPDATE PROCESS entry.)

  2. Delta check: compare validate-contract touchpoints vs `git diff --name-only HEAD~N`:
     │ Section 1: ✓ DELIVERED (3/3 gates green)
     │ Section 2: ~ PARTIAL — touchpoint X not in diff; 1/2 gates green
     │ Section 3: ✗ SKIPPED — BLOCKED, moved to backlog

  3. Confirm all validate-contract fully-automated gates are green.
     - If execute-agent reported DONE_WITH_CONCERNS: re-run is MANDATORY. Treat as uncertain by default.
     - If execute-agent reported DONE: may accept execute-agent's run evidence unless step 2 delta check found touchpoint mismatches.
     - If execute-agent reported NEEDS_CONTEXT: treat as DONE_WITH_CONCERNS. Re-run all validate-contract gates from scratch. Create a follow-up plan stub scoped to the area requiring missing context. Record as CONTEXT_PARTIAL: [missing context area] in the EVL summary. Pass the CONTEXT_PARTIAL list to UPDATE PROCESS as part of the EVL handoff summary.

     If uncertain: ask execute-agent to run pnpm test:local one final time.

     Zero-gates edge case — gated on whether the contract developed any behavior at all: if the validate-contract has no fully-automated tier gates (all gates are hybrid, agent-probe, or known-gap), the handling forks on whether the contract developed any behavior.

     - **No developed behavior (e.g. pure file moves, docs, comment-only changes — genuinely no automatable surface):** vacuous green is allowed. Emit: 'Step 3: vacuously green — validate-contract has 0 fully-automated gates (no developed behavior).' Record in EVL HANDOFF SUMMARY: gates_green: [] — no fully-automated gates. Proceed to Step 4. Do not create an execute-validate-fix loop for a gate-absent validation.

     - **Any developed behavior (HARD E2E gate — vacuous green BANNED):** if the contract developed ANY behavior (backend, container, browser, or frontend) but lists zero fully-automated E2E/integration gates, EVL MUST NOT report green. It must NOT emit 'vacuously green.' Every developed behavior must have its comprehensive test scenarios actually run, with an automated E2E/integration gate wherever the surface is automatable — there is no pure-internal free pass. Instead: classify the work CONDITIONAL / not-archivable / keep in active-testing, create a test-building backlog stub for the missing automated coverage, and continue. This is a classification gate, not a /goal stop — under /goal the loop writes the stub, sets the closeout classification to "Keep in active/ — needs further testing", and CONTINUES without pausing; interactive runs surface the missing-gate classification at the Phase-End Recommendation Gate. Only the existing loop-control bounds (10-cycle cap, Cascade BLOCKED, blast-radius conflict) still surface.

  4. If gates NOT green → execute-validate-fix loop:
     a. Spawn vc-execute-agent (supplement mode) with exact failing gate + relevant plan section
     b. Supplement is scoped to failing gate ONLY — no broader changes
     c. If root cause broader than gate → create follow-up plan stub instead
     d. Re-run failing test gate
     e. Loop until green OR gap accepted as known-gap. Under /goal: the orchestrator auto-accepts after 10 cycles, records in phase report, and writes a backlog note. Outside /goal: requires user approval.

  5. Classify plan for closeout. Use exactly one of:
     - "Ready for UPDATE PROCESS archival"
     - "Keep in active/ — needs further testing"
     - "Needs PLAN/UPDATE PROCESS reconciliation"

     EVL classification takes precedence over execute-agent's self-review classification when they conflict. Document the classification if it differs from what execute-agent reported.

     **Hard E2E classification rule:** any developed behavior (backend, container, browser, or frontend) lacking a passing fully-automated E2E/integration gate — wherever the surface is automatable — CANNOT be classified "Ready for UPDATE PROCESS archival." It must be classified "Keep in active/ — needs further testing" with a test-building backlog stub recorded. This holds even when every present gate is green and even under /goal — the classification changes, the program continues, only the existing loop-control bounds (10-cycle cap, Cascade BLOCKED, blast-radius conflict) still surface.

  6. Route to UPDATE PROCESS with full RIPER-5 handoff.

     Commit timing:
     (1) Source commit fires HERE — orchestrator invokes vc-git-manager immediately after the EVL HANDOFF SUMMARY block is emitted. Includes implementation files only.
     (2) Process commit fires AFTER UPDATE PROCESS — includes archived plan, context doc updates, phase report, and memory notes.
     Never leave verified-working source changes uncommitted at phase close.
     Never bundle source + process changes in one commit.
```

### EVL HANDOFF SUMMARY Format

The orchestrator emits this block (not execute-agent or vc-tester) before closing step 6.

```yaml
EVL HANDOFF SUMMARY:
gates_green: [list gate names]
known_gaps: [{gate: "[gate name]", backlog_note_path: "[path]"}]
follow_up_stubs: [{section: "[plan section]", stub_path: "[path]"}]
context_partial: ["area1", "area2"]  # (bare strings, not bracket-wrapped; matches vc-tester.md output format)
preliminary_packet_path: process/features/{feature}/reports/{phase}-evl-preliminary.md
closeout_classification: "Ready for UPDATE PROCESS archival" | "Keep in active/ — needs further testing" | "Needs PLAN/UPDATE PROCESS reconciliation"
```

All fields must be present even if empty (use `[]` for empty arrays). `preliminary_packet_path` must be a repo-relative path string.

This structured block is the machine-readable handoff for UPDATE PROCESS and G1 workflow scripts.

**Detection rule:** Scan tester output for a line matching exactly `EVL HANDOFF SUMMARY:`. The 6-field yaml block follows immediately on subsequent lines. If this anchor line is not found after a EVL-green signal: emit `PARSE_ERROR: EVL HANDOFF SUMMARY anchor not found` and re-request tester output before proceeding.

Under /goal: emit `PHASE_COMPLETE: EVL — EVL HANDOFF SUMMARY emitted; preliminary packet written`

### Agent-Probe Re-Verification

For agent-probe tier gates, EVL must re-invoke the probe agent fresh — never accept the execute-phase judgment without re-running.

Fresh probe means: spawn the probe as a new subagent via Agent tool call. Pass only:
(a) the plan section's goal
(b) the exact probe scenario
(c) current relevant file contents from disk

Do not pass prior conversation history or the execute-agent's prior probe outcome.

**Follow-up stubs — proceed immediately:** When a follow-up plan stub is created, the current session proceeds to UPDATE PROCESS right away. The stub is registered in the umbrella plan as the next phase. The orchestrator does NOT wait for the stub to be executed before closing the current phase.

### Cross-Phase Regressions

EVL also runs regression gates for surfaces that prior phases established as green, not just the current phase's blast radius. Source: prior phase validate-contracts (cumulative archive).

Archive location after each phase's EVL: `process/features/{feature}/reports/{phase}-validate-contract.md` (feature work) or `process/general-plans/reports/{plan-slug}-validate-contract.md` (general work).

EVL for phase N reads all archived contracts from phases 1 through N-1 and runs their fully-automated tier commands as regression checks. If a prior phase has no archived contract: skip its regression check and emit a warning.

If EVL misses a cross-phase regression, the next phase's inner RESEARCH will catch it during Step 1 (which reads prior phase reports and runs vc-test-coverage-plan).

---

## Phase-End Recommendation Gate (single round-trip)

The one exit pause for EXECUTE, presented after EVL closeout (EVL Step 5 classification drives the recommended option). Present everything in one block for **confirm / push back / go**:

1. **EVL closeout summary** — EVL HANDOFF SUMMARY (gates green, known gaps, follow-up stubs, context_partial) + what is now functional and testable.
2. **Recommended next step (marked recommended), bidirectional** — mapped from the EVL Step 5 classification:
   - **Advance to UPDATE PROCESS** (recommended when classification = "Ready for UPDATE PROCESS archival").
   - **Re-run EXECUTE (loop back)** — when classification = "Keep in active/ — needs further testing"; name the specific gaps + gate failures that feed the next entry. Bounded by the EVL 10-cycle cap.
   - **Loop back to PLAN** — when classification = "Needs PLAN/UPDATE PROCESS reconciliation" (scope/contract drift beyond the failing gate).
3. **Recommended strategy** for the next phase (UPDATE PROCESS) — 4-option suite where it materially differs from sequential.
4. **Optional deep work** (extra regression sweep, code-review pass, simplifier pass) offered as *choices*, not a pause.

Under `/goal` this gate auto-proceeds on the recommended option — including a re-EXECUTE loop, bounded by the 10-cycle cap. The interactive-only stops (per-stage pre-research approval, high-risk finalize / hard-stop-class deviation) do not fire under `/goal` — they backlog + continue instead.

---

## Self-Review Before Reporting DONE

Before reporting any exit code, execute-agent must:

1. Re-read the plan. Was each checklist item implemented exactly as specified?
2. Flag any deviation, no matter how minor. Include: file path / what differs / rationale.
3. Re-read the plan's `## Session Goal`. Compare what was implemented against what the user actually wanted. Ask: "Based on the Session Goal, what does the user truly want to see? What is missing?" Surface any delta as a deviation before reporting DONE.
4. Also check delivered work against the **SPEC's acceptance criteria** (the SPEC is the upstream product-discovery requirements doc that drives this plan). For each acceptance criterion, confirm whether the implemented work satisfies it; surface any unmet criterion as a deviation before reporting DONE.

---

## Specialist Agents (Spawned by Execute-Agent)

| Agent | When to spawn |
|---|---|
| vc-tester | After each implementation sub-step |
| vc-debugger | Bug encountered during implementation |
| vc-code-reviewer | Before marking phase complete |
| vc-code-simplifier | After reviewer passes (optional) |
| vc-ui-ux-designer | UI/UX implementation tasks |
| vc-git-manager | Git operations |

**Write tests on demand rule:** When vc-tester or vc-code-reviewer recommends new tests and the recommendation is within the blast radius of the current plan, execute-agent must write those tests before marking the section complete. Do not defer test-writing to a follow-up stub when the tests are directly verifiable within the current scope.

---

## User Input

EXECUTE has two ROUTINE user touchpoints (entry + exit) plus narrowly-scoped interactive-only safety stops (per-stage pre-research approval on complex single-file multi-stage plans, high-risk finalize / hard-stop-class deviation). None of the interactive-only stops fire under /goal — there they backlog-and-continue. No routine mid-phase interruptions.

- **Entry:** `ENTER EXECUTE MODE` — the resolution of VALIDATE's exit gate; never auto-triggered. Intent + strategy already settled there.
- **Exit:** the Phase-End Recommendation Gate (EVL closeout) — confirm / push back / go on the recommended next step (advance to UPDATE PROCESS **or** loop back: re-EXECUTE / back-to-PLAN) and run-mode.
- **Mid-phase (routine):** none. The former 50% check-in is removed — in **all** modes the agent writes a mid-phase progress note to the phase report file instead (what was implemented, any deviations, current gate status, what is now functional and testable). It is never a user pause.
- **Interactive-only stop 1 — per-stage pre-research approval** (complex single-file multi-stage plans only; see Session Start Skills). Does not apply to multi-phase programs.
- **Interactive-only stop 2 — high-risk finalize** (`risk-gate.json mustStopBeforeFinalize: true`) and the hard-stop-class deviation set (auth / billing / schema / public API / container lifecycle / secrets — see below).
- **Under /goal:** a true run pauses for nothing. Entry/exit gates auto-proceed, AND every interactive-only stop above becomes a **backlog note + continue** — high-risk finalize, hard-stop-class deviations, and pre-research findings are all recorded as backlog and the loop keeps going.

### Deviation Handling

- **Hard-stop class** (auth / billing / schema changes / public API surface changes / container lifecycle changes / secret management changes — when these are NOT in the validate-contract):
  - **Interactive:** stop and surface to the user before proceeding.
  - **Under `/goal`:** do NOT stop. Record the deviation as a **backlog note** (with what deviated / why / impact + the fact that it is hard-stop class and was not user-reviewed), then continue. A true /goal run pauses for nothing — the backlog note is the audit trail the user reviews later.
- **Auto-proceed class** (naming deviations / file location within same blast-radius area / implementation detail / library call variation within same semantic operation): document + continue in both modes.

Write a `## Deviations` section to the plan file with: what deviated / why / impact assessment. Never silently deviate — every deviation is recorded (a user stop in interactive mode, a backlog note under /goal).

---

## Exit Codes

`DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`

**DONE** — all Level 1 gates green (or accepted as known-gap); no plan deviations documented.

**DONE_WITH_CONCERNS** — all Level 1 gates green or accepted as known-gap, BUT at least one of:
(a) a plan deviation was required and was documented
(b) a test gate was accepted as known-gap
(c) session-goal diff found a meaningful discrepancy between what was implemented and what the user wanted

**BLOCKED** — continuation is structurally impossible even with all available context.

**NEEDS_CONTEXT** — a required context file, plan section, or external reference is unavailable. Partial progress was possible. Includes what context is missing and where it should come from.

EVL behavior difference: `DONE_WITH_CONCERNS` → EVL step 3 is a required re-check even if execute-agent already ran gates. `DONE` → EVL step 3 may accept execute-agent's gate run evidence.

Under /goal: when reporting DONE or DONE_WITH_CONCERNS, emit: `PHASE_COMPLETE: EXECUTE — [phase name] implementation complete. EVL initiated.`

---

## Post-Execute Phase Compliance Check (Orchestrator-Owned)

After execute-agent reports any exit code, the orchestrator runs a process compliance check before launching EVL. This checks that the RIPER-5 process was followed, not just that tests passed.

**6-item compliance checklist (orchestrator reads plan file and verifies each):**

1. `## Implementation Checklist` — all completed items are checked off; no checked item is empty
2. `## Validate Contract` — present in the plan file
3. Phase report written to `process/features/{feature}/reports/` or `process/general-plans/reports/`
4. Any deviation from plan documented in the plan file with rationale
5. For phase programs: umbrella `## Current Execution State` reflects this phase's status

   Required format:
   ```
   ## Current Execution State
   Last updated: [YYYY-MM-DD]
   Current phase: [N] of [total]
   Phase [N] name: [title]
   Phase [N] status: [NOT_STARTED | IN_PROGRESS | COMPLETE | COMPLETE_WITH_GAPS | BLOCKED]
   Phase [N] EVL: [green | partial | red | N/A]
   Phase [N] report: [path or 'not written']
   Next phase: [N+1] — [title]
   ```

   Compliance check verifies: (a) "Last updated" is today's date, (b) current phase has a non-NOT_STARTED status, (c) if EVL ran, EVL field is not "N/A".

6. Follow-up plan stubs — execute-agent must include all stub paths in its exit status message. Orchestrator receives this list before running the compliance check.

If any item fails: orchestrator blocks EVL and routes back to execute-agent or update-process-agent to close the gap. EVL does not start until compliance passes.

Under /goal: this check runs autonomously. Trivial failures are self-healed directly. Structural failures spawn the appropriate agent.
