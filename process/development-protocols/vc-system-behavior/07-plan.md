---
name: protocol:vc-system-behavior-07-plan
description: "PLAN phase reference: plan artifact requirements, test coverage, and phase-program handling."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing the PLAN phase"
---

# PLAN Phase

## What This Phase Does

The PLAN phase turns the requirements and the chosen "how" into a written plan artifact. No code is written here. The output is a single `*_PLAN_*.md` file.

**PLAN has two input paths:**
- **INNOVATE ran:** PLAN consumes the **Decision Summary** from INNOVATE (the chosen approach) on top of the locked SPEC.
- **INNOVATE was skipped** (mechanical "how" — one obvious path, no design choice): PLAN consumes the **locked SPEC directly**; there is no Decision Summary.

For non-trivial work the SPEC is always present upstream (it is the user-review checkpoint). Only orchestrator-classified trivial fixes have neither a SPEC nor a Decision Summary.

---

## Agent and Tools

**Agent:** `vc-plan-agent` (sonnet)

**Tools:** Read, Grep, Glob, Bash (safe read-only only, plus `date +%d-%m-%y`), Write (only inside `process/*/active/`)

---

## Session Start Skills (Run in Order, All Required)

These run before any planning work begins.

> **Single-trip rule (PHASE-GATES).** All Tier-0 skills below run as preparation but produce exactly one user pause: the Combined Clarification Gate from `03-session-start.md` Step 6.5 (intent restatement + clarifying questions + 4 strategy options in ONE `AskUserQuestion`). Do not pause at P-S0 and again at P-S4. Under `/goal` the gate auto-proceeds. See `12-reference.md` PHASE-GATES.

**[P-S-PREREQ] Input check (SPEC + optional Decision Summary)**

Before everything else, confirm the right input is present for the path taken:

- **Non-trivial work:** confirm the **locked SPEC file** is passed (its path is in the prompt). The SPEC is the mandatory upstream requirements doc.
- **INNOVATE ran:** also confirm the incoming **Decision Summary** has all 4 sections — Chosen Approach / Why This Over Alternatives / Risk Predictions / Key Constraints Accepted. If any section is missing: return `NEEDS_CONTEXT: Decision Summary incomplete — missing [section]`. Do not start planning.
- **INNOVATE was skipped** (mechanical "how"): there is no Decision Summary. PLAN proceeds from the SPEC directly — confirm the SPEC is present and skip the Decision Summary check.
- **Trivial fix:** neither SPEC nor Decision Summary is required.

If non-trivial work arrives with no SPEC and no Decision Summary: return `NEEDS_CONTEXT: no SPEC provided — SPEC is mandatory upstream for non-trivial work`.

**[P-S0] vc-intent-clarify**

Restate what is being planned and produce any clarifying questions — but do **NOT** pause here. They feed the single Combined Clarification Gate (entry gate). If the session is already well-understood, keep this brief.

**[P-S1] vc-context-discovery** (Tier 0) — REQUIRED (Part A + Part B frontmatter)

Load relevant context files. Required.

**[P-S2] vc-plan-discovery** (Tier 0) — REQUIRED (alongside P-S1, Part A + Part B frontmatter)

Run alongside P-S1. Find related plans to avoid duplication.

**[P-S3] vc-review-situation** (Tier 0) — REQUIRED

Confirm the active plan and branch. Understand what was done before.

**[P-S4] vc-agent-strategy-compare** (Tier 0) — REQUIRED (strategy for this phase)

Score a strategy for THIS plan phase (sequential vs parallel vs workflow vs team). Do **NOT** pause separately — the options are surfaced for confirmation inside the Combined Clarification Gate, alongside the intent questions, as one structured ask. Under `/goal` auto-select and auto-proceed.

---

## Skills During Planning (Run as Needed)

**[P1] vc-scout** (Tier 1) — REQUIRED (step 0 — before reading any existing plans)

Find files, modules, and prior work that overlap with what is being planned.

> Pattern divergence rule: If scout shows the planned approach differs from how 2 or more existing files in the same area do it, document the divergence and the reason in the plan's `## Architecture Notes` section. A divergence that is not documented is a plan quality failure.

> **Pattern divergence detection criteria:** A pattern is established if 2 or more files in the same package or blast-radius use the same structural approach. Divergence threshold: the planned approach uses a different structural approach than 2+ existing files in the same domain. vc-scout output must be explicitly compared to the planned approach before concluding divergence. If there are 0 relevant files, no divergence note is needed.

**[P2] vc-generate-plan** (Tier 1) — REQUIRED

All plan creates and updates go through this skill's schema.

**[P3] vc-test-coverage-plan** (Tier 1) — REQUIRED DURING drafting (TDD-first, not after). Full test-context-discovery + exhaustive 3-strategy scenario enumeration is required by design.

Tier assignments go in while the plan is being written, not appended at the end.

**By-design requirement:** Before assigning ANY tier, this skill MUST run full test-context-discovery over ALL testing context files — the `process/context/tests/all-tests.md` router AND its full downstream chain (container-e2e.md, browser-automation.md, live-e2e, etc.) — not just the router. Reading the router without following it to the deeper test docs is a defect, not an acceptable shortcut. After discovery, it MUST exhaustively enumerate ALL possible test scenarios — for EVERY developed surface across the blast radius (backend, container, browser, frontend) — across the THREE active strategies — AUTOMATED (fully-automated, including E2E/integration), HYBRID, and AGENT-PROBE. Known-Gap is NOT a strategy: it is only the residual bucket for genuinely-untestable items. This discovery + enumeration is mandatory, not optional.

Part A must run before Part B. Part A steps:

1. Run `find process/context/tests/ -type f | sort` to find all test context files.
2. Load `process/context/tests/all-tests.md` AND follow its routing table all the way down the chain to every relevant deeper file (container-e2e.md, e2e-tests.md, browser-automation.md, live-e2e, etc.) based on blast radius. Stopping at the router is a defect.
3. Load infra/container context if the blast radius touches runtime services.
4. Run `find apps/ packages/ -path '*/tests/*' -o -path '*/__tests__/*' -o -name '*.test.*' -o -name '*.spec.*' | sort` to find existing test files.
5. Exhaustively enumerate all candidate test scenarios across the three active strategies (AUTOMATED / HYBRID / AGENT-PROBE) before any tier is assigned. Items that fit no strategy fall to the Known-Gap residual bucket.

If Part A was not completed: emit `TIER_ASSIGNMENTS_BLOCKED` and stop. Do not generate tier assignments from memory.

When TIER_ASSIGNMENTS_BLOCKED fires, the plan-agent reports BLOCKED and routes back to RESEARCH to load the missing test chain. The plan-agent does not self-load it.

**Tier definitions:**

The first three tiers are the THREE active testing strategies (Fully-Automated / Hybrid / Agent-Probe). Known-Gap is NOT a strategy — it is the residual bucket for items that are genuinely untestable under all three strategies.

| Tier | What it means | Format required |
|---|---|---|
| Fully-Automated (AUTOMATED) | Runs in CI without human input; includes E2E/integration gates | Exact shell command with file path and runner |
| Hybrid (HYBRID) | Automated command + a required manual check | Command + description of the manual check |
| Agent-Probe (AGENT-PROBE) | A spawned agent observes behavior; no automated assertion | Probe scenario + expected signal |
| Known-Gap (residual, not a strategy) | No test exists or is feasible under any of the three strategies | Reason + what infra change would close the gap |

"Exact commands" means the full shell command with path and flags. Not "run tests."

**Hard E2E gate.** EVERY blast-radius area that develops behavior — backend, container, browser, frontend, every surface — MUST get comprehensive test coverage across the three active strategies (Fully-Automated / Hybrid / Agent-Probe) AND MUST assign at least one Fully-Automated E2E/integration gate wherever the surface is automatable. Agent-Probe is reserved for surfaces that genuinely cannot be fully automated; Known-Gap is a rare residual that must be explicitly justified. A plan that develops behavior but assigns zero test gates ("vacuously green") is banned. Agent-Probe or Known-Gap may NOT be the sole or terminal tier for an automatable developed surface. This is a classification gate, not a `/goal` stop:

- Under `/goal`, when a developed-behavior area lacks its required automated E2E gate, the plan does NOT halt. Instead: (1) a test-building backlog stub is created for the missing automated E2E coverage, (2) the area is classified "not-archivable / keep in active-testing", and (3) the loop CONTINUES. It never blocks the program.
- Outside `/goal`, surface the missing automated E2E gate as a re-PLAN loop-back trigger at the Phase-End Recommendation Gate.

Part B: assign all 4 tiers for each blast-radius area with exact commands.

Part C: for every agent-probe or known-gap tier, describe what test infra change would let it move toward fully-automated. Put this in `## Test Infra Improvement Notes`.

Part D: `## Verification Evidence` must include representative test scenarios, not just commands. Readers should understand what is being proved. The section is a table where each test gate row carries, at minimum:

| Column | Meaning |
|---|---|
| Gate / scenario | The test command (exact) plus the representative scenario it proves |
| Strategy | One of `automated` / `hybrid` / `agent-probe` (or `known-gap` for residual items) |
| Proves SPEC criterion | The SPEC acceptance-criterion id this gate proves (requirement→test traceability) |

Every gate MUST reference the SPEC acceptance-criterion id it proves, closing requirement→test traceability from the plan side. A gate with no linked criterion id is a plan quality failure.

**[P4] vc-generate-phase-program** (Tier 1, conditional) — REQUIRED when shape = PHASE PROGRAM

Run this BEFORE writing any file. It emits a kickoff recommendation. The kickoff recommendation is surfaced at the entry Combined Clarification Gate (or auto-proceeds under /goal) — it is not a separate mid-phase user pause.

Templates used:
- `vc-generate-phase-program/templates/umbrella-plan-template.md`
- `vc-generate-phase-program/templates/phase-stub-template.md`
- `vc-generate-phase-program/references/program-goal-charter-template.md`

**[P5] vc-agent-strategy-compare** (Tier 0) — REQUIRED when phase program shape detected

Run BEFORE creating any files. This picks the execution strategy for the program (how the N phase plans will be created).

> **Second distinct call:** This is a second `vc-agent-strategy-compare` call, distinct from Tier-0 P-S4. P-S4 sets strategy for THIS PLAN phase's drafting. P5 sets strategy for PHASE PROGRAM execution (how the N phase plans will be created — agent-team vs parallel-subagents). Pass explicitly distinct context.

If phases have dependencies: recommend sequential-first ordering.

**[P6] vc-predict** (Tier 1) — REQUIRED for COMPLEX plans

Run before writing the Implementation Checklist. Five-persona debate. Output goes into the plan's Risk Predictions section.

Note: INNOVATE's vc-predict debates which approach to pick. PLAN's vc-predict debates how to implement the chosen approach. Pass the chosen approach and planned implementation details, not the approach alternatives. When INNOVATE was skipped (mechanical "how"), PLAN's vc-predict debates the implementation of the SPEC's single obvious path — there is no chosen-approach handoff, so pass the SPEC's behavioral outcomes and the planned implementation.

**[P7] vc-scenario** (Tier 2) — REQUIRED for 2-3 highest-risk checklist items

Add edge cases into the checklist and test gates.

**[P8] vc-security** (Tier 2) — REQUIRED if auth/billing/secrets surface touched

Run before writing the Public Contracts and Blast Radius sections.

**[P9] vc-sequential-thinking** (Tier 1) — REQUIRED if 3+ interdependent phases

Verify ordering before writing the phase sequence.

**[P10] vc-docs-seeker** (Tier 1) — REQUIRED (mandatory, not conditional)

Run before any checklist step that references a library API signature.

**[P11] vc-validate-findings** (Tier 2) — OPTIONAL (recommended for COMPLEX plans)

Self-check before handoff. Catches gaps before vc-validate-agent runs the full suite.

---

## Plan Shape Decision Table

> **Classification options (3-way):** Plans can be SIMPLE, COMPLEX, or PHASE PROGRAM. Use the table below to auto-detect the right shape. If you must ask the user, provide a brief definition of each option.

Three shapes are available. Pick based on these signals:

| Shape | When to use | Key signals |
|---|---|---|
| SIMPLE | 1 file area, fits in 1 session, no real design choices | 8-15 steps, no cross-package blast radius |
| COMPLEX | Multiple sections, 1 session, scope is known | Sequential steps, design choices required |
| PHASE PROGRAM | 3+ independent phases, multi-session, /goal execution | Each phase can re-run alone; a program-level charter adds value |

Auto-detect using Large Program Detection signals. Do not ask the user unless signals are unclear. If asking, provide brief definitions for each option.

---

## What Every Plan Must Include

- `## Implementation Checklist` — concrete file paths, edit targets, and test gates per step
- `## Touchpoints` — every file to be created or modified
- `## Public Contracts` — API surfaces, schema changes, exported types affected
- `## Blast Radius` — packages and services that can break
- `## Verification Evidence` — per-step test commands (exact) plus representative scenarios; each gate row links a `Strategy` (automated/hybrid/agent-probe) and the `Proves SPEC criterion` id it proves (requirement→test traceability)
- `## Test Infra Improvement Notes` — how to move agent-probe and known-gap tiers toward fully-automated
- `## Resume and Execution Handoff` — last completed step, next step, test gate status

Phase programs also need these in the umbrella plan:

- `## Stable Program Goal` — contains the /goal block (written once, not changed)
- `## Current Execution State` — rewritten by update-process-agent after each phase
- `## Phase Ordering` — which phases depend on prior outputs, which are independent
  (Legacy alias: "Phase Sequence" — do not use "Phase Sequence" in new content. The canonical name is "Phase Ordering".)

---

## Phase Ordering Note (Phase Programs Only)

Later phases build on prior phase outputs: plan updates, report findings, test infra improvements, test updates. The orchestrator must read prior phase reports before starting each new phase.

Ordering rule: phases with sequential dependencies run first, in dependency order. Independent phases run later, or in parallel if strategy-compare recommends it. Never schedule a dependent phase before its dependency completes.

---

## Phase END — Phase-End Recommendation Gate (single round-trip)

**[P-END]** The one exit pause for PLAN. Present in a single block for **confirm / push back / go**:

1. **Plan summary** — the artifact path + extracted Implementation Checklist shown in chat.
2. **Recommended next step (marked recommended), bidirectional:**
   - **Advance** to VALIDATE/PVL — when the plan artifact is written and `validate-plan-artifact.mjs` passes.
   - **Re-run PLAN (loop back)** — when `validate-plan-artifact.mjs` fails, the test-tier matrix has gaps, or `## Test Infra Improvement Notes` is incomplete. Name the specific gaps + questions feeding the next entry gate. Bounded by the vc-autoresearch 10-cycle cap.
3. **Recommended strategy** for PVL — full 4-option suite with 7-signal score + cost, one marked recommended, as selectable choices.
4. **Optional deep work** (P11 vc-validate-findings self-check) offered as a *choice*, not a pause.

Under `/goal` this gate auto-proceeds on the recommended option (re-PLAN bounded by the active-loop cap).

---

## Orchestrator Behavior

Before spawning the plan agent:
- Confirm the locked SPEC file path is passed (mandatory for non-trivial work). If INNOVATE ran, also confirm the Decision Summary exists; if INNOVATE was skipped, the SPEC stands in for it.
- Pass the strategy recommendation.
- Check for existing plans (no duplicates).
- Pass feature folder context.
- For phase programs: check prior phase reports before spawning.

Overlap definition: a plan "overlaps" if it has the same `feature` frontmatter field AND its description mentions the same primary subsystem or endpoint. Same feature folder but different subsystem = not an overlap. When in doubt, ask the user: "Found existing plan [X] in [feature] — update it or create a new plan for [Y]?"

Stale overlap: plans older than 90 days with status CONDITIONAL or BLOCKED and no checklist updates since creation are stale. Under /goal, stale overlap always means "create new plan" without asking.

After the plan is written:
- Review the artifact at the stated path.
- Confirm exactly ONE plan file is selected.
- Present the Phase-End Recommendation Gate (recommend PVL).

---

## User Input

PLAN has exactly two user touchpoints — one at entry, one at exit. No mid-phase interruptions.

- **Entry:** the Combined Clarification Gate (`03-session-start.md` Step 6.5). After INNOVATE, `go` / confirm satisfies this; when INNOVATE was skipped, `go` after SPEC satisfies it. The phase-program kickoff recommendation is surfaced here too.
- **Exit:** the Phase-End Recommendation Gate (P-END) — confirm / push back / go on advance-to-PVL vs re-run-PLAN, plus strategy.
- **Mid-phase:** none. (`ENTER EXECUTE MODE` is never auto-triggered and never triggered by `go` — it is the VALIDATE→EXECUTE transition, not a PLAN touchpoint.)
- **Under /goal:** both gates auto-proceed; emit `PHASE_COMPLETE: PLAN — [plan file path] written. Proceed to VALIDATE.`

---

## Exit Gate (machine checklist)

All of these must be true before the PLAN phase is done:

- Plan artifact exists at the correct path
- `validate-plan-artifact.mjs` passes (or failures are documented as a re-PLAN loop-back trigger)
- Implementation Checklist is extracted and shown in chat
- `## Test Infra Improvement Notes` section is present
- vc-agent-strategy-compare was run for PVL and surfaced inside the Phase-End Recommendation Gate (not a separate pause)
- User responded at the Phase-End Recommendation Gate (confirm / push back / go)

---

## Artifact

`*_PLAN_*.md` in `process/general-plans/active/` or `process/features/{feature}/active/`
