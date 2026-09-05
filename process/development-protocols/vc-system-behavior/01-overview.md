---
name: protocol:vc-system-behavior-01-overview
description: "Authoritative end-to-end system behavior overview: every phase, both test loops, and the hardening summary. Entrypoint for the 12-file split."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: true
  read_when: "needing the canonical end-to-end VC-system behavior reference — start here"
---

# VC System Behavior — Overview

Last updated: 2026-06-08

This folder documents exactly how the RIPER-5 agent system behaves.
Every phase, every required skill, and every loop is described here.
Read this first if you are a new agent or resuming after a gap.
On any context gap — including a silent mid-run context compaction, not just a human re-pasting `/goal` — the loop auto-recovers its position by re-reading the umbrella `## Current Execution State` + `## Phase Loop Progress` + latest phase report, then reconciling that claimed state against actual git state (detail in `03-session-start.md` / `11-phase-programs.md`).

---

## What This System Is

RIPER-5 is a step-by-step development workflow for agents.
It prevents agents from jumping straight to code before understanding what to build.
These docs exist so agents know the rules and can follow them without guessing.

---

## The Full Pipeline

```
USER REQUEST
     │
     ▼
SESSION START (orchestrator main thread)
  intent-clarify → context-discovery → plan-discovery → strategy-compare → review-situation
     │
     ▼
RESEARCH ──► SPEC ──► INNOVATE ──► PLAN ──► PLAN-VALIDATE-LOOP (PVL) ──► EXECUTE ──► EXECUTE-VALIDATE-LOOP (EVL) ──► UPDATE PROCESS
                                       │                  │              │                │
                                plan-validate-fix      /goal block     LEVEL 1          LEVEL 2
                                  loop here             output here  (per-section)     (post-DONE)
                                  (on CONDITIONAL or                 iterate-until    execute-validate-fix
                                   BLOCKED, loop back to V1)         green per sect    loop on EVL fail
```

For a multi-phase program, after the last phase's EVL the program runs one **FINAL CROSS-PHASE E2E** verification gate (whole-system, EVL-style, 10-cycle-capped) before closeout — see `11-phase-programs.md`.

---

## The Two Loop Types

### Outer Loop

Runs once for phase programs (work with 3 or more phases).

```
RESEARCH → SPEC → INNOVATE → PLAN (umbrella + full phase plans, agent-team) → PVL (agent-team) → /goal → [phases execute autonomously] → FINAL CROSS-PHASE E2E → program closeout
```

The outer PLAN step creates all N full **COMPLEX-quality** phase plans at the same time, using an agent team.
The outer PVL validates all N plans at the same time, plus a coordinator for cross-phase concerns.
PVL must pass (or be conditional) before any execution begins.
After the last phase's EVL completes, a **final cross-phase E2E verification gate** runs — a comprehensive whole-system check that proves the integrated program actually works end-to-end before program closeout. It is an EVL-style loop bounded by the same 10-cycle cap (detail in `11-phase-programs.md`).
SPEC (product-discovery: what the user wants + why) runs after RESEARCH and before INNOVATE, locking program intent before any approach exploration or planning begins. INNOVATE then explores HOW to satisfy the locked SPEC. The umbrella SPEC governs all inner phases — the inner loop does NOT repeat SPEC.

### Inner Loop

Runs once per phase, automatically, under a `/goal` block.

```
R → I → P → PVL → E → EVL → UP  (full 7-step sequence every phase, no shortcuts)
```

The inner loop intentionally **skips SPEC** — the umbrella SPEC (locked in the outer loop) governs every inner phase, so SPEC is not repeated per phase. The 7 steps above are the inner-loop steps (R, I, P, PVL, E, EVL, UP); SPEC is not one of them. This is by design, not an omission.

Every non-trivial phase runs the full 7 inner-loop steps.
For phase programs, this inner loop repeats for every phase in the program.
Tier-0 skills fire at the entry of every step — no exceptions.

### Loop Term Glossary

- **PVL** — Plan-Validate-Loop. The validate phase, including any plan-validate-fix loops.
- **EVL** — Execute-Validate-Loop. Post-DONE orchestrator sweep that checks test gates.
- **plan-validate-fix loop** — When PVL returns CONDITIONAL or BLOCKED, the plan agent fixes the plan. PVL re-runs from V1. Loops automatically until PASS or 10-cycle cap.
- **execute-validate-fix loop** — When EVL finds a failing test gate, a scoped fix agent re-runs exactly that gate. Loops automatically until green or 10-cycle cap.

### Validate Verdicts (PVL outcomes)

Every PVL run ends in one of three verdicts:

- **PASS** — plan is sound. Proceed to EXECUTE.
- **CONDITIONAL** (abbreviated **COND**) — plan is mostly sound but has fixable gaps. The plan-validate-fix loop fires; the plan agent patches the gaps; PVL re-runs from V1.
- **BLOCKED** — plan has a fundamental problem that cannot be patched in-loop (missing dependency, unresolved blast-radius conflict). Gets a backlog note; in a phase program, the phase is skipped and the loop advances.

---

## Loop Mode Selection (PVL and EVL)

Both PVL and EVL are loops that can run automatically or with user confirmation. Before the first iteration of each loop, the system determines the mode.

### Mode Selection Rule

**Under /goal (autonomous phase program execution):** Always auto-run. No prompt needed. Both PVL and EVL run without pausing for user input.

**Outside /goal (standalone or first-time setup):** Ask the user once before the loop starts. The choice is sticky for the full loop.

Prompt to present:
> "Ready to run [PVL/EVL]. How do you want to proceed?
> (a) Auto-run — find gaps → fix → re-validate → loop until clean or cap reached. Agent self-decides at each iteration.
> (b) Step-by-step — present findings → you confirm → apply fix → re-validate → loop again or move forward.
> Recommendation: [auto-run | step-by-step] because [one-line reason]."

Always present a recommendation. The recommendation guides the user but does not override their choice.

### Auto-Run Mode (vc-autoresearch behavior)

The loop runs the vc-autoresearch skill pattern:
1. Research/gate step: validate-agent (PVL) or tester agent (EVL) runs checks
2. If gaps found: orchestrator routes back to plan-agent (PVL) or execute-agent (EVL) to fix
3. Plan-agent or execute-agent applies fix, emits completion signal
4. Validate-agent or tester re-runs from the start — back to step 1
5. Continues until: all gates pass (SUCCESS), plateau detected (HALT_PLATEAU), or 10-cycle cap (HALT_CAP)
6. At each iteration: write a short note summarizing what was found and fixed. Always surface recommendation for next iteration.

### Step-by-Step Mode

The loop pauses for user confirmation at two points per iteration:
1. After gap findings are presented: "Proceed to apply fix?" (with recommendation)
2. After fix is applied: "Run validate/test again?" (with recommendation)

If user says "move forward" at any point: accept current state as known-gap with a backlog note, and proceed.

> Reconciliation: these loop-control confirmations are not extra mid-phase user pauses — they fold into the phase EXIT gate (the Phase-End Recommendation Gate). Under `/goal` they auto-proceed and never pause.

> Position reconciliation on resume: on any context gap (including a silent mid-run compaction, not only a human re-pasting `/goal`), the loop auto-recovers its position by re-reading the umbrella `## Current Execution State` + `## Phase Loop Progress` + latest phase report, then cross-checking that claimed state against actual git state (last EVL-green commit / diff) to catch a stale or lying umbrella before continuing (detail in `11-phase-programs.md`).

---

## How to Navigate This Folder

| File | What it covers |
|---|---|
| `01-overview.md` | This file — the full pipeline, two loops, and folder map |
| `02-skill-tiers.md` | All skills grouped by when they run (Tier 0, 1, 2) and simple vs deep mode |
| `03-session-start.md` | What every session does before routing to a phase (7 steps, intent clarify, context discovery) |
| `04-research.md` | RESEARCH phase rules |
| `05-spec.md` | SPEC phase rules (new phase) |
| `06-innovate.md` | INNOVATE phase rules |
| `07-plan.md` | PLAN phase rules |
| `08-validate.md` | VALIDATE phase rules (V1–V7 gates) |
| `09-execute.md` | EXECUTE phase rules |
| `10-update-process.md` | UPDATE PROCESS phase rules |
| `11-phase-programs.md` | How multi-phase programs run under /goal |
| `12-reference.md` | Signal list, backlog items, and quick reference |
