---
name: protocol:vc-system-behavior-08-validate
description: "VALIDATE phase (PVL) reference: V1–V7 gate sequence, fan-out layers, and validate-contract schema."
date: 09-06-26
metadata:
  node_type: memory
  type: protocol
  read_order: 1
  required: false
  read_when: "running or auditing the VALIDATE/PVL phase"
---

# VALIDATE Phase (PVL)

## What This Phase Does

The VALIDATE phase turns a written plan into an executable contract. It runs a loop called the Plan-Validate-Loop (PVL). The output is a `## Validate Contract` section written into the plan file.

---

## Agent and Tools

**Agent:** `vc-validate-agent` (sonnet)

VALIDATE is planning/analysis work, not source-code execution, so it runs on sonnet. Only phases that carry out real code or build execution (EXECUTE) run on opus. See the model-selection policy in `.claude/skills/vc-agent-strategy-compare/SKILL.md` §Model Selection Policy.

**Tools:** Read, Grep, Glob, Bash, Write (only inside `process/`) — no source code modifications

---

## The PVL Loop

PVL is a loop, not a single pass. It goes V1 through V7. If V7 returns CONDITIONAL or BLOCKED, a plan-validate-fix loop fires and the loop restarts from V1.

```
PVL loop:
  V1 → V2 → V3 → V4 → V5 → V6 → V7
                                  │
                        PASS ─────┴──► exit PVL
                        CONDITIONAL → plan-validate-fix loop → back to V1
                          └─ if vc-plan-agent NEEDS_CONTEXT (partial): backlog NOTE + partial supplement + back to V1
                        BLOCKED → plan-validate-fix loop (or backlog note) → back to V1
```

> **Single-trip rule (PHASE-GATES).** VALIDATE has exactly two user touchpoints: an **entry** Combined Clarification Gate (`03-session-start.md` Step 6.5 — intent restatement + clarifying questions + 4 strategy options + PVL run-mode, in ONE `AskUserQuestion`) and an **exit** Phase-End Recommendation Gate (V4, single round-trip). The V1–V7 PVL gates are internal machine gates, NOT user round-trips. V5 is the user-decision step *inside* the single exit gate (V4), not a separate pause. Under `/goal` both user gates auto-proceed. See `12-reference.md` PHASE-GATES.

### PVL Mode Selection

The PVL run-mode (auto-run vs step-by-step) is NOT a separate pause. It is folded into the entry **Combined Clarification Gate** as one of the strategy options.

**Under /goal:** Always auto-run. No user prompt.

**Outside /goal:** The entry gate surfaces this choice once (sticky for the full PVL), alongside the intent restatement and 4-option strategy suite:
> "Ready to start PVL. How do you want to run it?
> (a) Auto-run — validate → if CONDITIONAL/BLOCKED: plan-agent fixes → re-validate from V1 → repeat until PASS or 10-cycle cap.
> (b) Step-by-step — present V7 verdict → you confirm → plan-agent supplements → re-validate → present verdict → confirm → loop or move forward.
> Recommendation: [auto-run | step-by-step] because [one-line reason]."

Do **not** pause separately for this — it rides inside the single entry gate.

In **auto-run mode** (vc-autoresearch behavior): the orchestrator automatically routes back to vc-plan-agent on CONDITIONAL/BLOCKED, then back to vc-validate-agent (V1), per iteration without pausing.
In **step-by-step mode**: the orchestrator pauses after each V7 verdict and after each supplement before re-running.

The loop automatically routes back to vc-plan-agent each time PVL finds a gap. After the plan fix, PVL re-runs from V1. This continues until PASS, HALT_PLATEAU, or 10-cycle cap.

**Plan-validate-fix loop:** When V7 returns CONDITIONAL or BLOCKED:

1. vc-plan-agent (supplement mode) appends or updates checklist sections to address the flagged gaps.
2. The supplement is scoped only to the flagged gaps — no broader scope expansion.
3. PVL re-runs from V1 with the updated plan.
4. Under /goal: CONDITIONAL → auto-supplement and re-run; BLOCKED → write a backlog note, skip the phase.

**This loop is run by the `vc-autoresearch` skill** (`domain: plan`) as its bookkeeper —
autoresearch owns the iteration counter, plateau/regression detection, the per-iteration
report, and the 10-cycle cap; vc-validate-agent and vc-plan-agent keep their own gate and
supplement mechanics. See `vc-autoresearch` SKILL.md §PVL Wiring.

**Parallel fix agents:** The validate step already fans out (vc-validate-findings Layer 1 +
Layer 2). When the gap set spans independent plan sections, the orchestrator spawns
**multiple parallel plan-fix agents** — one per independent gap group, partitioned so no two
agents edit the same plan region — instead of a single sequential supplement. When gaps are
interdependent or touch one section, use a single plan-fix agent.

**Two supplement modes — do not mix them up:**

- **PVL-supplement mode** — triggered by a V7 gap list; only touches sections listed in the gap list.
- **Inner-loop plan refresh mode** — triggered by inner R+I findings (inner loop Step 3); broad scope; re-runs all required plan skills.

**Inner Loop Refresh Note:** When Step 3 (inner-loop refresh) and Step 4's V7 PVL-supplement both run in the same PVL invocation, Step 3 must append this note to the plan file before Step 4 begins:

```
## Inner Loop Refresh Note: [YYYY-MM-DD] — changed sections: [list of section names changed by Step 3]. Invalidates prior validate-contract.
```

This note tells the PVL-supplement agent which concerns are new (introduced by the refresh) rather than pre-existing. This prevents the supplement agent from dismissing new concerns that look like prior ones.

PVL-supplement mode must NOT write `## Inner Loop Refresh Note`. Only Step 3 inner-loop refresh writes it.

**Placement:** Put `## Inner Loop Refresh Note` immediately before `## Validate Contract`. If no validate-contract exists yet, put it at the end of the file.

**Overwrite rule:** If an `## Inner Loop Refresh Note` already exists from a prior cycle, replace it entirely. Keep exactly one such note per plan file. Use YYYY-MM-DD format so V1 date comparison works.

Section 8 is the canonical owner of this format. vc-plan-agent.md and vc-validate-agent.md reference this definition — do not redefine it independently.

**Inner PVL vs outer PVL:** In phase programs, PVL runs as both an outer PVL (once before /goal, covers all phases) and an inner PVL (once per phase, under /goal). Outer PVL BLOCKED = user gate. Inner PVL BLOCKED = backlog note + skip phase, no user gate.

---

## V1 — Pre-Check

### Tier-0 Skills (all fire before V1 gate work)

- **vc-intent-clarify** — restate what is being validated; do **NOT** pause here. The restatement + any clarifying questions feed the single entry **Combined Clarification Gate** (`03-session-start.md` Step 6.5), not a separate go-ahead pause.
- **vc-context-discovery** (Part A + B) — load context; must do first
- **vc-plan-discovery** (alongside) — find related plans; must do first
- **vc-review-situation** — confirm active plan and branch
- **vc-agent-strategy-compare** — set strategy for this PVL pass

### Tier-1 Skill

- **vc-scout** — verify all file paths in the plan exist on disk; hard stop if critical paths are missing. (This is a broken-precondition halt, not a safety pause; it halts even under /goal — a plan referencing non-existent critical paths cannot be validated.)

### Pre-V1 Smoke Test

Before V1 gate work: run `pnpm typecheck` and `pnpm test:local` scoped to blast radius. If either fails, emit a PRE-CHECK FAIL block and halt — the baseline must be clean before validation begins. (This dirty-baseline halt is a broken-precondition halt, not a safety pause; it halts even under /goal.)

**Baseline is necessary but NOT sufficient.** A clean `pnpm typecheck` + `pnpm test:local` baseline is a precondition for validation, not evidence that the developed behavior works. For every developed surface a clean PASS additionally requires comprehensive test scenarios across the 3 strategies, with at least one NAMED fully-automated E2E/integration scenario planned wherever that surface is automatable (see V3 §Net Gate Rule — Hard E2E gate). A green baseline alone can never lift a developed area to PASS.

### Structural Validation

Run `validate-plan-artifact.mjs` on the incoming plan file.

- Exit code 1 AND missing required sections (Implementation Checklist, Blast Radius, Verification Evidence) → HARD STOP. Report BLOCKED. Route back to plan-agent to add missing sections.
- Exit code 1 AND only metadata failures (missing Date/Status fields) → record as CONCERN, continue to V2.

### Phase Program Check

If an umbrella plan exists: verify it has a `## Pre-PVL Conflict Resolution` section, or an explicit note saying "no blast-radius conflicts found." If absent AND any phase plan has `## Potential Blast Radius Conflicts` sections → HARD STOP. Orchestrator must run Pre-PVL Conflict Resolution before spawning vc-validate-agent.

Also check: if `## Pre-PVL Conflict Resolution` has entries with `Action: update Phase [X] blast-radius claim`, verify those updates were actually made. If any `Action:` item is still unresolved → HARD STOP.

**Umbrella plan path source:** Read from the Context Envelope `active-plan` field (if it points to a file containing `## Stable Program Goal`) OR from the orchestrator prompt's `Plan reference:` field. If neither is available: emit `HARD STOP — umbrella plan path not found in Context Envelope or prompt; orchestrator must pass it explicitly.` (This is a broken-precondition halt, not a safety pause; it halts even under /goal — the phase-program check cannot run without the umbrella path.)

**Definition of "absent":** A section is absent if (a) it does not exist in the file, OR (b) it exists but contains only the heading line with no content beneath it. The `## Potential Blast Radius Conflicts` section "has conflicts" only when it contains at least one conflict entry — an empty heading alone does not count.

**Inner PVL exception:** Skip the phase program check entirely for inner PVL invocations. Outer PVL already resolved all inter-phase conflicts.

### Existing Contract Check

If `## Validate Contract` already exists with PASS or CONDITIONAL: this is **not** a separate user pause. Surface "re-validate or proceed to EXECUTE?" as one of the options inside the exit **Phase-End Recommendation Gate** (V4), not as a standalone mid-phase round-trip.

**Advisory:** The orchestrator's pre-routing check is advisory only. Always spawn vc-validate-agent and let V1 make the final decision via a fresh file scan. Never skip spawning based on cached state.

### /goal Auto-Proceed Rule

Under /goal: scan the plan file for `## Inner Loop Refresh Note` with a date newer than `## Validate Contract`.

- If present → continue with V1 checks, then proceed to V2. Do not skip V1 structural validation (validate-plan-artifact.mjs, vc-scout path check, vc-review-situation) — those checks run first, then proceed to V2.
- If absent AND existing contract is PASS → auto-proceed to EXECUTE. Emit: `V1 AUTO-PROCEED: existing PASS contract accepted (no Inner Loop Refresh Note found)`

**Step 3 inner-loop refresh MUST append the structured note:** `## Inner Loop Refresh Note: [YYYY-MM-DD] — changed sections: [list]. Invalidates prior validate-contract.` This note is the concrete mechanism that triggers V1 re-validation on the next PVL pass.

---

## V2 — Two-Layer Fan-Out

### Required Skills

- **vc-agent-strategy-compare** — run before spawning any validate agents. Input: N Layer-1 agents + M Layer-2 agents. Output: sequential / parallel / workflow / team recommendation.
- **vc-validate-findings** (Tier 1) — run and pass the plan file path. This skill runs both layers.

### Layer 1 (4 agents, always run in parallel)

| Dimension | What it checks | Context loaded |
|---|---|---|
| Infra/setup fit | Container/worker/runtime architecture; target paths, ports | all-context.md → container + infra groups |
| Test coverage | Realistic tier strategy; checks whether vc-test-coverage-plan was invoked and tier assignments exist for all blast-radius areas | all-tests.md routing chain |
| Breaking changes | API contracts, schemas, public contracts, downstream consumers | Plan Public Contracts + Blast Radius |
| Security surface | STRIDE/OWASP via vc-security internally | Invokes vc-security internally |

Per-agent output format: `Dimension / Status (PASS/CONCERN/FAIL) / Findings / Confidence / Notes`

**Infra/setup fit criteria:**

- PASS: all plan target paths exist on disk; all referenced ports match `container/all-container.md`; all referenced worker node APIs match `infra/all-infra.md`
- CONCERN: one referenced path does not exist but the plan creates it; port or service mismatch is documented in the plan as a known change
- FAIL: plan references a service, port, or API that no longer exists AND the plan does not account for it (e.g., plan targets removed container services — noVNC/x11vnc services removed from current image)

**Missing tier assignments:** A plan can reach V7 PASS without tier assignments, but the concern must be explicitly acknowledged in the validate menu. The concern must surface in the validate menu as: `No tier assignments found for [area]`.

### Layer 2 (one agent per plan section, run in parallel)

Each agent answers 4 questions: mechanical feasibility / plan gaps / conflicts / single highest-risk edit.

For each CONCERN: invoke vc-scenario. For high-risk items: invoke vc-predict.

### [V2-PROBE] Layer 2 Feasibility Probe — Halt Point

When a Layer 2 dimension agent identifies a plan section that depends on an **untested runtime/system behavior** — one that cannot be answered by reading source files — it emits:

  VC-FEASIBILITY-PROBE-NEEDED: [hypothesis] — cost-class: [class]

and halts its own analysis. The agent does NOT continue to the per-agent output format.

**Halt timing:** The orchestrator waits for ALL Layer 2 agents in the current V2 pass to complete (or emit a probe). Only after the full fan-out finishes does VALIDATE halt before V3 synthesis. This ensures a single re-spawn handles all probes from one V2 pass.

**Mandatory orchestrator action:** The orchestrator MUST spawn `vc-debugger` to conduct the empirical probe — it MUST NOT attempt to resolve the probe itself or treat the verdict as known without running vc-debugger. The emitting Layer 2 agent has halted and cannot self-emit the verdict. The sequence is always: probe signal → ORCHESTRATOR spawns vc-debugger → vc-debugger emits `VC-FEASIBILITY-VERDICT-READY` → orchestrator re-spawns vc-validate-agent with the verdict block. Skipping the vc-debugger spawn is a routing gap regardless of whether the orchestrator believes the answer is obvious.

**Mechanical checks (NO probe):** edit targets findable by Grep, file exists, schema field present, export name readable from source, port in the container table, config key in env.ts.

**Probe candidates (emit + halt):** any behavior that requires a running system, live network call, or in-container exec to verify — e.g. "does the gateway forward header X at runtime?", "does the container proxy honor config Y?".

**Multiple probes in one V2 pass:** orchestrator batches them; resolves (parallel where cost-class permits); re-spawns vc-validate-agent ONCE with multiple Prior Feasibility: blocks.

**No contract while pending:** VALIDATE does NOT emit a net gate and does NOT write a validate-contract after emitting a probe. The "no contract + VC-FEASIBILITY-PROBE-NEEDED signal" IS the routing signal.

**PVL accounting:** probe halt + re-spawn does NOT increment the PVL cycle counter and does NOT write a results.tsv row.

**Re-spawn entry:** re-spawned vc-validate-agent starts from V1 with Prior Feasibility: block(s) in context. Records resolved probes in a `## Feasibility Probes Resolved` subsection of the validate-contract (omitted when no probe ran).

---

## V3 — Synthesis

### Required Skills

- **vc-sequential-thinking** (Tier 1) — required when agents return conflicting verdicts
- **vc-test-coverage-plan** (Tier 1) — generates Section III: tier assignments per blast-radius area (C1 GAP)

vc-test-coverage-plan must run the full Part A context loading sequence (find tests/ context files, load all-tests.md chain, discover existing test files) before generating tier assignments. It must also emit infra improvement suggestions for any agent-probe or known-gap tier.

**VALIDATE runs NO tests — it reads context and DEVELOPS scenarios.** VALIDATE is read-only; it executes nothing. Its testing job is to comprehensively READ the full test context chain — the `process/context/tests/all-tests.md` router AND its complete downstream chain (`container-e2e`, `browser-automation`, `live-e2e`, etc.) — and to DEVELOP comprehensive test scenarios across the 3 strategies for everything the plan will build. The actual RUNNING of those scenarios happens later, comprehensively, in EXECUTE and the EVL (execute-validate) step. At VALIDATE, a "passing E2E" requirement means the plan NAMES a real automated E2E scenario (grounded in the test-context-discovery above) for the behavior; green-confirmation is deferred to EXECUTE/EVL. VALIDATE never claims a test is green — it cannot run one.

### Net Gate Rule

- Any FAIL → BLOCKED
- CONCERNs only → CONDITIONAL
- No FAILs or CONCERNs → PASS

**Hard E2E gate (every developed surface).** A clean PASS REQUIRES that EVERY developed surface (backend, container, browser, frontend) has comprehensive test scenarios across the 3 strategies, with a NAMED fully-automated E2E/integration scenario planned wherever that surface is automatable. "Passing E2E" here means the plan NAMES a real automated E2E scenario for the behavior, grounded in the test-context-discovery — it does NOT mean a green run at VALIDATE (VALIDATE runs nothing; green-confirmation is deferred to EXECUTE/EVL). If a contract's developed area is covered only by the weak tiers (agent-probe, known-gap — where automation was possible) — or by no planned gate at all ("vacuously green") — the strongest verdict it can earn for that area is CONDITIONAL, never PASS. Known-Gap is a rare justified residual only. The weak tiers (where automation was possible) and the "vacuously green" state (a validate-contract with zero planned fully-automated gates) are BANNED as terminal PASS states.

This is a **classification gate, not a /goal stop.** It changes how the work is classified (CONDITIONAL / not-archivable / keep in active-testing) and forces a test-building backlog stub; it never halts the program. Under a true /goal run the loop creates the test-building stub, classifies the developed work CONDITIONAL, and CONTINUES — it does not pause. Only the existing loop-control bounds (10-cycle cap, Cascade BLOCKED, blast-radius conflict) still surface. A developed surface with genuinely no automatable surface (rare, justified Known-Gap) is unaffected by this rule.

### Known-Gap Exclusion

Before deriving the net gate verdict, scan the plan's `## Known Gaps (Resolved via Backlog)` section. Any gap listed there is pre-classified as `known-gap: documented as NEW PLAN REQUIRED`. These are excluded from the CONCERN/FAIL calculation. They appear in V3 output under a separate `Known Gaps` sub-section.

### Intra-File Conflict Resolution

When Layer 1 and Layer 2 give different verdicts for the same blast-radius area:

- Layer 2 takes precedence (plan-section-level detail beats architectural).
- Exception: a Layer 1 FAIL for a hard dependency (missing service, unavailable port, removed API) overrides a Layer 2 PASS. These hard dependency FAILs cannot be overridden.
- vc-sequential-thinking is required when this conflict resolution rule would produce a BLOCKED verdict that Layer 2 alone would not have produced.

---

## V4 — Validate Menu (the single exit Phase-End Recommendation Gate)

V4 **is** the one exit round-trip for VALIDATE. Everything the user decides about this phase — accept, supplement, re-run agents, re-validate, loop back to PLAN, or proceed to EXECUTE — is presented here in one block with a recommended option marked. There is no separate post-V7 ask: the /goal-block print prompt and the `ENTER EXECUTE MODE` advance are surfaced as options *inside* this gate (see V7).

### Required Skill

- **vc-agent-strategy-compare** (Tier 0) — generates the execution strategy section (7-signal table + 4 options) for the next phase (EXECUTE)

### Menu Contents

The menu shows:

- Net gate status
- Parallel strategy recommendation
- Agent-count estimates
- Cost guard: over 30 agents → show breakdown; over 100 → require explicit confirmation
- Test gates per tier
- Dimension findings
- Open gaps
- Test infra improvement suggestions
- Strategy-by-fit
- User options

### User Options (bidirectional — present these as the single exit gate; mark the net-gate-driven default as Recommended)

The recommended option is derived from the V3 net gate: PASS → Accept/advance; CONDITIONAL → Accept-with-concerns or supplement; BLOCKED → back to PLAN.

1. **Accept → advance to EXECUTE** (recommended on PASS) → PASS gate; proceed to V6 contract write + V7 /goal block.
2. **Accept with noted concerns: [list]** → CONDITIONAL gate (recommended on CONDITIONAL with acceptable concerns).
3. **Re-validate (loop back, same phase)** → trigger plan-validate-fix loop → re-run PVL from V1 (recommended on CONDITIONAL with unresolved gaps). Bounded by the 10-cycle cap.
4. **Request plan changes → loop back to PLAN** → BLOCKED, return to PLAN (recommended on BLOCKED).
5. **Re-run specific agents** → re-run those agents only, then re-present this gate (max 3 re-runs per session before escalating to BLOCKED).

This gate is bidirectional: options 1–2 advance, options 3–4 loop back (re-VALIDATE or back-to-PLAN). Under `/goal`, the recommended option auto-proceeds (see V5).

---

## V5 — User Confirmation (the decision step of the single exit gate)

V5 is **not** a second user round-trip — it is the user's response to the V4 Phase-End Recommendation Gate. Canonical statement: the exit gate is V4; V5 is the user's response to it. There is exactly one exit round-trip, not two.

Do not advance to V6 without one of: Accept / Accept with concerns / Re-validate / Request plan changes / Blocked.

If the path is BLOCKED: invoke vc-problem-solving first to check whether the FAILs can be resolved.

### Under /goal Autonomous Execution

The agent self-decides:

- CONDITIONAL → trigger plan-validate-fix loop → re-run PVL from V1
- BLOCKED → if resolvable: plan-validate-fix loop; if not: write a backlog note and continue with remaining phases

### 10-Cycle Cap

10 CONDITIONAL cycles maximum. After 10 cycles without reaching PASS: accept remaining CONCERNs as known-gaps (write a backlog note for each), write the validate-contract with CONDITIONAL status listing all accepted CONCERNs, and proceed to EXECUTE.

Record in phase report: `Inner PVL CONDITIONAL cap reached at 10 cycles — [N] concerns accepted.`

### BLOCKED Gap Class Rule (under /goal inner loop)

- Structural/architectural BLOCKED (wrong approach, missing hard dependency, architectural flaw) → skip phase, write detailed backlog note, continue with remaining phases.
- Missing-detail/checklist BLOCKED (missing test command, unclear file path, underspecified API signature) → attempt 1 validate-fix loop; if still BLOCKED after 1 cycle → write backlog note and skip phase.

The 1-cycle limit resets per PVL invocation. If the outer PVL fixed one concern but the inner PVL finds a new BLOCKED concern with a different root cause, that counts as a fresh 1-cycle allowance.

---

## V6 — Contract Write

### Pre-Write Check

Before writing the validate-contract, scan the plan file for any existing `## Validate Contract` block. If one exists: the `supersedes:` field is mandatory in the new contract. Its absence is a V6 compliance failure — halt and add the field before proceeding. If no prior contract exists: omit `supersedes:`.

### Steps

1. Apply plan updates (write accepted-concern mitigations into plan checklist).
2. Write `## Validate Contract` into the plan file.
3. For single plans: write `## Autonomous Goal Block` into the plan file. For phase programs: verify the umbrella `## Stable Program Goal` is current — do NOT rewrite it.

### Autonomous Goal Block Format (single-plan work)

Uses the same /goal block structure as V7 (SESSION GOAL / Charter + umbrella plan / Autonomy / Hard stop conditions / Next phase / Validate contract / Execute start), with a 4000-character limit. Set `Charter + umbrella plan: N/A — single plan`. Write this block once per plan file. Do not rewrite unless the session goal changes materially.

For single-plan work: use the V7 field set (SESSION GOAL / Charter + umbrella plan / Autonomy / Hard stop conditions / Next phase / Validate contract / Execute start). For phase-program umbrella plans: use the Stable Program Goal format from orchestration.md (TARGET / PER-PHASE LOOP / HARD STOPS / SAFETY / TEST GATES / VALIDATE CONTRACT / START). These are distinct formats for distinct scopes — do not conflate them.

**Autopilot Mode — provisional block already exists at V6:**
When an `{slug}_AUTOPILOT_GOAL_{date}.md` file exists in the task folder, V6 does NOT
write a second `## Autonomous Goal Block` to the plan file. V6 records test gate commands
in the validate-contract `Test gates:` field as normal. TEST GATES refresh is done by V7.

### Required Fields in `## Validate Contract`

All of these must be present:

- `Status:` PASS | CONDITIONAL | BLOCKED
- `Date:` YYYY-MM-DD
- `date:` same value as Date above (enables machine parsing)
- `generated-by:` outer-pvl | inner-pvl: phase-N — the `generated-by` field enables the Phase Program Pre-Routing Check Step 4b in orchestration.md to determine whether to re-run PVL.
- `Test gates:` one line per tier per blast-radius area — exact commands
- `Dimension findings:` 4 rows — infra/setup-fit | test-coverage | breaking-changes | security-surface — with status per dimension
- `Open gaps:` list of CONCERNs/FAILs from V3 net gate (empty list if PASS)
- `What This Coverage Does NOT Prove:` prose section — required even when PASS; enumerates what each test gate does NOT cover. **Hard E2E rule:** if any developed behavior lands in this section (i.e. it is left without a planned automated gate where automation was possible), the contract cannot be PASS — it is at most CONDITIONAL, and a test-building backlog stub must be created for that behavior. Only a developed surface with genuinely no automatable surface (rare, justified Known-Gap) may remain PASS while listing items here.
- `Accepted by:` user name/date OR `session (autonomous, /goal execution)` with a structured concern list

### NEEDS_CONTEXT Sub-Case

If vc-plan-agent returns NEEDS_CONTEXT during a validate-fix loop (an out-of-scope gap): 

1. Record the out-of-scope gap(s) as backlog notes with `NEW PLAN REQUIRED` flag.
2. Add a `## Known Gaps (Resolved via Backlog)` section to the plan file (or append if it exists), with entry: `- [gap name]: known-gap: documented as NEW PLAN REQUIRED — backlog: [path]`
3. Treat the in-scope supplements as applied.
4. Self-loop back to V1 and continue. This counts as one PVL cycle against the 10-cycle cap.

Backlog note format:

```
## [gap name] — NEW PLAN REQUIRED
Date: [YYYY-MM-DD]
Source: plan-validate-fix loop — file-scope bright-line triggered
Gap: [description]
Files outside blast-radius: [list — or 'N/A' if new API surface only]
New API surface: [list — or 'N/A' if files-only]
```

Path routing: feature-scoped work → `process/features/{feature}/backlog/`; general work → `process/general-plans/backlog/`

### Inner PVL Contract Overwrite

When the inner PVL writes a new validate-contract, it replaces the existing one entirely. The outer contract is no longer valid once the inner loop has current evidence. No versioned contracts — overwrite semantics.

### supersedes: Field Rule

Write `supersedes:` whenever a prior validate-contract of any type already exists in the plan file and is being overwritten. Format: `supersedes: [prior contract date] ([prior contract type: outer-pvl | inner-pvl: phase-N])`.

Two cases:

(a) Inner PVL overwrites an outer PVL contract → `supersedes: outer-pvl`.
(b) A validate-fix loop overwrites a prior inner contract → `supersedes: inner-pvl-[date]`.

Always include the prior contract type in parentheses so the audit trail is readable.

When no prior contract exists in the file: omit `supersedes:` entirely.

Example: `supersedes: 2026-06-05 (inner-pvl: phase-2)`

### Phase Program Hard-Stop Change Rule

When inner PVL V6 produces a validate-contract with new or changed hard-stop conditions compared to the umbrella's Stable Program Goal: the orchestrator MUST emit `HARD STOP — validate-contract hard stops changed: [list new/changed stops]` and pause for user review. This is the only case where the umbrella Stable Program Goal must be updated mid-program. **Under /goal:** do not pause — record the changed hard-stops as a backlog note and continue (a true /goal run pauses for nothing; GOAL-NEVER-STOPS).

### `## Known Gaps` Ownership

This section is written exclusively by vc-validate-agent (V7 NEEDS_CONTEXT sub-case). vc-plan-agent in any mode must not modify, remove, or overwrite it. If a SUPPLEMENT REQUEST would require changes in the same location, halt and flag rather than overwriting.

---

## V7 — Gate and /goal Block

Emit a handoff block: Gate / Plan path / Contract written / Next step.

### Required Skill

- **vc-agent-strategy-compare** (Tier 0) — required — generate EXECUTE phase strategy (full 4-option suite with cost estimates)

### Verdict Paths

**PASS:**

Post-PASS hardening decision is required. The orchestrator reviews all validate findings — even non-blocking ones — and explicitly decides: "Are there concerns, edge cases, or recommendations that would strengthen the plan before execution?" If yes → spawn vc-plan-agent to harden checklist items → route to EXECUTE with the strengthened plan. If no → route to EXECUTE directly.

PASS means "no blockers found." It does not mean "plan is as strong as it could be."

**CONDITIONAL:**

Trigger a plan-validate-fix loop: vc-plan-agent supplements the checklist → PVL re-runs from V1.

V7 must emit a structured gap list before triggering the validate-fix loop:

```
SUPPLEMENT REQUEST:
- Gap [N]: Section [section-id] | Concern: [exact concern text] | Severity: [FAIL/CONCERN] | Suggested addition: [1-sentence checklist item suggestion]
- Gap [N+1]: ...
```

The plan-agent in supplement mode must:
- Only touch sections listed in the gap list.
- Not expand scope beyond the listed sections.
- If resolving a gap requires touching unlisted sections: flag it and halt. Do not self-authorize scope expansion.

Section IDs use the heading slug format: `## Heading Text` → `heading-text` (lowercase, spaces to dashes). If a Section ID in the SUPPLEMENT REQUEST does not match any `##` heading in the plan file: skip that section and emit `SUPPLEMENT_ID_UNKNOWN: [id]`.

After vc-plan-agent completes a V7-triggered validate-fix loop, it emits: `SUPPLEMENT_APPLIED: [plan path] — [N] gap(s) addressed`. Orchestrator reaction: PVL re-runs from V1.

`SUPPLEMENT_APPLIED` is emitted exclusively during V7 plan-validate-fix loops. It is NOT emitted for Step 3 inner-loop plan refresh — that completion emits `PHASE_COMPLETE: PLAN-SUPPLEMENT` instead.

If vc-plan-agent receives a SUPPLEMENT REQUEST with missing required pipe-delimited fields for any Gap entry: return `NEEDS_CONTEXT: SUPPLEMENT REQUEST malformed — Gap [N] missing [field]. Re-issue structured gap list.` Do not attempt to parse malformed input.

**BLOCKED:**

Trigger a plan-validate-fix loop if the block is resolvable. If not: HARD STOP — never route to EXECUTE without resolution.

Exception under /goal (inner PVL): apply V5 BLOCKED gap class rule — structural BLOCKED → skip phase + backlog note; missing-detail BLOCKED → 1 validate-fix loop max, then skip + backlog note. HARD STOP applies only to outer PVL outside /goal.

After a CONDITIONAL V7 where the user accepts concerns rather than supplementing, the orchestrator surfaces a gap-analysis pass showing validate concerns NOT reflected in the plan checklist — gap analysis distinct from vc-review-situation, currently performed inline.

### /goal Block — Mandatory Orchestrator Output After V7 PASS

This is not a skill. The orchestrator must output this block before routing to execute. It blocks routing to EXECUTE if not done.

```
SESSION GOAL: [title from plan ## Session Goal]
Charter + umbrella plan: [path to umbrella] | N/A — single plan
Autonomy: phases execute autonomously; pause only on hard stops — see feedback_autonomous_phase_execution.md
Hard stop conditions / safety constraints:
- [verbatim hard stop 1 from validate-contract]
- [verbatim hard stop 2]
Next phase: EXECUTE: [plan path]
Validate contract: [plan path] (inline)
Execute start: [first run command] | [e2e spec] | probe: [probe scenario] | high-risk pack: yes/no
```

> Under a true /goal run, the listed hard-stops/safety constraints are recorded as backlog notes and execution continues; they are live pauses only outside /goal.

Rules:
- Keep under 4000 characters.
- Name the umbrella plan path or state "N/A" explicitly.
- List hard stops verbatim from the validate-contract.
- If a /goal is already active, emit the block as an update (not a replacement). Signal with `(UPDATE — phase N)` prefix in the SESSION GOAL line.

vc-validate-agent writes the block to the plan file but does not auto-print it. The "print the /goal block for copy-paste?" prompt is **not** a separate pause — it is surfaced as part of the single V4 exit gate (Accept → advance to EXECUTE). Under an active /goal: skip it entirely and auto-print.

Once the user pastes the /goal block into the session, everything moves forward autonomously. EXECUTE + EVL + UPDATE PROCESS all run without user gates; under /goal even hard-stop-class items backlog-and-continue (only loop-control bounds — PVL 10-cycle cap, Cascade BLOCKED, blast-radius conflict — still surface).

#### Autopilot Mode — (UPDATE) Variant at V7

When an `{slug}_AUTOPILOT_GOAL_{date}.md` file exists (autopilot run active):

1. Orchestrator reads existing provisional goal block from that file.
2. Emits **(UPDATE)** variant in chat:
   - SESSION GOAL line: `(UPDATE) SESSION GOAL: [original title]`
   - TEST GATES field: replaced with actual gate commands from the validate-contract.
   - All other fields unchanged from the provisional block.
3. Original `{slug}_AUTOPILOT_GOAL_{date}.md` NOT overwritten — append an
   `## (UPDATE) [YYYY-MM-DD]` section with the refreshed TEST GATES content only.
4. Signal emitted: `AUTOPILOT_ACTIVATED: [task description] — entry phase: post-validate — goal block emitted`

Under `/goal`: emit the (UPDATE) block automatically as part of V7 exit.

---

## Orchestrator Behavior

After V7 PASS: output the /goal block in chat (mandatory). Pass exactly one plan file path to execute-agent.

If multiple active plans exist: ask the user to select one. Execute-agent must not infer the plan from ambient state.

---

## User Input

VALIDATE has exactly two user touchpoints — one at entry, one at exit. No mid-phase interruptions. The V1–V7 PVL gates are internal machine gates, not user round-trips.

- **Entry:** the Combined Clarification Gate (`03-session-start.md` Step 6.5) — intent go-ahead + 4-option strategy + PVL run-mode (auto-run vs step-by-step) in one round-trip.
- **Exit:** the V4 Phase-End Recommendation Gate, resolved at V5 — Accept→advance-to-EXECUTE / Accept-with-concerns / Re-validate (loop back) / Request-plan-changes (back to PLAN) / Re-run-agents. The /goal-block print prompt and `ENTER EXECUTE MODE` advance ride inside this one gate.
- **Mid-phase:** none.
- **Under /goal:** both gates auto-proceed on the recommended option (CONDITIONAL → auto-supplement + re-run; BLOCKED → V5 gap-class rule). The mandatory post-V7 /goal block is still written and printed.

---

## Exit Gate (machine checklist)

All of these must be true before the VALIDATE phase is done:

- `## Validate Contract` written in plan file
- `## Autonomous Goal Block` written (single plan) or umbrella verified (phase program)
- /goal block output in chat
- vc-agent-strategy-compare run for EXECUTE
- User responded at the single V4/V5 exit gate (interactive: `ENTER EXECUTE MODE` or other option; under /goal: auto-proceed)

Under /goal (PASS sub-case): emit `PHASE_COMPLETE: VALIDATE — validate-contract written. Proceed to EXECUTE.`

For a first-time PASS (no validate-fix loops): emit without parenthetical.
For PASS after N cycles: emit `PHASE_COMPLETE: VALIDATE — validate-contract written (after [N] validate-fix loop(s)). Proceed to EXECUTE.`

---

## Artifacts

- `## Validate Contract` section written into the plan file
- `/goal block` output in chat
