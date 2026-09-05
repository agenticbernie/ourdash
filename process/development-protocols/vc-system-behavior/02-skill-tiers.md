---
name: protocol:vc-system-behavior-02-skill-tiers
description: "Skill tier reference: REQUIRED vs CONDITIONAL labels and which skills each phase must invoke."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "deciding which skills are mandatory vs optional for a phase"
---

# VC System Behavior — Skill Tiers

Last updated: 2026-06-08

This file lists every skill in the system and when it must run.
Skills are grouped into three tiers. Each tier has different rules about when to invoke.
Know your tier before you start a phase.

Phase order across this system is: `RESEARCH → SPEC → INNOVATE → PLAN → VALIDATE → EXECUTE → UPDATE PROCESS`. SPEC sits between RESEARCH and INNOVATE: it is a product-discovery requirements pass that reuses RESEARCH findings (it does not re-scout or re-docs-seek) and produces the requirements doc that INNOVATE then consumes.

---

## What Tiers Are

Tiers answer one question: how strictly must this skill be invoked?

- **Tier 0** — runs at the start of every phase, no exceptions.
- **Tier 1** — runs inside specific phases, required there.
- **Tier 2** — runs only when a specific condition is met. You must check the condition yourself.

---

## Tier 0 — Required at Every Phase Entry

These five skills fire at the start of every phase and every loop step.
No phase work begins without them. They run in this order:

1. **vc-intent-clarify** — Confirm what the task is. Restate scope and ask deeper questions. Wait for go-ahead.
2. **vc-context-discovery** — Discover all relevant context files (Part A) and extract plan frontmatter (Part B) into a Context Envelope.
3. **vc-plan-discovery** — Scan for related plans across all feature folders (Part A) and extract their frontmatter (Part B).
4. **vc-review-situation** — Check branch, worktree, and active plan. Advisory only. Does not authorize execution.

5. **vc-agent-strategy-compare** — Compare all 4 execution strategies with a 7-signal score and cost estimates. There is no default strategy. Pick the best fit. Surface ties to the user — do not resolve them silently.

   **Tiebreaker:** When two strategies score equally: prefer the lower-cost option if scope/timeline are unclear. Always surface the tie to the user — never resolve it silently. Point to `vc-agent-strategy-compare` SKILL.md for the full 7-signal rubric.

### Tier-0 Enforcement Rules

Under `/goal` autonomous execution, all 5 Tier-0 skills still fire at every inner loop step entry.
There are no shortcuts for Tier 0.

Under `/goal`, `vc-intent-clarify` emits a brief restatement to the chat log, then auto-proceeds.
It does NOT wait for confirmation. But the restatement MUST still be emitted. That is how the system proves Tier-0 ran.

Under `/goal`, `vc-agent-strategy-compare` likewise auto-selects from the 7-signal score and auto-proceeds — no strategy pause. (Keeps Tier-0 strategy confirmation in sync with the single **Combined Clarification Gate** in `03-session-start.md`.)

**Single confirmation per phase entry:** outside the auto-skip cases, intent clarification and strategy selection are presented together in ONE `AskUserQuestion` block (the Combined Clarification Gate), not two separate pauses. See `03-session-start.md` Step 6.5.

### Abbreviated Mode

For trivial fixes (single-file, under 15 lines, no schema/API/auth changes) and active-plan resumes, all 5 Tier-0 skills still fire — but in a shorter form:

| Skill | Abbreviated behavior |
|---|---|
| vc-intent-clarify | 1-line restatement, auto-proceed, no questions |
| vc-context-discovery | CLAUDE.md routing only, no full group chain |
| vc-plan-discovery | Scan active/ but expect no results; no deep search |
| vc-review-situation | Branch confirmation only |
| vc-agent-strategy-compare | Sequential confirmed without full 7-signal scoring |

**Active-plan resume timing:** Active-plan resume abbreviated mode fires only when: (1) exactly one matching plan file is found AND (2) the user's request contains the plan name or feature name. If either condition is missing, run full `vc-intent-clarify`.

### Conflict Resolution for Active Plan

When `vc-context-discovery` Part B and `vc-plan-discovery` Part B give different `active-plan` values:

1. Use the plan file explicitly passed in the orchestrator prompt.
2. If no plan was passed, use `vc-plan-discovery`'s result (it has a broader scan scope).
3. Record the conflict in the session header.

### Tier-0 Trigger Priority

When multiple abbreviated-mode triggers fire at the same time, the highest-priority one wins:

1. Explicit mode command ("ENTER X MODE")
2. /goal mid-program execution
3. Continuation phrase ("go", "proceed", "continue", "just do it")
4. Trivial fix or active-plan resume
5. Pure information question (not associated with a plan file; distinct from active-plan resume) — auto-route to vc-research-agent or answer directly in main thread.

Only the highest-priority trigger's abbreviated-mode behavior applies. Lower-priority outcomes are superseded by higher-priority.

### Phase Program Exception for Strategy Compare

When creating 3 or more phase plans at the same time, `vc-agent-strategy-compare` MUST recommend **agent-team**. The 4-option evaluation still runs, but agent-team wins on **signal 3** (agent communication required for blast-radius non-overlap across phases). This is a documented override, not a default.

---

## Tier 1 — Required in Specific Phases

These skills are required within specific phases. Skipping one is a phase compliance failure.

| Skill | Required in |
|---|---|
| vc-scout | RESEARCH, INNOVATE, PLAN, EXECUTE — runs as the first scanning step, before any grep or glob. (Not SPEC: SPEC sits between RESEARCH and INNOVATE and reuses RESEARCH findings rather than re-scouting.) |
| vc-docs-seeker | RESEARCH (on first encounter with any library), INNOVATE (library-dependent approach), PLAN (before API-signature checklist steps), EXECUTE (unclear API signatures). (Not SPEC: SPEC reuses RESEARCH findings and does not re-docs-seek.) |
| vc-test-coverage-plan | RESEARCH (test gap analysis before finalizing findings), PLAN (TDD-first during drafting), PVL/V3 (section III tier assignments) |
| vc-generate-spec | SPEC — all SPEC creates and updates go through this skill's templates. Its output is a product-discovery requirements doc (what the user wants + why, readable, with diagrams, for user review) and is the INPUT to INNOVATE — SPEC precedes INNOVATE. |
| vc-generate-plan | PLAN — all plan creates and updates go through this skill's schema |
| vc-generate-phase-program | PLAN — when shape is PHASE PROGRAM, invoke this before writing any file |
| vc-validate-findings | PVL/V2 — both layers are mandatory |
| vc-autoresearch | PVL (runs the plan-validate-fix loop as bookkeeper, `domain: plan`) and EVL (runs the execute-validate-fix loop, `domain: tests`). Owns the iteration counter, plateau/regression detection, TSV log, and 10-cycle cap; phase agents keep their own gate/supplement mechanics. Also usable standalone for spec/doc/UX hardening. See `.claude/skills/vc-autoresearch/SKILL.md` §PVL Wiring / §EVL Wiring. |
| vc-sequential-thinking | PVL/V3 (conflicting verdicts), EXECUTE (ambiguous step ordering) |
| vc-predict | INNOVATE (before Decision Summary), PLAN (COMPLEX plans, before checklist) |
| vc-generate-closeout | UPDATE PROCESS (9-field closeout packet before archiving), EVL step 1 |
| vc-audit-vc | UPDATE PROCESS — only if any agent, skill, or `.claude/` file was modified |
| vc-audit-context | UPDATE PROCESS — only if any `process/context/` file was modified |
| vc-audit-plans | UPDATE PROCESS — at natural session stopping points |

---

## Tier 2 — Situation-Triggered

These skills activate when specific conditions are met.
Before skipping a Tier-2 skill, check whether its condition applies.

| Skill | Run when |
|---|---|
| vc-security | The approach, plan, or section involves auth, billing, secrets, trust-boundary changes, or public API changes |
| vc-scenario | The approach or checklist item touches auth, billing, external APIs, or destructive operations |
| vc-problem-solving | Blocked after 2 or more attempts; scope keeps expanding; no viable approach found |
| vc-risk-evidence-pack | A high-risk class is identified in the plan blast radius or validate findings |
| vc-web-testing | Playwright, Vitest, or k6 test work is within the blast radius |
| vc-frontend-design | A UI/UX implementation task is within EXECUTE |
| vc-agent-strategy-compare (mid-phase) | 2 or more distinct investigation directions found mid-RESEARCH, or 2–3 approaches surfaced mid-INNOVATE |

---

## Simple vs Deep Mode

Several Tier-1 and Tier-2 skills can run in two modes.
All skills that support this follow the same contract.

### Simple Mode

- Runs directly in the invoking agent's context.
- Uses only what is already in the conversation (plan file, recent reads, chat history).
- Use when: narrow scope, clear blast radius, fresh context, non-critical decision.

### Deep Mode

- Spawns a research subagent first, before generating output.
- The research subagent uses vc-scout, vc-sequential-thinking, vc-scenario, vc-predict, and/or domain context reads to investigate the specific surface.
- The skill then generates output using those findings — grounded in actual codebase state, not just plan text.
- Use when: wide blast radius, ambiguous context, high-stakes decision, phase program kickoff, auth/billing/schema surface.

### Which Skills Support Simple/Deep

| Skill | Use Simple when | Use Deep when |
|---|---|---|
| vc-intent-clarify | Ambiguity score 3 or less, narrow scope | Score 4/4, phase program kickoff, 3+ packages, architectural decision |
| vc-scenario | Contained checklist item, narrow blast radius | Auth/billing/schema surface, 3+ files, HIGH_RISK label |
| vc-predict | Contained feature, no prior attempts known | Pattern previously tried in codebase, known failure surface |
| vc-agent-strategy-compare | File count and test infra are clear from context | Signal 3 or 5 cannot be scored without scanning |
| vc-generate-closeout | Session just ended, context is fresh | Resumed session, long execute, multi-phase program |
| vc-validate-findings | Self-contained plan, fresh context | Container/infra blast radius, 5+ packages, phase program |
| vc-review-situation | Quick orientation ("what's next") | Program review, session resume, full handoff needed |

### Enforcement

When invoking a skill that supports simple/deep, you must:
1. Explicitly decide which mode to use.
2. State the reason for the choice.

Default to SIMPLE. Escalate to DEEP only when a deep trigger applies.
Never silently default to deep — it spawns a subagent and costs tokens.
