---
name: protocol:vc-system-behavior-11-phase-programs
description: "Phase program reference: umbrella plan, inner loop, blast-radius coordination, and cascade BLOCKED handling."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing a multi-phase program inner loop"
---

# Phase Programs

A phase program is a multi-phase plan where each phase runs the full RIPER-5 loop. Each phase still has the two PHASE-GATES touchpoints — an entry Combined Clarification Gate and an exit Phase-End Recommendation Gate — but once the /goal block is pasted, **both per-phase gates auto-proceed** on their recommended option for every phase. The only interruptions are the intentional hard stops (see §Loop-Control Safety Bounds). See `12-reference.md` PHASE-GATES.

---

## Outer Loop (runs once to lock the program)

```
RESEARCH → SPEC → INNOVATE → PLAN (umbrella + full phase plans, agent-team) → PVL (agent-team) → /goal → [phases execute] → FINAL PROGRAM E2E → closeout
```

Both the outer PLAN and the outer PVL use an **agent team**. After the last phase's inner EVL, the program runs one final cross-phase E2E verification gate (see §Final Cross-Phase E2E Verification) before program closeout.

SPEC runs **once** in the outer loop, **immediately after RESEARCH and before INNOVATE**. It is a product-discovery requirements doc — it captures what the user wants and why (consuming RESEARCH findings + user intent), not a chosen approach. It locks and governs program intent before INNOVATE explores how to satisfy it. The umbrella SPEC governs all inner phases — the inner loop does NOT repeat SPEC (inner loop is `R → I → P → PVL → E → EVL → UP`).

### Outer PLAN — agent team creates N full phase plans at once

The outer PLAN step produces two artifacts via `vc-generate-phase-program`:

1. **Umbrella plan** — charter, `## Stable Program Goal`, `## Program SPEC` (link to / embedded program-level product-discovery requirements doc that governs all inner phases), `## Phase Ordering`, `## Current Execution State`
2. **Full phase plan per phase** — one complete plan file per identified phase, to the same standard as a standalone COMPLEX plan

Each phase plan must contain:
- Session Goal + observable outcome for this phase
- Full Implementation Checklist with concrete steps, file paths, edit targets
- Touchpoints and Public Contracts
- Blast Radius (specific files and packages)
- Test tier assignments per area with exact commands
- Verification Evidence (scenarios and commands)
- Test Infra Improvement Notes
- Resume and Execution Handoff
- Explicit dependencies on prior phases

**Goal Block Coexistence (Autopilot Mode):**
When autopilot is triggered on a phase program, two goal-block artifacts are required:
1. Provisional goal file: `{slug}_AUTOPILOT_GOAL_{dd-mm-yy}.md` in the task folder (written at session start, immutable).
2. Umbrella plan section: `## Stable Program Goal` in the umbrella plan file (written during outer PLAN, fixed until final UPDATE PROCESS).

Do NOT treat the umbrella section as a replacement for the provisional file. Both are durable artifacts serving different purposes:
- Provisional file: session-level resume artifact, immutable across all phases.
- Umbrella section: program-level charter reference for orchestrator routing during inner phases.

**When to use agent team:** `vc-agent-strategy-compare` must recommend **agent-team** — not parallel-subagents — when 3 or more phase plans are being created. Agent team members communicate. Parallel subagents cannot.

Agent team coordination covers:
- Which scope belongs in phase N vs N+1
- Blast radius non-overlap (two phases claiming the same file is a conflict)
- Dependency declarations (what phase N delivers that phase N+1 relies on)
- Test infra decisions that affect multiple phases

**Examples where agent-team is the right call:**
- Creating 3+ phase plans for a large feature (one teammate per phase)
- Running outer PVL across N phase plans (one validator per plan plus coordinator)
- Parallel research across 4+ independent subsystems
- Running EXECUTE across independent modules with no shared files

### Agent Team Coordination Protocol

Each phase-plan agent receives: umbrella plan path + assigned phase number + list of other agents' claimed blast-radius files (if the blast-radius list is not yet available: pass `'TBD — detect and flag conflicts'` as the value).

If an agent detects blast-radius overlap with another phase: flag the file path in a `## Potential Blast Radius Conflicts` section of its phase plan.

The coordinator (the orchestrator) resolves all flagged conflicts before the outer PVL begins.

**Blast-radius registry:** Each agent writes its blast-radius claim to `phase-blast-radius-registry.md` before writing its full plan. Later agents read this file before declaring their own blast radius.

- Feature-scoped: `process/features/{feature}/active/{program-slug}_{date}/phase-blast-radius-registry.md`
- General plans: `process/general-plans/active/{program-slug}_{date}/phase-blast-radius-registry.md`

One registry per program lives FLAT inside the program task folder (see plan-lifecycle.md §Phase-Program Folder Layout).

**Write rule:** Each agent appends a new `## Phase N` section to the registry. Never overwrite the whole file. If the file does not exist: create it with your section as the first content.

**Distributed workflow note:** When using the Workflow tool (distributed execution): the orchestrator must serialize registry writes. Pass the registry file to one agent at a time, or use a dedicated registry-write step. Interleaved concurrent appends in distributed mode can corrupt the registry.

**Before appending:** Read the current registry and check that it ends with a complete `## Phase [N]` section (has at least one non-heading content line after the heading). If the file ends with an incomplete heading with no content below it: complete the previous section with: `status: unknown — interrupted write detected; coordinator must resolve before proceeding`.

**Valid registry status values:**
- (no status field) = active claim — phase is in progress
- `status: BLOCKED-skipped` = phase was skipped due to dependency failure (files never modified)
- `status: DONE` = phase completed successfully
- `status: SUPERSEDED` = phase replaced by a different phase plan
- `status: BLOCKED` = read-compatibility alias for BLOCKED-skipped — do not write this in new entries

Only these four writable values: (no status field) / BLOCKED-skipped / DONE / SUPERSEDED.

**BLOCKED-skipped annotation scope:** This annotation applies only when the phase was BLOCKED at PVL (Step 4) before EXECUTE ran (Step 5). If a phase reached EXECUTE and was BLOCKED mid-execution: do not append this annotation. Mid-execution BLOCKED is noted in the phase report instead.

---

## Pre-PVL Conflict Resolution

After all phase plan agents complete, the orchestrator reads all `## Potential Blast Radius Conflicts` sections. For each flagged conflict, resolve it and write a `## Pre-PVL Conflict Resolution` section to the umbrella plan before spawning vc-validate-agent.

```
## Pre-PVL Conflict Resolution
- Conflict [N]: Phase [A] and Phase [B]
  Files: [list]
  Resolution: reassign to Phase [A] | reassign to Phase [B] | parallel-safe (independent changes)
  Action: update Phase [A/B] blast-radius claim | no action needed
```

Every conflict must have a Resolution and Action before the outer PVL begins.

Valid `Action` values:
- `update Phase [A] blast-radius claim`
- `update Phase [B] blast-radius claim`
- `no action needed`

**Orchestrator write exception:** The orchestrator MAY write the `## Pre-PVL Conflict Resolution` section inline. This is a coordination artifact that enables plan execution, not implementation work. It is a permitted exception to the standard orchestrator-does-not-implement rule.

**`parallel-safe` criteria:** A conflict is parallel-safe only when the two phases write to non-overlapping regions of the same file with no logical dependency between them. If the changes are on overlapping lines, or if one change depends on the other's output: use `reassign` instead.

**Disagreement rule:** If two phases classify the same conflict differently (one says `parallel-safe`, the other says `reassign`): apply the stricter classification. `reassign` always takes precedence. Document as: "Resolution: reassign to Phase [X] — one phase claimed parallel-safe but the other identified a dependency; safety-conservative resolution applied."

**Completion check:** Before spawning vc-validate-agent, confirm that all `Action: update Phase [X] blast-radius claim` entries have actually been applied. If not: the conflict is unresolved.

**No-conflict case:** If no conflicts are found, still write `## Pre-PVL Conflict Resolution` with the note: "No blast-radius conflicts found — all phase plans have clean blast-radius claims."

**BLOCKED conflict re-scope sub-procedure:** When a conflict has no safe resolution:
1. Spawn a single vc-plan-agent for the conflicted phase only (not a full agent-team re-run).
2. Scope to only the conflicted blast-radius section.
3. Outer PVL halts until the re-scoped phase plan is written and the conflict is resolved.
4. After re-scope: re-run conflict resolution for the updated phase only.
5. If conflict persists after 1 re-scope cycle: surface to user with a structured summary of (a) which phases conflict, (b) which files, (c) resolutions tried. Under /goal: this is a hard stop.

---

## Outer PVL — agent team validates N phase plans at once

One validator agent per phase plan runs full V1→V7 for that plan. The coordinator role is the orchestrator — no separate coordinator agent is spawned.

The orchestrator reads all per-plan validator outputs and writes cross-phase findings in the same chat thread:

```
COORDINATOR FINDINGS:
- Cross-phase concern [N]: Phase [A] and Phase [B] | Type: [dependency/overlap/ordering/missing-handoff] | Severity: [FAIL/CONCERN] | Resolution: [recommendation]
```

If coordinator findings include a FAIL: the affected phase plans are marked CONDITIONAL even if their individual validator returned PASS. Coordinator verdicts can override a per-plan PASS to CONDITIONAL. They cannot upgrade BLOCKED to CONDITIONAL.

**BLOCKED plan isolation:** One BLOCKED phase plan does not block the entire outer PVL. The overall outer PVL verdict becomes CONDITIONAL (not PASS) if any plan was BLOCKED. The isolated plan becomes the first target of the plan-validate-fix loop.

The outer PVL must reach PASS or CONDITIONAL before execution begins. If CONDITIONAL: plan-validate-fix loop fires, PVL re-runs from V1. Maximum 10 cycles. The goal is reaching a genuinely working state, not merely cycling a fixed number of times.

After 10 cycles without PASS: suspend the outer PVL. Surface to user with: "(N) remaining CONDITIONAL concerns, (M) attempted supplements, (K) concerns that could not be resolved." The user decides to accept CONDITIONAL and proceed, or defer the program to backlog.

After PASS: output /goal block → phases execute autonomously.

**Phase program validate-contract in /goal block:** The `Validate contract:` field points to the umbrella plan path. Per-phase contracts are listed as: `Phase N: [plan path] — contract: outer (will be replaced by inner PVL)`. Execute-agent reads its phase's validate-contract from the phase plan file at execution time — NOT from the /goal block's outer contract field.

---

## Inner Loop Per Phase

Every phase runs this 7-step loop at full RIPER-5 rigor. No shortcuts.

The outer loop produced a complete phase plan. The inner loop runs its own full R+I to surface new facts, then updates the plan, then runs a full PVL with current evidence. The inner loop has evidence the outer loop did not have. It is expected to improve the plan.

Every step fires all Tier-0 skills at entry. No skipping Tier 0.

```
STEP 0: Tier-0 Skills (MANDATORY at entry of EVERY step)
  vc-intent-clarify
  vc-context-discovery (Part A + B frontmatter)
  vc-plan-discovery (alongside context-discovery)
  vc-review-situation
  vc-agent-strategy-compare (strategy for THIS step's specific work)
```

> **Single-trip under /goal.** These Tier-0 skills run as silent prep for the phase's entry Combined Clarification Gate — under an active /goal the gate auto-proceeds, so they produce no user pause. They are mandatory work, not a user round-trip.

**Phase-level loop-back.** A phase's exit Phase-End Recommendation Gate is bidirectional: it may recommend advancing to the next phase OR re-running the same phase (e.g., inner PVL CONDITIONAL with unresolved gaps, or EVL classification "Keep in active/ — needs further testing"). Phase-level loop-backs are bounded by the vc-autoresearch 10-cycle cap (the same cap that bounds inner PVL and EVL). Under /goal these loop-backs are autonomous; they do not add a user gate.

Also read prior phase reports before any work begins for this phase.

**Dependency Viability Pre-Check (Step 0):** After reading prior phase reports, check the umbrella plan's `## Phase Ordering` for this phase's declared dependencies. If a dependency phase was BLOCKED-skipped and this phase's checklist explicitly requires that phase's deliverables: classify this phase as Dependency-BLOCKED at Step 0.

Step 0 Dependency-BLOCKED is handled entirely by the orchestrator — no agent is spawned, no machine-readable signal is emitted.

Action on Dependency-BLOCKED:
- Write a minimal phase report noting: `Dependency-BLOCKED — dependency phase [N] was BLOCKED-skipped; this phase cannot proceed until Phase [N] deliverables exist.`
- Register as BLOCKED in the umbrella plan.
- Append `status: BLOCKED-skipped — dependency BLOCKED at Step 0; files never modified` to this phase's entry in `phase-blast-radius-registry.md`.
- Do not run R→I→P→PVL. Proceed directly to the next phase.

Phase Loop Progress notation for Step 0 Dependency-BLOCKED:
`- [x] 0. Dependency-BLOCKED — [dependency phase N] not yet complete; minimal report written; advancing to Phase N+1.`

If the umbrella plan has no `## Phase Ordering` section: treat as "no dependencies declared" and proceed. Emit a CONCERN in the phase report: "Umbrella plan missing `## Phase Ordering` — dependency pre-check could not run; proceeding with no-dependency assumption."

**Prior phase report reading strategy:**
- Read the immediately prior phase report (Phase N-1) in full.
- For all earlier phases (Phase N-2 and before): read only the `## Forward Preview` section.
- Phase 1 edge case: no prior reports exist. Skip prior-report reading entirely. Read the umbrella plan's `## Stable Program Goal` section for program context instead.

**Boundary definition:**
- Phase 2 (first inner phase): Phase 1 is immediately prior → read in full. No earlier phases.
- Phase N (N ≥ 3): Phase N-1 → read in full. Phases 1 through N-2 → read Forward Preview only.

```
STEP 1: RESEARCH (full — scoped to this phase)
  Treat the outer-loop phase plan as prior art, not as a constraint.
  Surface new findings, drift, test gaps, library changes, blast radius updates.
  Run vc-test-coverage-plan (Part A + B + C + D).
  Emit infra improvement suggestions for any agent-probe/known-gap tiers found.
```

```
STEP 2: INNOVATE (full — scoped to this phase)
  Explore 2+ approaches. Run vc-predict. Produce Decision Summary.
  Do not skip vc-predict because "the outer loop already decided the approach."
  Inner R+I may surface a better approach or invalidate the outer-loop choice.
```

```
STEP 3: PLAN-SUPPLEMENT (update the existing phase plan with inner R+I findings)
  vc-plan-agent in supplement mode — update the existing plan in place.
  Do NOT create a new plan file.
  Update: Implementation Checklist, Blast Radius, Test tier assignments, Verification Evidence.
  Add: Test Infra Improvement Notes from inner R findings.
  The resulting plan must be complete and executable — not layered patches.
```

Step 3 runs BEFORE the inner PVL (Step 4). Any V7-triggered supplement from Step 4's inner PVL uses a narrow scope fence from Section 5 V7. These are two distinct supplement invocations with different scope permissions — never combine them in one plan-agent invocation.

Under /goal: when Step 3 completes, vc-plan-agent emits:
- If changes were made: `PHASE_COMPLETE: PLAN-SUPPLEMENT — phase plan [N] updated; Inner Loop Refresh Note written`
- If no changes needed: `PHASE_COMPLETE: PLAN-SUPPLEMENT — no changes; plan current`

Disambiguation: listen for `PHASE_COMPLETE: PLAN-SUPPLEMENT` (not `SUPPLEMENT_APPLIED` — that signal is reserved exclusively for V7 plan-validate-fix loop completions).

For the 'no changes; plan current' variant: no Inner Loop Refresh Note is written → V1 will find the existing PASS contract unmodified and may auto-proceed to EXECUTE (no re-validation required when no new facts surfaced).

**Important:** V1 cannot distinguish "Step 3 ran and found no changes" from "Step 3 not yet run" — both produce an absent Inner Loop Refresh Note. The Phase Loop Progress Step 3 checkbox is the only distinguishing artifact. The orchestrator MUST confirm Step 3 is ticked before treating V1 auto-proceed as valid under /goal.

```
STEP 4: PVL (full V1→V7 — with current inner-loop evidence)
  Runs against the plan as updated by Step 3.
  Maximum 10 validate-fix loops.
  Under /goal: CONDITIONAL → auto-supplement; BLOCKED → see BLOCKED handling below.
```

BLOCKED handling at Step 4:
1. Write a backlog NOTE for the entire phase.
2. Append `status: BLOCKED-skipped — blast-radius claim unresolved; files never modified` to this phase's entry in `phase-blast-radius-registry.md`.
3. Cascade check: if the immediately prior phase (N-1) is also BLOCKED-skipped with no intervening PASS phase — trigger Cascade BLOCKED Protocol immediately. Do not continue to step 3.
4. If no cascade: continue to the next phase.

vc-validate-agent emits: `PHASE_SKIPPED: BLOCKED — [phase N] backlog note written; advancing to Phase [N+1]`

The above BLOCKED rules apply to PVL (Step 4). For BLOCKED at other step types (Research, Innovate, Plan-supplement, EXECUTE, EVL, UPDATE PROCESS): see `What Moves Forward Without User Input` §NEEDS_CONTEXT step-class rule.

```
STEP 5: EXECUTE (fully autonomous)
  Before modifying any file: check phase-blast-radius-registry.md for claims by other phases.
  If a file you are about to modify appears in another phase's active claim: flag the conflict
  in the phase report and halt for orchestrator resolution before modifying that file.
  vc-execute-agent also checks the program registry at Step 0. If both the current phase AND its immediate prerequisite phase are BLOCKED-skipped: vc-execute-agent emits `CASCADE_BLOCKED:` and suspends.

  Full EXECUTE behavior. Level 1 per-section loop runs without user gates.
  Never pauses: irreversible/outward-facing/billing actions not in contract are
  deferred to backlog (skipped, not performed) and the loop continues.
```

```
STEP 6: EVL (Execute-Validate-Loop — Level 2)
  Orchestrator-owned post-DONE sweep.
  Execute-validate-fix loops: scoped to the failing gate only. No scope expansion.
  Root cause broader than gate → follow-up plan stub (not scope-expand).
  Under /goal: orchestrator auto-accepts known gaps. Records in phase report + backlog note.
  Emit: PHASE_COMPLETE: EVL — EVL HANDOFF SUMMARY emitted; preliminary packet written
```

```
STEP 7: UPDATE PROCESS for this phase
  Full UPDATE PROCESS behavior (see file 10-update-process.md).
  Write phase report. Update umbrella ## Current Execution State. Write backlog notes.
  Run validators: vc-audit-vc, vc-audit-context, vc-audit-plans as applicable.
  Run the phase-plan-completeness and phase-reports validators.
```

> **Two umbrella validators, disjoint scope.** `validate-umbrella-artifact.mjs` is the single writer of, and checks the structural shape of, one umbrella file (required sections, frontmatter, /goal-block length). `validate-umbrella-state.mjs` checks cross-phase state/inventory across the program (execution-state freshness, phase-status-table drift). Neither subsumes the other.

Advancement signal: `PHASE_COMPLETE: UPDATE PROCESS — [phase N name] archived; phase report written; process commit invoked`

Orchestrator ticks Step 7 checkbox, then proceeds to Phase N+1 Step 0.

### Commit Timing (under /goal)

Two commits per phase:

1. **Source commit at EVL-green** — after EVL HANDOFF SUMMARY is emitted; includes implementation files only. Format: `phase(N): [phase-plan-title] — EVL green, [N] gates, [N] known-gaps`

2. **Process commit after UPDATE PROCESS** — includes archived plan, context doc updates, phase report, memory notes. Format: `process(N): [phase-plan-title] — UPDATE PROCESS complete`

Do not commit mid-phase. Source commit fires after EVL HANDOFF SUMMARY, before UPDATE PROCESS begins.

---

## Final Cross-Phase E2E Verification

A multi-phase program must END with one final, comprehensive **whole-system E2E verification gate** that proves the integrated program actually works end-to-end. It runs after the last phase's EVL (Step 6) and UPDATE PROCESS (Step 7), and BEFORE program closeout. Per-phase EVL stays scoped to its own phase slice; this final gate is scoped to comprehensive cross-phase behavior — it exercises the program as a single integrated system, across the surfaces every phase delivered.

**Why it exists:** Each phase's EVL only proves that phase's own slice. Nothing in the per-phase loops proves the phases compose correctly into a working whole. This gate closes that gap before the program is declared delivered.

**Mechanics:**

1. Run it as an EVL-style loop, bounded by the same vc-autoresearch 10-cycle cap that bounds inner PVL and EVL.
2. On failure: create fix stubs (scoped follow-up plan stubs for the failing cross-phase scenarios) and/or loop back to the responsible phase — bounded by the 10-cycle cap.
3. Re-run the whole-system E2E from the start after each fix iteration.
4. Continue until: all cross-phase scenarios pass (SUCCESS → proceed to closeout), or the 10-cycle cap is reached.

**Cap-exhaustion behavior under /goal:** On cap-exhaustion, do NOT halt forever. Classify the program **"delivered-with-gaps"**, write backlog notes for every failing cross-phase scenario, and finish (proceed to closeout). A /goal program never ends in an infinite halt waiting on a human. (Interactive sessions surface a structured summary and ask instead.)

**Scope discipline:** This gate is whole-system / cross-phase only. It does NOT re-run or scope-expand any individual per-phase EVL — those remain scoped to their own slices and already ran during their phases.

---

## Autonomous /goal Rules

### What Moves Forward Without User Input

This list is the concrete expansion of "both per-phase gates auto-proceed": under an active /goal, the entry Combined Clarification Gate and the exit Phase-End Recommendation Gate of every phase resolve to their recommended option automatically, and the orchestrator proceeds on its own for:

- Phase transitions (Step 7 → Step 0 of next phase) — the exit gate auto-proceeds
- Both per-phase gates (entry Combined Clarification Gate + exit Phase-End Recommendation Gate) auto-resolving to their recommended option
- Strategy selection (Step 2 and all Tier-0 decisions)
- V5 accept/continue decisions — note: **V5 is the within-PVL user-confirmation gate** (Section 8 V5), not a separate phase-level user gate; under /goal it auto-resolves (CONDITIONAL → plan-supplement + re-run; BLOCKED → backlog + skip)
- Plan supplements
- Level 1 iterate-until-green loops
- EVL execute-validate-fix loops (scoped to failing gate)
- **Phase ordering restructuring** — reordering independent phases and marking dependency relationships. NOT autonomous: removing a phase plan entirely, merging two phases into one (both require user input).
- Creating a new phase plan file to resolve a blast-radius conflict. After writing a new phase plan file mid-program: update the `## Pre-PVL Conflict Resolution` section in the umbrella plan to cover the new plan's blast-radius claims. Compare new plan's blast radius against all existing phase plans' blast-radius registries. If no conflicts: append `[New phase [N] added [YYYY-MM-DD] — no new conflicts found]`. If conflicts: apply the BLOCKED conflict re-scope sub-procedure.
- Key or credential access required for fixes (proceed and document the access need in the phase report)
- Pausing when inner RESEARCH finds the current phase would break a prior phase's surface (restructure the program autonomously before re-executing)
- CONTEXT_PARTIAL warning from vc-context-discovery (proceed with best-effort context; note partial context in phase report)
- Outer PVL CONDITIONAL with isolated BLOCKED plan (auto-trigger plan-validate-fix loop)
- Backlog note creation and follow-up plan stub file creation
- EVL known-gap acceptance (record in phase report and backlog note)
- **Autonomous plan creation PVL:** Autonomous creation includes: writing the plan file + registering it in the umbrella + triggering inner PVL (via vc-validate-agent) before EXECUTE begins. PVL for new mid-program plans follows phase program V6 semantics: write validate-contract only; do NOT write a new /goal block; the umbrella's Stable Program Goal remains authoritative.

  **Skill sequence for mid-program plan creation:** Use abbreviated PLAN scope: Tier-0 skills + vc-scout + vc-generate-plan + vc-test-coverage-plan. Do NOT invoke vc-generate-phase-program. Do NOT use agent-team. DO invoke vc-agent-strategy-compare. Scope fence: the new plan covers only the conflict-resolution surface.

**Step-class rule** (applies to BLOCKED, NEEDS_CONTEXT, and CONTEXT_PARTIAL at any inner-loop step):
- Steps 1–3 (R, I, P-supplement) → continue with degraded quality; emit `CONTEXT_PARTIAL` warning in phase report
- Step 4 (PVL) BLOCKED → write backlog NOTE for the entire phase; skip to next phase (not next step); register as BLOCKED in umbrella
- Step 5 (EXECUTE) BLOCKED → treat as EVL L1 failure; create follow-up plan stub scoped to the missing context surface
- Steps 6–7 (EVL, UP) → continue with note; EVL can run partially (record which gates were skipped)

**Phase reordering notice:** Any autonomous restructuring emits `PHASE_RESTRUCTURE_NOTICE` in the current phase report under `## Phase Restructuring`:

```
## Phase Restructuring
- Original ordering: [comma-separated phase names in prior order]
- New ordering: [comma-separated phase names in new order]
- Reason: [one sentence — why the reordering was safe/autonomous]
- Affected phases: [comma-separated phase names that moved]
```

Emit this when the umbrella plan's `## Phase Ordering` sequence changes. Marking a dependency relationship without changing execution order does NOT trigger this signal.

### Real-World Side-Effect Actions (deferred to backlog under /goal — never performed autonomously)

A true `/goal` run pauses for nothing, so it also never *performs* an irreversible / outward-facing / costful real-world action on its own. When the loop reaches one of the actions below, it does **NOT** stop and does **NOT** execute it — it writes a **backlog note** describing the action that needs a human to perform/approve, **skips** it, and continues. (Interactive sessions stop and ask instead.)

Actions that are deferred-to-backlog under /goal rather than performed:

- DNS changes
- Production deploys
- Billing events (Stripe charges, credit mutations)
- Destructive schema migrations NOT listed in validate-contract
- Outward-facing changes (emails, webhooks, external API calls) not in contract
- Any action the contract says `mustStopBeforeFinalize: true`
- Secret rotation or credential mutation — actual DB write to the secrets table or sidecar credential reload
- Destructive filesystem operations on production volumes or prod-equivalent containers
- Elevating permissions, adding new admin endpoints, or expanding trust boundaries
- Cost-bearing cloud provider operations not pre-scoped in the validate-contract (new Hetzner VPS, Cloudflare Zone changes, Bright Data bandwidth operations)

> **Downstream caveat (accepted):** because these actions are skipped, any later phase that assumes the deploy/charge/migration already happened will run against the un-applied state. That is the accepted trade-off of "never stop" — the backlog note is the record the user works through afterward to bring the world into the state the program assumed.

DNS changes, production deploys, and billing events are deferred even if listed in the validate-contract. Schema migrations are deferred only if NOT listed in the validate-contract.

### Loop-Control Safety Bounds (still surface under /goal — these are the autonomy-termination net, not real-world actions)

These are not side-effects to skip; they are the bounds that stop a /goal program from looping forever, so they still surface for a decision:

- **Outer PVL 10-cycle cap reached without PASS** — surface structured summary and wait for decision.
- **Cascade BLOCKED** — two or more consecutive phases (N and N+1) are BLOCKED with no intervening PASS phase.
- **Blast-radius conflict still unresolved after 1 re-scope cycle** — surface a structured summary showing (a) which phases conflict, (b) which files, (c) resolutions tried — then await the user's decision before spawning outer vc-validate-agent.

**Inner vs. outer PVL gate distinction:** Inner PVL BLOCKED → backlog note, no user gate, continue. Outer PVL 10-cycle cap → user gate (cost-safety override of autonomy).

**Autopilot Mode integration:** When a user triggers Autopilot Mode (see `process/development-protocols/autopilot.md`), the per-phase gates listed above auto-proceed via the standing EXECUTE consent granted at autopilot trigger time. The three hard stops (irreversible/outward-facing action, Cascade BLOCKED, needs-live-provider feasibility probe) remain manual-first even under Autopilot Mode.

### Cascade BLOCKED Protocol

If two or more consecutive phases are BLOCKED (Phase N AND Phase N+1 are both BLOCKED with no intervening PASS): the orchestrator must suspend the program.

**Consecutive** means phases N and N+1 in the umbrella plan's `## Phase Ordering` are both BLOCKED with no PASS phase between them. Phase 2 BLOCKED + Phase 4 BLOCKED with Phase 3 PASS does NOT trigger this. Phase 2 BLOCKED + Phase 3 BLOCKED DOES trigger it.

Actions:
1. Write a structured dependency analysis to `process/features/{feature}/reports/cascade-blocked-{YYYY-MM-DD}.md` (or `process/general-plans/reports/` for general plans).
2. Surface to user with a recommendation (restructure phases, resolve Phase N gap first, or scope-reduce).
3. Await user input before continuing.

Required fields in the analysis file:

```yaml
phases_blocked: ["Phase N", "Phase N+1"]
dependency_chain: "Phase N BLOCKED because [reason]; Phase N+1 BLOCKED because it depends on Phase N's [deliverable] which was never produced"
attempts_made: [validate-fix loops tried, re-scope attempts]
recommendation: "restructure | resolve Phase N first | scope-reduce Phase N+1"
```

**Owner:** orchestrator (coordination artifact exception). After writing the cascade analysis file: paste a summary in chat and await the user's decision.

**Cascade BLOCKED applies during inner-loop execution only.** Outer PVL isolated BLOCKs trigger the BLOCKED conflict re-scope sub-procedure instead.

**All-phases-BLOCKED terminal condition:** If all phases in the umbrella plan show BLOCKED or BLOCKED-skipped (no COMPLETE or COMPLETE_WITH_GAPS phases):
1. Write a minimal program failure report to `process/features/{feature}/reports/`.
2. Update umbrella `## Current Execution State` to show all-blocked.
3. Write a single backlog note summarizing the program-level failure.
4. Do NOT archive the umbrella plan to `completed/` — leave in `active/`.
5. Surface to user: "All phases BLOCKED — program suspended. No working changes to commit."

### Session Crash Recovery

Recovery has two triggers. The **common case** is a human re-pasting the /goal block into a new session. The **silent case** is any other context gap — most importantly a silent mid-run context compaction, where no human re-pastes anything and the orchestrator simply loses its in-context loop position. Both triggers run the same re-hydration procedure: position is recovered from the umbrella files, never assumed from in-context memory.

If a /goal session is interrupted mid-phase:

1. **Trigger.** Either the user re-pastes the /goal block (common case), OR the orchestrator detects a context gap / silent mid-run compaction and auto-re-hydrates WITHOUT waiting for a human re-paste (silent case).
2. Orchestrator reads umbrella plan `## Current Execution State` to find last-known phase status.
3. Orchestrator reads `## Phase Loop Progress` checkboxes in the current phase plan:
   - All checked → phase completed; start from next phase
   - Some checked → phase was in progress at the checked step; research what was done, then resume from first unchecked step
   - None checked → phase not yet started; begin fresh from step 1
4. Orchestrator reads the latest phase report for the current phase to recover in-flight detail (last EVL gate run, recorded cycle counts, known gaps).
5. **Git reconciliation (integrity check).** Before resuming, cross-check the claimed umbrella/report state against actual git state — the last EVL-green commit, the working-tree diff, and the blast-radius registry status. If the umbrella claims a phase is COMPLETE/EVL-green but no corresponding source commit or diff exists (a stale or lying umbrella): trust the git evidence, correct the umbrella state, and resume from the genuinely-reached position rather than the claimed one.
6. If phase was mid-EXECUTE (some section items ticked): execute-agent reads the plan, finds the last ticked item, resumes from the next item. Do not re-run ticked sections.
7. If EVL was in progress: re-run EVL from step 1. EVL gate *results* are not persisted, so re-running the gates is safe — but the *cycle count* IS recovered from the phase report (see Cycle count preservation below) so the re-run does not reset the 10-cycle bound.

**Cycle count preservation:** Before re-running EVL, check the phase report for any `EVL execute-validate-fix loop count` recorded during the interrupted session. If count N was recorded: start the re-run counter at N, not 0.

---

## Phase Loop Progress Format

All new phase plans must use this 7-step format:

```
## Phase Loop Progress
- [ ] 1. RESEARCH — prior phase reports read; test context loaded
- [ ] 2. INNOVATE — approach decided; Decision Summary written
- [ ] 3. PLAN-SUPPLEMENT — existing phase plan updated with inner R+I findings; Inner Loop Refresh Note written if sections changed
- [ ] 4. PVL — validate-contract written; /goal block output

BLOCKED-skip variant: when vc-validate-agent emits `PHASE_SKIPPED: BLOCKED`, orchestrator marks Step 4 as:
  - [x] 4. PVL — BLOCKED-skipped; backlog note written
Steps 5–7 are NOT run for this phase. Advance directly to Phase N+1 Step 0.

- [ ] 5. EXECUTE — all Level 1 section loops green
- [ ] 6. EVL — all EVL gates green; follow-up stubs registered; EVL HANDOFF SUMMARY written (yaml fenced block); preliminary packet written to disk at `{preliminary_packet_path}`; Advancement signal: `PHASE_COMPLETE: EVL — EVL HANDOFF SUMMARY emitted; preliminary packet written`
- [ ] 7. UPDATE PROCESS — archived; context updated; committed
```

**Migration note:** Existing active phase plans with 5-step Progress sections are valid. Do not force-migrate them. New phase plans created after this specification must use the 7-step format.

The 5-step model in orchestration.md (steps 1a, 1b, 2, 3, 4) describes which agent gets spawned — it is the orchestrator's spawn-event view. The 7-step format is the plan file checkpoint view — what a human reading the plan can verify happened. Both remain valid for their respective purposes.

---

## MID_PROGRAM_PLAN_CREATED Signal

When vc-plan-agent creates a new plan mid-program (for conflict resolution or phase insertion), it emits: `MID_PROGRAM_PLAN_CREATED: [plan file path] — inner PVL required`

Orchestrator reaction:
1. Trigger inner PVL for the new plan only.
2. Do NOT output a new /goal block.
3. Umbrella Stable Program Goal remains authoritative and unchanged.

After inner PVL completes (PASS): proceed with the new plan as an additional phase in the program sequence.

---

## Phase Insertion Renumbering

When a new phase is inserted between existing phases (e.g., between phase 2 and phase 3):

1. Update `## Phase Ordering` in all active plans to reflect new numbering.
2. Re-annotate blast-radius registry entries with new phase numbers.
3. Re-number Context Envelope `phase` fields in any session-level context blocks.
4. Emit: `PHASE_RENUMBERED: [old-N] → [new-N]` for each shifted phase.

Orchestrator reaction on `PHASE_RENUMBERED`: update all internal phase number references in the umbrella plan (section headers, dependency references, Phase Loop Progress step numbers).

---

## Conflict Resolution Priority Cascade

When any phase finds a conflict, gap, or flaw — follow this priority order:

1. Fix immediately — if within current blast radius and reversible.
2. Update affected phase plans and the umbrella plan to reflect the fix.
3. Create new phase plan(s) for work that cannot be fixed inline. Update umbrella execution state.
4. Continue execution with the updated program.
5. Write a backlog note — last resort only when 1–4 are all genuinely impossible.

Never halt the program for a conflict that can be resolved by updating plans and continuing.

---

## Agent Team Coordination — Templates

| Template | Path |
|---|---|
| Umbrella plan | `vc-generate-phase-program/templates/umbrella-plan-template.md` |
| Phase stub | `vc-generate-phase-program/templates/phase-stub-template.md` |
| Program Goal Charter | `vc-generate-phase-program/references/program-goal-charter-template.md` |
| Program SPEC (umbrella product-discovery requirements doc governing inner phases) | `vc-generate-phase-program/templates/program-spec-template.md` |
| Phase loop workflow | `vc-generate-phase-program/templates/phase-loop-workflow-template.js` |

**Phase-loop workflow template — context slots:** the template carries `{test-runner}` (from the Context Envelope; the multi-runner `bun test | vitest` form is a display convention only — the template must expand to SEQUENTIAL execution, never a literal shell pipe), `{blast-radius-paths}` (from Context Envelope blast-radius-packages), `{validate-contract-path}` (the phase plan's validate-contract), and `{infra-context-group}` (the relevant context group for the phase).

**File editing via agent delegation (workflow design note):** the Workflow tool runs in a headless JS context with no direct file access, so all file edits MUST be delegated to `agent()` calls. Craft each agent prompt to include the exact file path, the target section, and the required change.

**Self-healing:** mid-execution supplement → diagnosis before retry → bounded by the same 10-cycle cap per section that bounds inner PVL and EVL.
