---
name: protocol:vc-system-behavior-06-innovate
description: "INNOVATE phase reference: approach comparison, decision summary, and predict/scenario usage."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing the INNOVATE phase"
---

# INNOVATE Phase Reference

## What This Phase Is

INNOVATE is where the agent explores **how** to satisfy the locked SPEC. It looks at options, compares them, and recommends one. It does not write plans. It does not write code. It produces a Decision Summary in the conversation.

**Input:** the locked SPEC (the product-discovery requirements doc from the SPEC phase — what the user wants and why) plus the RESEARCH findings. INNOVATE answers "given these requirements, which implementation approach is best?" **Output:** a Decision Summary that feeds PLAN.

INNOVATE runs *after* SPEC (`RESEARCH → SPEC → INNOVATE → PLAN`). It is the skippable phase for non-trivial work: when the "how" is mechanical (one obvious implementation path, no real design choice), INNOVATE is skipped and PLAN proceeds straight from the SPEC.

---

## Agent and Tools

**Agent:** `vc-innovate-agent` (sonnet)

**Tools allowed:** Read, Grep, Glob ONLY

**Tools NOT allowed:** Bash, Write, WebSearch

---

## Session Start (Tier 0 — required before anything else)

These run in order. Do not skip any of them.

> **Single-trip rule (PHASE-GATES).** All Tier-0 skills below run as preparation but produce exactly one user pause: the Combined Clarification Gate from `03-session-start.md` Step 6.5 (intent restatement + clarifying questions + 4 strategy options in ONE `AskUserQuestion`). Do not pause at I-S0 and again at I-S4. Under `/goal` the gate auto-proceeds. See `12-reference.md` PHASE-GATES.

### [I-S0] vc-intent-clarify (Tier 0) — REQUIRED

Run this first. Restate scope and produce any clarifying questions — but do **NOT** pause here. They feed the single Combined Clarification Gate. If continuing from SPEC: give a brief restatement only (the SPEC already locked intent; INNOVATE restates the implementation question it is about to explore).

### [I-S1] vc-context-discovery (Tier 0) — REQUIRED

Same as RESEARCH phase. Part A (directory discovery) + Part B (frontmatter extraction). Both required.

### [I-S2] vc-plan-discovery (Tier 0) — REQUIRED

Same as RESEARCH phase. Part A (scope scan) + Part B (frontmatter extraction). Run alongside I-S1.

### [I-S3] vc-review-situation (Tier 0) — REQUIRED

Check branch, worktree, and active plan state.

### [I-S4] vc-agent-strategy-compare (Tier 0) — REQUIRED

Score the full 4-option suite for this phase's work. Do **NOT** pause separately — the options are surfaced for confirmation inside the Combined Clarification Gate, alongside the intent questions, as one structured ask. Under `/goal` auto-select from the 7-signal score and auto-proceed.

---

## During INNOVATE (ordered by when they run)

### [I1] vc-scout (Tier 1) — REQUIRED

Before proposing anything: find existing patterns, prior implementations, and related conventions in the codebase. Only propose deviating from an existing pattern if there is a clear documented reason.

### [I2] vc-docs-seeker (Tier 1) — REQUIRED on any library-dependent approach

Confirm the API shape of any library before describing that approach in detail. Do not rely on training-data knowledge for API signatures.

### [I2.5] vc-feasibility-test — Conditional (runs BEFORE [I3])

Use this when an approach candidate hinges on an unverified external/runtime mechanism. Emit `VC-FEASIBILITY-PROBE-NEEDED: [hypothesis]` and halt. Do NOT proceed to vc-predict until the verdict returns. See `orchestration.md §VC-FEASIBILITY-PROBE-NEEDED Signal Routing`. Note: VALIDATE (Layer 2) is also a co-emitter of this signal; see `08-validate.md [V2-PROBE]`.

### [I3] vc-predict (Tier 1) — REQUIRED before writing the Decision Summary

Run the 5-persona debate: Architect, Security, Performance, UX, Devil's Advocate. This is a real skill invocation — not a mention in passing. It cannot be skipped. The output goes into the "Risk Predictions" section of the Decision Summary.

**Deep mode:** vc-predict runs in SIMPLE mode by default. If the approach touches a pattern that has failed before in this codebase, or a known risky surface: the INNOVATE agent emits exactly this signal and stops:

```
VC-PREDICT-DEEP-NEEDED: [surface/pattern] — pausing for research subagent.
```

The orchestrator then spawns a research subagent to gather deeper context, then re-spawns the INNOVATE agent with the findings. The INNOVATE agent does not move forward until vc-predict completes. This is an orchestrator-driven re-spawn, **not** a user pause — it does not count against the two-gate single-trip rule; user-facing optional deep work is offered at the Phase-End Recommendation Gate, not mid-phase.

### [I4] vc-scenario (Tier 2) — CONDITIONAL

Use this when any approach candidate touches auth, billing, external APIs, or destructive operations. Include the most significant edge cases in the Cons/Trade-offs section for that approach.

### [I5] vc-security (Tier 2) — CONDITIONAL

Use this when any approach involves auth flows, billing logic, secrets management, or trust-boundary decisions. Any unmitigated STRIDE threat must flag the approach as high-risk.

### [I6] vc-sequential-thinking (Tier 2) — CONDITIONAL

Use this when evaluating three or more competing dimensions at once (for example: cost vs latency vs maintainability vs delivery risk).

### [I7] vc-agent-strategy-compare (Tier 2) — CONDITIONAL (mid-phase)

Use this after two or three approaches have been surfaced, to decide whether to explore them in parallel or sequentially. Score it mid-phase but do **NOT** pause the user here — if a parallel-exploration choice is warranted, surface it as a selectable option in the Phase-End Recommendation Gate (I-END), not as a separate mid-phase round-trip.

### [I8] vc-problem-solving (Tier 2) — CONDITIONAL

Use this when no viable approach has been found after two or more exploration directions. Only report BLOCKED after this is exhausted.

---

## Phase-Lock Rules

These rules are strictly enforced. The INNOVATE agent must not break them.

- Present OPTIONS only. No final decisions. No concrete plans. No code.
- vc-predict MUST be invoked as a real skill call, not summarized or mentioned.
- The Decision Summary MUST exist before signaling readiness for the next phase.

---

## Required at Phase End

### [I-END] Phase-End Recommendation Gate (single round-trip)

The one exit pause for INNOVATE. Present everything in a single block for **confirm / push back / go**:

1. **Decision Summary** (chosen approach + rejected alternatives + Risk Predictions + constraints).
2. **Recommended next step (marked recommended), bidirectional:**
   - **Advance** to PLAN — when two or more viable approaches were genuinely explored and one is clearly chosen with no unmitigated high-risk threat. (SPEC already ran upstream; INNOVATE always advances to PLAN.)
   - **Re-run INNOVATE (loop back)** — when fewer than two viable approaches survive, vc-predict surfaced an unmitigated high-risk threat, or accepted constraints conflict. Name the specific gaps + questions that feed the next entry gate. Bounded by the vc-autoresearch 10-cycle cap.
3. **Recommended strategy** for the next phase — full 4-option suite (sequential / parallel-subagents / workflow / agent-team) with 7-signal score + cost estimates, one marked recommended, presented as selectable choices.
4. **Optional deep work** (vc-scenario, vc-security, vc-sequential-thinking, parallel approach exploration from I7) offered as *choices*, not a pause.

**Three or more phases detected:** If the locked SPEC (its scope / out-of-scope / independent-workstream framing), the Decision Summary, or research findings contain any of these signals — explicit "Phase N" labels, three or more independent work streams with no shared blast-radius files, or a multi-session delivery horizon — the recommended strategy MUST be **agent-team** (one agent per phase plan), routed through this gate. (The SPEC is the earliest place program shape becomes visible; INNOVATE reads it from there.) This is required because phase plan agents need to communicate to avoid blast-radius overlap and dependency conflicts.

Under `/goal` this gate auto-proceeds on the recommended option — including a re-INNOVATE loop, bounded by the active-loop cap.

---

## Decision Summary Format

Copy this format exactly. Every section is required. If the PLAN agent receives a Decision Summary missing any section, it returns `NEEDS_CONTEXT`.

```markdown
## Decision Summary

### Chosen Approach
[Name] — [1-sentence rationale]

### Why This Over Alternatives
| Alternative | Why Rejected |
|---|---|
| [Alt 1] | [1 sentence] |

### Risk Predictions
[vc-predict 5-persona output, verbatim or summarized per persona]

### Key Constraints Accepted
[Trade-offs the plan must honor]
```

---

## Orchestrator Behavior

**Before spawning the agent:**
- Confirm the Decision Summary does not already exist.
- Pass: the locked SPEC file path + research findings + INNOVATE strategy recommendation. INNOVATE explores how to satisfy the SPEC, so the SPEC is its primary input.

**After the agent finishes:**
- Receive the Decision Summary (chosen approach + rejected alternatives + rationale + Risk Predictions).
- Receive strategy recommendation for PLAN.
- If three or more phases were detected: surface the agent-team recommendation.

---

## User Input

INNOVATE has exactly two user touchpoints — one at entry, one at exit. No mid-phase interruptions.

- **Entry:** the Combined Clarification Gate (`03-session-start.md` Step 6.5) — intent go-ahead + strategy selection in one round-trip. Continuing from SPEC via `go` satisfies this.
- **Exit:** the Phase-End Recommendation Gate (I-END) — confirm / push back / go on the recommended next step (advance to PLAN **or** re-run INNOVATE) and strategy; optional deep work offered as choices.
- **Mid-phase:** none.
- **Under /goal:** both gates auto-proceed on the recommended option.

  Note: INNOVATE always advances to PLAN — SPEC ran upstream (outer loop) or is governed by the umbrella SPEC (phase-program inner loop). It never advances "back to SPEC".

---

## Exit Gate

All of these must be true before the phase is complete:

- Two or more genuinely different approaches were explored
- vc-predict was invoked; the debate is included in the Decision Summary under "Risk Predictions"
- Decision Summary is written with all four required sections: Chosen Approach, Why This Over Alternatives, Risk Predictions, Key Constraints Accepted
- vc-agent-strategy-compare was run for PLAN and surfaced inside the Phase-End Recommendation Gate (not a separate pause)
- User responded at the Phase-End Recommendation Gate (confirm / push back / go)

**Under /goal autonomous execution:** The "user says go" condition is auto-satisfied when all the above conditions are met. The agent emits: `PHASE_COMPLETE: INNOVATE — Decision Summary written` and moves on to PLAN (in both the outer loop and the phase-program inner loop — SPEC is never downstream of INNOVATE).

---

## Artifact

The Decision Summary is written in the conversation. No file is written.
