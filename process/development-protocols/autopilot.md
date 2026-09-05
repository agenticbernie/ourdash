---
name: protocol:autopilot
description: "Autopilot Mode — named trigger that front-loads all clarification into one consolidated round then drives the full RIPER-5 flow unattended. Defines trigger phrases, provisional goal block format, mode marker syntax, per-gate decision policy, hard stops, and deactivation rules."
date: 11-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 9
  required: false
  read_when: "user says 'autopilot', 'run autopilot', 'full autopilot', 'autonomous mode', '/autopilot', or ENTER AUTOPILOT MODE; or when reading orchestration.md §Autonomy Mode to understand autopilot integration"
---

# Autopilot Mode

## Purpose

Autopilot Mode is a named trigger that transforms a RIPER-5 run into a fully autonomous session. When a user says "run autopilot on [task]" (or an equivalent phrase) at any point in the RIPER-5 flow, the orchestrator: (1) asks every clarification question it could possibly need — exactly once, in one consolidated round; (2) emits a copy-pasteable provisional goal block that locks the session goal, the remaining phases, and the decision policy for every known gate; and (3) drives the full RIPER-5 flow — all required phases, both fix loops (PVL and EVL), and all preserved hard stops — without asking another question until the run completes or a hard stop fires.

---

## Trigger Phrases

The orchestrator recognizes autopilot intent from any of the following:

- `ENTER AUTOPILOT MODE` (canonical — preferred form)
- `run autopilot on [task]`
- `full autopilot`
- `yolo autopilot`
- `autonomous mode`
- `/autopilot`
- `fully autonomous run`
- `autopilot this`
- Natural-language equivalents at session start or any RIPER-5 phase boundary (e.g. "just run this fully on autopilot", "I want you to handle this autonomously")

**Lane variants** (see `§Lanes`): `autopilot quick: [task]`, `autopilot fast: [task]`, `autopilot full: [task]` — same standalone/sentence-initial detection rule applies.

Trigger detection fires at session start or at any phase boundary (after RESEARCH, SPEC, INNOVATE, PLAN, or VALIDATE). The orchestrator does not require the phrase to appear at the start of the message.

---

## Lanes

Autopilot Mode supports three lanes. Specify the lane by adding a suffix to the trigger phrase:

| Trigger form | Lane | Flow |
|---|---|---|
| `autopilot quick: [task]` | `quick` | scout → edit → scoped check (QUICK FIX lane) |
| `autopilot fast: [task]` | `fast` | R → S → I → P → V → EXECUTE + EVL (FAST MODE) |
| `autopilot [task]` | `full` | complete RIPER-5 (current default) |
| `autopilot full: [task]` | `full` | complete RIPER-5 (explicit) |

Lane suffix detection (standalone or sentence-initial rule applies — same as §Trigger Phrases):
- Before standard trigger-phrase matching, check whether the message begins with `autopilot quick:`, `autopilot fast:`, or `autopilot full:`.
- When matched, extract the task description after the colon (trim leading whitespace), set the lane, then continue the standard Trigger-Anywhere Detection Flow (situation review → CLR).
- Suffix variants cannot be embedded in descriptive text ("the autopilot fast: pipeline is broken" does NOT trigger fast lane).

**Lane behavior table:**

| Lane | Flow | Artifacts | Pauses |
|---|---|---|---|
| `quick` | scout → edit → scoped check | none (no plan / contract / EVL) | zero (EXECUTE CONSENT covers the one confirm) |
| `fast` | R → S → I → P → V → EXECUTE + EVL | plan file + validate-contract | zero (EXECUTE CONSENT satisfies post-VALIDATE pause) |
| `full` | complete RIPER-5 (current default) | all standard artifacts | standard gates |

**Escalation rule:** If quick-lane scope guard triggers (`QUICK_FIX_ABORT`), the orchestrator escalates one lane up (quick → fast). If fast-mode detects the task requires full RIPER-5 ceremony (3+ phase program, high-risk surface not in contract), the orchestrator escalates (fast → full). In both cases:
- Locked clarifications from the CLR carry over — no re-asking.
- The orchestrator emits a one-line notice: `escalated to [lane]: [reason]` (not a new signal string — this is plain prose).

**LANE goal-block field:** The optional 10th field in the provisional goal block. Position: after `START:`.

```
LANE: quick|fast|full
```

When absent, defaults to `full` (backward compatible — old goal blocks without LANE still pass the D1 validator). When present, only `quick`, `fast`, and `full` are valid values; any other value causes the D1 validator to FAIL.

**CLR lane question:** When task size is ambiguous, the consolidated clarification round gains one extra choice:
> "Lane: quick / fast / full — suggested [X] from size signals. Confirm or override."

See `§Trigger Phrases` for the canonical list — lane-suffix variants are trigger examples: add `autopilot quick: [task]` / `autopilot fast: [task]` / `autopilot full: [task]`. See `§Provisional Goal Block Format` for the optional `LANE:` 10th field.

---

## Trigger-Anywhere Detection Flow

When a trigger phrase is detected:

1. **Detect trigger phrase** in user message (see §Trigger Phrases above).
2. **Invoke `vc-review-situation`** to read on-disk artifacts and determine the current phase. Detection order (apply first matching condition):
   - `## Validate Contract` with `Gate: PASS` or `Gate: CONDITIONAL` present → post-VALIDATE
   - Plan file present (in `process/general-plans/active/` or `process/features/*/active/`) → post-PLAN or later (check for INNOVATE Decision Summary and SPEC file to refine)
   - INNOVATE Decision Summary present → post-INNOVATE
   - SPEC file (`*_SPEC_*.md`) present → post-SPEC
   - Research report or research findings written → post-RESEARCH
   - None of the above → session-start (no prior artifacts)
3. **Enter consolidated clarification round** (see §Consolidated Clarification Round).
4. **Emit provisional goal block** to chat (see §Provisional Goal Block Format).
5. **Write goal block to disk** (see §Disk Persistence Rule).
6. **Emit `AUTOPILOT_ACTIVATED` signal** (see §AUTOPILOT_ACTIVATED Signal).
7. **Begin autonomous run** (see §Autonomous Run Rules).

---

## Consolidated Clarification Round

Exactly one structured ask. The orchestrator NEVER issues a second clarification mid-run (except when a hard stop fires — see §Hard Stops List).

The single ask must contain:

- **(a) One-sentence restatement of intent** — confirm the orchestrator understood what the user wants.
- **(b) All clarifying questions** the orchestrator needs before running unattended, grouped by topic (task scope, constraints, out-of-scope items, any known unknowns).
- **(c) Autonomy boundaries confirmation** — explicitly asks the user to confirm the three hard-stop conditions (see §Hard Stops List) and whether any additional gates should remain manual-first. This is Dimension 6 of `vc-intent-clarify` and is marked CRITICAL.
- **(d) Strategy options for the first remaining phase** — presents the full 4-option suite (sequential / parallel-subagents / workflow / agent-team) with cost estimates, per `vc-agent-strategy-compare`.

After the user responds, all answers are locked. No follow-up questions until the run completes or a hard stop fires.

The clarification round IS the `vc-intent-clarify` invocation for this session. Its output must conform to `validate-intent-clarify-output.mjs` (restatement line present, ambiguity score 0-7, mode chosen, Dimension 6 present and marked CRITICAL).

---

## Provisional Goal Block Format

The provisional goal block is a copy-pasteable contract emitted to chat immediately after the clarification round resolves. It has 9 required fields (all field names are exact string anchors — do not rename or abbreviate):

```
SESSION GOAL: [concise task description]
ENTRY PHASE: [phase name and which phases are already complete in parens]
REMAINING PHASES:
  [ ] [phase name] — [strategy e.g. "agent team (3 sonnet planners)"]
  [ ] ...
CLARIFICATIONS LOCKED:
  1. [locked decision 1]
  2. ...
EXECUTE CONSENT: standing-granted via autopilot trigger ([date])
DECISION POLICY: [summary of per-gate automation rules]
HARD STOPS:
  - Irreversible/outward-facing actions require manual confirmation
  - Cascade BLOCKED (2 consecutive phases BLOCKED-skipped)
  - needs-live-provider feasibility probe
TEST GATES: TBD — populated after VALIDATE
START: [current phase / next action]
LANE: quick|fast|full
```

**Field rules:**

- Total block must be ≤ 4000 characters (hard limit — same as /goal block ceiling). Compress if needed.
- The 9 required field names (`SESSION GOAL:`, `ENTRY PHASE:`, `REMAINING PHASES:`, `CLARIFICATIONS LOCKED:`, `EXECUTE CONSENT:`, `DECISION POLICY:`, `HARD STOPS:`, `TEST GATES:`, `START:`) are exact string anchors. Phases 2–6 and the D1 validator assert against these exact strings.
- `LANE:` is an **optional** 10th field, placed after `START:`. Valid values: `quick`, `fast`, `full`. When absent, defaults to `full`. When present with an invalid value, the D1 validator FAILs.
- `EXECUTE CONSENT:` must contain the literal text `standing-granted` to pass the D1 validator.
- `TEST GATES:` contains `TBD — populated after VALIDATE` when autopilot is triggered before VALIDATE runs; after VALIDATE V7 completes, the (UPDATE) variant contains the real gate commands from the validate-contract.
- `REMAINING PHASES:` uses checkboxes — `[ ]` for pending, `[x]` for complete — and names the strategy for each phase.

---

## Disk Persistence Rule

Immediately after emitting the provisional goal block to chat, write it to disk at:

```
{active-task-folder}/{slug}_AUTOPILOT_GOAL_{dd-mm-yy}.md
```

Where:
- `{active-task-folder}` is the task folder for the current feature's active plan (e.g. `process/features/development-process/active/autopilot-mode_11-06-26/`).
- `{slug}` matches the plan slug.
- `{dd-mm-yy}` is today's date.

The disk file header must state: `Emitted: [datetime]. This is the provisional block. V7 of VALIDATE will emit the (UPDATE) variant.`

This disk file enables session resume (re-paste its contents as the /goal block to resume an interrupted autopilot run).

---

## Mode Marker Syntax

Every orchestrator response during an autopilot run begins with:

```
[MODE: AUTOPILOT | X]
```

Where `X` is replaced by the current RIPER-5 phase name: `RESEARCH`, `SPEC`, `INNOVATE`, `PLAN`, `VALIDATE`, `EXECUTE`, or `UPDATE PROCESS`.

Every spawned subagent during an autopilot run must also prefix its responses with `[MODE: AUTOPILOT | X]` (enforced via the `[AUTOPILOT CONTEXT]` injection block — see §[AUTOPILOT CONTEXT] Injection Schema).

---

## [AUTOPILOT CONTEXT] Injection Schema

Every subagent spawn during an autopilot run prepends the following single-line block to the subagent prompt:

```
[AUTOPILOT CONTEXT] Autopilot mode is active for this run — standing EXECUTE consent granted; decision policy: <paste DECISION POLICY field from goal block>; prefix every response with [MODE: AUTOPILOT | <PHASE>]. Auto-proceed on all reversible decisions; surface only hard stops.
```

The `<PHASE>` placeholder is replaced with the phase name the subagent is executing. The `<paste DECISION POLICY field from goal block>` placeholder is replaced with the verbatim DECISION POLICY value from the emitted goal block.

This single-line prepend is the canonical injection format. Do not use a multi-line block or embed additional fields.

---

## AUTOPILOT_ACTIVATED Signal

Emitted once immediately after the provisional goal block is printed to chat:

```
AUTOPILOT_ACTIVATED: [task description] — entry phase: [phase] — goal block emitted
```

The signal is printed to chat (not written to a file). It is listed in the signal inventory at `process/development-protocols/vc-system-behavior/12-reference.md`.

---

## Autonomous Run Rules

Per-gate decision policy for a running autopilot session:

| Gate | Autopilot behavior |
|---|---|
| Combined Clarification Gate (entry) | Consumed before run starts (one-round rule — see §Consolidated Clarification Round) |
| SPEC user review | `SPEC_INTENT_BLOCKED` items become backlog notes; run continues |
| INNOVATE approach selection | Orchestrator self-selects the recommended approach from the Decision Summary |
| Strategy-compare confirms | Orchestrator auto-selects recommended strategy |
| ENTER VALIDATE suggestion | Auto-proceeds |
| PVL supplement cycles | Auto-runs up to 10-cycle cap; gaps beyond cap become known-gaps in phase report |
| ENTER EXECUTE MODE gate | Standing consent granted by autopilot trigger (see EXECUTE CONSENT field in goal block) |
| High-risk evidence pack | **PAUSES and asks — manual-first always** |
| EVL cycles | Auto-runs up to 10-cycle cap; gaps become known-gaps |
| Post-EXECUTE cleanup | Auto-classifies; routes to UPDATE PROCESS autonomously or surfaces DONE_WITH_CONCERNS if ambiguous |
| Feasibility-probe (needs-live-provider cost class) | **PAUSES and asks — manual-first always (double opt-in per vc-feasibility-test)** |
| Cascade BLOCKED (two consecutive phases BLOCKED-skipped) | **PAUSES and asks — program-level hard stop** |

---

## V6/V7 UPDATE Variant

When VALIDATE V7 completes during an autopilot run, the orchestrator emits the `(UPDATE)` variant of the goal block:

- The `(UPDATE)` variant is identical to the provisional block except:
  - `SESSION GOAL:` is prefixed with `(UPDATE) `
  - `TEST GATES:` is replaced with the real gate commands from the new validate-contract
  - `START:` reflects the post-VALIDATE state
- The `(UPDATE)` variant is written to disk as a new `## (UPDATE) [YYYY-MM-DD]` section APPENDED to the goal block file (never overwritten). The original provisional block remains on disk for resume history.
- The provisional block in chat history is NOT edited (chat is immutable); the `(UPDATE)` variant is a new chat message.

---

## Phase-Program Interaction

When autopilot is triggered for work that has 3+ phases (a phase program):

- The provisional goal block file (`{slug}_AUTOPILOT_GOAL_{dd-mm-yy}.md`) is written to disk at session start, same as single-phase runs. This file remains the durable resume artifact.
- After the umbrella plan is written (outer PLAN step), the `## Stable Program Goal` section is ALSO written to the umbrella plan file. This section is the in-band goal reference for orchestrator routing during inner phases.
- Both artifacts coexist. The provisional goal file is the resume/session artifact; the umbrella `## Stable Program Goal` is the program-level charter reference. They are NOT alternatives — both are required for a valid phase program.
- After each inner phase completes, vc-update-process-agent updates the umbrella plan's `## Current Execution State` (Section 6 format: 8 fields covering phase N status, EVL status, phase report path, next phase). The provisional goal file is NOT re-written per-phase — it is a snapshot from session start.
- Under a running phase program, the [AUTOPILOT CONTEXT] injection prepend is used for every inner-loop subagent spawn (same as single-phase runs).

---

## Deactivation Rules

Autopilot deactivates when any of the following occurs:

1. The run completes UPDATE PROCESS for the final phase (normal completion).
2. The user explicitly says "stop autopilot", "pause autopilot", "exit autonomous mode", or similar.
3. A hard stop fires and the user chooses to abort rather than resume.
4. The session ends (deactivation is per-session — re-paste the goal block from disk to resume).

After deactivation, the orchestrator returns to standard RIPER-5 orchestration behavior (no [MODE: AUTOPILOT | X] prefix, no standing EXECUTE consent).

---

## Hard Stops List

Three conditions always pause and ask regardless of autopilot being active:

1. **Irreversible or outward-facing action** — e.g. sending external communications, permanent deletion, production deployment, spending credits at a live provider, secret rotation with real-world effect.
2. **Cascade BLOCKED** — two consecutive phases in a phase program are both BLOCKED-skipped.
3. **Feasibility probe requires `needs-live-provider` cost class** — double opt-in per `vc-feasibility-test` protocol. The orchestrator surfaces the probe hypothesis and cost-class to the user and waits for explicit approval before dispatching.

These are not deferrals-to-backlog. They are loop-control safety bounds that surface to the user.
