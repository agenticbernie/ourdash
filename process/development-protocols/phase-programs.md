---
name: protocol:phase-programs
description: "How to run large multi-phase programs: umbrella plan, per-phase split, 10-step loop, blocker handling, and foundation-vs-expansion boundaries."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 5
  required: false
  read_when: "planning or executing a multi-phase program (3+ dependent phases)"
---

# Phase Programs

## Purpose

Use this protocol for large, multi-phase efforts where one normal RIPER cycle is not enough.

Examples:

- test-infrastructure overhauls
- large migrations
- repo-wide platform hardening
- multi-surface feature programs
- architecture work that needs repeated validation and durable reporting

This protocol standardizes the stronger flow used in the Autonomous Testing Foundation:

1. design the overall program
2. split it into explicit phase plans
3. run a mini execution loop inside each phase
4. preserve learnings after every phase so progress survives compaction

## Kickoff Prompt

Full kickoff template: invoke `vc-generate-phase-program`.

## Kickoff Recommendation Format

Before creating any plan files for a new large program, present a short recommendation with:

1. **Program fit**
   - should this be `standard complex` or a `phase program`
   - why

2. **Recommended structure**
   - feature folder name
   - umbrella plan name
   - proposed phase list in order

3. **Recommended immediate next action**
   - what should happen now
   - what should wait until later

4. **Approval checkpoint**
   - ask whether to proceed with creating the plan artifacts

5. **Compressed session-goal block** — full shape and hard-rule (4000 char limit):
   invoke `vc-generate-phase-program`.

### Autonomous Session-Goal Variant

This is an explicit opt-in variant. It does NOT weaken the default supervised loop; it only applies
when the user sets a persistent autonomous session-goal (e.g. a standing `/goal`).

Full autonomy rules, GREEN/RED tier table, and safety constraints: invoke `vc-generate-phase-program`.

## When To Use A Phase Program

Prefer a phase program when any of these are true:

- the work naturally breaks into 3 or more dependent phases
- each phase needs its own validation gate before the next phase starts
- the work spans multiple packages, services, or runtime surfaces
- the user wants high-confidence progress with durable checkpoints
- repeated research is needed because new facts will emerge during execution

Do not use this protocol for a simple one-session feature or a small bug fix. Use the normal RIPER
flow instead.

## Core Model

Treat the large effort as two layers:

- **Program layer**: one umbrella project goal plus one orchestration plan
- **Phase layer**: many smaller plans, each with its own read -> execute -> validate -> report loop

The orchestrator does not run the whole program as one giant EXECUTE phase. It advances one phase at
a time.

## Required Artifacts

For a phase program, create or confirm:

1. a feature folder under `process/features/{feature}/`
2. ONE program task folder in `active/` (`{program-slug}_{date}/`) holding ALL program artefacts FLAT
3. one umbrella orchestration plan FLAT in that folder, which **must include a
   Program Goal Charter** (see "Program Goal Charter" above)
4. one plan file per phase, FLAT in the same program folder (no per-phase subfolders)
5. reports co-located FLAT in the program folder as `phase-NN-{slug}_REPORT_{date}.md`
6. references co-located FLAT in the program folder as `{slug}_REF_{date}.md`

Recommended folder layout (FLAT program-folder convention — ONE task folder holds everything):

```text
process/features/{feature}/
  active/
    {program-slug}_{date}/
      {program-slug}-umbrella_PLAN_{date}.md
      phase-01-{slug}_PLAN_{date}.md
      phase-01-{slug}_REPORT_{date}.md   <- co-located FLAT after execution
      phase-02-{slug}_PLAN_{date}.md
      phase-02-{slug}_REPORT_{date}.md
      phase-blast-radius-registry.md     <- one registry for the whole program
      {slug}_REF_{date}.md               <- references, also FLAT
  completed/
  backlog/
```

There are NO per-phase subfolders. Every phase plan, report, the registry, and references live FLAT
inside the single `{program-slug}_{date}/` folder, which moves as a unit on completion.

## Program Goal Charter

Every phase program must carry a **Program Goal Charter** as part of its umbrella orchestration plan.
The charter is the durable "north star" the user would otherwise hand-paste at the start of every
run. Generate it automatically when building the umbrella plan, fill in only program-specific content,
and keep it tight.

The charter is program-specific intent and safety only, not workflow rules. Do NOT re-paste the
7-step inner loop (`R → I → P → PVL → E → EVL → UP`) or execution discipline prose into the charter
— those are governed by this protocol.

Full blank template and filled-in reference example: invoke `vc-generate-phase-program` or read
`.claude/skills/vc-generate-phase-program/references/program-goal-charter-template.md`.

## Program Setup Sequence

Before execution begins:

1. run research to understand the full problem space
2. create the umbrella plan
3. split the work into phase plans with explicit dependencies
4. define what each phase green check proves
5. define what remains out of scope even if the phase passes

Every phase plan should include:

- objective
- dependencies
- exact validation gates
- durable report target
- blockers that would justify `BLOCKED`
- explicit line between "foundation proof" and "future follow-up" when relevant

## The Required Per-Phase Loop

The canonical per-phase loop is the **7-step inner loop** `R → I → P → PVL → E → EVL → UP`. It
SKIPS SPEC — SPEC runs once in the outer program loop (`R → S → I → P → V → E`), not per phase.
Full prose expansion: invoke `vc-generate-phase-program`.
The 7 steps are: 1 RESEARCH → 2 INNOVATE → 3 PLAN-SUPPLEMENT → 4 PVL (validate-contract) →
5 EXECUTE → 6 EVL (validate + regression + regression-found workflow) →
7 UPDATE-PROCESS (durable capture + commit + inter-phase UPDATE PROCESS + move-on).

This loop is mandatory. Do not jump straight from phase plan to implementation without a fresh
research pass on large programs.

### Phase Loop Progress Shape (7-step inner loop — phase programs, authoritative)

Each phase plan's `## Phase Loop Progress` section must track the canonical 7-step inner loop:

1. `1. RESEARCH` — research-agent: prior phase reports read, context loaded, plan drift checked, findings documented
2. `2. INNOVATE` — innovate-agent: approach decided, Decision Summary written
3. `3. PLAN-SUPPLEMENT` — plan-agent: gaps/pre-conditions from research/innovate written into checklist (or "n/a — research clean")
4. `4. PVL` — vc-validate-agent: full V1-V7; validate-contract written per `.claude/skills/vc-validate-findings/references/example-validate-output.md`
5. `5. EXECUTE` — all checklist items done; per-section test gates run and green (or gaps documented)
6. `6. EVL` — all EVL gates green; regression checked; follow-up stubs registered; EVL HANDOFF SUMMARY written
7. `7. UPDATE-PROCESS` — phase report written, umbrella state updated, commit done

Secondary view: the orchestrator's spawn-decision shorthand may collapse this to a coarser
research → validate → execute → update-process spawn view, but the 7-step inner loop above is the
authoritative per-phase loop.

### Single-Plan Phase Loop Progress (6-step — normal RIPER single plans)

NOTE: This 6-step shape is the SINGLE-PLAN loop, NOT the phase-program inner loop. The program
inner loop is the 7-step `R → I → P → PVL → E → EVL → UP` above. Do not conflate the two.

For single plans without a phase program umbrella, the loop template is:

1. `1. research` — research-agent completes
2. `2. innovate` — innovate-agent produces Decision Summary
3. `3. plan` — plan-agent creates plan file
4. `4. validate` — vc-validate-agent: validate-contract written
5. `5. execute` — vc-execute-agent: implementation complete
6. `6. update-process` — archival and context updates

Single-plan note: no plan-supplement step — INNOVATE + PLAN phases are the creation and
refinement cycle; gaps surface naturally there.

## Phase Status Rules

Use phase status honestly:

- `⏳ PLANNED` — not started
- `🔨 CODE DONE` — code exists but verification is incomplete
- `🧪 TESTING` — validation is actively in progress
- `✅ VERIFIED` — phase gates AND regression checks both pass with recorded evidence
- `🚧 BLOCKED` — progress is halted by a real blocker with a next action

A phase can only be `✅ VERIFIED` when both conditions are met:

1. the phase's own validation gates pass with the agreed evidence
2. regression checks against overlapping previously verified surfaces pass (or regressions were fixed and revalidated)

A phase can be `✅ VERIFIED` even when the overall program is not complete.

A program can be complete even when some future work was intentionally split into another feature
folder, as long as that boundary is documented clearly.

## Re-Research Rule

Large programs must re-research at phase entry.

Why:

- code drift may invalidate the old phase plan
- earlier phases often change later assumptions
- validation failures often expose better sequencing
- runtime and infra work can reveal hidden blockers

Minimum re-research inputs:

- selected phase plan
- latest phase report for the same phase, if any
- latest upstream phase reports that this phase depends on
- relevant `process/context/` docs
- recent git diff or commit history if the program spans many turns

## Durable Knowledge Rule

Do not let important learning live only in chat.

Write durable findings to:

- phase task folder (co-located `{slug}_REPORT_{date}.md`) for execution facts, commands, results, blockers, and decisions
- phase task folder (co-located `{slug}_REF_{date}.md`) for research that should inform future phases
- `process/context/` for stable operational knowledge that all future agents should know

## Default Closeout Shape For Phase Programs

After each executed phase, the orchestrator should end with a short closeout packet:

1. selected phase plan path
2. phase status:
   - `✅ VERIFIED`
   - `Keep in active/testing`
   - `🚧 BLOCKED`
   - `Needs reconciliation`
3. what green actually proves
4. regression status: surfaces checked, results, any fixes applied
5. what remains outside this phase
6. whether UPDATE PROCESS is the next required step
7. the exact next phase or follow-up plan if known

This is how a phase program "moves on" without losing durable state or requiring the user to infer
the next step from a long transcript.

If a future phase would fail without the new information, the current phase is not done until that
information is written somewhere durable.

## Blocker Handling

If a phase is blocked:

1. write the blocker into the phase report
2. state exactly what is blocked
3. state what evidence proved the block
4. state the safest next action
5. continue only with unblocked prerequisite or follow-up work that does not violate the phase boundary

Do not force a green status by widening scope or using unsafe local-only shortcuts.

## Regression Checkpoint Standard

After validating the current phase's own gates (step 4), check that previously verified work still holds.

**Scope selection:**

- identify previously verified surfaces that overlap with this phase's blast radius
- run the narrowest representative check for each overlapping surface
- if the phase touches shared infrastructure (DB, container, proxy, auth), include at least one check from each earlier phase that depends on that infrastructure
- if no earlier phases are verified yet, skip this step

Evidence format and what counts as a representative check: invoke `vc-generate-phase-program`.

## Regression-Found Workflow

Full decision tree (classification table + fix/revalidate/route rules): invoke `vc-generate-phase-program`.

Never paper over a regression. Always classify it and record it in the phase report, even if the fix is trivial.

## Safety Defaults

When designing phase validation or runtime targets:

- prefer disposable runtime targets (fresh containers, temp DB, isolated ports) over shared state that earlier phases depend on
- keep costful or manual gates explicit -- do not automate them silently
- never overclaim what a green check proves -- state exactly what it covers and what it does not
- if a phase requires destructive operations (DB reset, container rebuild, config wipe), isolate them so they cannot regress earlier work

## Foundation Versus Expansion

Many large programs should separate:

- **foundation proof**
- **full expansion**

Foundation means the system is safe, honest, and extendable.
Expansion means broad coverage across all product surfaces.

If those are different goals, split them into separate feature folders or follow-up plans instead of
keeping one giant active project alive forever.

## Relationship To RIPER-5

This protocol does not replace RIPER-5. It nests inside it.

- RIPER still governs research, planning, execute approval, and update-process behavior
- the phase program adds structure for repeating those behaviors phase by phase
- UPDATE PROCESS is especially important here because phase outputs must survive compaction

Think of it like this:

- normal RIPER: one feature, one plan, one execution cycle
- phase program RIPER: one big feature, many plans, many controlled execution cycles

## Orchestrator Responsibilities In A Phase Program

The orchestrator must:

- keep one selected current phase
- avoid mixing multiple phases into one execution pass
- ensure each phase has a report path before implementation begins
- ensure validation happens before status promotion
- move completed phase plans out of `active/` when the program reaches a real milestone or closeout
- split future work into a new feature folder when the original program has achieved its scoped goal

The orchestrator must not:

- let a worker infer the current phase from folder state alone
- keep coding across phases without updating reports or plans
- mark the entire program complete just because one foundation slice is green
