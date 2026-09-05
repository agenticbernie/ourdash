---
name: protocol:vc-system-behavior-04-research
description: "RESEARCH phase reference: required skills, outputs, and skip conditions."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing the RESEARCH phase"
---

# RESEARCH Phase Reference

## What This Phase Is

RESEARCH is the first phase of every non-trivial task. The agent reads the codebase, loads context, and gathers facts. It does not write files. It does not make decisions. It produces a findings summary in the conversation.

---

## Agent and Tools

**Agent:** `vc-research-agent` (sonnet)

**Tools allowed:** Read, Grep, Glob, Bash (safe commands only), WebSearch

**Bash whitelist:** `ls`, `cat`, `head`, `tail`, `git status`, `git log`, `git diff`, `find`, `grep`, `date`, `pwd`, `which`

**Tools NOT allowed:** Write

---

## Session Start (Tier 0 — required before anything else)

These run in order. Do not skip any of them.

> **Single-trip rule (PHASE-GATES).** All Tier-0 skills below (intent-clarify, context/plan discovery, review-situation, strategy-compare) run as *preparation* but produce exactly **one** user pause: the **Combined Clarification Gate** from `03-session-start.md` Step 6.5. Intent restatement + clarifying questions + the 4 strategy options are presented together in a single `AskUserQuestion`. Do NOT pause separately at R-S0 and again at R-S4. Under `/goal` the gate auto-proceeds. See `12-reference.md` (`PHASE-GATES`).

### [R-S0] vc-intent-clarify (Tier 0) — REQUIRED

Run this first. Restate what the user asked. Produce any clarifying questions — but do **NOT** pause here. They feed the single Combined Clarification Gate (see the single-trip rule above).

If coming from an orchestrator session that already ran intent-clarify: give a one-sentence restatement only. ("Proceeding with [scope]. My understanding: [one sentence]. Correct me if off.")

### [R-S1] vc-context-discovery (Tier 0) — REQUIRED

This has two parts. Both are required.

**Part A — Directory discovery:**

```bash
find process/context/ -type f | sort
find process/development-protocols/ -type f | sort
```

Then read `process/context/all-context.md`. Follow its routing table to load the smallest set of relevant context files. Each `all-{group}.md` file is also a router — follow it to the 1–2 deeper files that matter for this task.

If the prompt includes `Feature:`, also run:
```bash
find process/features/{feature}/ -type f | sort
```

If the task involves testing, debugging, or verification:
```bash
find process/context/tests/ -type f | sort
```
Then load `process/context/tests/all-tests.md` and follow its routing chain.

**Part B — Frontmatter extraction:**

For every plan file found in `active/`, extract: `name`, `description`, `feature`, `phase`, `date`.

If a plan file has no YAML frontmatter: infer from the file path and first heading. Mark inferred fields as `(inferred)`. Emit a `FRONTMATTER_MISSING` warning.

Use these fields to fill in the **Context Envelope** (see below).

**Context Envelope format:**

```
## Context Envelope
feature:               {value or "general"}
phase:                 {value or "N/A"}
session-goal:          {from plan ## Session Goal section}
blast-radius-packages: {comma-separated files/packages from plan ## Blast Radius}
active-plan:           {exact path to selected active plan}
test-runner:           {primary runner for blast-radius area}
validate-contract:     {yes / no}
branch:                {current git branch}
worktree:              {git worktree list output}
context-group:         {context routing match from all-context.md}
```

> Note: This display order is illustrative only. For implementation, follow the Section 9 yaml spec field order: feature → phase → session-goal → branch → worktree → context-group → blast-radius-packages → active-plan → test-runner → validate-contract.
> The H4 interim format uses the same canonical 10-field set.

The `test-runner` field comes from `all-tests.md` routing. For a blast radius that spans multiple runners, use pipe-delimited format: `bun test | vitest`. If the `all-tests.md` routing has not been run yet, write `PENDING — see all-tests.md`. Note for G1 template consumers: the pipe-delimited format is a display convention, not a shell command. G1 template must expand to sequential execution.

**If context discovery fails** (folder missing, file malformed, find returns nothing): keep going. Use Grep and Bash to find relevant files manually.

> CONTEXT_PARTIAL is NOT a standalone exit status code. When context discovery is partial, exit with `DONE_WITH_CONCERNS` and include `CONTEXT_PARTIAL: [reason]` in the Concerns field. Never return CONTEXT_PARTIAL as the sole status. See also: orchestration.md §Subagent Status Protocol — CONTEXT_PARTIAL is a supplemental warning flag, not one of the 4 main codes (DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT).

### [R-S2] vc-plan-discovery (Tier 0) — REQUIRED

Also has two parts. Both are required. Run alongside R-S1.

**Part A — Scope scan:**
- Same feature folder: scan everything — `active/`, `backlog/`, `completed/`, `reports/`, `references/`
- Other feature folders: scan `active/` only
- `process/general-plans/active/`: always scan

**Frontmatter match rules:**
- (a) A plan matches if its `feature` frontmatter field equals the current feature folder name exactly; OR
- (b) If no `feature` field: the feature name appears in the `description` field (case-insensitive)
- (c) If no `Feature:` is in the prompt, rule (b) does not apply. Plans without a feature frontmatter field are grouped as "unmatched (no feature context)"
- (d) If two feature names match the same plan description, list the plan under both AND flag it as `AMBIGUOUS_MATCH`
- Unmatched plans are listed as "other active plans (no feature match)" — still discoverable

**Stale plan rule:**
A plan is stale for discovery if it is more than 90 days old AND any of:
- It matched only by substring (no exact feature name match), OR
- Its status is CONDITIONAL or BLOCKED AND no Implementation Checklist items have been ticked since the plan was created

> Definition of "no checklist updates": no `- [x]` pattern with a date after the plan's creation date exists in the plan file.

Stale plans are tagged `(stale — verify relevance)`. They do not automatically trigger "update or create new?"

> Under /goal: if a plan is stale, always create a new plan without asking.

**Part B — Frontmatter extraction:**

For each plan file found, extract: `name`, `description`, `feature`, `phase`, `date`. Group by folder. This feeds the `active-plan` field in the Context Envelope.

### [R-S3] vc-review-situation (Tier 0) — REQUIRED

Check branch, worktree, and active plan state. Understand what is currently in flight.

### [R-S4] vc-agent-strategy-compare (Tier 0) — REQUIRED

Run this before spawning any research subagents. Score the full 4-option strategy suite (sequential / parallel / workflow / vc-team) with cost estimates. Do **NOT** pause separately — the options are surfaced for confirmation inside the Combined Clarification Gate, alongside the intent questions (single trip).

If the orchestrator already passed a strategy recommendation: verify it still makes sense. If not, re-score the full evaluation.

### Signals & prior-report reading (R-SIG)

- `VC-PREDICT-RESEARCH-COMPLETE` — emitted when this agent runs as a mid-INNOVATE scoped re-research spawn (triggered by `VC-PREDICT-DEEP-NEEDED`); the orchestrator must NOT advance the RESEARCH step on it.
- Under /goal phase programs, RESEARCH reads prior-phase reports before gathering new context.

---

## During Research (ordered by when they run)

### [R1] vc-scout — (Tier 1) — REQUIRED

Run this before any direct grep or glob searches. Pass the task description and keywords. Get a ranked file list. Use that list to guide all subsequent searches.

### [R2] vc-docs-seeker — (Tier 1) — REQUIRED on first library/framework encounter

When you first encounter a library, framework, or SDK: run vc-docs-seeker before relying on your training data. Pass: library name, version from package.json, and your specific question. Include the output as evidence in your findings.

### [R3] vc-sequential-thinking — (Tier 2) — CONDITIONAL

Use this when:
- Two or more competing explanations exist
- Three or more components interact
- Evidence points in conflicting directions

### [R4] vc-agent-strategy-compare — (Tier 2) — CONDITIONAL (mid-phase)

Use this when research reveals two or more distinct investigation directions. Do not start parallel work before running this and getting a recommendation.

### [R5] vc-test-coverage-plan — (Tier 1) — REQUIRED before finalizing findings

Before you wrap up, run this. It has three parts:

**Part A — Test gap analysis:** List every file in the blast radius that has no test coverage. List every behavior in the requirements that has no test.

**Part B — Infra improvement suggestions:** For every area where tests are agent-probe or known-gap tier, suggest what infrastructure change would allow automated testing instead. Label each suggestion as small, medium, or large effort.

**Part C — Test-scenario discovery by design (REQUIRED):** Before enumerating any gaps, run context-discovery across the **full** testing-context chain — the `process/context/tests/all-tests.md` router AND every downstream file it routes to (e.g. container-e2e, browser-automation, live-e2e, etc.). The router is **not** full knowledge: reading only `all-tests.md` without following it to the deeper test docs is a **defect**, not an acceptable shortcut. Then exhaustively enumerate ALL possible test scenarios for the blast radius and requirements, grouped by the **three active testing strategies**:

- **Fully-Automated (AUTOMATED)** — fully-automated tests, including E2E and integration.
- **Hybrid** — partly-automated, partly agent-assisted.
- **Agent-Probe** — verified by an agent driving the system.

Known-Gap is **not** a strategy — it is a **rare residual** bucket for items that are genuinely untestable by any of the three strategies. Do not park a behavior in Known-Gap to avoid the work of enumerating its automated/hybrid/agent-probe scenarios; any Known-Gap entry must be explicitly justified (genuinely no automatable AND no hybrid/agent-probe coverage possible).

**Every developed behavior — across all surfaces (backend, container, browser, frontend, every surface the work builds) — requires comprehensive test scenarios across the 3 strategies.** Real automated E2E/integration is required wherever the surface is automatable. A behavior is classified done/archivable only when it is covered by comprehensive tests, with a fully-automated E2E/integration test wherever the behavior is automatable; agent-probe and Known-Gap stand only as the explicitly-justified residual where automation is genuinely impossible. Note this coverage requirement against each scenario so SPEC and PLAN inherit it. This is a **classification gate**, not a `/goal` stop: a behavior missing comprehensive tests yields a test-building backlog note and a not-archivable mark, and the loop continues.

This thorough exploration is mandatory **by design** — not best-effort or optional. Its output directly feeds SPEC's acceptance criteria (each criterion names the scenario that proves it) and PLAN's test-coverage plan.

These must appear in your final findings.

> Test gap analysis, infra improvement suggestions, and the by-design 3-strategy test-scenario enumeration are emitted as part of the findings format.

### [R6] vc-validate-findings — (Tier 2) — OPTIONAL

Run this when the user asks to verify findings further. It runs two layers of verification (4 dimensions + per-finding agents).

### [R7] vc-problem-solving — (Tier 2) — CONDITIONAL

Use this when you cannot locate information after two or more attempts, or when the scope keeps growing. Document which techniques you tried. Only report BLOCKED after this is exhausted.

---

## Required at Phase End

### [R-END] Phase-End Recommendation Gate (single round-trip)

Before ending the phase, present ONE consolidated recommendation block for the user to **confirm / push back / go**:

- the findings summary (the named sections from the Exit Gate)
- a recommended **next step** — mark the **recommended** one. The next step is NOT advance-only; it is one of:
  - **advance** to SPEC (RESEARCH always hands off to SPEC for non-trivial work; SPEC turns these findings into a user-reviewable requirements doc). Skip straight to PLAN only for an orchestrator-classified trivial fix.
  - **re-run RESEARCH** (loop back) when findings are insufficient — open questions remain unresolved, the user request still has un-clarified ambiguity, the blast radius grew during research, or a key library/behavior could not be confirmed. The recommendation must name the *specific gaps* driving the re-research and the *questions to ask the user* (these feed the next entry gate's clarification).
- the recommended execution strategy for that next step — full 4-option suite with signal score (N/7) and cost estimates, with one option marked **recommended**
- any optional deep work offered as a *choice*, not a separate pause (e.g. run `vc-validate-findings`)
- if 2+ distinct investigation directions were found: a fan-out recommendation

This is the single end-of-phase ask. Do not split strategy confirmation and "go" into separate round-trips. Under `/goal` the gate auto-proceeds on the recommended option — including a re-RESEARCH loop, bounded by the active-loop cap (`vc-autoresearch`, 10-cycle ceiling) to prevent infinite re-research. See `12-reference.md` (`PHASE-GATES`).

---

## Orchestrator Behavior

**Before spawning the agent:**
- Check `process/general-plans/active/` and `process/features/*/active/` for any existing plan. Do not create a duplicate.
- Pass `all-context.md`, the full file listing, and the feature scope.
- If the task is feature-scoped: include `Feature: {name}` with override paths for Reports and Plans.

**After the agent finishes:**
- Receive the strategy recommendation for SPEC.
- Check: does the output include Test Gap Analysis AND infra improvement suggestions? Flag if missing.
- Read the status code: DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT.

---

## User Input

RESEARCH has exactly **two** user touchpoints — one at entry, one at exit (single round-trip each). No mid-phase interruptions.

- **Entry (one ask):** The Combined Clarification Gate (`03-session-start.md` Step 6.5) — confirm/correct the intent restatement, answer clarifying questions, and pick the execution strategy, all in one `AskUserQuestion`.
- **Exit (one ask):** The Phase-End Recommendation Gate (`R-END`) — the agent presents findings + recommended next phase + recommended strategy, and offers optional deep work (e.g. "validate findings further") as selectable choices. You **confirm / push back / go** in one response.
- **Mid-phase:** none. "Validate findings further?" is NOT a separate interruption — it is one of the options surfaced at the Exit gate.
- **Under /goal:** both gates auto-proceed; no pause.

---

## Exit Gate

All of these must be true before the phase is complete:

- Findings include these named sections: `## Scope and Blast Radius`, `## Key Facts`, `## Library/API Findings` (if applicable), `## Test Gap Analysis`, `## Infra Improvement Suggestions`, `## Open Questions`. Each section may be brief but must be present.
- `## Test Gap Analysis` lists all blast-radius files with no test coverage
- `## Infra Improvement Suggestions` covers every agent-probe and known-gap area
- vc-agent-strategy-compare was run for the SPEC phase (presented inside the Phase-End Recommendation Gate, not as a separate pause)
- User responded at the Phase-End Recommendation Gate (`confirm` / `push back` / `go`)

**Under /goal autonomous execution:** The "user says go" condition is auto-satisfied when the test gap analysis, infra improvement suggestions, and vc-agent-strategy-compare for SPEC are all complete. The agent emits: `PHASE_COMPLETE: RESEARCH — findings summary written` and moves on to SPEC. (Note: in a phase-program inner loop SPEC is skipped — the umbrella SPEC governs — so inner-loop RESEARCH moves on to INNOVATE instead. See `11-phase-programs.md`.)

---

## Artifact

Research findings are written in the conversation. No file is written.
