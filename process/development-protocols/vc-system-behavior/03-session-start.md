---
name: protocol:vc-system-behavior-03-session-start
description: "Session-start behavior: Context Envelope emission and Tier-0 required skills at the start of every inner-loop agent."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "understanding session-start steps and the Context Envelope"
---

# VC System Behavior — Session Start

Last updated: 2026-06-08

Session start runs before any phase work begins.
It runs before RESEARCH, before any subagent is spawned, every single time.
Follow these steps in order. You cannot skip steps.

> **Auto re-read on resume (fires automatically).** Session start also fires on ANY context gap — not only a fresh session or a human re-pasting the `/goal` block, but also a silent mid-run context compaction. On any such gap, before doing any phase work, the orchestrator MUST re-derive its loop position by re-reading the umbrella plan's `## Current Execution State` + `## Phase Loop Progress` and the latest phase report, then **reconcile that claimed state against actual git state** (the last EVL-green commit and the diff) to catch a stale or lying umbrella, before continuing. This is automatic — it does not require the user to re-paste `/goal`. The user still typically pastes a `/goal` block at program start; this auto re-read is the additional safety net for mid-run compaction. See Step 1.

---

## The 7 Steps

### Step 1 — Rough Orientation (3–5 files max, before any Tier-0 skills)

Run these commands and reads before anything else:

- `git status --short --branch`
- `find process/general-plans/active process/features -path '*/active/*' -type f | sort`
- Read `process/context/all-context.md` routing keywords
- If you know the feature name: `find process/features/{feature}/ -type f | sort`

If more than 5 candidate files match the task keywords, prioritize in this order:
1. The currently-active plan file whose name matches the task
2. `process/context/all-context.md`
3. The most recently modified active plan file

Skip all other candidates.

#### Auto Re-Read on Resume (any context gap, including silent compaction)

This sub-step fires automatically whenever loop position may have been lost — a new session, OR a silent mid-run context compaction (not only when the user re-pastes the `/goal` block). Before any phase work in a phase program, the orchestrator MUST recover its loop position:

1. Re-read the umbrella plan's `## Current Execution State` + `## Phase Loop Progress` and the latest phase report to recover the claimed loop position (which phase / which step / which section / which cycle).
2. **Reconcile the claimed state against actual git state** — check the last EVL-green commit and the working diff. If the umbrella's claimed state disagrees with git (e.g. umbrella says a phase is green but no matching green commit / diff exists), treat the umbrella as stale or lying: trust the git-reconciled position and correct the umbrella before continuing.
3. Only then continue with the recovered loop position.

This is automatic and does not require the user to re-paste `/goal`. It is the additional safety net for mid-run compaction; the user still typically pastes `/goal` at program start.

---

### Step 2 — vc-intent-clarify (Tier 0, runs BEFORE context loading)

This runs before any routing or subagent spawn.

Produce two things — both are required:

**(a) Deep restatement** — Articulate what you understand the user wants:
- Scope: what will change, what will not
- Goal: the underlying outcome the user wants, not just the stated task
- Constraints: anything the user implied (time, approach, limits)
- Related work: any active plans or prior context that seems relevant

**(b) Deeper clarifying questions** — Ask questions that surface unstated assumptions:
- What does success look like specifically?
- Are there areas that must NOT be touched?
- Is there an existing plan that should be resumed?
- What is the priority — quick fix or proper solution?

Produce the restatement and questions now, but do **NOT** pause here. The single confirmation happens once, at the **Combined Clarification Gate** (Step 6.5), where these questions are presented together with the strategy options in one structured ask. One confirmation per phase entry — never a double round-trip.

Format (feeds the combined gate): "Here is what I understand: [deep restatement]. My questions: [list]."

#### Auto-Skip Conditions

In these cases, Tier 0 still fires but the restatement and questions are shorter:

| Trigger | Restatement | Questions | Wait for go-ahead |
|---|---|---|---|
| /goal mid-program execution | Emit brief | Skip | Skip |
| Continuation phrase ("go", "proceed", "continue", "just do it") | Emit brief | Skip | Skip |
| Explicit mode command ("ENTER X MODE") | Emit brief | Skip | Skip |
| Pure single-target information question | Emit brief | Skip | Skip |
| Trivial fix (single-file, no new dependencies, no schema/API/auth, under 15 lines) | Emit 1-line | Skip | Skip |
| Resuming active plan | Emit 1-line | Skip | Skip |

#### Ambiguity Scoring

Score 4 binary signals: ambiguous scope / no explicit path / multiple intents / first interaction.

- Score 0–1: brief restatement + 1–2 targeted questions
- Score 2: restatement + routing summary + 2–3 questions
- Score 3+: full deep restatement + 3–4 multiple-choice clarifying questions

---

### Step 3 — vc-context-discovery (Tier 0)

This skill does two things. Both are required.

**Part A — Directory discovery:**

Run:
```bash
find process/context/ -type f | sort
find process/development-protocols/ -type f | sort
```

Then read `process/context/all-context.md` and follow its routing table to load the smallest relevant context group files. Each `all-{group}.md` is itself a router — follow it to load the 1–2 relevant deeper files for the blast radius.

If `Feature:` is set in the prompt:
```bash
find process/features/{feature}/ -type f | sort
```
This lists all subdirs: active/, backlog/, completed/, reports/, references/.

If the task touches testing, verification, or debugging:
```bash
find process/context/tests/ -type f | sort
```
Then load `process/context/tests/all-tests.md` and follow its routing chain to the relevant deeper file.

**Part B — Frontmatter extraction:**

For every plan file found in active/ (or passed in the prompt), extract these YAML frontmatter fields: `name`, `description`, `feature`, `phase`, `date`.

If a plan file has no YAML frontmatter block (legacy format):
- Extract from prose: `name` from first H1 heading, `feature` from file path, `phase` as N/A, `date` from filename date suffix if present
- Mark extracted fields as `(inferred)`
- Emit `FRONTMATTER_MISSING` warning in the Context Envelope
- Never halt — always produce a Context Envelope even if all fields are inferred

Surface the result as the **Context Envelope**:

```
## Context Envelope
feature:               {value or "general"}
phase:                 {value or "N/A"}
session-goal:          {from plan ## Session Goal section}
branch:                {current git branch}
worktree:              {git worktree list output}
context-group:         {context routing match from all-context.md}
blast-radius-packages: {comma-separated files/packages from plan ## Blast Radius}
active-plan:           {exact path to selected active plan}
test-runner:           {primary runner for blast-radius area, from all-tests.md routing}
validate-contract:     {yes / no}
```

#### Context Envelope Fields

| Field | Source |
|---|---|
| `feature` | Plan frontmatter or path |
| `phase` | Plan frontmatter |
| `session-goal` | If plan has `## Session Goal` → use that (mark `(from plan)`). If no plan yet → use vc-intent-clarify restatement (mark `(from restatement)`) |
| `blast-radius-packages` | If plan has `## Blast Radius` → use that. If no plan → derive from vc-scout output (mark `(estimated — no plan yet)`). If vc-scout not run → write `PENDING` |
| `active-plan` | Part B frontmatter extraction |
| `test-runner` | From all-tests.md routing. Multiple runners: use pipe-delimited format `bun test | vitest`. If routing not yet run: write `PENDING — see all-tests.md`. Note for G1 template consumers: the pipe-delimited format is a display convention, not a shell command. G1 template must expand to sequential execution. |
| `validate-contract` | Check for the section in the plan file |
| `branch` | `git status` — fallback: `(detached HEAD)` or `(no git repo)` |
| `worktree` | `git worktree list` — fallback: `main (no worktrees)` or `(no git repo)` |
| `context-group` | Context routing match from all-context.md |

> Note on field order: The template block above is emitted in the canonical 10-field order: feature → phase → session-goal → branch → worktree → context-group → blast-radius-packages → active-plan → test-runner → validate-contract. Copying the template verbatim produces canonical output. (The same field-order note appears in `04-research.md`.)
> The H4 interim format uses this same canonical 10-field set.

> Note on rehydration: when the envelope is being rebuilt after a context gap (new session or silent mid-run compaction), recovering the loop position — which phase / which step / which section / which cycle — is part of envelope rehydration. Derive it via the Step 1 "Auto Re-Read on Resume" sub-step (re-read umbrella `## Current Execution State` + `## Phase Loop Progress` + latest phase report, then reconcile against git state) and carry the recovered `phase` into this envelope.

#### If Context Discovery Fails

If the feature folder is missing, all-context.md is broken, or find returns nothing:
- Proceed with best-effort context — use Grep/Bash to find relevant files organically.
- Never halt because context discovery returned empty.
- Emit a `CONTEXT_PARTIAL` warning inside the phase report under a normal DONE or DONE_WITH_CONCERNS exit status.
- `CONTEXT_PARTIAL` is not a top-level exit status code. It is a warning flag only.

---

### Step 4 — vc-plan-discovery (Tier 0, run alongside Step 3)

This skill also does two things. Both are required.

**Part A — Scope scan:**

- Same-feature folder: scan ALL of active/, backlog/, completed/, reports/, references/
- Other feature folders: scan active/ only (match by frontmatter)
- general-plans/active/: always scan

**Harness session-scanning rule:** For sessions involving agent, skill, or harness work, Part A MUST also scan `process/features/development-process/backlog/` for NOTE files with severity HIGH or CRITICAL, and surface these as "active harness improvement items" in the plan-discovery output.

**How frontmatter matching works:**
- (a) Match if `feature` field equals the current feature folder name exactly; OR
- (b) If no `feature` field: match if the current feature folder name appears (case-insensitive) in the `description` field
- (c) If no `Feature:` in the prompt, rule (b) does not apply. All plans without a feature frontmatter field are grouped as "unmatched (no feature context)".
- (d) If two feature names match the same plan description, list the plan under both features AND flag it as `AMBIGUOUS_MATCH`.
- Unmatched plans are listed separately as "other active plans (no feature match)" — still discoverable

**Stale plan rule:**
A plan is stale for discovery if it is more than 90 days old AND any of:
- It matched only by substring (no exact feature name match), OR
- Its status is CONDITIONAL or BLOCKED AND no Implementation Checklist items have been ticked since the plan was created

> Definition of "no checklist updates": no `- [x]` pattern with a date after the plan's creation date exists in the plan file.

Stale plans are tagged `(stale — verify relevance)`. They do not automatically trigger "update or create new?" Under /goal, a stale plan always means: create a new plan without asking.

**Part B — Frontmatter extraction:**

For each plan file found, extract: `name`, `description`, `feature`, `phase`, `date`.
Group output by folder.
Surface what was tried, what was deferred, and what is currently active.
This feeds the `active-plan` field in the Context Envelope.

---

### Step 5 — vc-review-situation (Tier 0)

Check branch, worktree, and active-plan orientation.
This is advisory only. It does not authorize execution.

---

### Step 6 — vc-agent-strategy-compare (Tier 0)

Run BEFORE the Combined Clarification Gate. Score the 4 options:

`sequential / parallel-subagents / workflow / agent-team`

Include the 7-signal score and cost estimates for each option. Do **NOT** pause here — the strategy options are surfaced for confirmation inside the Combined Clarification Gate (Step 6.5), alongside the intent questions, as ONE structured ask.

There is no default strategy. Evaluate all 4 options genuinely.
When two strategies score equally, prefer the lower-cost option if scope or timeline is unclear. Surface the tie to the user as one of the strategy-question choices — do not resolve it silently.

**Auto-skip (mirrors Step 2's Auto-Skip Conditions):** when any auto-skip trigger fires (/goal mid-program, continuation phrase, explicit mode command, trivial fix, active-plan resume), strategy is auto-selected from the 7-signal score without presenting the question. Under `/goal` the orchestrator self-decides strategy and auto-proceeds — a true /goal run never pauses; irreversible/outward-facing/costful actions are deferred to backlog (skipped, not performed) rather than paused on. This keeps Step 6 in sync with `02-skill-tiers.md` (Abbreviated Mode) and CLAUDE.md's autonomous-/goal rule.

> Strategy scoring in this step is mandatory: it always runs and its output feeds the Combined Clarification Gate (Step 6.5). It does not pause on its own.

---

### Step 6.5 — Combined Clarification Gate (the single pause)

This is the **one and only** user pause in session start. Present everything in a single structured multiple-choice ask (Claude Code's `AskUserQuestion` tool):

- the intent restatement (Step 2) as the framing
- the clarifying questions (Step 2) as question items
- the strategy selection (Step 6) as one more question item — the 4 options, each labeled with its 7-signal score and cost estimate as selectable choices

The user answers all of it in one round-trip. There is no separate "confirm intent" then "confirm strategy" step — they are merged into this single ask.

Skip this gate entirely when an Auto-Skip Condition (Step 2 table) fired: emit the brief restatement, auto-select strategy from the 7-signal score, and proceed without pausing.

Note: Autopilot Mode trigger does NOT skip this gate — it replaces it with the Consolidated
Autopilot Clarification Round below. Auto-skip conditions apply only to the standard gate.

#### Autopilot Mode Path (when trigger detected before Step 6.5)

When an autopilot trigger phrase is detected (see `orchestration.md §Autopilot Trigger Routing`),
Step 6.5 is replaced by the **Consolidated Autopilot Clarification Round**:

- Issue exactly ONE `AskUserQuestion` call covering:
  1. Intent restatement confirmation (scope, task name, entry phase)
  2. Hard-stop boundaries confirmation (three hard stops remain manual)
  3. Gate deviations (any gates the user wants to remain interactive — default: none)
  4. Strategy options for the first remaining phase
- Dimension 6 (Autonomy Boundaries) from `vc-intent-clarify` is treated as CRITICAL.
- After the user responds, the provisional goal block is emitted and the `{slug}_AUTOPILOT_GOAL_{dd-mm-yy}.md` file is written to the task folder.
- Steps 2 + 6 + 6.5 collapse into this single round.
- No further clarification questions during the run (except the three hard stops).

Full specification: `process/development-protocols/autopilot.md §Consolidated Clarification Round`.

---

### Step 7 — Route to vc-research-agent

Pass these along when spawning:
- Context files loaded in Step 3
- Feature scope
- Plan path if known
- Strategy recommendation from Step 6

> Downstream order: after RESEARCH the phase sequence is `RESEARCH → SPEC → INNOVATE → PLAN`. The research agent's phase-end recommendation points to **SPEC**, not INNOVATE.
> Each phase also closes with its own EXIT gate (the Phase-End Recommendation Gate); this session-start flow only covers the entry into RESEARCH.

---

## Session Start Exit Gate

Before routing, confirm both:

- Combined Clarification Gate (Step 6.5) answered — intent go-ahead **and** strategy selection received in one round-trip (or an auto-skip/auto-proceed condition was met, which covers **both** intent and strategy together)
- vc-research-agent spawned with context files and the confirmed strategy attached
